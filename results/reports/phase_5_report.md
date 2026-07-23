# Phase 5 — Window Flags & Canonical Spine Finalization — Report

**Branch:** `phase/5` | **Baseline:** `phase-4-approved`

Description only, per the Evidence Standard — no recommendations. The bias call on chart 02 is Cooper's, per the phase prompt.

---

## 0. Pre-phase housekeeping

`phase-4-approved` did not exist when this phase began — Phase 4's last commit was `complete_awaiting_approval` and `master` was still at `phase-3-approved`. Per in-session authorization, the approval was recorded (`results/phase_4/digest.json` status → `complete_approved`), tagged `phase-4-approved` at Phase 4's tip, and `master` fast-forwarded, before `phase/5` was cut. Same pattern as every prior phase transition (cf. `phase-3-approved`).

---

## 1. T1 — pre-mutation guard + view DDL snapshot

| Check | Expected | Observed | Result |
|---|---|---|---|
| `in_scope` guard | 20,951 | 20,951 | pass |
| Trades cohort (`coverage_class='event_day_only'`, file1) | 287 | 287 | pass |
| Quotes cohort (`NOT quotes_full_window`, file1) | 386 | 386 | pass |
| Overlap: both / trades-only / quotes-only | 259 / 28 / 127 | 259 / 28 / 127 | pass |

All 8 reconciliation checks vs. `coverage_class.parquet` match exactly, reproducing Phase 4's T1. View DDL exported verbatim (`duckdb_views().sql`) to `view_ddl_pre.sql` (2,729 chars) as the rollback reference.

**A preview that mattered:** the live view already carries Phase 2 T8's `coverage_class`/`quotes_full_window` columns. Querying them for `source_file='file2'` showed 5,188/5,188 (100%) not-full-window on trades and 5,187/5,188 (99.98%) on quotes — before either budgeted full-table pass ran. This correctly anticipated T4's escalation. Source: `results/phase_5/artifacts/t1_guard.json`.

---

## 2. T2 — trades-side session bitmap, all 20,951 in-scope events

Extended Phase 3's exact bitmap derivation (XNYS, pinned `pandas_market_calendars==5.4.0`/`exchange_calendars==4.13.2`, offsets T-3..T+3) from the file1-only 287 cohort to the full in-scope population. Verified against `filtered_trades_dev_v3` first (50/50 events bitmap `1111111`, consistent with v3's `full_window` eligibility rule) before the one budgeted full-table pass over `filtered_trades` (4.95B rows).

| | not full window | full window | total |
|---|---|---|---|
| file1 | 287 | 15,476 | 15,763 |
| file2 | 5,188 (100.00%) | 0 | 5,188 |

Top bitmap pattern for the flagged population: `0001000` (event-day only), n=4,670. Source: `results/phase_5/artifacts/trades_bitmaps_summary.json`.

---

## 3. T3 — quotes-side session bitmap, all 20,951 in-scope events

Reused Phase 4 T4's cached full-population actual-sessions result (`_actual_quotes_sessions_cache.parquet`) instead of a second full-table pass. Reuse required calendar pin, offsets, and in-scope population to match — all three verified (`t3_cache_reuse_verification.json`, `reuse_authorized=true`): every one of the 20,772 distinct events in the cache belongs to the current 20,951-event in-scope population, and the calendar/offset configuration is identical between Phase 4 and Phase 5.

| | not full window | full window | total |
|---|---|---|---|
| file1 | 386 | 15,377 | 15,763 |
| file2 | 5,187 (99.98%) | 1 | 5,188 |

Independently reproduces T1's live-view preview via a different code path (cached tick data vs. the `coverage_class.parquet` join). Top bitmap pattern: `0001000`, n=4,559. Source: `results/phase_5/artifacts/quotes_bitmaps_all_summary.json`.

---

## 4. T4 — derive `spine_window_flags` + reconciliation

Built `results/phase_5/artifacts/spine_window_flags.parquet` (20,951 rows) merging T2/T3, computing `clean_window = trades_full_window AND quotes_full_window`, and carrying Phase 3's trades labels (287 cohort) and Phase 4's quotes labels (386 cohort) — `not_classified` for every flagged event outside those file1-scoped cohorts (i.e., all of file2), NULL only for clean events. Also materialized as DuckDB table `spine_window_flags`.

**T4a — file1 reconciliation (all exact):**

| Check | Expected | Observed | Match |
|---|---|---|---|
| Trades flagged | 287 | 287 | ✅ |
| Quotes flagged | 386 | 386 | ✅ |
| Union | 414 | 414 | ✅ |
| Overlap both/trades-only/quotes-only | 259/28/127 | 259/28/127 | ✅ |

**T4b — known-37 file2 no-quotes-file events:** all 37 located (Phase 4 T3's disk-level `trades_only` file2 events) and all 37 confirmed flagged on the quotes side.

**T4c — label integrity:** 0 violations in every direction (no flagged event with a NULL label, no clean event with a non-NULL label), both sides.

**T4d — file2 first measurement:**

| | n flagged | % of file2 (5,188) |
|---|---|---|
| trades | 5,188 | 100.00% |
| quotes | 5,187 | 99.98% |

This triggered **escalation row 4** (>5%/>260 threshold, written expecting a small file2 minority). Per the phase prompt's own instruction, work stopped here, was committed, and reported — full bitmap pattern tables in `results/phase_5/artifacts/reconciliation_summary.json`.

---

## 5. Amendment 4 — escalation row 4 disposition

Cooper's decision (2026-07-22, `prompts/phase_5_amendment_4.md`): the observed file2 flagged shares are **structural, not a defect** — consistent with Phase 2 T8's `coverage_class.parquet` (identical derivation, computed before this phase ran) and the already-registered 2025 3-column-schema data-quality issue. No re-derivation required. Escalation row 4 retroactively rescoped to file1 only:

| | flagged | % of file1 (15,763) | vs. 5%/788 threshold |
|---|---|---|---|
| trades | 287 | 1.82% | pass |
| quotes | 386 | 2.45% | pass |

`config/phase_5.json`'s original file2 threshold fields are retained, marked superseded, for the historical record. File2 keeps its `not_classified`/~100%-flagged state unchanged — T2/T3/T4 outputs stand as computed. Work resumed at T5.

---

## 6. T5 — rebuild `momentum_events_canonical`

Added `stage="t7"` to `src/data/canonical.py`: left-joins `spine_window_flags` on `(ticker, event_date_canonical, ROUND(momentum_pct,2))`, adding `trades_full_window`, `clean_window`, `trades_gap_label`, `quotes_gap_label`, `trades_bitmap`, `quotes_bitmap`. **`quotes_full_window` was not re-added** — the view already carries it from Phase 2 T8's `coverage_class` join (`stage="t6"`), and it was verified byte-identical to `spine_window_flags`' independently-recomputed value across all 20,951 events (0 mismatches) before the SQL was written; adding a second same-named column would be invalid.

| Check | Result |
|---|---|
| Row count | 23,268 → 23,268, unchanged |
| `in_scope` | 20,951 → 20,951, unchanged |
| Sample diff (400 seeded tickers, 3,103 rows, all pre-existing columns) | byte-identical, 0 diffs |
| New columns present | yes, all 6 |
| Idempotence (rebuilt twice) | DDL identical, data identical |

Live-view spot-check reconciles exactly against `spine_window_flags`: 287/386 file1, 5,188/5,187 file2, 15,349 clean / 5,602 flagged, 0 label-integrity violations. No escalations triggered (rows 1, 6 both clear). Source: `results/phase_5/artifacts/t5_mutation_safety.json`, `view_ddl_post.sql`.

---

## 7. T6 — charts

- **01 — clean vs. flagged by year** (`charts/01_clean_vs_flagged_by_year.html`): stacked clean/flagged by event year, faceted by `source_file`. File1's flagged share is small and roughly stable across years (32–122 events/year); file2 is ~100% flagged in its only year (2025).
- **02 — momentum_pct, clean vs. flagged** (`charts/02_momentum_pct_clean_vs_flagged.html`): violin+strip, log y-axis, no clipping. File1's clean (n=15,349) and flagged (n=414) distributions overlap closely — flagging does not visibly separate the momentum_pct distribution on file1. File2 has effectively no clean group (1/5,188), so its panel is degenerate by construction; the file1 panel is the one that answers the chart's bias question.
- **03 — flag label composition** (`charts/03_flag_label_composition.html`): `not_classified` dominates both sides (94.8% of trades-flagged, 93.1% of quotes-flagged) — by construction, since it is the entire file2 population and Phase 3/4's classification cohorts were file1-scoped. File1's own labels cover 100% of file1's flagged population with 0 `not_classified`. Per Amendment 4, this dominance is the expected shape, not evidence the carried classifications explain little.

All three visually verified via kaleido PNG render before commit.

---

## 8. Escalation check table

| # | Condition | Threshold | Observed | Result |
|---|---|---|---|---|
| 1 | Post-mutation `in_scope`/row count changed | any deviation | 23,268/20,951 unchanged both times | pass |
| 2 | T1 guard mismatch | any deviation | exact match | pass |
| 3 | T4a/b reconciliation mismatch | any deviation | exact match, 37/37 flagged | pass |
| 4 | file2 flagged share (original scope) | >5%/>260 | 100.00%/99.98% | **triggered → Amendment 4** |
| 5 | Label integrity | any violation | 0 | pass |
| 6 | Idempotence failure | any diff | 0 diffs | pass |
| 7 | Calendar pin drift | ≠5.4.0/4.13.2 | 5.4.0/4.13.2 installed | pass |
| 8 | Base-table/data-root write | any | none | pass |

---

## 9. Verification block

| Metric | Value | n | Source | Repro |
|---|---|---|---|---|
| Pre-mutation guard | 20,951/287/386/259-28-127 | 20,951 | `results/phase_5/artifacts/t1_guard.json` | `.venv/Scripts/python.exe -m research.phase_5.t1_guard` |
| Trades bitmap (all in-scope) | 287/5,188 flagged | 20,951 | `results/phase_5/artifacts/trades_bitmaps_summary.json` | `.venv/Scripts/python.exe -m research.phase_5.t2_trades_bitmap` |
| Quotes bitmap (all in-scope, cache reuse) | 386/5,187 flagged | 20,951 | `results/phase_5/artifacts/quotes_bitmaps_all_summary.json` | `.venv/Scripts/python.exe -m research.phase_5.t3_quotes_bitmap` |
| spine_window_flags + reconciliation | table in §4 | 20,951 | `results/phase_5/artifacts/reconciliation_summary.json` | `.venv/Scripts/python.exe -m research.phase_5.t4_derive_flags` |
| View rebuild mutation safety | table in §6 | 23,268 / 20,951 | `results/phase_5/artifacts/t5_mutation_safety.json` | `.venv/Scripts/python.exe -m research.phase_5.rebuild_canonical_view` |

**Filter waterfall (flag derivation):** `momentum_events` (23,268 raw) → `in_scope=TRUE` (20,951) → per-event 7-offset bitmap vs. `filtered_trades`/`filtered_quotes` (20,951 both sides) → `clean_window` (15,349) / flagged (5,602, of which 414 file1 + 5,188 file2).

**Filter waterfall (view rebuild):** live view pre-mutation (23,268 rows, 17 columns) → `stage="t7"` left-join on `spine_window_flags` → post-mutation (23,268 rows, 23 columns: +6 new, `quotes_full_window` not duplicated) → idempotence re-run (23,268 rows, byte-identical DDL and data).

**Environment:** `.venv` — duckdb 1.4.4, `pandas_market_calendars` 5.4.0, `exchange_calendars` 4.13.2 (matches the pin, no drift).

---

## 10. Output files

| File | Status |
|---|---|
| `prompts/phase_5.md`, `prompts/phase_5_amendment_4.md` | committed |
| `config/phase_5.json` | committed |
| `research/phase_5/*.py` (8 scripts) | committed |
| `results/phase_5/artifacts/*.json`, `*.sql` | committed |
| `results/phase_5/artifacts/*.parquet` | gitignored, regenerable |
| `results/phase_5/charts/01-03*.html` | committed |
| `src/data/canonical.py` | modified (stage="t7" added, additive) |
| `docs/Open-Items-Register.md` | updated (4 entries closed) |
| `results/phase_5/digest.json`, `REPORT.md` | committed |

### Commits (`phase-4-approved..HEAD`)

Pre-phase: phase-4 approval recorded + tagged, master fast-forwarded. T0 branch/prompt/config · T1 pre-mutation guard · T2 trades bitmap (pre-run commit + full-pass commit) · T3 quotes bitmap (cache reuse) · T4 derive flags — escalation row 4 · A4 Cooper's disposition · T5 view rebuild · T6 charts · T7 register/digest/REPORT (this commit).

---

## Approval Gate

Do not begin any follow-on work — including dev-sample rebuild, any Phase 6 scoping, or any use of `clean_window` as a filter in analysis — until Cooper has reviewed results and given explicit approval. On approval, tag `phase-5-approved`.
