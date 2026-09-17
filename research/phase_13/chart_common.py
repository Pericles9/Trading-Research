"""
Phase 13 shared chart helpers.

Standalone Plotly HTML, one chart per file, n annotated per bucket, config-hash
caption, kaleido PNG verify. Palette, layout helpers, and the CAT5 cap carried
unchanged from the approved Phase 9/11 charts (reuse-before-build) -- only the
config path, chart directory, and phase label differ.

Per Cooper's 2026-09-13 amendment (exploratory, no kill condition): no chart in
this phase draws a reference/threshold line, pass/fail shading, or a "winner"
annotation on any split. Chart 06 in particular must not reintroduce one.
"""
from __future__ import annotations

import hashlib
import json
import pathlib

import numpy as np
import pandas as pd

CFG = "config/phase_13.json"
ART = "results/phase_13/artifacts"
CHARTS = "results/phase_13/charts"

BLUE, ORANGE, AQUA, YELLOW, GREEN = "#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#008300"
VIOLET, RED, PINK = "#4a3aa7", "#e34948", "#e87ba4"
INK, INK2, GRID, SURFACE = "#0b0b0b", "#52514e", "#e1e0d9", "#fcfcfb"
CAT5 = [BLUE, ORANGE, AQUA, YELLOW, GREEN]          # validated; never exceed 5


def cfg_hash() -> str:
    b = pathlib.Path(CFG).read_bytes().replace(b"\r\n", b"\n")
    return hashlib.sha256(b).hexdigest()[:12]


def rgba(hexc: str, a: float) -> str:
    h = hexc.lstrip("#")
    return f"rgba({int(h[0:2],16)},{int(h[2:4],16)},{int(h[4:6],16)},{a})"


def caption(sample: str, filters: str, extra: str = "") -> str:
    lines = [f"sample: {sample}", f"filters: {filters}"]
    if extra:
        lines.append(extra)
    lines.append(f"config {cfg_hash()} · Phase 13")
    return "<br>".join(lines)


def base_layout(fig, title: str, cap: str, height: int = 660,
                cap_y: float = -0.30, margin_b: int = 200, margin_r: int = 60,
                width: int | None = None):
    fig.update_layout(
        title=dict(text=title, x=0.01, xanchor="left", font=dict(size=16, color=INK)),
        paper_bgcolor="white", plot_bgcolor=SURFACE,
        font=dict(color=INK, size=12),
        margin=dict(l=75, r=margin_r, t=90, b=margin_b),
        height=height, width=width,
        hovermode="closest",
        annotations=list(fig.layout.annotations) + [dict(
            text=cap, xref="paper", yref="paper", x=0.0, y=cap_y,
            showarrow=False, font=dict(size=9.5, color=INK2), xanchor="left",
            yanchor="top", align="left",
        )],
    )
    fig.update_xaxes(gridcolor=GRID, zerolinecolor=GRID, linecolor=GRID)
    fig.update_yaxes(gridcolor=GRID, zerolinecolor=GRID, linecolor=GRID)
    return fig


def legend_inside(fig, x: float = 0.012, y: float = 0.985, xanchor: str = "left",
                  yanchor: str = "top"):
    fig.update_layout(legend=dict(
        x=x, y=y, xanchor=xanchor, yanchor=yanchor,
        bgcolor="rgba(255,255,255,0.86)", bordercolor=GRID, borderwidth=1,
        font=dict(size=11)))
    return fig


def write(fig, name: str) -> str:
    pathlib.Path(CHARTS).mkdir(parents=True, exist_ok=True)
    path = f"{CHARTS}/{name}.html"
    fig.write_html(path, include_plotlyjs="cdn")
    try:
        fig.write_image(f"{CHARTS}/{name}.png", scale=1.35)
        png = "ok"
    except Exception as e:
        png = f"FAILED: {e}"
    print(f"wrote {path} | png {png}")
    return path


def load_p0() -> pd.DataFrame:
    df = pd.read_parquet(f"{ART}/p0_outcome.parquet")
    df["event_year"] = df["event_id"].str.extract(r"_(\d{4})-\d{2}-\d{2}_")[0]
    return df


def load_json(name: str) -> dict:
    with open(f"{ART}/{name}.json") as f:
        return json.load(f)


def box_from_stats(x_labels, stats_list, name: str, color: str, offsetgroup: str | None = None):
    """A plotly Box trace built from precomputed summary stats (n/p10/p25/median/
    p75/p90/mean), not raw values -- this program's summaries carry quantiles, not
    per-event arrays, by design (n per bucket is always reported; the raw arrays
    are not re-serialized into every chart's data payload)."""
    import plotly.graph_objects as go
    xs, q1, med, q3, lo, hi, mean, ns = [], [], [], [], [], [], [], []
    for x, s in zip(x_labels, stats_list):
        if not s or s.get("n", 0) == 0:
            continue
        xs.append(x)
        q1.append(s["p25"]); med.append(s["median"]); q3.append(s["p75"])
        lo.append(s["p10"]); hi.append(s["p90"]); mean.append(s["mean"])
        ns.append(s["n"])
    return go.Box(
        x=xs, q1=q1, median=med, q3=q3, lowerfence=lo, upperfence=hi, mean=mean,
        name=name, marker_color=color, offsetgroup=offsetgroup,
        customdata=np.array(ns).reshape(-1, 1),
        hovertemplate=(f"{name}<br>%{{x}}<br>n=%{{customdata[0]:,}}"
                       "<br>p10 %{lowerfence:.2f} · p25 %{q1:.2f} · median %{median:.2f} "
                       "· p75 %{q3:.2f} · p90 %{upperfence:.2f}<extra></extra>"),
    )


def small_multiples_split_chart(split_key: str, split_label: str, filename: str,
                                title: str, caption_extra: str, direction_note: str):
    """Shared builder for charts 03/04/05: small multiples, rows=event year,
    columns=detection-price decile, one panel per (year, decile) cell, box traces
    for the split's two sides. A horizon selector and a metric (MFE/MAE) selector
    are exposed as buttons rather than drawn as 8 separate static charts.

    No reference line, no shading, no "winner" label on either side -- both sides
    are drawn in neutral, non-ranked colors (escalation rows 2/3)."""
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots

    HORIZONS = [5, 15, 30, 60]
    METRICS = [("mfe_cost_mult", "MFE cost-multiple"), ("mae_cost_mult", "MAE cost-multiple")]
    t3 = load_json("t3_partition_summary")
    split = t3["splits"][split_key]

    years = sorted({c["year"] for c in split[f"horizon_{HORIZONS[0]}"]})
    deciles = sorted({c["price_decile"] for c in split[f"horizon_{HORIZONS[0]}"]})
    nrows, ncols = len(years), len(deciles)

    subplot_titles = [f"D{d}" if r == 0 else "" for r in range(nrows) for d in deciles]
    fig = make_subplots(rows=nrows, cols=ncols, subplot_titles=subplot_titles,
                        horizontal_spacing=0.006, vertical_spacing=0.018,
                        shared_yaxes=False)

    # trace_membership[(horizon, metric)] -> list of trace indices belonging to that
    # combo, so the horizon/metric buttons can build a single boolean visibility mask.
    trace_membership: dict[tuple[int, str], list[int]] = {(h, m[0]): [] for h in HORIZONS for m in METRICS}
    y_ranges: dict[tuple[int, str], list[float]] = {}
    trace_count = 0

    for h in HORIZONS:
        cells = {(c["year"], c["price_decile"], c["split_value"]): c for c in split[f"horizon_{h}"]}
        for metric_key, metric_label in METRICS:
            combo_vals = []
            for ri, year in enumerate(years):
                for ci, decile in enumerate(deciles):
                    for side, color in ((True, BLUE), (False, ORANGE)):
                        cell = cells.get((year, decile, side))
                        stats = cell[metric_key] if cell else None
                        visible = (h == 15 and metric_key == "mfe_cost_mult")
                        if stats and stats.get("n", 0) > 0:
                            combo_vals.extend([stats["p10"], stats["p90"]])
                            trace = box_from_stats(
                                [f"D{decile}"], [stats],
                                f"{split_label}: {'above' if side else 'below'} split",
                                color, offsetgroup="above" if side else "below",
                            )
                        else:
                            trace = go.Box(x=[], y=[], name=f"{split_label}: {'above' if side else 'below'} split",
                                          marker_color=color)
                        trace.visible = visible
                        trace.showlegend = bool(visible and ri == 0 and ci == 0)
                        fig.add_trace(trace, row=ri + 1, col=ci + 1)
                        trace_membership[(h, metric_key)].append(trace_count)
                        trace_count += 1
            if combo_vals:
                lo, hi = min(combo_vals), max(combo_vals)
                pad = 0.08 * (hi - lo) if hi > lo else 1.0
                y_ranges[(h, metric_key)] = [lo - pad, hi + pad]

    for ri in range(nrows):
        for ci in range(ncols):
            idx = ri * ncols + ci
            fig.update_xaxes(showticklabels=False, row=ri + 1, col=ci + 1)
            fig.update_yaxes(showticklabels=(ci == 0), row=ri + 1, col=ci + 1)
            if ci == 0:
                fig.update_yaxes(title_text=years[ri], title_font=dict(size=10), row=ri + 1, col=ci + 1)

    def yaxis_range_patch(h: int, metric_key: str) -> dict:
        rng = y_ranges.get((h, metric_key), [0, 1])
        patch = {}
        for i in range(1, nrows * ncols + 1):
            key = "yaxis" if i == 1 else f"yaxis{i}"
            patch[f"{key}.range"] = rng
        return patch

    def visibility_mask(h: int, metric_key: str) -> list[bool]:
        target = set(trace_membership[(h, metric_key)])
        return [i in target for i in range(trace_count)]

    horizon_buttons = [
        dict(label=f"{h} min", method="update",
             args=[{"visible": visibility_mask(h, "mfe_cost_mult")}, yaxis_range_patch(h, "mfe_cost_mult")])
        for h in HORIZONS
    ]
    metric_buttons = [
        dict(label=label, method="update",
             args=[{"visible": visibility_mask(15, key)}, yaxis_range_patch(15, key)])
        for key, label in METRICS
    ]

    fig.update_layout(
        updatemenus=[
            dict(type="buttons", direction="right", x=0.0, y=1.10, xanchor="left",
                 buttons=horizon_buttons, showactive=True, pad=dict(r=6)),
            dict(type="buttons", direction="right", x=0.45, y=1.10, xanchor="left",
                 buttons=metric_buttons, showactive=True, pad=dict(r=6)),
        ],
        boxmode="group",
    )
    fig.add_annotation(text="horizon:", x=-0.02, y=1.10, xref="paper", yref="paper",
                       showarrow=False, xanchor="right", font=dict(size=10))
    fig.add_annotation(text="metric:", x=0.43, y=1.10, xref="paper", yref="paper",
                       showarrow=False, xanchor="right", font=dict(size=10))

    import textwrap
    n_15_mfe = sum(c["mfe_cost_mult"].get("n", 0) for c in split["horizon_15"])
    wrapped = textwrap.wrap(caption_extra + " " + direction_note, width=118)
    cap = caption(
        sample=f"{split_label}, n≈{n_15_mfe:,} covered events at 15 min (varies by horizon/metric toggle).",
        filters=f"Rows = event year ({years[0]}-{years[-1]}), columns = detection-price decile "
                f"(D0=cheapest .. D{deciles[-1]}=most expensive). Cells below "
                "config.cross_cuts.min_cell_n_log_threshold are thin or empty boxes, not hidden.",
        extra="<br>        ".join(wrapped),
    )
    fig_height = 110 * nrows + 250
    base_layout(fig, title, cap, height=fig_height, width=140 * ncols + 120,
               cap_y=-0.05 - 0.012 * nrows - 90 / fig_height, margin_b=200 + 8 * nrows, margin_r=20)
    fig.update_layout(margin_t=110, showlegend=True,
                      legend=dict(orientation="h", y=1.0 + 6.0 / fig_height, x=0.0,
                                  xanchor="left", font=dict(size=10),
                                  bgcolor="rgba(255,255,255,0.86)", bordercolor=GRID, borderwidth=1))
    write(fig, filename)
