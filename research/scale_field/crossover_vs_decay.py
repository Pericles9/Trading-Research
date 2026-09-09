#!/usr/bin/env python
"""Does the crossover track the event's own timescale, or is it a cohort constant?
(review 2026-09-09 s4)

THE PREDICTION. If the crossover is where the read scale starts to resolve the event's
own rise-and-decay shape -- rather than a microstructure constant -- it should sit at a
fixed FRACTION of that shape's timescale, and should therefore move from event to event.
Fast-decaying events show it finer, slow ones coarser.

  tracks     -> the mechanism is confirmed and every event gets its own operating scale
                instead of a cohort-wide number. That is the difference between a value
                that holds on this cohort and one that transfers.
  no track   -> the crossover is a property of the tape shared across events, which is
                the more surprising result and worth its own investigation.

THE TIMESCALE, computed from the object that already exists rather than imported from
elsewhere. The surrogate's own curvature scale is

    L(t) = sqrt( | lambda_h / lambda_h'' | )

evaluated on the 30 s intensity -- the same lambda_h the surrogate is drawn from, so it
is the curvature the ENVELOPE actually has rather than a separate estimate of a
different thing. It is summarised intensity-weighted, because the envelope's curvature
where there is no tape is not what the read responds to.

THE CROSSOVER used here is the one measured at each bandwidth in bandwidth_floor.py, so
this regression inherits that run's caveat: the crossover LEVEL tracks h and is not a
tape property. What is being asked here is different and survives it -- whether the
crossover VARIES ACROSS EVENTS with their envelope curvature, at fixed h. A slope near
zero at every h means the crossover is not set by the envelope shape; a consistent
positive slope means it is.
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np
from scipy.ndimage import gaussian_filter1d

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(REPO_ROOT, "research", "phase_10d_diag1"))

import adapter                                                     # noqa: E402
from instrument_gates import OUT, jdump, ols                       # noqa: E402
from scale_field import collapse_same_timestamp                    # noqa: E402
from surrogate_bandwidth_family import smooth_lambda               # noqa: E402


def curvature_scale(lam, dt, h=30.0):
    """Intensity-weighted median of L = sqrt(|lam / lam''|), the envelope's own scale."""
    sg = h / dt
    a0 = gaussian_filter1d(lam, sg, order=0, mode="nearest")
    a2 = gaussian_filter1d(lam, sg, order=2, mode="nearest") / (dt * dt)
    ok = (a0 > 0) & np.isfinite(a2) & (np.abs(a2) > 0)
    if ok.sum() < 100:
        return float("nan")
    L = np.sqrt(np.abs(a0[ok] / a2[ok]))
    w = a0[ok]
    i = np.argsort(L)
    c = np.cumsum(w[i]) / w[i].sum()
    return float(np.interp(0.5, c, L[i]))


def main() -> int:
    src = os.path.join(OUT, "bandwidth_floor.json")
    if not os.path.exists(src):
        src = os.path.join(OUT, "surrogate_bandwidth_family.json")
    with open(src, encoding="utf-8") as f:
        fam = json.load(f)
    print("crossovers read from", os.path.basename(src))

    rows = []
    for eid in fam["events"]:
        ts_ns, meta = adapter.load_event_prints_meta(eid, None)
        arr = collapse_same_timestamp(ts_ns)
        lo, hi = adapter.segment_bounds_ns(eid.split("_")[1])["rth"]
        real = arr[(arr >= lo) & (arr < hi)]
        lam, n, dt = smooth_lambda(real, lo, hi, 30.0)
        rows.append({
            "event_id": eid,
            "prints_rth": int(real.size),
            "mean_rate": float(real.size / ((hi - lo) / 1e9)),
            "envelope_curvature_scale_s": curvature_scale(lam, dt),
            "crossover_by_h": {h: fam["events"][eid]["real"]["by_bandwidth"][h]["crossover_s"]
                               for h in fam["events"][eid]["real"]["by_bandwidth"]}})
    res = {"source": os.path.basename(src), "note": __doc__, "events": rows,
           "regressions": {}}

    L = np.array([r["envelope_curvature_scale_s"] for r in rows], float)
    R = np.array([r["mean_rate"] for r in rows], float)
    print(f"\n{'event':>10s} {'prints':>9s} {'rate /s':>8s} {'envelope L (s)':>15s}  "
          + "  ".join(f"{'x@h=' + h:>9s}" for h in rows[0]["crossover_by_h"]))
    for r in rows:
        print(f"{r['event_id'].split('_')[0]:>10s} {r['prints_rth']:9,d} "
              f"{r['mean_rate']:8.2f} {r['envelope_curvature_scale_s']:15.1f}  "
              + "  ".join(f"{v:9.1f}" if np.isfinite(v) else f"{'inf':>9s}"
                          for v in r["crossover_by_h"].values()))

    print(f"\nlog crossover on log envelope curvature scale   (n = {len(rows)})")
    print(f"{'h':>8s} {'slope':>9s} {'se':>8s} {'t':>7s} {'r':>7s} {'r2':>6s} {'n':>4s}")
    for h in rows[0]["crossover_by_h"]:
        y = np.array([r["crossover_by_h"][h] for r in rows], float)
        ok = np.isfinite(y) & np.isfinite(L) & (y > 0) & (L > 0)
        st = ols(np.log(L[ok]), np.log(y[ok])) if ok.sum() >= 4 else {"n": int(ok.sum())}
        res["regressions"][f"h={h}"] = st
        if "slope" in st:
            print(f"{h:>8s} {st['slope']:9.3f} {st['se_slope']:8.3f} {st['t']:7.2f} "
                  f"{st['r']:7.3f} {st['r2']:6.3f} {st['n']:4d}")
        else:
            print(f"{h:>8s} {'--':>9s}  (n = {st['n']}, too few finite crossovers)")

    print("\ncontrol: log crossover on log MEAN RATE (a cohort-level confound check)")
    for h in rows[0]["crossover_by_h"]:
        y = np.array([r["crossover_by_h"][h] for r in rows], float)
        ok = np.isfinite(y) & (y > 0)
        if ok.sum() >= 4:
            st = ols(np.log(R[ok]), np.log(y[ok]))
            res["regressions"][f"rate|h={h}"] = st
            print(f"{h:>8s} slope {st['slope']:+.3f}  r {st['r']:+.3f}  r2 {st['r2']:.3f}")
    jdump(res, "crossover_vs_decay.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
