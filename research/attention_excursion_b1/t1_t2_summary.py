"""
Brief 1, T1 + T2 -- summaries, artifacts and the two escalation checks that live here.

Reads the one-pass output of t1_t2_prior_close_tau.py and writes:
  artifacts/t1_prior_close.parquet   one row per D1 event
  artifacts/t2_tau.parquet           one row per D1 event, tau_ns int64, A12 flag carried
  artifacts/t2_proxy_outside_band.parquet   every event with tau_exact - tau_proxy outside [-1, 61] s,
                                     listed per event, not averaged (brief T2)
  artifacts/t1_t2_summary.json       coverage, census, the decomposition, escalation rows 1 and 4

Usage: .venv/Scripts/python.exe research/attention_excursion_b1/t1_t2_summary.py
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C  # noqa: E402


def q(s: pd.Series, ps=(0.01, 0.05, 0.25, 0.5, 0.75, 0.95, 0.99)) -> dict:
    s = pd.to_numeric(s, errors="coerce").dropna()
    if s.empty:
        return {"n": 0}
    out = {"n": int(s.size), "min": float(s.min()), "max": float(s.max()), "mean": float(s.mean())}
    out.update({f"p{int(round(p * 100)):02d}": float(s.quantile(p)) for p in ps})
    return out


def main() -> int:
    cfg = C.load_cfg()
    d = pd.read_parquet(C.art("t1_t2_pass.parquet"))
    n = len(d)
    assert n == 15763, n
    d["year"] = d["event_date_canonical"].str[:4]

    # ------------------------------------------------------------------ T1
    d["prior_close_available"] = d["prior_close_available"].fillna(False).astype(bool)
    both = d["prior_close_available"] & d["prior_close_mb_available"].fillna(False).astype(bool)
    d["abs_exact_vs_mb_bp"] = np.where(both, (d["prior_close_exact"] - d["prior_close_mb"]).abs() / d["prior_close_mb"] * 1e4, np.nan)
    d["exact_vs_mb_bp"] = np.where(both, (d["prior_close_exact"] - d["prior_close_mb"]) / d["prior_close_mb"] * 1e4, np.nan)
    auc = d["prior_close_source"] == "auction_8_15"
    t1_cols = ["event_id", "ticker", "event_date_canonical", "prior_session_date", "prior_close_available",
               "prior_close_source", "prior_close_exact", "prior_close_ts", "prior_close_exchange",
               "prior_close_size", "prior_close_codes", "n_prior_session_prints", "n_auction_8", "n_auction_15",
               "n_auction_8_15", "auction_n_distinct_prices", "auction_price_spread_bp", "auction_after_close_s",
               "auction_code8_price", "chosen_differs_from_code8", "last_rth_print_price", "prior_close_mb",
               "prior_close_mb_available", "exact_vs_mb_bp", "abs_exact_vs_mb_bp", "n_repair_rows"]
    t1 = d[[c for c in t1_cols if c in d.columns]].copy()
    t1["config_hash"] = C.cfg_hash()
    t1.to_parquet(C.art("t1_prior_close.parquet"), index=False)

    t1_sum = {
        "coverage": {"available": int(d["prior_close_available"].sum()), "of": n,
                     "share": float(d["prior_close_available"].mean())},
        "source_counts": d["prior_close_source"].value_counts(dropna=False).to_dict(),
        "fallback_applies_auction_absent": int((d["prior_close_source"] == "fallback_last_rth_print").sum()),
        "unavailable_by_year": d[~d["prior_close_available"]].groupby("year").size().to_dict(),
        "coverage_by_year": d.groupby("year")["prior_close_available"].agg(["sum", "size"]).to_dict("index"),
        "abs_exact_minus_minute_bar_bp": q(d["abs_exact_vs_mb_bp"]),
        "signed_exact_minus_minute_bar_bp": q(d["exact_vs_mb_bp"]),
        "exact_equals_minute_bar": int((d["abs_exact_vs_mb_bp"] == 0).sum()),
        "abs_diff_over_100bp": int((d["abs_exact_vs_mb_bp"] > 100).sum()),
        "abs_diff_over_500bp": int((d["abs_exact_vs_mb_bp"] > 500).sum()),
        "exact_available_mb_not": int((d["prior_close_available"] & ~d["prior_close_mb_available"].fillna(False).astype(bool)).sum()),
        "mb_available_exact_not": int((~d["prior_close_available"] & d["prior_close_mb_available"].fillna(False).astype(bool)).sum()),
        "auction_census": {
            "n_events_auction": int(auc.sum()),
            "distinct_auction_prices": d.loc[auc, "auction_n_distinct_prices"].value_counts().sort_index().to_dict(),
            "chosen_differs_from_largest_code8": int(d.loc[auc, "chosen_differs_from_code8"].fillna(False).astype(bool).sum()),
            "no_code8_print": int((auc & (d["n_auction_8"] == 0)).sum()),
            "chosen_exchange": d.loc[auc, "prior_close_exchange"].value_counts().head(8).to_dict(),
            "auction_after_close_s": q(d.loc[auc, "auction_after_close_s"]),
            "auction_vs_last_rth_print_abs_bp": q(((d.loc[auc, "prior_close_exact"] - d.loc[auc, "last_rth_print_price"]).abs()
                                                    / d.loc[auc, "last_rth_print_price"] * 1e4)),
        },
        "errors": d["error"].dropna().value_counts().to_dict() if "error" in d else {},
    }

    # ------------------------------------------------------------------ T2
    d["tau_available"] = d["tau_available"].fillna(False).astype(bool)
    for c in ["tau_ns", "tau_ns_noguard", "tau_ns_guard15", "tau_ns_mb"]:
        d[c] = d[c].astype("Int64")
    a12 = pd.read_parquet(C.REPO / C.A12, columns=["ticker", "event_date_canonical", "session_pair", "flag_cross_session_extreme"])
    a12 = a12[a12["session_pair"] == "tm1_t0"].copy()
    a12["event_date_canonical"] = pd.to_datetime(a12["event_date_canonical"]).dt.strftime("%Y-%m-%d")
    assert not a12.duplicated(["ticker", "event_date_canonical"]).any()
    d = d.merge(a12[["ticker", "event_date_canonical", "flag_cross_session_extreme"]],
                on=["ticker", "event_date_canonical"], how="left")
    d["a12_flag_available"] = d["flag_cross_session_extreme"].notna()

    prox = pd.read_parquet(C.REPO / C.PROXY, columns=["event_id", "tau_ns", "tau_available"]).rename(
        columns={"tau_ns": "tau_proxy_ns_f64", "tau_available": "tau_proxy_available"})
    d = d.merge(prox, on="event_id", how="left")
    # proxy was stored float64 (v1 defect, 256 ns grid at 1.7e18) -- harmless at 1 s resolution
    d["d_exact_minus_proxy_s"] = (d["tau_ns"].astype("float64") - d["tau_proxy_ns_f64"]) / C.NS
    d["d_mb_minus_proxy_s"] = (d["tau_ns_mb"].astype("float64") - d["tau_proxy_ns_f64"]) / C.NS
    d["d_exact_minus_mb_s"] = (d["tau_ns"].astype("float64") - d["tau_ns_mb"].astype("float64")) / C.NS
    lo_b, hi_b = cfg["t2_tau"]["proxy_band_s"]
    comparable = d["tau_available"] & d["tau_proxy_available"].fillna(False).astype(bool)
    d["proxy_comparable"] = comparable
    d["outside_proxy_band"] = comparable & ~d["d_exact_minus_proxy_s"].between(lo_b, hi_b)
    d["guard_moved_tau"] = d["tau_available"] & d["tau_ns_noguard"].notna() & (d["tau_ns"] != d["tau_ns_noguard"])
    d["guard_move_s"] = np.where(d["guard_moved_tau"], (d["tau_ns"].astype("float64") - d["tau_ns_noguard"].astype("float64")) / C.NS, np.nan)
    d["guard15_differs"] = d["tau_available"] & (d["tau_ns"] != d["tau_ns_guard15"]).fillna(True)

    t2_cols = ["event_id", "ticker", "event_date_canonical", "year", "prior_close_exact", "prior_close_source",
               "prior_close_available", "tau_available", "tau_reason", "tau_ns", "tau_price", "tau_level",
               "tau_codes", "tau_session_segment", "sec_from_0400", "sec_from_0930", "shares_0400_to_tau",
               "n_prints_0400_to_tau", "n_eventday_prints_0400_2000", "tau_move_at", "flag_cross_session_extreme",
               "a12_flag_available", "n_spikes_skipped", "tau_ns_noguard", "guard_moved_tau", "guard_move_s",
               "tau_ns_guard15", "guard15_differs", "tau_ns_mb", "tau_proxy_ns_f64", "tau_proxy_available",
               "proxy_comparable", "d_exact_minus_proxy_s", "d_mb_minus_proxy_s", "d_exact_minus_mb_s",
               "outside_proxy_band"]
    t2 = d[t2_cols].copy()
    t2["config_hash"] = C.cfg_hash()
    assert t2["tau_ns"].dtype == "Int64"
    t2.to_parquet(C.art("t2_tau.parquet"), index=False)

    ob = d[d["outside_proxy_band"]].copy()
    ob["cause"] = np.select(
        [ob["d_mb_minus_proxy_s"].between(lo_b, hi_b) & (ob["abs_exact_vs_mb_bp"] > 0),
         ob["guard_moved_tau"]],
        ["prior_close_change (tau under the minute-bar close is inside the band)", "spike_guard"],
        default="other")
    ob[["event_id", "ticker", "event_date_canonical", "tau_ns", "tau_proxy_ns_f64", "d_exact_minus_proxy_s",
        "d_mb_minus_proxy_s", "d_exact_minus_mb_s", "prior_close_exact", "prior_close_mb", "exact_vs_mb_bp",
        "prior_close_source", "guard_moved_tau", "cause"]].sort_values("d_exact_minus_proxy_s").to_parquet(
        C.art("t2_proxy_outside_band.parquet"), index=False)

    n_tau = int(d["tau_available"].sum())
    n_comp = int(comparable.sum())
    n_out = int(d["outside_proxy_band"].sum())
    row1 = {"criterion": "tau_available below 90% of D1", "observed": n_tau / n, "n": n_tau, "of": n,
            "fires": bool(n_tau / n < 0.90), "tier": "HARD STOP"}
    row4 = {"criterion": "tau_exact - tau_proxy outside [-1, 61] s for more than 2% of D1",
            "observed_share_of_d1": n_out / n, "n_outside": n_out, "of_d1": n, "n_comparable": n_comp,
            "share_of_comparable": n_out / n_comp if n_comp else None,
            "fires": bool(n_out / n > 0.02), "tier": "HARD STOP"}
    t2_sum = {
        "tau_available": {"n": n_tau, "of": n, "share": n_tau / n},
        "tau_reasons": d["tau_reason"].value_counts(dropna=False).to_dict(),
        "tau_available_by_year": d.groupby("year")["tau_available"].agg(["sum", "size"]).to_dict("index"),
        "segment": d.loc[d["tau_available"], "tau_session_segment"].value_counts().to_dict(),
        "a12_flag": {"flagged": int(d.loc[d["tau_available"], "flag_cross_session_extreme"].fillna(False).astype(bool).sum()),
                     "flag_missing": int((d["tau_available"] & ~d["a12_flag_available"]).sum())},
        "spike_guard": {"events_tau_moved": int(d["guard_moved_tau"].sum()),
                        "move_s": q(d["guard_move_s"]),
                        "events_with_any_spike_skipped": int((d["n_spikes_skipped"].fillna(0) > 0).sum()),
                        "noguard_crosses_guard_never": int((~d["tau_available"] & d["tau_ns_noguard"].notna() & d["prior_close_available"]).sum()),
                        "tau_differs_under_overlay_1p5pct_agreement": int(d["guard15_differs"].sum())},
        "proxy_comparison": {
            "comparable": n_comp,
            "exact_available_proxy_not": int((d["tau_available"] & ~d["tau_proxy_available"].fillna(False).astype(bool)).sum()),
            "proxy_available_exact_not": int((~d["tau_available"] & d["tau_proxy_available"].fillna(False).astype(bool)).sum()),
            "d_exact_minus_proxy_s": q(d.loc[comparable, "d_exact_minus_proxy_s"]),
            "inside_band": int((comparable & d["d_exact_minus_proxy_s"].between(lo_b, hi_b)).sum()),
            "outside_band": n_out,
            "outside_below": int((comparable & (d["d_exact_minus_proxy_s"] < lo_b)).sum()),
            "outside_above": int((comparable & (d["d_exact_minus_proxy_s"] > hi_b)).sum()),
            "outside_band_cause": ob["cause"].value_counts().to_dict(),
            "decomposition": {
                "tau_mb_minus_proxy_s (print vs minute stamp, same prior close)": q(d.loc[comparable, "d_mb_minus_proxy_s"]),
                "tau_mb_minus_proxy_inside_band": int((comparable & d["d_mb_minus_proxy_s"].between(lo_b, hi_b)).sum()),
                "tau_mb_available_of_comparable": int((comparable & d["tau_ns_mb"].notna()).sum()),
                "tau_exact_minus_tau_mb_s (prior close change only)": q(d.loc[comparable, "d_exact_minus_mb_s"]),
                "tau_exact_equals_tau_mb": int((comparable & (d["d_exact_minus_mb_s"] == 0)).sum()),
            },
        },
        "tau_codes_top": d.loc[d["tau_available"], "tau_codes"].value_counts().head(12).to_dict(),
        "sec_from_0400": q(d.loc[d["tau_available"], "sec_from_0400"]),
    }
    summary = {"config_hash": C.cfg_hash(), "t1": t1_sum, "t2": t2_sum,
               "escalation": {"row_1": row1, "row_4": row4}}
    C.write_json(f"{C.ART}/t1_t2_summary.json", summary)
    print("T1 coverage", t1_sum["coverage"], "\nsources", t1_sum["source_counts"])
    print("T1 |exact-mb| bp", t1_sum["abs_exact_minus_minute_bar_bp"])
    print("T2 tau", t2_sum["tau_available"], t2_sum["tau_reasons"])
    print("spike guard", t2_sum["spike_guard"])
    print("proxy", {k: v for k, v in t2_sum["proxy_comparison"].items() if k != "decomposition"})
    print("decomp", t2_sum["proxy_comparison"]["decomposition"])
    print("ROW 1", row1)
    print("ROW 4", row4)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
