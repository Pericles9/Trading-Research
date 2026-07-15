---
tags:
  - type/results
  - domain/data
  - project/vault
  - status/complete
created: 2026-07-11
---

# Minute/Trades Cleanup — Final Report

**Date:** 2026-07-11

## T1 — Schema check (fresh, not assumed)

`filtered/`'s current on-disk schema was re-sampled (8 random dirs): 3 variants
present, one of which is the minimal `(sip_timestamp BIGINT, price DOUBLE,
size BIGINT)` shape from the earlier trades migration — confirming that
convention is now part of the live corpus, not just a one-off.
`data/minute/trades/`'s `timestamp` column was confirmed as native
`TIMESTAMP_NS` (genuinely nanosecond-typed, though inspection showed the
low 3 digits are always zero — true microsecond precision, not full
nanosecond, still far finer than the 1% corruption bar). Schema was uniform
across a fresh 10-file random sample of the 1,303 unique-only files
specifically (not re-using the earlier overlap-set sample) — same 20-column
shape throughout. Subtractive fix: same 3-column output as before
(`sip_timestamp` derived from `timestamp` via `epoch_ns()`, `price`, `size`).

## T2 — 2020–2024 momentum_pct source

Did not reuse the 2025 sources. Found `data/momentum_events/full_2020_2024_momentum_scan_20251122_000515.parquet`
(18,660 rows, `ticker`/`date`/`momentum_pct` columns, 2020-01-03 to
2024-12-31 — covers all 1,303 target events with zero misses). Verified
against a known-good already-migrated event before trusting it at scale:
catalog says `CHEK 2020-01-09 → 30.22`; `filtered/`'s existing directory for
that event is literally named `CHEK_2020-01-09_30.22` — exact match.

## T3 — Migration and audit

1,303 / 1,303 migrated, 0 errors, 0 path collisions. Full audit (not
spot-check) on all 1,303: schema fingerprint, nanosecond-unit check,
`pct_whole_second` granularity (<0.999 bar) — **1,303 / 1,303 PASS, zero
failures.** `filtered/` event count: 29,208 → **30,511** (+1,303 exactly).

## T4 — Deletion

`data/minute/trades/` removed in full (18,630 files) — both the confirmed-duplicate
88.45 GB portion and the now-safely-migrated 1.67 GB portion, since the
latter's originals are redundant once verified elsewhere, per the approval
gate.

## T5 — Post-deletion verification

| Check | Before | After | Status |
|---|---|---|---|
| `data/minute/trades/` exists | 18,630 files | **gone** | ✓ |
| `data/filtered/` dir count | 30,511 (post-migration) | 30,511 | unchanged ✓ |
| `data/daily/` file count | 1,848 | 1,848 | unchanged ✓ |
| `data/minute/` (bars only, excl. `trades/`) | 24,590 | 24,590 | unchanged ✓ |
| `data/second10/` file count | 53,749 | 53,749 | unchanged ✓ |
| `data/illiquid_tests/` file count | 9 | 9 | unchanged ✓ |
| `data/quote_data/` file count | 19,136 | 19,136 | unchanged ✓ |
| `data/audit_reports/` file count | 13 | 13 | unchanged ✓ |
| Deletion errors | — | 0 | ✓ |

**Disk space:** `D:` used dropped from 443 GB to 359 GB — **~84 GB net freed**
(90.12 GB removed via deletion, offset by ~1.1 GB added to `filtered/` for
the 1,303 newly-migrated events in the compact 3-column format). Free space
on `D:`: 23 GB → **107 GB**.

## Status

`data/minute/trades/` no longer exists. All 1,303 previously-unique events
are now safely and verifiably present in `filtered/` alongside the rest of
the canonical corpus. Nothing else was touched. This closes out the
minute/trades investigation and cleanup.

One item carried forward, not addressed in this phase (per scope — this was
migration/deletion only): `src/data/ingest.py`'s `load_minute()` still has
the fallback code path written for `minute/trades/{TICKER}/{date}.parquet`
(see `minute_trades_investigation.md`, T3). That path is now permanently
dead — the directory it targets no longer exists — but the code itself
hasn't been touched, per this phase's read-only-except-migration/deletion
scope. Worth removing in a future ingestion-focused pass.
