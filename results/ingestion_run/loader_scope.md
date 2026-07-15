---
tags:
  - type/results
  - domain/data
  - project/src-core
  - status/complete
created: 2026-07-11
---

# DuckDB Ingestion — T2 Loader Scope Classification

All 11 loaders registered in `src/data/ingest.py`'s `LOADERS` dict, classified.

| # | Loader key | Source dir | Table(s) produced | Classification | Reason |
|---|---|---|---|---|---|
| 1 | `filtered` | `data/filtered/` | `filtered_trades`, `filtered_quotes` | **In scope** | Trades + quotes, both freshly verified/fixed this session |
| 2 | `daily` | `data/daily/` | `daily_bars` | Deferred | Candle — structural cleanup not landed |
| 3 | `minute` | `data/minute/` | `minute_bars` | Deferred | Candle — structural cleanup not landed |
| 4 | `second10` | `data/second10/` | `second10_bars` | Deferred | Candle — structural cleanup not landed |
| 5 | `quote_data` | `data/quote_data/` | `raw_quotes` | **In scope** | Full single-session quote corpus, 19,136 files, verified clean minus 4 known-corrupted (V0.0b) |
| 6 | `momentum_events` | `data/momentum_events/` | `momentum_events` | Out of scope | Source file predates 2025 gap-fill; missing ~7,252 events now in `filtered/`; regeneration-and-diff phase pending review |
| 7 | `metadata` | `data/metadata/` | `collection_stats`, `symbols_metadata` | **In scope** | Two small reference parquet files, no candle/staleness concerns |
| 8 | `market_hours` | `data/market-hours/` | `market_hours` | Deferred | Not named anywhere in this task's objective/T6/reporting; excluded per prior narrow-scope decision |
| 9 | `symbol_properties` | `data/symbol-properties/` | `symbol_properties` | Deferred | Same as above |
| 10 | `nautilus_catalog` | `data/nautilus_catalog/` | `nautilus_equity`, `nautilus_trade_tick` (VIEWs) | Deferred | Same as above |
| 11 | `trade_data` | `data/trade_data/` | `trade_data_events`, `trade_data_enhanced` | Deferred | Same as above; code itself flags "PROVENANCE UNKNOWN — review before using in production" |

**In-scope loaders for this run: `filtered`, `quote_data`, `metadata` (3 of 11).**

`illiquid_tests/` (named in the task's context as out-of-scope) does not
correspond to any of the 11 registered loaders — it has no loader at all, so
there's nothing to defer; noted for completeness.

## Note on `momentum_events` vs. this task's Objective line

The Objective paragraph lists `momentum_events` among the tables to ingest,
but the Context section explicitly excludes it with detailed reasoning
(source-file staleness) and instructs "exclude all of them" (candle-related
+ `momentum_events`). Treating Context as authoritative, consistent with the
same resolution reached earlier in this task's first pass.
