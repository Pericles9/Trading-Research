# Phase 2 — 2025 Reconciliation & `trade_data/high_momentum/` Window Coverage — Report

**Branch:** `phase/2` | **Baseline:** `phase-1c-approved`

No recommendations below — description only, per the Evidence Standard. This phase produces evidence for Cooper's 2025 inclusion/holdout decision; it does not make that decision.

---

## 0. Pre-T1 finding: `high_momentum/` was already gone

Before T1 ran, checking `data/trade_data/` found `high_momentum/` **absent entirely** from the current E: data root — no subfolder, 0 files, not even the 47 files a prior report describes as deliberately kept back. Root cause, per git-tracked `results/cleanup/deletion_report.md` and `emergency_unblock_report.md` (both dated 2026-07-11, one day before the D:→E: hardware migration on 2026-07-12): `high_momentum`'s contents were migrated into `filtered/` on **D:** before this phase was cut — 5,902 of 5,949 unique 2025-gap `(ticker, date)` pairs migrated with a **subtractive 3-column schema** (`sip_timestamp`/`price`/`size` only, ms→ns converted, trades-only, no quotes); 47 confirmed-lost/blocked events kept back. Those 47 are also absent from E: now; their fate between 2026-07-11 and the E: migration is untraced (out of scope).

This is larger than the escalation table's "`high_momentum/` absent — not a stop" row anticipated, since it also implies most of the 2025 `filtered_trades` population may itself be the migrated data under a lossier schema. Surfaced to Cooper before proceeding; **Cooper's explicit instruction: proceed as literally scoped.** T3a, T4's `high_momentum` column, and T5 execute as N/A/absent-source per that escalation row. Full addendum: `prompts/phase_2.md`.

---

## 1. Spine guard + 2025 population (T1)

`momentum_events_canonical` in-scope guard: **20,951 observed = 20,951 expected — pass.**

2025 slice definition confirmed directly (not assumed): `momentum_events.date` (file1) spans 2020-01-03..2024-12-31, zero 2025 rows; `event_date` (file2) spans 2025-01-03..2025-10-31, zero pre-2025 rows. So the prompt's `source_file='scan_2025'` resolves to **`source_file='file2'`**.

| | n |
|---|---|
| 2025 raw (file2) | 5,911 |
| 2025 in-scope | 5,188 |
| 2025 excluded | 723 |
| `repaired_1c` (of in-scope) | 518 |
| residual `flag_missing_event_day` (of in-scope) | 0 |
| residual `flag_window_calendar_bug` (of in-scope) | 3 |
| trades-only (`quotes_ingested=FALSE`, of in-scope) | 37 |
| `skipped_collision` sessions belonging to 2025 events | 2 (SDOT, SHMD — both session 2025-10-13) |

5,188 + 723 = 5,911 — reconciles exactly. Excluded-reason breakdown (instrument class / flag combinations): warrant 475, fund_product 177, preferred 22, common+`flag_trades_mom_outlier` 19, right 16, other 8, unit 3, common+`flag_bad_denominator` 3, warrant+`flag_bad_denominator` 1 → 723. Source: `results/phase_2/artifacts/t1_population.json`.

---

## 2. 2025 quality screen (T2)

Population: the 5,188-event 2025 in-scope slice (T1's definition, not the raw 5,911).

| Check | Result |
|---|---|
| `momentum_pct` distribution | median 45.05, p95 184.77, p99 366.59, max 918.26 (n=5,188) |
| `momentum_pct` > 10,000 (sanity bound) | 0 |
| `prev_close` ≤ 0.01 | 0 |
| Stored-vs-recomputed momentum mismatch (tol 0.01) | 1,385/5,188 (26.7%) |
| Duplicate `(ticker, event_day)` pairs | 0 |
| Date range | 2025-01-03 .. 2025-10-31, 422-609 events/month |

Recompute formula, derived and confirmed exact-match on sample rows before use: `price_move = event_high - prev_close`, `momentum_pct = price_move / prev_close * 100` (file2 rows carry `event_high`/`event_open`/`event_close`, not `high`/`open`/`close`, which are structurally NULL for every file2 row). The 1,385 mismatches have median magnitude 0.10 percentage points (75th pct 0.32, max 22.44) and concentrate among low-`prev_close` names — consistent with 2-decimal-rounding amplification at low share prices, not verified further this phase. Chart: `results/phase_2/charts/02_2025_momentum_quality.html`.

**Migration-signature facet** (addendum, descriptive schema-fingerprint check, not proof of origin): of 5,848 2025 raw events with any `filtered_trades` rows, **all 5,848** have some rows matching the 2026-07-11 migration's exact null pattern across all 8 dropped columns (`exchange`/`id`/`participant_timestamp`/`sequence_number`/`tape`/`trf_id`/`trf_timestamp`/`correction`), and **5,352 (91.5%) are fully so** (≥99.9% of that event's rows). Source: `results/phase_2/artifacts/scan_2025_quality.json`.

---

## 3. `high_momentum/` inventory (T3)

**T3a:** `high_momentum/`, `logs/`, and `metadata/` are all absent from `data/trade_data/`. What's actually there: `collection_progress.json`, `enhanced/`, `high_momentum_progress.json`, `momentum_events_for_collection.parquet`, `optimized_progress.json`, `rebuild_validation_sample/`, `robust_progress.json`, `ultra_optimized_progress.json` — a different set than Schema.md documents (`batches/`, `by_date/`, `by_ticker/` are also absent). `enhanced/` and `rebuild_validation_sample/` exist but are outside this phase's four authorized paths; noted by name only, contents not read, per the `trade_data/` quarantine. No per-file inventory parquet — there are no files to inventory. Source: `results/phase_2/artifacts/high_momentum_inventory_summary.json`.

**T3b:** `momentum_events_for_collection.parquet` — 4,359 rows, 9 columns, 0 nulls, 0 duplicate `(ticker, date)` pairs, **100% year-2024-dated** (2024-01-02..2024-12-31). It does **not** establish the 2025 `high_momentum` population as the prompt anticipated.

| Overlap direction | Result |
|---|---|
| collection_list → canonical (any match) | 4,359/4,359 (100%) |
| collection_list → canonical (in-scope match) | 4,154/4,359 |
| collection_list → canonical file1 (pre-2025) population specifically | 4,359/4,359 (100%) |
| canonical 2025 in-scope → collection_list | 0/5,188 (0%) |

This file matches the pre-2025 (file1) population exactly and the 2025 in-scope slice not at all — on this evidence it's unrelated to the 2025 gap-fill migration. Source: `results/phase_2/artifacts/collection_list_overlap.json`.

---

## 4. Window coverage — the core question (T4)

5,188 in-scope 2025 events × XNYS T-3..T+3 (all 5,188 anchor dates are valid XNYS sessions; 0 excluded) × `{filtered_trades, filtered_quotes}`. `high_momentum` column N/A throughout (§0/§3a). Session date per row derived from `sip_timestamp` exactly as `research/phase_1b/window_calendar_bug_quantification.py` does it (`CAST(TO_TIMESTAMP(sip_timestamp/1e9) AS DATE)`).

| Offset | % events, `filtered_trades` | % events, `filtered_quotes` |
|---|---|---|
| T-3 | 3.62% | 3.70% |
| T-2 | 0.73% | 1.56% |
| T-1 | 0.69% | 2.31% |
| T=0 | **100.00%** | 99.29% |
| T+1 | 0.46% | 0.50% |
| T+2 | 0.46% | 0.50% |
| T+3 | 4.01% | 4.03% |

This is the chart contract's own "looks like this if wrong" case: near-100% at the event day, collapsing everywhere else. Per-event covered-session-count distribution (of 7): `filtered_trades` — 4,670 events at exactly 1, 518 at 2, nothing higher. `filtered_quotes` is slightly less concentrated (37 events at 0, 4,559 at 1, 543 at 2, up to 7 in one case) but tells the same story.

**Strata:**

| Stratum | n events | T-3 | T-2 | T-1 | T=0 | T+1 | T+2 | T+3 (`filtered_trades` %) |
|---|---|---|---|---|---|---|---|---|
| `repaired_1c` | 518 | 36.29 | 7.34 | 6.95 | 100.00 | 4.63 | 4.63 | 40.15 |
| residual `flag_window_calendar_bug` | 3 | 0 | 0 | 0 | 100.00 | 0 | 0 | 0 |
| trades-only (`quotes_ingested=FALSE`) | 37 | 0 | 0 | 0 | 100.00 | 0 | 0 | 2.70 |

The 518 phase-1c-`repaired_1c` events do meaningfully better at the outer offsets (36-40% vs. 0.7-4.0% for the general population) — these are exactly the events phase 1c's targeted re-fetch touched. The trades-only stratum's 0% `filtered_quotes` at every offset is expected by definition (`quotes_ingested=FALSE`), not a new finding. Chart: `results/phase_2/charts/01_window_coverage_by_offset.html`. No chart 04 — `high_momentum` has no dates at all to facet by year (decision recorded in `digest.json`).

---

## 5. Overlap comparison (T5)

N/A. 0 `(event, session)` pairs are present in both `filtered_trades` and `high_momentum` by construction (§0/§3a). Escalation check (row divergence >10% on >10% of compared event-sessions) is vacuously not triggered — absence of divergence is not evidence of agreement. Column-schema diff, reported from `results/cleanup/deletion_report.md`'s documentation only (source can't be read to verify independently): `filtered_trades` carries 11 DB-table columns; `high_momentum`'s documented migration write path is 3 (`price`/`sip_timestamp`/`size`), all 3 a subset of the 11. Chart 03 produced as an annotated empty-state rather than omitted. Source: `results/phase_2/artifacts/source_comparison_summary.json`.

---

## 6. Escalation check table

| Criterion | Threshold | Observed | Result |
|---|---|---|---|
| T1 canonical in-scope ≠ 20,951 | any | 20,951 | pass |
| Any task requires a DB/data-root write | any | none — `read_only=True` throughout | pass |
| T3a filename parse rate < 95% | as stated | N/A — no files | N/A |
| T3a unreadable/corrupt files > 2% | as stated | N/A — no files | N/A |
| T5 row divergence > 10% on > 10% event-sessions | as stated | N/A — 0 compared pairs | N/A |
| T3 `high_momentum/` absent or unreadable | — | **absent** | **triggered — not a stop; post finding + continue (§0)** |

---

## 7. Verification block

| Number | Value | Source | Repro |
|---|---|---|---|
| Spine guard | 20,951 | `results/phase_2/artifacts/t1_population.json` | `.venv/Scripts/python.exe -m research.phase_2.t1_population` |
| 2025 in-scope | 5,188 | `results/phase_2/artifacts/t1_population.json` | same |
| Recompute mismatch | 1,385/5,188 | `results/phase_2/artifacts/scan_2025_quality.json` | `.venv/Scripts/python.exe -m research.phase_2.t2_quality_screen` |
| Migration-signature | 5,352/5,848 fully | `results/phase_2/artifacts/scan_2025_quality.json` | same |
| Collection-list overlap | 4,359/4,359 vs. file1; 0/5,188 vs. 2025 | `results/phase_2/artifacts/collection_list_overlap.json` | `.venv/Scripts/python.exe -m research.phase_2.t3_high_momentum_inventory` |
| Window coverage by offset | table in §4 | `results/phase_2/artifacts/window_coverage_summary.json`, `.parquet` | `.venv/Scripts/python.exe -m research.phase_2.t4_window_coverage` |
| Source comparison | 0 pairs | `results/phase_2/artifacts/source_comparison_summary.json` | `.venv/Scripts/python.exe -m research.phase_2.t5_source_comparison` |

**Environment note:** T1-T3's first runs used system Python (duckdb 1.5.3, pandas 3.0.2 — `pandas_market_calendars` not installed there); T4 onward used the project `.venv` (duckdb 1.4.4, pandas 2.3.3, `pandas_market_calendars` 5.3.0, `exchange_calendars` 4.12). All canonical-spine SQL is identical across both; results were cross-checked consistent (the T1 guard and T2's population count both match exactly between runs). `.venv`'s calendar library versions drift from the phase-1c pin (5.4.0/4.13.2) — not upgraded, to avoid an unrequested environment change; documented in `config/phase_2.json`.

### Output files

| File | Status |
|---|---|
| `prompts/phase_2.md` (incl. addendum) | committed |
| `config/phase_2.json` | committed |
| `research/phase_2/*.py` (8 scripts) | committed |
| `results/phase_2/artifacts/*.json` | committed |
| `results/phase_2/artifacts/*.parquet` | gitignored, regenerable |
| `results/phase_2/charts/01-03*.html` | committed |
| `results/phase_2/charts/04*` | not produced — condition not triggered |
| `results/phase_2/digest.json`, `REPORT.md` | committed |

### Commits (phase-1c-approved..HEAD)

T0 branch/prompt/config · T1 spine guard + 2025 population · T2 2025 quality screen + chart 02 · T3 high_momentum inventory (absent) + collection-list overlap · T4 window coverage matrix + chart 01 (incl. strata-bug fix) · T5 overlap comparison (N/A) + chart 03 · T7 digest + REPORT (this commit).

---

## Approval Gate

Do not begin Phase 3 or any follow-on work until Cooper has reviewed results and given explicit approval. Pending: **2025 inclusion vs. terminal-holdout status**, and — conditional on that — whether the dev sample is re-pinned to a 2025-inclusive eligibility pool.
