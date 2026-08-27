# Phase 10d — Spec: Burst Assembly Under a Merge Tolerance and a Run-Length Floor

**Date:** 2026-08-26
**Revision:** r2. Supersedes the r1 draft on two points found at 10d T0b — the identity cell's
`min_prints` value, and the handling of `ok=False` separators. Neither document was committed; this
replaces r1 rather than amending it.
**Status:** Specification. Reasoning and design record. The executable prompt is
`prompts/phase_10d.md`.
**Lineage:** v1 → v2 → v3 → v4 → 10b → 10c → **10d**. Phase 11 and 12 untouched.
**Also supersedes** an earlier draft specifying an exact-partition change and a dip-test gate, which
was built on the 10c outline rather than the committed config. See
`prompts/phase_10c_closing_note_erratum.md`.

---

## 1. What is actually left after 10c

10c fixed the normalization window basis, and **also already replaced the trough-selection rule** —
v4's first-trough-clearing-0.70 became argmax void across all troughs with no cutoff
(`A2.7.D17_burst_envelope_boundary`; `D13_void_parameter.threshold: null`, deliberate and permanent).
That removes the bias toward the mode nearest the short-interval peak. **Trough selection is not the
remaining defect.**

What remains is **fragmentation of the object population**, and it has two independent causes:

| # | Current rule | What it does |
|---|---|---|
| **1** | A sub-burst is a maximal run of **strictly consecutive** sub-threshold intervals. A run is broken by an interval at or above threshold **and equally by an interval failing the `ok` mask** | Splits one sustained burst into several whenever a single interval crosses back over the threshold — or whenever the local window was too thin to normalize against, which is a data-quality artifact rather than market behaviour |
| **2** | **No run-length floor is applied at any point.** 10c has no `min_prints` variable | Every single-interval run is emitted as a sub-burst. A single-interval object is one gap, two prints, and has no internal structure — it cannot be a burst under any reading |

**Cause 2 is quantitatively dominant and was not in the r1 draft.** At 10d T0b the Stage-1 agent
measured the emitted population as **52.3% single-interval objects (89,343 of 170,722)**, with the
recorded median duration computed over that population. *(Figures as reported at T0b; the phase
re-verifies them from `s1_t1_subbursts.parquet` rather than transcribing them from here.)*

**So 10d has two co-equal levers, not one and a side condition:**

- a **merge tolerance**, which joins runs that should not have been split;
- a **run-length floor**, which drops runs that were never bursts.

And the phase's job is not only to apply them but to **say which one moved the number.**

---

## 2. Scope

**In scope:** the merge tolerance, the run-length floor, and the separator-handling rule that governs
what a merge may bridge.

**Fixed background — everything 10c committed, unchanged:** the **centered** clock-time window
(`trailing` and `anchored_to_detection` remain forbidden; the A2.5 density-inversion reasoning is not
reopened); the **three kernels** with **D5 = 8 min primary**; 10c's **variant grid**; the **four
segments** including evening and the unlabelled population; the per-interval derived data floor and
the cell-level `ok.sum()` minimum, with `insufficient_context` carried and never given a fallback;
**argmax-void selection across all troughs with no cutoff**; histogram, bin grid, and the
Poisson-floor peak-survival rule; `collapse_same_timestamp`; D4; frozen cohort.

**Out of scope:** reinstating a void cutoff (§4 reports the counterfactual instead); an
exact-partition replacement for argmax-void; any new applicability gate; the wide log-spaced kernel
grid; the animated histogram; and everything closed by D6, D8, D9.

---

## 3. The three axes

### 3.1 Merge tolerance

Two components, composed — a run merges only if **both** hold:

- **Count tolerance `K`** — the separating run contains at most `K` intervals. Grid
  `K ∈ {0, 1, 2, 3, 5}`.
- **Depth tolerance `d`** — every separating interval lies below `threshold + d`, with **`d` in
  decades of normalized log interval, added to the threshold.** Grid `d ∈ {0, 0.25, 0.5, 1.0}`.

**Why additive in log space.** The threshold is a position on a normalized *log* axis and is
negative. Multiplying it by a factor makes it more negative as the factor grows — the tolerance would
tighten exactly as it was meant to loosen. Adding decades is multiplicative in linear interval terms,
which is the intended scaling, and is scale-free.

**Degeneracy.** A separating interval is non-burst by definition, so `d = 0` admits none regardless
of `K`, and `K = 0` admits none regardless of `d`. Of 20 combinations, **8 are bit-identical and 12
are distinct.** The merge-surface chart will show a flat plateau along both axes; **that plateau is a
parameterization artifact and is labelled as such.** Parameter-dominance is computed over the 12
non-degenerate cells only — including the 8 identical copies dilutes any real gradient by
construction.

### 3.2 Run-length floor — a co-equal axis, not a sensitivity

Grid `min_prints ∈ {2, 3, 5}`, **reference 2.**

**2 is the true no-op.** A single-interval run is 2 prints — `n_prints = n_intervals + 1` and
`n_intervals >= 1` — so 2 is the minimum the data structure can emit and filters nothing. **The r1
draft wrongly stated the reference as 3, on the belief that 10c carried v4's floor. 10c applies no
floor at all.** Setting the reference to 3 would delete a majority of the object population inside
the baseline, so every before/after comparison would be measuring the floor while appearing to
measure the merge.

This also revises a reading recorded earlier in the programme — that a run-length floor "filters the
output without changing what scale the threshold is found at." That was correct about v4. It is not
correct when the floor removes over half the population: at that share the floor is not trimming a
margin, it is selecting which objects exist.

### 3.3 Separator handling — a reported axis, reference is the conservative reading

10c breaks a run on two different conditions and the merge rule must distinguish them:

- an interval **at or above threshold** — a real gap, with a valid depth the `d` test can evaluate;
- an interval **failing the `ok` mask** — the local window was too thin to normalize against, so
  there is no trustworthy normalized value at all.

`sep ∈ {hard_break, bridgeable_count_only}`, **reference `hard_break`**:

- **`hard_break` (reference)** — an `ok=False` interval always ends a run and can never be bridged.
  Preserves `insufficient_context` semantics, uses no value the floor rejected, and is conservative
  in the safe direction: it can only make bursts shorter, so a duration increase measured under it is
  robust.
- **`bridgeable_count_only`** — an `ok=False` separator counts against `K` but is exempt from the `d`
  test, having no valid depth to test.

**Rejected outright: testing the raw `norm` value of an `ok=False` interval against `threshold + d`.**
That uses a number the data floor explicitly declared untrustworthy, and no grid position is offered
for it.

**Why both readings are computed rather than one chosen.** The difference between them *is* the
measurement of how much burst fragmentation is caused by data-quality gaps rather than by market
behaviour — a quantity nothing in the programme currently measures. Reporting the pair costs almost
nothing and answers a question that would otherwise need its own phase.

### 3.4 The measurement that decides what this phase found

The three axes make attribution possible, and **attribution is the deliverable** — not a single
improved duration number. Reported as three reads off the same grid:

- **Floor-only:** `(K=0, d=0)` across `min_prints ∈ {2, 3, 5}`. How much of any duration shift is
  just dropping trivial objects?
- **Merge-only:** `min_prints = 2` across the 12 non-degenerate `(K, d)` cells. How much is joining
  runs that were wrongly split?
- **Joint:** the full surface, to see whether the two interact or simply add.

Plus one diagnostic that distinguishes the mechanisms directly: **the `n_prints` composition of the
object population at each cell.** Merging should *promote* single-interval objects into longer ones —
the 2-print share falls while total print count inside bursts is preserved. The floor merely
*deletes* them — the 2-print share falls and those prints leave the burst population entirely. Those
are different outcomes and the composition histogram tells them apart where a median duration cannot.

**Either direction is a real answer.** If the shift is mostly floor-driven, the residual scale problem
was an object-definition problem and the merge rule is close to inert. If it is mostly merge-driven,
fragmentation-by-threshold-crossing was real. If neither moves duration materially, the scale is
coming from where argmax-void puts the threshold, and that is where the next phase looks. **Do not
soften a null.**

---

## 4. The counterfactual gate — reported, never applied

10c declines no event on void magnitude: `threshold: null`, so argmax-void ranks and never gates. A
decline path on peak count does exist — fewer than two surviving peaks, or no valid trough pair — and
it fired zero times on this cohort. D9's Zaliapin reasoning holds that the share of events where
bimodality fails is a **headline result**, and a method that never declines cannot produce it.

10d does not resolve that by fiat. It **reports the void-parameter distribution and the share of ok
cells that *would* be declined at each of a pre-registered set of candidate cutoffs, applying none**
— descriptive, no pass/fail, the same pattern the retired count-vs-print-count measurement now
follows. The number is large enough to matter, and putting it on a chart is what makes a later
decision informed rather than theoretical.

---

## 5. Control gate — before any real event is read

| Control | Construction | Required outcome |
|---|---|---|
| **C1 — identity** | Replay of a committed 10c cell, plus synthetic sequences | **All eight degenerate `(K, d)` cells at `min_prints = 2`, `sep = hard_break`** reproduce 10c's assembly **exactly, print for print**, and are identical to each other. **Hard gate.** |
| **C2 — monotonicity** | Synthetic sequences with known interruption structure | Merged count non-increasing and merged duration non-decreasing as `K` and `d` rise; count non-increasing as `min_prints` rises. **Hard gate.** |
| **C3 — depth direction** | Synthetic sequence with separators at known depths above threshold | Raising `d` admits **more** separators, never fewer. **Hard gate** — catches the multiplicative-on-a-negative-log error. |
| **C4 — separator equivalence** | Synthetic sequence containing **no** `ok=False` intervals | `hard_break` and `bridgeable_count_only` produce **identical** output. **Hard gate** — proves the axis is inert where it should be, so any difference on real data is attributable to `ok=False` gaps and nothing else. |
| **C5 — floor no-op** | Any labelled sequence | `min_prints = 2` deletes zero objects. **Hard gate** — this is what makes 2 the valid reference. |

A10b.1's distinction applies: correcting a specification defect a control exposes, before real data is
touched, is legitimate; moving a parameter until a number looks acceptable is not.

---

## 6. What 10d deliberately does not attempt

**An exact-partition replacement for argmax-void** (Wang & Song 2011, optimal univariate k-means by
dynamic programming). Dropped because argmax-void already removes the bias that motivated it, and
because the 2011 formulation is O(k·n²), needing either binned input or a harder O(k·n) build. Named
as a successor option if the assembly changes land and the scale is still wrong.

**Hartigan's dip test as an applicability gate.** Rejected on review and recorded so it is not
re-proposed: its null assumes i.i.d. draws and our intervals are autocorrelated by premise; at our n
it rejects for arbitrarily small departures, making the declined share a print-count measurement
wearing an applicability label; and a Monte Carlo p-value floors at 1/(B+1).

**A latent-state formulation** (Tokdar et al. 2010, hidden semi-Markov point process). Burst and
background as latent states with their own duration distributions — no threshold, and contiguous
bursts by construction because duration is modelled rather than patched. **This is the named
candidate if the merge and floor together still need hand-set values to behave.** The answer then is
not a third tolerance.

---

## 7. Decision to record

Appended to `docs/Universe-Decisions.md` as **D15** — D1–D14 are taken. **Append-only per escalation
row 13 as amended.** Cooper's to confirm before the prompt is committed.

> **D15 — Sub-bursts are assembled under a merge tolerance and a run-length floor**
> **Date:** 2026-08-26 · **Gate:** Cooper decision at the Phase 10c close-out
> **Amends:** D9's assembly rule only. D9's operating variable, its normalization and its
> decline-rather-than-invent convention stand, as does 10c's argmax-void threshold selection.
>
> **Decision.** A sub-burst is a maximal run of sub-threshold intervals **under a pre-registered merge
> tolerance and a pre-registered minimum run length**, both reported as grids whose reference cell
> reproduces the prior rule exactly. Whether a merge may bridge an interval excluded by the data floor
> is governed by a pre-registered **separator rule**, reference `hard_break`, with the alternative
> reading reported alongside.
>
> **Why.** Two independent mechanisms fragment the object population, and neither depends on the
> threshold being wrong. Strict consecutiveness splits one sustained burst whenever a single interval
> crosses back over the threshold — or whenever the local window was too thin to normalize against,
> which is a data-quality artifact and not market behaviour. And with no run-length floor, every
> single-interval run is emitted as a sub-burst; a single-interval object is one gap with no internal
> structure and cannot be a burst under any reading. Both deflate duration **by construction**,
> independently of threshold location.
>
> **What does not change.** The operating variable. The centered clock-time window at 10c's
> specification, `trailing` and `anchored_to_detection` still forbidden. The three kernels. **argmax-void
> selection with no cutoff** — `threshold: null` remains deliberate and permanent. Histogram, bin grid,
> peak-survival rule. D4. Segment stratification across all four segments. `insufficient_context`
> carried, labelled, never given a fallback.
>
> **Recorded alongside.** Every grid is reported in full and never selected after seeing results. **The
> phase's deliverable is the attribution** — how much of any duration shift is floor-driven and how much
> merge-driven — not a single improved number. **And separately:** 10c cannot decline on void magnitude,
> so it produces no bimodality-failure share; D9 holds that share to be a headline result. 10d reports
> the void distribution and the counterfactual declined share at candidate cutoffs **as description,
> applying none.** Whether an applicability gate should exist is left open.
>
> **How to apply:** cite D15 alongside D9 for any sub-burst assembled after 2026-08-26. **A sub-burst
> figure quoted without its merge tolerance, its run-length floor and its separator rule is
> incomplete**, as a detection-anchored figure quoted without its poll interval is incomplete under D7.

---

## 8. Cooper decision points

1. **The grids.** `K ∈ {0,1,2,3,5}`, `d ∈ {0,0.25,0.5,1.0}` decades, `min_prints ∈ {2,3,5}`,
   `sep ∈ {hard_break, bridgeable_count_only}`. 12 distinct `(K,d)` × 3 × 2 = **72 distinct
   configurations** per kernel-variant cell.
2. **Cost allocation.** Full cross at D5 = 8 min on 10c's reference variant; at the other kernels and
   variants, the identity cell plus the extremes of the non-degenerate range. The alternative is the
   full cross everywhere, roughly nine times the surface.
3. **Candidate cutoffs for the counterfactual report** (§4). A small pre-registered set spanning the
   observed void range, with 0.70 included because it is v4's retired value and makes the comparison
   legible. **None is applied.**
4. **No numeric duration bar is pre-registered**, deliberately: D13 records that no burst timescale is
   established at usable precision, so a numeric bar would invent the quantity the programme says it
   does not have. The scale judgment is **row 0 — Cooper's visual review against the tape.** Override
   only by recording a chosen constant as such.
5. **Count-vs-print-count is re-run descriptively, no gate** — carried from 10c's revision.

---

## 9. Open questions this phase does not resolve

- **Whether an applicability gate should exist at all.** 10c cannot decline on void magnitude; D9
  says the decline share is a headline result. 10d reports the counterfactual and decides nothing.
- **How much fragmentation is caused by `ok=False` gaps.** 10d *measures* this for the first time via
  the `sep` axis, but does not act on it. If the share is large, the data floor is shaping the object
  population and that belongs to a successor phase.
- **What distinguishes the `insufficient_context` population.** Related to but distinct from v4's
  uncharacterised `no_threshold` set, open on the same register.
- Whether the burst boundary should be **time-varying within a session**; whether an event is legible
  at **more than three window scales**. Both untested — the instruments were not built in 10c.
- Whether **an exact partition beats argmax-void.** Untested; §6.
