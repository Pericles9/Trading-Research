---
tags:
  - type/implementation
  - domain/backtest
  - domain/microstructure
  - project/src-core
  - status/complete
created: 2026-04-04
---

# Retail Impact

> **File:** `src/backtest/analytics/retail_impact.py` · **Lines:** 310

## Purpose

Spread-centric retail transaction cost model. Models TC as the max of half-spread and square-root market impact. Includes capital ladder ($5k / $25k / $100k), liquidity constraint, and capacity ceiling estimation.

## Math

$$TC_{total} = \max\!\left(\frac{\text{Spread}}{2},\; Y \cdot \sigma \cdot \sqrt{\frac{Q}{V}}\right) + \text{SEC fee} + \text{FINRA TAF}$$

## Functions

| Function | Signature | Purpose |
|----------|-----------|---------|
| `compute_retail_tc` | `(spread_pct, sigma, position_dollars, ...)` | Single trade TC |
| `scale_pnl_for_capital` | `(raw_pnl, spreads, ...)` | Apply round-trip TC to PnL array |
| `build_capital_ladder` | `(..., capitals)` | Multi-capital comparison |
| `estimate_capacity_ceiling` | `(..., baseline_sharpe)` | Max account before Sharpe degrades > 30% |

## Constants

| Constant | Value | Purpose |
|----------|-------|---------|
| `Y_IMPACT` | 0.10 | Kyle's lambda proxy |
| `LIQUIDITY_CAP` | 0.05 | Q ≤ 5% of 1-min volume |
| `SEC_FEE_PER_DOLLAR` | 8e-6 | SEC fee rate |
| `FINRA_TAF` | 0.000166 | FINRA TAF rate |

## Dependencies
- **Internal:** None
- **External:** `numpy`

---
*Back to [[Backtest Index]] · [[00-Index]]*
