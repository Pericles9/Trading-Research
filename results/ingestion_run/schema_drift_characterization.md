---
tags:
  - type/results
  - domain/data
  - project/src-core
  - status/complete
created: 2026-07-12
---

# Ingestion Loader Fix — T1 Schema Drift Characterization

Metadata-only scan (`parquet_schema()`) across the **full** file sets for all
3 affected tables — not the failing subset.

## `filtered_trades` — 24,609 files scanned

12 distinct columns across the corpus.

**2 genuine type conflicts** (not just presence/absence):

| Column | Types seen | Resolution |
|---|---|---|
| `size` | BIGINT (23,719 files), DOUBLE (890 files) | **BIGINT.** Verified — not assumed — by scanning all 1,175,438,628 rows across all 890 DOUBLE-typed files: zero non-whole-number values, max 57,688,368 (well inside exact-integer range for either type). Pure storage/type-inference artifact, not genuine fractional share counts. |
| `participant_timestamp` | BIGINT (17,188 files), DOUBLE (15 files) | **BIGINT.** The 15 DOUBLE-native files hold real nanosecond epoch values (~1.6–1.7×10¹⁸) — structurally impossible to represent exactly in a DOUBLE's 53-bit mantissa (exact range tops out at ~9.007×10¹⁵). Those 15 files' precision is already lost at the source; this is a fact, not a choice. Resolving to BIGINT avoids *additionally* degrading the other 17,188 files, which currently hold exact values. The column is confirmed unused by any downstream code (see `column_usage_scope.csv` from the earlier quotes-fix phase) — the resolution has zero effect on the signal pipeline either way. |

**9 columns present in only ~70% of files** (not a conflict — presence/absence
only, single type each): `correction` (15.7%), `trf_id`, `trf_timestamp`,
`participant_timestamp`, `element`, `exchange`, `id`, `sequence_number`,
`tape` (each ~70.5%). This isn't random drift — it's the documented,
deliberate outcome of the 2025 gap-fill migration
(`results/cleanup/deletion_report.md`), which wrote a subtractive 3-column
schema (`sip_timestamp`, `price`, `size` only) for the ~7,252 events it
added, versus the fuller native schema on the original ~17,357 files.
24,609 − 17,357 = 7,252, matching that migration's own count exactly.

## `filtered_quotes` — 23,003 files scanned

11 distinct columns.

**2 genuine type conflicts**, same pattern:

| Column | Types seen | Resolution |
|---|---|---|
| `ask_size` | BIGINT (22,866), DOUBLE (137) | **BIGINT.** Verified across all 87,689,842 rows in the 137 DOUBLE files: zero non-whole values, max 9,284,900. |
| `bid_size` | BIGINT (22,856), DOUBLE (147) | **BIGINT.** Verified across all 94,950,585 rows in the 147 DOUBLE files: zero non-whole values, max 7,728,200. |

**6 columns present in only ~75% of files**: `ask_exchange`, `bid_exchange`,
`element`, `participant_timestamp`, `sequence_number`, `tape` — same root
cause as above (subtractive gap-fill schema).

## `raw_quotes` (`data/quote_data/`) — 19,132 of 19,136 files scanned

**4 files confirmed unreadable** before schema scan even started — matches
the task's baseline exactly ("4 already known-corrupted per V0.0b"):
`CING_quotes_2024_08_16.parquet`, `CLRO_quotes_2023_05_09.parquet` ("too
small to be a Parquet file"), `POLA_quotes_2020_11_23.parquet`,
`RR_quotes_2024_09_23.parquet` (`ReadFile` I/O errors). Excluded from the
schema scan and will be excluded from ingestion the same way — they fail
before any row is read, not silently included.

7 real columns + 1 artifact column across the 19,132 readable files.

**2 genuine type conflicts**, same pattern again:

| Column | Types seen | Resolution |
|---|---|---|
| `ask_size` | BIGINT (19,035), DOUBLE (97) | **BIGINT.** Verified across 39,839,448 rows: zero non-whole values. |
| `bid_size` | BIGINT (19,048), DOUBLE (84) | **BIGINT.** Verified across 68,716,088 rows: zero non-whole values. |

**1 artifact column, not real data**: `__index_level_0__` (BIGINT, present
in 1,996/19,132 files = 10.4%). This is a pandas `DataFrame.to_parquet()`
serialization artifact (the row index written as a column when `index=False`
wasn't passed) — a meaningless per-file row-position integer with no
cross-file semantic meaning. **Resolution: drop, not included in the union
schema.** (Same artifact already independently identified in
`data/audit_reports/quotes_flagged_anomaly_files.csv`'s 2 pre-existing
flagged files, which are a separate, already out-of-scope anomaly.)

No `correction`/`trf_id`/etc.-style presence drift in this table — `ask_price`,
`bid_price`, `ask_size`, `bid_size`, `exchange`, `timestamp` are present in
100% of the 19,132 readable files.

## Summary of resolutions (no silent casts — every one verified)

| Table | Column | Native types | Resolved to | Verified by |
|---|---|---|---|---|
| `filtered_trades` | `size` | BIGINT/DOUBLE | BIGINT | Full scan, 1.18B rows, 0 fractional |
| `filtered_trades` | `participant_timestamp` | BIGINT/DOUBLE | BIGINT | Structural fact (double precision limit) + confirmed unused downstream |
| `filtered_quotes` | `ask_size` | BIGINT/DOUBLE | BIGINT | Full scan, 87.7M rows, 0 fractional |
| `filtered_quotes` | `bid_size` | BIGINT/DOUBLE | BIGINT | Full scan, 95.0M rows, 0 fractional |
| `raw_quotes` | `ask_size` | BIGINT/DOUBLE | BIGINT | Full scan, 39.8M rows, 0 fractional |
| `raw_quotes` | `bid_size` | BIGINT/DOUBLE | BIGINT | Full scan, 68.7M rows, 0 fractional |
| `raw_quotes` | `__index_level_0__` | BIGINT (10.4% of files) | **Dropped** | Pandas index artifact, not real data |

All other drift across all 3 tables is presence/absence only (a single,
consistent type per column) — resolved by union-then-NULL, no casting
required.
