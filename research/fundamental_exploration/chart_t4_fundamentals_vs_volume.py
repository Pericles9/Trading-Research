"""
E1-T4 charts: event volume and turnover-lower-bound by shares-outstanding decile,
small multiples (rows=event year, cols=detection-price decile), matching the
established small-multiples layout already used in this repo (research/phase_13/
chart_common.py's rows=year/cols=price-decile grid) for exactly this cross-cut shape.
Each panel is one box-per-shs-decile plot; cells under the display floor render as an
empty/thin box, not a hidden one.

Two separate files (volume, turnover) -- one question each, per research-charts skill.
Turnover's y-axis is explicitly labeled "lower bound, ordinal only" per the brief.

Usage: .venv/Scripts/python.exe research/fundamental_exploration/chart_t4_fundamentals_vs_volume.py
"""
from __future__ import annotations

import os
import sys

import plotly.graph_objects as go
from plotly.subplots import make_subplots

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from research.fundamental_exploration import chart_common as CC  # noqa: E402


def build_grid(metric_key: str, title: str, y_title: str, color: str, log_y: bool):
    data = CC.load_json("t4_cells")["cells"]
    years = sorted({c["year"] for c in data})
    deciles = sorted({c["price_decile"] for c in data})
    shs_deciles = sorted({c["shs_decile"] for c in data})

    subplot_titles = [f"D{d}" if r == 0 else "" for r in range(len(years)) for d in deciles]
    fig = make_subplots(rows=len(years), cols=len(deciles), subplot_titles=subplot_titles,
                         horizontal_spacing=0.006, vertical_spacing=0.02, shared_yaxes=True)

    by_cell = {(c["year"], c["price_decile"], c["shs_decile"]): c[metric_key] for c in data}
    all_vals = []
    for ri, year in enumerate(years):
        for ci, pdec in enumerate(deciles):
            stats_list = [by_cell.get((year, pdec, sdec), {"n": 0}) for sdec in shs_deciles]
            x_labels = [f"S{d}" for d in shs_deciles]
            trace = CC.box_from_stats(x_labels, stats_list, metric_key, color)
            fig.add_trace(trace, row=ri + 1, col=ci + 1)
            for s in stats_list:
                if s.get("n", 0) > 0:
                    all_vals.extend([s["p10"], s["p90"]])
            fig.update_xaxes(showticklabels=False, row=ri + 1, col=ci + 1)
            fig.update_yaxes(showticklabels=(ci == 0), row=ri + 1, col=ci + 1,
                              type="log" if log_y else "linear")
            if ci == 0:
                fig.update_yaxes(title_text=str(year), title_font=dict(size=10), row=ri + 1, col=ci + 1)

    fig.update_layout(showlegend=False, height=110 * len(years) + 160, width=100 * len(deciles) + 140)
    n_total = sum(s.get("n", 0) for s in by_cell.values())
    cap = CC.caption(
        sample=f"n={n_total:,} (event, year, price-decile, shs-decile) cell-memberships summed",
        filters=f"rows=event year ({years[0]}-{years[-1]}), columns=detection-price decile "
                f"(D0=cheapest..D{deciles[-1]}=most expensive), x-axis within each panel="
                f"shares-outstanding decile (S0=fewest..S{shs_deciles[-1]}=most, split-corrected)",
        extra=y_title,
    )
    CC.base_layout(fig, title, cap, height=110 * len(years) + 220, width=100 * len(deciles) + 160,
                    cap_y=-0.03 - 0.01 * len(years), margin_b=170 + 6 * len(years), margin_r=20)
    return fig


def main():
    fig1 = build_grid("volume_shares", "E1-T4: event volume by shares-outstanding decile",
                       "y-axis: regular-session event volume, shares (log)", CC.BLUE, log_y=True)
    CC.write(fig1, "t4_fundamentals_vs_volume", "01_volume_by_shs_decile")

    fig2 = build_grid("turnover_lower_bound",
                       "E1-T4: turnover (volume / shares outstanding) by shares-outstanding decile",
                       "y-axis: volume_shares / shs_shares_outstanding_corrected -- LOWER BOUND vs true "
                       "float, ordinal ranking only, never a level (log)", CC.ORANGE, log_y=True)
    CC.write(fig2, "t4_fundamentals_vs_volume", "02_turnover_lower_bound_by_shs_decile")


if __name__ == "__main__":
    main()
