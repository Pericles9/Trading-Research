# Trades Cleanup — Final Deletion Report

**Date:** 2026-07-11

## Summary

Migration of all 5,902 verified-clean 2025 gap events into `filtered/` is complete
and fully validated. `high_momentum`'s originals have been deleted for every event
with a verified copy in `filtered/`. The 47 events with no safe copy anywhere are
**kept, not deleted** — see "Deviation from literal T4" below.

## T1 — Clean vs. confirmed-lost (final)

Of the 5,949 `(ticker, date)` pairs unique to `high_momentum`:

| Bucket | Count | Reason |
|---|---|---|
| Migrate-eligible (clean) | 5,902 | schema=`richer_schema_sub_ns_scale`, `pct_whole_second`<10%, `momentum_pct` present, <10% null `sip_timestamp` |
| Confirmed-lost / blocked | 47 | 14 missing `momentum_pct` column entirely; 33 with ≥10% null `sip_timestamp` (one as high as 99.9%) |

Full list: `results/cleanup/confirmed_lost_events.csv`. This is unchanged from
what was reported earlier in this project — no new information has come in on
these 47 since then, and they still await an individual decision (accept the
loss, or re-pull via `collect_massive_data_v2.py`).

## T2/T2g — Migration (in two batches due to the disk-full incident)

- Batch 1 (before disk-full): 1,561 migrated and independently re-verified (1,561/1,561 PASS).
- Batch 2 (after emergency unblock, with the new disk-space guard): remaining 4,341 migrated, 0 errors. Guard checked free space every 200 files; never dropped below the 1GB floor (ended at 10.82 GB free).
- **Total migrated: 5,902 / 5,902.**

Schema applied uniformly: subtractive 3-column output (`sip_timestamp`, `price`,
`size` — the only columns either downstream loader reads by name), with
`sip_timestamp` converted ms→ns (×1,000,000) to match `filtered/`'s canonical
unit, and corrupted rows (null `sip_timestamp`/`price`/`size`) dropped at copy
time.

## T3 — Post-migration validation

Full audit (not spot-check) of all 5,902 migrated files using V0.0's own audit
logic (schema fingerprint, unit auto-detection, `pct_whole_second` granularity):

**5,902 / 5,902 PASS. Zero failures.**

- T3a: `filtered/` event count increased by exactly 5,902 (23,259 → 29,161).
  (First check showed an apparent 1-directory discrepancy — traced to my own
  original baseline count missing a third non-event file, `scanner_hit_catalog.json`,
  which happened to also split into 3 underscore-parts and slipped past the
  original validation regex. Not a real anomaly; corrected baseline matches exactly.)

Full detail: `results/cleanup/migration_validation.csv`.

## T4 — Deletion (with one deliberate deviation from the literal instruction)

The addendum's T4 text says to delete `high_momentum` "in full... since
verified copies now exist in `filtered/`." That justification is true for
5,902 events and **not true** for the 47 blocked events — no verified copy of
those exists anywhere. Deleting them now would be irreversible data loss with
no backup, which contradicts the approval gate in both this document and its
predecessor ("if the confirmed-lost list is non-trivial, surface it clearly
before deletion") and the explicit instruction not to invent/backfill missing
data. I deleted only the 5,902 events' originals and **kept the 47 blocked
events' source files** in `high_momentum` pending your decision.

- Deleted this session: 30,297 (first batch, always-safe duplicates + first
  migrated batch) + 4,341 (second batch, remainder) = **34,638 files total**.
- Remaining in `high_momentum`: **47 files** — exactly the blocked events, byte-for-byte.

## T5 — Post-deletion verification

| Check | Before this batch | After | Status |
|---|---|---|---|
| `filtered/` dir count | 29,161 | 29,161 | unchanged ✓ |
| `high_momentum` file count | 4,388 | 47 | exact expected delta (-4,341) ✓ |
| `quote_data/` file count | 19,136 | 19,136 | unchanged ✓ |
| `audit_reports/` file count | 13 | 13 | unchanged ✓ |
| Deletion errors | — | 0 | ✓ |

**Disk space:** ~22 GB free on `D:` (up from 2.9 MB at the low point of the
disk-full incident). ~12.59 GB freed by this batch's deletion, on top of the
~14.15 GB freed in the emergency-unblock phase.

## What's left

`high_momentum` now contains only the 47 blocked events (14 missing
`momentum_pct`, 33 corrupted `sip_timestamp`). Nothing else remains to migrate.
The only open decision is what to do with those 47 — awaiting your call.
