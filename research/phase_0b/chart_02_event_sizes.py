"""Chart 02 — how large are dev events in tick rows; will dev-tier iteration
meet the <60s target?

x=event (sorted), y=trade + quote row counts (log), bar or strip, cumulative
line secondary. Per-event rows in hover; total in title.
"""
from __future__ import annotations

import json
from pathlib import Path

import plotly.graph_objects as go
from plotly.subplots import make_subplots

REPO_ROOT = Path(__file__).resolve().parents[2]


def main(out_path: str) -> None:
    materialized = json.loads(
        (REPO_ROOT / "results" / "phase_0b" / "artifacts" / "dev_tables_materialized.json").read_text(encoding="utf-8")
    )
    trades_per_event = materialized["filtered_trades_dev"]["per_event_rows"]
    quotes_per_event = materialized["filtered_quotes_dev"]["per_event_rows"]

    events = sorted(trades_per_event.keys(), key=lambda k: trades_per_event[k], reverse=True)
    trade_counts = [trades_per_event[e] for e in events]
    quote_counts = [quotes_per_event.get(e, 0) for e in events]
    totals = [t + q for t, q in zip(trade_counts, quote_counts)]

    cumulative = []
    running = 0
    grand_total = sum(totals)
    for t in totals:
        running += t
        cumulative.append(100.0 * running / grand_total if grand_total else 0.0)

    fig = make_subplots(specs=[[{"secondary_y": True}]])

    fig.add_trace(
        go.Bar(x=events, y=trade_counts, name="trade rows", marker_color="#4C78A8",
               hovertext=[f"{e}: {t:,} trades" for e, t in zip(events, trade_counts)]),
        secondary_y=False,
    )
    fig.add_trace(
        go.Bar(x=events, y=quote_counts, name="quote rows", marker_color="#F58518",
               hovertext=[f"{e}: {q:,} quotes" for e, q in zip(events, quote_counts)]),
        secondary_y=False,
    )
    fig.add_trace(
        go.Scatter(x=events, y=cumulative, name="cumulative % of total rows", mode="lines+markers",
                    line=dict(color="#54A24B", dash="dot")),
        secondary_y=True,
    )

    fig.update_layout(
        barmode="stack",
        title=f"Dev sample event sizes — n=50 events, {grand_total:,} total trade+quote rows",
        height=650,
        template="plotly_white",
        xaxis=dict(tickangle=60, tickfont=dict(size=8)),
    )
    fig.update_yaxes(title_text="rows (log)", type="log", secondary_y=False)
    fig.update_yaxes(title_text="cumulative % of total rows", range=[0, 100], secondary_y=True)

    out = REPO_ROOT / out_path
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.write_html(str(out), include_plotlyjs="cdn")
    print(f"wrote {out}")


if __name__ == "__main__":
    import sys
    target = sys.argv[1] if len(sys.argv) > 1 else "results/phase_0b/charts/02_dev_sample_event_sizes.html"
    main(target)
