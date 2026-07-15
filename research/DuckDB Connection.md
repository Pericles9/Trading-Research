---
tags:
  - type/implementation
  - domain/data
  - project/src-core
  - status/complete
created: 2026-04-04
---

# DuckDB Connection

> **File:** `src/data/db.py` · **Lines:** 10

## Purpose

DuckDB connection manager. Single function returning a connection to `data/duckdb/main.duckdb`, creating the directory if needed.

## Function

```python
def get_connection(read_only=False) -> duckdb.DuckDBPyConnection
```

## Constants
- `DB_PATH = Path("data/duckdb/main.duckdb")`

## Dependencies
- **External:** `duckdb`

## Consumers
- [[DuckDB Ingest]]

---
*Back to [[Data Index]] · [[00-Index]]*
