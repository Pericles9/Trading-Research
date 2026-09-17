"""
E2-T1 chart: distance-to-boundary (log10(event_volume / min_volume_threshold))
distribution, overall and by each fundamental split E2-T5/T6 use. Box-from-stats per
group, all sharing one y-axis so "how close to the population as a whole" is a direct
visual comparison.

Usage: .venv/Scripts/python.exe research/fundamental_exploration/e2_chart_t1_boundary_audit.py
"""
from __future__ import annotations

import os
import sys

import plotly.graph_objects as go
from plotly.subplots import make_subplots

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from research.fundamental_exploration import chart_common as CC  # noqa: E402
from research.fundamental_exploration import common as C  # noqa: E402

SPLIT_ORDER = ["shs_decile", "flg_dilution_form_before_t0", "spl_reverse_split_365d",
               "flg_lag_bucket", "si_quality"]
SPLIT_TITLES = {
    "shs_decile": "shares-outstanding decile", "flg_dilution_form_before_t0": "dilution flag",
    "spl_reverse_split_365d": "reverse split (365d)", "flg_lag_bucket": "days since filing",
    "si_quality": "si_quality",
}


def main():
    summary = CC.load_json("e2_t1_boundary_audit_summary", root=C.ART_E2)
    overall = summary["overall_distance_log10"]
    splits = summary["splits"]

    fig = make_subplots(rows=1, cols=len(SPLIT_ORDER), subplot_titles=[SPLIT_TITLES[s] for s in SPLIT_ORDER],
                         horizontal_spacing=0.03, shared_yaxes=True)
    for ci, split_name in enumerate(SPLIT_ORDER, start=1):
        groups = splits[split_name]
        labels = list(groups.keys())
        stats_list = [groups[g] for g in labels]
        trace = CC.box_from_stats(labels, stats_list, split_name, CC.BLUE)
        fig.add_trace(trace, row=1, col=ci)
        fig.add_hline(y=overall["median"], line_dash="dot", line_color=CC.INK2, row=1, col=ci)
        fig.update_xaxes(tickangle=-30, row=1, col=ci)
    fig.update_yaxes(title="log10(event_volume / min_volume_threshold)", row=1, col=1)

    cap = CC.caption(
        sample=f"D1, n={summary['n_total']:,}. Dotted line = overall population median "
               f"({overall['median']:.2f}, ~{10**overall['median']:,.0f}x the q05 boundary).",
        filters="event_volume, min_volume_threshold read from raw momentum_events under D4 Amendment "
                "A13's exemption -- diagnostic only, entering no other computed quantity.",
        extra=f"Flagged splits (median < half the overall median, n>=20): "
              f"{summary['flagged_materially_closer_to_boundary'] or 'none'}.",
    )
    CC.base_layout(fig, "E2-T1: distance to the q05 volume-selection boundary, by fundamental split", cap,
                    height=620, cap_y=-0.32, margin_b=210, width=1400)
    CC.write(fig, "e2_t1", "01_boundary_distance_by_split", root=C.CHARTS_E2)


if __name__ == "__main__":
    main()
