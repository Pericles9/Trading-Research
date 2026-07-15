---
tags:
  - type/results
  - domain/signal
  - project/src-core
  - status/complete
created: 2026-04-04
---

# Phase 2 — Signal Forge

> **Scripts:** `research/phase_2_signal_forge/build_signal_forge.py` (v1, 856 lines) and `build_signal_forge_v2.py` (v2, 1201 lines)
> **Outputs:** `feature_matrix_v1.parquet` (22 features), `feature_matrix_v2_ext.parquet` (36 features)

## Purpose

Transform raw tick-level trades/quotes into a feature matrix of stochastic momentum signals. v1 covers the FLIP window only (09:30–09:45 ET); v2 extends to full-day (04:00–16:00 ET) with halt-stitched Hawkes intensity.

## v1 Pipeline

1. Normalize prices via $\phi$ (adjusted open / first RTH trade)
2. Regime tag (PRE / FLIP / STD)
3. Per-event feature extraction: Hawkes intensity & acceleration, CVD & convexity, OFI
4. Top-10 anatomy plots + heatmap
5. Assemble 22-column feature matrix

## v2 Additions

| Feature | Description |
|---------|-------------|
| Halt-stitched Hawkes | Freezes decay state $S$ during gaps > 5s (no phantom decay) |
| Full-day CVD | Continuous CVD across 09:30 transition |
| CVD convexity at transition | Savitzky-Golay 2nd derivative at 09:25–09:35 window |
| LULD features | `is_post_halt`, `n_halts`, `max_halt_duration_sec`, `hawkes_post_halt_surge` |
| Per-regime stats | Hawkes mean/std for pre, flip, RTH, fullday regimes |

## Key Numba JIT Functions

| Function | Purpose |
|----------|---------|
| `_hawkes_scan()` | Hawkes recurrence via Numba |
| `_hawkes_scan_halt_aware()` (v2) | Halt-aware Hawkes with frozen state |
| `_tick_rule_cvd()` | Tick rule CVD computation |
| `_ofi_kernel()` | Order Flow Imbalance kernel |

## Outputs — Feature Matrix v2 (36 columns)

Key features include: `hawkes_mean_flip`, `hawkes_max_flip`, `hawkes_acceleration_flip`, `cvd_convexity_flip`, `ofi_agg_flip`, `pre_market_gap_pct`, `pre_market_rvol`, `is_post_halt`, `n_halts`, `hawkes_post_halt_surge`, `seconds_since_unhalt`, plus per-regime Hawkes statistics.

## Artifacts

- [[MANIFEST]] — data provenance for this phase
- [[Forge_Audit_Log]] — v1 audit log
- [[Forge_Audit_Log_v2]] — v2 revised audit log
- [[SIGNAL_DICTIONARY]] — v1 feature definitions
- [[SIGNAL_DICTIONARY_v2]] — v2 extended feature definitions

## Data Sources
- [[Phase 1 — Scanner Context|scanner_context.parquet]]
- `data/filtered/*/trades.parquet` and `quotes.parquet`

## Consumers
- [[Phase 3 — Alpha Hunter]]

---
*Back to [[00-Index]]*
