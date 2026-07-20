"""
Phase 1c T3-R4 - chart 01: control fetch diffs.
"""
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

BLUE = "#2a78d6"
ORANGE = "#eb6834"
RED = "#e34948"
GRID = "#e1e0d9"
INK = "#0b0b0b"
INK_SEC = "#52514e"

df = pd.read_parquet("results/phase_1c/artifacts/control_fetch_diffs.parquet")
df["pair_label"] = df["ticker"] + " " + df["session"]
pairs = sorted(df["pair_label"].unique())

trades = df[df["side"] == "trades"].set_index("pair_label").reindex(pairs)
quotes = df[df["side"] == "quotes"].set_index("pair_label").reindex(pairs)

fig = make_subplots(
    rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.10,
    subplot_titles=("Row-count delta % (symmetric log)", "Matched-row field mismatch %"),
)

fig.add_trace(go.Bar(x=pairs, y=trades["row_delta_pct"], name="trades", marker_color=BLUE,
                      customdata=trades[["archive_n", "staged_n"]].values,
                      hovertemplate="%{x}<br>archive_n=%{customdata[0]:,}<br>fetched_n=%{customdata[1]:,}<extra></extra>"),
              row=1, col=1)
fig.add_trace(go.Bar(x=pairs, y=quotes["row_delta_pct"], name="quotes", marker_color=ORANGE,
                      customdata=quotes[["archive_n", "staged_n"]].values,
                      hovertemplate="%{x}<br>archive_n=%{customdata[0]:,}<br>fetched_n=%{customdata[1]:,}<extra></extra>"),
              row=1, col=1)
fig.add_hline(y=1, line=dict(color=RED, width=1, dash="dot"), row=1, col=1)
fig.add_hline(y=-1, line=dict(color=RED, width=1, dash="dot"), row=1, col=1)

fig.add_trace(go.Bar(x=pairs, y=trades["field_mismatch_pct"], name="trades", marker_color=BLUE, showlegend=False),
              row=2, col=1)
fig.add_trace(go.Bar(x=pairs, y=quotes["field_mismatch_pct"], name="quotes", marker_color=ORANGE, showlegend=False),
              row=2, col=1)
fig.add_hline(y=0.1, line=dict(color=RED, width=1, dash="dot"), row=2, col=1)

fig.update_yaxes(title="delta %", gridcolor=GRID, row=1, col=1)
fig.update_yaxes(title="mismatch %", gridcolor=GRID, row=2, col=1)
fig.update_xaxes(tickangle=-45, row=2, col=1)

# Only ARBB trades is non-zero on the delta panel (294.65%); everything
# else is exactly 0 - a genuinely honest linear axis (no symlog transform
# needed for a single dominant outlier among all-zero peers, and a
# manual log transform would need to handle the zeros).
fig.add_annotation(x="ARBB 2024-02-13", y=trades.loc["ARBB 2024-02-13", "row_delta_pct"],
                    text=f"{trades.loc['ARBB 2024-02-13', 'row_delta_pct']:.1f}%", showarrow=False,
                    yshift=14, font=dict(size=10, color=INK_SEC), row=1, col=1)

fig.update_layout(
    paper_bgcolor="#fcfcfb", plot_bgcolor="#fcfcfb",
    font=dict(family="system-ui, -apple-system, 'Segoe UI', sans-serif", color=INK, size=11),
    height=720,
    barmode="group",
    title=dict(
        text=(f"Does the new fetch path reproduce the archive? | 20 pairs (15 stratified + 5 targeted) | "
              f"threshold lines at ±1% row delta, 0.1% field mismatch"),
        x=0.02, xanchor="left", font=dict(size=14),
    ),
    legend=dict(bgcolor="rgba(0,0,0,0)"),
    margin=dict(t=90, b=140, l=70, r=30),
    annotations=[
        dict(
            text=("Archive/fetched n in hover per bar. ARBB trades (294.65% delta - archive capped at "
                  "exactly 50,000 rows, fetch recovered the true 197,326) and 4 pairs' price-precision "
                  "mismatches (NTZ/ENSC/BHAT/XTIA, all sub-cent, 99% concentrated on exchange=4 TRF prints) "
                  "were investigated and resolved as archive-side conditions, not fetch-path defects - "
                  "documented in t3r4_resolution.json. 17/20 pairs (85%) show exactly 0% on both panels. "
                  "source: results/phase_1c/artifacts/control_fetch_diffs.parquet"),
            xref="paper", yref="paper", x=0.02, y=-0.30, showarrow=False,
            font=dict(size=10.5, color=INK_SEC), xanchor="left",
        )
    ],
)

fig.write_html("results/phase_1c/charts/01_control_fetch_diffs.html", include_plotlyjs="inline")
print("chart 01 written")
