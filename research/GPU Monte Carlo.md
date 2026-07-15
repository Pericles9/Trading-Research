---
tags:
  - type/implementation
  - domain/backtest
  - domain/gpu
  - project/src-core
  - status/complete
created: 2026-04-04
---

# GPU Monte Carlo

> **File:** `src/backtest/analytics/gpu_monte_carlo.py` · **Lines:** 320

## Purpose

GPU-Accelerated 10,000-path Monte Carlo equity curve simulation. Uses CuPy (primary) or PyTorch (fallback) for massively parallel shuffled permutations. No serial Python loops.

## Functions

| Function | Purpose |
|----------|---------|
| `gpu_monte_carlo_fixed(trade_pnl, ...)` | 10k-path MC with fixed position sizing |
| `gpu_monte_carlo_kelly(trade_pnl, ...)` | 10k-path MC with rolling Kelly sizing |
| `compute_risk_of_ruin(max_drawdowns, threshold)` | Fraction of paths hitting ruin threshold |
| `compute_drawdown_durations(equity_curve)` | Duration array for each drawdown episode |

## Implementation
- **CuPy** path: `cupy.random.permutation` → cumulative sum → drawdown
- **PyTorch fallback**: `torch.randperm` on CUDA → same pipeline

## Dependencies
- **Internal:** None
- **External:** `cupy` (optional), `torch`, `numpy`

---
*Back to [[Backtest Index]] · [[00-Index]]*
