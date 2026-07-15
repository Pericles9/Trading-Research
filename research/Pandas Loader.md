---
tags:
  - type/implementation
  - domain/data
  - project/src-core
  - status/complete
created: 2026-04-04
---

# Pandas Loader

> **File:** `src/data/pandas_loader.py` · **Lines:** 200
> **Status:** Legacy — prefer [[Polars Loader]] for new code

## Purpose

Original Pandas-based data loader. Reads filtered parquet data, performs Lee-Ready classification via `pd.merge_asof`, removes LULD halts via `prepare_active_trades`.

## Functions

| Function | Purpose |
|----------|---------|
| `load_trades_and_quotes(folder)` → (trades, quotes) | Load parquet pair |
| `classify_trades_lee_ready(trades, quotes)` → DataFrame | Lee-Ready via merge_asof |
| `load_and_classify(base_path, event_dir)` → (merged, meta) | Full load + classify |
| `select_candidate(data_path, ...)` → (name, data) | Pick event + LULD filter |
| `list_events(data_path, momentum_threshold)` | Event discovery |

## Dependencies
- **Internal:** [[LULD Halt Detection]]
- **External:** `pandas`, `numpy`

## Consumers
- [[V2 Backtest Runner]], [[Archetype Backtest Runner]], [[MHP Data Loader]]

---
*Back to [[Data Index]] · [[00-Index]]*
