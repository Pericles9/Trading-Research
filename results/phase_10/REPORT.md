<!-- fullWidth: false tocVisible: true tableWrap: true -->
---
tags:
  - type/research
  - domain/microstructure
  - status/rejected
created: 2026-08-05
phase: 10
version: v3
config_hash: c5aea7f6
---

# Phase 10 v3 — Sub-Burst Decomposition

**Branch:** `phase/10` · **Baseline:** `phase-9-approved` (`7909d66`) · **config_hash:** `c5aea7f6`
**Spec:** `prompts/phase_10_v3.md` · **Decisions:** D8 (new), D7, D6 (diagnosis retained), D5, D4, D3, D1

> **STATUS — REJECTED. Pre-registered rows 0, 2, 3 and 4 fired. Rows 1, 5, 6 and 7 pass.**
> State committed at `3b491a4` before the stop. No parameter adjusted, no threshold moved, no
> constant-reference thresholding, two-state segmentation or Hawkes calibration reintroduced.
> **Row 0 ALSO FIRED: Cooper rejected the decomposition on visual review of chart 07 against
> the tape.** Row 0 overrides every other row in either direction, so the row-1 pass — the Arm A
> test, which this phase cleared for the first time — does **not** constitute acceptance. The
> sub-burst decomposition is rejected.

**Description only.** No envelope scale, observable or excursion rule is selected. No latency budget
is proposed. No result is characterised as good, weak, promising or disappointing.

---

## 1. Preconditions, supersession, decision record

| Item | Result |
|---|---|
| Cohort content hash | **`e1a0ac73a79aa573` asserted**, 114 rows, groups exact |
| `phase-9-approved` | `7909d66` |
| R1 detection artifacts | all four present; anchor **reused, not re-derived** |
| **D8 appended** to `docs/Universe-Decisions.md` | **+34 / −0** |
| v2 superseded | `REPORT_v2_v3_superseded.md`, `digest_v2_v3_superseded.json`, headed with D8 and naming what survives per D8(c) and what is withdrawn. **No v2 artifact deleted.** |

Earlier in this branch, D6, D7 and the Phase 10 library-map entry were also appended (+86/−0 and
+57/−0). All `docs/` writes on this branch are append-only, verified by diff.

---

## 2. Scale-separation gate (T1) — **PASSES**

Allan (primary) and Fano computed **directly on the point process** — no intensity estimate, no
smoothing bandwidth, no threshold. Dyadic ladder 2⁻⁶…2¹³ s, 20 rungs, 5.72 orders of magnitude.

| Observable | Segment | Knee | Interval | Slope before → after | ΔBIC | Row 6 |
|---|---|---:|---|---|---:|---|
| print rate | rth | **128.0 s** | see artifact | +0.171 → +1.043 | 68.65 | **PASS** |
| print rate | premarket | **16.0 s** | — | +0.249 → +0.946 | 45.61 | **PASS** |
| volume rate | rth | **64.0 s** | — | +0.107 → +0.719 | 49.56 | **PASS** |
| volume rate | premarket | **16.0 s** | — | +0.168 → +0.875 | 53.10 | **PASS** |

**Row 7 PASS** — per-event knee IQR 0.602–0.903 decades against a 1.0 ceiling.
**Row 5 PASS** — premarket/rth separation 0.903 decades (print), 0.602 (volume).

**What the knee is and is not.** The Allan factor does not sit near the Poisson value 1 anywhere on
the ladder: the rth/print median is already **5.99 at T = 15.6 ms** and rises monotonically to **1245
at 4096 s**. Clustering is present at every scale measured. The knee marks a change in the *rate of
increase* — empirical log-log slopes **0.173 below and 1.017 above** 128 s — i.e. where envelope
variation begins to dominate, not where clustering begins. Verified against the median curve
directly, because log-log axes make the left-hand portion look steeper than it is.

**Population note, stated not silent.** Gate rows are scored on the **configured segments**
(premarket, rth, post) only. A first run also scored a `no_detection` stratum — the 2 never-crossing
events, which have no detection anchor and therefore no segment — whose n=2 knee IQR of 1.957 decades
failed row 7. Row 7's observable is defined "within a segment"; scoring it on a 2-event non-segment
is a population error, not a finding. **No threshold was moved.** Their curves are retained.

Chart: [`v3_01_scale_separation.html`](charts/v3_01_scale_separation.html).

---

## 3. Envelope (T2)

The envelope scale **is** the T1 knee, per segment — not a free parameter, not swept independently of
the gate. Converted per event to `k_env = round(n_prints / session_span_seconds × knee_seconds)`,
clipped to [5, n−1]: the expected number of prints in a knee-duration window at that event's own mean
rate. Median `k_env` = **35** (print) and **22** (volume). Fast curve at k=50, the v2 reference
carried forward per D8(c).

Excursions are taken on the **ratio rate/envelope** — ON at 2.0×, OFF at 1.5×, merge and minimum
duration both at 0.25 × knee. The rule never compares rate to a constant, which is the defect D8
exists to prevent.

Chart: [`v3_02_envelope_examples.html`](charts/v3_02_envelope_examples.html).

---

## 4. Sub-bursts (T3), segment-conditioned

Pooled analysis cohort n=100. `row_cap_census` and `dev_v4_sidecar` carried, labeled, **never pooled**.

| Observable | Population | n events | n sub-bursts | count q25/**med**/q75 | duration med | spacing med |
|---|---|---:|---:|---|---:|---:|
| **print rate** | pooled | 100 | 5,679 | 13 / **27** / 53 | 33.09 s | 87.33 s |
| print rate | premarket | 28 | — | — / **131** / — | 11.62 s | 47.6 s |
| print rate | rth | 70 | — | — / **20** / — | 79.31 s | 254.0 s |
| print rate | row_cap_census | 8 | — | — / 30 / — | — | — |
| print rate | dev_v4_sidecar | 5 | — | — / 3 / — | — | — |
| **volume rate** | pooled | 100 | 10,360 | 33 / **70** / 128 | 24.53 s | 70.48 s |
| volume rate | premarket | 28 | — | — / **202** / — | 11.11 s | 47.5 s |
| volume rate | rth | 70 | — | — / **48** / — | 50.79 s | 122.0 s |

Premarket events yield ~6× the sub-burst count of regular-hours events at ~1/7 the duration —
consistent with premarket's 16 s knee against rth's 128 s.

### Move share (T3b/c)

| Observable | per-sub-burst share q25 / med / q75 | undefined denominator | largest / 2nd / 3rd (median) |
|---|---|---:|---|
| print rate | −0.031 / 0.000 / 0.039 | **0** | **0.195** / 0.083 / −0.061 |
| volume rate | −0.029 / 0.000 / 0.031 | **0** | 0.080 / 0.056 / −0.059 |

Median share of session **prints** inside sub-bursts: 0.207 (print) / 0.351 (volume). Median share of
session **seconds**: 0.093 / 0.271.

### Timing relative to the anchors (T3d)

| Observable | seconds from detection to sub-burst start (q25/med/q75) | seconds from peak (q25/med/q75) |
|---|---|---|
| print rate | 3,149 / 11,584 / 21,460 | −5,294 / 1,556 / 10,136 |
| volume rate | 2,131 / 9,823 / 20,446 | −7,050 / 781 / 8,143 |

Charts: [`v3_03`](charts/v3_03_subburst_count.html), [`v3_05`](charts/v3_05_subburst_duration_spacing.html),
[`v3_06`](charts/v3_06_subburst_move_share.html).

---

## 5. The Arm A test (T4) — **row 1 PASSES**

| Observable | Spearman vs T=0 print count | log-log slope | Threshold | Result |
|---|---:|---:|---|---|
| print rate | **+0.2772** | **+0.2605** | ≤ 0.50 and ≤ 0.35 | **PASS** |
| volume rate | **+0.3531** | **+0.1849** | ≤ 0.50 and ≤ 0.35 | **PASS** |
| *Arm A, for reference* | *+0.96* | *+0.85* | — | *(the defect)* |

Supporting diagnostics, pooled:

| Against | print rate Spearman / slope | volume rate Spearman / slope |
|---|---|---|
| session activity duration | +0.2055 / **+1.4249** | +0.3356 / **+1.1101** |
| absolute peak rate | +0.1680 / +0.0794 | +0.3167 / +0.0572 |

T4b asks whether print count dominates duration. It does not — the duration slope is five to six
times the print-count slope, and the peak-rate slope is near zero.

**One caveat on that comparison, stated rather than buried.** Session activity duration spans only
about **0.35 decades** across the cohort — most events run nearly the full session — against roughly
**3 decades** for print count. The duration slope is therefore fitted over a far narrower range and
carries correspondingly less weight than the print-count slope. The row-1 result rests on the
print-count correlation and slope, which are measured over the wide range; the duration comparison
supports it but should not be read as equally well determined.

Chart: [`v3_04_subburst_count_vs_prints.html`](charts/v3_04_subburst_count_vs_prints.html).

---

## 6. Stability (T5a–T5c)

**Observables.** Spearman on sub-burst count between print and volume rate = **0.4233** (n=100).
Levels also differ: median count 27 vs 70.

**Tie variants.** Median interval Jaccard between `as_is` and `collapse_same_timestamp` = **1.0000**
for both observables; identical sub-burst count on **89/100** (print) and **86/100** (volume). Tie
handling is a non-issue at these scales.

---

## 7. Pre-registered failure criteria (T5d)

| # | Mode | Observable | Observed | Threshold | Result |
|---|---|---|---:|---|---|
| **0** | **Cooper rejects the decomposition on visual review of chart 07** | — | — | Cooper's judgment | **FAILED — rejected by Cooper** |
| **1** | **Sub-burst count restates print count** | print | ρ +0.2772, slope +0.2605 | ≤0.50, ≤0.35 | **PASS** |
| **1** | | volume | ρ +0.3531, slope +0.1849 | ≤0.50, ≤0.35 | **PASS** |
| **2** | **Observable disagreement** | print vs volume | **+0.4233** | ≥ 0.50 | **FAIL** |
| **3** | **Envelope instability in the knee interval** | print | **+0.0735** | ≥ 0.50 | **FAIL** |
| **3** | | volume | **+0.1071** | ≥ 0.50 | **FAIL** |
| **4** | **Degenerate decomposition** | print | duration/floor **1.0339** | > 1.25 | **FAIL** |
| 4 | | volume | duration/floor 1.5333 | > 1.25 | PASS |
| 5 | Segment incompatibility | print | 0.903 decades | ≤ 1.0 or overlap | PASS |
| 5 | | volume | 0.602 decades | ≤ 1.0 or overlap | PASS |
| 6 | No characteristic scale *(gate)* | 4 cells | ΔBIC 45.6–68.7, slope change 0.61–0.87 | ≥10 and ≥0.20 | **PASS** ×4 |
| 7 | Gate not robust *(gate)* | 4 cells | IQR 0.602–0.903 decades | ≤ 1.0 | **PASS** ×4 |

**Nothing beyond pass/fail is stated about these results.**

**Row 3 is the substantive failure.** The sub-burst sets computed at the two ends of the knee's *own
bootstrap interval* overlap by a median interval Jaccard of **0.0735** (print) and **0.1071**
(volume). Inside the interval T1 itself placed on the knee, the decomposition returns almost entirely
different sub-bursts. The gate certified that a characteristic scale exists; row 3 says the knee is
not sharp enough to pin the decomposition it licenses.

**Row 4** fails on the print observable only, and on the duration half of the row — the
degenerate-share is 0.0 for both observables. Median print-rate sub-burst duration is 1.03× the
minimum-duration floor, i.e. sitting on the rule's own parameter.

**Row 0 fired.** Cooper rejected the decomposition on visual review of chart 07 against the tape.
Row 0 overrides every other row in either direction. The row-1 pass — the Arm A test, cleared here
for the first time in this phase — therefore does **not** constitute acceptance, and neither do rows
5, 6 and 7. Per D8's standing lesson, carried from v1: **a pass on stability rows is not evidence of
correctness.** This is the second consecutive phase version in which every numeric criterion that
mattered behaved while the visual review rejected the result.

---

## 8. Escalation check

| # | Condition | Observed | Result |
|---|---|---|---|
| Cohort | content hash asserted on every run | `e1a0ac73a79aa573` matched | **PASS** |
| D4 | spine numeric on a computation path | **0** — all quantities tick-derived | **PASS** |
| Scans | full pass over `filtered_trades`/`filtered_quotes` | **0** — targeted folder reads only | **PASS** |
| Runtime | ceilings | gate 39 s, T2–T4 21 s, all inside | **PASS** |
| Phase 13 | interval distribution as a finding | **0** — inter-trade time is a display axis only | **PASS** |
| Detector | output described as detector / signal / operating point | **0** | **PASS** |
| Selection | envelope scale, observable or rule selected | **0** | **PASS** |
| Writes | outside the allowlist | **0** — `docs/` writes append-only, +34/−0 this task | **PASS** |

---

## 9. Verification block

| Metric | Value | n | Source | Repro |
|---|---|---:|---|---|
| Gate knee, rth/print | 128.0 s, slopes +0.171→+1.043, ΔBIC 68.65 | 70 events | `v3_t1_gate.py:main` | `.venv/Scripts/python.exe research/phase_10/v3_t1_gate.py` |
| Gate knee, premarket/print | 16.0 s, ΔBIC 45.61 | 28 events | `v3_t1_gate.py:main` | same |
| Median Allan, rth/print @15.6 ms | 5.99 | 70 events | `v3_t1_gate.json` | same |
| Median Allan, rth/print @4096 s | 1245 | 70 events | `v3_t1_gate.json` | same |
| Sub-burst count median (print) | 27 (IQR 13–53) | 100 events | `v3_t2_t4_subbursts.py:main` | `... v3_t2_t4_subbursts.py` |
| Sub-burst count median (volume) | 70 (IQR 33–128) | 100 events | `v3_t2_t4_subbursts.py:main` | same |
| Row 1 Spearman / slope (print) | +0.2772 / +0.2605 | 100 events | `v3_t2_t4_subbursts.py:main` | same |
| Row 1 Spearman / slope (volume) | +0.3531 / +0.1849 | 100 events | `v3_t2_t4_subbursts.py:main` | same |
| Row 3 knee-interval Jaccard (print) | 0.0735 | 100 events | `v3_t5_stability.py:main` | `... v3_t5_stability.py` |
| Row 2 observable Spearman | 0.4233 | 100 events | `v3_t5_stability.py:main` | same |
| Row 4 duration/floor (print) | 1.0339 | 5,679 sub-bursts | `v3_t5_stability.py:main` | same |
| Tie-variant Jaccard | 1.0000 both observables | 100 events | `v3_t5_stability.py:main` | same |

---

## 10. Output files

| File | Status |
|---|---|
| `prompts/phase_10_v3.md`, `config/phase_10_v3.json` | committed before any run |
| `docs/Universe-Decisions.md` | **D8 appended, +34/−0** |
| `results/phase_10/REPORT_v2_v3_superseded.md`, `digest_v2_v3_superseded.json` | v2 record, retained |
| `results/phase_10/artifacts/v3_t1_gate.{json,parquet×2}` | gate curves and per-event knees |
| `results/phase_10/artifacts/v3_t3_subbursts.parquet`, `v3_t3_event_metrics.parquet` | decomposition |
| `results/phase_10/artifacts/v3_t2_t4_summary.json`, `v3_t5_stability.json` | measurements, failure rows |
| `results/phase_10/charts/v3_01–06*.html` (+ `.png`) | **kaleido-verified 6/6** |
| `results/phase_10/charts/v3_07_tape_review/` | per-event review + full-cohort index, untracked via nested `.gitignore` |
| `results/phase_10/{REPORT.md, digest.json}` | this |

---

## Approval gate

Not tagged, not merged. Phase 11 scoping not begun.

**Rows 0, 2, 3 and 4 fired.** Per the prompt: do not adjust parameters to make a criterion pass; do not
reintroduce constant-reference thresholding, two-state segmentation, or Hawkes calibration. None of
that was done.

**Chart 01 decided whether the phase is well-posed** — it passed: a characteristic clustering scale
exists. **Chart 04 decided whether the result is real** — row 1 passed, the first method in this
phase to clear the Arm A test. **Chart 07 was the gate, and Cooper rejected on it.** Producing chart
07 despite the numeric failures is what made that judgment possible at all; had it been skipped as
v2's was, the phase would have reported four numeric passes and a stalled decomposition with no way
to see why.

**Disposition: rejected on row 0.** What survives is the gate result (a characteristic scale exists,
at 128 s / 16 s) and the row-1 method finding (an envelope-relative reference breaks the print-count
dependence that sank Arm A). What is rejected is the decomposition those two results were meant to
license. Recording that as a numbered decision — as v1's row-0 rejection became D6 — is Cooper's.
