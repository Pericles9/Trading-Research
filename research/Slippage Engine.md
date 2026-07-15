---
tags:
  - type/implementation
  - domain/microstructure
  - domain/backtest
  - project/src-core
  - status/complete
created: 2026-04-04
---

# Slippage Engine

> **File:** `src/backtest/slippage_engine.py` · **Lines:** 170

## Purpose

L1 quote-based fill simulation for realistic slippage modeling. Simulates execution against top-of-book quotes with configurable market impact.

## Class: `SlippageEngine` (dataclass)

| Field | Default | Purpose |
|-------|---------|---------|
| `ask_price` | — | Current best ask |
| `bid_price` | — | Current best bid |
| `ask_size` | — | Ask depth |
| `bid_size` | — | Bid depth |
| `impact_bps_per_lot` | 2.0 | Price impact per 100 shares |

| Method | Purpose |
|--------|---------|
| `fill_buy(shares)` → float | Simulated buy fill price |
| `fill_sell(shares)` → float | Simulated sell fill price |
| `spread_at()` → float | Current spread |
| `compute_slippage_pnl(entry, exit, shares)` → float | Round-trip slippage cost |

## Top-Level Functions

| Function | Purpose |
|----------|---------|
| `aggregate_slippage(fill_records)` | Batch stats: theoretical vs quote-fill PnL, avg/median/p90 slippage |

## Dependencies
- **Internal:** None
- **External:** `numpy`, `dataclasses`

---
*Back to [[Backtest Index]] · [[00-Index]]*
