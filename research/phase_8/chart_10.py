"""
Phase 8 charts 10 + 10b (A10.2a-ii, A10.3d).
10 : ECDF of det_anchor time-of-day, one curve per session segment, era as
     line style. n per segment.
10b: distribution of tick max-move ratio (day_high_ext/tick_close_t_minus_1_rth)
     for the 394 det_undefined events, threshold line at 1.30 - the A10.3
     report-only diagnostic (clustered near threshold vs scattered).
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd
import plotly.graph_objects as go

from research.phase_8.chart_common import BLUE, AQUA, ORANGE, RED, INK, INK2, caption, write, base_layout

ANCH = "results/phase_8/artifacts/a102_detection_anchors.parquet"
META = "results/phase_8/artifacts/a102_detection_summary.json"
SEGCOL = {"premarket": BLUE, "rth": AQUA, "post": ORANGE}
ERASTYLE = {"era_2020_2021": "solid", "era_2022_2024": "dash"}


def chart_10(ev, meta):
    fig = go.Figure()
    d = ev[~ev.det_undefined].copy()
    d["et_hour"] = (240 + d["det_minute"]) / 60.0
    for seg in ["premarket", "rth", "post"]:
        for era, dash in ERASTYLE.items():
            s = d[(d.det_segment == seg) & (d.era == era)]["et_hour"].to_numpy()
            if len(s) == 0:
                continue
            xs = np.sort(s); ys = np.arange(1, len(xs) + 1) / len(xs)
            fig.add_trace(go.Scatter(x=xs, y=ys, mode="lines",
                                     line=dict(color=SEGCOL[seg], width=2, dash=dash),
                                     name=f"{seg} · {era[-4:]} (n={len(xs):,})"))
    for h, lab in [(9.5, "RTH open"), (16, "RTH close")]:
        fig.add_vline(x=h, line=dict(color=INK2, width=1, dash="dot"))
        fig.add_annotation(x=h, y=1.02, yref="paper", text=lab, showarrow=False, font=dict(size=9, color=INK2))
    sc = meta["detection_segment_counts"]
    fig.update_xaxes(title_text="det_anchor time-of-day (ET hour)", range=[4, 20], dtick=2)
    fig.update_yaxes(title_text="cumulative fraction (within segment)", range=[0, 1.02])
    cap = caption(sample=f"detection universe n={meta['detection_universe_n']:,} (det_undefined 394 excluded)",
                  filters=f"segments premarket {sc.get('premarket',0):,} / rth {sc.get('rth',0):,} / post {sc.get('post',0):,}; crossing on bar high, 1.30x")
    base_layout(fig, "10 · Detection-time distribution by session segment", cap, height=560)
    fig.update_layout(legend=dict(font=dict(size=9)))
    write(fig, "10_detection_time_distribution")


def chart_10b(ev, meta):
    und = ev[ev.det_undefined].copy()
    und["ratio"] = und["day_high_ext"] / und["tick_close_t_minus_1_rth"]
    r = und["ratio"].dropna().to_numpy()
    xs = np.sort(r); ys = np.arange(1, len(xs) + 1) / len(xs)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=xs, y=ys, mode="lines+markers", line=dict(color=BLUE, width=2),
                             marker=dict(size=3, color=BLUE), name=f"det_undefined anchor-present (n={len(xs)})"))
    fig.add_vline(x=1.30, line=dict(color=RED, width=1.5, dash="dash"))
    fig.add_annotation(x=1.30, y=0.05, text="1.30× threshold", showarrow=False,
                       font=dict(size=10, color=RED), textangle=-90, xanchor="left")
    d = meta["a10_3_diagnostic_394"]
    fig.update_xaxes(title_text="tick max move ratio  (day_high_ext / tick_close_t_minus_1_rth)")
    fig.update_yaxes(title_text="cumulative fraction of the 394", range=[0, 1.02])
    cap = caption(
        sample=f"det_undefined n=394 (anchor-present {d['n_anchor_present']}, no-anchor {d['n_no_anchor_has_t_minus_1_rth_false']})",
        filters=(f"median ratio {d['tick_maxmove_ratio_dist_anchor_present']['median']:.3f}; "
                 f"{d['clustered_near_threshold_share_of_anchor_present']:.1%} in [1.20,1.30) - clustered near threshold; "
                 f"split-adjacent proxy (ratio<1.0) n={d['split_adjacent_proxy_ratio_lt_1p0']}. A10.3 report-only"),
    )
    base_layout(fig, "10b · The 394 det_undefined: tick max-move vs the 1.30× threshold", cap, height=540)
    write(fig, "10b_det_undefined_maxmove")


def main():
    ev = pd.read_parquet(ANCH)
    with open(META) as f:
        meta = json.load(f)
    chart_10(ev, meta)
    chart_10b(ev, meta)


if __name__ == "__main__":
    main()
