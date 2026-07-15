---
tags:
  - type/implementation
  - domain/backtest
  - project/src-core
  - status/complete
created: 2026-04-04
---

# Audit Suite

> **File:** `src/backtest/analytics/audit.py` · **Lines:** 430

## Purpose

Mandatory 4-audit forensic suite for v4+. Validates trade quality across latency, classification, peak proximity, and timing.

## Audits

### 1. Latency Audit
Entry must occur ≥ 30s before price peak. Measures lead time distribution.

### 2. Tick Test vs Lee-Ready
Compares tick-rule classification against Lee-Ready quote-based classification. Reports agreement rate.

### 3. Peak Buyer Trap
Ensures 0% of entries occur within 0.5% of the session high (H\_max). Catches momentum chasers.

### 4. Entry-to-Climax Time (ECT)
ECT > 20s = early enough. Measures time from entry to the subsequent price climax.

## Key Functions

| Function | Purpose |
|----------|---------|
| `latency_audit(event_names, ...)` | Lead time to peak |
| `tick_vs_lee_ready_audit(event_names, ...)` | Classification comparison |
| `peak_buyer_trap_audit(event_names, ...)` | Proximity to peak |
| `entry_to_climax_audit(event_names, ...)` | ECT analysis |
| `run_full_audit(event_names, ...)` | Run all 4 + report |

## Outputs
- `audit_report.txt` (human-readable)
- `audit_report.json` (machine-readable)

## Dependencies
- **Internal:** [[Polars Loader]], [[V5 Backtest Runner]]
- **External:** `numpy`, `json`

---
*Back to [[Backtest Index]] · [[00-Index]]*
