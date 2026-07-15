---
tags:
  - type/implementation
  - domain/signal
  - project/v5-strategy
  - status/complete
created: 2026-04-04
---

# Archetype Classifier

> **File:** `src/signals/archetype_classifier.py` · **Lines:** 226

## Purpose

Instant-on parameter seeding for cold events. Classifies the first N trades against an archetype library using standardised Euclidean distance, then injects centroid Hawkes parameters and synthesises R-states for immediate online operation.

## Workflow

```mermaid
graph LR
    A[First 20 trades] --> B[Extract signature]
    B --> C[Match archetype]
    C --> D[Seed engine params]
    D --> E[Synthesise R-states]
    E --> F[Online inference]
```

## Classes

### `ArchetypeResult`
Immutable classification result.
- Fields: `archetype_id`, `archetype_name`, `distance`, `confidence`, `centroid_params`, `signature`, `observed_signature`, `classify_time_sec`, `n_trades_used`

### `ArchetypeClassifier`

| Method | Signature | Purpose |
|--------|-----------|---------|
| `__init__` | `(library_path)` | Load archetype library JSON |
| `classify` | `(t_sec, side_all, price_all, size_all, n_trades=20, burst_window_sec=10)` → ArchetypeResult | Classify cold event |
| `seed_engine` | `(result, warmup_duration_sec=900)` → BivariateHawkesEngine | Create pre-seeded engine |
| `seed_tracker` | `(engine, capacity=1000, n_synthetic_ticks=200)` → IntensityTracker | Create pre-filled tracker |

## Signature Features
`burst_trade_count_10s`, `burst_avg_iat_10s`, `burst_roc_10s`, `burst_avg_size_10s`, `buy_fraction`

## Dependencies
- **Internal:** [[Hawkes Engine]] (`BivariateHawkesEngine`, `IntensityTracker`, `build_beta_bank`)
- **External:** `numpy`, `json`, `logging`, `pathlib`, `time`

## Consumers
- [[Archetype Strategy]], [[Archetype Backtest Runner]]

---
*Back to [[Signals Index]] · [[00-Index]]*
