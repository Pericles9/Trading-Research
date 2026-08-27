"""
Phase 10d T4c-T4e -- break-cause census, per-object and per-event description, and
sub-burst timing against the D7 detection anchor and the event peak. Charts 03 and 04.

D7 POLL INTERVAL: 10c's committed detection_anchor_variant is `poll0` -- a 0-second poll
interval. It is stated on every detection-anchored figure and in every table row here,
per D7, and is read from config/phase_10c.json rather than assumed.

Usage: .venv/Scripts/python.exe research/phase_10d/t4_descriptive.py
"""
from __future__ import annotations

import hashlib
import json
import os
import sys

import numpy as np
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
SEGCOL = {"rth": C.ARM_A, "premarket": C.ARM_B, "evening": C.SIDECAR,
          "unlabelled": C.ROWCAP}


def conf():
    with open(os.path.join(ROOT, "config", "phase_10d.json"), encoding="utf-8") as f:
        return json.load(f)


def chash_of(d):
    return hashlib.sha256(json.dumps(d, sort_keys=True).encode()).hexdigest()[:8]


def main() -> int:
    C10D = conf()
    chash = chash_of(C10D)
    with open(os.path.join(ROOT, "config", "phase_10c.json"), encoding="utf-8") as f:
        cfg10c = json.load(f)
    poll = cfg10c["data"]["detection_anchor_variant"]
    poll_s = int(poll.replace("poll", ""))

    sb = pd.read_parquet(os.path.join(ART, "t4_subbursts.parquet"))
    bc = pd.read_parquet(os.path.join(ART, "t4_break_cause.parquet"))
    ctx = pd.read_parquet(os.path.join(ART, "t4_variant_context.parquet"))
    KP = C10D["upstream_10c"]["kernel_primary_min"]

    ref = sb[(sb.K == 0) & (sb.d == 0.0) & (sb.min_prints == 2)
             & (sb.sep == "hard_break")].copy()

    # ---------------------------------------------------------- T4c summary
    bcs = bc.groupby("kernel_min").agg(
        cells=("n_breaks", "size"), runs=("n_runs", "sum"), breaks=("n_breaks", "sum"),
        iv_above=("intervals_above_threshold", "sum"),
        iv_okfalse=("intervals_ok_false", "sum"),
        br_above=("breaks_above_threshold_only", "sum"),
        br_okfalse=("breaks_ok_false_involved", "sum")).reset_index()
    bcs["break_okfalse_share"] = bcs.br_okfalse / bcs.breaks
    bcs["interval_okfalse_share"] = bcs.iv_okfalse / (bcs.iv_above + bcs.iv_okfalse)

    # per segment: join the reference variant's segment labels onto each cell
    bc_seg = []
    for v in C10D["upstream_10c"]["variants"]:
        cv = ctx[ctx.variant == v][KEY + ["segment"]]
        j = bc.merge(cv, on=KEY, how="left")
        j["segment"] = j.segment.fillna("unlabelled")
        for (k, s), g in j.groupby(["kernel_min", "segment"]):
            bc_seg.append({"variant": float(v), "kernel_min": float(k), "segment": s,
                           "cells": int(len(g)), "breaks": int(g.n_breaks.sum()),
                           "breaks_ok_false_involved": int(g.breaks_ok_false_involved.sum()),
                           "break_okfalse_share": float(g.breaks_ok_false_involved.sum()
                                                        / max(g.n_breaks.sum(), 1)),
                           "intervals_ok_false": int(g.intervals_ok_false.sum()),
                           "intervals_above_threshold": int(g.intervals_above_threshold.sum())})
    bc_seg = pd.DataFrame(bc_seg)
    bc_seg.to_parquet(os.path.join(ART, "t4_break_cause_by_segment.parquet"), index=False)

    # ---------------------------------------------------------- T4d per-event
    ev_rows = []
    for (t, dt, k), g in ref.groupby(KEY + ["kernel_min"]):
        g = g.sort_values("start_ns")
        gaps = (g.start_ns.to_numpy()[1:] - g.end_ns.to_numpy()[:-1]) / 1e9
        top = np.sort(g.move_share.to_numpy())[::-1]
        ev_rows.append({
            "ticker": t, "event_date_canonical": dt, "kernel_min": float(k),
            "n_subbursts": int(len(g)),
            "spacing_median_s": float(np.median(gaps)) if gaps.size else np.nan,
            "spacing_q25_s": float(np.quantile(gaps, .25)) if gaps.size else np.nan,
            "spacing_q75_s": float(np.quantile(gaps, .75)) if gaps.size else np.nan,
            "move_share_1st": float(top[0]) if top.size > 0 else np.nan,
            "move_share_2nd": float(top[1]) if top.size > 1 else np.nan,
            "move_share_3rd": float(top[2]) if top.size > 2 else np.nan,
            "move_share_top3": float(top[:3].sum()) if top.size else np.nan,
            "move_share_all": float(g.move_share.sum()),
            "duration_median_s": float(g.duration_s.median()),
            "prints_in_bursts": int(g.n_prints.sum()),
        })
    ev = pd.DataFrame(ev_rows)
    ev.to_parquet(os.path.join(ART, "t4_event_summary.parquet"), index=False)

    # ---------------------------------------------------------- T4e timing
    tim_rows = []
    for v in C10D["upstream_10c"]["variants"]:
        # peak_ns already rides on every sub-burst row; take only segment+det_ns
        # from ctx so the merge does not produce peak_ns_x / peak_ns_y.
        cv = ctx[ctx.variant == v][KEY + ["segment", "det_ns"]]
        j = ref.merge(cv, on=KEY, how="left")
        j["segment"] = j.segment.fillna("unlabelled")
        j["t_vs_anchor_s"] = (j.start_ns - j.det_ns) / 1e9
        j["t_vs_peak_s"] = (j.start_ns - j.peak_ns) / 1e9
        for (k, s), g in j.groupby(["kernel_min", "segment"]):
            a = g.t_vs_anchor_s.dropna().to_numpy()
            p = g.t_vs_peak_s.dropna().to_numpy()
            tim_rows.append({
                "variant": float(v), "kernel_min": float(k), "segment": s,
                "detection_anchor_variant": poll, "poll_interval_s": poll_s,
                "n_subbursts": int(len(g)),
                "n_with_anchor": int(a.size),
                "anchor_median_s": float(np.median(a)) if a.size else np.nan,
                "anchor_q25_s": float(np.quantile(a, .25)) if a.size else np.nan,
                "anchor_q75_s": float(np.quantile(a, .75)) if a.size else np.nan,
                "share_before_anchor": float((a < 0).mean()) if a.size else np.nan,
                "peak_median_s": float(np.median(p)) if p.size else np.nan,
                "share_before_peak": float((p < 0).mean()) if p.size else np.nan})
    tim = pd.DataFrame(tim_rows)
    tim.to_parquet(os.path.join(ART, "t4_timing.parquet"), index=False)

    # ============================================================ chart 03
    fig = make_subplots(rows=1, cols=2, column_widths=[0.42, 0.58], subplot_titles=[
        "Run breaks by cause — share involving an ok=False interval",
        "Break-cause split per segment (variant 1.25 / 1.30 / 1.35 pooled per segment)"],
        horizontal_spacing=0.1)
    fig.add_trace(go.Bar(
        x=[f"{k:g} min" for k in bcs.kernel_min], y=bcs.break_okfalse_share,
        name="breaks involving ok=False", marker_color=C.ROWCAP, width=0.45,
        text=[f"{v:.2%}<br>{int(n):,}/{int(b):,}" for v, n, b
              in zip(bcs.break_okfalse_share, bcs.br_okfalse, bcs.breaks)],
        textposition="outside", textfont=dict(size=10),
        hovertemplate="kernel %{x}<br>%{y:.3%}<extra></extra>"), row=1, col=1)
    fig.update_xaxes(title_text="kernel", row=1, col=1)
    fig.update_yaxes(title_text="share of run breaks", tickformat=".1%",
                     range=[0, float(bcs.break_okfalse_share.max()) * 1.55], row=1, col=1)

    segs = ["premarket", "rth", "evening", "unlabelled"]
    for k in C10D["upstream_10c"]["kernels_min"]:
        s = bc_seg[bc_seg.kernel_min == k].groupby("segment").agg(
            br=("breaks", "sum"), bo=("breaks_ok_false_involved", "sum")).reindex(segs)
        fig.add_trace(go.Bar(
            x=segs, y=(s.bo / s.br).values, name=f"kernel {k:g} min",
            marker_color=KCOL[k],
            text=[("" if not np.isfinite(v) else f"{v:.2%}") for v in (s.bo / s.br).values],
            textposition="outside", textfont=dict(size=9),
            customdata=np.stack([s.bo.values, s.br.values], axis=-1),
            hovertemplate=("%{x}<br>%{y:.3%}<br>%{customdata[0]:,} of "
                           "%{customdata[1]:,} breaks<extra></extra>")), row=1, col=2)
    fig.update_xaxes(title_text="segment", row=1, col=2)
    fig.update_yaxes(title_text="share of run breaks involving ok=False",
                     tickformat=".1%", row=1, col=2)

    tot_br = int(bcs.breaks.sum()); tot_bo = int(bcs.br_okfalse.sum())
    cap = C.caption(
        sample=(f"130 ok (event, kernel) cells, {int(bcs.runs.sum()):,} raw runs, "
                f"{tot_br:,} run breaks. Reference cell K=0, d=0, min_prints=2, "
                f"sep=hard_break — 10c's rule exactly."),
        filters="label = 'ok' cells only; insufficient_context cells emit no runs.",
        chash=chash,
        extra=(f"<b>First measurement in the programme of this split.</b> A run break is "
               f"caused either by an interval AT OR ABOVE THRESHOLD — a real gap — or by "
               f"one FAILING THE ok MASK,<br>where the centered window held fewer intervals "
               f"than the per-event derived floor and no trustworthy normalized value "
               f"exists. The second is a data-quality artifact,<br>not market behaviour.<br>"
               f"<b>Observed: {tot_bo:,} of {tot_br:,} breaks ({tot_bo/tot_br:.2%}) involve "
               f"an ok=False interval.</b> At interval level the ok=False share is "
               f"{bcs.iv_okfalse.sum()/(bcs.iv_above.sum()+bcs.iv_okfalse.sum()):.1%}, higher "
               f"because<br>those intervals cluster inside long separator runs that break a "
               f"single time. No threshold is attached to this row — it is description."))
    C.finish(fig, "Chart 03 — Why is each run break there?",
             "Phase 10d T4c · real gap versus thin window, per kernel and per segment",
             cap, height=780, width=1340)
    m3 = C.write(fig, OUT, "03_break_cause")

    # ============================================================ chart 04
    fig = make_subplots(rows=2, cols=2, subplot_titles=[
        f"Sub-burst duration (s), ECDF — reference cell, kernel {KP:g} min",
        "Spacing between consecutive sub-bursts (s), ECDF",
        "Move share carried by the largest / 2nd / 3rd sub-burst, per event",
        f"Sub-burst start vs the D7 detection anchor ({poll}, poll interval {poll_s} s)"],
        vertical_spacing=0.16, horizontal_spacing=0.10)

    cv = ctx[ctx.variant == 1.25][KEY + ["segment", "det_ns"]]
    r8 = ref[ref.kernel_min == KP].merge(cv, on=KEY, how="left")
    r8["segment"] = r8.segment.fillna("unlabelled")
    for s in segs:
        g = r8[r8.segment == s]
        if not len(g):
            continue
        fig.add_trace(C.ecdf_trace(g.duration_s, s, SEGCOL[s], legendgroup=s),
                      row=1, col=1)
    fig.update_xaxes(type="log", title_text="duration (s), log", row=1, col=1)
    fig.update_yaxes(title_text="cumulative share", row=1, col=1)

    e8 = ev[ev.kernel_min == KP].merge(ctx[ctx.variant == 1.25][KEY + ["segment"]],
                                       on=KEY, how="left")
    e8["segment"] = e8.segment.fillna("unlabelled")
    for s in segs:
        g = e8[e8.segment == s]
        if not len(g):
            continue
        fig.add_trace(C.ecdf_trace(g.spacing_median_s, s, SEGCOL[s], legendgroup=s,
                                   showlegend=False), row=1, col=2)
    fig.update_xaxes(type="log", title_text="per-event median spacing (s), log", row=1, col=2)
    fig.update_yaxes(title_text="cumulative share of events", row=1, col=2)

    for i, col in enumerate(["move_share_1st", "move_share_2nd", "move_share_3rd"]):
        a = e8[col].dropna()
        fig.add_trace(go.Box(y=a, name=["largest", "2nd", "3rd"][i],
                             marker_color=[C.ARM_A, C.ARM_B, C.SIDECAR][i],
                             boxpoints="all", jitter=0.5, pointpos=0, showlegend=False,
                             marker=dict(size=4, opacity=0.6),
                             hovertemplate="%{y:.4f}<extra></extra>"), row=2, col=1)
    n_tiny = int((e8[["move_share_1st", "move_share_2nd", "move_share_3rd"]]
                  .to_numpy() < 1e-9).sum())
    fig.update_yaxes(type="log", title_text=f"share of session move (n={len(e8)} events)",
                     row=2, col=1)
    C.n_note(fig, f"{n_tiny} of {len(e8)*3} points below 1e-9 —<br>sub-bursts whose net "
                  f"price change is<br>~0. Shown, never clipped, which is<br>why the "
                  f"whiskers reach 1e-18.",
             x=0.02, y=0.30, row=2, col=1, xref="paper", yref="paper")

    for s in segs:
        g = r8[r8.segment == s]
        a = ((g.start_ns - g.det_ns) / 1e9).dropna()
        if not len(a):
            continue
        fig.add_trace(C.ecdf_trace(a, s, SEGCOL[s], legendgroup=s, showlegend=False),
                      row=2, col=2)
    fig.add_vline(x=0, line=dict(color=C.INK, width=1.5, dash="dash"), row=2, col=2)
    fig.update_xaxes(title_text="seconds from detection anchor (negative = before)",
                     row=2, col=2)
    fig.update_yaxes(title_text="cumulative share", row=2, col=2)

    cap = C.caption(
        sample=(f"Reference cell K=0, d=0, min_prints=2, sep=hard_break — 10c's rule "
                f"exactly. Kernel {KP:g} min (D5, primary); segment labels from variant "
                f"1.25.<br>n = {len(r8):,} sub-bursts across {len(e8)} events. "
                f"Outliers shown, never clipped."),
        filters="label = 'ok' cells only.",
        chash=chash,
        extra=(f"<b>D7:</b> the detection anchor is <b>{poll}</b> — poll interval "
               f"<b>{poll_s} s</b>. Stated here because a detection-anchored figure quoted "
               f"without its poll interval is incomplete under D7.<br>"
               f"<b>Segment labels are variant-dependent</b>, so panel 1, 2 and 4 colours "
               f"are variant 1.25's labelling. The objects themselves are "
               f"variant-independent — 10c computes them per (event, kernel) and cross-joins "
               f"the variant's segment/anchor context, and 10d does the same."))
    C.finish(fig, "Chart 04 — What the extracted objects look like",
             "Phase 10d T4d–T4e · duration, spacing, move share and timing at the reference cell",
             cap, height=980, width=1340)
    m4 = C.write(fig, OUT, "04_duration_spacing_moveshare")

    with open(os.path.join(ART, "t4_chart_manifest.json"), "w", encoding="utf-8") as f:
        json.dump({"task": "T4f", "charts": [m3, m4]}, f, indent=2)

    summ = {"phase": "10d", "task": "T4c-T4e", "config_hash": chash,
            "detection_anchor_variant": poll, "poll_interval_s": poll_s,
            "T4c_break_cause_by_kernel": bcs.to_dict("records"),
            "T4c_pooled": {"breaks": tot_br, "breaks_ok_false_involved": tot_bo,
                           "break_okfalse_share": tot_bo / tot_br,
                           "interval_okfalse_share": float(
                               bcs.iv_okfalse.sum() / (bcs.iv_above.sum() + bcs.iv_okfalse.sum()))},
            "T4d_event_summary_artifact": "results/phase_10d/artifacts/t4_event_summary.parquet",
            "T4e_timing_artifact": "results/phase_10d/artifacts/t4_timing.parquet"}
    with open(os.path.join(ART, "t4_descriptive_summary.json"), "w", encoding="utf-8") as f:
        json.dump(summ, f, indent=2, default=str)

    print(f"\nT4c pooled: {tot_bo:,}/{tot_br:,} breaks ({tot_bo/tot_br:.3%}) involve ok=False")
    print(bcs[["kernel_min", "breaks", "br_okfalse", "break_okfalse_share",
               "interval_okfalse_share"]].to_string(index=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
