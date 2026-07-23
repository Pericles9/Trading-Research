"""
Phase 5 chart 01 - clean vs flagged by year, faceted by source_file.
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
df["year"] = df["event_date_canonical"].dt.year
df["status"] = df["clean_window"].map({True: "clean", False: "flagged"})

years = sorted(df["year"].unique())

fig = make_subplots(
    rows=1, cols=2, column_widths=[0.55, 0.45],
    subplot_titles=(
        f"file1 (n={int((df['source_file']=='file1').sum()):,})",
        f"file2 (n={int((df['source_file']=='file2').sum()):,})",
    ),
)

for col_idx, sf in enumerate(["file1", "file2"], start=1):
    sub = df[df["source_file"] == sf]
    for status, color, textpos, textcolor in [
        ("clean", AQUA, "inside", "white"),
        ("flagged", RED, "outside", INK_SEC),
    ]:
        counts = sub[sub["status"] == status]["year"].value_counts().reindex(years, fill_value=0)
        fig.add_trace(
            go.Bar(
                x=years, y=counts.values, name=status, marker_color=color,
                legendgroup=status, showlegend=(col_idx == 1),
                text=[f"{v:,}" if v > 0 else "" for v in counts.values], textposition=textpos,
                textfont=dict(size=9, color=textcolor),
                hovertemplate=f"{sf} %{{x}} {status}: %{{y:,}}<extra></extra>",
            ),
            row=1, col=col_idx,
        )

fig.update_xaxes(title="event year", dtick=1, gridcolor=GRID, row=1, col=1)
fig.update_xaxes(title="event year", dtick=1, gridcolor=GRID, row=1, col=2)
fig.update_yaxes(title="n events", gridcolor=GRID, row=1, col=1)
fig.update_yaxes(title="n events", gridcolor=GRID, row=1, col=2)

fig.update_layout(
    barmode="stack",
    paper_bgcolor="#fcfcfb", plot_bgcolor="#fcfcfb",
    font=dict(family="system-ui, -apple-system, 'Segoe UI', sans-serif", color=INK, size=12),
    height=620, width=1180,
    title=dict(
        text=(f"Where do flagged events sit in time and source file? | total in-scope n={n_total:,}, "
              f"clean={int(df['clean_window'].sum()):,}, flagged={int((~df['clean_window']).sum()):,}"),
        x=0.02, xanchor="left", font=dict(size=13.5),
    ),
    legend=dict(bgcolor="rgba(0,0,0,0)"),
    margin=dict(t=110, b=140, l=70, r=30),
    annotations=list(fig.layout.annotations) + [
        dict(
            text=("clean_window = trades_full_window AND quotes_full_window (both sides have all 7 XNYS "
                  "T-3..T+3 sessions present). file2 (2025) is ~100% flagged in every year present (Phase 5<br>"
                  "Amendment 4: accepted as structural, not a defect - see prompts/phase_5_amendment_4.md). "
                  "n labeled per stack segment (blank where 0). source: research/phase_5/build_chart_01.py, "
                  "spine_window_flags.parquet"),
            xref="paper", yref="paper", x=0.02, y=-0.28, showarrow=False,
            font=dict(size=10, color=INK_SEC), xanchor="left",
        )
    ],
)

fig.write_html("results/phase_5/charts/01_clean_vs_flagged_by_year.html", include_plotlyjs="inline")
print(f"chart 01 written: n={n_total}, years={years}")
