"""
E2-T2a chart: B_e's real distribution (shares per 10-minute interval), faceted by
n_baseline_sessions -- the empirical picture Cooper asked for before setting the
baseline floor.

Usage: .venv/Scripts/python.exe research/fundamental_exploration/e2_chart_t2a_baseline.py
"""
from __future__ import annotations

import os
import sys

import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from research.fundamental_exploration import chart_common as CC  # noqa: E402
from research.fundamental_exploration import common as C  # noqa: E402


def main():
    df = pd.read_parquet(f"{C.ART_E2}/e2_t2a_baseline.parquet")
    summary = CC.load_json("e2_t2a_baseline_summary", root=C.ART_E2)

    fig = make_subplots(rows=1, cols=2, subplot_titles=("all events with a defined B_e", "by n_baseline_sessions"))

    valid = df.dropna(subset=["B_e"])
    fig.add_trace(go.Histogram(x=np.log10(valid["B_e"]), nbinsx=60, marker_color=CC.BLUE,
                                hovertemplate="log10(B_e)=%{x:.2f}<br>count=%{y}<extra></extra>"),
                  row=1, col=1)
    for n_sess, color in [(3, CC.BLUE), (2, CC.ORANGE), (1, CC.RED)]:
        sub = valid[valid["n_baseline_sessions"] == n_sess]
        fig.add_trace(go.Histogram(x=np.log10(sub["B_e"]), nbinsx=60, marker_color=color, opacity=0.6,
                                    name=f"n_baseline_sessions={n_sess} (n={len(sub):,})",
                                    hovertemplate="log10(B_e)=%{x:.2f}<br>count=%{y}<extra></extra>"),
                      row=1, col=2)
    fig.update_layout(barmode="overlay", height=560)
    fig.update_xaxes(title="log10(B_e), shares per 10-min interval")
    fig.update_yaxes(title="count")

    s = summary["B_e_distribution_shares_per_10min"]
    cap = CC.caption(
        sample=f"D1, n={summary['n_total']:,} ({summary['n_zero_baseline_sessions']} with "
               f"n_baseline_sessions==0, B_e undefined, excluded from this chart)",
        filters="B_e = total rth volume across present T-3..T-1 sessions / (n_present x 39 ten-minute intervals)",
        extra=(f"p1={s['p1']:,.0f} · p5={s['p5']:,.0f} · p10={s['p10']:,.0f} · p25={s['p25']:,.0f} · "
               f"median={s['median']:,.0f} · p75={s['p75']:,.0f} · p90={s['p90']:,.0f} · max={s['max']:,.0f} "
               f"shares/10-min. n_baseline_sessions: {summary['n_baseline_sessions_counts']}."),
    )
    CC.base_layout(fig, "E2-T2a: baseline volume B_e, pre-floor", cap, height=620, cap_y=-0.34, margin_b=220)
    CC.legend_inside(fig)
    CC.write(fig, "e2_t2a", "01_baseline_distribution", root=C.CHARTS_E2)


if __name__ == "__main__":
    main()
