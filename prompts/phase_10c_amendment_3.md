# Phase 10c — Amendment 3: Threshold Variants and Closing-Print Boundary

**Status:** Formal amendment. Resolves the two items raised in Claude Code's Amendment 2 response.
Both block Stage 1.

---

## A — Detection threshold variant: carry all three, do not collapse

**The defect.** `load_detection()` calls `drop_duplicates(subset=COHORT_KEY)` on
`v2_r13_detection.parquet`, which carries three rows per event (momentum threshold variants 1.25,
1.30, 1.35). Keeping the first row silently selected **1.25**. Every segment-stratified number in
Stage 0b and Stage 1 was computed on that variant, and it was never a recorded decision. Correctly
reported rather than patched.

**Decision: all three variants are carried through the pipeline as parallel arms.** No collapse,
no default selection. Same logic as the D6 kernel grid — report the set, don't pick a winner.

**This defers the question rather than answering it, and that is deliberate.** A single variant
will eventually have to be selected for anything tradeable, since the anchor defines T=0. Carrying
three makes the dependence visible and measurable instead of hidden behind a `drop_duplicates`
default. The selection decision comes later, on evidence, and is Cooper's.

### A1 — Required measurement: anchor-timing deltas, not just segment counts

The variant table circulated so far reports segment membership only:

| Threshold | post | premarket | rth | none |
|---|---|---|---|---|
| 1.25 | 1 | 30 | 80 | 3 |
| 1.30 | 1 | 29 | 80 | 4 |
| 1.35 | 3 | 28 | 64 | 19 |

**Reading this as "1.25 and 1.30 differ by one event" is wrong, and that framing (mine, in the
prior session) is withdrawn.** A lower threshold crosses earlier on the same run-up, so for every
event where two variants both have anchors, T=0 can sit at a different timestamp. Phase 10c
measures everything event-relative to that anchor. Identical segment counts are fully compatible
with materially different origins.

**Required of Claude Code:** for each variant pair (1.25↔1.30, 1.30↔1.35, 1.25↔1.35), report the
distribution of anchor-timing deltas across events where both variants produce an anchor —
median, IQR, p90, and the count exceeding one minute. Distribution chart before any summary
statistic, per the Chart Contract. This is the measurement that establishes how much the variant
choice actually matters; segment counts alone do not.

### A2 — Pre-registration against post-hoc selection

Three variants × three kernels (D6 = {2, 8, 32}) = **nine cells**. That is a large enough surface
that selecting the best-looking cell after the fact would be trivial and invisible.

**Pre-registered now, before any results exist:** all nine cells are reported together in every
digest. No variant and no kernel is selected, dropped, or promoted on the basis of how its results
look. Variant selection, when it happens, is a separate decision made on stated grounds and
recorded with a D-number — not an outcome of looking at nine result sets and preferring one.

### A3 — Downstream consequence: does the kernel grid stay fixed across variants?

A2.8's derived floor comes from per-segment σ, which comes from segment membership, which differs
by variant — 1.35 drops RTH from 80 to 64 events. So the floor derivation, and therefore D5 and
D6, could in principle differ per variant.

**Required:** re-derive the A2.8 floor table under 1.30 and 1.35 and report whether the RTH
binding rung is still 8 minutes in each.

- **If the binding rung is 8 across all three variants:** D5 = 8 and D6 = {2, 8, 32} hold
  globally, the grid stays fixed, and the nine cells remain directly comparable. This is the
  preferred outcome.
- **If it differs by variant:** stop and escalate. Do **not** assign per-variant grids — that
  would make the variants incomparable and defeat the point of carrying them in parallel. Whether
  to fix one grid across all variants (and which) is Cooper's decision.

### A4 — Dev-sample composition check

The dev sample (50 primary + 6 sidecar, seed 42, stratified by `momentum_pct` decile) was drawn
while 1.25 was silently in effect. Since variants change which events have anchors at all,
**confirm whether the seed-42 draw yields the same 56 events under 1.30 and 1.35.** If it does
not, the sample composition itself is variant-dependent, which needs its own decision before Stage
1 — carrying three variants on three different dev samples is not a comparison.

---

## B — Closing-print boundary: fix

**The artifact.** ACET 2020-09-18 anchors at 16:00:00.0078 ET — 7.8 ms after `session_close`.
Under Amendment 2A's `(prior close, this close]` boundary it falls into the *next* trading day and
was labeled `outside_redefined_day`. That is literally correct and economically wrong: closing
auction prints routinely report a few milliseconds after the nominal close, and a closing cross
belongs to the session that produced it.

**Decision: auction prints are assigned to their originating session.** The strict half-open
interval is not accepted at the closing edge.

**Rule not yet specified — Claude Code to report options before it is set.** Two candidate
mechanisms:

1. **Condition-code based.** If the trade archive carries condition codes identifying closing
   auction / closing print activity, assign those trades to the session whose close they settle,
   regardless of timestamp. Preferred if available — it keys on what the print *is*, not on how
   late it happens to report.
2. **Grace window.** A short fixed tolerance past `session_close` within which prints are assigned
   to the closing session. Introduces a constant, which the program otherwise avoids, and would
   need its value derived from the observed reporting-lag distribution rather than chosen.

**Required of Claude Code:** report (a) whether condition codes sufficient for mechanism 1 exist
in `filtered_trades`, and (b) the distribution of anchor timestamps falling within, say, one
second after `session_close`, across **all three threshold variants** — 1.35 moves `post` from 1
to 3 events, so the affected population is variant-dependent and one event is not the right basis
for setting a rule.

---

## C — Amendment 2 items closed

- **2A boundary definition** — implemented as specified, XNYS `session_close`, no constant. Closed,
  subject to the B fix above.
- **2B1** — resolved: the three omitted events were computed and returned definite results
  (one `post` anchor, two `never_crosses` with stated reasons). Neither a compute gap nor a
  reporting-scope exclusion.
- **2B4** — resolved: the two `unlabelled` events are positively unlabellable. No anchor exists, so
  no segment can be assigned under any boundary definition. Measured property, carried as such.
- **2C** — D5 = 8 and D6 = {2, 8, 32} confirmed on the corrected basis **for variant 1.25 only**.
  Now conditional again pending A3 above.

## D — Open, carried forward

- **The redefined day is currently near-inert.** Phase 10 derived anchors on 04:00–20:00 ET, so
  zero anchors exist in the prior-evening and overnight span the new boundary adds. Relabeling can
  only push events out, never pull any in — and it moved exactly one sidecar event. The reason for
  the boundary change (attributing prior-evening activity the scanner's own measurement window
  includes) is **not yet realized** and requires re-running the D7 detection derivation on the
  redefined window. Whether that re-run happens is an open decision, not something Amendment 2
  settled.
- **T1.5 population question.** D14 = 20,951 canonical events against 114 with anchors is a 0.5%
  survival rate. Before this is treated as a blocker, Claude Code should state whether 114 is the
  full-population result (a severe attrition finding needing its own investigation) or a processed
  subset (a scoping artifact). The two need entirely different responses.
- **A2.7.D17_burst_envelope_boundary** — delivered in a3fe68b; listed as outstanding in Amendment 1
  in error. Pending Cooper's read of the entry as written.