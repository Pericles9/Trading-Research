#!/usr/bin/env python
"""Is the segment the right conditioning variable, or is it just rate? (review s2a)

THE INVERSION TO EXPLAIN. In regular hours the marks land where the tape is FAST
(mark-weighted ~2.1/s against a session mean of 0.30/s). In premarket they land where
it is SLOW (~0.06/s implied, against a session mean of 2.11/s). The sign flips between
segments, which no skew artifact does.

THE MECHANISM THE REVIEW PROPOSES, and it is checkable. n_eff on the read path is
constant -- n_eff = 2*sqrt(pi)*s*lambda with s = rf*2.2568/lambda gives 8.01*rf at every
rate -- so survivorship is not an n_eff effect and the threshold is identical
everywhere. But the SIGNAL is not scale-free: a smooth envelope of curvature scale L
contributes F ~ (s/L)^2, which is 4e-4 at s = 4 s against L = 200 s and ~0.6 at
s = 153 s. So the boundary-following read has a second geometric bias, distinct from
the count-proportional-to-print-count one already retired: THE SLOWER THE TAPE, THE
COARSER THE READ, THE MORE ENVELOPE ENTERS, THE MORE LIKELY THE CELL SURVIVES.

If that is the mechanism, SEGMENT IS THE WRONG CONDITIONING VARIABLE and the finding
should be restated on local rate, where it becomes portable: the field detects real
structure wherever the tape is fast enough to be read below the crossover, whatever
segment that happens in.

THE TEST. Pool every defined cell from every segment, bin on local lambda-hat, and ask
whether premarket and regular-hours cells IN THE SAME RATE BIN behave the same -- same
read scale (which is arithmetic, s* = rf*2.2568/lambda, and so a check that the binning
works), and the same survivor fraction (which is not arithmetic and is the question).

Premarket and regular hours are still never POOLED into one number; they are compared
within matched rate bins, which is the opposite of pooling.
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

import event_panels as ep                                          # noqa: E402
from instrument_gates import (KERNELS, OUT, READ_FACTORS,          # noqa: E402
                              NoiseRuler, cohort, event_field, jdump,
                              read_at, segment_masks)

RATE_EDGES = np.array([0.0, 0.03, 0.1, 0.3, 1.0, 3.0, 10.0, 30.0, 100.0, np.inf])
BAND_S = 30.0


def main() -> int:
    cfg = ep.load_config()
    with open(os.path.join(OUT, "gateC_null_rate.json"), encoding="utf-8") as f:
        rows = json.load(f)["rows"]
    ruler = NoiseRuler(rows, "centred", "unconditional")

    acc = {}      # (segment, rate_bin, rf) -> accumulators
    for eid in list(cohort()["event_id"]):
        d = event_field(eid, cfg)
        segs = segment_masks(d["grid_ns"], eid.split("_")[1])
        dt = d["dt_eval"]
        n = d["Z_centred"].shape[0]
        lam = d["lam_centred"][:n]
        rb = np.digitize(lam, RATE_EDGES) - 1
        for f_ in READ_FACTORS:
            r = read_at(d, "centred", f_, debounce=True, cfg=cfg)
            sd2 = 2 * ruler.sd_at(r["n_eff"][:n])
            F = r["F"][:n]
            surv = r["on"][:n] & np.isfinite(F) & (F < -sd2)
            ss = r["s_star"][:n]
            for sname in ("premarket", "rth", "post"):
                m = segs[sname][:n] & np.isfinite(F) & np.isfinite(lam)
                for b in range(len(RATE_EDGES) - 1):
                    sel = m & (rb == b)
                    if not sel.any():
                        continue
                    k = (sname, b, f"{f_:g}")
                    a = acc.setdefault(k, {"t": 0.0, "t_on": 0.0, "t_surv": 0.0,
                                           "t_below30": 0.0, "sw": 0.0, "ss": 0.0,
                                           "n_ev": set()})
                    w = dt[:n][sel]
                    a["t"] += float(w.sum())
                    a["t_on"] += float(dt[:n][sel & r["on"][:n]].sum())
                    a["t_surv"] += float(dt[:n][sel & surv].sum())
                    a["t_below30"] += float(dt[:n][sel & surv & (ss < BAND_S)].sum())
                    good = sel & np.isfinite(ss)
                    a["sw"] += float(dt[:n][good].sum())
                    a["ss"] += float((dt[:n][good] * ss[good]).sum())
                    a["n_ev"].add(eid)
        print("  by-rate", eid.split("_")[0], "done", flush=True)

    res = {"rate_edges": [float(v) for v in RATE_EDGES], "band_s": BAND_S,
           "note": __doc__, "cells": {}}
    for (sname, b, f_), a in acc.items():
        res["cells"][f"{sname}|{b}|{f_}"] = {
            "segment": sname, "rate_bin": b,
            "rate_lo": float(RATE_EDGES[b]), "rate_hi": float(RATE_EDGES[b + 1]),
            "read_factor": float(f_), "n_events": len(a["n_ev"]),
            "defined_seconds": a["t"],
            "shaded_fraction": a["t_on"] / a["t"] if a["t"] > 0 else float("nan"),
            "survivor_fraction": a["t_surv"] / a["t"] if a["t"] > 0 else float("nan"),
            "survivor_share_below_30s": a["t_below30"] / a["t_surv"]
            if a["t_surv"] > 0 else float("nan"),
            "mean_read_scale_s": a["ss"] / a["sw"] if a["sw"] > 0 else float("nan")}
    jdump(res, "read_by_rate.json")

    for f_ in (1.0, 4.0):
        print(f"\n{'=' * 104}\nMATCHED ON LOCAL RATE, read_factor {f_:g}  "
              f"(segments compared within rate bins, never pooled)\n{'=' * 104}")
        print(f"{'lambda bin (/s)':>18s} {'seg':>10s} {'hours':>8s} {'mean s*':>9s} "
              f"{'shaded':>8s} {'survivor':>9s} {'surv<30s':>9s} {'n ev':>5s}")
        for b in range(len(RATE_EDGES) - 1):
            for sname in ("premarket", "rth"):
                k = f"{sname}|{b}|{f_:g}"
                if k not in res["cells"]:
                    continue
                c = res["cells"][k]
                if c["defined_seconds"] < 600:
                    continue
                print(f"{f'{RATE_EDGES[b]:g}-{RATE_EDGES[b+1]:g}':>18s} {sname:>10s} "
                      f"{c['defined_seconds']/3600:8.2f} {c['mean_read_scale_s']:9.2f} "
                      f"{c['shaded_fraction']:8.3f} {c['survivor_fraction']:9.4f} "
                      f"{c['survivor_share_below_30s']:9.3f} {c['n_events']:5d}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
