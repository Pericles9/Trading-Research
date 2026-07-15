---
tags:
  - type/implementation
  - domain/hawkes
  - project/src-core
  - status/complete
created: 2026-04-04
---

# MHP Analysis

> **File:** `src/models/analysis.py` · **Lines:** 280

## Purpose

Analysis module for fitted MHP models providing Granger-style causality analysis, impulse response function (IRF) plotting, interaction matrix heatmaps, fitted intensity visualisation, and result serialisation. Uses Plotly for interactive figures.

## Math — Impulse Response Function

$$\Delta\lambda_m(t) = \alpha_{mn} \cdot \beta \cdot e^{-\beta t}$$

## Functions

| Function | Signature | Purpose |
|----------|-----------|---------|
| `analyze_causality` | `(model, labels)` → dict | Granger-style directional causality from α matrix |
| `plot_impulse_response` | `(model, max_time, labels, save_path)` → Figure | IRF plot per stream pair |
| `plot_interaction_matrix` | `(model, labels, save_path)` → Figure | Heatmap of α interaction matrix |
| `plot_fitted_intensities` | `(model, events, T, max_points, labels, save_path)` → Figure | Fitted λ(t) with event rug plots |
| `save_results` | `(results, model, save_dir)` | Serialise parameters + causality to JSON |

## Dependencies
- **Internal:** None (takes model as argument)
- **External:** `numpy`, `plotly`, `pandas`, `json`, `torch`

---
*Back to [[Models Index]] · [[00-Index]]*
