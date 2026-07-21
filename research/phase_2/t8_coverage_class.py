"""
Phase 2 T8 - 2025 disposition + close-out: coverage_class computation.

Generalizes T4's window-coverage logic (research/phase_2/t4_window_coverage.py)
from the 2025-only slice to ALL in-scope events (20,951), to derive a
canonical-view-level flag rather than a phase-scoped measurement.

Per event: count of XNYS T-3..T+3 offsets present in filtered_trades
(post-1c heal - i.e. the live table as it stands today, no extra filtering)
-> coverage_class ('full_window' if 7/7, else 'event_day_only').
quotes_full_window: same logic off filtered_quotes, boolean.

Writes results/phase_2/artifacts/coverage_class.parquet, joined into
momentum_events_canonical by src/data/canonical.py (additive column,
non-destructive - same pattern as repaired_1c in phase 1c).

Session date derivation and calendar pin: identical to T4
(config/phase_2.json session_calendar / session_date_derivation).
Zero-DuckDB-write in THIS script - read_only=True. The view write
happens separately in src/data/canonical.py via a writable connection,
explicitly authorized by Cooper's T8 addendum.
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
OUT_PARQUET = "results/phase_2/artifacts/coverage_class.parquet"
OUT_SUMMARY = "results/phase_2/artifacts/coverage_class_summary.json"

OFFSETS = [-3, -2, -1, 0, 1, 2, 3]


def all_inscope_events(con, prev_close_floor, mom_sanity_cap):
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
            COALESCE(ef.flag_missing_event_day, FALSE) AS flag_missing_event_day
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
    SELECT ticker, event_date_canonical, ROUND(momentum_pct, 2) AS mom_2dp, source_file
    FROM scoped WHERE in_scope
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
    events = all_inscope_events(con, prev_close_floor, mom_sanity_cap)
    n_events = len(events)
    print(f"all in-scope events: {n_events}")

    xnys = mcal.get_calendar(cal_cfg["calendar_code"])
    xnys_sessions = pd.DatetimeIndex(
        xnys.schedule(start_date=cal_cfg["derivation_range"]["start"], end_date=cal_cfg["derivation_range"]["end"]).index
    ).normalize()
    session_pos = {d: i for i, d in enumerate(xnys_sessions)}

    events["event_date_canonical"] = pd.to_datetime(events["event_date_canonical"])
    anchor_not_session = events[~events["event_date_canonical"].isin(session_pos)]
    events = events[events["event_date_canonical"].isin(session_pos)].copy()
    print(f"events in matrix: {len(events)} (anchor_not_a_session excluded: {len(anchor_not_session)})")

    expected_rows = []
    for _, row in events.iterrows():
        i0 = session_pos[row["event_date_canonical"]]
        for k in OFFSETS:
            idx = i0 + k
            if 0 <= idx < len(xnys_sessions):
                expected_rows.append({
                    "ticker": row["ticker"], "event_date_canonical": row["event_date_canonical"],
                    "mom_2dp": row["mom_2dp"], "offset": k, "expected_session_date": xnys_sessions[idx],
                    "source_file": row["source_file"],
                })
    expected = pd.DataFrame(expected_rows)
    print(f"expected event-offset rows: {len(expected)}")

    events_key = events[["ticker", "event_date_canonical", "mom_2dp"]].copy()

    print("scanning filtered_trades (single pass, joined to ALL in-scope events)...")
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

    print("scanning filtered_quotes (single pass, joined to ALL in-scope events)...")
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

    def build_present(actual_df, source_name):
        m = expected.merge(
            actual_df.rename(columns={"n_rows": "n_rows_" + source_name}),
            left_on=["ticker", "event_date_canonical", "mom_2dp", "expected_session_date"],
            right_on=["ticker", "event_date_canonical", "mom_2dp", "session_date"],
            how="left",
        )
        m["n_rows_" + source_name] = m["n_rows_" + source_name].fillna(0).astype("int64")
        m["present_" + source_name] = m["n_rows_" + source_name] > 0
        return m.drop(columns=["session_date"], errors="ignore")

    matrix = build_present(actual_trades, "filtered_trades")
    matrix = matrix.merge(
        build_present(actual_quotes, "filtered_quotes")[
            ["ticker", "event_date_canonical", "mom_2dp", "offset", "present_filtered_quotes"]
        ],
        on=["ticker", "event_date_canonical", "mom_2dp", "offset"], how="left",
    )

    per_event = matrix.groupby(["ticker", "event_date_canonical", "mom_2dp", "source_file"]).agg(
        n_offsets_covered_trades=("present_filtered_trades", "sum"),
        n_offsets_covered_quotes=("present_filtered_quotes", "sum"),
    ).reset_index()
    per_event["coverage_class"] = per_event["n_offsets_covered_trades"].apply(
        lambda n: "full_window" if n == 7 else "event_day_only"
    )
    per_event["quotes_full_window"] = per_event["n_offsets_covered_quotes"] == 7
    per_event = per_event.rename(columns={"mom_2dp": "momentum_pct"})

    per_event.to_parquet(OUT_PARQUET, index=False)

    per_event["era"] = per_event["source_file"].map({"file1": "pre_2025", "file2": "2025"})
    overall = per_event["coverage_class"].value_counts().to_dict()
    by_era = per_event.groupby(["era", "coverage_class"]).size().unstack(fill_value=0).to_dict(orient="index")
    quotes_overall = per_event["quotes_full_window"].value_counts().to_dict()
    quotes_by_era = per_event.groupby(["era", "quotes_full_window"]).size().unstack(fill_value=0).to_dict(orient="index")

    summary = {
        "phase": "2", "task": "T8",
        "population": "momentum_events_canonical.in_scope=TRUE (ALL, not just 2025)",
        "n_events": n_events,
        "n_events_anchor_not_xnys_session": int(len(anchor_not_session)),
        "n_events_in_matrix": int(len(events)),
        "coverage_class_overall": {str(k): int(v) for k, v in overall.items()},
        "coverage_class_by_era": {str(k): {str(k2): int(v2) for k2, v2 in v.items()} for k, v in by_era.items()},
        "quotes_full_window_overall": {str(k): int(v) for k, v in quotes_overall.items()},
        "quotes_full_window_by_era": {str(k): {str(k2): int(v2) for k2, v2 in v.items()} for k, v in quotes_by_era.items()},
        "source": "research/phase_2/t8_coverage_class.py:main",
        "artifact": OUT_PARQUET,
    }
    with open(OUT_SUMMARY, "w") as f:
        json.dump(summary, f, indent=2, default=str)
    print(json.dumps(summary, indent=2, default=str))


if __name__ == "__main__":
    main()
