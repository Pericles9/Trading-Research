"""
Phase 6b - extended-day session spine + minute-bar builder. Shared code
path between the dev-tier smoke test (T2, filtered_trades_dev_v4) and
the single budgeted full pass (T3, filtered_trades).

Segment bounds fallback (measured fact, config/phase_6b.json's
pre_post_availability_check): installed pandas_market_calendars 5.4.0's
XNYS calendar exposes market_open/market_close only - no pre/post
columns. premarket = [04:00 ET, RTH open), rth = [RTH open, RTH close),
post = [RTH close, post end), post end = 20:00 ET normal / 17:00 ET on
an early-close date (RTH close < 16:00 ET).

Timezone rule (D3, docs/Universe-Decisions.md): session-date and segment
assignment are computed in America/New_York via DuckDB's ICU extension
(AT TIME ZONE), DST-aware - never by casting the UTC sip_timestamp to a
date (Phase 6's convention, which misassigns EST-winter post-market
prints after 19:00 ET to the next calendar day). The legacy UTC-cast
date is also computed alongside, purely so T2 can measure how often the
two disagree (the timezone cross-check) - it plays no role in bar
assignment.

Single-pass design is identical in spirit to Phase 6's build_minute_bars.py:
one GROUP BY (including in_window and segment) over the trades table
gives both the extended-day bars and the excluded-row-share stat from
one scan.
"""
from __future__ import annotations

import time
from datetime import time as dtime

import pandas as pd
import pandas_market_calendars as mcal

EARLY_CLOSE_THRESHOLD = dtime(16, 0, 0)
PREMARKET_START = dtime(4, 0, 0)
NORMAL_POST_END = dtime(20, 0, 0)
EARLY_CLOSE_POST_END = dtime(17, 0, 0)


def build_session_spine_v2(events: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    """events: DataFrame with ticker, event_date_canonical, momentum_pct.
    Returns one row per (event, offset in range): ticker, event_date_canonical
    (datetime), momentum_pct, session_offset, session_date (date),
    premarket_start_et, rth_open_et, rth_close_et, post_end_et (naive
    datetimes representing America/New_York wall clock), is_early_close."""
    cal_cfg = cfg["session_calendar"]
    offsets = cfg["offsets"]

    xnys = mcal.get_calendar(cal_cfg["calendar_code"])
    schedule = xnys.schedule(
        start_date=cal_cfg["derivation_range"]["start"],
        end_date=cal_cfg["derivation_range"]["end"],
    )
    sessions = pd.DatetimeIndex(schedule.index).normalize()
    session_pos = {d: i for i, d in enumerate(sessions)}
    rth_open_et = schedule["market_open"].dt.tz_convert("America/New_York").dt.tz_localize(None).to_numpy()
    rth_close_et = schedule["market_close"].dt.tz_convert("America/New_York").dt.tz_localize(None).to_numpy()

    ev = events[["ticker", "event_date_canonical", "momentum_pct"]].copy()
    ev["event_date_canonical"] = pd.to_datetime(ev["event_date_canonical"])

    records = []
    for row in ev.itertuples(index=False):
        d = row.event_date_canonical
        i0 = session_pos.get(d)
        if i0 is None:
            continue
        for off in offsets:
            j = i0 + off
            if j < 0 or j >= len(sessions):
                continue
            sess_date = sessions[j]
            o_et = pd.Timestamp(rth_open_et[j])
            c_et = pd.Timestamp(rth_close_et[j])
            is_early = c_et.time() < EARLY_CLOSE_THRESHOLD
            premarket_start = pd.Timestamp.combine(sess_date.date(), PREMARKET_START)
            post_end = pd.Timestamp.combine(sess_date.date(), EARLY_CLOSE_POST_END if is_early else NORMAL_POST_END)
            records.append((
                row.ticker, d, row.momentum_pct, off, sess_date.date(),
                premarket_start, o_et, c_et, post_end, is_early,
            ))

    spine = pd.DataFrame.from_records(
        records,
        columns=["ticker", "event_date_canonical", "momentum_pct", "session_offset", "session_date",
                 "premarket_start_et", "rth_open_et", "rth_close_et", "post_end_et", "is_early_close"],
    )
    return spine


_AGG_SQL_TEMPLATE = """
CREATE TEMPORARY TABLE _t6b_minute_agg_all AS
SELECT ticker, event_date_canonical, momentum_pct, session_offset, in_window, segment, minute_index,
       COUNT(*) AS n_trades,
       SUM(size) AS volume,
       SUM(price * size) AS notional,
       MAX(price) AS high,
       MIN(price) AS low,
       arg_min(price, sip_timestamp) AS first_price,
       arg_max(price, sip_timestamp) AS last_price,
       MIN(sip_timestamp) AS first_trade_ts,
       MAX(sip_timestamp) AS last_trade_ts,
       SUM(CASE WHEN et_date != utc_date THEN 1 ELSE 0 END) AS n_et_vs_utc_date_mismatch,
       -- A8.2 duplicate-print counters, computed in this same pass (no extra scan).
       -- A duplicate print shares an identical sip_timestamp, so it always falls in the
       -- same (event,offset,minute) bar - a per-bar strict/loose distinct-count captures
       -- every collision with no cross-minute leakage. n_dup = extra rows beyond distinct.
       COUNT(*) - COUNT(DISTINCT (sip_timestamp, price, size, sequence_number)) AS n_dup_strict,
       COUNT(*) - COUNT(DISTINCT (sip_timestamp, price, size)) AS n_dup_loose
FROM (
    SELECT t.ticker, t.event_date AS event_date_canonical, ROUND(t.momentum_pct, 2) AS momentum_pct,
           ss.session_offset,
           (et_ts >= ss.premarket_start_et AND et_ts < ss.post_end_et) AS in_window,
           CASE WHEN et_ts < ss.rth_open_et THEN 'premarket'
                WHEN et_ts < ss.rth_close_et THEN 'rth'
                ELSE 'post' END AS segment,
           CAST(FLOOR(EPOCH(et_ts - ss.premarket_start_et) / 60) AS INTEGER) AS minute_index,
           t.price, t.size, t.sip_timestamp, t.sequence_number, et_date, utc_date
    FROM (
        SELECT *,
               TO_TIMESTAMP(sip_timestamp / 1e9) AT TIME ZONE 'America/New_York' AS et_ts,
               CAST(TO_TIMESTAMP(sip_timestamp / 1e9) AT TIME ZONE 'America/New_York' AS DATE) AS et_date,
               CAST(TO_TIMESTAMP(sip_timestamp / 1e9) AS DATE) AS utc_date
        FROM {trades_table}
    ) t
    JOIN _t6b_session_spine ss
      ON t.ticker = ss.ticker
     AND t.event_date = ss.event_date_canonical
     AND ROUND(t.momentum_pct, 2) = ROUND(ss.momentum_pct, 2)
     AND t.et_date = ss.session_date
) sub
GROUP BY ticker, event_date_canonical, momentum_pct, session_offset, in_window, segment, minute_index
"""


def build_minute_bars_v2(con, trades_table: str, spine: pd.DataFrame, out_table: str) -> dict:
    """Single pass over trades_table (after LOAD icu). Creates/replaces out_table
    (in-window bars only, segment-tagged) and returns excluded-row-share stats
    for offset=0 plus the ET-vs-UTC date mismatch count, plus timing."""
    con.execute("INSTALL icu")
    con.execute("LOAD icu")

    con.execute("DROP TABLE IF EXISTS _t6b_session_spine")
    con.register("_t6b_session_spine_df", spine)
    con.execute("CREATE TEMPORARY TABLE _t6b_session_spine AS SELECT * FROM _t6b_session_spine_df")
    con.unregister("_t6b_session_spine_df")

    con.execute("DROP TABLE IF EXISTS _t6b_minute_agg_all")
    t0 = time.perf_counter()
    con.execute(_AGG_SQL_TEMPLATE.format(trades_table=trades_table))
    elapsed = time.perf_counter() - t0

    con.execute(f"DROP TABLE IF EXISTS {out_table}")
    con.execute(f"""
        CREATE TABLE {out_table} AS
        SELECT ticker, event_date_canonical, momentum_pct, session_offset, segment, minute_index,
               n_trades, volume,
               notional / NULLIF(volume, 0) AS vwap,
               high, low, first_price, last_price, first_trade_ts, last_trade_ts
        FROM _t6b_minute_agg_all
        WHERE in_window
    """)

    # COALESCE both conditional sums to 0 - SQL SUM() FILTER over zero matching
    # rows returns NULL, not 0 (e.g. an event with no excluded rows at all would
    # otherwise show NaN, not 0, for n_excluded).
    excluded_t0 = con.execute("""
        SELECT ticker, event_date_canonical, momentum_pct,
               COALESCE(SUM(n_trades) FILTER (in_window), 0) AS n_in_window,
               COALESCE(SUM(n_trades) FILTER (NOT in_window), 0) AS n_excluded,
               SUM(n_trades) AS n_total
        FROM _t6b_minute_agg_all
        WHERE session_offset = 0
        GROUP BY 1, 2, 3
    """).fetchdf()

    tz_mismatch = con.execute("""
        SELECT SUM(n_et_vs_utc_date_mismatch) AS n_mismatch, SUM(n_trades) AS n_total_rows
        FROM _t6b_minute_agg_all
    """).fetchdf()

    # A8.2 per-event duplicate-print rate (strict key), over ALL offsets/segments in the
    # scan - computed from the same temp table, no extra pass over the trades table.
    dup_prints = con.execute("""
        SELECT ticker, event_date_canonical, momentum_pct,
               COALESCE(SUM(n_dup_strict), 0) AS n_dup_strict,
               COALESCE(SUM(n_dup_loose), 0) AS n_dup_loose,
               SUM(n_trades) AS n_prints,
               COALESCE(SUM(n_dup_strict), 0)::DOUBLE / NULLIF(SUM(n_trades), 0) AS dup_strict_rate
        FROM _t6b_minute_agg_all
        GROUP BY 1, 2, 3
    """).fetchdf()

    con.execute("DROP TABLE IF EXISTS _t6b_minute_agg_all")
    con.execute("DROP TABLE IF EXISTS _t6b_session_spine")

    return {"elapsed_seconds": elapsed, "excluded_t0": excluded_t0, "tz_mismatch": tz_mismatch,
            "dup_prints": dup_prints}


def verify_bars_v2(con, bars_table: str, spine: pd.DataFrame) -> dict:
    """Integrity checks: minute indices within [0, day_length_minutes), no
    duplicate (event,offset,minute) keys, segment matches recomputed ET bounds."""
    dup = con.execute(f"""
        SELECT COUNT(*) FROM (
            SELECT ticker, event_date_canonical, momentum_pct, session_offset, minute_index, COUNT(*) AS c
            FROM {bars_table}
            GROUP BY 1,2,3,4,5
            HAVING COUNT(*) > 1
        )
    """).fetchone()[0]

    spine_sql = spine.assign(
        day_length_minutes=lambda d: (d["post_end_et"] - d["premarket_start_et"]).dt.total_seconds() / 60.0
    )[["ticker", "event_date_canonical", "momentum_pct", "session_offset", "day_length_minutes"]]

    con.execute("DROP TABLE IF EXISTS _t6b_verify_spine")
    con.register("_t6b_verify_spine_df", spine_sql)
    con.execute("CREATE TEMPORARY TABLE _t6b_verify_spine AS SELECT * FROM _t6b_verify_spine_df")
    con.unregister("_t6b_verify_spine_df")
    out_of_window = con.execute(f"""
        SELECT COUNT(*) FROM {bars_table} b
        JOIN _t6b_verify_spine s
          ON b.ticker = s.ticker AND b.event_date_canonical = s.event_date_canonical
         AND ROUND(b.momentum_pct, 2) = ROUND(s.momentum_pct, 2) AND b.session_offset = s.session_offset
        WHERE b.minute_index < 0 OR b.minute_index >= CEIL(s.day_length_minutes)
    """).fetchone()[0]
    con.execute("DROP TABLE IF EXISTS _t6b_verify_spine")

    bad_segment = con.execute(f"""
        SELECT COUNT(*) FROM {bars_table}
        WHERE segment NOT IN ('premarket', 'rth', 'post')
    """).fetchone()[0]

    return {"duplicate_keys": int(dup), "out_of_window_minute_indices": int(out_of_window), "bad_segment_labels": int(bad_segment)}
