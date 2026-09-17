"""
E2-T7 chart (scatter alternative to 01's box-plot-by-decile): momentum_pct and
duration_min vs detection_price, continuous (not binned to deciles), one point per
event -- same "no fundamental variable, no year cross-cut" scope as 01. color=year
is a visual aid only (5 years fit CAT5 exactly), not a facet/cross-cut. Additive:
file 02, 01 untouched.

Usage: .venv/Scripts/python.exe research/fundamental_exploration/e2_chart_t7_scatter.py
"""
from __future__ import annotations

import os
import sys

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from research.fundamental_exploration import chart_common as CC  # noqa: E402
from research.fundamental_exploration import common as C  # noqa: E402


def main():
    mom = pd.read_parquet(f"{C.ART_E2}/e2_t7_scatter_momentum.parquet")
    dur = pd.read_parquet(f"{C.ART_E2}/e2_t7_scatter_duration.parquet")

    years = sorted(mom["year"].dropna().unique())
    color_by_year = dict(zip(years, CC.CAT5))

    fig = make_subplots(
        rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.10,
        subplot_titles=("momentum_pct vs detection_price", "duration_min vs detection_price"),
    )

    for yr in years:
        g = mom[(mom["year"] == yr) & (mom["detection_price"] > 0) & mom["momentum_pct"].notna()]
        fig.add_trace(go.Scattergl(
            x=g["detection_price"], y=g["momentum_pct"], mode="markers", name=str(yr),
            legendgroup=str(yr),
            marker=dict(size=3.2, opacity=0.42, color=color_by_year[yr], line=dict(width=0)),
            hovertemplate="price=%{x:.2f}<br>momentum=%{y:.2f}%<extra></extra>",
        ), row=1, col=1)

    for yr in years:
        g = dur[(dur["year"] == yr) & (dur["detection_price"] > 0) & dur["duration_min"].notna()]
        fig.add_trace(go.Scattergl(
            x=g["detection_price"], y=g["duration_min"], mode="markers", name=str(yr),
            legendgroup=str(yr), showlegend=False,
            marker=dict(size=3.2, opacity=0.42, color=color_by_year[yr], line=dict(width=0)),
            hovertemplate="price=%{x:.2f}<br>duration=%{y:.1f}min<extra></extra>",
        ), row=2, col=1)

    fig.update_xaxes(title="detection_price ($, log)", type="log", row=1, col=1)
    fig.update_xaxes(title="detection_price ($, log)", type="log", row=2, col=1)
    fig.update_yaxes(title="momentum_pct (%, log)", type="log", row=1, col=1)
    fig.update_yaxes(title="duration_min (linear -- 52% exactly 0, E2-T3)", row=2, col=1)

    CC.legend_inside(fig, x=0.99, xanchor="right")
    n_mom, n_dur = len(mom), len(dur)
    cap = CC.caption(
        sample=f"D1, momentum n={n_mom:,}, duration n={n_dur:,}",
        filters="detection price, continuous (not binned to deciles) -- no fundamental variable, no year "
                "cross-cut (color=year is a visual aid only, not a facet). Compare against 01's "
                "box-plot-by-decile view of the same two responses.",
    )
    CC.base_layout(
        fig, "E2-T7 (scatter): momentum_pct and duration_min vs detection_price, continuous", cap,
        height=820, width=1000, cap_y=-0.13, margin_b=170,
    )
    CC.write(fig, "e2_t7", "02_arm_zero_scatter", root=C.CHARTS_E2)


if __name__ == "__main__":
    main()
