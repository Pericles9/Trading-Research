"""
Phase 2 T4 - window coverage matrix, the core question.

For each 2025 in-scope event (momentum_events_canonical.source_file='file2'
AND in_scope=TRUE, n=5,188), determines XNYS-expected T-3..T+3 sessions
(config/phase_2.json session_calendar pin, same as phase_1b/1c) and whether
each offset is present in filtered_trades / filtered_quotes post-heal.
Session date per row is derived from sip_timestamp exactly as
research/phase_1b/window_calendar_bug_quantification.py does it
(config/phase_2.json session_date_derivation).

high_momentum/ source is N/A throughout - see T3a (absent from the E: data
root). No chart-04 branch: high_momentum has no dates to check for a
pre-2025 extension (decisions_log in the digest records this explicitly).

Zero-DuckDB-write phase: read_only=True throughout.
"""
import json

import duckdb
import pandas as pd
import pandas_market_calendars as mcal

DB_PATH = "data/duckdb/main.duckdb"
PHASE_1B_CONFIG = "config/phase_1b.json"
PHASE_2_CONFIG = "config/phase_2.json"
CLASSIFICATION_PATH = "results/phase_1b/artifacts/instrument_classification.parquet"
EVENT_FLAGS_PATH = "results/phase_1b/artifacts/event_flags.parquet"
OUT_PARQUET = "results/phase_2/artifacts/window_coverage.parquet"
OUT_SUMMARY = "results/phase_2/artifacts/window_coverage_summary.json"

OFFSETS = [-3, -2, -1, 0, 1, 2, 3]


def canonical_2025_inscope_events(con, prev_close_floor, mom_sanity_cap):
    sql = f"""
    WITH canonical AS (
        SELECT
            me.ticker,
            COALESCE(me.date, me.event_date) AS event_date_canonical,
            me.momentum_pct,
            CASE WHEN me.date IS NOT NULL THEN 'file1' WHEN me.event_date IS NOT NULL THEN 'file2' END AS source_file,
            ic.class AS instrument_class,
            (me.prev_close < {prev_close_floor} OR me.momentum_pct >= {mom_sanity_cap}) AS flag_bad_denominator,
            ef.flag_trades_mom_outlier AS flag_trades_mom_outlier,
            COALESCE(ef.flag_missing_event_day, FALSE) AS flag_missing_event_day,
            COALESCE(ef.flag_window_calendar_bug, FALSE) AS flag_window_calendar_bug,
            COALESCE(ef.repaired_1c, FALSE) AS repaired_1c
        FROM momentum_events me
        LEFT JOIN read_parquet('{CLASSIFICATION_PATH}') ic ON me.ticker = ic.ticker
        LEFT JOIN read_parquet('{EVENT_FLAGS_PATH}') ef
          ON me.ticker = ef.ticker
         AND COALESCE(me.date, me.event_date) = ef.event_date_canonical
         AND ROUND(me.momentum_pct, 2) = ROUND(ef.momentum_pct, 2)
    ),
    scoped AS (
        SELECT *,
            (instrument_class IN ('common', 'common_adr')
             AND NOT flag_bad_denominator
             AND NOT COALESCE(flag_trades_mom_outlier, FALSE)
             AND NOT flag_missing_event_day) AS in_scope
        FROM canonical
    )
    SELECT ticker, event_date_canonical, ROUND(momentum_pct, 2) AS mom_2dp,
           flag_window_calendar_bug, repaired_1c
    FROM scoped WHERE source_file = 'file2' AND in_scope
    """
    return con.execute(sql).fetchdf()


def main():
    with open(PHASE_1B_CONFIG) as f:
        cfg1b = json.load(f)
    prev_close_floor = cfg1b["outlier_flags"]["prev_close_floor"]
    mom_sanity_cap = cfg1b["outlier_flags"]["mom_sanity_cap"]

    with open(PHASE_2_CONFIG) as f:
        cfg2 = json.load(f)
    cal_cfg = cfg2["session_calendar"]

    con = duckdb.connect(DB_PATH, read_only=True)
    events = canonical_2025_inscope_events(con, prev_close_floor, mom_sanity_cap)
    n_events = len(events)
    print(f"2025 in-scope events: {n_events}")

    # trades-only strata (quotes_ingested=FALSE) - separate query needed since
    # canonical_2025_inscope_events doesn't carry it; reuse T1's definition.
    trades_only_keys = con.execute(f"""
        WITH canonical AS (
            SELECT me.ticker, COALESCE(me.date, me.event_date) AS event_date_canonical,
                ROUND(me.momentum_pct, 2) AS mom_2dp,
                CASE WHEN me.date IS NOT NULL THEN 'file1' WHEN me.event_date IS NOT NULL THEN 'file2' END AS source_file,
                ic.class AS instrument_class,
                (me.prev_close < {prev_close_floor} OR me.momentum_pct >= {mom_sanity_cap}) AS flag_bad_denominator,
                ef.flag_trades_mom_outlier AS flag_trades_mom_outlier,
                COALESCE(ef.flag_missing_event_day, FALSE) AS flag_missing_event_day,
                (fq_distinct.ticker IS NOT NULL) AS quotes_ingested
            FROM momentum_events me
            LEFT JOIN read_parquet('{CLASSIFICATION_PATH}') ic ON me.ticker = ic.ticker
            LEFT JOIN read_parquet('{EVENT_FLAGS_PATH}') ef
              ON me.ticker = ef.ticker AND COALESCE(me.date, me.event_date) = ef.event_date_canonical
             AND ROUND(me.momentum_pct, 2) = ROUND(ef.momentum_pct, 2)
            LEFT JOIN (SELECT DISTINCT ticker, event_date, ROUND(momentum_pct,2) AS mom_2dp FROM filtered_quotes) fq_distinct
              ON me.ticker = fq_distinct.ticker AND COALESCE(me.date, me.event_date) = fq_distinct.event_date
             AND ROUND(me.momentum_pct, 2) = fq_distinct.mom_2dp
        )
        SELECT ticker, event_date_canonical, mom_2dp FROM canonical
        WHERE source_file='file2'
          AND instrument_class IN ('common','common_adr') AND NOT flag_bad_denominator
          AND NOT COALESCE(flag_trades_mom_outlier, FALSE) AND NOT flag_missing_event_day
          AND NOT quotes_ingested
    """).fetchdf()
    trades_only_keys["key"] = list(zip(trades_only_keys["ticker"], trades_only_keys["event_date_canonical"].astype(str), trades_only_keys["mom_2dp"]))
    trades_only_set = set(trades_only_keys["key"])

    # --- expected XNYS T-3..T+3 sessions per event ---
    xnys = mcal.get_calendar(cal_cfg["calendar_code"])
    xnys_sessions = pd.DatetimeIndex(
        xnys.schedule(start_date=cal_cfg["derivation_range"]["start"], end_date=cal_cfg["derivation_range"]["end"]).index
    ).normalize()
    session_pos = {d: i for i, d in enumerate(xnys_sessions)}

    events["event_date_canonical"] = pd.to_datetime(events["event_date_canonical"])
    anchor_not_session = events[~events["event_date_canonical"].isin(session_pos)]
    events = events[events["event_date_canonical"].isin(session_pos)].copy()

    expected_rows = []
    for _, row in events.iterrows():
        i0 = session_pos[row["event_date_canonical"]]
        for k in OFFSETS:
            idx = i0 + k
            if 0 <= idx < len(xnys_sessions):
                expected_rows.append({
                    "ticker": row["ticker"], "event_date_canonical": row["event_date_canonical"],
                    "mom_2dp": row["mom_2dp"], "offset": k, "expected_session_date": xnys_sessions[idx],
                    "flag_window_calendar_bug": row["flag_window_calendar_bug"], "repaired_1c": row["repaired_1c"],
                })
    expected = pd.DataFrame(expected_rows)
    print(f"expected event-offset rows: {len(expected)} (anchor_not_a_session excluded: {len(anchor_not_session)})")

    # --- actual per-event-per-session presence, filtered_trades & filtered_quotes ---
    events_key = events[["ticker", "event_date_canonical", "mom_2dp"]].copy()

    print("scanning filtered_trades (single pass, joined to 2025 in-scope events)...")
    actual_trades = con.execute("""
        SELECT ft.ticker, ft.event_date AS event_date_canonical, ft.momentum_pct AS mom_2dp,
               CAST(TO_TIMESTAMP(ft.sip_timestamp / 1e9) AS DATE) AS session_date,
               COUNT(*) AS n_rows
        FROM filtered_trades ft
        JOIN events_key e
          ON ft.ticker = e.ticker AND ft.event_date = e.event_date_canonical
         AND ROUND(ft.momentum_pct, 2) = e.mom_2dp
        GROUP BY 1, 2, 3, 4
    """).fetchdf()
    print(f"filtered_trades actual session rows: {len(actual_trades)}")

    print("scanning filtered_quotes (single pass, joined to 2025 in-scope events)...")
    actual_quotes = con.execute("""
        SELECT fq.ticker, fq.event_date AS event_date_canonical, fq.momentum_pct AS mom_2dp,
               CAST(TO_TIMESTAMP(fq.sip_timestamp / 1e9) AS DATE) AS session_date,
               COUNT(*) AS n_rows
        FROM filtered_quotes fq
        JOIN events_key e
          ON fq.ticker = e.ticker AND fq.event_date = e.event_date_canonical
         AND ROUND(fq.momentum_pct, 2) = e.mom_2dp
        GROUP BY 1, 2, 3, 4
    """).fetchdf()
    print(f"filtered_quotes actual session rows: {len(actual_quotes)}")

    actual_trades["mom_2dp"] = actual_trades["mom_2dp"].round(2)
    actual_quotes["mom_2dp"] = actual_quotes["mom_2dp"].round(2)

    def build_matrix(actual_df, source_name):
        m = expected.merge(
            actual_df.rename(columns={"n_rows": "n_rows_" + source_name}),
            left_on=["ticker", "event_date_canonical", "mom_2dp", "expected_session_date"],
            right_on=["ticker", "event_date_canonical", "mom_2dp", "session_date"],
            how="left",
        )
        m["n_rows_" + source_name] = m["n_rows_" + source_name].fillna(0).astype("int64")
        m["present_" + source_name] = m["n_rows_" + source_name] > 0
        return m.drop(columns=["session_date"], errors="ignore")

    matrix = build_matrix(actual_trades, "filtered_trades")
    matrix = matrix.merge(
        build_matrix(actual_quotes, "filtered_quotes")[
            ["ticker", "event_date_canonical", "mom_2dp", "offset", "n_rows_filtered_quotes", "present_filtered_quotes"]
        ],
        on=["ticker", "event_date_canonical", "mom_2dp", "offset"], how="left",
    )
    matrix["n_rows_high_momentum"] = pd.NA
    matrix["present_high_momentum"] = pd.NA  # N/A throughout - high_momentum/ absent (T3a)

    matrix["key"] = list(zip(matrix["ticker"], matrix["event_date_canonical"].astype(str), matrix["mom_2dp"]))
    matrix["trades_only_event"] = matrix["key"].isin(trades_only_set)
    matrix = matrix.drop(columns=["key"])

    matrix.to_parquet(OUT_PARQUET, index=False)

    # --- summary: % coverage by offset per source ---
    by_offset = matrix.groupby("offset").agg(
        n_events=("ticker", "count"),
        pct_filtered_trades=("present_filtered_trades", "mean"),
        pct_filtered_quotes=("present_filtered_quotes", "mean"),
    ).reset_index()
    by_offset["pct_filtered_trades"] = (by_offset["pct_filtered_trades"] * 100).round(2)
    by_offset["pct_filtered_quotes"] = (by_offset["pct_filtered_quotes"] * 100).round(2)

    # --- per-event covered-session-count distribution (0-7), per source ---
    per_event_trades = matrix.groupby(["ticker", "event_date_canonical", "mom_2dp"])["present_filtered_trades"].sum()
    per_event_quotes = matrix.groupby(["ticker", "event_date_canonical", "mom_2dp"])["present_filtered_quotes"].sum()
    dist_trades = per_event_trades.value_counts().sort_index().to_dict()
    dist_quotes = per_event_quotes.value_counts().sort_index().to_dict()

    # matrix already carries repaired_1c / flag_window_calendar_bug per row
    # (joined in via `events` at expected-rows construction time) - filter
    # directly rather than rebuilding a separate key-membership set.
    repaired_sub_direct = matrix[matrix["repaired_1c"]]
    calbug_sub_direct = matrix[matrix["flag_window_calendar_bug"]]

    def offset_pct(sub):
        g = sub.groupby("offset").agg(
            n_events=("ticker", "count"),
            pct_filtered_trades=("present_filtered_trades", "mean"),
            pct_filtered_quotes=("present_filtered_quotes", "mean"),
        ).reset_index()
        g["pct_filtered_trades"] = (g["pct_filtered_trades"] * 100).round(2)
        g["pct_filtered_quotes"] = (g["pct_filtered_quotes"] * 100).round(2)
        return g.to_dict(orient="records")

    trades_only_sub = matrix[matrix["trades_only_event"]]

    summary = {
        "phase": "2", "task": "T4",
        "population": "momentum_events_canonical.source_file='file2' AND in_scope=TRUE",
        "n_events": n_events,
        "n_events_anchor_not_xnys_session": int(len(anchor_not_session)),
        "n_events_in_matrix": int(len(events)),
        "high_momentum_source": "N/A - absent from E: data root, see T3a (results/phase_2/artifacts/high_momentum_inventory_summary.json)",
        "chart_04_branch": "not triggered - T3a found no high_momentum dates at all (dir absent), so no pre-2025 extension is possible; 2025-only matrix per decisions_log",
        "coverage_by_offset": by_offset.to_dict(orient="records"),
        "per_event_covered_session_count_distribution": {
            "filtered_trades": {str(k): int(v) for k, v in dist_trades.items()},
            "filtered_quotes": {str(k): int(v) for k, v in dist_quotes.items()},
        },
        "strata": {
            "repaired_1c": {"n_events": int(matrix[matrix['repaired_1c']][['ticker','event_date_canonical','mom_2dp']].drop_duplicates().shape[0]), "coverage_by_offset": offset_pct(repaired_sub_direct)},
            "residual_flag_window_calendar_bug": {"n_events": int(matrix[matrix['flag_window_calendar_bug']][['ticker','event_date_canonical','mom_2dp']].drop_duplicates().shape[0]), "coverage_by_offset": offset_pct(calbug_sub_direct)},
            "trades_only_quotes_not_ingested": {"n_events": int(trades_only_keys.shape[0]), "coverage_by_offset": offset_pct(trades_only_sub), "note": "quotes_ingested=FALSE by definition - 0% filtered_quotes coverage at every offset is expected, not a new finding"},
        },
        "source": "research/phase_2/t4_window_coverage.py:main",
        "artifact": OUT_PARQUET,
    }
    with open(OUT_SUMMARY, "w") as f:
        json.dump(summary, f, indent=2, default=str)
    print(json.dumps(summary, indent=2, default=str))


if __name__ == "__main__":
    main()
