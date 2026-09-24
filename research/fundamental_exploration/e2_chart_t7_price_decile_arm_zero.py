"""
E2-T7 chart: momentum_pct and duration_min by detection-price decile alone, no
fundamental variable, no year cross-cut -- the control E2-T5/T6 are read against.

Usage: .venv/Scripts/python.exe research/fundamental_exploration/e2_chart_t7_price_decile_arm_zero.py
"""
from __future__ import annotations

import os
import sys

from plotly.subplots import make_subplots

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from research.fundamental_exploration import chart_common as CC  # noqa: E402
from research.fundamental_exploration import common as C  # noqa: E402


def main():
    summary = CC.load_json(C.ev("e2_t7_price_decile_arm_zero_summary"), root=C.ART_E2)
    mom = summary["momentum_pct_by_price_decile"]
    dur = summary["duration_min_by_price_decile"]
    deciles = sorted(int(d) for d in mom.keys())
    labels = [f"D{d}" for d in deciles]

    fig = make_subplots(rows=1, cols=2, subplot_titles=("momentum_pct by price decile",
                                                          "duration_min by price decile"))
    mom_stats = [mom[str(d)] for d in deciles]
    fig.add_trace(CC.box_from_stats(labels, mom_stats, "momentum_pct", CC.VIOLET), row=1, col=1)
    fig.update_yaxes(title="momentum_pct (%)", type="log", row=1, col=1)

    dur_stats = [dur[str(d)]["duration_min"] for d in deciles]
    fig.add_trace(CC.box_from_stats(labels, dur_stats, "duration_min", CC.BLUE), row=1, col=2)
    fig.update_yaxes(title=f"duration_min (linear -- {C.zero_share_text()} exactly 0, E2-T3)", row=1, col=2)

    fig.update_layout(height=560, showlegend=False)
    cap = CC.caption(
        sample=f"D1, momentum n={summary['n_momentum']:,}, duration n={summary['n_duration']:,}",
        filters="detection-price decile alone -- no fundamental variable, no year cross-cut. "
                "Phase 11: net edge is a function of price level. If this reproduces what E2-T5/T6's "
                "fundamental splits show, the fundamental layer earned nothing here.",
    )
    CC.base_layout(fig, "E2-T7: price-decile arm zero, no fundamental variable", cap,
                    height=620, cap_y=-0.30, margin_b=210, width=1100)
    CC.write(fig, "e2_t7", C.ev("01_arm_zero_by_price_decile"), root=C.CHARTS_E2)


if __name__ == "__main__":
    main()
