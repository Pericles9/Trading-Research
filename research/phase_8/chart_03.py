"""
Phase 8 chart 03 - T=0 print-count distribution (row-cap detector).
ECDF of per-event T=0 print count on a log x-axis; rug marks at flagged
round numbers (50k/100k/200k); ARBB annotated.
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from research.phase_8.chart_common import BLUE, RED, ORANGE, INK, INK2, caption, write, base_layout

COUNTS = "results/phase_8/artifacts/t2_row_cap_counts.parquet"
META = "results/phase_8/artifacts/t2_row_cap_scan.json"
ROUND_NUMBERS = [50_000, 100_000, 200_000]


def main():
    df = pd.read_parquet(COUNTS)
    with open(META) as f:
        meta = json.load(f)
    c = df["t0_print_count"].astype("int64").to_numpy()
    c = c[c > 0]
    xs = np.sort(c)
    ys = np.arange(1, len(xs) + 1) / len(xs)

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=xs, y=ys, mode="lines", line=dict(color=BLUE, width=2),
                             name=f"ECDF (n={len(xs):,})"))

    # rug at flagged round numbers
    for v in ROUND_NUMBERS:
        hit = meta["round_number_exact_hits"][str(v)]
        fig.add_vline(x=v, line=dict(color=RED, width=1, dash="dot"))
        fig.add_annotation(x=np.log10(v), y=0.03, text=f"{v:,}<br>({hit} evt)", showarrow=False,
                           font=dict(size=9, color=RED), textangle=-90, xanchor="left")

    # ARBB - single legend entry; label only the two exact round-number hits to avoid clutter
    arbb = meta.get("arbb")
    if isinstance(arbb, list) and arbb:
        axs = [a["t0_print_count"] for a in arbb]
        ays = [float((xs <= xv).mean()) for xv in axs]
        atext = [(f"ARBB {xv:,}" if xv in (50_000, 100_000) else "") for xv in axs]
        fig.add_trace(go.Scatter(
            x=axs, y=ays, mode="markers+text",
            marker=dict(color=ORANGE, size=11, symbol="diamond", line=dict(color=INK, width=1)),
            text=atext, textposition="middle right", textfont=dict(size=10, color=INK),
            name=f"ARBB (n={len(arbb)} events)", showlegend=True))

    fig.update_xaxes(title_text="T=0 total print count (log)", type="log")
    fig.update_yaxes(title_text="cumulative fraction of D1 events", range=[0, 1.02])
    d = meta["distribution"]
    cap = caption(
        sample=f"D1 n={d['n']:,} (T0 print count > 0)",
        filters=(f"median {d['median']:,.0f}, IQR [{d['q25']:,.0f}, {d['q75']:,.0f}], "
                 f"max {d['max']:,}; exact round-number hits 50k/100k/200k = "
                 f"{meta['round_number_exact_hits']['50000']}/"
                 f"{meta['round_number_exact_hits']['100000']}/"
                 f"{meta['round_number_exact_hits']['200000']}"),
    )
    base_layout(fig, "03 · T=0 print-count distribution (silent row-cap detector)", cap, height=560)
    write(fig, "03_t0_print_count_distribution")


if __name__ == "__main__":
    main()
