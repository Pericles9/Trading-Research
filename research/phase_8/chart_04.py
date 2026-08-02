"""
Phase 8 chart 04 - markout heatmap (flagship).
Facet grid rows=horizon, cols=era. Each facet: x=anchor, y=participation
quintile, colour=median markout (diverging, 0-centred). Per-cell n printed.
Cells n<100 hatched (x overlay). 09:00 column: dashed hatched border + header
annotation (n=14,023, 1,740 excluded) legible without hover (A10.1a-iv).
"""
from __future__ import annotations

import json

import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from research.phase_8.chart_common import DIVERGING, INK, INK2, RED, caption, write, cfg_hash

SUMMARY = "results/phase_8/artifacts/t5_markout_summary.json"
ANCHORS = ["0900", "rth_open", "open+5", "open+15", "open+30", "open+60", "open+120", "t0_close"]
HORIZONS = ["anchor+30", "anchor+60", "t0_close", "t1_close", "t3_close"]
ERAS = [("era_2020_2021", "2020-21"), ("era_2022_2024", "2022-24")]
ZMAX = 0.25


def main():
    with open(SUMMARY) as f:
        S = json.load(f)
    cg = {(c["anchor"], c["horizon"], c["era"], c["participation_quintile"]): c for c in S["clock_grid"]}

    fig = make_subplots(
        rows=len(HORIZONS), cols=len(ERAS), shared_xaxes=True, shared_yaxes=True,
        horizontal_spacing=0.06, vertical_spacing=0.035,
        column_titles=[e[1] for e in ERAS],
        row_titles=[h for h in HORIZONS],
    )

    for ri, h in enumerate(HORIZONS, 1):
        for ci, (era, _) in enumerate(ERAS, 1):
            Z = np.full((5, len(ANCHORS)), np.nan)
            N = np.full((5, len(ANCHORS)), 0, dtype=int)
            for qi, q in enumerate([1, 2, 3, 4, 5]):
                for ai, a in enumerate(ANCHORS):
                    c = cg.get((a, h, era, q))
                    if c and c["median"] is not None:
                        Z[qi, ai] = c["median"]
                        N[qi, ai] = c["n"]
            fig.add_trace(go.Heatmap(
                z=Z, x=ANCHORS, y=[f"Q{q}" for q in [1, 2, 3, 4, 5]],
                zmid=0, zmin=-ZMAX, zmax=ZMAX, colorscale=DIVERGING,
                showscale=(ri == 1 and ci == len(ERAS)),
                colorbar=dict(title="median<br>markout", len=0.4, y=0.8) if (ri == 1 and ci == len(ERAS)) else None,
                hovertemplate="anchor %{x}<br>%{y}<br>median %{z:.3f}<extra></extra>",
                xgap=1, ygap=1,
            ), row=ri, col=ci)
            # per-cell n text + thin hatch
            ann_x, ann_y, ann_t, ann_c = [], [], [], []
            hx, hy = [], []
            for qi, q in enumerate([1, 2, 3, 4, 5]):
                for ai, a in enumerate(ANCHORS):
                    n = N[qi, ai]
                    thin = n < 100
                    ann_x.append(a); ann_y.append(f"Q{q}")
                    ann_t.append(str(n)); ann_c.append(RED if thin else INK)
                    if thin:
                        hx.append(a); hy.append(f"Q{q}")
            fig.add_trace(go.Scatter(
                x=ann_x, y=ann_y, mode="text", text=ann_t,
                textfont=dict(size=7, color="rgba(10,10,10,0.65)"), showlegend=False,
                hoverinfo="skip"), row=ri, col=ci)
            if hx:
                fig.add_trace(go.Scatter(
                    x=hx, y=hy, mode="markers",
                    marker=dict(symbol="x-thin", size=10, color="rgba(120,120,120,0.55)",
                                line=dict(width=1)),
                    showlegend=False, hoverinfo="skip"), row=ri, col=ci)

    # 09:00 column marker: dashed border rectangle in every facet (x index 0)
    for ri in range(1, len(HORIZONS) + 1):
        for ci in range(1, len(ERAS) + 1):
            xref = f"x{(ri-1)*len(ERAS)+ci}" if (ri-1)*len(ERAS)+ci > 1 else "x"
            yref = f"y{(ri-1)*len(ERAS)+ci}" if (ri-1)*len(ERAS)+ci > 1 else "y"
            fig.add_shape(type="rect", xref=xref, yref=yref,
                          x0=-0.5, x1=0.5, y0=-0.5, y1=4.5,
                          line=dict(color=INK, width=1.5, dash="dot"), fillcolor="rgba(0,0,0,0)")

    title = ("04 · Markout heatmap — anchor × participation quintile × horizon × era"
             "<br><span style='font-size:11px;color:#52514e'>09:00 column (dashed border): "
             "n=14,023 — 1,740 has_premarket_print=FALSE excluded, this column only</span>")

    cap = (f"sample: D1; clock grid, flagged union (56) excluded from cells · x=anchor y=participation quintile "
           f"colour=median signed log markout (zmid 0, ±{ZMAX} clip) · n<100 hatched (x) · config {cfg_hash()} · Phase 8")
    fig.update_layout(
        title=dict(text=title, x=0.01, y=0.985, font=dict(size=17, color=INK)),
        paper_bgcolor="white", plot_bgcolor="white", font=dict(color=INK, size=11),
        height=1520, width=1050, margin=dict(l=80, r=90, t=130, b=80),
        annotations=list(fig.layout.annotations) + [dict(
            text=cap, xref="paper", yref="paper", x=0.0, y=-0.05, showarrow=False,
            font=dict(size=9, color=INK2), xanchor="left")],
    )
    fig.update_xaxes(tickangle=-45, tickfont=dict(size=9))
    write(fig, "04_markout_heatmap")


if __name__ == "__main__":
    main()
