#!/usr/bin/env python
"""
Phase 13, T4b diagnostic: root-causing the tick-vs-bar MFE disagreement T4a found.

**HARD STOP finding, 2026-09-14.** T4a's first (50-event) test run against
filtered_trades showed a one-directional disagreement between tick-derived and
bar-derived MFE cost-multiple (bar always >= tick, never <), 36% of events at the
5-minute horizon. This script traces the mechanism directly rather than guessing.

**Root cause, confirmed here:** t1_build_p0.py selects bar rows via
`minute_index <= t0_minute_index + h` where `t0_minute_index = floor(minutes since
4am to t0)`. Because minute buckets are whole-minute granular, this always includes
the ENTIRE final minute bucket (t0_minute_index + h), whose clock-time end is up to
~60 seconds past the intended `t0 + h minutes` mark. The excess is
`60 - offset_into_minute` seconds, where `offset_into_minute` is how far past its
own minute's start t0 itself falls.

**Why the excess is large in practice, not a small rounding artifact:** per D33,
15,259/20,951 events (73%) use the `minute_a102` t0 tier, whose t0_ns is
*constructed* as the start of a minute bucket (`offset_into_minute ~= 0` by
construction) -- so the excess is close to the FULL 60 seconds for most of the
population, not a random draw. Confirmed directly below: population median
`offset_into_minute` is under 1 second.

This is a one-directional, population-wide bias in every mfe_/mae_/n_bars_ column
p0_outcome.parquet carries, inherited by T2's arm-zero distributions and T3's three
splits -- every headline number already committed in results/phase_13/{REPORT.md,
digest.json} and results/reports/phase_13_report.md. Per CLAUDE.md's Escalation
section ("Hard stop means stop. Do not fix. Do not tune. Do not proceed. Commit
state, post the criterion and the observed value, wait for instruction."), this
script only measures and records -- it does not patch t1_build_p0.py or re-run
anything downstream.

Usage: .venv/Scripts/python.exe research/phase_13/t4b_lookahead_diagnosis.py
"""
from __future__ import annotations

import json
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from research.phase_13 import common as C  # noqa: E402
from research.phase_13 import t3_partitions as T3  # noqa: E402
from research.phase_13.t1_build_p0 import compute_t0_minute_index  # noqa: E402

HORIZONS = [5, 15, 30, 60]
OUT_PATH = f"{C.ART}/t4b_lookahead_diagnosis.json"


def main():
    df, _meta = T3.build_df()
    keys = pd.read_parquet("results/fundamentals_f1/artifacts/ticker_identity.parquet",
                            columns=["event_id", "event_date_canonical"])
    d = df.merge(keys, on="event_id", how="inner")
    d["t0_minute_index"] = compute_t0_minute_index(d["t0_ns"], d["event_date_canonical"])

    t0_et = pd.to_datetime(d["t0_ns"], unit="ns", utc=True).dt.tz_convert("America/New_York")
    day4am = pd.to_datetime(d["event_date_canonical"]).dt.tz_localize("America/New_York") + pd.Timedelta(hours=4)
    minute_start = day4am + pd.to_timedelta(d["t0_minute_index"], unit="m")
    offset_s = (t0_et - minute_start).dt.total_seconds()
    excess_s = 60.0 - offset_s

    summary = {
        "finding": "t1_build_p0.py's window selection (minute_index <= t0_minute_index + h) "
                   "always includes the full final minute bucket, whose clock-time end is "
                   "(60 - offset_into_minute) seconds past the intended t0 + h*60s mark. This "
                   "is a one-directional look-ahead excess in every horizon's MFE/MAE, present "
                   "in the whole P0 population, not a data-quality issue in filtered_trades or "
                   "event_minute_bars_v2 (both confirmed to agree with each other's own content; "
                   "see t4a's own tick-vs-bar comparison).",
        "n_events": len(d),
        "offset_into_minute_seconds": {
            "min": float(offset_s.min()), "median": float(offset_s.median()),
            "mean": float(offset_s.mean()), "max": float(offset_s.max()),
        },
        "excess_lookahead_seconds": {
            "min": float(excess_s.min()), "median": float(excess_s.median()),
            "mean": float(excess_s.mean()), "max": float(excess_s.max()),
        },
        "excess_as_pct_of_horizon": {
            str(h): {
                "median_pct": round(100 * excess_s.median() / (h * 60), 2),
                "mean_pct": round(100 * excess_s.mean() / (h * 60), 2),
            } for h in HORIZONS
        },
        "why_offset_is_near_zero_for_most_events": "D33's tiered t0 construction: 15,259/20,951 "
            "events (73%) use the minute_a102 tier, whose t0_ns is built AS the start of a "
            "minute bucket by construction -- offset_into_minute ~= 0 for that tier, so the "
            "excess is close to the full 60 seconds for most of the population, not a random "
            "draw averaging ~30s.",
        "affects": [
            "results/phase_13/artifacts/p0_outcome.parquet (mfe_/mae_/n_bars_ columns, all 4 horizons)",
            "results/phase_13/artifacts/t2_arm_zero_summary.json (every decile x horizon cell)",
            "results/phase_13/artifacts/t3_partition_summary.json (every split x cell)",
            "results/phase_13/{REPORT.md, digest.json}, results/reports/phase_13_report.md "
            "(every headline MFE/MAE cost-multiple number already reported)",
        ],
        "does_not_affect": [
            "T1's coverage statistics (n_bars_h.notna() share) -- coverage is about whether ANY "
            "bar exists in the window, not the window's precise length",
            "the QUALITATIVE direction of T3's group comparisons is plausibly robust (the excess "
            "applies to both sides of every split in roughly the same way, since it depends on "
            "t0's own minute-offset, not on the split value) -- NOT independently verified here; "
            "flagged as an open question for whoever resolves this, not asserted as fact",
        ],
        "not_yet_done_pending_instruction": "t1_build_p0.py is NOT patched and P0/T2/T3 are NOT "
            "re-run by this script, per CLAUDE.md's Escalation rule -- this is a HARD STOP, "
            "reported as found, not fixed.",
        "config_hash": C.cfg_hash(),
    }
    C.write_json(OUT_PATH, summary)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
