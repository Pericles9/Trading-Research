"""
Phase 10d T3 -- the counterfactual gate report. DESCRIPTION ONLY. Nothing is applied.

T3a  void-parameter distribution under 10c's argmax-void selection, pooled and per
     segment, per kernel
T3b  share of ok cells that WOULD be declined at each pre-registered candidate cutoff
T3c  10c cannot decline on void magnitude; the peak-count decline path exists and fired
     0/504; insufficient_context reported alongside as a DIFFERENT quantity
T3d  the D9 Zaliapin tension, recorded and not resolved

No cutoff enters the computation path here or anywhere downstream (escalation 10d-R7).

DOUBLE-COUNTING NOTE, stated rather than left implicit: the void parameter is a function
of (event, kernel) only -- 10c computes sub-burst extraction once per (event, kernel) and
cross-joins onto each variant's segment/anchor labelling. So the 504-row cell artifact
holds only 168 DISTINCT void values. Void distributions are therefore reported over the
168 distinct (event, kernel) cells; anything cut by segment is reported per variant,
because segment membership is the one thing the variant changes.

Usage: .venv/Scripts/python.exe research/phase_10d/t3_counterfactual.py
"""
from __future__ import annotations

import hashlib
import json
import os

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
ART = os.path.join(ROOT, "results", "phase_10d", "artifacts")
KEY = ["ticker", "event_date_canonical"]


def cfg():
    with open(os.path.join(ROOT, "config", "phase_10d.json"), encoding="utf-8") as f:
        return json.load(f)


def cfg_hash(d):
    return hashlib.sha256(json.dumps(d, sort_keys=True).encode()).hexdigest()[:8]


def q(a):
    a = np.asarray(a, dtype=float)
    a = a[np.isfinite(a)]
    if a.size == 0:
        return {"n": 0}
    return {"n": int(a.size), "min": float(a.min()), "q25": float(np.quantile(a, .25)),
            "median": float(np.median(a)), "q75": float(np.quantile(a, .75)),
            "max": float(a.max())}


def main() -> int:
    conf = cfg()
    chash = cfg_hash(conf)
    cells = pd.read_parquet(os.path.join(ROOT, conf["upstream_10c"]["cells_artifact"]))

    # ---- assert the upstream structure rather than trusting the prompt
    assert len(cells) == 504, f"expected 504 cells, got {len(cells)}"
    kernels = sorted(cells.kernel_min.unique().tolist())
    variants = sorted(cells.threshold.unique().tolist())
    assert kernels == conf["upstream_10c"]["kernels_min"], kernels
    labels_present = sorted(cells.label.unique().tolist())

    distinct = cells.drop_duplicates(subset=KEY + ["kernel_min"])
    assert len(distinct) == 168, f"expected 168 distinct (event,kernel), got {len(distinct)}"

    # ---------------------------------------------------------------- T3a
    t3a = {"_basis": ("168 distinct (event, kernel) cells -- void is variant-independent; "
                      "segment cuts are reported per variant because segment membership is "
                      "the only thing the variant changes"),
           "pooled_by_kernel": {}, "by_kernel_variant_segment": []}
    for k in kernels:
        sub = distinct[(distinct.kernel_min == k) & (distinct.label == "ok")]
        t3a["pooled_by_kernel"][f"{k:g}min"] = q(sub.void)
    t3a["pooled_all_kernels"] = q(distinct[distinct.label == "ok"].void)

    for k in kernels:
        for v in variants:
            for seg in ["premarket", "rth", "evening", None]:
                s = cells[(cells.kernel_min == k) & (cells.threshold == v)
                          & (cells.label == "ok")]
                s = s[s.segment.isna()] if seg is None else s[s.segment == seg]
                st = q(s.void)
                if st["n"]:
                    t3a["by_kernel_variant_segment"].append(
                        {"kernel_min": float(k), "variant": float(v),
                         "segment": seg or "unlabelled", **st})

    # ---------------------------------------------------------------- T3b
    cutoffs = conf["counterfactual_cutoffs"]["values"]
    rows = []
    for k in kernels:
        sub = distinct[(distinct.kernel_min == k) & (distinct.label == "ok")]
        for c in cutoffs:
            n_below = int((sub.void < c).sum())
            rows.append({"scope": "distinct_event_kernel", "kernel_min": float(k),
                         "variant": None, "segment": "all", "cutoff": float(c),
                         "n_ok": int(len(sub)), "n_would_decline": n_below,
                         "would_decline_share": n_below / len(sub) if len(sub) else np.nan})
    for k in kernels:
        for v in variants:
            for seg in ["premarket", "rth", "evening", None]:
                s = cells[(cells.kernel_min == k) & (cells.threshold == v)
                          & (cells.label == "ok")]
                s = s[s.segment.isna()] if seg is None else s[s.segment == seg]
                if not len(s):
                    continue
                for c in cutoffs:
                    n_below = int((s.void < c).sum())
                    rows.append({"scope": "variant_segment", "kernel_min": float(k),
                                 "variant": float(v), "segment": seg or "unlabelled",
                                 "cutoff": float(c), "n_ok": int(len(s)),
                                 "n_would_decline": n_below,
                                 "would_decline_share": n_below / len(s)})
    t3b = pd.DataFrame(rows)
    t3b["applied"] = False
    t3b.to_parquet(os.path.join(ART, "t3_void_counterfactual.parquet"), index=False)

    # ---------------------------------------------------------------- T3c
    n_no_threshold = int((cells.label == "no_threshold").sum())
    n_unimodal = int((cells.label == "unimodal").sum())
    ic_rows = []
    for k in kernels:
        for v in variants:
            for seg in ["premarket", "rth", "evening", None]:
                s = cells[(cells.kernel_min == k) & (cells.threshold == v)]
                s = s[s.segment.isna()] if seg is None else s[s.segment == seg]
                if not len(s):
                    continue
                n_ic = int((s.label == "insufficient_context").sum())
                ic_rows.append({"kernel_min": float(k), "variant": float(v),
                                "segment": seg or "unlabelled", "n_cells": int(len(s)),
                                "n_insufficient_context": n_ic,
                                "share": n_ic / len(s)})
    ic = pd.DataFrame(ic_rows)

    t3c = {
        "labels_present_in_artifact": labels_present,
        "no_threshold_count": n_no_threshold,
        "no_threshold_share": n_no_threshold / len(cells),
        "unimodal_count": n_unimodal,
        "statement": (
            "10c CANNOT DECLINE ON VOID MAGNITUDE. config/phase_10c.json "
            "/settled/D13_void_parameter/threshold is null, marked 'deliberate and "
            "permanent': the void parameter ranks troughs and never gates. A DECLINE PATH "
            "ON PEAK COUNT DOES EXIST -- research/phase_10c/s1_t1_subbursts.py emits "
            "no_threshold when fewer than two peaks survive the Poisson floor, or when no "
            "valid trough pair exists -- and it fired "
            f"{n_no_threshold}/{len(cells)} on this cohort. 'unimodal' likewise appears "
            f"{n_unimodal} times."),
        "insufficient_context_by_cell": ic_rows,
        "insufficient_context_share_range": [float(ic.share.min()), float(ic.share.max())],
        "different_quantities": (
            "insufficient_context and no_threshold are NOT comparable and must never be "
            "presented as the same measurement. insufficient_context is a DATA-COVERAGE "
            "verdict: the centered window held fewer intervals than the per-event derived "
            "floor (n >= (sqrt(pi/2)*sigma_log10/log10 1.5)^2), or the cell held fewer "
            "than 50 ok intervals. no_threshold is a SHAPE verdict about bimodality. A "
            "thin window says nothing about whether the distribution is bimodal, and v4's "
            "10/100 no_threshold share is a shape measurement with no counterpart in 10c's "
            "output."),
        "v4_no_threshold_reference": (
            "v4's 10/100 is NOT read from this phase's artifacts and is not restated as a "
            "10d measurement. It is cited only to say that 10c has no comparable quantity."),
    }

    # ---------------------------------------------------------------- T3d
    t3d = {"tension": (
        "D9 adopts Zaliapin's reasoning that the share of events where bimodality fails is "
        "a HEADLINE RESULT, not an inconvenience -- the whole T=0 session sits in the "
        "vicinity of the dominant event, exactly where bimodality is known to break. 10c's "
        "argmax-void selection ranks troughs and never gates on void magnitude, so it "
        "returns a threshold for every cell that clears the data floor. A method that "
        "never declines on shape cannot produce the share D9 calls headline. The "
        "counterfactual above is the size of what is not being produced; it is reported "
        "and nothing is applied."),
        "resolved": False,
        "resolution_owner": "a successor phase, on Cooper's decision; see D20 'Whether an "
                            "applicability gate should exist is left open'"}

    out = {"phase": "10d", "task": "T3", "config_hash": chash,
           "source_artifact": conf["upstream_10c"]["cells_artifact"],
           "cutoffs_reported": cutoffs, "cutoffs_applied": [],
           "no_cutoff_applied": True,
           "T3a_void_distribution": t3a,
           "T3b_counterfactual": {"artifact": "results/phase_10d/artifacts/t3_void_counterfactual.parquet",
                                  "n_rows": int(len(t3b)),
                                  "distinct_scope_rows": t3b[t3b.scope == "distinct_event_kernel"]
                                  .to_dict("records")},
           "T3c_decline_paths": t3c,
           "T3d_zaliapin_tension": t3d}
    with open(os.path.join(ART, "t3_summary.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, default=str)

    print(f"config_hash {chash}")
    print("\nT3a void, distinct (event,kernel) ok cells:")
    for k, v in t3a["pooled_by_kernel"].items():
        print(f"  {k:>6}  n={v['n']:3d}  min {v['min']:.3f}  q25 {v['q25']:.3f}  "
              f"med {v['median']:.3f}  q75 {v['q75']:.3f}  max {v['max']:.3f}")
    print("\nT3b would-decline share (REPORTED, NOT APPLIED):")
    piv = (t3b[t3b.scope == "distinct_event_kernel"]
           .pivot(index="cutoff", columns="kernel_min", values="would_decline_share"))
    print(piv.round(4).to_string())
    print(f"\nT3c no_threshold {n_no_threshold}/{len(cells)}; unimodal {n_unimodal}; "
          f"insufficient_context share {ic.share.min():.3f}-{ic.share.max():.3f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
