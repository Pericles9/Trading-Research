---
tags:
  - type/results
  - domain/data
  - project/src-core
  - status/complete
created: 2026-07-12
linked_code: "[[ingest.py]]"
---

# Ingestion Loader Fix — T2 Implementation, T3 Verification

## T2 — What the fix does and why

Added two helpers to `src/data/ingest.py`:

- **`_scan_union_schema(con, paths, type_overrides, exclude_columns)`** —
  metadata-only scan (`parquet_schema()`) across every file in a dataset,
  returning the full column union with a resolved type per column, plus a
  per-file column-presence map. A type conflict (a column seen with more
  than one native type) must have an explicit `type_overrides` entry or the
  function raises — conflicts are never silently resolved.
- **`_build_select_for_file(...)`** — builds a per-file `SELECT` list
  containing only the columns that specific file actually has (cast to the
  resolved union type where it differs from the file's native type), plus
  the injected literal columns (`ticker`, `event_date`/`quote_date`,
  `momentum_pct`). Columns the file lacks are simply omitted —
  `INSERT INTO ... BY NAME` NULL-fills them automatically (verified
  directly before use — see prior turn's test).

`load_filtered` and `load_quote_data` now: scan the full union schema once
before the per-file loop, `CREATE TABLE` with that complete schema up
front, then loop per file using `INSERT INTO ... BY NAME` instead of the
old `CREATE TABLE AS` (first file) + positional `INSERT INTO` (rest), which
is what broke on any file whose column count didn't match the first file's.

### A bug in my own first attempt at this fix, caught by re-validation

The first implementation used raw `parquet_schema()` rows directly,
including — undetected — Parquet's internal LIST-encoding structural rows
(a `schema` root row, and for each LIST column a `list`/`element` pair
carrying the leaf type). This misread `element` as if it were a genuine
top-level column and produced a `CREATE TABLE` with unusable `nan`-typed
columns (`"schema" nan, "conditions" nan, "list" nan`), failing immediately
on all 3 tables. Caught by actually re-running the fix against the subset
rather than assuming the logic was correct from the design alone. Fixed by
filtering to rows with a real (string) `duckdb_type` and excluding Parquet's
reserved internal names (`schema`, `list`, `element`, `key`, `value`,
`entries`).

### Column-drop decision, made explicit here

The two exclusion mechanisms together mean `conditions` (`filtered_trades`)
and `conditions`/`indicators` (`filtered_quotes`) are dropped rather than
reconstructed as `BIGINT[]` columns. This is deliberate, not a side effect
that fell out of the LIST-parsing fix: both were already confirmed unused
by any downstream code in the earlier quotes-fix phase
(`column_usage_scope.csv`), and reconstructing LIST-typed columns correctly
in the per-file `BY NAME` insert path would add real, currently-untested
complexity for columns nothing reads. If a future need for either column
arises, this is the place to revisit.

## T2 — Type-conflict resolutions applied (from T1's characterization)

| Table | Column | Resolved to | Verified how |
|---|---|---|---|
| `filtered_trades` | `size` | BIGINT | Full scan, 1.18B rows, 0 fractional values |
| `filtered_trades` | `participant_timestamp` | BIGINT | Structural fact (nanosecond epoch exceeds DOUBLE's exact-int range) + confirmed unused downstream |
| `filtered_quotes` | `ask_size` | BIGINT | Full scan, 87.7M rows, 0 fractional values |
| `filtered_quotes` | `bid_size` | BIGINT | Full scan, 95.0M rows, 0 fractional values |
| `raw_quotes` | `ask_size` | BIGINT | Full scan, 39.8M rows, 0 fractional values |
| `raw_quotes` | `bid_size` | BIGINT | Full scan, 68.7M rows, 0 fractional values |
| `raw_quotes` | `__index_level_0__` | Dropped | Pandas index serialization artifact, not real data |

## T3 — Verification against the identical previously-failing subset

Re-ran `python -m src.data.ingest --dataset filtered --dataset quote_data
--dataset metadata` against the same staged 50-event/50-file subset that
originally produced 37 schema-drift errors (plus the already-separately-fixed
6 `momentum_pct` errors).

| Table | Files attempted | Errors | Result |
|---|---|---|---|
| `filtered_trades` | 50 | **0** | **PASS** — 5,717,505 rows from 50/50 files |
| `filtered_quotes` | 50 | **0** | **PASS** — 3,926,498 rows from 50/50 files |
| `raw_quotes` | 50 | **0** | **PASS** — 4,063,678 rows from 50/50 files |
| `metadata` (2 files) | 2 | 0 | PASS (unchanged, was already passing) |

**Zero schema-drift errors. Zero regressions in the `momentum_pct` fix** —
spot-checked directly: `BNAI 2024-05-31` (momentum_pct 226.74, the original
overflow trigger) loads correctly; max momentum_pct in the reloaded subset
is 226.74 with no errors.

### Content spot-checks (not just error counts)

- `filtered_trades` schema: `size` and `participant_timestamp` both BIGINT
  as resolved; no `conditions`/`schema`/`list`/`element` artifact columns.
- A 2025 gap-fill (subtractive-schema) file's rows correctly show real
  values for `sip_timestamp`/`price`/`size` and **NULL** (not missing, not
  an error) for `correction`/`trf_id`/`tape` — exactly the intended
  NULL-fill behavior for columns that file never had.

## Current state

`src/data/ingest.py`'s `filtered`, `quote_data` loaders are fixed and
verified against the exact case that broke them. `momentum_pct` fix
(unrelated, already-working) is unaffected. Ready to resume the paused
DuckDB ingestion task's T5 (full run).
