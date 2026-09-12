# Detecting and marking field formations — methods, formulas, and a validated pipeline

**Date:** 2026-09-08 · **Type:** method note. Records no decision, applies no gate, touches no real data.
**Scope, as set by Cooper:** detect the *formations* in the field (not a better boolean); represent them
**resolution-free — described by functions, not pixels**; run on the **rate channel plus the interval
side**; and build it so it can go either way on becoming a signal, which means the parameters get frozen
and written down now (§10).

**What is verified here.** Every derivative formula in §1 was checked against central differences to
~1e-9. The pipeline in §5 was run end to end on synthetic tapes with injected bumps of known location and
width, plus a matched null. **All validation is synthetic and Poisson-based, which is the easy case —
§4.3 is the caveat that matters and it is not small.**

---

## 1. The one fact that makes "resolution free" possible

`λ̂(t,s)` is a sum of Gaussians over the prints, so **`F` is an analytic function of `(t, ln s)` with
closed-form derivatives of every order.** There is no grid anywhere in the mathematics. The grid in the
current build is a rendering choice that leaked into the measurement.

Write `u = ln s`, **`z_i = (t − t_i)/s`**, `w_i = exp(−z_i²/2)`, and the kernel-weighted moments

```
M_k(t,s) = Σ w_i z_i^k / Σ w_i          k = 0 … 6      (M_0 = 1)
```

Then `F = M_2 − 1`, and the two recurrences that generate everything are

```
∂M_k/∂t = ( −M_{k+1} + k·M_{k−1} + M_k·M_1 ) / s
∂M_k/∂u =    M_{k+2} − k·M_k     − M_k·M_2
```

from which, written out:

```
F     = M_2 − 1
F_t   = ( −M_3 + 2M_1 + M_2M_1 ) / s
F_u   = M_4 − 2M_2 − M_2²
F_tt  = [ −(−M_4 + 3M_2 + M_3M_1) + (2 + M_2)(1 − M_2 + M_1²) + M_1(−M_3 + 2M_1 + M_2M_1) ] / s²
F_tu  = [ (−D_3 + 2D_1 + M_2D_1 + M_1D_2) − (−M_3 + 2M_1 + M_2M_1) ] / s ,  D_k = ∂M_k/∂u
F_uu  = (M_6 − 4M_4 − M_4M_2) − 2(1 + M_2)(M_4 − 2M_2 − M_2²)
```

**One pass over the prints gives `M_0…M_6`; from those, six exact derivatives at any `(t,s)` you like.**
Verified against central differences: max relative error 2.8e-9 over 40 random probe points.

> **A convention warning, written large because it bit me while producing this document.** With
> `z_i = (t − t_i)/s`, the formulas above are correct. With `z_i = (t_i − t)/s`, **every odd `t`-derivative
> flips sign** — `F_t` and `F_tu` are wrong, `F`, `F_u`, `F_tt`, `F_uu` are unchanged, and the field itself
> looks perfectly fine. My first implementation had this exact bug and it was invisible in `F`. This is the
> same class of error `burst_on()` was created to prevent, one derivative level up. **Put the convention in
> the code once, assert it in a test on a one-sided synthetic burst, and never restate it in prose.**

### 1.1 A free result: `n_eff` needs no rate estimate

```
n_eff(t,s) = √2 · Σ_i exp(−z_i²/2)
```

That is exactly `2√π·s·λ` for a homogeneous process, but it is computed from the prints directly. **So the
admissibility boundary needs no `λ̂`, no bandwidth for `λ̂`, and no smoothing choice** — a whole layer of
arbitrariness in the current `s_min` disappears, and the `s_min` line becomes a level set of an exactly
computable function rather than an estimate of one.

### 1.2 Cost

Only prints within `±6s` matter (`e^{−18} ≈ 1.5e−8`), so with sorted timestamps and `searchsorted`, one
evaluation is O(local count). The full pipeline in §5 ran a 12,748-print session in **1.8 s**. If that ever
becomes a bottleneck, the Fast Gauss Transform gives O(N+M) for many targets at once
([Yang, Duraiswami et al., *Improved Fast Gauss Transform*](http://users.umiacs.umd.edu/~ramanid/pubs/siam_fgt.pdf)),
but on these print counts it is not needed.

---

## 2. What the field already is, and the literature that comes with that

`s²λ̂″` is the continuous wavelet transform of the point measure with the **Mexican-hat (Marr) wavelet**,
which is the second derivative of a Gaussian. So

```
F(t,s) = W_ψ(t,s) / λ̂(t,s)          ψ = second derivative of a Gaussian
```

**The field is a self-normalised Mexican-hat wavelet transform of the trade point process.** The `1/λ̂` is
what makes it dimensionless and invariant to overall activity — the property that makes split-half valid
and the property that makes it blind to level. That reframing puts four mature toolkits in reach, and all
four are about exactly the objects you want:

- **Zero-crossing fingerprints and the interval tree** — [Witkin, *Scale-Space Filtering* (IJCAI 1983)](https://www.ijcai.org/Proceedings/83-2/Papers/091.pdf). Track zero-crossings of the second derivative through scale; they form arches that can merge but never split going coarse; arch apex = characteristic scale, arch feet = extent, arch height in `ln s` = stability. **`F = 0` is exactly `λ̂″ = 0`, so the field's zero contours *are* Witkin's fingerprint.**
- **Ridges** — [Eberly, Gardner, Morse, Pizer & Scharlach, *Ridges for image analysis* (JMIV 1994)](https://link.springer.com/article/10.1007/BF01262402). The spine of a feature as a curve, defined by Hessian eigen-structure rather than by thresholding.
- **Scale selection** — [Lindeberg, *Feature Detection with Automatic Scale Selection*](https://people.kth.se/~tony/papers/cvap198.pdf). Pick a feature's characteristic scale as the extremum of a γ-normalised response over scale, rather than by a rule of thumb.
- **Maxima-line tracking and scaling exponents** — the WTMM method, [Muzy, Bacry & Arneodo](http://www.scholarpedia.org/article/Wavelet-based_multifractal_analysis). This is *literally* ridge-tracking in a continuous wavelet scale-space, and it is the standard multifractal tool in finance. **If the field turns out to be scale-free (no special row), WTMM is the method that measures that properly rather than treating it as a failure.**

None of this is exotic and all of it is 25+ years old. **The thing you built is a known object with a known toolbox; the current build is using none of it.**

---

## 3. The formations, each as an equation

| formation | defining condition | what it yields |
|---|---|---|
| **spine of a burst** (ridge) | `F_t = 0`, `F_tt > 0` | the feature's centre as a curve `t(s)` |
| **arch apex / merge point** | `F = 0` **and** `F_t = 0` | one 2×2 Newton solve finds both; every topological event in the fingerprint |
| **which one it is** | sign of `F_u · F_tt` at the solution | `> 0` = an arch closing (pair annihilates going up). `< 0` = a pair *created* going up, which the causality theorem forbids — **a free correctness check on the estimator and the mask** |
| **rate step (dipole)** | a zero contour that spans the scale range **without** closing into an arch | topological, no threshold. Sign of `F` either side gives the direction |
| **onset/decay asymmetry** | `dt/d ln s` along the spine | a measured tilt rate; on a sharp-onset/`τ=25 s`-decay synthetic it ran 0.84·s at `s=4` down to 0.34·s at `s=64` |
| **separation of two features** | scale of their merge point | closed form `s ≈ √(D²/4 − σ²)` |
| **speckle vs structure** | persistence in `ln s` + calibrated significance | §4 |

**The merge readout is the sharpest thing in this document.** Newton-solving `{F = 0, F_t = 0}` from a
crude seed recovers the separation of two injected bumps:

| true separation D | recovered merge scale | closed-form prediction | error |
|---|---|---|---|
| 80 s | 39.33 | 39.69 | −0.9% |
| 160 s | 80.46 | 79.84 | +0.8% |
| 300 s | 149.66 | 149.92 | −0.2% |

Machine precision on the residual (`|F| < 1e-15`), no grid, from a deliberately bad starting guess.

---

## 4. Deciding what is real

### 4.1 The pointwise noise scale

`sd(F) ≈ 0.87/√n_eff` (delta method; Monte Carlo confirms, optimistic below `n_eff ≈ 12`).

### 4.2 The multiscale correction — one global threshold, not one per scale

A per-cell threshold is not a chart-level threshold. Use the additive per-scale calibration of
[Dümbgen & Spokoiny, *Multiscale Testing of Qualitative Hypotheses* (Ann. Statist. 2001)](https://projecteuclid.org/euclid.aos/996986504):

```
z(t,s)   = −F(t,s)·√n_eff(t,s) / 0.87
cal(t,s) = z(t,s) − √( 2·ln( T_span / s ) )
```

and compare `cal` to **one** global κ across all scales. That is what makes structure at 3 s and structure
at 300 s comparable under a single decision. It is the same idea as
[SiZer](https://www.researchgate.net/publication/224817266_SiZer_for_Exploration_of_Structures_in_Curves) —
which is the closest published relative of your whole panel, and worth reading for how it renders the map
as significance rather than as the statistic.

### 4.3 **The caveat that must not be skipped**

**`0.87/√n_eff` is a Poisson result.** On a tape whose Allan factor runs 5.99 at 15.6 ms to 1,245 at
4,096 s, the true `sd(F)` is larger — roughly by `√A(s)` — so every `z` above would be **inflated by a
factor of about 2.4 at the fine end and ~35 at the coarse end**, and κ would be meaningless.

**This is the exact error the scale-space arc made twice, and I am reproducing its shape here on purpose so
it is visible rather than buried.** The formulas in §4.1–4.2 give the correct *functional form* — how
significance should scale with `n_eff` and with `s`. **The constant must come from your existing matched
null (the phase 10b T3c machinery: rate-matched inhomogeneous Poisson draws from each event's own
intensity, 200 draws, reported as a family over bandwidth), not from 0.87.** Substitute the measured
per-scale null spread for `0.87/√n_eff` and everything else in this document stands unchanged.

### 4.4 Persistence

"Vertical persistence" has a proper name: [Edelsbrunner, Letscher & Zomorodian, *Topological Persistence
and Simplification* (2002)](https://pub.ista.ac.at/~edels/Papers/2002-04-TopologicalPersistence.pdf).
Two filtrations are natural here — the octaves a spine survives, and the depth of a minimum below the
lowest saddle joining it to a deeper one (topographic prominence, computable in O(n log n) per slice).
**Speckle has low persistence by construction**, which is why persistence is the right filter and a
magnitude threshold alone is not.

---

## 5. The pipeline — and the ordering result, which was not obvious

I built it the natural way first: **trace the `F = 0` fingerprint, extract arches, then filter.** On a
12,748-print synthetic tape with two injected bumps, that produced **157 apexes**, of which the filter kept
**one — an edge artifact at the analysis boundary — and lost both real bumps.**

The reason is in the noise ruler: noise arches have the same *shape* as real arches, so a topology built on
the raw zero set is a topology of noise, and the linking across scales is meaningless before the noise is
gone.

**The correct order is ridges first, calibrate, then group.**

```
1  SEED     coarse ladder (~6 rungs/octave). At each s, scan t for local minima of F.
            The grid exists ONLY here, and only to seed. It never touches a reported number.
2  POLISH   Newton on F_t = 0 using exact F_t, F_tt  ->  t to ~1e-10·s. Reject if F_tt <= 0.
3  GUARD    require |t - edges| > 6s   (cone of influence — the raw pipeline's one survivor
            was an edge effect, so this is not optional)
4  CALIBRATE  z and cal per §4; drop cal <= kappa; drop n_eff < 8
5  GROUP    surviving ridge points into features: same feature if |Δt| <= max(s, s')
6  DESCRIBE  characteristic scale = argmax of cal over the spine (Lindeberg scale selection);
            persistence = octaves spanned; duration = §6; tilt = dt/d ln s along the spine
7  POLISH s  bisect dcal/du = 0 along the ridge  ->  see 5.1.  WITHOUT THIS STEP THE METHOD
            IS NOT RESOLUTION-FREE AND THE HEADLINE CLAIM OF THIS DOCUMENT IS FALSE.
```

### 5.1 Scale polishing — a correction to the first version of this document

**The first version of this pipeline stopped at step 6 and I claimed the result was resolution-free. It was
not, and a seed-independence test caught it in under a minute.** Step 2 polishes `t` to ~1e-10 by Newton,
but the *scale* was left snapped to whichever seeding rung maximised `cal`. Varying the seed ladder from 3
to 12 rungs per octave moved `s*` by up to **8.6%** and `cal` by 0.67 — small enough to look like noise,
large enough to make every duration comparison across events meaningless.

The fix is one more 1-D solve, using derivatives that were already available:

```
n_eff = √2·Σw          ⇒   ∂n_eff/∂u = n_eff · M_2          (because ∂w/∂u = w·z²)
z     = −F·√n_eff/0.87 ⇒   ∂z/∂u     = −(√n_eff/0.87)·( F_u + F·M_2/2 )
cal   = z − √(2 ln(T/s)) ⇒ ∂cal/∂u   = ∂z/∂u + 1/√(2 ln(T/s))
```

Bisect `∂cal/∂u = 0` along the ridge (re-polishing `t` at each trial `s`). After that step the same
seed-density sweep gives **|Δt| < 5e-12 s, |Δ ln s| < 5e-13, |Δcal| < 1.5e-14** — the seeding grid provably
touches no reported number, which is what the claim required all along.

**Both this defect and its fix belong in the record**, because the defect was in exactly the property the
document argued hardest for, and it was invisible in every output until it was tested for directly.

**Result on the same tape** (`κ = 1.0`, persistence ≥ 1 octave, 1.8 s; values below are pre-§5.1, so
`s selected` moves slightly once scale polishing is applied — `t`, counts and the null result do not):

| found t | true t | s selected | F | n_eff | calibrated | octaves |
|---|---|---|---|---|---|---|
| 499.99 | 500 | 36.8 | −0.630 | 2,410 | 32.9 | 4.5 |
| 900.10 | 900 | 93.6 | −0.515 | 5,168 | 40.2 | 2.7 |

Two injected, two found, **locations exact to a tenth of a second**. On a matched null (flat 6/s Poisson,
8,849 prints, identical settings): **zero detections.**

A four-bump tape, widths 4 / 12 / 35 / 90 s: **4 detections, 4 injected, no false positives**, locations
within 0.6 s.

---

## 6. The duration readout — the `−0.5` contour is biased, and the fix is a two-parameter fit

The `−0.5` crossing is exact only for a bump with no background. With background it reads high, and the
bias grows with the bump's width. **Fit the closed form along the spine instead:**

```
F(s) = −( s² / (σ² + s²) ) · 1 / ( 1 + c·√(σ² + s²) )        c = b√(2π)/N
```

Two parameters — the width `σ` and the background-to-burst ratio `c`. The `−0.5` rule is its `c = 0`
special case, which is precisely why it reads high.

| true σ | `−0.5` crossing | error | model fit | error |
|---|---|---|---|---|
| 4 s | 4.56 | **+14%** | 3.56 | −11% |
| 8 s | 10.22 | **+28%** | 7.83 | −2% |
| 12 s | 14.80 | **+23%** | 11.90 | −1% |
| 35 s | 42.71 | **+22%** | 33.41 | −5% |
| 40 s | 74.10 | **+85%** | 42.46 | +6% |
| 90 s | never reached −0.5 | — | 75.18 | −16% |

**The contour readout fails outright on the widest feature and is biased +14 to +85% on the rest; the fit
is within 20% everywhere and within 5% in the middle of the range.** This supersedes the `−0.5` readout I
recommended in `scale_field_price_layouts.md` §4.1 — that one is a first look, not a measurement.

> **Corrected 2026-09-09, and the table above is left as it was measured.** That sentence read *"within
> 16% everywhere and within 6% in the middle of the range"*, which the table supported — but the table
> predates §5.1, as this section's own preamble says. Re-run through the promoted implementation
> (`research/scale_field/detector/`, which applies the scale polish before fitting), the mid-range
> improves and the widest degrades: `σ = 4 s` goes −11% → **−1.8%**, `σ = 12 s` −1% → **+0.1%**,
> `σ = 35 s` −5% → **−4.9%**, and `σ = 90 s` −16% → **−18.9%**. The widest feature remains the weakest
> case for this readout at any stage of the pipeline. Evidence:
> `results/scale_field/artifacts/detector/synthetic_validation.json`.

---

## 7. The interval side

Same machinery, different carrier, and it stays clear of the degeneracy that killed `D`.

**Do not threshold an absolute Poisson reference.** Instead define the **channel contrast**

```
G(t,s) = E_w[ log₁₀ Δt ]  −  ( −log₁₀ λ̂(t,s) )
```

— the kernel-weighted mean log interval against what the local rate implies. Under a locally Poisson tape
`G` is a **constant** (`−γ/ln10 = −0.2507`); on your tape it sits about 1.3 decades off it, everywhere.
**That offset is exactly why `G` must not be used as a boolean — and it does not matter at all if you
detect *structure in* `G` rather than thresholding `G`.** Ridges, apexes, persistence, §4 calibration:
identical pipeline, and the absolute offset cancels because every one of those operators is a derivative.

`G` needs the same moment machinery with an extra weighted sum `Σ w_i x_i`, `x_i = log₁₀ Δt_i`, so the
derivative recurrences carry over with one more index. **A feature in `G` with no matching feature in `F`
is clumping at unchanged mean rate** — the case the rate field cannot see, and the case the ITT mockup
showed produces speckle rather than a trumpet.

---

## 8. Output — the thing that makes it vector

Each detected formation becomes a row, not a region of shading:

```
event_id, channel(F|G), kernel(centred|trailing),
t_ridge, s_selected, sigma_fit, c_fit, fit_rss,
F_min, n_eff_at_min, z, calibrated, kappa_used,
persistence_octaves, tilt_dt_dlns, class(bump|void|step|merge),
merge_partner_id, merge_scale, apex_residual, edge_guard_ok
```

**That table is the resolution-free representation.** The render is then generated from it — spine as a
polyline, arch as the contour traced by continuation between the apex and the guard, feature footprint on
the price axis as `±√(σ̂² + s²)` — all SVG paths, sharp at any zoom, with no render-column artefacts and no
`vrect` blocks. And because it is a table, features become comparable across events, sortable, and
regressable, which shaded rectangles never were.

**Contour tracing, when you want the outline:** pseudo-arclength continuation on `F(t,u) = 0` using the
exact `(F_t, F_u)` as the tangent, with a Newton corrector normal to it. Step size adapts to curvature.
This is where "described by a function, not pixels" is literal — the curve is refined to whatever tolerance
you ask for, from the same closed form.

---

## 9. What I would use, in order

1. **§1 machinery + its convention test.** Everything else is built on it and it is a day's work.
2. **§4.3 first, not last** — replace `0.87` with your matched-null spread before any κ is chosen. Choosing
   κ against a Poisson constant is the failure this arc has already had twice.
3. **§5 pipeline** on the rate channel, with the edge guard.
4. **§6 fit** as the duration readout, with §5's `−0.5` value reported alongside it as a diagnostic.
5. **§7** on the interval side, and the `F`-vs-`G` disagreement as its own reported quantity.
6. Injection–recovery from `field_detects_or_noise.md` §4, now aimed at this detector rather than the
   boolean — the recovery surface over (duration × amplitude) is what turns κ into a stated detection limit.

---

## 10. Freezing, since the scope is undecided

Everything below is a free parameter. **If this may become a signal, these get committed before the first
run on real data**, and nothing here is chosen by looking at an outcome:

| parameter | proposed value | basis |
|---|---|---|
| `CUT` (kernel truncation) | 6 | `e^{−18}` ≈ 1.5e−8, numerical not statistical |
| seed ladder density | 6 rungs/octave | below the noise correlation length in `ln s` (~1.0–1.4) |
| `n_eff` floor | 8 | inherited; §4 argues for 12–27, **that change needs its own decision** |
| edge guard | `6s` from each end | same constant as `CUT` |
| κ | **from the matched null, not chosen** | §4.3 |
| persistence floor | 1 octave | measured noise decorrelation is 1.0–1.4 octaves in `ln s` |
| grouping radius | `max(s, s')` | the kernel's own width; no free number |
| scale range | `[s_min, session/8]` | already on the record from the build brief |

**Seven of the eight are derived from something rather than chosen, and the one that is not (κ) is the one
that must come from the null.** That is a defensible pre-registration surface, which the current
`read_factor` + debounce pair is not.

---

## 11. What I am not claiming

- **Everything measured here is synthetic**, and synthetic in the friendly way: Poisson background with
  Gaussian bumps. Your tape is 1.3 decades from Poisson. **The pipeline's zero false positives on a matched
  Poisson null says nothing about its false-positive rate on your tape** — that is what §4.3 and the
  injection–recovery build are for.
- **Detection is not measurement.** The pipeline localises well and estimates duration to ~10% on synthetic
  data where a duration exists. Whether a duration exists on the real cohort is the standing open question,
  and §2's WTMM note is the honest route if the answer is no.
- **None of this is causal.** Centred kernels read forward by ~`s`. The trailing-kernel version halves
  `n_eff` (`n_eff = √π·s·λ`, so the floor doubles) and loses the causality theorem entirely, so §3's
  correctness check does not apply to the online pane.
- **Nothing here touches tradeability.** A detector with a stated detection limit is a better instrument,
  not evidence of an edge.

---

## Sources

- [Witkin, *Scale-Space Filtering*, IJCAI 1983](https://www.ijcai.org/Proceedings/83-2/Papers/091.pdf) — zero-crossing contours through scale, the arch/interval-tree construction, stability as arch height.
- [Eberly, Gardner, Morse, Pizer & Scharlach, *Ridges for image analysis*, JMIV 1994](https://link.springer.com/article/10.1007/BF01262402) — the height-ridge definition used in §3.
- [Lindeberg, *Feature Detection with Automatic Scale Selection*, IJCV 1998](https://people.kth.se/~tony/papers/cvap198.pdf) — γ-normalised scale selection; §5 step 6.
- [Lindeberg, *Edge Detection and Ridge Detection with Automatic Scale Selection*, IJCV 1998](https://link.springer.com/article/10.1023/A:1008097225773) — the ridge-plus-scale-selection combination.
- [Chaudhuri & Marron, *SiZer for Exploration of Structures in Curves*, JASA 1999](https://www.researchgate.net/publication/224817266_SiZer_for_Exploration_of_Structures_in_Curves) — significance-as-the-map; the closest published relative of your panel.
- [Dümbgen & Spokoiny, *Multiscale Testing of Qualitative Hypotheses*, Ann. Statist. 2001](https://projecteuclid.org/euclid.aos/996986504) — the additive per-scale calibration in §4.2.
- [Edelsbrunner, Letscher & Zomorodian, *Topological Persistence and Simplification*, DCG 2002](https://pub.ista.ac.at/~edels/Papers/2002-04-TopologicalPersistence.pdf) — persistence as the principled feature filter.
- [Muzy, Bacry & Arneodo — wavelet-based multifractal analysis (WTMM), Scholarpedia](http://www.scholarpedia.org/article/Wavelet-based_multifractal_analysis) — maxima-line tracking in a continuous wavelet scale-space; the method for the scale-free case.
- [Yang, Duraiswami, Gumerov & Davis, *Improved Fast Gauss Transform*](http://users.umiacs.umd.edu/~ramanid/pubs/siam_fgt.pdf) — O(N+M) Gaussian summation, if evaluation ever becomes the bottleneck.
