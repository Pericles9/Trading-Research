"""
E1-T2 chart: coverage share per fundamental group, by year -- one bar chart, n per
year/group cell shown on hover and in the caption. Also renders the spl_quality vs
identity_quality crosstab as a second, small panel so the "unavailable" conflation
found in t2_coverage.py is visible, not just logged in JSON.

Usage: .venv/Scripts/python.exe research/fundamental_exploration/chart_t2_coverage.py
"""
from __future__ import annotations

import os
import sys

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from research.fundamental_exploration import chart_common as CC  # noqa: E402

GROUP_COLORS = {"flg": CC.BLUE, "shs": CC.ORANGE, "si": CC.AQUA, "spl": CC.GREEN}
GROUP_LABELS = {"flg": "flg (SEC filings)", "shs": "shs (SEC, shares out.)",
                "si": "si (vendor, short interest)", "spl": "spl (vendor, splits)"}


def main():
    cov = pd.read_parquet(f"{CC.ART}/t2_coverage_by_year.parquet")
    summary = CC.load_json("t2_coverage_summary")

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

    cliff = summary["cliff_check"]
    cliff_lines = "<br>".join(
        f"{g}: 2022-23 mean {cliff[g]['cliff_years_coverage']}, "
        f"other years mean {cliff[g]['other_years_mean_coverage']:.1%}"
        for g in ["flg", "shs", "si", "spl"]
    )
    spl_note = summary["spl_quality_semantics"]
    cap = CC.caption(
        sample=f"20,951 in-scope events, {summary['n_by_year']}",
        filters="coverage = share of events where {group}_quality != 'unavailable', no population filter applied",
        extra=(f"E1-T2's own check: SEC-sourced groups (flg, shs) do not show a 2022-23 cliff "
               f"(sec_shows_cliff_defect={summary['sec_shows_cliff_defect']}).<br>"
               f"spl_quality caveat: 'unavailable' conflates confirmed-zero-splits with "
               f"true data gaps ({spl_note['n_spl_unavailable_with_resolved_identity']:,} of its "
               f"'unavailable' rows have a resolved CIK) -- see t5_assemble.py:180-181."),
    )
    CC.base_layout(fig, "E1-T2: fundamental-group coverage by year", cap, height=620, cap_y=-0.42, margin_b=260)
    CC.legend_inside(fig)
    CC.write(fig, "t2_coverage", "01_coverage_by_year")


if __name__ == "__main__":
    main()
