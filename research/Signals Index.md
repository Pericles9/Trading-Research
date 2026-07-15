---
tags:
  - type/reference
  - domain/signal
  - project/src-core
  - status/complete
created: 2026-04-04
---

# Signals Index

> Signal processing filters, strategy configurations, regime gating, and Nautilus strategy adapters.

## Filters & Processing

| Module | File | Lines | Purpose |
|--------|------|-------|---------|
| [[Signal Processor]] | `src/signals/signal_processor.py` | 462 | 4-mode structural alpha filter |
| [[Alpha Config]] | `src/signals/alpha_config.py` | 175 | v5 strategy parameter container |
| [[Intensity Gating]] | `src/signals/intensity_gating.py` | 95 | Schmitt-trigger regime detection |
| [[Flow Z-Score Indicator]] | `src/signals/flow_zscore_indicator.py` | 145 | Volume anomaly visualization |

## Classification & Seeding

| Module | File | Lines | Purpose |
|--------|------|-------|---------|
| [[Archetype Classifier]] | `src/signals/archetype_classifier.py` | 226 | Cold-start classification |
| [[Archetype Injector]] | `src/signals/archetype_injector.py` | 243 | Instant-on parameter injection |

## Nautilus Strategies

| Module | File | Lines | Purpose |
|--------|------|-------|---------|
| [[Bivariate Strategy]] | `src/signals/bivariate_strategy.py` | 395 | 3-phase momentum strategy |
| [[Archetype Strategy]] | `src/signals/archetype_strategy.py` | 430 | 5-phase archetype-seeded strategy |

## Filter Mode Comparison

| Mode | Class | Method | Key Idea |
|------|-------|--------|----------|
| **Kalman-Bucy** | `KalmanFilter` | State-space with adaptive R | Smooth + drift tracking |
| **SWT** | `SWTFilter` | Haar wavelet decomposition | Multi-scale denoising |
| **CUSUM** | `CUSUMFilter` | Two-sided CUSUM | Mean-shift detection |
| **FracDiff** | `FracDiffFilter` | López de Prado fractional differencing | Memory-preserving stationarity |

---
*Back to [[00-Index]]*
