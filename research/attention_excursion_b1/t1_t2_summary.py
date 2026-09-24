"""
Brief 1, T1 + T2 under Amendment 1 -- summaries, artifacts, and the escalation rows and II.5 checks
that live here.

Writes:
  artifacts/t1_prior_close.parquet        one row per D1 event, A1.2 rule, run-1 and minute-bar closes alongside
  artifacts/t2_tau.parquet                one row per D1 event, tau_ns int64, A12 flag, tau_close_sensitive
  artifacts/t2_row4_outside_band.parquet  every event outside [-1, 61] s on the revised row 4, per event
  artifacts/t1_t2_summary.json            everything the report reads for T1/T2, rows 1/4/7, II.5

Usage: .venv/Scripts/python.exe research/attention_excursion_b1/t1_t2_summary.py
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C  # noqa: E402

SOURCES = ["listing_cross", "listing_official", "last_rth_print", "unavailable"]


def q(s, ps=(0.01, 0.05, 0.25, 0.5, 0.75, 0.95, 0.99)) -> dict:
    s = pd.to_numeric(pd.Series(s), errors="coerce").dropna()
    if s.empty:
        return {"n": 0}
    out = {"n": int(s.size), "min": float(s.min()), "max": float(s.max()), "mean": float(s.mean())}
    out.update({f"p{int(round(p * 100)):02d}": float(s.quantile(p)) for p in ps})
    return out


def boolcol(s: pd.Series) -> pd.Series:
    return s.astype("boolean").fillna(False).astype(bool)


def main() -> int:
    cfg = C.load_cfg()
    d = pd.read_parquet(C.art("t1_t2_pass.parquet"))
    n = len(d)
    assert n == 15763, n
    d["year"] = d["event_date_canonical"].str[:4]
    d["prior_close_available"] = boolcol(d["prior_close_available"])
    d["tau_available"] = boolcol(d["tau_available"])
    lo_b, hi_b = cfg["t2_tau"]["proxy_band_s"]

    # ------------------------------------------------------------------ T1
    r1 = pd.read_parquet(C.art("run1/t1_prior_close.parquet"),
                         columns=["event_id", "prior_close_exact", "prior_close_source", "prior_close_exchange",
                                  "auction_code8_price", "chosen_differs_from_code8"]).rename(
        columns={"prior_close_exact": "run1_close", "prior_close_source": "run1_source",
                 "prior_close_exchange": "run1_exchange", "auction_code8_price": "run1_code8_price",
                 "chosen_differs_from_code8": "run1_other_venue_pick"})
    r1["run1_other_venue_pick"] = boolcol(r1["run1_other_venue_pick"])
    d = d.merge(r1, on="event_id", how="left")
    both_mb = d["prior_close_available"] & boolcol(d["prior_close_mb_available"])
    d["revised_vs_mb_bp"] = np.where(both_mb, (d["prior_close_exact"] - d["prior_close_mb"]) / d["prior_close_mb"] * 1e4, np.nan)
    both_r1 = d["prior_close_available"] & d["run1_close"].notna()
    d["revised_vs_run1_bp"] = np.where(both_r1, (d["prior_close_exact"] - d["run1_close"]) / d["run1_close"] * 1e4, np.nan)

    t1_cols = ["event_id", "ticker", "event_date_canonical", "primary_exchange", "listing_ex", "listing_unknown",
               "prior_session_date", "prior_close_available", "prior_close_source", "unavailable_reason",
               "prior_close_exact", "prior_close_ts", "prior_close_exchange", "prior_close_size", "prior_close_codes",
               "n_prior_session_prints", "n_cross_prints", "n_official_prints", "n_listing_cross", "n_listing_official",
               "n_code38", "cross_venues_seen", "listing_venue_mismatch", "prior_close_mb", "revised_vs_mb_bp",
               "run1_close", "run1_source", "run1_exchange", "run1_other_venue_pick", "revised_vs_run1_bp", "n_repair_rows"]
    t1 = d[[c for c in t1_cols if c in d.columns]].copy()
    t1["config_hash"] = C.cfg_hash()
    t1.to_parquet(C.art("t1_prior_close.parquet"), index=False)

    src = d["prior_close_source"].value_counts().reindex(SOURCES, fill_value=0)
    mism = boolcol(d["listing_venue_mismatch"])
    ov = d[d["run1_other_venue_pick"]]
    ov_res = ov["prior_close_source"].value_counts().to_dict()
    ov_eq_code8 = int((np.abs(ov["prior_close_exact"] - ov["run1_code8_price"]) < 1e-12).sum())
    t1_sum = {
        "rule": "A1.2 precedence listing_cross > listing_official > last_rth_print > unavailable",
        "source_counts": {k: int(v) for k, v in src.items()},
        "coverage": {"available": int(d["prior_close_available"].sum()), "of": n,
                     "share": float(d["prior_close_available"].mean())},
        "unavailable_reasons": d.loc[~d["prior_close_available"], "unavailable_reason"].value_counts(dropna=False).to_dict(),
        "listing_unknown": int(boolcol(d["listing_unknown"]).sum()),
        "listing_by_mic": d["primary_exchange"].value_counts(dropna=False).to_dict(),
        "source_by_mic": pd.crosstab(d["primary_exchange"], d["prior_close_source"]).to_dict("index"),
        "listing_venue_mismatch": {"n": int(mism.sum()),
                                   "cross_venues_seen": d.loc[mism, "cross_venues_seen"].value_counts().to_dict(),
                                   "by_mic": d.loc[mism, "primary_exchange"].value_counts().to_dict(),
                                   "resolved_as": d.loc[mism, "prior_close_source"].value_counts().to_dict()},
        "revised_minus_run1_bp": q(d["revised_vs_run1_bp"]),
        "revised_equals_run1": int((d["revised_vs_run1_bp"] == 0).sum()),
        "revised_minus_minute_bar_bp": q(d["revised_vs_mb_bp"]),
        "abs_revised_minus_minute_bar_bp": q(np.abs(d["revised_vs_mb_bp"])),
        "revised_equals_minute_bar": int((d["revised_vs_mb_bp"] == 0).sum()),
        "run1_other_venue_picks": {"n": int(len(ov)), "now_resolve_as": ov_res,
                                   "now_equal_run1_code8_price": ov_eq_code8,
                                   "revised_minus_run1_bp": q(ov["revised_vs_run1_bp"])},
        "code38_events": int((d["n_code38"].fillna(0) > 0).sum()),
        "errors": d["error"].dropna().value_counts().to_dict() if "error" in d else {},
    }

    # ------------------------------------------------------------------ T2
    for c in ["tau_ns", "tau_ns_noguard", "tau_ns_guard15", "tau_ns_mb", "tau_proxy_prime_ns", "tau_proxy_mb_tick_ns"]:
        d[c] = d[c].astype("Int64")
    a12 = pd.read_parquet(C.REPO / C.A12, columns=["ticker", "event_date_canonical", "session_pair", "flag_cross_session_extreme"])
    a12 = a12[a12["session_pair"] == "tm1_t0"].copy()
    a12["event_date_canonical"] = pd.to_datetime(a12["event_date_canonical"]).dt.strftime("%Y-%m-%d")
    assert not a12.duplicated(["ticker", "event_date_canonical"]).any()
    d = d.merge(a12[["ticker", "event_date_canonical", "flag_cross_session_extreme"]], on=["ticker", "event_date_canonical"], how="left")
    prox = pd.read_parquet(C.REPO / C.PROXY, columns=["event_id", "tau_ns", "tau_available"]).rename(
        columns={"tau_ns": "tau_proxy_v1_f64", "tau_available": "tau_proxy_v1_available"})
    d = d.merge(prox, on="event_id", how="left")

    f = lambda c: d[c].astype("float64")  # noqa: E731
    # A1.1 row 4: against tau_proxy_prime on the same close
    d["d_exact_minus_proxy_prime_s"] = (f("tau_ns") - f("tau_proxy_prime_ns")) / C.NS
    comp4 = d["tau_available"] & d["tau_proxy_prime_ns"].notna()
    d["row4_comparable"] = comp4
    d["row4_outside_band"] = comp4 & ~d["d_exact_minus_proxy_prime_s"].between(lo_b, hi_b)
    # II.5: tau >= tau_proxy_prime minute start
    t0400 = pd.Series([C.et_ns(x, "04:00:00") for x in d["event_date_canonical"]], index=d.index, dtype="float64")
    pm_start = t0400 + np.floor((f("tau_proxy_prime_ns") - t0400) / C.MIN_NS) * C.MIN_NS
    ii5_viol = comp4 & (f("tau_ns") < pm_start)
    # construction validation: the tick proxy on the minute-bar close vs v1's stored proxy
    vv = d["tau_proxy_mb_tick_ns"].notna() & d["tau_proxy_v1_f64"].notna()
    v_err = (f("tau_proxy_mb_tick_ns") - d["tau_proxy_v1_f64"]).abs()
    # as-run sensitivity: against v1's stored proxy
    d["d_exact_minus_proxy_v1_s"] = (f("tau_ns") - d["tau_proxy_v1_f64"]) / C.NS
    comp_s = d["tau_available"] & boolcol(d["tau_proxy_v1_available"])
    out_s = comp_s & ~d["d_exact_minus_proxy_v1_s"].between(lo_b, hi_b)
    # A1.3 tau_close_sensitive
    has_a, has_b = d["tau_ns"].notna(), d["tau_ns_mb"].notna()
    d["tau_gap_close_s"] = np.where(has_a & has_b, (f("tau_ns") - f("tau_ns_mb")) / C.NS, np.nan)
    thr = cfg["t2_tau"]["amendment_1"]["tau_close_sensitive"]["threshold_s"]
    tcs = pd.Series(pd.NA, index=d.index, dtype="boolean")
    tcs[has_a & has_b] = np.abs(d.loc[has_a & has_b, "tau_gap_close_s"]) > thr
    tcs[has_a ^ has_b] = True
    d["tau_close_sensitive"] = tcs
    # spike guard
    d["guard_moved_tau"] = d["tau_available"] & d["tau_ns_noguard"].notna() & (d["tau_ns"] != d["tau_ns_noguard"]).fillna(False)
    d["guard_move_s"] = np.where(d["guard_moved_tau"], (f("tau_ns") - f("tau_ns_noguard")) / C.NS, np.nan)
    d["guard15_differs"] = d["tau_available"] & (d["tau_ns"] != d["tau_ns_guard15"]).fillna(True)

    t2_cols = ["event_id", "ticker", "event_date_canonical", "year", "prior_close_exact", "prior_close_source",
               "prior_close_available", "listing_venue_mismatch", "tau_available", "tau_reason", "tau_ns", "tau_price",
               "tau_level", "tau_codes", "tau_session_segment", "sec_from_0400", "sec_from_0930", "shares_0400_to_tau",
               "n_prints_0400_to_tau", "n_eventday_prints_0400_2000", "tau_move_at", "flag_cross_session_extreme",
               "tau_close_sensitive", "tau_gap_close_s", "tau_ns_mb", "n_spikes_skipped", "tau_ns_noguard",
               "guard_moved_tau", "guard_move_s", "tau_ns_guard15", "guard15_differs", "tau_proxy_prime_ns",
               "d_exact_minus_proxy_prime_s", "row4_comparable", "row4_outside_band", "tau_proxy_v1_f64",
               "d_exact_minus_proxy_v1_s"]
    t2 = d[t2_cols].copy()
    t2["config_hash"] = C.cfg_hash()
    assert t2["tau_ns"].dtype == "Int64", "tau_ns must stay integer"
    t2.to_parquet(C.art("t2_tau.parquet"), index=False)
    ob = d[d["row4_outside_band"]].copy()
    ob["cause"] = np.where(ob["guard_moved_tau"], "spike_guard", "other")
    ob[["event_id", "ticker", "event_date_canonical", "tau_ns", "tau_proxy_prime_ns", "d_exact_minus_proxy_prime_s",
        "guard_moved_tau", "guard_move_s", "n_spikes_skipped", "cause"]].sort_values("d_exact_minus_proxy_prime_s").to_parquet(
        C.art("t2_row4_outside_band.parquet"), index=False)

    n_tau = int(d["tau_available"].sum())
    n4 = int(d["row4_outside_band"].sum())
    fb = int(src["last_rth_print"] + src["unavailable"])
    esc = {
        "row_1": {"criterion": cfg["escalation"]["row_1"]["criterion"], "tier": "HARD STOP",
                  "observed_share": n_tau / n, "n": n_tau, "of": n, "fires": bool(n_tau / n < 0.90)},
        "row_4": {"criterion": cfg["escalation"]["row_4"]["criterion"], "tier": "HARD STOP",
                  "n_outside": n4, "of_d1": n, "observed_share_of_d1": n4 / n, "n_comparable": int(comp4.sum()),
                  "outside_below": int((comp4 & (d["d_exact_minus_proxy_prime_s"] < lo_b)).sum()),
                  "outside_above": int((comp4 & (d["d_exact_minus_proxy_prime_s"] > hi_b)).sum()),
                  "cause": ob["cause"].value_counts().to_dict(), "fires": bool(n4 / n > 0.02)},
        "row_4_as_run_sensitivity": {"criterion": cfg["escalation"]["row_4_as_run_sensitivity"]["criterion"],
                                     "tier": "reported sensitivity, not a gate", "n_outside": int(out_s.sum()),
                                     "of_d1": n, "share_of_d1": float(out_s.sum() / n), "n_comparable": int(comp_s.sum())},
        "row_7": {"criterion": cfg["escalation"]["row_7"]["criterion"], "tier": "LOG",
                  "n": fb, "of": n, "observed_share": fb / n, "fires": bool(fb / n > 0.10)},
    }
    ii5 = {
        "tau_ns_int64": str(t2["tau_ns"].dtype) == "Int64",
        "tau_ge_proxy_prime_minute_start": {"violations": int(ii5_viol.sum()), "checked": int(comp4.sum()),
                                            "passes": bool(ii5_viol.sum() == 0)},
        "proxy_prime_construction_reproduces_v1": {"within_1us": int((vv & (v_err <= 1000)).sum()), "compared": int(vv.sum()),
                                                   "max_abs_err_ns": float(v_err[vv].max()) if vv.any() else None},
    }
    tcs_b = d["tau_close_sensitive"]
    t2_sum = {
        "tau_available": {"n": n_tau, "of": n, "share": n_tau / n},
        "tau_reasons": d["tau_reason"].value_counts(dropna=False).to_dict(),
        "tau_available_by_year": d.groupby("year")["tau_available"].agg(["sum", "size"]).to_dict("index"),
        "segment": d.loc[d["tau_available"], "tau_session_segment"].value_counts().to_dict(),
        "a12_flag": {"flagged": int(boolcol(d.loc[d["tau_available"], "flag_cross_session_extreme"]).sum()),
                     "flag_missing": int((d["tau_available"] & d["flag_cross_session_extreme"].isna()).sum())},
        "tau_close_sensitive": {"true": int((tcs_b == True).sum()), "false": int((tcs_b == False).sum()),  # noqa: E712
                                "null": int(tcs_b.isna().sum()),
                                "one_side_only": int((has_a ^ has_b).sum()),
                                "tau_gap_close_s": q(d["tau_gap_close_s"]),
                                "tau_equal_under_both_closes": int((d["tau_gap_close_s"] == 0).sum())},
        "spike_guard": {"events_tau_moved": int(d["guard_moved_tau"].sum()), "move_s": q(d["guard_move_s"]),
                        "events_with_any_spike_skipped": int((d["n_spikes_skipped"].fillna(0) > 0).sum()),
                        "tau_differs_under_guard15": int(d["guard15_differs"].sum())},
        "row4_d_exact_minus_proxy_prime_s": q(d.loc[comp4, "d_exact_minus_proxy_prime_s"]),
        "as_run_d_exact_minus_proxy_v1_s": q(d.loc[comp_s, "d_exact_minus_proxy_v1_s"]),
        "tau_codes_top": d.loc[d["tau_available"], "tau_codes"].value_counts().head(8).to_dict(),
        "sec_from_0400": q(d.loc[d["tau_available"], "sec_from_0400"]),
    }
    C.write_json(f"{C.ART}/t1_t2_summary.json", {"config_hash": C.cfg_hash(), "t1": t1_sum, "t2": t2_sum,
                                                  "escalation": esc, "verification_II5": ii5})
    print("T1 sources", t1_sum["source_counts"], "mismatch", t1_sum["listing_venue_mismatch"]["n"])
    print("T1 revised-mb |bp|", {k: round(v, 1) for k, v in t1_sum["abs_revised_minus_minute_bar_bp"].items()})
    print("run1 other-venue picks", t1_sum["run1_other_venue_picks"]["now_resolve_as"], t1_sum["run1_other_venue_picks"]["now_equal_run1_code8_price"])
    print("tau", t2_sum["tau_available"], t2_sum["tau_reasons"])
    print("tcs", t2_sum["tau_close_sensitive"]["true"], t2_sum["tau_close_sensitive"]["false"], t2_sum["tau_close_sensitive"]["null"])
    for k, v in esc.items():
        print(k, {kk: vv for kk, vv in v.items() if kk != "criterion"})
    print("II5", ii5)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
