#!/usr/bin/env python
"""Gate D against the surrogate rather than against print count (review s2).

WHY GATE D'S PASS IS NOT ENOUGH, and it is a hole in the gate rather than in the run.
Gate D was built to catch the Arm A failure -- marks proportional to activity -- and it
catches it. It cannot catch the failure the surrogate control raised. A diurnal
envelope produces a roughly constant shaded fraction across events REGARDLESS of print
count, because every session has broadly the same shape. That looks exactly like a
pass. r = -0.016 at rf 4 is consistent with both "detecting real structure" and
"detecting the session envelope", and no regression on print count can separate them.

THE SEPARATING TEST. Run the identical marking on a smooth-rate surrogate -- same
lambda-hat path, same s_min, same read scale, same debounce, same threshold, NO
clustering at any scale -- and compare shaded and survivor fractions directly. The
surrogate IS the envelope hypothesis, made concrete and measurable. If the real tape's
survivor fraction does not exceed the surrogate's, the marks are the clock.

Reported per segment (never pooled) and split at the absolute read scale, because
read_scale_distribution.py showed the two segments read at scales two decades apart:
regular hours lands at a survivor-weighted median of 4.4 s at rf 4, premarket at 153 s.
A pooled number would average a real-band result with a clock-band one.

The surrogate is built ONCE per event over the full D3 window at 30 s bandwidth, so it
carries the diurnal shape, the open and the anchor, and is thinned from the running
maximum so the realisation is exact rather than binned.
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
from instrument_gates import (KERNELS, OUT, READ_FACTORS, NoiseRuler,  # noqa: E402
                              cohort, jdump, read_at, runs_from_bool,
                              segment_masks)
from scale_field import (_neff_coef, collapse_same_timestamp, field,  # noqa: E402
                         field_onesided, intervals, s_min_for_rate,
                         seconds_since)
from t1_lead_time import knn_rate                                  # noqa: E402

BW_S = 30.0
BAND_S = 30.0            # below: excess is not a rate path. above 64: it is.


def surrogate(ts_ns, lo_ns, hi_ns, seed, bw_s=BW_S, dt=0.5):
    rng = np.random.default_rng(seed)
    T = (hi_ns - lo_ns) / 1e9
    n = int(T / dt) + 1
    c = np.bincount(np.clip(((ts_ns - lo_ns) / 1e9 / dt).astype(np.int64), 0, n - 1),
                    minlength=n).astype(float)
    lam = gaussian_filter1d(c, bw_s / dt, mode="nearest") / dt
    lmax = float(lam.max())
    if lmax <= 0:
        return np.array([], dtype=np.int64)
    m = rng.poisson(lmax * T)
    u = np.sort(rng.uniform(0, T, m))
    keep = rng.random(m) < np.interp(u, (np.arange(n) + 0.5) * dt, lam) / lmax
    return (lo_ns + u[keep] * 1e9).astype(np.int64)


def build(arr, lo, hi, cfg, scales):
    """The committed pipeline, applied to whatever tape it is handed."""
    origin = int(arr[0])
    ts_s = seconds_since(arr, origin)
    ev_s, x = intervals(arr, origin=origin)
    cg = cfg["amendment_1"]["column_grid"]
    edges, grid_ns, dt_e, _ = ep.column_grid(arr, lo, hi, cg["prints_per_column_eval"],
                                             cg["eval_max_points"])
    tg = (grid_ns - origin).astype(np.float64) / 1e9
    out = {"t_grid": tg, "grid_ns": grid_ns, "scales": scales, "dt_eval": dt_e}
    for kern in KERNELS:
        Z = np.full((tg.size, scales.size), np.nan)
        for g in cfg["scale_ladder"]["groups"]:
            sc = scales[(scales >= g["min_seconds"] - 1e-12)
                        & (scales <= g["max_seconds"] + 1e-12)]
            if not sc.size:
                continue
            fn = field_onesided if kern == "onesided" else field
            kw = dict(neff_min=8.0, sigma_lo=8.0, edge_scales=4.0)
            if kern == "centred":
                kw["reduce"] = "interp"
            f = fn(ts_s, ev_s, x, tg, sc, **kw)
            for c_, jj in enumerate(np.searchsorted(scales, sc)):
                Z[:, jj] = np.where(np.isnan(Z[:, jj]), f["dlograte"][:, c_], Z[:, jj])
        lam = knn_rate(arr, grid_ns, k=20, causal=(kern == "onesided"))
        out["Z_" + kern] = Z
        out["lam_" + kern] = lam
        out["smin_" + kern] = s_min_for_rate(lam, neff_min=8.0, kernel=kern)
    return out


def main() -> int:
    cfg = ep.load_config()
    scales = ep.ladder(cfg)
    with open(os.path.join(OUT, "gateC_null_rate.json"), encoding="utf-8") as f:
        rows = json.load(f)["rows"]
    ruler = {k: NoiseRuler(rows, k, "unconditional") for k in KERNELS}
    res = {"bandwidth_s": BW_S, "band_split_s": BAND_S, "note": __doc__, "events": {}}
    t0 = time.perf_counter()

    for eid in list(cohort()["event_id"]):
        ts_ns, meta = adapter.load_event_prints_meta(eid, None)
        arr = collapse_same_timestamp(ts_ns)
        lo, hi = int(meta["window_start_ns"]), int(meta["window_end_ns"])
        sur = collapse_same_timestamp(surrogate(arr, lo, hi, seed=17))
        e = {"real_prints": int(arr.size), "surrogate_prints": int(sur.size),
             "tapes": {}}
        for tag, tape in (("real", arr), ("surrogate", sur)):
            d = build(tape, lo, hi, cfg, scales)
            segs = segment_masks(d["grid_ns"], eid.split("_")[1])
            dt = d["dt_eval"]
            tk = {}
            for kern in KERNELS:
                n = d["Z_" + kern].shape[0]
                kk = {}
                for f_ in READ_FACTORS:
                    r = read_at(d, kern, f_, debounce=True, cfg=cfg)
                    sd2 = 2 * ruler[kern].sd_at(r["n_eff"][:n])
                    surv = (r["on"][:n] & np.isfinite(r["F"][:n])
                            & (r["F"][:n] < -sd2))
                    ss = r["s_star"][:n]
                    row = {}
                    for sname, sm in list(segs.items()) + [("all", np.ones(n, bool))]:
                        m = sm[:n]
                        for bname, bm in (("all", np.ones(n, bool)),
                                          ("s_below_30", ss < BAND_S),
                                          ("s_above_64", ss > 64.0)):
                            sel = m & bm
                            dfn = sel & np.isfinite(r["F"][:n])
                            tot = float(np.nansum(dt[:n][dfn]))
                            row[f"{sname}|{bname}"] = {
                                "defined_seconds": tot,
                                "shaded_fraction": float(
                                    np.nansum(dt[:n][sel & r["on"][:n]]) / tot)
                                if tot > 0 else float("nan"),
                                "survivor_fraction": float(
                                    np.nansum(dt[:n][sel & surv]) / tot)
                                if tot > 0 else float("nan"),
                                "n_runs": len(runs_from_bool(sel & surv)),
                            }
                    kk[f"{f_:g}"] = row
                tk[kern] = kk
            e["tapes"][tag] = tk
        res["events"][eid] = e
        g = lambda t, k: e["tapes"][t]["centred"]["4"][k]["survivor_fraction"]
        print(f"  {eid.split('_')[0]:6s} rf4 survivor fraction  "
              f"RTH real {g('real','rth|all'):.4f} vs surr {g('surrogate','rth|all'):.4f}"
              f"  ({g('real','rth|all')/max(g('surrogate','rth|all'),1e-9):5.2f}x) | "
              f"PRE real {g('real','premarket|all'):.4f} vs surr "
              f"{g('surrogate','premarket|all'):.4f}"
              f"  ({g('real','premarket|all')/max(g('surrogate','premarket|all'),1e-9):5.2f}x)"
              f"   [{round(time.perf_counter()-t0)}s]", flush=True)

    jdump(res, "gateD_vs_surrogate.json")

    print("\n" + "=" * 96)
    print("SURVIVOR FRACTION, REAL vs SMOOTH-RATE SURROGATE (centred), median of ten events")
    print("=" * 96)
    for seg in ("rth", "premarket", "post"):
        print(f"\n--- {seg} ---")
        print(f"{'rf':>3s} {'band':>12s} {'real':>9s} {'surrogate':>10s} {'ratio':>7s} "
              f"{'real shaded':>12s} {'surr shaded':>12s}")
        for f_ in READ_FACTORS:
            for band in ("all", "s_below_30", "s_above_64"):
                k = f"{seg}|{band}"
                rr = np.nanmedian([res["events"][e]["tapes"]["real"]["centred"]
                                   [f"{f_:g}"][k]["survivor_fraction"]
                                   for e in res["events"]])
                sr = np.nanmedian([res["events"][e]["tapes"]["surrogate"]["centred"]
                                   [f"{f_:g}"][k]["survivor_fraction"]
                                   for e in res["events"]])
                rs = np.nanmedian([res["events"][e]["tapes"]["real"]["centred"]
                                   [f"{f_:g}"][k]["shaded_fraction"]
                                   for e in res["events"]])
                ss_ = np.nanmedian([res["events"][e]["tapes"]["surrogate"]["centred"]
                                    [f"{f_:g}"][k]["shaded_fraction"]
                                    for e in res["events"]])
                print(f"{f_:3.0f} {band:>12s} {rr:9.4f} {sr:10.4f} "
                      f"{rr/sr if sr > 0 else float('nan'):7.2f} {rs:12.4f} {ss_:12.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
