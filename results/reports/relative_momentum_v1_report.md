# Relative momentum v1 — causal threshold, corrected population — REPORT

**Branch:** `explore/relative-momentum-v1` · **Config hash:** `ede4e9e8082b`
**Status: complete.** T0–T5 ran, five charts, all four fixes applied.
Brief: `prompts/relative_momentum_v1.md`.

## What this settles

> **v0's damage was not an artifact.** With the level gate made causal and the population corrected to
> genuine +30% crossers, post-warmup and like-for-like: the baseline's median gross markout is **−39 bp**
> and Policy B's is **−187 bp**; the gross win rate falls from **43.6% to 38.9%**. The in-sample
> threshold accounted for part of v0's damage — v0's own threshold on this population gives −243 bp
> against the causal rule's −189 bp — but it was not the cause. **Level-gating on this score degrades the
> median outcome, causally and on the right population.**

**And Fix 3 answers the question the expensive rebuild was waiting on.** On all of D1, at the gate's own
window length, the median candidate still has no competitor; **27.9% of candidate moments carry a second
live name, against 10.5% measured on this gate population.** A full causal re-derivation over D1 would
buy roughly 2.7× the contest rate, not a cross-section where none existed. Whether that is worth the
build is a decision, not a measurement — but the number is now on record instead of guessed.

---

## T0 (Fix 2) — the population, with the gap gate ON

`t0_population.py` · `artifacts/t0_population.json`, `t0_candidates.parquet`

**Method: a faithful post-hoc reconstruction of the runner's own gap gate, not a re-run.**
`scanner-epg-momentum` is read-only per CLAUDE.md and its val_full run took 20,713 s. The gap gate is a
deterministic function of the tick stream inside each PASS window, and every PASS window's bounds are on
record in `per_trade.parquet`, so it reconstructs exactly.

The semantics reproduced, from `runner.py:822-895` — and the middle one matters, because a naive filter
would have got it wrong:

| behaviour | reproduced |
|---|---|
| rising edge already at or above +30% → **immediate** entry | yes |
| otherwise → **queued wait**, re-checking every tick while the window stays PASS; first qualifying tick enters | yes |
| window closes before the threshold is met → that window is **blocked** | yes |
| the condition is tested on `price[i]`; the fill is **`price[i+1]`**, the next tick | yes |
| `entry_ts` is `ts[i]`, the trigger tick, not the fill tick | yes |

**Validated before building on it:** 6 of 6 spot checks reproduce the existing run's recorded
`entry_price` exactly from `px[i+1]`.

**Threshold applied to `move_at` against the tick-derived prior close**, not to the gate's own
`intraday_pct`. D4 requires it, and v0-T4 measured the two measures at Spearman **0.314** — they are not
the same condition, and only one of the gate's three prev-close sources is tick-derived. The gate's own
measure is reported as a variant: only **208** of the 903 entries would have `intraday_pct_at_entry ≥ 30%`
on the v0 first window.

| step | n |
|---|---|
| events with at least one PASS window in the original run | 1,027 |
| **gap gate ON: events with a window that produces an entry** | **903** |
| — every window blocked (never reached +30% inside a PASS window) | 94 |
| — no tick-derived prior close | 30 |
| of which in D1 | **903** (all) |

**311 of the 903 entries are queued**, not immediate — 34%. A hard-block reading of the gap gate would
have thrown those away and shrunk the population by a third. Queued waits run median **120 s**, p95
1,244 s. Half the events entered on their first PASS window; p75 had 2 windows blocked first, p95 had 8.

**The population is now the thesis.** `move_at` at entry: p5 **+28.8%**, p25 +30.3%, **median +36.0%**,
p75 +54.7%. v0's entry `intraday_pct` had median +11.25% and p25 −23.4%. **57% of entry instants moved**
versus v0.

122 fills land marginally below the nominal +30% because the fill is the next tick — median gap −1.0%,
p5 −7.1%. That is the runner's own convention, reproduced, not a leak. It is also a real cost, and §T3
prices it.

Median hold **605 s**. `session_bucket` at the original edge: 602 pre-market, 299 regular hours, 2 post.

---

## T1 — the score at the new entry instant

`t1_score.py` · `artifacts/t1_score.json`, `t1_scored.parquet`

Unchanged by instruction: relative volume, 10-minute trailing window, E2's 3-session `B_e`, one measure.
τ is the gap-gated **trigger** instant, and the causality assertion in
`common.window_dollar_volume` fires if any print after τ reaches a returned quantity.

Score median **31.9** (v0: 13.4) — the gap gate selects moments with more volume behind them, as it
should. Immediate entries score far higher than queued ones (median 63.8 vs 11.3): waiting for the
threshold means entering after the burst that would have scored well.

The RTH-scoped-baseline mismatch carries over as a facet: 602 of 903 τ are pre-market, comparing an
extended-hours window against a regular-session baseline.

---

## T2 (Fix 1) — gate 1 made causal

`t2_gates.py` · `artifacts/t2_gates.json`, `t2_gated.parquet` · chart 05

At each candidate moment, the threshold is the 75th percentile of **strictly prior** candidate scores,
pooled across tickers. Nothing in the rule depends on data from after the trade it gates.

> **The warmup is not negligible, and the brief asked to be told.** 250 of 903 candidates — **27.7%** —
> sit in gate 1's warmup and pass by default. Warmup ends **2024-02-08**, a quarter of the way through an
> eight-month sample. Every gate-1 policy is therefore reported **both with and without** warmup, and the
> **post-warmup row is the one to read**.

The causal threshold **drifts**: 151 at its first defined value to 220 at its last, median 195. It is
drawn in chart 05 rather than quoted as one number, because a rule whose level moves is a different rule
from a fixed one. Post-warmup it passes **183 of 653 (28.0%)**.

For contrast, v0's in-sample threshold recomputed on *this* population is **216**, passing 226. The causal
rule is looser than v0's for most of the sample.

**Gate 2, unchanged** — and concurrency got *worse*, because the gap gate thinned the field:

| candidates live at that moment | 1 | 2 | 3 |
|---|---|---|---|
| candidate moments | **808** | 89 | 6 |

**89.5% alone**, against v0's 79.5%. Gate 2 passes 855 of 903; **808 of those passes are uncontested** and
only 47 won a contest. Policy B is 417 trades, of which 237 are warmup passes — **180 post-warmup**.

---

## T3 — the policy table

`t3_evaluate.py` · `artifacts/t3_evaluate.json`, `t3_evaluated.parquet` · chart 01

Cost is Phase 11's stack in both units (D19). **The gate has no native fill or cost model** — verified in
v0-T3: `pnl` is a pure price ratio and `strategy.json` has no fee block — so the brief's "whichever fits
better" had only one option. Per-share cost in bp: p25 51.7, **median 117.4**, p95 1,325.

### All figures in basis points. Post-warmup rows are the honest read.

| policy | n | warmup share | **gross median** | gross mean | net median flat | net median per-share | **win rate gross** | win net flat | hold s |
|---|---|---|---|---|---|---|---|---|---|
| A · every gap-gated signal | 903 | 27.7% | −1.3 | +163.7 | −72.2 | −232.6 | 45.2% | 41.2% | 605 |
| **A · post-warmup only** | **653** | 0% | **−39.3** | +158.5 | −110.3 | −283.2 | **43.6%** | 40.0% | 620 |
| B1 · causal gate 1 | 433 | 57.7% | −1.4 | +180.2 | −72.4 | −231.1 | 44.8% | 40.2% | 621 |
| **B1 · causal gate 1, POST-WARMUP** | **183** | 0% | **−188.7** | +183.7 | −259.7 | −379.9 | **38.8%** | 34.4% | 733 |
| B1-v0 · v0's in-sample gate 1, here | 226 | 23.0% | **−243.3** | +164.2 | −314.2 | −446.4 | 39.8% | 35.8% | 811 |
| B2 · gate 2 only | 855 | 27.7% | 0.0 | +176.4 | −71.0 | −228.2 | 45.5% | 41.3% | 599 |
| B · both gates | 417 | 56.8% | −1.4 | +191.2 | −72.4 | −231.1 | 44.6% | 39.8% | 619 |
| **B · both gates, POST-WARMUP** | **180** | 0% | **−186.9** | +197.6 | −257.9 | −378.4 | **38.9%** | 34.4% | 720 |
| B-contested · gate 2 decided | 25 | 28.0% | −133.0 | +572.2 | −204.0 | −188.7 | 48.0% | 44.0% | 812 |

### The full distribution

| policy | p1 | p5 | p10 | p25 | p50 | p75 | p90 | p95 | p99 |
|---|---|---|---|---|---|---|---|---|---|
| A · post-warmup | −2,513 | −1,474 | −1,083 | −594 | −39 | +478 | +1,404 | +2,489 | +5,626 |
| B1 · causal, post-warmup | −3,222 | −2,137 | −1,452 | −842 | −189 | +479 | +1,958 | +4,030 | +9,901 |
| B1-v0 · in-sample | −3,552 | −2,239 | −1,575 | −869 | −243 | +535 | +2,201 | +4,173 | +8,996 |
| B · both, post-warmup | −3,226 | −2,146 | −1,473 | −831 | −187 | +479 | +1,963 | +4,084 | +10,019 |

**Three readings.**

**The level gate degrades the median, causally.** Post-warmup A −39 bp → B −187 bp, win rate 43.6% →
38.9%. The causal rule is *less* damaging than v0's in-sample one (−189 vs −243) so the in-sample
threshold was part of v0's effect — but removing it does not remove the effect.

**Mean and median disagree again, in the same direction as v0.** B's mean (+198) exceeds A's (+159) while
its median is 148 bp worse, because qualification widens both tails: p1 −3,226 vs −2,513, p99 +10,019 vs
+5,626. **A profit-factor read of these same trades would call Policy B an improvement.** Only 4.5% of
trades are exactly zero, so the medians are real centres, not a degenerate atom.

**Nothing clears cost.** The best net median in the table is −71 bp. Not one policy, in either cost unit,
on the full or post-warmup base.

**One cost the gate imposes on itself and does not model.** Its fill convention — test `price[i]`, fill
`price[i+1]` — costs a **mean of −30.3 bp**, median 0.0, p5 −213.6, negative on 33.6% of entries. That is
*on top of* the spread cost above, not inside it.

**B-contested is n = 25.** Above the display floor of 20 but barely; its +572 bp mean is one large winner
and should not be read as a signal.

---

## T4 (Fix 4) — the price-level effect, separated from the gate effect

`t4_diagnostic.py` · `artifacts/t4_diagnostic.json`, `t4_diagnostic.parquet` · charts 02, 03

Detection price and decile reused from E1's artifact (F1-T6's D4-compliant tick-derived construction),
never re-derived. **No policy applied on this axis.**

| detection-price decile | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 |
|---|---|---|---|---|---|---|---|---|---|---|
| median detection price | $0.28 | $0.88 | $1.37 | $1.85 | $2.61 | $3.43 | $4.84 | $7.01 | $11.43 | $29.50 |
| n | 160 | 122 | 87 | 113 | 97 | 81 | 67 | 78 | 60 | 38 |
| gross median | −15.6 | 0.0 | 0.0 | −52.9 | −52.5 | −128.6 | −47.4 | −5.9 | **+32.7** | **+32.7** |
| net median, flat | −86.5 | −71.0 | −71.0 | −123.9 | −123.5 | −199.6 | −118.4 | −76.9 | −38.3 | −38.3 |
| **net median, per-share** | **−1,139** | −267 | −204 | −186 | −134 | −209 | −89 | −41 | **+5.3** | **+24.6** |

**The price effect is real, large, and monotone on the per-share axis** — from −1,139 bp at $0.28 to
+24.6 bp at $29.50. Only the top two deciles have a non-negative net per-share median. This is Phase 11's
finding reproduced on the gate's own trade rather than a fixed horizon.

**And it is not what the gate policies are doing.** Detection-price composition:

| | n | median detection price | decile median |
|---|---|---|---|
| A, all | 903 | $1.955 | 3.0 |
| A, post-warmup | 653 | $1.940 | 3.0 |
| B1, post-warmup | 183 | $1.765 | 3.0 |
| B, post-warmup | 180 | $1.753 | 3.0 |

**Every policy sits on the same part of the price axis as the baseline.** So the degradation in §T3 is a
gate effect, not a price-level re-sort. That is exactly what Fix 4 was for, and it comes back clean.

### Collinearity

| population | n | ρ |
|---|---|---|
| all candidate moments | 903 | **0.432** |
| post-warmup | 653 | 0.447 |
| flag clear (A12) | 677 | 0.434 |
| `flag_cross_session_extreme` | 226 | 0.429 |
| contested only | 95 | 0.454 |
| *v0 reference* | *997* | *0.692* |

ρ falls from 0.69 to 0.43 — **but this is mechanical, not a finding.** The gap gate compresses `move_at`
into a narrow band around +30% by construction, and a restricted range lowers a correlation. It is **not**
evidence the score became more independent of the move. The A12 split is flat, so the correlation is not a
cross-session artifact either way.

### The score decile panel — chart 02

The top decile is still the worst median cell: **−390 bp** at decile 9 (mean −87, the only negative mean
on the panel) and −207 bp at decile 7. Deciles 0–1 sit at 0.0. Same shape as v0 and as R0-T0c2's response
curve, now on a third trade definition.

---

## T5 (Fix 3) — true D1 concurrency

`t5_d1_concurrency.py` · `artifacts/t5_d1_concurrency.json`, `t5_d1_candidate_moments.parquet`,
`t5_d1_grid.parquet` · chart 04

The design written as Part I T1 of the R0 brief, which never ran. **A cheap read: 36 s.**

**The candidate moment is a proxy and has to be.** The gate's own first rising edge does not exist for
D1 — R0-T0b established the gate has never been run on 93% of it, and on nothing before 2023-11-17. The
proxy is the programme's own momentum definition: the first minute bar on the event day whose **high**
reaches `prior_close × 1.30`, taken at that bar's `first_trade_ts`. Causal, tick-derived
(`event_minute_bars_v2`; D5 A11 — reuse needs no citation), computable for all of D1.

> **It is an upper bound.** EPG fires on trade-arrival intensity, so it fires *later* than the raw
> crossing. With a fixed liveness window this proxy overstates how early candidates appear and therefore
> overstates concurrency. Every number below is a ceiling on what a full-D1 re-derivation could find.

**Coverage: 15,363 of 15,763 (97.5%).** 400 events have no minute bar reaching +30% of the tick-derived
prior close; carried with `tau_available = FALSE`, never dropped. `momentum_pct` is a vendor RTH-scoped
day's-high measure on an adjusted basis (D4), so it need not agree with a tick recompute.

**Events per session date, as a distribution** — 1,257 dates: p25 6, **median 10**, p75 16, p90 22,
**max 235**. By year the median runs 9 · 6 · 7 · 11 · 18 for 2020–2024, so density roughly triples from
2021 to 2024. v0's "17.35/session" was a mean over the val window; the median across all of D1 is 10, and
the tail is what the old brief predicted — a few frenzy sessions carrying the average.

Crossings cluster at the two opens: 1,755 in the 04:00 hour and 2,386 at 09:00, 2,158 at 10:00.

### Concurrency at candidate moments — the decision-relevant measure

| liveness | median live set | **share with ≥ 2** | p90 | max |
|---|---|---|---|---|
| **9 min** (v0's median window) | **1** | **27.9%** | 3 | 23 |
| 15 min | 1 | 36.3% | 3 | 29 |
| 30 min | **2** | 51.4% | 4 | 45 |
| 60 min | **2** | 67.9% | 6 | 59 |
| no cap (to session close) | 7 | 92.9% | 23 | 235 |
| *v1 gate population, measured* | *1* | *10.5%* | — | *3* |

On the 5-minute grid the same sweep reads 13.4% / 19.1% / 29.0% / 43.2% of *live* grid points carrying ≥2.
The at-candidate-moment figures are higher because crossings cluster, and they are the ones that matter:
a cross-section is only needed when a signal has just fired.

**By year** (grid, ≥2 where any live): 9-min liveness runs 16.9% · 8.6% · 8.6% · 10.7% · 17.4% for
2020–2024; 60-min runs 41.2% · 30.6% · 34.4% · 42.1% · **58.1%**. 2024 is materially denser, and in 2024
at 60-minute liveness the median live set finally reaches 2. The cross-section is regime-dependent, as the
old brief anticipated.

### What Fix 3 settles

At the gate's own window length, **full-D1 would raise the contest rate from 10.5% to 27.9%** — about
2.7× — while leaving the median candidate without a competitor. The cross-section is thin but not absent,
and it thickens with either a longer liveness definition or a 2024-like regime. It does **not** appear at
any liveness the current exit rule implies.

---

## Charts

`results/relative_momentum/v1/charts/` · `charts.py` · standalone Plotly HTML, one per file, Plotly
inline (offline, D14), light theme per E1's precedent.

- **`01_markout_distribution.html`** — ECDF: baseline post-warmup, Policy B post-warmup, and v0's
  in-sample gate 1 on this population, so the causal fix is separable from the population fix. Both cost
  bars drawn.
- **`02_score_decile_panel.html`** — median gross markout with IQR band and mean by score decile.
- **`03_price_decile_panel.html`** — Fix 4: gross, net-flat and net-per-share medians by detection-price
  decile, with n and median price annotated per bucket. No policy applied.
- **`04_d1_concurrency.html`** — Fix 3: share of live grid points with ≥2 candidates across the declared
  liveness sweep, by year, with the measured gate-population value drawn as a reference line.
- **`05_causal_gate1_threshold.html`** — Fix 1: every candidate score in time order with the causal
  threshold tracking through them, the warmup region shaded, and v0's in-sample level drawn for contrast.

---

## What this does and does not establish

**Establishes.** A causally computable level gate, on a population of genuine +30% crossers, still
degrades the median outcome and the win rate — so v0's result was not an artifact of the in-sample
threshold or the broken gap gate, though the in-sample threshold made it worse than it had to be. The
degradation is not a price-level re-sort: every policy sits at the same detection-price decile median as
the baseline. The price-level effect is separately real and large, and on the per-share cost axis it
dominates everything else in this report. No policy's median trade clears cost in either unit. And true
D1 concurrency at the gate's own window length is 27.9% contested, 2.7× this population's 10.5%.

**Does not establish.** Anything about the gate's own rising-edge logic — Facet 1 is reused, not
re-derived, and R0-T0b established it has never run on 93% of D1. The population remains a single 8-month
val slice, n = 903. Gate 1's warmup covers 27.7% of it, so the post-warmup rows rest on 653 candidates
and 180 Policy-B trades. B-contested is n = 25 and carries no weight. The D1 concurrency figure is an
upper bound from a proxy that fires earlier than EPG does. And this tests one attention measure; the
brief kept it to one deliberately.

**Constraints held.** D4 — every measured quantity tick-derived; no spine numeric column enters any
computed quantity, and `momentum_pct` only resolves folder paths. D5 — long-only; no short or fade
variant specified, implemented or measured. Coverage gaps flagged and carried at every step: 94 blocked
events, 30 without a prior close, 400 D1 events without a computable crossing, all carried. `move_at` is
the only move measure in any threshold, score or slice; PF = 1.9194 appears nowhere.

**Reproducibility gap, unchanged from v0:** `B_e` comes from
`results/fundamental_exploration/e2/artifacts/`, still **uncommitted**, so the score is not reproducible
from a clean checkout until those artifacts land.
