# Phase 1 — Filter Forensics — Report

**Branch:** `phase/1` | **Baseline:** `phase-0c-approved` | **Config hash:** `b35ce8ec` (`config/phase_1.json`)

No recommendations below — description only, per the Evidence Standard. Every claim cites its chart or artifact.

---

## 0. T0 docs housekeeping note

`docs/Agent_Prompt_Standard.md` (v1.3) and `docs/Mom-DB-Strategy-Research-Program.md` are now committed at their canonical paths (commit `fa4a86d`). `docs/Agent_Prompt_Standard (1).md` (the v1.1/v1.2 copy) was left untracked as instructed, and was still present on disk immediately after that commit — flagged there as a deletion candidate. By T7 (this report), the file is **no longer present on disk at all**. This phase never wrote to `docs/` after T0, so the removal happened outside this phase's actions — noted here rather than silently reconciled. See `docs/Research-Library-Map.md`'s `docs/` section for the same note.

---

## 1. Hardcoded parameter table (T1e)

All line numbers refer to `data/collection_scripts/filter_events_power_law.py`.

| Line(s) | Literal | Effect |
|---|---|---|
| `:7` | `base_dir = r"d:\Mom. DB started 11-21-25\data\momentum_events"` | Selects which two files are read (by filename) |
| `:8` | `"full_2020_2024_momentum_scan_20251122_000515.parquet"` | file1 identity |
| `:9` | `"momentum_scan_2025.parquet"` | file2 identity |
| `:10` | `"filtered_events_power_law_q05.parquet"` | Output filename |
| `:15-16` | `if 'volume' in df1.columns: rename to 'event_volume'` | Only cross-file schema reconciliation performed; does not cover `date`/`event_date` |
| `:27` | `dropna(subset=['momentum_pct','event_volume'])` | Row-eligibility filter |
| `:28` | `event_volume > 0` | Row-eligibility filter |
| `:29` | `momentum_pct > 0` | Row-eligibility filter (comment: required for log) |
| `:31-32` | `log10` transform on `momentum_pct`, `event_volume` | Defines the model's variable space |
| `:35` | `quantile(0.995)` | Training-set upper trim (top 0.5% momentum excluded from fit only) |
| `:42` | formula `'log_vol ~ log_mom'` | Model spec (dependent ~ regressor) |
| `:43` | `q=0.05` | Quantile level — the boundary and its ~5% conditional rejection rate |
| `:62` | `log_vol > log_vol_threshold` | The keep/drop decision |
| `:75` | `output_cols` construction | Which columns survive to `momentum_events` |
| `:78, 83` | `.to_parquet(...)`, `.to_csv(...)` | Output format/location |

Full narrative: `results/phase_1/filter_spec.md` (T1).

---

## 2. `momentum_pct` formula

**`momentum_pct = (high − prev_close) / prev_close × 100`** — a prior-close-to-intraday-high measure, not gap-at-open or close-to-close.

Not code-confirmed: the filter script only reads `momentum_pct`, never computes it (`filter_events_power_law.py:27,29,31`), and neither does `collect_massive_data.py:128`, which also only reads it. The generating scanner script is absent from this repository. Determined empirically against `file1`: `corr(momentum_pct, (high−prev_close)/prev_close×100) = 0.9997` (n=18,658); exact row match on `AA 2020-03-24` (`prev_close=5.67, high=7.48 → 31.92`, matching stored `momentum_pct=31.92`). Full candidate-formula comparison table: `results/phase_1/filter_spec.md` T1c.

---

## 3. NULL-date origin classification

**Classification: (b) — introduced by the filter script.**

`file2` (`momentum_scan_2025.parquet`) has no `date` column at all — only `event_date`. The script's `pd.concat([df1,df2], ignore_index=True)` (`:22`) is a column-union concat; its only schema reconciliation (`volume`→`event_volume`, `:15-16`) doesn't cover `date`/`event_date`. Every file2-sourced row therefore gets `date=NaN` structurally, not from any NULL value present in either source file.

**Evidence** (`artifacts/null_date_forensics.json`): `date IS NULL` and `event_date IS NOT NULL` are the *identical* 5,911 rows (100% overlap); `date IS NOT NULL` and `event_date IS NULL` are the identical 17,357 rows (100%). Perfect, disjoint partition. Row arithmetic: 5,950 raw file2 rows → 5,911 land in the final NULL-date set (39 dropped by the q05 filter, same mechanism as any other row).

**0c's 114 literal-"None" folders** (`none_date_lookup.json`) cross-referenced against the 5,911 NULL-date rows: **subset relationship** — 113 matched a single NULL-date row, 1 matched multiple NULL-date rows ambiguously, 0 matched a valid-date row. 114/5,911 = 1.93%.

**Distribution comparison** (chart 01, n=17,357 dated / n=5,911 NULL-date): medians close (42.60 vs 44.41) but NULL-date group's `momentum_pct` max is 53,799,900 vs the dated group's 48,557.72 — a ~1,100× outlier that pulls its mean three orders of magnitude above its own median. See `results/phase_1/charts/01_momentum_pct_by_date_status.html`.

---

## 4. Refit comparison

Read-only re-implementation (`research/phase_1/refit_boundary.py`) of the fit against the same two scan inputs:

| | Value |
|---|---|
| Raw concat rows | 24,610 |
| Cleaned (`calc_df`) rows | 24,501 |
| Training set (≤99.5th pct momentum) | 24,378 |
| Re-derived kept | 23,268 |
| `momentum_events` table rows | 23,268 |
| Overlap, both directions | 23,268 / 23,268 (**100%**) |
| Fitted params | Intercept=2.1261, log_mom=0.5846 |

Join key: `(ticker, COALESCE(date, event_date), ROUND(momentum_pct, 2))` — coalesced because plain `date` would silently exclude the 25% of rows sourced from file2 (see §3). Threshold (config): 0.95 — met with large margin. Source: `results/phase_1/artifacts/refit_comparison.json`. Chart: `results/phase_1/charts/02_q05_boundary.html` (all 24,501 cleaned rows shown, under the 50,000 cap, no subsampling needed).

**No escalation** — schema check also passed: `momentum_events`' 21 columns match the filter output's 21 columns exactly, no missing/extra/mistyped fields.

---

## 5. Orphan membership fractions

7,252 orphan folders (0c inventory) reclassified in `research/phase_1/orphan_drift.py` → `artifacts/orphan_summary.json`, `artifacts/orphan_classification.parquet` (gitignored, regenerable).

| Class | n | % of 7,252 |
|---|---|---|
| **False orphan** (date-bug artifact — same event as a NULL-date `momentum_events` row, misclassified by 0c's date-only join) | 5,911 | 81.51% |
| **Genuine orphan** | 1,341 | 18.49% |

Membership tests:
- **(i) raw scan inputs:** 100% of orphans (7,252/7,252) match a raw scan-input row (1,303 file1, 5,949 file2) — none are absent from the scan entirely.
- **(ii) T2 re-derived kept set:** by construction, identical to momentum_events membership (§4's 100% overlap) — the 5,911 false orphans match; the 1,341 genuine orphans match neither.
- **(iii) other `filtered_events_*.parquet` files:** none exist beyond the one file that populates `momentum_events` (T1a directory listing) — no independent third source to test against.

**Boundary test, genuine orphans only** (the population that actually bears on "residue of a looser filter run"): 1,232/1,341 (91.9%) fall **below** the current q05 boundary — ordinary filter rejects with a leftover folder. 109/1,341 have zero/invalid volume in the scan input (would fail the `event_volume > 0` prefilter, `:28`, regardless — boundary undefined). **0 genuine orphans sit above the boundary** — no evidence of filter drift. See `results/phase_1/charts/03_orphans_vs_boundary.html`.

---

## 6. T5 tables

### T5a — 409 parser-fix-recovered folders (194 dot-ticker + 215 lowercase-suffix)

| Table | n with any ticker rows | n with exact event-date rows |
|---|---|---|
| `filtered_trades` | 0 / 409 (0.0%) | 0 / 409 (0.0%) |
| `filtered_quotes` | 0 / 409 (0.0%) | 0 / 409 (0.0%) |

Verified not a query artifact: `filtered_trades`' entire 3,272-distinct-ticker universe contains **zero** tickers with a `.` or a lowercase character. Documented finding, not an escalation, per the phase prompt. Source: `results/phase_1/artifacts/ingestion_spotcheck.json` (`t5a_recovered_folders`).

### T5b — 50 dev-sample events, `filtered_trades_dev` / `filtered_quotes_dev` row counts

All 50 events have non-zero rows in both tables — **no escalation**.

| ticker | date | momentum_pct | n_trades | n_quotes |
|---|---|---|---|---|
| AHTpG | 2020-03-19 | 54.59 | 2,837 | 5,455 |
| AIFF | 2024-10-16 | 85.94 | 66,648 | 36,199 |
| AIHS | 2023-12-05 | 70.0 | 1,697 | 226,494 |
| AIMD | 2023-03-16 | 44.09 | 210,571 | 112,963 |
| AIRE | 2024-12-19 | 33.93 | 9,410 | 7,368 |
| AIRG | 2021-01-19 | 42.45 | 41,994 | 38,268 |
| AISP | 2024-03-13 | 33.07 | 177,521 | 157,438 |
| AIXI | 2024-09-24 | 31.35 | 14,704 | 14,617 |
| ALAR | 2023-08-28 | 36.75 | 6,550 | 9,186 |
| ALLR | 2024-05-02 | 152.55 | 691,579 | 300,045 |
| BFRG | 2023-03-03 | 47.99 | 46,373 | 28,691 |
| BGLC | 2024-07-24 | 31.31 | 3,627 | 5,244 |
| BHAT | 2020-06-16 | 32.0 | 65,523 | 40,977 |
| BHRpB | 2020-03-19 | 58.61 | 987 | 2,051 |
| BIIB | 2020-11-04 | 47.33 | 475,023 | 291,894 |
| BJDX | 2023-07-07 | 86.83 | 72,649 | 39,131 |
| BLBX | 2023-03-01 | 37.25 | 79,726 | 42,446 |
| BLRX | 2020-10-30 | 109.46 | 828,233 | 541,214 |
| BMEA | 2022-05-17 | 40.46 | 25,546 | 45,833 |
| BMR | 2023-04-17 | 35.21 | 2,241 | 3,439 |
| EQR | 2020-11-09 | 30.86 | 275,430 | 338,100 |
| EVOK | 2021-02-09 | 50.0 | 52,386 | 58,925 |
| FATBB | 2023-05-04 | 45.06 | 1,152 | 4,295 |
| FEBO | 2024-09-26 | 32.37 | 7,296 | 5,683 |
| FENG | 2024-05-30 | 42.54 | 9,218 | 8,707 |
| FG | 2022-12-01 | 162.22 | 37,230 | 15,864 |
| FNKO | 2023-11-03 | 33.56 | 73,442 | 128,268 |
| FRGE | 2022-04-26 | 56.43 | 170,899 | 131,858 |
| FRSX | 2024-12-20 | 38.04 | 103,238 | 116,050 |
| GLMD | 2022-12-21 | 77.42 | 5,165 | 4,769 |
| RILYP | 2024-08-22 | 41.69 | 6,276 | 7,527 |
| RNXT | 2021-11-10 | 131.24 | 730,967 | 262,612 |
| RNXT | 2024-11-22 | 30.57 | 4,254 | 3,626 |
| ROKU | 2023-11-02 | 32.53 | 1,048,411 | 1,406,485 |
| RSVRW | 2024-09-30 | 55.76 | 134 | 968 |
| RUM | 2024-01-23 | 43.56 | 888,972 | 1,069,451 |
| RVYL | 2024-11-25 | 58.68 | 6,811 | 8,665 |
| SABR | 2020-03-25 | 37.39 | 446,476 | 523,029 |
| SBFM | 2024-04-16 | 35.84 | 271,372 | 119,686 |
| SGBX | 2020-10-16 | 89.6 | 268,526 | 195,381 |
| TH | 2022-07-08 | 31.74 | 173,972 | 189,189 |
| TIRX | 2023-10-12 | 46.85 | 13,089 | 11,686 |
| TIVC | 2023-06-27 | 117.28 | 147,528 | 78,671 |
| TLSIW | 2024-02-20 | 36.37 | 124 | 600 |
| TMCI | 2024-05-14 | 34.22 | 137,600 | 141,245 |
| TMDX | 2022-05-04 | 41.15 | 66,544 | 77,854 |
| TOI | 2023-09-11 | 31.5 | 7,941 | 6,750 |
| TPST | 2022-04-27 | 69.07 | 46,690 | 25,717 |
| TPST | 2023-11-09 | 53.9 | 288,501 | 208,162 |
| TRUG | 2024-12-26 | 76.57 | 85,405 | 53,511 |

Source: `results/phase_1/artifacts/ingestion_spotcheck.json` (`t5b_dev_sample`).

---

## 7. Escalation check table

| Criterion | Threshold | Observed | Pass/Fail |
|---|---|---|---|
| T0: canonical docs absent, or standard header not v1.3 | either file | `docs/Agent_Prompt_Standard.md` absent at exact path (only untracked v1.1/v1.2 `(1).md` copy) | **Triggered → hard stop, then resolved** — Cooper placed both files; re-verified v1.3 at exact path, docs committed, CLAUDE.md updated |
| T1: `filter_events_power_law.py` missing/unreadable | — | present, 87 lines, read in full | Pass |
| T2: `momentum_events` schema vs script write logic | any missing/extra/mistyped column | 21/21 columns match exactly | Pass |
| T2: refit kept-set overlap | < 0.95 either direction | 1.0 both directions | Pass |
| T5b: any dev-sample event with zero rows | > 0 events | 0 of 50 | Pass |

**Documented findings, not hard stops** (per phase prompt): scan inputs present (T2 fallback not engaged); NULL-date origin classified (b) with full evidence (§3); 409/409 parser-fix-recovered folders absent from `filtered_trades`/`filtered_quotes` (§6, T5a).

---

## 8. Verification block

| Metric | Value | n | Source | Repro |
|---|---|---|---|---|
| momentum_events total | 23,268 | 23,268 | `data/duckdb/main.duckdb::momentum_events` | `duckdb.connect('data/duckdb/main.duckdb', read_only=True).execute('SELECT COUNT(*) FROM momentum_events')` |
| NULL-date rows | 5,911 | 5,911 | `momentum_events.date IS NULL` | `SELECT COUNT(*) FROM momentum_events WHERE date IS NULL` |
| Dated rows | 17,357 | 17,357 | `momentum_events.date IS NOT NULL` | `SELECT COUNT(*) FROM momentum_events WHERE date IS NOT NULL` |
| Refit kept count | 23,268 | 24,501 (calc_df) | `research/phase_1/refit_boundary.py` | `python research/phase_1/refit_boundary.py` |
| Refit/momentum_events overlap | 100% both dir. | 23,268 | `research/phase_1/refit_boundary.py` | `python research/phase_1/refit_boundary.py` |
| Orphans total | 7,252 | 7,252 | `results/phase_0c/artifacts/join_reconciliation_detail.json::t2c_results, class='orphan'` | `python research/phase_1/orphan_drift.py` |
| False orphans (date bug) | 5,911 | 7,252 | `research/phase_1/orphan_drift.py` | `python research/phase_1/orphan_drift.py` |
| Genuine orphans | 1,341 | 7,252 | `research/phase_1/orphan_drift.py` | `python research/phase_1/orphan_drift.py` |
| 409-folder DB presence | 0/409 both tables | 409 | `research/phase_1/ingestion_spotcheck.py` | `python research/phase_1/ingestion_spotcheck.py` |
| Dev-sample coverage | 50/50 nonzero | 50 | `research/phase_1/dev_sample_spotcheck.py` | `python research/phase_1/dev_sample_spotcheck.py` |

**Filter waterfall** (`filter_events_power_law.py`, re-derived read-only):

| Step | Rows in | Rows out | Dropped | Why |
|---|---|---|---|---|
| Raw concat (file1 18,660 + file2 5,950) | — | 24,610 | — | `pd.concat`, `:22` |
| `dropna`/`>0` cleaning | 24,610 | 24,501 | 109 | `event_volume<=0` in file1, `:27-29` |
| q=0.05 boundary filter | 24,501 | 23,268 | 1,233 | `log_vol > log_vol_threshold`, `:62` |

Config hash: `b35ce8ec` (`config/phase_1.json`, seed=42, overlap_threshold=0.95, chart_subsample_cap=50000).

---

## 9. Output file table

| File | Description | Status |
|---|---|---|
| `config/phase_1.json` | overlap threshold (0.95), chart subsample cap (50,000), seed (42), input paths | [x] |
| `results/phase_1/filter_spec.md` | line-cited filter spec (T1) | [x] |
| `results/phase_1/artifacts/scan_input_inventory.json` | script inputs, existence, row counts, columns | [x] |
| `results/phase_1/artifacts/refit_comparison.json` | refit vs momentum_events comparison | [x] |
| `results/phase_1/artifacts/null_date_forensics.json` | origin classification + evidence | [x] |
| `results/phase_1/artifacts/orphan_classification.parquet` | per-orphan membership flags (gitignored, regenerable) | [x] |
| `results/phase_1/artifacts/orphan_summary.json` | orphan fractions by class | [x] |
| `results/phase_1/artifacts/ingestion_spotcheck.json` | 409-folder presence + 50 dev-event row counts | [x] |
| `results/phase_1/charts/01_momentum_pct_by_date_status.html` | per contract | [x] |
| `results/phase_1/charts/02_q05_boundary.html` | per contract | [x] |
| `results/phase_1/charts/03_orphans_vs_boundary.html` | per contract | [x] |
| `results/phase_1/digest.json` | machine-readable digest (§11), validated | [x] |
| `results/phase_1/REPORT.md` | this file | [x] |

---

## 10. Commit list

```
ec56a45 prompt: Phase 1 T0 - branch cut, prompt and config committed
fa4a86d phase-1 T0: commit canonical docs, update CLAUDE.md pointers
a62c24d phase-1 T1: script forensics - filter_spec.md and scan input inventory
7aafaf7 phase-1 T2: read-only refit and comparison against momentum_events
eaf594b phase-1 T3: NULL-date origin classification (b) - introduced by filter script
6a2367d phase-1 T4: orphan drift test - most orphans are a date-bug artifact, not drift
eee576d phase-1 T5: DB coverage spot-check - 409 recovered folders and 50 dev events
663d2e7 phase-1 T6: chart contract - 01 NULL-date ECDF, 02 q05 boundary, 03 orphans
```
(T7 commit — digest, report, map — follows this file.)

---

## Approval Gate

Do not begin Phase 2 or any follow-on work until Cooper has reviewed results and given explicit approval.
