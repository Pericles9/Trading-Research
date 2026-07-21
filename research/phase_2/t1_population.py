"""
Phase 2 T1 - spine guard + 2025 population.

Zero-DuckDB-write phase: replicates src/data/canonical.py's create_view()
stage='t6' SQL as a read-only CTE against a read_only=True connection,
rather than calling create_view() (which issues CREATE OR REPLACE VIEW -
a schema write, banned this phase per config/phase_2.json's
canonical_view_note).

2025 slice = momentum_events_canonical.source_file = 'file2', confirmed
against momentum_events directly (config/phase_2.json 2025_slice_definition):
file1 (date IS NOT NULL) spans 2020-01-03..2024-12-31, zero 2025 rows;
file2 (event_date IS NOT NULL, date IS NULL) spans 2025-01-03..2025-10-31,
zero pre-2025 rows.
"""
import json

import duckdb
import pandas as pd

DB_PATH = "data/duckdb/main.duckdb"
PHASE_1B_CONFIG = "config/phase_1b.json"
CLASSIFICATION_PATH = "results/phase_1b/artifacts/instrument_classification.parquet"
EVENT_FLAGS_PATH = "results/phase_1b/artifacts/event_flags.parquet"
REPAIR_LEDGER_PATH = "results/phase_1c/artifacts/repair_ledger.parquet"
OUT_PATH = "results/phase_2/artifacts/t1_population.json"

EXPECTED_IN_SCOPE = 20951


def canonical_cte_sql(prev_close_floor: float, mom_sanity_cap: float) -> str:
    return f"""
    WITH canonical AS (
        SELECT
            me.ticker,
            COALESCE(me.date, me.event_date) AS event_date_canonical,
            me.momentum_pct,
            CASE
                WHEN me.date IS NOT NULL THEN 'file1'
                WHEN me.event_date IS NOT NULL THEN 'file2'
            END AS source_file,
            ic.class AS instrument_class,
            (me.prev_close < {prev_close_floor} OR me.momentum_pct >= {mom_sanity_cap}) AS flag_bad_denominator,
            ef.flag_trades_mom_outlier AS flag_trades_mom_outlier,
            COALESCE(ef.flag_missing_event_day, FALSE) AS flag_missing_event_day,
            COALESCE(ef.flag_window_calendar_bug, FALSE) AS flag_window_calendar_bug,
            COALESCE(ef.repaired_1c, FALSE) AS repaired_1c,
            (ft_distinct.ticker IS NOT NULL) AS trades_ingested,
            (fq_distinct.ticker IS NOT NULL) AS quotes_ingested,
            (
                ic.class IN ('common', 'common_adr')
                AND NOT COALESCE((me.prev_close < {prev_close_floor} OR me.momentum_pct >= {mom_sanity_cap}), FALSE)
                AND NOT COALESCE(ef.flag_trades_mom_outlier, FALSE)
                AND NOT COALESCE(ef.flag_missing_event_day, FALSE)
            ) AS in_scope
        FROM momentum_events me
        LEFT JOIN read_parquet('{CLASSIFICATION_PATH}') ic ON me.ticker = ic.ticker
        LEFT JOIN (
            SELECT DISTINCT ticker, event_date, ROUND(momentum_pct, 2) AS mom_2dp
            FROM filtered_trades
        ) ft_distinct
          ON me.ticker = ft_distinct.ticker
         AND COALESCE(me.date, me.event_date) = ft_distinct.event_date
         AND ROUND(me.momentum_pct, 2) = ft_distinct.mom_2dp
        LEFT JOIN (
            SELECT DISTINCT ticker, event_date, ROUND(momentum_pct, 2) AS mom_2dp
            FROM filtered_quotes
        ) fq_distinct
          ON me.ticker = fq_distinct.ticker
         AND COALESCE(me.date, me.event_date) = fq_distinct.event_date
         AND ROUND(me.momentum_pct, 2) = fq_distinct.mom_2dp
        LEFT JOIN read_parquet('{EVENT_FLAGS_PATH}') ef
          ON me.ticker = ef.ticker
         AND COALESCE(me.date, me.event_date) = ef.event_date_canonical
         AND ROUND(me.momentum_pct, 2) = ROUND(ef.momentum_pct, 2)
    )
    """


def main():
    with open(PHASE_1B_CONFIG) as f:
        cfg = json.load(f)
    prev_close_floor = cfg["outlier_flags"]["prev_close_floor"]
    mom_sanity_cap = cfg["outlier_flags"]["mom_sanity_cap"]

    con = duckdb.connect(DB_PATH, read_only=True)
    cte = canonical_cte_sql(prev_close_floor, mom_sanity_cap)

    total_in_scope = con.execute(cte + "SELECT COUNT(*) FROM canonical WHERE in_scope").fetchone()[0]
    guard_pass = total_in_scope == EXPECTED_IN_SCOPE

    by_source = con.execute(
        cte + "SELECT source_file, in_scope, COUNT(*) AS n FROM canonical GROUP BY 1,2 ORDER BY 1,2"
    ).fetchdf()

    strata = con.execute(cte + """
        SELECT
          COUNT(*) FILTER (WHERE in_scope) AS in_scope_n,
          COUNT(*) FILTER (WHERE NOT in_scope) AS excluded_n,
          COUNT(*) FILTER (WHERE in_scope AND repaired_1c) AS repaired_1c_n,
          COUNT(*) FILTER (WHERE in_scope AND flag_missing_event_day) AS residual_flag_missing_event_day_n,
          COUNT(*) FILTER (WHERE in_scope AND flag_window_calendar_bug) AS residual_flag_window_calendar_bug_n,
          COUNT(*) FILTER (WHERE in_scope AND trades_ingested AND NOT quotes_ingested) AS trades_only_n,
          COUNT(*) FILTER (WHERE in_scope AND trades_ingested) AS trades_ingested_n,
          COUNT(*) FILTER (WHERE in_scope AND quotes_ingested) AS quotes_ingested_n
        FROM canonical WHERE source_file='file2'
    """).fetchdf().iloc[0].to_dict()
    strata = {k: int(v) for k, v in strata.items()}

    excl_reasons = con.execute(cte + """
        SELECT
          instrument_class,
          flag_bad_denominator,
          flag_trades_mom_outlier,
          flag_missing_event_day,
          COUNT(*) AS n
        FROM canonical WHERE source_file='file2' AND NOT in_scope
        GROUP BY 1,2,3,4 ORDER BY n DESC
    """).fetchdf()

    # cross-check total 2025 raw rows reconcile: in_scope + excluded == file2 total
    file2_total = int(by_source[by_source["source_file"] == "file2"]["n"].sum())
    reconciles = (strata["in_scope_n"] + strata["excluded_n"]) == file2_total

    # skipped_collision stratum among 2025 in-scope events (repair_ledger.parquet, Phase 1c Amendment 2)
    ledger = pd.read_parquet(REPAIR_LEDGER_PATH)
    skipped = ledger[ledger["collision_status"] == "skipped_collision"].copy()
    skipped["event_date_canonical"] = skipped["event_date_canonical"].astype(str)
    skipped_2025 = skipped[skipped["event_date_canonical"].str.startswith("2025")]
    skipped_2025_events = (
        skipped_2025[["ticker", "event_date_canonical", "session"]]
        .drop_duplicates()
        .to_dict(orient="records")
    )

    out = {
        "phase": "2",
        "task": "T1",
        "config_hash_inputs": {"prev_close_floor": prev_close_floor, "mom_sanity_cap": mom_sanity_cap},
        "spine_guard": {
            "expected": EXPECTED_IN_SCOPE,
            "observed": int(total_in_scope),
            "pass": bool(guard_pass),
        },
        "population_by_source_file": by_source.to_dict(orient="records"),
        "2025_slice": {
            "definition": "momentum_events_canonical.source_file = 'file2' (confirmed: file1 has zero 2025 rows, file2 has zero pre-2025 rows)",
            "raw_file2_total_n": file2_total,
            "in_scope_n": strata["in_scope_n"],
            "excluded_n": strata["excluded_n"],
            "reconciles_to_file2_total": bool(reconciles),
            "repaired_1c_n": strata["repaired_1c_n"],
            "residual_flag_missing_event_day_n": strata["residual_flag_missing_event_day_n"],
            "residual_flag_window_calendar_bug_n": strata["residual_flag_window_calendar_bug_n"],
            "trades_only_n": strata["trades_only_n"],
            "trades_ingested_n": strata["trades_ingested_n"],
            "quotes_ingested_n": strata["quotes_ingested_n"],
            "skipped_collision_2025_n_sessions": len(skipped_2025_events),
            "skipped_collision_2025_events": skipped_2025_events,
        },
        "2025_excluded_reasons": excl_reasons.to_dict(orient="records"),
        "source": "research/phase_2/t1_population.py:main",
    }

    with open(OUT_PATH, "w") as f:
        json.dump(out, f, indent=2, default=str)
    print(json.dumps(out, indent=2, default=str))


if __name__ == "__main__":
    main()
