"""Chart 04 -- the decisive comparison: measured cost by decile vs. the exact required threshold."""
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
    data = json.loads((ARTIFACTS / "t6_final_comparison.json").read_text())
    rows = sorted(data["by_decile"], key=lambda r: r["decile"])
    required = data["required_round_trip_bp_to_close_closest_cell_gap"]
    baseline = data["baseline_round_trip_bp"]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=[str(r["decile"]) for r in rows],
        y=[r["measured_round_trip_equivalent_bp"] for r in rows],
        text=[f"n={r['n']:,}" for r in rows], textposition="outside",
        marker_color=T["winner"], name="measured (round-trip-equivalent)"))
    fig.add_hline(y=required, line_dash="dash", line_color="#1a7a4c",
                  annotation_text=f"required to close the gap: {required:.1f} bp",
                  annotation_position="top left")
    fig.add_hline(y=baseline, line_dash="dot", line_color=T["muted"],
                  annotation_text=f"Phase 11 baseline: {baseline:.2f} bp",
                  annotation_position="bottom left")

    fig.update_yaxes(title_text="round-trip-equivalent cost (bp), log scale", type="log",
                      range=[0.8, 2.1])
    fig.update_xaxes(title_text="participation decile (low -> high)")
    fig.update_layout(
        title="04 - Measured cost vs. the exact threshold: 0 of 10 deciles clear it",
        template="plotly_white", plot_bgcolor=T["surface"], paper_bgcolor=T["surface"],
        font_color=T["ink"], height=560,
        annotations=list(fig.layout.annotations) + [dict(
            text=(f"Cheapest decile ({min(r['measured_round_trip_equivalent_bp'] for r in rows):.1f} bp) "
                  f"is {data['cheapest_decile_multiple_of_required']:.1f}x the required threshold. "
                  "Measured: T3, dev tier, filtered_trades_dev_v4 dev_cohort='primary', 50 events, "
                  "T=0 only. Required: T5, exact reclassification against event_minute_bars_v2, "
                  "full universe (15,337 events)."),
            xref="paper", yref="paper", x=0, y=-0.22, showarrow=False, align="left",
            font=dict(size=10, color=T["ink2"]))],
        margin=dict(b=110),
    )
    CHARTS.mkdir(parents=True, exist_ok=True)
    out = CHARTS / "04_final_comparison.html"
    fig.write_html(out, include_plotlyjs="plotly.min.js")
    print(f"wrote {out} ({out.stat().st_size / 1024:.1f} KB)")


if __name__ == "__main__":
    main()
