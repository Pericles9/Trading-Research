"""
E2-T5: fundamentals against momentum_pct. Splits: shs_shares_outstanding decile,
flg_dilution_form_before_t0, spl_reverse_split_365d, flg_lag_ns bucket, si_ where
covered. Within year, within detection-price decile, per the brief. Read against
E2-T1's audit (no split flagged as materially closer to the volume-selection boundary).

momentum_pct: DE-1 (Cooper's sign-off) -- described only, never bucketed as an input to
anything else, never entering a computed statistic beyond this task's own distribution
summaries.

detection_price_decile: E1's own artifact (research/fundamental_exploration/
common.py's load_detection_price()), reused, not re-derived.

Usage: .venv/Scripts/python.exe research/fundamental_exploration/e2_t5_fundamentals_vs_momentum.py
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from research.fundamental_exploration import common as C  # noqa: E402

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


def build_response_frame() -> pd.DataFrame:
    cfg_e2 = C.load_cfg(C.CFG_E2)
    frame = pd.read_parquet(cfg_e2["universe"]["materialization_path"])
    frame["event_id"] = frame.apply(C.event_id, axis=1)

    ef = pd.read_parquet(f"{C.ART_E2}/e2_d1_fundamentals.parquet")
    ef = C.add_corrected_shares_outstanding(ef)
    ef = ef.merge(C.load_detection_price(), on="event_id", how="left")
    # ef has no momentum_pct of its own -- add_identity_fields (called once, below, after
    # this merge) would re-derive it from event_id and collide with frame's own column.

    df = frame[["event_id", "momentum_pct"]].merge(ef, on="event_id", how="inner")
    df = C.add_identity_fields(df)  # adds event_date_canonical/year; re-derives momentum_pct
    # from event_id (direct overwrite, not a merge) -- numerically identical to frame's own
    # column since both trace back to the same event_id string, not a collision.
    df["shs_decile"] = pd.qcut(df["shs_shares_outstanding_corrected"], N_DECILES, labels=False, duplicates="drop")
    df["flg_lag_days"] = df["flg_lag_ns"] / 86_400e9
    df["flg_lag_bucket"] = pd.cut(
        df["flg_lag_days"], bins=[-0.001, 1, 7, 30, 90, np.inf],
        labels=["<=1d", "1-7d", "7-30d", "30-90d", ">90d"],
    )
    return df


SPLITS = {
    "shs_decile": lambda df: df["shs_decile"].map(lambda d: f"S{int(d)}" if pd.notna(d) else "no_shs_data"),
    "flg_dilution_form_before_t0": lambda df: np.where(
        df["flg_quality"] == "unavailable", "unavailable", df["flg_dilution_form_before_t0"].astype(str)
    ),
    "spl_reverse_split_365d": lambda df: df["spl_reverse_split_365d"].astype(str),
    "flg_lag_bucket": lambda df: df["flg_lag_bucket"].astype(str),
    "si_quality": lambda df: df["si_quality"].astype(str),
}


def main() -> int:
    df = build_response_frame()

    results = {}
    for split_name, split_fn in SPLITS.items():
        df[f"_split_{split_name}"] = split_fn(df)
        cells = []
        for (year, pdec, sval), g in df.groupby(["year", "detection_price_decile", f"_split_{split_name}"], observed=True):
            cells.append({"year": year, "price_decile": int(pdec) if pd.notna(pdec) else None,
                          "split_value": sval, "momentum_pct": stats(g["momentum_pct"])})
        results[split_name] = cells

    n_cells_total = sum(len(v) for v in results.values())
    n_cells_suppressed = sum(1 for cells in results.values() for c in cells if c["momentum_pct"]["n"] < MIN_CELL_N)

    C.write_json(f"{C.ART_E2}/e2_t5_cells.json", {"splits": results})
    summary = {
        "task": "E2-T5 fundamentals against momentum_pct",
        "config_hash": C.cfg_hash(C.CFG_E2),
        "n_total": len(df),
        "splits": list(SPLITS.keys()),
        "n_cells_total": n_cells_total,
        "n_cells_suppressed": n_cells_suppressed,
        "min_cell_n_display_floor": MIN_CELL_N,
        "overall_momentum_pct": stats(df["momentum_pct"]),
    }
    C.write_json(f"{C.ART_E2}/e2_t5_fundamentals_vs_momentum_summary.json", summary)
    print(json.dumps(summary, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
