# Phase 10c — Amendment 5: Condition-Code Dictionary and Auction Rule

**Status:** Formal amendment. Supplies the dictionary Amendment 4 A1 required, sets the auction
code set, and records two findings the dictionary surfaced. One census (Section D) is requested
before Stage 1; the rest is settled here.

---

## A — The dictionary, retrieved

**Source:** Massive, *Conditions & Indicators* glossary —
`https://massive.com/glossary/conditions-indicators`. Retrieved 2026-08-25.

**Vendor identity note:** Polygon has rebranded to **Massive**. This is the same vendor as the
Massive API already used in the program for instrument classification, and the same vendor behind
the Phase 1b Amendment 1 API key. The `polygon.io` documentation URLs now redirect to
`massive.com`. Recording this so a future phase doesn't treat them as two sources.

**Phase 11 escalation row 22 is cleared, not bypassed.** That rule prohibits interpreting a
condition code *without a dictionary* — specifically, inferring meanings from the values
themselves. This is the vendor's own published table, obtained from the vendor's own
documentation. The prohibition was against guessing; this is not a guess.

**Required:** store this table on disk (suggest `data/metadata/`) so the offline environment (D14)
has it locally and no future phase repeats the retrieval. Also record it in
`docs/Open-Items-Register.md` against the open item Phase 11 T1c-iii created.

### Codes observed in the Phase 10c near-close census, decoded

| Code | Name | Updates volume? |
|---|---|---|
| 2 | Average Price Trade | Yes |
| 7 | Cash Sale | Yes |
| 8 | **Closing Prints** | Yes |
| 9 | Cross Trade | Yes |
| 12 | **Form T** — extended-hours trade | Yes |
| 14 | Intermarket Sweep | Yes |
| 15 | **Market Center Official Close** | **No** |
| 37 | Odd Lot Trade | Yes |
| 41 | Trade Thru Exempt | Yes |

---

## B — Auction code set: {8, 15}

**Decision:** the closing-auction rule (Amendment 4, A1) keys on **codes 8 and 15**. The proposed
set was {8, 9, 15}; **9 is dropped.**

### The empirical discriminant is now semantically confirmed

| Event | Codes | Reads as |
|---|---|---|
| ACET 2020-09-18 | [8, 9, 41] | Closing Print, executed as a Cross, trade-through exempt — a closing auction |
| ACET twin (92 µs later) | [15] | Market Center Official Close — the official close value |
| OST 2024-06-13 | [14, 12, 41] | Intermarket Sweep, **Form T** — extended-hours trade |
| CELH 2020-08-06 | [12] | **Form T** — extended-hours trade |
| BMR 2024-03-13 | [12, 37] | **Form T**, Odd Lot — extended-hours trade |

Claude Code's argument that exclusivity alone doesn't discriminate — code 12 being after-close
exclusive yet appearing on all three ordinary anchors — is confirmed by the dictionary rather than
merely consistent with it. **Form T is defined as a trade executed outside regular primary market
hours.** That is exactly why it is after-close exclusive and exactly why it does not mark an
auction. The reasoning was right for the right reason.

### Why 9 is dropped

**Cross Trade is not auction-specific.** Brokers cross customer orders during regular hours; the
code carries no session or auction semantics. Its after-close exclusivity in this cohort is a
property of these 114 events, not of the code, and would not be expected to hold on the full
population. ACET carries 8, so {8, 15} catches the anchor without depending on an ambiguous
member.

**Required before finalizing:** report how many prints in the near-close census carry **9 without
8 or 15**. Counts differ (8: 83, 9: 76), so some prints likely carry one without the other. If
that count is zero the choice is immaterial on this cohort; if it is non-zero, those prints are
exactly the ones {8, 9, 15} would have misclassified as auction.

### Scope — still needs confirming from Amendment 4

Amendment 4 A1 wrote the rule as applying to trades generally: trades identified as auction
activity belong to the session whose close they settle. Under that reading the set reassigns the
full near-close code-{8,15} population across session boundaries, not just the one ACET anchor.
**Confirm whether the intended scope is all trades or anchor classification only.** The error
tolerance on the code set is materially different between the two.

---

## C — Finding: code 15 is not a trade

The dictionary marks **code 15 (Market Center Official Close) as `updates_volume: No`** — along
with `updates_high_low: No` and `updates_last: No`. It is the dissemination of the official
closing value, not an execution.

**Consequence.** ACET's "twin" is not a duplicate trade. It is the official-close message carrying
the same price and size, 92 µs after the real closing print. The census counted **208 code-15
records across the cohort**, each sitting in the trade stream and each plausibly generating a
phantom sub-millisecond interval adjacent to a real print.

**Materiality:** 208 rows against millions is immaterial to the aggregate interval distribution.
This is not presented as an explanation of the v4 fragmentation result.

**Why it matters anyway:** it is the same class of problem — the interval stream contains records
the vendor does not consider trades, and Phase 10c has been treating every row as an execution.
The v4 lesson was that sub-millisecond structure is an artifact of what gets counted as a print.
That question has not been asked of the vendor's own metadata until now.

---

## D — Census requested: non-volume-updating records in the interval stream

**Not a decision — a measurement, before Stage 1.**

Report, across the cohort and by segment, the count and share of trade-stream records carrying
codes the vendor marks as **not updating volume**. From the retrieved table these include at
minimum:

| Code | Name |
|---|---|
| 15 | Market Center Official Close |
| 16 | Market Center Official Open |
| 38 | Corrected Consolidated Close (per listing market) |

Also report, separately, records carrying codes that update volume but **not** last sale or
high/low (2 Average Price Trade, 7 Cash Sale, 12 Form T, 13 Extended Trading Hours, 21 Price
Variation Trade, 37 Odd Lot Trade, 52 Contingent Trade, 53 Qualified Contingent Trade). These are
real executions and are not candidates for removal — the point is to know what the stream is made
of, not to filter it.

**No exclusion decision is proposed here.** Whether any record class is removed from the interval
stream is Cooper's call and would need its own amendment, since it changes what a "print" means
after Stage 0b already measured on the current definition.

---

## E — Detection-quality flag: BMR's anchor

BMR 2024-03-13's anchor carries **[12, 37]** — Form T and Odd Lot — at **5 shares**. A 5-share odd
lot in the after-hours session is setting T=0 for that event.

Recorded, not acted on. It is one sidecar event under one variant (1.35). But it is a concrete
instance of a general question the variant work has not asked: **whether detection should have a
minimum size or eligibility condition on the anchor print.** Flagged for the D7 re-derivation, not
for Phase 10c.

---

## F — A4 (evening σ) dissolves; no decision needed

Amendment 4 A4 asked how the new `evening` segment should get a σ for the A2.8 floor, given it
holds at most three events.

**The premise was wrong.** Per Claude Code's R2 note, the floor is derived **per event from that
event's own σ** — the 1.363 / 1.758 figures are segment summaries for reporting, not inputs. If
that is accurate, evening events get their own per-event floors and no segment-level evening σ
exists to set.

The only segment-level quantity in the chain was the **binding rung** used to derive the kernel
grid — and D6 = {2, 8, 32} is already fixed globally and confirmed across all three threshold
variants (Amendment 4, A3). Evening events are therefore evaluated against the global grid using
their own per-event floors, with `insufficient_context` applied per event/kernel pair as normal.

**Required:** confirm the floor is genuinely per-event. **If confirmed, A4 closes with no decision
and no borrowing.** If the floor is in fact segment-derived, A4 reopens as originally written and
comes back to Cooper.

---

## G — Amendment 4 items closed

- **4.A1 (dictionary)** — supplied in A above.
- **4.A1 (code set)** — set to {8, 15} in B, pending the 9-without-8-or-15 count and the scope
  confirmation.
- **4.A2 (evening segment)** — adopted; overnight span 20:00 → 04:00 confirmed measured-empty
  across all three variants.
- **4.A3 (grid re-check with ACET in RTH pool)** — binding rung holds at 8. D5 = 8 and
  D6 = {2, 8, 32} stand.
- **4.A4 (evening σ)** — dissolves per F, pending the per-event floor confirmation.
- **4.D (segment migration matrix)** — delivered. VEEE 2024-06-25 lost its anchor and CODX
  2020-03-11 moved premarket → rth between 1.25 and 1.30, both concealed by an identical rth
  marginal of 80. 1.30 → 1.35 changes 19 events.
- **Local reader vs. editing `research/phase_10/common.py`** — local reader confirmed correct.
  Phase 10 is closed and tagged; changing a closed phase's load path would alter its
  reproducibility for every future re-run. **Recorded as precedent:** later phases read what they
  need through their own readers rather than mutating closed-phase modules.

## H — Carried forward, not resolved here

- **`det_ns_*` stored as float64.** At epoch-nanosecond magnitude float64 spacing is 256 ns, so an
  anchor cannot round-trip exactly to its own print — an exact join silently returns nothing.
  Nearest-match recovers all four post-close anchors at 0 ns residual, so Phase 10c results are
  unaffected. **Two follow-ups:** (1) repair `det_ns_*` to int64 at source before anything depends
  on exact anchor times; (2) **confirm no timestamp-resolution measurement was computed from a
  float64 column** — T1 reported a median smallest non-zero gap of 80.5 ns and a minimum of 49 ns,
  both below the 256 ns quantization step. If those came from `sip_timestamp` (int64) they stand;
  if anything in that chain touched a float64 column, the figures are artifacts and the
  fragmentation-floor reasoning built on them inherits the error.
- **Auction rule is empirical plus semantic, not validated.** The dictionary confirms what the
  codes mean. It does not confirm that {8, 15} captures every closing auction in the archive, or
  that no non-auction print carries them. Standing limitation, carried into the phase.
- **Eligible-pool gap** — 15,299 eligible against D14's 20,951 canonical in-scope events, 5,652
  events (27%) unexplained. Open, required before any full-population run.
- **A2.7.D17_burst_envelope_boundary** — delivered in a3fe68b, still pending Cooper's read.