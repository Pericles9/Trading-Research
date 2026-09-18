# Relative momentum R0 — qualification-layer scoping — REPORT

**Branch:** `explore/relative-momentum-r0` · **Config hash:** `5fae280c7fed`
**Status: STOPPED AT T0b.** T0a (part 1) and T0b ran. T0a (part 2), T1, T1c, T2, T3, T4 and T5 did
not run.
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

**T0a part 2 — the `move_at` prior-close coverage assert — did not run.** It is a 15,763-event pass
over `data/filtered` to build the tick-derived prior session close, and its only consumer is
`move_at`, which is used in T2. T0b is a stopping gate and T0b fired; the pass was not started.
`research/relative_momentum/t0a2_prior_close.py` does not exist. This is an explicitly unfinished part
of the brief, not an oversight.

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
