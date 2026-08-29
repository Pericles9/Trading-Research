#!/usr/bin/env python
"""
Charts for steps 1 and 2. One chart per file (CLAUDE.md chart contract), Plotly,
offline `--plotlyjs directory`, never a CDN (D14). Palette imported from the Diag1
grammar so the repo keeps one palette.

  04_s_min_cohort      the resolution floor across all 100 events -- per event, and
                       as a distribution, against both band floors
  05_s_min_vs_subbursts  that floor against the three committed sub-burst duration
                       distributions, and the print count each is built from

Log x throughout: s_min is 2.26/lambda and lambda spans four orders of magnitude
across this cohort, so the axis is multiplicative. Outliers are shown, never clipped.
Every series carries its n.

Usage: .venv/Scripts/python.exe research/scale_field/plot_s_min.py
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

SEG_COLOR = {"premarket": "#eb6834", "rth": "#256abf", "no_detection": "#898781"}
SRC_COLOR = {"v4": "#8f300f", "10c_s1": "#c9491d", "10d_t4_reference": "#eb6834"}
WIN_COLOR = ["#0d366b", "#256abf", "#3987e5", "#86b6ef"]
BANDS = {"fine band floor 15.6 ms": 0.015625, "coarse band floor 1 s": 1.0}


def ecdf(a):
    a = np.sort(np.asarray(a, float)[np.isfinite(a)])
    return a, np.arange(1, a.size + 1) / a.size


def chart_s_min(df, summary, t):
    """Per-event range plus the pooled distribution. The range is the point: s_min is a
    FUNCTION of time, so an event is a span across the axis, not a dot."""
    d = df.sort_values("s_min_median").reset_index(drop=True)
    fig = make_subplots(rows=2, cols=1, vertical_spacing=0.10, row_heights=[0.62, 0.38],
                        subplot_titles=(
                            "per event — within-session s_min range (5th–95th percentile "
                            "of the session, dot = median moment)",
                            "pooled distribution (ECDF) — how far left the cohort can reach"))

    for seg, g in d.groupby("segment"):
        c = SEG_COLOR.get(seg, "#898781")
        for _, r in g.iterrows():
            fig.add_trace(go.Scattergl(
                x=[r["s_min_q05"], r["s_min_q95"]], y=[r.name, r.name], mode="lines",
                line=dict(color=c, width=1.4), opacity=0.55,
                showlegend=False, hoverinfo="skip"), row=1, col=1)
        fig.add_trace(go.Scattergl(
            x=g["s_min_median"], y=g.index, mode="markers",
            marker=dict(color=c, size=5),
            name=f"{seg} (n={len(g)})", legendgroup=seg,
            customdata=np.stack([g["event_id"], g["t0_print_count"],
                                 g["lambda_active"], g["s_min_q05"]], axis=-1),
            hovertemplate="%{customdata[0]}<br>%{customdata[1]:,} prints<br>"
                          "λ_active %{customdata[2]:.2f}/s<br>"
                          "s_min median %{x:.3g} s<br>best 5%% %{customdata[3]:.3g} s"
                          "<extra></extra>"), row=1, col=1)
    fig.update_yaxes(title_text="event (sorted by median s_min)", row=1, col=1,
                     showticklabels=False)

    for seg, g in d.groupby("segment"):
        for col, dash, lab in (("s_min_q05", "dot", "best 5% of session"),
                               ("s_min_median", "solid", "median moment")):
            x, y = ecdf(g[col])
            fig.add_trace(go.Scattergl(x=x, y=y, mode="lines",
                                       line=dict(color=SEG_COLOR.get(seg, "#898781"),
                                                 width=2 if dash == "solid" else 1.4,
                                                 dash=dash),
                                       name=f"{seg} · {lab}", legendgroup=seg,
                                       showlegend=False,
                                       hovertemplate=f"{seg} · {lab}<br>s_min %{{x:.3g}} s"
                                                     "<br>%{y:.0%} of events at or below"
                                                     "<extra></extra>"), row=2, col=1)
    fig.update_yaxes(title_text="share of events", tickformat=".0%", row=2, col=1)

    # Band floors, labelled INSIDE the lower panel at staggered heights -- at the top
    # of panel 1 they collide with each other and with the subplot title.
    for i, (lab, v) in enumerate(sorted(BANDS.items(), key=lambda kv: kv[1])):
        for r in (1, 2):
            fig.add_vline(x=v, row=r, col=1,
                          line=dict(color=t["ink"], width=1.3, dash="dash"))
        fig.add_annotation(row=2, col=1, x=np.log10(v), y=0.72 + 0.16 * i, yref="y domain",
                           text=lab, showarrow=False, xanchor="left", yanchor="middle",
                           xshift=4, font=dict(size=9, color=t["ink"]),
                           bgcolor=t["surface"], borderpad=2)

    ref = summary["s_min_reference"] if "s_min_reference" in summary else {}
    best = float(d["s_min_q05"].min())
    fig.update_xaxes(type="log", dtick=1, title_text="s_min = 2.26/λ  (seconds, log)",
                     row=2, col=1)
    fig.update_xaxes(type="log", dtick=1, row=1, col=1)
    fig.update_layout(
        title=dict(text=(
            "<b>The resolution floor across the analysis cohort</b> · "
            f"n = {len(d)} events, frozen manifest e1a0ac73a79aa573<br>"
            "<sup>s_min = 2.26/λ, from n_eff = 2√π·s·λ ≥ 8 rearranged — derived, not "
            "adopted. Below it nothing is measurable at any output resolution by this "
            f"method. <b>Best reachable anywhere in the cohort: {best*1e3:.0f} ms</b> "
            "(densest event, its most favourable 5%). λ by k-NN spacing, k=20. "
            "Description only — no gate is proposed here.</sup>"),
            font=dict(size=15, color=t["ink"]), x=0.01, xanchor="left"),
        height=900, paper_bgcolor=t["plane"], plot_bgcolor=t["surface"],
        font=dict(family='system-ui, -apple-system, "Segoe UI", sans-serif',
                  size=11, color=t["ink2"]),
        legend=dict(orientation="h", y=1.05, x=1, xanchor="right",
                    bgcolor="rgba(0,0,0,0)"),
        margin=dict(l=70, r=40, t=110, b=50))
    fig.update_xaxes(showgrid=True, gridcolor=t["grid"], linecolor=t["axis"])
    fig.update_yaxes(gridcolor=t["grid"], linecolor=t["axis"], zeroline=False)
    for a in fig.layout.annotations[:2]:
        a.font.update(size=11, color=t["ink2"]); a.update(x=0, xanchor="left")
    return fig


def chart_vs_subbursts(df, cmp_json, t):
    fig = make_subplots(rows=2, cols=1, vertical_spacing=0.12, row_heights=[0.55, 0.45],
                        subplot_titles=(
                            "duration — committed sub-bursts vs what this method can resolve",
                            "prints per committed sub-burst — the statement that needs no "
                            "cross-method inference"))

    x, y = ecdf(df["s_min_q05"])
    fig.add_trace(go.Scattergl(x=x, y=y, mode="lines",
                               line=dict(color=t["ink"], width=2.6),
                               name=f"s_min, best 5% of session (n={len(x)} events)",
                               hovertemplate="s_min %{x:.3g} s<br>%{y:.0%} of events"
                                             "<extra></extra>"), row=1, col=1)
    x, y = ecdf(df["s_min_median"])
    fig.add_trace(go.Scattergl(x=x, y=y, mode="lines",
                               line=dict(color=t["ink"], width=1.6, dash="dot"),
                               name=f"s_min, median moment (n={len(x)} events)",
                               hovertemplate="s_min %{x:.3g} s<br>%{y:.0%} of events"
                                             "<extra></extra>"), row=1, col=1)

    for lab, rec in cmp_json["sources"].items():
        if not rec.get("present"):
            continue
        d = rec["duration_seconds"]
        n = rec["prints_per_subburst"]
        qs = [d[f"q{k:02d}"] for k in (5, 25, 50, 75, 95)]
        cen = rec.get("floor_note") is not None
        fig.add_trace(go.Scattergl(x=qs, y=[.05, .25, .50, .75, .95], mode="lines+markers",
                                   line=dict(color=SRC_COLOR[lab], width=2,
                                             dash="dot" if cen else "solid"),
                                   marker=dict(size=7, color=SRC_COLOR[lab],
                                               symbol="x" if cen else "circle"),
                                   name=f"{lab} duration (n={d['n']:,})"
                                        + (" — CENSORED at 3 prints" if cen else ""),
                                   hovertemplate=f"{lab}<br>%{{x:.3g}} s at %{{y:.0%}}"
                                                 "<extra></extra>"), row=1, col=1)
        fig.add_trace(go.Bar(
            x=[f"{lab}"], y=[n["median"]],
            error_y=dict(type="data", symmetric=False,
                         array=[n["q75"] - n["median"]], arrayminus=[n["median"] - n["q25"]],
                         color=t["ink2"], width=6),
            marker=dict(color=SRC_COLOR[lab]), showlegend=False,
            customdata=[[n["share_le_3"], n["n"], n["min"], n.get("share_eq_2", 0)]],
            hovertemplate=f"{lab}<br>median %{{y:.0f}} prints<br>"
                          "%{customdata[3]:.1%} are EXACTLY 2 (one interval)<br>"
                          "%{customdata[0]:.1%} are ≤3<br>"
                          "n = %{customdata[1]:,} sub-bursts<br>observed minimum "
                          "%{customdata[2]:.0f}<extra></extra>"), row=2, col=1)
        eq2 = n.get("share_eq_2", 0.0)
        fig.add_annotation(row=2, col=1, x=lab, y=n["median"],
                           text=(f"median {n['median']:.0f} prints<br>"
                                 + (f"<sup><b>{eq2:.0%} are exactly 2 — one interval</b></sup>"
                                    if eq2 > 0 else
                                    f"<sup>floored at 3; {n['share_le_3']:.0%} sit on the floor</sup>")),
                           showarrow=False, yanchor="bottom", yshift=6,
                           font=dict(size=10, color=t["ink"]))

    fig.update_yaxes(title_text="quantile", tickformat=".0%", row=1, col=1)
    fig.update_xaxes(type="log", dtick=1, title_text="seconds (log)", row=1, col=1)
    fig.update_yaxes(title_text="prints per sub-burst<br>(median, IQR)", row=2, col=1)

    for lab, v in BANDS.items():
        fig.add_vline(x=v, row=1, col=1, line=dict(color=t["ink"], width=1.2, dash="dash"))
        fig.add_annotation(row=1, col=1, x=np.log10(v), y=0.06, yref="y domain", text=lab,
                           showarrow=False, xanchor="left", yanchor="bottom", xshift=4,
                           font=dict(size=9, color=t["muted"]),
                           bgcolor=t["surface"], borderpad=2)

    best = float(df["s_min_q05"].min())
    fig.update_layout(
        title=dict(text=(
            "<b>Resolution floor vs the committed sub-burst durations</b> · "
            "description only, no decision<br>"
            "<sup><b>Read the top panel with its caveat:</b> D9's operating variable is the "
            "interval itself and estimates no intensity, so n_eff does not bind that "
            "lineage on its own terms — a gap is a statement about two methods' domains, "
            "not a retraction of either, and <b>the clusters are real</b>: three prints "
            "inside 1.75 ms on a 0.30 prints/s tape is astronomically improbable under any "
            "stationary null. What is unsupported is their <i>duration</i> as a measured "
            "quantity. <b>The bottom panel needs no such inference</b> — it is the artifacts' "
            "own n_prints column. Every source is cut to ONE committed cell. "
            f"No event resolves below {best*1e3:.0f} ms at its best moment.</sup>"),
            font=dict(size=15, color=t["ink"]), x=0.01, xanchor="left"),
        height=880, paper_bgcolor=t["plane"], plot_bgcolor=t["surface"],
        font=dict(family='system-ui, -apple-system, "Segoe UI", sans-serif',
                  size=11, color=t["ink2"]),
        legend=dict(orientation="h", y=1.06, x=1, xanchor="right",
                    bgcolor="rgba(0,0,0,0)"),
        margin=dict(l=70, r=40, t=120, b=50), bargap=0.55)
    fig.update_xaxes(showgrid=True, gridcolor=t["grid"], linecolor=t["axis"])
    fig.update_yaxes(gridcolor=t["grid"], linecolor=t["axis"], zeroline=False)
    for a in fig.layout.annotations[:2]:
        a.font.update(size=11, color=t["ink2"]); a.update(x=0, xanchor="left")
    return fig


def chart_windows(cohort_json, t):
    """Admissibility by window. The D3 session is the wrong denominator and this chart
    exists to say so: what a strategy needs is whether the band is supported WHEN IT
    WOULD BE TRADING, which is at and after the D7 anchor (D5: intraday post-trigger)."""
    tw = cohort_json["tick_detail"]["by_window"]
    names = [k for k in tw if tw[k]["lambda_prints_per_s"].get("n")]
    fig = make_subplots(rows=2, cols=1, vertical_spacing=0.13, row_heights=[0.52, 0.48],
                        subplot_titles=(
                            "s_min within the window — the median moment of each event",
                            "events whose median moment supports the band (of those with "
                            "≥25 prints in the window)"))

    for i, w in enumerate(names):
        sm = tw[w]["s_min_median_seconds"]
        c = WIN_COLOR[i % len(WIN_COLOR)]
        qs = [sm[f"q{k:02d}"] for k in (5, 25, 50, 75, 95)]
        fig.add_trace(go.Scattergl(x=qs, y=[.05, .25, .50, .75, .95], mode="lines+markers",
                                   line=dict(color=c, width=2), marker=dict(size=7, color=c),
                                   name=f"{w} (n={sm['n']})",
                                   hovertemplate=f"{w}<br>s_min %{{x:.3g}} s at %{{y:.0%}}"
                                                 "<extra></extra>"), row=1, col=1)
    fig.update_yaxes(title_text="quantile across events", tickformat=".0%", row=1, col=1)
    fig.update_xaxes(type="log", dtick=1, title_text="s_min at the event's median moment "
                                                     "in the window (seconds, log)",
                     row=1, col=1)
    for lab, v in BANDS.items():
        fig.add_vline(x=v, row=1, col=1, line=dict(color=t["ink"], width=1.3, dash="dash"))
        fig.add_annotation(row=1, col=1, x=np.log10(v), y=0.04, yref="y domain", text=lab,
                           showarrow=False, xanchor="left", yanchor="bottom", xshift=4,
                           font=dict(size=9, color=t["muted"]),
                           bgcolor=t["surface"], borderpad=2)

    for band, colr in (("coarse", "#256abf"), ("fine", "#eb6834")):
        xs, ys, cd = [], [], []
        for w in names:
            n_tot = tw[w]["lambda_prints_per_s"]["n"]
            n_ok = tw[w]["n_events_median_moment_supports_band"][band]
            xs.append(w); ys.append(n_ok / n_tot if n_tot else 0)
            cd.append([n_ok, n_tot])
        fig.add_trace(go.Bar(x=xs, y=ys, name=f"{band} band", marker=dict(color=colr),
                             customdata=cd,
                             hovertemplate="%{x}<br>%{customdata[0]}/%{customdata[1]} events"
                                           "<br>%{y:.0%}<extra></extra>"), row=2, col=1)
        for x_, y_, c_ in zip(xs, ys, cd):
            fig.add_annotation(row=2, col=1, x=x_, y=y_, text=f"{c_[0]}/{c_[1]}",
                               showarrow=False, yanchor="bottom", yshift=4,
                               font=dict(size=9, color=t["ink2"]))
    fig.update_yaxes(title_text="share of events", tickformat=".0%", row=2, col=1)

    fig.update_layout(
        title=dict(text=(
            "<b>Admissibility by window — the session is the wrong denominator</b><br>"
            "<sup>The D3 extended session is mostly dead time; what matters is whether the "
            "band is supported <b>when a strategy would be acting</b>, which under D5 is at "
            "and after the D7 anchor. n falls with the window because fewer events carry "
            "≥25 prints in it — that drop is itself reported, not hidden. "
            "<b>The fine band is 0/n at every window.</b> Description only, no gate.</sup>"),
            font=dict(size=15, color=t["ink"]), x=0.01, xanchor="left"),
        height=860, paper_bgcolor=t["plane"], plot_bgcolor=t["surface"],
        font=dict(family='system-ui, -apple-system, "Segoe UI", sans-serif',
                  size=11, color=t["ink2"]),
        legend=dict(orientation="h", y=1.06, x=1, xanchor="right",
                    bgcolor="rgba(0,0,0,0)"),
        margin=dict(l=70, r=40, t=118, b=60), barmode="group", bargap=0.30)
    fig.update_xaxes(showgrid=True, gridcolor=t["grid"], linecolor=t["axis"])
    fig.update_yaxes(gridcolor=t["grid"], linecolor=t["axis"], zeroline=False)
    for a in fig.layout.annotations[:2]:
        a.font.update(size=11, color=t["ink2"]); a.update(x=0, xanchor="left")
    return fig


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--out", default="results/scale_field/charts/cohort")
    p.add_argument("--theme", choices=["light", "dark"], default="light")
    p.add_argument("--plotlyjs", default="directory", choices=["directory", "inline"])
    args = p.parse_args()
    t = THEMES[args.theme]
    jsmode = True if args.plotlyjs == "inline" else "directory"

    df = pd.read_parquet(rel("results/scale_field/artifacts/s_min_cohort.parquet"))
    with open(rel("results/scale_field/artifacts/s_min_cohort.json"), encoding="utf-8") as f:
        summary = json.load(f)
    with open(rel("results/scale_field/artifacts/s_min_vs_subbursts.json"), encoding="utf-8") as f:
        cmp_json = json.load(f)

    out = Path(rel(args.out)); out.mkdir(parents=True, exist_ok=True)
    written = []
    charts = [("04_s_min_cohort", chart_s_min(df, cmp_json, t)),
              ("05_s_min_vs_subbursts", chart_vs_subbursts(df, cmp_json, t))]
    if "tick_detail" in summary and "by_window" in summary.get("tick_detail", {}):
        charts.append(("06_admissibility_by_window", chart_windows(summary, t)))
    for name, fig in charts:
        path = out / f"{name}_{args.theme}.html"
        fig.write_html(path, include_plotlyjs=jsmode, full_html=True)
        written.append(str(path)); print(f"wrote {path}")

    with open(out / "chart_manifest.json", "w", encoding="utf-8") as f:
        json.dump({"charts": written, "theme": args.theme,
                   "config_hash": adapter.config_hash(),
                   "n_events": int(len(df)),
                   "offline_rule": "D14 — never a CDN",
                   "source": "research/scale_field/plot_s_min.py:main",
                   "reproduce": ".venv/Scripts/python.exe research/scale_field/plot_s_min.py "
                                f"--theme {args.theme}"}, f, indent=2)


if __name__ == "__main__":
    main()
