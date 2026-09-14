"""Chart 03 -- effective spread by participation decile. Standalone Plotly HTML.

Subsamples the per-print overlay (2,000/decile) rather than passing millions of raw points
into go.Violin/go.Box -- chart 02's first attempt embedded all ~9.5e6 raw points client-side
via go.Histogram and produced a 107 MB file; the same trap applies to go.Violin/go.Box with
`points` set on a full-size array. Summary quartiles (drawn from the full n, not the subsample)
are exact; only the visual point cloud is thinned, and the caption says so.
"""
from __future__ import annotations

import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "phase_10d_diag1"))
from plot_boundary_through_time import THEMES  # noqa: E402

import numpy as np
import pandas as pd
import plotly.graph_objects as go

REPO = pathlib.Path(__file__).resolve().parents[2]
ARTIFACTS = REPO / "results" / "impact_by_participation" / "artifacts"
CHARTS = REPO / "results" / "impact_by_participation" / "charts"
T = THEMES["light"]
SUBSAMPLE_PER_DECILE = 2000
RNG_SEED = 42


def main() -> None:
    d = pd.read_parquet(ARTIFACTS / "t3_cost_by_decile_prints.parquet",
                         columns=["decile", "eff_bp"])
    stats = json.loads((ARTIFACTS / "t3_cost_by_decile.json").read_text())["by_decile"]
    threshold_data = json.loads((ARTIFACTS / "t1_threshold.json").read_text())
    baseline_rt_bp = threshold_data["baseline_round_trip_bp"]

    rng = np.random.default_rng(RNG_SEED)
    fig = go.Figure()
    for row in sorted(stats, key=lambda r: r["decile"]):
        dec = row["decile"]
        sub = d[d.decile == dec]["eff_bp"]
        n_full = len(sub)
        n_sample = min(SUBSAMPLE_PER_DECILE, n_full)
        sample = sub.sample(n=n_sample, random_state=RNG_SEED) if n_full > n_sample else sub
        fig.add_trace(go.Violin(
            y=sample, x=[str(dec)] * len(sample), name=f"d{dec}",
            box_visible=True, meanline_visible=True, points="all",
            pointpos=0, jitter=0.3, marker=dict(size=2, opacity=0.15, color=T["ink2"]),
            line_color=T["winner"], showlegend=False,
        ))

    # Round-trip reference line: effective spread here is ONE-SIDED (a single fill), while
    # 70.98 bp is a ROUND TRIP (two fills) -- so the reference is halved for a like-for-like
    # comparison, stated explicitly rather than left for the reader to reconstruct.
    fig.add_hline(y=baseline_rt_bp / 2, line_dash="dash", line_color=T["muted"],
                  annotation_text=f"70.98 bp round trip / 2 = {baseline_rt_bp/2:.2f} bp "
                                  "one-sided reference", annotation_position="top left")

    n_per_decile = {r["decile"]: r["n"] for r in stats}
    fig.update_yaxes(title_text="effective spread (bp), log scale", type="log")
    fig.update_xaxes(title_text="participation decile (low -> high)")
    fig.update_layout(
        title="03 - Effective spread by participation decile (dev tier, T=0)",
        template="plotly_white", plot_bgcolor=T["surface"], paper_bgcolor=T["surface"],
        font_color=T["ink"], height=560,
        annotations=[dict(
            text=(f"n per decile: {', '.join(f'd{k}={v:,}' for k, v in sorted(n_per_decile.items()))}. "
                  f"Point cloud subsampled to {SUBSAMPLE_PER_DECILE}/decile for rendering "
                  "(quartiles/median drawn from the full n). filtered_trades_dev_v4 "
                  "dev_cohort='primary', 50 events, T=0 only."),
            xref="paper", yref="paper", x=0, y=-0.22, showarrow=False, align="left",
            font=dict(size=10, color=T["ink2"]))],
        margin=dict(b=110),
    )
    CHARTS.mkdir(parents=True, exist_ok=True)
    out = CHARTS / "03_cost_by_participation.html"
    fig.write_html(out, include_plotlyjs="plotly.min.js")
    print(f"wrote {out} ({out.stat().st_size / 1024:.1f} KB)")


if __name__ == "__main__":
    main()
