---
tags:
  - type/config-guide
  - domain/strategy
  - project/src-core
  - status/draft
created: 2026-08-23
phase: 10c
companion: phase_10c.json
---

# Phase 10c Config Guide

Ten fields to fill. Five now, five after Stage 0.

For each: what it is, what it controls, and what goes wrong at each end. **No recommended
values.** Where a derivation exists, it is named.

---

## Fill now — Class E (economically derived)

Set these before Stage 0 runs. They are statements about what is tradeable, not about what
is in the data, so no measurement is needed to reach them.

### `D8_min_median_duration_s`

**Units:** seconds. **Type:** floor.

Minimum acceptable median sub-burst duration. This is the gate v4 failed — it produced
349 nanoseconds.

**Derivation available.** Below your realistic pipeline latency you cannot act on a
sub-burst's boundaries, and consecutive sub-bursts are not distinguishable at decision time.
§4.2 condition 4 of the program doc states that sub-second signals during a burst are fiction
with retail-grade execution, and that 30-second-to-5-minute horizons survive modest latency.
The floor follows from your realistic detect-to-fill latency, not from the data.

- **Too low:** the gate lets through objects you can't trade, and Phase 10c repeats v4's
  outcome without noticing.
- **Too high:** you halt on a working method because genuine burst structure at this scale
  happens to be shorter than your patience. This is the more expensive error, because the
  halt reads as "the window basis wasn't the cause" when the truth is "the bar was wrong."

The asymmetry favours setting this at your **actual** latency rather than a comfortable
margin above it.

### `D7_threshold_lo_ms` and `D7_threshold_hi_s`

**Units:** milliseconds and seconds respectively. **Type:** band on the threshold interval.

The chosen threshold is the inter-trade interval separating "inside a burst" from "between
bursts." This band says where a defensible answer can land.

**Upper bound:** the largest inter-trade gap you'd still call burst interior. If the
threshold is 30 seconds, a 25-second silence counts as inside a burst — incoherent for a
scalp on a microcap.

**Lower bound:** constrained by audit check 4 to exceed `D1_sweep_floor_us` by at least one
order of magnitude. Since D1 isn't set yet, pick D7_lo on its own merits and the check will
catch a conflict at Stage 1. A threshold near the aggregation floor means nearly every
interval clears it and the event collapses into one sub-burst.

**Watch the interaction with D8.** The config reports `D8 / D7_hi` as the implied minimum
number of intervals in a median sub-burst. If your choices imply 500, that's a strong claim
about print density and you should see it before running, not after.

### `D9_slope_max`

**Units:** dimensionless. **Type:** ceiling on a log-log slope.

Per event, threshold location is regressed on kernel duration, both logged. The slope says
how much of the threshold's position is contributed by the window rather than the tape.

- **0** — the threshold is a structural property of the data. The method works.
- **1** — the threshold is a restatement of kernel duration. The method is measuring its own
  parameter.

**This is the weakest-derived field in the config.** D7 and D8 come from latency and cost;
D9 has anchors at 0 and 1 and nothing principled in between. The retired count-gate used
0.35, but that gate was retired for being wrong, so importing its number is not a
derivation. If you want an empirical answer instead of a picked one, the synthetic-null test
is still on the table — run the window machinery on simulated tape with a known structural
interval and see what slope a working method actually produces.

### `D4_median_precision_factor`

**Units:** multiplicative factor in log space. **Type:** precision target.

How tightly the local median must be estimated. Median standard error scales as one over the
square root of sample size, so this factor determines the minimum print count inside a
window before the estimate is trusted.

- **Too tight (near 1.0):** the derived minimum count balloons, `too_few_prints` swallows
  the sample, and the quiet parts of every event go unlabelled — which is where the
  interesting boundaries are.
- **Too loose:** the local median is noisy, and the normalisation adds variance rather than
  removing it.

**T0.4 measures the sensitivity** at 1.1, 1.2, 1.3 and 1.5, so if you'd rather set this at
Stage 0 approval than now, that's defensible — it isn't a gate value and nothing about the
Stage 1 outcome depends on having fixed it in advance. Your call whether to treat it as
Class E or move it.

---

## Fill at Stage 0 approval — Class M (measurement-derived)

Read these off the Stage 0 charts. Reading a scale off the data is not tuning; these
describe the shape of the input, not the quality of the output.

### `D1_sweep_floor_us`

**Units:** microseconds. **Read from:** T0.1, T0.2.

Prints within this interval of each other are aggregated into one trade event before any
interval is computed. This is the fix for v4's root cause.

T0.2 reports, for candidate floors from 1µs to 10ms: the fraction of raw prints absorbed,
and where the leftmost surviving mode lands. **Look for the floor above which the
sub-microsecond mode is gone and below which real structure starts disappearing.** If those
two points are far apart, the choice is easy. If they're close or inverted, that's itself a
finding worth pausing on.

- **Too low:** fragmentation survives and v4 repeats.
- **Too high:** genuine rapid trading gets merged away, and sub-burst counts fall for a
  reason that has nothing to do with the market.

### `D2_max_cutoff_ms`

**Units:** milliseconds. **Read from:** T0.3.

Ceiling on where the intraburst peak may sit. **Not a ceiling on the threshold** — the
threshold is a trough to the right of that peak and will normally land above this value.
That distinction was wrong in the original prompt and is corrected in Amendment A1.4.

T0.3 reports the across-event distribution of the largest peak location for each candidate
sweep floor. Set D2 above the bulk of that distribution with room, so that events in the
right tail still find a peak rather than falling out as `no_intraburst_peak`.

- **Too low:** many events return `no_intraburst_peak` and drop out of the analysis.
- **Too high:** the anchor stops constraining anything and you're back to v4's unbounded
  trough scan.

Audit check 4 requires this to exceed `D1_sweep_floor_us` by at least two orders of
magnitude.

### `D11_grid_ceiling_min`

**Units:** minutes. **Read from:** T0.5.

Widest kernel in the Stage 3 grid.

T0.5 reports clipped-window fraction against kernel duration and time of session. Because
centered windows clip at session boundaries, wide kernels degrade into narrower ones near
the open and close. **At some duration the clipped fraction is high enough that the kernel
no longer measures what its name says.** That point is your ceiling.

Expect this to come in lower than intuition suggests. A 512-minute centered window cannot
exist anywhere in a 390-minute regular session — it is clipped everywhere, by definition.

### `D14_population`

**Read from:** T0.7.

The in-scope event set for Stage 1 headline numbers. T0.7 reports counts and compute
estimates for each candidate definition.

### `D15_stage3_scope`

**Read from:** T0.7.

Full population or stratified subsample for Stage 3, with the stratification axis named if
a subsample.

**Separate decision from D14 on purpose.** Stage 1 is one kernel; Stage 3 is the population
times N kernels. The cost concern lands almost entirely here, and there's no reason the two
stages must run against the same set.

---

## Changing a value mid-run

Permitted, always. The agent does not refuse.

Any change to a Class E value is written to `results/phase_10c/change_log.json` before it
takes effect, recording the field, prior and new value, timestamp, stage and task in
progress, and **which outputs already existed at the time**.

That last field is the whole point. It is what lets a later reader distinguish a threshold
set in advance from one set after seeing what it would judge. The digest reports it as a
fact with no evaluative language attached.
