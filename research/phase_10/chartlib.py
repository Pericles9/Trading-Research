"""
Phase 10 chart helpers.

Standing chart rules (CLAUDE.md + Agent_Prompt_Standard §9): Plotly, standalone
HTML, one chart per file, n annotated per bucket always, distribution not just
centre, no smoothing, log axes where the data is multiplicative, outliers shown
and never clipped, every chart captioned with sample / filters / config hash.
Every chart writes a kaleido-verified .png sibling.

Palette: categorical slots 1, 2, 3, 7 of the validated reference palette
(blue / orange / aqua / violet). Verified with the data-viz validator under
--pairs all in light mode: all-pairs CVD worst ΔE 9.2 (deutan), normal-vision
worst ΔE 16.3, both above their floors. Aqua sits below 3:1 contrast on the
light surface, so the relief rule applies -- every series carrying it is also
direct-labeled with its n, which the chart contract requires anyway.
"""
from __future__ import annotations

import os

import numpy as np
import plotly.graph_objects as go

ARM_A = "#2a78d6"   # slot 1, blue
ARM_B = "#eb6834"   # slot 2, orange
SIDECAR = "#1baf7a"  # slot 3, aqua
ROWCAP = "#4a3aa7"  # slot 7, violet

ARM_COLOR = {"A": ARM_A, "B": ARM_B}
POP_COLOR = {
    "pooled_analysis_cohort": None,   # takes the arm colour
    "row_cap_census": ROWCAP,
    "dev_v4_sidecar": SIDECAR,
}
POP_LABEL = {
    "pooled_analysis_cohort": "analysis cohort (primary + extension)",
    "row_cap_census": "row_cap_census (never pooled)",
    "dev_v4_sidecar": "dev_v4_sidecar (never pooled)",
}

GRID = "#e2e2df"
INK = "#0b0b0b"
INK2 = "#52514e"
SURFACE = "#fcfcfb"

LAYOUT = dict(
    template="plotly_white",
    paper_bgcolor=SURFACE,
    plot_bgcolor=SURFACE,
    font=dict(family="Inter, Segoe UI, system-ui, sans-serif", size=13, color=INK),
    margin=dict(l=90, r=50, t=115, b=280),
    hovermode="closest",
    # Legend below the plot, above the caption: with two-line subplot titles a
    # top legend collides with them.
    legend=dict(orientation="h", yanchor="top", y=-0.20, xanchor="left", x=0,
                bgcolor="rgba(0,0,0,0)", font=dict(size=11.5)),
)


def caption(sample: str, filters: str, chash: str, extra: str = "") -> str:
    bits = [f"<b>Sample:</b> {sample}", f"<b>Filters:</b> {filters}"]
    if extra:
        bits.append(extra)
    bits.append(f"<b>config_hash:</b> {chash}")
    return "<br>".join(bits)


def finish(fig: go.Figure, title: str, subtitle: str, cap: str,
           height: int = 860, width: int = 1320) -> go.Figure:
    fig.update_layout(
        **LAYOUT,
        height=height, width=width,
        title=dict(
            text=f"<b>{title}</b><br><span style='font-size:12.5px;color:{INK2}'>{subtitle}</span>",
            x=0.0, xanchor="left", y=0.97, yanchor="top",
        ),
        annotations=list(fig.layout.annotations or []) + [dict(
            text=cap, xref="paper", yref="paper", x=0, y=-0.40,
            xanchor="left", yanchor="top", showarrow=False, align="left",
            font=dict(size=11, color=INK2),
        )],
    )
    # nudge subplot titles clear of the main title block
    for a in fig.layout.annotations:
        if getattr(a, "yref", None) == "paper" and getattr(a, "y", 0) == 1.0:
            a.update(y=1.005, font=dict(size=13, color=INK))
    fig.update_xaxes(gridcolor=GRID, zerolinecolor=GRID, linecolor=GRID, ticks="outside")
    fig.update_yaxes(gridcolor=GRID, zerolinecolor=GRID, linecolor=GRID, ticks="outside")
    return fig


def write(fig: go.Figure, out_dir: str, name: str) -> dict:
    """Write standalone HTML + kaleido-verified PNG sibling."""
    os.makedirs(out_dir, exist_ok=True)
    html = os.path.join(out_dir, f"{name}.html")
    png = os.path.join(out_dir, f"{name}.png")
    fig.write_html(html, include_plotlyjs="cdn", full_html=True,
                   config={"displaylogo": False, "responsive": False})
    fig.write_image(png, scale=2)
    ok = os.path.exists(png) and os.path.getsize(png) > 5000
    print(f"  {name}.html ({os.path.getsize(html)/1024:.0f} KB)  "
          f"png={'OK' if ok else 'FAILED'} ({os.path.getsize(png)/1024:.0f} KB)")
    return {"chart": f"{name}.html", "png": f"{name}.png", "kaleido_verified": bool(ok),
            "html_bytes": os.path.getsize(html), "png_bytes": os.path.getsize(png)}


def ecdf(a) -> tuple[np.ndarray, np.ndarray]:
    """Empirical CDF. Every point retained -- no binning, no clipping."""
    a = np.asarray(a, dtype=float)
    a = np.sort(a[np.isfinite(a)])
    if a.size == 0:
        return a, a
    return a, np.arange(1, a.size + 1) / a.size


def ecdf_trace(a, name: str, color: str, dash: str | None = None,
               legendgroup: str | None = None, showlegend: bool = True) -> go.Scatter:
    x, y = ecdf(a)
    return go.Scatter(
        x=x, y=y, mode="lines", name=f"{name} (n={x.size:,})",
        line=dict(color=color, width=2, dash=dash),
        legendgroup=legendgroup or name, showlegend=showlegend,
        hovertemplate=f"{name}<br>%{{x:,.4g}}<br>cum. share %{{y:.3f}}<extra></extra>",
    )


def strip_y(n: int, centre: float, spread: float, seed: int = 42) -> np.ndarray:
    """Deterministic jitter for a strip overlay."""
    return centre + np.random.default_rng(seed).uniform(-spread, spread, n)


def vline(fig, x: float, text: str, color: str = INK2, row=None, col=None) -> None:
    kw = {} if row is None else {"row": row, "col": col}
    fig.add_vline(x=x, line=dict(color=color, width=1.5, dash="dot"),
                  annotation_text=text, annotation_position="top",
                  annotation_font=dict(size=10.5, color=color), **kw)


def n_note(fig, text: str, x: float, y: float, row=None, col=None,
           xref="x", yref="paper") -> None:
    kw = {} if row is None else {"row": row, "col": col}
    fig.add_annotation(text=text, x=x, y=y, xref=xref, yref=yref, showarrow=False,
                       font=dict(size=11, color=INK2), align="left",
                       xanchor="left", yanchor="top", **kw)
