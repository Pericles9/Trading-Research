"""
Phase 10 v2 T6 -- charts 01-07 per the v2 chart contract.

Produced under a pre-registered FAILURE (rows 1, 2, 3, 6). The prompt requires
the observed values AND the charts be posted on a hard stop; chart 05 is the one
that shows the failure.

Usage: .venv/Scripts/python.exe research/phase_10/v2_t6_charts.py
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
from v2_common import (  # noqa: E402
    COHORT_KEY, POOLED, config_hash_v2, load_config_v2, rel, write_json,
)

OBS = {"print_rate": "print rate", "volume_rate": "share-volume rate"}
OBS_COLOR = {"print_rate": C.ARM_A, "volume_rate": C.ARM_B}
K_COLORS = ["#2a78d6", "#1baf7a", "#eda100", "#eb6834", "#4a3aa7"]


def band(fig, x, lo, hi, color, row=1, col=1):
    rgb = tuple(int(color[i:i + 2], 16) for i in (1, 3, 5))
    fig.add_trace(go.Scatter(
        x=list(x) + list(x)[::-1], y=list(hi) + list(lo)[::-1], fill="toself",
        fillcolor=f"rgba({rgb[0]},{rgb[1]},{rgb[2]},0.13)", line=dict(width=0),
        showlegend=False, hoverinfo="skip"), row=row, col=col)


def profile_chart(prof, cfg, chash, out, anchor, name, title, sub, reads):
    k_ref = cfg["estimator"]["k_reference"]
    fig = make_subplots(rows=1, cols=2, horizontal_spacing=0.09,
                        subplot_titles=[OBS["print_rate"], OBS["volume_rate"]])
    ns = {}
    for ci, obs in enumerate(OBS, 1):
        p = prof[(prof["anchor"] == anchor) & (prof["observable"] == obs)
                 & (prof["k"] == k_ref) & prof["cohort_group"].isin(POOLED)]
        if not len(p):
            continue
        g = p.groupby("t_seconds")["normalized_rate"]
        q = g.quantile([0.25, 0.5, 0.75]).unstack()
        n = g.size()
        ns[obs] = (int(p[COHORT_KEY].drop_duplicates().shape[0]), int(len(p)))
        x = q.index.to_numpy()
        band(fig, x, q[0.25], q[0.75], OBS_COLOR[obs], 1, ci)
        fig.add_trace(go.Scatter(
            x=x, y=q[0.5], mode="lines", line=dict(color=OBS_COLOR[obs], width=2.5),
            name=f"{OBS[obs]} median (n={ns[obs][0]} events)",
            customdata=n.to_numpy(),
            hovertemplate="t=%{x:,.3g}s<br>median %{y:.3f}<br>n events %{customdata}<extra></extra>",
        ), row=1, col=ci)
        fig.add_vline(x=0, line=dict(color=C.INK2, width=1.2, dash="dot"), row=1, col=ci)
        fig.update_xaxes(title_text=f"seconds since {anchor} (symmetric log)", type="log",
                         row=1, col=ci)
    fig.update_yaxes(title_text="rate / that event's own peak rate", range=[0, 1.02], row=1, col=1)
    C.finish(fig, title, sub,
             C.caption(f"pooled analysis cohort, n=100 events; k={k_ref}, as_is tie variant",
                       f"T=0 only; curves self-normalized by each event's own peak (D6)",
                       chash,
                       "Symmetric-log x: negative side is time BEFORE the anchor. "
                       f"<br><b>Reads:</b> {reads}"))
    return C.write(fig, out, name)


def main() -> int:
    cfg = load_config_v2()
    chash = config_hash_v2()
    art = rel(cfg["paths"]["out_artifacts"])
    out = rel(cfg["paths"]["out_charts"])
    k_grid, k_ref = cfg["estimator"]["k_grid"], cfg["estimator"]["k_reference"]
    polls = cfg["detection_anchor"]["poll_intervals_seconds"]

    m = pd.read_parquet(os.path.join(art, "v2_t1_event_metrics.parquet"))
    m["event_date_canonical"] = m["event_date_canonical"].astype(str)
    m["k_exceeds_n"] = m["k_exceeds_n"].fillna(False).astype(bool)
    m["decay_half_never"] = m["decay_half_never"].fillna(True).astype(bool)
    prof = pd.read_parquet(os.path.join(art, "v2_t1_profiles.parquet"))
    prof["event_date_canonical"] = prof["event_date_canonical"].astype(str)
    t5 = json.load(open(os.path.join(art, "v2_t5_stability.json"), encoding="utf-8"))

    asis = m[(m["tie_variant"] == "as_is") & (~m["k_exceeds_n"]) & m["cohort_group"].isin(POOLED)]
    ref = asis[asis["k"] == k_ref]
    man = []

    # ---------------------------------------------------------------- 01, 02
    man.append(profile_chart(
        prof, cfg, chash, out, "peak", "v2_01_profile_peak_anchored",
        "01 — What shape does intensity have around its peak?",
        "Self-normalized rate against time since peak. Median plus interquartile band. "
        "Peak is RETROSPECTIVE by construction — it uses the whole session.",
        "a flat band would mean no common shape, so no timescale exists."))
    man.append(profile_chart(
        prof, cfg, chash, out, "detection", "v2_02_profile_detection_anchored",
        "02 — What does it look like from the moment you could have known?",
        "Same curves, anchored at the D7 derived detection time (1s poll, threshold 1.30). "
        "Detection is a price-threshold crossing; peak is an intensity maximum; both come from the "
        "same T=0 tick stream and are not independently sourced.",
        "the peak already passed at t=0 for most events means the runway is gone before detection."))

    # ---------------------------------------------------------------- 03
    fig = go.Figure()
    caps = []
    for obs in OBS:
        for pi, p in enumerate(polls):
            v = ref.loc[ref["observable"] == obs, f"det_to_peak_s_poll{p}"].dropna()
            if not len(v):
                continue
            neg = float((v < 0).mean())
            if p in (0, 1, 60):
                lbl = ("instantaneous (UPPER BOUND, impossible)" if p == 0 else f"{p}s poll")
                x, y = C.ecdf(v)
                fig.add_trace(go.Scatter(
                    x=x, y=y, mode="lines", name=f"{OBS[obs]} — {lbl} (n={len(v)})",
                    line=dict(color=OBS_COLOR[obs], width=2,
                              dash={0: "dot", 1: "solid", 60: "dash"}[p]),
                    hovertemplate="%{x:,.4g}s<br>cum %{y:.3f}<extra></extra>"))
            if p == 1:
                caps.append(f"{OBS[obs]} @1s poll: <b>{neg:.1%} negative</b> "
                            f"({int((v < 0).sum())}/{len(v)} events, peak preceded detection); "
                            f"median {v.median():,.0f}s")
    fig.add_vline(x=0, line=dict(color="#b03a3a", width=2),
                  annotation_text="detection", annotation_position="top",
                  annotation_font=dict(size=10.5, color="#b03a3a"))
    fig.update_xaxes(title_text="detection → peak, seconds (signed; negative = peak BEFORE detection)")
    fig.update_yaxes(title_text="cumulative share of events", range=[0, 1.02])
    C.finish(fig, "03 — How much runway is there?",
             "Signed detection-to-peak. A FAMILY indexed by polling interval, not one distribution "
             "(D7). Nothing is clipped, excluded or absolute-valued.",
             C.caption("pooled analysis cohort, n=100 events; k=50, threshold 1.30",
                       "T=0 only; never-crossing events have no detection and are excluded here, "
                       "counted in the report", chash,
                       "<br>".join(caps) +
                       "<br><b>Reads:</b> mass at or below zero means the runway is gone before "
                       "detection."))
    man.append(C.write(fig, out, "v2_03_detection_to_peak"))

    # ---------------------------------------------------------------- 04
    fig = go.Figure()
    labs = cfg["timescales"]["decay_fraction_labels"]
    dash = {"half": "solid", "one_over_e": "dash", "one_tenth": "dot"}
    caps = []
    for obs in OBS:
        s = ref[ref["observable"] == obs]
        for lab in labs:
            never = s[f"decay_{lab}_never"].fillna(True).astype(bool)
            v = s.loc[~never, f"decay_{lab}_s"].dropna()
            if not len(v):
                continue
            x, y = C.ecdf(np.maximum(v, 1e-3))
            fig.add_trace(go.Scatter(
                x=x, y=y, mode="lines", name=f"{OBS[obs]} — to {lab} (n={len(v)})",
                line=dict(color=OBS_COLOR[obs], width=2, dash=dash[lab]),
                hovertemplate="%{x:,.4g}s<br>cum %{y:.3f}<extra></extra>"))
            caps.append(f"{OBS[obs]} to {lab}: n={len(v)}, never-reached {int(never.sum())}")
    fig.update_xaxes(type="log", title_text="seconds from peak until the curve falls below the "
                                            "fraction and STAYS below (log)")
    fig.update_yaxes(title_text="cumulative share of events", range=[0, 1.02])
    C.finish(fig, "04 — How fast does participation decay?",
             "Time from peak until the self-normalized curve falls to the fraction and stays below "
             "it for the remainder of the in-window session.",
             C.caption("pooled analysis cohort, n=100 events; k=50, as_is", "T=0 only", chash,
                       "<br>".join(caps) +
                       "<br><b>Reads:</b> timescales at the window edge would be truncation, not "
                       "decay."))
    man.append(C.write(fig, out, "v2_04_decay_timescale"))

    # ---------------------------------------------------------------- 05  (the failure)
    fig = make_subplots(rows=1, cols=2, horizontal_spacing=0.09,
                        subplot_titles=[OBS["print_rate"], OBS["volume_rate"]])
    for ci, obs in enumerate(OBS, 1):
        w = asis[(asis["observable"] == obs) & (~asis["decay_half_never"])].pivot_table(
            index=COHORT_KEY, columns="k", values="decay_half_s")
        for _, rr in w.iterrows():
            kk = [k for k in k_grid if k in rr.index and np.isfinite(rr[k])]
            if len(kk) < 2:
                continue
            fig.add_trace(go.Scatter(
                x=kk, y=[rr[k] for k in kk], mode="lines",
                line=dict(color="rgba(120,120,116,0.20)", width=1),
                showlegend=False, hoverinfo="skip"), row=1, col=ci)
        med = [t5["t5a_resolution"][obs]["pooled_median_decay_half_per_k"][f"k{k}"]["q50"] for k in k_grid]
        nn = [t5["t5a_resolution"][obs]["pooled_median_decay_half_per_k"][f"k{k}"]["n"] for k in k_grid]
        fig.add_trace(go.Scatter(
            x=k_grid, y=med, mode="lines+markers", line=dict(color=OBS_COLOR[obs], width=3),
            marker=dict(size=11), name=f"{OBS[obs]} pooled median",
            customdata=nn,
            hovertemplate="k=%{x}<br>median %{y:,.4g}s<br>n=%{customdata}<extra></extra>"),
            row=1, col=ci)
        fig.update_xaxes(type="log", title_text="k (log)", row=1, col=ci)
    fig.update_yaxes(type="log", title_text="decay-to-half, seconds (log)", row=1, col=1)
    fig.update_yaxes(type="log", row=1, col=2)
    r1 = [r for r in t5["t5d_failure_criteria"]["rows"] if r["row"] == 1]
    C.finish(fig, "05 — Is the answer a property of the market or of the estimator?",
             "Decay-to-half against the estimator's resolution k. Grey lines are individual events; "
             "coloured line is the pooled median. Both axes log.",
             C.caption("pooled analysis cohort, n=100 events; as_is tie variant", "T=0 only", chash,
                       "<b>FAILURE ROW 1 FIRED.</b> " + " · ".join(
                           f"{r['observable']} k{max(k_grid)}/k{min(k_grid)} ratio "
                           f"{r['observed']:.4f} vs band [0.333, 3.0] — FAIL" for r in r1) +
                       "<br><b>Reads:</b> a straight sloped line means the timescale is just "
                       "tracking resolution. Observed here is worse than sloped — it is "
                       "non-monotonic across k."))
    man.append(C.write(fig, out, "v2_05_resolution_stability"))

    # ---------------------------------------------------------------- 06
    fig = make_subplots(rows=1, cols=2, column_widths=[0.55, 0.45], horizontal_spacing=0.10,
                        subplot_titles=["Decay-to-half vs absolute peak rate",
                                        "Decay-to-half by absolute-peak-rate quartile"])
    for obs in OBS:
        s = ref[(ref["observable"] == obs) & (~ref["decay_half_never"])]
        fig.add_trace(go.Scatter(
            x=s["peak_rate_abs"], y=s["decay_half_s"], mode="markers",
            name=f"{OBS[obs]} (n={len(s)})",
            marker=dict(color=OBS_COLOR[obs], size=8, opacity=0.65,
                        line=dict(color=C.SURFACE, width=1)),
            customdata=s[COHORT_KEY].to_numpy(),
            hovertemplate="%{customdata[0]} %{customdata[1]}<br>peak rate %{x:,.4g}/s"
                          "<br>decay-half %{y:,.4g}s<extra></extra>"), row=1, col=1)
        q = t5["t4_level_conditioning"][obs]["by_absolute_peak_rate_quartile"]
        for qi in sorted(q):
            sub = s[pd.qcut(s["peak_rate_abs"].rank(method="first"), 4, labels=False) == int(qi)]
            fig.add_trace(go.Box(
                y=sub["decay_half_s"], x=[f"Q{int(qi)+1}"] * len(sub),
                name=f"{OBS[obs]} Q{int(qi)+1} (n={len(sub)})", showlegend=False,
                marker=dict(color=OBS_COLOR[obs], size=5, opacity=0.6),
                line=dict(color=OBS_COLOR[obs], width=2), fillcolor="rgba(0,0,0,0)",
                boxpoints="all", jitter=0.5, pointpos=0, offsetgroup=obs,
                hovertemplate=f"{OBS[obs]} Q{int(qi)+1}<br>%{{y:,.4g}}s<extra></extra>"),
                row=1, col=2)
    fig.update_xaxes(type="log", title_text="absolute peak rate (per second, log)", row=1, col=1)
    fig.update_yaxes(type="log", title_text="decay-to-half, seconds (log)", row=1, col=1)
    fig.update_xaxes(title_text="absolute-peak-rate quartile", row=1, col=2)
    fig.update_yaxes(type="log", title_text="decay-to-half, seconds (log)", row=1, col=2)
    r3 = [r for r in t5["t5d_failure_criteria"]["rows"] if r["row"] == 3]
    C.finish(fig, "06 — Does shape depend on absolute level?",
             "Self-normalization discards absolute level. This is the test of whether that discard "
             "is safe. Both axes log.",
             C.caption("pooled analysis cohort, n=100 events; k=50, as_is", "T=0 only", chash,
                       "<b>FAILURE ROW 3 FIRED.</b> " + " · ".join(
                           f"{r['observable']} top/bottom quartile ratio {r['observed']:,.2f} "
                           f"(Spearman {r['detail']['spearman']:.3f}) vs band [0.2, 5.0] — FAIL"
                           for r in r3) +
                       "<br><b>Reads:</b> a clean monotone trend means one timescale does not "
                       "exist, only a conditioned family."))
    man.append(C.write(fig, out, "v2_06_level_dependence"))

    # ---------------------------------------------------------------- 07
    a = ref[ref["observable"] == "print_rate"].set_index(COHORT_KEY)
    b = ref[ref["observable"] == "volume_rate"].set_index(COHORT_KEY)
    j = pd.concat([a["decay_half_s"].rename("p"), b["decay_half_s"].rename("v"),
                   a["peak_seconds_from_open"].rename("pp"),
                   b["peak_seconds_from_open"].rename("vp")], axis=1).dropna()
    fig = make_subplots(rows=1, cols=2, column_widths=[0.55, 0.45], horizontal_spacing=0.10,
                        subplot_titles=["Decay-to-half: print rate vs volume rate",
                                        "Peak-location difference |volume − print|"])
    lim = [max(1e-3, min(j["p"].min(), j["v"].min())) * 0.5, max(j["p"].max(), j["v"].max()) * 2]
    fig.add_trace(go.Scatter(x=lim, y=lim, mode="lines",
                             line=dict(color=C.GRID, width=1.5, dash="dash"),
                             name="identity", hoverinfo="skip"), row=1, col=1)
    fig.add_trace(go.Scatter(
        x=j["p"], y=j["v"], mode="markers", name=f"events (n={len(j)})",
        marker=dict(color=C.ARM_A, size=9, opacity=0.7, line=dict(color=C.SURFACE, width=1.2)),
        customdata=j.reset_index()[COHORT_KEY].to_numpy(),
        hovertemplate="%{customdata[0]} %{customdata[1]}<br>print %{x:,.4g}s"
                      "<br>volume %{y:,.4g}s<extra></extra>"), row=1, col=1)
    d = (j["vp"] - j["pp"]).abs()
    x, y = C.ecdf(np.maximum(d, 1e-3))
    fig.add_trace(go.Scatter(x=x, y=y, mode="lines", line=dict(color=C.ARM_B, width=2),
                             name=f"|peak difference| (n={len(d)})",
                             hovertemplate="%{x:,.4g}s<br>cum %{y:.3f}<extra></extra>"),
                  row=1, col=2)
    fig.update_xaxes(type="log", title_text="print-rate decay-to-half (s, log)", row=1, col=1)
    fig.update_yaxes(type="log", title_text="volume-rate decay-to-half (s, log)", row=1, col=1)
    fig.update_xaxes(type="log", title_text="|peak location difference| (s, log)", row=1, col=2)
    fig.update_yaxes(title_text="cumulative share of events", range=[0, 1.02], row=1, col=2)
    sp = t5["t5b_observable_agreement"]["spearman_decay_half"]
    C.finish(fig, "07 — Print rate versus volume rate",
             "The two observables are co-equal, not primary-and-check. Print rate is suspected of "
             "carrying a price-level fragmentation artifact; this is the test.",
             C.caption(f"pooled analysis cohort, n={len(j)} events; k=50, as_is", "T=0 only", chash,
                       f"<b>FAILURE ROW 2 FIRED.</b> Spearman on decay-to-half = {sp:.3f} vs the "
                       f"0.50 floor — FAIL. Peak locations agree within 60s on "
                       f"{t5['t5b_observable_agreement']['n_events_peak_within_60s']}/{len(j)} events."
                       "<br><b>Reads:</b> wide scatter means at least one observable is measuring "
                       "fragmentation rather than participation."))
    man.append(C.write(fig, out, "v2_07_observable_agreement"))

    n_ok = sum(x["kaleido_verified"] for x in man)
    write_json(os.path.join(art, "v2_t6_chart_manifest.json"), {
        "phase": "10", "version": "v2", "task": "T6", "config_hash": chash,
        "n_charts": len(man), "n_kaleido_verified": n_ok, "all_verified": n_ok == len(man),
        "charts": man, "note": "produced under a pre-registered failure (rows 1, 2, 3, 6); the "
                               "prompt requires charts be posted with the observed values",
        "source": "research/phase_10/v2_t6_charts.py:main"})
    print(f"kaleido-verified {n_ok}/{len(man)}")
    return 0 if n_ok == len(man) else 1


if __name__ == "__main__":
    raise SystemExit(main())
