---
tags:
  - type/implementation
  - domain/hawkes
  - domain/data
  - project/src-core
  - status/complete
created: 2026-04-04
---

# MHP Data Loader

> **File:** `src/models/data_loader.py` · **Lines:** 213

## Purpose

Data loading and preparation module for MHP. Constructs bivariate event streams (Stream 0: trade arrivals, Stream 1: volatility spikes) from parquet trade/quote data. Includes data cleaning, rolling volatility spike detection, and high-momentum candidate discovery.

## Functions

| Function | Signature | Purpose |
|----------|-----------|---------|
| `prepare_bivariate_data` | `(df_trades, df_quotes, vol_threshold=1.5, rolling_window=50, max_trades, ts_scale=1e-9, use_quote_volatility)` → (List[ndarray], dict) | Build [trade_times, vol_spike_times] in seconds + metadata |
| `load_data_from_dir` | `(base_path, event_dir, clean_trades, max_trades)` → (DataFrame, DataFrame) | Load trades.parquet + quotes.parquet |
| `get_high_momentum_candidates` | `(base_path, min_momentum, require_both)` → List[str] | Find candidate dirs with momentum ≥ threshold |

## Constants
- Default ts_scale: 1e-9 (nanoseconds → seconds)
- Vol spike: rolling_vol > mean + vol_threshold × std
- Trade cleaning: remove bottom 10% by size

## Dependencies
- **Internal:** None
- **External:** `numpy`, `pandas`, `pathlib`

## Consumers
- [[Rolling Pipeline]], [[Regime Hawkes Correlation]]

---
*Back to [[Models Index]] · [[00-Index]]*
