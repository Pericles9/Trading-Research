"""
v0 chart helpers. Same palette and layout contract as
research/relative_momentum/chart_common.py (carried from E1 <- phase_13 <- phase_11 <-
phase_9); only the config path and output directory differ.

Plotly embedded inline, never "cdn" -- the environment is offline (D14).
Light theme and a results-tree chart location, matching E1's precedent.
"""
from __future__ import annotations

import hashlib
import pathlib

CFG = "config/participation_exit_overlay.json"
REPO = pathlib.Path(__file__).resolve().parents[2]
CHARTS = "results/participation_exit_overlay/charts"

BLUE, ORANGE, AQUA, YELLOW, GREEN = "#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#008300"
VIOLET, RED, PINK = "#4a3aa7", "#e34948", "#e87ba4"
INK, INK2, GRID, SURFACE = "#0b0b0b", "#52514e", "#e1e0d9", "#fcfcfb"
CAT5 = [BLUE, ORANGE, AQUA, YELLOW, GREEN]


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
    lines.append(f"config {cfg_hash()} · Participation / exit overlay")
    return "<br>".join(lines)


def base_layout(fig, title: str, cap: str, height: int = 680,
                cap_y: float = -0.26, margin_b: int = 230, margin_r: int = 60):
    fig.update_layout(
        title=dict(text=title, x=0.01, xanchor="left", font=dict(size=16, color=INK)),
        paper_bgcolor="white", plot_bgcolor=SURFACE, font=dict(color=INK, size=12),
        margin=dict(l=80, r=margin_r, t=90, b=margin_b), height=height,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0))
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
