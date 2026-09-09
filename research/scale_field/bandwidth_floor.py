#!/usr/bin/env python
"""How tight can the surrogate be before the test goes blind? (review s1, second pass)

WHAT THE FIRST SWEEP FOUND, and it is a retraction. The crossover TRACKS the surrogate
bandwidth: 14 s at h = 5, 45 s at h = 15, 89 s at h = 30, 305 s at h = 100 -- roughly
3h throughout. And the positive control settles it: S30, a tape built to have envelope
structure above 30 s and NOTHING below it and no clustering anywhere, returns a
crossover of 88.8 s at h = 30 against the real tape's 89.3 s. Indistinguishable. So the
"30-64 s crossover" was the surrogate's bandwidth, exactly as the review predicted, and
it is withdrawn.

WHY THE ARTIFACT EXISTS, since it is not obvious: re-estimating lambda-hat at bandwidth
h from a tape whose intensity was ALREADY smooth at h gives an effective bandwidth of
h*sqrt(2), so the surrogate is systematically smoother than its own base. Any tape with
envelope structure shows a spurious excess below ~3h. The homogeneous-Poisson control
does not, because it has no envelope to double-smooth -- which is why one control was
not enough.

WHAT SURVIVES, and it is the reason this second pass exists. In the ratio curves the
excess below ~1 s is INVARIANT to h across a 60x sweep: 3.70/3.62/3.68/3.43/3.57 at
s = 0.25 s for h = 5/15/30/100/300. At h = 5 the surrogate already contains every
intensity variation down to 5 s, and the real tape still exceeds it 3.3-3.7x at
0.25-1 s. That excess cannot be intensity structure the surrogate is missing.

BUT A SWEEP DOWNWARD HAS ITS OWN FAILURE and neither existing control can see it. As h
falls, lambda-hat_h begins to fit the realisation rather than an intensity; in the limit
the surrogate reproduces the tape and the excess vanishes. That is a FALSE NEGATIVE, and
S30 and Poisson both return "no crossover" under it -- which is also what they return
when the procedure is working. They cannot distinguish blindness from correctness.

THE MISSING CONTROL is a tape with KNOWN FINE STRUCTURE. NS05 is a Neyman-Scott cluster
process: parents thinned from the real tape's own 30 s envelope, each spawning
Poisson(mu) offspring with Gaussian sigma = 0.5 s offsets. Same mean intensity as the
real tape, envelope identical, and clustering at a known 0.5 s that the procedure MUST
detect. Where the sweep loses NS05 is the overfitting floor, measured rather than
assumed -- and only bandwidths above that floor can be trusted to have found anything.
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
from surrogate_bandwidth_family import (SCALES, crossover,          # noqa: E402
                                        draw, field_sd, smooth_lambda)
from scale_field import collapse_same_timestamp                     # noqa: E402

BANDWIDTHS = (1.0, 2.0, 5.0, 15.0, 30.0)
NS_SIGMA = 0.5
NS_MU = 3.0


def neyman_scott(lam, n, dt, lo, sigma=NS_SIGMA, mu=NS_MU, seed=0):
    """Same mean intensity as `lam`, same envelope, clustering at a KNOWN sigma.

    Parents are drawn from lam/mu so the expected total is unchanged; each parent
    spawns Poisson(mu) offspring at Gaussian sigma offsets. The envelope is therefore
    identical to the base tape's and only the fine structure differs, which is exactly
    what the procedure is being asked to detect.
    """
    rng = np.random.default_rng(seed)
    T, lmax = n * dt, float(lam.max())
    if lmax <= 0:
        return np.array([], dtype=np.int64)
    m = rng.poisson(lmax * T / mu)
    u = np.sort(rng.uniform(0, T, m))
    keep = rng.random(m) < np.interp(u, (np.arange(n) + 0.5) * dt, lam) / lmax
    parents = u[keep]
    k = rng.poisson(mu, parents.size)
    off = np.repeat(parents, k) + rng.normal(0.0, sigma, int(k.sum()))
    off = np.sort(off[(off >= 0) & (off < T)])
    return (lo + off * 1e9).astype(np.int64)


def main() -> int:
    cfg = ep.load_config()
    n_ev = int(sys.argv[1]) if len(sys.argv) > 1 else 5
    events = list(cohort()["event_id"])[:n_ev]
    res = {"bandwidths": list(BANDWIDTHS), "scales": [float(v) for v in SCALES],
           "ns_sigma_s": NS_SIGMA, "ns_mu": NS_MU, "note": __doc__, "events": {}}
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
            "NS05_known_fine_structure": collapse_same_timestamp(
                neyman_scott(lam30, n30, dt30, lo, seed=451)),
            "S30_envelope_only": collapse_same_timestamp(
                draw(lam30, n30, dt30, lo, seed=911)),
            "poisson_nothing": np.sort(np.random.default_rng(912)
                                       .uniform(lo, hi, real.size).astype(np.int64)),
        }
        e = {}
        for bname, btape in bases.items():
            sd_base = field_sd(btape, lo, hi, grid_ns, origin)
            rows = {}
            for h in BANDWIDTHS:
                lam, n, dt = smooth_lambda(btape, lo, hi, h)
                sur = collapse_same_timestamp(draw(lam, n, dt, lo, seed=int(h * 10) + 7))
                ratio = sd_base / field_sd(sur, lo, hi, grid_ns, origin)
                rows[f"{h:g}"] = {"ratio": [float(v) for v in ratio],
                                  "crossover_s": crossover(ratio),
                                  "ratio_at_0p25": float(ratio[0]),
                                  "surrogate_prints": int(sur.size)}
            e[bname] = {"prints": int(btape.size), "by_bandwidth": rows}
        res["events"][eid] = e
        print(f"  {eid.split('_')[0]:6s} ratio at s=0.25 by h "
              + " ".join(f"{h:g}:{e['real']['by_bandwidth'][f'{h:g}']['ratio_at_0p25']:.2f}"
                         for h in BANDWIDTHS)
              + f"   NS05 "
              + " ".join(f"{h:g}:{e['NS05_known_fine_structure']['by_bandwidth'][f'{h:g}']['ratio_at_0p25']:.2f}"
                         for h in BANDWIDTHS)
              + f"  [{round(time.perf_counter()-t0)}s]", flush=True)

    jdump(res, "bandwidth_floor.json")

    names = ["real", "NS05_known_fine_structure", "S30_envelope_only", "poisson_nothing"]
    print("\n" + "=" * 100)
    print("RATIO AT s = 0.25 s AGAINST SURROGATE BANDWIDTH -- median across events")
    print("  NS05 has clustering at 0.5 s and MUST be detected; where it is lost is the "
          "overfitting floor")
    print("  S30 and poisson have NO fine structure and must read 1.00")
    print("=" * 100)
    print(f"{'base tape':30s}" + "".join(f"{'h=' + f'{h:g}':>11s}" for h in BANDWIDTHS))
    for b in names:
        v = [np.median([res["events"][e][b]["by_bandwidth"][f"{h:g}"]["ratio_at_0p25"]
                        for e in res["events"]]) for h in BANDWIDTHS]
        print(f"{b:30s}" + "".join(f"{q:11.2f}" for q in v))

    print("\nCROSSOVER (s)")
    print(f"{'base tape':30s}" + "".join(f"{'h=' + f'{h:g}':>11s}" for h in BANDWIDTHS))
    for b in names:
        v = []
        for h in BANDWIDTHS:
            x = [res["events"][e][b]["by_bandwidth"][f"{h:g}"]["crossover_s"]
                 for e in res["events"]]
            x = [q for q in x if np.isfinite(q)]
            v.append(np.median(x) if x else float("nan"))
        print(f"{b:30s}" + "".join(f"{q:11.2f}" if np.isfinite(q) else f"{'none':>11s}"
                                   for q in v))

    print("\nFULL RATIO CURVE, real base, by bandwidth (median across events)")
    print(f"{'s':>9s}" + "".join(f"{'h=' + f'{h:g}':>10s}" for h in BANDWIDTHS))
    for j, s in enumerate(SCALES):
        if abs(np.log2(s) % 1) > 1e-6 and s != 0.25:
            continue
        print(f"{s:9.2f}" + "".join(
            f"{np.median([res['events'][e]['real']['by_bandwidth'][f'{h:g}']['ratio'][j] for e in res['events']]):10.2f}"
            for h in BANDWIDTHS))

    print("\nFULL RATIO CURVE, NS05 base (the positive control for FINE structure)")
    print(f"{'s':>9s}" + "".join(f"{'h=' + f'{h:g}':>10s}" for h in BANDWIDTHS))
    for j, s in enumerate(SCALES):
        if abs(np.log2(s) % 1) > 1e-6 and s != 0.25:
            continue
        print(f"{s:9.2f}" + "".join(
            f"{np.median([res['events'][e]['NS05_known_fine_structure']['by_bandwidth'][f'{h:g}']['ratio'][j] for e in res['events']]):10.2f}"
            for h in BANDWIDTHS))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
