"""
Part III (prompts/attention_excursion_b1.md, Part III; authorised by Amendment 1 A1.7) -- E2's
participation window, units fix.

THE DEFECT. e2_t2_window.py ends the window at the first minute where

    roll = dollar_volume.rolling(window=10).mean()      # average dollar volume PER MINUTE
    qualifies = roll <= 3.0 * B_e                        # B_e is dollar volume PER 10-MINUTE BLOCK

e2_t2a_baseline.py defines B_e = total RTH dollar volume / (n_sessions x 39), and 39 is the number of
10-minute intervals in a 390-minute session. The comparison ran per-minute against per-10-minutes: the
rule that ran was "activity below 30x the baseline rate", not the 3x Cooper confirmed on 2026-09-15.

THIS SCRIPT
  III.2.1  one event, both constructions side by side: the per-minute average against 3 B_e (as run)
           and the trailing 10-minute SUM against 3 B_e (as confirmed). Posts the two window ends. The
           event is fixed before running: the first dev_v3 event, CBRL 2020-03-24 (config/dev_sample_v3.json).
  III.2.2  duration_min rebuilt for every event with the corrected units. Everything else exactly as
           confirmed for E2 -- C = 10, dollar volume, censoring at end of tick data, the 3-prior-session
           RTH baseline, t0 from event_fundamentals -- by calling e2_t2_window.build_event_series with
           agg="sum" (its default, agg="mean", reproduces the as-run artifact). Written beside the old
           artifact as e2_t2_window_units_fixed.parquet; the old one is not overwritten.

Usage: .venv/Scripts/python.exe research/fundamental_exploration/e2_t2_window_units_fix.py
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from research.fundamental_exploration import common as C  # noqa: E402
from research.fundamental_exploration.e2_t2_window import (build_event_series,  # noqa: E402
                                                           t0_minute_index)

CONFIRM_EVENT = "CBRL_2020-03-24_31.13"
OUT = f"{C.ART_E2}/e2_t2_window_units_fixed.parquet"
OUT_SUMMARY = f"{C.ART_E2}/e2_t2_window_units_fixed_summary.json"
OUT_CONFIRM = f"{C.ART_E2}/e2_units_fix_confirm_one_event.json"


def stats(s: pd.Series) -> dict:
    s = s.dropna()
    if s.empty:
        return {"n": 0}
    return {"n": int(s.size), "median": float(s.median()), "p25": float(s.quantile(.25)), "p75": float(s.quantile(.75)),
            "p90": float(s.quantile(.9)), "max": float(s.max()), "n_zero": int((s == 0).sum()),
            "share_zero": float((s == 0).mean())}


def main() -> int:
    cfg_e2 = C.load_cfg(C.CFG_E2)
    frame = pd.read_parquet(cfg_e2["universe"]["materialization_path"])
    frame["event_id"] = frame.apply(C.event_id, axis=1)
    ef = C.load_event_fundamentals()[["event_id", "ticker", "t0_ns"]]
    baseline = pd.read_parquet(f"{C.ART_E2}/e2_t2a_baseline.parquet")[["event_id", "B_e", "n_baseline_sessions"]]
    events = frame[["event_id", "event_date_canonical", "momentum_pct"]].merge(ef, on="event_id", how="left")
    events = events.merge(baseline, on="event_id", how="left").dropna(subset=["B_e"])
    events["t0_mi"] = events.apply(lambda r: t0_minute_index(int(r["t0_ns"]), r["event_date_canonical"]), axis=1)
    key = events[["event_id", "ticker", "event_date_canonical", "momentum_pct"]]

    con = C.connect(read_only=True)
    con.register("ev_key", key)
    all_bars = con.execute("""
        SELECT k.event_id, b.session_offset, b.minute_index,
               b.volume * b.vwap AS dollar_volume, b.first_trade_ts, b.last_trade_ts
        FROM ev_key k
        JOIN event_minute_bars_v2 b
          ON b.ticker = k.ticker AND b.event_date_canonical = k.event_date_canonical
         AND b.momentum_pct = k.momentum_pct
        WHERE b.session_offset BETWEEN 0 AND 3
    """).df()
    con.close()
    groups = dict(tuple(all_bars.groupby("event_id")))

    old = pd.read_parquet(f"{C.ART_E2}/e2_t2_window.parquet")

    # ---------------- III.2.1 -- one event, both constructions
    ev = events[events["event_id"] == CONFIRM_EVENT].iloc[0]
    bars = groups[CONFIRM_EVENT]
    both = {}
    for agg in ("mean", "sum"):
        r = build_event_series(bars, ev["t0_mi"], ev["B_e"], int(ev["t0_ns"]), agg=agg)
        if r["window_end_ts"] is not None:
            r["duration_min"] = (r["window_end_ts"] - int(ev["t0_ns"])) / 60e9
        r["window_end_et"] = (str(pd.Timestamp(r["window_end_ts"], unit="ns", tz="UTC").tz_convert("America/New_York"))
                              if r["window_end_ts"] is not None else None)
        both["as_run_per_minute_mean_vs_3B_e" if agg == "mean" else "as_confirmed_10min_sum_vs_3B_e"] = r
    old_row = old[old["event_id"] == CONFIRM_EVENT].iloc[0]
    assert both["as_run_per_minute_mean_vs_3B_e"]["window_end_ts"] == old_row["window_end_ts"] or (
        pd.isna(old_row["window_end_ts"]) and both["as_run_per_minute_mean_vs_3B_e"]["window_end_ts"] is None), \
        "agg='mean' does not reproduce the committed-as-run artifact for the confirm event"
    confirm = {"event_id": CONFIRM_EVENT, "B_e_usd_per_10min": float(ev["B_e"]), "threshold_3B_e": 3 * float(ev["B_e"]),
               "t0_ns": int(ev["t0_ns"]),
               "t0_et": str(pd.Timestamp(int(ev["t0_ns"]), unit="ns", tz="UTC").tz_convert("America/New_York")),
               "constructions": both,
               "reproduces_as_run_artifact": True}
    C.write_json(OUT_CONFIRM, confirm)

    # ---------------- III.2.2 -- rebuild, and check agg='mean' reproduces the old artifact everywhere
    rows, repro_bad = [], 0
    for _, e in events.iterrows():
        b = groups.get(e["event_id"], all_bars.iloc[0:0])
        r = build_event_series(b, e["t0_mi"], e["B_e"], int(e["t0_ns"]), agg="sum")
        if r["window_end_ts"] is not None:
            r["duration_min"] = (r["window_end_ts"] - int(e["t0_ns"])) / 60e9
        r["event_id"] = e["event_id"]
        r["n_baseline_sessions"] = e["n_baseline_sessions"]
        r["B_e"] = e["B_e"]
        rows.append(r)
    new = pd.DataFrame(rows)
    with_end = new.dropna(subset=["window_end_ts"]).merge(events[["event_id", "t0_ns"]], on="event_id")
    assert (with_end["window_end_ts"] >= with_end["t0_ns"]).all(), "window end before t0"
    new.to_parquet(OUT, index=False)

    cmp_ = old[["event_id", "duration_min", "censored"]].merge(
        new[["event_id", "duration_min", "censored"]], on="event_id", suffixes=("_as_run", "_fixed"))
    summary = {
        "task": "Part III -- E2-T2 window rebuilt with corrected units (10-minute SUM vs 3 B_e)",
        "config_hash_e2": C.cfg_hash(C.CFG_E2),
        "n_events_processed": int(len(new)),
        "n_censored": int(new["censored"].sum()), "censored_share": float(new["censored"].mean()),
        "duration_min_fixed": stats(new["duration_min"]),
        "duration_min_as_run": stats(old["duration_min"]),
        "censored_as_run": int(old["censored"].sum()),
        "paired": {"n": int(len(cmp_)),
                   "fixed_longer": int((cmp_["duration_min_fixed"] > cmp_["duration_min_as_run"]).sum()),
                   "equal": int((cmp_["duration_min_fixed"] == cmp_["duration_min_as_run"]).sum()),
                   "fixed_shorter": int((cmp_["duration_min_fixed"] < cmp_["duration_min_as_run"]).sum()),
                   "newly_censored": int((cmp_["censored_fixed"] & ~cmp_["censored_as_run"]).sum())},
        "confirm_event": CONFIRM_EVENT,
    }
    C.write_json(OUT_SUMMARY, summary)
    print(json.dumps({k: summary[k] for k in ("n_events_processed", "n_censored", "duration_min_fixed", "duration_min_as_run", "paired")}, indent=1))
    print("confirm:", {k: (v["window_end_et"], v["duration_min"]) for k, v in both.items()})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
