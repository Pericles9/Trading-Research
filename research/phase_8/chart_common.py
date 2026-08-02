"""
Phase 8 shared chart helpers. Standalone Plotly HTML, one per file, n
annotated, config-hash caption, kaleido PNG verify. Palette carried from
the approved 6b charts for cross-phase consistency (dataviz-style: fixed
categorical order, never cycled; one axis; legend for >=2 series;
distributions not centres; outliers shown/disclosed; log where
multiplicative).
"""
from __future__ import annotations

import hashlib

CFG = "config/phase_8.json"
CHARTS = "results/phase_8/charts"

# dataviz palette (fixed categorical order, from approved 6b)
BLUE, ORANGE, AQUA, YELLOW = "#2a78d6", "#eb6834", "#1baf7a", "#eda100"
GREEN, VIOLET, RED, PINK = "#008300", "#4a3aa7", "#e34948", "#e87ba4"
INK, INK2, GRID, SURFACE = "#0b0b0b", "#52514e", "#e1e0d9", "#fcfcfb"
CAT = [BLUE, ORANGE, AQUA, YELLOW, GREEN, VIOLET, RED, PINK]
# diverging pair for markout heatmaps (red<-0->blue, neutral gray midpoint)
DIVERGING = [[0.0, "#b2182b"], [0.5, "#f5f4ef"], [1.0, "#2166ac"]]


def cfg_hash() -> str:
    with open(CFG, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()[:12]


def rgba(hexc: str, a: float) -> str:
    h = hexc.lstrip("#")
    return f"rgba({int(h[0:2],16)},{int(h[2:4],16)},{int(h[4:6],16)},{a})"


def caption(sample: str, filters: str) -> str:
    return f"sample: {sample} · filters: {filters} · config {cfg_hash()} · Phase 8"


def write(fig, name: str) -> str:
    path = f"{CHARTS}/{name}.html"
    fig.write_html(path, include_plotlyjs="cdn")
    try:
        fig.write_image(f"{CHARTS}/{name}.png", scale=1.35)
        png = "ok"
    except Exception as e:  # kaleido verify
        png = f"FAILED: {e}"
    print(f"wrote {path} | png {png}")
    return path


def base_layout(fig, title: str, cap: str, height: int = 640):
    fig.update_layout(
        title=dict(text=title, x=0.01, xanchor="left", font=dict(size=17, color=INK)),
        paper_bgcolor="white", plot_bgcolor=SURFACE,
        font=dict(color=INK, size=12),
        margin=dict(l=70, r=40, t=70, b=120),
        height=height,
        annotations=list(fig.layout.annotations) + [dict(
            text=cap, xref="paper", yref="paper", x=0.0, y=-0.18,
            showarrow=False, font=dict(size=10, color=INK2), xanchor="left",
        )],
    )
    fig.update_xaxes(gridcolor=GRID, zerolinecolor=GRID, linecolor=GRID)
    fig.update_yaxes(gridcolor=GRID, zerolinecolor=GRID, linecolor=GRID)
    return fig
