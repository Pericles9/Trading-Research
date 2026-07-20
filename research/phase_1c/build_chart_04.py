"""
Phase 1c T7a - chart 04: updated universe waterfall.
"""
import json

import plotly.graph_objects as go

BLUE = "#2a78d6"
GREEN = "#008300"
RED = "#e34948"
GRID = "#e1e0d9"
INK = "#0b0b0b"
INK_SEC = "#52514e"

with open("results/phase_1c/artifacts/t7_recompute_summary.json") as f:
    s = json.load(f)

prior = s["prior_in_scope"]
restored = s["flag_missing_event_day_cleared"]
confirmed_zero = s["n_confirmed_zero_exclusions"]
new_total = s["new_in_scope"]

cov = {"both_sides": 20772, "trades_only": 179, "no_trades": 0}
residual = new_total - sum(cov.values())

labels = [f"1b terminal\n({prior:,})", "+ restored\n(healed)", "- confirmed-zero\n(closed)", "New in-scope"]
values = [prior, restored, -confirmed_zero, new_total]
measures = ["absolute", "relative", "relative", "total"]

labels += ["Both-sides\ningested", "Trades-only", "No trades"]
values += [cov["both_sides"], cov["trades_only"], cov["no_trades"]]
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
        text=(f"Does the post-heal universe balance? | {prior:,} + {restored:,} restored "
              f"- {confirmed_zero:,} confirmed-zero = {new_total:,} | residual={residual}"),
        x=0.02, xanchor="left", font=dict(size=14),
    ),
    xaxis=dict(gridcolor=GRID, tickangle=-20),
    yaxis=dict(title="event count", gridcolor=GRID),
    margin=dict(t=100, b=120, l=70, r=30),
    annotations=[
        dict(
            text=(f"n on every step. Terminal three bars sum exactly to the new in-scope total "
                  f"(20,772 + 179 + 0 = {new_total:,}). Coverage split unchanged in shape from "
                  f"Phase 1b (trades-only stayed at 179 - all 149 restored events already had "
                  f"quotes_ingested=TRUE pre-heal, a folder-level property independent of the "
                  f"event-day trades flag). source: results/phase_1c/artifacts/t7_recompute_summary.json"),
            xref="paper", yref="paper", x=0.02, y=-0.26, showarrow=False,
            font=dict(size=10.5, color=INK_SEC), xanchor="left",
        )
    ],
)

fig.write_html("results/phase_1c/charts/04_universe_waterfall_v2.html", include_plotlyjs="inline")
print("chart 04 written")
