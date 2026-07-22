"""
Phase 4 T3 - three-way reconciliation (disk <-> DB <-> spine).

Read-only. Joins T2's disk_census.parquet to (a) the DB ingestion
provenance columns already present on momentum_events_canonical
(trades_ingested / quotes_ingested - DISTINCT ticker/event_date/
momentum_pct match against filtered_trades/filtered_quotes, per
src/data/canonical.py) and (b) the full canonical spine (ALL momentum_events
rows, in_scope TRUE and FALSE both, with source_file carried) - not just
the in_scope subset, since locating the gap relative to the universe is
the point.

Join key: ticker + date (folder's parsed date vs. event_date_canonical)
+ momentum_pct rounded to 2dp - same convention as src/data/canonical.py
and every prior phase's event-key join. 'None'-date orphan folders
(114, all in presence_class='neither') cannot match by construction and
are reported separately, not silently dropped.
"""
import json

import duckdb
import pandas as pd

DB_PATH = "data/duckdb/main.duckdb"
CENSUS_PARQUET = "results/phase_4/artifacts/disk_census.parquet"
OUT_PARQUET = "results/phase_4/artifacts/reconciliation.parquet"
OUT_SUMMARY = "results/phase_4/artifacts/reconciliation_summary.json"


def main():
    print("loading disk census...")
    census = pd.read_parquet(CENSUS_PARQUET)
    census["date_parsed"] = pd.to_datetime(census["date_parsed"])
    census["mom_2dp"] = census["momentum_pct"].round(2)

    print("querying live momentum_events_canonical view (full spine, all rows - one pass)...")
    con = duckdb.connect(DB_PATH, read_only=True)
    spine = con.execute("""
        SELECT ticker, event_date_canonical, momentum_pct, source_file, in_scope,
               trades_ingested, quotes_ingested, coverage_class, quotes_full_window
        FROM momentum_events_canonical
    """).fetchdf()
    con.close()
    spine["event_date_canonical"] = pd.to_datetime(spine["event_date_canonical"])
    spine["mom_2dp"] = spine["momentum_pct"].round(2)
    print(f"spine rows (all momentum_events, in_scope + out): {len(spine)}")

    # de-dup guard: join key should be unique on the spine side
    dupe_keys = spine.duplicated(subset=["ticker", "event_date_canonical", "mom_2dp"], keep=False)
    n_spine_dupe_keys = int(dupe_keys.sum())

    merged = census.merge(
        spine,
        left_on=["ticker", "date_parsed", "mom_2dp"],
        right_on=["ticker", "event_date_canonical", "mom_2dp"],
        how="left",
        indicator=True,
    )
    merged["matched_to_spine"] = merged["_merge"] == "both"
    merged = merged.drop(columns=["_merge"])
    merged.to_parquet(OUT_PARQUET, index=False)

    # --- 1. trades_only folder breakdown by {in_scope, source_file, matched} ---
    trades_only = merged[merged["presence_class"] == "trades_only"].copy()
    trades_only["in_scope_label"] = trades_only["in_scope"].map({True: "in_scope", False: "out_of_scope"}).fillna("unmatched")
    trades_only["source_file_label"] = trades_only["source_file"].fillna("unmatched")
    trades_only_breakdown = (
        trades_only.groupby(["matched_to_spine", "in_scope_label", "source_file_label"], dropna=False)
        .size().reset_index(name="n").sort_values("n", ascending=False)
    )

    # --- 2. verify 127 quotes_only cohort vs disk-level trades_only + partial-quotes ---
    quotes_only_cohort = merged[(merged["matched_to_spine"]) & (merged["in_scope"]) & (merged["source_file"] == "file1")
                                 & (merged["coverage_class"] == "full_window") & (~merged["quotes_full_window"])]
    n_quotes_only_cohort = len(quotes_only_cohort)
    quotes_only_presence_split = quotes_only_cohort["presence_class"].value_counts().to_dict()
    # "no file" failure shape = presence_class == trades_only (quotes.parquet entirely absent)
    # "partial sessions" failure shape = presence_class == both (quotes.parquet present, but T4 will show incomplete)
    n_no_quotes_file = int(quotes_only_presence_split.get("trades_only", 0))
    n_partial_quotes_file = int(quotes_only_presence_split.get("both", 0))
    other_shapes = {k: int(v) for k, v in quotes_only_presence_split.items() if k not in ("trades_only", "both")}

    # --- 3. cross-check for the full 386 cohort: no-file vs partial-file ---
    cohort_386 = merged[(merged["matched_to_spine"]) & (merged["in_scope"]) & (merged["source_file"] == "file1")
                         & (~merged["quotes_full_window"])]
    n_cohort_386 = len(cohort_386)
    cohort_386_presence_split = {str(k): int(v) for k, v in cohort_386["presence_class"].value_counts().to_dict().items()}

    # --- 4. hard-stop check: quotes present+readable+in_scope but NOT quotes_ingested ---
    hard_stop_candidates = merged[
        (merged["quotes_present"]) & (merged["quotes_readable"] == True)  # noqa: E712
        & (merged["matched_to_spine"]) & (merged["in_scope"] == True)  # noqa: E712
        & (merged["quotes_ingested"] == False)  # noqa: E712
    ]
    n_hard_stop = len(hard_stop_candidates)

    summary = {
        "phase": "4", "task": "T3",
        "join_key": "ticker + date_parsed(folder) == event_date_canonical(spine) + ROUND(momentum_pct,2)",
        "n_disk_folders": len(census),
        "n_spine_rows_all": len(spine),
        "n_spine_duplicate_join_keys": n_spine_dupe_keys,
        "n_matched_to_spine": int(merged["matched_to_spine"].sum()),
        "n_unmatched_to_spine": int((~merged["matched_to_spine"]).sum()),
        "none_date_orphans_unmatched_by_construction": int(census["date_raw"].eq("None").sum()),
        "trades_only_breakdown": [
            {"matched_to_spine": bool(r["matched_to_spine"]), "in_scope": r["in_scope_label"],
             "source_file": r["source_file_label"], "n": int(r["n"])}
            for _, r in trades_only_breakdown.iterrows()
        ],
        "trades_only_total": int(len(trades_only)),
        "quotes_only_127_verification": {
            "n_quotes_only_cohort_observed": n_quotes_only_cohort,
            "expected_from_t1": 127,
            "matches_t1": n_quotes_only_cohort == 127,
            "presence_class_split": {str(k): int(v) for k, v in quotes_only_presence_split.items()},
            "n_no_quotes_file_at_all": n_no_quotes_file,
            "n_quotes_file_present_but_partial": n_partial_quotes_file,
            "other_presence_shapes": other_shapes,
            "note": "no_quotes_file_at_all = disk presence_class trades_only (quotes.parquet absent); quotes_file_present_but_partial = presence_class both (quotes.parquet exists but is not full_window - T4 computes the exact missing sessions).",
        },
        "cohort_386_no_file_vs_partial": {
            "n_cohort_386_observed": n_cohort_386,
            "expected_from_t1": 386,
            "matches_t1": n_cohort_386 == 386,
            "presence_class_split": cohort_386_presence_split,
            "n_no_quotes_file_at_all": int(cohort_386_presence_split.get("trades_only", 0)),
            "n_quotes_file_present_but_partial": int(cohort_386_presence_split.get("both", 0)),
        },
        "escalation_row1_hard_stop_check": {
            "condition": "quotes data present+readable on disk, in-scope event, matched to spine, but absent from filtered_quotes (quotes_ingested=FALSE)",
            "threshold": "0 events",
            "observed_n": n_hard_stop,
            "triggered": n_hard_stop >= 1,
            "events": hard_stop_candidates[["folder_name", "ticker", "date_parsed", "momentum_pct"]].to_dict(orient="records") if n_hard_stop else [],
        },
        "source": "research/phase_4/t3_reconciliation.py:main",
        "artifact": OUT_PARQUET,
    }
    with open(OUT_SUMMARY, "w") as f:
        json.dump(summary, f, indent=2, default=str)
    print(json.dumps(summary, indent=2, default=str))

    if summary["escalation_row1_hard_stop_check"]["triggered"]:
        print("\n*** ESCALATION row 1: quotes present+readable+in_scope but not ingested - see events above ***")
    if not summary["quotes_only_127_verification"]["matches_t1"]:
        print("\n*** WARNING: 127 quotes-only verification mismatch vs T1 - investigate ***")
    if not summary["cohort_386_no_file_vs_partial"]["matches_t1"]:
        print("\n*** WARNING: 386 cohort count mismatch vs T1 - investigate ***")


if __name__ == "__main__":
    main()
