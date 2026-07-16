"""Open the E: DuckDB read-only and compare table row counts against the
baseline recorded in data/Schema.md (T1b, prompts/phase_0b.md).

Read-only: opens with read_only=True, never writes to the database.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import duckdb

REPO_ROOT = Path(__file__).resolve().parents[2]
DUCKDB_PATH = REPO_ROOT / "data" / "duckdb" / "main.duckdb"

# As documented in data/Schema.md, last_reviewed 2026-07-14.
SCHEMA_MD_BASELINE = {
    "filtered_trades": 4_899_401_773,
    "filtered_quotes": 3_775_991_856,
    "raw_quotes": 1_757_761_017,
    "collection_stats": 1,
    "symbols_metadata": 2,
}


def main(out_path: str) -> None:
    con = duckdb.connect(str(DUCKDB_PATH), read_only=True)
    try:
        tables = [
            row[0]
            for row in con.execute(
                "SELECT table_name FROM information_schema.tables ORDER BY table_name"
            ).fetchall()
        ]
        actual = {t: con.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0] for t in tables}
    finally:
        con.close()

    comparison = []
    all_names = sorted(set(SCHEMA_MD_BASELINE) | set(actual))
    for name in all_names:
        expected = SCHEMA_MD_BASELINE.get(name)
        observed = actual.get(name)
        comparison.append(
            {
                "table": name,
                "expected_per_schema_md": expected,
                "observed": observed,
                "match": expected == observed,
            }
        )

    any_mismatch = any(not row["match"] for row in comparison)

    result = {
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "duckdb_path": str(DUCKDB_PATH),
        "schema_md_reviewed_date": "2026-07-14",
        "tables_present": tables,
        "comparison": comparison,
        "escalation_triggered": any_mismatch,
    }

    out = REPO_ROOT / out_path
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))
    if any_mismatch:
        print("HARD STOP: DuckDB row counts diverge from data/Schema.md")
        sys.exit(1)


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "results/phase_0b/artifacts/duckdb_state_check.json"
    main(target)
