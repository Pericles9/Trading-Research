"""
Phase 2 chart 03 - source row-count comparison (empty-state).
high_momentum/ absent (T3a) -> 0 (event, session) pairs present in both
sources -> nothing to plot. Chart is still produced per the chart contract,
annotated to explain why it's empty rather than omitted.
Source: results/phase_2/artifacts/source_comparison_summary.json
"""
import json

import plotly.graph_objects as go

BLUE = "#2a78d6"
GRID = "#e1e0d9"
INK = "#0b0b0b"
INK_SEC = "#52514e"

with open("results/phase_2/artifacts/source_comparison_summary.json") as f:
    s = json.load(f)

fig = go.Figure()
fig.add_trace(go.Scatter(x=[], y=[], mode="markers", marker=dict(color=BLUE, size=8), name="event-session pairs"))
fig.add_shape(type="line", x0=1, y0=1, x1=1e9, y1=1e9, xref="x", yref="y",
              line=dict(color=INK_SEC, dash="dash", width=1))

fig.update_xaxes(type="log", title="filtered_trades rows (per event-session, log)", gridcolor=GRID, range=[0, 9])
fig.update_yaxes(type="log", title="high_momentum rows (per event-session, log)", gridcolor=GRID, range=[0, 9])

fig.update_layout(
    paper_bgcolor="#fcfcfb", plot_bgcolor="#fcfcfb",
    font=dict(family="system-ui, -apple-system, 'Segoe UI', sans-serif", color=INK, size=12),
    height=560,
    title=dict(
        text="Do the two sources agree where they overlap? | n compared pairs = 0",
        x=0.02, xanchor="left", font=dict(size=14),
    ),
    annotations=[
        dict(
            text="NO DATA — high_momentum/ is absent from the E: data root (T3a)",
            xref="paper", yref="paper", x=0.5, y=0.5, showarrow=False,
            font=dict(size=18, color=INK_SEC),
        ),
        dict(
            text=(f"{s['reason']} y=x reference line shown (dashed) with no points on it. "
                  f"Escalation check (row divergence &gt;10% on &gt;10% of compared event-sessions): "
                  f"vacuously not triggered — 0 pairs to compare, not evidence of agreement. "
                  f"Documented (not independently verified) column-schema diff: filtered_trades carries "
                  f"{len(s['column_schema_diff']['filtered_trades_db_columns'])} columns "
                  f"({', '.join(s['column_schema_diff']['filtered_trades_db_columns'])}); high_momentum's "
                  f"migration write path is documented as {len(s['column_schema_diff']['high_momentum_documented_columns'])} "
                  f"columns only ({', '.join(s['column_schema_diff']['high_momentum_documented_columns'])}). "
                  f"source: results/phase_2/t5_source_comparison.py, results/cleanup/deletion_report.md"),
            xref="paper", yref="paper", x=0.02, y=-0.22, showarrow=False,
            font=dict(size=10, color=INK_SEC), xanchor="left",
        ),
    ],
    margin=dict(t=90, b=130, l=70, r=30),
)

fig.write_html("results/phase_2/charts/03_source_rowcount_comparison.html", include_plotlyjs="inline")
print("chart 03 written: n_compared=0 (empty-state)")
