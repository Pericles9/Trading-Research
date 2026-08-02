"""
Phase 8 chart 06 - rung markouts by crossing time-of-day.
Facet per rung; x=crossing time-of-day bin, y=rung->t0_close signed log
markout, violin + strip, era as colour. Per-bin n above each violin.
Participation is constant by construction at a rung (not a bucket). Every
rung reported; none preferred (row 10). Visible y range [-1,1]; beyond
disclosed.
"""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from research.phase_8.chart_common import BLUE, ORANGE, INK, INK2, rgba, caption, write, base_layout

GRID = "results/phase_8/artifacts/t5_markout_grid.parquet"
RUNGS = ["rung_1x", "rung_2x", "rung_5x", "rung_10x"]
BINS = ["premarket (04:00-09:30)", "open-10:30", "10:30-12:00", "12:00-14:00", "14:00-16:00", "post (16:00-20:00)"]
BINLAB = ["pre", "open-10:30", "10:30-12", "12-14", "14-16", "post"]
ERAS = [("era_2020_2021", "2020-21", BLUE), ("era_2022_2024", "2022-24", ORANGE)]
LO, HI = -1.0, 1.0


def main():
    g = pd.read_parquet(GRID)
    r = g[(g.anchor_kind == "rung") & (g.horizon_name == "t0_close")
          & g.markout.notna() & (~g.in_flagged_union)].copy()

    fig = make_subplots(rows=2, cols=2, shared_yaxes=True, shared_xaxes=True,
                        subplot_titles=[x.replace("rung_", "rung ") for x in RUNGS],
                        vertical_spacing=0.11, horizontal_spacing=0.05)
    n_beyond = 0
    seen = set()
    binmap = dict(zip(BINS, BINLAB))
    for i, rung in enumerate(RUNGS):
        row, col = i // 2 + 1, i % 2 + 1
        for ei, (era, elab, color) in enumerate(ERAS):
            sub = r[(r.anchor_name == rung) & (r.era == era) & r.crossing_bin.isin(BINS)].copy()
            n_beyond += int(((sub.markout < LO) | (sub.markout > HI)).sum())
            vis = sub[(sub.markout >= LO) & (sub.markout <= HI)]
            show = elab not in seen
            seen.add(elab)
            fig.add_trace(go.Violin(
                x=vis["crossing_bin"].map(binmap), y=vis["markout"], line_color=color,
                fillcolor=rgba(color, 0.3), points=False, meanline_visible=True,
                width=0.7, showlegend=show, legendgroup=elab, name=elab, spanmode="hard",
            ), row=row, col=col)
            # per-era n label per bin, stacked at two y levels, era-coloured
            ylab = 0.97 if ei == 0 else 0.86
            for b in BINS:
                nb = int((sub.crossing_bin == b).sum())
                if nb:
                    fig.add_annotation(row=row, col=col, x=binmap[b], y=ylab, text=f"{nb}",
                                       showarrow=False, font=dict(size=7, color=color))
        fig.add_hline(y=0, line=dict(color=INK2, width=1, dash="dot"), row=row, col=col)
    fig.update_layout(violinmode="group")

    fig.update_yaxes(title_text="rung → t0_close markout (log)", range=[LO, HI])
    fig.update_xaxes(tickangle=-30, tickfont=dict(size=8),
                     categoryorder="array", categoryarray=BINLAB)
    cap = caption(
        sample=f"D1 rung→t0_close, flagged union excluded; n={len(r):,}",
        filters=f"violins split by era; visible range [{LO},{HI}]; {n_beyond} beyond axis (retained); every rung reported, none preferred",
    )
    base_layout(fig, "06 · Rung markouts by crossing time-of-day", cap, height=760)
    fig.update_layout(legend=dict(orientation="h", yanchor="bottom", y=-0.11, x=0.4))
    write(fig, "06_rung_markouts_by_crossing_time")


if __name__ == "__main__":
    main()
