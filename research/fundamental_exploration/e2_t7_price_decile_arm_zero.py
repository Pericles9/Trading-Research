"""
E2-T7: price-decile arm zero. Both responses split by detection-price decile ALONE, no
fundamental variable, no year cross-cut -- the control E2-T5/T6 are read against.
Phase 11 established net edge is a function of price level; if price decile alone
reproduces what the fundamental splits show, the fundamental layer earned nothing here.

Usage: .venv/Scripts/python.exe research/fundamental_exploration/e2_t7_price_decile_arm_zero.py
"""
from __future__ import annotations

import json
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from research.fundamental_exploration import common as C  # noqa: E402


def stats(s: pd.Series) -> dict:
    s = s.dropna()
    if len(s) == 0:
        return {"n": 0}
    return {
        "n": int(len(s)), "mean": float(s.mean()),
        "p10": float(s.quantile(0.10)), "p25": float(s.quantile(0.25)),
        "median": float(s.quantile(0.50)), "p75": float(s.quantile(0.75)), "p90": float(s.quantile(0.90)),
    }


def main() -> int:
    cfg_e2 = C.load_cfg(C.CFG_E2)
    frame = pd.read_parquet(cfg_e2["universe"]["materialization_path"])
    frame["event_id"] = frame.apply(C.event_id, axis=1)
    detp = C.load_detection_price()

    momentum_df = frame[["event_id", "momentum_pct"]].merge(detp, on="event_id", how="left")

    window = pd.read_parquet(f"{C.ART_E2}/e2_t2_window.parquet")[["event_id", "duration_min", "censored"]]
    duration_df = frame[["event_id"]].merge(window, on="event_id", how="inner").merge(
        detp, on="event_id", how="left"
    )

    momentum_by_decile = {}
    for d, g in momentum_df.groupby("detection_price_decile"):
        momentum_by_decile[int(d)] = stats(g["momentum_pct"])

    duration_by_decile = {}
    for d, g in duration_df.groupby("detection_price_decile"):
        duration_by_decile[int(d)] = {"duration_min": stats(g["duration_min"]),
                                       "censored_share": float(g["censored"].mean())}

    momentum_by_decile_out = pd.DataFrame(momentum_by_decile).T.reset_index().rename(columns={"index": "decile"})
    momentum_by_decile_out.to_parquet(f"{C.ART_E2}/e2_t7_momentum_by_decile.parquet", index=False)

    summary = {
        "task": "E2-T7 price-decile arm zero",
        "config_hash": C.cfg_hash(C.CFG_E2),
        "n_momentum": len(momentum_df),
        "n_duration": len(duration_df),
        "momentum_pct_by_price_decile": momentum_by_decile,
        "duration_min_by_price_decile": duration_by_decile,
    }
    C.write_json(f"{C.ART_E2}/e2_t7_price_decile_arm_zero_summary.json", summary)
    print(json.dumps(summary, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
