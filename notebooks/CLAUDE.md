# notebooks/

## Purpose

Jupyter notebooks for exploratory data analysis, signal development, and visualization.
These are research and investigation tools — not production code. Results explored here
are eventually formalized into `src/` modules or documented in `research/`.

## Key Files

| Notebook | Purpose |
|----------|---------|
| `Hawkes.ipynb` | Hawkes process exploration and kernel visualization |
| `Univariate_Kernel_Hawkes.ipynb` | Single-dimension Hawkes analysis |
| `Signal_Lab_Report.ipynb` | Signal filter comparison (Kalman, SWT, CUSUM, FracDiff) |
| `Regime_Analysis.ipynb` | Regime detection and validation |
| `Intensity_Gating.ipynb` | Schmitt-trigger intensity gating exploration |
| `Flow_Z-Score_Indicator.ipynb` | Volume anomaly detection |
| `Analysis_Rolling_Hawkes.ipynb` | Rolling window Hawkes analysis |
| `Poisson_Intensity_Gate.ipynb` | Poisson intensity gating |
| `Power_Law_Audit.ipynb` | Power-law distribution validation for event catalog |
| `Lead-Lag of Intent.ipynb` | Lead-lag correlation analysis |

## Relevant Tags

- `type/research`, `type/results`
- `domain/hawkes`, `domain/signal`, `domain/regime`, `domain/backtest`
- `project/src-core`, `project/v5-strategy`

## Conventions

- Notebooks are for exploration only — do not use them as source-of-truth for production logic
- Any reusable function developed in a notebook should be extracted to `src/` before use
- Keep notebooks self-contained: import from `src/` rather than copying code in

## Notes

- No companion docs required for notebooks — their purpose is usually self-evident from
  the title and inline markdown cells
- Notebooks may reference parquet files in `data/` or `research/phase_*/` — these are
  off-limits for direct read; use DuckDB via `src/data/db.py` instead
- `notebooks/` is not git-tracked for outputs — clear outputs before committing
