"""
R0 shared chart helpers. Standalone Plotly HTML, one chart per file, n annotated per
bucket, config-hash caption.

Palette and layout helpers carried by value from research/fundamental_exploration/
chart_common.py (itself carried from phase_13 <- phase_11 <- phase_9,
reuse-before-build). Only the config path, chart directory and run label differ.

Embedding is `include_plotlyjs=True` (inline), never "cdn" -- a CDN reference is a live
network call and the environment is offline (D14).

Two deviations from the brief, both following E1's precedent on the identical slips and
both recorded in config/relative_momentum_r0.json:

  theme -- light, matching every chart in this repository's history. The brief's section
    I.5 says "dark theme"; no dark-theme chart exists anywhere in this repo.
  location -- results/relative_momentum/r0/charts/, not the brief header's top-level
    charts/relative_momentum/r0/. E1's brief carried the same slip and it was corrected
    before any code ran, precisely so the repo does not gain a stray top-level charts/
    directory (docs/Research-Library-Map.md, E1 entry; prompts/
    fundamental_exploration_e1.md section 7).
"""
from __future__ import annotations

import hashlib
import pathlib

CFG = "config/relative_momentum_r0.json"
REPO = pathlib.Path(__file__).resolve().parents[2]
CHARTS = "results/relative_momentum/r0/charts"

BLUE, ORANGE, AQUA, YELLOW, GREEN = "#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#008300"
VIOLET, RED, PINK = "#4a3aa7", "#e34948", "#e87ba4"
INK, INK2, GRID, SURFACE = "#0b0b0b", "#52514e", "#e1e0d9", "#fcfcfb"
CAT5 = [BLUE, ORANGE, AQUA, YELLOW, GREEN]  # validated; never exceed 5


def cfg_hash() -> str:
    b = (REPO / CFG).read_bytes().replace(b"\r\n", b"\n")
    return hashlib.sha256(b).hexdigest()[:12]


def rgba(hexc: str, a: float) -> str:
    h = hexc.lstrip("#")
    return f"rgba({int(h[0:2],16)},{int(h[2:4],16)},{int(h[4:6],16)},{a})"


def caption(sample: str, filters: str, extra: str = "") -> str:
    lines = [f"sample: {sample}", f"filters: {filters}"]
    if extra:
        lines.append(extra)
    lines.append(f"config {cfg_hash()} · Relative momentum R0 (scoping, descriptive only)")
    return "<br>".join(lines)


def base_layout(fig, title: str, cap: str, height: int = 660,
                cap_y: float = -0.30, margin_b: int = 210, margin_r: int = 60,
                width: int | None = None):
    fig.update_layout(
        title=dict(text=title, x=0.01, xanchor="left", font=dict(size=16, color=INK)),
        paper_bgcolor="white", plot_bgcolor=SURFACE,
        font=dict(color=INK, size=12),
        margin=dict(l=75, r=margin_r, t=90, b=margin_b),
        height=height, width=width,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
    )
    fig.update_xaxes(gridcolor=GRID, zeroline=False, linecolor=GRID)
    fig.update_yaxes(gridcolor=GRID, zeroline=False, linecolor=GRID)
    fig.add_annotation(text=cap, xref="paper", yref="paper", x=0, y=cap_y,
                       xanchor="left", yanchor="top", showarrow=False, align="left",
                       font=dict(size=11, color=INK2))
    return fig


def write(fig, filename: str) -> str:
    out = REPO / CHARTS / filename
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.write_html(str(out), include_plotlyjs=True, full_html=True)
    return str(out.relative_to(REPO)).replace("\\", "/")
