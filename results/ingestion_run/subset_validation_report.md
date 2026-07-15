---
tags:
  - type/results
  - domain/data
  - project/src-core
  - status/needs-review
created: 2026-07-11
---

# DuckDB Ingestion — T3 Subset Validation Report

## Result: T4 GATE — do not proceed to T5 for `filtered` or `quote_data`

Ran the real `src/data/ingest.py` CLI (not a simulation) against a staged
50-event/50-file subset (metadata used its full 2-file set — the natural
minimum unit). Command: `python -m src.data.ingest --dataset filtered
--dataset quote_data --dataset metadata --data-root <staging> --db-path
<staging_db>`.

| Loader | Table | Attempted | Failed | Failure rate | Result |
|---|---|---|---|---|---|
| `filtered` | `filtered_trades` | 50 | 22 | 44% | **FAIL** |
| `filtered` | `filtered_quotes` | 50 | 16 | 32% | **FAIL** |
| `quote_data` | `raw_quotes` | 50 | 5 | 10% | **FAIL** |
| `metadata` | `collection_stats`, `symbols_metadata` | 2 | 0 | 0% | **PASS** |

(A separate stdout `UnicodeEncodeError`/"Logging error" on the `─` separator
character is a harmless Windows console-encoding cosmetic issue in the
logging setup — not a data error, does not affect ingestion, not counted
above.)

## Root cause 1: heterogeneous source schema, not handled (37 errors)

`load_filtered`, and `load_quote_data` all use the same pattern: `CREATE
TABLE AS` from the first file's `SELECT *`, then `INSERT INTO ... SELECT *`
for every subsequent file — which only works if every file in the dataset
has the **same number of columns in the same order**. They don't:

```
Binder Error: table filtered_trades has 14 columns but 6 values were supplied
Binder Error: table filtered_trades has 14 columns but 15 values were supplied
Binder Error: table filtered_quotes has 15 columns but 8 values were supplied
Binder Error: table raw_quotes has 8 columns but 9 values were supplied
```

This is not a surprise in isolation — schema drift in this corpus is already
documented in `results/final_gap_fill/migration_report.md` ("Schema is
internally consistent with `filtered/`'s existing drift pattern (`correction`
present/absent, `size` occasionally DOUBLE)") — but the loader was never
updated to tolerate it. Whichever file happens to load first fixes the
table's column count; every file with a different column count then fails
and is silently skipped (caught by the per-file `try/except`, logged as an
error, loop continues). Over a 50-file sample this is already 10–44% loss;
at full scale (24,200 / 22,660 / 19,132 files) this would silently violate
the "row counts matching source counts exactly" success metric — the kind of
deviation T6's escalation criteria are built to catch, just discovered here
instead, before a wasted full run.

**There is already a working precedent for the fix in this same file**:
`load_nautilus_catalog` uses `read_parquet(..., union_by_name=true)` — DuckDB
natively harmonizes differing schemas across files by column name (missing
columns become NULL) instead of failing on positional mismatch. None of the
other loaders use this option.

## Root cause 2: `momentum_pct` type inference overflow (6 errors)

```
Conversion Error: Casting value "226.74" to type DECIMAL(4,2) failed: value is out of range!
```

`momentum_pct` is embedded as a bare literal (`{momentum_pct} AS
momentum_pct`) in both `load_filtered`'s trades and quotes queries. DuckDB
infers the column's type from whichever file's literal creates the table —
if that file's value fits `DECIMAL(4,2)` (max 99.99), every later file with
a momentum value ≥100 (e.g. 226.74, 157.43, 132.04 — all real, valid
momentum percentages in this corpus) fails to insert. Confirmed momentum
values well over 100% exist broadly in `filtered/` (not an edge case).

## What passed

`metadata` (`collection_stats`, `symbols_metadata`) loaded cleanly — single
file each, no schema-drift or type-inference exposure. Schema and row counts
matched expectations (1 row, 2 rows respectively — small reference tables).

## Gate decision (T4)

Per escalation criteria ("A loader's subset validation (T3) fails → stop for
that loader only, report; independent loaders continue"): **`filtered` and
`quote_data` do not pass T3 and should not proceed to T5 (full run) as-is.**
Running them unfixed against the full corpus would silently drop an
unpredictable ~10–44% of files per table — a worse outcome than not running
at all, and one that would only surface after the fact at T6 (or not at all,
if the resulting undercount were mistaken for the correct count).

`metadata` passed cleanly and could proceed to T5 independently, though at 2
files total there's little practical difference between validating and just
running it directly.

## Addendum — fix attempt and re-validation (2026-07-11, same session)

Applied two changes to `src/data/ingest.py`, re-ran the identical 50-event/
50-file subset against a fresh throwaway DB:

| Fix | Result |
|---|---|
| `CAST({momentum_pct} AS DOUBLE)` instead of a bare literal | **Worked.** All 6 `Conversion Error` (DECIMAL overflow) failures gone. |
| `union_by_name=true` added to each per-file `read_parquet(...)` call | **Did not work.** All 37 `Binder Error` (schema drift) failures persisted, identical files, identical column-count mismatches. |

**Why the second fix failed:** `union_by_name=true` harmonizes schemas
*across multiple files given to a single `read_parquet()` call* (a glob or
file list). It has no effect here because each file is read by its own
separate `read_parquet()` call inside a Python loop (needed to inject
per-file literals — `ticker`, `event_date`/`quote_date`, `momentum_pct` —
that aren't in the parquet content itself). Nothing unions the schema of
file #2's single-file read against the table's schema fixed by file #1;
`union_by_name` had nothing to union against within a one-file read. This was
a wrong diagnosis on my part, caught by re-running the same validation
rather than assuming the fix worked.

**What a real fix needs:** `INSERT INTO ... BY NAME` (DuckDB syntax matching
by column name, tolerating missing columns as NULL) would handle files with
*fewer* columns than the table. But this corpus has drift in both
directions — some files have more columns than the file that created the
table (`"14 columns but 15 values"`) — and `BY NAME` alone can't insert into
columns the table doesn't have yet. A correct fix needs either (a) a
first-pass scan of all files' schemas to build the full column union before
`CREATE TABLE`, or (b) `ALTER TABLE ... ADD COLUMN IF NOT EXISTS` for
new columns encountered mid-loop, before each `INSERT ... BY NAME`. This is
more involved than the one-line precedent I initially assumed applied, and I
have not attempted it.

**Current state of `src/data/ingest.py`:** the `momentum_pct` cast fix is
applied and confirmed working. The `union_by_name=true` additions are applied
but confirmed to have no effect — harmless (not a regression) but not a fix
either. **T5 (full run) still should not proceed** for `filtered` or
`quote_data` — the schema-drift bug is unresolved. Stopping here for review,
per instruction, rather than attempting a second-guess fix.
