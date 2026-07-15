---
tags:
  - type/implementation
  - domain/data
  - project/src-core
  - status/complete
created: 2026-04-04
---

# Manifest

> **File:** `src/utils/manifest.py` · **Lines:** 170

## Purpose

Backtest manifest & versioning system. Tracks every GPU audit run with unique version ID (e.g., `v4.3.001`), hyperparameters, git state (code SHA-256 fingerprint), and hardware telemetry.

## Functions

| Function | Purpose |
|----------|---------|
| `_gpu_telemetry()` | CUDA device info snapshot |
| `_system_telemetry()` | Platform/python/pytorch info |
| `_code_fingerprint()` | SHA-256 of all strategy .py files (first 16 chars) |
| `load_manifest()` → dict | Load or initialize `backtest_manifest.json` |
| `save_manifest(manifest)` | Atomic write (tmp → rename) |
| `next_version_id(manifest, major, minor)` | Sequential version string |
| `register_run(config_dict, n_events, ...)` → dict | Register pre-backtest metadata |
| `finalize_run(version_id, results, output_dir)` | Mark COMPLETE |
| `fail_run(version_id, error)` | Mark FAILED |
| `get_run(version_id)` | Retrieve specific run |
| `list_runs()` | List all (version_id, status, timestamp) |

## Constants
- `MANIFEST_PATH = Path("backtest_manifest.json")`

## Dependencies
- **Internal:** None
- **External:** `json`, `hashlib`, `platform`, `torch`

## Consumers
- [[GPU Batch Runner]]

---
*Back to [[Utils Index]] · [[00-Index]]*
