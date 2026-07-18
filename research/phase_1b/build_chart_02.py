"""
Phase 1b T1a - chart 02: instrument classes (vendor-verdict, post Amendment 1).
"""
import json

import plotly.graph_objects as go

BLUE = "#2a78d6"
GREEN = "#008300"
GRID = "#e1e0d9"
INK = "#0b0b0b"
INK_SEC = "#52514e"

with open("results/phase_1b/artifacts/instrument_classification_rebuild_summary.json") as f:
    s = json.load(f)

counts = s["class_counts_by_class_and_source"]
classes = sorted(counts.keys(), key=lambda c: -(counts[c]["momentum_events"] + counts[c]["folder_only"]))
me_vals = [counts[c]["momentum_events"] for c in classes]
fo_vals = [counts[c]["folder_only"] for c in classes]

fig = go.Figure(layout=dict(
    paper_bgcolor="#fcfcfb", plot_bgcolor="#fcfcfb",
    font=dict(family="system-ui, -apple-system, 'Segoe UI', sans-serif", color=INK, size=13),
    height=560,
    title=dict(
        text=(f"What does the universe lose to instrument scoping? | n_tickers={s['n_tickers']:,} "
              f"(vendor verdict, 0 unresolved - Amendment 1)"),
        x=0.02, xanchor="left", font=dict(size=15),
    ),
    xaxis=dict(title="instrument class", gridcolor=GRID),
    yaxis=dict(title="ticker count", gridcolor=GRID),
    barmode="stack",
    legend=dict(bgcolor="rgba(0,0,0,0)"),
    margin=dict(t=90, b=60, l=70, r=30),
))

fig.add_trace(go.Bar(x=classes, y=me_vals, name="momentum_events", marker_color=BLUE, text=me_vals, textposition="inside"))
fig.add_trace(go.Bar(x=classes, y=fo_vals, name="folder_only", marker_color=GREEN, text=fo_vals, textposition="outside"))

fig.update_layout(
    annotations=[
        dict(
            text=("n on every bar segment. common+common_adr = 2,939/3,377 tickers (87.0%) - in "
                  "scope per D4. No suspect classes remain post-Amendment-1 (vendor type is the "
                  "verdict, heuristic is validation-only). source: "
                  "results/phase_1b/artifacts/instrument_classification_rebuild_summary.json"),
            xref="paper", yref="paper", x=0.02, y=-0.16, showarrow=False,
            font=dict(size=10.5, color=INK_SEC), xanchor="left",
        )
    ],
)

fig.write_html("results/phase_1b/charts/02_instrument_classes.html", include_plotlyjs="inline")
print("chart 02 written")
