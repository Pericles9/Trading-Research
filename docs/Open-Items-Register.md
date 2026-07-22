<!-- fullWidth: false tocVisible: true tableWrap: true -->
---
tags:
  - type/register
  - domain/data
  - status/live
created: 2026-07-20
last_reviewed: 2026-07-20
---

# Open Items Register

Standing, append-only log of items surfaced during a phase but explicitly **not resolved**
in that phase — not a bug tracker, not a TODO list for the next phase's scope. An item
stays here until a phase explicitly takes it on and closes it out (with a dated closure
note, not a deletion).

No pre-existing register was found anywhere in the repo as of Phase 2 T8 (checked `docs/`,
`Research-Library-Map.md`, `Mom-DB-Strategy-Research-Program.md`) — this file is newly
created per Phase 2's T8 addendum instruction to "log verbatim to the register."

---

## Open

- **47 kept-back `high_momentum` events untraced 07-11→E:-migration.** `results/cleanup/deletion_report.md` (2026-07-11) documents 47 confirmed-lost/blocked events deliberately kept back (not deleted) in `high_momentum/` on D:. Phase 2 T3a found `high_momentum/` fully absent on E: (0 files) — the 47 are gone too, not just the migrated 5,902. Their fate between 2026-07-11 and the D:→E: hardware migration (2026-07-12) has not been traced. — logged Phase 2 T8.
- **`enhanced/` + `rebuild_validation_sample/` unread under quarantine.** Both exist under `data/trade_data/` (confirmed via directory listing in Phase 2 T3a) but are outside every phase's authorized path list so far and outside CLAUDE.md's `trade_data/` quarantine exceptions. Contents (row counts, schema, provenance) are unknown. — logged Phase 2 T8.
- **`Schema.md` stale on `trade_data/` structure.** `data/Schema.md`'s `trade_data/` row lists subfolders `batches/`, `by_date/`, `by_ticker/`, `enhanced/`, `high_momentum/`, `logs/`, `metadata/`. Phase 2 T3a found the actual E: top level is `collection_progress.json`, `enhanced/`, `high_momentum_progress.json`, `momentum_events_for_collection.parquet`, `optimized_progress.json`, `rebuild_validation_sample/`, `robust_progress.json`, `ultra_optimized_progress.json` — `batches/`, `by_date/`, `by_ticker/`, `high_momentum/`, `logs/`, `metadata/` are all absent; `rebuild_validation_sample/` isn't documented at all. `Schema.md` not corrected this phase (out of scope). — logged Phase 2 T8.
- 2025 T=0 data quality: 91.5% of 2025 in-scope events are fully the 3-column migrated schema (price/sip_timestamp/size only) — no exchange, participant_timestamp, or correction fields even on the event day. Any future 2025 analysis is structurally incapable of venue, condition-code, or SIP-vs-participant timing work until recollected. Source: Phase 2 REPORT §2 migration-signature facet.
- **37 in-scope file2 (2025) events have no quotes.parquet at all on disk.** Phase 4 T3's disk↔DB↔spine reconciliation of the 1,606-folder trades/quotes gap found 37 folders that are `in_scope=TRUE`, `source_file='file2'`, disk-level `presence_class='trades_only'` (no quotes file at all). This phase's 386-cohort classification (T4/T5) is scoped to `source_file='file1'` only, matching Phase 1b/2/3's precedent for file1-vs-file2 (2025) treatment — these 37 events were located but not bitmapped or classified. — logged Phase 4 T3/T8, 2026-07-21.

## Closed

- **Dev sample re-pinned v2→v3.** `config/dev_sample_v2.json`'s eligibility rule predated `coverage_class` (Phase 2 T8) and never screened T-3..T+3 window completeness — Phase 3 T2 found 15/50 v2 events were `event_day_only`. Re-pinned as v3 (`config/dev_sample_v3.json`, same seed 42, same decile stratification, eligibility rule adds `coverage_class='full_window' AND quotes_full_window=TRUE`). v2 remains committed as the historical sample, not deleted. — closed Phase 3 Amendment 1 (A1-T5), 2026-07-21.
- **venv calendar-library drift vs. the phase 1c pin.** `config/phase_1c.json` pins `pandas_market_calendars` 5.4.0 / `exchange_calendars` 4.13.2. The project `.venv` had 5.3.0 / 4.12 installed (confirmed Phase 2 T4). Phase 2 used the installed version rather than upgrading the shared venv, documented the drift, and judged the risk low for the 2019-12-01..2026-01-15 derivation range. Phase 3 post-approval review made the risk non-hypothetical (T3's classification depends on expected-session arithmetic) and verified harmlessness via an isolated install diff: byte-for-byte identical, 1,539/1,539 sessions, 0 diffs (`results/phase_3/artifacts/calendar_pin_verification.json`) — but left the shared venv itself uncorrected. **Closed Phase 4 T0b, 2026-07-21:** installed `pandas_market_calendars==5.4.0` and `exchange_calendars==4.13.2` directly into the shared `.venv` (no dependency conflicts on install); re-verified with a fresh diff against an isolated install of the old drifted versions — identical, 1,539/1,539 sessions, 0 diffs. See `results/phase_4/artifacts/t0b_versions.json`.
- **Quotes-side coverage gap (386 cohort) root-cause classified.** Phase 3 T3c identified the 386-event quotes cohort (`source_file='file1' AND quotes_full_window=FALSE`) but did not classify it. Phase 4 T2-T6 ran the full census/reconciliation/bitmap/classification/log-correlation pipeline: 0/386 unclassified, bitmap-first labels backward_missing=217/both_sides=150/forward_missing=19/archive_edge=0, with a Phase-3-precedence crosswalk (`label_p3_precedence`) computed alongside for comparability. See `results/phase_4/REPORT.md`, `results/phase_4/artifacts/classification_summary.json`. — closed Phase 4 T8, 2026-07-21.
