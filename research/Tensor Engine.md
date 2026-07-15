---
tags:
  - type/implementation
  - domain/hawkes
  - domain/gpu
  - project/src-core
  - status/complete
created: 2026-04-04
---

# Tensor Engine

> **File:** `src/models/tensor_engine.py` · **Lines:** 355
> **Status:** GPU-only — requires CUDA

## Purpose

GPU-Tensor Hawkes Engine using an **associative-scan** (Blelloch prefix-scan) to vectorise the exponential decay recursion across CUDA warps. Provides vectorised intensity computation, branching ratio, cross-stream resampling, VRAM batching, trade-level signals (CVD, VWAP, MFE/MAE), slippage stress-test, Monte Carlo equity paths, and session classification.

## Math

Associative scan identity:

$$(a_1, b_1) \oplus (a_2, b_2) = (a_1 \cdot a_2, \; a_2 \cdot b_1 + b_2)$$

where $a_i = e^{-\beta \cdot \Delta t_i}$ and $b_i = 1$, yielding $R_i$ via prefix scan in $O(N \log N)$ parallel work.

## Functions

| Function | Signature | Purpose |
|----------|-----------|---------|
| `build_beta_bank_tensor` | `(dt_avg_sec, n_kernels, device)` → Tensor | Log-spaced β bank on CUDA |
| `associative_scan_hawkes` | `(dt, betas, ts_scale)` → Tensor(B,K,N) | Blelloch up-sweep/down-sweep scan |
| `compute_intensity_tensor` | `(R_self, R_cross, mu, alpha_self, alpha_cross)` → Tensor(B,N) | Vectorised $\lambda(t) = \mu + \sum \alpha \cdot R$ |
| `compute_branching_ratio` | `(alpha_self, alpha_cross, betas)` → Tensor | $n = \sum(\alpha/\beta)$, clamped ≤ 0.99 |
| `resample_cross_features` | `(R_source, t_source, t_target)` → Tensor | Cross-stream R via searchsorted |
| `estimate_vram_bytes` | `(n_events, n_kernels, max_ticks)` → int | VRAM memory estimate |
| `compute_batch_size` | `(n_kernels, max_ticks, vram_fraction, device)` → int | Safe batch size (80% VRAM) |
| `compute_cvd_tensor` | `(signed_volume, mask)` → Tensor | Cumulative Volume Delta on GPU |
| `compute_vwap_tensor` | `(price, volume, window, mask)` → Tensor | Rolling VWAP via 1D conv |
| `compute_mfe_mae_tensor` | `(entry_prices, price_series, entry_ticks, exit_ticks)` → (MFE, MAE) | Per-trade excursion on GPU |
| `slippage_stress_test` | `(theoretical_pnl, slippage_bps_range, avg_trades)` → Tensor | PnL decay vs slippage |
| `monte_carlo_equity_paths` | `(trade_pnl, n_paths)` → Tensor | Random-order equity curves |
| `classify_sessions_tensor` | `(t_sec)` → Tensor(int32) | 5-session intraday classification |

## Constants
- `SESSION_LABELS = ["Pre-market", "Morning", "Mid-day", "Afternoon", "Post-market"]`
- Session boundaries: 4:00, 9:30, 11:30, 14:00, 16:00, 20:00

## Dependencies
- **Internal:** None (standalone)
- **External:** `numpy`, `torch`, `torch.nn.functional`

## Consumers
- [[GPU Batch Runner]]

---
*Back to [[Models Index]] · [[00-Index]]*
