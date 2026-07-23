"""
Phase 5a T3 - draw the v4 primary cohort (50 events, 5 per momentum_pct
decile, clean file1 frame, seed 42).

Sampling algorithm is copied verbatim from research/phase_3/build_dev_sample_v3.py
lines 63-73 (the v3 draw), cited in config/phase_5a.json's
primary_cohort.method_source. v3's logic is inline in main(), not
factored into an importable function, so it is replicated here exactly
(same pd.qcut call, same np.random.default_rng(seed).choice loop in the
same sorted-decile iteration order) rather than reimplemented from
memory - not escalation row 2 (the source IS located and cited).
"""
import json

import numpy as np
import pandas as pd

PHASE_5A_CONFIG = "config/phase_5a.json"
FRAME_PARQUET = "results/phase_5a/artifacts/sampling_frame.parquet"
OUT_PARQUET = "results/phase_5a/artifacts/dev_v4_primary_events.parquet"
OUT_SUMMARY = "results/phase_5a/artifacts/t3_primary_draw_summary.json"


def draw(eligible: pd.DataFrame, seed: int, n_deciles: int, per_decile: int) -> pd.DataFrame:
    """Verbatim replica of research/phase_3/build_dev_sample_v3.py:main lines 63-73."""
    eligible = eligible.copy()
    eligible["decile"] = pd.qcut(eligible["momentum_pct"], n_deciles, labels=False, duplicates="drop")
    rng = np.random.default_rng(seed)
    sampled_parts = []
    for d in sorted(eligible["decile"].unique()):
        pool = eligible[eligible["decile"] == d]
        take = min(per_decile, len(pool))
        idx = rng.choice(pool.index, size=take, replace=False)
        sampled_parts.append(pool.loc[idx])
    sample = pd.concat(sampled_parts).sort_values(["decile", "ticker", "event_date_canonical"]).reset_index(drop=True)
    return sample


def main():
    with open(PHASE_5A_CONFIG) as f:
        cfg = json.load(f)
    seed = cfg["seed"]
    n_deciles = cfg["primary_cohort"]["n_deciles"]
    per_decile = cfg["primary_cohort"]["per_decile"]

    frame = pd.read_parquet(FRAME_PARQUET)
    eligible = frame[frame["clean_window"] == True].copy()  # noqa: E712
    n_eligible = len(eligible)
    print(f"eligible (clean file1) population: {n_eligible}")

    # T3a - draw twice, verify byte-identical
    sample1 = draw(eligible, seed, n_deciles, per_decile)
    sample2 = draw(eligible, seed, n_deciles, per_decile)
    reproducible = sample1.equals(sample2)
    print(f"reproducibility check (draw run twice): identical={reproducible}")

    sample = sample1
    n_sample = len(sample)
    decile_counts = sample.groupby("decile").size().to_dict()
    n_deciles_available = int(eligible["decile"].nunique()) if "decile" in eligible.columns else None

    # escalation row 4 - any decile with < 5 clean events available to draw from
    eligible_deciled = eligible.copy()
    eligible_deciled["decile"] = pd.qcut(eligible_deciled["momentum_pct"], n_deciles, labels=False, duplicates="drop")
    pool_sizes = eligible_deciled.groupby("decile").size().to_dict()
    min_pool = min(pool_sizes.values())
    row4_triggered = min_pool < per_decile

    sample["dev_cohort"] = "primary"
    sample.to_parquet(OUT_PARQUET, index=False)

    summary = {
        "phase": "5a", "task": "T3",
        "n_eligible_population": n_eligible,
        "n_deciles_configured": n_deciles,
        "n_deciles_realized": len(pool_sizes),
        "decile_pool_sizes": {str(k): int(v) for k, v in pool_sizes.items()},
        "n_sample": n_sample,
        "decile_sample_counts": {str(k): int(v) for k, v in decile_counts.items()},
        "reproducibility_check": {"pass": reproducible, "n_diff_rows": 0 if reproducible else int((sample1 != sample2).any(axis=1).sum())},
        "escalation_row3_triggered": not reproducible,
        "escalation_row4_triggered": row4_triggered,
        "escalation_row4_min_pool_size": min_pool,
        "method_source": "research/phase_3/build_dev_sample_v3.py:main (lines 63-73), replicated verbatim in research/phase_5a/t3_draw_primary.py:draw",
        "source": "research/phase_5a/t3_draw_primary.py:main",
        "artifact": OUT_PARQUET,
    }
    with open(OUT_SUMMARY, "w") as f:
        json.dump(summary, f, indent=2, default=str)
    print(json.dumps(summary, indent=2, default=str))

    if not reproducible:
        print("\n*** ESCALATION row 3: draw not reproducible - HARD STOP ***")
    if row4_triggered:
        print(f"\n*** ESCALATION row 4: decile pool size {min_pool} < {per_decile} - HARD STOP ***")


if __name__ == "__main__":
    main()
