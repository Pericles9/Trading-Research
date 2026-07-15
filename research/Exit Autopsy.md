---
tags:
  - type/implementation
  - domain/backtest
  - project/src-core
  - status/complete
created: 2026-04-04
---

# Exit Autopsy

> **File:** `src/backtest/analytics/exit_autopsy.py` · **Lines:** 440

## Purpose

Premature-exit diagnostic. Quantifies exit quality: **Gain Sacrifice** (money left on table within 5 min post-exit), **Intensity SNR**, **Price-Near-High** detection.

## Hypothesis Under Test

> "≥80% of premature exits (Gain Sacrifice > 0.5%) are PEAK_DECAY while price is within 0.5% of high."

## Key Metrics

| Metric | Definition |
|--------|------------|
| Gain Sacrifice (GS) | MFE in 300s post-exit minus exit PnL |
| Intensity SNR | mean/std ratio of λ\_buy in 2s window around exit |
| Price-Near-High | Exit within 0.5% of position MFE |

## Functions

| Function | Purpose |
|----------|---------|
| `autopsy_trade(entry, exit_trade, ...)` | Single trade autopsy |
| `run_autopsy(runs_dir)` | Batch autopsy across all runs |

## Dependencies
- **Internal:** None (loads run data from JSON)
- **External:** `pandas`, `numpy`, `json`, `pathlib`

---
*Back to [[Backtest Index]] · [[00-Index]]*
