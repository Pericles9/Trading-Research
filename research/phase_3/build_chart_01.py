"""
Phase 3 chart 01 - missing pattern by classification label.
Source: results/phase_3/artifacts/classification.parquet (n=287)
"""
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

BLUE = "#2a78d6"
RED = "#e34948"
ORANGE = "#eb6834"
AQUA = "#1baf7a"
GRID = "#e1e0d9"
INK = "#0b0b0b"
INK_SEC = "#52514e"

LABEL_COLOR = {
    "backward_missing": BLUE,
    "forward_missing": RED,
    "both_sides": ORANGE,
    "calendar_residue": AQUA,
}
LABELS_ORDER = ["backward_missing", "forward_missing", "both_sides", "calendar_residue"]

df = pd.read_parquet("results/phase_3/artifacts/classification.parquet")
n = len(df)

bitmap_totals = df["bitmap"].value_counts()
bitmap_order = bitmap_totals.index.tolist()

fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.65, 0.35], vertical_spacing=0.05)

for label in LABELS_ORDER:
    sub = df[df["label"] == label]
    counts = sub["bitmap"].value_counts().reindex(bitmap_order, fill_value=0)
    fig.add_trace(
        go.Bar(x=bitmap_order, y=counts.values, name=label, marker_color=LABEL_COLOR[label],
               hovertemplate="bitmap=%{x}<br>" + label + "=%{y}<extra></extra>"),
        row=1, col=1,
    )

rng = np.random.default_rng(42)
for label in LABELS_ORDER:
    sub = df[df["label"] == label]
    x_positions = [bitmap_order.index(b) for b in sub["bitmap"]]
    jitter = rng.uniform(-0.35, 0.35, len(sub))
    fig.add_trace(
        go.Scatter(
            x=[bitmap_order[i] for i in x_positions], y=rng.uniform(0.1, 0.9, len(sub)),
            mode="markers", marker=dict(color=LABEL_COLOR[label], size=6, opacity=0.55),
            name=label, showlegend=False,
            hovertemplate="%{customdata[0]} " + label + "<extra></extra>",
            customdata=sub[["ticker"]].values,
        ),
        row=2, col=1,
    )

fig.update_xaxes(title="presence bitmap (T-3 T-2 T-1 T0 T+1 T+2 T+3), sorted by total count", tickangle=45, gridcolor=GRID, row=2, col=1)
fig.update_yaxes(title="n events", gridcolor=GRID, row=1, col=1)
fig.update_yaxes(title="strip (jittered)", showticklabels=False, gridcolor=GRID, row=2, col=1)

fig.update_layout(
    paper_bgcolor="#fcfcfb", plot_bgcolor="#fcfcfb",
    font=dict(family="system-ui, -apple-system, 'Segoe UI', sans-serif", color=INK, size=12),
    height=760, barmode="stack",
    title=dict(
        text=(f"Do the 287 concentrate in a few structural missing-offset patterns? | n=287, "
              f"22 distinct bitmaps, top-3 = {bitmap_totals.iloc[:3].sum()}/287 ({100*bitmap_totals.iloc[:3].sum()/n:.0f}%)"),
        x=0.02, xanchor="left", font=dict(size=13.5),
    ),
    legend=dict(bgcolor="rgba(0,0,0,0)"),
    margin=dict(t=90, b=140, l=70, r=30),
    annotations=[
        dict(
            text=("1=present, 0=missing at each of the 7 offsets T-3..T+3. Strip shows every one of "
                  "the 287 events, no sub-sampling. source: results/phase_3/t3_classify.py, "
                  "results/phase_3/artifacts/classification.parquet"),
            xref="paper", yref="paper", x=0.02, y=-0.30, showarrow=False,
            font=dict(size=10, color=INK_SEC), xanchor="left",
        )
    ],
)

fig.write_html("results/phase_3/charts/01_missing_pattern_by_class.html", include_plotlyjs="inline")
print(f"chart 01 written: n={n}, distinct bitmaps={len(bitmap_order)}")
