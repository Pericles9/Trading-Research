---
tags:
  - type/implementation
  - domain/signal
  - project/src-core
  - status/complete
created: 2026-04-04
---

# Signal Processor

> **File:** `src/signals/signal_processor.py` · **Lines:** 462

## Purpose

Four-mode structural alpha filter with hot-swappable backends for both entry (CVD/Volume) and exit (Hawkes Intensity) channels. Each mode provides `filtered_value`, `innovation`, and `triggered` state.

## Modes

### A — Kalman-Bucy (`KalmanFilter`)
Local level + drift state-space model with adaptive observation noise R.

$$x_t = \begin{bmatrix} \text{level} \\ \text{drift} \end{bmatrix}, \quad F = \begin{bmatrix} 1 & 1 \\ 0 & 1 \end{bmatrix}$$

- **Trigger:** Innovation > `trigger_sigma` × √(S)
- **Defaults:** q_state=1.0, q_drift=0.01, r_obs=5.0, trigger_sigma=2.0

### B — SWT (`SWTFilter`)
Online Haar wavelet decomposition with soft thresholding.
- Buffer of 2^level samples, Haar decompose, soft-threshold detail coefficients, reconstruct
- **Trigger:** df/dx > `deriv_sigma` × σ(derivative)
- **Defaults:** level_depth=4, threshold_factor=1.5, deriv_sigma=2.0

### C — CUSUM (`CUSUMFilter`)
Two-sided CUSUM for mean-shift detection with rolling baseline.

$$S^+_t = \max(0, S^+_{t-1} + x_t - \bar{x} - \delta)$$
$$S^-_t = \max(0, S^-_{t-1} - x_t + \bar{x} - \delta)$$

- **Trigger:** $S^+ > h$ or $S^- > h$ where $h = h\_sigma \times \sigma$
- **Defaults:** baseline_window=500, delta=1.0, h_sigma=4.0

### D — FracDiff (`FracDiffFilter`)
Fixed-window fractional differencing (López de Prado).

$$\tilde{x}_t = \sum_{k=0}^{K} w_k \cdot x_{t-k}, \quad w_k = -w_{k-1} \cdot \frac{d - k + 1}{k}$$

- **Trigger:** z-score of $\tilde{x}$ exceeds `z_sigma`
- **Defaults:** d=0.45, max_window=500, z_sigma=2.0

## Class: `SignalProcessor`

| Method | Purpose |
|--------|---------|
| `__init__(mode, entry_kwargs, exit_kwargs)` | Create entry + exit filter pair |
| `reset()` | Reset both filters |
| `entry_filter` / `exit_filter` | Direct access to filter objects |

## Batch Helper

```python
filtered, innovations, triggers = batch_filter(raw, mode="kalman", timestamps=None, **kwargs)
```

## Dependencies
- **Internal:** None (standalone)
- **External:** `numpy`, `math`, `abc`, `collections.deque`, `enum`

## Consumers
- [[Signal Bakeoff]], [[V5 Backtest Runner]]

---
*Back to [[Signals Index]] · [[00-Index]]*
