#!/usr/bin/env python
"""The Allan validity ceiling, measured rather than estimated from a rule of thumb.

THE CLAIM BEING SCOPED. `prompts/phase_10_v3.md` L73: the Allan factor "tolerates a
slowly-varying underlying rate". True -- and true only for T well below the envelope's own
variation scale. A(T) differences successive counts, which cancels a trend that is
approximately linear across 2T; once T approaches the scale on which the rate actually
curves, successive windows straddle genuinely different rates and the cancellation stops.
v3 stated the property and not the regime, and downstream that read as "Allan is
drift-immune, full stop", after which the whole ladder was quotable.

THE CEILING IS DIRECTLY OBSERVABLE AND NEEDS NO RULE OF THUMB. On an ENVELOPE-ONLY tape
with no clustering anywhere, A(T) = 1 at every rung where the statistic is valid. **The T
at which it departs from 1 is the ceiling, by definition.**

THE SURROGATE MUST BE h = 30, NOT h = 1. subpoisson_check.py established that lambda-hat
estimated at h = 1 s from ~3 prints/s turns its own sampling noise into real rate variation
in the surrogate -- A(4 s) reads 2.28 at h = 1 against 1.00 at h = 30 with nothing about
the tape changing. For measuring a ceiling that noise is the thing being measured, so the
surrogate has to be smooth enough not to carry it.

PER SEGMENT, because the knees this scopes are per segment -- v3 reports 128 s regular
hours and 16 s premarket -- and the envelope curvature that sets the ceiling differs
between them. Pooling would produce one number that is wrong for both.

REPLICATES, so "departs from 1" is a band and not a point. The ceiling is reported at
several departure levels rather than one, so the number is not an arbitrary choice
dressed as a measurement.
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

EXPS = range(-6, 13)
MINW = 8
N_REP = 40
H = 30.0
LEVELS = (1.05, 1.10, 1.25, 2.00)
KNEE = {"rth": 128.0, "premarket": 16.0}       # v3's committed knees, per segment


def acurve(ts, lo, hi):
    t = (ts - lo).astype(np.float64) / 1e9
    span = (hi - lo) / 1e9
    return np.array([allan_factor(t, 2.0 ** e, t_start=0.0, t_end=span,
                                  min_windows=MINW)[0] for e in EXPS])


def ceiling_from(med, Ts, level):
    """Smallest T at which the envelope-only median A first reaches `level` and stays
    at or above it. Interpolated in log T. NaN if it never does."""
    ok = np.isfinite(med)
    if ok.sum() < 3:
        return float("nan")
    T, m = np.asarray(Ts)[ok], med[ok]
    above = m >= level
    if not above.any():
        return float("nan")
    i = int(np.flatnonzero(above)[0])
    if i == 0:
        return float(T[0])
    a, b = m[i - 1], m[i]
    if b == a:
        return float(T[i])
    f = (level - a) / (b - a)
    return float(np.exp(np.log(T[i - 1]) + f * (np.log(T[i]) - np.log(T[i - 1]))))


def main() -> int:
    n_ev = int(sys.argv[1]) if len(sys.argv) > 1 else 5
    Ts = [2.0 ** e for e in EXPS]
    res = {"ladder_seconds": Ts, "n_replicates": N_REP, "bandwidth_s": H,
           "min_windows": MINW, "levels": list(LEVELS), "v3_knees": KNEE,
           "note": __doc__, "segments": {}}
    t0 = time.perf_counter()

    for seg in ("rth", "premarket"):
        per_event = {}
        for eid in list(cohort()["event_id"])[:n_ev]:
            ts_ns, meta = adapter.load_event_prints_meta(eid, None)
            lo, hi = adapter.segment_bounds_ns(eid.split("_")[1])[seg]
            a_all = collapse_same_timestamp(ts_ns)
            raw = a_all[(a_all >= lo) & (a_all < hi)]
            if raw.size < 3000:
                continue
            col = collapse_tol(raw, 10.0)
            lam, n, dt = smooth_lambda(col, lo, hi, H)
            band = []
            for r in range(N_REP):
                s = collapse_same_timestamp(draw(lam, n, dt, lo, seed=4400 + r))
                if s.size > 500:
                    band.append(acurve(s, lo, hi))
            if len(band) < 10:
                continue
            B = np.vstack(band)
            med = np.nanmedian(B, axis=0)
            per_event[eid] = {
                "median": [float(v) for v in med],
                "p2_5": [float(v) for v in np.nanpercentile(B, 2.5, axis=0)],
                "p97_5": [float(v) for v in np.nanpercentile(B, 97.5, axis=0)],
                "ceiling": {f"{L:g}": ceiling_from(med, Ts, L) for L in LEVELS},
                "prints_collapsed": int(col.size),
                "span_s": float((hi - lo) / 1e9)}
            print(f"  {seg:10s} {eid.split('_')[0]:6s} ceiling@1.10 = "
                  f"{per_event[eid]['ceiling']['1.1']:8.2f} s   "
                  f"[{round(time.perf_counter()-t0)}s]", flush=True)
        res["segments"][seg] = per_event

    # pooled ceilings
    for seg, per in res["segments"].items():
        if not per:
            continue
        res.setdefault("ceiling_median", {})[seg] = {
            f"{L:g}": float(np.nanmedian([per[e]["ceiling"][f"{L:g}"] for e in per]))
            for L in LEVELS}
    jdump(res, "allan_validity_ceiling.json")

    print("\n" + "=" * 92)
    print(f"ENVELOPE-ONLY TAPE (h = {H:g} s surrogate, NO clustering): A(T) must be 1 "
          f"where the statistic is valid")
    print("=" * 92)
    for seg, per in res["segments"].items():
        if not per:
            continue
        print(f"\n--- {seg}  (n = {len(per)} events, {N_REP} replicates each) ---")
        print(f"{'T (s)':>10s} {'median A':>10s} {'p2.5':>8s} {'p97.5':>8s}")
        for i, T in enumerate(Ts):
            m = np.nanmedian([per[e]["median"][i] for e in per])
            if not np.isfinite(m):
                continue
            lo_ = np.nanmedian([per[e]["p2_5"][i] for e in per])
            hi_ = np.nanmedian([per[e]["p97_5"][i] for e in per])
            print(f"{T:10g} {m:10.3f} {lo_:8.3f} {hi_:8.3f}")

    print("\n" + "=" * 92)
    print("THE CEILING -- smallest T at which an envelope-only tape's A(T) reaches each level")
    print("=" * 92)
    print(f"{'segment':>12s}" + "".join(f"{'A>=' + f'{L:g}':>12s}" for L in LEVELS)
          + f"{'v3 knee':>10s} {'knee vs ceiling':>18s}")
    for seg in res.get("ceiling_median", {}):
        c = res["ceiling_median"][seg]
        k = KNEE[seg]
        c110 = c.get("1.1", float("nan"))
        verdict = ("INSIDE  (valid)" if np.isfinite(c110) and k < c110
                   else "OUTSIDE (scope violation)" if np.isfinite(c110)
                   else "undetermined")
        print(f"{seg:>12s}" + "".join(f"{c[f'{L:g}']:12.2f}" for L in LEVELS)
              + f"{k:10g} {verdict:>18s}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
