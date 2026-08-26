"""
Phase 10c Stage 1, T4d -- charts 08-10 for the cross-kernel interpretation.

08  threshold location vs. kernel width, per event (T4a)
09  void parameter vs. kernel width, per event (T4b)
10  heterogeneity: best-separated kernel vs. event size / detection price decile /
    segment (T4c)

No combining rule anywhere -- these are per-event line plots read side by side, not
pooled into a single per-event number.

Usage: .venv/Scripts/python.exe research/phase_10c/s1_t4_charts.py
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
SEG_COLOR = {"rth": C.ARM_A, "premarket": C.ARM_B, "evening": C.SIDECAR, None: C.INK2}


def main() -> int:
    cfg, chash = c10c.load_cfg(), c10c.cfg_hash()
    pek = pd.read_parquet(rel(f"{ART}/s1_t4_per_event_kernel.parquet"))
    best = pd.read_parquet(rel(f"{ART}/s1_t4b_best_kernel.parquet"))
    ok = pek[pek.label == "ok"]

    cap = C.caption("dev_v4_primary + dev_v4_sidecar, 56 events", "label=='ok' kernels only; "
                    "one line per event, variant-independent by construction", chash)
    man = []

    # ---- 08 T4a threshold vs kernel, per event
    fig = go.Figure()
    for i, ((tk, ed), g) in enumerate(ok.groupby(["ticker", "event_date_canonical"])):
        g = g.sort_values("kernel_min")
        seg = g.segment.iloc[0]
        fig.add_trace(go.Scatter(
            x=g.kernel_min, y=g.threshold_seconds_median, mode="lines+markers",
            line=dict(color=SEG_COLOR.get(seg, C.INK2), width=1.2),
            marker=dict(size=5), opacity=0.55, showlegend=False,
            hovertemplate=f"{tk} {ed}<br>kernel=%{{x}} min<br>thr=%{{y:.4g}} s<extra></extra>"))
    for seg, col in [("rth", C.ARM_A), ("premarket", C.ARM_B), ("evening", C.SIDECAR)]:
        fig.add_trace(go.Scatter(x=[None], y=[None], mode="lines", name=seg,
                                 line=dict(color=col, width=2)))
    fig.update_xaxes(type="log", tickvals=KERNELS, title_text="kernel width (min)")
    fig.update_yaxes(type="log", title_text="threshold location (s)")
    fig = C.finish(fig, "T4a -- Threshold location vs. kernel width",
                  "Per-event lines. Flat = a real structural interval; slope ~1 = the threshold "
                  "scales with the local-median window (free-parameter form). Read is Cooper's.",
                  cap + "<br>Median per-event log-log slope: see s1_t4_summary.json (not "
                  "characterized here).", height=760, width=1100)
    man.append(C.write(fig, OUT, "s1_04_08_threshold_vs_kernel"))

    # ---- 09 T4b void vs kernel, per event
    fig = go.Figure()
    for (tk, ed), g in ok.groupby(["ticker", "event_date_canonical"]):
        g = g.sort_values("kernel_min")
        seg = g.segment.iloc[0]
        fig.add_trace(go.Scatter(
            x=g.kernel_min, y=g.void, mode="lines+markers",
            line=dict(color=SEG_COLOR.get(seg, C.INK2), width=1.2),
            marker=dict(size=5), opacity=0.55, showlegend=False,
            hovertemplate=f"{tk} {ed}<br>kernel=%{{x}} min<br>void=%{{y:.3f}}<extra></extra>"))
    for seg, col in [("rth", C.ARM_A), ("premarket", C.ARM_B), ("evening", C.SIDECAR)]:
        fig.add_trace(go.Scatter(x=[None], y=[None], mode="lines", name=seg,
                                 line=dict(color=col, width=2)))
    fig.update_xaxes(type="log", tickvals=KERNELS, title_text="kernel width (min)")
    fig.update_yaxes(title_text="void parameter (ranks only, D13 -- never gates)")
    fig = C.finish(fig, "T4b -- Void parameter strength by kernel",
                  "Per-event lines. Which kernel widths produce a clean split differs by event.",
                  cap, height=760, width=1100)
    man.append(C.write(fig, OUT, "s1_04_09_void_vs_kernel"))

    # ---- 10 T4c heterogeneity: best kernel vs size / price decile / segment
    fig = make_subplots(rows=1, cols=3, subplot_titles=[
        "best kernel vs. event size (n_intervals)", "best kernel vs. detection price decile",
        "best kernel by segment"])
    jitter = c10c  # reuse module import slot, no-op
    rng = np.random.default_rng(42)
    for k, col in zip(KERNELS, [C.ARM_A, C.ARM_B, C.SIDECAR]):
        sub = best[best.best_kernel_min == k]
        fig.add_trace(go.Scatter(x=sub.n_intervals, y=sub.best_kernel_min
                                 + rng.uniform(-0.15, 0.15, len(sub)) * sub.best_kernel_min,
                                 mode="markers", marker=dict(color=col, size=7),
                                 name=f"kernel={k:g}", legendgroup=f"k{k}",
                                 hovertemplate="n_intervals=%{x}<extra></extra>"), row=1, col=1)
        fig.add_trace(go.Scatter(x=sub.price_decile, y=sub.best_kernel_min
                                 + rng.uniform(-0.15, 0.15, len(sub)) * sub.best_kernel_min,
                                 mode="markers", marker=dict(color=col, size=7),
                                 name=f"kernel={k:g}", legendgroup=f"k{k}", showlegend=False,
                                 hovertemplate="price_decile=%{x}<extra></extra>"), row=1, col=2)
    fig.update_xaxes(type="log", title_text="n_intervals (event size)", row=1, col=1)
    fig.update_xaxes(title_text="detection price decile (0=cheapest)", row=1, col=2)
    fig.update_yaxes(type="log", tickvals=KERNELS, title_text="best kernel (min)", row=1, col=1)
    fig.update_yaxes(type="log", tickvals=KERNELS, row=1, col=2)

    by_seg = best.groupby(["segment", "best_kernel_min"], dropna=False).size().unstack(fill_value=0)
    for k, col in zip(KERNELS, [C.ARM_A, C.ARM_B, C.SIDECAR]):
        if k not in by_seg.columns:
            continue
        fig.add_trace(go.Bar(x=by_seg.index.astype(str), y=by_seg[k], name=f"kernel={k:g}",
                             marker_color=col, showlegend=False), row=1, col=3)
    fig.update_layout(barmode="stack")
    fig.update_yaxes(title_text="n events", row=1, col=3)

    cap10 = cap + (f"<br>Spearman best-kernel vs n_intervals and vs price decile: see "
                  "s1_t4_summary.json T4c_heterogeneity (neither significant at p<0.05 in this "
                  "dev sample -- reported, not treated as absence of an effect).")
    fig = C.finish(fig, "T4c -- Heterogeneity of the best-separated kernel",
                  "Jittered for visibility; underlying kernel value is exact (2/8/32 min)",
                  cap10, height=680, width=1560)
    man.append(C.write(fig, OUT, "s1_04_10_heterogeneity"))

    c10c.write_json(rel(f"{ART}/s1_t4_chart_manifest.json"), {"charts": man, "config_hash": chash})
    print(f"{len(man)} charts; kaleido {sum(m['kaleido_verified'] for m in man)}/{len(man)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
