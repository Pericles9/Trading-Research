# Phase 2b (Phase 3) — Pre-2025 `event_day_only` Characterization + Dev Sample Verification — Report

**Branch:** `phase/3` | **Baseline:** `phase-2-approved`

Covers the base prompt (`prompts/phase_3.md`) and Amendment 1 (`prompts/phase_3_amendment_1.md`), which superseded the original T2 task after it escalated. No recommendations below — description only, per the Evidence Standard. No statements about survivorship-bias magnitude, delisting rates, or T+1 implications — counts and descriptions only, per the prompt's explicit scope limit.

---

## 1. Spine guard + cohort reconciliation (T1)

`in_scope` guard: **20,951 = 20,951 — pass.** Trades cohort (`source_file='file1' AND coverage_class='event_day_only'`): **287 = 287 — pass.** Quotes cohort (`source_file='file1' AND quotes_full_window=FALSE`): **386 = 386 — pass.** All 5 reconciliation checks between the live `momentum_events_canonical` view and `results/phase_2/artifacts/coverage_class.parquet` match exactly — no drift since Phase 2 T8. Source: `results/phase_3/artifacts/t1_cohort.json`.

---

## 2. Dev sample check — original T2, escalated, superseded by Amendment 1

Dev sample v2 (`config/dev_sample_v2.json`, seed 42) membership check against the live canonical view: all 50 events matched, but **15/50 (30%)** carry `coverage_class='event_day_only'`, not `full_window` — 14 file2 (2025) events (expected, given Phase 2's finding that 2025 is essentially all `event_day_only`) **and one pre-2025 event, `PLBY_2021-02-16`**, one of the 287-cohort. This tripped the phase's own escalation criterion ("any dev event `coverage_class != 'full_window'`") — committed as a hard stop (`22d0123`), full listing in `results/phase_3/artifacts/dev_sample_coverage.json`.

---

## 3. Amendment 1 — dev sample v3 re-pin

**A1-T1 — prior-use safety scan.** Scanned all 7 committed `results/phase_*/{digest.json,REPORT.md}` for dev-tier mentions: 7 candidates found, all classified `not_a_hit` per the amendment's own distinguishing rule (sample-construction/QA checks — decile-spanning, zero-row, subset-match — or one Phase 0b infrastructure query-latency benchmark, none a substantive research finding whose comparability a re-pin would break). **0 true hits — escalation not triggered.** Full candidate list with reasoning: `results/phase_3/artifacts/a1_dev_usage_scan.json`.

**A1-T2 — v2 builder location.** Unambiguous: `research/phase_1b/build_dev_sample_v2.py` is the only script that writes `config/dev_sample_v2.json`. Confirmed it also materializes `filtered_trades_dev_v2`/`filtered_quotes_dev_v2` — distinct from the retired v1 tables (`filtered_trades_dev`/`filtered_quotes_dev`, built by `research/phase_0b/materialize_dev_tables.py` from the retired `config/dev_sample_events.csv`).

**A1-T3 — v3 build.** Eligibility = v2's rule **AND** `coverage_class='full_window'` **AND** `quotes_full_window=TRUE`. Eligible pool: **15,349** (down from v2's 18,787 — an ~18% reduction, as predicted, given pre-2025 `full_window`/`quotes_full_window` populations of 15,476/15,377). Same seed (42), same decile-stratification logic (`pd.qcut` + `numpy.random.default_rng`, byte-for-byte inherited), same count (50). Result: 50 events across all 10 deciles. `filtered_trades_dev_v3`: 11,871,483 rows; `filtered_quotes_dev_v3`: 7,943,227 rows, materialized from `filtered_trades`/`filtered_quotes` only (read-only source of the join — the main tables and the canonical view were never written to). **A1-T3b rule verification: 0/50 failures.** Subset verification: 0/50 mismatches. Source: `results/phase_3/artifacts/dev_sample_v3_build_summary.json`.

**A1-T3a — v2 vs. v3 overlap (descriptive).** **0/50 events in common** — every one of the 50 v2 events was dropped (including all 35 that were already `full_window`), and all 50 v3 events are new draws. Not an error: `rng.choice(pool.index, size=take, replace=False)` draws against each run's own eligible-population DataFrame's row indices; changing the eligibility filter changes which rows exist and in what order, so the same seed does not imply index alignment across two differently-filtered populations — even though the pool only shrank ~18%. This is inherited faithfully from `build_dev_sample_v2.py`, per the amendment's explicit instruction not to reinvent the stratification. Full before/after lists: `results/phase_3/artifacts/dev_sample_v3_vs_v2.json`.

**A1-T4 — `weak_listing_signature` refinement.** Added to T3's classification (§4 below): flags `backward_missing` events where the ticker's earliest archive-wide trade session is later than the event's expected T-3 session.

**A1-T5 — pointer update.** `CLAUDE.md`'s standing dev-sample rule now names v3; v2 remains committed as the historical sample, not deleted. `docs/Open-Items-Register.md` logs the re-pin as a closed action.

---

## 4. Classify the 287 (T3, resumed with the A1-T4 refinement)

Precedence-ordered, one label per event, **0/287 unclassified** (well under the 30% / 86-event threshold):

| Label | n | % of 287 | Dominant bitmap |
|---|---|---|---|
| `backward_missing` | 215 | 74.91% | `0011111` (n=117 — only T-3/T-2 missing) |
| `calendar_residue` | 35 | 12.20% | `0011111` (n=14) |
| `forward_missing` | 26 | 9.06% | `1111011` (n=8 — only T+2 missing) |
| `both_sides` | 11 | 3.83% | scattered, no single dominant pattern (top 3 tied at n=2 each) |
| `archive_edge` | 0 | 0% | n/a — every cohort event's expected window falls inside the observed file1 `filtered_trades` session-date range (2019-12-30 .. 2025-01-06) |
| `unclassified` | 0 | 0% | n/a |

22 distinct bitmap patterns across the 287; the top 3 (`0011111`, `0111111`, `0001111`) account for 226/287 (79%) — a clear concentration, not diffuse spread. Chart: `results/phase_3/charts/01_missing_pattern_by_class.html`.

**T3a — weak within-archive delisting signature.** Of the 26 `forward_missing` events, **3** have their event day as the ticker's last-seen date anywhere in the archive across all of that ticker's own in-scope event windows. Verbatim scope caveat: absence of a ticker's data after an event is *not* proof of delisting — it may simply mean no later event for that ticker. Within-archive signature only, not externally confirmed.

**A1-T4 — weak within-archive listing signature.** Of the 215 `backward_missing` events, **173** have the ticker's earliest archive-wide trade session later than the event's expected T-3 session. Verbatim scope caveat: absence of pre-event data is *consistent with* late listing but is not proof — within an event-conditional archive it is indistinguishable from flank-collection loss without external reference data, which is out of scope. `PLBY_2021-02-16` is the illustrative exemplar: bitmap `0111111` (only T-3 missing), `weak_listing_signature=TRUE`, expected T-3 = 2021-02-10 — the SPAC merger (with MCAC) consummation date; the ticker began trading as PLBY on Nasdaq 2021-02-11. This is the amendment's stated exemplar, not a per-event external lookup performed on the cohort.

**T3c — cohort overlap.** Of the 287 (trades) and 386 (quotes) cohorts: **259 in both**, **28 trades-only**, **127 quotes-only**. Chart: `results/phase_3/charts/03_trades_quotes_cohort_overlap.html` (quotes-only events carry no trades-side label, shown as a distinct grey segment — they are `full_window` on trades, failing only on quotes).

**Temporal distribution.** Cohort events span all 60 months of the file1 population (2019-2024); no single month or edge period dominates the `event_day_only` share on inspection. Chart: `results/phase_3/charts/02_cohort_temporal_distribution.html`.

---

## 5. Escalation check table

| Criterion | Threshold | Observed | Result |
|---|---|---|---|
| `in_scope` guard ≠ 20,951 | any | 20,951 | pass |
| T1 cohort ≠ 287 / 386 | any | 287 / 386 | pass |
| Dev sample manifest missing/ambiguous | any | resolved via CLAUDE.md's standing pointer | pass |
| **Any dev event `coverage_class != 'full_window'`** | ≥ 1 | **15/50** | **triggered — hard stop, superseded by Amendment 1** |
| A1: headline metric sourced from dev tier | ≥ 1 | 0/7 candidates | pass |
| A1: v2 builder ambiguous | any | unambiguous | pass |
| A1: v3 event fails full_window+quotes_full_window | ≥ 1 | 0/50 | pass |
| A1/T3: write to data root, DB, or canonical view | any | none (only new `dev_v3` tables created) | pass |
| `unclassified` label > 30% of 287 | > 86 | 0 | pass |

---

## 6. Verification block

| Metric | Value | Source | Repro |
|---|---|---|---|
| Spine guard | 20,951 | `results/phase_3/artifacts/t1_cohort.json` | `.venv/Scripts/python.exe -m research.phase_3.t1_cohort` |
| Trades / quotes cohort | 287 / 386 | `results/phase_3/artifacts/t1_cohort.json` | same |
| Dev v2 not-full_window | 15/50 | `results/phase_3/artifacts/dev_sample_coverage.json` | `.venv/Scripts/python.exe -m research.phase_3.t2_dev_sample_check` |
| A1 prior-use scan | 0/7 hits | `results/phase_3/artifacts/a1_dev_usage_scan.json` | `.venv/Scripts/python.exe -m research.phase_3.a1_t1_dev_usage_scan` |
| Dev v3 build | 50/50 pass | `results/phase_3/artifacts/dev_sample_v3_build_summary.json` | `.venv/Scripts/python.exe -m research.phase_3.build_dev_sample_v3` |
| v2↔v3 overlap | 0/50 | `results/phase_3/artifacts/dev_sample_v3_vs_v2.json` | `.venv/Scripts/python.exe -m research.phase_3.a1_t3a_v3_vs_v2_overlap` |
| Classification labels | table in §4 | `results/phase_3/artifacts/classification_summary.json`, `.parquet` | `.venv/Scripts/python.exe -m research.phase_3.t3_classify` |

**Filter waterfall (cohort derivation):** `momentum_events` (23,268 raw) → `momentum_events_canonical` `in_scope=TRUE` (20,951) → `source_file='file1'` (15,763) → `coverage_class='event_day_only'` (287, the trades cohort) / `quotes_full_window=FALSE` (386, the quotes cohort).

**Environment note:** All Phase 3 scripts ran on the project `.venv` (duckdb 1.4.4, pandas 2.3.3, `pandas_market_calendars` 5.3.0, `exchange_calendars` 4.12) — same drift from the phase-1c pin (5.4.0/4.13.2) as Phase 2, still uncorrected, logged in `docs/Open-Items-Register.md`.

### Output files

| File | Status |
|---|---|
| `prompts/phase_3.md`, `prompts/phase_3_amendment_1.md` | committed |
| `config/phase_3.json`, `config/dev_sample_v3.json` | committed |
| `research/phase_3/*.py` (11 scripts) | committed |
| `results/phase_3/artifacts/*.json` | committed |
| `results/phase_3/artifacts/classification.parquet` | gitignored, regenerable |
| `results/phase_3/charts/01-03*.html` | committed |
| `CLAUDE.md`, `docs/Open-Items-Register.md` | updated |
| `filtered_trades_dev_v3`, `filtered_quotes_dev_v3` (DB tables) | created, not git-tracked (DuckDB file) |
| `results/phase_3/digest.json`, `REPORT.md` | committed |

### Commits (phase-2-approved..HEAD)

T0 branch/prompt/config · T1 guard+cohort · T2 ESCALATION · A1-T0 amendment · A1-T1/T2 safety scan + builder location · A1-T3 v3 build · A1-T3a v2↔v3 overlap · A1-T5 pointer update · T3 classification (+ bug fix) · T4 charts 01-03 · T5 digest+REPORT (this commit) · T6 register line (next).

---

## Approval Gate

Do not begin any follow-on work — including any `coverage_class` semantic change, any further dev-sample action, or any recollection scoping — until Cooper has reviewed results and given explicit approval.
