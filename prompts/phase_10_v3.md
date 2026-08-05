# Phase 10 (v3) — Sub-Burst Decomposition

**Date:** 2026-08-04
**Branch:** `phase/10`
**Baseline:** `phase-9-approved`
**Supersedes:** `prompts/phase_10_v2.md` and `prompts/phase_10_v2_r1.md`
**Objective:** Determine whether the T=0 intensity process has a characteristic clustering scale, and if it does, decompose each event into a slowly-varying envelope plus sub-bursts riding on it.
**Primary success metric:** A sub-burst decomposition Cooper accepts on visual review against the tape, whose sub-burst count is demonstrably **not** a function of how many prints the event has.

---

## D8 — Sub-burst structure, measured against the event's own envelope

*(For appending to `docs/Universe-Decisions.md`. Append-only per the amended escalation row 13.)*

**Decision:** Phase 10 measures sub-burst structure within the T=0 session, using the event's own slowly-varying intensity as the reference level. D6's abandonment of within-session structure is reversed. D6's diagnosis is retained.

**What D6 got right and what it got wrong.** D6 correctly established that no quiet state exists on T=0 — the session runs a median 78× above flanking baseline throughout, so there is nothing to threshold against. That finding stands. D6 then drew the wrong conclusion from it: that within-session structure should be abandoned in favour of one global peak and one decay number. That discarded the structure the trading thesis depends on. An event-level decay figure cannot inform intraday entry or exit; sub-burst structure can.

**The actual defect, common to all four prior attempts.** Every method so far compared a fast-varying arrival rate against a reference level that does not describe the data:

| Attempt | Reference level | Failure |
|---|---|---|
| Arm A (Kleinberg) | session mean rate, constant | rate varies by orders of magnitude within the session; burst count correlated **0.96** with print count |
| Arm B | flanking-day, time-of-day matched | too thin to estimate — median 2.8 prints/min, 73/100 `baseline_partial` |
| Hawkes (prior project) | constant exogenous baseline | branching ratio pinned at criticality, a documented misspecification signature |
| v2 | none — one global peak | discarded within-session structure entirely; decay timescale ill-posed, four rows fired |

**The reference level must track the event.** Sub-bursts are excursions above the event's own envelope, not above a constant. This repairs Arm A's defect at the root: burst count correlated with print count because a fast rate was compared to a fixed level, so more prints produced more crossings. A reference that follows the event removes that mechanism rather than tuning around it.

**Conditional on a scale separation existing.** Envelope-and-excursion is only well-posed if the intensity process has a characteristic clustering scale — a slow band for the envelope, a fast band for the sub-bursts, and a gap between. If the process is self-similar, no principled envelope bandwidth exists and any choice manufactures the sub-bursts it then finds. That is Arm A's failure in new clothing. **T1 tests this and is a hard gate.**

**Consequences:**
- **(a)** v2's one-global-peak framing and T3c decay timescale are withdrawn.
- **(b)** v2 artifacts are superseded, not deleted, and retained as the evidentiary record. Renamed `*_v3_superseded` with a header pointing here.
- **(c)** These v2 results survive and carry forward: the detection anchor (110/110 exact against Phase 8, reference deviation 0.000e+00); detection-to-peak (median ~1,976s, poll-grid ratio 1.010); the 28% negative share; the segment split (premarket 0% negative, regular-hours 40%); the adaptive intensity estimator.
- **(d)** Detection segment becomes a **stratification variable from the start**, not a discovery. Premarket and regular-hours events differ by three orders of magnitude on v2's decay statistic and 40 points on negative share.
- **(e)** If T1's gate fails, D5's premise is wrong — no burst timescale exists to anchor downstream horizons to — and Phases 11, 13, 14, 16 and 17 re-anchor to detection, clock time, or price-path events. That is a first-order program finding, not a phase failure.

---

## Context & constraints

- **Cohort frozen.** v1 manifest, content hash `e1a0ac73a79aa573`, 114 events (50 dev v4 primary + 50 activity extension + 8 row-cap census + 6 sidecar), seed 42. Analysis cohort 100. Row-cap and sidecar carried, labeled, never pooled. Assert the hash at T0.
- **Detection anchor reused, not re-derived.** D7's rule and the R1 artifacts are validated and stand.
- **Everything stratified by detection segment** — premarket / regular-hours / after-hours — from T1 onward. Pooled figures may be reported alongside, never instead.
- **Pass budget over `filtered_trades` / `filtered_quotes` is zero.** Targeted folder reads only, per the v1 T0d equivalence proof.
- **D4 stands.** All quantities tick-derived. No spine numeric on any computation path.
- **Phase 13 boundary.** Inter-trade time is an input and a display axis. This phase does not produce interval distributions or noise-floor characterization as findings.
- **Offline, not a detector.** Envelope estimation is non-causal by construction. No output may be described as a detector, entry signal, or operating point.
- **Escalation row 13 as amended by R1:** writes permitted to `prompts/`, `config/`, `research/phase_10/`, `results/phase_10/`, plus **append-only** to `docs/Universe-Decisions.md` and `docs/Research-Library-Map.md`.
- Standard §§9–12 apply in full. Every statistic carries its n. Every claim cites its chart.

---

## Tasks

- [ ] **T0 — Preconditions, supersession, config**
  - [ ] T0a — Assert cohort content hash `e1a0ac73a79aa573`; confirm `phase-9-approved`; confirm R1 detection anchor artifacts present.
  - [ ] T0b — Commit `prompts/phase_10_v3.md` before any other work.
  - [ ] T0c — Append D8 to `docs/Universe-Decisions.md`. Append-only, zero deletions.
  - [ ] T0d — Supersede v2: rename v2 report and digest to `*_v3_superseded`, header pointing to D8 and naming what survives per D8(c). **Do not delete v2 artifacts.**
  - [ ] T0e — **Author and commit `config/phase_10_v3.json`.** Must carry: the counting-window ladder; gate thresholds; envelope estimator and its scale; excursion definition; both observables; segment strata; every failure threshold; chart caps; runtime ceilings. Propose and justify anything this prompt does not pin.
  - [ ] T0f — Commit.

- [ ] **T1 — Scale-separation gate**

  **This gate decides whether the rest of the phase is well-posed. Run it first and stop on failure.**

  Compute the **Allan factor** and the **Fano factor** as functions of counting-window duration, per event, swept across a dyadic ladder spanning at least four orders of magnitude. Both are computed directly on the point process — **no intensity estimation, no smoothing bandwidth, no threshold.** That independence is the point: the gate must not inherit the machinery it gates.

  - **Fano factor** F(T) = variance-to-mean ratio of counts in non-overlapping windows of duration T. Homogeneous Poisson gives F(T) = 1 flat.
  - **Allan factor** A(T) = mean squared difference of successive window counts, over twice the mean count. **This is the primary statistic** because it tolerates a slowly-varying underlying rate — which is exactly the envelope being separated out. Fano is reported alongside and will be inflated by the trend; that inflation is expected and is not itself evidence of clustering.

  Read the curves on log-log:
  - **Straight power law, no knee, across the ladder** → self-similar, no characteristic scale → **gate fails.**
  - **Knee or plateau** → a characteristic clustering scale exists, and **its location is the envelope/sub-burst boundary — derived, not chosen.**

  - [ ] T1a — Curves per event, per observable, per segment.
  - [ ] T1b — Knee detection: fit and report the knee location with an interval, or report its absence. State the method and justify it in `decisions_log`.
  - [ ] T1c — **Segment consistency.** Premarket and regular-hours must be evaluated separately. If their knees are incompatible, one envelope scale does not serve both — that is failure row 5, not something to average over.
  - [ ] T1d — Evaluate gate rows 6 and 7. **If either fires, hard stop. Commit, post the curves, do not proceed to T2.**
  - [ ] T1e — Commit.

- [ ] **T2 — Envelope estimation**
  Only if T1 passes. The envelope scale comes from T1's knee, per segment. It is **not** a free parameter and **not** swept independently of the gate.
  - [ ] T2a — Estimate the slowly-varying envelope of the arrival-rate curve at the gate-derived scale, per event, per observable. Reuse the v2 adaptive nearest-neighbour estimator; do not rebuild it.
  - [ ] T2b — Report envelope sensitivity **within the interval T1 placed on the knee** — not across an arbitrary grid. If the sub-burst set is unstable inside that interval, the knee is not sharp enough to support the decomposition. Failure row 3.
  - [ ] T2c — Commit.

- [ ] **T3 — Sub-burst identification**
  - [ ] T3a — Identify excursions of the rate curve above its own envelope. Define the excursion rule in `decisions_log` with its justification. **The rule operates on the ratio of rate to envelope, never on rate against a constant** — that is the defect D8 exists to prevent.
  - [ ] T3b — Per-sub-burst: start, end, duration, print count, share of session prints, share of session move.
  - [ ] T3c — Per-event: sub-burst count, spacing, and the share of session move carried by the largest, second, third.
  - [ ] T3d — Sub-burst timing relative to the **detection anchor** and to the **event peak**, both reused from v2.
  - [ ] T3e — Commit.

- [ ] **T4 — The Arm A test**

  **This is the task that decides whether the decomposition is real.** Arm A produced beautifully stable, well-distributed burst counts that turned out to be a restatement of print count. Nothing in v1's criteria caught it.

  - [ ] T4a — Spearman correlation of sub-burst count with T=0 print count, and the log-log slope. Pooled and per segment.
  - [ ] T4b — The same against session duration and against absolute peak rate. **If print count dominates duration, the count is an artifact.**
  - [ ] T4c — Sub-burst count per unit time and per thousand prints, distributed.
  - [ ] T4d — Evaluate failure row 1. Commit.

- [ ] **T5 — Stability**
  - [ ] T5a — Observable agreement: print rate versus volume rate, per event.
  - [ ] T5b — Tie-variant agreement, per the v2 tie handling.
  - [ ] T5c — Segment-conditioned reporting of every T3 quantity.
  - [ ] T5d — Evaluate all failure rows. Report observed against threshold, pass/fail, nothing further. Commit.

- [ ] **T6 — Charts** per contract below, kaleido-verified. **Chart 07 is produced whether or not numeric rows fire** — see the note there. Commit.

- [ ] **T7 — Digest and report.** Description only. **Do not select an envelope scale, an observable, or an excursion rule; do not propose a latency budget; do not characterize results as good, promising, weak, or disappointing.** Commit; working tree clean.

---

## Pre-registered failure criteria

| # | Failure mode | Observable | Threshold |
|---|---|---|---|
| **0** | **Cooper rejects the decomposition on visual review of chart 07 against the tape** | — | **Cooper's judgment. Overrides every other row in either direction.** |
| **1** | **Sub-burst count is a restatement of print count** *(the Arm A test)* | Spearman(sub-burst count, T=0 print count); log-log slope | **Proposed: correlation ≤ 0.50 and slope ≤ 0.35.** Arm A scored 0.96 and 0.85 |
| 2 | Observable disagreement | Rank correlation of sub-burst count between print rate and volume rate | Config |
| 3 | Envelope instability within the knee interval | Sub-burst set overlap across the T1 knee interval | Config |
| 4 | Degenerate decomposition | Share of events yielding one sub-burst spanning the session, or sub-burst duration sitting at the ladder's resolution | Config |
| 5 | Segment incompatibility | Separation between premarket and regular-hours knee locations | Config |
| **6** | **No characteristic scale** *(gate)* | Allan factor is a straight power law across the ladder with no detectable knee | Config; **hard gate at T1** |
| **7** | **Gate not robust** *(gate)* | Knee location varies beyond tolerance across events within a segment | Config; **hard gate at T1** |

**Row 1 is the one that matters most.** Rows 6 and 7 gate whether the work is well-posed; row 1 tests whether the result is real. **A pass on stability rows is not evidence of correctness** — v1 proved that decisively, with all four numeric rows passing while both arms were wrong.

**If any row fires:** hard stop, commit, post observed values and charts. Do not adjust parameters to make a criterion pass. Do not reintroduce constant-reference thresholding, two-state segmentation, or Hawkes calibration — all closed by D6 and D8, and reopening any requires a numbered decision.

---

## Chart contract

| # | File | Question | Encoding | Looks like this if wrong |
|---|---|---|---|---|
| 01 | `01_scale_separation.html` | **Is there a characteristic clustering scale?** | Allan factor against counting-window duration, log-log; per-event lines behind a per-segment median; Poisson reference at 1; fitted knee with its interval marked; Fano in a second panel | A straight line across the whole ladder — self-similar, no envelope scale exists, gate fails |
| 02 | `02_envelope_examples.html` | What does the envelope look like against the rate? | Rate curve and fitted envelope overlaid, log y, a handful of events spanning the activity range, one row per segment | Envelope tracking every wiggle, or flat through obvious structure |
| 03 | `03_subburst_count.html` | How many sub-bursts does a session have? | Distribution of per-event sub-burst count, per segment, per observable | All mass at 1, or a spike at one value |
| 04 | `04_subburst_count_vs_prints.html` | **Is the count real or a print-count artifact?** *(row 1)* | Sub-burst count against T=0 print count, log-log scatter, fitted slope with Arm A's 0.85 drawn as a reference line; second panel against session duration | Slope near Arm A's line — same defect, new method |
| 05 | `05_subburst_duration_spacing.html` | What timescale do sub-bursts live at? | Duration and spacing distributions, log x, per segment, with the T1 knee marked | Duration piled at the ladder resolution |
| 06 | `06_subburst_move_share.html` | Do sub-bursts carry the move? | Per-sub-burst share of session move; ranked panel for largest, second, third; timing relative to detection and to peak | Shares uniformly small — sub-bursts aren't where the move happens |
| 07 | `07_tape_review/` | **Does any of this correspond to what happened?** | **Per event, three panels on a shared time axis. Top: trade prints, price, marker size by share count, sub-burst intervals shaded. Middle: rate curve with envelope overlaid, log scale, both observables. Bottom: inter-trade time, log scale. Detection and peak marked on all three.** | Shaded intervals not matching visible density changes; envelope obviously wrong |

**Chart 07 is produced even if numeric rows fire.** v2 skipped it on the reasoning that acceptance was off the table — sound for gating a disqualified measurement, but it also removed the only means of judging *why* the measurement failed. Selection per config cap: dev v4 primary cohort plus a stratified draw across segment and sub-burst count, plus every event flagged by any failure row. If the T1 gate fails, chart 07 is still produced with the envelope omitted and the rate curve shown raw.

---

## Reporting

Post, each with n, each citing its chart, each split by segment:

1. Cohort and precondition assertions; supersession confirmation; D8 append confirmation with line counts
2. **Scale-separation table — knee location and interval per segment, or its absence; gate rows 6 and 7 pass/fail**
3. Envelope table — scale used, sensitivity within the knee interval
4. Sub-burst count, duration, spacing tables
5. Move-share table, with undefined-denominator counts
6. **Row 1 table — correlation and slope against print count, duration, and peak rate**
7. Observable and tie-variant agreement
8. Failure criteria table — rows 0–7, observed against threshold, pass/fail, nothing further
9. Verification block per §10 — every headline number with source, n, reproduce command
10. Output files; commit list

---

## Approval gate

No tag, no merge, no Phase 11 scoping until Cooper approves. On approval, tag `phase-10-approved`.

**Chart 01 decides whether the phase is well-posed. Chart 04 decides whether the result is real. Chart 07 is the gate.** All three reads are Cooper's.
