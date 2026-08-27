"""
10d Diagnostic 1, T1 -- frame construction and the T1d reconciliation gate.

THIS DIAGNOSTIC CHANGES NOTHING. No boundary rule is adopted, no parameter tuned, no
cutoff applied, no sub-burst re-derived.

10c's method is IMPORTED, not reimplemented: `peaks_poisson` and `envelope_boundary` come
from research/phase_10c/s1_t1_subbursts.py by explicit spec. The one thing 10c does not
expose is the LOSING troughs -- `envelope_boundary` returns the argmax only -- so
`all_troughs()` here enumerates the same loop and collects every candidate. It is not
trusted: on EVERY frame the top of that ladder is asserted equal to what 10c's own
`envelope_boundary` returns on the same input. The enumeration is verified against the
committed function, frame by frame, rather than assumed to match it.

Frame window: centered, width = the kernel duration, per config. Bin grid: the event's
full-session grid, fixed across frames, which is also 10c's own grid -- so the full-window
frame (frame_index = -1) reproduces 10c's per-cell computation exactly. That is T1d.

NON-CAUSAL. The window is centered; every frame reads forward in time by half a window.
Nothing here is a detector, a signal, or an operating point.

Usage: .venv/Scripts/python.exe research/phase_10d_diag1/t1_frames.py
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

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "research", "phase_10"))
# research/phase_10 and research/phase_10c both define common.py; only phase_10 goes on
# sys.path and 10c's is loaded by explicit spec, exactly as 10c's own scripts do it.
import common as p10  # noqa: E402
from common import rel  # noqa: E402
_s = ilu.spec_from_file_location("c10c", os.path.join(ROOT, "research", "phase_10c", "common.py"))
c10c = ilu.module_from_spec(_s); _s.loader.exec_module(c10c)
_s2 = ilu.spec_from_file_location("s1t1", os.path.join(ROOT, "research", "phase_10c",
                                                      "s1_t1_subbursts.py"))
s1t1 = ilu.module_from_spec(_s2); _s2.loader.exec_module(s1t1)

ART = os.path.join(ROOT, "results", "phase_10d_diag1", "artifacts")
KEY = ["ticker", "event_date_canonical"]


def conf():
    with open(os.path.join(ROOT, "config", "phase_10d_diag1.json"), encoding="utf-8") as f:
        return json.load(f)


def chash_of(d):
    return hashlib.sha256(json.dumps(d, sort_keys=True).encode()).hexdigest()[:8]


def all_troughs(centers, dens, pks):
    """Every candidate trough between adjacent surviving peaks, with its void.

    Identical loop to research/phase_10c/s1_t1_subbursts.py::envelope_boundary -- that
    function keeps only the argmax; this keeps the whole ladder. Verified against it on
    every frame by the caller.
    """
    out = []
    for a, b in zip(pks[:-1], pks[1:]):
        if b - a < 2:
            continue
        seg = dens[a + 1:b]
        t = a + 1 + int(np.argmin(seg))
        den = np.sqrt(dens[a] * dens[b])
        if den <= 0:
            continue
        out.append({"idx": int(t), "loc": float(centers[t]),
                    "void": float(1.0 - dens[t] / den),
                    "peak_l": int(a), "peak_r": int(b)})
    return out


def event_arrays(cfg10c, r, F, d1_us, k_min):
    """10c's labelling path, verbatim. Returns None where 10c would decline."""
    d = p10.read_event_trades(cfg10c, r.ticker, r.event_date_canonical,
                              r.momentum_pct, offsets=(0,))
    s0 = d.get(0)
    if s0 is None or len(s0) == 0:
        return None
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
        return None
    dt_s = np.diff(agg_ts).astype(np.float64) / 1e9
    keep = dt_s > 0
    assert keep.all(), "zero-length interval -- 10c's agg_ts indexing would misalign"
    li = np.log10(dt_s)
    mid = (agg_ts[:-1].astype(np.float64) + agg_ts[1:].astype(np.float64)) / 2.0
    b = c10c.session_bounds(r.event_date_canonical)
    if b is None:
        return None
    sigma = float(np.std(li, ddof=1))
    floor = c10c.median_se_min_count(sigma, F)
    edges = np.array([b["start_ns"], b["rth_open_ns"], b["rth_close_ns"], b["end_ns"]],
                     dtype=np.float64)
    seg_i = np.clip(np.searchsorted(edges, mid, "right") - 1, 0, len(edges) - 2)
    ser = pd.Series(li, index=pd.to_datetime(mid.astype("int64"), unit="ns"))
    loc_med = np.full(li.size, np.nan)
    wcount = np.zeros(li.size)
    for _bi in np.unique(seg_i):
        m_ = seg_i == _bi
        sub = ser[m_]
        if sub.size == 0:
            continue
        _roll = sub.rolling(f"{int(k_min)}min", center=True, min_periods=1)
        loc_med[m_] = _roll.median().to_numpy()
        wcount[m_] = _roll.count().to_numpy()
    ok = wcount >= floor if np.isfinite(floor) else np.zeros(li.size, bool)
    return {"agg_ts": agg_ts, "agg_px": agg_px, "li": li, "mid": mid, "ok": ok,
            "loc_med": loc_med, "norm": li - loc_med, "bounds": b,
            "derived_floor": float(floor), "n_prints": int(agg_ts.size)}


def hist_ladder(vals, bins, centers):
    """Histogram -> Poisson-surviving peaks -> the full trough ladder + 10c's winner."""
    cnt, _ = np.histogram(vals, bins=bins)
    tot = cnt.sum()
    if tot == 0:
        return None
    dens = cnt / (tot * 0.1)
    pks, _ = s1t1.peaks_poisson(cnt)
    if pks.size < 2:
        return {"dens": dens, "pks": pks, "ladder": [], "winner": None}
    ladder = all_troughs(centers, dens, pks)
    winner = s1t1.envelope_boundary(centers, dens, pks)   # 10c's own function, the oracle
    # verify the enumeration against it rather than trusting it
    if winner is not None:
        assert ladder, "10c found a winner where the enumeration found no trough"
        top = max(ladder, key=lambda x: x["void"])
        assert (top["idx"] == winner["idx"]
                and abs(top["void"] - winner["void"]) < 1e-12), (
            f"ladder top {top} != 10c envelope_boundary {winner}")
    return {"dens": dens, "pks": pks, "ladder": ladder, "winner": winner}


def main() -> int:
    C = conf()
    chash = chash_of(C)
    cfg10c = c10c.load_cfg()
    F = float(c10c.class_m(cfg10c)["D4_median_precision_factor"])
    d1_us = float(c10c.class_m(cfg10c)["D1_sweep_floor_us"])

    # ---- assert the upstream config, line-ending-insensitively
    raw = c10c.cfg_hash()
    with open(rel("config/phase_10c.json"), "rb") as f:
        _b = f.read()
    _CRLF, _LF = bytes([13, 10]), bytes([10])
    lf = hashlib.sha256(_b.replace(_CRLF, _LF)).hexdigest()[:8]
    exp_raw = C["upstream"]["phase_10c_config_hash_raw_crlf"]
    exp_lf = C["upstream"]["phase_10c_config_hash_lf"]
    assert raw in (exp_raw, exp_lf) or lf == exp_lf, f"10c config raw={raw} lf={lf}"

    cells10c = pd.read_parquet(os.path.join(ROOT, C["upstream"]["cells_artifact"]))
    dev = c10c.load_dev_sample(cfg10c)
    subset = [(e["ticker"], e["event_date_canonical"]) for e in C["event_subset"]["events"]]
    dev = dev[dev.apply(lambda r: (r.ticker, r.event_date_canonical) in subset, axis=1)]
    assert len(dev) == len(subset), f"subset resolved {len(dev)} of {len(subset)}"

    KERNELS = C["upstream"]["kernels_min"]
    div = int(C["frames"]["step_divisor"])
    cap = int(C["frames"]["max_frames_per_event_kernel"])
    min_iv = int(C["frames"]["min_intervals_per_frame"])

    frame_rows, trough_rows, recon_rows, step_rows = [], [], [], []
    t0 = time.perf_counter()

    for r in dev.itertuples(index=False):
        for k_min in KERNELS:
            ev = event_arrays(cfg10c, r, F, d1_us, k_min)
            if ev is None:
                continue
            ok_fin = ev["ok"] & np.isfinite(ev["norm"])
            nv_all = ev["norm"][ok_fin]
            base = {"ticker": r.ticker, "event_date_canonical": r.event_date_canonical,
                    "kernel_min": float(k_min)}

            if nv_all.size < C["upstream"]["cell_level_ok_minimum"]:
                frame_rows.append({**base, "frame_index": -1, "label": "insufficient_context",
                                   "t_ns": np.nan, "n_intervals": int(nv_all.size),
                                   "n_peaks": 0, "winner_norm": np.nan,
                                   "winner_void": np.nan, "winner_abs_s": np.nan,
                                   "local_median_s": np.nan, "ok_share": float(ok_fin.mean()),
                                   "n_prints_in_window": ev["n_prints"], "n_troughs": 0})
                continue

            # ---- the event's full-session grid, 10c's rule, fixed for every frame
            e_lo = np.floor(nv_all.min() * 10) / 10
            e_hi = np.ceil(nv_all.max() * 10) / 10 + 0.1
            bins = np.arange(e_lo, e_hi, 0.1)
            centers = (bins[:-1] + bins[1:]) / 2.0

            mid_ok = ev["mid"][ok_fin]
            norm_ok = ev["norm"][ok_fin]
            locmed_ok = ev["loc_med"][ok_fin]
            order = np.argsort(mid_ok, kind="stable")
            mid_ok, norm_ok, locmed_ok = mid_ok[order], norm_ok[order], locmed_ok[order]

            # ================= frame -1: the full window. THIS IS 10c's COMPUTATION.
            H = hist_ladder(norm_ok, bins, centers)
            w = H["winner"]
            lm_full = float(10.0 ** np.median(locmed_ok))
            frame_rows.append({
                **base, "frame_index": -1, "label": "full_window",
                "t_ns": float(ev["bounds"]["start_ns"]), "n_intervals": int(norm_ok.size),
                "n_peaks": int(H["pks"].size),
                "winner_norm": (w["loc"] if w else np.nan),
                "winner_void": (w["void"] if w else np.nan),
                "winner_abs_s": (lm_full * 10.0 ** w["loc"] if w else np.nan),
                "local_median_s": lm_full, "ok_share": float(ok_fin.mean()),
                "n_prints_in_window": ev["n_prints"], "n_troughs": len(H["ladder"])})
            for rank, tr in enumerate(sorted(H["ladder"], key=lambda x: -x["void"])):
                trough_rows.append({**base, "frame_index": -1, "rank": rank,
                                    "loc_norm": tr["loc"], "void": tr["void"],
                                    "loc_abs_s": lm_full * 10.0 ** tr["loc"],
                                    "local_median_s": lm_full})

            # ================= T1d reconciliation against 10c's committed per-cell value
            c10 = cells10c[(cells10c.ticker == r.ticker)
                           & (cells10c.event_date_canonical == r.event_date_canonical)
                           & (cells10c.kernel_min == k_min)]
            committed = c10.threshold_norm.dropna().unique()
            recon_rows.append({
                **base,
                "committed_threshold_norm": (float(committed[0]) if committed.size else None),
                "committed_void": (float(c10.void.dropna().unique()[0])
                                   if c10.void.dropna().size else None),
                "frame_full_window_norm": (w["loc"] if w else None),
                "frame_full_window_void": (w["void"] if w else None),
                "committed_label": (c10.label.iloc[0] if len(c10) else None),
                "matches": bool(committed.size and w is not None
                                and committed[0] == w["loc"])})

            # ================= stepped frames
            step_ns = k_min * 60.0 * 1e9 / div
            half = k_min * 60.0 * 1e9 / 2.0
            t_lo, t_hi = float(ev["bounds"]["start_ns"]), float(ev["bounds"]["end_ns"])
            n_nat = int(np.floor((t_hi - t_lo) / step_ns)) + 1
            capped = n_nat > cap
            if capped:
                step_ns = (t_hi - t_lo) / (cap - 1)
                n_nat = cap
            times = t_lo + np.arange(n_nat) * step_ns
            step_rows.append({**base, "step_ns": float(step_ns),
                              "step_min": float(step_ns / 6e10), "n_frames": int(n_nat),
                              "natural_step_min": float(k_min / div),
                              "cap": cap, "cap_bound": bool(capped)})

            lo_i = np.searchsorted(mid_ok, times - half, "left")
            hi_i = np.searchsorted(mid_ok, times + half, "right")
            # T1c also wants the in-window `ok` SHARE, which needs the unfiltered mid as
            # the denominator -- mid_ok is already ok-filtered and cannot supply it.
            mid_all = np.sort(ev["mid"])
            lo_a = np.searchsorted(mid_all, times - half, "left")
            hi_a = np.searchsorted(mid_all, times + half, "right")
            for fi, (t, a, b_, aa, ba) in enumerate(zip(times, lo_i, hi_i, lo_a, hi_a)):
                n_in = int(b_ - a)
                n_all = int(ba - aa)
                ok_share_f = (n_in / n_all) if n_all else np.nan
                if n_in < min_iv:
                    frame_rows.append({
                        **base, "frame_index": fi, "label": "thin", "t_ns": float(t),
                        "n_intervals": n_in, "n_peaks": 0, "winner_norm": np.nan,
                        "winner_void": np.nan, "winner_abs_s": np.nan,
                        "local_median_s": (float(10.0 ** np.median(locmed_ok[a:b_]))
                                           if n_in else np.nan),
                        "ok_share": ok_share_f, "n_prints_in_window": n_all + 1,
                        "n_troughs": 0})
                    continue
                Hf = hist_ladder(norm_ok[a:b_], bins, centers)
                wf = Hf["winner"] if Hf else None
                lm = float(10.0 ** np.median(locmed_ok[a:b_]))
                frame_rows.append({
                    **base, "frame_index": fi,
                    "label": ("ok" if wf else "no_threshold"), "t_ns": float(t),
                    "n_intervals": n_in, "n_peaks": int(Hf["pks"].size) if Hf else 0,
                    "winner_norm": (wf["loc"] if wf else np.nan),
                    "winner_void": (wf["void"] if wf else np.nan),
                    "winner_abs_s": (lm * 10.0 ** wf["loc"] if wf else np.nan),
                    "local_median_s": lm, "ok_share": ok_share_f,
                    "n_prints_in_window": n_all + 1,
                    "n_troughs": len(Hf["ladder"]) if Hf else 0})
                if Hf:
                    for rank, tr in enumerate(sorted(Hf["ladder"], key=lambda x: -x["void"])):
                        trough_rows.append({**base, "frame_index": fi, "rank": rank,
                                            "loc_norm": tr["loc"], "void": tr["void"],
                                            "loc_abs_s": lm * 10.0 ** tr["loc"],
                                            "local_median_s": lm})
            print(f"  {r.ticker} {r.event_date_canonical} k={k_min:g}  "
                  f"{n_nat} frames  ({time.perf_counter()-t0:.0f}s)", flush=True)

    fr = pd.DataFrame(frame_rows)
    tr = pd.DataFrame(trough_rows)
    rc = pd.DataFrame(recon_rows)
    st = pd.DataFrame(step_rows)
    os.makedirs(ART, exist_ok=True)
    fr.to_parquet(os.path.join(ART, "t1_frames.parquet"), index=False)
    tr.to_parquet(os.path.join(ART, "t1_troughs.parquet"), index=False, compression="zstd")
    rc.to_parquet(os.path.join(ART, "t1_reconciliation.parquet"), index=False)
    st.to_parquet(os.path.join(ART, "t1_frame_steps.parquet"), index=False)

    # ---------------------------------------------------------- T1d gate
    testable = rc[rc.committed_threshold_norm.notna()]
    n_match = int(testable.matches.sum())
    gate = {"diagnostic": "10d-diag1", "task": "T1d", "config_hash": chash,
            "cells_with_a_committed_threshold": int(len(testable)),
            "cells_reproduced_exactly": n_match,
            "cells_declined_by_10c_and_by_the_frame_pipeline": int(
                (rc.committed_threshold_norm.isna()).sum()),
            "rows": rc.to_dict("records"),
            "pass": bool(n_match == len(testable)),
            "criterion": ("the full-window frame must reproduce 10c's committed per-cell "
                          "threshold_norm EXACTLY (float equality, not a tolerance). "
                          "D1-R1 fires on any divergence.")}
    with open(os.path.join(ART, "t1d_reconciliation.json"), "w", encoding="utf-8") as f:
        json.dump(gate, f, indent=2, default=str)

    cap_bound_share = float(st.cap_bound.mean()) if len(st) else 0.0
    wf = {"diagnostic": "10d-diag1", "task": "T1", "config_hash": chash,
          "events": int(dev.shape[0]), "kernels": KERNELS,
          "event_kernel_cells": int(len(st)),
          "frames_total": int(len(fr)),
          "frames_full_window": int((fr.frame_index == -1).sum()),
          "frames_stepped": int((fr.frame_index >= 0).sum()),
          "frames_ok": int((fr.label == "ok").sum()),
          "frames_thin": int((fr.label == "thin").sum()),
          "frames_no_threshold": int((fr.label == "no_threshold").sum()),
          "frames_insufficient_context": int((fr.label == "insufficient_context").sum()),
          "trough_rows": int(len(tr)),
          "cap_bound_share": cap_bound_share,
          "D1_R3_threshold": C["frames"]["cap_bind_share_report_threshold"],
          "D1_R3_fires": bool(cap_bound_share > C["frames"]["cap_bind_share_report_threshold"]),
          "wall_clock_s": round(time.perf_counter() - t0, 1),
          "causal_status": ("NON-CAUSAL. Centered window; every frame reads forward in time "
                            "by half a kernel. Nothing here is a detector, a signal or an "
                            "operating point.")}
    with open(os.path.join(ART, "t1_waterfall.json"), "w", encoding="utf-8") as f:
        json.dump(wf, f, indent=2)

    print("\n--- T1d RECONCILIATION GATE ---")
    print(f"  testable cells        {len(testable)}")
    print(f"  reproduced exactly    {n_match}")
    print(f"  GATE                  {'PASS' if gate['pass'] else 'FAIL -- D1-R1'}")
    print("\n--- frames ---")
    for k, v in wf.items():
        if k not in ("causal_status",):
            print(f"  {k:<38} {v}")
    return 0 if gate["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
