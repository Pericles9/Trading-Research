<ide_opened_file>The user opened the file e:\Trading Research\notebooks\trades and codes.ipynb in the IDE. This may or may not be related to the current task.</ide_opened_file># Phase 10c — Amendment 1: A2.7 / A2.8 Resolution

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

## Revision — R3 conflicts resolved (2026-08-24)

Claude Code flagged three conflicts between this amendment's original draft and already-committed
Phase 10c config. All three are now resolved; content below reflects the resolution, not the
original draft.

- **C1 (A2.7.D2 rule) — my error.** The original draft thresholded the void parameter at 0.70,
  directly contradicting `D13_void_parameter` (threshold: null, "deliberate and permanent," 0.70
  named explicitly as the retired v4 value). Replaced below with an argmax rule that never applies
  a cutoff — the void parameter is used to rank candidates, not gate them.
- **C2 (window basis) — resolved: centered, as committed.** "Trailing" in the outline conflicted
  with `D3` (centered; trailing variants explicitly forbidden). Staying centered means Stage 0b's
  results (including R2's floor-clearing rungs) stay valid. It also means the non-causal-window
  problem this was originally meant to fix stays deferred — same status it had under v4, still
  parked for Phase 17.
- **C3 (first kernel) — resolved: 8 minutes.** "5 minutes" predated A1.5's base-2 grid alignment.
  8 minutes is where A2.8's floor actually clears for RTH, not just the nearest grid-aligned value.

## Revision 2 — A2.7 reframed, not fixed (2026-08-24)

Q2's measured comparison (`a3_d2_rule_confirmation.json`, `a3_d2_rule_comparison.parquet`) tested
both candidate-set rules head to head and settled a question bigger than which rule to pick — see
the new A2.7 section below for the reasoning. Short version: neither rule solves A2.7's original
check, and the conclusion is that A2.7's single-boundary premise doesn't hold given T0b.1's ~10
peaks per event, not that a fourth rule attempt is owed. A2.7 is demoted from a gate to a
descriptive diagnostic; its result is now read as evidence for leaning on the Stage 1 multi-kernel
comparison rather than as an unsolved defect in this amendment.

---

## A2.7 — reframed: not a fast/slow boundary, and no longer a gate

**What changed and why.** The per-event D2 idea was built on an assumption — one fast mode, one
slow mode, one boundary between them — that made sense before Stage 0b measured a median of 10
surviving peaks per event (up to 17). Two structurally different candidate-set rules were tested
head to head to find that boundary:

| | Rule A (top-two peaks) | Rule B (all troughs) |
|---|---|---|
| Candidates per event (median) | 2 | 9 |
| Median D2 | 5.6 ms | 17.8 s |
| Median void parameter | 0.491 | 0.894 |
| Check-4 pass rate (D2 ≥ 10 ms) | 46.4% (26/56) | 87.5% (49/56) |
| A2.7 verification pass rate (primary, n=50) | 58.0% (29/50) | 64.0% (32/50) |

The rules agree on which trough is D2 in only 12/56 events (21.4%); where they disagree, the
median D2 differs by 3.5 decades. That is not two estimates of the same quantity converging
imperfectly — it's two different objects. Rule A stays near fragmentation scale because "most
prominent" peaks are dominated by wherever fragmentation print-mass concentrates; premarket's
median (0.89 ms) sits an order of magnitude under even the fragmentation-noise floor. Rule B's
result is genuinely interesting — the first threshold anywhere in this line of work to land at a
burst-relevant timescale — but per its own check-4 behavior it isn't measuring an intraburst
fast/slow split either; it's closer to a burst-envelope boundary (where burst-period activity
gives way to background/quiet activity).

Neither rule reduces the original silent-failure rate (58%/64%, against a differently-defined 30%
Stage 0b baseline that isn't a clean comparison point — see below). Chasing a fourth rule variant
to find one that does would be searching for whichever specification makes the check pass, the
same failure mode already ruled out for Kleinberg, ACD, and the Allan/Fano knee elsewhere in this
program. **Decision: don't chase a fourth variant. A2.7's single-boundary premise doesn't fit data
this multi-modal, and the multi-kernel comparison already planned for Stage 1 is the correct tool
for letting fast and slow structure coexist without forcing them through one number.**

**Disposition:**

- **A2.7's silent-failure check is demoted from a gate to a descriptive report.** Both rates
  (58.0% / 64.0%, primary population) get carried into the Stage 1 digest with the caveat stated
  below — not as a pass/fail condition blocking anything.
- **Caveat, stated rather than buried:** 58%/64% is not a clean deterioration from Stage 0b's 30%.
  That baseline measured whether the later of the top-two peaks was taller — a hazard proxy, with
  no D2 in existence yet. The new figures measure the actual A2.7 question (tallest peak at or
  below the *computed* D2) for the first time. Different statistics; "30% → 58%" isn't a valid
  before/after comparison. What is solid: under both rules, with a real D2 computed two different
  ways, a majority of events show the configuration A2.7 was built to catch.
- **Rule B's value is carried forward, but relabeled — not reused as "D2" unchanged.** Calling it
  the fast/slow threshold would misrepresent what it measures, per Claude Code's own read of it as
  "a very different object" than an intraburst split. Working name: **burst-envelope boundary**.
  Needs its own decision-table entry from Claude Code, distinct from A2.7's original D2 slot,
  rather than continuing to overload one label with two meanings.
- **Selection rule for the envelope boundary:** argmax void parameter across all troughs in the
  event (Rule B), no threshold applied anywhere, per `D13_void_parameter`.
- **Peak ranking, resolved:** by prominence, not height. Height was my error in the original
  draft — inconsistent with how peaks were actually found and kept everywhere else in the
  pipeline (prominence-filtered), and it was the third under-specification measured on this rule.
  Moot for Rule B (ranking doesn't apply once all troughs are candidates) but stated for the
  record.

---

## A2.8 — local D5 (data floor) resolved: F = 1.5

**Decision:** F = 1.5, the loosest of the four tested. Derived floor: 156 prints. Clears at an
8-minute trailing window for the median RTH event.

**Labeling convention:** any event/kernel pair with fewer than 156 prints in its centered window is
labeled `insufficient_context`, carried forward, never given a fallback estimate — same convention
as `no_threshold` (void-gate) and `too_few_prints` (v4's count-based floor).

**Resolved: first kernel to validate is 8 minutes** — the RTH floor-clearing rung, not the
base-2-nearest-to-5 option (4 minutes). Premarket clears far earlier (1 minute, per R2) and should
show little `insufficient_context` labeling at this window. RTH is a different story worth
expecting rather than being surprised by: 8 minutes is where the *median* RTH event's print count
meets the floor, not comfortably clears it — so a non-trivial share of below-median-activity RTH
events will likely still land in `insufficient_context` even at the chosen first kernel. That's
expected behavior given F=1.5 was already the loosest option tested, not a sign the kernel choice
is wrong.

---

## Supersedes in the outline doc (`phase_10c_subburst_refinement_outline.md`)

- Open question 1 (trailing window anchoring) — unaffected, still open.
- Open question 2 (minimum trailing-window data floor) — **resolved** by A2.8 above.
- Open question 5 (threshold-selection rule) — **resolved, reframed**: no per-event fast/slow D2.
  A2.7 demoted to a descriptive diagnostic; Rule B's argmax value carries forward as a distinct
  "burst-envelope boundary" quantity, pending its own decision-table entry from Claude Code.

## Housekeeping — labeling collision, second instance

Flagged previously that global D2 (2025-data-exclusion flag) and A2.7's local D2 share a name, and
that A2.8's local D5 is unrelated to master D5 (long-only, burst-scale thesis). **Applied:** local
decision labels now carry section prefixes (`A2.7.D2`, `A2.8.D4`, `A2.8.D5`) per Claude Code's R3
report.

## D6 kernel grid — confirmed

D6 = {2, 8, 32} minutes, derived from the RTH floor-binding rung (8/4, 8, 8×4). Low rung 2 ≥ 1 ✓,
high rung 32 ≤ D11 = 64 ✓, all three on the base-2 grid at rungs 1, 3, 5 ✓. Applied to config.