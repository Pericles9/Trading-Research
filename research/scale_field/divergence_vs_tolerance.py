#!/usr/bin/env python
"""Is the surviving divergence real clustering, or residual fragmentation?

THE REMAINING DOUBT, and it is the sharpest one left. D uses m = E_w[log10 dt], and the
log makes it violently sensitive to short intervals: a 100 us interval enters at -4
against -0.5 for a third of a second. The identity collapse removes only ~30% of prints
-- the runs carrying the price-monotone-plus-contiguous signature -- so runs that fail
that signature (non-monotone same-order fills, for instance) are still present, and each
one contributes several very short intervals. Raw D at s = 1 s is -1.85 and collapsed is
-0.76, so the collapse already removed more than half of it. The rest could be the same
thing, incompletely removed.

THE TEST IS A SENSITIVITY CURVE, NOT A CHOICE OF TOLERANCE. D is reported as a function
of collapse tolerance, with the surrogate rebuilt from each collapsed tape so the
comparison stays like-for-like at every point:

  D keeps falling toward the surrogate  -> it is residual fragmentation all the way down
                                           and the interval channel has nothing either
  D plateaus at a negative value        -> there is clustering that is not the print
                                           process, and it is the first controlled
                                           positive result in this arc

Reporting the curve is what the review asked for in the bandwidth case -- report the
family, do not pick the member -- applied to the axis that remains open.
"""
from __future__ import annotations

import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(REPO_ROOT, "research", "phase_10d_diag1"))

import adapter                                                     # noqa: E402
import event_panels as ep                                          # noqa: E402
from divergence_controlled import D_curve, SCALES                  # noqa: E402
from instrument_gates import CACHE, cohort, jdump                  # noqa: E402
from scale_field import collapse_same_timestamp                    # noqa: E402
from subsecond_origin import collapse_tol                          # noqa: E402
from surrogate_bandwidth_family import draw, smooth_lambda         # noqa: E402

TOL_MS = (0.0, 1.0, 10.0, 100.0)
H = 1.0
REPORT_S = (1.0, 8.0, 64.0)


def main() -> int:
    cfg = ep.load_config()
    n_ev = int(sys.argv[1]) if len(sys.argv) > 1 else 5
    res = {"tolerances_ms": list(TOL_MS), "bandwidth_s": H,
           "scales": [float(v) for v in SCALES], "note": __doc__, "events": {}}
    t0 = time.perf_counter()

    for eid in list(cohort()["event_id"])[:n_ev]:
        ts_ns, meta = adapter.load_event_prints_meta(eid, None)
        lo, hi = adapter.segment_bounds_ns(eid.split("_")[1])["rth"]
        raw_all = collapse_same_timestamp(ts_ns)
        raw = raw_all[(raw_all >= lo) & (raw_all < hi)]
        if raw.size < 5000:
            continue
        e = {"prints_raw": int(raw.size), "by_tolerance": {}}
        for tol in TOL_MS:
            tape = collapse_tol(raw, tol)
            if tape.size < 3000:
                continue
            origin = int(tape[0])
            _, grid_ns, _, _ = ep.column_grid(tape, lo, hi, 1.13, 40000)
            lam, n, dt = smooth_lambda(tape, lo, hi, H)
            sur = collapse_same_timestamp(draw(lam, n, dt, lo, seed=77))
            e["by_tolerance"][f"{tol:g}"] = {
                "prints": int(tape.size),
                "retained_share": float(tape.size / raw.size),
                "D_real": D_curve(tape, grid_ns, origin),
                "D_surrogate": D_curve(sur, grid_ns, origin)}
        # the identity collapse, on the same axes, as the measured (non-tuned) point
        p = CACHE / f"identity_collapsed_{eid}.npy"
        if p.exists():
            tape = collapse_same_timestamp(np.load(p))
            origin = int(tape[0])
            _, grid_ns, _, _ = ep.column_grid(tape, lo, hi, 1.13, 40000)
            lam, n, dt = smooth_lambda(tape, lo, hi, H)
            sur = collapse_same_timestamp(draw(lam, n, dt, lo, seed=77))
            e["identity"] = {"prints": int(tape.size),
                             "retained_share": float(tape.size / raw.size),
                             "D_real": D_curve(tape, grid_ns, origin),
                             "D_surrogate": D_curve(sur, grid_ns, origin)}
        res["events"][eid] = e
        j = int(np.argmin(np.abs(SCALES - 1.0)))
        print(f"  {eid.split('_')[0]:6s} D(s=1) by tol "
              + " ".join(f"{t:g}ms:{e['by_tolerance'][f'{t:g}']['D_real'][j]:+.3f}"
                         for t in TOL_MS if f"{t:g}" in e["by_tolerance"])
              + (f"  identity:{e['identity']['D_real'][j]:+.3f}" if "identity" in e else "")
              + f"  [{round(time.perf_counter()-t0)}s]", flush=True)

    jdump(res, "divergence_vs_tolerance.json")
    ev = list(res["events"])

    print("\n" + "=" * 100)
    print("DIVERGENCE D AGAINST COLLAPSE TOLERANCE -- gap = real minus its own surrogate")
    print("  falls toward 0 = residual fragmentation;  plateaus = clustering that is not "
          "the print process")
    print("=" * 100)
    for s_t in REPORT_S:
        j = int(np.argmin(np.abs(SCALES - s_t)))
        print(f"\n  s = {SCALES[j]:g} s")
        print(f"    {'tolerance':>12s} {'kept':>7s} {'D real':>9s} {'D surr':>9s} "
              f"{'GAP':>9s}")
        for t in TOL_MS:
            k = f"{t:g}"
            g = [res["events"][e]["by_tolerance"][k] for e in ev
                 if k in res["events"][e]["by_tolerance"]]
            if not g:
                continue
            dr = np.nanmedian([x["D_real"][j] for x in g])
            ds = np.nanmedian([x["D_surrogate"][j] for x in g])
            print(f"    {t:10g}ms {np.median([x['retained_share'] for x in g]):7.3f} "
                  f"{dr:9.3f} {ds:9.3f} {dr - ds:9.3f}")
        gi = [res["events"][e]["identity"] for e in ev if "identity" in res["events"][e]]
        if gi:
            dr = np.nanmedian([x["D_real"][j] for x in gi])
            ds = np.nanmedian([x["D_surrogate"][j] for x in gi])
            print(f"    {'identity':>10s}   {np.median([x['retained_share'] for x in gi]):7.3f} "
                  f"{dr:9.3f} {ds:9.3f} {dr - ds:9.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
