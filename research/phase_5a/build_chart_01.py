"""
Phase 5a chart 01 - dev v4 primary cohort representativeness vs. the
clean file1 frame, on momentum_pct.
Source: results/phase_5a/artifacts/sampling_frame.parquet (n=15,349 clean file1),
         results/phase_5a/artifacts/dev_v4_primary_events.parquet (n=50),
         results/phase_5a/artifacts/dev_v4_sidecar_events.parquet (n=6, annotated only).
"""
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

BLUE = "#2a78d6"
RED = "#e34948"
AQUA = "#1baf7a"
GREY = "#9a988f"
GRID = "#e1e0d9"
INK = "#0b0b0b"
INK_SEC = "#52514e"

frame = pd.read_parquet("results/phase_5a/artifacts/sampling_frame.parquet")
frame_clean = frame[frame["clean_window"] == True].copy()  # noqa: E712
primary = pd.read_parquet("results/phase_5a/artifacts/dev_v4_primary_events.parquet")
sidecar = pd.read_parquet("results/phase_5a/artifacts/dev_v4_sidecar_events.parquet")

n_frame = len(frame_clean)
n_primary = len(primary)
n_sidecar = len(sidecar)

N_DECILES = 10
frame_clean["decile"] = pd.qcut(frame_clean["momentum_pct"], N_DECILES, labels=False, duplicates="drop")

fig = make_subplots(
    rows=1, cols=2, column_widths=[0.5, 0.5],
    subplot_titles=(
        f"ECDF: frame (n={n_frame:,}) vs. primary cohort (n={n_primary})",
        "Per-decile: sampled events (5/decile) over the frame's distribution",
    ),
)

# --- Panel A: ECDF, frame vs primary; sidecar as separate rug marks ---
def ecdf(values):
    x = np.sort(values)
    y = np.arange(1, len(x) + 1) / len(x)
    return x, y

fx, fy = ecdf(frame_clean["momentum_pct"].values)
px_, py = ecdf(primary["momentum_pct"].values)

fig.add_trace(go.Scatter(x=fx, y=fy, mode="lines", name="frame (n=15,349)", line=dict(color=GREY, width=2),
                          hovertemplate="frame<br>momentum_pct=%{x:.1f}<br>cum. prob=%{y:.3f}<extra></extra>"), row=1, col=1)
fig.add_trace(go.Scatter(x=px_, y=py, mode="lines+markers", name="primary cohort (n=50)", line=dict(color=BLUE, width=2),
                          marker=dict(size=5),
                          hovertemplate="primary<br>momentum_pct=%{x:.1f}<br>cum. prob=%{y:.3f}<extra></extra>"), row=1, col=1)
fig.add_trace(go.Scatter(
    x=sidecar["momentum_pct"], y=[0.0] * n_sidecar, mode="markers", name=f"flagged sidecar (n={n_sidecar}, not pooled)",
    marker=dict(color=RED, size=10, symbol="triangle-up"),
    hovertemplate="sidecar (not in ECDF)<br>momentum_pct=%{x:.1f}<extra></extra>",
), row=1, col=1)

fig.update_xaxes(title="momentum_pct (log)", type="log", gridcolor=GRID, row=1, col=1)
fig.update_yaxes(title="cumulative probability", gridcolor=GRID, range=[-0.05, 1.05], row=1, col=1)

# --- Panel B: per-decile violin (frame) + strip (primary sample) ---
decile_labels = [str(d) for d in range(N_DECILES)]
for d in range(N_DECILES):
    pool = frame_clean[frame_clean["decile"] == d]["momentum_pct"]
    fig.add_trace(go.Violin(
        x=[str(d)] * len(pool), y=pool, name="frame", legendgroup="frame_violin", showlegend=(d == 0),
        line_color=GREY, fillcolor=GREY, opacity=0.30, points=False, box_visible=False, meanline_visible=False,
        hoverinfo="skip",
    ), row=1, col=2)

primary_sorted = primary.sort_values("decile")
fig.add_trace(go.Scatter(
    x=primary_sorted["decile"].astype(str), y=primary_sorted["momentum_pct"], mode="markers", name="primary sample",
    marker=dict(color=BLUE, size=7, opacity=0.85), legendgroup="primary_strip",
    hovertemplate="decile %{x}<br>momentum_pct=%{y:.1f}<extra></extra>",
), row=1, col=2)

decile_n = primary.groupby("decile").size()
for d in range(N_DECILES):
    fig.add_annotation(
        x=str(d), y=1, text=f"n={int(decile_n.get(d, 0))}", showarrow=False, font=dict(size=9, color=INK_SEC),
        xref="x2", yref="y2 domain", yshift=12, row=1, col=2,
    )

fig.update_xaxes(title="momentum_pct decile", gridcolor=GRID, row=1, col=2)
fig.update_yaxes(title="momentum_pct (log)", type="log", gridcolor=GRID, row=1, col=2)

fig.update_layout(
    violinmode="overlay",
    paper_bgcolor="#fcfcfb", plot_bgcolor="#fcfcfb",
    font=dict(family="system-ui, -apple-system, 'Segoe UI', sans-serif", color=INK, size=12),
    height=700, width=1180,
    title=dict(
        text=(f"Does the 50-event primary cohort represent the clean file1 frame on momentum_pct? | "
              f"frame n={n_frame:,}, primary n={n_primary} (5/decile x 10 deciles), sidecar n={n_sidecar} (annotated only)"),
        x=0.02, xanchor="left", font=dict(size=13.5),
    ),
    legend=dict(bgcolor="rgba(0,0,0,0)"),
    margin=dict(t=110, b=150, l=70, r=30),
    annotations=list(fig.layout.annotations) + [
        dict(
            text=("Panel A: step-ECDF, frame (grey) vs. primary cohort (blue); sidecar events (red triangles) shown as "
                  "position-only rug marks at y=0, never pooled into either ECDF.<br>"
                  "Panel B: violin = frame's per-decile momentum_pct distribution (deciles computed over the clean "
                  "file1 frame, same qcut call as the draw); dots = the 5 primary-cohort events actually drawn in "
                  "each decile, n labeled per decile.<br>"
                  "source: research/phase_5a/build_chart_01.py, sampling_frame.parquet, dev_v4_primary_events.parquet, dev_v4_sidecar_events.parquet"),
            xref="paper", yref="paper", x=0.02, y=-0.20, showarrow=False,
            font=dict(size=10, color=INK_SEC), xanchor="left",
        )
    ],
)

fig.write_html("results/phase_5a/charts/01_dev_v4_representativeness.html", include_plotlyjs="inline")
print(f"chart 01 written: frame n={n_frame}, primary n={n_primary}, sidecar n={n_sidecar}")
