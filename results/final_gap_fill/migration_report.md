# Final Gap-Fill — Report

**Date:** 2026-07-11

## Momentum_pct source correction

The suggested source, `data/filtered/scanner_hit_catalog.json`, was checked and
does **not** contain `momentum_pct` at all (it carries scanner-hit mechanics:
threshold, hit price, hit timestamp). `data/trade_data/momentum_events_for_collection.parquet`
was also checked and covers only 2024 (Jan–Dec), zero 2025 rows. The actual
authoritative source is `data/momentum_events/momentum_scan_2025.parquet`
(5,950 rows, 2025-01-03 to 2025-10-31) — all 47 blocked events found in it, and
cross-checked against a known-good already-migrated event (AACG 2025-07-21:
catalog says 40.24, matches exactly what was extracted from that event's trade
file during the earlier migration).

## T1 — Pull results

All 47 events pulled via `collect_massive_data_v2.py` (staged to
`data/trade_data/rebuild_validation_sample/`, 4 concurrent workers, ~101s total).

**47 / 47 written. 0 empty. 0 failed. 0 rate-limit hits. 0 auth errors.**

Notable: real trade counts came back far lower than the corrupted originals —
e.g. AUR: 29.99M corrupted rows → 157,573 genuine; AREB: 18.77M → 695,417;
DNOW: 25.91M → 23,529; ENTA: 10.10M → 14,776; CXAI: 7.84M → 225,586. This is
strong independent confirmation that the null-`sip_timestamp` corruption
diagnosed earlier was real, not a false positive — these tickers never had
tens of millions of trades in a day; the original files were genuinely exploded.

## T2 — Audit (schema + pct_whole_second, strict <1% bar)

**47 / 47 PASS.** All files carry `sip_timestamp` and `participant_timestamp`
in genuine nanosecond precision natively (no unit conversion needed this time —
unlike the earlier ms-scale batch). Schema is internally consistent with
`filtered/`'s existing drift pattern (`correction` present/absent, `size`
occasionally DOUBLE) — same shape as the canonical corpus, not a new anomaly.

Full detail: `results/final_gap_fill/pull_results.csv`.

## T3 — Fetch outcome

No failures to report. All 47 of the previously-blocked events are now
genuinely recoverable — the corruption was in the earlier collection run, not
in the underlying data's availability.

## T4 — Migration into `filtered/`

47 / 47 migrated, 0 errors, 0 path collisions, 0 missing `momentum_pct` lookups.
Same subtractive 3-column schema as the rest of this migration effort
(`sip_timestamp`, `price`, `size` — the only columns either downstream loader
reads by name), for consistency with the 5,902 already migrated.

## T5 — Post-migration validation

47 / 47 pass full validation (row count > 0, `sip_timestamp` genuinely
nanosecond-scale). `filtered/` event count: 29,161 → **29,208** (+47 exactly).

## T6 — Cleanup

Deleted all 47 originals from `high_momentum`. 0 errors.

| Check | Result |
|---|---|
| `high_momentum` remaining files | **0** |
| `quote_data/` file count | 19,136 → 19,136 unchanged |
| `audit_reports/` file count | 13 → 13 unchanged |
| Free space on `D:` | ~24 GB |

## Status

`high_momentum` is now completely empty (0 files) but the directory itself has
not been removed — per the approval gate framing ("once this completes...
`high_momentum` can be removed entirely" reads as permission for a follow-up
step, not an instruction bundled into this one). All 5,949 originally-unique
2025 events are now safely and verifiably present in `filtered/`: 5,902 from
the earlier migration + these 47. Nothing outstanding.
