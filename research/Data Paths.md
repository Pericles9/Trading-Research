---
tags:
  - type/implementation
  - domain/data
  - project/src-core
  - status/complete
created: 2026-04-04
last_reviewed: 2026-04-04
linked_code: "[[paths.py]]"
---

# paths.py

## Purpose
Central path resolution for data and DuckDB storage locations. Keeps all code working correctly whether storage is local to the repo or split to an external drive via environment variables. Single source of truth for default roots and env override precedence.

## Key Functions / Classes
| Name | Type | Description |
|------|------|-------------|
| `resolve_data_root()` | function | Returns root folder for source parquet/csv/json datasets |
| `resolve_database_root()` | function | Returns root folder where DuckDB files should live |
| `resolve_duckdb_path()` | function | Returns full DuckDB `.db` file path |
| `_env_path(name)` | function | Reads a `Path` from an env var; returns `None` if unset |

## Inputs / Outputs
All three `resolve_*` functions accept an optional `explicit: Path | None` argument. If provided, it takes priority. Otherwise resolution falls through env vars and repo defaults.

**Priority order for `resolve_duckdb_path`:**
1. `explicit` argument
2. `MOM_DB_DUCKDB_PATH` env var
3. `MOM_DB_DATABASE_ROOT/main.duckdb`
4. `data/duckdb/main.duckdb` (repo default)

## Dependencies
- stdlib: `os`, `pathlib`
- `src/data/paths.py` is imported by `src/data/ingest.py`, `src/data/db.py`, `src/data/prepare_database_split.py`

## Usage Example
```python
from src.data.paths import resolve_duckdb_path, resolve_data_root

db_path = resolve_duckdb_path()           # uses env or repo default
db_path = resolve_duckdb_path(Path("/external/main.duckdb"))  # explicit override
data_root = resolve_data_root()
```

## Notes
- Module constants `DEFAULT_DATA_ROOT`, `DEFAULT_DATABASE_ROOT`, `DEFAULT_DUCKDB_PATH` are derived from `__file__` location — they are always correct relative to the repo regardless of where scripts are launched from.
- See `data/Schema.md` for the full dataset layout that these paths point into.

## Related
- [[DuckDB Connection]] — uses `resolve_duckdb_path`
- [[DuckDB Ingest]] — uses all three resolvers
- [[data/Schema.md]] — documents what lives at the resolved paths
