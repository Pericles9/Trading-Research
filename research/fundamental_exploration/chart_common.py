"""
E1 shared chart helpers. Standalone Plotly HTML, one chart per file, n annotated per
bucket, config-hash caption, kaleido PNG verify.

Palette and layout helpers carried by value from research/phase_13/chart_common.py
(itself carried from phase_9/phase_11, reuse-before-build) -- only the config path,
chart directory, phase label, and HTML-embedding mode differ.

**Embedding: `include_plotlyjs=True` (inline), not "cdn".** Phase 13's copy of this
module used `include_plotlyjs="cdn"`, which is a live network reference and
contradicts CLAUDE.md's offline-environment rule (D14) and the research-charts
skill's standing rule ("never reference a CDN"). fundamentals_f1's chart scripts
(chart_t6_coverage.py et al.) already embed inline for this reason -- followed here,
not phase_13's copy. Not corrected upstream; phase_13 is a separate, unmerged branch.
"""
from __future__ import annotations

import hashlib
import json
import pathlib

import numpy as np
import pandas as pd

CFG = "config/fundamental_exploration.json"
ART = "results/fundamental_exploration/artifacts"
CHARTS = "results/fundamental_exploration/charts"

BLUE, ORANGE, AQUA, YELLOW, GREEN = "#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#008300"
VIOLET, RED, PINK = "#4a3aa7", "#e34948", "#e87ba4"
INK, INK2, GRID, SURFACE = "#0b0b0b", "#52514e", "#e1e0d9", "#fcfcfb"
CAT5 = [BLUE, ORANGE, AQUA, YELLOW, GREEN]  # validated; never exceed 5


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
    lines.append(f"config {cfg_hash()} · Fundamental exploration E1 (descriptive only)")
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


def write(fig, subdir: str, name: str) -> str:
    out_dir = pathlib.Path(CHARTS) / subdir
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{name}.html"
    fig.write_html(str(path), include_plotlyjs=True)
    try:
        fig.write_image(str(out_dir / f"{name}.png"), scale=1.35)
        png = "ok"
    except Exception as e:
        png = f"FAILED: {e}"
    print(f"wrote {path} | png {png}")
    return str(path)


def box_from_stats(x_labels, stats_list, name: str, color: str, offsetgroup: str | None = None):
    """A plotly Box trace built from precomputed summary stats (n/p10/p25/median/p75/
    p90/mean), not raw values -- carried from phase_13/chart_common.py verbatim."""
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


def load_json(name: str) -> dict:
    with open(f"{ART}/{name}.json") as f:
        return json.load(f)
