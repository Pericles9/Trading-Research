#!/usr/bin/env python
"""
The scale-space field, charted.

Extends the Diag1 chart grammar (research/phase_10d_diag1/plot_boundary_through_time.py,
recorded as reusable for exactly this) with the KERNEL-SCALE axis replacing the
boundary track. Palette and theme come from that module by import, so there is one
palette in the repo rather than two that drift.

Three files, one chart each (CLAUDE.md chart contract):

  01_field_coarse   1 s .. 2048 s, whole session
  02_field_fine     15.6 ms .. 1 s, +/- 15 s around the D7 detection anchor, inside
                    a +/- 15 min read -- see scale_axis.fine in config/scale_field.json
  03_scale_profile  the scale axis itself, against v3's committed Allan curve.
                    Row 4 is the DISPERSION across time at each scale. It is there
                    because A(T) is a variance statistic and rows 2-3 are medians:
                    a change of character can live entirely in the spread while the
                    median stays flat, so reading the knee against a median alone
                    would be the wrong comparison.

Panels 01/02, on one shared time axis:

    1  price                     orientation
    2  RATE channel      dL/dln s   L = ln(kernel-smoothed intensity)
    3  INTERVAL channel  dm/dln s   m = kernel-weighted mean log10 interval
    4  local print rate            which stretches are thin, so the field is read honestly

SIGN CONVENTION, and it is opposite between the two channels -- test 3 in the
acceptance suite exists because getting this wrong is easy and invisible:

    dlograte < 0   intensity FALLS as the kernel widens -> mass is concentrated
                   here at this scale. This is the burst-like end.
    dm       > 0   m RISES with s -> intervals here are shorter than the
                   surroundings. This is the burst-like end.

So the two channels disagree in sign about the same phenomenon. The colour ramp on
the rate panel is therefore REVERSED, so that warm reads as burst-like on both
panels, while every colourbar tick still carries the true signed value. The mapping
is stated on the figure; nothing is negated in the data.

COLOUR MAPPING. Values are mapped through asinh, not clipped (CLAUDE.md: outliers
shown, never clipped). dlograte is bounded below by -1 and has a long positive tail
to ~+15, so a linear symmetric ramp would render the whole field as one flat colour
and a handful of bright cells. asinh is linear near 0 and logarithmic in the tails,
the zero point sits exactly at the neutral colour, and the ticks are labelled in the
original units.

NaN IS DRAWN AS ABSENCE, never as a value. Below the local inter-trade interval the
effective sample size collapses and `field()` returns NaN under n_eff >= 8. Those
cells are left blank. The blank region IS the result at that scale -- it is not a
rendering gap and it must not be filled.

NO THRESHOLD IS SHOWN because none exists yet. v3's knees are drawn as a PREDICTION
for where the scale axis should change character, not as a cutoff.

Usage:
    python plot_scale_field.py --event AEHL_2021-02-19_37.50
    python plot_scale_field.py --event CREX_2022-02-01_41.48 --theme dark
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
from scale_field import NEFF_S_MIN_COEF, s_min_for_rate  # noqa: E402
from plot_boundary_through_time import THEMES  # noqa: E402  -- one palette, imported

# Diverging ramp for a SIGNED field. The warm half is the Diag1 accent (#eb6834)
# darkened and lightened; the cool half is that module's BLUE_RAMP. Neutral sits at
# zero exactly -- see div_colorscale.
NEG = ["#0d366b", "#184f95", "#256abf", "#3987e5", "#86b6ef", "#cde2fb"]
POS = ["#fbe3cd", "#f6c9a2", "#f2a874", "#eb6834", "#c9491d", "#8f300f"]
NEUTRAL = {"light": "#f4f2ec", "dark": "#26262a"}

# Ticks in ORIGINAL units, positioned at asinh of themselves.
CBAR_TICKS = [-8, -4, -2, -1, -0.5, 0, 0.5, 1, 2, 4, 8, 16]


def div_colorscale(lo: float, hi: float, theme: str, reverse: bool = False):
    """Diverging scale whose neutral colour lands exactly on zero, wherever zero sits
    between lo and hi. A symmetric ramp would waste half its range here: dlograte is
    bounded below by -1 and runs to +15."""
    if not (lo < 0 < hi):
        span = [c for c in (NEG[::-1] if lo >= 0 else NEG)]
        span = POS if lo >= 0 else NEG[::-1]
        return [[i / (len(span) - 1), c] for i, c in enumerate(span)]
    frac = (0.0 - lo) / (hi - lo)
    neg, pos = NEG, POS
    if reverse:
        neg, pos = [c for c in POS[::-1]], [c for c in NEG[::-1]]
    stops = []
    for i, c in enumerate(neg):
        stops.append([frac * (i / (len(neg) - 1)), c])
    stops.append([frac, NEUTRAL[theme]])
    for i, c in enumerate(pos):
        stops.append([frac + (1 - frac) * ((i + 1) / len(pos)), c])
    stops[0][0], stops[-1][0] = 0.0, 1.0
    seen, out = set(), []
    for v, c in stops:                       # plotly requires strictly sorted stops
        v = min(max(float(v), 0.0), 1.0)
        if v in seen:
            v = min(v + 1e-6, 1.0)
        seen.add(v)
        out.append([v, c])
    out.sort(key=lambda s: s[0])
    return out


def et(ns):
    """Epoch ns -> naive America/New_York wall clock, for DISPLAY ONLY.

    Every axis in this repo is read in ET. Plotting the raw epoch would put an rth
    event under a 16:00 label that is really 11:00, which is the same confusion the
    D3 clock exists to prevent -- so the display conversion goes through the same
    timezone, not through a fixed offset.
    """
    return (pd.to_datetime(pd.Series(np.asarray(ns, dtype="int64")), unit="ns", utc=True)
            .dt.tz_convert("America/New_York").dt.tz_localize(None))


def grid(df: pd.DataFrame, col: str):
    """long form -> (t_ns, log2_scale, Z[scale, time])."""
    p = df.pivot_table(index="log2_scale", columns="t_ns", values=col, dropna=False)
    return p.columns.to_numpy(), p.index.to_numpy(), p.to_numpy()


def add_channel(fig, row, x, y, Z, t, theme, title, cbar_y, reverse, hover):
    v = Z[np.isfinite(Z)]
    lo, hi = (float(v.min()), float(v.max())) if v.size else (-1.0, 1.0)
    A = np.arcsinh(Z)
    alo, ahi = np.arcsinh(lo), np.arcsinh(hi)
    ticks = [t_ for t_ in CBAR_TICKS if lo <= t_ <= hi]
    fig.add_trace(
        go.Heatmap(
            x=et(x), y=y, z=A, zmin=alo, zmax=ahi,
            colorscale=div_colorscale(alo, ahi, theme, reverse=reverse),
            customdata=Z,
            hovertemplate=f"%{{x}}<br>scale 2^%{{y:.2f}} s<br>{hover}"
                          " %{customdata:.3f}<extra></extra>",
            colorbar=dict(
                title=dict(text=title, font=dict(size=10, color=t["ink2"])),
                len=0.30, y=cbar_y, thickness=10, outlinewidth=0,
                tickmode="array", tickvals=[float(np.arcsinh(v_)) for v_ in ticks],
                ticktext=[f"{v_:g}" for v_ in ticks],
                tickfont=dict(size=9, color=t["muted"]),
            ),
        ),
        row=row, col=1,
    )
    fig.update_yaxes(title_text="log₂ kernel scale (s)", row=row, col=1)
    return lo, hi


def knn_rate(tape_ns, x_ns, k=20):
    """Local print rate by k-nearest-neighbour spacing: lambda(t) = k / (span of the k
    prints bracketing t). Adaptive, never divides by an empty window, and matched to the
    quantity it feeds -- n_eff >= 8 needs about 8 effective prints, so a k=20 estimator
    is the right scale. A fixed-width count would swing between 0 and a large number on
    a sparse tape and draw the floor as noise instead of a floor."""
    ts = np.asarray(tape_ns, dtype=np.int64)
    if ts.size < k + 1:
        return np.full(len(x_ns), np.nan)
    i = np.searchsorted(ts, np.asarray(x_ns, dtype=np.int64))
    lo = np.clip(i - k // 2, 0, ts.size - 1 - k)
    span = (ts[lo + k] - ts[lo]).astype(np.float64) / 1e9
    return np.where(span > 0, k / span, np.nan)


def add_resolution_floor(fig, rows, x, rate, t, lo2, hi2, label_row=None):
    """s_min(t) = 2.26 / lambda(t), drawn on the field panels.

    n_eff = 2*sqrt(pi)*s*lambda >= 8  =>  s >= 2.257/lambda. This is a DATA limit, not
    a rendering one: nothing below the line is measurable at any output resolution, on
    any chart. Drawing it turns the blank region from something mysterious into
    something labelled, and makes the band's lower limit a per-event fact rather than
    a config constant. At the median rth rate of 2.5 prints/s the floor is 903 ms --
    which is most of the fine band."""
    smin = s_min_for_rate(rate)
    y = np.where(np.isfinite(smin) & (smin > 0), np.log2(np.maximum(smin, 1e-12)), np.nan)
    if not np.isfinite(y).any():
        return
    for r in rows:
        fig.add_trace(
            go.Scattergl(x=x, y=np.where((y >= lo2) & (y <= hi2), y, np.nan), mode="lines",
                         line=dict(color=t["ink"], width=1.6),
                         name="resolution floor", showlegend=False,
                         hovertemplate="%{x}<br>s_min %{y:.2f} (log2 s)<extra></extra>"),
            row=r, col=1)
    if label_row is not None:
        i = int(np.nanargmax(np.isfinite(y)))
        fig.add_annotation(row=label_row, col=1, x=x.iloc[i], y=float(y[i]),
                           text="resolution floor  s<sub>min</sub> = 2.26/\u03bb",
                           showarrow=False, xanchor="left", yanchor="bottom", xshift=4,
                           font=dict(size=9, color=t["ink"]))


def knee_lines(fig, rows, knee_s, label, t, x_end, lo2, hi2):
    y = float(np.log2(knee_s))
    if not (lo2 <= y <= hi2):
        return False
    for r in rows:
        fig.add_hline(y=y, row=r, col=1,
                      line=dict(color=t["ink2"], width=1.2, dash="dash"))
    fig.add_annotation(row=rows[0], col=1, x=x_end, y=y, text=label,
                       showarrow=False, xanchor="left", yanchor="bottom", xshift=4,
                       font=dict(size=9, color=t["ink2"]))
    return True


def local_rate(tape_ns, x_ns, win_s):
    """Prints per second in a centred window of `win_s`, evaluated on the chart grid.
    Support, not a smoothed estimate -- it answers 'how much data is under this
    column', which is the only thing panel 4 is for."""
    lo = np.searchsorted(tape_ns, x_ns - int(win_s * 5e8))
    hi = np.searchsorted(tape_ns, x_ns + int(win_s * 5e8))
    r = (hi - lo) / win_s
    return r          # zero stays zero; the caller blanks it rather than flooring it


def band_figure(ev, band, df, tape, mf, t, theme, seg_knees):
    anchor = et([mf["detection_anchor"]["anchor_ns"]]).iloc[0]
    x, y, Zr = grid(df, "dlograte")
    _, _, Zm = grid(df, "dm")
    pv = next(b for b in mf["bands"] if b["band"] == band)

    fig = make_subplots(
        rows=4, cols=1, shared_xaxes=True, vertical_spacing=0.035,
        row_heights=[0.13, 0.35, 0.35, 0.12],
        subplot_titles=(
            "price",
            "RATE channel — dL/dln s — warm = intensity concentrated at this scale",
            "INTERVAL channel — dm/dln s — warm = intervals shorter than the surroundings",
            "local print rate (prints/s, log)",
        ),
    )

    tp = tape[(tape["ts_ns"] >= x.min()) & (tape["ts_ns"] <= x.max())]
    fig.add_trace(go.Scattergl(x=et(tp["ts_ns"]), y=tp["price"],
                               mode="lines", line=dict(color=t["ink2"], width=1),
                               showlegend=False, name="price",
                               hovertemplate="%{x}<br>%{y}<extra></extra>"),
                  row=1, col=1)
    fig.update_yaxes(title_text="price", row=1, col=1)

    lo2, hi2 = float(y.min()), float(y.max())
    r_lo, r_hi = add_channel(fig, 2, x, y, Zr, t, theme,
                             "dL/dln s<br>(asinh scale)", 0.55, True, "dL/dln s")
    m_lo, m_hi = add_channel(fig, 3, x, y, Zm, t, theme,
                             "dm/dln s<br>(asinh scale)", 0.20, False, "dm/dln s")

    xe = et(x).iloc[-1]
    shown = [k for k, (s, lab) in seg_knees.items()
             if knee_lines(fig, (2, 3), s, lab, t, xe, lo2, hi2)]

    if x.min() <= mf["detection_anchor"]["anchor_ns"] <= x.max():
        for r in (1, 2, 3, 4):
            fig.add_vline(x=anchor, row=r, col=1,
                          line=dict(color=t["winner"], width=1.4, dash="dot"))
        fig.add_annotation(row=1, col=1, x=anchor, y=1.0, yref="y domain",
                           text="D7 detection anchor", showarrow=False,
                           xanchor="left", yanchor="top", xshift=4,
                           font=dict(size=9, color=t["winner"]))

    # lambda(t) for the resolution floor, by kNN spacing -- see knn_rate.
    rate_floor = knn_rate(tape["ts_ns"].to_numpy(), x)
    add_resolution_floor(fig, (2, 3), et(x), rate_floor, t, lo2, hi2, label_row=2)

    rate = local_rate(tape["ts_ns"].to_numpy(), x, max(1.0, pv["scale_max_seconds"]))
    fig.add_trace(go.Scattergl(x=et(x), y=np.where(rate > 0, rate, np.nan),
                               mode="lines", line=dict(color=t["muted"], width=1),
                               showlegend=False, name="print rate",
                               hovertemplate="%{x}<br>%{y:.2f} prints/s<extra></extra>"),
                  row=4, col=1)
    fig.update_yaxes(title_text="prints/s", type="log", row=4, col=1)

    nan_r = float(np.isnan(Zr).mean())
    nan_m = float(np.isnan(Zm).mean())
    knee_txt = ("; ".join(seg_knees[k][1] for k in shown) if shown
                else "v3 knees outside this band's scale range")
    fig.update_layout(
        title=dict(text=(
            f"<b>{ev}</b> · scale-space field · <b>{band}</b> band "
            f"{pv['scale_min_seconds']:g}–{pv['scale_max_seconds']:g} s, "
            f"{pv['n_scales']} scales at {pv['scales_per_octave']:g}/octave · "
            f"{pv['coverage']}<br>"
            f"<sup>{pv['n_arrivals_after_tie_collapse']:,} arrivals "
            f"({pv['n_ties_collapsed']:,} ties collapsed), "
            f"{pv['n_intervals']:,} intervals. "
            f"Blank = n_eff &lt; 8, masked not guessed: rate {nan_r:.0%}, "
            f"interval {nan_m:.0%} of cells. "
            f"Black line = resolution floor s<sub>min</sub> = 2.26/\u03bb, a DATA limit "
            f"(mean \u03bb here {pv['local_rate_prints_per_s']:.2f} prints/s \u2192 "
            f"{pv['s_min_seconds_at_mean_rate']:.3g} s): nothing below it is measurable at "
            f"any output resolution. "
            f"Colour is asinh, unclipped; ticks in original units. "
            f"Dashed = {knee_txt} (v3 prediction, not a cutoff). "
            f"No threshold applied — the Poisson null does not fit this tape.</sup>"),
            font=dict(size=15, color=t["ink"]), x=0.01, xanchor="left"),
        height=1080, hovermode="x unified",
        paper_bgcolor=t["plane"], plot_bgcolor=t["surface"],
        font=dict(family='system-ui, -apple-system, "Segoe UI", sans-serif',
                  size=11, color=t["ink2"]),
        margin=dict(l=72, r=104, t=112, b=45), showlegend=False,
    )
    fig.update_xaxes(title_text="America/New_York wall clock (D3)", row=4, col=1)
    fig.update_xaxes(showgrid=False, linecolor=t["axis"], zeroline=False)
    fig.update_yaxes(gridcolor=t["grid"], linecolor=t["axis"], zeroline=False)
    for a in fig.layout.annotations[:4]:
        a.font.update(size=11, color=t["ink2"])
        a.update(x=0, xanchor="left")
    return fig


def profile_figure(ev, df, allan, mf, t, seg_knees):
    """The scale axis itself. This is where the brief's one gate is read: v3's knee is
    a prediction for the continuous field, and the question is whether the field
    changes character near it.

    The two bands cover DIFFERENT TIME WINDOWS (coarse = whole session, fine = 30 min
    at the anchor), so they are drawn as separate series and never joined into one
    curve. Overlaying them would imply a continuity across s = 1 s that the run does
    not have."""
    fig = make_subplots(
        rows=5, cols=1, shared_xaxes=True, vertical_spacing=0.035,
        row_heights=[0.24, 0.20, 0.20, 0.20, 0.16],
        subplot_titles=(
            "v3 Allan factor A(T) — the committed discrete statistic, this event",
            "RATE channel — dL/dln s across time at each scale (median, 10–90%)",
            "INTERVAL channel — dm/dln s across time at each scale (median, 10–90%)",
            "DISPERSION across time (IQR) — the like-for-like comparator for A(T)",
            "n time-points where the field is defined (n_eff ≥ 8)",
        ),
    )

    a = allan[np.isfinite(allan["allan"])]
    fig.add_trace(go.Scatter(x=a["log2_T"], y=a["allan"], mode="lines+markers",
                             line=dict(color=t["ink2"], width=1.6),
                             marker=dict(size=6, color=t["ink2"]),
                             name="A(T)", customdata=a["n_pairs"],
                             hovertemplate="T = 2^%{x:.0f} s<br>A = %{y:.2f}"
                                           "<br>%{customdata} pairs<extra></extra>"),
                  row=1, col=1)
    low = a[a["n_pairs"] < 20]
    if len(low):
        fig.add_trace(go.Scatter(x=low["log2_T"], y=low["allan"], mode="markers",
                                 marker=dict(size=11, color="rgba(0,0,0,0)",
                                             line=dict(color=t["muted"], width=1.5)),
                                 name="low power", hoverinfo="skip", showlegend=False),
                      row=1, col=1)
    fig.add_hline(y=1.0, row=1, col=1, line=dict(color=t["grid"], width=1, dash="dot"))
    fig.add_annotation(row=1, col=1, x=a["log2_T"].max(), y=0.0, yref="y domain",
                       text="Poisson A = 1 (fixture, not a threshold)", showarrow=False,
                       xanchor="right", yanchor="bottom",
                       font=dict(size=9, color=t["muted"]))
    fig.update_yaxes(title_text="A(T)", type="log", dtick=1, row=1, col=1)

    colors = {"coarse": "#256abf", "fine": "#eb6834"}
    for r, key, unit in ((2, "dlograte", "dL/dln s"), (3, "dm", "dm/dln s")):
        for band, g in df.groupby("band"):
            q = (g.groupby("log2_scale")[key]
                   .agg(med="median", lo=lambda s: s.quantile(0.10),
                        hi=lambda s: s.quantile(0.90), n="count")
                   .reset_index())
            q = q[q["n"] > 0]
            c = colors[band]
            fig.add_trace(go.Scatter(
                x=np.concatenate([q["log2_scale"], q["log2_scale"][::-1]]),
                y=np.concatenate([q["hi"], q["lo"][::-1]]),
                fill="toself", fillcolor=c.replace("#", "rgba(").replace(
                    "rgba(", "rgba(") if False else _rgba(c, 0.14),
                line=dict(width=0), hoverinfo="skip", showlegend=False), row=r, col=1)
            fig.add_trace(go.Scatter(
                x=q["log2_scale"], y=q["med"], mode="lines",
                line=dict(color=c, width=2), name=f"{band} · {unit}",
                legendgroup=band, showlegend=(r == 2), customdata=q["n"],
                hovertemplate="scale 2^%{x:.2f} s<br>median %{y:.3f}"
                              "<br>n = %{customdata}<extra></extra>"), row=r, col=1)
        fig.add_hline(y=0.0, row=r, col=1, line=dict(color=t["grid"], width=1, dash="dot"))
        fig.update_yaxes(title_text=unit, row=r, col=1)

    # Row 4. A(T) is a VARIANCE statistic, so comparing it against a median (rows 2-3)
    # is not like for like -- a change of character can sit entirely in the spread while
    # the median stays flat. The IQR across time at each scale is the comparable
    # quantity, and it is what the knee prediction should be read against.
    for key, dash in (("dlograte", "solid"), ("dm", "dot")):
        for band, g in df.groupby("band"):
            q = (g.groupby("log2_scale")[key]
                   .agg(iqr=lambda v: v.quantile(0.75) - v.quantile(0.25), n="count")
                   .reset_index())
            q = q[q["n"] > 0]
            fig.add_trace(go.Scatter(
                x=q["log2_scale"], y=q["iqr"], mode="lines",
                line=dict(color=colors[band], width=1.8, dash=dash),
                showlegend=False, customdata=q["n"],
                hovertemplate="scale 2^%{x:.2f} s<br>IQR %{y:.3f}"
                              "<br>n = %{customdata}<extra></extra>"), row=4, col=1)
    fig.update_yaxes(title_text="IQR (solid rate,<br>dotted interval)",
                     type="log", dtick=1, row=4, col=1)

    for band, g in df.groupby("band"):
        n = g.groupby("log2_scale")["dm"].count().reset_index()
        n2 = g.groupby("log2_scale")["dlograte"].count().reset_index()
        fig.add_trace(go.Scatter(x=n2["log2_scale"], y=n2["dlograte"], mode="lines",
                                 line=dict(color=colors[band], width=1.4),
                                 name=f"{band} rate", showlegend=False,
                                 hovertemplate="2^%{x:.2f} s<br>%{y} rate cells<extra></extra>"),
                      row=5, col=1)
        fig.add_trace(go.Scatter(x=n["log2_scale"], y=n["dm"], mode="lines",
                                 line=dict(color=colors[band], width=1.4, dash="dot"),
                                 name=f"{band} interval", showlegend=False,
                                 hovertemplate="2^%{x:.2f} s<br>%{y} interval cells<extra></extra>"),
                      row=5, col=1)
    fig.update_yaxes(title_text="n defined", row=5, col=1)

    for _, (s, lab) in seg_knees.items():
        xv = float(np.log2(s))
        for r in (1, 2, 3, 4, 5):
            fig.add_vline(x=xv, row=r, col=1,
                          line=dict(color=t["ink2"], width=1.2, dash="dash"))
        fig.add_annotation(row=1, col=1, x=xv, y=1.0, yref="y domain", text=lab,
                           showarrow=False, xanchor="left", yanchor="top", xshift=3,
                           font=dict(size=9, color=t["ink2"]))

    # TWO caps, because span/8 depends on which span you mean and the difference is
    # the whole point of the brief's low-power warning. v3 tiled the EXTENDED session
    # (57,600 s -> cap 7,200 s); the brief reasons about an RTH session (23,400 s ->
    # cap 2,925 s). v3's headline rung at 4,096 s is under the first and over the
    # second, which is exactly why the pair count is quoted beside it.
    for b in mf["bands"]:
        sm = b.get("s_min_seconds_at_mean_rate")
        if not sm or not np.isfinite(sm):
            continue
        xv = float(np.log2(sm))
        for r in (2, 3, 4, 5):
            fig.add_vline(x=xv, row=r, col=1,
                          line=dict(color=colors[b["band"]], width=1.4, dash="dashdot"))
        fig.add_annotation(row=4, col=1, x=xv, y=0.0, yref="y domain", xshift=3,
                           text=f"s<sub>min</sub> {b['band']} = {sm:.3g} s",
                           showarrow=False, xanchor="left", yanchor="bottom",
                           font=dict(size=9, color=colors[b["band"]]))

    cap_ext = mf["coarse_cap_seconds"]
    cap_rth = 23400.0 / 8.0
    fig.add_vrect(x0=float(np.log2(cap_rth)), x1=13.9, line_width=0,
                  fillcolor="rgba(137,135,129,0.13)", layer="below")
    fig.add_vrect(x0=float(np.log2(cap_ext)), x1=13.9, line_width=0,
                  fillcolor="rgba(137,135,129,0.16)", layer="below")
    for cv, lab, dy in ((cap_rth, f"RTH span/8 = {cap_rth:.0f} s", "top"),
                        (cap_ext, f"extended span/8 = {cap_ext:.0f} s", "bottom")):
        fig.add_annotation(x=float(np.log2(cv)), y=1.0, yref="paper", xshift=-3,
                           text=lab, showarrow=False, xanchor="right", yanchor=dy,
                           font=dict(size=9, color=t["muted"]))

    fig.update_layout(
        title=dict(text=(
            f"<b>{ev}</b> · the scale axis · continuous field vs v3's discrete gate<br>"
            f"<sup>Bands cover different time windows (coarse = whole session, "
            f"fine = ±15 s at the D7 anchor) and are NEVER joined into one curve. "
            f"Dashed = v3's committed knees, a prediction for where the field should "
            f"change character. Bands are 10–90% across time, not confidence intervals — "
            f"no matched null has been computed yet. "
            f"<b>Read rows 2–3 with the n_eff mask in mind:</b> at fine scales only the "
            f"denser stretches clear n_eff ≥ 8, so each scale's median is taken over a "
            f"different subset of time — row 4 is how much time that is, and a trend "
            f"across scale is partly a trend in which time survives. "
            f"<b>Dash-dot = s<sub>min</sub> = 2.26/\u03bb</b>, the resolution floor at "
            f"this event\u2019s mean rate: a band whose lower end sits near its own floor "
            f"cannot identify a break there.</sup>"),
            font=dict(size=15, color=t["ink"]), x=0.01, xanchor="left"),
        height=1320, hovermode="x unified",
        paper_bgcolor=t["plane"], plot_bgcolor=t["surface"],
        font=dict(family='system-ui, -apple-system, "Segoe UI", sans-serif',
                  size=11, color=t["ink2"]),
        legend=dict(orientation="h", y=1.045, x=1, xanchor="right",
                    bgcolor="rgba(0,0,0,0)"),
        margin=dict(l=72, r=40, t=118, b=52),
    )
    fig.update_xaxes(title_text="log₂ kernel scale (seconds)  ·  log₂ T for A(T)",
                     row=5, col=1)
    fig.update_xaxes(range=[-6.6, 13.9])
    fig.update_xaxes(showgrid=False, linecolor=t["axis"], zeroline=False)
    fig.update_yaxes(gridcolor=t["grid"], linecolor=t["axis"], zeroline=False)
    for ann in fig.layout.annotations[:5]:
        ann.font.update(size=11, color=t["ink2"])
        ann.update(x=0, xanchor="left")
    return fig


def _rgba(hex_color, alpha):
    h = hex_color.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return f"rgba({r},{g},{b},{alpha})"


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--event", default="AEHL_2021-02-19_37.50")
    p.add_argument("--artifacts", default="results/scale_field/artifacts")
    p.add_argument("--out", default="results/scale_field/charts")
    p.add_argument("--theme", choices=["light", "dark"], default="light")
    p.add_argument("--plotlyjs", default="directory", choices=["directory", "inline"],
                   help="'directory' writes one shared plotly.min.js beside the charts. "
                        "Never CDN — D14, the environment is offline and a CDN "
                        "reference renders a blank page.")
    args = p.parse_args()

    t = THEMES[args.theme]
    ad = Path(adapter.rel(args.artifacts))
    out = Path(adapter.rel(args.out)) / args.event
    out.mkdir(parents=True, exist_ok=True)
    jsmode = True if args.plotlyjs == "inline" else "directory"

    df = pd.read_parquet(ad / f"field_{args.event}.parquet")
    tape = pd.read_parquet(ad / f"tape_{args.event}.parquet")
    allan = pd.read_parquet(ad / f"allan_{args.event}.parquet")
    with open(ad / f"field_{args.event}_manifest.json", encoding="utf-8") as f:
        mf = json.load(f)

    seg = mf["detection_anchor"]["event_segment"]
    knees = mf["v3_prediction"]["print_rate"]
    seg_knees = {seg: (knees[seg], f"v3 knee, {seg} print rate = {knees[seg]:g} s")}
    print(f"{args.event}: segment {seg}, v3 print-rate knee {knees[seg]:g} s "
          f"(the prediction this field is read against)")

    written = []
    for name, band in (("01_field_coarse", "coarse"), ("02_field_fine", "fine")):
        fig = band_figure(args.event, band, df[df["band"] == band], tape, mf, t,
                          args.theme, seg_knees)
        path = out / f"{name}_{args.theme}.html"
        fig.write_html(path, include_plotlyjs=jsmode, full_html=True)
        written.append(str(path)); print(f"wrote {path}")

    fig = profile_figure(args.event, df, allan, mf, t, seg_knees)
    path = out / f"03_scale_profile_{args.theme}.html"
    fig.write_html(path, include_plotlyjs=jsmode, full_html=True)
    written.append(str(path)); print(f"wrote {path}")

    with open(out / "chart_manifest.json", "w", encoding="utf-8") as f:
        json.dump({"event_id": args.event, "theme": args.theme,
                   "config_hash": mf["config_hash"],
                   "field_artifact": f"{args.artifacts}/field_{args.event}.parquet",
                   "charts": written,
                   "plotlyjs": args.plotlyjs,
                   "offline_rule": "D14 — never a CDN",
                   "source": "research/scale_field/plot_scale_field.py:main",
                   "reproduce": f".venv/Scripts/python.exe research/scale_field/"
                                f"plot_scale_field.py --event {args.event} "
                                f"--theme {args.theme}"}, f, indent=2)


if __name__ == "__main__":
    main()
