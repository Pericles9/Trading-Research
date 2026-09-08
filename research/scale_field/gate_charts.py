#!/usr/bin/env python
"""Charts for the instrument gates. Diagnostics, not deliverables (brief s2 rule 2).

The palette and themes are IMPORTED from research/phase_10d_diag1/
plot_boundary_through_time.py -- one palette in the repo, not two that drift. These
are curve charts, not scale-field heatmaps, so add_channel does not apply; where a
field pane is drawn the reference renderer is the one called.

Chart contract (Agent_Prompt_Standard s9): Plotly, standalone HTML, one per file, n
per bucket, no smoothing, log axes where the data is multiplicative, distributions
rather than centres, outliers shown and never clipped. Offline plotly.js (D14).
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np
import plotly.graph_objects as go

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(REPO_ROOT, "research", "phase_10d_diag1"))

from plot_boundary_through_time import THEMES            # noqa: E402

ART = os.path.join(REPO_ROOT, "results", "scale_field", "artifacts",
                   "instrument_gates")
OUT = os.path.join(REPO_ROOT, "results", "scale_field", "charts", "instrument_gates")
SERIES = ["#3b6ea5", "#eb6834", "#4a8c5f", "#8c5fa8", "#b58a2b", "#a8455f",
          "#3f8f8f", "#7a6a55", "#5f7fb5", "#c46a3a"]


def load(name):
    with open(os.path.join(ART, name), encoding="utf-8") as f:
        return json.load(f)


def shell(fig, t, title, subtitle, xt, yt, logx=False, logy=False, h=560):
    fig.update_layout(
        template="plotly_white", height=h,
        paper_bgcolor=t["surface"], plot_bgcolor=t["plane"],
        font=dict(color=t["ink2"], size=12),
        title=dict(text=f"<b>{title}</b><br><span style='font-size:11px;color:"
                        f"{t['muted']}'>{subtitle}</span>",
                   font=dict(color=t["ink"], size=15), x=0.01, xanchor="left"),
        margin=dict(l=70, r=30, t=95, b=70),
        legend=dict(font=dict(size=10), bgcolor="rgba(0,0,0,0)"),
        hovermode="closest")
    fig.update_xaxes(title_text=xt, gridcolor=t["grid"], linecolor=t["axis"],
                     zerolinecolor=t["grid"], type="log" if logx else "linear")
    fig.update_yaxes(title_text=yt, gridcolor=t["grid"], linecolor=t["axis"],
                     zerolinecolor=t["grid"], type="log" if logy else "linear")
    return fig


def save(fig, name):
    os.makedirs(OUT, exist_ok=True)
    p = os.path.join(OUT, name)
    fig.write_html(p, include_plotlyjs="directory", full_html=True)
    print("wrote", p)


# --------------------------------------------------------------------------- #

def chart_noise_ruler(t):
    """GATE C. sd(F) and the measured false-alarm rate against n_eff.

    The two facts the whole brief turns on are both here: sd is bounded away from
    zero at the read scale while F itself is bounded below at -1, and the negative
    tail is far thinner than normal theory at every n_eff on the grid.
    """
    r = load("gateC_null_rate.json")["rows"]
    fig = go.Figure()
    for i, (kern, cond) in enumerate([("centred", "unconditional"),
                                      ("centred", "masked"),
                                      ("onesided", "unconditional")]):
        q = sorted([x for x in r if x["kernel"] == kern and x["conditioning"] == cond],
                   key=lambda x: x["n_eff"])
        fig.add_trace(go.Scatter(
            x=[x["n_eff"] for x in q], y=[2 * x["sd"] for x in q], mode="lines+markers",
            name=f"2·sd  {kern}, {cond}", line=dict(color=SERIES[i], width=2),
            marker=dict(size=5),
            hovertemplate="n_eff %{x}<br>2·sd %{y:.3f}<extra></extra>"))
    ne = np.array([x["n_eff"] for x in r if x["kernel"] == "centred"
                   and x["conditioning"] == "unconditional"])
    ne.sort()
    fig.add_trace(go.Scatter(x=ne, y=2 * 0.87 / np.sqrt(ne), mode="lines",
                             name="2 × 0.87/√n_eff (asymptotic)",
                             line=dict(color=t["muted"], width=1, dash="dot")))
    fig.add_hline(y=1.0, line=dict(color=t["winner"], width=2),
                  annotation_text="F is bounded below at −1: above this line a 2-sd "
                                  "negative detection is IMPOSSIBLE",
                  annotation_font=dict(size=10, color=t["winner"]))
    for f, lab in ((8, "read_factor 1"), (16, "2"), (24, "3"), (32, "4")):
        fig.add_vline(x=f, line=dict(color=t["axis"], width=1, dash="dash"),
                      annotation_text=lab, annotation_font=dict(size=9,
                                                               color=t["muted"]))
    shell(fig, t, "Gate C — the detection threshold against the bound it has to fit inside",
          "2·sd(F) under a homogeneous Poisson null, 400,000 Monte Carlo draws per "
          "rung. n_eff = 2√π·s·λ̂ centred, √π·s·λ̂ one-sided. Vertical rules are the "
          "n_eff the read path delivers at each read_factor (n_eff = 8·read_factor "
          "exactly, since s* = read_factor·s_min).",
          "n_eff (effective prints in the kernel)", "2 · sd(F)", logx=True)
    save(fig, "gateC_noise_ruler.html")

    fig = go.Figure()
    for i, cond in enumerate(["unconditional", "masked"]):
        q = sorted([x for x in r if x["kernel"] == "centred"
                    and x["conditioning"] == cond], key=lambda x: x["n_eff"])
        fig.add_trace(go.Scatter(
            x=[x["n_eff"] for x in q],
            y=[max(x["p_lt_2sd"], 1e-6) for x in q], mode="lines+markers",
            name=f"measured P(F < −2·sd), {cond}",
            line=dict(color=SERIES[i], width=2), marker=dict(size=6),
            customdata=[x["n"] for x in q],
            hovertemplate="n_eff %{x}<br>P %{y:.5f}<br>n draws "
                          "%{customdata:,}<extra></extra>"))
    fig.add_hline(y=0.02275, line=dict(color=t["winner"], width=2, dash="dash"),
                  annotation_text="normal-theory one-tail 2σ = 0.0228 — never reached",
                  annotation_font=dict(size=10, color=t["winner"]))
    shell(fig, t, "Gate C — the false-alarm rate of the magnitude-thresholded mark",
          "Measured, not assumed. F is bounded below at −1 and right-skewed (skew "
          "2.01 at n_eff = 8), so the negative tail is far thinner than a Gaussian "
          "would suggest. Points at 1e-6 are zero hits in 400,000 draws.",
          "n_eff", "P(F < −2·sd) under the null", logx=True, logy=True)
    save(fig, "gateC_null_rate.html")


def chart_gateB(t):
    """GATE B. Survival of the marked time under the magnitude threshold."""
    b = load("gateB_noise_ruler.json")
    ev = list(b["events"])
    for kern in ("centred", "onesided"):
        fig = go.Figure()
        for i, e in enumerate(ev):
            rf = b["events"][e]["kernels"][kern]["read_factor"]
            xs = sorted(float(k) for k in rf)
            fig.add_trace(go.Scatter(
                x=xs,
                y=[rf[f"{x:.1f}"]["all"]["survival_share_of_marked"] for x in xs],
                mode="lines+markers", name=e.split("_")[0],
                line=dict(color=SERIES[i % len(SERIES)], width=2),
                marker=dict(size=7),
                customdata=[[rf[f"{x:.1f}"]["all"]["marked_seconds"],
                             rf[f"{x:.1f}"]["all"]["survivor_seconds"]] for x in xs],
                hovertemplate="read_factor %{x}<br>survival %{y:.4f}<br>"
                              "marked %{customdata[0]:,.0f} s → survivors "
                              "%{customdata[1]:,.0f} s<extra></extra>"))
        shell(fig, t,
              f"Gate B — fraction of marked time surviving F &lt; −2·sd ({kern} pane)",
              "Whole extended session, all ten panel events, n stated per point in "
              "hover (marked seconds → surviving seconds). The threshold is the Gate "
              "C table at n_eff = 2√π·s*·λ̂(t), read per cell, not a global constant. "
              "Reported at every read_factor: no single value is selected.",
              "read_factor  (s* = read_factor · s_min)",
              "surviving share of marked time")
        save(fig, f"gateB_survival_vs_read_factor_{kern}.html")

    fig = go.Figure()
    for i, e in enumerate(ev):
        by = b["events"][e]["kernels"]["centred"]["by_scale"]
        fig.add_trace(go.Scatter(
            x=[q["s"] for q in by], y=[q["survive_share"] for q in by],
            mode="lines", name=e.split("_")[0],
            line=dict(color=SERIES[i % len(SERIES)], width=1.6),
            customdata=[[q["n_eff_median"], q["neg_share"]] for q in by],
            hovertemplate="s %{x:.3g}s<br>survive %{y:.4f}<br>n_eff median "
                          "%{customdata[0]:.1f}<br>negative share "
                          "%{customdata[1]:.3f}<extra></extra>"))
    by0 = b["events"][ev[0]]["kernels"]["centred"]["by_scale"]
    fig.add_trace(go.Scatter(x=[q["s"] for q in by0], y=[q["null_rate"] for q in by0],
                             mode="lines", name="Poisson null rate at that n_eff",
                             line=dict(color=t["winner"], width=2, dash="dash")))
    shell(fig, t, "Gate B — survival against absolute scale, whole pane",
          "Time-weighted share of DEFINED cells at each ladder scale with F &lt; "
          "−2·sd(n_eff(t,s)), centred kernel. The dashed line is the false-alarm rate "
          "the same threshold carries at that row's median n_eff — a curve sitting on "
          "it is indistinguishable from noise at that scale.",
          "kernel scale s (seconds)", "share of defined cells surviving",
          logx=True, logy=True)
    save(fig, "gateB_survival_vs_scale.html")


def chart_gateE(t):
    """GATE E. Split-half reliability against scale -- no null, no threshold."""
    e = load("gateE_split_half.json")
    fig = go.Figure()
    for i, (eid, rows) in enumerate(e["events"].items()):
        if not rows:
            continue
        fig.add_trace(go.Scatter(
            x=[q["s"] for q in rows], y=[q["r_halfhalf"] for q in rows],
            mode="lines+markers", name=eid.split("_")[0],
            line=dict(color=SERIES[i % len(SERIES)], width=1.8),
            marker=dict(size=4),
            customdata=[[q["n_cells_median"], q["n_draws"]] for q in rows],
            hovertemplate="s %{x:.3g}s<br>r %{y:.3f}<br>cells %{customdata[0]:,.0f}"
                          "<br>draws %{customdata[1]}<extra></extra>"))
    fig.add_hline(y=0.0, line=dict(color=t["axis"], width=1))
    shell(fig, t, "Gate E — split-half reliability of the field against scale",
          "Each print assigned at random to half A or half B, the field computed "
          "independently on each, correlated at every scale on a FIXED absolute grid. "
          "F is invariant to λ → cλ, so thinning changes only the noise level — that "
          "invariance is verified numerically in gateE_split_half.json before the "
          "curve is read. Half-length reliability understates the full-data value.",
          "kernel scale s (seconds)", "corr(half A, half B)", logx=True)
    save(fig, "gateE_reliability.html")


def chart_gateF(t):
    """GATE F. Is the texture the same at every height?"""
    f = load("gateF_special_row.json")
    for metric, lab, ttl in (("median_width_over_s", "median negative-run width / s",
                              "blob width relative to the kernel that drew it"),
                             ("depth_median", "median F where F &lt; 0",
                              "depth of the negative field")):
        fig = go.Figure()
        for seg, dash in (("rth", "solid"), ("premarket", "dot")):
            for i, (eid, d) in enumerate(f["events"].items()):
                rows = d.get(seg) or []
                if not rows:
                    continue
                fig.add_trace(go.Scatter(
                    x=[q["s"] for q in rows], y=[q[metric] for q in rows],
                    mode="lines", name=f"{eid.split('_')[0]} {seg}",
                    line=dict(color=SERIES[i % len(SERIES)], width=1.4, dash=dash),
                    legendgroup=seg,
                    customdata=[q["n_runs"] for q in rows],
                    hovertemplate="s %{x:.3g}s<br>" + lab
                                  + " %{y:.3f}<br>n runs %{customdata:,}<extra></extra>"))
        for s_k, name in ((128.0, "Allan knee, regular hours"),
                          (16.0, "Allan knee, premarket")):
            fig.add_vline(x=s_k, line=dict(color=t["winner"], width=1.5, dash="dash"),
                          annotation_text=name,
                          annotation_font=dict(size=9, color=t["winner"]))
        shell(fig, t, f"Gate F — {ttl}, per scale row",
              "Premarket and regular hours are never pooled (v3 measured 0.903 "
              "decades of separation). v3's committed Allan knees are the "
              "prediction: the scale axis should change character near them.",
              "kernel scale s (seconds)", lab, logx=True)
        save(fig, f"gateF_{metric}.html")


def chart_gateD(t):
    """GATE D. Shaded fraction on print count, with the geometric control beside it."""
    per = load("gateD_per_event.json")["per_event"]
    reg = load("gateD_regression.json")["regressions"]
    for rf in ("1.0", "2.0", "4.0"):
        fig = go.Figure()
        x = np.array([r["n_prints"] for r in per], float)
        for i, (dv, lab) in enumerate([("shaded_fraction", "shaded fraction (sign only)"),
                                       ("survivor_fraction",
                                        "survivor fraction (F &lt; −2·sd)")]):
            y = np.array([r["kernels"]["centred"][rf]["all"][dv] for r in per], float)
            k = f"centred|rf{float(rf):g}|all"
            st = reg[k][f"{dv}_on_log_prints"]
            fig.add_trace(go.Scatter(
                x=x, y=y, mode="markers", name=f"{lab}  (slope {st['slope']:+.4f}, "
                                               f"r={st['r']:+.3f}, r²={st['r2']:.3f}, "
                                               f"n={st['n']})",
                marker=dict(size=8, color=SERIES[i], opacity=0.8),
                text=[r["event_id"] for r in per],
                hovertemplate="%{text}<br>prints %{x:,}<br>" + lab
                              + " %{y:.4f}<extra></extra>"))
            xs = np.linspace(np.log(x.min()), np.log(x.max()), 50)
            fig.add_trace(go.Scatter(x=np.exp(xs), y=st["intercept"] + st["slope"] * xs,
                                     mode="lines", showlegend=False,
                                     line=dict(color=SERIES[i], width=1.5, dash="dash")))
        shell(fig, t, f"Gate D — shaded fraction against print count, read_factor {rf}",
              "The DEPENDENT VARIABLE IS CORRECTED. A raw burst count carries a "
              "slope-1 dependence on print count from the geometry alone — the reads "
              "along the path number ≈ T/s_min ∝ λ̂·T — so the raw-count regression is "
              "reported only as the geometric control in gateD_regression.json. Arm A "
              "died at r = 0.96 on the uncorrected version.",
              "tick print count over the extended session",
              "share of admissible session time", logx=True)
        save(fig, f"gateD_shaded_vs_prints_rf{rf}.html")


def chart_excess(t):
    """Observed sd(F) against sampling-noise sd, per scale row. No threshold in it."""
    x = load("excess_variance.json")
    for kern in ("centred", "onesided"):
        fig = go.Figure()
        for seg, dash in (("rth", "solid"), ("premarket", "dot")):
            for i, (eid, d) in enumerate(x["events"].items()):
                rows = d.get(kern, {}).get(seg) or []
                if not rows:
                    continue
                fig.add_trace(go.Scatter(
                    x=[q["s"] for q in rows], y=[q["ratio"] for q in rows],
                    mode="lines", name=f"{eid.split('_')[0]} {seg}",
                    legendgroup=seg,
                    line=dict(color=SERIES[i % len(SERIES)], width=1.5, dash=dash),
                    customdata=[[q["sd_observed"], q["sd_null"], q["n_cells"]]
                                for q in rows],
                    hovertemplate="s %{x:.3g}s<br>ratio %{y:.2f}<br>sd obs "
                                  "%{customdata[0]:.3f} / sd null "
                                  "%{customdata[1]:.3f}<br>n cells "
                                  "%{customdata[2]:,}<extra></extra>"))
        fig.add_hline(y=1.0, line=dict(color=t["winner"], width=2),
                      annotation_text="1.0 — the field is pure estimator sampling "
                                      "noise at this scale",
                      annotation_font=dict(size=10, color=t["winner"]))
        shell(fig, t, f"Observed sd(F) ÷ sampling-noise sd, per scale row ({kern})",
              "The one curve in this read with no threshold, no burst definition and "
              "no clustering reference in it. The null sd is evaluated per cell at "
              "that cell's own n_eff and combined as √(mean sd²) — λ varies by a "
              "factor of ten inside a single scale row, so a row-median n_eff would "
              "understate the floor wherever the tape is thin.",
              "kernel scale s (seconds)", "sd observed / sd sampling-noise",
              logx=True, logy=True)
        save(fig, f"excess_variance_{kern}.html")


def chart_surrogate(t):
    """What the excess is made of: clustering below the bandwidth, rate path above."""
    x = load("surrogate_control.json")
    fig = go.Figure()
    for i, (eid, d) in enumerate(x["events"].items()):
        for tag, dash in (("real", "solid"), ("surrogate", "dash")):
            rows = d[tag]
            fig.add_trace(go.Scatter(
                x=[q["s"] for q in rows], y=[q["ratio"] for q in rows], mode="lines",
                name=f"{eid.split('_')[0]} — {tag}",
                line=dict(color=SERIES[i % len(SERIES)], width=2 if tag == "real" else 1.4,
                          dash=dash),
                customdata=[q["n_cells"] for q in rows],
                hovertemplate="s %{x:.3g}s<br>ratio %{y:.2f}<br>n cells "
                              "%{customdata:,}<extra></extra>"))
    fig.add_hline(y=1.0, line=dict(color=t["muted"], width=1.5),
                  annotation_text="pure sampling noise",
                  annotation_font=dict(size=10, color=t["muted"]))
    fig.add_vline(x=x["bandwidth_s"], line=dict(color=t["winner"], width=2, dash="dash"),
                  annotation_text=f"surrogate bandwidth {x['bandwidth_s']:g} s — below "
                                  f"this the surrogate has no structure at all",
                  annotation_font=dict(size=10, color=t["winner"]))
    shell(fig, t, "What the excess variance is made of",
          "Dashed: an inhomogeneous Poisson surrogate with the real tape's rate path "
          "smoothed at 30 s and NO clustering at any scale. Regular hours only. Below "
          "the bandwidth the surrogate sits at 1.0 and the real tape does not — that "
          "gap is structure a smooth rate path does not produce. Above ~64 s the two "
          "coincide, so the coarse excess IS the rate path. The rate channel cannot "
          "separate clumping from a rate excursion at constant mean rate (brief §11); "
          "this bounds where the question even arises.",
          "kernel scale s (seconds)", "sd observed / sd sampling-noise",
          logx=True, logy=True)
    save(fig, "surrogate_control.html")


def main() -> int:
    theme = THEMES["light"]
    which = sys.argv[1:] or ["C", "B", "E", "F", "D", "X", "S"]
    fns = {"C": chart_noise_ruler, "B": chart_gateB, "E": chart_gateE,
           "F": chart_gateF, "D": chart_gateD, "X": chart_excess,
           "S": chart_surrogate}
    for w in which:
        try:
            fns[w](theme)
        except FileNotFoundError as ex:
            print("skip", w, "--", ex)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
