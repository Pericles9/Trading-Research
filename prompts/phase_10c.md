---
tags:
  - type/phase-prompt
  - domain/strategy
  - project/src-core
  - status/draft
created: 2026-08-22
phase: 10c
standard: Agent Prompt Standard v1.3
---

# Phase 10c — Clock-Time Sub-Burst Decomposition

**Read this document in full before running anything.** It is self-contained. Do not
consult the Phase 10 v4 prompt or the Phase 10c planning notes; both contain superseded
decisions. Where this document and any prior artifact disagree, this document wins.

---

## 0. What you are being asked to do

Decompose the trade sequence of a momentum event into **sub-bursts** — contiguous runs of
unusually rapid trading — using the distribution of intervals between consecutive trades.

This is an **offline decomposition**, not a live detector. Lookahead is permitted. Nothing
in this phase runs in real time, and no decision here needs to be causal.

Phase 10c exists because Phase 10 v4 produced sub-bursts with a **median duration of 349
nanoseconds**. That is the timescale of a single marketable order sweeping several resting
orders and being reported as multiple prints. It is not a timescale anyone can trade. The
method found a real structure in the data and it was the wrong structure.

Your job is to find out whether three specific corrections produce sub-bursts at a
timescale a trader would recognise, and to describe what those objects look like. **You do
not evaluate whether the result is good.** See §9.

---

## 1. Background you need

### 1.1 The data

Momentum events are extreme single-day price moves in low-priced small-capitalisation
equities. The canonical universe is the DuckDB view `momentum_events_canonical`. Every
universe query joins against it with an inner join. Note that this view runs a live
DISTINCT scan over billions of rows — it is expensive. Materialise once per run, do not
call it in a loop.

Tick data lives in `filtered_trades` and `filtered_quotes`, parquet-backed in DuckDB.
**Never materialise either table to a dataframe.** Pull per-event slices only.

Each event has a **detection anchor** — the timestamp at which the event's momentum
condition was first satisfied. It is stored per event and is the reference point T=0 for
all timing measurements in this phase.

Timestamps use the `sip_timestamp` basis with `sequence_number` as tiebreak. Trades are
timestamped in nanoseconds.

### 1.2 Standing constraint D4 — tick-derived only

Every computed quantity in this phase must be derived from the tick archive. The event
spine carries price and volume columns whose adjustment basis does not match the tick
archive; that mismatch is irreconcilable and those columns are **permanently quarantined**.
You may display spine numerics as diagnostic labels on charts. You may not compute anything
from them. If you find yourself reaching for a spine price or volume column to calculate
something, stop and escalate.

### 1.3 Segment stratification

Every distribution, chart, and table in this phase is reported split by **detection
segment** — whether the event's detection anchor fell in pre-market or in regular trading
hours. These two populations behave differently and pooling them hides it. Report both
separately and pooled; never pooled alone.

---

## 2. The mechanism (carried forward from v4, unchanged)

### 2.1 Log-interval histogram

For a sequence of trade timestamps, compute the intervals between consecutive trades, take
the base-10 logarithm of each, and histogram them. Bin width 0.1 in log units.

The expectation is **bimodality**: a fast mode corresponding to trades inside a burst, and
a slow mode corresponding to the gaps between bursts. The trough between them is the
threshold that separates the two.

### 2.2 Peak finding

Locate histogram peaks using prominence-based peak detection. **No smoothing of the
histogram.** Smoothing introduces a bandwidth parameter, and a free parameter whose value
determines the reported answer is grounds for rejecting the method outright — see §8.

### 2.3 Void parameter

For a candidate trough sitting between a left peak and a right peak, the void parameter is

```
V = 1 - f(trough) / sqrt( f(peak_left) * f(peak_right) )
```

where `f` is histogram density at that location. It measures how cleanly the two modes are
separated. V near 1 means a deep, clean valley; V near 0 means the two modes are barely
distinguishable.

This construction comes from Selinger et al. (2007) and the logISI burst-detection method
of Pasquale et al. (2010), originally developed for neuronal spike trains. **We are
adopting the mechanism, not their calibration.** See §8 on what this means in practice.

### 2.4 Sub-burst definition

Once a threshold interval is chosen, a sub-burst is a maximal run of consecutive intervals
that all fall below it.

### 2.5 Tie handling

Trades sharing an exact timestamp produce a zero interval, and log(0) is undefined. Handle
this by collapsing exact-timestamp ties into a single trade event before computing
intervals. This is the reference variant; do not implement alternatives.

Note that this handles only *exact* ties. It does not address near-ties, which are the
subject of §3.1.

---

## 3. What changes in Phase 10c

Three corrections. All three are pre-registered below as decisions D1–D3. Two of them are
upstream of any result — if they are wrong, the phase produces no information.

### 3.1 Correction 1 — sweep aggregation at the data layer

The v4 failure was caused by a mode in the log-interval histogram at the nanosecond to
microsecond scale. This mode is an artifact of trade reporting: one marketable order that
sweeps several price levels is reported as several prints with near-identical timestamps.
Those prints are one economic event.

Sub-microsecond structure is also below the resolution at which these timestamps carry
meaning. Divergence between the consolidated feed timestamp and the participant timestamp
is on the order of microseconds to milliseconds. Structure finer than that is reporting
noise, not market behaviour.

**Fix:** before computing any intervals, aggregate consecutive prints whose timestamps fall
within a floor interval into a single trade event. Aggregate volume by summation; take the
volume-weighted average price; take the timestamp of the first constituent print.

The floor value is `D1_sweep_floor_us`, in microseconds. **[Cooper]** — you do not choose
this. It is set in the run configuration before execution.

### 3.2 Correction 2 — an absolute ceiling on the threshold search

v4 selected its threshold by scanning troughs left to right and taking the first one whose
void parameter cleared a cutoff. With a mode present at the nanosecond scale, the leftmost
trough is separated from everything else by five or six orders of magnitude, so its void
parameter is near-perfect and it wins every time. Sharpening the histogram makes this worse,
not better.

The source literature does not do this. In the logISI method the intraburst peak is defined
as the largest peak *at or below a pre-specified maximum cutoff value*, and only troughs
above that peak are candidates. That anchor is precisely the mechanism that prevents the
algorithm locking onto a spurious short-scale mode. v4 inherited the void parameter and the
trough-scanning rule and dropped the anchor.

**Fix:** reinstate it. Identify the intraburst peak as the largest histogram peak at an
interval at or below `D2_max_cutoff_ms`. Search for troughs only to the right of that peak.
If no peak exists at or below the ceiling, the event is labelled `no_intraburst_peak` and
carried — see §7.

`D2_max_cutoff_ms` is **[Cooper]**.

### 3.3 Correction 3 — clock-time window basis

v4 normalised each interval by a local median computed over a window defined as a **fraction
of print count** — 20% of the sequence length. The real-world duration of such a window
swings by orders of magnitude between the fast and slow parts of a session. A window that is
not anchored to clock time has no reason to produce a clock-time-scale answer.

**Fix:** the local normalisation window is defined in **clock time**. It remains **centered**
on the interval being normalised, exactly as in v4. Centering is not changing. This phase
changes the window basis and nothing else about the window.

Do not implement a trailing variant. Do not implement a variant anchored to the detection
anchor. This is an offline decomposition and causality is not a requirement here.

**Session boundaries.** A centered clock-time window will reach across session boundaries
and, at wide durations, across the overnight gap. The interval spanning an overnight gap is
on the order of fifteen hours and will dominate any local median that contains it.

Windows are therefore **clipped at session boundaries**. A window never spans a session
close or a session open. Where clipping reduces the window's contents below the data floor
(D4 below), the interval is labelled and carried, not estimated.

Report, per kernel, the fraction of intervals whose window was clipped. At wide kernel
durations this fraction will approach 1 near session edges, and it caps how wide the grid
can usefully go. That measurement is a deliverable, not a diagnostic.

### 3.4 Correction 4 — minimum data floor, derived not chosen

v4 required 200 prints in the normalisation window before trusting the local median. A
clock-time window needs its own floor, and it should be derived rather than picked.

The standard error of a median scales as one over the square root of the sample size.
Given a target precision for the local median expressed as a multiplicative factor in log
space — `D4_median_precision_factor`, **[Cooper]** — derive the implied minimum count and
document the derivation in the run digest.

Intervals whose window contains fewer than the derived minimum are labelled
`too_few_prints` and carried. **Never substitute a fallback estimate.** A labelled gap is
information; an imputed value is fabrication.

---

## 4. What is explicitly NOT in this phase

Do not implement, and do not raise as a question mid-run:

- **The count-versus-print-count gate.** Every prior version carried a hard stop testing
  sub-burst count against event print count. It is **retired**. A positive relationship
  between the two is mechanically expected — a bigger, longer, busier event produces more
  sub-bursts under any reasonable definition — and its existence is not evidence of a
  defect. It is reported as a descriptive chart with no threshold attached and no ability to
  stop the phase.
- **Any void-parameter cutoff.** v4 used 0.70, adopted from the neuroscience literature.
  This phase does **not threshold on the void parameter at all**. Report it as a continuous
  quantity and show its distribution. A binary cutoff is only needed for a binary decision,
  and this phase makes none.
- **Combining kernels into a single signal.** Out of scope. Report kernels side by side.
- **A minimum sub-burst run-length filter.** Out of scope. It filters output without
  changing the scale at which the threshold is found.
- **Benchmarking stability against published figures from neuroscience or seismology.**
  Those fields motivated the mechanism. Their calibration numbers are not a pass bar for
  this application. Stability is judged against our own kernels and our own data.

---

## 5. Pre-registered decisions

| ID | Decision | Value |
|----|----------|-------|
| D1 | Sweep aggregation floor, microseconds | `D1_sweep_floor_us` **[Cooper]** |
| D2 | Maximum cutoff for intraburst peak, milliseconds | `D2_max_cutoff_ms` **[Cooper]** |
| D3 | Window basis | Clock time, centered, clipped at session boundaries |
| D4 | Local median precision target, log-space factor | `D4_median_precision_factor` **[Cooper]** |
| D5 | First kernel duration | 5 minutes |
| D6 | Stage 2 kernel set | 1, 5, 30 minutes |
| D7 | Scale sanity band — median threshold location | `D7_threshold_lo_ms` to `D7_threshold_hi_s` **[Cooper]** |
| D8 | Scale sanity band — median sub-burst duration floor | `D8_min_median_duration_s` **[Cooper]** |
| D9 | Threshold-location slope pass band (Stage 2) | `D9_slope_max` **[Cooper]** |
| D10 | Full grid spacing | Geometric, base 2, from 1 minute |
| D11 | Full grid ceiling | `D11_grid_ceiling_min` **[Cooper]** |
| D12 | Tie handling | Collapse exact-timestamp ties |
| D13 | Void parameter | Reported continuous, never thresholded |

**No value marked [Cooper] is ever filled in by you.** If a run configuration reaches you
with a [Cooper] field empty, halt and escalate. Do not infer a sensible default, do not
copy the v4 value, do not proceed with a placeholder.

---

## 6. Satisfiability audit

Run this before any code executes. Confirm all four in writing in the run log, then stop and
wait for approval to proceed.

1. **Measurable** — every quantity named in §7 is computable from `filtered_trades` and the
   detection anchor alone, with no spine numerics.
2. **Threshold set** — every [Cooper] field in §5 carries a value in the run config.
3. **Reachable** — the dev sample can produce every chart in §10 and every field in the
   digest.
4. **Non-contradictory** — no two decisions in §5 conflict; in particular, confirm that
   `D2_max_cutoff_ms` sits above `D1_sweep_floor_us` by at least two orders of magnitude,
   and that the D7 sanity band lies at or below `D2_max_cutoff_ms`.

If any check fails, halt and escalate. **Do not proceed with three of four.**

---

## 7. Task sequence

Execution is **staged**. Each stage has a hard stop. A stage that hard-stops ends the run —
you do not proceed to the next stage, and you do not attempt a workaround.

Two-tier execution applies throughout: iterate on the **pinned 50-event development
sample** (v4, seed 42, stratified by momentum percentage decile) and produce headline
numbers only from the **full-population run on a frozen configuration**. Never report a dev
sample number as a result.

### Stage 1 — Single kernel, scale validation

**T1.1** Implement sweep aggregation per D1. Report, on the dev sample: distribution of
prints per aggregated event, fraction of raw prints absorbed, and the log-interval
histogram before and after aggregation on five representative events. The nanosecond mode
should be gone. **Confirm it visually before continuing.**

**T1.2** Implement the clock-time centered window per D3 at the 5-minute duration, with the
derived data floor per D4. Report the clipped-window fraction and the `too_few_prints`
fraction by segment.

**T1.3** Implement threshold selection per D2. For each event report: intraburst peak
location, chosen trough location, void parameter at that trough, and the label if no
threshold was found.

**T1.4** Extract sub-bursts. Report duration, spacing, count, timing relative to the
detection anchor, and share of the event's total price move falling inside sub-bursts.

**T1.5 — HARD STOP (scale sanity).** On the full population, compute the median threshold
location and the median sub-burst duration, by segment.

- If median threshold location falls outside `D7_threshold_lo_ms`–`D7_threshold_hi_s`
  **in either segment**, HALT.
- If median sub-burst duration falls below `D8_min_median_duration_s` **in either segment**,
  HALT.

This gate replaces the retired count gate. It tests whether the extracted objects are the
right *kind* of object, which is exactly what v4 failed. It does not test whether they are
useful — that is a later question and it has no threshold here.

On halt: report the numbers, the charts from T1.1–T1.4, and stop. **The correct conclusion
on a halt is that the window basis was not the root cause, and that is a real finding.** Do
not attempt to rescue the run by adjusting D1, D2, or D4.

### Stage 2 — Three kernels, scale-coupling test

Only if Stage 1 clears.

**T2.1** Run the full Stage 1 pipeline at 1, 5, and 30 minutes (D6).

**T2.2 — HARD STOP (scale coupling).** Per event, regress chosen threshold location on
kernel window duration, both in log space. Report the slope distribution.

- Slope near 0 means the threshold lands at the same interval regardless of window size —
  the void gate is finding a structural interval in the data.
- Slope near 1 means the threshold tracks the window — the trough is landing wherever the
  local median puts it, and the method is measuring its own parameter rather than the
  market.

If the median slope exceeds `D9_slope_max`, HALT and report.

This is the highest-information test in the phase and it costs three kernels rather than
the full grid. It runs here for that reason.

### Stage 3 — Full grid

Only if Stage 2 clears.

**T3.1** Extend to the geometric grid per D10 and D11: 1, 2, 4, 8, 16, 32, 64 minutes and
onward to the ceiling.

**T3.2** Per event, report which kernel durations yield a threshold and which yield
`no_threshold`, together with the void parameter at each. This describes, per event, which
timescales are legible. Expect this to differ across events. **That is a finding, not a
defect.**

**T3.3** Report the count of flagging kernels per moment as a continuous field, 0 to N. Note
in the digest that kernels are nested — a 32-minute window contains the 16-minute window —
so adjacent kernels agree by construction. This field measures **scale extent**, the range
of timescales at which a moment reads as bursty. **It is not a confidence score and must not
be described as one.**

**T3.4** As an integrity check, report the fraction of moments whose set of flagging kernels
is non-contiguous in scale. A moment flagged at kernels 4, 5 and 7 but not 6 indicates a
defect. Report the fraction; do not attempt to explain it.

**T3.5** Cross-tabulate the legible kernel scale against event duration, detection segment,
and detection-price decile.

---

## 8. Standing methodological constraints

**Scale parameters must be set by economic quantities, never by statistical convenience.**
Any free parameter whose value determines the reported answer is grounds for rejecting the
entire method family. This rule has already eliminated several candidate approaches in this
program. It applies to you in three specific ways:

- Do not sweep kernel durations and report the one that produces the cleanest separation.
  The grid is fixed by D10 and D11 and reported in full.
- Do not smooth the histogram to make peak finding easier.
- Do not adjust any [Cooper] value to make a gate pass.

**Physical-time pooling across events is a category error.** These events do not share a
clock. Do not pool raw intervals across events into a single histogram. All histograms are
per event.

**Hard stops over silent continuation.** If something is ambiguous, halt and escalate. Do
not choose the interpretation that lets the run finish.

**Amendment protocol.** Any deviation from this document requires a formal numbered
amendment carried into the prompt. Informal instructions mid-run are not authorisation.

---

## 9. Reporting posture

**Describe the picture. Do not read it.**

Report distributions, counts, and charts. Do not characterise results as encouraging,
disappointing, clean, promising, weak, or strong. Do not conclude that the method works or
does not work. Do not recommend next steps.

Every stated finding requires a supporting distributional chart. A number without a
distribution behind it is not reportable.

The only evaluative statements you make are the mechanical gate outcomes in T1.5 and T2.2:
a threshold was or was not crossed, and the run continues or halts.

---

## 10. Chart contract

No conclusion appears without a supporting chart. **Dual y-scale is forbidden.** Use linked
panels on a shared x-axis, per the Phase 9 precedent.

Required, per stage:

1. **Log-interval histogram, before and after sweep aggregation** — five representative
   events, overlaid.
2. **Interval-density heatmap** — time on x, log-interval bin on y, density as colour, with
   the chosen threshold overlaid as a line. One panel per kernel, stacked on a shared time
   axis. This is the primary session-evolution chart.
3. **Animated histogram** — the same underlying matrix as chart 2, rendered as a
   frame-scrubbable plotly figure with a slider, showing the density curve, detected peaks,
   chosen trough, and void parameter evolving across the session. Build the matrix once and
   render both charts from it. Produce this for a handful of events only, not the full
   population.
4. **Tape-review panel set** — trades on top, rate or envelope in the middle, interval axis
   at the bottom, sub-bursts shaded, all on a shared time axis. This is the existing
   pattern; extend it, do not invent a new chart grammar.
5. **Sub-burst duration and spacing distributions**, by segment.
6. **Timing relative to detection anchor** — distribution of sub-burst onsets against T=0.
7. **Move-share concentration** — fraction of the event's price move falling inside
   sub-bursts, distributed.
8. **Sub-burst count versus print count** — scatter with Spearman correlation and log-log
   slope annotated. **Descriptive only. No threshold line. No pass or fail language.**
9. **Threshold location versus kernel duration** (Stage 2) — per-event lines in log-log
   space, with the slope distribution as a companion panel.
10. **Void parameter distribution by kernel** (Stage 3).
11. **Clipped-window fraction by kernel duration and time of session.**

All charts are self-contained HTML using the existing plotly tooling. No new charting
dependency.

---

## 11. Verification block

Before the digest, confirm and record:

- Row counts at every stage: raw prints in, aggregated events out, intervals computed,
  intervals labelled, sub-bursts extracted. **These must reconcile.** Report the waterfall
  explicitly; unaccounted rows are a hard stop.
- No spine numeric entered any computation (D4).
- The dev sample is the pinned v4 sample, seed 42, n=50.
- The full-population run used a frozen config whose hash is recorded.
- Every [Cooper] value used, echoed back with its source.
- The derived data floor, with its derivation shown.
- Segment split counts, summing to the population total.

---

## 12. Digest contract

One digest per stage, containing:

- Stage and task identifiers, config hash, wall-clock runtime.
- Every [Cooper] value used.
- The verification block from §11 in full.
- All labelled-and-carried counts by label (`no_intraburst_peak`, `too_few_prints`,
  `no_threshold`), by segment.
- Gate outcomes with the computed value beside the threshold.
- A manifest of every chart produced, with file paths.
- Any escalation raised, with the reason.

---

## 13. Git discipline

- Branch per phase: `phase-10c`.
- Commit before any run.
- Commit at every task boundary (T1.1, T1.2, …).
- Commit before any escalation.
- Tag at each stage gate: `phase-10c-stage1`, `phase-10c-stage2`, `phase-10c-stage3`.
- Commit messages name the task identifier.

---

## 14. Cost note

Stage 3 multiplies the void-gate apparatus and the entire reporting surface by the number of
kernels. The staging in §7 exists to avoid paying that cost before the mechanism is known to
produce trading-scale objects at all. **Do not run stages out of order, and do not run
Stage 3 speculatively while Stage 2 is pending approval.**
