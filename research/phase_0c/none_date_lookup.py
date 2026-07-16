"""Cross-reference the 114 date_is_none folders against momentum_events.

For each None-date folder, extract (ticker, momentum_pct) from the folder
name and look up momentum_events rows matching on BOTH ticker and
momentum_pct (rounded to 2dp, the folder name's precision) - momentum_pct
is the only usable join key left once the date is known to be broken.

Three distinct outcomes are reported, not merged:
  - matched_valid_date: exactly one matching event row, with a non-null date
    (folder name is broken; the event itself is fine)
  - matched_null_date: exactly one matching event row, but its own date is
    ALSO null (worse - we don't know what window this folder's data,
    if any existed, would correspond to)
  - no_match_found: zero event rows share (ticker, momentum_pct) - the
    folder doesn't correspond to any known event at all
  - multiple_matches: more than one event row shares (ticker, momentum_pct)
    - ambiguous, reported separately, not folded into either bucket above

Read-only against momentum_events. Does not touch filtered_trades/
filtered_quotes/raw_quotes.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import duckdb
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]


def main(out_path: str) -> None:
    inv = pd.read_parquet(REPO_ROOT / "results" / "phase_0c" / "artifacts" / "folder_inventory.parquet")
    none_date_folders = inv[inv["date_is_none"]].copy()

    con = duckdb.connect(str(REPO_ROOT / "data" / "duckdb" / "main.duckdb"), read_only=True)

    null_date_count_in_momentum_events = con.execute(
        "SELECT COUNT(*) FROM momentum_events WHERE date IS NULL"
    ).fetchone()[0]

    results = []
    outcome_counts = {
        "matched_valid_date": 0,
        "matched_null_date": 0,
        "no_match_found": 0,
        "multiple_matches": 0,
    }

    for _, row in none_date_folders.iterrows():
        ticker = row["ticker"]
        mom = round(float(row["momentum_str"]), 2)

        matches = con.execute(
            "SELECT date, momentum_pct FROM momentum_events "
            "WHERE ticker = ? AND ROUND(momentum_pct, 2) = ?",
            [ticker, mom],
        ).fetchall()

        if len(matches) == 0:
            outcome = "no_match_found"
            event_date = None
        elif len(matches) > 1:
            outcome = "multiple_matches"
            event_date = [str(m[0]) for m in matches]
        else:
            event_date = matches[0][0]
            outcome = "matched_null_date" if event_date is None else "matched_valid_date"
            event_date = str(event_date) if event_date is not None else None

        outcome_counts[outcome] += 1
        results.append({
            "folder_name": row["folder_name"],
            "ticker": ticker,
            "momentum_str_from_folder": row["momentum_str"],
            "event_row_date": event_date,
            "outcome": outcome,
        })

    con.close()

    summary = {
        "total_none_date_folders": len(none_date_folders),
        "momentum_events_date_column_null_count_overall": null_date_count_in_momentum_events,
        "outcome_counts": outcome_counts,
        "sum_check": sum(outcome_counts.values()) == len(none_date_folders),
        "results": results,
    }

    out = REPO_ROOT / out_path
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in summary.items() if k != "results"}, indent=2))


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "results/phase_0c/artifacts/none_date_lookup.json"
    main(target)
