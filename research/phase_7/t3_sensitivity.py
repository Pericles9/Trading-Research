"""
Phase 7 T3 - latency-budget sensitivity to the flagged 736.

METHOD (forced by the phase's zero-full-table-pass AND no-calendar-arithmetic
budget): every crossing/median is computed by re-pooling Phase 6's already-
materialized per-event/per-minute artifacts (the direct output of Phase 6 T4's
computation over event_minute_bars_v1), filtered/re-pooled by event membership.
The session grid cannot be rebuilt here - that needs the XNYS spine (calendar
arithmetic, banned this phase) - so the pre-gridded per-minute realized-move-
fraction is the reuse point, exactly as config/phase_7.json pins. This is a
genuine re-aggregation of 6.1M per-event rows, not a re-read of the pooled
summary.

FLAG SOURCE: the flagged-event membership is the 736-key set from
t3_excluded_t0_rows.parquet WHERE excluded_share > 0.5. T2 proved this set is
byte-identical to the recreated view's flag_eth_dominant_t0=TRUE column (736
keys, 0 duplicate joins). The view's flag column is NOT queried directly:
EXPLAIN confirms DuckDB does not prune the view's trades_ingested/quotes_ingested
scans, so any SELECT of the flag would trigger the ~8.7B-row pass (escalation
row 11). Joining to the flag's definitional source is operationally identical
and scan-free.
"""
import json
import time

import duckdb
import numpy as np
import pandas as pd

from research.phase_6 import measurements as M

DB_PATH = "data/duckdb/main.duckdb"
PHASE_7_CONFIG = "config/phase_7.json"
ART = "results/phase_6_rth_only/artifacts"
ETH_SRC = f"{ART}/t3_excluded_t0_rows.parquet"
BARS_TABLE = "event_minute_bars_v1"

PER_MINUTE = f"{ART}/opportunity_decay_per_minute.parquet"
PER_MINUTE_SENS = f"{ART}/opportunity_decay_per_minute_sens.parquet"
MIN_WINDOW = f"{ART}/min_window_stats.parquet"
MIN_WINDOW_SENS = f"{ART}/min_window_stats_sens.parquet"

DEV_PRIMARY = "results/phase_5a/artifacts/dev_v4_primary_events.parquet"
DEV_SIDECAR = "results/phase_5a/artifacts/dev_v4_sidecar_events.parquet"
PHASE6_DEV_SUMMARY = f"{ART}/t2_dev_pipeline_summary.json"

OUT_PATH = "results/phase_7/artifacts/t3_sensitivity_summary.json"
THRESHOLDS_PCT = [25, 50, 75]


def _keyframe(df):
    """Return df with a normalized string key column for membership ops."""
    out = df.copy()
    out["_k_date"] = pd.to_datetime(out["event_date_canonical"]).dt.strftime("%Y-%m-%d")
    out["_k_mom"] = out["momentum_pct"].round(2)
    out["_key"] = list(zip(out["ticker"], out["_k_date"], out["_k_mom"]))
    return out


def _crossing(per_minute_df):
    pooled = M.pooled_per_minute_quantiles(per_minute_df)
    return M.pooled_median_crossing_minute(pooled), pooled


def _mw_medians(mw_df):
    return {f"{x}pct": float(mw_df[f"min_window_{x}pct_minutes"].median()) for x in THRESHOLDS_PCT}


def main():
    with open(PHASE_7_CONFIG) as f:
        cfg = json.load(f)
    repro = cfg["reproduction_targets"]
    esc_min = cfg["decay_shift_escalation_min"]
    thr = cfg["eth_dominant_threshold"]

    con = duckdb.connect(DB_PATH, read_only=True)

    # --- flagged 736 keys (== view flag_eth_dominant_t0, T2-verified, scan-free) ---
    flagged = con.execute(f"""
        SELECT ticker, CAST(CAST(event_date_canonical AS DATE) AS VARCHAR) AS d, ROUND(momentum_pct,2) AS m
        FROM read_parquet('{ETH_SRC}') WHERE excluded_share > {thr}
    """).fetchdf()
    flagged_keys = set(zip(flagged["ticker"], flagged["d"], flagged["m"]))
    assert len(flagged_keys) == 736, f"flagged key count {len(flagged_keys)} != 736"

    # ============ T3a - DEV TIER ============
    t_dev0 = time.perf_counter()
    dev = pd.concat([pd.read_parquet(DEV_PRIMARY), pd.read_parquet(DEV_SIDECAR)], ignore_index=True)
    dev_kf = _keyframe(dev)
    dev_keys = set(dev_kf["_key"])
    assert len(dev_keys) == 56, f"dev key count {len(dev_keys)} != 56"

    # 0 duplicate keys in the bar cache for the dev events (all offsets)
    con.execute("DROP TABLE IF EXISTS _dev_keys")
    con.register("_dev_df", dev_kf[["ticker", "_k_date", "_k_mom"]].rename(columns={"_k_date": "d", "_k_mom": "m"}))
    dev_dup = con.execute(f"""
        SELECT COUNT(*) FROM (
            SELECT b.ticker, b.event_date_canonical, b.momentum_pct, b.session_offset, b.minute_index, COUNT(*) c
            FROM {BARS_TABLE} b
            JOIN _dev_df d ON b.ticker=d.ticker
               AND CAST(b.event_date_canonical AS VARCHAR)=d.d AND ROUND(b.momentum_pct,2)=d.m
            GROUP BY 1,2,3,4,5 HAVING COUNT(*) > 1
        )
    """).fetchone()[0]

    # dev-tier pooling (subset of per-minute artifact) - the pipeline on the 56 dev events
    pm = pd.read_parquet(PER_MINUTE)
    pm_kf = _keyframe(pm)
    pm_s = pd.read_parquet(PER_MINUTE_SENS)
    pm_s_kf = _keyframe(pm_s)

    dev_pm = pm_kf[pm_kf["_key"].isin(dev_keys)]
    dev_pm_s = pm_s_kf[pm_s_kf["_key"].isin(dev_keys)]
    dev_cross_with, _ = _crossing(dev_pm)
    dev_cross_excl, _ = _crossing(dev_pm_s)
    dev_n = dev_pm[["ticker", "event_date_canonical", "momentum_pct"]].drop_duplicates().shape[0]

    # flag consistency (row 6): dev events flagged == dev events >50% in the Phase 6 dev artifact
    dev_flagged = sorted([k for k in dev_keys if k in flagged_keys])
    with open(PHASE6_DEV_SUMMARY) as f:
        p6dev = json.load(f)
    p6_dev_over50 = sorted([
        (e["ticker"], pd.to_datetime(e["event_date_canonical"]).strftime("%Y-%m-%d"), round(e["momentum_pct"], 2))
        if "momentum_pct" in e else (e["ticker"], None, None)
        for e in p6dev["excluded_row_share_t0"]["flagged_events"]
    ])
    # the Phase 6 dev artifact flagged_events lacks momentum_pct - match on (ticker, date) instead
    p6_over50_td = set((e["ticker"], pd.to_datetime(e["event_date_canonical"]).strftime("%Y-%m-%d"))
                       for e in p6dev["excluded_row_share_t0"]["flagged_events"])
    dev_flagged_td = set((k[0], k[1]) for k in dev_flagged)
    flag_consistency_ok = (dev_flagged_td == p6_over50_td)
    dev_runtime = time.perf_counter() - t_dev0

    row5_triggered = dev_runtime > 60
    row6_triggered = not flag_consistency_ok
    dev_dup_ok = dev_dup == 0

    # ============ T3b - REPRODUCTION (full D1) ============
    cross_all_with, _ = _crossing(pm_kf)
    cross_all_excl, _ = _crossing(pm_s_kf)
    n_all = pm_kf[["ticker", "event_date_canonical", "momentum_pct"]].drop_duplicates().shape[0]
    repro_ok = (cross_all_with == repro["crossing_with_min0"]) and (cross_all_excl == repro["crossing_excl_min0"])
    row7_triggered = not repro_ok

    # ============ T3c - SENSITIVITY (exclude flagged 736) ============
    pm_ex = pm_kf[~pm_kf["_key"].isin(flagged_keys)]
    pm_s_ex = pm_s_kf[~pm_s_kf["_key"].isin(flagged_keys)]
    cross_ex_with, _ = _crossing(pm_ex)
    cross_ex_excl, _ = _crossing(pm_s_ex)
    n_excl_flagged = pm_ex[["ticker", "event_date_canonical", "momentum_pct"]].drop_duplicates().shape[0]
    n_flagged_in_pm = n_all - n_excl_flagged

    delta_with = cross_ex_with - cross_all_with
    delta_excl = cross_ex_excl - cross_all_excl
    row8_triggered = (abs(delta_with) > esc_min) or (abs(delta_excl) > esc_min)

    # min-window medians, both populations, both min0 variants
    mw = _keyframe(pd.read_parquet(MIN_WINDOW))
    mw_s = _keyframe(pd.read_parquet(MIN_WINDOW_SENS))
    mw_ex = mw[~mw["_key"].isin(flagged_keys)]
    mw_s_ex = mw_s[~mw_s["_key"].isin(flagged_keys)]

    con.close()

    out = {
        "phase": "7", "task": "T3",
        "method": "re-pool Phase 6's per-minute realized-move-fraction artifacts (bar-cache-derived) by event membership; flag membership = 736-key set == view flag_eth_dominant_t0 (T2-verified, scan-free)",
        "flagged_n": 736,
        "t3a_dev_tier": {
            "n_dev_events": 56,
            "n_dev_in_per_minute": dev_n,
            "runtime_seconds": round(dev_runtime, 2),
            "runtime_ceiling": 60,
            "bar_cache_duplicate_keys_dev": int(dev_dup),
            "dev_flagged_events": [list(k) for k in dev_flagged],
            "phase6_dev_over50_ticker_date": sorted(list(p6_over50_td)),
            "flag_consistency_ok": bool(flag_consistency_ok),
            "dev_crossing_with_min0": dev_cross_with,
            "dev_crossing_excl_min0": dev_cross_excl,
            "escalation_row5_runtime_gt_60s": bool(row5_triggered),
            "escalation_row6_flag_inconsistency": bool(row6_triggered),
        },
        "t3b_reproduction": {
            "n": n_all,
            "crossing_with_min0": {"observed": cross_all_with, "target": repro["crossing_with_min0"], "match": cross_all_with == repro["crossing_with_min0"]},
            "crossing_excl_min0": {"observed": cross_all_excl, "target": repro["crossing_excl_min0"], "match": cross_all_excl == repro["crossing_excl_min0"]},
            "escalation_row7_reproduction_fail": bool(row7_triggered),
        },
        "t3c_sensitivity": {
            "n_full": n_all,
            "n_flagged_excluded": n_flagged_in_pm,
            "n_excl_flagged": n_excl_flagged,
            "n_excl_flagged_expected": 15027,
            "crossings": {
                "with_min0": {"full": cross_all_with, "excl_flagged": cross_ex_with, "delta": delta_with},
                "excl_min0": {"full": cross_all_excl, "excl_flagged": cross_ex_excl, "delta": delta_excl},
            },
            "min_window_medians": {
                "with_min0": {"full": _mw_medians(mw), "excl_flagged": _mw_medians(mw_ex)},
                "excl_min0": {"full": _mw_medians(mw_s), "excl_flagged": _mw_medians(mw_s_ex)},
            },
            "decay_shift_escalation_min": esc_min,
            "escalation_row8_shift_gt_threshold": bool(row8_triggered),
        },
        "source": "research/phase_7/t3_sensitivity.py:main",
    }
    with open(OUT_PATH, "w") as f:
        json.dump(out, f, indent=2, default=str)
    print(json.dumps(out, indent=2, default=str))

    triggered = []
    if row5_triggered: triggered.append("row5 (dev runtime > 60s)")
    if row6_triggered: triggered.append("row6 (dev flag inconsistency)")
    if row7_triggered: triggered.append("row7 (reproduction != 52/57)")
    if row8_triggered: triggered.append(f"row8 (crossing shift > {esc_min} min)")
    if triggered:
        print("\n*** ESCALATION: " + "; ".join(triggered) + " - HARD STOP ***")
    else:
        print("\nAll T3 escalation rows (5,6,7,8) clear.")


if __name__ == "__main__":
    main()
