---
tags:
  - type/implementation
  - domain/data
  - project/src-core
  - status/complete
created: 2026-04-04
---

# Polars Loader

> **File:** `src/data/polars_loader.py` · **Lines:** 420
> **Status:** ★ Canonical — all new code should use this loader

## Purpose

Polars zero-copy Arrow I/O data loader. Replaces Pandas-based loading with Polars lazy evaluation for 10–50× speedup. Vectorised Lee-Ready trade classification via `join_asof`. Produces `EventData` with zero-copy handoffs to numpy and torch.

## Lee-Ready Classification

Three-tier vectorised classification:
1. **Quote rule:** Compare trade price to midpoint
2. **Midpoint rule:** Use signed tick direction
3. **Tick rule + forward-fill:** Last resort

```python
trades = _classify_lee_ready_polars(trades, quotes)
# Adds columns: side (+1 buy, -1 sell), signed_volume, cvd
```

## Class: `EventData` (frozen dataclass)

| Field | Type | Purpose |
|-------|------|---------|
| `event_name` | str | Directory name |
| `df` | pl.DataFrame | Full classified dataframe |
| `n_trades` | int | Trade count |
| `n_quotes` | int | Quote count |
| `buy_pct` | float | Fraction of buys |
| `magnitude` | float | Event momentum |

| Method | Returns | Purpose |
|--------|---------|---------|
| `to_numpy()` | dict[str, ndarray] | Zero-copy to numpy arrays |
| `to_torch(device)` | dict[str, Tensor] | Cast to torch tensors |

## Key Functions

| Function | Purpose |
|----------|---------|
| `load_event(data_path, event_dir, max_trades)` → EventData | Lazy scan + classify + collect |
| `load_event_arrays(...)` → dict | Numpy shortcut |
| `list_events(data_path, min_magnitude, require_quotes)` | Event discovery |
| `filter_to_active_trades(ev, ...)` | LULD halt removal + market hours + active compression |
| `select_random_event(...)` | Random high-momentum event |

## Dependencies
- **Internal:** [[LULD Halt Detection]]
- **External:** `polars`, `numpy`, `pandas` (LULD bridge), `logging`

## Consumers
- [[V5 Backtest Runner]], [[Parallel Runner]], [[Signal Bakeoff]], [[Audit Suite]], [[Latency Audit]], [[Stat Validator]]

---
*Back to [[Data Index]] · [[00-Index]]*
