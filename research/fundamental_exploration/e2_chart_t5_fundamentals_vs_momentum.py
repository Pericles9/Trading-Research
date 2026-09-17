"""
E2-T5 charts: momentum_pct by each fundamental split, small multiples (rows=event
year, cols=detection-price decile, x-axis within panel=split value) -- same layout as
E1-T4/research/phase_13/chart_common.py for this exact cross-cut shape. One file per
split (5 files, one question each).

Usage: .venv/Scripts/python.exe research/fundamental_exploration/e2_chart_t5_fundamentals_vs_momentum.py
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from research.fundamental_exploration import chart_common as CC  # noqa: E402
from research.fundamental_exploration import common as C  # noqa: E402

SPLIT_VALUE_ORDER = {
    "flg_dilution_form_before_t0": ["False", "True", "unavailable"],
    "spl_reverse_split_365d": ["False", "True"],
    "flg_lag_bucket": ["<=1d", "1-7d", "7-30d", "30-90d", ">90d", "nan"],
    "si_quality": ["observed", "unavailable"],
}


def build_grid(split_name: str, title: str):
    data = CC.load_json("e2_t5_cells", root=C.ART_E2)["splits"][split_name]
    years = sorted({c["year"] for c in data})
    deciles = sorted({c["price_decile"] for c in data if c["price_decile"] is not None})

    if split_name == "shs_decile":
        split_values = [f"S{d}" for d in range(10)] + ["no_shs_data"]
    else:
        split_values = SPLIT_VALUE_ORDER.get(split_name, sorted({c["split_value"] for c in data}))

    import plotly.graph_objects as go
    from plotly.subplots import make_subplots

    subplot_titles = [f"D{d}" if r == 0 else "" for r in range(len(years)) for d in deciles]
    fig = make_subplots(rows=len(years), cols=len(deciles), subplot_titles=subplot_titles,
                         horizontal_spacing=0.006, vertical_spacing=0.02, shared_yaxes=True)

    by_cell = {(c["year"], c["price_decile"], c["split_value"]): c["momentum_pct"] for c in data}
    for ri, year in enumerate(years):
        for ci, pdec in enumerate(deciles):
            stats_list = [by_cell.get((year, pdec, sv), {"n": 0}) for sv in split_values]
            trace = CC.box_from_stats(split_values, stats_list, split_name, CC.VIOLET)
            fig.add_trace(trace, row=ri + 1, col=ci + 1)
            fig.update_xaxes(showticklabels=False, row=ri + 1, col=ci + 1)
            fig.update_yaxes(showticklabels=(ci == 0), type="log", row=ri + 1, col=ci + 1)
            if ci == 0:
                fig.update_yaxes(title_text=str(year), title_font=dict(size=10), row=ri + 1, col=ci + 1)

    fig.update_layout(showlegend=False, height=110 * len(years) + 160, width=100 * len(deciles) + 140)
    n_total = sum(s.get("n", 0) for s in by_cell.values())
    cap = CC.caption(
        sample=f"n={n_total:,} cell-memberships summed",
        filters=f"rows=event year ({years[0]}-{years[-1]}), columns=detection-price decile "
                f"(D0=cheapest..D{deciles[-1]}=most expensive), x-axis within each panel={split_name}",
        extra="momentum_pct: DE-1, described only, never bucketed as an input elsewhere. Read against "
              "E2-T1's distance-to-boundary audit -- no split there flagged as artificially close to "
              "the volume-selection filter.",
    )
    CC.base_layout(fig, title, cap, height=110 * len(years) + 220, width=100 * len(deciles) + 160,
                    cap_y=-0.03 - 0.01 * len(years), margin_b=190 + 6 * len(years), margin_r=20)
    return fig


def main():
    titles = {
        "shs_decile": "E2-T5: momentum_pct by shares-outstanding decile",
        "flg_dilution_form_before_t0": "E2-T5: momentum_pct by dilution flag",
        "spl_reverse_split_365d": "E2-T5: momentum_pct by reverse-split flag",
        "flg_lag_bucket": "E2-T5: momentum_pct by days-since-filing bucket",
        "si_quality": "E2-T5: momentum_pct by si_quality",
    }
    for i, (split_name, title) in enumerate(titles.items(), start=1):
        fig = build_grid(split_name, title)
        CC.write(fig, "e2_t5", f"{i:02d}_momentum_by_{split_name}", root=C.CHARTS_E2)


if __name__ == "__main__":
    main()
