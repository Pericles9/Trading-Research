"""
10d Diagnostic 1, T2 -- the static boundary tracks. Charts 01-05.

01  absolute-units track: EVERY candidate trough against session time, winner highlighted,
    reference lines at 1 ms / 10 ms / 100 ms / 1 s / 10 s
02  normalized-units track: the same in decades
03  mode-count trace: surviving peaks per frame, through the session
04  winner vs runner-up, both unit systems, plus the void-gap distribution
05  cross-kernel overlay of the winner's absolute track at 2 / 8 / 32 min

DESCRIPTION ONLY. The reference lines are read-off guides; nothing is compared against them
for pass/fail, and no boundary rule is adopted anywhere.

Usage: .venv/Scripts/python.exe research/phase_10d_diag1/t2_charts.py
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
from common import ns_to_et  # noqa: E402

ART = os.path.join(ROOT, "results", "phase_10d_diag1", "artifacts")
OUT = os.path.join(ROOT, "results", "phase_10d_diag1", "charts")
KEY = ["ticker", "event_date_canonical"]
KCOL = {2.0: C.ARM_A, 8.0: C.ARM_B, 32.0: C.SIDECAR}
KP = 8.0


def conf():
    with open(os.path.join(ROOT, "config", "phase_10d_diag1.json"), encoding="utf-8") as f:
        return json.load(f)


def chash_of(d):
    return hashlib.sha256(json.dumps(d, sort_keys=True).encode()).hexdigest()[:8]


def ev_label(t, d):
    return f"{t} {d}"


def add_refs(fig, refs, row, col, xdom=None):
    for v, lab in refs:
        fig.add_hline(y=v, line=dict(color=C.GRID, width=1, dash="dot"), row=row, col=col)


def main() -> int:
    Cc = conf()
    chash = chash_of(Cc)
    fr = pd.read_parquet(os.path.join(ART, "t1_frames.parquet"))
    tr = pd.read_parquet(os.path.join(ART, "t1_troughs.parquet"))
    st = pd.read_parquet(os.path.join(ART, "t1_frame_steps.parquet"))
    events = [(e["ticker"], e["event_date_canonical"], e["slot"])
              for e in Cc["event_subset"]["events"]]
    refs = [(v, lab) for v, lab in zip(Cc["reference_lines_s"],
                                       ["1 ms", "10 ms", "100 ms", "1 s", "10 s"])]
    W, H = Cc["charts"]["width"], Cc["charts"]["height_static"]
    manifest = []

    fr_t = fr[fr.frame_index >= 0]
    tr_t = tr[tr.frame_index >= 0]

    # ================================================================= 01 / 02
    for tag, ycol, ylab, logy, name, title, sub in [
        ("abs", "loc_abs_s", "candidate boundary (s), log", True,
         "01_boundary_track_absolute",
         "Chart 01 — Every candidate boundary through the session, in absolute units",
         "10d-diag1 T2a · kernel 8 min · winner highlighted, losers shown · "
         "does any candidate ever reach a tradeable timescale?"),
        ("norm", "loc_norm", "candidate boundary (decades, normalized)", False,
         "02_boundary_track_normalized",
         "Chart 02 — The same candidates in normalized units",
         "10d-diag1 T2b · kernel 8 min · flat here but moving in chart 01 means the local "
         "median is doing the work, not the shape")]:
        fig = make_subplots(rows=len(events), cols=1, vertical_spacing=0.035,
                            subplot_titles=[f"{t} {d} — {s}" for t, d, s in events])
        for i, (t, d, slot) in enumerate(events):
            rr, cc = i + 1, 1
            g = tr_t[(tr_t.ticker == t) & (tr_t.event_date_canonical == d)
                     & (tr_t.kernel_min == KP)]
            if not len(g):
                lab = fr[(fr.ticker == t) & (fr.event_date_canonical == d)
                         & (fr.kernel_min == KP) & (fr.frame_index == -1)].label
                why = ("10c declines this cell — insufficient_context, so it has no "
                       "boundary and no ladder"
                       if (len(lab) and lab.iloc[0] == "insufficient_context")
                       else "no frame in this cell carries a candidate ladder")
                fig.add_annotation(text=why, xref="x domain", yref="y domain",
                                   x=0.5, y=0.5, showarrow=False,
                                   font=dict(size=12, color=C.INK2), row=rr, col=cc)
                fig.update_yaxes(visible=False, row=rr, col=cc)
                fig.update_xaxes(visible=False, row=rr, col=cc)
                continue
            lose = g[g["rank"] > 0]
            win = g[g["rank"] == 0].sort_values("frame_index")
            fig.add_trace(go.Scattergl(
                x=ns_to_et(fr_t.set_index(["ticker", "event_date_canonical", "kernel_min",
                                           "frame_index"])
                           .loc[list(zip(lose.ticker, lose.event_date_canonical,
                                         lose.kernel_min, lose.frame_index))]
                           .t_ns.to_numpy().astype(np.int64)),
                y=lose[ycol], mode="markers", showlegend=(i == 0), name="losing candidates",
                marker=dict(color=lose.void, colorscale="Viridis", size=2.4, opacity=0.5,
                            cmin=0, cmax=1,
                            colorbar=dict(title="void", len=0.32, y=0.86, x=1.005,
                                          thickness=11) if i == 0 else None),
                hovertemplate="%{y:.4g}<br>void %{marker.color:.3f}<extra></extra>"),
                row=rr, col=cc)
            wt = fr_t[(fr_t.ticker == t) & (fr_t.event_date_canonical == d)
                      & (fr_t.kernel_min == KP)].set_index("frame_index")
            fig.add_trace(go.Scattergl(
                x=ns_to_et(wt.loc[win.frame_index].t_ns.to_numpy().astype(np.int64)),
                y=win[ycol], mode="markers", showlegend=(i == 0), name="argmax winner",
                marker=dict(color=C.ARM_B, size=3.2),
                hovertemplate="winner %{y:.4g}<extra></extra>"), row=rr, col=cc)
            if logy:
                for v, lab in refs:
                    fig.add_hline(y=v, line=dict(color=C.GRID, width=1, dash="dot"),
                                  row=rr, col=cc)
                fig.update_yaxes(type="log", row=rr, col=cc)
            fig.update_yaxes(title_text=ylab, title_font=dict(size=10),
                             tickfont=dict(size=9), row=rr, col=cc)
        n_tot = len(tr_t[tr_t.kernel_min == KP])
        n_win = int((tr_t[tr_t.kernel_min == KP]["rank"] == 0).sum())
        extra_bits = []
        if tag == "abs":
            for v, lab in refs:
                a = (tr_t[tr_t.kernel_min == KP].loc_abs_s >= v).mean()
                w_ = (tr_t[(tr_t.kernel_min == KP) & (tr_t["rank"] == 0)].loc_abs_s >= v).mean()
                extra_bits.append(f"≥ {lab}: any candidate {a:.1%}, winner {w_:.1%}")
            extra = ("<b>Reference lines are read-off guides only</b> — nothing is compared "
                     "against them for pass/fail, and D13 records that no burst timescale is "
                     "established at usable precision.<br><b>Share of candidates at or above "
                     "each line (kernel 8):</b> " + " · ".join(extra_bits))
        else:
            extra = ("Normalized units are decades relative to each interval's own local "
                     "median. A candidate flat here and moving in chart 01 is a fixed "
                     "position on the shape<br>with a moving denominator; the reverse means "
                     "the shape itself is moving.")
        cap = C.caption(
            sample=(f"7 pre-registered events × kernel 8 min. {n_tot:,} candidate troughs "
                    f"over {n_win:,} frames with a boundary. Every candidate is plotted; "
                    f"nothing is clipped.<br>Frame window = kernel width, centered; step = "
                    f"kernel/8 = 1 min."),
            filters=("Frames holding fewer than 30 in-window intervals are labelled `thin`, "
                     "carried, and given no candidate ladder and no fallback — they contribute "
                     "no point here."),
            chash=chash, extra=extra)
        C.finish(fig, title, sub, cap, height=1720, width=W)
        for a in fig.layout.annotations:
            if getattr(a, "font", None) is not None and a.text and " — " in str(a.text):
                a.update(font=dict(size=12))
        manifest.append(C.write(fig, OUT, name))

    # ================================================================= 03
    fig = make_subplots(rows=2, cols=2, vertical_spacing=0.15, horizontal_spacing=0.09,
                        column_widths=[0.62, 0.38], subplot_titles=[
                            "Surviving peaks per frame through the session (kernel 8 min)",
                            "Distribution of surviving peaks per frame",
                            "Candidate troughs per frame through the session",
                            "Frame labels: how many frames support a ladder at all"])
    f8 = fr_t[(fr_t.kernel_min == KP)]
    # The subset spans 2020-2024, so a shared absolute clock axis collapses each session
    # into a vertical line. Panels 1 and 2 use MINUTES FROM SESSION START instead, which is
    # the only x that lets five different dates be overlaid.
    for i, (t, d, slot) in enumerate(events):
        g = f8[(f8.ticker == t) & (f8.event_date_canonical == d) & (f8.label == "ok")]
        if not len(g):
            continue
        t0_ns = float(f8[(f8.ticker == t)
                         & (f8.event_date_canonical == d)].t_ns.min())
        x_rel = (g.t_ns.to_numpy() - t0_ns) / 6e10
        col = [C.ARM_A, C.ARM_B, C.SIDECAR, C.ROWCAP, "#8d7ee0", "#c0392b", "#16a085"][i]
        fig.add_trace(go.Scattergl(x=x_rel, y=g.n_peaks, mode="markers",
                                   name=ev_label(t, d),
                                   marker=dict(color=col, size=2.6, opacity=0.7),
                                   legendgroup=ev_label(t, d)), row=1, col=1)
        fig.add_trace(go.Scattergl(x=x_rel, y=g.n_troughs, mode="markers",
                                   name=ev_label(t, d),
                                   marker=dict(color=col, size=2.6, opacity=0.7),
                                   legendgroup=ev_label(t, d), showlegend=False),
                      row=2, col=1)
    fig.update_xaxes(title_text="minutes from session start (04:00 ET)", row=1, col=1)
    fig.update_xaxes(title_text="minutes from session start (04:00 ET)", row=2, col=1)
    fig.add_hline(y=2, line=dict(color=C.INK, width=1.4, dash="dash"), row=1, col=1)
    fig.add_annotation(text="2 peaks — the bimodal case the void parameter assumes",
                       xref="x domain", yref="y", x=0.015, y=2, yshift=10, showarrow=False,
                       xanchor="left", font=dict(size=10.5, color=C.INK), row=1, col=1)
    fig.update_yaxes(title_text="surviving peaks", row=1, col=1)
    fig.update_yaxes(title_text="candidate troughs", row=2, col=1)

    ok8 = f8[f8.label == "ok"]
    vc = ok8.n_peaks.value_counts().sort_index()
    fig.add_trace(go.Bar(x=vc.index, y=vc.values / vc.sum(), marker_color=C.ARM_B,
                         showlegend=False,
                         text=[f"{v/vc.sum():.1%}" if v / vc.sum() > 0.05 else ""
                               for v in vc.values], textposition="outside",
                         hovertemplate="%{x} peaks<br>%{y:.2%}<extra></extra>"),
                  row=1, col=2)
    fig.update_xaxes(title_text=f"surviving peaks per frame (n={len(ok8):,} frames)",
                     row=1, col=2)
    fig.update_yaxes(title_text="share of frames", tickformat=".0%", row=1, col=2)

    lc = f8.label.value_counts()
    fig.add_trace(go.Bar(x=lc.index, y=lc.values, marker_color=C.ROWCAP, showlegend=False,
                         text=[f"{v:,}<br>{v/lc.sum():.1%}" for v in lc.values],
                         textposition="outside",
                         hovertemplate="%{x}<br>%{y:,}<extra></extra>"), row=2, col=2)
    fig.update_yaxes(title_text=f"frames (of {int(lc.sum()):,})",
                     range=[0, lc.max() * 1.25], row=2, col=2)

    share_ge3 = float((ok8.n_peaks >= 3).mean())
    cap = C.caption(
        sample=(f"7 pre-registered events, kernel 8 min, {len(ok8):,} frames carrying a "
                f"boundary. Frame window = kernel width, centered; step 1 min."),
        filters="`thin` frames (<30 in-window intervals) carry no ladder and are excluded from the peak distribution.",
        chash=chash,
        extra=(f"<b>The void parameter grades a trough against its two flanking peaks — a "
               f"construction that assumes two modes.</b> At frame resolution "
               f"<b>{share_ge3:.1%} of frames carrying a boundary have three or more "
               f"surviving peaks</b><br>(median {int(ok8.n_peaks.median())}, range "
               f"{int(ok8.n_peaks.min())}–{int(ok8.n_peaks.max())}), so a frame typically "
               f"offers {int(ok8.n_troughs.median())} candidate troughs and argmax picks one "
               f"of them. Only {int((ok8.n_peaks == 2).sum())} of {len(ok8):,} frames are the "
               f"two-peak case.<br>This is the multimodality question answered directly "
               f"rather than inferred. No rule is changed here."))
    C.finish(fig, "Chart 03 — How many modes are actually present, through time?",
             "10d-diag1 T2c · surviving peaks and candidate troughs per frame", cap,
             height=940, width=W)
    manifest.append(C.write(fig, OUT, "03_mode_count"))

    # ================================================================= 04
    piv = tr_t[tr_t.kernel_min == KP].pivot_table(
        index=KEY + ["frame_index"], columns="rank",
        values=["loc_abs_s", "void", "loc_norm"])
    have = [c for c in (0, 1) if ("void", c) in piv.columns]
    both = piv.dropna(subset=[("void", 0), ("void", 1)]) if len(have) == 2 else piv.iloc[0:0]
    gap = (both[("void", 0)] - both[("void", 1)]).to_numpy()
    r0a, r1a = both[("loc_abs_s", 0)].to_numpy(), both[("loc_abs_s", 1)].to_numpy()

    fig = make_subplots(rows=2, cols=2, vertical_spacing=0.155, horizontal_spacing=0.10,
                        subplot_titles=[
                            "Winner vs runner-up, absolute units — is the runner-up coarser?",
                            "Winner − runner-up void gap, ECDF",
                            "Absolute boundary by ladder rank (median, IQR)",
                            "Share of candidates at or above each reference timescale, by rank"])
    fig.add_trace(go.Scattergl(x=r0a, y=r1a, mode="markers", showlegend=False,
                               marker=dict(color=gap, colorscale="Plasma", size=3,
                                           opacity=0.55, cmin=0, cmax=float(np.nanmax(gap)),
                                           colorbar=dict(title="void gap", len=0.32,
                                                         y=0.85, x=1.005, thickness=11)),
                               hovertemplate=("winner %{x:.4g} s<br>runner-up %{y:.4g} s"
                                              "<extra></extra>")), row=1, col=1)
    lo, hi = np.nanmin([r0a.min(), r1a.min()]), np.nanmax([r0a.max(), r1a.max()])
    fig.add_trace(go.Scatter(x=[lo, hi], y=[lo, hi], mode="lines", showlegend=False,
                             line=dict(color=C.INK, width=1.2, dash="dash"),
                             hoverinfo="skip"), row=1, col=1)
    fig.update_xaxes(type="log", title_text="winner (s), log", row=1, col=1)
    fig.update_yaxes(type="log", title_text="runner-up (s), log", row=1, col=1)

    fig.add_trace(C.ecdf_trace(gap, "winner − runner-up void gap", C.ARM_B), row=1, col=2)
    fig.update_xaxes(title_text="void gap", row=1, col=2)
    fig.update_yaxes(title_text="cumulative share of frames", row=1, col=2)

    t8 = tr_t[tr_t.kernel_min == KP]
    ranks = sorted(t8["rank"].unique())[:10]
    med = [t8[t8["rank"] == r].loc_abs_s.median() for r in ranks]
    q25 = [t8[t8["rank"] == r].loc_abs_s.quantile(.25) for r in ranks]
    q75 = [t8[t8["rank"] == r].loc_abs_s.quantile(.75) for r in ranks]
    ns = [int((t8["rank"] == r).sum()) for r in ranks]
    fig.add_trace(go.Scatter(x=ranks, y=med, mode="lines+markers", showlegend=False,
                             line=dict(color=C.ARM_A, width=2.5),
                             marker=dict(size=8), customdata=ns,
                             error_y=dict(type="data", symmetric=False,
                                          array=np.array(q75) - np.array(med),
                                          arrayminus=np.array(med) - np.array(q25),
                                          color=C.ARM_A, width=4),
                             hovertemplate=("rank %{x}<br>median %{y:.4g} s"
                                            "<br>n=%{customdata:,}<extra></extra>")),
                  row=2, col=1)
    for v, lab in refs:
        fig.add_hline(y=v, line=dict(color=C.GRID, width=1, dash="dot"), row=2, col=1)
    fig.update_xaxes(title_text="ladder rank (0 = argmax winner)", row=2, col=1)
    fig.update_yaxes(type="log", title_text="absolute boundary (s), log", row=2, col=1)

    for (v, lab), col in zip(refs, [C.ARM_A, C.ARM_B, C.SIDECAR, C.ROWCAP, "#c0392b"]):
        ys = [float((t8[t8["rank"] == r].loc_abs_s >= v).mean()) for r in ranks]
        fig.add_trace(go.Scatter(x=ranks, y=ys, mode="lines+markers", name=f"≥ {lab}",
                                 line=dict(color=col, width=2), marker=dict(size=6),
                                 hovertemplate=f"rank %{{x}}<br>≥ {lab}: %{{y:.1%}}<extra></extra>"),
                      row=2, col=2)
    fig.update_xaxes(title_text="ladder rank", row=2, col=2)
    fig.update_yaxes(title_text="share at or above", tickformat=".0%", row=2, col=2)

    cap = C.caption(
        sample=(f"7 pre-registered events, kernel 8 min. {len(both):,} frames carrying at "
                f"least two candidates; {len(t8):,} candidates in total."),
        filters="`thin` frames excluded — they carry no ladder.",
        chash=chash,
        extra=(f"<b>Winner and runner-up sit at the same scale.</b> Median winner "
               f"{np.median(r0a)*1e3:.3f} ms, median runner-up {np.median(r1a)*1e3:.3f} ms; "
               f"the runner-up is coarser than the winner in {float((r1a>r0a).mean()):.1%} of "
               f"frames.<br>Median void gap <b>{np.median(gap):.4f}</b>, and "
               f"{float((gap<0.05).mean()):.1%} of frames have a gap below 0.05 — argmax is "
               f"often choosing between near-ties, but between near-ties AT THE SAME SCALE.<br>"
               f"<b>The coarse candidates live further down the ladder</b>, which panel 3 "
               f"shows directly: median absolute location rises monotonically with rank. "
               f"Description only; no rule is adopted."))
    C.finish(fig, "Chart 04 — Is argmax choosing between near-ties, and is the runner-up coarser?",
             "10d-diag1 T2d · the losing candidates, which no prior chart has shown", cap,
             height=980, width=W)
    manifest.append(C.write(fig, OUT, "04_winner_vs_runnerup"))

    # ================================================================= 05
    fig = make_subplots(rows=len(events), cols=1, vertical_spacing=0.035,
                        subplot_titles=[f"{t} {d} — {s}" for t, d, s in events])
    for i, (t, d, slot) in enumerate(events):
        rr, cc = i + 1, 1
        for k in Cc["upstream"]["kernels_min"]:
            g = fr_t[(fr_t.ticker == t) & (fr_t.event_date_canonical == d)
                     & (fr_t.kernel_min == k) & (fr_t.label == "ok")]
            if not len(g):
                continue
            fig.add_trace(go.Scattergl(
                x=ns_to_et(g.t_ns.to_numpy().astype(np.int64)), y=g.winner_abs_s,
                mode="markers", name=f"kernel {k:g} min", legendgroup=f"k{k}",
                showlegend=(i == 0), marker=dict(color=KCOL[k], size=2.4, opacity=0.6),
                hovertemplate=f"kernel {k:g} min<br>%{{y:.4g}} s<extra></extra>"),
                row=rr, col=cc)
        for v, lab in refs:
            fig.add_hline(y=v, line=dict(color=C.GRID, width=1, dash="dot"), row=rr, col=cc)
        fig.update_yaxes(type="log", title_text="winner (s), log",
                         title_font=dict(size=10), tickfont=dict(size=9), row=rr, col=cc)

    kt = (fr_t[fr_t.label == "ok"].groupby("kernel_min")
          .agg(n=("winner_abs_s", "size"), med=("winner_abs_s", "median"),
               med_lm=("local_median_s", "median")))
    ratio_txt = " · ".join(f"{k:g} min: winner median {r.med*1e3:.3f} ms, local median "
                           f"{r.med_lm*1e3:.3f} ms (n={int(r.n):,})"
                           for k, r in kt.iterrows())
    cap = C.caption(
        sample=("7 pre-registered events × 3 kernels, winner only, `ok` frames. Frame window "
                "= that kernel's width; step = that kernel / 8."),
        filters="`thin` and `insufficient_context` frames carry no winner and are absent.",
        chash=chash,
        extra=(f"<b>PARTIAL READ, and labelled as one.</b> Three kernels, not the wide "
               f"log-spaced grid 10c deferred. Three points cannot separate a structural "
               f"interval from a smooth scaling.<br><b>Observed:</b> {ratio_txt}.<br>"
               f"A winner track that is flat across kernels would be a structural interval; "
               f"one that scales with the kernel is landing wherever the local median puts "
               f"it. The local median is shown alongside<br>because it is the normalization "
               f"denominator and moves with the kernel by construction."))
    C.finish(fig, "Chart 05 — The winner's absolute track at three kernels",
             "10d-diag1 T2e · partial read on threshold location versus window size", cap,
             height=1720, width=W)
    manifest.append(C.write(fig, OUT, "05_cross_kernel"))

    with open(os.path.join(ART, "t2_chart_manifest.json"), "w", encoding="utf-8") as f:
        json.dump({"task": "T2f", "charts": manifest}, f, indent=2)
    print(f"\n{len(manifest)} charts, kaleido "
          f"{sum(m['kaleido_verified'] for m in manifest)}/{len(manifest)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
