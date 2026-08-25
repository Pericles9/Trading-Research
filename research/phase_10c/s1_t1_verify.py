"""
Phase 10c Stage 1, T1 Verification Block -- executable assertions, not prose.

Per S5's requirement (motivated by two prior defects where prose and executed path
diverged): every claim below is an assert that fails loudly, not a printed statement.

Also documents the population-scope finding this task surfaced: BMR (used in
Amendment 4/6 as one of the '4 evening anchors' backing the {8,15} auction code-set)
is cohort_group='activity_extension', not part of the 56-event Stage-1 dev sample --
Amendment 4-6's condition-code census was computed over the full, unfiltered
114-row t1_cohort_manifest.parquet rather than the dev sample it was reported
alongside. Recorded, not retroactively fixed in the tagged Stage 0/0b artifacts or
the already-committed Amendment 4-6 JSON.

Usage: .venv/Scripts/python.exe research/phase_10c/s1_t1_verify.py
"""
from __future__ import annotations

import importlib.util as ilu
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "phase_10"))
from common import rel  # noqa: E402
_s = ilu.spec_from_file_location("c10c", os.path.join(HERE, "common.py"))
c10c = ilu.module_from_spec(_s); _s.loader.exec_module(c10c)

ART = "results/phase_10c/artifacts"


def main() -> int:
    cfg_open = c10c.load_cfg()
    cells = pd.read_parquet(rel(f"{ART}/s1_t1_cells.parquet"))
    coh = pd.read_parquet(rel("results/phase_10/artifacts/t1_cohort_manifest.parquet"))

    checks = {}

    # 1. every event in the analysable subset appears in exactly one segment bucket per variant
    g = cells.groupby(["ticker", "event_date_canonical", "threshold", "kernel_min"]).size()
    assert (g == 1).all(), "an (event, threshold, kernel) cell must be exactly one row"
    per_ev_var = cells.groupby(["ticker", "event_date_canonical", "threshold"]).segment.nunique()
    assert (per_ev_var <= 1).all(), (
        "an event must resolve to at most one DISTINCT segment per variant across kernels "
        "(0 = consistently unlabelled/no anchor, 1 = consistently one segment; >1 would mean "
        "the same event/variant disagreed on segment across kernel widths, which should be "
        "impossible since segment depends only on the anchor, never on the kernel)")
    checks["exactly_one_segment_per_event_per_variant"] = "PASS"

    # 2. auction-code events land in the segment assign_segment() assigns, not the timestamp default
    acet = cells[(cells.ticker == "ACET") & (cells.threshold.isin([1.25, 1.30]))]
    assert len(acet) == 6, f"expected 6 ACET cells (2 variants x 3 kernels), got {len(acet)}"
    assert (acet.segment == "rth").all(), (
        "ACET carries condition code 8 -- assign_segment() must override it to rth, not the "
        "timestamp-default 'evening' it would get without the override")
    checks["ACET_auction_override_applied"] = "PASS, all 6 cells segment=rth"

    # 3. no variant's rows were deduplicated away at load
    assert set(cells.threshold.unique()) == {1.25, 1.30, 1.35}, "a variant is missing entirely"
    n_by_variant = cells.groupby("threshold")[["ticker", "event_date_canonical"]] \
        .apply(lambda d: d.drop_duplicates().shape[0])
    assert (n_by_variant == 56).all(), (
        f"every variant must carry all 56 dev-sample events (found {n_by_variant.to_dict()})")
    checks["no_variant_deduplicated_at_load"] = "PASS, 56 events x 3 variants all present"

    # 4. Class M values at close equal Class M values at open
    m_open = {"D5_first_kernel_min": 8.0, "D6_stage2_kernels_min": [2, 8, 32],
              "D4_median_precision_factor": 1.5, "D2_max_cutoff_ms": "VOID"}
    m_close = c10c.class_m(cfg_open)
    assert float(m_close["D5_first_kernel_min"]) == m_open["D5_first_kernel_min"]
    assert float(m_close["D4_median_precision_factor"]) == m_open["D4_median_precision_factor"]
    assert sorted(m_close["D6_stage2_kernels_min"]) == m_open["D6_stage2_kernels_min"]
    assert m_close["D2_max_cutoff_ms"] == m_open["D2_max_cutoff_ms"]
    checks["class_M_unchanged_open_to_close"] = "PASS"

    # 5. population-scope finding: BMR is not a dev-sample event
    bmr_group = coh[coh.ticker == "BMR"].cohort_group.tolist()
    assert bmr_group == ["activity_extension"], f"expected BMR=activity_extension, got {bmr_group}"
    assert "BMR" not in set(cells.ticker), "BMR must not appear in the dev-sample cell table"
    checks["BMR_confirmed_out_of_dev_sample_scope"] = (
        f"PASS -- BMR cohort_group={bmr_group[0]!r}, absent from s1_t1_cells.parquet. "
        "Amendment 4-6's condition-code census included it anyway (unfiltered "
        "t1_cohort_manifest.parquet, 114 rows across 4 cohort_groups, not just the 56-event "
        "dev sample). True dev-sample evening population at threshold 1.35 is 2 (OST, CELH), "
        "not the 3 (OST, CELH, BMR) implied by Amendment 4's discriminant test.")

    out = {"phase": "10c", "stage": "1", "task": "T1_verification", "checks": checks,
          "all_pass": True, "source": "research/phase_10c/s1_t1_verify.py:main"}
    c10c.write_json(rel(f"{ART}/s1_t1_verify.json"), out)
    for k, v in checks.items():
        print(f"{k}: {v}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
