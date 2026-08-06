<!-- fullWidth: false tocVisible: true tableWrap: true -->
---
tags:
  - type/research
  - domain/microstructure
  - status/escalated
created: 2026-08-05
phase: 10
version: v4
config_hash: fbb992ed
---

# Phase 10 v4 — Sub-Burst Detection from Locally-Normalized Log Inter-Trade Intervals

**Branch:** `phase/10` · **Baseline:** `phase-9-approved` (`7909d66`) · **config_hash:** `fbb992ed`
**Spec:** `prompts/phase_10_v4.md` · **Decisions:** D9 (new), D7, D6/D8 (diagnoses retained), D5, D4, D3, D1

> **STATUS — HARD STOP. Pre-registered rows 1 and 6 fired. Rows 2, 3, 4, 5 and 7 pass.**
> State committed at `a26cc64` before the stop. No parameter adjusted, no threshold moved, no
> fallback threshold given to any `no_threshold` event, no intensity estimation reintroduced.
> Row 0 (Cooper's visual review of chart 06) is not evaluated by the agent — chart 06 was produced
> so that it can be.

**Description only.** No normalization window, void cutoff or minimum print count is selected. No
latency budget is proposed. No result is characterised as good, weak, promising or disappointing.

---

## 1. Preconditions and decision record

| Item | Result |
|---|---|
| Cohort content hash | **`e1a0ac73a79aa573` asserted**, 114 rows |
| `phase-9-approved` | `7909d66` |
| R1 detection artifacts | present; anchor **reused, not re-derived** |
| **D9 appended** to `docs/Universe-Decisions.md` | **+39 / −0** |

### One correction recorded in D9 rather than transcribed

D9 as drafted states *"v3 is withdrawn before execution; no v3 artifacts exist."* **That is not what
happened**, and a decision record must not contradict the repo. Phase 10 v3 ran to completion: its
Allan/Fano gate **passed** on all four cells (knees 128 s rth / 16 s premarket, ΔBIC 45.6–68.7); its
row 1 — the Arm A test — **passed** for the first time in the phase (Spearman 0.2772 / 0.3531); rows
2, 3 and 4 fired; and Cooper then rejected it on row 0. Artifacts are committed under
`results/phase_10/artifacts/v3_*`.

Two v3 results are load-bearing for D9's own argument and would be lost if the record said v3 never
ran: that **a characteristic clustering scale does exist** in this data, and that **an event-relative
reference breaks the print-count dependence** that sank Arm A. D9 supersedes v3's *method*; it does
not erase v3's *evidence*. Consequence (a) is corrected in the appended entry, with the reasoning.

---

## 2. Ties and timestamp resolution (T1)

| Quantity | Pooled (n=100) |
|---|---|
| Share of prints tied with predecessor | median **0.0000**, q75 0.0000, max 0.0812, mean 0.0069 |
| Timestamp resolution actually present | median smallest non-zero gap **80.5 ns** (min 49 ns, max 8,388 ns) |

Resolution is measured per event from the data, never assumed. Two variants were run;
`collapse_same_timestamp` is the reference because a zero interval cannot exist under it by
construction, so the log transform needs no imputed value.

**Phase 13 boundary.** This phase *uses* inter-trade intervals as its operating variable. It does
**not** produce the interval distribution as a characterized finding, the noise floor, or interval
regime definitions — those remain Phase 13's. The boundary is narrow here and is stated deliberately.

---

## 3. The void gate and `no_threshold` (T3)

| Population | n | `no_threshold` | share |
|---|---:|---:|---:|
| **pooled analysis cohort** | 100 | **10** | **0.100** |
| premarket | 28 | 3 | 0.107 |
| regular hours | 70 | 7 | 0.100 |

**The gate works and declines on a tenth of the cohort**, which is what D9's Zaliapin reasoning
predicted: the bimodality separating clustered from background events breaks in the vicinity of the
dominant event, and the whole T=0 session is that vicinity. A `no_threshold` event is one where the
method declines to declare sub-bursts rather than inventing them. **No fallback threshold was applied
to any of them.**

| Void parameter (threshold-bearing events, n=90) | Value |
|---|---|
| Median | **0.8345** |
| Share within 0.05 above the 0.70 cutoff | **0.2667** (row 3 threshold ≤ 0.30 — PASS) |

| Derived threshold (decades of normalized log interval) | Value |
|---|---|
| Pooled median | **−3.225** |
| premarket / rth median | −3.125 / −3.275 |

A threshold of −3.2 decades means **intervals roughly 1/1700 of the local median**.

Charts: [`v4_01`](charts/v4_01_log_interval_histograms.html), [`v4_02`](charts/v4_02_void_parameter.html).

---

## 4. Sub-bursts (T4)

Threshold-bearing events only, n=90, reference cell (`collapse_same_timestamp`, window 20%,
min_prints 3).

| Quantity | q25 / **median** / q75 | max |
|---|---|---:|
| Sub-burst count per event | 33 / **210.5** / 1,702 | 9,761 |
| Duration (seconds) | 2.31e−07 / **3.49e−07** / 1.33e−05 | 1.873 |
| Spacing (seconds) | 0.0065 / **1.156** / 7.16 | 24,859 |
| Share of session prints inside sub-bursts | 0.030 / **0.062** / 0.142 | 0.808 |
| Move share, rank 1 / 2 / 3 (median) | **−0.0233** / −0.0062 / −0.0122 | — |

0 undefined move-share denominators. Chart: [`v4_05`](charts/v4_05_duration_spacing_moveshare.html).

**Median sub-burst duration is 349 nanoseconds.**

---

## 5. The Arm A test (T5) — **row 1 FAILS**

| Against | Spearman | log-log slope |
|---|---:|---:|
| **T=0 print count** | **+0.8748** | **+0.9224** |
| absolute activity (prints/sec) | +0.8650 | +0.9504 |
| session activity duration | +0.4839 | +4.5278 |
| *Arm A, for reference* | *+0.96* | *+0.85* |
| *v3, for reference* | *+0.277 / +0.353* | *+0.261 / +0.185* |

Thresholds: Spearman ≤ 0.50, slope ≤ 0.35. **Both breached, and the slope sits above Arm A's own
0.85.** Chart: [`v4_04`](charts/v4_04_count_vs_prints.html).

### What the numbers say together

The threshold lands at −3.2 decades; sub-bursts are runs of **sub-microsecond** intervals with a
median duration of 349 ns against an 80.5 ns timestamp resolution; there are ~210 per event; they
carry ~6% of session prints and a rank-1 move share of −0.023.

Chart 01 shows the mechanism directly. Every threshold-bearing event has an **isolated narrow spike
at y ≈ −3.5**, separated from the broad main body by a deep trough; the void gate finds that trough
and takes it. That spike is **order fragmentation** — one marketable order sweeping several resting
orders produces several prints microseconds apart. The `no_threshold` events are precisely those
whose histograms are smooth and broad with no such spike.

So the method is separating **multi-fill microstructure from everything else**, not bursts from
quiet. The number of multi-fill events scales with the number of prints, which is why row 1 returns
+0.87 — the Arm A defect, reached by a fifth route.

---

## 6. Stability (T6a) and causal audit (T6c)

| Test | Observed | Threshold | Result |
|---|---|---|---|
| Normalization window, 10–30% grid | median relative change **0.1984** | ≤ 0.20 | **PASS** |
| *Ko et al. published comparison* | *0.003* | — | reported, not required |
| Tie variants | median relative change **0.0000** | ≤ 0.20 | **PASS** |
| Minimum print count, 2/3/5 | in artifact | — | — |

The window result passes but sits at 0.198 against a 0.20 bar, and is **66× the published 0.3%**.
Both figures are stated; the gap is a fact about our data relative to the neuroscience regime, not a
judgment.

**Causal audit (T6c):** 18 fields tagged. **2 causal** — the D7 detection anchor and the segment
label derived from it, both causal by construction because D7 was written as an operating-time
anchor. **16 non-causal.** The threshold itself is the most non-causal quantity in the phase: it is
the trough of the completed session's histogram. Phase 17 must re-derive the normalization, the
histogram, the void gate and the threshold under causality; none of them is a re-parameterization of
what is here. Artifact: `v4_causal_audit.parquet`.

---

## 7. Pre-registered failure criteria (T6d)

| # | Mode | Observed | Threshold | Result |
|---|---|---:|---|---|
| **0** | Cooper rejects on chart 06 | — | Cooper's judgment | **not evaluated** |
| **1** | **Count restates print count** | ρ **+0.8748**, slope **+0.9224** | ≤0.50, ≤0.35 | **FAIL** |
| 2 | Method does not apply to cohort | 0.1000 | ≤ 0.60 | PASS |
| 3 | Void clusters at cutoff | 0.2667 | ≤ 0.30 | PASS |
| 4 | Window drives the answer | 0.1984 | ≤ 0.20 | PASS |
| 5 | Tie handling drives the answer | 0.0000 | ≤ 0.20 | PASS |
| **6** | **Degenerate decomposition** | duration/floor **4.34** | > 10.0 | **FAIL** |
| 7 | Segment incompatibility | 0.150 decades | ≤ 1.0 | PASS |

**Nothing beyond pass/fail is stated about these results.** Row 6 fails on the duration half; the
degenerate share is 0.0.

Per the standing lesson in D6, D8 and D9: **a pass on stability rows is not evidence of
correctness.** Rows 2–5 and 7 passing does not endorse anything — and rows 4 and 5 passing is
precisely what you would expect from a method that is stably measuring the wrong object.

---

## 8. Escalation check

| Condition | Observed | Result |
|---|---|---|
| Cohort hash asserted | `e1a0ac73a79aa573` matched | **PASS** |
| Intensity curve estimated anywhere | **0** — the operating variable is the interval itself | **PASS** |
| D4 spine numeric on a computation path | **0** | **PASS** |
| Full pass over `filtered_trades` / `filtered_quotes` | **0** | **PASS** |
| Runtime ceilings | 12 s pipeline, 0.9 s max/event | **PASS** |
| Fallback threshold given to a `no_threshold` event | **0** | **PASS** |
| Phase 13 interval distribution as a finding | **0** — operating variable only | **PASS** |
| Output described as detector / signal / operating point | **0** | **PASS** |
| Writes outside the allowlist | **0** — `docs/` append-only, +39/−0 | **PASS** |

---

## 9. Verification block

| Metric | Value | n | Source | Repro |
|---|---|---:|---|---|
| `no_threshold` share | 0.100 | 100 | `v4_t5_t6.py:main` | `.venv/Scripts/python.exe research/phase_10/v4_t5_t6.py` |
| Void median | 0.8345 | 90 | `v4_t5_t6.py:main` | same |
| Threshold median | −3.225 decades | 90 | `v4_t5_t6.py:main` | same |
| Sub-burst count median | 210.5 | 90 | `v4_t5_t6.py:main` | same |
| Sub-burst duration median | 3.49e−07 s | 114,074 | `v4_t5_t6.py:main` | same |
| Timestamp resolution median | 80.5 ns | 100 | `v4_t5_t6.py:main` | same |
| Row 1 Spearman / slope | +0.8748 / +0.9224 | 90 | `v4_t5_t6.py:main` | same |
| Row 4 window relative change | 0.1984 | 90 | `v4_t5_t6.py:main` | same |
| Row 5 tie relative change | 0.0000 | 90 | `v4_t5_t6.py:main` | same |
| Pipeline | 650 event-rows, 128,818 sub-bursts, 12 s | 114 events | `v4_pipeline.py:main` | `... research/phase_10/v4_pipeline.py` |

---

## 10. Output files

| File | Status |
|---|---|
| `prompts/phase_10_v4.md`, `config/phase_10_v4.json` | committed before any run |
| `docs/Universe-Decisions.md` | **D9 appended, +39/−0** |
| `results/phase_10/artifacts/v4_event_metrics.parquet`, `v4_subbursts.parquet`, `v4_histograms.parquet` | pipeline output |
| `results/phase_10/artifacts/v4_causal_audit.parquet` | 18 fields tagged |
| `results/phase_10/artifacts/v4_t5_t6_summary.json`, `v4_pipeline_raw.json` | measurements, failure rows |
| `results/phase_10/charts/v4_01–05*.html` (+ `.png`) | **kaleido-verified 5/5** |
| `results/phase_10/charts/v4_06_tape_review/` | **60 charts + full-cohort index, all 11 `no_threshold` events charted first**, 5 panels each, 323 MB, untracked via nested `.gitignore` |
| `results/phase_10/{REPORT.md, digest.json}` | this |

Prior versions retained: v1 (`REPORT_v1_superseded`), v2 (`REPORT_v2_v3_superseded`),
v3 (`REPORT_v3_superseded`, rejected on row 0), plus their artifacts.

---

## 11. Chart 06 rebuilt — the shading was invisible, and the reason is the finding

The first build of chart 06 shaded sub-burst intervals on the full-session axis and **showed
nothing**. The rectangles were drawn; they were sub-pixel. With a median duration of 348 ns on a
57,600-second axis, a sub-burst is 6×10⁻¹² of the axis width — roughly one ten-billionth of a pixel.
That is not a plotting bug so much as the same fact row 6 fires on, expressed visually.

The rebuild has **five panels** instead of three:

1–3. Full session — price with sub-burst **locations** marked as ticks (labelled as locations, not
widths), inter-trade time, and normalized log interval with the threshold.
4. **Zoom ≈2 s** on the densest sub-burst region, intervals shaded to true extent.
5. **Zoom ≈5–20 µs** on a typical busy sub-burst, intervals shaded to true extent.

Two defects found and fixed during the rebuild, both stated rather than quietly corrected: a long
sub-burst overlapping a tight window stretched that panel's axis out of the window (rects are now
clipped to the window and the axis range is set explicitly), and the tight zoom initially centred on
the single longest sub-burst — a 1.9 s outlier — which made a "tight" zoom meaningless. It now
centres on the busiest sub-burst among the typical ones (under 1 ms, which is 90.5% of them).

**The tight zoom is itself the clearest statement of the result.** On MRSN 2023-05-03 the largest
typical sub-burst is **7 prints at the same price inside 10.7 µs** — one marketable order sweeping
the book. That is the object this method is counting.

---

## Approval gate

Not tagged, not merged. Phase 11 scoping not begun.

**Rows 1 and 6 fired.** Per the prompt: do not adjust parameters to make a criterion pass; do not
fall back to a global threshold for `no_threshold` events; do not reintroduce intensity estimation,
envelope fitting, constant-reference thresholding, two-state segmentation or Hawkes calibration.
None of that was done.

**Chart 01 showed whether the method had anything to work with** — it did, on 90 of 100 events, but
what it found was the multi-fill mode. **Chart 04 showed whether the result is real** — it is not;
row 1 fails at +0.87 / +0.92. **Chart 06 is the gate**, produced despite the failure, with every
`no_threshold` event charted first. All three reads are Cooper's.
