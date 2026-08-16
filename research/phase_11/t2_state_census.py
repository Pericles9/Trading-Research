"""Phase 11 T2 - economically nonsensical state census (Holden & Jacobsen).

Census only. NO cleaning is applied and no quote state is excluded; the
exclusion rule is set by Cooper at the T4 gate (escalation row 19).

State definitions are Cooper's 2026-08-15 ruling, which imported the v2
three-way split over Amendment 1 A1-2's single union:

  state_hard_unusable = null price U non-positive price U one-side-missing
                        U crossed          -> no midpoint exists, or it is
                                              economically impossible.
                                              ESCALATION ROW 5 IS DEFINED HERE.
  state_degraded      = locked U zero-size, among rows NOT already hard
                        -> a midpoint exists and is computable.
  state_clean         = neither.

Per-state non-exclusive shares and the pairwise overlap matrix are also
reported (A1-2, retained), so the double-counting is visible rather than
inferred. A WIDE quote is not unusable - width is the measurement.

Clock-time weighting: each quote prevails from its own sip_timestamp until the
next quote, clipped at its segment boundary, so a premarket quote never credits
time to RTH. Ordering is always explicit (sip_timestamp, sequence_number), never
storage order (escalation row 19).

Dev v4 primary cohort only. Zero full-table passes (escalation row 12).
"""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))

import pandas as pd
from common import ARTIFACTS, connect, primary_events, session_bounds

OFFSETS = (0, -1, -3)

PRED = {
    "crossed":        "bid_price > ask_price",
    "locked":         "bid_price = ask_price",
    "null_price":     "bid_price IS NULL OR ask_price IS NULL",
    "nonpos_price":   "bid_price <= 0 OR ask_price <= 0",
    "one_side_miss":  "(bid_price IS NULL) <> (ask_price IS NULL)",
    "zero_bid_size":  "bid_size IS NULL OR bid_size = 0",
    "zero_ask_size":  "ask_size IS NULL OR ask_size = 0",
}
HARD = "(bid_price IS NULL OR ask_price IS NULL OR bid_price <= 0 OR ask_price <= 0 " \
       "OR bid_price > ask_price)"
DEGR = "(bid_price = ask_price OR bid_size IS NULL OR bid_size = 0 " \
       "OR ask_size IS NULL OR ask_size = 0)"


def day_offset_map(events: pd.DataFrame) -> pd.DataFrame:
    """(event_date, session_date) -> trading-day offset, from the pinned XNYS calendar."""
    import exchange_calendars as xcals

    cal = xcals.get_calendar("XNYS")
    rows = []
    for ed in sorted({pd.Timestamp(d) for d in events["event_date"]}):
        sess = cal.sessions_in_range(ed - pd.Timedelta(days=20), ed + pd.Timedelta(days=20))
        sess = [s.tz_localize(None) if s.tz else s for s in sess]
        if ed not in sess:
            continue
        i0 = sess.index(ed)
        for i, s in enumerate(sess):
            if abs(i - i0) <= 3:
                rows.append({"event_date": ed.date(), "session_date": s.date(),
                             "day_offset": i - i0})
    return pd.DataFrame(rows)


def build(con) -> None:
    ev = primary_events(con)
    dates = con.execute(
        "SELECT DISTINCT et(sip_timestamp)::DATE d FROM mom.filtered_quotes_dev_v4 "
        "WHERE dev_cohort='primary'"
    ).df()["d"]
    con.register("sb_df", session_bounds(dates))
    con.register("dayoff_df", day_offset_map(ev))
    con.execute("CREATE TABLE sb AS SELECT * FROM sb_df")
    con.execute("CREATE TABLE dayoff AS SELECT * FROM dayoff_df")

    # Segment label plus that segment's END, used to clip prevailing-quote duration.
    seg_sql = """
      CASE WHEN sb.is_session IS NOT TRUE            THEN 'non_session'
           WHEN q.et_ts::TIME < TIME '04:00:00'      THEN 'outside_early'
           WHEN q.et_ts < sb.rth_open                THEN 'premarket'
           WHEN q.et_ts < sb.rth_close               THEN 'rth'
           WHEN q.et_ts::TIME < TIME '20:00:00'      THEN 'post'
           ELSE 'outside_late' END
    """
    segend_sql = """
      CASE WHEN sb.is_session IS NOT TRUE            THEN NULL
           WHEN q.et_ts::TIME < TIME '04:00:00'      THEN q.et_ts::DATE + TIME '04:00:00'
           WHEN q.et_ts < sb.rth_open                THEN sb.rth_open
           WHEN q.et_ts < sb.rth_close               THEN sb.rth_close
           WHEN q.et_ts::TIME < TIME '20:00:00'      THEN q.et_ts::DATE + TIME '20:00:00'
           ELSE NULL END
    """
    con.execute(f"""
        CREATE TABLE q AS
        SELECT ticker, event_date, session_date, day_offset, segment,
               bid_price, ask_price, bid_size, ask_size,
               sip_timestamp, sequence_number,
               -- prevailing duration: to the next quote, clipped at the segment end
               GREATEST(0, LEAST(
                   COALESCE(LEAD(sip_timestamp) OVER w, seg_end_ns), seg_end_ns
               ) - sip_timestamp) AS dur_ns
        FROM (
          SELECT q.ticker, q.event_date, q.et_ts::DATE AS session_date, dof.day_offset,
                 {seg_sql} AS segment,
                 epoch_ns(({segend_sql}) AT TIME ZONE 'America/New_York') AS seg_end_ns,
                 q.bid_price, q.ask_price, q.bid_size, q.ask_size,
                 q.sip_timestamp, q.sequence_number
          FROM (SELECT *, et(sip_timestamp) AS et_ts
                FROM mom.filtered_quotes_dev_v4 WHERE dev_cohort='primary') q
          LEFT JOIN sb ON sb.session_date = q.et_ts::DATE
          LEFT JOIN dayoff dof ON dof.event_date = q.event_date AND dof.session_date = q.et_ts::DATE
        ) x
        WINDOW w AS (PARTITION BY ticker, event_date, session_date
                     ORDER BY sip_timestamp, sequence_number)
    """)
    # epoch_ns() of an ET wall-clock needs the same UTC re-anchoring the macro used.
    con.execute("""
        CREATE TABLE base AS
        SELECT * FROM q
        WHERE day_offset IN (0, -1, -3) AND segment IN ('premarket','rth','post')
    """)


def t2a(con) -> None:
    per_state = ",\n".join(
        f"SUM(CASE WHEN {p} THEN dur_ns ELSE 0 END)::DOUBLE / NULLIF(SUM(dur_ns),0) "
        f"AS time_{n}, AVG(CASE WHEN {p} THEN 1.0 ELSE 0.0 END) AS rows_{n}"
        for n, p in PRED.items()
    )
    con.execute(f"""
        CREATE TABLE t2a AS
        SELECT ticker, event_date, day_offset, segment,
               COUNT(*) AS n_quotes, SUM(dur_ns) AS total_dur_ns,
               SUM(CASE WHEN {HARD} THEN dur_ns ELSE 0 END)::DOUBLE
                   / NULLIF(SUM(dur_ns),0) AS time_hard_unusable,
               SUM(CASE WHEN NOT {HARD} AND {DEGR} THEN dur_ns ELSE 0 END)::DOUBLE
                   / NULLIF(SUM(dur_ns),0) AS time_degraded,
               SUM(CASE WHEN NOT {HARD} AND NOT {DEGR} THEN dur_ns ELSE 0 END)::DOUBLE
                   / NULLIF(SUM(dur_ns),0) AS time_clean,
               AVG(CASE WHEN {HARD} THEN 1.0 ELSE 0.0 END) AS rows_hard_unusable,
               AVG(CASE WHEN NOT {HARD} AND {DEGR} THEN 1.0 ELSE 0.0 END) AS rows_degraded,
               {per_state}
        FROM base GROUP BY 1,2,3,4
    """)
    # Pairwise overlap of the non-exclusive predicates, on clock time (T=0 RTH).
    names = list(PRED)
    pairs = ",\n".join(
        f"SUM(CASE WHEN ({PRED[a]}) AND ({PRED[b]}) THEN dur_ns ELSE 0 END)::DOUBLE"
        f" / NULLIF(SUM(dur_ns),0) AS ov_{a}__{b}"
        for i, a in enumerate(names) for b in names[i:]
    )
    con.execute(f"""
        CREATE TABLE t2a_overlap AS
        SELECT ticker, event_date, {pairs}
        FROM base WHERE day_offset = 0 AND segment = 'rth' GROUP BY 1,2
    """)


def t2b(con) -> None:
    """Run-length in clock time, T=0, for every individual state AND the two unions.

    A run is a maximal stretch of consecutive quotes (explicit sort) in the same
    state; its length is the summed prevailing duration. Reported per state so a
    2% share concentrated in one long run is distinguishable from a 2% share
    scattered across the session.
    """
    parts = []
    for name, pred in list(PRED.items()) + [("hard_unusable", HARD),
                                            ("degraded", f"NOT {HARD} AND {DEGR}")]:
        parts.append(f"""
        SELECT '{name}' AS state, ticker, event_date, segment,
               COUNT(*) AS n_runs, MAX(run_ns) AS max_run_ns,
               QUANTILE_CONT(run_ns, 0.5) AS p50_run_ns,
               QUANTILE_CONT(run_ns, 0.95) AS p95_run_ns,
               SUM(run_ns) AS total_run_ns
        FROM (
          SELECT ticker, event_date, segment, grp, SUM(dur_ns) AS run_ns
          FROM (
            SELECT *, SUM(CASE WHEN in_state <> prev_state OR prev_state IS NULL
                               THEN 1 ELSE 0 END) OVER w2 AS grp
            FROM (
              SELECT ticker, event_date, segment, dur_ns, sip_timestamp, sequence_number,
                     ({pred}) AS in_state, LAG(({pred})) OVER w AS prev_state
              FROM base WHERE day_offset = 0
              WINDOW w AS (PARTITION BY ticker, event_date, segment
                           ORDER BY sip_timestamp, sequence_number)
            ) a
            WINDOW w2 AS (PARTITION BY ticker, event_date, segment
                          ORDER BY sip_timestamp, sequence_number)
          ) b
          WHERE in_state GROUP BY 1,2,3,4
        ) r GROUP BY 1,2,3,4""")
    con.execute("CREATE TABLE t2b AS " + "\nUNION ALL\n".join(parts))

    con.execute(f"""
        CREATE TABLE t2b_hard_only AS
        SELECT ticker, event_date, segment,
               COUNT(*) AS n_runs,
               MAX(run_ns) AS max_run_ns,
               QUANTILE_CONT(run_ns, 0.5) AS p50_run_ns,
               QUANTILE_CONT(run_ns, 0.95) AS p95_run_ns,
               SUM(run_ns) AS total_run_ns
        FROM (
          SELECT ticker, event_date, segment, grp, SUM(dur_ns) AS run_ns
          FROM (
            SELECT *, SUM(CASE WHEN is_hard <> prev_hard OR prev_hard IS NULL
                               THEN 1 ELSE 0 END) OVER w2 AS grp
            FROM (
              SELECT ticker, event_date, segment, dur_ns, sip_timestamp, sequence_number,
                     {HARD} AS is_hard,
                     LAG({HARD}) OVER w AS prev_hard
              FROM base WHERE day_offset = 0
              WINDOW w AS (PARTITION BY ticker, event_date, segment
                           ORDER BY sip_timestamp, sequence_number)
            ) a
            WINDOW w2 AS (PARTITION BY ticker, event_date, segment
                          ORDER BY sip_timestamp, sequence_number)
          ) b
          WHERE is_hard GROUP BY 1,2,3,4
        ) r GROUP BY 1,2,3
    """)


def t2c_t2d(con) -> None:
    """Stale top-of-book runs, and quote-to-trade / inter-quote intervals."""
    # Age of the prevailing BBO (price pair) at each T=0 trade.
    con.execute("""
        CREATE TABLE bbo_runs AS
        SELECT ticker, event_date, session_date, segment, day_offset,
               MIN(sip_timestamp) AS run_start_ns,
               MAX(sip_timestamp) AS run_last_ns,
               SUM(dur_ns) AS run_ns, COUNT(*) AS n_quotes_in_run
        FROM (
          SELECT *, SUM(CASE WHEN bid_price IS DISTINCT FROM prev_b
                             OR ask_price IS DISTINCT FROM prev_a THEN 1 ELSE 0 END)
                    OVER (PARTITION BY ticker, event_date, session_date
                          ORDER BY sip_timestamp, sequence_number) AS grp
          FROM (
            SELECT *, LAG(bid_price) OVER w AS prev_b, LAG(ask_price) OVER w AS prev_a
            FROM base
            WINDOW w AS (PARTITION BY ticker, event_date, session_date
                         ORDER BY sip_timestamp, sequence_number)
          ) a
        ) b
        GROUP BY 1,2,3,4,5,grp
    """)
    con.execute("""
        CREATE TABLE t2c_runs AS
        SELECT ticker, event_date, segment, COUNT(*) n_runs,
               QUANTILE_CONT(run_ns, 0.5) p50_ns, QUANTILE_CONT(run_ns, 0.95) p95_ns,
               MAX(run_ns) max_ns, SUM(run_ns) total_ns
        FROM bbo_runs WHERE day_offset = 0 GROUP BY 1,2,3
    """)
    # Trades, segment-labelled, then ASOF to the run they land in.
    con.execute("""
        CREATE TABLE tr AS
        SELECT t.ticker, t.event_date, t.et_ts::DATE AS session_date, dof.day_offset,
               CASE WHEN sb.is_session IS NOT TRUE       THEN 'non_session'
                    WHEN t.et_ts::TIME < TIME '04:00:00' THEN 'outside_early'
                    WHEN t.et_ts < sb.rth_open           THEN 'premarket'
                    WHEN t.et_ts < sb.rth_close          THEN 'rth'
                    WHEN t.et_ts::TIME < TIME '20:00:00' THEN 'post'
                    ELSE 'outside_late' END AS segment,
               t.price, t.size, t.sip_timestamp
        FROM (SELECT *, et(sip_timestamp) AS et_ts
              FROM mom.filtered_trades_dev_v4 WHERE dev_cohort='primary') t
        LEFT JOIN sb ON sb.session_date = t.et_ts::DATE
        LEFT JOIN dayoff dof ON dof.event_date = t.event_date AND dof.session_date = t.et_ts::DATE
    """)
    con.execute("""
        CREATE TABLE t2c_trade_age AS
        SELECT t.ticker, t.event_date, t.segment,
               COUNT(*) n_trades,
               COUNT(r.run_start_ns) n_matched,
               QUANTILE_CONT(t.sip_timestamp - r.run_start_ns, 0.5) p50_age_ns,
               QUANTILE_CONT(t.sip_timestamp - r.run_start_ns, 0.95) p95_age_ns,
               AVG(CASE WHEN t.sip_timestamp - r.run_start_ns > 1e9 THEN 1.0 ELSE 0.0 END)
                   AS share_age_gt_1s,
               AVG(CASE WHEN t.sip_timestamp - r.run_start_ns > 6e10 THEN 1.0 ELSE 0.0 END)
                   AS share_age_gt_60s
        FROM tr t
        ASOF LEFT JOIN bbo_runs r
          ON t.ticker = r.ticker AND t.event_date = r.event_date
         AND t.session_date = r.session_date
         AND t.sip_timestamp >= r.run_start_ns
        WHERE t.day_offset = 0 AND t.segment IN ('premarket','rth','post')
        GROUP BY 1,2,3
    """)
    con.execute("""
        CREATE TABLE t2d AS
        SELECT q.ticker, q.event_date, q.day_offset, q.segment,
               q.n_quotes, COALESCE(t.n_trades, 0) AS n_trades,
               q.n_quotes::DOUBLE / NULLIF(t.n_trades, 0) AS quote_to_trade,
               q.p50_iq_ns, q.p95_iq_ns
        FROM (
          SELECT ticker, event_date, day_offset, segment, COUNT(*) n_quotes,
                 QUANTILE_CONT(dur_ns, 0.5) p50_iq_ns, QUANTILE_CONT(dur_ns, 0.95) p95_iq_ns
          FROM base GROUP BY 1,2,3,4
        ) q
        LEFT JOIN (
          SELECT ticker, event_date, day_offset, segment, COUNT(*) n_trades
          FROM tr WHERE day_offset IN (0,-1,-3) AND segment IN ('premarket','rth','post')
          GROUP BY 1,2,3,4
        ) t USING (ticker, event_date, day_offset, segment)
    """)


def t2e(con) -> None:
    """Quoted spread, event day vs T-1 / T-3. QUOTED, not effective (row 8/10)."""
    con.execute("""
        CREATE TABLE t2e AS
        SELECT ticker, event_date, day_offset, segment,
               SUM(dur_ns) AS dur_ns, COUNT(*) AS n_quotes,
               SUM((ask_price - bid_price) * dur_ns) / NULLIF(SUM(dur_ns),0)
                   AS tw_spread_dollars,
               SUM(10000.0 * (ask_price - bid_price)
                   / ((ask_price + bid_price) / 2.0) * dur_ns)
                   / NULLIF(SUM(dur_ns),0) AS tw_spread_bp
        FROM base
        WHERE NOT (bid_price IS NULL OR ask_price IS NULL OR bid_price <= 0
                   OR ask_price <= 0 OR bid_price > ask_price)
        GROUP BY 1,2,3,4
    """)


def main() -> None:
    con = connect()
    build(con)
    t2a(con)
    t2b(con)
    t2c_t2d(con)
    t2e(con)

    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    for name, tbl in [("t2a_state_census", "t2a"), ("t2a_overlap", "t2a_overlap"),
                      ("t2b_run_lengths", "t2b"), ("t2b_hard_runs", "t2b_hard_only"), ("t2c_bbo_runs", "t2c_runs"),
                      ("t2c_trade_age", "t2c_trade_age"), ("t2d_quote_to_trade", "t2d"),
                      ("t2e_quoted_spread", "t2e")]:
        df = con.execute(f"SELECT * FROM {tbl}").df()
        df.to_parquet(ARTIFACTS / f"{name}.parquet", index=False)
        print(f"{name:24s} rows={len(df):>6,}")

    chk = con.execute("""
        SELECT MAX(ABS(time_hard_unusable + time_degraded + time_clean - 1.0)) AS max_dev
        FROM t2a WHERE total_dur_ns > 0
    """).fetchone()[0]
    print(f"\npartition check  max |hard+degraded+clean - 1| = {chk:.3e}")

    r5 = con.execute("""
        SELECT QUANTILE_CONT(time_hard_unusable, 0.5) med, MAX(time_hard_unusable) mx,
               COUNT(*) n
        FROM t2a WHERE day_offset = 0 AND segment = 'rth'
    """).fetchone()
    print(f"ROW 5  median hard_unusable time share, T=0 RTH = {r5[0]:.6f} "
          f"(max {r5[1]:.4f}, n={r5[2]}) | threshold 0.25 -> "
          f"{'FIRES' if r5[0] > 0.25 else 'does not fire'}")


if __name__ == "__main__":
    main()
