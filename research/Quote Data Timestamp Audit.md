---
tags:
  - type/results
  - domain/data
  - project/src-core
  - status/needs-review
created: 2026-07-09
last_reviewed: 2026-07-09
---

# Quote Data Timestamp Audit

## Purpose

Phase V0.0b diagnostic: sibling to [[Trade Data Timestamp Audit]] (Phase V0.0), not a
dependent phase — does not gate, and is not gated by, the trades-corpus rebuild decision.
Verifies at full-corpus scale that quote timestamps carry genuine nanosecond precision,
following up Cooper's informal spot check during the quote-noise investigation, so the
"quotes are clean" conclusion rests on measurement rather than a spot check.

Script: `audit_quotes_sweep.py` (root) — imports `get_schema_fingerprint` and
`detect_unit_and_check_granularity` unchanged from `auditdb.py`; only file discovery and
the timestamp-column priority list are quote-specific.

## Decisions

1. **Corpus located empirically, not assumed to mirror trades** (per the phase spec's
   explicit instruction, given the trades layout had already been wrong twice). Found at
   `data/quote_data` — flat `.parquet` files, no subdirectories, no `.json` sidecars.
   19,136 files discovered, all matching a **single** naming convention:
   `TICKER_quotes_YYYY_MM_DD.parquet`. Unlike trades, there is no second dash-date
   convention here. 0 unparsed filenames.
2. **Timestamp column candidates adapted for quotes**: `sip_timestamp` →
   `participant_timestamp` → `ask_timestamp` → `bid_timestamp` → `timestamp`, falling back
   to any bare non-metadata column if none match. In practice, **no file in any sample
   carried a named candidate** — every file falls back to a bare `timestamp` column, which
   showed genuine ~19-digit nanosecond-epoch values in pre-sweep spot checks.
3. **T1 gates passed without intervention**: 19,136 files vs. the known 20,317 trades
   count is a 5.8% deviation (within the 20% tolerance); 0 unparsed filenames (within the
   50-file tolerance).
4. **T2 escalation fired once, then was overridden.** The per-file `pct_whole_second >=
   10%` criterion hit at file ~5,465/19,136 (`EDUC_quotes_2020_08_07.parquet`, 22.02%
   whole-second). Per spec this is a hard stop — reported per the escalation format and
   held for instruction. **Cooper reviewed and instructed the sweep to proceed** rather
   than hard-stop on every such file. The script was amended: this criterion now logs
   and continues (flagged files are still collected in full and reported explicitly, not
   averaged into the rollup) instead of raising. All other escalation criteria (unhandled
   exceptions, unparsed filenames, count deviation, checkpoint stall) remained hard stops
   and were not touched. The sweep resumed from the existing checkpoint (5,466 files
   already done) and completed all 19,136 files.

## Findings

### Schema fingerprint breakdown (file-weighted and record-weighted)

| Schema category | Files | % files | Records | % records |
|---|---|---|---|---|
| `bare_timestamp_schema` (ask/bid price+size, exchange, timestamp) | 17,136 | 89.55% | 1,430,795,721 | 81.36% |
| `pandas_index_leak_schema` (adds `__index_level_0__`) | 1,996 | 10.43% | 327,718,804 | 18.64% |
| `other` (unreadable — see below) | 4 | 0.02% | 0 | 0.00% |
| **Total** | **19,136** | 100% | **1,758,514,525** | 100% |

### 4 files are unreadable at the file-system level — not a timestamp/schema issue

These failed inside DuckDB's `parquet_schema()` metadata read itself (caught by
`get_schema_fingerprint`'s existing internal try/except, so they did not count as
"unhandled exceptions" against the escalation criterion, but they are a genuine and
more serious finding than schema drift):

| File | Error |
|---|---|
| `POLA_quotes_2020_11_23.parquet` | `IO Error: ... Data error (cyclic redundancy check)` |
| `RR_quotes_2024_09_23.parquet` | `IO Error: ... Data error (cyclic redundancy check)` |
| `CING_quotes_2024_08_16.parquet` | `Invalid Input Error: File too small to be a Parquet file` |
| `CLRO_quotes_2023_05_09.parquet` | `Invalid Input Error: File too small to be a Parquet file` |

CRC errors indicate on-disk bit-level corruption (bad sectors / incomplete write); the
"too small" errors indicate truncated files. All four have `file_mtime` of 2026-01-11,
the same date the bulk of the corpus was rewritten (see cross-tab below) — consistent
with, but not proof of, an interrupted or partially-failed rewrite on that date.

### Whole-second anomaly (>=10% threshold — not the 99.9% corruption bar used for trades)

Only **2 of 19,136 files (0.01%)** exceed the 10% anomaly threshold, together **3,956,073
records (0.22%)** of the corpus. Corpus-wide `pct_whole_second` mean is **1.85e-05**
(0.0019%), max is **0.2202** (22.02%) — consistent with Cooper's "clean" spot check at
full-corpus scale, with two specific exceptions:

| File | Date | `pct_whole_second` | Records | Unique timestamps | `file_mtime` |
|---|---|---|---|---|---|
| `EDUC_quotes_2020_08_07.parquet` | 2020-08-07 | 0.2202 | 3,954,002 | 3,630,290 | 2026-01-15T08:30:49 |
| `PNBK_quotes_2020_08_06.parquet` | 2020-08-06 | 0.1212 | 2,071 | 1,945 | 2026-01-14T22:36:10 |

Both flagged files carry the `pandas_index_leak_schema` fingerprint and both have
`file_mtime` in the 2026-01-14/01-15 window — the same rewrite batch as the rest of that
1,996-file schema category (see below), not an isolated one-off. Only 2 of that batch's
1,996 files show the anomaly, though — it is not a category-wide effect.

### Duplicate ticker+date pairs

**0 duplicate groups.** Expected: quotes has only one naming convention, so filenames are
inherently unique per (ticker, date) — there is no second convention to create a
trades-style duplicate pair.

### Mtime-vs-schema cross-tab

- The overwhelming majority of `bare_timestamp_schema` files (17,011 of 17,136) share
  `file_mtime` = **2026-01-11**, a single calendar date — the entire corpus appears to
  have been rewritten in one pass on that date.
- The 4 unreadable files also have `file_mtime` = 2026-01-11.
- `pandas_index_leak_schema` files (1,996) mostly span **2026-01-14 to 2026-01-15** (a
  2-day window) — a distinct, later touch than the main 2026-01-11 rewrite.
- This is a materially different rewrite signature than trades' 2025-11-24/25 window —
  the quotes corpus was touched roughly two months later and, unlike trades, that rewrite
  did not introduce systemic whole-second truncation.

## Escalation check table (final run)

| Criterion | Observed | Threshold | Result |
|---|---|---|---|
| Quote file count vs. known trades count (20,317) | 19,136 files (5.8% deviation) | within 20% | PASS |
| Unparsed ticker/date filenames | 0 | ≤ 50 | PASS |
| Unhandled exceptions during sweep | 0 (4 read errors caught internally, see above) | 0 | PASS |
| Any single file `pct_whole_second` | max 0.2202; 2 files ≥ 10% | < 10% (**overridden 2026-07-09** — log-and-continue per Cooper, not hard-stop) | FAIL (accepted) |
| Checkpoint stall | none observed | ≤ 30 min | PASS |

## Output Artifacts

| File | Contents |
|------|----------|
| `data/audit_reports/quotes_timestamp_audit_full.csv` | Per-file schema fingerprint, timestamp unit, `pct_whole_second`, record count, `file_mtime` — all 19,136 files |
| `data/audit_reports/quotes_duplicate_ticker_date_pairs.csv` | Empty — 0 duplicate groups |
| `data/audit_reports/quotes_mtime_schema_crosstab.csv` | `schema_fingerprint` × mtime date min/max/nunique |
| `data/audit_reports/quotes_naming_conventions_found.txt` | Derived naming pattern (single convention) |
| `data/audit_reports/quotes_unparsed_filenames.txt` | Empty — 0 unparsed |
| `data/audit_reports/quotes_summary_rollup.json` | File- and record-weighted schema/anomaly summary |
| `data/audit_reports/quotes_flagged_anomaly_files.csv` | The 2 files ≥ 10% whole-second, full detail (not averaged away) |

## Status

**Approval gate open.** Do not conclude `quotes.parquet` needs no remediation, and do not
begin any quotes-dependent hygiene work (Q1–Q4 in Hawkes_Impact_v2 §4.3), until Cooper has
reviewed these findings and given explicit approval. This phase does not block, and is not
blocked by, the trades corpus rebuild proceeding independently.

## Related

- [[Trade Data Timestamp Audit]] — sibling Phase V0.0 trades audit; same method, disjoint corpus
- [[Data Index]] — data-layer module documentation hub
- [[DuckDB Ingest]] — ingestion pipeline these quote files feed into
- [[Schema]] — documented trade/quote schema, for comparison against what's actually on disk
