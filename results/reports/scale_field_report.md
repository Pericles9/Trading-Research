# Scale-space field on the momentum cohort — build report

**Spec:** `prompts/scale_field_brief.md` · **Config:** `config/scale_field.json`
**Status:** stopped at order-of-work step 3, as instructed. **Step 4 is Cooper's.**
**Date:** 2026-08-28 · **Branch:** cut from `phase/10d-diag1`
**Revised 2026-08-28** after independent verification (`VERIFICATION.md`). One defect
fixed in the estimator (the rate channel had no data floor) and **one headline number
withdrawn** — see §4. The reconciliation gate re-ran after both and is unchanged.

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

| event | λ | s_min | coarse band starts at | masked share, coarse |
|---|---:|---:|---|---:|
| AEHL | 2.46 prints/s | **0.919 s** | 1 s — *at its own floor* | 52% |
| CREX | 17.8 prints/s | **0.127 s** | 1 s — clear of it | 33% |

AEHL's coarse band spends its first three octaves at or below its own floor, so the subset
of time that survives the mask changes with every grid choice, and the fitted break moves
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
