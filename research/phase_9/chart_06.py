"""
Chart 06 - does entry latency matter when the exit is fixed?

x = latency, y = markout from det+latency to t0_close, violin + strip.

CHART CONTRACT DEVIATION, deliberate and recorded in REPORT.md: the contract
specifies "n-attrition line on secondary axis". A dual y-scale is the one
encoding the project's visualization standard forbids outright, so attrition
ships as a linked LOWER PANEL sharing the x-axis - same information, same
chart file, no second y-scale on the same plot area.

Failure appearance: violins identical across latency -> latency genuinely does
not matter and Phase 8's claim stands.

Read alongside chart 05: on this fixed-exit grid the HOLD shortens as latency
grows (median 552 min at det+0 down to 523 min at det+30), so latency and
holding period are still entangled here, in the opposite direction from Phase
8 §19. Chart 05 is the grid that separates them.
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from research.phase_9 import chart_common as K
from research.phase_9 import common as C


def main():
    cfg = C.load_cfg()
    lats = cfg["latencies"]
    j = json.load(open(f"{C.ART}/t4_axis_summary.json"))
    G = pd.read_parquet(f"{C.ART}/t4_axis_grid.parquet")
    E = G[(G.grid == "fixed_exit") & G.markout.notna()]

    rng, outside = K.zoom_range(E["markout"].values)

    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.76, 0.24],
                        vertical_spacing=0.055,
                        subplot_titles=["", "n attrition across the latency axis (T4c)"])

    for i, lat in enumerate(lats):
        s = E.loc[E.latency == lat, "markout"].dropna()
        lab = f"det+{lat}"
        fig.add_trace(go.Violin(
            y=s.values, x=[lab] * len(s), name=lab,
            line=dict(color=K.CAT5[i], width=1.5),
            fillcolor=K.rgba(K.CAT5[i], 0.22),
            points=False, showlegend=False, spanmode="hard", hoverinfo="skip"), row=1, col=1)
        pts, _ = K.subsample(s.values, cap=1200)
        fig.add_trace(go.Scatter(
            y=pts, x=np.full(len(pts), lab), mode="markers",
            marker=dict(color=K.rgba(K.INK2, 0.16), size=3), showlegend=False,
            hovertemplate=f"{lab}<br>markout %{{y:.4f}}<extra></extra>"), row=1, col=1)
        med = float(s.median())
        fig.add_trace(go.Scatter(
            y=[med], x=[lab], mode="markers",
            marker=dict(color=K.INK, size=13, symbol="line-ew-open", line=dict(width=3, color=K.INK)),
            name="median", showlegend=(i == 0),
            hovertemplate=f"{lab} median {med:+.5f}<extra></extra>"), row=1, col=1)
        c = j["fixed_exit"][f"lat{lat}"]
        # pinned inside the bottom of the panel; a top placement collides with
        # the two-line subtitle
        fig.add_annotation(x=lab, y=0.015, yref="y domain", xref="x",
                           text=(f"n={c['n']:,}<br>med {c['median']:+.4f}<br>"
                                 f"hold {c['median_effective_hold_minutes']:.0f}m"),
                           showarrow=False, font=dict(size=8.5, color=K.INK2), yanchor="bottom")

    att = j["attrition"]["fixed_exit"]
    xs = [f"det+{l}" for l in lats]
    lost = [att[f"lat{l}"]["n_lost_vs_lat0"] for l in lats]
    fig.add_trace(go.Bar(
        x=xs, y=lost, marker_color=K.rgba(K.ORANGE, 0.75), showlegend=False,
        text=[f"{v:,}" for v in lost], textposition="outside", textfont=dict(size=9),
        hovertemplate="%{x}<br>events lost vs det+0: %{y:,}<extra></extra>"), row=2, col=1)

    fig.add_hline(y=0, line=dict(color=K.INK2, width=1, dash="dot"), row=1, col=1)

    n0 = att[f"lat{lats[0]}"]["n_defined"]
    title = ("06 · Fixed-exit markout by entry latency (exit = t0_close)<br>"
             "<sub>det+0 is a physical impossibility, carried only as the ladder's upper bound<br>"
             "the hold SHORTENS as latency grows, so latency is not isolated here — see chart 05</sub>")
    cap = K.caption(
        f"detection universe n=15,369, eras pooled",
        "entry defined (det+latency ≤ last T0 print) and t0_close > 0",
        f"n, median and median effective hold printed inside each violin · strip sub-sampled to 1,200/latency<br>"
        f"y zoomed to the 0.5–99.5 pct band; {outside:,} points lie outside, remain in the figure<br>"
        f"and autorange on double-click — nothing is clipped<br>"
        f"lower panel: events lost relative to det+0 (n={n0:,}); total attrition across the<br>"
        f"whole ladder is {max(lost):,} events ({max(lost)/n0:.2%})<br>"
        "CONTRACT DEVIATION: attrition is a linked lower panel, not a secondary<br>"
        "y-axis (dual y-scales are forbidden by the project chart standard)")
    fig.update_yaxes(title_text="markout  log(p_t0_close / p_entry)", range=rng, row=1, col=1)
    fig.update_yaxes(title_text="events lost<br>vs det+0", row=2, col=1)
    fig.update_xaxes(title_text="entry latency (minutes after detection)", row=2, col=1)
    K.base_layout(fig, title, cap, height=830, cap_y=-0.30, margin_b=300, margin_r=60, width=1050)
    K.legend_inside(fig, x=0.012, y=0.985)
    for a in fig.layout.annotations[:2]:
        a.font.size = 11
    K.write(fig, "06_latency_fixed_exit")


if __name__ == "__main__":
    main()
