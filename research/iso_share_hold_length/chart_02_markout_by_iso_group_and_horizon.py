#!/usr/bin/env python
"""Chart 02 -- median-cut separation by horizon: real iso_share vs. negative control
(placebo) vs. positive control (planted). This chart's actual message is the escalation
finding: the negative-control line is not indistinguishable-near-zero as it should be,
and sits at or above the real line at several horizons -- the "looks like this if wrong"
case from the Chart Contract, realized.

Usage: .venv/Scripts/python.exe research/iso_share_hold_length/chart_02_markout_by_iso_group_and_horizon.py
"""
from __future__ import annotations

import json
import os

import plotly.graph_objects as go

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
IN_JSON = os.path.join(REPO, "results", "iso_share_hold_length", "artifacts", "t3_separation.json")
OUT = os.path.join(REPO, "results", "iso_share_hold_length", "charts",
                    "02_markout_by_iso_group_and_horizon.html")
HORIZONS = ["det+15", "det+30", "det+60", "t0_close", "t1_close", "t3_close"]


def main() -> int:
    d = json.load(open(IN_JSON, encoding="utf-8"))

    median_cut = next(r for r in d["real_sweep_iso_share"] if r["cut_quantile"] == 0.50)
    real_sep = [median_cut["by_horizon"][h]["separation_bp"] for h in HORIZONS]
    real_n = [f"hi={median_cut['by_horizon'][h]['n_hi']},lo={median_cut['by_horizon'][h]['n_lo']}"
              for h in HORIZONS]

    neg_median_cut = next(r for r in d["negative_control"]["sweep"] if r["cut_quantile"] == 0.50)
    neg_sep = [neg_median_cut["by_horizon"][h]["separation_bp"] for h in HORIZONS]

    req = [d.get("real_sweep_iso_share")[0]["by_horizon"][h]["required_separation_bp"]
           for h in HORIZONS]

    pc = d["positive_control"]["detected_separation_bp_by_horizon"]
    pc_planted = d["positive_control"]["planted_magnitude_bp"]
    pos_sep = [pc.get(h) for h in HORIZONS]

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=HORIZONS, y=real_sep, mode="lines+markers",
                              name="real iso_share (median cut)", line=dict(color="#2ca02c", width=3),
                              text=real_n, hovertemplate="%{x}: %{y:.1f} bp (%{text})<extra></extra>"))
    fig.add_trace(go.Scatter(x=HORIZONS, y=neg_sep, mode="lines+markers",
                              name="negative control (placebo, median cut)",
                              line=dict(color="#d62728", width=2, dash="dot")))
    fig.add_trace(go.Scatter(x=HORIZONS, y=pos_sep, mode="lines+markers",
                              name=f"positive control (planted {pc_planted:.1f} bp)",
                              line=dict(color="#1f77b4", width=2, dash="dash")))
    fig.add_trace(go.Scatter(x=HORIZONS, y=req, mode="lines+markers",
                              name="required separation (Sec 1)",
                              line=dict(color="black", width=1, dash="dashdot")))
    fig.add_hline(y=0, line_color="gray", line_width=1)

    fig.update_layout(
        title=("Median-cut separation by horizon: real vs. negative vs. positive control "
               "-- both controls fail (n=49 dev tier)"),
        xaxis_title="horizon (fixed 5-min entry latency)",
        yaxis_title="group separation, high - low (bp)",
        annotations=[dict(
            text=("The negative-control (placebo) line should sit near zero and does not -- "
                  "it exceeds the real iso_share line at 4 of 6 horizons and the required "
                  "separation at all 6. The positive control (a known "
                  f"{pc_planted:.1f} bp planted effect) is not cleanly recovered either. "
                  "Diagnosis: t3_close markout std=7121 bp at n=49, driven by single outlier "
                  "events (UCAR +44,768 bp, IMTE -9,640 bp) -- the median-split statistic is "
                  "dominated by which side of the cut a few extreme events land on, real or "
                  "placebo. n per horizon: 49 events matched; per-cut group sizes in hover. "
                  "Source: results/iso_share_hold_length/artifacts/t3_separation.json"),
            xref="paper", yref="paper", x=0, y=-0.32, showarrow=False,
            align="left", font=dict(size=10),
        )],
        margin=dict(b=160),
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
    )
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    fig.write_html(OUT, include_plotlyjs="directory")
    print(f"wrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
