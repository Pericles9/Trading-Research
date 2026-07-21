"""
Phase 2 chart 01 - window coverage by offset (the core question).
Source: results/phase_2/artifacts/window_coverage_summary.json
high_momentum bars omitted (N/A - absent from E: data root, T3a).
"""
import json

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

BLUE = "#2a78d6"
GREEN = "#008300"
GRID = "#e1e0d9"
INK = "#0b0b0b"
INK_SEC = "#52514e"

with open("results/phase_2/artifacts/window_coverage_summary.json") as f:
    s = json.load(f)

by_offset = pd.DataFrame(s["coverage_by_offset"]).sort_values("offset")
n_events = s["n_events_in_matrix"]

x_labels = [f"T{int(k):+d}" if k != 0 else "T=0 (event day)" for k in by_offset["offset"]]

fig = make_subplots(rows=2, cols=1, shared_xaxes=False, row_heights=[0.68, 0.32], vertical_spacing=0.10,
                     subplot_titles=("% of events with session present, by offset",
                                      "per-event covered-session count (0-7), filtered_trades vs filtered_quotes"))

fig.add_trace(go.Bar(x=x_labels, y=by_offset["pct_filtered_trades"], name="filtered_trades", marker_color=BLUE,
                      text=[f"{v:.1f}%" for v in by_offset["pct_filtered_trades"]], textposition="outside"), row=1, col=1)
fig.add_trace(go.Bar(x=x_labels, y=by_offset["pct_filtered_quotes"], name="filtered_quotes", marker_color=GREEN,
                      text=[f"{v:.1f}%" for v in by_offset["pct_filtered_quotes"]], textposition="outside"), row=1, col=1)

dist_t = s["per_event_covered_session_count_distribution"]["filtered_trades"]
dist_q = s["per_event_covered_session_count_distribution"]["filtered_quotes"]
counts = [str(k) for k in range(8)]
dist_t_vals = [dist_t.get(k, 0) for k in counts]
dist_q_vals = [dist_q.get(k, 0) for k in counts]

fig.add_trace(go.Bar(x=counts, y=dist_t_vals, name="filtered_trades (per-event n)", marker_color=BLUE,
                      text=dist_t_vals, textposition="outside", showlegend=False), row=2, col=1)
fig.add_trace(go.Bar(x=counts, y=dist_q_vals, name="filtered_quotes (per-event n)", marker_color=GREEN,
                      text=dist_q_vals, textposition="outside", showlegend=False), row=2, col=1)

fig.update_xaxes(title="window offset", gridcolor=GRID, row=1, col=1)
fig.update_yaxes(title="% of events (session present)", gridcolor=GRID, range=[0, 108], row=1, col=1)
fig.update_xaxes(title="covered sessions out of 7", gridcolor=GRID, row=2, col=1)
fig.update_yaxes(title="n events", gridcolor=GRID, row=2, col=1)

fig.update_layout(
    paper_bgcolor="#fcfcfb", plot_bgcolor="#fcfcfb",
    font=dict(family="system-ui, -apple-system, 'Segoe UI', sans-serif", color=INK, size=12),
    height=820,
    barmode="group",
    title=dict(
        text=(f"Do the 2025 events have full XNYS T-3..T+3 coverage, and in which source? | "
              f"n events in matrix={n_events:,} (of {s['n_events']:,} 2025 in-scope; "
              f"{s['n_events_anchor_not_xnys_session']} excluded: anchor not an XNYS session). "
              f"high_momentum: N/A (absent from E: data root, see T3a)"),
        x=0.02, xanchor="left", font=dict(size=13.5),
    ),
    legend=dict(bgcolor="rgba(0,0,0,0)"),
    margin=dict(t=110, b=140, l=70, r=30),
    annotations=list(fig.layout.annotations) + [
        dict(
            text=(f"high_momentum/ bars omitted (N/A - absent from the E: data root; see chart 03 / T3a / T5). "
                  f"Per T2's migration-signature facet, ~91.5% of 2025 events' filtered_trades rows bear the "
                  f"2026-07-11 migration's subtractive-schema fingerprint - this chart shows whether that migrated "
                  f"population carries genuine T-3..T+3 coverage or is event-day-only. "
                  f"source: results/phase_2/t4_window_coverage.py, results/phase_2/artifacts/window_coverage.parquet"),
            xref="paper", yref="paper", x=0.02, y=-0.13, showarrow=False,
            font=dict(size=10, color=INK_SEC), xanchor="left",
        )
    ],
)

fig.write_html("results/phase_2/charts/01_window_coverage_by_offset.html", include_plotlyjs="inline")
print(f"chart 01 written: n_events={n_events}")
