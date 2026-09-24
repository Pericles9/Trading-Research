"""
Brief 1 -- the charts behind the T2 HARD STOP (escalation row 4). Written at the stop to show the
distributions the stop is posted on; no task after T2 is run.

  charts/attention_excursion/b1/t2/01_tau_exact_minus_proxy_ecdf.html
  charts/attention_excursion/b1/t2/02_spike_guard_moves.html
  charts/attention_excursion/b1/t1/01_prior_close_exact_vs_minute_bar.html

Dark theme per the brief (II.1). One chart per file, n in every legend entry, nothing clipped: the
signed seconds axis is drawn on asinh so both tails (to -10.5 h and +12 h) stay on the page.

Usage: .venv/Scripts/python.exe research/attention_excursion_b1/charts_t2.py
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd
import plotly.graph_objects as go

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C  # noqa: E402

BG, FG, GRID = "#111418", "#e6e6e6", "#2a2f36"
BLUE, ORANGE, GREEN, RED, GREY = "#4ea1ff", "#ffb347", "#7ed957", "#ff6b6b", "#9aa4b2"


def layout(fig: go.Figure, title: str, xt: str, yt: str) -> go.Figure:
    fig.update_layout(template="plotly_dark", paper_bgcolor=BG, plot_bgcolor=BG,
                      font=dict(color=FG, size=13), title=dict(text=title, x=0.01),
                      legend=dict(bgcolor="rgba(0,0,0,0)", yanchor="top", y=0.98, x=0.01),
                      margin=dict(l=70, r=30, t=90, b=90))
    fig.update_xaxes(title=xt, gridcolor=GRID, zeroline=False)
    fig.update_yaxes(title=yt, gridcolor=GRID, zeroline=False)
    return fig


def ecdf(x: np.ndarray):
    x = np.sort(x)
    return x, np.arange(1, x.size + 1) / x.size


def asinh_ticks():
    vals = [-36000, -3600, -600, -60, -1, 0, 1, 61, 600, 3600, 36000]
    labs = ["-10 h", "-1 h", "-10 m", "-60 s", "-1 s", "0", "+1 s", "+61 s", "+10 m", "+1 h", "+10 h"]
    return [float(np.arcsinh(v)) for v in vals], labs


def main() -> int:
    t2 = pd.read_parquet(C.art("t2_tau.parquet"))
    t1 = pd.read_parquet(C.art("t1_prior_close.parquet"), columns=["event_id", "abs_exact_vs_mb_bp", "exact_vs_mb_bp",
                                                                   "prior_close_source"])
    d = t2[t2["proxy_comparable"]].merge(t1[["event_id", "abs_exact_vs_mb_bp"]], on="event_id")
    n_d1 = len(t2)

    # ---------------------------------------------------------------- T2 chart 1
    fig = go.Figure()
    fig.add_vrect(x0=np.arcsinh(-1), x1=np.arcsinh(61), fillcolor=GREEN, opacity=0.12, line_width=0,
                  annotation_text="band [-1, 61] s", annotation_position="top left")
    series = [
        ("all comparable: tau_exact - tau_proxy", d["d_exact_minus_proxy_s"], BLUE, "solid"),
        ("exact close == minute-bar close", d.loc[d["abs_exact_vs_mb_bp"] == 0, "d_exact_minus_proxy_s"], GREEN, "solid"),
        ("exact close != minute-bar close", d.loc[d["abs_exact_vs_mb_bp"] > 0, "d_exact_minus_proxy_s"], RED, "solid"),
        ("decomposition: tau_mb - tau_proxy (same close as proxy)", d["d_mb_minus_proxy_s"].dropna(), ORANGE, "dot"),
    ]
    for name, s, col, dash in series:
        s = s.dropna().to_numpy()
        out = int(((s < -1) | (s > 61)).sum())
        x, y = ecdf(np.arcsinh(s))
        fig.add_trace(go.Scatter(x=x, y=y, mode="lines", line=dict(color=col, dash=dash, width=2),
                                 name=f"{name} -- n={s.size:,}, outside band {out:,} ({out / s.size:.1%})"))
    tv, tl = asinh_ticks()
    fig.update_xaxes(tickvals=tv, ticktext=tl)
    n_out = int(t2["outside_proxy_band"].sum())
    layout(fig, f"T2 -- tau_exact minus the v1 crossing proxy, D1 (n comparable = {len(d):,} of {n_d1:,})<br>"
                f"<sup>HARD STOP, escalation row 4: {n_out:,} of {n_d1:,} D1 events ({n_out / n_d1:.1%}) outside [-1, 61] s "
                f"against a 2% threshold. The orange curve holds the prior close fixed at the proxy's own.</sup>",
           "tau_exact - tau_proxy (asinh axis; every value drawn, none clipped)", "cumulative share of events")
    fig.write_html(C.chart_path("t2", "01_tau_exact_minus_proxy_ecdf.html"), include_plotlyjs="cdn")

    # ---------------------------------------------------------------- T2 chart 2
    mv = t2.loc[t2["guard_moved_tau"], "guard_move_s"].to_numpy()
    fig = go.Figure()
    edges = np.logspace(np.floor(np.log10(mv.min())), np.ceil(np.log10(mv.max())), 40)
    cnt, _ = np.histogram(mv, bins=edges)
    ctr = np.sqrt(edges[:-1] * edges[1:])
    fig.add_trace(go.Bar(x=ctr, y=cnt, width=np.diff(edges) * 0.9, marker_color=ORANGE,
                         name=f"events whose tau the guard moved -- n={mv.size:,}",
                         hovertemplate="%{x:.3g} s: n=%{y}<extra></extra>"))
    fig.update_xaxes(type="log")
    n_sk = int((t2["n_spikes_skipped"].fillna(0) > 0).sum())
    layout(fig, f"T2 -- how far the spike guard moved tau (n = {mv.size:,} of {int(t2['tau_available'].sum()):,} events with tau)<br>"
                f"<sup>{n_sk:,} events had at least one spike skipped; tau moves later by construction. "
                f"Under the overlay's 1.5% neighbour agreement {int(t2['guard15_differs'].sum()):,} events' tau differs.</sup>",
           "tau (guarded) - tau (no guard), seconds, log axis", "events per bin")
    fig.write_html(C.chart_path("t2", "02_spike_guard_moves.html"), include_plotlyjs="cdn")

    # ---------------------------------------------------------------- T1 chart
    m = t1.dropna(subset=["exact_vs_mb_bp"])
    fig = go.Figure()
    for src, col in [("auction_8_15", BLUE), ("fallback_last_rth_print", ORANGE)]:
        s = m.loc[m["prior_close_source"] == src, "exact_vs_mb_bp"].to_numpy()
        if s.size == 0:
            continue
        x, y = ecdf(np.arcsinh(s))
        fig.add_trace(go.Scatter(x=x, y=y, mode="lines", line=dict(color=col, width=2),
                                 name=f"{src} -- n={s.size:,}, equal {int((s == 0).sum()):,}, |diff|>100 bp {int((np.abs(s) > 100).sum()):,}"))
    tv = [float(np.arcsinh(v)) for v in [-5000, -500, -100, -10, 0, 10, 100, 500, 5000, 30000]]
    fig.update_xaxes(tickvals=tv, ticktext=["-5000", "-500", "-100", "-10", "0", "+10", "+100", "+500", "+5000", "+30000"])
    layout(fig, f"T1 -- exact prior close vs the minute-bar close the earlier move_at build used (n = {len(m):,})<br>"
                "<sup>exact = Amendment 6 {8,15} auction print (else last RTH print); minute-bar = last RTH minute bar's last_price, "
                "which segments on the timestamp rule and so never sees the closing cross</sup>",
           "(exact - minute-bar) / minute-bar, bp (asinh axis; nothing clipped)", "cumulative share of events")
    fig.write_html(C.chart_path("t1", "01_prior_close_exact_vs_minute_bar.html"), include_plotlyjs="cdn")
    print("charts written")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
