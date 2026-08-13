"""
Phase 10b A10b.2 A2-T1 / A2-T2 -- the knee's sampling distribution, and the
pre-registered usability decision point.

Refits the knee independently on n_knee_draws fresh realizations of each
clustered control, then asks whether the per-control biases are one bias.

Uses no envelope test. Reads no real event -- every input is simulated.

A2-T2d is a HARD STOP BY DESIGN (escalation row 4): post and wait whatever the
outcome.

Usage: .venv/Scripts/python.exe research/phase_10b/a2_t1_t2_knee.py
"""
from __future__ import annotations

import json
import os
import sys
import time

import numpy as np
import pandas as pd
from scipy import stats as sps

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "phase_10"))
from v2_common import rel, write_json  # noqa: E402
sys.path.insert(0, HERE)
from knee import _design, fit_piecewise  # noqa: E402
from pipeline import allan_curve  # noqa: E402
from t1_plateau import cfg_hash, load_cfg  # noqa: E402
from t2r5_controls import INJ, build_controls  # noqa: E402

A2 = "results/phase_10b/amendment_2"
CTRLS = ("C3", "C4", "C3p", "C4p")
SINGLE, MULTI = ("C3", "C3p"), ("C4", "C4p")


# Which transition physically corresponds to each control's injected scale.
# Fixed by the shape of the process, NOT by the observed answer:
#   a single-scale cluster control rises off 1 and reaches its plateau  -> rise->flat
#   C4's COARSE component sits above the fine plateau and lifts off it  -> flat->rise
POSITION_RULE = {"C3": "onset", "C3p": "onset", "C4p": "onset", "C4": "offset"}


def plateau_transition(sel, kind):
    """Position rule fixed independently of the injected value.

    kind='onset'  -> the breakpoint that ENDS a rising segment and begins a flat one
                     (where the Allan curve reaches its plateau)
    kind='offset' -> the breakpoint that ENDS a flat segment and begins a rising one
                     (where the curve lifts off a plateau)

    Reported alongside nearest-to-injected because 'nearest' selects on the answer
    and its coverage is optimistically biased by construction.
    """
    bps, sl = sel["breakpoints_T_s"], sel["segment_slopes"]
    best, bi = None, None
    for j, b in enumerate(bps):
        before, after = sl[j], sl[j + 1]
        if kind == "onset":
            ok = before > 0.05 and abs(after) < abs(before) / 2
            score = abs(after)
        else:
            ok = after > 0.05 and abs(before) < abs(after) / 2
            score = abs(before)
        if ok and (best is None or score < best):
            best, bi = score, b
    return bi if bi is not None else (bps[-1] if bps else None)


def main() -> int:
    cfg, chash = load_cfg(), cfg_hash()
    a2 = json.load(open(rel("config/phase_10b_amendment_2.json"), encoding="utf-8"))
    c2c, c3c = cfg["t2_controls"], cfg["t3_allan"]
    span = float(c2c["rth_span_s"])
    res_ns = float(c2c["C1"]["quantization_ns"])
    ladder = np.array([2.0 ** e for e in range(c3c["ladder_exponents"][0],
                                               c3c["ladder_exponents"][1] + 1)])
    min_pairs, kmax = c3c["min_pairs_pooled"], c3c["knee_max_segments"]
    ndraw, sbase = a2["n_knee_draws"], a2["knee_draw_seed_base"]
    lo_q, hi_q = (1 - a2["bootstrap_interval"]) / 2 * 100, (1 + a2["bootstrap_interval"]) / 2 * 100
    crit = a2["a2_t2c_usability_criteria"]

    os.makedirs(rel(f"{A2}/artifacts"), exist_ok=True)
    os.makedirs(rel(f"{A2}/charts"), exist_ok=True)

    # ---------------------------------------------------------------- A2-T0b
    stored = json.load(open(rel("results/phase_10b/artifacts/t2_controls.json"), encoding="utf-8"))
    coh = pd.read_parquet(rel(cfg["cohort"]["manifest"]))
    n_target = float(np.median(coh["t0_print_count"]))
    base = build_controls(cfg, span, n_target, np.random.default_rng(c2c["seed"]), res_ns)
    regen = {nm: {"stored": stored["results"][nm]["n_prints"], "regen": int(base[nm].size),
                  "match": bool(stored["results"][nm]["n_prints"] == base[nm].size)}
             for nm in stored["results"]}
    if not all(v["match"] for v in regen.values()):
        print("ROW 2 FIRES -- seed-42 regeneration does not reproduce stored summaries")
        for k, v in regen.items():
            print(f"  {k}: stored {v['stored']} regen {v['regen']} {v['match']}")
        return 2
    print(f"A2-T0b: seed-{c2c['seed']} regeneration reproduces all six print counts exactly")

    # ---------------------------------------------------------------- A2-T1
    t0 = time.perf_counter()
    rows = []
    for d in range(ndraw):
        ctl = build_controls(cfg, span, n_target, np.random.default_rng(sbase + d), res_ns)
        for nm in CTRLS:
            t = ctl[nm]
            cur = allan_curve(t, 0.0, span, ladder, min_pairs)
            by = {int(np.argmin(np.abs(np.log2(ladder) - np.log2(r["T"])))): r for r in cur}
            val = np.array([by[i]["allan"] if i in by else np.nan for i in range(len(ladder))])
            el = np.array([by[i]["eligible"] if i in by else False for i in range(len(ladder))])
            kn = fit_piecewise(ladder[el], val[el], kmax)
            if kn is None:
                continue
            sel = kn["selected"]
            bps = sel["breakpoints_T_s"]
            near = min(bps, key=lambda b: abs(np.log2(b) - np.log2(INJ[nm]))) if bps else np.nan
            rows.append({
                "draw": d, "control": nm, "injected_s": INJ[nm], "n_prints": int(t.size),
                "selected_k": sel["k"], "delta_bic_vs_k1": kn["delta_bic_vs_k1"],
                "n_breakpoints": len(bps),
                "bp_first_s": float(bps[0]) if bps else np.nan,
                "bp_last_s": float(bps[-1]) if bps else np.nan,
                "bp_nearest_injected_s": float(near) if bps else np.nan,
                "bp_position_rule_s": float(plateau_transition(sel, POSITION_RULE[nm]) or np.nan),
                "position_rule": POSITION_RULE[nm],
                "err_nearest_rungs": float(np.log2(near) - np.log2(INJ[nm])) if bps else np.nan,
                "err_position_rungs": (
                    float(np.log2(plateau_transition(sel, POSITION_RULE[nm])) - np.log2(INJ[nm]))
                    if plateau_transition(sel, POSITION_RULE[nm]) else np.nan),
                "slopes": json.dumps([round(s, 4) for s in sel["segment_slopes"]]),
            })
        if (d + 1) % 100 == 0:
            print(f"  {d+1}/{ndraw} draws ({time.perf_counter()-t0:.0f}s)", flush=True)
    df = pd.DataFrame(rows)
    df.to_parquet(rel(f"{A2}/artifacts/t1_knee_distributions.parquet"), index=False)

    def summ(g, col, inj):
        v = g[col].dropna().to_numpy()
        lg = np.log2(v) - np.log2(inj)
        lo, hi = np.percentile(lg, [lo_q, hi_q])
        return {"n_draws": int(v.size),
                "median_breakpoint_s": float(np.median(v)),
                "ci95_breakpoint_s": [float(2.0 ** (np.log2(inj) + lo)),
                                      float(2.0 ** (np.log2(inj) + hi))],
                "bias_rungs_median": float(np.median(lg)),
                "spread_rungs_ci95_width": float(hi - lo),
                "ci95_rungs": [float(lo), float(hi)],
                "covers_injected": bool(lo <= 0.0 <= hi),
                "bias_se_rungs": float(np.std(lg, ddof=1) / np.sqrt(v.size))}

    per = {}
    for nm in CTRLS:
        g = df[df["control"] == nm]
        per[nm] = {
            "injected_s": INJ[nm], "n_draws": int(len(g)),
            "selected_k_counts": {str(k): int(c) for k, c in g["selected_k"].value_counts().items()},
            "nearest_to_injected": summ(g, "bp_nearest_injected_s", INJ[nm]),
            "position_rule": dict(summ(g, "bp_position_rule_s", INJ[nm]),
                                  rule=POSITION_RULE[nm]),
            "first_breakpoint": summ(g, "bp_first_s", INJ[nm]),
            "last_breakpoint": summ(g, "bp_last_s", INJ[nm]),
        }

    # A2-T1d: dBIC <= 2 bracket on the base realization, for comparison only
    brackets = {}
    for nm in CTRLS:
        t = base[nm]
        cur = allan_curve(t, 0.0, span, ladder, min_pairs)
        by = {int(np.argmin(np.abs(np.log2(ladder) - np.log2(r["T"])))): r for r in cur}
        val = np.array([by[i]["allan"] if i in by else np.nan for i in range(len(ladder))])
        el = np.array([by[i]["eligible"] if i in by else False for i in range(len(ladder))])
        m = el & np.isfinite(val) & (val > 0)
        x, y = np.log2(ladder[m]), np.log(val[m])
        o = np.argsort(x)
        x, y = x[o], y[o]
        n = x.size
        kn = fit_piecewise(ladder[el], val[el], kmax)
        k = kn["selected_k"]
        best_bic = kn["selected"]["bic"]
        ok_bp = []
        if k >= 2:
            for i in range(3, n - 2):
                # profile the LAST breakpoint over rung positions, others at their fit
                others = [b for b in kn["selected"]["breakpoints_log2T"][:-1]]
                bps = tuple(sorted(others + [x[i]]))
                X = _design(x, bps)
                beta, *_ = np.linalg.lstsq(X, y, rcond=None)
                rss = float(((y - X @ beta) ** 2).sum())
                bic = n * np.log(max(rss, 1e-300) / n) + 2 * k * np.log(n)
                if bic - best_bic <= 2.0:
                    ok_bp.append(float(2.0 ** x[i]))
        brackets[nm] = {"delta_bic_le_2_breakpoints_s": ok_bp,
                        "bracket_rungs_width": (float(np.log2(max(ok_bp)) - np.log2(min(ok_bp)))
                                                if ok_bp else None),
                        "note": ("Profiled over the LAST breakpoint on the base realization only. "
                                 "Reported for comparison; A2-T1d says trust the bootstrap where "
                                 "they differ, because breakpoint estimation is non-regular.")}

    # A2-T1e: multi-scale -- do the two breakpoint intervals overlap?
    multi = {}
    for nm in MULTI:
        g = df[(df["control"] == nm) & (df["selected_k"] >= 3)]
        if not len(g):
            multi[nm] = {"n_draws_with_2_breakpoints": 0}
            continue
        f = np.log2(g["bp_first_s"].to_numpy())
        l = np.log2(g["bp_last_s"].to_numpy())
        fi = np.percentile(f, [lo_q, hi_q])
        li = np.percentile(l, [lo_q, hi_q])
        fine_target = np.log2(1e-5) if nm == "C4" else None
        multi[nm] = {
            "n_draws_with_2_breakpoints": int(len(g)),
            "first_bp_ci95_s": [float(2.0 ** fi[0]), float(2.0 ** fi[1])],
            "last_bp_ci95_s": [float(2.0 ** li[0]), float(2.0 ** li[1])],
            "intervals_overlap": bool(fi[1] >= li[0]),
            "separation_rungs_median": float(np.median(l - f)),
            "coarse_target_s": INJ[nm],
            "last_bp_bias_rungs_vs_coarse": float(np.median(l) - np.log2(INJ[nm])),
            "fine_target_s": 1e-5 if nm == "C4" else None,
            "first_bp_bias_rungs_vs_fine": (float(np.median(f) - fine_target)
                                            if fine_target is not None else None),
            "compression_systematic": (
                bool(np.median(f) > fine_target and np.median(l) < np.log2(INJ[nm]))
                if fine_target is not None else None),
            "compression_note": (
                "C4's single fit missed in OPPOSITE directions -- first breakpoint above the "
                "injected 1e-5 s, last breakpoint below the injected 60 s. 'compression_systematic' "
                "is True when that same inward pattern holds at the median across draws."),
        }

    # ---------------------------------------------------------------- A2-T2
    def common_bias(names, col="err_nearest_rungs"):
        """Fixed-effect common bias with a between-control homogeneity test.

        Q = sum w_i (b_i - bbar)^2 with w_i = 1/se_i^2 is chi-square on len-1 df
        under a single common bias (Cochran's Q).
        """
        b, se = [], []
        for nm in names:
            v = df[df["control"] == nm][col].dropna().to_numpy()
            b.append(float(np.median(v)))
            se.append(float(np.std(v, ddof=1) / np.sqrt(v.size)))
        b, se = np.array(b), np.array(se)
        # The breakpoint estimator is DISCRETE -- breakpoints can only land on ladder
        # rungs -- so a control whose fit picks the same rung in every draw has a
        # measured se of exactly 0 and Q diverges. Floor the se at the resolution the
        # estimator actually has: a 1-rung quantum has sd 1/sqrt(12) rungs per draw.
        se_floor = (1.0 / np.sqrt(12.0)) / np.sqrt(ndraw)
        se_used = np.maximum(se, se_floor)
        w = 1.0 / se_used ** 2
        bbar = float((w * b).sum() / w.sum())
        se_bar = float(np.sqrt(1.0 / w.sum()))
        Q = float((w * (b - bbar) ** 2).sum())
        dfree = len(names) - 1
        p = float(sps.chi2.sf(Q, dfree)) if dfree > 0 else float("nan")
        return {"controls": list(names), "per_control_bias_rungs": b.tolist(),
                "per_control_se_rungs_measured": se.tolist(),
                "per_control_se_rungs_used": se_used.tolist(),
                "se_floor_rungs": float(se_floor),
                "se_floor_note": ("Measured se is 0 wherever the fit selects the same rung in "
                                  "every draw. Floored at the estimator's own quantization, "
                                  "(1 rung)/sqrt(12)/sqrt(n_draws), so Q is finite. Q remains "
                                  "hypersensitive: with a near-deterministic estimator any "
                                  "difference between controls is significant, so the plain "
                                  "bias_range_rungs below is the practically meaningful number."),
                "common_bias_rungs": bbar,
                "common_bias_ci95": [bbar - 1.96 * se_bar, bbar + 1.96 * se_bar],
                "bias_range_rungs": float(b.max() - b.min()),
                "bias_min_rungs": float(b.min()), "bias_max_rungs": float(b.max()),
                "Q": Q, "df": dfree, "p_homogeneity": p,
                "consistent_with_single_bias": bool(p >= crit["common_bias_min_p"])}

    t2 = {"all_four": common_bias(CTRLS), "single_scale": common_bias(SINGLE),
          "multi_scale": common_bias(MULTI),
          "statistic": ("Cochran's Q homogeneity test on the four per-control median biases, "
                        "weighted by the inverse squared standard error of each median across "
                        f"{ndraw} draws. p >= {crit['common_bias_min_p']} is consistent with a "
                        "single common bias.")}

    c3p = per["C3p"]["nearest_to_injected"]
    cov_n = sum(per[nm]["nearest_to_injected"]["covers_injected"] for nm in CTRLS)
    usab = {
        "row_1_interval_width_C3p": {
            "observed_rungs": c3p["spread_rungs_ci95_width"],
            "threshold_rungs": crit["knee_interval_max_rungs"],
            "pass": bool(c3p["spread_rungs_ci95_width"] <= crit["knee_interval_max_rungs"]),
            "meaning_if_failed": "The knee cannot locate a scale at all"},
        "row_2_coverage": {
            "observed": cov_n, "of": len(CTRLS), "threshold": crit["knee_coverage_min"],
            "per_control": {nm: per[nm]["nearest_to_injected"]["covers_injected"] for nm in CTRLS},
            "pass": bool(cov_n >= crit["knee_coverage_min"]),
            "meaning_if_failed": "The knee is biased in a way its own spread does not cover"},
        "row_3_common_bias": {
            "p": t2["all_four"]["p_homogeneity"], "threshold": crit["common_bias_min_p"],
            "pass": t2["all_four"]["consistent_with_single_bias"],
            "meaning_if_failed": ("A calibration fitted on single-scale controls cannot transfer "
                                 "to the multi-scale real cohort")},
    }
    usab["survival_test_passed"] = bool(usab["row_1_interval_width_C3p"]["pass"]
                                        and usab["row_2_coverage"]["pass"])
    usab["row_5_fires"] = not usab["survival_test_passed"]

    out = {"phase": "10b", "amendment": "A10b.2", "task": "A2-T1/A2-T2",
           "config_hash": chash, "no_real_event_read": True,
           "a2_t0b_regeneration": regen,
           "n_knee_draws": ndraw, "knee_draw_seed_base": sbase,
           "per_control": per, "delta_bic_brackets": brackets, "multi_scale": multi,
           "bias_consistency": t2, "usability_criteria": usab,
           "position_rule_note": (
               "'nearest_to_injected' is the statistic A10b.1's pass/fail used and is reported for "
               "comparability, but it SELECTS ON THE ANSWER -- its coverage is optimistically "
               "biased by construction. 'plateau_onset' is a position rule fixed independently of "
               "the injected value: the breakpoint that ends a rising segment and begins a flat "
               "one. Both are reported at every control."),
           "timing_seconds": round(time.perf_counter() - t0, 1),
           "source": "research/phase_10b/a2_t1_t2_knee.py:main"}
    write_json(rel(f"{A2}/artifacts/t2_bias_consistency.json"), out)

    print(f"\nA2-T1 knee sampling distribution ({ndraw} draws per control)")
    print(f"{'ctrl':5s} {'injected':>10s} {'median bp':>11s} {'bias':>7s} {'CI95 width':>11s} "
          f"{'CI95 (rungs)':>20s}  covers")
    for nm in CTRLS:
        s = per[nm]["nearest_to_injected"]
        print(f"{nm:5s} {INJ[nm]:10.6g} {s['median_breakpoint_s']:11.6g} "
              f"{s['bias_rungs_median']:+7.3f} {s['spread_rungs_ci95_width']:11.3f} "
              f"[{s['ci95_rungs'][0]:+.3f}, {s['ci95_rungs'][1]:+.3f}]".rjust(20) +
              f"  {s['covers_injected']}")
    print("\n  position rule fixed by process shape (does not select on the answer):")
    for nm in CTRLS:
        s = per[nm]["position_rule"]
        print(f"    {nm:5s} [{s['rule']:6s}] bias {s['bias_rungs_median']:+.3f} "
              f"width {s['spread_rungs_ci95_width']:.3f} covers {s['covers_injected']}")
    print("\nA2-T2 bias consistency (Cochran's Q):")
    for k in ("all_four", "single_scale", "multi_scale"):
        v = t2[k]
        print(f"  {k:14s} common {v['common_bias_rungs']:+.3f} "
              f"CI [{v['common_bias_ci95'][0]:+.3f}, {v['common_bias_ci95'][1]:+.3f}] "
              f"range={v['bias_range_rungs']:.3f} Q={v['Q']:.1f} p={v['p_homogeneity']:.3g} "
              f"-> {'single bias' if v['consistent_with_single_bias'] else 'NOT one bias'}")
    print("\nA2-T2c usability criteria:")
    r1, r2, r3 = usab["row_1_interval_width_C3p"], usab["row_2_coverage"], usab["row_3_common_bias"]
    print(f"  1  C3' 95% interval width  {r1['observed_rungs']:.3f} rungs  <= {r1['threshold_rungs']}"
          f"   {'PASS' if r1['pass'] else 'FAIL'}")
    print(f"  2  coverage                {r2['observed']} of {r2['of']}  >= {r2['threshold']}"
          f"        {'PASS' if r2['pass'] else 'FAIL'}")
    print(f"  3  common bias p           {r3['p']:.3g}  >= {r3['threshold']}"
          f"        {'PASS' if r3['pass'] else 'FAIL'}")
    print(f"\n  SURVIVAL TEST (rows 1 and 2): "
          f"{'PASSED' if usab['survival_test_passed'] else 'FAILED -- row 5 fires'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
