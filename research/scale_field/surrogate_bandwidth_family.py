#!/usr/bin/env python
"""Is the 30 s crossover the tape's, or the surrogate's bandwidth? (review 2026-09-09 s1)

THE PROBLEM, AND IT IS FATAL IF UNCHECKED. Three of the four routes behind the
scale-anchored finding -- Gate D vs surrogate, Gate E's ceiling, the excess-variance
control -- are three readings of ONE object, the rate-matched surrogate. That surrogate
simulates from lambda-hat estimated at bandwidth h, so BY CONSTRUCTION it contains
intensity structure down to h and none below it. A result of the form "real exceeds
surrogate below 30 s and matches it above 64 s" is therefore exactly what any tape
would produce, structure or not, if h were 30 s. The finding and the artifact are
observationally identical at a single bandwidth.

THE SEPARATING TEST is to sweep h and watch the crossover. If it tracks h, it is the
surrogate's. If it sits still while h sweeps a decade, it is the tape's.

BUT THE SWEEP HAS AN ARTIFACT AT EACH END, so the sweep alone does not settle it:

  h too LARGE -> the surrogate lacks structure the real tape has, and the excess is
                 spurious. This is the failure the review names.
  h too SMALL -> lambda-hat_h begins fitting the realisation itself rather than an
                 intensity (at the limit h -> 0 it IS the empirical measure and the
                 surrogate reproduces the tape exactly), so the excess vanishes
                 spuriously. This failure runs the OTHER way and would manufacture a
                 false retraction.

So the sweep is run on THREE base tapes, two of which have a known answer:

  REAL          the cohort tape. The question.
  S30 (+ve)     a surrogate built at h = 30 s, then treated as if it were real.
                Ground truth: intensity structure above 30 s, NOTHING below, no
                clustering anywhere. The procedure must recover a crossover AT 30 s
                and must recover it at every h. If it does not, the procedure cannot
                locate a crossover and the real tape's answer means nothing.
  POISSON (-ve) homogeneous, rate matched to the event. Ground truth: no structure at
                any scale. The ratio must be 1.0 everywhere, at every h. Any departure
                is the overfitting bias above, measured rather than argued.

The statistic is a ratio of like to like -- sd of the field on the base tape over sd of
the field on its own surrogate, at each scale -- so the sampling-noise floor cancels to
first order and no null table enters.

Regular hours only. Premarket is not poolable with it and is handled separately
(premarket_coverage.py, premarket_by_rate.py).
"""
from __future__ import annotations

import json
import os
import sys
import time

import numpy as np
from scipy.ndimage import gaussian_filter1d

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(REPO_ROOT, "research", "phase_10d_diag1"))

import adapter                                                      # noqa: E402
import event_panels as ep                                           # noqa: E402
from instrument_gates import cohort, jdump                          # noqa: E402
from scale_field import (collapse_same_timestamp, field, intervals,  # noqa: E402
                         seconds_since)

BANDWIDTHS = (5.0, 15.0, 30.0, 100.0, 300.0)
SCALES = np.geomspace(0.25, 512.0, 4 * 11 + 1)       # 4/octave
DT_LAM = 0.25
CROSS_LEVEL = 1.10        # "matches the surrogate" = ratio within 10%


def smooth_lambda(ts_ns, lo, hi, h, dt=DT_LAM):
    T = (hi - lo) / 1e9
    n = int(T / dt) + 1
    c = np.bincount(np.clip(((ts_ns - lo) / 1e9 / dt).astype(np.int64), 0, n - 1),
                    minlength=n).astype(float)
    return gaussian_filter1d(c, h / dt, mode="nearest") / dt, n, dt


def draw(lam, n, dt, lo, seed):
    rng = np.random.default_rng(seed)
    T, lmax = n * dt, float(lam.max())
    if lmax <= 0:
        return np.array([], dtype=np.int64)
    m = rng.poisson(lmax * T)
    u = np.sort(rng.uniform(0, T, m))
    keep = rng.random(m) < np.interp(u, (np.arange(n) + 0.5) * dt, lam) / lmax
    return (lo + u[keep] * 1e9).astype(np.int64)


def field_sd(arr, lo, hi, t_grid_ns, origin):
    """sd of F at each scale, time-weighted, on a shared grid so tapes are comparable."""
    if arr.size < 1000:
        return np.full(SCALES.size, np.nan)
    a = collapse_same_timestamp(arr)
    ts = seconds_since(a, origin)
    ev, x = intervals(a, origin=origin)
    tg = (t_grid_ns - origin).astype(np.float64) / 1e9
    Z = field(ts, ev, x, tg, SCALES, neff_min=8.0, edge_scales=4.0)["dlograte"]
    out = np.full(SCALES.size, np.nan)
    for j in range(SCALES.size):
        v = Z[:, j][np.isfinite(Z[:, j])]
        if v.size >= 400:
            out[j] = float(v.std())
    return out


def crossover(ratio, level=CROSS_LEVEL):
    """Coarsest scale at which the ratio is still above `level`, interpolated in log s.
    NaN if the ratio never clears it (no excess anywhere) or never drops (excess
    everywhere) -- both are reported as such rather than clamped to an endpoint."""
    r = np.asarray(ratio, float)
    ok = np.isfinite(r)
    if ok.sum() < 5:
        return float("nan")
    s, rr = SCALES[ok], r[ok]
    above = rr > level
    if not above.any():
        return float("nan")
    if above.all():
        return float("inf")
    last = np.flatnonzero(above)[-1]
    if last + 1 >= s.size:
        return float("inf")
    a, b = rr[last], rr[last + 1]
    if a == b:
        return float(s[last])
    f = (a - level) / (a - b)
    return float(np.exp(np.log(s[last]) + f * (np.log(s[last + 1]) - np.log(s[last]))))


def main() -> int:
    cfg = ep.load_config()
    n_ev = int(sys.argv[1]) if len(sys.argv) > 1 else 6
    events = list(cohort()["event_id"])[:n_ev]
    res = {"bandwidths": list(BANDWIDTHS), "scales": [float(v) for v in SCALES],
           "cross_level": CROSS_LEVEL, "note": __doc__, "events": {}}
    t0 = time.perf_counter()

    for eid in events:
        ts_ns, meta = adapter.load_event_prints_meta(eid, None)
        arr = collapse_same_timestamp(ts_ns)
        lo, hi = adapter.segment_bounds_ns(eid.split("_")[1])["rth"]
        real = arr[(arr >= lo) & (arr < hi)]
        if real.size < 5000:
            continue
        origin = int(real[0])
        _, grid_ns, _, _ = ep.column_grid(real, lo, hi, 1.13, 40000)

        lam30, n30, dt30 = smooth_lambda(real, lo, hi, 30.0)
        bases = {
            "real": real,
            "S30_positive_control": collapse_same_timestamp(
                draw(lam30, n30, dt30, lo, seed=911)),
            "poisson_negative_control": np.sort(
                np.random.default_rng(912).uniform(lo, hi, real.size).astype(np.int64)),
        }
        e = {}
        for bname, btape in bases.items():
            sd_base = field_sd(btape, lo, hi, grid_ns, origin)
            rows = {}
            for h in BANDWIDTHS:
                lam, n, dt = smooth_lambda(btape, lo, hi, h)
                sur = collapse_same_timestamp(draw(lam, n, dt, lo, seed=int(h) * 13 + 7))
                sd_sur = field_sd(sur, lo, hi, grid_ns, origin)
                ratio = sd_base / sd_sur
                rows[f"{h:g}"] = {
                    "ratio": [float(v) for v in ratio],
                    "sd_base": [float(v) for v in sd_base],
                    "sd_surrogate": [float(v) for v in sd_sur],
                    "crossover_s": crossover(ratio),
                    "surrogate_prints": int(sur.size)}
            e[bname] = {"prints": int(btape.size), "by_bandwidth": rows}
        res["events"][eid] = e
        c = lambda b: [e[b]["by_bandwidth"][f"{h:g}"]["crossover_s"] for h in BANDWIDTHS]
        print(f"  {eid.split('_')[0]:6s} crossover by h {list(BANDWIDTHS)}"
              f"\n         real {['%.0f' % v if np.isfinite(v) else str(v) for v in c('real')]}"
              f"\n         S30  {['%.0f' % v if np.isfinite(v) else str(v) for v in c('S30_positive_control')]}"
              f"\n         pois {['%.0f' % v if np.isfinite(v) else str(v) for v in c('poisson_negative_control')]}"
              f"   [{round(time.perf_counter()-t0)}s]", flush=True)

    jdump(res, "surrogate_bandwidth_family.json")

    print("\n" + "=" * 92)
    print("CROSSOVER (seconds) AGAINST SURROGATE BANDWIDTH h -- median across events")
    print("  tracks h  => the crossover is the surrogate's and the finding is withdrawn")
    print("  sits still => it is the tape's")
    print("=" * 92)
    print(f"{'base tape':28s}" + "".join(f"{'h=' + f'{h:g}':>12s}" for h in BANDWIDTHS))
    for b in ("real", "S30_positive_control", "poisson_negative_control"):
        v = []
        for h in BANDWIDTHS:
            x = [res["events"][e][b]["by_bandwidth"][f"{h:g}"]["crossover_s"]
                 for e in res["events"] if b in res["events"][e]]
            x = [q for q in x if np.isfinite(q)]
            v.append(np.median(x) if x else float("nan"))
        print(f"{b:28s}" + "".join(f"{q:12.1f}" if np.isfinite(q) else f"{'none':>12s}"
                                   for q in v))

    print("\nRATIO CURVES, real base, median across events (1.00 = surrogate reproduces "
          "the tape)")
    print(f"{'s':>9s}" + "".join(f"{'h=' + f'{h:g}':>10s}" for h in BANDWIDTHS))
    for j, s in enumerate(SCALES):
        if abs(np.log2(s) % 1) > 1e-6 and s != 0.25:
            continue
        row = []
        for h in BANDWIDTHS:
            x = [res["events"][e]["real"]["by_bandwidth"][f"{h:g}"]["ratio"][j]
                 for e in res["events"]]
            x = [q for q in x if np.isfinite(q)]
            row.append(np.median(x) if x else float("nan"))
        print(f"{s:9.2f}" + "".join(f"{q:10.2f}" for q in row))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
