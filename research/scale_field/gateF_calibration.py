#!/usr/bin/env python
"""Calibrate the negative-run width statistic before its flatness is quoted (review s4).

THE TWO REFERENCE POINTS.

  PURE NOISE -> 2.00.  Derived, not assumed. lam_hat from a Poisson tape smoothed at
  scale s has autocovariance proportional to exp(-t^2/4s^2), so its spectrum is
  proportional to exp(-w^2 s^2). For a stationary Gaussian process the zero-crossing
  rate of the k-th derivative is (1/pi)*sqrt(lambda_{2k+2}/lambda_{2k}) with
  lambda_n the n-th spectral moment. F < 0 iff lam_hat'' < 0, so k = 2:

      lambda_6/lambda_4 = [Gamma(7/2)/s^7] / [Gamma(5/2)/s^5] = 2.5/s^2
      rate = sqrt(2.5)/(pi s) = 0.5033/s   ->   mean run length = 1.987 s

  so mean width/s -> 1.987, which is the 2.00 the review states.

  A BUMP OF WIDTH sigma READ AT SCALE s -> 2*sqrt(1 + sigma^2/s^2).  Convolving a
  Gaussian of width sigma with one of width s gives width sqrt(sigma^2+s^2), and the
  second derivative of a Gaussian is negative inside +/- its own width, so the negative
  region is 2*sqrt(sigma^2+s^2) wide. 2.83 at sigma = s, 2.00 as sigma -> 0.

WHAT IS BEING CALIBRATED is not the theory but MY ESTIMATOR OF IT: runs are measured by
summing dt over contiguous negative cells on a print-indexed grid, they are cut by NaN
from the n_eff and edge masks, and they are cut by the segment boundary. Each of those
truncates runs and biases the statistic DOWN. Gate F reported 1.85 where theory says
1.987, and this establishes how much of that gap is the estimator.

Three grids are run so the cause is separable rather than argued about:
  uniform_fine     -- uniform t-grid at s/8, no masks. The estimator's own ceiling.
  uniform_masked   -- same grid, n_eff and edge masks on. Isolates the masks.
  print_indexed    -- the grid Gate F actually ran on. Isolates the grid.
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(REPO_ROOT, "research", "phase_10d_diag1"))

import event_panels as ep                                          # noqa: E402
from instrument_gates import OUT, jdump, runs_from_bool            # noqa: E402
from scale_field import (collapse_same_timestamp, field, intervals,  # noqa: E402
                         seconds_since)

THEORY_NOISE = np.sqrt(2.5) / np.pi          # crossings per s -> mean run = 1/this
NOISE_TARGET = 1.0 / THEORY_NOISE             # 1.9869


def widths(F, t, dt):
    """Gate F's statistic, unchanged: contiguous cells with F < 0, width = sum of dt."""
    neg = np.isfinite(F) & (F < 0)
    w = [float(np.nansum(dt[a:b])) for a, b in runs_from_bool(neg)]
    return np.array([x for x in w if x > 0])


def interior(F, t, dt, edge):
    """Drop runs that touch either end of the evaluated span. A truncated run is not a
    measurement of a run length, and both references are for COMPLETE runs."""
    neg = np.isfinite(F) & (F < 0)
    out = []
    r = runs_from_bool(neg)
    for a, b in r:
        if a == 0 or b >= len(F):
            continue
        if not (np.isfinite(F[a - 1]) and np.isfinite(F[min(b, len(F) - 1)])):
            continue                              # bounded by NaN, not by a crossing
        if t[a] < t[0] + edge or t[b - 1] > t[-1] - edge:
            continue
        out.append(float(np.nansum(dt[a:b])))
    return np.array([x for x in out if x > 0])


def run_case(ts, tg, scales, neff_min, tag):
    ev, x = ts[1:], np.log10(np.diff(ts))
    f = field(ts, ev, x, tg, scales, neff_min=neff_min, edge_scales=4.0)
    dt = np.gradient(tg)
    rows = []
    for j, s in enumerate(scales):
        F = f["dlograte"][:, j]
        if np.isfinite(F).sum() < 500:
            continue
        w_all = widths(F, tg, dt)
        w_int = interior(F, tg, dt, edge=6 * s)
        if w_int.size < 30:
            continue
        rows.append({"grid": tag, "s": float(s),
                     "n_runs_all": int(w_all.size), "n_runs_interior": int(w_int.size),
                     "mean_all_over_s": float(w_all.mean() / s),
                     "median_all_over_s": float(np.median(w_all) / s),
                     "mean_interior_over_s": float(w_int.mean() / s),
                     "median_interior_over_s": float(np.median(w_int) / s),
                     "defined_share": float(np.isfinite(F).mean())})
    return rows


def main() -> int:
    rng = np.random.default_rng(5)
    scales = np.geomspace(1.0, 64.0, 25)
    res = {"theory": {"noise_mean_width_over_s": NOISE_TARGET,
                      "bump_formula": "2*sqrt(1 + sigma^2/s^2)",
                      "bump_sigma_eq_s": 2 * np.sqrt(2)},
           "note": __doc__, "noise": [], "bump": []}

    # ---------------- reference 1: pure homogeneous Poisson ----------------
    lam, T = 40.0, 12000.0
    ts = np.sort(rng.uniform(0, T, rng.poisson(lam * T)))
    print(f"noise reference: homogeneous Poisson, lambda = {lam}/s, T = {T:.0f}s, "
          f"{ts.size:,} prints")
    for tag, neff, npts in (("uniform_fine", 0.0, 300000),
                            ("uniform_masked", 8.0, 300000)):
        tg = np.linspace(0, T, npts)
        res["noise"] += run_case(ts, tg, scales, neff, tag)
    # the grid Gate F actually ran on
    arr = (ts * 1e9).astype(np.int64)
    _, gns, _, _ = ep.column_grid(arr, int(arr[0]), int(arr[-1]), 1.13, 60000)
    tg = (gns - arr[0]).astype(np.float64) / 1e9
    res["noise"] += run_case(ts, tg, scales, 8.0, "print_indexed")

    print(f"\n{'grid':>16s} {'s':>7s} {'mean all/s':>11s} {'mean interior/s':>16s} "
          f"{'median int/s':>13s} {'n runs':>8s}   target {NOISE_TARGET:.3f}")
    for r in res["noise"]:
        if abs(np.log2(r["s"]) % 1) > 1e-6:
            continue
        print(f"{r['grid']:>16s} {r['s']:7.2f} {r['mean_all_over_s']:11.3f} "
              f"{r['mean_interior_over_s']:16.3f} {r['median_interior_over_s']:13.3f} "
              f"{r['n_runs_interior']:8d}")

    # ---------------- reference 2: an injected bump of width sigma ----------------
    print(f"\nbump reference: sigma = 8 s on a {lam}/s background, "
          f"width of the negative run CONTAINING THE BUMP CENTRE")
    sig, amp, T2 = 8.0, 400.0, 2000.0
    base = np.sort(rng.uniform(0, T2, rng.poisson(lam * T2)))
    bump = rng.normal(T2 / 2, sig, rng.poisson(amp * sig * np.sqrt(2 * np.pi)))
    tsb = np.sort(np.concatenate([base, bump[(bump > 0) & (bump < T2)]]))
    tgb = np.linspace(0, T2, 200000)
    dtb = np.gradient(tgb)
    scb = np.array([sig / 4, sig / 2, sig, 2 * sig, 4 * sig])
    fb = field(tsb, tsb[1:], np.log10(np.diff(tsb)), tgb, scb, neff_min=8.0,
               edge_scales=4.0)
    print(f"{'s':>7s} {'s/sigma':>8s} {'measured W/s':>13s} {'predicted W/s':>14s} "
          f"{'ratio':>7s}")
    for j, s in enumerate(scb):
        F = fb["dlograte"][:, j]
        neg = np.isfinite(F) & (F < 0)
        w = None
        for a, b in runs_from_bool(neg):
            if tgb[a] <= T2 / 2 <= tgb[b - 1]:
                w = float(np.nansum(dtb[a:b]))
                break
        pred = 2 * np.sqrt(1 + (sig / s) ** 2)
        row = {"s": float(s), "s_over_sigma": float(s / sig),
               "measured_over_s": (w / s) if w else float("nan"),
               "predicted_over_s": float(pred),
               "ratio": (w / s / pred) if w else float("nan")}
        res["bump"].append(row)
        print(f"{s:7.2f} {s/sig:8.3f} {row['measured_over_s']:13.3f} {pred:14.3f} "
              f"{row['ratio']:7.3f}")

    jdump(res, "gateF_calibration.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
