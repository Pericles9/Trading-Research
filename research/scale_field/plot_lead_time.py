#!/usr/bin/env python
"""
Task 1 chart: the lead-time distribution against its chance-matching null.

The null is the point of the picture. With the field boolean firing more often than the
level detector, a nearest-onset match will pair almost anything, so the observed lead
means nothing until it is drawn against onsets shifted circularly inside the same window
-- count and spacing preserved, timing relationship destroyed.

One chart per file (CLAUDE.md), Plotly, offline --plotlyjs directory, never a CDN (D14).

Usage: .venv/Scripts/python.exe research/scale_field/plot_lead_time.py
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(REPO_ROOT, "research", "phase_10d_diag1"))

import adapter  # noqa: E402
from adapter import rel  # noqa: E402
from plot_boundary_through_time import THEMES  # noqa: E402

SEG_COLOR = {"premarket": "#eb6834", "rth": "#256abf"}


def ecdf(a):
    a = np.sort(np.asarray(a, float)[np.isfinite(a)])
    return a, np.arange(1, a.size + 1) / a.size


def build(ev, on, summ, t):
    p = summ["burst_orientation_PRIMARY"]
    nl = p["circular_shift_null"]
    fig = make_subplots(
        rows=3, cols=1, vertical_spacing=0.11, row_heights=[0.40, 0.30, 0.30],
        subplot_titles=(
            "signed lead of FIELD relative to LEVEL, in units of the kernel scale s "
            "(positive = field fired first)",
            "Jaccard overlap of the two ON-sets, per event",
            "R² of ridge strength on log λ̂ at the same (t, s) — how much of the field is rate"))

    sub = on[on["orientation"] == "burst"]
    x, y = ecdf(sub["lead_in_s_units"])
    fig.add_trace(go.Scattergl(x=x, y=y, mode="lines",
                               line=dict(color=t["ink"], width=2.6),
                               name=f"observed (n={len(x)} matched onsets)",
                               hovertemplate="lead %{x:+.3f} s-units<br>%{y:.0%}"
                                             "<extra></extra>"), row=1, col=1)
    fig.add_vline(x=0.0, row=1, col=1, line=dict(color=t["ink2"], width=1.4, dash="dash"))
    fig.add_annotation(row=1, col=1, x=0.0, y=0.02, yref="y domain", xshift=4,
                       text="zero lead", showarrow=False, xanchor="left", yanchor="bottom",
                       font=dict(size=9, color=t["ink2"]))
    obs = p["share_of_onsets_field_first"]
    nul = nl["null_share_field_first"]["q50"]
    fig.add_hline(y=1 - obs, row=1, col=1, line=dict(color="#256abf", width=1.2, dash="dot"))
    fig.add_hline(y=1 - nul, row=1, col=1, line=dict(color="#898781", width=1.2, dash="dot"))
    fig.add_annotation(row=1, col=1, x=-2.9, y=1 - obs, xanchor="left",
                       yanchor="bottom", showarrow=False,
                       text=f"<b>observed: field first only {obs:.1%} of onsets</b>",
                       font=dict(size=10, color="#256abf"),
                       bgcolor=t["surface"], borderpad=2)
    fig.add_annotation(row=1, col=1, x=-2.9, y=1 - nul, xanchor="left",
                       yanchor="top", showarrow=False,
                       text=f"chance-matching null: {nul:.0%} (symmetric by construction)",
                       font=dict(size=10, color="#898781"),
                       bgcolor=t["surface"], borderpad=2)
    fig.update_yaxes(title_text="share of onsets", tickformat=".0%", row=1, col=1)
    fig.update_xaxes(title_text="lead (units of s)", range=[-3, 3], row=1, col=1)

    for seg, g in ev.groupby("segment"):
        if seg not in SEG_COLOR:
            continue
        xx, yy = ecdf(g["jaccard_burst"])
        fig.add_trace(go.Scattergl(x=xx, y=yy, mode="lines",
                                   line=dict(color=SEG_COLOR[seg], width=2),
                                   name=f"{seg} (n={len(g)})",
                                   hovertemplate=f"{seg}<br>Jaccard %{{x:.3f}}<br>%{{y:.0%}}"
                                                 "<extra></extra>"), row=2, col=1)
    fig.add_vline(x=0.9, row=2, col=1, line=dict(color=t["ink"], width=1.4, dash="dash"))
    fig.add_annotation(row=2, col=1, x=0.9, y=0.5, yref="y domain", xshift=-4,
                       text="restatement bar, 0.9", showarrow=False, xanchor="right",
                       font=dict(size=9, color=t["ink"]))
    fig.update_yaxes(title_text="share of events", tickformat=".0%", row=2, col=1)
    fig.update_xaxes(title_text="Jaccard", range=[0, 1], row=2, col=1)

    for seg, g in ev.groupby("segment"):
        if seg not in SEG_COLOR or "r2_ridge_on_loglambda" not in g:
            continue
        xx, yy = ecdf(g["r2_ridge_on_loglambda"])
        fig.add_trace(go.Scattergl(x=xx, y=yy, mode="lines",
                                   line=dict(color=SEG_COLOR[seg], width=2),
                                   showlegend=False,
                                   hovertemplate=f"{seg}<br>R² %{{x:.3f}}<br>%{{y:.0%}}"
                                                 "<extra></extra>"), row=3, col=1)
    fig.update_yaxes(title_text="share of events", tickformat=".0%", row=3, col=1)
    fig.update_xaxes(title_text="R²", range=[0, 1], row=3, col=1)

    la = p["lead_seconds_all_onsets"]
    fig.update_layout(
        title=dict(text=(
            "<b>Task 1 — does the parameter-free field boolean lead a level detector?</b> · "
            f"n = {summ['n_events']} events, anchor → +60 s<br>"
            "<sup>FIELD = sign of dL/dln s at the smallest scale clearing 2·s_min(t); "
            "LEVEL = λ̂ above its own trailing q90 at that same scale. Both debounced at one "
            "kernel width. <b>Answer: neither.</b> Jaccard "
            f"{p['jaccard']['q50']:.2f} is far below the 0.9 restatement bar and R² "
            f"{summ['r2_ridge_on_loglambda']['q50']:.2f} says the field is not mostly rate — "
            f"but the median lead is {la['q50']:+.3f} s and the field fires first only "
            f"{obs:.1%} of the time against a {nul:.0%} chance baseline, so it <b>lags</b>.</sup>"),
            font=dict(size=15, color=t["ink"]), x=0.01, xanchor="left"),
        height=1000, paper_bgcolor=t["plane"], plot_bgcolor=t["surface"],
        font=dict(family='system-ui, -apple-system, "Segoe UI", sans-serif',
                  size=11, color=t["ink2"]),
        legend=dict(orientation="h", y=1.05, x=1, xanchor="right",
                    bgcolor="rgba(0,0,0,0)"),
        margin=dict(l=70, r=40, t=118, b=50))
    fig.update_xaxes(showgrid=True, gridcolor=t["grid"], linecolor=t["axis"])
    fig.update_yaxes(gridcolor=t["grid"], linecolor=t["axis"], zeroline=False)
    for a in fig.layout.annotations[:3]:
        a.font.update(size=11, color=t["ink2"]); a.update(x=0, xanchor="left")
    return fig


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="results/scale_field/charts/cohort")
    ap.add_argument("--theme", choices=["light", "dark"], default="light")
    ap.add_argument("--plotlyjs", default="directory", choices=["directory", "inline"])
    args = ap.parse_args()
    A = rel("results/scale_field/artifacts")
    ev = pd.read_parquet(os.path.join(A, "t1_lead_time_events.parquet"))
    on = pd.read_parquet(os.path.join(A, "t1_lead_time_onsets.parquet"))
    with open(os.path.join(A, "t1_lead_time.json"), encoding="utf-8") as f:
        summ = json.load(f)
    out = Path(rel(args.out)); out.mkdir(parents=True, exist_ok=True)
    fig = build(ev, on, summ, THEMES[args.theme])
    path = out / f"07_lead_time_{args.theme}.html"
    fig.write_html(path, include_plotlyjs=(True if args.plotlyjs == "inline" else "directory"),
                   full_html=True)
    print(f"wrote {path}")


if __name__ == "__main__":
    main()
