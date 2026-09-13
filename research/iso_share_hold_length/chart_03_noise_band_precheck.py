#!/usr/bin/env python
"""Chart 03 -- full-tier vs. dev-tier noise band against the required separation, by horizon.

Question: does the noise band shrink enough at full tier for the required separation to be
distinguishable from chance? (T4 bootstrap precheck)

Usage: .venv/Scripts/python.exe research/iso_share_hold_length/chart_03_noise_band_precheck.py
"""
from __future__ import annotations

import json
import os

import plotly.graph_objects as go

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
IN_JSON = os.path.join(REPO, "results", "iso_share_hold_length", "artifacts", "t4_bootstrap_precheck.json")
OUT = os.path.join(REPO, "results", "iso_share_hold_length", "charts", "03_noise_band_precheck.html")
HORIZONS = ["det+15", "det+30", "det+60", "t0_close", "t1_close", "t3_close"]


def main() -> int:
    d = json.load(open(IN_JSON, encoding="utf-8"))
    full = d["full_tier"]
    dev = d["dev_tier_49_sanity_check"]["by_horizon"]

    required = [full[h]["required_separation_bp"] for h in HORIZONS]
    full_p95 = [full[h]["null_separation_abs_pctiles_bp"]["p95"] for h in HORIZONS]
    full_max = [full[h]["null_separation_abs_pctiles_bp"]["max"] for h in HORIZONS]
    dev_p95 = [dev[h]["null_separation_abs_p95_bp"] for h in HORIZONS]
    dev_max = [dev[h]["null_separation_abs_max_bp"] for h in HORIZONS]
    n_full = [full[h]["n_events"] for h in HORIZONS]
    n_dev = [dev[h]["n_events"] for h in HORIZONS]

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=HORIZONS, y=required, mode="lines+markers",
                              name="required separation (Sec 1)",
                              line=dict(color="black", width=3)))
    fig.add_trace(go.Scatter(x=HORIZONS, y=dev_max, mode="lines+markers",
                              name=f"dev-tier (n={n_dev[0]}) null max, 5000 reps",
                              line=dict(color="#d62728", width=2, dash="dot")))
    fig.add_trace(go.Scatter(x=HORIZONS, y=dev_p95, mode="lines+markers",
                              name=f"dev-tier (n={n_dev[0]}) null p95",
                              line=dict(color="#d62728", width=1, dash="dot"), opacity=0.5))
    fig.add_trace(go.Scatter(x=HORIZONS, y=full_max, mode="lines+markers",
                              name=f"full-tier (n~{n_full[0]:,}) null max, 5000 reps",
                              line=dict(color="#2ca02c", width=2, dash="dash")))
    fig.add_trace(go.Scatter(x=HORIZONS, y=full_p95, mode="lines+markers",
                              name=f"full-tier (n~{n_full[0]:,}) null p95",
                              line=dict(color="#2ca02c", width=1, dash="dash"), opacity=0.5))

    fig.update_yaxes(type="log", title="separation (bp), log scale")
    fig.update_layout(
        title=("Noise band vs. required separation: dev tier (n=49) vs. full tier (n~15,330) -- "
               "zero new tick reads, bootstrap over the already-committed markout grid"),
        xaxis_title="horizon (fixed 5-min entry latency)",
        annotations=[dict(
            text=("At dev tier, the required separation sits WITHIN the null's range at every "
                  "horizon (matches T3's actual control failure). At full tier, the required "
                  "separation clears even the null's 5000-rep MAXIMUM by a wide margin at every "
                  "horizon (12-19x the null's own standard deviation) -- P(null >= required) = "
                  "0/5000 at every horizon. This is a precheck of statistical power only: it says "
                  "nothing about whether iso_share itself carries a real effect, only that full "
                  "tier is capable of measuring one if it exists. "
                  "Source: results/iso_share_hold_length/artifacts/t4_bootstrap_precheck.json"),
            xref="paper", yref="paper", x=0, y=-0.32, showarrow=False,
            align="left", font=dict(size=10),
        )],
        margin=dict(b=140),
        legend=dict(orientation="h", yanchor="bottom", y=1.02),
    )
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    fig.write_html(OUT, include_plotlyjs="directory")
    print(f"wrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
