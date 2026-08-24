---
tags:
  - type/phase-amendment
  - domain/strategy
  - project/src-core
  - status/draft
created: 2026-08-23
phase: 10c
amends:
  - Phase-10c-Amendment-A2.md
standard: Agent Prompt Standard v1.3
---

# Phase 10c — Amendment 1: A2.7 / A2.8 Resolution

> **Filename note.** Issued titled "Amendment 1" while `phase_10c_amendment_a1.md` and
> `phase_10c_amendment_a2.md` already exist and mean something else. Filed under a
> content-descriptive name rather than a number to avoid adding a third collision to the
> two the Housekeeping section below already flags. Title preserved verbatim.

**Status:** Formal amendment. Resolves the two decisions escalated in the Stage 0b digest
(`results/phase_10c/digests/stage0b_digest.json`). To be carried into the Stage 1 prompt.

**Not blocking, but unresolved:** the Stage 0b digest's event-count reconciliation gap (56 total
vs. 53 in the T0b.6 segment table vs. 50 implied by the 3+12 premarket/RTH breakdown of the 19/56
figure) has been sent back to Claude Code for an event-level accounting and hasn't returned yet.
Neither decision below depends on the exact figure — the new verification clause under A2.7 will
re-measure against whatever the corrected per-event D2 produces. If the accounting turns out to
change which events belong in the population at all, that supersedes this amendment's numbers, not
its logic.

---

## A2.7 — local D2 resolved: per-event

**Decision:** D2 (the fast/slow-mode interval boundary tested in A2.7) is set per-event, not
per-segment or globally.

**Rationale:** T0b.1 found a median of 10 surviving peaks per event (up to 17). A single
segment-level split was always going to be a compromise against that much per-event structure —
per-event resolution fits what the data is actually showing.

**Selection rule — drafted, needs Cooper's confirmation before Stage 1 runs:** scanning outward
from the fastest (shortest-interval) surviving peak, take the first trough whose void parameter
clears the reference cutoff (0.70) as that event's D2. This reuses the existing threshold logic,
applied to a second and independent question — which peak marks the fast/slow boundary — rather
than assumed to carry over automatically from the original per-event threshold decision. **If a
different rule is intended, specify it here before Stage 1.**

**Required new verification.** A2.7's underlying concern was that a fixed threshold could silently
select the wrong mode — a taller, later peak sitting at or below D2, which the Stage 0b digest
measured at 19/56 events (33.9%; premarket 3/15, rth 12/35), pending the reconciliation check
above. Moving to per-event D2 does not automatically fix this — it depends entirely on whether the
selection rule above reliably lands on the true fast/slow boundary rather than some other trough
among the ~10 available. **Stage 1 must re-run the same check** (largest peak at or below D2,
without triggering `no_intraburst_peak`) using the new per-event D2 and report the resulting rate
against the Stage 0b baseline. If the rate doesn't drop meaningfully, per-event D2 hasn't solved
the problem it was adopted to solve, and the selection rule needs revisiting before Stage 1
proceeds further.

---

## A2.8 — local D5 (data floor) resolved: F = 1.5

**Decision:** F = 1.5, the loosest of the four tested. Derived floor: 156 prints. Clears at an
8-minute trailing window for the median RTH event.

**Labeling convention:** any event/kernel pair with fewer than 156 prints in its trailing window is
labeled `insufficient_context`, carried forward, never given a fallback estimate — same convention
as `no_threshold` (void-gate) and `too_few_prints` (v4's count-based floor).

**Flag — tension with the outline's kernel-validation plan.** The outline set 5 minutes as the
first kernel to stand up and validate before expanding to the full log-spaced grid. Even at F=1.5
— the loosest option on the table — the median RTH event doesn't clear the floor until 8 minutes.
The 5-minute kernel will show substantial `insufficient_context` labeling for RTH events by
construction, not as something to debug. **Cooper: decide (a) keep 5 minutes as first validation
and expect/report the `insufficient_context` rate on it, or (b) move first validation to 8+
minutes, where the floor is actually cleared for the median event.** Premarket's own
floor-clearing point wasn't derived in the Stage 0b digest (only RTH was) — worth requesting from
Claude Code before deciding, since premarket's flat, much higher density (T0b.5: 87.5–90.9/min,
no anchor effect vs. RTH's 42.4 vs. 6.0/min) may clear the floor at a shorter window than RTH does.

---

## Supersedes in the outline doc (`phase_10c_subburst_refinement_outline.md`)

- Open question 1 (trailing window anchoring) — unaffected, still open.
- Open question 2 (minimum trailing-window data floor) — **resolved** by A2.8 above.
- Open question 5 (threshold-selection rule) — **partially resolved**: per-event D2 selection rule
  drafted above, pending Cooper's confirmation and the Stage 1 verification requirement.

## Housekeeping — labeling collision, second instance

Flagged previously that global D2 (2025-data-exclusion flag) and A2.7's local D2 share a name.
This digest confirms the same pattern recurs at least once more: A2.8's local "D5" is unrelated to
master D5 (long-only, burst-scale thesis). Both are internally clear from context but risk
misreads in future digests or when skimming Class M checks. Worth prefixing local decision labels
by their appendix section (`A2.7.D2`, `A2.8.D5`) before Stage 1, rather than continuing to reuse
bare `D#` for two different scopes.

---

# Agent response, 2026-08-23 — carried in the same document

## R1. Reconciliation gap: resolved, no events missing

Requested above and returned here. Artifact:
`results/phase_10c/artifacts/a3_event_accounting.json`.

| Segment | primary | sidecar | total |
|---|---|---|---|
| premarket | 15 | 1 | 16 |
| rth | 35 | 2 | 37 |
| post | 0 | 1 | 1 |
| unlabelled | 0 | 2 | 2 |
| **total** | **50** | **6** | **56** |

- **56** — all dev-sample events, 50 primary plus 6 sidecar.
- **53** — the T0b.6 gate table, premarket 16 + rth 37. The gate is specified "by segment" and
  segment means premarket or RTH, so the 3 omitted events are the post(1) and unlabelled(2). **All
  three are sidecar**, which A1.6 already carries and reports separately.
- **50** — primary only, splitting premarket 15 + rth 35.

The 19/56 figure decomposes the same way: **19 counts all 56 events**, while the 3/15 + 12/35
breakdown published beside it was **primary only = 15/50**. The remaining 4 are sidecar (4 of the
6 sidecar events have the later peak taller). 15 + 4 = 19. No event is missing or double counted.

The presentation was the defect, not the population: one figure quoted on all-56 and its
breakdown on primary-only, in the same sentence. Stage 1 reports every count with its population
named inline.

## R2. Premarket floor-clearing point: requested, returned

Median window count by kernel and the smallest clearing rung, both segments, centered windows
clipped at the RTH open and close per A2.5:

| F | premarket floor | clears at | rth floor | clears at |
|---|---|---|---|---|
| 1.1 | 1,703 | 8 min | 2,832 | none ≤ 64 |
| 1.2 | 465 | 2 min | 774 | 32 min |
| 1.3 | 225 | 1 min | 374 | 16 min |
| **1.5** | **94** | **1 min** | **156** | **8 min** |

**At the chosen F = 1.5, premarket clears at 1 minute and RTH at 8.** RTH is the binding segment
by three rungs. The premarket floor is 94 rather than 156 because the floor is derived per event
from that event's own σ, and premarket σ is lower (1.363 vs 1.758).

## R3. Two conflicts with committed decisions — flagged, not applied

Both are recorded rather than resolved, because each contradicts a decision already committed to
`config/phase_10c.json`.

**C1 — the drafted A2.7.D2 rule thresholds the void parameter at 0.70.** Config `D13_void_parameter`
sets `threshold: null` with the note *"null here is deliberate and permanent, not a [Cooper] field.
The void parameter is never thresholded in this phase."* Prompt §4 is more specific still: *"Any
void-parameter cutoff. v4 used 0.70, adopted from the neuroscience literature. This phase does
**not** threshold on the void parameter at all."* The drafted rule uses that exact retired value.
Not implemented pending explicit resolution — either D13 and §4 are amended, or the rule uses a
different discriminator.

**C2 — "trailing window" contradicts the settled window basis.** A2.8 says "trailing window" three
times, and the superseded-outline section lists "trailing window anchoring" as still open. Config
`D3_window` is `basis: clock_time`, `centering: centered`, with `_forbidden_variants:
["trailing", "anchored_to_detection"]`, and prompt §3.3 states *"It remains **centered** … Do not
implement a trailing variant."* **Every floor-clearing number in R2 and in the Stage 0b digest was
computed on centered windows.** On a trailing window the counts and therefore the clearing rungs
would differ. Not implemented pending resolution.

**C3 — "5 minutes as the first kernel" is stale.** A1.5 amended D5 from 5 to 4 minutes specifically
so all Stage 2 kernels sit on the base-2 grid, and A2.8 then made D5 derived. Option (a) as
written would reintroduce the off-grid defect A1.5 fixed, since 5 is not a base-2 rung. The live
options are 4 (the A1.5 value) or 8 (what A2.8's rule derives at F = 1.5).

## R4. Applied

| Item | Action |
|---|---|
| A2.8 F = 1.5 | `D4_median_precision_factor = 1.5`, Class M, set |
| `insufficient_context` | Registered as a carried label alongside `no_threshold`, `too_few_prints`, `no_intraburst_peak` |
| A2.7 D2 scope | Recorded as **per-event**; the selection rule is left unset pending C1 |
| Housekeeping | Local labels now carry their section prefix: `A2.7.D2`, `A2.8.D5` |
| D5 / D6 | Derivation recorded (8 min RTH-binding at F = 1.5 ⇒ D6 = {2, 8, 32}); field left unset pending the (a)/(b) choice and C3 |

Stage 1 is not started. The amendment states the selection rule "needs Cooper's confirmation
before Stage 1 runs", and C1, C2 and the (a)/(b) choice are open.
