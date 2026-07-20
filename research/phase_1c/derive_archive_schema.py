"""
Phase 1c T0 support - derive the file-level archive schema for trades.parquet
and quotes.parquet across the full data/filtered/ corpus (metadata-only scan,
reuses src.data.ingest's _scan_union_schema - the same mechanism the real
ingest path uses). Confirms config/phase_1c.json's archive_schema block.

Read-only: scans parquet footers only, writes nothing to data/.
"""
import json
import sys
import time
from pathlib import Path

import duckdb

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from src.data.ingest import _scan_union_schema  # noqa: E402

OUT_PATH = "results/phase_1c/artifacts/archive_schema_reference.json"


def main():
    con = duckdb.connect(read_only=False)

    t0 = time.time()
    trades_paths = sorted(Path("data/filtered").glob("*/trades.parquet"))
    trades_schema, _ = _scan_union_schema(
        con, trades_paths, type_overrides={"size": "BIGINT", "participant_timestamp": "BIGINT"}
    )
    print(f"trades: {len(trades_paths)} files scanned in {time.time() - t0:.1f}s")

    t0 = time.time()
    quotes_paths = sorted(Path("data/filtered").glob("*/quotes.parquet"))
    quotes_schema, _ = _scan_union_schema(
        con, quotes_paths, type_overrides={"ask_size": "BIGINT", "bid_size": "BIGINT"}
    )
    print(f"quotes: {len(quotes_paths)} files scanned in {time.time() - t0:.1f}s")

    # _scan_union_schema deliberately drops LIST-typed columns (conditions,
    # indicators - see src/data/ingest.py's PARQUET_LIST_INTERNAL_NAMES).
    # Confirmed present at the file level via direct inspection of a sample
    # file's parquet_schema() (conditions: BIGINT[] on both trades and
    # quotes; indicators: BIGINT[] on quotes only) - added back here since
    # the file-level archive schema (this phase's fetch-alignment target,
    # and what T6's repair siblings must match) is the true source of
    # record, not the DB tables' derived, LIST-dropped schema.
    sample = duckdb.execute(
        f"SELECT name, duckdb_type FROM parquet_schema('{trades_paths[0].as_posix()}')"
    ).fetchdf()
    assert "conditions" in sample["name"].values, "conditions column not found in sample trades file - archive schema assumption invalid"
    trades_schema_full = {**trades_schema, "conditions": "BIGINT[]"}

    sample_q = duckdb.execute(
        f"SELECT name, duckdb_type FROM parquet_schema('{quotes_paths[0].as_posix()}')"
    ).fetchdf()
    assert "conditions" in sample_q["name"].values and "indicators" in sample_q["name"].values, \
        "conditions/indicators not found in sample quotes file - archive schema assumption invalid"
    quotes_schema_full = {**quotes_schema, "conditions": "BIGINT[]", "indicators": "BIGINT[]"}

    out = {
        "phase": "1c",
        "task": "T0-support",
        "n_trades_files_scanned": len(trades_paths),
        "n_quotes_files_scanned": len(quotes_paths),
        "trades_file_level_schema": trades_schema_full,
        "quotes_file_level_schema": quotes_schema_full,
        "trades_db_table_schema": trades_schema,
        "quotes_db_table_schema": quotes_schema,
        "note": "file_level = archive schema for fetch alignment (T2) and repair siblings (T6). "
                "db_table = filtered_trades/filtered_quotes as ingested (conditions/indicators dropped "
                "by src/data/ingest.py's deliberate LIST-column-drop design, unchanged by this phase).",
    }
    with open(OUT_PATH, "w") as f:
        json.dump(out, f, indent=2)
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
