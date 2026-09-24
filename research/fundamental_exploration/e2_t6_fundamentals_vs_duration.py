"""
E2-T6: fundamentals against window duration. Same splits and within-year, within-
detection-price-decile structure as E2-T5, plus E2-T4's facets (t0 session segment).
Censored share reported per cell -- a cell whose censored share differs from its
neighbours is reporting censoring, not duration (per the brief). Note: censored_share
is 0 for the population as a whole (E2-T2/T3), so every cell's censored share is
trivially 0 too -- reported explicitly rather than silently omitted just because it's
uniform.

Two cross-cuts, not one four-way grid (year x price_decile x split x segment would be
too sparse to read): (1) year x price_decile x split_value, matching E2-T5 exactly, and
(2) t0_segment x split_value, the direct E2-T4 facet, kept separate and coarser so it
stays legible on its own.

Usage: .venv/Scripts/python.exe research/fundamental_exploration/e2_t6_fundamentals_vs_duration.py
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from research.fundamental_exploration import common as C  # noqa: E402
from research.fundamental_exploration.e2_t5_fundamentals_vs_momentum import SPLITS  # noqa: E402

N_DECILES = C.load_cfg()["deciles"]["n"]
MIN_CELL_N = C.load_cfg()["min_cell_n_display_floor"]


def stats(s: pd.Series) -> dict:
    s = s.dropna()
    if len(s) == 0:
        return {"n": 0}
    return {
        "n": int(len(s)), "mean": float(s.mean()),
        "p10": float(s.quantile(0.10)), "p25": float(s.quantile(0.25)),
        "median": float(s.quantile(0.50)), "p75": float(s.quantile(0.75)), "p90": float(s.quantile(0.90)),
    }


def build_frame() -> pd.DataFrame:
    cfg_e2 = C.load_cfg(C.CFG_E2)
    frame = pd.read_parquet(cfg_e2["universe"]["materialization_path"])
    frame["event_id"] = frame.apply(C.event_id, axis=1)

    ef = pd.read_parquet(f"{C.ART_E2}/e2_d1_fundamentals.parquet")
    ef = C.add_corrected_shares_outstanding(ef)
    ef = ef.merge(C.load_detection_price(), on="event_id", how="left")

    window = pd.read_parquet(C.ev(f"{C.ART_E2}/e2_t2_window.parquet"))[["event_id", "duration_min", "censored"]]
    tod = pd.read_parquet(C.ev(f"{C.ART_E2}/e2_t4_time_of_day.parquet"))[["event_id", "t0_segment"]]

    df = frame[["event_id"]].merge(ef, on="event_id", how="inner")
    df = df.merge(window, on="event_id", how="inner").merge(tod, on="event_id", how="inner")
    df = C.add_identity_fields(df)
    df["shs_decile"] = pd.qcut(df["shs_shares_outstanding_corrected"], N_DECILES, labels=False, duplicates="drop")
    df["flg_lag_days"] = df["flg_lag_ns"] / 86_400e9
    df["flg_lag_bucket"] = pd.cut(
        df["flg_lag_days"], bins=[-0.001, 1, 7, 30, 90, np.inf],
        labels=["<=1d", "1-7d", "7-30d", "30-90d", ">90d"],
    )
    return df


def cell_dict(g: pd.DataFrame) -> dict:
    return {
        "duration_min": stats(g["duration_min"]), "n": len(g),
        "censored_share": float(g["censored"].mean()),
        "share_zero": float((g["duration_min"] == 0).mean()),
    }


def main() -> int:
    df = build_frame()

    year_price_splits = {}
    segment_splits = {}
    for split_name, split_fn in SPLITS.items():
        df[f"_split_{split_name}"] = split_fn(df)

        cells = []
        for (year, pdec, sval), g in df.groupby(["year", "detection_price_decile", f"_split_{split_name}"], observed=True):
            cells.append({"year": year, "price_decile": int(pdec) if pd.notna(pdec) else None,
                          "split_value": sval, **cell_dict(g)})
        year_price_splits[split_name] = cells

        seg_cells = []
        for (seg, sval), g in df.groupby(["t0_segment", f"_split_{split_name}"], observed=True):
            seg_cells.append({"t0_segment": seg, "split_value": sval, **cell_dict(g)})
        segment_splits[split_name] = seg_cells

    C.write_json(C.ev(f"{C.ART_E2}/e2_t6_cells_year_price.json"), {"splits": year_price_splits})
    C.write_json(C.ev(f"{C.ART_E2}/e2_t6_cells_segment.json"), {"splits": segment_splits})

    n_cells_total = sum(len(v) for v in year_price_splits.values())
    n_cells_suppressed = sum(1 for cells in year_price_splits.values() for c in cells if c["n"] < MIN_CELL_N)

    summary = {
        "task": "E2-T6 fundamentals against window duration",
        "config_hash": C.cfg_hash(C.CFG_E2),
        "n_total": len(df),
        "splits": list(SPLITS.keys()),
        "n_cells_total_year_price": n_cells_total,
        "n_cells_suppressed_year_price": n_cells_suppressed,
        "min_cell_n_display_floor": MIN_CELL_N,
        "overall_censored_share": float(df["censored"].mean()),
        "overall_censored_share_note": "0 for the population as a whole (E2-T2/T3) -- every cell's own "
                                        "censored_share is trivially 0 too, reported explicitly rather "
                                        "than omitted because it's uniform.",
        "overall_duration": stats(df["duration_min"]),
    }
    C.write_json(C.ev(f"{C.ART_E2}/e2_t6_fundamentals_vs_duration_summary.json"), summary)
    print(json.dumps(summary, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
