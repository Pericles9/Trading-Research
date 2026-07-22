---
tags:
  - type/strategy-proposal
  - domain/research
  - project/scanner-epg-momentum
  - status/draft
created: 2026-07-08
revised: 2026-07-08 (v2 — climb thesis promoted to spine; rank-1 finding reclassified; catalyst axis added)
scope: Strategic synthesis — the climb thesis, event-time drift structure, quote-side change detection (MRD), scanner heat rebuild, data budget expansion
status: DRAFT v2 — awaiting Cooper review. All free parameters marked [COOPER DECIDES]. No implementation before explicit approval.
---

# Climb Thesis / EVQ / MRD — Strategy Synthesis v2

**The thesis (day-1, now explicit):** Capitalize on active stocks moving up the scanner list that climb into 1st or 2nd place. This is the axis of the research program. EPG, Hawkes, WJI, and MRD were all instruments pointed at the same underlying quantity — participation arriving in a name — measured indirectly from one name's tape. Rank velocity measures it directly and cross-sectionally: participation arriving in this name *relative to its competitors for attention*. The thesis has been untestable to date for one reason only: **rank trajectories were never recorded.** Lack of data, not lack of priority.

**Why this is better-posed than everything prior:** the climb is a *policy on an observable state*, not a detection problem. Rank is measured, not inferred — no CUSUM machinery is needed to know a name went 40→12. The research question is continuation, not detection: given a partial active climb with these properties, what is E[PnL | enter now]? This dodges the detection-delay wall (§3) entirely, because the wall existed only for quantities that must be inferred from noisy paths.

**Bottom line of v2:** the noise findings closed exit-timing research; the edge budget is set at entry by selection. The climb thesis *is* the selection hypothesis. EVQ becomes "which climbs to continue-bet." The heat axes are the climb's context variables. MRD is demoted to a candidate exit input. The scanner trajectory dataset is the research dataset, making live archival and historical scanner replay the critical path of the entire project.

Standing constraints throughout: no trade signing anywhere, no rolling windows, banned excursion metrics stay banned, the trail stays frozen, halted time never advances clocks.

---

## 1. Strategic frame

From the noise findings (excursion doc, 2026-07-07):

- Harvestable edge ≈ **+0.9% gross per event**, fixed at entry by event selection
- Exits reshape, they do not earn (F4) — established over 488 causal exit configs
- MFE-family metrics are volatility gauges; all threshold-touch statistics banned
- Drift is heterogeneous across events — the only demonstrated axis of exploitable structure

v2 extends this with the thesis above, one correction, and one new channel:

1. **Correction:** F4's optional-stopping argument binds only on a true martingale. The per-bar return distribution is non-stationary (positive early → negative middle → centered late), opening two narrow exceptions to "exits cannot earn" (§2).
2. **New channel:** all prior conditioning attempts were trade- or price-derived. The quote channel is untested and is the only remaining channel satisfying the no-signing constraint (§3).

### 1.1 The rank-1 finding, reclassified

Prior documentation recorded: rank-1 scanner entries systematically underperform. **v2 reclassifies this finding from "structural" to "uninformative pending re-cut."** The recorded statistic was computed on context-free snapshots that pooled incommensurable situations — at minimum: (a) the 37%-up-on-no-news leader of a thin pre-market list (dilution/pump archetype), (b) the catalyst-driven leader of a broad hot tape, (c) the active climber that just arrived at #1, (d) the stale sitter parked there since early pre-market. Averaging these is an aggregation artifact (Simpson-class), the same failure family as the gap-at-hit/mom_pct stratification bug and the heat quartiles.

**Epistemic status, stated precisely:** the composition argument establishes that the old statistic is *uninformative*. It does **not** establish that strong rank-1 entries were good — that is a hypothesis. The supporting recollection ("the vast majority of those entries were before rank 1 meant anything") derives from manual-trading memory, the most confirmation-prone source available, and must be verified against entry records, not trusted.

**DIAG-RANK1 (required, cheap, runs early):** pull the historical rank-1 entries; attach reconstructible context (breadth from the event table, news/filing-at-hit from Polygon historical news + EDGAR timestamps, session, climb history where data permits); cut the underperformance by context.

- Composition story **predicts**: underperformance concentrates in thin-breadth × no-catalyst cells and vanishes or inverts in broad-tape × catalyst × active-climb cells.
- If underperformance is instead flat across contexts, the composition story fails, the original finding stands, and the climb thesis takes a direct hit at its most important cell (arrival at #1).

Either outcome is informative. This diagnostic is the cheapest test of the thesis's most exposed prediction.

### 1.2 Commitment-bias register

A thesis held since day 1 carries the highest confirmation-bias risk in the project. Manual-trading observations are genuine evidence, but sampled through a live attention filter that oversamples memorable climbs. Protection = the same discipline the noise doc imposed on excursions: every thesis claim below is pre-registered with a null, and the kill criteria are written before any sweep (§5.4, §7).

---

## 2. The non-stationarity decomposition

The observed drift shape (positive early → negative middle → centered late) admits two structurally different explanations requiring different tools.

### Case A — Deterministic event-time profile μ(t)

Drift as a common function of event time. If true: no detection needed — μ(t) is estimated cross-sectionally, power scaling with event count, not path length. **F4 does not apply**: optional stopping forbids path-dependent exits on a martingale; a deterministic-time exit on a process with sign-changing μ(t) legitimately earns ∫₀^t* μ dt > +0.91% if the middle of the curve is genuinely negative. Existing bound: SEB-X timer sweep best EV +1.03% vs +0.91% hold — either the sign-crossing structure is worth ≤ ~0.1%, or the timer grid was too coarse.

**ANALYSIS-μT (decisive, one pass, runs first):** mean **and** median cumulative-return curves vs event time, stratified by session and price bucket (median required — bimodal PnL means the mean curve can be tail-dominated). Read the zero-crossing.

**v2 addition — second alignment:** the curve anchored to scanner hit mixes climbs, arrivals, and stale sitters. That superposition could *itself* produce the observed positive→negative→flat shape (early climbers' gains + post-arrival fades). Re-anchor a second set of curves to **climb-relative time** (t=0 at climb onset, and separately at top-2 arrival), data permitting. This makes the composition question directly visible and quantifies the entry-confirmation tax for any delayed-entry rule.

- Hit-anchored curve monotone-ish AND climb-anchored curves flat → F4 stands, shape was artifact, Case A closed.
- Pronounced hump, especially in climb-relative time → schedule structure is real; window length and entry timing belong at the curve's features. That is EV, not shape.

Not a banned metric: realized PnL of a deterministic exit as a function of time.

### Case B — Stochastic per-path regimes

Per-path changepoint times → online CPD problem. Detection-delay theory: CUSUM average delay ≈ h/KL, h ≈ ln(ARL₀) ≈ 6 for one false alarm per ~400 observations.

Gaussian mean shift δ at σ = 2%/bar (KL = δ²/2σ²):

| Drift shift δ | Over 30 bars | KL/bar | Detection delay |
|---|---|---|---|
| 0.1%/bar | +3% | 0.00125 | ~4,800 bars |
| 0.2%/bar | +6% | 0.005 | ~1,200 bars |
| 0.73%/bar | +22% | 0.067 | ~90 bars |

Variance shift σ→2σ: KL ≈ 0.32/bar → delay ≈ 19 bars.

**Conclusion:** drift changepoints on price are undetectable within the event horizon by an order of magnitude, and CUSUM is minimax-optimal (Moustakides 1986), so this is the floor for any method. Vol/intensity changepoints are 60–250× more detectable per observation. Price-mean CPD is closed. Case B is pursued only through the quote channel (§3) — and note the thesis-level point: the climb itself is *observed*, not detected, which is why the climb thesis is exempt from this entire section.

---

## 3. MRD — Mid-Revision Direction detector (exit candidate)

**v2 status:** demoted from co-headline to candidate exit input for the climb strategy. Rationale: the thesis supplies entry; F4's empirical basis (488 configs) was entirely price/trade-derived, so a quote-side regime-death exit is the first exit input not downstream of an already-falsified channel; and if Case B regimes exist, a path-dependent exit on a genuinely regime-switching process can earn.

### 3.1 Design requirements for a CPD-native signal

1. High KL per observation
2. High observation rate (delay is counted in observations)
3. Known or stable H₀ — pinned analytically or by symmetry, never estimated from the watched stream (the adaptive-reference trap that broke every peak/EMA threshold)
4. Bounded noise
5. Directional without trade signing

Price fails 1 and 4. Trade-derived features fail 5. L1 quote-size imbalance fails 3 and 4 in this universe (lumpy, spoofable, heavy-tailed) — upgrade path only.

### 3.2 The signal

Discard magnitude, keep sign. Each NBBO midpoint revision is one observation: x = +1 (up) or −1 (down). **H₀: p(up) = 0.5 by symmetry, not estimation** — zero per-event parameters, no warmup, no Hawkes fit. Noise bounded at ±1 by construction; the sign channel escapes the vol wall because its noise floor is independent of price volatility. Drift must transmit through the quote process as revision-direction asymmetry.

### 3.3 The detector

One-sided CUSUM on the Bernoulli log-likelihood ratio vs design alternative p₁:

```
on up-revision:    S ← max(0, S + ln(2·p₁))
on down-revision:  S ← max(0, S + ln(2·(1−p₁)))
PASS when S > h
```

Mirrored down-detector runs simultaneously. **Bank of 2–3 parallel CUSUMs** at p₁ ∈ {0.55, 0.60, 0.65}, fire on any: mismatch cost is asymmetric (a p₁=0.60 design detects stronger regimes faster, suffers only on weaker), so the bank buys near-GLR robustness for six floats of state. [COOPER DECIDES: bank membership; any-fire vs per-detector action.]

Delay budget (h ≈ 6):

| Regime p(up) | KL/rev | Delay (obs) | @ 2 rev/s | @ 5 rev/s |
|---|---|---|---|---|
| 0.55 | 0.0050 | ~1,200 | ~10 min | ~4 min |
| 0.60 | 0.0201 | ~300 | ~2.5 min | ~1 min |
| 0.65 | 0.0457 | ~130 | ~65 s | ~26 s |

Structural property: **observation rate scales with the action** — revision rates explode when a regime starts, so the detector accelerates exactly when it matters. Price bars cannot do this. No warmup is a second structural advantage: H₀ holds from the first post-hit revision, no ~300s dead time in a front-loaded-drift universe.

### 3.4 Method selection (clean-slate)

| Method | Verdict |
|---|---|
| CUSUM (bank) | **Selected.** Minimax-optimal for this family; 2 ops/revision; state plottable on 4-panel charts |
| Shiryaev–Roberts | Near-identical in practice; no advantage |
| GLR | Solves unknown-p₁ at O(window) + hidden bandwidth; the bank achieves it cheaper |
| BOCPD (Beta-Bernoulli) | Closed-form on binary data; run-length posterior = graded regime-age signal. **Upgrade path** if regime age becomes an input |
| HMM filter | Heaviest estimation burden; wins only on recurring-regime structure not demonstrated |
| Sliding-window tests | Strictly dominated frontier; arbitrary bandwidth |
| Offline (PELT etc.) | Not for live — detection, not localization. Retained as ground-truth labeler offline |

**Calibration note:** optimality theory assumes iid; quote streams are not (flicker → negative autocorrelation, harmless; fade cascades → positive, harmful). **h is calibrated from empirically measured ARL₀ on real rest-state revision streams**, never from theoretical formulas. Applies to every method equally.

### 3.5 Known risks

- **Magnitude blindness / bimodality.** Winners are a +38% tail mode; if drift lives in rare large revisions, a sign test is structurally blind (F6's failure mode, mirrored). Checkable offline before any build: p(up) trajectories, winners vs losers.
- **Autocorrelation** must be measured; may need a one-tick/minimum-dwell revision filter.
- **Quote quality per bucket.** Bid-side quotes evaporate in thin names pre-halt; locked/crossed markets; sub-penny flicker in <$2 names. Rest-state symmetry verified **per price bucket**; if thin names rest at p=0.53 structurally, the no-estimation advantage is gone there.
- **Halts:** revision stream stops, S holds, no clock advancement.

### 3.6 Placement

Exit-side default: down-fire = per-path regime-death exit, evaluated against the frozen trail. Up-fire logged, not acted on, in v1 — the entry role belongs to the climb, and ANALYSIS-μT's climb-anchored curves quantify what any confirmation delay would cost. Toll gate and EVQ sit between hit and arming, so MRD inherits selection for free. Per-symbol state = six floats; trivial for the shared-feed asyncio architecture. Frozen-trail commitment stands until MRD passes MRD-0 gates. [COOPER DECIDES: exit-only / both-logged for v1.]

---

## 4. Changepoint semantics — which fires mean anything

CPD gives syntax ("distribution shifted at τ, upward, this much evidence"), never semantics ("this is tradeable"). Meaning comes from the event level:

- **EVQ (the climb + context) decides which events' fires can mean anything**
- **CPD decides when within a selected event** — timing only, never asked to find edge

Differentiation layers at the fire, by cost:

1. **Direction + state grammar (free).** Up-fire from rest = logged. Up-fire in position = ignore (v1). Down-fire in position = exit. Down-fire from rest = no action / short-side exclusion flag (subtraction-alpha input).
2. **The h threshold (one knob).** Raising h *is* "ignore weak changepoints." No quality filter beyond h until h alone is shown insufficient.
3. **Noise-implied fire-rate benchmark (hard gate).** Under H₀ a CUSUM at h fires at ≈ 1/ARL₀(h) per revision; given each event's rest-state revision rate, the pure-noise fire count per event is computable. Offline validation must show observed fires exceed noise-implied, and that the **excess** fires separate winners from losers. Total ≈ noise-implied → the detector is a revision-rate thermometer, the runner rate rebuilt in quote space. Dead.
4. **Per-fire feature classification — prohibited initially.** Classifying fires on path features is the entry-time-feature problem in a new hat (three trade-side nulls set the prior). Only if layers 1–3 validate but underperform; labeled attempt #4.

---

## 5. The climb model — scanner heat rebuilt around the thesis

The prior quantization work was sloppy; the theory survived. v2 rebuilds it as the climb's context model.

### 5.1 Five axes

| Axis | Definition | Nature |
|---|---|---|
| **Breadth** | Count of concurrent qualifying events | Tape state (level) |
| **Intensity** | Aggregate magnitude of concurrent events | Tape state (level) |
| **Crowding** | This event's position in the concurrent population | Event state (level) |
| **Velocity** | Rank trajectory into / through the ladder | Event state (derivative) — **the thesis variable** |
| **Catalyst** | News/filing presence at T_hit (Polygon news, EDGAR timestamps) | Event state (binary-ish) — **new in v2** |

The catalyst axis is what separates the situations the old rank-1 statistic conflated (dilution leader vs catalyst leader). Consequence for architecture: the fundamental enrichment layer, previously offline-only labeling, acquires a **thin live component** — a point-in-time catalyst flag at hit. Cheap, causal, and per DIAG-RANK1 potentially the highest-leverage single bit in the system.

**Hard constraint (v2): no rank-derived feature enters EVQ alone — only as rank × context.** Rank 1 of 5 and rank 1 of 50 do not share a column. This is the general rule the rank-1 artifact teaches: rank is a numerator without a denominator.

All axes enter **continuous** — no hand quantization. Quartiles were an analysis convenience that hardened into architecture (border-of-grid failure family). Cut points, if any, emerge from the fit with confidence intervals.

### 5.2 Velocity — relativity, mechanism, and limits

**What relativity buys:** rank is invariant to common scaling — tape-wide vol cancels by construction, killing the vol-thermometer objection in its macro form; convention-consistent (relative measures, no rolling windows). **Mechanism, not just correlation:** in this niche the scanner is the attention-allocation device; the participating traders watch the same ranked lists. A climber captures marginal attention from the names it passes, and attention is order flow. (Origin: Cooper's manual-trading observation; now the project spine.)

**What it doesn't fix:**

- **Idiosyncratic vol leaks through.** A 4%/bar sub-$1 name churns ranks from noise faster than a 1.5%/bar $12 name. Rank spacing is non-uniform (power-law gap spacing widens toward the top). → churn null computed **per rank band**; velocity defined on normalized gap%-vs-list-median, not integer rank.
- **Composition churn → active/passive decomposition.** Rank moves when others enter/exit/fade with zero own action. **Active velocity** = own gap% rose while passing others (fresh flow — the thesis object). **Passive velocity** = competitors faded (survivor on a cooling tape). Hypothesized archetype mapping: passive persistence ↔ multi-day-runner profile; fast active climbs terminating at #1 ↔ parabolic-discovery crowding. Corollary under test: **the trade is the transition, not the state** — enter during the active climb; arrival at rank 1–2 is the exit region, the exhaust of the attention capture, not the target. The absorbing barrier at the top is where the sign may flip.
- **Denominator instability.** Rank 5 of 8 ≠ rank 5 of 60; velocity's denominator is the breadth axis. The five axes are built together or not at all.

### 5.3 Validation constraints

- **Point-in-time or it doesn't exist.** Every component computable at decision time from the live feed, zero revisions, zero forward information.
- **Archive the full ranked scanner population at scan cadence** — not just at hits. Required for trajectories; makes live/backtest bit-identical; **the cheapest irreplaceable data in this document.** Starts immediately, no gate.
- **Vol-conditional validation.** Null: heat axes are volatility thermometers. Each axis must predict frozen-stack PnL conditional on per-event σ, gap-at-hit, price bucket, session. Separation that vanishes under conditioning = the runner rate in macro clothing.
- **Churn null for velocity, sharpened for the thesis.** Under pure rank churn some names climb into the top 2 by luck. Null: frozen-stack PnL conditional on a luck-climb = unconditional +0.9% drift. Thesis: active climbers exceed it. Passive climbs approximate the luck population; the active/passive decomposition is what makes the thesis falsifiable.
- **Target metric:** realized net PnL of the frozen exit stack per event. Never MFE-family.

### 5.4 Pre-registered predictions of the climb thesis

In order of testing cost. [COOPER DECIDES: final registered list before HEAT-0.]

1. ~~Static rank-1-at-entry underperforms~~ — **struck in v2**: the confirming statistic is an aggregation artifact (§1.1); neither confirmed nor necessary. Replaced by DIAG-RANK1's context-cut prediction: underperformance concentrates in thin-breadth × no-catalyst cells.
2. **Active climbers outperform passive climbers** on frozen-stack PnL, conditional on σ, price bucket, session. **← kill criterion for the thesis.**
3. Climb-anchored PnL is front-loaded relative to top-2 arrival (ANALYSIS-μT second alignment).
4. Post-arrival-at-#1 returns are flat-to-negative in the no-catalyst stratum (the exit-side prediction).
5. The active-climb effect strengthens with breadth (passing 40 names means more than passing 6).

### 5.5 Regime conditioning, resurrected

Year-level regime conditioning died on sample size (five yearly means within MOE — conceded). **Breadth-at-hit is the daily-frequency regime proxy that objection demanded**: ~1,250 session observations. The rebuild restores the regime axis with adequate power.

### 5.6 Historical replayability — critical path

**v2 elevation:** if the climb thesis is the axis, the scanner trajectory dataset *is* the research dataset, and this is the single most important open item in the project. Velocity is backtestable only if the scanner is deterministically recomputable from market data at each timestamp — requiring universe-wide bars at scan cadence, not just data for names that qualified. Polygon grouped/snapshot endpoints likely suffice; scope immediately (FEAS-REPLAY). If replay is infeasible, the thesis is testable only from live archival forward — which sets the paper-trading calendar and makes ARCHIVE-SCAN's start date the binding constraint on the entire program.

---

## 6. Data budget rebuild

### 6.1 Why the working sample was 311

Funnel: ~15,000 power-law-filtered events → 990 Tier-1 entries (toll gate) → partition splits → 311 val trades (gate fired). Every cut was correct **for exit research**. The 311 was a budget allocation for a question the project no longer asks.

### 6.2 The selection-research denominator

- **EVQ is classification; the ~14,000 excluded events are the negative class.** The current budget discards, by construction, exactly the examples a selection model learns from.
- Covariate→drift estimation needs neither gate nor trail — hold-to-window-close return per event is a valid target across the population. Working n: hundreds → thousands.
- **Partition structure becomes temporal.** Historical test split is consumed (noise doc provenance). Structure: pre-2025 for hypothesis generation and fitting; 2025-01→present untouched + forward paper as the only validation that counts. On record: pre-2025 is not pristine for EVQ either — a year of exit-lens examination makes the leak indirect but nonzero; priors set accordingly; nothing ships without the temporal holdout.

### 6.3 The audits — gate everything above

- **AUDIT-COND:** `filter_events_power_law.py` — identify the conditioning variable. **If it conditions on realized mom_pct rather than gap-at-hit, the 15k population is outcome-conditioned**: the fizzles (the negative class) are systematically missing, and a classifier trained on it ranks events that already succeeded — useless live. This is the gap-at-hit/mom_pct bug at the population level. If outcome-conditioned → historical re-scan on the live criterion (gap-at-hit ≥ 30% at time-of-hit) defines the true point-in-time population; map coverage against `filtered/`; backfill from Polygon. [COOPER DECIDES: re-scan window and collection budget.]
- **AUDIT-COV:** of the point-in-time population, how many events have quotes in `filtered/`? Sets MRD-0's sample (diagnostic, not config selection — wide sampling spends no partition budget).
- **AUDIT-SCALE:** the entry_price > $1,000 scaling item (scheduled EVQ-0); a corrupted-scale event in a price-bucketed model is a poisoned covariate.
- **Compute reality:** thousands of events × 7-day tick windows on the 32GB box = batched DuckDB passes per HPC conventions from day one.

---

## 7. Sequencing (v2)

Phase names provisional. [COOPER DECIDES: naming, ordering, go/no-go at every gate.]

| Phase | Content | Cost | Gate / kill criteria |
|---|---|---|---|
| **ARCHIVE-SCAN** | Live scanner population archival at scan cadence | Small, ongoing | No gate — **starts immediately**; every unarchived session is unrecoverable thesis data |
| **FEAS-REPLAY** | Scope historical scanner reconstruction from Polygon grouped/snapshot data | Scoping only | Determines whether the thesis is historically testable or live-forward only; **critical path** |
| **DIAG-RANK1** | Context re-cut of historical rank-1 entries (breadth, catalyst-at-hit, session, climb history where available) | Cheap | Composition story predicts concentration in thin×no-catalyst cells; flat across contexts → thesis's arrival-cell prediction takes a direct hit |
| **ANALYSIS-μT** | Cumulative-return curves, mean+median, by stratum; **two alignments** (hit-anchored, climb-anchored) | One pass, existing data | Adjudicates Case A; quantifies confirmation tax; informs window length |
| **AUDIT-COND / COV / SCALE** | §6.3 | Script reading + inventory | Gates the EVQ denominator and MRD-0 sample |
| **MRD-0** | Offline, analysis-only: rest-state p(up) per bucket; autocorrelation; revision-rate profiles; p(up) trajectories winners vs losers; empirical ARL₀ curve; noise-implied vs observed fires | Quote pulls (widen per AUDIT-COV) | **Kill:** winners show no revision asymmetry → channel dead. **Kill:** total fires ≈ noise-implied → thermometer |
| **HEAT-0 / CLIMB-0** | Five-axis computation on the audited population; vol-conditional main effects; per-band churn null; active/passive decomposition; predictions 2–5 of §5.4 | Depends on AUDIT-COND + FEAS-REPLAY | **Kill (thesis):** prediction 2 fails — active climbers do not beat passive climbers or the unconditional drift under conditioning |
| **MRD-1** | Only if MRD-0 passes: CUSUM bank, exit-side, val sweep vs frozen trail | Standard phase | Cooper approval; CVaR5 escalation per convention |
| **EVQ / climb model** | Continuous covariates (five axes + buckets + session + fundamentals) → drift model; temporal holdout | Largest | Endgame architecture per existing plan, respecified as "which climbs to continue-bet" |

Dependencies: ARCHIVE-SCAN, FEAS-REPLAY, DIAG-RANK1, ANALYSIS-μT, and the audits are mutually independent — all can start in parallel. CLIMB-0 hard-requires AUDIT-COND and (for historical velocity) FEAS-REPLAY. MRD-0 benefits from AUDIT-COV but does not require it.

---

## 8. Open decisions register (v2)

| # | Decision | Options on the table | Owner |
|---|---|---|---|
| 1 | MRD v1 placement | exit-only / both-logged-exit-acted | Cooper |
| 2 | CUSUM bank membership | {0.55, 0.60, 0.65} or subset; any-fire vs per-detector | Cooper |
| 3 | Velocity definition | normalized gap%-vs-median vs percentile rank; trajectory horizon; climb-onset definition | Cooper |
| 4 | Active/passive attribution rule | thresholds for "own gap% rose" vs "competitors faded"; mixed-climb handling | Cooper |
| 5 | Catalyst flag definition | Polygon news classes + EDGAR filing types counted as catalyst; staleness window | Cooper |
| 6 | Pre-registered CLIMB-0 list | §5.4 items 2–5 + any additions; interaction policy | Cooper |
| 7 | Temporal holdout boundary | 2025-01-01 (per noise doc provenance) vs later | Cooper |
| 8 | Backfill scope if AUDIT-COND fails | re-scan window; Polygon collection budget | Cooper |

---

## 9. Constraints honored (standing)

- No trade signing in any feature, reference, or detector input — including no WJI/Hawkes buy/sell-split dependencies
- No rolling windows (relativity preserved by cross-sectional definitions)
- Banned metrics stay banned: raw MFE quantiles, runner rates, threshold-touch statistics, capture-vs-MFE objectives
- No rank-derived feature enters any model without its context denominator (breadth at minimum) — **new standing rule, v2**
- Target metric: realized net PnL of the frozen exit stack per event; deterministic-time exit PnL curves permitted (ANALYSIS-μT)
- Trail frozen; MRD enters the exit stack only through MRD-0 → MRD-1 gates
- Halted time never advances any accumulator or decay clock
- Temporal holdout (2025+ plus paper forward) is the only remaining clean validation; all pre-2025 findings are fit-era
- Manual-trading recollections are hypothesis generators, never evidence — verified against records or archived data before entering any registered claim
- Agents present data; Cooper selects all free parameters

---

## 10. Changelog

**v2 (2026-07-08):**
- Climb thesis (active climbers into 1st/2nd) promoted to project spine; EVQ respecified as "which climbs to continue-bet"
- Rank-1 underperformance finding reclassified structural → uninformative (aggregation artifact); DIAG-RANK1 added; prediction 1 struck and replaced
- Catalyst axis added (fifth context variable); fundamentals layer acquires a thin live component (point-in-time catalyst flag)
- Standing rule added: rank features never enter without context denominator
- ANALYSIS-μT gains climb-anchored second alignment
- ARCHIVE-SCAN and FEAS-REPLAY elevated to critical path
- MRD demoted to candidate exit input
- Decisions register expanded (active/passive attribution, catalyst definition, climb-onset definition)

**v1 (2026-07-08):** initial synthesis — non-stationarity decomposition, MRD design, four-axis heat rebuild, data budget rebuild.

---

*Approval gate: no implementation work on any phase in §7 until Cooper has reviewed this document and given explicit per-phase approval.*