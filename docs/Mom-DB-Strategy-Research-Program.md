<!-- fullWidth: false tocVisible: true tableWrap: true -->
---
tags:
  - type/research-spec
  - domain/strategy
  - project/src-core
  - status/draft
created: 2026-07-13
---

# Mom_db Strategy Research Program

**Version:** 2.0\
**Project:** Momentum Event Research — Mom_db

**Data Audit → Structural Constraints → High-Participation Trading → Two-Signal Regime Architecture → Development Process**

---

## 0. Purpose & Scope

This document consolidates the full research design conversation into a single working spec. It covers, in order:

1. What the Mom_db dataset is and what it was built to answer (per `Schema.md`)
2. The data audit and characterization work that must happen before any alpha research
3. The two structural constraints that shape every credible strategy on this archive
4. The case for trading intraday **during** high-participation windows, and the conditions that make it survivable
5. The four foundational measurements that convert that question from vibes into a cost curve
6. A two-signal architecture: a **regime detector** (when the game is on) and an **intra-regime direction signal** (what to do while it's on)
7. The development workflow, validation discipline, and sequenced execution plan

The intended reader is a quant developer/researcher picking this up cold. Every design decision here traces back to either a property of the data or a named failure mode. Where something is unknown, it is flagged as unknown rather than papered over.

---

## 1. The Dataset: What Mom_db Actually Is

### 1.1 Structure

Mom_db is an **event-conditional tick archive**. It is not a general market data lake. Its spine and its purpose are one thing: extreme momentum events.

**The spine — `momentum_events`.** One row per event. Events were selected by `filter_events_power_law.py`, which fits a **q=0.05 quantile regression in log-space** against momentum scan inputs and keeps the extreme tail. The output is `filtered_events_power_law_q05.parquet` (+ CSV). This filter *is* the universe definition. Every downstream result is conditional on it.

**The crown jewel — `filtered/`.** For each event, a folder named `{TICKER}_{YYYY-MM-DD}_{momentum_pct_2dp}` containing two files: `trades.parquet` and `quotes.parquet`, covering a **7-trading-day window centered on the event (T-3 … T+3)**. This is the highest-resolution, highest-provenance asset in the archive. It is where the core research happens.

**Supporting resolutions.** `daily/` (per-symbol daily bars), `minute/` (per-symbol, per-session minute bars), `second10/` (per-symbol, per-session 10-second bars), `quote_data/` (raw symbol-day quote ticks). These exist to support baseline construction, reconciliation, and coarse scans — not as primary research surfaces.

**Reference data.** `market-hours/` (session calendar), `symbol-properties/` (point-in-time symbol attributes), `metadata/` (collection stats, symbol metadata).

**Access layer.** A DuckDB implementation (`src/data/db.py`, `src/data/ingest.py`, `src/data/paths.py`) materializes most datasets into tables (`filtered_trades`, `filtered_quotes`, `momentum_events`, `daily_bars`, `minute_bars`, `second10_bars`, `raw_quotes`, etc.) and exposes the Nautilus catalog as live views (`nautilus_equity`, `nautilus_trade_tick`). The presence of a Nautilus catalog implies an event-driven backtest engine exists downstream — that is the *last* stage of the research pipeline, not the first.

**Provenance.** The schema doc classifies each dataset as **Confirmed** (writer script found), **Inferred** (structure verified, writer missing), or **Unknown** (no reliable evidence). Only `momentum_events`, `filtered/`, and the collection log are Confirmed. Roughly half the archive — `daily/`, `minute/`, `second10/`, `quote_data/`, most of `trade_data/`, `metadata/`, `market-hours/`, `symbol-properties/`, and the Nautilus catalog build — has no confirmed writer in the current workspace. This is not a footnote. It sets policy (see §2.6).

### 1.2 What the data was built to answer

The T-3…T+3 window design means the archive supports exactly three temporal questions:

- **Pre-event (T-3…T-1):** is there detectable buildup — quote behavior, volume creep, accumulation — before the event day? Expected to be weak, but the data is sitting there and it costs one measurement pass.
- **Event day (T=0):** intraday dynamics — the gap, the first-minutes behavior, continuation vs. fade conditional on observables, participation bursts, halts.
- **Post-event (T+1…T+3):** day-2 continuation/fade, gap-fill statistics, mean reversion after blowoff, and — critically — the one surface where the ex-ante information problem largely disappears.

Any strategy built on this archive should exploit that framing, not fight it.

---

## 2. Phase 1 — Data Audit & Characterization

Nothing in this section is alpha research. All of it is prerequisite. The first deliverable of the program is an **audit report** (parquet artifacts + markdown summary), and no signal work begins until it exists.

### 2.1 Define the event, precisely

The q05 power-law filter defines the universe, and its exact mechanics are currently unknown to the researcher. **First job: read `filter_events_power_law.py`.** Answer:

- What was regressed on what? Momentum vs. dollar volume? Vs. float? Vs. price? The regressor choice determines *which kind of extreme* the archive contains.
- How is `momentum_pct` measured — gap at open, open-to-high, close-to-close? The folder naming (`{TICKER}_{DATE}_{MOM}`) encodes it to 2dp, so it is a per-event scalar, but its definition changes what "an event" means.
- What does the fitted quantile boundary look like? The universe boundary is a **researcher choice, not a law of nature**, and it becomes a sensitivity axis later (§7.3).

Then pull distributions straight from `momentum_events` in DuckDB:

- Total event count and date range (this sets the effective sample size for everything downstream)
- Unique ticker count and **repeat-ticker frequency** — serial gappers are common in this universe, and repeat tickers create leakage across validation splits (§7.3)
- The `momentum_pct` histogram — shape, tail thickness, any truncation artifacts from the filter

### 2.2 Column-level inspection & timestamp semantics

`Schema.md` maps folders, not columns. Run `inspect_parquet_columns.py` (already present in `collection_scripts/`) against `filtered_trades` and `filtered_quotes` and establish:

- **Trade condition codes** — present or not? Without them, you cannot exclude non-regular-way prints (odd settlements, derivative prints, averages) from price formation logic.
- **Exchange / venue codes** — needed to understand where liquidity actually posts and prints in these names.
- **Timestamp semantics** — SIP timestamp vs. participant timestamp, precision (nanosecond vs. millisecond), timezone, and monotonicity within files. **Nothing tick-level is trustworthy until timestamp semantics are nailed down.** A signal computed on participant timestamps but executed against SIP-time reality is a different signal.
- Size fields, and whether odd lots appear (odd lots do not update the SIP top-of-book historically — this matters for BBO-derived features in low-priced names where odd-lot share is high).

### 2.3 Coverage & integrity

- **Join rate, both directions:** does every row in `momentum_events` have a matching `filtered/` folder? Does every folder have a matching event row? Orphans on either side indicate collection failures or filter drift between runs.
- **Window completeness:** are all 7 sessions present per event? Missing sessions inside the window are diagnostic. **Missing T+1…T+3 sessions specifically flag halts and delistings** — which cluster in exactly this universe. That absence is simultaneously *signal* (post-event death is an outcome) and *data hazard* (a backtest that silently drops delisted names inflates T+1 results).
- **Session boundary sanity:** validate tick timestamps against `market-hours/` — pre-market and post-market coverage, half days, DST transitions.

### 2.4 Quote & trade quality characterization

These are thin, violent names. Before trusting any BBO-derived signal, measure per event and pooled:

- **Crossed / locked market frequency** — how often, how long, and whether it concentrates in bursts (it will; see §4.2 condition 3)
- **Zero-size and stale quotes** — stale-quote run lengths, i.e., how long the displayed BBO sits untouched while trades print through it
- **Quote-to-trade ratios** and inter-quote interval distributions — quote flicker vs. genuine liquidity
- **Spread distributions, event day vs. T-3 baseline** — this is the direct empirical test of the spread-compression claim in §4.1

This pass determines whether spread-sensitive features are usable at all, and it feeds the fill model (§7.2) directly.

### 2.5 Cross-resolution reconciliation

Aggregate `filtered_trades` up to 10-second, 1-minute, and daily bars and diff against `second10_bars`, `minute_bars`, and `daily_bars` on overlapping symbol-days. Disagreements expose **silent collection bugs cheaply** — mismatched condition-code handling, timezone slips, missing venues. This is the single highest-value integrity check per unit of effort, because it cross-validates Confirmed data against Inferred data without needing the missing writer scripts.

### 2.6 Provenance quarantine policy

Standing rule: **nothing load-bearing gets built on Inferred or Unknown provenance data** until reconciled against writer logic or validated by reconciliation (§2.5).

- `filtered/` and `momentum_events` are Confirmed → primary research surface.
- `daily/`, `minute/`, `second10/`, `quote_data/` are Inferred → usable for baselines and reconciliation once §2.5 passes; not for headline results before that.
- `trade_data/` is Unknown with a legacy-mess directory structure (`batches/`, `by_date/`, `enhanced/`, progress JSONs) → treat as radioactive. Do not touch until provenance is reconciled or an external archive of collection scripts surfaces.

The schema doc's own "Known Gaps" section is the previous owner telling you the foundation was never fully verified. Believe them.

### 2.7 Audit deliverable

One report, versioned: event universe statistics (§2.1), column and timestamp findings (§2.2), coverage matrices (§2.3), quote-quality distributions (§2.4), reconciliation diffs (§2.5), and the quarantine ledger (§2.6). Boring. Everything else stands on it.

---

## 3. Structural Constraints

Two problems shape every credible strategy on this archive. They are **design constraints, not caveats** — they determine which strategy surfaces are honest before a single feature is computed.

### 3.1 Ex-ante trigger selection bias

The events were selected **with full knowledge of the event-day outcome**. The filter saw the completed daily move and kept the extreme tail. Consequence: any intraday entry placed *before the move completes* is partially trading on the information that was used to select the sample. A naive backtest that "enters at 9:35 on event days" is answering the question "what if I could see the closing scanner output at the open" — which is fiction.

Two clean escapes:

1. **Ex-ante trigger reconstruction.** Define a trigger computable in real time from data available at time *t* — e.g., "up X% from open by time *t* on Y× time-of-day-matched relative volume" — apply it inside the event days, and **measure outcomes strictly after trigger time**. The trigger, not the filter, becomes the entry condition. Events that never trip the trigger are excluded from that strategy's sample.
2. **Trade T+1.** By the T+1 open, the event day is fully observable. Entry conditions on T+1 use only completed information. This is the **cleanest research surface the dataset offers**, and it is why the strategy-family ranking in §6 puts day-2 strategies first.

### 3.2 Missing counterfactuals

The archive contains **only the filter's winners**. There is no set of near-misses — names that gapped 25%, tripped a plausible real-time scanner, and then died. Consequences:

- **Conditional questions are answerable:** "given an event, what predicts continuation vs. fade" is fully supported.
- **Unconditional questions are not:** trigger precision in the wild — how many false positives a live scanner fires per true event — cannot be estimated from this archive alone. A strategy's live PnL depends on exactly that ratio.

Partial mitigations, in order of availability:

- **Check the breadth of `daily/`.** If it covers a wide symbol universe (currently unknown — audit item), it can seed a partial control set of near-miss days at daily resolution.
- **Flanking days as pseudo-controls** (§5.1, step 5): T-3…T-1 and T+2…T+3 are quieter sessions *on the same names*, usable for false-positive estimation — with the honest caveat that they are event-adjacent, not independent.
- **Eventually, an unconditional universe scan** must happen before capital does (§5.4, §8). This is a known hole to flag, not paper over.

### 3.3 Credible strategy surfaces, ranked (revised under D5)

1. **Intraday post-trigger, long-only** — the program spine. Requires ex-ante trigger reconstruction per §3.1 escape #1, with all outcomes measured strictly post-trigger. Carries the counterfactual gap on trigger precision (§3.2), which D5 upgrades from a caveat to a near-front blocker: under a gate-then-trade design, the live false-positive rate is a direct PnL term.
2. **T+1 (day-2) continuation** — the cleanest ex-ante surface the archive offers, retained as a **single optional measurement pass** answering "does this archive contain any edge at all." Not a pillar, and it no longer gates detector work. Long-only under D5; the fade variant is dropped.
3. **Pre-event detection (T-3…T-1)** — unchanged. One measurement pass, most likely a respectful burial.

**Note on the prior ranking.** v1.x ranked T+1 first on ex-ante cleanliness, and the Operating Plan ordered the T+1 markout grid ahead of detector development on the reasoning that a flat grid saves six weeks. D5 overrides that ordering deliberately, accepting the cost: the cheapest edge-existence check is now optional rather than gating. Recorded here so the override is visible, not inferred.

---

## 4. Trading Intraday During High-Participation Windows

### 4.1 Why the conventional logic inverts

The standard "avoid the frenzy" wisdom comes from liquid large caps, where you can trade any time of day and the high-volume windows are where informed institutional flow runs you over. That logic **inverts in thin gap names**:

- **Outside the burst, there is no market.** Quoted spreads of 2–5%, no size on the book, a single 200-share print moves the tape. "Waiting for calm" in this universe means waiting for liquidity to disappear.
- **Spreads compress when participation spikes.** Transaction costs are typically *lowest* exactly when the tape looks scariest. This is an empirical claim, and it is directly measurable in `filtered_quotes` (§2.4, §4.3) — measure it, don't assume it.

Conclusion: in this universe, the high-participation windows are not merely tradeable — **they are the only windows worth trading**. The real risk does not live in volatility; it concentrates in halt exposure (condition 2 below).

### 4.2 Survivability conditions

The yes is conditional. Four conditions, each of which is where a backtest quietly lies if ignored:

**Condition 1 — Take liquidity, don't provide it.** During a burst, resting orders get filled precisely when flow turns against you. Adverse selection against passive orders in a squeezing thin float is brutal. Crossing the spread with a directional view is plausible; making markets in these conditions is how you donate. Strategy design implication: aggressive-only entry logic, spread cost fully charged (§7.2).

**Condition 2 — Halts are the tail risk, not volatility.** LULD halts cluster in exactly these windows. The strategy-ending scenario is *trapped-in-halt with a 20% adverse reopen*, not a fast market. Therefore halt risk is a **first-class model input**, not a footnote:

- P(halt | current state) — estimable from trade timestamps plus LULD band arithmetic
- Reopen gap distribution conditional on pre-halt state
- Position sizing constrained to **survive the worst plausible reopen**, not the average one

**Condition 3 — The backtest is least trustworthy exactly here.** Burst windows are where BBO data is dirtiest: crossed/locked quotes, quote flicker, stale SIP prints. The measured "edge" during high participation is the number most contaminated by fill fantasy. Mitigations: use **effective spread** (trade price vs. prevailing midpoint) rather than quoted spread; pessimistic fill assumptions; and quantify quote quality per event before trusting anything (§2.4).

**Condition 4 — Latency constrains signal horizon, not participation.** With retail-grade execution, sub-second signals during a burst are fiction — the book you see is stale by the time you act. But 30-second-to-5-minute horizons survive modest latency fine. The window doesn't rule you out; it rules out certain *speeds*. Design implication: every feature is lagged by realistic pipeline latency at decision time (§5.2).

### 4.3 The four foundational measurements

Per event, computed from `filtered_trades` + `filtered_quotes`. These convert the participation question from vibes into a cost curve, and they feed every downstream design decision (thresholds in §5.1, cost model in §7.2, sizing in condition 2):

1. **Volume/range concentration curve** — what fraction of the day's move and volume occurs in what fraction of time. Output: burst duration scales and the **opportunity-decay curve** that prices detection delay (§5.1, step 4).
2. **Spread conditional on participation** — quoted and effective spread bucketed by participation rate. Output: the direct test of the compression claim (§4.1) and the regime-label spread threshold (§5.1, step 1).
3. **Effective spread and impact of aggressive prints, burst vs. quiet** — price impact per unit signed volume in each state. Output: the false-positive cost (round-trip effective spread, §5.1 step 4) and the raw material for the impact-efficiency feature (§5.2).
4. **Halt frequency and reopen gap distributions** — P(halt | conditions), time-to-halt, reopen gap sizes. Output: the sizing constraint and the LULD-proximity veto (§5.2).

---

## 5. Two-Signal Architecture

### 5.0 Design principle: the clock and the state

Two different problems with **two different loss functions**:

- The **regime detector** is a clock. It decides *when the game is on*. It is optimized for **detection latency vs. false-positive cost**.
- The **intra-regime direction signal** is state. It decides *what to do while the game is on*. It is optimized for **cost-adjusted markouts within confirmed regimes**.

Do not collapse them into one score. A blended score makes losses unattributable — you cannot tell whether you lost because you entered a dead regime (clock failure) or traded the wrong direction in a live one (state failure). Separation is what makes the system debuggable.

Build the clock first.

### 5.1 Signal 1 — Regime detection

**Step 1: Label regimes offline, with hindsight.** Before any online detector exists, define what a regime *is* on historical data where lookahead is allowed. Candidate label: rolling windows where volume rate > k× baseline AND spread < event-median, sustained ≥ N seconds, with merge rules for gaps and a minimum dwell time. The four measurements feed the definition directly — the concentration curve (§4.3.1) sets duration scales; spread-vs-participation (§4.3.2) sets the compression threshold. Then run **sensitivity analysis on the label itself**: perturb k, N, and the merge rules and check regime-set stability. **If small label changes produce wildly different regime sets, the foundation is sand** and no detector downstream can be meaningfully evaluated.

**Step 2: Solve the baseline problem.** "High participation *relative to what*?" is most of the detector. These names did 50k shares/day for a month, then 40M on event day. Naive ratios against pre-event baselines explode and saturate immediately — everything on event day looks like a regime, and the detector degenerates into a session flag. Options, to be tested against labels:

- **Time-of-day-matched baselines** built from T-3…T-1 (volume rate at 9:45 compared to 9:45 on flanking days, not to a whole-day average)
- **Log-space rates**, which tame multiplicative blowups
- **Additive rate changes** instead of ratios where baselines approach zero

This step is unglamorous, and it is where the detector actually gets built.

**Step 3: Online detector — simplest thing that meets the latency budget.** The concentration curve makes the budget explicit: if 50% of the move happens in the first 4 minutes and the detector needs 90 seconds to confirm, ~40% of the opportunity is burned on confirmation. Candidates, in increasing sophistication:

- **Threshold + hysteresis** — regime-on at rate > k_on × baseline, regime-off below k_off < k_on. Dumb, fast, and hard to beat.
- **CUSUM / Bayesian online changepoint detection** on trade arrival rate — principled rate-shift detection with quantifiable expected delay.
- **Self-exciting (Hawkes-type) intensity** — λ(t) as a continuous participation measure that captures *clustering* rather than mere level; a branching ratio approaching 1 reads as a reflexive, self-feeding regime.

Standing rule: **complexity must be earned.** A fancier detector must beat threshold+hysteresis on detection latency at matched false-positive rate, or it is decoration.

**Step 4: Pick the operating point by expected PnL, not ROC.** Every false positive costs a round-trip effective spread (measurement #3). Every second of detection delay costs opportunity along the concentration curve (measurement #1). The objective is: (move captured per true positive × TP rate) − (FP cost × FP rate). **AUC is a vanity metric here** — a detector can dominate on ROC and lose money at every feasible operating point.

**Step 5: Use flanking days as pseudo-controls.** T-3…T-1 and T+2…T+3 are quieter sessions *on the same names*. Run the frozen detector there to estimate false-positive behavior. This is the honest FP estimate available without new data collection — with the explicit caveat that flanking days are event-adjacent, not independent, so it patches rather than solves the counterfactual gap (§3.2).

**Step 6: Detect regime death with equal care.** Intensity decay, spread re-widening, flow flip. The fade after a burst is violent, and **the end-detector is the primary exit** of any intra-regime strategy. Regime entry and regime death are equally important problems; under-investing in the second is the classic failure mode.

### 5.2 Signal 2 — Intra-regime direction

**Target definition first.** The label is **cost-adjusted markouts**: forward mid-price move minus effective spread, at horizons matched to regime internal timescales from the concentration curve. Not raw returns — in this universe the spread eats naive signals whole, and a signal that predicts raw mid moves smaller than the spread predicts nothing tradeable.

**The benchmark that keeps you honest.** Within a detected burst, the base rate already favors continuation — that is what self-excitation *means*. Therefore the direction signal must beat **"always long while regime is on," after costs** — not beat zero. Most intra-regime "alpha" evaporates against this null. If a candidate signal doesn't clear it, the strategy is *the detector plus a market order*, and that is a perfectly fine strategy. Simpler is better; know which one you actually have.

**Feature stack**, roughly ordered by expected information value:

1. **Signed flow imbalance** — aggressor classification via quote rule / Lee-Ready on the tick data; rolling signed volume. The basic question: who is crossing, bid or ask?
2. **Impact efficiency** — price change per unit signed volume; the running derivative of measurement #3. Rising impact per share = the book is thinning = continuation is fragile. Falling impact against heavy flow = absorption = someone large is sitting there. **This second-order feature is where the real information is expected to live** — level features mostly restate the regime detector.
3. **Spread re-widening mid-regime** — liquidity providers backing off is an early instability tell, often preceding intensity decay.
4. **Regime age vs. the hazard function** — duration distributions from measurement #1 give P(death | age). Minute 1 of a typical burst and minute 9 are different trades even with identical instantaneous flow.
5. **LULD proximity + P(halt | state)** — primarily a position-size scaler and hard veto near bands (measurement #4). Secondary hypothesis worth one measurement pass: halt-and-continue vs. band-rejection patterns may carry directional information.

**Capacity discipline.** The effective sample size is **regimes, not ticks** — likely hundreds to low thousands. Methodology follows from that:

- Event-study each feature against markouts first: bucketed conditional means, monotonicity checks. Kill features here, cheaply.
- Then a linear model on a small handful of **orthogonalized** survivors.
- Anything fancier must beat the linear model out-of-sample under **ticker-blocked splits** — repeat tickers leak hard, and a model that memorizes serial gappers will look brilliant in-sample.

**Lag everything.** Every feature is computed as of decision time minus realistic pipeline latency. A feature computed at *t* but acted on at *t*+800ms in a burst is a different feature. Bake the lag into research, not just production.

### 5.3 Development order

1. Label regimes offline (§5.1.1) →
2. Characterize labeled regimes: duration distributions, internal structure, spread/impact evolution over regime life →
3. Build online detector, evaluate against labels, choose operating point by PnL (§5.1.3–4) →
4. Event-study direction features **within true-positive regimes only** (§5.2) →
5. Joint walk-forward of detector + direction + exit stack, with **halts modeled as forced holds** through the reopen.

### 5.4 The circularity trap

Named explicitly because it will otherwise bite silently: the events were selected on big daily moves, so **nearly every event day contains a labeled regime by construction**. Consequences:

- Conditional analysis is fine: "given a regime, what happens" is exactly what the archive supports.
- **Regime frequency statistics from this archive say nothing about the wild.** How often the detector fires on an ordinary trading day across an ordinary universe is unknowable from event-conditional data.
- Flanking-day pseudo-controls partially patch this. A proper **unconditional universe scan has to happen before capital does.** It is on the risk register (§8), not optional.

---

## 6. Event Studies Before Backtests

Standing methodology: **event-study first, backtest second.** Conditional forward-return analysis is cheap in DuckDB and tells you where the meat is before a single line of order-management logic exists.

- **Markout grid (burst-relative under D5):** cost-adjusted forward returns at horizons matched to measured burst timescales, anchored on burst confirmation. Day-scale anchors (open, close, T+1, T+3) are retained only for the optional T+1 pass and are not the primary grid.
- **Conditioning features (event level):** gap size, first-5-minute range, relative volume, spread regime, trade imbalance, prior-day behavior from T-3…T-1, `momentum_pct` itself.
- **Output:** conditional markout tables with bucketed means, monotonicity checks, and sample counts per bucket. Hypotheses that show nothing here do not graduate to backtesting.

This layer is also where the three strategy families (§3.3) get triaged: T+1 continuation/fade gets its feature set from completed event-day observables; intraday post-trigger gets its markouts measured strictly post-trigger; pre-event detection gets its single measurement pass and, most likely, a respectful burial.

---

## 7. Development Workflow & Process

### 7.1 Layered pipeline

Each layer produces a **versioned artifact**. No layer starts before the previous one's artifact exists.

1. **Audit layer** → data-quality report (§2.7). Deliverable #1 of the program.
2. **Feature layer** → event-level and intraday features precomputed **once** into DuckDB tables. Expensive labels and lookups are resolved once per event at the anchor and cached — never recomputed inside a research loop.
3. **Event-study layer** → markout tables conditional on features (§6). Weak hypotheses die here, cheaply.
4. **Vectorized backtest** → survivors only, under the cost model in §7.2. Fast iteration, harsh assumptions.
5. **Nautilus (event-driven) backtest** → last, for final execution realism on the short list. The catalog views mark it as the production engine; it is far too slow for hypothesis triage, which is why it sits at the end.

### 7.2 Cost & fill model requirements

In this universe **the cost model matters more than the alpha model.** Non-negotiables:

- **Always cross the spread** on entry and exit — aggressive-only assumption per §4.2 condition 1.
- **Effective spread, not quoted spread**, as the cost basis (§4.2 condition 3).
- **Slippage scaled to observed spread and participation** — your fill degrades with your own size relative to the tape.
- **LULD halts modeled as "you cannot exit"** — forced hold through the halt, fill at the reopen distribution from measurement #4. No backtest that lets you exit into a halt is admissible.
- Where shorting enters (T+1 fade variants): SSR mechanics and borrow availability are modeled or the variant is shelved.

### 7.3 Validation discipline

- **Time-based splits:** train on older events, test on newer. Regimes shift in this space; random splits flatter the model.
- **Ticker-level blocking:** repeat tickers leak across splits (§2.1, §5.2). No ticker appears on both sides of a split.
- **Universe-boundary sensitivity:** sweep the q05 threshold. The filter is a researcher choice (§2.1); results that only exist at exactly q=0.05 are artifacts.
- **Label sensitivity:** the regime-label perturbation test (§5.1.1) is a standing gate, not a one-off.
- **Cost sensitivity:** every headline result reported at 1×, 1.5×, 2× the base cost model. Edges that die at 1.5× are not edges.

### 7.4 Process habits

- **Half-page hypothesis spec before code**, for every idea: ex-ante signal definition, entry/exit, cost assumptions, and *what failure would look like*. If the failure mode can't be written down, the hypothesis isn't ready.
- **`research/` sandbox vs. `src/` promotion:** exploratory code lives in `research/`; only tested, promoted logic enters `src/`. The DuckDB layer (§1.1) is the shared substrate for both.
- **Deterministic, config-driven runs** with versioned outputs, so any table in any report regenerates from a config hash.

---

## 8. Risks, Gaps & Open Questions

| # | Item | Status | Consequence if ignored |
|---|---|---|---|
| 1 | Provenance reconciliation for Inferred/Unknown datasets (§2.6) | Open — external archive not located | Silent data corruption enters baseline construction and reconciliation |
| 2 | Exact mechanics of the q05 filter (§2.1) | Open — script unread | Universe definition misunderstood; sensitivity sweeps mis-specified |
| 3 | Missing counterfactual / near-miss set (§3.2) | Structural — **near-front blocker under D5** (was: partially mitigated by flanking days). Hardened by Phase 8 A10.2d: the rejected-candidate population is confirmed absent from the archive, so the live FP rate is unmeasurable from what is on disk | Under D5's gate-then-trade design the live false-positive rate is a **direct PnL term, not a caveat** — every markout is conditional on power-law-filter membership, which is not knowable at detection time |
| 4 | Circularity of regime frequency (§5.4) | Structural — **near-front blocker under D5** (was: requires unconditional universe scan before capital). The scan cannot be sequenced last | Detector fire-rate in the wild unknown, so the cost of every false fire is unpriced; under a long-only burst strategy that cost is paid in round-trip effective spread on every wrong gate |
| 5 | `daily/` universe breadth for control-set construction (§3.2) | Open — audit item | Determines whether a partial counterfactual set is even buildable in-house |
| 6 | Halt/reopen model fidelity (§4.3.4, §7.2) | Open — measurement pass required | Tail risk mis-sized; the one scenario that ends the strategy is unpriced |
| 7 | Regime label stability (§5.1.1) | Open — perturbation test pending | All detector evaluation is built on sand |
| 8 | Delisting/halt handling in T+1 results (§2.3) | Open — coverage audit item | Day-2 strategy results inflated by silent survivor filtering |
| 9 | Archive universe (q05 on completed daily moves) vs. intended live universe (real-time ≥30% from previous close, pre/post-market inclusive) are different populations | Open — first-class under D5 | Every conditional result is measured on a population the live screen does not reproduce; live PnL diverges by an unquantified amount |

---

## 9. Sequenced Execution Plan

**Week 1 — Audit only.** Read the two Confirmed scripts (`filter_events_power_law.py`, `collect_massive_data.py`). Run §2.1–2.6. Produce the audit report (§2.7). No alpha work. Boring by design — everything else stands on it, and the schema doc's own gap list is the previous owner saying the foundation was never fully verified.

**Weeks 2–3 — Foundational measurements + feature layer.** The four measurements (§4.3) per event, pooled and bucketed. Precompute the event-level feature tables (§7.1 layer 2). First pass of the event-study grid (§6) for the T+1 family — it is the cleanest surface and the fastest path to knowing whether the archive contains a tradeable edge at all.

**Weeks 3–4 — Regime labeling.** Offline labels, perturbation stability test, labeled-regime characterization (§5.1 steps 1–2, §5.3 steps 1–2). Baseline construction from flanking days.

**Weeks 4–6 — Detector development.** Threshold+hysteresis baseline, then CUSUM/BOCPD and intensity-based challengers; operating point by expected PnL; flanking-day FP estimation; regime-death detector (§5.1 steps 3–6).

**Weeks 6–8 — Direction signal.** Feature event-studies within true-positive regimes against the always-long null; orthogonalized linear model; ticker-blocked out-of-sample (§5.2).

**Weeks 8+ — Joint walk-forward and engine realism.** Detector + direction + exit stack under the full cost model with halts as forced holds (§5.3 step 5); vectorized first, Nautilus for the short list (§7.1 layers 4–5). In parallel: scope the unconditional universe scan (§5.4) — it gates capital, so it cannot start last.

Dates are ordinal, not promises. The gates between phases are the artifacts, not the calendar.

---

## Appendix A — Glossary

- **Effective spread** — 2 × |trade price − prevailing midpoint|; what aggressive orders actually paid, as opposed to the quoted spread.
- **Markout** — forward price move from a reference point (fill, trigger, regime confirmation) at a fixed horizon; *cost-adjusted markout* subtracts effective spread.
- **LULD** — Limit Up–Limit Down: exchange volatility bands that pause trading when breached; the dominant tail-risk mechanism in this universe.
- **SSR** — Short Sale Restriction (Reg SHO 201): triggered by a 10% intraday decline; constrains short entries to upticks through the next day.
- **Aggressor classification / Lee-Ready** — inferring whether a trade was buyer- or seller-initiated by comparing trade price to the prevailing quote (with tick-rule fallback).
- **CUSUM / BOCPD** — cumulative-sum and Bayesian online changepoint detection; sequential tests for rate shifts with quantifiable detection delay.
- **Hawkes intensity / branching ratio** — self-exciting point-process arrival rate λ(t); branching ratio near 1 means each event begets ~1 more: a reflexive, self-feeding regime.
- **Impact efficiency** — price change per unit signed volume; rising = thinning book, falling under heavy flow = absorption.
- **Hazard function** — P(regime death in the next instant | regime age); turns duration distributions into an age-conditional exit prior.
- **Pseudo-controls (flanking days)** — T-3…T-1 and T+2…T+3 sessions used to estimate detector false positives on the same names outside the event day.
- **Quantile regression (q=0.05, log-space)** — the power-law tail filter that defined the event universe; the archive's selection mechanism and a standing sensitivity axis.

---

## Version History

| Version | Date       | Change                                                                                                              |
| ------- | ---------- | ------------------------------------------------------------------------------------------------------------------- |
| 2.0     | 2026-08-03 | D5 redirect: §3.3 re-ranked, §6 re-anchored, §8 risk items #3/#4 upgraded, §9 rewritten. Short-side variants removed. |
| 1.x     | 2026-07-13 | Initial spec. No version history was recorded before the 2.0 bump; "1.x" is the retroactive designation used by §3.3's note on the prior ranking. |

**Status of the 2.0 row, 2026-08-03 (agent note, not Cooper text).** §3.3, §6 and §8 landed as
described. **§9 was not rewritten** — `prompts/redirect_d5.md` T3d specifies §9 as "sequenced from the
phase map in T4", and T4 hard-stopped: `docs/Claude-Code-Operating-Plan.md` does not exist in this
checkout and the T4 map's rows 8 and 9 conflict with the already-approved Phase 8 and the in-flight
Phase 9. §9 therefore still carries the v1.x week-numbered plan and is stale with respect to D5.
Remove this note when T3d lands. See `results/redirect_d5/REPORT.md`.
