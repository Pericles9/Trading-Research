"""
Phase 10d T5h -- charts 06 to 10.

06  attribution: floor-only vs merge-only vs joint -- which moved duration?
07  n_prints composition: does merging PROMOTE short objects, or does the floor DELETE them?
08  merge surface across K x d x min_prints, degenerate plateau labelled as an artifact
09  kernel and variant consistency
10  count vs print count -- descriptive only, nothing here can fail

Usage: .venv/Scripts/python.exe research/phase_10d/t5_charts.py
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
READCOL = {"identity": C.INK, "floor_only": C.ROWCAP, "merge_only": C.ARM_A,
           "joint": C.SIDECAR}


def main() -> int:
    with open(os.path.join(ROOT, "config", "phase_10d.json"), encoding="utf-8") as f:
        C10D = json.load(f)
    chash = hashlib.sha256(json.dumps(C10D, sort_keys=True).encode()).hexdigest()[:8]
    with open(os.path.join(ART, "t5_attribution.json"), encoding="utf-8") as f:
        S = json.load(f)
    t5a = pd.read_parquet(os.path.join(ART, "t5_attribution_by_kernel.parquet"))
    t5as = pd.read_parquet(os.path.join(ART, "t5_attribution_by_segment.parquet"))
    t5b = pd.read_parquet(os.path.join(ART, "t5_nprints_composition.parquet"))
    var = pd.read_parquet(os.path.join(ART, "t5_variant_consistency.parquet"))
    sb = pd.read_parquet(os.path.join(ART, "t4_subbursts.parquet"))
    cells = pd.read_parquet(os.path.join(ART, "t4_cell_summary.parquet"))
    KP = C10D["upstream_10c"]["kernel_primary_min"]
    KERNELS = C10D["upstream_10c"]["kernels_min"]
    att = S["T5a_attribution"]
    prior = S["prior_version_figures"]
    manifest = []

    # ==================================================================== 06
    fig = make_subplots(rows=2, cols=2, subplot_titles=[
        f"Median duration by read — kernel {KP:g} min, sep=hard_break",
        "Shift from the identity cell, in decades",
        "Duration ECDF — identity vs the extreme of each mechanism",
        "Attribution per segment (kernel 8 min, variant 1.25 labelling)"],
        vertical_spacing=0.155, horizontal_spacing=0.10)

    kp = t5a[t5a.kernel_min == KP]
    order = ["identity", "floor_only", "merge_only", "joint"]
    for rd in order:
        g = kp[kp.read == rd]
        fig.add_trace(go.Box(
            y=g["median"] * 1e3, name=rd, marker_color=READCOL[rd], boxpoints="all",
            jitter=0.4, pointpos=0, showlegend=False, marker=dict(size=6, opacity=0.75),
            customdata=np.stack([g.K, g.d, g.min_prints, g.n_objects], axis=-1),
            hovertemplate=("K=%{customdata[0]} d=%{customdata[1]} mp=%{customdata[2]}"
                           "<br>median %{y:.4f} ms<br>n=%{customdata[3]:,}<extra></extra>")),
            row=1, col=1)
    fig.update_yaxes(type="log", title_text="median sub-burst duration (ms), log",
                     row=1, col=1)

    for rd in order[1:]:
        g = kp[kp.read == rd]
        fig.add_trace(go.Box(y=g.shift_decades, name=rd, marker_color=READCOL[rd],
                             boxpoints="all", jitter=0.4, pointpos=0, showlegend=False,
                             marker=dict(size=6, opacity=0.75),
                             customdata=np.stack([g.K, g.d, g.min_prints], axis=-1),
                             hovertemplate=("K=%{customdata[0]} d=%{customdata[1]} "
                                            "mp=%{customdata[2]}<br>%{y:+.4f} dec"
                                            "<extra></extra>")), row=1, col=2)
    fig.add_hline(y=0, line=dict(color=C.INK, width=1, dash="dash"), row=1, col=2)
    fig.update_yaxes(title_text="shift from identity (decades)", row=1, col=2)

    hb = sb[(sb.sep == "hard_break") & (sb.kernel_min == KP)]
    picks = [("identity (10c's rule)", 0, 0.0, 2, C.INK),
             ("floor only  min_prints=3", 0, 0.0, 3, C.ROWCAP),
             ("floor only  min_prints=5", 0, 0.0, 5, "#8d7ee0"),
             ("merge only  K=5 d=1.0", 5, 1.0, 2, C.ARM_A),
             ("joint  K=5 d=1.0 mp=5", 5, 1.0, 5, C.SIDECAR)]
    for lab, K, d, mp, col in picks:
        g = hb[(hb.K == K) & (hb.d == d) & (hb.min_prints == mp)]
        fig.add_trace(C.ecdf_trace(g.duration_s, lab, col), row=2, col=1)
    fig.update_xaxes(type="log", title_text="duration (s), log", row=2, col=1)
    fig.update_yaxes(title_text="cumulative share", row=2, col=1)

    segs = [s for s in ["premarket", "rth", "evening", "unlabelled"]
            if s in t5as.segment.unique()]
    for rd, col in (("floor_only", C.ROWCAP), ("merge_only", C.ARM_A)):
        ys, xs, ns = [], [], []
        for s in segs:
            g = t5as[(t5as.segment == s) & (t5as.read == rd)]
            if rd == "floor_only":
                g = g[g.min_prints == 3]
                v = float(g.shift_decades.iloc[0]) if len(g) else np.nan
            else:
                v = float(g.shift_decades.max()) if len(g) else np.nan
            n_id = int(t5as[(t5as.segment == s)
                            & (t5as.read == "identity")].n_objects.iloc[0])
            # n on every bucket (Evidence Standard) -- the unlabelled segment is tiny and
            # its median is correspondingly unstable, which the axis label must show.
            xs.append(f"{s}<br>n={n_id:,}"); ys.append(v)
            ns.append(n_id)
        fig.add_trace(go.Bar(x=xs, y=ys, name=("floor only (mp=3)" if rd == "floor_only"
                                               else "merge only (max)"),
                             marker_color=col,
                             text=[f"{v:+.3f}" for v in ys], textposition="outside",
                             textfont=dict(size=9),
                             customdata=ns,
                             hovertemplate=("%{x}<br>%{y:+.4f} dec<br>identity n="
                                            "%{customdata:,}<extra></extra>")), row=2, col=2)
    fig.update_yaxes(title_text="shift from identity (decades)", row=2, col=2)
    fig.update_xaxes(title_text="segment", row=2, col=2)

    v4d = prior["v4_duration_pooled"]; c10d_ = prior["c10c_duration_pooled"]
    cap = C.caption(
        sample=(f"46,709 sub-bursts at the identity cell, kernel {KP:g} min, 43 ok events. "
                f"Floor-only = (K=0, d=0) across min_prints; merge-only = min_prints=2 "
                f"across the 12 non-degenerate (K,d) cells;<br>joint = the full surface. "
                f"Segment labels from variant 1.25."),
        filters="sep = hard_break (the reference separator rule). label='ok' cells only.",
        chash=chash,
        extra=(
            f"<b>ATTRIBUTION — the floor moved it, by {att['ratio_floor_over_merge']:.1f}×.</b> "
            f"Floor-only at min_prints=3 shifts the median <b>{att['floor_only_at_mp3_decades']:+.4f} "
            f"decades</b> ({att['identity_median_s']*1e3:.3f} → "
            f"{att['identity_median_s']*1e3*10**att['floor_only_at_mp3_decades']:.3f} ms); at "
            f"min_prints=5, {att['floor_only_at_mp5_decades']:+.4f}.<br>The strongest of the twelve "
            f"merge cells shifts it <b>{att['merge_only_max_shift_decades']:+.4f} decades</b> "
            f"(median across the twelve, {att['merge_only_median_shift_decades']:+.4f}). Joint max "
            f"{att['joint_max_shift_decades']:+.4f}, against an additive prediction of "
            f"{att['additive_prediction_decades']:+.4f} — an interaction of "
            f"{att['interaction_decades']:+.4f} decades, so the two are mildly super-additive, "
            f"not independent.<br>"
            f"<b>10d-R4 does not fire:</b> the two shifts differ by "
            f"{S['R4_separability']['abs_difference_decades']:.4f} decades against a "
            f"separability floor of {S['R4_separability']['separability_min_decades']}, and both "
            f"exceed the negligible bound. The mechanisms are separable.<br>"
            f"<b>Prior figures, read from their artifacts, across DIFFERENT cohorts:</b> v4 pooled "
            f"median {v4d['median']*1e9:.0f} ns (n={v4d['n']:,}, 100-event cohort, "
            f"v4_t5_t6_summary.json); 10c pooled median {c10d_['median']*1e3:.3f} ms "
            f"(n={c10d_['n']:,}, 56-event dev sample, all three kernels, s1_t1_subbursts.parquet).<br>"
            f"10d's identity cell reproduces 10c bit-exactly. <b>{c10d_['share_2print']:.1%} of 10c's "
            f"objects are single-interval</b> — that population is what min_prints=3 removes."))
    C.finish(fig, "Chart 06 — Which mechanism moved the duration distribution?",
             "Phase 10d T5a · floor-only versus merge-only versus joint · this is the deliverable",
             cap, height=1020, width=1340)
    manifest.append(C.write(fig, OUT, "06_attribution"))

    # ==================================================================== 07
    fig = make_subplots(rows=1, cols=2, subplot_titles=[
        "2-print share vs prints retained inside bursts — promotion or deletion?",
        f"Object print-count distribution at four cells (kernel {KP:g} min)"],
        column_widths=[0.52, 0.48], horizontal_spacing=0.1)
    b = t5b[t5b.kernel_min == KP]
    for rd in ["identity", "floor_only", "merge_only", "joint"]:
        g = b[b.read == rd]
        fig.add_trace(go.Scatter(
            x=g.share_2print, y=g.prints_retained_share, mode="markers", name=rd,
            marker=dict(color=READCOL[rd], size=11, opacity=0.85,
                        line=dict(color=C.INK, width=0.8)),
            customdata=np.stack([g.K, g.d, g.min_prints, g.n_objects,
                                 g.prints_delta_vs_identity], axis=-1),
            hovertemplate=("K=%{customdata[0]} d=%{customdata[1]} mp=%{customdata[2]}"
                           "<br>2-print share %{x:.3f}<br>prints retained %{y:.4f}"
                           "<br>n=%{customdata[3]:,}  Δprints=%{customdata[4]:+,}"
                           "<extra></extra>")), row=1, col=1)
    fig.add_hline(y=1.0, line=dict(color=C.INK, width=1.2, dash="dash"), row=1, col=1)
    fig.add_annotation(x=0.25, y=1.0, text="prints preserved — PROMOTION", showarrow=False,
                       yshift=10, xanchor="left", font=dict(size=10, color=C.ARM_A),
                       row=1, col=1)
    fig.add_annotation(x=0.25, y=0.972, text="prints leave the burst population — DELETION",
                       showarrow=False, xanchor="left",
                       font=dict(size=10, color=C.ROWCAP), row=1, col=1)
    fig.update_xaxes(title_text="share of objects with n_prints = 2", row=1, col=1)
    fig.update_yaxes(title_text="prints inside bursts ÷ prints inside bursts at identity",
                     row=1, col=1)

    hb = sb[(sb.sep == "hard_break") & (sb.kernel_min == KP)]
    for lab, K, d, mp, col in picks[:4]:
        g = hb[(hb.K == K) & (hb.d == d) & (hb.min_prints == mp)]
        vc = g.n_prints.value_counts().sort_index()
        vc = vc[vc.index <= 40]
        fig.add_trace(go.Scatter(x=vc.index, y=vc.values / len(g), mode="lines+markers",
                                 name=f"{lab} (n={len(g):,})",
                                 line=dict(color=col, width=2), marker=dict(size=4),
                                 hovertemplate="n_prints %{x}<br>share %{y:.4f}<extra></extra>"),
                      row=1, col=2)
    fig.update_xaxes(title_text="n_prints per object (truncated at 40 for display)",
                     row=1, col=2)
    fig.update_yaxes(type="log", title_text="share of objects, log", row=1, col=2)

    ident = b[b.read == "identity"].iloc[0]
    f3 = b[(b.read == "floor_only") & (b.min_prints == 3)].iloc[0]
    mmax = b[b.read == "merge_only"].sort_values("prints_delta_vs_identity").iloc[-1]
    cap = C.caption(
        sample=(f"Every grid cell at kernel {KP:g} min, sep=hard_break. Identity cell "
                f"n={int(ident.n_objects):,} objects holding {int(ident.prints_in_bursts):,} "
                f"prints."),
        filters="label='ok' cells only.",
        chash=chash,
        extra=(
            f"<b>This is the diagnostic a median cannot give.</b> Both mechanisms lower the "
            f"2-print share; only one keeps the prints.<br>"
            f"<b>Floor (min_prints=3):</b> 2-print share {ident.share_2print:.3f} → "
            f"{f3.share_2print:.3f}, objects {int(ident.n_objects):,} → {int(f3.n_objects):,}, "
            f"and prints inside bursts fall by {abs(int(f3.prints_delta_vs_identity)):,} "
            f"({1-f3.prints_retained_share:.2%}). Those prints leave the burst population — "
            f"<b>deletion</b>.<br>"
            f"<b>Merge (strongest cell, K={int(mmax.K)} d={mmax.d:g}):</b> 2-print share "
            f"{ident.share_2print:.3f} → {mmax.share_2print:.3f}, objects "
            f"{int(ident.n_objects):,} → {int(mmax.n_objects):,}, and prints inside bursts "
            f"{'rise' if mmax.prints_delta_vs_identity>0 else 'fall'} by "
            f"{abs(int(mmax.prints_delta_vs_identity)):,} "
            f"({mmax.prints_retained_share:.4f}× identity). Short objects become longer ones — "
            f"<b>promotion</b>.<br>"
            f"A merge at K=1 preserves the print count exactly, by construction: two objects of "
            f"a and b intervals separated by one interval give (a+1)+(b+1) = a+b+2 prints before "
            f"and (a+1+b)+1 = a+b+2 after."))
    C.finish(fig, "Chart 07 — Promotion or deletion?",
             "Phase 10d T5b · n_prints composition, which separates the two mechanisms",
             cap, height=820, width=1340)
    manifest.append(C.write(fig, OUT, "07_nprints_composition"))

    # ==================================================================== 08
    Ks = C10D["merge_grid"]["K"]; ds = C10D["merge_grid"]["d"]
    mps = C10D["min_prints_grid"]["values"]
    ec = cells[(cells.label == "ok") & (cells.kernel_min == KP)
               & (cells.sep == "hard_break")]
    fig = make_subplots(rows=2, cols=3, subplot_titles=[
        f"objects — min_prints={m}" for m in mps] + [
        f"median duration (ms) — min_prints={m}" for m in mps],
        vertical_spacing=0.19, horizontal_spacing=0.075)
    for ci, mp in enumerate(mps, 1):
        for ri, (field, agg) in enumerate([("n_objects", "sum"), ("dur_median", "median")], 1):
            Z = np.full((len(ds), len(Ks)), np.nan)
            for a, dd in enumerate(ds):
                for bkt, K in enumerate(Ks):
                    key = (K, dd) if not (K == 0 or dd == 0.0) else (0, 0.0)
                    g = ec[(ec.K == key[0]) & (ec.d == key[1]) & (ec.min_prints == mp)]
                    if len(g):
                        Z[a, bkt] = (g[field].sum() if agg == "sum"
                                     else g[field].median() * 1e3)
            fig.add_trace(go.Heatmap(
                z=Z, x=[str(k) for k in Ks], y=[f"{d:g}" for d in ds],
                colorscale="Blues" if ri == 1 else "Oranges", showscale=False,
                text=[[("" if not np.isfinite(v) else
                        (f"{v:,.0f}" if ri == 1 else f"{v:.3f}")) for v in row] for row in Z],
                texttemplate="%{text}", textfont=dict(size=9),
                hovertemplate="K=%{x} d=%{y}<br>%{z:,.4f}<extra></extra>"), row=ri, col=ci)
            fig.update_xaxes(title_text="K", row=ri, col=ci)
            if ci == 1:
                fig.update_yaxes(title_text="d (decades)", row=ri, col=ci)
    for ri in (1, 2):
        for ci in (1, 2, 3):
            fig.add_shape(type="rect", x0=-0.5, x1=0.5, y0=-0.5, y1=len(ds) - 0.5,
                          line=dict(color=C.ROWCAP, width=2.5, dash="dot"),
                          row=ri, col=ci)
            fig.add_shape(type="rect", x0=-0.5, x1=len(Ks) - 0.5, y0=-0.5, y1=0.5,
                          line=dict(color=C.ROWCAP, width=2.5, dash="dot"),
                          row=ri, col=ci)
    cap = C.caption(
        sample=(f"43 ok events, kernel {KP:g} min, sep=hard_break. Objects summed across "
                f"events; median duration is the median of per-event medians."),
        filters="label='ok' cells only.",
        chash=chash,
        extra=(
            "<b>The dotted L is a PARAMETERIZATION ARTIFACT, not a result.</b> The K=0 column "
            "and the d=0 row are the eight degenerate cells: a separating interval is "
            "non-burst by definition,<br>so d=0 admits none regardless of K and K=0 admits "
            "none regardless of d. All eight are bit-identical to the identity cell — proved "
            "at T2 control C1 — and are stored once,<br>flagged degenerate, then broadcast for "
            "display. A reader must not read the flat L as a finding about the tolerance.<br>"
            f"<b>10d-R3 does not fire.</b> Over the twelve non-degenerate cells the tolerance "
            f"rank correlates with per-event median duration at |ρ| = "
            f"{S['T5d_R3_parameter_dominance']['tolerance_rho_duration']:.3f} and with count at "
            f"{S['T5d_R3_parameter_dominance']['tolerance_rho_count']:.3f}, against a maximum "
            f"event-characteristic correlation of "
            f"{S['T5d_R3_parameter_dominance']['max_event_characteristic_rho_duration']:.3f} "
            f"(duration) and "
            f"{S['T5d_R3_parameter_dominance']['max_event_characteristic_rho_count']:.3f} "
            f"(count). The answer tracks the event, not the parameter."))
    C.finish(fig, "Chart 08 — Merge surface across K × d × min_prints",
             "Phase 10d T5d · count and duration over the full pre-registered grid",
             cap, height=940, width=1340)
    manifest.append(C.write(fig, OUT, "08_merge_surface"))

    # ==================================================================== 09
    fig = make_subplots(rows=1, cols=3, subplot_titles=[
        "Attribution per kernel — floor-only (mp=3) vs merge-only (max)",
        "Identity median duration per kernel",
        "Merge shift per segment × variant (kernel 8, K=5 d=1.0)"],
        horizontal_spacing=0.085)
    pk = S["T5g_R6_kernel_variant"]["per_kernel"]
    labs = list(pk.keys())
    fig.add_trace(go.Bar(x=labs, y=[pk[l]["floor_only_mp3_decades"] for l in labs],
                         name="floor only (mp=3)", marker_color=C.ROWCAP,
                         text=[f"{pk[l]['floor_only_mp3_decades']:+.3f}" for l in labs],
                         textposition="outside", textfont=dict(size=10)), row=1, col=1)
    fig.add_trace(go.Bar(x=labs, y=[pk[l]["merge_only_max_decades"] for l in labs],
                         name="merge only (max)", marker_color=C.ARM_A,
                         text=[f"{pk[l]['merge_only_max_decades']:+.3f}" for l in labs],
                         textposition="outside", textfont=dict(size=10)), row=1, col=1)
    fig.update_yaxes(title_text="shift from identity (decades)",
                     range=[0, max(pk[l]["floor_only_mp3_decades"] for l in labs) * 1.35],
                     row=1, col=1)

    fig.add_trace(go.Bar(x=labs, y=[pk[l]["identity_median_s"] * 1e3 for l in labs],
                         name="identity median", marker_color=C.INK, showlegend=False,
                         text=[f"{pk[l]['identity_median_s']*1e3:.3f} ms" for l in labs],
                         textposition="outside", textfont=dict(size=10)), row=1, col=2)
    fig.update_yaxes(type="log", title_text="median duration (ms), log", row=1, col=2)

    for v, col in zip(sorted(var.variant.unique()), [C.ARM_A, C.ARM_B, C.SIDECAR]):
        g = var[var.variant == v]
        fig.add_trace(go.Bar(x=g.segment, y=g.merge_shift_decades, name=f"variant {v:g}",
                             marker_color=col, customdata=g.n_identity,
                             hovertemplate=("%{x}<br>%{y:+.4f} dec<br>identity n="
                                            "%{customdata:,}<extra></extra>")), row=1, col=3)
    fig.update_yaxes(title_text="merge shift (decades)", row=1, col=3)

    r6 = S["T5g_R6_kernel_variant"]
    cap = C.caption(
        sample="43 / 38 / 49 ok events at kernels 8 / 2 / 32 min. All three variants carried.",
        filters="sep = hard_break; label='ok' cells only.",
        chash=chash,
        extra=(
            f"<b>10d-R6 does not fire.</b> The floor dominates at every kernel — "
            f"{ {k: v['dominant'] for k, v in pk.items()} } — so the attribution is not "
            f"kernel-specific.<br>Sign is coherent at 2 or more of 3 kernels: "
            f"{r6['coherent_sign_at_2_of_3']}; at least one kernel shows a material shift: "
            f"{r6['any_kernel_material']}.<br>"
            f"<b>The variant axis cannot move the objects, only their labels.</b> 10c computes "
            f"sub-bursts once per (event, kernel) and cross-joins each variant's "
            f"segment/anchor context; 10d does the same.<br>Panel 3 therefore shows segment "
            f"membership changing under the variant, not the decomposition changing."))
    C.finish(fig, "Chart 09 — Does the attribution hold across kernels and variants?",
             "Phase 10d T5g · consistency of the floor-over-merge result",
             cap, height=780, width=1340)
    manifest.append(C.write(fig, OUT, "09_kernel_variant_consistency"))

    # ==================================================================== 10
    ident_cells = cells[(cells.label == "ok") & (cells.kernel_min == KP)
                        & (cells.sep == "hard_break") & (cells.min_prints == 2)
                        & (cells.K == 0) & (cells.d == 0.0)]
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=ident_cells.n_prints_session, y=ident_cells.n_objects, mode="markers",
        name=f"events (n={len(ident_cells)})",
        marker=dict(color=C.ARM_A, size=10, opacity=0.8, line=dict(color=C.INK, width=0.8)),
        text=ident_cells.ticker,
        hovertemplate="%{text}<br>prints %{x:,}<br>sub-bursts %{y:,}<extra></extra>"))
    x = ident_cells.n_prints_session.to_numpy(dtype=float)
    y = ident_cells.n_objects.to_numpy(dtype=float)
    m = (x > 0) & (y > 0)
    sl, ic = np.polyfit(np.log10(x[m]), np.log10(y[m]), 1)
    xs = np.linspace(np.log10(x[m].min()), np.log10(x[m].max()), 50)
    fig.add_trace(go.Scatter(x=10**xs, y=10**(sl * xs + ic), mode="lines",
                             name=f"log-log fit, slope {sl:.4f}",
                             line=dict(color=C.ROWCAP, width=2, dash="dash")))
    fig.update_xaxes(type="log", title_text="T=0 D1-aggregated print count, log")
    fig.update_yaxes(type="log", title_text="sub-bursts at the identity cell, log")
    t5e = S["T5e_count_vs_print_count"]
    p = S["prior_version_figures"]
    cap = C.caption(
        sample=f"43 ok events, kernel {KP:g} min, identity cell (K=0, d=0, min_prints=2, sep=hard_break).",
        filters="label='ok' cells only.",
        chash=chash,
        extra=(
            f"<b>DESCRIPTIVE ONLY. Nothing here can fail.</b> Retired as a hard stop at 10c "
            f"on Cooper's call and carried for comparability. A positive relation is expected: "
            f"a bigger, longer,<br>more active event mechanically produces more sub-bursts "
            f"under any definition.<br>"
            f"<b>10d:</b> Spearman {t5e['t0_print_count']['spearman']:.4f}, log-log slope "
            f"{t5e['t0_print_count']['loglog_slope']:.4f}, n={t5e['t0_print_count']['n']}.<br>"
            f"<b>Prior versions, read from their committed artifacts:</b> "
            f"v4 {p['v4_count_vs_prints']['spearman_t0_print_count']:.4f} / "
            f"{p['v4_count_vs_prints']['loglog_slope_t0_print_count']:.4f} "
            f"(n={p['v4_count_vs_prints']['n']}, v4_t5_t6_summary.json); "
            f"v3 {p['v3_count_vs_prints']['print_rate_spearman']:.4f}–"
            f"{p['v3_count_vs_prints']['volume_rate_spearman']:.4f} / "
            f"{p['v3_count_vs_prints']['volume_rate_slope']:.4f}–"
            f"{p['v3_count_vs_prints']['print_rate_slope']:.4f} (v3_t2_t4_summary.json); "
            f"v1 Arm A {p['v1_count_vs_prints']['spearman']:.2f} / "
            f"{p['v1_count_vs_prints']['loglog_slope']:.2f}.<br>"
            f"<b>Attribution gap on the v1 pair, recorded:</b> unlike v3 and v4 it exists only "
            f"in results/phase_10/REPORT.md prose (line 127), not in any committed JSON "
            f"artifact. Quoted with that provenance, not re-derived.<br>"
            f"<b>Cohorts differ</b> — v1/v3/v4 ran a 100-event cohort, 10c/10d the 56-event "
            f"dev sample — so these are not like-for-like."))
    C.finish(fig, "Chart 10 — Sub-burst count versus print count",
             "Phase 10d T5e · descriptive, no gate, reported for comparability",
             cap, height=760, width=1180)
    manifest.append(C.write(fig, OUT, "10_count_vs_print_count"))

    with open(os.path.join(ART, "t5_chart_manifest.json"), "w", encoding="utf-8") as f:
        json.dump({"task": "T5h", "charts": manifest}, f, indent=2)
    print(f"\n{len(manifest)} charts, kaleido verified "
          f"{sum(m['kaleido_verified'] for m in manifest)}/{len(manifest)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
