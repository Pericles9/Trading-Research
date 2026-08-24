"""
Phase 10c Stage 1 -- T1.1 to T1.4 on the dev sample.

Pipeline, in the order the prompt specifies:
  T1.1  aggregate at D1 = 100 us (anchor-based)
  T1.2  centered clock-time window at D5 = 8 min, clipped at the RTH open/close
        and the day edges (A2.5); derived data floor from D4 = 1.5 per event;
        intervals whose window is under the floor -> insufficient_context
  T1.3  NORMALISE each interval by its window's local median, histogram the
        normalised log intervals, select the threshold as the burst-envelope
        boundary (A2.7.D17: argmax void across ALL troughs, never thresholded)
  T1.4  sub-bursts = maximal runs of normalised intervals below the threshold

Also carries the A2.7 silent-selection check as a DESCRIPTIVE report (demoted
from a gate by Revision 2).

Usage: .venv/Scripts/python.exe research/phase_10c/t1_subbursts.py [--full]
"""
from __future__ import annotations

import importlib.util as ilu
import os
import sys
import time

import numpy as np
import pandas as pd
from scipy.signal import find_peaks, peak_prominences

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "phase_10"))
import common as p10  # noqa: E402
from common import rel  # noqa: E402
_s = ilu.spec_from_file_location("c10c", os.path.join(HERE, "common.py"))
c10c = ilu.module_from_spec(_s); _s.loader.exec_module(c10c)

ART = "results/phase_10c/artifacts"


def peaks_poisson(cnt):
    pk, _ = find_peaks(cnt)
    if pk.size == 0:
        return pk, np.zeros(0)
    prom = peak_prominences(cnt, pk)[0]
    keep = prom > np.sqrt(np.maximum(cnt[pk], 1))
    return pk[keep], prom[keep]


def envelope_boundary(centers, dens, pks):
    """A2.7.D17 -- argmax void across ALL troughs. Void ranks, never gates (D13)."""
    best = None
    for a, b in zip(pks[:-1], pks[1:]):
        if b - a < 2:
            continue
        seg = dens[a + 1:b]
        t = a + 1 + int(np.argmin(seg))
        den = np.sqrt(dens[a] * dens[b])
        if den <= 0:
            continue
        v = float(1.0 - dens[t] / den)
        if best is None or v > best["void"]:
            best = {"idx": int(t), "loc": float(centers[t]), "void": v,
                    "peak_l": int(a), "peak_r": int(b)}
    return best


def main() -> int:
    full = "--full" in sys.argv
    cfg, chash = c10c.load_cfg(), c10c.cfg_hash()
    M, E = c10c.class_m(cfg), c10c.class_e(cfg)
    d1 = float(M["D1_sweep_floor_us"])
    k_min = float(M["D5_first_kernel_min"])
    F = float(M["D4_median_precision_factor"])

    dev = c10c.load_dev_sample(cfg).merge(c10c.load_detection(cfg), on=p10.COHORT_KEY, how="left")
    t0 = time.perf_counter()
    ev_rows, sb_rows = [], []
    wf = {"events": 0, "prints_raw": 0, "prints_tie_collapsed": 0, "prints_after_D1": 0,
          "intervals": 0, "intervals_insufficient_context": 0, "intervals_usable": 0,
          "subbursts": 0}

    for i, r in enumerate(dev.itertuples(index=False), 1):
        d = p10.read_event_trades(cfg, r.ticker, r.event_date_canonical, r.momentum_pct,
                                  offsets=(0,))
        s0 = d.get(0)
        if s0 is None or len(s0) == 0:
            continue
        wf["events"] += 1
        raw_ts = s0["sip_timestamp"].to_numpy()
        raw_px = s0["price"].to_numpy(dtype=np.float64)
        wf["prints_raw"] += int(raw_ts.size)

        # ---- T1.1 tie collapse then D1 aggregation, carrying VWAP
        uniq, inv = np.unique(raw_ts, return_inverse=True)
        wf["prints_tie_collapsed"] += int(uniq.size)
        sz = s0["size"].to_numpy(dtype=np.float64)
        wsum = np.bincount(inv, weights=raw_px * sz, minlength=uniq.size)
        ssum = np.bincount(inv, weights=sz, minlength=uniq.size)
        px_u = np.where(ssum > 0, wsum / np.maximum(ssum, 1e-12),
                        np.bincount(inv, weights=raw_px, minlength=uniq.size)
                        / np.maximum(np.bincount(inv, minlength=uniq.size), 1))
        agg_ts, _ = c10c.sweep_aggregate(uniq, d1)
        gi = np.searchsorted(uniq, agg_ts)
        # VWAP over each aggregated group
        bnd = np.append(gi, uniq.size)
        grp = np.repeat(np.arange(agg_ts.size), np.diff(bnd))
        gw = np.bincount(grp, weights=px_u[:uniq.size] * ssum, minlength=agg_ts.size)
        gs = np.bincount(grp, weights=ssum, minlength=agg_ts.size)
        agg_px = np.where(gs > 0, gw / np.maximum(gs, 1e-12), px_u[gi])
        wf["prints_after_D1"] += int(agg_ts.size)
        if agg_ts.size < 20:
            continue

        dt_s = np.diff(agg_ts).astype(np.float64) / 1e9
        keep = dt_s > 0
        dt_s, li = dt_s[keep], np.log10(dt_s[keep])
        mid = ((agg_ts[:-1].astype(np.float64) + agg_ts[1:].astype(np.float64)) / 2.0)[keep]
        wf["intervals"] += int(li.size)
        b = c10c.session_bounds(r.event_date_canonical)
        if b is None:
            continue

        # ---- T1.2 centered clock-time window, clipped at RTH + day edges (A2.5)
        half = k_min * 60.0 * 1e9 / 2.0
        edges = np.array([b["start_ns"], b["rth_open_ns"], b["rth_close_ns"], b["end_ns"]],
                         dtype=np.float64)
        seg_i = np.clip(np.searchsorted(edges, mid, "right") - 1, 0, len(edges) - 2)
        lo = np.maximum(mid - half, edges[seg_i])
        hi = np.minimum(mid + half, edges[seg_i + 1])
        clipped = (mid - half < edges[seg_i]) | (mid + half > edges[seg_i + 1])

        # Local median over the centered clock-time window, by time-based rolling
        # median PER SESSION BLOCK. Rolling within a block IS the A2.5 clipping
        # rule -- a window cannot reach across the RTH open or close because each
        # block rolls independently. n counts INTERVALS in the window, which is the
        # sample size the D4 floor derivation is about: the median is taken over
        # log intervals, not over prints.
        ser = pd.Series(li, index=pd.to_datetime(mid.astype("int64"), unit="ns"))
        loc_med = np.full(li.size, np.nan)
        wcount = np.zeros(li.size)
        win = f"{int(k_min)}min"
        for _bi in np.unique(seg_i):
            m_ = seg_i == _bi
            sub = ser[m_]
            if sub.size == 0:
                continue
            _roll = sub.rolling(win, center=True, min_periods=1)
            loc_med[m_] = _roll.median().to_numpy()
            wcount[m_] = _roll.count().to_numpy()

        sigma = float(np.std(li, ddof=1))
        floor = c10c.median_se_min_count(sigma, F)
        ok = wcount >= floor if np.isfinite(floor) else np.zeros(li.size, bool)
        wf["intervals_insufficient_context"] += int((~ok).sum())
        wf["intervals_usable"] += int(ok.sum())

        seg = getattr(r, "det_segment", None)
        key = {"ticker": r.ticker, "event_date_canonical": r.event_date_canonical,
               "cohort_group": r.cohort_group, "is_sidecar": bool(r.is_sidecar),
               "det_segment": seg}
        base = {**key, "n_prints_raw": int(raw_ts.size), "n_prints_agg": int(agg_ts.size),
                "n_intervals": int(li.size), "sigma_log10": sigma,
                "derived_floor": float(floor), "kernel_min": k_min,
                "clipped_fraction": float(clipped.mean()),
                "insufficient_context_fraction": float((~ok).mean())}
        if ok.sum() < 50:
            ev_rows.append({**base, "label": "insufficient_context", "threshold_norm": np.nan,
                            "threshold_seconds_median": np.nan, "void": np.nan,
                            "n_subbursts": 0, "n_peaks": 0})
            continue

        # ---- T1.3 local median normalisation, then the envelope boundary
        norm = li - loc_med
        nv = norm[ok & np.isfinite(norm)]
        if nv.size < 50:
            ev_rows.append({**base, "label": "insufficient_context", "threshold_norm": np.nan,
                            "threshold_seconds_median": np.nan, "void": np.nan,
                            "n_subbursts": 0, "n_peaks": 0})
            continue
        e_lo, e_hi = np.floor(nv.min() * 10) / 10, np.ceil(nv.max() * 10) / 10 + 0.1
        bins = np.arange(e_lo, e_hi, 0.1)
        cnt, _ = np.histogram(nv, bins=bins)
        centers = (bins[:-1] + bins[1:]) / 2.0
        dens = cnt / (cnt.sum() * 0.1)
        pks, _ = peaks_poisson(cnt)
        if pks.size < 2:
            ev_rows.append({**base, "label": "unimodal", "threshold_norm": np.nan,
                            "threshold_seconds_median": np.nan, "void": np.nan,
                            "n_subbursts": 0, "n_peaks": int(pks.size)})
            continue
        env = envelope_boundary(centers, dens, pks)
        if env is None:
            ev_rows.append({**base, "label": "no_threshold", "threshold_norm": np.nan,
                            "threshold_seconds_median": np.nan, "void": np.nan,
                            "n_subbursts": 0, "n_peaks": int(pks.size)})
            continue

        thr = env["loc"]
        thr_s = 10 ** (thr + loc_med[ok])            # threshold expressed in seconds, per interval
        # A2.7 descriptive check: tallest peak at or below the boundary not the fastest
        below = [p for p in pks if centers[p] <= thr]
        silent = bool(len(below) >= 2 and max(below, key=lambda q: dens[q]) != below[0])

        # ---- T1.4 sub-bursts = maximal runs of normalised intervals below threshold
        inb = ok & np.isfinite(norm) & (norm < thr)
        idx = np.flatnonzero(inb)
        runs = np.split(idx, np.flatnonzero(np.diff(idx) != 1) + 1) if idx.size else []
        det_ns = getattr(r, "det_ns", np.nan)
        for run in runs:
            if run.size < 1:
                continue
            t_start, t_end = agg_ts[run[0]], agg_ts[run[-1] + 1]
            p_start, p_end = agg_px[run[0]], agg_px[run[-1] + 1]
            sb_rows.append({**key, "n_intervals": int(run.size),
                            "start_ns": int(t_start), "end_ns": int(t_end),
                            "duration_s": float((t_end - t_start) / 1e9),
                            "t_from_detection_s": (float((t_start - det_ns) / 1e9)
                                                   if np.isfinite(det_ns) else np.nan),
                            "abs_move": float(abs(p_end - p_start))})
        wf["subbursts"] += len(runs)
        tot_move = float(np.abs(np.diff(agg_px)).sum())
        in_move = float(sum(abs(agg_px[run[-1] + 1] - agg_px[run[0]]) for run in runs))
        ev_rows.append({**base, "label": "ok", "threshold_norm": float(thr),
                        "threshold_seconds_median": float(np.median(thr_s)),
                        "void": env["void"], "n_subbursts": len(runs),
                        "n_peaks": int(pks.size), "silent_selection": silent,
                        "move_share_in_subbursts": (in_move / tot_move) if tot_move > 0 else np.nan})
        if i % 10 == 0:
            print(f"  {i}/{len(dev)} ({time.perf_counter()-t0:.0f}s)", flush=True)

    ev = pd.DataFrame(ev_rows)
    sb = pd.DataFrame(sb_rows)
    tag = "full" if full else "dev"
    ev.to_parquet(rel(f"{ART}/t1_{tag}_events.parquet"), index=False)
    sb.to_parquet(rel(f"{ART}/t1_{tag}_subbursts.parquet"), index=False)
    wf["timing_seconds"] = round(time.perf_counter() - t0, 1)
    wf["config_hash"] = chash
    c10c.write_json(rel(f"{ART}/t1_{tag}_waterfall.json"), wf)

    print(f"\nwaterfall: {wf}")
    print(f"\nlabels: {ev.label.value_counts().to_dict()}")
    o = ev[ev.label == "ok"]
    print(f"\nthreshold location (seconds), by segment  [D7 band "
          f"{E['D7_threshold_lo_ms']/1000:g} to {E['D7_threshold_hi_s']:g} s]:")
    for s, g in o.groupby(o.det_segment.fillna("unlabelled")):
        print(f"   {s:11s} n={len(g):2d}  median {g.threshold_seconds_median.median():10.4g} s")
    print(f"\nsub-burst duration (s), by segment  [D8 floor "
          f"{E['D8_min_median_duration_s']:g} s]:")
    if len(sb):
        sb2 = sb.merge(o[p10.COHORT_KEY[:2]], on=p10.COHORT_KEY[:2], how="inner")
        for s, g in sb2.groupby(sb2.det_segment.fillna("unlabelled")):
            print(f"   {s:11s} n={len(g):5d}  median {g.duration_s.median():10.4g} s")
    print(f"\nA2.7 descriptive: silent selection on "
          f"{int(o.silent_selection.sum())}/{len(o)} events with a threshold")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
