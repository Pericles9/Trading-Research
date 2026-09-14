#!/usr/bin/env python
"""Chart 01 -- max intraday decline from prior close, dev tier, Reg SHO 201 trigger threshold marked.

Usage: .venv/Scripts/python.exe research/reg_sho_201/chart_01_decline_distribution.py
"""
from __future__ import annotations

import json
import os

import pandas as pd
import plotly.graph_objects as go

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
IN_PARQUET = os.path.join(REPO, "results", "reg_sho_201", "artifacts", "t1_trigger_check.parquet")
IN_JSON = os.path.join(REPO, "results", "reg_sho_201", "artifacts", "t1_trigger_check.json")
OUT = os.path.join(REPO, "results", "reg_sho_201", "charts", "01_decline_distribution.html")


def main() -> int:
    df = pd.read_parquet(IN_PARQUET)
    summary = json.load(open(IN_JSON, encoding="utf-8"))
    ok = df[df.status == "ok"].copy()
    ok["decline_pct"] = ok["max_intraday_decline"] * 100

    import numpy as np
    ok = ok.reset_index(drop=True)
    ok["triggered_t0"] = ok["triggered_t0"].astype(bool)
    rng = np.random.default_rng(20260914)
    jitter = rng.uniform(-0.15, 0.15, size=len(ok))
    ok["_jitter"] = jitter

    fig = go.Figure()
    fig.add_trace(go.Box(
        y=ok["decline_pct"], name=f"events (n={len(ok)})", boxpoints=False,
        line_color="#888", fillcolor="rgba(51,102,204,0.15)",
    ))
    not_trig = ok[~ok["triggered_t0"]]
    fig.add_trace(go.Scatter(
        x=not_trig["_jitter"], y=not_trig["decline_pct"], mode="markers",
        marker=dict(color="#3366cc", size=7), name="not triggered",
    ))
    trig = ok[ok["triggered_t0"]]
    fig.add_trace(go.Scatter(
        x=trig["_jitter"], y=trig["decline_pct"], mode="markers",
        marker=dict(color="#d62728", size=9, symbol="diamond"), name="triggered (>=10%)",
    ))
    fig.add_hline(y=10, line_dash="dash", line_color="red",
                  annotation_text="Rule 201 trigger: 10% decline")
    fig.add_hline(y=0, line_dash="dot", line_color="gray")

    fig.update_layout(
        title="Reg SHO 201 -- max intraday decline from prior RTH close, dev tier",
        yaxis_title="max intraday decline from prior close (%)",
        annotations=[dict(
            text=(f"n={len(ok)} events (1 excluded, no T-1 RTH bar). "
                  f"Triggered (red points, decline >= 10%): {summary['n_triggered_t0']} "
                  f"({summary['share_triggered_t0']*100:.1f}%). "
                  f"Median max decline: {summary['max_intraday_decline_summary']['median']*100:.1f}% "
                  "(negative = day's low never fell below prior close -- expected for a "
                  "momentum-selected cohort). p90: "
                  f"{summary['max_intraday_decline_summary']['p90']*100:.1f}%. "
                  "Measurement only -- no short-side execution logic implied (D5 stands). "
                  "Source: results/reg_sho_201/artifacts/t1_trigger_check.json"),
            xref="paper", yref="paper", x=0, y=-0.22, showarrow=False,
            align="left", font=dict(size=10),
        )],
        margin=dict(b=110),
    )
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    fig.write_html(OUT, include_plotlyjs="directory")
    print(f"wrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
