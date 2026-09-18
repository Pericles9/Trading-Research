# Relative momentum v0 — build & evaluate — REPORT

**Branch:** `explore/relative-momentum-v0` · **Config hash:** `c90d8126dd12`
**Status: complete.** T0–T4 ran, four charts, both policies evaluated.
Brief: `prompts/relative_momentum_v0.md`.

**Headline: the qualification layer selects worse trades than taking every signal.** On the
like-for-like base, Policy A's median gross markout is 0 bp and Policy B's is −218 bp; Policy B's
gross win rate is 40.6% against A's 49.6%. It is the level gate doing it, not the cross-sectional one,
and the mechanism is visible in the score decile panel: the top two score deciles — exactly what the
75th-percentile gate selects — carry the worst median outcomes in the population.

**Second finding, which bounds the first: the cross-sectional half barely ran.** 79.5% of candidate
moments had no competitor live at all, so gate 2 passed 892 of 999 candidates and 794 of those passes
were uncontested. Only 42 of Policy B's 244 trades came from a moment where the cross-sectional gate
decided anything. That is a property of this population, not of the universe — see §T4.

---

## What was built, and on what

**Facet 1 — the gate, reused as-is.** The brief allowed either re-running the gate causally against all
of D1 or using the existing fired population. **The existing population was used.** Re-running is not a
small lift: it means executing or re-implementing `epg_replay.py`'s online Hawkes refit over ~15,763
events, and `scanner-epg-momentum` is read-only here. Nothing in that repository was executed, imported
or modified; its committed per-trade record was read.

Source: `scanner-epg-momentum/backtest/results/phase_f/val_full/per_trade.parquet`.

**Facet 2 — qualification, built fresh.** Score, gates, concurrency, policies and diagnostics are all
new code in `research/relative_momentum_v0/`.

---

## T0 — population and coverage

`t0_population.py` · `artifacts/t0_population.json`, `t0_candidates.parquet`

| step | n |
|---|---|
| gate first-window trades, one per event | **1,027** |
| of which in D1 | **999** (28 outside — R0-T0b resolved them: warrants, preferreds, fund products, and in-scope-class events carrying `flag_trades_mom_outlier`) |
| with a tick-derived prior close, so `move_at` is defined | 997 |
| with E2's baseline `B_e`, so the score is defined | 999 |
| with a resolvable `filtered/` folder, so the tick window is readable | 1,027 |
| **scorable** (in D1 + baseline + folder) | **999** |
| **evaluable** (scorable + prior close) | **997** |

`entry_type == 'first'` marks the first entry of *each* pass window, so an event carries several
(4,622 across 1,027 events). The brief's "first window only" is the earliest per event.

> **Coverage, stated plainly as the brief requires: this build runs on 997 of 15,763 D1 events —
> 6.32%.** It is not a measurement over D1. The population is the val-split slice the gate was actually
> run on: **2023-11-17 to 2024-07-22, 168 session dates**, 6.11 candidates per date.

**Three population facts that change what the numbers mean.**

- **The gap gate was off.** `gap_gate_enabled: false` on all 1,027 events, `blocked_by_gap: 0`. The
  ≥30% entry condition was **not enforced** on these trades. The run's own
  `intraday_pct_at_entry` has median **+11.25%** and p25 **−23.42%**. These are EPG rising edges, not
  "+30% crossers at entry".
- **The exit mix.** The brief specifies window-close exit; `natural_exit_*` is that exit and is primary
  here. On the first window it is `epg_window_close` for **860** of 1,027, `luld_upper` 119,
  `luld_lower` 48. Carried, not dropped. The exit actually realized in the Phase F run (which had
  EXIT_D active) is reported alongside as the secondary table.
- **The hold is not 52 seconds.** That figure is the median across all 6,004 trades in the run. On the
  first window with a window-close exit the median hold is **540 s** (9 minutes), p25 275 s, p75 1,056 s.
  This matters for the cost choice below.

---

## T1 — attention score v0

`t1_score.py` · `artifacts/t1_score.json`, `t1_scored.parquet`

> score = (dollar volume of all prints in `[τ − 600s, τ]`) / `B_e`

τ is the candidate's own first rising-edge entry. **Causality is asserted in code**, not assumed:
`common.window_dollar_volume` raises if any print with `sip_timestamp > τ` reaches a returned quantity.

Volume is read from each event's own `filtered/` `trades.parquet` rather than through `filtered_trades`.
A targeted 10-minute range query against that 4.9B-row table does not prune — measured at **9.5 s for a
single window**, which is ~2.7 hours for this population. The folder pass took **66 s** for all 1,027.

**`B_e` reused unchanged**, and its definition checked rather than assumed: `total_baseline_dollar_volume
/ B_e` takes exactly three values across the population — **39, 78, 117** — which is
`n_baseline_sessions × 39` ten-minute blocks in a 6.5-hour RTH session. `B_e` is therefore mean dollar
volume per 10-minute **RTH** block over the available prior sessions. 990 of 999 have all three sessions.

| score quantile | value |
|---|---|
| p5 | 0.066 |
| p25 | 1.28 |
| **p50** | **13.41** |
| p75 | 138.39 |
| p95 | 2,028 |
| max | 199,492 |

Five orders of magnitude. No window was empty — 0 zero-volume windows, so no measured zero had to be
distinguished from an unavailable score here, though the code keeps them separate.

**A scale mismatch, carried as a facet rather than corrected.** `B_e` is RTH-scoped, and **644 of 999
candidate moments are pre-market** (352 regular hours, 3 post). For those the ratio compares an
extended-hours window against a regular-session baseline. This inflates or deflates the *level* and so
bears on gate 1; it largely does not bear on gate 2, because all candidates live at the same instant
share the same session bucket.

---

## T2 — the two gates

`t2_gates.py` · `artifacts/t2_gates.json`, `t2_gated.parquet`

**Gate 1 — level.** Threshold = 75th percentile of the score = **138.39**. Passes **250** of 999
(25.0%). It passes exactly a quarter by construction: the percentile is computed on this same
population, so the level is in-sample. It is a declared v0 default, not a fitted threshold, but it is
not an out-of-sample level either. Stated, not hidden.

**Gate 2 — cross-section.** Passes **892** of 999 (89.3%). Of those, **794 are uncontested** — the
candidate was alone in its live set — and only **98** won a contest.

### The concurrency distribution — chart 03

| candidates live at that moment | 1 | 2 | 3 | 4 | 5 |
|---|---|---|---|---|---|
| candidate moments | **794** | 174 | 29 | 1 | 1 |

**Median live-set size is 1. 79.5% of candidate moments have no competitor at all.** Gate 2 has nothing
to decide on four moments in five.

Where a contest did happen (205 moments), it was rarely close: the ratio of the live set's top score to
its runner-up has median **28.2×**, p25 4.1×. When two names are live, one is usually loud and the other
is not.

**Policy B is 244 trades**, 23.8% of Policy A. **202 of them come from uncontested moments** and only
**42** from contested ones.

---

## T3 — Policy A against Policy B

`t3_evaluate.py` · `artifacts/t3_evaluate.json`, `t3_evaluated.parquet` · chart 01

`pnl_pct` as recorded is **gross** — it equals `(exit_price/entry_price − 1) × 100` to 2.8e-14, and
`config/strategy.json` carries `epg`, `hawkes`, `exit_d`, `luld` and `gap_gate` blocks and **no fee
block**. The brief offered a choice between Phase 11's figure and the gate's native cost model; **the
gate has no native cost model, so there is no choice to make** and Phase 11's is applied, in both units
per D19.

The per-share leg is the harsher bar and it is not close: entry prices here have median **$1.94** and p5
**$0.16**, so 2.512 cents is a round trip of **129.5 bp at the median**, p75 303 bp, p95 1,528 bp.

### Primary — window-close exit, all figures in basis points

| policy | n | **gross median** | gross mean | net median, flat cost | net median, per-share cost | **win rate gross** | win net flat | win net per-share |
|---|---|---|---|---|---|---|---|---|
| A · all first-window signals | 1,027 | **0.0** | +211.0 | −71.0 | −178.3 | **49.85%** | 42.94% | 34.57% |
| **A · scorable base (like-for-like)** | **999** | **0.0** | +194.0 | −71.0 | −185.1 | **49.55%** | 42.54% | 34.03% |
| B1 · gate 1 only (level) | 250 | **−231.3** | +207.1 | −302.2 | −394.5 | 40.40% | 38.00% | 36.00% |
| B2 · gate 2 only (cross-section) | 892 | **0.0** | +195.9 | −71.0 | −186.9 | 49.33% | 42.60% | 34.08% |
| **B · EPG+Qual, both gates** | **244** | **−217.5** | +213.6 | −288.5 | −394.5 | **40.57%** | 38.11% | 36.07% |
| B-contested · gate 2 actually decided | 42 | −162.2 | **−12.9** | −233.2 | −286.7 | 45.24% | 40.48% | 40.48% |

### The full distribution, as the brief asks — gross bp, window-close exit

| policy | p1 | p5 | p10 | p25 | p50 | p75 | p90 | p95 | p99 |
|---|---|---|---|---|---|---|---|---|---|
| A · all | −2,535 | −1,292 | −912 | −329 | 0 | 431 | 1,174 | 2,460 | 5,524 |
| A · scorable | −2,559 | −1,299 | −914 | −342 | 0 | 411 | 1,163 | 2,379 | 5,396 |
| B1 · gate 1 | −3,484 | −2,171 | −1,465 | −853 | −231 | 730 | 2,161 | 4,051 | 8,808 |
| B2 · gate 2 | −2,712 | −1,321 | −918 | −357 | 0 | 402 | 1,160 | 2,384 | 5,580 |
| **B · both gates** | −3,501 | −2,188 | −1,478 | −852 | −218 | 704 | 2,222 | 4,255 | 8,855 |
| B-contested | −4,376 | −2,416 | −2,089 | −1,080 | −162 | 735 | 2,067 | 4,469 | 5,151 |

**Mean and median disagree in sign, and both are reported.** The distribution is heavily right-skewed:
Policy A's median is 0 bp while its mean is +211 bp, carried by a p99 of +5,524 bp. Qualification
*widens* the distribution in both directions — B's p1 is −3,501 against A's −2,559, and its p99 is
+8,855 against +5,396 — leaving the mean essentially unchanged (+214 vs +194) while the median falls by
218 bp and the win rate falls 9 points. A mean-or-profit-factor read of these same trades would call
Policy B neutral; a median-or-win-rate read calls it clearly worse. **Only 4.5% of trades are exactly
zero, so the 0 bp median is a real centre, not a degenerate mass.**

The one cell where the cross-sectional gate actually decided something, B-contested, is the **only cell
in the table with a negative mean** (−12.9 bp). n = 42, above the display floor of 20 but small, and
read as such.

### Secondary — realized exit as run in Phase F

| policy | n | gross median | net median flat | win rate gross |
|---|---|---|---|---|
| A · all | 1,027 | 0.0 | −71.0 | 48.00% |
| A · scorable | 999 | 0.0 | −71.0 | 47.65% |
| B · both gates | 244 | −95.3 | −166.3 | 40.16% |

Same direction, smaller gap. Nothing here depends on which exit is used.

**Under no policy, on either exit, in either cost unit, does the median trade clear cost.** The best
median net figure anywhere in this report is −71.0 bp.

---

## T4 — diagnostic panel (gates nothing)

`t4_diagnostic.py` · `artifacts/t4_diagnostic.json`, `t4_diagnostic.parquet` · charts 02, 04

### Collinearity: the score largely restates the move

Spearman between the attention score and `move_at` at each candidate moment:

| population | n | ρ |
|---|---|---|
| all candidate moments | 997 | **0.692** |
| flag clear (A12) | 758 | 0.687 |
| `flag_cross_session_extreme` (A12) | 239 | 0.697 |
| pre-market | 642 | 0.720 |
| regular hours | 352 | 0.732 |
| contested moments only | 204 | 0.663 |

ρ is the diagnostic, not the verdict — chart 04 carries the scatter. The A12 split is flat (0.687 vs
0.697), so the collinearity is **not** a cross-session-basis artifact. At ρ ≈ 0.69 the score is
substantially a restatement of how far the name has already moved, which is what the brief wanted
answered in the same pass.

### The mechanism — chart 02

| score decile | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 |
|---|---|---|---|---|---|---|---|---|---|---|
| `move_at` median | −0.005 | 0.072 | 0.112 | 0.109 | 0.158 | 0.219 | 0.274 | 0.359 | 0.483 | 0.759 |
| **gross median bp** | 0.0 | +10.6 | 0.0 | +80.7 | +85.4 | +59.5 | +6.1 | 0.0 | **−200.5** | **−388.0** |
| gross mean bp | −1.6 | +123.0 | +85.3 | +171.0 | +108.0 | +418.1 | +257.5 | +468.7 | +375.9 | **−60.4** |

`move_at` rises monotonically with score decile — the collinearity again, as a picture. The median
outcome rises to a plateau around deciles 3–5 and then **falls hard through the top two deciles, which
is exactly the region gate 1 selects.** Decile 9 is the only decile with a negative mean as well.

This reproduces R0-T0c2's response curve on a completely different trade definition — that was Phase
11's fixed-horizon trade (anchor + 5 min, 30 min hold), this is the gate's rising-edge/window-close
trade with a 540 s median hold. Two different instruments, same direction: **more move already achieved
at decision time predicts a worse forward outcome.**

### Two things that bound what the evaluation covers

**(a) The gate's own move measure is not the tick-derived one.** Spearman between the run's
`intraday_pct_at_entry` and `move_at` is only **0.314**. 21.5% of entries have gate-measured ≥30%
against 38.7% tick-measured. The gate resolves its previous close from a three-source chain — DuckDB
`daily_bars`, a daily parquet, or the last trade of the prior event-day folder — and only the third is
tick-derived. Where the two disagree, the gate's "30%" is not the 30% a D4-compliant measure would
have applied. (It blocked nothing in this run regardless: the gap gate was off.)

**(b) The concurrency result is a lower bound, not a universe property.**

| | n | session dates | per date |
|---|---|---|---|
| candidates (this build) | 1,027 | 168 | **6.11** |
| D1 over the same dates | 2,914 | 168 | **17.35** |

**Density ratio 2.84×.** The gate ran on the `mom ≥ 50` slice; D1 over the same dates is 2.84× denser
per session. If the gate ran on every D1 event, per-date candidate density would rise by roughly that
factor and live-set sizes with it. **Gate 2's near-inertness here is a property of this population, not
a measured property of the universe** — and correspondingly, nothing here shows a cross-section would
still be absent at full density.

---

## Charts

`results/relative_momentum/v0/charts/` · `research/relative_momentum_v0/charts.py` · standalone Plotly
HTML, one chart per file, Plotly inline (never a CDN — the environment is offline, D14), light theme
per E1's precedent.

- **`01_markout_distribution_A_vs_B.html`.** ECDF of gross markout for A, B and B-contested, so each
  policy's median is where its curve crosses y = 0.5 and the full shape including both tails is on the
  page. Both cost bars drawn as vertical lines, so "clears cost" is read off the picture. Nothing
  clipped.
- **`02_score_decile_panel.html`.** Median gross markout with its IQR band against score decile, n on
  every bucket, mean plotted separately because mean and median disagree in sign. The region gate 1
  selects is shaded.
- **`03_concurrency_distribution.html`.** Counts of live-set size at each candidate moment, with the
  n = 1 column marked as the region where gate 2 decides nothing.
- **`04_score_vs_move_at.html`.** Score against `move_at`, both log axes, contested moments marked
  separately, ρ annotated beside the scatter rather than in place of it.

---

## What this does and does not establish

**Establishes, on this population:** the attention score as specified restates the move at ρ ≈ 0.69;
selecting on its top quartile picks the worst median outcomes in the population; Policy B is worse than
Policy A on median, win rate and both net-of-cost medians, and no policy's median trade clears cost in
either cost unit. The mean tells a different story from the median and both are on the table.

**Does not establish:** anything about D1. This is 6.32% of it, one 8-month val slice, with the gap
gate off and entries that are mostly not +30% crossers at the moment of entry. It does not establish
that a cross-section is absent at full density — at 2.84× the candidate density the live-set
distribution would be materially different, and that is unmeasured. It does not test any other
attention measure; v0 is relative volume alone, by instruction. And gate 1's level is in-sample by
construction.

**Constraints held throughout.** D4 — every measured quantity is tick-derived; no spine numeric column
enters any computed quantity, and `momentum_pct` is used only to resolve a folder path. D5 — long-only;
no short or fade variant was specified, implemented or measured. Coverage gaps are flagged and carried
at every step, never dropped. `move_at` is the only move measure used anywhere, per the brief's first
non-negotiable; PF = 1.9194 appears nowhere in this build, per the second.

**One dependency worth recording:** `B_e` comes from
`results/fundamental_exploration/e2/artifacts/e2_t2a_baseline.parquet`, which is **uncommitted** on
`explore/fundamental-e1` and remains uncommitted. This build reads it and does not modify it, but the
score is not reproducible from a clean checkout until E2's artifacts are committed.
