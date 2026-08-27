# Phase 10d — Report

**Date:** 2026-08-26 · **Branch:** `phase/10d`, cut from `master` at `213bd7c`
**Config:** `config/phase_10d.json`, hash `c5dd2fdc`
**Prompt:** `prompts/phase_10d.md` (r2) · **Spec:** `prompts/phase_10d_spec.md` (r2)
**Decision recorded:** `docs/Universe-Decisions.md` **D20** (drafted as D15 — see §2.6)
**Audience:** a fresh chat with no context. Everything needed to read this is stated here.

---

## 1. What this phase did, in one paragraph

Phase 10c produced sub-bursts by taking maximal runs of **strictly consecutive** intervals
lying below a per-event threshold, and applied **no run-length floor at all**. 10d changed
only how those labelled intervals become burst objects: it added a **merge tolerance**
(two runs separated by a short, shallow interruption become one), a **separator rule**
(whether an interruption caused by missing data may be bridged), and a **run-length floor**
(`min_prints`). Nothing upstream moved — same centered clock-time window, same three
kernels, same variant grid, same argmax-void threshold with no cutoff, same histogram and
peak-survival rule. The phase's deliverable is **not a better duration number; it is the
attribution** — which of the two mechanisms moved the number, and by how much.

**The answer: the run-length floor, by a factor of 7.2.** At the primary kernel the floor
alone shifts median sub-burst duration **+0.3209 decades**; the strongest of the twelve
merge cells shifts it **+0.0838 decades**. The two are cleanly separable and both are real.

---

## 2. Six specification defects found, and what was done about each

The phase prompt carries a standing rule: *if anything in it contradicts
`config/phase_10c.json` or a Stage 1 artifact, the artifact wins — post the discrepancy, do
not resolve it as a judgment call.* That rule fired six times. Four were found before the
prompt reached its committed form; two were found during execution. All six are recorded
because each changes what the phase means.

### 2.1–2.4 The four carried in `prompts/phase_10c_closing_note_erratum.md`

An earlier 10d draft was built on 10c's pre-phase *outline* rather than its committed
config, and was wrong on four settled points: the window basis (it said **trailing**; 10c
committed **centered**, with `trailing` a listed forbidden variant), the threshold rule (it
said **first trough clearing void 0.70**; 10c committed **argmax void across all troughs,
never thresholded**), the declined-share baseline, and a claimed retirement of causal debt
that never happened. Full text in the erratum, committed at `b7ac104`.

### 2.5 10c applies no run-length floor — so `min_prints = 3` is not the identity cell

Found at T0b. The r1 prompt and spec both defined the identity cell as
`K=0, d=0, min_prints=3`, calling it "the exact configuration 10c runs", and control C1
required the degenerate cells to reproduce 10c at that floor.

There is **no `min_prints` variable in `research/phase_10c/s1_t1_subbursts.py`**. Every
maximal run is emitted with no length filter. From
`results/phase_10c/artifacts/s1_t1_subbursts.parquet` (n = 170,722 objects):

| `n_prints` | count | share |
|---|---|---|
| **2** (a single interval) | **89,343** | **52.3%** |
| 3 | 31,004 | 18.2% |
| 4 | 15,920 | 9.3% |
| ≥ 5 | 34,455 | 20.2% |

Applying `min_prints = 3` deletes 89,343 objects — 52.3% of the population — so C1 as
written was unsatisfiable. **The identity is `min_prints = 2`**, which is a strict no-op:
`n_prints = n_intervals + 1` and `n_intervals ≥ 1`, so 2 is the minimum the data structure
can emit. Corrected in r2; the grid `{2, 3, 5}` was unchanged, only the reference moved.

This is also why the floor turned out to be the dominant mechanism (§6). It is not a
sensitivity — at 52.3% it selects which objects exist.

### 2.6 The decision number: D15 was already taken

`prompts/phase_10d_spec.md` §7 drafts the decision as **D15** on the stated basis that
"D1–D14 are taken". They are not: **Phase 11 appended D15–D19** (D15 coverage-column
source, D16 instrument reference convention, D17 quote-state exclusion, D18 Stage B
population, D19 spread/cost units). `CLAUDE.md`'s pointer list stops at D14 and is stale in
the same way. Appending a second D15 would collide with a committed decision, and
append-only leaves no clean way to renumber afterwards.

**Appended as D20**, every other word verbatim from spec §7, with the renumber recorded
inline in the decision itself. **Confirm or override.**

### 2.7 Stage 1's recorded config hash is stale by one commit

Found at T4, by an assertion that was supposed to be a formality. `config/phase_10d.json`
pre-registered `config_hash_expected: 998c2461`, read from
`results/phase_10c/digests/stage1_digest.json`. The assertion failed.

`998c2461` is the CRLF-byte hash of `config/phase_10c.json` **as of commit `0f079a9`**.
Commit `39ec87e` ("phase-10c-stage-1 T0: denominator resolved") **edited that config inside
Stage 1**, and `39ec87e` precedes `692d9d0` ("phase-10c-stage-1 T1"), the commit that
produced `s1_t1_cells.parquet` and `s1_t1_subbursts.parquet`. So Stage 1's T1 ran under the
post-edit config while its digest, `REPORT.md` and `s1_t0_denominator.json` all carry the
pre-edit hash. True values: **`17124203`** (LF-normalised) / **`a0943e2a`** (raw, CRLF as
committed).

Separately: `research/phase_10c/common.py::cfg_hash()` hashes **raw file bytes**, so its
output depends on the checkout's line endings. Stage 0 recorded `9c739c08`, which is the
**LF**-form hash at `9587f10`; Stage 0b and Stage 1 recorded **CRLF**-form hashes. The
convention flipped mid-phase and the value is not reproducible across clones with different
`core.autocrlf`. 10d asserts both forms. **No 10c artifact was edited.**

### 2.8 10c has no "reference variant" — the cost allocation was widened, not narrowed

Spec §3.3 drafts a reduced cost allocation: full cross at D5 = 8 min "on 10c's reference
variant", reduced sets elsewhere, to avoid "roughly nine times the surface". Two problems,
both pre-registered in `config/phase_10d.json` rather than discovered at run time:

1. **10c has no reference variant.** Amendment 3 A carries all three (1.25 / 1.30 / 1.35)
   and selects none, and 10c escalation row 3 makes dropping, promoting or selecting a
   variant a hard stop. Designating one here would have been that act.
2. **The 9× cost does not exist.** 10c's own design note in `s1_t1_subbursts.py` records
   that sub-burst extraction is a function of `(event, kernel)` **only** — the variant
   determines segment and anchor labelling and nothing in the assembly math. The variant
   axis is a cross-join, not a recomputation, so the true cost is 3×, not 9×.

10d therefore ran the **full cross at all three kernels**, cross-joined onto all three
variants. This widens the drafted allocation and narrows nothing.

---

## 3. What was fixed and what was frozen

**Frozen background, asserted at run time against `config/phase_10c.json`:** centered
clock-time window (`trailing` and `anchored_to_detection` forbidden); kernels
{2, 8, 32} min with **D5 = 8 min primary**; variants {1.25, 1.30, 1.35}, all carried, none
selected; four segments (premarket, rth, evening, unlabelled); per-interval derived data
floor `n ≥ (√(π/2)·σ_log10 / log10 1.5)²` plus the cell-level `ok.sum() ≥ 50` minimum;
argmax-void threshold selection with **no cutoff** (`D13_void_parameter.threshold: null`);
histogram, bin grid and the Poisson peak-survival rule; D4 tick-derivation.

**The pre-registered grids** (committed at `3112d74`, before any real event was read):

| Axis | Grid | Reference | Note |
|---|---|---|---|
| `K` count tolerance | {0, 1, 2, 3, 5} intervals | 0 | 0 admits no separator |
| `d` depth tolerance | {0, 0.25, 0.5, 1.0} **decades added to threshold** | 0 | additive, never multiplicative — the threshold is negative on a normalized log axis, so multiplying tightens as the factor grows |
| `min_prints` | {2, 3, 5} | **2** | 2 is the true no-op (§2.5) |
| `sep` | {`hard_break`, `bridgeable_count_only`} | **`hard_break`** | whether an `ok=False` interruption may be bridged |

**Identity cell = `K=0, d=0, min_prints=2, sep=hard_break`** — 10c's rule exactly.

**8 of the 20 `(K, d)` combinations are degenerate**, bit-identical to the identity: a
separator is non-burst by definition, so `d=0` admits none regardless of `K` and `K=0`
admits none regardless of `d`. Only 12 are distinct. They are stored once, flagged
`degenerate`, and the resulting flat plateau on chart 08 is labelled a parameterization
artifact. Parameter dominance is computed over the 12 non-degenerate cells only.

---

## 4. Control gate — T2, hard barrier, no real event read

`research/phase_10d/controls.py` → `results/phase_10d/controls/*.json` · **chart 01**

| Control | Required | Observed | Verdict |
|---|---|---|---|
| **C1 identity** | all 8 degenerate cells at `min_prints=2, sep=hard_break` reproduce 10c print for print and are identical to each other | 8 committed 10c `(event, kernel)` cells replayed (2 → 34,149 runs), all match, all 8 cells identical; plus 50 synthetic sequences, all match | **PASS** (hard) |
| **C2 monotonicity** | count non-increasing, duration non-decreasing as `K`, `d`, `min_prints` rise | **0 violations in 2,400 gated checks** over 200 sequences | **PASS** (hard) |
| **C3 depth direction** | raising `d` admits more separators, never fewer | separators admitted 0 / 1 / 2 / 4 at `d` = 0 / 0.25 / 0.5 / 1.0, exactly matching a construction with separators at 0.1 / 0.3 / 0.6 / 0.9 decades above threshold | **PASS** (hard) |
| **C4 separator equivalence** | identical output when no `ok=False` interval exists | **12,000 comparisons, 0 differences**; converse check confirms the rules do differ when `ok=False` is present (3 objects vs 1) | **PASS** (hard) |
| **C5 floor no-op** | `min_prints=2` deletes zero objects | **0 of 47,454** deleted at 2; 5,970 (12.6%) at 3; 16,101 (33.9%) at 5 | **PASS** (hard) |

**All five hard gates passed. 10d-R2 did not fire.**

### 4.1 One specification correction made inside the gate

Spec §5 asks C2 to gate on "merged duration non-decreasing". **Median object duration is
not monotone under a correct merge** and cannot be gated on: objects `[1s, 1s, 100s, 100s]`
have median 50.5 s, and merging the two 100 s objects gives `[1s, 1s, 200s]`, median 1 s —
a decrease produced by a correct merge. C2 therefore gates on **count, total duration and
max duration**, which are monotone by construction, and reports the median un-gated with
the counterexample recorded in `c2_monotonicity.json` and on chart 01. Observed
non-monotone median cases: 0. This is the A10b.1-legitimate case — a specification defect
a control exposed, corrected before any real data was touched.

### 4.2 Why C1's "replay" is not a real-event read

Assembly is a pure function of the interval label array. C1 reconstructs a committed 10c
cell's label structure from its **emitted objects** in `s1_t1_subbursts.parquet` and
round-trips it through `assemble.py`. That reads a committed artifact, not ticks, so it
sits legitimately behind the T2 barrier. Separator widths are not recoverable from the
artifact and are reconstructed as exactly one; that is sufficient for the identity cell,
where separator width is irrelevant by construction, and C2/C3 exercise separator width on
synthetic sequences with known structure. The full-strength check came at T4 (§5.1).

---

## 5. What the assembly produced — T4

`research/phase_10d/t4_assembly.py` · waterfall in `t4_waterfall.json`

| Stage | Count |
|---|---|
| events in dev sample | 56 |
| events with T=0 prints | 56 |
| raw prints | 3,774,862 |
| after `collapse_same_timestamp` | 3,671,288 |
| after D1 sweep aggregation (100 µs) | 2,629,076 |
| intervals | **2,629,020** |
| zero-length intervals dropped | **0** |
| `(event, kernel)` cells | 168 |
| → `insufficient_context` | 38 |
| → `no_threshold` | **0** |
| → `ok` | **130** |
| assembly configurations run | 10,140 |
| sub-burst rows written | 6,811,163 |
| wall clock | 128 s |

### 5.1 The identity cell reproduces 10c bit-exactly, on real data

This is stronger than C1 and is the check that makes every comparison in §6 meaningful.
Against `results/phase_10c/artifacts/s1_t1_subbursts.parquet`:

| Field | Result |
|---|---|
| object count | 170,722 = 170,722 |
| `start_ns` | **identical**, all 170,722 |
| `end_ns` | **identical**, all 170,722 |
| `n_prints` | **identical**, all 170,722 |
| `duration_s` | **identical**, all 170,722 |
| `move_share` | max absolute difference **0.0** |

Interval count (2,629,020) and `ok` cell count (130) also match 10c exactly. Reproducing
`duration_s` bit-exactly required subtracting the int64 nanosecond timestamps **before**
casting to float — casting first loses ~256 ns at 1e18 magnitudes.

An assertion in `t4_assembly.py` also confirms a latent soundness condition in 10c's own
code: 10c indexes `agg_ts` with **filtered** interval indices (`keep = dt_s > 0`), which is
only correct when the filter drops nothing. It drops nothing here (0 of 2,629,020), so
10c's indexing is sound on this cohort. Asserted rather than assumed.

### 5.2 T4c — why is each run break there? First measurement of this split in the programme

`results/phase_10d/artifacts/t4_break_cause.parquet` · **chart 03**

A run breaks either because an interval sits **at or above threshold** — a real gap — or
because it **fails the `ok` mask**, meaning the centered window held fewer intervals than
the per-event derived floor so no trustworthy normalized value exists. The second is a
data-quality artifact, not market behaviour, and nothing in the programme had measured it.

| Kernel | ok cells | runs | breaks | breaks involving `ok=False` | share | interval-level `ok=False` share |
|---|---|---|---|---|---|---|
| 2 min | 38 | 97,122 | 97,084 | 984 | **1.01%** | 26.4% |
| 8 min | 43 | 46,709 | 46,666 | 268 | **0.57%** | 4.46% |
| 32 min | 49 | 26,891 | 26,842 | 47 | **0.18%** | 1.01% |
| **pooled** | **130** | **170,722** | **170,592** | **1,299** | **0.761%** | **11.9%** |

**Fragmentation is not a data-quality artifact.** 99.24% of run breaks are real
above-threshold gaps. The interval-level share is higher because `ok=False` intervals
cluster inside long separator runs that break a run only once. No threshold is attached to
this row — it is description.

This also predicts the separator axis will be nearly inert, and it is (§6.4).

---

## 6. The attribution — T5, the deliverable

`research/phase_10d/t5_attribution.py` → `t5_attribution.json` · **charts 06, 07, 08, 09**
All figures below: **kernel 8 min (D5, primary), `sep = hard_break`, label `ok` cells only,
43 events, 46,709 objects at the identity cell.**

### 6.1 Which mechanism moved duration

| Read | Cell | n objects | median duration | shift from identity |
|---|---|---|---|---|
| **identity** (10c's rule) | K=0, d=0, mp=2 | 46,709 | **1.7513 ms** | — |
| **floor only** | K=0, d=0, **mp=3** | 23,662 | 3.666 ms | **+0.3209 decades** |
| **floor only** | K=0, d=0, **mp=5** | 10,990 | 6.994 ms | **+0.6014 decades** |
| **merge only** (strongest of 12) | K=5, d=1.0, mp=2 | 35,435 | 2.105 ms | **+0.0838 decades** |
| **merge only** (median of 12) | — | — | — | **+0.0470 decades** |
| **joint** (max) | K=5, d=1.0, mp=5 | 11,574 | — | **+0.9062 decades** |

- **The floor moved it, by 7.17×.** Floor-only max shift 0.6014 decades against merge-only
  max 0.0838.
- **The two are mildly super-additive**, not independent: joint max at `mp=3` is **+0.5165
  decades** against an additive prediction of +0.4047 (floor `mp=3` 0.3209 + merge max
  0.0838), an interaction of **+0.1118 decades**. Across the whole joint surface the largest
  shift is **+0.9062 decades**, at `K=5, d=1.0, mp=5`.
- Per segment (variant 1.25 labelling, kernel 8): floor-only at `mp=3` shifts premarket
  **+0.4256** (n = 24,844, identity median 1.1666 ms), rth **+0.2599** (n = 21,839, identity
  median 2.6292 ms), unlabelled **+0.0744** (n = 26, identity median 6836.7 ms); merge-only
  max shifts premarket **+0.0596**, rth **+0.1152**, unlabelled **+1.0930**. **The unlabelled
  segment holds 26 objects** and its median is correspondingly unstable — it is reported, not
  leaned on. `evening` has no `ok` event at variant 1.25; under variant 1.35 two events
  (CELH 2020-08-06, OST 2024-06-13) label `evening` — see §6.6.

### 6.2 Promotion versus deletion — the diagnostic a median cannot give (chart 07)

Both mechanisms lower the share of single-interval objects. Only one keeps the prints.

| Cell | n objects | 2-print share | prints inside bursts | Δ vs identity |
|---|---|---|---|---|
| identity | 46,709 | 0.4934 | 1,751,485 | — |
| floor `mp=3` | 23,662 | 0.0000 | 1,705,391 | **−46,094 (−2.63%)** |
| floor `mp=5` | 10,990 | 0.0000 | 1,662,902 | **−88,583 (−5.06%)** |
| merge K=1 d=0.25 | 44,025 | 0.4827 | 1,751,485 | **0 (exactly)** |
| merge K=5 d=1.0 | 35,435 | 0.4387 | 1,756,504 | **+5,019 (+0.29%)** |

The floor **deletes**: objects and their prints leave the burst population. The merge
**promotes**: short objects become longer ones and the prints stay. A merge at `K=1`
preserves the print count *exactly*, by construction — two objects of `a` and `b` intervals
separated by one interval give `(a+1)+(b+1) = a+b+2` prints before and `(a+1+b)+1 = a+b+2`
after.

### 6.3 Parameter dominance — 10d-R3

Computed over the **twelve non-degenerate `(K, d)` cells only**, kernel 8, `mp=2`,
`sep=hard_break`. The row fires if count or duration tracks the tolerance more strongly
than it tracks any event characteristic.

| Quantity | tolerance rank \|ρ\| | max event-characteristic \|ρ\| |
|---|---|---|
| per-event median duration | **0.032** | **0.944** |
| per-event object count | **0.045** | **0.399** |

**Does not fire, and not marginally.** The answer tracks the event by an order of
magnitude, not the parameter.

### 6.4 Separator sensitivity — T5c

111 matched cells compared across all three kernels. `bridgeable_count_only` never produces
more objects than `hard_break`; **maximum absolute change in object count is 0.559%**, and
3 of 111 cells are bit-identical. This is the T4c break-cause split expressed in object
terms: because only 0.761% of breaks involve an `ok=False` interval, allowing those to be
bridged barely moves anything. **The conservative reference costs almost nothing**, and
this is the first quantification in the programme of how much burst fragmentation is a
data-quality artifact rather than market behaviour. It is small.

### 6.5 Degeneracy — 10d-R5

| Measure | Observed (max over cells) | Config threshold |
|---|---|---|
| events yielding a single sub-burst | **6.52%** | 20% |
| objects at the timestamp resolution floor (100 µs = `D1_sweep_floor_us`) | **0.0045%** | 50% |

**Does not fire.**

### 6.6 Kernel and variant consistency — 10d-R6

| Kernel | ok events | identity median | floor-only (mp=3) | merge-only (max) | dominant |
|---|---|---|---|---|---|
| 2 min | 38 | 1.0719 ms | **+0.3429 dec** | +0.2474 dec | **floor** |
| 8 min | 43 | 1.7513 ms | **+0.3209 dec** | +0.0838 dec | **floor** |
| 32 min | 49 | 1.6490 ms | **+0.2972 dec** | +0.0631 dec | **floor** |

The margin narrows at the 2-minute kernel (1.39× rather than 7.17×) — the shortest window
produces the most `ok=False` intervals (26.4% at interval level, §5.2) and the most
fragmented runs, so there is more for a merge to join. The ordering does not change.

**The floor dominates at every kernel. Does not fire.** The variant axis cannot move the
objects, only their labels — 10c computes sub-bursts once per `(event, kernel)` and
cross-joins each variant's segment/anchor context, and 10d does the same. Chart 09 panel 3
shows segment membership changing under the variant, not the decomposition changing.
Three of 56 events change segment with the variant: CELH 2020-08-06 and OST 2024-06-13 are
`rth` at 1.25/1.30 and `evening` at 1.35; CODX 2020-03-11 is `premarket` at 1.25 and `rth`
at 1.30/1.35.

### 6.7 Count versus print count — T5e, descriptive only, no gate

| Version | Spearman | log-log slope | n | Source |
|---|---|---|---|---|
| **10d** (identity cell, kernel 8) | **0.3986** | **0.5548** | 43 | this phase |
| v4 | 0.8748 | 0.9224 | 90 | `v4_t5_t6_summary.json /t5_arm_a_test/pooled` |
| v3 | 0.2772 / 0.3531 | 0.2605 / 0.1849 | 83 / 98 | `v3_t2_t4_summary.json /t4_arm_a_test/pooled` |
| v1 Arm A | 0.96 | 0.85 | — | `results/phase_10/REPORT.md` line 127 |

**Retired as a hard stop at 10c. Nothing here can fail.** A positive relation is expected —
a bigger, longer, more active event mechanically produces more sub-bursts under any
definition.

**Two attribution caveats, recorded rather than smoothed over.** (1) The **v1 pair exists
only in `REPORT.md` prose**; no committed JSON artifact under `results/phase_10/artifacts/`
carries a Spearman in [0.9, 1.0]. It is quoted with that provenance and was not re-derived.
(2) **The cohorts differ** — v1/v3/v4 ran a 100-event cohort, 10c/10d the 56-event dev
sample — so these are not like-for-like.

---

## 7. The counterfactual applicability gate — T3, reported, applied nowhere

`t3_void_counterfactual.parquet`, `t3_summary.json` · **chart 02**

Reported over the **168 distinct `(event, kernel)` cells**: the void parameter is a function
of `(event, kernel)` only, so the 504-row cell artifact holds 168 distinct values and a
per-variant report would triple-count.

**Void at the argmax-void trough, `ok` cells:**

| Kernel | n | min | q25 | median | q75 | max |
|---|---|---|---|---|---|---|
| 2 min | 38 | 0.209 | 0.708 | 0.882 | 0.985 | 1.000 |
| 8 min | 43 | 0.296 | 0.686 | 0.893 | 0.994 | 1.000 |
| 32 min | 49 | 0.387 | 0.741 | 0.886 | 1.000 | 1.000 |

**Share that WOULD be declined at each candidate cutoff — none applied:**

| Cutoff | 2 min | 8 min | 32 min |
|---|---|---|---|
| 0.50 | 15.8% (6/38) | 16.3% (7/43) | 8.2% (4/49) |
| 0.60 | 21.1% (8/38) | 23.3% (10/43) | 16.3% (8/49) |
| **0.70** (v4's retired value) | **21.1% (8/38)** | **27.9% (12/43)** | **24.5% (12/49)** |
| 0.80 | 36.8% (14/38) | 41.9% (18/43) | 30.6% (15/49) |
| 0.90 | 55.3% (21/38) | 58.1% (25/43) | 55.1% (27/49) |

### 7.1 What 10c can and cannot decline — stated exactly

**10c cannot decline on void magnitude.** `config/phase_10c.json`
`/settled/D13_void_parameter/threshold` is `null`, marked *"deliberate and permanent"*: the
void parameter ranks troughs and never gates. **A decline path on peak count does exist** —
`research/phase_10c/s1_t1_subbursts.py` emits `no_threshold` when fewer than two peaks
survive the Poisson floor, or when no valid trough pair exists — **and it fired 0 of 504 on
this cohort.** `unimodal` likewise appears 0 times.

**`insufficient_context` is a different quantity and is not comparable to v4's 10/100.**
It runs 0.0%–66.7% across cells and is a **data-coverage** verdict — the centered window
held fewer intervals than the per-event derived floor, or the cell held fewer than 50 `ok`
intervals. v4's `no_threshold` is a **shape** verdict about bimodality, and its own artifact
records the reason for all 10 as *"no trough clears void cutoff 0.7"* — a rule 10c retired.
A thin window says nothing about whether a distribution is bimodal.

### 7.2 The D9 / Zaliapin tension, recorded and not resolved

D9 adopts Zaliapin's reasoning that the share of events where bimodality fails is a
**headline result**, because the whole T=0 session sits in the vicinity of the dominant
event, exactly where bimodality is known to break. 10c's argmax-void selection returns a
threshold for every cell that clears the data floor, so **a method that never declines on
shape cannot produce the share D9 calls headline.** The table above is the size of what is
not being produced. Nothing is applied and nothing is decided; whether an applicability
gate should exist is left open in D20 and on the register.

---

## 8. Causal status — T6a

`causal_audit.parquet`, `t6_causal_audit.json`. Counts read from
`results/phase_10/artifacts/v4_causal_audit.parquet`.

v4's audit holds **18 fields: 16 non-causal, 2 causal** (`detection_anchor_ns`,
`detection_segment`). **10c retired zero** of them — `stage1_digest.json`
`/v4_comparison/causal_status_vs_v4_causal_audit` records `n_retired_by_stage1: 0`,
*"window stayed centered, not trailing; causal debt unchanged, still parked for Phase 17"*.

**10d retires none either and claims none.** It adds 8 fields and **all 8 are non-causal**:
26 fields total after 10d, 24 non-causal. The reason is structural. The window is
**centered**, so every quantity downstream of the local median reads forward in time by half
a kernel; and the argmax-void threshold is a property of the completed-session histogram. A
merge tolerance and a run-length floor operate on objects that are already non-causal and
cannot make them causal. **The debt stays parked for Phase 17.**

---

## 9. Escalation check

| Row | Condition | Observed | Fired |
|---|---|---|---|
| **10d-R0** | Cooper rejects the decomposition on tape review | **43 charts in `charts/05_tape_review/`, evaluated by nobody but Cooper** | **open — Cooper's** |
| 10d-R1 | 10c's assembly spec not reconstructable | every T0b row filled from a committed artifact | no |
| 10d-R2 | control gate fails | C1–C5 all PASS | no |
| 10d-R3 | merge tolerance drives the answer | tolerance \|ρ\| 0.032 / 0.045 vs event-characteristic 0.944 / 0.399 | no |
| 10d-R4 | attribution not separable | shifts 0.3209 vs 0.0838 decades, difference **0.2370** against a 0.05 separability floor; both exceed the 0.05 negligible bound | no |
| 10d-R5 | degenerate decomposition | single-sub-burst share 6.52% (limit 20%); resolution-floor share 0.0045% (limit 50%) | no |
| 10d-R6 | attribution kernel- or variant-specific | floor dominates at all three kernels | no |
| 10d-R7 | a cutoff applied to the void parameter | **none applied anywhere**; `counterfactual_cutoffs.applied = false` in config; T3 reports only | no |
| 10d-R8 | an `ok=False` interval tested on raw `norm` | never — `_separator_admissible()` excludes those intervals from the depth test under both rules | no |
| 10d-R9 | full-table plan over `filtered_trades`/`filtered_quotes` | zero full passes; targeted per-event folder reads only | no |

**No row fired in 10d's own code. 10d-R0 is open and is Cooper's.**

---

## 10. Verification block

| Number | Script · function | Rows in → out | Reproduction |
|---|---|---|---|
| Control gate C1–C5 | `research/phase_10d/controls.py` → `c1_identity`…`c5_floor_noop` | 8 committed cells + 200 synthetic sequences → 5 verdicts | `.venv/Scripts/python.exe research/phase_10d/controls.py` |
| Waterfall, identity reproduction, break-cause | `research/phase_10d/t4_assembly.py::main` | 3,774,862 raw prints → 2,629,020 intervals → 168 cells (38 `insufficient_context`, 0 `no_threshold`, 130 `ok`) → 10,140 configs → 6,811,163 object rows | `.venv/Scripts/python.exe research/phase_10d/t4_assembly.py` |
| Void distribution, counterfactual shares | `research/phase_10d/t3_counterfactual.py::main` | 504 cell rows → 168 distinct → 130 `ok` → 5 cutoffs × 3 kernels | `.venv/Scripts/python.exe research/phase_10d/t3_counterfactual.py` |
| Break-cause by segment, per-event, timing | `research/phase_10d/t4_descriptive.py::main` | 170,722 identity objects → 130 event-kernel rows, 3 variants | `.venv/Scripts/python.exe research/phase_10d/t4_descriptive.py` |
| Attribution, R3/R4/R5/R6 | `research/phase_10d/t5_attribution.py::main` | 6,811,163 object rows → 3 reads × 3 kernels; R3 over 12 non-degenerate cells | `.venv/Scripts/python.exe research/phase_10d/t5_attribution.py` |
| Causal audit | `research/phase_10d/t6_causal.py::main` | 18 v4 fields + 8 new → 26 | `.venv/Scripts/python.exe research/phase_10d/t6_causal.py` |
| Charts 01–10 | `t2_chart.py`, `t3_chart.py`, `t4_descriptive.py`, `t4_tape.py`, `t5_charts.py` | → 10 charts + 43 tape files, all kaleido-verified | see each script's docstring |

**Config hash `c5dd2fdc`** (`config/phase_10d.json`, SHA-256 of the canonical JSON, first 8
hex). **Upstream 10c config**: `17124203` LF / `a0943e2a` raw — **not** the `998c2461` its
own digest records (§2.7).

**Pass budget over `filtered_trades` / `filtered_quotes`: zero.** All tick reads are
targeted per-event folder reads through `research/phase_10/common.py::read_event_trades`,
offsets `(0,)` only.

---

## 11. Output files

| File | Status |
|---|---|
| `prompts/phase_10d.md`, `prompts/phase_10d_spec.md`, `prompts/phase_10c_closing_note_erratum.md` | ✅ |
| `config/phase_10d.json` | ✅ |
| `research/phase_10d/assemble.py` | ✅ |
| `research/phase_10d/controls.py`, `t3_counterfactual.py`, `t4_assembly.py`, `t4_descriptive.py`, `t4_tape.py`, `t5_attribution.py`, `t6_causal.py`, `t2_chart.py`, `t3_chart.py`, `t5_charts.py` | ✅ |
| `results/phase_10d/controls/c1…c5.json`, `gate.json` | ✅ |
| `results/phase_10d/artifacts/t3_void_counterfactual.parquet`, `t3_summary.json` | ✅ |
| `results/phase_10d/artifacts/t4_break_cause.parquet`, `t4_break_cause_by_segment.parquet` | ✅ |
| `results/phase_10d/artifacts/t4_subbursts.parquet` (6,811,163 rows), `t4_cell_summary.parquet`, `t4_event_summary.parquet`, `t4_timing.parquet`, `t4_variant_context.parquet`, `t4_waterfall.json` | ✅ |
| `results/phase_10d/artifacts/t5_attribution.json` + 6 parquet siblings | ✅ |
| `results/phase_10d/artifacts/causal_audit.parquet`, `t6_causal_audit.json` | ✅ |
| `results/phase_10d/charts/01…04, 06…10` — 10/10 Kaleido-verified | ✅ |
| `results/phase_10d/charts/05_tape_review/` — 43 events, 43/43 Kaleido-verified, **270 MB, untracked and regenerable** following 10c's `s1_07_tape_review/` convention; `artifacts/t4_tape_manifest.json` is the committed record | ✅ |
| `docs/Universe-Decisions.md` — append-only, **D20** (drafted as D15) | ✅ |

---

## 12. What this phase did not do

- It did not reinstate a void cutoff, anywhere, at any task.
- It did not select a `k`, a kernel, a variant, or a grid position by results.
- It did not retire any causal debt, and does not claim to have.
- It did not characterise the duration result as good, promising, weak, or disappointing —
  D13 records that no burst timescale is established at usable precision, so there is no bar
  to compare against, and none was invented.
- It did not decide whether an applicability gate should exist. §7 measures the cost and
  applies nothing.
- It did not characterise the `insufficient_context` population, which remains open on the
  register since v4 in its `no_threshold` form.

**Open for Cooper:** the D15 → D20 renumber (§2.6); 10d-R0 on charts 05, 06 and 07.

**Carried in from 10c and NOT in this phase's prompt scope**, so untouched and still open: the
eligible-pool gap (15,299 vs D14's 20,951) and the `det_ns_*` float64 repair, both of which 10c's
`docs/Research-Library-Map.md` entry names as "carried to Phase 10d". The 10d prompt does not
mention either, and 10d did not address them.
