---
tags:
  - type/implementation
  - domain/hawkes
  - domain/signal
  - project/src-core
  - status/complete
created: 2026-04-04
---

# Intensity Gating

> **File:** `src/signals/intensity_gating.py` · **Lines:** 95

## Purpose

Identifies market regimes from event arrival intensity using Schmitt-trigger hysteresis for stable transitions. Three regimes: Quiet (0), Normal (1), High/Momentum (2).

## Class: `IntensityGater`

| Method | Signature | Purpose |
|--------|-----------|---------|
| `__init__` | `(n_iat=50, window_sec=60, quiet_pct=0.75, high_pct=0.95, hysteresis_buffer=0.1)` | Configure thresholds |
| `calculate_rolling_intensity` | `(df)` → Series | Counts-per-second rolling mean |
| `calculate_iat_intensity` | `(df)` → Series | 1/mean(IAT) rolling intensity |
| `update_regimes` | `(lambda_series, q_thresh, h_thresh)` → Series | Schmitt-trigger state machine |

## Regime Codes
| Code | Label | Percentile |
|------|-------|------------|
| 0 | Quiet | below 75th |
| 1 | Normal | 75th–95th |
| 2 | High (Momentum) | above 95th |

Hysteresis: high→normal only when below (high_pct − buffer)

## Dependencies
- **Internal:** None (standalone)
- **External:** `numpy`, `pandas`

## Consumers
- [[Rolling Pipeline]], [[Regime Hawkes Correlation]]

---
*Back to [[Signals Index]] · [[00-Index]]*
