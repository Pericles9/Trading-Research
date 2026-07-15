---
tags:
  - type/pipeline
  - domain/signal
  - project/src-core
  - status/complete
created: 2026-04-04
---

# AlphaMomentum Phase 2 – Signal Forge MANIFEST

## Project Overview
**Name:** AlphaMomentum_Phase2_SignalForge  
**Objective:** Transform raw tick-level trades and quotes into a GPU-accelerated
feature matrix of stochastic momentum signals, bridging the split-adjusted gap
between event history and raw market data.

**Build Status: COMPLETE (v2 REVISED — Extended Signal Forge)**

---

## v2 REVISED — Extended Signal Forge

### What Changed
- **Full-day timeline** (04:00–16:00 ET) instead of FLIP-only Hawkes/CVD
- **Halt-stitched Hawkes kernel**: S frozen during gaps > 5s (no phantom decay)
- **Genuine LULD halt detection** at 300s threshold for halt context features
- **CVD Convexity at 09:30 transition** ("Elbow" window: 09:25–09:35)
- **15 new features** (37 total columns) including halt context
- **4-panel anatomy plots** with halt zones, full-day Hawkes, micro-zoom
- **Proof chart**: HALT_RUNNER_TPST_2023-10-11.png (41 LULD halts, λ surge 881.9)

### v2 Results Summary

| Metric | v1 | v2 |
|---|---|---|
| Events forged | 2,820 | 2,816 |
| Feature columns | 22 | **37** |
| Timeline | FLIP only | **04:00–16:00** |
| Hawkes kernel | Standard | **Halt-stitched** |
| Events with LULD halts | N/A | **1,067 (37.9%)** |
| Anatomy plots | 10 (3-panel) | **12 (4-panel) + proof chart** |
| Execution time | 358s | **653s** |
| Errors | 0 | 0 |

---

## v1 Results Summary (Legacy)

| Metric | Value |
|---|---|
| Scanner events (Phase 1 input) | 4,549 |
| Events with filtered tick data | 2,967 |
| **Successfully forged** | **2,820** |
| Normalization outliers (excluded) | 147 |
| Hawkes features computed | 2,624 (93.0%) |
| OFI features computed | 2,683 (95.1%) |
| PM context features computed | 2,596 (92.1%) |
| Anatomy plots generated | 10 |
| Heatmap events | 30 |
| Total execution time | 358s |
| Peak GPU memory | ~50 MB |

---

## Pipeline Architecture

```
scanner_context.parquet (Phase 1: 4,549 events)
         │
         ▼
┌─────────────────────────┐
│ 1. NORMALIZATION LAYER  │  φ = Price_Adj,Open / Price_Raw,FirstTrade
│    Split-fix all raw     │  Apply φ to all trades & quotes
│    tick prices           │
└────────────┬────────────┘
             ▼
┌─────────────────────────┐
│ 2. REGIME TAGGER        │  PRE (04:00–09:29)
│    Classify every tick   │  FLIP (09:30–09:44)
│    by time-of-day        │  STD (09:45–16:00)
└────────────┬────────────┘
             ▼
┌─────────────────────────┐
│ 3. GPU FEATURE FORGE    │  PyTorch / CUDA (GTX 1070)
│    ├─ Hawkes Intensity   │  Associative scan, exp kernel
│    ├─ CVD Convexity      │  Tick-rule signed volume, 2nd deriv
│    ├─ Order Flow Imbal.  │  Quote-level bid/ask pressure
│    └─ Pre-Market Context │  PM_High_Distance, PM_Volume_Ratio
└────────────┬────────────┘
             ▼
┌─────────────────────────┐
│ 4. FEATURE ASSEMBLY     │  One row per event
│    Aggregate per-regime  │  Mean/Max/Final per FLIP & STD windows
│    summary statistics    │
└────────────┬────────────┘
             ▼
    feature_matrix_v1.parquet
```

---

## Data Sources

| Source | Records | Coverage |
|---|---|---|
| `scanner_context.parquet` | 4,549 events | 1,307 dates, 1,653 tickers |
| `data/filtered/{T}_{D}_{M}/trades.parquet` | ~2,999 events | Raw tick trades (7-day window) |
| `data/filtered/{T}_{D}_{M}/quotes.parquet` | ~2,999 events | Top-of-book quotes |
| `data/minute/{T}/{D}.parquet` | 4,544 events | 1-minute OHLCV bars |

---

## Normalization Layer

### The Split-Fix
Many tickers in the momentum universe underwent reverse splits between the event
date and data collection. The events data uses **split-adjusted** prices while
filtered tick data has **raw unadjusted** prices.

$$\phi = \frac{P_{\text{Adjusted, Open}}}{P_{\text{Raw, FirstRTHTrade}}}$$

- $\phi \approx 1.0$: No split adjustment needed
- $\phi \gg 1$: Forward split occurred (adjusted > raw)
- $\phi \ll 1$: Reverse split occurred (adjusted < raw)
- All raw prices are multiplied by $\phi$ before feature computation

### Outlier Detection
Events where $|\log_{10}(\phi)| > 3$ (1000x ratio) are flagged as potentially
erroneous and excluded from the feature matrix.

---

## Regime Definitions

| Regime_ID | Name | Window (ET) | Description |
|---|---|---|---|
| 1 | PRE | 04:00:00 – 09:29:59 | Pre-market session |
| 2 | FLIP | 09:30:00 – 09:44:59 | Volatility shock at market open |
| 3 | STD | 09:45:00 – 16:00:00 | Standard session |

Timestamps in filtered/ tick data are nanosecond-resolution **UTC**.
ET = UTC - 5h (EST) or UTC - 4h (EDT). DST boundaries are handled per-event.

---

## Feature Summary (v2)

See `SIGNAL_DICTIONARY_v2.md` for full mathematical definitions.

| Feature Group | v1 Count | v2 Count | Key Additions |
|---|---|---|---|
| Hawkes Intensity | 4 | **11** | pre, rth, fullday, post_halt_surge |
| CVD Convexity | 4 | **7** | fullday_final, transition_mean/max |
| Order Flow Imbalance | 4 | 4 | — |
| Pre-Market Context | 4 | 4 | — |
| Halt Context | 0 | **5** | is_post_halt, n_halts, durations |
| Normalization | 2 | 2 | — |
| **Total features** | **18** | **33** | (+4 identifiers = 37 cols) |

---

## Outputs

### v2 (Current)
| File | Description |
|---|---|
| `feature_matrix_v2_ext.parquet` | Extended feature matrix (37 cols, halt-stitched) |
| `plots_v2/HALT_RUNNER_TPST_2023-10-11.png` | ★ Proof chart — halt-stitched signal |
| `plots_v2/anatomy_{TICKER}.png` | 4-panel full-day anatomy plots (12 events) |
| `plots_v2/intensity_heatmap_v2.png` | Full-day Hawkes intensity heatmap |
| `Forge_Audit_Log_v2.md` | v2 audit log with halt context summary |
| `SIGNAL_DICTIONARY_v2.md` | Full v2 signal definitions with halt-stitching LaTeX |
| `build_signal_forge_v2.py` | v2 pipeline source |

### v1 (Legacy)
| File | Description |
|---|---|
| `feature_matrix_v1.parquet` | Original feature dataset (22 cols, FLIP-only) |
| `plots/anatomy_{TICKER}.png` | 3-panel FLIP-only anatomy plots |
| `plots/intensity_heatmap.png` | FLIP-only Hawkes heatmap |
| `Forge_Audit_Log.md` | v1 audit log |
| `SIGNAL_DICTIONARY.md` | v1 signal definitions |
| `build_signal_forge.py` | v1 pipeline source |

---

## Key Signal Findings

### Normalization (Split-Fix)
- Median φ = 1.004 (most events need no adjustment)
- Mean φ = 41.9 (skewed by extreme reverse-split tickers)
- 147 events excluded as outliers (|log₁₀(φ)| > 3)

### Hawkes Intensity
- Median FLIP intensity: 60.4 trades/sec, Max peak: 7,481 (SNDL 2021-02-11)
- GME meme-stock events dominate top-5 by peak intensity
- Acceleration (Δλ) mean ≈ 0 across all events — symmetric intensification/relaxation as expected

### CVD & Convexity
- Median FLIP CVD is **negative** (−18,188 shares) — net selling pressure dominates at open for most gappers
- Max CVD positive: +37.6M shares (SNDL) — extreme buyer dominance
- Convexity sign ratio median = 0.49 — roughly balanced between parabolic buying and selling

### OFI
- Median OFI is slightly negative (−5.0) — mild ask-side pressure
- The imbalance ratio median = 0.49 — near-symmetric directional pressure at the book level

### Pre-Market Context
- Median PM_High_Distance = −14.4% — **most gappers open 14% BELOW their pre-market high**
- PM_Volume_Ratio median = 15.1x — FLIP volume explodes 15x above pre-market baseline

### Performance
- Processing: 0.13s/event average (numba JIT + selective I/O)
- GPU used only for memory monitoring; core compute is numba @njit (sequential scans)
