# Phase 1c — Amendment 2: T6 Escalation Resolution (Collision Guard + SDOT Remediation)

**Date:** 2026-07-19
**Resolves:** T6 hard stop — SDOT 2025-10-13 quote heal inserted 1,604 rows on top of 1,603 pre-existing archive quote rows (trades were genuinely 0 for that session; quotes had partially collected). Whole-population scan found exactly 2 affected pairs: SDOT (inserted, needs remediation) and SHMD (caught pre-insertion). Commit f5594a0.
**Root cause:** T1's heal targets were derived calendrically, on the assumption that the calendar bug failed trades and quotes together per session. It can fail them independently. The manifest therefore contained (ticker, session, side) targets that already had rows, and the write path had no pre-insertion collision check. The original "rows never select targets" rule was correct for *selection* but left *collision-before-write* unguarded.
**Decision (Cooper):** Add a per-session-per-side collision guard as a standing safeguard. Heal fills absence only, never supplements presence. Remediate SDOT by removing this phase's inserted rows and re-healing under the guard.

Commit this file to `prompts/`, then execute T6-R below before resuming ingestion of remaining targets.

---

## Tasks

- [ ] **T6-R1 — Pre-insertion collision guard (standing, applies to all remaining and future ingests)**
  Before writing any heal pair to the main tables, per side independently: query the target table for existing rows at (ticker, session). Branch:

  | Existing rows at (ticker, session, side) | Action |
  |---|---|
  | 0 | Heal normally (this is genuine absence — the only case heal is authorized to fill) |
  | > 0 | **Skip this side's heal for this session.** Record `skipped_collision` with the pre-existing row count in the ledger. Do not merge, dedupe, or supplement. |

  The guard runs at write time regardless of what the manifest says — the manifest was derived on an assumption now known to be incomplete, so the table state at write time is authoritative, not the manifest.
  - [ ] T6-R1a — Re-scan all remaining un-ingested targets with the guard applied; post the full collision list (expected: SHMD quotes 2025-10-13, plus SDOT quotes once its inserted rows are removed in T6-R2). Any collision beyond the 2 already found → post it, not a stop (the guard handles it), but note under `surprises`.
  - [ ] T6-R1b — Commit

- [ ] **T6-R2 — SDOT remediation (surgical removal, not in-place edit)**
  From the repair ledger, identify the exact 1,604 quote rows this phase inserted for SDOT 2025-10-13. Remove precisely those rows — restoring the table to its 1,603 pre-existing original quotes for that session, untouched.
  - [ ] T6-R2a — Verification: post-removal quote count at SDOT 2025-10-13 == 1,603 (the pre-heal original). Also confirm SDOT's row counts at every **other** session this phase touched are unchanged. Any deviation → hard stop.
  - [ ] T6-R2b — Delete the `quotes_repair_1c.parquet` sibling written for SDOT 2025-10-13 (the trades sibling stays — SDOT's trades gap is real and heals in T6-R3). Ledger updated to `skipped_collision` for that pair's quote side.
  - [ ] T6-R2c — Commit

- [ ] **T6-R3 — Complete SDOT and SHMD under the guard**
  - SDOT 2025-10-13: trades side (archive 0 rows) heals normally if not already ingested; quotes side skipped per guard.
  - SHMD 2025-10-13: trades side heals normally; quotes side skipped (357 pre-existing rows per the T6 findings).
  - [ ] T6-R3a — Post-ingest check per the original T6 rule (table count == staged count) for the trades heals only. Commit.

- [ ] **T6-R4 — Resume remaining ingestion**
  Process all remaining verified heal pairs through the guarded write path. Every pair passes the T6-R1 guard before insertion.
  - [ ] T6-R4a — Commit (ledger state)

---

## Downstream changes

1. **Repair ledger** gains `collision_status` per pair per side: `healed` / `skipped_collision` (with pre-existing count) / `not_targeted`. This is now part of the phase's permanent record.
2. **T7 flag flips:** a `flag_window_calendar_bug` offset is cleared if that session is now covered **whether by heal or by pre-existing rows** — a skipped-collision session is covered, just not by this phase. The flag tracks coverage, not authorship. `repaired_1c` is set only where this phase actually wrote rows.
3. **T7 arithmetic:** the restored-event count must reconcile against `healed` ledger rows only; `skipped_collision` sessions that were already covered don't change `in_scope` (they were never the blocker for their event unless another offset was).
4. **T8 volume reconciliation:** SDOT 2025-10-13 has no healed trades-vs-scan entry if its trades were already... (they weren't — trades were 0, so SDOT trades DO heal and DO get a reconciliation entry). SHMD likewise. No special-casing needed; the guard only touched quote sides.
5. **CLAUDE.md** (T9), add to the repair-provenance bullet:
   > - Heal writes fill genuine absence only. A pre-insertion collision guard skips any (ticker, session, side) that already has rows — heal never merges, dedupes, or supplements existing collection output. Sessions covered by pre-existing rows are flagged covered but not `repaired_1c`.

---

## Escalation Criteria (amendment scope)

| Condition | Threshold | Action |
|---|---|---|
| SDOT post-removal count ≠ 1,603, or any other SDOT session altered (T6-R2a) | any | Hard stop — post full SDOT session-by-session counts |
| Collision guard trips on a **trades** target (not just quotes) | any | Hard stop — implies trades also partially collected somewhere, contradicting the T6 scan; post it |
| Collisions beyond SDOT + SHMD | any | Not a stop — guard handles it; record under `surprises` |
| All other Phase 1c criteria | unchanged | unchanged |

---

## Approval Gate

Unchanged.
