---
tags:
  - type/implementation
  - domain/backtest
  - project/v5-strategy
  - status/complete
created: 2026-04-04
---

# V2 Backtest Runner

> **File:** `src/backtest/v2_runner.py` · **Lines:** 480

## Purpose

Reactive-Momentum Hawkes v2 backtest runner with auto-tuning loop. Supports `catalog` mode (Nautilus BacktestEngine) and `event` mode (tick-by-tick simulation). Post-run auto-tuning adjusts parameters if avg PCR < 0.3 or avg MAE > −5%.

## Entry Paths
1. **Velocity impulse fast-path** — bypass catalyst if velocity sustained
2. **σ-spike catalyst** + 3-gate confirmation (same as [[Bivariate Strategy]])

## Exit Triggers
- `PEAK_DECAY`, `SELL_DOM`, `TIME_STOP`

## Auto-Tune Rules
- If avg PCR < 0.3 → decrease `exit_peak_decay_pct`
- If avg MAE > −5% → increase `exit_time_stop_sec`

## Dependencies
- **Internal:** [[Hawkes Engine]], [[Bivariate Strategy]], [[Pandas Loader]]
- **External:** `numpy`, `plotly`, `json`, `argparse`

---
*Back to [[Backtest Index]] · [[00-Index]]*
