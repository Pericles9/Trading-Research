#!/usr/bin/env python
"""What is the sub-second excess made of? (not on the review's list -- see below)

WHY THIS RUNS. The review's s1 came back the wrong way: the 30-64 s crossover was the
surrogate's bandwidth. What survives is a different and finer claim -- a 3.5-4.0x excess
in field sd at 0.25-0.5 s that is invariant to the surrogate bandwidth from h = 1 to
h = 30, with both structureless controls reading 1.00 at every h. That claim is now the
headline, it was not the headline anyone reviewed, and it needs one sanity check before
it is handed over.

THE LEADING ALTERNATIVE, and nothing measured so far excludes it. A single order filling
against multiple resting quotes prints as several trades within microseconds to
milliseconds. That is order fragmentation, not market structure, and it would produce
exactly what is observed: a large excess in field variance that grows as the kernel
narrows, invariant to any surrogate bandwidth coarser than it, and absent from a
surrogate drawn as a Poisson process at the same intensity.

THE TEST. Rebuild the tape collapsing prints within a tolerance rather than only exact
timestamp ties, and recompute the excess. The committed tie variant is
collapse_same_timestamp (exact ties only, config/phase_10_v4.json). Sweeping the
tolerance over 0, 1, 10, 100 ms separates the two readings:

  excess SURVIVES a 100 ms collapse -> there is structure at 0.25-1 s that is not
                                       fragmentation, and the finding stands
  excess COLLAPSES with tolerance    -> it is sub-tolerance print clustering, the
                                       finding is about the print process rather than
                                       the arrival process, and it should be renamed

THE COLLAPSE IS DIAGNOSTIC ONLY. It is not proposed as a change to the tie variant --
that is committed and is not this read's to move.
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
from instrument_gates import cohort, jdump                         # noqa: E402
from scale_field import collapse_same_timestamp                    # noqa: E402
from surrogate_bandwidth_family import (SCALES, draw, field_sd,    # noqa: E402
                                        smooth_lambda)

TOL_MS = (0.0, 1.0, 10.0, 100.0)
H = 1.0            # the tightest bandwidth both null controls pass at


def collapse_tol(ts_ns, tol_ms):
    """Keep the first print of each run separated by less than `tol_ms` from the last
    kept one. tol = 0 reduces exactly to collapse_same_timestamp."""
    a = collapse_same_timestamp(ts_ns)
    if tol_ms <= 0 or a.size == 0:
        return a
    tol = np.int64(tol_ms * 1e6)
    keep = [a[0]]
    last = a[0]
    for v in a[1:]:
        if v - last >= tol:
            keep.append(v)
            last = v
    return np.array(keep, dtype=np.int64)


def main() -> int:
    cfg = ep.load_config()
    n_ev = int(sys.argv[1]) if len(sys.argv) > 1 else 5
    res = {"tolerances_ms": list(TOL_MS), "bandwidth_s": H,
           "scales": [float(v) for v in SCALES], "note": __doc__, "events": {}}
    t0 = time.perf_counter()

    for eid in list(cohort()["event_id"])[:n_ev]:
        ts_ns, meta = adapter.load_event_prints_meta(eid, None)
        arr = collapse_same_timestamp(ts_ns)
        lo, hi = adapter.segment_bounds_ns(eid.split("_")[1])["rth"]
        real = arr[(arr >= lo) & (arr < hi)]
        if real.size < 5000:
            continue
        d = np.diff(real).astype(np.float64) / 1e6          # ms
        e = {"prints": int(real.size),
             "itt_share_below_1ms": float((d < 1.0).mean()),
             "itt_share_below_10ms": float((d < 10.0).mean()),
             "itt_share_below_100ms": float((d < 100.0).mean()),
             "itt_median_ms": float(np.median(d)), "by_tolerance": {}}
        for tol in TOL_MS:
            tape = collapse_tol(real, tol)
            if tape.size < 5000:
                e["by_tolerance"][f"{tol:g}"] = {"prints": int(tape.size),
                                                 "ratio": None}
                continue
            origin = int(tape[0])
            _, grid_ns, _, _ = ep.column_grid(tape, lo, hi, 1.13, 40000)
            lam, n, dt = smooth_lambda(tape, lo, hi, H)
            sur = collapse_same_timestamp(draw(lam, n, dt, lo, seed=77))
            ratio = (field_sd(tape, lo, hi, grid_ns, origin)
                     / field_sd(sur, lo, hi, grid_ns, origin))
            e["by_tolerance"][f"{tol:g}"] = {
                "prints": int(tape.size),
                "retained_share": float(tape.size / real.size),
                "ratio": [float(v) for v in ratio]}
        res["events"][eid] = e
        print(f"  {eid.split('_')[0]:6s} itt<1ms {e['itt_share_below_1ms']:.3f} "
              f"<10ms {e['itt_share_below_10ms']:.3f}  "
              + " ".join(f"tol{t:g}:{e['by_tolerance'][f'{t:g}']['retained_share']:.2f}"
                         for t in TOL_MS if e["by_tolerance"][f"{t:g}"]["ratio"])
              + f"  [{round(time.perf_counter()-t0)}s]", flush=True)

    jdump(res, "subsecond_origin.json")

    print("\n" + "=" * 92)
    print(f"FIELD sd RATIO (tape / its own h = {H:g} s surrogate) BY COLLAPSE TOLERANCE"
          f" -- median across events")
    print("  if the excess is order fragmentation it falls away as the tolerance rises")
    print("=" * 92)
    print(f"{'s':>9s}" + "".join(f"{'tol=' + f'{t:g}ms':>12s}" for t in TOL_MS))
    for j, s in enumerate(SCALES):
        if abs(np.log2(s) % 1) > 1e-6 and s != 0.25:
            continue
        row = []
        for t in TOL_MS:
            v = [res["events"][e]["by_tolerance"][f"{t:g}"]["ratio"][j]
                 for e in res["events"]
                 if res["events"][e]["by_tolerance"][f"{t:g}"]["ratio"]]
            v = [q for q in v if np.isfinite(q)]
            row.append(np.median(v) if v else float("nan"))
        print(f"{s:9.2f}" + "".join(f"{q:12.2f}" for q in row))

    print(f"\n{'event':>10s} {'prints':>9s} {'itt<1ms':>9s} {'itt<10ms':>9s} "
          f"{'itt<100ms':>10s} {'median itt ms':>14s}")
    for eid, e in res["events"].items():
        print(f"{eid.split('_')[0]:>10s} {e['prints']:9,d} "
              f"{e['itt_share_below_1ms']:9.3f} {e['itt_share_below_10ms']:9.3f} "
              f"{e['itt_share_below_100ms']:10.3f} {e['itt_median_ms']:14.1f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
