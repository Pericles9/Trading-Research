"""
Phase 8 chart 13 (A10.2c-v) - detection-anchored markout heatmap.
Facet rows=horizon, cols=era; x=latency offset, y=detection time-of-day bin,
colour=median markout (diverging, 0-centred). Per-cell n. n<100 hatched.
Latency=0 column marked a physical upper bound (dashed border).
"""
from __future__ import annotations

import json

import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from research.phase_8.chart_common import DIVERGING, INK, INK2, RED, cfg_hash, write

SUMMARY = "results/phase_8/artifacts/a102_detection_markout_summary.json"
LAT = [0, 1, 5, 15, 30]
DET_BINS = ["premarket", "0930-1000", "1000-1100", "1100-1300", "after_1300"]
BINLAB = ["pre", "0930-10", "10-11", "11-13", ">13"]
HORIZ = ["det+5", "det+15", "det+30", "det+60", "t0_close", "t1_close", "t3_close"]
ERAS = [("era_2020_2021", "2020-21"), ("era_2022_2024", "2022-24")]
ZMAX = 0.08


def main():
    with open(SUMMARY) as f:
        S = json.load(f)
    g = {(c["horizon"], c["era"], c["latency"], c["det_bin"]): c for c in S["grid"]}

    fig = make_subplots(rows=len(HORIZ), cols=len(ERAS), shared_xaxes=True, shared_yaxes=True,
                        horizontal_spacing=0.07, vertical_spacing=0.018,
                        column_titles=[e[1] for e in ERAS], row_titles=HORIZ)
    for ri, h in enumerate(HORIZ, 1):
        for ci, (era, _) in enumerate(ERAS, 1):
            Z = np.full((len(DET_BINS), len(LAT)), np.nan)
            N = np.zeros((len(DET_BINS), len(LAT)), dtype=int)
            for yi, b in enumerate(DET_BINS):
                for xi, L in enumerate(LAT):
                    c = g.get((h, era, L, b))
                    if c and c["median"] is not None:
                        Z[yi, xi] = c["median"]; N[yi, xi] = c["n"]
            fig.add_trace(go.Heatmap(
                z=Z, x=[str(L) for L in LAT], y=BINLAB, zmid=0, zmin=-ZMAX, zmax=ZMAX,
                colorscale=DIVERGING, showscale=(ri == 1 and ci == len(ERAS)),
                colorbar=dict(title="median<br>markout", len=0.35, y=0.85) if (ri == 1 and ci == len(ERAS)) else None,
                xgap=1, ygap=1, hovertemplate="lat %{x}<br>%{y}<br>median %{z:.3f}<extra></extra>",
            ), row=ri, col=ci)
            tx, ty, tt = [], [], []
            hx, hy = [], []
            for yi, b in enumerate(DET_BINS):
                for xi, L in enumerate(LAT):
                    tx.append(str(L)); ty.append(BINLAB[yi]); tt.append(str(N[yi, xi]))
                    if N[yi, xi] < 100:
                        hx.append(str(L)); hy.append(BINLAB[yi])
            fig.add_trace(go.Scatter(x=tx, y=ty, mode="text", text=tt,
                                     textfont=dict(size=6, color="rgba(10,10,10,0.6)"),
                                     showlegend=False, hoverinfo="skip"), row=ri, col=ci)
            if hx:
                fig.add_trace(go.Scatter(x=hx, y=hy, mode="markers",
                                         marker=dict(symbol="x-thin", size=8, color="rgba(120,120,120,0.5)", line=dict(width=1)),
                                         showlegend=False, hoverinfo="skip"), row=ri, col=ci)

    title = ("13 · Detection-anchored markout heatmap — latency × detection time × horizon × era"
             "<br><span style='font-size:11px;color:#52514e'>x=latency (min after +30% crossing); "
             "latency 0 (dashed) = physical upper bound; detection universe n=15,369</span>")
    cap = (f"sample: detection universe; flagged union excluded · colour=median signed log markout "
           f"(zmid 0, ±{ZMAX} clip) · n<100 hatched · config {cfg_hash()} · Phase 8")
    fig.update_layout(title=dict(text=title, x=0.01, y=0.992, font=dict(size=16, color=INK)),
                      paper_bgcolor="white", plot_bgcolor="white", font=dict(color=INK, size=10),
                      height=2100, width=920, margin=dict(l=70, r=90, t=120, b=70),
                      annotations=list(fig.layout.annotations) + [dict(
                          text=cap, xref="paper", yref="paper", x=0.0, y=-0.035, showarrow=False,
                          font=dict(size=9, color=INK2), xanchor="left")])
    fig.update_xaxes(title_text="", tickfont=dict(size=8), type="category")
    fig.update_yaxes(type="category", categoryorder="array", categoryarray=BINLAB, tickfont=dict(size=8))
    write(fig, "13_detection_markout_heatmap")


if __name__ == "__main__":
    main()
