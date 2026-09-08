# Does the scale field detect anything real on this tape?

**Date:** 2026-09-08 (revised same day after review). **Type:** diagnostic read. Records no
decision, applies no gate, produces no digest.
**Brief:** goals-and-tests, 2026-09-07. **Cohort:** the ten committed panel events
(`results/scale_field/artifacts/event_panels_cohort.csv`), plus a 60-event print-count-stratified
draw for Gate D.
**Code:** `research/scale_field/instrument_gates.py`, `gateA_resolve.py`, `satisfiability.py`,
`excess_variance.py`, `surrogate_control.py`, `gateD_cohort.py`, `gate_charts.py`, and the
review follow-ups `read_scale_distribution.py`, `gateD_vs_surrogate.py`, `gateE_ceiling.py`,
`gateF_calibration.py`, `gateF_recompute.py`.
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

## 1. The answer to §1

**The field detects real structure below about 30 seconds and detects nothing but the clock above about
60. That band, not the read factor, is the finding.**

Four methods with almost nothing in common now put the crossover in the same place:

| method | below ~30 s | above ~64 s |
|---|---|---|
| survivor fraction vs smooth-rate surrogate (RTH) | **9.9 – 41× the envelope** | **0.43 – 2.0×**, mostly ≤ 1 |
| split-half reliability vs its surrogate ceiling | r 0.90–0.96, **ceiling ≈ 0.00** | r 0.96–0.99, **ceiling 0.95–0.99** |
| observed sd(F) ÷ sampling noise, real vs surrogate | real/surrogate **1.9 – 3.1×** | real/surrogate **0.76 – 1.03** |
| negative-run width vs its two calibrated references | at or **below** the Poisson value | at the Poisson value |

The read factor matters only because it decides **which side of that line the read lands on**, and the
answer differs per segment — which is why they were never poolable. Weighted by the marks themselves,
at `read_factor = 4`: **regular hours reads at a median 4.4 s with 100% of surviving marks below 30 s**;
**premarket reads at 153 s with 75% above 64 s**; post-close at 99 s with 71% above. So the same
`read_factor = 4` is a real detection in regular hours and a clock reading in premarket.

So option **(iii)** still holds, but "detects cleanly at `read_factor = 4`" was the wrong compression and
is withdrawn. The correct statement is: **in regular hours the field detects structure a smooth rate
path cannot produce, at 10–41× the envelope, at every read factor, because in regular hours every read
factor lands below 30 s. In premarket and post-close at `read_factor ≥ 2` it does not — it reads the
session envelope.** The `read_factor = 1` defect is unchanged and is separate: its satisfiable band is
empty, so nothing it detects can be measured.

> **One input to this brief does not exist.** §0 directs "read `claude/scale_field_reading_grammar.md`
> first". There is no `claude/` directory in this checkout and no file of that name in the repo or in
> git history — it lives in the Claude project, not the git tree. Every derivation attributed to it was
> re-derived here from `scale_field.py` and re-checked numerically, and **all of them reproduce**
> (Gate C's table to ≤ 0.013 absolute), so each now has two independent derivations rather than one.

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

## 9. Six routes, and the one line they all draw

Nothing here rests on one measurement. Six methods with almost nothing in common were run. **They do
not agree on a read factor. They agree on a scale.**

| route | what it needs | below ~30 s | above ~64 s |
|---|---|---|---|
| Gate D vs surrogate (RTH) | a rate-matched control | **9.9 – 41×** the envelope | 0.43 – 2.0×, mostly ≤ 1 |
| Gate E vs its ceiling | a rate-matched control | excess r **0.87 – 0.95** | excess r **0.00 – 0.02** |
| excess variance vs surrogate | a rate-matched control | real/surrogate **1.9 – 3.1×** | real/surrogate 0.76 – 1.03 |
| Gate B magnitude threshold | a Poisson null | survivors **111×** the null | survivors 11 – 17× the null |
| Gate F width, calibrated | two analytic references | **shorter** than Poisson | at Poisson |
| Gate D on print count, n = 60 | a cohort with leverage | *cannot distinguish these* — see §6.3 | |

**Every route that carries a rate-matched control puts the crossover at 30–64 s.** The two routes that
do not — the Poisson null and the print-count regression — cannot see it, and that is the structural
lesson: **a Poisson null and a print-count regression both score the session envelope as a detection.**
Gate B's 111× and Gate D's `r² = 0.000` are both true and both would look identical on a tape with no
clustering whatsoever above the envelope.

**What none of it establishes.** The rate channel cannot separate clumping from a smooth rate excursion
at constant mean rate — two tapes with identical `λ̂(t)`, one Poisson and one violently clustered, give
identical fields (brief §11). The surrogate narrows the question to below 30 s but cannot answer it:
what is established is that **something below 30 s is not a 30-second-smooth rate path**, not that it is
clumping. Nothing here is evidence about burst *duration* (Gate F: nothing in 8–512 s was resolved), or
about tradeability, which D24 and D25 closed on cost arithmetic.

## 10. What I would do next — offered as a view, and labelled as one

1. **State the finding as a band, not a read factor, wherever it is written down.** "Detects at
   `read_factor = 4`" is false in premarket and true in regular hours for a reason that has nothing to
   do with 4: it is whether the read lands below 30 s. The read factor is a means; the band is the
   finding.

2. **Retire `read_factor = 1` from the panels — the derivation is complete and does not depend on
   anything still open.** `n_eff = 8` exactly at the read, `2·sd = 0.785`, `F ≥ −1`, so detection needs
   `σ < 0.523·s_min` while a width can only be read at `σ ≥ s_min`: **the satisfiable band is empty.**
   That is arithmetic, it holds at every rate on every event, and it is unaffected by everything the
   review corrected. It is a real decision with a real derivation and belongs in
   `docs/Universe-Decisions.md`, which this read deliberately did not touch. **Note the tension to
   resolve when writing it:** `rf = 1` in RTH also has the *highest* envelope contrast of any read
   (40.9× against 9.9× at `rf = 4`). It is the purest detection and the least measurable one, and the
   case for retiring it is measurability, not signal.

3. **Do not read anything above ~60 s on this channel as burst structure, in any segment.** In
   premarket and post the real tape produces *fewer* survivors up there than a structureless tape with
   the same rate path (0.49–0.83×). That is the strongest single statement in this read and it is the
   one most likely to be misused if the band is dropped.

4. **The open question this leaves is what the sub-30 s excess is.** The rate channel provably cannot
   answer it. Two routes exist and they are not equivalent: the interval channel (separate work, out of
   scope here) or injection–recovery, which is now well-posed in a way it was not last week — a
   candidate operating point (`rf` 3–4 in RTH), a candidate band (below 30 s, where every controlled
   route agrees the excess is real), and a pre-registered prediction from §5.1 that recovery must
   collapse for `σ > s*·√(1/(2·sd) − 1)`.

5. **Open the charts before any of this is written down.** They are at
   `results/scale_field/charts/instrument_gates/` and are gitignored by the same deliberate rule that
   excludes the panel charts, so they exist only locally. Every closure in this lineage has turned on
   looking at a picture, and none of the numbers above substitute for `read_scale_survivor_weighted.html`
   and `gateD_vs_surrogate_rth.html`.

**A note on the format, since it produced two of the four corrections.** The brief's numbers were
carried by reference to a file outside the checkout, and its Gate A tolerance and Gate E "no reference
needed" claim were both wrong in ways an agent with only the repo could not check against anything.
**A goals-and-tests brief has to carry its numbers and its references inline** — not because the
derivations were bad, but because the agent's whole world is the checkout, and a pre-registered number
it cannot verify is indistinguishable from one it must not question.

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
                      .venv/Scripts/python.exe research/scale_field/read_scale_distribution.py
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

**Constraints observed.** The estimator in `scale_field.py` is imported and called, never modified —
`compute_event` from the committed panel script is what produces every field here. The renderer is
`plot_boundary_through_time.THEMES`, imported, not re-derived. Every quantity is tick-derived; no spine
numeric enters any computation and `momentum_pct` appears only as a cohort descriptor (D4). Reads are
targeted per event through the canonical spine — no full-table scan over `filtered_trades`. Premarket
and regular hours are reported separately throughout and never pooled. Every quantity is reported at
all four read factors, and `_reduce_extremum` stays off.
