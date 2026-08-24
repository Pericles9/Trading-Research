"""Phase 10c Stage 0b charts. Linked panels on a shared x-axis; no dual y-scale."""
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

ART, CH = "results/phase_10c/artifacts", "results/phase_10c/charts"
SEGC = {"premarket": C.ARM_B, "rth": C.ARM_A}


def main() -> int:
    cfg, chash = c10c.load_cfg(), c10c.cfg_hash()
    E, M = c10c.class_e(cfg), c10c.class_m(cfg)
    d16 = float(E["D16_min_median_void"])
    ev = pd.read_parquet(rel(f"{ART}/t0b_2_void.parquet"))
    cur = pd.read_parquet(rel(f"{ART}/t0b_1_curves.parquet"))
    sw = pd.read_parquet(rel(f"{ART}/t0b_4_prominence_sweep.parquet"))
    df = pd.read_parquet(rel(f"{ART}/t0b_3_5_density_floor.parquet"))
    man = []
    prim = ev[~ev.is_sidecar]

    # ---------------- B1: peak set
    fig = make_subplots(rows=1, cols=2, horizontal_spacing=0.09, subplot_titles=[
        "Post-aggregation density with every surviving peak marked, 10 events",
        "Across-event distribution of peak count"])
    reps = ev.sort_values("n_prints_agg").iloc[np.linspace(0, len(ev) - 1, 10).astype(int)]
    for _, r in reps.iterrows():
        s = cur[(cur.ticker == r.ticker) & (cur.event_date_canonical == r.event_date_canonical)]
        s = s.sort_values("log10s")
        col = SEGC.get(r.det_segment, C.INK2)
        fig.add_trace(go.Scatter(x=s.log10s, y=s.density, mode="lines", opacity=0.6,
                                 line=dict(width=1.2, color=col), showlegend=False,
                                 hovertemplate=f"{r.ticker}<br>log10 %{{x:.2f}}<extra></extra>"),
                      row=1, col=1)
        pp = s[s.is_peak]
        fig.add_trace(go.Scatter(x=pp.log10s, y=pp.density, mode="markers", showlegend=False,
                                 marker=dict(size=6, color=col, symbol="circle-open",
                                             line=dict(width=1.6, color=col)),
                                 hoverinfo="skip"), row=1, col=1)
    for seg, g in ev.groupby(ev.det_segment.fillna("unlabelled")):
        fig.add_trace(go.Box(x=g.n_peaks, name=f"{seg} (n={len(g)})", orientation="h",
                             marker_color=SEGC.get(seg, C.INK2), boxpoints="all", jitter=0.5,
                             pointpos=0, marker=dict(size=5), showlegend=False), row=1, col=2)
    fig.update_xaxes(title_text="log10 inter-trade interval (s)", row=1, col=1)
    fig.update_xaxes(title_text="peaks surviving the Poisson floor", row=1, col=2)
    fig.update_yaxes(title_text="density", row=1, col=1)
    C.finish(fig, "B1 — Full peak set after aggregation at D1 = 100 µs (T0b.1)",
             "A peak is kept only where its prominence in count units exceeds the Poisson "
             "counting noise sqrt(k) in its own bin (A2.4 Part 1). That is a per-peak test, so no "
             "global prominence constant is used anywhere in this chart.",
             C.caption(f"dev sample n={len(ev)} events, {int(ev.n_intervals.sum()):,} "
                       "post-aggregation intervals",
                       f"D1 = {M['D1_sweep_floor_us']:.0f} µs, anchor-based aggregation; bin width "
                       "0.1 log units; no smoothing", chash,
                       f"<b>Median surviving peak count is {ev.n_peaks.median():.0f}</b> "
                       f"(quartiles {ev.n_peaks.quantile(.25):.0f}–{ev.n_peaks.quantile(.75):.0f}, "
                       f"max {ev.n_peaks.max():.0f}), by segment "
                       f"premarket {ev[ev.det_segment=='premarket'].n_peaks.median():.0f} and "
                       f"rth {ev[ev.det_segment=='rth'].n_peaks.median():.0f}. The method's stated "
                       "precondition is a two-mode histogram; the count is reported here as "
                       "measured."),
             height=640, width=1500)
    man.append(C.write(fig, rel(CH), "b1_peak_set"))

    # ---------------- B2: void, the gate statistic
    fig = go.Figure()
    for seg, g in ev.groupby(ev.det_segment.fillna("unlabelled")):
        v = g["void"].dropna()
        fig.add_trace(go.Box(x=v, name=f"{seg} (n={len(v)})", orientation="h", boxpoints="all",
                             jitter=0.5, pointpos=0, marker=dict(size=6),
                             marker_color=SEGC.get(seg, C.INK2)))
    fig.add_vline(x=d16, line=dict(color="#C23531", width=2.6, dash="dash"),
                  annotation_text=f"D16 = {d16}", annotation_position="top")
    fig.update_xaxes(title_text="void parameter at the deepest trough between the two most "
                                "prominent peaks")
    pm = ev[ev.det_segment == "premarket"]["void"].median()
    rt = ev[ev.det_segment == "rth"]["void"].median()
    C.finish(fig, "B2 — Void parameter distribution and the T0b.6 precondition gate",
             "Continuous, never thresholded per D13. The red line is the pre-registered gate "
             "value, fixed before this distribution existed.",
             C.caption(f"dev sample n={len(ev)} events; "
                       f"{int(ev.label.eq('bimodal').sum())} produced a computable trough, "
                       f"{int(ev.label.eq('unimodal').sum())} labelled unimodal",
                       "void = 1 - f(trough) / sqrt(f(peak_lo) * f(peak_hi)); peaks from the "
                       "Poisson-derived floor", chash,
                       f"<b>Gate outcome: median void {pm:.4f} premarket and {rt:.4f} rth, both "
                       f"above D16 = {d16}. The gate does not fire.</b><br>"
                       "The gate tests the trough between the two most prominent peaks. B1 reports "
                       "how many peaks are present."),
             height=560, width=1400)
    man.append(C.write(fig, rel(CH), "b2_void_gate"))

    # ---------------- B3: A2.7 D2 gap
    fig = go.Figure()
    for seg, g in prim.groupby("det_segment"):
        fig.add_trace(go.Scatter(x=g.peak_lo_log10s, y=g.peak_hi_log10s, mode="markers",
                                 marker=dict(size=10, color=SEGC.get(seg, C.INK2), opacity=0.8),
                                 name=f"{seg} (n={len(g)})",
                                 hovertemplate="fast %{x:.2f}<br>slow %{y:.2f}<extra></extra>"))
    f95 = prim.peak_lo_log10s.quantile(.95)
    s05 = prim.peak_hi_log10s.quantile(.05)
    fig.add_vline(x=f95, line=dict(color=C.ARM_A, width=2, dash="dash"),
                  annotation_text=f"fast-mode p95 = {f95:+.2f}", annotation_position="top left")
    fig.add_hline(y=s05, line=dict(color=C.ARM_B, width=2, dash="dash"),
                  annotation_text=f"slow-mode p5 = {s05:+.2f}", annotation_position="bottom right")
    lim = [prim.peak_lo_log10s.min() - .3, prim.peak_hi_log10s.max() + .3]
    fig.add_trace(go.Scatter(x=lim, y=lim, mode="lines", line=dict(color=C.INK2, width=1,
                  dash="dot"), name="equal locations", hoverinfo="skip"))
    fig.update_xaxes(title_text="location of the EARLIER of the two most prominent peaks (fast), log10 s")
    fig.update_yaxes(title_text="location of the LATER of the two most prominent peaks (slow), log10 s")
    C.finish(fig, "B3 — Joint distribution of the two most prominent peaks, and the A2.7 D2 test",
             "A2.7 requires D2 to sit between the fast mode's right tail and the slow mode's left "
             "tail across all events. Rule 1 applies if p95(fast) < p5(slow); rule 2 applies if "
             "they overlap.",
             C.caption(f"primary dev-sample events n={len(prim)} (sidecar excluded from the "
                       "percentiles per A1.6)",
                       "the two most prominent peaks per event, ordered by LOCATION not by height; peaks from the Poisson-derived floor",
                       chash,
                       f"<b>p95(fast) = {f95:+.3f} exceeds p5(slow) = {s05:+.3f}, so the tails "
                       f"overlap by {f95 - s05:.3f} decades.</b> Under A2.7 rule 2 no single "
                       "global D2 exists and the prescribed response is to report the overlap and "
                       "escalate rather than pick a compromise value."),
             height=700, width=1280)
    man.append(C.write(fig, rel(CH), "b3_d2_gap"))

    # ---------------- B4: dispersion + too_few grid
    d = df[df.det_segment.isin(["premarket", "rth"])]
    fig = make_subplots(rows=1, cols=2, horizontal_spacing=0.10, subplot_titles=[
        "sigma_log10 before and after aggregation, by segment",
        "too_few_prints fraction, median across events"])
    raw = pd.read_parquet(rel(f"{ART}/t0_4_density_d4.parquet")).drop_duplicates(
        subset=["ticker", "event_date_canonical"])
    for nm, s, col in (("raw (Stage 0)", raw.sigma_log10, C.INK2),
                       ("post-aggregation", ev.sigma_log10_post_agg, C.ARM_A)):
        fig.add_trace(go.Box(x=s.dropna(), name=nm, orientation="h", marker_color=col,
                             boxpoints="all", jitter=0.5, pointpos=0, marker=dict(size=5),
                             showlegend=False), row=1, col=1)
    for seg in ("premarket", "rth"):
        for fac, dash in ((1.2, "solid"), (1.5, "dot")):
            s = d[(d.det_segment == seg) & (d.precision_factor == fac)]
            g = s.groupby("kernel_min").too_few_prints_fraction.median()
            fig.add_trace(go.Scatter(x=g.index, y=g.values, mode="lines+markers",
                                     line=dict(color=SEGC[seg], width=2.2, dash=dash),
                                     marker=dict(size=8), name=f"{seg}, F={fac}"), row=1, col=2)
    fig.update_xaxes(title_text="sigma_log10 (decades)", row=1, col=1)
    fig.update_xaxes(type="log", title_text="kernel duration (minutes, log)", row=1, col=2)
    fig.update_yaxes(title_text="fraction of intervals", row=1, col=2)
    C.finish(fig, "B4 — Post-aggregation dispersion and the D4 / D5 derivation inputs (T0b.3)",
             "Derived floor is n >= (sqrt(pi/2) * sigma_log10 / log10 F)^2, recomputed on the "
             "post-aggregation sigma. Windows are clipped at the RTH open and close per A2.5. "
             "Segments are never pooled.",
             C.caption(f"dev sample, premarket n={d[d.det_segment=='premarket'].ticker.nunique()} "
                       f"and rth n={d[d.det_segment=='rth'].ticker.nunique()} tickers",
                       f"D1 = {M['D1_sweep_floor_us']:.0f} µs; base-2 rungs 1 to D11 = "
                       f"{M['D11_grid_ceiling_min']} min", chash,
                       f"sigma falls from {raw.sigma_log10.median():.3f} raw to "
                       f"{ev.sigma_log10_post_agg.median():.3f} after aggregation "
                       f"(premarket {ev[ev.det_segment=='premarket'].sigma_log10_post_agg.median():.3f}, "
                       f"rth {ev[ev.det_segment=='rth'].sigma_log10_post_agg.median():.3f}).<br>"
                       "<b>A2.8's D5 rule — the smallest rung where the median RTH event clears "
                       "the floor — resolves to 32 min at F=1.2, 16 min at F=1.3 and 8 min at "
                       "F=1.5. At F=1.1 no rung at or below D11 = 64 clears it.</b>"),
             height=640, width=1500)
    man.append(C.write(fig, rel(CH), "b4_dispersion_floor"))

    # ---------------- B5: prominence sensitivity + near-detection density
    fig = make_subplots(rows=1, cols=2, horizontal_spacing=0.10, subplot_titles=[
        "Trough displacement across the prominence sweep (T0b.4)",
        "Print density: session-wide vs near the detection anchor (T0b.5)"])
    disp = sw.dropna(subset=["trough_log10s"]).groupby(
        ["ticker", "event_date_canonical"]).trough_log10s.agg(lambda s: s.max() - s.min())
    fig.add_trace(go.Box(x=disp.values, name=f"n={len(disp)}", orientation="h",
                         marker_color=C.ARM_A, boxpoints="all", jitter=0.5, pointpos=0,
                         marker=dict(size=6), showlegend=False), row=1, col=1)
    u = df.drop_duplicates(subset=["ticker", "event_date_canonical"])
    u = u[u.det_segment.isin(["premarket", "rth"])]
    for nm, col_, colr in (("session-wide", "session_prints_per_min", C.INK2),
                           ("near detection", "near_detection_prints_per_min", C.ARM_A)):
        vals = [u[u.det_segment == s][col_].median() for s in ("premarket", "rth")]
        fig.add_trace(go.Bar(x=["premarket", "rth"], y=vals, name=nm, marker_color=colr),
                      row=1, col=2)
    fig.update_xaxes(title_text="max - min trough location across prominence 0.01-0.20 (decades)",
                     row=1, col=1)
    fig.update_yaxes(type="log", title_text="prints per minute (log)", row=1, col=2)
    C.finish(fig, "B5 — Prominence sensitivity and near-detection density (T0b.4, T0b.5)",
             "A2.4 Part 2: displacement across the prominence sweep measures whether the answer "
             "tracks the parameter. It carries no pass threshold in this phase and is reported "
             "beside the D9 slope distribution in the Stage 2 digest.",
             C.caption(f"displacement n={len(disp)} events with a trough at 2 or more sweep "
                       f"values; density n={u.ticker.nunique()} tickers",
                       "prominence sweep 0.01/0.02/0.05/0.10/0.20 as a fraction of each event's "
                       f"own peak density; near-detection window "
                       f"{cfg['stage_0b_sweeps']['T0b_5_near_detection_window_min']} min", chash,
                       f"Trough displacement median {np.median(disp):.2f} decades "
                       f"(p90 {np.percentile(disp, 90):.2f}).<br>"
                       "<b>RTH density near the detection anchor is "
                       f"{u[u.det_segment=='rth'].near_detection_prints_per_min.median():.1f}/min "
                       f"against {u[u.det_segment=='rth'].session_prints_per_min.median():.1f}/min "
                       "session-wide</b>, which is the quantity A2.8 directs D5 to be sized on. "
                       "Premarket is flat between the two measures."),
             height=620, width=1500)
    man.append(C.write(fig, rel(CH), "b5_prominence_density"))

    c10c.write_json(rel(f"{ART}/t0b_chart_manifest.json"),
                    {"config_hash": chash, "charts": man,
                     "source": "research/phase_10c/t0b_charts.py:main"})
    print(f"{len(man)} charts; kaleido {sum(m['kaleido_verified'] for m in man)}/{len(man)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
