"""
Phase 5a T2 - build and verify the sampling frame.

Read-only. Frame = momentum_events_canonical WHERE in_scope=TRUE AND
source_file='file1' (Universe Decision D1, docs/Universe-Decisions.md).
Verifies frame counts against config/phase_5a.json's escalation
thresholds and reconciles the 414 flagged count against
spine_window_flags.parquet's own union/overlap figures (Phase 5 T4a).
"""
import json

import duckdb
import pandas as pd

DB_PATH = "data/duckdb/main.duckdb"
PHASE_5A_CONFIG = "config/phase_5a.json"
SPINE_WINDOW_FLAGS = "results/phase_5/artifacts/spine_window_flags.parquet"
OUT_PARQUET = "results/phase_5a/artifacts/sampling_frame.parquet"
OUT_SUMMARY = "results/phase_5a/artifacts/t2_frame_summary.json"


def main():
    with open(PHASE_5A_CONFIG) as f:
        cfg = json.load(f)
    th = cfg["escalation_thresholds"]

    con = duckdb.connect(DB_PATH, read_only=True)
    frame = con.execute("""
        SELECT ticker, event_date_canonical, momentum_pct, source_file,
               trades_full_window, quotes_full_window, clean_window,
               trades_gap_label, quotes_gap_label, trades_bitmap, quotes_bitmap
        FROM momentum_events_canonical
        WHERE in_scope = TRUE AND source_file = 'file1'
    """).fetchdf()
    con.close()

    n_total = len(frame)
    n_clean = int(frame["clean_window"].sum())
    n_flagged = n_total - n_clean
    frame.to_parquet(OUT_PARQUET, index=False)
    print(f"sampling frame: {n_total} total, {n_clean} clean, {n_flagged} flagged")

    # reconcile the 414 flagged against spine_window_flags' own file1 union/overlap (Phase 5 T4a)
    swf = pd.read_parquet(SPINE_WINDOW_FLAGS)
    swf_f1 = swf[swf["source_file"] == "file1"]
    n_trades_flagged = int((~swf_f1["trades_full_window"]).sum())
    n_quotes_flagged = int((~swf_f1["quotes_full_window"]).sum())
    n_both = int(((~swf_f1["trades_full_window"]) & (~swf_f1["quotes_full_window"])).sum())
    n_trades_only = int(((~swf_f1["trades_full_window"]) & (swf_f1["quotes_full_window"])).sum())
    n_quotes_only = int(((swf_f1["trades_full_window"]) & (~swf_f1["quotes_full_window"])).sum())
    n_union = n_both + n_trades_only + n_quotes_only

    exp = th["frame_flagged_reconciliation_expected"]
    reconciliation = {
        "trades_cohort": {"expected": exp["trades_cohort"], "observed": n_trades_flagged, "match": n_trades_flagged == exp["trades_cohort"]},
        "quotes_cohort": {"expected": exp["quotes_cohort"], "observed": n_quotes_flagged, "match": n_quotes_flagged == exp["quotes_cohort"]},
        "overlap_both": {"expected": exp["overlap"]["both"], "observed": n_both, "match": n_both == exp["overlap"]["both"]},
        "overlap_trades_only": {"expected": exp["overlap"]["trades_only"], "observed": n_trades_only, "match": n_trades_only == exp["overlap"]["trades_only"]},
        "overlap_quotes_only": {"expected": exp["overlap"]["quotes_only"], "observed": n_quotes_only, "match": n_quotes_only == exp["overlap"]["quotes_only"]},
        "union_vs_frame_flagged": {"union_from_swf": n_union, "frame_flagged": n_flagged, "match": n_union == n_flagged},
    }
    all_reconciled = all(v["match"] for v in reconciliation.values())

    checks = {
        "frame_total": {"expected": th["frame_total_expected"], "observed": n_total, "pass": n_total == th["frame_total_expected"]},
        "frame_clean": {"expected": th["frame_clean_expected"], "observed": n_clean, "pass": n_clean == th["frame_clean_expected"]},
        "frame_flagged": {"expected": th["frame_flagged_expected"], "observed": n_flagged, "pass": n_flagged == th["frame_flagged_expected"]},
    }
    all_pass = all(v["pass"] for v in checks.values()) and all_reconciled

    summary = {
        "phase": "5a", "task": "T2",
        "frame_counts": {"total": n_total, "clean": n_clean, "flagged": n_flagged},
        "checks": checks,
        "reconciliation_vs_spine_window_flags": reconciliation,
        "all_reconciled": all_reconciled,
        "all_pass": all_pass,
        "escalation_row1_triggered": not all_pass,
        "source": "research/phase_5a/t2_sampling_frame.py:main",
        "artifact": OUT_PARQUET,
    }
    with open(OUT_SUMMARY, "w") as f:
        json.dump(summary, f, indent=2, default=str)
    print(json.dumps(summary, indent=2, default=str))

    if not all_pass:
        print("\n*** ESCALATION row 1: frame count or reconciliation mismatch - HARD STOP ***")


if __name__ == "__main__":
    main()
