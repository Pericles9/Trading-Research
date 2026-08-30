# Scale-space field on the momentum cohort — build report

**Spec:** `prompts/scale_field_brief.md` · **Config:** `config/scale_field.json`
**Status:** stopped at order-of-work step 3, as instructed. **Step 4 is Cooper's.**
**Date:** 2026-08-28 · **Branch:** cut from `phase/10d-diag1`
**Revised 2026-08-28** after independent verification (`VERIFICATION.md`). One defect
fixed in the estimator (the rate channel had no data floor) and **one headline number
withdrawn** — see §4. The reconciliation gate re-ran after both and is unchanged.
**Revised again 2026-08-28** after Cooper's step-4 read. The knee comparison is
**withdrawn as an acceptance criterion** (§8), and steps 1–2 of Cooper's recommended
order are run and reported (§9).
**CLOSED 2026-08-28 — D22.** The scale-space field closes as a detector; the resolution
floor survives and is the deliverable. §14 is the close-out. Tasks 2–5 not run.
**Revised a fifth time 2026-08-28** — work-order Task 1 run and reported in §13. It was
specified as the task that decides the rest, and it came back negative on the operational
claim, so Tasks 2–5 are not started.
**Revised a fourth time 2026-08-28** after Cooper's read on the corrected steps 1–2:
§11 is the operating envelope and the challenge it puts to this build's own premise,
§12 promotes the 49/100 to a finding, and §10.4 is downgraded.
**Revised a third time 2026-08-28** after Cooper's read on steps 1–2. Three checks were
raised against §9 and **two of them found errors in numbers published here** — §10 has
the corrections, which are applied in place in §9 as well. §10 also carries the
restatement test and the re-cut admissibility. Nothing is appended to the decision
register.

This is not a phase and does not carry a phase's escalation table. The brief carries one
gate (the Allan reconciliation) and one stopping point (chart it and stop). Both are
discharged below.

---

## 1. What was built

| File | What it is |
|---|---|
| `research/scale_field/scale_field.py` | The estimator, plus the changes recorded in §5. |
| `research/scale_field/test_scale_field.py` | The specification. 19 assertions (16 delivered + 3 pinning the Allan window). |
| `research/scale_field/adapter.py` | **The handoff.** Event id → sorted int64-ns tape. Frozen-cohort loader with the hash asserted. |
| `research/scale_field/test_adapter.py` | 16 assertions against real event folders. |
| `research/scale_field/test_verification.py` | 8 adversarial assertions from independent verification. Found a real defect (§5.2). |
| `research/scale_field/test_break_is_not_the_pyramid.py` | Is the dispersion break in the data or in the pyramid? §4. |
| `research/scale_field/reconcile_allan.py` | The gate. Exit 2 on divergence. |
| `research/scale_field/run_field_one_event.py` | One event, both bands, both channels. |
| `research/scale_field/plot_scale_field.py` | Three charts, extending the Diag1 grammar. |
| `research/scale_field/make_digest.py` | `results/scale_field/digest.json`, regenerated from artifacts. |

**43 assertions pass.** `.venv/Scripts/python.exe -m pytest research/scale_field -q`

The adapter does **not** implement a read path. The targeted per-event reader and the D3
session clock already exist in `research/phase_10/common.py`, are committed, and were
proven equivalent to `filtered_trades_dev_v4` row-for-row on all 56 dev v4 events at Phase
10 T0d. They are imported unchanged. Reimplementing them would have created a second read
path to keep in sync and voided that equivalence proof. Zero passes over `filtered_trades`
or `filtered_quotes`; the pass budget is intact.

---

## 2. The gate: Allan reconciliation against v3 — **PASSED**

`results/scale_field/artifacts/reconcile_allan.json`
Reproduce: `.venv/Scripts/python.exe research/scale_field/reconcile_allan.py`

| Quantity | Value |
|---|---|
| Target | `results/phase_10/artifacts/v3_t1_gate_curves.parquet`, observable `print_rate` |
| Cohort | 114 events, 100 pooled; content hash `e1a0ac73a79aa573` asserted |
| Cells compared | **2,166** (114 events × 19 eligible rungs) |
| Cells reproduced | **2,166** |
| Cells diverged | **0** |
| **Max relative difference** | **0.000e+00** (tolerance 1e-12) |
| Rungs v3 kept and this path dropped | 0 |
| Rungs this path kept and v3 dropped | 0 |
| Window-count mismatches | 0 |
| Rungs declined by **both** | 114 — the 2¹³ = 8,192 s rung, 7 windows against a floor of 8 |

Bit-exact, not merely close. The bar was exact float reproduction because both paths run
the same arithmetic on the same integers; the tolerance exists only to absorb association
order and was never needed.

Four things had to be matched explicitly or the comparison would have been meaningless,
and each was a way to get a plausible wrong answer:

- **Window origin.** v3 tiles the D3 extended session `[04:00 ET, post_end)`, not the
  data's own support, so empty stretches are real zeros. This is why `allan_factor` gained
  `t_start`/`t_end` (§5) — the origin cannot be inferred from the prints.
- **Raw prints, ties intact.** v3's gate does not collapse ties; collapsing is the interval
  channel's variant and would change every count.
- **The partial trailing window is dropped, never clipped into.**
- **`min_windows = 8`**, v3's `min_windows_for_a_rung`. A rung below it is dropped, not
  returned small.

---

## 3. Step 3: one event, both bands, both channels

The brief says one event. **Two were run**, and the reason is a finding rather than a
preference. The first, chosen as the median rth event, produced an interval channel that
was **92% masked** over the brief's ±15 min window — at 2.46 prints/s, `n_eff` never
reaches 8 below 0.919 s (§4.1). The floor did exactly its job and must not be relaxed, but
a band that is 92% blank has not exercised the fine channel. Premarket events carry ~7× the print count (segment medians:
121,716 vs 17,425), so the median premarket event was added. Segments are not poolable
(v3: 0.903 decades of separation), and v3's knees differ by segment, so one of each also
lets the prediction be checked at both predicted locations.

| Event | Segment | T=0 prints | Ties | Min gap | v3 knee prediction |
|---|---|---:|---:|---:|---:|
| `AEHL_2021-02-19_37.50` | rth | 17,365 | 0 | 98 ns | 128 s |
| `CREX_2022-02-01_41.48` | premarket | 119,149 | 0 | 64 ns | 16 s |

Both are pooled analysis-cohort events carrying no flag (row cap, dup prints, ETH-dominant,
1c repair all False), so nothing in either picture is a known artifact. AEHL is already in
the Diag1 animation set, so its tape has been read before under the previous grammar.

### Band geometry, and both ends are bounded

| Band | Scales | Coverage | Grid | Masked (rate / interval) |
|---|---|---|---|---|
| coarse | 1–2,048 s, 89 scales, 8/octave | whole T=0 session | 63.1 s/col (AEHL), 43.3 (CREX) | AEHL 52% / 52% · CREX 33% / 33% |
| fine | 15.6 ms–1 s, 49 scales, 8/octave | ±15 s at the D7 anchor, read with ±15 min of context | 20 ms/col | AEHL 69% / 69% · CREX 49% / 49% |

The two channels now mask **identically**, which is the visible consequence of §5.2: before that fix the rate column read 24% / 13% / 19% / 7% and the difference was the rate channel returning numbers from windows holding a fraction of a print.

- **Coarse cap.** `session_span / 8`. The extended session is 57,600 s → 7,200 s; an RTH
  session is 23,400 s → 2,925 s. The 2,048 s ceiling is under both. Stated, not implicit.
  Note the two caps differ and the brief's low-power warning uses the RTH one: v3's
  headline rung at 4,096 s is **under** the extended cap but **over** the RTH cap, which is
  why its pair count (13) is quoted beside it on chart 03.
- **Fine floor, configured.** 2⁻²⁰ s = 0.954 µs, ~12× the median timestamp resolution.
  This run stops at 2⁻⁶ s, far above it.
- **Fine floor, actual.** `s ≥ 2.26/λ` (§4.1) — 0.919 s for AEHL, 0.127 s for CREX. This is
  the binding one and it is per-event, not a config constant. It is drawn on both field
  panels as a solid black line. Below `n_eff ≥ 8` the field is NaN and was given no
  fallback; blank regions are the result, not a rendering gap.

### Charts

`results/scale_field/charts/{event_id}/`, light and dark, `--plotlyjs directory`, never a
CDN (D14). Palette imported from `plot_boundary_through_time.py` so there is one palette in
the repo rather than two that drift.

| File | What it shows |
|---|---|
| `01_field_coarse` | price · rate channel · interval channel · local print rate, on one ET time axis |
| `02_field_fine` | the same four panels over ±15 s at the anchor |
| `03_scale_profile` | v3's Allan curve · both channels' median vs scale · **dispersion vs scale** · n defined |

Row 4 of chart 03 exists because **A(T) is a variance statistic and rows 2–3 are medians.**
A change of character can live entirely in the spread while the median stays flat, and on
this data it largely does — comparing the knee against a median alone would have been the
wrong comparison and would have produced a false negative.

Two reading rules are printed on the figures rather than left in a footnote:

- **The sign convention is opposite between the channels.** `dlograte < 0` and `dm > 0`
  both mean burst-like. The rate panel's ramp is reversed so warm reads as burst-like on
  both, while every colourbar tick still carries the true signed value. Nothing is negated
  in the data. (Acceptance test 3 exists because getting this wrong is easy and invisible.)
- **The `n_eff` mask changes which time is being averaged.** At fine scales only the denser
  stretches clear the floor, so each scale's median is over a different subset of time. Row
  5 is how much time that is; a trend across scale is partly a trend in which time survives.

Colour is mapped through `asinh`, unclipped, with ticks in original units — `dlograte` is
bounded below by −1 and runs to +15, so a linear symmetric ramp would have rendered the
field as one flat colour and a handful of bright cells.

---

## 4. What the charts show — description only, the call is Cooper's

The brief poses one question: v3's knees are a prediction for the continuous field, and the
scale axis should show a change of character near them. Fitting v3's own `broken_stick`
(imported from `research/phase_10/v3_t1_gate.py`, not reimplemented) to this event's Allan
curve and to the field's coarse-band dispersion:

| Event | Segment | v3 committed knee | This event's Allan knee | Rate-channel IQR knee | Interval-channel IQR knee |
|---|---|---:|---:|---:|---:|
| AEHL | rth | 128 s | **128.0 s** (ΔBIC 38.5) | 215.3 s — **not identified**, see below | 16.0 s |
| CREX | premarket | 16 s | **16.0 s** (ΔBIC 43.5) | 234.8 s — **robust**, see below | 3.1 s |

`results/scale_field/artifacts/knee_comparison.json`

**The discrete side reproduces per event.** Each event's own Allan knee lands exactly on
its segment's committed knee, out of 19 ladder rungs, on both events and both segments.

### 4.1 A withdrawn claim

The first version of this report said *"the rate channel's dispersion breaks near 200 s on
both events regardless of segment."* **That claim is withdrawn.** It did not survive the
sensitivity test the verification note asked for, and it was also computed before the
rate-channel defect in §5.2 was fixed.

`research/scale_field/test_break_is_not_the_pyramid.py` ·
`results/scale_field/artifacts/break_pyramid_sensitivity.json`

| Configuration | AEHL (rth, 2.46 prints/s) | CREX (premarket, 17.8 prints/s) |
|---|---:|---:|
| band min 1.0 s (primary) | 215.3 s | 234.8 s |
| band min √2 (decimation schedule moved ×1.414) | 279.2 s | 215.3 s |
| **exact — pyramid removed entirely** | **64.0 s** | **256.0 s** |
| pyramid, same subsampled grid | 1290.2 s | 256.0 s |
| ΔBIC range across configurations | 8.4 – 80.9 | 18.1 – 130.3 |

**CREX holds.** 215–256 s across all four configurations including `field_exact`, which has
no binning, no decimation and no interpolation, with consistent slopes (≈ −0.18 → +0.08).

**AEHL does not.** 64 / 215 / 279 / 1290 s — a 20× spread, slopes bearing no resemblance to
each other, and a ΔBIC as low as 8.4. Its break location is not identified.

**The mechanism is the resolution floor**, and it is arithmetic:

> `n_eff = 2√π·s·λ ≥ 8`  ⟹  **`s ≥ 2.26/λ`**

| event | λ near the anchor (±15 min) | s_min there | λ session-mean | **s_min session-mean** | masked share, coarse |
|---|---:|---:|---:|---:|---:|
| AEHL | 2.46 prints/s | 0.919 s | 0.30 prints/s | **7.48 s** — coarse band starts *below its own floor* | 52% |
| CREX | 18.2 prints/s | 0.124 s | 2.07 prints/s | **1.09 s** — coarse band starts at it | 33% |

*(Corrected 2026-08-28. The first version of this table quoted the **near-anchor** λ and
then reasoned from it about the **coarse** band, which is session-wide. The two differ by
an order of magnitude because the near-anchor window excludes the dead hours. The
session-mean column is the one the coarse-band claim rests on, and it is the more
adverse of the two — AEHL's coarse band begins three octaves below its own floor, not at
it.)*

AEHL's coarse band spends its first three octaves below its own floor, so the subset of
time that survives the mask changes with every grid choice, and the fitted break moves
with it. This was expected to be a fine-band caveat; it turns out to govern whether a
**coarse**-band break is identifiable at all. `s_min(t) = 2.26/λ̂(t)` is now drawn on every
field panel (λ̂ by k-nearest-neighbour spacing, k = 20) and each band's mean-rate `s_min` is
marked on the scale-profile chart.

### 4.2 What stands

So on n = 2 the prediction is **partly met, and less than the first version claimed**: the
Allan statistic reproduces per event; the continuous field shows a robust break on the one
event dense enough to identify one, at ~215–256 s, which is **not** that event's segment
knee (16 s). Four caveats:

1. **n = 2 events**, one of which cannot identify a break. v3's knees were fit on the median
   curve across a whole segment (70 rth, 28 premarket), not per event.
2. **No matched null exists yet.** The 10–90 bands on chart 03 are dispersion across time,
   not confidence intervals. Nothing here is tested against anything.
3. **The ΔBIC values on the field rows are not comparable to the Allan row's.** The 89 scale
   points are quadrature on a smooth continuum and are strongly dependent; the 19 Allan
   rungs are far closer to independent. The field's ΔBIC is inflated by construction and is
   reported as a fitted break location, not a significance test.
4. **The bands cover different time windows** (coarse = whole session, fine = ±15 s at the
   anchor) and are never joined into one curve on any chart.

No threshold was applied and none is available. The Poisson constant stays a unit-test
fixture: v3 measured A rising to 1,245, so a z-score against Poisson would be inflated by
roughly √A(T) — ~2.4× at milliseconds, ~35× at the hour scale.

## 5. Deviations, recorded rather than silently taken

### 5.1 `intervals()` lost nanosecond gaps on real data — a defect, fixed

The delivered `intervals()` computed `ts/1e9` and differenced in float64. Every tape in the
acceptance suite starts near t = 0, so nothing exercised float64 precision at epoch
magnitude. Real prints do.

Measured on `ALXO_2020-08-05_31.58` (the adapter's known event): epoch nanoseconds as
float64 **seconds** have a **238 ns ULP**, against an archive median timestamp resolution of
80.5 ns and a minimum of 49 ns. **4 of 899** strictly-increasing unique timestamps went
non-positive under the naive conversion, and the worst gap error was **447 ns against a
954 ns scale floor** — the entire fine band would have been quantisation noise wearing a
plausible shape. Rebasing to an int64 origin before the float conversion drops the worst
error to **0.004 ns**.

Fixed by differencing in int64 before any float conversion and requiring an explicit
origin: `intervals(ts, origin=…)` and `seconds_since(ts, origin)`, the latter positional so
it cannot be forgotten. The guard function I first added (`_assert_resolved`) is **gone**,
superseded by the delivered API — which is safe by construction — and by V1 in
`test_verification.py`, which asserts the whole field is bit-identical for a tape at t≈0 and
the same tape at a real 2020 `sip_timestamp`. That covers the defect *class*, not the one
instance, which is the better test.

### 5.2 The rate channel had no data floor — a defect found by independent verification

`VERIFICATION.md` V5. The interval channel masked on `n_eff ≥ 8`; **the rate channel masked
only on `c0 > 0`.** At the median rth rate of 2.5 prints/s a 15.6 ms kernel holds 0.14
expected prints and still returned `|dL/dln s| ≈ 14`, against 0.4–1.1 where there is real
data — and those values then set the colour scale, which is much of why the first fine-band
render showed nothing. Fixed: the same `n_eff` construction now gates both channels, so they
mask identically (AEHL coarse 0.24 → 0.52, equal to the interval channel's 0.52).

This changed a reported number. The ~200 s break in §4 was first computed on the unfloored
channel; the corrected value and its sensitivity are in §4.1.

### 5.3 A recorded negative result: `_reduce_extremum`, off by default

Hypothesis: point-sampling a field onto columns far wider than the kernel deletes short
features, and extremum-preserving decimation would recover them. **Tested and rejected** —
it raises the background floor as much as the signal (p99 0.59 → 1.53), and the apparent
early win was an artefact of maximising over the unfloored fine-band noise of §5.2. The
function stays in the module, **off**, as the record.

### 5.4 `allan_factor()` gained `t_start` / `t_end` / `min_windows`

The delivered signature tiles `[min(ts), max(ts))`. v3 tiles the D3 extended session. The
origin cannot be inferred from the prints, so reconciling required passing it. Defaults
reproduce the prior behaviour exactly and a test asserts that; a second test asserts that
padding the window with empty time changes the answer, which is why the argument has to
exist rather than be guessed.

### 5.5 The fine band is charted over ±15 s inside a ±15 min read, not over ±15 min

A heatmap column cannot be narrower than its kernel or the panel draws sub-pixel structure
as noise. Over 1,800 s a chart-width grid gives ~1.3 s per column against a 15.6 ms
smallest kernel; the first render duly produced a picket fence. The honest window for a
band reaching 15.6 ms is ~22 s. At ±15 s on a 1,500-point grid the spacing is 20 ms, which
resolves the floor, and the top scale still spans 30 kernel widths. **The ±15 min of tape
is still read**, so the estimator has full context either side and the edge mask never
bites inside the charted window. Compute cost is unchanged — it is set by the pyramid's bin
count over the read window — so the brief's 7 s/event budget holds.

Recorded in `config/scale_field.json` `scale_axis.fine.window_deviation_from_brief` and
carried into every run manifest.

### 5.6 Segment assignment does not use the DuckDB ICU extension

The adapter stub specified `TO_TIMESTAMP(sip_timestamp/1e9) AT TIME ZONE 'America/New_York'`.
That names one implementation of the ET wall clock, and it is not the one this repo uses:
Phase 10 onward reads event folders directly and never opens DuckDB on the tick path,
because the pass budget over `filtered_trades` is zero. The **constraint** the stub protects
— ET wall clock, never a UTC cast — is met exactly by `common.session_window`. Three tests
pin it: segments tile the extended day, an early close shortens the post segment, and the
premarket start is a different UTC hour in winter than in summer.

### 5.7 Two events instead of one

See §3. The first event's fine band was 92% masked and had not exercised the channel.

### 5.8 Naming

`10d-R0` in the brief's step 4 is the name of a gate that has already **fired**
(2026-08-27, D21). The step 4 here is a fresh Cooper read, not that gate reopening. Flagged
so the register is not read as reopened.

---

## 6. Reproduce

```
.venv/Scripts/python.exe -m pytest research/scale_field -q
.venv/Scripts/python.exe research/scale_field/reconcile_allan.py
.venv/Scripts/python.exe research/scale_field/run_field_one_event.py --event AEHL_2021-02-19_37.50
.venv/Scripts/python.exe research/scale_field/run_field_one_event.py --event CREX_2022-02-01_41.48
.venv/Scripts/python.exe research/scale_field/plot_scale_field.py --event AEHL_2021-02-19_37.50
.venv/Scripts/python.exe research/scale_field/plot_scale_field.py --event CREX_2022-02-01_41.48
.venv/Scripts/python.exe research/scale_field/test_break_is_not_the_pyramid.py
.venv/Scripts/python.exe research/scale_field/make_digest.py
```

**Untracked by design**, matching the standing rule for regenerable artifacts:
`results/scale_field/artifacts/*.parquet` (12 MB) and `results/scale_field/charts/*/*.html`
plus the local `plotly.min.js` (53 MB for two events; D14 forbids a CDN so the bundle has to
be local). Every JSON manifest, which carries every n and every provenance field, **is**
tracked.

---

## 7. Stopped here

Step 3 is complete and the brief says stop, and the verification note's two action items
have both been carried out (`VERIFICATION.md`, §"Follow-up run"). **Step 4 is Cooper's
read.** Step 5 —
matched-null thresholds via `research/phase_10b/pipeline.py` (`kernel_intensity`,
`simulate_inhomogeneous`, `quantize`, `allan_curve` are all present and reusable), then the
cohort — is gated on it and has not been started.

No decision number was appended. Nothing here settles anything that belongs in
`docs/Universe-Decisions.md`; next free number remains **D22**.

---

## 8. Cooper's step-4 read — the knee comparison is withdrawn as a criterion

Cooper read the step-3 output on 2026-08-28 and withdrew the brief's own gate. Recorded
here because the report's §4 was written against it.

**The knee reconciliation gated nothing.** Cooper tested both candidate summary statistics
against known injected truth, at fixed intensity contrast (5×) and duty cycle (0.20):

- **Pooled amplitude versus scale does not select scale at all.** Median |dL/dln s| across
  a session pins to the finest grid point for every injected τ over a 25× span. Fitting a
  broken stick to a session-pooled curve is the v3 machinery being re-imported into the
  method that exists to avoid it — which is exactly what §4 of this report did.
- **The local ridge tracks, then degrades:** ratio of recovered to injected τ runs 1.55,
  0.99, 0.59, **0.18** for τ = 2, 8, 32, 128 s, with the IQR widening from 0.86 to 2.25
  decades.
- **The Allan knee has no stable conversion:** τ-to-knee ratios of 8, 12.8 and 5.1 across
  a 25× τ span.

So CREX's 16 s Allan knee against its ~235 s field break is **not a disagreement to
explain** — it is two uncalibrated statistics being compared. §4.2's "the prediction is
partly met" over-claims in the same direction the withdrawn "~200 s on both events" did,
and the right reading is that **no summary statistic in play has been shown to recover a
known timescale at the scales this cohort lives at.**

What survives: the bit-exact Allan reproduction in §2 was a good gate **on the
point-process plumbing**, which is what it actually tests. And the field's *local*
behaviour at an isolated burst is clean and already pinned in the acceptance suite —
3.4 s recovered for a 3 s burst, 38.3 s for 40 s.

Cooper also named three errors as their own: the `allan_factor` regression, the σ_lo test
that cannot discriminate, and the knee criterion itself. All three are recorded in
`VERIFICATION.md` and in the commit history; none required a change here beyond this
section.

---

## 9. Steps 1 and 2 of the recommended order

Cooper's order: (1) `s_min` across the cohort, (2) compare it to the committed sub-burst
durations, (3) recovery grid, (4) matched null, (5) cohort. **Steps 1 and 2 are run and
reported here, as corrected by §10. Step 3 is not started.**

### 9.1 Step 1 — the resolution floor across all 100 events

`research/scale_field/s_min_cohort.py` · `results/scale_field/artifacts/s_min_cohort.json`
Charts: `charts/cohort/04_s_min_cohort_*`, `06_admissibility_by_window_*`

The artifact-only figure — `t0_print_count` from the frozen manifest and the D3
extended-day span, **no field computation and no tick pass**, 0.2 s for all 100 events:

| segment | n | q25 | median `s_min` | q75 |
|---|---:|---:|---:|---:|
| premarket | 28 | 0.455 | **1.07 s** | 4.41 |
| rth | 70 | 3.19 | **7.46 s** | 76.4 |
| pooled | 100 | 1.66 | **5.16 s** | 38.4 |

**But the session is the wrong denominator, and §10.3 is why.** The D3 extended day is
mostly dead time. What a strategy needs to know is whether the band is supported *when it
would be acting*, which under D5 is at and after the D7 anchor:

| window | n events | λ median | `s_min` median | **coarse admissible** | fine |
|---|---:|---:|---:|---:|---:|
| D3 session | 100 | — | 49.3 s | 15 / 100 | 0 / 100 |
| anchor ±15 min | 95 | 1.97 /s | 2.73 s | 24 / 95 | 0 |
| anchor → +15 min | 93 | 2.68 /s | 1.91 s | 35 / 93 | 0 |
| anchor → +60 s | 75 | 4.88 /s | 0.759 s | 44 / 75 | 0 |
| **anchor → +10 s** | 49 | 8.40 /s | **0.357 s** | **43 / 49** | 0 |

Two things must be read together. At the momentum system's own ~10 s holding period,
**43 of 49 events support the coarse band** — the session-wide 15/100 badly understated it.
**And n falls with the window**: only 49 of 100 events carry 25 or more prints in
the 10 s after their own trigger. That drop is a finding, not a filtering convenience.

**The fine band is 0 of n at every window, and at every event's most favourable 5% of its
session.** Reaching 10 ms would need ~145 prints/s sustained at `n_eff = 8`, or ~54/s even
with the floor relaxed to three prints. The densest event in the cohort
(SOS_2021-02-17_34.12, 831,614 prints) runs 38.9/s at its most
active 5% and bottoms out at **58.0 ms**.

### 9.2 Step 2 — against the committed sub-burst durations

`research/scale_field/s_min_vs_subbursts.py` · Chart `charts/cohort/05_s_min_vs_subbursts_*`

**The caveat bounds everything below.** D9's operating variable is the inter-trade
interval and the lineage deliberately estimates no intensity, so `n_eff` **does not bind
D9's construction on its own terms.** Nothing here says a committed sub-burst is wrong —
and §10.4 tested that directly and found they are not restatements either.

**Every source is cut to one committed cell** (§10.2 corrects an earlier version that
did not):

| lineage | cell | n | median duration | **median prints** | **exactly 2 prints** | ≤3 |
|---|---|---:|---:|---:|---:|---:|
| v4 | committed artifact, **censored at 3** | 128,818 | 348 ns | 3 | — | 54.1% |
| 10c Stage 1 | kernel 8, no floor | 46,709 | 1.75 ms | **3** | **49.3%** | 66.9% |
| 10d T4 | reference cell (D20) | 46,709 | 1.75 ms | **3** | **49.3%** | 66.9% |

10d's reference cell (`K=0, d=0, min_prints=2, hard_break`) is an identity merge over
10c's own runs and comes back **bit-identical to 10c Stage 1** — 46,709 objects, same
histogram. That is a useful internal check of the 10d pipeline.

**On the uncensored cells the modal committed sub-burst is exactly two prints — 49.3% of
them. A two-print object is a single interval.** It has no internal structure by
construction and its "duration" is one inter-trade gap rather than an estimated quantity.
v4's median of 3 is not comparable: `config/phase_10_v4.json` sets
`min_prints_reference: 3`, so that distribution is censored at 3 and the 54.1% sitting
exactly there is pile-up on the floor.

Cooper's phrasing — *"a statement about the two or three fastest prints in a session, not
about a market state"* — is **what the committed artifacts say about themselves**, off
their own `n_prints` column, needing nothing from this method.

### 9.3 What this does not say — and the half that is constructive

**The clusters are real.** Three prints inside 1.75 ms on a tape running at 0.30 prints/s
is astronomically improbable under any stationary null. What is unsupported is their
**duration as a measured quantity**: for half the population it is one interval, and a
two-interval sum has a coefficient of variation near 70%. **Detecting an anomalous cluster
needs far fewer prints than estimating a local rate.** This closes the burst-*duration*
question and leaves the burst-*detection* question open.

**And `s_min` does not say the field is useless on this cohort — it says which band it
works in.** The band that survives is the second-to-minute band, which is both measurable
(43/49 events at the 10 s horizon, 44/75 at 60 s) and the one the momentum system
actually trades in. The accurate framing is **"the tape cannot answer the question the
lineage asked"** — not "the tape cannot answer any question", which is the reading a
reader will take unless the first is written carefully.

- **No decision is appended.** Next free number remains **D22**.
- **No gate is proposed or applied.** Whether `s ≥ 2.26/λ` becomes the applicability gate
  that 10c open item 4 and 10d §4 leave open is Cooper's decision, correctly untaken.
- **This is not a retraction of D21 or of any sub-burst artifact.**
- **The floor's one convention does not matter here.** `n_eff ≥ 8` is a choice and halving
  it halves `s_min`; the gaps above are orders of magnitude, not factors. There is no
  admissible floor value at which the millisecond band becomes measurable on this cohort.

---

## 10. Cooper's read on steps 1–2 — three checks, two errors found

### 10.1 Check 1 — "v4's method minimum is 3 prints" (my wording was wrong)

Confirmed from the artifact, as Cooper asked. v4's **observed** minimum is 3 and 54.1% sit
exactly there. But 3 is **not** the structural minimum: `n_prints = n_intervals + 1` with
`n_intervals ≥ 1` gives 2, and `config/phase_10_v4.json` sets `min_prints_reference: 3` as
a **configured run-length floor** with its own rationale. So the correct statement is that
**v4's distribution is censored at 3 and the 54.1% is pile-up on the floor** — the true
shape below it is not observable in that artifact. Cooper is right that the structural
minimum is 2; my phrase "method minimum" blurred configured and structural. Corrected in
§9.2, and this makes the uncensored sources the ones to read.

### 10.2 Check 2 — the 10d row count (a real error)

Cooper's suspicion was correct. Filtering `t4_subbursts.parquet` on `kernel_min == 8`
alone leaves **78 distinct `(K, d, min_prints, sep)` cells** and 1,934,084 rows, so the
median I published was taken over a mixture of the whole assembly grid. The committed
reference cell is `K=0, d=0.0, min_prints=2, sep=hard_break` — and
`config/phase_10d.json` explicitly records that `min_prints`' reference is **2**, "the
TRUE no-op", noting that "the r1 draft's reference of 3 was wrong on this and was
corrected at T0b".

| | published (wrong) | corrected |
|---|---:|---:|
| n | 1,934,084 (78 cells) | **46,709** (one cell) |
| median duration | 3.37 ms | **1.75 ms** |
| median prints | 4 | **3** |
| ≤3 prints | 43.3% | **66.9%** |

**Did the pooled basis reach 10d's own record?** Audited, because this would have been
the second committed 10-series number on the wrong population after the 10c closing-note
erratum. `research/scale_field/audit_10d_basis.py` ·
`results/scale_field/artifacts/audit_10d_basis.json`

**It did not. 10d's committed record is clean.** All 8 digest headline metrics are
accounted for — 5 name their assembly cell explicitly, and 3 are computed *upstream* of
the `(K, d, min_prints, sep)` grid (the run-level break-cause census, the T3b void
counterfactual, the T3c 10c threshold share), so having no cell is correct rather than
missing; each exemption is recorded with its reason. The T5 attribution artifacts — 10d's
stated deliverable — are keyed per cell by construction (117 / 117 / 237 distinct cells).
The REPORT's identity figure of **1.7513 ms over 46,709 objects reproduces from the
artifact exactly**. **The pooled figure was introduced by me and lived only in
`results/scale_field/`.** 10d's headline never moved and its floor-over-merge attribution
(7.17×) was always per cell.

**And the audit produced a free corroboration.** 10d computed `share_2print` per cell in
`t4_cell_summary.parquet` by a different code path. Its identity-cell value is
**0.4934** against my independent recomputation of **0.4934** off `t4_subbursts.parquet`.
The two-print composition finding is corroborated, not merely repeated.

### 10.3 Check 3 — session coverage was the wrong denominator (a real error)

Also correct. "The median event supports the coarse band over 2.8% of its session" is
dominated by dead premarket hours. Re-cut on windows at and after the D7 anchor, the
picture changes by a factor of six on admissibility — see the window table in §9.1. The
session figure is kept as the conservative artifact-only baseline and is explicitly no
longer the admissibility denominator.

### 10.4 The restatement test — reported, then left alone

`research/scale_field/subburst_is_a_restatement.py` ·
`results/scale_field/artifacts/subburst_restatement.json`

Per event, log–log OLS of median sub-burst duration on a low quantile of that event's own
inter-trade interval distribution, against three pre-named conditions: slope within 0.25
of 1, R² ≥ 0.80, and the left-tail fit beating a median-interval control by ≥ 0.10 R².

| source | n | slope vs 5th pct | R² left tail | R² median control | predictor log₁₀ IQR | response log₁₀ IQR |
|---|---:|---:|---:|---:|---:|---:|
| 10c Stage 1 (uncensored) | 41 | 0.205 | 0.004 | 0.017 | 1.47 dec | 4.42 dec |
| v4 (censored) | 90 | 1.250 | 0.353 | 0.377 | 1.40 dec | 2.71 dec |

**The previous wording — "NOT supported", stated as a null — is withdrawn.** Three
concerns were raised against it; two were checked here and do not apply, and the third
does and is decisive for one arm.

- **"R² ≈ 0 is not evidence until the predictor's range is reported."** Checked, and it
  **does not apply**: the predictor moved **1.47 decades** (log₁₀ IQR) on the uncensored
  arm, roughly three times the 0.5-decade bar. That null is not an artifact of a static
  predictor.
- **"A near-constant response would mean the statistic is pinned by the object
  definition"** — a third possibility, and a stronger finding than either alternative.
  Checked, and it **does not apply**: the response spans **4.43 decades**.
- **Collinearity does apply, and it kills the v4 arm.** An event's low interval quantile
  and its median interval both scale with 1/λ. R² 0.353 against 0.377 is a gap of 0.024
  on 90 points, which cannot separate collinear predictors. My earlier sentence — *"so it
  tracks overall event pace, not the left tail"* — claimed more than the design delivers
  and is withdrawn. What v4 supports is only that duration tracks event **pace**.

So the uncensored arm is a real null on the 41 events it covers, with an adequate
predictor range — but n = 41, over a response spanning 4.4 decades of a heterogeneous
population. **Weak evidence, not a settled result.** It is recorded and then left alone:
it enters no load-bearing sentence, and nothing further is spent on it. The floor result
settles "the scale is unmeasurable on this tape" on its own terms — 58 ms best case
against a 1.75 ms median object — and does not need this test.

### 10.5 Stopped here

Cooper's revised order: (1) the restatement regression — **done, §10.4**; (2) re-cut
admissibility on the detection window — **done, §9.1**; (3) the recovery grid, **re-aimed
at 1 s to 300 s at the observed session rates (0.30 /s rth, 2.11 /s premarket)** rather
than at millisecond scales no event supports — **not started**; (4) matched null on the
same mask; (5) cohort last, and only for the band that survives (3).

---

## 11. The operating envelope — and a challenge to this build's premise

§9.1 showed the detection window raising `s_min`. **The window also bounds the scale axis
from above**, and that was missing: the estimator masks within `edge_scales = 4` kernel
widths of each end, so a window of length W admits only **s < W/8**. Improving the floor
inside a short window buys less than it appears to, because the ceiling comes down with it.

| window | λ median | s_min | s_max = W/8 | **usable decades** | octaves | coarse admissible |
|---|---:|---:|---:|---:|---:|---:|
| anchor ±15 min | 1.97 /s | 1.14 s | 225 s | **2.29** | 7.6 | 24 / 95 |
| anchor → +15 min | 2.68 /s | 0.843 s | 112.5 s | **2.13** | 7.1 | 35 / 93 |
| anchor → +300 s | 3.06 /s | 0.738 s | 37.5 s | **1.71** | 5.7 | 38 / 90 |
| anchor → +60 s | 4.88 /s | 0.462 s | 7.5 s | **1.21** | 4.0 | 44 / 75 |
| **anchor → +10 s** | 8.40 /s | 0.269 s | 1.25 s | **0.67** | 2.2 | 43 / 49 |
| full session | 0.30 /s | 7.52 s | 2925 s | 2.59 | 8.6 | 15 / 100 |

*(`s_min` here is taken at the median λ. The median of the per-event `s_min` differs —
Jensen — and both are in the artifact; quoting one as the other would overstate the range.)*

**Inside the operational window the field has about one decade of usable scale. In the
first ten seconds it has two-thirds of a decade — roughly two octaves.**

**This is a challenge to the recommendation this work started from, and it should be
recorded as one rather than buried.** The case for a continuous scale axis over a handful
of fixed kernels rests on having decades to select across; automatic scale selection is
what a continuum buys. **At 2–4 octaves there is very little to select over, and three or
four fixed kernels with matched-null bands would carry almost the same information at a
fraction of the machinery.**

What the field still earns in that band, and it is not nothing:

- **`s_min(t)` fell out of the construction**, and it produced the entire cohort finding
  in §9 and §12. That alone paid for the build.
- **Localisation in time** is unaffected by the scale range being short.
- **The floor is time-varying**, so a fixed-kernel scheme would need `s_min(t)` anyway —
  and at that point most of the machinery already exists.

**So step 3's brief widens: the recovery grid must also answer whether the continuum beats
three fixed kernels in a one-decade band.** If it does not, the deliverable is the floor
plus a small fixed-kernel rate statistic — a cheaper and more defensible object than a
scale-space field.

**Step 3 re-aimed** (superseding both earlier aims; 1–300 s was wrong at both ends —
300 s does not fit inside a tradeable window, and 1 s is below the floor for a large share
of events at the shorter windows):

> Inject τ over **0.3 – 10 s**, at **λ ∈ {2.5, 5, 8.4} /s**, in windows of **10 s and
> 60 s** — the observed near-anchor regime, not the session-mean one — across intensity
> contrast and duty cycle. **Include a fixed-kernel arm as the control.** Report bias and
> spread of whichever summary statistic is proposed.

---

## 12. Half the cohort is inactive when a ten-second horizon would be trading

**Only 49 of 100 events carry 25 or more prints in the 10 s after their own detection
anchor.** This was first reported as a caveat on the window table. It is not a caveat; it
is a statement about the opportunity set, and it was produced for free.

Set beside Phase 11's premarket cost figures — both verified against the committed
artifacts rather than quoted from memory:

| quantity | value | source |
|---|---:|---|
| premarket median time-weighted quoted spread at T=0 | **760.3 bp** | `results/phase_11/artifacts/t2e_i_implied_price.json` |
| premarket median share of trades on quotes > 1 s old | **62.3%** | `t2c_trade_age.parquet`, median across 48 events |
| events with ≥ 25 prints in anchor → +10 s | **49 / 100** | `s_min_cohort.parquet` |

**And the two subsets coincide — measured, not asserted.** Joining the resolution floor to
Phase 11's quote-staleness table on the 49 events that overlap on their own detection
segment:

- **corr(log₁₀ T=0 print count, share of trades on quotes > 1 s old) = −0.697** (n = 49).
- Events **measurable** at the +10 s horizon: median **44.8%** stale, median 50,228 prints.
- Events **not** measurable there: median **56.1%** stale, median 7,188 prints.

The same reading shows in premarket's own numbers: median event 62.3% stale but
**trade-weighted only 31.6%**, because staleness concentrates in the thin events.

**The events that are measurable and the events that are tradeable look like the same
subset, and it is about half the cohort.** The mechanism is not mysterious — more prints
means more quote updates — so this is a confirmation that two independent constraints
coincide, not a discovery. It bears directly on what the momentum system's real
opportunity set is.

**Caveats.** n = 49, being the overlap between this cohort and Phase 11's dev sample v3;
a correlation across events, not a causal claim; and "measurable" here means the event's
median moment in the window clears the coarse band's 1 s floor, which is this method's
criterion and not a trading one.

---

## 13. Task 1 — the field boolean does not lead a level detector. It lags.

`research/scale_field/t1_lead_time.py` · `results/scale_field/artifacts/t1_lead_time.json`
Chart: `charts/cohort/07_lead_time_{light,dark}.html`

**The concession first, because it stands.** The boolean this produces has no free
parameter. `dL/dln s` crossing zero is a *sign*, and the boundary it is read against,
`s_min = 2.26/λ̂(t)`, is arithmetic. Zero is not a tunable and 2.26 is not a cutoff. After
a lineage that died on a literature-adopted 0.70, that is a real structural gain and it is
independent of everything below.

### 13.1 The sign in the work order selects voids, not bursts

The task specifies `dL/dln s > 0`. On this estimator

> `dL/dln s = E_w[z²] − 1`,  `z = (t − tᵢ)/s`

so at the centre of a cluster narrow compared with `s` every `z ≈ 0` and the quantity goes
to **−1**; in a gap the nearest prints sit at `|z| ≫ 1` and it goes **positive**. Measured
on a synthetic 120/s burst in a 3/s background: negative at **14 of 14** scales inside the
burst (min −0.884), positive at wide scales in the quiet stretch.

Since LEVEL is a *high-activity* detector, comparing it against a void detector would pit
two anti-correlated things against each other and the lead time would be meaningless.
**Both orientations are reported**; `dL/dln s < 0` is primary.

### 13.2 The matching needed a null before any lead could be read

The first run matched **100% of LEVEL onsets** to a FIELD partner. That is not agreement —
FIELD fires ~2.8× as often as LEVEL, so with a ±7.8 s tolerance essentially any onset
finds a neighbour by chance, and a median lead near zero is exactly what chance pairing
produces.

Two corrections, both non-tunable:

- **Debounce at one kernel width**, applied to *both* booleans so neither is advantaged.
  An ON run shorter than the kernel that produced it has not been resolved by that kernel.
  That is arithmetic, not a threshold.
- **Tolerance tied to FIELD's own onset spacing** (half the median gap), not to `s` —
  matching cannot be allowed a window wider than the thing it is matching within.
- **A circular-shift null**: FIELD onsets shifted circularly inside the window, 200 draws
  per event, preserving count and spacing while destroying any timing relationship.

### 13.3 Result — neither of the two pre-named outcomes

n = 75 events, 531 matched onsets, anchor → +60 s,
median `s*` = 1.567 s.

| quantity | observed | null / bar |
|---|---:|---:|
| Jaccard of the two ON-sets | **0.263** (IQR 0.170–0.352) | restatement bar ~0.9 |
| R² of ridge strength on log λ̂ | **0.180** (IQR 0.102–0.352) | — |
| median signed lead | **-0.060 s** (-0.214 in units of `s`) | null +0.012 s |
| share of onsets where FIELD fired first | **29.7%** | **50%** chance baseline |
| share of LEVEL onsets matched at all | 50% | 67% under the null |

**It is not a restatement.** Jaccard 0.26 is nowhere near the 0.9 bar,
and R² 0.18 says the field's magnitude is mostly *not* explained by rate. The
field is measuring something the level detector is not.

**And it does not lead. It lags, and significantly.** The field fires first on
29.7% of matched onsets against a **50%** chance
baseline — the circular-shift null is symmetric by construction, so 50% is exactly what no
relationship looks like. Observed is well below it. The median lead is
-0.060 s, about 0.21 of a kernel width **behind** LEVEL. Consistent
across segments: premarket -0.214,
rth -0.174 in units of `s`.

The literal `> 0` orientation, for completeness: Jaccard 0.094 (near-disjoint,
as a void detector against a busy detector should be), field-first
52.4% against the same 50% null — i.e. indistinguishable
from chance.

### 13.4 What this decides

Cooper's own read, fixed before the run: *"If it turns on at the same instants, the
parameter-free construction is elegant but adds nothing operationally."* The measured
answer is worse than "same instants" — **it turns on later**.

**This is a null on the tradeable claim and it is not being softened.** The parameter-free
construction remains a genuine structural gain (§13's opening) and the field remains
distinct from a rate detector (Jaccard 0.26, R² 0.18) — but "distinct" and "earlier" are
different properties, and only the second was the one that would have made it a signal.

**Tasks 2–5 are not started.** Task 1 was specified as the task that decides the rest, and
what it decided is that the lead-time premise does not hold. Task 3's fixed-kernel control
arm is now the more interesting of the remaining work, not less: a field that lags a level
detector in a 2-octave band has a weaker case against three fixed kernels than it did
before this ran. That is Cooper's call, not this report's.

**Caveats.** n = 75 events with enough data in the +60 s window, which is the
same admissibility limit §12 describes. The LEVEL detector's trailing q90 over a 300 s
causal lookback is one choice among several; a faster or slower baseline would move its
onsets. And "lags by 0.2 of a kernel width" is a small absolute time — the finding is that
it is *not early*, not that the lag itself is exploitable.

---

## 14. Close-out — D22

### 14.1 The sign lives in code now

`dL/dln s = E_w[z²] − 1` goes to **−1** at a cluster centre and positive in a gap, so
`< 0` is burst-like. **The suite always had this right** — `argmin` in the duration-recovery
test, `-nanmin` in the amplitude-monotonicity test, `max(-dlograte) > 0` in the sign test.
The error was in prose restating the convention, not in code.

Fixed structurally rather than by correction: `scale_field.burst_on(f, scales, s_min_t,
factor=2.0)` and `divergence_on(...)` now define the booleans **once**, with
`scale_index_at()` doing the `factor · s_min` selection. Prose references the helper
instead of restating the condition, so this class of error cannot recur. Three new tests
pin it — the sign inside a burst, the **−1 lower bound**, and the Poisson identity of `D`.
**46 assertions pass.**

### 14.2 Why it lags, and why the bound matters — both structural

Two properties of the estimator, not two unlucky runs:

- **Bounded below by −1**, because `E_w[z²] ≥ 0`. The burst signal *saturates*. Under a
  sign condition it fires constantly (ON 34% of the window, 2.8× the level
  detector's onset rate); under a magnitude condition it barely fires. Poor discrimination
  in either direction.
- **Centred**, so it cannot go negative until the burst is centred in the kernel, while a
  level statistic responds as soon as burst mass enters at all — roughly `s` earlier. The
  lag was derivable in advance and the measured **-0.214** kernel widths sits
  exactly there.

Task 1 aimed the harness at what this statistic is structurally worst at. That is a
specification error, and it does not change the result: **the field is not an onset
detector.**

### 14.3 The one test left — `D` fails on real tape, and the kill condition is met

`D = m + lograte/ln10 + γ/ln10` is identically zero under a locally Poisson process at any
rate path. It is a level difference between two channels at one scale, so it has neither
the centring nor the boundedness that sank `dL/dln s`. Run in the Task 1 harness with one
channel swapped — nothing new built.

| form | ON share | onsets | Jaccard vs LEVEL | lead | vs chance |
|---|---:|---:|---:|---:|---:|
| `D < 0` — **parameter-free** | **100%** | 4 | 0.177 | — | unreadable |
| `D <` trailing q10 — *not* parameter-free | 2.1% | 41 | 0.018 | +0.229 `s` | **p = 0.349** |

**The parameter-free form is degenerate.** `D`'s zero is the *Poisson* identity, and this
tape sits **1.29 decades below it** at the read scale — the build brief's
opening warning, applying here too. `D < 0` is ON essentially always and emits
4 onsets across 75 events. A permanently-ON boolean is not a detector.

**The relative form does not clear the bar.** Point estimate +0.229 kernel widths,
but the share of onsets on which `D` fires first is **not distinguishable from chance** —
binomial **p = 0.349** on n = 41, from only
20 of 75 events, Wilcoxon p = 0.444, lead IQR
-0.76..+0.84 s straddling zero. And it is not
parameter-free, which was the property `D` was proposed for. For contrast the field's
*lag* is real at p = 3.05e-10 on n = 239.

**A point estimate is not a lead. The kill condition is met.**

### 14.4 The caveat that binds every lead time in this line

Both booleans use a **centred** kernel, so both read forward by about `s`. A detector
firing 3 s "before" a synthetic onset is that, not prescience. **Relative ordering
survives — both cheat equally — but no absolute timing claim does.** Nothing here is
tradeable until the construction is re-derived on a **one-sided kernel** and the comparison
re-run. This has been standing since the first verification note and was never discharged;
it is now recorded in D22 as the precondition on any future attempt rather than left as
work in progress.

### 14.5 What survives — the deliverable

- **The resolution floor `s ≥ 2.26/λ`.** The first applicability criterion this programme
  has had that is **derived rather than adopted**.
- **49.3% of committed sub-bursts are exactly two prints** — one interval — corroborated
  independently by 10d's own `share_2print` column.
- **Measurable and tradeable are the same ~half of the cohort** (49/100 at the 10 s
  horizon; corr(log print count, quote staleness) = −0.697).
- **The D9 lineage's timescales sit ~4.8 orders of magnitude below what the tape
  supports**, floor relaxed all the way to three prints.

### 14.6 Tasks 2–5 not run, and why that is the right call

Task 2 (emit `D` as a panel) is superseded — `D` is now emitted and tested, and §14.3 is
the answer. Tasks 3–5 are not run. At 2–4 usable octaves, with the onset test negative and
the statistic bounded, **the fixed-kernel control arm is no longer a control — it is the
likely winner**, and Task 3 would mostly be paying to confirm that. The finding is the
deliverable; the detector was the part we were hoping for.

**D22 appended to `docs/Universe-Decisions.md`; `CLAUDE.md`'s pointer list updated in the
same commit. Next free number: D23.**
