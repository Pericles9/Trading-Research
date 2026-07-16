# Phase 1 — Filter Forensics

**Date:** 2026-07-16
**Baseline:** Phase 0c (tag `phase-0c-approved`) — 23,268 `momentum_events` rows; 17,203 eligible; 5,911 NULL-date rows exactly equal to 5,911 `folder_absent`; 7,252 orphan folders; 154 `missing_quotes`; 409 folders recovered by 0c's parser fix (194 dot-ticker + 215 lowercase-suffix).
**Objective:** Produce a line-cited, plain-language spec of how the event universe was defined — inputs, regressor, `momentum_pct` formula, q=0.05 boundary, keep rule — and classify the origin of the 5,911 NULL dates and the 7,252 orphan folders. One DB coverage spot-check rides along, triggered by the 0c parser fix.
**Primary success metric:** `filter_spec.md` complete with every mechanic cited to file:line, and NULL-date origin classified as (a) already NULL in scan inputs, (b) introduced by the filter script, or (c) undeterminable — with evidence either way. A (c) with evidence is an acceptable outcome; a (a)/(b) without evidence is not.

---

**Context:**

- Read targets: `data/collection_scripts/filter_events_power_law.py`; its scan-input parquets (exact paths discovered in T1 — Schema.md indicates they live alongside the output in `data/momentum_events/`); the `momentum_events` table; Phase 0c artifacts (`folder_inventory.parquet`, `join_reconciliation_detail.json`, `none_date_lookup.json`).
- **Never execute `filter_events_power_law.py`.** It writes into `data/momentum_events/` and can overwrite the spine of the entire archive. All re-derivation is a read-only re-implementation in `research/phase_1/`, writing only to `results/phase_1/artifacts/`.
- `data/` is read-only as always. No fixes, no re-ingestion, no parameter changes anywhere. This phase reads, re-derives, and reports.
- Scale: everything is event-level/metadata except T5, which runs bounded queries against full `filtered_trades` / `filtered_quotes` (4.9B / 3.8B rows). Commit before T5. Project only the columns needed. Expect minutes, not seconds; over ~10 minutes per query is fine but commit first per §12.
- All analysis code in `research/phase_1/`, config-driven from `config/phase_1.json`, seed 42 for any sampling.

---

## Tasks

- [ ] **T0 — Branch, prompt, docs housekeeping**
  Cut `phase/1` from tag `phase-0c-approved`. Commit `prompts/phase_1.md` and `config/phase_1.json` before any other work.
  Cooper has placed the canonical docs at `docs/Agent_Prompt_Standard.md` (header must read v1.3) and `docs/Mom-DB-Strategy-Research-Program.md`. Verify both exist at those exact paths, commit both, and update `CLAUDE.md`'s Pointers section to reference them (remove the Phase 0b gap language). Leave `docs/Agent_Prompt_Standard (1).md` (the v1.2 copy) untracked; list it as a deletion candidate in the report.
  - [ ] T0a — Commit

- [ ] **T1 — Script forensics → `results/phase_1/filter_spec.md`**
  Read `filter_events_power_law.py` end to end. Every item below cited to file:line.
  - [ ] T1a — Inputs: every file/glob the script reads; which exist on disk today; row counts and column lists for each that loads → `artifacts/scan_input_inventory.json`
  - [ ] T1b — The fit: dependent variable, regressor(s), functional form, log-space handling, the q=0.05 quantile mechanics, any pre-filters (price, volume, listing screens), library used
  - [ ] T1c — The exact `momentum_pct` formula, traced to input columns (gap-at-open vs open-to-high vs close-to-close vs other)
  - [ ] T1d — The keep rule and any secondary filters; every output column written, including exactly how `date` is populated and whether any code path can emit a NULL/None date
  - [ ] T1e — Hardcoded parameter table: every literal in the script that changes the output
  - [ ] T1f — Commit

- [ ] **T2 — Refit and compare (read-only re-implementation)**
  Regardless of input availability: verify `momentum_events` column names/types match the script's write logic.
  If all scan inputs from T1a exist and load: re-implement the fit in `research/phase_1/refit_boundary.py`, derive the kept set, compare against `momentum_events` on (ticker, date, momentum_pct rounded 2dp) — row counts and set overlap in both directions → `artifacts/refit_comparison.json`.
  **Documented fallback (not an escalation):** if any input is missing or unreadable, record which in `scan_input_inventory.json`, skip the refit, run chart 02 in fallback mode.
  - [ ] T2a — Commit

- [ ] **T3 — NULL-date forensics**
  For the 5,911 NULL-date rows: trace the `date` field through the pipeline. NULL in the scan inputs for those rows, or introduced by the script (join miss, parse failure, missing key)? Classify origin (a)/(b)/(c) with evidence → `artifacts/null_date_forensics.json`. Compare NULL vs dated rows on `momentum_pct` and every other populated column (chart 01). Cross-reference the 114 literal-"None" folders (0c's `none_date_lookup.json`) against the NULL-date rows: subset, disjoint, or partial overlap, with counts.
  - [ ] T3a — Commit

- [ ] **T4 — Orphan drift test**
  For the 7,252 orphan folders (0c inventory): using ticker/date/momentum parsed from folder names, test membership against (i) the scan-input rows, (ii) the T2 re-derived kept set if built, and (iii) any other `filtered_events_*.parquet` files present in `data/momentum_events/` — list that folder's complete contents first. Report the fraction of orphans falling below vs above the current q05 boundary (or below the minimum kept `momentum_pct` in fallback mode) → `artifacts/orphan_classification.parquet` + `orphan_summary.json`. Chart 03.
  - [ ] T4a — Commit

- [ ] **T5 — DB coverage spot-check (full tier — commit first)**
  - [ ] T5a — For the 409 parser-fix-recovered folders: one aggregated presence query per table against `filtered_trades` and `filtered_quotes` (ticker-level membership; event-window date check as a secondary column). Report how many of the 409 have any rows in each table → `artifacts/ingestion_spotcheck.json`. **Post only. Do not ingest, repair, or modify anything.**
  - [ ] T5b — For the 50 dev-sample events (`config/dev_sample_events.csv`): per-event row counts in `filtered_trades_dev` and `filtered_quotes_dev`, all 50 rows in the report. Any zero → escalation row 5.
  - [ ] T5c — Commit

- [ ] **T6 — Charts per the Chart Contract**
  - [ ] T6a — `01_momentum_pct_by_date_status.html`
  - [ ] T6b — `02_q05_boundary.html`
  - [ ] T6c — `03_orphans_vs_boundary.html`
  - [ ] T6d — Commit

- [ ] **T7 — Digest, report, map**
  Write `digest.json` (§11 of the standard; must pass `research/phase_0b/validate_digest.py`) and `REPORT.md` (every claim cites its chart or artifact). Update `docs/Research-Library-Map.md` with this phase's files. Confirm `git status` clean.
  - [ ] T7a — Commit

---

## Escalation Criteria

Stop and post results. Do not proceed to the next task. Table order is priority order.

| Condition | Threshold | Action |
|---|---|---|
| T0: canonical docs absent, or standard header not v1.3 | either file | Hard stop — commit, post exactly what exists at both paths, await instruction |
| T1: `data/collection_scripts/filter_events_power_law.py` missing or unreadable | — | Hard stop — commit, post directory listing of `collection_scripts/`, await instruction |
| T2: `momentum_events` schema vs script write logic | any missing / extra / mistyped column | Hard stop — commit, post column diff, await instruction |
| T2: refit kept-set overlap (only when all inputs present) | < 95% in either direction | Hard stop — commit, post overlap stats + chart 02, await instruction |
| T5b: any dev-sample event with zero rows in either dev table | > 0 events | Hard stop — commit, post the full 50-row count table, await instruction |

**Documented findings, not hard stops** — post in the report and in digest `surprises`, then continue: scan inputs missing (T2 fallback engages); NULL-date origin classified (c); any of the 409 folders absent from `filtered_trades`/`filtered_quotes` (T5a).

---

## Output Files

| File | Description | Status |
|---|---|---|
| `config/phase_1.json` | overlap threshold (0.95), chart subsample cap (50,000), seed (42), input paths | [ ] |
| `results/phase_1/filter_spec.md` | the line-cited filter spec (T1) | [ ] |
| `results/phase_1/artifacts/scan_input_inventory.json` | script inputs, existence, row counts, columns | [ ] |
| `results/phase_1/artifacts/refit_comparison.json` | conditional — only if all inputs present | [ ] |
| `results/phase_1/artifacts/null_date_forensics.json` | origin classification + evidence | [ ] |
| `results/phase_1/artifacts/orphan_classification.parquet` | per-orphan membership flags | [ ] |
| `results/phase_1/artifacts/orphan_summary.json` | orphan fractions by class | [ ] |
| `results/phase_1/artifacts/ingestion_spotcheck.json` | 409-folder presence + 50 dev-event row counts | [ ] |
| `results/phase_1/charts/01_momentum_pct_by_date_status.html` | per contract | [ ] |
| `results/phase_1/charts/02_q05_boundary.html` | per contract | [ ] |
| `results/phase_1/charts/03_orphans_vs_boundary.html` | per contract | [ ] |

`digest.json` and `REPORT.md` implicit.

---

## Chart Contract

| # | File | Question | Encoding | n shown | Looks like this if wrong |
|---|---|---|---|---|---|
| 01 | `charts/01_momentum_pct_by_date_status.html` | Are the 5,911 NULL-date events a random draw from the same `momentum_pct` distribution as the 17,357 dated events? | x = momentum_pct (log), ECDF overlay (NULL vs dated) with strip overlay beneath | per-group n in legend | The curves separate materially — the missing 25% of the spine is biased, and every downstream statistic inherits that bias |
| 02 | `charts/02_q05_boundary.html` | Does the fitted q05 boundary cleanly separate kept from dropped in the scan inputs? | x = regressor from T1b (log), y = momentum measure (log); scatter of scan-input rows (seeded subsample ≤ 50k, stated in caption), fitted boundary line, kept set colored | total, subsample, and kept counts in caption | Kept points scattered on both sides of the line — filter drift, or the keep rule is not what the spec says. **Fallback mode** (inputs missing): histogram of `momentum_pct` from `momentum_events`; wrong = no clean truncation edge where the filter should have cut |
| 03 | `charts/03_orphans_vs_boundary.html` | Do the 7,252 orphan folders look like the residue of an earlier, looser filter run? | x = momentum parsed from folder name (log), ECDF: orphans vs matched folders, with the boundary / minimum-kept reference line | per-group n in legend | Orphans occupy the same range as matched folders with no low-side tail — drift does not explain them and their origin remains unknown |

Standing chart rules per §9 of the standard apply (Plotly standalone HTML, one chart per file, no smoothing, outliers shown, caption states sample + filters + config hash).

---

## Reporting

On completion, post:

1. Hardcoded parameter table (T1e), each row line-cited
2. The `momentum_pct` formula, one line, cited
3. NULL-date origin classification (a)/(b)/(c) + the evidence behind it
4. Refit comparison numbers, or the fallback note stating which inputs were missing
5. Orphan membership fractions by class
6. T5 tables: 409-folder presence counts per table; all 50 dev-event row counts
7. Escalation check table (every criterion, observed value, pass/fail)
8. Verification block per §10 — every headline number with source path, filter waterfall, one-line repro, config hash
9. Output file table with status filled in
10. Commit list

Every claim cites its chart or artifact. No recommendations. On escalation: criterion + observed value, results up to the failure point, no recommendations.

---

## Approval Gate

Do not begin Phase 2 or any follow-on work until Cooper has reviewed results and given explicit approval.
