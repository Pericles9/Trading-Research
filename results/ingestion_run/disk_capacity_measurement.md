---
tags:
  - type/results
  - domain/data
  - project/src-core
  - status/complete
created: 2026-07-12
---

# Disk Architecture — T2 Capacity Measurement

## T1 — Failed DB deleted

`D:\Trading Research\data\duckdb\main.duckdb` (102.33GB, partial/crashed
from the disk-full incident) deleted. D: free space: 0GB → 102.3GB.

## T2a — D: usage breakdown

D: total 465.2GB. Top-level `D:\Trading Research` breakdown (296.8GB, after
the failed DB's deletion):

| Directory | Size |
|---|---|
| `data/` | 214.05 GB |
| `scanner-epg-momentum/` | 65.34 GB |
| `hawkes-ofi-impact/` | 10.13 GB |
| `.venv/` | 5.23 GB |
| `archive/` | 1.46 GB |
| (rest) | ~0.6 GB |

`data/` broken down further — the parquet source data relevant to this
ingestion:

| Directory | Size | Role |
|---|---|---|
| `filtered/` | **183.11 GB** | Source for `filtered_trades`/`filtered_quotes` |
| `quote_data/` | **27.1 GB** | Source for `raw_quotes` |
| `second10/` | 1.21 GB | Candle — out of scope for this ingestion |
| `nautilus_catalog/` | 1.0 GB | Out of scope |
| `trade_data/` | 0.79 GB | Out of scope (provenance-unknown, deferred) |
| `minute/` | 0.75 GB | Candle — out of scope |
| (rest) | <0.1 GB | — |

`filtered/` + `quote_data/` = **210.21 GB**, the only two directories that
matter for the current in-scope ingestion (`filtered`, `quote_data`,
`metadata` per `loader_scope.md`). The candle directories are tiny (~3GB
combined) and not worth relocating — they're out of scope for this
ingestion pass regardless.

Elsewhere on D: `D:\archived` (58.2GB, separate from `D:\Trading Research`)
and a couple of small legacy directories (~2GB) — not part of this project's
active data, not touched.

Other drives: **C: 8.7GB free** (922GB used — no real headroom), **E:
930.8GB free** (0.1GB used — effectively empty).

## T2b/c — Real capacity estimate, not the original guess

The original 250–400GB estimate was extrapolated from a 50-file subset and
turned out too wide to be actionable on its own. Replaced with:

1. **`filtered_trades`: 102.33GB — actual**, not estimated (the full table
   completed successfully before the disk-full incident: 24,200 files,
   4,899,401,773 rows). 20.88 bytes/row.
2. **`filtered_quotes` and `raw_quotes`: measured on real 500-file samples**
   run through the actual `_scan_union_schema`/`_build_select_for_file`
   loader logic (not copied files, not simulated — the real per-file insert
   path), written to a throwaway DB on E: to avoid touching C:/D: space,
   then deleted:

| Table | Measured bytes/row | Total rows (exact, via `parquet_file_metadata`) | Estimated size |
|---|---|---|---|
| `filtered_trades` | 20.88 (actual) | 4,899,401,773 | **102.33 GB (actual)** |
| `filtered_quotes` | 17.75 (measured, 500-file sample, 73.6M rows) | 3,787,286,022 | **67.21 GB** |
| `raw_quotes` | 14.86 (measured, 500-file sample, 47.7M rows) | 1,759,177,124 | **26.14 GB** |
| **Total** | | 10,445,864,919 | **195.67 GB** |

This is meaningfully *lower* than the original wide estimate — `filtered_quotes`
and `raw_quotes` have fewer/narrower columns than `filtered_trades` (no
`VARCHAR id` field, fewer drift columns), so their per-row storage cost is
genuinely smaller, not just assumed to be.

**Margin check:** moving `filtered/` + `quote_data/` (210.21GB) to E: frees
D: from 102.3GB → **312.51GB**. Against the 195.67GB point estimate, that's
**116.84GB of margin** — above the top of the requested 50–100GB range.
Moving only these two directories is sufficient; no need to touch the candle
directories or other subprojects.

## Escalation check

`T2 finds insufficient margin even after moving everything movable off D:` —
**not triggered.** 312.51GB free vs. 195.67GB estimated need, 116.84GB
margin, clears the 50-100GB bar without needing to move anything beyond
`filtered/` and `quote_data/`. Proceeding to T3.
