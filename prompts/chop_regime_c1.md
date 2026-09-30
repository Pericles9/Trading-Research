# Chop regime filter — C1: the measures and the tuning suite

**Date:** 2026-09-30 · **Type:** build, instrument check, interactive suite. **Not a phase. Fits nothing.**
Cooper sets the filter by eye after the stop.
**Branch:** `explore/chop-regime-c1`, cut from `explore/shape-classifier-s2` at `e71b68a`. It reuses b2's τ
and attention artifacts, S1's types, and S2's τ-anchored fundamentals, causal `tau_close_sensitive` and
remaining-path labels, as they are.
**Outputs:** `results/chop_regime/c1/` (artifacts, charts in per-task subfolders, REPORT.md plus its copy in
`results/reports/`). Suite: `results/chop_regime/c1/suite/chop_suite.html`. Config
`config/chop_regime_c1.json`, committed before any run.
**Precedent:** `prompts/attention_threshold_suite.md` — one offline HTML file, data measured by the pipeline
and embedded, sliders in absolute units, no optimiser, commit before any later read. Same shape and the same
prohibitions here, applied to moments inside the trade instead of events at τ.
**Ends at a stop (T9)** with the suite in Cooper's hands.

---

## 0. Why, in six lines

1. S1 found six hindsight path types. Chop is 59.9% of events, exhausted 17.8%, fade 12.1%. Almost all the
   money is in the other ~10% (burst, slow climb, runaway).
2. S2 found the types only weakly predictable at τ (AUC about 0.55–0.68 on unseen tickers), and watching the
   path after τ did not improve prediction of what is left. Cooper: the classifier is not worth moving
   forward with.
3. The direction now is **a book of long-only strategies, each convex on certain types.** Every one of them
   loses a little on each entry into chop: it pays the spread and rides noise.
4. So the first shared piece is **a regime filter**: at any moment a long strategy might enter, is this stock
   in a state where a trade only pays spread and noise?
5. Cooper sets its thresholds by eye, in absolute units. No percentile sets anything and nothing suggests a
   value.
6. This brief builds the per-moment measures on the 2020–22 slice, checks the instruments, builds the suite,
   and stops. **It sets nothing.**

**What S2 already covered, so this is not a re-run.** S2's after-τ inputs were return so far, the high and
drawdown from it, trade rate and dollar flow (and their ratio to the pre-τ rate), acceleration, realised
volatility and halts. The rate and volatility inputs overlap with part of §4 here. S2 did **not** have the
spread, displayed depth, cost-to-noise, print concentration, efficiency ratio or variance ratio. It also
predicted the path to 20:00, not the next 5–60 minutes. Short-horizon regime is a different question from
the day's type, and spread and volatility persist over minutes far more than types do over hours.

## 1. Terms used below

- **τ** — the first print on the event day at or above 1.30 × the tick-derived prior close (b1/b2), with the
  spike guard.
- **Moment t** — a time at which a long strategy might enter (§3). The filter's answer is per moment.
- **Segment** — premarket 04:00–09:30, regular hours 09:31–16:00, after hours 16:01–20:00 ET. **Auction
  minutes** 09:30:00–09:31:00 and 16:00:00–16:01:00.
- **Collapsed trade** — the D26 rule: prints within 10 ms that are one order reported many times count once.
  Raw print counts are carried alongside.
- **Volume bucket** — an equal-share-volume slice of a window. Each bucket carries **two prices**: the
  quote midpoint at its last print, and its volume-weighted average (VWAP). Raw prints are not used for the
  scale-free measures: bid-ask bounce makes every stock look mean-reverting at fine scales (Roll 1984).
  **VWAP has its own bias, which matters here.** Averaging a random walk inside each bucket gives
  neighbouring bucket returns a positive correlation (about +0.25 for continuous averaging, Working 1960)
  and lowers their measured variance by about a third. On VWAPs, pure noise would read as trending on the
  variance ratio, and own noise would be understated in `cost_noise`. The midpoint has neither problem but is
  stale on this tape (Phase 11: median quote age 1.37 s at a regular-hours trade, far worse premarket).
  **§6 decides which price is primary**, from a control that runs the whole pipeline on noise.
- **Own noise** — how much a window's price would wander with its own returns and no drift or ordering
  (§4c gives the formulas).
- **Round trip at t** — the full quoted spread at t: ask − bid, in bp of the midpoint and in cents (D19). Paid
  once on entry and once on exit, half each time. Phase 11's flat stack (70.98 bp, 2.512 ¢ per share, from
  effective spreads, regular hours) is drawn as a reference line, never used as the per-moment cost.
- **Slices** — development 2020-01-01 → 2022-12-31; selection 2023-01-01 → 2024-07-22; final 2024-07-23 →
  2024-12-31 (D38, `results/attention_excursion/b1/slices.parquet`). The 50 dev and 6 sidecar events are
  quarantined from every slice. **2025 (file2, outside D1) is sealed** (§2, D40).

## 2. Decisions this brief carries

| item | value | source |
|---|---|---|
| Short side | permanently off the table. Long only (D5) | Cooper, 2026-09-30 |
| Thresholds and bin edges | set by Cooper by eye, absolute units. No percentile or rank sets any threshold, edge or default; every default filters nothing | standing, 2026-09-24 |
| **Horizons** | **both ladders, read side by side, no rung privileged:** wall clock {5, 15, 60} min; volume clock {0.25, 0.5, 1} × `V_pre` (shares traded from τ's segment start to τ, S2's anchor, known at τ) | Cooper, 2026-09-30 |
| **Thresholds by segment** | **separate slider values for premarket, regular hours and after hours.** Premarket quoted spreads run about 760 bp median against about 84 bp in regular hours (Phase 11), and bursts are about 3× more common premarket (S1). One pooled cost threshold would mostly switch premarket off | Cooper, 2026-09-30 |
| **Moment grid** | every minute from τ to τ + 60 min, then every 5 minutes to 20:00, weighted so counts are per minute (§3) | Cooper, 2026-09-30 |
| **Where the committed filter is checked** | 2023–24, first-seen tickers as the primary read (§9). **2025 stays sealed for the whole book** | Cooper, 2026-09-30 → D40 |
| A12 (`flag_cross_session_extreme`) | **excluded from this build entirely, including as a facet.** S2's T0 showed it reads the event day's own last trade; it flags 54% of runaways against 1–2.5% of chop, fade and exhausted. A facet on it is a split on the outcome | S2 T0, Amendment 1 A1.6 |

**T0 appends D40 to `docs/Universe-Decisions.md`, verbatim, and updates the `CLAUDE.md` decision index and
next-free pointer (D41) in the same commit:**

> **D40 — 2025 is sealed for the book as a whole.**
> *Date:* 2026-09-30 · *Gate:* chop regime C1, Cooper-approved.
> **Decision.** The 2025 events (file2, outside D1, about 5,200) are read once, for the book of long-only
> strategies as a whole, after every component (regime filters, entries, exits, sizing) is frozen and
> committed. No component is tested on 2025 on its own. Components are checked on 2023–24, with tickers
> absent from 2020–22 as the primary read and all events beside it, clustered by ticker.
> **Why.** Every D1 year has been read (S2's rolling folds tested 2022, 2023 and 2024). 2025 is the only
> untouched data. Spending it on one component leaves the book with no clean test.
> **Scope.** Anything that fits, tunes or selects, including a threshold set by eye.

## 3. Population and moments

**Events:** development slice, τ available, dev and sidecar quarantined. Assert the counts against
`slices.parquet` and b2's τ table. The quarantined 56 are **built** (§6 runs on them) but never embedded.

**Moments per event:**

| moment | definition | weight |
|---|---|---|
| τ | the crossing print. Entry for hindsight columns = the next print after τ (S2's convention) | 1 |
| τ + 1 … τ + 60 min | every minute, wall clock | 1 |
| after τ + 60 min | every 5 minutes, to the last grid time before 20:00 | 5 |

The weight makes every count and share in the suite a count of **moment-minutes**, so the coarser late grid
does not under-count the late day.

**Carried per moment, never dropped:** segment of t (which may differ from τ's); minutes since τ; time of
day; `in_auction_minute`; `no_print_since_last_moment`; `halt_state` (b2's regular-hours ≥ 300 s gap rule,
plus labels where they exist); `quotes_available` (Phase 11's `quotes_ingested`, D15 source).

**Moments in an auction minute** are carried and labelled, measures `unavailable`. They are not entry moments
for a continuous-trading strategy and are not given slider values.

## 4. The measures — all strictly at or before t

**Causality:** every function asserts that no print or quote with `sip_timestamp > t` reaches it. **Segment
rule:** every window lies inside t's own segment and contains no auction minute (b2 R3). A window that cannot
fit is `unavailable` at that scale, never truncated silently.

### 4a. The scale ladder

Anchored at the top, as in b2's A2 and the handoff: **`H_t` = t − start of t's segment** (04:00, 09:31 or
16:01). Rung k covers the trailing window `W_k = H_t / 2^k`, k = 0, 1, 2, … No window length is chosen.

**Counting stop — declared, not derived:** a rung is valid for the scale-free measures (§4c) only if its
window holds **at least 64 collapsed trades** (two per bucket at 32 buckets, so each bucket VWAP averages
over more than one order). Rungs are generated down to the first k where the window's own trade rate predicts
fewer than 64, as b2 R1 did. The count stop for rate measures stays b2's 17 per half-window.

Carry `n_valid_rungs` per moment, and `finest_rung` (the smallest valid window). Rung 0 is the whole segment
so far and is used for context (§4d).

### 4b. Presence and cost — absolute units ("is anyone here", "can it be traded")

| column | definition | units |
|---|---|---|
| `trade_rate_k` | collapsed trades in `W_k` ÷ minutes, per valid rung; raw print rate beside it | trades/min |
| `dollar_flow_k` | Σ price × size in `W_k` ÷ minutes | $/min |
| `spread_bp_t`, `spread_c_t` | ask − bid at t, over the midpoint (bp) and in cents | bp, ¢ |
| `spread_tw_bp`, `spread_tw_c` | time-weighted quoted spread over the finest valid rung | bp, ¢ |
| `quote_age_s` | seconds since the best bid or offer last changed. Phase 11: the book here is **wide and slow** (median age 1.37 s at a regular-hours trade) | s |
| `depth_ask_usd`, `depth_bid_usd` | displayed size × price at the best ask and best bid at t. **A presence check, not a capacity check** (v2 floor brief: in this cap range depth is 0.2–1.1% of mid-cap depth) | $ |
| `cost_noise_h` | round trip at t ÷ own noise over horizon h (below), one column per horizon, 6 in all | unitless |

**Own noise over a horizon.** From the finest valid rung's 32 bucket log returns (on the primary bucket
price, §6):
- wall clock: `σ_h = sqrt( Σ r² ÷ window minutes × h )`;
- volume clock: `σ_h = sqrt( Σ r² ÷ window shares × m · V_pre )`.

`cost_noise_h` = `spread_bp_t` ÷ `σ_h` in bp. It reads directly: **at 1, one round trip costs one typical
move over the hold.** Chop is where that ratio is large. The cents version is the same number, so one column
serves both units; the spread itself is shown in both.

**Depth needs one check first (T0).** The quote table's `bid_size` and `ask_size` must be confirmed as
shares, not round lots, in every year 2020–22, from the data (for example, sizes against the trade sizes that
print at the touch). If the unit cannot be established per year, depth is **not built** (escalation row 4)
and the suite runs without it.

### 4c. Relative and scale-free — "is this a crowd or one order", "is it trending or chopping"

| column | definition | catches |
|---|---|---|
| `turnover_t` | shares traded 04:00 → t ÷ shares outstanding as of t (S2's τ-anchored F1 build, `shs_asof_ns < t` asserted). **Lower bound** — shares outstanding, not float. Dilution flag and `shs_quality` carried | edge case 2 |
| `turnover_rate_k` | shares in `W_k` ÷ shares outstanding ÷ minutes | edge case 2 |
| `n_eff_k` | **effective number of independent orders** in `W_k`: 1 ÷ Σ sᵢ², where sᵢ is each collapsed order's share of the window's volume. Plain units: orders | edge case 1 |
| `top3_share_k` | share of window volume in the 3 largest collapsed orders | edge case 1 |
| `move_per_trade_k` | abs(log price change over `W_k`) ÷ collapsed trades, bp per trade | edge case 1 |
| `er_k`, `er_rel_k` | **efficiency ratio** (Kaufman): abs(net log move) ÷ Σ abs(bucket log returns), over the window's 32 buckets. `er_rel` = `er` ÷ its own-noise value, below | chop vs trend |
| `vr2_k`, `vr4_k`, `vz2_k`, `vz4_k` | **variance ratio** (Lo & MacKinlay 1988) at q = 2 and 4 over the 32 bucket returns, and its heteroskedasticity-robust z-score. Below 1 (z < 0) is mean-reverting, above 1 (z > 0) trending | chop vs trend |

**Noise references, per moment, from the window's own returns — not Gaussian textbook values.** The
programme learned twice (b1 Amendment 2, S1) that Gaussian references mislead on fat-tailed, tick-discrete
tapes.

- **Efficiency ratio.** Resampling a window's own demeaned returns with replacement (S1's null) gives, to
  first order, `er_0 = sqrt(2 ÷ (π n)) × s ÷ mean|r − r̄|`, with n = 32, s the returns' standard deviation.
  For Gaussian returns this is the familiar 1/√n; for fat tails it is higher, because one big step dominates
  both the net move and the path length. **`er_rel = 1` is noise**, above 1 is trend, below 1 is chop.
- **Variance ratio.** Its robust z-score is already in noise units: **0 is noise, ±1.64 the 90% band.**

Both references are closed-form approximations with n = 32, and both assume the bucket returns carry no
correlation the pipeline itself created. **§6 checks both assumptions**: against 200 resampled draws per
window, and against paths rebuilt from shuffled print-level returns, which puts the bucket averaging back in.
A failure stops the build (row 3).

**One property to know in advance, stated plainly.** Activity-level measures (`trade_rate`, `dollar_flow`,
`turnover_rate`) **are the session envelope** (D26: above 10 ms the arrival record holds the envelope and
nothing else). That is intended here: the envelope is exactly "is anyone here". The scale-free measures are
built on the volume clock, which absorbs the rate, so they are not envelope readers. The v15 standard asks
that this be said, not discovered.

### 4d. Context — the slower scale, for edge case 3 (pauses between legs)

From the rung-0 window (segment start → t), bucketed to 32:

| column | definition |
|---|---|
| `leg_s` | the largest rise from a bucket low to a later bucket high, over own noise across the buckets it spans (the `rise_s` construction) |
| `leg_bp`, `leg_c` | the same rise in money |
| `giveback` | log(leg high ÷ price at t) ÷ log(leg high ÷ leg low). 0 = at the high, 1 = all given back, above 1 = below the leg's low |
| `since_high_min`, `since_high_vol` | minutes since the leg's high; share of rung-0 volume traded since it |
| `act_ratio` | collapsed trade rate over the finest valid rung ÷ rate over rung 0. Above 1: busier now than the segment so far |

A shallow pullback after a real leg on still-elevated activity is what a pause looks like. The suite lets
Cooper say what "real", "shallow" and "elevated" mean (§7b).

## 5. Hindsight columns — for eyeballing only, never a slider

Hindsight is allowed here as it was in S1: it is what Cooper judges the filter against. **Nothing in this
section can be selected as a filter condition**, and the build asserts that no hindsight column is wired to
a slider.

Per moment and horizon h (all 6), entry = the next print after t, prices spike-guarded:

- `fwd_ret_h` — last print at or before t + h against entry; `fwd_mfe_h` — highest print in (t, t + h];
  `fwd_mae_h` — lowest. Each in bp and cents, gross, and net of the round trip at t.
- `h_censored` — the horizon ran past 20:00 or the segment end; the forward window is cut there and flagged.
- `no_print_in_h` — no print in the horizon. **This bears on the open item from S2**: burst top-decile picks
  with a median of exactly −71 bp, meaning zero gross move over 30 minutes. That is what a stale or dead
  moment looks like, and here it is a visible class instead of a hidden median.
- **`chop_h`** — the hindsight chop label: `fwd_mfe_h` < c × round trip at t. **c is a viewing slider,
  default 1**, because what counts as "cost-relevant" is Cooper's call.
- **`rem_type`** — S2's remaining-path type (S1 rules applied to the path from the moment to 20:00), read
  from S2's artifacts at the moments where it exists: τ, +1, +2, +5, +10, +20 min. Nothing new is computed.

### Gallery finders — declared rules, labelled "gallery finder, not a filter"

Found automatically, so Cooper sees what the filter does to each edge case. The numbers are in config,
declared, with no derivation claimed. They only choose which tapes to show.

| gallery | rule at t | hindsight? |
|---|---|---|
| **G1 low-volume pop** | at the finest valid rung, `n_eff` ≤ 5 **and** `top3_share` ≥ 0.6 | no |
| **G2 higher-float noise** | `turnover_t` < 1% **and** `dollar_flow` ≥ $20,000/min at the finest valid rung **and** abs(`er_rel` − 1) ≤ 0.25 **and** abs(`vz2`) < 1.64 at every valid rung 1–4 | no |
| **G3 pause between legs** | `leg_s` ≥ 2 **and** 0.1 ≤ `giveback` ≤ 0.6, **and in hindsight** the price in (t, t + 60 min] exceeds the leg high by at least one round trip at t **and** by at least 1 own-noise unit over that forward span | yes |

Carry `g1`, `g2`, `g3` flags on every moment. G3 is the false positive that matters, so its count is pinned
(§7c, panel A).

## 6. Instrument checks — the four controls, on the 56 quarantined events

Runs on the dev and sidecar events only, **before** the full build. Pass bands are declared here. **Any
failure is a HARD STOP.**

| control | construction | pass |
|---|---|---|
| **Negative — the references** | per window, 200 seeded resamples (with replacement) of its own demeaned bucket returns | median over windows of (mean resampled `er` ÷ closed-form `er_0`) within **0.90–1.10** at every rung; resampled `vz2`, `vz4`: abs(median) < **0.15**, standard deviation within **0.80–1.25** |
| **Negative — the whole pipeline** | per event, the window's **print-level** returns shuffled and re-integrated with the prints' own times and sizes kept, then bucketed exactly as real data. Same for midpoint changes at quote-update level | the same bands as above, **run separately for the midpoint and the VWAP price.** This is the control that sees the averaging bias |
| **Positive — trend** | resampled paths with an injected net drift of d ∈ {1, 2, 4} own-noise units across the window | median `er_rel` rises with d, and exceeds **2.0** at d = 4 |
| **Positive — autocorrelation** | resampled returns passed through AR(1) with φ = +0.5 and −0.5 (at n = 32 the robust z for φ = 0.3 sits right at 1.64, too close to the band to be a fair test) | median `vz2` ≥ **+1.64** at +0.5 and ≤ **−1.64** at −0.5 |
| **Edge of detectability** | φ = ±0.25 and d = 1 | reported only, no band. It shows what the instruments can and cannot see at n = 32 |

**Which bucket price is primary, decided by the whole-pipeline control, not by preference:**

| midpoint | VWAP | primary |
|---|---|---|
| passes | passes | midpoint (no averaging); VWAP carried as the check |
| passes | fails | midpoint; VWAP dropped from the suite, its failure reported |
| fails | passes | VWAP; midpoint dropped, its failure reported |
| fails | fails | **HARD STOP** (row 3) |

Moments without quotes use VWAP whatever the ruling, flagged `price_basis = vwap_fallback`.
| **Null-parameter sweep** | buckets per window {16, 32, 64} | medians of `er_rel`, `vz2`, `cost_noise_h` per setting; any that move more than 20% are labelled **bucket-dependent** in the suite |
| **Blindness** | prices × 10 and × 0.1; separately, sub-$1 prices rounded to the $0.01 grid | scale-free and bp measures identical to 1e-9 under rescaling; the rounding change is reported per event |
| **Price-basis agreement** | `vz2` and `er_rel` on the midpoint against the VWAP, real data | Spearman per rung and segment reported; disagreement reported, not resolved |
| **Causality** | a test feeds a print and a quote after t into every measure function | must raise |
| **Segment** | a test feeds a window that crosses a segment boundary or contains an auction minute | must raise |

## 7. The suite

### 7a. What it is

One self-contained HTML file. Plotly inlined (D14), dark theme. The per-moment table is embedded as typed
arrays at build time; filtering happens in the browser and every panel redraws on each slider move. **No
measurement is recomputed in the browser.** It filters a table the pipeline measured.

**Size.** About 7,500 events × about 170 moments is roughly 1.3M moments. Budget **≤ 100 MB** for the file.
If the full development slice does not fit, embed the largest **seeded event sample, stratified by year ×
τ's segment**, that does, and state the fraction in the always-visible header. Whole events only, never
thinned moments, so each event's in-trade sequence stays intact.

**Header, always visible:** *"Development slice only (2020–22). Thresholds in absolute units, per segment.
Hindsight columns are for judgement, never conditions. Commit before any 2023–24 read. 2025 is sealed. The
galleries are the evidence; the curves summarise them."*

### 7b. Controls — the filter's logic

**Per segment.** Premarket, regular hours and after hours each have their own slider values, with a
"copy to the other segments" button. A moment uses the values for **its own** segment, not τ's.

**Chop conditions.** Each is off by default. When switched on, its slider starts at the value that filters
nothing (the measure's minimum or maximum in the embedded data), so nothing is rejected until Cooper moves
it. Direction is fixed by meaning:

| group | conditions (filter the moment if …) |
|---|---|
| presence and cost | `trade_rate` < x · `dollar_flow` < x · `spread_bp_t` > x · `spread_c_t` > x · `quote_age_s` > x · `depth_ask_usd` < x · `cost_noise_h` > x (Cooper picks h) |
| relative | `turnover_rate` < x · `n_eff` < x · `top3_share` > x · `move_per_trade` > x |
| scale-free | `er_rel` < x · `vz2` < x · `vz4` < x — each at a chosen rung, **or "at every valid rung"** (the handoff's "two or more scales") |

**Combination:** filter if **any** active condition fires, or if **at least m** of them fire (m selectable).

**Pause override.** A filtered moment is **kept** if every active override condition holds: `leg_s` ≥ x,
`giveback` ≤ x, `act_ratio` ≥ x (each on/off). **The override can rescue a moment only from the relative and
scale-free conditions, never from presence and cost.** A pause in a name with a 700 bp spread is still
untradeable.

**Unavailable values.** Per condition, Cooper chooses whether `unavailable` (no valid rung, no quote) counts
as filtered or passes. Default: filtered for presence and cost, passes for scale-free. The count affected is
shown beside the toggle.

**Viewing controls (do not change the filter):** horizon (one of the 6), chop-label multiple c, cost unit
(bp / cents), gross / net, facet filter (year, segment, price tier at τ: < $1 · $1–3 · $3–10 · ≥ $10,
`tau_close_sensitive` three-state, dilution flag, quotes available).

### 7c. Panels

**A — Pinned, always visible.**
- Moment-minutes kept and filtered, overall and by segment, year and price tier; events with at least one
  kept moment.
- **Pauses filtered: x of y (G3)**, by segment. The largest number on the page.
- Low-volume pops kept: x of y (G1). Higher-float noise kept: x of y (G2).
- **A readability line at 20** on every count. A cell under 20 cannot be missed.

**B — Each active measure against its threshold.** Full distribution per segment, log axis where the
measure is a positive quantity, the threshold drawn, the rejected side shaded. **Reference lines drawn:**
`er_rel` = 1, `vz` = 0 and ±1.64, `cost_noise_h` = 1, the flat Phase 11 stack on the spread panels.

**C — What the filter does to outcomes.** Kept vs filtered ECDFs of `fwd_ret_h` and `fwd_mfe_h` at the
chosen horizon, the chosen unit, gross or net, n on every curve, both round-trip lines drawn. Two uncertainty
readings, each computed **on a button press** (they take seconds):
- **Noise band:** 100 seeded random filters that keep the same share of moments inside each segment ×
  minutes-since-τ octave cell. The 5–95% band of their kept-minus-filtered median difference is drawn. A
  difference inside the band is what a random filter with the same timing produces.
- **Ticker bootstrap:** 95% interval on the kept-minus-filtered median difference, resampling tickers.

**D — The hindsight chop label.** Share of `chop_h` among kept and filtered moments at every horizon (6
bars each, both ladders side by side), with n. Beside it, **`rem_type` mix, kept vs filtered**, at τ, +1,
+2, +5, +10 and +20 min, all six types shown, n per cell.

**E — Where the filter bites in time.** Kept share against minutes since τ (log axis) and against time of
day, one line per segment. It shows whether a setting is really a regime filter or just switches off
premarket or the late day.

**F — Which conditions fire together.** Counts of moments filtered by each active condition alone and by
each combination (an intersection chart). It shows redundancy, for example spread and trade rate firing on
the same moments.

**G — Galleries. This is where the judgement is built.** Tabs: G1, G2, G3, **near the line** (the k moments
just inside and just outside the most recently moved threshold, k default 12), and a seeded random draw of
kept and of filtered moments. Pools are fixed at build time (up to 150 moments per finder, seeded); each
strip's kept or filtered state is live.

Each strip: **trade prints as dots** (standing rule), best bid and best ask as lines, collapsed-order volume
as bars, from the start of t's segment (or t − 60 min if later) to t + 60 min. **The moment t is a vertical
line and everything after it is shaded "hindsight".** The leg low and high are marked. A badge says kept or
filtered, which condition fired, and whether the override rescued it. The caption carries ticker, date,
segment, minutes since τ, and the moment's measures. Clicking pins a strip.

### 7d. What the suite must not do

- **No optimiser. No "suggested", "best" or ranked setting.** Nothing computes where a threshold should go.
- No percentile-defined edge, bin or default. Axis ranges run from the embedded minimum to maximum.
- No 2023–24 or 2025 row, in any form. The build asserts every embedded row is in the development slice.
- No A12, in any form (§2).
- No hindsight column as a condition (§5).
- No aggregate without its distribution and n.
- No recomputation of measurements in the browser.

### 7e. Export

A button writes the filter config as JSON: per segment, the active conditions, their thresholds and units,
the rung choice for each scale-free condition, the combination rule, the override settings, the
`unavailable` choices, the `cost_noise` horizon, the embedded data's hash and sample fraction, and a
timestamp. The viewing controls in use are recorded too (horizon, c, unit), since they were part of what
Cooper looked at.

## 8. Report

REPORT.md describes, interprets nothing, reads every number from artifacts by code. It opens with the
escalation table and the D40 commit, then:

- coverage: events, moments, weights; moments per segment; `unavailable` share per measure and rung; the
  quote-size unit finding (T0); quotes-unavailable events;
- the §6 control table, pass or fail per row, with its charts, and the primary-price ruling;
- the distribution of every measure per segment (no outcome column);
- the embedded sample fraction and file size;
- **the column dictionary**, generated from the artifacts: name, type, units, causal or hindsight, which
  panel uses it.

**No outcome is summarised in REPORT.md.** The outcome panels exist for Cooper in the suite.

## 9. Commit, then check — what happens after Cooper sets the filter

Setting a threshold while looking at outcome panels is a choice made with the data in view. That is
legitimate here, and it changes what comes after. Under D38 it is selecting, so the ticker-blocked test
applies from this point.

1. **Export and commit** the config before anything else runs. The commit hash is its timestamp.
2. **A separate brief (C2)**, not this suite, applies the committed filter with the pipeline:
   - first to **every** development-slice event, not only the embedded sample, as a check that the sample
     represented the slice;
   - then to **2023–24**, reported on the same panels. **The primary read is tickers absent from 2020–22**
     (about a third of the 2023 → mid-2024 events, and about 17% of the late-2024 ones). All events are
     reported beside it, with ticker-clustered intervals. For scale (b1): 33% of the 2023 → mid-2024 events are
     tickers absent from 2020–22. For late 2024 the share is at least the 17% that were new against all
     earlier slices; C2 counts it exactly.
3. **Moving any threshold after that read makes a new filter.** It is committed as such, and 2023–24 counts
   as spent for it.
4. **2025 is not touched (D40).** It is read once, for the frozen book.

**Two properties worth knowing in advance.** The development slice is the sparser market (median 6–9
crossings a day against 18 in 2024), so a filter set there is tested in a busier one; a filter that only
works in one regime will show it at step 2. And a filter judged at one horizon can be wrong at another; the
committed config records which horizon Cooper was viewing, and C2 reports all six.

## 10. Tasks

- **T0 — Freeze and population.**
  - Config committed. D40 appended and the decision index updated (§2), same commit.
  - Assert the development-slice event count against `slices.parquet`, τ availability against b2, and the
    quarantine.
  - `tau_ns` is int64 in every artifact. The handoff records that stored τ in b1/b2/S1 was rounded to
    multiples of 256 ns by a float64 step. Take τ from whichever committed source S2 used for its entries,
    state which, and assert int64 on read.
  - **Quote-size unit census** (§4b), per year, from the data. Post the finding.
  - **Timing:** run T1–T4 on the 56 quarantined events, report wall time, and extrapolate to the development
    slice using per-event print counts. Runtime ceiling 6 hours (row 10).
- **T1 — Moment grid** (§3), with weights, flags and segment labels.
- **T2 — Presence and cost measures** (§4b), including the six `cost_noise_h` columns.
- **T3 — Relative measures** (§4c, first five rows).
- **T4 — Scale-free and context measures** (§4c rest, §4d), with the closed-form references.
- **T5 — The four controls** (§6), on the 56 quarantined events, and the primary bucket price ruled from
  the whole-pipeline control's table. **A failure is a HARD STOP.** On a pass, commit the ruling and
  continue.
- **T6 — Full build**, T1–T4 on the development slice, plus the §5 hindsight columns and the `rem_type` join
  from S2.
- **T7 — Gallery pools and flags** (§5), with per-strip print data (downsample to at most 2,000 prints per
  strip, keeping the extremes).
- **T8 — The suite** (§7), with its build-time assertions (§12).
- **T9 — REPORT.md** (§8), charts, commit, push. **Post:** the escalation table, the control table,
  coverage per segment, the quote-size finding, the embedded sample fraction. **Then stop.**

## 11. Escalation

| row | criterion | tier |
|---|---|---|
| 1 | any causality assertion fires | HARD STOP |
| 2 | any segment assertion fires | HARD STOP |
| 3 | any §6 control misses its pass band | HARD STOP |
| 4 | quote-size units cannot be established for a year | LOG. Depth not built for that year; its conditions show `unavailable` |
| 5 | embedded sample below 50% of development-slice events | LOG. Header states the fraction |
| 6 | moments with no valid scale-free rung above 40% of moment-minutes in any segment | LOG. It says how thin these tapes are at this counting stop |
| 7 | events with quotes unavailable | LOG with count, carried as their own facet value |
| 8 | A12, or any hindsight column, reaches the suite's condition inputs | HARD STOP (build assertion) |
| 9 | any embedded row outside the development slice | HARD STOP (build assertion) |
| 10 | extrapolated runtime above 6 hours | HARD STOP. Post; do not shrink the grid, the ladder or the population silently |

## 12. Verification — executable, not prose

- Development-slice event count and quarantine asserted; moment counts per event reconcile to the grid rule;
  weights sum to the minutes covered.
- `tau_ns` int64 on read and in every artifact.
- Causality and segment assertions wired into every measure function and exercised by tests that require
  the raise.
- Bucket volume conservation in every window.
- Blindness invariance to 1e-9.
- The suite build asserts: every row development slice; no A12 column; no hindsight column in the
  condition set; no column that is a percentile or rank; row count equals the embedded sample.
- Every number in REPORT.md is read from an artifact by code.

## 13. Constraints

D4 tick-derived (trades and quotes) · D5 long-only, D25 stands · D14 offline, Plotly inlined, no installs ·
D19 bp and cents for every cost and spread · flag and carry; `unavailable`, zero and censored kept distinct ·
named paths staged, commit at each task boundary · dark theme · charts in per-task subfolders · nothing in
`scanner-epg-momentum` or `hawkes-ofi-impact` is touched.

**Not in this brief:** any strategy, entry or exit; any threshold; any read of 2023–24 or 2025; the A12
replacement (a corporate-action flag from the split records is a separate item); news.

## Appendix — citations

Kaufman, *Smarter Trading* (1995) — efficiency ratio · Lo & MacKinlay (1988), *Review of Financial Studies*
1(1) — variance ratio and its heteroskedasticity-robust statistic · Roll (1984), *Journal of Finance* 39(4)
— bid-ask bounce as negative autocorrelation · Working (1960), *Econometrica* 28(4) — averaging a random
walk induces positive correlation in the averaged series · Andersen, Bollerslev, Diebold & Labys (2000) — the
volatility signature plot, the same idea as reading the variance ratio across scales · Clark (1973),
Ané & Geman (2000) — the volume clock.
