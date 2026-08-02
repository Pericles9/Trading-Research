"""
Phase 8 chart 05 - flagship markout distributions.
Violin + strip of rth_open -> t0_close signed log markout per participation
quintile, faceted by era, zero-line. Visible y range [-1, 1]; count beyond
disclosed in caption (outliers not deleted - full grid retained).
"""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from research.phase_8.chart_common import INK, INK2, rgba, caption, write, base_layout

GRID = "results/phase_8/artifacts/t5_markout_grid.parquet"
QRAMP = {1: "#c6dbef", 2: "#9ecae1", 3: "#6baed6", 4: "#3182bd", 5: "#08519c"}
ERAS = [("era_2020_2021", "2020-21"), ("era_2022_2024", "2022-24")]
LO, HI = -1.0, 1.0


def main():
    g = pd.read_parquet(GRID)
    f = g[(g.anchor_name == "rth_open") & (g.horizon_name == "t0_close")
          & g.markout.notna() & (~g.in_flagged_union) & g.pq.notna()].copy()

    fig = make_subplots(rows=1, cols=2, shared_yaxes=True,
                        subplot_titles=[e[1] for e in ERAS])
    n_beyond = 0
    for ci, (era, _) in enumerate(ERAS, 1):
        for q in [1, 2, 3, 4, 5]:
            s = f[(f.era == era) & (f.pq == q)]["markout"]
            n_beyond += int(((s < LO) | (s > HI)).sum())
            vis = s[(s >= LO) & (s <= HI)]
            fig.add_trace(go.Violin(
                x=[f"Q{q}"] * len(vis), y=vis, line_color=QRAMP[q],
                fillcolor=rgba(QRAMP[q], 0.4), points="all", pointpos=0, jitter=0.35,
                marker=dict(size=2, color=rgba(QRAMP[q], 0.28)), meanline_visible=True,
                width=0.85, showlegend=False, spanmode="hard",
            ), row=1, col=ci)
            m = s.median()
            fig.add_annotation(row=1, col=ci, x=f"Q{q}", y=0.90,
                               text=f"{m:+.3f}<br>n={len(s)}", showarrow=False,
                               font=dict(size=8, color=INK),
                               bgcolor="rgba(255,255,255,0.65)")
        fig.add_hline(y=0, line=dict(color=INK2, width=1, dash="dot"), row=1, col=ci)

    fig.update_yaxes(title_text="rth_open → t0_close markout (log)", range=[LO, HI], row=1, col=1)
    fig.update_xaxes(title_text="participation quintile (low→high)")
    cap = caption(
        sample=f"D1 flagship rth_open→t0_close, flagged union excluded; n={len(f):,}",
        filters=f"visible range [{LO},{HI}]; {n_beyond} points beyond axis (retained, not deleted); zero-line dotted",
    )
    base_layout(fig, "05 · Flagship markout distributions by participation quintile", cap, height=600)
    write(fig, "05_markout_distributions_flagship")


if __name__ == "__main__":
    main()
