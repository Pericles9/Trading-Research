"""Chart 01 -- T1's threshold sweep. Standalone Plotly HTML.

Reuses the repo's standing palette (THEMES["light"] from
research/phase_10d_diag1/plot_boundary_through_time.py) rather than inventing a new one.
"""
from __future__ import annotations

import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "phase_10d_diag1"))
from plot_boundary_through_time import THEMES  # noqa: E402

import plotly.graph_objects as go

REPO = pathlib.Path(__file__).resolve().parents[2]
ARTIFACTS = REPO / "results" / "impact_by_participation" / "artifacts"
CHARTS = REPO / "results" / "impact_by_participation" / "charts"
T = THEMES["light"]


def main() -> None:
    data = json.loads((ARTIFACTS / "t1_threshold.json").read_text())
    sweep = data["sweep"]
    x = [r["round_trip_bp"] for r in sweep]
    p_bound = [r["p_clear_upper_bound"] for r in sweep]
    p_stop = [r["p_stop_reached_share"] for r in sweep]
    p_both = [r["p_reached_both_order_unknown"] for r in sweep]
    n = data["sweep_n"]
    be = data["p_breakeven"]

    fig = go.Figure()
    fig.add_hline(y=be, line_dash="dash", line_color=T["muted"],
                  annotation_text=f"p_breakeven = {be:.4f}", annotation_position="top left")
    fig.add_trace(go.Scatter(x=x, y=p_bound, mode="lines+markers", name="p_clear upper bound "
                              "(profit reached, order ignored)", line=dict(color=T["winner"])))
    fig.add_trace(go.Scatter(x=x, y=p_stop, mode="lines+markers", name="p_stop reached (any "
                              "order)", line=dict(color=T["ink2"])))
    fig.add_trace(go.Scatter(x=x, y=p_both, mode="lines+markers", name="both reached (order "
                              "determines outcome)", line=dict(color=T["axis"], dash="dot")))
    fig.add_trace(go.Scatter(
        x=[70.98], y=[0.3885], mode="markers", name="T3's actual p_clear_optimistic "
        "(exact ordering, this cell)", marker=dict(color=T["ink"], size=12, symbol="x")))

    fig.update_xaxes(type="log", title_text="round_trip_bp (log scale)")
    fig.update_yaxes(title_text="probability", range=[0, 1])
    fig.update_layout(
        title="01 - Does a smaller round-trip cost close the closest-cell gap?",
        template="plotly_white", plot_bgcolor=T["surface"], paper_bgcolor=T["surface"],
        font_color=T["ink"], height=560,
        annotations=[dict(
            text=(f"n={n:,} entries, latency 1 min, horizon 60 min, profit_k=3/stop_m=2 "
                  "(closest cell, results/phase_10e/REPORT.md sec.5). Upper bound and stop-"
                  "reached share are computed from t2_excursion.parquet's mfe_h60/mae_h60 "
                  "(reached-at-all, order ignored) -- NOT the exact ordering-sensitive "
                  "quantity T3 measures (marked x). config_hash: n/a (analysis-only, no "
                  "config committed for this sweep)."),
            xref="paper", yref="paper", x=0, y=-0.22, showarrow=False, align="left",
            font=dict(size=11, color=T["ink2"]))],
        margin=dict(b=120),
    )
    CHARTS.mkdir(parents=True, exist_ok=True)
    out = CHARTS / "01_threshold_sweep.html"
    # D14: offline environment, no CDN. Local plotly.min.js per chart directory, matching the
    # standing convention (results/phase_10e/charts/plotly.min.js and siblings).
    fig.write_html(out, include_plotlyjs="plotly.min.js")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
