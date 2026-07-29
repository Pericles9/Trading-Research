"""
Phase 6b A6.3b (T4) - measurements from event_minute_bars_v2 only. No further
full passes over filtered_trades (reads the bar cache + builds the spine via
calendar arithmetic, which is 6b's design, not a table scan).

Primary opportunity-decay anchors on the tick-derived tick_close_t_minus_1_rth
(A8.2/D4). rth_legacy re-runs Phase 6's original RTH-open-anchored decay on
v2's rth-segment bars for direct comparability to Phase 6's 52/57.
"""
import json

import numpy as np
import pandas as pd

from research.phase_6b.build_minute_bars_v2 import build_session_spine_v2
from research.phase_6b import measurements_v2 as M2

DB_PATH = "data/duckdb/main.duckdb"
PHASE_6B_CONFIG = "config/phase_6b.json"
ELIGIBLE_EVENTS = "results/phase_6b/artifacts/t1_eligible_events.parquet"
BARS_TABLE = "event_minute_bars_v2"
A = "results/phase_6b/artifacts"
OUT_SUMMARY = f"{A}/t4_measurements_v2_summary.json"


def compute_deciles(events, cfg):
    return pd.qcut(events["momentum_pct"], 10, labels=False, duplicates="drop")


def main():
    import duckdb
    with open(PHASE_6B_CONFIG) as f:
        cfg = json.load(f)
    thresholds = cfg["min_window_thresholds_pct"]

    events = pd.read_parquet(ELIGIBLE_EVENTS)
    events["event_date_canonical"] = pd.to_datetime(events["event_date_canonical"])
    events["decile"] = compute_deciles(events, cfg)
    print(f"eligible events: {len(events)}")

    print("building extended-day spine (for session bounds; no table scan)...")
    spine = build_session_spine_v2(events, cfg)
    session_bounds = M2.session_bounds_from_spine(spine, offset=0)

    con = duckdb.connect(DB_PATH, read_only=True)
    bars_t0 = con.execute(f"""
        SELECT ticker, event_date_canonical, momentum_pct, segment, minute_index, n_trades, volume, vwap,
               high, low, first_price, last_price
        FROM {BARS_TABLE} WHERE session_offset = 0
    """).fetchdf()
    tm1 = con.execute(f"""
        SELECT ticker, event_date_canonical, momentum_pct, session_offset, segment, minute_index, last_price
        FROM {BARS_TABLE} WHERE session_offset = -1 AND segment IN ('premarket','rth')
    """).fetchdf()
    con.close()
    bars_t0["event_date_canonical"] = pd.to_datetime(bars_t0["event_date_canonical"])
    tm1["event_date_canonical"] = pd.to_datetime(tm1["event_date_canonical"])
    print(f"bars_t0: {len(bars_t0)} rows | tm1 pre/rth: {len(tm1)} rows")

    grid = M2.build_full_grid(bars_t0, session_bounds)

    # T4a concentration, T4b min-window, T4c segment shares
    concentration = M2.compute_concentration_curves(grid)
    min_window = M2.compute_min_window_stats(grid, thresholds, min_minute_included=0)
    segment_shares = M2.compute_segment_shares(bars_t0)

    # T4d primary opportunity-decay (tick anchor)
    day_high_ext = M2.compute_day_high_ext(bars_t0)
    tick_anchor = M2.compute_tick_close_t_minus_1_rth(tm1)
    id_map = grid[M2.EVENT_KEYS + ["event_id"]].drop_duplicates()
    anchor_by_id = id_map.merge(tick_anchor, on=M2.EVENT_KEYS, how="left").set_index("event_id")["tick_close_t_minus_1_rth"]
    dh_by_id = id_map.merge(day_high_ext, on=M2.EVENT_KEYS, how="left").set_index("event_id")["day_high_ext"]
    per_minute, per_event = M2.compute_primary_opportunity_decay(grid, anchor_by_id, dh_by_id)
    pooled = M2.pooled_per_minute_quantiles(per_minute)
    crossing = M2.pooled_median_crossing_minute(pooled)

    n_has_anchor = int(per_event["has_t_minus_1_rth"].sum())
    n_no_anchor = int((~per_event["has_t_minus_1_rth"]).sum())
    n_denom_nonpos = int(per_event["denom_nonpositive"].sum())

    # headline_b: realized(t) at each event's own RTH-open minute (extended-day clock)
    per_minute_id = per_minute.merge(id_map, on=M2.EVENT_KEYS, how="left")
    rth_open_by_id = id_map.merge(session_bounds[M2.EVENT_KEYS + ["rth_open_min"]], on=M2.EVENT_KEYS, how="left") \
        .set_index("event_id")["rth_open_min"]
    realized_at_open = M2.realized_at_minute(per_minute_id, rth_open_by_id)

    # headline_c: ET clock time-of-day of day_high_ext. high_time_of_day builds its lookup
    # key as (ticker, event_date_canonical, momentum_pct) off bars_t0 (whose momentum_pct is
    # the cache's ROUND(,2) value), so key the premarket-start map the same way - round the
    # spine's momentum_pct to 2dp and use the same to_datetime, so the tuple map matches.
    bars_t0["momentum_pct"] = bars_t0["momentum_pct"].round(2)
    pm_start_by_key = spine[spine["session_offset"] == 0].drop_duplicates(M2.EVENT_KEYS).copy()
    pm_start_by_key["event_key"] = list(zip(pm_start_by_key["ticker"],
                                            pd.to_datetime(pm_start_by_key["event_date_canonical"]),
                                            pm_start_by_key["momentum_pct"].round(2)))
    pm_start_map = pm_start_by_key.set_index("event_key")["premarket_start_et"]
    high_tod = M2.high_time_of_day(bars_t0, pm_start_map)

    # T4e rth_legacy comparability
    per_minute_rth, per_event_rth = M2.compute_rth_legacy_decay(bars_t0, session_bounds)
    pooled_rth = M2.pooled_per_minute_quantiles(per_minute_rth)
    crossing_rth = M2.pooled_median_crossing_minute(pooled_rth)

    # persist artifacts
    concentration.to_parquet(f"{A}/concentration_curves_v2.parquet", index=False)
    min_window.to_parquet(f"{A}/min_window_stats_v2.parquet", index=False)
    segment_shares.to_parquet(f"{A}/segment_shares.parquet", index=False)
    per_minute.to_parquet(f"{A}/opportunity_decay_primary_per_minute.parquet", index=False)
    per_event.to_parquet(f"{A}/opportunity_decay_primary.parquet", index=False)
    pooled.to_parquet(f"{A}/pooled_decay_primary.parquet", index=False)
    per_minute_rth.to_parquet(f"{A}/opportunity_decay_rth_legacy_per_minute.parquet", index=False)
    per_event_rth.to_parquet(f"{A}/opportunity_decay_rth_legacy.parquet", index=False)
    pooled_rth.to_parquet(f"{A}/pooled_decay_rth_legacy.parquet", index=False)
    high_tod.to_parquet(f"{A}/high_time_of_day.parquet", index=False)

    # flag_has_dup_prints (A6.3a row-7 disposition, Cooper flag-and-proceed): the 7 events
    # exact-confirmed to carry duplicate prints in filtered_trades (a63a_dup_recheck.json).
    # Annotation only - not dropped; volume-based measures for these events are inflated by
    # their dup rate, price-path decay is unaffected.
    with open(f"{A}/a63a_dup_recheck.json") as f:
        recheck = json.load(f)
    dup_keys = {(e["ticker"], pd.Timestamp(e["event_date"]), round(float(e["m"]), 2))
                for e in recheck["real_duplication_events"]}
    events["flag_has_dup_prints"] = events.apply(
        lambda r: (r["ticker"], pd.Timestamp(r["event_date_canonical"]), round(float(r["momentum_pct"]), 2)) in dup_keys, axis=1)
    n_flagged_dup = int(events["flag_has_dup_prints"].sum())

    # T4f sortable full-population index
    idx = events[["ticker", "event_date_canonical", "momentum_pct", "decile", "flag_has_dup_prints"]].copy()
    idx = idx.merge(segment_shares[M2.EVENT_KEYS + ["premarket_share", "rth_share", "post_share"]], on=M2.EVENT_KEYS, how="left")
    idx = idx.merge(min_window, on=M2.EVENT_KEYS, how="left")
    idx = idx.merge(per_event[M2.EVENT_KEYS + ["has_t_minus_1_rth", "denom_nonpositive", "minutes_to_50pct"]]
                    .rename(columns={"minutes_to_50pct": "minutes_to_50pct_primary"}), on=M2.EVENT_KEYS, how="left")
    idx = idx.merge(per_event_rth[M2.EVENT_KEYS + ["minutes_to_50pct"]]
                    .rename(columns={"minutes_to_50pct": "minutes_to_50pct_rth_legacy"}), on=M2.EVENT_KEYS, how="left")
    idx = idx.merge(high_tod[M2.EVENT_KEYS + ["high_hour_decimal"]], on=M2.EVENT_KEYS, how="left")
    ra = per_event.copy()  # per_event already carries event_id from compute_primary_opportunity_decay
    ra["realized_at_rth_open"] = ra["event_id"].map(realized_at_open)
    idx = idx.merge(ra[M2.EVENT_KEYS + ["realized_at_rth_open"]], on=M2.EVENT_KEYS, how="left")
    idx.to_parquet(f"{A}/event_index_v2.parquet", index=False)

    prim_pop = per_event[per_event["has_t_minus_1_rth"]]
    summary = {
        "phase": "6b", "task": "A6.3b (T4)",
        "n_events": len(events), "grid_rows": len(grid),
        "primary_anchor": "tick_close_t_minus_1_rth (A8.2/D4, tick-only)",
        "primary_population": {
            "n_has_t_minus_1_rth": n_has_anchor, "n_no_anchor_excluded": n_no_anchor,
            "n_denom_nonpositive": n_denom_nonpos,
            "pct_no_anchor": round(100.0 * n_no_anchor / len(events), 4),
            "pct_denom_nonpositive": round(100.0 * n_denom_nonpos / max(n_has_anchor, 1), 4),
        },
        "headlines": {
            "a_primary_pooled_median_crossing_minute_since_0400et": crossing,
            "b_realized_at_rth_open_median": float(np.nanmedian(realized_at_open.to_numpy())) if len(realized_at_open) else None,
            "c_high_time_of_day_median_hour_et": float(high_tod["high_hour_decimal"].median()),
            "rth_legacy_pooled_median_crossing_minute_since_open": crossing_rth,
            "min_window_median_minutes": {f"{x}pct": float(min_window[f"min_window_{x}pct_minutes"].median()) for x in thresholds},
            "segment_volume_share_medians": {s: float(segment_shares[f"{s}_share"].median()) for s in ["premarket", "rth", "post"]},
        },
        "primary_minutes_to_50pct_median_over_anchored": float(prim_pop["minutes_to_50pct"].median()),
        "n_never_crossed_primary": int(prim_pop["minutes_to_50pct"].isna().sum()),
        "flag_has_dup_prints_n": n_flagged_dup,
        "flag_has_dup_prints_note": "7 events exact-confirmed with duplicate prints (a63a_dup_recheck.json); annotation only (Cooper flag-and-proceed), volume-based measures inflated for these, price-path decay unaffected",
        "source": "research/phase_6b/t4_measurements_v2.py:main",
    }
    with open(OUT_SUMMARY, "w") as f:
        json.dump(summary, f, indent=2, default=str)
    print(json.dumps(summary, indent=2, default=str))


if __name__ == "__main__":
    main()
