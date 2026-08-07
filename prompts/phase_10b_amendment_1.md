# Phase 10b — Amendment 1 (A10b.1): T2 Control-Gate Resolution

**Date:** 2026-08-06
**Resolves:** T2 hard stop, escalation row 4 (C1–C4 required outcomes not met). Agent's control-gate report of 2026-08-06.
**Decision (Cooper):** Four changes, all pre-run. Three of the four correct defects in `prompts/phase_10b.md` and `config/phase_10b.json` as drafted. Rerun the control harness. **No real event is read until the amended controls pass.**

Commit this file to `prompts/` and the amended `config/phase_10b.json` **before** executing any task below. Then run T2-R0 through T2-R5. On a pass, resume `prompts/phase_10b.md` at T3 with the amended definitions in force. Every other section of the original prompt is unchanged.

---

## Why this is not a retune

The gate forbids adjusting a method to make a control pass. That prohibition is intact. The distinction being applied:

- **Forbidden:** moving a threshold, window, or parameter until the number looks acceptable.
- **This amendment:** the controls established that the pre-registered T3 crossing statistic does not measure the quantity C3 and C4 ask it to recover, and that the T4 eligibility rule admits bandwidths the estimator cannot serve. Both are specification defects, identified from the control output, corrected before any real data is touched.

The discipline that keeps the distinction honest is **validation on scales the respecified statistic has not seen** (T2-R3). If the new statistic recovers only the 10 µs case that motivated the change, it was fitted to that case, and that is a hard stop.

**On the record, three of these four are drafting errors in the original prompt, not execution errors:**

1. T3d specified a *departure point* while v3 — the very result T5 compares against — used a *knee*. The prompt introduced a like-for-unlike comparison.
2. The T4 eligibility rule policed empty λ̂ (the floored-time test) but not stale λ̂, which is what a fixed 60 s block produces when the kernel is narrower than the block.
3. The stated rationale for the widest-h crossing rule — *"the crossing that survives the most permissive null"* — is sign-inverted. Narrow bandwidth means λ̂ hugs the data, the null absorbs structure, and rejection is harder. **The most permissive null is the narrowest eligible bandwidth, not the widest.**

The agent's four implementation defects (in-sample band fitting, Λ snapped to grid nodes, a grid unable to represent the block structure, missing edge correction) were caught and fixed by the controls before this report and are not in scope here. They are recorded in the T2 report as evidence the gate works.

---

## Context additions

- **Every new value in this amendment goes into `config/phase_10b.json` and is committed before the rerun.** The injected validation scales in T2-R3 are pre-registered by that commit. Choosing them after seeing the knee statistic's behaviour would void the validation.
- **No real event is read by any pipeline in this amendment.** Escalation row 14 and the zero-pass budget stand.
- The original T2 passes — band coverage 0.9348–0.9460, C3 plateau 5.9852 vs E[N²]/E[N] = 6.0000, C4 scale separation 4.19e6 — are **not re-litigated**. They are re-asserted numerically in T2-R5 to confirm the amendment did not break them, and any change in them is itself a hard stop.

---

## Tasks

- [ ] **T2-R0 — Departure direction diagnostic. Runs first; it may make Change 3 a no-op.**
  From the existing C1 and C2 artifacts, without rerunning anything: for every rung and every eligible bandwidth, report whether each out-of-band excursion was **above** the upper band edge or **below** the lower edge. Report as a table: control, bandwidth, rung, share above, share below, share inside.
  - [ ] T2-R0a — Report the observed 0.871 (C1, h = 64 s) and 0.774 (C2, h = 16,384 s) decomposed into upward and downward shares.
  - [ ] T2-R0b — **Interpretation is fixed in advance.** A downward departure — the real curve falling *below* a matched-Poisson band — is not evidence of clustering. It is the opposite, and counting it as a control failure is a specification defect. Under Change 3 it stops being counted.
  - [ ] T2-R0c — **Hard stop if C1's failure is predominantly upward** (upward share alone ≥ 0.05 of eligible rungs). T2e reported band coverage of 0.9348–0.9460 against a nominal 95% band, so roughly 6% of rungs fall outside by chance and roughly 3% above. An upward excess materially beyond that is not explained by this amendment. Post the rung profile — which rungs, and whether they cluster at one end of the ladder — and wait.
  - [ ] T2-R0d — Commit. Read-only on artifacts; no simulation in this task.

- [ ] **T2-R1 — Change 1: respecify the T3 crossing statistic as a knee.**
  Replace T3d in `prompts/phase_10b.md` (recorded here, the original file is not edited).

  **Old (void):** the lowest eligible rung above which the real pooled curve is outside the band at every subsequent eligible rung.

  **New:** on the pooled log A(T) versus log T curve, fit piecewise-linear models with k = 1, 2, 3 segments over the eligible rungs, breakpoints searched over rung positions only. Select k by BIC. **Report every breakpoint, each as a rung index with its bracketing seconds, together with ΔBIC of the selected model against k = 1.** Report the fitted slope of every segment.

  Rationale, and the reason this is not a free choice: **v3's Allan/Fano gate — the 128 s / 16 s knee with ΔBIC 45.6–68.7 — is already a plateau-to-slope transition statistic.** The original T3d specified a departure point, which is a different object, and T5 would have compared two unlike quantities. This change makes T5's comparison like-for-like and is required whether or not C3 passes.
  - [ ] T2-R1a — Record why the departure statistic cannot work: a cluster process departs from Poisson at the finest resolvable scale, because two points in one cluster can be arbitrarily close. The departure point therefore measures the finest clustering present. **On real data it would land on the fragmentation scale in every event and nothing in the phase would have flagged it.**
  - [ ] T2-R1b — The matched-null band is retained and still computed. It is no longer the source of the crossing statistic; it remains the evidence for whether any structure exists at all, and charts 02, 03 and 04 still show it.
  - [ ] T2-R1c — **Directional rule, applying to real data as well as controls:** where the band is used to state that structure exists, only excursions **above** the upper edge count. Downward excursions are reported separately and never as evidence of clustering.
  - [ ] T2-R1d — Commit config and this specification before running anything.

- [ ] **T2-R2 — Change 2: held-out block length scales with bandwidth.**
  Replace the fixed 60 s block in T4b.

  **New:** block length = `max(h / block_ratio, block_floor_event)` where `block_ratio` = 4 (config) and `block_floor_event` is, per event, the smallest block duration whose median block print count is at least `min_prints_per_block` = 20 (config). Odd/even fold structure unchanged; both folds still reported separately.

  Rationale: at h = 16 s and 32 s against a 60 s block, the kernel is narrower than the block it must reach across, so λ̂ inside a held-out block is extrapolated from ≥ 30 s away. It is **stale, not empty**, so the floored-time rule cannot see it — which is why C1 showed pass shares of 0.26 and 0.00 at those bandwidths on genuinely homogeneous data.
  - [ ] T2-R2a — **The alternative fix — declaring h < 60 s ineligible — is rejected and the rejection is recorded.** It truncates the sweep at 64 s, and v3's premarket knee is 16 s. That would exclude the premarket segment's candidate answer from the search range by construction.
  - [ ] T2-R2b — **New eligibility rule:** bandwidths where `block_floor_event` binds (that is, h / 4 < `block_floor_event`) are ineligible for crossing determination, shaded on chart 05, and reported with their count — the same treatment already given to floored time. Report the binding share per segment.
  - [ ] T2-R2c — Confirm the held-out property survives: with block = h/4 the kernel spans the held-out block, but no individual held-out arrival is localized by the fitting blocks. State the check performed.
  - [ ] T2-R2d — Commit.

- [ ] **T2-R3 — Change 1 validation on unseen injected scales. This is the task that makes Change 1 legitimate rather than fitted.**
  Draw two new controls with cluster durations **pre-registered here and committed before the run**: **C3′ at 1 ms** and **C4′ at 100 ms**. Same background rate, same cluster size k = 6, same timestamp quantization, same draw count as C3/C4.
  - [ ] T2-R3a — **Required outcome: the knee statistic recovers 1 ms and 100 ms each within 1 rung.**
  - [ ] T2-R3b — **Hard stop if the knee recovers 10 µs but misses either new scale.** That is the signature of a statistic fitted to the case that motivated it, and it voids Change 1 rather than the controls.
  - [ ] T2-R3c — Commit.

- [ ] **T2-R4 — Change 3: inside-band evaluation range, per control, from the simulator's own parameters.**
  The original config states the ≥ 0.90 inside-band rule and separately states the widest-h crossing rule, and never says which h the inside-share is evaluated at. Under "min over eligible h" C1 and C2 fail; under "max" both pass; under "widest" C1 passes and C2 fails. **The ambiguity is resolved as follows, and it is neither min nor max.**

  | Control | Inside-band requirement holds over | Reason |
  |---|---|---|
  | C1 (homogeneous) | **all eligible h** | The flat null is correctly specified at every bandwidth |
  | C2 (inhomogeneous, real event shape) | **h ≤ `c2_lambda_timescale`** | Recorded in config as the smoothing bandwidth used to build the injected profile |
  | C3, C4, C3′, C4′ | not applicable | These are required to be **outside** the band; they carry knee-recovery requirements instead |

  Rationale: C2 failed at h = 16,384 s, which is wider than the session. At that bandwidth λ̂ is flat and C2's arrivals genuinely are clustered relative to it — **because C2 was constructed with real rate structure.** Requiring C2 to pass against a null that is misspecified for it by construction is not a strict requirement, it is an incoherent one. The range is decidable from the simulator's parameters before the run, which is why it is committed rather than chosen after.
  - [ ] T2-R4a — Aggregation across the eligible range is the **minimum** inside-band share over eligible h. Within a correctly specified range, min is the right aggregator — that part of the original call was correct.
  - [ ] T2-R4b — Apply the T2-R1c directional rule to all inside-band shares.
  - [ ] T2-R4c — Commit.

- [ ] **T2-R5 — Rerun the full control harness and re-assert the passes.**
  C1, C2, C3, C4, C3′, C4′ end to end through the shared pipeline. No separate control implementation.
  - [ ] T2-R5a — **Re-assert the original passes numerically.** Band coverage in [0.90, 0.99]; C3 plateau height within ±25% of E[N²]/E[N]; C4 scale separation ≥ 1024. **Any material movement in these is a hard stop** — it means the amendment broke something that was working.
  - [ ] T2-R5b — Chart 04 amended: add C3′ and C4′ panels (2×3 facet), draw the fitted piecewise-linear segments and every selected breakpoint over each curve, mark injected scales with vertical rules, and shade downward excursions distinctly from upward.
  - [ ] T2-R5c — Post the full amended required-outcome table. Commit.

- [ ] **T2-R6 — Change 4: T6 wording.**
  The original T6 clause reads *"Produced regardless of every numeric outcome above, including a T2 hard stop."* CLAUDE.md states a hard stop means stop and wait. The agent was right to stop and right to ask rather than choose.

  **The conflict is moot in this instance and the wording was sloppy.** T6 charts real events with the T3 and T4 crossings overlaid; at a T2 stop no real event has been read and neither crossing exists, so T6 has no inputs. The "regardless" clause was written to prevent the v2 failure — skipping tape review because the numbers came back null or ugly — not to override a stop before any data is touched.

  **Amended to:** *"Produced regardless of any numeric outcome in T3, T4 or T5, including a null result, an ugly result, or an escalation on rows 6 through 9."* On a T2 hard stop, CLAUDE.md governs and T6 does not run.
  - [ ] T2-R6a — Commit.

---

## Amended Required Outcomes

| Control | Check | Required | Status |
|---|---|---|---|
| C1 | Inside-band share, upward excursions only, min over **all** eligible h | ≥ 0.90 | [ ] |
| C1 | T4 interior crossing under h/4 blocks | none | [ ] |
| C2 | Inside-band share, upward only, min over h ≤ `c2_lambda_timescale` | ≥ 0.90 | [ ] |
| C2 | T4 interior crossing | none | [ ] |
| C3 | Plateau height vs E[N²]/E[N] | ±25% | [ ] |
| C3 | **Knee** recovers 10 µs | within 1 rung | [ ] |
| C3 | T4 crossing recovers 10 µs | within 1 rung | [ ] |
| C4 | Two scales visible and separated | ≥ 1024 | [ ] |
| C4 | **Knee** recovers 60 s | within 1 rung | [ ] |
| C4 | T4 crossing recovers 60 s | within 1 rung | [ ] |
| **C3′** | **Knee recovers 1 ms** | within 1 rung | [ ] |
| **C4′** | **Knee recovers 100 ms** | within 1 rung | [ ] |
| All | Band coverage, nominal 95% | [0.90, 0.99] | [ ] |

---

## Escalation Criteria — amendments to the original table

Original rows 0–14 stand unchanged except as noted. Rows below are inserted and checked in table order.

| # | Condition | Threshold | Action |
|---|---|---|---|
| 4 | *(amended)* Any required outcome in the Amended Required Outcomes table not met | any | Hard stop — do not proceed to T3, do not adjust method |
| 4a | C1's out-of-band share is predominantly **upward** (T2-R0c) | upward share ≥ 0.05 | Hard stop — not explained by this amendment; post the rung profile |
| 4b | Knee recovers 10 µs but misses C3′ (1 ms) or C4′ (100 ms) | either | Hard stop — Change 1 was fitted; the statistic is void, not the control |
| 4c | Any original T2 pass moves materially on rerun (T2-R5a) | any | Hard stop — the amendment broke something that worked |
| 4d | Bandwidth ineligibility from `block_floor_event` binding exceeds `ineligible_share_max` (config: 0.40) of the sweep on either segment | > 0.40 | Hard stop — too little of the sweep is testable to interpret a crossing |
| 15 | A second amendment is required to make any control pass | any | Hard stop — **post and wait.** Two rounds of specification repair on one gate is a signal the method does not fit the data, not a third round to be written |

---

## Config additions

All committed to `config/phase_10b.json` **before** the rerun.

| Key | Value | Used by |
|---|---|---|
| `crossing_statistic` | `"piecewise_knee"` | T3d |
| `knee_max_segments` | 3 | T3d |
| `knee_selection` | `"bic"` | T3d |
| `band_direction` | `"upper_only"` | T3c, T2-R1c, T2-R4b |
| `block_ratio` | 4 | T4b |
| `min_prints_per_block` | 20 | T4b |
| `ineligible_share_max` | 0.40 | Row 4d |
| `c2_lambda_timescale` | *(the smoothing bandwidth used to build C2's injected profile — record the actual value)* | T2-R4 |
| `control_c3_prime_duration_s` | 1e-3 | T2-R3 |
| `control_c4_prime_duration_s` | 1e-1 | T2-R3 |

The original `min_pairs_pooled` (20), `min_pairs_event` (5), `lambda_floor_frac` (1e-3), `floored_time_max` (0.20), `n_control_draws` (200), `n_null_draws` (200), `ks_alpha` (0.05) and `ks_pass_share` (0.50) are unchanged.

---

## Output Files

| File | Description | Status |
|---|---|---|
| `prompts/phase_10b_amendment_1.md` | This file | [ ] |
| `config/phase_10b.json` | Amended, committed before the rerun | [ ] |
| `results/phase_10b/artifacts/t2r0_departure_direction.json` | Upward/downward decomposition per control, bandwidth, rung | [ ] |
| `results/phase_10b/artifacts/t2_controls.json` | Rewritten — all six controls, amended outcomes | [ ] |
| `results/phase_10b/artifacts/t2r3_unseen_scale_validation.json` | C3′ and C4′ knee recovery | [ ] |
| `results/phase_10b/artifacts/t2r2_block_eligibility.json` | Binding share per bandwidth per segment | [ ] |
| `results/phase_10b/charts/04_control_harness.html` | Amended — 2×3, segments and breakpoints drawn, directional shading | [ ] |

---

## Reporting

On completion of T2-R5, post:

1. **T2-R0 departure table** — C1 and C2 decomposed upward/downward/inside, by bandwidth and rung, with the rung profile.
2. **Amended required-outcome table** — every row, observed, pass/fail, with n.
3. **Knee recovery table** — injected scale vs recovered breakpoint vs rung error, for C3, C4, **C3′, C4′**, with ΔBIC and selected k per curve.
4. **Re-assertion table** — band coverage, C3 plateau, C4 separation: original value, rerun value, delta.
5. **Block eligibility table** — bandwidths excluded by floored time, by `block_floor_event` binding, and the remaining testable share per segment.
6. **Escalation check table** — original rows 0–14 plus 4a–4d and 15.
7. **Verification block** (§10) for every number above.
8. Commit list.

Description only. No recommendations. Every claim cites chart 04.

On escalation, post which criterion triggered, the observed value, the tables completed to that point, and nothing else.

---

## Approval Gate

**On a pass:** resume `prompts/phase_10b.md` at T3, with the knee statistic, the directional band rule, and the h/4 block structure in force. No further approval needed to proceed from T3 to T7 — the original approval gate at the end of Phase 10b still governs the phase.

**On any hard stop, including row 15:** post and wait. Do not write a second amendment.

The controls have now caught four implementation defects and three specification defects across two runs, before any real event was read. **That is the gate working as intended, and none of it would have surfaced from an outcome threshold.** If a third round is needed, the reading is that the method does not fit the data — and that is a finding about the data, to be recorded as one.
