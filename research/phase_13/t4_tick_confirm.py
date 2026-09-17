"""
Phase 13, T4: tick-level confirmation, target = T3b (share turnover).

Cooper-triggered 2026-09-14 ("proceed with tick confg" -> AskUserQuestion ->
T3b, the largest population-aggregate separation of the three splits). Confirms
T3b's minute-bar-derived MFE/MAE against filtered_trades (raw ticks) directly --
same population, same horizons, same round-trip cost. Not a new claim: a check on
whether the existing one survives contact with the tick data the bars were built
from. No kill condition, no pass/fail anywhere in this script's output (same rule
as every other task in this phase -- escalation rows 2/3).

Bulk single-join design, reusing the pattern already proven at full-table scale
elsewhere in this repo (research/phase_6b/build_minute_bars_v2.py: one bulk join +
GROUP BY MAX/MIN over the full ~4.95B-row filtered_trades table, ~25 min for a
heavier per-minute aggregation over 15,763 events). This query is a single
[t0, t0+horizon] window per event with a plain MAX(price)/MIN(price), no minute
bucketing -- lighter than that benchmark. Filtered on the raw sip_timestamp BIGINT
column directly, not a converted timestamp (which defeats row-group pruning,
confirmed elsewhere in this repo).

Usage: .venv/Scripts/python.exe research/phase_13/t4_tick_confirm.py [--limit N]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from research.phase_13 import common as C  # noqa: E402
from research.phase_13 import t3_partitions as T3  # noqa: E402

HORIZONS = [5, 15, 30, 60]
OUT_PATH = f"{C.ART}/t4_tick_confirmation.json"
TICK_PARQUET = f"{C.ART}/t4_tick_mfe_mae.parquet"
NS_PER_MIN = 60 * 1_000_000_000


def describe(s: pd.Series) -> dict:
    s = s.dropna()
    if len(s) == 0:
        return {"n": 0}
    return {
        "n": int(len(s)),
        "p10": float(s.quantile(0.10)), "p25": float(s.quantile(0.25)),
        "median": float(s.median()), "p75": float(s.quantile(0.75)), "p90": float(s.quantile(0.90)),
        "mean": float(s.mean()),
    }


def build_events_frame(df: pd.DataFrame, limit: int | None) -> pd.DataFrame:
    keys = pd.read_parquet("results/fundamentals_f1/artifacts/ticker_identity.parquet",
                            columns=["event_id", "ticker", "event_date_canonical", "momentum_pct"])
    ev = df[df["t3b_high_turnover"].notna()][
        ["event_id", "t0_ns", "detection_price", "round_trip_cost_dollars", "t3b_high_turnover"]
    ].merge(keys, on="event_id", how="inner")
    if limit:
        ev = ev.head(limit).copy()
    return ev


def pull_tick_extremes(con, events: pd.DataFrame, horizon: int) -> pd.DataFrame:
    con.register("t4_events", events)
    sql = f"""
        SELECT e.event_id, MAX(t.price) AS tick_high, MIN(t.price) AS tick_low, COUNT(*) AS n_ticks
        FROM t4_events e
        JOIN filtered_trades t
          ON e.ticker = t.ticker
         AND e.event_date_canonical = t.event_date
         AND ROUND(t.momentum_pct, 2) = ROUND(e.momentum_pct, 2)
         AND t.sip_timestamp >= e.t0_ns
         AND t.sip_timestamp <= e.t0_ns + {horizon * NS_PER_MIN}
        GROUP BY e.event_id
    """
    return con.execute(sql).df()


def pull_bar_extremes(con, events: pd.DataFrame, horizon: int) -> pd.DataFrame:
    """Same window, from event_minute_bars_v2, for the tick-vs-bar comparison (T4b)."""
    from research.phase_13.t1_build_p0 import compute_t0_minute_index
    ev2 = events.copy()
    ev2["t0_minute_index"] = compute_t0_minute_index(ev2["t0_ns"], ev2["event_date_canonical"])
    con.register("t4_events_bar", ev2)
    sql = f"""
        SELECT e.event_id, MAX(b.high) AS bar_high, MIN(b.low) AS bar_low
        FROM t4_events_bar e
        JOIN main_db.event_minute_bars_v2 b
          ON e.ticker = b.ticker AND e.event_date_canonical = b.event_date_canonical
         AND e.momentum_pct = b.momentum_pct AND b.session_offset = 0
         AND b.minute_index BETWEEN e.t0_minute_index AND e.t0_minute_index + {horizon}
        GROUP BY e.event_id
    """
    return con.execute(sql).df()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None, help="test on the first N events only")
    args = ap.parse_args()

    df, _meta = T3.build_df()
    con = C.connect(read_only=True)
    events = build_events_frame(df, args.limit)
    print(f"T4 population: {len(events)} events (T3b-covered)")

    all_rows = []
    per_horizon_summary = {}
    t_start = time.time()
    for h in HORIZONS:
        t0 = time.time()
        ticks = pull_tick_extremes(con, events, h)
        bars = pull_bar_extremes(con, events, h)
        print(f"  h={h}min: tick pull {len(ticks)} events in {time.time()-t0:.1f}s, bar pull {len(bars)} events")

        merged = events.merge(ticks, on="event_id", how="left").merge(bars, on="event_id", how="left", suffixes=("", "_bar"))
        merged["mfe_dollars_tick"] = (merged["tick_high"] - merged["detection_price"]).clip(lower=0)
        merged["mae_dollars_tick"] = (merged["detection_price"] - merged["tick_low"]).clip(lower=0)
        merged["mfe_cost_mult_tick"] = merged["mfe_dollars_tick"] / merged["round_trip_cost_dollars"]
        merged["mae_cost_mult_tick"] = merged["mae_dollars_tick"] / merged["round_trip_cost_dollars"]
        merged["mfe_dollars_bar"] = (merged["bar_high"] - merged["detection_price"]).clip(lower=0)
        merged["mae_dollars_bar"] = (merged["detection_price"] - merged["bar_low"]).clip(lower=0)
        merged["mfe_cost_mult_bar"] = merged["mfe_dollars_bar"] / merged["round_trip_cost_dollars"]
        merged["mae_cost_mult_bar"] = merged["mae_dollars_bar"] / merged["round_trip_cost_dollars"]
        merged["horizon"] = h

        both = merged[merged["tick_high"].notna() & merged["bar_high"].notna()]
        # A tick high strictly above the bar high (or tick low strictly below the bar
        # low) means the bar excluded at least one printed trade the tick table has --
        # a bar-build discrepancy, not noise (ties are expected and not a disagreement).
        high_disagree = (both["tick_high"] - both["bar_high"]).abs() > 1e-9
        low_disagree = (both["tick_low"] - both["bar_low"]).abs() > 1e-9
        any_disagree = high_disagree | low_disagree
        max_high_gap = float((both["tick_high"] - both["bar_high"]).abs().max()) if len(both) else None
        max_low_gap = float((both["tick_low"] - both["bar_low"]).abs().max()) if len(both) else None

        per_horizon_summary[h] = {
            "n_events": len(merged),
            "n_tick_covered": int(merged["tick_high"].notna().sum()),
            "n_bar_covered": int(merged["bar_high"].notna().sum()),
            "n_both_covered": len(both),
            "n_high_disagree": int(high_disagree.sum()),
            "n_low_disagree": int(low_disagree.sum()),
            "share_any_disagree": float(any_disagree.mean()) if len(both) else None,
            "max_high_gap_dollars": max_high_gap,
            "max_low_gap_dollars": max_low_gap,
            "tick_mfe_cost_mult_below_median_turnover": describe(
                merged.loc[merged["t3b_high_turnover"] == False, "mfe_cost_mult_tick"]),  # noqa: E712
            "tick_mfe_cost_mult_above_median_turnover": describe(
                merged.loc[merged["t3b_high_turnover"] == True, "mfe_cost_mult_tick"]),  # noqa: E712
            "tick_mae_cost_mult_below_median_turnover": describe(
                merged.loc[merged["t3b_high_turnover"] == False, "mae_cost_mult_tick"]),  # noqa: E712
            "tick_mae_cost_mult_above_median_turnover": describe(
                merged.loc[merged["t3b_high_turnover"] == True, "mae_cost_mult_tick"]),  # noqa: E712
            "bar_mfe_cost_mult_below_median_turnover": describe(
                merged.loc[merged["t3b_high_turnover"] == False, "mfe_cost_mult_bar"]),  # noqa: E712
            "bar_mfe_cost_mult_above_median_turnover": describe(
                merged.loc[merged["t3b_high_turnover"] == True, "mfe_cost_mult_bar"]),  # noqa: E712
        }
        all_rows.append(merged[[
            "event_id", "horizon", "t3b_high_turnover", "n_ticks",
            "mfe_cost_mult_tick", "mae_cost_mult_tick", "mfe_cost_mult_bar", "mae_cost_mult_bar",
        ]])

    os.makedirs(C.ART, exist_ok=True)
    pd.concat(all_rows, ignore_index=True).to_parquet(TICK_PARQUET, index=False)

    summary = {
        "target_split": "t3b_share_turnover",
        "triggered_by": "Cooper, 2026-09-14: 'proceed with tick confg' -> AskUserQuestion -> T3b",
        "n_population": len(events),
        "elapsed_seconds": round(time.time() - t_start, 1),
        "by_horizon": {str(h): v for h, v in per_horizon_summary.items()},
        "note": "Tick-derived (filtered_trades) vs. bar-derived (event_minute_bars_v2) MFE/MAE "
                "cost-multiple, same events, same windows. No kill condition, no pass/fail "
                "declaration -- distributions reported for comparison only.",
        "config_hash": C.cfg_hash(),
    }
    C.write_json(OUT_PATH, summary)
    print(json.dumps({k: v for k, v in summary.items() if k != "by_horizon"}, indent=2))
    for h in HORIZONS:
        s = per_horizon_summary[h]
        print(f"\n--- horizon {h}min ---")
        print(f"  tick/bar: {s['n_both_covered']} both-covered, share any disagree={s['share_any_disagree']}")
        print(f"  tick median MFE cost-mult: below={s['tick_mfe_cost_mult_below_median_turnover'].get('median')}, "
              f"above={s['tick_mfe_cost_mult_above_median_turnover'].get('median')}")


if __name__ == "__main__":
    main()
