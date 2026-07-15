---
tags:
  - type/results
  - domain/data
  - project/vault
  - status/complete
created: 2026-07-12
---

# Full D: Migration — T1: Inventory

D: total used ≈ 355.6GB (matches D:'s ~362.8GB used minus ~7GB of
OS-managed content — `$RECYCLE.BIN`, `System Volume Information` — not
touched by this migration).

## Top-level breakdown

| Path | Size | Status |
|---|---|---|
| `D:\Trading Research\data\filtered` | 183.11 GB | **Already on E:**, verified (47,615/47,615 files, exact byte match + content spot-check) |
| `D:\Trading Research\data\quote_data` | 27.10 GB | **Already on E:**, 19,127/19,136 verified good; 7 files need re-copy (source confirmed fine), 2 files unrecoverable anywhere (`POLA_quotes_2020_11_23`, `RR_quotes_2024_09_23`) |
| `D:\Trading Research\scanner-epg-momentum` | 65.34 GB | **Never backed up** |
| `D:\archived\old_projects` | 55.89 GB | **Never backed up** |
| `D:\Trading Research\hawkes-ofi-impact` | 10.13 GB | **Never backed up** |
| `D:\Trading Research\.venv` | 5.23 GB | **Never backed up** — but regenerable (`pip install -r requirements.txt`), not irreplaceable data (see note below) |
| `D:\Trading Research\data\second10` | 1.21 GB | **Never backed up** (candle data, out of ingestion scope but still source data) |
| `D:\Trading Research\archive` | 1.46 GB | **Never backed up** |
| `D:\PostgreSQL` | 1.23 GB | **Special case — see below, not a simple copy candidate** |
| `D:\Trading Research\data\nautilus_catalog` | 1.00 GB | **Never backed up** |
| `D:\archived\legacy_system` | 0.96 GB | **Never backed up** |
| `D:\Trading Research\data\trade_data` | 0.79 GB | **Never backed up** |
| `D:\Trading Research\data\minute` | 0.75 GB | **Never backed up** (candle data) |
| `D:\Mom. DB failed 11-21-25` | 0.64 GB | **Never backed up** — old, separate failed project (its own `.venv`/`src`/`data`), not part of the active vault |
| `D:\Trading Research\notebooks` | 0.52 GB | **Never backed up** |
| `D:\Trading Research\data\illiquid_tests` | 0.03 GB | **Never backed up** |
| `D:\Trading Research\data\daily` | 0.02 GB | **Never backed up** (candle data) |
| `D:\Trading Research\research` | 0.02 GB | **Never backed up** |
| `D:\Trading Research\data\audit_reports` | 0.01 GB | **Never backed up** |
| `D:\Trading Research\data\collection_scripts` | 0.01 GB | **Never backed up** |
| `D:\Trading Research\results` | 0.01 GB | **Never backed up** (includes this investigation's own output files) |
| `D:\archived\archived_scripts` | 0.01 GB | **Never backed up** |
| Everything else (`.claude`, `.github`, `.obsidian`, `.pytest_cache`, `.vscode`, `__pycache__`, `inbox`, `logs`, `prompts`, `src`, `tests`, `data/{raw,metadata,symbol-properties,duckdb,momentum_events,market-hours,processed,features}`, `PropertyVISUALSTUDIO2017FOLDER`) | ~0 GB combined | Never backed up, negligible size |

## Special case: `D:\PostgreSQL`

**8 `postgres.exe` processes are currently running** — this is a *live*
database data directory, not static files. A raw file copy (robocopy,
`Copy-Item`) of a running PostgreSQL data directory does not produce a
consistent, restorable backup — WAL segments and in-progress writes mean
the copied files could be internally inconsistent, and worse, would create
a **false sense of security**: "it's backed up" for data that isn't
actually safely captured. Proper backup needs `pg_dump`/`pg_basebackup`, or
stopping the service first. **Excluded from this migration pass** — needs
its own explicit decision, not a default file copy. Flagged, not silently
skipped.

## Never-backed-up total

**≈145.3 GB** (144.0GB of straightforward file content + 1.23GB PostgreSQL,
excluded pending its own decision). This is the priority-one migration
target per T2 — it's the sole point of failure for this data if D:
degrades further before migration completes.

## Note on `.venv` (5.23GB)

Included in the "never backed up" figure above since the task asked for
the entire contents of D:, but flagging explicitly: this is a regenerable
Python virtual environment (`pip install -r requirements.txt` recreates
it), not irreplaceable data. Migrating it costs real time against a
this-session-limited I/O budget on a degrading drive for content that
isn't actually at risk of permanent loss. Included in T3's migration queue,
but placed last in priority order — see T2.
