---
tags:
  - type/implementation
  - domain/hawkes
  - project/src-core
  - status/complete
created: 2026-04-04
---

# MHP Model

> **File:** `src/models/mhp_model.py` · **Lines:** 261

## Purpose

Core D-dimensional Multivariate Hawkes Process with exponential kernels, implementing conditional intensity computation, MLE fitting, simulation via Ogata's thinning algorithm, and windowed log-likelihood for rolling estimation.

## Math

$$\lambda_m(t) = \mu_m + \sum_{n=1}^{D} \sum_{t_j^n < t} \alpha_{mn} \cdot \beta \cdot e^{-\beta(t - t_j^n)}$$

Log-likelihood:

$$\log \mathcal{L} = \sum_m \left[ \sum_i \log \lambda_m(t_i^m) - \int_0^T \lambda_m(s) \, ds \right]$$

Branching ratio: $n^* = \max \text{eigenvalue}(\alpha / \beta)$, clamped ≤ 0.99.

## Class: `MultivariateHawkes(nn.Module)`

| Method | Signature | Purpose |
|--------|-----------|---------|
| `forward` | `(t, events)` → Tensor | Compute $\lambda(t)$ at time $t$ |
| `compute_log_likelihood` | `(events, T)` → Tensor | Full-window log-likelihood |
| `fit` | `(events, T, epochs=500, lr=0.01)` → dict | MLE fitting via Adam |
| `get_parameters` | `()` → (μ, α, β) | Return numpy arrays |
| `branching_ratio` | `()` → float | Max branching ratio |
| `simulate` | `(T, max_events, seed)` → List[ndarray] | Ogata thinning simulation |
| `compute_window_log_likelihood` | `(window_events, history, T_start, T_end)` → Tensor | Windowed LL with history |
| `fit_window` | `(window_events, history, T_start, T_end, epochs, lr)` → float | Fit one window |

## Dependencies
- **Internal:** None
- **External:** `numpy`, `torch`, `torch.nn`

## Consumers
- [[Rolling Hawkes Engine]], [[GPU Accelerated MHP]], [[MHP Analysis]]

---
*Back to [[Models Index]] · [[00-Index]]*
