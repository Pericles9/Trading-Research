# Phase 6c — Defect #4 Confirmation: Cohort-Stratified Verdict & Residual Diagnosis

**Date:** 2026-07-23
**Baseline:** tip of `phase/6b` (at the A6.1 full stop). Branch `phase/6c` from it. `master` remains at `phase-5a-approved`.
**Objective:** Resolve the A6.1 criterion-1 failure the disciplined way: determine whether the vendor-basis mechanism (defect #4) is confirmed on the population the criterion should have been computed over, and individually classify every residual outlier. **Diagnosis only — no fix code, no changes to 6b's pipeline, no full-table passes.** Phase 6b remains stopped until this phase's gate.
**Primary success metric:** A verdict artifact Cooper can approve or reject in one reading: stratified criteria table + a classification for each of the 7 residuals with its evidence attached.

---

**Context:**

- **Why stratification is legitimate, not tuning:** dev v4 comprises a 50-event **primary cohort** (drawn from the clean-window frame to represent the population) and a 6-event **flagged sidecar** (SLXN, APLD, ACET, RBC, NUKK, PSIX — drawn *because* their archives are degraded, to exercise broken-data code paths; 5a report §4). Population-level statistical criteria are only meaningful over the primary cohort; A5.1/A6.1 pooled both. This was a criterion-design error at the chat layer, recorded as such. The stratified recomputation uses the **already-committed** `a61_basis_confirmation_rerun.json` — same numbers, correct denominator, no re-measurement.
- **The 7 residuals:** SCLX, VEEE, NEPH, ZENA (primary) · ACET, NUKK, PSIX (sidecar). Working hypotheses to test per event, from the A6.1 artifact's own pattern: the sidecar pair with internal r1′/r2′ disagreement (ACET 0.996/1.158, NUKK 5.98/7.98) both disagree in the direction *our tick high < vendor high* — consistent with tape coverage gaps at the peak, not a basis effect; the 5 band-margin cases (r1′≈r2′, both a few points outside 2%) look like the passing population with wider noise.
- **Standing constraints:** `CLAUDE.md` applies. Read-only with respect to 6b's code and artifacts; this phase writes only under `results/phase_6c/`, `research/phase_6c/`, `prompts/`, `config/`.

---

## Tasks

- [ ] **T0 — Branch, prompt/config commit**
  `phase/6c` from `phase/6b` tip. Commit `prompts/phase_6c.md`, `config/phase_6c.json` (band width 2%, stratified threshold 90%, classification rules below — all tunables in config).
  - [ ] T0a — Commit

- [ ] **T1 — Stratified recomputation** (from `a61_basis_confirmation_rerun.json` only)
  Recompute all three A6.1 criteria separately for: primary cohort, sidecar, pooled. Identify which event had an undefined ratio and which cohort it belongs to. Output the full table to `results/phase_6c/artifacts/t1_stratified_criteria.json`. **No threshold changes, no band changes** — same 2%, same 90%, applied per stratum.
  - [ ] T1a — Commit

- [ ] **T2 — Per-residual classification** (all 7; dev bars + A6.1's bar-series dumps; no new full-table queries)
  For each residual, assemble and record:
  - Cohort membership and (for sidecar) its drawn bitmap pattern from the 5a report
  - T-1 and T+0 coverage evidence: RTH bar count vs. the primary-cohort median, first/last print times, longest intra-RTH gap in minutes, ETH-vs-RTH row share (flag ZENA's known 59.4% ETH share)
  - The internal-disagreement direction and magnitude (r2′ vs r1′), and whether the vendor high exceeds our tick high
  - Distance outside the 2% band for the margin cases
  Classify each event into exactly one of: **`band_margin`** (r1′≈r2′ internally, ≤5 points outside the band, no coverage anomaly), **`coverage_gap`** (our tape demonstrably thin/missing where the vendor high implies prints — vendor high > our high with supporting gap evidence), **`unexplained`** (fits neither). Rules are fixed above — the agent applies them, it does not invent categories. Output: `t2_residual_classification.json` with the evidence block per event.
  - [ ] T2a — Commit

- [ ] **T3 — Verdict artifact + one chart**
  - `results/phase_6c/artifacts/verdict.json`: the stratified criteria table, the 7 classifications, and a single boolean the gate turns on: `mechanism_confirmed_on_primary` = (criterion 1 ≥ 90% on primary) AND (criteria 2, 3 pass on primary) AND (`unexplained` count = 0).
  - `charts/01_r_agreement_by_cohort.html` — per-event |r1′−r2′|/r2′ (log y), grouped primary vs. sidecar, 2% band drawn, residuals labeled by name and classification color. Question: is disagreement concentrated in the sidecar? Looks-like-this-if-wrong: primary and sidecar distributions indistinguishable (then cohort composition doesn't explain the failure and the mechanism needs the dedicated audit regardless of the boolean).
  - [ ] T3a — Kaleido-verify, commit

- [ ] **T4 — Digest and report**
  `digest.json`, `REPORT.md` per the Evidence Standard. Description only. The report states the boolean and the evidence; **whether defect #4 is confirmed, and whether 6b resumes, is Cooper's call at the gate.**
  - [ ] T4a — Commit; working tree clean

---

## Escalation Criteria

| # | Condition | Threshold |
|---|---|---|
| 1 | Any `unexplained` classification | > 0 — finish T2 for all 7, then stop before T3 and post the unexplained events' evidence blocks |
| 2 | Primary-cohort criterion 1 | < 90% — finish T1, stop, post the stratified table (the cohort story is then wrong and no verdict is drafted) |
| 3 | Any write outside this phase's four paths, or any new full-table pass | any |
| 4 | Any modification to 6b code/artifacts | any |

---

## Output Files

`config/phase_6c.json` · `results/phase_6c/artifacts/t1_stratified_criteria.json`, `t2_residual_classification.json`, `verdict.json` · `charts/01_r_agreement_by_cohort.html` · `digest.json`, `REPORT.md` — all committed.

---

## Reporting

Post: stratified criteria table · 7-row classification table with one-line evidence summaries · the boolean · chart 01 · escalation table · commit list.

---

## Approval Gate

On Cooper's approval: tag `phase-6c-approved`. Disposition options at the gate (Cooper selects; the agent does not pre-select): **(a)** mechanism confirmed → 6b resumes at A6.2 with a one-line Amendment 7 recording the verdict and adding the standing rule that *population-level statistical criteria in all future prompts are computed on representative cohorts only, with pathological/sidecar strata reported separately*; **(b)** not confirmed → scope the full-population basis audit as its own phase before 6b resumes. No 6b work of any kind before the tag exists.
