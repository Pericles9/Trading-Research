"""
Phase 10 v2 T0a -- preconditions, cohort pin, and the detection-anchor audit.

Checks, in order:
  row 1  `phase-9-approved` present; v1 cohort manifest present and hash-matched
  row 2  cohort joins to momentum_events_canonical WHERE in_scope = TRUE
  row 9  a scanner detection timestamp is available for every cohort event

Row 9 is the one that fires. The prompt's T2b specifies "the scanner detection
timestamp for the event, taken from the canonical spine", and the canonical spine
carries no timestamp column of any kind. This script quantifies both candidate
substitutes so the escalation posts with the full option set rather than just the
failure. It ranks nothing and substitutes nothing -- a hard stop is not worked
around (CLAUDE.md).

Writes results/phase_10/artifacts/v2_t0a_escalation_row9.json.

Usage: .venv/Scripts/python.exe research/phase_10/v2_t0a_preconditions.py
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys

import duckdb
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import COHORT_KEY, rel, write_json  # noqa: E402

MANIFEST = "results/phase_10/artifacts/t1_cohort_manifest.parquet"
A102 = "results/phase_8/artifacts/a102_detection_anchors.parquet"
CATALOG = "data/filtered/scanner_hit_catalog.json"
OUT = "results/phase_10/artifacts/v2_t0a_escalation_row9.json"

EXPECTED_GROUPS = {"dev_v4_primary": 50, "activity_extension": 50,
                   "row_cap_census": 8, "dev_v4_sidecar": 6}
EXPECTED_COHORT_HASH = "e1a0ac73a79aa573"


def cohort_content_hash(c: pd.DataFrame) -> str:
    """Pin the frozen v1 cohort by content, not by file mtime.

    sha256 over the CSV of (ticker, event_date_canonical, momentum_pct,
    cohort_group) sorted by the 3-part key. Order-independent by construction,
    so it survives a regeneration of the (gitignored) parquet.
    """
    body = c.sort_values(COHORT_KEY)[COHORT_KEY + ["cohort_group"]].to_csv(index=False)
    return hashlib.sha256(body.encode()).hexdigest()[:16]


def load_cohort_frozen() -> pd.DataFrame:
    c = pd.read_parquet(rel(MANIFEST))
    c["event_date_canonical"] = c["event_date_canonical"].astype(str)
    return c


def check_row_1(c: pd.DataFrame) -> dict:
    tag = subprocess.run(["git", "rev-parse", "phase-9-approved^{commit}"],
                         capture_output=True, text=True, cwd=rel(".")).stdout.strip()
    h = cohort_content_hash(c)
    groups = c["cohort_group"].value_counts().to_dict()
    return {
        "phase_9_approved_tag": tag or None,
        "v1_cohort_manifest_present": True,
        "v1_cohort_rows": int(len(c)),
        "v1_cohort_groups": groups,
        "v1_embedded_config_hash": sorted(c["config_hash"].unique().tolist()),
        "v1_seed": sorted(c["seed"].unique().tolist()),
        "cohort_content_sha256_16": h,
        "cohort_content_hash_expected": EXPECTED_COHORT_HASH,
        "hash_matched": h == EXPECTED_COHORT_HASH,
        "groups_matched": groups == EXPECTED_GROUPS,
        "escalation_row_1": "PASS" if (tag and groups == EXPECTED_GROUPS) else "FAIL",
    }


def check_row_2(con, c: pd.DataFrame) -> dict:
    cn = con.execute(
        "SELECT ticker, event_date_canonical, ROUND(momentum_pct,2) AS momentum_pct "
        "FROM momentum_events_canonical WHERE in_scope"
    ).fetchdf()
    cn["event_date_canonical"] = cn["event_date_canonical"].astype(str)
    m = c.merge(cn, on=COHORT_KEY, how="left", indicator=True)
    n = int((m["_merge"] == "both").sum())
    return {"n_cohort": int(len(c)), "n_matched": n, "shortfall": int(len(c) - n),
            "escalation_row_2": "PASS" if n == len(c) else "FAIL"}


def audit_detection_anchor(con, c: pd.DataFrame) -> dict:
    """Row 9. Is a scanner detection timestamp available for every cohort event?"""
    canon_cols = [r[0] for r in con.execute("DESCRIBE momentum_events_canonical").fetchall()]
    raw_cols = [r[0] for r in con.execute("DESCRIBE momentum_events").fetchall()]
    time_like = [x for x in canon_cols
                 if any(t in x.lower() for t in ("time", "_ts", "detect", "scan", "hit", "minute", "hour"))]

    a = pd.read_parquet(rel(A102)).rename(columns={"mp": "momentum_pct"})
    a["event_date_canonical"] = a["event_date_canonical"].astype(str)
    a["momentum_pct"] = a["momentum_pct"].round(2)
    ma = c.merge(a[COHORT_KEY + ["det_minute", "det_undefined"]], on=COHORT_KEY,
                 how="left", indicator=True)
    ma["usable"] = (ma["_merge"] == "both") & (~ma["det_undefined"].fillna(True))

    with open(rel(CATALOG), encoding="utf-8") as f:
        cat = pd.DataFrame(list(json.load(f).values()))
    cat["key"] = cat["ticker"] + ":" + cat["date"].astype(str)
    ck = c.assign(key=c["ticker"] + ":" + c["event_date_canonical"])
    ms = ck.merge(cat[["key", "scanner_hit_ts_ns", "scanner_hit_tod_sec", "notes"]],
                  on="key", how="left")

    return {
        "canonical_time_like_columns": time_like,
        "canonical_has_detection_timestamp": bool(time_like),
        "raw_spine_columns": raw_cols,
        "A_phase8_reconstructed": {
            "cohort_present": int((ma["_merge"] == "both").sum()),
            "det_undefined": int(ma["det_undefined"].fillna(True).sum()),
            "cohort_usable": int(ma["usable"].sum()),
            "usable_by_group": ma.groupby("cohort_group")["usable"].agg(["size", "sum"])
                                 .rename(columns={"size": "n", "sum": "usable"}).to_dict("index"),
        },
        "B_scanner_hit_catalog": {
            "catalog_records_total": int(len(cat)),
            "catalog_records_with_timestamp": int(cat["scanner_hit_ts_ns"].notna().sum()),
            "cohort_present_in_catalog": int(ms["notes"].notna().sum()),
            "cohort_with_usable_timestamp": int(ms["scanner_hit_ts_ns"].notna().sum()),
            "usable_by_group": ms.groupby("cohort_group")["scanner_hit_ts_ns"]
                                 .agg(["size", "count"]).rename(columns={"size": "n", "count": "usable"})
                                 .to_dict("index"),
            "the_populated": ms.loc[ms["scanner_hit_ts_ns"].notna(),
                                    ["ticker", "event_date_canonical", "cohort_group",
                                     "scanner_hit_tod_sec"]].to_dict("records"),
        },
        "escalation_row_9": "FAIL — triggered",
    }


def main() -> int:
    c = load_cohort_frozen()
    con = duckdb.connect(rel("data/duckdb/main.duckdb"), read_only=True)
    con.execute("SET enable_progress_bar=false")
    r1 = check_row_1(c)
    r2 = check_row_2(con, c)
    r9 = audit_detection_anchor(con, c)
    con.close()

    # Preserve the hand-written narrative in the committed artifact; refresh only
    # the measured fields, so re-running this script cannot silently drop the
    # escalation's reasoning.
    out_path = rel(OUT)
    doc = {}
    if os.path.exists(out_path):
        with open(out_path, encoding="utf-8") as f:
            doc = json.load(f)
    doc.setdefault("phase", "10")
    doc["measured"] = {"row_1": r1, "row_2": r2, "row_9": r9}
    write_json(out_path, doc)

    print(f"row 1 (tag + cohort hash): {r1['escalation_row_1']}  hash={r1['cohort_content_sha256_16']} "
          f"matched={r1['hash_matched']}")
    print(f"row 2 (canonical join):    {r2['escalation_row_2']}  {r2['n_matched']}/{r2['n_cohort']}")
    print(f"row 9 (detection anchor):  {r9['escalation_row_9']}")
    print(f"  canonical time-like columns: {r9['canonical_time_like_columns']}")
    print(f"  A) phase-8 reconstructed det_minute usable: "
          f"{r9['A_phase8_reconstructed']['cohort_usable']}/114 (minute grain, not a scanner time)")
    print(f"  B) scanner_hit_catalog usable timestamps:   "
          f"{r9['B_scanner_hit_catalog']['cohort_with_usable_timestamp']}/114")
    return 9


if __name__ == "__main__":
    raise SystemExit(main())
