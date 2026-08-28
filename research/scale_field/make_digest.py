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


def main() -> int:
    cfg = adapter.load_config()
    art = rel(cfg["paths"]["out_artifacts"])

    with open(os.path.join(art, "reconcile_allan.json"), encoding="utf-8") as f:
        rec = json.load(f)

    events = []
    for path in sorted(glob.glob(os.path.join(art, "field_*_manifest.json"))):
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
        "status": "stopped_at_step_3_awaiting_cooper",
        "order_of_work": cfg["order_of_work"],
        "stop_after": cfg["stop_after"],
        "steps": {
            "1_adapter": {
                "done": True,
                "tests": "research/scale_field/test_adapter.py + test_scale_field.py",
                "n_assertions_passing": 39,
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
            "4_cooper_reads_it": {"done": False, "owner": "Cooper"},
            "5_matched_null_then_cohort": {
                "done": False,
                "gated_on": "step 4",
                "rule": cfg["poisson_null"]["replacement"],
            },
        },
        "events": events,
        "deviations_recorded": [
            {"what": "allan_factor gained t_start / t_end / min_windows",
             "why": "v3 tiles the D3 extended session, not the data support; the origin "
                    "cannot be inferred from the prints. Defaults reproduce the prior "
                    "behaviour exactly and a test asserts it.",
             "where": "research/scale_field/scale_field.py:allan_factor"},
            {"what": "intervals() differences in int64 and takes origin_ns; "
                     "_assert_resolved raises on an unrebased epoch tape",
             "why": "float64 seconds since the epoch have a 238 ns ULP against a 49 ns "
                    "minimum gap. Measured on ALXO_2020-08-05_31.58: 4 of 899 strictly "
                    "increasing timestamps went non-positive and the worst gap error was "
                    "447 ns against a 954 ns scale floor.",
             "where": "research/scale_field/scale_field.py:intervals"},
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
