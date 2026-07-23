"""
Phase 5 chart 03 - flag label composition, trades vs quotes side.
not_classified shown explicitly (it is the file2 population under flag-
and-carry, Phase 5 Amendment 4 - not treated as the chart's failure
appearance per the amendment).
Source: results/phase_5/artifacts/spine_window_flags.parquet (n=20,951).
"""
import pandas as pd
import plotly.graph_objects as go

BLUE = "#2a78d6"
ORANGE = "#eb6834"
GRID = "#e1e0d9"
INK = "#0b0b0b"
INK_SEC = "#52514e"

df = pd.read_parquet("results/phase_5/artifacts/spine_window_flags.parquet")
n_total = len(df)

trades_counts = df["trades_gap_label"].value_counts()
quotes_counts = df["quotes_gap_label"].value_counts()

all_labels = sorted(set(trades_counts.index) | set(quotes_counts.index))
# not_classified last so it reads as the "everything else" bucket, other labels by descending combined count
label_order = sorted(
    [l for l in all_labels if l != "not_classified"],
    key=lambda l: -(trades_counts.get(l, 0) + quotes_counts.get(l, 0)),
) + (["not_classified"] if "not_classified" in all_labels else [])

trades_vals = [int(trades_counts.get(l, 0)) for l in label_order]
quotes_vals = [int(quotes_counts.get(l, 0)) for l in label_order]

fig = go.Figure()
fig.add_trace(go.Bar(
    x=label_order, y=trades_vals, name="trades", marker_color=BLUE,
    text=[f"{v:,}" for v in trades_vals], textposition="outside", textfont=dict(size=9),
    hovertemplate="trades %{x}: %{y:,}<extra></extra>",
))
fig.add_trace(go.Bar(
    x=label_order, y=quotes_vals, name="quotes", marker_color=ORANGE,
    text=[f"{v:,}" for v in quotes_vals], textposition="outside", textfont=dict(size=9),
    hovertemplate="quotes %{x}: %{y:,}<extra></extra>",
))

n_not_classified_trades = int(trades_counts.get("not_classified", 0))
n_not_classified_quotes = int(quotes_counts.get("not_classified", 0))
n_flagged_trades = int((~df["trades_full_window"]).sum())
n_flagged_quotes = int((~df["quotes_full_window"]).sum())

fig.update_xaxes(title="gap label", gridcolor=GRID, tickangle=15)
fig.update_yaxes(title="n events", gridcolor=GRID, type="log")

fig.update_layout(
    barmode="group",
    paper_bgcolor="#fcfcfb", plot_bgcolor="#fcfcfb",
    font=dict(family="system-ui, -apple-system, 'Segoe UI', sans-serif", color=INK, size=12),
    height=700, width=1180,
    title=dict(
        text=(f"What explains the flagged population? | trades flagged={n_flagged_trades:,} "
              f"(not_classified={n_not_classified_trades:,}, {100*n_not_classified_trades/n_flagged_trades:.1f}%), "
              f"quotes flagged={n_flagged_quotes:,} (not_classified={n_not_classified_quotes:,}, "
              f"{100*n_not_classified_quotes/n_flagged_quotes:.1f}%)"),
        x=0.02, xanchor="left", font=dict(size=13.5),
    ),
    legend=dict(bgcolor="rgba(0,0,0,0)"),
    margin=dict(t=110, b=190, l=70, r=30),
    annotations=[
        dict(
            text=("not_classified dominates both sides by construction: it is the entire file2 (2025) flagged "
                  "population (Phase 3/4's classification cohorts were file1-scoped, so file2 was never<br>"
                  "forensically classified). Per Phase 5 Amendment 4, this is the expected shape given the "
                  "structural file2 finding at T4 - not evidence the file1 carried classifications explain<br>"
                  "little; file1's own classified labels (backward_missing/both_sides/forward_missing/"
                  "calendar_residue) cover 100% of file1's flagged population with 0 not_classified. "
                  "y-axis is log (not_classified n dwarfs the others).<br>"
                  "source: research/phase_5/build_chart_03.py, spine_window_flags.parquet, "
                  "prompts/phase_5_amendment_4.md"),
            xref="paper", yref="paper", x=0.02, y=-0.34, showarrow=False,
            font=dict(size=10, color=INK_SEC), xanchor="left",
        )
    ],
)

fig.write_html("results/phase_5/charts/03_flag_label_composition.html", include_plotlyjs="inline")
print(f"chart 03 written: n_total={n_total}, trades_not_classified={n_not_classified_trades}, quotes_not_classified={n_not_classified_quotes}")
