<!-- fullWidth: false tocVisible: true tableWrap: true -->
---
tags:
  - type/research
  - domain/microstructure
  - status/escalated
created: 2026-08-04
phase: 10
version: v2
config_hash: d48912b0
---

# Phase 10 v2 — Intensity Profile and Burst Timescale

**Branch:** `phase/10` · **Baseline:** `phase-9-approved` (`7909d66`) · **config_hash:** `d48912b0`
**Specs:** `prompts/phase_10_v2.md` + `prompts/phase_10_v2_r1.md` · **Decisions:** D6, D7

> **STATUS — HARD STOP. Four pre-registered failure criteria fired: rows 1, 2, 3 and 6.**
> State committed at `38082da` before the stop. No parameter was adjusted, no threshold moved,
> no segmentation or thresholding reintroduced. Rows 4, 5, 7, 8 and 9 pass. Row 0 (Cooper's
> visual review) is not evaluated.

**Description only.** No `k`, observable, poll interval or threshold is selected. No latency budget
is proposed. No result is characterised as good, weak, promising or disappointing.

---

## 0. Method — one thing stated plainly

**Detection comes from a price threshold. Peak comes from arrival intensity. Both are computed from
the same T=0 tick stream.** These are different quantities and the comparison is legitimate, but the
two anchors are **not independently sourced**, and nothing in this report should be read as though
they were.

The estimator is a **centred k-block adaptive kNN arrival-rate estimator**: for sorted arrival times
`t[0..n-1]` and window `k`, the block for index `i` is `a = clip(i - k//2, 0, n-k)`, `b = a + k - 1`,
`span = t[b] - t[a]`; print rate `= k / span`, share-volume rate `= sum(size[a..b]) / span`. It is
evaluated **at the arrival times themselves**, so the sampling of the output is as adaptive as the
estimator and no output grid is imposed. Fixed-width binning is prohibited (escalation row 7) and was
not used. Rationale: within-session rate spans several orders of magnitude, so any fixed width
adequate at the peak is empty in the tails.

Every curve is **self-normalized by its own event's peak** (D6): shape uses no baseline. The flanking
sessions supply exactly one scalar per event, for the terminal condition only.

---

## 1. Tie structure (T0d)

| Population | n events | prints | tied w/ prev | share | per-event share tied (med / max) | max tie run |
|---|---:|---:|---:|---:|---|---:|
| **pooled analysis cohort** | **100** | 7,556,472 | 122,044 | **1.62%** | 0.0000 / 0.0812 | 18 |

Smallest non-zero inter-arrival gap observed: **49 ns** (median across events 80 ns). `k` exceeds the
distinct-timestamp count on **1** pooled event, at `k=500` only — so a zero-span block, and therefore
a floored infinite rate, **cannot occur at the reference `k=50` anywhere in the pooled cohort**.

This is a tie-structure diagnostic only. No inter-trade interval distribution, noise floor, or
interval regime is produced — those are Phase 13's deliverable (escalation row 8 of the v1 prompt).

---

## 2. Estimator and resolution grid (T1)

| Item | Value |
|---|---|
| Family | centred k-block adaptive kNN, evaluated at arrival times |
| `k` grid | 5, 15, 50, 150, 500 (two orders of magnitude, as required) |
| Reference `k` | **50 — a reporting convention, not a selection** (escalation row 12) |
| Grid justification | `k=5` is the smallest window averaging more than a couple of gaps; `k=500` is ~2% of the median pooled event (25,204 prints) and 0.06% of the largest (831,614) |
| Observables | print rate and share-volume rate, **co-equal**, reported side by side |
| Tie variants | `as_is` (all `k`) and `collapse_same_timestamp` (reference `k`) |
| Runtime | 11.8 s total, 1.32 s max/event vs a 120 s ceiling |

---

## 3. Detection anchor (R1.3, D7)

| Quantity | Observed |
|---|---|
| Reference price undefined | **1 / 114**, flagged and carried, never imputed |
| Never-crosses @ threshold 1.30 | **2 / 100 pooled = 2.0%** |
| Phase 8 comparison for that rate | 394/15,763 = 2.50% `det_undefined` over full D1 |
| Detection segment @ 1s poll | **rth 70 · premarket 28 · post 0** |
| (T−1,T0) `flag_cross_session_extreme` in cohort | 6 events; **0** of them never-cross |

Never-crosses are the expected D4 consequence: the universe was selected on `momentum_pct` computed
from quarantined spine numerics, and the anchor is re-derived on tick. A12 applies because the D7
trigger *is* a cross-session ratio; the Phase 9 flag was joined, never re-derived.

### Phase 8 cross-check (R1.4)

| Comparison | Exact | Within ±1 min | Beyond tolerance |
|---|---:|---:|---:|
| crossing-minute (floor) vs `det_minute` — **exact analogue** | **110 / 110** | 110/110 | **0** |
| 60s-poll minute vs `det_minute` — as R1.4a specifies | 0 / 110 | 110/110 | 0 |
| reference price vs `tick_close_t_minus_1_rth` | **max relative deviation 0.000e+00** | — | — |

The 60s-poll row is the ceil-vs-floor convention difference, not a disagreement: `det_minute` is the
minute *containing* the crossing; the D7 60s poll is the first boundary *at or after* it. Neither
side was adjusted to fit the other (R1.4b). 4 never-crossing here and 4 `det_undefined` in Phase 8
are excluded and counted.

---

## 4. Detection-to-peak — a family indexed by polling interval (T3a)

Pooled analysis cohort, `k=50`, threshold 1.30, n=98 (2 never-cross). **Signed, unclipped, never
absolute-valued** (escalation row 10).

| Poll | print rate: q25 / **median** / q75 (s) | **% negative** | volume rate: q25 / **median** / q75 (s) | **% negative** |
|---|---|---:|---|---:|
| **instantaneous** *(UPPER BOUND — physically impossible)* | −23.8 / **1,975.9** / 9,824.0 | **27.6%** | −26.7 / **2,558.7** / 10,742.6 | **27.6%** |
| 1 s | −24.1 / **1,975.2** / 9,823.3 | **28.6%** | −27.3 / **2,558.4** / 10,742.2 | **28.6%** |
| 5 s | −25.4 / 1,973.2 / 9,821.5 | 29.6% | −29.1 / 2,556.9 / 10,738.9 | 29.6% |
| 15 s | −32.9 / 1,970.7 / 9,819.0 | 29.6% | −39.1 / 2,551.9 / 10,731.4 | 29.6% |
| 60 s | −55.3 / **1,955.7** / 9,789.0 | 29.6% | −55.3 / **2,521.9** / 10,708.9 | 29.6% |

**Roughly 28% of events have peak arrival intensity *before* detection.** The interquartile range
spans from negative to nearly three hours — this is not a concentrated distribution.

The spread across the poll family is small: the median moves 1,975.9 → 1,955.7 s (1.0%) from
instantaneous to a 60 s poll. Chart: [`v2_03_detection_to_peak.html`](charts/v2_03_detection_to_peak.html).

---

## 5. Decay timescale and terminal condition (T3c, T3d)

Pooled, `k=50`, `as_is`. "Falls to the fraction **and stays below** for the remainder of the session."

| Observable | to 1/2 | to 1/e | to 1/10 | never-reached |
|---|---:|---:|---:|---:|
| print rate | **67.4 s** | 739.1 s | 4,794.4 s | 0 / 0 / 0 |
| share-volume rate | **107.2 s** | 509.7 s | 4,881.4 s | 0 / 0 / 0 |

**Terminal condition** (unnormalized rate below a multiple of the event's scalar whole-day flanking
baseline), with undefined counts:

| Observable | 1× (n, median) | 2× | 5× |
|---|---|---|---|
| print rate | 67, 16,916 s · **33 undefined** | 77, 16,909 s · 23 undefined | 83, 15,711 s · 17 undefined |
| share-volume rate | 58, 17,866 s · **42 undefined** | 68, 15,734 s · 32 undefined | 80, 14,474 s · 20 undefined |

Chart: [`v2_04_decay_timescale.html`](charts/v2_04_decay_timescale.html).

---

## 6. Conditioning (T4, R1.3d)

### By detection segment — the split is enormous

| Segment | n | decay-to-half (print) | detection-to-peak @1s | % negative |
|---|---:|---:|---:|---:|
| premarket | 28 | **6,693.2 s** | 8,246.7 s | **0.0%** |
| rth | 70 | **6.2 s** | 337.1 s | **40.0%** |

Three orders of magnitude in decay-to-half between segments, and the negative share goes from 0% to
40%. Segment is a conditioning variable per R1.3d, and on this evidence it is not optional.

### By absolute peak rate (failure row 3)

| Observable | top/bottom quartile ratio of median decay-to-half | Spearman vs peak rate |
|---|---:|---:|
| print rate | **539.06** | (see `v2_t5_stability.json`) |
| share-volume rate | **9.84** | — |

Chart: [`v2_06_level_dependence.html`](charts/v2_06_level_dependence.html).

---

## 7. Stability (T5a–T5c)

**Resolution.** Pooled median decay-to-half by `k`:

| Observable | k=5 | k=15 | **k=50** | k=150 | k=500 |
|---|---:|---:|---:|---:|---:|
| print rate | 5,905.2 s | 2,602.8 s | **67.4 s** | 17.1 s | 134.6 s |
| share-volume rate | — | — | **107.2 s** | — | — |

Non-monotonic, spanning two and a half orders of magnitude. Per-event curves swing across ~10 orders
of magnitude, reaching microseconds. Chart: [`v2_05_resolution_stability.html`](charts/v2_05_resolution_stability.html).

**Observables.** Spearman on decay-to-half = **0.354** (n=100). Peak locations agree within 60 s on a
minority of events. Chart: [`v2_07_observable_agreement.html`](charts/v2_07_observable_agreement.html).

**Tie variants.** Median |log ratio| of decay-to-half between `as_is` and `collapse_same_timestamp` =
**0.000** for both observables; peak identical on **87/100** events; peak moved beyond the event's own
decay on 2% (print) / 6% (volume). Both inside tolerance — **escalation row 8 not triggered.**

---

## 8. Pre-registered failure criteria (T5d)

| # | Mode | Observable | Observed | Threshold | Result |
|---|---|---|---:|---|---|
| **0** | Cooper rejects the profile on chart 08 | — | — | Cooper's judgment | **not evaluated** |
| **1** | **Resolution instability** | print rate | **0.0228** | 0.333 – 3.0 | **FAIL** |
| **1** | Resolution instability | volume rate | **0.1991** | 0.333 – 3.0 | **FAIL** |
| **2** | **Observable disagreement** | Spearman | **0.354** | ≥ 0.50 | **FAIL** |
| **3** | **Level dependence too strong to pool** | print rate | **539.06** | 0.2 – 5.0 | **FAIL** |
| **3** | Level dependence | volume rate | **9.84** | 0.2 – 5.0 | **FAIL** |
| 4 | Peak not captured in-window | both | 0.0000 | ≤ 0.20 | PASS |
| 5 | No decay within session | both | 0.0000 | ≤ 0.20 | PASS |
| **6** | **Peak instability across the grid** | print rate | **96.23** | ≤ 1.0 | **FAIL** |
| **6** | Peak instability | volume rate | **115.86** | ≤ 1.0 | **FAIL** |
| 7 | Anchor does not exist for the cohort | never-crosses | 0.0200 | ≤ 0.20 | PASS |
| 8 | Phase 8 disagreement | 60s poll | 0.0000 | ≤ 0.10 | PASS |
| **9** | **Polling dominates the answer** | print rate | **1.0103** | ≤ 2.0 | **PASS** |
| 9 | Polling dominates | volume rate | 1.0146 | ≤ 2.0 | PASS |

**Nothing beyond pass/fail is stated about these results.**

Row 9 is worth its own line because it was pre-registered as "the one to watch": widening the poll
from instantaneous to 60 s changes the median detection-to-peak by 1.0%. On this cohort the runway
figure is **not** an artifact of assuming instantaneous detection.

Per the standing lesson carried from v1 and recorded in D6: **a stability pass is not evidence of
correctness.** Rows 4, 5, 7, 8 and 9 passing does not endorse anything.

---

## 9. Escalation check — all 13 rows (as amended by R1)

| # | Condition | Observed | Result |
|---|---|---|---|
| 1 | Tag absent / cohort hash mismatch | tag `7909d66`; cohort hash `e1a0ac73a79aa573` matched | **PASS** |
| 2 | Canonical `in_scope` join shortfall | 114 / 114, shortfall 0 | **PASS** |
| 3 | D4-quarantined spine numeric on a computation path | **0** — reference price is the tick-derived T−1 RTH close | **PASS** |
| 4 | Full-table pass over `filtered_trades`/`filtered_quotes` | **0 scans** — per-event folder reads, equivalence proven in v1 T0d | **PASS** |
| 5 | Runtime ceiling breached | 11.8 s total / 1.32 s max vs 3600 s / 120 s | **PASS** |
| 6 | Interval-labeling, thresholding or state assignment introduced | **0** — closed by D6, none added | **PASS** |
| 7 | Fixed-width binning as the rate estimator | **0** — adaptive kNN only | **PASS** |
| 8 | Tie variants diverge beyond tolerance | median \|log ratio\| 0.000; within tolerance | **PASS** |
| 9 | Derived anchor undefined other than never-crosses | **0** (1 reference-price-undefined event is inside the never-crosses disposition) | **PASS** |
| 10 | Negative detection-to-peak clipped/excluded/abs'd | **0** — signed and untouched | **PASS** |
| 11 | Output described as detector / signal / operating point / budget | **0** | **PASS** |
| 12 | `k`, observable or timescale selected or called preferable | **0** | **PASS** |
| 13 | Write outside the allowlist | **0** — the two `docs/` writes are append-only per R1.1, verified +86/−0 and +57/−0 | **PASS** |

---

## 10. Verification block

| Metric | Value | n | Source | Repro |
|---|---|---:|---|---|
| Cohort content hash | `e1a0ac73a79aa573` | 114 | `v2_common.py:cohort_content_hash` | `.venv/Scripts/python.exe research/phase_10/v2_t0a_preconditions.py` |
| Never-crosses @1.30 | 2/100 = 0.0200 | 100 | `v2_r13_detection.py:main` | `... research/phase_10/v2_r13_detection.py` |
| Phase 8 agreement (floor) | 110/110 exact | 110 | `v2_r14_phase8_check.py:main` | `... research/phase_10/v2_r14_phase8_check.py` |
| Reference-price max rel. dev. | 0.000e+00 | 110 | `v2_r14_phase8_check.py:main` | same |
| Tied prints, pooled | 122,044 / 7,556,472 = 1.62% | 100 | `v2_t0d_ties.py:main` | `... research/phase_10/v2_t0d_ties.py` |
| Detection-to-peak median @1s (print) | 1,975.2 s | 98 | `v2_t1_t4_profile.py:main` | `... research/phase_10/v2_t1_t4_profile.py` |
| Detection-to-peak negative share @1s | 0.286 | 98 | `v2_t1_t4_profile.py:main` | same |
| Decay-to-half median (print, k=50) | 67.4 s | 100 | `v2_t1_t4_profile.py:main` | same |
| Decay-to-half by k (print) | 5905.2 / 2602.8 / 67.4 / 17.1 / 134.6 | 100 | `v2_t5_stability.py:main` | `... research/phase_10/v2_t5_stability.py` |
| Observable Spearman | 0.354 | 100 | `v2_t5_stability.py:main` | same |
| Level top/bottom ratio (print) | 539.06 | 100 | `v2_t5_stability.py:main` | same |
| Peak instability ratio (print) | 96.23 | 100 | `v2_t5_stability.py:main` | same |

**Cohort waterfall** is unchanged from v1 §10 — the cohort is frozen and reused, not redrawn.

---

## 11. What was not produced, and why

**Chart 08, the per-event tape review, was not produced.** It is the acceptance gate for failure row
0, and acceptance is not on the table while four numeric rows have fired. Producing an 80-chart
review set to gate a measurement already disqualified by its own pre-registered criteria would invert
the order of the gate. This is a scoping call, stated rather than silently taken; if you want the tape
review anyway — for instance to judge whether the *peak anchor* is sound independently of the decay
timescale — it is one command away.

**T3b, the rise profile, is not reported separately.** It is the detection→peak segment of the
detection-anchored profile in chart 02, and with ~28% of events having a negative detection-to-peak
interval the "rise" is empty for that share by construction.

---

## 12. Output files

| File | Status |
|---|---|
| `prompts/phase_10_v2.md`, `prompts/phase_10_v2_r1.md` | committed before any work |
| `config/phase_10_v2.json` | committed before any run |
| `docs/Universe-Decisions.md` | **D6 and D7 appended** (+86/−0) |
| `docs/Research-Library-Map.md` | **Phase 10 entry appended** (+57/−0) |
| `results/phase_10/REPORT_v1_superseded.md`, `digest_v1_superseded.json` | v1 relabelled per R1.2 |
| `results/phase_10/artifacts/v2_t0a_escalation_row9.json` | the row-9 stop and its resolution |
| `results/phase_10/artifacts/v2_r13_detection.{parquet,json}`, `v2_r13_reference_price.parquet` | detection anchor |
| `results/phase_10/artifacts/v2_r14_phase8_crosscheck.json` | cross-check |
| `results/phase_10/artifacts/v2_t0d_tie_structure.{parquet,json}` | tie structure |
| `results/phase_10/artifacts/v2_t1_event_metrics.parquet`, `v2_t1_profiles.parquet`, `v2_t1_t4_summary.json` | estimation, anchors, timescales |
| `results/phase_10/artifacts/v2_t5_stability.json` | stability + failure criteria |
| `results/phase_10/charts/v2_01–07*.html` (+ `.png`) | **kaleido-verified 7/7** |
| `results/phase_10/charts/v2_08_tape_review/` | **not produced** — see §11 |
| `results/phase_10/{REPORT.md, digest.json}` | this |

---

## 13. Commits

`8170c53` R1.0 prompt · `086f280` R1.1 D6+D7+map · `81826db` R1.2 v1 relabel · `b71bcd0` T0c config ·
`46398d1` R1.3 detection anchor · `528eff7` R1.4 Phase 8 cross-check · `de5ed07` T0d+T1–T4 ·
`38082da` **T5 failure** · `b8495b3` T6 charts · *(this commit)* T7 digest + report

---

## Approval gate

Not tagged, not merged. Phase 11 scoping not begun.

**Four pre-registered failure criteria fired.** Per the prompt: do not adjust parameters to make a
criterion pass; do not reintroduce segmentation, thresholding of the intensity series, or Hawkes
calibration — all three are closed by D6 and reopening any requires a numbered decision. None of that
was done. Awaiting instruction.
