# Phase 1b — Universe Repair & Canonicalization — Report

**Branch:** `phase/1b` | **Baseline:** `phase-1-approved` | **Config hash:** `2d1fb57a` (`config/phase_1b.json`)

Covers the base prompt (`prompts/phase_1b.md`) and three amendments resolving escalations along the way: Amendment 1 (T1 suspect-class hard stop), Amendment 2 (T4b zero-row hard stop), Amendment 3 (T5b zero-trades hard stop). No recommendations below — description only, per the Evidence Standard.

---

## 1. Classification counts (T1a, post-rebuild)

The original 9-rule heuristic left 174/3,377 tickers (5.15%) in a `*_suspect` class, unresolvable by the advisory source (`symbol-properties-database.csv` — confirmed a generic broker contract-spec file with a single wildcard `usa,[*],equity` row, zero per-ticker equity rows for this universe). This triggered a hard stop (T1, commit `230b913`).

**Amendment 1** replaced the advisory-plus-heuristic approach with an authoritative pull from the Massive reference API (`/v3/reference/tickers`, 36,282 rows fetched, 100% of the 3,377-ticker universe matched). Vendor `type` is now the classification verdict; the heuristic is retained as a validation column only.

| Vendor type | Class | In scope | n |
|---|---|---|---|
| CS | common | yes | 2,717 |
| ADRC | common_adr | yes | 227 |
| WARRANT | warrant | no | 191 |
| PFD | preferred | no | 95 |
| ETF | fund_product | no | 91 |
| FUND | fund_product | no | 23 |
| SP ("Structured Product" — baby bonds, e.g. `APOpA`, `FpB`, `FpC`) | other | no | 13 |
| UNIT | unit | no | 13 |
| RIGHT | right | no | 7 |
| — | unresolved | no | 0 |

0 unresolved (T1-R4 gate re-check pass). Chart: `results/phase_1b/charts/02_instrument_classes.html`.

**Heuristic validation** (T1-R3a): 159/3,377 non-suspect disagreements (4.71%, under the 5% threshold but close to it). 94% of disagreements are the heuristic's catch-all `common` rule silently absorbing 114 `fund_product` and 27 `preferred` tickers it had no pattern for (e.g. all-caps-P preferred suffixes like `APOpA`, `RILYP`-style). **Ticker-reuse check** (T1-R3b): 0/3,366 conflicts (event dates vs. vendor active/delisted window).

---

## 2. Canonical spine verification (T2)

`momentum_events_canonical` (view, `src/data/canonical.py`) over the raw `momentum_events` table.

- **Row count:** exactly 23,268 (T2a — pass).
- **Folder-join ambiguity** (T2b): 0 events with multiple folder matches, 0 folders with multiple event matches (join key: `ticker, event_date_canonical, ROUND(momentum_pct,2)`).
- **No-folder coverage** (T2c): 0 momentum_events rows with no matching folder at all.

---

## 3. Flag summary

| Flag | n flagged | % of relevant population | Source |
|---|---|---|---|
| `flag_bad_denominator` (T3) | 8 / 23,268 | 0.034% | `prev_close < 0.01 OR momentum_pct >= 10000`; the 53,799,900% row (`SOLS`) confirmed caught |
| `flag_trades_mom_outlier` (T5a) | 105 / 20,907 | 0.50% | q=0.995 quantile regression, `log(momentum_pct) ~ log(n_trades_event_day)` |
| `flag_missing_event_day` (T5b → Amendment 3) | 150 / 21,057 | 0.71% | zero trades on the event's true calendar day; 142 `calendar_bug`, 8 `unknown` |
| `flag_window_calendar_bug` (Amendment 3, T5-R3) | 1,849 / 20,802 in-scope | 8.89% | T-3..T+3 window has session-shape damage from the same collector bug — **annotation, not a scope exclusion** |

Chart 01 (mechanism/bivariate flags vs. trades): `results/phase_1b/charts/01_trades_vs_momentum_flags.html`. Chart 05 (window damage by offset): `results/phase_1b/charts/05_calendar_damage_by_offset.html`.

### The root cause behind `flag_missing_event_day` / `flag_window_calendar_bug`

`data/collection_scripts/collect_massive_data.py`'s `get_trading_window()` built T-3..T+3 windows using `pandas.tseries.holiday.USFederalHolidayCalendar`, which disagrees with the actual NYSE/NASDAQ (XNYS) session calendar. Confirmed by direct spot-check: `MSTR` on 2024-11-11 (Veterans Day) has 2,747,522 rows tagged to that event, spanning 2024-11-06 through 2024-11-14, but **zero** on 2024-11-11 itself, despite being one of the most liquid tickers in the universe.

**Set A** (14 dates, 2020–2025, derived via pinned `pandas_market_calendars` XNYS, T5-R1): Columbus Day ×6, Veterans Day ×6 (2023 as the Friday-observed 11-10), the 2021 first Juneteenth observance, and the 2021-12-31 observed-New-Year's shift. **Set B** (7 dates): Good Friday ×6 plus the 2025-01-09 special closure. All 12 distinct dates behind the 142 `calendar_bug` events are confirmed within Set A (0 missing — T5-R1 cross-check pass).

**Blast radius** (T5-R3): 1,849/20,802 in-scope events (8.89%, well under the 3,000/~15% escalation threshold) have window-shape damage. Outer offsets (T-3=500, T+3=557) are entirely `missing_session` damage (a Set A date at the boundary shifts the whole window outward); inner offsets show a mix of `missing_session` and `short_window`, consistent with Set B dates landing mid-window. Corroboration sample (20 outer-offset `missing_session` events): 9/20 (45%) confirmed an extra T-4/T+4 session — the remainder trace to a second sub-mechanism (a Set B date consuming one of the collector's 3 stepping moves without extending reach, e.g. `GIII`/2020-04-07 with Good Friday 2020-04-10 at the collector's 3rd forward step), not a corroboration failure.

**Surprise:** 33 in-scope events anchored exactly on Columbus Day 2025 (2025-10-13) have trades on the anchor day — unlike the 142-event pattern — because `get_trading_window`'s `date_range` never includes a non-business-day center at all. Flagged `flag_window_calendar_bug=TRUE` distinctly (`anchor_on_set_a`), not root-caused further (out of Amendment 3's scope).

**Decision (Cooper):** no repair in Phase 1b — flag and quantify only. Targeted re-collection is Phase 1c, gated separately. `collect_massive_data.py` remains never-execute.

---

## 4. Re-ingestion table (T4)

Of the 409 parser-fix-recovered folders, 7 classify `common`/`common_adr`:

| Folder | Class | Trades rows ingested | Quotes rows ingested |
|---|---|---|---|
| `CIG.C_2020-06-22_451.45` | common_adr | 86,656 | 65,313 |
| `GTN.A_2023-11-02_33.62` | common | 569 | 3,388 |
| `GTN.A_2024-04-22_36.55` | common | 421 | 2,904 |
| `GTN.A_2024-05-02_33.09` | common | 745 | 1,576 |
| `GTN.A_2024-11-14_112.00` | common | 9,957 | 10,046 |
| `GTN.A_2024-11-15_38.37` | common | 10,137 | 8,557 |
| `GTN.A_2025-06-12_31.87` | common | 885 | **0** (`quotes.parquet` never existed on disk) |

Total: +109,370 `filtered_trades` rows, +91,784 `filtered_quotes` rows. The remaining 402 recovered folders (preferred/warrant/unit/right/other) recorded `out_of_scope_unigested` in `folder_inventory_v2.parquet` — no ingestion attempted.

`GTN.A_2025-06-12_31.87`'s 0 quotes rows triggered T4b's hard stop under the literal criterion (any 0-row folder post-ingest). **Amendment 2** resolved this: the event stays in scope; coverage becomes per-side (`trades_ingested`, `quotes_ingested` on the canonical view, replacing the single `folder_ingested` column), and missing quote coverage is a recorded fact, not an eligibility veto. Re-verified under the rewritten criterion (0-row only a stop when the source parquet existed): 7/7 pass.

**Universe-wide trades-only count** (T4-R2): 1,606 folders have a trades file but no quotes file (vs. ~1,540 expected from prior context; diff 66 exceeds the 50-event surprise threshold — noted, not investigated, per T4-R2a). By class: common=1,223, warrant=291, common_adr=44, fund_product=36, preferred=7, unit=4, right=1. By year: 2020=172, 2021=70, 2022=483, 2023=468, 2024=264, 2025=149.

**Dev v1 forensics** (T4d): confirmed `AHTpG` and `BHRpB` have 0 rows in `filtered_trades`/`filtered_quotes` but nonzero rows in the dev v1 tables (2,837/5,455 and 987/2,051) — dev v1 was materialized from a source other than the main tables. Root cause: `src/data/ingest.py`'s `load_filtered` still uses the pre-fix `[A-Z0-9]+` ticker pattern (the Phase 0c parser fix only touched `research/phase_0c/build_folder_inventory.py`, never the production ingest path) — the same root-cause class as the 409 recovered folders. No repair attempted; dev v1 stays retired.

---

## 5. Accounting waterfall (T6)

| Step | n dropped | n remaining |
|---|---|---|
| Start | — | 23,268 |
| − non-common instruments (excl. fund_product) | 1,897 | 21,371 |
| − fund_product | 307 | 21,064 |
| − bad-denominator | 7 | 21,057 |
| − bivariate outliers | 105 | 20,952 |
| − zero-trade events | 150 | 20,802 |
| − `flag_missing_event_day` (pending 1c repair) | 0 (same set as prior step) | 20,802 |
| **In-scope universe** | | **20,802** |

Matches the view's own `in_scope` count exactly. Terminal coverage split (Amendment 2): **both-sides ingested = 20,623**, **trades-only = 179**, **no folder = 0**. Sum = 20,802, residual = 0. 1,849 in-scope events carry `flag_window_calendar_bug` as an annotation (not a drop).

**Folder-side accounting:** 24,609 (24,200 + 409) = **23,268 matched-to-spine** (using Phase 1's reclassified count — includes the 5,911 false orphans, matched via `event_date` since raw `date` is structurally NULL) + **1,341 genuine orphans**. Residual = 0.

Chart: `results/phase_1b/charts/03_universe_waterfall.html`.

---

## 6. Dev v2 manifest + subset verification (T7)

Eligibility (Amendment 3): `in_scope AND trades_ingested AND quotes_ingested AND NOT flag_window_calendar_bug` → 18,787 eligible events. Stratified 5/decile, seed=42 → **50 events across all 10 deciles**. `filtered_trades_dev_v2` (8,282,847 rows) / `filtered_quotes_dev_v2` (5,959,286 rows) materialized from the main tables only via a join on `(ticker, event_date, ROUND(momentum_pct,2))`.

- **T7a subset verification:** 0/50 mismatches (dev row count == main-table row count, both tables).
- **T7b zero-row check:** 0/50 zero-row events.

Chart: `results/phase_1b/charts/04_dev_v2_coverage.html`.

---

## 7. Escalation check table

| Criterion | Threshold | Observed | Pass/Fail |
|---|---|---|---|
| Canonical spine row count | ≠ 23,268 | 23,268 | Pass |
| T1 suspect-class unresolved | > 2% | 5.15% → **Triggered**, resolved by Amendment 1 → 0% | Pass (post-amendment) |
| Classification disagreement (non-suspect) | > 5% | 4.71% | Pass |
| Folder-join multi-matches | > 25 | 0 | Pass |
| 53.8M% row not caught | any | caught | Pass |
| T4b: re-ingested folder 0 rows | any | `GTN.A_2025-06-12` → **Triggered**, resolved by Amendment 2 (per-side coverage) → 7/7 pass under rewritten criterion | Pass (post-amendment) |
| Bivariate flag rate | > 1.5% | 0.50% | Pass |
| Zero-event-day-trades | > 50 | 150 → **Triggered**, resolved by Amendment 3 (flagged, not repaired) | Pass (post-amendment) |
| T1-R1: 142 dates missing from Set A | any | 0 | Pass |
| T1-R3b: ticker-reuse conflicts | > 25 | 0 | Pass |
| T5-R3: `flag_window_calendar_bug` | > 3,000 | 1,849 (8.89%) | Pass |
| Waterfall residual (event + folder side) | ≠ 0 | 0 / 0 | Pass |
| T7a/b: dev v2 subset / zero-row | any | 0 / 0 | Pass |
| Recovered-folder in-scope count (T4, revised) | > 25 | 7 | Pass (no confirmation pause needed) |

---

## 8. Verification block

| Metric | Value | n | Source | Repro |
|---|---|---|---|---|
| Canonical spine row count | 23,268 | 23,268 | `momentum_events_canonical` | `python research/phase_1b/build_canonical_spine.py` |
| Vendor classification, 0 unresolved | 0 | 3,377 | `results/phase_1b/artifacts/instrument_classification.parquet` | `python research/phase_1b/rebuild_classification.py` |
| Bivariate flag rate | 0.50% | 20,907 | `results/phase_1b/artifacts/bivariate_outlier_flag_summary.json` | `python research/phase_1b/bivariate_outlier_flag.py` |
| Window calendar-bug blast radius | 8.89% | 20,802 | `results/phase_1b/artifacts/t5r3_window_damage_summary.json` | `python research/phase_1b/window_calendar_bug_quantification.py` |
| In-scope universe | 20,802 | 23,268 | `results/phase_1b/artifacts/t6_waterfall_summary.json` | `python research/phase_1b/build_waterfall.py` |
| Dev v2 subset match | 50/50 | 50 | `results/phase_1b/artifacts/t7_dev_sample_v2_summary.json` | `python research/phase_1b/build_dev_sample_v2.py` |

**Filter waterfall:** see §5 above (full step-by-step table).

Config hash: `2d1fb57a` (`config/phase_1b.json`, seed=42; `pandas_market_calendars` 5.4.0 / `exchange_calendars` 4.13.2, XNYS).

---

## 9. Output file table

| File | Description | Status |
|---|---|---|
| `config/phase_1b.json` | seed, thresholds, classification rules, session calendar pin | [x] |
| `src/data/canonical.py` | `momentum_events_canonical` view (staged t2/t5/t6) | [x] |
| `results/phase_1b/artifacts/instrument_classification.parquet` | vendor-verdict classification | [x] |
| `results/phase_1b/artifacts/event_flags.parquet` | per-event flags + n_trades_event_day | [x] |
| `results/phase_1b/artifacts/folder_inventory_v2.parquet` | 24,609 folders, match/ingestion/scope status | [x] |
| `config/dev_sample_v2.json` | dev sample v2 manifest | [x] |
| `results/phase_1b/charts/01_trades_vs_momentum_flags.html` | per contract | [x] |
| `results/phase_1b/charts/02_instrument_classes.html` | per contract | [x] |
| `results/phase_1b/charts/03_universe_waterfall.html` | per contract | [x] |
| `results/phase_1b/charts/04_dev_v2_coverage.html` | per contract | [x] |
| `results/phase_1b/charts/05_calendar_damage_by_offset.html` | Amendment 3 addition | [x] |
| `results/phase_1b/artifacts/ticker_reference_snapshot.parquet` | Amendment 1 — vendor reference records | [x] |
| `results/phase_1b/digest.json` | validated, 65 lines | [x] |
| `results/phase_1b/REPORT.md` | this file | [x] |

**Not committed:** `data/Schema.md`'s T8 addendum (Known Gaps section) was written to disk exactly as instructed, but `/data/` is excluded by `.gitignore` project-wide and `data/Schema.md` has never been tracked in git history (confirmed via `git log --all`). Committing it would be the first-ever exception to that standing rule — not made unilaterally. The edit is live on disk.

---

## 10. Commit list

27 commits on `phase/1b` from `phase-1-approved`. Full list:

```
01f2a38 prompt: Phase 1b T0 - branch cut from master (phase-1-approved), prompt and config
230b913 phase-1b T1: ESCALATION - suspect-class tickers 5.15% exceeds 2% threshold
12e7df6 prompt: Phase 1b Amendment 1 - T1 escalation resolution via Massive reference API
7b8e9d7 chore: gitignore local secrets dir for Phase 1b Amendment 1 API key
f2bd9ca phase-1b T1-R1: bulk reference snapshot from Massive API
cbeef5f phase-1b T1-R3: rebuild classification with vendor type as verdict
b663a96 phase-1b T1-R4: T1 gate re-check passes - resuming at T2
a46342f phase-1b T2: momentum_events_canonical view - row count exact, 0 ambiguity
fec6f49 phase-1b T3: mechanism outlier flag - 8/23,268 flagged, 53.8M% row caught
633ddf4 phase-1b T4a: pre-ingestion list, 7 in-scope recovered folders
0b3635a phase-1b T4b: ESCALATION - GTN.A_2025-06-12_31.87 has 0 rows in filtered_quotes
c5f4800 prompt: Phase 1b Amendment 2 - T4b escalation resolution, per-side coverage
652c953 phase-1b T4-R1: split folder_ingested into trades_ingested/quotes_ingested
2a26eea phase-1b T4c/T4-R2: folder_inventory_v2 - scope status + trades-only headline
ab34f8d phase-1b T4d/T4-R3: dev v1 forensics + rewritten escalation re-verification
5a7d612 phase-1b T5: ESCALATION - 150 zero-event-day-trades events exceeds 50
81afeb2 prompt: Phase 1b Amendment 3 - T5b resolution, session calendar pinned
cefba8e phase-1b T5-R1: calendar mismatch derivation - Set A (14) / Set B (7)
ebb1474 phase-1b T5-R2: zero-trades cause annotation - 142 calendar_bug, 8 unknown
6e1dde9 phase-1b T5-R3: window calendar bug blast radius - 1,849/20,802 (8.89%)
8cab7ce phase-1b T5-R4: Amendment 3 gate re-check passes - resuming at T6
4a6d597 phase-1b T6: in_scope finalized, waterfall balances to 0 residual
ec411d7 phase-1b T6a: chart 03 - universe waterfall
5d28b8b phase-1b T7: dev sample v2 - 50 events, 10 deciles, subset verified
88d4fd8 phase-1b T7c: chart 04 - dev v2 coverage
eefa3b5 phase-1b T8: standing docs update - CLAUDE.md universe rules (verbatim)
39939a1 phase-1b: charts 01 (trades vs momentum flags) and 02 (instrument classes)
```

(T9 digest/report commit follows this file.)

---

## Approval Gate

Do not begin Phase 2 or any follow-on work until Cooper has reviewed results and given explicit approval. This gate also constitutes approval of the Phase 1c scope draft (targeted re-collection of the 142 `flag_missing_event_day` events and the 1,849 `flag_window_calendar_bug`-damaged windows) as next work, per Amendment 3.
