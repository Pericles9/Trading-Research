---
tags:
  - type/phase-amendment
  - domain/strategy
  - project/src-core
  - status/draft
created: 2026-08-23
phase: 10c
amends:
  - Phase-10c-Prompt.md
  - Phase-10c-Amendment-A1.md
standard: Agent Prompt Standard v1.3
---

# Amendment A2 to Phase 10c

**Carried into the prompt. Not an informal instruction.** Supersedes the named sections of
`Phase-10c-Prompt.md` and `Phase-10c-Amendment-A1.md`. Where documents disagree, the highest
amendment number wins.

Issued at Stage 0 approval, 2026-08-23, against digest
`results/phase_10c/digests/stage0_digest.json`, commit `f376b1f`, tag `phase-10c-stage0`.

Stage 0 executed correctly and its constraints held. This amendment responds to five open
items raised by the run and to **two specification defects in the original prompt** that
Stage 0 surfaced.

---

## A2.1 — Finding: D1 is not identifiable from the data

**Recorded as a finding, not a problem.**

The Stage 0 config guide directed the sweep floor to be read from the point above which the
sub-microsecond mode disappears. **That criterion is vacuous.** Aggregating at floor F
merges every print pair closer than F, so no surviving interval can be shorter than F and
histogram mass piles against the floor. The leftmost mode therefore sits at F by
construction, for any F.

T0.2 confirms this exactly: mode minus floor is +0.05 log₁₀ at every candidate tested, which
is the center of the first bin above the floor at the configured bin width of 0.1. The
measurement returned arithmetic, not a reading.

The absorbed-fraction curve carries the real information. Across 1µs to 10ms the absorbed
fraction rises approximately uniformly per decade (0.023 → 0.116 → 0.222 → 0.391 → 0.535),
which is the signature of an approximately log-uniform interval distribution in that range.
**A separable fragmentation mode would produce a plateau** — a region where all
fragmentation is absorbed and no genuine trade has yet been merged. No plateau exists in the
tested range.

**Consequence.** There is no scale separation in the sub-millisecond region from which to
derive D1. Under the standing rule that a scale parameter which the data cannot identify
must come from an economic quantity rather than statistical convenience, **D1 is set from
timestamp provenance**: above consolidated-feed timestamp jitter, below the fastest genuine
trade spacing.

This finding is carried into the digest and the phase writeup. It is not a defect in Stage 0.

---

## A2.2 — Specification defect: T0.3 reported an insufficient peak statistic

T0.3 as specified reports only the largest peak location. **The entire method assumes the
log-interval histogram is bimodal** — a fast mode, a slow mode, and a trough between them
whose depth the void parameter measures. Without two modes there is no trough, no threshold,
and no sub-burst.

T0.3 cannot show whether a second mode exists. That precondition therefore went unmeasured,
and the defect is in the original specification rather than in the run.

Stage 0's σ_log₁₀ = **2.22 decades** raises this from pedantic to urgent. Equity interval
distributions typically run 0.5–1.0. At 2.22, ±1σ spans roughly 0.6ms to 17s. That
dispersion, together with the flat absorbed-fraction curve, is consistent with a heavy-tailed
near-scale-free process. **Scale-free distributions have no modes and no troughs.**

If bimodality does not survive sweep aggregation, no choice of D1, D2, D4 or D11 rescues the
phase. **This must be established before any Class M value that depends on it is set.**

---

## A2.3 — New Stage 0b: bimodality precondition and post-aggregation scale

Inserted between Stage 0 and Stage 1. Amends §7 and A1.10.

Same 56 events, same pull, no new machinery. Runs at **D1 = 100 µs** (A2.6).

### Hard constraints

Inherits every Stage 0 constraint: no sub-bursts, no cross-event pooling, per-event
histograms only. Stage 0b **may** compute a candidate trough and void parameter, because
that is the precondition being tested. It **does not** extract sub-bursts and **does not**
apply a normalisation window.

Ends in a mandatory halt.

### Tasks

**T0b.1 — Full peak set.** Per event, post-aggregation: peak count, all peak locations, all
prominences. Report the across-event distribution of peak count, and the joint distribution
of the two most prominent peak locations. Chart: per-event histograms with all peaks marked
for ten representative events, plus the across-event peak-count distribution.

**T0b.2 — Void parameter distribution.** Per event, at the deepest trough between the two
most prominent peaks, report the void parameter as a continuous quantity. Report by segment.
Events with fewer than two peaks are labelled `unimodal` and counted, not dropped.

**T0b.3 — Post-aggregation dispersion.** Recompute σ_log₁₀ per event after aggregation at
D1. Report the across-event distribution, by segment, alongside the raw σ from Stage 0.
Recompute the D4 derived floor at candidate factors 1.1, 1.2, 1.3, 1.5 using the new σ, and
report the resulting `too_few_prints` fraction **split by segment**, never pooled.

**T0b.4 — Prominence sensitivity.** Sweep prominence 0.01–0.20. Report how far the selected
peak pair and the resulting trough location move across the sweep, per event, as a log-space
displacement. Report the across-event distribution of that displacement.

**T0b.5 — Near-detection print density.** Report RTH print density measured in a window
around the detection anchor, alongside the session-wide figure from T0.4. Stage 0's
session-wide RTH density of 7.5/min may be depressed by the low-activity afternoon; the
quantity that matters for kernel sizing is density where the analysis actually runs.

**T0b.6 — PRECONDITION GATE.** If the median void parameter from T0b.2 falls below
`D16_min_median_void` **in either segment**, HALT.

A void distribution concentrated near zero means the histogram is not bimodal, there is no
structural interval to find, and the method has no object to operate on. **The correct
conclusion on this halt is that the log-interval decomposition is the wrong instrument for
this data — not that a parameter needs adjusting.** Do not attempt to rescue the run by
altering D1 or the prominence level.

`D16_min_median_void` is **[Cooper]**, Class E, set before Stage 0b runs.

**T0b.7 — HALT.** Produce the Stage 0b digest and stop.

---

## A2.4 — Specification defect: peak prominence was an unconfigured free parameter

Open item O1 is correct and the omission is a specification defect. The config fixes the
peak-finding criterion and forbids smoothing but sets no prominence level. Prominence selects
the peak, the peak bounds the trough search, and the trough is the answer. **This is the
exact shape of free parameter the standing rule exists to catch**, and it was left open.

Closed in two parts, both required.

**Part 1 — derived floor.** Histogram bin counts carry Poisson counting noise of order √k. A
peak whose prominence does not exceed the counting noise in its own bin is not distinguishable
from noise. Derive a per-event minimum prominence on that basis and document the derivation
in the digest. This replaces a chosen constant with a data-derived floor.

**Part 2 — sensitivity is the test.** T0b.4 measures how far the answer moves as the
parameter moves. **This is structurally identical to the D9 scale-coupling test**: if the
answer tracks the parameter, the parameter is the answer.

Report the T0b.4 displacement distribution **beside the D9 slope distribution** in the Stage
2 digest, not as a separate concern. Both measure the same pathology at different points in
the pipeline.

No pass threshold is attached to prominence sensitivity in this phase. It is reported.

---

## A2.5 — Session boundary definition (open item O2)

**Resolved: clip at the regular-session open and close.**

Stage 0's T0.4 supplies the argument. Premarket median print density is 131.6/min against
RTH 7.5/min — a **17× inversion**, with RTH the thinner segment. A centered window spanning
09:30 mixes two regimes differing by more than an order of magnitude in pace, and the local
median inside such a window is set by whichever side is denser rather than by local pace.

That is precisely the failure the clock-time window basis exists to prevent. Extended-day-only
clipping would permit it.

D11 reads from the plus-RTH column of T0.5.

**The 17× density inversion is itself a finding** and is carried into the phase writeup
independent of its use here.

---

## A2.6 — Class M dispositions

| ID | Value | Basis |
|----|-------|-------|
| D1 | **100 µs** | Timestamp provenance per A2.1; above feed jitter, below fastest genuine spacing. Absorbs 22%. Leaves `D7_threshold_lo_ms` = 10 admissible under check-4 condition 2 with one decade of margin. |
| D11 | **64 minutes** | T0.5 plus-RTH: 0.137 clipped at 32 min, 0.417 at 128. At 128 the kernel does not measure what its label states. |
| D14 | **20,951 (full in-scope)** | 5.7h single-threaded parallelises acceptably. Headline numbers are not taken from a subsample. |
| D2 | **HELD** | Requires the fast/slow peak gap from T0b.1. See A2.7. |
| D4 | **HELD** | Requires post-aggregation σ from T0b.3. Stage 0's σ = 2.22 was measured pre-aggregation. |
| D15 | **HELD** | Pending the single-pull requirement in A2.9. |

---

## A2.7 — D2 selection rule, pre-registered

D2's failure mode is worse than the original config guide stated, and the rule is recorded
here **before** T0b.1 output exists.

The original guide described the high-side failure as "the anchor stops constraining." The
actual high-side failure is silent and worse. In a sparse event there are more intervals
between bursts than inside them, so **the slow mode can be the taller peak.** If D2 sits
above it, then "largest peak at or below D2" selects the *slow* mode as the intraburst peak.
The trough search then runs to the right of the slow mode and returns either nothing or a
meaningless value — **without triggering `no_intraburst_peak`.**

D2 must therefore sit **between the fast mode's right tail and the slow mode's left tail,
across all events** — a substantially tighter constraint than "above the fast peak."

**Pre-registered selection rule.** From T0b.1's joint distribution of the two most prominent
peak locations:

1. If the fast-mode right tail (p95) and the slow-mode left tail (p5) are separated, set D2
   in the gap, positioned to keep `no_intraburst_peak` incidence low.
2. If they overlap, **no single global D2 exists.** Do not pick a compromise value. Report
   the overlap and escalate; the resolution is per-segment or per-event D2, which is a new
   decision requiring its own amendment.

Note that D1 now performs most of the anti-fragmentation work. D2 is defence in depth rather
than the primary mechanism, which argues for a generous position within the gap rather than
a tight one against the fast peak.

---

## A2.8 — D5 and D6 become derived, not chosen

Stage 0 surfaced a defect in D5 that would halt Stage 1 for reasons unrelated to the method.

At RTH session-wide density of 7.5 prints/min, the 4-minute kernel holds roughly **30
prints**. Any plausible D4 derived floor exceeds that by an order of magnitude. RTH intervals
would therefore be labelled `too_few_prints` nearly everywhere, the Stage 1 scale-sanity gate
evaluates "either segment out of band," and **Stage 1 halts on an empty RTH cell rather than
on a finding.**

The 4-minute value (amended from 5 in A1.5 purely for base-2 grid alignment) was never
derived from anything.

**D5 is amended to a derived quantity**, set at Stage 0b approval:

> D5 is the smallest rung on the base-2 grid at which the median RTH event clears the D4
> derived data floor, using the near-detection density from T0b.5.

**D6 is amended to follow D5** on the grid: `{D5 ÷ 4, D5, D5 × 4}`, subject to the low rung
being at least 1 minute and the high rung at most D11.

Both become Class M, set at Stage 0b approval.

**This is not a workaround for a thin segment.** If RTH is only legible at wide kernels while
premarket is legible at narrow ones, that is exactly the per-event scale-legibility structure
T3.2 exists to characterise. The correction here is only that Stage 1's single validating
kernel must be one where *both* segments can produce an answer.

---

## A2.9 — Stage 3 input/output requirement

Prior guidance overstated Stage 3's cost by treating it as population × kernel count. That
holds only for a naive implementation.

**Requirement:** each event's trades are pulled and aggregated **once**. Kernels are looped
in memory over that single materialisation. **No re-query per kernel.**

The dominant per-event cost is the DuckDB slice pull. Window computation and peak-finding
over resident data is cheap by comparison, so realistic Stage 3 cost is on the order of 2–3×
Stage 1 rather than N×.

Two quantities do scale with kernel count and must be sized before the run: the per-kernel
chart surface, and the T3.3 scale-extent array, which is per-moment across all kernels.
Report both estimates in the Stage 2 digest.

D15 is set at Stage 0b approval once this requirement is reflected in the cost estimate.

---

## A2.10 — Open item O5, no action

The 10,000 µs candidate floor absorbs 53.5% of prints. Check-4 condition 2 excluding it is
the constraint operating as designed, and the absorbed fraction disqualifies it independently
of the check. Accepted, no change.

---

## A2.11 — Amended register

| ID | Field | Class | Status |
|----|-------|-------|--------|
| D1 | `D1_sweep_floor_us` | M | **100** |
| D2 | `D2_max_cutoff_ms` | M | Held — Stage 0b approval, rule in A2.7 |
| D4 | `D4_median_precision_factor` | M | Held — Stage 0b approval (reclassified from E) |
| D5 | `D5_first_kernel_min` | M | Derived — Stage 0b approval, rule in A2.8 |
| D6 | `D6_stage2_kernels_min` | M | Derived from D5, rule in A2.8 |
| D7 | `D7_threshold_lo_ms` | E | Set before Stage 0b |
| D7 | `D7_threshold_hi_s` | E | Set before Stage 0b |
| D8 | `D8_min_median_duration_s` | E | Set before Stage 0b |
| D9 | `D9_slope_max` | E | Set before Stage 0b |
| D11 | `D11_grid_ceiling_min` | M | **64** |
| D14 | `D14_population` | M | **20,951** |
| D15 | `D15_stage3_scope` | M | Held — Stage 0b approval, per A2.9 |
| D16 | `D16_min_median_void` | E | **New.** Set before Stage 0b. Gates T0b.6. |

D4 is **reclassified from Class E to Class M**. A1.3 asked whether it was flat or steep;
Stage 0 answered steep, which makes it a data question rather than a preference. It is not a
gate value, so setting it from measurement carries no pre-registration cost.

---

## A2.12 — Revised stage sequence

| Stage | Produces | Gate |
|-------|----------|------|
| 0 | Interval landscape | Complete — `phase-10c-stage0` |
| 0b | Bimodality precondition, post-aggregation scale | **D16 void precondition** |
| 1 | Sub-bursts at the D5 kernel | Scale sanity (D7, D8) |
| 2 | Three kernels per D6 | Scale coupling (D9), prominence sensitivity reported alongside |
| 3 | Full base-2 grid to D11 = 64 min | None — descriptive |

Git: commit at every T0b task boundary, tag `phase-10c-stage0b` at the gate.
