"""
Phase 10d T4f -- chart 05, the tape review. THIS IS 10d-R0. Cooper's alone; this script
produces the chart set and evaluates nothing.

One file per event, four panels, kernel 8 min (D5 primary), variant 1.25 for segment and
anchor labelling only (the objects are variant-independent):

  1  full session: price, with sub-burst locations at the REFERENCE cell
  2  full session: normalized log10 interval with the argmax-void threshold
  3  ZOOM on the densest sub-burst region -- REFERENCE cell (K=0, d=0, min_prints=2),
     which is 10c's rule exactly, shaded to true extent
  4  the SAME zoom -- JOINT cell (K=5, d=1.0, min_prints=3), so what the merge and the
     floor did to the same tape is visible side by side

Usage: .venv/Scripts/python.exe research/phase_10d/t4_tape.py
"""
from __future__ import annotations

import hashlib
import importlib.util as ilu
import json
import os
import sys
import time

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "research", "phase_10"))
import chartlib as C  # noqa: E402
import common as p10  # noqa: E402
from common import ns_to_et, rel  # noqa: E402
_s = ilu.spec_from_file_location("c10c", os.path.join(ROOT, "research", "phase_10c", "common.py"))
c10c = ilu.module_from_spec(_s); _s.loader.exec_module(c10c)
_s2 = ilu.spec_from_file_location("s1t1", os.path.join(ROOT, "research", "phase_10c",
                                                      "s1_t1_subbursts.py"))
s1t1 = ilu.module_from_spec(_s2); _s2.loader.exec_module(s1t1)
from assemble import SEP_HARD_BREAK, assemble, label_intervals  # noqa: E402

ART = os.path.join(ROOT, "results", "phase_10d", "artifacts")
OUT = os.path.join(ROOT, "results", "phase_10d", "charts", "05_tape_review")
KP = 8.0
REF = dict(K=0, d=0.0, min_prints=2)
JOINT = dict(K=5, d=1.0, min_prints=3)


def main() -> int:
    with open(os.path.join(ROOT, "config", "phase_10d.json"), encoding="utf-8") as f:
        C10D = json.load(f)
    chash = hashlib.sha256(json.dumps(C10D, sort_keys=True).encode()).hexdigest()[:8]
    cfg10c = c10c.load_cfg()
    F = float(c10c.class_m(cfg10c)["D4_median_precision_factor"])
    d1_us = float(c10c.class_m(cfg10c)["D1_sweep_floor_us"])
    ctx_all = pd.read_parquet(os.path.join(ART, "t4_variant_context.parquet"))
    # Segment membership is VARIANT-DEPENDENT for 3 of 56 events (CELH 2020-08-06 and
    # OST 2024-06-13 are rth at 1.25/1.30 and evening at 1.35; CODX 2020-03-11 is
    # premarket at 1.25 and rth at 1.30/1.35). Carry all three labels on every chart so
    # the set demonstrably spans all four segments and no reader is misled by one
    # variant's labelling.
    seg_by_variant = ctx_all.pivot_table(
        index=["ticker", "event_date_canonical"], columns="variant",
        values="segment", aggfunc="first")
    ctx = ctx_all[ctx_all.variant == 1.25].set_index(["ticker", "event_date_canonical"])

    dev = c10c.load_dev_sample(cfg10c)
    os.makedirs(OUT, exist_ok=True)
    manifest, t0 = [], time.perf_counter()

    for i, r in enumerate(dev.itertuples(index=False), 1):
        d = p10.read_event_trades(cfg10c, r.ticker, r.event_date_canonical,
                                  r.momentum_pct, offsets=(0,))
        s0 = d.get(0)
        if s0 is None or len(s0) == 0:
            continue
        raw_ts = s0["sip_timestamp"].to_numpy()
        raw_px = s0["price"].to_numpy(dtype=np.float64)
        uniq, inv = np.unique(raw_ts, return_inverse=True)
        sz = s0["size"].to_numpy(dtype=np.float64)
        wsum = np.bincount(inv, weights=raw_px * sz, minlength=uniq.size)
        ssum = np.bincount(inv, weights=sz, minlength=uniq.size)
        px_u = np.where(ssum > 0, wsum / np.maximum(ssum, 1e-12),
                        np.bincount(inv, weights=raw_px, minlength=uniq.size)
                        / np.maximum(np.bincount(inv, minlength=uniq.size), 1))
        agg_ts, _ = c10c.sweep_aggregate(uniq, d1_us)
        gi = np.searchsorted(uniq, agg_ts)
        bnd = np.append(gi, uniq.size)
        grp = np.repeat(np.arange(agg_ts.size), np.diff(bnd))
        gw = np.bincount(grp, weights=px_u[:uniq.size] * ssum, minlength=agg_ts.size)
        gs = np.bincount(grp, weights=ssum, minlength=agg_ts.size)
        agg_px = np.where(gs > 0, gw / np.maximum(gs, 1e-12), px_u[gi])
        if agg_ts.size < 20:
            continue
        dt_s = np.diff(agg_ts).astype(np.float64) / 1e9
        li = np.log10(dt_s)
        mid = (agg_ts[:-1].astype(np.float64) + agg_ts[1:].astype(np.float64)) / 2.0
        b = c10c.session_bounds(r.event_date_canonical)
        if b is None:
            continue
        sigma = float(np.std(li, ddof=1))
        floor = c10c.median_se_min_count(sigma, F)
        edges = np.array([b["start_ns"], b["rth_open_ns"], b["rth_close_ns"], b["end_ns"]],
                         dtype=np.float64)
        seg_i = np.clip(np.searchsorted(edges, mid, "right") - 1, 0, len(edges) - 2)

        ser = pd.Series(li, index=pd.to_datetime(mid.astype("int64"), unit="ns"))
        loc_med = np.full(li.size, np.nan); wcount = np.zeros(li.size)
        for _bi in np.unique(seg_i):
            m_ = seg_i == _bi
            sub = ser[m_]
            if sub.size == 0:
                continue
            _roll = sub.rolling(f"{int(KP)}min", center=True, min_periods=1)
            loc_med[m_] = _roll.median().to_numpy(); wcount[m_] = _roll.count().to_numpy()
        ok = wcount >= floor if np.isfinite(floor) else np.zeros(li.size, bool)
        if ok.sum() < C10D["upstream_10c"]["cell_level_ok_minimum"]:
            continue
        norm = li - loc_med
        nv = norm[ok & np.isfinite(norm)]
        e_lo, e_hi = np.floor(nv.min() * 10) / 10, np.ceil(nv.max() * 10) / 10 + 0.1
        bins = np.arange(e_lo, e_hi, 0.1)
        cnt, _ = np.histogram(nv, bins=bins)
        centers = (bins[:-1] + bins[1:]) / 2.0
        dens = cnt / (cnt.sum() * 0.1)
        pks, _ = s1t1.peaks_poisson(cnt)
        env = s1t1.envelope_boundary(centers, dens, pks) if pks.size >= 2 else None
        if env is None:
            continue
        thr = float(env["loc"])
        inb = label_intervals(norm, ok, thr)
        a_ref = assemble(norm, ok, agg_ts, thr, sep=SEP_HARD_BREAK, inb=inb, **REF)
        a_jnt = assemble(norm, ok, agg_ts, thr, sep=SEP_HARD_BREAK, inb=inb, **JOINT)
        if a_ref["n_objects"] == 0:
            continue

        # densest region: widest window holding the most reference objects
        s_ns = a_ref["start_ns"]
        span = max(int((agg_ts[-1] - agg_ts[0]) * 0.02), 1)
        cnts = np.searchsorted(s_ns, s_ns + span) - np.arange(s_ns.size)
        j = int(np.argmax(cnts))
        z0, z1 = int(s_ns[j]), int(s_ns[j]) + span

        et = ns_to_et(agg_ts)
        fig = make_subplots(rows=4, cols=1, vertical_spacing=0.075, subplot_titles=[
            f"Full session — price, with {a_ref['n_objects']:,} sub-burst locations at the reference cell",
            "Full session — normalized log10 interval, with the argmax-void threshold",
            f"ZOOM — REFERENCE cell K=0, d=0, min_prints=2 (10c's rule exactly)",
            f"SAME ZOOM — JOINT cell K=5, d=1.0 decades, min_prints=3"])

        fig.add_trace(go.Scatter(x=et, y=agg_px, mode="lines", name="price",
                                 line=dict(color=C.INK, width=1)), row=1, col=1)
        fig.add_trace(go.Scatter(
            x=ns_to_et(s_ns), y=np.full(s_ns.size, np.nanmin(agg_px)), mode="markers",
            name=f"sub-burst start (n={s_ns.size:,})",
            marker=dict(color=C.ARM_B, size=4, symbol="line-ns-open")), row=1, col=1)
        fig.update_yaxes(title_text="price", row=1, col=1)

        # Scattergl, not Scatter: an event can carry 570k intervals and the SVG renderer
        # does not survive that. Every point is kept -- nothing is decimated or clipped.
        fig.add_trace(go.Scattergl(x=ns_to_et(mid.astype("int64")), y=norm, mode="markers",
                                   name="normalized log10 interval", showlegend=False,
                                   marker=dict(color=C.GRID, size=1.6)), row=2, col=1)
        fig.add_hline(y=thr, line=dict(color=C.ROWCAP, width=1.6, dash="dash"), row=2, col=1)
        fig.add_annotation(x=et[0], y=thr, text=f" threshold {thr:.3f} (void {env['void']:.3f})",
                           showarrow=False, xanchor="left", yanchor="bottom",
                           font=dict(size=10, color=C.ROWCAP), row=2, col=1)
        fig.update_yaxes(title_text="norm. log10 interval", row=2, col=1)

        zm = (agg_ts >= z0) & (agg_ts <= z1)
        for rr, res, colr in ((3, a_ref, C.ARM_A), (4, a_jnt, C.SIDECAR)):
            fig.add_trace(go.Scatter(x=ns_to_et(agg_ts[zm]), y=agg_px[zm], mode="lines+markers",
                                     name="price" if rr == 3 else None, showlegend=False,
                                     line=dict(color=C.INK, width=1),
                                     marker=dict(size=2.5, color=C.INK)), row=rr, col=1)
            sel = (res["start_ns"] <= z1) & (res["end_ns"] >= z0)
            nsel = int(sel.sum())
            # ONE filled polygon trace, not N shapes. add_vrect per object is O(N) layout
            # shapes and stalls outright at the thousands of objects a dense zoom holds.
            if nsel:
                lo_ = np.maximum(res["start_ns"][sel], z0).astype(np.int64)
                hi_ = np.minimum(res["end_ns"][sel], z1).astype(np.int64)
                lo_et, hi_et = ns_to_et(lo_), ns_to_et(hi_)
                yy = agg_px[zm]
                y0_, y1_ = float(np.nanmin(yy)), float(np.nanmax(yy))
                pad = (y1_ - y0_) * 0.06 or 0.01
                px_, py_ = [], []
                for a_, b_ in zip(lo_et, hi_et):
                    px_ += [a_, a_, b_, b_, None]
                    py_ += [y0_ - pad, y1_ + pad, y1_ + pad, y0_ - pad, None]
                fig.add_trace(go.Scatter(
                    x=px_, y=py_, mode="lines", fill="toself", fillcolor=colr,
                    opacity=0.30, line=dict(width=0), showlegend=False,
                    hoverinfo="skip"), row=rr, col=1)
            lab = ("reference" if rr == 3 else "joint")
            med = float(np.median(res["duration_s"])) if res["n_objects"] else float("nan")
            fig.add_annotation(
                x=0.005, y=0.98, xref="x domain", yref="y domain", row=rr, col=1,
                text=(f"<b>{lab}</b>: {nsel} objects in view · {res['n_objects']:,} in the "
                      f"session · median duration {med*1e3:.3f} ms"),
                showarrow=False, xanchor="left", yanchor="top",
                font=dict(size=11, color=colr))
            fig.update_yaxes(title_text="price", row=rr, col=1)

        key_ = (r.ticker, r.event_date_canonical)
        seg = ctx.loc[key_, "segment"] if key_ in ctx.index else None
        seg = seg if isinstance(seg, str) else "unlabelled"
        if key_ in seg_by_variant.index:
            row_ = seg_by_variant.loc[key_]
            segs_all = {float(v): (row_[v] if isinstance(row_[v], str) else "unlabelled")
                        for v in seg_by_variant.columns}
        else:
            segs_all = {}
        seg_txt = " · ".join(f"{v:g}: <b>{sg}</b>" for v, sg in sorted(segs_all.items()))
        seg_varies = len(set(segs_all.values())) > 1
        cap = C.caption(
            sample=(f"{r.ticker} {r.event_date_canonical} · segment by variant — {seg_txt}"
                    + ("  <b>(this event changes segment with the variant)</b>"
                       if seg_varies else "")
                    + f" · kernel {KP:g} min (D5, primary) · {agg_ts.size:,} D1-aggregated "
                      f"prints, {li.size:,} intervals.<br>Zoom window {span/1e9:.1f} s, "
                      f"chosen as the densest sub-burst region at the reference cell."),
            filters=(f"ok mask (window ≥ derived floor {floor:.0f} intervals): "
                     f"{ok.sum():,}/{ok.size:,}. Other kernels and variants are on record in "
                     f"t4_cell_summary.parquet, not re-plotted here."),
            chash=chash,
            extra=("<b>This chart is 10d-R0 and it is Cooper's.</b> The question is whether "
                   "the marked bursts match what is on the tape. Nothing here is evaluated "
                   "by the agent.<br>Panels 3 and 4 are the same tape under the two cells: "
                   "the reference reproduces 10c print for print, the joint cell applies both "
                   "10d changes at their grid extremes."))
        C.finish(fig, f"Chart 05 — Tape review · {r.ticker} {r.event_date_canonical}",
                 "Phase 10d T4f · 10d-R0 · reference cell versus joint cell on the same tape",
                 cap, height=1500, width=1340)
        name = f"{r.ticker}_{r.event_date_canonical}"
        manifest.append({**C.write(fig, OUT, name), "ticker": r.ticker,
                         "event_date_canonical": str(r.event_date_canonical),
                         "segment_v125": seg,
                         "segment_by_variant": {str(k): v for k, v in segs_all.items()},
                         "segment_varies_with_variant": bool(seg_varies),
                         "n_ref": a_ref["n_objects"],
                         "n_joint": a_jnt["n_objects"]})
        if i % 10 == 0:
            print(f"  {i}/{len(dev)} ({time.perf_counter()-t0:.0f}s)", flush=True)

    with open(os.path.join(ART, "t4_tape_manifest.json"), "w", encoding="utf-8") as f:
        json.dump({"task": "T4f", "chart": "05_tape_review", "n_events": len(manifest),
                   "kernel_min": KP, "reference_cell": REF, "joint_cell": JOINT,
                   "charts": manifest}, f, indent=2)
    md = pd.DataFrame(manifest)
    segs = {"by_variant_1.25": md.segment_v125.value_counts().to_dict(),
            "any_variant": pd.Series([s_ for m in manifest
                                      for s_ in m["segment_by_variant"].values()]
                                     ).value_counts().to_dict()}
    print(f"\n{len(manifest)} tape charts written to {OUT}")
    print(f"segments covered: {segs}")
    print(f"kaleido verified: {sum(m['kaleido_verified'] for m in manifest)}/{len(manifest)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
