#!/usr/bin/env python
"""What is the excess variance made of -- clustering, or the rate path?

excess_variance.py measures observed sd(F) against the estimator's own sampling-noise
sd and finds a ratio of 2.3-3.0 at every scale, rising to 27x at the coarse end. That
says the field is not sampling noise. It does NOT say what the field is responding to.

THE CONTROL. Build an inhomogeneous Poisson surrogate whose intensity is the real
tape's rate path smoothed at bandwidth `bw`, and run the identical measurement on it.
The surrogate has, by construction:

    * the SAME rate excursions above bw -- same diurnal shape, same open, same anchor
    * NO clustering at all, at any scale -- it is Poisson given its own intensity

so the comparison splits the excess in two along the bandwidth:

    s << bw : surrogate ratio ~ 1  =>  any real-tape excess there is clustering
    s >> bw : surrogate ratio ~ real =>  the excess there is the rate path

THIS IS NOT A GATE and it settles nothing about clumping on its own. The rate channel
provably cannot separate clumping from a smooth rate excursion at constant mean rate
(brief s11): two tapes with identical lambda-hat(t), one Poisson and one violently
clustered, give identical fields. What this control CAN do is stop the headline
number being read as evidence of clumping when a rate path would produce it.

Thinning from the running maximum, so the realisation is exact rather than binned.
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np
from scipy.ndimage import gaussian_filter1d

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(REPO_ROOT, "research", "phase_10d_diag1"))

import adapter                                                     # noqa: E402
import event_panels as ep                                          # noqa: E402
from scale_field import (_neff_coef, collapse_same_timestamp, field,  # noqa: E402
                         intervals, s_min_for_rate, seconds_since)
from t1_lead_time import knn_rate                                  # noqa: E402

ART = os.path.join(REPO_ROOT, "results", "scale_field", "artifacts",
                   "instrument_gates")
BW_S = 30.0


def surrogate(ts_ns, lo_ns, hi_ns, seed, bw_s=BW_S, dt=0.5):
    rng = np.random.default_rng(seed)
    T = (hi_ns - lo_ns) / 1e9
    n = int(T / dt) + 1
    c = np.bincount(np.clip(((ts_ns - lo_ns) / 1e9 / dt).astype(np.int64), 0, n - 1),
                    minlength=n).astype(float)
    lam = gaussian_filter1d(c, bw_s / dt, mode="nearest") / dt
    lmax = float(lam.max())
    if lmax <= 0:
        return np.array([], dtype=np.int64)
    m = rng.poisson(lmax * T)
    u = np.sort(rng.uniform(0, T, m))
    keep = rng.random(m) < np.interp(u, (np.arange(n) + 0.5) * dt, lam) / lmax
    return (lo_ns + u[keep] * 1e9).astype(np.int64)


def measure(arr, lo, hi, cfg, sd_at, coef, scales):
    """The excess-variance curve, RTH only, on whatever tape it is handed."""
    origin = int(arr[0])
    ts_s = seconds_since(arr, origin)
    ev_s, x = intervals(arr, origin=origin)
    edges, grid_ns, dt_e, _ = ep.column_grid(arr, lo, hi, 1.13, 40000)
    tg = (grid_ns - origin).astype(np.float64) / 1e9
    Z = np.full((tg.size, scales.size), np.nan)
    for g in cfg["scale_ladder"]["groups"]:
        sc = scales[(scales >= g["min_seconds"] - 1e-12)
                    & (scales <= g["max_seconds"] + 1e-12)]
        if not sc.size:
            continue
        f = field(ts_s, ev_s, x, tg, sc, neff_min=8.0, sigma_lo=8.0, edge_scales=4.0)
        for c_, jj in enumerate(np.searchsorted(scales, sc)):
            Z[:, jj] = np.where(np.isnan(Z[:, jj]), f["dlograte"][:, c_], Z[:, jj])
    lam = knn_rate(arr, grid_ns, k=20, causal=False)
    return Z, lam, dt_e, grid_ns


def main() -> int:
    cfg = ep.load_config()
    with open(os.path.join(ART, "gateC_null_rate.json"), encoding="utf-8") as f:
        rows = json.load(f)["rows"]
    tab = {q["n_eff"]: q["sd"] for q in rows
           if q["kernel"] == "centred" and q["conditioning"] == "unconditional"}
    ks = np.array(sorted(tab))
    lsd = np.log([tab[k] for k in ks])

    def sd_at(ne):
        ne = np.asarray(ne, float)
        v = np.exp(np.interp(np.log(np.clip(ne, 1e-9, None)), np.log(ks), lsd))
        return np.where(ne > ks[-1],
                        tab[ks[-1]] * np.sqrt(ks[-1] / np.maximum(ne, 1e-9)), v)

    scales = ep.ladder(cfg)
    coef = _neff_coef("centred")
    eids = sys.argv[1:] or ["JFIN_2020-06-15_60.44", "POLA_2021-01-22_55.92"]
    out = {"bandwidth_s": BW_S, "note": __doc__, "events": {}}

    for eid in eids:
        ts_ns, meta = adapter.load_event_prints_meta(eid, None)
        arr = collapse_same_timestamp(ts_ns)
        b = adapter.segment_bounds_ns(eid.split("_")[1])
        lo, hi = b["rth"]
        real = arr[(arr >= lo) & (arr < hi)]
        sur = collapse_same_timestamp(surrogate(real, lo, hi, seed=17))
        print(f"{eid}: real {real.size:,} prints, surrogate {sur.size:,}")
        e = {}
        for tag, tape in (("real", real), ("surrogate", sur)):
            Z, lam, dt_e, gns = measure(tape, lo, hi, cfg, sd_at, coef, scales)
            n = Z.shape[0]
            res = []
            for j, s in enumerate(scales):
                F = Z[:n, j]
                ok = np.isfinite(F) & np.isfinite(lam[:n])
                if ok.sum() < 500:
                    continue
                ne = coef * s * lam[:n][ok]
                w = dt_e[:n][ok]
                w = w / w.sum()
                mu = float((w * F[ok]).sum())
                obs = float(np.sqrt((w * (F[ok] - mu) ** 2).sum()))
                nul = float(np.sqrt((w * sd_at(ne) ** 2).sum()))
                res.append({"s": float(s), "sd_observed": obs, "sd_null": nul,
                            "ratio": obs / nul if nul > 0 else float("nan"),
                            "n_cells": int(ok.sum()),
                            "n_eff_median": float(np.median(ne))})
            e[tag] = res
        out["events"][eid] = e
        print(f"{'s':>9s} {'real ratio':>11s} {'surr ratio':>11s} {'real/surr':>10s}")
        rr = {round(q["s"], 4): q for q in e["real"]}
        sr = {round(q["s"], 4): q for q in e["surrogate"]}
        for s in sorted(set(rr) & set(sr)):
            if abs(np.log2(s) % 1) > 1e-6 and s != 0.25:
                continue
            print(f"{s:9.3f} {rr[s]['ratio']:11.2f} {sr[s]['ratio']:11.2f} "
                  f"{rr[s]['ratio']/sr[s]['ratio']:10.2f}")
        print()

    with open(os.path.join(ART, "surrogate_control.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, default=float)
    print("wrote", os.path.join(ART, "surrogate_control.json"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
