---
tags:
  - type/implementation
  - domain/hawkes
  - domain/gpu
  - project/src-core
  - status/complete
created: 2026-04-04
---

# GPU Accelerated MHP

> **File:** `src/models/gpu_accelerated_mhp.py` · **Lines:** 285

## Purpose

GPU-accelerated rolling MHP with O(N) recursive NLL computation via a JIT-compiled kernel, memory-optimal batched sliding-window fitting with AMP mixed-precision, and gradient clipping. Designed for high-throughput batch processing.

## Class: `RollingHawkesGPU(nn.Module)`

| Method | Signature | Purpose |
|--------|-----------|---------|
| `prepare_batch` | `(events, window_starts, window_size, history_horizon)` → 5 Tensors | Merge/sort events into padded batch |
| `batch_log_likelihood` | `(mu, alpha, dt, types, is_event, target_mask, ...)` → Tensor | NLL for batch via recursive JIT |
| `fit_batch` | `(events, window_starts_np, window_size, init_params, epochs, lr)` → (Tensor, Tensor) | One batch with warm-start |

## Key Functions

| Function | Purpose |
|----------|---------|
| `compute_recursive_nll_jit` | JIT-compiled recursive NLL log-sum |
| `run_rolling_analysis_gpu` | End-to-end rolling GPU analysis pipeline |

## Constants
- Branching ratio penalty threshold: 0.95
- Gradient clip max_norm: 1.0
- Default batch_size: 64

## Dependencies
- **Internal:** None
- **External:** `torch`, `numpy`, `pandas`

## Consumers
- [[Rolling Pipeline]]

---
*Back to [[Models Index]] · [[00-Index]]*
