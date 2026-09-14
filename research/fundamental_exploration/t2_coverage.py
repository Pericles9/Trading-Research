"""
E1-T2: coverage as a variable, not a filter. Coverage share per fundamental group, by
year. fin_ is excluded per SS1 (deferred, amendment F1-A1) -- flg/shs/si/spl only.

Brief's own check (prompts/fundamental_exploration_e1.md E1-T2): the SEC-sourced groups
(flg_, shs_) must NOT show the 2022-23 vendor coverage cliff, because EDGAR filings carry
no subscription gate. If they do, that's a build defect, not a property of the data --
this script computes the actual numbers and flags the comparison explicitly rather than
asserting the expected shape.

Coverage = share of events where {group}_quality != 'unavailable', matching
research/fundamentals_f1/chart_t6_coverage.py's own definition exactly (reuse, not a new
convention).

Usage: .venv/Scripts/python.exe research/fundamental_exploration/t2_coverage.py
"""
from __future__ import annotations

import json
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from research.fundamental_exploration import common as C  # noqa: E402

GROUPS = ["flg", "shs", "si", "spl"]
SEC_SOURCED = ["flg", "shs"]
VENDOR_SOURCED = ["si", "spl"]
CLIFF_YEARS = ["2022", "2023"]


def main() -> int:
    ef = C.load_event_fundamentals()
    ef = C.add_identity_fields(ef)

    n_by_year = ef.groupby("year").size()
    rows = []
    for g in GROUPS:
        covered = ef[f"{g}_quality"] != "unavailable"
        cov_by_year = covered.groupby(ef["year"]).sum()
        share = (cov_by_year / n_by_year).fillna(0)
        for year in n_by_year.index:
            rows.append({
                "group": g, "year": year, "n_total": int(n_by_year[year]),
                "n_covered": int(cov_by_year.get(year, 0)), "coverage_share": float(share[year]),
            })
    cov_table = pd.DataFrame(rows)
    cov_table.to_parquet(f"{C.ART}/t2_coverage_by_year.parquet", index=False)

    # The cliff check: for each SEC-sourced group, compare CLIFF_YEARS' coverage share
    # against the mean of every other year. Same comparison run on the vendor-sourced
    # groups as the "what a real cliff looks like" reference point.
    cliff_check = {}
    for g in GROUPS:
        g_rows = cov_table[cov_table["group"] == g].set_index("year")["coverage_share"]
        cliff_years_present = [y for y in CLIFF_YEARS if y in g_rows.index]
        other_years = g_rows.index.difference(cliff_years_present)
        cliff_mean = float(g_rows.loc[cliff_years_present].mean()) if cliff_years_present else None
        other_mean = float(g_rows.loc[other_years].mean()) if len(other_years) else None
        drop = (other_mean - cliff_mean) if (cliff_mean is not None and other_mean is not None) else None
        cliff_check[g] = {
            "cliff_years_coverage": {y: float(g_rows[y]) for y in cliff_years_present},
            "other_years_mean_coverage": other_mean,
            "drop_vs_other_years": drop,
            "source": "SEC (no subscription gate)" if g in SEC_SOURCED else "vendor",
        }

    sec_defect = any(
        (cliff_check[g]["drop_vs_other_years"] or 0) > 0.15 for g in SEC_SOURCED
        if cliff_check[g]["drop_vs_other_years"] is not None
    )

    # spl_quality (research/fundamentals_f1/t5_assemble.py:180-181) defaults to
    # "unavailable" and only flips to "observed" when spl_n_splits_365d > 0 or
    # spl_last_split_ratio is notna -- so a confirmed zero-splits-in-window event and a
    # genuinely unresolved one are BOTH labeled "unavailable". Not fixed here (F1 is a
    # closed, separately-verified build; research/ never edits it mid-exploration) --
    # cross-tabbed against identity_quality instead, since a resolved CIK makes
    # spl_n_splits_365d=0 a real observed zero rather than a true gap. Per the brief's
    # own SS3 rule: "unavailable and zero are different states and never collapsed".
    spl_vs_identity = pd.crosstab(ef["spl_quality"], ef["identity_quality"]).to_dict()
    spl_unavailable_resolved_identity = int(
        ((ef["spl_quality"] == "unavailable") & (ef["identity_quality"] != "unresolved")).sum()
    )
    spl_note = {
        "defect": "spl_quality conflates 'confirmed zero splits in the 365d window' with "
                  "'split history could not be resolved' -- both are labeled 'unavailable'. "
                  "Source: research/fundamentals_f1/t5_assemble.py:180-181.",
        "spl_quality_vs_identity_quality_crosstab": spl_vs_identity,
        "n_spl_unavailable_with_resolved_identity": spl_unavailable_resolved_identity,
        "n_spl_unavailable_with_resolved_identity_note": "of spl_quality=='unavailable' rows, "
            "this many have a resolved CIK -- for those, spl_n_splits_365d=0 is very likely a "
            "real confirmed zero, not a true data gap. Not asserted as certain: spl_flat's own "
            "source coverage for a resolved CIK is a separate question this crosstab cannot answer.",
    }

    summary = {
        "task": "E1-T2 coverage by year",
        "config_hash": C.cfg_hash(),
        "groups": GROUPS, "sec_sourced": SEC_SOURCED, "vendor_sourced": VENDOR_SOURCED,
        "cliff_check": cliff_check,
        "sec_shows_cliff_defect": sec_defect,
        "spl_quality_semantics": spl_note,
        "n_by_year": n_by_year.to_dict(),
    }
    C.write_json(f"{C.ART}/t2_coverage_summary.json", summary)
    print(json.dumps(summary, indent=2, default=str))
    return 1 if sec_defect else 0


if __name__ == "__main__":
    raise SystemExit(main())
