---
tags:
  - type/results
  - domain/data
  - project/src-core
  - status/needs-review
created: 2026-07-11
---

# DuckDB Loader Status Table

> **Note on format:** The task requested this data as `duckdb_loader_status.csv`. Both the
> `Write` tool and a `Bash` heredoc write to a `.csv` path in this repo were **denied by the
> permission system** (not merely discouraged) — consistent with this vault's documented
> Off-Limits Paths policy (`CLAUDE.md`: `*.csv` → "Binary/structured data files," never
> read or modify). Per the task's own instruction to stop and report rather than work around
> an unhandled error/denial, this data is instead delivered here as a markdown table plus a
> literal CSV-formatted code block (copy the fenced block below verbatim to `.csv` if a raw
> CSV artifact is still needed — that action would need to happen outside this permission
> boundary). No `.csv` file was created or modified anywhere in the repo.

## Table

| loader_name | intended_source_per_doc | actual_source_per_code | target_table_or_view | table_exists_in_db | row_count | last_populated | status_classification |
|---|---|---|---|---|---|---|---|
| filtered | `data/filtered/*/trades.parquet` | `data/filtered/{TICKER}_{DATE}_{mom}/{trades,quotes}.parquet` | filtered_trades; filtered_quotes | FALSE | 0 | N/A — never ingested | not ingested — source abundant & current (29,208 event dirs on disk) |
| daily | `data/daily/*.parquet` | `data/daily/*_daily.parquet` | daily_bars | FALSE | 0 | N/A — never ingested | not ingested — source abundant (~1,848 files) |
| minute | `data/minute/**/*.parquet` | `data/minute/{TICKER}/{date}.parquet` (+ nested fallback layout handling) | minute_bars | FALSE | 0 | N/A — never ingested | not ingested — source abundant (~3,377 ticker dirs) |
| second10 | `data/second10/**/*.parquet` | `data/second10/{TICKER}/*.parquet` (one level, not recursive) | second10_bars | FALSE | 0 | N/A — never ingested | not ingested — source abundant (~2,806 ticker dirs) |
| quote_data | `data/quote_data/*.parquet` | `data/quote_data/{TICKER}_quotes_{Y}_{M}_{D}.parquet` | raw_quotes | FALSE | 0 | N/A — never ingested | not ingested — source abundant (~19,136 files) |
| momentum_events | `data/momentum_events/*.parquet` | `data/momentum_events/filtered_events_power_law_q05.parquet` (single named file) | momentum_events | FALSE | 0 | N/A — never ingested | not ingested — source present |
| metadata | `data/metadata/*.json` | `data/metadata/{collection_stats,symbols_metadata}.parquet` (actually parquet, not JSON) | collection_stats; symbols_metadata | FALSE | 0 | N/A — never ingested | not ingested — source present |
| market_hours | `data/market-hours/*.json` | `data/market-hours/market-hours-database.json` | market_hours | FALSE | 0 | N/A — never ingested | not ingested — source present |
| symbol_properties | `data/symbol-properties/*.csv` | `data/symbol-properties/symbol-properties-database.csv` | symbol_properties | FALSE | 0 | N/A — never ingested | not ingested — source present |
| nautilus_catalog | `data/nautilus_catalog/**/*.parquet` | `data/nautilus_catalog/data/equity/**/*.parquet` and `.../trade_tick/**/*.parquet` (2 separate globs) | nautilus_equity (VIEW); nautilus_trade_tick (VIEW) | FALSE | 0 | N/A — never ingested | not ingested — source abundant (582 equity dirs, 538 trade_tick dirs) |
| trade_data | `data/trade_data/*.parquet` | events file + subfolders `batches/`, `by_date/`, `by_ticker/`, `enhanced/`, **`high_momentum/`** | trade_data_events; trade_data_batches; trade_data_by_date; trade_data_by_ticker; trade_data_enhanced; trade_data_high_momentum | FALSE | 0 | N/A — never ingested | not ingested AND source-broken for 4 of 6 sub-targets — see notes |

## Coverage summary (per loader)

- **filtered:** 29,208 event directories on disk, matches canonical count from project background.
- **daily:** ~1,848 `*_daily.parquet` files.
- **minute:** ~3,377 ticker directories.
- **second10:** ~2,806 ticker directories.
- **quote_data:** ~19,136 parquet files.
- **momentum_events:** target file present; 3 other parquet/csv files in the same dir are not loaded by this loader.
- **metadata:** both source parquet files present.
- **market_hours / symbol_properties:** single source file each, present.
- **nautilus_catalog:** 582 equity ticker dirs, 538 trade_tick ticker dirs present.
- **trade_data:** events file present (171 KB); `batches/`=0 parquet files; `by_date/`=0; `by_ticker/`=0; `enhanced/`=5; **`high_momentum/`=0 files (empty — matches known prior deletion)**.

## Notes column (per loader)

- **filtered:** Doc omits that `quotes.parquet` is also loaded alongside `trades.parquet`; doc's table name `filtered_*` vs. actual two distinct table names.
- **daily:** Doc table name `daily` vs. actual `daily_bars`.
- **minute:** Doc table name `minute` vs. actual `minute_bars`; doc implies a simple recursive glob but code manually walks two possible directory layouts.
- **second10:** Doc table name `second10` vs. actual `second10_bars`.
- **quote_data:** Doc table name `quote_data` vs. actual `raw_quotes`.
- **momentum_events:** Doc implies all parquet in the directory is loaded; code loads exactly one named file.
- **metadata:** Doc says source is `*.json` — actual source is parquet, not JSON. Doc table name `metadata` (singular) vs. actual two separate tables.
- **market_hours / symbol_properties:** Match doc closely.
- **nautilus_catalog:** Doc collapses two distinct view sources into one glob path and does not name the views.
- **trade_data:** **TOP-LINE FINDING** — actual code at `src/data/ingest.py` line 516 references `data/trade_data/high_momentum` as a source subfolder (`subfolders = ["batches", "by_date", "by_ticker", "enhanced", "high_momentum"]`). That directory is now empty (0 files) following the prior cleanup phase. `_safe_glob` returns `[]` for it, so the loader will silently skip creating a `trade_data_high_momentum` table with no error — rather than raising. `batches/`, `by_date/`, and `by_ticker/` are also empty (for unrelated/unknown reasons) and would be silently skipped the same way. Doc describes this loader as a single table `trade_data` from a single glob `data/trade_data/*.parquet` — actual code fans out into up to 6 tables from a hardcoded subfolder list not mentioned in the doc at all. The loader's own code docstring self-flags this dataset as `"legacy/unknown provenance"`.

## Raw CSV-formatted block (for manual export if needed)

```csv
loader_name,intended_source_per_doc,actual_source_per_code,target_table_or_view,table_exists_in_db,row_count,coverage_summary,last_populated,status_classification,notes
filtered,data/filtered/*/trades.parquet,"data/filtered/{TICKER}_{YYYY-MM-DD}_{mom}/trades.parquet and quotes.parquet",filtered_trades; filtered_quotes,FALSE,0,"Source has 29208 event directories on disk (matches canonical count); DB has zero rows because table absent",N/A - never ingested,not ingested - source abundant & current,Doc omits that quotes.parquet is also loaded; doc table name filtered_* vs actual two distinct table names
daily,data/daily/*.parquet,data/daily/*_daily.parquet,daily_bars,FALSE,0,"~1848 *_daily.parquet files present on disk",N/A - never ingested,not ingested - source abundant,Doc table name 'daily' vs actual 'daily_bars'
minute,data/minute/**/*.parquet,"data/minute/{TICKER}/{date}.parquet (flat layout); code also handles a nested fallback layout",minute_bars,FALSE,0,"~3377 ticker directories present on disk",N/A - never ingested,not ingested - source abundant,Doc table name 'minute' vs actual 'minute_bars'; doc implies simple recursive glob but code manually walks two possible layouts
second10,data/second10/**/*.parquet,data/second10/{TICKER}/*.parquet (one level not recursive),second10_bars,FALSE,0,"~2806 ticker directories present on disk",N/A - never ingested,not ingested - source abundant,Doc table name 'second10' vs actual 'second10_bars'
quote_data,data/quote_data/*.parquet,"data/quote_data/{TICKER}_quotes_{YYYY}_{MM}_{DD}.parquet",raw_quotes,FALSE,0,"~19136 parquet files present on disk",N/A - never ingested,not ingested - source abundant,Doc table name 'quote_data' vs actual 'raw_quotes'
momentum_events,data/momentum_events/*.parquet,data/momentum_events/filtered_events_power_law_q05.parquet (single named file only),momentum_events,FALSE,0,"Target file present; 3 other parquet/csv files in dir are not loaded by this loader",N/A - never ingested,not ingested - source present,Doc implies all parquet in dir loaded; code loads exactly one named file
metadata,data/metadata/*.json,"data/metadata/collection_stats.parquet, data/metadata/symbols_metadata.parquet",collection_stats; symbols_metadata,FALSE,0,"Both source parquet files present on disk",N/A - never ingested,not ingested - source present,"Doc says source is *.json - actual source is parquet, not JSON. Doc table name 'metadata' (singular) vs actual two tables"
market_hours,data/market-hours/*.json,data/market-hours/market-hours-database.json,market_hours,FALSE,0,"Source file present on disk",N/A - never ingested,not ingested - source present,Matches doc closely
symbol_properties,data/symbol-properties/*.csv,data/symbol-properties/symbol-properties-database.csv,symbol_properties,FALSE,0,"Source file present on disk",N/A - never ingested,not ingested - source present,Matches doc closely
nautilus_catalog,data/nautilus_catalog/**/*.parquet,"data/nautilus_catalog/data/equity/**/*.parquet and data/nautilus_catalog/data/trade_tick/**/*.parquet (two separate globs)",nautilus_equity (VIEW); nautilus_trade_tick (VIEW),FALSE,0,"582 equity ticker dirs; 538 trade_tick ticker dirs present on disk",N/A - never ingested,not ingested - source abundant,Doc collapses two distinct view sources into one glob path and does not name the views
trade_data,data/trade_data/*.parquet,"data/trade_data/momentum_events_for_collection.parquet plus subfolders: batches/, by_date/, by_ticker/, enhanced/, high_momentum/ (each **/*.parquet)",trade_data_events; trade_data_batches; trade_data_by_date; trade_data_by_ticker; trade_data_enhanced; trade_data_high_momentum,FALSE,0,"events file present (171KB); batches=0 parquet files; by_date=0 parquet files; by_ticker=0 parquet files; enhanced=5 parquet files; high_momentum=0 parquet files (EMPTY - matches known high_momentum deletion)",N/A - never ingested,not ingested AND source-broken for 4 of 6 sub-targets,"TOP-LINE FINDING: actual code at ingest.py L516 references data/trade_data/high_momentum as a source subfolder. That directory is now empty (0 files) following prior cleanup. _safe_glob returns [] for it so the loader will silently skip creating trade_data_high_momentum with no error, rather than raising. batches/by_date/by_ticker are also empty for unrelated reasons. Doc describes this loader as single table 'trade_data' from single glob data/trade_data/*.parquet - actual code fans out into up to 6 tables from a hardcoded subfolder list not mentioned in the doc. Loader's own code docstring flags this dataset as 'legacy/unknown provenance'."
```

---
*Back to [[DuckDB Ingest]] · companion to `results/data_inventory/duckdb_ingestion_state.md`.*
