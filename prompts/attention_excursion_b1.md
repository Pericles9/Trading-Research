> **Filing note (Claude Code, 2026-09-23).** Filed verbatim as received, on branch
> `explore/attention-excursion-b1`. **The document arrived truncated** at the 50,000-character
> message limit: it ends mid-row in Part II's escalation table (row 6, "thin paths above 20% of
> th"), so **escalation rows 6 onward and all of Part III (the E2 units fix and its retraction
> sweep) were never received** and are not reproduced here. Brief 1 (Part II) was run from this
> text; nothing in Part III was acted on. Part I here supersedes the v3 design filed at
> `claude/attention_and_the_excursion.md` (branch `claude/attention-and-the-excursion-v3`,
> `e46f5ea`), which is not on this branch.

# Attention and the excursion — design, Brief 1, and the E2 fix

**Date:** 2026-09-23 · **Version:** combined document. Replaces three documents, which now redirect
here: `claude/attention_logic_rebuild.md` (design, v3.1), `prompts/attention_excursion_b1.md` (Brief 1)
and `prompts/e2_units_retraction.md` (E2 fix). The repo copy filed by Claude Code at
`claude/attention_and_the_excursion.md` (branch `claude/attention-and-the-excursion-v3`, `e46f5ea`) is
the design at v3 and is superseded by Part I here.
**Companion:** `claude/relative_momentum_findings_log.md` holds every number from this line of work.
Every figure used here is summarised where it is used.

**Structure and status — the split matters even though the file is one:**

| part | what | status |
|---|---|---|
| **I** | the design: why the earlier attention logic failed, the excursion vector, the attention measures, fundamentals, predictions, controls, split, kill conditions, and all settled decisions | reasoning and design — **not runnable** |
| **II** | Brief 1: build the crossing instant on D1, measure the open boundary, build everything on the dev sample, run the four controls, stop | **runnable now**; ends at a hard stop |
| **III** | E2's 10× window units error and its retraction sweep | **runnable now**, independent |

---

# PART I — The design

## I.0 What this is, in one paragraph

**The goal is the relationship between attention — however it is best measured — and the stock's
excursion after the decision moment.** It is not an entry/exit mechanism and never was; v0–v2 turned it
into one, and every attention result since then has been tangled with the participation gate's entry and
exit. The excursion is turned into a short vector that is comparable across any two events, without
assuming the path has no drift — the rise-then-fall is expected and the vector is built to describe it.
Attention is measured strictly before the decision moment, in forms that are unitless and scale to each
stock's own activity, so a $0.30 name and a $12 name can sit on the same axis. Fundamentals come in where
they have a mechanism: as the denominator for attention (turnover) and as the only attention source with
its own clock (catalysts — SEC filings; news is deferred). Absolute and
cross-sectional attention are built side by side and read jointly, because each only means something
given the other. **If attention and the excursion vector line up, the vector becomes the ruler for both,
and a universe selection tool.**

---

## I.1 Why the earlier attention logic failed — kept short, all still true

| # | break | evidence |
|---|---|---|
| 1 | **Measured attention already arrived, not attention still arriving.** Buyers who already bought are in the price and are the future sellers | loudest decile worst on four trade definitions (Phase 11 fixed hold, v0, v1, exit overlay) |
| 2 | **The score measured obscurity.** Relative volume = current dollar volume ÷ the stock's own prior-3-day average | 84.5% of the score's spread came from the baseline; in 38% of contests the winner had less current trading than the loser |
| 3 | **Tape activity is made by the move.** Volume and price change come from the same order flow | score vs move 0.69; 63% of entries scored on a window containing the crossing burst |
| 4 | **"Relative" had no mechanism and rarely ran** | median candidate had no competitor; crowding-out never tested |
| 5 | **Tested only through the gate's entry and exit**, whose exit is itself attention-driven | 903 events, one 8-month slice, read three times |

Everything below is built to avoid all five.

---

## I.2 The outcome: the excursion vector

### I.2a What it has to do

- **Make any two paths comparable** — different prices, different trading speeds, different session
  segments.
- **Assume nothing about drift.** The theory says there is a drift up, then a drift down, with blurry
  boundaries. The vector describes that shape; it does not test it against a no-drift world.
- **Avoid boxes.** No minute windows, no fitted change point, no chosen horizon. The path runs from the
  decision moment to the end of the session, however long that is.

### I.2b Two normalisations, neither assumes no drift

**Clock — the stock's own trading.** Progress along the path is measured as the share of the
remaining session's volume that has traded, `u ∈ [0, 1]`, not minutes. A stock trading 5,000 times a
minute and one trading 50 times a minute are then on the same axis. This is the volume clock (Clark
1973; Ané & Geman 2000), and it is the direct answer to the programme's own lesson that *events do not
share a clock.* Wall-clock time is carried alongside every component, never discarded.

**Scale — the event's own noise.** Price moves are expressed in units of the event's own volatility,
`σ`, measured over the forward path. Drift barely affects a volatility measured on fine steps: over a
small step the random part is of size `√step` and the drift part is of size `step`, so as steps shrink
the drift contribution vanishes. `σ` is estimated with **bipower variation** (Barndorff-Nielsen &
Shephard 2004), which is also robust to jumps — halts and single-print spikes would otherwise inflate it.

**The path itself is built from equal-volume buckets**, not raw prints. Each bucket's price is its
volume-weighted average. This removes bid-ask bounce, which on a raw trade-to-trade series inflates `σ`
and deflates every height measured in `σ` units. Bucket count is declared as a ladder
`{50, 100, 200}` over the remaining session, read side by side, no rung privileged — there is no
economic derivation for one number, so it is not pretended.

**Heights are expressed over the whole path's spread, `σ_path = σ_b × √N`**, where `σ_b` is the
per-bucket noise and N the bucket count. (An earlier draft divided by per-bucket `σ_b`; that makes the
no-drift reference grow with N and the rungs incomparable. Over `σ_path` a no-drift path's expected peak
is about 0.80 on every rung.)

### I.2c The components

Three markers the path gives for free: **start** (the decision moment `τ`), **peak** (the highest bucket
price — this *is* the MFE), **end** (last print of the session).

| component | definition | captures |
|---|---|---|
| `u_peak` | volume-clock position of the peak, 0 → 1 | how much of the remaining trading the rise took |
| `rise_s` | log(peak ÷ price at τ) ÷ `σ_path` | height of the rise in noise units |
| `fall_s` | log(peak ÷ last price) ÷ `σ_path` | give-back after the peak, in noise units |
| `dip_before_peak_s` | largest drawdown between τ and the peak ÷ `σ_path` | whether the rise was clean or ragged (MAE before the peak) |
| `terminal_s` | log(last price ÷ price at τ) ÷ `σ_path` | where it finished — the quantity D25 found decays |
| `sigma_b_bp`, `sigma_path_bp` | noise, in bp | the link from noise units back to money |
| `rise_bp`, `fall_bp`, `rise_cents`, `fall_cents` | the same heights in money, both units | what the cost stack is compared against |
| `t_peak_s`, `t_end_s` | wall-clock seconds from τ to peak, to end | the wall-clock twin of `u_peak` |

**Edge classes, each its own row, never pooled or dropped:**

- **Rise censored** — the peak is in the last bucket; the rise never turned within the session. Same
  logic as the exit overlay's censored class, which held +1,702 bp at session end.
- **No rise** — the peak is at τ. `rise_s = 0`, everything is fall.
- **Halt inside the path** — carried with the gap proxy used in the exit overlay (any inter-trade gap
  > 60 s) and exact halt labels where they exist.
- **Thin path** — fewer than 250 prints after τ (an average of 5 per bucket on the coarsest rung).
  Declared, not derived.

### I.2d Reference shapes — eyeball lines, not tests

A path with no drift has known shapes on this scale, and they go on every chart as a line to read
against, never as a null the data must beat:

- **Peak height**: on average about **0.8** of the path's own spread (`√(2/π)` for a random walk).
- **Peak timing**: the **arcsine law** — a no-drift path's maximum piles up near the very start and the
  very end, not the middle. **A `u_peak` histogram with mass at both ends is what noise looks like.** A
  hump in the interior is what a rise-then-fall looks like. This single picture is the most direct test
  of the theory available, and it involves no attention measure at all.

### I.2e Optional, later: let the data name the shapes

Sample every normalised path at fixed points on the volume clock and run functional principal components
(Ramsay & Silverman): the dominant shapes come out of the data and each event gets coordinates on them.
**Used only to check whether the eight-number vector misses something**, never as the primary object —
it is the most elegant option and so the one to be most suspicious of.

---

## I.3 The attention side, rebuilt

All measured strictly before τ, asserted in code. All unitless or self-scaled, so they compare across
names without any own-history baseline.

### A1 — Turnover: attention as a share of the supply

> `turnover_τ` = shares traded from session start to τ ÷ shares outstanding as of τ

- **Why:** it measures how much of the available stock has already changed hands — the used-up buyer
  pool from I.1, break 1, stated in the right units.
- **Source:** `shs_shares_outstanding_corrected` from Build F1 — the SEC cover-page count as of the last
  filing accepted before `t0`, split-corrected.
- **It is shares outstanding, not float.** Float is always smaller, so this turnover is a **lower
  bound**, valid as a ranking, never as a level. E1 already built and charted it under that label.
- **Known bias, direction stated in advance:** a company diluting into the move carries a stale,
  too-small share count, so its turnover is **overstated** — on exactly the offering-adjacent events.
  Every A1 panel is split by the dilution flag so this surfaces rather than ships.
- **Carried per event:** `shs_lag_ns` (how stale the count is), `shs_quality`, and
  `shs_share_count_suspect` (146 events with implausible counts under 100,000 shares; diagnostic only).
- **Coverage:** 70–80% of D1 by year. The uncovered share is its own class in every table.

### A2 — Acceleration: is attention still arriving? The scale field, used as an envelope reader

**Yes, the scale field is useful here — but as an envelope reader, not a detector.** D26 closed the
timing channel with a precise result: above 10 ms, the trade-arrival record contains **the session
envelope and nothing else**. The envelope is the slowly varying trade rate — which is exactly what
attention is on the tape. So the field's burst-detection role is dead, and its rate-estimation machinery
is exactly the right tool for reading the envelope's slope.

> `λ_s(τ)` = causal trade-rate estimate at τ, one-sided kernel of scale `s` (D23 established the kernel
> must be one-sided — a centred kernel reads the future)
>
> `accel_s(τ)` = log( `λ_s(τ)` ÷ `λ_2s(τ)` ) — the rate over the recent scale against the rate over twice
> that scale. Positive means speeding up at that scale.

- **Read as a curve across scales, no scale privileged.** Scales run on a base-2 ladder.
- **It is a ratio of the name to itself**, so how quiet the stock usually is cancels out — break 2
  cannot recur.

**Zooming out — the ladder is anchored at the top, not the bottom (v3, 2026-09-22).** Left to itself the
field converges to extremely fine resolution: on a dense tape the resolution floor (`s ≥ 2.26 / λ`, the
applicability criterion that survived D22) sits at a fraction of a second, and a ladder built upward
from there spends almost all its rungs in the sub-second region D26 already closed as envelope-plus-
fragmentation. Attention builds over minutes to hours. So the ladder is built **from the coarse end
down**:

1. **Top rung = the event's own pre-decision history**, `H = τ − session start` (04:00 ET). The coarsest
   question is "is the second half of today's history busier than the first half?"
2. **Each rung below halves it:** `H/2, H/4, H/8, …` Every event gets the same octave structure relative
   to its own day, whether it crossed at 04:07 or at 14:30. No seconds are chosen anywhere.
3. **Stop descending at whichever comes first:**
   - the resolution floor, `2.26 / λ`; or
   - **the counting-noise stop** — the rung where the recent window holds too few trades to tell a
     doubling of rate from noise. A trade count `n` has relative error about `1/√n`, so resolving a
     doubling (log ratio 0.69) at two standard errors needs **at least 17 trades in each half-window**
     (derivation in Part II, T5).

In practice this means a handful of octaves per event, all in the region where attention lives. **The
simplest implementation needs no kernel at all** — count trades in each halving window and take the
ratio. The field's one-sided kernel is the smoothed version of the same thing, and its value is its
known instrument properties (the controls it has already passed). Build the simple count version as
primary and the kernel version as a check; if they disagree, that disagreement is itself the thing to
look at.

**Three lessons from the scale-field arc that bind this measure:**

1. **The bandwidth-composition artifact.** Re-estimating a rate at bandwidth `h` from a tape already
   smooth at `h` composes to `h√2` and produces spurious structure below about `3h`. A fast-vs-slow
   ratio is exactly the construction that can fall into this, so the positive and negative controls in
   I.6c are mandatory, not optional.
2. **The same read factor means different scales in different segments** (4.4 s in regular hours vs
   153 s premarket). Scales are anchored to the event's own rate, never to a fixed number of seconds.
3. **Dense and non-isolated at every scale.** There are no burst objects. Acceleration is a continuous
   quantity at each moment, never "a burst started."

**One new confound, specific to this measure:** crossings cluster at the two opens (04:00 and 09:30).
Activity accelerates at the open for every stock, so acceleration measured in the first minutes after an
open is partly the clock, not the name. **Open-adjacent crossings are their own class in every panel**,
with the boundary measured from the market-wide open surge (Part II, T3) and approved from the picture.

### A3 — Catalysts: the only attention source with its own clock

Every tape measure is partly the move, however carefully it is built. A catalyst is not: it arrives at a
timestamp that owes nothing to the tape. For an attention thesis it is also **causal** — it is where the
attention comes from.

**Most catalysts are not filings (Cooper, 2026-09-22).** Small-cap catalysts mostly arrive as press
releases over the newswires; an 8-K may follow later or never. So filings alone have low recall.

| source | status | what it gives |
|---|---|---|
| **SEC filings** (`flg_`) | held, 98.8% coverage, exact acceptance timestamps | a high-precision, low-recall catalyst flag |
| **News** | **deferred (Cooper, 2026-09-23)** — all-or-nothing, and a large infrastructure and data cost | — |

**Consequence, stated now:** the "no catalyst" group contains news-driven events, so any catalyst
comparison is biased toward no difference. A difference that shows up anyway is credible; no difference
is uninformative. If news is ever added, it first has to pass one check: an item published before τ,
with a timestamp that is when it first appeared, not a later backfill.

Carried as a **categorical conditioning variable**, never a score term: **filing within 24 h before τ /
none**, with hours from filing to τ alongside. The dilution flag is not a catalyst class — see I.5.

### Retired, kept, and not built

| item | disposition | reason |
|---|---|---|
| Relative volume (current ÷ prior-3-day baseline) | **reference column only** | measures obscurity (I.1, break 2) |
| Level gate, absolute floor, participation gate | **out of this design** | they belong to the entry/exit question, which this is not |
| **Hawkes self-excitation (branching ratio)** | **not built** | see below |

**Why the Hawkes measure is not built.** A branching ratio estimates how much activity is trades
triggering trades rather than arrivals from outside. On a tape whose arrival rate changes slowly across
the session, a Hawkes model with a constant background rate reads that slow change as self-excitation
and reports near-critical values that are not real — Filimonov & Sornette (2015) showed this directly
on high-frequency data. D26 says the envelope is the only thing on this tape. So a branching ratio here
would most likely be the envelope wearing a different label, and A2 already reads the envelope directly.
It would add an estimator, not information. Revisit only if A2 is flat and a time-varying-background
Hawkes model is specified.

---

## I.4 Fundamentals — what we hold and whether each earns a place

### I.4a What Build F1 holds (as-of t0, joined on the SEC company identifier, never on ticker)

| group | source | coverage (all events) | content |
|---|---|---|---|
| `flg_` filings | SEC submissions, acceptance timestamps (UTC, exact) | **98.8%** | last form before t0, lag, filings in 24 h / 72 h, dilution flag, 8-K item numbers |
| `shs_` shares outstanding | SEC cover page (`EntityCommonStockSharesOutstanding`) | **76.8%** (D1: 70–80% by year) | as-filed count, split-corrected count, as-of timestamp, lag, quality, suspect flag |
| `si_` short interest | vendor, twice-monthly settlement | 97.3% | shares short, days to cover, lag |
| `spl_` splits | vendor | 41.7% (a confirmed zero and a data gap are conflated) | splits in 365 d, reverse-split flag (always defined), last split ratio |
| `fin_` financial statements | vendor, frozen at first filing | 39.6%, **collinear with year** (2–5% in 2020–22, 48–66% in 2023–24) | revenue, net income, assets, liabilities, cash, share averages |
| short volume (daily) | vendor | archived, not in `event_fundamentals` | daily short volume and ratio |
| float | vendor snapshot | — | **banned from any computed quantity (D27)**: today's float attached to a past event is a lookahead |

**There is no float.** Tier 1 (shares outstanding) is built; tiers 2 (dilution correction) and 3
(affiliate subtraction) are not.

### I.4b Is there a reason to use them? Yes — three roles, each with a mechanism

The theory has two sides: attention is **demand**, and the rise ends when demand meets **supply**. Every
tape measure is demand-side. Fundamentals are the only data the programme holds on the supply side.

| role | columns | mechanism | use |
|---|---|---|---|
| **Denominator for attention** | `shs_` | turnover needs a share count (A1) | enables A1 |
| **Off-tape attention** | `flg_` catalyst class | exogenous attention arriving on its own clock (A3) | P3 |
| **Bias check on turnover** | `flg_dilution_form_before_t0` | a diluting company's share count is stale and too small, so its turnover reads high | control facet on A1 only — **not a prediction** (Cooper, 2026-09-22: dilution as a driver of the excursion is set aside) |

### I.4c What does not earn a place

| group | disposition | reason |
|---|---|---|
| `spl_` reverse split | **descriptive facet only** | real mechanism (compliance-driven shell cohort) but the sign on a noise-unit vector cannot be derived — it could run either way. No declared direction means no test |
| `si_` short interest | **descriptive facet only** | twice-monthly and published with a lag; it cannot know the state on the event day |
| `fin_` financials | **not used** | no articulated channel into a same-session move; coverage is a calendar artifact, so any split is a year split |
| float tiers 2–3 | **not built** | nothing has earned the weeks of work yet. If A1 matters and the dilution split shows the predicted overstatement, tier 2 becomes the obvious next build |

### I.4d Two governing rules that apply

- **D32 A1** — fundamental columns go against an outcome only as a small, pre-registered partition test
  with declared directions, within year and within detection-price decile, with the price partition run
  first as the competing explanation. I.5 declares exactly that.
- **This design supplies what the fundamental research was blocked on.** The September 13 proposal for
  preliminary fundamental research stalled on having no population-scale outcome variable, and proposed
  building excursion measures to be one. The excursion vector is that outcome — built from ticks rather
  than minute bars, so it is not the coarse screening version that proposal settled for.

---

## I.5 Pre-registered predictions — confirmed hesitantly (Cooper, 2026-09-22)

Declared before any excursion vector is computed. Three relationships. One is two-sided, and that is
recorded as honestly as the signed ones:

| # | predictor | predicted relationship | mechanism |
|---|---|---|---|
| **P1** | A1 turnover | **two-sided — no direction declared** | two opposite mechanisms, neither derivably stronger: *used-up buyer pool* → lower `rise_s`, earlier `u_peak`; *thin supply being absorbed* → higher `rise_s`, later `u_peak` |
| **P2** | A2 acceleration | **higher acceleration → higher `rise_s`, later `u_peak`** | attention still arriving |
| **P3** | A3 catalyst before τ vs none | **catalyst → higher `rise_s`, later `u_peak`** | exogenous attention on its own clock |

**What a two-sided P1 costs, stated now.** A test without a declared direction can find a relationship
either way, so it gets a stricter bar: **a monotone P1 curve counts only if the same sign appears in the
development slice and replicates in the selection slice.** A sign seen once is a hypothesis for the next
slice, not a result. If P1 comes back flat, both mechanisms may be present and cancelling — the joint
read in I.5a (turnover × acceleration) is where that would show, since the two mechanisms predict
opposite behaviour when attention is still arriving vs when it has stalled.

**Dilution is removed as a prediction** and kept only as the bias-check facet on A1 (I.4b).

**Relationships not predicted, and therefore descriptive only:** reverse-split cohort, short interest,
anything against `terminal_s` (D25 already measured the terminal value decaying unconditionally),
participant breadth such as odd-lot share (the mechanism gives both signs).

### I.5a Absolute and cross-sectional, built side by side

**They are contingent on each other, so neither gates the other (Cooper, 2026-09-22).** Absolute
attention only means something relative to what else is competing for the same traders, and a
cross-sectional rank only means something if attention itself organises the excursion. Reading one first
and gating the other on it would assume away the dependence. So both are built in the same pass, on the
same events, against the same excursion vector, and read on one surface.

**The two axes, per event at its τ:**

| axis | measures | comparable across names because |
|---|---|---|
| **absolute** — the name against itself | A1 turnover, A2 acceleration curve, A3 catalyst | unitless or self-scaled |
| **cross-sectional** — the name against everything live | **share of the live set's combined dollar flow** in the recent window (the name's dollar volume ÷ the sum over all live crossers, itself included); rank on A2 among live names; live-set size | dollars are dollars — the one quantity every name competes for directly, with no own-history denominator |

**"Alone" is a cross-sectional state, not a missing value.** A name with no competitor holds 100% of the
live flow. That keeps the 72%-plus of crossings that have no competitor inside the design instead of
outside it, and it turns density itself into a variable.

**How the contingency is read:**

1. **The joint surface.** Each excursion component on a grid of absolute measure × cross-sectional
   share, cell n in every cell. Neither axis is collapsed first.
2. **The interaction, stated as two questions:**
   - Does the absolute relationship (P2, and P1's sign) **change with competition** — same slope alone
     as when contested, or steeper when the name is taking the room's money?
   - Does cross-sectional share matter **holding the absolute measures fixed** — among names with
     similar acceleration, does the one taking more of the live flow rise further?
3. **The competition check runs in the same pass, not ahead of it.** When a new name crosses, does the
   trade rate of names already live drop against their own trend, compared with moments when nothing new
   crossed? No outcome involved. It is the mechanism under the cross-sectional axis: if it shows no
   drop, the cross-sectional share is describing co-movement, not competition, and it is read that way.

**Two confounds the cross-section carries that the absolute axis does not:**

- **Live names are at different points in their own moves.** The new crosser is at +30% by
  construction; names that crossed earlier are further along. Dollar share compares them anyway. Each
  live name's `move_at` and time since its own crossing are carried, and the share is also computed
  within live names crossed in the same octave of the day.
- **Liveness is a box.** A name has to be counted as live for some span after it crosses. There is no
  derivation for the span, so it is a declared ladder read side by side: **15 min, 60 min, rest of
  session**. A cross-sectional result that exists at one liveness only is a liveness result.

**Sample size, stated now.** At 15-minute liveness, the earlier crossing proxy put roughly 36% of D1
crossings in a contested moment — an upper bound. The contested half of the surface will be thin in
2021–2023 and thicker in 2024. Cells below 20 are shown, labelled, and not read.

### I.5b Universe selection

If the relationships hold, the excursion vector becomes the ruler for a combined score: a partition
defined before τ, on absolute attention × cross-sectional share × catalyst, that shifts the distribution
of `rise_s` and `u_peak`. That is a universe filter in D32 A1's sense.

**A necessary-condition cost gate, stated now:** an excursion no exit could harvest is worthless, and no
exit captures more than the full rise. So a partition only proceeds toward an exit design if its
**`rise_bp` exceeds the round-trip cost** (70.98 bp flat and 2.512 ¢ per share, both units) on a majority
of its events. Necessary, not sufficient — clearing it earns an exit study, not a strategy.

---

## I.6 The design — unchanged in shape

### I.6a Decision instant

**The tick-exact first print at or above 1.30 × the tick-derived prior close**, on all of D1. Every
name has made the same move at τ by construction, which removes break 3's confound instead of adjusting
for it. The speed of the run up to +30% is carried as a facet (wall clock and volume clock from session
start to τ).

Two build requirements:
- The earlier crossing proxy stamped **the first trade of the minute** whose high reached +30%, up to
  ~60 s before the real crossing — harmless for counting, a lookahead as a decision moment. It is
  replaced by the exact print.
- The prior close uses the exact closing-auction print rule (condition codes 8 and 15), not the last
  regular-hours minute bar the earlier `move_at` build used.

### I.6b Controls

- **Detection-price partition first**, as the competing explanation for everything. Price drives the
  per-share cost from −1,139 bp to +25 bp across deciles, and cheap stocks file, dilute and reverse-split
  more.
- **Within year**, because density triples from 2021 to 2024 and fundamental coverage is year-shaped.
- **Session segment** (premarket / regular / post) and **open-adjacent class** on every panel.
- **Random-permutation null** on each attention axis, seeded, so every curve has a noise reference.
- **Cross-session magnitude flag (A12)**: the +30% crossing is a cross-session ratio, so flagged events
  are reported as their own row.

### I.6c Instrument checks, on the 50-event dev sample, before anything touches D1

Per the four-control standard:

| control | construction | must show |
|---|---|---|
| **negative** | each event's own bucket returns, demeaned and shuffled | `u_peak` follows the arcsine shape, `rise_s` near 0.8; `accel_s` ≈ 0 at every scale on a constant-rate Poisson tape |
| **positive** | the same shuffled path with a known rise-then-fall drift injected at a known `u` | the vector recovers the injected peak location and heights; `accel_s` recovers an injected rate ramp |
| **null-parameter sweep** | bucket ladder `{50, 100, 200}`, kernel bandwidths | components stable across rungs; any component that moves with the rung is reported as rung-dependent |
| **blindness** | rescale prices by a constant; change the tick grid | vector invariant |

Numeric pass criteria are declared in Part II, T6. Only after these pass is the configuration frozen and the full-population run made.

### I.6d Reading rule

- The primary object is the **response curve**: each excursion component across the full range of each
  attention measure, in declared equal-population buckets, distribution and n in every bucket.
- **Evidence is monotone movement in the predicted direction, holding across bucket-ladder rungs, within
  year, within price tier.** A single good cell is declared now as not a result.
- No threshold is set inside the study. Cooper reads the curves.

### I.6e Split (D38)

Chronological, declared and committed before the first read:

| slice | dates | events |
|---|---|---|
| development | 2020-01-01 → 2022-12-31 | 7,650 |
| selection | 2023-01-01 → 2024-07-22 | 5,409 — contains the slice already read for relative volume; acceptable for selection only |
| **final** | 2024-07-23 → 2024-12-31 | 2,704 — never read for any attention measure; touched once |

**Repeat tickers are allowed across slices** (D38, Part II T0c). The standing ticker-blocked rule would
remove 83% of the final slice and 67% of the selection slice, because these names run again and again.
The rule exists to stop a fitted model memorising a ticker; this study fits nothing. So every uncertainty
estimate is clustered by ticker, and every read is repeated on first-seen tickers as a sensitivity. The
50 dev events and 6 sidecar events are quarantined from all three slices.

### I.6f Kill conditions, written before anything runs

1. **Step zero shows no rise-then-fall.** If the unconditional `u_peak` distribution across D1 looks like
   the arcsine shape and `rise_s` sits at the no-drift reference, the excursion is volatility on
   average. Attention can still split the population, but the theory's premise is not visible in the
   aggregate — recorded as such before P1–P3 are read.
2. **P2 is not monotone in the development slice** at any rung, alone or contested: **tape attention
   closes.** A3 (catalysts) is then the only attention measure left standing.
3. **P1–P3 all fail on both axes:** attention does not organise the excursion. The line closes as
   documentation.
4. **Competition absent and cross-sectional share flat holding the absolute measures fixed (I.5a):** the
   cross-sectional axis is removed for good. Either one alone is not enough to remove it — that is the
   contingency.
5. **Relationships hold but no partition passes the cost gate (I.5b):** real information, not a universe
   change. Recorded and handed to the exit layer as an input.

**Honest prior:** D25 closed the unconditional long thesis, and the level form of attention has failed
four times. What is different now is the question — the shape of the path rather than a trade's P&L — and
that the measures no longer restate the move. Both are reasons to run it once, cleanly. Neither is a
reason to expect it to work.

---

## I.7 Order of work

| step | what | touches outcomes? | cost |
|---|---|---|---|
| 0 | Build τ (exact crossing, exact prior close) on all of D1 | no | one tick pass over event folders (v0 read 1,027 folders in 66 s) |
| 1 | Build the excursion vector + attention measures (both axes) on the **dev sample**; run I.6c's four controls, including the counting-noise stop for A2 | dev sample only | small |
| 2 | Freeze config; build the vector, both attention axes, and the competition check on all of D1, in one pass | builds, does not read outcomes | one pass |
| 3 | **Step zero** — unconditional excursion vector, faceted, against the reference shapes | yes, unconditional only | cheap |
| 4 | P1–P3 on the joint surface, development slice, price partition first | yes | cheap |
| 5 | Selection slice (P1's replication bar applies here), then the final slice once | yes | cheap |

**Part II covers steps 0–1** (plus the open-boundary measurement) and ends at a hard stop. Steps 2–5 are later briefs. Step 3 can end the line before step 4 is written. **Part III** (the E2 units fix) is independent and can run at any time.

---

## I.8 What this does not do

- Does not design an entry, an exit, a hold, or a position size.
- Does not use the participation gate or any of its outputs.
- Does not use `momentum_pct` in any computed quantity; `move_at` is fixed at +30% by construction.
- Does not construct a composite score. Measures are read side by side.
- Does not use the vendor float, financial statements, or any fundamental column outside the declared
  roles (turnover denominator, catalyst flag, dilution as a bias facet on turnover).
- Does not set a threshold on anything.

---

## I.9 Decisions — all settled (Cooper, 2026-09-22/23)

| id | decision | value |
|---|---|---|
| **DA-1** | Session end | **event-day 20:00 ET** — the last print at or before 20:00 on the event day. Not end-of-tick-data |
| **DA-2** | Bucket ladder for the path | **{50, 100, 200}** equal-volume buckets, read side by side, no rung privileged |
| **DA-3** | Liveness ladder, cross-sectional axis | **{15 min, 60 min, rest of session}** after a name's own τ |
| **DA-4** | Open-adjacent boundary for acceleration | **measured, not chosen** — Part II T3 produces it; Cooper approves from the picture |
| **DA-5** | Split | **chronological, repeat tickers allowed, ticker-clustered uncertainty, first-seen-ticker sensitivity** — D38 |
| **DA-6** | Catalysts | **SEC filings only; news deferred** (all-or-nothing, large infrastructure and data cost). Low-recall proxy, biased toward no difference |
| **DA-7** | Predictions | P1 turnover **two-sided** (same sign in development, replicated in selection) · P2 acceleration **positive** · P3 catalyst **positive**. Dilution is a bias facet on turnover only |
| **DA-8** | Axes | absolute and cross-sectional built side by side and read jointly; neither gates the other |
| **DA-9** | Acceleration ladder | anchored at the top (the event's own pre-decision history, halved), stopping at the D22 resolution floor or the counting-noise stop (≥ 17 trades per half, derived) |

---

# PART II — Brief 1: build the instruments, read no outcome

**Type:** build. **Not a phase. Runnable now.** Produces instruments and controls; reads no
attention-versus-outcome relationship anywhere, including on the dev sample.
**Branch:** `explore/attention-excursion-b1`, cut from `explore/participation-exit-overlay` (it carries
the v1 crossing-proxy and v2/overlay artifacts this reuses).
**Outputs:** `results/attention_excursion/b1/` · `charts/attention_excursion/b1/` (per-task subfolders) ·
config `config/attention_excursion_b1.json`, **committed before any run**.
**Decisions consumed:** DA-1 … DA-9 (Part I, I.9).
**Ends at a HARD STOP (T7)** for Cooper's review. Nothing after it is authorised by this document.

## II.1 Standing constraints

D4 tick-derived only; spine numerics never enter a computed quantity; `momentum_pct` resolves folder paths
only · D5 long-only · D14 offline · D19 every cost-bearing figure in bp **and** cents · A12: the +30%
crossing is a cross-session ratio, so `flag_cross_session_extreme` is carried and every panel shows
flagged events as their own row · flag and carry, never drop · `unavailable`, zero and censored are three
distinct states · every membership and coverage claim is an executable assertion · commits stage named
paths only · charts dark theme, Plotly inline, one per file, n on every bucket.

---

## II.2 Tasks

### T0 — Population, membership, slices, decision record

**T0a.** D1 = `in_scope = TRUE AND source_file = 'file1'`, asserted at **15,763** against
`results/phase_5a/artifacts/sampling_frame.parquet`. Dev sample = `config/dev_sample_v3.json` (50
events), asserted; the 6 Phase-10 sidecar events (`dev_v4_sidecar`) are listed alongside.

**T0b — slice membership file, written, not read.** `results/attention_excursion/b1/slices.parquet`,
one row per D1 event: `slice ∈ {development, selection, final, dev_quarantine}` by
`event_date_canonical` — development 2020-01-01 → 2022-12-31 · selection 2023-01-01 → 2024-07-22 · final
2024-07-23 → 2024-12-31 · the 50 dev events and 6 sidecar events → `dev_quarantine` regardless of date.
Carry `ticker`, `first_seen_slice` (the earliest slice the ticker appears in) and `is_first_seen_ticker`.
Assert: slices partition D1 exactly; no dev/sidecar event outside `dev_quarantine`. Report counts per
slice and first-seen counts (expected ≈ 7,650 / 5,409 / 2,704 before quarantine).

**T0c — append D38 to `docs/Universe-Decisions.md`**, verbatim, and update the `CLAUDE.md` decision index
and next-free pointer (D39) in the same commit:

> **D38 — Measurement studies that fit no parameters may use chronological splits with repeat tickers.**
> *Date:* 2026-09-23 · *Gate:* attention/excursion design, Cooper-approved.
> **Decision.** For a study that fits, tunes or selects no parameter on the data being split, the
> standing ticker-blocked rule ("no ticker on both sides") is replaced by: chronological slices; repeat
> tickers permitted across slices; every uncertainty estimate clustered by ticker; every read repeated on
> first-seen tickers as a sensitivity.
> **Why.** The ticker-blocked rule exists to stop a fitted model memorising a name. With nothing fitted
> there is nothing to memorise; what remains is non-independence of repeat runs, which clustering
> addresses. Enforcing the rule on this universe removed 83% of the proposed final slice (2,254 of 2,704)
> and 67% of the selection slice (3,610 of 5,409) — these names run repeatedly.
> **Scope.** Any study that fits, tunes, or selects anything — a threshold, a weight, a model — remains
> under the ticker-blocked rule. A study that later begins fitting inherits the rule from that point.

### T1 — Exact prior close

Tick-derived prior XNYS session close (`exchange_calendars`, pinned), closing print resolved by the
Amendment 6 two-rule fix on condition codes `{8, 15}`. **Not** the last regular-hours minute bar the
earlier `move_at` build used. Report coverage, the count where the auction print is absent and the
fallback applies, and the distribution of |exact − minute-bar close| in bp against the earlier build.
Events where no prior close can be built: `prior_close_available = FALSE`, carried.

### T2 — Exact decision instant τ, all of D1

> τ = the first print on the event day at or after 04:00 ET with price ≥ 1.30 × prior close (T1),
> excluding a print that fails the **spike guard**.

**Spike guard**, the exit overlay's construction, adopted here as a declared rule for this build: a
print is a spike if it deviates by more than 3% from **both** its immediate neighbours **and** those
neighbours agree with each other within 3%. A spike cannot set τ; the search continues. Report how many
events' τ moved because of it and by how much.

Carry: `tau_ns` (int64 — never float64; v2 found float64 rounds tick timestamps by up to 128 ns),
`tau_price`, `tau_available`, `tau_session_segment`, seconds from 04:00, seconds from 09:30,
`flag_cross_session_extreme`.

**Check against the old proxy** (`results/relative_momentum/v1/artifacts/t5_d1_candidate_moments.parquet`,
which stamped the first trade of the minute whose high reached +30%): distribution of
`tau_exact − tau_proxy` in seconds. Expected 0–60 s for nearly all events. Values outside [−1, 61] s are
listed per event, not averaged.

### T3 — The open-adjacent boundary, measured (DA-4)

Crossings cluster at 04:00 and 09:30, and every stock's activity accelerates at an open. This task
measures how long that market-wide surge lasts, so the boundary is read off data, not chosen.

From `event_minute_bars_v2`, all D1 events, event day only: per event, per minute, `n_trades` divided by
that event's own median per-minute `n_trades` over the event day (so no single loud name dominates). Take
the cross-event median and IQR of that normalised rate at each minute of clock time from 03:55 to 10:30,
**excluding each event's minutes after its own τ** (so the profile is not the crossing burst itself).
Chart both opens at one-minute resolution with n per minute. **Propose** the boundary as the first minute
after each open where the median returns to within its own IQR of the level 10–20 minutes later; Cooper
confirms or replaces it at T7. **No outcome enters this task.**

### T4 — Build the excursion vector on the dev sample

Path: every print in (τ, last print ≤ 20:00 ET], event day only.

**Buckets.** For each rung N ∈ {50, 100, 200}: cut the path into N buckets of equal share volume. A print
larger than a bucket's remaining capacity is split across buckets at its own price. Bucket price = VWAP.
Assert: bucket volumes sum to the path's total volume; every print is assigned.

**Noise scale** (Part I, I.2). Per-bucket noise
`σ_b = sqrt( (π/2) · mean_i |r_i| · |r_{i−1}| )` over log bucket returns (bipower variation,
Barndorff-Nielsen & Shephard 2004: robust to jumps and halts). **Heights are expressed in units of the
whole path's spread, `σ_path = σ_b · √N`**, not per-bucket `σ_b`. Over `σ_path`, a no-drift path's expected peak is about
**0.80** on every rung (`√(2/π)`), so the rungs can be compared directly.

| component | definition |
|---|---|
| `u_peak` | cumulative-volume position of the highest bucket, 0 → 1 |
| `rise_s` | log(peak bucket price ÷ `tau_price`) ÷ `σ_path` |
| `fall_s` | log(peak ÷ last bucket price) ÷ `σ_path` |
| `dip_before_peak_s` | largest drawdown between τ and the peak ÷ `σ_path` |
| `terminal_s` | log(last ÷ `tau_price`) ÷ `σ_path` |
| `sigma_b_bp`, `sigma_path_bp` | noise in bp |
| `rise_bp`, `fall_bp`, `rise_cents`, `fall_cents` | heights in money, both units (D19) |
| `t_peak_s`, `t_end_s` | wall-clock seconds τ → peak, τ → end |

**Edge classes, each flagged, never dropped:** `rise_censored` (peak in the last bucket) · `no_rise` (peak
in the first bucket) · `halt_in_path` (any inter-print gap > 60 s, plus exact LULD-V3c halt labels where
they exist, via the overlay's `load_halt_labels`) · `thin_path` — **declared: fewer than 250 prints after
τ** (an average of 5 per bucket on the coarsest rung); thin paths are still computed where possible and
flagged.

### T5 — Build both attention axes on the dev sample

**Everything strictly at or before τ. Assert in code, as v0's `window_dollar_volume` did: any print with
`sip_timestamp > τ` reaching an attention quantity raises.**

**Trade counting uses the D26 identity-collapse rule** (`research/scale_field/subsecond_origin.collapse_tol`
at 10 ms): prints within the collapse tolerance that are one order reported many times count as one
trade. Raw print counts are carried alongside. Share volume is unaffected by collapsing.

**A1 — turnover.** Shares traded from 04:00 ET to τ ÷ `shs_shares_outstanding_corrected` from
`event_fundamentals`. Assert `shs_asof_ns < tau_ns` per event; any violation is a LOG row and the event's
turnover is `unavailable`, not computed. Carry `shs_lag_ns`, `shs_quality`, `shs_share_count_suspect`,
`flg_dilution_form_before_t0` (bias facet: a diluting company's count is stale and too small, so its
turnover reads high).

**A2 — acceleration, ladder anchored at the top.** `H = τ − 04:00 ET`. Rung k has window
`W_k = H / 2^k`, k = 0, 1, 2, …:

> `accel_k = ln( n_recent / n_older )`, where `n_recent` = collapsed trades in `[τ − W_k/2, τ]` and
> `n_older` = collapsed trades in `[τ − W_k, τ − W_k/2)`.

Descend while **both** hold, and stop at the first rung where either fails:
- **Counting-noise stop:** `n_recent ≥ 17` and `n_older ≥ 17`. Derivation: the standard error of a log
  count ratio is about `sqrt(1/n₁ + 1/n₂)`; resolving a doubling (ln 2 = 0.693) at two standard errors
  requires `sqrt(2/n) ≤ 0.347`, so `n ≥ 16.7`. Carried in config with the derivation, not tuned.
- **Resolution floor (D22):** `W_k / 2 ≥ 2.26 / λ_k`, with `λ_k` the collapsed trade rate over `W_k`.

`n_older = 0` with `n_recent > 0` is the class `from_nothing`, carried, never logged as +∞ in a numeric
column. Report the number of valid rungs per event.

**A2 check version:** the scale field's one-sided causal kernel rate (D23 requires one-sided) at scales
`W_k/2` and `W_k`, ratio logged. Report per-rung Spearman between the count version and the kernel
version. Disagreement is reported, not resolved.

**A3 — catalyst (filings only, DA-6).** From `event_fundamentals`: `filing_24h` = any filing accepted
within 24 h before τ; hours from the most recent filing to τ; `flg_last_form`; `flg_dilution_form_before_t0`
carried as a facet only.

**Cross-sectional axis.** For each dev event j, at its τ_j, and for each liveness L ∈ DA-3: the live set
is every D1 event on the same date with `τ_i ≤ τ_j ≤ τ_i + L` (j included). This needs τ for all D1 (T2)
and reads each live name's own folder.
- `live_n` — live-set size. **Alone is live_n = 1, not missing.**
- `flow_share_k` — j's dollar volume ÷ the live set's total dollar volume, over `[τ_j − W_k, τ_j]`, for
  each of j's valid A2 rungs. **All names are measured on identical clock windows at that moment.**
- `accel_rank_k` — j's rank on `accel_k` among live names, each name's counts taken over the same
  windows. Only names that clear the counting-noise stop on that window are ranked; the count ranked is
  carried.
- For each live name: `move_at` at τ_j (tick-derived, T1 prior close) and seconds since its own τ.

### T5b — Competition check: code built and validated on dev dates only

For a crossing j and each name i already live at τ_j (crossed earlier, within L): compare i's collapsed
trade rate in `[τ_j, τ_j + W]` against `[τ_j − W, τ_j]`, for W ∈ {5, 15, 60} min (declared ladder, no
derivation, read side by side). Matched control: for the same name i, moments within its live span with
no other D1 crossing within ±W, drawn with a seed from config. Output the paired log-ratio distributions,
crossing versus control. **Built and run only on the dates of the 50 dev events in Part II.** The full-D1
run belongs to a later brief after config freeze. It touches no outcome of j and is a mechanism check
only.

### T6 — The four controls (Control Standard), dev sample

Pass criteria are declared here. A failure is a HARD STOP.

| control | construction | pass |
|---|---|---|
| **Negative — excursion** | per event and rung, 200 seeded shuffles of demeaned bucket log returns, re-integrated from `tau_price` | pooled `u_peak` matches the arcsine distribution (chart against the CDF; KS distance reported); mean `rise_s` within **0.70–0.90** on every rung |
| **Negative — acceleration** | homogeneous Poisson tape with the event's own pre-τ trade count and span | `accel_k` centred on 0 (|median| < 0.1) with spread consistent with `sqrt(2/n)` at every rung |
| **Positive — excursion** | the shuffled path with an injected rise then fall: peak at u = 0.3, rise 2.0 and fall 1.5 in `σ_path` units | recovered `u_peak` within ±0.05; recovered heights within ±15%; on every rung |
| **Positive — acceleration** | inhomogeneous Poisson whose rate doubles at a known time before τ | `accel_k` ≈ ln 2 (within ±0.2) on rungs whose halves straddle the step, ≈ 0 on rungs that don't |
| **Null-parameter sweep** | the bucket ladder; count vs kernel A2 | component medians reported per rung; any component whose median moves more than 20% across rungs is labelled rung-dependent |
| **Blindness** | multiply every price by 10 and by 0.1; separately, round sub-$1 prices to the $0.01 grid | σ-unit and bp components identical to 1e-9 under rescaling; under rounding, the change is reported per event |

### T7 — Report and HARD STOP

`results/attention_excursion/b1/REPORT.md` (+ copy at `results/reports/attention_excursion_b1_report.md`).
Describes the pictures. No interpretation, no findings section, no recommendation.

**Charts** (one per file, dark theme, n on every bucket):
- T2: `tau_exact − tau_proxy` ECDF; spike-guard moves.
- T3: the open profiles at 04:00 and 09:30 with the proposed boundaries drawn.
- T4: one strip per dev event showing the bucketed path on the volume clock with τ, peak and end marked,
  at all three rungs. **This is the picture that shows whether the vector describes the path.**
- T4: pooled `u_peak` histogram per rung **with the arcsine reference drawn** (dev sample, unconditional,
  no attention split).
- T5: per-event A2 rung curves (accel vs k), count and kernel versions overlaid; valid-rung count
  distribution.
- T5b: crossing-versus-control log-ratio distributions per W.
- T6: one chart per control with its pass band drawn.

**Then stop.** Commit, push, post: the control table (pass/fail per row), the T3 proposed boundaries, T2
coverage, the `shs_asof` violation count, and the thin-path share.

---

## II.3 Escalation

| row | criterion | tier |
|---|---|---|
| 1 | `tau_available` below 90% of D1 | HARD STOP |
| 2 | any T6 control fails its declared pass criterion | HARD STOP |
| 3 | any print after τ reaches an attention quantity (assertion fires) | HARD STOP |
| 4 | `tau_exact − tau_proxy` outside [−1, 61] s for more than 2% of D1 | HARD STOP. The proxy and the exact rule disagree about what the crossing is |
| 5 | `shs_asof_ns ≥ tau_ns` for any event | LOG, per event |
| 6 | thin paths above 20% of th

[Received truncated here -- message exceeded the 50,000 character limit.]
