"""
Phase 10c Stage 1, T3e -- charts 05-07 for the anchor-relative outputs.

05  sub-burst position relative to detection (T3a)
06  near-anchor print density (T3b)
07  first vs. largest-by-move-share sub-burst timing since detection (T3c)

Every caption below carries ANCHOR_DELTA_CAPTION (escalation row 7).

Usage: .venv/Scripts/python.exe research/phase_10c/s1_t3_charts.py
"""
from __future__ import annotations

import importlib.util as ilu
import os
import sys

import numpy as np
import pandas as pd
from plotly.subplots import make_subplots

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "phase_10"))
import chartlib as C  # noqa: E402
from common import rel  # noqa: E402
_s = ilu.spec_from_file_location("c10c", os.path.join(HERE, "common.py"))
c10c = ilu.module_from_spec(_s); _s.loader.exec_module(c10c)
_s3 = ilu.spec_from_file_location("s1t3", os.path.join(HERE, "s1_t3_anchor_relative.py"))
s1t3 = ilu.module_from_spec(_s3); _s3.loader.exec_module(s1t3)

ART = "results/phase_10c/artifacts"
OUT = "results/phase_10c/charts"
KERNELS = [2.0, 8.0, 32.0]
VARIANTS = [1.25, 1.30, 1.35]
DASH = {1.25: "solid", 1.30: "dash", 1.35: "dot"}
SEG_COLOR = {"rth": C.ARM_A, "premarket": C.ARM_B, "evening": C.SIDECAR}


def main() -> int:
    cfg, chash = c10c.load_cfg(), c10c.cfg_hash()
    sb_v = pd.read_parquet(rel(f"{ART}/s1_t3a_subburst_position.parquet"))
    t3b = pd.read_parquet(rel(f"{ART}/s1_t3b_near_anchor_density.parquet"))
    first_df = pd.read_parquet(rel(f"{ART}/s1_t3c_first_subburst.parquet"))
    largest_df = pd.read_parquet(rel(f"{ART}/s1_t3c_largest_subburst.parquet"))
    import json
    t3c_summary = json.load(open(rel(f"{ART}/s1_t3c_summary.json"), encoding="utf-8"))
    first_is_largest = t3c_summary["share_where_first_is_also_largest"]

    cap = C.caption("dev_v4_primary + dev_v4_sidecar, 56 events", "sub-bursts with a valid anchor",
                    chash, extra=s1t3.ANCHOR_DELTA_CAPTION)
    man = []

    # ---- 05 T3a position vs detection
    segs = [s for s in ["rth", "premarket", "evening"] if s in sb_v.segment.unique()]
    fig = make_subplots(rows=1, cols=3, subplot_titles=[f"kernel = {k:g} min" for k in KERNELS])
    for ci, k in enumerate(KERNELS, 1):
        for seg in segs:
            for v in VARIANTS:
                a = sb_v[(sb_v.kernel_min == k) & (sb_v.segment == seg)
                        & (sb_v.threshold == v)].t_from_detection_s.dropna().to_numpy()
                if a.size == 0:
                    continue
                fig.add_trace(C.ecdf_trace(a, f"{seg} thr={v:g}", SEG_COLOR.get(seg, C.INK2),
                                           dash=DASH[v], legendgroup=f"{seg}-{v}",
                                           showlegend=(ci == 1)), row=1, col=ci)
        fig.add_vline(x=0, line=dict(color=C.INK2, width=1, dash="dot"), row=1, col=ci)
    fig.update_yaxes(title_text="cumulative share", row=1, col=1)
    fig.update_xaxes(title_text="seconds from detection")
    fig = C.finish(fig, "T3a -- Sub-burst position relative to detection",
                   "Signed seconds from that variant's anchor; 0 = detection", cap,
                   height=640, width=1500)
    man.append(C.write(fig, OUT, "s1_03_05_position_vs_detection"))

    # ---- 06 T3b near-anchor density
    fig = make_subplots(rows=1, cols=3, subplot_titles=[f"kernel = {k:g} min" for k in KERNELS])
    for ci, k in enumerate(KERNELS, 1):
        for seg in segs:
            for v in VARIANTS:
                a = t3b[(t3b.kernel_min == k) & (t3b.segment == seg)
                       & (t3b.threshold == v)].prints_per_min.dropna().to_numpy()
                if a.size == 0:
                    continue
                fig.add_trace(C.ecdf_trace(a, f"{seg} thr={v:g}", SEG_COLOR.get(seg, C.INK2),
                                           dash=DASH[v], legendgroup=f"{seg}-{v}",
                                           showlegend=(ci == 1)), row=1, col=ci)
        fig.update_xaxes(type="log", row=1, col=ci)
    fig.update_yaxes(title_text="cumulative share", row=1, col=1)
    fig = C.finish(fig, "T3b -- Near-anchor print density",
                   "D1-aggregated prints within +/- kernel/2 min of the anchor, per minute", cap,
                   height=640, width=1500)
    man.append(C.write(fig, OUT, "s1_03_06_near_anchor_density"))

    # ---- 07 T3c first vs largest timing since detection
    fig = make_subplots(rows=1, cols=3, subplot_titles=[f"kernel = {k:g} min" for k in KERNELS])
    for ci, k in enumerate(KERNELS, 1):
        for v in VARIANTS:
            af = first_df[(first_df.kernel_min == k)
                         & (first_df.threshold == v)].t_from_detection_s.dropna().to_numpy()
            al = largest_df[(largest_df.kernel_min == k)
                            & (largest_df.threshold == v)].t_from_detection_s.dropna().to_numpy()
            if af.size:
                fig.add_trace(C.ecdf_trace(af, f"first thr={v:g}", C.ARM_A, dash=DASH[v],
                                           legendgroup=f"first-{v}", showlegend=(ci == 1)),
                              row=1, col=ci)
            if al.size:
                fig.add_trace(C.ecdf_trace(al, f"largest thr={v:g}", C.ARM_B, dash=DASH[v],
                                           legendgroup=f"largest-{v}", showlegend=(ci == 1)),
                              row=1, col=ci)
        fig.update_xaxes(type="log", row=1, col=ci)
    fig.update_yaxes(title_text="cumulative share", row=1, col=1)
    share_txt = "; ".join(f"thr={v:g}: {first_is_largest[str(v)]:.1%} first-is-also-largest"
                         for v in VARIANTS)
    fig = C.finish(fig, "T3c -- First vs. largest-by-move-share sub-burst since detection",
                   "Timing (seconds from detection) of each event's first sub-burst and its "
                   "largest by price-move share", cap + f"<br><b>First is also largest:</b> {share_txt}",
                   height=640, width=1500)
    man.append(C.write(fig, OUT, "s1_03_07_first_vs_largest"))

    c10c.write_json(rel(f"{ART}/s1_t3_chart_manifest.json"), {"charts": man, "config_hash": chash})
    print(f"{len(man)} charts; kaleido {sum(m['kaleido_verified'] for m in man)}/{len(man)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
