"""
Phase 6 T5 - Chart 04: opportunity decay. x=minutes since open, y=median +
quartile band of realized-move fraction; horizontal 0.5 rule annotated
with crossing minute; both with/without-minute-0 variants overlaid.
Failure mode: median never reaches 0.5, or crosses at minute 1 in the
with-minute-0 variant only (opening-print artifact).
"""
import json

import pandas as pd
import plotly.graph_objects as go

from research.phase_6.chart_common import config_hash
from research.phase_6 import measurements as M

POOLED = "results/phase_6/artifacts/pooled_decay.parquet"
POOLED_SENS = "results/phase_6/artifacts/pooled_decay_sens.parquet"
T4_SUMMARY = "results/phase_6/artifacts/t4_measurements_summary.json"
OUT_HTML = "results/phase_6/charts/04_opportunity_decay.html"


def _band_traces(fig, df, color, name, dash=None):
    fig.add_trace(go.Scatter(x=df["minute_index"], y=df["q75"], mode="lines", line=dict(width=0),
                              showlegend=False, hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=df["minute_index"], y=df["q25"], mode="lines", line=dict(width=0),
                              fill="tonexty", fillcolor=color.replace("rgb", "rgba").replace(")", ",0.15)"),
                              showlegend=False, hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=df["minute_index"], y=df["median"], mode="lines",
                              line=dict(color=color, width=2, dash=dash), name=name,
                              customdata=df["n"], hovertemplate="minute=%{x}<br>median=%{y:.3f}<br>n=%{customdata}"))


def build():
    with open(T4_SUMMARY) as f:
        summary = json.load(f)
    crossing = summary["headline"]["pooled_median_minutes_to_50pct_move_with_minute0"]
    crossing_sens = summary["headline"]["pooled_median_minutes_to_50pct_move_excl_minute0"]

    pooled = pd.read_parquet(POOLED)
    pooled_sens = pd.read_parquet(POOLED_SENS)

    fig = go.Figure()
    _band_traces(fig, pooled, "rgb(214,39,40)", f"with minute 0 (n up to {pooled['n'].max()}, crosses 0.5 at minute {crossing:.0f})")
    _band_traces(fig, pooled_sens, "rgb(23,140,140)", f"excl minute 0 (n up to {pooled_sens['n'].max()}, crosses 0.5 at minute {crossing_sens:.0f})", dash="dash")

    fig.add_hline(y=0.5, line=dict(color="gray", dash="dot", width=1))
    fig.add_vline(x=crossing, line=dict(color="rgb(214,39,40)", dash="dot", width=1))
    fig.add_vline(x=crossing_sens, line=dict(color="rgb(23,140,140)", dash="dot", width=1))

    fig.update_xaxes(title_text="minutes since open")
    fig.update_yaxes(title_text="realized-move fraction |cum_move(t)| / |open->close move|")
    fig.update_layout(
        title="Opportunity decay - pooled median + IQR, with vs. without opening print",
        height=600, width=1100,
        annotations=[dict(
            text=(f"n={summary['n_events']} events | median±IQR per minute, n(t) varies with session length (half-days) | "
                  f"filters: D1 eligible (T1), T=0 | config hash: {config_hash()}"),
            xref="paper", yref="paper", x=0, y=-0.12, showarrow=False, font=dict(size=10, color="gray"))],
    )
    fig.write_html(OUT_HTML)
    print(f"wrote {OUT_HTML} (crossing with={crossing}, excl={crossing_sens})")
    return fig


if __name__ == "__main__":
    build()
