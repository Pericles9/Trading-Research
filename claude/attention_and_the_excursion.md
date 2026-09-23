# Attention and the excursion — rebuilt design (v3)

**Date:** 2026-09-22 · **Type:** reasoning document and proposed design. **Not a phase, not a brief,
not authorised.** Supersedes v1 and v2 of this document (same path, same day). v3 changes: A2's ladder
zooms out from the event's own history; catalysts extend beyond filings to news; turnover is two-sided;
dilution is dropped as a prediction; absolute and cross-sectional axes are built side by side. Decisions
in §9 are Cooper's.
**Companion:** `claude/relative_momentum_findings_log.md` holds every number from the arc so far. Every
figure used here is summarised where it is used.

> **Filing note, added when this document was committed (2026-09-23), not part of the document as
> authored.** Filed at this path as v3 — the first version of this document to reach this checkout;
> v1 and v2 do not exist here, so "supersedes" is asserted by the document, not verifiable from this
> repo's history. The companion `claude/relative_momentum_findings_log.md` also does not exist in this
> checkout. **No code was written and nothing was run against this document** — its own status line
> forbids that, and this filing does not change that status. Two things surfaced while checking it,
> reported here rather than silently:
>
> 1. **A factual correction to prior committed work.** The exit-overlay report
>    (`results/participation_exit_overlay/REPORT.md`, commit `4e806d2`) and its config state "E2's
>    brief, config and code were never committed — only its artifacts." **That is false.** They exist,
>    committed 2026-09-17, on `origin/explore/fundamental-e2` — a branch never merged into this
>    checkout's lineage (this work branched from `explore/fundamental-e1`, before E2 landed there).
>    `prompts/fundamental_exploration_e2.md` and `config/fundamental_exploration_e2.json` are on that
>    branch. This means E2's actual declared `C`, censoring rule and window construction are
>    recoverable, and the participation-overlay report's own rebuilt `C = 10 min` and its account of
>    why E2's window artifact looks the way it does may need revisiting against the real brief. Not
>    acted on here — flagged so it isn't repeated.
> 2. **Appendix A's numbers, checked against the cited artifact
>    (`results/relative_momentum/v2/artifacts/t1b_enriched.parquet`, n=903, branch
>    `explore/relative-momentum-v2`):** the variance decomposition reproduces almost exactly (numerator
>    share 0.155, baseline share 0.845 here vs. 0.155/0.845 cited). The contested-pair win-rate
>    direction and rough magnitude also reproduce (37.25% here vs. 37.6% cited), but the pair count
>    does not: 51 here vs. 101 cited, using "the winner at each live-set-≥2 moment paired against
>    every other live member." The qualitative finding is corroborated; the exact pair count is
>    **unreconciled**, not confirmed.

---

## 0. What this is now, in one paragraph

**The goal is the relationship between attention — however it is best measured — and the stock's
excursion after the decision moment.** It is not an entry/exit mechanism and never was; v0–v2 turned it
into one, and every attention result since then has been tangled with the participation gate's entry and
exit. The excursion is turned into a short vector that is comparable across any two events, without
assuming the path has no drift — the rise-then-fall is expected and the vector is built to describe it.
Attention is measured strictly before the decision moment, in forms that are unitless and scale to each
stock's own activity, so a $0.30 name and a $12 name can sit on the same axis. Fundamentals come in where
they have a mechanism: as the denominator for attention (turnover) and as the only attention source with
its own clock (catalysts — filings, plus news if it passes a timestamp check). Absolute and
cross-sectional attention are built side by side and read jointly, because each only means something
given the other. **If attention and the excursion vector line up, the vector becomes the ruler for both,
and a universe selection tool.**

---

## 1. Why the earlier attention logic failed — kept short, all still true

| # | break | evidence |
|---|---|---|
| 1 | **Measured attention already arrived, not attention still arriving.** Buyers who already bought are in the price and are the future sellers | loudest decile worst on four trade definitions (Phase 11 fixed hold, v0, v1, exit overlay) |
| 2 | **The score measured obscurity.** Relative volume = current dollar volume ÷ the stock's own prior-3-day average | 84.5% of the score's spread came from the baseline; in 38% of contests the winner had less current trading than the loser |
| 3 | **Tape activity is made by the move.** Volume and price change come from the same order flow | score vs move 0.69; 63% of entries scored on a window containing the crossing burst |
| 4 | **"Relative" had no mechanism and rarely ran** | median candidate had no competitor; crowding-out never tested |
| 5 | **Tested only through the gate's entry and exit**, whose exit is itself attention-driven | 903 events, one 8-month slice, read three times |

Everything below is built to avoid all five.

---

## 2. The outcome: the excursion vector

### 2a. What it has to do

- **Make any two paths comparable** — different prices, different trading speeds, different session
  segments.
- **Assume nothing about drift.** The theory says there is a drift up, then a drift down, with blurry
  boundaries. The vector describes that shape; it does not test it against a no-drift world.
- **Avoid boxes.** No minute windows, no fitted change point, no chosen horizon. The path runs from the
  decision moment to the end of the session, however long that is.

### 2b. Two normalisations, neither assumes no drift

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

### 2c. The components

Three markers the path gives for free: **start** (the decision moment `τ`), **peak** (the highest bucket
price — this *is* the MFE), **end** (last print of the session).

| component | definition | captures |
|---|---|---|
| `u_peak` | volume-clock position of the peak, 0 → 1 | how much of the remaining trading the rise took |
| `rise_σ` | log(peak ÷ price at τ) ÷ σ | height of the rise in noise units |
| `fall_σ` | log(peak ÷ last price) ÷ σ | give-back after the peak, in noise units |
| `dip_before_peak_σ` | largest drawdown between τ and the peak ÷ σ | whether the rise was clean or ragged (MAE before the peak) |
| `terminal_σ` | log(last price ÷ price at τ) ÷ σ | where it finished — the quantity D25 found decays |
| `σ_bp` | σ per bucket, in bp | the link from noise units back to money |
| `rise_bp`, `fall_bp` | the same heights in bp and in cents | what the cost stack is compared against |
| `t_peak_s`, `t_end_s` | wall-clock seconds from τ to peak, to end | the wall-clock twin of `u_peak` |

**Edge classes, each its own row, never pooled or dropped:**

- **Rise censored** — the peak is in the last bucket; the rise never turned within the session. Same
  logic as the exit overlay's censored class, which held +1,702 bp at session end.
- **No rise** — the peak is at τ. `rise_σ = 0`, everything is fall.
- **Halt inside the path** — carried with the gap proxy used in the exit overlay (any inter-trade gap
  > 60 s) and exact halt labels where they exist.
- **Thin path** — too few prints after τ to populate the bucket ladder's smallest rung. Threshold
  declared before the run.

### 2d. Reference shapes — eyeball lines, not tests

A path with no drift has known shapes on this scale, and they go on every chart as a line to read
against, never as a null the data must beat:

- **Peak height**: on average about **0.8** of the path's own spread (`√(2/π)` for a random walk).
- **Peak timing**: the **arcsine law** — a no-drift path's maximum piles up near the very start and the
  very end, not the middle. **A `u_peak` histogram with mass at both ends is what noise looks like.** A
  hump in the interior is what a rise-then-fall looks like. This single picture is the most direct test
  of the theory available, and it involves no attention measure at all.

### 2e. Optional, later: let the data name the shapes

Sample every normalised path at fixed points on the volume clock and run functional principal components
(Ramsay & Silverman): the dominant shapes come out of the data and each event gets coordinates on them.
**Used only to check whether the eight-number vector misses something**, never as the primary object —
it is the most elegant option and so the one to be most suspicious of.

---

## 3. The attention side, rebuilt

All measured strictly before τ, asserted in code. All unitless or self-scaled, so they compare across
names without any own-history baseline.

### A1 — Turnover: attention as a share of the supply

> `turnover_τ` = shares traded from session start to τ ÷ shares outstanding as of τ

- **Why:** it measures how much of the available stock has already changed hands — the used-up buyer
  pool from §1, break 1, stated in the right units.
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
     doubling (log ratio 0.69) at two standard errors needs roughly a dozen trades in the finer window.
     The exact count is derived in the brief, not chosen by eye.

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
   §6c are mandatory, not optional.
2. **The same read factor means different scales in different segments** (4.4 s in regular hours vs
   153 s premarket). Scales are anchored to the event's own rate, never to a fixed number of seconds.
3. **Dense and non-isolated at every scale.** There are no burst objects. Acceleration is a continuous
   quantity at each moment, never "a burst started."

**One new confound, specific to this measure:** crossings cluster at the two opens (04:00 and 09:30).
Activity accelerates at the open for every stock, so acceleration measured in the first minutes after an
open is partly the clock, not the name. **Open-adjacent crossings are their own class in every panel**,
with the boundary declared before the run.

### A3 — Catalysts: the only attention source with its own clock

Every tape measure is partly the move, however carefully it is built. A catalyst is not: it arrives at a
timestamp that owes nothing to the tape. For an attention thesis it is also **causal** — it is where the
attention comes from.

**Most catalysts are not filings (Cooper, 2026-09-22).** Small-cap catalysts mostly arrive as press
releases over the newswires; an 8-K may follow later or never. So filings alone have low recall: the
"no filing" group is full of news-driven events, which dilutes any comparison toward zero. Two sources,
used together:

| source | status | what it gives |
|---|---|---|
| **SEC filings** (`flg_`) | held, 98.8% coverage, exact acceptance timestamps | a high-precision, low-recall catalyst flag |
| **News** (Massive's news endpoint, publication timestamps) | **not pulled**; needs a network authorisation like the fundamentals pull (D14 A1) | the recall filings miss |

**Before any news is used, one check decides whether it is usable:** on a random sample of D1 events,
does the news record hold an item published *before* τ, and is the publication timestamp the time the
item first appeared rather than a later backfill? Vendor news history commonly fails the second part
silently. Recall (share of events with any pre-τ item) and timestamp integrity are the headline numbers;
if either fails, news stays out and filings are carried alone, labelled as a lower-recall proxy.

Carried as a **categorical conditioning variable**, never a score term: **catalyst before τ (filing or
news) / none**, with hours from catalyst to τ alongside. The dilution flag is no longer a catalyst class
— see §5.

### Retired, kept, and not built

| item | disposition | reason |
|---|---|---|
| Relative volume (current ÷ prior-3-day baseline) | **reference column only** | measures obscurity (§1, break 2) |
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

## 4. Fundamentals — what we hold and whether each earns a place

### 4a. What Build F1 holds (as-of t0, joined on the SEC company identifier, never on ticker)

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

### 4b. Is there a reason to use them? Yes — three roles, each with a mechanism

The theory has two sides: attention is **demand**, and the rise ends when demand meets **supply**. Every
tape measure is demand-side. Fundamentals are the only data the programme holds on the supply side.

| role | columns | mechanism | use |
|---|---|---|---|
| **Denominator for attention** | `shs_` | turnover needs a share count (A1) | enables A1 |
| **Off-tape attention** | `flg_` catalyst class (plus news, if it passes its check) | exogenous attention arriving on its own clock (A3) | P3 |
| **Bias check on turnover** | `flg_dilution_form_before_t0` | a diluting company's share count is stale and too small, so its turnover reads high | control facet on A1 only — **not a prediction** (Cooper, 2026-09-22: dilution as a driver of the excursion is set aside) |

### 4c. What does not earn a place

| group | disposition | reason |
|---|---|---|
| `spl_` reverse split | **descriptive facet only** | real mechanism (compliance-driven shell cohort) but the sign on a noise-unit vector cannot be derived — it could run either way. No declared direction means no test |
| `si_` short interest | **descriptive facet only** | twice-monthly and published with a lag; it cannot know the state on the event day |
| `fin_` financials | **not used** | no articulated channel into a same-session move; coverage is a calendar artifact, so any split is a year split |
| float tiers 2–3 | **not built** | nothing has earned the weeks of work yet. If A1 matters and the dilution split shows the predicted overstatement, tier 2 becomes the obvious next build |

### 4d. Two governing rules that apply

- **D32 A1** — fundamental columns go against an outcome only as a small, pre-registered partition test
  with declared directions, within year and within detection-price decile, with the price partition run
  first as the competing explanation. §5 declares exactly that.
- **This design supplies what the fundamental research was blocked on.** The September 13 proposal for
  preliminary fundamental research stalled on having no population-scale outcome variable, and proposed
  building excursion measures to be one. The excursion vector is that outcome — built from ticks rather
  than minute bars, so it is not the coarse screening version that proposal settled for.

---

## 5. Pre-registered predictions — confirmed hesitantly (Cooper, 2026-09-22)

Declared before any excursion vector is computed. Three relationships. One is two-sided, and that is
recorded as honestly as the signed ones:

| # | predictor | predicted relationship | mechanism |
|---|---|---|---|
| **P1** | A1 turnover | **two-sided — no direction declared** | two opposite mechanisms, neither derivably stronger: *used-up buyer pool* → lower `rise_σ`, earlier `u_peak`; *thin supply being absorbed* → higher `rise_σ`, later `u_peak` |
| **P2** | A2 acceleration | **higher acceleration → higher `rise_σ`, later `u_peak`** | attention still arriving |
| **P3** | A3 catalyst before τ vs none | **catalyst → higher `rise_σ`, later `u_peak`** | exogenous attention on its own clock |

**What a two-sided P1 costs, stated now.** A test without a declared direction can find a relationship
either way, so it gets a stricter bar: **a monotone P1 curve counts only if the same sign appears in the
development slice and replicates in the selection slice.** A sign seen once is a hypothesis for the next
slice, not a result. If P1 comes back flat, both mechanisms may be present and cancelling — the joint
read in §5a (turnover × acceleration) is where that would show, since the two mechanisms predict
opposite behaviour when attention is still arriving vs when it has stalled.

**Dilution is removed as a prediction** and kept only as the bias-check facet on A1 (§4b).

**Relationships not predicted, and therefore descriptive only:** reverse-split cohort, short interest,
anything against `terminal_σ` (D25 already measured the terminal value decaying unconditionally),
participant breadth such as odd-lot share (the mechanism gives both signs).

### 5a. Absolute and cross-sectional, built side by side

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

### 5b. Universe selection

If the relationships hold, the excursion vector becomes the ruler for a combined score: a partition
defined before τ, on absolute attention × cross-sectional share × catalyst, that shifts the distribution
of `rise_σ` and `u_peak`. That is a universe filter in D32 A1's sense.

**A necessary-condition cost gate, stated now:** an excursion no exit could harvest is worthless, and no
exit captures more than the full rise. So a partition only proceeds toward an exit design if its
**`rise_bp` exceeds the round-trip cost** (70.98 bp flat and 2.512 ¢ per share, both units) on a majority
of its events. Necessary, not sufficient — clearing it earns an exit study, not a strategy.

---

## 6. The design — unchanged in shape

### 6a. Decision instant

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

### 6b. Controls

- **Detection-price partition first**, as the competing explanation for everything. Price drives the
  per-share cost from −1,139 bp to +25 bp across deciles, and cheap stocks file, dilute and reverse-split
  more.
- **Within year**, because density triples from 2021 to 2024 and fundamental coverage is year-shaped.
- **Session segment** (premarket / regular / post) and **open-adjacent class** on every panel.
- **Random-permutation null** on each attention axis, seeded, so every curve has a noise reference.
- **Cross-session magnitude flag (A12)**: the +30% crossing is a cross-session ratio, so flagged events
  are reported as their own row.

### 6c. Instrument checks, on the 56-event dev sample, before anything touches D1

Per the four-control standard:

| control | construction | must show |
|---|---|---|
| **negative** | each event's own bucket returns, demeaned and shuffled | `u_peak` follows the arcsine shape, `rise_σ` near 0.8; `accel_s` ≈ 0 at every scale on a constant-rate Poisson tape |
| **positive** | the same shuffled path with a known rise-then-fall drift injected at a known `u` | the vector recovers the injected peak location and heights; `accel_s` recovers an injected rate ramp |
| **null-parameter sweep** | bucket ladder `{50, 100, 200}`, kernel bandwidths | components stable across rungs; any component that moves with the rung is reported as rung-dependent |
| **blindness** | rescale prices by a constant; change the tick grid | vector invariant |

Only after these pass is the configuration frozen and the full-population run made.

### 6d. Reading rule

- The primary object is the **response curve**: each excursion component across the full range of each
  attention measure, in declared equal-population buckets, distribution and n in every bucket.
- **Evidence is monotone movement in the predicted direction, holding across bucket-ladder rungs, within
  year, within price tier.** A single good cell is declared now as not a result.
- No threshold is set inside the study. Cooper reads the curves.

### 6e. Split

Chronological, ticker-disjoint across boundaries, declared and committed before the first read:

| slice | dates | note |
|---|---|---|
| development | 2020-01-01 → 2022-12-31 | sparser regime; era reported |
| selection | 2023-01-01 → 2024-07-22 | contains the slice already read for relative volume — acceptable for selection only |
| **final** | 2024-07-23 → 2024-12-31 | never read for any attention measure; touched once |

The 56-event dev sample is used for the instrument checks in §6c and is excluded from all three slices.

### 6f. Kill conditions, written before anything runs

1. **Step zero shows no rise-then-fall.** If the unconditional `u_peak` distribution across D1 looks like
   the arcsine shape and `rise_σ` sits at the no-drift reference, the excursion is volatility on
   average. Attention can still split the population, but the theory's premise is not visible in the
   aggregate — recorded as such before P1–P3 are read.
2. **P2 is not monotone in the development slice** at any rung, alone or contested: **tape attention
   closes.** A3 (catalysts) is then the only attention measure left standing.
3. **P1–P3 all fail on both axes:** attention does not organise the excursion. The line closes as
   documentation.
4. **Competition absent and cross-sectional share flat holding the absolute measures fixed (§5a):** the
   cross-sectional axis is removed for good. Either one alone is not enough to remove it — that is the
   contingency.
5. **Relationships hold but no partition passes the cost gate (§5b):** real information, not a universe
   change. Recorded and handed to the exit layer as an input.

**Honest prior:** D25 closed the unconditional long thesis, and the level form of attention has failed
four times. What is different now is the question — the shape of the path rather than a trade's P&L — and
that the measures no longer restate the move. Both are reasons to run it once, cleanly. Neither is a
reason to expect it to work.

---

## 7. Order of work

| step | what | touches outcomes? | cost |
|---|---|---|---|
| 0 | Build τ (exact crossing, exact prior close) on all of D1 | no | one tick pass over event folders (v0 read 1,027 folders in 66 s) |
| 0b | **News check** (§3 A3) — pull for a random sample, measure recall before τ and timestamp integrity | no | needs a network authorisation; can run in parallel with everything else |
| 1 | Build the excursion vector + attention measures (both axes) on the **dev sample**; run §6c's four controls, including the counting-noise stop for A2 | dev sample only | small |
| 2 | Freeze config; build the vector, both attention axes, and the competition check on all of D1, in one pass | builds, does not read outcomes | one pass |
| 3 | **Step zero** — unconditional excursion vector, faceted, against the reference shapes | yes, unconditional only | cheap |
| 4 | P1–P3 on the joint surface, development slice, price partition first | yes | cheap |
| 5 | Selection slice (P1's replication bar applies here), then the final slice once | yes | cheap |

Step 3 can end the line before step 4 is written.

---

## 8. What this does not do

- Does not design an entry, an exit, a hold, or a position size.
- Does not use the participation gate or any of its outputs.
- Does not use `momentum_pct` in any computed quantity; `move_at` is fixed at +30% by construction.
- Does not construct a composite score. Measures are read side by side.
- Does not use the vendor float, financial statements, or any fundamental column outside the declared
  roles (turnover denominator, catalyst flag, dilution as a bias facet on turnover).
- Does not set a threshold on anything.

---

## 9. Decisions for Cooper

**Settled 2026-09-22:** predictions confirmed hesitantly, with turnover two-sided and dilution dropped
(§5); catalysts extended beyond filings (§3 A3); absolute and cross-sectional built side by side (§5a);
A2 ladder anchored from the top (§3 A2).

**Still open:**

1. **Bucket ladder `{50, 100, 200}`** for the path, or a different declared ladder.
2. **The open-adjacent boundary** for A2 — how many minutes after 04:00 and 09:30 count as "the clock,
   not the name."
3. **Liveness ladder `{15 min, 60 min, rest of session}`** for the cross-sectional axis (§5a).
4. **Split boundaries** in §6e.
5. **Session end** = the event day's extended-session close (20:00 ET), or E2's precedent of "end of
   available tick data."
6. **Authorise the news sample pull** (step 0b) under the same kind of scoped network exception the
   fundamentals pull used.

Once these are answered, this becomes a Claude Code brief. Signs and kill conditions carry over
verbatim.

---

## Appendix A — diagnostics behind §1

From `results/relative_momentum/v2/artifacts/t1b_enriched.parquet` (branch
`explore/relative-momentum-v2`), n = 903, no outcome column read. With `s = log10(score)`,
`n = log10(notional_usd)`, `b = log10(B_e)`, so `s ≈ n − b`: numerator share of var(s) =
cov(s, n)/var(s) = 0.155; baseline share = −cov(s, b)/var(s) = 0.845. Contested pairs: live set =
same-date candidates with entry ≤ τ ≤ their window close; the highest-score name paired against each
other member; 101 pairs; winner had lower `notional_usd` in 37.6%. Timing from
`results/participation_exit_overlay/artifacts/t2_overlay.parquet`: 62.8% of τ within 600 s of t0.

## Appendix B — citations

Ané & Geman (2000), *Journal of Finance* 55(5) — volume/transaction clock · Barndorff-Nielsen & Shephard
(2004), *Journal of Financial Econometrics* 2(1) — bipower variation · Clark (1973), *Econometrica* 41(1)
· Filimonov & Sornette (2015), *Quantitative Finance* 15(8) — spurious Hawkes criticality under a
time-varying background · Ramsay & Silverman, *Functional Data Analysis* · Barber & Odean (2008), *Review
of Financial Studies* 21(2) · Da, Engelberg & Gao (2011), *Journal of Finance* 66(5) · Karpoff (1987),
*Journal of Financial and Quantitative Analysis* 22(1) · Hirshleifer, Lim & Teoh (2009), *Journal of
Finance* 64(5).
