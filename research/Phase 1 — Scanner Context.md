---
tags:
  - type/results
  - domain/signal
  - project/src-core
  - status/complete
created: 2026-04-04
---

# Phase 1 — Scanner Context

> **Script:** `research/phase_1_context/build_scanner_context.py` · **Lines:** 681
> **Output:** `scanner_context.parquet`

## Purpose

Reconstructs the 9:30 AM "Top Gappers" scanner for every momentum-event day, applies a 30% hard gap filter, ranks tickers, computes volume metrics, and runs QC checks.

## Pipeline

| Step | Description |
|------|-------------|
| 1 | Load & merge/dedup 3 momentum-event sources |
| 2 | Gap calculation & 30% hard filter |
| 3 | `gap_rank` per date |
| 4 | Volume Intensity (first 5-min from minute data) |
| 5 | RVOL (30-day avg from daily data) |
| 6 | Save parquet |
| 7 | Visualization suite (histogram, leaderboard, rank-stability) |
| 8 | QC (survivorship bias, open-price consistency, split detection) |
| 9 | Write `build_log.md` |

## Output Schema — `scanner_context.parquet`

| Column | Type | Description |
|--------|------|-------------|
| `ticker` | str | Symbol |
| `date` | date | Event date |
| `prev_close` | f64 | Previous close |
| `open` | f64 | Open price |
| `high` | f64 | Session high |
| `close` | f64 | Close |
| `volume` | i64 | Total volume |
| `gap_pct` | f64 | Gap percentage |
| `momentum_at_high` | f64 | Price change at high |
| `gap_rank` | i32 | Rank within date |
| `vol_5min` | f64 | First 5-min volume |
| `volume_intensity_rank` | i32 | Volume intensity rank |
| `rvol` | f64 | Relative volume (vs 30-day avg) |

## Data Sources
- `data/momentum_events/filtered_events_power_law_q05.parquet`
- `data/momentum_events/full_2020_2024_momentum_scan_*.parquet`
- `data/momentum_events/momentum_scan_2025.parquet`
- `data/minute/{TICKER}/{DATE}.parquet`
- `data/daily/{TICKER}_daily.parquet`
- `data/filtered/` (for tick-level QC)

## Consumers
- [[Phase 2 — Signal Forge]], [[Phase 3 — Alpha Hunter]]

---
*Back to [[00-Index]]*
