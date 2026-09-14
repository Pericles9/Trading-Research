"""
Build F1, F1-T6b: chart the coverage surface. Distribution before aggregate -- every panel
below shows n per cell, never a bare percentage with no denominator in view.

Palette literals copied from research/phase_9/chart_common.py's validated CAT5 set, matching
this build's established convention (chart_t1_identity_quality.py, chart_t3_filing_proximity.py).

Usage: .venv/Scripts/python.exe research/fundamentals_f1/chart_t6_coverage.py
"""
from __future__ import annotations

import os
import sys

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from research.fundamentals_f1 import common as C  # noqa: E402

BLUE, ORANGE, AQUA, YELLOW, GREEN = "#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#008300"
INK, INK2, GRID, SURFACE = "#0b0b0b", "#52514e", "#e1e0d9", "#fcfcfb"
GROUP_COLORS = {"flg": BLUE, "shs": ORANGE, "fin": AQUA, "si": YELLOW, "spl": GREEN}
GROUPS = ["flg", "shs", "fin", "si", "spl"]

OUT_HTML = f"{C.CHARTS}/t6_coverage_surface.html"


def main():
    ef = pd.read_parquet(f"{C.NORMALIZED_ROOT}/event_fundamentals.parquet")
    ctx = pd.read_parquet(f"{C.ART}/t6_context.parquet")
    df = ef.merge(ctx, on="event_id", how="left")
    df["year"] = df["event_id"].str.extract(r"_(\d{4})-\d{2}-\d{2}_")[0]
    n_total = len(df)

    fig = make_subplots(
        rows=4, cols=1, vertical_spacing=0.09,
        subplot_titles=(
            "Coverage by year", "Coverage by detection-price decile (0=cheapest, 9=priciest)",
            "Coverage by delisted status", "Coverage by exchange",
        ),
    )

    def add_panel(row, by_col, order=None):
        cats = order if order is not None else sorted(df[by_col].dropna().unique())
        for g in GROUPS:
            covered = df[df[f"{g}_quality"] != "unavailable"]
            n_by_cat = df.groupby(by_col, observed=True).size().reindex(cats, fill_value=0)
            cov_by_cat = covered.groupby(by_col, observed=True).size().reindex(cats, fill_value=0)
            share = (cov_by_cat / n_by_cat).fillna(0)
            fig.add_trace(
                go.Bar(x=[str(c) for c in cats], y=share.values, name=g, marker_color=GROUP_COLORS[g],
                       legendgroup=g, showlegend=(row == 1),
                       customdata=n_by_cat.values,
                       hovertemplate=f"{g}_quality observed: " + "%{y:.1%} (n=%{customdata})<extra></extra>"),
                row=row, col=1,
            )
        fig.update_yaxes(title="share observed", range=[0, 1.05], gridcolor=GRID, row=row, col=1)

    add_panel(1, "year")
    add_panel(2, "detection_price_decile", order=list(range(10)))
    add_panel(3, "delisted_status")
    add_panel(4, "primary_exchange")

    fig.update_layout(
        barmode="group", height=1500,
        title=f"F1-T6: coverage surface (n={n_total:,} in-scope events)",
        plot_bgcolor=SURFACE, paper_bgcolor=SURFACE, font=dict(color=INK),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        margin=dict(t=120, b=140),
        annotations=list(fig.layout.annotations) + [
            dict(text=f"sample: {n_total:,} in-scope events · every bar labeled with its own n on hover "
                      f"· config {C.cfg_hash()} · F1-T6b",
                 xref="paper", yref="paper", x=0, y=-0.05, showarrow=False,
                 font=dict(size=10, color=INK2), align="left")
        ],
    )
    os.makedirs(C.CHARTS, exist_ok=True)
    fig.write_html(OUT_HTML, include_plotlyjs=True)  # D14: no CDN, embed inline
    print(f"wrote {OUT_HTML}")


if __name__ == "__main__":
    main()
