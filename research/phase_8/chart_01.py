"""
Phase 8 chart 01 - realized(09:30) decomposition.
Top panel: share-of-realized(09:30) violins, one per component (share_ok events).
Bottom panel: absolute log-move violins, one per component (all defined events).
Outliers disclosed: the share ratio blows up as the numerator -> 0; the visible
share range is [-1, 2] and the count of events beyond it is annotated per
component (data is not deleted - full stats in t1_decomposition.json).
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from research.phase_8.chart_common import BLUE, ORANGE, AQUA, INK, INK2, rgba, caption, write, base_layout

PARQUET = "results/phase_8/artifacts/t1_decomposition.parquet"
COMPS = [("seg_t1_post", "T-1 post 16:00-20:00", BLUE),
         ("seg_overnight", "overnight jump", ORANGE),
         ("seg_t0_pre", "T0 premarket ->09:30", AQUA)]
SHARE_LO, SHARE_HI = -1.0, 2.0


def main():
    df = pd.read_parquet(PARQUET)
    defined = ~df["decomp_undefined"]
    share_ok = defined & ~df["share_undefined"]
    n_defined = int(defined.sum())
    n_share = int(share_ok.sum())
    n_decomp_undef = int(df["decomp_undefined"].sum())
    n_share_undef = int(df["share_undefined"].sum())

    fig = make_subplots(
        rows=2, cols=1, row_heights=[0.5, 0.5], vertical_spacing=0.13,
        subplot_titles=("share of realized(09:30) — visible range [-1, 2]",
                        "absolute log move (log return vs T-1 RTH close)"),
    )

    beyond_notes = []
    for i, (col, label, color) in enumerate(COMPS):
        s = df.loc[share_ok, f"share_{col}"]
        inrange = s[(s >= SHARE_LO) & (s <= SHARE_HI)]
        n_beyond = int((~((s >= SHARE_LO) & (s <= SHARE_HI))).sum())
        beyond_notes.append(f"{label}: {n_beyond} beyond axis")
        fig.add_trace(go.Violin(
            y=inrange, name=label, legendgroup=label, line_color=color,
            fillcolor=rgba(color, 0.35), points="all", pointpos=0, jitter=0.35,
            marker=dict(size=2.5, color=rgba(color, 0.30)), meanline_visible=True,
            width=0.85, showlegend=False, spanmode="hard",
        ), row=1, col=1)
        m = df.loc[share_ok, f"share_{col}"].median()
        fig.add_annotation(row=1, col=1, x=label, y=1.68,
                           text=f"med {m:.2f}<br>n={n_share}", showarrow=False,
                           font=dict(size=10, color=INK),
                           bgcolor="rgba(255,255,255,0.7)")

    for col, label, color in COMPS:
        a = df.loc[defined, col]
        fig.add_trace(go.Violin(
            y=a, name=label, legendgroup=label, line_color=color,
            fillcolor=rgba(color, 0.35), points="all", pointpos=0, jitter=0.35,
            marker=dict(size=2.5, color=rgba(color, 0.30)), meanline_visible=True,
            width=0.85, showlegend=False,
        ), row=2, col=1)
        m = a.median()
        fig.add_annotation(row=2, col=1, x=label, y=a.max(),
                           text=f"med {m:.3f}<br>n={n_defined}", showarrow=False,
                           font=dict(size=10, color=INK), yshift=8)

    fig.add_hline(y=0, line=dict(color=INK2, width=1, dash="dot"), row=1, col=1)
    fig.add_hline(y=0, line=dict(color=INK2, width=1, dash="dot"), row=2, col=1)
    fig.update_yaxes(range=[SHARE_LO, SHARE_HI], title_text="share", row=1, col=1)
    fig.update_yaxes(title_text="log move", row=2, col=1)

    cap = caption(
        sample=f"D1 n=15,763; defined n={n_defined}; share_ok n={n_share}",
        filters=(f"decomp_undefined={n_decomp_undef} (no T-1 ext bars/anchor); "
                 f"share_undefined={n_share_undef} (numerator<=0, in bottom panel only); "
                 + "; ".join(beyond_notes)),
    )
    base_layout(fig, "01 · Realized-at-open decomposition: T-1 post / overnight / T0 premarket", cap, height=760)
    write(fig, "01_realized_open_decomposition")


if __name__ == "__main__":
    main()
