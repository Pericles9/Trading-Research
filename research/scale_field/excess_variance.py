#!/usr/bin/env python
"""Observed sd(F) against the sampling-noise sd at the same n_eff, per scale row.

THE ONE CURVE WITH NO THRESHOLD IN IT. Gate B asks what survives a cut; this asks how
much of the field's variance is not sampling error, at every scale, with no cut, no
burst definition and no null model beyond the estimator's own sampling law.

  observed sd(F(.,s))  /  sd_null(n_eff(t,s))

At 1.0 the field is pure estimator noise at that scale. Above 1.0 the tape is
contributing variance the estimator would not produce on its own. The ratio is what a
split-half correlation measures indirectly, and it needs no second computation of the
field to obtain.

The null sd is evaluated PER CELL at that cell's own n_eff and then combined as
sqrt(mean(sd^2)) -- the null sd varies by a factor of ten within a single scale row
because lambda does, and using the row's median n_eff instead would understate the
noise floor wherever the tape is thin.

Premarket and regular hours are reported separately and never pooled (v3 measured
0.903 decades of separation; failure row 5).
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

import adapter                                        # noqa: E402
from scale_field import _neff_coef                    # noqa: E402

CACHE = os.environ.get("GATE_CACHE",
                       os.path.join(os.environ.get("TEMP", "/tmp"), "gatecache"))
ART = os.path.join(REPO_ROOT, "results", "scale_field", "artifacts",
                   "instrument_gates")


def main() -> int:
    with open(os.path.join(ART, "gateC_null_rate.json"), encoding="utf-8") as f:
        rows = json.load(f)["rows"]
    out = {"definition": __doc__, "events": {}}
    for kern in ("centred", "onesided"):
        tab = {q["n_eff"]: q["sd"] for q in rows
               if q["kernel"] == kern and q["conditioning"] == "unconditional"}
        ks = np.array(sorted(tab))
        lsd = np.log([tab[k] for k in ks])

        def sd_at(ne):
            ne = np.asarray(ne, float)
            v = np.exp(np.interp(np.log(np.clip(ne, 1e-9, None)), np.log(ks), lsd))
            hi = ne > ks[-1]
            return np.where(hi, tab[ks[-1]] * np.sqrt(ks[-1] / np.maximum(ne, 1e-9)), v)

        for fn in sorted(os.listdir(CACHE)):
            eid = fn[:-4]
            d = np.load(os.path.join(CACHE, fn))
            Z = d["Z_" + kern].astype(np.float64)
            lam = d["lam_" + kern]
            dt = d["dt_eval"]
            sc = d["scales"]
            n = Z.shape[0]
            coef = _neff_coef(kern)
            b = adapter.segment_bounds_ns(eid.split("_")[1])
            e = out["events"].setdefault(eid, {}).setdefault(kern, {})
            for seg in ("premarket", "rth"):
                lo, hi = b[seg]
                m = ((d["grid_ns"] >= lo) & (d["grid_ns"] < hi))[:n]
                if m.sum() < 2000:
                    continue
                res = []
                for j, s in enumerate(sc):
                    F = Z[:n, j]
                    ok = m & np.isfinite(F) & np.isfinite(lam[:n])
                    if ok.sum() < 500:
                        continue
                    ne = coef * s * lam[:n][ok]
                    w = dt[:n][ok]
                    w = w / w.sum()
                    mu = float((w * F[ok]).sum())
                    obs = float(np.sqrt((w * (F[ok] - mu) ** 2).sum()))
                    nul = float(np.sqrt((w * sd_at(ne) ** 2).sum()))
                    res.append({"s": float(s), "n_cells": int(ok.sum()),
                                "n_eff_median": float(np.median(ne)),
                                "sd_observed": obs, "sd_null": nul,
                                "ratio": obs / nul if nul > 0 else float("nan"),
                                "excess_sd": float(np.sqrt(max(obs ** 2 - nul ** 2, 0.0))),
                                "mean_F": mu})
                e[seg] = res
            print(f"  {kern:9s} {eid:24s} done")

    with open(os.path.join(ART, "excess_variance.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, default=float)
    print("wrote", os.path.join(ART, "excess_variance.json"))

    for kern in ("centred", "onesided"):
        for seg in ("rth", "premarket"):
            pool = {}
            for eid, d in out["events"].items():
                for q in d.get(kern, {}).get(seg, []):
                    pool.setdefault(round(q["s"], 4), []).append(q)
            print(f"\n== {kern} / {seg} == observed sd(F) / sampling-noise sd, "
                  f"median across events")
            print(f"{'s':>9s} {'n ev':>5s} {'n_eff med':>10s} {'sd obs':>8s} "
                  f"{'sd null':>8s} {'ratio':>7s} {'excess sd':>10s}")
            for s in sorted(pool):
                if abs(np.log2(s) % 1) > 1e-6 and s != 0.25:
                    continue
                q = pool[s]
                print(f"{s:9.3f} {len(q):5d} "
                      f"{np.median([x['n_eff_median'] for x in q]):10.1f} "
                      f"{np.median([x['sd_observed'] for x in q]):8.3f} "
                      f"{np.median([x['sd_null'] for x in q]):8.3f} "
                      f"{np.median([x['ratio'] for x in q]):7.2f} "
                      f"{np.median([x['excess_sd'] for x in q]):10.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
