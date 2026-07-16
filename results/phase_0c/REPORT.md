# Phase 0c Report — Event/Folder Join Reconciliation

**Branch:** `phase/0c` (from tag `phase-0b-approved`) | **Status:** Complete, awaiting Cooper's review/approval.

## 1. T1 — folder class counts (post-fix)

| Class | Count |
|---|---|
| `both_files` | 23,003 |
| `trades_only` | 1,606 |
| `quotes_only` | 0 |
| `neither` | 114 (all 114 `date_is_none` folders — confirmed empty) |
| `unparseable_name` | 0 |
| *(excluded, not classified)* | 3 stray non-folder files |

Total classified: 24,723. Sum check: passes.

**Hard stop hit and resolved** (see §4): pre-fix `unparseable_name` was 526. Three separate, non-overlapping causes: 194 dot-containing tickers (warrants), 215 lowercase-suffix tickers (preferred shares), 114 literal-`"None"`-date folders, 3 stray files. Fixed per Cooper's three-part instruction; post-fix `unparseable_name` = 0.

## 2. T2 reconciliation table, both directions

**Events → folders** (T2a/T2b, 23,268 total):

| | Count |
|---|---|
| Eligible (joinable) | 17,203 |
| Non-eligible | 6,065 |

Non-eligible, by class:

| Class | Count |
|---|---|
| `folder_absent` | 5,911 |
| `missing_quotes` | 154 |
| `missing_trades` | 0 |
| `missing_both` | 0 |
| `format_mismatch` | 0 |
| `duplicate_collision` | 0 |

Sum: 6,065 ✓

**Folders → events** (T2c, 24,723 total):

| Class | Count |
|---|---|
| `matched` | 17,357 |
| `orphan` | 7,252 |
| `none_date_unresolved` | 114 |
| `unparseable` | 0 |

Sum: 24,723 ✓

Cross-check: 17,203 (eligible) + 154 (`missing_quotes`, folder matches but incomplete) = 17,357 (`matched`). The two directions agree exactly.

## 3. Failure-class table + samples

| Class | n | Sample size | Pointer |
|---|---|---|---|
| `folder_absent` | 5,911 | 20 | `results/phase_0c/artifacts/failure_samples.json` |
| `missing_quotes` | 154 | 20 | same file |

All other T2b classes are 0 — no examples to draw.

## 4. Escalation check table

| Criterion | Threshold | Observed | Pass/Fail |
|---|---|---|---|
| T1 `unparseable_name` | > 50 | 526 (pre-fix) → **triggered**; 0 (post-fix) | Triggered, then resolved per Cooper's instruction |
| T2a reproduction | ≠ 17,203 | 17,203 | PASS |
| `format_mismatch` (T2b) | > 0 | 0 | PASS |
| `duplicate_collision` (T2b) | > 0 | 0 | PASS |
| T2b sum | ≠ 6,065 | 6,065 | PASS |
| T2c sum | ≠ folder total | 24,723 = 24,723 | PASS |

## 5. Verification block

| Claim | Script | Repro |
|---|---|---|
| Folder inventory, post-fix | `research/phase_0c/build_folder_inventory.py` | `python -m research.phase_0c.build_folder_inventory` |
| None-date lookup | `research/phase_0c/none_date_lookup.py` | `python -m research.phase_0c.none_date_lookup` |
| T2a/T2b/T2c reconciliation | `research/phase_0c/build_join_reconciliation.py` | `python -m research.phase_0c.build_join_reconciliation` |
| Failure samples | `research/phase_0c/build_failure_samples.py` | `python -m research.phase_0c.build_failure_samples` |
| Charts 01–03 | `research/phase_0c/chart_0{1,2,3}_*.py` | `python -m research.phase_0c.chart_01_momentum_pct` (etc.) |

## 6. Two findings beyond this phase's scope, flagged not investigated

- **`momentum_events.date` is NULL for 5,911 of 23,268 rows (25.4%).** Discovered via the None-date folder lookup, not searched for directly. `folder_absent` (5,911) exactly equals this count. Not interpreted further — that's explicitly out of scope for this phase.
- **Two files appeared in `docs/`** (`Agent_Prompt_Standard (1).md`, confirming a real v1.2 of the prompt standard, and `Mom-DB-Strategy-Research-Program.md`) with mtimes predating this phase, not found in Phase 0b's exhaustive search. Read in full; both appear genuine and substantive (the strategy doc's §2.3 explicitly calls for this exact reconciliation). Not committed or acted on — outside this phase's write scope (`results/phase_0c/`, `config/`, `prompts/`, `research/phase_0c/` only).

## 7. Output files

| File | Status |
|---|---|
| `config/phase_0c.json` | Done |
| `results/phase_0c/artifacts/folder_inventory.parquet` | Done (post-fix) |
| `results/phase_0c/artifacts/folder_inventory_summary.json` | Done |
| `results/phase_0c/artifacts/none_date_lookup.json` | Done |
| `results/phase_0c/artifacts/join_reconciliation.json` (+ `_detail.json`) | Done |
| `results/phase_0c/artifacts/failure_samples.json` | Done |
| `results/phase_0c/artifacts/repeat_ticker_comparison.json` | Done (not a required output file, added for T4's third comparison) |
| `results/phase_0c/charts/01_momentum_pct_joinable_vs_dropped.html` | Done |
| `results/phase_0c/charts/02_events_over_time_by_join_status.html` | Done |
| `results/phase_0c/charts/03_failure_class_counts.html` | Done |
| `results/phase_0c/REPORT.md`, `digest.json` | Done (digest passes its own validator, 57 lines) |

## 8. Commit list

```text
6145b2f docs: Phase 0c prompt + config
f5a6048 data: Phase 0c T1 - folder inventory, unparseable_name escalation
18ccc23 fix: Phase 0c T1 hard-stop resolution - parser fix, exclusions, None-date lookup
72d364e data: Phase 0c T2 - bidirectional join reconciliation
8a0b1dd data: Phase 0c T3 - failure samples for folder_absent and missing_quotes
5984852 data: Phase 0c T4 - distribution comparison charts, joinable vs dropped
```

(A final commit follows this REPORT.md + digest.json + map update.)
