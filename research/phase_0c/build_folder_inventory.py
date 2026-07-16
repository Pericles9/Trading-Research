"""T1 - single os.scandir pass over data/filtered/, classifying every entry.

Directory listing / existence checks only - no parquet files are opened.
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]

FOLDER_PATTERN = re.compile(r"^(?P<ticker>[A-Z0-9]+)_(?P<date>\d{4}-\d{2}-\d{2})_(?P<mom>[\d.]+)$")


def classify(is_dir: bool, name_parses: bool, has_trades: bool, has_quotes: bool) -> str:
    if not name_parses:
        return "unparseable_name"
    if not is_dir:
        return "neither"
    if has_trades and has_quotes:
        return "both_files"
    if has_trades and not has_quotes:
        return "trades_only"
    if has_quotes and not has_trades:
        return "quotes_only"
    return "neither"


def main(out_parquet: str, out_summary: str) -> None:
    filtered_dir = REPO_ROOT / "data" / "filtered"
    rows = []

    with os.scandir(filtered_dir) as it:
        for entry in it:
            name = entry.name
            is_dir = entry.is_dir()
            m = FOLDER_PATTERN.match(name)
            name_parses = m is not None

            ticker = m.group("ticker") if m else None
            date = m.group("date") if m else None
            mom_str = m.group("mom") if m else None

            has_trades = is_dir and (Path(entry.path) / "trades.parquet").exists()
            has_quotes = is_dir and (Path(entry.path) / "quotes.parquet").exists()

            cls = classify(is_dir, name_parses, has_trades, has_quotes)

            rows.append({
                "folder_name": name,
                "is_dir": is_dir,
                "name_parses": name_parses,
                "ticker": ticker,
                "date": date,
                "momentum_str": mom_str,
                "has_trades": has_trades,
                "has_quotes": has_quotes,
                "class": cls,
            })

    df = pd.DataFrame(rows)
    out_pq = REPO_ROOT / out_parquet
    out_pq.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(out_pq, index=False)

    class_counts = df["class"].value_counts().to_dict()
    summary = {
        "total_entries": len(df),
        "class_counts": {k: int(v) for k, v in class_counts.items()},
        "all_classes": ["both_files", "trades_only", "quotes_only", "neither", "unparseable_name"],
    }
    for c in summary["all_classes"]:
        summary["class_counts"].setdefault(c, 0)
    summary["sum_check"] = sum(summary["class_counts"][c] for c in summary["all_classes"]) == summary["total_entries"]

    out_sum = REPO_ROOT / out_summary
    out_sum.parent.mkdir(parents=True, exist_ok=True)
    out_sum.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    pq = sys.argv[1] if len(sys.argv) > 1 else "results/phase_0c/artifacts/folder_inventory.parquet"
    sm = sys.argv[2] if len(sys.argv) > 2 else "results/phase_0c/artifacts/folder_inventory_summary.json"
    main(pq, sm)
