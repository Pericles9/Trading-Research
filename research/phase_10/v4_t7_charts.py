"""
Phase 10 v4 T7 -- charts 01-05. Produced under the failure (rows 1, 6).

Usage: .venv/Scripts/python.exe research/phase_10/v4_t7_charts.py
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import chartlib as C  # noqa: E402
from v2_common import COHORT_KEY, POOLED, rel, write_json  # noqa: E402
from v4_pipeline import cfg_hash, load_cfg  # noqa: E402

SC = {"premarket": C.ARM_B, "rth": C.ARM_A}


def main() -> int:
    cfg = load_cfg()
    chash = cfg_hash()
    art = rel(cfg["paths"]["out_artifacts"])
    out = rel(cfg["paths"]["out_charts"])
    cut = cfg["threshold"]["void_parameter"]["cutoff"]
    tie_ref = cfg["ties"]["reference_variant"]
    wref = cfg["normalization"]["window_fraction_reference"]
    mref = cfg["subbursts"]["min_prints_reference"]

    ev = pd.read_parquet(os.path.join(art, "v4_event_metrics.parquet"))
    sb = pd.read_parquet(os.path.join(art, "v4_subbursts.parquet"))
    hi = pd.read_parquet(os.path.join(art, "v4_histograms.parquet"))
    for d in (ev, sb, hi):
        d["event_date_canonical"] = d["event_date_canonical"].astype(str)
    t = json.load(open(os.path.join(art, "v4_t5_t6_summary.json"), encoding="utf-8"))
    ref = ev[(ev["tie_variant"] == tie_ref) & (ev["window_fraction"] == wref)
             & (ev["min_prints"].fillna(mref) == mref)]
    pool = ref[ref["cohort_group"].isin(POOLED)]
    ok = pool[pool["status"] == "ok"]
    psb = sb[sb["cohort_group"].isin(POOLED)]
    man = []

    # ------------------------------------------------------------- 01
    # `hi` already carries the base fields (segment, n_prints_raw); merging pool
    # in would suffix them.
    hp = hi[hi.set_index(COHORT_KEY).index.isin(pool.set_index(COHORT_KEY).index)].copy()
    picks = []
    for seg in ("premarket", "rth"):
        s = hp[(hp["segment"] == seg) & (hp["has_threshold"])].sort_values("n_prints_raw")
        if len(s):
            picks.append(s.iloc[[0, len(s) // 2, len(s) - 1]])
        nt = hp[(hp["segment"] == seg) & (~hp["has_threshold"])]
        if len(nt):
            picks.append(nt.head(3))
    sel = pd.concat(picks, ignore_index=True).head(12)
    ncol = 3
    nrow = int(np.ceil(len(sel) / ncol))
    fig = make_subplots(rows=nrow, cols=ncol, vertical_spacing=0.085, horizontal_spacing=0.06,
                        subplot_titles=[
                            f"{r.ticker} {r.event_date_canonical}<br>"
                            f"<sub>{r.segment} · {int(r.n_prints_raw):,} prints · "
                            + (f"void {r.void:.3f}, thr {r.threshold_decades:+.2f}"
                               if r.has_threshold else "NO THRESHOLD") + "</sub>"
                            for r in sel.itertuples(index=False)])
    for i, r in enumerate(sel.itertuples(index=False)):
        rr, cc = i // ncol + 1, i % ncol + 1
        x = np.asarray(r.hist_centres, dtype=float)
        y = np.asarray(r.hist_density, dtype=float)
        if x.size == 0:
            continue
        col = SC.get(r.segment, C.ARM_A)
        fig.add_trace(go.Scatter(x=x, y=y, mode="lines", line=dict(color=col, width=1.6),
                                 showlegend=False,
                                 hovertemplate="y=%{x:.2f}<br>density %{y:.4g}<extra></extra>"),
                      row=rr, col=cc)
        if r.has_threshold:
            for pv, dash, cl in ((r.peak_left_decades, "dot", "#008300"),
                                 (r.peak_right_decades, "dot", "#008300")):
                if pd.notna(pv):
                    fig.add_vline(x=pv, line=dict(color=cl, width=1, dash=dash), row=rr, col=cc)
            fig.add_vline(x=r.threshold_decades, line=dict(color="#b03a3a", width=2),
                          row=rr, col=cc)
        fig.update_xaxes(title_text="normalized log10 interval" if rr == nrow else None,
                         range=[-5, 3], row=rr, col=cc)
        fig.update_yaxes(type="log", row=rr, col=cc)
    C.finish(fig, "01 — Is the interval distribution actually bimodal?",
             "Normalized log-interval histogram per event (log y). Green dotted = detected peaks, "
             "red = chosen trough (the threshold). Events spanning the activity range in each "
             "segment, plus no-threshold examples.",
             C.caption(f"{len(sel)} events from the pooled analysis cohort",
                       f"tie={tie_ref}, window={wref:.0%}; normalized log10 interval", chash,
                       f"no_threshold pooled: {t['t3_no_threshold']['pooled']['n_no_threshold']}/"
                       f"{t['t3_no_threshold']['pooled']['n_events']} = "
                       f"{t['t3_no_threshold']['pooled']['share_no_threshold']:.1%}. "
                       f"Median chosen threshold {t['t3_threshold']['pooled']['q50']:+.3f} decades — "
                       "intervals roughly 1/1700 of the local median."
                       "<br><b>Reads:</b> unimodal or ragged means no separation to threshold on."),
             height=300 * nrow + 320, width=1400)
    man.append(C.write(fig, out, "v4_01_log_interval_histograms"))

    # ------------------------------------------------------------- 02
    fig = make_subplots(rows=1, cols=2, column_widths=[0.5, 0.5], horizontal_spacing=0.10,
                        subplot_titles=["Void parameter distribution",
                                        "Void parameter vs T=0 print count"])
    for seg, col in SC.items():
        v = ok.loc[ok["segment"] == seg, "void"].dropna()
        if not len(v):
            continue
        x, y = C.ecdf(v)
        fig.add_trace(go.Scatter(x=x, y=y, mode="lines", line=dict(color=col, width=2),
                                 name=f"{seg} (n={len(v)})",
                                 hovertemplate="void %{x:.4f}<br>cum %{y:.3f}<extra></extra>"),
                      row=1, col=1)
        s = ok[ok["segment"] == seg]
        fig.add_trace(go.Scatter(x=s["n_prints_raw"], y=s["void"], mode="markers",
                                 marker=dict(color=col, size=8, opacity=0.7,
                                             line=dict(color=C.SURFACE, width=1)),
                                 name=f"{seg}", showlegend=False,
                                 customdata=s[COHORT_KEY].to_numpy(),
                                 hovertemplate="%{customdata[0]} %{customdata[1]}<br>"
                                               "%{x:,.0f} prints<br>void %{y:.4f}<extra></extra>"),
                      row=1, col=2)
    m = cfg["failure_criteria"]["row_3"]["margin"]
    for cc in (1, 2):
        fig.add_vline(x=cut, line=dict(color="#b03a3a", width=2, dash="dash"),
                      row=1, col=cc) if cc == 1 else fig.add_hline(
            y=cut, line=dict(color="#b03a3a", width=2, dash="dash"), row=1, col=cc)
    fig.add_vrect(x0=cut, x1=cut + m, fillcolor="#b03a3a", opacity=0.08, line_width=0, row=1, col=1)
    fig.update_xaxes(title_text=f"void parameter (cutoff {cut})", row=1, col=1)
    fig.update_yaxes(title_text="cumulative share of events", range=[0, 1.02], row=1, col=1)
    fig.update_xaxes(type="log", title_text="T=0 print count (log)", row=1, col=2)
    fig.update_yaxes(title_text="void parameter", row=1, col=2)
    C.finish(fig, "02 — Which events support a threshold, and how comfortably?",
             "Void parameter = 1 − f(trough)/√(f(peak_left)·f(peak_right)). Only events clearing the "
             "0.70 cutoff get a threshold; the rest are labeled no_threshold and get none.",
             C.caption(f"threshold-bearing events, n={len(ok)} of {len(pool)} pooled",
                       f"tie={tie_ref}, window={wref:.0%}", chash,
                       f"Median void {t['t3_void']['pooled']['q50']:.4f}. "
                       f"Share within {m} above the cutoff: "
                       f"{t['t3_void']['share_within_margin_above_cutoff']:.4f} "
                       f"(row 3 threshold ≤ 0.30) — PASS. Shaded band is that margin."
                       "<br><b>Reads:</b> mass piled just above the cutoff would mean a pass/fail "
                       "count hides the fragility."))
    man.append(C.write(fig, out, "v4_02_void_parameter"))

    # ------------------------------------------------------------- 03
    fig = go.Figure()
    for seg, col in SC.items():
        v = ok.loc[ok["segment"] == seg, "n_subbursts"]
        if not len(v):
            continue
        x, y = C.ecdf(np.maximum(v, 0.5))
        fig.add_trace(go.Scatter(x=x, y=y, mode="lines", line=dict(color=col, width=2),
                                 name=f"{seg} (n={len(v)}, median {np.median(v):,.0f})",
                                 hovertemplate="%{x:,.0f} sub-bursts<br>cum %{y:.3f}<extra></extra>"))
    fig.update_xaxes(type="log", title_text="sub-bursts per event (log)")
    fig.update_yaxes(title_text="cumulative share of events", range=[0, 1.02])
    C.finish(fig, "03 — How many sub-bursts does a session have?",
             "Per-event count, threshold-bearing events only, by detection segment. Log x.",
             C.caption(f"threshold-bearing events, n={len(ok)}", f"tie={tie_ref}, window={wref:.0%}, "
                       f"min_prints={mref}", chash,
                       f"no_threshold events excluded here and counted separately: "
                       f"{t['t3_no_threshold']['pooled']['n_no_threshold']} pooled. "
                       f"Pooled median {t['t4_descriptive']['pooled']['subburst_count']['q50']:,.0f}, "
                       f"max {t['t4_descriptive']['pooled']['subburst_count']['q100']:,.0f}."
                       "<br><b>Reads:</b> all mass at 1, or a single spike, would be degenerate."))
    man.append(C.write(fig, out, "v4_03_subburst_count"))

    # ------------------------------------------------------------- 04 (the failure)
    fig = make_subplots(rows=1, cols=2, horizontal_spacing=0.09,
                        subplot_titles=["vs T=0 print count (failure row 1)", "vs session duration"])
    for ci, (xcol, xlab) in enumerate((("n_prints_raw", "T=0 print count (log)"),
                                       ("print_span_seconds", "session activity duration, s (log)")), 1):
        for seg, col in SC.items():
            s = ok[ok["segment"] == seg]
            fig.add_trace(go.Scatter(x=s[xcol], y=np.maximum(s["n_subbursts"], 0.5), mode="markers",
                                     marker=dict(color=col, size=8, opacity=0.7,
                                                 line=dict(color=C.SURFACE, width=1)),
                                     name=f"{seg} (n={len(s)})", showlegend=(ci == 1),
                                     customdata=s[COHORT_KEY].to_numpy(),
                                     hovertemplate="%{customdata[0]} %{customdata[1]}<br>"
                                                   "x %{x:,.4g}<br>%{y:,.0f} sub-bursts<extra></extra>"),
                          row=1, col=ci)
        m2 = (ok[xcol] > 0) & (ok["n_subbursts"] > 0)
        if m2.sum() > 5:
            b, a = np.polyfit(np.log10(ok.loc[m2, xcol]), np.log10(ok.loc[m2, "n_subbursts"]), 1)
            xs = np.linspace(np.log10(ok.loc[m2, xcol].min()), np.log10(ok.loc[m2, xcol].max()), 20)
            fig.add_trace(go.Scatter(x=10 ** xs, y=10 ** (a + b * xs), mode="lines",
                                     line=dict(color=C.INK, width=2.5),
                                     name=f"fitted slope {b:+.3f}", hoverinfo="skip"), row=1, col=ci)
        if ci == 1:
            x0 = ok["n_prints_raw"].min()
            xs = np.linspace(np.log10(x0), np.log10(ok["n_prints_raw"].max()), 20)
            fig.add_trace(go.Scatter(x=10 ** xs, y=10 ** (0.6 + 0.85 * (xs - np.log10(x0))),
                                     mode="lines", line=dict(color="#b03a3a", width=2, dash="dash"),
                                     name="Arm A reference slope 0.85", hoverinfo="skip"),
                          row=1, col=ci)
        fig.update_xaxes(type="log", title_text=xlab, row=1, col=ci)
        fig.update_yaxes(type="log", title_text="sub-bursts per event (log)", row=1, col=ci)
    a5 = t["t5_arm_a_test"]["pooled"]
    C.finish(fig, "04 — Is the count real or a print-count artifact?",
             "The Arm A test. Arm A's burst count correlated +0.96 with print count at log-log slope "
             "0.85; that reference slope is drawn in red.",
             C.caption(f"threshold-bearing events, n={len(ok)}", f"tie={tie_ref}, window={wref:.0%}",
                       chash,
                       f"<b>FAILURE ROW 1 FIRED.</b> Spearman "
                       f"{a5['t0_print_count']['spearman']:+.4f} (≤0.50), log-log slope "
                       f"{a5['t0_print_count']['loglog_slope']:+.4f} (≤0.35). The fitted slope sits "
                       "ABOVE Arm A's reference line. Against absolute activity (prints/sec): "
                       f"Spearman {a5['absolute_activity_prints_per_sec']['spearman']:+.4f}, slope "
                       f"{a5['absolute_activity_prints_per_sec']['loglog_slope']:+.4f}."
                       "<br><b>Reads:</b> a slope near the red line is the same defect in a fifth "
                       "method."))
    man.append(C.write(fig, out, "v4_04_count_vs_prints"))

    # ------------------------------------------------------------- 05
    fig = make_subplots(rows=1, cols=3, horizontal_spacing=0.07,
                        subplot_titles=["sub-burst duration", "inter-sub-burst spacing",
                                        "share of session move"])
    floor_s = t["t6d_failure_criteria"]["rows"][5]["observed"]["resolution_floor_s"]
    for seg, col in SC.items():
        s = psb[psb["segment"] == seg]
        for ci, c in enumerate(("duration_seconds", "spacing_seconds", "move_share"), 1):
            v = s[c].dropna()
            if not len(v):
                continue
            xx = np.maximum(v, 1e-9) if ci < 3 else v
            x, y = C.ecdf(xx)
            fig.add_trace(go.Scatter(x=x, y=y, mode="lines", line=dict(color=col, width=2),
                                     name=f"{seg} (n={len(v):,})", showlegend=(ci == 1),
                                     hovertemplate="%{x:,.4g}<br>cum %{y:.3f}<extra></extra>"),
                          row=1, col=ci)
    for ci in (1, 2):
        fig.add_vline(x=floor_s, line=dict(color="#b03a3a", width=2, dash="dash"),
                      annotation_text=f"timestamp resolution {floor_s*1e9:.0f} ns",
                      annotation_position="top", annotation_font=dict(size=9.5, color="#b03a3a"),
                      row=1, col=ci)
        fig.update_xaxes(type="log", title_text="seconds (log)", row=1, col=ci)
    fig.update_xaxes(title_text="share of session move (signed)", range=[-0.5, 0.5],
                     rangeslider=dict(visible=True, thickness=0.05), row=1, col=3)
    fig.update_yaxes(title_text="cumulative share", range=[0, 1.02], row=1, col=1)
    p = t["t4_descriptive"]["pooled"]
    C.finish(fig, "05 — What timescale do sub-bursts live at, and do they carry the move?",
             "Duration, spacing and per-sub-burst share of the session move, by segment. Log x on the "
             "first two, with the timestamp resolution floor marked.",
             C.caption(f"{len(psb):,} sub-bursts over {len(ok)} threshold-bearing events",
                       f"tie={tie_ref}, window={wref:.0%}, min_prints={mref}", chash,
                       f"<b>FAILURE ROW 6 FIRED.</b> Median duration "
                       f"{p['duration_seconds']['q50']*1e9:.0f} ns against a {floor_s*1e9:.0f} ns "
                       f"resolution floor — 4.34×, where >10× was required. Rank-1 move share median "
                       f"{p['move_share_by_rank']['rank_1']['q50']:+.4f}; "
                       f"{p['n_move_share_undefined']} undefined denominators."
                       "<br><b>Reads:</b> duration piled at the resolution floor means the "
                       "decomposition is reading the clock, not the tape."))
    man.append(C.write(fig, out, "v4_05_duration_spacing_moveshare"))

    n_ok = sum(x["kaleido_verified"] for x in man)
    write_json(os.path.join(art, "v4_t7_chart_manifest.json"),
               {"phase": "10", "version": "v4", "task": "T7", "config_hash": chash,
                "n_charts": len(man), "n_kaleido_verified": n_ok,
                "all_verified": n_ok == len(man), "charts": man,
                "note": "produced under the failure (rows 1, 6)",
                "source": "research/phase_10/v4_t7_charts.py:main"})
    print(f"kaleido-verified {n_ok}/{len(man)}")
    return 0 if n_ok == len(man) else 1


if __name__ == "__main__":
    raise SystemExit(main())
