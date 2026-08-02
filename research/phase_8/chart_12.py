"""
Phase 8 chart 12 (A10.2b) - contamination test.
Violin + strip of t0_close -> t1_close signed log markout by pre-open
participation quintile (pq_rth_open), era faceted, zero-line. Encoding matched
to chart 05 so the two read side by side. Visible range [-1,1]; beyond disclosed.
"""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from research.phase_8.chart_common import INK, INK2, rgba, caption, write, base_layout

PARQUET = "results/phase_8/artifacts/a102_contamination.parquet"
QRAMP = {1: "#c6dbef", 2: "#9ecae1", 3: "#6baed6", 4: "#3182bd", 5: "#08519c"}
ERAS = [("era_2020_2021", "2020-21"), ("era_2022_2024", "2022-24")]
LO, HI = -1.0, 1.0


def main():
    d = pd.read_parquet(PARQUET)
    d = d[d.horizon_name == "t1_close"]

    fig = make_subplots(rows=1, cols=2, shared_yaxes=True, subplot_titles=[e[1] for e in ERAS])
    n_beyond = 0
    for ci, (era, _) in enumerate(ERAS, 1):
        for q in [1, 2, 3, 4, 5]:
            s = d[(d.era == era) & (d.pq_rth_open == q)]["markout"]
            n_beyond += int(((s < LO) | (s > HI)).sum())
            vis = s[(s >= LO) & (s <= HI)]
            fig.add_trace(go.Violin(
                x=[f"Q{q}"] * len(vis), y=vis, line_color=QRAMP[q], fillcolor=rgba(QRAMP[q], 0.4),
                points="all", pointpos=0, jitter=0.35, marker=dict(size=2, color=rgba(QRAMP[q], 0.28)),
                meanline_visible=True, width=0.85, showlegend=False, spanmode="hard",
            ), row=1, col=ci)
            m = s.median()
            fig.add_annotation(row=1, col=ci, x=f"Q{q}", y=0.90, text=f"{m:+.3f}<br>n={len(s)}",
                               showarrow=False, font=dict(size=8, color=INK), bgcolor="rgba(255,255,255,0.65)")
        fig.add_hline(y=0, line=dict(color=INK2, width=1, dash="dot"), row=1, col=ci)

    fig.update_yaxes(title_text="t0_close → t1_close markout (log)", range=[LO, HI], row=1, col=1)
    fig.add_annotation(text="pre-open participation quintile (pq_rth_open, low→high)",
                       xref="paper", yref="paper", x=0.5, y=-0.09, showarrow=False,
                       font=dict(size=12, color=INK), xanchor="center")
    cap = caption(
        sample=f"D1 detection-independent; t0_close→t1_close, flagged union excluded; n={len(d):,}",
        filters=(f"bucket = pre-open quintile (headline gradient's bucket); visible [{LO},{HI}]; "
                 f"{n_beyond} beyond axis (retained); NO T0 move in this return - the clean read"),
    )
    base_layout(fig, "12 · Contamination test — headline gradient with no T0 hindsight left", cap, height=600)
    write(fig, "12_contamination_test")


if __name__ == "__main__":
    main()
