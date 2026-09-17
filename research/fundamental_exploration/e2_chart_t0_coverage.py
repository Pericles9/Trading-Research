"""
E2-T0 chart: D1 fundamental-group coverage by year. Same definition and layout as
E1-T2's chart_t2_coverage.py, restricted to D1 (n=15,763) instead of the full
in-scope population.

Usage: .venv/Scripts/python.exe research/fundamental_exploration/e2_chart_t0_coverage.py
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

GROUP_COLORS = {"flg": CC.BLUE, "shs": CC.ORANGE, "si": CC.AQUA, "spl": CC.GREEN}
GROUP_LABELS = {"flg": "flg (SEC filings)", "shs": "shs (SEC, shares out.)",
                "si": "si (vendor, short interest)", "spl": "spl (vendor, splits)"}


def main():
    cov = pd.read_parquet(f"{C.ART_E2}/e2_t0_coverage_by_year.parquet")
    summary = CC.load_json("e2_t0_population_summary", root=C.ART_E2)

    fig = make_subplots(rows=1, cols=1)
    years = sorted(cov["year"].unique())
    for g in ["flg", "shs", "si", "spl"]:
        gdf = cov[cov["group"] == g].set_index("year").reindex(years)
        fig.add_trace(go.Bar(
            x=years, y=gdf["coverage_share"], name=GROUP_LABELS[g], marker_color=GROUP_COLORS[g],
            customdata=gdf[["n_covered", "n_total"]].values,
            hovertemplate=f"{GROUP_LABELS[g]}<br>%{{x}}: %{{y:.1%}}<br>n=%{{customdata[0]:,}}/%{{customdata[1]:,}}<extra></extra>",
        ))
    fig.update_layout(barmode="group", height=560)
    fig.update_yaxes(title="coverage share ({group}_quality != 'unavailable')", range=[0, 1.05])
    fig.update_xaxes(title="event year")

    cap = CC.caption(
        sample=f"D1 population (in_scope=TRUE AND source_file='file1'), n=15,763, {summary['n_by_year']}",
        filters="coverage = share of events where {group}_quality != 'unavailable', no population filter applied. "
                "No 2020-2024 gap by construction here (D1 has zero 2025 events -- all 2025 in-scope events are file2).",
        extra="spl_quality carries E1-T2's own finding: 'unavailable' conflates confirmed-zero-splits with true data gaps.",
    )
    CC.base_layout(fig, "E2-T0: D1 fundamental-group coverage by year", cap, height=620, cap_y=-0.34, margin_b=220)
    CC.legend_inside(fig)
    CC.write(fig, "e2_t0", "01_coverage_by_year", root=C.CHARTS_E2)


if __name__ == "__main__":
    main()
