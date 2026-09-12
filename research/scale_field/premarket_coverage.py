#!/usr/bin/env python
"""Is the premarket conclusion a grid-coverage artifact? (review 2026-09-09 s2b)

THE HYPOTHESIS. At premarket's dense moments s* = rf * 2.2568/lambda is very small. The
committed ladder floor is 0.25 s. If those reads fall off the bottom of the ladder they
are not marked at the scale the rule asks for -- they are either dropped, or silently
taken at the floor, which is ABOVE rf * s_min. Either way the fast stretches would be
mechanically under-represented, leaving only the slow-stretch reads behind, and
"premarket reads at 153 s" would be a statement about the grid rather than the tape.

WHAT burst_on ACTUALLY DOES, checked in the code rather than assumed: scale_index_at
takes the smallest ladder scale >= factor * s_min(t) that is also defined. Where
factor * s_min falls BELOW the ladder floor the read is taken AT THE FLOOR -- so the
cell is NOT dropped, it is read too coarse. config/scale_field_panels.json calls this
out under ladder_floor_binds and requires the share to be reported per event.

So there are two distinct leaks and they are counted separately:

  floor_binds      rf * s_min(t) < 0.25 s  -- read too coarse, cell still marked
  no_scale_clears  no ladder scale qualifies at all -- cell genuinely absent
  masked           the field is NaN there (n_eff < 8) -- absent for a data reason

If floor_binds is material in premarket at rf 4, the premarket median read scale is
biased UP by exactly the mechanism the review describes, and the premarket conclusion
is void until it is recomputed on a ladder that reaches lower.
"""
from __future__ import annotations

import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(REPO_ROOT, "research", "phase_10d_diag1"))

import event_panels as ep                                          # noqa: E402
from instrument_gates import (KERNELS, READ_FACTORS, cohort,        # noqa: E402
                              event_field, jdump, segment_masks)


def main() -> int:
    cfg = ep.load_config()
    floor = float(ep.ladder(cfg)[0])
    res = {"ladder_floor_s": floor, "note": __doc__, "events": {}}
    print(f"ladder floor = {floor} s\n")

    for eid in list(cohort()["event_id"]):
        d = event_field(eid, cfg)
        segs = segment_masks(d["grid_ns"], eid.split("_")[1])
        dt = d["dt_eval"]
        n = d["Z_centred"].shape[0]
        smin = d["smin_centred"][:n]
        Z = d["Z_centred"]
        defined_any = np.isfinite(Z[:n]).any(axis=1)
        e = {}
        for sname in ("premarket", "rth", "post"):
            m = segs[sname][:n]
            w = np.where(m, dt[:n], 0.0)
            tot = float(w.sum())
            row = {"segment_seconds": tot,
                   "lambda_q10": float(np.nanquantile(d["lam_centred"][:n][m], 0.10)),
                   "lambda_median": float(np.nanmedian(d["lam_centred"][:n][m])),
                   "lambda_q90": float(np.nanquantile(d["lam_centred"][:n][m], 0.90)),
                   "by_rf": {}}
            for f_ in READ_FACTORS:
                target = f_ * smin
                fb = np.isfinite(target) & (target < floor)
                row["by_rf"][f"{f_:g}"] = {
                    "floor_binds_time_share": float(w[fb].sum() / tot)
                    if tot > 0 else float("nan"),
                    "masked_everywhere_time_share": float(
                        w[~defined_any].sum() / tot) if tot > 0 else float("nan"),
                    "target_below_floor_median_s": float(
                        np.nanmedian(target[fb])) if fb.any() else float("nan"),
                }
            e[sname] = row
        res["events"][eid] = e

    jdump(res, "premarket_coverage.json")

    print("SHARE OF SEGMENT TIME WHERE THE LADDER FLOOR BINDS "
          "(rf * s_min < 0.25 s: read TOO COARSE, cell still marked)")
    print(f"{'segment':>11s} " + "".join(f"{'rf' + f'{f:g}':>9s}" for f in READ_FACTORS)
          + f"{'masked':>9s}{'lam q10':>9s}{'lam med':>9s}{'lam q90':>9s}")
    for sname in ("premarket", "rth", "post"):
        g = [res["events"][e][sname] for e in res["events"]]
        vals = [np.median([x["by_rf"][f"{f:g}"]["floor_binds_time_share"] for x in g])
                for f in READ_FACTORS]
        print(f"{sname:>11s} " + "".join(f"{v:9.4f}" for v in vals)
              + f"{np.median([x['by_rf']['4']['masked_everywhere_time_share'] for x in g]):9.4f}"
              + f"{np.median([x['lambda_q10'] for x in g]):9.3f}"
              + f"{np.median([x['lambda_median'] for x in g]):9.3f}"
              + f"{np.median([x['lambda_q90'] for x in g]):9.3f}")

    print("\nPer event, premarket, rf = 4:")
    print(f"{'event':>10s} {'floor binds':>12s} {'masked':>9s} {'lam q90':>9s} "
          f"{'rf4*smin at q90 lam':>20s}")
    for eid in res["events"]:
        p = res["events"][eid]["premarket"]
        print(f"{eid.split('_')[0]:>10s} {p['by_rf']['4']['floor_binds_time_share']:12.4f} "
              f"{p['by_rf']['4']['masked_everywhere_time_share']:9.4f} "
              f"{p['lambda_q90']:9.3f} {4*2.2567583341910247/p['lambda_q90']:20.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
