---
tags:
  - type/implementation
  - domain/signal
  - project/v5-strategy
  - status/complete
created: 2026-04-04
---

# Archetype Injector

> **File:** `src/signals/archetype_injector.py` · **Lines:** 243

## Purpose

Instant-on parameter injection for AlphaMomentumHawkes v5. Similar to [[Archetype Classifier]] but uses a frozen dataclass `ArchetypeMatch` and adds `seed_branching_ratio()` and `replay_buffer()` methods for the v5 entry pipeline.

## Classes

### `ArchetypeMatch` (frozen dataclass)
- All fields from `ArchetypeResult` plus: `seeded_branching_buy`, `seeded_branching_sell`

### `ArchetypeInjector`

| Method | Signature | Purpose |
|--------|-----------|---------|
| `classify` | `(t_sec, side_all, price_all, size_all, n_trades=20)` → ArchetypeMatch | Classify cold event |
| `seed_engine` | `(match, warmup_duration_sec=900)` → BivariateHawkesEngine | Pre-seeded engine |
| `seed_tracker` | `(engine, capacity=1000, n_synthetic_ticks=200)` → IntensityTracker | Pre-filled tracker |
| `seed_branching_ratio` | `(match)` → float | Quick branching ratio from centroid |
| `replay_buffer` | `(engine, tracker, t_sec, side_all, n_trades=20)` | Replay real ticks through seeded engine |

## Dependencies
- **Internal:** [[Hawkes Engine]]
- **External:** `numpy`, `json`, `logging`, `pathlib`, `time`, `dataclasses`

## Consumers
- [[V5 Backtest Runner]]

---
*Back to [[Signals Index]] · [[00-Index]]*
