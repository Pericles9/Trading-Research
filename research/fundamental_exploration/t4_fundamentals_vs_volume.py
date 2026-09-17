"""
E1-T4: fundamentals against volume. Event volume, and turnover as a fraction of
shares outstanding, by shares-outstanding decile -- within year, within
detection-price decile (T2's own finding: coverage is collinear with the calendar, so
everything downstream runs within year; T5/T7 already show price is a real competing
axis, so it's held fixed here too).

Turnover = volume_shares / shs_shares_outstanding_corrected (SS1's split-correction,
common.add_corrected_shares_outstanding) is a LOWER BOUND on turnover against true
float (shares outstanding >= float), and only an ordinal ranking, never a level --
labeled that way on the axis itself, not just the caption, per the brief's own
instruction.

common.py's shs_share_count_suspect diagnostic (found while building this task,
generalized in E1-T6) flags events whose corrected share count is implausibly small
(<100,000, a stated round threshold, never a filter) -- these inflate any cell's MEAN
turnover sharply (one event alone reaches 790,351x) while leaving the median/IQR the
box plot foregrounds comparatively unaffected. Reported per cell here so an unusually
high mean in one panel can be traced back to it rather than read as a real signal.

Usage: .venv/Scripts/python.exe research/fundamental_exploration/t4_fundamentals_vs_volume.py
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
        "n": int(len(s)), "mean": float(s.mean()), "max": float(s.max()),
        "p10": float(s.quantile(0.10)), "p25": float(s.quantile(0.25)),
        "median": float(s.quantile(0.50)), "p75": float(s.quantile(0.75)),
        "p90": float(s.quantile(0.90)),
    }


def main() -> int:
    df = pd.read_parquet(f"{C.ART}/e1_joined.parquet")
    tape = pd.read_parquet(f"{C.ART}/tape_metrics.parquet")
    df = df.merge(tape, on="event_id", how="left")
    df = C.add_corrected_shares_outstanding(df)
    df = C.add_identity_fields(df)

    df["shs_decile"] = pd.qcut(df["shs_shares_outstanding_corrected"], N_DECILES, labels=False, duplicates="drop")
    df["turnover_lower_bound"] = df["volume_shares"] / df["shs_shares_outstanding_corrected"]

    n_no_shs = int(df["shs_shares_outstanding_corrected"].isna().sum())
    n_zero_volume = int((df["volume_shares"] == 0).sum())
    n_shs_zero_artifact = int(df["shs_zero_artifact"].sum())

    cells = []
    for (year, pdec, sdec), g in df.groupby(["year", "detection_price_decile", "shs_decile"], observed=True):
        cells.append({
            "year": year, "price_decile": int(pdec), "shs_decile": int(sdec),
            "volume_shares": stats(g["volume_shares"]),
            "turnover_lower_bound": stats(g["turnover_lower_bound"]),
            "n_shs_share_count_suspect": int(g["shs_share_count_suspect"].sum()),
        })
    C.write_json(f"{C.ART}/t4_cells.json", {"cells": cells})

    n_cells = len(cells)
    n_suppressed = sum(1 for c in cells if c["turnover_lower_bound"]["n"] < MIN_CELL_N)

    summary = {
        "task": "E1-T4 fundamentals against volume",
        "config_hash": C.cfg_hash(),
        "n_total": len(df),
        "n_no_shs_data": n_no_shs,
        "n_shs_zero_artifact": n_shs_zero_artifact,
        "n_shs_zero_artifact_note": "shs_shares_outstanding==0.0 exactly, a data artifact (common.py's "
            "add_corrected_shares_outstanding) -- shs_shares_outstanding_corrected is NaN for these, so "
            "they're excluded here (n_no_shs_data above includes them), not divided-by-zero into inf.",
        "n_zero_session_volume": n_zero_volume,
        "n_shs_share_count_suspect": int(df["shs_share_count_suspect"].sum()),
        "n_shs_share_count_suspect_note": f"shs_shares_outstanding_corrected < "
            f"{C.SHARE_COUNT_SUSPECT_THRESHOLD:,} shares -- descriptive diagnostic, never a filter "
            f"(common.py, generalized from this task's own finding). Inflates cell means, not medians.",
        "n_cells_total": n_cells,
        "n_cells_suppressed": n_suppressed,
        "min_cell_n_display_floor": MIN_CELL_N,
        "turnover_definition": "volume_shares (regular-session, event_date_canonical) / "
                                "shs_shares_outstanding_corrected -- a LOWER BOUND vs true float, "
                                "ordinal ranking only, never a level.",
    }
    C.write_json(f"{C.ART}/t4_fundamentals_vs_volume_summary.json", summary)
    print(json.dumps(summary, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
