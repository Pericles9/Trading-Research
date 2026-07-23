"""
Phase 5 chart 02 - momentum_pct distribution, clean vs flagged, faceted by
source_file. Log y-axis (momentum_pct is multiplicative). Violin + strip,
outliers shown (points='all'), no clipping, no smoothing.
Source: results/phase_5/artifacts/spine_window_flags.parquet (n=20,951).
"""
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

AQUA = "#1baf7a"
RED = "#e34948"
GRID = "#e1e0d9"
INK = "#0b0b0b"
INK_SEC = "#52514e"

df = pd.read_parquet("results/phase_5/artifacts/spine_window_flags.parquet")
n_total = len(df)
df["status"] = df["clean_window"].map({True: "clean", False: "flagged"})

fig = make_subplots(
    rows=1, cols=2, column_widths=[0.5, 0.5],
    subplot_titles=(
        f"file1 (n={int((df['source_file']=='file1').sum()):,})",
        f"file2 (n={int((df['source_file']=='file2').sum()):,})",
    ),
)

status_order = ["clean", "flagged"]
status_color = {"clean": AQUA, "flagged": RED}

for col_idx, sf in enumerate(["file1", "file2"], start=1):
    sub = df[df["source_file"] == sf]
    for status in status_order:
        vals = sub.loc[sub["status"] == status, "momentum_pct"]
        if len(vals) == 0:
            continue
        n = len(vals)
        # n baked into the category label itself (not a floating annotation) - robust
        # against log-axis/subplot annotation-placement quirks
        x_label = f"{status}<br>n={n:,}"
        fig.add_trace(
            go.Violin(
                x=[x_label] * len(vals), y=vals, name=status, legendgroup=status,
                showlegend=(col_idx == 1), line_color=status_color[status],
                fillcolor=status_color[status], opacity=0.35,
                points="all", pointpos=0, jitter=0.35,
                marker=dict(size=3, opacity=0.35, color=status_color[status]),
                box_visible=True, meanline_visible=True,
                hovertemplate=f"{sf} {status}<br>momentum_pct=%{{y:.1f}}<extra></extra>",
            ),
            row=1, col=col_idx,
        )

fig.update_yaxes(title="momentum_pct (log)", type="log", gridcolor=GRID, row=1, col=1)
fig.update_yaxes(title="momentum_pct (log)", type="log", gridcolor=GRID, row=1, col=2)
fig.update_xaxes(title=None, gridcolor=GRID, row=1, col=1)
fig.update_xaxes(title=None, gridcolor=GRID, row=1, col=2)

fig.update_layout(
    violinmode="group",
    paper_bgcolor="#fcfcfb", plot_bgcolor="#fcfcfb",
    font=dict(family="system-ui, -apple-system, 'Segoe UI', sans-serif", color=INK, size=12),
    height=650, width=1180,
    title=dict(
        text="Does flagging bias the research universe on momentum_pct? | full distributions shown, no clipping, log y-axis",
        x=0.02, xanchor="left", font=dict(size=13.5),
    ),
    legend=dict(bgcolor="rgba(0,0,0,0)"),
    margin=dict(t=110, b=100, l=70, r=30),
    annotations=list(fig.layout.annotations) + [
        dict(
            text=("Violin + strip (all points shown), box+mean overlay. file2 has effectively no 'clean' group<br>"
                  "(1/5,188) so its comparison is degenerate by construction (Phase 5 Amendment 4) - the file1 "
                  "panel is the one that answers the bias question the chart contract intends. "
                  "source: research/phase_5/build_chart_02.py, spine_window_flags.parquet"),
            xref="paper", yref="paper", x=0.02, y=-0.20, showarrow=False,
            font=dict(size=10, color=INK_SEC), xanchor="left",
        )
    ],
)

fig.write_html("results/phase_5/charts/02_momentum_pct_clean_vs_flagged.html", include_plotlyjs="inline")
print(f"chart 02 written: n={n_total}")
