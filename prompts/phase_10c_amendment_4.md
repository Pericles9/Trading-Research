# Phase 10c — Amendment 4: Closing-Print Rules and Population Tier

**Status:** Formal amendment. Resolves the two items left blocking after Amendment 3. One
measurement (A1 below) is still required before the first rule can be written; the second rule and
the population decision are settled here.

---

## A — Closing-print handling: two rules, not one

The post-close anchor population is bimodal across four orders of magnitude, and the gap is
substantive rather than dispersion — the two groups are different phenomena and get different
treatment.

| Event | Offset past close | Variant | Nature |
|---|---|---|---|
| ACET 2020-09-18 | +0.0078 s | 1.25, 1.30 | Closing cross |
| OST 2024-06-13 | +31.2 s | 1.35 | After-hours trade |
| CELH 2020-08-06 | +4,477.9 s | 1.35 | After-hours trade |
| BMR 2024-03-13 | +5,297.2 s | 1.35 | After-hours trade |

**A grace window is rejected.** Calibrating one would require a reporting-lag distribution, and
there is exactly one closing-cross observation to derive it from. A constant set on n=1 is the
kind of statistically-convenient scale parameter this program rules out everywhere else.

### A1 — Auction prints: assigned to their originating session, keyed on condition codes

**Decision:** trades identified as closing-auction activity by condition code belong to the session
whose close they settle, regardless of timestamp. No constant, no tolerance window.

**Rule not yet writable.** The ACET anchor print (21.40 × 229,769) carries codes [8, 9, 41], while
its twin 92 µs later carries [15] — the closing cross reported twice, and **the anchor is not the
[15] print**. Keying on the obvious closing-print code would miss the actual anchor. Setting the
rule off a single event would repeat, in miniature, the error A1 of Amendment 3 just corrected.

**Required of Claude Code before the rule is set:**

1. Add `conditions` to `_TRADE_COLS`. It exists in every `data/filtered/<event>/trades.parquet` and
   has never been read by Phase 10c. Low risk — reading an additional column changes the load path,
   not any computed result — but it should be a recorded change, not a silent one.
2. Report the **cohort-wide condition-code distribution** for prints at or near session close,
   across all three threshold variants.
3. Report the **archive's own code definitions** from its documentation. Do not use assumed or
   remembered code-to-meaning mappings; state the source.
4. Propose the code set the rule keys on, with the distribution as its justification. Cooper sets
   it; the agent does not select it.

### A2 — After-hours anchors: a new segment, not an exclusion

The three after-hours events are **not artifacts**. Under Amendment 2A the trading day begins at
the prior session close, so activity between the close and 20:00 legitimately belongs to the
following day. Those events' momentum triggers occurred in the evening session — that is a real
finding about when they fired, not a boundary error.

**`outside_redefined_day` is therefore the wrong label** and is retired. Post-close activity is not
outside the day; it is the opening span of the next one.

**Decision: a new segment, `evening`, covering prior session close → 20:00 ET.** Plain name, no
abbreviation.

The full segment set under the redefined day becomes:

| Segment | Span |
|---|---|
| `evening` | prior session close → 20:00 ET |
| `premarket` | 04:00 → 09:30 ET |
| `rth` | 09:30 ET → session close |

**`post` is retired as a segment.** Under `(prior close, this close]` the day ends at the close, so
no post-close span exists within it by construction.

**Gap to resolve:** 20:00 → 04:00 ET is inside the redefined day but carries no segment, since
regular venue trading does not occur there. Claude Code should confirm whether any anchors fall in
that span across the three variants. If none do, record it as measured-empty rather than assumed
empty. If any do, they need their own handling and this amendment is incomplete.

### A3 — Downstream re-check required (this changes σ again)

Amendment 3's A3 confirmed the RTH binding rung holds at 8 minutes across all three variants. The
rules above change segment membership again, so that confirmation is now conditional:

- **ACET moves to `rth`** under variants 1.25 and 1.30, adding one event to the RTH σ pool (37 → 38).
- The three after-hours events move to `evening`, which does not affect the `rth` or `premarket`
  pools — they were never in them.

**Required:** re-derive the A2.8 floor table with ACET included in the RTH pool. One event in 38 is
unlikely to move the binding rung, but "unlikely" is not "checked."

- **If the rung holds at 8:** D5 and D6 stand, no escalation.
- **If it moves:** stop and escalate. Do not apply a new grid.

### A4 — The `evening` segment has no usable σ

`evening` will hold at most three events, all under variant 1.35. A per-segment σ estimated on
n≤3 is not a reliable basis for A2.8's derived floor.

**Not resolved here — Cooper's decision, flagged for the Stage 1 prompt.** The options are to have
`evening` borrow `premarket`'s σ (defensible on the grounds that both are thin extended-hours
sessions, but it is an assumption, not a measurement), or to carry `evening` events as
`insufficient_context` for floor purposes and report them descriptively without a derived floor.
The second is more honest and is my recommendation, but it is not the agent's call.

---

## B — T1.5 population: dev tier, Stage 1 proceeds

**Decision: Phase 10c runs on the pinned dev sample. T1.5 does not block Stage 1.**

114 is a deliberate stratified subset (5 per `t0_print_count` decile per arm, from a 15,299-event
eligible pool: 50 + 50 + 8 + 6), not attrition. Nothing was lost. Detection was only ever derived
on those events.

This is exactly what the program's two-tier architecture specifies: a pinned dev sample for
iteration, one full-population run on frozen config. Phase 10c is iteration work. Running D7
detection across the remaining 20,837 events to unblock a dev-sample refinement stage would invert
that architecture — the expensive full-population pass should follow config freeze, not precede it.

**Carried forward for the full-population run, not now:** the eligible pool was 15,299 against
D14's 20,951 canonical in-scope events — **5,652 events (27%) were not eligible for Phase 10
detection at all.** The reason needs to be established and recorded before any full-population run,
since it silently bounds what that run can cover. Not urgent; must not be forgotten.

---

## C — Reporting consequence of Amendment 3's A1

The measured anchor-timing deltas (median 112.9 s for 1.25↔1.30, 313.6 s for 1.25↔1.35, max
13,856 s) are comparable to the kernel widths themselves — the 2-minute kernel is 120 s against a
112.9 s median disagreement, and only the 32-minute kernel is comfortably larger than the widest
pair's median.

**Required in the Stage 1 digest: outputs split into two classes, reported separately.**

- **Anchor-independent** — void gate, threshold location, sub-burst duration, spacing between
  sub-bursts. Computed on centered windows around each print; the variant arms should agree
  closely here, and disagreement would itself be a finding.
- **Anchor-relative** — sub-burst position relative to detection, near-anchor density, which
  sub-burst is first or largest since detection. These inherit the full variant delta. Under D8
  these are the quantities the phase exists to produce, so the inherited uncertainty must be
  stated alongside them rather than left for interpretation time.

---

## D — Additional measurement request

**Per-event segment migration matrix across the three threshold variants.** Amendment 3's marginal
counts showed rth at 37 under both 1.25 and 1.30, which is fully compatible with events swapping in
and out offsettingly. Aggregate counts already concealed the timing deltas once; the same error
class applies to segment membership. Report per-event, not marginal.

---

## E — Standing caveat: the 1.35 arm

Analysable subset by variant, within the fixed 56-event dev manifest:

| Threshold | Anchored | rth | premarket | unlabelled |
|---|---|---|---|---|
| 1.25 | 54/56 | 37 | 16 | 2 |
| 1.30 | 53/56 | 37 | 15 | 3 |
| 1.35 | 45/56 | 28 | 15 | 11 |

The three arms are comparable in grid (D5/D6 hold globally) but **not in power**. The 1.35 arm
carries 80% of the sample overall and 76% of RTH. Its cells will be materially noisier, and that
must be stated wherever the arms are compared — a cleaner-looking result under 1.35 could be
thinner data rather than better structure.

---

## F — Amendment 3 items closed

- **3.A1** — delivered. The withdrawal of "1.25 and 1.30 differ by one event" is confirmed by
  measurement; the variants differ by a median of nearly two minutes in T=0 and by more than a
  minute on 59% of events.
- **3.A3** — grid holds across all three variants. Now conditional again pending A3 above.
- **3.A4** — the dev manifest is variant-independent (drawn on `t0_print_count` before detection
  existed, so no circularity between sample selection and the measured quantity). What varies is
  anchor availability within the fixed 56, not the sample itself.
- **3.D (T1.5)** — resolved in B above.
- **3.D (eligible-pool gap)** — open, carried to the full-population run.
- **A2.7.D17_burst_envelope_boundary** — still pending Cooper's read of the delivered entry.