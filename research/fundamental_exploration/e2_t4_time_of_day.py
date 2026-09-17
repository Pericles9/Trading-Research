"""
E2-T4: the time-of-day confound, made visible, without any fundamental variable. A flat
RTH-based baseline gives a morning event further to fall than an afternoon one (T3's own
result already shows this mechanically: duration is overwhelmingly 0 for events whose t0
sits well below their own baseline's own scale). This establishes the size of that effect
on its own so E2-T5/T6's fundamental-split panels can be read against it, per the brief.

t0_minute_index reused verbatim from e2_t2_window.py (not re-derived) -- minute_index 0 ==
04:00:00 America/New_York, confirmed directly against event_minute_bars_v2's own
first_trade_ts values.

Usage: .venv/Scripts/python.exe research/fundamental_exploration/e2_t4_time_of_day.py
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from research.fundamental_exploration import common as C  # noqa: E402
from research.fundamental_exploration.e2_t2_window import t0_minute_index  # noqa: E402

# minute_index boundaries confirmed directly: 0=04:00, 330=09:30 (rth open), 720=16:00 (rth close)
SEGMENT_BOUNDS = [(0, 330, "pre_market"), (330, 720, "regular"), (720, 960, "after_hours")]


def classify_segment(mi: int) -> str:
    for lo, hi, label in SEGMENT_BOUNDS:
        if lo <= mi < hi:
            return label
    return "out_of_range"


def half_hour_label(mi: int) -> str:
    start_min_of_day = (4 * 60 + mi // 30 * 30) % (24 * 60)
    h, m = divmod(start_min_of_day, 60)
    end_min_of_day = (start_min_of_day + 30) % (24 * 60)
    eh, em = divmod(end_min_of_day, 60)
    return f"{h:02d}:{m:02d}-{eh:02d}:{em:02d}"


def main() -> int:
    cfg_e2 = C.load_cfg(C.CFG_E2)
    frame = pd.read_parquet(cfg_e2["universe"]["materialization_path"])
    frame["event_id"] = frame.apply(C.event_id, axis=1)
    ef = C.load_event_fundamentals()[["event_id", "t0_ns"]]

    window = pd.read_parquet(f"{C.ART_E2}/e2_t2_window.parquet")
    df = frame[["event_id", "event_date_canonical"]].merge(ef, on="event_id", how="left")
    df = df.merge(window, on="event_id", how="inner")  # only events with a built window

    df["t0_mi"] = df.apply(lambda r: t0_minute_index(int(r["t0_ns"]), r["event_date_canonical"]), axis=1)
    df["t0_segment"] = df["t0_mi"].apply(classify_segment)
    df["t0_half_hour"] = df["t0_mi"].apply(half_hour_label)
    df["t0_half_hour_order"] = df["t0_mi"] // 30

    df[["event_id", "t0_mi", "t0_segment", "t0_half_hour", "t0_half_hour_order"]].to_parquet(
        f"{C.ART_E2}/e2_t4_time_of_day.parquet", index=False
    )

    def stats(s: pd.Series) -> dict:
        s = s.dropna()
        if len(s) == 0:
            return {"n": 0}
        return {"n": int(len(s)), "mean": float(s.mean()), "median": float(s.median()),
                "share_zero": float((s == 0).mean()), "p75": float(s.quantile(0.75)),
                "p90": float(s.quantile(0.90))}

    by_segment = {seg: stats(df.loc[df["t0_segment"] == seg, "duration_min"])
                  for seg in ["pre_market", "regular", "after_hours"]}
    by_half_hour = {}
    for order in sorted(df["t0_half_hour_order"].unique()):
        sub = df[df["t0_half_hour_order"] == order]
        label = sub["t0_half_hour"].iloc[0]
        by_half_hour[label] = {"order": int(order), **stats(sub["duration_min"])}

    summary = {
        "task": "E2-T4 time-of-day confound",
        "config_hash": C.cfg_hash(C.CFG_E2),
        "n_total": len(df),
        "segment_counts": df["t0_segment"].value_counts().to_dict(),
        "duration_by_segment": by_segment,
        "duration_by_half_hour": by_half_hour,
    }
    C.write_json(f"{C.ART_E2}/e2_t4_time_of_day_summary.json", summary)
    print(json.dumps(summary, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
