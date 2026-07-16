# Phase 0c — Event/Folder Join Reconciliation

**Date:** 2026-07-16
**Baseline:** Phase 0b — `momentum_events` loaded (23,268 rows), dev sample pinned (50 events from 17,203 eligible)
**Objective:** Explain the two unreconciled gaps in the Phase 0b eligibility waterfall: (a) 23,268 events → 17,203 with a joinable folder (6,065 dropped, ~26%), and (b) ~24,200 trades files on disk vs. 23,268 event rows (folders that map to no event). Classify *why* each direction fails. No fixes, no dev-sample changes, no data writes.
**Primary success metric:** Every one of the 6,065 non-joinable events assigned to exactly one failure class, and every on-disk folder assigned to exactly one match class, with counts that sum to their totals.

---

**Context:**
- This phase touches the filesystem (`data/filtered/`) and the `momentum_events` table only. It does not query `filtered_trades` / `filtered_quotes` / `raw_quotes`. No dev/full tier split needed — everything here is metadata-scale.
- The Phase 0b join key was `data/filtered/{ticker}_{date}_{momentum_pct:.2f}/` requiring both `trades.parquet` and `quotes.parquet` present. That exact logic is the thing under audit — reproduce it first, then decompose it.
- Directory listing only for T1–T2. Do not open any parquet file in this phase.
- Read-only with respect to all data. The only writes are to `results/phase_0c/`, `config/`, `prompts/`, `research/phase_0c/`.
- The dev sample (`config/dev_sample_events.csv`) is frozen. Nothing in this phase modifies it regardless of findings.
- Schema.md reference counts, for orientation only (do not treat as ground truth): 24,200 trades files ingested, 22,660 quotes files ingested.

---

## Tasks

- [ ] **T0 — Branch and commit prompt**
  Cut `phase/0c` from the `phase-0b-approved` tag. Commit `prompts/phase_0c.md` and `config/phase_0c.json` before any other work. Config holds: seed (42), per-class failure sample size (20), data root, and the folder-name format string under test.

- [ ] **T1 — Folder inventory**
  Single `os.scandir` pass over `data/filtered/`. For each entry record: folder name, parsed components (ticker, date, momentum string) if the name parses, and which of `trades.parquet` / `quotes.parquet` exist (existence only — no reads). Classify every folder into exactly one of: `both_files`, `trades_only`, `quotes_only`, `neither`, `unparseable_name`. Write `results/phase_0c/artifacts/folder_inventory.parquet` and a class-count summary JSON.
  - [ ] T1a — Commit

- [ ] **T2 — Bidirectional join**
  - [ ] T2a — **Events → folders.** Reproduce the Phase 0b eligibility logic exactly (same format string, same both-files requirement) and confirm it yields 17,203. If it does not, hard stop per the escalation table — the waterfall itself is unreproducible.
  - [ ] T2b — For each of the remaining 6,065 events, classify into exactly one of:
    1. `format_mismatch` — a folder for the same ticker+date exists, but under a momentum string that differs from `{momentum_pct:.2f}` (capture both strings)
    2. `folder_absent` — no folder for that ticker+date under any momentum string
    3. `missing_quotes` — folder matches, `trades.parquet` present, `quotes.parquet` absent
    4. `missing_trades` — folder matches, `quotes.parquet` present, `trades.parquet` absent
    5. `missing_both` — folder matches, both files absent
    6. `duplicate_collision` — more than one folder matches the ticker+date
    Classes are checked in this order; first match wins. Counts must sum to 6,065.
  - [ ] T2c — **Folders → events.** For every folder in T1's inventory, classify: `matched` (joins to exactly one event row), `orphan` (parses but no event row for its ticker+date), `ambiguous` (multiple event rows match), `unparseable`. Counts must sum to the T1 folder total.
  - [ ] T2d — Write `results/phase_0c/artifacts/join_reconciliation.json` with all class counts, both directions. Commit.

- [ ] **T3 — Failure sampling**
  For each nonzero T2b class, draw 20 examples (seed=42; all of them if the class has fewer than 20). For each example record: event row fields (ticker, date, momentum_pct at full precision), the expected folder name, what actually exists on disk for that ticker+date (`ls` of matching prefixes), and the classified reason. Write `results/phase_0c/artifacts/failure_samples.json`. This is the artifact Cooper reads to judge whether the classifications are right.
  - [ ] T3a — Commit

- [ ] **T4 — Distribution comparison, joinable vs. dropped**
  From `momentum_events`, compare the 17,203 joinable vs. 6,065 non-joinable events on: `momentum_pct` distribution, event date distribution, and repeat-ticker membership (whether the event's ticker appears in more than one event). Produce the three charts in the Chart Contract. No interpretation — the charts carry it.
  - [ ] T4a — Commit

- [ ] **T5 — Digest and report**
  Write `digest.json` (per §11 of `docs/Agent_Prompt_Standard.md`, validated by `research/phase_0b/validate_digest.py`) and `REPORT.md`. Every claim cites its chart or artifact. No recommendations.
  - [ ] T5a — Commit; confirm working tree clean

---

## Escalation Criteria

Stop and post results. Do not proceed to the next task.

| Condition | Threshold | Action |
|---|---|---|
| T2a reproduction of the 17,203 eligible count | ≠ 17,203 | Hard stop — commit, post both counts and the logic diff, await instruction |
| `format_mismatch` class count (T2b) | > 0 | Hard stop — commit, post count + all sampled examples with both momentum strings, await instruction. This class means the dev-sample eligibility set was defined by a formatting bug. |
| `duplicate_collision` class count (T2b) | > 0 | Hard stop — commit, post examples, await instruction |
| T2b class counts sum | ≠ 6,065 | Hard stop — classification is not a partition; commit and post the discrepancy |
| T2c class counts sum | ≠ T1 folder total | Hard stop — same reason, other direction |
| `unparseable_name` folder count (T1) | > 50 | Hard stop — commit, post 20 examples, await instruction |

`folder_absent`, `missing_quotes`, `missing_trades`, `missing_both`, and `orphan` at any count are **findings, not stops** — post the counts and continue. (`missing_quotes` is expected to be roughly the known ~1,540-file gap; `orphan` is expected to be nonzero given 24,200 trades files vs. 23,268 events.)

---

## Output Files

| File | Description | Status |
|---|---|---|
| `config/phase_0c.json` | Seed, sample sizes, data root, format string under test | [ ] |
| `results/phase_0c/artifacts/folder_inventory.parquet` | One row per folder: name, parse result, file presence, class | [ ] |
| `results/phase_0c/artifacts/folder_inventory_summary.json` | T1 class counts | [ ] |
| `results/phase_0c/artifacts/join_reconciliation.json` | T2 class counts, both directions, with totals check | [ ] |
| `results/phase_0c/artifacts/failure_samples.json` | 20 classified examples per nonzero failure class | [ ] |
| `results/phase_0c/charts/01_momentum_pct_joinable_vs_dropped.html` | Chart Contract #01 | [ ] |
| `results/phase_0c/charts/02_events_over_time_by_join_status.html` | Chart Contract #02 | [ ] |
| `results/phase_0c/charts/03_failure_class_counts.html` | Chart Contract #03 | [ ] |

---

## Chart Contract

| # | File | Question | Encoding | n shown | Looks like this if wrong |
|---|---|---|---|---|---|
| 01 | `charts/01_momentum_pct_joinable_vs_dropped.html` | Do dropped events differ from joinable ones on `momentum_pct`? | x=momentum_pct (log where positive), overlaid ECDFs, one line per join status; strip sub-sample beneath | n per group in legend | The two ECDFs separate — dropped events concentrate in a specific momentum range (this is the "dev sample is biased" picture) |
| 02 | `charts/02_events_over_time_by_join_status.html` | Are drops concentrated in time (a collection-run failure) or spread evenly? | x=event date (monthly bins), y=count, stacked or grouped bars by join status | n per bin in hover; totals in title | Drops cluster in specific months — pointing at particular collection runs rather than random attrition |
| 03 | `charts/03_failure_class_counts.html` | Which failure class explains the 6,065? | x=failure class, y=count, bar (categorical counts — the bar *is* the distribution here) | Count labeled on each bar; total in title | `format_mismatch` or `duplicate_collision` bars are nonzero (also escalation triggers) |

Note on the failure-appearance column for 01 and 02: "wrong" here means *the drop is not benign*. Overlapping ECDFs and evenly spread drops are the good outcome.

---

## Reporting

On completion, post:
1. T1 folder class counts, with total
2. T2 reconciliation table, both directions, each summing to its total
3. Failure-class table with per-class n and a pointer to `failure_samples.json`
4. Escalation check table — every criterion, observed value, pass/fail
5. Verification block (§10): every headline count with its script path and a one-line repro command
6. Output file table with status filled in
7. Commit list

Description of what the charts show is allowed. No interpretation of what the drop means for the dev sample or the program — that call is Cooper's.

---

## Approval Gate

Do not begin Phase 1 or any follow-on work until Cooper has reviewed results and given explicit approval.
