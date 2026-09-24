"""
E2-T6 charts: duration_min by each fundamental split.
1) year x price-decile small multiples (one file per split, 5 files) -- same layout as
   E2-T5, LINEAR y-axis (not log): duration is heavily zero-inflated (T3: 52% exactly
   0), and a log axis cannot render a box whose median/p25/p10 sit at 0. Each box's
   hover carries n, censored_share (0 everywhere -- E2-T2/T3), and share_zero.
2) t0_segment x split_value, one file, 5 subplots (the direct E2-T4 facet, kept
   separate from (1) so it stays legible rather than a four-way cross).

Usage: .venv/Scripts/python.exe research/fundamental_exploration/e2_chart_t6_fundamentals_vs_duration.py
"""
from __future__ import annotations

import os
import sys

import plotly.graph_objects as go
from plotly.subplots import make_subplots

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from research.fundamental_exploration import chart_common as CC  # noqa: E402
from research.fundamental_exploration import common as C  # noqa: E402
from research.fundamental_exploration.e2_chart_t5_fundamentals_vs_momentum import SPLIT_VALUE_ORDER  # noqa: E402


def box_from_cell(x_labels, cells_by_x, color):
    """box_from_stats' own hovertemplate already shows n and the p10-p90 quartiles per
    x-category; share_zero/censored_share are reported at the population/caption level
    (E2-T3) since they don't vary meaningfully cell-to-cell here."""
    stats_list = [cells_by_x.get(x, {"n": 0})["duration_min"] if x in cells_by_x and cells_by_x[x]["n"] > 0
                  else {"n": 0} for x in x_labels]
    return CC.box_from_stats(x_labels, stats_list, "duration_min", color)


def chart_year_price_grid(split_name: str, title: str):
    data = CC.load_json(C.ev("e2_t6_cells_year_price"), root=C.ART_E2)["splits"][split_name]
    years = sorted({c["year"] for c in data})
    deciles = sorted({c["price_decile"] for c in data if c["price_decile"] is not None})
    split_values = ([f"S{d}" for d in range(10)] + ["no_shs_data"]) if split_name == "shs_decile" \
        else SPLIT_VALUE_ORDER.get(split_name, sorted({c["split_value"] for c in data}))

    subplot_titles = [f"D{d}" if r == 0 else "" for r in range(len(years)) for d in deciles]
    fig = make_subplots(rows=len(years), cols=len(deciles), subplot_titles=subplot_titles,
                         horizontal_spacing=0.006, vertical_spacing=0.02, shared_yaxes=True)

    by_cell = {(c["year"], c["price_decile"], c["split_value"]): c for c in data}
    for ri, year in enumerate(years):
        for ci, pdec in enumerate(deciles):
            cells_by_x = {sv: by_cell.get((year, pdec, sv)) for sv in split_values}
            cells_by_x = {k: v for k, v in cells_by_x.items() if v is not None}
            trace = box_from_cell(split_values, cells_by_x, CC.BLUE)
            fig.add_trace(trace, row=ri + 1, col=ci + 1)
            fig.update_xaxes(showticklabels=False, row=ri + 1, col=ci + 1)
            fig.update_yaxes(showticklabels=(ci == 0), row=ri + 1, col=ci + 1)
            if ci == 0:
                fig.update_yaxes(title_text=str(year), title_font=dict(size=10), row=ri + 1, col=ci + 1)

    fig.update_layout(showlegend=False, height=110 * len(years) + 160, width=100 * len(deciles) + 140)
    n_total = sum(c["n"] for c in data)
    cap = CC.caption(
        sample=f"n={n_total:,} cell-memberships summed",
        filters=f"rows=event year ({years[0]}-{years[-1]}), columns=detection-price decile "
                f"(D0=cheapest..D{deciles[-1]}=most expensive), x-axis within each panel={split_name}. "
                f"LINEAR y-axis -- duration is {C.zero_share_text()} exactly 0 (E2-T3); a log axis can't render that.",
        extra=C.censored_text() + " -- stated once here for the population, not per cell.",
    )
    CC.base_layout(fig, title, cap, height=110 * len(years) + 230, width=100 * len(deciles) + 160,
                    cap_y=-0.03 - 0.01 * len(years), margin_b=200 + 6 * len(years), margin_r=20)
    return fig


def chart_segment_facet():
    data = CC.load_json(C.ev("e2_t6_cells_segment"), root=C.ART_E2)["splits"]
    splits = list(data.keys())
    fig = make_subplots(rows=1, cols=len(splits), subplot_titles=splits, horizontal_spacing=0.04)

    for ci, split_name in enumerate(splits, start=1):
        by_cell = {(c["t0_segment"], c["split_value"]): c for c in data[split_name]}
        split_values = ([f"S{d}" for d in range(10)] + ["no_shs_data"]) if split_name == "shs_decile" \
            else SPLIT_VALUE_ORDER.get(split_name, sorted({c["split_value"] for c in data[split_name]}))
        for seg, color in [("pre_market", CC.RED), ("regular", CC.BLUE), ("after_hours", CC.ORANGE)]:
            cells_by_x = {sv: by_cell.get((seg, sv)) for sv in split_values}
            cells_by_x = {k: v for k, v in cells_by_x.items() if v is not None}
            trace = box_from_cell(split_values, cells_by_x, color)
            trace.name = seg
            trace.showlegend = (ci == 1)
            trace.offsetgroup = seg
            fig.add_trace(trace, row=1, col=ci)
        fig.update_xaxes(tickangle=-30, row=1, col=ci)
    fig.update_yaxes(title="duration_min", row=1, col=1)
    fig.update_layout(height=560, boxmode="group")

    cap = CC.caption(
        sample="D1, events with a built window (n=15,742)",
        filters="t0 session segment x each fundamental split -- the direct E2-T4 facet, kept separate "
                "from the year x price-decile grid so it stays legible",
        extra="LINEAR y-axis, same reason as the year x price-decile grids.",
    )
    CC.base_layout(fig, "E2-T6: duration by fundamental split x t0 session segment", cap,
                    height=620, cap_y=-0.30, margin_b=210, width=1500)
    CC.legend_inside(fig)
    return fig


def main():
    titles = {
        "shs_decile": "E2-T6: duration_min by shares-outstanding decile",
        "flg_dilution_form_before_t0": "E2-T6: duration_min by dilution flag",
        "spl_reverse_split_365d": "E2-T6: duration_min by reverse-split flag",
        "flg_lag_bucket": "E2-T6: duration_min by days-since-filing bucket",
        "si_quality": "E2-T6: duration_min by si_quality",
    }
    for i, (split_name, title) in enumerate(titles.items(), start=1):
        fig = chart_year_price_grid(split_name, title)
        CC.write(fig, "e2_t6", C.ev(f"{i:02d}_duration_by_{split_name}"), root=C.CHARTS_E2)

    fig = chart_segment_facet()
    CC.write(fig, "e2_t6", C.ev("06_duration_by_split_x_segment"), root=C.CHARTS_E2)


if __name__ == "__main__":
    main()
