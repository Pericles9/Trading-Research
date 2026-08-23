---
tags:
  - type/phase-amendment
  - domain/strategy
  - project/src-core
  - status/draft
created: 2026-08-23
phase: 10c
amends: Phase-10c-Prompt.md
standard: Agent Prompt Standard v1.3
---

# Amendment A1 to Phase 10c

**Carried into the prompt. Not an informal instruction.** This document supersedes the
named sections of `Phase-10c-Prompt.md`. Where the two disagree, this document wins. Read
both before running anything.

Issued in response to the satisfiability audit of 2026-08-23, which returned PASS / FAIL /
FAIL / CANNOT EVALUATE. The audit halted correctly. Items A1.1 through A1.9 below resolve
every finding.

---

## A1.1 — Two classes of decision value

The original §5 table treated all eight unfilled values identically. That was wrong. They
divide into two classes with different provenance and different timing, and conflating them
is what made the audit unsatisfiable.

### Class M — Measurement-derived

Set **after Stage 0** (A1.2), by reading the interval landscape. These describe the shape
of the data and cannot be reasoned to from first principles.

| ID | Value | Read from |
|----|-------|-----------|
| D1 | `D1_sweep_floor_us` | Where the sub-microsecond mode ends |
| D2 | `D2_max_cutoff_ms` | Where the candidate intraburst peak sits |
| D11 | `D11_grid_ceiling_min` | Where clipped-window fraction becomes disqualifying |

### Class E — Economically derived

Set **before Stage 0**, from the cost and latency model. These are statements about what is
tradeable, not about what is in the data. **They must be locked before any sub-burst exists.**

| ID | Value | Derives from |
|----|-------|--------------|
| D4 | `D4_median_precision_factor` | Estimator precision preference (low sensitivity — see A1.3) |
| D7 | `D7_threshold_lo_ms`, `D7_threshold_hi_s` | Interval above which a gap is not "inside a burst" |
| D8 | `D8_min_median_duration_s` | Realistic pipeline latency |
| D9 | `D9_slope_max` | Coupling tolerance (natural anchors at 0 and 1) |

**Guidance on Class E, for Cooper only. The agent does not act on this section.**

D8 is a floor on median sub-burst duration. Below your realistic pipeline latency you cannot
act on the object's boundaries at all, and consecutive sub-bursts are not distinguishable at
decision time. §4.2 condition 4 of the program doc states that sub-second signals during a
burst are fiction with retail-grade execution and that 30-second-to-5-minute horizons
survive modest latency. That is a wall-clock statement and it is the derivation.

D7 bounds the threshold interval itself. Its upper bound is the largest inter-trade gap you
would still call "inside a burst" — if the threshold is 30 seconds, a 25-second silence
counts as burst interior, which is incoherent for a scalp. Its lower bound is set relative
to D1 (see A1.4).

D9 measures how much of the threshold's location is contributed by the window rather than
the data. It has natural anchors: 0 means the threshold is a structural property of the
tape, 1 means it is a restatement of the kernel duration. The retired count-gate used 0.35
as its log-log slope bar; that precedent exists but carries no authority here.

### The locking rule

**Class E values are frozen at Stage 0 approval and do not move again.**

If Stage 1 halts on D7 or D8, or Stage 2 halts on D9, **the correct response is to record
the finding and stop.** Revising a gate threshold after seeing the output it judged is not
an amendment — it converts the gate into a description. Any such revision requires a new
phase number and a new pre-registration, not a patch to this one.

**Cooper may override any value at any point.** The agent does not refuse and does not
argue. It records.

Any mid-run change to a Class E value is written to `results/phase_10c/change_log.json`
before the change takes effect, capturing: the field, its prior and new value, the wall-clock
timestamp, the stage and task in progress, and **which outputs already existed when the
change was made**. That last field is the one that matters — it is what lets a later reader
tell a pre-registered threshold from a revised one.

The digest reports whether any Class E value was changed after its stage's output existed.
It reports this as a fact, with no evaluative language attached.

---

## A1.2 — New Stage 0: interval landscape measurement

Inserted before Stage 1. Amends §7.

**Purpose:** produce everything needed to set Class M values, and nothing else.

### Hard constraints on Stage 0

- **Stage 0 produces no sub-bursts.** No threshold is selected. No void parameter is
  computed. No normalisation window is applied.
- **No interval pooling across events.** Pooling on physical time across events is a
  category error — these events do not share a clock. Every histogram is per event. Where a
  population-level statement is needed, report the **distribution across events of a
  per-event summary quantity**, never a merged histogram.
- Stage 0 ends in a **mandatory halt** for Cooper's disposition. It does not flow into
  Stage 1.

### Tasks

**T0.1 — Raw interval landscape.** Per event, on the dev sample: log-interval histogram of
raw (unaggregated) trade intervals, bin width 0.1 log units. Report the distribution across
events of: location of the leftmost mode, location of the first local minimum right of it,
and the fraction of intervals falling below that minimum. Chart: per-event histograms for
ten representative events, plus the across-event distributions of those three summary
quantities.

**T0.2 — Sweep floor sensitivity.** Recompute T0.1 with candidate aggregation floors
spanning 1µs to 10ms in decade steps. Report, per candidate floor: fraction of raw prints
absorbed, and the resulting location of the leftmost surviving mode. **Report all
candidates. Do not recommend one.**

**T0.3 — Candidate intraburst peak location.** For each candidate floor from T0.2, report
the across-event distribution of the largest peak location in the aggregated histogram.
This is the quantity D2 must sit above.

**T0.4 — Print density.** Distribution across events of prints per minute, by segment,
including within-event variation across the session. Feeds the D4 derivation.

**T0.5 — Clipped-window fraction.** For candidate kernel durations across the full base-2
grid out to 512 minutes, report the fraction of intervals whose centered window would be
clipped by a session boundary, as a function of kernel duration and time of session. This is
the measurement that bounds D11.

**T0.6 — Detection anchor variant migration.** Count events whose detection segment
(pre-market versus regular hours) differs between the poll0 and poll60 anchor variants, and
report the full migration matrix across all five variants. Cheap query, resolves A1.6.

**T0.7 — Population counts.** Report in-scope event counts under each candidate population
definition, with the Stage 1 and Stage 3 compute estimate for each. Resolves A1.7.

**T0.8 — HALT.** Produce the Stage 0 digest and stop. Do not begin Stage 1.

---

## A1.3 — D4 sensitivity, folded into Stage 0

`D4_median_precision_factor` is a researcher preference rather than a data reading, but its
consequences are a data question. Add to T0.4: report the derived minimum print count and
the resulting `too_few_prints` fraction at candidate factors of 1.1, 1.2, 1.3 and 1.5, at
the 4-minute kernel.

If the `too_few_prints` fraction is materially flat across that range, D4 is low-sensitivity
and can be set by preference. If it is steep, D4 is load-bearing and needs its own decision.
**Report which. Do not recommend a value.**

---

## A1.4 — Correction of check 4 (audit finding C1)

The audit is correct and the original condition was a mechanism error on my part.

The maximum cutoff value bounds **where the intraburst peak may sit**, not where the
threshold lands. The threshold is a trough to the *right* of that peak, and in the source
method it routinely sits above the cutoff — that is the entire point, since the trough
separates the intraburst mode from the interburst mode. The original §6 check collapsed
"ceiling on the peak search" into "ceiling on the answer," which inverts the mechanism and
confines the threshold to a band that cannot contain a tradeable value.

**§6 check 4 is replaced in full by:**

1. `D2_max_cutoff_ms` exceeds `D1_sweep_floor_us` by at least two orders of magnitude.
2. `D7_threshold_lo_ms` exceeds `D1_sweep_floor_us` by at least one order of magnitude. A
   threshold sitting near the aggregation floor collapses the event into a single sub-burst.
3. No relation between D7 and D2 is asserted or checked. The threshold sits above the
   intraburst peak by construction.

**Add to the §12 digest contract**, as a reported quantity and not a gate:

```
implied_min_intervals_per_subburst = D8_min_median_duration_s / D7_threshold_hi_s
```

If the chosen D7 and D8 imply that a median sub-burst must contain several hundred
intervals, that is worth seeing before the run rather than discovering after it. **Report
the number. Do not evaluate it.**

---

## A1.5 — Kernel grid alignment (audit finding C2)

The audit is correct: D5's 5-minute anchor and D6's {1, 5, 30} set are off the base-2 grid,
so the Stage 2 slope test cannot be read against Stage 3 rung-for-rung.

- **D5 is amended to 4 minutes.**
- **D6 is amended to {1, 4, 32} minutes.**
- D10 is unchanged: geometric, base 2, from 1 minute.

The 5-minute figure was a chosen constant with no economic content behind it. Moving it to
4 places all three Stage 2 kernels on the Stage 3 grid at rungs 0, 2 and 5.

---

## A1.6 — Dev sample and detection anchor

**Dev sample.** §7's parenthetical merged two different objects. It is amended to:

> the pinned 50-event development sample `dev_v4_primary`, stratified by `t0_print_count`
> decile

The "momentum percentage decile" wording described `dev_sample_v3.json` and is **struck**.
v3 is not used in this phase; it carries no detection anchors and deriving them is not a
task here.

Print-count stratification is the correct axis for this phase and not merely the available
one: sweep aggregation (D1) bites hardest where print density is highest, and the
fragmentation mode that ended v4 is a print-density phenomenon. Stratifying on print count
guarantees coverage across exactly the axis where D1 changes behaviour.

**Sidecar events.** The 6 flagged events in `dev_v4_primary` are **carried, labelled, and
reported separately** in every dev-sample distribution. They are not excluded and not
silently merged.

**Detection anchor.** Resolved by T0.6. Standing preference, subject to that result:
**poll0**, on the grounds that detection latency is a cost question belonging to Phase 11
and 12, not a structural-measurement question belonging here. If T0.6 shows material
segment migration across variants, the choice becomes a decision with its own D-number
rather than a default.

---

## A1.7 — Population definition

Resolved by T0.7. Note the cost asymmetry the original prompt underspecified: **Stage 1 is
one kernel; Stage 3 is the population times N kernels.** The two-order-of-magnitude concern
lands almost entirely on Stage 3.

The population definition and the Stage 3 scope are therefore **two separate decisions**,
both taken at Stage 0 approval:

- `D14_population` — the in-scope event set for Stage 1 headline numbers.
- `D15_stage3_scope` — full population or stratified subsample, with the stratification axis
  named if a subsample.

Both are **[Cooper]**.

---

## A1.8 — Named quarantine of `momentum_pct`

Amends §1.2. The audit surfaced that `filtered_trades` carries a `momentum_pct` column.

**`filtered_trades.momentum_pct` is a spine numeric and is quarantined from all
computation.** It may be displayed as a diagnostic chart label. It may not enter any
calculation, filter, sort key, or derived quantity.

This is the exact shape of the D4 failure that triggered the original quarantine: a spine
numeric sitting inside an otherwise-trusted table, one convenient join away from entering a
computation. T1.4's "total price move" is computed from tick prices in `filtered_trades`,
never from this column.

Add to the §11 verification block: an explicit confirmation, by column name, that
`momentum_pct` was not referenced in any computation path.

---

## A1.9 — Amended [Cooper] register

Supersedes the §5 table's value column. Ten fields, two timings.

| ID | Field | Class | Set at |
|----|-------|-------|--------|
| D1 | `D1_sweep_floor_us` | M | Stage 0 approval |
| D2 | `D2_max_cutoff_ms` | M | Stage 0 approval |
| D4 | `D4_median_precision_factor` | E | Before Stage 0 |
| D7 | `D7_threshold_lo_ms` | E | Before Stage 0 |
| D7 | `D7_threshold_hi_s` | E | Before Stage 0 |
| D8 | `D8_min_median_duration_s` | E | Before Stage 0 |
| D9 | `D9_slope_max` | E | Before Stage 0 |
| D11 | `D11_grid_ceiling_min` | M | Stage 0 approval |
| D14 | `D14_population` | M | Stage 0 approval |
| D15 | `D15_stage3_scope` | M | Stage 0 approval |

Unchanged from the original: **no [Cooper] value is ever filled by the agent.** Not
inferred, not defaulted, not copied from the v4 configuration. An empty field is a halt.

Amended satisfiability protocol: **check 2 is evaluated per stage, not once.** Stage 0
requires only the Class E values present. Stage 1 requires Class E and Class M both present
and Stage 0 approved.

---

## A1.10 — Revised stage sequence

For reference. Amends §7's opening.

| Stage | Produces | Gate |
|-------|----------|------|
| 0 | Interval landscape, no sub-bursts | Mandatory halt for disposition |
| 1 | Sub-bursts at the 4-minute kernel | Scale sanity (D7, D8) |
| 2 | Three kernels {1, 4, 32} | Scale coupling (D9) |
| 3 | Full base-2 grid to D11 | None — descriptive |

Stages run in order. **Do not run a stage speculatively while the prior stage's gate is
pending approval.**
