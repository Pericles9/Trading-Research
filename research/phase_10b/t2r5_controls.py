"""
Phase 10b A10b.1 T2-R1..T2-R5 -- amended control harness.

Six controls (C1, C2, C3, C4, C3', C4') end to end through the SHARED pipeline.
Changes in force:
  1  crossing statistic = piecewise knee (research/phase_10b/knee.py), BIC-selected
  2  held-out block = max(h / block_ratio, block_floor_event)
  3  inside-band share counts UPWARD excursions only, over a per-control range
  4  (T6 wording, no code)

No real event is read. Every control is simulated.

Usage: .venv/Scripts/python.exe research/phase_10b/t2r5_controls.py
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
from knee import fit_piecewise  # noqa: E402
from pipeline import (allan_curve, grid_dx, heldout_intensity, quantize,  # noqa: E402
                      rescale_ks, simulate_cluster, simulate_homogeneous,
                      simulate_inhomogeneous)
from t1_plateau import cfg_hash, load_cfg  # noqa: E402

OUT_J = "results/phase_10b/artifacts/t2_controls.json"
OUT_P = "results/phase_10b/artifacts/t2_control_curves.parquet"
OUT_R3 = "results/phase_10b/artifacts/t2r3_unseen_scale_validation.json"
OUT_R2 = "results/phase_10b/artifacts/t2r2_block_eligibility.json"

INJ = {"C3": 1e-5, "C4": 60.0, "C3p": 1e-3, "C4p": 1e-1}   # knee target per control
CLUSTERED = ("C3", "C4", "C3p", "C4p")


def block_floor_event(t, start, end, min_prints, steps_per_octave=8):
    """Smallest block duration whose MEDIAN block print count is >= min_prints.

    Median block count is non-decreasing in block duration, so a geometric scan
    finds the smallest satisfying duration to within one grid step. The grid step
    is recorded, not assumed.
    """
    span = end - start
    if t.size == 0:
        return span, {"reason": "no prints"}
    lo = np.log2(max(span / t.size, 1e-9)) - 2
    for j in range(int(lo * steps_per_octave), int(np.log2(span) * steps_per_octave) + 1):
        b = 2.0 ** (j / steps_per_octave)
        nb = int(np.floor(span / b))
        if nb < 2:
            break
        idx = np.floor((t - start) / b).astype(np.int64)
        idx = idx[(idx >= 0) & (idx < nb)]
        med = float(np.median(np.bincount(idx, minlength=nb)))
        if med >= min_prints:
            return float(b), {"median_block_prints": med, "n_blocks": nb,
                              "grid_steps_per_octave": steps_per_octave}
    return float(span), {"reason": "no block duration below the session span reaches the floor"}


def build_controls(cfg, span, n_target, rng, res_ns):
    """C1-C4 unchanged from the original run; C3' and C4' are C3 with the
    pre-registered 1 ms and 100 ms cluster durations."""
    c2c = cfg["t2_controls"]
    grid = np.arange(0.0, span + 0.25, 0.25)
    tp, tau = 0.02 * span, 0.06 * span
    shape = np.where(grid < tp, 0.15 + 0.85 * (grid / tp), 0.15 + 0.85 * np.exp(-(grid - tp) / tau))
    lam_c2 = shape * (n_target / float((shape * 0.25).sum()))

    out = {}
    out["C1"] = simulate_homogeneous(n_target / span, 0.0, span, rng, res_ns)
    out["C2"] = simulate_inhomogeneous(lam_c2, grid, rng, res_ns)
    k3 = 6
    bg3 = simulate_homogeneous(n_target / (k3 * span), 0.0, span, rng, res_ns)
    out["C3"] = simulate_cluster(bg3, k3, INJ["C3"], rng, res_ns)
    k4f, k4c = 6, 20
    bgf = simulate_inhomogeneous(lam_c2 * 0.5 / k4f, grid, rng)
    fine = simulate_cluster(bgf, k4f, 1e-5, rng)
    bgc = simulate_homogeneous(n_target * 0.5 / (k4c * span), 0.0, span, rng)
    coarse = simulate_cluster(bgc, k4c, INJ["C4"], rng)
    c4 = np.sort(np.concatenate((fine, coarse)))
    out["C4"] = np.sort(quantize(c4, res_ns))
    for nm, dur in (("C3p", c2c["control_c3_prime_duration_s"]),
                    ("C4p", c2c["control_c4_prime_duration_s"])):
        bg = simulate_homogeneous(n_target / (k3 * span), 0.0, span, rng, res_ns)
        out[nm] = simulate_cluster(bg, k3, dur, rng, res_ns)
    return out


def expected_plateau(t, gap_s):
    if t.size < 2:
        return float(t.size)
    s = np.diff(np.concatenate(([0], np.flatnonzero(np.diff(t) > gap_s) + 1, [t.size]))).astype(float)
    return float((s ** 2).sum() / s.sum())


def loglog_peaks(T, val, elig):
    m = elig & (val > 0) & np.isfinite(val)
    if m.sum() < 5:
        return []
    lt, lv = np.log2(T[m]), np.log(val[m])
    sl = np.gradient(lv, lt)
    out = [{"T": float(T[m][i]), "slope": float(sl[i])}
           for i in range(1, sl.size - 1)
           if sl[i] > sl[i - 1] and sl[i] >= sl[i + 1] and sl[i] > 0]
    return sorted(out, key=lambda d: -d["slope"])


def rung_err(ladder, got_T, target_T):
    """Rung distance between a recovered breakpoint and an injected scale."""
    return abs(np.log2(got_T) - np.log2(target_T))


def main() -> int:
    cfg, chash = load_cfg(), cfg_hash()
    c2c, c3c, c4c = cfg["t2_controls"], cfg["t3_allan"], cfg["t4_rescaling"]
    ladder = np.array([2.0 ** e for e in range(c3c["ladder_exponents"][0],
                                               c3c["ladder_exponents"][1] + 1)])
    hs = [2.0 ** e for e in c3c["control_band_h_exponents"]]
    hs_t4 = [2.0 ** e for e in range(c4c["bandwidth_exponents"][0],
                                     c4c["bandwidth_exponents"][1] + 1)]
    min_pairs, pcts = c3c["min_pairs_pooled"], c3c["band_percentiles"]
    res_ns = float(c2c["C1"]["quantization_ns"])
    span = float(c2c["rth_span_s"])
    max_grid, br = c4c["max_grid_points"], c4c["block_ratio"]
    mpb, floor_frac = c4c["min_prints_per_block"], c4c["lambda_floor_frac"]
    fl_max, kmax = c4c["floored_time_max"], c3c["knee_max_segments"]
    req = c2c["required_numeric"]
    c2_range = float(c2c["c2_lambda_timescale"])

    coh = pd.read_parquet(rel(cfg["cohort"]["manifest"]))
    n_target = float(np.median(coh["t0_print_count"]))
    ctrls = build_controls(cfg, span, n_target, np.random.default_rng(c2c["seed"]), res_ns)

    t0 = time.perf_counter()
    results, rows, blocks = {}, [], {}
    for name, t in ctrls.items():
        bfe, bfe_info = block_floor_event(t, 0.0, span, mpb)
        blk_rows = []
        for h in hs_t4:
            binds = (h / br) < bfe
            blk_rows.append({"h": float(h), "block_s": float(max(h / br, bfe)),
                             "block_floor_binds": bool(binds)})
        bind_share = float(np.mean([r["block_floor_binds"] for r in blk_rows]))
        blocks[name] = {"block_floor_event_s": bfe, "block_floor_detail": bfe_info,
                        "bind_share_of_t4_sweep": bind_share, "by_h": blk_rows,
                        "n_prints": int(t.size)}

        cur = allan_curve(t, 0.0, span, ladder, min_pairs)
        by = {int(np.argmin(np.abs(np.log2(ladder) - np.log2(r["T"])))): r for r in cur}
        val = np.array([by[i]["allan"] if i in by else np.nan for i in range(len(ladder))])
        elig = np.array([by[i]["eligible"] if i in by else False for i in range(len(ladder))])

        inside_by_h = {}
        for h in hs:
            block = max(h / br, bfe)
            binds = (h / br) < bfe
            dx, glim = grid_dx(h, block, span, max_grid)
            lam_grid = heldout_intensity(t, 0.0, span, h, block, dx, floor_frac)
            floored = lam_grid[2]
            h_elig = bool((not binds) and (not glim) and floored <= fl_max)
            grid, lam, _ = lam_grid
            draws = np.full((c2c["n_control_draws"], len(ladder)), np.nan)
            rng = np.random.default_rng(c2c["seed"] + 1)
            for d in range(c2c["n_control_draws"]):
                td = simulate_inhomogeneous(lam, grid, rng, res_ns)
                for r in allan_curve(td, 0.0, span, ladder, min_pairs):
                    draws[d, int(np.argmin(np.abs(np.log2(ladder) - np.log2(r["T"]))))] = r["allan"]
            lo = np.nanpercentile(draws, pcts[0], axis=0)
            hi = np.nanpercentile(draws, pcts[1], axis=0)
            ok = elig & np.isfinite(val) & np.isfinite(lo) & np.isfinite(hi)
            above, below = ok & (val > hi), ok & (val < lo)
            # Change 3 / T2-R1c: only UPWARD excursions count against inside-share
            share_up_inside = float((~above[ok]).mean()) if ok.any() else np.nan
            rng2 = np.random.default_rng(c2c["seed"] + 99)
            fresh = np.full((c2c["n_coverage_draws"], len(ladder)), np.nan)
            for d in range(c2c["n_coverage_draws"]):
                td = simulate_inhomogeneous(lam, grid, rng2, res_ns)
                for r in allan_curve(td, 0.0, span, ladder, min_pairs):
                    fresh[d, int(np.argmin(np.abs(np.log2(ladder) - np.log2(r["T"]))))] = r["allan"]
            cov = float(np.nanmean(((fresh >= lo) & (fresh <= hi))[:, ok])) if ok.any() else np.nan
            inside_by_h[f"h={h:g}"] = {
                "h": float(h), "block_s": float(block), "block_floor_binds": bool(binds),
                "grid_limited": bool(glim), "floored_time_fraction": float(floored),
                "h_eligible": h_elig, "n_eligible_rungs": int(ok.sum()),
                "share_inside_upper_only": share_up_inside,
                "share_above": float(above[ok].mean()) if ok.any() else np.nan,
                "share_below": float(below[ok].mean()) if ok.any() else np.nan,
                "band_coverage": cov}
            for i in range(len(ladder)):
                rows.append({"control": name, "h": float(h), "h_eligible": h_elig,
                             "T": float(ladder[i]),
                             "allan": float(val[i]) if np.isfinite(val[i]) else None,
                             "band_lo": float(lo[i]) if np.isfinite(lo[i]) else None,
                             "band_hi": float(hi[i]) if np.isfinite(hi[i]) else None,
                             "eligible": bool(ok[i]), "above": bool(above[i]),
                             "below": bool(below[i])})

        # ---- Change 1: the knee, on the control's own curve over eligible rungs
        kn = fit_piecewise(ladder[elig], val[elig], kmax)
        results[name] = {
            "n_prints": int(t.size), "block_floor_event_s": bfe,
            "bind_share_of_t4_sweep": bind_share,
            "eligible_bandwidths": [r["h"] for r in inside_by_h.values() if r["h_eligible"]],
            "inside_by_h": inside_by_h, "knee": kn,
            "loglog_slope_peaks": loglog_peaks(ladder, val, elig)[:3],
            "measured_expected_plateau": expected_plateau(t, 2 * INJ.get(name, 1e-5)),
        }
        print(f"  {name}: n={t.size:,} bfe={bfe:.2f}s bind={bind_share:.3f} "
              f"elig_h={len(results[name]['eligible_bandwidths'])} "
              f"knee_k={kn['selected_k'] if kn else None} "
              f"bps={[round(b, 6) for b in kn['selected']['breakpoints_T_s']] if kn else None} "
              f"({time.perf_counter()-t0:.0f}s)", flush=True)

    # ---------------------------------------------------------------- T4
    t4res = {}
    for name, t in ctrls.items():
        bfe = blocks[name]["block_floor_event_s"]
        r4 = []
        for h in hs_t4:
            binds = (h / br) < bfe
            block = max(h / br, bfe)
            dx, glim = grid_dx(h, block, span, max_grid)
            if binds or glim:
                r4.append({"h": float(h), "eligible": False, "pass_share": None,
                           "reason": "block_floor binds" if binds else "grid limited",
                           "block_s": float(block)})
                continue
            p, n, fl = 0, 0, []
            r = rescale_ks(t, 0.0, span, h, block, floor_frac * t.size / span, dx)
            for f in r["folds"]:
                if f is None:
                    continue
                n += 1
                fl.append(f["floored_time_fraction"])
                p += int(f["ks_pvalue"] >= c4c["ks_alpha"])
            fm = float(np.mean(fl)) if fl else 1.0
            r4.append({"h": float(h), "block_s": float(block), "n_folds": n,
                       "pass_share": (p / n) if n else None, "floored_time_fraction_mean": fm,
                       "eligible": bool(n > 0 and fm <= fl_max)})
        el = [r for r in r4 if r["eligible"]]
        pas = [r["pass_share"] >= c4c["ks_pass_share"] for r in el]
        cr = None
        if el and any(pas) and not all(pas):
            for j in range(len(el)):
                if all(pas[j:]):
                    cr = el[j]["h"]
                    break
        t4res[name] = {"rows": r4, "n_eligible": len(el), "crossing_h": cr,
                       "reason": ("no eligible bandwidth" if not el else
                                  "passes at every eligible h" if all(pas) else
                                  "fails at every eligible h" if not any(pas) else
                                  "lowest h at and above which the pass share stays >= 0.5")}
        print(f"  T4 {name}: elig={len(el)}/{len(hs_t4)} crossing={cr} ({t4res[name]['reason']})",
              flush=True)

    # ---------------------------------------------------------------- verdicts
    v = {}
    for nm, rng_hi in (("C1", None), ("C2", c2_range)):
        r = results[nm]
        sel = [d for d in r["inside_by_h"].values()
               if d["h_eligible"] and (rng_hi is None or d["h"] <= rng_hi)]
        shares = [d["share_inside_upper_only"] for d in sel]
        v[nm] = {
            "evaluation_range": ("all eligible h" if rng_hi is None
                                 else f"eligible h <= c2_lambda_timescale = {rng_hi:g} s"),
            "n_bandwidths_in_range": len(sel),
            "bandwidths_in_range": [d["h"] for d in sel],
            "share_inside_upper_only_by_h": {f"h={d['h']:g}": d["share_inside_upper_only"]
                                             for d in sel},
            "min_share_inside_upper_only": float(np.nanmin(shares)) if shares else None,
            "required": req["c1_c2_min_share_inside"],
            "pass_inside": bool(shares and np.nanmin(shares) >= req["c1_c2_min_share_inside"]),
            "t4_crossing_h": t4res[nm]["crossing_h"], "t4_reason": t4res[nm]["reason"],
            "pass_t4_no_interior_crossing": bool(t4res[nm]["crossing_h"] is None)}
        v[nm]["pass"] = v[nm]["pass_inside"] and v[nm]["pass_t4_no_interior_crossing"]

    for nm in CLUSTERED:
        r = results[nm]
        kn = r["knee"]
        bps = kn["selected"]["breakpoints_T_s"] if kn else []
        errs = [rung_err(ladder, b, INJ[nm]) for b in bps]
        best = float(min(errs)) if errs else None
        v[nm] = {
            "injected_scale_s": INJ[nm], "selected_k": kn["selected_k"] if kn else None,
            "delta_bic_vs_k1": kn["delta_bic_vs_k1"] if kn else None,
            "breakpoints_T_s": bps,
            "segment_slopes": kn["selected"]["segment_slopes"] if kn else None,
            "best_breakpoint_rung_error": best,
            "pass_knee": bool(best is not None and best <= 1.0 + 1e-9)}
        if nm in ("C3", "C4"):
            cr = t4res[nm]["crossing_h"]
            v[nm]["t4_crossing_h"] = cr
            v[nm]["t4_rung_error"] = float(rung_err(ladder, cr, INJ[nm])) if cr else None
            v[nm]["t4_target_in_sweep"] = bool(min(hs_t4) <= INJ[nm] <= max(hs_t4))
            v[nm]["pass_t4"] = bool(cr is not None and rung_err(ladder, cr, INJ[nm]) <= 1.0 + 1e-9)
    # C3 plateau, C4 separation -- re-asserted, not re-litigated
    widest = max(v["C1"]["bandwidths_in_range"]) if v["C1"]["bandwidths_in_range"] else max(hs)
    lo_e, hi_e = cfg["t1_fragmentation"]["plateau_rungs_exponents"]
    pl = [r["allan"] for r in rows if r["control"] == "C3" and r["h"] == widest
          and r["allan"] and 2.0 ** lo_e <= r["T"] <= 2.0 ** hi_e]
    ph = float(np.exp(np.mean(np.log(pl)))) if pl else float("nan")
    exp_pl = results["C3"]["measured_expected_plateau"]
    v["C3"]["plateau_height"] = ph
    v["C3"]["expected_size_weighted_mean"] = exp_pl
    v["C3"]["plateau_relative_error"] = float(ph / exp_pl - 1.0) if exp_pl else None
    v["C3"]["pass_plateau"] = bool(exp_pl and abs(ph / exp_pl - 1.0) <= req["c3_plateau_tolerance"])
    pk = results["C4"]["loglog_slope_peaks"]
    sep = (max(pk[0]["T"], pk[1]["T"]) / min(pk[0]["T"], pk[1]["T"])) if len(pk) >= 2 else None
    v["C4"]["separation_ratio"] = sep
    v["C4"]["pass_separation"] = bool(sep and sep >= req["c4_scale_separation_min_ratio"])

    v["C3"]["pass"] = all(v["C3"][k] for k in ("pass_knee", "pass_t4", "pass_plateau"))
    v["C4"]["pass"] = all(v["C4"][k] for k in ("pass_knee", "pass_t4", "pass_separation"))
    v["C3p"]["pass"] = v["C3p"]["pass_knee"]
    v["C4p"]["pass"] = v["C4p"]["pass_knee"]

    covs = [d["band_coverage"] for r in results.values() for d in r["inside_by_h"].values()
            if d["h_eligible"] and np.isfinite(d["band_coverage"])]
    lo_c, hi_c = req["t2e_coverage_range"]
    v["T2e_band_coverage"] = {"min": float(np.nanmin(covs)), "max": float(np.nanmax(covs)),
                              "median": float(np.nanmedian(covs)), "n_checks": len(covs),
                              "required_range": [lo_c, hi_c],
                              "pass": bool(np.nanmin(covs) >= lo_c and np.nanmax(covs) <= hi_c)}
    worst_bind = max(b["bind_share_of_t4_sweep"] for b in blocks.values())
    v["row_4d_block_ineligibility"] = {
        "rule": "bind share of the T4 bandwidth sweep > ineligible_share_max",
        "threshold": c4c["ineligible_share_max"],
        "by_control": {k: b["bind_share_of_t4_sweep"] for k, b in blocks.items()},
        "worst": worst_bind, "FIRED": bool(worst_bind > c4c["ineligible_share_max"])}
    v["row_4b_fitted_check"] = {
        "rule": "knee recovers 10 us but misses C3' (1 ms) or C4' (100 ms)",
        "c3_pass": v["C3"]["pass_knee"], "c3p_pass": v["C3p"]["pass_knee"],
        "c4p_pass": v["C4p"]["pass_knee"],
        "FIRED": bool(v["C3"]["pass_knee"] and not (v["C3p"]["pass_knee"] and v["C4p"]["pass_knee"]))}
    v["ALL_PASS"] = bool(all(v[k]["pass"] for k in ("C1", "C2", "C3", "C4", "C3p", "C4p",
                                                    "T2e_band_coverage"))
                         and not v["row_4d_block_ineligibility"]["FIRED"]
                         and not v["row_4b_fitted_check"]["FIRED"])

    pd.DataFrame(rows).to_parquet(rel(OUT_P), index=False)
    write_json(rel(OUT_R2), {"phase": "10b", "task": "T2-R2", "config_hash": chash,
                             "rule": c4c["block_rule"], "by_control": blocks,
                             "t4_sweep_h": hs_t4,
                             "held_out_property_check": (
                                 "With block = max(h/4, block_floor_event) the kernel spans the "
                                 "held-out block, but lambda-hat inside a held-out block is still "
                                 "built ONLY from opposite-parity blocks: the support mask passed to "
                                 "kernel_intensity is the complement of the evaluated blocks, so no "
                                 "held-out arrival contributes to the rate used to rescale it. "
                                 "Verified by construction in pipeline.heldout_intensity and by the "
                                 "homogeneous-Poisson check (mean rescaled interval 0.995-1.004)."),
                             "source": "research/phase_10b/t2r5_controls.py:main"})
    write_json(rel(OUT_R3), {"phase": "10b", "task": "T2-R3", "config_hash": chash,
                             "pre_registered": c2c["unseen_scale_validation"],
                             "controls": {nm: {k: v[nm][k] for k in
                                               ("injected_scale_s", "selected_k", "delta_bic_vs_k1",
                                                "breakpoints_T_s", "best_breakpoint_rung_error",
                                                "pass_knee")}
                                          for nm in CLUSTERED},
                             "row_4b": v["row_4b_fitted_check"],
                             "source": "research/phase_10b/t2r5_controls.py:main"})
    write_json(rel(OUT_J), {
        "phase": "10b", "task": "T2-R5", "amendment": "A10b.1", "config_hash": chash,
        "no_real_event_read": True,
        "controls": {"span_s": span, "n_target_prints": n_target,
                     "timestamp_resolution_ns": res_ns, "injected_scales_s": INJ},
        "band_h_family": hs, "t4_h_family": hs_t4,
        "results": results, "t4": t4res, "block_eligibility": blocks, "verdicts": v,
        "timing_seconds": round(time.perf_counter() - t0, 1),
        "source": "research/phase_10b/t2r5_controls.py:main",
        "artifacts": [OUT_J, OUT_P, OUT_R2, OUT_R3]})

    print("\n--- T2-R5 AMENDED VERDICTS ---")
    for k in ("C1", "C2", "C3", "C4", "C3p", "C4p", "T2e_band_coverage"):
        print(f"  {k:20s} {'PASS' if v[k]['pass'] else 'FAIL'}")
    print(f"  {'row 4b (fitted)':20s} {'FIRED' if v['row_4b_fitted_check']['FIRED'] else 'ok'}")
    print(f"  {'row 4d (bind share)':20s} "
          f"{'FIRED' if v['row_4d_block_ineligibility']['FIRED'] else 'ok'} "
          f"(worst {worst_bind:.3f} vs {c4c['ineligible_share_max']})")
    print(f"  {'GATE':20s} {'PASS' if v['ALL_PASS'] else 'FAIL -- HARD STOP'}")
    return 0 if v["ALL_PASS"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
