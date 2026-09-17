"""
E1-T6 charts: reverse-split cohort (spl_reverse_split_365d True vs False) compared
across the variables T1-T5/T7 already established as informative -- detection price,
shares outstanding, event volume, turnover, filing lag, dilution rate, and per-group
coverage. Two files: one distributional (box-from-stats per metric, plus a jittered
raw-point strip behind the 4 metrics affected by the share-count-artifact tail --
outliers shown, never clipped, per research-charts skill SS2), one for the two
rate-style comparisons (dilution rate, coverage).

Usage: .venv/Scripts/python.exe research/fundamental_exploration/chart_t6_reverse_split_cohort.py
"""
from __future__ import annotations

import os
import sys

import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from research.fundamental_exploration import chart_common as CC  # noqa: E402

METRICS = [
    ("detection_price", "detection price (USD)", True),
    ("shs_shares_outstanding_corrected", "shares outstanding, corrected", True),
    ("volume_shares", "event volume (shares)", True),
    ("turnover_lower_bound", "turnover, lower bound (ordinal only)", True),
    ("flg_lag_ns_days", "days since nearest filing", True),
]
COHORTS = [("reverse_split_365d_true", CC.RED, -0.18), ("reverse_split_365d_false", CC.BLUE, 0.18)]


def chart_01_distributions():
    full = CC.load_json("t6_reverse_split_cohort")
    data = full["cohorts"]
    raw = full.get("raw_samples", {})
    rng = np.random.default_rng(42)

    fig = make_subplots(rows=1, cols=len(METRICS),
                         subplot_titles=[m[1] for m in METRICS], horizontal_spacing=0.05)
    for ci, (key, label, log_y) in enumerate(METRICS, start=1):
        for cohort_name, color, x_offset in COHORTS:
            s = data[cohort_name][key]
            trace = CC.box_from_stats([label], [s], cohort_name.replace("reverse_split_365d_", ""), color,
                                       offsetgroup=cohort_name)
            trace.showlegend = (ci == 1)
            fig.add_trace(trace, row=1, col=ci)
            if key in raw and cohort_name in raw[key]:
                pts = np.asarray(raw[key][cohort_name])
                pts = pts[pts > 0] if log_y else pts
                jitter = rng.uniform(-0.12, 0.12, size=len(pts))
                fig.add_trace(go.Scatter(
                    x=[x_offset + j for j in jitter], y=pts, mode="markers",
                    marker=dict(size=3, color=color, opacity=0.18), showlegend=False, hoverinfo="y",
                ), row=1, col=ci)
        fig.update_xaxes(showticklabels=False, range=[-0.6, 0.6], row=1, col=ci)
        fig.update_yaxes(type="log" if log_y else "linear", row=1, col=ci)

    n_true = data["reverse_split_365d_true"]["n"]
    n_false = data["reverse_split_365d_false"]["n"]
    ssn = full["share_count_suspect_note"]
    cap = CC.caption(
        sample=f"reverse_split_365d=True: n={n_true:,} · False: n={n_false:,}. {full['raw_samples_note']}",
        filters="spl_reverse_split_365d: bool_or(ratio<1) in the 365 days before t0, filled False when "
                "no split matches -- always defined, no unavailable state (unlike spl_quality, E1-T2)",
        extra=(f"turnover_lower_bound: volume_shares / shs_shares_outstanding_corrected, ordinal only, "
               f"never a level. {ssn['n_total_below_threshold']} events (both cohorts) carry "
               f"shs_shares_outstanding_corrected < {ssn['threshold']:,} shares -- implausible for a real "
               f"company (one trades ~79M shares against a filed count of 100) -- shown, not excluded; "
               f"this is what pulls turnover's MEAN far above its median in both cohorts. Prefer median/IQR."),
    )
    CC.base_layout(fig, "E1-T6: reverse-split cohort vs. rest, key distributions", cap,
                    height=680, cap_y=-0.38, margin_b=250, width=1300)
    CC.legend_inside(fig)
    CC.write(fig, "t6_reverse_split_cohort", "01_key_distributions")


def chart_02_rates():
    data = CC.load_json("t6_reverse_split_cohort")["cohorts"]
    groups = ["flg", "shs", "si", "spl"]
    fig = make_subplots(rows=1, cols=2, subplot_titles=("per-group coverage", "dilution-flag rate"))

    for cohort_name, color in [("reverse_split_365d_true", CC.RED), ("reverse_split_365d_false", CC.BLUE)]:
        cov = data[cohort_name]["coverage"]
        fig.add_trace(go.Bar(x=groups, y=[cov[g] for g in groups], name=cohort_name.replace("reverse_split_365d_", ""),
                              marker_color=color, legendgroup=cohort_name,
                              hovertemplate="%{x}<br>%{y:.1%}<extra></extra>"), row=1, col=1)
        dil = data[cohort_name]["dilution_rate"]
        fig.add_trace(go.Bar(x=["dilution rate"], y=[dil["rate"]], name=cohort_name.replace("reverse_split_365d_", ""),
                              marker_color=color, legendgroup=cohort_name, showlegend=False,
                              customdata=[dil["n"]],
                              hovertemplate="n=%{customdata:,}<br>%{y:.1%}<extra></extra>"), row=1, col=2)
    fig.update_layout(barmode="group")
    fig.update_yaxes(title="share", range=[0, 1.05], row=1, col=1)
    fig.update_yaxes(title="rate", range=[0, 1.05], row=1, col=2)

    n_true = data["reverse_split_365d_true"]["n"]
    n_false = data["reverse_split_365d_false"]["n"]
    cap = CC.caption(
        sample=f"reverse_split_365d=True: n={n_true:,} · False: n={n_false:,}",
        filters="coverage = share of {group}_quality != 'unavailable' (spl's own share carries E1-T2's "
                "zero/unavailable-conflation caveat); dilution rate over flg_quality != 'unavailable' only",
    )
    CC.base_layout(fig, "E1-T6: reverse-split cohort vs. rest, coverage and dilution rate", cap,
                    height=560, cap_y=-0.30, margin_b=190)
    CC.write(fig, "t6_reverse_split_cohort", "02_coverage_and_dilution_rate")


if __name__ == "__main__":
    chart_01_distributions()
    chart_02_rates()
