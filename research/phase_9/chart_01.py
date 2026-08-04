"""
Chart 01 - are the extreme cross-session ratios corporate actions or real moves?

x = exp(r) on a log axis, ECDF over all defined pairs, rug of the flagged
points, vertical bands at integer k and 1/k, flag threshold marked.

Failure appearance (from the contract): flagged points spread smoothly with no
mass at the integer bands -> they are real moves and the flag is over-broad.
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from research.phase_9 import chart_common as K
from research.phase_9 import common as C

FLAGS = f"{C.ART}/t1_cross_session_flags.parquet"


def main():
    cfg = C.load_cfg()
    thr = cfg["ca_flag_log_threshold"]
    tol = cfg["ca_integer_tolerance"]
    kmin, kmax = cfg["integer_ratio_range"]
    j = json.load(open(f"{C.ART}/t1_ca_detector.json"))

    P = pd.read_parquet(FLAGS)
    n_tot = len(P)
    fl = P[P.flag_cross_session_extreme]
    n_fl = len(fl)
    n_int = int(fl["within_integer_tolerance"].sum())
    kstar = j["integer_diagnostic"]["band_resolution_limit"]["first_k_where_bands_touch"]

    fig = go.Figure()

    # Integer bands. Only the RESOLVABLE ones (k < kstar) are drawn as bands;
    # at k >= kstar the 3% bands touch and tile the axis, so drawing them
    # individually would paint a wash that reads as signal. That zone is shown
    # once as a hatched region and labelled for what it is.
    for k in range(kmin, min(kmax, kstar - 1) + 1):
        for val in (k, 1.0 / k):
            fig.add_vrect(x0=val * (1 - tol), x1=val * (1 + tol),
                          fillcolor=K.rgba(K.YELLOW, 0.45), line_width=0, layer="below")
    for lo, hi in ((kstar * (1 - tol), kmax * (1 + tol)),
                   (1.0 / (kmax * (1 + tol)), 1.0 / (kstar * (1 - tol)))):
        fig.add_vrect(x0=lo, x1=hi, fillcolor=K.rgba(K.INK2, 0.12), line_width=0, layer="below")

    # ECDF per session pair
    for i, pair in enumerate(C.PAIRS):
        s = P.loc[P.session_pair == pair, "ratio"].dropna().sort_values()
        if not len(s):
            continue
        y = np.arange(1, len(s) + 1) / len(s)
        fig.add_trace(go.Scatter(
            x=s.values, y=y, mode="lines", name=f"{pair} (n={len(s):,})",
            line=dict(color=K.CAT5[i], width=2),
            hovertemplate=f"{pair}<br>ratio %{{x:.4f}}<br>ECDF %{{y:.4f}}<extra></extra>"))

    # rug of flagged points
    rug, sub = K.subsample(fl["ratio"].values)
    fig.add_trace(go.Scatter(
        x=rug, y=np.full(len(rug), -0.045), mode="markers",
        name=f"flagged (n={n_fl:,}{', rug sub-sampled' if sub else ''})",
        marker=dict(color=K.rgba(K.RED, 0.55), size=6, symbol="line-ns-open",
                    line=dict(width=1.2, color=K.RED)),
        hovertemplate="flagged ratio %{x:.4f}<extra></extra>"))

    # flag thresholds, labels staggered so they cannot collide
    for v, anch, yy in ((np.exp(-thr), "right", 0.60), (np.exp(thr), "left", 0.50)):
        fig.add_vline(x=v, line=dict(color=K.INK, width=2, dash="dash"))
        fig.add_annotation(x=np.log10(v), y=yy, xref="x", yref="paper",
                           text=f" flag threshold {v:.4f}× ", showarrow=False,
                           font=dict(size=10, color=K.INK), xanchor=anch,
                           bgcolor="rgba(255,255,255,0.82)")
    fig.add_annotation(x=np.log10(np.sqrt(kstar * kmax)), y=0.35, xref="x", yref="paper",
                       text=f"k ≥ {kstar}: bands touch,<br>membership automatic",
                       showarrow=False, font=dict(size=9, color=K.INK2),
                       bgcolor="rgba(255,255,255,0.82)")

    from research.phase_9.t1_ca_detector import band_null_coverage
    chance = band_null_coverage(fl["r"].abs(), thr, tol, kmin, kmax)
    title = (f"01 · Cross-session price ratios: flagged set vs integer bands<br>"
             f"<sub>{n_tot:,} defined pairs · {n_fl:,} flagged · {n_int:,} within {tol:.0%} of k or 1/k"
             f" = {n_int/n_fl:.1%} of flagged, vs {chance:.1%} expected by chance</sub>")
    cap = K.caption(
        "D1 n=15,763; pairs (T−1,T0)/(T0,T+1)/(T0,T+2)/(T0,T+3)",
        "both session closes present and > 0",
        f"flag = |log r| ≥ ln 1.8, magnitude only<br>"
        f"yellow = k or 1/k ± {tol:.0%}, k = {kmin}…{kstar-1} (resolvable)<br>"
        f"grey = k ≥ {kstar}, bands touch there and membership is automatic<br>"
        f"rug: {K.strip_note(n_fl)}")
    fig.update_xaxes(type="log", title_text="price ratio  exp(r) = p_later_close / p_earlier_close  (log scale)")
    fig.update_yaxes(title_text="ECDF", range=[-0.08, 1.05])
    K.base_layout(fig, title, cap, height=760, cap_y=-0.175, margin_b=250, margin_r=70)
    K.legend_inside(fig)
    K.write(fig, "01_cross_session_ratio_ecdf")


if __name__ == "__main__":
    main()
