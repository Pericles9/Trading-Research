"""
Phase 6b T2 - dev-tier extended-day minute-bar builder + measurement
pipeline, against filtered_trades_dev_v4 (56 events, both cohorts).
Verifies the exact code path (build_minute_bars_v2.py, measurements_v2.py)
that T3 will run once, unmodified, against the full filtered_trades table.
"""
import json
import os

import duckdb
import pandas as pd

from research.phase_6b.build_minute_bars_v2 import build_session_spine_v2, build_minute_bars_v2, verify_bars_v2
from research.phase_6b import measurements_v2 as M2

DB_PATH = "data/duckdb/main.duckdb"
PHASE_6B_CONFIG = "config/phase_6b.json"
PRIMARY_MANIFEST = "results/phase_5a/artifacts/dev_v4_primary_events.parquet"
SIDECAR_MANIFEST = "results/phase_5a/artifacts/dev_v4_sidecar_events.parquet"
DEV_BARS_TABLE = "event_minute_bars_dev_v2"
OUT_DIR = "results/phase_6b/artifacts"
OUT_SUMMARY = "results/phase_6b/artifacts/t2_dev_pipeline_summary.json"


def load_dev_manifest():
    primary = pd.read_parquet(PRIMARY_MANIFEST)
    sidecar = pd.read_parquet(SIDECAR_MANIFEST)
    cols = ["ticker", "event_date_canonical", "momentum_pct", "dev_cohort", "trades_bitmap", "quotes_bitmap"]
    return pd.concat([primary[cols], sidecar[cols]], ignore_index=True)


def load_tick_anchor(con, bars_table):
    """A8.2/D4: tick_close_t_minus_1_rth per event, from the bar cache (offset -1,
    segment in {premarket, rth}) - the tick-derived last trade at/before the T-1 RTH
    close. Replaces the pre-D4 spine prev_close anchor. No spine column read."""
    tm1 = con.execute(f"""
        SELECT ticker, event_date_canonical, momentum_pct, session_offset, segment, minute_index, last_price
        FROM {bars_table} WHERE session_offset = -1 AND segment IN ('premarket', 'rth')
    """).fetchdf()
    anchor = M2.compute_tick_close_t_minus_1_rth(tm1)
    anchor["event_date_canonical"] = pd.to_datetime(anchor["event_date_canonical"])
    return anchor


def sidecar_bitmap_check(con, bars_table, manifest, offsets):
    sidecar = manifest[manifest["dev_cohort"] == "flagged_sidecar"]
    bars_offsets = con.execute(f"""
        SELECT ticker, event_date_canonical, momentum_pct, session_offset, COUNT(*) AS n_bars
        FROM {bars_table} GROUP BY 1,2,3,4
    """).fetchdf()
    bars_offsets["event_date_canonical"] = pd.to_datetime(bars_offsets["event_date_canonical"])
    mismatches = []
    for row in sidecar.itertuples():
        d = pd.to_datetime(row.event_date_canonical)
        sub = bars_offsets[(bars_offsets["ticker"] == row.ticker) & (bars_offsets["event_date_canonical"] == d) &
                            (abs(bars_offsets["momentum_pct"] - row.momentum_pct) < 1e-6)]
        present_offsets = set(sub["session_offset"].tolist())
        for i, off in enumerate(offsets):
            bitmap_present = row.trades_bitmap[i] == "1"
            has_bars = off in present_offsets
            if bitmap_present != has_bars:
                mismatches.append({"ticker": row.ticker, "event_date_canonical": str(d.date()), "session_offset": off,
                                    "trades_bitmap": row.trades_bitmap, "bitmap_says_present": bitmap_present, "has_bars": has_bars})
    return mismatches


def main():
    with open(PHASE_6B_CONFIG) as f:
        cfg = json.load(f)
    offsets = cfg["offsets"]
    thresholds_pct = cfg["min_window_thresholds_pct"]
    os.makedirs(OUT_DIR, exist_ok=True)

    manifest = load_dev_manifest()
    print(f"dev manifest: {len(manifest)} events ({(manifest['dev_cohort']=='primary').sum()} primary, {(manifest['dev_cohort']=='flagged_sidecar').sum()} sidecar)")

    spine = build_session_spine_v2(manifest, cfg)
    print(f"session spine v2: {len(spine)} (event,offset) rows, {int(spine['is_early_close'].sum())} early-close sessions")

    con = duckdb.connect(DB_PATH, read_only=False)
    build_result = build_minute_bars_v2(con, "filtered_trades_dev_v4", spine, DEV_BARS_TABLE)
    elapsed = build_result["elapsed_seconds"]
    print(f"build_minute_bars_v2: {elapsed:.3f}s")

    verify = verify_bars_v2(con, DEV_BARS_TABLE, spine)
    print(f"verify: {verify}")

    mismatches = sidecar_bitmap_check(con, DEV_BARS_TABLE, manifest, offsets)
    print(f"sidecar bitmap mismatches: {len(mismatches)}")

    tz = build_result["tz_mismatch"].iloc[0]
    n_mismatch = int(tz["n_mismatch"] or 0)
    n_total_rows = int(tz["n_total_rows"] or 0)
    print(f"ET-vs-UTC date mismatch: {n_mismatch}/{n_total_rows} rows ({100.0*n_mismatch/max(n_total_rows,1):.4f}%)")

    example_mismatches = []
    if n_mismatch > 0:
        con.execute("INSTALL icu"); con.execute("LOAD icu")
        example_mismatches = con.execute(f"""
            SELECT ticker, sip_timestamp,
                   TO_TIMESTAMP(sip_timestamp/1e9) AS utc_ts,
                   TO_TIMESTAMP(sip_timestamp/1e9) AT TIME ZONE 'America/New_York' AS et_ts
            FROM filtered_trades_dev_v4
            WHERE CAST(TO_TIMESTAMP(sip_timestamp/1e9) AT TIME ZONE 'America/New_York' AS DATE)
                != CAST(TO_TIMESTAMP(sip_timestamp/1e9) AS DATE)
            LIMIT 5
        """).fetchdf().to_dict(orient="records")

    n_bar_rows = con.execute(f"SELECT COUNT(*) FROM {DEV_BARS_TABLE}").fetchone()[0]
    by_offset = con.execute(f"""
        SELECT session_offset, COUNT(DISTINCT (ticker,event_date_canonical,momentum_pct)) AS n_events, COUNT(*) AS n_bar_rows
        FROM {DEV_BARS_TABLE} GROUP BY session_offset ORDER BY session_offset
    """).fetchdf()
    print(by_offset)

    excluded_t0 = build_result["excluded_t0"]
    import numpy as np
    excluded_t0["excluded_share"] = np.where(excluded_t0["n_total"] > 0, excluded_t0["n_excluded"] / excluded_t0["n_total"], np.nan)

    bars_t0 = con.execute(f"""
        SELECT ticker, event_date_canonical, momentum_pct, segment, minute_index, n_trades, volume, vwap,
               high, low, first_price, last_price
        FROM {DEV_BARS_TABLE} WHERE session_offset = 0
    """).fetchdf()
    tick_anchor_df = load_tick_anchor(con, DEV_BARS_TABLE)  # A8.2/D4: tick anchor, not spine prev_close
    con.close()

    session_bounds = M2.session_bounds_from_spine(spine, offset=0)
    grid = M2.build_full_grid(bars_t0, session_bounds)

    concentration = M2.compute_concentration_curves(grid)
    min_window = M2.compute_min_window_stats(grid, thresholds_pct, min_minute_included=0)
    day_high_ext = M2.compute_day_high_ext(bars_t0)
    segment_shares = M2.compute_segment_shares(bars_t0)

    id_map = grid[M2.EVENT_KEYS + ["event_id"]].drop_duplicates()
    id_map["event_date_canonical"] = pd.to_datetime(id_map["event_date_canonical"])
    anchor_by_id = id_map.merge(tick_anchor_df, on=M2.EVENT_KEYS, how="left").set_index("event_id")["tick_close_t_minus_1_rth"]
    dh_by_id = id_map.merge(day_high_ext, on=M2.EVENT_KEYS, how="left").set_index("event_id")["day_high_ext"]

    per_minute, per_event_summary = M2.compute_primary_opportunity_decay(grid, anchor_by_id, dh_by_id)
    pooled = M2.pooled_per_minute_quantiles(per_minute)
    crossing = M2.pooled_median_crossing_minute(pooled)
    n_no_anchor = int((~per_event_summary["has_t_minus_1_rth"]).sum())
    n_denom_nonpos = int(per_event_summary["denom_nonpositive"].sum())
    print(f"dev-tier primary pooled median crossing minute (since 04:00 ET): {crossing}")
    print(f"dev-tier has_t_minus_1_rth=FALSE: {n_no_anchor}/{len(per_event_summary)} | denom_nonpositive: {n_denom_nonpos}")

    per_minute_rth, per_event_summary_rth = M2.compute_rth_legacy_decay(bars_t0, session_bounds)
    pooled_rth = M2.pooled_per_minute_quantiles(per_minute_rth)
    crossing_rth = M2.pooled_median_crossing_minute(pooled_rth)
    print(f"dev-tier rth_legacy pooled median crossing minute (since RTH open): {crossing_rth}")

    concentration.to_parquet(f"{OUT_DIR}/concentration_curves_v2_dev.parquet", index=False)
    min_window.to_parquet(f"{OUT_DIR}/min_window_stats_v2_dev.parquet", index=False)
    segment_shares.to_parquet(f"{OUT_DIR}/segment_shares_dev.parquet", index=False)
    per_event_summary.to_parquet(f"{OUT_DIR}/opportunity_decay_primary_dev.parquet", index=False)
    per_event_summary_rth.to_parquet(f"{OUT_DIR}/opportunity_decay_rth_legacy_dev.parquet", index=False)

    runtime_ok = elapsed < cfg["escalation_thresholds"]["dev_tier_max_seconds_per_pass"]
    integrity_ok = verify["duplicate_keys"] == 0 and verify["out_of_window_minute_indices"] == 0 and verify["bad_segment_labels"] == 0
    sidecar_ok = len(mismatches) == 0

    summary = {
        "phase": "6b", "task": "T2",
        "manifest_n": len(manifest), "spine_rows": len(spine),
        "build": {"elapsed_seconds": round(elapsed, 3), "max_seconds": cfg["escalation_thresholds"]["dev_tier_max_seconds_per_pass"], "pass": runtime_ok},
        "bars": {"n_rows": int(n_bar_rows), "by_offset": by_offset.to_dict(orient="records")},
        "verify_integrity": {**verify, "pass": integrity_ok},
        "sidecar_bitmap_check": {"n_mismatches": len(mismatches), "mismatches": mismatches, "pass": sidecar_ok},
        "tz_cross_check": {"n_mismatch": n_mismatch, "n_total_rows": n_total_rows,
                            "pct_mismatch": round(100.0 * n_mismatch / max(n_total_rows, 1), 6),
                            "examples": example_mismatches},
        "excluded_row_share_t0": {
            "max_share": float(excluded_t0["excluded_share"].max()) if len(excluded_t0) else None,
            "n_events_over_50pct_excluded": int((excluded_t0["excluded_share"] > 0.5).sum()),
        },
        "dev_measurements_preview": {
            "concentration_curve_rows": len(concentration), "min_window_events": len(min_window),
            "segment_shares_events": len(segment_shares),
            "primary_anchor": "tick_close_t_minus_1_rth (A8.2/D4 - tick-only, replaces the quarantined spine close anchor)",
            "primary_pooled_median_crossing_minute_since_0400et": crossing,
            "rth_legacy_pooled_median_crossing_minute_since_open": crossing_rth,
            "has_t_minus_1_rth_false_events": n_no_anchor,
            "denom_nonpositive_events": n_denom_nonpos,
        },
        "escalation_row2_triggered": False,
        "escalation_row6_triggered": not runtime_ok,
        "source": "research/phase_6b/t2_dev_pipeline.py:main",
    }
    with open(OUT_SUMMARY, "w") as f:
        json.dump(summary, f, indent=2, default=str)
    print(json.dumps(summary, indent=2, default=str))

    if not integrity_ok:
        print("\n*** ESCALATION: bar integrity violation - HARD STOP ***")
    if not runtime_ok:
        print(f"\n*** ESCALATION row 6: dev-tier runtime {elapsed:.1f}s > threshold - HARD STOP ***")
    if not sidecar_ok:
        print(f"\n*** WARNING: {len(mismatches)} sidecar bitmap/bars mismatches ***")


if __name__ == "__main__":
    main()
