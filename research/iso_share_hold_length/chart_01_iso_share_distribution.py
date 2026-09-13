#!/usr/bin/env python
"""Chart 01 -- per-event iso_share distribution, dev tier.

Question: what does the iso_share distribution look like, and how much mass is
zero/near-zero? (T2a)

Usage: .venv/Scripts/python.exe research/iso_share_hold_length/chart_01_iso_share_distribution.py
"""
from __future__ import annotations

import json
import os

import pandas as pd
import plotly.graph_objects as go

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
IN_PARQUET = os.path.join(REPO, "results", "iso_share_hold_length", "artifacts", "t2_iso_share.parquet")
IN_JSON = os.path.join(REPO, "results", "iso_share_hold_length", "artifacts", "t2_iso_share.json")
OUT = os.path.join(REPO, "results", "iso_share_hold_length", "charts", "01_iso_share_distribution.html")


def main() -> int:
    df = pd.read_parquet(IN_PARQUET)
    summary = json.load(open(IN_JSON, encoding="utf-8"))
    ok = df[df.status == "ok"].copy()
    n_total = len(df)
    n_ok = len(ok)

    fig = go.Figure()
    fig.add_trace(go.Histogram(
        x=ok["iso_share"], nbinsx=20, marker_color="#3366cc",
        name=f"iso_share (n={n_ok})",
    ))
    fig.add_trace(go.Box(
        x=ok["iso_share"], y=["strip"] * n_ok, boxpoints="all", jitter=0.6,
        pointpos=0, marker_color="#333", line_color="rgba(0,0,0,0)",
        fillcolor="rgba(0,0,0,0)", name="events (strip)", yaxis="y2", showlegend=True,
    ))
    med = summary["iso_share_summary"]["median"]
    fig.add_vline(x=med, line_dash="dash", line_color="black",
                  annotation_text=f"median {med:.3f}")

    fig.update_layout(
        title="iso_share distribution -- dev tier, 5-min entry anchor (T2)",
        xaxis_title="iso_share (ISO-flagged volume / total volume, [T=0 open, det_minute+5min])",
        yaxis=dict(title="count", domain=[0.25, 1.0]),
        yaxis2=dict(domain=[0.0, 0.15], showticklabels=False),
        bargap=0.05,
        annotations=[dict(
            text=(f"n_events={n_total}, n_ok={n_ok} (coverage={summary['coverage']:.3f}), "
                  f"status_counts={summary['status_counts']}<br>"
                  f"share exactly zero: {summary['iso_share_summary']['share_exactly_zero']:.3f} "
                  f"-- NOT zero-inflated as expected going in (T2a)<br>"
                  f"config: dev_sample_v3.json, dev_cohort=primary, iso_code=14, latency=5min. "
                  f"Source: results/iso_share_hold_length/artifacts/t2_iso_share.json"),
            xref="paper", yref="paper", x=0, y=-0.28, showarrow=False,
            align="left", font=dict(size=10),
        )],
        margin=dict(b=140),
    )
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    fig.write_html(OUT, include_plotlyjs="directory")
    print(f"wrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
