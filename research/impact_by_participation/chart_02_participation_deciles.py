"""Chart 02 -- participation-rate distribution and decile boundaries. Standalone Plotly HTML."""
from __future__ import annotations

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


def main() -> None:
    d = pd.read_parquet(ARTIFACTS / "t2_participation.parquet",
                         columns=["participation_rate", "decile"])
    n = len(d)
    log_pr = np.log10(d["participation_rate"].clip(lower=1e-6))

    # Pre-bin in Python -- go.Histogram would embed all n raw points client-side for
    # browser-side binning, which produced a 107 MB file here (n ~ 9.5e6). go.Bar on
    # pre-computed counts is the same distribution view at a few hundred bytes of data.
    counts_arr, edges = np.histogram(log_pr, bins=80)
    centers = (edges[:-1] + edges[1:]) / 2
    widths = edges[1:] - edges[:-1]

    fig = go.Figure()
    fig.add_trace(go.Bar(x=centers, y=counts_arr, width=widths, marker_color=T["winner"],
                         name="all prints (dev tier)"))
    boundaries = d.groupby("decile")["participation_rate"].min().sort_index()
    for dec, b in boundaries.items():
        if dec == 1:
            continue
        fig.add_vline(x=float(np.log10(max(b, 1e-6))), line_dash="dot", line_color=T["muted"])
    counts = d.groupby("decile").size()
    for dec, cnt in counts.items():
        fig.add_annotation(x=float(np.log10(max(boundaries[dec], 1e-6)) + 0.15),
                            y=1, yref="paper", text=f"d{dec}: n={cnt:,}",
                            showarrow=False, font=dict(size=9, color=T["ink2"]),
                            textangle=-90, yanchor="top")

    fig.update_xaxes(title_text="log10(participation rate)")
    fig.update_yaxes(title_text="count of prints")
    fig.update_layout(
        title="02 - Participation-rate distribution and decile boundaries (dev tier)",
        template="plotly_white", plot_bgcolor=T["surface"], paper_bgcolor=T["surface"],
        font_color=T["ink"], height=520,
        annotations=fig.layout.annotations + (dict(
            text=(f"n={n:,} prints, filtered_trades_dev_v4 dev_cohort='primary', 50 events, "
                  "matched to their own "
                  "(session_offset, minute_index) bar via event_minute_bars_v2. Deciles are "
                  "rank-based (~equal n per decile), boundaries marked as vertical lines."),
            xref="paper", yref="paper", x=0, y=-0.2, showarrow=False, align="left",
            font=dict(size=11, color=T["ink2"])),),
        margin=dict(b=100),
    )
    CHARTS.mkdir(parents=True, exist_ok=True)
    out = CHARTS / "02_participation_deciles.html"
    fig.write_html(out, include_plotlyjs="plotly.min.js")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
