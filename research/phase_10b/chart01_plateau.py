"""
Phase 10b chart 01 -- does the sub-knee Allan plateau height track sweep size?

Reads t1_sweep_runs.parquet. This is the ONLY task that reads it (scope fence,
config.t1_fragmentation.sweep_run_scope).

Usage: .venv/Scripts/python.exe research/phase_10b/chart01_plateau.py
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from scipy import stats as sps

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "phase_10"))
import chartlib as C  # noqa: E402
from v2_common import COHORT_KEY, rel, write_json  # noqa: E402
sys.path.insert(0, HERE)
from t1_plateau import cfg_hash, load_cfg  # noqa: E402

SC = {"premarket": C.ARM_B, "rth": C.ARM_A}


def main() -> int:
    cfg = load_cfg()
    chash = cfg_hash()
    t1c = cfg["t1_fragmentation"]
    gp = t1c["sweep_gap_s"]["primary"]
    lo_e, hi_e = t1c["plateau_rungs_exponents"]
    never = cfg["cohort"]["never_pooled"]
    fit = json.load(open(rel("results/phase_10b/artifacts/t1_plateau_fit.json"), encoding="utf-8"))

    runs = pd.read_parquet(rel("results/phase_10b/artifacts/t1_sweep_runs.parquet"))
    runs["event_date_canonical"] = runs["event_date_canonical"].astype(str)
    cur = pd.read_parquet(rel(cfg["paths"]["v3_allan_curves"]))
    cur["event_date_canonical"] = cur["event_date_canonical"].astype(str)
    pl = cur[(cur["observable"] == "print_rate") & (cur["T"] >= 2.0 ** lo_e)
             & (cur["T"] <= 2.0 ** hi_e) & (cur["allan"] > 0)].copy()
    pl["log_allan"] = np.log(pl["allan"])
    plat = pl.groupby(COHORT_KEY + ["segment", "cohort_group"])["log_allan"].agg(
        h="mean", iqr=lambda x: float(np.percentile(x, 75) - np.percentile(x, 25))).reset_index()
    plat["is_flat"] = plat["iqr"] <= t1c["plateau_flatness_max"]
    m = plat.merge(runs[runs["sweep_gap_s"] == gp], on=COHORT_KEY + ["cohort_group"], how="left")
    m = m[~m["cohort_group"].isin(never)]

    fig = make_subplots(
        rows=1, cols=2, horizontal_spacing=0.09,
        subplot_titles=["vs SIZE-WEIGHTED mean run size E[N²]/E[N] — the prediction",
                        "vs PLAIN mean run size E[N] — shown for contrast"])
    for ci, (xcol, key) in enumerate((("size_weighted_mean_run_size", "regression_vs_size_weighted"),
                                      ("mean_run_size", "regression_vs_plain_mean")), 1):
        for seg, col in SC.items():
            s = m[(m["segment"] == seg) & m["is_flat"] & (m[xcol] > 0)]
            x = m[(m["segment"] == seg) & (~m["is_flat"]) & (m[xcol] > 0)]
            if len(x):
                fig.add_trace(go.Scatter(
                    x=x[xcol], y=np.exp(x["h"]), mode="markers",
                    marker=dict(color=col, size=8, opacity=0.30, symbol="x"),
                    name=f"{seg} — excluded, not flat (n={len(x)})", showlegend=(ci == 1),
                    customdata=x[COHORT_KEY + ["iqr"]].to_numpy(),
                    hovertemplate="%{customdata[0]} %{customdata[1]}<br>x %{x:,.3f}"
                                  "<br>plateau %{y:,.3f}<br>log-IQR %{customdata[3]:.3f}<extra></extra>"),
                    row=1, col=ci)
            if not len(s):
                continue
            fig.add_trace(go.Scatter(
                x=s[xcol], y=np.exp(s["h"]), mode="markers",
                marker=dict(color=col, size=9, opacity=0.8, line=dict(color=C.SURFACE, width=1)),
                name=f"{seg} — flat (n={len(s)})", showlegend=(ci == 1),
                customdata=s[COHORT_KEY].to_numpy(),
                hovertemplate="%{customdata[0]} %{customdata[1]}<br>x %{x:,.3f}"
                              "<br>plateau %{y:,.3f}<extra></extra>"), row=1, col=ci)
            r = fit["by_segment"][seg][key]
            if r["slope"] is not None:
                xs = np.linspace(np.log(s[xcol].min()), np.log(s[xcol].max()), 20)
                fig.add_trace(go.Scatter(
                    x=np.exp(xs), y=np.exp(r["intercept"] + r["slope"] * xs), mode="lines",
                    line=dict(color=col, width=2.5),
                    name=f"{seg} fit: slope {r['slope']:+.3f} "
                         f"[{r['ci95'][0]:+.3f}, {r['ci95'][1]:+.3f}]",
                    showlegend=True, hoverinfo="skip"), row=1, col=ci)
        # slope-1 reference through the pooled centroid
        s_all = m[m["is_flat"] & (m[xcol] > 0)]
        if len(s_all):
            gx = float(np.exp(np.log(s_all[xcol]).mean()))
            gy = float(np.exp(s_all["h"].mean()))
            xs = np.array([s_all[xcol].min(), s_all[xcol].max()], dtype=float)
            fig.add_trace(go.Scatter(x=xs, y=gy * (xs / gx), mode="lines",
                                     line=dict(color=C.INK2, width=1.6, dash="dash"),
                                     name="slope = 1 reference", showlegend=(ci == 1),
                                     hoverinfo="skip"), row=1, col=ci)
        fig.update_xaxes(type="log", title_text=("size-weighted mean run size E[N²]/E[N] (log)"
                                                 if ci == 1 else "plain mean run size E[N] (log)"),
                         row=1, col=ci)
        fig.update_yaxes(type="log", title_text="Allan plateau height (log)", row=1, col=ci)

    b_pm, b_rt = fit["by_segment"]["premarket"], fit["by_segment"]["rth"]
    C.finish(
        fig, "01 — Does the sub-knee Allan plateau height track sweep size?",
        f"Plateau = mean of log Allan over rungs 2^{lo_e} s to 2^{hi_e} s "
        f"({2.0**lo_e:g}–{2.0**hi_e:g} s), print observable. Sweep runs = maximal runs of prints with "
        f"inter-print gap ≤ {gp:g} s. Both axes log; the dashed line is slope 1 through the centroid. "
        "Non-flat events are plotted as faded crosses and excluded from every fit.",
        C.caption(
            f"pooled analysis cohort; premarket n={b_pm['n_events']} ({b_pm['n_flat']} flat, "
            f"{b_pm['n_excluded_not_flat']} excluded), rth n={b_rt['n_events']} "
            f"({b_rt['n_flat']} flat, {b_rt['n_excluded_not_flat']} excluded)",
            f"v3 per-event Allan curves, print observable; sweep gap {gp:g} s; "
            f"non-flat = log-IQR > {t1c['plateau_flatness_max']}; row-cap and sidecar never pooled",
            chash,
            "<b>Size-weighted:</b> premarket slope "
            f"{b_pm['regression_vs_size_weighted']['slope']:+.4f} "
            f"CI [{b_pm['regression_vs_size_weighted']['ci95'][0]:+.3f}, "
            f"{b_pm['regression_vs_size_weighted']['ci95'][1]:+.3f}], r²="
            f"{b_pm['regression_vs_size_weighted']['r2']:.3f} · rth "
            f"{b_rt['regression_vs_size_weighted']['slope']:+.4f} "
            f"CI [{b_rt['regression_vs_size_weighted']['ci95'][0]:+.3f}, "
            f"{b_rt['regression_vs_size_weighted']['ci95'][1]:+.3f}], r²="
            f"{b_rt['regression_vs_size_weighted']['r2']:.3f} — <b>slope 1 inside the CI for both</b>."
            "<br><b>Plain mean:</b> slopes "
            f"{b_pm['regression_vs_plain_mean']['slope']:+.3f} and "
            f"{b_rt['regression_vs_plain_mean']['slope']:+.3f} — slope 1 far outside both CIs, which "
            "is the spurious rejection testing against E[N] alone produces."
            "<br><b>Reads:</b> flat scatter, or slope ≠ 1 against BOTH x-definitions, would mean the "
            "plateau is not fragmentation and T3's sub-knee region is unexplained."),
        height=780, width=1400)
    man = C.write(fig, rel(cfg["paths"]["out_charts"]), "01_plateau_vs_sweep_size")
    write_json(rel("results/phase_10b/artifacts/t1_chart_manifest.json"),
               {"phase": "10b", "chart": man, "config_hash": chash,
                "reads": ["results/phase_10b/artifacts/t1_sweep_runs.parquet",
                          cfg["paths"]["v3_allan_curves"]],
                "scope_fence_note": "This is the only task in the phase that reads t1_sweep_runs.parquet.",
                "source": "research/phase_10b/chart01_plateau.py:main"})
    return 0 if man["kaleido_verified"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
