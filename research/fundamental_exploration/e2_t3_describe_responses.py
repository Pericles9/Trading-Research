"""
E2-T3: describe the two responses on their own. momentum_pct (DE-1: read directly from
momentum_events_canonical / here, already present in sampling_frame.parquet -- avoids
the pathologically slow live view scan E1-T0/E2-T0 already established, since
momentum_pct is not gated behind in_scope's own filtered_trades/filtered_quotes joins
in this materialization) and duration_min (E2-T2).

Censored share and baseline_thin share stated in-panel, not in a caption, per the
brief. baseline_thin is DEFERRED (Cooper, see config cooper_pending) -- stated as "not
computed" explicitly, never silently omitted or defaulted to a number.

Usage: .venv/Scripts/python.exe research/fundamental_exploration/e2_t3_describe_responses.py
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from research.fundamental_exploration import common as C  # noqa: E402


def dist_stats(s: pd.Series) -> dict:
    s = s.dropna()
    if len(s) == 0:
        return {"n": 0}
    return {
        "n": int(len(s)), "mean": float(s.mean()), "min": float(s.min()), "max": float(s.max()),
        "p10": float(s.quantile(0.10)), "p25": float(s.quantile(0.25)),
        "median": float(s.quantile(0.50)), "p75": float(s.quantile(0.75)), "p90": float(s.quantile(0.90)),
    }


def main() -> int:
    cfg_e2 = C.load_cfg(C.CFG_E2)
    frame = pd.read_parquet(cfg_e2["universe"]["materialization_path"])
    frame["event_id"] = frame.apply(C.event_id, axis=1)

    window = pd.read_parquet(C.ev(f"{C.ART_E2}/e2_t2_window.parquet"))
    df = frame[["event_id", "momentum_pct"]].merge(window, on="event_id", how="left")

    n_total_d1 = len(frame)
    n_with_window = len(window)
    n_censored = int(window["censored"].sum())
    n_zero_duration = int((window["duration_min"] == 0).sum())
    n_positive_duration = int((window["duration_min"] > 0).sum())

    momentum_stats = dist_stats(df["momentum_pct"])
    duration_stats = dist_stats(window["duration_min"])
    duration_positive_stats = dist_stats(window.loc[window["duration_min"] > 0, "duration_min"])

    # survival curve: share of the (uncensored + censored, Kaplan-Meier-equivalent, but
    # trivial here since censored_share is 0) population with duration_min > x, for a grid of x.
    durations_sorted = np.sort(window["duration_min"].dropna().to_numpy())
    grid = np.unique(np.concatenate([[0], durations_sorted, [durations_sorted.max() if len(durations_sorted) else 0]]))
    survival = [{"x": float(x), "share_gt_x": float((durations_sorted > x).mean())} for x in grid]

    by_n_baseline = {}
    for n_sess in sorted(window["n_baseline_sessions"].unique()):
        sub = window[window["n_baseline_sessions"] == n_sess]
        by_n_baseline[str(n_sess)] = {
            "n": len(sub), "n_censored": int(sub["censored"].sum()),
            "duration_stats": dist_stats(sub["duration_min"]),
        }

    summary = {
        "task": "E2-T3 describe the two responses",
        "config_hash": C.cfg_hash(C.CFG_E2),
        "n_total_d1": n_total_d1,
        "n_with_window": n_with_window,
        "n_skipped_no_baseline": n_total_d1 - n_with_window,
        "momentum_pct_stats": momentum_stats,
        "duration_min_stats": duration_stats,
        "duration_min_positive_only_stats": duration_positive_stats,
        "n_censored": n_censored,
        "censored_share": n_censored / n_with_window if n_with_window else None,
        "n_zero_duration": n_zero_duration,
        "zero_duration_share": n_zero_duration / n_with_window if n_with_window else None,
        "n_positive_duration": n_positive_duration,
        "baseline_thin_status": "NOT COMPUTED -- Cooper deferred the baseline floor (config "
                                 "cooper_pending.de2_baseline_floor); baseline_thin is absent from "
                                 "e2_t2_window.parquet, not defaulted to False.",
        "by_n_baseline_sessions": by_n_baseline,
        "survival_curve_note": "share of events with duration_min > x, for x on a grid spanning the "
                                "observed range. censored_share is 0 here (E2-T2), so this is the plain "
                                "empirical survival function, not a Kaplan-Meier estimator (the two "
                                "coincide when there is no censoring).",
    }
    C.write_json(C.ev(f"{C.ART_E2}/e2_t3_describe_responses_summary.json"), summary)
    C.write_json(C.ev(f"{C.ART_E2}/e2_t3_survival_curve.json"), {"survival": survival})
    print(json.dumps({k: v for k, v in summary.items() if k != "survival_curve_note"}, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
