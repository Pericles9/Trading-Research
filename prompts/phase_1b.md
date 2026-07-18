# Phase 1b — Universe Repair & Canonicalization

**Date:** 2026-07-17
**Baseline:** Phase 1 — filter forensics complete. Established: 23,268 events in `momentum_events`; 5,911 NULL-date rows caused by the file2 `date`/`event_date` schema split (filter script concat bug, confirmed); 7,252 folder-side orphans of which 5,911 are false orphans (date bug) and 1,341 are genuine filter rejects with folders on disk; 409 folders recovered by the widened ticker regex have zero rows in `filtered_trades`/`filtered_quotes`; `momentum_pct` max of 53,799,900% in the file2 group with `prev_close` min of 0.0.
**Objective:** Build the canonical event spine, classify instruments, scope the universe to common stock, flag outliers, repair the small ingestion gap that remains in scope, and re-pin the dev sample — so Phase 2 computes statistics on a defined universe instead of a contaminated table.
**Primary success metric:** `momentum_events_canonical` exists with exactly 23,268 rows, every downstream flag populated, universe accounting waterfall balances to zero unexplained residual, and dev sample v2 verifies as a strict subset of the main tables.

---

**Context:**
- This is a repair/canonicalization phase. No alpha work, no markouts, no signal features.
- All decisions below were made by Cooper at the Phase 1 gate. The agent implements; it does not re-litigate thresholds. Any threshold that seems wrong → escalate, do not adjust.
- `symbol-properties-database.csv` is **Unknown provenance (quarantined)**. It may be read in this phase for one purpose only: as an **advisory cross-check** on instrument classification (T1). It is never load-bearing. Disagreements are reported, not resolved by preferring it.
- The Phase 0 dev tables (`filtered_trades_dev`/`filtered_quotes_dev`) are known-bad: they contain rows for tickers that have zero rows in the main tables (AHTpG, BHRpB), so they were not derived from the main tables. They are retired by this phase. Do not use them for anything.
- Writes to `filtered_trades`/`filtered_quotes` are permitted **only** in T4 (re-ingestion of classified-common recovered folders) and only via the existing ingest path. No other table mutations anywhere in this phase.
- All config values live in `config/phase_1b.json`. No magic numbers in code.

---

## Decisions Being Implemented (Cooper, Phase 1 gate — for reference, not re-derivation)

| # | Decision |
|---|---|
| D1 | Canonical date = `COALESCE(date, event_date)`. Raw `momentum_events` is never modified. |
| D2 | Universe membership = join to canonical spine, `in_scope = TRUE`. No aggregate over tick tables without it. |
| D3 | The 409 recovered folders: resolved via D4. Classified-common members get re-ingested; the rest are out of scope and stay unigested. |
| D4 | Instrument scope = **common stock only**. In: all common share classes (A/B/C, incl. FATBB-style), ADRs. Out: preferreds, warrants, rights, units. |
| D5 | Outliers are **flagged, never deleted**; canonical view excludes flagged rows by default. Two flags: mechanism (`prev_close < 0.01` OR `momentum_pct >= 10000`) and bivariate (above a q=0.995 quantile regression of log momentum on log event-day trade count). |

---

## Tasks

- [ ] **T0 — Branch and commit prompt**
  Cut `phase/1b` from main. Commit `prompts/phase_1b.md` and `config/phase_1b.json` before any other work.

- [ ] **T1 — Instrument classification**
  Classify every distinct ticker appearing in (a) `momentum_events` and (b) the folder inventory (24,200 + 409 recovered), using this rule set, applied in order, first match wins:

  | Priority | Pattern | Class |
  |---|---|---|
  | 1 | ticker contains `.WS` segment (e.g., `ACHR.WS`, `NE.WS.A`) | warrant |
  | 2 | ticker matches `[A-Z]+p[A-Z]?$` (lowercase `p` notation, e.g., `AHTpG`) | preferred |
  | 3 | ticker ends `.U` | unit |
  | 4 | ticker ends `.R` | right |
  | 5 | ticker ends `.A`/`.B`/`.C` (no `.WS` segment) | common_class_share |
  | 6 | 5-letter all-caps ticker ending in `W` | warrant_suspect |
  | 7 | 5-letter all-caps ticker ending in `U` | unit_suspect |
  | 8 | 5-letter all-caps ticker ending in `R` | right_suspect |
  | 9 | anything else | common |

  Rules 6–8 are *suspect* classes, not verdicts — a 5-letter ticker ending in W can be common (rule collisions exist). For every ticker in a suspect class: cross-check against `symbol-properties-database.csv` (advisory). If symbol-properties resolves it, record `resolved_by = symbol_properties_advisory`; if it does not appear there or disagrees ambiguously, class stays `*_suspect` and the ticker goes on the escalation list in the report.
  Also cross-check **all** non-suspect classifications against symbol-properties where the ticker appears; record the disagreement rate.
  Write `results/phase_1b/artifacts/instrument_classification.parquet` (ticker, class, rule_hit, resolved_by, symbol_properties_class, agrees).
  - [ ] T1a — Classification counts table (class × source: momentum_events / folder-only) with n
  - [ ] T1b — Commit

- [ ] **T2 — Canonical spine**
  Create `momentum_events_canonical` as a **view** over the raw table (raw table untouched), with columns:
  `ticker, event_date_canonical (COALESCE(date, event_date)), momentum_pct, source_file ('file1'|'file2'), instrument_class, flag_bad_denominator, flag_trades_mom_outlier (NULL until T5), has_folder, folder_ingested, in_scope (NULL until T6)`.
  View definition lives in `src/data/canonical.py` (or `.sql`) — this is a deliberate, instructed promotion to `src/`.
  - [ ] T2a — Row count check: exactly 23,268. Any other number → escalate.
  - [ ] T2b — Folder-join ambiguity check: join key `(ticker, event_date_canonical, ROUND(momentum_pct,2))` against the folder inventory. Count events with multiple folder matches and folders with multiple event matches. Report both with n.
  - [ ] T2c — Event-side coverage count: events with **no** matching folder at all, by instrument class. Headline number only — the deep-dive stays in Phase 4.
  - [ ] T2d — Commit

- [ ] **T3 — Mechanism outlier flag**
  `flag_bad_denominator = (prev_close < 0.01) OR (momentum_pct >= 10000)` (thresholds from config). Report count flagged, split by source_file, with the top 10 flagged rows (ticker, date, prev_close, momentum_pct) as a table.
  - [ ] T3a — Confirm the 53,799,900% row is caught; if it is not caught by this rule, escalate rather than widening the rule.
  - [ ] T3b — Commit

- [ ] **T4 — Re-ingest in-scope recovered folders**
  From the 409 recovered folders: select those whose ticker classifies as `common` or `common_class_share` in T1. Expected count: ~10 or fewer. Ingest their `trades.parquet`/`quotes.parquet` into the main tables via the existing ingest path (`src/data/ingest.py` mechanics).
  - [ ] T4a — Commit **before** the ingestion run
  - [ ] T4b — Post-ingest verification: every re-ingested folder now has > 0 rows in both tables for its exact event window; post per-folder row counts
  - [ ] T4c — The remaining recovered folders (preferred/warrant/unit/right) are recorded as `out_of_scope_unigested` in the folder inventory artifact. No ingestion for them.
  - [ ] T4d — One forensic query for the record: confirm the Phase 0 dev tables contain rows for ≥ 1 ticker with zero main-table rows, and record in the Decisions Log that dev v1 was built from a source other than the main tables. No repair of dev v1 — it is retired, not fixed.
  - [ ] T4e — Commit

- [ ] **T5 — Bivariate outlier flag (trades × momentum)**
  For every event with `instrument_class IN ('common','common_class_share')` and `flag_bad_denominator = FALSE` and an ingested folder: compute `n_trades_event_day` (trade count in `filtered_trades` for that ticker on `event_date_canonical`, universe-join per D2).
  Fit quantile regression, q = **0.995** (config), of `log(momentum_pct)` on `log(n_trades_event_day)` — same machinery as the q05 filter, upper tail. `flag_trades_mom_outlier = TRUE` for events above the fitted line.
  - [ ] T5a — Report count flagged with n and the flagged share as % of the fit population. Design expectation ≈ 0.5%; if > 1.5%, escalate.
  - [ ] T5b — Events in scope-eligible classes with an ingested folder but **zero** event-day trades: count them, list them, flag as `flag_zero_event_day_trades`. If > 50, escalate.
  - [ ] T5c — Chart 01 per the Chart Contract
  - [ ] T5d — Commit

- [ ] **T6 — Finalize `in_scope` and the accounting waterfall**
  `in_scope = instrument_class IN ('common','common_class_share') AND NOT flag_bad_denominator AND NOT flag_trades_mom_outlier AND NOT flag_zero_event_day_trades`.
  Produce the waterfall, every step with n, summing exactly:
  23,268 → minus non-common instruments → minus bad-denominator → minus bivariate outliers → minus zero-trade events → **in-scope universe** → split into (folder ingested / folder not ingested / no folder).
  Separately, folder-side: 24,200 + 409 = matched-to-spine + 1,341 genuine orphans + any residual. **Residual must be 0 or escalate.**
  - [ ] T6a — Chart 03 per the Chart Contract
  - [ ] T6b — Commit

- [ ] **T7 — Dev sample v2**
  Draw 50 events from `in_scope = TRUE AND folder_ingested = TRUE`, stratified 5 per `momentum_pct` decile (deciles computed on that same population), seed = 42 (config). Write the manifest to `config/dev_sample_v2.json` (ticker, date, momentum_pct, decile).
  Materialize `filtered_trades_dev_v2` / `filtered_quotes_dev_v2` **from the main DuckDB tables** — never from parquet files — so the subset property holds by construction.
  - [ ] T7a — Subset verification: for each of the 50 events, dev row count == main-table row count for the same (ticker, window). Any mismatch → escalate.
  - [ ] T7b — Zero-row check: no dev event with 0 trades or 0 quotes. Any → escalate.
  - [ ] T7c — Chart 04 per the Chart Contract
  - [ ] T7d — Commit

- [ ] **T8 — Standing docs update (verbatim, no editorial changes)**
  Append to `CLAUDE.md` exactly:

  > **Universe rules (Phase 1b, Cooper-approved):**
  > - Universe membership = inner join to `momentum_events_canonical` WHERE `in_scope = TRUE`. Never aggregate `filtered_trades`/`filtered_quotes` without this join — the tables physically contain out-of-universe rows (1,341 orphan-folder events and non-common instruments).
  > - Canonical event date = `event_date_canonical`. Never use raw `momentum_events.date` (structurally NULL for all file2 rows).
  > - Instrument scope: common stock only (all share classes, ADRs). Preferreds, warrants, rights, units are out of scope.
  > - Outliers are flags, never deletions. Default exclusion happens in the canonical view. Changing a flag definition is a Cooper decision.
  > - Dev sample = v2 (`config/dev_sample_v2.json`, seed 42). v1 and the `*_dev` tables are retired — do not read them. Dev tables are materialized from main tables only.

  Append to `Schema.md` under Known Gaps exactly:

  > **Resolved 2026-07 (Phase 1/1b):** The 5,911 NULL-date rows in `momentum_events` are confirmed as a filter-script artifact — `filter_events_power_law.py` concatenates file1 (`date`) and file2 (`event_date`) without reconciling the date columns. Canonical access is via `momentum_events_canonical` (writer: `src/data/canonical.py`, provenance Confirmed). Raw table left untouched.

  - [ ] T8a — Commit

- [ ] **T9 — Digest and report**
  Write `digest.json` per §11 and `REPORT.md`. Every claim cites its chart. All escalation-list tickers from T1 included in the report.
  - [ ] T9a — Commit; confirm working tree clean

---

## Escalation Criteria

Stop and post results. Do not proceed to the next task. Commit first.

| Condition | Threshold | Action |
|---|---|---|
| Canonical spine row count ≠ 23,268 | any deviation | Hard stop — post count and diff, await instruction |
| Unresolved suspect-class tickers (T1) | > 2% of distinct tickers | Hard stop — post the list, await instruction |
| Classification disagreement vs symbol-properties (non-suspect classes) | > 5% of overlapping tickers | Hard stop — post disagreement table, await instruction |
| Folder-join multi-matches (T2b) | > 25 events ambiguous | Hard stop — post examples, await instruction |
| 53.8M% row not caught by mechanism flag (T3a) | any | Hard stop — do not widen the rule |
| Any re-ingested folder with 0 rows post-ingest (T4b) | any | Hard stop — post folder list, await instruction |
| Bivariate flag rate (T5a) | > 1.5% of fit population | Hard stop — post chart 01, await instruction |
| Zero-event-day-trade in-scope events (T5b) | > 50 | Hard stop — post list, await instruction |
| Waterfall residual (T6) | ≠ 0 | Hard stop — post waterfall, await instruction |
| Dev v2 subset or zero-row check fails (T7a/T7b) | any | Hard stop — post mismatch detail, await instruction |

---

## Output Files

| File | Description | Status |
|---|---|---|
| `config/phase_1b.json` | seed, dev_n, strat rule, q_outlier=0.995, prev_close_floor=0.01, mom_sanity_cap=10000, classification rule version, all escalation thresholds | [ ] |
| `src/data/canonical.py` | `momentum_events_canonical` view definition (instructed promotion) | [ ] |
| `results/phase_1b/artifacts/instrument_classification.parquet` | Per-ticker class, rule hit, advisory cross-check | [ ] |
| `results/phase_1b/artifacts/event_flags.parquet` | Per-event flags + n_trades_event_day | [ ] |
| `results/phase_1b/artifacts/folder_inventory_v2.parquet` | 24,609 folders with match status, ingestion status, scope status | [ ] |
| `config/dev_sample_v2.json` | Dev sample v2 manifest | [ ] |
| `results/phase_1b/charts/01_trades_vs_momentum_flags.html` | Chart contract #01 | [ ] |
| `results/phase_1b/charts/02_instrument_classes.html` | Chart contract #02 | [ ] |
| `results/phase_1b/charts/03_universe_waterfall.html` | Chart contract #03 | [ ] |
| `results/phase_1b/charts/04_dev_v2_coverage.html` | Chart contract #04 | [ ] |

---

## Chart Contract

| # | File | Question | Encoding | n shown | Looks like this if wrong |
|---|---|---|---|---|---|
| 01 | `charts/01_trades_vs_momentum_flags.html` | Do the two outlier flags catch the artifact corner and only that corner? | x=n_trades_event_day (log), y=momentum_pct (log), scatter all fit-population events; color = unflagged / mechanism / bivariate; q=0.995 fitted line overlaid; range slider, no clipping | n per flag group in legend; total n in title | Flagged points scattered through the body of the cloud rather than concentrated in the high-momentum/low-trades corner; or real high-volume monsters (ALLR/BLRX-class) flagged |
| 02 | `charts/02_instrument_classes.html` | What does the universe lose to instrument scoping? | x=instrument class, y=event count, bar; faceted by source (momentum_events vs folder-only); suspect classes visually distinct | n on every bar | Large suspect/ambiguous bars, or common share materially below ~90% of events |
| 03 | `charts/03_universe_waterfall.html` | Does every one of 23,268 events land in exactly one bucket? | Waterfall: start 23,268, sequential drops per T6, terminal in-scope split by coverage status | n on every step | Any unexplained residual step; terminal buckets not summing to start |
| 04 | `charts/04_dev_v2_coverage.html` | Does dev v2 cover the momentum distribution of the in-scope universe? | x=momentum_pct (log), ECDF of in-scope population with the 50 dev events overlaid as strip markers colored by decile | population n and dev n in title | Dev markers clustered in a sub-range; empty deciles |

Standard chart rules per `Agent_Prompt_Standard.md` §9 apply. This is an analysis/repair phase: exempt from §7 per-event charts, not exempt from this contract.

---

## Reporting

On completion, post:
1. Classification counts table (T1a) with the suspect/escalation-list tickers enumerated
2. Canonical spine verification: row count, multi-match counts, no-folder count by class
3. Flag summary table: each flag, n flagged, % of relevant population
4. Re-ingestion table: folder, class, rows ingested (trades/quotes)
5. The full accounting waterfall with n at every step
6. Dev v2 manifest summary + subset verification result
7. Escalation check table: every criterion, observed value, pass/fail
8. Verification block (§10): every headline number with SQL/script path, filter waterfall, repro command, config hash
9. Output file table with status filled in
10. Commit list

Every claim cites its chart. No recommendations. Descriptions of what is visible are allowed; interpretation is not.

---

## Approval Gate

Do not begin Phase 2 or any follow-on work until Cooper has reviewed results and given explicit approval. Phase 2 will be re-scoped against the canonical spine after this gate.
