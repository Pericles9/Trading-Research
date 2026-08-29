"""
Step 2: the resolution-floor distribution against the committed sub-burst duration
distributions. DESCRIPTION ONLY. No decision, no gate, nothing appended.

THE CAVEAT COMES FIRST BECAUSE IT BOUNDS EVERYTHING BELOW. D9's operating variable is
the inter-trade interval itself, and the lineage deliberately estimates no intensity.
`n_eff` is a property of a kernel-smoothed rate estimator, so **it does not bind D9's
construction on D9's own terms.** Nothing here says a committed sub-burst is wrong. The
comparison is between what this method can resolve and what that method reported, and a
gap is a statement about the two methods' domains, not a retraction of either.

So the load-bearing statement here is the one that needs no cross-method inference at
all, because it is read directly off the committed artifacts' own columns:

    HOW MANY PRINTS IS A COMMITTED SUB-BURST MADE OF?

That is answerable from `n_prints`, which every sub-burst artifact carries. It requires
no n_eff, no resolution floor, and no assumption from this method. It is reported first
and it is the finding. The s_min comparison follows as context.

Inputs, all committed:
    results/scale_field/artifacts/s_min_cohort.parquet   (step 1)
    results/phase_10/artifacts/v4_subbursts.parquet      v1->v4 lineage
    results/phase_10c/artifacts/s1_t1_subbursts.parquet  10c Stage 1
    results/phase_10d/artifacts/t4_subbursts.parquet     10d assembly grid

Usage: .venv/Scripts/python.exe research/scale_field/s_min_vs_subbursts.py
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import adapter  # noqa: E402
from adapter import rel  # noqa: E402

OUT = "results/scale_field/artifacts/s_min_vs_subbursts.json"
PRIMARY_KERNEL = 8.0        # config/phase_10d.json upstream_10c.kernel_primary_min

# EVERY SOURCE IS CUT TO ONE CELL. An earlier version of this script filtered 10d on
# kernel_min alone, which left 78 distinct (K, d, min_prints, sep) cells in the frame
# and took a median over a mixture of 1.93M rows across the whole assembly grid. The
# reference cell is committed in config/phase_10d.json: K=0 and d=0 are the identity
# merge (merge_grid.degenerate_cells), min_prints=2 is the TRUE no-op
# (min_prints_grid.reference, with the note that "the r1 draft's reference of 3 was
# wrong on this and was corrected at T0b"), and sep=hard_break is
# separator_grid.reference. Cut that way it is bit-identical to 10c Stage 1 at the same
# kernel -- 46,709 rows, same n_prints histogram -- which is what an identity merge over
# 10c's own runs should be, and is a useful internal check of the 10d pipeline.
SOURCES = [
    {"label": "v4", "path": "results/phase_10/artifacts/v4_subbursts.parquet",
     "dur": "duration_seconds", "select": None,
     "floor": 3,
     "what": "v1->v4 lineage, threshold-from-trough on log intervals",
     "cell": "the committed v4 artifact. config/phase_10_v4.json min_prints_reference = 3, "
             "so this distribution is CENSORED at 3 prints -- see floor_note."},
    {"label": "10c_s1", "path": "results/phase_10c/artifacts/s1_t1_subbursts.parquet",
     "dur": "duration_s", "select": {"kernel_min": PRIMARY_KERNEL},
     "floor": None,
     "what": "10c Stage 1, after the window fix",
     "cell": "kernel_min = 8. 10c applies NO run-length floor at any point (there is no "
             "min_prints variable in research/phase_10c/s1_t1_subbursts.py), so this "
             "distribution is UNCENSORED and is the one to read."},
    {"label": "10d_t4_reference", "path": "results/phase_10d/artifacts/t4_subbursts.parquet",
     "dur": "duration_s",
     "select": {"kernel_min": PRIMARY_KERNEL, "K": 0, "d": 0.0, "min_prints": 2,
                "sep": "hard_break"},
     "floor": None,
     "what": "10d assembly grid at its committed REFERENCE cell (D20)",
     "cell": "kernel_min=8, K=0, d=0.0, min_prints=2, sep=hard_break. Identity merge and "
             "no-op floor, so bit-identical to 10c Stage 1 at kernel 8 by construction."},
]


def q(a, qs=(0.05, 0.25, 0.5, 0.75, 0.95)) -> dict:
    a = np.asarray(a, float)
    a = a[np.isfinite(a) & (a > 0)]
    if a.size == 0:
        return {"n": 0}
    return {"n": int(a.size), "min": float(a.min()), "max": float(a.max()),
            **{f"q{int(x*100):02d}": float(np.quantile(a, x)) for x in qs}}


def main() -> int:
    sm = pd.read_parquet(rel("results/scale_field/artifacts/s_min_cohort.parquet"))
    sm["event_date_canonical"] = sm["event_date_canonical"].astype(str)
    key = ["ticker", "event_date_canonical"]
    floors = sm[key + ["segment", "s_min_session", "s_min_active", "s_min_q05",
                       "s_min_median"]].copy()

    best = float(sm["s_min_q05"].min())
    print(f"cohort n={len(sm)}   best s_min anywhere (any event, its best 5% of session) "
          f"= {best*1e3:.1f} ms")

    out = {
        "task": "step 2 -- resolution floor vs the committed sub-burst durations",
        "type": "DESCRIPTION ONLY. No decision, no gate, nothing appended to the register.",
        "config_hash": adapter.config_hash(),
        "caveat_first": "D9's operating variable is the inter-trade interval and the "
                        "lineage deliberately estimates no intensity, so n_eff does NOT "
                        "bind D9's construction on its own terms. Nothing here says a "
                        "committed sub-burst is wrong. The load-bearing statement is the "
                        "print count, which is read off the committed artifacts' own "
                        "columns and needs no cross-method inference.",
        "s_min_reference": {
            "best_anywhere_seconds": best,
            "best_anywhere_event": str(sm.loc[sm["s_min_q05"].idxmin(), "event_id"]),
            "best_anywhere_meaning": "the most favourable 5% of the session of the single "
                                     "densest event in the cohort. No event, at any moment, "
                                     "resolves below this.",
            "pooled_within_session_median_seconds": float(sm["s_min_median"].median()),
            "n_events_reaching_10ms_at_best": int((sm["s_min_q05"] <= 0.010).sum()),
            "n_events_reaching_100ms_at_best": int((sm["s_min_q05"] <= 0.100).sum()),
            "n_events_reaching_1s_at_best": int((sm["s_min_q05"] <= 1.0).sum()),
            "n_events": int(len(sm)),
        },
        "sources": {},
    }

    for src in SOURCES:
        path = rel(src["path"])
        if not os.path.exists(path):
            out["sources"][src["label"]] = {"present": False, "path": src["path"]}
            continue
        sel = src["select"] or {}
        cols = key + [src["dur"], "n_prints"] + [c for c in sel if c not in key]
        d = pd.read_parquet(path, columns=cols)
        d["event_date_canonical"] = d["event_date_canonical"].astype(str)
        rec = {"present": True, "path": src["path"], "what": src["what"],
               "cell": src["cell"], "n_subbursts_before_cell_cut": int(len(d))}
        for col, val in sel.items():
            d = d[np.isclose(d[col], val)] if isinstance(val, (int, float)) else d[d[col] == val]
        rec["cell_selector"] = {k: (float(v) if isinstance(v, (int, float)) else v)
                                for k, v in sel.items()}
        rec["n_subbursts_in_cell"] = int(len(d))

        # ---- THE FINDING: how many prints is a sub-burst made of?
        n = d["n_prints"].to_numpy()
        rec["prints_per_subburst"] = {
            "n": int(n.size), "min": int(n.min()), "max": int(n.max()),
            "q25": float(np.quantile(n, .25)), "median": float(np.median(n)),
            "q75": float(np.quantile(n, .75)),
            "share_eq_2": round(float((n == 2).mean()), 4),
            "share_le_3": round(float((n <= 3).mean()), 4),
            "share_le_5": round(float((n <= 5).mean()), 4),
            "share_le_10": round(float((n <= 10).mean()), 4),
        }
        if src["floor"]:
            rec["floor_note"] = (
                f"CENSORED: a run-length floor of {src['floor']} prints is configured for "
                f"this cell, so the distribution cannot show anything below it. The share "
                f"sitting exactly at {src['floor']} is pile-up ON the floor, not a natural "
                f"mode, and the true distribution below it is not observable here. Read the "
                f"uncensored sources instead.")
            rec["share_at_floor"] = round(float((n == src["floor"]).mean()), 4)
        rec["duration_seconds"] = q(d[src["dur"]])

        # ---- context: against each sub-burst's OWN event's floor
        m = d.merge(floors, on=key, how="inner")
        rec["n_joined_to_cohort"] = int(len(m))
        if len(m):
            for fl, lab in (("s_min_q05", "best_5pct_of_session"),
                            ("s_min_median", "median_moment_of_session"),
                            ("s_min_session", "session_mean_rate")):
                below = m[src["dur"]] < m[fl]
                rec[f"share_shorter_than_own_event_floor__{lab}"] = round(float(below.mean()), 4)
            rec["median_ratio_floor_over_duration"] = round(
                float((m["s_min_q05"] / m[src["dur"]]).median()), 1)
        out["sources"][src["label"]] = rec

        p = rec["prints_per_subburst"]
        lab = src["label"]
        cens = f"   [CENSORED at {src['floor']} prints]" if src["floor"] else ""
        print("")
        print(f"{lab:18s} n={rec['n_subbursts_in_cell']:,}"
              f"   median duration {rec['duration_seconds']['q50']*1e3:.4g} ms{cens}")
        print(f"                   prints: min {p['min']}  median {p['median']:.0f}  "
              f"(q25 {p['q25']:.0f}, q75 {p['q75']:.0f})   "
              f"=2: {p['share_eq_2']:.1%}   <=3: {p['share_le_3']:.1%}")
        if len(m):
            print(f"                   shorter than its own event's BEST-case floor: "
                  f"{rec['share_shorter_than_own_event_floor__best_5pct_of_session']:.1%}"
                  f"   median floor/duration ratio {rec['median_ratio_floor_over_duration']:,.0f}x")

    out["reading"] = (
        "On the UNCENSORED cells -- 10c Stage 1 at kernel 8, and 10d's reference cell, "
        "which are the same 46,709 objects -- the MODAL committed sub-burst is exactly "
        "2 prints: 49.3% of them. A 2-print object is a SINGLE INTERVAL. It has no "
        "internal structure by construction, and its 'duration' is one inter-trade gap "
        "rather than an estimated quantity. 66.9% are 3 prints or fewer. v4's median of 3 "
        "is not comparable: config/phase_10_v4.json sets min_prints_reference = 3, so "
        "that distribution is censored at 3 and the 54.1% sitting exactly there is "
        "pile-up on the floor. All of this is read off the artifacts' own n_prints column "
        "and requires nothing from this method. The resolution-floor comparison adds that "
        "no event in the cohort resolves below 58 ms at its most favourable moment -- but "
        "that comparison is across methods and carries the caveat above, whereas the print "
        "count does not. NOTE WHAT THIS DOES NOT SAY: three prints inside 1.75 ms on a "
        "tape running at 0.30 prints/s is astronomically improbable under any stationary "
        "null, so the CLUSTERS ARE REAL. What is not supported is their DURATION as a "
        "measured quantity. Detection needs far fewer prints than rate estimation.")
    out["source"] = "research/scale_field/s_min_vs_subbursts.py:main"
    out["reproduce"] = ".venv/Scripts/python.exe research/scale_field/s_min_vs_subbursts.py"

    with open(rel(OUT), "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    print(f"\nwrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
