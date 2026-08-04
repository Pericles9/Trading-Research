"""
Chart 04 - do premarket-detected and RTH-detected events retrace differently?

Facet per horizon; x = detection segment, y = retrace_excursion, violin +
strip; ticker-block bootstrap 95% CI on each median overlaid.

Failure appearance: violins fully overlap across segments at every horizon ->
no segment effect.

HORIZON CEILING: T+3.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from research.phase_9 import chart_common as K
from research.phase_9 import common as C
from research.phase_9.t5_clustered import block_bootstrap_median

HZ = ["t0_close", "t1_close", "t2_close", "t3_close"]
SEGS = ["premarket", "rth", "post"]


def main():
    cfg = C.load_cfg()
    reps, seed = cfg["bootstrap_reps"], cfg["bootstrap_seed"]
    R = pd.read_parquet(f"{C.ART}/t3_retracement.parquet")

    fig = make_subplots(rows=1, cols=4, shared_yaxes=True,
                        subplot_titles=HZ, horizontal_spacing=0.02)

    for ci, h in enumerate(HZ, start=1):
        d = R[R.horizon == h]
        for si, sg in enumerate(SEGS):
            s = d[d.det_segment == sg]
            v = s["retrace_excursion"].dropna()
            if not len(v):
                continue
            fig.add_trace(go.Violin(
                y=v.values, x=[sg] * len(v), name=sg,
                line=dict(color=K.CAT5[si], width=1.4),
                fillcolor=K.rgba(K.CAT5[si], 0.22),
                points=False, showlegend=False, spanmode="hard",
                hoverinfo="skip"), row=1, col=ci)
            pts, _ = K.subsample(v.values, cap=500)
            fig.add_trace(go.Scatter(
                y=pts, x=np.full(len(pts), sg), mode="markers",
                marker=dict(color=K.rgba(K.INK2, 0.18), size=3), showlegend=False,
                hovertemplate=f"{sg}<br>retrace %{{y:.3f}}<extra></extra>"), row=1, col=ci)

            bb = block_bootstrap_median(s["retrace_excursion"].values, s["ticker"].values,
                                        reps, seed)
            if bb["point"] is not None:
                fig.add_trace(go.Scatter(
                    y=[bb["lo"], bb["hi"]], x=[sg, sg], mode="lines",
                    line=dict(color=K.INK, width=4), showlegend=False,
                    hovertemplate=f"{sg} block CI [{bb['lo']:.3f}, {bb['hi']:.3f}]<extra></extra>"),
                    row=1, col=ci)
                fig.add_trace(go.Scatter(
                    y=[bb["point"]], x=[sg], mode="markers",
                    marker=dict(color="white", size=9, symbol="circle",
                                line=dict(width=2.5, color=K.INK)),
                    name="median + ticker-block 95% CI",
                    showlegend=(ci == 1 and si == 0),
                    hovertemplate=(f"{sg} median {bb['point']:.4f}<br>"
                                   f"block CI [{bb['lo']:.4f}, {bb['hi']:.4f}]<br>"
                                   f"n={bb['n']:,} · {bb['n_tickers']:,} tickers<extra></extra>")),
                    row=1, col=ci)
            fig.add_annotation(x=sg, y=0.012, yref=f"y{ci if ci>1 else ''} domain",
                               xref=f"x{ci if ci>1 else ''}",
                               text=f"n={len(v):,}", showarrow=False,
                               font=dict(size=8.5, color=K.INK2), yanchor="bottom")

    for yv in (0.5, 1.0):
        fig.add_hline(y=yv, line=dict(color=K.INK2, width=1, dash="dot"))

    title = ("04 · Excursion retracement by detection segment and horizon<br>"
             "<sub>violin + strip, ticker-block bootstrap 95% CI on each median · T+3 horizon ceiling</sub>")
    cap = K.caption(
        "detection universe n=15,369",
        "H − A > 0; horizon session present in v2",
        f"ticker-block bootstrap: {reps:,} reps, seed {seed}, percentile CI<br>"
        "n printed inside each violin · strip sub-sampled to 500/cell<br>"
        "y zoomed to [−1.5, 2.5]; tails remain in the figure (double-click to autorange)<br>"
        "dotted lines at 0.5 and 1.0 (back to the T−1 RTH close)")
    fig.update_yaxes(title_text="retrace_excursion", range=[-1.5, 2.5], row=1, col=1)
    for ci in range(1, 5):
        fig.update_yaxes(range=[-1.5, 2.5], row=1, col=ci)
    fig.add_annotation(x=0.5, y=-0.085, xref="paper", yref="paper",
                       text="detection segment", showarrow=False, font=dict(size=12, color=K.INK))
    K.base_layout(fig, title, cap, height=780, cap_y=-0.20, margin_b=290, margin_r=60)
    K.legend_inside(fig, x=0.012, y=0.985)
    for a in fig.layout.annotations[:4]:
        a.font.size = 11
    K.write(fig, "04_retracement_by_segment")


if __name__ == "__main__":
    main()
