"""
Phase 4 T4 - per-session quotes presence bitmap for the 386 cohort.

Single full-tier grouped pass over filtered_quotes, joined to ALL 20,951
in-scope events (not just the 386 cohort) - mirrors Phase 3 T3's join
shape exactly, because Phase 4 T5's weak listing/delisting signature
(T5a) needs each cohort ticker's last-seen/first-seen quotes session
date across ALL of that ticker's own in-scope event windows, which can
include events outside the 386 cohort. Per the phase's Context section
("the only full-table pass is the single grouped per-session presence
query in T4"), this script also caches the full per-event actual-session
result to _actual_quotes_sessions_cache.parquet so T5 reuses it instead
of re-scanning filtered_quotes.

Bitmap convention mirrors research/phase_3/t3_classify.py exactly:
OFFSETS = [-3,-2,-1,0,1,2,3], "1"/"0" per offset, so patterns are
directly comparable across the trades (287) and quotes (386) cohorts.
Session calendar: XNYS, pinned pandas_market_calendars 5.4.0 /
exchange_calendars 4.13.2 (corrected into the shared venv at T0b).
"""
import json

import duckdb
import pandas as pd
import pandas_market_calendars as mcal

DB_PATH = "data/duckdb/main.duckdb"
PHASE_1B_CONFIG = "config/phase_1b.json"
PHASE_4_CONFIG = "config/phase_4.json"
COVERAGE_CLASS_PARQUET = "results/phase_2/artifacts/coverage_class.parquet"
OUT_PARQUET = "results/phase_4/artifacts/quotes_bitmaps.parquet"
CACHE_PARQUET = "results/phase_4/artifacts/_actual_quotes_sessions_cache.parquet"

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
        LEFT JOIN read_parquet('results/phase_1b/artifacts/instrument_classification.parquet') ic ON me.ticker = ic.ticker
        LEFT JOIN read_parquet('results/phase_1b/artifacts/event_flags.parquet') ef
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

    with open(PHASE_4_CONFIG) as f:
        cfg4 = json.load(f)
    cal_cfg = cfg4["session_calendar"]

    con = duckdb.connect(DB_PATH, read_only=True)
    events = all_inscope_events(con, prev_close_floor, mom_sanity_cap)
    print(f"all in-scope events (lightweight replica): {len(events)}")

    cc = pd.read_parquet(COVERAGE_CLASS_PARQUET)
    cc["event_date_canonical"] = pd.to_datetime(cc["event_date_canonical"])
    cc["mom_2dp"] = cc["momentum_pct"].round(2)
    cohort = cc[(cc["source_file"] == "file1") & (~cc["quotes_full_window"])].copy()
    n_cohort = len(cohort)
    print(f"quotes cohort (file1, NOT quotes_full_window) from coverage_class.parquet: {n_cohort}")

    events["event_date_canonical"] = pd.to_datetime(events["event_date_canonical"])
    events_key = events[["ticker", "event_date_canonical", "mom_2dp"]].copy()

    xnys = mcal.get_calendar(cal_cfg["calendar_code"])
    xnys_sessions = pd.DatetimeIndex(
        xnys.schedule(start_date=cal_cfg["derivation_range"]["start"], end_date=cal_cfg["derivation_range"]["end"]).index
    ).normalize()
    session_pos = {d: i for i, d in enumerate(xnys_sessions)}
    print(f"XNYS calendar: {mcal.__version__}, {len(xnys_sessions)} sessions in derivation range")

    print("scanning filtered_quotes (single full-table pass, joined to ALL 20,951 in-scope events)...")
    actual = con.execute("""
        SELECT fq.ticker, fq.event_date AS event_date_canonical, fq.momentum_pct AS mom_2dp,
               CAST(TO_TIMESTAMP(fq.sip_timestamp / 1e9) AS DATE) AS session_date
        FROM filtered_quotes fq
        JOIN events_key e
          ON fq.ticker = e.ticker AND fq.event_date = e.event_date_canonical
         AND ROUND(fq.momentum_pct, 2) = e.mom_2dp
        GROUP BY 1, 2, 3, 4
    """).fetchdf()
    con.close()
    actual["mom_2dp"] = actual["mom_2dp"].round(2)
    print(f"actual (ticker,event,session) rows: {len(actual)}")

    actual.to_parquet(CACHE_PARQUET, index=False)
    print(f"cached full actual-sessions result to {CACHE_PARQUET} for T5 reuse (avoids a second full-table pass)")

    actual_by_event = actual.groupby(["ticker", "event_date_canonical", "mom_2dp"])["session_date"].apply(set).to_dict()

    records = []
    for _, row in cohort.iterrows():
        ticker, d, mom = row["ticker"], row["event_date_canonical"], row["mom_2dp"]
        key = (ticker, d, mom)
        if d not in session_pos:
            continue  # guard; should not happen for in-scope events
        i0 = session_pos[d]
        expected = {k: xnys_sessions[i0 + k] for k in OFFSETS if 0 <= i0 + k < len(xnys_sessions)}
        actual_set = actual_by_event.get(key, set())
        present = {k: (v in actual_set) for k, v in expected.items()}
        missing_offsets = sorted(k for k, p in present.items() if not p)
        bitmap = "".join("1" if present.get(k, False) else "0" for k in OFFSETS)

        records.append({
            "ticker": ticker, "event_day": d, "momentum_pct": mom,
            "bitmap": bitmap, "missing_offsets": missing_offsets,
            "n_missing": len(missing_offsets),
            "expected_t_minus_3": expected.get(-3),
            "expected_t_plus_3": expected.get(3),
        })

    df = pd.DataFrame(records)
    df.to_parquet(OUT_PARQUET, index=False)

    bitmap_counts = df["bitmap"].value_counts()
    print(f"\n{len(df)} cohort events bitmapped; {len(bitmap_counts)} distinct patterns")
    print(bitmap_counts.head(10))

    if len(df) != n_cohort:
        print(f"\n*** WARNING: bitmapped {len(df)} events but cohort is {n_cohort} - some cohort events missing session_pos guard hit ***")


if __name__ == "__main__":
    main()
