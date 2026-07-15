---
tags:
  - type/implementation
  - domain/data
  - project/src-core
  - status/complete
created: 2026-04-04
---

# DuckDB Ingest

> **File:** `src/data/ingest.py` · **Lines:** 686

## Purpose

DuckDB data ingest pipeline. Loads 11 dataset types from parquet/CSV/JSON into DuckDB tables. Each loader is idempotent (skips if table exists).

## Loaders

| Loader | Table | Source |
|--------|-------|--------|
| `load_filtered` | `filtered_*` | `data/filtered/*/trades.parquet` |
| `load_daily` | `daily` | `data/daily/*.parquet` |
| `load_minute` | `minute` | `data/minute/**/*.parquet` |
| `load_second10` | `second10` | `data/second10/**/*.parquet` |
| `load_quote_data` | `quote_data` | `data/quote_data/*.parquet` |
| `load_momentum_events` | `momentum_events` | `data/momentum_events/filtered_events_power_law_q05.parquet` (one specific curated file, not all parquet in the dir — see note below) |
| `load_metadata` | `collection_stats`, `symbols_metadata` | `data/metadata/collection_stats.parquet`, `data/metadata/symbols_metadata.parquet` |
| `load_market_hours` | `market_hours` | `data/market-hours/*.json` |
| `load_symbol_properties` | `symbol_properties` | `data/symbol-properties/*.csv` |
| `load_nautilus_catalog` | VIEWs | `data/nautilus_catalog/**/*.parquet` |
| `load_trade_data` | `trade_data_events` + `trade_data_enhanced` | `data/trade_data/momentum_events_for_collection.parquet` + `data/trade_data/enhanced/**/*.parquet` — see note below |

**`load_momentum_events` note:** `data/momentum_events/` also holds
`filtered_events_power_law_q05.csv` (redundant export of the parquet, not
loaded), `momentum_scan_2025.parquet`, and
`full_2020_2024_momentum_scan_20251122_000515.parquet`. Investigated
2026-07-11: the two `*_scan_*` files are raw scan-candidate outputs (used
elsewhere in this project as a `momentum_pct` lookup source when migrating
trade data into `filtered/`), not the curated event table this loader is
meant to produce — `filtered_events_power_law_q05.parquet` has zero row
overlap with `momentum_scan_2025.parquet` and only partial overlap with the
2020-2024 scan, confirming it's a distinct, purpose-built filtered subset,
not "the same data missing 3 files." Loading only it is intentional and
correct. Separately worth knowing: this curated file predates (Jan 2026) the
2025 gap-fill and `minute/trades/` migrations completed since, so it does not
cover ~7,252 of the 30,511+ events now in `filtered/` — a data-freshness
question for whoever regenerates it, not a loader bug.

**`load_trade_data` note:** Investigated 2026-07-11. The subfolder list was
`["batches", "by_date", "by_ticker", "enhanced", "high_momentum"]`; four of
five were confirmed empty (0 parquet files) — `high_momentum` because the
trades-corpus cleanup emptied it, the other three for unrelated, unknown
reasons predating that cleanup. Reduced to `["enhanced"]`, the only subfolder
with data. `data/trade_data/rebuild_validation_sample/` (58 parquet files)
was found but deliberately not added — it substantially duplicates data
already loaded via `load_filtered`, and whether staging/validation output
belongs in a permanent table is left as an open question rather than decided
here. This loader's own code docstring still flags the whole dataset
`"legacy/unknown provenance"` — that has not changed.

## CLI

```bash
python -m src.data.ingest --all              # Load everything
python -m src.data.ingest --dataset filtered  # Load one dataset
python -m src.data.ingest --verify-only       # Print table inventory
```

## Dependencies
- **Internal:** [[DuckDB Connection]]
- **External:** `duckdb`, `pandas`, `argparse`, `json`, `logging`

---
*Back to [[Data Index]] · [[00-Index]]*
