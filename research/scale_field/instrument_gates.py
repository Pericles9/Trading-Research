#!/usr/bin/env python
"""
Is the scale field detecting structure on the real tape, or is it responding to
sampling noise and to the geometry of its own read path?

DIAGNOSTIC. Records no decision, applies no gate to any phase, produces no digest.

The estimator is NOT modified. scale_field.py and event_panels.compute_event are
imported and called; everything here wraps them.

GATES, run in order, STOPPING ON THE FIRST FAILURE (brief s2 rule 7):

  0  log base            nat-log vs log10. Settles every threshold below.
  A  correctness         zero-sum identity, closed-bottom blobs, sign helper.
  B  noise ruler         what survives F < -2*sd(n_eff), by read_factor and scale.
  C  null rate           P(F < -2*sd) measured by Monte Carlo, not assumed.
  D  print-count         shaded fraction vs print count, dependent variable corrected.
  E  split-half          reliability against scale, on a fixed absolute grid.
  F  special row         is the texture the same at every height?

Usage:
    .venv/Scripts/python.exe research/scale_field/instrument_gates.py --gate 0
    .venv/Scripts/python.exe research/scale_field/instrument_gates.py --gate A
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(REPO_ROOT, "research", "phase_10d_diag1"))

import adapter                                                      # noqa: E402
import event_panels as ep                                           # noqa: E402
from scale_field import (_neff_coef, burst_on, field, field_exact,   # noqa: E402
                         s_min_for_rate)

CACHE = Path(os.environ.get("GATE_CACHE",
                            os.path.join(os.environ.get("TEMP", "/tmp"), "gatecache")))
OUT = Path(REPO_ROOT) / "results" / "scale_field" / "artifacts" / "instrument_gates"
KERNELS = ("centred", "onesided")
SEGMENTS = ("premarket", "rth", "post")
READ_FACTORS = (1.0, 2.0, 3.0, 4.0)


# --------------------------------------------------------------------------- #
# field cache -- compute_event is called unchanged, its Z stored as float32
# --------------------------------------------------------------------------- #

def event_field(event_id: str, cfg: dict, refresh: bool = False) -> dict:
    CACHE.mkdir(parents=True, exist_ok=True)
    p = CACHE / (event_id + ".npz")
    if p.exists() and not refresh:
        z = np.load(p, allow_pickle=True)
        return {k: z[k] for k in z.files}
    r = ep.compute_event(event_id, cfg)
    d = {"t_grid": r["t_grid"].astype(np.float64),
         "grid_ns": r["grid_ns"].astype(np.int64),
         "scales": r["scales"].astype(np.float64),
         "dt_eval": r["dt_eval"].astype(np.float64),
         "origin_ns": np.int64(r["origin_ns"]),
         "arrivals_ns": r["arrivals_ns"].astype(np.int64),
         "n_prints": np.int64(r["meta"]["n_prints"])}
    for k in KERNELS:
        kd = r["kernels"][k]
        d["Z_" + k] = kd["Z"].astype(np.float32)
        d["lam_" + k] = kd["lam"].astype(np.float64)
        d["smin_" + k] = kd["s_min_t"].astype(np.float64)
        for tag in ("primary", "overlay"):
            d["on_" + k + "_" + tag] = kd["reads"][tag]["on"]
            d["onraw_" + k + "_" + tag] = kd["reads"][tag]["on_raw"]
            d["sstar_" + k + "_" + tag] = kd["reads"][tag]["s_star"].astype(np.float64)
    np.savez(p, **d)
    return d


def cohort(n=None) -> pd.DataFrame:
    c = pd.read_csv(Path(REPO_ROOT) / "results" / "scale_field" / "artifacts"
                    / "event_panels_cohort.csv")
    return c if n is None else c.head(n)


def segment_masks(grid_ns, date) -> dict:
    b = adapter.segment_bounds_ns(date)
    return {k: (grid_ns >= lo) & (grid_ns < hi) for k, (lo, hi) in b.items()}


def jdump(obj, name):
    OUT.mkdir(parents=True, exist_ok=True)
    with open(OUT / name, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, default=float)
    print("wrote", (OUT / name).as_posix())


# --------------------------------------------------------------------------- #
# GATE 0 -- the log base
# --------------------------------------------------------------------------- #

def gate0() -> dict:
    """Every print at the same instant. F = -1.000 nat-log, -0.434 log10.

    Settled from the code path AND numerically, not from a docstring: field() forms
    lr = ln(c0/dt) and dlr = s^2*c2/c0 = s^2*lam''/lam = d ln lam / d ln s.
    """
    rng = np.random.default_rng(0)
    ts = np.sort(np.full(400, 0.0) + rng.normal(0, 1e-9, 400))
    ev, x = ts[1:], np.log10(np.maximum(np.diff(ts), 1e-12))
    rows = []
    for s in (0.1, 1.0, 10.0):
        for kern in KERNELS:
            f = field_exact(ts, ev, x, np.array([0.0]), np.array([s]),
                            neff_min=0.0, kernel=kern)
            rows.append({"s": s, "kernel": kern, "F": float(f["dlograte"][0, 0])})
    v = np.array([r["F"] for r in rows])
    base = ("natural" if abs(v.mean() + 1.0) < 1e-6 else
            "log10" if abs(v.mean() + 1.0 / np.log(10)) < 1e-6 else "UNKNOWN")
    return {"gate": "0", "rows": rows, "delta_limit_F": float(v.mean()),
            "log_base": base,
            "threshold_multiplier": 1.0 if base == "natural" else 0.4343,
            "pass": base == "natural"}


# --------------------------------------------------------------------------- #
# GATE A -- correctness
# --------------------------------------------------------------------------- #

def zero_sum_exact(seed=7, lam=20.0, T=120.0, scales=(0.5, 2.0, 8.0)) -> list:
    """THE ESTIMATOR CHECK, on the pairwise reference over the whole real line.

    F*lam_hat = s^2 * lam_hat'', and int lam_hat'' dt = [lam_hat']_-inf^+inf = 0, so
    the lam-weighted time integral is EXACTLY zero. field_exact can be evaluated
    outside the data support, so the identity is testable with no truncation. This
    form isolates 'the estimator is wrong' from 'the domain is finite'.
    """
    rng = np.random.default_rng(seed)
    ts = np.sort(rng.uniform(0, T, rng.poisson(lam * T)))
    ev, x = ts[1:], np.log10(np.diff(ts))
    out = []
    for s in scales:
        tg = np.linspace(-10 * s, T + 10 * s, 60001)
        f = field_exact(ts, ev, x, tg, np.array([s]), neff_min=0.0)
        F, L = f["dlograte"][:, 0], f["lograte"][:, 0]
        ok = np.isfinite(F) & np.isfinite(L)
        w = np.exp(L[ok])
        out.append({"s": s, "rel_residual": float((F[ok] * w).sum() / w.sum())})
    return out


def zero_sum_event(d, kernel) -> list:
    """The same identity on the rendered field, lam-weighted, per ladder scale.

    THE WEIGHT IS lam_hat*dt, NOT THE RAW PRINT COUNT, and the difference is not
    cosmetic. int F*lam dt = s^2 int lam'' dt = 0 is an exact identity; sum_i F(t_i)
    is a Monte-Carlo estimate of the same integral and carries sampling error
    ~sd/sqrt(n), which at n = 1e5 is ~1e-3 and can never reach the 1e-5 relative
    tolerance the brief sets. The exact form is the one that can be held to that
    tolerance, so it is the one run; the print-weighted mean is reported beside it.
    """
    Z = d["Z_" + kernel].astype(np.float64)
    lam_t = d["lam_" + kernel]
    dt = d["dt_eval"]
    scales = d["scales"]
    coef = _neff_coef(kernel)
    n = min(Z.shape[0], lam_t.size, dt.size)
    out = []
    for j, s in enumerate(scales):
        F = Z[:n, j]
        ok = np.isfinite(F) & np.isfinite(lam_t[:n])
        if ok.sum() < 100:
            continue
        w = lam_t[:n][ok] * dt[:n][ok]
        out.append({"s": float(s), "n_cells": int(ok.sum()),
                    "rel_residual": float((F[ok] * w).sum() / w.sum()),
                    "n_eff_median": float(coef * s * np.nanmedian(lam_t[:n][ok]))})
    return out


def closed_bottom_blobs(Z) -> dict:
    """Babaud et al. 1986: Gaussian scale-space creates no new zero-crossings going
    coarse. A negative region whose LOWER edge is closed -- defined, non-negative
    cells directly beneath it at the next finer ladder scale -- is masking,
    decimation or a bug.

    NOT APPLIED TO THE ONE-SIDED PANE. A half-Gaussian is not a scale-space kernel
    and the theorem does not hold there; running it would manufacture failures.

    A blob is EXEMPT where the cells beneath are NaN (the n_eff mask or the edge
    mask) or where it already sits on the bottom ladder rung -- that is the boundary
    of the domain, not a closed bottom.
    """
    from scipy import ndimage
    neg = np.isfinite(Z) & (Z < 0)
    lab, n = ndimage.label(neg, structure=np.ones((3, 3), int))
    if n == 0:
        return {"n_blobs": 0, "n_closed_bottom": 0, "closed_share": 0.0,
                "closed_area_share": 0.0, "neg_area": 0}
    closed = closed_area = total_area = 0
    for i, sl in enumerate(ndimage.find_objects(lab), start=1):
        rs, cs = sl
        sub = lab[rs, cs] == i
        area = int(sub.sum())
        total_area += area
        jlo = cs.start
        if jlo == 0:
            continue
        rows = np.flatnonzero(sub[:, 0]) + rs.start
        below = Z[rows, jlo - 1]
        if np.all(np.isfinite(below) & (below >= 0)):
            closed += 1
            closed_area += area
    return {"n_blobs": int(n), "n_closed_bottom": int(closed),
            "closed_share": closed / n,
            "closed_area_share": closed_area / max(total_area, 1),
            "neg_area": int(total_area)}


def sign_helper_check() -> dict:
    """burst_on() returns True where F is NEGATIVE, asserted on a synthetic bump."""
    rng = np.random.default_rng(11)
    bg, T, s_b, amp = 20.0, 200.0, 4.0, 200.0
    base = np.sort(rng.uniform(0, T, rng.poisson(bg * T)))
    bump = np.sort(rng.normal(T / 2, s_b, rng.poisson(amp * s_b * np.sqrt(2 * np.pi))))
    bump = bump[(bump > 0) & (bump < T)]
    ts = np.sort(np.concatenate([base, bump]))
    ev, x = ts[1:], np.log10(np.diff(ts))
    tg = np.linspace(20, T - 20, 4000)
    scales = np.geomspace(0.25, 64, 73)
    f = field(ts, ev, x, tg, scales)
    lam = bg + amp * np.exp(-0.5 * ((tg - T / 2) / s_b) ** 2)
    on, sstar, j = burst_on(f, scales, s_min_for_rate(lam), factor=2.0)
    inb = np.abs(tg - T / 2) < s_b
    Fv = f["dlograte"][np.arange(tg.size), np.clip(j, 0, None)]
    med = float(np.nanmedian(Fv[inb]))
    return {"F_in_bump_median": med,
            "on_share_in_bump": float(on[inb].mean()),
            "on_share_far_outside": float(on[np.abs(tg - T / 2) > 6 * s_b].mean()),
            "pass": bool(med < 0 and on[inb].mean() > 0.9)}


def gateA(cfg, events) -> dict:
    res = {"gate": "A",
           "zero_sum_exact_reference": zero_sum_exact(),
           "sign_helper": sign_helper_check(),
           "events": {}}
    for eid in events:
        t0 = time.perf_counter()
        d = event_field(eid, cfg)
        e = {"n_prints": int(d["n_prints"])}
        for k in KERNELS:
            zs = zero_sum_event(d, k)
            r = np.array([q["rel_residual"] for q in zs])
            nm = np.array([q["n_eff_median"] for q in zs])
            deep = np.abs(r[nm >= 32]) if (nm >= 32).any() else np.abs(r)
            e[k] = {"max_abs_rel": float(np.abs(r).max()),
                    "median_abs_rel": float(np.median(np.abs(r))),
                    "max_abs_rel_where_neff_ge_32": float(deep.max()),
                    "n_scales": len(zs)}
        e["blobs_centred"] = closed_bottom_blobs(d["Z_centred"].astype(np.float64))
        e["seconds"] = round(time.perf_counter() - t0, 1)
        res["events"][eid] = e
        print("  A", eid, "zs_max", round(e["centred"]["max_abs_rel"], 5),
              "closed_blobs", e["blobs_centred"]["n_closed_bottom"],
              "/", e["blobs_centred"]["n_blobs"], f"({e['seconds']}s)")
    return res


# --------------------------------------------------------------------------- #
# THE NOISE RULER -- Monte Carlo sampling error of F under a Poisson null
# --------------------------------------------------------------------------- #
#
# F = E_w[z^2] - 1 with w_i = exp(-z_i^2/2), z = (t - t_i)/s. Evaluated at t = 0 with
# s = 1: prints beyond |z| = 6 carry weight e^-18 = 1.5e-8 and are dropped. The
# statistic is scale-free in these units, so ONE (lambda, s) pair per n_eff is the
# whole story and no tape needs simulating.
#
# n_eff realised = (sum w)^2 / sum w^2, which is exactly what field()/field_exact()
# compute (2*sqrt(pi)*sg*c0^2/ch reduces to it algebraically). Cells below the floor
# come back NaN in the real field, so the mask-conditioned row is reported beside the
# unconditional one -- but the PRIMARY threshold is the unconditional table, because
# that is the one the brief pre-registers, and at low n_eff it is the HARDER of the
# two (2sd = 0.78 against 0.59). The easier one is never taken.

def mc_null(neff_target, kernel="centred", n_draw=400000, half=6.0, seed=0,
            chunk=20000):
    rng = np.random.default_rng(seed)
    coef = _neff_coef(kernel)
    lam = neff_target / coef                                  # s = 1
    lo, hi = (-half, half) if kernel == "centred" else (0.0, half)
    mu = lam * (hi - lo)
    # the (draws x prints) block is dense, so the chunk scales inversely with mu --
    # at n_eff = 512 a fixed 20,000-row chunk would allocate 288 MB per pass
    chunk = int(np.clip(4e6 / max(mu, 1.0), 200, chunk))
    F, NE, done = [], [], 0
    while done < n_draw:
        m = min(chunk, n_draw - done)
        done += m
        n = rng.poisson(mu, m)
        nmax = int(n.max()) if n.size else 0
        if nmax == 0:
            F.append(np.full(m, np.nan)); NE.append(np.zeros(m)); continue
        u = rng.uniform(lo, hi, (m, nmax))
        live = np.arange(nmax)[None, :] < n[:, None]
        z2 = u * u
        w = np.where(live, np.exp(-0.5 * z2), 0.0)
        B = w.sum(1)
        S2 = (w * w).sum(1)
        NE.append(np.divide(B * B, S2, out=np.zeros(m), where=S2 > 0))
        F.append(np.divide((w * z2).sum(1), B, out=np.full(m, np.nan), where=B > 0)
                 - 1.0)
    return np.concatenate(F), np.concatenate(NE)


def null_table(kernel="centred", n_draw=400000,
               grid=(3, 4, 6, 8, 10, 12, 16, 20, 26, 32, 45, 64, 90, 128, 256, 512)):
    rows = []
    for ne in grid:
        f, ner = mc_null(ne, kernel, n_draw=n_draw, seed=int(ne) * 7 + 1)
        for tag, sel in (("unconditional", np.isfinite(f)),
                         ("masked", np.isfinite(f) & (ner >= 8.0))):
            v = f[sel]
            if v.size < 500:
                continue
            sd = float(v.std(ddof=1))
            rows.append({"kernel": kernel, "n_eff": float(ne), "conditioning": tag,
                         "n": int(v.size), "keep_share": float(sel.mean()),
                         "sd": sd, "mean": float(v.mean()),
                         "skew": float(((v - v.mean()) ** 3).mean() / sd ** 3),
                         "p_neg": float((v < 0).mean()),
                         "p_lt_2sd": float((v < -2 * sd).mean()),
                         "asymptotic_0p87_over_sqrt_neff": 0.87 / np.sqrt(ne),
                         "min": float(v.min())})
    return rows


class NoiseRuler:
    """sd(F) and the null rate at any n_eff, log-log interpolated off the MC table.

    Interpolation is in log n_eff / log sd because sd ~ n_eff^-1/2 over most of the
    range; a linear interpolation of the same table would misstate sd by up to 4%
    between rungs. Outside the table it EXTRAPOLATES ON THE ASYMPTOTE, never flat.
    """

    def __init__(self, rows, kernel="centred", conditioning="unconditional"):
        r = [q for q in rows if q["kernel"] == kernel
             and q["conditioning"] == conditioning]
        r.sort(key=lambda q: q["n_eff"])
        self.ne = np.array([q["n_eff"] for q in r])
        self.sd = np.array([q["sd"] for q in r])
        self.pl = np.array([q["p_lt_2sd"] for q in r])
        self.pn = np.array([q["p_neg"] for q in r])

    def sd_at(self, neff):
        n = np.asarray(neff, float)
        out = np.exp(np.interp(np.log(np.clip(n, 1e-9, None)), np.log(self.ne),
                               np.log(self.sd)))
        hi = n > self.ne[-1]
        if np.any(hi):
            out = np.where(hi, self.sd[-1] * np.sqrt(self.ne[-1] / np.maximum(n, 1e-9)),
                           out)
        return out

    def p_lt_2sd_at(self, neff):
        n = np.asarray(neff, float)
        return np.interp(np.log(np.clip(n, 1e-9, None)), np.log(self.ne), self.pl)


def gateC(n_draw=400000) -> dict:
    """The null rate of the magnitude-thresholded mark, MEASURED not assumed.

    F is bounded below at -1 and strongly right-skewed at low n_eff, so the negative
    tail is far thinner than normal theory. The Gaussian two-sided-2sd rate is 0.0228;
    nothing on this grid comes close to it, and at n_eff = 8 it is 160x optimistic.
    """
    rows = null_table("centred", n_draw) + null_table("onesided", n_draw)
    brief = {4: 0.94, 8: 0.38, 12: 0.28, 20: 0.21, 32: 0.16, 64: 0.11, 128: 0.078}
    chk = []
    for ne, want in brief.items():
        got = [q for q in rows if q["kernel"] == "centred" and q["n_eff"] == ne
               and q["conditioning"] == "unconditional"]
        if got:
            chk.append({"n_eff": ne, "preregistered_sd": want,
                        "measured_sd": round(got[0]["sd"], 4),
                        "abs_diff": round(abs(got[0]["sd"] - want), 4)})
    return {"gate": "C", "rows": rows, "preregistered_table_check": chk,
            "gaussian_reference_p_lt_2sd": 0.02275,
            "pass": bool(chk and max(c["abs_diff"] for c in chk) < 0.01)}


# --------------------------------------------------------------------------- #
# GATE B -- the noise ruler applied to the tape
# --------------------------------------------------------------------------- #

def read_at(d, kernel, factor, debounce=True, cfg=None):
    """The mark at an arbitrary read factor, through burst_on() unchanged.

    burst_on and the debounce are the committed definitions; only `factor` moves.
    -> dict with the boolean, F at the read scale, s*, and n_eff at the read scale.
    """
    Z = d["Z_" + kernel].astype(np.float64)
    scales = d["scales"]
    smin = d["smin_" + kernel]
    on, sstar, j = burst_on({"dlograte": Z}, scales, smin, factor=factor)
    if debounce and cfg is not None:
        db = cfg["burst_marking"]["debounce"]
        on = ep.debounce_runs(on, d["t_grid"], sstar,
                              merge_factor=db["merge_gap_factor"],
                              min_factor=db["min_on_duration_factor"])
    ii = np.arange(Z.shape[0])
    F = np.where(j >= 0, Z[ii, np.clip(j, 0, None)], np.nan)
    neff = _neff_coef(kernel) * sstar * d["lam_" + kernel][:Z.shape[0]]
    return {"on": on, "F": F, "s_star": sstar, "n_eff": neff, "j": j}


def runs_from_bool(b):
    b = np.asarray(b, bool)
    if not b.any():
        return []
    e = np.flatnonzero(np.diff(np.concatenate([[0], b.view(np.int8), [0]])))
    return list(zip(e[0::2], e[1::2]))


def gateB(cfg, events, ruler, ruler_masked) -> dict:
    """B1: fraction of currently-marked TIME that survives F < -2*sd(n_eff).
       B2: the same against read_factor and against absolute scale.
       Plus the detection-versus-measurement test the brief asks be verified.
    """
    res = {"gate": "B", "events": {}, "structural": {}}

    # the structural arithmetic, computed rather than quoted
    res["structural"]["two_sd_at_read"] = {
        str(f): {"n_eff_at_read": 8.0 * f,
                 "two_sd": float(2 * ruler.sd_at(8.0 * f)),
                 "available_headroom_below_-1": float(1.0 - 2 * ruler.sd_at(8.0 * f)),
                 "two_sd_masked_conditioning": float(2 * ruler_masked.sd_at(8.0 * f))}
        for f in READ_FACTORS}
    res["structural"]["bump_depth_minus_s2_over_sig2_plus_s2"] = {
        "s_eq_sigma": -0.5, "s_eq_2sigma": -0.8, "s_eq_4sigma": -0.94}

    for eid in events:
        d = event_field(eid, cfg)
        date = eid.split("_")[1]
        segs = segment_masks(d["grid_ns"], date)
        dt = d["dt_eval"]
        n = d["Z_centred"].shape[0]
        e = {"n_prints": int(d["n_prints"]), "kernels": {}}
        for kernel in KERNELS:
            kd = {"read_factor": {}, "by_scale": {}}
            for f in READ_FACTORS:
                r = read_at(d, kernel, f, debounce=True, cfg=cfg)
                sd2 = 2 * ruler.sd_at(r["n_eff"][:n])
                sd2m = 2 * ruler_masked.sd_at(r["n_eff"][:n])
                surv = r["on"][:n] & np.isfinite(r["F"][:n]) & (r["F"][:n] < -sd2)
                survm = r["on"][:n] & np.isfinite(r["F"][:n]) & (r["F"][:n] < -sd2m)
                row = {"n_eff_at_read_median": float(np.nanmedian(r["n_eff"][:n]))}
                for sname, sm in list(segs.items()) + [("all", np.ones(n, bool))]:
                    m = sm[:n]
                    tot_on = float(np.nansum(dt[:n][r["on"][:n] & m]))
                    tot_def = float(np.nansum(dt[:n][np.isfinite(r["F"][:n]) & m]))
                    row[sname] = {
                        "marked_seconds": tot_on,
                        "defined_seconds": tot_def,
                        "marked_share_of_defined": tot_on / tot_def if tot_def > 0 else float("nan"),
                        "survivor_seconds": float(np.nansum(dt[:n][surv & m])),
                        "survival_share_of_marked":
                            float(np.nansum(dt[:n][surv & m]) / tot_on) if tot_on > 0 else float("nan"),
                        "survival_share_masked_ruler":
                            float(np.nansum(dt[:n][survm & m]) / tot_on) if tot_on > 0 else float("nan"),
                        "survivor_share_of_defined":
                            float(np.nansum(dt[:n][surv & m]) / tot_def) if tot_def > 0 else float("nan"),
                    }
                # detection vs measurement: depth, width, and the read scale
                dep, wid, sst = [], [], []
                for a, b in runs_from_bool(surv):
                    dep.append(float(np.nanmin(r["F"][a:b])))
                    wid.append(float(np.nansum(dt[a:b])))
                    sst.append(float(np.nanmedian(r["s_star"][a:b])))
                if len(dep) >= 8:
                    dep = np.array(dep); wid = np.array(wid); sst = np.array(sst)
                    ok = np.isfinite(dep) & np.isfinite(wid) & np.isfinite(sst) & (wid > 0) & (sst > 0)
                    lw, ls = np.log(wid[ok]), np.log(sst[ok])
                    row["surviving_runs"] = {
                        "n_runs": int(ok.sum()),
                        "corr_depth_vs_log_width": float(np.corrcoef(dep[ok], lw)[0, 1]),
                        "corr_log_width_vs_log_sstar": float(np.corrcoef(lw, ls)[0, 1]),
                        "slope_log_width_on_log_sstar":
                            float(np.polyfit(ls, lw, 1)[0]),
                        "median_width_over_sstar": float(np.median(wid[ok] / sst[ok])),
                        "median_depth": float(np.median(dep[ok])),
                    }
                else:
                    row["surviving_runs"] = {"n_runs": int(len(dep))}
                kd["read_factor"][str(f)] = row

            # B2 second half: survival against ABSOLUTE scale, whole pane
            Z = d["Z_" + kernel].astype(np.float64)
            lam = d["lam_" + kernel][:n]
            coef = _neff_coef(kernel)
            by = []
            for j, s in enumerate(d["scales"]):
                F = Z[:n, j]
                ne = coef * s * lam
                ok = np.isfinite(F) & np.isfinite(ne)
                if ok.sum() < 200:
                    continue
                thr = 2 * ruler.sd_at(ne[ok])
                w = dt[:n][ok]
                by.append({"s": float(s),
                           "n_eff_median": float(np.median(ne[ok])),
                           "defined_share": float(ok.mean()),
                           "neg_share": float(np.sum(w * (F[ok] < 0)) / w.sum()),
                           "survive_share": float(np.sum(w * (F[ok] < -thr)) / w.sum()),
                           "null_rate": float(ruler.p_lt_2sd_at(np.median(ne[ok])))})
            kd["by_scale"] = by
            e["kernels"][kernel] = kd
        res["events"][eid] = e
        c = e["kernels"]["centred"]["read_factor"]
        print("  B", eid, " survival of marked time, rf 1/2/3/4:",
              " ".join(f"{c[str(f)]['all']['survival_share_of_marked']:.3f}"
                       for f in READ_FACTORS))
    return res


# --------------------------------------------------------------------------- #
# GATE D -- independence from print count, dependent variable corrected
# --------------------------------------------------------------------------- #

def gateD_event(eid, cfg, ruler) -> dict | None:
    """One event, summary only -- the field is NOT cached here. 105 scales x 60k
    columns is 57 MB per event and a 50-event regression does not need it kept."""
    try:
        r = ep.compute_event(eid, cfg)
    except SystemExit:
        return None
    except Exception as ex:                        # a tape that will not load
        print("   skip", eid, type(ex).__name__, ex)
        return None
    date = eid.split("_")[1]
    segs = segment_masks(r["grid_ns"], date)
    dt = r["dt_eval"]
    out = {"event_id": eid, "n_prints": int(r["meta"]["n_prints"]), "kernels": {}}
    for kernel in KERNELS:
        kd = r["kernels"][kernel]
        Z = kd["Z"]
        n = Z.shape[0]
        smin = kd["s_min_t"]
        coef = _neff_coef(kernel)
        d = {"t_grid": r["t_grid"], "scales": r["scales"], "dt_eval": dt,
             "Z_" + kernel: Z, "lam_" + kernel: kd["lam"], "smin_" + kernel: smin,
             "grid_ns": r["grid_ns"]}
        kk = {}
        for f in READ_FACTORS:
            rd = read_at(d, kernel, f, debounce=True, cfg=cfg)
            sd2 = 2 * ruler.sd_at(rd["n_eff"][:n])
            surv = rd["on"][:n] & np.isfinite(rd["F"][:n]) & (rd["F"][:n] < -sd2)
            row = {}
            for sname, sm in list(segs.items()) + [("all", np.ones(n, bool))]:
                m = sm[:n]
                dfn = np.isfinite(rd["F"][:n]) & m
                tot_def = float(np.nansum(dt[:n][dfn]))
                tot_on = float(np.nansum(dt[:n][rd["on"][:n] & m]))
                tot_sv = float(np.nansum(dt[:n][surv & m]))
                # "marks per s_min of session": the count correction. The number of
                # INDEPENDENT reads along the path is ~ T/s_min, so a raw count has a
                # slope-1 dependence on print count built into the geometry. Dividing
                # by that count is the same correction the shaded fraction applies.
                nreads = float(np.nansum(dt[:n][dfn] / np.maximum(smin[:n][dfn], 1e-9)))
                row[sname] = {
                    "defined_seconds": tot_def,
                    "shaded_fraction": tot_on / tot_def if tot_def > 0 else float("nan"),
                    "survivor_fraction": tot_sv / tot_def if tot_def > 0 else float("nan"),
                    "n_runs_raw": len(runs_from_bool(rd["on"][:n] & m)),
                    "n_runs_survivor": len(runs_from_bool(surv & m)),
                    "reads_per_session": nreads,
                    "marks_per_s_min": (len(runs_from_bool(rd["on"][:n] & m)) / nreads
                                        if nreads > 0 else float("nan")),
                    "survivors_per_s_min": (len(runs_from_bool(surv & m)) / nreads
                                            if nreads > 0 else float("nan")),
                }
            kk[str(f)] = row
        out["kernels"][kernel] = kk
    return out


def ols(x, y):
    ok = np.isfinite(x) & np.isfinite(y)
    if ok.sum() < 4:
        return {"n": int(ok.sum())}
    x, y = x[ok], y[ok]
    b, a = np.polyfit(x, y, 1)
    yh = a + b * x
    ss = np.sum((y - yh) ** 2)
    st = np.sum((y - y.mean()) ** 2)
    r = float(np.corrcoef(x, y)[0, 1])
    se = float(np.sqrt(ss / (x.size - 2) / np.sum((x - x.mean()) ** 2)))
    return {"n": int(x.size), "slope": float(b), "intercept": float(a),
            "se_slope": se, "t": float(b / se) if se > 0 else float("nan"),
            "r": r, "r2": float(1 - ss / st) if st > 0 else float("nan")}


def gateD(rows, cfg) -> dict:
    res = {"gate": "D", "n_events": len(rows), "regressions": {},
           "underpowered_below_n": 40,
           "note": ("the raw-count regression is reported ONLY as the geometric "
                    "control the brief names -- reads along the path number ~T/s_min "
                    "which is proportional to the print count, so a slope near 1 "
                    "there is arithmetic and means nothing about the detector.")}
    lp = np.array([np.log(r["n_prints"]) for r in rows])
    for kernel in KERNELS:
        for f in READ_FACTORS:
            for sname in ("all", "rth", "premarket"):
                key = f"{kernel}|rf{f:g}|{sname}"
                g = lambda k: np.array([r["kernels"][kernel][str(f)][sname][k]
                                        for r in rows], float)
                res["regressions"][key] = {
                    "shaded_fraction_on_log_prints": ols(lp, g("shaded_fraction")),
                    "survivor_fraction_on_log_prints": ols(lp, g("survivor_fraction")),
                    "marks_per_s_min_on_log_prints": ols(lp, g("marks_per_s_min")),
                    "survivors_per_s_min_on_log_prints": ols(lp, g("survivors_per_s_min")),
                    "GEOMETRIC_CONTROL_log_raw_count_on_log_prints":
                        ols(lp, np.log(np.maximum(g("n_runs_raw"), 1))),
                    "median_shaded_fraction": float(np.nanmedian(g("shaded_fraction"))),
                    "median_survivor_fraction": float(np.nanmedian(g("survivor_fraction"))),
                }
    res["powered"] = len(rows) >= 40
    return res


# --------------------------------------------------------------------------- #
# GATE E -- split-half reliability against scale
# --------------------------------------------------------------------------- #

def thinning_invariance(seed=3) -> dict:
    """VERIFY THE PROPERTY THE TEST RESTS ON before trusting the test.

    F is invariant to lambda -> c*lambda: a constant inside a log is an additive
    offset and its scale-derivative is zero. Uniform thinning is that constant to
    first order; only n_eff changes, so only the NOISE LEVEL changes.
    """
    rng = np.random.default_rng(seed)
    T, lam = 400.0, 200.0
    ts = np.sort(rng.uniform(0, T, rng.poisson(lam * T)))
    # a deterministic rate excursion, so the field has real structure to preserve
    keep = rng.random(ts.size) < 0.3 + 0.6 * np.exp(-0.5 * ((ts - 200) / 20) ** 2)
    ts = ts[keep]
    ev, x = ts[1:], np.log10(np.diff(ts))
    tg = np.linspace(60, T - 60, 4000)
    sc = np.geomspace(0.5, 64, 29)
    full = field(ts, ev, x, tg, sc)["dlograte"]
    out = []
    for frac in (0.5, 0.25):
        sel = rng.random(ts.size) < frac
        t2 = ts[sel]
        e2, x2 = t2[1:], np.log10(np.diff(t2))
        h = field(t2, e2, x2, tg, sc)["dlograte"]
        for j, s in enumerate(sc):
            ok = np.isfinite(full[:, j]) & np.isfinite(h[:, j])
            if ok.sum() < 200:
                continue
            out.append({"thin_fraction": frac, "s": float(s),
                        "corr_with_full": float(np.corrcoef(full[ok, j], h[ok, j])[0, 1]),
                        "mean_full": float(full[ok, j].mean()),
                        "mean_thinned": float(h[ok, j].mean()),
                        "bias": float((h[ok, j] - full[ok, j]).mean())})
    return out


def gateE(cfg, events, n_draws=3, seed=101) -> dict:
    """Assign each print randomly to half A or half B. Compute the field independently
    on each. Correlate at each scale, ON A FIXED ABSOLUTE SCALE GRID -- letting each
    half pick its own read scale would compare two different quantities, because each
    half has lower lambda and therefore a higher s_min of its own.
    """
    from scale_field import collapse_same_timestamp, intervals, seconds_since
    sc = np.geomspace(0.25, 512.0, 4 * 11 + 1)          # 4/octave, fixed and absolute
    res = {"gate": "E", "scale_grid": [float(v) for v in sc],
           "thinning_invariance": thinning_invariance(), "events": {}}
    for eid in events:
        ts_ns, meta = adapter.load_event_prints_meta(eid, None)
        arr = collapse_same_timestamp(ts_ns)
        origin = int(arr[0])
        lo, hi = int(meta["window_start_ns"]), int(meta["window_end_ns"])
        edges, grid_ns, dt, k_eff = ep.column_grid(arr, lo, hi, 4.52, 12000)
        tg = (grid_ns - origin).astype(np.float64) / 1e9
        rng = np.random.default_rng(seed + abs(hash(eid)) % 10000)
        acc = {j: [] for j in range(sc.size)}
        nn = {j: [] for j in range(sc.size)}
        for draw in range(n_draws):
            half = rng.random(arr.size) < 0.5
            fields = []
            for sel in (half, ~half):
                a = arr[sel]
                if a.size < 500:
                    fields = []; break
                t_s = seconds_since(a, origin)
                e_s, x = intervals(a, origin=origin)
                fields.append(field(t_s, e_s, x, tg, sc)["dlograte"])
            if not fields:
                continue
            A, B = fields
            for j in range(sc.size):
                ok = np.isfinite(A[:, j]) & np.isfinite(B[:, j])
                if ok.sum() < 200:
                    continue
                a_, b_ = A[ok, j], B[ok, j]
                if a_.std() < 1e-12 or b_.std() < 1e-12:
                    continue
                acc[j].append(float(np.corrcoef(a_, b_)[0, 1]))
                nn[j].append(int(ok.sum()))
        rows = []
        for j, s in enumerate(sc):
            if not acc[j]:
                continue
            r = float(np.mean(acc[j]))
            rows.append({"s": float(s), "n_draws": len(acc[j]),
                         "r_halfhalf": r,
                         "r_spearman_brown": float(2 * r / (1 + r)) if r > -1 else float("nan"),
                         "n_cells_median": float(np.median(nn[j]))})
        res["events"][eid] = rows
        if rows:
            print("  E", eid, "r at 1/4/16/64s:",
                  " ".join(f"{q['r_halfhalf']:.2f}" for q in rows
                           if abs(np.log2(q["s"] / 1) % 2) < 1e-6 and q["s"] in (1.0, 4.0, 16.0, 64.0)))
    return res


# --------------------------------------------------------------------------- #
# GATE F -- is there a special row?
# --------------------------------------------------------------------------- #

def gateF(cfg, events) -> dict:
    """Same blob sizes relative to s, same depth distribution, no preferred row?

    If yes the process is scale-free, there is no characteristic burst duration, and
    no estimator work will produce one. v3's committed Allan knees -- 128 s regular
    hours, 16 s premarket -- are the PREDICTION: the scale axis should change
    character near them.
    """
    res = {"gate": "F", "allan_knee_prediction": {"rth": 128.0, "premarket": 16.0},
           "events": {}}
    for eid in events:
        d = event_field(eid, cfg)
        date = eid.split("_")[1]
        segs = segment_masks(d["grid_ns"], date)
        dt = d["dt_eval"]
        Z = d["Z_centred"].astype(np.float64)
        n = Z.shape[0]
        e = {}
        for sname in ("premarket", "rth"):
            m = segs[sname][:n]
            if m.sum() < 2000:
                continue
            rows = []
            for j, s in enumerate(d["scales"]):
                F = np.where(m, Z[:n, j], np.nan)
                ok = np.isfinite(F)
                if ok.sum() < 500:
                    continue
                neg = ok & (F < 0)
                widths = [float(np.nansum(dt[a:b])) for a, b in runs_from_bool(neg)]
                widths = [w for w in widths if w > 0]
                if len(widths) < 5:
                    continue
                depths = F[neg]
                rows.append({
                    "s": float(s),
                    "n_runs": len(widths),
                    "median_width_over_s": float(np.median(widths) / s),
                    "mean_width_over_s": float(np.mean(widths) / s),
                    "neg_time_share": float(np.nansum(dt[:n][neg]) / np.nansum(dt[:n][ok])),
                    "depth_median": float(np.median(depths)),
                    "depth_p01": float(np.quantile(depths, 0.01)),
                    "depth_min": float(depths.min()),
                    "F_sd": float(F[ok].std()),
                    "F_sd_over_null": float("nan"),
                })
            e[sname] = rows
        res["events"][eid] = e
    return res


# --------------------------------------------------------------------------- #
# main
# --------------------------------------------------------------------------- #

def load_rulers():
    """Gate C's measured table, reloaded. B and D read their thresholds off it, so
    the threshold is one artifact and never a second copy of the numbers."""
    with open(OUT / "gateC_null_rate.json", encoding="utf-8") as f:
        rows = json.load(f)["rows"]
    return (NoiseRuler(rows, "centred", "unconditional"),
            NoiseRuler(rows, "centred", "masked"),
            NoiseRuler(rows, "onesided", "unconditional"),
            NoiseRuler(rows, "onesided", "masked"))


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--gate", default="0")
    p.add_argument("--n-events", type=int, default=10)
    p.add_argument("--events-file", default=None,
                   help="CSV with an event_id column; overrides the panel cohort")
    p.add_argument("--draws", type=int, default=3)
    p.add_argument("--n-draw", type=int, default=400000)
    p.add_argument("--refresh", action="store_true")
    a = p.parse_args()
    cfg = ep.load_config()
    if a.events_file:
        events = list(pd.read_csv(a.events_file)["event_id"])[:a.n_events]
    else:
        events = list(cohort(a.n_events)["event_id"])

    if a.gate == "0":
        r = gate0()
        print(json.dumps(r, indent=2, default=float))
        jdump(r, "gate0_log_base.json")
    elif a.gate == "A":
        jdump(gateA(cfg, events), "gateA_correctness.json")
    elif a.gate == "C":
        r = gateC(a.n_draw)
        for c in r["preregistered_table_check"]:
            print("  C n_eff", c["n_eff"], "prereg", c["preregistered_sd"],
                  "measured", c["measured_sd"], "diff", c["abs_diff"])
        jdump(r, "gateC_null_rate.json")
    elif a.gate == "B":
        ru, rm, _, _ = load_rulers()
        jdump(gateB(cfg, events, ru, rm), "gateB_noise_ruler.json")
    elif a.gate == "D":
        ru, _, _, _ = load_rulers()
        rows, t0 = [], time.perf_counter()
        for i, eid in enumerate(events):
            r = gateD_event(eid, cfg, ru)
            if r:
                rows.append(r)
            print(f"   D {i+1}/{len(events)} {eid} n={len(rows)} "
                  f"{round(time.perf_counter()-t0)}s", flush=True)
        jdump({"per_event": rows}, "gateD_per_event.json")
        jdump(gateD(rows, cfg), "gateD_regression.json")
    elif a.gate == "E":
        jdump(gateE(cfg, events, n_draws=a.draws), "gateE_split_half.json")
    elif a.gate == "F":
        jdump(gateF(cfg, events), "gateF_special_row.json")
    else:
        raise SystemExit("unknown gate " + a.gate)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
