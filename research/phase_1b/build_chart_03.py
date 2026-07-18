"""
Phase 1b T6a - chart 03: universe waterfall.
"""
import json

import plotly.graph_objects as go

BLUE = "#2a78d6"
GREEN = "#008300"
MAGENTA = "#e87ba4"
RED = "#e34948"
GRID = "#e1e0d9"
INK = "#0b0b0b"
INK_SEC = "#52514e"

with open("results/phase_1b/artifacts/t6_waterfall_summary.json") as f:
    s = json.load(f)

steps = s["event_side_waterfall"]["steps"]
cov = s["event_side_waterfall"]["terminal_coverage_split"]
window_annot = s["event_side_waterfall"]["flag_window_calendar_bug_annotation"]

labels = ["Start\n(23,268)"]
values = [steps[0]["n"]]
measures = ["absolute"]
for st in steps[1:]:
    labels.append(st["step"].replace("minus_", "-").replace("_", " "))
    values.append(-st["n_dropped"])
    measures.append("relative")

labels += ["Both-sides\ningested", "Trades-only", "No folder"]
values += [cov["both_sides_ingested"], cov["trades_only"], cov["no_folder"]]
measures += ["absolute", "absolute", "absolute"]

fig = go.Figure(go.Waterfall(
    x=labels, y=values, measure=measures,
    increasing=dict(marker_color=GREEN),
    decreasing=dict(marker_color=RED),
    totals=dict(marker_color=BLUE),
    text=[f"{abs(v):,}" for v in values],
    textposition="outside",
    connector=dict(line=dict(color=GRID)),
))

fig.update_layout(
    paper_bgcolor="#fcfcfb", plot_bgcolor="#fcfcfb",
    font=dict(family="system-ui, -apple-system, 'Segoe UI', sans-serif", color=INK, size=12),
    height=620,
    title=dict(
        text=(f"Does every one of 23,268 events land in exactly one bucket? | "
              f"in-scope n={cov['sum']:,}, residual={cov['residual']} | "
              f"{window_annot['n_in_scope_and_flagged']:,} in-scope events carry "
              f"flag_window_calendar_bug (annotation, not a drop)"),
        x=0.02, xanchor="left", font=dict(size=14),
    ),
    xaxis=dict(gridcolor=GRID, tickangle=-30),
    yaxis=dict(title="event count", gridcolor=GRID),
    margin=dict(t=100, b=140, l=70, r=30),
    annotations=[
        dict(
            text=("n on every step. Terminal three bars (both-sides ingested / "
                  "trades-only / no folder) sum exactly to the in-scope total, per "
                  "Amendment 2's coverage split. source: "
                  "results/phase_1b/artifacts/t6_waterfall_summary.json"),
            xref="paper", yref="paper", x=0.02, y=-0.30, showarrow=False,
            font=dict(size=10.5, color=INK_SEC), xanchor="left",
        )
    ],
)

fig.write_html("results/phase_1b/charts/03_universe_waterfall.html", include_plotlyjs="inline")
print("chart 03 written")
