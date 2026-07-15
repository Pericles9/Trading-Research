---
tags:
  - type/implementation
  - domain/backtest
  - project/src-core
  - status/complete
created: 2026-04-04
---

# Trade Analyzer

> **File:** `src/backtest/analytics/trade_analyzer.py` · **Lines:** 340

## Purpose

Polars-based trade analyzer for deep excursion & efficiency metrics. **All aggregation uses `group_by`/`agg` — zero for-loops.**

## Metric Categories

### Excursion Profile
- MAE, MFE, MAE/MFE ratio, Recovery Factor (`recovered_pnl / abs(MAE)`)

### Time & Profit Efficiency
- TTP (Time to Peak): seconds from entry to MFE
- Profit Velocity: PnL / hold_duration
- Capital Cloggers: trades > 120s with < 0.5% PnL

### Statistical Robustness
- Expectancy: $E = \frac{\sum \text{PnL}}{N}$
- Profit Factor: $PF = \frac{\sum \text{wins}}{\sum |\text{losses}|}$
- SQN (System Quality Number): $SQN = \frac{E}{\sigma_{PnL}} \cdot \sqrt{N}$

## Functions

| Function | Purpose |
|----------|---------|
| `build_trade_frame(summaries)` → pl.DataFrame | One row per round-trip |
| `enrich_with_excursions(df, rows)` | Join excursion data |
| `compute_excursion_profile(df)` | MAE/MFE/recovery stats |
| `compute_efficiency_metrics(df)` | TTP/velocity/clogger stats |
| `compute_statistical_robustness(df)` | Expectancy/PF/SQN |
| `duration_heatmap(df)` | WR by duration bucket |
| `archetype_heatmap(df)` | WR by archetype |
| `full_analysis(df)` | All metrics → single dict |

## Dependencies
- **Internal:** None
- **External:** `polars`, `numpy`, `math`

## Consumers
- [[Stat Validator]]

---
*Back to [[Backtest Index]] · [[00-Index]]*
