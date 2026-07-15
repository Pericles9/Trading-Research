---
tags:
  - type/results
  - domain/signal
  - project/src-core
  - status/complete
created: 2026-04-04
---

# Phase 1b — Extended Hours

> **Directory:** `research/phase_1_ext_hours/`
> **Script:** *(none — manual notebook analysis)*

## Purpose

Extended hours context analysis. Pre-market (4:00–9:30 ET) and after-hours data analysis for gap prediction.

## Outputs

| File | Purpose |
|------|---------|
| `extended_context.parquet` | Extended hours price/volume features |
| `volatility_analysis.parquet` | Pre-market volatility metrics |
| `build_log.md` | Processing log |
| `MANIFEST.md` | Data provenance |
| `DATA_FIXES.md` | Data quality issues & corrections |
| `plots/` | Visualization artifacts |

## Artifacts

- [[MANIFEST]] — data provenance for this phase
- [[build_log]] — processing run log
- [[DATA_FIXES]] — data quality issues and corrections

## Consumers
- [[Phase 2 — Signal Forge]] (optional extended features)

---
*Back to [[00-Index]]*
