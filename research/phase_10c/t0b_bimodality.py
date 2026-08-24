"""
Phase 10c Stage 0b -- T0b.1 to T0b.5, the bimodality precondition.

Runs at D1 = 100 us. Inherits every Stage 0 constraint: no sub-bursts, no
cross-event pooling, per-event histograms only, no normalisation window applied.
Stage 0b MAY compute a candidate trough and void parameter because that is the
precondition being tested (A2.3).

Prominence floor is DERIVED, not chosen (A2.4 Part 1): a peak is kept only if its
prominence in COUNT units exceeds the Poisson counting noise sqrt(k) in its own
bin. That is a per-peak test and needs no global constant.

Usage: .venv/Scripts/python.exe research/phase_10c/t0b_bimodality.py
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
GRID = [1, 2, 4, 8, 16, 32, 64]          # base-2 rungs up to D11 = 64


def peaks_poisson(cnt: np.ndarray):
    """A2.4 Part 1. All peaks whose prominence in COUNT units exceeds sqrt(k) at
    their own bin. Returns (kept_idx, prominence_counts_kept)."""
    pk, _ = find_peaks(cnt)
    if pk.size == 0:
        return pk, np.zeros(0)
    prom = peak_prominences(cnt, pk)[0]
    keep = prom > np.sqrt(np.maximum(cnt[pk], 1))
    return pk[keep], prom[keep]


def void_between(centers, dens, i, j):
    """Void at the deepest trough between two peak indices."""
    a, b = (i, j) if i < j else (j, i)
    if b - a < 2:
        return None
    seg = dens[a + 1:b]
    t = a + 1 + int(np.argmin(seg))
    denom = np.sqrt(dens[a] * dens[b])
    if denom <= 0:
        return None
    return {"trough_idx": t, "trough_log10s": float(centers[t]),
            "void": float(1.0 - dens[t] / denom),
            "peak_lo_log10s": float(centers[a]), "peak_hi_log10s": float(centers[b])}


def top_two(pk, prom):
    if pk.size < 2:
        return None
    o = np.argsort(prom)[::-1][:2]
    return int(pk[o[0]]), int(pk[o[1]])


def main() -> int:
    cfg, chash = c10c.load_cfg(), c10c.cfg_hash()
    M, E = c10c.class_m(cfg), c10c.class_e(cfg)
    d1 = float(M["D1_sweep_floor_us"])
    s0b = cfg["stage_0b_sweeps"]
    sweep = s0b["T0b_4_prominence_sweep"]
    factors = s0b["T0b_3_candidate_precision_factors"]
    nd_win = float(s0b["T0b_5_near_detection_window_min"])

    dev = c10c.load_dev_sample(cfg).merge(c10c.load_detection(cfg), on=p10.COHORT_KEY, how="left")
    t0 = time.perf_counter()
    peak_rows, ev_rows, sweep_rows, tf_rows, curve_rows = [], [], [], [], []
    wf = {"events": 0, "prints_raw": 0, "prints_tie_collapsed": 0,
          "prints_after_D1_aggregation": 0, "intervals": 0}

    for i, r in enumerate(dev.itertuples(index=False), 1):
        d = p10.read_event_trades(cfg, r.ticker, r.event_date_canonical, r.momentum_pct,
                                  offsets=(0,))
        s0 = d.get(0)
        if s0 is None or len(s0) == 0:
            continue
        wf["events"] += 1
        raw = s0["sip_timestamp"].to_numpy()
        wf["prints_raw"] += int(raw.size)
        ts = c10c.collapse_ties(raw)
        wf["prints_tie_collapsed"] += int(ts.size)
        agg, absorbed = c10c.sweep_aggregate(ts, d1)
        wf["prints_after_D1_aggregation"] += int(agg.size)
        logs = c10c.log_intervals(agg)
        wf["intervals"] += int(logs.size)
        if logs.size < 10:
            continue
        centers, dens, cnt = c10c.hist_density(logs)
        bounds = c10c.session_bounds(r.event_date_canonical)
        seg = getattr(r, "det_segment", None)
        key = {"ticker": r.ticker, "event_date_canonical": r.event_date_canonical,
               "cohort_group": r.cohort_group, "is_sidecar": bool(r.is_sidecar),
               "det_segment": seg}

        # ---------------- T0b.1 full peak set, Poisson-derived floor
        pk, prom = peaks_poisson(cnt)
        for p_, pr in zip(pk, prom):
            peak_rows.append({**key, "peak_log10s": float(centers[p_]),
                              "prominence_counts": float(pr), "bin_count": int(cnt[p_]),
                              "poisson_floor": float(np.sqrt(max(cnt[p_], 1)))})
        for ci in np.flatnonzero(dens > 0):
            curve_rows.append({**key, "log10s": float(centers[ci]),
                               "density": float(dens[ci]),
                               "is_peak": bool(ci in set(pk.tolist()))})

        # ---------------- T0b.2 void at the deepest trough between the top two peaks
        sigma = float(np.std(logs, ddof=1))
        row = {**key, "n_prints_tie_collapsed": int(ts.size), "n_prints_agg": int(agg.size),
               "frac_absorbed_D1": float(absorbed / ts.size) if ts.size else np.nan,
               "n_intervals": int(logs.size), "n_peaks": int(pk.size),
               "sigma_log10_post_agg": sigma,
               "median_log10s_post_agg": float(np.median(logs))}
        tt = top_two(pk, prom)
        if tt is None:
            row.update({"label": "unimodal", "void": np.nan, "trough_log10s": np.nan,
                        "peak_lo_log10s": float(centers[pk[0]]) if pk.size else np.nan,
                        "peak_hi_log10s": np.nan})
        else:
            v = void_between(centers, dens, *tt)
            if v is None:
                row.update({"label": "adjacent_peaks", "void": np.nan,
                            "trough_log10s": np.nan,
                            "peak_lo_log10s": float(centers[min(tt)]),
                            "peak_hi_log10s": float(centers[max(tt)])})
            else:
                row.update({"label": "bimodal", **v})
                row.pop("trough_idx", None)
        ev_rows.append(row)

        # ---------------- T0b.4 prominence sensitivity (relative-to-max sweep)
        for pf in sweep:
            p2 = c10c.find_modes(centers, dens, pf)
            if p2.size >= 2:
                pr2 = peak_prominences(dens, p2)[0]
                o = np.argsort(pr2)[::-1][:2]
                a, b = int(p2[o[0]]), int(p2[o[1]])
                vv = void_between(centers, dens, a, b)
                sweep_rows.append({**key, "prominence_frac": pf, "n_peaks": int(p2.size),
                                   "peak_lo_log10s": float(centers[min(a, b)]),
                                   "peak_hi_log10s": float(centers[max(a, b)]),
                                   "trough_log10s": vv["trough_log10s"] if vv else np.nan,
                                   "void": vv["void"] if vv else np.nan})
            else:
                sweep_rows.append({**key, "prominence_frac": pf, "n_peaks": int(p2.size),
                                   "peak_lo_log10s": np.nan, "peak_hi_log10s": np.nan,
                                   "trough_log10s": np.nan, "void": np.nan})

        # ---------------- T0b.3 / T0b.5 density and the D4 floor across the grid
        if bounds:
            span_min = (bounds["end_ns"] - bounds["start_ns"]) / 6e10
            sess_ppm = agg.size / span_min if span_min else np.nan
            det_ns = getattr(r, "det_ns", None)
            near_ppm = np.nan
            if det_ns is not None and np.isfinite(float(det_ns)):
                lo = float(det_ns) - nd_win * 30e9
                hi = float(det_ns) + nd_win * 30e9
                lo = max(lo, float(bounds["start_ns"])); hi = min(hi, float(bounds["end_ns"]))
                if hi > lo:
                    n_in = int(np.searchsorted(agg, hi) - np.searchsorted(agg, lo))
                    near_ppm = n_in / ((hi - lo) / 6e10)
            base = {**key, "sigma_log10_post_agg": sigma,
                    "session_prints_per_min": float(sess_ppm),
                    "near_detection_prints_per_min": float(near_ppm)}
            mid = (agg[:-1].astype(np.float64) + agg[1:].astype(np.float64)) / 2.0
            for k_ in GRID:
                half = k_ * 60.0 * 1e9 / 2.0
                # A2.5: clip at the RTH open and close as well as the day edges
                edges = np.array([bounds["start_ns"], bounds["rth_open_ns"],
                                  bounds["rth_close_ns"], bounds["end_ns"]], dtype=np.float64)
                li = np.searchsorted(edges, mid, "right") - 1
                li = np.clip(li, 0, len(edges) - 2)
                lo_b, hi_b = edges[li], edges[li + 1]
                lo = np.maximum(mid - half, lo_b)
                hi = np.minimum(mid + half, hi_b)
                wc = np.searchsorted(agg, hi, "right") - np.searchsorted(agg, lo, "left")
                for fac in factors:
                    need = c10c.median_se_min_count(sigma, fac)
                    tf_rows.append({**base, "kernel_min": k_, "precision_factor": fac,
                                    "derived_min_count": need,
                                    "window_count_median": float(np.median(wc)),
                                    "too_few_prints_fraction": float((wc < need).mean())
                                    if np.isfinite(need) else np.nan})
        if i % 10 == 0:
            print(f"  {i}/{len(dev)} events ({time.perf_counter()-t0:.0f}s)", flush=True)

    os.makedirs(rel(ART), exist_ok=True)
    pd.DataFrame(peak_rows).to_parquet(rel(f"{ART}/t0b_1_peaks.parquet"), index=False)
    pd.DataFrame(ev_rows).to_parquet(rel(f"{ART}/t0b_2_void.parquet"), index=False)
    pd.DataFrame(sweep_rows).to_parquet(rel(f"{ART}/t0b_4_prominence_sweep.parquet"), index=False)
    pd.DataFrame(tf_rows).to_parquet(rel(f"{ART}/t0b_3_5_density_floor.parquet"), index=False)
    pd.DataFrame(curve_rows).to_parquet(rel(f"{ART}/t0b_1_curves.parquet"), index=False)
    wf["timing_seconds"] = round(time.perf_counter() - t0, 1)
    wf["D1_sweep_floor_us"] = d1
    wf["config_hash"] = chash
    c10c.write_json(rel(f"{ART}/t0b_waterfall.json"), wf)

    e = pd.DataFrame(ev_rows)
    print(f"\nwaterfall: {wf}")
    print(f"\nT0b.1 peak count (Poisson-derived floor): "
          f"{e.n_peaks.describe()[['min','25%','50%','75%','max']].to_dict()}")
    print(f"T0b.2 labels: {e.label.value_counts().to_dict()}")
    print("\nT0b.2 VOID by segment (the T0b.6 gate statistic):")
    for s, g in e.groupby(e.det_segment.fillna("UNLABELLED")):
        v = g["void"].dropna()
        if len(v):
            print(f"   {s:12s} n={len(v):2d}/{len(g):2d}  median {v.median():.4f}  "
                  f"p10 {v.quantile(.1):.4f}  p90 {v.quantile(.9):.4f}")
        else:
            print(f"   {s:12s} n=0/{len(g)}  no void computable")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
