"""Chart 08 - does impact per unit signed volume rise or fall with participation?

x = participation quintile, y = delta-mid per unit signed volume; violin + strip;
facet by impact window and detection segment; unclassifiable share annotated per
cell. Distributions, never a fitted slope (T8b). No burst/quiet split (D11/D13).
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
from common import CONFIG

A = "results/phase_11/artifacts"
SEGS = ["premarket", "rth", "post"]
MIN_N = CONFIG["universe"]["min_cell_n"]


def main() -> None:
    cells = pd.read_parquet(f"{A}/t8_impact.parquet")
    d = pd.read_parquet(f"{A}/t8_impact_cells.parquet")
    wins = sorted(cells.window_minutes.unique())

    fig = make_subplots(rows=len(wins), cols=3,
                        subplot_titles=[f"{w}-min window · {s}" for w in wins for s in SEGS],
                        horizontal_spacing=0.07, vertical_spacing=0.10)
    rng = np.random.default_rng(42)
    for ri, w in enumerate(wins):
        col = f"impact_{w}m"
        for ci, seg in enumerate(SEGS):
            sub = d[d.det_segment == seg]
            for pq in [1, 2, 3, 4, 5]:
                s = sub[sub.pq_rth_open == pq][col].replace([np.inf, -np.inf], np.nan).dropna()
                if len(s) < 5:
                    continue
                lo, hi = s.quantile(.01), s.quantile(.99)
                thin = len(s) < MIN_N
                fig.add_trace(go.Violin(
                    x=np.full(len(s), pq), y=s.clip(lo, hi), showlegend=False,
                    line=dict(color=K.INK2 if thin else K.BLUE, width=1.3),
                    fillcolor=K.rgba(K.RED if thin else K.BLUE, .12 if thin else .20),
                    points=False, width=.8, spanmode="hard", hoverinfo="skip",
                ), row=ri + 1, col=ci + 1)
                v, _ = K.subsample(s.clip(lo, hi).values, 300)
                fig.add_trace(go.Scatter(
                    x=pq + rng.uniform(-.13, .13, len(v)), y=v, mode="markers",
                    showlegend=False, marker=dict(color=K.rgba(K.BLUE, .35), size=3),
                    hovertemplate=f"pq {pq}<br>%{{y:.3g}}<extra></extra>",
                ), row=ri + 1, col=ci + 1)
                uc = cells[(cells.window_minutes == w) & (cells.det_segment == seg)
                           & (cells.pq_rth_open == pq)]
                ann = f"n={len(s):,}"
                if len(uc):
                    ann += f"<br>uncl {uc.unclassifiable_share.iloc[0]:.1%}"
                if thin:
                    ann += "<br><b>HATCHED</b>"
                fig.add_annotation(x=pq, y=hi, xref=f"x{ri*3+ci+1}", yref=f"y{ri*3+ci+1}",
                                   text=ann, showarrow=False, font=dict(size=7, color=K.INK),
                                   bgcolor="rgba(255,255,255,.75)")
            fig.add_hline(y=0, line=dict(color=K.INK2, width=1, dash="dash"),
                          row=ri + 1, col=ci + 1)
            fig.update_xaxes(tickmode="array", tickvals=[1, 2, 3, 4, 5],
                             title_text="participation quintile"
                             if ri == len(wins) - 1 else None, row=ri + 1, col=ci + 1)
            fig.update_yaxes(title_text="Δmid ÷ signed volume" if ci == 0 else None,
                             row=ri + 1, col=ci + 1)

    cap = K.caption(
        sample="detection universe with quotes_ingested, minute-grain cells from "
               "event_quote_metrics_v1. n and unclassifiable share printed per cell; "
               "cells n<100 hatched.<br>        Violins are drawn on the 1st-99th "
               "percentile range for legibility; NO point is removed from the underlying "
               "distribution or from the artifact.",
        filters="Lee & Ready (1991) quote rule at δ = 0 on the sip basis (D16), tick-rule "
                "fallback. THE 5-SECOND RULE IS NOT APPLIED - on nanosecond data the<br>"
                "         contemporaneous quote signs best and T3 put the at-or-inside "
                "peak in a plateau containing δ = 0. Unclassifiable trades are never dropped.",
        extra="Distributions only - no regression and no fitted impact exponent (T8b). "
              "No burst/quiet split (D11, D13).<br>       The configured 1 s and 5 s "
              "windows both resolve to the 1-minute cache grain; sub-minute impact is "
              "not measurable here and no sub-second window is permitted (row 23).",
    )
    K.base_layout(fig, "08 · Impact per unit signed volume, by participation quintile",
                  cap, height=330 * len(wins) + 140, width=1240, cap_y=-0.09, margin_b=215)
    for a in fig.layout.annotations[:len(wins) * 3]:
        a.font.size = 11
        a.font.color = K.INK
    K.write(fig, "08_impact_by_participation")


if __name__ == "__main__":
    main()
