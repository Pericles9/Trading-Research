<!-- COPY OF RECORD for `data/Schema.md`, which is untracked because `.gitignore`
     excludes `/data/` wholly. Edit HERE; mirror to `data/Schema.md` for anyone reading the
     data tree directly. Established 2026-09-10, D26 follow-up. -->

---
tags:
  - type/data-schema
  - domain/data
  - project/src-core
  - status/complete
created: 2026-04-04
last_reviewed: 2026-07-14
---
# Mom_db Data Schema & Build Provenance

## Scope

This document maps each top-level folder under `data/` to:

1. File/folder format
2. Naming schema
3. Script(s) used to build it (when found in current workspace)
4. Target snapshot duration

## Provenance Status Legend

- **Confirmed**: explicit writer logic found in current workspace.
- **Inferred**: structure verified on disk, but writer script not found here.
- **Unknown**: no reliable writer evidence found in current workspace.

## Archived Script Note

No workspace-local `archived` folder was found during repo search. If historical collection scripts exist outside this checkout, the unresolved provenance entries below should be reconciled against that external archive.

## Folder-by-Folder Schema

| Folder | File / Folder Format | Naming Schema (observed) | Build Script(s) Found | Target Duration | Provenance |
|---|---|---|---|---|---|
| `collection_scripts/` | Python scripts + logs | `collect_massive_data.py`, `filter_events_power_law.py`, `inspect_parquet_columns.py`, `collection_log.txt` | N/A (script source folder) | N/A | Confirmed |
| `momentum_events/` | Parquet + CSV event tables | `filtered_events_power_law_q05.parquet`, `filtered_events_power_law_q05.csv`; plus momentum scan parquet inputs | `collection_scripts/filter_events_power_law.py` | Event-level records (no fixed window; one row per event) | Confirmed |
| `filtered/` | Per-event folders containing 2 parquet files | Folder: `{TICKER}_{YYYY-MM-DD}_{momentum_pct_2dp}`; files: `trades.parquet`, `quotes.parquet` | `collection_scripts/collect_massive_data.py` (input: `momentum_events/filtered_events_power_law_q05.parquet`) | **7 trading-day window** centered on event date (T-3 ... T+3) | Confirmed |
| `daily/` | Parquet files | `{TICKER}_daily.parquet` | Not found in current workspace | 1-day bars aggregated across multi-date history per symbol file | Inferred |
| `minute/` | Folder-per-symbol with daily parquet files | `{TICKER}/{YYYY-MM-DD}.parquet` | Not found in current workspace | 1-minute bars for one trading session per file | Inferred |
| `second10/` | Folder-per-symbol with daily parquet files | `{TICKER}/{TICKER}_{YYYY-MM-DD}.parquet` | Not found in current workspace | 10-second bars for one trading session per file | Inferred |
| `quote_data/` | Flat parquet files | `{TICKER}_quotes_{YYYY}_{MM}_{DD}.parquet` | Not found in current workspace | Quote ticks for one symbol-day per file | Inferred |
| `trade_data/` | Mixed folders + parquet + JSON progress files | Subfolders: `batches/`, `by_date/`, `by_ticker/`, `enhanced/`, `high_momentum/`, `logs/`, `metadata/`; files: `momentum_events_for_collection.parquet`, `*_progress.json` | Legacy helper reference only in `debug_schema.py`; no active writer found | Likely symbol/day or batch snapshots (depends on subfolder) | Unknown |
| `metadata/` | Parquet | `collection_stats.parquet`, `symbols_metadata.parquet` | Not found in current workspace | Dataset-level summary snapshots (non-time-series payloads) | Unknown |
| `market-hours/` | JSON | `market-hours-database.json` | Not found in current workspace | Calendar/session metadata (date-level) | Unknown |
| `symbol-properties/` | CSV | `symbol-properties-database.csv` | Not found in current workspace | Point-in-time symbol attributes | Unknown |
| `nautilus_catalog/` | Nested parquet catalog layout | `data/equity/{SYMBOL}.{VENUE}/...parquet`, `data/trade_tick/{SYMBOL}.{VENUE}/...parquet` | No catalog writer found in current workspace (many readers/consumers exist) | Instrument/venue-partitioned history; file-level duration not established here | Inferred |
| `collection_scripts/collection_log.txt` (artifact) | Text log | Line-oriented run log of collection process | Written by `collect_massive_data.py` logging | Runtime log across full collection batch | Confirmed |

## Confirmed Build Pipeline (Current Workspace)

1. **Momentum filter stage**
	- Script: `collection_scripts/filter_events_power_law.py`
	- Reads momentum scan parquet source files.
	- Fits q=0.05 quantile regression in log-space.
	- Writes `momentum_events/filtered_events_power_law_q05.parquet` (+ CSV).

2. **Event snapshot collection stage**
	- Script: `collection_scripts/collect_massive_data.py`
	- Reads filtered event parquet.
	- For each event, fetches trades + quotes and writes:
	  - `filtered/{TICKER}_{DATE}_{MOM}/trades.parquet`
	  - `filtered/{TICKER}_{DATE}_{MOM}/quotes.parquet`
	- Uses a 7-trading-day window around event date.

## DuckDB Implementation (Current)

### Current Database Location

As of 2026-07-14, both the source data root and the DuckDB file live on
**E:** (`E:\Trading Research\data`, `E:\Trading Research\data\duckdb\main.duckdb`),
set as the hardcoded default in `src/data/paths.py`. This is not the repo-relative
default shown in the CLI examples below — D: (the drive the repo's default path
would otherwise resolve to) has confirmed, worsening hardware defects and was
migrated off entirely. See `results/hardware/` for the migration/verification
record and `results/ingestion_run/e_drive_ingestion_report.md` for the full
E:-based buildout and verification. Do not write new data to D:.

### Components

- `src/data/db.py`
	- Connection manager (`get_connection`) for DuckDB.
	- Creates parent directory before opening DB.
	- Supports externalized DB location via:
		1. `db_path` argument
		2. `MOM_DB_DUCKDB_PATH`
		3. `MOM_DB_DATABASE_ROOT/main.duckdb`
		4. fallback `data/duckdb/main.duckdb`

- `src/data/ingest.py`
	- Multi-dataset ingest CLI (`--all`, `--dataset`, `--verify-only`).
	- Data root defaults to `MOM_DB_DATA_ROOT` (if set), else `data/` in repo.
	- Optional `--db-path` to write into any DuckDB file.
	- Creates materialized tables for most datasets and live views for Nautilus catalog parquet globs.

- `src/data/paths.py`
	- Central path resolution for data/database split scenarios.
	- Single source of truth for project default roots and env override precedence.

### Ingested Tables / Views

| Dataset Key | Table / View Name | Type | Status | Rows (E:, 2026-07-14) |
|---|---|---|---|---|
| `filtered` | `filtered_trades` | Table | **Loaded** — 24,200/24,200 files, exact match | 4,899,401,773 |
| `filtered` | `filtered_quotes` | Table | **Loaded** — 22,660/22,660 files, exact match | 3,775,991,856 |
| `quote_data` | `raw_quotes` | Table | **Loaded** — 19,123/19,136 files; 13 excluded (9 unreadable/absent source files, 2 truncated, 2 OOM on malformed metadata) — see `e_drive_ingestion_report.md` | 1,757,761,017 |
| `metadata` | `collection_stats` | Table | **Loaded** | 1 |
| `metadata` | `symbols_metadata` | Table | **Loaded** | 2 |
| `daily` | `daily_bars` | Table | Not loaded — out of scope for this buildout | — |
| `minute` | `minute_bars` | Table | Not loaded — out of scope for this buildout | — |
| `second10` | `second10_bars` | Table | Not loaded — out of scope for this buildout | — |
| `momentum_events` | `momentum_events` | Table | Not loaded — out of scope for this buildout | — |
| `market_hours` | `market_hours` | Table | Not loaded — out of scope for this buildout | — |
| `symbol_properties` | `symbol_properties` | Table | Not loaded — out of scope for this buildout | — |
| `trade_data` | `trade_data_events`, `trade_data_*` | Table | Not loaded — out of scope for this buildout | — |
| `nautilus_catalog` | `nautilus_equity`, `nautilus_trade_tick` | View | Not loaded — out of scope for this buildout | — |

The current `main.duckdb` on E: only contains the 5 loaded tables above
(`filtered_trades`, `filtered_quotes`, `raw_quotes`, `collection_stats`,
`symbols_metadata` — confirmed via `information_schema.tables`). The recent
buildout effort was scoped to `filtered/`, `quote_data/`, and `metadata/`
only; the remaining loaders exist in `src/data/ingest.py` and are runnable
via `--dataset <key>` but have not been exercised against the E: data root.

### CLI Reference

```bash
# Full ingest using resolved defaults
python -m src.data.ingest --all

# Selective ingest
python -m src.data.ingest --dataset filtered --dataset minute

# Override both roots explicitly
python -m src.data.ingest --data-root D:/mom_db_storage/data --db-path D:/mom_db_storage/data/duckdb/main.duckdb

# Verify inventory only
python -m src.data.ingest --verify-only
```

## Database Directory Split Prep (New)

To support splitting this research repo from storage, a migration prep utility is now available:

- Script: `src/data/prepare_database_split.py`
- Purpose:
	1. Create target directory scaffold
	2. Build `migration_manifest.json` with dataset sizes and source/target mapping
	3. Emit `env.example` with `MOM_DB_*` variables
	4. Optional `--copy` to physically copy datasets

```bash
# Plan only (no copy)
python -m src.data.prepare_database_split --target-root D:/mom_db_storage

# Plan + copy data
python -m src.data.prepare_database_split --target-root D:/mom_db_storage --copy
```

### Recommended Split Layout

```text
D:/mom_db_storage/
├── data/
│   ├── duckdb/
│   │   └── main.duckdb
│   ├── filtered/
│   ├── daily/
│   ├── minute/
│   ├── second10/
│   ├── quote_data/
│   ├── trade_data/
│   ├── momentum_events/
│   ├── metadata/
│   ├── market-hours/
│   ├── symbol-properties/
│   └── nautilus_catalog/
├── migration_manifest.json
└── env.example
```

### Environment Variables for Split Mode

- `MOM_DB_DATA_ROOT`
- `MOM_DB_DATABASE_ROOT`
- `MOM_DB_DUCKDB_PATH`

These let the same codebase run unchanged whether storage is local to this repo or external.

## Known Gaps / Follow-up Needed

The following datasets are present on disk but currently lack writer provenance in this checkout:

- `daily/`
- `minute/`
- `second10/`
- `quote_data/`
- Most of `trade_data/` generation flow
- `metadata/`, `market-hours/`, `symbol-properties/`
- `nautilus_catalog/` build process

If an external or missing archive exists, reconcile these entries there and update this file from **Inferred/Unknown** to **Confirmed** with script paths.

**Resolved 2026-07 (Phase 1/1b):** The 5,911 NULL-date rows in `momentum_events` are confirmed as a filter-script artifact — `filter_events_power_law.py` concatenates file1 (`date`) and file2 (`event_date`) without reconciling the date columns. Canonical access is via `momentum_events_canonical` (writer: `src/data/canonical.py`, provenance Confirmed). Raw table left untouched.

**Confirmed 2026-07 (Phase 1b):** `collect_massive_data.py` computed T-3..T+3 windows against the US federal holiday calendar, not the exchange calendar. Consequences: event days falling on federal-but-not-market holidays (Columbus Day, Veterans Day, Juneteenth 2021 observance) were never collected (142 events); windows containing such dates are missing that session and include an extra outer session; windows containing market-closed federal-business days (Good Friday, special closures) are one real session short. Flags: `flag_missing_event_day`, `flag_window_calendar_bug` on the canonical view. Repair: Phase 1c (targeted re-collection).
