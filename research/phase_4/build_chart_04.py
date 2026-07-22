"""
Phase 4 chart 04 - trades x quotes label agreement matrix, dual cohort (n=259).
Source: results/phase_3/artifacts/classification.parquet (trades label, Phase 3's precedence)
+ results/phase_4/artifacts/classification.parquet (quotes label, bitmap-first).
Joined on ticker + event_day + momentum_pct(2dp) - the 259 events in both the
287 trades cohort and the 386 quotes cohort (T1 overlap_both).
"""
import pandas as pd
import plotly.graph_objects as go

GRID = "#e1e0d9"
INK = "#0b0b0b"
INK_SEC = "#52514e"

trades = pd.read_parquet("results/phase_3/artifacts/classification.parquet")
quotes = pd.read_parquet("results/phase_4/artifacts/classification.parquet")

trades["mom_2dp"] = trades["momentum_pct"].round(2)
quotes["mom_2dp"] = quotes["momentum_pct"].round(2)

both = trades[["ticker", "event_day", "mom_2dp", "label"]].merge(
    quotes[["ticker", "event_day", "mom_2dp", "label"]],
    on=["ticker", "event_day", "mom_2dp"], how="inner", suffixes=("_trades", "_quotes"),
)
n_both = len(both)

trades_label_order = ["backward_missing", "forward_missing", "both_sides", "calendar_residue", "archive_edge"]
quotes_label_order = ["backward_missing", "forward_missing", "both_sides", "archive_edge"]
trades_label_order = [l for l in trades_label_order if l in both["label_trades"].unique()]
quotes_label_order = [l for l in quotes_label_order if l in both["label_quotes"].unique()]

matrix = pd.crosstab(both["label_quotes"], both["label_trades"]).reindex(
    index=quotes_label_order, columns=trades_label_order, fill_value=0
)

z = matrix.values
text = [[str(v) for v in row] for row in z]

on_diagonal_labels = set(trades_label_order) & set(quotes_label_order)
n_diag = sum(int(matrix.loc[l, l]) for l in on_diagonal_labels if l in matrix.index and l in matrix.columns)
pct_diag = 100 * n_diag / n_both if n_both else 0

fig = go.Figure(data=go.Heatmap(
    z=z, x=trades_label_order, y=quotes_label_order, text=text, texttemplate="%{text}",
    colorscale=[[0, "#fcfcfb"], [1, "#2a78d6"]],
    hovertemplate="trades=%{x}<br>quotes=%{y}<br>n=%{z}<extra></extra>",
    colorbar=dict(title="n events"),
))

fig.update_xaxes(title="trades-side label (Phase 3 precedence)", gridcolor=GRID)
fig.update_yaxes(title="quotes-side label (bitmap-first)", gridcolor=GRID)

fig.update_layout(
    paper_bgcolor="#fcfcfb", plot_bgcolor="#fcfcfb",
    font=dict(family="system-ui, -apple-system, 'Segoe UI', sans-serif", color=INK, size=12),
    height=620, width=900,
    title=dict(
        text=(f"For the 259 dual-cohort events, do trades-side and quotes-side labels agree? | "
              f"n={n_both}, same-name-label agreement={n_diag}/{n_both} ({pct_diag:.0f}%)"),
        x=0.02, xanchor="left", font=dict(size=13.5),
    ),
    margin=dict(t=90, b=90, l=140, r=30),
    annotations=[
        dict(
            text=(f"n in every cell. trades label uses Phase 3's calendar_residue-intercepting precedence; "
                  f"quotes label is this phase's bitmap-first primary classification - the two use different "
                  f"precedence rules by design (see T5), so off-diagonal mass partly reflects that methodology "
                  f"difference, not only independent causes. source: research/phase_4/build_chart_04.py, "
                  f"results/phase_3/artifacts/classification.parquet, results/phase_4/artifacts/classification.parquet"),
            xref="paper", yref="paper", x=0.02, y=-0.22, showarrow=False,
            font=dict(size=10, color=INK_SEC), xanchor="left",
        )
    ],
)

fig.write_html("results/phase_4/charts/04_trades_quotes_label_matrix.html", include_plotlyjs="inline")
print(f"chart 04 written: n_both={n_both} (expected 259), same-name agreement={n_diag} ({pct_diag:.0f}%)")
