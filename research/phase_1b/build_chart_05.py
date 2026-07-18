"""
Phase 1b T5-R3a - chart 05: calendar damage by window offset.
"""
import json

import plotly.graph_objects as go

BLUE = "#2a78d6"
GREEN = "#008300"
RED = "#e34948"
GRID = "#e1e0d9"
INK = "#0b0b0b"
INK_SEC = "#52514e"

TEMPLATE_LAYOUT = dict(
    paper_bgcolor="#fcfcfb",
    plot_bgcolor="#fcfcfb",
    font=dict(family="system-ui, -apple-system, 'Segoe UI', sans-serif", color=INK, size=13),
    xaxis=dict(gridcolor=GRID, zerolinecolor=GRID, linecolor="#c3c2b7"),
    yaxis=dict(gridcolor=GRID, zerolinecolor=GRID, linecolor="#c3c2b7"),
    legend=dict(bgcolor="rgba(0,0,0,0)"),
    margin=dict(t=90, b=60, l=70, r=30),
)

with open("results/phase_1b/artifacts/t5r3_window_damage_summary.json") as f:
    s = json.load(f)
with open("results/phase_1b/artifacts/t5r2_zero_trades_cause.json") as f:
    r2 = json.load(f)

damage = s["damage_by_offset"]
offsets_order = ["-3", "-2", "-1", "1", "2", "3"]
labels = ["T-3", "T-2", "T-1", "T+1", "T+2", "T+3"]
missing_vals = [damage[o]["missing_session"] for o in offsets_order]
short_vals = [damage[o]["short_window"] for o in offsets_order]

fig = go.Figure(layout=dict(
    **TEMPLATE_LAYOUT, height=560,
    title=dict(
        text=(f"Which window offsets did the calendar bug damage? | "
              f"in-scope n={s['n_in_scope_population']:,}, flagged n={s['n_flagged_window_calendar_bug']:,} "
              f"({s['flagged_pct_of_in_scope']}%)"),
        x=0.02, xanchor="left", font=dict(size=15),
    ),
))

fig.add_trace(go.Bar(
    x=labels, y=missing_vals, name=f"missing_session (n={sum(missing_vals):,})",
    marker_color=RED, text=missing_vals, textposition="outside",
))
fig.add_trace(go.Bar(
    x=labels, y=short_vals, name=f"short_window (n={sum(short_vals):,})",
    marker_color=BLUE, text=short_vals, textposition="outside",
))

# T=0 marker row for the 142 missing-event-day cases
n_calendar_bug_t0 = r2["n_calendar_bug"]
fig.add_trace(go.Scatter(
    x=["T=0"], y=[n_calendar_bug_t0], mode="markers+text",
    marker=dict(color=GREEN, size=18, symbol="diamond"),
    text=[f"{n_calendar_bug_t0}"], textposition="top center",
    name=f"flag_missing_event_day at T=0 (n={n_calendar_bug_t0}, excluded from in-scope)",
))

fig.update_layout(
    barmode="group",
    xaxis=dict(title="window offset", categoryorder="array", categoryarray=["T-3", "T-2", "T-1", "T=0", "T+1", "T+2", "T+3"]),
    yaxis=dict(title="event count"),
    annotations=[
        dict(
            text=("n on every bar/marker. T=0 (green diamond) is the 142 calendar_bug "
                  "flag_missing_event_day events (excluded from in-scope entirely, not part "
                  "of the flanking-offset damage counts). T-3/T+3 bars are entirely "
                  "missing_session (0 short_window) - outer-offset damage predominantly "
                  "shows as a full session shift, not a partial short window. "
                  "source: results/phase_1b/artifacts/t5r3_window_damage_summary.json, "
                  "t5r2_zero_trades_cause.json"),
            xref="paper", yref="paper", x=0.02, y=-0.16, showarrow=False,
            font=dict(size=10.5, color=INK_SEC), xanchor="left",
        )
    ],
)

fig.write_html("results/phase_1b/charts/05_calendar_damage_by_offset.html", include_plotlyjs="inline")
print("chart 05 written")
