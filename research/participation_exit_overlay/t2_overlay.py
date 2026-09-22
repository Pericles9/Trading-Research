"""
T2: the timing overlay.

Four timestamps per event on one clock, in seconds from t0:

    t0 -> participation_onset -> tau (EPG entry) -> window_close (EPG exit) -> participation_end

Two distributions are the object:

  window_close - participation_end   negative means EPG exits while participation is still live.
                                     THIS IS THE HEADLINE NUMBER.
  tau - participation_onset          negative means EPG enters before participation arrives.

Both faceted by n_baseline_sessions (E2 DE-2), session segment, and detection-price decile.
Censored events are their own class with their share stated; no mean is taken across censored and
uncensored (E2 DE-3), which is why every facet reports medians and quantiles and the censored
count sits beside them rather than inside them.

The overlay uses the FACT timestamps, not the confirmed ones: it asks when participation moved,
not when a trader could have known. T3's exit uses the confirmed instant.

Usage: .venv/Scripts/python.exe research/participation_exit_overlay/t2_overlay.py
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from research.participation_exit_overlay import common as C  # noqa: E402

IN = f"{C.ART}/t1_participation.parquet"
OUT_JSON = f"{C.ART}/t2_overlay.json"
OUT_PARQUET = f"{C.ART}/t2_overlay.parquet"

FLOOR = 20


def qd(x, ps=(.05, .25, .5, .75, .95)):
    x = np.asarray(x, dtype=float)
    x = x[np.isfinite(x)]
    if x.size == 0:
        return {}
    return {"n": int(x.size),
            **{f"p{int(p * 100)}": round(float(np.quantile(x, p)), 1) for p in ps}}


def facet(d: pd.DataFrame, by: str, col: str, censor_col: str) -> list:
    out = []
    for k, g in d.groupby(by, dropna=False):
        v = g[col]
        row = {by: str(k), "n": int(len(g)),
               "n_censored": int(g[censor_col].sum()),
               "share_censored": round(float(g[censor_col].mean()), 4),
               "n_defined": int(v.notna().sum())}
        if int(v.notna().sum()) < FLOOR:
            row["below_display_floor"] = True
        else:
            row.update(qd(v))
            row["share_negative"] = round(float((v.dropna() < 0).mean()), 4)
        out.append(row)
    return out


def main() -> int:
    cfg = C.load_cfg()
    d = pd.read_parquet(C.REPO / IN)

    dp = pd.read_parquet(C.REPO / C.DETECTION_PRICE)
    d = d.merge(dp, on="event_id", how="left")
    d["move_at_decile"] = pd.qcut(d["move_at_entry"], 10, labels=False, duplicates="drop")

    # the four marks, all in seconds from t0, on one clock
    for name, col in [("onset", "participation_onset_ns"), ("tau", "tau_ns"),
                      ("window_close", "natural_exit_ts"), ("end", "participation_end_ns")]:
        d[f"sec_from_t0_{name}"] = (d[col] - d["t0_ns"]) / C.NS
    d.to_parquet(C.REPO / OUT_PARQUET, index=False)

    ok = d[d["bars_available"].fillna(False)]
    head = ok["windowclose_minus_end_sec"]
    ent = ok["tau_minus_onset_sec"]

    summary = {
        "task": "T2 timing overlay",
        "config_hash": C.cfg_hash(),
        "n": int(len(d)),
        "uses_fact_timestamps": "the overlay asks when participation MOVED. T3's exit uses the "
                                "confirmed instant, which is C minutes later.",
        "four_marks_sec_from_t0": {
            name: qd(ok[f"sec_from_t0_{name}"])
            for name in ("onset", "tau", "window_close", "end")},
        "HEADLINE_window_close_minus_participation_end_sec": {
            **qd(head),
            "n_censored_end": int(ok["end_censored"].sum()),
            "share_censored_end": round(float(ok["end_censored"].mean()), 4),
            "share_negative": round(float((head.dropna() < 0).mean()), 4),
            "reading": "negative means EPG closed the position while participation was still "
                       "live. Censored events have no participation_end inside the session and "
                       "are excluded from this statistic BY CONSTRUCTION, not by choice -- their "
                       "count is stated beside it and they are, if anything, the strongest cases "
                       "of participation outliving the window.",
        },
        "tau_minus_participation_onset_sec": {
            **qd(ent),
            "share_negative": round(float((ent.dropna() < 0).mean()), 4),
            "reading": "negative means EPG entered before participation arrived.",
        },
        "participation_already_live_at_t0": {
            "share": round(float((ok["trailing_at_t0_usd"] >= ok["threshold_usd"]).mean()), 4),
            "trailing_over_threshold_at_t0_median": round(
                float((ok["trailing_at_t0_usd"] / ok["threshold_usd"]).median()), 3),
            "reading": "the onset distribution is pinned near t0+1 minute because participation "
                       "is ALREADY above 3 x B_e at t0 for most events -- not a rule artifact. "
                       "t0 is the detection anchor, so the burst is already underway there.",
        },
        "facets": {
            "headline_by_n_baseline_sessions": facet(
                ok, "n_baseline_sessions", "windowclose_minus_end_sec", "end_censored"),
            "headline_by_session_segment": facet(
                ok, "session_bucket", "windowclose_minus_end_sec", "end_censored"),
            "headline_by_detection_price_decile": facet(
                ok, "detection_price_decile", "windowclose_minus_end_sec", "end_censored"),
            "entry_gap_by_session_segment": facet(
                ok, "session_bucket", "tau_minus_onset_sec", "onset_censored"),
        },
        "de2_baseline_thin": {"n_thin": int(ok["baseline_thin"].sum()),
                              "note": "flagged and carried; facetted above by n_baseline_sessions"},
        "output_parquet": OUT_PARQUET,
    }
    C.write_json(OUT_JSON, summary)

    print("=== FOUR MARKS, seconds from t0 ===")
    print(pd.DataFrame(summary["four_marks_sec_from_t0"]).T.to_string())
    print("\n=== HEADLINE: window_close - participation_end (sec) ===")
    print(json.dumps(summary["HEADLINE_window_close_minus_participation_end_sec"], indent=2))
    print("\n=== tau - participation_onset (sec) ===")
    print(json.dumps(summary["tau_minus_participation_onset_sec"], indent=2))
    print("\n=== participation already live at t0? ===")
    print(json.dumps(summary["participation_already_live_at_t0"], indent=2))
    for k, v in summary["facets"].items():
        print(f"\n--- {k} ---")
        print(pd.DataFrame(v).to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
