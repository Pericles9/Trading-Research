"""
Phase 10b chart 04 (A10b.1 amended) -- the synthetic control harness, six controls.

2x3 facet. Per panel: the control's Allan curve, its matched-null band at every
bandwidth, the BIC-selected piecewise-linear fit with its breakpoints, and the
injected timescale. Upward and downward excursions are shaded distinctly --
under A10b.1 only UPWARD excursions count as evidence of structure.

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

ORDER = ["C1", "C2", "C3", "C3p", "C4", "C4p"]
TITLES = {
    "C1": "C1 — homogeneous Poisson<br><sub>must stay inside the band</sub>",
    "C2": "C2 — inhomogeneous Poisson<br><sub>must stay inside, h ≤ 1404 s</sub>",
    "C3": "C3 — clusters over 10 µs<br><sub>knee must recover 10 µs</sub>",
    "C3p": "C3′ — clusters over 1 ms  (UNSEEN)<br><sub>knee must recover 1 ms</sub>",
    "C4": "C4 — two scales, 10 µs + 60 s<br><sub>knee must recover 60 s</sub>",
    "C4p": "C4′ — clusters over 100 ms  (UNSEEN)<br><sub>knee must recover 100 ms</sub>",
}
HCOL = ["#5B8FF9", "#61DDAA", "#F6BD16", "#E8684A", "#9270CA", "#78D3F8",
        "#7BC7E8", "#B6E3B6", "#F5C99B", "#D98BA0", "#A9A9E8"]


def main() -> int:
    cfg, chash = load_cfg(), cfg_hash()
    res = json.load(open(rel("results/phase_10b/artifacts/t2_controls.json"), encoding="utf-8"))
    d = pd.read_parquet(rel("results/phase_10b/artifacts/t2_control_curves.parquet"))
    v, inj = res["verdicts"], res["controls"]["injected_scales_s"]
    hs = sorted(d["h"].unique())

    fig = make_subplots(rows=2, cols=3, subplot_titles=[TITLES[k] for k in ORDER],
                        vertical_spacing=0.20, horizontal_spacing=0.07)
    for ax, name in enumerate(ORDER):
        r, cc = divmod(ax, 3)
        r, cc = r + 1, cc + 1
        sub = d[d["control"] == name]
        elig_hs = [h for h in hs
                   if len(sub[(sub["h"] == h) & sub["h_eligible"]]) > 0]
        for hi_, h in enumerate(hs):
            s = sub[(sub["h"] == h) & sub["eligible"] & sub["band_lo"].notna()].sort_values("T")
            if not len(s):
                continue
            el = h in elig_hs
            col = HCOL[hi_ % len(HCOL)]
            fig.add_trace(go.Scatter(
                x=np.concatenate([s["T"], s["T"][::-1]]),
                y=np.concatenate([s["band_hi"], s["band_lo"][::-1]]),
                fill="toself", fillcolor=col, opacity=0.28 if el else 0.05,
                line=dict(width=0), hoverinfo="skip", showlegend=False), row=r, col=cc)
            fig.add_trace(go.Scatter(
                x=s["T"], y=s["band_hi"], mode="lines",
                line=dict(color=col, width=1, dash="dot"), opacity=1.0 if el else 0.30,
                name=f"null band, h={h:g} s" + ("" if el else "  (ineligible)"),
                legendgroup=f"h{h}", showlegend=(ax == 0),
                hovertemplate=f"h={h:g} s<br>T %{{x:.3e}}<br>hi %{{y:.4f}}<extra></extra>"),
                row=r, col=cc)
        # the control's own curve, drawn at the widest eligible bandwidth
        wh = max(elig_hs) if elig_hs else max(hs)
        s0 = sub[(sub["h"] == wh) & sub["eligible"]].sort_values("T")
        fig.add_trace(go.Scatter(
            x=s0["T"], y=s0["allan"], mode="lines", line=dict(color=C.INK2, width=2.6),
            name="control Allan curve", legendgroup="ctrl", showlegend=(ax == 0),
            hovertemplate="T %{x:.3e} s<br>Allan %{y:.4f}<extra></extra>"), row=r, col=cc)
        for flag, colr, lab in (("above", "#C23531", "excursion ABOVE (counts)"),
                                ("below", "#5B8FF9", "excursion BELOW (never counted)")):
            m = s0[s0[flag]]
            if len(m):
                fig.add_trace(go.Scatter(
                    x=m["T"], y=m["allan"], mode="markers",
                    marker=dict(color=colr, size=9, symbol="circle-open",
                                line=dict(width=2.2, color=colr)),
                    name=lab, legendgroup=flag, showlegend=(ax == 0),
                    hovertemplate=f"{flag}<br>T %{{x:.3e}} s<extra></extra>"), row=r, col=cc)
        # BIC-selected piecewise fit
        kn = res["results"][name]["knee"]
        if kn:
            sel = kn["selected"]
            xs = np.log2(s0["T"].to_numpy())
            ys = sel["intercept"] + sel["segment_slopes"][0] * xs
            for j, b in enumerate(sel["breakpoints_log2T"]):
                dsl = sel["segment_slopes"][j + 1] - sel["segment_slopes"][j]
                ys = ys + dsl * np.maximum(xs - b, 0.0)
            fig.add_trace(go.Scatter(
                x=2.0 ** xs, y=np.exp(ys), mode="lines",
                line=dict(color="#111111", width=1.8, dash="dash"),
                name=f"piecewise fit (BIC k={sel['k']})", legendgroup="fit",
                showlegend=(ax == 0), hoverinfo="skip"), row=r, col=cc)
            for b in sel["breakpoints_T_s"]:
                fig.add_vline(x=b, line=dict(color="#111111", width=1.6, dash="dot"),
                              row=r, col=cc)
        if name in inj:
            fig.add_vline(x=inj[name], line=dict(color="#C23531", width=2, dash="dash"),
                          row=r, col=cc)
        fig.update_xaxes(type="log", row=r, col=cc,
                         title_text="counting-window duration T (s, log)" if r == 2 else None)
        fig.update_yaxes(type="log", title_text="Allan factor (log)" if cc == 1 else None,
                         row=r, col=cc)

    kt = " · ".join(
        f"<b>{n}</b> inj {inj[n]:.0e}→bp {v[n]['breakpoints_T_s'][-1] if v[n]['breakpoints_T_s'] else float('nan'):.3g} "
        f"({v[n]['best_breakpoint_rung_error']:+.2f} rung, {'PASS' if v[n]['pass_knee'] else 'FAIL'})"
        for n in ("C3", "C3p", "C4", "C4p"))
    C.finish(
        fig, "04 — Synthetic control harness, A10b.1 amended: six controls, knee statistic",
        "Every control runs the SAME pipeline the real cohort would. Shaded regions are 95% "
        "matched-null bands (200 draws) from an out-of-sample λ̂ at each bandwidth h; faded bands are "
        "bandwidths made ineligible by the h/4 block rule or the floored-time rule. Red circles mark "
        "excursions ABOVE the band — the only ones A10b.1 counts as evidence of structure; blue "
        "circles mark excursions BELOW, reported but never counted. Black dashed line is the "
        "BIC-selected continuous piecewise-linear fit, black dotted verticals its breakpoints, red "
        "dashed vertical the injected timescale.",
        C.caption(
            f"6 synthetic controls, ~{res['controls']['n_target_prints']:,.0f} prints each over "
            f"{res['controls']['span_s']:,.0f} s; {res['band_h_family'].__len__()} bandwidths, "
            "200 null draws per band, 200 independent draws for coverage; no real event read",
            "sparse Allan (pipeline.py, verified exactly against a dense reference); λ̂ out of sample "
            "with Diggle edge correction on blocks of max(h/4, block_floor_event); knee = continuous "
            "piecewise-linear, k=1..3, BIC, ≥3 rungs per segment; 33-rung ladder 2⁻²⁰…2¹² s",
            chash,
            f"<b>GATE: {'PASS' if v['ALL_PASS'] else 'FAIL — HARD STOP'}.</b> "
            f"<b>Row 4d FIRED</b>: block_floor_event binds on "
            f"{v['row_4d_block_ineligibility']['worst']:.3f} of the T4 sweep on every control "
            f"(threshold {v['row_4d_block_ineligibility']['threshold']}) — 13 of 21 bandwidths, "
            "because a 20-print median block needs ~17–23 s at these rates while h/4 reaches that "
            "only at h ≳ 70–90 s.<br>"
            f"<b>Knee recovery:</b> {kt} — the knee lands systematically ABOVE the injected scale, "
            "by +0.97 to +2.91 rungs; only the 1 ms case is within tolerance. Row 4b does NOT fire "
            "(C3 itself misses, so the statistic is not fitted to the case that motivated it).<br>"
            f"<b>C1 now PASSES</b> at {v['C1']['min_share_inside_upper_only']:.3f} upper-only "
            "(was 0.871 counting both directions) — the directional rule did exactly what T2-R0 "
            f"predicted. <b>C2 fails</b> at {v['C2']['min_share_inside_upper_only']:.3f} (h=1024 s).<br>"
            f"<b>Re-assertions hold:</b> C3 plateau {v['C3']['plateau_height']:.4f} vs 6.0000 "
            f"({v['C3']['plateau_relative_error']:+.3%}), C4 separation "
            f"{v['C4']['separation_ratio']:,.0f}, coverage "
            f"{v['T2e_band_coverage']['min']:.4f}–{v['T2e_band_coverage']['max']:.4f}."),
        height=1180, width=1720)
    man = C.write(fig, rel(cfg["paths"]["out_charts"]), "04_control_harness")
    write_json(rel("results/phase_10b/artifacts/t2_chart_manifest.json"),
               {"phase": "10b", "chart": man, "config_hash": chash, "amendment": "A10b.1",
                "reads": ["results/phase_10b/artifacts/t2_control_curves.parquet",
                          "results/phase_10b/artifacts/t2_controls.json"],
                "source": "research/phase_10b/chart04_controls.py:main"})
    return 0 if man["kaleido_verified"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
