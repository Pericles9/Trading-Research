"""
Phase 10c Stage 0 -- T0.1 to T0.5, the interval landscape.

Produces NO sub-bursts, selects NO threshold, computes NO void parameter and
applies NO normalisation window (A1.2). Every histogram is per event; nothing is
pooled across events on physical time.

Usage: .venv/Scripts/python.exe research/phase_10c/t0_landscape.py
"""
from __future__ import annotations

import os
import sys
import time

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "phase_10"))
from common import rel  # noqa: E402  (phase_10 common)
import common as p10  # noqa: E402
sys.path.insert(0, HERE)
import importlib.util as _ilu  # noqa: E402
_spec = _ilu.spec_from_file_location("c10c", os.path.join(HERE, "common.py"))
c10c = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(c10c)

ART = "results/phase_10c/artifacts"
PROM_SWEEP = [0.01, 0.02, 0.05, 0.10, 0.20]


def summarise_hist(logs, prom_frac):
    """Leftmost mode, first local minimum right of it, and the mass below that
    minimum. Reported per prominence value -- the config fixes the criterion but
    not its value, so Stage 0 sweeps it rather than choosing (see digest)."""
    centers, dens, cnt = c10c.hist_density(logs)
    pk = c10c.find_modes(centers, dens, prom_frac)
    if pk.size == 0:
        return {"n_peaks": 0, "leftmost_mode_log10s": None, "first_trough_log10s": None,
                "frac_below_trough": None, "largest_peak_log10s": None}
    left = int(pk[0])
    tr = c10c.first_trough_right_of(centers, dens, left)
    frac = float((logs < centers[tr]).mean()) if tr is not None else None
    big = int(pk[int(np.argmax(dens[pk]))])
    return {"n_peaks": int(pk.size),
            "leftmost_mode_log10s": float(centers[left]),
            "first_trough_log10s": float(centers[tr]) if tr is not None else None,
            "frac_below_trough": frac,
            "largest_peak_log10s": float(centers[big])}


def main() -> int:
    cfg, chash = c10c.load_cfg(), c10c.cfg_hash()
    dev = c10c.load_dev_sample(cfg)
    det = c10c.load_detection(cfg)
    dev = dev.merge(det, on=p10.COHORT_KEY, how="left")
    floors = cfg["stage_0_sweeps"]["T0_2_candidate_sweep_floors_us"]
    kernels = cfg["stage_0_sweeps"]["T0_5_candidate_kernels_min"]
    factors = cfg["stage_0_sweeps"]["T0_4_candidate_precision_factors"]
    k4 = cfg["stage_0_sweeps"]["T0_4_sensitivity_kernel_min"]

    t0 = time.perf_counter()
    ev_rows, floor_rows, clip_rows, d4_rows, dens_rows = [], [], [], [], []
    waterfall = {"events_attempted": 0, "events_with_trades": 0, "raw_prints": 0,
                 "prints_after_tie_collapse": 0, "intervals_raw": 0}

    for i, r in enumerate(dev.itertuples(index=False), 1):
        waterfall["events_attempted"] += 1
        d = p10.read_event_trades(cfg, r.ticker, r.event_date_canonical, r.momentum_pct,
                                  offsets=(0,))
        s0 = d.get(0)
        if s0 is None or len(s0) == 0:
            continue
        waterfall["events_with_trades"] += 1
        raw = s0["sip_timestamp"].to_numpy()
        waterfall["raw_prints"] += int(raw.size)
        ts = c10c.collapse_ties(raw)
        waterfall["prints_after_tie_collapse"] += int(ts.size)
        logs = c10c.log_intervals(ts)
        waterfall["intervals_raw"] += int(logs.size)
        bounds = c10c.session_bounds(r.event_date_canonical)

        key = {"ticker": r.ticker, "event_date_canonical": r.event_date_canonical,
               "cohort_group": r.cohort_group, "is_sidecar": bool(r.is_sidecar),
               "det_segment": getattr(r, "det_segment", None)}

        # ---- T0.1 raw landscape, per prominence value
        for pf in PROM_SWEEP:
            ev_rows.append({**key, "prominence_frac": pf, "n_prints_raw": int(raw.size),
                            "n_prints_tie_collapsed": int(ts.size),
                            "n_intervals": int(logs.size),
                            "sigma_log10": float(np.std(logs, ddof=1)) if logs.size > 1 else np.nan,
                            "median_log10s": float(np.median(logs)) if logs.size else np.nan,
                            **summarise_hist(logs, pf)})

        # keep the density curve at the middle prominence for charting
        centers, dens, _ = c10c.hist_density(logs)
        for ci in np.flatnonzero(dens > 0):
            dens_rows.append({**key, "log10s": float(centers[ci]), "density": float(dens[ci]),
                              "stage": "raw"})

        # ---- T0.2 / T0.3 sweep-floor sensitivity
        for f in floors:
            agg, absorbed = c10c.sweep_aggregate(ts, f)
            lg = c10c.log_intervals(agg)
            row = {**key, "floor_us": f, "n_prints_in": int(ts.size),
                   "n_events_out": int(agg.size), "n_absorbed": int(absorbed),
                   "frac_absorbed": float(absorbed / ts.size) if ts.size else np.nan,
                   "n_intervals": int(lg.size)}
            for pf in PROM_SWEEP:
                s = summarise_hist(lg, pf)
                row[f"leftmost_mode_p{pf}"] = s["leftmost_mode_log10s"]
                row[f"largest_peak_p{pf}"] = s["largest_peak_log10s"]
                row[f"n_peaks_p{pf}"] = s["n_peaks"]
            floor_rows.append(row)

        # ---- T0.5 clipped-window fraction, both boundary definitions
        if bounds:
            for k in kernels:
                for rth in (False, True):
                    c = c10c.clipped_fraction(ts, bounds, k, rth)
                    clip_rows.append({**key, "kernel_min": k, "cut_at_rth": rth, **c})

        # ---- T0.4 print density + D4 sensitivity at the 4-minute kernel
        if bounds and ts.size > 1:
            span_min = (bounds["end_ns"] - bounds["start_ns"]) / 6e10
            per_min = ts.size / span_min if span_min else np.nan
            edges = np.arange(bounds["start_ns"], bounds["end_ns"] + 6e10, 6e10)
            pm, _ = np.histogram(ts, bins=edges)
            sigma = float(np.std(logs, ddof=1)) if logs.size > 1 else np.nan
            mid = (ts[:-1].astype(np.float64) + ts[1:].astype(np.float64)) / 2.0
            half = k4 * 60.0 * 1e9 / 2.0
            lo = np.maximum(mid - half, float(bounds["start_ns"]))
            hi = np.minimum(mid + half, float(bounds["end_ns"]))
            wc = np.searchsorted(ts, hi, "right") - np.searchsorted(ts, lo, "left")
            base = {**key, "prints_per_min_mean": float(per_min),
                    "prints_per_min_p10": float(np.percentile(pm, 10)),
                    "prints_per_min_median": float(np.median(pm)),
                    "prints_per_min_p90": float(np.percentile(pm, 90)),
                    "window_count_median": float(np.median(wc)), "sigma_log10": sigma}
            for fac in factors:
                need = c10c.median_se_min_count(sigma, fac)
                d4_rows.append({**base, "precision_factor": fac, "derived_min_count": need,
                                "too_few_prints_fraction": float((wc < need).mean())
                                if np.isfinite(need) else np.nan})

        if i % 10 == 0:
            print(f"  {i}/{len(dev)} events ({time.perf_counter()-t0:.0f}s)", flush=True)

    os.makedirs(rel(ART), exist_ok=True)
    pd.DataFrame(ev_rows).to_parquet(rel(f"{ART}/t0_1_raw_landscape.parquet"), index=False)
    pd.DataFrame(floor_rows).to_parquet(rel(f"{ART}/t0_2_floor_sensitivity.parquet"), index=False)
    pd.DataFrame(clip_rows).to_parquet(rel(f"{ART}/t0_5_clipped_fraction.parquet"), index=False)
    pd.DataFrame(d4_rows).to_parquet(rel(f"{ART}/t0_4_density_d4.parquet"), index=False)
    pd.DataFrame(dens_rows).to_parquet(rel(f"{ART}/t0_1_density_curves.parquet"), index=False)
    waterfall["timing_seconds"] = round(time.perf_counter() - t0, 1)
    waterfall["config_hash"] = chash
    c10c.write_json(rel(f"{ART}/t0_waterfall.json"), waterfall)

    print(f"\nwaterfall: {waterfall}")
    e = pd.DataFrame(ev_rows)
    print(f"\nT0.1 leftmost mode (log10 s), across {e.ticker.nunique()} events, by prominence:")
    for pf in PROM_SWEEP:
        s = e[e.prominence_frac == pf]["leftmost_mode_log10s"].dropna()
        print(f"   prom={pf:<5} n={len(s):3d}  median {s.median():+.2f}  "
              f"p10 {s.quantile(.1):+.2f}  p90 {s.quantile(.9):+.2f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
