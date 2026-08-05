"""
Phase 10 v3 T6 -- charts 02-06. Produced under a partial failure (rows 2, 3, 4).

Usage: .venv/Scripts/python.exe research/phase_10/v3_t6_charts.py
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
from v2_common import COHORT_KEY, POOLED, knn_rate, read_event_trades, rel, session_window, write_json  # noqa: E402
from v3_t1_gate import cfg_hash, load_cfg  # noqa: E402
from v3_t2_t4_subbursts import resolve  # noqa: E402

OBS = {"print_rate": "print rate", "volume_rate": "share-volume rate"}
OC = {"print_rate": C.ARM_A, "volume_rate": C.ARM_B}
SC = {"premarket": C.ARM_B, "rth": C.ARM_A}


def main() -> int:
    cfg = load_cfg()
    chash = cfg_hash()
    art = rel(cfg["paths"]["out_artifacts"])
    out = rel(cfg["paths"]["out_charts"])
    ev = pd.read_parquet(os.path.join(art, "v3_t3_event_metrics.parquet"))
    sub = pd.read_parquet(os.path.join(art, "v3_t3_subbursts.parquet"))
    for d in (ev, sub):
        d["event_date_canonical"] = d["event_date_canonical"].astype(str)
    ev["ok"] = ev["ok"].fillna(False).astype(bool)
    t5 = json.load(open(os.path.join(art, "v3_t5_stability.json"), encoding="utf-8"))
    t24 = json.load(open(os.path.join(art, "v3_t2_t4_summary.json"), encoding="utf-8"))
    gate = json.load(open(os.path.join(art, "v3_t1_gate.json"), encoding="utf-8"))
    pe = ev[ev["cohort_group"].isin(POOLED) & ev["ok"]]
    ps = sub[sub["cohort_group"].isin(POOLED)]
    man = []

    # ---------------------------------------------------------------- 02 envelope examples
    sel = (pe[pe["observable"] == "print_rate"]
           .sort_values("n_prints_t0").groupby("segment")
           .apply(lambda g: g.iloc[[0, len(g) // 2, len(g) - 1]] if len(g) >= 3 else g,
                  include_groups=False)
           .reset_index())
    rows_n = len(sel)
    fig = make_subplots(rows=rows_n, cols=1, shared_xaxes=False, vertical_spacing=0.055,
                        subplot_titles=[f"{r.ticker} {r.event_date_canonical} — {r.segment}, "
                                        f"{int(r.n_prints_t0):,} prints, knee {r.knee_seconds:g}s"
                                        for r in sel.itertuples(index=False)])
    for ri, r in enumerate(sel.itertuples(index=False), 1):
        d = read_event_trades(cfg, r.ticker, r.event_date_canonical, r.momentum_pct, offsets=(0,))
        t0 = d.get(0)
        if t0 is None or len(t0) == 0:
            continue
        ts = t0["sip_timestamp"].to_numpy(); sz = t0["size"].to_numpy(dtype=float)
        w = session_window(r.event_date_canonical, 0)
        et = pd.to_datetime(pd.Series(ts), unit="ns", utc=True).dt.tz_convert("America/New_York").dt.tz_localize(None)
        fast = knn_rate(ts, sz, cfg["envelope"]["fast_k"], 1e-9)["print_rate"]
        env = knn_rate(ts, sz, int(r.k_env), 1e-9)["print_rate"]
        step = max(1, len(ts) // 40000)
        fig.add_trace(go.Scattergl(x=et[::step], y=fast[::step], mode="lines",
                                   line=dict(color="rgba(27,27,26,0.55)", width=0.8),
                                   name="rate (k=50)", showlegend=(ri == 1),
                                   legendgroup="fast"), row=ri, col=1)
        fig.add_trace(go.Scattergl(x=et[::step], y=env[::step], mode="lines",
                                   line=dict(color=SC.get(r.segment, C.ARM_A), width=2.2),
                                   name=f"envelope (k_env from knee)", showlegend=(ri == 1),
                                   legendgroup="env"), row=ri, col=1)
        fig.update_yaxes(type="log", title_text="prints/s (log)", row=ri, col=1)
    C.finish(fig, "02 — What does the envelope look like against the rate?",
             "Fast rate (k=50) and the gate-derived envelope, print observable. One row per selected "
             "event: thinnest, median and busiest within each detection segment. Log y.",
             C.caption(f"{rows_n} events selected from the pooled analysis cohort",
                       "T=0 only; envelope k_env = expected prints in a knee-duration window at the "
                       "event's own mean rate", chash,
                       "<b>Reads:</b> an envelope tracking every wiggle, or flat through obvious "
                       "structure, is wrong. Row 3 FAILED — the sub-burst set is unstable inside "
                       "the knee's own bootstrap interval."),
             height=260 * rows_n + 320, width=1400)
    man.append(C.write(fig, out, "v3_02_envelope_examples"))

    # ---------------------------------------------------------------- 03 count
    fig = make_subplots(rows=1, cols=2, subplot_titles=[OBS[o] for o in OBS],
                        horizontal_spacing=0.09, shared_yaxes=True)
    for ci, obs in enumerate(OBS, 1):
        for si, (sname, col) in enumerate(SC.items()):
            v = pe.loc[(pe["observable"] == obs) & (pe["segment"] == sname), "n_subbursts"]
            if not len(v):
                continue
            fig.add_trace(go.Box(x=np.maximum(v, 0.5), y=[si] * len(v), orientation="h",
                                 name=f"{sname} (n={len(v)})", legendgroup=sname,
                                 showlegend=(ci == 1),
                                 marker=dict(color=col, size=6, opacity=0.75,
                                             line=dict(color=C.SURFACE, width=1)),
                                 line=dict(color=col, width=2), fillcolor="rgba(0,0,0,0)",
                                 boxpoints="all", jitter=0.6, pointpos=0, width=0.5,
                                 hovertemplate="%{x:,.0f} sub-bursts<extra></extra>"),
                          row=1, col=ci)
            fig.add_annotation(x=np.log10(max(v.max(), 1)), y=si + 0.33,
                               xref=f"x{ci if ci > 1 else ''}", yref=f"y{ci if ci > 1 else ''}",
                               xanchor="right", showarrow=False,
                               text=f"n={len(v)}  median={np.median(v):,.0f}",
                               font=dict(size=10.5, color=C.INK2))
        fig.update_xaxes(type="log", title_text="sub-bursts per event (log)", row=1, col=ci)
    fig.update_yaxes(tickmode="array", tickvals=[0, 1], ticktext=list(SC), row=1, col=1)
    C.finish(fig, "03 — How many sub-bursts does a session have?",
             "Per-event sub-burst count, split by detection segment (D8 consequence (d)). Log x.",
             C.caption("pooled analysis cohort, n=100 events (premarket 28, rth 70)",
                       "T=0 only; excursions on rate/envelope at the gate-derived knee", chash,
                       f"print median {t24['t3_counts']['print_rate']['count']['q50']:.0f}, "
                       f"volume median {t24['t3_counts']['volume_rate']['count']['q50']:.0f}"
                       "<br><b>Reads:</b> all mass at 1, or a spike at one value, would be "
                       "degenerate."), height=700)
    man.append(C.write(fig, out, "v3_03_subburst_count"))

    # ---------------------------------------------------------------- 04 the Arm A test
    fig = make_subplots(rows=1, cols=2, horizontal_spacing=0.09,
                        subplot_titles=["vs T=0 print count (failure row 1)",
                                        "vs session duration"])
    for ci, (xcol, xlab) in enumerate(
            (("n_prints_t0", "T=0 print count (log)"),
             ("print_span_seconds", "session activity duration, s (log)")), 1):
        for obs in OBS:
            s = pe[pe["observable"] == obs]
            fig.add_trace(go.Scatter(
                x=s[xcol], y=np.maximum(s["n_subbursts"], 0.5), mode="markers",
                name=f"{OBS[obs]} (n={len(s)})", legendgroup=obs, showlegend=(ci == 1),
                marker=dict(color=OC[obs], size=8, opacity=0.65,
                            line=dict(color=C.SURFACE, width=1)),
                customdata=s[COHORT_KEY].to_numpy(),
                hovertemplate="%{customdata[0]} %{customdata[1]}<br>x %{x:,.4g}"
                              "<br>%{y:,.0f} sub-bursts<extra></extra>"), row=1, col=ci)
            m = (s[xcol] > 0) & (s["n_subbursts"] > 0)
            if m.sum() > 5:
                b, a = np.polyfit(np.log10(s.loc[m, xcol]), np.log10(s.loc[m, "n_subbursts"]), 1)
                xs = np.linspace(np.log10(s.loc[m, xcol].min()), np.log10(s.loc[m, xcol].max()), 20)
                fig.add_trace(go.Scatter(x=10 ** xs, y=10 ** (a + b * xs), mode="lines",
                                         line=dict(color=OC[obs], width=2.5),
                                         name=f"{OBS[obs]} slope {b:+.3f}", legendgroup=obs,
                                         hoverinfo="skip"), row=1, col=ci)
        if ci == 1:
            x0 = pe["n_prints_t0"].min()
            xs = np.linspace(np.log10(x0), np.log10(pe["n_prints_t0"].max()), 20)
            fig.add_trace(go.Scatter(x=10 ** xs, y=10 ** (0.2 + 0.85 * (xs - np.log10(x0))),
                                     mode="lines", line=dict(color="#b03a3a", width=2, dash="dash"),
                                     name="Arm A reference slope 0.85", hoverinfo="skip"),
                          row=1, col=ci)
        fig.update_xaxes(type="log", title_text=xlab, row=1, col=ci)
        fig.update_yaxes(type="log", title_text="sub-bursts per event (log)", row=1, col=ci)
    r1 = t24["failure_row_1"]["rows"]
    C.finish(fig, "04 — Is the count real or a print-count artifact?",
             "The Arm A test. Arm A's burst count correlated +0.96 with print count at log-log "
             "slope 0.85; its reference slope is drawn in red.",
             C.caption("pooled analysis cohort, n=100 events", "T=0 only", chash,
                       "<b>FAILURE ROW 1 PASSES.</b> " + " · ".join(
                           f"{r['observable']}: Spearman {r['spearman_vs_print_count']:+.4f} "
                           f"(≤0.50), slope {r['loglog_slope']:+.4f} (≤0.35)" for r in r1) +
                       "<br>Slope against session DURATION is "
                       f"{t24['t4_arm_a_test']['pooled']['print_rate']['session_duration_seconds']['loglog_slope']:+.3f} "
                       f"(print) / "
                       f"{t24['t4_arm_a_test']['pooled']['volume_rate']['session_duration_seconds']['loglog_slope']:+.3f} "
                       "(volume) — several times the slope against print count. Count scales with "
                       "how long activity lasts, not with how many prints it contains."
                       "<br><b>Reads:</b> a slope near the red line would be the same defect in a "
                       "new method."))
    man.append(C.write(fig, out, "v3_04_subburst_count_vs_prints"))

    # ---------------------------------------------------------------- 05 duration & spacing
    fig = make_subplots(rows=1, cols=2, horizontal_spacing=0.09,
                        subplot_titles=["sub-burst duration", "inter-sub-burst spacing"])
    for ci, col in enumerate(("duration_seconds", "spacing_seconds"), 1):
        for obs in OBS:
            for sname, scol in SC.items():
                v = ps.loc[(ps["observable"] == obs) & (ps["segment"] == sname), col].dropna()
                if not len(v):
                    continue
                x, y = C.ecdf(np.maximum(v, 1e-3))
                fig.add_trace(go.Scatter(x=x, y=y, mode="lines",
                                         line=dict(color=OC[obs], width=2,
                                                   dash="solid" if sname == "rth" else "dash"),
                                         name=f"{OBS[obs]} / {sname} (n={len(v):,})",
                                         showlegend=(ci == 1),
                                         hovertemplate="%{x:,.4g}s<br>cum %{y:.3f}<extra></extra>"),
                              row=1, col=ci)
        for sname, scol in SC.items():
            kn = gate["segment_fits"]["print_rate"][sname]["fit"]["knee_seconds"]
            fig.add_vline(x=kn, line=dict(color=scol, width=1.5, dash="dot"),
                          annotation_text=f"{sname} knee {kn:g}s", annotation_position="top",
                          annotation_font=dict(size=10, color=scol), row=1, col=ci)
        fig.update_xaxes(type="log", title_text=f"{col.replace('_',' ')} (log)", row=1, col=ci)
        fig.update_yaxes(title_text="cumulative share", range=[0, 1.02], row=1, col=ci)
    r4 = [r for r in t5["t5d_failure_criteria"]["rows"] if r["row"] == 4]
    C.finish(fig, "05 — What timescale do sub-bursts live at?",
             "Duration and spacing ECDFs by observable and segment, with each segment's T1 knee "
             "marked. Log x.",
             C.caption("pooled analysis cohort, n=100 events", "T=0 only", chash,
                       "<b>FAILURE ROW 4: print rate FAILS.</b> " + " · ".join(
                           f"{r['observable']} median duration "
                           f"{r['observed']['median_duration_over_floor']:.4f}x the minimum-duration "
                           f"floor ({r['observed']['floor_s']:.3g}s), required > 1.25x" for r in r4) +
                       "<br><b>Reads:</b> duration piled at the rule's own floor means the floor is "
                       "generating the answer."))
    man.append(C.write(fig, out, "v3_05_subburst_duration_spacing"))

    # ---------------------------------------------------------------- 06 move share
    fig = make_subplots(rows=1, cols=2, column_widths=[0.55, 0.45], horizontal_spacing=0.10,
                        subplot_titles=["All sub-bursts — share of session move",
                                        "Timing relative to detection"])
    n_und = {}
    for obs in OBS:
        s = ps[ps["observable"] == obs]
        n_und[obs] = int(s["move_share"].isna().sum())
        x, y = C.ecdf(s["move_share"])
        fig.add_trace(go.Scatter(x=x, y=y, mode="lines", line=dict(color=OC[obs], width=2),
                                 name=f"{OBS[obs]} (n={len(s):,})",
                                 hovertemplate="%{x:,.4g}<br>cum %{y:.3f}<extra></extra>"),
                      row=1, col=1)
        v = s["seconds_from_detection"].dropna()
        x, y = C.ecdf(v)
        fig.add_trace(go.Scatter(x=x, y=y, mode="lines", line=dict(color=OC[obs], width=2),
                                 name=f"{OBS[obs]} (n={len(v):,})", showlegend=False,
                                 hovertemplate="%{x:,.4g}s<br>cum %{y:.3f}<extra></extra>"),
                      row=1, col=2)
    fig.add_vline(x=0, line=dict(color=C.GRID, width=1), row=1, col=1)
    fig.add_vline(x=0, line=dict(color="#b03a3a", width=2), annotation_text="detection",
                  annotation_position="top", annotation_font=dict(size=10, color="#b03a3a"),
                  row=1, col=2)
    fig.update_xaxes(title_text="sub-burst share of session move (signed)", range=[-1, 1],
                     rangeslider=dict(visible=True, thickness=0.05), row=1, col=1)
    fig.update_yaxes(title_text="cumulative share of sub-bursts", range=[0, 1.02], row=1, col=1)
    fig.update_xaxes(title_text="seconds from detection to sub-burst start (signed)", row=1, col=2)
    fig.update_yaxes(range=[0, 1.02], row=1, col=2)
    rk = t5["t5c_segment_conditioned"]["print_rate"]["pooled"]["move_share_by_rank"]
    C.finish(fig, "06 — Do sub-bursts carry the move?",
             "Per-sub-burst share of the T=0 session move (signed, unclipped), and sub-burst start "
             "time relative to the D7 detection anchor.",
             C.caption("pooled analysis cohort, n=100 events", "T=0 only", chash,
                       f"Undefined denominator: print {n_und['print_rate']}, "
                       f"volume {n_und['volume_rate']} sub-bursts (session move exactly 0). "
                       f"Largest sub-burst median share {rk['rank_1']['q50']:.3f}, "
                       f"2nd {rk['rank_2']['q50']:.3f}, 3rd {rk['rank_3']['q50']:.3f} (print). "
                       "Left panel opens at ±1; drag the slider for the full extent — nothing clipped."
                       "<br><b>Reads:</b> uniformly small shares would mean sub-bursts aren't where "
                       "the move happens."))
    man.append(C.write(fig, out, "v3_06_subburst_move_share"))

    n_ok = sum(m["kaleido_verified"] for m in man)
    write_json(os.path.join(art, "v3_t6_chart_manifest.json"),
               {"phase": "10", "version": "v3", "task": "T6", "config_hash": chash,
                "n_charts": len(man), "n_kaleido_verified": n_ok,
                "all_verified": n_ok == len(man), "charts": man,
                "note": "produced under a partial failure (rows 2, 3, 4)",
                "source": "research/phase_10/v3_t6_charts.py:main"})
    print(f"kaleido-verified {n_ok}/{len(man)}")
    return 0 if n_ok == len(man) else 1


if __name__ == "__main__":
    raise SystemExit(main())
