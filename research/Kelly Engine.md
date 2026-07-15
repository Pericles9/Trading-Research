---
tags:
  - type/implementation
  - domain/backtest
  - project/src-core
  - status/complete
created: 2026-04-04
---

# Kelly Engine

> **File:** `src/backtest/analytics/kelly_engine.py` · **Lines:** 320

## Purpose

Rolling Kelly Criterion position sizing engine. Implements Half-Kelly with 20% max cap. Builds equity curves for both Kelly and fixed sizing. Go/No-Go report card.

## Math

$$f^* = \frac{p \cdot b - q}{b}$$

where $p$ = win rate, $b$ = avg win / avg loss, $q = 1 - p$.

**Half-Kelly:** $f = \frac{f^*}{2}$, capped at 20%.

## Functions

| Function | Purpose |
|----------|---------|
| `compute_kelly_fraction(pnl_history, ...)` | Single Kelly f* computation |
| `build_kelly_equity_curve(trade_pnl, lookback, ...)` | Rolling Half-Kelly equity curve + stats |
| `build_fixed_equity_curve(trade_pnl, ...)` | Fixed-size equity curve |
| `monte_carlo_kelly(trade_pnl, n_paths, ...)` | 1k-path MC with Kelly |
| `monte_carlo_fixed(trade_pnl, n_paths, ...)` | GPU MC with fixed sizing |
| `kelly_vs_fixed_report(trade_pnl, ...)` | Go/No-Go comparison |

## Dependencies
- **Internal:** None
- **External:** `numpy`, `torch`

---
*Back to [[Backtest Index]] · [[00-Index]]*
