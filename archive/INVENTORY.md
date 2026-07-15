---
tags:
  - type/reference
  - project/vault
  - status/complete
created: 2026-04-04
---
# Archive Inventory

> Auto-generated catalog of archived run artifacts and misc files.
> These outputs are **read-only historical records** — the code that produced them
> now lives under `src/`.

## Run Artifacts (`archive/runs/`)

| Directory | Files | Size (MB) | Contents | Produced By |
|-----------|-------|-----------|----------|-------------|
| `bivariate_kernel_hawkes/` | 36 | 49 | Fitted intensities (.npy), kernel weight plots (.html/.png), fit diagnostics (.json) | `src/models/hawkes_engine.py` (BivariateHawkesEngine) |
| `gpu_audit/` | 2 | 0.5 | GPU vs CPU parity audit (.parquet) | `src/backtest/gpu_batch_runner.py` |
| `luld_preview/` | 1 | 5 | LULD halt preview report (.html) | `src/data/luld_halt_detection.py` |
| `multivariate_hawkes/` | 50 | 16 | MHP rolling analysis: causality matrices (.json), Granger plots (.png/.html), IRF (.csv) | `src/models/` MHP subsystem |
| `research_notebook_runs/` | 339 | 1287 | Full research pipeline outputs per symbol-day: intensity plots (.html/.png), fitted params (.npy), feature matrices (.parquet) | Notebooks → research phases 1-4 |
| `signal_lab/` | 200 | 34 | Signal filter comparison: ROC curves (.png), noise spectra (.npy), bakeoff summaries (.txt/.json) | `src/backtest/signal_bakeoff.py` |
| `stat_validation/` | 40 | 104 | Statistical validation: KS/AD test results (.json), regime transition matrices (.png), validated feature sets (.parquet) | `src/backtest/stat_validator.py` |
| `v53_temporal_beta/` | 5 | 1 | v5.3 temporal-beta sweep configs and results (.json) | `src/backtest/v5_runner.py` |
| `v5_battle/` | 12 | 2 | v5 head-to-head battle configs, PnL curves (.json) | `src/backtest/v5_runner.py` + `optimizer.py` |

**Total:** ~685 artifacts, ~1.5 GB

## Misc Files (`archive/misc/`)

| File | Description |
|------|-------------|
| `final_lead_lag_config.json` | Best lead-lag regression hyperparams |
| `kelly_audit_events.json` | Kelly criterion audit event log |
| `retail_audit_events.json` | Retail impact audit event log |
| `stat_validator.py` | Standalone copy of stat validation (canonical: `src/backtest/stat_validator.py`) |
| `quick_select_momentum.py` | One-off momentum event selector |
| `select_high_momentum_events.py` | One-off high-momentum event filter |
| `tps_opt.db` | SQLite DB from TPS optimization sweep |
| `smoke_test_10.log` | 10-symbol smoke test log |
| `Signal_Lab_Report_*.png` | Signal lab report screenshots (3 files) |
| `*_flow_zscore.png` | Flow z-score indicator example plots (3 files) |
| `newplot.png` | One-off Plotly export |

## Related

- [[Archive Inventory]] — human-readable research vault index for this archive
