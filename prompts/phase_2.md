# Phase 2 — 2025 Reconciliation & `trade_data/high_momentum/` Window Coverage

**Date:** 2026-07-20
**Baseline:** `phase-1c-approved` — canonical spine `momentum_events_canonical`: 20,951 in-scope (20,772 both-sides + 179 trades-only), `repaired_1c` live, all calendar-explained gaps healed. Residuals: 1 `flag_missing_event_day` (SNWV_2022-10-10), 17 `flag_window_calendar_bug`, 10 `skipped_collision` sessions. Dev sample v2 (50 events, seed 42) pinned and unaffected by the heal.
**Objective:** Quality-screen the 2025 scan rows, determine whether `trade_data/high_momentum/` covers the XNYS T-3…T+3 session window per 2025 in-scope event, and compare it against the healed `filtered/` archive where the two overlap.
**Primary success metric:** Per-event, per-offset coverage matrix for every 2025 in-scope event, both sources side by side, with the residual-flag strata separated. This phase produces the evidence for Cooper's 2025 inclusion/holdout decision at the gate — it does not make that decision.

**Format note:** compact prompt. Standard §§9–12 (chart rules, verification block, digest contract, git discipline) apply by reference to `docs/Agent_Prompt_Standard.md` v1.3 — commit per task, every number with n, every claim cites a chart or artifact, no recommendations.

---

**Context & constraints:**

- **Scoped quarantine lift.** Cooper explicitly authorizes **read-only** access to `data/trade_data/high_momentum/`, `data/trade_data/momentum_events_for_collection.parquet`, and the adjacent `trade_data/logs/` + `trade_data/metadata/` where needed to establish provenance. Nothing else in `trade_data/` is touched. Path per Schema.md — if the actual location differs, post what was found and use it, read-only.
- **Zero DuckDB writes this phase.** No new tables, no inserts, no view changes. All outputs go to `results/phase_2/`. If any task appears to require a DB or data-root write, that is a hard stop, not a workaround.
- **Spine join, not folder presence.** Every event-level aggregate joins `momentum_events_canonical` with `in_scope = TRUE`. `filtered/` coverage is read from `filtered_trades` / `filtered_quotes` (which now contain the 1c heals), never from a raw directory scan.
- **XNYS only.** Expected T-3…T+3 sessions per event are derived from the XNYS session calendar off `event_date_canonical`. The legacy federal-calendar function is not used for anything in this phase.
- **Residuals are strata.** The 1 + 17 residual-flag events and the 10 `skipped_collision` sessions are reported separately wherever they fall into a measurement — never silently pooled.
- **Reuse before recompute.** If a committed Phase 1b/1c artifact already contains a required measurement, cite it (path + which sub-item it covers) in `decisions_log` instead of recomputing.
- Parquet footers (row counts, min/max timestamps, schema) are sufficient wherever the task doesn't need row-level reads. `high_momentum/` file integrity is unknown — wrap all reads; unreadable files are counted and listed, not fixed.
- Config: `config/phase_2.json` — junk-momentum sanity bound (default 10,000), recompute-mismatch tolerance (0.01), divergence thresholds (0.10 / 0.10), filename parse-rate floor (0.95), unreadable-file ceiling (0.02), seed 42.

---

## Tasks

- [ ] **T0 — Branch.** Cut `phase/2` from `phase-1c-approved`. Commit `prompts/phase_2.md` + `config/phase_2.json` before any other work.

- [ ] **T1 — Spine guard + 2025 population.** Verify `momentum_events_canonical` `in_scope = TRUE` count equals **20,951** (escalation row 1 on mismatch). Define the 2025 slice: `source_file = 'scan_2025'` (or the equivalent canonical flag) AND `in_scope = TRUE`. Report: 2025 in-scope n; 2025 excluded n by exclusion reason; how many 2025 events carry `repaired_1c`, a residual flag, or trades-only coverage. → `artifacts/t1_population.json`. Commit.

- [ ] **T2 — 2025 quality screen** (descriptive; nothing deleted, no spine writes — junk flags live in the artifact only, pending Cooper's inclusion decision). For the 2025 slice: `momentum_pct` distribution; junk flags (`momentum_pct` > sanity bound; `prev_close` ≤ 0.01 where the column exists; stored vs. recomputed momentum mismatch > tolerance where fields permit); duplicate `(ticker, event_day)` pairs; event_day range and per-month counts. → `artifacts/scan_2025_quality.json` + chart 02. Commit.

- [ ] **T3 — `high_momentum/` inventory** (read-only, per the scoped lift):
  - [ ] T3a — Structure: directory layout, naming schema, file formats, column schemas, and whether quotes exist there or trades only. Parse every filename/folder into `(ticker, date[, …])`; report parse rate. Distinct tickers, full date range, files-per-ticker distribution, per-file row counts + min/max timestamps from footers, unreadable-file count. → `artifacts/high_momentum_inventory.parquet` (one row per file) + summary JSON.
  - [ ] T3b — Characterize `momentum_events_for_collection.parquet`: row count, columns, date range; overlap with the canonical spine on `(ticker, event_day)`, both directions. This establishes what population `high_momentum/` was built to cover. If unreadable: record, continue, note in surprises. → `artifacts/collection_list_overlap.json`.
  - [ ] T3c — Commit.

- [ ] **T4 — Window coverage — the core question.** For each 2025 in-scope event: the 7 expected XNYS sessions, and presence of each offset (−3…+3) in (a) `filtered_trades` post-heal, (b) `filtered_quotes` post-heal, (c) `high_momentum/` trades (and quotes, if T3a found any). Outputs: full per-event × per-offset matrix; summary by offset per source; per-event covered-session-count distribution (0–7) per source; residual-flag and `repaired_1c` strata broken out. **If T3a shows `high_momentum/` contains pre-2025 dates, extend the matrix to all in-scope events and facet by year; otherwise 2025 only — state which branch was taken in `decisions_log`.** → `artifacts/window_coverage.parquet` + summary JSON + charts 01 (and 04 if the extended branch runs). Commit.

- [ ] **T5 — Overlap comparison.** For every `(event, session)` present in both `filtered_trades` and `high_momentum/`: per-session trade row counts compared; column-schema diff between the sources (enumerate, don't stop). Divergence > 10% of rows on > 10% of compared event-sessions → escalation row 4. → `artifacts/source_comparison.parquet` + chart 03. Commit.

- [ ] **T6 — Charts** per contract; any not already written in T2/T4/T5. Commit.

- [ ] **T7 — Digest, REPORT.** Digest passes the validator; every claim cites its chart; working tree clean. Commit.

---

## Escalation Criteria (table order = priority)

| Condition | Threshold | Action |
|---|---|---|
| T1: canonical in-scope count ≠ 20,951 | any | Hard stop — wrong spine version; post observed count, await |
| Any task requiring a write to the data root or any DuckDB object | any | Hard stop — post what write seemed necessary and why, await |
| T3a: filename parse rate < 95% | as stated | Hard stop — post unparsed examples grouped by pattern, await |
| T3a: unreadable/corrupt files > 2% of inventory | as stated | Hard stop — post failure list + error classes, await |
| T5: row divergence > 10% on > 10% of compared event-sessions | as stated | Hard stop — post divergence table + chart 03, await |
| T3: `high_momentum/` absent or unreadable at the expected path | — | Post finding + continue; T3a/T4(c-source)/T5 marked N/A. Not a stop |

Documented findings, not stops: junk-row counts (T2); quotes absent from `high_momentum/` (T3a); schema diffs between sources (T5); `collection_list` unreadable (T3b).

---

## Output Files

| File | Status |
|---|---|
| `config/phase_2.json` | [ ] |
| `results/phase_2/artifacts/t1_population.json` | [ ] |
| `results/phase_2/artifacts/scan_2025_quality.json` | [ ] |
| `results/phase_2/artifacts/high_momentum_inventory.parquet` + summary JSON | [ ] |
| `results/phase_2/artifacts/collection_list_overlap.json` | [ ] |
| `results/phase_2/artifacts/window_coverage.parquet` + summary JSON | [ ] |
| `results/phase_2/artifacts/source_comparison.parquet` | [ ] |
| `results/phase_2/charts/01–03` (+ 04 conditional) | [ ] |

---

## Chart Contract

| # | File | Question | Encoding | n shown | Looks like this if wrong |
|---|---|---|---|---|---|
| 01 | `charts/01_window_coverage_by_offset.html` | Do the 2025 events have full XNYS T-3…T+3 coverage, and in which source? | x = session offset (−3…+3), y = % of events with session present, grouped bars: `filtered_trades` / `filtered_quotes` / `high_momentum` (+ hm quotes if found); per-event covered-count strip beneath | n events per source in title, per-bar counts | Bars near 100% at offset 0 but collapsing at ±1…3 in `high_momentum` — event-day-only collection; the T+1 surface for 2025 rests entirely on `filtered/` |
| 02 | `charts/02_2025_momentum_quality.html` | How much of the 2025 scan is junk? | x = momentum_pct (log), ECDF + strip, junk-flagged rows colored, sanity bound marked | total and flagged n in legend | Flagged mass is a fat contiguous tail rather than isolated points — systematic prev_close corruption, not a few bad rows |
| 03 | `charts/03_source_rowcount_comparison.html` | Do the two sources agree where they overlap? | x = `filtered_trades` rows, y = `high_momentum` rows, per event-session, log-log scatter, y = x line, unreadable/zero-row points flagged | n compared pairs in caption | Points off the diagonal in one direction — one source is systematically thinner and "clean" needs a definition |
| 04 | `charts/04_coverage_year_by_offset.html` *(conditional — only if T3a finds pre-2025 dates)* | Does `high_momentum` coverage vary by event year? | x = offset, y = year, heatmap of % coverage, count annotated per cell | n per cell | Coverage strong only for one year band — the folder is a partial recollection, not a parallel archive |

---

## Reporting

Post: T1 population table with strata; 2025 quality table; inventory summary (including the quotes-present answer, stated plainly); collection-list overlap both directions; window-coverage matrix by offset and source with residual strata separated; T5 divergence summary + schema diff; escalation check table; verification block; output files; commits. No recommendations.

---

## Approval Gate

Do not begin Phase 3 or any follow-on work until Cooper has reviewed results and given explicit approval. Pending at this gate, from Cooper: **2025 inclusion vs. terminal-holdout status**, and — conditional on that — whether the dev sample is re-pinned to a 2025-inclusive eligibility pool.

---

## Addendum — pre-execution finding (recorded before T1 ran)

Before T1 ran, investigation of `data/trade_data/` found `high_momentum/` **absent entirely** from the current E: data root (no subfolder, 0 files — not even the 47 previously-blocked files). Root cause, per git-tracked `results/cleanup/deletion_report.md` and `emergency_unblock_report.md` (dated 2026-07-11, one day before the D:→E: hardware migration on 2026-07-12): `high_momentum`'s contents were already migrated into `filtered/` on **D:** before this phase was cut — 5,902 of 5,949 unique 2025-gap `(ticker, date)` pairs migrated (subtractive 3-column schema: `sip_timestamp`/`price`/`size` only, ms→ns converted, trades-only, no quotes), 47 confirmed-lost/blocked events kept back and not deleted. The 47 remaining files are not present on E: either; their fate between 2026-07-11 and the E: migration has not been traced further (out of this phase's scope).

Per the escalation table row "`high_momentum/` absent or unreadable — post finding + continue; T3a/T4(c-source)/T5 marked N/A. Not a stop," and Cooper's explicit instruction to proceed as literally scoped: T3a, T4's `high_momentum` column, and T5 are executed as N/A / absent-source. The migration provenance and its data-quality implications (subtractive schema now embedded in a portion of `filtered_trades` for 2025 events) are recorded in `decisions_log` / `surprises` and folded into T2's quality screen as an additional descriptive (non-blocking) facet, not as a redefinition of T4/T5's literal scope.
