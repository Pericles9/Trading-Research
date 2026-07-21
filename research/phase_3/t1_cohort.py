"""
Phase 3 T1 - spine guard + cohort reconciliation.

Read-only phase throughout (read_only=True). Queries the LIVE
momentum_events_canonical view (as it stands post-Phase-2-T8, no
create_view() calls here) for the guard and cohort derivation, then
independently reconciles those counts against the
results/phase_2/artifacts/coverage_class.parquet artifact (read directly,
bypassing the view) per the prompt's "derive from the live view, then
reconcile against the parquet" instruction.
"""
import json

import duckdb
import pandas as pd

DB_PATH = "data/duckdb/main.duckdb"
COVERAGE_CLASS_PARQUET = "results/phase_2/artifacts/coverage_class.parquet"
PHASE_3_CONFIG = "config/phase_3.json"
OUT_PATH = "results/phase_3/artifacts/t1_cohort.json"


def main():
    with open(PHASE_3_CONFIG) as f:
        cfg = json.load(f)
    expected_guard = cfg["escalation_thresholds"]["canonical_in_scope_expected"]
    expected_trades_cohort = cfg["escalation_thresholds"]["trades_cohort_expected"]
    expected_quotes_cohort = cfg["escalation_thresholds"]["quotes_cohort_expected"]

    con = duckdb.connect(DB_PATH, read_only=True)

    print("querying live momentum_events_canonical view (one pass)...")
    live = con.execute("""
        SELECT
          COUNT(*) FILTER (WHERE in_scope) AS in_scope_n,
          COUNT(*) FILTER (WHERE in_scope AND source_file='file1' AND coverage_class='event_day_only') AS trades_cohort_n,
          COUNT(*) FILTER (WHERE in_scope AND source_file='file1' AND coverage_class='full_window') AS trades_full_window_n,
          COUNT(*) FILTER (WHERE in_scope AND source_file='file1') AS file1_inscope_n,
          COUNT(*) FILTER (WHERE in_scope AND source_file='file1' AND NOT quotes_full_window) AS quotes_cohort_n,
          COUNT(*) FILTER (WHERE in_scope AND source_file='file1' AND quotes_full_window) AS quotes_full_window_n
        FROM momentum_events_canonical
    """).fetchdf().iloc[0].to_dict()
    live = {k: int(v) for k, v in live.items()}
    con.close()

    print("reading coverage_class.parquet directly (bypassing the view)...")
    cc = pd.read_parquet(COVERAGE_CLASS_PARQUET)
    cc_file1 = cc[cc["source_file"] == "file1"]
    parquet_trades_cohort_n = int((cc_file1["coverage_class"] == "event_day_only").sum())
    parquet_trades_full_window_n = int((cc_file1["coverage_class"] == "full_window").sum())
    parquet_quotes_cohort_n = int((~cc_file1["quotes_full_window"]).sum())
    parquet_quotes_full_window_n = int((cc_file1["quotes_full_window"]).sum())
    parquet_file1_n = int(len(cc_file1))

    reconciliation = {
        "trades_cohort_match": live["trades_cohort_n"] == parquet_trades_cohort_n,
        "trades_full_window_match": live["trades_full_window_n"] == parquet_trades_full_window_n,
        "quotes_cohort_match": live["quotes_cohort_n"] == parquet_quotes_cohort_n,
        "quotes_full_window_match": live["quotes_full_window_n"] == parquet_quotes_full_window_n,
        "file1_inscope_n_match": live["file1_inscope_n"] == parquet_file1_n,
    }
    all_reconciled = all(reconciliation.values())

    guard_pass = live["in_scope_n"] == expected_guard
    trades_cohort_pass = live["trades_cohort_n"] == expected_trades_cohort
    quotes_cohort_pass = live["quotes_cohort_n"] == expected_quotes_cohort

    out = {
        "phase": "3", "task": "T1",
        "spine_guard": {"expected": expected_guard, "observed": live["in_scope_n"], "pass": guard_pass},
        "cohort_derivation": "pre-2025 (source_file='file1') AND in_scope=TRUE AND coverage_class='event_day_only' (trades cohort); same population AND quotes_full_window=FALSE (quotes cohort). Derived from the live momentum_events_canonical view.",
        "live_view": live,
        "coverage_class_parquet": {
            "file1_inscope_n": parquet_file1_n,
            "trades_cohort_n": parquet_trades_cohort_n,
            "trades_full_window_n": parquet_trades_full_window_n,
            "quotes_cohort_n": parquet_quotes_cohort_n,
            "quotes_full_window_n": parquet_quotes_full_window_n,
        },
        "reconciliation": reconciliation,
        "all_reconciled": all_reconciled,
        "escalation_checks": {
            "spine_guard_pass": guard_pass,
            "trades_cohort_expected": expected_trades_cohort,
            "trades_cohort_observed": live["trades_cohort_n"],
            "trades_cohort_pass": trades_cohort_pass,
            "quotes_cohort_expected": expected_quotes_cohort,
            "quotes_cohort_observed": live["quotes_cohort_n"],
            "quotes_cohort_pass": quotes_cohort_pass,
        },
        "source": "research/phase_3/t1_cohort.py:main",
    }
    with open(OUT_PATH, "w") as f:
        json.dump(out, f, indent=2, default=str)
    print(json.dumps(out, indent=2, default=str))

    if not (guard_pass and trades_cohort_pass and quotes_cohort_pass and all_reconciled):
        print("\n*** ESCALATION: one or more T1 checks failed - see escalation_checks / reconciliation above ***")


if __name__ == "__main__":
    main()
