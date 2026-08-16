"""Chart 03 - does the quoted spread compress on the event day, and in cents or
only in basis points?

Two measures (basis points, cents) x two segments (premarket, RTH). x = day
offset (-3, -1, 0), y = time-weighted QUOTED spread on a log axis, violin +
strip, one point per event.

QUOTED spread, not effective: ask - bid needs no trade and no adopted alignment
offset, so it is legal before the T4 gate (escalation row 10 bars effective
spread only).

Failure appearance from the contract: violins fully overlapping across offsets
- no event-day spread effect, and the compression claim is unsupported at
session grain.
"""
from __future__ import annotations

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

import chart_common as K

A = "results/phase_11/artifacts"
OFFSETS = [-3, -1, 0]
OFF_COLOR = {-3: K.AQUA, -1: K.ORANGE, 0: K.BLUE}
PANELS = [("tw_spread_bp", "premarket", "basis points · premarket"),
          ("tw_spread_bp", "rth", "basis points · RTH"),
          ("tw_spread_cents", "premarket", "cents · premarket"),
          ("tw_spread_cents", "rth", "cents · RTH")]


def main() -> None:
    d = pd.read_parquet(f"{A}/t2e_quoted_spread.parquet")
    d["tw_spread_cents"] = d.tw_spread_dollars * 100.0

    fig = make_subplots(rows=2, cols=2, subplot_titles=[p[2] for p in PANELS],
                        horizontal_spacing=0.10, vertical_spacing=0.13)

    seen = set()
    rng = np.random.default_rng(42)
    for i, (measure, seg, _) in enumerate(PANELS):
        r, c = divmod(i, 2)
        for off in OFFSETS:
            s = d[(d.segment == seg) & (d.day_offset == off)][measure].dropna()
            s = s[s > 0]
            if not len(s):
                continue
            fig.add_trace(go.Violin(
                x=np.full(len(s), off), y=s, name=f"T{off:+d}" if off else "T=0",
                legendgroup=str(off), showlegend=off not in seen,
                line=dict(color=OFF_COLOR[off], width=2),
                fillcolor=K.rgba(OFF_COLOR[off], 0.20),
                points=False, width=0.75, spanmode="hard",
                hoverinfo="skip",
            ), row=r + 1, col=c + 1)
            fig.add_trace(go.Scatter(
                x=off + rng.uniform(-0.13, 0.13, len(s)), y=s, mode="markers",
                showlegend=False, legendgroup=str(off),
                marker=dict(color=K.rgba(OFF_COLOR[off], 0.62), size=6,
                            line=dict(width=1, color="white")),
                hovertemplate=f"T{off:+d}<br>%{{y:,.2f}}<extra></extra>",
            ), row=r + 1, col=c + 1)
            med = float(s.median())
            fig.add_annotation(x=off, y=np.log10(med), xref=f"x{i+1}", yref=f"y{i+1}",
                               text=f"<b>{med:,.1f}</b><br>n={len(s)}", showarrow=False,
                               font=dict(size=9, color=K.INK), yshift=0,
                               bgcolor="rgba(255,255,255,0.80)")
            seen.add(off)

    for i, (measure, seg, _) in enumerate(PANELS):
        r, c = divmod(i, 2)
        fig.update_xaxes(tickmode="array", tickvals=OFFSETS,
                         ticktext=["T−3", "T−1", "T=0"], range=[-3.7, 0.7],
                         title_text="session offset" if r == 1 else None,
                         row=r + 1, col=c + 1)
        fig.update_yaxes(type="log", row=r + 1, col=c + 1,
                         title_text=("time-weighted quoted spread (bp, log)" if r == 0
                                     else "time-weighted quoted spread (cents, log)")
                         if c == 0 else None)

    cap = K.caption(
        sample="dev v4 PRIMARY cohort, 50 events. One point per event per session "
               "offset; n printed at each median.<br>        Post segment measured and "
               "in the artifact, not drawn - the Chart Contract specifies "
               "premarket/RTH facets.",
        filters="dev_cohort='primary'. Rows in state_hard_unusable are excluded from the "
                "spread only<br>         (no midpoint exists on them); no other quote "
                "state is excluded. Time weighting is<br>         prevailing-quote "
                "duration clipped at each segment boundary.",
        extra="QUOTED spread (ask − bid), not effective spread. Effective spread requires a "
              "trade and<br>       an adopted alignment offset and is barred before the T4 "
              "gate (escalation row 10).",
    )
    K.base_layout(fig, "03 · Quoted spread, event day vs. baseline — in cents, or only in "
                       "basis points?",
                  cap, height=880, width=1120, cap_y=-0.135, margin_b=200)
    fig.update_layout(violinmode="overlay",
                      legend=dict(orientation="h", y=1.075, x=0.0, xanchor="left",
                                  font=dict(size=11), bgcolor="rgba(255,255,255,0.86)",
                                  bordercolor=K.GRID, borderwidth=1))
    for a in fig.layout.annotations[:4]:
        a.font.size = 12.5
        a.font.color = K.INK
    K.write(fig, "03_spread_event_vs_baseline")


if __name__ == "__main__":
    main()
