"""T2 - bidirectional join reconciliation between momentum_events and
data/filtered/ folders.

T2a reproduces Phase 0b's eligibility check EXACTLY as it originally ran
(direct string construction f"{ticker}_{date}_{momentum_pct:.2f}" + both-
files existence check) - independent of T1's regex-classifier fix, since
Phase 0b's own logic never used regex parsing at all.

T2b classifies the resulting non-eligible events; T2c classifies every
T1 folder from the folders side. The 114 date_is_none folders are routed
to their own none_date_unresolved class in T2c, per Cooper's instruction -
never merged into matched/orphan/ambiguous.
"""
from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

import duckdb
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]


def t2a_reproduce_eligibility(con: duckdb.DuckDBPyConnection) -> tuple[list[dict], list[dict]]:
    """Exact reproduction of research/phase_0b/build_dev_sample.py's
    eligible_events(): direct string construction, both-files existence
    check. Returns (eligible, non_eligible) event dict lists."""
    filtered_dir = REPO_ROOT / "data" / "filtered"
    rows = con.execute("SELECT ticker, date, momentum_pct FROM momentum_events ORDER BY ticker, date").fetchall()

    eligible, non_eligible = [], []
    for ticker, date, momentum_pct in rows:
        folder_name = f"{ticker}_{date}_{momentum_pct:.2f}"
        folder = filtered_dir / folder_name
        rec = {"ticker": ticker, "date": str(date), "momentum_pct": momentum_pct, "expected_folder": folder_name}
        if (folder / "trades.parquet").exists() and (folder / "quotes.parquet").exists():
            eligible.append(rec)
        else:
            non_eligible.append(rec)
    return eligible, non_eligible


def build_ticker_date_index(inv: pd.DataFrame) -> dict:
    """(ticker, date) -> list of {folder_name, momentum_str, has_trades, has_quotes}, real dates only."""
    real = inv[~inv["date_is_none"]]
    idx = defaultdict(list)
    for _, r in real.iterrows():
        idx[(r["ticker"], r["date"])].append({
            "folder_name": r["folder_name"],
            "momentum_str": r["momentum_str"],
            "has_trades": bool(r["has_trades"]),
            "has_quotes": bool(r["has_quotes"]),
        })
    return idx


def t2b_classify_non_eligible(non_eligible: list[dict], td_index: dict) -> list[dict]:
    results = []
    for ev in non_eligible:
        key = (ev["ticker"], ev["date"])
        candidates = td_index.get(key, [])
        expected_mom_str = f"{ev['momentum_pct']:.2f}"
        exact = [c for c in candidates if c["momentum_str"] == expected_mom_str]
        other = [c for c in candidates if c["momentum_str"] != expected_mom_str]

        if len(other) > 0:
            cls = "format_mismatch"
        elif len(candidates) == 0:
            cls = "folder_absent"
        elif len(exact) > 1:
            cls = "duplicate_collision"
        else:
            c = exact[0]
            if c["has_trades"] and not c["has_quotes"]:
                cls = "missing_quotes"
            elif c["has_quotes"] and not c["has_trades"]:
                cls = "missing_trades"
            elif not c["has_trades"] and not c["has_quotes"]:
                cls = "missing_both"
            else:
                cls = "unexpected_both_present"

        results.append({**ev, "class": cls, "candidate_momentum_strs": [c["momentum_str"] for c in candidates]})
    return results


def t2c_classify_folders(inv: pd.DataFrame, event_key_counts: Counter) -> list[dict]:
    results = []
    for _, r in inv.iterrows():
        if r["date_is_none"]:
            results.append({"folder_name": r["folder_name"], "class": "none_date_unresolved"})
            continue
        if not r["name_parses"]:
            results.append({"folder_name": r["folder_name"], "class": "unparseable"})
            continue

        key = (r["ticker"], r["date"], round(float(r["momentum_str"]), 2))
        n = event_key_counts.get(key, 0)
        if n == 1:
            cls = "matched"
        elif n == 0:
            cls = "orphan"
        else:
            cls = "ambiguous"
        results.append({"folder_name": r["folder_name"], "class": cls})
    return results


def main(out_path: str) -> None:
    con = duckdb.connect(str(REPO_ROOT / "data" / "duckdb" / "main.duckdb"), read_only=True)

    eligible, non_eligible = t2a_reproduce_eligibility(con)
    t2a_check = {
        "eligible_count": len(eligible),
        "expected": 17203,
        "matches": len(eligible) == 17203,
        "non_eligible_count": len(non_eligible),
    }

    inv = pd.read_parquet(REPO_ROOT / "results" / "phase_0c" / "artifacts" / "folder_inventory.parquet")
    td_index = build_ticker_date_index(inv)

    t2b_results = t2b_classify_non_eligible(non_eligible, td_index)
    t2b_counts = Counter(r["class"] for r in t2b_results)
    t2b_sum_check = sum(t2b_counts.values()) == len(non_eligible)

    event_rows = con.execute("SELECT ticker, date, ROUND(momentum_pct, 2) FROM momentum_events").fetchall()
    event_key_counts = Counter((t, str(d), m) for t, d, m in event_rows if d is not None)
    con.close()

    t2c_results = t2c_classify_folders(inv, event_key_counts)
    t2c_counts = Counter(r["class"] for r in t2c_results)
    t2c_sum_check = sum(t2c_counts.values()) == len(inv)

    summary = {
        "t2a": t2a_check,
        "t2b_class_counts": dict(t2b_counts),
        "t2b_sum_check": t2b_sum_check,
        "t2b_sum_check_detail": {"sum": sum(t2b_counts.values()), "expected": len(non_eligible)},
        "t2c_class_counts": dict(t2c_counts),
        "t2c_sum_check": t2c_sum_check,
        "t2c_sum_check_detail": {"sum": sum(t2c_counts.values()), "expected": len(inv)},
        "escalations": {
            "t2a_mismatch": not t2a_check["matches"],
            "format_mismatch_nonzero": t2b_counts.get("format_mismatch", 0) > 0,
            "duplicate_collision_nonzero": t2b_counts.get("duplicate_collision", 0) > 0,
            "t2b_not_a_partition": not t2b_sum_check,
            "t2c_not_a_partition": not t2c_sum_check,
        },
    }

    out = REPO_ROOT / out_path
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    # Full per-row detail, for T3's sampling step
    detail_path = out.parent / "join_reconciliation_detail.json"
    detail_path.write_text(json.dumps({"t2b_results": t2b_results, "t2c_results": t2c_results}, indent=2), encoding="utf-8")

    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "results/phase_0c/artifacts/join_reconciliation.json"
    main(target)
