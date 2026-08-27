"""
Phase 10d T3e -- chart 02, the void counterfactual. DESCRIPTION ONLY.

Left  : ECDF of the argmax-void parameter over the 168 distinct (event, kernel) cells,
        one line per kernel, with every candidate cutoff drawn as a reference line.
        The ECDF height where a cutoff line crosses IS the would-be declined share.
Right : the same as a bar read-off, per kernel per cutoff, with n on every bar.

Captioned "NO CUTOFF APPLIED" because that is the whole point of the chart.

Usage: .venv/Scripts/python.exe research/phase_10d/t3_chart.py
"""
from __future__ import annotations

import hashlib
import json
import os
import sys

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "research", "phase_10"))
import chartlib as C  # noqa: E402

ART = os.path.join(ROOT, "results", "phase_10d", "artifacts")
OUT = os.path.join(ROOT, "results", "phase_10d", "charts")
KEY = ["ticker", "event_date_canonical"]
KCOL = {2.0: C.ARM_A, 8.0: C.ARM_B, 32.0: C.SIDECAR}


def main() -> int:
    with open(os.path.join(ROOT, "config", "phase_10d.json"), encoding="utf-8") as f:
        conf = json.load(f)
    chash = hashlib.sha256(json.dumps(conf, sort_keys=True).encode()).hexdigest()[:8]

    cells = pd.read_parquet(os.path.join(ROOT, conf["upstream_10c"]["cells_artifact"]))
    distinct = cells.drop_duplicates(subset=KEY + ["kernel_min"])
    cf = pd.read_parquet(os.path.join(ART, "t3_void_counterfactual.parquet"))
    cf = cf[cf.scope == "distinct_event_kernel"]
    cutoffs = conf["counterfactual_cutoffs"]["values"]
    kernels = conf["upstream_10c"]["kernels_min"]

    fig = make_subplots(rows=1, cols=2, column_widths=[0.55, 0.45],
                        subplot_titles=[
                            "Void parameter at the argmax-void trough — ECDF (no cutoff applied)",
                            "Share that WOULD be declined at each candidate cutoff — reported, not applied"],
                        horizontal_spacing=0.09)

    for k in kernels:
        a = distinct[(distinct.kernel_min == k) & (distinct.label == "ok")].void
        fig.add_trace(C.ecdf_trace(a, f"kernel {k:g} min", KCOL[k],
                                   legendgroup=f"k{k}"), row=1, col=1)
    for c in cutoffs:
        fig.add_vline(x=c, line=dict(color=C.GRID, width=1.5, dash="dot"), row=1, col=1)
        fig.add_annotation(x=c, y=1.045, text=f"{c:g}", showarrow=False, xref="x1",
                           yref="y1", font=dict(size=10, color=C.INK2))
    fig.add_vline(x=0.70, line=dict(color=C.ROWCAP, width=2, dash="dash"), row=1, col=1)
    fig.add_annotation(x=0.70, y=0.06, text="0.70<br>v4's retired value", showarrow=False,
                       xref="x1", yref="y1", font=dict(size=10, color=C.ROWCAP),
                       xanchor="right")
    fig.update_xaxes(title_text="void parameter  V = 1 − f(trough) / √(f(peak_L)·f(peak_R))",
                     range=[0, 1.02], row=1, col=1)
    fig.update_yaxes(title_text="cumulative share of ok cells", range=[0, 1.09], row=1, col=1)

    for k in kernels:
        s = cf[cf.kernel_min == k].sort_values("cutoff")
        n = int(s.n_ok.iloc[0])
        fig.add_trace(go.Bar(
            x=[f"{c:g}" for c in s.cutoff], y=s.would_decline_share,
            name=f"kernel {k:g} min (n={n})", marker_color=KCOL[k],
            text=[f"{v:.0%}<br>{int(nn)}/{n}" for v, nn in
                  zip(s.would_decline_share, s.n_would_decline)],
            textposition="outside", textfont=dict(size=9),
            legendgroup=f"k{k}", showlegend=False,
            hovertemplate=(f"kernel {k:g} min<br>cutoff %{{x}}<br>would decline "
                           f"%{{y:.1%}}<extra></extra>")), row=1, col=2)
    fig.update_xaxes(title_text="candidate cutoff (none applied)", row=1, col=2)
    fig.update_yaxes(title_text="share of ok cells that would be declined",
                     range=[0, 0.78], tickformat=".0%", row=1, col=2)

    ic_lo, ic_hi = 0.0, 0.0
    with open(os.path.join(ART, "t3_summary.json"), encoding="utf-8") as f:
        summ = json.load(f)
    ic_lo, ic_hi = summ["T3c_decline_paths"]["insufficient_context_share_range"]

    cap = C.caption(
        sample=("168 distinct (event, kernel) cells from 56 dev-sample events × 3 kernels, "
                "results/phase_10c/artifacts/s1_t1_cells.parquet.<br>Void is a function of "
                "(event, kernel) only, so the 504-row artifact holds 168 distinct values — "
                "reporting it per variant would triple-count."),
        filters=("label = 'ok' only (cells that cleared 10c's data floor): n = 38 / 43 / 49 "
                 "at kernels 2 / 8 / 32 min."),
        chash=chash,
        extra=(
            "<b>NO CUTOFF APPLIED — anywhere, at any task, in this phase.</b> This chart is "
            "description. No value on it enters the computation path; doing so is "
            "escalation row 10d-R7.<br>"
            "<b>What 10c can and cannot decline:</b> it CANNOT decline on void magnitude — "
            "D13_void_parameter.threshold is null, marked deliberate<br>and permanent, so void "
            "ranks troughs and never gates. A decline path on PEAK COUNT does exist (fewer "
            "than two<br>Poisson-surviving peaks, or no valid trough pair) and it fired "
            "<b>0/504</b> on this cohort; 'unimodal' likewise appears 0 times.<br>"
            f"<b>Not the same quantity:</b> 10c's insufficient_context share runs "
            f"{ic_lo:.1%}–{ic_hi:.1%} across cells, but that is a DATA-COVERAGE verdict<br>(thin "
            "window vs. the per-event derived floor), not a bimodality verdict. It is not "
            "comparable to v4's 10/100 no_threshold<br>share and is not presented as such."))

    C.finish(fig, "Chart 02 — Void distribution and the counterfactual declined share",
             "Phase 10d T3 · what an applicability gate would cost, measured and not applied",
             cap, height=760, width=1340)
    meta = C.write(fig, OUT, "02_void_counterfactual")
    with open(os.path.join(ART, "t3_chart_manifest.json"), "w", encoding="utf-8") as f:
        json.dump({"task": "T3e", "charts": [meta]}, f, indent=2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
