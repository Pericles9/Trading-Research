#!/usr/bin/env python
"""Gate E needs a reference, not a null (review s3). This builds the ceiling.

WHY THE BARE NUMBER IS NOT INTERPRETABLE. Reliability near 1 at EVERY scale, including
fine scales where n_eff is small and noise should dominate, is the signature of a
shared low-frequency component inflating the correlation. Both halves are thinned
copies of one realisation, so both carry the same diurnal envelope; if that envelope
holds most of the variance at a given scale, r goes to 1 whether or not the fine
structure replicates. "No null model needed" was the wrong claim -- a null is not
needed, but a CEILING is, and Gate E as first run had none.

TWO REFERENCES, both from the surrogate that already exists.

  1. THE CEILING. Run the identical split-half on the smooth-rate surrogate: same
     lambda-hat path, same envelope, NO clustering at any scale. Whatever r it returns
     is what the envelope alone buys. If the surrogate returns 0.95 at some scale, then
     0.97 on the real tape means nothing there.

  2. THE RESIDUAL. Subtract each half's smooth-rate expectation and correlate what is
     left. The envelope expectation is DETERMINISTIC and identical for both halves --
     F_env(t,s) = s^2 * (G_s * lam_bw)'' / (G_s * lam_bw) -- computed from the 30 s
     intensity directly, with no sampling in it. Note that F_env does not depend on the
     thinning fraction at all: F is invariant to lam -> c*lam, which is the same
     property the split-half test rests on, so one envelope serves both halves and the
     full tape. corr(F_A - F_env, F_B - F_env) is the reliability of the part that is
     not the envelope, which is the part in question.

Both halves are evaluated on a FIXED ABSOLUTE scale grid, as in Gate E.
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

import adapter                                                     # noqa: E402
import event_panels as ep                                          # noqa: E402
from instrument_gates import cohort, jdump                         # noqa: E402
from scale_field import (collapse_same_timestamp, field, intervals,  # noqa: E402
                         seconds_since)

BW_S = 30.0
SCALES = np.geomspace(0.25, 512.0, 4 * 11 + 1)      # 4/octave, fixed and absolute
DT_ENV = 0.5


def smooth_intensity(ts_ns, lo_ns, hi_ns, bw_s=BW_S, dt=DT_ENV):
    T = (hi_ns - lo_ns) / 1e9
    n = int(T / dt) + 1
    c = np.bincount(np.clip(((ts_ns - lo_ns) / 1e9 / dt).astype(np.int64), 0, n - 1),
                    minlength=n).astype(float)
    return gaussian_filter1d(c, bw_s / dt, mode="nearest") / dt, n, dt


def surrogate_from(lam, n, dt, lo_ns, seed):
    rng = np.random.default_rng(seed)
    T = n * dt
    lmax = float(lam.max())
    if lmax <= 0:
        return np.array([], dtype=np.int64)
    m = rng.poisson(lmax * T)
    u = np.sort(rng.uniform(0, T, m))
    keep = rng.random(m) < np.interp(u, (np.arange(n) + 0.5) * dt, lam) / lmax
    return (lo_ns + u[keep] * 1e9).astype(np.int64)


def envelope_field(lam, n, dt, t_grid, origin_offset_s):
    """F_env(t,s) from the DETERMINISTIC 30 s intensity. No sampling anywhere in it."""
    gt = (np.arange(n) + 0.5) * dt - origin_offset_s
    out = np.full((t_grid.size, SCALES.size), np.nan)
    for j, s in enumerate(SCALES):
        sg = s / dt
        a0 = gaussian_filter1d(lam, sg, order=0, mode="nearest")
        a2 = gaussian_filter1d(lam, sg, order=2, mode="nearest")
        v = np.divide(sg * sg * a2, a0, out=np.full_like(a0, np.nan), where=a0 > 0)
        out[:, j] = np.interp(t_grid, gt, v, left=np.nan, right=np.nan)
    return out


def half_fields(arr, origin, t_grid, rng):
    half = rng.random(arr.size) < 0.5
    fs = []
    for sel in (half, ~half):
        a = arr[sel]
        if a.size < 500:
            return None
        ev, x = intervals(a, origin=origin)
        fs.append(field(seconds_since(a, origin), ev, x, t_grid, SCALES)["dlograte"])
    return fs


def corr_by_scale(A, B, sub=None):
    out = []
    for j in range(SCALES.size):
        a, b = A[:, j], B[:, j]
        ok = np.isfinite(a) & np.isfinite(b)
        if sub is not None:
            ok &= np.isfinite(sub[:, j])
            a = a - sub[:, j]
            b = b - sub[:, j]
        if ok.sum() < 200:
            out.append((np.nan, 0))
            continue
        aa, bb = a[ok], b[ok]
        if aa.std() < 1e-12 or bb.std() < 1e-12:
            out.append((np.nan, int(ok.sum())))
            continue
        out.append((float(np.corrcoef(aa, bb)[0, 1]), int(ok.sum())))
    return out


def main() -> int:
    cfg = ep.load_config()
    n_draws = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    events = list(cohort()["event_id"])[:8]
    res = {"bandwidth_s": BW_S, "scale_grid": [float(v) for v in SCALES],
           "n_draws": n_draws, "note": __doc__, "events": {}}
    t0 = time.perf_counter()

    for eid in events:
        ts_ns, meta = adapter.load_event_prints_meta(eid, None)
        arr = collapse_same_timestamp(ts_ns)
        origin = int(arr[0])
        lo, hi = int(meta["window_start_ns"]), int(meta["window_end_ns"])
        cg = cfg["amendment_1"]["column_grid"]
        _, grid_ns, _, _ = ep.column_grid(arr, lo, hi, 4.52, 12000)
        tg = (grid_ns - origin).astype(np.float64) / 1e9

        lam, n, dt = smooth_intensity(arr, lo, hi)
        env = envelope_field(lam, n, dt, tg, (origin - lo) / 1e9)
        sur = collapse_same_timestamp(surrogate_from(lam, n, dt, lo, seed=17))

        acc = {k: [[] for _ in range(SCALES.size)]
               for k in ("real", "real_residual", "surrogate")}
        nn = [[] for _ in range(SCALES.size)]
        for dr in range(n_draws):
            rng = np.random.default_rng(101 + dr * 7 + abs(hash(eid)) % 1000)
            fr = half_fields(arr, origin, tg, rng)
            if fr:
                for j, (r, c) in enumerate(corr_by_scale(fr[0], fr[1])):
                    if np.isfinite(r):
                        acc["real"][j].append(r); nn[j].append(c)
                for j, (r, c) in enumerate(corr_by_scale(fr[0], fr[1], sub=env)):
                    if np.isfinite(r):
                        acc["real_residual"][j].append(r)
            rng2 = np.random.default_rng(202 + dr * 7 + abs(hash(eid)) % 1000)
            fs = half_fields(sur, int(sur[0]), tg - (int(sur[0]) - origin) / 1e9, rng2)
            if fs:
                for j, (r, c) in enumerate(corr_by_scale(fs[0], fs[1])):
                    if np.isfinite(r):
                        acc["surrogate"][j].append(r)

        rows = []
        for j, s in enumerate(SCALES):
            if not acc["real"][j]:
                continue
            rows.append({
                "s": float(s),
                "r_real": float(np.mean(acc["real"][j])),
                "r_surrogate_CEILING": float(np.mean(acc["surrogate"][j]))
                if acc["surrogate"][j] else float("nan"),
                "r_real_residual": float(np.mean(acc["real_residual"][j]))
                if acc["real_residual"][j] else float("nan"),
                "n_cells_median": float(np.median(nn[j])) if nn[j] else float("nan")})
        res["events"][eid] = rows
        print(f"  E-ceiling {eid.split('_')[0]:6s} "
              f"[{round(time.perf_counter()-t0)}s]", flush=True)

    jdump(res, "gateE_ceiling.json")

    pool = {}
    for eid, rows in res["events"].items():
        for q in rows:
            pool.setdefault(round(q["s"], 4), []).append(q)
    print("\n" + "=" * 88)
    print("GATE E WITH A CEILING -- median across events")
    print("=" * 88)
    print(f"{'s':>9s} {'r real':>8s} {'r SURROGATE':>12s} {'excess':>8s} "
          f"{'r residual':>11s} {'cells':>9s}")
    for s in sorted(pool):
        if abs(np.log2(s) % 1) > 1e-6 and s != 0.25:
            continue
        q = pool[s]
        rr = np.nanmedian([x["r_real"] for x in q])
        rc = np.nanmedian([x["r_surrogate_CEILING"] for x in q])
        print(f"{s:9.3f} {rr:8.3f} {rc:12.3f} {rr-rc:8.3f} "
              f"{np.nanmedian([x['r_real_residual'] for x in q]):11.3f} "
              f"{np.nanmedian([x['n_cells_median'] for x in q]):9.0f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
