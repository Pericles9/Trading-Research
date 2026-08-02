"""
Phase 8 chart 11 (A10.2a-iii) - the runway measurement.
Panel A: ECDF of minutes from det_anchor to day_high_ext time.
Panel B: ECDF of log distance between the det anchor price and day_high_ext.
Era as colour. This is the tradeable opportunity-decay curve.
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from research.phase_8.chart_common import BLUE, ORANGE, INK2, caption, write, base_layout

ANCH = "results/phase_8/artifacts/a102_detection_anchors.parquet"
META = "results/phase_8/artifacts/a102_detection_summary.json"
ERAS = [("era_2020_2021", "2020-21", BLUE), ("era_2022_2024", "2022-24", ORANGE)]


def ecdf(s):
    xs = np.sort(s); return xs, np.arange(1, len(xs) + 1) / len(xs)


def main():
    ev = pd.read_parquet(ANCH)
    with open(META) as f:
        meta = json.load(f)
    d = ev[~ev.det_undefined].copy()

    fig = make_subplots(rows=1, cols=2, subplot_titles=(
        "A · minutes from detection to day-high", "B · log distance detection→day-high"))
    for era, elab, color in ERAS:
        de = d[d.era == era]
        xs, ys = ecdf(de["runway_minutes"].dropna().to_numpy())
        fig.add_trace(go.Scatter(x=xs, y=ys, mode="lines", line=dict(color=color, width=2),
                                 name=f"{elab} (n={len(xs):,})", legendgroup=elab), row=1, col=1)
        xs2, ys2 = ecdf(de["runway_log_distance"].dropna().to_numpy())
        fig.add_trace(go.Scatter(x=xs2, y=ys2, mode="lines", line=dict(color=color, width=2),
                                 name=elab, legendgroup=elab, showlegend=False), row=1, col=2)

    rm, rl = meta["runway_minutes"], meta["runway_log_distance"]
    fig.update_xaxes(title_text="minutes (log)", type="log", row=1, col=1)
    fig.update_xaxes(title_text="log distance to day-high", row=1, col=2)
    fig.update_yaxes(title_text="cumulative fraction", range=[0, 1.02], row=1, col=1)
    fig.update_yaxes(range=[0, 1.02], row=1, col=2)
    for c in (1, 2):
        fig.add_hline(y=0.5, line=dict(color=INK2, width=1, dash="dot"), row=1, col=c)
    cap = caption(
        sample=f"detection universe n={meta['detection_universe_n']:,} (det_undefined 394 excluded)",
        filters=(f"runway minutes median {rm['median']:.0f} (IQR {rm['q25']:.0f}-{rm['q75']:.0f}); "
                 f"log distance median {rl['median']:.3f} (IQR {rl['q25']:.3f}-{rl['q75']:.3f}); "
                 f"crossing on bar high, 1.30x"),
    )
    base_layout(fig, "11 · Runway: time and move remaining after detection", cap, height=560)
    fig.update_layout(legend=dict(orientation="h", yanchor="bottom", y=-0.28, x=0.3))
    write(fig, "11_detection_to_high_runway")


if __name__ == "__main__":
    main()
