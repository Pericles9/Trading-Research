# Fundamental exploration E1 — descriptive baseline

**Date:** 2026-09-14 · **Type:** exploration brief. Minimal task list, by Cooper's call.
**Status:** **not a phase.** No phase number, no pre-registered decisions, no escalation rows. It records
no decision, tests no hypothesis, and produces no finding. It ends at a report of pictures.

**Outputs:** `results/fundamental_exploration/` and `charts/fundamental_exploration/`, chart subfolders per
task. Branch `explore/fundamental-e1`.

---

## 0. The scope line, stated first because everything depends on it

**Descriptive only. No fundamental column touches an outcome variable.** No excursion, no expectancy, no
net-of-cost anything, no post-`t0` return in any form. DF-6 is not being tested, relaxed, or approached —
this work stays entirely on the other side of it, which is why it needs no written sentence and no gate.

"In relation to volume and other things" is read as **event characteristics, not event results.** Volume,
print count, price level, duration, session, year. What the event *was*, not what it *paid*.

Crossings that would be outcome tests are listed in §5 and deliberately not run.

---

## 1. Variables

### Fundamental side — from `event_fundamentals`

| variable | carried as |
|---|---|
| `shs_shares_outstanding` | **as filed, not split-adjusted, a lower bound on float.** Never labelled "float" in any chart, column or sentence. |
| `shs_lag_ns`, `shs_quality` | staleness is a variable, not a footnote |
| `flg_last_form`, `flg_lag_ns`, `flg_n_filings_24h`, `flg_n_filings_72h`, `flg_dilution_form_before_t0`, `flg_quality` | filing proximity |
| `spl_n_splits_365d`, `spl_reverse_split_365d`, `spl_last_split_ratio` | split history |
| `si_shares_short`, `si_lag_ns`, `si_quality` | short interest — heavily lagged by construction, descriptive only |
| `fin_*` | **excluded.** Deferred per amendment F1-A1. Nothing here earns the element mapping. |

**No market cap is constructed.** Shares outstanding is carried raw. The size picture comes from the
two-way shares-outstanding × detection-price table in E1-T3, which puts the two axes side by side without
ever multiplying them into a level that would need the split correction, the price basis and the
float-versus-outstanding caveat all to be right at once.

### Tape side — all tick-derived, per D4

Detection price at `t0` · event volume in shares and notional over declared windows · print count at `t0` ·
median inter-trade interval · session (pre-market / regular hours / after hours) · year · ticker.

**Spine OHLC and volume columns are not used.** D4, unchanged.

### One caveat that applies to every task using share counts

`shs_shares_outstanding` is **as filed** and wrong by the split factor after any reverse split. Reverse
splits are routine in this corner of the market. Every task that uses the share count either applies
`spl_last_split_ratio` and reports the corrected figure alongside the raw one, or states in the panel that
the cohort contains no reverse split. Silently using the raw count is the adjustment-basis mistake this
programme has already paid for once.

---

## 2. Tasks

**E1-T0 — Join and assert membership.**
Join `event_fundamentals` to the canonical spine. Assert in code: exactly **20,951** rows, `event_id`
unique, and set equality against `momentum_events_canonical WHERE in_scope = TRUE` **in both directions**.
This is the one piece of ceremony kept from F1, and it is kept because equal counts with different
membership is the defect that has actually happened here, twice.

**E1-T1 — Univariate distributions.**
Every variable in §1. The `unavailable` share stated in the same panel as the distribution, never in a
caption. Log axes where the range demands them. No summary statistic appears anywhere without its
distribution above it.

**E1-T2 — Coverage as a variable, not a filter.**
Coverage share per group by year. The SEC-sourced groups (`flg_`, `shs_`) **must not** show the 2022–23
vendor coverage cliff — they have no subscription behind them. If they do, **stop**: that is a build defect,
not a property of the data. Everything downstream runs **within year**, because coverage is collinear with
the calendar and therefore with regime.

**E1-T3 — Shares outstanding × detection price, two-way.**
Event counts by shares-outstanding decile × detection-price decile. Report cell counts. This is the size
picture, and it is a table rather than a product.

**E1-T4 — Fundamentals against volume.**
Event volume, and turnover as a fraction of shares outstanding, by shares-outstanding decile — **within
year, within price decile.** Turnover built on shares outstanding is a **lower bound** and valid only as an
ordinal ranking, never as a level. Label it that way in the axis, not the caption.

**E1-T5 — Filing proximity landscape.**
Form-type mix of the nearest prior filing · time-since-filing distribution · dilution-flag rate by year and
by price decile. Descriptive only — no continuation measure, no "events with filings did X" sentence.

**E1-T6 — Reverse-split cohort.**
Everything above, split by `spl_reverse_split_365d`. One flag, no construction, real mechanism, and likely
the sharpest-looking cut in the table — which is exactly why it gets its own task instead of being buried
as a facet where it would read as a discovery.

**E1-T7 — Collinearity map.**
Association among the fundamental variables, and each of them against detection price. The point is to find
out **how much of the fundamental layer is a price split wearing different clothes** before anything is
built on top of it. Phase 11 already established that net edge is a function of detection-price level; if
the fundamental variables are mostly restating price, that should be visible here for the cost of one pass.

**E1-T8 — Report.**
`results/fundamental_exploration/REPORT.md`. Describes the pictures. **No interpretation, no findings
section, no recommendations.** Cooper reads.

---

## 3. Conventions carried over

Dark theme · charts grouped in per-task subfolders, never dumped flat · distribution before any aggregate ·
outliers flagged, never deleted · `unavailable` and zero are different states and never collapsed · the
agent describes the picture, Cooper decides what it means.

---

## 4. What this does not do

- Does not construct market cap, float, or any derived ratio other than the ordinal turnover in E1-T4.
- Does not touch `fin_`.
- Does not use the vendor float endpoint. DF-1 stands.
- Does not put any fundamental column against any outcome.
- Does not filter the population on coverage.
- Does not produce a finding.

---

## 5. Out of scope here — the crossings that would need DF-6's sentence first

Recorded so the follow-on is scoped rather than improvised: shares-outstanding decile against net
expectancy · dilution flag against continuation and flip timing · reverse-split cohort against excursion ·
short interest against the bear leg. Each of those is a partition test, needs a population-scale outcome
variable that does not yet exist, and needs the written sentence naming the decision it would change.
**None of them run under this brief.**

---

## 6. One risk worth naming

**Exploration seeds priors.** After E1, no partition can honestly be described as pre-registered unless it
was declared before E1 was read. So: E1 is recorded as **documentation**, and any partition tested later is
either declared in writing before this report is read, or labelled exploratory when it is tested. Cheap to
observe now, impossible to recover later.

---

## 7. Deviations from this brief's literal text, resolved at drafting/T0 time

Per this repo's own reuse-before-build and "cite repo paths, mark unverified" discipline, two lines above
were checked against actual repo state before any code ran and did not hold:

- **§3 "Dark theme."** No dark-theme chart exists anywhere in this repo's history. Every phase's
  `chart_common.py` (phase_6, phase_8, phase_9, phase_11, phase_13) and `fundamentals_f1`'s inline chart
  scripts use the same validated **light** palette (`INK #0b0b0b` text on `SURFACE #fcfcfb`, `CAT5`
  categorical set, CVD-checked) — including `phase_13`, drafted the same day as this brief. Treated as a
  drafting slip, not a new instruction; **E1 charts use the established light palette**, copied by value
  into `research/fundamental_exploration/chart_common.py` per the repo's own copy-not-cross-import
  convention.
- **Output paths.** "`results/fundamental_exploration/` and `charts/fundamental_exploration/`" read
  literally would create a new top-level `charts/` directory. No other phase or task directory in this
  repo has one — every one of them (including `fundamentals_f1` and `phase_13`, both current) nests
  `charts/` under its own `results/<name>/` directory. Treated as shorthand, not a new structural
  convention; **charts live at `results/fundamental_exploration/charts/<task>/`.**

Neither correction changes any task's scope, variable list, or the descriptive-only boundary in §0.

## 8. Context noted at T0 time, not acted on

`phase/13` (branch, not yet merged to `master`) ran a related fundamental-partition test (T3: `flg_dilution`,
share turnover, `spl_reverse_split`, cross-cut by detection-price decile) against a population-scale outcome
variable, and hit a **HARD STOP on 2026-09-14** — a look-ahead defect in that outcome's window construction
(`t1_build_p0.py`), affecting every P0/T2/T3 number already reported there. That defect is isolated to
`phase/13`'s own outcome computation (`event_minute_bars_v2` MFE/MAE at a horizon); E1 computes no outcome
and reads none of `phase/13`'s artifacts, so nothing here is affected by it. Recorded because the territory
overlaps (same `event_fundamentals.parquet`, same three fundamental splits) and because §6's own caution
about exploration seeding priors is worth reading against work already sitting, stopped, on that branch.
