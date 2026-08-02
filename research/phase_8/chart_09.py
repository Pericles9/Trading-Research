"""
Phase 8 chart 09 (A10.1a-iii/A10.1a-iv) - rth_open markout split by
has_premarket_print. Violin + strip of rth_open -> t0_close signed log
markout, split by has_premarket_print, faceted by era, zero-line marked.
Per-group n above each violin. Description only. Visible range [-1,1];
beyond disclosed.
"""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from research.phase_8.chart_common import BLUE, ORANGE, INK, INK2, rgba, caption, write, base_layout

GRID = "results/phase_8/artifacts/t5_markout_grid.parquet"
ERAS = [("era_2020_2021", "2020-21"), ("era_2022_2024", "2022-24")]
GROUPS = [(True, "has PM print", BLUE), (False, "no PM print (1,740)", ORANGE)]
LO, HI = -1.0, 1.0


def main():
    g = pd.read_parquet(GRID)
    f = g[(g.anchor_name == "rth_open") & (g.horizon_name == "t0_close") & g.markout.notna()].copy()

    fig = make_subplots(rows=1, cols=2, shared_yaxes=True, subplot_titles=[e[1] for e in ERAS])
    n_beyond = 0
    seen = set()
    for ci, (era, _) in enumerate(ERAS, 1):
        for val, lab, color in GROUPS:
            s = f[(f.era == era) & (f.has_premarket_print == val)]["markout"]
            n_beyond += int(((s < LO) | (s > HI)).sum())
            vis = s[(s >= LO) & (s <= HI)]
            show = lab not in seen
            seen.add(lab)
            fig.add_trace(go.Violin(
                x=[lab] * len(vis), y=vis, line_color=color, fillcolor=rgba(color, 0.35),
                points="all", pointpos=0, jitter=0.35, marker=dict(size=2, color=rgba(color, 0.25)),
                meanline_visible=True, width=0.8, showlegend=show, legendgroup=lab, name=lab,
                spanmode="hard",
            ), row=1, col=ci)
            m = s.median()
            fig.add_annotation(row=1, col=ci, x=lab, y=0.90, text=f"med {m:+.3f}<br>n={len(s):,}",
                               showarrow=False, font=dict(size=9, color=INK),
                               bgcolor="rgba(255,255,255,0.65)")
        fig.add_hline(y=0, line=dict(color=INK2, width=1, dash="dot"), row=1, col=ci)

    fig.update_yaxes(title_text="rth_open → t0_close markout (log)", range=[LO, HI], row=1, col=1)
    cap = caption(
        sample=f"D1 rth_open→t0_close by has_premarket_print; n={len(f):,}",
        filters=f"visible range [{LO},{HI}]; {n_beyond} beyond axis (retained); description only (A10.1a-iii)",
    )
    base_layout(fig, "09 · RTH-open markout by has_premarket_print", cap, height=600)
    fig.update_layout(legend=dict(orientation="h", yanchor="bottom", y=-0.22, x=0.2))
    write(fig, "09_rth_open_by_premarket_print")


if __name__ == "__main__":
    main()
