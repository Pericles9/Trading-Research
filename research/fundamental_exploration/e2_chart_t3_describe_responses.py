"""
E2-T3 charts: momentum_pct and duration_min distributions, survival curve, duration by
n_baseline_sessions. Censored share and baseline_thin status stated in-panel per the
brief, never only in a caption.

duration_min is heavily zero-inflated (52.2% exactly 0) -- shown as its own explicit
bar/share rather than silently dropped from a log-scale histogram (same class of care
as E1's shares-outstanding zero-artifact finding: zero and "small positive" are
different states here too, and collapsing them into one log-axis view would hide the
dominant mode entirely).

Usage: .venv/Scripts/python.exe research/fundamental_exploration/e2_chart_t3_describe_responses.py
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from research.fundamental_exploration import chart_common as CC  # noqa: E402
from research.fundamental_exploration import common as C  # noqa: E402


def chart_01_momentum_and_duration():
    cfg_e2 = C.load_cfg(C.CFG_E2)
    frame = pd.read_parquet(cfg_e2["universe"]["materialization_path"])
    frame["event_id"] = frame.apply(C.event_id, axis=1)
    window = pd.read_parquet(C.ev(f"{C.ART_E2}/e2_t2_window.parquet"))
    summary = CC.load_json(C.ev("e2_t3_describe_responses_summary"), root=C.ART_E2)

    fig = make_subplots(rows=1, cols=2, subplot_titles=("momentum_pct", "duration_min: zero vs. positive"))
    fig.add_trace(go.Histogram(x=np.log10(frame["momentum_pct"]), nbinsx=60, marker_color=CC.VIOLET,
                                hovertemplate="log10(momentum_pct)=%{x:.2f}<br>count=%{y}<extra></extra>"),
                  row=1, col=1)
    fig.update_xaxes(title="log10(momentum_pct, %)", row=1, col=1)

    n_zero = summary["n_zero_duration"]
    n_pos = summary["n_positive_duration"]
    fig.add_trace(go.Bar(x=["duration_min == 0"], y=[n_zero], marker_color=CC.RED,
                          hovertemplate="n=%{y:,}<extra></extra>", showlegend=False), row=1, col=2)
    fig.add_trace(go.Bar(x=["duration_min > 0"], y=[n_pos], marker_color=CC.BLUE,
                          hovertemplate="n=%{y:,}<extra></extra>", showlegend=False), row=1, col=2)
    fig.update_yaxes(title="count", row=1, col=2)

    fig.add_annotation(
        text=(f"<b>censored: {summary['n_censored']:,} / {summary['n_with_window']:,} "
              f"({summary['censored_share']:.1%})</b><br>"
              f"<b>baseline_thin: not computed (floor deferred)</b>"),
        xref="x domain", yref="y domain", x=0.02, y=1.18, xanchor="left", yanchor="bottom",
        showarrow=False, font=dict(size=11, color=CC.INK), row=1, col=2,
    )
    fig.update_layout(height=560)

    cap = CC.caption(
        sample=f"D1, momentum_pct n={summary['momentum_pct_stats']['n']:,}, "
               f"duration_min n={summary['n_with_window']:,} ({summary['n_skipped_no_baseline']} skipped, "
               f"no baseline buildable)",
        filters="momentum_pct read directly from momentum_events_canonical (DE-1, Cooper's sign-off) -- "
                "described only, never bucketed, never entering any computed statistic",
        extra="momentum_pct and duration_min are mechanically coupled (SS3): a longer window gives more "
              "time to print a higher high. Reported separately here, never combined into one score.",
    )
    CC.base_layout(fig, "E2-T3: momentum_pct and duration_min, on their own", cap, height=620, cap_y=-0.30, margin_b=210)
    CC.write(fig, "e2_t3", C.ev("01_momentum_and_duration"), root=C.CHARTS_E2)


def chart_02_survival_and_baseline_facet():
    surv = CC.load_json(C.ev("e2_t3_survival_curve"), root=C.ART_E2)["survival"]
    summary = CC.load_json(C.ev("e2_t3_describe_responses_summary"), root=C.ART_E2)
    window = pd.read_parquet(C.ev(f"{C.ART_E2}/e2_t2_window.parquet"))

    fig = make_subplots(rows=1, cols=2, subplot_titles=("survival curve (share with duration > x)",
                                                          "duration by n_baseline_sessions"))
    xs = [s["x"] for s in surv]
    ys = [s["share_gt_x"] for s in surv]
    fig.add_trace(go.Scatter(x=xs, y=ys, mode="lines", line=dict(color=CC.BLUE, shape="hv"),
                              hovertemplate="x=%{x:.1f} min<br>share>x=%{y:.1%}<extra></extra>"), row=1, col=1)
    fig.update_xaxes(title="duration_min (x)", type="log", row=1, col=1)
    fig.update_yaxes(title="share of events with duration_min > x", range=[0, 1.02], row=1, col=1)

    for n_sess, color in [(3, CC.BLUE), (2, CC.ORANGE), (1, CC.RED)]:
        grp = window[window["n_baseline_sessions"] == n_sess]["duration_min"]
        sub = grp[grp > 0]
        fig.add_trace(go.Box(y=sub, name=f"n={n_sess} (n_events={len(grp):,}, "
                                          f"{len(sub):,} with duration>0)",
                              marker_color=color, boxpoints=False), row=1, col=2)
    fig.update_yaxes(title="duration_min", type="log", row=1, col=2)

    cap = CC.caption(
        sample=f"D1, n={summary['n_with_window']:,}",
        filters=(C.censored_text() + "; the survival curve is the plain empirical function over uncensored "
                 "events, not a Kaplan-Meier estimator"),
        extra=(f"duration=0 ({C.zero_share_text(1)} of events) is excluded from the log-scale box plot at right (a box "
               f"plot cannot show a mass point at 0 on a log axis) -- see chart 01 for the zero-vs-positive "
               f"split. n_baseline_sessions=1/2 groups are small (140/107 events) relative to 3 (15,495)."),
    )
    CC.base_layout(fig, "E2-T3: survival curve and duration by baseline-session count", cap,
                    height=620, cap_y=-0.32, margin_b=210)
    CC.write(fig, "e2_t3", C.ev("02_survival_and_baseline_facet"), root=C.CHARTS_E2)


if __name__ == "__main__":
    chart_01_momentum_and_duration()
    chart_02_survival_and_baseline_facet()
