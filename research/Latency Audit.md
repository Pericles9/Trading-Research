---
tags:
  - type/implementation
  - domain/backtest
  - project/src-core
  - status/complete
created: 2026-04-04
---

# Latency Audit

> **File:** `src/backtest/analytics/latency_audit.py` · **Lines:** 430

## Purpose

Phase 1 Forensic Latency Audit. For each entry: finds burst bottom (5s lookback), burst peak (30s lookahead), computes latency, range position (0=bottom, 1=peak), acceleration (2nd derivative), volume impulse ratio. Identifies logic leaks: ROC delay, α confirmation bias, deceleration at entry.

## Functions

| Function | Purpose |
|----------|---------|
| `find_burst_bottom(t_sec, price, entry_time, lookback)` | Local min in 5s lookback |
| `find_burst_peak(t_sec, price, entry_time, lookahead)` | Local max in 30s lookahead |
| `compute_acceleration_at_entry(...)` | 2nd derivative of price |
| `detect_volume_impulse(...)` | 500ms buy volume spike vs 60s baseline |
| `run_latency_audit(run_dir, event_name, ...)` | Full audit pipeline |

## Outputs
- Plotly scatter: Entry vs Burst Peak positions

## Dependencies
- **Internal:** [[Polars Loader]]
- **External:** `numpy`, `plotly`, `json`

---
*Back to [[Backtest Index]] · [[00-Index]]*
