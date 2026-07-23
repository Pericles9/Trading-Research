# Phase 5 — Amendment 4

**Branch:** `phase/5` (continue on the existing branch; do not cut a new one)
**Baseline for this amendment:** the committed T4 hard stop (`78e64f4`)
**Triggered by:** T4 escalation row 4 — file2 (2025) flagged share observed at 100.00% trades
(5,188/5,188) and 99.98% quotes (5,187/5,188), vastly exceeding the original >5%/>260 threshold.

**Cooper's decision (2026-07-22):** The observed file2 flagged shares are **accepted as
structural**, consistent with two facts already on record before this phase ran:
Phase 2 T8's `coverage_class.parquet` (which showed the same ~100%/99.98% file2
not-full-window split via the identical derivation), and the recorded file2
schema-migration issue (91.5% of file2 events carry only the degraded 3-column
schema — `docs/Open-Items-Register.md`, "2025 T=0 data quality"). This is **not a
data defect** and **no re-derivation is required** — T2/T3/T4's numbers stand as
computed.

**What this amendment authorizes:**
1. Escalation row 4's bound is **retroactively rescoped to file1 only**. File2 is
   removed from row 4's denominator/population entirely — its ~100% flagged share
   is now the expected, described outcome, not a threshold violation.
2. Under the file1-only scope, the original row-4 check now reads: trades flagged
   287/15,763 = **1.82%**, quotes flagged 386/15,763 = **2.45%** — both pass a
   >5%/>260 threshold easily (this is unchanged data; only the population the
   check is evaluated over has changed).
3. File2 flagged events retain their `not_classified` label on both sides (T4's
   existing behavior — unchanged). Per-event `trades_bitmap`/`quotes_bitmap`
   strings continue to carry the missing-offset shape for every file2 event,
   labeled or not.
4. Chart 03 (`03_flag_label_composition.html`) is **expected** to show
   `not_classified` dominance, driven by file2. This is not the chart's failure
   appearance under this amendment — the agent describes what the chart shows and
   adds a caption note pointing to this amendment, rather than treating
   `not_classified` dominance as evidence the carried classifications explain
   little (the chart contract's original failure-appearance language assumed a
   small file2 population; it no longer applies as written).

**What it does NOT authorize:** any change to `in_scope`, any deletion, any
change to `coverage_class` semantics, any change to the flag-and-carry
disposition itself (still flag every non-clean-window event, both files, no
exclusions), or any exemption for file1 (file1's flagged population is still
bound by the original 287/386/414/259-28-127 exact-match checks in T4a — those
are unaffected and remain in force).

**Supersedes in `prompts/phase_5.md`:** escalation row 4's population/threshold
only. Original **T5, T6, T7** stand as written, with T6's chart 03
caption/description updated per point 4 above. T0–T4 stand as already executed
and committed (`1491e47`..`78e64f4`) — not re-run.

---

## Revised escalation row 4

| Condition | Threshold | Population | Action |
|---|---|---|---|
| file1 flagged share (either side) | > 5% of file1 in-scope events (> 788) | `source_file='file1'` only | Hard stop — post counts, await instruction |

Superseded row (for the record): the original threshold read ">5% of file2 in-scope events (>260)" over the full file2 population — retired by this amendment, not deleted from history (see `prompts/phase_5.md`, `results/phase_5/artifacts/reconciliation_summary.json`).

Observed under the revised check: trades 1.82% (287/15,763), quotes 2.45% (386/15,763) — both pass.

---

## Tasks

- [ ] **A4-T0 — Commit this amendment**
  Commit `prompts/phase_5_amendment_4.md` before resuming.

- [ ] **Resume T5 — Rebuild `momentum_events_canonical`** (as written in `prompts/phase_5.md`)
- [ ] **Resume T6 — Charts per the Chart Contract**, chart 03 caption updated per point 4 above
- [ ] **Resume T7 — Register, digest, report**, digest/REPORT note this amendment and the file1-rescoped row 4 result explicitly

---

## Approval Gate

Unchanged from `prompts/phase_5.md`. Do not begin any follow-on work until Cooper has reviewed T5-T7 results and given explicit approval. On approval, tag `phase-5-approved`.
