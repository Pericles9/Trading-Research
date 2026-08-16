"""T6 - effective spread at the detection anchor.

Reads event_quote_metrics_v1 (the single budgeted pass). No further scan.

D16  reference midpoint = contemporaneous consolidated best quote at delta = 0,
     sip_timestamp basis. That is the basis the cache was built on.
D19  reported in basis points AND cents (and as a share of the detection price).
D18  all three segments computed; the decision rests on RTH alone.

Effective spread for a minute bar, size-weighted over its trades:
    eff_dollars = 2 * SUM(|p - m| * size) / SUM(size)
    eff_bp      = 10000 * eff_dollars / tw_mid
    eff_cents   = 100 * eff_dollars

Latency 0 is a physical impossibility and is labelled the upper bound
(Phase 8 / D7 convention).
"""
from __future__ import annotations

import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))

import duckdb
import pandas as pd
from common import ARTIFACTS, CONFIG, DB

ANCH = "results/phase_8/artifacts/a102_detection_anchors.parquet"
PART = "results/phase_8/artifacts/t3_participation.parquet"
QSESS = "results/phase_4/artifacts/_actual_quotes_sessions_cache.parquet"
LAT = [0, 1, 5, 15, 30]
MIN_N = CONFIG["universe"]["min_cell_n"]


def connect_ro():
    con = duckdb.connect()
    con.execute(f"ATTACH '{DB}' AS mom (READ_ONLY)")
    con.execute("SET enable_progress_bar = false")
    return con


def build(con) -> pd.DataFrame:
    lat_union = " UNION ALL ".join(
        f"SELECT ticker, event_date, det_minute + {l} AS tgt, {l} AS latency FROM det"
        for l in LAT)
    con.execute(f"""
        CREATE TABLE det AS
        SELECT a.ticker, a.event_date_canonical AS event_date, round(a.mp,2) AS mp2,
               a.det_minute, a.det_segment, a.era, a.day_high_ext,
               a.det_price_lat0, a.det_price_lat1, a.det_price_lat5,
               a.det_price_lat15, a.det_price_lat30,
               p.pq_rth_open
        FROM read_parquet('{ANCH}') a
        LEFT JOIN read_parquet('{PART}') p
          ON p.ticker = a.ticker AND p.event_date_canonical = a.event_date_canonical
         AND round(p.mp,2) = round(a.mp,2)
        JOIN (SELECT DISTINCT ticker, event_date_canonical, mom_2dp
              FROM read_parquet('{QSESS}')) q
          ON q.ticker = a.ticker AND q.event_date_canonical = a.event_date_canonical
         AND q.mom_2dp = round(a.mp,2)
        WHERE a.det_undefined = FALSE
    """)
    con.execute(f"""
        CREATE TABLE t6 AS
        SELECT d.ticker, d.event_date, d.det_segment, d.era, d.pq_rth_open, t.latency,
               c.minute_index AS resolved_minute, t.tgt AS target_minute,
               c.tw_mid, c.n_trades, c.sum_size, c.unusable_time_share,
               c.locked_time_share, c.bbo_age_at_trade_p50,
               2.0 * c.sum_abs_p_minus_m_size / NULLIF(c.sum_size, 0) AS eff_dollars,
               100.0 * 2.0 * c.sum_abs_p_minus_m_size / NULLIF(c.sum_size, 0) AS eff_cents,
               10000.0 * 2.0 * c.sum_abs_p_minus_m_size
                   / NULLIF(c.sum_size, 0) / NULLIF(c.tw_mid, 0) AS eff_bp,
               CASE t.latency WHEN 0 THEN d.det_price_lat0 WHEN 1 THEN d.det_price_lat1
                    WHEN 5 THEN d.det_price_lat5 WHEN 15 THEN d.det_price_lat15
                    ELSE d.det_price_lat30 END AS det_price
        FROM ({lat_union}) t
        JOIN det d USING (ticker, event_date)
        ASOF LEFT JOIN (SELECT * FROM mom.event_quote_metrics_v1
                        WHERE n_trades > 0 AND sum_size > 0) c
          ON t.ticker = c.ticker AND t.event_date = c.event_date
         AND t.tgt >= c.minute_index
    """)
    df = con.execute("SELECT * FROM t6").df()
    df["eff_share_of_det_price"] = df.eff_dollars / df.det_price.where(df.det_price > 0)
    return df


def cells(df: pd.DataFrame, by: list[str]) -> pd.DataFrame:
    g = df.dropna(subset=["eff_bp"]).groupby(by, dropna=False)
    out = g.agg(n=("eff_bp", "size"),
                eff_bp_p25=("eff_bp", lambda s: s.quantile(.25)),
                eff_bp_p50=("eff_bp", "median"),
                eff_bp_p75=("eff_bp", lambda s: s.quantile(.75)),
                eff_bp_p95=("eff_bp", lambda s: s.quantile(.95)),
                eff_cents_p25=("eff_cents", lambda s: s.quantile(.25)),
                eff_cents_p50=("eff_cents", "median"),
                eff_cents_p75=("eff_cents", lambda s: s.quantile(.75)),
                eff_share_p50=("eff_share_of_det_price", "median")).reset_index()
    out["hatched_n_below_100"] = out.n < MIN_N
    return out


def main() -> None:
    con = connect_ro()
    df = build(con)
    df.to_parquet(ARTIFACTS / "t6_effective_spread.parquet", index=False)

    by_cell = cells(df, ["det_segment", "era", "pq_rth_open", "latency"])
    by_lat = cells(df, ["det_segment", "latency"])
    by_cell.to_parquet(ARTIFACTS / "t6_cells.parquet", index=False)

    out = {
        "task": "T6", "phase": "11", "date": "2026-08-16",
        "source": "event_quote_metrics_v1 (the single budgeted pass). No further scan.",
        "definition": {
            "eff_dollars": "2 * SUM(|p - m| * size) / SUM(size) over the resolved bar",
            "eff_bp": "10000 * eff_dollars / tw_mid",
            "eff_cents": "100 * eff_dollars",
            "midpoint": "contemporaneous consolidated best quote at delta = 0, "
                        "sip_timestamp basis (D16)",
            "anchor": "det_anchor reused frozen from Phase 8 a102 (D7); ASOF-resolved to "
                      "the last bar with trades at or before det_minute + latency",
        },
        "latency_0_caveat": "Latency 0 is a physical impossibility and is the UPPER BOUND, "
                            "not an achievable operating point (Phase 8 / D7 convention).",
        "standing_qualifier": CONFIG["standing_qualifier"]["text"],
        "n_events": int(df[["ticker", "event_date"]].drop_duplicates().shape[0]),
        "by_segment_latency": json.loads(by_lat.to_json(orient="records")),
        "cells_below_min_n": int(by_cell.hatched_n_below_100.sum()),
        "min_cell_n": MIN_N,
    }
    pathlib.Path(ARTIFACTS / "t6_effective_spread.json").write_text(json.dumps(out, indent=2))
    print(f"T6 rows {len(df):,} | events {out['n_events']:,}")
    print(by_lat[["det_segment", "latency", "n", "eff_bp_p50", "eff_cents_p50",
                  "eff_share_p50"]].to_string(index=False))


if __name__ == "__main__":
    main()
