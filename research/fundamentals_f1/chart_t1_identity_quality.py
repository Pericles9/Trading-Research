"""
Build F1, F1-T1d: chart the resolved_ambiguous and unresolved share by year.

Palette reused from research/phase_9/chart_common.py's validated CAT5 set (documented there
as CVD-safe, lightness-banded, contrast-checked) rather than a new one -- three categories
here read as a status triad (good/warning/critical), which GREEN/YELLOW/RED already encode
in that set.

Usage: .venv/Scripts/python.exe research/fundamentals_f1/chart_t1_identity_quality.py
"""
from __future__ import annotations

import os
import sys

import pandas as pd
import plotly.graph_objects as go

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from research.fundamentals_f1 import common as C  # noqa: E402

GREEN, YELLOW, RED = "#008300", "#eda100", "#e34948"
INK, INK2, GRID, SURFACE = "#0b0b0b", "#52514e", "#e1e0d9", "#fcfcfb"

OUT_HTML = f"{C.CHARTS}/t1_identity_quality_by_year.html"


def main():
    spine = pd.read_parquet(f"{C.ART}/ticker_identity.parquet")
    spine["year"] = spine["event_date_canonical"].str[:4]
    table = spine.groupby(["year", "identity_quality"]).size().unstack(fill_value=0)
    for col in ("resolved_exact", "resolved_ambiguous", "unresolved"):
        if col not in table.columns:
            table[col] = 0
    n_by_year = table.sum(axis=1)
    shares = table.div(n_by_year, axis=0)
    years = list(table.index)

    fig = go.Figure()
    fig.add_bar(x=years, y=shares["resolved_exact"], name="resolved_exact", marker_color=GREEN,
                text=[f"n={n}" for n in table["resolved_exact"]], textposition="none",
                hovertemplate="%{x}: resolved_exact %{y:.1%} (n=%{customdata})<extra></extra>",
                customdata=table["resolved_exact"])
    fig.add_bar(x=years, y=shares["resolved_ambiguous"], name="resolved_ambiguous", marker_color=YELLOW,
                hovertemplate="%{x}: resolved_ambiguous %{y:.1%} (n=%{customdata})<extra></extra>",
                customdata=table["resolved_ambiguous"])
    fig.add_bar(x=years, y=shares["unresolved"], name="unresolved", marker_color=RED,
                hovertemplate="%{x}: unresolved %{y:.1%} (n=%{customdata})<extra></extra>",
                customdata=table["unresolved"])

    for i, year in enumerate(years):
        fig.add_annotation(x=year, y=1.03, text=f"n={n_by_year[year]}", showarrow=False,
                            font=dict(size=11, color=INK2))

    fig.update_layout(
        barmode="stack",
        title="F1-T1: identity resolution quality by year",
        yaxis=dict(title="share of events", tickformat=".0%", range=[0, 1.1], gridcolor=GRID),
        xaxis=dict(title="event year", gridcolor=GRID),
        plot_bgcolor=SURFACE, paper_bgcolor=SURFACE,
        font=dict(color=INK),
        legend=dict(orientation="h", yanchor="bottom", y=1.08, xanchor="left", x=0),
        margin=dict(t=90),
        annotations=list(fig.layout.annotations) + [
            dict(text=f"sample: 20,951 in-scope events, 2,930 tickers · escalation row 2 threshold 5%, "
                      f"combined ambiguous+unresolved {(shares['resolved_ambiguous'].sum()*0 + (table['resolved_ambiguous'].sum()+table['unresolved'].sum())/table.values.sum()):.2%} (does not fire) · "
                      f"config {C.cfg_hash()} · F1-T1",
                 xref="paper", yref="paper", x=0, y=-0.18, showarrow=False, font=dict(size=10, color=INK2))
        ],
    )
    os.makedirs(C.CHARTS, exist_ok=True)
    fig.write_html(OUT_HTML, include_plotlyjs=True)  # D14: no CDN, embed inline
    print(f"wrote {OUT_HTML}")
    print(table)


if __name__ == "__main__":
    main()
