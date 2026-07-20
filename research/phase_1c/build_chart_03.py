"""
Phase 1c T8 - chart 03: volume reconciliation.
"""
import json

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

BLUE = "#2a78d6"
ORANGE = "#eb6834"
GRID = "#e1e0d9"
INK = "#0b0b0b"
INK_SEC = "#52514e"

df = pd.read_parquet("results/phase_1c/artifacts/volume_reconciliation.parquet")
with open("results/phase_1c/artifacts/t8_volume_reconciliation_summary.json") as f:
    s = json.load(f)

fig = make_subplots(
    rows=1, cols=2, column_widths=[0.68, 0.32],
    subplot_titles=("Fetched vs. scan event-day volume", "Ratio distribution (fetched / scan)"),
    horizontal_spacing=0.10,
)

fig.add_trace(
    go.Scattergl(
        x=df["scan_volume"], y=df["fetched_volume"], mode="markers",
        marker=dict(color=BLUE, size=6, opacity=0.6),
        name=f"events (n={len(df):,})",
        hovertext=df["ticker"] + " " + df["event_date_canonical"].astype(str),
    ),
    row=1, col=1,
)
axis_min = min(df["scan_volume"].min(), df["fetched_volume"].min()) * 0.5
axis_max = max(df["scan_volume"].max(), df["fetched_volume"].max()) * 2
ref = np.logspace(np.log10(axis_min), np.log10(axis_max), 50)
fig.add_trace(
    go.Scatter(x=ref, y=ref, mode="lines", line=dict(color=INK, width=1.5, dash="dash"), name="y=x"),
    row=1, col=1,
)

fig.add_trace(
    go.Histogram(
        x=np.log10(df["ratio"]), marker_color=ORANGE, opacity=0.85,
        nbinsx=30, name="log10(ratio)",
    ),
    row=1, col=2,
)
fig.add_vline(x=0, line=dict(color=INK, width=1.5, dash="dash"), row=1, col=2)

fig.update_xaxes(type="log", title="scan event_volume (log)", gridcolor=GRID, row=1, col=1)
fig.update_yaxes(type="log", title="fetched trade volume (log)", gridcolor=GRID, row=1, col=1)
fig.update_xaxes(title="log10(fetched / scan)", gridcolor=GRID, row=1, col=2)
fig.update_yaxes(title="n events", gridcolor=GRID, row=1, col=2)

fig.update_layout(
    paper_bgcolor="#fcfcfb", plot_bgcolor="#fcfcfb",
    font=dict(family="system-ui, -apple-system, 'Segoe UI', sans-serif", color=INK, size=12),
    height=560,
    title=dict(
        text=(f"Does fetched event-day volume agree with the scan's event_volume? | "
              f"n={s['n_events_reconciled']:,} | median ratio={s['ratio_stats']['median']:.3f}"),
        x=0.02, xanchor="left", font=dict(size=14),
    ),
    showlegend=False,
    margin=dict(t=90, b=110, l=70, r=30),
    annotations=[
        dict(
            text=(f"n={s['n_events_reconciled']:,} healed event-day trades reconciled against momentum_events."
                  f"event_volume. Right-skewed: median={s['ratio_stats']['median']:.2f}x, mean={s['ratio_stats']['mean']:.1f}x, "
                  f"p75={s['ratio_stats']['p75']:.1f}x, max={s['ratio_stats']['max']:.1f}x - a handful of events where "
                  f"fetched tick volume vastly exceeds the scan's recorded figure. Scan volume basis (venues, condition "
                  f"codes, session boundaries) unknown - measurement only, gated on the median (threshold [0.5, 2.0], "
                  f"not triggered). source: results/phase_1c/artifacts/t8_volume_reconciliation_summary.json"),
            xref="paper", yref="paper", x=0.02, y=-0.24, showarrow=False,
            font=dict(size=10.5, color=INK_SEC), xanchor="left",
        )
    ],
)

fig.write_html("results/phase_1c/charts/03_volume_reconciliation.html", include_plotlyjs="inline")
print("chart 03 written")
