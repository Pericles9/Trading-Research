# Does the scale field detect anything real on this tape?

**Date:** 2026-09-08 · **Type:** diagnostic read. Records no decision, applies no gate, produces no digest.
**Brief:** goals-and-tests, 2026-09-07. **Cohort:** the ten committed panel events
(`results/scale_field/artifacts/event_panels_cohort.csv`), plus a 60-event print-count-stratified
draw for Gate D.
**Code:** `research/scale_field/instrument_gates.py`, `gateA_resolve.py`, `satisfiability.py`,
`excess_variance.py`, `surrogate_control.py`, `gateD_cohort.py`, `gate_charts.py`.
**Artifacts:** `results/scale_field/artifacts/instrument_gates/`. **Charts:**
`results/scale_field/charts/instrument_gates/`.

---

## 0. Gate 0 — the log base. Natural log. Every threshold in the brief stands unchanged.

`scale_field.py` computes **`∂ ln λ̂ / ∂ ln s`**. Settled two ways, neither of them a docstring:

- **From the code path.** `field()` forms `lr = ln(c0/dt)` and `dlr = sg²·c2/c0 = s²λ̂″/λ̂`, which is
  the natural-log derivative. `field_exact()` forms `E_w[z²] − 1`, the same object.
- **Numerically, by the check that settles it with no ambiguity.** Every print at the same instant,
  evaluated at that instant: **F = −1.000000** at s = 0.1, 1.0 and 10.0 s, under **both** kernels
  (`gate0_log_base.json`). The log₁₀ form would have read −0.4343.

**Threshold multiplier = 1.0.** Nothing below is rescaled.

---

## 1. The answer to §1, in five sentences

**The field is not noise. Its current read is.**

At every scale from 0.25 s to 2048 s the field carries **2.3–3.0× more standard deviation than the
estimator's own sampling error** — split-half reliability confirms it independently at **r = 0.90–0.99
with no null model and no threshold anywhere in the test** — and below ~30 s that excess is **not**
reproducible by an inhomogeneous Poisson surrogate carrying the same rate path, so the instrument is
responding to something on the tape. But at `read_factor = 1.0`, the primary read the committed panels
render, **only 1.5–3.8% of marked time survives a per-cell `F < −2·sd(n_eff)` test** (median 2.1%), and
that is not a tuning problem: at the read scale `n_eff = 8` exactly, where `2·sd = 0.785` against a
statistic **bounded below at −1**, the detection requirement (`σ < 0.523·s_min`) and the
duration-readout requirement (`σ ≥ s_min`) are **arithmetically incompatible — the satisfiable band at
`read_factor = 1` is empty**, opening only at 2 (0.32 decades), 3 (0.59) and 4 (0.77). Gate D closes
the same gap from the other side on 60 events spanning 197× in print count: with the magnitude
threshold applied at `read_factor = 4` the survivor fraction is **flat against print count
(r = −0.016, r² = 0.000)**, while at `read_factor = 1` it rises **19×** and the sign-only shaded
fraction tracks print count at every read factor (r = 0.54–0.75).

So of the brief's three options this is **(iii): the field detects structure beyond noise, but only
above `read_factor ≈ 2` — cleanly at 4 — and the current read scale is the defect rather than the
field**, with the qualification that even at 4 a median of only 22% of marked time survives, because
the sign-thresholded boolean was a poor detector by construction and `burst_on`'s own docstring
already said so.

> **One input to this brief does not exist.** §0 directs "read `claude/scale_field_reading_grammar.md`
> first" and says most of the brief's numbers are derived and numerically checked there. There is no
> `claude/` directory in this checkout and no file of that name anywhere in the repo or in git history.
> Every derivation the brief attributes to it has therefore been re-derived here from
> `scale_field.py` and re-checked numerically — the `sd(F)` table, the `n_eff` coefficients, the
> `−s²/(σ²+s²)` depth law, the `P(F < 0) ≈ 0.48` null, the −1 bound. **All of them reproduce**
> (Gate C's table matches to ≤ 0.013 absolute), so nothing is lost, but the brief's claim that they
> are checked *there* could not be verified.

---

## 2. Gate outcomes

| gate | quantity | pre-registered threshold | observed | verdict |
|---|---|---|---|---|
| **0** | F in the delta limit | −1.000 (nat) / −0.434 (log₁₀) | **−1.000000**, both kernels, 3 scales | **natural log** |
| **A1** | λ̂-weighted zero-sum, exact estimator | 0 to 1e-5 relative | **−6.6e-19 … +3.5e-18** at s = 0.5, 2, 8 | **pass** |
| **A1** | same, pyramid path, all masks off | — | **≤ 1.8e-3** at every probe scale | pass (binning) |
| **A1** | same, as rendered (n_eff + edge mask) | — | −4.6e-2 (s=0.25) → −9.3e-4 (s=1024) | **attributed, not a defect** |
| **A2** | closed-bottom blobs, centred pane | none | 2.5–5.5% by count, **0.19–0.69% by area** | **render-path artefact** |
| **A2** | same, exact estimator, 8/16/32/64 rungs per octave | none | **0, 1, 1, 0** blobs; ≤ 0.011% by area | pass |
| **A3** | `burst_on()` fires where F < 0 | True on negative | **True/False on `[[−0.7, …], [+0.4, …]]`**; 48 committed assertions pass | **pass** |
| **B1** | share of marked time surviving `F < −2·sd`, `rf = 1` | most marks fail (pre-registered) | **median 2.1%**, range 1.5–3.8% | **pre-registered expectation confirmed** |
| **B2** | same, `rf` = 2 / 3 / 4 | — | **13.9% / 19.3% / 21.8%** median | rises, then plateaus |
| **B2** | survival vs absolute scale | whatever survives sits coarse | **6.4% at 0.25 s → 31% at 2048 s** | **confirmed** |
| **B** | survivors as a share of *defined* time ÷ Poisson null rate | — | **111× (rf1), 20× / 14× / 12×** | above null everywhere |
| **B** | detection and duration-readout simultaneously satisfiable? | — | **band empty at rf 1**; 0.32 / 0.59 / 0.77 decades at rf 2/3/4 | **not at the primary read** |
| **C** | sd(F) vs the brief's table | 0.94 / 0.38 / 0.28 / 0.21 / 0.16 / 0.11 / 0.078 | **0.931 / 0.393 / 0.287 / 0.208 / 0.160 / 0.110 / 0.077** | **table reproduced** |
| **C** | P(F < −2·sd) at n_eff = 8 | measure it | **6e-5** — 380× thinner than normal theory (0.0228) | **measured** |
| **C** | P(F < 0) under the null | ≈ 0.48 | **0.4805** at n_eff = 8 | confirmed |
| **D** | survivor fraction on log print count, `rf = 4`, RTH, **n = 60** | no material dependence | **r = −0.016, r² = 0.000**, 0.1009 → 0.0999 over 197× | **pass** |
| **D** | same at `rf = 1` | " | r = 0.734, r² = 0.539, 19× rise | **fails at the primary read** |
| **D** | sign-only shaded fraction, any `rf` | " | r = 0.54 – 0.75, r² = 0.29 – 0.56 | **fails** |
| **D** | geometric control: log raw count on log prints | slope ≈ 1 is arithmetic | **r = 0.971 / 0.982 / 0.991** | Arm A's r = 0.96 reproduced, means nothing |
| **E** | split-half reliability vs scale, 8 events × 3 draws | none | **0.898 – 0.993**, min 0.865 anywhere | **never collapses** |
| **E** | thinning invariance `λ → cλ` (verified first) | bias ≈ 0 | **+0.0015** at 50%, **+0.0016** at 25% | **verified** |
| **F** | preferred scale row at v3's Allan knees (128 s RTH, 16 s premarket) | a change of character near them | **none: width/s flat at ~1.85 from 8 s to 512 s** | **no special row** |

---

## 3. Gate A — the zero-sum, decomposed rather than declared

The brief sets a 1e-5 relative tolerance and says a failure voids everything downstream. It does not
fail, but getting there required two corrections **to my own first pass**, both stated here rather
than quietly applied.

**The weight.** The identity is `∫ F(t,s)·λ̂_s(t) dt = s²∫λ̂_s″ dt = 0`, where `λ̂_s` is the intensity
**smoothed at that same scale s**. My first pass weighted by the k = 20 kNN rate that sets `s_min` — a
different estimator of a different quantity — and produced residuals of 0.24–0.74. Weighting an
identity by the wrong λ does not test the identity. The field's own `lograte` output is `λ̂_s` and is
what the resolved run uses.

**The literal form in the brief is not the form that can meet the tolerance.** `Σᵢ F(tᵢ)` over prints
is a Monte-Carlo estimate of the same integral and carries sampling error ≈ sd/√n, which at n = 10⁵ is
~1e-3 — it can never reach 1e-5 for any correct estimator. The exact identity is the λ̂-weighted time
integral, and that is the one held to the tolerance. Both are reported.

Decomposition on `JFIN_2020-06-15_60.44` (`gateA_resolve.json`), λ̂ₛ-weighted, per probe scale:

| variant | s = 0.25 | 1 | 4 | 16 | 64 | 256 | 1024 |
|---|---|---|---|---|---|---|---|
| exact pairwise, whole real line | — | −6.6e-19 … +3.5e-18 across s = 0.5, 2, 8 | | | | | |
| pyramid, **no masks at all** | +5.4e-4 | −9.7e-4 | −1.0e-3 | −1.1e-3 | −1.3e-3 | −1.6e-3 | −1.8e-3 |
| pyramid, edge mask only | — | — | — | — | — | — | — |
| **as rendered** (n_eff ≥ 8 + edge) | −4.6e-2 | −2.2e-2 | −7.6e-3 | −2.5e-3 | −1.3e-3 | −8.7e-4 | −9.3e-4 |

**The residual is the n_eff mask, and its sign is predictable.** The mask removes cells where λ̂ is
low; those are the gaps, and F is *positive* in gaps. Removing positive cells leaves a negative mean.
At s = 0.25 s only 3.7% of cells on a uniform grid survive the mask, and their λ̂-weighted mean F is
−0.046 rather than 0.

**The control that settles it.** An inhomogeneous Poisson surrogate with the same duration and the
same rate path — **no burst structure whatever** — run through the identical pyramid, ladder, edge mask
and n_eff mask, gives −1.9e-2 at s = 0.25 falling to −9.1e-4 at 1024 s: the same profile, the same
sign, the same order of magnitude. The residual is a property of the mask geometry, not of the tape
and not of the estimator.

**Closed-bottom blobs.** 2.5–5.5% by count on the rendered panels, but **0.19–0.69% by area**, and they
do **not** concentrate at the three cost-group seams (s = 2 and s = 64 carry 1.1% of them). They sit at
the fine end of the ladder, 0.27–1.7 s, which is where the pyramid's own documented error is largest
(its docstring measures `dlograte` error at up to 0.49 of the field's sd in the first octave) and where
the n_eff mask leaves only 4–20% of cells defined. Run on the **exact pairwise estimator** with a
uniform grid at 8, 16, 32 and 64 rungs per octave, the counts are **0, 1, 1, 0** out of 42–43 blobs,
≤ 0.011% by area. Babaud's theorem is a statement about the continuum; the continuum estimator obeys
it, and the render path departs from it by under 0.7% of negative area. **This does not touch the
marking**, which reads the raw sign at `s*(t)` and never the blob topology.

**Sign.** `burst_on()` returns True on negative F, asserted directly on a two-cell fixture rather than
through a tape, and the 48 committed assertions in `test_scale_field.py`, `test_onesided.py` and
`test_event_panels.py` pass unchanged.

One thing my own first sign fixture found, recorded because it is the brief's subject rather than a
bug: a bump of σ = 4 s at 220 prints/s puts `s_min` at 10.3 ms, so a `2·s_min` read lands two decades
below the feature, where the analytic depth `−s²/(σ²+s²)` is −0.00003 and the sign is a coin flip
(measured share negative: 0.500). Read at scales comparable to the feature the sign is unambiguous:

| s | s/σ | median F in bump | median F outside | analytic depth (no background) | share F < 0 in bump |
|---|---|---|---|---|---|
| 0.25 | 0.06 | −0.002 | +0.009 | −0.004 | **0.500** |
| 1.0 | 0.25 | −0.039 | +0.001 | −0.059 | 1.000 |
| 4.0 | 1.00 | −0.385 | +0.001 | −0.500 | 1.000 |
| 16.0 | 4.00 | −0.651 | +0.007 | −0.941 | 1.000 |

The measured depths sit above the analytic ones because the bump rides a 20/s background, which the
analytic form ignores — the gap is dilution, and it makes every detection threshold below **harder**,
not easier.

---

## 4. Gate C — the noise ruler, measured

400,000 Monte Carlo draws per rung, both kernels, `F = E_w[z²] − 1` evaluated exactly with no tape
simulated (the statistic is scale-free in units of s, so one (λ, s) pair per `n_eff` is the whole
story). The brief's pre-registered table is reproduced:

| n_eff | 4 | 8 | 12 | 20 | 32 | 64 | 128 |
|---|---|---|---|---|---|---|---|
| **brief** | 0.94 | 0.38 | 0.28 | 0.21 | 0.16 | 0.11 | 0.078 |
| **measured** | 0.931 | 0.393 | 0.287 | 0.208 | 0.160 | 0.110 | 0.077 |
| skew | 4.99 | 2.01 | 1.19 | 0.71 | 0.52 | 0.35 | 0.24 |
| P(F < 0) | 0.471 | **0.481** | 0.486 | 0.488 | 0.491 | 0.494 | 0.495 |
| **P(F < −2·sd)** | **0** | **6e-5** | 1.1e-3 | 3.5e-3 | 6.7e-3 | 1.0e-2 | 1.4e-2 |

Worst absolute deviation 0.013 at n_eff = 8 (3.3% relative); the asymptotic `0.87/√n_eff` is optimistic
below n_eff ≈ 12 exactly as the brief says, and is within 1% above 32.

**Two facts here carry the whole read.**

1. **The measured false-alarm rate is nothing like normal theory.** At n_eff = 8 it is 6e-5 against the
   Gaussian 0.0228 — **380× thinner** — and it never reaches the Gaussian rate at any n_eff on the
   grid, topping out at 0.018 at n_eff = 512. A normal-theory threshold would have been badly wrong in
   the conservative direction.
2. **Below n_eff = 6.31 a 2-sd negative detection is impossible for any feature whatsoever**, because
   `2·sd` exceeds 1 and F ≥ −1 always. At n_eff = 4, zero of 400,000 draws cleared it. The field's own
   mask floor is n_eff ≥ 8, so **the primary read sits 1.27× above the line where detection becomes
   arithmetically impossible.**

Chart: `gateC_noise_ruler.html`, `gateC_null_rate.html`.

---

## 5. Gate B — what survives

**B1, per-cell survival of the currently-marked time**, threshold read per cell at that cell's own
`n_eff = 2√π·s*(t)·λ̂(t)` (never a global constant), debounce and `burst_on` unchanged, both kernels,
all four read factors reported because reporting only the one that passes is the failure this lineage
is trying to stop repeating:

| read_factor | n_eff at read | 2·sd | **centred, median survival of marked time** | range | one-sided |
|---|---|---|---|---|---|
| **1.0** | 8 | **0.785** | **2.1%** | 1.5 – 3.8% | 2.2% |
| 2.0 | 16 | 0.476 | 13.9% | 10.4 – 23.7% | 6.2% |
| 3.0 | 24 | 0.376 | 19.3% | 15.7 – 28.2% | 10.4% |
| 4.0 | 32 | 0.319 | 21.8% | 17.3 – 30.4% | 13.9% |

The sign condition itself marks **a median 32.8% of admissible session time** (range 24.2–40.1%) —
*below* the null's own P(F < 0) = 0.48, which is itself worth noting: the debounced sign mark fires
less often than a coin would.

Per segment (never pooled — v3's 0.903 decades, failure row 5), at `rf = 1`, centred: regular hours
2.5–6.8%, premarket 0.1–9.3%, post-close **0.0–1.1%**. Post-close shading is essentially all noise at
the primary read on every event in the cohort.

**Against the null rather than against zero.** Survivors as a share of *defined* time, versus the
measured Poisson false-alarm rate at the same n_eff:

| rf | null rate | median observed | × null |
|---|---|---|---|
| 1.0 | 0.00006 | 0.0072 | **111×** |
| 2.0 | 0.00236 | 0.0467 | 19.8× |
| 3.0 | 0.00483 | 0.0700 | 14.5× |
| 4.0 | 0.00666 | 0.0830 | 12.5× |

So the survivors are far above chance at every read factor. The small survival *share* is not the field
failing to find anything; it is the sign condition marking three times as much tape as the magnitude
condition can support.

**B2, against absolute scale** (centred, whole pane, median of ten events). What survives sits coarse,
as pre-registered:

| s (s) | 0.25 | 1 | 4 | 16 | 64 | 256 | 1024 | 2048 |
|---|---|---|---|---|---|---|---|---|
| survive share | 0.064 | 0.105 | 0.155 | 0.199 | 0.212 | 0.241 | 0.278 | 0.310 |
| null rate | 0.0025 | 0.0089 | 0.0147 | 0.0184 | 0.0184 | 0.0184 | 0.0184 | 0.0184 |
| × null | 26 | 12 | 11 | 11 | 11 | 13 | 15 | 17 |

Chart: `gateB_survival_vs_read_factor_{centred,onesided}.html`, `gateB_survival_vs_scale.html`.

### 5.1 Detection versus measurement — the gap, closed with a number

The brief asks this be verified rather than assumed. Both requirements are derived against `s_min`,
which makes the answer scale-free — it holds at every rate on every event and needs no tape:

- **Detection.** Depth at the centre of a Gaussian bump of width σ read at scale s is exactly
  `−s²/(σ²+s²)`. A 2-sd detection needs `s²/(σ²+s²) > 2·sd`, i.e. **`σ < s·√(1/(2·sd) − 1)`**, and is
  available at all only while `2·sd < 1`.
- **Duration readout.** The depth curve is flat in σ once s ≫ σ, so a width can only be read from
  scales down to σ itself — and `s ≥ s_min` is a data limit, so **`σ ≥ s_min`**.

Since `s* = read_factor · s_min` exactly, both conditions reduce to a band in `σ/s_min`:

| read_factor | 2·sd | σ_max / s_min (detection) | σ_min / s_min (readout) | **band** |
|---|---|---|---|---|
| **1** | 0.785 | **0.523** | 1.000 | **EMPTY** |
| 2 | 0.476 | 2.100 | 1.000 | 0.322 decades |
| 3 | 0.376 | 3.868 | 1.000 | 0.588 decades |
| 4 | 0.319 | 5.845 | 1.000 | 0.767 decades |

**At the primary read the two requirements are contradictory.** Anything deep enough to detect is too
narrow to have been resolved, and anything wide enough to measure is too shallow to clear the
threshold. This is the detection-versus-measurement gap the resolution-floor finding left open in
words, and background dilution makes it **worse** than the table shows.

The empirical signature agrees. Across surviving runs at `rf = 1`, depth and width are **uncorrelated**
(r = −0.14 … +0.05 on all ten events), and surviving runs are **narrower than the read scale that drew
them** (median width / s\* = 0.23–0.71). At `rf = 2` and 4 the depth–width correlation turns clearly
negative (−0.26 … −0.49): deeper marks are narrower, which is the noise signature, not a feature
signature. *(Caveat on my own construction: the debounce enforces a 1×s\* minimum on the sign mark, but
the magnitude threshold then cuts runs into shorter pieces, so sub-s\* surviving widths are partly an
artefact of applying the cut after the debounce.)*

---

## 6. Gate D — independence from print count

**Cohort, and why it is not the panel ten.** The brief says ten events is too few and to say so rather
than report an r² on ten. It is worse than too few: the panel cohort is a joint [p70, p80] filter on
**both** print count and momentum, so its print count spans 66,451–123,044 — a range of **1.85×**.
Adding events inside that band adds n and adds no leverage on the only axis being regressed. Gate D
therefore runs on a **print-count-stratified draw**, six per decile of the readable D1 pool, same
committed procedure otherwise (readability = `clean_window AND trades_ingested`, stable mergesort on
the 3-part key before a seed-42 draw, ≥ 5,000 prints so a tape exists at all):

**n = 60 events, print count 5,107 → 1,006,799 — 197×, 2.29 decades, 5.28 natural-log units.** Powered
against the brief's floor of 40. Momentum is not held fixed (that would re-narrow the pool) and is
carried per event; the draw spans `momentum_pct` 30.2–273.8.

### 6.1 The geometric control fires, and it means nothing

Regressing **log raw burst count** on log print count — the uncorrected form that killed Arm A:

| read_factor | 1 | 2 | 4 |
|---|---|---|---|
| slope | 0.726 | 0.785 | 0.854 |
| **r** | **0.971** | **0.982** | **0.991** |
| r² | 0.943 | 0.964 | 0.983 |

**Arm A died at r = 0.96. This is r = 0.97–0.99, and it is arithmetic.** The read path is
`s = read_factor·2.26/λ̂(t)`, so the independent reads along it number ≈ `T/s_min ∝ λ̂·T`, which *is* the
print count. Running this regression and reporting it as a finding would have produced a confirmed
failure that says nothing about the detector. The brief was right to forbid it, and the control
confirms the mechanism is present exactly as described.

### 6.2 The corrected dependent variable

Shaded fraction of **admissible** session time, and the same with the Gate B magnitude threshold
applied. Fitted values at the ends of the print-count range make "material" concrete:

| segment | rf | dependent variable | slope | r | r² | fit @ 5.1k | fit @ 1.0M | change |
|---|---|---|---|---|---|---|---|---|
| all | 1 | shaded fraction (sign only) | +0.0277 | 0.621 | 0.386 | 0.256 | 0.402 | 1.57× |
| all | 1 | **survivor fraction (2·sd)** | +0.0027 | **0.642** | 0.412 | 0.0029 | 0.0172 | 6.0× |
| all | 2 | shaded fraction (sign only) | +0.0193 | 0.541 | 0.292 | 0.287 | 0.389 | 1.36× |
| all | 2 | **survivor fraction (2·sd)** | −0.0031 | **−0.345** | 0.119 | 0.060 | 0.043 | 0.73× |
| all | 3 | **survivor fraction (2·sd)** | −0.0057 | −0.437 | 0.191 | 0.089 | 0.060 | 0.67× |
| all | 4 | shaded fraction (sign only) | +0.0285 | 0.745 | 0.556 | 0.337 | 0.488 | 1.45× |
| all | 4 | **survivor fraction (2·sd)** | −0.0026 | **−0.220** | 0.048 | 0.095 | 0.081 | 0.85× |
| **rth** | **4** | **survivor fraction (2·sd)** | **−0.0002** | **−0.016** | **0.000** | **0.1009** | **0.0999** | **0.99×** |

**The pass condition is met, and the magnitude threshold is what meets it.** The brief's condition is
that the shaded fraction show no material dependence *once the magnitude threshold from Gate B is
applied*. With it applied at `read_factor = 4`, regular hours: **r = −0.016, r² = 0.000, and the fitted
survivor fraction moves from 0.1009 to 0.0999 across 197× in print count.** Flat. At `rf = 2` and 3 the
dependence is weak and **negative** (r = −0.22 to −0.44) — the wrong sign for the Arm A mechanism,
which produced *more* marks on denser tapes.

**The failures that remain, stated rather than buried.**

- **The sign-only shaded fraction does still track print count** at every read factor: r = 0.54–0.75,
  r² = 0.29–0.56, rising 1.3–1.6× across the range. The sign mark is not print-count-independent. The
  magnitude threshold is doing the work, and this is a fourth piece of evidence that the boolean rather
  than the field is the weak component.
- **At `read_factor = 1` the survivor fraction rises 6× (all) and 19× (RTH)** with print count,
  r² = 0.41–0.54, on a base of 0.3–1.5% of session. That is a material dependence and it fails the
  condition at the primary read. **My reading of the mechanism, offered as a view:** since
  `n_eff = 8` at the read *by construction*, print count cannot be acting through the effective
  sample. What it moves is the **absolute** scale of the read — `s* = s_min ∝ 1/λ` — so a slow tape is
  read at tens of seconds, where §8.1's surrogate says the excess is entirely the rate path, and a fast
  tape is read at sub-second, where the genuine excess lives. If that is right the rf1 dependence is
  the read scale sliding across a band in which the tape's character genuinely changes, not the Arm A
  mechanism. It is not the same defect, but it is not independence either, and I have not measured it
  directly.
- **"Marks per `s_min`" over-corrects.** r = −0.83 to −0.85 at every read factor. That is expected once
  the raw-count exponent is measured at 0.73–0.85 rather than 1.0: dividing a `prints^0.8` count by a
  `prints^1.0` read budget leaves `prints^-0.2`. **The scale-invariant shaded fraction is the right
  DV of the two the brief offered**, and the count correction should not be used.

Charts: `gateD_shaded_vs_prints_rf{1.0,2.0,4.0}.html`.

---

## 7. Gate E — split-half reliability against scale

Each print assigned at random to half A or half B, three draws per event, the field computed
independently on each, correlated at every scale on a **fixed absolute grid** (letting each half pick
its own read scale would compare two different quantities, since each half has lower λ and therefore a
higher `s_min` of its own). Eight events.

**The invariance the test rests on, verified before the test is read.** `F` is invariant to `λ → cλ`,
because a constant inside a log is an additive offset whose scale-derivative is zero. Measured on a
synthetic tape with a deliberate rate excursion: thinning to 50% shifts the mean field by
**+0.0015**, and to 25% by **+0.0016** — no bias. What thinning does change is the noise: correlation
with the full-data field falls to 0.80 at 50% and 0.62 at 25%. Level unchanged, noise up, exactly as
the theory requires.

| s (s) | 0.25 | 0.5 | 1 | 2 | 4 | 8 | 16 | 32 | 64 | 128 | 256 | 512 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **median r(A,B)** | 0.962 | 0.939 | 0.915 | **0.898** | 0.902 | 0.909 | 0.924 | 0.942 | 0.963 | 0.977 | 0.986 | 0.993 |
| min across events | 0.938 | 0.882 | 0.876 | 0.878 | 0.871 | 0.868 | 0.865 | 0.914 | 0.949 | 0.970 | 0.977 | 0.988 |
| Spearman–Brown | 0.981 | 0.968 | 0.956 | 0.946 | 0.949 | 0.953 | 0.961 | 0.970 | 0.981 | 0.988 | 0.993 | 0.996 |
| jointly-defined cells | 4,860 | 6,962 | 8,822 | 10,107 | 11,068 | 11,628 | 11,790 | 11,857 | 11,912 | 11,956 | 11,978 | 11,981 |

**Reliability never collapses.** The minimum is 0.898 at s = 2 s and every event clears 0.865
everywhere. The field is estimating something present in the data at every scale the cohort supports —
this is the same conclusion §8.1 reaches by a completely different route, with no null model, no burst
definition and no threshold anywhere in it.

**Read against the read scale**, which is what the brief asks for: reliability does **not** climb from
low at `1·s_min` to high at `2·` or `3·`. It is already high at the fine end. So the diagnosis is not
"the field is noise at the read scale" — it is that the field is fine and the **boolean** built on top
of it is what fails Gate B. Those are different failures and this read separates them.

**Two caveats, both against the number rather than for it.** First, the fine-scale rows are measured on
a **heavily selected subset**: at s = 0.25 s only 41% of the coarse-end grid is defined in *both*
halves, because each half needs `λ_half ≥ 9/s`, so the correlation there is computed on the densest
stretches of the tape and does not describe the fine band generally. Second, and more important, **a
split-half test cannot separate clustering from the rate path** — both halves inherit the same λ(t),
so a purely inhomogeneous Poisson tape would also show high reliability. Gate E establishes that the
field is reproducible, not what it is reproducing. §8.1's surrogate is the control that addresses that,
and it says: below 30 s, something a rate path does not produce; above 60 s, the rate path.

Chart: `gateE_reliability.html`.

---

## 8. Gate F — is there a special row, and what the variance is made of

**No special row.** Median negative-run width divided by s, centred kernel, median across events:

| s (s) | 0.25 | 1 | 4 | 8 | 16 | 32 | 64 | 128 | 256 | 512 |
|---|---|---|---|---|---|---|---|---|---|---|
| **RTH** width/s | 1.21 | 1.56 | 1.78 | 1.82 | 1.83 | 1.86 | 1.88 | **1.88** | 1.87 | 1.98 |
| **premarket** width/s | 0.95 | 1.51 | 1.69 | 1.60 | **1.79** | 1.85 | 1.79 | 1.85 | 1.84 | 1.89 |
| RTH median depth | −0.79 | −0.49 | −0.33 | −0.27 | −0.24 | −0.20 | −0.20 | −0.19 | −0.20 | −0.23 |
| RTH negative time share | 0.30 | 0.36 | 0.41 | 0.43 | 0.44 | 0.44 | 0.44 | 0.45 | 0.45 | 0.46 |

Width relative to the kernel that drew it is **flat at ≈1.85 from 8 s to 512 s** — which is the
noise-blob value (≈2s) — and shows **no change of character at v3's committed Allan knees**, 128 s
regular hours or 16 s premarket. Depth and negative-time-share are equally flat across both. **The
field's texture is the same at every height**: on this evidence the process is scale-free over the
band the cohort supports, there is no characteristic burst duration in it, and no estimator work on
this channel will produce one. The brief said that if the knees do not show, one of the two
measurements is wrong; the Allan factor and the scale-field texture are measuring different things and
this read does not adjudicate which, but they do not agree.

Charts: `gateF_median_width_over_s.html`, `gateF_depth_median.html`.

### 8.1 The one curve with no threshold in it

Observed sd(F) at each scale row against the **estimator's own sampling-noise sd**, the null evaluated
per cell at that cell's `n_eff` and combined as `√(mean sd²)` — λ varies by a factor of ten inside one
scale row, so a row-median n_eff would understate the floor wherever the tape is thin. Median of ten
events, regular hours, centred:

| s (s) | 0.25 | 1 | 4 | 16 | 64 | 128 | 512 | 2048 |
|---|---|---|---|---|---|---|---|---|
| sd observed | 2.19 | 1.47 | 0.68 | 0.34 | 0.26 | 0.25 | 0.23 | 0.32 |
| sd sampling noise | 0.78 | 0.50 | 0.23 | 0.11 | 0.055 | 0.038 | 0.019 | 0.010 |
| **ratio** | **2.67** | **2.91** | **2.67** | **3.37** | 4.75 | 5.85 | 12.2 | **27.4** |

The observed sd **plateaus at ≈0.24 from 32 s outward while the noise floor keeps falling as
`n_eff^-1/2`**. That plateau is the field's answer to §1: it is variance the estimator does not
produce on its own, at every scale, on every event, in both segments and under both kernels
(one-sided runs 3.0–4.3× fine, 32× at 2048 s).

**What the excess is made of.** An inhomogeneous Poisson surrogate carrying the real tape's rate path
smoothed at 30 s — same diurnal shape, same open, **no clustering at any scale** — run through the
identical pipeline, regular hours:

| s (s) | 0.25 | 1 | 4 | 16 | 32 | 64 | 128 | 512 | 2048 |
|---|---|---|---|---|---|---|---|---|---|
| JFIN real | 2.69 | 2.55 | 2.79 | 2.33 | 2.76 | 13.2 | 6.7 | 14.9 | 43.7 |
| JFIN **surrogate** | **0.92** | **1.01** | **1.02** | **1.21** | 7.04 | 7.89 | 6.5 | 17.2 | 57.6 |
| POLA real | 2.70 | 2.94 | 2.55 | 3.35 | 4.11 | 5.24 | 7.0 | 12.1 | 23.4 |
| POLA **surrogate** | **0.93** | **0.95** | **1.07** | **1.25** | 2.74 | 5.26 | 8.0 | 14.9 | 28.9 |

Two things at once, and they point opposite ways:

- **Below the surrogate bandwidth the surrogate sits at 0.92–1.25 and the real tape does not.** The
  ratio of ratios is 1.9–3.1. There is genuine sub-30-s structure that a smooth rate path does not
  produce. *(This also independently confirms the noise ruler is calibrated on real-geometry data:
  a structureless tape reads 1.0.)*
- **Above ~64 s the two coincide** (real/surrogate 0.76–1.03). **The entire coarse-scale excess — the
  27× at 2048 s — is the rate path.** Nothing above about a minute is evidence of burst structure, and
  it is exactly the coarse end where Gate B's survivors concentrate.

The rate channel cannot separate clumping from a rate excursion at constant mean rate (brief §11), so
this does not establish clumping below 30 s. It does establish that **the coarse survivors are the
diurnal shape**, and that reading them as bursts would be a mistake.

Chart: `excess_variance_{centred,onesided}.html`, `surrogate_control.html`.

---

## 9. The four independent routes, and where they agree

Nothing here rests on one measurement. Four methods with almost nothing in common were run, and they
converge:

| route | what it needs | verdict on the **field** | verdict on the **mark at `rf = 1`** |
|---|---|---|---|
| **Gate B** per-cell magnitude threshold | a null model | survivors 111× the null rate | 2.1% of marked time survives |
| **Gate D** print-count regression, n = 60 | a cohort with leverage | survivor fraction flat at `rf = 4` (r² = 0.000) | r² = 0.54, rises 19× with print count |
| **Gate E** split-half | no null, no threshold, no burst definition | r = 0.90 – 0.99 at every scale | (does not test the boolean) |
| **§8.1** excess variance + surrogate | no threshold; a rate-matched control | 2.3 – 3.0× sampling noise below 30 s | (does not test the boolean) |

**Every route that tests the field says it is estimating something real. Every route that tests the
`read_factor = 1` boolean says that boolean is mostly noise.** That is one finding, not two, and it is
the answer in §1.

**What none of these routes establishes.** The rate channel cannot separate clumping from a smooth
rate excursion at constant mean rate — two tapes with identical `λ̂(t)`, one Poisson and one violently
clustered, give identical fields (brief §11). §8.1's surrogate narrows where the question arises (below
~30 s) but cannot answer it. Nothing here is evidence about clumping, about burst *duration* (Gate F
says there is no characteristic one on this channel), or about tradeability, which D24 and D25 closed
on cost arithmetic.

---

## 10. What I would do next — offered as a view, and labelled as one

1. **Move the read to `read_factor` 4 and re-render the panels, or stop calling the shading a burst
   mark.** Three independent things point at the same number. The satisfiability table is arithmetic,
   not an empirical finding that might come out differently on more events: at `rf = 1` there is no
   feature width that is simultaneously detectable and measurable, and the band only reaches 0.77
   decades at 4. Gate B's survival plateaus at 3–4. Gate D's print-count dependence vanishes at 4
   (r² = 0.000) and is still material at 1 and weakly negative at 2–3. Meanwhile the panels currently
   in `results/scale_field/charts/event_panels/` shade a median 33% of the session, of which ~2% is
   separable from sampling noise. The cost of moving is one octave of resolution and it is the cheapest
   thing on this list.

2. **Drop the sign condition for a magnitude condition, and accept that it fires rarely.**
   `burst_on`'s docstring already predicted both halves of what Gate B measured. A boolean that marks
   33% of the tape and is 98% noise is worse than one that marks 0.7% and is 111× the null rate.

3. **Do not read anything above ~60 s on this channel as burst structure.** The surrogate control says
   the coarse excess is the rate path, and Gate B says the coarse end is where the survivors are. Those
   two facts together mean the most "significant" part of the current field is the diurnal shape.

4. **Injection–recovery is now worth building, and it should be aimed at 1–30 s.** The brief rules it
   out of this scope and rightly. But Gates B and E have said the instrument is worth characterising,
   §8.1 has localised the only band where the excess is not explained by a rate path, and the
   satisfiability table gives a pre-registered prediction for what the recovery surface must look like
   — recovery should collapse for `σ > s*·√(1/(2·sd) − 1)`. That is a falsifiable prediction of a
   detection limit, not a fishing expedition, which is a better place to start an expensive build than
   the one this line has started from before.

5. **Gate F's disagreement with the Allan knees deserves its own hour.** Width/s is flat to three
   significant figures across 128 s and 16 s. Either the knee is not a feature of the arrival process
   at the scales the field reads, or one of the two measurements is wrong. It is cheap to check and it
   is currently an unreconciled contradiction between two committed results.

---

## 11. Reproduction

```
GATE_CACHE=<scratch>  .venv/Scripts/python.exe research/scale_field/instrument_gates.py --gate 0
                      .venv/Scripts/python.exe research/scale_field/instrument_gates.py --gate C --n-draw 400000
                      .venv/Scripts/python.exe research/scale_field/instrument_gates.py --gate A
                      .venv/Scripts/python.exe research/scale_field/instrument_gates.py --gate B
                      .venv/Scripts/python.exe research/scale_field/instrument_gates.py --gate E --n-events 8 --draws 3
                      .venv/Scripts/python.exe research/scale_field/instrument_gates.py --gate F
                      .venv/Scripts/python.exe research/scale_field/gateD_cohort.py
                      .venv/Scripts/python.exe research/scale_field/instrument_gates.py --gate D --n-events 60 \
                          --events-file results/scale_field/artifacts/instrument_gates/gateD_cohort.csv
                      .venv/Scripts/python.exe research/scale_field/gateA_resolve.py JFIN_2020-06-15_60.44
                      .venv/Scripts/python.exe research/scale_field/satisfiability.py
                      .venv/Scripts/python.exe research/scale_field/excess_variance.py
                      .venv/Scripts/python.exe research/scale_field/surrogate_control.py
                      .venv/Scripts/python.exe research/scale_field/gate_charts.py
                      .venv/Scripts/python.exe -m pytest research/scale_field/ -q
```

Gate C must run before B and D — both read their thresholds off `gateC_null_rate.json` so the threshold
is one artifact and never a second copy of the numbers. Gate D is the long pole at 48 minutes for 60
events; everything else is minutes.

**Charts, and the number each one supports.**

| chart | supports |
|---|---|
| `gateC_noise_ruler.html` | 2·sd against the −1 bound; the read factors marked at n_eff = 8·rf |
| `gateC_null_rate.html` | measured P(F < −2·sd), 380× thinner than normal theory at n_eff = 8 |
| `gateB_survival_vs_read_factor_{centred,onesided}.html` | 2.1% → 21.8% survival of marked time |
| `gateB_survival_vs_scale.html` | survivors sit coarse; the null rate drawn on the same axes |
| `gateD_shaded_vs_prints_rf{1.0,2.0,4.0}.html` | the n = 60 scatter, slope, r² |
| `gateE_reliability.html` | r = 0.90–0.99 at every scale |
| `gateF_median_width_over_s.html`, `gateF_depth_median.html` | flat texture through both Allan knees |
| `excess_variance_{centred,onesided}.html` | observed sd ÷ sampling-noise sd, 2.3–27× |
| `surrogate_control.html` | the excess is clustering below 30 s, rate path above 60 s |

**Constraints observed.** The estimator in `scale_field.py` is imported and called, never modified —
`compute_event` from the committed panel script is what produces every field here. The renderer is
`plot_boundary_through_time.THEMES`, imported, not re-derived. Every quantity is tick-derived; no spine
numeric enters any computation and `momentum_pct` appears only as a cohort descriptor (D4). Reads are
targeted per event through the canonical spine — no full-table scan over `filtered_trades`. Premarket
and regular hours are reported separately throughout and never pooled. Every quantity is reported at
all four read factors, and `_reduce_extremum` stays off.
