# --- Provenance (Phase 0b T2) ---
# Recovered from D:\Trading Research\src\data\db.py (modified/uncommitted
# relative to that repo's HEAD; no commit hash applies). Source mtime:
# 2026-03-14. Content unmodified from the D: copy.
# ---------------------------------
"""DuckDB connection manager for mom_db."""
from __future__ import annotations

from pathlib import Path

import duckdb

from src.data.paths import resolve_duckdb_path


def get_connection(
    read_only: bool = False,
    db_path: Path | None = None,
) -> duckdb.DuckDBPyConnection:
    """Return a DuckDB connection.

    The database location can be overridden with either:
    - ``db_path`` argument
    - ``MOM_DB_DUCKDB_PATH``
    - ``MOM_DB_DATABASE_ROOT`` (+ ``main.duckdb``)
    """
    resolved = resolve_duckdb_path(db_path)
    resolved.parent.mkdir(parents=True, exist_ok=True)
    return duckdb.connect(str(resolved), read_only=read_only)
