"""
Phase 6 - session spine + minute-bar builder. Shared code path between the
dev-tier smoke test (T2, against filtered_trades_dev_v4) and the single
budgeted full pass (T3, against filtered_trades) - the point of T2 is to
verify this exact code before it is allowed to touch the 4.95B-row table.

Session spine: for each event (ticker, event_date_canonical, momentum_pct)
and each offset in config["offsets"], the expected session's calendar date
(XNYS arithmetic, same derivation as research/phase_5/t2_trades_bitmap.py)
plus that session's actual market_open/market_close (pandas_market_calendars
schedule - half-days are NOT assumed, they come from the schedule itself).
market_open/close are tz-aware UTC; .timestamp() gives the same UTC-epoch-
seconds basis as sip_timestamp/1e9 (session_date_derivation in
config/phase_6.json), so no further tz handling is needed downstream.

The spine's offset column is named session_offset, not offset - "offset"
is a reserved keyword in DuckDB SQL (OFFSET clause) and breaks unquoted
in a SELECT list.

Minute-bar aggregation is ONE single SQL pass over the trades table: the
join assigns every trade row to (event, offset) via an exact calendar-date
match (never a folder-presence or timestamp-range join), computes
in_session and minute_index per row, and GROUPs BY including in_session -
this way both the in-session bars AND the excluded (pre/post-session)
row counts come out of the same scan, so a second full-table pass is never
needed to get the excluded-row-share statistic (escalation row 7 allows
exactly one full pass over filtered_trades).

first_price/last_price (arg_min/arg_max on sip_timestamp) are both kept
per minute even though the phase prompt's bar-column list names only
last_price explicitly - first_price is needed to read "open price = first
in-session print" (T4c) directly off minute 0 of each event/offset without
a second pass, symmetric with the already-specified last_price/arg_max
pattern. Logged as a decision, not a reinterpretation of any measurement
formula.
"""
from __future__ import annotations

import time

import pandas as pd
import pandas_market_calendars as mcal


def build_session_spine(events: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    """events: DataFrame with ticker, event_date_canonical (any date-like), momentum_pct.
    Returns one row per (event, offset in derivation range): ticker, event_date_canonical
    (as datetime.date), momentum_pct, session_offset, session_date (datetime.date),
    session_open_epoch, session_close_epoch (float, UTC epoch seconds)."""
    cal_cfg = cfg["session_calendar"]
    offsets = cfg["offsets"]

    xnys = mcal.get_calendar(cal_cfg["calendar_code"])
    schedule = xnys.schedule(
        start_date=cal_cfg["derivation_range"]["start"],
        end_date=cal_cfg["derivation_range"]["end"],
    )
    sessions = pd.DatetimeIndex(schedule.index).normalize()
    session_pos = {d: i for i, d in enumerate(sessions)}
    opens = schedule["market_open"].to_numpy()
    closes = schedule["market_close"].to_numpy()

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
            o = pd.Timestamp(opens[j])
            c = pd.Timestamp(closes[j])
            records.append((
                row.ticker, d, row.momentum_pct, off,
                sessions[j].date(), o.timestamp(), c.timestamp(),
            ))

    spine = pd.DataFrame.from_records(
        records,
        columns=["ticker", "event_date_canonical", "momentum_pct", "session_offset",
                 "session_date", "session_open_epoch", "session_close_epoch"],
    )
    return spine


_AGG_SQL_TEMPLATE = """
CREATE TEMPORARY TABLE _t6_minute_agg_all AS
SELECT ticker, event_date_canonical, momentum_pct, session_offset, in_session, minute_index,
       COUNT(*) AS n_trades,
       SUM(size) AS volume,
       SUM(price * size) AS notional,
       MAX(price) AS high,
       MIN(price) AS low,
       arg_min(price, sip_timestamp) AS first_price,
       arg_max(price, sip_timestamp) AS last_price,
       MIN(sip_timestamp) AS first_trade_ts,
       MAX(sip_timestamp) AS last_trade_ts
FROM (
    SELECT t.ticker, t.event_date AS event_date_canonical, ROUND(t.momentum_pct, 2) AS momentum_pct,
           ss.session_offset,
           (t.sip_timestamp / 1e9 >= ss.session_open_epoch
            AND t.sip_timestamp / 1e9 <  ss.session_close_epoch) AS in_session,
           CAST(FLOOR((t.sip_timestamp / 1e9 - ss.session_open_epoch) / 60) AS INTEGER) AS minute_index,
           t.price, t.size, t.sip_timestamp
    FROM {trades_table} t
    JOIN _t6_session_spine ss
      ON t.ticker = ss.ticker
     AND t.event_date = ss.event_date_canonical
     AND ROUND(t.momentum_pct, 2) = ROUND(ss.momentum_pct, 2)
     AND CAST(TO_TIMESTAMP(t.sip_timestamp / 1e9) AS DATE) = ss.session_date
) sub
GROUP BY ticker, event_date_canonical, momentum_pct, session_offset, in_session, minute_index
"""


def build_minute_bars(con, trades_table: str, spine: pd.DataFrame, out_table: str) -> dict:
    """Single pass over trades_table. Creates/replaces out_table (in-session bars
    only, permanent) and returns excluded-row-share stats for offset=0 plus timing."""
    con.execute("DROP TABLE IF EXISTS _t6_session_spine")
    con.register("_t6_session_spine_df", spine)
    con.execute("CREATE TEMPORARY TABLE _t6_session_spine AS SELECT * FROM _t6_session_spine_df")
    con.unregister("_t6_session_spine_df")

    con.execute("DROP TABLE IF EXISTS _t6_minute_agg_all")
    t0 = time.perf_counter()
    con.execute(_AGG_SQL_TEMPLATE.format(trades_table=trades_table))
    elapsed = time.perf_counter() - t0

    con.execute(f"DROP TABLE IF EXISTS {out_table}")
    con.execute(f"""
        CREATE TABLE {out_table} AS
        SELECT ticker, event_date_canonical, momentum_pct, session_offset, minute_index,
               n_trades, volume,
               notional / NULLIF(volume, 0) AS vwap,
               high, low, first_price, last_price, first_trade_ts, last_trade_ts
        FROM _t6_minute_agg_all
        WHERE in_session
    """)

    excluded_t0 = con.execute("""
        SELECT ticker, event_date_canonical, momentum_pct,
               SUM(n_trades) FILTER (in_session) AS n_in_session,
               SUM(n_trades) FILTER (NOT in_session) AS n_excluded,
               SUM(n_trades) AS n_total
        FROM _t6_minute_agg_all
        WHERE session_offset = 0
        GROUP BY 1, 2, 3
    """).fetchdf()

    con.execute("DROP TABLE IF EXISTS _t6_minute_agg_all")
    con.execute("DROP TABLE IF EXISTS _t6_session_spine")

    return {"elapsed_seconds": elapsed, "excluded_t0": excluded_t0}


def verify_bars(con, bars_table: str, spine: pd.DataFrame) -> dict:
    """Integrity checks: minute indices within [0, session_length_minutes), no
    duplicate (event,offset,minute) keys."""
    dup = con.execute(f"""
        SELECT COUNT(*) FROM (
            SELECT ticker, event_date_canonical, momentum_pct, session_offset, minute_index, COUNT(*) AS c
            FROM {bars_table}
            GROUP BY 1,2,3,4,5
            HAVING COUNT(*) > 1
        )
    """).fetchone()[0]

    spine_sql = spine.assign(
        session_minutes=lambda d: (d["session_close_epoch"] - d["session_open_epoch"]) / 60.0
    )[["ticker", "event_date_canonical", "momentum_pct", "session_offset", "session_minutes"]]

    con.execute("DROP TABLE IF EXISTS _t6_verify_spine")
    con.register("_t6_verify_spine_df", spine_sql)
    con.execute("CREATE TEMPORARY TABLE _t6_verify_spine AS SELECT * FROM _t6_verify_spine_df")
    con.unregister("_t6_verify_spine_df")
    out_of_session = con.execute(f"""
        SELECT COUNT(*) FROM {bars_table} b
        JOIN _t6_verify_spine s
          ON b.ticker = s.ticker AND b.event_date_canonical = s.event_date_canonical
         AND ROUND(b.momentum_pct, 2) = ROUND(s.momentum_pct, 2) AND b.session_offset = s.session_offset
        WHERE b.minute_index < 0 OR b.minute_index >= CEIL(s.session_minutes)
    """).fetchone()[0]
    con.execute("DROP TABLE IF EXISTS _t6_verify_spine")

    return {"duplicate_keys": int(dup), "out_of_session_minute_indices": int(out_of_session)}
