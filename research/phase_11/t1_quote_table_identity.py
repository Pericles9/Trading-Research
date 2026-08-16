"""Phase 11 T1a / T1b - what filtered_quotes actually contains.

Dev tier only: the 50 frozen dev-v4 PRIMARY events. Zero full-table passes
(escalation row 12). Every ordered computation uses an explicit ORDER BY, so
nothing depends on storage order (escalation row 19); the storage-order census
itself is T1c-v, against the source parquet, exempt by name (row 19a).

Outputs
  results/phase_11/artifacts/t1a_exchange_identity.parquet
  results/phase_11/artifacts/t1a_exchange_frequency.parquet
  results/phase_11/artifacts/t1b_timestamps.parquet
  results/phase_11/artifacts/t1b_clock_latency.parquet
"""
from __future__ import annotations

import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).parent))

import pandas as pd
from common import ARTIFACTS, connect, primary_events, session_bounds

SEG_CASE = """
CASE
  WHEN sb.is_session IS NOT TRUE                       THEN 'non_session'
  WHEN q.et_ts::TIME <  TIME '04:00:00'                THEN 'outside_early'
  WHEN q.et_ts       <  sb.rth_open                    THEN 'premarket'
  WHEN q.et_ts       <  sb.rth_close                   THEN 'rth'
  WHEN q.et_ts::TIME <  TIME '20:00:00'                THEN 'post'
  ELSE 'outside_late'
END
"""


def build_base(con) -> None:
    """One materialised dev-tier working set, segment-labelled. In-memory only."""
    ev = primary_events(con)
    dates = con.execute(
        """
        SELECT DISTINCT et(sip_timestamp)::DATE AS d
        FROM mom.filtered_quotes_dev_v4 WHERE dev_cohort = 'primary'
        """
    ).df()["d"]
    sb = session_bounds(dates)
    con.register("sb_df", sb)
    con.register("ev_df", ev[["ticker", "event_date", "momentum_pct"]])
    con.execute("CREATE TABLE sb AS SELECT * FROM sb_df")
    con.execute("CREATE TABLE ev AS SELECT * FROM ev_df")

    con.execute(
        f"""
        CREATE TABLE base AS
        SELECT
          q.ticker, q.event_date,
          q.bid_exchange, q.ask_exchange,
          q.bid_price, q.ask_price, q.bid_size, q.ask_size,
          q.sip_timestamp, q.participant_timestamp, q.sequence_number,
          q.et_ts::DATE                                    AS session_date,
          (q.et_ts::DATE = q.event_date)                   AS is_t0,
          {SEG_CASE}                                       AS segment
        FROM (
          SELECT *, et(sip_timestamp) AS et_ts
          FROM mom.filtered_quotes_dev_v4
          WHERE dev_cohort = 'primary'
        ) q
        LEFT JOIN sb ON sb.session_date = q.et_ts::DATE
        """
    )


def t1a(con) -> None:
    """Consolidated best-quote reading: exchange identity, T=0, by segment."""
    con.execute(
        """
        CREATE TABLE t1a AS
        SELECT ticker, event_date, segment,
               COUNT(*)                                                      AS n_rows,
               COUNT(DISTINCT bid_exchange)                                  AS n_bid_exch,
               COUNT(DISTINCT ask_exchange)                                  AS n_ask_exch,
               COUNT(DISTINCT bid_exchange) + COUNT(DISTINCT ask_exchange)   AS n_exch_sum,
               AVG(CASE WHEN bid_exchange <> ask_exchange THEN 1.0 ELSE 0.0 END) AS share_two_sided,
               COUNT(*) FILTER (WHERE bid_exchange IS NULL OR ask_exchange IS NULL) AS n_null_exch
        FROM base
        WHERE is_t0
        GROUP BY 1, 2, 3
        """
    )
    con.execute(
        """
        CREATE TABLE t1a_freq AS
        SELECT ticker, event_date, 'bid' AS side, bid_exchange AS exchange, COUNT(*) AS n_rows
        FROM base WHERE is_t0 GROUP BY 1, 2, 3, 4
        UNION ALL
        SELECT ticker, event_date, 'ask', ask_exchange, COUNT(*)
        FROM base WHERE is_t0 GROUP BY 1, 2, 3, 4
        """
    )


def t1b(con) -> None:
    """Timestamp semantics. All aggregates are order-free or use explicit ORDER BY."""
    # Row 4a needs three well-defined denominators; a straddle of 1% escalates.
    con.execute(
        """
        CREATE TABLE t1b_null AS
        SELECT ticker, event_date,
          COUNT(*) FILTER (WHERE is_t0)                                          AS n_t0_all,
          COUNT(*) FILTER (WHERE is_t0 AND segment = 'rth')                      AS n_t0_rth_sip,
          SUM(CASE WHEN is_t0 AND (sip_timestamp IS NULL OR sip_timestamp = 0)
                   THEN 1 ELSE 0 END)                                            AS n_sip_bad_t0_all,
          SUM(CASE WHEN is_t0 AND segment = 'rth'
                        AND (sip_timestamp IS NULL OR sip_timestamp = 0)
                   THEN 1 ELSE 0 END)                                            AS n_sip_bad_t0_rth,
          SUM(CASE WHEN is_t0 AND (participant_timestamp IS NULL
                                   OR participant_timestamp = 0)
                   THEN 1 ELSE 0 END)                                            AS n_par_bad_t0_all,
          SUM(CASE WHEN is_t0 AND segment = 'rth'
                        AND (participant_timestamp IS NULL
                             OR participant_timestamp = 0)
                   THEN 1 ELSE 0 END)                                            AS n_par_bad_t0_rth,
          COUNT(*)                                                               AS n_rows_all_sessions
        FROM base
        GROUP BY 1, 2
        """
    )
    # Resolution: smallest non-zero gap, per event, per clock. Integer ns throughout.
    for col, name in (("sip_timestamp", "sip"), ("participant_timestamp", "par")):
        con.execute(
            f"""
            CREATE TABLE t1b_res_{name} AS
            SELECT ticker, event_date,
                   MIN(d) FILTER (WHERE d > 0)                       AS min_nonzero_gap_ns,
                   QUANTILE_CONT(d, 0.5) FILTER (WHERE d > 0)        AS median_gap_ns,
                   MAX(d)                                            AS max_gap_ns,
                   COUNT(*) FILTER (WHERE d = 0)                     AS n_zero_gap,
                   COUNT(*)                                          AS n_gaps
            FROM (
              SELECT ticker, event_date,
                     {col} - LAG({col}) OVER (
                       PARTITION BY ticker, event_date, session_date ORDER BY {col}
                     ) AS d
              FROM base WHERE is_t0
            ) g
            WHERE d IS NOT NULL
            GROUP BY 1, 2
            """
        )
    # T1b-ii: ordering agreement under an explicit sort by sip_timestamp.
    con.execute(
        """
        CREATE TABLE t1b_order AS
        SELECT ticker, event_date,
          COUNT(*)                                                   AS n_pairs,
          AVG(CASE WHEN d_par < 0 THEN 1.0 ELSE 0.0 END)             AS share_par_inverts,
          AVG(CASE WHEN d_seq < 0 THEN 1.0 ELSE 0.0 END)             AS share_seq_inverts,
          AVG(CASE WHEN d_sip = 0 THEN 1.0 ELSE 0.0 END)             AS share_sip_ties,
          SUM(CASE WHEN d_sip = 0 AND d_seq = 0 THEN 1 ELSE 0 END)   AS n_tie_seq_dup,
          SUM(CASE WHEN d_sip = 0 THEN 1 ELSE 0 END)                 AS n_tie_rows
        FROM (
          SELECT ticker, event_date,
            sip_timestamp - LAG(sip_timestamp) OVER w AS d_sip,
            participant_timestamp - LAG(participant_timestamp) OVER w AS d_par,
            sequence_number - LAG(sequence_number) OVER w AS d_seq
          FROM base WHERE is_t0
          WINDOW w AS (PARTITION BY ticker, event_date, session_date
                       ORDER BY sip_timestamp, sequence_number)
        ) g
        WHERE d_sip IS NOT NULL
        GROUP BY 1, 2
        """
    )
    # T1b-iii: reporting latency between the two clocks, by segment.
    con.execute(
        """
        CREATE TABLE t1b_latency AS
        SELECT ticker, event_date, segment,
          COUNT(*)                                        AS n_rows,
          QUANTILE_CONT(lat, 0.01) AS p01, QUANTILE_CONT(lat, 0.25) AS p25,
          QUANTILE_CONT(lat, 0.50) AS p50, QUANTILE_CONT(lat, 0.75) AS p75,
          QUANTILE_CONT(lat, 0.99) AS p99,
          MIN(lat) AS min_ns, MAX(lat) AS max_ns,
          AVG(CASE WHEN lat < 0 THEN 1.0 ELSE 0.0 END)    AS share_negative
        FROM (
          SELECT ticker, event_date, segment,
                 sip_timestamp - participant_timestamp AS lat
          FROM base WHERE is_t0
        ) g
        GROUP BY 1, 2, 3
        """
    )


def main() -> None:
    con = connect()
    build_base(con)
    t1a(con)
    t1b(con)

    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    out = {
        "t1a_exchange_identity": "SELECT * FROM t1a ORDER BY ticker, event_date, segment",
        "t1a_exchange_frequency": "SELECT * FROM t1a_freq ORDER BY ticker, event_date, side, exchange",
        "t1b_null": "SELECT * FROM t1b_null ORDER BY ticker, event_date",
        "t1b_resolution_sip": "SELECT * FROM t1b_res_sip ORDER BY ticker, event_date",
        "t1b_resolution_par": "SELECT * FROM t1b_res_par ORDER BY ticker, event_date",
        "t1b_order": "SELECT * FROM t1b_order ORDER BY ticker, event_date",
        "t1b_clock_latency": "SELECT * FROM t1b_latency ORDER BY ticker, event_date, segment",
    }
    for name, q in out.items():
        df = con.execute(q).df()
        df.to_parquet(ARTIFACTS / f"{name}.parquet", index=False)
        print(f"{name:26s} rows={len(df):>7,}")

    # Segment census, including the rows that fall outside the extended session.
    seg = con.execute(
        """
        SELECT segment, is_t0, COUNT(*) n, COUNT(DISTINCT (ticker, event_date)) n_events
        FROM base GROUP BY 1, 2 ORDER BY 2 DESC, 4 DESC, 3 DESC
        """
    ).df()
    seg.to_parquet(ARTIFACTS / "t1_segment_census.parquet", index=False)
    print("\nsegment census (is_t0 first):")
    print(seg.to_string(index=False))


if __name__ == "__main__":
    main()
