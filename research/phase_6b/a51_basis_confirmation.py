"""
Phase 6b Amendment 5, A5.1 - confirm the spine-OHLC adjustment-basis
mismatch mechanism at dev tier, before any fix code runs. No new
full-table passes - everything here reads existing dev bars
(event_minute_bars_dev_v2, all offsets already materialized by T2) and
momentum_events (small, not a full-table-pass concern).

r1 = spine.prev_close / tick_close_T-1 (last trade price of the T-1
extended day, from event_minute_bars_dev_v2 offset=-1; NULL if the
event has no T-1 bars).
r2 = COALESCE(spine.high, spine.event_high) / day_high_ext (T=0, already
computed at T2 - results/phase_6b/artifacts/opportunity_decay_primary_dev.parquet).
"""
import json

import duckdb
import numpy as np
import pandas as pd

DB_PATH = "data/duckdb/main.duckdb"
PRIMARY_MANIFEST = "results/phase_5a/artifacts/dev_v4_primary_events.parquet"
SIDECAR_MANIFEST = "results/phase_5a/artifacts/dev_v4_sidecar_events.parquet"
DAY_HIGH_EXT_ARTIFACT = "results/phase_6b/artifacts/opportunity_decay_primary_dev.parquet"
DEV_BARS_TABLE = "event_minute_bars_dev_v2"
OUT_JSON = "results/phase_6b/artifacts/a51_basis_confirmation.json"

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

    t_minus_1_last = con.execute(f"""
        SELECT ticker, event_date_canonical, momentum_pct, segment, minute_index, last_price
        FROM {DEV_BARS_TABLE}
        WHERE session_offset = -1
        QUALIFY minute_index = MAX(minute_index) OVER (PARTITION BY ticker, event_date_canonical, momentum_pct)
    """).fetchdf()
    con.close()
    t_minus_1_last = t_minus_1_last.rename(columns={"last_price": "tick_close_t_minus_1", "segment": "t_minus_1_segment"})
    t_minus_1_last["event_date_canonical"] = pd.to_datetime(t_minus_1_last["event_date_canonical"])

    day_high_ext = pd.read_parquet(DAY_HIGH_EXT_ARTIFACT)[EVENT_KEYS + ["day_high_ext"]]
    day_high_ext["event_date_canonical"] = pd.to_datetime(day_high_ext["event_date_canonical"])

    ev = manifest.copy()
    ev["mom_2dp"] = ev["momentum_pct"].round(2)
    merged = ev.merge(spine_prices, on=["ticker", "event_date_canonical", "mom_2dp"], how="left")
    merged = merged.merge(t_minus_1_last, on=EVENT_KEYS, how="left")
    merged = merged.merge(day_high_ext, on=EVENT_KEYS, how="left")

    merged["spine_high_coalesced"] = merged["high"].combine_first(merged["event_high"])
    merged["r1"] = merged["prev_close"] / merged["tick_close_t_minus_1"]
    merged["r2"] = merged["spine_high_coalesced"] / merged["day_high_ext"]
    merged["has_t_minus_1"] = merged["tick_close_t_minus_1"].notna()
    merged["denom_nonpositive_t0"] = merged["day_high_ext"] <= merged["prev_close"]

    both_defined = merged[merged["r1"].notna() & merged["r2"].notna()].copy()
    both_defined["rel_diff"] = (both_defined["r1"] - both_defined["r2"]).abs() / both_defined["r2"]
    n_both = len(both_defined)
    n_agree = int((both_defined["rel_diff"] < 0.02).sum())
    pct_agree = 100.0 * n_agree / n_both if n_both else float("nan")
    criterion_1_pass = pct_agree >= 90.0

    dup_tickers = manifest["ticker"].value_counts()
    dup_tickers = dup_tickers[dup_tickers > 1].index.tolist()
    per_ticker_stability = []
    criterion_2_pass = True
    for t in dup_tickers:
        sub = merged[merged["ticker"] == t][["ticker", "event_date_canonical", "r1", "r2"]]
        r_vals = pd.concat([sub["r1"], sub["r2"]]).dropna()
        stable = bool(r_vals.max() / r_vals.min() < 1.10) if len(r_vals) >= 2 else None
        if stable is False:
            criterion_2_pass = False
        per_ticker_stability.append({"ticker": t, "rows": sub.to_dict(orient="records"), "stable_within_10pct": stable})
    if not dup_tickers:
        criterion_2_pass = None  # not testable at dev tier

    flagged = merged[merged["denom_nonpositive_t0"]]
    unflagged = merged[~merged["denom_nonpositive_t0"]]
    flagged_factor = pd.concat([flagged["r1"], flagged["r2"]]).dropna()
    unflagged_factor = pd.concat([unflagged["r1"], unflagged["r2"]]).dropna()
    n_flagged_materially_gt1 = int((flagged_factor > 1.05).sum())
    pct_flagged_materially_gt1 = 100.0 * n_flagged_materially_gt1 / len(flagged_factor) if len(flagged_factor) else float("nan")
    unflagged_near_1 = float((unflagged_factor.sub(1).abs() < 0.05).mean()) if len(unflagged_factor) else float("nan")
    criterion_3_pass = pct_flagged_materially_gt1 >= 90.0

    all_pass = bool(criterion_1_pass) and (criterion_2_pass is not False) and bool(criterion_3_pass)

    out_cols = EVENT_KEYS + ["dev_cohort", "prev_close", "spine_high_coalesced", "tick_close_t_minus_1", "t_minus_1_segment",
                             "day_high_ext", "r1", "r2", "has_t_minus_1", "denom_nonpositive_t0"]
    full_table = merged[out_cols].copy()
    full_table["event_date_canonical"] = full_table["event_date_canonical"].astype(str)

    summary = {
        "phase": "6b", "task": "A5.1", "n_total_dev_events": n_total,
        "criterion_1_ratio_agreement": {
            "n_events_both_r1_r2_defined": n_both, "n_agree_within_2pct": n_agree,
            "pct_agree": round(pct_agree, 2) if n_both else None, "threshold_pct": 90.0, "pass": criterion_1_pass,
        },
        "criterion_2_per_ticker_stability": {
            "duplicate_tickers_in_dev_sample": dup_tickers, "detail": per_ticker_stability,
            "pass": criterion_2_pass, "note": "None = not testable at dev tier (no repeated tickers)" if not dup_tickers else None,
        },
        "criterion_3_flagged_vs_unflagged_factors": {
            "n_flagged_events": len(flagged), "n_flagged_factor_observations": len(flagged_factor),
            "n_flagged_materially_gt1_05": n_flagged_materially_gt1, "pct_flagged_materially_gt1": round(pct_flagged_materially_gt1, 2) if len(flagged_factor) else None,
            "unflagged_share_within_5pct_of_1": round(unflagged_near_1, 4) if len(unflagged_factor) else None,
            "pass": criterion_3_pass,
        },
        "all_criteria_pass": all_pass,
        "escalation_row_5a_triggered": not all_pass,
        "n_no_t_minus_1_bars": int((~merged["has_t_minus_1"]).sum()),
        "no_t_minus_1_events": merged[~merged["has_t_minus_1"]][EVENT_KEYS].astype(str).to_dict(orient="records"),
        "full_table": full_table.to_dict(orient="records"),
        "source": "research/phase_6b/a51_basis_confirmation.py:main",
    }
    with open(OUT_JSON, "w") as f:
        json.dump(summary, f, indent=2, default=str)

    print(f"n_total={n_total}")
    print(f"criterion 1 (ratio agreement): {n_agree}/{n_both} = {pct_agree:.1f}% (need >=90%) -> {'PASS' if criterion_1_pass else 'FAIL'}")
    print(f"criterion 2 (per-ticker stability, {len(dup_tickers)} dup tickers): {criterion_2_pass}")
    print(f"criterion 3 (flagged>1, unflagged~1): flagged {pct_flagged_materially_gt1:.1f}% >1.05, unflagged {unflagged_near_1:.1%} within 5% of 1 -> {'PASS' if criterion_3_pass else 'FAIL'}")
    print(f"ALL CRITERIA PASS: {all_pass}")
    print(f"events with no T-1 bars: {int((~merged['has_t_minus_1']).sum())}")

    if not all_pass:
        print("\n*** ESCALATION row 5a: A5.1 confirmation criteria FAILED - HARD STOP, no fix authorized ***")


if __name__ == "__main__":
    main()
