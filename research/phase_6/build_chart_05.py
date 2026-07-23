"""
Phase 6 T5 - Chart 05: per-event opportunity-decay overlay. Top decile,
bottom decile, seeded random 30 (seed 42), color by group, low alpha,
against the pooled median+IQR band (light gray backdrop) so the failure
mode - one group systematically off the pooled band - is actually
checkable. Uses the with-minute-0 variant (chart 04's primary variant).
"""
import json

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from research.phase_6.chart_common import EVENT_KEYS, seeded_overlay_groups, config_hash

PER_MINUTE = "results/phase_6/artifacts/opportunity_decay_per_minute.parquet"
POOLED = "results/phase_6/artifacts/pooled_decay.parquet"
EVENT_INDEX = "results/phase_6/artifacts/event_index.parquet"
PHASE_6_CONFIG = "config/phase_6.json"
OUT_HTML = "results/phase_6/charts/05_per_event_overlay.html"

GROUP_COLORS = {"top_decile": "rgb(214,39,40)", "bottom_decile": "rgb(31,119,180)", "seeded_random_30": "rgb(127,127,127)"}


def build():
    with open(PHASE_6_CONFIG) as f:
        cfg = json.load(f)
    seed = cfg["chart_overlay"]["overlay_seed"]
    n_random = cfg["chart_overlay"]["overlay_random_n"]

    events = pd.read_parquet(EVENT_INDEX)
    per_minute = pd.read_parquet(PER_MINUTE)
    pooled = pd.read_parquet(POOLED)

    groups = seeded_overlay_groups(events, seed, n_random)

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=pooled["minute_index"], y=pooled["q75"], mode="lines", line=dict(width=0),
                              showlegend=False, hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=pooled["minute_index"], y=pooled["q25"], mode="lines", line=dict(width=0),
                              fill="tonexty", fillcolor="rgba(0,0,0,0.08)", name="pooled IQR (all eligible)", hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=pooled["minute_index"], y=pooled["median"], mode="lines",
                              line=dict(color="black", width=2, dash="dot"), name="pooled median (all eligible)"))

    for grp_name, grp_events in groups.items():
        color = GROUP_COLORS.get(grp_name, "rgb(140,86,75)")
        merged = per_minute.merge(grp_events[EVENT_KEYS], on=EVENT_KEYS)
        first = True
        for keys, sub in merged.groupby(EVENT_KEYS):
            sub = sub.sort_values("minute_index")
            fig.add_trace(go.Scatter(
                x=sub["minute_index"], y=sub["realized_move_fraction"], mode="lines",
                line=dict(color=color, width=1), opacity=0.35,
                name=f"{grp_name} (n={len(grp_events)})" if first else None, showlegend=first,
                hovertemplate=f"{keys[0]} {str(keys[1])[:10]}<br>minute=%{{x}}<br>frac=%{{y:.3f}}",
            ))
            first = False

    fig.add_hline(y=0.5, line=dict(color="gray", dash="dot", width=1))
    fig.update_xaxes(title_text="minutes since open")
    max_frac = per_minute["realized_move_fraction"].max()
    q99 = per_minute["realized_move_fraction"].quantile(0.99)
    # Default viewport zoomed to where the pooled band + most events live; not a clip -
    # every point is still in the figure (Evidence Standard: outliers shown, never
    # clipped). Autoscale / scroll-zoom reveals the full extent up to max_frac.
    fig.update_yaxes(title_text="realized-move fraction", range=[0, 3])
    n_total = len(events)
    fig.update_layout(
        title="Per-event opportunity decay: top/bottom momentum_pct decile + seeded random 30 vs. pooled band",
        height=600, width=1100,
        annotations=[dict(
            text=(f"groups: top_decile n={len(groups['top_decile'])}, bottom_decile n={len(groups['bottom_decile'])}, "
                  f"seeded_random_{n_random} n={len(groups[f'seeded_random_{n_random}'])} (seed={seed}) | pooled n={n_total} | "
                  f"y-axis zoomed to [0,3] by default (not clipped - population max={max_frac:.0f}, "
                  f"99th pct={q99:.1f}; use Autoscale/scroll-zoom to see full tail) | config hash: {config_hash()}"),
            xref="paper", yref="paper", x=0, y=-0.12, showarrow=False, font=dict(size=10, color="gray"))],
    )
    fig.write_html(OUT_HTML)
    print(f"wrote {OUT_HTML}")
    return fig


if __name__ == "__main__":
    build()
