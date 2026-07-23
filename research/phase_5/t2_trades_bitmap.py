"""
Phase 5 T2 - trades-side per-event session bitmap, ALL 20,951 in-scope events.

Extends Phase 3's t3_classify.py bitmap derivation (same OFFSETS, same XNYS
calendar arithmetic, same join shape) from the file1-only 287 cohort to the
full in-scope population, both source files. This is one of the phase's two
budgeted full-table passes (config/phase_5.json full_table_pass_budget).

Usage: python -m research.phase_5.t2_trades_bitmap [--table filtered_trades_dev_v3]
Default table is filtered_trades (the full pass). Pass --table filtered_trades_dev_v3
to develop/verify the SQL against the dev tier first, per the phase prompt's
explicit instruction, before spending the one budgeted full-table pass.
"""
import argparse
import json

import duckdb
import pandas as pd
import pandas_market_calendars as mcal

DB_PATH = "data/duckdb/main.duckdb"
PHASE_1B_CONFIG = "config/phase_1b.json"
PHASE_5_CONFIG = "config/phase_5.json"
CLASSIFICATION_PATH = "results/phase_1b/artifacts/instrument_classification.parquet"
EVENT_FLAGS_PATH = "results/phase_1b/artifacts/event_flags.parquet"
OUT_PARQUET = "results/phase_5/artifacts/trades_bitmaps.parquet"
OUT_SUMMARY = "results/phase_5/artifacts/trades_bitmaps_summary.json"


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
    ap = argparse.ArgumentParser()
    ap.add_argument("--table", default="filtered_trades")
    ap.add_argument("--out-parquet", default=OUT_PARQUET)
    ap.add_argument("--out-summary", default=OUT_SUMMARY)
    args = ap.parse_args()
    dev_mode = args.table != "filtered_trades"

    with open(PHASE_1B_CONFIG) as f:
        cfg1b = json.load(f)
    prev_close_floor = cfg1b["outlier_flags"]["prev_close_floor"]
    mom_sanity_cap = cfg1b["outlier_flags"]["mom_sanity_cap"]

    with open(PHASE_5_CONFIG) as f:
        cfg5 = json.load(f)
    cal_cfg = cfg5["session_calendar"]
    offsets = cfg5["offsets"]

    con = duckdb.connect(DB_PATH, read_only=True)
    events = all_inscope_events(con, prev_close_floor, mom_sanity_cap)
    print(f"all in-scope events (lightweight replica): {len(events)}")

    if dev_mode:
        dev_keys = con.execute(f"""
            SELECT DISTINCT ticker, event_date AS event_date_canonical, ROUND(momentum_pct, 2) AS mom_2dp
            FROM {args.table}
        """).fetchdf()
        events["event_date_canonical"] = pd.to_datetime(events["event_date_canonical"])
        dev_keys["event_date_canonical"] = pd.to_datetime(dev_keys["event_date_canonical"])
        dev_key_set = set(zip(dev_keys["ticker"], dev_keys["event_date_canonical"], dev_keys["mom_2dp"]))
        events = events[[(r.ticker, r.event_date_canonical, r.mom_2dp) in dev_key_set for r in events.itertuples()]].copy()
        print(f"dev-mode: restricted to {len(events)} events present in {args.table}")
    else:
        events["event_date_canonical"] = pd.to_datetime(events["event_date_canonical"])

    events_key = events[["ticker", "event_date_canonical", "mom_2dp"]].copy()

    xnys = mcal.get_calendar(cal_cfg["calendar_code"])
    xnys_sessions = pd.DatetimeIndex(
        xnys.schedule(start_date=cal_cfg["derivation_range"]["start"], end_date=cal_cfg["derivation_range"]["end"]).index
    ).normalize()
    session_pos = {d: i for i, d in enumerate(xnys_sessions)}
    print(f"XNYS calendar: {mcal.__version__}, {len(xnys_sessions)} sessions in derivation range")

    print(f"scanning {args.table} (single pass, joined to {len(events)} in-scope events)...")
    actual = con.execute(f"""
        SELECT t.ticker, t.event_date AS event_date_canonical, t.momentum_pct AS mom_2dp,
               CAST(TO_TIMESTAMP(t.sip_timestamp / 1e9) AS DATE) AS session_date
        FROM {args.table} t
        JOIN events_key e
          ON t.ticker = e.ticker AND t.event_date = e.event_date_canonical
         AND ROUND(t.momentum_pct, 2) = e.mom_2dp
        GROUP BY 1, 2, 3, 4
    """).fetchdf()
    con.close()
    actual["mom_2dp"] = actual["mom_2dp"].round(2)
    print(f"actual (ticker,event,session) rows: {len(actual)}")

    actual_by_event = actual.groupby(["ticker", "event_date_canonical", "mom_2dp"])["session_date"].apply(set).to_dict()

    records = []
    for row in events.itertuples():
        ticker, d, mom, source_file = row.ticker, row.event_date_canonical, row.mom_2dp, row.source_file
        key = (ticker, d, mom)
        if d not in session_pos:
            continue  # guard; should not happen for in-scope events
        i0 = session_pos[d]
        expected = {k: xnys_sessions[i0 + k] for k in offsets if 0 <= i0 + k < len(xnys_sessions)}
        actual_set = actual_by_event.get(key, set())
        present = {k: (v in actual_set) for k, v in expected.items()}
        missing_offsets = sorted(k for k, p in present.items() if not p)
        bitmap = "".join("1" if present.get(k, False) else "0" for k in offsets)
        trades_full_window = len(missing_offsets) == 0 and len(expected) == len(offsets)

        records.append({
            "ticker": ticker, "event_date_canonical": d, "momentum_pct": mom, "source_file": source_file,
            "trades_bitmap": bitmap, "trades_missing_offsets": missing_offsets,
            "trades_n_missing": len(missing_offsets), "trades_full_window": trades_full_window,
            "expected_offsets_in_range": len(expected),
        })

    df = pd.DataFrame(records)
    df.to_parquet(args.out_parquet, index=False)

    n_events = len(df)
    n_full_window = int(df["trades_full_window"].sum())
    n_flagged = n_events - n_full_window
    by_source = df.groupby("source_file")["trades_full_window"].agg(["sum", "count"]).to_dict(orient="index")

    summary = {
        "phase": "5", "task": "T2", "table_scanned": args.table, "dev_mode": dev_mode,
        "n_events": n_events, "n_full_window": n_full_window, "n_flagged_not_full_window": n_flagged,
        "by_source_file": {
            k: {"full_window": int(v["sum"]), "not_full_window": int(v["count"] - v["sum"]), "total": int(v["count"])}
            for k, v in by_source.items()
        },
        "bitmap_top10": df["trades_bitmap"].value_counts().head(10).to_dict(),
        "source": "research/phase_5/t2_trades_bitmap.py:main",
        "artifact": args.out_parquet,
    }
    with open(args.out_summary, "w") as f:
        json.dump(summary, f, indent=2, default=str)
    print(json.dumps(summary, indent=2, default=str))


if __name__ == "__main__":
    main()
