# Phase 8 — Event-Study Grid: Forward Markouts from Tradeable Anchors

**Branch:** `phase/8` · **Baseline:** `phase-6b-approved` (`event_minute_bars_v2`, 45,925,350 rows; D1 = 15,763) · **Status:** complete, awaiting Cooper's review
**Amendment A10.1** (Cooper, 2026-08-01) applied: 09:00 anchor retained with a population guard, escalation row 7 raised 10%→15%, `flag_possible_row_cap` added. Config hash in every chart caption.

This is the program's first forward-return measurement. Every quantity derives from `event_minute_bars_v2` — **zero passes over `filtered_trades`/`filtered_quotes`** (escalation row 3 held). All prices are tick-derived last-trade-at/before values; the T1 tick anchor and `day_high_ext` are reused frozen from 6b (D4-clean). No spine numeric on any computation path (row 4 = 0). Markouts are **signed log returns** — sign kept, never absolute-valued. **The agent describes the picture; the read on a forward edge is Cooper's, from charts 04/05/06.**

---

## 1. Precondition table (T0b) — `event_minute_bars_v2` coverage, D1-joined

| offset | rows | distinct events | minute_index range |
|---|---|---|---|
| −3 | 4,846,371 | 15,527 | 0–959 |
| −2 | 5,090,571 | 15,598 | 0–959 |
| −1 | 5,712,058 | 15,729 | 0–959 |
| 0 | 8,519,526 | 15,763 | 0–959 |
| +1 | 8,153,038 | 15,741 | 0–959 |
| +2 | 7,073,605 | 15,744 | 0–959 |
| +3 | 6,530,181 | 15,747 | 0–959 |

Per segment (every offset): premarket `minute_index` 0–329, rth 330–719, post 540–959 (the 540 floor = 13:00 ET on early-close half-days). All seven offsets carry all three segments. Per-event gaps on flanking offsets are genuine absence of trades, not table incompleteness. **Row 2 not triggered.** v2 row-count pin 45,925,350 (match); DDL SHA256 `219bc01a479544b4…`.

## 2. Decomposition table (T1) — `realized(09:30)` into three log-space components

Additive vs the tick anchor `tick_close_t_minus_1_rth`; components sum to `log(p_0930/anchor)`. [chart 01](charts/01_realized_open_decomposition.html)

| component | median share of realized(09:30) | median abs log move | n |
|---|---|---|---|
| `seg_t1_post` (T-1 16:00→20:00) | 0.171 | 0.011 | 12,938 |
| `seg_overnight` (T-1 last → T0 first ext) | 0.017 | 0.001 | 12,938 |
| `seg_t0_pre` (T0 first ext → 09:30) | 0.642 | 0.032 | 12,938 |

`decomp_undefined` = 223 (no T-1 ext bars / missing anchor), own row. `share_undefined` = 2,602 (numerator ≤ 0; enters the absolute-move panel only), own row. Cross-check: recomputed median `realized_at_rth_open` = 0.1775 ≈ 6b's 0.173. The overnight component carries the fattest tails in the absolute panel; the T0-premarket component carries the largest median share.

## 3. Participation table (T3) — per clock anchor

Baseline = median over {T-1,T-2,T-3}. Pre-registered rule: `logrv_session` if `b_clock` zero/undefined for >20% of D1, else `logrv_clock`. Rank-based quintiles (5 balanced buckets, ~3,149 each). [t3_participation.json](artifacts/t3_participation.json)

| anchor | mi | undef-or-zero rate | form selected |
|---|---|---|---|
| 0900 | 300 | 18.7% | `logrv_clock` |
| rth_open | 330 | 1.6% | `logrv_clock` |
| open+5 | 335 | 1.4% | `logrv_clock` |
| open+15 | 345 | 1.1% | `logrv_clock` |
| open+30 | 360 | 0.9% | `logrv_clock` |
| open+60 | 390 | 0.6% | `logrv_clock` |
| open+120 | 450 | 0.4% | `logrv_clock` |
| t0_close | 959 | 0.1% | `logrv_clock` |

`no_baseline` n = 20 (0.13%) — carried, never pooled. **Rows 5, 6 not triggered** (0900 at 18.7% < 20%).

## 4. Flagship markout table (T5) — `rth_open → t0_close`, participation quintile × era

Median signed-log markout (n). rth_open is a neutral session-start reference (not markout-selected). [chart 05](charts/05_markout_distributions_flagship.html), [chart 04](charts/04_markout_heatmap.html)

| quintile | 2020-21 median (n) | 2022-24 median (n) |
|---|---|---|
| Q1 (low participation) | +0.194 (976) | +0.208 (2,040) |
| Q2 | +0.191 (1,228) | +0.197 (1,851) |
| Q3 | +0.160 (1,183) | +0.167 (1,963) |
| Q4 | +0.065 (1,086) | +0.097 (2,060) |
| Q5 (high participation) | −0.100 (827) | −0.041 (2,316) |

Median markout declines monotonically with rising pre-open participation, in both eras; Q5 is negative. The same vertical gradient appears across anchors and at the t0_close/t1_close/t3_close horizons in the heatmap. **Sensitivity (A10.1c-iii):** pooled t0_close median = 0.1409 (clean, n=15,530); without the 8 `flag_possible_row_cap` = 0.1408; without the 7 `flag_has_dup_prints` = 0.1408 (Δ < 0.0002).

## 5. Rung attrition table (T4c) — per rung

Rung = first T0 minute where cumulative volume ≥ mult × `b_session`. [chart 07](charts/07_rung_attrition.html)

| rung | n reaching | % of D1 | median crossing ET |
|---|---|---|---|
| 1× | 14,926 | 94.7% | 10:07 |
| 2× | 13,261 | 84.1% | 10:25 |
| 5× | 10,119 | 64.2% | 10:46 |
| 10× | 7,487 | 47.5% | 10:38 |

~25% of crossings occur in premarket. Rung markout to t0_close by crossing-time bin: premarket crossings show the widest downside spread, later crossings tighter around zero. [chart 06](charts/06_rung_markouts_by_crossing_time.html) **Every rung reported; none selected, recommended, or preferred (row 10).**

## 6. Flagged-population table (T5d) — carried rows, `rth_open → t0_close`

The union (56 events) is excluded from the quintile cells and reported separately here. [t5_markout_summary.json](artifacts/t5_markout_summary.json)

| population | n | note |
|---|---|---|
| `no_baseline` | 20 | no T-1/T-2/T-3 trades in v2 |
| `has_t_minus_1_rth`=FALSE | 36 | no T-1 pre/rth anchor (6b) |
| `denom_nonpositive` | 5 | day_high_ext ≤ anchor (6b) |
| `flag_has_dup_prints` | 7 | exact-duplicate prints (6b) |
| `flag_possible_row_cap` | 8 | T0 count ∈ {50k,100k,200k} |

`anchor_undefined` is carried per-cell (absent rows). Per-population flagship markouts are in the artifact.

## 7. Survivorship table (T6) — missing next sessions, by era

Diagnostic only: no exclusions, no reweighting, no external base rate, no causal or bias-magnitude claim. Trading-session calendar derived from v2's own trade timestamps (1,263 sessions, 2019-12-30…2025-01-06). [chart 08](charts/08_survivorship_census.html)

| | n | missing T+1 | missing T+2 | missing T+3 |
|---|---|---|---|---|
| 2020-21 | 5,371 | 4 (0.07%) | 4 (0.07%) | 6 (0.11%) |
| 2022-24 | 10,392 | 18 (0.17%) | 15 (0.14%) | 10 (0.10%) |
| overall | 15,763 | 22 (0.14%) | 19 (0.12%) | 16 (0.10%) |

Sessions-to-ticker-last-seen: median 236 (most D1 tickers recur — repeat spikers). The event-windowed archive makes last-seen a lower bound, not a delisting date.

## 8. 09:00 anchor block (A10.1a)

The 09:00 clock anchor is `anchor_undefined` for **1,740 events (11.04%)** — no T0 print at/before 09:00 ET. Reported n at 09:00 is **14,023** everywhere (never inherits 15,763); the 1,740 (`has_premarket_print`=FALSE) are dropped from the 09:00 column only and present at every other anchor. Chart 04's 09:00 column carries a dashed border and a header note. **Free comparison (A10.1a-iii), `rth_open → t0_close` by `has_premarket_print`** [chart 09](charts/09_rth_open_by_premarket_print.html):

| group | 2020-21 median (n) | 2022-24 median (n) |
|---|---|---|
| has premarket print | +0.127 (4,500) | +0.137 (9,523) |
| no premarket print | +0.185 (802) | +0.207 (731) |

The no-premarket-print events sit higher and tighter at RTH open — a distinct population, which is why the guard exists.

## 9. Row-cap block (A10.1c) — the 8 `flag_possible_row_cap` events

| ticker | date | momentum_pct | T0 print count |
|---|---|---|---|
| ANY | 2021-09-02 | 80.69 | 200,000 |
| AMIX | 2024-07-19 | 57.04 | 100,000 |
| APLD | 2024-09-05 | 76.23 | 100,000 |
| BBBY | 2022-08-08 | 63.48 | 100,000 |
| ARBB | 2023-12-26 | 377.89 | 100,000 |
| APRE | 2021-06-16 | 60.82 | 100,000 |
| ARBB | 2024-02-13 | 195.45 | 50,000 |
| BCAB | 2022-08-10 | 104.16 | 50,000 |

ARBB lands on exactly 100,000 and exactly 50,000 on two different events. Flagship with/without sensitivity: Δ < 0.0002 (§4). Root cause requires reading `filtered/` parquet — **out of scope**, registered as a remediation open item; `flag_possible_row_cap` is homed in the phase-8 artifact (like `flag_has_dup_prints`), not `canonical.py` (Cooper, 2026-08-01).

## 10. ETH-dominant decay split (T2a)

[chart 02](charts/02_decay_by_eth_flag.html) — ETH-dominant (n=734) median realized fraction peaks ~0.47 in premarket and falls to ~0.25 at RTH open, **never crossing 0.5**; not-ETH-dominant (n=14,988) crosses 0.5 at **495 min** (~12:15 ET; pooled-all 6b ref 516). Chart split only — `flag_eth_dominant_t0` is never a markout bucket.

---

## 11. Escalation check table

| # | condition | threshold | observed | result |
|---|---|---|---|---|
| 1 | tag `phase-6b-approved` absent | any | present, master at 295a0e1 | pass |
| 2 | v2 missing offset / incomplete coverage | any | 7 offsets × 3 segments, 0–959 | pass |
| 3 | full pass over filtered_trades/quotes | any | 0 | pass |
| 4 | D4 spine numeric on computation path | >0 | 0 | pass |
| 5 | `no_baseline` share | >5% | 0.13% | pass |
| 6 | same-clock baseline undefined | >20% | 18.7% (0900) | not triggered |
| 7 | clock `anchor_undefined` (amended) | **>15%** | 11.04% (0900) | pass (was hard stop at 10%) |
| 8 | markout cell n | <100 | thin cells hatched, no claim | handled |
| 9 | write outside sanctioned dirs | any | none (results/reports/ copy flagged) | pass |
| 10 | rung/anchor selected on markouts | any | none | pass |
| 11 | bucketing var not anchor-knowable | any | none | pass |
| 12 | `has_premarket_print`≠1740 or row_cap≠8 | any | 1740 & 8 | pass |

## 12. Verification block

| metric | value | n | source | reproduce |
|---|---|---|---|---|
| v2 row-count pin | 45,925,350 | — | t0_preconditions.json | `python -m research.phase_8.t0_preconditions` |
| realized-open shares | pre 0.642 / post 0.171 / o/n 0.017 | 12,938 | t1_decomposition.json | `python -m research.phase_8.t1_decomposition` |
| ETH decay 0.5 crossing | never / 495 | 734 / 14,988 | t2_eth_split.json | `python -m research.phase_8.t2a_eth_split` |
| round-number hits | 50k=2,100k=5,200k=1 | 15,763 | t2_row_cap_scan.json | `python -m research.phase_8.t2b_row_cap` |
| no_baseline | 20 (0.13%) | 15,763 | t3_participation.json | `python -m research.phase_8.t3_participation` |
| 0900 anchor_undefined | 1,740 (11.04%) | 15,763 | t4_anchors_summary.json | `python -m research.phase_8.t4_anchors` |
| label backfill | 1,740 / 8 | 15,763 | a101_label_backfill.json | `python -m research.phase_8.a101_backfill` |
| flagship Q1→Q5 (22-24) | +0.208 → −0.041 | 2,040→2,316 | t5_markout_summary.json | `python -m research.phase_8.t5_markout_grid` |
| survivorship missing T+1 | 22 (0.14%) | 15,763 | t6_survivorship.json | `python -m research.phase_8.t6_survivorship` |

## 13. Output files

| file | status |
|---|---|
| `config/phase_8.json`, `prompts/phase_8.md`, `prompts/phase_8_amendment_10.md` | ✓ |
| `results/phase_8/artifacts/t0_preconditions.json` … `t6_survivorship.json` (+ `a101_label_backfill.json`) | ✓ |
| `results/phase_8/artifacts/*.parquet` (t4_anchors, t5_markout_grid, intermediates) | ✓ gitignored, regenerable |
| `results/phase_8/charts/01–09*.html` (+ .png) | ✓ kaleido-verified |
| `results/phase_8/{digest.json, REPORT.md}` | ✓ |
| `results/reports/phase_8_report.md` (cross-phase copy) | ⚠ pending — blocked by escalation row 9; flagged for Cooper |

## 14. Amendment note

Escalation row 7 fired at **11.04%** on the 09:00 anchor (T4) and the phase hard-stopped without a fix. Cooper approved Amendment A10.1: 09:00 retained with the population guard (own n=14,023; `has_premarket_print` label; free `rth_open` comparison; chart 04 marking), row 7 raised **10% → 15%**, `flag_possible_row_cap` added to the carried-flag set. Both conditions of the raise (A10.1a-i explicit denominator, A10.1a-iv chart marking) implemented.

## Commits

T0 preconditions · T1 decomposition · T2 ETH-split + row-cap · T3 participation · T4 (hard stop) · A10.1-T0 amendment · A10.1-T1 backfill · A10.1-T2 rung attrition · A10.1-T3 markout grid · A10.1-T4 survivorship · A10.1-T5 digest/report.

**No recommendations. No characterisation of any result as good, promising, weak, or disappointing.** The read on a forward edge is Cooper's, from charts 04, 05, and 06.
