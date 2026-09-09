# Does the scale field detect anything real on this tape?

**Date:** 2026-09-08, **revised 2026-09-09 after a second review** - see §1, which withdraws the
scale-anchored headline. **Type:** diagnostic read. Records no decision, applies no gate, produces no
digest.
**Brief:** goals-and-tests, 2026-09-07. **Cohort:** the ten committed panel events
(`results/scale_field/artifacts/event_panels_cohort.csv`), plus a 60-event print-count-stratified
draw for Gate D.
**Code:** `research/scale_field/instrument_gates.py`, `gateA_resolve.py`, `satisfiability.py`,
`excess_variance.py`, `surrogate_control.py`, `gateD_cohort.py`, `gate_charts.py`, and the
review follow-ups `read_scale_distribution.py`, `gateD_vs_surrogate.py`, `gateE_ceiling.py`,
`gateF_calibration.py`, `gateF_recompute.py`; and the 2026-09-09 follow-ups
`surrogate_bandwidth_family.py`, `bandwidth_floor.py`, `subsecond_origin.py`,
`premarket_coverage.py`, `read_by_rate.py`, `absolute_vs_ratio.py`, `crossover_vs_decay.py`.
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

## 1. The answer to §1 — third version, and the second retraction

**The 30-second crossover was the surrogate's bandwidth, not the tape's. It is withdrawn.**
**What survives the bandwidth sweep is a sub-second excess, and that excess is print fragmentation.**
**On this cohort, at the scales this instrument can read, there is no established burst structure left.**

Sweeping the surrogate bandwidth `h` over 1 – 300 s, the measured crossover is **2.6 s, 5.5 s, 14.6 s,
42.5 s, 86.9 s, 305 s** — it tracks `h` at roughly `2.6h` throughout. **The positive control settles it
beyond argument: `S30`, a tape built to carry envelope structure above 30 s, nothing below it and no
clustering anywhere, returns a crossover of 88.8 s at `h = 30` against the real tape's 89.3 s.
Indistinguishable.** The mechanism is that re-estimating `λ̂` at bandwidth `h` from a tape already
smooth at `h` gives an effective bandwidth of `h√2`, so any tape with an envelope shows a spurious
excess below ~3h. A homogeneous-Poisson control does not — which is why one control was not enough, and
why the first version of this read had no way to catch it.

**What survived that sweep looked like a real finding for about an hour.** Below ~1 s the excess is
genuinely invariant to `h`: **3.99 / 3.79 / 3.78 / 3.48 / 3.63** at `s = 0.25 s` for `h` = 1 / 2 / 5 /
15 / 30, a 30× sweep, while both structureless controls read **0.96 – 1.03 at every `h`**. That cannot
be intensity structure the surrogate is missing.

**It is order fragmentation.** 40–57% of inter-print intervals on these tapes are **under one
millisecond** (median ITT 0.3–2.8 ms). Collapsing prints within a tolerance — and rebuilding the
surrogate from the collapsed tape each time, so the comparison stays like-for-like — the excess at
0.25 s falls **4.06 → 2.63 → 1.29 → below 1** at tolerances of 0 / 1 / 10 / 100 ms. **The
bandwidth-invariant fine excess is driven by sub-10 ms print clustering**, which sits at or below the
band CLAUDE.md already records as unmeasurable on this cohort ("zero of 100 events are admissible in
the fine band; do not aim any test there"). Whether it is one order printing many times or genuine
ultra-fast arrival clustering is **not decidable from the trade tape alone** and needs order-level
attribution or the quote side.

**So, against the brief's three options: the honest answer is now (ii) for every scale this cohort can
measure.** The field is a correct instrument — Gates 0, A, C and F's calibration all hold, and the
estimator is right to machine precision — but every positive claim this lineage has made about *what it
detects* has now failed a control: the coarse marks are the session envelope, the mid-scale crossover
was the surrogate's bandwidth, and the fine excess is the print process.

**What is still true, and it is not nothing:** the field is not *sampling* noise (Gate B's survivors
run 111× the estimator's own null; Gate E's raw reliability is 0.90–0.99), the estimator is correct,
the noise ruler reproduces, and `read_factor = 1`'s satisfiable band is empty. Those are statements
about the instrument and they stand. **The statements about the tape do not.**

> **One input to this brief does not exist.** §0 directs "read `claude/scale_field_reading_grammar.md`
> first". There is no such file in the checkout or in git history — it lives in the Claude project. Every
> derivation attributed to it was re-derived here and reproduces (Gate C's table to ≤ 0.013 absolute).

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
| **D** | survivor fraction on log print count, `rf = 4`, RTH, **n = 60** | no material dependence | **r = −0.016, r² = 0.000**, 0.1009 → 0.0999 over 197× | pass, but see next row |
| **D** | **same, against the smooth-rate surrogate instead** (review §2) | real ≫ envelope | **RTH 9.9×**, `s<30` **10.6×**; `s>64` **2.0×**; premarket `s>64` **0.83×** | **the separating test; print count could not do it** |
| **D** | same at `rf = 1`, RTH, vs surrogate | " | **40.9×** the envelope | real, but yield 1.2% and satisfiable band empty |
| **D** | sign-only shaded fraction on print count, any `rf` | no material dependence | r = 0.54 – 0.75, r² = 0.29 – 0.56 | **fails** |
| **D** | geometric control: log raw count on log prints | slope ≈ 1 is arithmetic | **r = 0.971 / 0.982 / 0.991** | Arm A's r = 0.96 reproduced, means nothing |
| **E** | split-half reliability vs scale, 8 events × 3 draws | none | 0.898 – 0.993, min 0.865 | **not interpretable alone** |
| **E** | **the same on a smooth-rate surrogate — the CEILING** (review §3) | — | **≈ 0.00 below 8 s**, 0.33 at 16 s, 0.82 at 32 s, **0.95–0.99 above 64 s** | **fine-scale r is real; coarse r is the envelope** |
| **E** | reliability in excess of that ceiling | — | **0.87 – 0.95 below 8 s**; **0.00 – 0.02 above 64 s** | the band, again |
| **E** | thinning invariance `λ → cλ` (verified first) | bias ≈ 0 | **+0.0015** at 50%, **+0.0016** at 25% | **verified** |
| **F** | **width statistic calibrated** (review §4) | 2.00 on noise, 2.83 on a `σ = s` bump | **1.99 – 2.10** on Poisson (target 1.987); **2.838** on the bump (predicted 2.828, ratio **1.003**) | **estimator unbiased** |
| **F** | real tape, mean width/s, complete runs only | — | RTH **1.36 → 1.97**, never above the Poisson value; p90 2.4–2.8 vs Poisson p90 3.0–3.1 | **nothing in 8–512 s was ever resolved** |
| **F** | read scale in absolute seconds, mark-weighted, `rf = 4` (review §1) | — | **RTH 4.4 s, 100% < 30 s**; premarket 153 s, 75% > 64 s | **the finding is per segment** |
| **G1** | **crossover vs surrogate bandwidth `h`** (2026-09-09 §1) | sits still if it is the tape's | **2.6 / 5.5 / 14.6 / 42.5 / 86.9 / 305 s** at `h` = 1/2/5/15/30/100 — **tracks `h` at ≈2.6h** | **the crossover is the surrogate's. WITHDRAWN** |
| **G1** | positive control `S30` (envelope only, nothing below 30 s) at `h = 30` | must show no crossover | **88.8 s** vs the real tape's **89.3 s** | **indistinguishable — the artifact, proven** |
| **G1** | negative control, homogeneous Poisson, every `h ≤ 30` | 1.00, no crossover | **0.38 – 0.94 s**, i.e. none | pass |
| **G1** | excess at `s = 0.25 s` across `h` = 1 … 30 | — | **3.99 / 3.79 / 3.78 / 3.48 / 3.63** | **invariant — survives the sweep** |
| **G1** | both null controls at `s = 0.25 s`, every `h` | 1.00 | **0.96 – 1.03** | pass |
| **G2** | **the surviving fine excess vs collapse tolerance** (0/1/10/100 ms) | — | **4.06 → 2.63 → 1.29 → <1** at `s = 0.25 s` | **it is sub-10 ms print clustering** |
| **G2** | share of inter-print intervals under 1 ms | — | **0.40 – 0.57**; median ITT 0.3 – 2.8 ms | the tape is fragmented at that scale |
| **G3** | premarket read scale a ladder-floor artefact? (§2b) | — | floor binds **0.00 – 0.02%** of premarket time at `rf 4` | **not an artefact** |
| **G3** | premarket vs RTH **matched on local rate** (§2a) | — | survivor fraction within a rate bin: **pre 0.098 / rth 0.113** at λ 1–3, **0.112 / 0.178** at λ 10–30 | **the segment split is a rate difference** |
| **G4** | `rf = 1`'s 40.9× — ratio or vanishing denominator? (§3) | — | ratio non-monotone **37 / 46 / 21 / 11**; abs excess **0.012 / 0.057 / 0.084 / 0.096**; excess mean F **2.02 / 1.43 / 1.07 / 0.83 sd** | **ratio retired; the two absolute statistics disagree** |
| **G5** | crossover vs event envelope curvature (§4) | tracks if it is the envelope | slope 0.12 – 0.85, **t ≤ 1.25, n = 5**, and L spans only 92 – 111 s | **underpowered — no leverage in this cohort** |

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

**The literal form in the brief is not the form that can meet the tolerance — the threshold was wrong,
not the estimator.** `Σᵢ F(tᵢ)` over prints
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

### 5.2 Where the read actually lands, in seconds

**The tension the review found, and it is the first thing to settle.** Gate B's survivors concentrate
at the coarse end of the ladder; the surrogate control says the excess above ~64 s is entirely the rate
path. If the marks that clear the noise ruler sit up there, the threshold is firing on the session
envelope and *"detects cleanly at rf = 4"* would be a statement about the clock.

**A session-mean λ̂ is the wrong denominator and would have got this backwards.** Marks concentrate
where the tape is fast, so the read scale *where marks actually occur* is far finer than a session mean
implies. Every number below is time-weighted over the surviving marks themselves.

Read scale `s* = read_factor · s_min(t)` in absolute seconds, survivor-weighted, median across the ten
events:

| segment | rf | q05 | q25 | **median** | q75 | q95 | **share < 30 s** | share > 64 s |
|---|---|---|---|---|---|---|---|---|
| **rth** | 1 | 0.25 | 0.25 | **0.34** | 1.24 | 3.30 | **1.000** | 0.000 |
| rth | 2 | 0.25 | 1.14 | **2.41** | 4.28 | 8.39 | **1.000** | 0.000 |
| rth | 4 | 0.55 | 2.28 | **4.38** | 8.12 | 16.03 | **1.000** | **0.000** |
| **premarket** | 1 | 1.08 | 6.77 | **12.84** | 33.80 | 46.14 | 0.574 | 0.000 |
| premarket | 2 | 6.57 | 26.51 | **86.75** | 166.62 | 225.01 | 0.266 | **0.621** |
| premarket | 4 | 9.12 | 52.20 | **152.71** | 292.21 | 414.83 | **0.159** | **0.746** |
| **post** | 4 | 26.80 | 61.80 | **99.07** | 146.03 | 213.67 | 0.059 | 0.711 |

**Regular hours reads at 4.4 s at `rf = 4`, and 100.0% of surviving marked time sits below 30 s** — the
q95 is 16 s, so essentially the whole distribution is inside the band where the excess is not a rate
path. The mark-weighted rate there is ≈ 2.1 prints/s, about **seven times** the session mean, which is
exactly the understatement the review predicted a session mean would produce.

**Premarket and post-close do not.** At `rf ≥ 2` their surviving marks sit 62–75% above 64 s. Same
read factor, same threshold, opposite band — which is why the segments were never poolable, and why
the finding has to be stated per segment.

Charts: `read_scale_survivor_weighted.html`, `read_scale_marked_weighted.html`.

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

### 6.3 Gate D against the surrogate — the test print count could not do

> **⚠ Every number in this subsection uses the `h = 30 s` surrogate, and §10 shows that bandwidth
> manufactures a crossover at ~89 s on a tape with no structure below 30 s. The comparison BETWEEN
> read factors and BETWEEN segments is unaffected — they all face the same surrogate — but the
> "below 30 s / above 64 s" split it reports is the surrogate's bandwidth and not the tape's.
> Read §10 first.**

**The gate had a hole and it is mine.** Gate D was built to catch the Arm A failure — marks
proportional to activity — and it catches it. It cannot catch the failure the surrogate control raised.
**A diurnal envelope produces a roughly constant shaded fraction across events regardless of print
count, because every session has broadly the same shape — which a print-count regression scores as a
pass.** `r = −0.016` at `rf = 4` is consistent with both "detecting real structure" and "detecting the
session envelope", and no regression on print count can separate them.

The surrogate *is* the envelope hypothesis made measurable: same `λ̂` path, same `s_min`, same read
scale, same debounce, same threshold, **no clustering at any scale**. Survivor fraction, median of the
ten panel events, split by the absolute read scale because the segments read two decades apart:

| segment | band | rf 1 | rf 2 | rf 3 | rf 4 |
|---|---|---|---|---|---|
| **rth** | all | **40.9×** | **29.9×** | **15.9×** | **9.9×** |
| rth | `s < 30 s` | 41.2× | 31.5× | 17.7× | **10.6×** |
| rth | `s > 64 s` | — | — | 0.43× | **2.0×** |
| **premarket** | all | 4.0× | 1.07× | 1.31× | **1.37×** |
| premarket | `s < 30 s` | — | **12.5×** | **6.0×** | **10.2×** |
| premarket | `s > 64 s` | — | 0.64× | 1.06× | **0.83×** |
| **post** | all | 0.88× | 0.93× | 1.01× | **0.80×** |
| post | `s < 30 s` | — | — | **6.0×** | **3.5×** |
| post | `s > 64 s` | 0.00× | 0.49× | 0.71× | **0.78×** |

**Three things fall out and they are consistent across all three segments.**

1. **Below 30 s the real tape runs 3.5–41× the envelope.** That is detection, and it survives in every
   segment including premarket and post, where the segment-level number does not.
2. **Above 64 s the real tape is at or below the envelope** — 0.43× to 2.0×, and *below 1.0* in
   premarket and post at every read factor. Marks up there are not merely explained by the clock, in
   the slow segments the real tape produces **fewer** of them than a structureless tape with the same
   rate path.
3. **The segment-level "all" rows are the misleading ones**, and they are what §1's first draft
   quoted. RTH's `all` number is dominated by its `s < 30 s` band because 100% of RTH survivors sit
   there; premarket's `all` number collapses to 1.07–1.37× because most of *its* survivors sit above
   64 s. Same read factor, same threshold, opposite conclusions — resolved only by splitting on
   absolute scale.

Charts: `gateD_vs_surrogate_{rth,premarket}.html`.

---

## 7. Gate E — split-half reliability, and the ceiling it was missing

> **⚠ The ceiling in this section is built at `h = 30 s`. The finding that the coarse-scale
> reliability is entirely envelope stands — the ceiling reaches 0.95 by 64 s, well above `h`, where the
> surrogate is faithful. The finding that fine-scale reliability is "real structure" inherits §10: the
> `h = 30` ceiling is blind to everything below 30 s by construction, so a near-zero ceiling there was
> guaranteed and proves nothing. §10 redoes it properly.**

**"No null needed" was the wrong claim, and it was mine.** A null is not needed; a **ceiling** is.
Reliability near 1 at *every* scale, including fine scales where `n_eff` is small and noise should
dominate, is the signature of a shared low-frequency component inflating the correlation: both halves
are thinned copies of one realisation, so both carry the same diurnal envelope, and if that envelope
holds most of the variance then `r → 1` whether or not the fine structure replicates.

**The ceiling is the identical split-half run on the smooth-rate surrogate** — same envelope, no
clustering at any scale. Whatever `r` it returns is what the envelope alone buys. Median across eight
events, three draws each, fixed absolute scale grid:

| s (s) | 0.25 | 0.5 | 1 | 2 | 4 | 8 | 16 | 32 | 64 | 128 | 256 | 512 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| r real | 0.963 | 0.941 | 0.913 | 0.897 | 0.903 | 0.904 | 0.926 | 0.940 | 0.962 | 0.975 | 0.985 | 0.992 |
| **r ceiling (surrogate)** | **0.012** | 0.005 | −0.010 | −0.009 | 0.016 | **0.039** | 0.328 | 0.816 | **0.945** | 0.974 | 0.985 | 0.991 |
| **excess over ceiling** | **0.951** | 0.936 | 0.923 | 0.906 | 0.887 | **0.865** | 0.598 | 0.124 | **0.017** | 0.001 | 0.000 | 0.001 |
| r, envelope subtracted | 0.963 | 0.941 | 0.913 | 0.897 | 0.903 | 0.902 | 0.913 | 0.841 | 0.451 | −0.416 | −0.770 | −0.779 |

**The worry was right to raise and the measurement answers it in the opposite direction.** The envelope
buys **essentially nothing below 8 s** — the ceiling is 0.012 at 0.25 s and 0.039 at 8 s, so the
fine-scale reliability of 0.90–0.96 is **almost entirely real structure**. It is above 16 s that the
ceiling climbs, and by 64 s it has eaten the whole number: `r = 0.962` against a ceiling of `0.945`,
excess **0.017**.

**So Gate E's number is quotable, but only below ~16 s, and it was not quotable as first written.**
The corrected statement: split-half reliability in excess of what the envelope alone provides is
0.87–0.95 below 8 s and 0.00–0.02 above 64 s. That is the same crossover the surrogate control and
Gate D-vs-surrogate find, reached with no null model, no threshold and no burst definition.

**A caveat on the third row, against my own metric.** Subtracting a common envelope expectation from
both halves and correlating the residuals agrees with the raw number below 16 s (there is nothing to
subtract) but goes **negative** above 128 s, which is an artefact rather than a finding: at scales
where `F_env ≈ F_full ≈ (F_A+F_B)/2`, the residuals become `±(F_A−F_B)/2` and anti-correlate by
construction. **The surrogate ceiling is the clean reference and is the one to read**; the residual row
is kept because it agrees where it is valid and because its failure mode is worth recording.

The earlier caveat stands and is now quantified: at s = 0.25 s only 41% of the coarse-end grid is
defined in *both* halves, so the fine rows describe the densest stretches of tape rather than the fine
band generally.

Thinning invariance is unchanged and was verified before any of this was read: thinning to 50% shifts
the mean field by **+0.0015**, to 25% by **+0.0016**. Level unchanged, noise up.

Chart: `gateE_ceiling.html`.

---

## 8. Gate F — calibrated, and it says nothing was ever resolved

**The first pass quoted an uncalibrated statistic and drew too strong a conclusion from it. Both are
corrected here.**

### 8.0 The statistic, against both of its references

Two reference points, and the estimator is checked against each before its output is read.

**Pure noise → 1.987, derived not assumed.** `λ̂` from a Poisson tape smoothed at scale `s` has
autocovariance ∝ `exp(−t²/4s²)`, hence spectrum ∝ `exp(−ω²s²)`. For a stationary Gaussian process the
zero-crossing rate of the k-th derivative is `(1/π)√(λ_{2k+2}/λ_{2k})` in spectral moments, and
`F < 0 ⟺ λ̂″ < 0`, so k = 2: `λ₆/λ₄ = 2.5/s²`, rate `= √2.5/(πs) = 0.5033/s`, **mean run length
1.987 s**.

**A bump of width σ read at scale s → `2√(1 + σ²/s²)`**, since convolving Gaussians of width σ and s
gives `√(σ²+s²)` and the second derivative of a Gaussian is negative inside ±its own width. **2.828 at
σ = s.**

Measured:

| reference | target | measured | ratio |
|---|---|---|---|
| homogeneous Poisson, **mean** width/s, s = 1 … 64 | 1.987 | **1.99 – 2.10** | 1.00 – 1.06 |
| injected bump, σ = s | 2.828 | **2.838** | **1.003** |
| injected bump, s = 2σ | 2.236 | 2.243 | 1.003 |
| injected bump, s = 4σ | 2.062 | 2.065 | 1.002 |

**The estimator is unbiased.** The masks and the print-indexed grid contribute nothing (`uniform_fine`,
`uniform_masked` and `print_indexed` agree to three decimals at λ = 40/s).

**So where did 1.85 come from?** Two errors in the first pass, both biasing down, both mine.
**(a) It quoted the median against a mean reference.** The 1.987 target is the reciprocal of a
crossing rate, i.e. a mean; run lengths are right-skewed, so on pure noise the median returns 1.88–2.01
where the mean returns 1.99. **(b) It counted truncated runs** — runs cut by a NaN cell or by the
segment boundary are not measurements of a run length, and on real tape at fine scales the defined
share is low, so this bit hardest exactly where the first pass reported its lowest values.

### 8.1 The corrected curve, and what it says

Mean width/s over **complete runs only**, median across the ten events:

| s (s) | 0.25 | 0.5 | 1 | 2 | 4 | 8 | 16 | 32 | 64 | 128 | 256 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **RTH mean, complete** | 1.355 | 1.489 | 1.629 | 1.691 | 1.783 | 1.822 | 1.858 | 1.904 | 1.878 | **1.966** | 1.814 |
| ÷ Poisson (1.987) | 0.68 | 0.75 | 0.82 | 0.85 | 0.90 | 0.92 | 0.94 | 0.96 | 0.95 | **0.99** | 0.91 |
| complete share | 0.54 | 0.65 | 0.75 | 0.87 | 0.94 | 0.99 | 0.99 | 0.99 | 0.98 | 0.98 | 0.91 |
| premarket mean, complete | 1.597 | 1.639 | 1.774 | 1.728 | 1.745 | 1.769 | 1.894 | 1.900 | 1.685 | 1.885 | — |

**It is not flat, and it never approaches 2.83.** The corrected curve *rises* from 0.68× the Poisson
value at 0.25 s to 0.99× at 128 s — so the earlier "flat at 1.85" was substantially truncation. What
survives calibration is the stronger and simpler claim, and it is the review's reading rather than the
first pass's:

**Nothing in 8–512 s has σ comparable to s.** A resolved feature at its own scale would push width/s
toward 2.83; the real tape never exceeds 1.97, and its p90 (2.40–2.78 RTH) sits *below* the pure-Poisson
p90 (2.98–3.10). **Every quantile of the width distribution is shorter than Poisson, never longer.**
That is *"nothing in this band was ever resolved"* — a different claim from *"the process is
scale-free"*, and the first pass should not have made the second one.

It also points the same way as everything else: runs shorter than Poisson means **more** zero-crossings
than Poisson, i.e. structure at higher frequency than the scale being read — consistent with the empty
satisfiable band, and with the excess living below 30 s.

**On the Allan comparison, the review is right and I overstated it.** The Allan factor counts variance
against window width; negative-run width is curvature geometry. **A process can have an Allan knee with
no change in curvature texture**, so the absence of a knee-shaped feature in this statistic is not
evidence that either measurement is wrong. The two measure different things. Flagging the
non-appearance was worth doing; calling it a contradiction was not, and that framing is withdrawn.

Charts: `gateF_calibrated.html`, `gateF_median_width_over_s.html`, `gateF_depth_median.html`.

### 8.2 The one curve with no threshold in it

> **⚠ The surrogate comparison in this subsection is `h = 30 s`. Its coarse half stands; its
> "below 30 s the excess is not a rate path" half is circular — a 30 s-smooth surrogate cannot
> reproduce 5 s structure by construction. §10.**

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

## 9. The premarket inversion, and §3's split — review items 2 and 3

### 9.1 Premarket is not a grid artefact, and it is not a segment effect

**§2(b), the five-minute check, comes back clean.** The ladder floor (`0.25 s`) binds on **0.00–0.02%
of premarket time at `rf = 4`** — the fast premarket stretches are not falling off the bottom of the
grid. (It binds more in *regular hours*: 4.8% at `rf 1`, 0.58% at `rf 4`.) What *is* large in premarket
is the `n_eff` mask: 3–73% of premarket time has no defined scale at all on some events, which is the
tape being too thin, not the grid being too coarse.

**§2(a) resolves the inversion, and it dissolves the segment split.** Matched on local `λ̂`, premarket
and regular hours behave the same — survivor fraction within a rate bin, `rf = 4`:

| λ̂ bin (/s) | 0.03–0.1 | 0.1–0.3 | 0.3–1 | 1–3 | 3–10 | 10–30 | 30–100 |
|---|---|---|---|---|---|---|---|
| **premarket** | 0.080 | 0.106 | 0.114 | 0.098 | 0.086 | 0.112 | 0.256 |
| **rth** | 0.029 | 0.072 | 0.078 | 0.113 | 0.158 | 0.178 | 0.319 |
| mean `s*` premarket (s) | 193 | 62 | 20 | 5.8 | 1.9 | 0.61 | 0.26 |
| mean `s*` rth (s) | 129 | 55 | 17 | 5.9 | 2.0 | 0.64 | 0.26 |
| survivor share below 30 s | 0.00 | 0.00 | 0.93–0.99 | 1.00 | 1.00 | 1.00 | 1.00 |

**Same rate, same read scale, same survivorship.** The segment difference is a *time-allocation*
difference: across the ten events premarket spends **26.4 hours below λ̂ = 0.1/s** and 0.9 h above
10/s, while regular hours spends **34.4 h above 1/s** and 1.9 h below 0.1/s. Premarket reads at 153 s
because premarket is mostly dead tape, not because premarket is different.

**So segment was the wrong conditioning variable and the review is right that rate is the portable
one.** The crossing of the 30 s line happens at `λ̂ ≈ 0.3/s` at `rf = 4`, which is arithmetic
(`4 × 2.2568 / 30 = 0.30`) and confirms the binning rather than discovering anything.

**One correction to the review's proposed mechanism.** The envelope-bias argument — slower tape, coarser
read, more envelope, more survivors — predicts survivorship *falling* with rate. **Measured, it rises**:
0.029 → 0.319 across the RTH rate bins. So the mechanism is real but is not the dominant term. Slow tape
does manufacture coarse survivors (6.5% of premarket time below λ̂ = 0.03/s, **all of it above 30 s**),
but fast tape produces more of them and all below 30 s. Both effects are present; the second is larger.

### 9.2 The 40.9× was a vanishing denominator — and the two absolute statistics disagree

**The ratio is retired, as the review asked, and the reason is visible in its own numbers:** it is
**non-monotone** in read factor — 37.4, 46.1, 21.3, 11.2 at `rf` 1/2/4 — which no property of the read
should be. It is division by a surrogate field that collapses as `(s/L)²`.

On the two absolute statistics, both holding `n_eff` fixed at `8.01·rf`:

| rf | sd at read | survivor fraction, real | surrogate | **ABS excess** | **excess mean F, in sd** |
|---|---|---|---|---|---|
| 1 | 0.392 | 0.0118 | 0.0003 | 0.0117 | **+2.018** |
| 2 | 0.238 | 0.0584 | 0.0013 | 0.0569 | +1.426 |
| 3 | 0.188 | 0.0881 | 0.0043 | 0.0840 | +1.067 |
| 4 | 0.159 | 0.1076 | 0.0092 | **0.0957** | +0.826 |

**They disagree, so the tension changes shape rather than dissolving.** On yield — excess survivor time
per unit admissible time — `rf = 4` leads by **8×**, and the review's prediction holds. On per-cell
displacement from the envelope, `rf = 1` leads at **2.02 sd against 0.83**, and it does not. Both are
absolute, both hold `n_eff` fixed, and they are measuring different things: `rf = 1` reads where the
contrast per cell is largest, but its threshold (`2·sd = 0.785` against a bound of −1) admits almost
nothing; `rf = 4` reads where contrast per cell is weaker and the threshold is three times easier.

**The decision text should therefore say: the ratio is not a comparable statistic and is withdrawn;
`rf = 1` is retired on measurability (the satisfiable band is empty) and on yield (8× less), not on
per-cell signal, where it is in fact the strongest read.** That is a narrower claim than either the
original tension or the review's proposed resolution.

*(Both rows use the `h = 30` surrogate and inherit §10's caveat on absolute magnitude; the comparison
between read factors is unaffected because they face the same surrogate.)*

---

## 10. The bandwidth sweep, and what it took away

*(This is the review's §1, run with four controls rather than one. It is placed last because it
retracts things stated above, and the retraction is easier to read once they have been stated.)*

### 10.1 The sweep

| base tape | ground truth | h=1 | h=2 | h=5 | h=15 | h=30 | h=100 | h=300 |
|---|---|---|---|---|---|---|---|---|
| **real** | the question | 2.6 | 5.5 | 14.6 | 42.5 | 86.9 | 305 | none |
| **S30** envelope only, nothing below 30 s | crossover at 30 s, or none | 0.7 | 0.8 | 0.8 | 31.1 | **89.2** | 297 | none |
| **NS05** clusters at σ = 0.5 s | must be detected | 2.5 | 4.7 | 10.7 | 39.3 | 86.6 | — | — |
| **Poisson** nothing at all | 1.00, no crossover | 0.7 | 0.6 | 0.4 | 0.9 | 0.4 | 99 | 214 |

**The real tape's crossover is ≈ 2.6·h at every bandwidth over two decades.** And `S30` — which by
construction has *nothing* below 30 s — returns **89.2 s at `h = 30` against the real tape's 86.9 s.**
A tape with no fine structure and the real tape are indistinguishable on this statistic at the
bandwidth the earlier sections used.

**Why:** re-estimating `λ̂` at bandwidth `h` from a tape already smooth at `h` composes to `h√2`, so the
surrogate is smoother than its own base and every tape with an envelope shows a spurious excess below
~3h. The Poisson control does not show it because it has no envelope to double-smooth — **one control
was not enough, and that is the methodological lesson.**

### 10.2 What survived, and how it was checked

The ratio *curve*, not the crossover, is bandwidth-invariant at the fine end:

| s | h=1 | h=2 | h=5 | h=15 | h=30 |
|---|---|---|---|---|---|
| **0.25** | **3.99** | 3.79 | 3.78 | 3.48 | 3.63 |
| 0.50 | 3.62 | 3.74 | 3.49 | 3.48 | 3.55 |
| 1.00 | 2.09 | 3.42 | 3.45 | 3.43 | 3.17 |
| 4.00 | 1.02 | 1.21 | 2.30 | 3.51 | 3.65 |
| 64.0 | 0.99 | 0.99 | 0.99 | 1.05 | 1.21 |
| `S30` at 0.25 | 0.96 | 1.03 | 1.03 | 1.03 | 1.03 |
| `Poisson` at 0.25 | — | — | — | — | — (masked) |

At `h = 1` the surrogate carries every intensity variation down to 1 s and the real tape **still**
exceeds it 4× at 0.25 s, while `S30` reads 0.96. **`NS05` is the control that says the procedure has
not gone blind**: a σ = 0.5 s cluster process is still detected at `h = 1` (ratio 1.54 at s = 1 s),
though it is losing sensitivity there — at `h ≥ 2` it reads 1.95–2.04. So `h = 1` is near the
overfitting floor but has not passed it.

**And `NS05`'s shape does not match the real tape's.** NS05 peaks at s ≈ 1 s and reads **1.03 at
0.25 s** — below its own cluster width a cluster looks like a locally elevated Poisson rate, so there
is nothing for a curvature statistic to see. The real tape rises **monotonically as s falls**. Whatever
the real fine structure is, it is *not* shaped like clustering at 0.5 s; it is at or below the ladder
floor.

### 10.3 And below the ladder floor is the print process

| s | tol = 0 ms | 1 ms | 10 ms | 100 ms |
|---|---|---|---|---|
| **0.25** | **4.06** | **2.63** | **1.29** | — (masked) |
| 0.50 | 3.66 | 2.14 | 1.42 | 0.46 |
| 1.00 | 2.13 | 1.65 | 1.16 | 0.67 |
| 4.00 | 1.02 | 0.93 | 0.81 | 0.72 |

**40–57% of inter-print intervals on these tapes are under one millisecond**, median ITT 0.3–2.8 ms.
Collapsing prints within a tolerance — with the surrogate rebuilt from the collapsed tape each time, so
`F`'s invariance to `λ → cλ` keeps the comparison like-for-like and thinning alone cannot move the
ratio — takes the 0.25 s excess from **4.06 to 1.29 at a 10 ms tolerance** and below 1 at 100 ms.

**The surviving excess is sub-10 ms print clustering.** CLAUDE.md already records that band as
unmeasurable on this cohort. Whether it is one order printing many times against multiple resting
quotes, or genuine ultra-fast arrival clustering, **cannot be decided from the trade tape alone** —
it needs order-level attribution or the quote side, and neither is in scope here.

*(The collapse is diagnostic only. `collapse_same_timestamp` is the committed tie variant and nothing
here proposes moving it.)*

### 10.4 Review §4 — the portability test is underpowered, not negative

Regressing log crossover on log envelope curvature scale gives slopes of 0.12 / −0.05 / 0.52 / 0.85 /
0.33 at `h` = 1/2/5/15/30, **all with `t ≤ 1.25` on n = 5**. But the cohort supplies almost no leverage:
the ten events' envelope curvature scales span **92.4 – 110.7 s, a factor of 1.2**. The right statement
is not "the crossover does not track the envelope" but **"this cohort cannot test it"** — and since
§10.1 shows the crossover is set by `h` rather than by the tape, the question as posed is moot until
there is a crossover that is a tape property to regress.

Charts: `bandwidth_family_ratio.html`, `bandwidth_floor_controls.html`,
`subsecond_collapse.html`.

---

## 11. What I would do next — offered as a view, and labelled as one

1. **Write down the retraction before anything else.** Two headlines from this read are now wrong in
   the record: "detects cleanly at `read_factor = 4`" (withdrawn 2026-09-08) and "the crossover is at
   30 seconds" (withdrawn here). The pattern in both is the same and is worth stating once, plainly:
   **this lineage keeps finding structure in the properties of its own instrument.** Arm A found it in
   the print count, Gate B found it in a Poisson null that does not contain the envelope, the scale
   finding found it in a surrogate bandwidth. Each was caught by a control, and each control had to be
   built after the claim was made.

2. **The one decision that survives all of this is still worth taking, and it is unchanged.** Retire
   `read_factor = 1` from the panels. `n_eff = 8` exactly at the read, `2·sd = 0.785`, `F ≥ −1`, so
   detection needs `σ < 0.523·s_min` while a width can only be read at `σ ≥ s_min` — **the satisfiable
   band is empty.** That is arithmetic. It does not depend on any surrogate, any null, or any of the
   three retracted findings. §9.2 sharpens the wording: retire it on measurability and yield, **not**
   on per-cell signal, where it is the strongest read of the four.

3. **Do not run injection–recovery yet.** It was the natural next build when there was a band and an
   operating point; there is now neither. Recovering an injected burst would prove the instrument can
   see what you put in — which Gate F's calibration and `NS05` have already shown — without addressing
   the question that actually failed, which is whether anything in the tape is there to be found.

4. **The one question left is well-posed and cheap: is there anything between 10 ms and 1 s?**
   §10.3 puts the surviving excess below 10 ms and CLAUDE.md rules that band unmeasurable here. §10.2
   shows the real tape's shape does not match clustering at 0.5 s. So the honest next measurement is a
   **collapsed-tape** run: rebuild at a 10 ms tolerance, which removes the fragmentation, and ask
   whether *anything* clears a bandwidth-swept surrogate between 10 ms and a few seconds. The numbers
   in §10.3 already hint at the answer (1.29 and 1.42 at 0.25 and 0.5 s, against 1.00 controls) — a
   small residual, worth one clean measurement rather than a programme.

5. **If that comes back at 1.0, the rate channel is finished on this cohort and should be said so.**
   Not "further work is needed" — finished. Four segmentation attempts died in this lineage before
   this one; the expensive part each time was how long it took to say so, and this read has now spent
   three headlines learning the same thing.

6. **Whatever happens, adopt the review's general form of the lesson**, because it applies to every
   future gate here and not just this one:

   > **A null that does not contain the structure you are conditioning on will score that structure as
   > signal.** A surrogate that contains too little is a false-positive machine; one that contains too
   > much is a false-negative machine; and the bandwidth is the dial between them. **Audit a control
   > for what it contains, not only for what it randomises** — and sweep the dial rather than picking
   > a value.

7. **Open the charts.** They are gitignored by the same deliberate rule that excludes the panel charts
   and exist only locally: `results/scale_field/charts/instrument_gates/`. `bandwidth_family_ratio.html`
   and `subsecond_collapse.html` carry the retraction, and neither is legible from a table.

**A note on Gate F, adopting the review's reading.** `width/s = 2√(1 + σ²/s²) ≥ 2` for an isolated
bump — a feature can only make the negative region *wider* than `2s`, never narrower. So "every
quantile shorter than Poisson, never longer" is not merely the absence of resolved features: **it means
the negative regions are being cut short by neighbours**, adjacent features closer than `2s`
interposing positive ridges. Read positively, **the fine structure is densely packed and non-isolated
at every scale examined**, tightest at fine scales (0.68× Poisson) and loosening toward coarse (0.99×)
— the same direction as everything else, from a statistic with no surrogate in it at all. It also says
plainly what the burst object was never going to be: **there are no isolated episodes to segment**,
anywhere in 8–512 s. D21 §6(b) chose the continuous state descriptor on pragmatic grounds; this is the
geometric reason that was the right call.

## 12. Reproduction

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
                      .venv/Scripts/python.exe research/scale_field/read_scale_distribution.py
                      .venv/Scripts/python.exe research/scale_field/premarket_coverage.py
                      .venv/Scripts/python.exe research/scale_field/read_by_rate.py
                      .venv/Scripts/python.exe research/scale_field/absolute_vs_ratio.py
                      .venv/Scripts/python.exe research/scale_field/surrogate_bandwidth_family.py 6
                      .venv/Scripts/python.exe research/scale_field/bandwidth_floor.py 5
                      .venv/Scripts/python.exe research/scale_field/subsecond_origin.py 5
                      .venv/Scripts/python.exe research/scale_field/crossover_vs_decay.py
                      .venv/Scripts/python.exe research/scale_field/gateE_ceiling.py 3
                      .venv/Scripts/python.exe research/scale_field/gateF_calibration.py
                      .venv/Scripts/python.exe research/scale_field/gateF_recompute.py
                      .venv/Scripts/python.exe research/scale_field/gateD_vs_surrogate.py
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
| `read_scale_survivor_weighted.html` | RTH reads at 4.4 s, premarket at 153 s, at the same rf |
| `gateD_vs_surrogate_{rth,premarket}.html` | 9.9-41x the envelope below 30 s, <=1x above 64 s |
| `gateE_ceiling.html` | the ceiling the envelope alone buys: ~0 below 8 s, 0.95+ above 64 s |
| `gateF_calibrated.html` | the width statistic against both references; nothing resolved |
| `bandwidth_family_ratio.html` | **the retraction** - the crossover tracks h at ~2.6h |
| `bandwidth_controls_{real,NS05...,S30...}.html` | the ratio curve per h, with its controls |
| `subsecond_collapse.html` | **4.06 -> 1.29 at a 10 ms collapse** - it is fragmentation |
| `read_by_rate_{survivor_fraction,mean_read_scale_s}.html` | matched on rate, the segments agree |

**Constraints observed.** The estimator in `scale_field.py` is imported and called, never modified —
`compute_event` from the committed panel script is what produces every field here. The renderer is
`plot_boundary_through_time.THEMES`, imported, not re-derived. Every quantity is tick-derived; no spine
numeric enters any computation and `momentum_pct` appears only as a cohort descriptor (D4). Reads are
targeted per event through the canonical spine — no full-table scan over `filtered_trades`. Premarket
and regular hours are reported separately throughout and never pooled. Every quantity is reported at
all four read factors, and `_reduce_extremum` stays off.
