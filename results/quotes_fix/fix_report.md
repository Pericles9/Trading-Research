---
tags:
  - type/results
  - domain/data
  - project/src-core
  - status/complete
created: 2026-07-11
linked_code: "[[quotes_fix]]"
---

# Quotes Migration Fix — Final Report

## Summary

Of the 5,871 events broken by the 2025 gap-fill migration's quotes
path-construction bug, **5,800 (98.8%) are now fixed** — `quotes.parquet`
correctly placed in the existing, correctly-named `filtered/` folder,
schema-fingerprint and row-count verified against source. **71 (1.2%) remain
unfixed**, each with a specific, documented reason, and each still marked by
a visible empty `{TICKER}_None_{momentum}` placeholder folder.

## 1. Coverage result (T1)

| | Count |
|---|---|
| Target events (bug signature) | 5,871 |
| Matched in `quote_data/` | 5,813 |
| **No `quote_data/` source** | **58** |

Full per-event list: `coverage_check.csv`. The 58 unmatched events have no
recovery path via this source — they would need a fresh API pull, same as
the earlier 47-event final-gap-fill case.

## 2. Schema check result (T2)

Original check hard-stopped on an ambiguous `participant_timestamp` mapping.
Resolved by two follow-up investigations (see `schema_check.md` for full
detail):
- Column-usage scan confirmed only 5 of `filtered/`'s 12 quote columns are
  read by any downstream code: `sip_timestamp`, `bid_price`, `ask_price`,
  `bid_size`, `ask_size`.
- Direct row-level join confirmed `quote_data.timestamp == sip_timestamp` and
  `quote_data.exchange == participant_timestamp` exactly (100% match) — but
  `participant_timestamp` is unused, so only the `timestamp → sip_timestamp`
  mapping actually matters, and that one is unambiguous.

**Fix used a subtractive 5-column schema**: `sip_timestamp` (from
`quote_data.timestamp`), `bid_price`, `ask_price`, `bid_size`, `ask_size`.
Nothing invented, nothing derived from an unconfirmed mapping.

A separate, independent finding (`row_count_gap_investigation.md`) also
applies: `quote_data/` is a single-session (4am–8pm ET) capture, while
`filtered/`'s existing files carry multi-day context. **Every one of the
5,800 recovered files is single-session only** — any downstream calculation
that needs pre-event days (e.g. a `T-3`…`T-1` baseline window) will find no
quote data outside the event session for these 5,800 specific events. This
is a known, accepted limitation of this recovery path, not an oversight.

## 3. Fix outcome (T3–T5)

| Disposition | Count | Detail |
|---|---|---|
| **Fixed** | **5,800** | Copied, schema+row-count verified (15-file spot check, 100% exact match) |
| No `quote_data/` source | 58 | Listed in `coverage_check.csv` (`found_in_quote_data=False`) |
| Excluded — flagged anomaly | 12 | Implausible in-session quote volume (>2M rows); see below |
| Excluded — source file corrupted | 1 | `PLRZ_quotes_2025_07_23.parquet` — CRC (cyclic redundancy check) error reading the file, disk-level corruption in the source, not a code issue |
| **Total unfixed** | **71** | 58 + 12 + 1 |
| **Total target** | **5,871** | 5,800 + 71 ✓ |

### T3a — Flagged anomalies excluded from the bulk copy (12 events)

The task's named examples (AUR 2021-11-19, and a 2020-03 COVID-week cluster)
turned out **not to be in the 5,871 target set at all** — they came from the
separate 600-event control sample used for the row-count-gap investigation,
not from the broken-events list. Checked directly; confirmed no overlap.

Applying the same anomaly signature those examples represent (implausible
in-session quote volume) directly to the actual 5,813 matched targets found
**12 events** exceeding 2,000,000 rows in a single 16-hour session (vs. a
clean-sample maximum of 1,630,662 legitimate rows and a median of ~20,000):

| Ticker | Date | Rows | Notes |
|---|---|---|---|
| DNOW | 2025-02-13 | 81,628,164 | Matches a ticker already documented as trades-corrupted in `results/final_gap_fill/migration_report.md` ("DNOW: 25.91M corrupted → 23,529 genuine") |
| ENTA | 2025-02-13 | 28,230,812 | Same — already documented ("ENTA: 10.10M corrupted → 14,776 genuine") |
| AREB | 2025-01-07 | 5,143,253 | Same — already documented ("AREB: 18.77M corrupted → 695,417 genuine") |
| TQQQ | 2025-04-09 | 8,484,210 | Not previously documented; all-distinct-timestamp signature matching the confirmed AUR corruption pattern |
| TSLL | 2025-04-09 | 3,116,280 | Same signature |
| NVDL | 2025-04-09 | 2,603,740 | Same signature |
| NVDU | 2025-04-09 | 2,175,330 | Same signature |
| TSLQ | 2025-06-05 | 2,633,609 | Same signature |
| OPEN | 2025-07-21 | 2,908,455 | Same signature |
| BYND | 2025-10-21 | 2,407,028 | Same signature |
| BYND | 2025-10-22 | 3,451,945 | Same signature |
| INTC | 2025-09-18 | 2,150,304 | Same signature |

Cross-checked against the existing `data/audit_reports/quotes_flagged_anomaly_files.csv`
(a prior, differently-scoped audit for schema-fingerprint anomalies) — **zero
overlap**; that audit's 2 flagged files (EDUC, PNBK) are a different anomaly
class entirely. This row-count screen is a new finding, not a re-discovery.
Full list: `flagged_anomalies.csv`. **Not recovered, not deleted — the
`None` placeholder folders for these 12 events were left in place.**

### T5 — Placeholder cleanup

- 5,791 empty `None` placeholder folders deleted (one per fixed event).
- 9 fixed events had no placeholder to delete at copy time — traced to 5
  `(ticker, momentum)` key collisions where two different fixed events
  (different dates) coincidentally shared one placeholder folder name; the
  first deletion in each pair already removed it. No data issue — both
  sibling events were still correctly fixed in T3.
- **Edge case found and corrected**: the same key-collision pattern also hit
  4 *unfixed* events (`SSII` 2023-06-06, `VBIX` 2025-02-13, `WLDSW`
  2023-01-30, `WLDSW` 2023-10-18) — each shared its placeholder key with a
  *fixed* sibling, so the marker was deleted when the fixed sibling was
  cleaned up, silently removing the "visible marker of the remaining gap"
  the task required. Caught by verifying marker survival for all 71 unfixed
  events post-cleanup; recreated the 3 missing empty placeholder directories
  (`WLDSW`'s two unfixed events share one directory). **Verified: all 71
  unfixed events now have a surviving marker.**
- Final placeholder count: 114 `_None_` directories remain — 47 for the
  strict-ticker-format unfixed events (44 originally survived + 3
  recreated) and 64 for the separate, out-of-scope special-character-ticker
  gap (untouched throughout).

## 4. Updated `filtered/` quotes-completeness picture

| | Before this fix | After this fix |
|---|---|---|
| Regex-valid event folders (`filtered/`) | 24,200 | 24,200 (unchanged — no folders added/removed) |
| Folders with `trades.parquet` | 24,200 | 24,200 |
| Folders with `quotes.parquet` | 16,860 | **22,660** |
| Folders missing `quotes.parquet` | 7,340 | **1,540** |

Of the remaining 1,540 gap:
- **1,469** — the separate, pre-existing gap with no matching `None` folder
  (different root cause, out of scope for this fix, per the original task).
- **71** — this fix's leftovers (58 no-source, 12 flagged-anomaly, 1
  CRC-corrupted source), each individually documented above.

The 409 special-character-ticker folders (e.g. `ACHR.WS`) remain a fully
separate, untouched issue — not counted in the numbers above since they
don't match the loader's ticker regex at all.

## What this means for the paused DuckDB ingestion task

`filtered_quotes` (via `load_filtered`) will now load from 22,660 event
folders instead of 16,860 — the expected-count baseline for that table's T6
verification should be set accordingly, not to the original 30,511 or any
earlier partial figure. `filtered_trades` is unaffected by this phase (still
24,200, per the earlier trades-count investigation). No DuckDB ingestion was
run in this phase — `data/duckdb/main.duckdb` is untouched, still empty.
