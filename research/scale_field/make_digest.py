"""
Digest for the scale-field build. Regenerated from the artifacts, never hand-edited.

This is not a phase, so there is no escalation table to score -- the brief carries
exactly one gate (the Allan reconciliation) and one stopping point (step 3, Cooper
reads the chart). Both are recorded here with their observed values.

Usage: .venv/Scripts/python.exe research/scale_field/make_digest.py
"""
from __future__ import annotations

import glob
import json
import os
import sys

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import adapter  # noqa: E402
from adapter import rel  # noqa: E402

OUT = "results/scale_field/digest.json"


def _sensitivity(art: str) -> dict:
    path = os.path.join(art, "break_pyramid_sensitivity.json")
    if not os.path.exists(path):
        return {"run": False}
    with open(path, encoding="utf-8") as f:
        d = json.load(f)
    return {"run": True, "verdicts": d.get("verdicts"),
            "sigma_lo_is_not_the_knob": d["sigma_lo_is_not_the_knob"]["claim"],
            "artifact": "results/scale_field/artifacts/break_pyramid_sensitivity.json"}


def _floor(art: str) -> dict:
    """Steps r1/r2: the resolution floor across the cohort, and the sub-burst comparison."""
    out = {}
    for key, name in (("cohort", "s_min_cohort.json"), ("vs_subbursts", "s_min_vs_subbursts.json")):
        path = os.path.join(art, name)
        if not os.path.exists(path):
            out[key] = {"run": False}
            continue
        with open(path, encoding="utf-8") as f:
            d = json.load(f)
        if key == "cohort":
            out[key] = {
                "run": True, "rule": d["rule"], "n_events": d["n_events"],
                "inputs": d["inputs"], "seconds_elapsed": d["seconds_elapsed"],
                "s_min_session_median_by_segment": {
                    k: round(v["q50"], 4) for k, v in
                    d["s_min_session_seconds"]["by_segment"].items()},
                "admissibility": {b: a["n_admissible"] for b, a in
                                  d["admissibility_on_lambda_session"].items()},
                "artifact": f"results/scale_field/artifacts/{name}",
            }
        else:
            out[key] = {
                "run": True, "caveat": d["caveat_first"],
                "best_reachable_anywhere_seconds": d["s_min_reference"]["best_anywhere_seconds"],
                "n_events_reaching_10ms_at_best": d["s_min_reference"]["n_events_reaching_10ms_at_best"],
                "prints_per_subburst_median": {
                    k: v["prints_per_subburst"]["median"] for k, v in d["sources"].items()
                    if v.get("present")},
                "share_le_3_prints": {
                    k: v["prints_per_subburst"]["share_le_3"] for k, v in d["sources"].items()
                    if v.get("present")},
                "reading": d["reading"],
                "artifact": f"results/scale_field/artifacts/{name}",
            }
    return out


def _restatement(art: str) -> dict:
    path = os.path.join(art, "subburst_restatement.json")
    if not os.path.exists(path):
        return {"run": False}
    with open(path, encoding="utf-8") as f:
        d = json.load(f)
    return {"run": True,
            "question": d["task"],
            "verdicts": d.get("verdicts"),
            "conclusion": d["conclusion"]["reading"],
            "restatement_supported": d["conclusion"]["restatement_supported"],
            "power_caveats": d["conclusion"]["power_caveats"],
            "artifact": "results/scale_field/artifacts/subburst_restatement.json"}


def main() -> int:
    cfg = adapter.load_config()
    art = rel(cfg["paths"]["out_artifacts"])

    with open(os.path.join(art, "reconcile_allan.json"), encoding="utf-8") as f:
        rec = json.load(f)

    events = []
    for path in sorted(glob.glob(os.path.join(art, "field_*_manifest.json"))):
        if "_sig12_" in os.path.basename(path):
            continue                      # sensitivity run, not a primary result
        with open(path, encoding="utf-8") as f:
            mf = json.load(f)
        fld = pd.read_parquet(os.path.join(art, f"field_{mf['event_id']}.parquet"))
        per_band = {}
        for b in mf["bands"]:
            g = fld[fld["band"] == b["band"]]
            per_band[b["band"]] = {
                "scale_range_seconds": [b["scale_min_seconds"], b["scale_max_seconds"]],
                "n_scales": b["n_scales"],
                "t_grid_points": b["t_grid_points"],
                "t_grid_span_seconds": b["t_grid_span_seconds"],
                "grid_spacing_seconds": round(b["t_grid_span_seconds"] / b["t_grid_points"], 6),
                "n_cells": int(len(g)),
                "n_defined_rate": int(g["dlograte"].notna().sum()),
                "n_defined_interval": int(g["dm"].notna().sum()),
                "share_masked_rate": round(float(g["dlograte"].isna().mean()), 4),
                "share_masked_interval": round(float(g["dm"].isna().mean()), 4),
                "seconds_elapsed": b["seconds_elapsed"],
                "sigma_lo": b.get("sigma_lo"),
                "local_rate_prints_per_s": b.get("local_rate_prints_per_s"),
                "s_min_seconds_at_mean_rate": b.get("s_min_seconds_at_mean_rate"),
                "n_arrivals": b["n_arrivals_after_tie_collapse"],
                "n_intervals": b["n_intervals"],
            }
        allan = pd.read_parquet(os.path.join(art, f"allan_{mf['event_id']}.parquet"))
        a = allan[allan["allan"].notna()]
        events.append({
            "event_id": mf["event_id"],
            "cohort_group": mf["cohort_group"],
            "pooled": mf["pooled"],
            "detection_segment": mf["detection_anchor"]["event_segment"],
            "n_t0_prints": mf["tape"]["n_prints"],
            "n_tied_prints": mf["tape"]["n_tied_prints"],
            "min_nonzero_gap_ns": mf["tape"]["min_nonzero_gap_ns"],
            "v3_knee_prediction_seconds": mf["v3_prediction"]["print_rate"][
                mf["detection_anchor"]["event_segment"]],
            "allan_first_rung": {"T": float(a["T"].iloc[0]), "A": float(a["allan"].iloc[0])},
            "allan_last_rung": {"T": float(a["T"].iloc[-1]), "A": float(a["allan"].iloc[-1]),
                                "n_pairs": int(a["n_pairs"].iloc[-1])},
            "bands": per_band,
            "charts": sorted(os.path.basename(p) for p in glob.glob(
                os.path.join(rel(cfg["paths"]["out_charts"]), mf["event_id"], "*.html"))),
        })

    digest = {
        "name": "scale_field",
        "title": cfg["title"],
        "spec": cfg["spec"],
        "config_hash": adapter.config_hash(),
        "status": "r1_r2_corrected_after_cooper_read_recovery_grid_not_started",
        "order_of_work": cfg["order_of_work"],
        "stop_after": cfg["stop_after"],
        "steps": {
            "1_adapter": {
                "done": True,
                "tests": "test_scale_field.py (19) + test_adapter.py (16) + test_verification.py (8, independent adversarial suite)",
                "n_assertions_passing": 43,
                "reproduce": ".venv/Scripts/python.exe -m pytest research/scale_field -q",
            },
            "2_reconciliation_gate": {
                "done": True,
                "criterion": cfg["reconciliation"]["rule"],
                "n_cells_compared": rec["n_cells_compared"],
                "n_cells_reproduced": rec["n_cells_reproduced"],
                "n_cells_diverged": rec["n_cells_diverged"],
                "max_rel_diff": rec["max_rel_diff"],
                "tolerance_rel": rec["tolerance_rel"],
                "rungs_declined_by_both": rec["n_rungs_declined_by_both"],
                "reconciled": rec["reconciled"],
                "hard_stop": rec["hard_stop"],
                "reproduce": rec["reproduce"],
            },
            "3_one_event_both_bands_both_channels": {
                "done": True,
                "n_events": len(events),
                "reproduce": ".venv/Scripts/python.exe research/scale_field/"
                             "run_field_one_event.py --event {event_id}",
            },
            "4_cooper_reads_it": {"done": True, "owner": "Cooper", "date": "2026-08-28",
                                  "outcome": "knee criterion withdrawn; new order issued"},
            "r1_s_min_cohort": {"done": True,
                                "reproduce": ".venv/Scripts/python.exe research/scale_field/"
                                             "s_min_cohort.py --tick-detail"},
            "r2_s_min_vs_subbursts": {"done": True,
                                      "reproduce": ".venv/Scripts/python.exe research/"
                                                   "scale_field/s_min_vs_subbursts.py"},
            "r2b_restatement_test": {"done": True, "outcome": "NOT supported",
                                     "reproduce": ".venv/Scripts/python.exe research/"
                                                  "scale_field/subburst_is_a_restatement.py"},
            "r3_recovery_grid": {"done": False, "gated_on": "nothing -- next up",
                                 "RE-AIMED": "at 1 s to 300 s at the OBSERVED session rates "
                                             "(0.30/s rth, 2.11/s premarket), not at "
                                             "millisecond scales no event supports",
                                 "what": "inject tau across a log grid across intensity "
                                         "contrast and duty cycle; report bias and spread of "
                                         "whichever summary statistic is proposed"},
            "r4_matched_null": {"done": False, "gated_on": "r3",
                                "rule": cfg["poisson_null"]["replacement"],
                                "note": "on the same s_min mask so null and data share a support"},
            "r5_cohort": {"done": False, "gated_on": "r3, r4"},
        },
        "events": events,
        "break_pyramid_sensitivity": _sensitivity(art),
        "cooper_step_4_read": {
            "date": "2026-08-28",
            "knee_criterion": "WITHDRAWN. Neither candidate summary statistic recovers a "
                              "known timescale at the scales this cohort lives at. The "
                              "bit-exact Allan reproduction stands as a gate on the "
                              "point-process plumbing, which is what it tests.",
            "where": "config/scale_field.json reconciliation.v3_knees_role; "
                     "results/scale_field/REPORT.md section 8",
        },
        "resolution_floor": _floor(art),
        "cooper_read_on_r1_r2": {
            "date": "2026-08-28",
            "checks_raised": 3,
            "errors_found_in_published_numbers": 2,
            "check_1_v4_minimum": "my wording. v4's observed min IS 3 but that is a "
                                  "CONFIGURED floor (min_prints_reference), not the "
                                  "structural minimum of 2, so the distribution is "
                                  "censored and the 54.1% is pile-up on the floor.",
            "check_2_10d_rows": "REAL ERROR. kernel_min==8 alone left 78 (K,d,min_prints,"
                                "sep) cells / 1,934,084 rows. Reference cell is 46,709 "
                                "rows, median 1.75 ms / 3 prints, bit-identical to 10c.",
            "check_3_denominator": "REAL ERROR. Session coverage understated admissibility "
                                   "~6x. Re-cut on post-anchor windows.",
            "restatement_test": "NOT supported -- see resolution_floor.restatement.",
        },
        "restatement": _restatement(art),
        "deviations_recorded": [
            {"what": "allan_factor gained t_start / t_end / min_windows",
             "why": "v3 tiles the D3 extended session, not the data support; the origin "
                    "cannot be inferred from the prints. Defaults reproduce the prior "
                    "behaviour exactly and a test asserts it.",
             "where": "research/scale_field/scale_field.py:allan_factor"},
            {"what": "intervals() differences in int64 and takes an explicit origin; "
                     "seconds_since() requires one positionally",
             "why": "float64 seconds since the epoch have a 238 ns ULP against a 49 ns "
                    "minimum gap. Measured on ALXO_2020-08-05_31.58: 4 of 899 strictly "
                    "increasing timestamps went non-positive and the worst gap error was "
                    "447 ns against a 954 ns scale floor.",
             "where": "research/scale_field/scale_field.py:intervals"},
            {"what": "the RATE channel gained the same n_eff >= 8 floor as the interval "
                     "channel (found by independent verification, V5)",
             "why": "it masked only on c0 > 0, so a window holding a fraction of a print "
                    "returned |dL/dln s| ~ 14 against 0.4-1.1 where there is real data -- "
                    "and those values then set the colour scale. Masked share on the "
                    "coarse band moved 0.24 -> 0.52 for AEHL once fixed.",
             "where": "research/scale_field/scale_field.py:field"},
            {"what": "_reduce_extremum added but OFF by default",
             "why": "recorded NEGATIVE result. Extremum decimation raises the background "
                    "floor as much as the signal (p99 0.59 -> 1.53); the apparent win was "
                    "an artefact of the unfloored rate channel above.",
             "where": "research/scale_field/scale_field.py:_reduce_extremum"},
            {"what": "fine band charted over +/- 15 s inside a +/- 15 min read, not "
                     "+/- 15 min as the brief states",
             "why": "a heatmap column cannot be narrower than its kernel; at +/- 15 min "
                    "a chart-width grid gives 1.3 s per column against a 15.6 ms "
                    "smallest kernel and the panel aliases. Compute cost unchanged.",
             "where": "config/scale_field.json scale_axis.fine.window_deviation_from_brief"},
            {"what": "segment assignment uses common.session_window, not the DuckDB ICU "
                     "extension named in the adapter stub",
             "why": "the constraint is the ET wall clock, and it is met exactly. The tick "
                    "path never opens DuckDB because the pass budget over filtered_trades "
                    "is zero.",
             "where": "research/scale_field/adapter.py module docstring"},
        ],
        "untracked_by_design": {
            "results/scale_field/artifacts/*.parquet":
                "regenerable; .gitignore, matching results/phase_*/artifacts/*.parquet",
            "results/scale_field/charts/*/*.html + plotly.min.js":
                "53 MB for two events, regenerable; D14 forbids a CDN so the bundle is local",
        },
        "source": "research/scale_field/make_digest.py:main",
    }

    with open(rel(OUT), "w", encoding="utf-8") as f:
        json.dump(digest, f, indent=2)
    print(f"wrote {OUT}  ({len(events)} events)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
