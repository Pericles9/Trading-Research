# Phase 5a — Dev Sample v4 Rebuild + Universe Decision Record

**Date:** 2026-07-22
**Baseline:** `phase-5-approved` — canonical spine finalized: 23,268 rows, 20,951 in-scope, `spine_window_flags` joined (15,349 clean / 5,602 flagged; 414 file1 + 5,188 file2)
**Objective:** Record the finalized analysis universe as committed decisions, then pin dev sample v4 drawn from it. No analysis in this phase.
**Primary success metric:** `filtered_trades_dev_v4` / `filtered_quotes_dev_v4` materialized, draw reproducible byte-identical from seed, representativeness chart written.

---

**Context:**

- This phase makes two decisions executable that were reached at the Phase 5 gate. They are Cooper's decisions, recorded here — the agent implements, it does not re-litigate:
  - **D1 — Analysis universe.** `in_scope = TRUE AND source_file = 'file1'`. The 2025/file2 pull (5,188 events) is excluded from all analysis: separate collection process, ~100% not-full-window, registered 3-column-schema data-quality issue. Consequence acknowledged: the analysis date range ends 2024, and time-based validation splits cannot test against 2025. Expected frame: **15,763 events** (15,349 clean, 414 flagged).
  - **D2 — `clean_window` semantics.** `clean_window` is an **eligibility flag for window-dependent measurements**, not a universe filter. Events flagged for missing forward sessions (dominant pattern `0001000`) are disproportionately halt/delisting outcomes; silently dropping them inflates T+1 results (risk register #8). Standing rule for all future phases: no query filters on `clean_window = TRUE` without the prompt stating which window-dependent measurement requires it, and flagged events are counted as outcomes wherever outcome frequencies are reported.
- Dev sample v3 predates the finalized universe and D1/D2. It is **superseded, not deleted** — `filtered_trades_dev_v3` / `filtered_quotes_dev_v3` remain in the DB untouched.
- Sampling design (fixed, not tunable):
  - **Primary cohort:** 50 events from `clean_window = TRUE` file1, stratified **5 per `momentum_pct` decile**, deciles computed within the clean file1 frame (n=15,349), **seed 42**, same stratification scheme as v3.
  - **Flagged sidecar:** 6 events from the 414 file1 flagged events, allocated across the most frequent bitmap patterns — one event per pattern for the top 6 patterns by count; if fewer than 6 distinct patterns exist, allocate remaining slots to the top pattern. Seed 42. The sidecar exists so code paths that handle flagged events per D2 are exercisable at dev tier. It is **never pooled with the primary cohort in any statistic**.
  - Both cohorts carry a `dev_cohort` column: `'primary'` | `'flagged_sidecar'`.
- All tick extraction joins through `momentum_events_canonical` on `(ticker, event_date_canonical, ROUND(momentum_pct, 2))` — never folder presence.
- DuckDB SQL, not pandas, for anything touching `filtered_trades` / `filtered_quotes`.
- Standing constraints per `CLAUDE.md` apply (no D: writes, no base-table mutation, provenance quarantine).

---

## Tasks

- [ ] **T0 — Approval housekeeping, branch, prompt/config commit**
  Record Phase 5 approval per the established pattern (in-session authorization by this prompt's approval): set `results/phase_5/digest.json` status → `complete_approved`, tag `phase-5-approved` at Phase 5's tip, fast-forward `master`. Then cut `phase/5a` from master. Commit `prompts/phase_5a.md` and `config/phase_5a.json` (seed, cohort sizes, decile scheme, sidecar allocation rule — every tunable in config, none in code).
  - [ ] T0a — Commit

- [ ] **T1 — Record D1/D2 in the decisions record**
  Write both decisions verbatim (as stated in Context) to `docs/Universe-Decisions.md`, numbered D1 and D2, each with date, deciding phase gate (`phase-5-approved`), and the consequence lines. Update `docs/Open-Items-Register.md`: close the "2025 inclusion decision" item, referencing D1.
  - [ ] T1a — Commit

- [ ] **T2 — Build and verify the sampling frame**
  From `momentum_events_canonical`, materialize the frame `in_scope = TRUE AND source_file = 'file1'` to `results/phase_5a/artifacts/sampling_frame.parquet`. Verify counts: total = 15,763, `clean_window = TRUE` = 15,349, flagged = 414. Verify the 414 reconcile with `spine_window_flags` exactly (same union/overlap figures as Phase 5 T4a: 287/386/259-28-127).
  - [ ] T2a — Commit

- [ ] **T3 — Draw v4 primary cohort**
  Compute `momentum_pct` deciles over the 15,349 clean-frame events. Draw 5 per decile, seed 42, method identical to the v3 draw (cite the v3 script path used and reuse its sampling function; if the v3 function cannot be located, hard stop — do not reimplement from memory). Write the 50-event list to `results/phase_5a/artifacts/dev_v4_primary_events.parquet`.
  - [ ] T3a — Reproducibility check: run the draw twice; event lists must be byte-identical
  - [ ] T3b — Commit

- [ ] **T4 — Draw flagged sidecar**
  Rank the 414 flagged file1 events' combined bitmap patterns (trades bitmap ∥ quotes bitmap) by frequency. Draw per the allocation rule in Context, seed 42. Write to `results/phase_5a/artifacts/dev_v4_sidecar_events.parquet` with the pattern each event represents.
  - [ ] T4a — Reproducibility check as in T3a
  - [ ] T4b — Commit

- [ ] **T5 — Materialize dev v4 tick tables**
  Create `filtered_trades_dev_v4` and `filtered_quotes_dev_v4`: all tick rows for the 56 events (spine join, not folder filter), `dev_cohort` column attached. Do not modify or drop the v3 tables. Log row counts per table and per cohort. Runtime check: one representative aggregate query (spread median by event, primary cohort) must complete in under 60 seconds; log the timing.
  - [ ] T5a — Verify every primary event has both trades and quotes rows; sidecar events may legitimately lack quotes rows (e.g., the no-quotes-file cohort) — log per-event presence, do not treat absence as failure for the sidecar
  - [ ] T5b — Commit

- [ ] **T6 — Representativeness chart** (per Chart Contract)
  - [ ] T6a — `charts/01_dev_v4_representativeness.html` written and visually verified via kaleido PNG
  - [ ] T6b — Commit

- [ ] **T7 — Digest and report**
  `digest.json` per §11, `REPORT.md` per the Evidence Standard. Every claim cites its chart or artifact. Decisions log captures any implementation micro-decisions (e.g., tie-breaking in decile edges).
  - [ ] T7a — Commit; confirm working tree clean

---

## Escalation Criteria

Stop and post results. Do not proceed to the next task.

| # | Condition | Threshold | Action |
|---|---|---|---|
| 1 | Frame counts | ≠ 15,763 / 15,349 / 414 | Hard stop — commit, post observed counts and the reconciliation diff vs. `spine_window_flags`, await instruction |
| 2 | v3 sampling function not located | cannot cite script path | Hard stop — do not reimplement; post search paths tried, await instruction |
| 3 | Draw reproducibility | any diff between repeat draws | Hard stop — commit, post both event lists, await instruction |
| 4 | Any decile with < 5 clean events | n < 5 | Hard stop — post decile counts, await instruction |
| 5 | Primary event missing trades or quotes rows | any | Hard stop — post event list with per-side row counts, await instruction |
| 6 | Dev-tier runtime | representative query > 60s | Hard stop — post timing and query plan, await instruction |
| 7 | Any write to base tables, v3 dev tables, or data root | any | Hard stop |

---

## Output Files

| File | Description | Status |
|---|---|---|
| `docs/Universe-Decisions.md` | D1/D2 recorded | [ ] |
| `config/phase_5a.json` | Seed, cohort sizes, decile scheme, sidecar rule | [ ] |
| `results/phase_5a/artifacts/sampling_frame.parquet` | 15,763-event frame | [ ] |
| `results/phase_5a/artifacts/dev_v4_primary_events.parquet` | 50-event primary list | [ ] |
| `results/phase_5a/artifacts/dev_v4_sidecar_events.parquet` | 6-event sidecar list with patterns | [ ] |
| `results/phase_5a/charts/01_dev_v4_representativeness.html` | Per Chart Contract | [ ] |
| DuckDB tables `filtered_trades_dev_v4`, `filtered_quotes_dev_v4` | Materialized dev tier | [ ] |

---

## Chart Contract

| # | File | Question | Encoding | n shown | Looks like this if wrong |
|---|---|---|---|---|---|
| 01 | `charts/01_dev_v4_representativeness.html` | Does the 50-event primary cohort represent the clean file1 frame on `momentum_pct`? | x=`momentum_pct` (log), ECDF: frame (n=15,349) vs. primary cohort (n=50); secondary panel: per-decile strip of sampled events over frame violin | Frame and cohort n in title; 5 per decile annotated | Cohort ECDF visibly departs from frame ECDF; sampled points cluster within deciles instead of spanning them |

Standard chart rules apply (§9). The sidecar is annotated on the chart as separate marks, clearly labeled, never pooled into the primary ECDF.

---

## Reporting

On completion, post:
1. Frame verification table (counts + reconciliation vs. `spine_window_flags`)
2. Primary cohort table: decile, n, momentum_pct range sampled
3. Sidecar table: event, bitmap pattern represented
4. Dev table row counts per table per cohort, and the representative-query timing
5. Escalation check table — all 7 rows
6. Verification block (§10) with filter waterfall frame → cohorts → tick rows
7. Output file table with status filled in; commit list

Every claim cites its chart or artifact. No recommendations.

---

## Approval Gate

Do not begin Phase 6 scoping or any analysis work until Cooper has reviewed results and given explicit approval. On approval, tag `phase-5a-approved`. Dev sample v4 is then **pinned** — it does not change for the remainder of the program.
