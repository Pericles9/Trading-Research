#!/usr/bin/env python
"""T4 -- full-tier noise-band precheck, BEFORE authorising any full-tier ISO-share read.

Why this runs before T5, not after. T3's dev-tier controls (n=49) failed because the
median-of-a-heavy-tailed-distribution statistic has enormous sampling variance at small n --
diagnosed post-hoc, which is itself the process gap this task closes. The fix is not a
different statistic (that would be tuning until something fires, exactly what the Control
Standard exists to prevent); it is running the SAME negative control at the sample size T5
would actually use, BEFORE spending the per-event `conditions` read budget T5 requires
(there is no DuckDB shortcut for that column -- T0's finding -- so T5 is not free the way
this precheck is).

WHAT MAKES THIS FREE. results/phase_8/artifacts/a102_detection_markout_grid.parquet already
carries the FULL ~15,300-event candidate universe at every (latency, horizon) cell -- confirmed
live below, not assumed. No new tick pass, no new per-event file read, no full-tier DuckDB
query. This is a bootstrap over an already-committed, already-full-tier artifact.

METHOD. For each horizon at latency=5 (Sec 1's fixed entry anchor), draw `reps` random
50/50 splits of the real event population (no iso_share involved -- this is what full-tier
random noise looks like, not what full-tier ISO share looks like), compute the difference of
group medians in bp each time, and report the resulting empirical distribution against
Sec 1's required-separation table. This is T3a's negative control, re-run at the sample size
T5 would use, as a design input rather than a post-hoc diagnosis.

Usage: .venv/Scripts/python.exe research/iso_share_hold_length/t4_bootstrap_precheck.py
"""
from __future__ import annotations

import json
import os

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
OUT = os.path.join(REPO, "results", "iso_share_hold_length", "artifacts", "t4_bootstrap_precheck.json")

LATENCY = 5
HORIZONS = ["det+15", "det+30", "det+60", "t0_close", "t1_close", "t3_close"]
REQUIRED_SEPARATION_BP = {  # Sec 1 of the prompt, latency=5 -- identical to T3's table
    "det+15": 133.9, "det+30": 200.5, "det+60": 260.7,
    "t0_close": 320.5, "t1_close": 646.1, "t3_close": 861.8,
}
REPS = 5000
SEED = 20260913


def bootstrap_null_separation(markout_bp: np.ndarray, reps: int, seed: int) -> np.ndarray:
    """reps random 50/50 splits (no relationship to any covariate) -> array of
    |median(high) - median(low)| in bp, the empirical null this phase's split-and-compare
    procedure would produce on pure noise at this exact n."""
    rng = np.random.default_rng(seed)
    n = len(markout_bp)
    half = n // 2
    out = np.empty(reps, dtype=np.float64)
    for i in range(reps):
        idx = rng.permutation(n)
        hi = markout_bp[idx[:half]]
        lo = markout_bp[idx[half:]]
        out[i] = np.median(hi) - np.median(lo)
    return out


def main() -> int:
    g = pd.read_parquet(os.path.join(
        REPO, "results", "phase_8", "artifacts", "a102_detection_markout_grid.parquet"))
    g = g[(g.latency == LATENCY) & (g.horizon.isin(HORIZONS))].copy()

    results = {}
    for h in HORIZONS:
        sub = g[g.horizon == h]
        mk_bp = (sub["markout"].dropna().to_numpy()) * 10000.0
        n = len(mk_bp)
        null_sep = bootstrap_null_separation(mk_bp, REPS, SEED + hash(h) % 10_000)
        abs_null = np.abs(null_sep)
        req = REQUIRED_SEPARATION_BP[h]
        results[h] = {
            "n_events": int(n),
            "median_markout_bp": float(np.median(mk_bp)),
            "iqr_bp": [float(np.percentile(mk_bp, 25)), float(np.percentile(mk_bp, 75))],
            "required_separation_bp": req,
            "null_separation_abs_pctiles_bp": {
                "p50": float(np.percentile(abs_null, 50)),
                "p90": float(np.percentile(abs_null, 90)),
                "p95": float(np.percentile(abs_null, 95)),
                "p99": float(np.percentile(abs_null, 99)),
                "max": float(abs_null.max()),
            },
            "null_separation_std_bp": float(null_sep.std()),
            "p_null_exceeds_required": float((abs_null >= req).mean()),
            "sigma_multiples_of_required_over_null_std": float(req / null_sep.std()),
        }

    # Same precheck at dev-tier n (49), for direct comparison to what T3 actually saw --
    # sanity check that this bootstrap reproduces the magnitude T3's real controls found.
    iso = pd.read_parquet(os.path.join(
        REPO, "results", "iso_share_hold_length", "artifacts", "t2_iso_share.parquet"))
    dev_keys = iso[iso.status == "ok"][["ticker", "event_date", "momentum_pct"]].copy()
    dev_keys["event_date"] = pd.to_datetime(dev_keys["event_date"])
    g2 = g.rename(columns={"mp": "momentum_pct"})
    dev_check = {}
    for h in HORIZONS:
        sub = g2[g2.horizon == h].merge(
            dev_keys, left_on=["ticker", "event_date_canonical", "momentum_pct"],
            right_on=["ticker", "event_date", "momentum_pct"], how="inner")
        mk_bp = sub["markout"].dropna().to_numpy() * 10000.0
        null_sep = bootstrap_null_separation(mk_bp, REPS, SEED + hash(h) % 10_000)
        dev_check[h] = {
            "n_events": int(len(mk_bp)),
            "null_separation_abs_p95_bp": float(np.percentile(np.abs(null_sep), 95)),
            "null_separation_abs_max_bp": float(np.abs(null_sep).max()),
        }

    out = {
        "task": ("T4 -- full-tier noise-band precheck, read-only against the already-committed "
                 "full-universe markout grid, zero new tick reads"),
        "grid_source": "results/phase_8/artifacts/a102_detection_markout_grid.parquet",
        "latency_minutes": LATENCY,
        "bootstrap_reps": REPS,
        "bootstrap_seed_base": SEED,
        "split": "50/50 random, no covariate -- the pure-noise null a real split-and-compare would see",
        "full_tier": results,
        "dev_tier_49_sanity_check": {
            "note": ("reproduces T3's actual negative-control finding as a sanity check on this "
                     "bootstrap's methodology -- compare null_separation_abs_max_bp here to T3's "
                     "reported 2257.6 bp max"),
            "by_horizon": dev_check,
        },
        "source": "research/iso_share_hold_length/t4_bootstrap_precheck.py:main",
        "reproduce": ".venv/Scripts/python.exe research/iso_share_hold_length/t4_bootstrap_precheck.py",
    }
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=2, default=str)

    print(f"{'horizon':>10} {'n':>7} {'required_bp':>12} {'null_p95_bp':>12} {'null_max_bp':>12} "
          f"{'req/null_std':>13} {'P(null>=req)':>13}")
    for h in HORIZONS:
        r = results[h]
        print(f"{h:>10} {r['n_events']:>7} {r['required_separation_bp']:>12.1f} "
              f"{r['null_separation_abs_pctiles_bp']['p95']:>12.1f} "
              f"{r['null_separation_abs_pctiles_bp']['max']:>12.1f} "
              f"{r['sigma_multiples_of_required_over_null_std']:>13.2f} "
              f"{r['p_null_exceeds_required']:>13.4f}")
    print("\ndev-tier (n=49) sanity check vs T3's actual finding:")
    for h in HORIZONS:
        d = dev_check[h]
        print(f"  {h:>10} n={d['n_events']:>3}  null p95={d['null_separation_abs_p95_bp']:>8.1f} bp  "
              f"null max={d['null_separation_abs_max_bp']:>8.1f} bp")
    print(f"\nwrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
