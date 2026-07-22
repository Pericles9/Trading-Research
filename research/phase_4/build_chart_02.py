"""
Phase 4 chart 02 - quotes missing pattern by class, vs. the trades side.
Source: results/phase_4/artifacts/classification.parquet (n=386, bitmap-first label)
+ results/phase_3/artifacts/classification.parquet (n=287, Phase 3's label) for the side panel.
"""
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

BLUE = "#2a78d6"
RED = "#e34948"
ORANGE = "#eb6834"
AQUA = "#1baf7a"
PURPLE = "#8b5fbf"
GRID = "#e1e0d9"
INK = "#0b0b0b"
INK_SEC = "#52514e"

LABEL_COLOR = {
    "backward_missing": BLUE,
    "forward_missing": RED,
    "both_sides": ORANGE,
    "calendar_residue": AQUA,
    "archive_edge": PURPLE,
}

quotes = pd.read_parquet("results/phase_4/artifacts/classification.parquet")
trades = pd.read_parquet("results/phase_3/artifacts/classification.parquet")

n_quotes, n_trades = len(quotes), len(trades)

quotes_bitmap_order = quotes["bitmap"].value_counts().index.tolist()
trades_bitmap_order = trades["bitmap"].value_counts().index.tolist()

fig = make_subplots(
    rows=1, cols=2, column_widths=[0.62, 0.38],
    subplot_titles=(f"Quotes cohort (n={n_quotes}, bitmap-first label)", f"Trades cohort (n={n_trades}, Phase 3 label)"),
)

quotes_labels_present = [l for l in LABEL_COLOR if l in quotes["label"].unique()]
for label in quotes_labels_present:
    sub = quotes[quotes["label"] == label]
    counts = sub["bitmap"].value_counts().reindex(quotes_bitmap_order, fill_value=0)
    fig.add_trace(
        go.Bar(x=quotes_bitmap_order, y=counts.values, name=label, marker_color=LABEL_COLOR[label],
               legendgroup=label,
               hovertemplate="bitmap=%{x}<br>" + label + "=%{y}<extra></extra>"),
        row=1, col=1,
    )

trades_labels_present = [l for l in LABEL_COLOR if l in trades["label"].unique()]
for label in trades_labels_present:
    sub = trades[trades["label"] == label]
    counts = sub["bitmap"].value_counts().reindex(trades_bitmap_order, fill_value=0)
    fig.add_trace(
        go.Bar(x=trades_bitmap_order, y=counts.values, name=label, marker_color=LABEL_COLOR[label],
               legendgroup=label, showlegend=(label not in quotes_labels_present),
               hovertemplate="bitmap=%{x}<br>" + label + "=%{y}<extra></extra>"),
        row=1, col=2,
    )

fig.update_xaxes(title="bitmap (T-3..T+3)", tickangle=45, gridcolor=GRID, tickfont=dict(size=8), row=1, col=1)
fig.update_xaxes(title="bitmap (T-3..T+3)", tickangle=45, gridcolor=GRID, tickfont=dict(size=8), row=1, col=2)
fig.update_yaxes(title="n events", gridcolor=GRID, row=1, col=1)
fig.update_yaxes(title="n events", gridcolor=GRID, row=1, col=2)

quotes_top1_pct = 100 * quotes["bitmap"].value_counts().iloc[0] / n_quotes
trades_top1_pct = 100 * trades["bitmap"].value_counts().iloc[0] / n_trades

fig.update_layout(
    paper_bgcolor="#fcfcfb", plot_bgcolor="#fcfcfb",
    font=dict(family="system-ui, -apple-system, 'Segoe UI', sans-serif", color=INK, size=12),
    height=620, width=1180, barmode="stack",
    title=dict(
        text=(f"Do quotes-side gap patterns mirror the trades-side patterns? | "
              f"quotes: {len(quotes_bitmap_order)} distinct patterns, top pattern={quotes_top1_pct:.0f}% "
              f"vs. trades: {len(trades_bitmap_order)} distinct patterns, top pattern={trades_top1_pct:.0f}%"),
        x=0.02, xanchor="left", font=dict(size=13.5),
    ),
    legend=dict(bgcolor="rgba(0,0,0,0)"),
    margin=dict(t=110, b=140, l=70, r=30),
    annotations=list(fig.layout.annotations) + [
        dict(
            text=("1=present, 0=missing at each of the 7 offsets T-3..T+3, both panels ordered by descending "
                  "frequency within their own cohort. Quotes label is bitmap-first (this phase's primary "
                  "classification); trades label is Phase 3's original. source: research/phase_4/build_chart_02.py, "
                  "classification.parquet (phase 4 + phase 3)"),
            xref="paper", yref="paper", x=0.02, y=-0.30, showarrow=False,
            font=dict(size=10, color=INK_SEC), xanchor="left",
        )
    ],
)

fig.write_html("results/phase_4/charts/02_quotes_missing_pattern_by_class.html", include_plotlyjs="inline")
print(f"chart 02 written: quotes n={n_quotes} ({len(quotes_bitmap_order)} patterns), trades n={n_trades} ({len(trades_bitmap_order)} patterns)")
