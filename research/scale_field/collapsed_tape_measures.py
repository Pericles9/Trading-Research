#!/usr/bin/env python
"""What survives when prints that were not separate events are collapsed.

Three measurements on one pass, because all three consume the same pair of tapes.

  A -- ALLAN FACTOR (review s2). The curve "5.99 at 15.6 ms rising to 1,245 at 4,096 s"
       is the standing justification for "Poisson nulls are too weak here" and is cited
       across the programme. At T = 15.6 ms, on a tape where ~60% of prints sit inside
       sub-millisecond runs, counting variance is dominated by whether a reporting burst
       lands inside the window. Recomputed on the collapsed tape, on v3's own dyadic
       ladder, same window origin, same min_windows -- so the raw column here IS the
       reconciled v3 quantity and the comparison is rung for rung.

  B -- THE FINE EXCESS, honestly. s10.3 collapsed on a TIME TOLERANCE, which the review
       correctly called tuning in the negative direction. This collapses on the identity
       signature measured in fragmentation_identity.py -- price-monotone AND
       (multi-venue OR sequence-contiguous) -- which is a measurement, not a chosen
       parameter, and is more conservative: it keeps 70% of prints where a 1 ms tolerance
       kept 54%.

  C -- THE INTERVAL CHANNEL AND THE DIVERGENCE (review s5). The rate channel provably
       cannot see clumping at constant mean rate. Two statistics can, and both are run:

         dm/dln s  the interval channel, m = kernel-weighted mean log10 inter-trade
                   interval. Takes x = log10(dt) directly, so on an uncollapsed tape a
                   100 us interval enters at -4 against -0.5 for a third of a second --
                   the sub-millisecond mode would dominate it far more than it dominated
                   the rate channel. THIS IS WHY IT MUST RUN COLLAPSED.

         D(t,s)    the cross-channel divergence, m + lograte/ln10 + gamma/ln10.
                   IDENTICALLY ZERO at every scale under a locally Poisson process AT
                   ANY RATE PATH, so its sign needs no null and no surrogate -- the
                   envelope cancels out of it by construction. Negative means more
                   clustered than Poisson. This is the statistic the whole arc should
                   arguably have used, and it is already in scale_field.py with an
                   acceptance test pinning the identity.

       A Poisson surrogate at the collapsed tape's own rate path is carried as the
       reference for both, so "zero" is checked rather than assumed.

Regular hours. The identity-collapsed tapes come from fragmentation_identity.py.
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
from instrument_gates import CACHE, cohort, jdump                   # noqa: E402
from scale_field import (allan_factor, collapse_same_timestamp,     # noqa: E402
                         divergence, field, intervals, seconds_since)
from surrogate_bandwidth_family import draw, field_sd, smooth_lambda  # noqa: E402

ALLAN_EXPONENTS = range(-6, 14)          # v3's dyadic ladder, 2^-6 .. 2^13 s
MIN_WINDOWS = 8
BANDWIDTHS = (1.0, 5.0, 30.0)
CH_SCALES = np.geomspace(0.25, 512.0, 4 * 11 + 1)


def allan_curve(ts_ns, lo, hi):
    ts_s = (ts_ns - lo).astype(np.float64) / 1e9
    span = (hi - lo) / 1e9
    out = {}
    for e in ALLAN_EXPONENTS:
        T = 2.0 ** e
        A, n = allan_factor(ts_s, T, t_start=0.0, t_end=span, min_windows=MIN_WINDOWS)
        out[f"{T:g}"] = {"T": float(T), "A": float(A), "n_pairs": int(n)}
    return out


def channels(arr, lo, hi, grid_ns, origin):
    """m, dm, lograte and the divergence on a fixed absolute scale grid."""
    a = collapse_same_timestamp(arr)
    if a.size < 2000:
        return None
    ts = seconds_since(a, origin)
    ev, x = intervals(a, origin=origin)
    tg = (grid_ns - origin).astype(np.float64) / 1e9
    f = field(ts, ev, x, tg, CH_SCALES, neff_min=8.0, edge_scales=4.0)
    D = divergence(f)
    out = []
    for j, s in enumerate(CH_SCALES):
        d, dm = D[:, j], f["dm"][:, j]
        okd, okm = np.isfinite(d), np.isfinite(dm)
        if okd.sum() < 400:
            continue
        out.append({"s": float(s), "n": int(okd.sum()),
                    "D_mean": float(d[okd].mean()), "D_median": float(np.median(d[okd])),
                    "D_sd": float(d[okd].std()),
                    "D_share_negative": float((d[okd] < 0).mean()),
                    "dm_mean": float(dm[okm].mean()) if okm.sum() > 400 else float("nan"),
                    "dm_sd": float(dm[okm].std()) if okm.sum() > 400 else float("nan")})
    return out


def main() -> int:
    cfg = ep.load_config()
    n_ev = int(sys.argv[1]) if len(sys.argv) > 1 else 5
    res = {"allan_ladder": [2.0 ** e for e in ALLAN_EXPONENTS],
           "min_windows": MIN_WINDOWS, "bandwidths": list(BANDWIDTHS),
           "scales": [float(v) for v in CH_SCALES], "note": __doc__, "events": {}}
    t0 = time.perf_counter()

    for eid in list(cohort()["event_id"])[:n_ev]:
        p = CACHE / f"identity_collapsed_{eid}.npy"
        if not p.exists():
            print("  skip (no identity-collapsed tape):", eid)
            continue
        ts_ns, meta = adapter.load_event_prints_meta(eid, None)
        raw_all = collapse_same_timestamp(ts_ns)
        lo, hi = adapter.segment_bounds_ns(eid.split("_")[1])["rth"]
        raw = raw_all[(raw_all >= lo) & (raw_all < hi)]
        col = collapse_same_timestamp(np.load(p))
        if raw.size < 5000 or col.size < 5000:
            continue
        origin = int(raw[0])
        _, grid_ns, _, _ = ep.column_grid(raw, lo, hi, 1.13, 40000)

        e = {"prints_raw": int(raw.size), "prints_collapsed": int(col.size),
             "retained_share": float(col.size / raw.size),
             "allan": {"raw": allan_curve(raw, lo, hi),
                       "collapsed": allan_curve(col, lo, hi)},
             "excess": {}, "channels": {}}

        # B -- the fine excess on the identity-collapsed tape
        for tag, tape in (("raw", raw), ("collapsed", col)):
            sd_base = field_sd(tape, lo, hi, grid_ns, origin)
            row = {}
            for h in BANDWIDTHS:
                lam, n, dt = smooth_lambda(tape, lo, hi, h)
                sur = collapse_same_timestamp(draw(lam, n, dt, lo, seed=int(h * 10) + 7))
                row[f"{h:g}"] = [float(v) for v in
                                 (sd_base / field_sd(sur, lo, hi, grid_ns, origin))]
            e["excess"][tag] = row

        # C -- interval channel and divergence, with a Poisson reference
        lam, n, dt = smooth_lambda(col, lo, hi, 30.0)
        surC = collapse_same_timestamp(draw(lam, n, dt, lo, seed=333))
        for tag, tape in (("raw", raw), ("collapsed", col),
                          ("collapsed_poisson_surrogate", surC)):
            c = channels(tape, lo, hi, grid_ns, origin)
            if c:
                e["channels"][tag] = c
        res["events"][eid] = e
        print(f"  {eid.split('_')[0]:6s} kept {e['retained_share']:.3f}  "
              f"A(15.6ms) {e['allan']['raw']['0.015625']['A']:6.2f} -> "
              f"{e['allan']['collapsed']['0.015625']['A']:6.2f}   "
              f"A(4096s) {e['allan']['raw']['4096']['A']:7.1f} -> "
              f"{e['allan']['collapsed']['4096']['A']:7.1f}   "
              f"[{round(time.perf_counter()-t0)}s]", flush=True)

    jdump(res, "collapsed_tape_measures.json")
    ev = list(res["events"])

    print("\n" + "=" * 84)
    print("A -- ALLAN FACTOR, RAW vs IDENTITY-COLLAPSED (median across events)")
    print("=" * 84)
    print(f"{'T (s)':>12s} {'raw A':>10s} {'collapsed A':>13s} {'ratio':>8s} {'n ev':>5s}")
    for T in res["allan_ladder"]:
        k = f"{T:g}"
        r = [res["events"][e]["allan"]["raw"][k]["A"] for e in ev]
        c = [res["events"][e]["allan"]["collapsed"][k]["A"] for e in ev]
        r = [v for v in r if np.isfinite(v)]
        c = [v for v in c if np.isfinite(v)]
        if not r or not c:
            continue
        mr, mc = np.median(r), np.median(c)
        print(f"{T:12g} {mr:10.2f} {mc:13.2f} {mc/mr if mr else float('nan'):8.3f} "
              f"{len(r):5d}")

    print("\n" + "=" * 84)
    print("B -- FINE EXCESS, RAW vs IDENTITY-COLLAPSED (sd ratio to own surrogate)")
    print("=" * 84)
    print(f"{'s':>9s}" + "".join(f"{tag[:4]+' h='+f'{h:g}':>14s}"
                                 for tag in ("raw", "collapsed") for h in BANDWIDTHS))
    for j, s in enumerate(CH_SCALES):
        if abs(np.log2(s) % 1) > 1e-6 and s != 0.25:
            continue
        row = []
        for tag in ("raw", "collapsed"):
            for h in BANDWIDTHS:
                v = [res["events"][e]["excess"][tag][f"{h:g}"][j] for e in ev]
                v = [q for q in v if np.isfinite(q)]
                row.append(np.median(v) if v else np.nan)
        print(f"{s:9.2f}" + "".join(f"{q:14.2f}" for q in row))

    print("\n" + "=" * 84)
    print("C -- DIVERGENCE D = m + lograte/ln10 + gamma/ln10")
    print("    IDENTICALLY ZERO under a locally Poisson process AT ANY RATE PATH.")
    print("    Negative = more clustered than Poisson. No null, no surrogate needed.")
    print("=" * 84)
    print(f"{'s':>9s} {'D raw':>10s} {'D collapsed':>12s} {'D surrogate':>12s} "
          f"{'share D<0 col':>14s} {'dm collapsed':>13s}")
    for j, s in enumerate(CH_SCALES):
        if abs(np.log2(s) % 1) > 1e-6 and s != 0.25:
            continue
        def g(tag, key):
            v = []
            for e in ev:
                rows = res["events"][e]["channels"].get(tag) or []
                m = [q for q in rows if abs(q["s"] - s) < 1e-9]
                if m and np.isfinite(m[0][key]):
                    v.append(m[0][key])
            return np.median(v) if v else np.nan
        print(f"{s:9.2f} {g('raw','D_median'):10.4f} "
              f"{g('collapsed','D_median'):12.4f} "
              f"{g('collapsed_poisson_surrogate','D_median'):12.4f} "
              f"{g('collapsed','D_share_negative'):14.3f} "
              f"{g('collapsed','dm_mean'):13.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
