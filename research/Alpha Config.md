---
tags:
  - type/implementation
  - domain/signal
  - project/src-core
  - status/complete
created: 2026-04-04
---

# Alpha Config

> **File:** `src/signals/alpha_config.py` · **Lines:** 175

## Purpose

Standalone configuration class (`AlphaDeltaConfig`) with all tunable parameters for the AlphaMomentumHawkes v5 production strategy. Covers entry gates, exit rules, dynamic refit, position sizing, and cooldown.

## Class: `AlphaDeltaConfig`

Uses `__slots__` for memory efficiency. All defaults overridable via `**kwargs`.

### Entry Gates

| Parameter | Default | Purpose |
|-----------|---------|---------|
| `catalyst_gate_pct` | 30.0 | Price must be > 30% above prev close |
| `cvd_threshold_sigma` | 2.2 | CVD velocity σ threshold |
| `alpha_min_entry` | 0.35 | Min branching ratio for entry |
| `entry_cap_pct` | 1.25 | Anti-chase: max % from base |
| `frequency_gate_mult` | 2.0 | Trade frequency ≥ 2× baseline |

### Exit Rules

| Parameter | Default | Purpose |
|-----------|---------|---------|
| `exit_blowoff_decay_pct` | 15.0 | λ decay from peak for exit |
| `exit_expectation_gap_sec` | 45.0 | No new high within 45s → exit |
| `exit_alpha_collapse` | 0.30 | α below 0.30 → hard exit |
| `reaper_time_sec` | 120.0 | 120s capital clogger kill |
| `reaper_min_pnl_pct` | 0.5 | Min PnL to survive reaper |
| `trailing_stop_pct` | 5.0 | Trailing stop -5% |
| `hard_stop_pct` | 10.0 | Hard stop -10% |
| `time_stop_sec` | 600.0 | Max hold 10 minutes |

### Dynamic Refit

| Parameter | Default | Purpose |
|-----------|---------|---------|
| `dynamic_refit_interval_sec` | 10.0 | Refit α every 10s |
| `dynamic_refit_window_sec` | 60.0 | Lookback window for refit |

## Methods

| Method | Purpose |
|--------|---------|
| `to_dict()` → dict | Serialise all params |

## Consumers
- [[V5 Backtest Runner]], [[Optimizer]], [[Signal Bakeoff]], [[GPU Batch Runner]]

---
*Back to [[Signals Index]] · [[00-Index]]*
