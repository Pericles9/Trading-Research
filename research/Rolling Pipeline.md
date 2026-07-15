---
tags:
  - type/implementation
  - domain/hawkes
  - project/src-core
  - status/complete
created: 2026-04-04
---

# Rolling Pipeline

> **File:** `src/models/rolling_pipeline.py` · **Lines:** 131

## Purpose

CLI pipeline integrating [[Intensity Gating]] with [[GPU Accelerated MHP|GPU-Accelerated MHP]] fitting. Loads trade/quote data, identifies momentum regime blocks (regime 2), runs `run_rolling_analysis_gpu` on each block, and exports parameter time-series CSV + heatmap plots.

## Functions

| Function | Purpose |
|----------|---------|
| `plot_parameter_heatmap(df_results, output_path)` | Seaborn heatmap of α evolution over time |
| `main()` | Full pipeline: load → gate → fit → export |

## CLI

```bash
python -m src.models.rolling_pipeline --candidate TICKER_DATE_MAG \
    --data_path data/filtered --window_beta_mult 3 --step_overlap 0.25 --beta 20
```

## Dependencies
- **Internal:** [[MHP Data Loader]], [[Intensity Gating]], [[GPU Accelerated MHP]]
- **External:** `pandas`, `numpy`, `torch`, `matplotlib`, `seaborn`, `argparse`

---
*Back to [[Models Index]] · [[00-Index]]*
