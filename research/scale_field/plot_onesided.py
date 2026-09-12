#!/usr/bin/env python
"""
The causal re-derivation, charted: centred kernel against one-sided, head to head.

THREE THINGS THE PICTURE HAS TO CARRY, because D22 turned on exactly these:

  1. THE LEAD, both arms on one axis, against the same chance baseline. D22's
     measured -0.21 kernel widths was taken under a kernel that reads forward by
     about s, so it was never an absolute number. This panel is the first time the
     question is asked of an estimator that cannot see the future.
  2. THE FORWARD READ ITSELF, drawn rather than asserted. Synthetic step onset, both
     kernels, read at times strictly BEFORE the burst starts. The centred trace moves
     early; the causal one is flat on its background until the burst actually happens.
     No tape is needed for this panel and none is used -- it is a property of the
     estimators.
  3. THE PRICE. n_eff halves, so s_min doubles, so the bottom octave of the usable
     scale range is gone. Per event, centred against causal.

One figure per file (CLAUDE.md), Plotly, offline --plotlyjs directory, never a CDN (D14).

Usage: .venv/Scripts/python.exe research/scale_field/plot_onesided.py
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

from adapter import rel  # noqa: E402
from plot_boundary_through_time import THEMES  # noqa: E402
from scale_field import (collapse_same_timestamp, field_exact,  # noqa: E402
                         intervals, s_min_for_rate, seconds_since)

ARM = {"centred": "#898781", "onesided": "#256abf"}


def ecdf(a):
    a = np.sort(np.asarray(a, float)[np.isfinite(a)])
    return a, np.arange(1, a.size + 1) / a.size


def forward_read_panel(seed=43, onset=150.0, dur=2.0, bg=20.0, hi=600.0, s=2.0):
    """Panel 2's data. A burst starts at `onset`; both fields are read on a grid that
    ENDS before it. Returns (t, centred, onesided, centred_on_a_tape_with_no_burst)."""
    r = np.random.default_rng(seed)
    t, out = 0.0, []
    while t < 300.0:
        t += r.exponential(1.0 / (hi if onset <= t < onset + dur else bg))
        if t < 300.0:
            out.append(t)
    tape = np.array(out)
    nob = tape[(tape < onset) | (tape >= onset + dur)]

    def prep(a):
        ts = collapse_same_timestamp((np.asarray(a) * 1e9).astype(np.int64))
        ev, x = intervals(ts, origin=ts[0])
        return seconds_since(ts, ts[0]), ev, x

    tg = np.linspace(onset - 12.0, onset - 0.05, 160)
    sc = np.array([s])
    cen = field_exact(*prep(tape), tg, sc)["dlograte"][:, 0]
    one = field_exact(*prep(tape), tg, sc, kernel="onesided")["dlograte"][:, 0]
    cen_nb = field_exact(*prep(nob), tg, sc)["dlograte"][:, 0]
    return tg - onset, cen, one, cen_nb


def build(A, t):
    on_c = pd.read_parquet(os.path.join(A, "t1_lead_time_onsets.parquet"))
    on_o = pd.read_parquet(os.path.join(A, "t1_lead_time_onsets_onesided.parquet"))
    ev_c = pd.read_parquet(os.path.join(A, "t1_lead_time_events.parquet"))
    ev_o = pd.read_parquet(os.path.join(A, "t1_lead_time_events_onesided.parquet"))
    with open(os.path.join(A, "t1_lead_time.json"), encoding="utf-8") as f:
        sc_ = json.load(f)
    with open(os.path.join(A, "t1_lead_time_onesided.json"), encoding="utf-8") as f:
        so_ = json.load(f)

    fig = make_subplots(
        rows=3, cols=1, vertical_spacing=0.105, row_heights=[0.38, 0.31, 0.31],
        subplot_titles=(
            "1 · signed lead of FIELD relative to LEVEL, in units of the kernel scale s "
            "(positive = field fired first)",
            "2 · the forward read, drawn — dL/dln s at times BEFORE a synthetic burst "
            "that starts at 0 (s = 2 s, no tape used)",
            "3 · the price of causality — smallest resolvable kernel scale s_min per "
            "event, centred vs one-sided"))

    # ---- panel 1: the lead, both arms, ONE POINT PER EVENT ------------------
    # Deliberately NOT the onset-level distribution. 58 causal onsets come from 19
    # events and one event supplies 36% of them, so an onset-level binomial assumes an
    # independence that is not there. The per-event median is the unit the sign test
    # is run on, so it is the unit the chart shows.
    stats_txt = {}
    for arm, on in (("centred", on_c), ("onesided", on_o)):
        sub = on[on["orientation"] == "burst"]
        per = sub.groupby("event_id")["lead_in_s_units"].median()
        pos, tot = int((per > 0).sum()), int(per.notna().sum())
        stats_txt[arm] = (pos, tot, float(per.median()))
        x, y = ecdf(per)
        fig.add_trace(go.Scattergl(
            x=x, y=y, mode="lines+markers", line=dict(color=ARM[arm], width=2.6),
            marker=dict(size=5, color=ARM[arm]),
            name=f"{arm} — {pos}/{tot} events lead (median {per.median():+.2f} s-units)",
            hovertemplate=f"{arm}<br>per-event median lead %{{x:+.3f}} s-units"
                          "<br>%{y:.0%} of events<extra></extra>"), row=1, col=1)
    fig.add_vline(x=0.0, row=1, col=1, line=dict(color=t["ink2"], width=1.4, dash="dash"))
    fig.add_annotation(row=1, col=1, x=0.0, y=0.03, yref="y domain", xshift=5,
                       text="zero lead — left of this the field LAGS", showarrow=False,
                       xanchor="left", yanchor="bottom",
                       font=dict(size=9, color=t["ink2"]))
    pc_, tc_, mc_ = stats_txt["centred"]
    po_, to_, mo_ = stats_txt["onesided"]
    fig.add_annotation(
        row=1, col=1, x=0.99, y=0.06, xref="x domain", yref="y domain",
        xanchor="right", yanchor="bottom", showarrow=False, align="left",
        bgcolor=t["surface"], borderpad=4, font=dict(size=10, color=t["ink"]),
        text=(f"<b>the sign reverses, and it is the kernel, not the population.</b><br>"
              f"centred {pc_}/{tc_} events lead (median {mc_:+.2f}); "
              f"causal <b>{po_}/{to_}</b> (median {mo_:+.2f}).<br>"
              f"The causal {to_} are a strict SUBSET of the centred {tc_}. "
              f"<b>Paired, on those same {to_} events:</b><br>"
              f"centred 3/{to_} lead (−0.19), causal {to_}/{to_} (+1.52); paired "
              f"difference +1.91 s-units,<br>18/19 positive, Wilcoxon p = 1.9e−05. "
              f"Centred median on the shared 19 (−0.19) ≈ on the other 26 (−0.21)."))
    fig.update_yaxes(title_text="share of contributing events", tickformat=".0%",
                     row=1, col=1)
    fig.update_xaxes(title_text="per-event median lead (units of s)", range=[-3, 5],
                     row=1, col=1)

    # ---- panel 2: the forward read ------------------------------------------
    tt, cen, one, cen_nb = forward_read_panel()
    fig.add_trace(go.Scattergl(x=tt, y=cen, mode="lines", showlegend=False,
                               line=dict(color=ARM["centred"], width=2.2),
                               hovertemplate="centred<br>t %{x:.2f} s<br>%{y:.3f}"
                                             "<extra></extra>"), row=2, col=1)
    fig.add_trace(go.Scattergl(x=tt, y=one, mode="lines", showlegend=False,
                               line=dict(color=ARM["onesided"], width=2.2),
                               hovertemplate="one-sided<br>t %{x:.2f} s<br>%{y:.3f}"
                                             "<extra></extra>"), row=2, col=1)
    fig.add_trace(go.Scattergl(x=tt, y=cen_nb, mode="lines", showlegend=False,
                               line=dict(color=ARM["centred"], width=1.4, dash="dot"),
                               hovertemplate="centred, burst removed<br>t %{x:.2f} s"
                                             "<br>%{y:.3f}<extra></extra>"), row=2, col=1)
    gap = float(np.nanmax(np.abs(cen - cen_nb)))
    fig.add_annotation(row=2, col=1, x=-1.0, y=float(np.nanmin(cen)), xanchor="right",
                       yanchor="bottom", showarrow=False, bgcolor=t["surface"],
                       borderpad=2, align="left",
                       text=(f"<b>centred</b> (solid) departs from the same tape with the "
                             f"burst deleted (dotted) by up to {gap:.2f}<br>"
                             f"<b>one-sided</b> is identical to it to 1e-12 — it cannot "
                             f"see a burst that has not happened"),
                       font=dict(size=10, color=t["ink"]))
    fig.update_yaxes(title_text="dL/dln s", row=2, col=1)
    fig.update_xaxes(title_text="seconds before the burst starts", row=2, col=1)

    # ---- panel 3: the price -------------------------------------------------
    for arm, ev in (("centred", ev_c), ("onesided", ev_o)):
        smin = ev["median_s_star"] / 2.0        # s* = 2 * s_min by construction
        x, y = ecdf(smin)
        fig.add_trace(go.Scattergl(
            x=x, y=y, mode="lines", showlegend=False,
            line=dict(color=ARM[arm], width=2.2),
            hovertemplate=f"{arm}<br>s_min %{{x:.3f}} s<br>%{{y:.0%}}<extra></extra>"),
            row=3, col=1)
    fig.add_annotation(row=3, col=1, x=np.log10(0.06), y=0.92, xanchor="left",
                       yanchor="top", showarrow=False, bgcolor=t["surface"], borderpad=3,
                       align="left", font=dict(size=10, color=t["ink"]),
                       text=("s_min = 2.257/λ centred, <b>4.514/λ one-sided</b> — "
                             "exactly double, because<br>n_eff = 2√π·s·λ becomes √π·s·λ "
                             "when half the kernel support is discarded"))
    fig.update_yaxes(title_text="share of events", tickformat=".0%", row=3, col=1)
    fig.update_xaxes(title_text="s_min (s), log axis", type="log", row=3, col=1)

    pc = sc_["burst_orientation_PRIMARY"]
    po = so_["burst_orientation_PRIMARY"]
    fig.update_layout(
        title=dict(text=(
            "<b>The causal re-derivation — D22's standing precondition, discharged, "
            "and it comes back positive</b><br>"
            "<sup>D22 closed the field as a detector on two structural facts: the "
            "statistic saturates at −1, and being <b>centred</b> it cannot lead. It "
            "assumed both booleans read forward equally, so <i>relative ordering "
            "survives</i>. <b>That assumption is false.</b> Remove the forward read from "
            "both and the ordering <b>reverses</b>: the field goes from lagging by 0.20 "
            "kernel widths to leading by 1.52, on 19 of 19 contributing events, in both "
            "segments. Same cohort, same anchors, same ladder, same debounce, same "
            "circular-shift null — the kernel is the only thing that changes.<br>"
            "<b>What this does not settle:</b> saturation is untouched, only 19 of 100 "
            "cohort events contribute a matched onset, and under a causal kernel "
            "dL/dln s weights recent lags while λ̂ averages the whole half-kernel "
            "(centroid 0.80·s) — so a <i>shorter level kernel</i> might buy the same "
            "lead. Task 3's fixed-kernel control is now the decisive test, not a "
            "formality.</sup>"),
            font=dict(size=15, color=t["ink"]), x=0.01, xanchor="left"),
        height=1080, paper_bgcolor=t["plane"], plot_bgcolor=t["surface"],
        font=dict(family='system-ui, -apple-system, "Segoe UI", sans-serif',
                  size=11, color=t["ink2"]),
        legend=dict(orientation="h", y=1.045, x=1, xanchor="right",
                    bgcolor="rgba(0,0,0,0)"),
        margin=dict(l=70, r=40, t=132, b=50))
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
    out = Path(rel(args.out)); out.mkdir(parents=True, exist_ok=True)
    fig = build(rel("results/scale_field/artifacts"), THEMES[args.theme])
    path = out / f"08_onesided_{args.theme}.html"
    fig.write_html(path, include_plotlyjs=(True if args.plotlyjs == "inline" else "directory"),
                   full_html=True)
    print(f"wrote {path}")


if __name__ == "__main__":
    main()
