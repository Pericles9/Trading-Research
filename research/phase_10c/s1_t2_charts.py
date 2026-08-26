"""
Phase 10c Stage 1, T2f -- charts 01-04 for the anchor-independent outputs.

01  threshold location (s), ECDF, faceted by kernel, colored by segment, one line
    style per variant (T2a)
02  sub-burst duration (s), ECDF, same layout (T2b)
03  spacing between consecutive sub-bursts (s), ECDF, faceted by kernel, one line
    per variant -- expected near-identical (T2c, T2e confirms)
04  void parameter at the chosen trough, ECDF, faceted by kernel, colored by segment,
    one line style per variant (T2d)

All ECDFs (Chart Contract: distribution, never centre-only). Log x-axis on 01-03
(multiplicative). n stated in every trace's legend label (chartlib.ecdf_trace).

Usage: .venv/Scripts/python.exe research/phase_10c/s1_t2_charts.py
"""
from __future__ import annotations

import importlib.util as ilu
import os
import sys

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "phase_10"))
import chartlib as C  # noqa: E402
from common import rel  # noqa: E402
_s = ilu.spec_from_file_location("c10c", os.path.join(HERE, "common.py"))
c10c = ilu.module_from_spec(_s); _s.loader.exec_module(c10c)

ART = "results/phase_10c/artifacts"
OUT = "results/phase_10c/charts"
KERNELS = [2.0, 8.0, 32.0]
VARIANTS = [1.25, 1.30, 1.35]
DASH = {1.25: "solid", 1.30: "dash", 1.35: "dot"}
SEG_COLOR = {"rth": C.ARM_A, "premarket": C.ARM_B, "evening": C.SIDECAR}


def facet_by_kernel_segment(df, value_col, title, subtitle, cap, name, log_x=True):
    segs = [s for s in ["rth", "premarket", "evening"] if s in df.segment.unique()]
    fig = make_subplots(rows=1, cols=len(KERNELS),
                        subplot_titles=[f"kernel = {k:g} min" for k in KERNELS])
    for ci, k in enumerate(KERNELS, 1):
        for seg in segs:
            for v in VARIANTS:
                sub = df[(df.kernel_min == k) & (df.segment == seg) & (df.threshold == v)]
                a = sub[value_col].dropna().to_numpy()
                if a.size == 0:
                    continue
                tr = C.ecdf_trace(a, f"{seg} thr={v:g}", SEG_COLOR.get(seg, C.INK2),
                                  dash=DASH[v], legendgroup=f"{seg}-{v}",
                                  showlegend=(ci == 1))
                fig.add_trace(tr, row=1, col=ci)
        if log_x:
            fig.update_xaxes(type="log", row=1, col=ci)
    fig.update_yaxes(title_text="cumulative share", row=1, col=1)
    fig = C.finish(fig, title, subtitle, cap, height=620, width=1500)
    return C.write(fig, OUT, name)


def facet_by_kernel_only(df, value_col, title, subtitle, cap, name, log_x=True):
    fig = make_subplots(rows=1, cols=len(KERNELS),
                        subplot_titles=[f"kernel = {k:g} min" for k in KERNELS])
    for ci, k in enumerate(KERNELS, 1):
        for v in VARIANTS:
            sub = df[(df.kernel_min == k) & (df.threshold == v)]
            a = sub[value_col].dropna().to_numpy()
            if a.size == 0:
                continue
            tr = C.ecdf_trace(a, f"thr={v:g}", C.ARM_A, dash=DASH[v],
                              legendgroup=f"thr-{v}", showlegend=(ci == 1))
            fig.add_trace(tr, row=1, col=ci)
        if log_x:
            fig.update_xaxes(type="log", row=1, col=ci)
    fig.update_yaxes(title_text="cumulative share", row=1, col=1)
    fig = C.finish(fig, title, subtitle, cap, height=620, width=1500)
    return C.write(fig, OUT, name)


def main() -> int:
    cfg, chash = c10c.load_cfg(), c10c.cfg_hash()
    cells = pd.read_parquet(rel(f"{ART}/s1_t1_cells.parquet"))
    sb = pd.read_parquet(rel(f"{ART}/s1_t1_subbursts.parquet"))
    ok = cells[cells.label == "ok"].copy()

    seg_map = cells[["ticker", "event_date_canonical", "threshold", "kernel_min",
                     "segment"]].drop_duplicates()
    sb_sorted = sb.sort_values(["ticker", "event_date_canonical", "kernel_min", "start_ns"])
    grp = sb_sorted.groupby(["ticker", "event_date_canonical", "kernel_min"])
    sb_sorted["prev_end_ns"] = grp.end_ns.shift(1)
    sb_sorted["spacing_s"] = (sb_sorted.start_ns - sb_sorted.prev_end_ns) / 1e9
    spacing = sb_sorted.dropna(subset=["spacing_s"]).copy()

    sb_v = sb.merge(seg_map, on=["ticker", "event_date_canonical", "kernel_min"], how="left")
    spacing_v = spacing.merge(seg_map, on=["ticker", "event_date_canonical", "kernel_min"],
                              how="left")

    sample = "dev_v4_primary + dev_v4_sidecar, 56 events"
    cap_base = C.caption(sample, "label=='ok' cells only; 3 variants x 3 kernels", chash)

    man = []
    man.append(facet_by_kernel_segment(
        ok, "threshold_seconds_median",
        "T2a -- Threshold location", "Chosen envelope-boundary trough, seconds, by segment and variant",
        cap_base + "<br>x: log scale. Line dash = threshold variant.", "s1_02_01_threshold_location"))
    man.append(facet_by_kernel_segment(
        sb_v, "duration_s",
        "T2b -- Sub-burst duration", "Per sub-burst, by segment and variant",
        cap_base + "<br>x: log scale (duration spans microseconds to session-scale). "
        "Line dash = threshold variant.", "s1_02_02_subburst_duration"))
    man.append(facet_by_kernel_only(
        spacing_v, "spacing_s",
        "T2c -- Spacing between consecutive sub-bursts", "Per kernel; not segment-split",
        cap_base + "<br>x: log scale. T2e confirms these are identical across variants by "
        "construction (spacing never depends on the anchor).", "s1_02_03_subburst_spacing"))
    man.append(facet_by_kernel_segment(
        ok, "void",
        "T2d -- Void parameter at the chosen trough", "By segment and variant. D13: ranks, never gates.",
        cap_base + "<br>x: linear (void in [0,1)). Line dash = threshold variant.",
        "s1_02_04_void_parameter", log_x=False))

    c10c.write_json(rel(f"{ART}/s1_t2_chart_manifest.json"),
                    {"charts": man, "config_hash": chash})
    print(f"{len(man)} charts; kaleido {sum(m['kaleido_verified'] for m in man)}/{len(man)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
