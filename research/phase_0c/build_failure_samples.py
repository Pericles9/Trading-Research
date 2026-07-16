"""T3 - for each nonzero T2b failure class, sample up to 20 examples
(seed=42) with full event-row detail, expected folder name, and what
actually exists on disk for that ticker+date (directory listing only)."""
from __future__ import annotations

import json
import random
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SAMPLE_SIZE = 20
SEED = 42


def disk_listing_for_prefix(ticker: str, date: str) -> list[str]:
    filtered_dir = REPO_ROOT / "data" / "filtered"
    prefix = f"{ticker}_{date}_"
    return sorted(p.name for p in filtered_dir.iterdir() if p.name.startswith(prefix))


def main(out_path: str) -> None:
    detail = json.loads(
        (REPO_ROOT / "results" / "phase_0c" / "artifacts" / "join_reconciliation_detail.json").read_text(encoding="utf-8")
    )
    t2b_results = detail["t2b_results"]

    by_class: dict[str, list[dict]] = {}
    for r in t2b_results:
        by_class.setdefault(r["class"], []).append(r)

    samples = {}
    for cls, rows in by_class.items():
        rng = random.Random(SEED)
        chosen = rng.sample(rows, min(SAMPLE_SIZE, len(rows)))
        examples = []
        for ev in chosen:
            examples.append({
                "ticker": ev["ticker"],
                "date": ev["date"],
                "momentum_pct_full_precision": ev["momentum_pct"],
                "expected_folder": ev["expected_folder"],
                "disk_listing_matching_prefix": disk_listing_for_prefix(ev["ticker"], ev["date"]),
                "classified_reason": ev["class"],
            })
        samples[cls] = {
            "class_total_count": len(rows),
            "sampled_count": len(examples),
            "examples": examples,
        }

    out = REPO_ROOT / out_path
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(samples, indent=2), encoding="utf-8")
    print(json.dumps({k: {"class_total_count": v["class_total_count"], "sampled_count": v["sampled_count"]} for k, v in samples.items()}, indent=2))


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "results/phase_0c/artifacts/failure_samples.json"
    main(target)
