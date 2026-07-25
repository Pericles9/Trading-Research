"""
Phase 7 T2 - ETH-dominant flag on the canonical spine.

Recreates momentum_events_canonical at stage="t8" (additive: two new
columns flag_eth_dominant_t0, t0_eth_row_share; Phase 2 T8 / Phase 5 T5
precedent - no column removed/renamed/retyped, no base table touched).

ZERO-FULL-TABLE-PASS DISCIPLINE (escalation row 11): the view carries
trades_ingested/quotes_ingested columns whose definition scans
filtered_trades/filtered_quotes (~8.7B rows). Any SELECT/COUNT over the
VIEW would trigger that scan. So this task NEVER queries the view for
verification. It:
  1. CREATE OR REPLACE VIEW at stage t8 (pure DDL - no scan),
  2. DESCRIBE the view to confirm the two columns exist (no scan),
  3. verifies all counts via scan-free direct queries that replicate the
     view's OWN flag-join and in_scope formula against momentum_events +
     the committed parquets (classification, event_flags) + the Phase 6
     ETH artifact - none of which touch filtered_trades/filtered_quotes.

Because the verification SQL is byte-identical in logic to the view's
(same join keys, same filter, same in_scope formula from
src/data/canonical.py), proving the direct queries proves the view.
"""
import json

import duckdb

from src.data.canonical import (
    create_view,
    ETH_DOMINANT_SOURCE_PATH,
    ETH_DOMINANT_THRESHOLD,
    CLASSIFICATION_PATH,
    EVENT_FLAGS_PATH,
    IN_SCOPE_CLASSES,
    _p,
    _load_thresholds,
)

DB_PATH = "data/duckdb/main.duckdb"
SAMPLING_FRAME = "results/phase_5a/artifacts/sampling_frame.parquet"  # committed D1 materialization (15,763)
OUT_PATH = "results/phase_7/artifacts/t2_flag_verification.json"

EXPECTED_TRUE = 736
EXPECTED_IN_SCOPE = 20951
EXPECTED_D1 = 15763


def main():
    prev_close_floor, mom_sanity_cap = _load_thresholds()
    eth_src = _p(ETH_DOMINANT_SOURCE_PATH)
    classification = _p(CLASSIFICATION_PATH)
    event_flags = _p(EVENT_FLAGS_PATH)

    con = duckdb.connect(DB_PATH, read_only=False)

    # --- Step 1: recreate the view at stage t8 (DDL only, no scan) ---
    create_view(con, stage="t8", prev_close_floor=prev_close_floor, mom_sanity_cap=mom_sanity_cap)
    view_cols = con.execute("DESCRIBE momentum_events_canonical").fetchdf()["column_name"].tolist()
    has_flag = "flag_eth_dominant_t0" in view_cols
    has_share = "t0_eth_row_share" in view_cols
    print(f"view recreated at stage t8. new columns present: flag_eth_dominant_t0={has_flag}, t0_eth_row_share={has_share}")

    # --- Step 2: scan-free verification via direct queries (NO view materialization) ---

    # (a) flagged 736: the view's ethd subquery join, replicated exactly, joined to the spine.
    flag_check = con.execute(f"""
        WITH ethd AS (
            SELECT ticker,
                   CAST(CAST(event_date_canonical AS DATE) AS VARCHAR) AS event_date_canonical,
                   ROUND(momentum_pct, 2) AS momentum_pct,
                   excluded_share AS t0_eth_row_share
            FROM read_parquet('{eth_src}')
            WHERE excluded_share > {ETH_DOMINANT_THRESHOLD}
        ),
        matched AS (
            SELECT me.ticker, COALESCE(me.date, me.event_date) AS ed, ROUND(me.momentum_pct,2) AS m,
                   ethd.t0_eth_row_share
            FROM momentum_events me
            JOIN ethd
              ON me.ticker = ethd.ticker
             AND COALESCE(me.date, me.event_date) = ethd.event_date_canonical
             AND ROUND(me.momentum_pct, 2) = ethd.momentum_pct
        )
        SELECT
            (SELECT COUNT(*) FROM ethd) AS ethd_rows,
            (SELECT COUNT(DISTINCT (ticker,event_date_canonical,momentum_pct)) FROM ethd) AS ethd_distinct_keys,
            (SELECT COUNT(*) FROM matched) AS n_flag_true,
            (SELECT COUNT(DISTINCT (ticker,ed,m)) FROM matched) AS n_flag_true_distinct,
            (SELECT MIN(t0_eth_row_share) FROM matched) AS share_min,
            (SELECT MAX(t0_eth_row_share) FROM matched) AS share_max
    """).fetchdf().iloc[0]
    n_flag_true = int(flag_check["n_flag_true"])

    # (b) duplicate join keys: does any single spine event match >1 artifact row,
    #     OR does any artifact key match >1 spine row? Either would inflate the flag.
    dup_check = con.execute(f"""
        WITH ethd AS (
            SELECT ticker,
                   CAST(CAST(event_date_canonical AS DATE) AS VARCHAR) AS event_date_canonical,
                   ROUND(momentum_pct, 2) AS momentum_pct
            FROM read_parquet('{eth_src}')
            WHERE excluded_share > {ETH_DOMINANT_THRESHOLD}
        )
        SELECT
            -- spine rows that match more than one artifact key
            (SELECT COUNT(*) FROM (
                SELECT me.ticker, COALESCE(me.date, me.event_date) AS ed, ROUND(me.momentum_pct,2) AS m, COUNT(*) c
                FROM momentum_events me
                JOIN ethd ON me.ticker = ethd.ticker
                   AND COALESCE(me.date, me.event_date) = ethd.event_date_canonical
                   AND ROUND(me.momentum_pct, 2) = ethd.momentum_pct
                GROUP BY 1,2,3 HAVING COUNT(*) > 1
            )) AS spine_rows_multi_matched,
            -- artifact keys that match more than one spine row
            (SELECT COUNT(*) FROM (
                SELECT ethd.ticker, ethd.event_date_canonical, ethd.momentum_pct, COUNT(*) c
                FROM ethd
                JOIN momentum_events me ON me.ticker = ethd.ticker
                   AND COALESCE(me.date, me.event_date) = ethd.event_date_canonical
                   AND ROUND(me.momentum_pct, 2) = ethd.momentum_pct
                GROUP BY 1,2,3 HAVING COUNT(*) > 1
            )) AS artifact_keys_multi_matched
    """).fetchdf().iloc[0]
    dup_total = int(dup_check["spine_rows_multi_matched"]) + int(dup_check["artifact_keys_multi_matched"])

    # (c) in_scope + D1: the view's in_scope formula, replicated scan-free
    #     (in_scope does NOT depend on trades_ingested/quotes_ingested).
    scope_check = con.execute(f"""
        WITH canon AS (
            SELECT
                CASE WHEN me.date IS NOT NULL THEN 'file1' WHEN me.event_date IS NOT NULL THEN 'file2' END AS source_file,
                ic.class AS instrument_class,
                (me.prev_close < {prev_close_floor} OR me.momentum_pct >= {mom_sanity_cap}) AS flag_bad_denominator,
                COALESCE(ef.flag_trades_mom_outlier, FALSE) AS flag_trades_mom_outlier,
                COALESCE(ef.flag_missing_event_day, FALSE) AS flag_missing_event_day
            FROM momentum_events me
            LEFT JOIN read_parquet('{classification}') ic ON me.ticker = ic.ticker
            LEFT JOIN read_parquet('{event_flags}') ef
              ON me.ticker = ef.ticker
             AND COALESCE(me.date, me.event_date) = ef.event_date_canonical
             AND ROUND(me.momentum_pct, 2) = ROUND(ef.momentum_pct, 2)
        ),
        scoped AS (
            SELECT source_file,
                (instrument_class IN {IN_SCOPE_CLASSES}
                 AND NOT COALESCE(flag_bad_denominator, FALSE)
                 AND NOT flag_trades_mom_outlier
                 AND NOT flag_missing_event_day) AS in_scope
            FROM canon
        )
        SELECT
            SUM(CASE WHEN in_scope THEN 1 ELSE 0 END) AS in_scope_total,
            SUM(CASE WHEN in_scope AND source_file='file1' THEN 1 ELSE 0 END) AS d1_total
        FROM scoped
    """).fetchdf().iloc[0]
    in_scope_total = int(scope_check["in_scope_total"])
    d1_total = int(scope_check["d1_total"])

    # (d) cross-check D1 against the committed sampling_frame.parquet (Phase 5a's frozen D1)
    d1_frame = con.execute(f"SELECT COUNT(*) FROM read_parquet('{_p(SAMPLING_FRAME)}')").fetchone()[0]

    con.close()

    # --- escalation row 4 ---
    row4_triggered = (
        n_flag_true != EXPECTED_TRUE
        or in_scope_total != EXPECTED_IN_SCOPE
        or d1_total != EXPECTED_D1
        or dup_total != 0
    )

    out = {
        "phase": "7", "task": "T2",
        "view_stage": "t8",
        "view_recreated": True,
        "new_columns_present": {"flag_eth_dominant_t0": has_flag, "t0_eth_row_share": has_share},
        "eth_dominant_definition": {
            "source_artifact": eth_src,
            "threshold": ETH_DOMINANT_THRESHOLD,
            "rule": "excluded_share > 0.5 (strict, matches Phase 6 T3 research/phase_6/t3_full_pass.py)",
            "flag_true_means": "event's T=0 tick rows are >50% outside the XNYS regular session",
            "join_key": "(ticker, COALESCE(date,event_date), ROUND(momentum_pct,2))",
        },
        "verification_method": "scan-free - replicates the view's flag-join and in_scope formula against momentum_events + committed parquets; the view itself is never SELECTed (would trigger the trades_ingested/quotes_ingested full-table scan, escalation row 11).",
        "flag_true_count": {"observed": n_flag_true, "expected": EXPECTED_TRUE, "pass": n_flag_true == EXPECTED_TRUE},
        "eth_artifact_subset_rows": int(flag_check["ethd_rows"]),
        "eth_artifact_subset_distinct_keys": int(flag_check["ethd_distinct_keys"]),
        "flag_true_distinct_keys": int(flag_check["n_flag_true_distinct"]),
        "flagged_share_range": {"min": float(flag_check["share_min"]), "max": float(flag_check["share_max"])},
        "duplicate_join_keys": {
            "spine_rows_multi_matched": int(dup_check["spine_rows_multi_matched"]),
            "artifact_keys_multi_matched": int(dup_check["artifact_keys_multi_matched"]),
            "total": dup_total, "pass": dup_total == 0,
        },
        "in_scope": {"observed": in_scope_total, "expected": EXPECTED_IN_SCOPE, "pass": in_scope_total == EXPECTED_IN_SCOPE},
        "d1": {"observed": d1_total, "expected": EXPECTED_D1, "pass": d1_total == EXPECTED_D1},
        "d1_sampling_frame_crosscheck": {"observed": int(d1_frame), "expected": EXPECTED_D1, "pass": int(d1_frame) == EXPECTED_D1},
        "escalation_row4_triggered": row4_triggered,
        "source": "research/phase_7/t2_eth_flag.py:main",
    }
    with open(OUT_PATH, "w") as f:
        json.dump(out, f, indent=2)
    print(json.dumps(out, indent=2))
    if row4_triggered:
        print("\n*** ESCALATION row 4: flag/universe count mismatch or duplicate keys - HARD STOP ***")


if __name__ == "__main__":
    main()
