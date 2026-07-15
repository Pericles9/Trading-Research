---
tags:
  - type/implementation
  - domain/backtest
  - project/src-core
  - status/complete
created: 2026-04-04
---

# Excursion V1

> **File:** `src/backtest/analytics/excursion_v1.py` · **Lines:** 250

## Purpose

Excursion Analytics v1 — MFE/MAE/PCR computation for round-trip trades.

## Math

$$PCR = \frac{\text{realized PnL}}{\text{MFE in trade}}, \quad \text{clamped to } [-1, 1]$$

$$\text{Gain Sacrifice} = \text{MFE} - \text{realized PnL}$$

## Functions

| Function | Purpose |
|----------|---------|
| `_pair_entries_exits(trades_log)` | Pair ENTRY/EXIT into round-trips |
| `compute_excursions(trades_log, t_sec, price, ...)` | Per-trade MFE, MAE, PCR, gain sacrifice |
| `aggregate_excursions(exc_list)` | Summary stats (total PnL, win rate, avg PCR) |
| `_trigger_breakdown(exc_list)` | Stats by exit trigger |
| `_entry_type_breakdown(exc_list)` | Stats by entry type |

## Outputs
- CSV: per-trade excursion data
- JSON: aggregate summary

## Dependencies
- **Internal:** None
- **External:** `numpy`, `pathlib`, `logging`

## Consumers
- [[Optimizer]], [[Stat Validator]]

---
*Back to [[Backtest Index]] · [[00-Index]]*
