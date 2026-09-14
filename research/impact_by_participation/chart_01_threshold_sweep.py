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

    t5 = json.loads((ARTIFACTS / "t5_exact_reclassification.json").read_text())
    x5 = [r["round_trip_bp"] for r in t5["sweep"]]
    y5 = [r["p_clear_optimistic"] for r in t5["sweep"]]
    required_bp = t5["threshold_interpolated_round_trip_bp"]

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
        x=x5, y=y5, mode="lines+markers", name="p_clear_optimistic, EXACT (T5, "
        "event_minute_bars_v2 reclassification)", line=dict(color="#1a7a4c", width=3)))
    fig.add_trace(go.Scatter(
        x=[70.98], y=[0.3885], mode="markers", name="T3's actual p_clear_optimistic "
        "(exact ordering, this cell, baseline cost)",
        marker=dict(color=T["ink"], size=12, symbol="x")))
    fig.add_vline(x=required_bp, line_dash="dot", line_color="#1a7a4c",
                  annotation_text=f"exact threshold: {required_bp:.1f} bp",
                  annotation_position="bottom right")

    fig.update_xaxes(type="log", title_text="round_trip_bp (log scale)")
    fig.update_yaxes(title_text="probability", range=[0, 1])
    fig.update_layout(
        title="01 - Does a smaller round-trip cost close the closest-cell gap? (bound, then exact)",
        template="plotly_white", plot_bgcolor=T["surface"], paper_bgcolor=T["surface"],
        font_color=T["ink"], height=580,
        annotations=[dict(
            text=(f"n={n:,} entries, latency 1 min, horizon 60 min, profit_k=3/stop_m=2 "
                  "(closest cell, results/phase_10e/REPORT.md sec.5). The upper bound (orange) "
                  "ignores touch order and was T1's initial, insufficient answer; the EXACT "
                  "curve (dark green, T5) reclassifies touch order minute-by-minute from "
                  "event_minute_bars_v2 and matches T3's measured 0.3885 at baseline exactly "
                  "(marked x). Exact threshold to clear p_breakeven: ~11.0 bp, 15.5% of the "
                  "70.98 bp baseline -- far below any participation decile T3 measured "
                  "(50.7-71.5 bp round-trip-equivalent, chart 03)."),
            xref="paper", yref="paper", x=0, y=-0.26, showarrow=False, align="left",
            font=dict(size=11, color=T["ink2"]))],
        margin=dict(b=140),
    )
    CHARTS.mkdir(parents=True, exist_ok=True)
    out = CHARTS / "01_threshold_sweep.html"
    # D14: offline environment, no CDN. Local plotly.min.js per chart directory, matching the
    # standing convention (results/phase_10e/charts/plotly.min.js and siblings).
    fig.write_html(out, include_plotlyjs="plotly.min.js")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
