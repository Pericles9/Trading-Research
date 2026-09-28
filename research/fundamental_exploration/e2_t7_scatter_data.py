"""
E2-T7 scatter chart data prep: persists per-event momentum_pct/duration_min against
the continuous detection_price (not binned to deciles) plus year, for the true-
scatter alternative to 01's box-plot-by-decile chart. Mirrors
e2_t7_price_decile_arm_zero.py's own frame construction (same joins, same source
columns) with year added via add_identity_fields -- no new logic, only a different
persistence shape (raw rows, not decile-aggregated stats).

Usage: .venv/Scripts/python.exe research/fundamental_exploration/e2_t7_scatter_data.py
"""
from __future__ import annotations

import os
import sys

import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from research.fundamental_exploration import common as C  # noqa: E402


def main() -> int:
    cfg_e2 = C.load_cfg(C.CFG_E2)
    frame = pd.read_parquet(cfg_e2["universe"]["materialization_path"])
    frame["event_id"] = frame.apply(C.event_id, axis=1)
    detp = C.load_detection_price()

    momentum_df = frame[["event_id", "momentum_pct"]].merge(detp, on="event_id", how="left")
    momentum_df = C.add_identity_fields(momentum_df)
    mom_path = C.ev(f"{C.ART_E2}/e2_t7_scatter_momentum.parquet")
    momentum_df[["event_id", "year", "momentum_pct", "detection_price"]].to_parquet(mom_path, index=False)

    window = pd.read_parquet(C.ev(f"{C.ART_E2}/e2_t2_window.parquet"))[["event_id", "duration_min", "censored"]]
    duration_df = frame[["event_id"]].merge(window, on="event_id", how="inner").merge(
        detp, on="event_id", how="left"
    )
    duration_df = C.add_identity_fields(duration_df)
    dur_path = C.ev(f"{C.ART_E2}/e2_t7_scatter_duration.parquet")
    duration_df[["event_id", "year", "duration_min", "censored", "detection_price"]].to_parquet(dur_path, index=False)

    print(f"wrote {mom_path} rows={len(momentum_df):,}; wrote {dur_path} rows={len(duration_df):,}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
