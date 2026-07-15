---
tags:
  - type/implementation
  - domain/hawkes
  - project/src-core
  - status/complete
created: 2026-04-04
---

# Rolling Hawkes Engine

> **File:** `src/models/RollingHawkesEngine.py` · **Lines:** 128

## Purpose

Rolling-window MHP estimation engine that runs a sliding window over event streams, fitting [[MHP Model|MultivariateHawkes]] with warm-start parameters at each step. Captures non-stationary dynamics with configurable overlap and optional regime masking.

## Class: `RollingHawkesEngine`

| Method | Signature | Purpose |
|--------|-----------|---------|
| `__init__` | `(beta=20.0, step_size_ratio=0.25)` | 75% default overlap |
| `fit_rolling_mhp` | `(events, regime_mask, timestamps_full, epochs_per_window=50)` → DataFrame | Fit MHP on rolling windows, returns parameter time-series |

## Constants
- History horizon: $3.0 / \beta$ (95% of kernel integral)
- Default step_size_ratio: 0.25 (75% overlap)
- Min events per window: 5

## Dependencies
- **Internal:** [[MHP Model]] (`MultivariateHawkes`)
- **External:** `numpy`, `pandas`, `torch`

## Consumers
- [[Rolling Pipeline]]

---
*Back to [[Models Index]] · [[00-Index]]*
