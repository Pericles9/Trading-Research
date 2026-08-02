"""
Phase 8 chart 08 - survivorship census (diagnostic).
Panel A: missing T+1/T+2/T+3 counts by era (grouped bars, n labelled).
Panel B: ECDF of (ticker last-seen - event date) in XNYS sessions, per era.
Description only - no external base rate, no causal or bias claim.
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from research.phase_8.chart_common import BLUE, ORANGE, INK, INK2, caption, write, base_layout

PARQUET = "results/phase_8/artifacts/t6_survivorship.parquet"
META = "results/phase_8/artifacts/t6_survivorship.json"
ERAS = [("era_2020_2021", "2020-21", BLUE), ("era_2022_2024", "2022-24", ORANGE)]


def main():
    with open(META) as f:
        m = json.load(f)
    df = pd.read_parquet(PARQUET)

    fig = make_subplots(rows=1, cols=2, column_widths=[0.42, 0.58], horizontal_spacing=0.12,
                        subplot_titles=("missing T+1/T+2/T+3 (count)",
                                        "ECDF: event → ticker last-seen"))

    horizons = ["missing_t1", "missing_t2", "missing_t3"]
    hlab = ["T+1", "T+2", "T+3"]
    for era, elab, color in ERAS:
        e = m["by_era"][era]
        fig.add_trace(go.Bar(
            x=hlab, y=[e[h] for h in horizons], name=f"{elab} (n={e['n']:,})",
            marker_color=color, text=[e[h] for h in horizons], textposition="outside",
            textfont=dict(size=10, color=INK), legendgroup=elab,
        ), row=1, col=1)

    for era, elab, color in ERAS:
        s = df[df.era == era]["sessions_to_lastseen"].dropna().to_numpy()
        xs = np.sort(s)
        ys = np.arange(1, len(xs) + 1) / len(xs)
        fig.add_trace(go.Scatter(
            x=xs, y=ys, mode="lines", line=dict(color=color, width=2),
            name=f"{elab} (n={len(xs):,})", legendgroup=elab, showlegend=False,
        ), row=1, col=2)

    fig.update_yaxes(title_text="missing count", row=1, col=1)
    fig.update_xaxes(title_text="horizon", row=1, col=1)
    fig.update_xaxes(title_text="sessions to ticker last-seen", row=1, col=2)
    fig.update_yaxes(title_text="cumulative fraction", range=[0, 1.02], row=1, col=2)

    ov = m["overall"]
    cap = caption(
        sample=f"D1 n={ov['n']:,}",
        filters=(f"missing T+1 {ov['missing_t1']} ({ov['missing_t1_rate']:.2%}) / "
                 f"T+2 {ov['missing_t2']} / T+3 {ov['missing_t3']}; last-seen median "
                 f"{m['sessions_to_lastseen']['median']:.0f} sessions. Event-windowed archive: "
                 f"last-seen is a lower bound, not a delisting date. Diagnostic only."),
    )
    base_layout(fig, "08 · Survivorship census (diagnostic, no accommodation)", cap, height=560)
    fig.update_layout(barmode="group", legend=dict(orientation="h", yanchor="bottom", y=-0.32, x=0.1))
    write(fig, "08_survivorship_census")


if __name__ == "__main__":
    main()
