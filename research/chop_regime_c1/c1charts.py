"""
Chop regime C1 -- REPORT charts (T9, Amendment 1 run). Plotly, standalone HTML, one chart per file, dark theme, one offline
plotly.min.js per chart folder (D14). Sample, filters and config hash in every caption; n on every panel. No outcome
column is charted here (the outcome panels are in the suite).

  t5/01_null_er_by_rung          the A1.3 null on the 53 quarantined events per rung and basis: band, median, the real er
                                 median, and the trend-injected medians (d = 1, 2, 4)
  t5/02_positive_cells           per cell: median er at d = 4 against the cell's null 95th value (gate: above, cells >= 20)
  t5/03_whole_pipeline_constructions   the first run's diagnosis (t5a): three null constructions against the first run's bands
  t5/04_sweep                    er and cost_noise medians at 16 / 32 / 64 buckets
  t6/01_coverage                 moment-minutes per segment and the unavailable shares (no scale-free rung, no rate rung, no
                                 quote at t, VWAP fallback)
  t6/02_rung_availability        share of moment-minutes with a valid rung k, both ladders, per segment
  t6/03_measure_distributions    every causal measure's weighted ECDF per segment (selector), from a seeded subsample
  t6/04_basis_agreement          Spearman of er, midpoint vs VWAP, per rung and segment, development slice
  t6b/01_null_bands              the development-slice null band per segment x tier x rung, beside the real er quartiles

Usage: .venv/Scripts/python.exe research/chop_regime_c1/c1charts.py
"""
from __future__ import annotations

import os
import shutil
import sys

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import c1common as C  # noqa: E402

BG, FG, GRID = "#111418", "#e6e6e6", "#2a2f36"
COL = {"mid": "#4C9AFF", "vwap": "#FF8B3D"}
SEGC = {"premarket": "#c39bff", "regular": "#4C9AFF", "after_hours": "#7bd88f"}
BAND = "rgba(150, 150, 150, 0.22)"
TIERS = ["<$1", "$1-3", "$3-10", ">=$10"]
CFG = C.load_cfg()


def style(fig, title, caption, h=620):
    fig.update_layout(template="plotly_dark", paper_bgcolor=BG, plot_bgcolor=BG, height=h, font=dict(color=FG, size=12),
                      title=dict(text=title, x=0.01), margin=dict(l=70, r=30, t=80, b=130))
    fig.add_annotation(text=caption, xref="paper", yref="paper", x=0, y=-0.17, showarrow=False, align="left", font=dict(size=11, color="#9aa4ae"),
                       xanchor="left", yanchor="top")
    fig.update_xaxes(gridcolor=GRID)
    fig.update_yaxes(gridcolor=GRID)
    return fig


def save(fig, task, name):
    fig.write_html(str(C.chart_path(task, name)), include_plotlyjs="directory")


def cap(sample, extra, code):
    return f"{sample}. {extra}<br>config {C.cfg_hash()} · {code}"


Q53 = "Sample: the 53 quarantined events with tau, every valid scale-free window (>= 64 collapsed trades, 32 buckets); synthetic nulls, not market outcomes"
DEV = "Sample: the 7,525 development-slice events with tau (2020-22), every non-auction moment, weighted by moment-minutes"


def t5_charts():
    s = C.read_json("t5_summary.json")
    R = pd.DataFrame(s["per_rung"])
    fig = make_subplots(rows=1, cols=2, subplot_titles=["midpoint (primary)", "VWAP (check)"], shared_yaxes=True)
    for c, bs in enumerate(("mid", "vwap"), start=1):
        g = R[R["basis"] == bs].sort_values("k")
        fig.add_trace(go.Scatter(x=g["k"], y=g["null_p95"], mode="lines", line=dict(width=0), showlegend=False, hoverinfo="skip"), row=1, col=c)
        fig.add_trace(go.Scatter(x=g["k"], y=g["null_p05"], mode="lines", line=dict(width=0), fill="tonexty", fillcolor=BAND, name="null 5–95%", showlegend=c == 1), row=1, col=c)
        fig.add_trace(go.Scatter(x=g["k"], y=g["null_median"], mode="lines+markers", line=dict(color="white", dash="dot"), name="null median", showlegend=c == 1,
                                 text=[f"n windows {w:,}, draws {d:,}" for w, d in zip(g["windows"], g["null_draws"])], hovertemplate="rung %{x}<br>%{y:.3f}<br>%{text}<extra></extra>"),
                      row=1, col=c)
        fig.add_trace(go.Scatter(x=g["k"], y=g["real_er_median"], mode="markers", marker=dict(color=COL[bs], size=8), name="real er median", showlegend=c == 1), row=1, col=c)
        for d, dash in ((1, "dot"), (2, "dash"), (4, "solid")):
            fig.add_trace(go.Scatter(x=g["k"], y=g[f"median_er_d{d}"], mode="lines", line=dict(color="#ffd479", dash=dash, width=1.5), name=f"null + drift d = {d}",
                                     showlegend=c == 1), row=1, col=c)
        fig.add_trace(go.Scatter(x=g["k"], y=[1.02] * len(g), mode="text", text=[f"{w:,}" for w in g["windows"]], textfont=dict(size=9, color="#9aa4ae"),
                                 showlegend=False, hoverinfo="skip"), row=1, col=c)
    fig.update_xaxes(title_text="rung k (window = H_t / 2^k)")
    fig.update_yaxes(title_text="er", range=[0, 1.06], row=1, col=1)
    style(fig, "A1.3 null on the 53 quarantined events: er per rung (numbers at the top: n windows per rung)",
          cap(Q53, "20 draws per window: the window's demeaned print-level (VWAP) or quote-update (midpoint) returns resampled with replacement, re-integrated and bucketed "
                   "as real data; drift d adds d own-noise units of the null walk across the window.", "research/chop_regime_c1/t5_controls.py"))
    save(fig, "t5", "01_null_er_by_rung.html")

    c = pd.read_parquet(C.art("t5_cells.parquet"))
    fig = go.Figure()
    for bs in ("mid", "vwap"):
        for gated, sym in ((True, "circle"), (False, "circle-open")):
            g = c[(c["basis"] == bs) & (c["gated"] == gated)]
            fig.add_trace(go.Scatter(x=g["null_p95"], y=g["median_er_d4"], mode="markers", marker=dict(color=COL[bs], symbol=sym, size=8),
                                     name=f"{bs} · {'gated (≥ 20 windows)' if gated else 'shown, < 20 windows'} (n cells {len(g)})",
                                     text=[f"{a} · n windows {b}" for a, b in zip(g["cell"], g["windows"])], hovertemplate="%{text}<br>null p95 %{x:.3f}<br>d=4 median %{y:.3f}<extra></extra>"))
    f = c[c["pass"] == False]  # noqa: E712
    fig.add_trace(go.Scatter(x=f["null_p95"], y=f["median_er_d4"], mode="markers+text", marker=dict(color="#ff6b6b", size=14, symbol="x"), text=f["cell"],
                             textposition="bottom right", name=f"failing (n {len(f)})"))
    fig.add_trace(go.Scatter(x=[0, 1], y=[0, 1], mode="lines", line=dict(color="#9aa4ae", dash="dash"), name="y = x (pass: above)"))
    fig.update_xaxes(title_text="cell's null 95th value (er)", range=[0, 1.03])
    fig.update_yaxes(title_text="median er at d = 4", range=[0, 1.03])
    style(fig, "Positive control per cell (segment × rung × price tier × basis): median er at d = 4 against the cell's null 95th value",
          cap(Q53, "Pass: above y = x in every cell holding ≥ 20 windows. er ≤ 1, so a cell whose null 95th value is 1.0 cannot pass.", "research/chop_regime_c1/t5_controls.py"), h=640)
    save(fig, "t5", "02_positive_cells.html")

    D = pd.read_parquet(C.art("t5a_whole_pipeline_diagnosis.parquet"))
    D = D[D["rung"] == "all"]
    NR = CFG["controls"]["negative_references"]
    stats = [("er_statistic_median", "ER statistic", NR["er_ratio_band"], "linear"), ("vz2_median", "vz2 median", (-NR["vz_abs_median_max"], NR["vz_abs_median_max"]), "linear"),
             ("vz4_median", "vz4 median", (-NR["vz_abs_median_max"], NR["vz_abs_median_max"]), "linear"), ("vz2_sd", "vz2 SD (log)", NR["vz_sd_band"], "log"),
             ("vz4_sd", "vz4 SD (log)", NR["vz_sd_band"], "log")]
    fig = make_subplots(rows=1, cols=5, subplot_titles=[x[1] for x in stats], horizontal_spacing=0.06)
    for i, (col, _, band, ax) in enumerate(stats, start=1):
        for bs in ("mid", "vwap"):
            g = D[D["basis"] == bs]
            fig.add_trace(go.Scatter(x=g["kind"], y=g[col].replace([np.inf], np.nan), mode="markers", marker=dict(color=COL[bs], size=11), name=bs, showlegend=i == 1,
                                     customdata=g["windows"], hovertemplate="%{x}<br>%{y:.4g}<br>n windows %{customdata}<extra></extra>"), row=1, col=i)
        fig.add_hrect(y0=band[0], y1=band[1], fillcolor="rgba(120,200,120,0.15)", line_width=0, row=1, col=i)
        fig.update_yaxes(type=ax, row=1, col=i)
    style(fig, "First T5 run (A1.0 cause 1): the whole-pipeline null under three constructions, against the first run's bands (shaded)",
          cap(Q53, "literal = permuted raw returns (a bridge carrying the window's net move); bridge0 = permuted demeaned returns; bootstrap = demeaned returns with replacement "
                   "(A1.3's construction). 20 draws per window. The variance-ratio columns were retired by A1.1.", "research/chop_regime_c1/t5a_whole_pipeline_diagnosis.py"), h=560)
    save(fig, "t5", "03_whole_pipeline_constructions.html")

    sw = s["sweep"]
    fig = make_subplots(rows=1, cols=2, subplot_titles=["er (median)", "cost_noise_h (median, primary, finest rung)"])
    for bs in ("mid", "vwap"):
        v = sw[f"er_{bs}"]
        fig.add_trace(go.Scatter(x=[16, 32, 64], y=[v["16"], v["32"], v["64"]], mode="lines+markers", line=dict(color=COL[bs]), name=f"er {bs}{' (bucket-dependent)' if v['bucket_dependent'] else ''}"),
                      row=1, col=1)
    for h in C.HORIZONS:
        v = sw[f"cost_noise_{h}"]
        fig.add_trace(go.Scatter(x=[16, 32, 64], y=[v["16"], v["32"], v["64"]], mode="lines+markers", name=f"cost_noise_{h}{' (bucket-dependent)' if v['bucket_dependent'] else ''}"),
                      row=1, col=2)
    fig.update_xaxes(title_text="buckets per window", type="log", tickvals=[16, 32, 64])
    style(fig, "Null-parameter sweep: medians at 16, 32 and 64 buckets (a move > 20% labels the measure bucket-dependent)",
          cap(Q53.replace("; synthetic nulls, not market outcomes", "; real windows"), f"n windows: midpoint {s['windows_by_basis']['mid']:,}, VWAP {s['windows_by_basis']['vwap']:,}.",
              "research/chop_regime_c1/t5_controls.py"), h=520)
    save(fig, "t5", "04_sweep.html")


def t6_charts():
    s = C.read_json("t6_summary.json")
    segs = [x for x in C.SEGS if x in s["per_segment"]]
    ps = s["per_segment"]
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, subplot_titles=["moment-minutes per segment of t", "share of the segment's moment-minutes"], vertical_spacing=0.14)
    allseg = list(ps)
    fig.add_trace(go.Bar(x=allseg, y=[ps[x]["moment_minutes"] for x in allseg], text=[f"{ps[x]['moment_minutes']:,} mm · {ps[x]['moments']:,} moments · {ps[x]['events']:,} events" for x in allseg],
                         marker_color="#9aa4ae", showlegend=False), row=1, col=1)
    for key, lab, colr in (("no_scale_free_rung_share", "no valid scale-free rung", "#ff6b6b"), ("no_rate_rung_share", "no valid rate rung", "#ffd479"),
                           ("no_quote_at_t_share", "no quote at t", "#c39bff"), ("vwap_fallback_share", "VWAP fallback (finest rung)", "#7bd88f")):
        fig.add_trace(go.Bar(x=segs, y=[ps[x][key] for x in segs], name=lab, marker_color=colr), row=2, col=1)
    fig.add_hline(y=0.40, line=dict(color="#ff6b6b", dash="dash"), row=2, col=1)
    fig.update_yaxes(type="log", title_text="moment-minutes", row=1, col=1)
    fig.update_yaxes(title_text="share", range=[0, 1], row=2, col=1)
    style(fig, "Coverage per segment of t (dashed: row 6's 40% line for 'no valid scale-free rung')",
          cap(DEV, "Auction-minute moments are carried and labelled; they are not entry moments and have no measures.", "research/chop_regime_c1/t6_build.py"), h=700)
    save(fig, "t6", "01_coverage.html")

    ra = pd.DataFrame(s["rung_availability"])
    fig = make_subplots(rows=1, cols=2, subplot_titles=["scale-free ladder (>= 64 collapsed trades)", "rate ladder (>= 17 per half-window, D22 floor)"], shared_yaxes=True)
    for c, lad in enumerate(("scale_free", "rate"), start=1):
        for seg in segs:
            g = ra[(ra["ladder"] == lad) & (ra["segment"] == seg)].sort_values("k")
            fig.add_trace(go.Scatter(x=g["k"], y=g["share"], mode="lines+markers", line=dict(color=SEGC[seg]), name=seg, showlegend=c == 1,
                                     text=[f"{v:,} mm" for v in g["valid_moment_minutes"]], hovertemplate="rung %{x}<br>share %{y:.3f}<br>%{text}<extra></extra>"), row=1, col=c)
    fig.update_xaxes(title_text="rung k")
    fig.update_yaxes(title_text="share of the segment's moment-minutes with a valid rung k", range=[0, 1.02], row=1, col=1)
    style(fig, "Rung availability per segment", cap(DEV, "Valid moment-minutes in hover.", "research/chop_regime_c1/t6_build.py"), h=520)
    save(fig, "t6", "02_rung_availability.html")

    years = sorted(C.dev_slice(C.load_population())["year"].unique())
    cols = ["trade_rate", "raw_rate", "dollar_flow", "spread_bp_t", "spread_c_t", "spread_tw_bp", "spread_tw_c", "quote_age_s", "depth_ask_usd", "depth_bid_usd",
            "turnover_t", "turnover_rate", "n_eff", "top3_share", "move_per_trade", "er", "er_vwap", "er_rel", "er_allmax", "leg_s", "leg_bp", "giveback",
            "since_high_min", "since_high_vol", "act_ratio"] + [f"cost_noise_{h}" for h in C.HORIZONS]
    m = pd.concat([pd.read_parquet(C.art(f"t6_moments_{y}.parquet"), columns=["segment", "weight"] + cols) for y in years], ignore_index=True)
    m = m[m["segment"].isin(C.SEGS)]
    n_all = len(m)
    sub = m.sample(n=min(300_000, n_all), random_state=20260930)
    fig = go.Figure()
    buttons = []
    traces_per = len(C.SEGS)
    for ci, c in enumerate(cols):
        for seg in C.SEGS:
            g = sub[sub["segment"] == seg]
            x = g[c].astype(float).to_numpy()
            w = g["weight"].to_numpy(float)
            fin = np.isfinite(x)
            pos = fin & (x > 0)
            o = np.argsort(x[pos])
            xs, cw = x[pos][o], np.cumsum(w[pos][o])
            tot = w[fin].sum()
            k = np.unique(np.r_[np.linspace(0, xs.size - 1, min(xs.size, 600)).astype(int)]) if xs.size else np.zeros(0, int)
            nz = int((fin & (x <= 0)).sum())
            fig.add_trace(go.Scatter(x=xs[k], y=(cw[k] + w[fin & (x <= 0)].sum()) / tot if tot else [], mode="lines", line=dict(color=SEGC[seg], shape="hv"), visible=ci == 0,
                                     name=f"{seg} (n {int(fin.sum()):,}; ≤ 0: {nz:,}; NaN {int(np.isnan(x).sum()):,}; inf {int(np.isinf(x).sum()):,})"))
        vis = [False] * (len(cols) * traces_per)
        vis[ci * traces_per:(ci + 1) * traces_per] = [True] * traces_per
        buttons.append(dict(label=c, method="update", args=[{"visible": vis}, {"xaxis.title.text": f"{c} (log)"}]))
    fig.update_layout(updatemenus=[dict(buttons=buttons, x=0, y=1.13, xanchor="left", bgcolor="#1d2229", font=dict(color=FG))])
    fig.update_xaxes(type="log", title_text=f"{cols[0]} (log)")
    fig.update_yaxes(title_text="share of moment-minutes ≤ x", range=[0, 1.02])
    style(fig, "Every causal measure per segment: weighted ECDF (select the measure)",
          cap(DEV.replace("every non-auction moment", f"a seeded subsample of {len(sub):,} of {n_all:,} non-auction moments"),
              "Log x; values ≤ 0 sit off the axis and are counted in the legend (the ECDF starts at their share); NaN = unavailable, inf = a flat window's cost_noise.",
              "research/chop_regime_c1/c1charts.py"), h=600)
    save(fig, "t6", "03_measure_distributions.html")

    A = pd.read_parquet(C.art("t6_basis_agreement.parquet"))
    A = A.groupby(["segment", "rung"]).apply(lambda g: pd.Series({"spearman": np.average(g["spearman"].fillna(0), weights=g["n"]) if g["n"].sum() else np.nan,
                                                                  "n": int(g["n"].sum())}), include_groups=False).reset_index()
    fig = go.Figure()
    for seg in C.SEGS:
        g = A[A["segment"] == seg].sort_values("rung")
        fig.add_trace(go.Scatter(x=g["rung"], y=g["spearman"], mode="lines+markers", line=dict(color=SEGC[seg]), name=seg, text=[f"n {v:,}" for v in g["n"]],
                                 hovertemplate="rung %{x}<br>Spearman %{y:.3f}<br>%{text}<extra></extra>"))
    fig.update_xaxes(title_text="rung k")
    fig.update_yaxes(title_text="Spearman, er midpoint vs VWAP", range=[-0.05, 1.05])
    style(fig, "Price-basis agreement on the development slice", cap(DEV.replace(", weighted by moment-minutes", "; windows with both prices"),
                                                                     "Per year Spearman averaged with window-count weights; n windows in hover.", "research/chop_regime_c1/t6_build.py"), h=500)
    save(fig, "t6", "04_basis_agreement.html")


def t6b_charts():
    b = pd.read_parquet(C.art("t6b_null_bands.parquet"))
    fig = make_subplots(rows=3, cols=4, subplot_titles=[f"{s} · {t}" for s in C.SEGS for t in TIERS], shared_xaxes=True, shared_yaxes=True,
                        vertical_spacing=0.07, horizontal_spacing=0.03)
    for r, seg in enumerate(C.SEGS, start=1):
        for c, t in enumerate(TIERS, start=1):
            g = b[(b["segment"] == seg) & (b["tier"] == t) & (b["basis"] == "mid")].sort_values("k")
            v = b[(b["segment"] == seg) & (b["tier"] == t) & (b["basis"] == "vwap")].sort_values("k")
            first = r == 1 and c == 1
            fig.add_trace(go.Scatter(x=g["k"], y=g["null_p95"], mode="lines", line=dict(width=0), showlegend=False, hoverinfo="skip"), row=r, col=c)
            fig.add_trace(go.Scatter(x=g["k"], y=g["null_p05"], mode="lines", line=dict(width=0), fill="tonexty", fillcolor=BAND, name="midpoint null 5–95%", showlegend=first), row=r, col=c)
            fig.add_trace(go.Scatter(x=g["k"], y=g["null_median"], mode="lines", line=dict(color="white", dash="dot"), name="midpoint null median", showlegend=first,
                                     text=[f"sampled {a:,} of {w:,} windows{' (FEW)' if f else ''}" for a, w, f in zip(g["windows_sampled"], g["windows_in_cell"], g["label_few_windows"])],
                                     hovertemplate="rung %{x}<br>%{y:.3f}<br>%{text}<extra></extra>"), row=r, col=c)
            fig.add_trace(go.Scatter(x=g["k"], y=g["real_q50"], mode="markers", marker=dict(color=COL["mid"], size=6), name="real er median (midpoint)", showlegend=first,
                                     error_y=dict(type="data", symmetric=False, array=g["real_q75"] - g["real_q50"], arrayminus=g["real_q50"] - g["real_q25"], width=0, color=COL["mid"]),
                                     text=[f"n {x:,}" for x in g["real_er_n"]], hovertemplate="rung %{x}<br>%{y:.3f}<br>%{text}<extra></extra>"), row=r, col=c)
            fig.add_trace(go.Scatter(x=v["k"], y=v["null_median"], mode="lines", line=dict(color=COL["vwap"], dash="dash", width=1), name="VWAP null median (fallback reference)",
                                     showlegend=first), row=r, col=c)
            few = g[g["label_few_windows"]]
            if len(few):
                fig.add_trace(go.Scatter(x=few["k"], y=few["null_median"], mode="markers", marker=dict(symbol="x", color="#ff6b6b", size=8), name="< 20 sampled windows",
                                         showlegend=first), row=r, col=c)
    fig.update_yaxes(range=[0, 1])
    fig.update_xaxes(title_text="rung k", row=3)
    style(fig, "A1.3 null bands on the development slice per cell (t's segment × price tier at τ × rung): null band and median beside the real er median and IQR",
          cap("Sample: up to 2,000 seeded windows per cell, 20 draws each, from the development-slice build", "The real er distribution covers every eligible window in the cell "
              "(a pre-t measure). Red x: fewer than 20 sampled windows.", "research/chop_regime_c1/t6b_null_bands.py"), h=980)
    save(fig, "t6b", "01_null_bands.html")


def main() -> int:
    d = C.REPO / C.CHARTS / "t5"
    if d.exists():
        shutil.rmtree(d)                                   # the first run's charts are in git at 1be4f65; never two generations in the tree
    t5_charts()
    t6_charts()
    t6b_charts()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
