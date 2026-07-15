---
tags:
  - type/implementation
  - domain/backtest
  - project/v5-strategy
  - status/complete
created: 2026-04-04
---

# V5 Backtest Runner

> **File:** `src/backtest/v5_runner.py` · **Lines:** 580
> **Version:** v5 (production)

## Purpose

AlphaMomentumHawkes v5 production-scale tick-by-tick backtest simulation. Implements 6 entry gates and 7 exit triggers with dynamic α refitting, CVD velocity Welford online stats, quote-fill slippage, and excursion analysis.

## Entry Gates (all must pass)

| # | Gate | Threshold |
|---|------|-----------|
| 1 | Catalyst | Price > 30% above prev close |
| 2 | CVD Velocity | > 2.2σ + acceleration detected |
| 3 | Alpha Slope | Branching ratio > 0.35 |
| 4 | Anti-Chase | Price < 1.25% from base |
| 5 | Frequency | Trade rate ≥ 2× baseline |
| 6 | Late Filter | Not too far from event-day open |

## Exit Triggers

| Trigger | Condition |
|---------|-----------|
| VWAP_BLOWOFF | 15% λ decay from peak |
| EXPECTATION_GAP | No new high within 45s |
| ALPHA_COLLAPSE | α < 0.30 |
| REAPER_120S | >120s hold with <0.5% PnL |
| TRAILING_STOP | −5% from peak |
| HARD_STOP | −10% from entry |
| TIME_STOP | 600s max hold |

## Key Functions

| Function | Purpose |
|----------|---------|
| `_run_one_simulation(arrays, config, ...)` | Core tick-by-tick loop |
| `run_event(event_name, ...)` | Single event (load → classify → simulate → save) |
| `run_batch(event_names, ...)` | Multi-event validation |
| `_generate_plots(trades_log, ...)` | Plotly intensity + PnL charts |

## Dependencies
- **Internal:** [[Hawkes Engine]], [[Archetype Injector]], [[Alpha Config]], [[Polars Loader]]
- **External:** `numpy`, `polars`, `plotly`, `json`, `argparse`

## Consumers
- [[Optimizer]], [[Parallel Runner]], [[Stat Validator]], [[Audit Suite]]

---
*Back to [[Backtest Index]] · [[00-Index]]*
