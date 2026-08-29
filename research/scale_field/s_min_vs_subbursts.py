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

SOURCES = [
    {"label": "v4", "path": "results/phase_10/artifacts/v4_subbursts.parquet",
     "dur": "duration_seconds", "kernel": None,
     "what": "the v1->v4 sub-burst lineage, threshold-from-trough on log intervals"},
    {"label": "10c_s1", "path": "results/phase_10c/artifacts/s1_t1_subbursts.parquet",
     "dur": "duration_s", "kernel": "kernel_min",
     "what": "10c Stage 1, after the window fix"},
    {"label": "10d_t4", "path": "results/phase_10d/artifacts/t4_subbursts.parquet",
     "dur": "duration_s", "kernel": "kernel_min",
     "what": "10d assembly grid (merge tolerance x run-length floor, D20)"},
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
        cols = key + [src["dur"], "n_prints"] + ([src["kernel"]] if src["kernel"] else [])
        d = pd.read_parquet(path, columns=cols)
        d["event_date_canonical"] = d["event_date_canonical"].astype(str)
        rec = {"present": True, "path": src["path"], "what": src["what"],
               "n_subbursts_all": int(len(d))}

        if src["kernel"]:
            d = d[np.isclose(d[src["kernel"]], PRIMARY_KERNEL)]
            rec["kernel_filter"] = f"{src['kernel']} == {PRIMARY_KERNEL} (10c/10d primary)"
            rec["n_subbursts_primary_kernel"] = int(len(d))

        # ---- THE FINDING: how many prints is a sub-burst made of?
        n = d["n_prints"].to_numpy()
        rec["prints_per_subburst"] = {
            "n": int(n.size), "min": int(n.min()), "max": int(n.max()),
            "q25": float(np.quantile(n, .25)), "median": float(np.median(n)),
            "q75": float(np.quantile(n, .75)),
            "share_le_3": round(float((n <= 3).mean()), 4),
            "share_le_5": round(float((n <= 5).mean()), 4),
            "share_le_10": round(float((n <= 10).mean()), 4),
        }
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
        print(f"\n{src['label']:8s} n={rec.get('n_subbursts_primary_kernel', rec['n_subbursts_all']):,}"
              f"   median duration {rec['duration_seconds']['q50']*1e3:.3g} ms")
        print(f"         prints per sub-burst: median {p['median']:.0f}  "
              f"(q25 {p['q25']:.0f}, q75 {p['q75']:.0f})   "
              f"<=3 prints: {p['share_le_3']:.1%}   <=5: {p['share_le_5']:.1%}")
        if len(m):
            print(f"         shorter than its own event's BEST-case floor: "
                  f"{rec['share_shorter_than_own_event_floor__best_5pct_of_session']:.1%}"
                  f"   median floor/duration ratio {rec['median_ratio_floor_over_duration']:,.0f}x")

    out["reading"] = (
        "The median committed sub-burst is 2-4 prints across all three lineages, with "
        "46-71% of them at 3 prints or fewer. That is read off the artifacts' own "
        "n_prints column and requires nothing from this method. Cooper's phrasing -- 'a "
        "statement about the two or three fastest prints in a session, not about a market "
        "state' -- is therefore not a hypothesis awaiting test; it is what the committed "
        "artifacts already say about themselves. The resolution-floor comparison adds "
        "that no event in the cohort resolves below 58 ms at its most favourable moment, "
        "which is 21x above 10d's median sub-burst duration and 5 orders of magnitude "
        "above v4's -- but that comparison is across methods and carries the caveat above, "
        "whereas the print count does not.")
    out["source"] = "research/scale_field/s_min_vs_subbursts.py:main"
    out["reproduce"] = ".venv/Scripts/python.exe research/scale_field/s_min_vs_subbursts.py"

    with open(rel(OUT), "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)
    print(f"\nwrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
