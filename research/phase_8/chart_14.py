"""
Phase 8 chart 14 (A10.2c-v) - distributions behind the flagship detection cell.
Violin + strip of det+5 -> t0_close signed log markout by detection time-of-day
bin, era faceted, zero-line. Per-bin n. Visible range [-1,1]; beyond disclosed.
"""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from research.phase_8.chart_common import INK, INK2, rgba, caption, write, base_layout

GRID = "results/phase_8/artifacts/a102_detection_markout_grid.parquet"
BINS = ["premarket", "0930-1000", "1000-1100", "1100-1300", "after_1300"]
BINLAB = ["pre", "0930-10", "10-11", "11-13", ">13"]
BINRAMP = {"premarket": "#c6dbef", "0930-1000": "#9ecae1", "1000-1100": "#6baed6",
           "1100-1300": "#3182bd", "after_1300": "#08519c"}
ERAS = [("era_2020_2021", "2020-21"), ("era_2022_2024", "2022-24")]
LO, HI = -1.0, 1.0


def main():
    g = pd.read_parquet(GRID)
    f = g[(g.latency == 5) & (g.horizon == "t0_close") & g.markout.notna()].copy()

    fig = make_subplots(rows=1, cols=2, shared_yaxes=True, subplot_titles=[e[1] for e in ERAS])
    n_beyond = 0
    for ci, (era, _) in enumerate(ERAS, 1):
        for bi, b in enumerate(BINS):
            s = f[(f.era == era) & (f.det_bin == b)]["markout"]
            n_beyond += int(((s < LO) | (s > HI)).sum())
            vis = s[(s >= LO) & (s <= HI)]
            fig.add_trace(go.Violin(
                x=[BINLAB[bi]] * len(vis), y=vis, line_color=BINRAMP[b], fillcolor=rgba(BINRAMP[b], 0.4),
                points="all", pointpos=0, jitter=0.35, marker=dict(size=2, color=rgba(BINRAMP[b], 0.28)),
                meanline_visible=True, width=0.85, showlegend=False, spanmode="hard",
            ), row=1, col=ci)
            m = s.median()
            fig.add_annotation(row=1, col=ci, x=BINLAB[bi], y=0.90, text=f"{m:+.3f}<br>n={len(s)}",
                               showarrow=False, font=dict(size=8, color=INK), bgcolor="rgba(255,255,255,0.65)")
        fig.add_hline(y=0, line=dict(color=INK2, width=1, dash="dot"), row=1, col=ci)

    fig.update_yaxes(title_text="det+5 → t0_close markout (log)", range=[LO, HI], row=1, col=1)
    fig.add_annotation(text="detection time-of-day bin (premarket → after 13:00)", xref="paper", yref="paper",
                       x=0.5, y=-0.09, showarrow=False, font=dict(size=12, color=INK), xanchor="center")
    cap = caption(
        sample=f"detection universe, flagged union excluded; det+5→t0_close; n={len(f):,}",
        filters=f"det+5 = 5 min after +30% crossing (tradeable); visible [{LO},{HI}]; {n_beyond} beyond axis (retained)",
    )
    base_layout(fig, "14 · Detection markout distributions — det+5 → t0_close by detection time", cap, height=600)
    write(fig, "14_detection_markout_distributions")


if __name__ == "__main__":
    main()
