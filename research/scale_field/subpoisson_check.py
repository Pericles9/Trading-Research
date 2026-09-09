#!/usr/bin/env python
"""Is the ~10% Allan deficit a finding, or surrogate-construction bias? (review s3)

THE NUMBER. On the 10 ms collapsed tape the real Allan factor sits BELOW its rate-matched
surrogate at every rung -- 0.91, 0.87, 0.88, 0.99 at 15.6 ms / 4 s / 64 s / 2048 s. A
deficit means MORE REGULAR THAN POISSON at the same rate path, which is the opposite of
clustering and would be the only positive characterisation the arc has produced.

THE PERCENTILE TEST THE REVIEW ASKS FOR IS NECESSARY AND NOT SUFFICIENT, and the reason
is specific to how the surrogate is built. lambda-hat_h is estimated from a FINITE
realisation and then simulated from. At h = 1 s and ~3 prints/s a bandwidth window holds
about three prints, so lambda-hat_1 is dominated by its own sampling noise -- and that
noise becomes GENUINE RATE VARIATION in the surrogate. The surrogate therefore carries
rate structure the truth does not have, which inflates its A(T) above the true value.
A deficit of the real tape against it is then expected with no clustering anywhere.

That is visible in the committed table already: at T = 4 s the h = 30 surrogate reads
1.00 and the h = 1 surrogate reads 2.28. Nothing about the tape changed between those
two numbers; only the estimator's own noise did.

SO THE TEST IS THE POSITIVE CONTROL, RUN ON THE ALLAN COMPARISON ITSELF. Take a tape
with KNOWN ground truth -- an inhomogeneous Poisson draw with no clustering at all -- and
push it through the identical procedure. If it shows the same deficit, the deficit is the
procedure. If only the real tape shows it, the real tape is sub-Poisson.

  real_collapsed   the question
  known_poisson    an h = 30 draw from the collapsed tape's own rate path. No
                   clustering, by construction. Its deficit IS the procedure's bias.

Replicates give the band; the control gives the meaning. Both are reported.
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
from instrument_gates import cohort, jdump                         # noqa: E402
from scale_field import allan_factor, collapse_same_timestamp      # noqa: E402
from subsecond_origin import collapse_tol                          # noqa: E402
from surrogate_bandwidth_family import draw, smooth_lambda         # noqa: E402

EXPS = range(-6, 12)
MINW = 8
N_REP = 60
HS = (1.0, 30.0)


def acurve(ts, lo, hi):
    t = (ts - lo).astype(np.float64) / 1e9
    span = (hi - lo) / 1e9
    return np.array([allan_factor(t, 2.0 ** e, t_start=0.0, t_end=span,
                                  min_windows=MINW)[0] for e in EXPS])


def replicate_band(base, lo, hi, h, n_rep, seed0):
    lam, n, dt = smooth_lambda(base, lo, hi, h)
    out = []
    for r in range(n_rep):
        s = collapse_same_timestamp(draw(lam, n, dt, lo, seed=seed0 + r))
        if s.size < 1000:
            continue
        out.append(acurve(s, lo, hi))
    return np.vstack(out) if out else None


def main() -> int:
    n_ev = int(sys.argv[1]) if len(sys.argv) > 1 else 5
    res = {"exponents": list(EXPS), "n_replicates": N_REP, "bandwidths": list(HS),
           "min_windows": MINW, "note": __doc__, "events": {}}
    t0 = time.perf_counter()

    for eid in list(cohort()["event_id"])[:n_ev]:
        ts_ns, meta = adapter.load_event_prints_meta(eid, None)
        lo, hi = adapter.segment_bounds_ns(eid.split("_")[1])["rth"]
        raw_all = collapse_same_timestamp(ts_ns)
        raw = raw_all[(raw_all >= lo) & (raw_all < hi)]
        if raw.size < 5000:
            continue
        col = collapse_tol(raw, 10.0)
        lam30, n30, dt30 = smooth_lambda(col, lo, hi, 30.0)
        known = collapse_same_timestamp(draw(lam30, n30, dt30, lo, seed=8801))

        e = {"prints_collapsed": int(col.size), "prints_known": int(known.size),
             "bases": {}}
        for bname, base in (("real_collapsed", col), ("known_poisson", known)):
            a = acurve(base, lo, hi)
            b = {"A": [float(v) for v in a], "by_h": {}}
            for h in HS:
                band = replicate_band(base, lo, hi, h, N_REP, seed0=int(h) * 1000 + 1)
                if band is None:
                    continue
                q = np.nanpercentile(band, [2.5, 50, 97.5], axis=0)
                below = a < q[0]
                b["by_h"][f"{h:g}"] = {
                    "p2_5": [float(v) for v in q[0]],
                    "median": [float(v) for v in q[1]],
                    "p97_5": [float(v) for v in q[2]],
                    "ratio_to_median": [float(v) for v in (a / q[1])],
                    "below_p2_5": [bool(v) for v in below],
                    "n_rungs_below": int(np.nansum(below & np.isfinite(a))),
                    "n_rungs_finite": int(np.nansum(np.isfinite(a)))}
            e["bases"][bname] = b
        res["events"][eid] = e
        r1 = e["bases"]["real_collapsed"]["by_h"]["1"]
        k1 = e["bases"]["known_poisson"]["by_h"]["1"]
        print(f"  {eid.split('_')[0]:6s} rungs below p2.5  real {r1['n_rungs_below']}"
              f"/{r1['n_rungs_finite']}   KNOWN-POISSON {k1['n_rungs_below']}"
              f"/{k1['n_rungs_finite']}   [{round(time.perf_counter()-t0)}s]", flush=True)

    jdump(res, "subpoisson_check.json")
    ev = list(res["events"])

    for h in HS:
        print("\n" + "=" * 100)
        print(f"ALLAN vs {N_REP} SURROGATE REPLICATES AT h = {h:g} s "
              f"(median across {len(ev)} events)")
        print("  a deficit on the KNOWN-POISSON row is procedure bias, not a property "
              "of the tape")
        print("=" * 100)
        print(f"{'T (s)':>10s} | {'real A':>9s} {'rep med':>9s} {'ratio':>7s} "
              f"{'<p2.5':>6s} | {'known A':>9s} {'rep med':>9s} {'ratio':>7s} {'<p2.5':>6s}")
        for i, ex in enumerate(EXPS):
            row = []
            for b in ("real_collapsed", "known_poisson"):
                A = np.nanmedian([res["events"][e]["bases"][b]["A"][i] for e in ev])
                M = np.nanmedian([res["events"][e]["bases"][b]["by_h"][f"{h:g}"]
                                  ["median"][i] for e in ev])
                nb = sum(res["events"][e]["bases"][b]["by_h"][f"{h:g}"]["below_p2_5"][i]
                         for e in ev)
                row.append((A, M, A / M if M else np.nan, nb))
            if not np.isfinite(row[0][0]):
                continue
            print(f"{2.0**ex:10g} | {row[0][0]:9.2f} {row[0][1]:9.2f} {row[0][2]:7.3f} "
                  f"{row[0][3]:3d}/{len(ev):<2d} | {row[1][0]:9.2f} {row[1][1]:9.2f} "
                  f"{row[1][2]:7.3f} {row[1][3]:3d}/{len(ev):<2d}")

    print("\nVERDICT INPUTS")
    for h in HS:
        for b, lab in (("real_collapsed", "real"), ("known_poisson", "KNOWN POISSON")):
            tot = sum(res["events"][e]["bases"][b]["by_h"][f"{h:g}"]["n_rungs_below"]
                      for e in ev)
            fin = sum(res["events"][e]["bases"][b]["by_h"][f"{h:g}"]["n_rungs_finite"]
                      for e in ev)
            print(f"  h={h:>4g}  {lab:14s} rungs below the 2.5th percentile: "
                  f"{tot}/{fin} = {100*tot/max(fin,1):.1f}%")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
