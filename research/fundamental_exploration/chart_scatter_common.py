"""
Shared scatter/strip chart builders for E2's T5/T6/T7 "more interpretable" charts --
one marker per event (never a per-cell aggregate), continuous fundamentals as real
x/y scatter, categorical fundamentals as jittered strips. Detection-price decile
(continuous colorscale, shared coloraxis -> one colorbar per figure) replaces the
old grid's price-decile columns; event year replaces the old grid's rows via
faceting -- so both dimensions of the original year x price-decile x split box grid
survive without a 50-cell layout.

Scattergl (not Scatter) throughout -- up to ~15.7k points per chart, WebGL keeps
render fast. Cooper approved this design (color=price decile, facet=year, jittered
strips for categoricals) 2026-09-17 before any of this was written.

Reuse target for e2_chart_t5_scatter.py / e2_chart_t6_scatter.py / e2_chart_t7_scatter.py.
"""
from __future__ import annotations

import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from research.fundamental_exploration import chart_common as CC

JITTER_SEED = 42
MARKER_SIZE = 3.2
MARKER_OPACITY = 0.42
COLORSCALE = "Viridis"


def _grid_shape(n_panels: int) -> tuple[int, int]:
    cols = min(n_panels, 5)
    rows = -(-n_panels // cols)
    return rows, cols


def _add_scatter_trace(fig, row: int, col: int, x, y, color_vals):
    fig.add_trace(
        go.Scattergl(
            x=x, y=y, mode="markers",
            marker=dict(size=MARKER_SIZE, opacity=MARKER_OPACITY, color=color_vals,
                        coloraxis="coloraxis", line=dict(width=0)),
            hovertemplate="x=%{x:.3f}<br>y=%{y:.3f}<extra></extra>",
            showlegend=False,
        ),
        row=row, col=col,
    )


def continuous_scatter_by_year(
    df, *, x_col: str, y_col: str, color_col: str, title: str, x_title: str, y_title: str,
    log_x: bool, log_y: bool, colorbar_title: str, cap: str,
    out_root: str, out_subdir: str, out_name: str, height: int = 420,
):
    years = sorted(df["year"].dropna().unique())
    rows, cols = _grid_shape(len(years))

    groups = []
    for yr in years:
        g = df[df["year"] == yr].dropna(subset=[x_col, y_col, color_col])
        if log_x:
            g = g[g[x_col] > 0]
        if log_y:
            g = g[g[y_col] > 0]
        groups.append(g)
    subplot_titles = [f"{yr} (n={len(g):,})" for yr, g in zip(years, groups)]

    fig = make_subplots(rows=rows, cols=cols, subplot_titles=subplot_titles,
                         shared_xaxes=True, shared_yaxes=True,
                         horizontal_spacing=0.02, vertical_spacing=0.18)
    for i, g in enumerate(groups):
        r, c = i // cols + 1, i % cols + 1
        x = np.log10(g[x_col]) if log_x else g[x_col]
        y = np.log10(g[y_col]) if log_y else g[y_col]
        _add_scatter_trace(fig, r, c, x, y, g[color_col])
        if r == rows:
            fig.update_xaxes(title=("log10 " + x_title if log_x else x_title), title_font=dict(size=10), row=r, col=c)
        if c == 1:
            fig.update_yaxes(title=("log10 " + y_title if log_y else y_title), row=r, col=c)

    fig.update_layout(coloraxis=dict(colorscale=COLORSCALE, colorbar=dict(title=colorbar_title, len=0.65)))
    CC.base_layout(fig, title, cap, height=height * rows + 190, width=min(1500, 260 * cols + 160),
                    cap_y=-0.10 - 0.02 * rows, margin_b=190 + 10 * rows, margin_r=110, margin_t=110)
    return CC.write(fig, out_subdir, out_name, root=out_root)


def categorical_strip_by_year(
    df, *, cat_col: str, cat_order: list[str], y_col: str, color_col: str, title: str, y_title: str,
    log_y: bool, colorbar_title: str, cap: str,
    out_root: str, out_subdir: str, out_name: str, height: int = 420,
):
    years = sorted(df["year"].dropna().unique())
    rows, cols = _grid_shape(len(years))
    rng = np.random.default_rng(JITTER_SEED)
    cat_index = {c: i for i, c in enumerate(cat_order)}

    groups = []
    for yr in years:
        g = df[df["year"] == yr].dropna(subset=[y_col, color_col])
        g = g[g[cat_col].isin(cat_order)]
        if log_y:
            g = g[g[y_col] > 0]
        groups.append(g)
    subplot_titles = [f"{yr} (n={len(g):,})" for yr, g in zip(years, groups)]

    fig = make_subplots(rows=rows, cols=cols, subplot_titles=subplot_titles,
                         shared_yaxes=True, horizontal_spacing=0.02, vertical_spacing=0.18)
    for i, g in enumerate(groups):
        r, c = i // cols + 1, i % cols + 1
        xi = g[cat_col].map(cat_index).astype(float) + rng.uniform(-0.18, 0.18, len(g))
        y = np.log10(g[y_col]) if log_y else g[y_col]
        _add_scatter_trace(fig, r, c, xi, y, g[color_col])
        fig.update_xaxes(tickmode="array", tickvals=list(range(len(cat_order))), ticktext=cat_order,
                          range=[-0.5, len(cat_order) - 0.5], title_font=dict(size=10), row=r, col=c)
        if c == 1:
            fig.update_yaxes(title=("log10 " + y_title if log_y else y_title), row=r, col=c)

    fig.update_layout(coloraxis=dict(colorscale=COLORSCALE, colorbar=dict(title=colorbar_title, len=0.65)))
    CC.base_layout(fig, title, cap, height=height * rows + 190, width=min(1500, 260 * cols + 160),
                    cap_y=-0.10 - 0.02 * rows, margin_b=190 + 10 * rows, margin_r=110, margin_t=110)
    return CC.write(fig, out_subdir, out_name, root=out_root)
