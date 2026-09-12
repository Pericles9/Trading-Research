# GOING_LIVE — what this package needs before it touches the cohort

**Date:** 2026-09-09, updated 2026-09-10 for D26. **Status: BLOCKED, on three items, none of
them owned here.** Two are technical; the third is a standing decision.

Everything in `research/scale_field/detector/` has been built and validated on synthetic
tapes only. No file in this package has ever opened a real-data path, and `detect()` and
`detect_interval()` both raise rather than run without the numbers below. This file states
exactly what is missing so that landing it is a config change against tested code.

---

## The two blockers

### 1. The bandwidth-audited matched-null constant

**What is needed:** the per-scale spread of the statistic under a null whose bandwidth
content is *audited rather than assumed, and swept rather than picked*.

**Why the obvious answer is wrong.** `field_feature_extraction_methods.md` §4.3 prescribes
taking the constant from the matched null instead of the Poisson `0.87`. That is right about
the direction and, as of today, wrong about the destination: commit `1a34975` withdrew the
scale-anchored finding after the crossover was shown to track the *surrogate's* bandwidth at
roughly `3h`, with a structureless positive control reproducing the real tape's crossover to
within 0.5 s. So the object §4.3 points at is not yet a fixed reference.

**Two constants are needed, not one.** They are different statistics and the second is not a
rescaling of the first:

| channel | Poisson constant | status |
|---|---|---|
| `F` | `0.87` | wrong on this tape by roughly `sqrt(A(s))`; the Allan factor runs 5.99 at 15.6 ms to 1,245 at 4,096 s, so `z` is inflated ~2.4x at the fine end and ~35x at the coarse end |
| `G` | **`0.348`**, measured here (`measure_noise_constant()`), bounded above by `sqrt(0.5570² + 0.4343²) = 0.7063` | same status. `G` is the quieter statistic per effective print, but its Poisson constant is no more usable than `F`'s |

**Call shape once it lands** — no code change, both are already required arguments:

```python
detect(prints, t0, t1, s_lo, s_hi, noise_constant=<F null spread>, kappa=<from the null>)
detect_interval(prints, t0, t1, s_lo, s_hi, noise_constant=<G null spread>, kappa=<from the null>)
```

If the null spread turns out to be scale-dependent rather than a single number — which is
the likely outcome, since that is what an Allan factor of 1,245 implies — then
`noise_constant` becomes a callable of `s` and the four call sites inside `ridge.py` and
`interval.py` that divide by it change together. That is the one code change this blocker
could force, and it is contained.

**Config slots, already present and null:** `config/scale_field_detector.json` →
`parameters.noise_constant`, `parameters.kappa`, and the `kappa_gate` block.

### 2. The fragmentation collapse convention

**What is needed:** the rule for turning one order reported as several prints into one
arrival — identity-based or time-tolerance, and if time-tolerance, the tolerance.

**Why this package cannot proceed without it, and why it bites `G` far harder than `F`.**
`G` is built on `log10 dt`. A fragmented order contributes intervals at or near zero, which
is where the log diverges. `F` only sees fragmentation as extra local density; `G` sees it
as the single largest departure available in the statistic. **An uncollapsed fragmented tape
would produce the strongest possible clumping signal for a reason that has nothing to do
with market structure.** Since the gates thread reports a large fraction of sub-millisecond
intervals are fragmentation, this is not a small correction.

**And the collapse itself is not neutral — D26 measured this, and it cuts the other way.**
D26 EDIT 1 records that a 10 ms collapse "puts a hard floor under every interval and a dead
time is more regular than Poisson at `T` near it", and that **the collapse bites on 60% of
the real tape's intervals against 3.5% of a control's.** For `G` that is close to
worst-case: a hard floor truncates the interval distribution from below, which is precisely
where `G`'s carriers live, and it pushes the statistic toward the **`regular`** direction —
the same direction the small-`n_eff` bias already pushes it (§ "What is NOT blocked" below).
So on real tape the two-sided detector has a known bias toward `regular` from two
independent mechanisms, one of which touches the majority of carriers.

**Consequence for the convention choice, stated as a requirement rather than a preference:**
whatever collapse lands, `G` needs the dead-time floor characterised, not just applied —
the fraction of carriers at the floor, per event and per segment, reported alongside any
`G` result. A `regular`-direction detection on a collapsed tape is uninterpretable without
it.

**What this package does instead, and it is not a proposal.** `interval_carriers()` takes
`collapse_exact_ties=True`, which drops exactly-equal timestamps and nothing else. It exists
so synthetic robustness can be probed. **It is test scaffolding. It must not be read as a
recommended convention, and it is not adequate for real tape** — fragmentation on the real
cohort is not confined to exactly-equal timestamps.

**Call shape once it lands:** the collapse happens *before* the tape reaches this package.
Both entry points take a print array; a collapsed tape is simply a different array. If the
convention is time-tolerance based, the tolerance belongs in `config/scale_field_detector.json`
alongside the other frozen parameters, and the collapse function belongs wherever the gates
thread puts it — not here, because this package must not own a decision it did not make.

**One more thing D26 changes about blocker 1, and it makes the blocker harder, not easier.**
EDIT 1 also records that the sub-Poisson deficit from 1 s to 32 s is **surrogate estimation
noise**: `lambda-hat_h` is fitted to a finite realisation and then simulated from, so at
`h = 1 s` and ~3 prints/s the estimator's own noise becomes real rate variation in the
surrogate and inflates its `A(T)`. A known-Poisson base tape pushed through the identical
procedure showed a *larger* deficit than the real tape at every one of those rungs.

So sweeping the surrogate bandwidth is necessary but **not sufficient**: the surrogate has
an estimation-noise floor of its own that varies with `h` and with the local rate. Any
constant taken from it has to be shown free of that floor — which is what "audited for what
it contains, not only for what it randomises" means in practice.

---

### 3. D26 — cohort timing work is closed

**D26 (2026-09-09) closes the within-session timing line on this cohort.** It addresses this
package by name. Quoting its EDIT 3, because it is the operative sentence and paraphrase
would soften it:

> the same-day detector reopening (`fc0ef2e`, `a24fecd`) is addressed explicitly rather than
> left as a contradiction: it runs on synthetic tapes only, its two free parameters are unset
> and required without defaults so a cohort run cannot happen by accident, and it was Cooper's
> own reopening already gated on commit `1a34975`. **This decision closes cohort timing work,
> not instrument work on synthetic data, and is the gate that detector clears if it is ever
> pointed at the cohort.**

**What that means here, precisely.** Everything in this package — both channels, the G
extension of 2026-09-10 included — is inside what D26 permits, because it is instrument work
on synthetic tapes. Nothing in it is inside what D26 permits the moment it reads a cohort
tape. **Blockers 1 and 2 are technical and could in principle be cleared by the gates thread;
blocker 3 cannot be cleared by anyone but Cooper**, and clearing it means reopening a
decision taken one day ago on measured grounds.

Stated plainly so nobody has to reconstruct it later: **if the two technical blockers land
tomorrow, this detector still must not be pointed at the cohort.** D26 is the binding
constraint, and it is a decision, not a missing number.

---

## A fourth item, owned here, that is not a blocker for `F` but is one for any dense-tape claim

**`persistence_octaves` is a grid quantity, and it gates the feature count.** Found
2026-09-09; recorded as two `strict=True` xfail tests
(`test_seed_density_independence_dense_tape_F` and `_G`) and in full in
`results/scale_field/artifacts/detector/interval_synthetic_validation.json`.

The §5.1 scale polish made `s_selected` resolution-free but left the *extent* — `log2(max/min)`
over member ridge points — read off the seed ladder. Because persistence is a gate (`>= 1`
octave), the feature **count** moves with seed density wherever features are dense enough to
sit near the floor: `F` gives 6/7/7/6/7 and `G` gives 7/6/5/6/5 on a dense tape, against a
stable 2/2/2/2/2 on the two-feature tape the committed `F` test uses.

**This matters more on this cohort than it would anywhere else.** The gates thread reports no
isolated resolved feature at any scale from 8 s to 512 s — the fine structure is densely
packed and non-isolated everywhere. Dense-and-interacting is the operating regime here, so a
seed-dependent feature count is a defect in exactly the regime the detector would be used in.

**Any feature-count statistic is unsafe until this is fixed.** Per-feature quantities
(`t_ridge`, `s_selected`, `D`, `z`) are polished and safe; counts, and anything aggregated
over counts, are not. The print-count regression in
`claude/field_credibility_and_value_tests.md` §3.1 is a count statistic and would inherit
this directly.

**The fix, not attempted:** make the extent resolution-free by continuation along the ridge
to its termination scales, solved rather than read off rungs. That is a design change to
committed, tested code and needs its own decision.

---

## What is NOT blocked

The instrument itself. Both channels are built, both are tested, and the cheap results are
already in hand and do not depend on either blocker:

- `G`'s baseline is `-gamma/ln10 = -0.2506816`, verified to 1e7 draws — **not zero**, and
  nothing may be built on the assumption that it is.
- `G` sees clumping at constant mean rate at **29x** `F`'s calibrated significance on the same
  tape, which is the blindness in `F` that motivated the second channel, demonstrated rather
  than asserted.
- **`G` is not independent of the rate channel.** A pure rate gradient produces a spurious
  clumping signal of size `D = log10<lam>_w - <lam log10 lam>_w/<lam>_w`, always negative,
  matched to the closed form within ~0.005 decades. Correcting it requires choosing a
  `lambda-hat` bandwidth — which is the dependence that produced the `1a34975` retraction — so
  the correction is deliberately **not** built here.

That last point is the one to carry into the real run: **on real tape, `G` firing in the
clumped direction is not by itself evidence of clumping.** The diurnal envelope alone will
produce it, in the same direction, everywhere the rate is not flat.
