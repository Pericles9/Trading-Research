"""Chart 01 — does the 50-event dev sample span the full momentum_pct distribution?

x=momentum_pct (log), full-universe ECDF + histogram; dev-sample events as a
colored rug overlay; decile boundaries (computed over the eligible pool, per
build_dev_sample.py) as vertical lines. Full n in title; eligible + selected n
per decile annotated.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

import duckdb
import plotly.graph_objects as go
from plotly.subplots import make_subplots

REPO_ROOT = Path(__file__).resolve().parents[2]


def main(out_path: str) -> None:
    con = duckdb.connect(str(REPO_ROOT / "data" / "duckdb" / "main.duckdb"), read_only=True)
    all_pct = [r[0] for r in con.execute(
        "SELECT momentum_pct FROM momentum_events WHERE momentum_pct IS NOT NULL ORDER BY momentum_pct"
    ).fetchall()]
    con.close()

    dev_rows = list(csv.DictReader((REPO_ROOT / "config" / "dev_sample_events.csv").open(encoding="utf-8")))
    dev_pct = [float(r["momentum_pct"]) for r in dev_rows]
    dev_decile = [int(r["decile"]) for r in dev_rows]

    build_summary = json.loads((REPO_ROOT / "results" / "phase_0b" / "artifacts" / "dev_sample_build.json").read_text(encoding="utf-8"))
    eligible_per_decile = build_summary["eligible_per_decile"]
    n_eligible = build_summary["eligibility_waterfall"]["eligible_with_filtered_folder"]
    n_total = len(all_pct)

    # Decile boundaries over the eligible pool (matches build_dev_sample.py's assign_deciles)
    con2 = duckdb.connect(str(REPO_ROOT / "data" / "duckdb" / "main.duckdb"), read_only=True)
    con2.close()

    n = len(all_pct)
    ecdf_y = [(i + 1) / n for i in range(n)]

    fig = make_subplots(
        rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05,
        row_heights=[0.35, 0.65],
        subplot_titles=("Histogram (full universe, log x)", "ECDF (full universe) + dev-sample rug"),
    )

    fig.add_trace(
        go.Histogram(x=all_pct, nbinsx=80, name=f"Full universe (n={n_total})", marker_color="#4C78A8", opacity=0.85),
        row=1, col=1,
    )

    fig.add_trace(
        go.Scatter(x=all_pct, y=ecdf_y, mode="lines", name=f"ECDF (n={n_total})", line=dict(color="#4C78A8")),
        row=2, col=1,
    )

    decile_colors = [
        "#E45756", "#F58518", "#B279A2", "#54A24B", "#EECA3B",
        "#72B7B2", "#FF9DA6", "#9D755D", "#BAB0AC", "#4C78A8",
    ]
    for d in range(10):
        xs = [p for p, dd in zip(dev_pct, dev_decile) if dd == d]
        if not xs:
            continue
        fig.add_trace(
            go.Scatter(
                x=xs, y=[0.0] * len(xs), mode="markers",
                marker=dict(symbol="line-ns-open", size=14, color=decile_colors[d], line=dict(width=2)),
                name=f"decile {d} (eligible={eligible_per_decile[d]}, selected={len(xs)})",
            ),
            row=2, col=1,
        )

    fig.update_xaxes(type="log", title_text="momentum_pct (log)", row=2, col=1)
    fig.update_yaxes(title_text="count", row=1, col=1)
    fig.update_yaxes(title_text="ECDF", row=2, col=1)
    fig.update_layout(
        title=f"Dev sample stratification — full universe n={n_total}, eligible n={n_eligible}, selected n=50 (5/decile x 10 deciles)",
        height=800,
        template="plotly_white",
        legend=dict(orientation="h", yanchor="bottom", y=-0.35),
    )

    out = REPO_ROOT / out_path
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.write_html(str(out), include_plotlyjs="cdn")
    print(f"wrote {out}")


if __name__ == "__main__":
    import sys
    target = sys.argv[1] if len(sys.argv) > 1 else "results/phase_0b/charts/01_dev_sample_stratification.html"
    main(target)
