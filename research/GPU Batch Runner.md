---
tags:
  - type/implementation
  - domain/backtest
  - domain/gpu
  - project/src-core
  - status/complete
created: 2026-04-04
---

# GPU Batch Runner

> **File:** `src/backtest/gpu_batch_runner.py` · **Lines:** 430

## Purpose

Full-session GPU tensor backtest using CUDA associative-scan Hawkes ([[Tensor Engine]]). Dynamic VRAM batching (80% fraction), versioned Parquet output via [[Manifest]], session log with VRAM telemetry.

## Class: `SessionLog`

| Method | Purpose |
|--------|---------|
| `log(msg)` | Timestamped log entry |
| `log_vram(label)` | Record VRAM usage snapshot |
| `save(path)` | Export log to file |

## Key Functions

| Function | Purpose |
|----------|---------|
| `_load_event_arrays(event_name, ...)` | Load numpy arrays |
| `pad_and_tensorise(events, device)` | Batch to CUDA tensors |
| `run_gpu_audit(event_names, ...)` | Main GPU batch entry point |
| `_collect_trade_records(...)` | Extract per-trade results |
| `_compute_aggregate_results(...)` | Batch statistics |

## Dependencies
- **Internal:** [[Tensor Engine]], [[Alpha Config]], [[Manifest]]
- **External:** `torch`, `polars`, `numpy`

---
*Back to [[Backtest Index]] · [[00-Index]]*
