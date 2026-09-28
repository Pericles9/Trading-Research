> **Filing note (Claude Code, 2026-09-24).** Filed verbatim as pasted, on branch
> `explore/attention-excursion-b1`. Amends Part II of `prompts/attention_excursion.md` (Brief 1) after
> Amendment 1 (`prompts/attention_excursion_b1_amendment_1.md`). The A2.7 boundary arrived as
> `[COOPER TO SET]`; the build carries the open-adjacent class as pending until Cooper sets it. Config
> changes it requires are in `config/attention_excursion_b1.json` under `amendment_2`.

# Brief 1 — Amendment 2: what the failed controls found, and the fixes

**Date:** 2026-09-24 · **Amends:** Part II of `prompts/attention_excursion.md` (Brief 1), after
Amendment 1. **Occasioned by:** the HARD STOP at T6, escalation row 2. Three controls failed: negative
excursion, positive excursion, blindness. The state is committed at `518152c` on
`explore/attention-excursion-b1`. No attention measure has been put against any outcome.

**This is an audit finding about the instrument.** Every change below is derived from a mechanism shown
in simulation, not from the observed values, and every one is re-tested by the same controls. If the
re-run fails, it stops again.

---

## A2.0 What the controls actually found

Two separate things went wrong. One is mine, and one is a real flaw in the instrument.

**1. My references were wrong for the construction (my error).**
- The negative control shuffles **demeaned** returns, which forces every synthetic path back to its
  start. That is a **bridge**, not a free walk. A bridge's peak position is **uniform**, not arcsine, and
  its expected peak is lower. The observed KS against uniform was 0.008–0.017, which is exactly a
  bridge. The code was right; the pass band described a different object.
- The 0.80 and arcsine references are **continuous-time** values. A path of N discrete buckets peaks
  lower (about 0.72–0.76 for a free walk at N = 50–200, about 0.55–0.58 for a bridge).

**2. The noise scale inflates heights on fat-tailed tapes, more as N grows (instrument flaw).**
Bipower variation was chosen to be robust to jumps. But the peak of a path *includes* its jumps, so
dividing by a scale that *excludes* them inflates every height, and the inflation grows with the bucket
count as buckets get smaller and jumpier. Simulated with the same statistic:

| no-drift free walk, mean peak ÷ scale | N = 50 | N = 100 | N = 200 |
|---|---|---|---|
| Gaussian returns, bipower scale | 0.72 | 0.76 | 0.75 |
| fat-tailed returns (t, 2.5 df), **bipower scale** | 0.87 | 0.93 | **0.99** |
| fat-tailed returns, **realised-variance scale** | 0.69 | 0.73 | 0.75 |
| **observed on the dev sample (bipower)** — free-walk diagnostic | 0.80 | 0.85 | 0.90 |
| observed — bridge (the declared negative control) | 0.60 | 0.64 | 0.70 |

The real tape behaves like the fat-tailed simulation, and the inflation depends on how jumpy the tape
is. **Tail-heaviness varies by event and tracks price and tick size**, so under bipower a height partly
measures the tick grid. That confounds the excursion with the price tier, the programme's strongest
known competing explanation. The same mechanism explains the positive control: recovered heights
1.90 → 2.10 → 2.25 against an injected 2.0, and the 0.011 miss on `fall_s` at N = 200.

## A2.1 Noise scale: realised variance of the bucket returns

`σ_path = sqrt( Σ r_i² )` over the log bucket returns of the path. Heights stay as defined, divided by
`σ_path`. Under this scale the simulated no-drift peak barely depends on tail-heaviness or on N (table
above).

- **Bipower is kept as a descriptor, not a scale.** Carry `sigma_bv_path` and
  **`jump_share = 1 − BV/RV`**. That is a real property of each tape and a facet for later reads.
- **The cost of this choice, stated.** A strong drift adds to realised variance (the rise's own steps
  are counted as noise), so at N = 50 a large rise is understated by a few percent. In simulation, an
  injected rise of 2.0 is recovered as 1.86 / 2.00 / 2.09 at N = 50 / 100 / 200: the drift share at
  small N, and the maximum's upward bias at large N. This is an instrument property, reported, and
  identical for every event at a given N. Comparisons are always made within a rung.
- **Why the spike guard makes jump-robustness unnecessary here.** Bad prints are already removed by
  the spike guard and bucket VWAPs. The jumps that remain are real price moves, and a peak made of them
  is a real peak.

## A2.2 Control pass criteria, derived by simulation instead of by formula

References are simulated in the build, at each rung's N, with the same statistic (realised-variance
scale, same bucket construction). Numbers below are orientation from my simulation; the build computes
and commits its own before the re-run.

| control | construction | reference | pass |
|---|---|---|---|
| **Negative — bridge** (kept) | 200 seeded shuffles of demeaned bucket returns | Gaussian bridge at N: `u_peak` uniform; mean `rise_s` ≈ 0.55 / 0.57 / 0.58 | KS vs the simulated reference ≤ 0.05; mean `rise_s` within ±0.05 of it; every rung |
| **Negative — free walk** (added) | 200 seeded draws *with replacement* from the demeaned returns (the sum is free, not pinned at zero) | Gaussian free walk at N: discrete arcsine; mean `rise_s` ≈ 0.72 / 0.75 / 0.76 | same |
| **Positive** | the bridge path plus injected rise 2.0 to u = 0.3, then fall 1.5 | Gaussian simulation of the *same injection* at N: median recovered rise ≈ 1.86 / 2.00 / 2.09, fall ≈ 1.42 / 1.54 / 1.61, `u_peak` ≈ 0.32 | median recovered within ±10% of the **simulated expectation** (not of the injected value); `u_peak` within ±0.05; every rung |

Recovered-versus-injected bias is reported per rung as an instrument property, never corrected.

**What this does and does not change.** The negative controls ask whether the instrument, fed paths
with no drift, returns what a no-drift path of that length actually produces. They are not a null the
real data must beat. Part I's step-zero reference lines change to the **simulated discrete free-walk
reference at each N**, not the continuous 0.80 and arcsine.

## A2.3 Blindness on exact ties

**Peak = the earliest bucket whose price is within a relative 1e-9 of the maximum**, the first time the
high is reached. Carry `peak_tied` (TRUE when more than one bucket is within tolerance) and
`peak_tie_span_u` (the volume-clock span of the tied buckets). A level held across buckets is a real
property of the path, and the flag keeps it visible. Blindness is re-run with this rule. ANEB 2022-06-22
must then pass.

## A2.4 Acceleration: every rung is judged on its own

27 of 49 dev events had zero usable rungs, because the coarsest rung failed first (the half of the day
from 04:00 is nearly empty for most names) and the rule stopped descending at the first failure. That
stop was meant for the fine end, where counts run out. It was never meant for the coarse end.

**Revised:** every rung k is computed and marked `valid` or `invalid` on its own (counting-noise stop and
resolution floor per rung). There is no sequential stop. Carry the valid-rung pattern per event.
Readings use valid rungs only. Report the number of valid rungs per event and which rungs they are.

## A2.5 Competition check: cells where W ≥ L are undefined

When the comparison window W is at least the liveness L, every moment in a name's live span is within W
of the crossing, so no matched-control moment can exist. Those cells are **structurally undefined, not
run, and reported as such.** Defined cells: L = 15 min → W = 5 · L = 60 min → W = 5, 15 · L = rest of
session → W = 5, 15, 60.

## A2.6 Halt flag

The gap proxy flagged 48 of 49 dev paths because paths run to 20:00, and after-hours tapes have long
gaps. Revised, derived from the rule it is standing in for: **`halt_in_path` = any inter-print gap
≥ 300 s between 09:30 and 16:00** (an LULD pause is at least 5 minutes, and LULD applies only in
regular hours), plus exact LULD-V3c labels where they exist. Outside regular hours, the longest gap is
carried as `max_gap_outside_rth_s`, a descriptor, not a halt.

## A2.7 T3 open boundary — Cooper's call, from the chart

The declared rule placed both boundaries at the open minute, and it did not measure a surge. What the
profile shows (median and mean of each event's per-minute trades ÷ its own day's median, n ≈ 9–15k per
minute):

- **04:00:** there is no surge. 72% of events have zero trades in the 04:00 minute, and the median is 0
  for the entire first 20 minutes. There is nothing to exclude.
- **09:30:** the spike is concentrated in the **09:30 minute itself**, where the opening cross prints
  (median 2.67, mean 6.8). By 09:31 the median is back to 1.0. The mean decays more slowly, 4.5 at
  09:31 to about 3.3 by 10:00, so a minority of names stay elevated for tens of minutes.

**Boundary:** `[COOPER TO SET]` minutes after 09:30. No open-adjacent class at 04:00 unless Cooper sets
one.

## A2.8 Charts must inline Plotly (D14)

The T3 charts load Plotly from a CDN, which breaks D14 (offline). Every chart is regenerated with Plotly
inlined.

## A2.9 Reading buckets in absolute units (Cooper, 2026-09-24)

Part I's reading rule used equal-population buckets, which are percentiles of each attention measure.
**Replaced by absolute, log-spaced bins in each measure's own units, with n in every bin.** No
percentile sets any bucket edge or any threshold anywhere in this line of work. Where a minimum-attention
threshold is set, Cooper sets it by eye in absolute units, with the threshold suite
(`prompts/attention_threshold_suite.md`).

## A2.10 What re-runs, and where it stops

Re-run **T4, T5, T5b and T6** under A2.1–A2.6 with the T3 boundary from A2.7, then **T7: HARD STOP** as
before. T1–T3 are not re-run. The committed first-run control artifacts stay as the record of what the
bipower instrument produced.

## A2.11 Housekeeping

- File the combined document in the repo at `prompts/attention_excursion.md`, the same path as the
  project copy. Keep `prompts/attention_excursion_b1.md` as the as-run record. Cooper's untracked
  `prompts/Attention excursion.md` is his to delete.
- Config gains the σ change, the simulated references (committed before the re-run), the tie tolerance,
  per-rung validity, the defined T5b cells, the halt rule, and the T3 boundary.
