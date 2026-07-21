"""
Phase 2 T3 - high_momentum/ inventory (read-only, scoped quarantine lift).

T3a: high_momentum/ is absent from the current E: data root - documented
here rather than inventoried, per the escalation table's "absent - post
finding + continue, not a stop" row. Provenance for the absence: git-tracked
results/cleanup/deletion_report.md + emergency_unblock_report.md (dated
2026-07-11, one day before the D:->E: hardware migration on 2026-07-12).

T3b: characterizes data/trade_data/momentum_events_for_collection.parquet
(the one file from the phase's authorized path list that does exist) and
its overlap with the canonical spine, both directions.

Zero-DuckDB-write phase: read_only=True throughout. Nothing in trade_data/
outside the four explicitly authorized paths (high_momentum/,
momentum_events_for_collection.parquet, logs/, metadata/) is read.
"""
import json
import os

import duckdb
import pandas as pd

DB_PATH = "data/duckdb/main.duckdb"
PHASE_1B_CONFIG = "config/phase_1b.json"
CLASSIFICATION_PATH = "results/phase_1b/artifacts/instrument_classification.parquet"
EVENT_FLAGS_PATH = "results/phase_1b/artifacts/event_flags.parquet"
HIGH_MOMENTUM_DIR = "data/trade_data/high_momentum"
LOGS_DIR = "data/trade_data/logs"
METADATA_DIR = "data/trade_data/metadata"
COLLECTION_LIST = "data/trade_data/momentum_events_for_collection.parquet"
OUT_T3A = "results/phase_2/artifacts/high_momentum_inventory_summary.json"
OUT_T3B = "results/phase_2/artifacts/collection_list_overlap.json"


def canonical_cte_sql(prev_close_floor: float, mom_sanity_cap: float) -> str:
    return f"""
    WITH canonical AS (
        SELECT
            me.ticker,
            COALESCE(me.date, me.event_date) AS event_date_canonical,
            me.momentum_pct,
            CASE WHEN me.date IS NOT NULL THEN 'file1' WHEN me.event_date IS NOT NULL THEN 'file2' END AS source_file,
            ic.class AS instrument_class,
            (me.prev_close < {prev_close_floor} OR me.momentum_pct >= {mom_sanity_cap}) AS flag_bad_denominator,
            ef.flag_trades_mom_outlier AS flag_trades_mom_outlier,
            COALESCE(ef.flag_missing_event_day, FALSE) AS flag_missing_event_day
        FROM momentum_events me
        LEFT JOIN read_parquet('{CLASSIFICATION_PATH}') ic ON me.ticker = ic.ticker
        LEFT JOIN read_parquet('{EVENT_FLAGS_PATH}') ef
          ON me.ticker = ef.ticker
         AND COALESCE(me.date, me.event_date) = ef.event_date_canonical
         AND ROUND(me.momentum_pct, 2) = ROUND(ef.momentum_pct, 2)
    )
    SELECT ticker, event_date_canonical, source_file,
        (instrument_class IN ('common', 'common_adr')
         AND NOT flag_bad_denominator
         AND NOT COALESCE(flag_trades_mom_outlier, FALSE)
         AND NOT flag_missing_event_day) AS in_scope
    FROM canonical
    """


def t3a_inventory():
    dir_exists = os.path.isdir(HIGH_MOMENTUM_DIR)
    n_files = 0
    if dir_exists:
        n_files = sum(len(files) for _, _, files in os.walk(HIGH_MOMENTUM_DIR))

    logs_exists = os.path.isdir(LOGS_DIR)
    metadata_exists = os.path.isdir(METADATA_DIR)

    # Enumerate what IS present under trade_data/ top level, for an honest
    # record against what Schema.md documents (batches/, by_date/,
    # by_ticker/, enhanced/, high_momentum/, logs/, metadata/). Only names
    # are listed - enhanced/ and rebuild_validation_sample/ are outside this
    # phase's four authorized paths and their contents are not read.
    trade_data_root = "data/trade_data"
    top_level = sorted(os.listdir(trade_data_root)) if os.path.isdir(trade_data_root) else []

    summary = {
        "phase": "2", "task": "T3a",
        "expected_path": HIGH_MOMENTUM_DIR,
        "high_momentum_dir_exists": dir_exists,
        "high_momentum_file_count": n_files,
        "logs_dir_exists": logs_exists,
        "metadata_dir_exists": metadata_exists,
        "trade_data_top_level_entries": top_level,
        "finding": (
            "high_momentum/ is absent from the current E: data root (no subfolder, 0 files - "
            "not even the 47 previously-blocked files documented as kept-back in the final "
            "deletion report). Root cause, per git-tracked results/cleanup/deletion_report.md "
            "and results/cleanup/emergency_unblock_report.md (both dated 2026-07-11, one day "
            "before the D:->E: hardware migration on 2026-07-12): high_momentum's contents were "
            "already migrated into filtered/ on D: before this phase was cut - 5,902 of 5,949 "
            "unique 2025-gap (ticker,date) pairs migrated (subtractive 3-column schema: "
            "sip_timestamp/price/size only, ms->ns converted, trades-only, no quotes), 47 "
            "confirmed-lost/blocked events kept back and not deleted. The 47 remaining files are "
            "not present on E: either; their fate between 2026-07-11 and the E: migration has not "
            "been traced further (out of this phase's scope, per the addendum in prompts/phase_2.md). "
            "logs/ and metadata/ (the other two paths this phase's scoped lift authorized) are also "
            "absent. Per the escalation table's 'high_momentum absent - post finding + continue; "
            "T3a/T4(c-source)/T5 marked N/A. Not a stop' row, and Cooper's explicit instruction to "
            "proceed as literally scoped: T3a produces this documentation artifact in place of an "
            "inventory; no per-file rows exist to write to a parquet artifact."
        ),
        "out_of_scope_siblings_observed_not_read": {
            "note": (
                "enhanced/ and rebuild_validation_sample/ exist under trade_data/ but are not among "
                "the four paths this phase's scoped quarantine lift authorizes (high_momentum/, "
                "momentum_events_for_collection.parquet, logs/, metadata/). Directory listing only "
                "(names/sizes) was used for this honest-inventory note; no file contents were read, "
                "per CLAUDE.md's trade_data/ quarantine ('do not touch, ever, without explicit "
                "instruction')."
            ),
        },
        "escalation_check": {
            "condition": "high_momentum/ absent or unreadable at the expected path",
            "triggered": not dir_exists,
            "action": "Post finding + continue; T3a/T4(c-source)/T5 marked N/A. Not a stop.",
        },
    }
    with open(OUT_T3A, "w") as f:
        json.dump(summary, f, indent=2, default=str)
    print(json.dumps(summary, indent=2, default=str))
    return summary


def t3b_collection_list():
    try:
        df = pd.read_parquet(COLLECTION_LIST)
        readable = True
        err = None
    except Exception as e:
        df = None
        readable = False
        err = str(e)

    if not readable:
        out = {"phase": "2", "task": "T3b", "readable": False, "error": err,
               "note": "collection_list unreadable - documented finding, not a stop."}
        with open(OUT_T3B, "w") as f:
            json.dump(out, f, indent=2, default=str)
        print(json.dumps(out, indent=2))
        return out

    n_rows = len(df)
    columns = df.columns.tolist()
    date_min, date_max = str(df["date"].min().date()), str(df["date"].max().date())
    year_counts = df["date"].dt.year.value_counts().sort_index().to_dict()
    n_dupe_ticker_date = int(df.duplicated(subset=["ticker", "date"]).sum())
    n_nulls_by_col = {c: int(df[c].isna().sum()) for c in columns}

    with open(PHASE_1B_CONFIG) as f:
        cfg1b = json.load(f)
    prev_close_floor = cfg1b["outlier_flags"]["prev_close_floor"]
    mom_sanity_cap = cfg1b["outlier_flags"]["mom_sanity_cap"]

    con = duckdb.connect(DB_PATH, read_only=True)
    canon = con.execute(canonical_cte_sql(prev_close_floor, mom_sanity_cap)).fetchdf()
    canon["event_date_str"] = canon["event_date_canonical"].astype(str)

    cl = df[["ticker", "date"]].copy()
    cl["date_str"] = cl["date"].dt.strftime("%Y-%m-%d")

    # direction 1: collection_list -> canonical (does each collection-list row have a canonical match?)
    merged_cl_to_canon = cl.merge(
        canon[["ticker", "event_date_str", "in_scope"]],
        left_on=["ticker", "date_str"], right_on=["ticker", "event_date_str"], how="left",
    )
    cl_matched = merged_cl_to_canon["event_date_str"].notna().sum()
    cl_matched_in_scope = (merged_cl_to_canon["in_scope"] == True).sum()  # noqa: E712

    # direction 2: canonical (2025 in-scope slice) -> collection_list (does each 2025 in-scope event appear in the collection list?)
    canon_2025_inscope = canon[(canon["source_file"] == "file2") & (canon["in_scope"] == True)].copy()  # noqa: E712
    merged_canon_to_cl = canon_2025_inscope.merge(
        cl[["ticker", "date_str"]], left_on=["ticker", "event_date_str"], right_on=["ticker", "date_str"], how="left",
    )
    canon_2025_matched = merged_canon_to_cl["date_str"].notna().sum()

    # collection_list is entirely 2024-dated (established below) - also check against file1 (pre-2025) population specifically
    canon_file1 = canon[canon["source_file"] == "file1"].copy()
    merged_cl_to_file1 = cl.merge(
        canon_file1[["ticker", "event_date_str", "in_scope"]],
        left_on=["ticker", "date_str"], right_on=["ticker", "event_date_str"], how="left",
    )
    cl_matched_file1 = merged_cl_to_file1["event_date_str"].notna().sum()

    out = {
        "phase": "2", "task": "T3b",
        "path": COLLECTION_LIST,
        "readable": True,
        "n_rows": n_rows,
        "columns": columns,
        "date_range": {"min": date_min, "max": date_max},
        "year_counts": {str(k): int(v) for k, v in year_counts.items()},
        "n_duplicate_ticker_date_pairs": n_dupe_ticker_date,
        "n_nulls_by_column": n_nulls_by_col,
        "finding": (
            f"momentum_events_for_collection.parquet is 100% year-2024 dated ({date_min}..{date_max}, "
            f"{n_rows} rows, 0 nulls, 0 duplicate (ticker,date) pairs). It does NOT establish the 2025 "
            f"high_momentum population as the prompt anticipated - this file has zero 2025 rows. Its "
            f"actual purpose/relationship to the 2025 gap-fill migration described in results/cleanup/ "
            f"is not established by this file's contents alone and is not further investigated here "
            f"(out of scope - only overlap with the canonical spine was asked for)."
        ),
        "overlap": {
            "collection_list_to_canonical": {
                "n_collection_list_rows": n_rows,
                "n_matched_any_canonical": int(cl_matched),
                "n_matched_canonical_in_scope": int(cl_matched_in_scope),
                "n_matched_file1_population": int(cl_matched_file1),
                "pct_matched_any": round(100 * cl_matched / n_rows, 2) if n_rows else 0.0,
            },
            "canonical_2025_inscope_to_collection_list": {
                "n_2025_inscope_events": int(len(canon_2025_inscope)),
                "n_matched_in_collection_list": int(canon_2025_matched),
                "pct_matched": round(100 * canon_2025_matched / len(canon_2025_inscope), 2) if len(canon_2025_inscope) else 0.0,
            },
        },
        "source": "research/phase_2/t3_high_momentum_inventory.py:t3b_collection_list",
    }
    with open(OUT_T3B, "w") as f:
        json.dump(out, f, indent=2, default=str)
    print(json.dumps(out, indent=2, default=str))
    return out


if __name__ == "__main__":
    t3a_inventory()
    t3b_collection_list()
