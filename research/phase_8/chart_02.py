"""
Phase 8 chart 02 - extended-day decay curve split by flag_eth_dominant_t0.
x = minutes since 04:00 ET; y = median realized fraction; one line per flag
group with IQR bands. Vertical rules at RTH open (330) and normal RTH close (720).
"""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go

from research.phase_8.chart_common import BLUE, ORANGE, INK, INK2, rgba, caption, write, base_layout

CURVES = "results/phase_8/artifacts/t2_eth_split_curves.parquet"
import json

GROUPS = [(False, "not ETH-dominant", BLUE), (True, "ETH-dominant (T0>50% outside RTH)", ORANGE)]


def main():
    c = pd.read_parquet(CURVES)
    with open("results/phase_8/artifacts/t2_eth_split.json") as f:
        meta = json.load(f)
    ne = meta["decay_population_events"]

    fig = go.Figure()
    for eth_val, label, color in GROUPS:
        g = c[c.eth == eth_val].sort_values("minute_index")
        n_ev = ne["eth_true"] if eth_val else ne["eth_false"]
        # IQR band
        fig.add_trace(go.Scatter(
            x=list(g.minute_index) + list(g.minute_index[::-1]),
            y=list(g.q75) + list(g.q25[::-1]),
            fill="toself", fillcolor=rgba(color, 0.15), line=dict(width=0),
            hoverinfo="skip", showlegend=False,
        ))
        fig.add_trace(go.Scatter(
            x=g.minute_index, y=g.med, mode="lines", line=dict(color=color, width=2),
            name=f"{label} (n={n_ev:,})",
        ))

    fig.add_hline(y=0.5, line=dict(color=INK2, width=1, dash="dot"),
                  annotation_text="0.5", annotation_position="right")
    for mi, lab in [(330, "RTH open"), (720, "RTH close")]:
        fig.add_vline(x=mi, line=dict(color=INK2, width=1, dash="dash"))
        fig.add_annotation(x=mi, y=1.02, yref="paper", text=lab, showarrow=False,
                           font=dict(size=10, color=INK2))

    xt = meta["median_crossing_0p5_minute_since_0400"]
    fig.update_xaxes(title_text="minutes since 04:00 ET", range=[0, 959])
    fig.update_yaxes(title_text="median realized fraction (tick anchor)", range=[0, 1.05])
    cap = caption(
        sample=f"primary decay population; ETH-dominant n={ne['eth_true']}, other n={ne['eth_false']}",
        filters=(f"realized fraction defined (has_t_minus_1_rth, denom>0); "
                 f"0.5 crossing: ETH-dom {xt['eth_true']}, other {xt['eth_false']} min "
                 f"(pooled-all 6b ref 516); IQR bands shaded"),
    )
    base_layout(fig, "02 · Extended-day decay curve by ETH-dominant flag", cap, height=580)
    fig.update_layout(legend=dict(orientation="h", yanchor="bottom", y=-0.28, x=0))
    write(fig, "02_decay_by_eth_flag")


if __name__ == "__main__":
    main()
