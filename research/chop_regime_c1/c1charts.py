"""
Chop regime C1 -- charts. Plotly, standalone HTML, one chart per file, dark theme, one offline plotly.min.js per chart
folder (D14). Every chart carries its sample, filters and config hash; n is on every panel.

T5 (the section 6 controls; the record of the T5 HARD STOP):
  01_null_er_by_rung          per-window ER statistic of both noise nulls per rung and basis, the 0.90-1.10 band shaded
  02_null_vz_by_rung          the nulls' vz2 / vz4 median and standard deviation per rung (two stacked panels, shared x)
  03_real_vz2_tails           ECDF of |vz2| on the real windows, per basis, log x
  04_whole_pipeline_constructions   T5a: the literal, bridge0 and bootstrap constructions against the bands
  05_positive_controls        median er_rel against injected drift; median vz2 against AR(1) phi

Deviation, recorded here and in REPORT.md: the null z-draws were pooled in memory and only their n, median and standard
deviation were kept, so 02 shows the spread as a standard deviation; 03 carries the real windows' full distribution.

Usage: .venv/Scripts/python.exe research/chop_regime_c1/c1charts.py
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import c1common as C  # noqa: E402

BG, FG, GRID = "#111418", "#e6e6e6", "#2a2f36"
COL = {"mid": "#4C9AFF", "vwap": "#FF8B3D"}          # two categorical slots, a blue / orange pair
BAND = "rgba(120, 200, 120, 0.15)"
CFG = C.load_cfg()
NR = CFG["controls"]["negative_references"]


def style(fig, title: str, caption: str, h: int = 620):
    fig.update_layout(template="plotly_dark", paper_bgcolor=BG, plot_bgcolor=BG, height=h, font=dict(color=FG, size=12),
                      title=dict(text=title, x=0.01), margin=dict(l=70, r=30, t=80, b=120))
    fig.add_annotation(text=caption, xref="paper", yref="paper", x=0, y=-0.16, showarrow=False, align="left", font=dict(size=11, color="#9aa4ae"),
                       xanchor="left", yanchor="top")
    fig.update_xaxes(gridcolor=GRID)
    fig.update_yaxes(gridcolor=GRID)
    return fig


def save(fig, task: str, name: str) -> None:
    p = C.chart_path(task, name)
    fig.write_html(str(p), include_plotlyjs="directory")


def caption(extra: str) -> str:
    return (f"Sample: the 53 quarantined events with tau (dev_v3 49, dev_v4 sidecar 4), every valid scale-free window (>= 64 collapsed trades, 32 buckets). "
            f"{extra}<br>config {C.cfg_hash()} · research/chop_regime_c1/t5_controls.py · synthetic nulls, not market outcomes")


def chart_01(W: pd.DataFrame) -> None:
    fig = make_subplots(rows=2, cols=2, shared_xaxes=True, subplot_titles=[
        "references · midpoint", "references · VWAP", "whole pipeline (literal shuffle) · midpoint", "whole pipeline (literal shuffle) · VWAP"],
        vertical_spacing=0.12, horizontal_spacing=0.07)
    for r, (col, lab) in enumerate((("ref_er_ratio", "mean resampled er / er_0"), ("wp_er_rel_mean", "mean shuffled er_rel")), start=1):
        for c, bs in enumerate(C.BASES, start=1):
            g = W[(W["basis"] == bs) & W[col].notna()]
            ks = sorted(g["k"].unique())
            for k in ks:
                x = g.loc[g["k"] == k, col]
                fig.add_trace(go.Box(y=x, x=[k] * len(x), name=f"k={k}", marker_color=COL[bs], boxpoints="outliers", showlegend=False,
                                     hovertemplate=f"rung {k}<br>{lab}: %{{y:.3f}}<br>n windows {len(x)}<extra></extra>"), row=r, col=c)
            med = g.groupby("k")[col].median()
            n = g.groupby("k")[col].size()
            fig.add_trace(go.Scatter(x=med.index, y=med.values, mode="markers+text", marker=dict(color="white", size=7, symbol="diamond"),
                                     text=[f"n={v}" for v in n.values], textposition="top center", textfont=dict(size=9), showlegend=False,
                                     hovertemplate="rung %{x}<br>median %{y:.3f}<extra></extra>"), row=r, col=c)
            fig.add_hrect(y0=NR["er_ratio_band"][0], y1=NR["er_ratio_band"][1], fillcolor=BAND, line_width=0, row=r, col=c)
            fig.update_yaxes(title_text=lab, type="log", row=r, col=c)
    fig.update_xaxes(title_text="rung k (window = H_t / 2^k)", row=2)
    style(fig, "Null ER statistic per rung — band 0.90–1.10 shaded (white diamond = median over windows)",
          caption("Per window: references = mean over 200 resamples of the window's demeaned bucket returns of er, over the closed-form er_0; whole pipeline = "
                  "mean over 20 permutations of the print-level (VWAP) or quote-update (midpoint) log returns of er_rel. Log y; boxes show every rung's windows."), h=820)
    save(fig, "t5", "01_null_er_by_rung.html")


def chart_02(P: pd.DataFrame) -> None:
    P = P[P["control"].isin(["references", "whole_pipeline"]) & (P["rung"] != "all")].copy()
    P["k"] = P["rung"].astype(int)
    fig = make_subplots(rows=2, cols=2, shared_xaxes=True, subplot_titles=["midpoint · median z", "VWAP · median z", "midpoint · SD of z (log)", "VWAP · SD of z (log)"],
                        vertical_spacing=0.12, horizontal_spacing=0.07)
    dash = {"references": "solid", "whole_pipeline": "dot"}
    sym = {2: "circle", 4: "square"}
    for c, bs in enumerate(C.BASES, start=1):
        for ctl in ("references", "whole_pipeline"):
            g = P[(P["basis"] == bs) & (P["control"] == ctl)].sort_values("k")
            for q in (2, 4):
                kw = dict(mode="lines+markers", line=dict(color=COL[bs], dash=dash[ctl]), marker=dict(symbol=sym[q], size=7),
                          name=f"{ctl} vz{q}", legendgroup=f"{ctl}{q}", showlegend=(c == 1),
                          customdata=g[f"vz{q}_n"], hovertemplate=f"{ctl} vz{q}<br>rung %{{x}}<br>%{{y:.4g}}<br>n draws %{{customdata}}<extra></extra>")
                fig.add_trace(go.Scatter(x=g["k"], y=g[f"vz{q}_median"], **kw), row=1, col=c)
                fig.add_trace(go.Scatter(x=g["k"], y=g[f"vz{q}_sd"], **{**kw, "showlegend": False}), row=2, col=c)
        fig.add_hrect(y0=-NR["vz_abs_median_max"], y1=NR["vz_abs_median_max"], fillcolor=BAND, line_width=0, row=1, col=c)
        fig.add_hrect(y0=NR["vz_sd_band"][0], y1=NR["vz_sd_band"][1], fillcolor=BAND, line_width=0, row=2, col=c)
        fig.update_yaxes(type="log", title_text="SD of z", row=2, col=c)
        fig.update_yaxes(title_text="median z", row=1, col=c)
    fig.update_xaxes(title_text="rung k", row=2)
    style(fig, "Null variance-ratio z per rung — median (top, band ±0.15) and SD (bottom, band 0.80–1.25, log y)",
          caption("Two stacked panels share the rung axis (no dual axis). Solid = references (200 resamples per window), dotted = whole pipeline (20 permutations); "
                  "circle vz2, square vz4. The pooled draws were not retained, so spread is shown as an SD (deviation recorded in REPORT.md); n draws per point in hover."), h=820)
    save(fig, "t5", "02_null_vz_by_rung.html")


def chart_03(W: pd.DataFrame) -> None:
    fig = go.Figure()
    for bs in C.BASES:
        z = np.sort(W.loc[(W["basis"] == bs) & W["vz2"].notna(), "vz2"].abs().to_numpy())
        z = np.maximum(z, 1e-6)
        y = np.arange(1, z.size + 1) / z.size
        step = max(1, z.size // 4000)
        idx = np.r_[np.arange(0, z.size, step), z.size - 1]
        fig.add_trace(go.Scatter(x=z[idx], y=y[idx], mode="lines", line=dict(color=COL[bs]), name=f"{bs} (n={z.size:,})"))
        tail = W.loc[W["basis"] == bs, "vz2"].abs()
        fig.add_annotation(x=np.log10(30), y=0.2 + (0.1 if bs == "mid" else 0), xref="x", yref="y", showarrow=False, font=dict(color=COL[bs]),
                           text=f"{bs}: |vz2| > 10 in {(tail > 10).mean():.2%}, > 100 in {(tail > 100).mean():.2%}")
    fig.add_vline(x=1.64, line=dict(color="#9aa4ae", dash="dash"))
    fig.update_xaxes(type="log", title_text="|vz2| on the real window (log)")
    fig.update_yaxes(title_text="share of windows ≤ x")
    style(fig, "Real windows: ECDF of |vz2| per basis (dashed: 1.64)",
          caption("Real bucket returns (not a null). ECDF drawn on every point up to 4,000 per line (even stride); all windows count in n and in the tail shares. "
                  "|vz2| floored at 1e-6 for the log axis only."))
    save(fig, "t5", "03_real_vz2_tails.html")


def chart_04(D: pd.DataFrame) -> None:
    D = D[D["rung"] == "all"]
    stats = [("er_statistic_median", "median over windows of mean er_rel", NR["er_ratio_band"], "linear"),
             ("vz2_median", "pooled median vz2", (-NR["vz_abs_median_max"], NR["vz_abs_median_max"]), "linear"),
             ("vz4_median", "pooled median vz4", (-NR["vz_abs_median_max"], NR["vz_abs_median_max"]), "linear"),
             ("vz2_sd", "pooled SD vz2 (log)", NR["vz_sd_band"], "log"), ("vz4_sd", "pooled SD vz4 (log)", NR["vz_sd_band"], "log")]
    fig = make_subplots(rows=1, cols=5, subplot_titles=[s[1] for s in stats], horizontal_spacing=0.06)
    for i, (col, _, band, ax) in enumerate(stats, start=1):
        for bs in C.BASES:
            g = D[D["basis"] == bs]
            fig.add_trace(go.Scatter(x=g["kind"], y=g[col].replace([np.inf], np.nan), mode="markers", marker=dict(color=COL[bs], size=11),
                                     name=bs, showlegend=(i == 1), customdata=g["windows"],
                                     hovertemplate="%{x}<br>%{y:.4g}<br>n windows %{customdata}<extra></extra>"), row=1, col=i)
        fig.add_hrect(y0=band[0], y1=band[1], fillcolor=BAND, line_width=0, row=1, col=i)
        fig.update_yaxes(type=ax, row=1, col=i)
    style(fig, "T5a — the whole-pipeline null under three constructions, against the reference bands (shaded)",
          caption("literal = the brief's text (raw returns permuted: a bridge carrying the window's own net move); bridge0 = demeaned returns permuted; "
                  "bootstrap = demeaned returns drawn with replacement. 20 draws per window, pooled over rungs; n windows in hover. "
                  "research/chop_regime_c1/t5a_whole_pipeline_diagnosis.py"), h=560)
    save(fig, "t5", "04_whole_pipeline_constructions.html")


def chart_05(P: pd.DataFrame, summ: dict) -> None:
    fig = make_subplots(rows=1, cols=2, subplot_titles=["trend: median er_rel against injected drift d", "autocorrelation: median vz2 against AR(1) phi"])
    for bs in C.BASES:
        t = P[(P["basis"] == bs) & P["control"].str.startswith("trend_d")].copy()
        t["d"] = t["control"].str.replace("trend_d", "").astype(float)
        t = t.sort_values("d")
        fig.add_trace(go.Scatter(x=t["d"], y=t["er_statistic_median"], mode="lines+markers", line=dict(color=COL[bs]), name=bs, customdata=t["windows"],
                                 hovertemplate="d %{x}<br>median er_rel %{y:.3f}<br>n draws %{customdata}<extra></extra>"), row=1, col=1)
        a = P[(P["basis"] == bs) & P["control"].str.startswith("ar_")].copy()
        a["phi"] = a["control"].str.replace("ar_", "").astype(float)
        a = a.sort_values("phi")
        fig.add_trace(go.Scatter(x=a["phi"], y=a["vz2_median"], mode="lines+markers", line=dict(color=COL[bs]), name=bs, showlegend=False, customdata=a["windows"],
                                 hovertemplate="phi %{x}<br>median vz2 %{y:.3f}<br>n draws %{customdata}<extra></extra>"), row=1, col=2)
    fig.add_hline(y=2.0, line=dict(color="#9aa4ae", dash="dash"), row=1, col=1)
    fig.add_hline(y=1.0, line=dict(color="#555", dash="dot"), row=1, col=1)
    for y in (1.64, -1.64):
        fig.add_hline(y=y, line=dict(color="#9aa4ae", dash="dash"), row=1, col=2)
    fig.update_xaxes(title_text="d (own-noise units across the window)", row=1, col=1)
    fig.update_xaxes(title_text="phi", row=1, col=2)
    fig.update_yaxes(title_text="median er_rel", row=1, col=1)
    fig.update_yaxes(title_text="median vz2", row=1, col=2)
    style(fig, "Positive controls — injected trend and autocorrelation (dashed: 2.0; ±1.64; d = 1 and phi = ±0.25 are the edge of detectability, report only)",
          caption("50 resamples per window of its demeaned bucket returns, plus d x s / sqrt(32) per step (trend) or through AR(1) (autocorrelation); pooled over rungs."), h=560)
    save(fig, "t5", "05_positive_controls.html")


def main() -> int:
    W = pd.read_parquet(C.art("t5_windows.parquet"))
    P = pd.read_parquet(C.art("t5_pooled.parquet"))
    D = pd.read_parquet(C.art("t5a_whole_pipeline_diagnosis.parquet"))
    summ = C.read_json("t5_summary.json")
    chart_01(W)
    chart_02(P)
    chart_03(W)
    chart_04(D)
    chart_05(P, summ)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
