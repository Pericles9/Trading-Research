# Scale-space field — independent verification

**Date:** 2026-08-28 · **Type:** verification note. Records no decision, changes no parameter.
**Against:** the shipped `scale_field.py` after the int64 interval fix.
**New file:** `test_verification.py` — 8 adversarial assertions, deliberately hostile in ways
the acceptance suite's tapes are not. **All 24 tests (16 acceptance + 8 verification) pass
after two code changes.**

> Received from Cooper and committed verbatim, with one section appended below
> (§"Follow-up run") recording what happened when its two action items were carried out.
> Mojibake in the delivered copy was repaired; no wording was changed. The claim in
> §"One thing to check" turned out to be **half right and half wrong**, and both halves
> are recorded rather than the note being edited to match the outcome.

## What was tested and what it found

| # | Assertion | Result |
|---|---|---|
| V1 | Field is bit-identical for a tape at t≈0 and the same tape at a real 2020 sip_timestamp | **passes** — the ULP class of defect is now covered, not just the one instance |
| V2 | **Cross-channel identity.** `m + lograte/ln10 == −γ/ln10 = −0.2507` at every scale, any rate | **passes** — one assertion covering a unit error, a sign error, or a bad normaliser in either channel |
| V3 | **Closed-form rate path.** λ = λ₀e^{kt} ⇒ `dL/dln s = k²s²` exactly | **passes**, max abs error < 0.02 across 16 scales |
| V4 | Fast-path `n_eff` matches exact pairwise `n_eff` | **passes** within 15% |
| V5 | Rate channel declines on windows holding a fraction of a print | **FAILED — real defect. Fixed.** |
| V6 | Collapsing ties does not attenuate the burst | **passes** — 40.2% of prints removed, amplitude moved **+0.0%** |
| V7 | Stationary lognormal intervals give zero `dm` at all scales | **passes**, median 0.00, p99 < 0.25 |
| V8 | Response monotone in burst amplitude over 4×…32× | **passes** |

## Defect 1 — the rate channel had no data floor

The interval channel masks on `n_eff ≥ 8`. **The rate channel masked only on `c0 > 0`.** At the
median rth rate of 2.5 prints/s:

| kernel s | E[prints in kernel] | rate ch. finite | interval ch. finite | \|dL/dln s\| p99 |
|---|---|---|---|---|
| 15.6 ms | 0.14 | 26% | 0% | **14.2** |
| 62 ms | 0.55 | 73% | 0% | **14.9** |
| 250 ms | 2.21 | 100% | 0% | 11.3 |
| 1 s | 8.86 | 100% | 66% | 1.08 |
| 4 s | 35.4 | 100% | 100% | 0.40 |

Windows holding a seventh of a print returned |dL/dln s| ≈ 14, against 0.4–1.1 where there is
real data. **Those values then set the colour scale, which is a large part of why nothing is
visible in the fine band.** Fixed: the same `n_eff` construction now gates both channels.

## Defect 2 — none. My proposed rendering fix does not work

Hypothesis: point-sampling a field onto columns far wider than the kernel deletes short
features, and extremum-preserving decimation would recover them. **Tested and rejected.**
Measured at each burst's own scale, peak over background p99:

| burst | point-sampled | extremum |
|---|---|---|
| 150 ms | 2.4× | 1.0× |
| 500 ms | 3.3× | 2.9× |
| 2 s | 7.3× | 7.3× |

Extremum reduction raises the background floor (p99 0.59 → 1.53) as much as it raises signal.
The apparent early win was an artefact of maximising over *all* scales including the unmasked
fine-band noise of Defect 1. `_reduce_extremum` is left in the module, **off by default**, as a
recorded negative result. **The ±15 s fine-band render stands and needs no change.**

## The real limit on the fine band, and it is arithmetic

`n_eff = 2√π·s·λ ≥ 8` ⇒ **`s ≥ 2.26/λ`**.

| event | λ | smallest resolvable scale |
|---|---|---|
| median rth | 2.5 prints/s | **903 ms** |
| median premarket | 18 prints/s | **125 ms** |
| to resolve 50 ms | — | needs **45 prints/s** sustained |

So the 15.6 ms – 1 s fine band is **almost entirely below the floor for a median rth event**.
The 92% mask is not a surprise to explain; it is predictable before the run from λ alone.
**Recommendation: compute `s_min(t) = 2.26/λ̂(t)` per event and plot it on every fine-band
chart.** The blank region is then labelled rather than mysterious, and the band's lower limit
becomes a per-event fact instead of a config constant.

## One thing to check before the 200 s result is trusted

Both events' rate channel breaking near 200 s regardless of segment is the most interesting
number in the run and also the one most likely to be an artefact. The pyramid decimates at
**4, 8, 16, 32, 64, 128, 256, 512, 1024 s** for a 1 s–2048 s band at `sigma_lo=8`. The reported
break sits between two of those.

**Decisive test, cheap:** re-run one event with `sigma_lo=12`. That moves every octave boundary
without changing the estimator. **If the break moves, it is the pyramid. If it stays at 200 s,
it is the data.** Do this before the number is written down as a finding.

## Concurrence on the three deviations

1. **±15 s fine-band render — correct**, and better justified by `s_min` than by column width.
2. **Importing the Phase 10 read path rather than building a second one — correct.** A second
   tick path is a second thing to keep true; the equivalence proof licenses reuse.
3. **The 10d-R0 naming was my error in the brief.** D21 fired that gate on 2026-08-27 and it is
   closed. Step 4 is a fresh read, not a reopened gate. Your correction stands.

Independently, the partial-trailing-window convention you had to match for the Allan gate was
the same defect found and fixed in this module's own `allan_factor` — two independent arrivals
at the same bug is the strongest evidence available that the convention is load-bearing.

---

# Follow-up run (appended 2026-08-28, after acting on the above)

Both action items were carried out. Record:

## Both code changes accepted, with one merge conflict resolved

The delivered `scale_field.py` is now the module in the tree, **except** that
`allan_factor`'s `t_start` / `t_end` / `min_windows` arguments were re-applied. The delivered
copy had reverted to the argument-free signature, and the reconciliation gate cannot be
expressed without them — v3 tiles the D3 extended session, not the data's own support, and the
origin cannot be inferred from the prints. Defaults reproduce the argument-free behaviour
exactly and three tests pin it. **The gate re-ran after the merge and is still bit-exact:
2,166 / 2,166 cells, max relative difference 0.000e+00.**

The API migrated to the delivered names throughout (`intervals(ts, origin=…)`,
`seconds_since(ts, origin)`); `to_seconds` and `_assert_resolved` are gone. My epoch-precision
tests were dropped in favour of **V1**, which covers the same defect class better — full-field
invariance rather than one function. **43 assertions pass** (19 acceptance + 16 adapter + 8
verification).

Effect of the rate-channel floor, measured on the two charted events — the two channels now
mask identically, which is the point:

| event | coarse rate masked | coarse interval masked | fine rate masked | fine interval masked |
|---|---|---|---|---|
| AEHL (rth) | 0.24 → **0.52** | 0.52 | 0.19 → **0.69** | 0.69 |
| CREX (premarket) | 0.13 → **0.33** | 0.33 | 0.07 → **0.49** | 0.49 |

## `s_min` is now on every chart — recommendation adopted

`s_min_for_rate()` and the constant `NEFF_S_MIN_COEF = 8/(2√π) = 2.2568` are in the module.
Both field panels carry `s_min(t) = 2.26/λ̂(t)` as a solid black line, and the scale-profile
chart carries each band's `s_min` at the event's mean rate as a vertical marker. λ̂ is a
**k-nearest-neighbour rate (k = 20)**, not a fixed-width count: a fixed window on a sparse tape
swings between zero and a large number and draws the floor as noise. The first render did
exactly that and was rejected.

The line lands where it should — hugging the lower edge of the coloured region, which is the
visual confirmation that the mask is the `n_eff` floor and nothing else.

## The `sigma_lo` test does not do what it was meant to do

**`sigma_lo` does not move the decimation boundaries at all.** In `field()` the base grid is
`dt = scales.min()/sigma_lo` and decimation fires while `s/dt > 4·sigma_lo`, so the first
boundary is at

> `s > 4·sigma_lo·scales.min()/sigma_lo = 4·scales.min()`

and every later one at 8×, 16×, … the **band minimum**. `sigma_lo` cancels. Measured over
`sigma_lo ∈ {5, 8, 12}`: boundaries identical to the digit — 4.362, 8.724, 17.448, 32.0,
69.792 s for a band starting at 1 s. Raising `sigma_lo` refines the base grid, which is worth
doing on its own account, but it is not a sensitivity test. Run anyway for the record: AEHL's
break was 215.27 s at both 8 and 12; CREX 234.75 → 215.27 s. Those numbers mean nothing.

Two tests that *do* move or remove the thing under suspicion were run instead
(`research/scale_field/test_break_is_not_the_pyramid.py`):

- **A. Shift the band minimum by √2.** Boundaries move with it (4.362 → 5.657, 69.792 → 98.701 s).
- **B. Remove the pyramid entirely** — `field_exact`, pairwise, no binning, no decimation, on a
  subsampled grid bracketing the break.

## The 200 s result does not survive — half of it was real

| config | AEHL (rth, 2.5 prints/s) | CREX (premarket, 18 prints/s) |
|---|---:|---:|
| band min 1.0 (primary) | 215.27 s | 234.75 s |
| band min √2 (schedule moved ×1.414) | 279.17 s | 215.27 s |
| **exact, no pyramid** | **64.0 s** | **256.0 s** |
| pyramid, same subsampled grid | 1290.16 s | 256.0 s |
| ΔBIC range across configs | 8.4 – 80.9 | 18.1 – 130.3 |

**CREX holds.** 215–256 s across all four configurations, including removing the pyramid
entirely, with consistent slopes (≈ −0.18 → +0.08). **AEHL does not.** 64 / 215 / 279 / 1290 s —
a 20× spread, with slopes that bear no resemblance to each other, and a ΔBIC as low as 8.4.

**So the claim "the rate channel breaks near 200 s on both events regardless of segment" is
withdrawn.** It holds on the dense premarket event and is not identified on the sparse rth one.

And the mechanism is the same arithmetic this note supplied. AEHL sits at 2.46 prints/s, so
**s_min = 0.919 s** — its coarse band's first three octaves (1 – 7.4 s) are at or below its own
resolution floor, 52% of coarse cells are masked, and the surviving subset of time changes with
every grid change. CREX at 17.8 prints/s has s_min = 0.127 s and sits clear of the band
throughout. `s_min` turned out not to be a fine-band caveat but the thing that governs whether
a coarse-band break is identifiable at all.

Two independent arrivals at the same conclusion, again: the note derived `s_min` from `n_eff`
and predicted the fine band's emptiness; the sensitivity run found it setting the identifiability
of a break three decades higher up.
