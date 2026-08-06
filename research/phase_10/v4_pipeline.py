"""
Phase 10 v4 T1-T6 -- sub-burst detection from locally-normalized log inter-trade
intervals.

  T1  intervals and ties (two variants; the resolution floor is taken from the
      data, never assumed)
  T2  local normalization: y = log10(dt) - centred moving MEDIAN of log10(dt)
      over window_fraction x sequence length. NON-CAUSAL by construction.
  T3  normalized log-interval histogram -> peaks -> trough -> VOID PARAMETER
      gate. Where no trough clears the cutoff, NO sub-bursts are declared; the
      event is labeled `no_threshold`, carried, never given a fallback.
  T4  sub-bursts = runs of intervals below the per-event threshold
  T5  the Arm A test
  T6  stability + causal audit

NO INTENSITY CURVE IS ESTIMATED ANYWHERE (D9). The operating variable is the
inter-trade interval itself.

Usage: .venv/Scripts/python.exe research/phase_10/v4_pipeline.py
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import time

import numpy as np
import pandas as pd
from scipy import signal as sps_signal
from scipy import stats as sps

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from v2_common import (  # noqa: E402
    COHORT_KEY, POOLED, collapse_ties, load_frozen_cohort, quantiles,
    read_event_trades, rel, session_window, write_json,
)

CFG = "config/phase_10_v4.json"
OBS = ("print_rate",)  # the interval process is the print process; volume enters via size weights


def load_cfg():
    with open(rel(CFG), encoding="utf-8") as f:
        return json.load(f)


def cfg_hash():
    with open(rel(CFG), "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()[:8]


# ------------------------------------------------------------------ T2
def moving_median_log(y: np.ndarray, frac: float, anchor_div: int = 10) -> np.ndarray:
    """Centred moving median of `y`, window = frac * len(y).

    Evaluated at anchors spaced window/anchor_div apart and linearly
    interpolated -- O(anchor_div * n) instead of O(n log w) for w ~ 1e5.
    """
    n = y.size
    w = max(11, int(round(frac * n)) | 1)
    if w >= n:
        return np.full(n, float(np.median(y)))
    half = w // 2
    stride = max(1, w // anchor_div)
    anchors = np.arange(0, n, stride)
    if anchors[-1] != n - 1:
        anchors = np.append(anchors, n - 1)
    med = np.empty(anchors.size, dtype=np.float64)
    for j, i in enumerate(anchors):
        a, b = max(0, i - half), min(n, i + half + 1)
        med[j] = np.median(y[a:b])
    return np.interp(np.arange(n), anchors, med)


# ------------------------------------------------------------------ T3
def derive_threshold(yn: np.ndarray, cfg) -> dict:
    """Histogram -> peaks -> trough -> void gate. Returns the threshold or a
    `no_threshold` reason. No smoothing: that would reintroduce a bandwidth."""
    hc = cfg["threshold"]["histogram"]
    pf = cfg["threshold"]["peak_finding"]
    vp = cfg["threshold"]["void_parameter"]
    bw = hc["bin_width_decades"]
    lo, hi = hc["range_decades"]
    edges = np.arange(lo, hi + bw, bw)
    counts, _ = np.histogram(yn, bins=edges)
    if counts.sum() == 0:
        return {"has_threshold": False, "reason": "empty histogram"}
    dens = counts.astype(float) / counts.sum() / bw
    centres = (edges[:-1] + edges[1:]) / 2.0

    prom = pf["prominence_fraction_of_max"] * dens.max()
    peaks, _ = sps_signal.find_peaks(dens, prominence=prom,
                                     distance=pf["min_peak_separation_bins"])
    if peaks.size < 2:
        return {"has_threshold": False, "reason": f"{peaks.size} peak(s) found; need >= 2",
                "n_peaks": int(peaks.size),
                "peak_positions": centres[peaks].tolist() if peaks.size else [],
                "hist_density": dens, "hist_centres": centres}

    left = int(peaks[0])  # short-interval (intra-burst) peak
    cands = []
    for right in peaks[1:]:
        seg = dens[left:int(right) + 1]
        t_rel = int(np.argmin(seg))
        t_idx = left + t_rel
        denom = np.sqrt(dens[left] * dens[int(right)])
        void = 1.0 - (dens[t_idx] / denom) if denom > 0 else 0.0
        cands.append({"peak_left_decades": float(centres[left]),
                      "peak_right_decades": float(centres[int(right)]),
                      "trough_decades": float(centres[t_idx]),
                      "void": float(void)})
    passing = [c for c in cands if c["void"] >= vp["cutoff"]]
    if not passing:
        return {"has_threshold": False,
                "reason": f"no trough clears void cutoff {vp['cutoff']}",
                "n_peaks": int(peaks.size),
                "best_void": float(max(c["void"] for c in cands)),
                "candidates": cands, "hist_density": dens, "hist_centres": centres}
    chosen = passing[0]  # FIRST clearing trough, scanning left to right
    return {"has_threshold": True, "reason": None, "n_peaks": int(peaks.size),
            "threshold_decades": chosen["trough_decades"], "void": chosen["void"],
            "peak_left_decades": chosen["peak_left_decades"],
            "peak_right_decades": chosen["peak_right_decades"],
            "n_candidates": len(cands), "candidates": cands,
            "hist_density": dens, "hist_centres": centres}


# ------------------------------------------------------------------ T4
def runs_below(yn: np.ndarray, thr: float, min_prints: int) -> list[tuple[int, int]]:
    """Maximal runs of consecutive intervals strictly below `thr`.

    Interval i joins arrival i to arrival i+1, so a run of intervals [a, b]
    spans arrivals a .. b+1, i.e. (b - a + 2) prints.
    """
    m = (yn < thr).astype(np.int8)
    if m.size == 0:
        return []
    pad = np.concatenate(([0], m, [0]))
    e = np.diff(pad)
    starts = np.flatnonzero(e == 1)
    ends = np.flatnonzero(e == -1) - 1
    return [(int(a), int(b)) for a, b in zip(starts, ends) if (b - a + 2) >= min_prints]


def main() -> int:
    cfg = load_cfg()
    chash = cfg_hash()
    art = rel(cfg["paths"]["out_artifacts"])
    cohort = load_frozen_cohort({"paths": {"cohort_manifest": cfg["paths"]["cohort_manifest"]},
                                 "cohort": {"content_hash": cfg["cohort"]["content_hash"]}})
    tie_ref = cfg["ties"]["reference_variant"]
    wgrid = cfg["normalization"]["window_fraction_grid"]
    wref = cfg["normalization"]["window_fraction_reference"]
    mgrid = cfg["subbursts"]["min_prints_grid"]
    mref = cfg["subbursts"]["min_prints_reference"]
    min_n = cfg["normalization"]["min_prints_for_normalization"]

    det = pd.read_parquet(rel(cfg["paths"]["detection"]))
    det["event_date_canonical"] = det["event_date_canonical"].astype(str)
    det = det[np.isclose(det["threshold"], cfg["detection_anchor"]["threshold"])].set_index(COHORT_KEY)
    v2m = pd.read_parquet(rel(cfg["paths"]["v2_event_metrics"]))
    v2m["event_date_canonical"] = v2m["event_date_canonical"].astype(str)
    v2m = v2m[(v2m["tie_variant"] == "as_is") & (v2m["k"] == 50)
              & (v2m["observable"] == "print_rate")].set_index(COHORT_KEY)["peak_ns"]

    ev_rows, sb_rows, hist_rows = [], [], []
    t0all = time.perf_counter()
    per_ev = []

    for i, r in enumerate(cohort.itertuples(index=False), 1):
        t_ev = time.perf_counter()
        w = session_window(r.event_date_canonical, 0)
        d = read_event_trades(cfg, r.ticker, r.event_date_canonical, r.momentum_pct, offsets=(0,))
        t0 = d.get(0)
        if t0 is None or len(t0) == 0:
            continue
        ts_raw = t0["sip_timestamp"].to_numpy()
        px_raw = t0["price"].to_numpy(dtype=float)
        sz_raw = t0["size"].to_numpy(dtype=float)
        key = (r.ticker, r.event_date_canonical, r.momentum_pct)
        drow = det.loc[key] if key in det.index else None
        if isinstance(drow, pd.DataFrame):
            drow = drow.iloc[0]
        seg = (drow["det_segment_poll1"] if drow is not None
               and pd.notna(drow["det_segment_poll1"]) else "no_detection")
        det_ns = (int(drow["det_ns_poll1"]) if drow is not None
                  and pd.notna(drow["det_ns_poll1"]) else None)
        pk_ns = v2m.get(key)

        # ---- T1 ties
        dt_raw = np.diff(ts_raw)
        n_tied = int((dt_raw == 0).sum())
        nz = dt_raw[dt_raw > 0]
        res_floor_ns = int(nz.min()) if nz.size else 1

        variants = {}
        cts, csz, _ = collapse_ties(ts_raw, sz_raw)
        # prices of the collapsed arrivals = price of the LAST print at that timestamp
        first_idx = np.flatnonzero(np.concatenate(([True], ts_raw[1:] != ts_raw[:-1])))
        last_idx = np.append(first_idx[1:] - 1, ts_raw.size - 1)
        variants["collapse_same_timestamp"] = (cts, px_raw[last_idx], csz)
        ts_floor = ts_raw.copy()
        variants["resolution_floor"] = (ts_floor, px_raw, sz_raw)

        base = {"ticker": r.ticker, "event_date_canonical": r.event_date_canonical,
                "momentum_pct": r.momentum_pct, "cohort_group": r.cohort_group,
                "segment": seg, "n_prints_raw": int(ts_raw.size),
                "n_tied_with_prev": n_tied,
                "share_tied": float(n_tied / max(ts_raw.size - 1, 1)),
                "resolution_floor_ns": res_floor_ns,
                "session_span_seconds": float(w["span_minutes"] * 60)}

        for tv, (tsv, pxv, szv) in variants.items():
            n = tsv.size
            dt = np.diff(tsv).astype(np.float64)
            if tv == "resolution_floor":
                dt = np.where(dt <= 0, float(res_floor_ns), dt)
            dt = dt / 1e9
            if n < min_n or dt.size < 10 or not np.all(dt > 0):
                ev_rows.append({**base, "tie_variant": tv, "window_fraction": None,
                                "min_prints": None, "status": "too_few_prints",
                                "has_threshold": False, "n_subbursts": 0,
                                "n_prints_variant": int(n)})
                continue
            ly = np.log10(dt)
            sess_move = float(pxv[-1] - pxv[0])
            span = float(tsv[-1] - tsv[0]) / 1e9

            for frac in (wgrid if tv == tie_ref else [wref]):
                yn = ly - moving_median_log(ly, frac)
                th = derive_threshold(yn, cfg)
                is_ref_cell = (tv == tie_ref and frac == wref)
                if is_ref_cell:
                    hist_rows.append({**base, "hist_density": th.get("hist_density", np.zeros(0)).tolist(),
                                      "hist_centres": th.get("hist_centres", np.zeros(0)).tolist(),
                                      "has_threshold": th["has_threshold"],
                                      "threshold_decades": th.get("threshold_decades"),
                                      "void": th.get("void"), "n_peaks": th.get("n_peaks", 0),
                                      "peak_left_decades": th.get("peak_left_decades"),
                                      "peak_right_decades": th.get("peak_right_decades"),
                                      "reason": th.get("reason"),
                                      "best_void": th.get("best_void")})
                if not th["has_threshold"]:
                    ev_rows.append({**base, "tie_variant": tv, "window_fraction": frac,
                                    "min_prints": mref, "status": "no_threshold",
                                    "has_threshold": False, "no_threshold_reason": th["reason"],
                                    "best_void": th.get("best_void"), "n_peaks": th.get("n_peaks", 0),
                                    "n_subbursts": 0, "n_prints_variant": int(n),
                                    "session_move": sess_move,
                                    "session_move_defined": bool(sess_move != 0)})
                    continue

                for mp in (mgrid if is_ref_cell else [mref]):
                    runs = runs_below(yn, th["threshold_decades"], mp)
                    rec = {**base, "tie_variant": tv, "window_fraction": frac, "min_prints": mp,
                           "status": "ok", "has_threshold": True,
                           "threshold_decades": th["threshold_decades"], "void": th["void"],
                           "n_peaks": th["n_peaks"], "n_subbursts": len(runs),
                           "n_prints_variant": int(n), "print_span_seconds": span,
                           "session_move": sess_move,
                           "session_move_defined": bool(sess_move != 0)}
                    covered = 0.0
                    prints_in = 0
                    largest_span = 0.0
                    if is_ref_cell and mp == mref:
                        prev_end = None
                        for j, (a, b) in enumerate(runs):
                            i0, i1 = a, b + 1
                            p = pxv[i0:i1 + 1]
                            dur = float(tsv[i1] - tsv[i0]) / 1e9
                            covered += dur
                            prints_in += (i1 - i0 + 1)
                            largest_span = max(largest_span, dur)
                            move = float(p[-1] - p[0])
                            sb_rows.append({
                                **base, "subburst_index": j,
                                "start_idx": i0, "end_idx": i1,
                                "start_ns": int(tsv[i0]), "end_ns": int(tsv[i1]),
                                "duration_seconds": dur, "n_prints": int(i1 - i0 + 1),
                                "share_session_prints": (i1 - i0 + 1) / n,
                                "volume": float(szv[i0:i1 + 1].sum()),
                                "subburst_move": move,
                                "move_share": (move / sess_move) if sess_move != 0 else np.nan,
                                "spacing_seconds": (float(tsv[i0] - prev_end) / 1e9
                                                    if prev_end is not None else np.nan),
                                "seconds_from_detection": (float(tsv[i0] - det_ns) / 1e9
                                                           if det_ns is not None else np.nan),
                                "seconds_from_peak": (float(tsv[i0] - int(pk_ns)) / 1e9
                                                      if pk_ns is not None and pd.notna(pk_ns) else np.nan),
                            })
                            prev_end = int(tsv[i1])
                        rec.update({"subburst_covered_seconds": covered,
                                    "share_session_prints_in_subbursts": prints_in / n,
                                    "share_session_seconds_in_subbursts": covered / span if span > 0 else np.nan,
                                    "largest_subburst_span_share": largest_span / span if span > 0 else np.nan})
                    ev_rows.append(rec)
        per_ev.append(time.perf_counter() - t_ev)
        if i % 20 == 0:
            print(f"  {i}/{len(cohort)} events ({time.perf_counter()-t0all:.0f}s)", flush=True)

    ev = pd.DataFrame(ev_rows)
    sb = pd.DataFrame(sb_rows)
    hi = pd.DataFrame(hist_rows)
    ev.to_parquet(os.path.join(art, "v4_event_metrics.parquet"), index=False)
    sb.to_parquet(os.path.join(art, "v4_subbursts.parquet"), index=False)
    hi.to_parquet(os.path.join(art, "v4_histograms.parquet"), index=False)

    write_json(os.path.join(art, "v4_pipeline_raw.json"),
               {"n_event_rows": int(len(ev)), "n_subbursts": int(len(sb)),
                "timing": {"total_seconds": round(time.perf_counter() - t0all, 1),
                           "max_per_event": round(float(np.max(per_ev)), 2)},
                "config_hash": chash})
    print(f"pipeline done: {len(ev)} event-rows, {len(sb):,} sub-bursts, "
          f"{time.perf_counter()-t0all:.0f}s, max/event {np.max(per_ev):.1f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
