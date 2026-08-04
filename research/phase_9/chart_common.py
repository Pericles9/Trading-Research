"""
Phase 9 shared chart helpers.

Standalone Plotly HTML, one chart per file, n annotated per bucket, config-hash
caption, kaleido PNG verify. Palette carried unchanged from the approved 6b/7/8
charts for cross-phase consistency.

Palette note: the full 8-slot categorical order FAILS the normal-vision
adjacent-pair check (#e87ba4 vs #e34948, dE 13.2 < 15). No Phase 9 chart uses
more than 5 categorical series, and the first 5 slots pass every check
(lightness band, chroma floor, CVD separation, normal-vision floor). Phase 9
therefore caps categorical use at CAT5 and never reaches the failing pair.
The sub-3:1 contrast WARN on #1baf7a / #eda100 is relieved by the per-bucket n
labels that the Evidence Standard already requires on every chart.

Deviation from the Chart Contract, recorded here and in REPORT.md: chart 06 is
specified with "n-attrition line on secondary axis". A dual y-scale is the one
encoding the project's visualization standard forbids outright, so attrition
ships as a linked lower panel sharing the x-axis instead - same information,
same chart file, no second y-scale.
"""
from __future__ import annotations

import hashlib
import pathlib

import numpy as np

CFG = "config/phase_9.json"
CHARTS = "results/phase_9/charts"

BLUE, ORANGE, AQUA, YELLOW, GREEN = "#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#008300"
VIOLET, RED, PINK = "#4a3aa7", "#e34948", "#e87ba4"
INK, INK2, GRID, SURFACE = "#0b0b0b", "#52514e", "#e1e0d9", "#fcfcfb"
CAT5 = [BLUE, ORANGE, AQUA, YELLOW, GREEN]          # validated; never exceed 5
DIVERGING = [[0.0, "#b2182b"], [0.5, "#f5f4ef"], [1.0, "#2166ac"]]

STRIP_MAX = 2500        # sub-sample cap for strip overlays; disclosed in caption
STRIP_SEED = 42


def cfg_hash() -> str:
    b = pathlib.Path(CFG).read_bytes().replace(b"\r\n", b"\n")
    return hashlib.sha256(b).hexdigest()[:12]


def rgba(hexc: str, a: float) -> str:
    h = hexc.lstrip("#")
    return f"rgba({int(h[0:2],16)},{int(h[2:4],16)},{int(h[4:6],16)},{a})"


def caption(sample: str, filters: str, extra: str = "") -> str:
    """Wrapped onto its own lines - a single long caption line overflows the
    figure width and collides with the legend at these figure sizes."""
    lines = [f"sample: {sample}", f"filters: {filters}"]
    if extra:
        lines.append(extra)
    lines.append(f"config {cfg_hash()} · Phase 9")
    return "<br>".join(lines)


def subsample(values, cap: int = STRIP_MAX, seed: int = STRIP_SEED):
    """Strip overlays above `cap` points are sub-sampled; callers disclose it."""
    v = np.asarray(values, float)
    v = v[np.isfinite(v)]
    if len(v) <= cap:
        return v, False
    rng = np.random.default_rng(seed)
    return rng.choice(v, cap, replace=False), True


def strip_note(n: int, cap: int = STRIP_MAX) -> str:
    """Caption fragment for a strip/rug overlay - says nothing when the series
    fits under the cap, so a chart never claims a sub-sample it did not take."""
    return f"strip overlay sub-sampled to {cap:,} of {n:,} points" if n > cap else \
           f"all {n:,} points shown"


def base_layout(fig, title: str, cap: str, height: int = 660,
                cap_y: float = -0.30, margin_b: int = 200, margin_r: int = 60,
                width: int | None = None):
    """Caption sits BELOW the legend, not on top of the x-axis title. Callers
    that add a legend put it at y=-0.16; the caption clears it at cap_y."""
    fig.update_layout(
        title=dict(text=title, x=0.01, xanchor="left", font=dict(size=16, color=INK)),
        paper_bgcolor="white", plot_bgcolor=SURFACE,
        font=dict(color=INK, size=12),
        margin=dict(l=75, r=margin_r, t=90, b=margin_b),
        height=height, width=width,
        hovermode="closest",
        annotations=list(fig.layout.annotations) + [dict(
            # yanchor="top" so a multi-line caption grows DOWNWARD from cap_y
            # into the bottom margin; the default centre anchor pushes half the
            # block up into the plot area.
            text=cap, xref="paper", yref="paper", x=0.0, y=cap_y,
            showarrow=False, font=dict(size=9.5, color=INK2), xanchor="left",
            yanchor="top", align="left",
        )],
    )
    fig.update_xaxes(gridcolor=GRID, zerolinecolor=GRID, linecolor=GRID)
    fig.update_yaxes(gridcolor=GRID, zerolinecolor=GRID, linecolor=GRID)
    return fig


def zoom_range(values, lo_q: float = 0.005, hi_q: float = 0.995, pad: float = 0.06):
    """Initial y-range for heavy-tailed markouts, plus the count left outside.

    Outliers are never deleted - every point stays in the figure and
    double-click autoranges to the full extent. This only sets the OPENING
    view, because a log-return axis spanning -3.7 to +5.2 renders the entire
    bulk as a flat line at zero. Callers must disclose the count in the caption.
    """
    v = np.asarray(values, float)
    v = v[np.isfinite(v)]
    if not len(v):
        return None, 0
    lo, hi = float(np.quantile(v, lo_q)), float(np.quantile(v, hi_q))
    if hi <= lo:
        return None, 0
    span = hi - lo
    rng = [lo - pad * span, hi + pad * span]
    outside = int(((v < rng[0]) | (v > rng[1])).sum())
    return rng, outside


def legend_inside(fig, x: float = 0.012, y: float = 0.985, xanchor: str = "left",
                  yanchor: str = "top"):
    """Legend inside the plot area on a translucent panel.

    Bottom legends and the mandatory multi-line caption compete for the same
    strip and collide at these figure sizes; the caption is not optional, so
    the legend moves.
    """
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
