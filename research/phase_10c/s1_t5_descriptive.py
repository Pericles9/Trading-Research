"""
Phase 10c Stage 1, T5 -- descriptive-only reporting. No gates, no pass/fail anywhere
in this file.

T5a  sub-burst count vs. T=0 print count, per cell. Spearman + log-log slope, scatter
     with raw points. A positive relationship is EXPECTED (Amendment 1 retired this as
     a gate, row 1) -- reported as context.
T5b  A2.7 silent-failure rate, per cell: share of 'ok' events where the tallest peak
     at or below the envelope boundary is other than the fastest. Carries the caveat
     that these figures are NOT comparable to Stage 0b's 30% (a different statistic,
     computed with no boundary in existence at the time).

Escalation row 5 requires a chart wherever a summary statistic is stated -- T5a gets
one (chart 11), even though the prompt's own T5 checklist names no chart number.

Usage: .venv/Scripts/python.exe research/phase_10c/s1_t5_descriptive.py
"""
from __future__ import annotations

import importlib.util as ilu
import os
import sys

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from scipy.stats import spearmanr

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


def main() -> int:
    cfg, chash = c10c.load_cfg(), c10c.cfg_hash()
    cells = pd.read_parquet(rel(f"{ART}/s1_t1_cells.parquet"))
    coh = pd.read_parquet(rel("results/phase_10/artifacts/t1_cohort_manifest.parquet"))
    ok = cells[cells.label == "ok"].merge(
        coh[["ticker", "event_date_canonical", "t0_print_count"]],
        on=["ticker", "event_date_canonical"], how="left")

    # -------------------------------------------------------- T5a
    t5a_rows = []
    for (v, k), g in ok.groupby(["threshold", "kernel_min"]):
        x, y = g.t0_print_count.to_numpy(), g.n_subbursts.to_numpy()
        m = (x > 0) & (y > 0)
        rho, p = spearmanr(x[m], y[m]) if m.sum() > 2 else (np.nan, np.nan)
        slope = float(np.polyfit(np.log(x[m]), np.log(y[m]), 1)[0]) if m.sum() > 2 else np.nan
        t5a_rows.append({"threshold": v, "kernel_min": k, "n": int(m.sum()),
                         "spearman_rho": float(rho), "p_value": float(p),
                         "log_log_slope": slope})
    t5a = pd.DataFrame(t5a_rows)
    t5a.to_parquet(rel(f"{ART}/s1_t5a_subburst_vs_printcount.parquet"), index=False)
    # T5a/T5b don't segment-stratify, and label=='ok' never depends on the variant --
    # so, like T2c's spacing, every (kernel) row is IDENTICAL across the 3 variants by
    # construction. Confirmed here rather than left to look like an unexplained coincidence.
    piv_check = t5a.pivot_table(index="kernel_min", columns="threshold", values="spearman_rho")
    identical_across_variants = bool(np.isclose(
        (piv_check.max(axis=1) - piv_check.min(axis=1)).max(), 0.0, atol=1e-12))

    # -------------------------------------------------------- T5b
    def silent_rate(g):
        elig = g.dropna(subset=["silent_selection"])
        if len(elig) == 0:
            return {"n": 0, "n_silent": 0, "rate": None}
        return {"n": int(len(elig)), "n_silent": int(elig.silent_selection.sum()),
                "rate": float(elig.silent_selection.mean())}
    t5b_rows = []
    for (v, k), g in ok.groupby(["threshold", "kernel_min"]):
        s = silent_rate(g)
        t5b_rows.append({"threshold": v, "kernel_min": k, **s})
    t5b = pd.DataFrame(t5b_rows)
    t5b.to_parquet(rel(f"{ART}/s1_t5b_silent_selection_rate.parquet"), index=False)

    out = {
        "phase": "10c", "stage": "1", "task": "T5_descriptive", "config_hash": chash,
        "T5a_subburst_vs_printcount": {
            "no_threshold_no_gate": True,
            "rows": t5a_rows,
            "identical_across_variants": identical_across_variants,
            "why_identical": ("T5a doesn't segment-stratify, and label=='ok' never depends on the "
                              "threshold variant (only the kernel does -- s1_t1_subbursts.py's "
                              "design note). So every (kernel) row here is the SAME population "
                              "and the SAME values under all 3 variants, confirmed by the check "
                              "above rather than left as an unexplained coincidence -- the same "
                              "reasoning as T2c's identical spacing result."),
            "reading": ("A positive Spearman/log-log slope is EXPECTED -- a bigger, longer, more "
                       "active event produces more sub-bursts under any reasonable definition "
                       "(Amendment 1 retired this as a gate). Reported as context."),
        },
        "T5b_A27_silent_failure_rate": {
            "rows": t5b_rows,
            "identical_across_variants": identical_across_variants,
            "caveat": ("These figures are NOT comparable to Stage 0b's 30% (T0b's silent-selection "
                      "check measured whether the LATER of the top-two-prominence peaks was "
                      "taller, with no envelope boundary in existence at all -- a different "
                      "statistic on a different mechanism). This measures, at the CHOSEN envelope "
                      "boundary, whether the tallest peak at or below it is the fastest-arriving "
                      "one; a different question, on a mechanism that didn't exist at Stage 0b."),
        },
        "source": "research/phase_10c/s1_t5_descriptive.py:main",
    }
    c10c.write_json(rel(f"{ART}/s1_t5_summary.json"), out)

    # -------------------------------------------------------- chart 11 (T5a needs one, row 5)
    fig = make_subplots(rows=1, cols=3, subplot_titles=[f"kernel = {k:g} min" for k in KERNELS])
    for ci, k in enumerate(KERNELS, 1):
        for v in VARIANTS:
            g = ok[(ok.kernel_min == k) & (ok.threshold == v)]
            fig.add_trace(go.Scatter(x=g.t0_print_count, y=g.n_subbursts, mode="markers",
                                     marker=dict(color=C.ARM_A if v == 1.25 else
                                                (C.ARM_B if v == 1.30 else C.SIDECAR), size=6,
                                                opacity=0.65),
                                     name=f"thr={v:g} (n={len(g)})", legendgroup=f"v{v}",
                                     showlegend=(ci == 1)), row=1, col=ci)
        fig.update_xaxes(type="log", title_text="T=0 print count", row=1, col=ci)
    fig.update_yaxes(type="log", title_text="sub-burst count", row=1, col=1)
    cap = C.caption("dev_v4_primary + dev_v4_sidecar, 56 events", "label=='ok' cells only", chash,
                    extra="No threshold, no pass/fail -- descriptive context only (Amendment 1 "
                    "retired this as a gate).")
    fig = C.finish(fig, "T5a -- Sub-burst count vs. T=0 print count",
                  "Raw points, all shown. Spearman/slope per cell in s1_t5_summary.json",
                  cap, height=640, width=1500)
    man = [C.write(fig, OUT, "s1_05_11_subburst_vs_printcount")]
    c10c.write_json(rel(f"{ART}/s1_t5_chart_manifest.json"), {"charts": man, "config_hash": chash})

    print("T5a Spearman rho / log-log slope by cell:")
    for r in t5a_rows:
        print(f"  thr={r['threshold']} kernel={r['kernel_min']}: n={r['n']} "
              f"rho={r['spearman_rho']:.3f} slope={r['log_log_slope']:.3f}")
    print("\nT5b silent-selection rate by cell:")
    for r in t5b_rows:
        print(f"  thr={r['threshold']} kernel={r['kernel_min']}: n={r['n']} "
              f"rate={r['rate']}")
    print(f"\n{len(man)} chart(s); kaleido {sum(m['kaleido_verified'] for m in man)}/{len(man)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
