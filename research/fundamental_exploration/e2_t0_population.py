"""
E2-T0: population, membership, coverage. D1 = in_scope = TRUE AND source_file = 'file1',
n = 15,763.

source_file is NOT a stored column -- src/data/canonical.py computes it on the fly inside
momentum_events_canonical's view (CASE WHEN me.date IS NOT NULL THEN 'file1' WHEN
me.event_date IS NOT NULL THEN 'file2' END), and a live COUNT(*) filtering on it joins
filtered_trades/filtered_quotes (pathologically slow, same class as E1-T0's finding). D1's
own citation artifact, results/phase_5a/artifacts/sampling_frame.parquet, already IS the
D1 population (confirmed directly: 15,763 rows, source_file=='file1' on all of them) --
used here instead of a live view scan, per prompts/fundamental_exploration_e2.md SS8.

event_fundamentals.parquet (20,951 rows) has no source_file column -- it's the FULL
in-scope population (file1 + file2 mixed). D1's subset is recovered by joining on event_id
(reused from research/fundamental_exploration/common.py, not re-derived) against
sampling_frame.parquet's own (ticker, event_date_canonical, momentum_pct).

Coverage by group by year is NOT literally carried forward from E1 (E1's numbers are for
the full 20,951-event population, a different, larger population than D1) -- recomputed
here, restricted to D1, reusing E1-T2's own coverage definition ({group}_quality !=
'unavailable') rather than inventing a new one.

Usage: .venv/Scripts/python.exe research/fundamental_exploration/e2_t0_population.py
"""
from __future__ import annotations

import json
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from research.fundamental_exploration import common as C  # noqa: E402

CFG = C.load_cfg(C.CFG_E2)
TARGET_ROW_COUNT = CFG["universe"]["target_row_count"]
SAMPLING_FRAME_PATH = CFG["universe"]["materialization_path"]
GROUPS = ["flg", "shs", "si", "spl"]


def main() -> int:
    frame = pd.read_parquet(SAMPLING_FRAME_PATH)
    checks = []

    checks.append({
        "name": "d1_row_count_and_source_file",
        "pass": bool(len(frame) == TARGET_ROW_COUNT and (frame["source_file"] == "file1").all()),
        "n_rows": len(frame), "expected": TARGET_ROW_COUNT,
        "n_source_file_file1": int((frame["source_file"] == "file1").sum()),
    })

    frame_ids = set(frame.apply(C.event_id, axis=1))
    checks.append({
        "name": "d1_event_id_unique",
        "pass": len(frame_ids) == len(frame),
        "n_rows": len(frame), "n_unique": len(frame_ids),
    })

    ef = C.load_event_fundamentals()
    ef_ids = set(ef["event_id"])
    only_in_frame = frame_ids - ef_ids
    only_in_ef_d1 = ef_ids - frame_ids  # informational only -- ef spans file1+file2, a larger population
    d1_fundamentals = ef[ef["event_id"].isin(frame_ids)].copy()
    checks.append({
        "name": "d1_subset_of_event_fundamentals",
        "pass": not only_in_frame,
        "n_d1": len(frame_ids), "n_event_fundamentals_total": len(ef_ids),
        "n_d1_missing_from_event_fundamentals": len(only_in_frame),
        "n_matched": len(d1_fundamentals),
        "sample_missing": list(only_in_frame)[:5],
        "note": "checks D1 (sampling_frame.parquet) is fully contained in event_fundamentals -- "
                "event_fundamentals also carries file2 events (a larger population), so the reverse "
                "direction (event_fundamentals subset of D1) is not expected to hold and is not asserted.",
    })

    d1_fundamentals = C.add_identity_fields(d1_fundamentals)
    n_by_year = d1_fundamentals.groupby("year").size()
    cov_rows = []
    for g in GROUPS:
        covered = d1_fundamentals[f"{g}_quality"] != "unavailable"
        cov_by_year = covered.groupby(d1_fundamentals["year"]).sum()
        share = (cov_by_year / n_by_year).fillna(0)
        for year in n_by_year.index:
            cov_rows.append({
                "group": g, "year": year, "n_total": int(n_by_year[year]),
                "n_covered": int(cov_by_year.get(year, 0)), "coverage_share": float(share[year]),
            })
    cov_table = pd.DataFrame(cov_rows)
    cov_table.to_parquet(f"{C.ART_E2}/e2_t0_coverage_by_year.parquet", index=False)
    d1_fundamentals.to_parquet(f"{C.ART_E2}/e2_d1_fundamentals.parquet", index=False)

    n_fail = sum(1 for c in checks if not c["pass"])
    summary = {
        "task": "E2-T0 population, membership, coverage",
        "config_hash": C.cfg_hash(C.CFG_E2),
        "n_checks": len(checks), "n_fail": n_fail, "checks": checks,
        "n_by_year": n_by_year.to_dict(),
        "coverage_by_year": cov_rows,
    }
    C.write_json(f"{C.ART_E2}/e2_t0_population_summary.json", summary)
    print(json.dumps(summary, indent=2, default=str))
    return 1 if n_fail else 0


if __name__ == "__main__":
    raise SystemExit(main())
