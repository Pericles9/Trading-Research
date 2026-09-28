"""
E2-T6 charts (scatter/strip alternative to 01-05's box grids): duration_min vs each
fundamental, one marker per event, mirroring e2_chart_t5_scatter.py exactly except
for the response variable and a linear y-axis (duration_min is 52% exactly 0, per
E2-T3 -- cannot render on a log axis, same reason 01-05 use linear). Additive:
files 07-11, 01-06 untouched.

Usage: .venv/Scripts/python.exe research/fundamental_exploration/e2_chart_t6_scatter.py
"""
from __future__ import annotations

import os
import sys

import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from research.fundamental_exploration import chart_scatter_common as SC  # noqa: E402
from research.fundamental_exploration import common as C  # noqa: E402


def main():
    df = pd.read_parquet(C.ev(f"{C.ART_E2}/e2_t6_scatter_events.parquet"))
    cap_base = (
        f"sample: D1, n={len(df):,} (per-panel n shown; coverage gaps drop points, never impute). "
        + C.censored_text() + "."
    )

    SC.continuous_scatter_by_year(
        df, x_col="shs_shares_outstanding_corrected", y_col="duration_min", color_col="detection_price_decile",
        title="E2-T6 (scatter): duration_min vs shares outstanding, by year",
        x_title="shares outstanding (corrected)", y_title=f"duration_min (linear -- {C.zero_share_text()} exactly 0)",
        log_x=True, log_y=False, colorbar_title="price decile",
        cap=f"{cap_base}<br>filters: color=detection-price decile, facet=event year. "
            "Replaces 01's decile-box grid with the raw per-event cloud.",
        out_root=C.CHARTS_E2, out_subdir="e2_t6", out_name=C.ev("07_duration_vs_shares_outstanding_scatter"),
    )
    SC.continuous_scatter_by_year(
        df.assign(flg_lag_days_p1=df["flg_lag_days"] + 1),
        x_col="flg_lag_days_p1", y_col="duration_min", color_col="detection_price_decile",
        title="E2-T6 (scatter): duration_min vs days-since-filing, by year",
        x_title="filing lag, days + 1", y_title=f"duration_min (linear -- {C.zero_share_text()} exactly 0)",
        log_x=True, log_y=False, colorbar_title="price decile",
        cap=f"{cap_base}<br>filters: color=detection-price decile, facet=event year. x is lag_days+1 so "
            "same-day filings (lag=0) still render on a log axis. Replaces 04's bucket-box grid with "
            "the continuous variable directly.",
        out_root=C.CHARTS_E2, out_subdir="e2_t6", out_name=C.ev("08_duration_vs_filing_lag_scatter"),
    )
    SC.categorical_strip_by_year(
        df, cat_col="split_dilution", cat_order=["False", "True", "unavailable"],
        y_col="duration_min", color_col="detection_price_decile",
        title="E2-T6 (strip): duration_min by dilution flag, by year",
        y_title=f"duration_min (linear -- {C.zero_share_text()} exactly 0)", log_y=False, colorbar_title="price decile",
        cap=f"{cap_base}<br>filters: color=detection-price decile, facet=event year, x jittered within "
            "category (seed 42). Replaces 02's decile-box grid.",
        out_root=C.CHARTS_E2, out_subdir="e2_t6", out_name=C.ev("09_duration_by_dilution_flag_strip"),
    )
    SC.categorical_strip_by_year(
        df, cat_col="split_reverse_split", cat_order=["False", "True"],
        y_col="duration_min", color_col="detection_price_decile",
        title="E2-T6 (strip): duration_min by reverse-split flag, by year",
        y_title=f"duration_min (linear -- {C.zero_share_text()} exactly 0)", log_y=False, colorbar_title="price decile",
        cap=f"{cap_base}<br>filters: color=detection-price decile, facet=event year, x jittered within "
            "category (seed 42). Replaces 03's decile-box grid.",
        out_root=C.CHARTS_E2, out_subdir="e2_t6", out_name=C.ev("10_duration_by_reverse_split_strip"),
    )
    SC.categorical_strip_by_year(
        df, cat_col="split_si_quality", cat_order=["observed", "unavailable"],
        y_col="duration_min", color_col="detection_price_decile",
        title="E2-T6 (strip): duration_min by si_quality, by year",
        y_title=f"duration_min (linear -- {C.zero_share_text()} exactly 0)", log_y=False, colorbar_title="price decile",
        cap=f"{cap_base}<br>filters: color=detection-price decile, facet=event year, x jittered within "
            "category (seed 42). Replaces 05's decile-box grid.",
        out_root=C.CHARTS_E2, out_subdir="e2_t6", out_name=C.ev("11_duration_by_si_quality_strip"),
    )


if __name__ == "__main__":
    main()
