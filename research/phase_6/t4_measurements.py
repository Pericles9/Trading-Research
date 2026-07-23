"""
Phase 6 T4 - measurements computed from event_minute_bars_v1 (T=0 only).
No further full-table passes - this script only ever queries the bars
cache (already materialized by T3), never filtered_trades.
"""
import json

import duckdb
import numpy as np
import pandas as pd

from research.phase_6.build_minute_bars import build_session_spine
from research.phase_6 import measurements as M

DB_PATH = "data/duckdb/main.duckdb"
PHASE_6_CONFIG = "config/phase_6.json"
ELIGIBLE_EVENTS = "results/phase_6/artifacts/t1_eligible_events.parquet"
BARS_TABLE = "event_minute_bars_v1"

OUT_CONCENTRATION = "results/phase_6/artifacts/concentration_curves.parquet"
OUT_MIN_WINDOW = "results/phase_6/artifacts/min_window_stats.parquet"
OUT_MIN_WINDOW_SENS = "results/phase_6/artifacts/min_window_stats_sens.parquet"
OUT_DECAY_SUMMARY = "results/phase_6/artifacts/opportunity_decay.parquet"
OUT_DECAY_SUMMARY_SENS = "results/phase_6/artifacts/opportunity_decay_sens.parquet"
OUT_DECAY_PER_MINUTE = "results/phase_6/artifacts/opportunity_decay_per_minute.parquet"
OUT_DECAY_PER_MINUTE_SENS = "results/phase_6/artifacts/opportunity_decay_per_minute_sens.parquet"
OUT_POOLED = "results/phase_6/artifacts/pooled_decay.parquet"
OUT_POOLED_SENS = "results/phase_6/artifacts/pooled_decay_sens.parquet"
OUT_INDEX_DATA = "results/phase_6/artifacts/event_index.parquet"
OUT_SUMMARY = "results/phase_6/artifacts/t4_measurements_summary.json"


def compute_deciles(events: pd.DataFrame, cfg: dict) -> pd.Series:
    n = cfg["chart_overlay"].get("n_deciles", 10)
    return pd.qcut(events["momentum_pct"], n, labels=False, duplicates="drop")


def main():
    with open(PHASE_6_CONFIG) as f:
        cfg = json.load(f)
    thresholds_pct = cfg["min_window_thresholds_pct"]
    excl_minute = cfg["opening_print_sensitivity"]["exclude_minute_index"]
    shift_mult = cfg["opening_print_sensitivity"]["shift_escalation_multiple"]

    events = pd.read_parquet(ELIGIBLE_EVENTS)
    events["event_date_canonical"] = pd.to_datetime(events["event_date_canonical"])
    events["decile"] = compute_deciles(events, cfg)
    print(f"eligible events: {len(events)}")

    print("building session spine (T=0 only needed here, but build_session_spine derives all offsets - cheap, no DB access)...")
    spine = build_session_spine(events, cfg)
    session_minutes = M.session_minutes_from_spine(spine, offset=0)
    print(f"session_minutes: {len(session_minutes)} events")

    con = duckdb.connect(DB_PATH, read_only=True)
    bars_t0 = con.execute(f"""
        SELECT ticker, event_date_canonical, momentum_pct, minute_index, n_trades, volume, vwap,
               high, low, first_price, last_price
        FROM {BARS_TABLE} WHERE session_offset = 0
    """).fetchdf()
    con.close()
    print(f"bars_t0 loaded: {len(bars_t0)} rows")

    grid = M.build_full_grid(bars_t0, session_minutes)
    print(f"full grid: {len(grid)} rows")

    # T4a
    concentration = M.compute_concentration_curves(grid)
    concentration.to_parquet(OUT_CONCENTRATION, index=False)
    print(f"T4a concentration curves: {len(concentration)} rows -> {OUT_CONCENTRATION}")

    # T4b
    min_window = M.compute_min_window_stats(grid, thresholds_pct, min_minute_included=0)
    min_window.to_parquet(OUT_MIN_WINDOW, index=False)
    print(f"T4b min-window stats: {len(min_window)} events -> {OUT_MIN_WINDOW}")

    # T4c
    per_minute, per_event_summary = M.compute_opportunity_decay(grid, min_minute_included=0)
    pooled = M.pooled_per_minute_quantiles(per_minute)
    crossing = M.pooled_median_crossing_minute(pooled)
    per_minute.to_parquet(OUT_DECAY_PER_MINUTE, index=False)
    per_event_summary.to_parquet(OUT_DECAY_SUMMARY, index=False)
    pooled.to_parquet(OUT_POOLED, index=False)
    print(f"T4c opportunity decay (with minute 0): pooled median crosses 0.5 at minute {crossing}")

    # T4d - opening-print sensitivity (independent recompute, not a mask)
    min_window_sens = M.compute_min_window_stats(grid, thresholds_pct, min_minute_included=excl_minute + 1)
    per_minute_sens, per_event_summary_sens = M.compute_opportunity_decay(grid, min_minute_included=excl_minute + 1)
    pooled_sens = M.pooled_per_minute_quantiles(per_minute_sens)
    crossing_sens = M.pooled_median_crossing_minute(pooled_sens)
    min_window_sens.to_parquet(OUT_MIN_WINDOW_SENS, index=False)
    per_minute_sens.to_parquet(OUT_DECAY_PER_MINUTE_SENS, index=False)
    per_event_summary_sens.to_parquet(OUT_DECAY_SUMMARY_SENS, index=False)
    pooled_sens.to_parquet(OUT_POOLED_SENS, index=False)
    print(f"T4d opportunity decay (excl minute 0): pooled median crosses 0.5 at minute {crossing_sens}")

    ratio = crossing_sens / crossing if crossing not in (0, None) and not np.isnan(crossing) and crossing != 0 else float("nan")
    row5_triggered = (not np.isnan(ratio)) and (ratio > shift_mult or ratio < 1.0 / shift_mult)
    print(f"sensitivity ratio (excl/with): {ratio:.4f} (escalation if >{shift_mult} or <{1/shift_mult:.4f})")

    # T4e - sortable full-population index data
    idx = events[["ticker", "event_date_canonical", "momentum_pct", "decile"]].copy()
    idx = idx.merge(min_window, on=["ticker", "event_date_canonical", "momentum_pct"], how="left")
    idx = idx.merge(per_event_summary[["ticker", "event_date_canonical", "momentum_pct", "minutes_to_50pct", "open_close_abs_move", "denom_is_zero"]],
                     on=["ticker", "event_date_canonical", "momentum_pct"], how="left")
    idx.to_parquet(OUT_INDEX_DATA, index=False)
    print(f"T4e index data: {len(idx)} events -> {OUT_INDEX_DATA}")

    summary = {
        "phase": "6", "task": "T4",
        "n_events": len(events),
        "grid_rows": len(grid),
        "headline": {
            "pooled_median_minutes_to_50pct_move_with_minute0": crossing,
            "pooled_median_minutes_to_50pct_move_excl_minute0": crossing_sens,
            "sensitivity_ratio_excl_over_with": ratio,
            "min_window_median_minutes": {
                f"{x}pct": float(min_window[f"min_window_{x}pct_minutes"].median()) for x in thresholds_pct
            },
        },
        "denom_zero_events": int(per_event_summary["denom_is_zero"].sum()),
        "min_never_crossed_50pct": {
            "with_minute0": int(per_event_summary["minutes_to_50pct"].isna().sum()),
            "excl_minute0": int(per_event_summary_sens["minutes_to_50pct"].isna().sum()),
        },
        "escalation_row5_triggered": bool(row5_triggered),
        "escalation_row5_threshold": shift_mult,
        "source": "research/phase_6/t4_measurements.py:main",
        "artifacts": {
            "concentration_curves": OUT_CONCENTRATION, "min_window_stats": OUT_MIN_WINDOW,
            "min_window_stats_sens": OUT_MIN_WINDOW_SENS, "opportunity_decay": OUT_DECAY_SUMMARY,
            "opportunity_decay_sens": OUT_DECAY_SUMMARY_SENS, "pooled_decay": OUT_POOLED,
            "pooled_decay_sens": OUT_POOLED_SENS, "event_index": OUT_INDEX_DATA,
        },
    }
    with open(OUT_SUMMARY, "w") as f:
        json.dump(summary, f, indent=2, default=str)
    print(json.dumps(summary, indent=2, default=str))

    if row5_triggered:
        print(f"\n*** ESCALATION row 5: sensitivity ratio {ratio:.2f} exceeds {shift_mult}x either direction - HARD STOP ***")


if __name__ == "__main__":
    main()
