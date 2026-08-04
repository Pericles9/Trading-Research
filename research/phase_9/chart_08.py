"""
Chart 08 - how much does ticker clustering cost us?

Left: events-per-ticker histogram (log y).
Centre + right: forest plots of every headline median with the ticker-block
bootstrap 95% CI and the naive event-level CI side by side.

Failure appearance: block CIs indistinguishable from naive CIs -> clustering
costs nothing.

The forest is SPLIT BY UNIT rather than pooled onto one axis. Markout medians
live near -0.03 log and retracement medians near +1.4 ratio; on a shared axis
the markout intervals collapse to invisible specks and the panel cannot be
read. Two panels, each with one axis in its own units, is the correct form -
and it keeps the "one axis" rule intact rather than reaching for a dual scale.
"""
from __future__ import annotations

import json

import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from research.phase_9 import chart_common as K
from research.phase_9 import common as C


def main():
    j = json.load(open(f"{C.ART}/t5_clustered_inference.json"))
    dist = j["events_per_ticker"]
    stats = j["headline_medians"]
    bs = j["bootstrap"]

    markouts = [s for s in stats if not s["name"].startswith("retrace")]
    retrace = [s for s in stats if s["name"].startswith("retrace")]

    fig = make_subplots(
        rows=1, cols=3, column_widths=[0.235, 0.435, 0.33],
        horizontal_spacing=0.135,
        subplot_titles=[
            f"events per ticker — {dist['n_events']:,} events / {dist['n_tickers']:,} tickers",
            "markout medians (log return)",
            "retracement medians (ratio)"])

    ks = sorted(int(k) for k in dist["histogram"])
    vs = [dist["histogram"][str(k)] for k in ks]
    fig.add_trace(go.Bar(
        x=ks, y=vs, marker_color=K.rgba(K.BLUE, 0.85), marker_line_width=0, showlegend=False,
        hovertemplate="%{x} events/ticker<br>%{y:,} tickers<extra></extra>"), row=1, col=1)
    fig.add_annotation(
        x=0.97, y=0.05, xref="x domain", yref="y domain", xanchor="right", yanchor="bottom",
        text=(f"median {dist['events_per_ticker_median']:.0f}/ticker · mean "
              f"{dist['events_per_ticker_mean']:.2f} · max {dist['events_per_ticker_max']}<br>"
              f"{dist['share_events_in_tickers_ge_5']:.0%} of events in tickers ≥5 events<br>"
              f"{dist['share_events_in_tickers_ge_10']:.0%} of events in tickers ≥10 events"),
        showarrow=False, font=dict(size=9, color=K.INK), align="left",
        bgcolor="rgba(255,255,255,0.9)", bordercolor=K.GRID, borderwidth=1)

    def forest(group, col, first_legend):
        order = list(reversed(group))
        for i, s in enumerate(order):
            if s["block_ci95"][0] is None:
                continue
            show = first_legend and i == len(order) - 1
            fig.add_trace(go.Scatter(
                x=s["naive_ci95"], y=[i + 0.17] * 2, mode="lines",
                line=dict(color=K.rgba(K.ORANGE, 0.95), width=7),
                name="naive (iid) 95% CI", showlegend=show,
                hovertemplate=(f"{s['name']}<br>naive CI [{s['naive_ci95'][0]:.4f}, "
                               f"{s['naive_ci95'][1]:.4f}]<extra></extra>")), row=1, col=col)
            fig.add_trace(go.Scatter(
                x=s["block_ci95"], y=[i - 0.17] * 2, mode="lines",
                line=dict(color=K.rgba(K.BLUE, 0.95), width=7),
                name="ticker-block 95% CI", showlegend=show,
                hovertemplate=(f"{s['name']}<br>block CI [{s['block_ci95'][0]:.4f}, "
                               f"{s['block_ci95'][1]:.4f}]<br>width ratio "
                               f"{s['width_ratio_block_over_naive']:.2f}×<extra></extra>")), row=1, col=col)
            fig.add_trace(go.Scatter(
                x=[s["median"]], y=[i], mode="markers",
                marker=dict(color=K.INK, size=8, symbol="diamond"), showlegend=False,
                hovertemplate=(f"{s['name']}<br>median {s['median']:.4f}<br>"
                               f"n={s['n']:,} · {s['n_tickers']:,} tickers<br>"
                               f"median of per-ticker medians {s['median_of_ticker_medians']:.4f}<br>"
                               f"{s['share_tickers_negative']:.1%} of tickers negative<extra></extra>")),
                row=1, col=col)
            fig.add_annotation(
                x=1.01, y=i, xref=f"x{col} domain", yref=f"y{col}", xanchor="left",
                text=f"n={s['n']:,} · {s['width_ratio_block_over_naive']:.2f}×",
                showarrow=False, font=dict(size=8, color=K.INK2))
        fig.add_vline(x=0, line=dict(color=K.INK2, width=1.5, dash="dot"), row=1, col=col)
        labs = [s["name"].split(" | ", 1)[-1] if col == 2 else s["name"].replace("retrace_", "")
                for s in order]
        fig.update_yaxes(tickmode="array", tickvals=list(range(len(order))), ticktext=labs,
                         tickfont=dict(size=8.5), range=[-0.7, len(order) - 0.3], row=1, col=col)

    forest(markouts, 2, True)
    forest(retrace, 3, False)

    wr = j["ci_width_ratio_summary"]
    title = ("08 · The cost of ticker clustering<br>"
             "<sub>events concentrate in a few thousand tickers, so nominal n overstates the number of "
             "independent observations</sub>")
    cap = K.caption(
        f"D1 n={dist['n_events']:,} across {dist['n_tickers']:,} tickers",
        "per-statistic populations as labelled; full detail in t5_clustered_inference.json",
        f"ticker-block bootstrap: resample TICKERS with replacement, {bs['reps']:,} reps, seed {bs['seed']}, "
        f"percentile CI · naive comparison: event-level iid bootstrap, same reps and seed<br>"
        f"width ratio block/naive: median {wr['median_block_over_naive']:.2f}×, range "
        f"{wr['min']:.2f}–{wr['max']:.2f}× across {wr['n_statistics']} statistics<br>"
        f"forest split by UNIT: markout medians sit near −0.03 log and retracement medians near +1.4 ratio; "
        f"on a shared axis the markout intervals are invisible<br>"
        f"right margin of each panel prints n and the width ratio; hover gives the "
        f"median-of-per-ticker-medians and the share of tickers with a negative median<br>"
        f"ratios slightly below 1.0 are Monte Carlo noise at {bs['reps']:,} reps, not a narrower true interval")
    fig.update_xaxes(title_text="events per ticker", row=1, col=1)
    fig.update_yaxes(title_text="tickers (log)", type="log", row=1, col=1)
    fig.update_xaxes(title_text="median log markout", row=1, col=2)
    fig.update_xaxes(title_text="median retracement ratio", row=1, col=3)
    K.base_layout(fig, title, cap, height=700, cap_y=-0.22, margin_b=240, margin_r=120, width=1750)
    fig.update_layout(legend=dict(x=0.255, y=-0.085, xanchor="left", orientation="h",
                                  bgcolor="rgba(255,255,255,0.86)",
                                  bordercolor=K.GRID, borderwidth=1, font=dict(size=10)))
    for a in fig.layout.annotations[:3]:
        a.font.size = 11
    K.write(fig, "08_clustered_inference")


if __name__ == "__main__":
    main()
