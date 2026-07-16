# --- Provenance (Phase 0b T2) ---
# Recovered from D:\Trading Research\src\data\paths.py (uncommitted/untracked
# working-tree state on D: as of 2026-07-15 - that repo's git history never
# captured this file; no commit hash applies). Source mtime: 2026-07-13.
# Content unmodified from the D: copy.
# ---------------------------------
"""Path resolution helpers for data and DuckDB storage.

These helpers keep data and database locations configurable so the project
code can continue to work when storage is moved outside the repo.
"""
from __future__ import annotations

import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).parents[2]
# D: (Samsung 870 EVO) has confirmed, worsening hardware defects (SMART-verified,
# bad-block count climbing through this project's diagnostic sessions). Data and
# the DuckDB file both live on E: now — see results/hardware/ for the migration
# and verification record.
DEFAULT_DATA_ROOT = Path(r"E:\Trading Research\data")
DEFAULT_DATABASE_ROOT = DEFAULT_DATA_ROOT / "duckdb"
DEFAULT_DUCKDB_PATH = DEFAULT_DATABASE_ROOT / "main.duckdb"


def _env_path(name: str) -> Path | None:
    raw = os.getenv(name)
    if not raw:
        return None
    return Path(raw).expanduser()


def resolve_data_root(explicit: Path | None = None) -> Path:
    """Resolve root folder for source parquet/csv/json datasets."""
    if explicit is not None:
        return explicit.expanduser().resolve()
    from_env = _env_path("MOM_DB_DATA_ROOT")
    if from_env is not None:
        return from_env.resolve()
    return DEFAULT_DATA_ROOT.resolve()


def resolve_database_root(explicit: Path | None = None) -> Path:
    """Resolve root folder where DuckDB files should live."""
    if explicit is not None:
        return explicit.expanduser().resolve()
    from_env = _env_path("MOM_DB_DATABASE_ROOT")
    if from_env is not None:
        return from_env.resolve()
    return DEFAULT_DATABASE_ROOT.resolve()


def resolve_duckdb_path(explicit: Path | None = None) -> Path:
    """Resolve DuckDB database file path.

    Priority:
    1) explicit path argument
    2) MOM_DB_DUCKDB_PATH
    3) MOM_DB_DATABASE_ROOT/main.duckdb
    4) repo default data/duckdb/main.duckdb
    """
    if explicit is not None:
        return explicit.expanduser().resolve()
    from_env_file = _env_path("MOM_DB_DUCKDB_PATH")
    if from_env_file is not None:
        return from_env_file.resolve()
    database_root = resolve_database_root()
    return (database_root / "main.duckdb").resolve()
