# Testing the detector — credibility and value are two different questions

**Date:** 2026-09-09 · **Type:** test design + one executed result. Records no decision, applies no gate.
**Concerns:** the ridge-first feature detector in `claude/field_feature_extraction_methods.md`.

---

## 0. The distinction, and why conflating it is how instruments survive too long

**Credibility:** does it measure what it claims to measure?
**Value:** does what it measures carry information that is not already available more cheaply?

**An instrument can be perfectly credible and completely worthless.** The rate field may be exactly that —
a correct, precise, well-calibrated measurement of the curvature of the trade rate, which is a restatement
of the trade rate. Every test in §2 could pass at machine precision and the answer to "should we use this"
could still be no.

The two also have opposite cost profiles. **Credibility tests are cheap, mostly need no tape and no null,
and produce yes/no answers. Value tests are expensive and need the matched null.** The tempting order is
therefore all of §2 then all of §3 — and that is wrong, because §3.0 is the cheapest test in this document
and it is the one that can make the rest pointless. **Order by cheapest-killer-first across both
categories, not category by category.** §6 gives that order.

---

## 1. What happened when I ran four of these on my own work

Before writing this I ran the §2A battery against the detector I handed over on the 8th. Four tests,
about a minute of compute:

| test | prediction | result |
|---|---|---|
| input-order permutation | bitwise identical output | **pass**, bitwise |
| time rescaling (`t → c·t`, `c = 10±³`) | `t*`, `s*` scale by `c`; `F`, `n_eff`, `z`, `cal` **unchanged** | **pass** — errors 1e-16 |
| 50% thinning ×3 | `F` invariant, `n_eff` halves ⇒ `z` ratio `1/√2 = 0.707`; **no new feature may appear** | **pass** — 0.700 / 0.694 / 0.722, zero new features |
| seed-density independence (3→12 rungs/octave) | every reported number identical | **FAIL** |

**The seed test failed, and it failed in exactly the property the document argued hardest for.** Locations
were fine; the *selected scale* moved by up to **8.6%** and the calibrated significance by 0.67, because
`t` was Newton-polished to 1e-10 while the scale was left snapped to whichever seeding rung happened to win.
Small enough to read as noise. Large enough to make duration comparisons across events meaningless — which
is the one thing the detector exists to produce.

Diagnosed and fixed in the same sitting (a bisection on `∂cal/∂u = 0`, derivatives already in hand); after
the fix the same sweep gives `|Δ ln s| < 5e-13`. Recorded as §5.1 of the methods doc.

**That is the argument for this whole document, made concretely: a one-minute test found a real defect in a
day-old deliverable, and the defect was invisible in every output until something looked for it directly.**
It also raises the prior that there are more.

---

## 2. Credibility battery

### 2A. Free, self-consistent, no tape and no null

Each is a unit test with a **pre-registered exact prediction**, which is what makes it a test rather than
an inspection.

| test | exact prediction | status |
|---|---|---|
| analytic derivatives vs central differences | agreement to ~1e-9 | done, 2.8e-9 |
| **`z`-convention test** | on a one-sided synthetic burst, `F_t` has a known sign | **not yet written, and it is the one that already bit me** |
| input-order permutation | bitwise identical | done |
| time rescaling | exact, per §1 | done |
| uniform thinning | `z` ratio `1/√2`, no new features | done |
| seed-density independence | identical to solver tolerance | done after the §5.1 fix |
| **forbidden-sign count** | `sign(F_u·F_tt) < 0` must occur **zero** times on the centred kernel — the causality theorem forbids creation going coarse | not run |
| **trade-weighted zero-sum** | `Σ_prints F = 0` at every scale, since `∫λ̂″ dt = 0` | not run |
| **two independent code paths** | moment-recursion vs FFT convolution must agree to ~1e-9 | **not run, and I introduced a `dt²` scaling bug in an FFT path this week** |

The last three are hours of work and they are the ones with a demonstrated failure rate.

### 2B. Against the record — the house reconciliation gate

- **Allan reconciliation.** The detector's `λ̂` machinery must reproduce v3's committed Allan-factor curve
  rung for rung on the same dyadic ladder. Divergence means the point-process handling differs and
  everything downstream is uninterpretable. **Hard stop**, same as the build brief's gate.
- **Agreement with `burst_on()`.** Run both on the same events. They will disagree; the useful output is
  *where*. If the new detector's features sit inside old marks, it is a refinement. If they sit somewhere
  else entirely, one of the two is reading the boundary and the disagreement localises which.

### 2C. Against ground truth you install — blind injection–recovery

The real build, and the protocol matters more than the machinery:

1. A script takes real event tapes and superposes injected bursts of known `(t, σ, amplitude)` on a
   pre-registered grid over the band the cohort supports (~1 s to a few hundred s).
2. **Half the tapes get nothing. The assignment and the seed are written to a file and not looked at.**
3. The detector runs at the committed `κ`.
4. Unblind and score.

Three outputs: the **recovery surface** over (duration × amplitude); **localisation error** in seconds and
in `s_min`; and the **false-alarm rate on the un-injected half**. The headline is **the detection limit —
the smallest burst this detector reliably finds on this tape at this operating point.** That number does
not currently exist anywhere in the programme, and `resolution_floor_finding.md` §2 explicitly left the gap
open in writing.

**Include injections near session boundaries.** The unpolished pipeline's single surviving detection on a
synthetic tape was an edge artifact. That failure mode is not hypothetical here; it is observed.

---

## 3. Value battery — the harder half

### 3.0 The precondition: is there a characteristic timescale at all? — and it is a reconciliation

**This is the cheapest test in this document and the one that can make everything else moot.** Run the
detector across the cohort, histogram `s*` in `ln s`, and compare against the same histogram from matched
nulls. If the two are the same shape, the features are the detector's own bandpass and there is nothing to
find.

**It is also a free reconciliation between two independent measurements already on the record, and that
makes it falsifiable in advance.** v3 reported Allan knees at **128.0 s regular hours and 16.0 s
premarket** (print rate). The build brief already recorded those as *a prediction for the continuous
field*. So:

> **Pre-registered prediction: the `s*` histogram should show excess mass near 128 s on regular-hours
> events and near 16 s on premarket events, relative to matched nulls. If it does not, one of the two
> measurements is wrong, and that is the finding.**

That is worth more than most of the rest of this document because it is cheap, it is decisive, it uses only
committed artifacts, and it can fail.

Segments are not poolable — 0.903 decades of separation, already failure row 5.

### 3.1 The restatement battery — historically the killer, so it runs first among the value tests

Regress each reported parameter on the cheapest thing that could explain it, log-log. This is the shape
that has killed four things in this programme.

| dependent | regressor | what a slope near 1 with high R² means |
|---|---|---|
| **feature count per session** | print count | **the Arm A failure, a fourth time** |
| `σ̂` | 2nd–5th percentile of the local interval distribution | the duration statistic restates a low interval quantile — the exact test `resolution_floor_finding.md` §3 proposed for the old one |
| `σ̂` | `1/λ̂` locally | the readout is the boundary in disguise |
| feature `t*` | D7 anchor times | the detector finds the thing you used to define the event |

> **Pre-registered prediction on the first row, and it is sharp.** The Dümbgen–Spokoiny penalty
> `√(2 ln(T/s))` exists precisely to hold the per-session false-alarm rate constant as the number of
> independent cells grows. **So the slope of feature count on print count should be near zero, not near
> one.** If it comes back near one, the local reference did not remove the mechanism it was introduced to
> remove, the penalty is not doing its job, and no further work on the field is warranted until that is
> understood.

**Also report partial R²**: how much variance in `σ̂` survives conditioning on the local rate. If ~0, there
is no incremental information regardless of how well every other test went.

### 3.2 Feature-level split-half — the strongest cheap value test

`field_detects_or_noise.md` §1 proposed split-half on the **field**. **Do it on the feature list instead**,
which is much stronger: split prints into halves A and B, run the detector independently on each, and ask
what fraction of A's features have a match in B — same `t*` within `max(s, s′)`, same `s*` within a stated
factor.

Report the matched fraction **as a curve against `cal`**, not as one number, because the thinning test
already establishes that `z` falls by `√2` on a half tape: raw count *must* drop, and a single number would
read that as unreliability. What matters is whether the features that survive are the *same* features.

No null model, no ground truth, no threshold. A day.

### 3.3 Does it compress? — a value test that needs no forward returns

Fit two point-process models on a training segment and compare **held-out** log-likelihood on segments not
used for fitting:

- **(a)** smooth inhomogeneous Poisson, rate at a fixed bandwidth.
- **(b)** the same, plus the detected features as parametric bumps at their fitted `(t*, σ̂, amplitude)`.

**If (b) does not beat (a) out of sample, the features are not structure.** Held-out, not in-sample, and
count the parameters honestly — (b) has more.

This is the piece I think is missing from the programme's toolkit: **a way to say a descriptive object is
worth something without going anywhere near a return.** It also has a clean interpretation — the features
are worth exactly the bits they save.

### 3.4 Cross-event recurrence

Do features recur with consistent parameters across events of a class? Compare the joint distribution of
`(σ̂, depth, tilt, persistence)` on real events against the same from matched nulls. Indistinguishable
means no object, however precisely each individual one was located.

### 3.5 Predictive value

Costs pre-registration and the full standard. **Do not touch it until 3.0–3.4 have passed.** The line in
the build brief is unambiguous and this is the moment it applies.

---

## 4. The benchmark ladder — what it actually has to beat

Value is always relative to the cheapest thing that could replace it. In cost order:

| rung | method | cost |
|---|---|---|
| 0 | nothing — a constant | zero |
| 1 | print count | zero |
| 2 | `λ̂` above a fixed threshold at a fixed bandwidth | trivial |
| 3 | excursion above the event's own envelope (D8's object) | small |
| 4 | current `burst_on()` | built |
| 5 | the ridge detector | this arc |

**Every value test in §3 should be reported for rungs 2, 3 and 5 side by side.** A method that does not
beat rung 2 is not worth its complexity, whatever its credibility — and the honest possibility is that
`s²λ̂″/λ̂` is a sophisticated way of finding the tops of rate excursions, which rung 3 finds directly with a
fraction of the machinery.

---

## 5. Decision table

| test | outcome | action |
|---|---|---|
| 2A forbidden-sign or zero-sum | fails | estimator or mask bug. Stop and fix; nothing downstream is interpretable |
| 2B Allan reconciliation | diverges | **hard stop**, per the build brief |
| 3.0 `s*` histogram | matches the null | **no characteristic timescale.** Stop the detector line; the honest continuation is WTMM/scaling-exponent work, which measures scale-freeness instead of fighting it |
| 3.0 `s*` histogram | excess near 128 s / 16 s | two independent measurements agree. Strongest positive result available at this cost |
| 3.1 count vs print count | slope ≈ 1 | **Arm A, fourth occurrence.** Stop everything until the mechanism is understood |
| 3.1 `σ̂` vs interval quantile | slope ≈ 1, high R² | the duration statistic is a restatement. The detector may still locate well; the duration output is retracted |
| 3.2 split-half | matched fraction low at high `cal` | the output is not reproducible on its own data. Stop |
| 3.3 held-out likelihood | (b) ≤ (a) | features are not structure. Retire the object, keep the instrument note as a negative result |
| 2C injection–recovery | detection limit far above what the cohort contains | the detector is correct and inapplicable — rename, record the limit, stop |
| all pass | — | then, and only then, §3.5 with pre-registration |

---

## 6. Order and cost

1. **§3.0 — the `s*` histogram against matched nulls.** Hours. Decisive. Reconciles two committed results.
2. **§3.1 — count vs print count.** Hours. Committed artifacts only. Historically the killer.
3. **§2A — the three unrun free tests** (convention, forbidden sign, zero-sum, two code paths). Hours.
4. **§2B — Allan reconciliation.** A day. Hard stop.
5. **§3.2 — feature-level split-half.** A day. No null needed.
6. **§3.3 — held-out likelihood.** Days.
7. **§2C — blind injection–recovery.** The real build. Only worth starting once 1–6 say the instrument is
   worth characterising.

Note that **the two cheapest things in the list are both value tests, not credibility tests.** That
inversion is deliberate.

---

## 7. The base rate, stated plainly

This programme has killed four things with this shape, three of them for the same mechanism. The prior on
a new detector in the same family surviving all of §3 is not high, and the tests above are ordered so that
the most likely killers run first and cheapest.

**That is not an argument against building it.** It is an argument for not building §2C before §3.0 and
§3.1 have run, because §2C is weeks and §3.0 is hours.

---

## 8. What none of this tests

- **Tradeability.** Nothing here, including every test passing, is evidence of an edge.
- **Timing.** Centred kernels read forward by ~`s`. Relative orderings survive; no absolute timing claim
  does. The trailing-kernel variant halves `n_eff` and loses the causality theorem, so §2A's forbidden-sign
  check does not apply to it.
- **The synthetic validation transfers.** Every number in §1 came from Poisson tapes with Gaussian bumps.
  Your tape sits ~1.3 decades from Poisson. Passing invariance tests on synthetic data says the *code* is
  right; it says nothing about the *calibration*, which is why `κ` must come from the matched null.
- **Whether the object exists.** A perfect detector on a tape with no characteristic timescale finds
  nothing, and that is a correct result rather than a failure of the detector. §3.0 is the test that
  distinguishes those two, and it should not be run after the expensive work — it should be run first.
