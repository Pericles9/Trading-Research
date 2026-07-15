---
tags:
  - type/results
  - domain/signal
  - project/src-core
  - status/complete
created: 2026-04-04
---

# Phase 4 — Campaign

> **Scripts:** `research/phase_4_campaign/build_campaign.py` (serial, 1102 lines) and `build_campaign_hpc.py` (HPC, 1060 lines)
> **Outputs:** `prime_candidates.parquet`, `scored_universe.parquet`

## Purpose

Regime-aware backtesting: scores all events via XGBoost, runs a 3-way "Bake-Off" (Baseline vs Filtered vs Campaign), generates equity curve and performance report.

## Bake-Off Strategies

### Baseline
- Trade every event, 2×ATR stop, FIFO exit

### Filtered
- Same logic restricted to **top-25%** by XGBoost score

### Campaign
- **Vector Check:** Price > VWAP AND CVD > 0
- **Elastic Leash:** 3.5×ATR stop (high score) vs 1.5×ATR (low score)
- **Pyramiding:** +50% at +2% if rank #1
- Adjusted Hawkes β based on regime score

## HPC vs Serial

| Feature | Serial | HPC |
|---------|--------|-----|
| Inference | Python loop | Single DMatrix batch |
| Simulation | Sequential | `joblib.Parallel` across all cores |
| Kernels | Python loops | `@njit` Numba (zero iterrows) |
| Data loading | Per-event `os.listdir` | Pre-built directory index |
| Target | Minutes | < 60 seconds |

## HPC Numba Kernels

| Function | Purpose |
|----------|---------|
| `_hawkes_intensity_vec` | Vectorised Hawkes intensity |
| `_cvd_tick_rule` | Tick-rule CVD |
| `_running_vwap` | Rolling VWAP |
| `_atr_from_bars` | ATR from bar data |
| `_sim_baseline` / `_sim_campaign` | Pure-numba strategy simulation |

## Outputs

| File | Purpose |
|------|---------|
| `prime_candidates.parquet` | Top-25% filtered universe |
| `scored_universe.parquet` | All events with XGBoost scores |
| `Campaign_Report.md` | Performance comparison report |
| `plots/performance_comparison.png` | Equity curves |
| `plots/drawdown_comparison.png` | Drawdown comparison |
| `plots/score_vs_return.png` | Score vs realised return |

## Artifacts

- [[Campaign_Report]] — performance comparison report (Baseline vs Filtered vs Campaign)

## Data Sources
- [[Phase 3 — Alpha Hunter|xgb_regime_model.json + fused_dataset.parquet]]
- `data/filtered/*/trades.parquet`

---
*Back to [[00-Index]]*
