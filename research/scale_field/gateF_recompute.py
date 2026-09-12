#!/usr/bin/env python
"""Gate F's width statistic re-run on the cohort with the calibration applied.

gateF_calibration.py established that the estimator is unbiased: on pure Poisson its
MEAN width/s returns 1.98-2.10 against a derived target of 1.987, and on an injected
bump it returns 2.838 where theory says 2.828 (ratio 1.003). The masks and the
print-indexed grid contribute nothing at high lambda.

TWO THINGS THE FIRST GATE F RUN GOT WRONG, both biasing DOWN, both fixed here.

  (a) IT QUOTED THE MEDIAN. The 2.00 reference is a MEAN -- it comes from a
      zero-crossing rate, which is a reciprocal of a mean. Run lengths are
      right-skewed, so on pure noise the median returns 1.88-2.01 while the mean
      returns 1.99. Comparing a median against a mean reference understates by ~0.1.

  (b) IT COUNTED TRUNCATED RUNS. A run cut by a NaN cell (the n_eff mask, the edge
      mask) or by the segment boundary is not a measurement of a run length. On the
      real tape at fine scales the defined share is low, so this bites hardest exactly
      where the first run reported its lowest values.

Both references are for COMPLETE runs, so both are applied. The raw numbers are kept
beside the corrected ones rather than replaced.
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(REPO_ROOT, "research", "phase_10d_diag1"))

import event_panels as ep                                     # noqa: E402
from instrument_gates import (CACHE, cohort, event_field,      # noqa: E402
                              jdump, runs_from_bool, segment_masks)

NOISE_MEAN = 1.9869                    # derived, gateF_calibration.py
BUMP_SIGMA_EQ_S = 2 * np.sqrt(2)       # 2.8284


def main() -> int:
    cfg = ep.load_config()
    res = {"references": {"pure_noise_mean_width_over_s": NOISE_MEAN,
                          "sigma_eq_s_bump_width_over_s": BUMP_SIGMA_EQ_S,
                          "calibration": "gateF_calibration.json"},
           "note": __doc__, "events": {}}

    for eid in list(cohort()["event_id"]):
        d = event_field(eid, cfg)
        segs = segment_masks(d["grid_ns"], eid.split("_")[1])
        dt = d["dt_eval"]
        Z = d["Z_centred"].astype(np.float64)
        n = Z.shape[0]
        e = {}
        for sname in ("premarket", "rth"):
            m = segs[sname][:n]
            if m.sum() < 2000:
                continue
            rows = []
            for j, s in enumerate(d["scales"]):
                F = np.where(m, Z[:n, j], np.nan)
                fin = np.isfinite(F)
                if fin.sum() < 500:
                    continue
                neg = fin & (F < 0)
                raw, comp = [], []
                for a, b in runs_from_bool(neg):
                    w = float(np.nansum(dt[a:b]))
                    if w <= 0:
                        continue
                    raw.append(w)
                    # COMPLETE only: bounded by a real sign change on both sides,
                    # inside the segment, and away from the edge mask
                    if a == 0 or b >= n:
                        continue
                    if not (fin[a - 1] and fin[min(b, n - 1)]):
                        continue
                    if not (m[a - 1] and m[min(b, n - 1)]):
                        continue
                    comp.append(w)
                if len(comp) < 20:
                    continue
                raw = np.array(raw); comp = np.array(comp)
                rows.append({
                    "s": float(s), "n_runs_raw": int(raw.size),
                    "n_runs_complete": int(comp.size),
                    "complete_share": float(comp.size / raw.size),
                    "defined_share": float(fin.mean()),
                    "MEAN_complete_over_s": float(comp.mean() / s),
                    "median_complete_over_s": float(np.median(comp) / s),
                    "mean_raw_over_s": float(raw.mean() / s),
                    "median_raw_over_s": float(np.median(raw) / s),
                    "p90_complete_over_s": float(np.quantile(comp, 0.90) / s),
                    "max_complete_over_s": float(comp.max() / s),
                })
            e[sname] = rows
        res["events"][eid] = e
        print("  F", eid, "done", flush=True)

    jdump(res, "gateF_recompute.json")

    for seg in ("rth", "premarket"):
        pool = {}
        for eid, d_ in res["events"].items():
            for q in d_.get(seg, []):
                pool.setdefault(round(q["s"], 4), []).append(q)
        print(f"\n=== {seg} === CALIBRATED width/s. noise reference {NOISE_MEAN:.3f}; "
              f"a resolved sigma = s feature would give {BUMP_SIGMA_EQ_S:.3f}")
        print(f"{'s':>9s} {'MEAN cmpl/s':>12s} {'vs noise':>9s} {'p90 cmpl/s':>11s} "
              f"{'mean raw/s':>11s} {'cmpl share':>11s} {'defined':>8s} {'n runs':>8s}")
        for s in sorted(pool):
            if abs(np.log2(s) % 1) > 1e-6 and s != 0.25:
                continue
            q = pool[s]
            mc = np.median([x["MEAN_complete_over_s"] for x in q])
            print(f"{s:9.3f} {mc:12.3f} {mc/NOISE_MEAN:9.3f} "
                  f"{np.median([x['p90_complete_over_s'] for x in q]):11.3f} "
                  f"{np.median([x['mean_raw_over_s'] for x in q]):11.3f} "
                  f"{np.median([x['complete_share'] for x in q]):11.3f} "
                  f"{np.median([x['defined_share'] for x in q]):8.3f} "
                  f"{int(np.median([x['n_runs_complete'] for x in q])):8d}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
