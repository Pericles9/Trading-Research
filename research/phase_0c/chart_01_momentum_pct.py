"""Chart 01 - do dropped events differ from joinable ones on momentum_pct?

x=momentum_pct (log where positive), overlaid ECDFs by join status, strip
sub-sample beneath. n per group in legend.
"""
from __future__ import annotations

import sys
from pathlib import Path

import duckdb
import plotly.graph_objects as go
from plotly.subplots import make_subplots

REPO_ROOT = Path(__file__).resolve().parents[2]


def ecdf_xy(values: list[float]) -> tuple[list[float], list[float]]:
    xs = sorted(values)
    n = len(xs)
    ys = [(i + 1) / n for i in range(n)]
    return xs, ys


def main(out_path: str) -> None:
    filtered_dir = REPO_ROOT / "data" / "filtered"
    con = duckdb.connect(str(REPO_ROOT / "data" / "duckdb" / "main.duckdb"), read_only=True)
    rows = con.execute("SELECT ticker, date, momentum_pct FROM momentum_events").fetchall()
    con.close()

    joinable, dropped = [], []
    for ticker, date, mom in rows:
        folder = filtered_dir / f"{ticker}_{date}_{mom:.2f}"
        is_eligible = (folder / "trades.parquet").exists() and (folder / "quotes.parquet").exists()
        (joinable if is_eligible else dropped).append(mom)

    joinable_pos = [m for m in joinable if m > 0]
    dropped_pos = [m for m in dropped if m > 0]

    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05, row_heights=[0.75, 0.25])

    jx, jy = ecdf_xy(joinable_pos)
    dx, dy = ecdf_xy(dropped_pos)
    fig.add_trace(go.Scatter(x=jx, y=jy, mode="lines", name=f"joinable (n={len(joinable)})", line=dict(color="#4C78A8")), row=1, col=1)
    fig.add_trace(go.Scatter(x=dx, y=dy, mode="lines", name=f"dropped (n={len(dropped)})", line=dict(color="#E45756")), row=1, col=1)

    import random
    rng = random.Random(42)
    strip_j = rng.sample(joinable_pos, min(1500, len(joinable_pos)))
    strip_d = rng.sample(dropped_pos, min(1500, len(dropped_pos)))
    fig.add_trace(go.Scatter(x=strip_j, y=[0.15] * len(strip_j), mode="markers",
                              marker=dict(color="#4C78A8", size=3, opacity=0.3), name="joinable (strip sample)"), row=2, col=1)
    fig.add_trace(go.Scatter(x=strip_d, y=[-0.15] * len(strip_d), mode="markers",
                              marker=dict(color="#E45756", size=3, opacity=0.3), name="dropped (strip sample)"), row=2, col=1)

    fig.update_xaxes(type="log", title_text="momentum_pct (log)", row=2, col=1)
    fig.update_yaxes(title_text="ECDF", row=1, col=1)
    fig.update_yaxes(visible=False, range=[-1, 1], row=2, col=1)
    fig.update_layout(
        title=f"momentum_pct: joinable (n={len(joinable)}) vs. dropped (n={len(dropped)})",
        height=700, template="plotly_white",
    )

    out = REPO_ROOT / out_path
    out.parent.mkdir(parents=True, exist_ok=True)
    fig.write_html(str(out), include_plotlyjs="cdn")
    print(f"wrote {out}")


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "results/phase_0c/charts/01_momentum_pct_joinable_vs_dropped.html"
    main(target)
