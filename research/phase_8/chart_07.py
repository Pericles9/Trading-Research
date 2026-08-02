"""
Phase 8 chart 07 - rung attrition.
Panel A: fraction of D1 reaching each rung (bar, n labelled).
Panel B: ECDF of crossing time-of-day per rung (ET hour).
Rungs are ordered magnitude -> a single-hue sequential ramp (light=1x, dark=10x).
Every rung reported; none selected/recommended/preferable (escalation row 10).
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from research.phase_8.chart_common import INK, INK2, caption, write, base_layout

T4 = "results/phase_8/artifacts/t4_anchors.parquet"
SUMMARY = "results/phase_8/artifacts/t4_anchors_summary.json"
RUNGS = ["rung_1x", "rung_2x", "rung_5x", "rung_10x"]
RAMP = {"rung_1x": "#9ecae1", "rung_2x": "#4292c6", "rung_5x": "#2171b5", "rung_10x": "#08519c"}
N_D1 = 15763


def main():
    with open(SUMMARY) as f:
        summ = json.load(f)
    attr = summ["rung_attrition"]

    grid = pd.read_parquet(T4)
    rung = grid[grid.anchor_kind == "rung"][["ticker", "event_date_canonical", "mp",
                                             "anchor_name", "crossing_minute"]].drop_duplicates()

    fig = make_subplots(rows=1, cols=2, column_widths=[0.36, 0.64],
                        subplot_titles=("fraction of D1 reaching each rung",
                                        "ECDF of crossing time-of-day (ET)"))

    # Panel A: bars
    fracs = [attr[r]["frac_of_d1"] for r in RUNGS]
    ns = [attr[r]["n_reaching"] for r in RUNGS]
    fig.add_trace(go.Bar(
        x=[r.replace("rung_", "") for r in RUNGS], y=fracs,
        marker_color=[RAMP[r] for r in RUNGS], showlegend=False,
        text=[f"{f:.1%}<br>n={n:,}" for f, n in zip(fracs, ns)], textposition="outside",
        textfont=dict(size=10, color=INK),
    ), row=1, col=1)
    fig.update_yaxes(title_text="fraction of D1", range=[0, 1.05], row=1, col=1)
    fig.update_xaxes(title_text="rung (x b_session)", row=1, col=1)

    # Panel B: ECDF per rung (ET decimal hour)
    for r in RUNGS:
        cm = rung[rung.anchor_name == r]["crossing_minute"].dropna().to_numpy()
        if len(cm) == 0:
            continue
        et_hour = (240 + cm) / 60.0
        xs = np.sort(et_hour)
        ys = np.arange(1, len(xs) + 1) / len(xs)
        fig.add_trace(go.Scatter(
            x=xs, y=ys, mode="lines", line=dict(color=RAMP[r], width=2),
            name=f"{r.replace('rung_','')} (n={len(xs):,})",
        ), row=1, col=2)
    for h, lab in [(9.5, "RTH open"), (16, "RTH close")]:
        fig.add_vline(x=h, line=dict(color=INK2, width=1, dash="dash"), row=1, col=2)
    fig.update_xaxes(title_text="crossing time-of-day (ET hour)", range=[4, 20],
                     dtick=2, row=1, col=2)
    fig.update_yaxes(title_text="cumulative fraction reaching by time", range=[0, 1.02], row=1, col=2)

    cap = caption(
        sample=f"D1 n={N_D1:,}; rung = first T0 minute cum vol >= mult x b_session",
        filters=("reaching: 1x 94.7% / 2x 84.1% / 5x 64.2% / 10x 47.5%; "
                 "ECDF conditional on reaching; every rung reported, none preferred"),
    )
    base_layout(fig, "07 · Rung attrition and crossing time-of-day", cap, height=560)
    fig.update_layout(legend=dict(x=0.44, y=0.99, yanchor="top", xanchor="left",
                                  bgcolor="rgba(255,255,255,0.65)", font=dict(size=10)))
    write(fig, "07_rung_attrition")


if __name__ == "__main__":
    main()
