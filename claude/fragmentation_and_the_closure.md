# The sub-bursts were not events

**Date:** 2026-09-09 · **Type:** finding. **D26 was written from this read** (`docs/Universe-Decisions.md`),
from Cooper's draft text of the same date, edited only where §3.1 and §2 required a correction.
**Cohort:** five of the ten committed panel events, regular hours (`event_panels_cohort.csv`).
**Code:** `research/scale_field/{fragmentation_identity,collapsed_tape_measures,divergence_controlled,divergence_vs_tolerance}.py`.
**Artifacts:** `results/scale_field/artifacts/instrument_gates/`.
**Companion:** `claude/scale_field_instrument_gates.md`, which this supersedes on every question about
what the tape contains.

---

## 1. The finding, in one paragraph

**On these tapes, 40–57% of inter-print intervals are under one millisecond, and prints inside those
sub-millisecond runs are consecutive in SIP sequence number 93–99% of the time against a permuted null
of 0.000.** They are one order reported many times, not many orders. **Collapse them, and the tape
becomes statistically indistinguishable from an inhomogeneous Poisson process at every scale from
15.6 ms to 2,048 seconds** — by the Allan factor against a rate-matched surrogate, and by the
cross-channel divergence, which is exactly zero under a locally Poisson process at any rate path and
needs no surrogate at all. **The lineage's sub-burst objects were most likely not events, the Allan
curve that justified rejecting Poisson nulls was measuring the print process, and there is nothing
left above 10 ms for either channel to find.**

---

## 2. The retroactive closure — what the D9 sub-bursts actually were

`resolution_floor_finding.md` §2 drew a line and explicitly declined to cross it:

> *"It is not a claim that those sub-bursts are noise. Three prints inside 1.75 ms on a tape running at
> 0.30 prints/s is astronomically improbable under any stationary null. **Those clusters are real.**
> What is not real is their duration as a measured quantity."*

**The arithmetic was right and the unit of observation was wrong.** That calculation assumed three
prints were three events. Measured on the record rather than assumed:

| property of sub-millisecond runs | observed | permuted null | lift |
|---|---|---|---|
| **sequence-contiguous** | **0.933** | **0.000** | **∞** |
| price-monotone | 0.868 | 0.450 | 1.93× |
| multi-venue | 0.561 | 0.856 | **0.66×** |

*(τ = 1 ms; the null holds the run structure fixed and permutes the per-print attributes across the
session, so it asks whether these runs are coincidental collisions of independent arrivals. At τ =
0.1 ms sequence-contiguity is 0.987.)*

**Consecutive SIP sequence numbers, essentially always.** Independent arrivals from independent
participants do not get consecutive sequence numbers 93–99% of the time; one order's fills do. **One
trade occurring has probability ≈ 1, and the astronomical improbability evaporates.**

**The mechanism, corrected twice — once by the data and once by the review.**

**Condition code 14 is `Intermarket Sweep`** (public trade-conditions glossary, supplied at review
2026-09-09 and now recorded in `data/filtered/METADATA.md`; no other code in this table is established
and any other reading remains [verify]). Tuples containing it are enriched **7.0–15.5× inside
sub-millisecond runs.**

That reconciles what first looked like a contradiction. An ISO lets a taker **walk multiple price levels
on one venue** without violating trade-through protection, because they have simultaneously routed ISOs
to the protected quotes elsewhere. **So a run is the single-venue leg of a multi-venue sweep** —
single-venue, price-monotone, sequence-contiguous, ISO-flagged, with the other legs reporting as their
own separate runs.

**And the multi-venue deficit should not be read as evidence about routing, because it is partly
definitional.** Runs are defined by sequence contiguity, and one venue's fills report together, so
run-by-contiguity biases toward single-venue by construction. The 0.561-against-0.856 row is reported
above because it is what was measured, but **it does not support an inference about how orders were
routed** and is not used for one.

**So the lineage's sub-burst objects — v4's 348 ns median, 10c's 1.75 ms, 10d's 3.37 ms — were not
merely unmeasurable, which is what the resolution floor established. They were most likely not events.**
That is mechanistic rather than statistical, and it explains why eight versions of object definition
never survived a tape review: **there was no object.**

---

## 3. The Allan factor was measuring the print process and the envelope

**The premise.** "The Allan factor on this tape runs 5.99 at 15.6 ms to 1,245 at 4,096 s" is the
standing justification for *"Poisson nulls are too weak here"* and appears in the build brief, the goals
brief's traps list, and at least three derived documents.

**The control it never had.** `A(T) > 1` measures rate variation **or** clustering and does not separate
them — the same limitation as the rate channel. An inhomogeneous Poisson surrogate carrying the same
rate path and no clustering is the reference the curve has never been read against.

Regular hours, five events, v3's dyadic ladder, `min_windows = 8`:

| T (s) | raw | **10 ms collapsed** | surrogate h=30 | surrogate h=1 |
|---|---|---|---|---|
| **0.0156** | 9.79 | **0.91** | 1.00 | 1.00 |
| 0.0625 | 14.25 | 1.03 | 1.00 | 1.00 |
| 0.25 | 15.81 | 1.15 | 1.00 | 1.01 |
| 1 | 17.02 | 1.31 | 1.01 | 1.09 |
| 4 | 25.80 | 1.98 | 1.00 | **2.28** |
| 16 | 35.31 | 5.19 | 1.32 | **6.05** |
| 64 | 94.18 | 24.65 | 13.17 | **28.06** |
| 256 | 386.56 | 129.16 | 116.24 | **131.32** |
| 2048 | 5172.77 | 2173.21 | 2136.95 | **2197.96** |

**Two things, and both are corrections to the premise.**

1. **At 15.6 ms the collapsed tape reads 0.91 — Poisson, marginally sub-Poisson.** The 5.99 (9.79 on
   this cohort) was **entirely order fragmentation.** *(0.91 rather than 1.00 is the dead-time artefact
   of enforcing a 10 ms minimum spacing, which makes the process slightly more regular than Poisson at
   T ≈ 15 ms. Expected, and it is the direction that argues against clustering, not for it.)*

2. **Every remaining rung is reproduced by the `h = 1 s` surrogate**, which has the rate path and no
   clustering: 2.28 against 1.98 at 4 s, 6.05 against 5.19 at 16 s, 28.06 against 24.65 at 64 s,
   2,198 against 2,173 at 2,048 s. **The surrogate is at or above the real tape at every rung.**

**So the Allan curve on this tape decomposes completely into fragmentation at the fine end and the rate
envelope at the coarse end, with no clustering term.** The premise it supports — that Poisson nulls are
too weak here — **does not survive**, and should be struck from the documents that cite it.

*(The identity-based collapse of §2, being conservative, removes only ~30% of prints and leaves
fragmentation behind; it reduces A by a near-constant ~0.70 at every rung, which is the signature of
fragmentation multiplying A by a scale-independent factor. The 10 ms tolerance removes it fully. Both
columns are in `collapsed_tape_measures.json` and `allan_controlled.json`.)*

### 3.1 The ~10% deficit is procedure bias, from two separate mechanisms

The collapsed tape sits **below** its surrogate at most rungs, and a deficit means *more regular than
Poisson*, which would be the only positive characterisation the arc produced. It is not one. Checked
against 60 replicates per rung, with a **known-Poisson base tape pushed through the identical
procedure** — its deficit is by definition the procedure's:

| T | real A | rep median | ratio | **known-Poisson ratio** | known below p2.5 |
|---|---|---|---|---|---|
| 1 s | 1.31 | 1.09 | 1.197 | **0.933** | **5/5** |
| 4 s | 1.98 | 2.27 | 0.873 | **0.628** | **5/5** |
| 8 s | 2.74 | 3.37 | 0.812 | **0.565** | **5/5** |
| 16 s | 5.19 | 5.99 | 0.865 | **0.598** | **5/5** |
| 32 s | 11.05 | 11.75 | 0.940 | **0.790** | **5/5** |

**The known-Poisson control shows a *larger* deficit than the real tape at every one of these rungs.**
The mechanism is that `λ̂_h` is estimated from a finite realisation and then simulated from: at `h = 1 s`
and ~3 prints/s a bandwidth window holds about three prints, so the estimator's own sampling noise
becomes **genuine rate variation in the surrogate**, inflating its `A(T)` above the truth. It is visible
in the committed table without any of this: at T = 4 s the `h = 30` surrogate reads 1.00 and the `h = 1`
surrogate reads 2.28, and nothing about the tape changed between those two numbers.

**A second, separate bias holds at the finest rungs.** At T = 15.6 ms the real tape reads 0.914 and was
5/5 below the band — but the band there was built from surrogates that had **not been collapsed**. A
10 ms collapse imposes a hard 10 ms floor on every interval, and a dead time makes a process more
regular than Poisson at T comparable to it. Re-running with the replicates put through the *same*
collapse moves the band to **0.935–0.963** and the ratio to **0.949**; and the residual is
under-corrected rather than real, because the collapse bites on **60% of the real tape's intervals
against 3.5% of the control's**.

**So: no sub-Poisson finding. "No clustering term" stands, and the deficit is the procedure at every
rung** — surrogate estimation noise from 1 s to 32 s, collapse dead time at and below 31 ms.
(`subpoisson_check.json`, `deadtime_check.json`.)

---

## 4. The interval channel, which the rate channel was structurally unable to reach

The rate channel provably cannot see clumping at constant mean rate — two tapes with identical `λ̂(t)`,
one Poisson and one violently clustered, give identical rate-channel fields. **The cross-channel
divergence can, and it is the strongest tool in the module:**

```
D(t,s) = m + lograte/ln10 + γ/ln10        m = kernel-weighted mean log₁₀ inter-trade interval
```

**`D` is identically zero at every scale under a locally Poisson process at any rate path** — the
envelope cancels out of it by construction — so its sign needs no null and no surrogate. Negative means
intervals shorter than Poisson at the same rate, which is clustering. `scale_field.py` already carries
it with an acceptance test pinning the identity.

**It was run with all four controls**, because three retractions in this arc came from not having them:

| control | asks | result at s = 1 s |
|---|---|---|
| negative — homogeneous Poisson | must read 0 | **+0.034** |
| positive — `S30`, envelope only | must read 0 | +0.011 |
| **sweep** — h over 1–30 s | is the gap the tape's or the null's? | gap **−0.834 / −0.851 / −0.849** — flat |
| **blindness** — `NS05`, clusters at 0.5 s | must be seen, or the statistic is deaf | −0.013 at 1 s, **−0.252 at 512 s** |

**On the identity-collapsed tape the divergence looked like the first controlled positive result in the
arc**: −0.84 decades at s = 1 s against surrogates at ±0.01, with 98.5–100% of cells negative, and **a
gap flat across a 30× bandwidth sweep** — the exact test that killed the rate-channel claim.

**Then it failed the one axis left.** `D` uses `log₁₀ Δt`, so a 100 µs interval enters at −4 against
−0.5 for a third of a second; it is far more sensitive to residual fragmentation than the rate channel
was. Reported as a sensitivity curve rather than a chosen tolerance — **gap = real minus its own
surrogate, rebuilt from each collapsed tape**:

| collapse tolerance | prints kept | gap at s = 1 s | at 8 s | at 64 s |
|---|---|---|---|---|
| 0 ms (exact ties only) | 1.000 | −1.886 | −1.695 | −1.611 |
| 1 ms | 0.540 | −0.359 | −0.360 | −0.350 |
| **10 ms** | 0.399 | **+0.008** | **−0.003** | **−0.005** |
| 100 ms | 0.288 | +0.166 | +0.151 | +0.136 |
| identity signature (§2) | 0.699 | −0.836 | −0.767 | −0.776 |

**At a 10 ms collapse the gap is zero at every scale from 1 s to 64 s.** Not small — zero, to three
decimal places, at three scales two octaves apart. And the tolerance is not chosen to make that happen:
**1 ms brackets it from below (−0.36, under-collapsed) and 100 ms from above (+0.17, over-collapsed
into artificial regularity), and the crossing is where fragmentation ends rather than where a signal
dies.**

**The identity collapse's residual −0.84 is itself residual fragmentation** — it is conservative by
design, removing only runs it can prove are one order, so it leaves sub-10 ms prints that fail the
signature. Its gap is the part it did not remove.

**If there were clustering at 100 ms or 1 s, collapsing at 10 ms would not touch it and the gap would
stay negative. It does not.**

---

## 5. What is now established, and what is not

**Established, under controls, on this cohort:**

- Sub-millisecond print runs are one order reported many times (sequence-contiguity 0.933–0.987 against
  a null of 0.000).
- The Allan curve is fragmentation plus the rate envelope, with **no clustering term** — reproduced rung
  for rung by a rate-matched surrogate.
- Above 10 ms, **both channels find nothing beyond the envelope.** The rate channel found the envelope
  (`scale_field_instrument_gates.md` §10); the interval channel and the divergence find zero.

**Not established, and worth being precise about:**

- **This says nothing about scales below 10 ms.** CLAUDE.md already records that band as unmeasurable
  on this cohort ("zero of 100 events are admissible in the fine band"). Whether there is genuine
  ultra-fast arrival clustering underneath the fragmentation **cannot be decided from the trade tape
  alone** — it needs order-level attribution or the quote side.
- **This is five events, regular hours.** The five agree closely, and the mechanism is structural rather
  than statistical, but it is five.
- **A verified condition-code table would strengthen §2 considerably** and is unavailable offline.

---

## 6. The standing rule this arc earned

Four retractions, and **every one came from a control, not from a review.** The failure mode here is not
insufficient analytical rigour; it is insufficient controls. Adopting the review's formulation, with the
fourth row added:

> **A null that does not contain the structure you are conditioning on will score that structure as
> signal.** A control that contains too little is a false-positive machine; one that contains too much
> is a false-negative machine; the bandwidth is the dial between them. **Audit a control for what it
> contains, not only for what it randomises, and sweep the dial rather than picking a value.**

| control | asks | why it is not optional |
|---|---|---|
| **negative** | does the procedure stay quiet on structureless data? | catches a broken statistic |
| **positive** | does it fire on known structure at the scale of interest? | catches a mis-scaled read |
| **null-parameter sweep** | is the boundary the data's or the null's? | **this arc's 30 s crossover was the null's** |
| **blindness** | can it still see *anything* here, or has it been tuned deaf? | **a negative and a positive control both return "quiet" when the method works AND when it is blind — only a positive planted at the edge of detectability separates those** |

The fourth is the one that is always missing, and it is the one that made the divergence result
trustworthy enough to then falsify honestly rather than either believing or dismissing it.

---

## 7. What I would do next — a view, and one proposed decision

1. **Strike the Allan premise from the documents that cite it.** "A(15.6 ms) = 5.99, so Poisson nulls
   are too weak here" is not true after fragmentation is removed; the collapsed value is 0.91. It is
   cited in at least the build brief, the goals brief's traps list, and three of the review documents,
   and it will outlive this session in all of them.

2. **D26 is written.** The within-session timing line is closed, executing D21 §6(c) — the first time
   this question has been *closed* rather than abandoned. Cooper's draft text of 2026-09-09 is the basis;
   I edited it in three places only, each because a measurement required it: the sub-Poisson deficit is
   procedure bias and not a finding (§3.1), condition code 14 is confirmed rather than `[verify]` (§2),
   and the scope section now states explicitly why the same-day detector reopening does not conflict.
   **The `CLAUDE.md` index update that D26 requires is outstanding** — that file carries another
   session's uncommitted edit, and staging it would capture that work in an unrelated commit.

3. **If anything continues, it is the print-process question, and it is a different question.** "Is
   there ultra-fast arrival clustering underneath the fragmentation" is answerable only with order-level
   attribution or the quote side. It is interesting, it is not the momentum question, and it should be
   scoped as its own thing rather than as a continuation of this one.

4. **Do not run injection–recovery.** It would demonstrate the instrument can recover what is injected —
   which `NS05` and Gate F's calibration have already shown — without touching the question that
   actually failed.

5. **One piece of housekeeping the retraction requires.** The `rf = 1` vs `rf = 4` comparison in
   `scale_field_instrument_gates.md` §9.2 was computed against the `h = 30` surrogate that §10 retracts.
   The comparison *between* read factors survives (both face the same surrogate) but the absolute
   magnitudes do not, and it is marked accordingly rather than carried into any decision text. **The
   empty satisfiable band at `rf = 1` is unaffected** — it comes from `n_eff = 8`, `2·sd = 0.785` and
   the −1 floor, which is arithmetic with no null in it. With the answer at "nothing above 10 ms," it
   is now an **instrument property** rather than an operating decision, because there is no operating
   point left to choose between.
