---
tags:
  - type/implementation
  - domain/hawkes
  - domain/regime
  - project/src-core
  - status/complete
created: 2026-04-04
---

# Regime Hawkes Correlation

> **File:** `src/models/regime_hawkes_corr.py` · **Lines:** 260

## Purpose

Combines Poisson intensity-gating regimes with Hawkes process fits to compute regime-gated correlations between Hawkes intensity and forward volatility. Scans up to 250 high-momentum events, computes lead/lag cross-correlations, and generates per-event and aggregate Plotly figures.

## Functions

| Function | Signature | Purpose |
|----------|-----------|---------|
| `list_candidates` | `(base_path, min_momentum, limit)` → List[str] | Find candidate dirs |
| `compute_forward_vol` | `(log_rets, lookahead, min_ticks)` → ndarray | Forward-looking realised vol |
| `compute_xcorr` | `(a, b, lags, min_samples)` → List[float] | Cross-correlation at specified lags |
| `process_event` | `(event_dir, base_path, max_ticks, min_samples)` → dict | Full pipeline: load → gate → fit → correlate |
| `summarize_results` | `(results)` → dict | Aggregate correlation stats |
| `render_event_figure` | `(res, run_dir)` | 5-panel Plotly figure per event |
| `render_aggregate_figures` | `(results, run_dir)` | Aggregate lag correlation + histogram |
| `main` | (CLI) | Full sweep over candidates |

## Constants
- `LAGS = np.arange(-50, 51)` — 101 lag values

## Dependencies
- **Internal:** [[LULD Halt Detection]], various utility functions
- **External:** `numpy`, `pandas`, `plotly`, `argparse`

---
*Back to [[Models Index]] · [[00-Index]]*
