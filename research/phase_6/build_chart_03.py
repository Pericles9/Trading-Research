"""
Phase 6 T5 - Chart 03: minimum-window CDF. CDF of window length (minutes,
log x), one trace per X in {25,50,75}. Failure mode: mass at full session
length (no bursts) or at 1 minute for all X (artifact).
"""
import json

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from research.phase_6.chart_common import config_hash

MIN_WINDOW = "results/phase_6/artifacts/min_window_stats.parquet"
PHASE_6_CONFIG = "config/phase_6.json"
OUT_HTML = "results/phase_6/charts/03_min_window_cdf.html"


def ecdf(values: np.ndarray):
    x = np.sort(values)
    y = np.arange(1, len(x) + 1) / len(x)
    return x, y


def build():
    with open(PHASE_6_CONFIG) as f:
        cfg = json.load(f)
    thresholds = cfg["min_window_thresholds_pct"]

    df = pd.read_parquet(MIN_WINDOW)
    n_total = len(df)

    fig = go.Figure()
    colors = {25: "rgb(31,119,180)", 50: "rgb(255,127,14)", 75: "rgb(44,160,44)"}
    for x in thresholds:
        col = f"min_window_{x}pct_minutes"
        vals = df[col].dropna().to_numpy()
        vals = vals[vals > 0]
        xg, yg = ecdf(vals)
        fig.add_trace(go.Scatter(x=xg, y=yg, mode="lines", name=f"{x}% of volume (n={len(vals)})",
                                  line=dict(color=colors.get(x, "gray"), width=2)))

    fig.update_xaxes(title_text="window length (minutes, log scale)", type="log")
    fig.update_yaxes(title_text="cumulative fraction of events", range=[0, 1])
    fig.update_layout(
        title=f"Minimum contiguous window holding X% of T=0 session volume (n={n_total})",
        height=550, width=900,
        annotations=[dict(
            text=f"n={n_total} events | filters: D1 eligible (T1), T=0 bars only | config hash: {config_hash()}",
            xref="paper", yref="paper", x=0, y=-0.14, showarrow=False, font=dict(size=10, color="gray"))],
    )
    fig.write_html(OUT_HTML)
    print(f"wrote {OUT_HTML} (n={n_total})")
    return fig


if __name__ == "__main__":
    build()
