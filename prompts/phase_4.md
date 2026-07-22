# Phase 4 — Quotes-Side Coverage Census & Root-Cause Classification

**Date:** 2026-07-21
**Baseline:** `phase-3-approved` — spine guard 20,951 `in_scope`; file1 population 15,763; trades-side `event_day_only` cohort (287) fully classified; quotes-side cohort (386) identified but not root-caused
**Objective:** Establish the current disk↔DB↔spine state of quotes coverage across `filtered/`, quantify where the historical 1,540-file trades/quotes gap actually lives relative to the research universe, and classify the quotes-side gaps for the in-scope file1 cohort the way Phase 3 classified the trades side
**Primary success metric:** Full three-way reconciliation (disk census ↔ DB contents ↔ canonical spine) with zero unexplained rows, and ≥ 70% of the quotes-gap cohort classified

---

**Context:**
- The quotes-side numbers carried in from Phase 3 T3c (all `source_file='file1' AND in_scope=TRUE`): **386** events with `quotes_full_window=FALSE`; of these, **259** are also in the trades 287-cohort, **127** are quotes-only (`full_window` on trades). **28** trades-cohort events have no quotes-side flag.
- The historical folder-level gap from Schema.md (snapshot 2026-07-14, pre-1c): 24,200 trades files vs. 22,660 quotes files. **These counts are treated as a historical reference, not an expected current value** — Phase 1c re-collection has since modified the archive, and this phase measures current state.
- Working hypothesis on record (Cooper's, not to be asserted as finding): the quotes gaps originate in an error during the original dataset buildout. This phase gathers the evidence that would speak to it; it does not conclude on it.
- All aggregate queries against `filtered_trades` / `filtered_quotes` require the standing spine join (`momentum_events_canonical`, `in_scope=TRUE`) per CLAUDE.md. The census in T2 is the one deliberate exception: it must ALSO count out-of-universe folders, because locating the gap relative to the universe is the point. Where the join is intentionally omitted, the query must say so in a comment and the output must carry an `in_scope` breakdown column.
- **Two-tier deviation, justified:** this is a census/metadata phase. The unit of work is folders and event-sessions, not ticks. The only full-table pass is the single grouped per-session presence query in T4. There is no iterative development against tick data, so the dev tier does not apply. This deviation from the two-tier rule is per this paragraph, as required by the standard.
- Read-only guarantee: no writes to the data root, the DuckDB main tables, or `momentum_events_canonical`. New artifacts and (if needed) new `_phase4` DB tables only.
- Classification labels for the quotes side reuse Phase 3's vocabulary (`backward_missing`, `forward_missing`, `calendar_residue`, `both_sides`, `archive_edge`) **but with a changed precedence design — see T5. This is a deliberate divergence, justified there, with a crosswalk column preserving Phase 3 comparability.**

---

## Tasks

- [ ] **T0 — Branch and commit prompt**
  Cut `phase/4` from main (post phase-3 merge). Commit `prompts/phase_4.md` and `config/phase_4.json` before any other work.

- [ ] **T0b — Venv calendar pin correction (register item, approved Phase 3 gate)**
  Install `pandas_market_calendars==5.4.0` and `exchange_calendars==4.13.2` into the project `.venv` (the shared environment — this is the sanctioned correction, unlike the Phase 3 isolated check). Verify with an import-and-print of both versions. Re-run the existing XNYS session diff check from the Phase 3 gate verification against its saved reference output — expected 1,539/1,539, 0 diffs. Close the register line in `docs/Open-Items-Register.md`.
  - [ ] T0b-a — Version check artifact written
  - [ ] T0b-b — Diff check passes; commit

- [ ] **T1 — Spine guard**
  `in_scope=TRUE` count = 20,951 exactly. Quotes cohort (`source_file='file1' AND quotes_full_window=FALSE`) = 386 exactly. Trades cohort = 287 exactly. Overlap = 259/28/127 exactly. Artifact: `results/phase_4/artifacts/t1_guard.json`.
  - [ ] T1a — Commit

- [ ] **T2 — Filesystem census of `filtered/`**
  One pass over every event folder under the data root's `filtered/`. Per folder record: folder name (parsed into ticker/date/momentum_pct), `trades.parquet` {present, readable, row_count, min/max session date}, `quotes.parquet` {same four}. Readability = parquet footer opens and row count returns; do not scan full contents. Derive per-folder `presence_class ∈ {both, trades_only, quotes_only, neither}`.
  Artifact: `results/phase_4/artifacts/disk_census.parquet` + summary JSON with totals.
  - [ ] T2a — Report current totals vs. the historical 24,200/22,660 reference; describe drift, attribute nothing
  - [ ] T2b — Any file that is present but unreadable or readable-with-zero-rows: list exhaustively in the summary JSON (escalation table row 3 applies)
  - [ ] T2c — Commit

- [ ] **T3 — Three-way reconciliation (disk ↔ DB ↔ spine)**
  Join the census to (a) the DB: distinct event-folder provenance in `filtered_trades` / `filtered_quotes` (use the ingestion provenance columns; if none exist, derive by ticker+session-date match and document the method in the decisions log), and (b) `momentum_events_canonical` (all rows, with `in_scope` and `source_file` carried as columns).
  Required outputs:
  - Breakdown of every `trades_only` folder by {`in_scope`, `source_file`, matched-to-spine y/n} — **this is the number that locates the 1,540-gap descendant relative to the universe**
  - Verification that the 127 quotes-only in-scope file1 events from T1 are exactly the in-scope file1 subset of the disk-level `trades_only` + partial-quotes population, or an exact accounting of why not
  - Cross-check for the 386 cohort: does each have a quotes.parquet at all (partial sessions) vs. no file? Two different failure shapes; count both.
  - **Hard-stop check:** any event with quotes data present and readable on disk but absent from `filtered_quotes` for an in-scope event (escalation row 1)
  Artifact: `results/phase_4/artifacts/reconciliation.parquet` + JSON summary.
  - [ ] T3a — Commit

- [ ] **T4 — Per-session quotes presence bitmap (386 cohort)**
  Single full-tier grouped pass over `filtered_quotes` with the spine join: for each of the 386 events, a 7-position session bitmap (T-3..T+3) of quotes presence, using expected sessions from the XNYS calendar (post-T0b pinned versions). Mirror Phase 3's bitmap conventions exactly so patterns are comparable across the two cohorts.
  Artifact: `results/phase_4/artifacts/quotes_bitmaps.parquet`.
  - [ ] T4a — Commit before the run (long-run rule), commit results after

- [ ] **T5 — Root-cause classification (386 cohort)**
  Same label vocabulary as Phase 3. **Changed design, per approval-gate discussion:** labels are assigned **bitmap-first**; `repaired_1c` and `flag_window_calendar_bug` are carried as separate annotation columns and do NOT intercept the label. Rationale (baked in per the standard): Phase 3's precedence rule produced a label (`calendar_residue`) coarser than the true cause for 21 of 35 events; the quotes side starts clean. For cross-phase comparability, ALSO compute a `label_p3_precedence` column applying Phase 3's exact rule, so both labelings exist side by side.
  - [ ] T5a — Weak listing/delisting signatures computed with the same definitions as Phase 3 T3a / A1-T4, applied to the quotes cohort
  - [ ] T5b — Unclassified count vs. threshold (escalation row 4)
  - [ ] T5c — Commit

- [ ] **T6 — Collection-log correlation (descriptive only)**
  Parse `collection_scripts/collection_log.txt` (Confirmed provenance) for quote-fetch failures, errors, retries, or skips attributable to specific events. Match against the quotes-gap population from T3. Output: per-event {log_evidence ∈ {explicit_failure, mentioned_no_failure, not_mentioned}, matched log lines}. **No causal language.** Counts and examples only.
  Artifact: `results/phase_4/artifacts/log_correlation.parquet` + JSON summary.
  - [ ] T6a — Commit

- [ ] **T7 — Charts per the Chart Contract**
  - [ ] T7a-d — Charts 01–04 written
  - [ ] T7e — Commit

- [ ] **T8 — Digest, report, register**
  `digest.json` per §11, `REPORT.md` with every claim citing its chart. Add register lines: (a) quotes-side classification complete, (b) T0b pin closed, (c) any new open items from surprises. Confirm working tree clean.
  - [ ] T8a — Commit

---

## Escalation Criteria

Stop and post results. Do not proceed to the next task.

| # | Condition | Threshold | Action |
|---|-----------|-----------|--------|
| 1 | Quotes data on disk, readable, in-scope event, absent from `filtered_quotes` | ≥ 1 event | Hard stop — this is an ingestion gap, not a collection gap; changes the whole diagnosis. Commit, post the event list, await instruction |
| 2 | T1 guard mismatch (20,951 / 386 / 287 / 259-28-127) | any | Hard stop — spine drift since Phase 3 approval |
| 3 | Present-but-unreadable or zero-row quotes.parquet in census | ≥ 1 file | Hard stop — contradicts the "exact match" ingestion record; commit, post file list, await instruction |
| 4 | `unclassified` label share of 386 cohort | > 30% (> 115 events) | Hard stop — classification scheme not carrying over; post bitmap pattern table |
| 5 | T0b diff check | ≠ 0 diffs | Hard stop — the Phase 3 harmlessness verification no longer holds; post the diff |
| 6 | Any write to data root, DB main tables, or canonical view | any | Hard stop — post what was written and how |

---

## Output Files

| File | Description | Status |
|------|-------------|--------|
| `config/phase_4.json` | Thresholds, expected counts, paths, pinned calendar versions | [ ] |
| `results/phase_4/artifacts/t1_guard.json` | Spine/cohort guard values | [ ] |
| `results/phase_4/artifacts/disk_census.parquet` | Per-folder census | [ ] |
| `results/phase_4/artifacts/census_summary.json` | Totals, drift vs. historical reference, unreadable/zero-row list | [ ] |
| `results/phase_4/artifacts/reconciliation.parquet` | Disk↔DB↔spine join | [ ] |
| `results/phase_4/artifacts/reconciliation_summary.json` | Gap location breakdown | [ ] |
| `results/phase_4/artifacts/quotes_bitmaps.parquet` | Per-event session bitmaps, 386 cohort | [ ] |
| `results/phase_4/artifacts/classification.parquet` | Labels + annotations + `label_p3_precedence` | [ ] |
| `results/phase_4/artifacts/classification_summary.json` | Label table with n | [ ] |
| `results/phase_4/artifacts/log_correlation.parquet` + `.json` | Log-evidence match | [ ] |
| `results/phase_4/charts/01–04_*.html` | Per Chart Contract | [ ] |
| `results/phase_4/artifacts/t0b_versions.json` | Post-fix version + diff-check record | [ ] |

---

## Chart Contract

| # | File | Question | Encoding | n shown | Looks like this if wrong |
|---|------|----------|----------|---------|--------------------------|
| 01 | `charts/01_gap_location_waterfall.html` | Where does the trades/quotes folder gap live relative to the research universe? | Waterfall/stacked bars: all folders → presence_class → in_scope split → source_file split; counts as bar labels | Every bar labeled with n | Gap distributed evenly across in-scope and out-of-universe — no concentration, hypothesis of a localizable buildout error looks unsupported |
| 02 | `charts/02_quotes_missing_pattern_by_class.html` | Do quotes-side gap patterns mirror the trades-side patterns? | x=bitmap pattern (ordered by frequency), y=count, color=bitmap-first label; side panel: same chart for the trades 287 from Phase 3 artifacts | Per-bar n | Quotes patterns structurally different from trades patterns (e.g., mid-window holes, not edge-truncation) |
| 03 | `charts/03_cohort_temporal_distribution.html` | Is the quotes-gap cohort concentrated in time? | x=event month, y=count, color=presence shape (no-file vs. partial-file); overlay: file1 population share per month | Per-month n | Uniform share across all months — no collection-era signature |
| 04 | `charts/04_trades_quotes_label_matrix.html` | For the 259 dual-cohort events, do trades-side and quotes-side labels agree? | Heatmap: x=trades label (P3), y=quotes bitmap-first label, cell=n | n in every cell | Off-diagonal mass — the two sides fail for unrelated reasons per event |

Standard chart rules per Agent_Prompt_Standard.md §9 apply.

---

## Reporting

On completion, post:
1. T1 guard table
2. Census totals + drift vs. historical reference, with the unreadable/zero-row count stated explicitly even if 0
3. Gap-location breakdown table (the chart-01 numbers)
4. Classification label table with n and %, both labelings (bitmap-first and `label_p3_precedence`) side by side
5. Log-correlation summary: counts per evidence class
6. Escalation check table — every row, observed value, pass/fail
7. Verification block (§10) with filter waterfall
8. Output file table, commit list

Every claim cites its chart. Description only; no recommendations; no causal claims about the buildout-error hypothesis — evidence classes and counts speak for themselves.

On escalation: criterion, observed value, state committed, no fix attempted.

---

## Approval Gate

Do not begin any follow-on work — including any spine mutation, any `quotes_full_window` semantic change, or any recollection scoping — until Cooper has reviewed results and given explicit approval.
