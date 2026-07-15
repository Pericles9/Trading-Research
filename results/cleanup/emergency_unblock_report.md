# Emergency Unblock — Re-verification + Scoped Deletion Report

**Date:** 2026-07-11

## T1 — Independent full re-verification of the 1,561 migrated files

Ran V0.0's own audit logic (`get_schema_fingerprint`, `pick_timestamp_column`,
`detect_unit_and_check_granularity` from `auditdb.py`) against all 1,561 files,
not a spot-check. Checked four conditions per file: schema matches the intended
3-column output exactly, unit auto-detects as nanoseconds with magnitude > 1e17
(confirms the ms→ns conversion was applied), `pct_whole_second` < 0.999 (V0.0's
own corruption threshold), and row count > 0.

**Result: 1,561 / 1,561 PASS. Zero failures.**

(First run showed 0/1561 pass — traced to a bug in the verification script itself,
comparing DuckDB SQL type names against Parquet physical type names (`BIGINT` vs
`INT64`) and not accounting for the schema-group row. Fixed and re-run; the
underlying `unit_ok`/`granularity_ok`/`rows_ok` checks had already passed on the
first run, confirming the data itself was never in question.)

Full detail: `results/cleanup/migrated_1561_reverification.csv`.

## T2 — Safe-to-delete set

Safe set = every `high_momentum` file whose `(ticker, date)` either (a) already
has a `filtered/` counterpart unrelated to this migration (13,398 events — not
part of any pending decision), or (b) was migrated and passed T1 above (1,561
events, all 1,561 passed).

Excluded: all files backing the 4,341 still-pending events (3,146 broken/needs
retry + 1,195 never attempted) and the 47 blocked events (14 missing
`momentum_pct`, 33 with ≥10% null `sip_timestamp`). Independently confirmed the
excluded set is exactly 4,388 files (one `.parquet` per event, zero `.json`
sidecars — consistent with these all coming from the same later collection batch
that never wrote JSON metadata) and exactly matches 4,341 + 47 = 4,388.

- Safe files to delete: **30,297**
- Total size: **14.15 GB** (14,148,391,408 bytes)

Full list: `results/cleanup/safe_delete_set.csv`.

## T3 — Deletion executed

30,297 / 30,297 deleted. **0 errors.**

## T4 — Post-deletion verification

| Check | Result |
|---|---|
| `filtered/` dir count unchanged from post-migration state | 24,820 → 24,820 ✓ |
| `high_momentum` remaining file count | 34,685 → 4,388 (exact expected delta) ✓ |
| Remaining `high_momentum` events == expected pending+blocked set | exact set equality, 0 missing, 0 extra ✓ |
| `quote_data/` file count unchanged | 19,136 → 19,136 ✓ |
| `audit_reports/` file count unchanged | 13 → 13 ✓ |
| Disk space freed | ~14.1 GB freed (manifest predicted 14.15 GB) ✓ |
| Current free space on `D:` | ~14 GB (up from 2.9 MB) |
| Sufficient to resume migrating remaining 4,341 events (2× avg migrated-file-size × 4,341 = 7.42 GB threshold) | **Yes** — 14 GB > 7.42 GB |

## Current status

- `filtered/` now has 1,561 newly and validly migrated 2025 events added to its
  existing 23,260 directories.
- `high_momentum` now contains only the 4,388 files backing the 4,341 pending
  and 47 blocked events — nothing else.
- Disk space is no longer critical. Migration of the remaining 4,341 events can
  resume; the 47 blocked events still await review.
- Per this phase's approval gate: migration is **not** resumed and the 47
  blocked events are **not** acted on in this phase.
