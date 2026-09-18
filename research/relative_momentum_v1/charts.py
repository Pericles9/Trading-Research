"""
v1 charts.

01 -- markout distribution: baseline against Policy B, POST-WARMUP, plus v0's in-sample gate 1
      recomputed on this population. The third series is what separates the causal fix from the
      population fix. ECDF, so each median is a crossing and the whole shape is on the page.
02 -- the score decile panel on the corrected population.
03 -- Fix 4: net markout by detection-price decile, both cost units, no policy applied. The
      per-share leg is what makes the price axis dominate.
04 -- Fix 3: the share of candidate moments with a competitor, across the declared liveness
      sweep, D1 against the gate population, faceted by year.
05 -- the causal gate-1 threshold as it actually moved through the sample, with the warmup
      region marked and v0's in-sample level drawn for contrast.

Usage: .venv/Scripts/python.exe research/relative_momentum_v1/charts.py
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np
import pandas as pd
import plotly.graph_objects as go

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from research.relative_momentum_v1 import chart_common as K  # noqa: E402
from research.relative_momentum_v1 import common as C  # noqa: E402

IN = f"{C.ART}/t4_diagnostic.parquet"
T5 = f"{C.ART}/t5_d1_concurrency.json"


def chart_01(d: pd.DataFrame, cost_bp: float) -> str:
    post = d[~d["gate1_warmup"]]
    ser = [
        ("A · baseline, post-warmup", post, K.BLUE),
        ("B · both gates, post-warmup (causal gate 1)", post[post["policy_b"]], K.ORANGE),
        ("B1-v0 · v0's in-sample gate 1, this population",
         d[d["gate1_level_v0_style_insample"]], K.VIOLET),
    ]
    fig = go.Figure()
    for label, sub, color in ser:
        v = np.sort(sub["gross_pnl_pct"].to_numpy(dtype=float) * 100)
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
                       text=f"flat cost {cost_bp:.0f} bp", showarrow=False,
                       font=dict(size=10, color=K.RED))
    med_ps = float(np.nanmedian(d["cost_cents_bp"]))
    fig.add_vline(x=med_ps, line_width=1.5, line_dash="dot", line_color=K.INK2)
    fig.add_annotation(x=med_ps, y=0.92, yref="paper", yanchor="bottom",
                       text=f"median per-share cost {med_ps:.0f} bp", showarrow=False,
                       font=dict(size=10, color=K.INK2))
    fig.add_hline(y=0.5, line_width=1, line_dash="dot", line_color=K.INK2)
    fig.update_xaxes(title_text="gross markout, window-close exit (bp; view window ±4,000)",
                     range=[-4000, 4000])
    fig.update_yaxes(title_text="cumulative share of trades", range=[0, 1])
    cap = K.caption(
        sample="gap-gated first-window trades, n=903 total, 653 post-warmup; "
               "2023-11-17 to 2024-07-22",
        filters="nothing trimmed or clipped; curves run flat past the view window. Policy rows "
                "are post-warmup, the subset where the causal gate 1 was actually active.",
        extra="Population fixed (gap gate ON, median move_at at entry +36%) and gate 1 made "
              "causal. The purple series is v0's in-sample threshold on this same population, so "
              "the causal fix is separable from the population fix.")
    K.base_layout(fig, "v1 · markout distribution — the level gate still degrades the median",
                  cap, height=700, cap_y=-0.24, margin_b=240)
    return K.write(fig, "01_markout_distribution.html")


def chart_02(d: pd.DataFrame, cost_bp: float) -> str:
    s = d.copy()
    s["dec"] = pd.qcut(s["score"], 10, labels=False, duplicates="drop")
    g = s.groupby("dec")["gross_pnl_pct"]
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
    fig.update_xaxes(title_text="attention score decile", tickmode="array",
                     tickvals=list(range(10)))
    fig.update_yaxes(title_text="gross markout (bp)")
    cap = K.caption(
        sample=f"gap-gated first-window trades with a score, n={len(s):,}",
        filters="none — equal-population deciles, every trade in exactly one bucket.",
        extra="Mean and median disagree in sign in the top deciles and both are plotted. On this "
              "population move_at is compressed to a narrow band around +30% by the gap gate, so "
              "the score is no longer largely a restatement of the move (ρ 0.69 → 0.43) and the "
              "top decile is still the worst median cell.")
    K.base_layout(fig, "v1 · outcome against attention score decile, corrected population", cap,
                  height=700, cap_y=-0.26, margin_b=240)
    return K.write(fig, "02_score_decile_panel.html")


def chart_03(d: pd.DataFrame, cost_bp: float) -> str:
    g = d.groupby("detection_price_decile")
    x = np.arange(10)
    gross = (g["gross_pnl_pct"].median() * 100).to_numpy()
    net_flat = gross - cost_bp
    net_ps = g["net_bp_per_share"].median().to_numpy()
    n = g.size().to_numpy()
    px = g["detection_price"].median().to_numpy()
    fig = go.Figure()
    for y, color, name in [(gross, K.BLUE, "gross median"),
                           (net_flat, K.ORANGE, "net median — flat 70.98 bp"),
                           (net_ps, K.RED, "net median — per-share 2.512¢")]:
        fig.add_trace(go.Scatter(x=x, y=y, mode="lines+markers", name=name,
                                 line=dict(color=color, width=2.5), marker=dict(size=8),
                                 hovertemplate=name + "<br>decile %{x}<br>%{y:,.0f} bp"
                                               "<extra></extra>"))
    fig.add_trace(go.Scatter(x=x, y=gross, mode="text",
                             text=[f"n={a}<br>${b:,.2f}" for a, b in zip(n, px)],
                             textposition="top center", textfont=dict(size=9, color=K.INK2),
                             showlegend=False, hoverinfo="skip"))
    fig.add_hline(y=0, line_width=2, line_dash="dash", line_color=K.INK)
    fig.update_xaxes(title_text="detection-price decile (0 = cheapest)", tickmode="array",
                     tickvals=list(range(10)))
    fig.update_yaxes(title_text="markout (bp)")
    cap = K.caption(
        sample=f"gap-gated first-window trades, n={len(d):,}. Detection price and decile reused "
               "from E1's artifact (F1-T6's tick-derived construction), not re-derived.",
        filters="none — no policy applied on this chart. Bucket n and median detection price are "
                "annotated; all ten deciles are above the display floor of 20.",
        extra="Fix 4. The per-share leg is what makes the price axis dominate: a fixed 2.512¢ is "
              "an enormous bp cost on a $0.28 name and a small one on a $29 name. The gate "
              "policies do NOT move along this axis — all of them sit at decile median 3.")
    K.base_layout(fig, "v1 · Fix 4 — markout by detection-price decile, no policy applied", cap,
                  height=700, cap_y=-0.26, margin_b=250)
    return K.write(fig, "03_price_decile_panel.html")


def chart_04(t5: dict) -> str:
    caps = ["9", "15", "30", "60"]
    by_year = t5["concurrency_on_5min_grid_by_year"]
    years = sorted(by_year["9"].keys())
    fig = go.Figure()
    for cap, color in zip(caps, [K.BLUE, K.ORANGE, K.AQUA, K.VIOLET]):
        y = [by_year[cap][yr]["share_two_or_more_where_any_live"] * 100 for yr in years]
        fig.add_trace(go.Scatter(x=years, y=y, mode="lines+markers",
                                 name=f"D1, liveness {cap} min",
                                 line=dict(color=color, width=2.5), marker=dict(size=8),
                                 hovertemplate=f"liveness {cap} min<br>%{{x}}<br>"
                                               "%{y:.1f}%<extra></extra>"))
    gate = t5["v1_gate_population_reference"]["share_alone"]
    fig.add_hline(y=(1 - gate) * 100, line_width=2, line_dash="dot", line_color=K.RED)
    fig.add_annotation(xref="paper", x=0.02, y=(1 - gate) * 100, yanchor="bottom",
                       text=f"v1 gate population, measured: {(1 - gate) * 100:.1f}%",
                       showarrow=False, font=dict(size=10, color=K.RED))
    fig.update_xaxes(title_text="event year")
    fig.update_yaxes(title_text="share of live grid points with ≥ 2 candidates (%)")
    cov = t5["coverage"]
    cap = K.caption(
        sample=f"all of D1 with a computable +30% crossing: {cov['n_with_crossing']:,} of "
               f"{cov['n_d1']:,} events ({cov['share']:.1%}), 1,257 session dates, "
               "5-minute grid over 04:00–20:00 ET",
        filters=f"{cov['n_without_crossing']} events have no minute bar reaching +30% of the "
                "tick-derived prior close and are carried with tau unavailable, never dropped. "
                "'no cap' is in the artifact but off this chart — it is not a gate.",
        extra="Fix 3. Liveness is a declared a-priori sweep, read across, never selected from. "
              "The candidate moment is the first +30% crossing, which fires EARLIER than an EPG "
              "rising edge, so every number here is an UPPER bound on what a full-D1 gate "
              "re-derivation could find.")
    K.base_layout(fig, "v1 · Fix 3 — how often D1 offers a cross-section at all", cap,
                  height=680, cap_y=-0.26, margin_b=250)
    return K.write(fig, "04_d1_concurrency.html")


def chart_05(d: pd.DataFrame) -> str:
    s = d.sort_values("entry_ts").reset_index(drop=True)
    x = pd.to_datetime(s["entry_ts"], unit="ns", utc=True)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=x, y=s["score"], mode="markers", name="candidate score",
                             marker=dict(size=4, color=K.rgba(K.BLUE, .35)),
                             hovertemplate="%{x}<br>score %{y:,.1f}<extra></extra>"))
    fig.add_trace(go.Scatter(x=x, y=s["gate1_threshold_causal"], mode="lines",
                             name="causal gate-1 threshold (75th pct of prior observations)",
                             line=dict(color=K.ORANGE, width=2.5),
                             hovertemplate="%{x}<br>threshold %{y:,.1f}<extra></extra>"))
    ins = float(np.quantile(s["score"].to_numpy(dtype=float), 0.75))
    fig.add_hline(y=ins, line_width=2, line_dash="dash", line_color=K.VIOLET)
    fig.add_annotation(xref="paper", x=0.99, y=np.log10(ins), yanchor="bottom", xanchor="right",
                       text=f"v0's in-sample threshold on this population: {ins:,.0f}",
                       showarrow=False, font=dict(size=10, color=K.VIOLET))
    warm = s[s["gate1_warmup"]]
    if len(warm):
        fig.add_vrect(x0=x.iloc[0], x1=x.iloc[len(warm) - 1],
                      fillcolor=K.rgba(K.RED, .07), line_width=0,
                      annotation_text=f"gate-1 warmup: {len(warm)} candidates "
                                      f"({len(warm) / len(s):.1%}), all pass by default",
                      annotation_position="top left",
                      annotation_font=dict(size=10, color=K.RED))
    fig.update_yaxes(type="log", title_text="attention score (log axis)")
    fig.update_xaxes(title_text="candidate moment (UTC)")
    cap = K.caption(
        sample=f"gap-gated candidates in chronological order, n={len(s):,}",
        filters="none — every candidate plotted. The threshold line is undefined during warmup "
                "and starts where the 250th prior observation lands.",
        extra="Fix 1. The threshold uses only observations strictly before each moment, so it is "
              "computable on day one of live trading. It drifts 151 → 220 across the sample, "
              "which is why it is drawn rather than quoted as one number.")
    K.base_layout(fig, "v1 · Fix 1 — the causal gate-1 threshold as it actually moved", cap,
                  height=680, cap_y=-0.26, margin_b=240)
    return K.write(fig, "05_causal_gate1_threshold.html")


def main() -> int:
    cfg = C.load_cfg()
    cost_bp = cfg["evaluation"]["cost"]["round_trip_bp"]
    d = pd.read_parquet(C.REPO / IN)
    t5 = json.load(open(C.REPO / T5))
    out = [chart_01(d, cost_bp), chart_02(d, cost_bp), chart_03(d, cost_bp),
           chart_04(t5), chart_05(d)]
    C.write_json(f"{C.ART}/charts.json",
                 {"task": "v1 charts", "config_hash": C.cfg_hash(), "charts": out})
    for p in out:
        print("wrote", p)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
