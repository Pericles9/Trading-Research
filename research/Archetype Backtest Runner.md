---
tags:
  - type/implementation
  - domain/backtest
  - project/v5-strategy
  - status/complete
created: 2026-04-04
---

# Archetype Backtest Runner

> **File:** `src/backtest/archetype_runner.py` · **Lines:** 600

## Purpose

Archetype-seeded instant-on simulation (v3). Replaces 30% warmup with archetype classification on first 20 trades. Dynamic transition refits after 2 min of live data. Supports batch validation.

## Workflow

```mermaid
graph LR
    A[Buffer 20 trades] --> B[Classify archetype]
    B --> C[Seed engine + tracker]
    C --> D[Run tick-by-tick sim]
    D --> E[Dynamic refit at 120s]
    E --> F[Continue with live params]
```

## Key Functions

| Function | Purpose |
|----------|---------|
| `_run_one_simulation(...)` | Tick loop with diagnostics |
| `run_event_simulation(...)` | Single event with archetype seeding |
| `run_batch_validation(...)` | Multi-event loop |

## Dependencies
- **Internal:** [[Hawkes Engine]], [[Archetype Classifier]], [[Archetype Strategy]]
- **External:** `numpy`, `plotly`, `json`, `argparse`

---
*Back to [[Backtest Index]] · [[00-Index]]*
