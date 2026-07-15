---
tags:
  - type/implementation
  - domain/backtest
  - project/src-core
  - status/complete
created: 2026-04-04
---

# Parallel Runner

> **File:** `src/backtest/parallel_runner.py` · **Lines:** 300

## Purpose

`ProcessPoolExecutor`-based parallel execution of 20k+ events for v5. Process-level isolation, progress tracking with ETA, checkpointing every N events, result aggregation.

## Key Functions

| Function | Purpose |
|----------|---------|
| `_worker_run_event(args)` | Child-process worker (isolated) |
| `run_parallel_batch(event_names, ...)` | Main orchestrator |
| `_aggregate_results(results)` | Compute batch stats |
| `_save_checkpoint(...)` | Incremental save |

## Dependencies
- **Internal:** [[Polars Loader]] (`list_events`), [[V5 Backtest Runner]] (`run_event`)
- **External:** `concurrent.futures`, `json`, `argparse`

## Consumers
- [[Stat Validator]]

---
*Back to [[Backtest Index]] · [[00-Index]]*
