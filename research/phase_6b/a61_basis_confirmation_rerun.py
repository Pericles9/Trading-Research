"""
Phase 6b Amendment 6, A6.1 - session-matched basis confirmation retest.
Corrects A5.1's session-scope mismatch: r1'/r2' now compare vendor
RTH-consolidated prices against RTH-scoped tick anchors on both sides,
rather than mixing an RTH-scoped vendor value against an extended-day
tick value. No new full-table passes - reads existing dev bars
(event_minute_bars_dev_v2, offsets -1 and 0, already materialized by T2).

tick_close_T-1_rth = last trade price of T-1 at or before the T-1 RTH
close (segment IN ('premarket','rth') - i.e. everything up to and
including the RTH close, the closing-auction-adjacent print - excludes
T-1 post). day_high_rth = max T+0 price within segment='rth' only.
"""
import json

import duckdb
import pandas as pd

DB_PATH = "data/duckdb/main.duckdb"
PRIMARY_MANIFEST = "results/phase_5a/artifacts/dev_v4_primary_events.parquet"
SIDECAR_MANIFEST = "results/phase_5a/artifacts/dev_v4_sidecar_events.parquet"
DEV_BARS_TABLE = "event_minute_bars_dev_v2"
OUT_JSON = "results/phase_6b/artifacts/a61_basis_confirmation_rerun.json"

EVENT_KEYS = ["ticker", "event_date_canonical", "momentum_pct"]


def load_dev_manifest():
    primary = pd.read_parquet(PRIMARY_MANIFEST)
    sidecar = pd.read_parquet(SIDECAR_MANIFEST)
    cols = ["ticker", "event_date_canonical", "momentum_pct", "dev_cohort"]
    m = pd.concat([primary[cols], sidecar[cols]], ignore_index=True)
    m["event_date_canonical"] = pd.to_datetime(m["event_date_canonical"])
    return m


def main():
    manifest = load_dev_manifest()
    n_total = len(manifest)

    con = duckdb.connect(DB_PATH, read_only=True)
    spine_prices = con.execute("""
        SELECT ticker, COALESCE(date, event_date) AS event_date_canonical, ROUND(momentum_pct, 2) AS mom_2dp,
               prev_close, high, event_high
        FROM momentum_events
    """).fetchdf()
    spine_prices["event_date_canonical"] = pd.to_datetime(spine_prices["event_date_canonical"])

    t_minus_1_rth_last = con.execute(f"""
        SELECT ticker, event_date_canonical, momentum_pct, segment, minute_index, last_price
        FROM {DEV_BARS_TABLE}
        WHERE session_offset = -1 AND segment IN ('premarket', 'rth')
        QUALIFY minute_index = MAX(minute_index) OVER (PARTITION BY ticker, event_date_canonical, momentum_pct)
    """).fetchdf()
    t_minus_1_rth_last = t_minus_1_rth_last.rename(columns={"last_price": "tick_close_t_minus_1_rth", "segment": "t_minus_1_rth_last_segment"})
    t_minus_1_rth_last["event_date_canonical"] = pd.to_datetime(t_minus_1_rth_last["event_date_canonical"])

    day_high_rth = con.execute(f"""
        SELECT ticker, event_date_canonical, momentum_pct, MAX(high) AS day_high_rth
        FROM {DEV_BARS_TABLE}
        WHERE session_offset = 0 AND segment = 'rth'
        GROUP BY 1, 2, 3
    """).fetchdf()
    day_high_rth["event_date_canonical"] = pd.to_datetime(day_high_rth["event_date_canonical"])

    # full T-1 and T+0 bar series for the residual-outlier dump
    bars_t_minus_1_full = con.execute(f"""
        SELECT ticker, event_date_canonical, momentum_pct, segment, minute_index, n_trades, volume, vwap, high, low, first_price, last_price
        FROM {DEV_BARS_TABLE} WHERE session_offset = -1 ORDER BY ticker, event_date_canonical, momentum_pct, minute_index
    """).fetchdf()
    bars_t0_full = con.execute(f"""
        SELECT ticker, event_date_canonical, momentum_pct, segment, minute_index, n_trades, volume, vwap, high, low, first_price, last_price
        FROM {DEV_BARS_TABLE} WHERE session_offset = 0 ORDER BY ticker, event_date_canonical, momentum_pct, minute_index
    """).fetchdf()
    con.close()
    bars_t_minus_1_full["event_date_canonical"] = pd.to_datetime(bars_t_minus_1_full["event_date_canonical"])
    bars_t0_full["event_date_canonical"] = pd.to_datetime(bars_t0_full["event_date_canonical"])

    ev = manifest.copy()
    ev["mom_2dp"] = ev["momentum_pct"].round(2)
    merged = ev.merge(spine_prices, on=["ticker", "event_date_canonical", "mom_2dp"], how="left")
    merged = merged.merge(t_minus_1_rth_last, on=EVENT_KEYS, how="left")
    merged = merged.merge(day_high_rth, on=EVENT_KEYS, how="left")

    merged["spine_high_coalesced"] = merged["high"].combine_first(merged["event_high"])
    merged["r1p"] = merged["prev_close"] / merged["tick_close_t_minus_1_rth"]
    merged["r2p"] = merged["spine_high_coalesced"] / merged["day_high_rth"]
    merged["has_t_minus_1_rth"] = merged["tick_close_t_minus_1_rth"].notna()
    merged["denom_nonpositive_t0_rth"] = merged["day_high_rth"] <= merged["prev_close"]

    both_defined = merged[merged["r1p"].notna() & merged["r2p"].notna()].copy()
    both_defined["rel_diff"] = (both_defined["r1p"] - both_defined["r2p"]).abs() / both_defined["r2p"]
    n_both = len(both_defined)
    n_agree = int((both_defined["rel_diff"] < 0.02).sum())
    pct_agree = 100.0 * n_agree / n_both if n_both else float("nan")
    criterion_1_pass = pct_agree >= 90.0

    dup_tickers = manifest["ticker"].value_counts()
    dup_tickers = dup_tickers[dup_tickers > 1].index.tolist()
    per_ticker_stability = []
    criterion_2_pass = True
    for t in dup_tickers:
        sub = merged[merged["ticker"] == t][["ticker", "event_date_canonical", "r1p", "r2p"]]
        r_vals = pd.concat([sub["r1p"], sub["r2p"]]).dropna()
        stable = bool(r_vals.max() / r_vals.min() < 1.10) if len(r_vals) >= 2 else None
        if stable is False:
            criterion_2_pass = False
        per_ticker_stability.append({"ticker": t, "rows": sub.to_dict(orient="records"), "stable_within_10pct": stable})
    if not dup_tickers:
        criterion_2_pass = None

    flagged = merged[merged["denom_nonpositive_t0_rth"]]
    unflagged = merged[~merged["denom_nonpositive_t0_rth"]]
    flagged_factor = pd.concat([flagged["r1p"], flagged["r2p"]]).dropna()
    unflagged_factor = pd.concat([unflagged["r1p"], unflagged["r2p"]]).dropna()
    n_flagged_materially_gt1 = int((flagged_factor > 1.05).sum())
    pct_flagged_materially_gt1 = 100.0 * n_flagged_materially_gt1 / len(flagged_factor) if len(flagged_factor) else float("nan")
    # "cluster near 1 or a small-integer reciprocal" - check near 1 OR near 1/2,1/3,1/4,1/5,1/10,1/15,1/20
    import numpy as np
    reciprocals = [1.0] + [1.0 / k for k in (2, 3, 4, 5, 6, 8, 10, 12, 15, 20, 25, 30, 50)]
    def _near_any(x, targets, tol=0.05):
        return any(abs(x - t) < tol * t for t in targets) if pd.notna(x) else False
    unflagged_near_cluster = unflagged_factor.apply(lambda x: _near_any(x, reciprocals)).mean() if len(unflagged_factor) else float("nan")
    criterion_3_pass = pct_flagged_materially_gt1 >= 90.0

    all_pass = bool(criterion_1_pass) and (criterion_2_pass is not False) and bool(criterion_3_pass)

    # residual outliers: events failing the 2% band after session matching
    residual = both_defined[both_defined["rel_diff"] >= 0.02][EVENT_KEYS].drop_duplicates()
    residual_dump = []
    for row in residual.itertuples(index=False):
        key = {"ticker": row.ticker, "event_date_canonical": str(row.event_date_canonical), "momentum_pct": row.momentum_pct}
        t1_series = bars_t_minus_1_full[(bars_t_minus_1_full["ticker"] == row.ticker) &
                                         (bars_t_minus_1_full["event_date_canonical"] == row.event_date_canonical) &
                                         (abs(bars_t_minus_1_full["momentum_pct"] - row.momentum_pct) < 1e-6)]
        t0_series = bars_t0_full[(bars_t0_full["ticker"] == row.ticker) &
                                  (bars_t0_full["event_date_canonical"] == row.event_date_canonical) &
                                  (abs(bars_t0_full["momentum_pct"] - row.momentum_pct) < 1e-6)]
        residual_dump.append({**key, "t_minus_1_bars": t1_series.drop(columns=EVENT_KEYS).to_dict(orient="records"),
                               "t0_bars": t0_series.drop(columns=EVENT_KEYS).to_dict(orient="records")})

    out_cols = EVENT_KEYS + ["dev_cohort", "prev_close", "spine_high_coalesced", "tick_close_t_minus_1_rth",
                             "t_minus_1_rth_last_segment", "day_high_rth", "r1p", "r2p", "has_t_minus_1_rth", "denom_nonpositive_t0_rth"]
    full_table = merged[out_cols].copy()
    full_table["event_date_canonical"] = full_table["event_date_canonical"].astype(str)

    summary = {
        "phase": "6b", "task": "A6.1", "n_total_dev_events": n_total,
        "criterion_1_ratio_agreement": {
            "n_events_both_defined": n_both, "n_agree_within_2pct": n_agree,
            "pct_agree": round(pct_agree, 2) if n_both else None, "threshold_pct": 90.0, "pass": criterion_1_pass,
        },
        "criterion_2_per_ticker_stability": {
            "duplicate_tickers": dup_tickers, "detail": per_ticker_stability, "pass": criterion_2_pass,
        },
        "criterion_3_flagged_vs_unflagged_factors": {
            "n_flagged_events": len(flagged), "pct_flagged_materially_gt1": round(pct_flagged_materially_gt1, 2) if len(flagged_factor) else None,
            "unflagged_share_near_1_or_small_integer_reciprocal": round(float(unflagged_near_cluster), 4) if len(unflagged_factor) else None,
            "pass": criterion_3_pass,
        },
        "all_criteria_pass": all_pass,
        "n_no_t_minus_1_rth_bars": int((~merged["has_t_minus_1_rth"]).sum()),
        "n_residual_outliers": len(residual),
        "residual_outlier_events": residual.astype(str).to_dict(orient="records"),
        "residual_outlier_bar_dump": residual_dump,
        "full_table": full_table.to_dict(orient="records"),
        "source": "research/phase_6b/a61_basis_confirmation_rerun.py:main",
    }
    with open(OUT_JSON, "w") as f:
        json.dump(summary, f, indent=2, default=str)

    print(f"n_total={n_total}")
    print(f"criterion 1: {n_agree}/{n_both} = {pct_agree:.1f}% (need >=90%) -> {'PASS' if criterion_1_pass else 'FAIL'}")
    print(f"criterion 2 ({len(dup_tickers)} dup tickers): {criterion_2_pass}")
    for d in per_ticker_stability:
        print(f"   {d['ticker']}: stable={d['stable_within_10pct']} rows={d['rows']}")
    print(f"criterion 3: flagged {pct_flagged_materially_gt1:.1f}% >1.05, unflagged near-cluster {unflagged_near_cluster:.1%} -> {'PASS' if criterion_3_pass else 'FAIL'}")
    print(f"ALL CRITERIA PASS: {all_pass}")
    print(f"residual outliers (>=2% after session matching): {len(residual)} -> {residual['ticker'].tolist()}")
    print(f"events with no T-1 RTH bars: {int((~merged['has_t_minus_1_rth']).sum())}")

    if not all_pass:
        print("\n*** A6.1 criteria FAILED - HARD STOP, no fix authorized - dedicated diagnosis phase needed ***")
    else:
        print("\n*** A6.1 CONFIRMED - proceeding to A6.2/A6.3 ***")


if __name__ == "__main__":
    main()
