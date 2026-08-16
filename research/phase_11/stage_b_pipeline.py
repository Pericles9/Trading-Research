"""Phase 11 Stage B pipeline - the quote-metrics cache builder.

One event-partitioned pass. Used by T5a on dev v4 for timing, then by T5b on the
detection universe. Identical SQL both times, so the timing extrapolates.

Conventions fixed at the T4 gate:
  D16  reference midpoint = contemporaneous consolidated best quote at delta = 0
       on the sip_timestamp basis; sequence_number is the secondary ASOF key.
  D17  exclude crossed / null / non-positive / one-side-missing / zero-size.
       LOCKED IS CARRIED.
  D19  every spread and cost carried in BOTH basis points and cents.

Grain: event x offset x session-minute x segment, T=0 session only.
`offset` is the ALIGNMENT offset, a single value (0) under D16. The column is
kept so the key matches the T5c integrity contract and so a later phase can add
rungs without a schema change. T=0 only because every Stage B measurement (T6 at
det+latency, T7 exits through t0_close, T8 impact windows) lives on the event
day, and D19 bars a baseline session from standing in as a cost proxy anyway.

Lee & Ready (1991): quote rule against the contemporaneous midpoint, tick-rule
fallback on midpoint-equal prints. The 5-second lag rule is NOT applied - on
nanosecond data the contemporaneous quote signs best, and T3 measured the
at-or-inside share peaking in a plateau containing delta = 0.
"""
from __future__ import annotations

import time

ORIGIN = "04:00:00"          # minute_index origin, ET (Phase 8/9 convention)

# D17. Locked (bid = ask) is deliberately absent from this predicate.
EXCL = ("(bid_price IS NULL OR ask_price IS NULL OR bid_price <= 0 OR ask_price <= 0 "
        "OR bid_size IS NULL OR bid_size = 0 OR ask_size IS NULL OR ask_size = 0 "
        "OR bid_price > ask_price)")

_SEG = """CASE WHEN sb.is_session IS NOT TRUE       THEN 'non_session'
               WHEN x.et_ts::TIME < TIME '04:00:00' THEN 'outside_early'
               WHEN x.et_ts < sb.rth_open           THEN 'premarket'
               WHEN x.et_ts < sb.rth_close          THEN 'rth'
               WHEN x.et_ts::TIME < TIME '20:00:00' THEN 'post'
               ELSE 'outside_late' END"""

_SEGEND = """CASE WHEN sb.is_session IS NOT TRUE       THEN NULL
                  WHEN x.et_ts::TIME < TIME '04:00:00' THEN x.et_ts::DATE + TIME '04:00:00'
                  WHEN x.et_ts < sb.rth_open           THEN sb.rth_open
                  WHEN x.et_ts < sb.rth_close          THEN sb.rth_close
                  WHEN x.et_ts::TIME < TIME '20:00:00' THEN x.et_ts::DATE + TIME '20:00:00'
                  ELSE NULL END"""


def _labelled(table: str, cols: str, where: str) -> str:
    return f"""
      SELECT x.ticker, x.event_date, {_SEG} AS segment,
             CAST(date_diff('minute', x.et_ts::DATE + TIME '{ORIGIN}', x.et_ts)
                  AS INTEGER) AS minute_index,
             epoch_ns(({_SEGEND}) AT TIME ZONE 'America/New_York') AS seg_end_ns,
             {cols}
      FROM (SELECT *, et(sip_timestamp) AS et_ts FROM {table} WHERE {where}) x
      LEFT JOIN sb ON sb.session_date = x.et_ts::DATE
      WHERE x.et_ts::DATE = x.event_date
        AND {_SEG} IN ('premarket', 'rth', 'post')
    """


def build_cache(con, quotes_tbl: str, trades_tbl: str, where: str,
                out_table: str = "event_quote_metrics_v1") -> float:
    """Materialise the cache into `out_table`. Returns wall seconds.

    Caller must have created `sb` (session bounds) and the `et()` macro.
    """
    t0 = time.perf_counter()

    # ---- quotes: prevailing duration, exclusion flag, BBO-change marker ----
    con.execute(f"""
        CREATE OR REPLACE TEMP TABLE _q AS
        SELECT *,
               (bid_price + ask_price) / 2.0 AS mid,
               ask_price - bid_price         AS spread_dollars,
               GREATEST(0, LEAST(COALESCE(LEAD(sip_timestamp) OVER w, seg_end_ns),
                                 seg_end_ns) - sip_timestamp) AS dur_ns,
               CASE WHEN bid_price IS NOT DISTINCT FROM LAG(bid_price) OVER w
                     AND ask_price IS NOT DISTINCT FROM LAG(ask_price) OVER w
                    THEN 0 ELSE 1 END AS is_bbo_change
        FROM (
          SELECT *, {EXCL} AS excluded, (bid_price = ask_price) AS is_locked
          FROM ({_labelled(quotes_tbl,
                           'x.bid_price, x.ask_price, x.bid_size, x.ask_size, '
                           'x.sip_timestamp, x.sequence_number', where)})
        )
        WINDOW w AS (PARTITION BY ticker, event_date, segment
                     ORDER BY sip_timestamp, sequence_number)
    """)

    # ---- per-minute quote aggregates (D19: both units) ---------------------
    con.execute("""
        CREATE OR REPLACE TEMP TABLE _qm AS
        SELECT ticker, event_date, 0 AS offset_ns, minute_index, segment,
               COUNT(*)                                          AS n_quotes,
               SUM(dur_ns)                                       AS dur_ns_total,
               SUM(is_bbo_change)                                AS n_bbo_changes,
               SUM(CASE WHEN excluded THEN dur_ns ELSE 0 END)::DOUBLE
                   / NULLIF(SUM(dur_ns), 0)                      AS unusable_time_share,
               SUM(CASE WHEN is_locked AND NOT excluded THEN dur_ns ELSE 0 END)::DOUBLE
                   / NULLIF(SUM(dur_ns), 0)                      AS locked_time_share,
               SUM(CASE WHEN NOT excluded THEN spread_dollars * dur_ns END)
                   / NULLIF(SUM(CASE WHEN NOT excluded THEN dur_ns END), 0)
                                                                 AS tw_spread_dollars,
               SUM(CASE WHEN NOT excluded THEN 10000.0 * spread_dollars / mid * dur_ns END)
                   / NULLIF(SUM(CASE WHEN NOT excluded THEN dur_ns END), 0)
                                                                 AS tw_spread_bp,
               SUM(CASE WHEN NOT excluded THEN mid * dur_ns END)
                   / NULLIF(SUM(CASE WHEN NOT excluded THEN dur_ns END), 0) AS tw_mid
        FROM _q GROUP BY 1, 2, 3, 4, 5
    """)

    # ---- trades signed against the contemporaneous non-excluded quote ------
    con.execute(f"""
        CREATE OR REPLACE TEMP TABLE _t AS
        SELECT t.ticker, t.event_date, t.segment, t.minute_index, t.sip_timestamp,
               t.price, t.size, q.mid, q.bid_price, q.ask_price,
               q.run_start_ns,
               CASE WHEN q.mid IS NULL              THEN NULL
                    WHEN t.price > q.mid            THEN  1
                    WHEN t.price < q.mid            THEN -1
                    ELSE NULL END                   AS sign_quote
        FROM ({_labelled(trades_tbl, 'x.price, x.size, x.sip_timestamp, '
                                     'x.sequence_number', where)}) t
        ASOF LEFT JOIN (
          SELECT ticker, event_date, segment, sip_timestamp, mid, bid_price, ask_price,
                 -- MAX, not MIN: the start of the CURRENT stale run is the MOST RECENT
                 -- BBO change at or before this quote. MIN would give the first change
                 -- of the whole segment and report an age of hours.
                 MAX(sip_timestamp) FILTER (is_bbo_change = 1)
                   OVER (PARTITION BY ticker, event_date, segment
                         ORDER BY sip_timestamp, sequence_number
                         ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS run_start_ns
          FROM _q WHERE NOT excluded
        ) q
          ON t.ticker = q.ticker AND t.event_date = q.event_date
         AND t.segment = q.segment
         AND t.sip_timestamp >= q.sip_timestamp
    """)

    # Tick-rule fallback for midpoint-equal prints; unclassifiable stays NULL.
    con.execute("""
        CREATE OR REPLACE TEMP TABLE _t2 AS
        SELECT *, COALESCE(sign_quote, CASE WHEN price > prev_diff THEN 1
                                            WHEN price < prev_diff THEN -1 END) AS sgn
        FROM (
          SELECT *, LAST_VALUE(prev_px IGNORE NULLS) OVER (
                      PARTITION BY ticker, event_date, segment
                      ORDER BY sip_timestamp
                      ROWS BETWEEN UNBOUNDED PRECEDING AND 1 PRECEDING) AS prev_diff
          FROM (
            SELECT *, CASE WHEN price IS DISTINCT FROM
                                LAG(price) OVER (PARTITION BY ticker, event_date, segment
                                                 ORDER BY sip_timestamp)
                           THEN price END AS prev_px
            FROM _t
          )
        )
    """)

    con.execute("""
        CREATE OR REPLACE TEMP TABLE _tm AS
        SELECT ticker, event_date, 0 AS offset_ns, minute_index, segment,
               COUNT(*)                                              AS n_trades,
               SUM(size)                                             AS sum_size,
               SUM(CASE WHEN mid IS NOT NULL THEN abs(price - mid) * size END)
                                                                     AS sum_abs_p_minus_m_size,
               SUM(CASE WHEN sgn IS NOT NULL THEN size END)          AS sum_size_classified,
               SUM(CASE WHEN sgn IS NOT NULL THEN sgn * size END)    AS signed_volume,
               COUNT(*) FILTER (sgn IS NULL)                         AS n_unclassifiable,
               COUNT(*) FILTER (mid IS NULL)                         AS n_no_quote,
               QUANTILE_CONT(sip_timestamp - run_start_ns, 0.5)      AS bbo_age_at_trade_p50,
               QUANTILE_CONT(sip_timestamp - run_start_ns, 0.95)     AS bbo_age_at_trade_p95,
               AVG(CASE WHEN sip_timestamp - run_start_ns > 1e9 THEN 1.0 ELSE 0.0 END)
                                                                     AS trade_share_age_gt_1s,
               AVG(CASE WHEN sip_timestamp - run_start_ns > 6e10 THEN 1.0 ELSE 0.0 END)
                                                                     AS trade_share_age_gt_60s
        FROM _t2 GROUP BY 1, 2, 3, 4, 5
    """)

    # ---- T4c tie audit, emitted from THIS scan (Cooper option (ii), 2026-08-16) ----
    # arg_min/arg_max(price, sip_timestamp) is deterministic only where the extremum
    # timestamp is unique within the bar. Where it is shared AND the tied prints differ
    # in price, first_price/last_price are arbitrary among the tied set - with no
    # ordering error anywhere in the code. Only AFFECTED bars are kept; absence from
    # this table means the bar is unaffected. Totals travel in the JSON.
    con.execute("""
        CREATE OR REPLACE TEMP TABLE _tie AS
        SELECT ticker, event_date, segment, minute_index, n_trades,
               n_at_min, n_at_max, px_range_at_min, px_range_at_max,
               GREATEST(px_range_at_min, px_range_at_max)                AS px_range_max,
               GREATEST(px_range_at_min, px_range_at_max) * 100.0        AS px_range_cents,
               10000.0 * GREATEST(px_range_at_min, px_range_at_max)
                   / NULLIF(bar_mid_px, 0)                              AS px_range_bp
        FROM (
          SELECT ticker, event_date, segment, minute_index,
                 COUNT(*)                                               AS n_trades,
                 COUNT(*) FILTER (sip_timestamp = min_ts)               AS n_at_min,
                 COUNT(*) FILTER (sip_timestamp = max_ts)               AS n_at_max,
                 MAX(price) FILTER (sip_timestamp = min_ts)
                   - MIN(price) FILTER (sip_timestamp = min_ts)         AS px_range_at_min,
                 MAX(price) FILTER (sip_timestamp = max_ts)
                   - MIN(price) FILTER (sip_timestamp = max_ts)         AS px_range_at_max,
                 (MAX(price) + MIN(price)) / 2.0                        AS bar_mid_px
          FROM (
            SELECT *,
                   MIN(sip_timestamp) OVER b AS min_ts,
                   MAX(sip_timestamp) OVER b AS max_ts
            FROM _t2
            WINDOW b AS (PARTITION BY ticker, event_date, segment, minute_index)
          )
          GROUP BY 1, 2, 3, 4
        )
        WHERE n_at_min >= 2 OR n_at_max >= 2
    """)

    con.execute(f"""
        CREATE OR REPLACE TABLE {out_table} AS
        SELECT COALESCE(q.ticker, t.ticker)             AS ticker,
               COALESCE(q.event_date, t.event_date)     AS event_date,
               COALESCE(q.offset_ns, t.offset_ns)       AS offset_ns,
               COALESCE(q.minute_index, t.minute_index) AS minute_index,
               COALESCE(q.segment, t.segment)           AS segment,
               q.n_quotes, q.dur_ns_total, q.n_bbo_changes, q.unusable_time_share,
               q.locked_time_share, q.tw_spread_dollars, q.tw_spread_bp, q.tw_mid,
               t.n_trades, t.sum_size, t.sum_abs_p_minus_m_size, t.sum_size_classified,
               t.signed_volume, t.n_unclassifiable, t.n_no_quote,
               t.bbo_age_at_trade_p50, t.bbo_age_at_trade_p95,
               t.trade_share_age_gt_1s, t.trade_share_age_gt_60s
        FROM _qm q
        FULL OUTER JOIN _tm t
          ON q.ticker = t.ticker AND q.event_date = t.event_date
         AND q.offset_ns = t.offset_ns AND q.minute_index = t.minute_index
         AND q.segment = t.segment
    """)
    return time.perf_counter() - t0
