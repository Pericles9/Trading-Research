# Relative momentum R0 — qualification-layer scoping — REPORT

**Branch:** `explore/relative-momentum-r0` · **Config hash:** `5fae280c7fed`
**Status: STOPPED AT T0b.** T0a (parts 1 and 2) and T0b ran. T1, T1c, T2, T3, T4 and T5 did not run.
(T0a part 2 was deferred at the stop and run later, in Addendum 2, because `move_at` needs it.)
**Addendum, 2026-09-18:** sections T0b-4 and T0c were added after the stop, in answer to the
2026-09-18 read of T0b. Neither restarts the brief: T0b-4 re-measures a number that read draws an
inference from, and T0c is that read section 3 check, which runs entirely on Phase 11 committed output.
**Addendum 2, 2026-09-18:** T0a part 2 and T0c2 were added on the erratum to that read, which mandates
rerunning T0c with the causal measure move_at. **T0c2 reverses T0c direction and supersedes every T0c
slice built on momentum_pct.** T0c rows are kept below as the record of what the defective
specification produced.
**Not a phase, not a finding.** No decision recorded, no hypothesis tested, no outcome variable
touched (DR-5). Describes the pictures; Cooper decides what they mean.

Brief: `prompts/relative_momentum_r0.md` (v3, 2026-09-17), filed at that path by this run — see §0.

---

## 0 — Record of what the brief cites that this checkout does not contain

Posted first because two of the numbers the brief's §I.1 table rests on are among them.

| cited path | state in this checkout |
|---|---|
| `prompts/relative_momentum_r0.md` (v2) | does not exist — never committed |
| `prompts/relative_momentum_r1_inputs.md` | does not exist — never committed |
| `prompts/relative_momentum_r0_amendment_1.md` | does not exist — never committed |
| `claude/where_next_universe_criteria.md` | does not exist (Criteria 1, 2, 5 are cited from it) |
| `claude/prompt_standard_amendment_v15.md` | does not exist (§B is cited as the defect class T0b catches) |
| `claude/fundamental_data_float_scoping_note.md` | does not exist (§2, §4, §6 are cited by DR-4 and T5) |
| `prompts/fundamental_exploration_e2.md` | does not exist — E2's artifacts exist, its brief was never committed |

The v3 document was filed at `prompts/relative_momentum_r0.md` so that
`config/relative_momentum_r0.json`'s `_meta.prompt` citation resolves to a real file; the four
unresolvable citations are marked `[unverified]` inline there. No redirect stubs were created for the
three superseded paths — there is nothing to redirect from.

**Two cited profit factors are not verifiable from this checkout.**

| brief's §I.1 claim | what is in this checkout |
|---|---|
| `scanner-epg-momentum` Phase H, **PF = 1.5297** | `scanner-epg-momentum/backtest/CLAUDE.md` states "Phase H requires explicit approval before any implementation" and lists no Phase H results directory. No such run exists here. |
| `hawkes-ofi-impact` Phase U, **PF = 1.0962** on 100-event validation | recorded in `scanner-epg-momentum/backtest/CLAUDE.md`'s phase table as **"Derived … See parent."** The parent project is `D:\Trading Research\hawkes-ofi-impact` — the drive CLAUDE.md records as confirmed failing hardware, migrated off 2026-07-12. The local `hawkes-ofi-impact/` tree was not read for this. |
| `hawkes-ofi-impact` Phase K escalation | same provenance; not verified here. |

The profit factors that **are** reproducible from files in this checkout are
`scanner-epg-momentum/backtest/results/phase_f/val_full/run_summary.json` → **PF = 1.9194**, n = 6,004
trades, and `.../phase_f/test_full/run_summary.json` → **PF = 2.1849**, n = 611 trades. T0b's overlap
join is run against the first of those, as the largest gate run that exists here.

**Four smaller drafting items.** The first two are recorded and not corrected; the last two are
deviations this run took, each following the precedent E1 set on the identical slip two days earlier.

- DR-4 names `float_lag_ns` and `float_quality`. The columns that exist (Build F1, D31) are
  `shs_lag_ns` and `shs_quality`. Same quantity, different name.
- T3 says the round trip "is fixed at 70.98 bp / 2.512 cents". `results/phase_11/REPORT.md:72` gives
  those as the **median** round-trip cost in the named cell — a cell of 10,544 rows of which 3,363
  have a defined ratio, realized capture being non-positive on 52.86% of it. What Phase 11 and D24
  establish is that the round trip does not scale with horizon, not that it is a single number.
- §I.5 asks for a dark theme. No dark-theme chart exists anywhere in this repository's history; E1
  recorded the same slip and used the standard light theme
  (`config/fundamental_exploration.json` `chart_theme.deviation_from_brief`). Same treatment here,
  recorded in `config/relative_momentum_r0.json`.

- The brief's header writes charts to a top-level `charts/relative_momentum/r0/`. They are written
  to **`results/relative_momentum/r0/charts/`** instead. E1's brief carried the identical slip and it
  was corrected before any code ran, precisely so the repository does not gain a stray top-level
  `charts/` directory — see the E1 entry in `docs/Research-Library-Map.md` and
  `prompts/fundamental_exploration_e1.md` §7. Following that precedent rather than the brief's literal
  path; recorded in `config/relative_momentum_r0.json` `chart_theme.deviation_from_brief`.

`results/fundamental_exploration/e2/artifacts/` — which DR-3's relative-volume baseline `B_e` depends
on — is **uncommitted** on `explore/fundamental-e1` and remains uncommitted here. Recorded, not
touched.

---

## T0a (part 1) — Population and membership

`research/relative_momentum/t0a_population.py` · `artifacts/t0a_population.json`

D1 built in code from `results/phase_5/artifacts/quotes_bitmaps_all.parquet` — D15's materialization
of `momentum_events_canonical WHERE in_scope = TRUE`, reused from `config/fundamentals_f1.json` and
`config/fundamental_exploration.json` rather than re-derived. A live `SELECT` against the view was
attempted first and killed after more than ten minutes of eight-thread CPU: the view's staged
construction joins `filtered_trades` (4.9B rows) and `filtered_quotes` (3.8B rows) unconditionally for
its coverage flags, so every query against it scans both. That is the same finding
`research/fundamentals_f1/verify_event_fundamentals.py` recorded on 2026-09-12, reproduced here.

**Four assertions, all pass.**

| assertion | observed | expected |
|---|---|---|
| `in_scope = TRUE` row count | 20,951 | 20,951 |
| D1 row count (`in_scope` AND `source_file = 'file1'`) | **15,763** | 15,763 |
| `event_id` unique on D1 | 15,763 unique / 15,763 rows | equal |
| `(ticker, event_date_canonical)` unique on D1 | 0 duplicates | 0 |

The fourth matters for T0b: the gate's result files carry only `(ticker, date)`, so the join key has
to be that pair. It is a key on D1.

`in_scope` splits 15,763 `file1` / 5,188 `file2`. D1 spans **2020-01-03 to 2024-12-31**, 1,257
distinct session dates and 2,576 distinct tickers, by year: 2020 · 3,439 — 2021 · 1,932 —
2022 · 2,279 — 2023 · 3,021 — 2024 · 5,092. No 2025 event is in D1, consistent with §I.6.

**T0a part 2 — the `move_at` prior-close coverage assert — was deferred at the stop and has since
run.** Its only consumer is `move_at`, used in T2; T0b is a stopping gate and T0b fired, so the pass
was not started at the time. The erratum of 2026-09-18 needs `move_at`, so it was built then, and it
did not require the 15,763-folder tick pass originally anticipated — `event_minute_bars_v2` already
carries the quantity. **Coverage: 15,721 of 15,763 (99.73%); 42 events cannot have a tick-derived
prior close built, carried and never dropped.** Full result and the one recorded divergence from
§I.2's literal wording: **§T0a part 2 in Addendum 2**,
`research/relative_momentum/t0a2_prior_close.py`.

---

## T0b — THE OVERLAP JOIN · stopping gate

`research/relative_momentum/t0b_overlap_join.py`, `t0b2_exception_resolution.py`,
`t0b3_exception_flags.py`
`artifacts/t0b_overlap_join.json`, `t0b2_exception_resolution.json`,
`t0b3_exception_flags.json`, `t0b_gate_listable.parquet`, `t0b_gate_runs.parquet`,
`t0b_membership.parquet`, `t0b2_gate_exceptions.parquet`

Nothing under `scanner-epg-momentum/` was executed, imported or modified (§I.6). Its event-selection
rule — `backtest/data/loaders/trades.py::list_events` — was re-implemented read-only over
`data/filtered` in `research/relative_momentum/common.py`, with the same regex and the same
semantics. Both projects resolve to the **same physical archive**: `DATA_ROOT` in
`scanner-epg-momentum/backtest/data/schemas/mom_db.py` is `parents[4] / "data"`, which is
`E:/Trading Research/data`. The two populations therefore differ by selection rule, not by data
source.

"The participation gate's event set" is not one set, so three nested populations are reported.

| population | rule | n |
|---|---|---|
| **G_list** | a `data/filtered` folder whose name parses, carries a date, has `mom_pct ≥ 50.0`, and has `trades.parquet` — the largest population the backtest could ever address | **9,342** (24,723 folders scanned) |
| **G_run** | `(ticker, date)` the gate was actually executed on — every `per_event_summary.json` under `scanner-epg-momentum/backtest/results` (101 files, 8,762 rows) | **1,136** |
| **G_fired** | G_run rows with `n_pass_edges ≥ 1` | **1,120** |
| **G_pf** | the single run behind the reproducible headline: `results/phase_f/val_full`, PF = 1.9194 | **1,027** (all 1,027 fired) |

### The table, both directions

| relationship | ∩ | only left | only right | share of left | share of right |
|---|---|---|---|---|---|
| G_list vs **D1** | 5,717 | 3,625 | 10,046 | 61.20% | **36.27%** |
| G_list vs D1, on `event_id` | 5,717 | 3,625 | 10,046 | 61.20% | 36.27% |
| G_list vs `in_scope` (all source files) | 7,905 | 1,437 | 13,046 | 84.62% | 37.73% |
| G_run vs **D1** | 1,097 | 39 | 14,666 | 96.57% | **6.96%** |
| G_fired vs **D1** | 1,087 | 33 | 14,676 | 97.05% | **6.90%** |
| G_pf vs **D1** | 999 | 28 | 14,764 | 97.27% | **6.34%** |
| G_run vs G_list | 1,136 | **0** | 8,206 | 100% | 12.16% |

The `event_id` row is identical to the `(ticker, date)` row in every cell. Folder-name `mom_pct` and
canonical `momentum_pct` agree on every matched event; the join is not sensitive to which key is used.

G_run ⊆ G_list exactly: 0 events were run that the lister would not admit.

### Why D1 loses 10,046 events to the gate's lister

One reason, and only one.

| reason a D1 event is not in G_list | n |
|---|---|
| `mom_pct < 50` | **10,046** |
| any other reason | 0 |

Every D1 event the gate's lister rejects is rejected for sitting below its 50% floor. None is
rejected for a missing folder, a missing `trades.parquet`, or an unparseable name. Chart 02 shows
where that floor falls inside D1's own `momentum_pct` distribution.

### By year

| year | D1 | G_list admits | gate **run** on | gate **fired** on |
|---|---|---|---|---|
| 2020 | 3,439 | 1,100 | **0** | **0** |
| 2021 | 1,932 | 698 | **0** | **0** |
| 2022 | 2,279 | 793 | **0** | **0** |
| 2023 | 3,021 | 1,108 | 159 | 158 |
| 2024 | 5,092 | 2,018 | 938 | 929 |

The participation gate has never been executed on any event before **2023-11-17**, the val-split
start date in `scanner-epg-momentum/backtest/config/holdout_boundary.json`. Three of D1's five years
carry zero gate observations of any kind.

### The 39 gate events that are not in D1

All 39 resolve the same way: **present on the raw `momentum_events` spine (23,268 rows), not
`in_scope`.** None is off the spine. Every one of the 39 resolves to a named reason — the table has
no residue.

| reason not `in_scope` | n |
|---|---|
| instrument class `warrant` | 18 |
| instrument class `fund_product` | 5 |
| instrument class `preferred` | 4 |
| **`flag_trades_mom_outlier = TRUE`** (class is in scope) | **12** |

27 are instrument classes Mom-DB's universe rules exclude by decision — warrants (`SOUNW` ×5,
`DJTWW` ×2, `CORZW`, `CORZZ`, `CIFRW`, `BFRGW`, `AISPW`, …), preferreds (`STRC` ×4) and fund products
(`DXYZ` ×4 plus the `CONL` ETF). Read instead against the vendor reference types in
`results/phase_1b/artifacts/ticker_reference_snapshot.parquet` — the classification source of record,
never re-queried from the API — the same 39 split WARRANT 18 · CS 11 · PFD 4 · FUND 4 · ETF 1 ·
ADRC 1; `fund_product` is the class that covers both FUND and ETF.

The remaining **12** carry an in-scope instrument class (11 `common`, 1 `common_adr`) and are excluded
by a single flag, the same one in all twelve: **`flag_trades_mom_outlier = TRUE`**. Neither
`flag_bad_denominator` nor `flag_missing_event_day` is set on any of them. Their spine `momentum_pct`
runs from 724.82% (`BGLC`) to 1,720.31% (`ZJYL`), every one of the twelve above +700%.

Resolved in `research/relative_momentum/t0b3_exception_flags.py` against the `in_scope` formula in
`src/data/canonical.py` (stage t6/t7/t8), with `flag_bad_denominator` recomputed from the raw spine at
`config/phase_1b.json`'s thresholds (`prev_close_floor = 0.01`, `mom_sanity_cap = 10000`) and the
other two flags read from `results/phase_1b/artifacts/event_flags.parquet` — the same artifact the
view reads. Full lists: `artifacts/t0b2_gate_exceptions.parquet`,
`artifacts/t0b3_exception_flags.json`.

### The criterion

> **Are the participation gate's event set and D1 the same population?**

| quantity | observed |
|---|---|
| share of D1 the gate's lister would even admit | **36.27%** |
| share of D1 the gate was ever **run** on | **6.96%** (1,097 / 15,763) |
| share of D1 the gate ever **fired** on | **6.90%** (1,087 / 15,763) |
| share of the reproducible headline PF run that is inside D1 | **97.27%** (999 / 1,027) |
| **materially disjoint** | **TRUE** |

The disjointness is **one-sided and asymmetric**, and both sides of that are in the table above. The
gate's events are almost entirely Mom-DB events: 97.27% of the PF run sits inside D1, and the 28 that
do not are mostly warrants and preferreds. What does not hold is the converse — D1 is 15.4× the size
of the largest gate run that exists, the gate has been executed on 6.96% of it, and on none of it
before 2023-11-17.

`materially_disjoint` is evaluated against a rule declared inside the script — *share of D1 the gate
was ever run on < 0.50* — a stated round threshold, not a fitted one. The brief sets no numeric bar;
the number the decision is read on is **6.96%**.

**Per §I.1: the table is posted and the brief stops here.**

---

## Charts

`results/relative_momentum/r0/charts/` · `research/relative_momentum/chart_t0b.py` · standalone Plotly HTML,
one chart per file, Plotly embedded inline (never a CDN — the environment is offline, D14).

- **`01_population_funnel_by_year.html`.** Four grouped bars per event year: D1, what the gate's
  lister would admit, what the gate was run on, what it fired on. Counts labelled on every bar. The
  2020, 2021 and 2022 groups carry two bars at zero.
- **`02_gate_floor_against_d1_momentum.html`.** D1's `momentum_pct` in 60 log-spaced bins over the
  full observed range, split at the gate's `min_mom_pct = 50.0` and coloured either side of it.
  Nothing is clipped, the upper tail included. 10,046 of 15,763 events (63.7%) fall below the floor.
  `momentum_pct` appears here as a labelled diagnostic of a selection boundary — brief §I.2, D4's sole
  exception — and enters no computed quantity anywhere in this run.

---

## What the stop leaves unbuilt

Mechanical consequences of the numbers above, not recommendations.

**DR-1's candidate set does not exist for D1.** It is defined as "every D1 event whose participation
gate has fired its **first** rising edge at or before τ". That edge is on record for **1,087** D1
events and for **zero** D1 events dated before 2023-11-17. T1's concurrency distribution, T2's rank
agreement, T3's cost check and T4's random control all take the candidate set as input.

**Producing the missing edges is not inside R0's scope.** `scanner-epg-momentum` is read-only to this
brief (§I.6), so the gate cannot be executed on the other 14,676 D1 events from here; and
re-implementing `epg_replay.py`'s gate inside Mom-DB is a build, not a scoping measurement.

**Two items in §I.7 were never reached.** The liveness sweep (DR-1) and the ratcheting reading (DR-2)
both required Cooper before the T1 run. T1 did not run, so neither was consumed.

**Part II is untouched.** R1 was not authorised by the brief and nothing in it was read, planned or
computed. §II.4's slice sizes were explicitly to "follow from the overlap join"; the overlap join is
now on record.

---

## Scope boundary, restated from the brief

R0 touched no outcome variable: no forward return, no excursion, no expectancy, no cost-unit
quantity, no continuation measure (DR-5). It set no threshold on anything except the declared
`materially_disjoint` reading rule stated above. It constructed no attention score. It promoted
nothing to a universe criterion or an entry signal. It did not modify `scanner-epg-momentum`. It
touched no 2025 or non-`file1` event. `momentum_pct` entered no computed quantity.

Per §I.8: this report seeds priors. Anything tested in R1 is either declared in writing before this
report is read, or labelled exploratory.

---

# ADDENDUM — 2026-09-18

Written in answer to the read of T0b dated 2026-09-18. Nothing here restarts the brief. §T0b-4
re-measures a quantity that read draws an inference from; §T0c runs that read's §3 check, which needs
no new data pass. T1–T5 and Part II remain not run, and §4 and §5 of that read are its own open
decisions, untouched here.

## T0b-4 — the fire rate, re-measured

`research/relative_momentum/t0b4_fire_rate.py` · `artifacts/t0b4_fire_rate.json`,
`t0b4_fire_rate_per_run.parquet`, `t0b4_skipped_events.parquet`

The read's §2 infers from T0b's *run 6.96% / fired 6.90%* pair that the rising-edge logic almost never
says no. **T0b's two numbers cannot carry that inference, and the correct instrument gives a stronger
version of the same conclusion.**

Why they cannot carry it: both are a **union across 101 result files** and many gate configurations.
An event counts as fired if any one configuration ever fired on it once. That is the right measure for
what T0b used it for — *has this D1 event ever been run on / ever fired* — and the wrong denominator
for a fire rate.

Two things had to be fixed to measure it.

**The runner family.** The result tree holds two runners writing two different schemas and using two
different entry mechanisms.

| family | schema marker | entry mechanism | runs | summary rows |
|---|---|---|---|---|
| `rising_edge` | `n_pass_windows`, `mean_pass_window_sec` | EPG rising edge — `n_pass_edges` **is** the entry counter | 34 | 3,013 |
| `entry_eligible` | `n_passtofail_transitions`, `n_entry_eligible_blocks`, `gate_at_scanner_hit` | first-pass, not a rising edge | 65 | 5,581 |

The `entry_eligible` family writes `n_pass_edges = 0` on **every** row while recording nonzero
`n_passtofail_transitions` and nonzero trades on those same rows. Reading those zeros as "the gate
declined" is a category error — on this axis the family is **unavailable, not negative**, and it is
excluded from every rate below rather than counted as a decline. (Before this split, a naive pooled
read gave 63 of 101 runs with "zero fires" and a median per-run fire rate of 0.0. That number was an
artifact of the schema, not a property of the gate.)

**The skipped population.** `per_event_summary.json` has no row for an event the runner attempted and
abandoned. Those are in `skipped_events.json`, and restoring them changes the denominator.

### The fire rate

| population | n | fired | rate |
|---|---|---|---|
| `rising_edge` family, all runs, summary rows | 3,013 | 3,008 | **99.83%** |
| per-run rate: min / median / max | — | — | 0.988 / **1.000** / 1.000 |
| runs in that family with zero fires | — | — | **0** |
| `phase_f/val_full` (the PF = 1.9194 run), summary rows | 1,027 | 1,027 | **100%** |
| `phase_f/val_full`, **attempted** (summary rows + skipped) | 1,228 | 1,027 | **83.63%** |

**The read's §2 conclusion holds and is understated.** On the family where the rising edge is the
entry mechanism, the gate fires on 99.83% of the events it sees, never below 98.8% in any single run.
Whatever selectivity the gate contributes, it is not in the rising-edge test.

### Where the selectivity actually sits, in the headline run

201 of 1,228 attempted events (16.4%) never reached the gate:

| skip reason | n |
|---|---|
| `setup_filter_fail` | **88** |
| `missing_prev_close` | 81 |
| `error` | 13 |
| `insufficient_trades` | 12 |
| `no_t_event` | 6 |
| `insufficient_quotes` | 1 |

**`setup_filter_fail` is the largest single reason, and no code in this checkout emits that string.**
A grep over `scanner-epg-momentum/**/*.py` finds `missing_prev_close` and `no_t_event` in the runners
but no `setup_filter_fail` anywhere. That is consistent with the repository's own record — its
`backtest/CLAUDE.md` says the setup filter was "**Removed from initial entry gate.** Computed but does
not block first entry" — but the consequence is worth stating plainly: **the population behind
PF = 1.9194 was filtered by a rule that is no longer in the code, and 88 events were removed by it.**
Not re-derivable from this checkout.

## T0c — Phase 11 re-sliced on the gate-admissible domain

`research/relative_momentum/t0c_phase11_reslice.py`, `chart_t0c.py` ·
`artifacts/t0c_phase11_reslice.json`, `t0c_named_cell_sliced.parquet` · charts 03, 04

The read's §3 check, run as specified: no new data pass. Phase 11's
`results/phase_11/artifacts/t7_cost_vs_capture.parquet` is already per
(ticker, event_date, latency, hold); this re-slices its named cell.

**Two assertions, both pass.** The named cell (`det_segment = rth`, latency 5, hold 30) reproduces
**n = 10,544**, matching `t7_cost_vs_capture.json` `named_cell.n`; and all 10,544 rows resolve into D1,
0 outside.

### What this cannot settle, stated before the numbers

Phase 11's markout is a **fixed-horizon** trade: enter at the detection anchor + 5 min latency, hold
30 min, exit. The gate's PF is a **different trade**: rising-edge entry, window-close exit, median hold
**52 seconds** in the val_full run. Re-slicing the population does not make them the same trade. This
is a population diagnostic, not a reconciliation.

> **SUPERSEDED by §T0c2 (Addendum 2).** Every slice in this table that uses `momentum_pct` is built
> on a variable brief §I.2 bars from bucketing. The causal re-run reverses the sign: S5's +66 bp
> becomes −1,054 bp, S3's +134 bp becomes −1,026 bp. This table is retained as the record of what the
> defective specification produced; read §T0c2's table instead.

### The table — all figures in basis points

| slice | n | markout p25 | **markout median** | markout p75 | share ≤ 0 | rt_cost median | **net median** | share net ≤ 0 |
|---|---|---|---|---|---|---|---|---|
| S0 named cell, as published | 10,544 | −606 | **−164** | +208 | 63.1% | 70.98 | **−263** | 67.1% |
| S2 mom < 50, before 2023-11-17 | 5,065 | −612 | **−237** | +68 | 70.3% | 53.50 | **−322** | 74.9% |
| S3 mom ≥ 50, before 2023-11-17 | 1,843 | −587 | **+134** | +881 | 45.8% | 82.75 | **+53** | 48.7% |
| S4 mom < 50, on/after 2023-11-17 | 2,575 | −603 | **−204** | +105 | 67.7% | 84.82 | **−324** | 73.3% |
| **S5 gate-admissible (both)** | 1,061 | −619 | **+66** | +799 | 47.4% | 106.30 | **−57** | 52.6% |
| S6 gate lister admits, on/after | 1,061 | −619 | **+66** | +799 | 47.4% | 106.30 | **−57** | 52.6% |
| S7 the `phase_f/val_full` PF population | 473 | −634 | **+92** | +933 | 46.1% | 112.57 | **−17** | 50.4% |

S6 is identical to S5 because on D1 the gate lister's only rejection is `mom_pct < 50` (T0b). S7 is 473,
not 999, because the named cell's RTH / defined-entry-and-exit conditions cover 473 of the PF run's 999
D1 events.

**Three readings, in order.**

**The pre-cost median flips, and it is the momentum floor that flips it.** S0's −164 bp becomes +66 bp
on the gate-admissible domain and +92 bp on the PF population itself. Decomposed, the two mechanisms do
not contribute equally: the momentum floor alone (S3) gives **+134 bp**, while the date boundary alone
(S4) gives **−204 bp** and does not flip. The recent-regime boundary works *against* the flip —
S3 +134 → S5 +66.

**Net of cost it does not flip, and cost rises on exactly that domain.** Median round-trip cost goes
70.98 bp (S0) → 106.30 (S5) → 112.57 (S7), and the net median stays negative on both gate slices
(−57 bp, −17 bp) with the share of non-positive net at 52.6% and 50.4% — a coin flip. S3 is the only
slice in the table with a positive net median. **This is T3's concern arriving before T3 did:** the
gate's domain does select more expensive names.

**The slicing variable is not known at decision time.** `momentum_pct` is a prior-close-to-day's-high
measure (D4; brief §I.2, which bars it as a bucketing variable for precisely this reason). Conditioning
an outcome on it selects sessions that went up a lot, so a positive shift in a forward markout is what
that conditioning does mechanically. **It cannot be read as "extreme-momentum names behave better."**

The distinction that matters for what this implies about the gate: the gate's **live entry logic** is
causal (scanner ≥ 30% intraday, `gap ≥ 30%`, EPG rising edge). Its **backtest population** is not — the
`min_mom = 50.0` floor reads `momentum_pct` off the event folder name, a day's-high quantity. So this
is backtest sample selection on a lookahead variable, not a lookahead in the trading rule. Recorded as
an observation about the population, not as an evaluation of the gate.

### A12 — cross-session flag split

`flag_cross_session_extreme` carried per D4 Amendment A12; untrimmed is primary, flagged rows are their
own row and are never dropped.

| slice | n | markout median | net median |
|---|---|---|---|
| S0 flag clear | 9,831 | −173 | −276 |
| S0 **flagged** | 713 | +11 | −28 |
| S5 flag clear | 866 | +22 | −95 |
| S5 **flagged** | 195 | **+311** | **+241** |
| S7 flag clear | 373 | +61 | −78 |
| S7 **flagged** | 100 | **+239** | **+213** |

The flip concentrates in the flagged set. On S5 the flagged median is +311 bp against +22 bp clear, and
the flagged subset is the only place in this addendum where a net median is solidly positive. A12 exists
because a corporate action between two sessions changes the basis across the boundary; 195 of S5's 1,061
rows carry that flag.

### Charts

- **`charts/03_markout_ecdf_by_slice.html`.** ECDF of pre-cost markout in bp, five slices, with the
  x = 0 line and the y = 0.5 line drawn — a curve's median is where it crosses the dotted line, so the
  flip is read off the whole distribution rather than from a summary. n and median in every legend
  entry. No observation dropped or clipped; the ±3,000 bp window is for legibility and the curves run
  flat past it.
- **`charts/04_net_markout_ecdf_by_slice.html`.** The same for `markout − rt_cost`, using Phase 11's
  own per-row `rt_cost` rather than a scalar.

S7 is in the tables but not on the charts — a sixth series would exceed the validated five-colour
palette, and it sits between S3 and S5 on both panels.

## Not addressed here

§4 of the read (rescope to the gate-admissible domain, or re-derive the gate causally against all of
D1) and §5 (the Project-docs citation fix, and the `prompts/relative_momentum_r0.md` stub drift) are
both marked as Cooper's open decisions in that document. Neither is acted on here.

---

# ADDENDUM 2 — 2026-09-18 — the causal re-run

Mandated by the erratum to the 2026-09-18 read: *"This entire check must be rerun with
`move_at(e, τ)` … before any reading of 'does extreme momentum predict continuation' can be trusted."*
That is the one bounded instruction in the erratum and it is what this addendum does. The erratum's
Path A / Path B consequence is a recorded preference, not an instruction, and is not acted on.

**The re-run reverses T0c's direction.** T0c's table is superseded by the table below on every slice
that used `momentum_pct`. T0c's rows remain in this report as the record of what the defective
specification produced.

## T0a part 2 — the tick-derived prior session close, finally built

`research/relative_momentum/t0a2_prior_close.py` · `artifacts/t0a2_prior_close.json`,
`t0a2_prior_close.parquet`

`move_at` needs a prior close, so the half of T0a the stop deferred is now run.

**Reused, not re-derived.** The last RTH minute bar's `last_price` at `session_offset = -1` from
`event_minute_bars_v2` — verbatim the construction `research/phase_12/t2b_band_arithmetic.py` uses for
LULD band arithmetic and `research/reg_sho_201/t1_trigger_check.py` reuses for Rule 201, both of which
name it D4-safe. That table is Phase 6b's extended-day tick aggregate; D5 Amendment A11 records that
reusing it needs no citation. It covers exactly the 15,763 `(ticker, event_date_canonical)` pairs that
are D1.

**Coverage, as a first-class number per T0a:** **15,721 of 15,763 (99.73%)**. **42 events cannot have a
tick-derived prior close built** — 2020 · 4, 2021 · 5, 2022 · 10, 2023 · 8, 2024 · 15. They are carried
in the artifact with `prior_close_available = FALSE`, never dropped. None is non-positive. All 10,544
rows of Phase 11's named cell resolve, so the re-run below has no censored rows.

**One divergence from the brief's literal wording, recorded not taken silently.** §I.2 specifies the
closing print be resolved by Phase 10c Amendment 6's `{8, 15}` auction override. `event_minute_bars_v2`
is Phase 6b output and predates that amendment, so its `segment` is assigned on the timestamp rule
alone. Amendment 6's own census bounds the affected population at **291 near-close prints against 25.2M**
in the cohort, and this construction takes the last RTH *minute bar* rather than a specific print, so
the residual is smaller still. The A6-exact alternative is a fresh 15,763-folder tick pass over
`data/filtered`. Named residual; say so if the exact version is wanted.

## T0c2 — the check re-run on `move_at`

`research/relative_momentum/t0c2_move_at_reslice.py`, `chart_t0c2.py` ·
`artifacts/t0c2_move_at_reslice.json`, `t0c2_named_cell_move_at.parquet` · charts 05, 06

> `move_at_entry = (entry_price − prior_close) / prior_close`

evaluated at τ = the named cell's own entry instant, the detection anchor plus 5 minutes of latency.
`entry_price` is Phase 11's own column and is known at τ by construction, so **nothing after the
decision enters the slicing variable**. Both terms are tick-derived (D4). Two assertions pass: the cell
is n = 10,544, and `move_at_entry` is defined on all 10,544.

**A12 applies to the slicing variable itself.** `move_at` is a cross-session ratio whose denominator
spans (T−1, T0), so `flag_cross_session_extreme` is carried and every headline is reported with and
without it, untrimmed first.

### How much of T0c's flip population was hindsight

|  | `move_at_entry` < 50% | `move_at_entry` ≥ 50% |
|---|---|---|
| `momentum_pct` < 50 | 7,630 | 10 |
| **`momentum_pct` ≥ 50** | **2,577** | **327** |

Of the 2,904 events T0c's momentum slice selected, **2,577 — 88.7% — had not moved 50% at decision
time.** They got there later in the session. The causal population is 337 events, **3.2%** of the cell.
That is the lookahead, counted.

### The table, on the causal measure

| slice | n | markout p25 | **markout median** | markout p75 | share ≤ 0 | rt_cost median | **net median** | share net ≤ 0 |
|---|---|---|---|---|---|---|---|---|
| S0 named cell, as published | 10,544 | −606 | **−164** | +208 | 63.1% | 71.0 | **−263** | 67.1% |
| C2 move < 50%, before 2023-11-17 | 6,694 | −587 | **−166** | +196 | 63.6% | 59.5 | **−255** | 67.2% |
| C3 move ≥ 50%, before 2023-11-17 | 214 | −2,093 | **−1,026** | +348 | 69.5% | 134.3 | **−1,230** | 71.3% |
| C4 move < 50%, on/after 2023-11-17 | 3,513 | −583 | **−142** | +225 | 61.5% | 92.5 | **−259** | 66.6% |
| **C5 move ≥ 50%, on/after — the causal analogue of S5** | **123** | −2,145 | **−1,054** | +499 | 69.1% | 110.7 | **−966** | 68.6% |
| C7 the PF population (membership, not a move slice) | 473 | −634 | **+92** | +933 | 46.1% | 112.6 | **−17** | 50.4% |

**The sign reverses.** T0c's S5 read **+66 bp** gross and −57 bp net. Its causal analogue C5 reads
**−1,054 bp** gross and **−966 bp** net. The same reversal holds pre-boundary: S3 **+134** → C3
**−1,026**. Nothing in the causal table has a positive median on either measure.

C5 is n = 123 and C3 is n = 214. Both are above the config's display floor of 20 but they are small
populations and are read as such — the causal "already moved ≥ 50%" cohort is only 3.2% of the cell.

C7 is unchanged from T0c's S7 because it is a *membership* slice, not a move slice: it is the events
the PF run traded. Its positive gross median therefore still carries the `min_mom = 50` lookahead in the
gate's own backtest population — it is listed for continuity, not as a surviving result.

### The response curve — chart 05, the primary object, no threshold set

| decile of `move_at_entry` | range | n | markout median | rt_cost median | **net median** | share net ≤ 0 |
|---|---|---|---|---|---|---|
| 0 | −34.5% … +21.0% | 1,055 | −133 | 121.8 | **−315** | 69.1% |
| 1 | 21.0 … 24.6% | 1,054 | −105 | 87.7 | **−217** | 64.6% |
| 2 | 24.6 … 26.8% | 1,054 | −101 | 68.6 | **−213** | 66.7% |
| 3 | 26.8 … 28.3% | 1,055 | −105 | 56.3 | **−166** | 63.5% |
| 4 | 28.3 … 29.5% | 1,054 | −108 | 46.4 | **−169** | 63.6% |
| 5 | 29.5 … 30.6% | 1,055 | −84 | 43.6 | **−129** | 65.7% |
| 6 | 30.6 … 31.9% | 1,054 | −154 | 51.1 | **−219** | 67.1% |
| 7 | 31.9 … 34.3% | 1,054 | −224 | 65.9 | **−289** | 67.9% |
| 8 | 34.3 … 39.0% | 1,054 | −400 | 85.6 | **−518** | 71.4% |
| 9 | 39.0 … 2,043% | 1,055 | −751 | 107.7 | **−883** | 71.2% |

**Every decile is negative on both measures, and above decile 5 the curve is monotone in the wrong
direction** — net median −129 bp at decile 5 falling to −883 bp at decile 9, a factor of 6.8. The more
of the move that has already happened at decision time, the worse the forward markout. Round-trip cost
moves the same way over the top half (43.6 → 107.7 bp), so gross and net degrade together.

The mass of the universe sits in a narrow band: deciles 1–8 span +21% to +39%, which is the detection
threshold's own neighbourhood. The causal variable barely separates the cohort except in the tails.

### A12 — and what happens to the erratum's one lead

The erratum carried one exploratory lead: the cross-session-flagged subset at S5 netting +311 bp
against +22 bp clear, "the only solidly positive net cell." On the causal variable that split becomes
far wider, and its character becomes legible.

| slice | n | markout median | **net median** | share net ≤ 0 |
|---|---|---|---|---|
| S0 named cell — flag clear | 9,831 | −173 | −276 | 68.4% |
| S0 named cell — **FLAGGED** | 713 | +11 | −28 | 51.5% |
| **C5 — flag clear** | **84** | **−1,600** | **−1,659** | **87.5%** |
| **C5 — FLAGGED** | **39** | **+1,094** | **+863** | **29.0%** |
| C7 — flag clear | 373 | +61 | −78 | 52.4% |
| C7 — **FLAGGED** | 100 | +239 | +213 | 43.3% |

**The entire positive result on the causal gate-analogue slice is inside the flagged 39 events.** With
them, C5 nets −966 bp; the 84 unflagged events net **−1,659 bp** and are negative 87.5% of the time.
`move_at_entry` reaches **2,043%** at its maximum, which is not a price move.

`flag_cross_session_extreme` is a magnitude flag, not a corporate-action classifier (D4 A12's own
wording), so this does not establish that those 39 are corporate actions. What it does establish is that
the lead points at the population A12 exists to isolate, and that it is 39 events. It is not carried
forward here as a lead; on this evidence it is a candidate artifact, and separating the two requires a
corporate-action source the archive does not have.

### Charts

- **`charts/05_response_curve_move_at_entry.html`.** Median forward markout and net markout against
  equal-population deciles of `move_at_entry`, interquartile band drawn around each median, n on every
  bucket, median round-trip cost on the same axis so the gross-to-net gap is visible rather than
  asserted. No threshold anywhere on it.
- **`charts/06_markout_ecdf_causal_slices.html`.** The chart-03 encoding on the causal variable, built
  to be read directly against it. On chart 03 the gate-admissible median sits right of zero; on chart 06
  it does not. **The pair is the finding.**

### What this does and does not establish

It establishes that T0c's flip was an artifact of the slicing variable, that a decision-time measure of
the same quantity reverses the sign, and that the reversal is monotone across the top half of the causal
range. Within Phase 11's fixed-horizon trade — anchor + 5 min latency, 30 min hold — **more move already
achieved predicts a worse forward markout, gross and net.**

It does not measure the gate's trade, which is a rising-edge entry with a window-close exit and a
52-second median hold. Phase 11's horizon is 30 minutes. Nothing here reconciles PF = 1.9194, and
nothing here is a test of the gate.

## Still not addressed

The erratum's Path A / Path B consequence, and §5 of the original read (the Project-docs citation fix
and the `prompts/relative_momentum_r0.md` stub drift). Both are recorded preferences or open decisions
in Cooper's own documents and neither is acted on here. T1–T5 of the brief and Part II remain not run.
