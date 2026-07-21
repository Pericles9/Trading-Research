"""
Phase 3 chart 03 - trades/quotes cohort overlap with classification-label breakdown.
Source: results/phase_3/artifacts/classification.parquet (287 trades cohort, labeled)
+ results/phase_2/artifacts/coverage_class.parquet (386 quotes cohort membership).
"""
import pandas as pd
import plotly.graph_objects as go

BLUE = "#2a78d6"
RED = "#e34948"
ORANGE = "#eb6834"
AQUA = "#1baf7a"
GREY = "#9a988f"
GRID = "#e1e0d9"
INK = "#0b0b0b"
INK_SEC = "#52514e"

LABEL_COLOR = {
    "backward_missing": BLUE,
    "forward_missing": RED,
    "both_sides": ORANGE,
    "calendar_residue": AQUA,
    "not_classified (quotes-only, trades full_window)": GREY,
}
LABEL_ORDER = list(LABEL_COLOR.keys())

trades = pd.read_parquet("results/phase_3/artifacts/classification.parquet")
trades["event_day"] = pd.to_datetime(trades["event_day"])
trades_keys = set(zip(trades["ticker"], trades["event_day"], trades["momentum_pct"].round(2)))
trades_label = trades.set_index(["ticker", "event_day", trades["momentum_pct"].round(2)])["label"]

cc = pd.read_parquet("results/phase_2/artifacts/coverage_class.parquet")
cc["event_date_canonical"] = pd.to_datetime(cc["event_date_canonical"])
cc["mom_2dp"] = cc["momentum_pct"].round(2)
quotes_cohort = cc[(cc["source_file"] == "file1") & (~cc["quotes_full_window"])]
quotes_keys = set(zip(quotes_cohort["ticker"], quotes_cohort["event_date_canonical"], quotes_cohort["mom_2dp"]))

both_keys = trades_keys & quotes_keys
trades_only_keys = trades_keys - quotes_keys
quotes_only_keys = quotes_keys - trades_keys

def label_breakdown(keys):
    counts = {l: 0 for l in LABEL_ORDER}
    for k in keys:
        if k in trades_label.index:
            lbl = trades_label.loc[k]
            counts[lbl] = counts.get(lbl, 0) + 1
        else:
            counts["not_classified (quotes-only, trades full_window)"] += 1
    return counts

groups = {"both": both_keys, "trades-only": trades_only_keys, "quotes-only": quotes_only_keys}
group_names = list(groups.keys())
breakdowns = {g: label_breakdown(k) for g, k in groups.items()}

fig = go.Figure()
for label in LABEL_ORDER:
    ys = [breakdowns[g][label] for g in group_names]
    if sum(ys) == 0:
        continue
    fig.add_trace(go.Bar(
        x=group_names, y=ys, name=label, marker_color=LABEL_COLOR[label],
        text=[str(y) if y else "" for y in ys], textposition="inside",
    ))

totals = {g: sum(breakdowns[g].values()) for g in group_names}

fig.update_xaxes(title="cohort overlap group", gridcolor=GRID)
fig.update_yaxes(title="n events", gridcolor=GRID)

fig.update_layout(
    paper_bgcolor="#fcfcfb", plot_bgcolor="#fcfcfb",
    font=dict(family="system-ui, -apple-system, 'Segoe UI', sans-serif", color=INK, size=12),
    height=600, barmode="stack",
    title=dict(
        text=(f"Do the trades-coverage and quotes-coverage gaps hit the same events? | "
              f"both={totals['both']}, trades-only={totals['trades-only']}, quotes-only={totals['quotes-only']} "
              f"(trades cohort n=287, quotes cohort n=386)"),
        x=0.02, xanchor="left", font=dict(size=13.5),
    ),
    legend=dict(bgcolor="rgba(0,0,0,0)"),
    margin=dict(t=90, b=100, l=70, r=30),
    annotations=[
        dict(
            text=("n per bar segment shown inline. quotes-only events have no trades-side classification "
                  "label (they are full_window on trades, only failing on quotes) - shown as a distinct grey "
                  "segment. source: results/phase_3/build_chart_03.py, classification.parquet, coverage_class.parquet"),
            xref="paper", yref="paper", x=0.02, y=-0.20, showarrow=False,
            font=dict(size=10, color=INK_SEC), xanchor="left",
        )
    ],
)

fig.write_html("results/phase_3/charts/03_trades_quotes_cohort_overlap.html", include_plotlyjs="inline")
print(f"chart 03 written: both={totals['both']}, trades_only={totals['trades-only']}, quotes_only={totals['quotes-only']}")
