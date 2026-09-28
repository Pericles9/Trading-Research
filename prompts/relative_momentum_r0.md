# Relative momentum — qualification layer: scoping brief (R0) + R1 design inputs

**Date:** 2026-09-17 · **Version:** v3 — combines what were three documents into one.
**Supersedes:** `prompts/relative_momentum_r0.md` (v2), `prompts/relative_momentum_r1_inputs.md`, and
`prompts/relative_momentum_r0_amendment_1.md` (already superseded before this). No prior version ran;
there is no result to retract. Those three paths now redirect here.

> **Filing note, added by the R0 run (2026-09-17), not part of the brief as authored.** None of the
> three superseded paths exist in this checkout — `prompts/relative_momentum_r0.md`,
> `prompts/relative_momentum_r1_inputs.md` and `prompts/relative_momentum_r0_amendment_1.md` were
> never committed, so there is nothing to redirect and no redirect stubs were created. This file is
> v3 as authored, filed at the primary path so that `config/relative_momentum_r0.json`'s
> `_meta.prompt` citation resolves. Four further paths the brief cites do not exist in this
> checkout either and are marked `[unverified]` where they appear below:
> `claude/where_next_universe_criteria.md`, `claude/prompt_standard_amendment_v15.md`,
> `claude/fundamental_data_float_scoping_note.md`, `prompts/fundamental_exploration_e2.md`.
> See `results/relative_momentum/r0/REPORT.md` §0.

**Structure.** Part I is R0 — a scoping measurement, ready to send to Claude Code, not a phase, touches no
outcome. Part II is the design inputs for R1 — fixed before any data is seen, **not a phase brief, not
authorised**. The split in status is real even though the document is now one file: R0 can run today: R1
cannot start until R0's stopping gates clear.

---

# PART I — R0: does a cross-section exist, and does attention add anything to it

**Type:** scoping measurement. **Status: not a phase.** Records no decision, tests no hypothesis, produces
no finding, **touches no outcome variable.**
**Population:** D1 only — `in_scope = TRUE AND source_file = 'file1'`, n = 15,763.
**Outputs:** `results/relative_momentum/r0/` · `charts/relative_momentum/r0/`. Branch
`explore/relative-momentum-r0`.

## I.0 What is being scoped

A two-facet strategy. The facets are separable by design, and the separation is the point — failure
attribution requires separable model layers.

| facet | what it decides | status |
|---|---|---|
| **entry / exit** | when to get in and out of a given event | **exists** — the participation gate in `scanner-epg-momentum` (`backtest/epg_replay.py`, `setup_filter.py`). Entry on the gate's rising edge; exit on window close. **Restricted here to the first window only** |
| **qualification** | which event to be in at all | **to be developed** — an attention score, gated twice: above a level, and highest among live candidates |

**R0 scopes the qualification facet only, and it does not build the score.** It answers the two questions
that can kill qualification before anything is built, both from the existing cache with no new data pass.

**Why this direction is worth scoping.** It is the first candidate in this programme that satisfies
Criterion 5 from `claude/where_next_universe_criteria.md` `[unverified]`: selecting on a demonstrated
explosive move and going **long** the most explosive name bets *with* the property the universe was
selected for. That is the structural defect that closed the short side, and this does not inherit it.

**The reframing that decides what R0 measures.** Qualification is a **capacity-allocation problem, not a
prediction problem.** A ranker only has value when the gate fires on more names than can be taken. If it
opens on one name a day, every signal is taken and the ranker is decoration. If it opens on six, a choice
is forced, and the only question is whether attention rank beats choosing randomly or choosing whichever
fired first. That makes T4's random-pick arm the real benchmark rather than a formality, and it makes T1's
concurrency distribution the measurement that decides whether any of this is worth building.

## I.1 T0b is a stopping gate: are these the same population?

The participation gate's logic and its reported profit factor live in a **separate repository** with its
own event set, cost treatment and fill assumptions. **Mom-DB has never verified the two populations are
the same population.** There is an unresolved contradiction across the records that this brief sits
directly on top of:

| source | claim |
|---|---|
| Mom-DB Phase 11 | the median trade is **negative before costs** |
| `scanner-epg-momentum` Phase H / `hawkes-ofi-impact` Phase U | **PF = 1.5297** / **PF = 1.0962** on 100-event validation |
| `hawkes-ofi-impact` Phase K | escalated on **entry-edge mean cost-adjusted return ≤ 0** |

**The third row contradicts the second from inside the same codebase.**

**T0b — the overlap join.** Inner-join the participation-gate backtest's event set to
`momentum_events_canonical`. Assert set relationships **in both directions** in executable code: gate
events present in the canonical spine; canonical events the gate ever fired on; symmetric difference both
ways, with counts.

**This stops the brief on failure.** If the populations are materially disjoint, the profit-factor figures
are not statements about this universe, and every downstream task rests on a citation to another
repository's result — the defect class `claude/prompt_standard_amendment_v15.md` §B `[unverified]` exists
to catch. Post the table and **stop.**

## I.2 The correction that changes what gets computed

**`momentum_pct` cannot be the ranking variable, and must not be the collinearity control.**

It is a prior-close-to-**day's-high** measure, so at any moment during the session it is not yet known.
Phase 8 already prohibits it as a bucketing variable for that reason. A cross-sectional ranker built on it
would rank today's names using information that does not exist yet — the q05 lookahead defect in a new
costume.

**R0 defines a causal move measure and uses it everywhere `momentum_pct` would otherwise sit:**

> `move_at(e, τ)` = (last qualifying trade price for event `e` at or before `τ` − tick-derived prior
> session close) / prior session close

Tick-derived per D4. Prior session close uses the Phase 10c construction: prior XNYS session via
`exchange_calendars`, closing print resolved by the two-rule condition-code fix on `{8, 15}`. The spine's
`momentum_pct` appears only as a labelled diagnostic for cross-referencing prior phases and enters no
computed quantity.

## I.3 Pre-registered decisions

**DR-1 — Candidate set.** The candidate set at time `τ` on session date `d` is every D1 event whose
participation gate has fired its **first** rising edge at or before `τ` on `d`, subject to a liveness cap.

Liveness is carried as a declared sweep, **not** tuned: `L ∈ {15 min, 30 min, 60 min, no cap}`, all four
reported side by side, the multi-scale reading discipline Phase 10c uses. **The gate's own window close is
carried alongside as a fifth, competing liveness definition** and reported next to the clock-time caps —
it is the definition the deployed system would actually use. **Cooper approves the sweep before the run.**

**DR-2 — First window only. The justification is comparability, not performance.**

The gate's participation bar ratchets upward as an event progresses, so the second and third windows open
on a strictly higher and non-stationary bar than the first. **The first window is the only entry whose
qualification condition is stationary across events.**

**This must be the recorded reason.** Adopted because first-window results look better, the restriction
would be a scale parameter chosen by statistical convenience, which the standing constraint bans.

**DR-3 — Attention measures are strictly pre-`τ` causal.** Every measure is computed on a window ending at
`τ` and opening backward. No post-`τ` bar, print or quote enters any measure, asserted in code. Window
`W = 10 min`, matching E2's participation construction so the two read against each other.

| measure | definition |
|---|---|
| **print rate** | trade count in `[τ − W, τ]` |
| **dollar volume** | Σ price × size in `[τ − W, τ]` |
| **relative volume** | window volume ÷ `B_e`, where `B_e` is E2's flat 3-prior-session 10-minute baseline, reused unchanged |
| **quote update rate** | quote message count in `[τ − W, τ]` |
| **exchange breadth** | distinct executing exchanges in `[τ − W, τ]` |
| **sweep-order share** | share of prints in `[τ − W, τ]` carrying condition code 14 (intermarket sweep) |

The sweep flag already exists as a byproduct of the timing-channel cleanup — confirm before deriving it
fresh. It is the only candidate in the set that is **not a restatement of "lots of volume"**: it measures
urgency rather than quantity. Prior art: Chakravarty, Jain, Upson & Wood (2012) on sweep prints as a
price-discovery marker.

`n_baseline_sessions` (0–3) and `baseline_thin` carry forward from E2 and **facet every relative-volume
panel.** A one-session baseline is a different measurement from a three-session one.

**DR-4 — Share-count normalisation, with a required arm.** Cooper's call is to normalise on tier-1 shares
outstanding now rather than block on the dilution correction. The condition is that the predicted failure
is checked rather than shipped.

`claude/fundamental_data_float_scoping_note.md` §4 `[unverified]` states that skipping the dilution tier
*"does not produce a slightly stale float; it produces the wrong one precisely where the interesting
events are."* Applied to a denominator, the consequence is **directional and known in advance**: a name
diluting into the move carries a stale, too-small share count, so its attention-per-share is
**overstated** — and offering-adjacent events are plausibly the ones most likely to fail.

> **Required arm: every normalised measure is computed both with and without the share-count denominator,
> and both are split by `flg_dilution_form_before_t0`.** If the denominator helps only on non-diluting
> events, the sign error surfaces instead of shipping.

The vendor float endpoint stays banned from every computed quantity per the scoping note §2. Tier-1 counts
carry `float_lag_ns` and `float_quality`; no panel pools across quality tiers without faceting on them.

**DR-5 — R0 touches no outcome.** No forward return, no excursion, no expectancy, no cost-unit quantity,
no continuation measure of any kind. Those are R1 — Part II.

## I.4 Tasks

**T0a — Population and membership.** D1 in code with an asserted count. Assert the `move_at` recompute
covers the full D1 set; report as a first-class number the events where the tick-derived prior close
cannot be built. Carried, never dropped.

**T0b — THE OVERLAP JOIN.** §I.1. Post the table and **stop** on material disjointness.

**T1 — Day density. This is the gating measurement.**

Per session date: count of D1 events, count with a first gate rising edge, and the clock-time distribution
of those edges. Then, on a 5-minute grid across the extended session, the **candidate set size at `τ`**
under each of DR-1's five liveness definitions.

Report as a distribution, not an average. Roughly 15,763 events over four years averages to a number
almost no day resembles; the count is expected to be dominated by a small number of frenzy sessions, and
the mean of that distribution is a fiction.

**Faceted by year, mandatory.** If the cross-section exists in 2021 and not in 2023, a regime-dependent
cross-section is itself the result and must not be averaged away.

**T1c — What the restriction costs.** Gate windows per event, and what first-window-only does to the
candidate count. The "~150 trades per event" figure belongs to `hawkes-ofi-impact` and is **withdrawn as a
reference point for this work.**

**What T1 decides:** if the median session carries fewer than two simultaneously live candidates,
cross-sectional ranking is not available and the idea collapses into a single-name intensity rule — a
different idea, testable, but not this one. **No threshold is pre-set**: the shape of the distribution,
not a summary number, carries the decision, and Cooper reads it.

**T2 — Does attention add anything to the move itself?**

On observations where the candidate set has ≥ 2 members, at each `τ`, rank candidates by `move_at(e, τ)`
and by each DR-3 measure. Two reported objects, in this order:

1. **The rank-rank scatter** per measure, cell counts shown. Distribution before any aggregate. Spearman ρ
   reported *alongside*, never in place of it.
2. **Top-1 disagreement rate** — the fraction of `(d, τ)` observations where the attention-ranked leader is
   a different ticker from the move-ranked leader.

**Disagreement is the decision-relevant instrument; ρ is the diagnostic.** A correlation of 0.8 is
compatible with the same name leading almost always *and* with the leader differing a third of the time;
only the second leaves an attention ranker anything to do.

**Faceted by candidate set size** — with two candidates, disagreement is a coin flip by construction — **and
by the score margin between leader and runner-up.** Two candidates a fraction apart make "highest" noise;
the disagreement rate is uninformative without knowing how often the lead is decisive.

**T3 — The cost check, which Phase 11 makes load-bearing.**

Phase 11 found net edge is a function of detection-price level, and the round trip is fixed at 70.98 bp /
2.512 cents and does not scale with horizon. **If loudest-on-the-tape systematically selects the cheapest,
most fragmented names, this makes the cost problem worse rather than better.**

Attention rank against detection-price decile, distribution per cell, cell n shown. Near-zero marginal
cost, and the check most likely to come back against the idea that motivated the brief.

**T4 — Arm zero.** Candidate set size and top-1 disagreement with attention replaced by a random
permutation of the candidates — same grid, same facets, seeded from config. The negative control required
by the Control Standard: it establishes what disagreement arises from nothing, so T2's number has a
reference. Without it, a disagreement rate is a number without a scale.

**T5 — Filing proximity, optional.** Form type and minutes elapsed for the nearest filing accepted before
`t0`, from the EDGAR daily index. Carried as a **categorical conditioning variable**, never as a term in
any score. `claude/fundamental_data_float_scoping_note.md` §6 `[unverified]` ranks it above every
balance-sheet field, and for an attention thesis it is **causal** — a prospectus supplement or 8-K is
where attention comes from. **Skip if the daily index is not yet parsed;** R0 does not block on it.

**T6 — Report.** `results/relative_momentum/r0/REPORT.md`. Describes the pictures. No interpretation, no
recommendations, no findings section.

## I.5 Conventions carried

Dark theme · per-task chart subfolders · distribution before any aggregate · outliers flagged, never
deleted · `unavailable`, zero and censored are three distinct states, never collapsed · every membership
and coverage claim asserted in executable code, not prose · the agent describes the picture, Cooper
decides what it means.

## I.6 What R0 does not do

- Does not touch 2025 or non-file1 events.
- Does not use `momentum_pct` in any computed quantity (§I.2).
- Does not measure any outcome, return, excursion or expectancy (DR-5).
- Does not construct a composite attention score. Measures are read side by side; combination is out of
  scope, as in Phase 10c.
- Does not set any threshold, on attention or anything else.
- Does not promote anything to a universe criterion or an entry signal.
- Does not modify anything in `scanner-epg-momentum`. That repository is **read-only** to this brief.

## I.7 Open — requires Cooper before the run

- **The liveness sweep** (DR-1), including whether the gate's own window close is the primary definition
  rather than the fifth.
- **The ratcheting reading** (DR-2). First-window-only is justified here by the participation bar
  ratcheting upward across windows, making later windows non-stationary. **Confirm or correct**; the
  justification is load-bearing and is the only thing keeping the restriction out of the
  chosen-by-convenience category.

## I.8 Two things to have in view before R0 is read

**Criterion 2 is violated and the qualification idea makes it bite.** The archive keeps only names that
crossed +30%, not what the screen declined. R0 dodges this by defining the cross-section as *today's
crossers so far*, which is genuinely observable in real time — but that is narrower than "the stock with
the most attention right now," and it is the only version the data supports. Widening the claim later
requires new collection, not new analysis.

**R0 seeds priors.** After it is read, no split can honestly be called pre-registered unless it was written
down first. R0 is documentation; anything tested in R1 is either declared before this report is read or
labelled exploratory.

**On external attention data.** The ranking may eventually use anything, including news, social and search
volume. Two constraints: it is bound hard by Criterion 1 — only usable if point-in-time correct at
intraday resolution, timestamped when the attention arrived rather than backfilled, which most vendors'
historical products fail invisibly — and **it cannot rescue T1.** If there is no cross-section on a typical
day, no attention source of any kind produces one. Density is a property of the universe, not of the
measurement. R0 is therefore deliberately tape-only.

---

# PART II — R1: design inputs, recorded before any data is seen

**Type:** recorded design inputs. **Not a phase brief. R1 is not authorised by this document.**
**Purpose:** fix the inputs while nothing has been observed, so that when R1 is written it is written
against decisions rather than against a distribution.
**Blocked on:** Part I's overlap join (T0b) and concurrency distribution (T1).

## II.1 The reading rule, which determines everything else

**No parameter in R1 is fitted. Nothing is set by looking at the data first.**

Two constructions carry the whole design, and between them they remove the free-parameter problem rather
than managing it:

1. **The response curve is the primary object.** R1 reports continuation as a **function of the attention
   score across its full range** — finely bucketed, with the distribution in every bucket and its n. No
   threshold is set inside R1. Cooper reads the curve and places the gate where the economics work, the
   same Class E / Class M split Phase 10c uses: economically derived values fixed before, measurement
   derived values fixed at approval.
2. **Where a ladder is unavoidable it is declared a priori and read across, never selected from.** The
   evidence is the **pattern across the ladder**, not the best cell.

> **What R1 looks for: monotone improvement in continuation as the attention axis is climbed, holding
> across the drawdown ladder. A single favourable cell is not a result and is pre-declared as such.**

**The honest caveat, recorded rather than buried.** A human placing a threshold on a curve is still a
choice with degrees of freedom — fewer, and reasoned rather than swept, but not free. **The final slice is
therefore untouched by R1** and is spent once, on the gate that Cooper sets from R1's curve.

## II.2 The two continuation definitions. Both are carried

They fail in opposite directions, and the contrast is what makes running both worth more than choosing.

| | **C1 — change while the window is on** | **C2 — change before a drawdown stop** |
|---|---|---|
| what exits you | the participation gate | the price path |
| endogenous to attention | **yes** | no |
| relation to the trade | exactly what would be captured | approximate |
| role | deployment measure | research measure |

- **C1 predicts, C2 does not** → the relationship is window duration, not price continuation. The score is
  measuring the gate measuring attention.
- **C2 predicts, C1 does not** → the gate's exit is destroying an edge present in the price. An exit-design
  finding, on the axis that already dominates variance and ruin risk.
- **Both** → real. **Neither** → closed cheaply.

**II.2a — C1 must be decomposed.** Window length is set by participation and participation is driven by
attention, so change-while-open is partly a measurement of **how long the window stayed open.** This is
the same mechanical coupling `prompts/fundamental_exploration_e2.md` §3 `[unverified]` flags between
momentum percent and participation duration.

> change-while-open = **duration** × **average rate of change**

Attention against **duration** is close to tautological. Attention against **displacement given duration**
is the question. The two are reported as separate objects and **never blended into one number.**

Maximum favourable excursion inside the window is carried as a diagnostic, because otherwise "never went
up" and "went up and gave it all back" record identically — opposite situations for exit design.

**II.2b — C2 must be causal.** A drawdown threshold expressed against the *total* move uses the full
excursion, including the part that has not happened yet. The causal form ratchets:

> the stop triggers when `(running_max − price) ≥ d × (running_max − entry)`, where `running_max` is the
> maximum since entry

**Percent-of-move rather than percent-of-price is the right construction**, and the reason is recorded: an
event that runs 30% and one that runs 300% do not share a price scale any more than events share a clock,
and a fixed percent-of-price stop additionally collides with the tick-pinned absolute spread structure
Phase 11 found.

**II.2c — the denominator floor is round-trip cost, not a chosen number.** When `(running_max − entry)` is
small the ratio explodes on noise. A cell is **valid for an event only where
`(1 − d) × (running_max − entry) ≥` round-trip cost** — 70.98 bp / 2.512 cents, read from config, not
re-derived. Events failing it at a given `d` are reported as their own class at that cell: never pooled,
never dropped.

## II.3 The ladders, derived a priori

**No value here is chosen by looking at a distribution.** Each is a structural endpoint or a base-2 step,
the same construction as Phase 10c's log-spaced kernel grid.

**II.3a — Drawdown ladder.** `d ∈ {1/8, 1/4, 1/2, 1}`

- `d = 1` is the **structural endpoint**: the whole move is given back, the exit is at entry, breakeven.
  Beyond it the stop sits below entry, which is a different rule.
- `d = 1/2` is the scale-free midpoint — half the move returned.
- `d = 1/4` and `1/8` continue the series downward into the tight-trail region.

**II.3b — The attention axis is a curve, not a ladder.** Continuation is reported against the score's full
range in declared equal-population buckets, with each bucket's distribution and n. If a summary read is
wanted alongside, it is taken at declared percentiles `{50th, 75th, 90th, 95th}` — chosen a priori as
round points on a rank transform, **not placed where continuation looks best.** Monotonicity across the
curve is the evidence; no point on it is privileged.

**II.3c — Margin ladder.** `k ∈ {0, 1/2}` of the day's cross-sectional score spread, `k = 0` being the
no-margin control. A **secondary two-value read**, not a third grid axis.

**Grid size.** The primary surface is the drawdown ladder × the attention curve, read side by side. Even
four drawdown rungs against a bucketed curve is a wide multiple-comparison surface — which is exactly why
§II.1's reading rule is monotonicity rather than best-cell.

## II.4 The split

**Chronological, ticker-disjoint across boundaries, three-way.** Declared and committed before the first
read; the final slice is read exactly once.

- **Random assignment leaks.** The same ticker appears on both sides, and frenzy days place correlated
  events in train and test simultaneously. Phases 9 and 10e already cluster bootstrap by event and ticker;
  the same logic binds the split itself.
- **Three slices, not two** — development, selection, and a final slice touched once, ever. Even under
  §II.1's no-fitting rule, reading one holdout repeatedly degrades it.
- **Chronological, because the concurrency Part I T1 measures is probably regime-dependent.** A random
  split hides a 2021-versus-2023 difference; a chronological one surfaces it. **Era composition is
  reported on every slice**, so a failure is attributable to regime rather than to signal.
- **The 56-event dev sample is quarantined from R1.** It has been examined extensively and is stratified
  on print count. Not eligible for anything fitted, selected, or validated.
- **Slice sizes are not set here.** They follow from the overlap join: how many of the 15,763 D1 events the
  participation gate actually fires on.

## II.5 Scope note on the absolute gate

The gate's level is calibrated **conditional on the event having crossed +30%.** It is a statement about
continuation *after* the crossing, not about attention levels in general, and it is valid only applied to
names that have crossed.

It must not be transported to a universe without the crossing filter, and no report may state it as a
general claim about attention. The universe's survivorship — only crossers are stored — does **not** bite
here, because the outcome that varies is continuation, and both of its classes are present in the archive.

## II.6 Open, and blocking

- **The ratcheting reading**, carried from Part I §I.7. First-window-only is justified by the
  participation bar ratcheting upward across windows. Cooper confirms or corrects.
- **R1 is not written.** It waits on the overlap join and on Part I T1's concurrency distribution. If the
  median session carries fewer than two simultaneously live candidates, the relative half of the
  qualification layer does not exist and R1 is rescoped to the absolute half alone.
