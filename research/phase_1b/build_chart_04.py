"""
Phase 1b T7c - chart 04: dev v2 coverage.
"""
import json
import sys
from pathlib import Path

import numpy as np
import plotly.graph_objects as go

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from src.data.db import get_connection  # noqa: E402

BLUE = "#2a78d6"
GREEN = "#008300"
MAGENTA = "#e87ba4"
YELLOW = "#eda100"
AQUA = "#1baf7a"
ORANGE = "#eb6834"
VIOLET = "#4a3aa7"
RED = "#e34948"
GRID = "#e1e0d9"
INK = "#0b0b0b"
INK_SEC = "#52514e"

DECILE_COLORS = [BLUE, GREEN, MAGENTA, YELLOW, AQUA, ORANGE, VIOLET, RED, "#898781", "#0d366b"]


def ecdf(values):
    v = np.sort(np.asarray(values, dtype=float))
    y = np.arange(1, len(v) + 1) / len(v)
    return v, y


def main():
    con = get_connection(read_only=False)
    pop = con.execute(
        """
        SELECT momentum_pct FROM momentum_events_canonical
        WHERE in_scope AND trades_ingested AND quotes_ingested AND NOT flag_window_calendar_bug
        """
    ).fetchdf()["momentum_pct"].values
    n_pop = len(pop)

    with open("config/dev_sample_v2.json") as f:
        manifest = json.load(f)
    dev_events = manifest["events"]
    n_dev = len(dev_events)

    x, y = ecdf(pop)
    fig = go.Figure(layout=dict(
        paper_bgcolor="#fcfcfb", plot_bgcolor="#fcfcfb",
        font=dict(family="system-ui, -apple-system, 'Segoe UI', sans-serif", color=INK, size=13),
        height=600,
        title=dict(
            text=(f"Does dev v2 cover the momentum distribution of the in-scope universe? | "
                  f"population n={n_pop:,}, dev n={n_dev}"),
            x=0.02, xanchor="left", font=dict(size=15),
        ),
        xaxis=dict(type="log", title="momentum_pct (log)", gridcolor=GRID, linecolor="#c3c2b7"),
        yaxis=dict(title="ECDF", gridcolor=GRID, linecolor="#c3c2b7", domain=[0.18, 1]),
        yaxis2=dict(domain=[0, 0.12], showticklabels=False, range=[-0.5, 9.5]),
        legend=dict(bgcolor="rgba(0,0,0,0)"),
        margin=dict(t=90, b=90, l=70, r=30),
    ))

    fig.add_trace(go.Scatter(
        x=x, y=y, mode="lines", name=f"in-scope eligible population (n={n_pop:,})",
        line=dict(color="#898781", width=2),
    ))

    for decile in range(10):
        pts = [e for e in dev_events if e["decile"] == decile]
        if not pts:
            continue
        fig.add_trace(go.Scatter(
            x=[p["momentum_pct"] for p in pts], y=[decile] * len(pts),
            mode="markers", marker=dict(color=DECILE_COLORS[decile], size=10, symbol="line-ns-open", line=dict(width=2, color=DECILE_COLORS[decile])),
            name=f"decile {decile} (n={len(pts)})", yaxis="y2",
            hovertext=[f"{p['ticker']} {p['date']} mom={p['momentum_pct']}" for p in pts],
        ))

    fig.update_layout(
        annotations=[
            dict(
                text=(f"Grey line: ECDF of the {n_pop:,}-event eligible population "
                      f"(in_scope AND trades_ingested AND quotes_ingested AND NOT "
                      f"flag_window_calendar_bug). Colored ticks: the 50 dev v2 events, "
                      f"one row per decile, positioned at their actual momentum_pct. "
                      f"source: config/dev_sample_v2.json"),
                xref="paper", yref="paper", x=0.02, y=-0.16, showarrow=False,
                font=dict(size=10.5, color=INK_SEC), xanchor="left",
            )
        ],
    )

    fig.write_html("results/phase_1b/charts/04_dev_v2_coverage.html", include_plotlyjs="inline")
    print(f"chart 04 written: population n={n_pop}, dev n={n_dev}")


if __name__ == "__main__":
    main()
