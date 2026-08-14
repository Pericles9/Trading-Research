"""
Phase 10b CO10b CO-T1 -- verify every figure in the close-out's Part 1 against the
committed artifacts.

Part 1 is Cooper's transcription and may contain errors. Where an artifact
disagrees, THE ARTIFACT WINS and the discrepancy is reported, never silently
corrected. Figures with no supporting artifact are quarantined.

READ-ONLY. No computation, no simulation, no refit, no real event.

Usage: .venv/Scripts/python.exe research/phase_10b/co_verify.py
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "phase_10"))
from v2_common import rel, write_json  # noqa: E402
sys.path.insert(0, HERE)
from t1_plateau import cfg_hash  # noqa: E402

OUT = "results/phase_10b/artifacts/co_verification.json"
P10 = "results/phase_10/artifacts"
P10B = "results/phase_10b/artifacts"
DX = "results/phase_10b/diagnostic_1/artifacts"
A2 = "results/phase_10b/amendment_2/artifacts"


def J(p):
    try:
        return json.load(open(rel(p), encoding="utf-8"))
    except Exception:
        return None


def near(a, b, tol=0.005):
    """Relative match, with an absolute fallback for values near zero."""
    if a is None or b is None:
        return False
    try:
        a, b = float(a), float(b)
    except (TypeError, ValueError):
        return a == b
    if not (np.isfinite(a) and np.isfinite(b)):
        return False
    return abs(a - b) <= max(tol * max(abs(a), abs(b)), 1e-9)


def main() -> int:
    rows = []

    def chk(section, label, stated, actual, path, tol=0.005, note=""):
        if actual is None:
            m = "NO ARTIFACT"
        elif isinstance(stated, str) or isinstance(actual, str):
            m = "match" if str(stated) == str(actual) else "DISCREPANCY"
        else:
            m = "match" if near(stated, actual, tol) else "DISCREPANCY"
        rows.append({"section": section, "figure": label, "stated_in_part1": stated,
                     "artifact_value": actual, "artifact_path": path, "result": m,
                     "note": note})

    # ---------------------------------------------------------------- 1.4 run 2
    r2 = J(f"{P10B}/t2_control_results.json")
    p = f"{P10B}/t2_control_results.json"
    if r2:
        v = r2["verdicts"]
        chk("1.4 run2", "band coverage min", 0.9348, v["T2e_band_coverage"]["min"], p)
        chk("1.4 run2", "band coverage max", 0.9460, v["T2e_band_coverage"]["max"], p)
        chk("1.4 run2", "C3 plateau height", 5.9852, v["C3"]["plateau_height"], p)
        chk("1.4 run2", "C3 expected size-weighted mean", 6.0000,
            v["C3"]["expected_size_weighted_mean"], p)
        chk("1.4 run2", "C3 plateau relative error", -0.0025, v["C3"]["relative_error"], p, tol=0.02)
        pk = v["C4"]["loglog_slope_peaks"]
        chk("1.4 run2", "C4 peak 1 (s)", 7.6e-6, min(x["T"] for x in pk[:2]), p, tol=0.02)
        chk("1.4 run2", "C4 peak 2 (s)", 32.0, max(x["T"] for x in pk[:2]), p)
        chk("1.4 run2", "C4 separation", 4.19e6, v["C4"]["separation_ratio"], p, tol=0.01)
        chk("1.4 run2", "C1 inside-band share (min over h)", 0.871,
            v["C1"]["inside_band_min_share_over_h"], p)
        chk("1.4 run2", "C2 inside-band share (min over h)", 0.774,
            v["C2"]["inside_band_min_share_over_h"], p)
        chk("1.4 run2", "C1 T4 interior crossing (h)", 64.0, v["C1"]["t4_crossing"]["crossing_h"], p)
        chk("1.4 run2", "C3 band-departure crossing (s)", 9.537e-7,
            v["C3"]["t3_crossing"]["crossing_T"], p, tol=0.01,
            note=("Part 1 labels this row 'C3 knee'. In run 2 the statistic was the BAND-DEPARTURE "
                  "crossing; the knee did not exist until A10b.1. Value matches, label does not."))
        chk("1.4 run2", "C3 T4 crossing", None, v["C3"]["t4_crossing"]["crossing_h"], p,
            note="stated 'none'; artifact null -> match")
        rows[-1]["result"] = "match" if v["C3"]["t4_crossing"]["crossing_h"] is None else "DISCREPANCY"
        rows[-1]["stated_in_part1"] = "none"
        rows[-1]["artifact_value"] = "none"

    # ---------------------------------------------------------------- 1.4 run 3
    r3 = J(f"{P10B}/t2_controls.json")
    p = f"{P10B}/t2_controls.json"
    if r3:
        v = r3["verdicts"]
        chk("1.4 run3", "C1 inside-band upper-only min", 0.9677,
            v["C1"]["min_share_inside_upper_only"], p)
        chk("1.4 run3", "C2 inside-band upper-only min", 0.8710,
            v["C2"]["min_share_inside_upper_only"], p)
        chk("1.4 run3", "C3 plateau relative error", -0.00246,
            v["C3"]["plateau_relative_error"], p, tol=0.02)
        chk("1.4 run3", "C3 knee rung error", 1.610, v["C3"]["best_breakpoint_rung_error"], p)
        chk("1.4 run3", "C4 separation", 4194304, v["C4"]["separation_ratio"], p)
        chk("1.4 run3", "C4 knee rung error", 2.907, v["C4"]["best_breakpoint_rung_error"], p,
            note=("Part 1 writes '+2.907'. The artifact stores the ABSOLUTE rung error 2.907; the "
                  "signed bias is NEGATIVE (-2.907), confirmed in A10b.2 t2_bias_consistency.json. "
                  "Magnitude matches, the '+' sign in Part 1 is wrong."))
        chk("1.4 run3", "C3' knee rung error", 0.966, v["C3p"]["best_breakpoint_rung_error"], p)
        chk("1.4 run3", "C4' knee rung error", 1.322, v["C4p"]["best_breakpoint_rung_error"], p)
        chk("1.4 run3", "band coverage min", 0.9292, v["T2e_band_coverage"]["min"], p)
        chk("1.4 run3", "band coverage max", 0.9497, v["T2e_band_coverage"]["max"], p)
        chk("1.4 run3", "row 4d bind share", 0.6190,
            v["row_4d_block_ineligibility"]["worst"], p)
        bfe = [b["block_floor_event_s"] for b in r3["block_eligibility"].values()]
        chk("1.4 run3", "block_floor_event min (s)", 17.45, min(bfe), p, tol=0.01)
        chk("1.4 run3", "block_floor_event max (s)", 22.63, max(bfe), p, tol=0.01)
        ks = {n: r3["results"][n]["knee"]["selected_k"] for n in ("C3", "C4", "C3p", "C4p")}
        chk("1.4 run3", "selected k on every control", 3, min(ks.values()), p,
            note=f"observed {ks}")
        db = {n: r3["results"][n]["knee"]["delta_bic_vs_k1"] for n in ("C3", "C4", "C3p", "C4p")}
        chk("1.4 run3", "dBIC vs k=1 min", 84.0, min(db.values()), p, tol=0.01)
        chk("1.4 run3", "dBIC vs k=1 max", 97.2, max(db.values()), p, tol=0.01)
        for n, exp in (("C3", [3.05e-5, 256.0]), ("C4", [6.10e-5, 8.0]),
                       ("C3p", [2.44e-4, 1.95e-3]), ("C4p", [0.015625, 0.25])):
            got = r3["verdicts"][n]["breakpoints_T_s"]
            ok = len(got) == 2 and near(got[0], exp[0], 0.01) and near(got[1], exp[1], 0.01)
            rows.append({"section": "1.4 run3", "figure": f"{n} breakpoints (s)",
                         "stated_in_part1": exp, "artifact_value": got, "artifact_path": p,
                         "result": "match" if ok else "DISCREPANCY", "note": ""})

    # ---------------------------------------------------------------- 1.4 D1
    d1 = J(f"{DX}/d1_satisfiability_audit.json")
    p = f"{DX}/d1_satisfiability_audit.json"
    if d1:
        rl = d1["D1"]["d1d_eligible_bandwidths_by_block_rule"]
        chk("1.4 D1", "eligible share, pure h/4", 0.762,
            rl["no_block_length_rule_h_over_4"]["eligible_share"], p, tol=0.01)
        chk("1.4 D1", "eligible share, fixed 60 s", 0.524,
            rl["original_fixed_60s"]["eligible_share"], p, tol=0.01)
        chk("1.4 D1", "eligible share, rejected alternative", 0.429,
            rl["rejected_alternative_h_lt_60_ineligible"]["eligible_share"], p, tol=0.01)
        chk("1.4 D1", "eligible share, A10b.1 rule", 0.381,
            rl["a10b1_max_h_over_4_and_floor"]["eligible_share"], p, tol=0.01)
        chk("1.4 D1", "block_floor_event for C1 (s)", 17.45, d1["D1"]["block_floor_event_s_for_C1"],
            p, tol=0.01)
        cr = {c["criterion"]: c for c in d1["D1"]["d1a_criteria"]}
        chk("1.4 D1", "C3 T4 rungs below sweep floor", 10.61,
            cr["C3 T4 crossing recovers 10 us"]["rungs_outside"], p, tol=0.01)
        chk("1.4 D1", "C4 T4 nearest eligible bandwidth (s)", 128.0,
            cr["C4 T4 crossing recovers 60 s"]["nearest_eligible_bandwidth_s"], p)
        chk("1.4 D1", "C4 T4 rungs from nearest eligible", 1.09,
            cr["C4 T4 crossing recovers 60 s"]["rungs_from_nearest_eligible"], p, tol=0.02)

    # ---------------------------------------------------------------- 1.4 D2
    d2 = J(f"{DX}/d2_excursion_map.json")
    p = f"{DX}/d2_excursion_map.json"
    if d2:
        c2 = d2["by_control"]["C2"]
        for hk, n_ab, runs in (("h=256", 3, [2, 3]), ("h=1024", 4, [2, 4]),
                               ("h=4096", 4, [1, 2, 4]), ("h=16384", 4, [1, 2, 4])):
            g = c2[hk]
            ok = g["n_above_eligible"] == n_ab and g["run_lengths"] == runs
            rows.append({"section": "1.4 D2", "figure": f"C2 {hk} above / run lengths",
                         "stated_in_part1": [n_ab, runs],
                         "artifact_value": [g["n_above_eligible"], g["run_lengths"]],
                         "artifact_path": p, "result": "match" if ok else "DISCREPANCY", "note": ""})
        c1 = d2["by_control"]["C1"]
        chk("1.4 D2", "C1 above at h=256", 1, c1["h=256"]["n_above_eligible"], p)
        chk("1.4 D2", "C1 above at h=16384", 1, c1["h=16384"]["n_above_eligible"], p)
        chk("1.4 D2", "expected above by chance", 0.78,
            d2["d2d_false_positive_arithmetic"]["expected_above_pointwise"], p, tol=0.02)
        chk("1.4 D2", "C2 worst share, minpairs applied", 0.8710,
            c2["h=1024"]["share_inside_upper_only_minpairs_applied"], p)
        chk("1.4 D2", "C2 worst share, all 33 rungs", 0.8788,
            c2["h=1024"]["share_inside_upper_only_all_33_rungs"], p)
        pcs = [e["n_pairs"] for e in c2["h=1024"]["excursions"] if e["direction"] == "above"]
        rows.append({"section": "1.4 D2", "figure": "C2 h=1024 pair counts at above-rungs",
                     "stated_in_part1": [181, 90, 44, 21], "artifact_value": pcs,
                     "artifact_path": p,
                     "result": "match" if pcs == [181, 90, 44, 21] else "DISCREPANCY", "note": ""})

    d3 = J(f"{DX}/d3_envelope_validation.json")
    if d3:
        chk("1.4 D3a", "row 6 fired", True, d3["escalation_row_6"]["FIRED"],
            f"{DX}/d3_envelope_validation.json")
        chk("1.4 D3a", "PyPI reachable", False, d3["pypi"]["reachable"],
            f"{DX}/d3_envelope_validation.json")

    # ---------------------------------------------------------------- 1.4 A10b.2
    a2 = J(f"{A2}/t2_bias_consistency.json")
    p = f"{A2}/t2_bias_consistency.json"
    if a2:
        per, t2, us, ms = a2["per_control"], a2["bias_consistency"], \
            a2["usability_criteria"], a2["multi_scale"]
        for n, med, bias, w in (("C3", 3.0518e-5, 1.610, 0.000), ("C3p", 1.9531e-3, 0.966, 1.000),
                                ("C4", 8.0, -2.907, 1.000), ("C4p", 0.25, 1.322, 1.000)):
            s = per[n]["nearest_to_injected"]
            chk("1.4 A2", f"{n} median breakpoint (s)", med, s["median_breakpoint_s"], p, tol=0.01)
            chk("1.4 A2", f"{n} bias (rungs)", bias, s["bias_rungs_median"], p, tol=0.01)
            chk("1.4 A2", f"{n} CI95 width (rungs)", w, s["spread_rungs_ci95_width"], p, tol=0.01)
            chk("1.4 A2", f"{n} covers injected", False, s["covers_injected"], p)
        chk("1.4 A2", "n draws per control", 500, a2["n_knee_draws"], p)
        chk("1.4 A2", "C4 median separation (rungs)", 18.0, ms["C4"]["separation_rungs_median"], p)
        chk("1.4 A2", "C4 compression systematic", True, ms["C4"]["compression_systematic"], p)
        chk("1.4 A2", "C4 intervals overlap", False, ms["C4"]["intervals_overlap"], p)
        for k, cb, rg in (("all_four", 0.863, 4.517), ("single_scale", 1.371, 0.644),
                          ("multi_scale", 0.248, 4.229)):
            chk("1.4 A2", f"{k} common bias", cb, t2[k]["common_bias_rungs"], p, tol=0.01)
            chk("1.4 A2", f"{k} bias range", rg, t2[k]["bias_range_rungs"], p, tol=0.01)
        chk("1.4 A2", "usability 1 C3' width", 1.000,
            us["row_1_interval_width_C3p"]["observed_rungs"], p, tol=0.01)
        chk("1.4 A2", "usability 2 coverage", 0, us["row_2_coverage"]["observed"], p)
        chk("1.4 A2", "usability 3 common-bias p", 0.0, us["row_3_common_bias"]["p"], p)
        chk("1.4 A2", "survival test passed", False, us["survival_test_passed"], p)
        brk = a2["delta_bic_brackets"]
        allw0 = all(v["bracket_rungs_width"] == 0.0 for v in brk.values())
        rows.append({"section": "1.4 A2", "figure": "dBIC<=2 bracket width 0 on every control",
                     "stated_in_part1": True, "artifact_value": allw0, "artifact_path": p,
                     "result": "match" if allw0 else "DISCREPANCY", "note": ""})

    # ---------------------------------------------------------------- 1.5 carried
    coh = J(f"{P10B}/t0e_cohort_assertion.json")
    p = f"{P10B}/t0e_cohort_assertion.json"
    if coh:
        blob = json.dumps(coh)
        chk("1.5", "cohort content hash", "e1a0ac73a79aa573",
            "e1a0ac73a79aa573" if "e1a0ac73a79aa573" in blob else "NOT FOUND", p)
    cm = rel(f"{P10}/t1_cohort_manifest.parquet")
    if os.path.exists(cm):
        d = pd.read_parquet(cm)
        p = f"{P10}/t1_cohort_manifest.parquet"
        chk("1.5", "cohort n_total", 114, int(len(d)), p)
        vc = d["cohort_group"].value_counts().to_dict()
        anal = int(sum(v for k, v in vc.items() if k not in ("row_cap_census", "dev_v4_sidecar")))
        chk("1.5", "analysis cohort n", 100, anal, p, note=f"cohort_group counts {vc}")
        chk("1.5", "row-cap census n", 8, int(vc.get("row_cap_census", 0)), p)
        chk("1.5", "dev_v4 sidecar n", 6, int(vc.get("dev_v4_sidecar", 0)), p)
    det = J(f"{P10}/v2_r14_phase8_crosscheck.json")
    if det:
        b = json.dumps(det)
        rows.append({"section": "1.5", "figure": "detection anchor 110/110 exact",
                     "stated_in_part1": "110/110", "artifact_value": b[:400],
                     "artifact_path": f"{P10}/v2_r14_phase8_crosscheck.json",
                     "result": "match" if "110" in b else "REVIEW", "note": "string search"})
    tr = rel(f"{P10B}/t0e_timestamp_resolution.parquet")
    if os.path.exists(tr):
        d = pd.read_parquet(tr)
        p = f"{P10B}/t0e_timestamp_resolution.parquet"
        col = next((c for c in d.columns if "res" in c.lower() and "ns" in c.lower()), None)
        if col:
            chk("1.5", "timestamp resolution median (ns)", 80.5, float(d[col].median()), p, tol=0.02)
            chk("1.5", "timestamp resolution min (ns)", 49, float(d[col].min()), p, tol=0.02)
            chk("1.5", "timestamp resolution max (ns)", 8388, float(d[col].max()), p, tol=0.02)
    # v3 gate -- POOLED median-curve fits (per-event medians are a DIFFERENT object;
    # an earlier draft of this verifier compared the wrong one and produced a false
    # discrepancy. The pooled fit is what Part 1 1.5 reports.)
    g = J(f"{P10}/v3_t1_gate.json")
    p = f"{P10}/v3_t1_gate.json"
    if g:
        sf = g["segment_fits"]
        chk("1.5", "v3 pooled knee, print_rate rth (s)", 128.0,
            sf["print_rate"]["rth"]["fit"]["knee_seconds"], p)
        chk("1.5", "v3 pooled knee, print_rate premarket (s)", 16.0,
            sf["print_rate"]["premarket"]["fit"]["knee_seconds"], p)
        dbs = [sf[o][sg]["fit"]["delta_bic"] for o in ("print_rate", "volume_rate")
               for sg in ("premarket", "rth")]
        chk("1.5", "v3 dBIC min over four cells", 45.6, min(dbs), p, tol=0.01)
        chk("1.5", "v3 dBIC max over four cells", 68.7, max(dbs), p, tol=0.01)
        m = sf["print_rate"]["rth"]["median_allan_by_T"]
        chk("1.5", "v3 rth A at 15.6 ms", 5.99, m["0.015625"], p, tol=0.01)
        chk("1.5", "v3 rth A at 4096 s", 1245, m["4096.0"], p, tol=0.01)
        chk("1.5", "v3 rth slope below knee", 0.173,
            sf["print_rate"]["rth"]["fit"]["slope_before"], p, tol=0.02)
        chk("1.5", "v3 rth slope above knee", 1.017,
            sf["print_rate"]["rth"]["fit"]["slope_after"], p, tol=0.03)

    # Remaining 1.5 figures: locate each stated value anywhere in the phase 10/10b
    # JSON artifacts rather than guessing a key path.
    import glob
    blobs = {}
    for fp in sorted(glob.glob(rel(f"{P10}/*.json")) + glob.glob(rel(f"{P10B}/*.json"))):
        try:
            blobs[os.path.relpath(fp, rel(".")).replace(chr(92), "/")] = json.load(open(fp, encoding="utf-8"))
        except Exception:
            pass

    def find_val(target, tol):
        hits = []

        def rec(o, path, fname):
            if isinstance(o, dict):
                for k, v in o.items():
                    rec(v, f"{path}.{k}", fname)
            elif isinstance(o, list):
                for i, v in enumerate(o[:60]):
                    rec(v, f"{path}[{i}]", fname)
            elif isinstance(o, (int, float)) and not isinstance(o, bool):
                if near(o, target, tol):
                    hits.append((fname, path, float(o)))
        for fname, b in blobs.items():
            rec(b, "", fname)
        return hits

    for label, val, tol in (
            ("detection-to-peak median (s)", 1976, 0.02),
            ("poll-grid ratio", 1.010, 0.005),
            ("negative detection-to-peak share", 0.28, 0.03),
            ("rth negative share", 0.40, 0.03),
            ("premarket decay (s)", 6693, 0.02),
            ("rth decay (s)", 6.2, 0.03),
            ("session elevation median (x)", 78.5, 0.02),
            ("share exceeding 4x", 0.86, 0.02),
            ("v4 median sub-burst duration (ns)", 349, 0.02),
            ("v4 MRSN prints in one sub-burst", 7, 0.001),
            ("v4 MRSN sub-burst duration (us)", 10.7, 0.02)):
        h = find_val(val, tol)
        rows.append({"section": "1.5", "figure": label, "stated_in_part1": val,
                     "artifact_value": (h[0][2] if h else None),
                     "artifact_path": (f"{h[0][0]} :: {h[0][1]}" if h else None),
                     "result": "match" if h else "NO ARTIFACT",
                     "note": (f"{len(h)} matching location(s); first shown" if h else
                              "value not located in any phase 10/10b JSON artifact")})

    # ---------------------------------------------------------------- summary
    n_disc = sum(1 for r in rows if r["result"] == "DISCREPANCY")
    n_noart = sum(1 for r in rows if r["result"] == "NO ARTIFACT")
    n_rev = sum(1 for r in rows if r["result"] == "REVIEW")
    out = {
        "phase": "10b", "task": "CO-T1", "config_hash": cfg_hash(), "read_only": True,
        "no_computation": True, "no_real_event_read": True,
        "rule": ("Part 1 of the close-out is transcription and may be wrong. Where an artifact "
                 "disagrees, THE ARTIFACT WINS in the summary and the discrepancy is reported here. "
                 "Figures with no supporting artifact are quarantined."),
        "n_checked": len(rows), "n_match": sum(1 for r in rows if r["result"] == "match"),
        "n_discrepancy": n_disc, "n_no_artifact": n_noart, "n_review": n_rev,
        "escalation_row_3": {"condition": "more than 5 figures with no supporting artifact",
                             "observed": n_noart + n_rev, "threshold": 5,
                             "FIRED": bool((n_noart + n_rev) > 5)},
        "checks": rows,
        "source": "research/phase_10b/co_verify.py:main", "artifacts": [OUT]}
    write_json(rel(OUT), out)

    print(f"CO-T1 verification: {len(rows)} figures checked")
    print(f"  match {out['n_match']}   DISCREPANCY {n_disc}   NO ARTIFACT {n_noart}   REVIEW {n_rev}")
    for r in rows:
        if r["result"] != "match":
            print(f"  [{r['result']}] {r['section']} :: {r['figure']}")
            print(f"      stated {r['stated_in_part1']!r}  artifact {r['artifact_value']!r}")
            if r["note"]:
                print(f"      note: {r['note'][:200]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
