# Phase 4 — Quotes-Side Coverage Census & Root-Cause Classification — Report

**Branch:** `phase/4` | **Baseline:** `phase-3-approved`

Description only, per the Evidence Standard — no recommendations, no causal claims about the buildout-error hypothesis on record. Evidence classes and counts speak for themselves.

---

## 1. T0b — venv calendar pin correction

Installed `pandas_market_calendars==5.4.0` / `exchange_calendars==4.13.2` directly into the shared `.venv` (was 5.3.0/4.12) — no dependency conflicts. Re-verified with fresh evidence (not just trusting Phase 3's isolated-install artifact): XNYS session list under the corrected venv, diffed against a fresh isolated install of the old drifted versions — **identical, 1,539/1,539 sessions, 0 diffs.** Closes the register item opened Phase 2 T8. Source: `results/phase_4/artifacts/t0b_versions.json`.

---

## 2. T1 — spine guard + cohort + overlap reconciliation

| Check | Expected | Observed | Result |
|---|---|---|---|
| `in_scope` guard | 20,951 | 20,951 | pass |
| Trades cohort (`source_file='file1' AND coverage_class='event_day_only'`) | 287 | 287 | pass |
| Quotes cohort (`source_file='file1' AND NOT quotes_full_window`) | 386 | 386 | pass |
| Overlap: both / trades-only / quotes-only | 259 / 28 / 127 | 259 / 28 / 127 | pass |

All 8 reconciliation checks between the live `momentum_events_canonical` view and `results/phase_2/artifacts/coverage_class.parquet` match exactly. `coverage_class` and `quotes_full_window` are independent per-row flags, so the overlap is a single `FILTER` pass, not a set join. Source: `results/phase_4/artifacts/t1_guard.json`.

---

## 3. T2 — filesystem census of `filtered/`

One pass over every folder under `data/filtered/`, deliberately **not** spine-joined (counts out-of-universe folders too). **24,723 event folders** (+ 3 non-folder top-level files: `METADATA.md`, `filtered_events_power_law_q05.parquet`, `scanner_hit_catalog.json`, not counted as events).

| `presence_class` | n |
|---|---|
| `both` | 23,003 |
| `trades_only` | 1,606 |
| `quotes_only` | 0 |
| `neither` | 114 |

The 114 `neither` folders are **exactly** the 114 `'None'`-date orphan folders (unresolvable-date/warrant tickers, e.g. `ACHR.WS_None_32.60`) — confirmed by exact set equality. Every real-dated folder has at least one of the two files. **0** unreadable or zero-row parquet files (escalation row 3 threshold: 0 — pass). `row_count` and session min/max date come from parquet footer/row-group statistics only, per T2's readability definition — no data-page scan.

**Drift vs. the pre-1c historical reference** (Schema.md snapshot, 2026-07-14: 24,200 trades / 22,660 quotes files) — treated as informational only, described not attributed: current 24,609 trades files present (**+409**), 23,003 quotes files present (**+343**). Source: `results/phase_4/artifacts/census_summary.json`.

---

## 4. T3 — three-way reconciliation (disk ↔ DB ↔ spine)

Joined the census to the full raw `momentum_events` population (23,268 rows, in-scope and out, via the live canonical view's `trades_ingested`/`quotes_ingested` provenance columns) on ticker + date + `ROUND(momentum_pct,2)`. **0 duplicate join keys.** Every one of the 23,268 raw `momentum_events` rows has a corresponding disk folder (`n_matched_to_spine` = 23,268 = spine row count) — the excess 1,455 disk folders (24,723 − 23,268) are the ones with no `momentum_events` correspondent: 114 by construction (`'None'`-date orphans) + 1,341 real-dated folders absent from the raw table entirely.

**Gap location (the 1,606 `trades_only` folders):**

| Bucket | n | % of gap |
|---|---|---|
| Unmatched to spine (no `momentum_events` row at all) | 1,341 | 83.5% |
| in_scope / file1 | 142 | 8.8% |
| out_of_scope / file2 | 74 | 4.6% |
| in_scope / file2 | 37 | 2.3% |
| out_of_scope / file1 | 12 | 0.7% |

The 1,341 unmatched figure independently reproduces CLAUDE.md's already-documented "1,341 orphan-folder events" — a consistency check, not a new finding. **The gap concentrates almost entirely (83.5%) outside the raw events table**, not within the in-scope research universe. Chart: `results/phase_4/charts/01_gap_location_waterfall.html`.

**127 quotes-only verification (T1's overlap number):** exact match, **127 = 98 (no quotes file at all, disk `trades_only`) + 29 (quotes file present but partial)** — two distinct failure shapes, both counted, confirming these are exactly the in-scope file1 subset of the disk-level `trades_only` + partial-quotes population.

**386-cohort no-file vs. partial-file:** **142 no-file + 244 partial-file = 386.** The 142 no-file count is itself an exact match to the "in_scope / file1" row of the gap-location table above (142 = 142) — every in-scope file1 disk-level `trades_only` folder is a member of the 386 cohort with no quotes file at all.

**Escalation row 1 (hard-stop check) — quotes data present + readable on disk, in-scope, matched to spine, but absent from `filtered_quotes`:** **0 events.** Pass — no ingestion gap found; whatever explains the quotes gap, it is not a mismatch between disk and the ingested table. Source: `results/phase_4/artifacts/reconciliation_summary.json`.

---

## 5. T4 — per-session quotes presence bitmap (386 cohort)

Single full-table pass over `filtered_quotes`, joined to all 20,951 in-scope events (not just the 386 cohort — the per-ticker signature check in T5 needs each ticker's full in-scope session history). XNYS calendar, pinned versions (5.4.0/4.13.2, post-T0b), same derivation range as Phase 2/3 (2019-12-01..2026-01-15, 1,539 sessions). **386/386 cohort events bitmapped, 16 distinct patterns.** Top pattern `0000000` (all 7 offsets missing) = **142** events — matches T3's no-quotes-file-at-all count exactly. Cached the full actual-sessions result for T5's reuse, so this is the phase's only full-table pass, per the Context section's commitment.

---

## 6. T5 — root-cause classification (386 cohort)

**Changed precedence design vs. Phase 3** (justified — Phase 3's calendar-flag intercept produced a label coarser than the true bitmap-shape cause for 21/35 `calendar_residue` events; the quotes side starts clean). Primary `label` is **bitmap-first**: intercepts only on `archive_edge` (a structural date-range check, unaffected by the calendar-flag critique), then falls through purely to the missing-offset pattern. `flag_window_calendar_bug`/`repaired_1c` are carried as annotation columns only and do not appear as a label. `label_p3_precedence` is also computed, applying Phase 3's exact original rule, for comparability.

| Label (bitmap-first) | n | % of 386 | Label (P3 precedence) | n | % of 386 |
|---|---|---|---|---|---|
| `backward_missing` | 217 | 56.22% | `backward_missing` | 195 | 50.52% |
| `both_sides` | 150 | 38.86% | `both_sides` | 139 | 36.01% |
| `forward_missing` | 19 | 4.92% | `calendar_residue` | 34 | 8.81% |
| `archive_edge` | 0 | 0% | `forward_missing` | 18 | 4.66% |
| `unclassified` | 0 | 0% | `archive_edge` / `unclassified` | 0 / 0 | 0% |

**0/386 unclassified** (escalation row 4: well under the 30%/115-event threshold — pass). No `archive_edge` events — every cohort event's expected window falls inside the observed file1 `filtered_quotes` session-date range (2019-12-30 .. 2025-01-06).

**Crosswalk (label × label_p3_precedence):** the 34 `calendar_residue` (P3-rule) events split under bitmap-first into **22 backward_missing + 11 both_sides + 1 forward_missing** — reproducing the coarsening effect the redesign was meant to surface. Chart: `results/phase_4/charts/02_quotes_missing_pattern_by_class.html`.

**T5a — weak signatures** (same definitions as Phase 3 T3a / A1-T4, applied quotes-side; within-archive only, not proof of delisting/late-listing):
- `forward_missing` (19 total): **3** show the weak delisting signature (event day = ticker's last-seen quotes session archive-wide).
- `backward_missing` (217 total): **195 (89.9%)** show the weak listing signature (ticker's first-seen quotes session later than expected T-3) — notably higher than Phase 3's trades-side rate (173/215, 80.5%).

Source: `results/phase_4/artifacts/classification_summary.json`.

---

## 7. T6 — collection-log correlation (descriptive only)

Parsed `data/collection_scripts/collection_log.txt` (113,871 lines; 17,745 `Processing` attempt records, 484 explicit `No quotes collected for X in window [...]` whole-window-failure records, plus per-session `Saved`/`No X found` lines) against the 386 cohort.

| `log_evidence` | n | % of 386 |
|---|---|---|
| `explicit_failure` | 142 | 36.79% |
| `mentioned_no_failure` | 244 | 63.21% |
| `not_mentioned` | 0 | 0% |

Every cohort event has some log trace. `explicit_failure` (142) maps exactly onto the no-quotes-file-at-all population — all 142 classify `both_sides` under bitmap-first (a fully-missing 7/7 window spans both sides of T=0), internally consistent with T3/T4/T5. No causal language; counts and matched-line examples only. Source: `results/phase_4/artifacts/log_correlation_summary.json`.

---

## 8. Escalation check table

| # | Condition | Threshold | Observed | Result |
|---|---|---|---|---|
| 1 | Quotes present+readable, in-scope, absent from `filtered_quotes` | ≥ 1 | 0 | pass |
| 2 | T1 guard mismatch (20,951 / 386 / 287 / 259-28-127) | any | exact match | pass |
| 3 | Present-but-unreadable or zero-row quotes.parquet | ≥ 1 | 0 | pass |
| 4 | `unclassified` share of 386 cohort | > 30% (>115) | 0 (0%) | pass |
| 5 | T0b diff check | ≠ 0 diffs | 0 diffs | pass |
| 6 | Any write to data root, DB main tables, or canonical view | any | none | pass |

No escalations triggered this phase.

---

## 9. Verification block

| Metric | Value | n | Source | Repro |
|---|---|---|---|---|
| T0b pin correction + diff | 1,539/1,539, 0 diffs | — | `results/phase_4/artifacts/t0b_versions.json` | `.venv/Scripts/python.exe -m research.phase_4.t0b_calendar_pin_correction --old-path <isolated 5.3.0/4.12 install>` |
| Spine guard | 20,951 | 20,951 | `results/phase_4/artifacts/t1_guard.json` | `.venv/Scripts/python.exe -m research.phase_4.t1_guard` |
| Trades / quotes cohort + overlap | 287 / 386 / 259-28-127 | — | `results/phase_4/artifacts/t1_guard.json` | same |
| Disk census | 24,723 folders | 24,723 | `results/phase_4/artifacts/census_summary.json` | `.venv/Scripts/python.exe -m research.phase_4.t2_disk_census` |
| Three-way reconciliation | table in §4 | 24,723 disk / 23,268 spine | `results/phase_4/artifacts/reconciliation_summary.json` | `.venv/Scripts/python.exe -m research.phase_4.t3_reconciliation` |
| Quotes bitmaps | 386/386, 16 patterns | 386 | `results/phase_4/artifacts/quotes_bitmaps.parquet` | `.venv/Scripts/python.exe -m research.phase_4.t4_quotes_bitmap` |
| Classification labels | table in §6 | 386 | `results/phase_4/artifacts/classification_summary.json` | `.venv/Scripts/python.exe -m research.phase_4.t5_classify` |
| Log correlation | table in §7 | 386 | `results/phase_4/artifacts/log_correlation_summary.json` | `.venv/Scripts/python.exe -m research.phase_4.t6_log_correlation` |

**Filter waterfall (cohort derivation):** `momentum_events` (23,268 raw) → `momentum_events_canonical` `in_scope=TRUE` (20,951) → `source_file='file1'` (15,763) → `NOT quotes_full_window` (386, the quotes cohort) — cross-checked against `coverage_class='event_day_only'` (287, the trades cohort) with overlap 259/28/127.

**Filter waterfall (disk census, T2/T3):** all `filtered/` entries (24,726) → event folders only (24,723; 3 non-folder files excluded) → `presence_class='trades_only'` (1,606, the gap) → matched to `momentum_events` (265 matched: 142+74+37+12) / unmatched (1,341).

**Environment:** `.venv` — duckdb 1.4.4, pandas 2.3.3, pyarrow 23.0.0, `pandas_market_calendars` 5.4.0, `exchange_calendars` 4.13.2 (corrected this phase, T0b — no drift from the phase-1c pin).

---

## 10. Output files

| File | Status |
|---|---|
| `prompts/phase_4.md` | committed |
| `config/phase_4.json` | committed |
| `research/phase_4/*.py` (12 scripts) | committed |
| `results/phase_4/artifacts/*.json` | committed |
| `results/phase_4/artifacts/*.parquet` | gitignored, regenerable |
| `results/phase_4/charts/01-04*.html` | committed |
| `docs/Open-Items-Register.md` | updated (T0b closed, T5 classification-complete line added) |
| `results/phase_4/digest.json`, `REPORT.md` | committed |

### Commits (phase-3-approved..HEAD)

T0 branch/prompt/config · T0b venv calendar pin correction · T1 spine guard · T2 disk census · T3 three-way reconciliation · T4 quotes bitmap (pre-run commit) · T5 classification · T6 log correlation · T7 charts 01-04 · T8 digest+REPORT+register (this commit).

---

## Approval Gate

Do not begin any follow-on work — including any spine mutation, any `quotes_full_window` semantic change, or any recollection scoping — until Cooper has reviewed results and given explicit approval.
