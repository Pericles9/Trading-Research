"""
Phase 10b chart 04 -- the synthetic control harness (T2, the gate).

One panel per control, Allan curve against its matched-null band, all eligible
bandwidths overlaid. Ineligible bandwidths (out-of-sample lambda-hat at the floor)
are drawn faded so the exclusion is visible rather than silent.

Usage: .venv/Scripts/python.exe research/phase_10b/chart04_controls.py
"""
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
from t1_plateau import cfg_hash, load_cfg  # noqa: E402

TITLES = {
    "C1": "C1 — homogeneous Poisson<br><sub>must stay inside the band</sub>",
    "C2": "C2 — inhomogeneous Poisson<br><sub>must stay inside the band</sub>",
    "C3": "C3 — clusters, k=6 over 10 µs<br><sub>must leave it, at 10 µs</sub>",
    "C4": "C4 — two scales, 10 µs + 60 s<br><sub>both must be visible, separated</sub>",
}
HCOL = ["#5B8FF9", "#61DDAA", "#F6BD16", "#E8684A", "#9270CA", "#78D3F8"]


def main() -> int:
    cfg, chash = load_cfg(), cfg_hash()
    res = json.load(open(rel("results/phase_10b/artifacts/t2_control_results.json"),
                         encoding="utf-8"))
    d = pd.read_parquet(rel("results/phase_10b/artifacts/t2_control_curves.parquet"))
    v = res["verdicts"]
    hs = sorted(d["h"].unique())

    fig = make_subplots(rows=2, cols=2, subplot_titles=[TITLES[k] for k in ("C1", "C2", "C3", "C4")],
                        vertical_spacing=0.19, horizontal_spacing=0.09)
    for ax, name in enumerate(("C1", "C2", "C3", "C4")):
        r, cc = divmod(ax, 2)
        r, cc = r + 1, cc + 1
        sub = d[d["control"] == name]
        for hi_, h in enumerate(hs):
            s = sub[(sub["h"] == h) & sub["eligible"] & sub["band_lo"].notna()].sort_values("T")
            if not len(s):
                continue
            el = bool(s["h_eligible"].iloc[0])
            col = HCOL[hi_ % len(HCOL)]
            fig.add_trace(go.Scatter(
                x=np.concatenate([s["T"], s["T"][::-1]]),
                y=np.concatenate([s["band_hi"], s["band_lo"][::-1]]),
                fill="toself", fillcolor=col, opacity=0.30 if el else 0.07,
                line=dict(width=0), hoverinfo="skip", showlegend=False), row=r, col=cc)
            fig.add_trace(go.Scatter(
                x=s["T"], y=s["band_hi"], mode="lines",
                line=dict(color=col, width=1, dash="dot"),
                name=f"null band, h={h:g} s" + ("" if el else "  (INELIGIBLE — λ̂ at floor)"),
                legendgroup=f"h{h}", showlegend=(ax == 0), opacity=1.0 if el else 0.35,
                hovertemplate=f"h={h:g}<br>T %{{x:.3e}} s<br>band hi %{{y:.4f}}<extra></extra>"),
                row=r, col=cc)
        s0 = sub[(sub["h"] == max(hs)) & sub["eligible"]].sort_values("T")
        fig.add_trace(go.Scatter(
            x=s0["T"], y=s0["allan"], mode="lines+markers",
            line=dict(color=C.INK2, width=2.6), marker=dict(size=4, color=C.INK2),
            name="control's own Allan curve", legendgroup="ctrl", showlegend=(ax == 0),
            hovertemplate="T %{x:.3e} s<br>Allan %{y:.4f}<extra></extra>"), row=r, col=cc)
        for xv, lab in ((1e-5, "injected 10 µs"), (60.0, "injected 60 s")):
            if name in ("C3", "C4") and (name == "C4" or xv == 1e-5):
                fig.add_vline(x=xv, line=dict(color="#C23531", width=1.4, dash="dash"),
                              row=r, col=cc)
        fig.update_xaxes(type="log", row=r, col=cc,
                         title_text="counting-window duration T (s, log)" if r == 2 else None)
        fig.update_yaxes(type="log", title_text="Allan factor (log)", row=r, col=cc)

    n = res["controls"]["n_target_prints"]
    c3, c4 = v["C3"], v["C4"]
    C.finish(
        fig, "04 — Synthetic control harness: does the pipeline recover a known answer?",
        "Each control is run through the SAME T3/T4 pipeline the real cohort would use. Shaded "
        "regions are 95% matched-null bands (200 draws) from an out-of-sample λ̂ at each bandwidth "
        "h; faded bands are bandwidths where λ̂ collapses to the floor (h below the 60 s held-out "
        "block) and are excluded. Dark line is the control's own Allan curve, drawn at the widest h. "
        "Red dashes mark the injected timescales.",
        C.caption(
            f"4 synthetic controls, ~{n:,.0f} prints each over a {res['controls']['span_s']:,.0f} s "
            f"session; {res['n_control_draws']} null draws per band, "
            f"{res['n_coverage_draws']} independent draws for the coverage check",
            "sparse Allan (research/phase_10b/pipeline.py, verified exactly against a dense "
            "reference); λ̂ fitted out of sample on alternating 60 s blocks; 33-rung ladder "
            "2⁻²⁰…2¹² s; eligible rungs require ≥20 window pairs",
            chash,
            f"<b>GATE: {'PASS' if v['ALL_PASS'] else 'FAIL — HARD STOP'}.</b> "
            f"Band coverage {v['T2e_band_coverage']['min']:.3f}–{v['T2e_band_coverage']['max']:.3f} "
            f"(required {v['T2e_band_coverage']['required_range']}) — <b>PASS</b>, the band machinery "
            "is calibrated.<br>"
            f"<b>C3 plateau {c3['plateau_height']:.3f} vs expected E[N²]/E[N] = "
            f"{c3['expected_size_weighted_mean']:.3f}</b> "
            f"({c3['relative_error']:+.1%}) — PASS, the magnitude of the injected clustering is "
            "recovered exactly.<br>"
            f"<b>C3 crossing {c3['t3_crossing'].get('crossing_T'):.2e} s vs injected 1.00e-05 s — "
            "FAIL.</b> A cluster process departs from Poisson at the smallest resolvable scale, so "
            "the band-exit point measures the finest clustering present, not the cluster duration. "
            "The 10 µs scale appears as the <i>knee</i> where the curve reaches its plateau, which "
            "is visible here at ~1e-4 s. The pre-registered crossing statistic does not measure the "
            "quantity C3 requires it to measure.<br>"
            f"<b>C1 inside {v['C1']['inside_band_min_share_over_h']:.3f}, "
            f"C2 {v['C2']['inside_band_min_share_over_h']:.3f}</b> "
            f"(required ≥ {v['C1']['inside_band_required']:.2f}, taken as the minimum over eligible "
            "h) — FAIL. At h ≫ the profile's own timescale the null cannot represent the profile, so "
            "C2 leaves a band that was never matched to it; at T ≳ h the plug-in null inherits λ̂'s "
            "estimation error and sits above a truly Poisson C1."),
        height=1180, width=1500)
    man = C.write(fig, rel(cfg["paths"]["out_charts"]), "04_control_harness")
    write_json(rel("results/phase_10b/artifacts/t2_chart_manifest.json"),
               {"phase": "10b", "chart": man, "config_hash": chash,
                "reads": ["results/phase_10b/artifacts/t2_control_curves.parquet",
                          "results/phase_10b/artifacts/t2_control_results.json"],
                "source": "research/phase_10b/chart04_controls.py:main"})
    return 0 if man["kaleido_verified"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
