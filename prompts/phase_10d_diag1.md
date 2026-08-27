# Phase 10d — Diagnostic 1: The Boundary Through Time

**Date:** 2026-08-27
**Branch:** `phase/10d-diag1`, cut from the 10d tip
**Baseline:** Phase 10d as posted (attribution complete, 10d-R0 open)
**Type:** Diagnostic. **Not a phase.** Follows the `prompts/phase_10b_diagnostic_1.md` precedent.
**Objective:** Show the locally-normalized log-interval distribution evolving across the session, with
**every candidate trough** and the chosen boundary plotted as they move — in both normalized and
absolute units.
**Primary success metric:** Cooper can answer, from the charts, whether the boundary is stable, and
whether any candidate boundary ever reaches a tradeable timescale.

---

## 1. Why this exists now

10d eliminated assembly as the cause of the millisecond scale. The merge moved duration +0.0838
decades — 21% on a quantity that needs orders of magnitude — and the break-cause census found 99.24%
of run breaks are real above-threshold gaps, not data-quality artifacts. There was no fragmentation to
repair.

**That leaves threshold location as the surviving explanation, and it has a specific form worth
testing.** Void medians of 0.88–0.89 say argmax-void is finding a *very* well-separated boundary,
confidently, every time. Order fragmentation is an extremely tight, extremely distinct cluster — so if
the distribution carries three modes (fragmentation, real bursts, background), the deepest valley is
plausibly the fragmentation/rest boundary, and argmax-void faithfully picks it. **A shallower but
coarser valley further right would never win an argmax and would be invisible in every chart produced
so far**, because every chart so far plots only the winner.

This diagnostic plots the losers.

It also builds the instrument 10c specified and deferred — the animated histogram — and takes a
partial read on the "threshold location versus window size" question deferred with it, at the three
committed kernels rather than the wide log-spaced grid.

---

## 2. Constraints

- **This changes nothing.** No threshold rule is adopted, no parameter is tuned, no gate is applied,
  no decision is appended, no sub-burst is re-derived. **If a task appears to require selecting a
  boundary rule, stop and post.** The output is pictures and the tables behind them.
- **10c's method is reproduced exactly, not re-specified.** Centered clock-time window; the three
  kernels with D5 = 8 min primary; the Poisson-floor peak-survival rule; argmax void across all
  troughs with no cutoff; the per-interval data floor and cell-level minimum with
  `insufficient_context` carried. Recompute the rolling histogram at frame resolution using the same
  code path as `s1_t1_subbursts.py` — **import it, do not reimplement it.** Any divergence from 10c's
  committed per-cell boundary at the corresponding full-window frame is a hard stop.
- **Non-causal and labelled as such.** The window is centered; every frame reads forward in time by
  half a window. This is an offline diagnostic and no output may be described as a detector, a signal,
  or an operating point. Carry the causal tag; retire nothing.
- **D4 stands.** Tick-derived throughout. **Pass budget over `filtered_trades` / `filtered_quotes` is
  zero** — targeted per-event folder reads only.
- **Cohort frozen**, hash asserted. Segment stratification across all four segments.
- **Every tunable in `config/phase_10d_diag1.json`** with a `_why`: event subset and its selection
  rule, frame step, frame cap, reference lines, chart dimensions, seeds.
- **D14 — offline.** numpy, scipy, plotly, pyarrow, pandas confirmed present at 10d T0c. Frame-based
  HTML via plotly animation frames or a slider, per 10c's implementation note — **no video file, no
  new dependency.**
- **Write scope, escalation row 13 as amended:** `prompts/`, `config/`, `research/`, `results/`. **No
  append to `docs/Universe-Decisions.md`** — diagnostics record no decision.
- **Evidence Standard.** No finding without its chart. Every statistic carries its n. **No
  recommendations.** Describe the picture.

---

## 3. Tasks

### T0 — Preconditions

- [ ] **T0a** — Verify state from git and the filesystem: 10d tip, tree clean, 10d artifacts present
      and hash-matched. **Hard stop if the tree is dirty.**
- [ ] **T0b** — Pre-register the event subset in config and commit it **before computing anything**:
      a small set spanning the activity range and **all four segments**, including at least one
      `insufficient_context`-heavy event and at least one event from the short-duration and the
      long-duration ends. State the selection rule. **Chosen after seeing the frames is not
      pre-registration.**
- [ ] T0c — Read-only. Post the state table and the subset with its rule. Commit config.

### T1 — Frame construction

- [ ] **T1a** — For each event in the subset, at each kernel, step a frame index across the session.
      **Frame step = kernel duration / 8** (1 min at the 8-min kernel), subject to a config frame cap;
      if the cap binds, widen the step and **record the actual step and frame count per event**.
- [ ] **T1b** — At each frame, recompute through 10c's code path: the local normalized log-interval
      histogram, the surviving peaks, **every candidate trough with its void value**, and the argmax
      winner. Persist all of it — the candidate ladder is the point of this diagnostic, not a
      by-product.
- [ ] **T1c** — At each frame also record: the local median interval (the normalization denominator
      itself), the count of surviving peaks, the in-window print count, and the `ok` share.
- [ ] **T1d — Reconciliation gate.** At the frame whose window matches 10c's per-cell computation,
      the boundary must reproduce 10c's committed value. **Any divergence is a hard stop** — it means
      the frame pipeline is not the method.
- [ ] T1e — Commit `t1_frames.parquet`.

### T2 — The static boundary track *(this is the chart that scales)*

Static, one per event, every event at D5 = 8 min. **Read this before the animation** — the pattern is
found here and understood there.

- [ ] **T2a — Absolute-units track.** Every candidate trough plotted against session time in
      **absolute interval units** (`local_median × 10^boundary`), the argmax winner highlighted, the
      losers shown as a scatter cloud sized or coloured by void. **Reference lines at 1 ms, 10 ms,
      100 ms, 1 s, 10 s.** The question this answers directly: **does any candidate boundary, winner
      or not, ever reach a tradeable timescale?**
- [ ] **T2b — Normalized-units track.** The same in decades of normalized log interval. **Both are
      required and they are not redundant:** the local median moves through the session, so a boundary
      that is flat in normalized terms is moving in absolute terms, and vice versa. **A static
      per-event chart cannot show that and every chart produced so far has been static.**
- [ ] **T2c — Mode-count trace**, on the same time axis: surviving peaks per frame. Two versus three
      or more, through the session. **This is the multimodality question answered directly rather than
      inferred.**
- [ ] **T2d — Runner-up trace.** The second-best trough by void, plotted alongside the winner in both
      unit systems. **If the runner-up sits consistently at a coarser and more plausible scale, that is
      the finding this diagnostic exists to surface.** Report the winner–runner-up void gap
      distributed — a narrow gap means argmax is choosing between near-ties.
- [ ] **T2e — Cross-kernel overlay**, subset events only: the winner's absolute track at 2, 8 and 32
      min on one axis. **Partial read on 10c's deferred "threshold location versus window size"
      question** — three points, not the wide grid, and labelled as partial. If the absolute boundary
      is roughly flat across kernels it is a structural interval; if it scales with window size it is
      landing wherever the local median puts it.
- [ ] T2f — Charts 01–05. Commit.

### T3 — The animation

- [ ] **T3a** — Frame-scrubbable HTML per subset event at D5 = 8 min: slider or animation frames, no
      video. Panels on one synced time axis, extending the existing tape-review grammar rather than
      inventing a new one:
      **top** — tape (price and prints);
      **middle** — local median interval through time, the normalization denominator;
      **bottom** — the histogram at frame *t*, with surviving peaks, **all candidate troughs annotated
      with their void values**, and the winner marked;
      **inset or fourth panel** — the T2a absolute track with a playhead at frame *t*.
- [ ] **T3b** — Fix the histogram's x-range and y-range across all frames of an event. **A rescaling
      axis makes a stationary distribution look like it is moving** and would make the whole animation
      unreadable as evidence.
- [ ] **T3c** — Annotate each frame with clock time, time relative to the D7 detection anchor **with
      its poll interval**, in-window print count, and `ok` share.
- [ ] **T3d** — Multi-kernel layout: produce **both** readings on two subset events — one animation
      per kernel, and a single animation with the three kernels' histograms panelled together — and
      report which is more legible. 10c deferred this choice; make it once, on evidence, and record it
      for whoever builds the next one.
- [ ] T3e — Commit. Tape-scale HTML follows 10c's untracked convention with a committed manifest.

### T4 — Report

- [ ] **T4a** — Tables behind every chart: boundary position distributed over frames per event, in
      both unit systems; winner–runner-up void gap; mode-count shares; cross-kernel comparison; frame
      step and count per event.
- [ ] **T4b** — Write `results/phase_10d_diag1/REPORT.md`. **Describe what the pictures show. Draw no
      conclusion about what boundary rule should be used** — that is the successor phase's question and
      Cooper's call.
- [ ] **T4c** — State explicitly whether the histogram's shape is **stationary or shifting** across the
      session, per event and pooled, and whether the boundary tracks the shape or jumps between modes.
      **Both answers are useful; do not soften a null.** If the shape is stationary and the boundary is
      stable, a single per-event threshold is the right object and the scale problem lives entirely in
      which valley wins.
- [ ] T4d — Digest. Commit. **Post and stop.**

---

## 4. Escalation

| # | Condition | Action |
|---|---|---|
| **D1-R1** | Frame pipeline does not reproduce 10c's committed boundary at the matching window (T1d) | Hard stop — the pipeline is not the method |
| **D1-R2** | Any boundary rule adopted, any parameter tuned, any cutoff applied | Hard stop — this diagnostic changes nothing |
| **D1-R3** | Frame cap binds on more than a config-stated share of events | Post; widen the step and record it. Not a stop |
| **D1-R4** | Any full-table pass over `filtered_trades` / `filtered_quotes` | Standing escalation row 4 |

No other escalation criteria. **A diagnostic cannot fail on its findings** — every result it can
produce is information.

---

## 5. Chart Contract

| # | File | Question | Reading it |
|---|---|---|---|
| 01 | `01_boundary_track_absolute.html` | **Does any candidate boundary ever reach a tradeable timescale?** | Every candidate in absolute units against time, winner highlighted, reference lines at 1 ms → 10 s. **If nothing reaches 100 ms at any point in any event, this distribution has no tradeable-scale valley and that is a program-level finding** |
| 02 | `02_boundary_track_normalized.html` | Is the boundary stable in normalized terms? | Flat here but moving in 01 means the local median is doing the work, not the shape |
| 03 | `03_mode_count.html` | How many modes are actually present, through time? | Two versus three-or-more per frame. Three-or-more with a coarse runner-up is the multimodality hypothesis confirmed |
| 04 | `04_winner_vs_runnerup.html` | Is argmax choosing between near-ties? | Narrow void gap plus a coarse runner-up means the rule is discarding the useful boundary on a small margin |
| 05 | `05_cross_kernel.html` | Structural interval, or an artifact of window size? | Flat across kernels = structural. Scaling ~1:1 with window = landing wherever the local median puts it |
| 06 | `06_animation/` | What is the distribution actually doing? | Per-event, frame-scrubbable. **Fixed axes across frames** |

---

## 6. Reporting

On completion, post: the reconciliation result (T1d); the stationary-or-shifting verdict per T4c; the
boundary-track tables in both unit systems; the winner–runner-up gap distribution; mode-count shares;
the cross-kernel comparison; the animation-layout finding from T3d; frame steps and counts; output
file table; verification block; commit list.

Every claim cites its chart. Every statistic carries its n and its kernel. **No recommendations.**

---

## 7. Approval Gate

**Nothing here changes Phase 10d, and 10d-R0 remains open and unaffected.** On completion, post and
stop. Cooper reads charts 01, 03 and 04 and decides what, if anything, the next phase is.
