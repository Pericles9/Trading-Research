# Phase 1c — Amendment 1: T3 Escalation Resolution (Optional-Field Handling)

**Date:** 2026-07-19
**Resolves:** T3 hard stop (vendor response missing archive column `correction`; new vendor field `decimal_size`), commit d598c30.
**Decision (Cooper):** The original criterion tested schema-equivalence against a union schema the archive's own files never individually satisfied. It is replaced with **content-equivalence**: optional sparse fields may be absent from a vendor response only where the archive's corresponding rows are also empty in that field. The trust gate is simultaneously sharpened — conditional emission is tested directly, not assumed.

Commit this file to `prompts/`, then execute T3-R below. The formal 20-pair control run restarts from scratch under the amended rules; the METC pre-flight fetch remains as staged evidence only.

---

## Tasks (replace the original T3 selection and gate; T3's diff mechanics otherwise stand)

- [ ] **T3-R1 — Derive the optional-field class from archive evidence**
  A column qualifies as **optional** iff both: (a) non-null rate in the full table below 1% (config), and (b) demonstrably absent from the per-file schema of at least some archive parquet files (footer inspection on a sample of ≥ 200 files per table, seed from config) — proving conditional presence was original collection behavior, not a vendor change. Expected members: `correction`, possibly `trf_id`/`trf_timestamp` if (b) holds for them (note: they returned as null-valued keys in the METC response, so they may be always-emitted — the archive evidence decides, not the single response).
  Post the derived list per table with each field's non-null rate and file-absence rate, both with n. Write the list to `config/phase_1c.json` as `optional_fields`. All other columns are **required**.
  - [ ] T3-R1a — Commit

- [ ] **T3-R2 — Amended escalation criterion (replaces "archive schema column absent → hard stop")**

  | Condition | Action |
  |---|---|
  | **Required** column absent from a vendor response | Hard stop |
  | **Optional** column absent, and the archive rows for that (ticker, session) contain **zero** non-null values in it | Allowed — NULL-fill on alignment; record per pair |
  | **Optional** column absent, but the archive rows for that (ticker, session) contain non-null values in it | Hard stop — genuine content regression |
  | Optional column present: non-null count or values mismatch archive on matched rows | Counts toward the existing T3b field-mismatch threshold |
  | New vendor field not in archive schema (e.g., `decimal_size`) | Dropped on alignment, preserved in raw staging, enumerated once in the report — not a stop |

- [ ] **T3-R3 — Amended control-pair selection**
  20 pairs total, re-drawn (new seed recorded in config): 15 per the original stratification (years × trade-count terciles), plus **5 targeted pairs drawn from sessions where the archive contains non-null `correction` rows** (and, if T3-R1 admits other optional fields with non-null clusters, at least 1 targeted pair each, within the 5). The targeted pairs directly test conditional emission: the vendor response must contain the optional column with matching non-null counts and values for those sessions.
  - [ ] T3-R3a — Post the 20-pair list with, per pair, the archive's non-null count for each optional field
  - [ ] T3-R3b — Commit

- [ ] **T3-R4 — Run the formal control diff under the amended rules**
  Original T3 diff mechanics plus one added column per optional field: archive non-null count vs fetched non-null count per pair. Chart 01 gains a panel: optional-field non-null count agreement across the 20 pairs (n per pair).
  Gate thresholds otherwise unchanged (row delta > 1%, matched-row field mismatch > 0.1%, row-defining code-set differences → hard stop).
  - [ ] T3-R4a — Commit; on pass, resume the original prompt at T4

---

## Downstream changes

1. **T2 alignment logic:** NULL-fill optional fields when absent; per-pair record of which fields were filled goes into the repair ledger (new column `optional_fields_null_filled`).
2. **T6 verification:** unchanged — post-ingest row counts are content checks and already schema-agnostic.
3. **Report:** the optional-field derivation table (T3-R1) and the targeted-pair results are standing sections; the `decimal_size` enumeration lands in the dropped-vendor-fields section already required.

---

## Escalation Criteria (amendment scope)

| Condition | Threshold | Action |
|---|---|---|
| Any targeted pair where the vendor omits an optional field the archive populates for that session | any | Hard stop — conditional-emission hypothesis falsified |
| Optional-field derivation returns > 4 fields per table | — | Not a stop — post the list under `surprises` (more per-file variability than believed warrants eyes, not a halt) |
| All other Phase 1c criteria | unchanged | unchanged |

---

## Approval Gate

Unchanged.
