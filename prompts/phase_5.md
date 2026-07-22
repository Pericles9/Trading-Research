# Phase 5 — Window Flags & Canonical Spine Finalization

**Date:** 2026-07-21
**Baseline:** `phase-4-approved` — quotes-side census + classification complete; T1 guard 20,951 / 287 / 386 / 259-28-127; 0 escalations
**Objective:** Apply the approved disposition — flag and carry every in-scope event lacking a full 7-session clean window on both feeds — and rebuild `momentum_events_canonical` as the finalized spine.
**Primary success metric:** Canonical view rebuilt with additive window-flag columns; all reconciliation checks in §Escalation exact; rebuild idempotent; `in_scope` population unchanged at 20,951.

**Authorizing decision (Cooper, 2026-07-21):** Flag and carry all events that do not have a full 7-trading-day clean window. No deletions. No recollection. No `in_scope` changes. This closes the disposition question held at the Phase 4 approval gate.

---

**Context:**

- DB: `E:\Trading Research\data\duckdb\main.duckdb`. Canonical view: `momentum_events_canonical`.
- Calendar: XNYS, `pandas_market_calendars==5.4.0` / `exchange_calendars==4.13.2` (post-Phase-4 T0b pin). Derivation range 2019-12-01..2026-01-15, 1,539 sessions. Any deviation from this pin is escalation row 7.
- **Scope: all 20,951 in-scope events, both source files.** Prior cohorts (287 trades / 386 quotes) were file1-scoped; they are reconciliation targets here, not the flag source. Flags are recomputed from the tick tables.
- Session-presence definitions are reused verbatim: trades side per Phase 3's bitmap derivation, quotes side per Phase 4 T4. Do not redefine "present."
- Phase 4's cached quotes actual-sessions artifact (`results/phase_4/artifacts/quotes_bitmaps.parquet` + its full-population cache) may be reused for the quotes side **only if** its config hash and calendar pin resolve to committed state; otherwise recompute. State which path was taken in the decisions log.
- Full-table pass budget: **2 maximum** (one trades, one quotes; 1 if the quotes cache is reusable). Develop all derivation SQL on the dev tier first; one full run after config freeze.
- Existing classification labels are carried, not recomputed: trades-side labels from Phase 3's classification artifact, quotes-side from `results/phase_4/artifacts/classification_summary.json` source data. No new forensic passes.
- This phase mutates the canonical view definition. That is the **only** permitted mutation. No writes to base tables, no writes to the data root.

---

## Tasks

- [ ] **T0 — Branch and commit prompt**
  Cut `phase/5` from main at `phase-4-approved`. Commit `prompts/phase_5.md` and `config/phase_5.json` before any other work.

- [ ] **T1 — Pre-mutation guard and view snapshot**
  Reproduce Phase 4's T1 guard against the live view: `in_scope` 20,951; trades cohort 287; quotes cohort 386; overlap 259/28/127. Export the current `momentum_events_canonical` view DDL verbatim to `results/phase_5/artifacts/view_ddl_pre.sql` and commit it — this is the rollback reference.
  - [ ] T1a — Any guard mismatch → escalation row 2
  - [ ] T1b — Commit

- [ ] **T2 — Trades-side session bitmap, all in-scope events**
  Per-event 7-offset presence bitmap against `filtered_trades` for all 20,951 in-scope events, using Phase 3's exact derivation and expected-session logic (XNYS, post-1c canonical dates). Dev tier first; one full pass. Write `results/phase_5/artifacts/trades_bitmaps.parquet`.
  - [ ] T2a — Commit before the full run; commit after

- [ ] **T3 — Quotes-side session bitmap, all in-scope events**
  Same, against `filtered_quotes`, per Phase 4 T4's derivation. Reuse the Phase 4 cache if hash-verifiable (see Context); otherwise one full pass. Write `results/phase_5/artifacts/quotes_bitmaps_all.parquet`.
  - [ ] T3a — Commit

- [ ] **T4 — Derive flags and labels**
  Build `results/phase_5/artifacts/spine_window_flags.parquet` and DuckDB table `spine_window_flags`, one row per in-scope event, columns:
  - `trades_full_window` BOOL — all 7 expected sessions present in `filtered_trades`
  - `quotes_full_window` BOOL — all 7 expected sessions present in `filtered_quotes`
  - `clean_window` BOOL — both of the above
  - `trades_gap_label` — Phase 3 classification label where classified; `not_classified` for flagged events outside Phase 3's scope (file2); NULL only for clean events
  - `quotes_gap_label` — Phase 4 bitmap-first label where classified; `not_classified` for flagged events outside the 386 cohort (file2); NULL only for clean events
  - `trades_bitmap`, `quotes_bitmap` — 7-char offset strings
  Reconciliation checks (all must be exact; any miss → escalation row 3):
  - [ ] T4a — file1 subset: `NOT trades_full_window` = 287; `NOT quotes_full_window` = 386; union = 414; overlap = 259/28/127
  - [ ] T4b — file2 quotes-side no-file events ≥ 37, and the 37 known events all flagged
  - [ ] T4c — No flagged event with NULL label; no clean event with a non-NULL label
  - [ ] T4d — Report file2 flagged counts, trades and quotes side, with n — first measurement of this population; escalation row 4 bounds it
  - [ ] T4e — Commit

- [ ] **T5 — Rebuild `momentum_events_canonical`**
  Rebuild the view to left-join `spine_window_flags` on the canonical key, adding the six columns above. Additive only: no existing column changes, no row changes, no `in_scope` logic changes. Export post-mutation DDL to `results/phase_5/artifacts/view_ddl_post.sql`.
  - [ ] T5a — Post-mutation checks: row count unchanged; `in_scope` = 20,951 unchanged; all pre-existing columns byte-identical on a seeded 1,000-row sample diff
  - [ ] T5b — Idempotence: run the rebuild twice; second run produces zero definitional or data diff
  - [ ] T5c — Commit (rebuild SQL is a committed script in `research/phase_5/`, runnable end-to-end)

- [ ] **T6 — Charts per the Chart Contract**
  - [ ] T6a — `01_clean_vs_flagged_by_year.html`
  - [ ] T6b — `02_momentum_pct_clean_vs_flagged.html`
  - [ ] T6c — `03_flag_label_composition.html`
  - [ ] T6d — Commit

- [ ] **T7 — Register, digest, report**
  Update `docs/Open-Items-Register.md`: close the quotes-disposition item and the 37-event file2 item (both resolved by flag-and-carry); record the ~46 no-signature file1 events as flagged-with-label-carried, closed. Write `digest.json` per §11 and `REPORT.md`; every claim cites its chart.
  - [ ] T7a — Commit; confirm working tree clean

---

## Escalation Criteria

Stop and post results. Do not proceed. Do not fix.

| # | Condition | Threshold | Action |
|---|---|---|---|
| 1 | Post-mutation `in_scope` count or view row count changed | any deviation from 20,951 / pre-mutation row count | Hard stop — commit, post counts, restore is NOT attempted, await instruction |
| 2 | T1 pre-mutation guard mismatch | any deviation from 20,951 / 287 / 386 / 259-28-127 | Hard stop — commit, post table, await instruction |
| 3 | T4 file1 reconciliation mismatch | any deviation from 287 / 386 / 414 / 259-28-127, or any of the 37 known file2 events unflagged | Hard stop — commit, post diff of expected vs. observed event sets, await instruction |
| 4 | file2 flagged share (either side) | > 5% of file2 in-scope events (> 260) | Hard stop — post counts and bitmap pattern table, await instruction |
| 5 | Label integrity | any flagged event with NULL label, or clean event with non-NULL label | Hard stop — post offending rows, await instruction |
| 6 | Idempotence failure (T5b) | any diff on second rebuild | Hard stop — commit both DDL exports, post diff, await instruction |
| 7 | Calendar pin drift | installed versions ≠ 5.4.0 / 4.13.2 | Hard stop before any derivation runs |
| 8 | Any write to base tables or data root | any | Hard stop |

---

## Output Files

| File | Description | Status |
|---|---|---|
| `results/phase_5/artifacts/view_ddl_pre.sql` | Pre-mutation view DDL (rollback reference) | [ ] |
| `results/phase_5/artifacts/view_ddl_post.sql` | Post-mutation view DDL | [ ] |
| `results/phase_5/artifacts/trades_bitmaps.parquet` | Per-event trades presence bitmaps, all in-scope | [ ] |
| `results/phase_5/artifacts/quotes_bitmaps_all.parquet` | Per-event quotes presence bitmaps, all in-scope | [ ] |
| `results/phase_5/artifacts/spine_window_flags.parquet` | The flags + labels table | [ ] |
| `results/phase_5/artifacts/reconciliation_summary.json` | T4 check results, expected vs. observed | [ ] |
| `research/phase_5/rebuild_canonical_view.py` (or `.sql`) | Committed, re-runnable rebuild | [ ] |
| `results/phase_5/charts/01-03*.html` | Per contract | [ ] |
| `docs/Open-Items-Register.md` | Updated per T7 | [ ] |

---

## Chart Contract

| # | File | Question | Encoding | n shown | Looks like this if wrong |
|---|---|---|---|---|---|
| 01 | `charts/01_clean_vs_flagged_by_year.html` | Where do flagged events sit in time and source file? | x=event year, y=count, stacked bar clean/flagged, facet by source_file | Count label per stack segment | Flagged mass appears in years/files where prior phases found none — contradicts the census |
| 02 | `charts/02_momentum_pct_clean_vs_flagged.html` | Does flagging bias the research universe? | x=clean vs flagged, y=momentum_pct (log), violin + strip, facet by source_file | Per-group n above each violin | Distributions clearly separated — flagged events are systematically different momentum events, and every downstream result conditional on `clean_window` inherits that skew |
| 03 | `charts/03_flag_label_composition.html` | What explains the flagged population? | x=label, y=count, grouped by side (trades/quotes), `not_classified` shown explicitly | Count per bar | `not_classified` dominates — the carried classifications explain little of what the full-population recompute found |

Chart 02's failure appearance is the one that matters for the program: flag-and-carry only preserves interpretability if the flagged set isn't a biased slice of the universe. Describe what the chart shows; the bias call is Cooper's.

---

## Reporting

On completion, post:
1. Flag summary table: side × source_file × flagged/clean, with n per cell
2. Label composition table (both sides), with n
3. T4 reconciliation table: every check, expected, observed, exact-match column
4. T5 mutation-safety table: row count, in_scope count, sample-diff result, idempotence result
5. Escalation check table
6. Verification block (§10) including both filter waterfalls (flag derivation; view rebuild)
7. Output file table, commit list

Every claim cites its chart. No recommendations. The file2 flagged counts (T4d) are a first measurement — report them with bitmap pattern breakdown, describe, do not explain.

---

## Approval Gate

Do not begin any follow-on work — including dev-sample rebuild, any Phase 6 scoping, or any use of `clean_window` as a filter in analysis — until Cooper has reviewed results and given explicit approval. On approval, tag `phase-5-approved`; this tag is the finalized canonical spine all downstream phases cite.
