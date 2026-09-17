"""
Phase 13, T1: build P0, the population-scale outcome, in cost units.

Per event, from event_minute_bars_v2: maximum favorable excursion (MFE) and maximum
adverse excursion (MAE) from t0 (config.p0_outcome.entry_reference), at horizons
5/15/30/60 minutes, expressed as a multiple of that event's own round-trip cost
(config.p0_outcome.cost_unit_source).

**minute_index convention, checked directly before building this (not assumed):**
event_minute_bars_v2 and event_quote_metrics_v1 both key minute_index as "minutes
since 04:00:00 ET that session" -- continuous across premarket/rth/post, not reset
per segment (verified: AAL 2021-01-28 session_offset=0 has premarket 0-329 (330 min
= 4:00-9:30), rth 330-719 (390 min = 9:30-16:00), post 720-959 (240 min = 16:00-20:00),
and minute_index=0's first_trade_ts converts to exactly 04:00:00.05 ET). This lets
t0's minute_index be computed directly from t0_ns (pandas tz-convert, no join needed
to locate it), and lets both tables be queried by minute_index range instead of by
(segment, local index) bookkeeping that would need to handle segment-boundary
crossings for the longer horizons.

**Bulk join, not per-event point queries.** A single-event filtered query against
event_minute_bars_v2 (46M rows) was observed to be slow (DuckDB's own progress
estimate started above an hour) during reconciliation, while the same filter against
event_quote_metrics_v1 returned in under a second -- the two tables do not have the
same physical layout/pruning behavior. Querying it 20,951 times would not finish in
any reasonable session. This script does exactly one bulk join across the full table
for every event's outcome at every horizon, registering the small (20,951-row) events
frame and letting DuckDB's optimizer handle the join as a single scan.

Usage: .venv/Scripts/python.exe research/phase_13/t1_build_p0.py [--limit N]
"""
from __future__ import annotations

import argparse
import json
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from research.phase_13 import common as C  # noqa: E402

HORIZONS = [5, 15, 30, 60]
MAX_HORIZON = max(HORIZONS)
OUT_PATH = f"{C.ART}/p0_outcome.parquet"
COVERAGE_PATH = f"{C.ART}/p0_coverage_summary.json"


def compute_t0_minute_index(t0_ns: pd.Series, event_date_canonical: pd.Series) -> pd.Series:
    t0_et = pd.to_datetime(t0_ns, unit="ns", utc=True).dt.tz_convert("America/New_York")
    day_4am = pd.to_datetime(event_date_canonical).dt.tz_localize("America/New_York") + pd.Timedelta(hours=4)
    minutes = (t0_et - day_4am).dt.total_seconds() / 60.0
    return minutes.apply(lambda m: int(m) if pd.notna(m) else None)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None, help="test on the first N events only")
    args = ap.parse_args()

    cfg = C.load_cfg()
    p0cfg = cfg["p0_outcome"]

    ef = pd.read_parquet(f"{C.FUNDAMENTALS_ROOT}/event_fundamentals.parquet",
                          columns=["event_id", "ticker", "t0_ns"])
    t0_spine = pd.read_parquet("results/fundamentals_f1/artifacts/t0_spine.parquet",
                                columns=["event_id", "event_date_canonical", "momentum_pct"])
    ctx = pd.read_parquet("results/fundamentals_f1/artifacts/t6_context.parquet",
                           columns=["event_id", "detection_price"])
    events = ef.merge(t0_spine, on="event_id", how="inner").merge(ctx, on="event_id", how="left")
    assert len(events) == 20951, f"expected 20951 events, got {len(events)}"

    if args.limit:
        events = events.head(args.limit).copy()
        print(f"TEST MODE: limited to {len(events)} events")

    events["t0_minute_index"] = compute_t0_minute_index(events["t0_ns"], events["event_date_canonical"])
    events["event_date"] = pd.to_datetime(events["event_date_canonical"]).dt.date

    n_missing_price = events["detection_price"].isna().sum()
    print(f"{n_missing_price} events with no detection_price (from F1-T6) -- excluded from cost-multiple, kept in outcome as NaN")

    con = C.connect(read_only=True)
    con.register("events", events)

    # ---- round-trip cost: tw_spread_bp at (or nearest to) t0's minute ----
    cost = con.execute("""
        SELECT e.event_id, q.minute_index AS cost_minute_index, q.tw_spread_bp,
               ABS(q.minute_index - e.t0_minute_index) AS cost_minute_offset
        FROM events e
        JOIN main_db.event_quote_metrics_v1 q
          ON e.ticker = q.ticker AND e.event_date = q.event_date AND q.offset_ns = 0
        QUALIFY ROW_NUMBER() OVER (PARTITION BY e.event_id ORDER BY ABS(q.minute_index - e.t0_minute_index)) = 1
    """).df()
    print(f"round-trip cost located for {len(cost)}/{len(events)} events "
          f"(nearest-minute match, median offset {cost['cost_minute_offset'].median():.1f} min)")

    events = events.merge(cost[["event_id", "tw_spread_bp", "cost_minute_offset"]], on="event_id", how="left")
    events["round_trip_cost_bp"] = 2.0 * events["tw_spread_bp"]
    events["round_trip_cost_dollars"] = events["detection_price"] * events["round_trip_cost_bp"] / 10000.0

    # ---- MFE/MAE from event_minute_bars_v2, one bulk join across the full max-horizon window ----
    con.register("events2", events)
    bars = con.execute(f"""
        SELECT e.event_id, e.t0_minute_index, b.minute_index, b.high, b.low
        FROM events2 e
        JOIN main_db.event_minute_bars_v2 b
          ON e.ticker = b.ticker AND e.event_date_canonical = b.event_date_canonical
          AND e.momentum_pct = b.momentum_pct AND b.session_offset = 0
          AND b.minute_index BETWEEN e.t0_minute_index AND e.t0_minute_index + {MAX_HORIZON}
    """).df()
    print(f"bulk minute-bar join: {len(bars)} bar-rows across {bars['event_id'].nunique()} distinct events")

    out = events[["event_id", "ticker", "t0_ns", "t0_minute_index", "detection_price",
                  "round_trip_cost_bp", "round_trip_cost_dollars", "cost_minute_offset"]].copy()
    n_covered = {}
    for h in HORIZONS:
        window = bars[bars["minute_index"] <= bars["t0_minute_index"] + h]
        agg = window.groupby("event_id").agg(high=("high", "max"), low=("low", "min"), n_bars=("minute_index", "count"))
        out = out.merge(agg.rename(columns={"high": f"high_{h}", "low": f"low_{h}", "n_bars": f"n_bars_{h}"}),
                         on="event_id", how="left")
        out[f"mfe_dollars_{h}"] = (out[f"high_{h}"] - out["detection_price"]).clip(lower=0)
        out[f"mae_dollars_{h}"] = (out["detection_price"] - out[f"low_{h}"]).clip(lower=0)
        out[f"mfe_cost_mult_{h}"] = out[f"mfe_dollars_{h}"] / out["round_trip_cost_dollars"]
        out[f"mae_cost_mult_{h}"] = out[f"mae_dollars_{h}"] / out["round_trip_cost_dollars"]
        n_covered[h] = int(out[f"n_bars_{h}"].notna().sum())

    os.makedirs(C.ART, exist_ok=True)
    out.to_parquet(OUT_PATH, index=False)

    coverage = {
        "n_total_events": len(events),
        "n_missing_detection_price": int(n_missing_price),
        "n_missing_round_trip_cost": int(events["round_trip_cost_bp"].isna().sum()),
        "coverage_by_horizon": {str(h): {"n_covered": n_covered[h], "share": n_covered[h] / len(events)} for h in HORIZONS},
        "cost_minute_offset_median": float(cost["cost_minute_offset"].median()),
        "config_hash": C.cfg_hash(),
    }
    C.write_json(COVERAGE_PATH, coverage)
    print(json.dumps(coverage, indent=2))


if __name__ == "__main__":
    main()
