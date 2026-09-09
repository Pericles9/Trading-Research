#!/usr/bin/env python
"""The divergence, put through the control that killed the other three claims.

WHY THIS EXISTS. collapsed_tape_measures.py section C found the cross-channel divergence
D = m + lograte/ln10 + gamma/ln10 sitting at -0.76 to -1.31 decades on the
identity-collapsed tape, with 98.5-100% of cells negative, against a Poisson surrogate
at -0.02 to -0.07. D is IDENTICALLY ZERO under a locally Poisson process at any rate
path, so unlike the rate channel it does not need a surrogate to be read at all.

BUT "LOCALLY POISSON" IS THE LOAD-BEARING WORD and it is exactly where the previous
three claims died. D is zero when lambda is constant ACROSS THE KERNEL. If lambda varies
WITHIN the kernel, m (event-weighted) and lograte (time-weighted) respond differently by
Jensen and D goes negative with no clustering present at all. A surrogate smoothed at
h = 30 s is constant across a 1 s kernel by construction, so its D ~ 0 proves only that
the identity holds -- not that a real tape's D is clustering.

THE CONTROL IS THE SAME ONE: sweep the surrogate bandwidth. A surrogate at h carries the
real rate path down to h, so if the real tape's D is within-kernel rate variation, the
surrogate's D approaches it as h falls. If the gap holds at h = 1 s while the two null
controls stay at zero, then within-kernel rate variation above 1 s is excluded.

THE SAME FOUR CONTROLS AS THE RATE CHANNEL, because that is what the standing rule now
requires and because three retractions came from not having them:

  negative      homogeneous Poisson              D must be 0
  positive      S30, envelope only, no clumping  D must be 0 (it is Poisson given lambda)
  sweep         h over 1 - 30 s                  is the gap the tape's or the null's?
  blindness     NS05, clusters at a known 0.5 s  D must be clearly negative, or the
                                                 statistic cannot see clumping here at all

NS05 is the one that matters most for a POSITIVE result: it proves the statistic
responds to clumping on this cohort's own tapes at a known scale, so a negative D on the
real tape is a detection rather than an artefact of something unexamined.

Runs on the IDENTITY-COLLAPSED tape (fragmentation_identity.py), because m takes
x = log10(dt) directly and the sub-millisecond mode would otherwise dominate it.
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

import adapter                                                      # noqa: E402
import event_panels as ep                                           # noqa: E402
from bandwidth_floor import neyman_scott                            # noqa: E402
from instrument_gates import CACHE, cohort, jdump                   # noqa: E402
from scale_field import (collapse_same_timestamp, divergence,       # noqa: E402
                         field, intervals, seconds_since)
from surrogate_bandwidth_family import draw, smooth_lambda          # noqa: E402

BANDWIDTHS = (1.0, 5.0, 30.0)
SCALES = np.geomspace(0.25, 512.0, 4 * 11 + 1)


def D_curve(arr, grid_ns, origin):
    a = collapse_same_timestamp(arr)
    if a.size < 2000:
        return None
    ts = seconds_since(a, origin)
    ev, x = intervals(a, origin=origin)
    tg = (grid_ns - origin).astype(np.float64) / 1e9
    f = field(ts, ev, x, tg, SCALES, neff_min=8.0, edge_scales=4.0)
    D = divergence(f)
    out = []
    for j in range(SCALES.size):
        d = D[:, j][np.isfinite(D[:, j])]
        out.append(float(np.median(d)) if d.size >= 400 else float("nan"))
    return out


def main() -> int:
    cfg = ep.load_config()
    n_ev = int(sys.argv[1]) if len(sys.argv) > 1 else 5
    res = {"bandwidths": list(BANDWIDTHS), "scales": [float(v) for v in SCALES],
           "note": __doc__, "events": {}}
    t0 = time.perf_counter()

    for eid in list(cohort()["event_id"])[:n_ev]:
        p = CACHE / f"identity_collapsed_{eid}.npy"
        if not p.exists():
            continue
        ts_ns, meta = adapter.load_event_prints_meta(eid, None)
        lo, hi = adapter.segment_bounds_ns(eid.split("_")[1])["rth"]
        col = collapse_same_timestamp(np.load(p))
        if col.size < 5000:
            continue
        origin = int(col[0])
        _, grid_ns, _, _ = ep.column_grid(col, lo, hi, 1.13, 40000)
        lam30, n30, dt30 = smooth_lambda(col, lo, hi, 30.0)

        e = {"prints": int(col.size), "curves": {}}
        e["curves"]["real_collapsed"] = D_curve(col, grid_ns, origin)
        e["curves"]["NS05_blindness_control"] = D_curve(
            collapse_same_timestamp(neyman_scott(lam30, n30, dt30, lo, seed=451)),
            grid_ns, origin)
        e["curves"]["poisson_negative_control"] = D_curve(
            np.sort(np.random.default_rng(912).uniform(lo, hi, col.size).astype(np.int64)),
            grid_ns, origin)
        for h in BANDWIDTHS:
            lam, n, dt = smooth_lambda(col, lo, hi, h)
            e["curves"][f"surrogate_h{h:g}"] = D_curve(
                collapse_same_timestamp(draw(lam, n, dt, lo, seed=int(h * 10) + 7)),
                grid_ns, origin)
        res["events"][eid] = e
        j1 = int(np.argmin(np.abs(SCALES - 1.0)))
        print(f"  {eid.split('_')[0]:6s} D at s=1s  real {e['curves']['real_collapsed'][j1]:+.3f}  "
              + "  ".join(f"h{h:g} {e['curves'][f'surrogate_h{h:g}'][j1]:+.3f}"
                          for h in BANDWIDTHS)
              + f"  NS05 {e['curves']['NS05_blindness_control'][j1]:+.3f}"
              + f"  pois {e['curves']['poisson_negative_control'][j1]:+.3f}"
              + f"  [{round(time.perf_counter()-t0)}s]", flush=True)

    jdump(res, "divergence_controlled.json")
    ev = list(res["events"])
    keys = (["real_collapsed"] + [f"surrogate_h{h:g}" for h in BANDWIDTHS]
            + ["NS05_blindness_control", "poisson_negative_control"])
    labs = ["real", "surr h=1", "surr h=5", "surr h=30", "NS05", "Poisson"]

    print("\n" + "=" * 96)
    print("MEDIAN DIVERGENCE D (decades). Zero = indistinguishable from Poisson at that")
    print("scale. Negative = intervals shorter than Poisson at the same rate = clustered.")
    print("=" * 96)
    print(f"{'s':>9s}" + "".join(f"{l:>13s}" for l in labs))
    for j, s in enumerate(SCALES):
        if abs(np.log2(s) % 1) > 1e-6 and s != 0.25:
            continue
        row = []
        for k in keys:
            v = [res["events"][e]["curves"][k][j] for e in ev
                 if res["events"][e]["curves"].get(k)]
            v = [q for q in v if np.isfinite(q)]
            row.append(np.median(v) if v else np.nan)
        print(f"{s:9.2f}" + "".join(f"{q:13.3f}" for q in row))

    print("\nGAP: real minus the surrogate at each bandwidth (the part the rate path "
          "does NOT explain)")
    print(f"{'s':>9s}" + "".join(f"{'h=' + f'{h:g}':>13s}" for h in BANDWIDTHS))
    for j, s in enumerate(SCALES):
        if abs(np.log2(s) % 1) > 1e-6 and s != 0.25:
            continue
        row = []
        for h in BANDWIDTHS:
            v = [res["events"][e]["curves"]["real_collapsed"][j]
                 - res["events"][e]["curves"][f"surrogate_h{h:g}"][j] for e in ev]
            v = [q for q in v if np.isfinite(q)]
            row.append(np.median(v) if v else np.nan)
        print(f"{s:9.2f}" + "".join(f"{q:13.3f}" for q in row))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
