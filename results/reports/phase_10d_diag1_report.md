# Phase 10d — Diagnostic 1: The Boundary Through Time — Report

**Date:** 2026-08-27 · **Branch:** `phase/10d-diag1`, cut from the 10d tip (`8ee1734`)
**Config:** `config/phase_10d_diag1.json`, hash **`0879d61c`** (see §8 on why the hash needs
an explicit UTF-8 read)
**Prompt:** `prompts/phase_10d_diag1.md`
**Type:** Diagnostic. **Not a phase. It changes nothing.** No boundary rule adopted, no
parameter tuned, no cutoff applied, no decision appended, no sub-burst re-derived.
**Audience:** a fresh chat with no context.

---

## 1. What was asked, and what came back

10d eliminated assembly as the cause of the millisecond sub-burst scale. This diagnostic
tests the surviving explanation — threshold *location* — by plotting, for the first time,
**the candidates argmax-void discards**. Every chart in the programme so far has plotted
only the winner.

Four findings, in the order they answer the prompt's questions.

**1. The distribution is not bimodal. It is richly multimodal.** At 8-minute frame
resolution, **99.8% of frames carrying a boundary hold three or more surviving peaks**
(median **8**, range 2–19). Only **4 of 2,308** frames are the two-peak case the void
parameter's construction presumes. A frame therefore offers a median of **7 candidate
troughs** (q25 5, q75 9, max 18) and argmax picks one. *(Chart 03)*

**2. Candidate boundaries do reach tradeable timescales. The winners mostly do not.**
Across all kernels, **26.5% of the 66,225 candidate troughs sit at ≥ 100 ms** and 9.9% at
≥ 1 s. Restricted to the argmax winners the same shares are **6.7%** and **5.0%**.
*(Chart 01)*

**3. The coarse candidate is not the runner-up — it is rank 5 and below.** The runner-up is
coarser than the winner in **56.2%** of frames, barely better than a coin flip, and its
median location (4.544 ms) is within 2% of the winner's (4.449 ms). The coarse valleys live
further down the ladder, and median absolute location rises **monotonically with rank**:
4.4 ms at rank 0 → 28.4 ms at rank 5 → **117.7 ms at rank 6** → 153.9 ms at rank 8. At
ranks 6–8 more than half of all candidates are ≥ 100 ms. The median winner–runner-up void
gap is **0.0511**, so argmax is frequently choosing between near-ties — but between
near-ties *at the same scale*. *(Chart 04)*

**4. The boundary is neither stationary nor stable, and the movement is not the
denominator's.** See §5.

**No recommendation follows from any of this.** What boundary rule should be used is the
successor phase's question and Cooper's call.

---

## 2. Reconciliation gate — T1d

**PASS. 16 of 16 testable cells reproduced 10c's committed boundary exactly**, by float
equality rather than a tolerance.

| | |
|---|---|
| event-kernel cells built | 21 (7 events × 3 kernels) |
| cells with a committed 10c threshold | **16** |
| reproduced exactly at the full-window frame | **16** |
| cells 10c declines (`insufficient_context`), declined identically here | **5** |

The full-window frame (`frame_index = -1`) *is* 10c's per-cell computation: same centered
window, same per-interval derived floor and cell-level minimum, same bin grid, same
Poisson-floor peak rule, same `envelope_boundary`. **D1-R1 did not fire.**

A second check runs on every frame, not just the reconciliation one. 10c's
`envelope_boundary` returns the argmax only, so `all_troughs()` in
`research/phase_10d_diag1/t1_frames.py` enumerates the same loop and keeps the whole ladder
— and is **asserted equal to 10c's own function at the top of the ladder on every one of
the 9,605 frames that carry a boundary.** The enumeration is verified against the committed
code, not assumed to match it.

---

## 3. Frames

| Kernel | frames/event | step | window | frames | `ok` | `thin` | `no_threshold` |
|---|---|---|---|---|---|---|---|
| 2 min | 3,841 | 0.25 min | 2 min centered | 15,364 | 42.9% | **57.0%** | 0 |
| 8 min | 961 | 1 min | 8 min centered | 4,805 | 48.0% | **51.9%** | 2 |
| 32 min | 241 | 4 min | 32 min centered | 1,687 | 41.4% | **58.6%** | 0 |

Totals: 21,877 frames (21,856 stepped + 21 full-window), 9,605 carrying a boundary, 66,225
candidate troughs. **D1-R3 did not fire** — the 4,000-frame cap never binds, by design
(§7). Runtime 13 s.

**Slightly over half of all kernel-width frames are `thin`** — fewer than 30 in-window
intervals, so a 0.1-decade histogram cannot support the Poisson-floor peak rule. Those
frames are carried, labelled, and given **no ladder and no fallback boundary**, per the
programme's decline-rather-than-invent convention. The share is strongly event-dependent at
kernel 8: SOS 100% `ok`, ZENA 72%, AMCX 41%, AEHL 26%, **USEG 0.9% (9 frames of 961)**.
This is a direct consequence of choosing the kernel width as the frame window (§7) and it
is a finding about the data, not a defect: at RTH print densities an 8-minute window simply
does not hold enough intervals to shape a histogram.

---

## 4. The candidate ladder

### 4.1 Reach — does any candidate reach a tradeable timescale?

Pooled across all three kernels, n = 66,225 candidates / 9,621 winners:

| At or above | any candidate | argmax winner |
|---|---|---|
| 1 ms | 74.16% (49,022) | 63.99% (6,146) |
| 10 ms | 47.04% (31,094) | 21.20% (2,036) |
| **100 ms** | **26.53% (17,537)** | **6.73% (646)** |
| 1 s | 9.90% (6,547) | 5.03% (483) |
| 10 s | 1.32% (871) | 1.04% (100) |

**The reference lines are read-off guides, not criteria.** D13 records that no burst
timescale is established at usable precision, so nothing is compared against them for
pass/fail.

### 4.2 By ladder rank, kernel 8 min

| Rank | n | median | q25 – q75 | median void | ≥ 100 ms | ≥ 1 s |
|---|---|---|---|---|---|---|
| **0 (winner)** | 2,308 | **4.449 ms** | 0.99 – 14.4 ms | 0.893 | 9.2% | 7.7% |
| 1 | 2,304 | 4.544 ms | — | 0.782 | 8.2% | 4.3% |
| 2 | 2,275 | 5.048 ms | — | 0.704 | 13.8% | 5.3% |
| 3 | 2,144 | 6.730 ms | — | 0.641 | 22.2% | 8.2% |
| 4 | 1,911 | 11.916 ms | — | 0.597 | 31.8% | 10.2% |
| 5 | 1,589 | 28.374 ms | — | 0.555 | 40.7% | 16.3% |
| **6** | 1,269 | **117.695 ms** | — | 0.523 | **51.7%** | 22.0% |
| 7 | 980 | 152.986 ms | — | 0.493 | 53.8% | 24.7% |
| 8 | 661 | 153.887 ms | — | 0.488 | 53.6% | 27.5% |

Void falls smoothly with rank (0.893 → 0.488) while absolute location rises by a factor of
35. The ladder is a **gradient, not a two-horse race**.

---

## 5. Stationary or shifting — T4c

**Not stationary, not stable, and the movement is not the normalization denominator's.**

Because `log₁₀(absolute boundary) = log₁₀(local median) + normalized boundary`, the two
sources of movement separate exactly. Pooled over 8-minute `ok` frames (n = 2,308):

| Quantity | sd (decades) |
|---|---|
| absolute boundary, log₁₀ | 1.257 |
| local median, log₁₀ — the denominator | **0.742** |
| normalized boundary — the position on the shape | **1.466** |

| Variance share of the absolute boundary | |
|---|---|
| local median | 34.8% |
| normalized position | **135.9%** |
| cross term (2·cov) | **−70.7%** |

**The position on the shape moves about twice as much as the denominator does**, and the
two partly cancel — which is why the absolute track in chart 01 looks calmer than either of
its components. Per event at kernel 8: sd(normalized) 1.28–1.65 decades against
sd(local median) 0.57–0.86, in every event with more than 9 frames.

**The movement is switching, not drift.** Consecutive frames share **87.5%** of their data
(8-minute window, 1-minute step). Even so, the winner moves by:

- **more than 0.5 decades between 27.3%** of adjacent frame pairs;
- **more than 1.0 decade between 17.5%** (n = 2,303 adjacent pairs).

Per event: AMCX 40.2%, ZENA 31.0%, AEHL 30.2%, SOS 18.9% of adjacent pairs move >0.5
decades. A boundary that relocates by a factor of ten between two windows sharing seven
eighths of their intervals is not tracking a slowly-moving shape — it is switching between
candidates. §4 shows there are a median of 8 candidates to switch between.

**Caveat, stated so it cannot be misread as stability:** USEG contributes 9 `ok` frames of
961 and shows sd(normalized) = 0.000 and 0% hops. That is nine frames, not a stable event.

---

## 6. Cross-kernel — T2e, a partial read and labelled as one

Three kernels, not the wide log-spaced grid 10c deferred. **Three points cannot separate a
structural interval from a smooth scaling**, and this table is not offered as if they could.

| Kernel | `ok` frames | winner median | q25 – q75 | local median | median peaks | candidates ≥ 100 ms |
|---|---|---|---|---|---|---|
| 2 min | 6,598 | 1.420 ms | 0.47 – 5.52 ms | 73.845 ms | 8 | 25.9% |
| 8 min | 2,308 | 4.449 ms | 0.99 – 14.36 ms | 87.451 ms | 8 | 27.5% |
| 32 min | 699 | 5.356 ms | 1.02 – 22.60 ms | 70.319 ms | 8 | 29.0% |

Two observations, both descriptive. The winner's median rises **3.8×** across a **16×**
range of kernel — a log-log slope of about **0.48**, so neither flat (which would read as a
structural interval) nor 1:1 with the window. And the local median does **not** scale with
the kernel at all (73.8 → 87.5 → 70.3 ms, non-monotone), so the winner's rise is not the
denominator moving. The median mode count is 8 at every kernel.

---

## 7. Choices this diagnostic had to make, and why

**Frame window = the kernel width.** The prompt fixes the frame *step* (kernel/8) but not
the window. Two committed sources state the window as `[t − kernel/2, t + kernel/2]`: 10c's
T1 local-median definition, and the docstring of `research/phase_10c/s1_t6_animation.py`.
That is what is used here. Its cost is the 52–59% `thin` share in §3, which is reported
rather than engineered away by widening the window.

**Bin grid = the event's full-session grid, fixed across frames.** It is 10c's own grid, so
the full-window frame reproduces 10c exactly (that is the T1d gate); and a grid recomputed
per frame would make a stationary distribution appear to move, which is the defect T3b bans
for the axis range.

**Frame cap 4,000, set above the binding point deliberately.** The natural count is 3,841 at
the 2-minute kernel over a 16-hour extended session. A cap that silently coarsened the
2-minute kernel would degrade exactly the kernel where the boundary moves fastest.

**Event subset: deterministic, no seed.** Seven events chosen by argmin/argmax over
committed artifacts with alphabetical tie-break — lowest / median / highest activity (913 to
570,573 prints), shortest and longest identity-cell sub-burst duration (0.107 ms to 466 s),
most `insufficient_context` cells, and evening coverage. All four segments present. Selected
and committed at `404c51f` **before any frame was computed**.

---

## 8. Discrepancies found, posted rather than resolved silently

### 8.1 10c *did* build the animated histogram

The prompt describes the animated histogram as "the instrument 10c specified and deferred".
10c built it: **T6a–c prototype on 4 events in both candidate layouts, then T6d on the full
56-event dev sample** — `results/phase_10c/charts/s1_06_animation_full/` (113 files, 8.3 MB),
manifest `results/phase_10c/artifacts/s1_t6d_manifest.json`.

### 8.2 The layout question was already decided, by Cooper

The prompt's T3d says "10c deferred this choice; make it once, on evidence". That manifest
records `layout: combined_comparative_3_panel`, **`layout_chosen_by: "Cooper (T6c)"`**. The
choice was made. What Cooper has *not* seen is that layout **with the candidate-ladder panel
added**, which is what §9 reports on instead.

### 8.3 What 10c's animation does not do — and its own docstring says it does

This is why the diagnostic's core content still stands. `s1_t6_animation.py`'s docstring
states the frame window is `[t − kernel/2, t + kernel/2]` and that "peaks are freshly
detected per frame (Poisson floor, same as T1)". Neither is what the code does:

- `build_frames()` uses `win_ns = (session_span / n_frames) * 1.5` — about **60 minutes**
  against an 8-minute kernel, roughly 7.5× the stated width;
- it returns `{t, centers, dens, n}` only. **No peak detection happens per frame at all**,
  and the event's single global threshold is drawn as a fixed reference line.

So 10c's committed animation showed the density moving against a fixed line. It did not show
the candidate ladder, which is this diagnostic's subject.

### 8.4 A third hash-reproducibility defect in this lineage

`config/phase_10d_diag1.json` hashes to **`0879d61c`** read as UTF-8 and to `2e15b95e` read
under the Windows default cp1252, because its `_why` strings contain non-ASCII characters.
Every script here reads it with an explicit encoding, so `0879d61c` is the canonical value.
`config/phase_10d.json` is pure ASCII and is unaffected — which is why 10d's `c5dd2fdc` was
stable. This follows 10c's two hash defects recorded in `results/phase_10d/REPORT.md` §2.7:
`cfg_hash()` hashing raw line-ending-sensitive bytes, and Stage 1's recorded value being
stale by one commit. **Config hashes in this programme are only reproducible if both the
encoding and the line endings are pinned.**

---

## 9. Animation layout — T3d, decided on evidence

Both readings were built on the two pre-registered events.

| | Layout A (per kernel) | Layout B (combined) |
|---|---|---|
| files | 3 | 1 |
| size, AMCX | 1.90 MB | **1.23 MB** |
| size, ZENA | 2.12 MB | **1.39 MB** |
| sliders | 3 | **1** |
| frames retained | **193 native per kernel** | 121, index-resampled |
| x-axes | 1 per file | **3, and they cannot be shared** |

**The decisive fact is that the three kernels do not share a bin grid.** Each cell's grid is
derived from its own full-session normalized range, so for AMCX the grids are
[−3.75, 4.45] over 83 bins, [−3.85, 3.95] over 79, and [−3.45, 4.05] over 76; for ZENA, 86 /
88 / 90 bins over three different ranges. Layout B therefore needs three separate x-axes and
its panels **cannot be compared bin-for-bin by eye** — which is the one thing a combined
layout is for. It also resamples 193 native frames down to 121 to share a slider, losing 37%
of the 8-minute kernel's resolution.

Layout A costs three files and three sliders but preserves every kernel's native grid and
native frame set. **Recorded for whoever builds the next one; nothing is changed here, and
Cooper's T6c choice stands unless he revisits it.**

---

## 10. Causal status

**NON-CAUSAL throughout, and nothing is retired.** The window is centered, so every frame
reads forward in time by half a kernel; the ladder and the winner are properties of a
completed window. No output here is a detector, a signal, or an operating point. 10c retired
zero of v4's 16 non-causal fields, 10d retired none, and this diagnostic retires none. The
debt remains parked for Phase 17.

---

## 11. Escalation

| Row | Condition | Observed | Fired |
|---|---|---|---|
| **D1-R1** | frame pipeline does not reproduce 10c's boundary | 16/16 exact | **no** |
| **D1-R2** | any boundary rule adopted, parameter tuned, cutoff applied | none — reference lines are read-off guides and enter no computation | **no** |
| **D1-R3** | frame cap binds above the config share | cap 4,000 never binds; 0.0% | **no** |
| **D1-R4** | full-table pass over `filtered_trades`/`filtered_quotes` | zero; targeted per-event folder reads only | **no** |

---

## 12. Verification block

| Number | Script · function | In → out | Reproduction |
|---|---|---|---|
| Frames, ladders, T1d gate | `research/phase_10d_diag1/t1_frames.py::main` | 7 events × 3 kernels → 21 cells → 21,877 frames → 66,225 candidates; gate 16/16 | `.venv/Scripts/python.exe research/phase_10d_diag1/t1_frames.py` |
| Charts 01–05 | `t2_charts.py::main` | 21,856 stepped frames → 5 charts | `…/t2_charts.py` |
| Animations, T3d | `t3_animation.py::main` | 7 events → 5 built, 2 declined; 8 layout files | `…/t3_animation.py` |
| All tables, T4c verdict | `t4_tables.py::main` | 9,605 `ok` frames → `t4_tables.json` | `…/t4_tables.py` |

Config hash **`0879d61c`** (UTF-8). Upstream asserted: 10c config `17124203` LF /
`a0943e2a` raw CRLF — corroborated independently by `s1_t6d_manifest.json`, which records
`a0943e2a`. **Zero full-table passes.** Charts 5/5 Kaleido-verified.

---

## 13. Output files

| File | Status |
|---|---|
| `prompts/phase_10d_diag1.md`, `config/phase_10d_diag1.json` | ✅ |
| `research/phase_10d_diag1/{t1_frames,t2_charts,t3_animation,t4_tables}.py` | ✅ |
| `results/phase_10d_diag1/artifacts/t1d_reconciliation.json`, `t1_waterfall.json`, `t4_tables.json`, `t2_chart_manifest.json`, `t3_animation_manifest.json` | ✅ |
| `results/phase_10d_diag1/artifacts/t1_frames.parquet`, `t1_troughs.parquet`, `t1_reconciliation.parquet`, `t1_frame_steps.parquet` | ✅ (gitignored, regenerable per §12) |
| `results/phase_10d_diag1/charts/01…05` — 5/5 Kaleido-verified | ✅ |
| `results/phase_10d_diag1/charts/06_animation/` — 5 event animations + 8 layout files, 77 MB | ✅ **untracked**, manifest is the record, per 10c's `s1_06_animation_full/` convention |
| `docs/Universe-Decisions.md` | **not touched** — diagnostics record no decision |

---

## 14. What this diagnostic did not do

It adopted no boundary rule, tuned no parameter, applied no cutoff, re-derived no sub-burst,
and appended no decision. It did not characterise any result as good or bad. It did not
decide whether the coarse candidates at rank 5+ are the right object — that is a choice
about what is being measured, and it belongs to Cooper and to whatever phase follows.

**10d-R0 remains open and is unaffected by anything here.**
