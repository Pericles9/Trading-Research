# What the shapes in the scale field mean — a reading grammar derived from the statistic

**Date:** 2026-09-07 · **Type:** derivation. Records no decision, applies no gate, runs on no data.
**Occasioned by:** Cooper's question — the panels show a lot of visual structure and there is no stated
rule for what any of it means.
**Method:** everything below comes from writing the statistic in closed form and reading its consequences.
Every identity quoted was checked numerically against a direct evaluation of the estimator on synthetic
intensity functions; agreement is exact to plotting precision. **No claim here is about your tape.**

**Convention note that changes every number by 2.3×.** I take the field as `F = ∂ ln λ̂ / ∂ ln s` —
**natural** log on both. If the code uses `log₁₀ λ̂` against `ln s`, every value below is multiplied by
`1/ln 10 = 0.434` and the lower bound is −0.434 rather than −1. Confirm which before using any threshold
from this document. The *shapes* are unaffected; only the numbers move.

---

## 1. The statistic, written three ways

With a Gaussian kernel of width `s`, `z = (t − tᵢ)/s`, `w = exp(−z²/2)`, and
`λ̂(t,s) = (1/s√2π) Σ w`:

| form | what it says |
|---|---|
| **(A)** `F = E_w[z²] − 1` | how spread out the prints are inside the window, against the spread a flat rate would give |
| **(B)** `F = s²·λ̂″/λ̂` | **the sign of F is exactly the sign of the curvature of the smoothed trade rate** |
| **(C)** `F = s²(ln λ̂)″ + (s·(ln λ̂)′)²` | curvature of log-rate, plus the square of its slope |

(A) and (B) are the same object because the properly normalised Gaussian satisfies the heat equation,
`∂λ̂/∂ln s = s²·∂²λ̂/∂t²`. (C) is (B) expanded via `λ̂″/λ̂ = (ln λ̂)″ + ((ln λ̂)′)²`.

**Five properties fall straight out, and they govern everything else:**

1. **`F ≥ −1`, with equality only if every print in the window sits at the same instant.** Bounded below.
2. **`F` is unbounded above.** A window with a hole in the middle and prints at `|z| = 3` gives `F ≈ 8`.
   The statistic is violently asymmetric: bursts saturate, voids do not.
3. **`F = 0` under any locally flat rate**, exactly, with no distributional assumption. This zero is
   arithmetic about the kernel, not a Poisson reference — which is why it is safe where the two
   Poisson-referenced constructions in this arc were not.
4. **`F` is invariant to `λ → c·λ` for any constant `c`.** Doubling every print in the session changes
   nothing. **The field cannot see how busy the tape is. It sees only the shape of the rate envelope.**
5. **`F < 0` ⟺ `λ̂` is concave at `(t, s)`.** "Burst on" means, precisely and only, *the smoothed trade
   rate is curving over here at this scale*.

Property 5 is the one to internalise, because it is much narrower than "there is a burst here."

---

## 2. The shape dictionary

### 2.1 A rate bump — the trumpet

Take a Gaussian rate bump of width `σ`. Then `λ̂` is Gaussian of width `√(σ² + s²)` and the field is
available in closed form:

```
F(t,s) = −s²/(σ²+s²) + s²t²/(σ²+s²)²
```

Two readings come out of this, both exact:

- **At the centre, `F(0,s) = −s²/(s²+σ²)`.** This passes through **−0.5 exactly at `s = σ`**, and its
  descent in `ln s` is steepest exactly there. **The scale at which the field first reaches −0.5 over
  the burst centre is the burst's Gaussian width.** That is a parameter-free duration readout, and it
  is the only one in this construction that does not depend on amplitude.
- **The negative region at scale `s` has half-width `√(σ² + s²)`.** Below `s ≈ σ` that is flat at `σ`;
  above it, it grows as `s`.

So a bump draws a **trumpet**: vertical-sided at fine scales, flaring open above `s ≈ σ`.
**The height of the flare is the duration. The centre of the column is the location.**

Depth saturates: `−0.8` at `s = 2σ`, `−0.94` at `s = 4σ`. Beyond that the field is telling you the
kernel is much wider than the feature — nothing about intensity. **A very dark cell is a narrow feature,
not a violent one.**

| `s/σ` | `F` at centre |
|---|---|
| 0.25 | −0.059 |
| 0.5 | −0.200 |
| **1.0** | **−0.500** |
| 2.0 | −0.800 |
| 4.0 | −0.941 |

**Caveat that matters operationally:** to see the flat-sided base you need scales *below* `σ`. With
`s_min = 2.26/λ̂`, durations under roughly `2–3 × s_min` show only their flare, and their duration is not
readable. Bursts shorter than that are detectable but not measurable — which is the resolution-floor
result restated in the geometry.

### 2.2 A rate step — the dipole with no apex

A step in rate produces `λ̂″` of one sign on one side and the other sign on the other, with a zero at
the step. Verified on a sharp 4× step up with `s = 50`:

| `t` | −100 | −50 | −20 | 0 | +20 | +50 | +100 |
|---|---|---|---|---|---|---|---|
| `F` | +0.30 | **+0.49** | +0.22 | 0.00 | −0.15 | **−0.21** | −0.08 |

**Blue-then-red, straddling a time, is a rate increase. Red-then-blue is a rate decrease.** The lobes
sit at `±s` and the whole pattern scales with `s`, so **it opens upward forever and never closes into an
apex**. That is the discriminator:

> **A single-signed feature that closes to an apex is a bump and has a duration.
> A two-lobed feature that opens without ever closing is a step and has none.**

### 2.3 Any monotone rise or decay — positive, always

Set curvature to zero in form (C): on a log-linear rate ramp `F = (s·(ln λ̂)′)² > 0`.

- **Exponential decay** `λ ∝ e^{−t/τ}` gives `F = (s/τ)²`, positive everywhere.
- **Omori / power-law decay** `λ ∝ t^{−p}` gives `F = s²p(1+p)/t²`, positive everywhere. Checked at
  `p = 0.6`: predicted 0.0096, measured 0.0100.

**Consequence, and it is a big one.** A Hawkes-style event — sharp onset, long power-law relaxation —
puts a **thin negative sliver at the onset and a broad positive region over the entire decay tail**.
The field does not mark the aftermath of an event as a burst. It marks the instant the rate stops
climbing. **"Positive" does not mean "quiet." Most of the visible aftermath of a real event is positive.**

### 2.4 Two features — the merge, and where it happens

Two bumps of width `σ` separated by `D` sit as two negative columns with a positive ridge between them.
The ridge vanishes and they merge into one when

```
s ≈ √(D²/4 − σ²)
```

Checked at `σ = 5`, `D = 100`: predicted merge at `s = 49.7`, the centre field crosses zero between
`s = 48` and `s = 50`. **The scale at which two blobs merge reads their separation off the chart
directly.** A tree of Y-shaped merges going up in scale is the visual form of a clustering hierarchy,
and is what a Hawkes or multifractal cascade is supposed to look like.

### 2.5 The one hard law: nothing is created going coarse

`λ̂` satisfies the heat equation, and so does `λ̂′`. In 1D, the Gaussian is the unique kernel whose
scale-space never creates new zero-crossings as scale increases (Babaud–Witkin–Baudin–Duda, 1986).
`F`'s zero contours **are** the zero-crossings of `λ̂′`'s derivative, so the theorem applies to this
chart exactly:

> **Going up in scale, features may merge and vanish. They may never split, and they may never appear
> out of nothing.**

**Any blob on the offline pane whose bottom edge is closed — a bubble with nothing beneath it — is an
artifact: masking, decimation, edge effect, or a bug.** This is a free correctness check on the render
that requires no null model.

**It does not hold on the online pane.** A one-sided kernel does not satisfy the heat equation. Blobs
appearing from nowhere with scale are legitimate there, so the two panes must not be checked the same way.

### 2.6 Tilt — onset/decay asymmetry

For a symmetric feature the negative column is vertical. For an asymmetric one the centre of the column
drifts, with scale, toward the heavy side, because a wider kernel is pulled by mass further out.
Measured on a sharp onset with a 30 s exponential tail:

| `s` | 2 | 5 | 10 | 20 | 40 |
|---|---|---|---|---|---|
| location of most-negative cell | +1.5 | +4.0 | +7.0 | +12.5 | +19.0 |

**A column leaning to the right as it rises = sharp onset, slow decay.** Leaning left = slow build,
abrupt stop. The lean rate is roughly `0.5·s` per scale for a strongly one-sided feature.

This is a real microstructure quantity and, as far as I can tell, it is the most under-used piece of
information on the chart. Onset-decay asymmetry is what separates an information event from a
liquidity air-pocket, and the field encodes it as a visible tilt.

### 2.7 Horizontal banding — a characteristic timescale

A row of the heatmap that looks different from the rows above and below it, *across the whole session*,
is a preferred timescale in the process. This is the thing the build brief predicted near v3's Allan
knees (128 s regular hours, 16 s premarket, from the committed Allan-factor curve — the measurement of
how clustered arrivals are as a function of counting-window width).

**The converse is the more important read.** If the field's texture is statistically the same at every
height — same blob sizes relative to `s`, same depth distribution, no preferred row — **the process is
scale-free and there is no burst duration to find.** That is the standing negative finding of this
programme, and it is readable by eye off a single panel. If you cannot pick a special row, the answer to
"how long is a burst" is "the question is malformed."

### 2.8 Coarse-scale structure — that is the intraday shape, not signal

At `s` approaching a sizeable fraction of the session, the only thing with curvature is the session
envelope itself. A U-shaped intraday volume profile is convex through midday and concave at the ends,
so the top of the panel should read **positive across the middle of the session and negative near the
open and the close**, on every event, always. That band is the seasonality given a coordinate rather
than subtracted. It is not evidence of anything, and a threshold that fires there is firing on the clock.

### 2.9 The `s_min` line is a redundant plot of the rate

`log s_min(t) = log 2.26 − log λ̂(t)`. **The boundary line is the negated log intensity.** It carries no
information that pane 1 and pane 4 do not already carry; it is the same curve upside down.

That matters for the mark, not the picture — see §4.

---

## 3. What the field structurally cannot show

Worth stating plainly, because several of these look like they should be visible and are not.

1. **Activity level.** Property 4: invariant to `λ → cλ`. A sustained high-rate plateau has zero
   curvature and reads `F ≈ 0` — identical to dead tape. **The field cannot distinguish busy from quiet.**
   If the tradeable object is "elevated activity," this instrument does not measure it.
2. **Trends.** §2.3: any monotone move in log-rate reads positive. The field marks the *top* of a rate
   excursion, never its rise.
3. **Clumping at constant mean rate.** The rate channel sees only `λ̂`. Two tapes with identical
   `λ̂(t)` — one Poisson, one violently clustered inside — give **identical fields**. That separation
   lives in the interval channel, which is a different statistic:
   `F_interval = Cov_w(z², log₁₀ Δt)` — the kernel-weighted covariance between squared distance from
   centre and log interval. Negative there means intervals shorten toward the middle. It is a genuinely
   independent channel and the panels do not show it.
4. **Anything below `s_min`.** Correctly masked.

---

## 4. The noise ruler — what a meaningless blob looks like

This is the part that decides whether any of the structure is worth reading, and it is derivable.

**Sampling error.** For a homogeneous Poisson process the delta method gives
`Var(F) ≈ 0.75/n_eff`, i.e. **`sd(F) ≈ 0.87/√n_eff`**. Monte Carlo (20,000 draws per row):

| `n_eff` | 4 | **8** | 12 | 20 | 32 | 64 | 128 |
|---|---|---|---|---|---|---|---|
| sd(F) | 0.94 | **0.38** | 0.28 | 0.21 | 0.16 | 0.11 | 0.078 |
| `0.87/√n_eff` | 0.44 | 0.31 | 0.25 | 0.19 | 0.15 | 0.11 | 0.077 |
| `P(F < 0)` | 0.47 | **0.48** | 0.49 | 0.49 | 0.49 | 0.49 | 0.50 |
| skew | 5.3 | 1.6 | 1.1 | 0.7 | 0.5 | 0.3 | 0.3 |

The asymptotic formula is optimistic below `n_eff ≈ 12`; the true `sd` at the floor is **0.38**.

**Set that against the signal.** The deepest a perfectly matched bump ever reads is −0.5 at `s = σ`.
**At `n_eff = 8` the noise standard deviation is 0.38 and the entire available signal is 0.5.** A
well-matched, real burst clears one standard error and change. **`n_eff ≥ 8` is a floor for the estimate
existing, not for it being readable.** For a matched burst to clear 2 sd you need `n_eff ≳ 12`; for 3 sd,
`n_eff ≳ 27`. `read_factor = 2.0` gives `n_eff = 16`, `3.0` gives 24. **That, and not the sign
convention, is the argument for reading above the boundary.**

**Correlation structure — what a noise blob looks like.** Measured on Poisson tape:

| lag in `t` (units of `s`) | 0.25 | 0.5 | 1.0 | 1.5 | 2.0 | 3.0 |
|---|---|---|---|---|---|---|
| correlation | 0.93 | 0.72 | 0.08 | **−0.48** | **−0.62** | −0.16 |

| `Δ ln s` | 0.22 | 0.47 | 0.69 | 0.92 | 1.16 | 1.39 |
|---|---|---|---|---|---|---|
| correlation | 0.94 | 0.77 | 0.59 | 0.41 | 0.26 | 0.18 |

**Read the negative numbers in the first table.** Noise in this field is not speckle. **A noise blob is a
negative core about `2s` wide with positive lobes at `±2s`, about 1.5 octaves tall.** That is the same
shape as a real burst with its shoulders (§2.1). **The pattern is not the evidence.** What separates
signal from noise is only:

- **vertical persistence** beyond ~1.5 octaves of `ln s`, and
- **depth** beyond about `2 × 0.87/√n_eff` at the scale where it is read.

A red core with blue shoulders spanning one octave is what a null tape produces all day.

**Multiple comparisons.** Independent cells number roughly `T/(2s)` per row times `~ln(s_max/s_min)/1.2`
rows. For a session and a scale ladder this is tens of thousands. The max of the null field over the grid
runs near `sd × √(2 ln N) ≈ 4–4.5 sd`. **A per-cell threshold is not a chart-level threshold**, which is
the Dümbgen–Spokoiny per-scale penalty argument (an additive per-scale correction that makes statistics
at different bandwidths comparable under one global critical value) arriving from the noise side.

---

## 5. Three consequences for the burst mark as currently built

These follow from the above and are, I think, the load-bearing part of this document.

### 5.1 The sign test has no discriminating power, and the reason is structural

Under the null, `P(F < 0) ≈ 0.48` — a coin flip by construction, since `F` is a centred statistic.
Under *structure*, it goes the other way and hard. On a synthetic session with two bumps on a
background, the **print-weighted** fraction of cells with `F < 0` was 0.94 at `s = 2 s`, 0.86 at 40 s,
0.61 at 300 s.

The mechanism is exact. `F·λ̂ = s²λ̂″`, and `∫λ̂″ dt = 0`, so **the trade-weighted mean of the field is
exactly zero at every scale** (verified to 1e-5). But `F` is bounded below at −1 and unbounded above, so
the zero is reached by *many* prints sitting in shallow negative and *few* sitting in deep positive.
And that is not an accident: prints are concentrated near local maxima of intensity, which is exactly
where the curvature is negative.

> **"`F < 0` at this print" is close to "this print is near a local maximum of the trade rate," and most
> prints are.** A sign test cannot help but fire most of the time. This is the same degeneracy the arc
> already hit once, but it is not caused by the Poisson reference — it is caused by the asymmetric range
> of the statistic, and swapping the reference will not fix it. **A magnitude threshold is required, and
> it has to be asymmetric between the two signs.**

The trade-weighted zero-sum is also a free correctness check on any rendered field: **sum `F` over the
prints at any fixed scale and it must come out at zero.** If it does not, the masking is asymmetric or
the estimator is wrong.

### 5.2 Burst *count* is proportional to print count even if the field is pure noise

The read path is `s = read_factor · s_min(t) = read_factor · 2.26/λ̂(t)`. The number of *independent*
reads along that path over a session is `≈ T/s_min ∝ λ̂·T` — **the print count.**

**So a regression of burst count on print count has a slope of 1 built into the geometry, on noise.**
The Arm A failure shape (burst count correlating 0.96 with print count) would reproduce here on a
random tape, and would not mean the same thing.

**The print-count regression is still the right first test, but the dependent variable has to change.**
Use **shaded fraction of admissible session time**, which is scale-invariant and has a derivable null
of ≈0.48, or **burst count per `s_min` of session**. Regressing raw count would produce a confirmed
failure that is an artifact of the read path.

### 5.3 The read path is a diagonal cut, and it has no fixed timescale

Reading at `s ∝ 1/λ̂(t)` means the field is sampled along a curve that is itself the (negated, scaled)
log rate. Two things follow:

- **A diagonal cut through a trumpet crosses its walls at different places than a horizontal cut**, so
  the on-duration of a mark is a mixture of the feature's geometry and the boundary's motion. The
  confound flagged in §0(b) of the panels work order, stated as geometry.
- **The mark holds `n_eff` fixed at 8, never the duration.** On fast tape it asks a question about
  8 prints spanning milliseconds; on slow tape, 8 prints spanning minutes. **Two marks in the same
  session are answers to two different questions**, and no duration derived from them is comparable
  across events or across time within an event.

Neither is fatal, but **any horizontal cut — a fixed `s` in seconds — is a cleaner object than the
boundary-following cut**, and both should be on the chart. A fixed-`s` row asks one question everywhere.

---

## 6. The checks this makes available with no data run

In rough order of cost:

1. **Zero-sum.** Trade-weighted mean of `F` at each scale must be 0. Correctness check on the estimator
   and the mask. Minutes.
2. **No blob has a closed bottom** on the offline pane. Violations are render or masking defects, not
   findings. Visual, free. Does not apply to the online pane.
3. **The noise ruler on the existing panels.** Overlay `±2 × 0.87/√n_eff(t,s)` as a contour. Everything
   inside it is indistinguishable from a null tape. My expectation is that this removes most of what is
   currently visible at and near the boundary, and that what survives sits at coarse scales.
4. **Is there a special row?** If the texture is scale-invariant top to bottom, the burst-duration
   question is malformed and no amount of estimator work fixes it.
5. **Change the dependent variable in the print-count regression** before running it (§5.2).
6. **Raise the read factor to 2–3 on the grounds of §4**, not on the boundary-coupling grounds — the
   noise argument is the stronger one and it gives a number.

---

## 7. What I would not claim from any of this

- **None of it is evidence that your tape has bursts.** These are properties of the estimator. They tell
  you what a picture *would* mean; they do not tell you what your picture *does* mean.
- **The duration readout in §2.1 assumes a Gaussian-shaped rate bump.** Real excursions are not Gaussian,
  and for a sharply asymmetric one the `−0.5` crossing and the column centre disagree (§2.6). The readout
  degrades gracefully but it is not exact off the model.
- **§5.1 does not say the field is broken.** It says the *sign* of the field is a poor detector. The
  field itself carries the duration, the location, the asymmetry, and the merge structure, none of which
  a boolean uses.
- **Nothing here reopens the tradeability question.** A legible field and a profitable one are different
  claims.
