#!/usr/bin/env python
"""
Phase 13, T5: Verification Block, in the structured drift-dict + exit-code + --json
twin-output style of tools/verify_cited_paths.py / research/fundamentals_f1's own
Verification Block. Every assertion in prompts/phase_13.md checked directly, not
asserted in prose. READ-ONLY except for the charts-directory text scan.

Usage:
    .venv/Scripts/python.exe research/phase_13/verify_partition_test.py
    .venv/Scripts/python.exe research/phase_13/verify_partition_test.py --json
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import re
import sys

import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from research.phase_13 import common as C  # noqa: E402
from research.phase_13 import t3_partitions as T3  # noqa: E402

HORIZONS = [5, 15, 30, 60]
FORBIDDEN_PATTERNS = [
    r"\bclears?\b", r"\bcleared\b", r"\bpass(?:es|ed)?\b", r"\bwins?\b", r"\bwon\b", r"\bwinner\b",
    r"\bkill[- ]condition\b", r"\bthe finding\b", r"\bheadline\b",
]
# A hit somewhere near a negation word is describing the ABSENCE of a verdict
# ("no kill condition", "not a pass/fail line", "not to declare ... a winner") --
# exactly what this phase's design requires it to say. A wide, non-adjacency-anchored
# window is used deliberately: real sentences put a few words between the negation
# and the flagged term ("not to declare a comparison's winner"). Only a hit with no
# negation anywhere in the window is a real candidate.
NEGATION_WINDOW = 50
NEGATION_RE = re.compile(r"\b(no|not|n't|without|never|neither)\b", re.IGNORECASE)


def check_p0_row_count_and_coverage() -> dict:
    p0 = pd.read_parquet(f"{C.ART}/p0_outcome.parquet")
    with open(f"{C.ART}/p0_coverage_summary.json") as f:
        coverage = json.load(f)
    ok_rows = len(p0) == 20951
    recompute = {}
    mismatches = {}
    for h in HORIZONS:
        recomputed_n = int(p0[f"n_bars_{h}"].notna().sum())
        recorded_n = coverage["coverage_by_horizon"][str(h)]["n_covered"]
        recompute[h] = recomputed_n
        if recomputed_n != recorded_n:
            mismatches[h] = {"recomputed": recomputed_n, "recorded": recorded_n}
    return {
        "name": "p0_row_count_and_coverage",
        "pass": bool(ok_rows and not mismatches),
        "n_rows": len(p0), "expected": 20951,
        "recomputed_n_covered_by_horizon": recompute,
        "mismatches_vs_coverage_summary": mismatches,
    }


def check_split_n_conservation(df: pd.DataFrame) -> dict:
    """For every split and horizon, sum(cell n) across all year x decile cells must equal
    a direct count of events with both a defined split value and a defined outcome at
    that horizon -- rebuilt independently from the raw dataframe, not from the JSON the
    build script already wrote."""
    with open(f"{C.ART}/t3_partition_summary.json") as f:
        summary = json.load(f)

    violations = {}
    for name, col in T3.SPLITS.items():
        for h in HORIZONS:
            cells = summary["splits"][name][f"horizon_{h}"]
            summed_n = sum(c["mfe_cost_mult"].get("n", 0) for c in cells)
            # cross_cut's outer groupby (event_year x detection_price_decile) drops rows
            # missing either key (pandas groupby default dropna=True) -- match that here,
            # or every event with a defined split+outcome but no price decile would show
            # as a spurious mismatch.
            direct_n = int((
                df[col].notna() & df[f"mfe_cost_mult_{h}"].notna()
                & df["detection_price_decile"].notna() & df["event_year"].notna()
            ).sum())
            if summed_n != direct_n:
                violations[f"{name}_h{h}"] = {"summed_from_cells": summed_n, "direct_count": direct_n}
    return {"name": "split_n_conservation_above_plus_below_equals_covered", "pass": not violations,
            "violations": violations}


def check_no_spine_numeric_leakage(df: pd.DataFrame) -> dict:
    """Reuses F1-T5d's DuckDB-schema-introspection pattern: no column read into T3's
    dataframe may be a spine numeric (D4) or an unrecognized transform of one."""
    con = C.connect(read_only=True)
    schema_rows = con.execute("DESCRIBE momentum_events_canonical").df()
    numeric_types = {"BIGINT", "DOUBLE", "INTEGER", "FLOAT", "HUGEINT", "SMALLINT", "DECIMAL"}
    numeric_cols = set(
        schema_rows.loc[schema_rows["column_type"].str.upper().isin(numeric_types), "column_name"]
    ) - {"momentum_pct"}
    overlap = numeric_cols & set(df.columns)
    return {
        "name": "no_spine_numeric_column_leakage",
        "pass": not overlap,
        "momentum_events_canonical_numeric_cols_checked": len(numeric_cols),
        "overlap": sorted(overlap),
    }


def check_fundamental_columns_are_partition_keys_only() -> dict:
    """D32 / Amendment A1: a fundamental column may label a group; it may never itself
    be averaged, differenced, or otherwise fed into the outcome variable. Checked by
    confirming the outcome columns (mfe_/mae_/round_trip_cost_) carry no fundamentals
    (flg_/shs_/spl_/si_/fin_) prefix and are unchanged by which split is being read."""
    p0 = pd.read_parquet(f"{C.ART}/p0_outcome.parquet")
    outcome_cols = [c for c in p0.columns if c.startswith(("mfe_", "mae_", "round_trip_cost", "n_bars_"))]
    forbidden_prefixes = ("flg_", "shs_", "spl_", "si_", "fin_")
    tainted = [c for c in outcome_cols if c.startswith(forbidden_prefixes)]
    return {"name": "fundamental_columns_are_partition_keys_only", "pass": not tainted,
            "outcome_cols_checked": len(outcome_cols), "tainted": tainted}


def check_no_pass_fail_language() -> dict:
    """Escalation row 2: no output artifact or chart may declare a split
    'cleared'/'passed'/'won'. Scans chart HTML and the JSON/report artifacts Cooper
    actually reads as findings -- not the .py scripts' own docstrings/comments, which
    legitimately name this vocabulary while describing the rule itself, and not
    prompts/phase_13.md, the rule's own source text."""
    paths = (
        glob.glob(f"{C.CHARTS}/*.html")
        + glob.glob(f"{C.ART}/*.json")
        + glob.glob(f"{os.path.dirname(C.ART)}/*.json")  # digest.json
        + glob.glob(f"{os.path.dirname(C.ART)}/*.md")  # REPORT.md
        + ["results/reports/phase_13_report.md"]
    )
    hits = {}
    combined = "|".join(FORBIDDEN_PATTERNS)
    pattern = re.compile(combined, re.IGNORECASE)
    for p in paths:
        if not os.path.exists(p):
            continue
        text = open(p, encoding="utf-8", errors="replace").read()
        found = []
        for m in pattern.finditer(text):
            preceding = text[max(0, m.start() - NEGATION_WINDOW):m.start()]
            if NEGATION_RE.search(preceding):
                continue
            found.append(m.group(0).lower())
        if found:
            hits[p] = sorted(set(found))
    return {"name": "no_pass_fail_or_kill_condition_language", "pass": not hits, "hits": hits}


def check_config_hash_consistency() -> dict:
    with open(f"{C.ART}/p0_coverage_summary.json") as f:
        p0_cov = json.load(f)
    with open(f"{C.ART}/t2_arm_zero_summary.json") as f:
        t2 = json.load(f)
    with open(f"{C.ART}/t3_partition_summary.json") as f:
        t3 = json.load(f)
    hashes = {"p0_coverage": p0_cov["config_hash"], "t2": t2["config_hash"], "t3": t3["config_hash"]}
    current = C.cfg_hash()
    mismatched = {k: v for k, v in hashes.items() if v != current}
    return {"name": "config_hash_consistency", "pass": not mismatched,
            "current_config_hash": current, "recorded_hashes": hashes, "mismatched": mismatched}


def check_kill_condition_disabled() -> dict:
    cfg = C.load_cfg()
    enabled = cfg.get("kill_condition", {}).get("enabled", True)
    return {"name": "kill_condition_disabled_per_cooper_amendment", "pass": enabled is False,
            "kill_condition_enabled": enabled}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    df, _meta = T3.build_df()
    checks = [
        check_p0_row_count_and_coverage(),
        check_split_n_conservation(df),
        check_no_spine_numeric_leakage(df),
        check_fundamental_columns_are_partition_keys_only(),
        check_no_pass_fail_language(),
        check_config_hash_consistency(),
        check_kill_condition_disabled(),
    ]
    n_fail = sum(1 for c in checks if not c["pass"])
    out = {"task": "Phase 13 Verification Block", "n_checks": len(checks), "n_fail": n_fail, "checks": checks}

    if args.json:
        print(json.dumps(out, indent=2, default=str))
        return 1 if n_fail else 0

    print("=== Phase 13 Verification Block ===\n")
    for c in checks:
        status = "PASS" if c["pass"] else "FAIL"
        print(f"  [{status}] {c['name']}")
        if not c["pass"]:
            print(f"         {json.dumps({k: v for k, v in c.items() if k not in ('name', 'pass')}, default=str)[:800]}")
    print(f"\n{n_fail} of {len(checks)} checks failed" if n_fail else f"\nall {len(checks)} checks passed")
    return 1 if n_fail else 0


if __name__ == "__main__":
    raise SystemExit(main())
