# Phase 13 — Fundamental Partition Test

**Type:** exploratory partition test. Not a backtest — no trade record, no per-event chart
requirement (§8 of the standard is exempt; §10's Chart Contract still applies in full).
**Produces:** a population-scale, per-event outcome variable (P0) in cost-multiple units; a
detection-price-decile control arm (arm zero); three fundamental splits, cross-cut by event
year and price decile.
**Gate Mode:** sync-required.
**Branch:** `phase/13`, cut from `master` once PR #5 (`build/fundamentals-f1` → `master`) merged.
`event_fundamentals.parquet` and D32 Amendment A1 are both on `master` as of this branch point.
**Standard:** `docs/Agent_Prompt_Standard.md` v1.4, §§1–13 in full.

> **Reconstruction note, 2026-09-13.** This document was drafted, posted, and approved (with
> amendments) in the same session it describes, but the file itself was never written to disk —
> T0's commit (`e0ed9a3`) landed `config/phase_13.json` only. `tools/verify_cited_paths.py` caught
> the gap (`prompts/phase_13.md` cited by `docs/Research-Library-Map.md` but absent from the repo)
> before T3's commit could compound it. This text is reconstructed from the approved plan as it was
> actually executed in T0–T2's commits and `config/phase_13.json`'s own record of the approval
> exchange — it is not a retroactive rewrite of what was approved, it is recovering what was lost.

> **Amendment, 2026-09-13, before any task ran.** This phase executes D32 Amendment A1 — the
> gating sentence: *"If a partition of the universe on a pre-`t0` observable produces a
> sub-population whose net-expectancy distribution clears the round-trip cost stack — where the
> full population's does not — then D24 and D25's arithmetic reopens on that sub-population, and
> the universe definition changes to that partition. If no partition does, the fundamental layer
> is documentation and the line stays closed."* Cooper's approval ("approved, proceed") carried two
> amendments in the same exchange: T3b/T3c run **undirected** rather than pre-registered ("no pre
> reg"), and **no split — including T3a — is evaluated against a kill-condition margin**
> ("exploratory, no kill condition"). **This is a departure from this program's own standing
> caution** — D25's "what must not happen" warns against searching a result space without a
> pre-registered stopping rule, and D26's retraction history is the record of what that costs. The
> instruction is followed as given, not silently absorbed and not overridden: the mitigation here is
> in *how this phase reports* (every split's both tails shown, every cell a distribution not a
> verdict, no chart or script permitted to declare a split "cleared" — Escalation rows 2/3 below),
> not in re-imposing a kill condition Cooper explicitly declined.

---

## Context

- The architect's proposal, "What the preliminary fundamental research should look like"
  (2026-09-13), signed off by Cooper ("i sign off"), is the design this phase executes. §0's
  one-line answer: partition the universe on a pre-`t0` fundamental observable against a
  to-be-built population-scale outcome, with the detection-price floor as the competing
  explanation (arm zero).
- No per-event, population-scale outcome variable exists yet. Phase 11's 70.98 bp round-trip cost
  (T7 named cell, n=10,544) is a **population aggregate**, not a per-event denominator — this
  phase's T1 builds the per-event equivalent.
- `event_minute_bars_v2` (45,925,350 rows, `research/phase_6b/build_minute_bars_v2.py`, built
  directly from `filtered_trades`/`filtered_trades_dev_v4`) and `event_quote_metrics_v1`
  (9,017,475 rows) are both tick-derived — checked directly before use, not assumed — so neither
  is D4-quarantined.
- `event_fundamentals.parquet` (Build F1, 20,951 rows, all 9 Verification Block checks passing as
  of the branch point) is read directly. No fundamental column is ever an input to a computed
  outcome (D32) — a fundamental column labels a group; the group's own outcome is computed from
  tick/quote data exclusively.

---

## Constraints

- D4/A9/A12/A13 stand: tick- and bar-derived measurement only. `detection_price` (from F1-T6) is
  already D4-compliant — no spine numeric column enters any computation here.
- D32 / Amendment A1 stand: fundamental columns are partition keys, never regression inputs.
- Per Cooper's 2026-09-13 amendment: **exploratory, no kill condition on any split.** T3a keeps the
  direction the signed-off proposal pre-registered; T3b/T3c are undirected.
- Every tunable lives in `config/phase_13.json`. Working directory: repo root
  (`E:\Trading-Research-f1`, a worktree of `E:\Trading Research` — data paths route through
  `resolve_data_root()`, never a cwd-relative literal; this exact bug class was found and fixed
  across Build F1 on 2026-09-12/13).

---

## Tasks

- [ ] **T0 — Branch, config, preconditions**
  - [ ] T0a — Cut `phase/13` from `master`.
  - [ ] T0b — Write `config/phase_13.json`: entry reference (`t0`), horizon grid
        (5/15/30/60 min), per-event cost-unit source (`event_quote_metrics_v1`), split
        definitions (T3a `pre_registered`, T3b/T3c `undirected`), `kill_condition.enabled: false`,
        cross-cut spec (`event_year` × `detection_price_decile`, `min_cell_n_log_threshold: 200`).
  - [ ] T0c — Run `tools/verify_claude_md_indices.py` and `tools/verify_cited_paths.py`. Confirm no
        new unresolved citation traces to this branch's own files.
  - [ ] T0d — Commit `prompts/phase_13.md` and `config/phase_13.json` together.

- [ ] **T1 — P0: the population-scale outcome**
  - [ ] T1a — Per event, from `event_minute_bars_v2`: MFE/MAE from `t0` at 5/15/30/60 min, in units
        of that event's own round-trip cost (`2 × tw_spread_bp` from `event_quote_metrics_v1` at
        the entry reference's minute). **Bulk single-join design required** — a per-event point
        query against `event_minute_bars_v2` is pathologically slow (observed: DuckDB's own
        progress estimate exceeded a day on a single-ticker filter); register the small events
        frame and let the optimizer hash-join in one scan.
  - [ ] T1b — Coverage report: round-trip-cost and minute-bar coverage share, by horizon.
  - [ ] T1c — Commit.

- [ ] **T2 — Arm zero: detection-price-decile control**
  - [ ] T2a — MFE/MAE cost-multiple distributions by `detection_price_decile` (F1-T6), every
        horizon, no fundamental data at all. This is T3's competing explanation, not optional —
        cheap stocks file differently, dilute more, reverse-split more, and cost more to trade, so
        a fundamental split can be a price split in different clothes.
  - [ ] T2b — Commit.

- [ ] **T3 — P1: fundamental partitions, within-year, within-price-decile, exploratory.** Three
      splits, each evaluated **within event year** (coverage is collinear with the vendor calendar
      cliff, F1-T6c) **and within detection-price decile** (T2's control, nested per §5 of the
      design this phase executes). **Per Cooper's 2026-09-13 amendment: exploratory, no kill
      condition on any split.** T3a keeps the direction the signed-off proposal pre-registered;
      T3b/T3c run undirected, both signs reported.
  - [ ] T3a — `flg_dilution_form_before_t0` split. Pre-registered direction (from the signed-off
        proposal, not invented by this phase): events with a dilution filing before `t0` show
        worse continuation and a faster flip.
  - [ ] T3b — Share-turnover proxy: event-day tick volume / `shs_shares_outstanding`,
        **split-adjusted using `spl_` history — not optional**, given how routine reverse splits
        are in this cohort. Split at the population median. Undirected.
  - [ ] T3c — `spl_reverse_split_365d` split, same basis as T3b. Undirected.
  - [ ] T3d — For each split: MFE/MAE cost-multiple distribution above vs. below, at every horizon,
        cross-cut by year and by price decile. Distribution before aggregate; no bare pass/fail on
        a mean; no split declared a finding; a cell below `config.cross_cuts.min_cell_n_log_threshold`
        is flagged, not reported at equal weight.
  - [ ] T3e — Commit.

- [x] **T4 — Tick-level confirmation** *(conditional, Cooper-gated)*. Not auto-triggered by
      anything — no kill condition exists to trigger it. Runs only if Cooper explicitly names a
      specific cross-cut worth confirming after reviewing T3's charts. Not part of this phase's
      own completion.

      **Triggered 2026-09-14.** Cooper: "proceed with tick confg" — the target was not named in
      that message, so a follow-up `AskUserQuestion` was posted rather than guessed; Cooper chose
      the recommended option: **T3b, share turnover** (the largest population-aggregate separation
      of the three splits, ~3x median MFE cost-multiple at 15 min). Confirms T3b's minute-bar-derived
      MFE/MAE against `filtered_trades` (raw ticks) directly, over the same population and horizons
      T3b already used — not a new claim, a check on whether the existing one survives contact with
      the tick data the bars were built from. Same no-kill-condition, no-pass/fail rule as every
      other task in this phase (escalation rows 2/3 still apply).
      - [ ] T4a — Per-event tick-level MFE/MAE from `filtered_trades`, all 4 horizons, one bulk
            join (register the events frame, `MAX(price)`/`MIN(price)` `GROUP BY event_id`,
            filtered on the raw `sip_timestamp` BIGINT column — not a converted timestamp, which
            defeats row-group pruning elsewhere in this repo). Tested on a small subset before the
            full ~11,971-event population per the standing two-tier-execution discipline.
      - [ ] T4b — Per-event tick-vs-bar agreement: share of events where tick MAX/MIN differs from
            `event_minute_bars_v2`'s bar high/low in the same window, and by how much. A real
            disagreement is a finding about the bar-build pipeline, not about T3b.
      - [ ] T4c — Re-run T3b's above/below-median-turnover distribution comparison using
            tick-derived MFE/MAE cost-multiple instead of bar-derived. Report whether the same
            qualitative separation holds — as a distribution comparison, not a verdict.
      - [ ] T4d — Chart `07_t4_tick_vs_bar_confirmation.html` (added to the Chart Contract, §7).
      - [ ] T4e — Commit.

- [ ] **T5 — Charts, Verification Block, digest, report.** Every chart in the Chart Contract,
      `research/phase_13/verify_partition_test.py` per §11, `results/phase_13/digest.json` per
      §12, `results/phase_13/REPORT.md` per §7/§10 with a copy at
      `results/reports/phase_13_report.md`. Commit; `git status` clean.

---

## Escalation Criteria

Stop, commit, post observed values, await instruction for HARD STOP rows. LOG rows continue and
are recorded in `digest.json`'s `surprises`. Table order is priority order.

| # | Condition | Threshold | Tier | Action |
|---|---|---|---|---|
| 1 | Working tree dirty at T0a, or a data path bypasses `resolve_data_root()` | any | HARD STOP | Commit, post, await instruction |
| 2 | Any script, chart, or report text states a split "clears," "passes," "wins," or otherwise declares a pass/fail outcome | any | HARD STOP | Per Cooper's amendment — no kill condition exists, so no artifact may act as if one does |
| 3 | Any single cross-cut cell is presented as "the finding," headlined, or otherwise singled out without Cooper having asked for it | any | HARD STOP | Distributions are reported whole; no cell is promoted above the others by this phase itself |
| 4 | A fundamental column (`flg_`/`shs_`/`spl_`/`si_`/`fin_`) used as an input to a computed outcome rather than a partition key | any | HARD STOP | D32 / Amendment A1 |
| 5 | Minute-bar or round-trip-cost coverage, by horizon | < 80% | LOG | Continue; record in `surprises` — fired at T1, 75.2% |
| 6 | A boolean split column (`flg_`/`spl_`) used without gating on its own `_quality` column when that column has an `unavailable` value that folds silently into `False` | any | HARD STOP | Confirmed both `flg_quality` and `spl_quality` do exactly this — 248 and 12,219 events respectively |
| 7 | A cross-cut cell below `config.cross_cuts.min_cell_n_log_threshold` | any | LOG | Continue; flagged in the cell itself, not hidden by coarsening the cut |
| 8 | A spine numeric column (D4) reaches any computation path | any | HARD STOP | |
| 9 | Write outside `results/phase_13/`, `prompts/`, `config/`, `research/phase_13/` | any | HARD STOP | |
| 10 | Tick-derived MFE/MAE disagrees with `event_minute_bars_v2`'s bar-derived value for the same event/window | > 5% of covered events, or any single event by > 2x | LOG | Continue; record in `surprises` — this is a finding about the bar-build pipeline (research/phase_6b/build_minute_bars_v2.py), not about T3b, and does not block T4's own reporting |

If no escalation criteria apply to a task, that is stated explicitly in that task's commit message.

---

## Output Files

| File | Description | Status |
|---|---|---|
| `prompts/phase_13.md`, `config/phase_13.json` | Committed at T0 | [x] |
| `research/phase_13/common.py` | Shared config/connection plumbing | [x] |
| `research/phase_13/t1_build_p0.py`, `results/phase_13/artifacts/p0_coverage_summary.json` | T1 | [x] |
| `research/phase_13/t2_arm_zero.py`, `results/phase_13/artifacts/t2_arm_zero_summary.json` | T2 | [x] |
| `research/phase_13/t3_partitions.py`, `results/phase_13/artifacts/t3_partition_summary.json` | T3 | [x] |
| `research/phase_13/verify_partition_test.py` | Verification Block, §11 | [x] |
| `research/phase_13/{chart_common,chart_01..chart_06}.py`, `results/phase_13/charts/01-06*.{html,png}` | Per Chart Contract | [x] |
| `research/phase_13/t4_tick_confirm.py`, `results/phase_13/artifacts/t4_tick_confirmation.json` | T4, Cooper-triggered 2026-09-14 (T3b) | [ ] |
| `research/phase_13/chart_07.py`, `results/phase_13/charts/07_t4_tick_vs_bar_confirmation.{html,png}` | T4d, added to Chart Contract | [ ] |
| `results/phase_13/{digest.json, REPORT.md}` | Per §12/§7 | [x] |
| `results/reports/phase_13_report.md` | Cross-phase copy | [x] |
| `docs/Research-Library-Map.md` | Folder-level addendum, updated every task boundary | [x] |

`results/phase_13/artifacts/p0_outcome.parquet` and `results/phase_13/artifacts/*.parquet`
intermediate files are gitignored (regenerable from committed scripts + config), matching the
`results/fundamentals_f1/artifacts/*.parquet` / `results/scale_field/artifacts/*.parquet`
convention for non-source-of-record parquet.

---

## Reporting

On completion, post:
1. T0d state (branch, config hash)
2. T1 coverage table (round-trip cost and minute-bar coverage, by horizon)
3. T2's price-decile distribution table
4. T3's cross-cut tables, all three splits, both tails, every horizon — **no split ranked, no
   split declared a finding**
5. T4's tick-vs-bar agreement table and the tick-derived T3b comparison, if T4 was triggered
6. Escalation check table, all 10 rows, tier and observed value
7. Output file table with final status
8. Verification Block result

On HARD STOP escalation, post the criterion, the observed value, the state up to that point, and
no recommendation.

Every posted table carries n. Every claim cites its chart.

---

## Chart Contract

| # | File | Question | Encoding | n shown | Looks like this if wrong |
|---|---|---|---|---|---|
| 01 | `charts/01_p0_coverage.html` | How much of the universe does P0 actually cover? | Bar chart, coverage share by horizon, faceted by event year | n covered / n total per facet | Flat 100% everywhere — coverage gap silently absorbed rather than measured |
| 02 | `charts/02_arm_zero_price_decile.html` | Does detection price alone predict net expectancy? | MFE/MAE cost-multiple distribution (box or violin) by price decile, faceted by horizon | n per decile | No gradient across deciles — price alone explains nothing, so a fundamental split's gradient (if any) is not just price in disguise |
| 03 | `charts/03_flg_dilution_split.html` | Does a pre-`t0` dilution filing associate with worse continuation? | Small multiples: MFE/MAE cost-multiple distribution above/below the split, rows = year, columns = price decile | n per cell, sparse cells hatched | A single aggregate bar standing in for the small multiples — collapsing the cross-cut hides exactly the heterogeneity T2 exists to control for |
| 04 | `charts/04_shs_turnover_split.html` | Does share turnover (split-adjusted) associate with the outcome, in either direction? | Same layout as 03 | n per cell, sparse cells hatched | A reference line or shading implying a threshold — this split has no pre-registered direction and no kill condition |
| 05 | `charts/05_spl_reverse_split.html` | Does a reverse split in the trailing 365 days associate with the outcome, in either direction? | Same layout as 03 | n per cell, sparse cells hatched | Same failure mode as 04 |
| 06 | `charts/06_all_splits_summary.html` | How do all three splits compare to arm zero, side by side? | All three splits + arm zero on one page, same y-axis scale, **no reference line, no pass/fail shading, no ranking** | n per split/side | Any visual cue (color, ordering, annotation) that implies one split "won" — this chart exists to let Cooper compare, not to declare a comparison's winner |
| 07 | `charts/07_t4_tick_vs_bar_confirmation.html` | Added at T4 (Cooper-triggered 2026-09-14). Does T3b's bar-derived finding hold against raw ticks? | Two panels: (a) tick-vs-bar MFE/MAE agreement, one point per event; (b) T3b's above/below-median-turnover distribution comparison, tick-derived vs. bar-derived side by side | n per panel | Tick and bar values disagree substantially with no explanation — a pipeline discrepancy, not a finding about T3b itself |

---

## Approval Gate

**Gate Mode: sync-required.**

Approved by Cooper, 2026-09-13 ("approved, proceed"), with two amendments made in the same
exchange: T3b/T3c run undirected rather than pre-registered ("no pre reg"), and no split —
including T3a — is evaluated against a kill-condition margin ("exploratory, no kill condition").

Do not begin T4 (tick-level confirmation) or any follow-on phase until Cooper has reviewed T3's
charts and the digest, and either names a specific cross-cut worth confirming at tick level or
closes the phase as read. This phase's own completion (T0–T3, plus T5's charts/digest/report) does
not require T4 to run — T4 is explicitly optional and Cooper-triggered only.
