---
tags:
  - type/implementation
  - domain/signal
  - domain/ofi
  - project/src-core
  - status/complete
created: 2026-04-04
---

# Flow Z-Score Indicator

> **File:** `src/signals/flow_zscore_indicator.py` · **Lines:** 145

## Purpose

Volume anomaly visualization. Loads trade data, resamples to 20s OHLC bars, computes a log-space EWM Z-score of volume with 2-hour half-life, and produces dark-background candlestick + Z-score charts with regime colouring.

## Class: `FlowZScoreAnalyzer`

| Method | Purpose |
|--------|---------|
| `__init__(ticker_name, trades_df, date_filter)` | Initialise with trade data |
| `calculate_indicators()` | Compute log-volume EWM Z-score (span=360 bars ≈ 2h) |
| `plot()` | Candlestick + Z-score chart with region fills |

## Z-Score Thresholds
- ≥ 3σ: Critical (dark red)
- ≥ 2σ: Extreme (red)
- ≤ −2σ: Low activity (blue)

## Dependencies
- **Internal:** None
- **External:** `matplotlib`, `pandas`, `numpy`

---
*Back to [[Signals Index]] · [[00-Index]]*
