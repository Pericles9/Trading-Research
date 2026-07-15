---
tags:
  - type/implementation
  - domain/backtest
  - project/src-core
  - status/complete
created: 2026-04-04
---

# Excursion V2

> **File:** `src/backtest/analytics/excursion_v2.py` · **Lines:** 530

## Purpose

Post-trade excursion & diagnostic analysis v2. Adds **Toxic Entry Report** (K-Means clustering), **Branching Ratio correlation**, and **Auto-Threshold Suggestions** for filtering bottom-PCR quartile.

## Toxic Entry Clustering

Uses K-Means on normalised features:
- `[MAE, MFE, roc_30s, vd_60s, intensity_imbalance]`
- Labels clusters as TOXIC / NEUTRAL / BEST based on median PCR

## Auto-Threshold Suggestions
Identifies the worst-performing quartile and proposes new entry gate thresholds to filter them out.

## Functions

| Function | Purpose |
|----------|---------|
| `compute_excursions(...)` → DataFrame | 30+ columns of per-trade metrics |
| `identify_toxic_entries(exc_df, n_clusters)` | K-Means TOXIC/NEUTRAL/BEST labeling |
| `suggest_entry_thresholds(exc_df)` | Auto-threshold proposals |
| `generate_diagnostic_report(exc_df, ...)` | 8-panel Plotly HTML |

## Dependencies
- **Internal:** None
- **External:** `pandas`, `numpy`, `sklearn`, `plotly`

---
*Back to [[Backtest Index]] · [[00-Index]]*
