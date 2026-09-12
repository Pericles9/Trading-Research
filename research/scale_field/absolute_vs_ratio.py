#!/usr/bin/env python
"""Is 40.9x at rf 1 a strong read, or a vanishing denominator? (review 2026-09-09 s3)

THE CLAIM UNDER TEST, and it was mine to write into the decision tension: "rf = 1 in
RTH has the highest envelope contrast of any read -- 40.9x against 9.9x at rf = 4."

THE REVIEW'S OBJECTION, which is a statement about the denominator. A smooth envelope of
curvature scale L contributes F ~ (s/L)^2 to the field, so as the read scale goes fine
the SURROGATE's field collapses toward zero quadratically. A ratio against a vanishing
null inflates without limit and says nothing about the numerator. 40.9x at rf 1 would
then be division by nearly nothing and 9.9x at rf 4 division by something real -- not
comparable, and the larger number the weaker evidence.

THE COMPARABLE QUANTITIES ARE ABSOLUTE, and both hold n_eff fixed at 8.01*rf along the
read path, so nothing about the noise level moves between read factors:

  survivors per unit admissible time        real - surrogate, not real / surrogate
  excess in sd units   (mean F_real - mean F_surrogate) / sd(n_eff at the read)

Both are computed on the SAME tapes, the SAME grid and the SAME read as
gateD_vs_surrogate.py, so the ratio and the absolute statistics are two views of one
run rather than two runs.

If rf = 1 does not lead on the absolute statistics, the decision tension dissolves: rf 1
is retired for measurability AND it was never the purest detection, it merely had the
smallest denominator. If it still leads, the tension is real and belongs in the decision
text as written.
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
from instrument_gates import (OUT, READ_FACTORS, NoiseRuler,        # noqa: E402
                              cohort, jdump, read_at)
from scale_field import (collapse_same_timestamp, field, intervals,  # noqa: E402
                         s_min_for_rate, seconds_since)
from t1_lead_time import knn_rate                                   # noqa: E402

BW_S = 30.0


def surrogate(ts_ns, lo, hi, seed, h=BW_S, dt=0.25):
    rng = np.random.default_rng(seed)
    T = (hi - lo) / 1e9
    n = int(T / dt) + 1
    c = np.bincount(np.clip(((ts_ns - lo) / 1e9 / dt).astype(np.int64), 0, n - 1),
                    minlength=n).astype(float)
    lam = gaussian_filter1d(c, h / dt, mode="nearest") / dt
    lmax = float(lam.max())
    if lmax <= 0:
        return np.array([], dtype=np.int64)
    m = rng.poisson(lmax * T)
    u = np.sort(rng.uniform(0, T, m))
    keep = rng.random(m) < np.interp(u, (np.arange(n) + 0.5) * dt, lam) / lmax
    return (lo + u[keep] * 1e9).astype(np.int64)


def build(arr, lo, hi, grid_ns, origin, scales, cfg):
    ts = seconds_since(arr, origin)
    ev, x = intervals(arr, origin=origin)
    tg = (grid_ns - origin).astype(np.float64) / 1e9
    Z = np.full((tg.size, scales.size), np.nan)
    for g in cfg["scale_ladder"]["groups"]:
        sc = scales[(scales >= g["min_seconds"] - 1e-12)
                    & (scales <= g["max_seconds"] + 1e-12)]
        if not sc.size:
            continue
        f = field(ts, ev, x, tg, sc, neff_min=8.0, sigma_lo=8.0, edge_scales=4.0,
                  reduce="interp")
        for c_, jj in enumerate(np.searchsorted(scales, sc)):
            Z[:, jj] = np.where(np.isnan(Z[:, jj]), f["dlograte"][:, c_], Z[:, jj])
    lam = knn_rate(arr, grid_ns, k=20, causal=False)
    return {"t_grid": tg, "grid_ns": grid_ns, "scales": scales,
            "Z_centred": Z, "lam_centred": lam,
            "smin_centred": s_min_for_rate(lam, neff_min=8.0, kernel="centred")}


def main() -> int:
    cfg = ep.load_config()
    scales = ep.ladder(cfg)
    with open(os.path.join(OUT, "gateC_null_rate.json"), encoding="utf-8") as f:
        rows = json.load(f)["rows"]
    ruler = NoiseRuler(rows, "centred", "unconditional")
    res = {"bandwidth_s": BW_S, "note": __doc__, "events": {}}
    t0 = time.perf_counter()

    for eid in list(cohort()["event_id"]):
        ts_ns, meta = adapter.load_event_prints_meta(eid, None)
        arr = collapse_same_timestamp(ts_ns)
        lo, hi = adapter.segment_bounds_ns(eid.split("_")[1])["rth"]
        real = arr[(arr >= lo) & (arr < hi)]
        if real.size < 5000:
            continue
        origin = int(real[0])
        _, grid_ns, dt_e, _ = ep.column_grid(real, lo, hi, 1.13, 40000)
        sur = collapse_same_timestamp(surrogate(real, lo, hi, seed=17))
        d_r = build(real, lo, hi, grid_ns, origin, scales, cfg)
        d_s = build(sur, lo, hi, grid_ns, origin, scales, cfg)
        e = {}
        for f_ in READ_FACTORS:
            out = {}
            for tag, d in (("real", d_r), ("surrogate", d_s)):
                n = d["Z_centred"].shape[0]
                r = read_at(d, "centred", f_, debounce=True, cfg=cfg)
                F = r["F"][:n]
                ok = np.isfinite(F)
                sd2 = 2 * ruler.sd_at(r["n_eff"][:n])
                surv = r["on"][:n] & ok & (F < -sd2)
                w = dt_e[:n]
                tot = float(w[ok].sum())
                out[tag] = {
                    "survivor_fraction": float(w[surv].sum() / tot),
                    "shaded_fraction": float(w[r["on"][:n] & ok].sum() / tot),
                    "mean_F": float(np.average(F[ok], weights=w[ok])),
                    "sd_at_read": float(ruler.sd_at(8.01 * f_)),
                    "n_eff_at_read_median": float(np.nanmedian(r["n_eff"][:n])),
                    "defined_seconds": tot}
            sd = out["real"]["sd_at_read"]
            e[f"{f_:g}"] = {
                **{f"{k}_{t}": out[t][k] for t in ("real", "surrogate")
                   for k in ("survivor_fraction", "mean_F")},
                "ABS_excess_survivor_fraction":
                    out["real"]["survivor_fraction"] - out["surrogate"]["survivor_fraction"],
                "RATIO_survivor_fraction":
                    out["real"]["survivor_fraction"]
                    / max(out["surrogate"]["survivor_fraction"], 1e-12),
                "EXCESS_meanF_in_sd_units":
                    (out["real"]["mean_F"] - out["surrogate"]["mean_F"]) / sd,
                "sd_at_read": sd,
                "defined_seconds": out["real"]["defined_seconds"]}
        res["events"][eid] = e
        print(f"  {eid.split('_')[0]:6s} "
              + " ".join(f"rf{f:g} abs {e[f'{f:g}']['ABS_excess_survivor_fraction']:.4f}"
                         f"/sd {e[f'{f:g}']['EXCESS_meanF_in_sd_units']:+.3f}"
                         for f in READ_FACTORS)
              + f"  [{round(time.perf_counter()-t0)}s]", flush=True)

    jdump(res, "absolute_vs_ratio.json")

    print("\n" + "=" * 100)
    print("RATIO vs ABSOLUTE, regular hours, median across events")
    print("  the ratio is not comparable across read factors; the absolute statistics are")
    print("=" * 100)
    print(f"{'rf':>3s} {'sd at read':>11s} {'surv real':>10s} {'surv surr':>10s} "
          f"{'RATIO':>8s} {'ABS excess':>11s} {'excess meanF in sd':>19s}")
    for f_ in READ_FACTORS:
        g = [res["events"][e][f"{f_:g}"] for e in res["events"]]
        print(f"{f_:3.0f} {np.median([x['sd_at_read'] for x in g]):11.4f} "
              f"{np.median([x['survivor_fraction_real'] for x in g]):10.4f} "
              f"{np.median([x['survivor_fraction_surrogate'] for x in g]):10.4f} "
              f"{np.median([x['RATIO_survivor_fraction'] for x in g]):8.1f} "
              f"{np.median([x['ABS_excess_survivor_fraction'] for x in g]):11.4f} "
              f"{np.median([x['EXCESS_meanF_in_sd_units'] for x in g]):19.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
