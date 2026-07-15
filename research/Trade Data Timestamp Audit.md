---
tags:
  - type/results
  - domain/data
  - project/src-core
  - status/needs-review
created: 2026-07-09
last_reviewed: 2026-07-09
---

# Trade Data Timestamp Audit

## Purpose

Phase V0.0 diagnostic: scan every trade file under `data/trade_data/high_momentum` for
schema drift and timestamp-precision corruption, gate the sweep with explicit escalation
criteria, and report findings for Cooper's review before any Phase V0 (Data Hygiene Audit)
or remediation work begins.

Scripts: `auditdb.py` (root, ad hoc dry-run tool) and `audit_full_sweep.py` (root, gated
full-sweep orchestrator — imports `auditdb.py`'s per-file logic unchanged).

## Decisions

1. **`auditdb.py` was non-functional and got fixed.** It assumed a nested
   `{TICKER}_{DATE}_{MOM}/trades.parquet` directory layout (that layout exists only under
   `data/filtered/`). The real target, `data/trade_data/high_momentum`, is flat `.parquet`
   files under two coexisting naming conventions — `TICKER_trades_YYYY_MM_DD.parquet`
   (legacy, 19,347 files) and `TICKER_YYYY-MM-DD_trades.parquet` (current, 970 files).
   Discovery always returned 0 directories, so the audit was silently a no-op. Rewrote
   `discover_event_dirs` → `discover_trade_files` to scan the flat files directly and added
   `parse_ticker_date` to handle both filename conventions.
2. **`audit_full_sweep.py` built as a separate gated orchestrator** rather than folding
   checkpointing/duplicate-detection/cross-tab logic into `auditdb.py`, so the original
   script stays a simple manual dry-run tool. Reuses `get_schema_fingerprint`,
   `pick_timestamp_column`, and `detect_unit_and_check_granularity` from `auditdb.py`
   unchanged.
3. **T1 escalation gate triggered on first run**: 20,317 discovered files vs. a ~34,000
   estimate (40.2% deviation, exceeding the 15% tolerance). Diagnosis at the time: total
   directory entries including paired `.json` sidecar files = 34,685 (within 2% of the
   estimate), suggesting the estimate counted all files, not just `.parquet` trade files.
   **Cooper confirmed 20,317 is the correct ground truth** — the ~34,000 figure was the
   original candidate-event count before paring down to the events trade data was actually
   pulled for. The file-count gate was disabled accordingly (`EXPECTED_FILE_COUNT_ESTIMATE
   = None` in `audit_full_sweep.py`) rather than deleted, so the reasoning stays in the code.
4. **Full sweep executed across all 20,317 files** with the gate disabled. Completed clean:
   0 unhandled exceptions, no checkpoint stalls, all five output artifacts written.

## Findings

### Schema fingerprint breakdown (file-weighted and trade-weighted)

| Schema category | Files | % files | Trades | % trades |
|---|---|---|---|---|
| `reduced_schema` (`timestamp`/`datetime`, no sip/participant timestamp) | 12,713 | 62.57% | 1,399,789,631 | 59.22% |
| `richer_schema_sub_ns_scale` (`sip_timestamp`/`participant_timestamp` present) | 5,949 | 29.28% | 866,101,177 | 36.64% |
| `malformed_exploded` (`element`/`list`/`__index_level_0__` — looks like a broken pandas `.explode()`) | 1,655 | 8.15% | 97,967,763 | 4.14% |
| **Total** | **20,317** | 100% | **2,363,858,571** | 100% |

Note: `richer_schema_sub_ns_scale` is a slight misnomer carried over from the dry run —
`sip_timestamp` values in this dataset are actually millisecond-scale (13 digits), not
true nanosecond Polygon timestamps. Flagged, not yet investigated further.

### Whole-second timestamp corruption

12,819 files (63.09%) / 1,406,673,941 trades (59.51%) have ≥99.9% of trades landing on a
whole second. Corruption is **not** perfectly confined to `reduced_schema`: 12,713
corrupted files are `reduced_schema`, but **106 additional corrupted files are
`malformed_exploded`** — none of the `richer_schema_sub_ns_scale` files show whole-second
corruption.

### Duplicate ticker+date pairs

970 duplicate groups (every current-convention file has a legacy-convention counterpart
for the same ticker+date — accounts for all 970 current-convention files).

- **596 groups**: exact `n_trades` match between the two files (byte-for-byte duplicate
  suspicion).
- **374 groups**: `n_trades` differs, often by an order of magnitude — independent
  re-collections, not copies. Top examples by volume: AMC 2021-01-27 (384,997 legacy vs.
  6,696,486 current), OCGN 2021-02-08 (357,000 vs. 3,361,742), GME 2021-01-27 (393,997 vs.
  3,151,694).

### Mtime-vs-schema cross-tab

- `reduced_schema` (12,713 files) mtimes span exactly two calendar dates:
  **2025-11-24 (3,020 files)** and **2025-11-25 (9,693 files)**.
- `richer_schema_sub_ns_scale` variants mostly mtime **2025-11-27** (5,867 files across 3
  sub-variants), with a smaller set on 2026-01-14/01-15 (68 files).
- `malformed_exploded` variants mostly mtime **2026-01-14/01-15**; the 106
  corrupted-and-malformed files are all mtime **2026-01-15** specifically — a distinct,
  more recent event from the reduced-schema corruption window.

Explicit percentages:
- % of ALL files with mtime = 2025-11-24: **14.86%**
- % of CORRUPTED files with mtime = 2025-11-24: **23.56%** (remaining 76.44% are 2025-11-25)
- % of NON-CORRUPTED files with mtime = 2025-11-24: **0.00%**

These numbers are reported plainly per the Phase V0.0 spec — no conclusion is drawn here
on whether they confirm or refute the bulk-rewrite-on-2025-11-24 hypothesis; that call is
Cooper's once he's reviewed the table.

## Escalation check table (final run)

| Criterion | Observed | Threshold | Result |
|---|---|---|---|
| File count vs original estimate | 20,317 files (gate disabled per Cooper's confirmation) | n/a | PASS |
| Unparsed ticker/date filenames | 0 | ≤ 50 | PASS |
| Unhandled exceptions during sweep | 0 | 0 | PASS |
| Checkpoint stall | none observed | ≤ 30 min | PASS |

## Output Artifacts

| File | Contents |
|------|----------|
| `data/audit_reports/timestamp_audit_full.csv` | Per-file schema fingerprint, timestamp unit, `pct_whole_second`, `n_trades`, `file_mtime` — all 20,317 files |
| `data/audit_reports/duplicate_ticker_date_pairs.csv` | All 970 duplicate `(ticker, date)` groups with per-file `n_trades` comparison |
| `data/audit_reports/mtime_schema_crosstab.csv` | `schema_fingerprint` × mtime date min/max/nunique |
| `data/audit_reports/unparsed_filenames.txt` | Filenames matching neither naming regex (empty — 0 found) |
| `data/audit_reports/summary_rollup.json` | File- and trade-weighted schema/corruption summary |

## Status

**Approval gate open.** Do not begin Phase V0 (Data Hygiene Audit) or any
remediation/rebuild work until Cooper has reviewed these findings and given explicit
approval.

## Related

- [[Data Index]] — data-layer module documentation hub
- [[DuckDB Ingest]] — 11-loader ingestion pipeline these trade files feed into
- [[Audit Suite]] — companion 4-audit forensic diagnostics for backtest results
- [[Schema]] — documented (aspirational) trade data schema, now known to diverge from
  what's actually on disk in `high_momentum`
