"""Chart 02 - are drops concentrated in time (a collection-run failure) or
spread evenly?

x=event date (monthly bins), y=count, stacked bars by join status. n per
bin in hover; totals in title.
"""
from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

import duckdb
import plotly.graph_objects as go

REPO_ROOT = Path(__file__).resolve().parents[2]


def main(out_path: str) -> None:
    filtered_dir = REPO_ROOT / "data" / "filtered"
    con = duckdb.connect(str(REPO_ROOT / "data" / "duckdb" / "main.duckdb"), read_only=True)
    rows = con.execute("SELECT ticker, date, momentum_pct FROM momentum_events").fetchall()
    con.close()

    joinable_months: Counter = Counter()
    dropped_months: Counter = Counter()
    null_date_count = 0

    for ticker, date, mom in rows:
        if date is None:
            null_date_count += 1
            continue
        folder = filtered_dir / f"{ticker}_{date}_{mom:.2f}"
        is_eligible = (folder / "trades.parquet").exists() and (folder / "quotes.parquet").exists()
        month = str(date)[:7]  # YYYY-MM
        (joinable_months if is_eligible else dropped_months)[month] += 1

    all_months = sorted(set(joinable_months) | set(dropped_months))
    j_counts = [joinable_months.get(m, 0) for m in all_months]
    d_counts = [dropped_months.get(m, 0) for m in all_months]

    fig = go.Figure()
    fig.add_trace(go.Bar(x=all_months, y=j_counts, name="joinable", marker_color="#4C78A8",
                          hovertext=[f"{m}: {c} joinable" for m, c in zip(all_months, j_counts)]))
    fig.add_trace(go.Bar(x=all_months, y=d_counts, name="dropped", marker_color="#E45756",
                          hovertext=[f"{m}: {c} dropped" for m, c in zip(all_months, d_counts)]))

    fig.update_layout(
        barmode="stack",
        title=(
            f"Events by month and join status — {sum(j_counts)} joinable, {sum(d_counts)} dropped "
            f"({null_date_count} null-date events excluded, no month to bin)"
        ),
        xaxis_title="event month", yaxis_title="count",
        height=600, template="plotly_white",
        xaxis=dict(tickangle=60),
    )

    out = REPO_ROOT / out_path
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.write_html(str(out), include_plotlyjs="cdn")
    print(f"wrote {out}")


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "results/phase_0c/charts/02_events_over_time_by_join_status.html"
    main(target)
