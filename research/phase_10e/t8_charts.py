#!/usr/bin/env python
"""
Phase 10e charts 01-05 (Arm 1). Plotly, standalone HTML, one figure per file, offline
--plotlyjs directory, never a CDN (D14). n per bucket always; distributions, not centres;
outliers shown, never clipped. D19: bp and cents together wherever a price quantity appears.

Every chart carries the cell it is drawn from and the config hash in its caption.

Usage: .venv/Scripts/python.exe research/phase_10e/t8_charts.py
"""
from __future__ import annotations

import hashlib
import json
import os

import duckdb
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
CFG = os.path.join(REPO, "config", "phase_10e.json")
A = os.path.join(REPO, "results/phase_10e/artifacts")
CH = os.path.join(REPO, "results/phase_10e/charts")

INK, INK2, GRID, SURF = "#1b1b1a", "#5a5854", "#e6e3dd", "#faf9f7"
OPT, PESS, BE, RW = "#256abf", "#898781", "#c0392b", "#e08a1e"


def save(fig, name, cap):
    fig.update_layout(
        paper_bgcolor="#ffffff", plot_bgcolor=SURF,
        font=dict(family='system-ui, -apple-system, "Segoe UI", sans-serif', size=11,
                  color=INK2),
        margin=dict(l=70, r=40, t=120, b=90))
    fig.add_annotation(text=cap, xref="paper", yref="paper", x=0, y=-0.14,
                       showarrow=False, xanchor="left", align="left",
                       font=dict(size=9, color=INK2))
    fig.update_xaxes(showgrid=True, gridcolor=GRID, linecolor=GRID)
    fig.update_yaxes(gridcolor=GRID, linecolor=GRID, zeroline=False)
    os.makedirs(CH, exist_ok=True)
    p = os.path.join(CH, name)
    fig.write_html(p, include_plotlyjs="directory", full_html=True)
    print(f"  wrote {os.path.relpath(p, REPO)}")


def main() -> int:
    cfg = json.load(open(CFG, encoding="utf-8"))
    chash = hashlib.sha256(open(CFG, "rb").read()).hexdigest()[:12]
    nc = cfg["named_cell"]; rt_bp = cfg["cost"]["round_trip_bp"]
    rt_c = cfg["cost"]["round_trip_cents"]
    g = pd.read_parquet(os.path.join(A, "t3_shares.parquet"))
    pw = g[g.denominator == "print_weighted"].copy()
    strat = pd.read_parquet(os.path.join(A, "t3b_stratification.parquet"))
    base = (f"Phase 10e Arm 1 · config {chash} · round trip {rt_bp} bp / {rt_c} cents "
            f"(Phase 11, not recomputed) · print-weighted denominator")

    c = duckdb.connect(); c.execute("PRAGMA threads=4")
    c.execute("PRAGMA memory_limit='6GB'")
    c.execute(f"create view t2 as select * from "
              f"read_parquet('{os.path.join(A,'t2_excursion.parquet')}')")

    # ---- 01 excursion distribution -------------------------------------------
    hor = cfg["arm1"]["horizons_minutes"]
    qs = np.round(np.arange(0.01, 1.0, 0.01), 2)
    rows = []
    for h in hor:
        d = c.execute(f"""select {','.join(
            f'quantile_cont(mfe_h{h}/fill_price - 1, {q}) as mfe_{int(q*100)}' for q in qs)},
            {','.join(f'quantile_cont(mae_h{h}/fill_price - 1, {q}) as mae_{int(q*100)}'
                      for q in qs)}, count(*) as n
            from t2 where latency_minutes = {nc['latency_minutes']}
              and det_segment = '{nc['det_segment']}'""").fetchdf()
        rows.append((h, d))
    fig = go.Figure()
    for i, (h, d) in enumerate(rows):
        sh = 0.35 + 0.65 * i / max(1, len(rows) - 1)
        fig.add_trace(go.Scatter(
            x=[d[f"mfe_{int(q*100)}"].iloc[0] * 10000 for q in qs], y=qs,
            mode="lines", line=dict(color=f"rgba(37,106,191,{sh:.2f})", width=2.2),
            name=f"MFE, H={h}m (n={int(d.n.iloc[0]):,})"))
        fig.add_trace(go.Scatter(
            x=[d[f"mae_{int(q*100)}"].iloc[0] * 10000 for q in qs], y=qs,
            mode="lines", line=dict(color=f"rgba(192,57,43,{sh:.2f})", width=2.2, dash="dot"),
            name=f"MAE, H={h}m (n={int(d.n.iloc[0]):,})"))
    for mult, lab in ((1, "1x"), (1.5, "1.5x"), (3, "3x profit barrier"),
                      (-2, "2x stop barrier")):
        fig.add_vline(x=mult * rt_bp, line=dict(color=INK, width=1.1, dash="dash"))
        fig.add_annotation(x=mult * rt_bp, y=1.02, yref="paper", text=f"{lab}",
                           showarrow=False, font=dict(size=9, color=INK))
    fig.update_xaxes(title_text="excursion from fill (bp) — "
                                f"1x round trip = {rt_bp} bp = {rt_c} cents",
                     range=[-600, 600])
    fig.update_yaxes(title_text="ECDF", tickformat=".0%")
    fig.update_layout(height=620, title=dict(
        text="<b>01 · What does the path offer from an arbitrary entry?</b><br>"
             "<sup>MFE (blue) and MAE (red dotted), ECDF, one pair per horizon. "
             f"Named cell's latency and segment: L={nc['latency_minutes']}m, "
             f"{nc['det_segment']}. Barriers drawn at 3x profit and 2x stop.</sup>",
        font=dict(size=15, color=INK), x=0.01, xanchor="left"))
    save(fig, "01_excursion_distribution.html",
         base + " · MFE/MAE relative to fill price, both tails shown, nothing clipped")

    # ---- 02 outcome shares ---------------------------------------------------
    d = pw[pw.latency_minutes == nc["latency_minutes"]].copy()
    d["cell"] = "k" + d.profit_k.astype(str) + "/m" + d.stop_m.astype(str)
    fig = make_subplots(rows=1, cols=len(hor), shared_yaxes=True,
                        subplot_titles=[f"H = {h} min" for h in hor])
    for j, h in enumerate(hor, 1):
        s = d[d.horizon_minutes == h].sort_values(["profit_k", "stop_m"])
        for bound, cl in (("optimistic", OPT), ("pessimistic", PESS)):
            fig.add_trace(go.Bar(
                x=s.cell + ("  opt" if bound == "optimistic" else "  pess"),
                y=s[f"p_clear_{bound}"], marker_color=cl, showlegend=(j == 1),
                name=f"p_clear {bound}",
                customdata=np.stack([s.n, s.distinct_events, s.p_breakeven], -1),
                hovertemplate="p_clear %{y:.4f}<br>n %{customdata[0]:,}"
                              "<br>events %{customdata[1]:,}"
                              "<br>p_breakeven %{customdata[2]:.3f}<extra></extra>"),
                row=1, col=j)
        for _, r in s.iterrows():
            for val, cl2 in ((r.p_breakeven, BE), (r.p_randomwalk, RW)):
                fig.add_shape(type="line", x0=-0.5, x1=len(s) * 2 - 0.5, y0=val, y1=val,
                              line=dict(color=cl2, width=1.4, dash="dash"), row=1, col=j)
    fig.update_yaxes(title_text="share", range=[0, 0.85], row=1, col=1)
    fig.update_layout(height=560, barmode="group", title=dict(
        text="<b>02 · How do entries actually end?</b>  "
             "<span style='color:#c0392b'>— p_breakeven</span>  "
             "<span style='color:#e08a1e'>— p_randomwalk</span><br>"
             f"<sup>p_clear under both R1 bounds, latency {nc['latency_minutes']}m, all six "
             "barrier cells. <b>Every bar sits below its own red break-even line in every "
             "panel.</b></sup>",
        font=dict(size=15, color=INK), x=0.01, xanchor="left"))
    save(fig, "02_outcome_shares.html",
         base + " · p_breakeven=(m+1)/(k+m), p_randomwalk=m/(k+m); n per bar in hover")

    # ---- 03 ambiguity --------------------------------------------------------
    lat = cfg["arm1"]["latency_minutes"]
    fig = make_subplots(rows=1, cols=len(lat), shared_yaxes=True,
                        subplot_titles=[f"latency {L} min" for L in lat])
    for j, L in enumerate(lat, 1):
        s = pw[pw.latency_minutes == L]
        piv = s.pivot_table(index="horizon_minutes",
                            columns=["profit_k", "stop_m"], values="ambiguous_share")
        npv = s.pivot_table(index="horizon_minutes",
                            columns=["profit_k", "stop_m"], values="n")
        fig.add_trace(go.Heatmap(
            z=piv.values, x=[f"k{a}/m{b}" for a, b in piv.columns],
            y=[str(i) for i in piv.index], zmin=0, zmax=0.25,
            colorscale="Blues", showscale=(j == len(lat)),
            colorbar=dict(title="ambiguous<br>share", tickformat=".0%"),
            customdata=npv.values,
            hovertemplate="ambiguous %{z:.4f}<br>n %{customdata:,}<extra></extra>"),
            row=1, col=j)
    fig.update_yaxes(title_text="horizon (min)", row=1, col=1)
    fig.update_layout(height=460, title=dict(
        text="<b>03 · Can minute bars answer the first-passage question at all?</b><br>"
             "<sup>R1 ambiguous share = the share of entries where BOTH barriers are first "
             "touched inside the same bar, which is exactly where the two bounds disagree. "
             "Colour scale runs to the 25% reporting trigger (row 10a).</sup>",
        font=dict(size=15, color=INK), x=0.01, xanchor="left"))
    save(fig, "03_ambiguity.html", base + " · n per cell in hover")

    # ---- 04 path position ----------------------------------------------------
    s = strat[strat.axis == "minutes_since_anchor"].sort_values("band")
    fig = go.Figure()
    for bound, cl, lo, hi in (("optimistic", OPT, "ci_opt_lo", "ci_opt_hi"),
                              ("pessimistic", PESS, "ci_pess_lo", "ci_pess_hi")):
        fig.add_trace(go.Scatter(
            x=s.band, y=s[hi], mode="lines", line=dict(width=0), showlegend=False))
        fig.add_trace(go.Scatter(
            x=s.band, y=s[lo], mode="lines", line=dict(width=0), fill="tonexty",
            fillcolor=("rgba(37,106,191,0.18)" if bound == "optimistic"
                       else "rgba(137,135,129,0.18)"), showlegend=False))
        fig.add_trace(go.Scatter(
            x=s.band, y=s[f"p_clear_{bound}"], mode="lines+markers",
            line=dict(color=cl, width=2.6), marker=dict(size=8),
            name=f"p_clear {bound}",
            customdata=np.stack([s.n, s.distinct_events], -1),
            hovertemplate="%{y:.4f}<br>n %{customdata[0]:,}"
                          "<br>events %{customdata[1]:,}<extra></extra>"))
    fig.add_hline(y=float(s.p_breakeven.iloc[0]), line=dict(color=BE, width=1.6, dash="dash"))
    fig.add_hline(y=float(s.p_randomwalk.iloc[0]), line=dict(color=RW, width=1.6, dash="dash"))
    fig.add_annotation(x=s.band.iloc[-1], y=float(s.p_breakeven.iloc[0]), xanchor="right",
                       yanchor="bottom", text="p_breakeven 0.600", showarrow=False,
                       font=dict(size=10, color=BE))
    fig.add_annotation(x=s.band.iloc[-1], y=float(s.p_randomwalk.iloc[0]), xanchor="right",
                       yanchor="bottom", text="p_randomwalk 0.400", showarrow=False,
                       font=dict(size=10, color=RW))
    fig.update_yaxes(title_text="p_clear", range=[0.25, 0.65])
    fig.update_xaxes(title_text="minutes since detection anchor")
    fig.update_layout(height=540, title=dict(
        text="<b>04 · Does where you are on the path matter?</b><br>"
             "<sup>Named cell's barriers (k=3, m=2) and latency. Ribbons are 95% "
             "event-clustered bootstrap CIs, 2,000 reps. <b>Monotone decline across all six "
             "bands — and every band sits below break-even.</b></sup>",
        font=dict(size=15, color=INK), x=0.01, xanchor="left"))
    save(fig, "04_path_position.html",
         base + " · n and distinct events per band in hover; CIs cluster on event")

    # ---- 05 s_min stratification ---------------------------------------------
    s = strat[strat.axis == "s_min_band"].copy()
    ordr = ["[0.0, 0.5)", "[0.5, 1.0)", "[1.0, 2.0)", "[2.0, 5.0)", "[5.0, 10.0)",
            "[10.0, 30.0)", "[30.0, 100.0)", "[100.0, inf)"]
    s["o"] = s.band.map({b: i for i, b in enumerate(ordr)})
    s = s.sort_values("o")
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    for bound, cl, lo, hi in (("optimistic", OPT, "ci_opt_lo", "ci_opt_hi"),
                              ("pessimistic", PESS, "ci_pess_lo", "ci_pess_hi")):
        fig.add_trace(go.Scatter(x=s.band, y=s[hi], mode="lines", line=dict(width=0),
                                 showlegend=False), secondary_y=False)
        fig.add_trace(go.Scatter(
            x=s.band, y=s[lo], mode="lines", line=dict(width=0), fill="tonexty",
            fillcolor=("rgba(37,106,191,0.18)" if bound == "optimistic"
                       else "rgba(137,135,129,0.18)"), showlegend=False),
            secondary_y=False)
        fig.add_trace(go.Scatter(
            x=s.band, y=s[f"p_clear_{bound}"], mode="lines+markers",
            line=dict(color=cl, width=2.6), marker=dict(size=8),
            name=f"p_clear {bound}",
            customdata=np.stack([s.n, s.distinct_events], -1),
            hovertemplate="%{y:.4f}<br>n %{customdata[0]:,}"
                          "<br>events %{customdata[1]:,}<extra></extra>"), secondary_y=False)
    fig.add_trace(go.Bar(x=s.band, y=s.median_mfe_bp, marker_color="rgba(30,140,90,0.30)",
                         name="median MFE (bp)", customdata=s.n.to_numpy()[:, None],
                         hovertemplate="median MFE %{y:.1f} bp<br>n %{customdata[0]:,}"
                                       "<extra></extra>"), secondary_y=True)
    fig.add_hline(y=float(s.p_breakeven.iloc[0]), line=dict(color=BE, width=1.6, dash="dash"))
    fig.add_hline(y=float(s.p_randomwalk.iloc[0]), line=dict(color=RW, width=1.6, dash="dash"))
    fig.update_yaxes(title_text="p_clear", range=[0.25, 0.65], secondary_y=False)
    fig.update_yaxes(title_text="median MFE (bp)", secondary_y=True, showgrid=False)
    fig.update_xaxes(title_text="s_min band (seconds) — smaller = faster, more resolvable tape")
    fig.update_layout(height=560, title=dict(
        text="<b>05 · Does the tape's resolvability relate to what the path pays?</b><br>"
             "<sup>RTH only, named cell's barriers. <b>Not flat</b> — p_clear falls from "
             "0.378 at the fastest tape to 0.300 at the slowest, and median MFE falls with "
             "it. s_min is therefore more than an estimability gate. Every band is still "
             "below break-even.</sup>",
        font=dict(size=15, color=INK), x=0.01, xanchor="left"))
    save(fig, "05_smin_stratification.html",
         base + " · RTH only; s_min = 2.26/lambda from the bar's print count; "
                "CIs cluster on event")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
