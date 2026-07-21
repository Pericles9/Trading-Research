# Phase 2b — Pre-2025 `event_day_only` Characterization + Dev Sample Verification

**Date:** 2026-07-21
**Baseline:** `phase-2-approved` — canonical spine 20,951 in-scope, `coverage_class` + `quotes_full_window` live; 287 pre-2025 `event_day_only` events, 386 pre-2025 `quotes_full_window=FALSE` events (source: `results/phase_2/artifacts/coverage_class_summary.json`)
**Objective:** Mechanically classify why 287 pre-2025 events lack full T-3..T+3 trades coverage, and verify the pinned dev sample is uncontaminated by them.
**Primary success metric:** Every one of the 287 events carries exactly one classification label, with an unclassified remainder ≤ 30%; dev sample membership check completed with an explicit pass/fail count.

**Why this phase exists (context, not a task):** Missing post-event sessions in this universe plausibly encode delistings and halt-deaths — an outcome, not a bug. `coverage_class` currently cannot distinguish "died after the event" from "collection failure." Until the 287 are classified, any future T+1 analysis that filters on `full_window` has an unquantified survivorship exposure. This phase produces the classification counts; what they mean for the T+1 family is Cooper's read.

---

**Context:**
- Read-only phase. `read_only=True` on every DuckDB connection. No writes to the data root, the DB, or the canonical view. The only repo writes are this phase's own outputs plus the single docs line in T6.
- Primary surfaces: `momentum_events_canonical` (with `coverage_class`, `quotes_full_window`, `repaired_1c`, `flag_window_calendar_bug`), `filtered_trades`, `filtered_quotes`. Nothing else. `trade_data/` quarantine remains in force.
- Every aggregate over `filtered_trades` / `filtered_quotes` goes through an inner join to `momentum_events_canonical` with `in_scope = TRUE`. No exceptions, including ticker-level lookups (T3).
- Session logic: XNYS calendar, same derivation as Phase 2 T4 (`research/phase_2/t4_window_coverage.py`). Session date from `sip_timestamp` via `CAST(TO_TIMESTAMP(sip_timestamp/1e9) AS DATE)`.
- The 287-event cohort must be **derived from `coverage_class` in the live view**, then reconciled against `results/phase_2/artifacts/coverage_class.parquet`. It is not re-derived from raw coverage logic in this phase.
- Population is small (287). No dev-tier split; run against the full cohort directly. The dev-sample check (T2) touches 50 events. Nothing in this phase approaches the scale that requires two-tier execution.
- **Explicit scope limit:** this archive is event-conditional. Absence of a ticker's data after an event is *not* proof of delisting — it may simply mean no later event for that ticker. T3 produces within-archive signatures only. External delisting confirmation (reference data, symbol properties) is out of scope for this phase and is not to be attempted from Inferred/Unknown-provenance sources.

---

## Tasks

- [ ] **T0 — Branch and commit prompt**
  Cut `phase/3` from main. Commit `prompts/phase_3.md` and `config/phase_3.json` before any other work. Config holds: expected cohort sizes (287, 386), spine guard value (20,951), the unclassified-remainder threshold (0.30), and the dev-sample manifest path.

- [ ] **T1 — Spine guard + cohort reconciliation**
  Verify `in_scope = TRUE` count = 20,951. Derive the cohort: pre-2025 (file1) AND `coverage_class = 'event_day_only'`. Expected n = 287 exactly. Derive the quotes cohort: pre-2025 AND `quotes_full_window = FALSE`. Expected n = 386 exactly. Reconcile both against `coverage_class.parquet`. Write `results/phase_3/artifacts/t1_cohort.json` with counts and the reconciliation result.
  - [ ] T1a — Commit

- [ ] **T2 — Dev sample membership check**
  Load the pinned dev sample v2 event list from its committed Phase 0 manifest (path in `config/phase_3.json`; if the manifest cannot be located unambiguously, escalate — do not reconstruct the sample from seed). Join against the canonical view. Report, per dev event: `coverage_class`, `quotes_full_window`, `repaired_1c`. Write `results/phase_3/artifacts/dev_sample_coverage.json` with the full 50-row listing plus summary counts.
  - [ ] T2a — Escalation check: any dev event with `coverage_class != 'full_window'` → hard stop
  - [ ] T2b — Commit

- [ ] **T3 — Classify the 287**
  For each cohort event, compute the 7-offset presence bitmap (T-3..T+3, `filtered_trades`), then assign exactly one label by this precedence order. First matching rule wins; the rules and thresholds below are fixed — do not adjust them in response to results.

  1. `calendar_residue` — `flag_window_calendar_bug = TRUE` or `repaired_1c = TRUE`
  2. `archive_edge` — any of the event's 7 XNYS window sessions falls outside the observed session-date range of `filtered_trades` for the file1 population (compute that observed min/max once, spine-joined, and record it in the artifact)
  3. `forward_missing` — every missing offset is ≥ T+1 (pre-event flanks fully present)
  4. `backward_missing` — every missing offset is ≤ T-1 (post-event flanks fully present)
  5. `both_sides` — missing offsets on both sides of T=0
  6. `unclassified` — anything not matched above (should be structurally impossible given rules 3-5 exhaust the patterns; if nonzero, that is itself the finding — report it, do not patch the rules)

  - [ ] T3a — Within `forward_missing` only: for each event, check whether the event day is the latest session date for that ticker across **all of that ticker's own in-scope event windows** (spine-joined). Report the count for which it is. Label this in the report as a *weak within-archive delisting signature*, verbatim, with the scope-limit caveat from Context.
  - [ ] T3b — Cross-tab: classification × presence-bitmap pattern, and classification × event year. Write `results/phase_3/artifacts/classification.parquet` (one row per event: ticker, event_day, bitmap, label, signature flag) and `classification_summary.json`.
  - [ ] T3c — Overlap: of the 287 (trades cohort) and 386 (quotes cohort), report n in both, trades-only, quotes-only. Write into `classification_summary.json`.
  - [ ] T3d — Commit

- [ ] **T4 — Charts per the Chart Contract below**
  - [ ] T4a — `01_missing_pattern_by_class.html`
  - [ ] T4b — `02_cohort_temporal_distribution.html`
  - [ ] T4c — `03_trades_quotes_cohort_overlap.html`
  - [ ] T4d — Commit

- [ ] **T5 — Digest and report**
  Write `digest.json` per §11 and `REPORT.md`. Every claim cites its chart. Classification counts carried with n. No statements about survivorship bias magnitude, delisting rates, or what any of this implies for T+1 work — counts and descriptions only.
  - [ ] T5a — Commit

- [ ] **T6 — Docs line (verbatim, no composition)**
  Append exactly this line to `docs/Open-Items-Register.md`, unmodified:
  "2025 T=0 data quality: 91.5% of 2025 in-scope events are fully the 3-column migrated schema (price/sip_timestamp/size only) — no exchange, participant_timestamp, or correction fields even on the event day. Any future 2025 analysis is structurally incapable of venue, condition-code, or SIP-vs-participant timing work until recollected. Source: Phase 2 REPORT §2 migration-signature facet."
  - [ ] T6a — Commit; confirm working tree clean

---

## Escalation Criteria

Stop and post results. Do not proceed to the next task.

| Condition | Threshold | Action |
|---|---|---|
| `in_scope` guard ≠ 20,951 | any deviation | Hard stop — commit, post observed count, await instruction |
| T1 cohort count ≠ 287 or quotes cohort ≠ 386 | any deviation | Hard stop — commit, post both counts and the reconciliation diff vs. `coverage_class.parquet`, await instruction |
| Dev sample manifest missing or ambiguous | any | Hard stop — commit, post candidate paths found, await instruction. Do not reconstruct from seed. |
| Any dev event `coverage_class != 'full_window'` | ≥ 1 event | Hard stop — commit, post the affected event rows, await instruction |
| `unclassified` label count | > 30% of 287 (> 86 events) | Hard stop — commit, post bitmap patterns of unclassified events, await instruction |
| Any task requires a write to the data root, DB, or canonical view | any | Hard stop — this phase is read-only |

---

## Output Files

| File | Description | Status |
|---|---|---|
| `results/phase_3/artifacts/t1_cohort.json` | Guard values, cohort counts, reconciliation result | [ ] |
| `results/phase_3/artifacts/dev_sample_coverage.json` | 50-row dev sample coverage listing + summary | [ ] |
| `results/phase_3/artifacts/classification.parquet` | Per-event: bitmap, label, signature flag | [ ] |
| `results/phase_3/artifacts/classification_summary.json` | Label counts, cross-tabs, cohort overlap | [ ] |
| `results/phase_3/charts/01_missing_pattern_by_class.html` | Chart 01 | [ ] |
| `results/phase_3/charts/02_cohort_temporal_distribution.html` | Chart 02 | [ ] |
| `results/phase_3/charts/03_trades_quotes_cohort_overlap.html` | Chart 03 | [ ] |
| `config/phase_3.json` | Thresholds, expected counts, manifest path | [ ] |

---

## Chart Contract

| # | File | Question | Encoding | n shown | Looks like this if wrong |
|---|---|---|---|---|---|
| 01 | `charts/01_missing_pattern_by_class.html` | Do the 287 concentrate in a few structural missing-offset patterns? | x = presence bitmap pattern (sorted by count), y = n events, bar; color = classification label; strip of individual events beneath | n per bar, total in title | No dominant patterns — counts spread thinly across many arbitrary bitmaps, suggesting diffuse collection loss rather than structural causes |
| 02 | `charts/02_cohort_temporal_distribution.html` | Are the 287 clustered in time (archive edges, specific periods) relative to the full file1 population? | x = event date (monthly bins), y = share of that month's file1 events that are `event_day_only`, bar; secondary panel: raw monthly counts for both populations | Per-month cohort n on bars; both population totals in title | Flat proportional rate across all months — no edge clustering, no period concentration |
| 03 | `charts/03_trades_quotes_cohort_overlap.html` | Do the trades-coverage and quotes-coverage gaps hit the same events? | Grouped bar: both / trades-only / quotes-only, with per-group classification-label breakdown as stacked color | n per bar segment | Near-zero overlap — the two gaps have independent causes and must be tracked separately |

Standard chart rules per Agent_Prompt_Standard.md §9 apply. Chart 01's strip overlay is feasible at n=287; do not sub-sample.

---

## Reporting

On completion, post:
1. Guard + cohort reconciliation table (T1), with n
2. Dev sample check: summary counts + explicit pass/fail statement, and the full 50-row table
3. Classification table: label, n, % of 287, dominant bitmap pattern per label
4. `forward_missing` signature count (T3a), with the verbatim weak-signature caveat
5. Cohort overlap table (T3c)
6. Escalation check table — every criterion, observed value, pass/fail
7. Verification block per §10 — every headline number with source path, repro command, filter waterfall for the cohort derivation
8. Output file table with status filled in; commit list

Every claim cites its chart. Descriptions of what is visible are allowed. No recommendations, no survivorship-bias conclusions, no statements about what the labels imply for T+1 strategy work.

---

## Approval Gate

Do not begin any follow-on work — including any change to `coverage_class` semantics, any dev-sample action, or any recollection scoping — until Cooper has reviewed results and given explicit approval.
