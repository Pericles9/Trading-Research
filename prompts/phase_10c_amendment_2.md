# Phase 10c — Amendment 2: Session Boundary and Full-Population Labeling

**Status:** Formal amendment. Blocks Stage 1 — the labeling work below must complete and the
downstream re-derivation check must return before Stage 1 runs.

**Scope:** two coupled items. (1) The trading-day boundary is redefined to the prior session
close. (2) All 56 events must carry a segment label under that definition; the current
53-event coverage is not sufficient to proceed.

---

## A — Trading-day boundary redefined

**Decision:** the trading day for Phase 10c purposes begins at the **prior session close** and
runs through the following session's close. This matches what the momentum scanner actually
measures — its percentage move is computed from the prior close, so the analysis window should
start where the scanner's own measurement starts.

**Definition — prior session close per XNYS, not a fixed clock time.** Cooper's framing was "4pm
the weekday before." The intent is right; the literal value would be wrong on two recurring cases:

- **Early closes.** Half-days (day after Thanksgiving, Christmas Eve, July 3rd in some years)
  close at **13:00 ET**, not 16:00. A hardcoded 16:00 boundary would place up to three hours of
  non-existent session inside the window and mislabel anything falling there.
- **Holidays.** "The weekday before" resolves to Monday for a Tuesday event — but if that Monday
  was a market holiday, the true prior close was the preceding Friday.

Both are handled correctly and automatically by the **XNYS calendar already pinned in this
program** (federal holiday calendars are banned program-wide for exactly this class of error). No
new constant is introduced: the boundary is whatever XNYS reports as the prior session's close for
that event's date.

**Consequence to expect:** activity between the prior close and midnight now belongs to the event's
own trading day rather than the preceding one. Events currently labeled `post` are the most
obvious reclassification candidates, but the check below should not assume they are the only ones.

---

## B — Full-population segment labeling required

**Problem.** Stage 0b's gate table covered 53 of 56 events (premarket 16, rth 37). The three
omitted are the single `post` event and the two `unlabelled` events, all sidecar. Amendment 1
accepted this as a reporting-scope difference rather than a population defect, which was correct
for that context.

**It is not sufficient going forward.** Under the redefined boundary, segment membership itself is
in question, so partial labeling can't be carried into Stage 1. Every event in the population needs
a segment label derived under Amendment 2A.

**Required of Claude Code:**

1. **Clarify the existing gap first, from `a3_event_accounting.json`:** were anchors and segment
   labels *not computed* for the three omitted events, or computed and merely excluded from
   segment-stratified reporting? The remedial work differs — a genuine compute gap versus a
   reporting-scope choice.
2. **Recompute the anchor and segment label for all 56 events** under the prior-session-close
   boundary, XNYS-derived.
3. **Report the reclassification explicitly** — a before/after table of segment membership showing
   which events moved and why. Not a summary count; per-event, since only a handful are expected
   to move and the identities matter for item 4.
4. **Resolve the two `unlabelled` events** or state positively why they cannot be labeled. Carrying
   `unlabelled` into Stage 1 is acceptable only if it is a measured property of those events, not
   an unresolved gap.

---

## C — Downstream re-derivation check (the part that actually matters)

**D5 = 8 and D6 = {2, 8, 32} are already applied to config, and both were derived under the old
session definition.** The dependency chain is:

> segment membership → per-segment σ (premarket 1.363, RTH 1.758) → A2.8.D4 per-event derived
> floor → RTH floor-clearing rung (8 min) → D5 → D6 = {D5/4, D5, D5×4}

If any event reclassifies between segments, σ changes, and every link downstream of it is derived
from a superseded basis.

**This is a check, not a prediction of failure.** If only a few sidecar events move, σ likely
shifts negligibly and the binding rung stays at 8 — in which case D5 and D6 stand exactly as
applied and nothing downstream moves.

**Required:** after the relabeling in B, re-derive the A2.8 floor table on the new segment
assignments and report whether the RTH binding rung is still 8 minutes.

- **If it remains 8:** D5 and D6 are confirmed on the corrected basis. Note it in the digest and
  proceed to Stage 1.
- **If it moves:** stop and escalate. Do not apply a new D5/D6 — the grid derivation is Cooper's
  decision, and re-deriving it silently would be exactly the kind of agent-side patch this program
  prohibits.

---

## D — Amendment 1 status under this change

Amendment 1's substantive resolutions are unaffected in logic but partly conditional in their
numbers:

- **A2.7 reframing** (single-boundary premise rejected, demoted to descriptive, Rule B carried
  forward as the burst-envelope boundary) — **unaffected.** The reasoning rests on peak
  multi-modality, not on segment assignment.
- **A2.8 F = 1.5** — **unaffected as a choice.** F is a confidence level, selected independently of
  which events sit in which segment.
- **A2.8 derived floor (156 prints), D5 = 8, D6 = {2, 8, 32}** — **conditional**, pending the
  re-derivation in C above.
- **Outstanding from Amendment 1, unchanged:** the burst-envelope boundary still needs its own
  decision-table entry from Claude Code, distinct from A2.7's original D2 slot.