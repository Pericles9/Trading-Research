---
tags:
  - type/results
  - domain/data
  - project/src-core
  - status/complete
created: 2026-07-11
---

# DuckDB Ingestion — Code Fixes (Investigate-Then-Fix)

Code review and fixes only. No DuckDB ingestion was run in this phase — all
verification was by dry inspection (tracing loader logic against the real
directory tree without touching the database, and comparing dataset
contents directly with DuckDB queries).

## Disposition summary

| # | Item | Finding | Disposition | Change made |
|---|---|---|---|---|
| T1 | `load_minute()` dead fallback path | `data/minute/trades/` confirmed gone (deleted earlier this session). Direct check of all 3,376 current ticker dirs under `data/minute/`: every one has direct `.parquet` files — zero would ever hit the nested-fallback branch. Fallback was provably dead code, not just stale-but-harmless. | **Fixed.** | Removed the `if sub_parquets: ... else: # Nested ...` branching in `load_minute()` (`src/data/ingest.py`); kept only the direct-file path. Dry-traced the simplified logic: 3,376 tickers, 24,590 files — exact match to the known-good candle inventory count. |
| T2 | `momentum_events` loads only 1 of 4 files in its directory | Investigated rather than assumed. `filtered_events_power_law_q05.parquet` (loaded) has **zero row overlap** with `momentum_scan_2025.parquet` and only partial overlap (17,357/18,660) with `full_2020_2024_momentum_scan_*.parquet` — it is a distinct, purpose-built curated/filtered subset (19,170 rows, extra analysis columns like `min_volume_threshold`), not the same data as the two scan files minus some rows. The `.csv` is a redundant export of the same parquet (same row count, one fewer column — the pandas index artifact). Loading only the curated file is intentional and correct, not a bug. | **No code fix — confirmed intentional.** Not escalated (the escalation criterion was "confirmed real defect"; this is the opposite finding). | Doc corrected to explain the distinction explicitly (see `research/DuckDB Ingest.md`) rather than implying "all parquet in the dir" is loaded. Separately noted: the curated file (Jan 2026) predates the 2025 gap-fill and `minute/trades/` migrations completed since, so once ingested this table will not reflect ~7,252 of the 30,511+ events now in `filtered/`. This is a source-data freshness question for whoever regenerates the curated file, not something the loader can or should fix on its own. |
| T3 | `metadata` loader reads parquet; doc says JSON | Checked `data/metadata/` directly: contains exactly `collection_stats.parquet` and `symbols_metadata.parquet` — **no `.json` files exist there at all.** Code is correct; doc was wrong. | **Doc fixed, no code change.** | `research/DuckDB Ingest.md` row corrected from `data/metadata/*.json` to the two actual parquet filenames, and the table-name column corrected from singular `metadata` to the actual two table names `collection_stats`, `symbols_metadata`. |
| T4 | `trade_data`'s hardcoded 6-table fanout list | Checked each of the 5 subfolders directly: `batches/`=0 parquet files, `by_date/`=0, `by_ticker/`=0, `enhanced/`=5, `high_momentum/`=0 (emptied by this session's cleanup). Also found `rebuild_validation_sample/` (58 parquet files) — real, populated, not in the list. | **Fixed (partial) + flagged (partial).** Removed the four confirmed-empty entries. Did *not* add `rebuild_validation_sample` — it substantially duplicates data already reachable via `load_filtered`, and whether staging/validation output belongs in a permanent `trade_data_*` table is a judgment call, not something to decide unilaterally. | `subfolders` list in `load_trade_data()` reduced from `["batches", "by_date", "by_ticker", "enhanced", "high_momentum"]` to `["enhanced"]`. Dry-traced: `enhanced` resolves to exactly 5 files, matching direct inspection. Doc updated with a note explaining both the removal and the deliberately-not-added `rebuild_validation_sample`. |

## Evidence detail

### T1 — `load_minute()`

```
$ ls data/minute/ | grep -i trades
(no output — confirmed gone)

Dry check: 3,376/3,376 ticker dirs under data/minute/ have direct .parquet files.
0 dirs would have hit the nested-fallback branch even before removal.
```

Before/after: the `else` branch (lines 224–245 in the pre-edit file) walking
`minute/trades/{TICKER}/{date}.parquet` as a second-level nested layout was
removed in full. The primary branch (direct `{TICKER}/{date}.parquet` files)
is unchanged in behavior — verified by dry-tracing the post-edit code against
the real tree: 3,376 tickers, 24,590 files, matching the earlier candle
inventory's independently-derived count exactly.

### T2 — `momentum_events`

```
filtered_events_power_law_q05.parquet: 23,268 rows, 19,170 (ticker,date) pairs
  overlap with momentum_scan_2025.parquet:            0
  overlap with full_2020_2024_momentum_scan_*:        17,357 / 18,660
  pairs in neither scan file:                         1,813
filtered_events_power_law_q05.csv: same 23,268 rows, same columns minus
  the pandas index artifact — genuinely redundant, not divergent content.
mtime: 2026-01-19 (after both scan files, consistent with being a
  downstream/derived product of them, not an independent parallel source).
```

Zero overlap with the 2025 scan file rules out "this should just include
2025 events too" as an easy fix — the curated file was never meant to cover
2025 at all; it's a different kind of artifact entirely (a filtered research
output, not a raw candidate list).

### T3 — `metadata`

```
$ ls -la data/metadata/
collection_stats.parquet
symbols_metadata.parquet
(no .json files present)
```

### T4 — `trade_data`

```
batches/:        exists, 0 parquet files
by_date/:        exists, 0 parquet files
by_ticker/:       exists, 0 parquet files
enhanced/:        exists, 5 parquet files
high_momentum/:   exists, 0 parquet files (emptied by this session's cleanup)
rebuild_validation_sample/: exists, 58 parquet files (NOT in the hardcoded list)

Dry trace post-edit: subfolders=["enhanced"] -> 5 files, matches direct inspection.
```

## What was NOT touched

- No DuckDB ingestion was run — `data/duckdb/main.duckdb` remains at 0 tables,
  unchanged by this phase.
- No data files were moved, deleted, or modified — code and one companion doc
  only.
- Other pre-existing doc-vs-code divergences found in the earlier Data Layer
  Inventory (e.g. `daily` vs. actual table name `daily_bars`, `minute` vs.
  `minute_bars`, `second10` vs. `second10_bars`, `quote_data` vs. `raw_quotes`,
  `filtered_*` not distinguishing `filtered_trades`/`filtered_quotes`,
  `nautilus_catalog`'s two-glob VIEW setup) were **not** in scope for this
  phase's four items and were left as-is.

## Escalation check

| Condition | Result |
|---|---|
| `momentum_events` file-skipping is a confirmed real defect | **No** — confirmed intentional and correct, not escalated |
| Any task required touching data, not just code | No — code and one doc only |
| A fix was applied and later found to override intentional behavior | No |

## Approval gate status

Per this task's gate: no DuckDB ingestion has been run. All four items now
have a clear, evidence-based disposition. Ready for review before any
ingestion run is attempted.
