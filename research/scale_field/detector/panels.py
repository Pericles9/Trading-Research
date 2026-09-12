#!/usr/bin/env python
"""Scale-field panels for the two detector channels, on the validated synthetic scenarios.

WHAT THIS IS. A render of tests that already ran and passed, not a new measurement. Each
scenario corresponds to a named test in test_detector.py and reproduces its numbers through
the same code path -- ridge.detect for F, interval.detect_interval for G.

SYNTHETIC ONLY. Every tape here is generated in-process. No cohort file is opened, which is
what keeps this inside D26 (see GOING_LIVE.md).

THE RENDERER IS IMPORTED, NOT REWRITTEN, per the standing rule that there is one palette in
the repo and not two that drift:

    research/phase_10d_diag1/plot_boundary_through_time.py   -> THEMES
    research/scale_field/plot_scale_field.py                 -> add_channel, add_resolution_floor,
                                                                knn_rate, et, div_colorscale

`add_channel` is the fine-band heatmap construction that was signed off for the panels; it
is called ONCE PER CHANNEL rather than reimplemented, which is the whole point. Neither
module is modified by this file.

A NOTE ON THE X AXIS. add_channel renders through `et()`, which maps epoch nanoseconds to
America/New_York wall clock because every axis in this repo is read in ET. These tapes have
no date, so t = 0 is anchored to a nominal 09:30 purely so the axis is legible in the
format the rest of the programme reads. The times on these charts mean elapsed seconds and
nothing else. Every title and caption says so.

Run:  .venv/Scripts/python.exe research/scale_field/detector/panels.py
Out:  results/scale_field/charts/detector/
"""
from __future__ import annotations

import json
import os
import sys
import time

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
sys.path.insert(0, os.path.join(REPO_ROOT, "research", "scale_field"))
sys.path.insert(0, os.path.join(REPO_ROOT, "research", "phase_10d_diag1"))

from plot_boundary_through_time import THEMES                      # noqa: E402
from plot_scale_field import (                                     # noqa: E402
    add_channel,
    add_resolution_floor,
    et,
    knn_rate,
)

from detector import POISSON_NOISE_CONSTANT, detect                # noqa: E402
from detector.interval import G0, G, detect_interval               # noqa: E402
from detector.moments import F                                     # noqa: E402
from detector.validate_interval import clumped_tape, hump_lam, sample  # noqa: E402

OUT = os.path.join(REPO_ROOT, "results", "scale_field", "charts", "detector")

# The two Poisson constants. Correct for SYNTHETIC POISSON tapes, which is all that is
# rendered here, and wrong for the cohort -- see GOING_LIVE.md.
NOISE_C_F = POISSON_NOISE_CONSTANT      # 0.87
NOISE_C_G = 0.348                       # measured in measure_noise_constant()
KAPPA = 1.0

T0, T1 = 0.0, 1500.0
S_LO, S_HI = 2.0, 300.0

# t = 0 anchored here for axis legibility only. These tapes have no date.
BASE_NS = pd.Timestamp("2020-01-02 09:30", tz="America/New_York").value


def to_ns(t_seconds):
    return (BASE_NS + np.asarray(t_seconds, dtype=float) * 1e9).astype("int64")


# ---------------------------------------------------------------------------------------
# Scenario tapes. 1 and 2 are the constructions validate_interval.py already uses; 3 is the
# realistic combination and is built here because it did not exist.
# ---------------------------------------------------------------------------------------

def scenario_rate_hump():
    return sample(hump_lam, T1, 70.0, 41)


def scenario_clumping():
    return clumped_tape()


def scenario_combined(seed=61, bg=6.0, e0=560.0, e1=700.0, K=7, tight=0.015):
    """A genuine rate excursion at t=850 AND a clumping episode at t=630.

    The clumping is laid down at the LOCAL rate where it sits, so it changes interval
    structure without changing lambda-hat -- the same trick scenario 2 uses, applied inside
    a tape that also has a gradient. That separates the two findings on one axis: F should
    own the hump, G should own the clump, and G should ALSO show the size-bias skirt around
    the hump where no clumping exists.
    """
    rng = np.random.default_rng(seed)
    p = sample(hump_lam, T1, 70.0, seed)
    local = float(np.mean(hump_lam(np.linspace(e0, e1, 400))))
    p = p[(p < e0) | (p > e1)]
    n_par = rng.poisson(local / K * (e1 - e0))
    parents = e0 + np.sort(rng.random(n_par)) * (e1 - e0)
    kids = (parents[:, None] + rng.exponential(tight, size=(n_par, K))).ravel()
    return np.sort(np.concatenate([p, kids[(kids >= e0) & (kids <= e1)]]))


# ---------------------------------------------------------------------------------------
# Field evaluation on the (t, log2 s) grid the panels use
# ---------------------------------------------------------------------------------------

def field_grids(prints, n_t=340, per_octave=5):
    """F and D = G - G0 over a shared grid. Cells with no defined estimate stay NaN --
    masked, not guessed, exactly as the committed panels do."""
    from detector.interval import interval_carriers

    carriers, x_int, _ = interval_carriers(prints)
    ts = np.linspace(T0, T1, n_t)
    n_s = int(per_octave * np.log2(S_HI / S_LO)) + 1
    scales = np.exp(np.linspace(np.log(S_LO), np.log(S_HI), n_s))

    ZF = np.full((n_s, n_t), np.nan)
    ZG = np.full((n_s, n_t), np.nan)
    for i, s in enumerate(scales):
        for j, t in enumerate(ts):
            ZF[i, j] = F(prints, t, s)
            g = G(carriers, x_int, t, s)
            ZG[i, j] = np.nan if not np.isfinite(g) else g - G0
    return ts, np.log2(scales), ZF, ZG


def mark_features(fig, row, feats, t_theme, *, colour, symbol, label, get_t, get_s, get_cal):
    """Overlay detected survivors at their polished (t, s), sized by calibrated significance.

    Same convention the F-channel apexes already use: the mark sits where the solver put it,
    not where a grid cell is.
    """
    if not feats:
        return
    cals = np.array([get_cal(f) for f in feats], dtype=float)
    sizes = 8.0 + 14.0 * (np.log10(np.clip(cals, 1e-6, None) + 1.0)
                          / max(np.log10(cals.max() + 1.0), 1e-9))
    fig.add_trace(
        go.Scatter(
            x=et(to_ns([get_t(f) for f in feats])),
            y=[np.log2(get_s(f)) for f in feats],
            mode="markers",
            marker=dict(size=sizes, color=colour, symbol=symbol,
                        line=dict(color=t_theme["ink"], width=1.1), opacity=0.95),
            name=label, showlegend=False,
            customdata=np.stack([[get_t(f) for f in feats],
                                 [get_s(f) for f in feats], cals], axis=-1),
            hovertemplate=("<b>" + label + "</b><br>t = %{customdata[0]:.2f} s"
                           "<br>s* = %{customdata[1]:.2f} s"
                           "<br>calibrated = %{customdata[2]:.2f}<extra></extra>"),
        ),
        row=row, col=1,
    )


def build_panel(name, prints, title, finding, theme="light", counts_are_illustrative=False):
    t_theme = THEMES[theme]
    ts, y, ZF, ZG = field_grids(prints)
    x_ns = to_ns(ts)

    f_feats = detect(prints, T0, T1, S_LO, S_HI, noise_constant=NOISE_C_F, kappa=KAPPA,
                     fit_durations=False)
    g_feats = detect_interval(prints, T0, T1, S_LO, S_HI, noise_constant=NOISE_C_G,
                              kappa=KAPPA)

    fig = make_subplots(
        rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.045,
        row_heights=[0.16, 0.42, 0.42],
        subplot_titles=(
            "local print rate (prints/s, log) — the tape the two channels see",
            "RATE channel — F = s²·λ̂″/λ̂ — circles are ridge.detect survivors",
            "INTERVAL channel — D = G − G₀ — diamonds are interval.detect_interval survivors "
            "(clumped ▼ / regular ▲ by hover)",
        ),
    )

    rate = knn_rate(to_ns(prints), x_ns)
    fig.add_trace(go.Scattergl(x=et(x_ns), y=np.where(rate > 0, rate, np.nan),
                               mode="lines", line=dict(color=t_theme["ink2"], width=1.2),
                               showlegend=False, name="print rate",
                               hovertemplate="%{y:.2f} prints/s<extra></extra>"),
                  row=1, col=1)
    fig.update_yaxes(title_text="prints/s", type="log", row=1, col=1)

    lo2, hi2 = float(y.min()), float(y.max())
    add_channel(fig, 2, x_ns, y, ZF, t_theme, theme, "F<br>(asinh scale)", 0.62, True, "F")
    add_channel(fig, 3, x_ns, y, ZG, t_theme, theme, "G − G₀<br>(asinh, decades)", 0.18,
                False, "G − G₀ (dec)")

    add_resolution_floor(fig, (2, 3), et(x_ns), knn_rate(to_ns(prints), x_ns),
                         t_theme, lo2, hi2, label_row=2)

    mark_features(fig, 2, f_feats, t_theme, colour=t_theme["winner"], symbol="circle",
                  label="F survivor", get_t=lambda f: f.t_ridge,
                  get_s=lambda f: f.s_selected, get_cal=lambda f: f.calibrated)
    for direction, sym in (("clumped", "diamond"), ("regular", "triangle-up")):
        sel = [f for f in g_feats if f.direction == direction]
        mark_features(fig, 3, sel, t_theme, colour=t_theme["winner"], symbol=sym,
                      label=f"G survivor ({direction})", get_t=lambda f: f.t_ridge,
                      get_s=lambda f: f.s_selected, get_cal=lambda f: f.calibrated)

    nan_f, nan_g = float(np.isnan(ZF).mean()), float(np.isnan(ZG).mean())
    count_note = (
        "<b>Feature COUNTS on this panel are illustrative only.</b> persistence_octaves is "
        "read off the seed ladder, so on dense interacting tapes the count moves with seed "
        "density (F 6/7/7/6/7, G 7/6/5/6/5 across 3–12 rungs/octave). Per-feature values "
        "(t, s*, calibrated) are solver-polished and do not move. "
        if counts_are_illustrative else "")

    fig.update_layout(
        title=dict(text=(
            f"<b>SYNTHETIC — {title}</b><br>"
            f"<sup><b>{finding}</b><br>"
            f"{prints.size:,} prints on a generated tape. <b>No cohort data.</b> "
            f"x-axis is a nominal wall clock anchored at 09:30 so the axis reads in the "
            f"house format; these tapes have no date and the times mean elapsed seconds.<br>"
            f"Calibration, both channels: z = |departure|·√n_eff ⁄ c, "
            f"cal = z − √(2·ln(T/s)), survivors are cal &gt; κ = {KAPPA:g} with "
            f"n_eff ≥ 8 and persistence ≥ 1 octave. "
            f"c<sub>F</sub> = {NOISE_C_F} (Poisson, for F). "
            f"c<sub>G</sub> = {NOISE_C_G} (Poisson, measured). "
            f"F's baseline is 0 and is ARITHMETIC; <b>G's baseline is a CONSTANT, "
            f"G₀ = −γ/ln10 = {G0:.6f}</b>, not zero.<br>"
            f"<b>G's rate-gradient size-bias is UNCORRECTED in this render.</b> Where G "
            f"marks appear on a gradient with no clumping, those are the expected artifact "
            f"being displayed, not false positives to be explained away. "
            f"{count_note}"
            f"Blank = no estimate, masked not guessed: F {nan_f:.0%}, G {nan_g:.0%} of cells. "
            f"Black line = s<sub>min</sub> = 2.26/λ, a DATA limit. Colour is asinh, "
            f"unclipped, ticks in original units — for G, negative = intervals SHORTER than "
            f"the local rate implies (clumped).</sup>"),
            font=dict(size=15, color=t_theme["ink"]), x=0.01, xanchor="left"),
        height=1020, hovermode="closest",
        paper_bgcolor=t_theme["plane"], plot_bgcolor=t_theme["surface"],
        font=dict(family='system-ui, -apple-system, "Segoe UI", sans-serif',
                  size=11, color=t_theme["ink2"]),
        margin=dict(l=72, r=104, t=190, b=45), showlegend=False,
    )
    fig.update_xaxes(title_text="elapsed time (axis shown as nominal ET wall clock)", row=3, col=1)
    fig.update_xaxes(showgrid=False, linecolor=t_theme["axis"], zeroline=False)
    fig.update_yaxes(gridcolor=t_theme["grid"], linecolor=t_theme["axis"], zeroline=False)
    for a in fig.layout.annotations[:3]:
        a.font.update(size=11, color=t_theme["ink2"])
        a.update(x=0, xanchor="left")

    return fig, f_feats, g_feats


def main():
    os.makedirs(OUT, exist_ok=True)
    scenarios = [
        ("s1_rate_hump_only", scenario_rate_hump(),
         "Scenario 1 — pure rate hump, ZERO clumping",
         "The size-bias finding. G fires on the hump's FLANKS with no clumping present "
         "anywhere in the tape — any rate gradient reads as clumping.",
         "test_cross_check_G_DOES_respond_to_a_pure_rate_hump", False),
        ("s2_clumping_only", scenario_clumping(),
         "Scenario 2 — clumping at CONSTANT mean rate, zero gradient",
         "The case F cannot see. G fires once and hard; F speckles into several weak marks "
         "rather than forming a coherent trumpet.",
         "test_positive_control_G_sees_what_F_cannot", False),
        ("s3_combined", scenario_combined(),
         "Scenario 3 — a genuine rate excursion that ALSO clusters",
         "The realistic case. The channels agree on the clump and diverge around the hump, "
         "where G's marks are the uncorrected size-bias rather than structure.",
         "combination of the two controls above; no single test asserts this tape", True),
    ]

    manifest = {
        "what": "Scale-field panels for the F and G detector channels.",
        "synthetic_only": True,
        "cohort_contact": "none",
        "d26": ("instrument work on synthetic data, which D26 permits explicitly; it becomes "
                "cohort timing work, which D26 closes, the moment a real tape is read"),
        "renderer": {
            "imported_not_rewritten": True,
            "palette_and_themes": "research/phase_10d_diag1/plot_boundary_through_time.py",
            "heatmap_and_floor": ("research/scale_field/plot_scale_field.py -- add_channel "
                                  "called once per channel, plus add_resolution_floor and "
                                  "knn_rate"),
            "modified": "neither module was modified",
        },
        "calibration": {
            "formula": "z = |departure|*sqrt(n_eff)/c ; cal = z - sqrt(2*ln(T/s))",
            "kappa": KAPPA,
            "c_F": NOISE_C_F, "c_G": NOISE_C_G,
            "both_are_poisson_constants": ("correct for these synthetic Poisson tapes and "
                                           "wrong for the cohort -- see "
                                           "research/scale_field/detector/GOING_LIVE.md"),
            "G_baseline": G0,
        },
        "known_uncorrected": {
            "G_size_bias": ("G's response to a rate gradient is NOT corrected in these "
                            "renders. Scenario 1 marks are the artifact on display."),
            "persistence_counts": ("feature counts are seed-ladder dependent on dense tapes; "
                                   "scenario 3 counts are captioned illustrative only"),
        },
        "x_axis": ("nominal ET wall clock anchored at 09:30 for legibility. These tapes have "
                   "no date; the times mean elapsed seconds."),
        "html_is_gitignored": ("results/scale_field/charts/*/*.html -- regenerable by running "
                               "research/scale_field/detector/panels.py; this manifest is the "
                               "tracked record"),
        "scenarios": [],
    }

    for slug, tape, title, finding, test_name, illustrative in scenarios:
        t0 = time.time()
        fig, ff, gf = build_panel(slug, tape, title, finding,
                                  counts_are_illustrative=illustrative)
        path = os.path.join(OUT, f"{slug}.html")
        fig.write_html(path, include_plotlyjs="directory", full_html=True)
        elapsed = time.time() - t0

        manifest["scenarios"].append(dict(
            file=f"{slug}.html", title=title, finding=finding,
            corresponds_to_test=test_name, n_prints=int(tape.size),
            runtime_s=round(elapsed, 1),
            counts_illustrative_only=illustrative,
            F_survivors=len(ff),
            F_best_calibrated=round(max((f.calibrated for f in ff), default=0.0), 2),
            G_survivors=len(gf),
            G_best_calibrated=round(max((f.calibrated for f in gf), default=0.0), 2),
            G_directions=sorted({f.direction for f in gf}),
            G_features=[dict(t=round(f.t_ridge, 2), s=round(f.s_selected, 2),
                             direction=f.direction, D=round(f.D_at_ridge, 4),
                             cal=round(f.calibrated, 2)) for f in gf],
            F_features=[dict(t=round(f.t_ridge, 2), s=round(f.s_selected, 2),
                             cal=round(f.calibrated, 2)) for f in ff],
        ))
        print(f"{slug:22s} {tape.size:7,} prints  F {len(ff):2d} (best cal "
              f"{max((f.calibrated for f in ff), default=0.0):7.2f})  "
              f"G {len(gf):2d} (best cal {max((f.calibrated for f in gf), default=0.0):7.2f})"
              f"  {elapsed:5.1f}s")

    with open(os.path.join(OUT, "chart_manifest.json"), "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2)
    print("\nwritten:", os.path.relpath(OUT, REPO_ROOT))


if __name__ == "__main__":
    main()
