"""
Phase 1c T7a - chart 02: healed sessions by offset.
"""
import json

import pandas as pd
import plotly.graph_objects as go

BLUE = "#2a78d6"
GREEN = "#008300"
RED = "#e34948"
GRID = "#e1e0d9"
INK = "#0b0b0b"
INK_SEC = "#52514e"

manifest = pd.read_parquet("results/phase_1c/artifacts/heal_manifest.parquet")
ledger = pd.read_parquet("results/phase_1c/artifacts/repair_ledger.parquet")

# "Covered" (trades side ok or skipped_collision) is the healed/no-longer-
# damaged signal - every manifest row requires trades (fetch_trades=True
# always per T1), so the trades side alone determines whether that
# specific session gap closed.
trades_ledger = ledger[ledger["side"] == "trades"]
covered_keys = set(zip(trades_ledger[trades_ledger["verification_status"].isin(["ok", "skipped_collision"])]["event_key"],
                        trades_ledger[trades_ledger["verification_status"].isin(["ok", "skipped_collision"])]["session"]))

manifest["covered"] = list(zip(manifest["event_key"], manifest["session"]))
manifest["healed"] = manifest["covered"].apply(lambda k: k in covered_keys)

offsets = [-3, -2, -1, 0, 1, 2, 3]
damaged_before = [int((manifest["offset_k"] == k).sum()) for k in offsets]
healed = [int(((manifest["offset_k"] == k) & manifest["healed"]).sum()) for k in offsets]
remaining = [d - h for d, h in zip(damaged_before, healed)]

x_labels = [f"T{k:+d}" if k != 0 else "T=0\n(event day)" for k in offsets]

fig = go.Figure()
fig.add_trace(go.Bar(x=x_labels, y=damaged_before, name="damaged-before", marker_color=RED,
                      text=damaged_before, textposition="outside"))
fig.add_trace(go.Bar(x=x_labels, y=healed, name="healed", marker_color=GREEN,
                      text=healed, textposition="outside"))
fig.add_trace(go.Bar(x=x_labels, y=remaining, name="remaining", marker_color=BLUE,
                      text=remaining, textposition="outside"))

fig.update_layout(
    paper_bgcolor="#fcfcfb", plot_bgcolor="#fcfcfb",
    font=dict(family="system-ui, -apple-system, 'Segoe UI', sans-serif", color=INK, size=12),
    height=560,
    barmode="group",
    title=dict(
        text=(f"Did the heal close the damage where it mattered? | "
              f"total damaged n={sum(damaged_before):,}, healed n={sum(healed):,}, remaining n={sum(remaining):,}"),
        x=0.02, xanchor="left", font=dict(size=14),
    ),
    xaxis=dict(title="window offset", gridcolor=GRID),
    yaxis=dict(title="session count", gridcolor=GRID),
    legend=dict(bgcolor="rgba(0,0,0,0)"),
    margin=dict(t=90, b=100, l=70, r=30),
    annotations=[
        dict(
            text=("n on every bar. T=0 isolates the 150 event-day heals (142 calendar_bug + 8 "
                  "collection_failure). remaining = damaged-before - healed, traced to the 12 T4 "
                  "fetch failures (required archive columns absent from the vendor response) plus "
                  "4 confirmed-empty flanking sessions (thin names, genuinely zero trades - fetched "
                  "successfully but nothing to insert). source: "
                  "results/phase_1c/artifacts/heal_manifest.parquet + repair_ledger.parquet"),
            xref="paper", yref="paper", x=0.02, y=-0.22, showarrow=False,
            font=dict(size=10.5, color=INK_SEC), xanchor="left",
        )
    ],
)

fig.write_html("results/phase_1c/charts/02_healed_sessions_by_offset.html", include_plotlyjs="inline")
print(f"chart 02 written: damaged={damaged_before}, healed={healed}, remaining={remaining}")
