"""
E2-T4 chart: duration_min by t0 session segment and by t0 half-hour bucket, no
fundamental variable -- the confound's own size, for E2-T5/T6's panels to be read
against.

Usage: .venv/Scripts/python.exe research/fundamental_exploration/e2_chart_t4_time_of_day.py
"""
from __future__ import annotations

import os
import sys

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from research.fundamental_exploration import chart_common as CC  # noqa: E402
from research.fundamental_exploration import common as C  # noqa: E402


def main():
    tod = pd.read_parquet(C.ev(f"{C.ART_E2}/e2_t4_time_of_day.parquet"))
    window = pd.read_parquet(C.ev(f"{C.ART_E2}/e2_t2_window.parquet"))[["event_id", "duration_min"]]
    df = tod.merge(window, on="event_id", how="left")
    summary = CC.load_json(C.ev("e2_t4_time_of_day_summary"), root=C.ART_E2)

    fig = make_subplots(rows=1, cols=2, subplot_titles=("by t0 session segment", "by t0 half-hour bucket"),
                         column_widths=[0.25, 0.75])
    for seg, color in [("pre_market", CC.RED), ("regular", CC.BLUE), ("after_hours", CC.ORANGE)]:
        sub = df.loc[df["t0_segment"] == seg, "duration_min"]
        fig.add_trace(go.Box(y=sub, name=f"{seg} (n={len(sub):,})", marker_color=color, boxpoints=False),
                      row=1, col=1)
    fig.update_yaxes(title="duration_min", row=1, col=1)

    hh = df.groupby(["t0_half_hour_order", "t0_half_hour"], observed=True)["duration_min"].agg(
        ["median", "count", lambda s: s.quantile(0.75), lambda s: s.quantile(0.90)]
    ).reset_index()
    hh.columns = ["order", "label", "median", "n", "p75", "p90"]
    hh = hh.sort_values("order")
    # median is excluded from this log-scale panel -- it is exactly 0 for most buckets
    # (consistent with the population as a whole) and a log axis simply drops zero/negative
    # points, which would render as silent gaps rather than an honest "0" value. p75/p90
    # are positive throughout and are what a log axis is actually useful for here.
    for col, name, color in [("p75", "p75", CC.ORANGE), ("p90", "p90", CC.RED)]:
        fig.add_trace(go.Scatter(x=hh["label"], y=hh[col], mode="lines+markers", name=name,
                                  line=dict(color=color), customdata=hh["n"],
                                  hovertemplate="%{x}<br>%{y:.1f} min (n=%{customdata})<extra></extra>"),
                      row=1, col=2)
    fig.update_xaxes(tickangle=-60, row=1, col=2)
    fig.update_yaxes(title="duration_min (p75/p90 only -- median is 0 for most buckets, see caption)",
                      type="log", row=1, col=2)
    fig.update_layout(height=580, width=1300)

    cap = CC.caption(
        sample=f"D1, n={summary['n_total']:,}",
        filters="no fundamental variable in this chart -- t0 session/half-hour only, per the brief",
        extra=(f"regular={summary['segment_counts']['regular']:,} · "
               f"pre_market={summary['segment_counts']['pre_market']:,} · "
               f"after_hours={summary['segment_counts']['after_hours']:,}. "
               f"p90 by segment: pre_market {summary['duration_by_segment']['pre_market']['p90']:.0f}min · "
               f"regular {summary['duration_by_segment']['regular']['p90']:.0f}min · "
               f"after_hours {summary['duration_by_segment']['after_hours']['p90']:.0f}min -- pre-market "
               f"events that DO run positive duration run far longer, as DE-2's flat RTH baseline predicts. "
               f"Right panel shows p75/p90 only -- median is 0 for nearly every half-hour bucket "
               f"(consistent with the population as a whole, T3), and a log axis can't render a zero."),
    )
    CC.base_layout(fig, "E2-T4: the time-of-day confound, no fundamental variable", cap,
                    height=640, cap_y=-0.34, margin_b=240, width=1300)
    CC.write(fig, "e2_t4", C.ev("01_duration_by_time_of_day"), root=C.CHARTS_E2)


if __name__ == "__main__":
    main()
