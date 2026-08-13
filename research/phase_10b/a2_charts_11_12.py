"""A10b.2 charts 11 and 12 -- the knee's sampling distribution, and one bias or several."""
from __future__ import annotations

import json
import os
import sys

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "phase_10"))
import chartlib as C  # noqa: E402
from v2_common import rel, write_json  # noqa: E402
sys.path.insert(0, HERE)
from t1_plateau import cfg_hash  # noqa: E402

A2 = "results/phase_10b/amendment_2"
ORDER = ["C3", "C3p", "C4", "C4p"]
LBL = {"C3": "C3 — 10 µs", "C3p": "C3′ — 1 ms  (unseen)",
       "C4": "C4 — 60 s coarse (two-scale)", "C4p": "C4′ — 100 ms  (unseen)"}
SINGLE = ("C3", "C3p", "C4p")


def main() -> int:
    chash = cfg_hash()
    r = json.load(open(rel(f"{A2}/artifacts/t2_bias_consistency.json"), encoding="utf-8"))
    df = pd.read_parquet(rel(f"{A2}/artifacts/t1_knee_distributions.parquet"))
    per, br, t2, us = r["per_control"], r["delta_bic_brackets"], r["bias_consistency"], \
        r["usability_criteria"]
    nd = r["n_knee_draws"]

    # ---------------------------------------------------------------- chart 11
    fig = make_subplots(rows=2, cols=2, subplot_titles=[LBL[c] for c in ORDER],
                        vertical_spacing=0.19, horizontal_spacing=0.09)
    for i, nm in enumerate(ORDER):
        rr, cc = divmod(i, 2)
        rr, cc = rr + 1, cc + 1
        g = df[df["control"] == nm]
        v = g["bp_nearest_injected_s"].dropna().to_numpy()
        inj = per[nm]["injected_s"]
        s = per[nm]["nearest_to_injected"]
        vals, cnts = np.unique(v, return_counts=True)
        fig.add_trace(go.Bar(
            x=vals, y=cnts, marker_color=C.ARM_A, width=[x * 0.12 for x in vals],
            name="breakpoint estimate", showlegend=(i == 0),
            hovertemplate="breakpoint %{x:.4g} s<br>%{y} of " + str(nd) +
                          " draws<extra></extra>"), row=rr, col=cc)
        lo, hi = s["ci95_breakpoint_s"]
        fig.add_vrect(x0=lo, x1=hi, fillcolor=C.ARM_A, opacity=0.16, line_width=0, row=rr, col=cc)
        bp = br[nm]["delta_bic_le_2_breakpoints_s"]
        if bp:
            fig.add_vrect(x0=min(bp) * 0.985, x1=max(bp) * 1.015, fillcolor="#9270CA", opacity=0.22,
                          line=dict(color="#9270CA", width=1.2, dash="dot"), row=rr, col=cc)
        fig.add_vline(x=inj, line=dict(color="#C23531", width=2.4, dash="dash"), row=rr, col=cc)
        fig.update_xaxes(type="log", title_text="breakpoint estimate (s, log)" if rr == 2 else None,
                         row=rr, col=cc)
        fig.update_yaxes(title_text="draws" if cc == 1 else None, row=rr, col=cc)
    for nm, col, lab in (("x", C.ARM_A, "95% bootstrap interval"),
                         ("y", "#9270CA", "ΔBIC ≤ 2 bracket"),
                         ("z", "#C23531", "injected scale")):
        fig.add_trace(go.Scatter(x=[None], y=[None], mode="markers",
                                 marker=dict(color=col, size=10, symbol="square"),
                                 name=lab, showlegend=True))
    rowtxt = " · ".join(
        f"<b>{nm}</b> {per[nm]['nearest_to_injected']['bias_rungs_median']:+.3f} rungs, "
        f"width {per[nm]['nearest_to_injected']['spread_rungs_ci95_width']:.2f}" for nm in ORDER)
    C.finish(
        fig, "11 — How far does the knee move between draws?",
        "The BIC-selected breakpoint, refit independently on every draw. Red dashed line is the "
        "injected scale. Blue shading is the 95% bootstrap interval; purple is the ΔBIC ≤ 2 bracket "
        "on the base realization. Breakpoints can only land on ladder rungs, so the estimator is "
        "discrete and its distribution is a set of spikes.",
        C.caption(
            f"{nd} independent realizations per control, all simulated; no real event read",
            "continuous piecewise-linear fit, k=1..3, BIC-selected, ≥3 rungs per segment; "
            "33-rung ladder 2⁻²⁰…2¹² s; eligible rungs require ≥20 window pairs",
            chash,
            f"<b>The knee is precise and biased.</b> {rowtxt}.<br>"
            f"The 95% interval spans <b>0 or 1 rung</b> in every case, and the ΔBIC ≤ 2 bracket "
            "agrees — both say the estimator is stable. But the injected scale falls <b>outside</b> "
            f"that interval for <b>{us['row_2_coverage']['of'] - us['row_2_coverage']['observed']} of "
            f"{us['row_2_coverage']['of']}</b> controls, because the bias exceeds the spread.<br>"
            "<b>Reads:</b> an interval spanning several rungs would mean the knee cannot locate a "
            "scale. That is not what happened — it locates a scale sharply, and the scale it locates "
            "is not the injected one."),
        height=900, width=1500)
    m11 = C.write(fig, rel(f"{A2}/charts"), "11_knee_sampling_distribution")

    # ---------------------------------------------------------------- chart 12
    fig2 = go.Figure()
    for grp, names, col in (("single-scale", SINGLE, C.ARM_A),
                            ("multi-scale (coarse)", ("C4",), C.ARM_B)):
        ys = [LBL[n] for n in names]
        b = [per[n]["nearest_to_injected"]["bias_rungs_median"] for n in names]
        lo = [per[n]["nearest_to_injected"]["ci95_rungs"][0] for n in names]
        hi = [per[n]["nearest_to_injected"]["ci95_rungs"][1] for n in names]
        fig2.add_trace(go.Scatter(
            x=b, y=ys, mode="markers", marker=dict(color=col, size=13),
            error_x=dict(type="data", symmetric=False,
                         array=[h - x for h, x in zip(hi, b)],
                         arrayminus=[x - l for x, l in zip(b, lo)],
                         color=col, thickness=2.4, width=8),
            name=f"{grp} (n={len(names)})",
            hovertemplate="%{y}<br>bias %{x:+.3f} rungs<extra></extra>"))
    for key, col, lab, pos in (("single_scale", C.ARM_A, "common bias, single-scale", "top right"),
                               ("all_four", C.INK2, "common bias, all four", "bottom left")):
        v = t2[key]
        fig2.add_vrect(x0=v["common_bias_ci95"][0], x1=v["common_bias_ci95"][1],
                       fillcolor=col, opacity=0.16, line_width=0)
        fig2.add_vline(x=v["common_bias_rungs"], line=dict(color=col, width=1.8, dash="dot"),
                       annotation_text=f"{lab}: {v['common_bias_rungs']:+.3f}",
                       annotation_position=pos,
                       annotation=dict(font=dict(color=col, size=12)))
    fig2.add_vline(x=0.0, line=dict(color="#C23531", width=2.4, dash="dash"),
                   annotation_text="zero bias = injected scale recovered",
                   annotation_position="top left",
                   annotation=dict(font=dict(color="#C23531", size=12)))
    fig2.update_xaxes(title_text="bias in rungs (estimated breakpoint − injected scale, log₂)")
    ss, af = t2["single_scale"], t2["all_four"]
    C.finish(
        fig2, "12 — One bias, or several?",
        "Median bias per control with its 95% bootstrap interval. Vertical bands are the "
        "inverse-variance common-bias estimates. C4 is entered at its coarse 60 s scale, the "
        "transition its two-scale structure adds.",
        C.caption(
            f"{nd} draws per control; 4 controls; all simulated, no real event read",
            "Cochran's Q on the four median biases, inverse-variance weighted; standard errors "
            "floored at the estimator's own 1-rung quantisation because a fit that selects the same "
            "rung in every draw has a measured SE of exactly zero",
            chash,
            f"<b>Single-scale controls cluster:</b> common bias {ss['common_bias_rungs']:+.3f} rungs, "
            f"spread across controls {ss['bias_range_rungs']:.3f} rungs. "
            f"<b>C4's coarse scale sits {per['C4']['nearest_to_injected']['bias_rungs_median']:+.3f}</b>, "
            f"making the all-four range {af['bias_range_rungs']:.3f} rungs.<br>"
            f"Cochran's Q rejects a single common bias in every grouping (p = {af['p_homogeneity']:.3g} "
            "across all four). That test is <b>hypersensitive here</b> — the estimator is nearly "
            "deterministic, so its standard errors are near zero and any difference registers. The "
            "practically meaningful numbers are the ranges: <b>0.644 rungs within single-scale, 4.517 "
            "rungs once the multi-scale coarse transition is included.</b><br>"
            "<b>Reads:</b> non-overlapping intervals mean a calibration fitted on single-scale "
            "controls cannot transfer to a multi-scale cohort."),
        height=620, width=1440)
    m12 = C.write(fig2, rel(f"{A2}/charts"), "12_bias_consistency")
    write_json(rel(f"{A2}/artifacts/t1_t2_chart_manifest.json"),
               {"charts": [m11, m12], "config_hash": chash,
                "source": "research/phase_10b/a2_charts_11_12.py:main"})
    return 0 if (m11["kaleido_verified"] and m12["kaleido_verified"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
