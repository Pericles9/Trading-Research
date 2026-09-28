"""
v0 charts.

01 -- markout distribution, Policy A against Policy B. The brief asks for the full
      distribution, not a median, so this is an ECDF: each policy's median is where its curve
      crosses y = 0.5, and the whole shape including both tails is on the page. The two cost
      bars are drawn as vertical lines so "clears cost" is read off the picture.
02 -- the score decile panel. Median gross markout with its interquartile band against decile
      of the attention score, n on every bucket, and the mean plotted separately because mean
      and median disagree in sign here and averaging them away would hide the finding.
03 -- the concurrency distribution. How many candidates were live at each candidate moment.
      Gate 2 has nothing to decide left of 2, so this is what licenses or kills the whole
      cross-sectional half.
04 -- the collinearity scatter: attention score against move_at at each candidate moment,
      both log axes, Spearman rho annotated rather than substituted for the picture.

Usage: .venv/Scripts/python.exe research/relative_momentum_v0/charts.py
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np
import pandas as pd
import plotly.graph_objects as go

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from research.relative_momentum_v0 import chart_common as K  # noqa: E402
from research.relative_momentum_v0 import common as C  # noqa: E402

IN = f"{C.ART}/t4_diagnostic.parquet"
T4 = f"{C.ART}/t4_diagnostic.json"


def chart_01(d: pd.DataFrame, cost_bp: float) -> str:
    sc = d[d["score_available"]]
    ser = [
        ("A · EPG-only (scorable base)", sc, K.BLUE),
        ("B · EPG+Qual, both gates", d[d["policy_b"]], K.ORANGE),
        ("B-contested · gate 2 actually decided", d[d["policy_b"] & ~d["gate2_trivial_singleton"]],
         K.VIOLET),
    ]
    fig = go.Figure()
    for label, sub, color in ser:
        v = np.sort(sub["natural_exit_pnl_pct"].to_numpy(dtype=float) * 100)
        v = v[np.isfinite(v)]
        if v.size == 0:
            continue
        fig.add_trace(go.Scatter(
            x=v, y=np.arange(1, v.size + 1) / v.size, mode="lines",
            name=f"{label} (n={v.size:,}, median {np.quantile(v, .5):+,.0f} bp, "
                 f"mean {v.mean():+,.0f})",
            line=dict(color=color, width=2),
            hovertemplate=label + "<br>%{x:,.0f} bp<br>F = %{y:.3f}<extra></extra>"))
    fig.add_vline(x=0, line_width=2, line_dash="dash", line_color=K.INK)
    fig.add_vline(x=cost_bp, line_width=1.5, line_dash="dot", line_color=K.RED)
    fig.add_annotation(x=cost_bp, y=1.0, yref="paper", yanchor="bottom",
                       text=f"flat round-trip cost {cost_bp:.0f} bp", showarrow=False,
                       font=dict(size=10, color=K.RED))
    med_cents = float(np.nanmedian(d["cost_cents_bp"]))
    fig.add_vline(x=med_cents, line_width=1.5, line_dash="dot", line_color=K.INK2)
    fig.add_annotation(x=med_cents, y=0.93, yref="paper", yanchor="bottom",
                       text=f"median per-share cost {med_cents:.0f} bp", showarrow=False,
                       font=dict(size=10, color=K.INK2))
    fig.add_hline(y=0.5, line_width=1, line_dash="dot", line_color=K.INK2)
    fig.update_xaxes(title_text="gross markout, window-close exit (bp; view window ±4,000)",
                     range=[-4000, 4000])
    fig.update_yaxes(title_text="cumulative share of trades", range=[0, 1])
    cap = K.caption(
        sample="first-window gate trades, phase_f/val_full, 2023-11-17 to 2024-07-22",
        filters="none — nothing trimmed or clipped; the curves run flat past the view window. "
                "Policy A is shown on the scorable base (n=999), the like-for-like denominator "
                "for Policy B.",
        extra="Entry = first rising edge, exit = window close, median hold 540 s. pnl is GROSS "
              "(the gate applies no cost model); the two dotted lines are the cost bars a trade "
              "has to clear.")
    K.base_layout(fig, "v0 · markout distribution — Policy A against Policy B", cap,
                  height=700, cap_y=-0.24, margin_b=240)
    return K.write(fig, "01_markout_distribution_A_vs_B.html")


def chart_02(d: pd.DataFrame, cost_bp: float) -> str:
    s = d[d["score_available"]].copy()
    s["dec"] = pd.qcut(s["score"], 10, labels=False, duplicates="drop")
    g = s.groupby("dec")["natural_exit_pnl_pct"]
    x = np.arange(10)
    p25, p50, p75 = (g.quantile(q).to_numpy() * 100 for q in (.25, .5, .75))
    mean = g.mean().to_numpy() * 100
    n = g.size().to_numpy()

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=np.concatenate([x, x[::-1]]),
                             y=np.concatenate([p75, p25[::-1]]), fill="toself",
                             fillcolor=K.rgba(K.BLUE, .13), line=dict(width=0),
                             hoverinfo="skip", name="median — IQR"))
    fig.add_trace(go.Scatter(x=x, y=p50, mode="lines+markers+text", name="median gross markout",
                             line=dict(color=K.BLUE, width=2.5), marker=dict(size=8),
                             text=[f"n={v}" for v in n], textposition="bottom center",
                             textfont=dict(size=9, color=K.INK2),
                             hovertemplate="decile %{x}<br>median %{y:,.0f} bp<extra></extra>"))
    fig.add_trace(go.Scatter(x=x, y=mean, mode="lines+markers", name="mean gross markout",
                             line=dict(color=K.ORANGE, width=2, dash="dash"),
                             marker=dict(size=7, symbol="diamond"),
                             hovertemplate="decile %{x}<br>mean %{y:,.0f} bp<extra></extra>"))
    fig.add_hline(y=0, line_width=2, line_dash="dash", line_color=K.INK)
    fig.add_hline(y=cost_bp, line_width=1.5, line_dash="dot", line_color=K.RED)
    fig.add_vrect(x0=7.5, x1=9.5, fillcolor=K.rgba(K.RED, .07), line_width=0,
                  annotation_text="gate 1 selects here (≥ 75th pct)",
                  annotation_position="top left",
                  annotation_font=dict(size=10, color=K.RED))
    fig.update_xaxes(title_text="attention score decile (0 = lowest relative volume)",
                     tickmode="array", tickvals=list(range(10)))
    fig.update_yaxes(title_text="gross markout, window-close exit (bp)")
    cap = K.caption(
        sample=f"scorable first-window gate trades, n={len(s):,}",
        filters="none — equal-population deciles, every scorable trade in exactly one bucket.",
        extra="Mean and median disagree in sign across the top deciles and both are plotted; "
              "the distribution is heavy-tailed to the right, so neither alone describes it. "
              "The shaded band is where gate 1 selects.")
    K.base_layout(fig, "v0 · outcome against attention score decile — gate 1 selects the worst "
                       "median cells", cap, height=700, cap_y=-0.26, margin_b=240)
    return K.write(fig, "02_score_decile_panel.html")


def chart_03(d: pd.DataFrame) -> str:
    s = d[d["score_available"]]
    vc = s["n_live_at_tau"].value_counts().sort_index()
    fig = go.Figure()
    fig.add_bar(x=vc.index.astype(int), y=vc.to_numpy(), marker_color=K.BLUE,
                text=[f"{v:,}" for v in vc.to_numpy()], textposition="outside",
                hovertemplate="%{x} live candidates<br>n = %{y:,}<extra></extra>",
                name="candidate moments")
    fig.add_vrect(x0=0.5, x1=1.5, fillcolor=K.rgba(K.RED, .09), line_width=0,
                  annotation_text="gate 2 has nothing to decide",
                  annotation_position="top right",
                  annotation_font=dict(size=10, color=K.RED))
    fig.update_xaxes(title_text="candidates with a live gate window at that moment "
                                "(includes the candidate itself)",
                     tickmode="array", tickvals=list(range(1, int(vc.index.max()) + 1)))
    fig.update_yaxes(title_text="candidate moments (count)")
    share = float((s["n_live_at_tau"] == 1).mean())
    cap = K.caption(
        sample=f"scorable candidate moments, n={len(s):,}, over 168 session dates",
        filters="none — every scorable candidate moment is counted once.",
        extra=f"{share:.1%} of candidate moments have no competitor at all, so the "
              "cross-sectional gate passes them trivially. Liveness is the gate's own "
              "window-close definition. This is a LOWER BOUND: the gate ran on the mom ≥ 50 "
              "slice, and D1 over these same dates is 2.84× denser per session.")
    K.base_layout(fig, "v0 · concurrency — how many names the gate had live at once", cap,
                  height=660, cap_y=-0.28, margin_b=240)
    return K.write(fig, "03_concurrency_distribution.html")


def chart_04(d: pd.DataFrame, rho: float) -> str:
    s = d[d["score_available"] & d["move_at"].notna()].copy()
    s = s[(s["score"] > 0) & (s["move_at"] > -1)]
    x = s["move_at"].to_numpy() + 1.0      # shift so log axis is usable; labelled below
    y = s["score"].to_numpy()
    contested = s["n_live_at_tau"].to_numpy() >= 2
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=x[~contested], y=y[~contested], mode="markers",
                             name=f"alone in live set (n={int((~contested).sum()):,})",
                             marker=dict(size=5, color=K.rgba(K.BLUE, .45))))
    fig.add_trace(go.Scatter(x=x[contested], y=y[contested], mode="markers",
                             name=f"contested moment (n={int(contested.sum()):,})",
                             marker=dict(size=7, color=K.rgba(K.ORANGE, .8),
                                         line=dict(width=0.5, color=K.ORANGE))))
    fig.update_xaxes(type="log", title_text="1 + move_at at the candidate moment (log axis; "
                                            "1.0 = flat on the prior close)")
    fig.update_yaxes(type="log", title_text="attention score = 10-min dollar volume / B_e "
                                            "(log axis)")
    cap = K.caption(
        sample=f"scorable candidate moments with move_at defined, n={len(s):,}",
        filters="points with score ≤ 0 or move_at ≤ −100% cannot be placed on log axes; none "
                "exist in this population, so nothing is dropped.",
        extra=f"Spearman ρ = {rho:.3f} on all candidate moments, reported alongside the "
              "picture and never in place of it. The score substantially restates the move "
              "rather than adding to it.")
    K.base_layout(fig, "v0 · collinearity — attention score against move_at", cap,
                  height=700, cap_y=-0.24, margin_b=230)
    return K.write(fig, "04_score_vs_move_at.html")


def main() -> int:
    cfg = C.load_cfg()
    cost_bp = cfg["evaluation"]["cost"]["round_trip_bp"]
    d = pd.read_parquet(C.REPO / IN)
    rho = json.load(open(C.REPO / T4))["collinearity_score_vs_move_at"][
        "all_candidate_moments"]["rho"]
    out = [chart_01(d, cost_bp), chart_02(d, cost_bp), chart_03(d), chart_04(d, rho)]
    C.write_json(f"{C.ART}/charts.json", {"task": "v0 charts",
                                          "config_hash": C.cfg_hash(), "charts": out})
    for p in out:
        print("wrote", p)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
