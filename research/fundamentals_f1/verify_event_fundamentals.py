#!/usr/bin/env python
"""
Build F1, F1-T5d: Verification Block for `event_fundamentals`, in the structured
drift-dict + exit-code + --json twin-output style of tools/verify_cited_paths.py /
tools/verify_claude_md_indices.py -- every assertion in prompts/fundamentals_f1.md SS5,
checked directly, not asserted in prose. READ-ONLY.

Usage:
    .venv/Scripts/python.exe research/fundamentals_f1/verify_event_fundamentals.py
    .venv/Scripts/python.exe research/fundamentals_f1/verify_event_fundamentals.py --json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys

import duckdb
import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from research.fundamentals_f1 import common as C  # noqa: E402
from research.fundamentals_f1 import t5_assemble as T5  # noqa: E402

QUALITY_ENUMS = C.load_cfg()["quality_enums"]
ACCEPTED_LIKE_COLS = [
    "flg_last_accepted_ns", "shs_accepted_ns", "shs_asof_ns", "fin_accepted_ns",
    "si_asof_ns", "spl_last_split_ns",
]


def check_row_count_and_uniqueness(df: pd.DataFrame) -> dict:
    ok_count = len(df) == C.TARGET_ROW_COUNT
    ok_unique = df["event_id"].is_unique
    return {
        "name": "row_count_and_uniqueness",
        "pass": bool(ok_count and ok_unique),
        "n_rows": len(df), "expected": C.TARGET_ROW_COUNT,
        "n_unique_event_id": int(df["event_id"].nunique()),
    }


def check_event_id_set_equality(df: pd.DataFrame) -> dict:
    universe = pd.read_parquet(C.UNIVERSE_MATERIALIZATION_PATH)
    # event_date_canonical is datetime64[ns] here (unlike t0_spine/ticker_identity, where it's
    # already a plain date string) -- str(Timestamp) renders "2021-01-28 00:00:00" and would
    # silently produce a wrong event_id (and a false 100%-mismatch) if not normalized first.
    universe = universe.copy()
    universe["event_date_canonical"] = universe["event_date_canonical"].dt.strftime("%Y-%m-%d")
    universe_ids = set(universe.apply(C.event_id, axis=1))
    table_ids = set(df["event_id"])
    only_in_universe = universe_ids - table_ids
    only_in_table = table_ids - universe_ids
    return {
        "name": "event_id_set_equality_vs_universe_materialization",
        "pass": not only_in_universe and not only_in_table,
        "n_universe": len(universe_ids), "n_table": len(table_ids),
        "n_only_in_universe": len(only_in_universe), "n_only_in_table": len(only_in_table),
        "sample_only_in_universe": list(only_in_universe)[:5],
        "sample_only_in_table": list(only_in_table)[:5],
    }


def check_t0_tier_counts(df: pd.DataFrame) -> dict:
    counts = df["t0_source"].value_counts().to_dict()
    total = sum(counts.values())
    ns_poll1 = counts.get("nanosecond_poll1", 0)
    return {
        "name": "t0_tier_counts",
        "pass": bool(total == C.TARGET_ROW_COUNT and ns_poll1 == 110),
        "counts": counts, "total": total, "nanosecond_poll1": ns_poll1, "expected_nanosecond_poll1": 110,
    }


def check_no_lookahead(df: pd.DataFrame) -> dict:
    violations = {}
    for col in ACCEPTED_LIKE_COLS:
        bad = df[df[col].notna() & (df[col] >= df["t0_ns"])]
        if len(bad):
            violations[col] = {"n": len(bad), "sample_event_ids": bad["event_id"].head(5).tolist()}
    return {"name": "no_lookahead_accepted_or_asof_ns", "pass": not violations, "violations": violations}


def check_quality_enums(df: pd.DataFrame) -> dict:
    col_to_enum = {
        "identity_quality": "identity_quality", "flg_quality": "flg_quality",
        "shs_quality": "shs_quality", "fin_quality": "fin_quality",
        "si_quality": "si_quality", "spl_quality": "spl_quality",
    }
    violations = {}
    for col, enum_key in col_to_enum.items():
        allowed = set(QUALITY_ENUMS[enum_key])
        seen = set(df[col].dropna().unique())
        bad = seen - allowed
        if bad:
            violations[col] = {"unexpected_values": sorted(bad), "allowed": sorted(allowed)}
    return {"name": "quality_enum_domains", "pass": not violations, "violations": violations}


def check_no_spine_numeric_leakage(df: pd.DataFrame) -> dict:
    con = C.connect(read_only=True)
    schema_rows = con.execute("DESCRIBE momentum_events_canonical").df()
    numeric_types = {"BIGINT", "DOUBLE", "INTEGER", "FLOAT", "HUGEINT", "SMALLINT", "DECIMAL"}
    numeric_cols = set(
        schema_rows.loc[schema_rows["column_type"].str.upper().isin(numeric_types), "column_name"]
    ) - {"momentum_pct"}  # momentum_pct is the D4-exempted selection variable, not a leakage risk
    overlap = numeric_cols & set(df.columns)
    return {
        "name": "no_spine_numeric_column_leakage",
        "pass": not overlap,
        "momentum_events_canonical_numeric_cols_checked": len(numeric_cols),
        "overlap": sorted(overlap),
    }


def check_provenance_completeness(df: pd.DataFrame) -> dict:
    pairs = [
        ("flg_last_form", "flg_last_accession"), ("shs_shares_outstanding", "shs_accession"),
        ("fin_revenue", "fin_accession"), ("si_shares_short", None),
        ("spl_last_split_ratio", None),
    ]
    violations = {}
    for value_col, accession_col in pairs:
        if accession_col is None:
            continue
        bad = df[df[value_col].notna() & df[accession_col].isna()]
        if len(bad):
            violations[value_col] = {"n": len(bad), "sample_event_ids": bad["event_id"].head(5).tolist()}
    return {"name": "provenance_completeness", "pass": not violations, "violations": violations,
            "note": "si_/spl_ groups have no per-observation accession in the vendor source; "
                    "not checked here, tracked as a known source-of-truth limitation."}


def check_fetch_manifests(sample_hash_cap: int = 50_000, seed: int = 42) -> dict:
    # cap is a safety valve, not a real sampling limit -- re-hashing the full 23,480-file
    # archive took 5s when measured directly (2026-09-12), so "every file" (SS5's own
    # wording) is checked in full, not sampled, at this archive's current size.
    massive_root = "data/raw/fundamentals/massive/2026-09-12"
    massive_manifest_path = f"{massive_root}/fetch_manifest.json"
    checksums_path = f"{massive_root}/checksums.json"
    result = {"name": "fetch_manifest_checksums", "manifests_checked": [], "violations": {}}
    if not os.path.exists(massive_manifest_path):
        result["pass"] = False
        result["violations"]["massive"] = "manifest file missing"
        return result
    with open(massive_manifest_path) as f:
        manifest = json.load(f)
    bad_files = {}
    for source, info in manifest["sources"].items():
        d = f"{massive_root}/{source}"
        if not os.path.isdir(d):
            bad_files[source] = "directory missing"
            continue
        files = os.listdir(d)
        if len(files) != info["n_ciks_pulled"]:
            bad_files[source] = f"{len(files)} files on disk vs {info['n_ciks_pulled']} in manifest"
    result["manifests_checked"].append({"path": massive_manifest_path, "sources": list(manifest["sources"])})

    if not os.path.exists(checksums_path):
        bad_files["checksums.json"] = "missing -- checksums not verifiable"
    else:
        with open(checksums_path) as f:
            checksums = json.load(f)
        import random
        random.seed(seed)
        all_entries = [(s, fn, sha) for s, files in checksums.items() for fn, sha in files.items()]
        sample = random.sample(all_entries, min(sample_hash_cap, len(all_entries)))
        mismatches, missing = [], []
        for source, fn, expected_sha in sample:
            path = f"{massive_root}/{source}/{fn}"
            if not os.path.exists(path):
                missing.append(path)
                continue
            with open(path, "rb") as f:
                actual = hashlib.sha256(f.read()).hexdigest()
            if actual != expected_sha:
                mismatches.append(path)
        if mismatches or missing:
            bad_files["checksums.json"] = {"sampled": len(sample), "missing_files": missing, "sha_mismatches": mismatches}
        result["manifests_checked"].append({
            "path": checksums_path, "n_files_recorded": len(all_entries), "n_sampled_and_verified": len(sample),
        })
    result["violations"].update(bad_files)

    sec_manifests = [
        "data/raw/fundamentals/sec/2026-09-12/submissions_manifest.json",
        "data/raw/fundamentals/sec/2026-09-12/companyfacts_manifest.json",
    ]
    for p in sec_manifests:
        if os.path.exists(p):
            result["manifests_checked"].append({"path": p, "note": "existence-only; no per-file sha256 recorded (documented gap)"})
        else:
            result["violations"][p] = "manifest file missing"
    result["pass"] = not result["violations"]
    return result


def check_deterministic_rebuild() -> dict:
    a = T5.build()
    b = T5.build()
    identical = a.equals(b)
    return {"name": "deterministic_rebuild", "pass": bool(identical),
            "note": "event_fundamentals rebuilt twice in-process; pandas .equals() (values + dtypes)."}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    df = pd.read_parquet(f"{C.NORMALIZED_ROOT}/event_fundamentals.parquet")

    checks = [
        check_row_count_and_uniqueness(df),
        check_event_id_set_equality(df),
        check_t0_tier_counts(df),
        check_no_lookahead(df),
        check_quality_enums(df),
        check_no_spine_numeric_leakage(df),
        check_provenance_completeness(df),
        check_fetch_manifests(),
        check_deterministic_rebuild(),
    ]
    n_fail = sum(1 for c in checks if not c["pass"])
    out = {"task": "F1-T5d Verification Block", "n_checks": len(checks), "n_fail": n_fail, "checks": checks}

    if args.json:
        print(json.dumps(out, indent=2, default=str))
        return 1 if n_fail else 0

    print("=== F1-T5d Verification Block ===\n")
    for c in checks:
        status = "PASS" if c["pass"] else "FAIL"
        print(f"  [{status}] {c['name']}")
        if not c["pass"]:
            print(f"         {json.dumps({k: v for k, v in c.items() if k not in ('name', 'pass')}, default=str)[:500]}")
    print(f"\n{n_fail} of {len(checks)} checks failed" if n_fail else f"\nall {len(checks)} checks passed")
    return 1 if n_fail else 0


if __name__ == "__main__":
    raise SystemExit(main())
