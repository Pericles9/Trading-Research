---
tags:
  - type/results
  - domain/data
  - project/src-core
  - status/needs-review
created: 2026-07-11
---

# DuckDB Ingestion State — Intended Design vs. Actual Reality

Read-only discovery audit. No source code, database, or data files were modified in the
course of this investigation. Verified against the live `data/duckdb/main.duckdb` file and
the current `src/data/ingest.py` / `src/data/db.py` / `src/data/paths.py` source using
DuckDB 1.5.3 (Python `duckdb` package), plus direct filesystem inspection of every source
directory referenced by the loader code.

## TOP-LINE FINDING #1 — The database has never been populated

`data/duckdb/main.duckdb` exists, but it is **completely empty**: 0 user tables, 0 user
views (only DuckDB's own internal `system` schema views are present). Confirmed three ways:
`information_schema.tables` (0 rows), `SHOW TABLES` (`[]`), and `duckdb_tables()` (0 rows).

- File size: **12,288 bytes** — the size of a bare/freshly-initialized DuckDB file with no
  data blocks, consistent with "never ingested" rather than "ingested then emptied."
- Last modified: **2026-02-28 16:15:47** (file birth time is identical — it has not been
  written to since creation).
- No other `.duckdb` file exists anywhere in the repo outside `.venv/` and `archive/`
  (confirmed via `**/*.duckdb` glob and a `find` sweep). No `MOM_DB_DATA_ROOT`,
  `MOM_DB_DATABASE_ROOT`, or `MOM_DB_DUCKDB_PATH` environment variables are set, so
  `src/data/paths.resolve_duckdb_path()` resolves to exactly this file — there is no
  alternate/shadow database being used instead.

**Consequence:** every one of the 11 documented loaders is, in the actual running system,
in a "not yet run against this database" state — regardless of how much source data exists
on disk (and for most loaders, a great deal does). `research/DuckDB Ingest.md` describes
the ingest pipeline's *design and CLI* accurately as far as loader logic goes, but it reads
as if the pipeline is an operating, populated system ("status/complete" in its frontmatter);
the actual database backing it has zero rows in zero tables. This is a documentation-implies-
production-state gap, not a code bug — the loader code itself appears intact and runnable.

## TOP-LINE FINDING #2 — `load_trade_data` does reference `data/trade_data/high_momentum`

The `trade_data` loader (`load_trade_data()` in `src/data/ingest.py`, lines 491-564) is the
only one of the 11 loaders whose actual source code touches the now-emptied
`data/trade_data/high_momentum` path. Verified directly in source:

```python
subfolders = ["batches", "by_date", "by_ticker", "enhanced", "high_momentum"]
...
for sf in subfolders:
    sf_dir = td_dir / sf                      # data/trade_data/high_momentum
    ...
    parquets = _safe_glob(sf_dir, "**/*.parquet")
    if not parquets:
        log.info(f"[{table_name}] No parquet files in {sf}/ — skipping")
        continue
```

`data/trade_data/high_momentum` is confirmed empty on disk (0 files, directory still
exists). Because `_safe_glob` returns `[]` for an empty directory rather than raising, this
sub-loader does **not** error — it silently logs "No parquet files ... — skipping" and never
creates a `trade_data_high_momentum` table. This is not a crash risk, but it is a real,
code-level dangling reference: this loader's `high_momentum` branch now points at a source
that will never again produce data, and — because the whole `trade_data` loader is
documented (both in `research/DuckDB Ingest.md` and in its own source docstring) as
`"legacy/unknown provenance"` — nobody would notice a table silently failing to materialize
unless they read the log output. Flagging per instructions; the other three empty
`trade_data` subfolders (`batches/`, `by_date/`, `by_ticker/` — all 0 parquet files) have the
same silent-skip behavior but were not named in the background brief, so they're noted here
for completeness rather than as a separate top-line item.

No other loader's source path touches `high_momentum` or any `trade_data/` subpath.

---

## 1. Intended Design (per `research/DuckDB Ingest.md` and `research/DuckDB Connection.md`)

- **Source doc:** `research/DuckDB Ingest.md`, companion to `src/data/ingest.py` (400
  lines per the doc's own header — actual file is 704 lines, see divergence note below).
  Frontmatter status: `status/complete`.
- **Connection manager doc:** `research/DuckDB Connection.md`, companion to
  `src/data/db.py`. Describes a single `get_connection()` returning a connection to
  `data/duckdb/main.duckdb`.
- **Design intent:** 11 idempotent loaders (each skips if its target table already exists),
  invoked via `python -m src.data.ingest --all|--dataset <name>|--verify-only`. The doc's
  loader table:

| Loader (doc) | Table (doc) | Source (doc) |
|---|---|---|
| `load_filtered` | `filtered_*` | `data/filtered/*/trades.parquet` |
| `load_daily` | `daily` | `data/daily/*.parquet` |
| `load_minute` | `minute` | `data/minute/**/*.parquet` |
| `load_second10` | `second10` | `data/second10/**/*.parquet` |
| `load_quote_data` | `quote_data` | `data/quote_data/*.parquet` |
| `load_momentum_events` | `momentum_events` | `data/momentum_events/*.parquet` |
| `load_metadata` | `metadata` | `data/metadata/*.json` |
| `load_market_hours` | `market_hours` | `data/market-hours/*.json` |
| `load_symbol_properties` | `symbol_properties` | `data/symbol-properties/*.csv` |
| `load_nautilus_catalog` | VIEWs | `data/nautilus_catalog/**/*.parquet` |
| `load_trade_data` | `trade_data` | `data/trade_data/*.parquet` |

## 2. Documentation-vs-Code Divergences (doc vs. actual `src/data/ingest.py`)

The doc's loader *names* and *source directories* are broadly accurate, but several
**table names** and **source-glob details** it states do not match the actual code:

| Loader | Doc says table = | Actual table(s) created | Doc says source = | Actual source (verified in code) |
|---|---|---|---|---|
| `load_filtered` | `filtered_*` | `filtered_trades`, `filtered_quotes` (two separate tables) | `data/filtered/*/trades.parquet` | Matches, but also loads `quotes.parquet` per event dir (doc doesn't mention quotes) and appends `ticker`/`event_date`/`momentum_pct` columns parsed from the folder name regex `^(TICKER)_(YYYY-MM-DD)_(mom)$` |
| `load_daily` | `daily` | `daily_bars` | `data/daily/*.parquet` | `data/daily/*_daily.parquet` (narrower pattern; matches actual filenames like `AACG_daily.parquet`) |
| `load_minute` | `minute` | `minute_bars` | `data/minute/**/*.parquet` | Not a simple recursive glob — code manually walks `data/minute/{TICKER}/*.parquet` and also handles a fallback nested layout `data/minute/{X}/{TICKER}/*.parquet`; actual on-disk layout is the flat `data/minute/{TICKER}/{date}.parquet` form |
| `load_second10` | `second10` | `second10_bars` | `data/second10/**/*.parquet` | `data/second10/{TICKER}/*.parquet` (one level, not recursive `**`); matches actual on-disk layout |
| `load_quote_data` | `quote_data` | `raw_quotes` | `data/quote_data/*.parquet` | Matches, with filename pattern `{TICKER}_quotes_{Y}_{M}_{D}.parquet` |
| `load_momentum_events` | `momentum_events` | `momentum_events` | `data/momentum_events/*.parquet` | One specific file only: `data/momentum_events/filtered_events_power_law_q05.parquet` (doc implies all parquet in the dir; actual dir has 3 other parquet/csv files not loaded) |
| `load_metadata` | `metadata` (singular) | `collection_stats`, `symbols_metadata` (two tables) | `data/metadata/*.json` | Actually reads **parquet**, not JSON: `collection_stats.parquet`, `symbols_metadata.parquet` — doc's `*.json` source pattern is wrong for this loader |
| `load_market_hours` | `market_hours` | `market_hours` | `data/market-hours/*.json` | `data/market-hours/market-hours-database.json` (specific file, matches) |
| `load_symbol_properties` | `symbol_properties` | `symbol_properties` | `data/symbol-properties/*.csv` | `data/symbol-properties/symbol-properties-database.csv` (specific file, matches) |
| `load_nautilus_catalog` | VIEWs (unnamed) | `nautilus_equity`, `nautilus_trade_tick` (named views) | `data/nautilus_catalog/**/*.parquet` | `data/nautilus_catalog/data/equity/**/*.parquet` and `data/nautilus_catalog/data/trade_tick/**/*.parquet` separately — doc collapses two distinct view sources into one glob |
| `load_trade_data` | `trade_data` (singular) | `trade_data_events` + `trade_data_{batches,by_date,by_ticker,enhanced,high_momentum}` (up to 6 tables) | `data/trade_data/*.parquet` | `data/trade_data/momentum_events_for_collection.parquet` plus 5 named subfolders walked with `**/*.parquet`; doc's single-table/single-glob description substantially understates the actual multi-table fan-out and does not mention the subfolder list at all |

Additionally, `research/DuckDB Ingest.md` states `src/data/ingest.py` is **400 lines**; the
actual file is **704 lines**. The doc has not been regenerated since a substantial expansion
of the loader code (most likely when per-subfolder handling, dual-layout minute/second10
walking, and the `trade_data` legacy loader were added).

## 3. Loader-by-Loader Actual State

All 11 loaders share the same DB-level status: **no target table or view exists** in
`data/duckdb/main.duckdb` (verified via `information_schema.tables`, `SHOW TABLES`, and
`duckdb_tables()`/`duckdb_views()` — all empty of user objects). Row counts are therefore
**0** for every loader, not because any table exists and is empty, but because ingestion
has never been executed against this database file. What differs between loaders is purely
the *on-disk source data* they would read from if `python -m src.data.ingest --all` were run.

| # | Loader | Actual source (from code) | Source exists? | Source volume (top-level count) | DB table(s) | Row count | Classification |
|---|---|---|---|---|---|---|---|
| 1 | `filtered` | `data/filtered/{TICKER}_{DATE}_{mom}/{trades,quotes}.parquet` | Yes | 29,208 event dirs (matches canonical count from background) | `filtered_trades`, `filtered_quotes` (absent) | 0 | Not ingested — source abundant & current |
| 2 | `daily` | `data/daily/*_daily.parquet` | Yes | ~1,848 files | `daily_bars` (absent) | 0 | Not ingested — source abundant |
| 3 | `minute` | `data/minute/{TICKER}/{date}.parquet` | Yes | ~3,377 ticker dirs | `minute_bars` (absent) | 0 | Not ingested — source abundant |
| 4 | `second10` | `data/second10/{TICKER}/*.parquet` | Yes | ~2,806 ticker dirs | `second10_bars` (absent) | 0 | Not ingested — source abundant |
| 5 | `quote_data` | `data/quote_data/{TICKER}_quotes_{Y}_{M}_{D}.parquet` | Yes | ~19,136 files | `raw_quotes` (absent) | 0 | Not ingested — source abundant |
| 6 | `momentum_events` | `data/momentum_events/filtered_events_power_law_q05.parquet` | Yes (single file present) | 1 target file (dir has 4 files total) | `momentum_events` (absent) | 0 | Not ingested — source present |
| 7 | `metadata` | `data/metadata/{collection_stats,symbols_metadata}.parquet` | Yes | 2 files | `collection_stats`, `symbols_metadata` (absent) | 0 | Not ingested — source present |
| 8 | `market_hours` | `data/market-hours/market-hours-database.json` | Yes | 1 file | `market_hours` (absent) | 0 | Not ingested — source present |
| 9 | `symbol_properties` | `data/symbol-properties/symbol-properties-database.csv` | Yes | 1 file | `symbol_properties` (absent) | 0 | Not ingested — source present |
| 10 | `nautilus_catalog` | `data/nautilus_catalog/data/{equity,trade_tick}/**/*.parquet` | Yes | 582 equity ticker dirs, 538 trade_tick ticker dirs | `nautilus_equity`, `nautilus_trade_tick` VIEWs (absent) | 0 | Not ingested — source abundant |
| 11 | `trade_data` | `data/trade_data/momentum_events_for_collection.parquet` + subfolders `batches/`, `by_date/`, `by_ticker/`, `enhanced/`, **`high_momentum/`** | Mixed (see below) | 1 events file (171 KB); `batches`=0, `by_date`=0, `by_ticker`=0 parquet files; `enhanced`=5 parquet files; **`high_momentum`=0 files (empty)** | `trade_data_events`, `trade_data_enhanced` would populate; `trade_data_batches`, `trade_data_by_date`, `trade_data_by_ticker`, `trade_data_high_momentum` would silently not be created | 0 | Not ingested; AND source-broken for 4 of 6 sub-targets, including `high_momentum` — see Top-Line Finding #2 |

None of the 11 loaders qualifies as "fully populated & current" or "populated but stale" —
those classifications require a table to exist. None qualifies as "not yet implemented or
stubbed" either in the sense of missing code — all 11 loader functions are fully implemented
in `src/data/ingest.py` and registered in the `LOADERS` dict. The single classification that
actually fits all 11, precisely, is: **implemented in code, source data present (in varying
completeness), but never executed against `data/duckdb/main.duckdb` — table/view absent.**
`trade_data` additionally has partially-empty source data independent of the DB question.

## 4. Other Notes

- `research/DuckDB Ingest.md` and `research/DuckDB Connection.md` both have
  `status/complete` in frontmatter and `created: 2026-04-04`. Given the database has never
  been populated as of this audit (2026-07-11) and the doc's line-count/table-name/source
  details are stale relative to current `ingest.py`, `status/complete` describes the doc's
  own completeness as a companion doc, not the operational state of the pipeline it
  describes — worth distinguishing if this doc is read as "the ingest pipeline works and is
  populated."
- `src/data/paths.py` supports overriding data/db roots via `MOM_DB_DATA_ROOT`,
  `MOM_DB_DATABASE_ROOT`, `MOM_DB_DUCKDB_PATH` env vars — none were set in this shell
  session, so all resolution fell through to repo defaults (`data/` and
  `data/duckdb/main.duckdb`). If ingestion were previously run under a different env-var
  configuration (e.g. pointing at an external drive), that database was not found anywhere
  searched in this repo.
- No `.wal` (write-ahead log) file was found alongside `main.duckdb`, consistent with a
  cleanly-closed, unwritten database rather than an interrupted ingest.
- `data/trade_data/rebuild_validation_sample/` exists on disk but is not referenced by any
  loader in `src/data/ingest.py` — not a divergence in the sense of "broken," just dead/unused
  from the ingest pipeline's perspective.

---
*Read-only discovery audit. Source: `src/data/ingest.py`, `src/data/db.py`,
`src/data/paths.py`, `data/duckdb/main.duckdb` (DuckDB 1.5.3), filesystem inspection of
`data/*`. See also [[DuckDB Ingest]], [[DuckDB Connection]].*
