"""Phase 11 T3 - trade-quote alignment sweep. The control gate.

For each dev-primary trade, ASOF-join to the quote prevailing at
`trade_time + delta` for every delta in config.alignment_sweep.alignment_offsets_ns
(27 rungs, half-decade log spacing, -1s..+1s, includes exactly 0).

T3a-i runs the WHOLE sweep twice: once with BOTH tables on sip_timestamp, once
with BOTH tables on participant_timestamp. T3c repeats both on the T-3 baseline
session.

Every join is an explicit ASOF on (ticker, event_date, session_date) with an
explicit ordering key - never storage order (escalation row 19).

The agent selects a row of the T3b pre-registered reading rule and states
nothing further. No offset is adopted here; that is Cooper's at the T4 gate
(escalation row 19).

Output: results/phase_11/artifacts/t3_alignment_sweep.parquet
"""
from __future__ import annotations

import pathlib
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).parent))

import pandas as pd
from common import ARTIFACTS, CONFIG, connect, primary_events, session_bounds
from t2_state_census import day_offset_map

OFFSETS = CONFIG["alignment_sweep"]["alignment_offsets_ns"]
WATCHDOG = CONFIG["runtime"]["query_watchdog_seconds"]
HARD = ("(q_bid IS NULL OR q_ask IS NULL OR q_bid <= 0 OR q_ask <= 0 OR q_bid > q_ask)")


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

    seg = """
      CASE WHEN sb.is_session IS NOT TRUE       THEN 'non_session'
           WHEN x.et_ts::TIME < TIME '04:00:00' THEN 'outside_early'
           WHEN x.et_ts < sb.rth_open           THEN 'premarket'
           WHEN x.et_ts < sb.rth_close          THEN 'rth'
           WHEN x.et_ts::TIME < TIME '20:00:00' THEN 'post'
           ELSE 'outside_late' END
    """
    for tbl, src, cols in (
        ("qq", "mom.filtered_quotes_dev_v4",
         "x.bid_price AS q_bid, x.ask_price AS q_ask"),
        ("tt", "mom.filtered_trades_dev_v4", "x.price AS t_price, x.size AS t_size"),
    ):
        con.execute(f"""
            CREATE TABLE {tbl} AS
            SELECT x.ticker, x.event_date, x.et_ts::DATE AS session_date,
                   dof.day_offset, {seg} AS segment,
                   x.sip_timestamp, x.participant_timestamp, x.sequence_number, {cols}
            FROM (SELECT *, et(sip_timestamp) AS et_ts FROM {src}
                  WHERE dev_cohort='primary') x
            LEFT JOIN sb ON sb.session_date = x.et_ts::DATE
            LEFT JOIN dayoff dof ON dof.event_date = x.event_date
                                AND dof.session_date = x.et_ts::DATE
            WHERE dof.day_offset IN (0, -3)
        """)
    for t in ("qq", "tt"):
        n = con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        print(f"  {t}: {n:,} rows")


def sweep(con, basis: str, day_offset: int) -> pd.DataFrame:
    """One (clock basis, session) sweep across all 27 offsets."""
    frames = []
    for d in OFFSETS:
        t0 = time.perf_counter()
        df = con.execute(f"""
            SELECT t.ticker, t.event_date, t.segment,
                   COUNT(*)                                              AS n_trades,
                   COUNT(*) FILTER (WHERE q.{basis} IS NULL)             AS n_no_quote,
                   COUNT(*) FILTER (WHERE q.{basis} IS NOT NULL
                                      AND {HARD})                        AS n_unusable_quote,
                   COUNT(*) FILTER (WHERE q.{basis} IS NOT NULL AND NOT {HARD}
                                      AND t.t_price >= q.q_bid
                                      AND t.t_price <= q.q_ask)          AS n_at_or_inside,
                   COUNT(*) FILTER (WHERE q.{basis} IS NOT NULL AND NOT {HARD}
                                      AND abs(t.t_price - q.q_bid) < 1e-9) AS n_at_bid,
                   COUNT(*) FILTER (WHERE q.{basis} IS NOT NULL AND NOT {HARD}
                                      AND abs(t.t_price - q.q_ask) < 1e-9) AS n_at_ask,
                   COUNT(*) FILTER (WHERE q.{basis} IS NOT NULL AND NOT {HARD}
                                      AND t.t_price > q.q_bid + 1e-9
                                      AND t.t_price < q.q_ask - 1e-9)    AS n_strictly_inside,
                   COUNT(*) FILTER (WHERE q.{basis} IS NOT NULL AND NOT {HARD}
                                      AND t.t_price < q.q_bid - 1e-9)    AS n_below_bid,
                   COUNT(*) FILTER (WHERE q.{basis} IS NOT NULL AND NOT {HARD}
                                      AND t.t_price > q.q_ask + 1e-9)    AS n_above_ask
            FROM tt t
            ASOF LEFT JOIN qq q
              ON t.ticker = q.ticker AND t.event_date = q.event_date
             AND t.session_date = q.session_date
             AND t.{basis} + {d} >= q.{basis}
            WHERE t.day_offset = {day_offset}
              AND t.segment IN ('premarket','rth','post')
            GROUP BY 1,2,3
        """).df()
        el = time.perf_counter() - t0
        if el > WATCHDOG:
            raise RuntimeError(f"escalation row 12a: query exceeded "
                               f"{WATCHDOG}s at delta={d}")
        df["offset_ns"] = d
        df["basis"] = basis
        df["day_offset"] = day_offset
        frames.append(df)
        print(f"    delta={d:>13,} ns  {el:6.2f}s  rows={len(df)}")
    return pd.concat(frames, ignore_index=True)


def main() -> None:
    con = connect()
    build(con)
    t_all = time.perf_counter()
    out = []
    for basis in ("sip_timestamp", "participant_timestamp"):
        for day_offset in (0, -3):
            print(f"  sweep basis={basis} day_offset={day_offset}")
            out.append(sweep(con, basis, day_offset))
    df = pd.concat(out, ignore_index=True)
    df["share_at_or_inside"] = df.n_at_or_inside / df.n_trades
    df["share_at_bid"] = df.n_at_bid / df.n_trades
    df["share_at_ask"] = df.n_at_ask / df.n_trades
    df["share_below_bid"] = df.n_below_bid / df.n_trades
    df["share_above_ask"] = df.n_above_ask / df.n_trades
    df["share_no_quote"] = df.n_no_quote / df.n_trades

    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    df.to_parquet(ARTIFACTS / "t3_alignment_sweep.parquet", index=False)
    print(f"\nt3_alignment_sweep rows={len(df):,}  wall={time.perf_counter()-t_all:.1f}s")

    # Peak rung per (basis, day_offset, segment), on the pooled median across events.
    print("\npeak offset by pooled median share_at_or_inside:")
    g = (df.groupby(["basis", "day_offset", "segment", "offset_ns"])
           .share_at_or_inside.median().reset_index())
    for (b, d, s), sub in g.groupby(["basis", "day_offset", "segment"]):
        best = sub.loc[sub.share_at_or_inside.idxmax()]
        at0 = float(sub[sub.offset_ns == 0].share_at_or_inside.iloc[0])
        print(f"  {b:22s} T{d:+d} {s:10s} peak delta={int(best.offset_ns):>13,} ns "
              f"share={best.share_at_or_inside:.4f} | at delta=0 share={at0:.4f}")


if __name__ == "__main__":
    main()
