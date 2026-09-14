#!/usr/bin/env python
"""Chart 01 -- RTH gap-duration distribution, before any threshold. T1b.

Question: do tape gaps carry a halt signature (mass near the 300s pause length), or is the
distribution smooth with no such mass (route 1 identifies nothing)?

Scope note, disclosed rather than silently deviated from: the Chart Contract calls for faceting
by segment and participation quintile. T1a is RTH-only by the prompt's own explicit text ("on the
T=0 RTH segment"), so there is no segment to facet by in this data; participation is not computed
by T1 at all (a Phase 8/11 concept this task does not join). Both omissions are structural, not
an oversight -- reported here rather than fabricating a facet.

Usage: .venv/Scripts/python.exe research/phase_12/chart_01_gap_duration.py
"""
from __future__ import annotations

import json
import os

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
IN_PARQUET = os.path.join(REPO, "results", "phase_12", "artifacts", "t1_gap_census.parquet")
IN_JSON = os.path.join(REPO, "results", "phase_12", "artifacts", "t1_gap_census.json")
OUT = os.path.join(REPO, "results", "phase_12", "charts", "01_gap_duration.html")
GAP_THRESHOLD_S = 60
PAUSE_LENGTH_S = 300


def main() -> int:
    g = pd.read_parquet(IN_PARQUET)
    summary = json.load(open(IN_JSON, encoding="utf-8"))
    n_total = len(g)
    dur = g["duration_s"].to_numpy()
    dur_pos = dur[dur > 0]

    fig = make_subplots(rows=1, cols=2, subplot_titles=(
        "ECDF, all RTH gaps (log duration)",
        "Histogram, candidate gaps >= 60s (log-spaced bins)"))

    # Subsample the ECDF to ~3000 order-statistic points -- a step function needs only enough
    # points to render its shape faithfully; embedding all 3.06M raw points produced an 81MB
    # file. Disclosed here and in the caption per this repo's chart-size discipline.
    sorted_d = np.sort(dur_pos)
    n_full = len(sorted_d)
    N_ECDF_POINTS = 3000
    idx = np.unique(np.linspace(0, n_full - 1, N_ECDF_POINTS).astype(int))
    ecdf_x = sorted_d[idx]
    ecdf_y = (idx + 1) / n_full
    fig.add_trace(go.Scatter(x=ecdf_x, y=ecdf_y, mode="lines",
                              name=f"ECDF ({len(idx)} of {n_full:,} points)",
                              line=dict(color="#3366cc")), row=1, col=1)
    fig.add_vline(x=GAP_THRESHOLD_S, line_dash="dot", line_color="orange", row=1, col=1)
    fig.add_vline(x=PAUSE_LENGTH_S, line_dash="dash", line_color="red", row=1, col=1)

    cand = g[g.is_candidate]["duration_s"].to_numpy()
    bins = np.logspace(np.log10(GAP_THRESHOLD_S), np.log10(cand.max()), 40)
    fig.add_trace(go.Histogram(x=cand, xbins=dict(start=bins[0], end=bins[-1]),
                                marker_color="#3366cc", name=f"candidates (n={len(cand)})",
                                autobinx=False, nbinsx=40), row=1, col=2)
    fig.add_vline(x=PAUSE_LENGTH_S, line_dash="dash", line_color="red", row=1, col=2,
                  annotation_text="300s pause length")

    fig.update_xaxes(type="log", title_text="gap duration (s, log)", row=1, col=1)
    fig.update_xaxes(type="log", title_text="gap duration (s, log)", row=1, col=2)
    fig.update_yaxes(title_text="cumulative share", row=1, col=1)
    fig.update_yaxes(title_text="count", row=1, col=2)

    dist = summary["gap_distribution"]
    fig.update_layout(
        title="T1b -- RTH gap-duration distribution, dev tier (56 events), before threshold",
        annotations=list(fig.layout.annotations) + [dict(
            text=(f"n_gaps_total={n_total:,} (n_events=56, all cohorts). "
                  f"n_candidates(>=60s)={dist['n_candidates_ge_threshold']:,} "
                  f"({dist['share_candidates']*100:.3f}% of all gaps). "
                  f"p50={dist['p50']:.4f}s p99={dist['p99']:.2f}s max={dist['max']:.1f}s.<br>"
                  "SHAPE: uniform 20s-binned candidate counts decline smoothly from 200-300s "
                  "(56,44,31,21,19) then reverse upward at 300-320s (31) before resuming decline "
                  "-- a modest but real local excess at the pause length, not a smooth power-law "
                  "tail throughout. Not faceted by segment (T1 is RTH-only) or participation "
                  "quintile (not computed by this task) -- see script docstring. ECDF panel "
                  f"subsampled to {len(idx)} order-statistic points of {n_full:,} total for file "
                  "size; the step function is faithful at this resolution, no point altered.<br>"
                  "Source: results/phase_12/artifacts/t1_gap_census.json"),
            xref="paper", yref="paper", x=0, y=-0.22, showarrow=False,
            align="left", font=dict(size=10),
        )],
        margin=dict(b=140), showlegend=False,
    )
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    fig.write_html(OUT, include_plotlyjs="directory")
    print(f"wrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
