# Chop regime C1 — Amendment 1: get to the suite

**Date:** 2026-09-30 · **Amends:** `prompts/chop_regime_c1.md` after the HARD STOP at T5 (escalation row 3).
**Effect:** fixes the control I specified wrong, narrows the stop rule to what actually blocks the suite,
drops the variance ratio, rules the midpoint primary, and runs **T5 (re-run) → T6 → T7 → T8 → T9 straight
through to the suite.** The deliverable at T9 is unchanged: `results/chop_regime/c1/suite/chop_suite.html`.

---

## A1.0 What went wrong — two of the three causes are the brief's

1. **The whole-pipeline null was mis-specified (my error).** §6 said "shuffled and re-integrated". A
   shuffle is a reordering, so it keeps the window's sum: every shuffled path starts and ends where the real
   window does and keeps its net move. It cannot read as noise. The reference control right above it used
   a with-replacement resample of demeaned returns, and this one should have too.
2. **The stop rule was too broad (my error).** Row 3 stopped the whole build on any control failure in any
   measure. The failures were all in the scale-free measures. None of them touches spread, depth, activity,
   concentration or cost-to-noise, which are the core of the filter. The standing rule is that a stop sits
   only where crossing it changes a decision. A failure in one measure should remove or label that measure,
   not hold back the suite.
3. **The robust variance-ratio z is unstable on sparse returns.** This is a real property of the data and
   the brief did not anticipate it. Midpoint bucket returns are mostly zero with isolated one-tick moves.
   The z-score's variance term then goes to about 0, and z blows up (|vz2| > 10 in 0.53% of real midpoint
   windows, 0.13% of VWAP windows). All 6 blindness mismatches were this effect.

**What the run confirmed:** the VWAP averaging bias the brief predicted is real and large. VWAP `vz2` has a
median of about +1.45 on noise, however the null is built.

## A1.1 The variance ratio is dropped from C1

Columns `vr2_k`, `vr4_k`, `vz2_k` and `vz4_k` are not built, and their conditions are removed from §7b.

**Why drop it rather than patch it:**

- On VWAP it is biased toward "trending" by construction.
- On the midpoint, a floor on nonzero returns would add another declared threshold. It would also make the
  variance ratio `unavailable` on the thinnest tapes, which is where chop lives.
- The non-robust z assumes evenly sized returns, which these tapes are not.
- Even on clean data, the variance ratio at q = 2 over 32 returns has a standard deviation of about 0.18,
  so it resolves little.
- The efficiency ratio asks the same question (trend or chop) and passed its positive control on both prices.

**Revisit only if** the G3 gallery shows the efficiency ratio cannot separate pauses from chop.

## A1.2 The midpoint is the primary bucket price

The midpoint is used for `er` and for own noise (`σ_h` in `cost_noise_h`). VWAP understates variance by
about a third, which would overstate `cost_noise` by about 1.2×.

- VWAP `er` is carried as a check column, `er_vwap_k`. It is never a condition.
- Moments without quotes use VWAP, flagged `price_basis = vwap_fallback`. That is 31 development-slice
  events (row 7).

## A1.3 The efficiency-ratio noise reference: simulated through the pipeline, drawn as a band

The closed-form `er_0` passed against resampled bucket returns (1.008 midpoint, 1.005 VWAP). It did not
match the whole pipeline. So the suite **draws the simulated noise instead of dividing by a formula.** This
is the standing rule: reference lines come from simulated noise.

**The condition is on raw `er`** (0 to 1, unitless): filter if `er` < x, at a chosen rung or at every valid
rung. `er_rel_k` and `er_0_k` stay as columns but are not conditions.

**The null — the S1 construction, applied at print level:**

- Per window, resample the window's own **demeaned** print-level returns **with replacement**.
- For the midpoint, resample the demeaned midpoint changes at quote-update level.
- Keep the prints' and updates' own times and sizes.
- Re-integrate from the window's first price, then bucket and compute `er` exactly as on real data.

**Where it is built:** per cell of t's segment × rung × price tier at τ (< $1 · $1–3 · $3–10 · ≥ $10; the
tick size changes at $1). It uses a seeded sample of development-slice windows: up to 2,000 windows per
cell, 20 draws each. It reads only pre-t returns, so no outcome is touched.

**Output:** the null's median and its 5–95% band for each cell. Cells with fewer than 20 windows are shown
and labelled.

**In the suite:** panel B draws the band for the cell in view beside the real `er` distribution. The noise
line on the `er` slider is that cell's null median.

**G2 rule, revised:** replace both the `er_rel` and the `vz2` clauses with: `er` inside its cell's null
5–95% band at every valid rung 1–4. The other two G2 clauses stay. It is a gallery finder, not a threshold.

## A1.4 Controls, re-specified — re-run T5 on the 53 quarantined events with τ

| control | construction | pass |
|---|---|---|
| **Negative** | the A1.3 null on the 53 events, per cell | **reported, no band.** It is the reference, not a test |
| **Positive — trend** | the A1.3 null paths with an injected net drift of d ∈ {1, 2, 4} own-noise units | median `er` at d = 4 above the cell's null 95th value, at every rung with at least 20 windows. Midpoint and VWAP |
| **Null-parameter sweep** | buckets per window {16, 32, 64} | medians of `er` and `cost_noise_h` per setting; any that move more than 20% are labelled bucket-dependent |
| **Blindness** | prices × 10 and × 0.1; separately, sub-$1 prices rounded to the $0.01 grid | every bp and unitless measure `isclose(rtol = atol = 1e-9)`; rounding change reported per event |
| **Price-basis agreement** | `er` on the midpoint against VWAP, real windows | Spearman per rung and segment, reported |
| **Causality, segment** | as §6 | must raise. Re-run, since the code changed |

The AR(1) positive control is retired with the variance ratio. It passed on both prices before retirement:
+2.44 / −2.29 on the midpoint and +2.49 / −2.35 on VWAP.

## A1.5 Escalation, revised

| row | criterion | tier |
|---|---|---|
| 1, 2, 8, 9, 10 | unchanged: causality, segment, A12 or hindsight in conditions, a non-development row embedded, runtime | HARD STOP |
| **3a** | a **presence or cost** measure fails blindness | HARD STOP |
| **3b** | a **scale-free** measure fails its positive or blindness control | **LOG.** The measure is removed from the suite's conditions, kept as a column, and the failure is shown in the suite header. **The build continues** |
| 4–7 | unchanged | LOG |

**No other stop before T9.** If no HARD STOP row fires, the run goes from the T5 re-run straight to the
suite.

## A1.6 Accepted as done, no action

- Quote sizes are shares in 2020–22, so depth is built. Row 4 is clear.
- VWAPs are computed relative to the window's first print. Blindness uses `isclose(rtol = atol = 1e-9)`.
- D40 and D41 are committed; next free is D42.
- 7,525 of 7,620 development-slice events have τ. The controls run on the 53 of 56 quarantined events that
  have τ.
- One quarantined event's 15-minute forward return was printed in a smoke test. Quarantined events are never
  embedded, and no development-slice outcome was read. It is recorded and needs no action.

## A1.7 Text changes to the brief, for the record

- §4c: drop the variance-ratio row. The references paragraph is replaced by A1.3.
- §5: G2 rule per A1.3.
- §6: the table is replaced by A1.4. The primary-price ruling table is replaced by A1.2.
- §7b: the scale-free group becomes `er` < x, at a chosen rung or at every valid rung.
- §7c panel B: reference lines are the `er` null band per cell, `cost_noise_h` = 1, and the flat Phase 11
  stack on the spread panels.
- §11: row 3 per A1.5.
- REPORT.md adds: the A1.0 cause list; the null bands per cell; the measures removed under 3b, if any.
