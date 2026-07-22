"""
Phase 5 T1 - pre-mutation guard + view DDL snapshot.

Read-only (read_only=True). Reproduces Phase 4's T1 guard verbatim
against the live momentum_events_canonical view, then exports the
view's current CREATE VIEW statement (via duckdb_views().sql, the
catalog's own verbatim text) to results/phase_5/artifacts/view_ddl_pre.sql
as the rollback reference ahead of T5's mutation.
"""
import json

import duckdb
import pandas as pd

DB_PATH = "data/duckdb/main.duckdb"
COVERAGE_CLASS_PARQUET = "results/phase_2/artifacts/coverage_class.parquet"
PHASE_5_CONFIG = "config/phase_5.json"
OUT_JSON = "results/phase_5/artifacts/t1_guard.json"
OUT_DDL = "results/phase_5/artifacts/view_ddl_pre.sql"


def main():
    with open(PHASE_5_CONFIG) as f:
        cfg = json.load(f)
    th = cfg["escalation_thresholds"]
    expected_guard = th["canonical_in_scope_expected"]
    expected_trades_cohort = th["trades_cohort_expected"]
    expected_quotes_cohort = th["quotes_cohort_expected"]
    expected_overlap = th["overlap_expected"]

    con = duckdb.connect(DB_PATH, read_only=True)

    print("exporting live view DDL (duckdb_views().sql)...")
    ddl_df = con.execute(
        "SELECT sql FROM duckdb_views() WHERE view_name='momentum_events_canonical' AND schema_name='main'"
    ).fetchdf()
    if len(ddl_df) != 1:
        raise RuntimeError(f"expected exactly 1 momentum_events_canonical view definition, found {len(ddl_df)}")
    ddl_sql = ddl_df["sql"].iloc[0]
    with open(OUT_DDL, "w") as f:
        f.write(ddl_sql + "\n")
    print(f"wrote {len(ddl_sql)} chars to {OUT_DDL}")

    print("querying live momentum_events_canonical view (one pass)...")
    live = con.execute("""
        SELECT
          COUNT(*) AS view_row_count,
          COUNT(*) FILTER (WHERE in_scope) AS in_scope_n,
          COUNT(*) FILTER (WHERE in_scope AND source_file='file1') AS file1_inscope_n,
          COUNT(*) FILTER (WHERE in_scope AND source_file='file2') AS file2_inscope_n,
          COUNT(*) FILTER (WHERE in_scope AND source_file='file1' AND coverage_class='event_day_only') AS trades_cohort_n,
          COUNT(*) FILTER (WHERE in_scope AND source_file='file1' AND coverage_class='full_window') AS trades_full_window_n,
          COUNT(*) FILTER (WHERE in_scope AND source_file='file1' AND NOT quotes_full_window) AS quotes_cohort_n,
          COUNT(*) FILTER (WHERE in_scope AND source_file='file1' AND quotes_full_window) AS quotes_full_window_n,
          COUNT(*) FILTER (WHERE in_scope AND source_file='file1' AND coverage_class='event_day_only' AND NOT quotes_full_window) AS overlap_both,
          COUNT(*) FILTER (WHERE in_scope AND source_file='file1' AND coverage_class='event_day_only' AND quotes_full_window) AS overlap_trades_only,
          COUNT(*) FILTER (WHERE in_scope AND source_file='file1' AND coverage_class='full_window' AND NOT quotes_full_window) AS overlap_quotes_only,
          -- file2 preview, same coverage_class-derived logic, not part of the file1 guard itself
          COUNT(*) FILTER (WHERE in_scope AND source_file='file2' AND coverage_class='event_day_only') AS file2_trades_event_day_only_n,
          COUNT(*) FILTER (WHERE in_scope AND source_file='file2' AND NOT quotes_full_window) AS file2_quotes_not_full_window_n
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
    parquet_overlap_both = int(((cc_file1["coverage_class"] == "event_day_only") & (~cc_file1["quotes_full_window"])).sum())
    parquet_overlap_trades_only = int(((cc_file1["coverage_class"] == "event_day_only") & (cc_file1["quotes_full_window"])).sum())
    parquet_overlap_quotes_only = int(((cc_file1["coverage_class"] == "full_window") & (~cc_file1["quotes_full_window"])).sum())

    reconciliation = {
        "trades_cohort_match": live["trades_cohort_n"] == parquet_trades_cohort_n,
        "trades_full_window_match": live["trades_full_window_n"] == parquet_trades_full_window_n,
        "quotes_cohort_match": live["quotes_cohort_n"] == parquet_quotes_cohort_n,
        "quotes_full_window_match": live["quotes_full_window_n"] == parquet_quotes_full_window_n,
        "file1_inscope_n_match": live["file1_inscope_n"] == parquet_file1_n,
        "overlap_both_match": live["overlap_both"] == parquet_overlap_both,
        "overlap_trades_only_match": live["overlap_trades_only"] == parquet_overlap_trades_only,
        "overlap_quotes_only_match": live["overlap_quotes_only"] == parquet_overlap_quotes_only,
    }
    all_reconciled = all(reconciliation.values())

    guard_pass = live["in_scope_n"] == expected_guard
    trades_cohort_pass = live["trades_cohort_n"] == expected_trades_cohort
    quotes_cohort_pass = live["quotes_cohort_n"] == expected_quotes_cohort
    overlap_pass = (
        live["overlap_both"] == expected_overlap["both"]
        and live["overlap_trades_only"] == expected_overlap["trades_only"]
        and live["overlap_quotes_only"] == expected_overlap["quotes_only"]
    )
    sums_consistent = (
        live["overlap_both"] + live["overlap_trades_only"] == live["trades_cohort_n"]
        and live["overlap_both"] + live["overlap_quotes_only"] == live["quotes_cohort_n"]
    )

    # file2 coverage_class-derived preview - NOT a T2/T3 bitmap recompute, just what the
    # already-committed Phase 2 T8 artifact implies via the live view. Reported for
    # visibility ahead of the full bitmap passes; T4 is the authoritative measurement.
    file2_preview = {
        "file2_inscope_n": live["file2_inscope_n"],
        "file2_trades_event_day_only_n": live["file2_trades_event_day_only_n"],
        "file2_quotes_not_full_window_n": live["file2_quotes_not_full_window_n"],
        "file2_trades_event_day_only_pct": round(100 * live["file2_trades_event_day_only_n"] / live["file2_inscope_n"], 2),
        "file2_quotes_not_full_window_pct": round(100 * live["file2_quotes_not_full_window_n"] / live["file2_inscope_n"], 2),
        "note": "coverage_class/quotes_full_window on the live view for source_file='file2', via Phase 2 T8's already-committed coverage_class.parquet join. Not yet a fresh T2/T3 bitmap recompute - see decisions_log if this preview and escalation row 4's 5%/260 threshold are in tension.",
    }

    out = {
        "phase": "5", "task": "T1",
        "spine_guard": {"expected": expected_guard, "observed": live["in_scope_n"], "pass": guard_pass},
        "view_row_count": live["view_row_count"],
        "cohort_derivation": "in_scope=TRUE AND source_file='file1'; trades cohort = coverage_class='event_day_only'; quotes cohort = NOT quotes_full_window. Derived from the live momentum_events_canonical view, identical to Phase 4 T1.",
        "live_view": live,
        "coverage_class_parquet": {
            "file1_inscope_n": parquet_file1_n,
            "trades_cohort_n": parquet_trades_cohort_n,
            "trades_full_window_n": parquet_trades_full_window_n,
            "quotes_cohort_n": parquet_quotes_cohort_n,
            "quotes_full_window_n": parquet_quotes_full_window_n,
            "overlap_both": parquet_overlap_both,
            "overlap_trades_only": parquet_overlap_trades_only,
            "overlap_quotes_only": parquet_overlap_quotes_only,
        },
        "reconciliation": reconciliation,
        "all_reconciled": all_reconciled,
        "sums_consistent": sums_consistent,
        "file2_preview": file2_preview,
        "escalation_checks": {
            "spine_guard_expected": expected_guard,
            "spine_guard_observed": live["in_scope_n"],
            "spine_guard_pass": guard_pass,
            "trades_cohort_expected": expected_trades_cohort,
            "trades_cohort_observed": live["trades_cohort_n"],
            "trades_cohort_pass": trades_cohort_pass,
            "quotes_cohort_expected": expected_quotes_cohort,
            "quotes_cohort_observed": live["quotes_cohort_n"],
            "quotes_cohort_pass": quotes_cohort_pass,
            "overlap_expected": expected_overlap,
            "overlap_observed": {
                "both": live["overlap_both"],
                "trades_only": live["overlap_trades_only"],
                "quotes_only": live["overlap_quotes_only"],
            },
            "overlap_pass": overlap_pass,
        },
        "view_ddl_pre_export": OUT_DDL,
        "source": "research/phase_5/t1_guard.py:main",
    }
    with open(OUT_JSON, "w") as f:
        json.dump(out, f, indent=2, default=str)
    print(json.dumps(out, indent=2, default=str))

    all_pass = guard_pass and trades_cohort_pass and quotes_cohort_pass and overlap_pass and all_reconciled and sums_consistent
    if not all_pass:
        print("\n*** ESCALATION row 2: one or more T1 checks failed - see escalation_checks / reconciliation above ***")


if __name__ == "__main__":
    main()
