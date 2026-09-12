# GOING_LIVE's two blockers, answered — and one of them was resting on a withdrawn premise

**Date:** 2026-09-10 · **Type:** cross-thread note. Records no decision.
**For:** whoever picks up `research/scale_field/detector/`.
**Status of that package's files:** uncommitted working-tree state from another session. **Nothing here
edits them.** This is the answer, put where it can be found; landing it is that thread's call.

---

## 0. Why this exists

`research/scale_field/detector/GOING_LIVE.md` states the package is **BLOCKED on two items, neither of
them owned there**, and names the gates thread as the owner of both. Both are now answered by D26 and the
work behind it. **One of the two is not merely answered — its stated justification has been withdrawn**,
and going live on the version in that file would import a retracted premise into a live detector.

---

## 1. Blocker 2 first, because it is a clean answer

> *"the rule for turning one order reported as several prints into one arrival — identity-based or
> time-tolerance, and if time-tolerance, the tolerance."*

**Both exist and are measured. The package's instinct — that `collapse_exact_ties=True` is test
scaffolding and not adequate for real tape — is exactly right, and understated.** 40–57% of inter-print
intervals on this cohort are under one millisecond; exact ties are a small part of it.

**The identity rule** (`research/scale_field/fragmentation_identity.py::collapse_identity`): within runs
of prints separated by < 1 ms, collapse a run to one arrival if it is **price-monotone AND (multi-venue OR
sequence-contiguous)**. It is a measurement, not a convention — sub-ms runs are sequence-contiguous 0.933
of the time (0.987 at τ = 0.1 ms) against a run-structure-preserving permutation null of **0.000**, and
enriched 7–15× in condition code 14, `Intermarket Sweep`. It **retains ~70% of prints** and is
deliberately conservative: it removes only what it can prove is one order.

**The time-tolerance rule is 10 ms**, and its justification is not that a signal dies there. The
cross-channel divergence crosses zero at a 10 ms collapse **simultaneously at s = 1 s, 8 s and 64 s**
(gap +0.008, −0.003, −0.005), bracketed below by under-collapse (−0.36 at 1 ms) and above by
over-collapse into artificial regularity (+0.17 at 100 ms). **The crossing being scale-invariant is what
makes 10 ms a measured boundary of the reporting process rather than a tuned parameter.**

**Which to use depends on what the package needs**, and the two are not interchangeable:

| | identity | 10 ms tolerance |
|---|---|---|
| removes | only provable one-order runs | all sub-10 ms structure |
| keeps | ~70% of prints | ~40% |
| residual fragmentation | **yes** — divergence gap still −0.84 | none measurable — gap 0.000 |
| right for | anything needing prints to be real arrivals | **anything built on `log10 dt`** |

**For `G` specifically, use the 10 ms tolerance, not the identity rule.** `GOING_LIVE.md` is right that
`G` sees fragmentation as the single largest departure available in the statistic, and the identity
rule's conservatism leaves enough behind to produce a −0.84 decade signal that is not market structure.

---

## 2. Blocker 1 — answered, and its premise is withdrawn

> *"the per-scale spread of the statistic under a null whose bandwidth content is audited rather than
> assumed, and swept rather than picked."*

**The audit was done and it is in D26.** Sweeping the surrogate bandwidth over 1–300 s, the crossover
tracks `h` at ≈2.6h, and a structureless positive control (`S30`) returned 89.2 s at `h = 30` against the
real tape's 86.9 s. **So there is no fixed matched-null reference to take a constant from, and the file
is right to treat that as unresolved.**

**But the reason it gives for rejecting the Poisson constant no longer holds.** `GOING_LIVE.md` states:

> *"`0.87` — wrong on this tape by roughly `sqrt(A(s))`; the Allan factor runs 5.99 at 15.6 ms to 1,245 at
> 4,096 s, so `z` is inflated ~2.4x at the fine end and ~35x at the coarse end"*

**D26 withdrew that curve as a clustering measurement.** `A(T)` measures rate variation **or** clustering
and was never rate-matched. On the 10 ms collapsed tape:

| T | raw | 10 ms collapsed | surrogate h = 1 (no clustering) |
|---|---|---|---|
| **15.6 ms** | 9.79 | **0.91** | 1.00 |
| 4 s | 25.80 | 1.98 | **2.28** |
| 64 s | 94.18 | 24.65 | **28.06** |
| 2048 s | 5172.77 | 2173.21 | **2197.96** |

**At the fine end the inflation factor is not 2.4× — it is ≈1.0.** `A(15.6 ms)` falls to 0.91 once
fragmentation is removed, so on a properly collapsed tape **the Poisson constant is very nearly right at
fine scales**, and the correction the file assumes is necessary there is not.

**At the coarse end the inflation is real but it is not clustering — it is the rate envelope**, which an
`h = 1` surrogate reproduces at or above the real value at every rung. That distinction matters for what
to do next: **a clustering inflation would have to be absorbed into a constant; an envelope inflation is
better removed by conditioning on `λ̂`, which the package already understands it must not do naively.**

**So the corrected statement of blocker 1:**

- On a **collapsed** tape, `0.87` is approximately correct at fine scales and the `√A(s)` correction is
  not needed there.
- At coarse scales the departure is the envelope, and **that is precisely the dependence
  `1a34975` retracted** — so it stays unresolved, exactly as the file concludes, but for a different
  reason than the one written.
- **The file's own closing warning is the durable one and is independently confirmed:** *"on real tape,
  `G` firing in the clumped direction is not by itself evidence of clumping. The diurnal envelope alone
  will produce it."* The gates thread measured that from the other side — rate-matched surrogates read
  `D` = −0.02 to −0.29, drifting negative at coarse `s` with no clustering present anywhere. **Two
  threads, two methods, same conclusion.**

---

## 3. The third item is the one I would treat as the real blocker

`persistence_octaves` being a grid quantity makes the feature **count** seed-dependent (6/7/7/6/7 and
7/6/5/6/5 on a dense tape). `GOING_LIVE.md` already notes this bites hardest here because the gates
thread found **no isolated resolved feature at any scale from 8 s to 512 s** — every quantile of the
negative-run width sits at or below the Poisson value, never above, which is the signature of features
packed closer than `2s` and truncating each other.

**Dense-and-interacting is not one regime among several on this cohort — measured, it is the only
regime.** So a seed-dependent count is not a corner case, and I would treat it as blocking ahead of
either named blocker, for any statistic aggregated over counts.

---

## 4. What D26 does and does not say about this package

**D26 does not close it.** The decision states so explicitly: the package runs on synthetic tapes only,
its two free parameters are unset and required without defaults, and it is scoped to the instrument lane.
**D26 closes cohort timing work, not instrument work on synthetic data.**

**But D26 is the gate it clears if it is ever pointed at the cohort** — and the honest reading is that
after D26 there is no cohort timing question left for it to answer. If this package goes live, the case
for doing so has to be made on something other than "the field might find bursts", because that question
is now closed by measurement in both channels.
