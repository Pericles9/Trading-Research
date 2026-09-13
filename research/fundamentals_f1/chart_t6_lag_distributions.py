"""
Build F1, digest item 6: lag distribution per group -- not the mean, the distribution.
Companion to chart_t6_coverage.py; both are read by REPORT.md's digest.

Usage: .venv/Scripts/python.exe research/fundamentals_f1/chart_t6_lag_distributions.py
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from research.fundamentals_f1 import common as C  # noqa: E402

BLUE, ORANGE, AQUA, YELLOW, GREEN = "#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#008300"
INK, INK2, GRID, SURFACE = "#0b0b0b", "#52514e", "#e1e0d9", "#fcfcfb"
GROUPS = [("flg", "flg_lag_ns", BLUE), ("shs", "shs_lag_ns", ORANGE), ("fin", "fin_lag_ns", AQUA),
          ("si", "si_lag_ns", YELLOW), ("spl", None, GREEN)]

OUT_HTML = f"{C.CHARTS}/t6_lag_distributions.html"


def main():
    ef = pd.read_parquet(f"{C.NORMALIZED_ROOT}/event_fundamentals.parquet")
    ef["spl_lag_ns"] = ef["t0_ns"] - ef["spl_last_split_ns"]

    fig = make_subplots(rows=5, cols=1, vertical_spacing=0.05,
                         subplot_titles=[f"{g}_lag (days)" for g, _, _ in GROUPS])
    for i, (g, col, color) in enumerate(GROUPS, start=1):
        lag_col = col if col else "spl_lag_ns"
        lag_days = (ef[lag_col] / 1e9 / 86400.0).dropna()
        lag_days = lag_days[lag_days > 0]
        n = len(lag_days)
        log_lag = np.log10(lag_days.values) if n else np.array([])
        fig.add_trace(go.Histogram(x=log_lag, nbinsx=60, marker_color=color, name=g,
                                    showlegend=False), row=i, col=1)
        if n:
            tickvals = list(range(int(np.floor(log_lag.min())), int(np.ceil(log_lag.max())) + 1))
            fig.update_xaxes(tickvals=tickvals, ticktext=[f"{10**t:g}" for t in tickvals],
                              gridcolor=GRID, row=i, col=1)
        fig.update_yaxes(title="n", gridcolor=GRID, row=i, col=1)
        median = lag_days.median() if n else float("nan")
        p90 = lag_days.quantile(0.9) if n else float("nan")
        fig.layout.annotations[i - 1].update(
            text=f"{g}_lag (days, log10 x-axis) -- n={n:,}, median={median:.1f}d, p90={p90:.1f}d"
        )

    fig.update_layout(
        height=1700, title="F1: lag-to-t0 distribution per group (positive-lag rows only)",
        plot_bgcolor=SURFACE, paper_bgcolor=SURFACE, font=dict(color=INK),
        margin=dict(t=100, b=100),
        annotations=list(fig.layout.annotations) + [
            dict(text=f"n=20,951 in-scope events per group (before dropping unavailable/non-positive lag) "
                      f"· config {C.cfg_hash()} · digest item 6",
                 xref="paper", yref="paper", x=0, y=-0.035, showarrow=False,
                 font=dict(size=10, color=INK2), align="left")
        ],
    )
    os.makedirs(C.CHARTS, exist_ok=True)
    fig.write_html(OUT_HTML, include_plotlyjs=True)  # D14: no CDN, embed inline
    print(f"wrote {OUT_HTML}")


if __name__ == "__main__":
    main()
