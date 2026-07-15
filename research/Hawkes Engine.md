---
tags:
  - type/implementation
  - domain/hawkes
  - project/src-core
  - status/complete
created: 2026-04-04
---

# Hawkes Engine

> **File:** `src/models/hawkes_engine.py` · **Lines:** 546
> **Status:** ★ Core — production-grade bivariate Hawkes intensity engine

## Purpose

Bivariate Kernel Hawkes Engine providing both **batch** (torch-accelerated) and **online** (numpy, tick-by-tick) interfaces for bivariate Hawkes intensity estimation. Used for research/walk-forward calibration and inside Nautilus strategies.

## Math

Conditional intensity for stream $m \in \{buy, sell\}$:

$$\lambda_m(t) = \mu_m + \sum_{k=1}^{K} \alpha_{m,self}^{(k)} R_{m}^{(k)}(t) + \sum_{k=1}^{K} \alpha_{m,cross}^{(k)} R_{\bar{m}}^{(k)}(t)$$

where the recursive feature:

$$R^{(k)}_i = 1 + e^{-\beta_k \cdot \Delta t} \cdot R^{(k)}_{i-1}$$

## Classes

### `_OnlineStreamState` (dataclass)
Incremental recursive features for one buy/sell stream.
- `update(t, betas, ts_scale)` — register new event, update R-state with exponential decay

### `IntensityTracker`
Rolling window tracker for $\lambda_{buy}$ / $\lambda_{sell}$ with percentile queries, hysteresis peak tracking, Welford O(1) stats, EMA damping, frozen baseline, and velocity ($d\lambda/dt$) tracking.

| Method | Purpose |
|--------|---------|
| `push(lam_buy, lam_sell, timestamp)` | Push new intensity observation |
| `buy_percentile(value)` → float | Percentile rank of value |
| `buy_in_top_pctile(value, top_pct)` → bool | Is value in top N%? |
| `buy_sigma_spike(value, k)` → bool | Is value > μ + kσ? |
| `freeze_baseline()` | Snapshot current stats as baseline |
| `velocity_impulse(k, consecutive)` → bool | Detect velocity spike |
| `peak_start(current_lam_buy)` | Begin peak tracking |
| `peak_decay_pct(current_lam_buy)` → float | Decay from peak (%) |

Constants: capacity=1000, EMA α=0.2, peak confirm=3

### `BivariateHawkesEngine`
Unified bivariate Hawkes intensity engine with batch fitting, walk-forward, and online incremental inference.

| Method | Purpose |
|--------|---------|
| `fit_batch(t_buy, t_sell, steps, lr, l1_ratio)` → dict | Full batch ElasticNet fitting |
| `walk_forward_batch(...)` → dict | Walk-forward with rolling windows |
| `reset_online()` | Clear online state |
| `online_update(timestamp, side)` | Process single trade tick |
| `online_intensity()` → (λ_buy, λ_sell) | Current intensity pair |
| `branching_snapshot()` → dict | Current branching ratios |

## Key Functions

| Function | Signature | Purpose |
|----------|-----------|---------|
| `build_beta_bank` | `(dt_avg_sec, num=7)` → ndarray | Log-spaced decay-rate bank |
| `compute_recursive_features_torch` | `(arrival_times, betas, ts_scale, dev)` → Tensor | Batch R computation on GPU |
| `sample_features_at_timestamps` | `(R_source, source_times, query_times)` → Tensor | Cross-stream R via searchsorted |

## Dependencies
- **Internal:** None (standalone)
- **External:** `numpy`, `torch`, `collections.deque`, `dataclasses`

## Consumers
- [[Archetype Classifier]], [[Archetype Injector]], [[Bivariate Strategy]], [[Archetype Strategy]]
- [[V5 Backtest Runner]], [[V2 Backtest Runner]], [[Archetype Backtest Runner]]
- [[Signal Bakeoff]], [[GPU Batch Runner]]

## Planned Extension — Event-Time Mode

> See [[Scanner-Hawkes-OFI Impact]] for full specification.

At high TPS (>300 trades/sec), clock-time decay `exp(-β · dt_sec)` degenerates — `dt_sec → 0` so decay → 1 and recursive features become trade counters. Planned fix: add `time_mode="event"` where `decay = exp(-β_event)` is applied **per-event** (constant, independent of arrival rate). Requires a new `build_event_beta_bank()` helper and a `time_mode` branch in `_OnlineStreamState.update()` and `compute_recursive_features_torch()`.

---
*Back to [[Models Index]] · [[00-Index]]*
