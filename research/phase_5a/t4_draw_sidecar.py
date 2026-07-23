"""
Phase 5a T4 - draw the flagged sidecar (6 events, from the 414 file1
flagged events, allocated across the most frequent combined bitmap
patterns). Never pooled with the primary cohort in any statistic
(config/phase_5a.json flagged_sidecar.pooled_with_primary=false).
"""
import json

import numpy as np
import pandas as pd

PHASE_5A_CONFIG = "config/phase_5a.json"
FRAME_PARQUET = "results/phase_5a/artifacts/sampling_frame.parquet"
OUT_PARQUET = "results/phase_5a/artifacts/dev_v4_sidecar_events.parquet"
OUT_SUMMARY = "results/phase_5a/artifacts/t4_sidecar_draw_summary.json"


def draw(flagged: pd.DataFrame, seed: int, n_events: int) -> pd.DataFrame:
    flagged = flagged.copy()
    flagged["pattern"] = flagged["trades_bitmap"] + "|" + flagged["quotes_bitmap"]
    pattern_counts = flagged["pattern"].value_counts()
    ranked_patterns = pattern_counts.index.tolist()  # descending frequency; pandas value_counts is stable-sorted

    rng = np.random.default_rng(seed)
    top_n = ranked_patterns[:n_events]
    slots = list(top_n)
    if len(top_n) < n_events:
        # fewer than n_events distinct patterns: remaining slots go to the top pattern
        slots += [ranked_patterns[0]] * (n_events - len(top_n))

    drawn_rows = []
    used_index_by_pattern = {}
    for pattern in slots:
        pool = flagged[flagged["pattern"] == pattern]
        already_used = used_index_by_pattern.get(pattern, [])
        pool = pool[~pool.index.isin(already_used)]
        idx = rng.choice(pool.index, size=1, replace=False)
        drawn_rows.append(pool.loc[idx])
        used_index_by_pattern.setdefault(pattern, []).extend(list(idx))

    sample = pd.concat(drawn_rows).reset_index(drop=True)
    return sample, pattern_counts


def main():
    with open(PHASE_5A_CONFIG) as f:
        cfg = json.load(f)
    seed = cfg["seed"]
    n_events = cfg["flagged_sidecar"]["n_events"]

    frame = pd.read_parquet(FRAME_PARQUET)
    flagged = frame[frame["clean_window"] == False].copy()  # noqa: E712
    n_flagged = len(flagged)
    print(f"flagged (file1) population: {n_flagged}")

    sample1, pattern_counts = draw(flagged, seed, n_events)
    sample2, _ = draw(flagged, seed, n_events)
    reproducible = sample1.equals(sample2)
    print(f"reproducibility check (draw run twice): identical={reproducible}")

    sample = sample1
    sample["dev_cohort"] = "flagged_sidecar"
    sample.to_parquet(OUT_PARQUET, index=False)

    n_distinct_patterns = len(pattern_counts)
    top6 = pattern_counts.head(6).to_dict()

    summary = {
        "phase": "5a", "task": "T4",
        "n_flagged_population": n_flagged,
        "n_distinct_patterns": n_distinct_patterns,
        "top_patterns_by_frequency": {k: int(v) for k, v in top6.items()},
        "n_sidecar": len(sample),
        "sidecar_events": sample[["ticker", "event_date_canonical", "momentum_pct", "pattern"]].to_dict(orient="records"),
        "reproducibility_check": {"pass": reproducible},
        "escalation_row3_triggered": not reproducible,
        "source": "research/phase_5a/t4_draw_sidecar.py:main",
        "artifact": OUT_PARQUET,
    }
    with open(OUT_SUMMARY, "w") as f:
        json.dump(summary, f, indent=2, default=str)
    print(json.dumps(summary, indent=2, default=str))

    if not reproducible:
        print("\n*** ESCALATION row 3: draw not reproducible - HARD STOP ***")


if __name__ == "__main__":
    main()
