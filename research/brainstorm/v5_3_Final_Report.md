---
tags:
  - type/results
  - domain/backtest
  - project/v5-strategy
  - status/complete
created: 2026-02-10
---

# AlphaMomentumHawkes v5.3 — 'Temporal Beta' Hybrid — Final Report

**Generated:** 2026-02-10 19:49:02
**Runtime:** 3315.9s (55.3 min)
**Events:** 200 (125 with trades)

## Executive Summary

| Metric | v5.3 (Temporal Beta) | v4 (Lead-Follower) | Delta |
|--------|---------------------:|-------------------:|------:|
| SQN | -9.20 | 8.40 | -17.60 |
| Total PnL | -2047.03% | +36.90% | -2083.93% |
| Win Rate | 20.5% | 74.1% | -53.6% |
| Profit Factor | 0.01 | — | — |
| Total Trades | 5,626 | 40,985 | — |
| Runners >10% | 3 | — | — |
| MFE Efficiency | 0.387 | — | — |

## Two-Stage Exit Breakdown

- **Stage 1 Exits** (PnL < 3%, λ decay): 5371
- **Stage 2 Exits** (PnL ≥ 3%, trail): 12
- **Runners >5%:** 10
- **Runners >10%:** 3

## Temporal Lock Audit

The 3.0s Temporal Lock prevents premature exits from flickering signals.

- **Locks Fired:** 8731
- **Locks Reset (signal flickered):** 3108
- **Premature Exits Prevented:** 3108

## PnL Distribution

| Percentile | PnL |
|-----------|----:|
| P10 | -40.68% |
| P25 | -24.85% |
| P50 (Median) | -9.41% |
| P75 | -1.55% |
| P90 | -0.09% |

## Duration Heatmap

| Bucket | Events |
|--------|-------:|
| 0-10s | 30 |
| 10-30s | 61 |
| 30-60s | 28 |
| 60-120s | 6 |
| 120-300s | 0 |
| 300s+ | 0 |

## Top 10 Runners

| Event | PnL | MFE | Efficiency | Runners>10% |
|-------|----:|----:|-----------:|------------:|
| TWO_2020-03-25_91.19 | +9.63% | 1.41% | 0.160 | 0 |
| OLB_2024-05-02_76.99 | +3.97% | 2.25% | 0.862 | 0 |
| RCON_2024-04-12_33.59 | +1.27% | 1.30% | 0.494 | 0 |
| IMMP_2020-12-10_268.06 | +1.16% | 1.41% | 0.818 | 0 |
| NRXP_2022-03-09_35.63 | +0.87% | 0.72% | 0.611 | 0 |
| KREF_2020-03-26_33.19 | +0.62% | 0.27% | -0.365 | 0 |
| QBTS_2024-11-22_52.28 | +0.39% | 0.52% | 0.083 | 0 |
| SMX_2024-12-04_290.14 | +0.36% | 1.53% | -5.394 | 0 |
| LFST_2023-03-08_33.12 | +0.32% | 0.49% | 0.250 | 0 |
| SIFY_2024-09-03_174.76 | +0.26% | 0.66% | -1.350 | 0 |

## Worst 5 Events

| Event | PnL | Entries | Archetype |
|-------|----:|-------:|-----------|
| GIGM_2022-08-15_64.63 | -94.00% | 124 | Archetype-3 |
| NCTY_2021-02-09_39.81 | -78.34% | 145 | Archetype-3 |
| AEI_2021-02-11_86.34 | -73.33% | 107 | Archetype-3 |
| DDL_2021-06-30_95.58 | -73.04% | 126 | Archetype-3 |
| NEON_2024-08-21_59.52 | -72.53% | 141 | Archetype-3 |

## Per-Archetype Breakdown

| Archetype | N | Avg PnL | Total PnL | Win Rate | Runners |
|-----------|--:|--------:|----------:|---------:|--------:|
| Archetype-3 | 117 | -16.78% | -1963.08% | 21% | 3 |
| Archetype-2 | 5 | -14.10% | -70.48% | 25% | 0 |
| Archetype-1 | 3 | -4.49% | -13.47% | 4% | 0 |

## Configuration

```
Beta Bank:        [100, 30, 10, 3, 1, 0.3, 0.1]
Temporal Lock:    3.0s continuous signal required
Stage 1 Thr:      3.0% PnL
Stage 1 Exit:     lam decay 15% from peak + 3s lock
Stage 2 Exit:     Trail VWAP_1min / α<0.20 / -3% trailing + 3s lock
Anti-Chase:       ≤ lowest_5s × 1.0125
Catalyst Gate:    30%
CVD Threshold:    2.2σ
Alpha Band:       [0.35, 0.85]
Spread Max:       1.5%
Expectation Gap:  45s
120s Reaper:      PnL < 0.5%
Hard Stop:        -10%
Slippage:         Buy@Ask, Sell@Bid, +0.05% vol impact
```

---
*v5.3 'Temporal Beta' Hybrid — 200 events in 55.3 min*

## Related

- [[v5_Battle_Results]] — predecessor v5 Battle Royale run
- [[V5 Backtest Runner]] — runner that produced this output
- [[README]] — brainstorm directory guide
- [[00-Index]] — vault index