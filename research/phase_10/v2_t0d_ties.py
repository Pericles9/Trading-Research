"""
Phase 10 v2 T0d -- timestamp-tie structure.

Ties are a first-order concern for any rate estimator and are characterized here
BEFORE one is chosen: a block of k prints sharing one timestamp has zero elapsed
span, and an unguarded kNN rate estimator returns infinity there. v1 floored
370,525 gaps (mean 2.7% of prints, correlated 0.64 with print count).

Phase 13 boundary (v2 context): this is a TIE-STRUCTURE diagnostic -- the share
of consecutive prints sharing a timestamp and the timestamp resolution actually
present. It is NOT an inter-trade interval distribution, no noise floor is
characterized, and no interval regime is defined.

Usage: .venv/Scripts/python.exe research/phase_10/v2_t0d_ties.py
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from v2_common import (  # noqa: E402
    COHORT_KEY, POOLED, config_hash_v2, load_config_v2, load_frozen_cohort,
    quantiles, read_event_trades, rel, tie_structure, write_json,
)

OUT = "v2_t0d_tie_structure.parquet"
OUT_SUMMARY = "v2_t0d_tie_structure.json"


def main() -> int:
    cfg = load_config_v2()
    chash = config_hash_v2()
    out_dir = rel(cfg["paths"]["out_artifacts"])
    cohort = load_frozen_cohort(cfg)
    k_grid = cfg["estimator"]["k_grid"]

    rows = []
    for r in cohort.itertuples(index=False):
        d = read_event_trades(cfg, r.ticker, r.event_date_canonical, r.momentum_pct, offsets=(0,))
        t0 = d.get(0)
        ts = np.zeros(0, dtype=np.int64) if t0 is None else t0["sip_timestamp"].to_numpy()
        st = tie_structure(ts)
        rows.append({"ticker": r.ticker, "event_date_canonical": r.event_date_canonical,
                     "momentum_pct": r.momentum_pct, "cohort_group": r.cohort_group,
                     **st,
                     "collapse_ratio": (st["n_distinct_timestamps"] / st["n_prints"])
                     if st["n_prints"] else None,
                     **{f"k{k}_exceeds_n": bool(k > st["n_prints"]) for k in k_grid},
                     **{f"k{k}_exceeds_distinct": bool(k > st["n_distinct_timestamps"]) for k in k_grid}})

    t = pd.DataFrame(rows)
    t.to_parquet(os.path.join(out_dir, OUT), index=False)
    pooled = t[t["cohort_group"].isin(POOLED)]

    def grp(sub):
        return {
            "n_events": int(len(sub)),
            "n_prints_total": int(sub["n_prints"].sum()),
            "n_tied_with_prev_total": int(sub["n_tied_with_prev"].sum()),
            "share_tied_overall": float(sub["n_tied_with_prev"].sum() / max(sub["n_prints"].sum() - len(sub), 1)),
            "share_tied_per_event": quantiles(sub["share_tied"]),
            "max_tie_run": quantiles(sub["max_tie_run"]),
            "distinct_timestamp_ratio": quantiles(sub["collapse_ratio"]),
            "n_events_with_zero_ties": int((sub["n_tied_with_prev"] == 0).sum()),
        }

    res = {
        "n": int(pooled["min_nonzero_gap_ns"].notna().sum()),
        "min_ns_observed": int(pooled["min_nonzero_gap_ns"].min()) if pooled["min_nonzero_gap_ns"].notna().any() else None,
        "median_min_gap_ns": float(pooled["min_nonzero_gap_ns"].median()) if pooled["min_nonzero_gap_ns"].notna().any() else None,
    }

    summary = {
        "phase": "10", "version": "v2", "task": "T0d", "config_hash": chash,
        "what_this_is": "tie structure only. NOT an inter-trade interval distribution, no noise "
                        "floor, no interval regime -- those are Phase 13's deliverable.",
        "by_group": {g: grp(sub) for g, sub in t.groupby("cohort_group")},
        "pooled_analysis_cohort": grp(pooled),
        "timestamp_resolution_present": {
            **res,
            "note": "smallest NON-ZERO inter-arrival gap observed per event, pooled. This is the "
                    "resolution actually present in the data, as distinct from the nominal ns "
                    "field width.",
        },
        "estimator_consequence": {
            "zero_span_floor_seconds": cfg["estimator"]["zero_span_floor_seconds"],
            "n_events_where_k_exceeds_distinct_timestamps": {
                f"k{k}": int(pooled[f"k{k}_exceeds_distinct"].sum()) for k in k_grid},
            "n_events_where_k_exceeds_n_prints": {
                f"k{k}": int(pooled[f"k{k}_exceeds_n"].sum()) for k in k_grid},
            "reading": "Where k exceeds the number of DISTINCT timestamps, a zero-span block is "
                       "possible in the as_is variant and the floored rate becomes the peak. That "
                       "is precisely what the collapse_same_timestamp variant removes, and why "
                       "both variants are run (T1c).",
        },
        "source": "research/phase_10/v2_t0d_ties.py:main",
        "artifact": f"{cfg['paths']['out_artifacts']}{OUT}",
    }
    write_json(os.path.join(out_dir, OUT_SUMMARY), summary)

    p = summary["pooled_analysis_cohort"]
    print(f"pooled n={p['n_events']} prints={p['n_prints_total']:,}")
    print(f"  tied-with-prev overall: {p['n_tied_with_prev_total']:,} = {p['share_tied_overall']:.4f}")
    print(f"  per-event share tied: median {p['share_tied_per_event']['q50']:.4f} "
          f"(q25 {p['share_tied_per_event']['q25']:.4f} / q75 {p['share_tied_per_event']['q75']:.4f}, "
          f"max {p['share_tied_per_event']['q100']:.4f})")
    print(f"  max tie run: median {p['max_tie_run']['q50']:.0f}, max {p['max_tie_run']['q100']:.0f}")
    print(f"  min non-zero gap (ns): min {res['min_ns_observed']}, median {res['median_min_gap_ns']:,.0f}")
    print(f"  k > distinct timestamps: {summary['estimator_consequence']['n_events_where_k_exceeds_distinct_timestamps']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
