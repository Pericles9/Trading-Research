"""
Phase 4 chart 01 - gap location waterfall.
Source: results/phase_4/artifacts/disk_census.parquet (n=24,723 folders)
+ results/phase_4/artifacts/reconciliation.parquet (matched_to_spine, in_scope, source_file).
"""
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

BLUE = "#2a78d6"
RED = "#e34948"
ORANGE = "#eb6834"
AQUA = "#1baf7a"
GREY = "#9a988f"
GRID = "#e1e0d9"
INK = "#0b0b0b"
INK_SEC = "#52514e"

census = pd.read_parquet("results/phase_4/artifacts/disk_census.parquet")
recon = pd.read_parquet("results/phase_4/artifacts/reconciliation.parquet")
n_total = len(census)

# --- Panel A: all folders by presence_class ---
presence_order = ["both", "trades_only", "quotes_only", "neither"]
presence_counts = census["presence_class"].value_counts().reindex(presence_order, fill_value=0)
presence_color = {"both": AQUA, "trades_only": RED, "quotes_only": ORANGE, "neither": GREY}

# --- Panel B: trades_only (the gap, n=1,606) by matched/in_scope/source_file ---
trades_only = recon[recon["presence_class"] == "trades_only"].copy()
trades_only["in_scope_label"] = trades_only["in_scope"].map({True: "in_scope", False: "out_of_scope"}).fillna("unmatched")
trades_only["bucket"] = trades_only.apply(
    lambda r: "unmatched to spine" if not r["matched_to_spine"]
    else f"{r['in_scope_label']} / {r['source_file']}", axis=1
)
bucket_counts = trades_only["bucket"].value_counts().sort_values(ascending=False)
bucket_color = {
    "unmatched to spine": GREY,
    "in_scope / file1": AQUA,
    "out_of_scope / file2": RED,
    "in_scope / file2": ORANGE,
    "out_of_scope / file1": BLUE,
}

fig = make_subplots(rows=1, cols=2, column_widths=[0.35, 0.65], subplot_titles=(
    "All folders, by disk presence (n=24,723)",
    "The gap (trades_only, n=1,606) located against the spine",
))

fig.add_trace(
    go.Bar(x=presence_order, y=presence_counts.values,
           marker_color=[presence_color[p] for p in presence_order],
           text=[f"{v:,}" for v in presence_counts.values], textposition="outside",
           showlegend=False,
           hovertemplate="%{x}: %{y:,}<extra></extra>"),
    row=1, col=1,
)

fig.add_trace(
    go.Bar(x=bucket_counts.index.tolist(), y=bucket_counts.values,
           marker_color=[bucket_color.get(b, GREY) for b in bucket_counts.index],
           text=[f"{v:,}" for v in bucket_counts.values], textposition="outside",
           showlegend=False,
           hovertemplate="%{x}: %{y:,}<extra></extra>"),
    row=1, col=2,
)

fig.update_xaxes(title="presence_class", gridcolor=GRID, row=1, col=1)
fig.update_xaxes(title="spine match / in_scope / source_file", tickangle=20, gridcolor=GRID, row=1, col=2)
fig.update_yaxes(title="n folders", gridcolor=GRID, row=1, col=1)
fig.update_yaxes(title="n folders", gridcolor=GRID, row=1, col=2)

n_unmatched = int((~trades_only["matched_to_spine"]).sum())
pct_unmatched = 100 * n_unmatched / len(trades_only)

fig.update_layout(
    paper_bgcolor="#fcfcfb", plot_bgcolor="#fcfcfb",
    font=dict(family="system-ui, -apple-system, 'Segoe UI', sans-serif", color=INK, size=12),
    height=620, width=1180,
    title=dict(
        text=(f"Where does the trades/quotes folder gap live relative to the research universe? | "
              f"total folders={n_total:,}, gap (trades_only)={len(trades_only):,}, "
              f"{pct_unmatched:.1f}% of the gap is unmatched to the raw events table entirely"),
        x=0.02, xanchor="left", font=dict(size=13.5),
    ),
    margin=dict(t=110, b=140, l=70, r=30),
    annotations=list(fig.layout.annotations) + [
        dict(
            text=("n on every bar. 'unmatched to spine' = folder has no corresponding row in momentum_events at "
                  "all (114 are 'None'-date orphans, counted separately in presence_class=neither, not in this "
                  "trades_only panel; the remainder are real-dated tickers/dates absent from momentum_events - "
                  "matches CLAUDE.md's documented 1,341-orphan figure). source: research/phase_4/build_chart_01.py, "
                  "disk_census.parquet, reconciliation.parquet"),
            xref="paper", yref="paper", x=0.02, y=-0.28, showarrow=False,
            font=dict(size=10, color=INK_SEC), xanchor="left",
        )
    ],
)

fig.write_html("results/phase_4/charts/01_gap_location_waterfall.html", include_plotlyjs="inline")
print(f"chart 01 written: total={n_total}, trades_only={len(trades_only)}, unmatched={n_unmatched} ({pct_unmatched:.1f}%)")
