"""
Phase 10b T2 -- synthetic control harness. THE GATE.

Runs the SHARED T3/T4 pipeline (research/phase_10b/pipeline.py) end to end on four
simulated inputs with known answers, before any real event is touched by T3 or T4.
There is no separate control implementation -- a control that runs different code
tests nothing.

  C1  homogeneous Poisson             -> must look Poisson at every scale
  C2  inhomogeneous Poisson           -> must look Poisson at every scale
  C3  cluster process, k=6 over 10 us -> must NOT, and the departure must be at 10 us
  C4  two injected scales, 10 us + 60 s -> both must be visible and separated

Required outcomes (pre-registered; hard stop on any miss, do not tune to pass):
  C1,C2  T3 curve inside the 95% matched-null band on >= 90% of eligible rungs
         T4 no interior crossing
  C3     plateau height within +-25% of E[N^2]/E[N]; T3 and T4 crossings each
         within 1 rung of the injected 10 us
  C4     T3 shows both scales, separated; T4 recovers 60 s within 1 rung
  T2e    band coverage within [0.90, 0.99]

Usage: .venv/Scripts/python.exe research/phase_10b/t2_controls.py
"""
from __future__ import annotations

import json
import os
import sys
import time

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "phase_10"))
from v2_common import rel, write_json  # noqa: E402
sys.path.insert(0, HERE)
from pipeline import (allan_curve, grid_dx, heldout_intensity, quantize, rescale_ks,  # noqa: E402
                      simulate_cluster, simulate_homogeneous, simulate_inhomogeneous)
from t1_plateau import cfg_hash, load_cfg  # noqa: E402

OUT_J = "results/phase_10b/artifacts/t2_control_results.json"
OUT_P = "results/phase_10b/artifacts/t2_control_curves.parquet"
INJ_FINE, INJ_COARSE = 1e-5, 60.0     # the two injected scales


# --------------------------------------------------------------- shared rules
def nearest_rung(ladder: np.ndarray, T: float) -> int:
    return int(np.argmin(np.abs(np.log2(ladder) - np.log2(T))))


def crossing_rung(T: np.ndarray, val: np.ndarray, lo: np.ndarray, hi: np.ndarray,
                  eligible: np.ndarray) -> dict:
    """Lowest eligible rung at and above which the curve is OUTSIDE the band at
    every eligible rung. Shared by T2/T3 -- one definition, no per-control tuning."""
    idx = np.flatnonzero(eligible)
    if idx.size == 0:
        return {"crossing_T": None, "crossing_index": None, "reason": "no eligible rung"}
    outside = (val > hi) | (val < lo)
    best = None
    for j in range(idx.size):
        if outside[idx[j:]].all():
            best = idx[j]
            break
    if best is None:
        return {"crossing_T": None, "crossing_index": None,
                "reason": "curve never leaves the band and stays out"}
    return {"crossing_T": float(T[best]), "crossing_index": int(best),
            "side": "above" if val[best] > hi[best] else "below"}


def loglog_peaks(T: np.ndarray, val: np.ndarray, eligible: np.ndarray) -> list[dict]:
    """Interior local maxima of the log-log slope d log A / d log T -- one per
    injected timescale for a process with distinct clustering scales."""
    m = eligible & (val > 0)
    if m.sum() < 5:
        return []
    lt, lv = np.log2(T[m]), np.log(val[m])
    sl = np.gradient(lv, lt)
    out = []
    for i in range(1, sl.size - 1):
        if sl[i] > sl[i - 1] and sl[i] >= sl[i + 1] and sl[i] > 0:
            out.append({"T": float(T[m][i]), "slope": float(sl[i])})
    return sorted(out, key=lambda d: -d["slope"])


def matched_null_band(t_ctrl, start, end, h, ladder, min_pairs, n_draws, grid_dx,
                      rng, res_ns, pcts, cfg4, lam_grid=None):
    """95% band of Allan curves from an inhomogeneous Poisson null whose rate is
    lambda-hat at bandwidth h, fitted OUT OF SAMPLE (config circularity_note).

    Pass `lam_grid` to reuse an already-fitted (grid, lambda) so the coverage check
    is drawn against the same null the band was built from."""
    if lam_grid is None:
        grid, lam, floored = heldout_intensity(
            t_ctrl, start, end, h, cfg4["held_out"]["block_seconds"], grid_dx,
            cfg4["lambda_floor_frac"])
    else:
        grid, lam, floored = lam_grid
    draws = np.full((n_draws, len(ladder)), np.nan)
    for d in range(n_draws):
        td = simulate_inhomogeneous(lam, grid, rng, res_ns)
        for r in allan_curve(td, start, end, ladder, min_pairs):
            draws[d, nearest_rung(np.asarray(ladder), r["T"])] = r["allan"]
    lo = np.nanpercentile(draws, pcts[0], axis=0)
    hi = np.nanpercentile(draws, pcts[1], axis=0)
    return (grid, lam, floored), lo, hi, draws


def t4_share_curve(realizations, start, end, hs, cfg4, max_grid):
    """T4 on a set of realizations: share passing the rescaling KS at each h.

    The intensity floor is RELATIVE -- lambda_floor_frac times the realization's
    own mean rate -- per config t4_rescaling.lambda_floor_frac."""
    rows = []
    for h in hs:
        dx, grid_limited = grid_dx(h, cfg4["held_out"]["block_seconds"], end - start, max_grid)
        p, n, fl = 0, 0, []
        for t in realizations:
            floor_abs = cfg4["lambda_floor_frac"] * (t.size / (end - start))
            r = rescale_ks(t, start, end, h, cfg4["held_out"]["block_seconds"], floor_abs, dx)
            for f in r["folds"]:
                if f is None:
                    continue
                n += 1
                fl.append(f["floored_time_fraction"])
                p += int(f["ks_pvalue"] >= cfg4["ks_alpha"])
        fmean = float(np.mean(fl)) if fl else 1.0
        rows.append({"h": float(h), "n_folds": n, "pass_share": (p / n) if n else np.nan,
                     "floored_time_fraction_mean": fmean, "grid_dx": dx,
                     "grid_limited": bool(grid_limited),
                     "eligible": bool(n > 0 and not grid_limited
                                      and fmean <= cfg4["floored_time_max"])})
    return rows


def t4_crossing(rows, thresh) -> dict:
    el = [r for r in rows if r["eligible"]]
    if not el:
        return {"crossing_h": None, "reason": "no eligible bandwidth"}
    pas = [r["pass_share"] >= thresh for r in el]
    if all(pas):
        return {"crossing_h": None, "reason": "passes at every eligible h -- no interior crossing"}
    if not any(pas):
        return {"crossing_h": None, "reason": "fails at every eligible h -- no interior crossing"}
    for j in range(len(el)):
        if all(pas[j:]):
            return {"crossing_h": float(el[j]["h"]), "index": j,
                    "reason": "lowest h at and above which the pass share stays >= 0.5"}
    return {"crossing_h": None, "reason": "pass share never stabilizes above the threshold"}


# --------------------------------------------------------------- the controls
def build_controls(cfg, span, n_target, rng, res_ns):
    """C1-C4. Rate and duration are matched to the cohort's median rth event; the
    profile shape for C2/C4 is a synthetic post-trigger decay, so no real tick data
    enters the controls."""
    grid = np.arange(0.0, span + 0.25, 0.25)
    tp, tau = 0.02 * span, 0.06 * span
    shape = np.where(grid < tp, 0.15 + 0.85 * (grid / tp), 0.15 + 0.85 * np.exp(-(grid - tp) / tau))
    lam_c2 = shape * (n_target / float((shape * 0.25).sum()))

    c1 = simulate_homogeneous(n_target / span, 0.0, span, rng, res_ns)
    c2 = simulate_inhomogeneous(lam_c2, grid, rng, res_ns)
    k3 = 6
    bg3 = simulate_homogeneous(n_target / (k3 * span), 0.0, span, rng, res_ns)
    c3 = simulate_cluster(bg3, k3, INJ_FINE, rng, res_ns)
    # C4: fine sweeps of 6 over 10 us, superposed on coarse bursts of 20 over 60 s
    k4f, k4c = 6, 20
    bgf = simulate_inhomogeneous(lam_c2 * 0.5 / k4f, grid, rng)
    fine = simulate_cluster(bgf, k4f, INJ_FINE, rng)
    bgc = simulate_homogeneous(n_target * 0.5 / (k4c * span), 0.0, span, rng)
    coarse = simulate_cluster(bgc, k4c, INJ_COARSE, rng)
    c4 = np.sort(np.concatenate((fine, coarse)))
    c4 = quantize(c4, res_ns); c4.sort()
    return {"C1": c1, "C2": c2, "C3": c3, "C4": c4}, {"k3": k3, "k4_fine": k4f, "k4_coarse": k4c}


def expected_plateau(t, gap_s=INJ_FINE * 2):
    """E[N^2]/E[N] of the injected clusters, measured from the realization itself."""
    if t.size < 2:
        return float(t.size)
    sizes = np.diff(np.concatenate(([0], np.flatnonzero(np.diff(t) > gap_s) + 1, [t.size])))
    s = sizes.astype(float)
    return float((s ** 2).sum() / s.sum())


def main() -> int:
    cfg, chash = load_cfg(), cfg_hash()
    c2, c3, c4 = cfg["t2_controls"], cfg["t3_allan"], cfg["t4_rescaling"]
    ladder = np.array([2.0 ** e for e in range(c3["ladder_exponents"][0],
                                               c3["ladder_exponents"][1] + 1)])
    hs_band = [2.0 ** e for e in c3["null_band_h_subset_exponents"]]
    hs_t4 = [2.0 ** e for e in range(c4["bandwidth_exponents"][0],
                                     c4["bandwidth_exponents"][1] + 1)]
    min_pairs = c3["min_pairs_pooled"]
    pcts = c3["band_percentiles"]
    res_ns = float(c2["C1"]["quantization_ns"])
    max_grid = c4["max_grid_points"]
    span = float(c2["rth_span_s"])

    coh = pd.read_parquet(rel(cfg["cohort"]["manifest"]))
    n_target = float(np.median(coh["t0_print_count"]))
    rng = np.random.default_rng(c2["seed"])
    ctrls, kinfo = build_controls(cfg, span, n_target, rng, res_ns)

    t_start = time.perf_counter()
    results, curve_rows = {}, []
    for name, t in ctrls.items():
        cur = allan_curve(t, 0.0, span, ladder, min_pairs)
        by_T = {nearest_rung(ladder, r["T"]): r for r in cur}
        val = np.array([by_T[i]["allan"] if i in by_T else np.nan for i in range(len(ladder))])
        elig = np.array([by_T[i]["eligible"] if i in by_T else False for i in range(len(ladder))])

        inside_by_h, cross_by_h = {}, {}
        for h in hs_band:
            dx, _gl = grid_dx(h, c4["held_out"]["block_seconds"], span, max_grid)
            lam_grid = heldout_intensity(t, 0.0, span, h, c4["held_out"]["block_seconds"], dx,
                                         c4["lambda_floor_frac"])
            h_eligible = lam_grid[2] <= c4["floored_time_max"]
            lam_grid, lo, hi, draws = matched_null_band(
                t, 0.0, span, h, ladder, min_pairs, c2["n_control_draws"], dx,
                np.random.default_rng(c2["seed"] + 1), res_ns, pcts, c4, lam_grid)
            ok = elig & np.isfinite(val) & np.isfinite(lo) & np.isfinite(hi)
            inside = ok & (val >= lo) & (val <= hi)
            share = float(inside[ok].mean()) if ok.any() else np.nan
            # T2e coverage: FRESH draws from the SAME lambda-hat, independent of the
            # 200 that made the band
            _, _, _, fresh = matched_null_band(
                t, 0.0, span, h, ladder, min_pairs, c2["n_coverage_draws"], dx,
                np.random.default_rng(c2["seed"] + 99), res_ns, pcts, c4, lam_grid)
            cov = np.nanmean(((fresh >= lo) & (fresh <= hi))[:, ok]) if ok.any() else np.nan
            inside_by_h[f"h={h:g}"] = {"share_inside": share, "n_eligible": int(ok.sum()),
                                       "band_coverage": float(cov),
                                       "floored_time_fraction": float(lam_grid[2]),
                                       "h_eligible": bool(h_eligible)}
            cross_by_h[f"h={h:g}"] = dict(crossing_rung(ladder, val, lo, hi, ok),
                                          h_eligible=bool(h_eligible))
            for i in range(len(ladder)):
                curve_rows.append({"control": name, "h": h, "h_eligible": bool(h_eligible),
                                   "T": float(ladder[i]),
                                   "allan": float(val[i]) if np.isfinite(val[i]) else None,
                                   "band_lo": float(lo[i]) if np.isfinite(lo[i]) else None,
                                   "band_hi": float(hi[i]) if np.isfinite(hi[i]) else None,
                                   "eligible": bool(ok[i]), "inside": bool(inside[i])})

        # T4: pass-share curve over independent realizations of the same generator
        reals = [t] + [build_controls(cfg, span, n_target,
                                      np.random.default_rng(c2["seed"] + 1000 + d), res_ns)[0][name]
                       for d in range(c2["n_control_draws_t4"] - 1)]
        t4rows = t4_share_curve(reals, 0.0, span, hs_t4, c4, max_grid)

        eh = [h for h in hs_band if inside_by_h[f"h={h:g}"]["h_eligible"]]
        results[name] = {
            "n_prints": int(t.size),
            "eligible_bandwidths": eh,
            "share_inside_by_h": inside_by_h,
            "t3_crossing_by_h": cross_by_h,
            "t3_widest_h_crossing": cross_by_h[f"h={(max(eh) if eh else max(hs_band)):g}"],
            "loglog_slope_peaks": loglog_peaks(ladder, val, elig)[:3],
            "t4": {"rows": t4rows, "crossing": t4_crossing(t4rows, c4["ks_pass_share"])},
            "measured_expected_plateau": expected_plateau(t),
        }
        print(f"  {name}: n={t.size:,}  inside(widest h)="
              f"{inside_by_h[f'h={(max(eh) if eh else max(hs_band)):g}']['share_inside']:.3f}  "
              f"cross={results[name]['t3_widest_h_crossing'].get('crossing_T')}  "
              f"t4cross={results[name]['t4']['crossing'].get('crossing_h')} "
              f"({time.perf_counter()-t_start:.0f}s)", flush=True)

    # ------------------------------------------------------------ verdicts
    req = c2["required_numeric"]
    v = {}
    for name in ("C1", "C2"):
        r = results[name]
        shares = [d["share_inside"] for d in r["share_inside_by_h"].values() if d["h_eligible"]]
        v[name] = {
            "inside_band_min_share_over_h": float(np.nanmin(shares)),
            "inside_band_required": req["c1_c2_min_share_inside"],
            "pass_inside": bool(np.nanmin(shares) >= req["c1_c2_min_share_inside"]),
            "t4_crossing": r["t4"]["crossing"],
            "pass_t4_no_interior_crossing": bool(r["t4"]["crossing"]["crossing_h"] is None),
        }
        v[name]["pass"] = v[name]["pass_inside"] and v[name]["pass_t4_no_interior_crossing"]

    elig_hs = [h for h in hs_band
               if results["C1"]["share_inside_by_h"][f"h={h:g}"]["h_eligible"]]
    widest = max(elig_hs) if elig_hs else max(hs_band)
    r3 = results["C3"]
    lo_e, hi_e = cfg["t1_fragmentation"]["plateau_rungs_exponents"]
    pl = [row["allan"] for row in curve_rows
          if row["control"] == "C3" and row["h"] == max(hs_band) and row["allan"]
          and 2.0 ** lo_e <= row["T"] <= 2.0 ** hi_e]
    ph = float(np.exp(np.mean(np.log(pl)))) if pl else float("nan")
    exp_pl = r3["measured_expected_plateau"]
    inj_i = nearest_rung(ladder, INJ_FINE)
    c3x = r3["t3_widest_h_crossing"]
    v["C3"] = {
        "plateau_height": ph, "expected_size_weighted_mean": exp_pl,
        "relative_error": float(ph / exp_pl - 1.0) if exp_pl else None,
        "pass_plateau": bool(exp_pl and abs(ph / exp_pl - 1.0) <= req["c3_plateau_tolerance"]),
        "injected_scale_s": INJ_FINE, "injected_rung_index": inj_i,
        "t3_crossing": c3x,
        "pass_t3_crossing": bool(c3x["crossing_index"] is not None
                                 and abs(c3x["crossing_index"] - inj_i) <= req["c3_crossing_rung_tolerance"]),
        "t4_crossing": r3["t4"]["crossing"],
        "pass_t4_crossing": bool(r3["t4"]["crossing"]["crossing_h"] is not None
                                 and abs(np.log2(r3["t4"]["crossing"]["crossing_h"])
                                         - np.log2(INJ_FINE)) <= 1.0 + 1e-9),
    }
    v["C3"]["pass"] = all(v["C3"][k] for k in ("pass_plateau", "pass_t3_crossing", "pass_t4_crossing"))

    r4 = results["C4"]
    pk = r4["loglog_slope_peaks"]
    sep = (len(pk) >= 2 and max(pk[0]["T"], pk[1]["T"]) / min(pk[0]["T"], pk[1]["T"])
           >= req["c4_scale_separation_min_ratio"])
    t4c = r4["t4"]["crossing"]["crossing_h"]
    v["C4"] = {
        "loglog_slope_peaks": pk[:2],
        "separation_ratio": (max(pk[0]["T"], pk[1]["T"]) / min(pk[0]["T"], pk[1]["T"])
                             if len(pk) >= 2 else None),
        "pass_two_scales_separated": bool(sep),
        "operationalization": ("'both scales visible and separated' = at least two interior local "
                               "maxima of d log A / d log T, at rungs separated by a factor >= "
                               f"{req['c4_scale_separation_min_ratio']}"),
        "t4_crossing": r4["t4"]["crossing"], "injected_coarse_s": INJ_COARSE,
        "pass_t4_recovers_60s": bool(t4c is not None
                                     and abs(np.log2(t4c) - np.log2(INJ_COARSE)) <= 1.0 + 1e-9),
    }
    v["C4"]["pass"] = v["C4"]["pass_two_scales_separated"] and v["C4"]["pass_t4_recovers_60s"]

    covs = [d["band_coverage"] for r in results.values()
            for d in r["share_inside_by_h"].values() if d["h_eligible"]]
    lo_c, hi_c = req["t2e_coverage_range"]
    v["T2e_band_coverage"] = {
        "min": float(np.nanmin(covs)), "max": float(np.nanmax(covs)),
        "median": float(np.nanmedian(covs)), "required_range": [lo_c, hi_c],
        "n_checks": len(covs),
        "pass": bool(np.nanmin(covs) >= lo_c and np.nanmax(covs) <= hi_c),
    }
    v["ALL_PASS"] = all(v[k]["pass"] for k in ("C1", "C2", "C3", "C4", "T2e_band_coverage"))

    pd.DataFrame(curve_rows).to_parquet(rel(OUT_P), index=False)
    write_json(rel(OUT_J), {
        "phase": "10b", "task": "T2", "config_hash": chash,
        "gate": ("Hard stop on any required outcome not met. Do not proceed to T3. Do not adjust "
                 "the method to make a control pass -- post the control output and wait."),
        "shared_pipeline": "research/phase_10b/pipeline.py (T2, T3 and T4 all call it)",
        "controls": {"span_s": span, "n_target_prints": n_target,
                     "n_target_source": "median t0_print_count over the frozen 114-event cohort",
                     "profile_source": ("synthetic post-trigger decay, ramp to 2% of span then "
                                        "exponential with tau = 6% of span -- no real tick data "
                                        "enters any control"),
                     "timestamp_resolution_ns": res_ns, **kinfo,
                     "injected_scales_s": [INJ_FINE, INJ_COARSE]},
        "band_h_family": hs_band, "t4_h_family": hs_t4,
        "n_control_draws": c2["n_control_draws"], "n_coverage_draws": c2["n_coverage_draws"],
        "n_control_draws_t4": c2["n_control_draws_t4"],
        "results": results, "verdicts": v,
        "timing_seconds": round(time.perf_counter() - t_start, 1),
        "source": "research/phase_10b/t2_controls.py:main", "artifacts": [OUT_J, OUT_P],
    })

    print("\n--- T2 VERDICTS ---")
    for k in ("C1", "C2", "C3", "C4", "T2e_band_coverage"):
        print(f"  {k:20s} {'PASS' if v[k]['pass'] else 'FAIL'}")
    print(f"  {'GATE':20s} {'PASS -- proceed to T3' if v['ALL_PASS'] else 'FAIL -- HARD STOP'}")
    return 0 if v["ALL_PASS"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
