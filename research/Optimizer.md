---
tags:
  - type/implementation
  - domain/backtest
  - project/src-core
  - status/complete
created: 2026-04-04
---

# Optimizer

> **File:** `src/backtest/optimizer.py` · **Lines:** 310

## Purpose

AlphaMomentumHawkes v4 self-optimization loop (3-iteration feedback). 6 scenario-analysis rules diagnose backtest results and adjust config parameters automatically.

## Diagnostic Rules

| Scenario | Adjustment |
|----------|------------|
| HIGH_MAE | Increase `cvd_threshold_sigma` |
| LOW_PCR | Decrease patience (quicker exits) |
| LOW_WINRATE | Increase `alpha_slope_lookback_sec` |
| HIGH_CHURN | Increase cooldown |
| OVER_TRADING | Reduce `max_entries` |
| LATE_ENTRIES | Tighten `entry_cap_pct` |

## Tuning Ranges

| Parameter | Min | Max |
|-----------|-----|-----|
| `cvd_threshold_sigma` | 1.5 | 3.0 |
| `alpha_slope_lookback_sec` | 0.5 | 2.0 |
| `hold_patience_factor` | 0.5 | 2.0 |

## Key Functions

| Function | Purpose |
|----------|---------|
| `_diagnose_and_adjust(results, config)` | Rule engine |
| `optimize(event_name, ...)` | Single-event 3-iter optimization |
| `optimize_batch(event_names, ...)` | Portfolio-level optimization |

## Dependencies
- **Internal:** [[V5 Backtest Runner]], [[Alpha Config]], [[Excursion V1]]
- **External:** `numpy`, `json`, `argparse`

---
*Back to [[Backtest Index]] · [[00-Index]]*
