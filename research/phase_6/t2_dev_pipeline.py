"""
Phase 6 T2 - dev-tier minute-bar builder + measurement pipeline, against
filtered_trades_dev_v4 (56 events, both cohorts). Verifies the exact code
path (research/phase_6/build_minute_bars.py, research/phase_6/measurements.py)
that T3 will run once, unmodified, against the full filtered_trades table.
"""
import json
import time

import duckdb
import pandas as pd

from research.phase_6.build_minute_bars import build_session_spine, build_minute_bars, verify_bars
from research.phase_6 import measurements as M

DB_PATH = "data/duckdb/main.duckdb"
PHASE_6_CONFIG = "config/phase_6.json"
PRIMARY_MANIFEST = "results/phase_5a/artifacts/dev_v4_primary_events.parquet"
SIDECAR_MANIFEST = "results/phase_5a/artifacts/dev_v4_sidecar_events.parquet"
DEV_BARS_TABLE = "event_minute_bars_dev_v4"
# Flat under artifacts/ (not a dev_tier/ subfolder) so the *.parquet gitignore
# pattern (results/phase_*/artifacts/*.parquet - one level only) actually
# reaches these regenerable dev-tier outputs, matching every prior phase's
# artifact layout convention.
OUT_DIR = "results/phase_6/artifacts"
OUT_SUMMARY = "results/phase_6/artifacts/t2_dev_pipeline_summary.json"


def load_dev_manifest():
    primary = pd.read_parquet(PRIMARY_MANIFEST)
    sidecar = pd.read_parquet(SIDECAR_MANIFEST)
    cols = ["ticker", "event_date_canonical", "momentum_pct", "dev_cohort", "trades_bitmap", "quotes_bitmap"]
    manifest = pd.concat([primary[cols], sidecar[cols]], ignore_index=True)
    return manifest


def sidecar_bitmap_check(con, bars_table, manifest, offsets):
    sidecar = manifest[manifest["dev_cohort"] == "flagged_sidecar"]
    bars_offsets = con.execute(f"""
        SELECT ticker, event_date_canonical, momentum_pct, session_offset, COUNT(*) AS n_bars
        FROM {bars_table}
        GROUP BY 1,2,3,4
    """).fetchdf()
    bars_offsets["event_date_canonical"] = pd.to_datetime(bars_offsets["event_date_canonical"])

    mismatches = []
    for row in sidecar.itertuples():
        d = pd.to_datetime(row.event_date_canonical)
        sub = bars_offsets[
            (bars_offsets["ticker"] == row.ticker) &
            (bars_offsets["event_date_canonical"] == d) &
            (abs(bars_offsets["momentum_pct"] - row.momentum_pct) < 1e-6)
        ]
        present_offsets = set(sub["session_offset"].tolist())
        for i, off in enumerate(offsets):
            bitmap_says_present = row.trades_bitmap[i] == "1"
            has_bars = off in present_offsets
            if bitmap_says_present != has_bars:
                mismatches.append({
                    "ticker": row.ticker, "event_date_canonical": str(d.date()), "session_offset": off,
                    "trades_bitmap": row.trades_bitmap, "bitmap_says_present": bitmap_says_present,
                    "has_bars": has_bars,
                })
    return mismatches


def _render_eyeball_preview(concentration, pooled, pooled_sens, crossing, crossing_sens, out_path):
    """Informal dev-tier QA render only - not a Chart Contract deliverable
    (those are built to spec in T5). Just enough to eyeball sane shapes
    before committing to the full-tier run."""
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots

    fig = make_subplots(rows=1, cols=2, subplot_titles=(
        "Volume concentration (per-event, dev n=56)", "Opportunity decay - pooled median (dev n=56)"))

    for (ticker, d, mom), sub in concentration.groupby(["ticker", "event_date_canonical", "momentum_pct"]):
        sub = sub.sort_values("time_share")
        fig.add_trace(go.Scatter(x=sub["time_share"], y=sub["volume_share"], mode="lines",
                                  line=dict(width=1, color="rgba(80,120,200,0.35)"), showlegend=False), row=1, col=1)
    fig.add_shape(type="line", x0=0, y0=0, x1=1, y1=1, line=dict(dash="dot", color="gray"), row=1, col=1)

    fig.add_trace(go.Scatter(x=pooled["minute_index"], y=pooled["median"], mode="lines",
                              name=f"with minute 0 (crosses {crossing:.0f}m)", line=dict(color="crimson")), row=1, col=2)
    fig.add_trace(go.Scatter(x=pooled_sens["minute_index"], y=pooled_sens["median"], mode="lines",
                              name=f"excl minute 0 (crosses {crossing_sens:.0f}m)", line=dict(color="teal")), row=1, col=2)
    fig.add_hline(y=0.5, line=dict(dash="dot", color="gray"), row=1, col=2)

    fig.update_xaxes(title_text="session time share", row=1, col=1)
    fig.update_yaxes(title_text="cum volume share", row=1, col=1)
    fig.update_xaxes(title_text="minutes since open", row=1, col=2)
    fig.update_yaxes(title_text="pooled median realized-move fraction", row=1, col=2)
    fig.update_layout(title="Phase 6 T2 dev-tier eyeball preview (n=56, informal QA only)", height=450, width=1000)
    fig.write_html(out_path)
    print(f"dev-tier eyeball preview written: {out_path}")


def main():
    with open(PHASE_6_CONFIG) as f:
        cfg = json.load(f)
    offsets = cfg["offsets"]
    thresholds_pct = cfg["min_window_thresholds_pct"]
    excl_minute = cfg["opening_print_sensitivity"]["exclude_minute_index"]

    import os
    os.makedirs(OUT_DIR, exist_ok=True)

    manifest = load_dev_manifest()
    print(f"dev manifest: {len(manifest)} events ({(manifest['dev_cohort']=='primary').sum()} primary, {(manifest['dev_cohort']=='flagged_sidecar').sum()} sidecar)")

    spine = build_session_spine(manifest, cfg)
    print(f"session spine: {len(spine)} (event,offset) rows")

    con = duckdb.connect(DB_PATH, read_only=False)
    build_result = build_minute_bars(con, "filtered_trades_dev_v4", spine, DEV_BARS_TABLE)
    elapsed = build_result["elapsed_seconds"]
    print(f"build_minute_bars: {elapsed:.3f}s")

    verify = verify_bars(con, DEV_BARS_TABLE, spine)
    print(f"verify: {verify}")

    mismatches = sidecar_bitmap_check(con, DEV_BARS_TABLE, manifest, offsets)
    print(f"sidecar bitmap mismatches: {len(mismatches)}")

    n_bar_rows = con.execute(f"SELECT COUNT(*) FROM {DEV_BARS_TABLE}").fetchone()[0]
    n_events_bars = con.execute(f"SELECT COUNT(DISTINCT (ticker,event_date_canonical,momentum_pct)) FROM {DEV_BARS_TABLE}").fetchone()[0]
    by_offset = con.execute(f"""
        SELECT session_offset, COUNT(DISTINCT (ticker,event_date_canonical,momentum_pct)) AS n_events, COUNT(*) AS n_bar_rows
        FROM {DEV_BARS_TABLE} GROUP BY session_offset ORDER BY session_offset
    """).fetchdf()
    print(by_offset)

    excluded_t0 = build_result["excluded_t0"]
    excluded_t0["excluded_share"] = excluded_t0["n_excluded"] / excluded_t0["n_total"].replace(0, pd.NA)
    high_excluded = excluded_t0[excluded_t0["excluded_share"] > 0.5]

    bars_t0 = con.execute(f"""
        SELECT ticker, event_date_canonical, momentum_pct, minute_index, n_trades, volume, vwap,
               high, low, first_price, last_price
        FROM {DEV_BARS_TABLE} WHERE session_offset = 0
    """).fetchdf()
    con.close()

    session_minutes = M.session_minutes_from_spine(spine, offset=0)
    grid = M.build_full_grid(bars_t0, session_minutes)

    concentration = M.compute_concentration_curves(grid)
    min_window = M.compute_min_window_stats(grid, thresholds_pct, min_minute_included=0)
    per_minute, per_event_summary = M.compute_opportunity_decay(grid, min_minute_included=0)
    pooled = M.pooled_per_minute_quantiles(per_minute)
    crossing = M.pooled_median_crossing_minute(pooled)

    min_window_sens = M.compute_min_window_stats(grid, thresholds_pct, min_minute_included=excl_minute + 1)
    per_minute_sens, per_event_summary_sens = M.compute_opportunity_decay(grid, min_minute_included=excl_minute + 1)
    pooled_sens = M.pooled_per_minute_quantiles(per_minute_sens)
    crossing_sens = M.pooled_median_crossing_minute(pooled_sens)

    concentration.to_parquet(f"{OUT_DIR}/concentration_curves_dev.parquet", index=False)
    min_window.to_parquet(f"{OUT_DIR}/min_window_stats_dev.parquet", index=False)
    per_event_summary.to_parquet(f"{OUT_DIR}/opportunity_decay_dev.parquet", index=False)
    pooled.to_parquet(f"{OUT_DIR}/pooled_decay_dev.parquet", index=False)
    min_window_sens.to_parquet(f"{OUT_DIR}/min_window_stats_sens_dev.parquet", index=False)
    per_event_summary_sens.to_parquet(f"{OUT_DIR}/opportunity_decay_sens_dev.parquet", index=False)
    pooled_sens.to_parquet(f"{OUT_DIR}/pooled_decay_sens_dev.parquet", index=False)

    print(f"dev-tier pooled median crossing minute (with minute 0): {crossing}")
    print(f"dev-tier pooled median crossing minute (excl minute 0): {crossing_sens}")

    _render_eyeball_preview(concentration, pooled, pooled_sens, crossing, crossing_sens, f"{OUT_DIR}/dev_tier_preview.html")

    runtime_ok = elapsed < cfg["escalation_thresholds"]["dev_tier_max_seconds_per_pass"]
    integrity_ok = verify["duplicate_keys"] == 0 and verify["out_of_session_minute_indices"] == 0
    sidecar_ok = len(mismatches) == 0

    summary = {
        "phase": "6", "task": "T2",
        "manifest_n": len(manifest),
        "spine_rows": len(spine),
        "build": {"elapsed_seconds": round(elapsed, 3), "max_seconds": cfg["escalation_thresholds"]["dev_tier_max_seconds_per_pass"], "pass": runtime_ok},
        "bars": {"n_rows": int(n_bar_rows), "n_distinct_events": int(n_events_bars), "by_offset": by_offset.to_dict(orient="records")},
        "verify_integrity": {**verify, "pass": integrity_ok},
        "sidecar_bitmap_check": {"n_mismatches": len(mismatches), "mismatches": mismatches, "pass": sidecar_ok},
        "excluded_row_share_t0": {
            "max_share": float(excluded_t0["excluded_share"].max()) if len(excluded_t0) else None,
            "n_events_over_50pct_excluded": int(len(high_excluded)),
            "flagged_events": high_excluded[["ticker", "event_date_canonical", "n_in_session", "n_excluded", "n_total", "excluded_share"]].to_dict(orient="records"),
        },
        "dev_measurements_preview": {
            "concentration_curve_rows": len(concentration),
            "min_window_events": len(min_window),
            "opportunity_decay_events": len(per_event_summary),
            "pooled_median_crossing_minute_with_minute0": crossing,
            "pooled_median_crossing_minute_excl_minute0": crossing_sens,
            "denom_zero_events": int(per_event_summary["denom_is_zero"].sum()),
        },
        "escalation_row3_triggered": not integrity_ok,
        "escalation_row6_triggered": not runtime_ok,
        "source": "research/phase_6/t2_dev_pipeline.py:main",
    }
    with open(OUT_SUMMARY, "w") as f:
        json.dump(summary, f, indent=2, default=str)
    print(json.dumps(summary, indent=2, default=str))

    if not integrity_ok:
        print("\n*** ESCALATION row 3: bar integrity violation - HARD STOP ***")
    if not runtime_ok:
        print(f"\n*** ESCALATION row 6: dev-tier runtime {elapsed:.1f}s > {cfg['escalation_thresholds']['dev_tier_max_seconds_per_pass']}s - HARD STOP ***")
    if not sidecar_ok:
        print(f"\n*** WARNING: {len(mismatches)} sidecar bitmap/bars mismatches - see summary ***")


if __name__ == "__main__":
    main()
