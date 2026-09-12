#!/usr/bin/env python
"""Where, in ABSOLUTE SECONDS, does the read actually land -- weighted by the marks?

THE TENSION THIS SETTLES (review s1). Gate B's survivors concentrate at the coarse end
of the ladder. The surrogate control says the excess above ~64 s is entirely the rate
path. If the marks that clear the noise ruler sit above 64 s then the threshold is
firing on the session envelope, and "detects cleanly at read_factor 4" would be a
statement about the clock.

WHY THE SESSION-MEAN RATE IS THE WRONG DENOMINATOR and would understate this: marks
concentrate where the tape is fast, so the read scale WHERE MARKS ACTUALLY OCCUR is
far finer than a session-mean lambda implies. Every distribution here is therefore
weighted by the thing being asked about --

    marked_weighted     : time-weighted over cells the boolean marks
    survivor_weighted   : time-weighted over cells that also clear F < -2*sd
    all_defined         : the unweighted comparison, so the shift is visible

-- and reported per segment, because premarket and regular hours are not poolable
(v3, 0.903 decades, failure row 5).

THE TWO REFERENCE LINES come from surrogate_control.py, not from this script:
30 s is the surrogate bandwidth, below which the surrogate carries no structure at all
and the real tape's excess is therefore not a rate path; 64 s is where real and
surrogate ratios converge (real/surrogate 0.76-1.03), above which the excess IS the
rate path. Between them is unadjudicated.
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

import adapter                                                    # noqa: E402
import event_panels as ep                                         # noqa: E402
from instrument_gates import (CACHE, KERNELS, OUT, READ_FACTORS,   # noqa: E402
                              NoiseRuler, event_field, cohort, jdump,
                              read_at, segment_masks)

REAL_BAND_S = 30.0        # surrogate bandwidth: below this the surrogate has nothing
CLOCK_BAND_S = 64.0       # above this real and surrogate ratios coincide


def wq(x, w, qs=(0.05, 0.25, 0.5, 0.75, 0.95)):
    """Weighted quantiles. The weight is TIME, not cells: on a print-indexed grid a
    column in a dead stretch spans minutes and one near the anchor spans milliseconds,
    so a cell-count quantile would be a statement about the grid."""
    ok = np.isfinite(x) & np.isfinite(w) & (w > 0)
    if ok.sum() < 20:
        return {str(q): float("nan") for q in qs}
    xs, ws = x[ok], w[ok]
    i = np.argsort(xs)
    xs, ws = xs[i], ws[i]
    c = np.cumsum(ws) / ws.sum()
    return {str(q): float(np.interp(q, c, xs)) for q in qs}


def main() -> int:
    cfg = ep.load_config()
    with open(os.path.join(OUT, "gateC_null_rate.json"), encoding="utf-8") as f:
        rows = json.load(f)["rows"]
    ruler = {k: NoiseRuler(rows, k, "unconditional") for k in KERNELS}

    res = {"reference_bands": {"real_excess_below_s": REAL_BAND_S,
                               "rate_path_above_s": CLOCK_BAND_S,
                               "source": "surrogate_control.json"},
           "note": __doc__, "events": {}}

    for eid in list(cohort()["event_id"]):
        d = event_field(eid, cfg)
        segs = segment_masks(d["grid_ns"], eid.split("_")[1])
        dt = d["dt_eval"]
        e = {}
        for kern in KERNELS:
            n = d["Z_" + kern].shape[0]
            ke = {}
            for f_ in READ_FACTORS:
                r = read_at(d, kern, f_, debounce=True, cfg=cfg)
                sd2 = 2 * ruler[kern].sd_at(r["n_eff"][:n])
                surv = r["on"][:n] & np.isfinite(r["F"][:n]) & (r["F"][:n] < -sd2)
                ss = r["s_star"][:n]
                row = {}
                for sname, sm in list(segs.items()) + [("all", np.ones(n, bool))]:
                    m = sm[:n]
                    sel = {"all_defined": m & np.isfinite(ss) & np.isfinite(r["F"][:n]),
                           "marked_weighted": m & r["on"][:n] & np.isfinite(ss),
                           "survivor_weighted": m & surv & np.isfinite(ss)}
                    q = {}
                    for tag, s_ in sel.items():
                        w = np.where(s_, dt[:n], 0.0)
                        tot = float(w.sum())
                        q[tag] = {
                            "seconds": tot,
                            "quantiles_s": wq(ss, w),
                            "share_below_30s": float(w[ss < REAL_BAND_S].sum() / tot)
                            if tot > 0 else float("nan"),
                            "share_above_64s": float(w[ss > CLOCK_BAND_S].sum() / tot)
                            if tot > 0 else float("nan"),
                        }
                    row[sname] = q
                ke[f"{f_:g}"] = row
            e[kern] = ke
        res["events"][eid] = e
        c = e["centred"]["4"]
        print(f"  {eid.split('_')[0]:6s} rf4 survivor-weighted median s*: "
              f"rth {c['rth']['survivor_weighted']['quantiles_s']['0.5']:8.2f}s "
              f"(<30s {c['rth']['survivor_weighted']['share_below_30s']:.2f}) | "
              f"pre {c['premarket']['survivor_weighted']['quantiles_s']['0.5']:7.2f}s "
              f"(<30s {c['premarket']['survivor_weighted']['share_below_30s']:.2f})",
              flush=True)

    jdump(res, "read_scale_distribution.json")

    print("\n" + "=" * 100)
    print("READ SCALE IN ABSOLUTE SECONDS, weighted by SURVIVING marks (centred), "
          "median across the ten events")
    print("=" * 100)
    for seg in ("premarket", "rth", "post"):
        print(f"\n--- {seg} ---")
        print(f"{'rf':>3s} {'q05':>8s} {'q25':>8s} {'median':>8s} {'q75':>8s} "
              f"{'q95':>8s} {'share<30s':>10s} {'share>64s':>10s}")
        for f_ in READ_FACTORS:
            g = [res["events"][e]["centred"][f"{f_:g}"][seg]["survivor_weighted"]
                 for e in res["events"]]
            qs = lambda k: np.nanmedian([x["quantiles_s"][k] for x in g])
            print(f"{f_:3.0f} {qs('0.05'):8.2f} {qs('0.25'):8.2f} {qs('0.5'):8.2f} "
                  f"{qs('0.75'):8.2f} {qs('0.95'):8.2f} "
                  f"{np.nanmedian([x['share_below_30s'] for x in g]):10.3f} "
                  f"{np.nanmedian([x['share_above_64s'] for x in g]):10.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
