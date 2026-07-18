# Phase 1b — Amendment 2: T4b Escalation Resolution

**Date:** 2026-07-18
**Resolves:** T4b hard stop (GTN.A_2025-06-12_31.87 — quotes.parquet never existed on disk; trades ingested cleanly, 885 rows), commit 0b3635a.
**Decision (Cooper):** The event stays in scope. Missing quote coverage is a recorded coverage fact, not an ingestion failure. Coverage becomes per-side, universe-wide.

Commit this file to `prompts/`, then resume at T4-R below and continue to T5.

---

## Tasks (insert before T5)

- [ ] **T4-R1 — Split the coverage flag on the canonical view**
  Replace `folder_ingested` with two columns, computed from the main tables (not the folder listing):
  - `trades_ingested` — > 0 rows in `filtered_trades` for (ticker, event window)
  - `quotes_ingested` — > 0 rows in `filtered_quotes` for (ticker, event window)
  `in_scope` continues to key off the trades side only. GTN.A_2025-06-12 lands as `trades_ingested = TRUE, quotes_ingested = FALSE, in_scope` per the normal D4/flag logic.
  - [ ] T4-R1a — Commit (view definition change touches `src/data/canonical.py` — instructed)

- [ ] **T4-R2 — Universe-wide trades-only count**
  Add `has_quotes_file` to `folder_inventory_v2.parquet` (from disk listing) and post one headline table: n folders with trades file but no quotes file, n events affected, split by instrument class and by year of `event_date_canonical`, each with n. **No further characterization** — the why belongs to Phase 4. This is a count, not an investigation.
  - [ ] T4-R2a — Cross-check: the count should be on the order of the known 24,200 − 22,660 = 1,540 file gap. If it differs from 1,540 by more than 50, note it in `surprises` and continue (do not stop — Phase 4 owns the explanation).
  - [ ] T4-R2b — Commit

- [ ] **T4-R3 — Rewritten escalation criterion (replaces the T4b row)**

  | Condition | Threshold | Action |
  |---|---|---|
  | Re-ingested folder with 0 rows post-ingest **where the source parquet existed on disk** | any | Hard stop |
  | Source parquet absent on disk | — | Record in inventory + report; not a stop |

  Re-verify the 7 recovered folders under the rewritten criterion and post the verification table. Expected: 7/7 pass (6 both-sides, 1 trades-only-by-source).
  - [ ] T4-R3a — Commit; resume original prompt at T5

---

## Changes to the original prompt (downstream)

1. **T5 fit population:** unchanged (it keys on ingested trades, which GTN.A has).
2. **T6 waterfall:** the terminal coverage split becomes three buckets: both-sides ingested / trades-only / no folder. Each with n.
3. **T7 dev sample v2:** eligibility now requires `in_scope = TRUE AND trades_ingested = TRUE AND quotes_ingested = TRUE`. A dev sample used for BBO/spread development cannot contain quote-less events.
4. **T8 CLAUDE.md block**, add one bullet:
   > - Coverage is per-side: `trades_ingested` and `quotes_ingested` on the canonical view. Any quote-derived statistic filters on `quotes_ingested = TRUE` and reports the n excluded by that filter. Trades-only events (~1,540-folder population, Phase 4 owns the explanation) are in scope for trade-side work only.
5. **Chart 03 (waterfall):** reflect the three-bucket terminal split.

---

## Approval Gate

Unchanged. No intermediate approval added.
