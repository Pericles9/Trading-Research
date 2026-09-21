# Relative momentum v2 — absolute floor, then cross-sectional rank — REPORT

**Branch:** `explore/relative-momentum-v2` · **Config hash:** `50046a0f582a`
**Status: STOPPED AT THE T1b CALIBRATION GATE.** T1, T1b and T3 ran. T2 (policies), T4
(diagnostics) and T5 (charts) did not.
Brief: `prompts/relative_momentum_v2.md` · plan: Correction 1 (2026-09-21) incorporated in full.

## The stop, up front

> **Gate 6 (power) FAILED on the price-filter-on arm.** At the reference rung, `F+R contested` projects
> to **9 trades** against the declared readable floor of **20**. The price-filter-off arm projects 47 and
> is readable. Per the approved plan — *"Post the table. Stop if the F+R contested cell is too small to
> read"* — v2 stops here rather than spending the evaluation pass and discovering it afterwards.

Gates 5b and 5c both **passed**, and two results came out of the stop that change what v2 is for. Both
are below: the floor's rungs are genuinely in the left tail this time, but **the pathology the floor was
built to catch is nearly absent from this population** (4 of 47 contested winners), and **T3 refutes the
illiquidity-filter explanation of v0's damage outright**.

---

## What ran

| task | status | output |
|---|---|---|
| T1 — measure floor quantities, all 903 | complete | `t1_measure.json`, `t1_measured.parquet` |
| T1b — calibration gate (5b / 5c / 6) | complete, **gate 6 fired** | `t1b_calibration.json`, `t1b_projection.parquet`, `t1b_enriched.parquet` |
| T3 — settle v0's gate-1 mechanism | complete (independent of the stop) | `t3_v0_mechanism.json`, `t3_v0_mechanism.parquet` |
| T2 — floor + five policies | **not run** | — |
| T4 — diagnostics, price decile | **not run** | — |
| T5 — charts | **not run** | — |

T3 was run despite the stop because it touches neither the floor nor the policy table — it is one query
on `results/relative_momentum/v0/artifacts/t4_diagnostic.parquet` — and the question it settles is a
standing one.

**Population: 903 of 15,763 D1 events = 5.7%**, val split 2023-11-17 → 2024-07-22. Not a measurement over
D1. Reused from v1-T0, not rebuilt: the tick-exact gap-gate reconstruction including queued entries and
the runner's next-tick fill, validated 6/6 against the run's own recorded `entry_price`.

**T2 of the brief (true D1 candidate density) is satisfied by v1-T5 and is not recomputed.** Headline:
coverage 15,363/15,763 (97.5%); **27.9% of candidate moments carry a second live name at 9-minute
liveness** (the gate's own median window) against 10.5% measured on this gate population; 51.4% at 30 min,
67.9% at 60 min; the +30%-crossing proxy fires earlier than an EPG rising edge so every figure is an upper
bound.

---

## A defect found and fixed on the way in

`entry_ts` in v1's artifact is **float64**. At 1.7e18 the float64 grid spacing is 256 ns, so every stored
τ was rounded by up to ~128 ns. τ *is* a tick timestamp by construction (v1 set it to `ts[i]`), so
`common.snap_tau_to_tick` snaps it back to its nearest real tick and asserts the snap is under 10 µs —
which is what makes it a precision recovery rather than a shift.

Observed: 903 snapped, 866 non-zero, **max |snap| = 128 ns** — exactly half the grid spacing, the
signature of pure rounding.

It mattered for two candidates. **BENF 2024-07-05** and **JL 2024-01-29** were rounded *upward past their
own trigger print* by 115 ns and 58 ns; their previous print was 601 s and 4,639 s earlier, so the
`ts <= τ` window measured **completely empty** and the floor would have rejected them for a
floating-point reason. Before the fix `print_count` had p0 = 0; after, p0 = 1. **v1's own score window
carries the same two zero-volume windows** — a 2-of-903 effect on v1's ranker, recorded here.

---

## T1 — the floor quantities on all 903

`t1_measure.py` · 49 s · Correction 1 §5b: measured on the full population, not the 90-row sample whose
p5/p95 rested on ~4 observations.

| quantity | p1 | p5 | p25 | **p50** | p75 | p95 | p100 |
|---|---|---|---|---|---|---|---|
| print count | 27 | 91 | 418 | **1,599** | 4,608 | 10,871 | 77,763 |
| notional USD | 11,839 | 37,308 | 194,225 | **618,818** | 1,778,572 | 7,897,088 | 348,826,800 |
| venues | 2 | 3 | 6 | **10** | 13 | 15 | 16 |
| NBBO updates | 24 | 56 | 251 | **858** | 2,353 | 5,967 | 33,255 |
| spread bp | 0 | 30 | 76 | **121** | 192 | 473 | 7,027 |
| spread ¢ | 0 | 0.08 | 1.00 | **2.00** | 6.50 | 30.00 | 6,500 |
| depth USD (both sides) | 326 | 661 | 1,492 | **2,530** | 3,946 | 10,833 | 50,370 |
| last price | $0.077 | $0.190 | $0.958 | **$2.15** | $4.87 | $15.64 | $227.00 |

D17 applied to quote rows (crossed / null / one-sided / zero-size excluded, **locked carried**):
**1.38%** of raw quote rows excluded. Depth unavailable for **2** of 903 — those are not rejected on
`no_depth`; the pseudocode's `DEPTH_AVAILABLE` guard applies and the flag is carried.

**The build-time ASSERT is a live test, not a comment.** `assert_floor_inputs_absolute` is called with
the floor's projection and then deliberately called again with a `score` column added; the second call is
required to raise. It does. Relative volume, `B_e` and every percentile are structurally unable to reach
the floor.

---

## T1b — the calibration gate

### Gate 5b — rung positions on the full 903: **PASS**

| constant | reference | rejects | verdict |
|---|---|---|---|
| `MIN_PRINTS` | 50 prints | **2.55%** | pass |
| `MIN_NOTIONAL_USD` | $25,000 (S = $1,250) | **2.99%** | pass |
| `MIN_VENUES` | 2 venues | **0.89%** | pass |
| `MIN_QUOTES` | 25 messages | **1.44%** | pass |
| `MAX_SPREAD_BP` | 1,000 bp | **0.78%** | pass |
| `MIN_DEPTH_USD` | $100 | **0.11%** | pass |
| — `MIN_PRICE_USD` *(separate filter, not in the AND)* | $2.512 (X = 100) | **54.37%** | — |

All six floor rungs sit at or below **p3**. Correction 1's repositioning worked: my first draft's rungs
sat at ~p25 of an already-activity-filtered population, which is a second selection gate — the exact
mechanism that damaged v0 and v1. And the price filter's 54% rejection confirms it had to come out of the
AND: left inside, it would have masked every other condition.

### Gate 5c — is the pathology in the sample? **PASS, but barely**

The floor exists to catch one thing: the **dead-tape winner** — a name with no absolute attention that
holds all the relative attention because nothing else is trading. Low activity is defined as
`print_count ≤ p10` (133 prints in 10 minutes), n = 91.

| | |
|---|---|
| low-activity candidates | **91** |
| — by segment | **regular_hours 67**, pre_market 23, post_market 1 |
| rank winners under rank-only (no floor) | 855 |
| **contested** rank winners under rank-only | **47** |
| of which low-activity | **4** (8.5%) |
| median score, low-activity | **14.2** |
| median score, the rest | **36.0** |

**The pathology exists but it is 4 events.** And the direction is the opposite of the architecture's
premise: low-activity candidates score *lower* on the ratio (median 14.2 vs 36.0), and their score-decile
distribution is skewed **down** — 9/11/11/19/14/13/7/3/3/1 across deciles 0→9. On this population a thin
tape does not generally buy you a high relative-volume score.

**This falsifies my own recorded prediction #3.** I predicted the binding condition would catch
**premarket** dead tape. The low-activity cases are **regular_hours 67 to premarket 23** — RTH dead tape,
not premarket. Predictions #1 and #2 held (see below).

### Gate 6 — power projection: **FAIL on the price-on arm**

| arm | floor survivors | survivor share | F+R | **F+R contested** | NO_TRADE moments | readable (≥20) |
|---|---|---|---|---|---|---|
| price filter **off** | 854 | 94.6% | 810 | **47** | 49 | **yes** |
| price filter **on** | 390 | 43.2% | 383 | **9** | 513 | **no** |

Across all 13 configurations the price-off arm holds 43–47 contested and the price-on arm holds 7–10 —
with one exception: `MAX_PER_SHARE_COST_BP = 200` (the loosest price rung, `MIN_PRICE` = $1.256) reaches
**20** contested, exactly at the floor.

**Fail-reason histogram at the reference rung** (counts of the 903; a candidate can fail more than one):

| condition | n | by segment |
|---|---|---|
| `thin_notional` | **27** | RTH 18, pre 9 |
| `too_few_prints` | **23** | RTH 18, pre 4, post 1 |
| `dead_book` | 13 | pre 6, RTH 6, post 1 |
| `single_venue` | 8 | RTH 7, pre 1 |
| `spread_too_wide` | 7 | pre 4, RTH 2, post 1 |
| `no_depth` | 1 | pre 1 |

### Predictions, checked

| # | prediction | outcome |
|---|---|---|
| 1 | the floor rejects a **small minority** | **HELD** — 5.4% rejected (854 of 903 survive) |
| 2 | `single_venue` rejects **almost nobody** | **HELD** — 0.89% |
| 3 | the binding condition catches **premarket** dead tape | **FAILED on the segment.** `thin_notional` and `too_few_prints` are indeed the binding pair, but the cases are RTH 18 / pre 4–9, not premarket |
| 4 | if the floor still rejects a large share, the rungs are too high | n/a — it rejects 5.4% |

---

## T3 — v0's gate-1 mechanism, settled

`t3_v0_mechanism.py` · one query on v0's committed artifact, no new data pass. v0's own candidates and its
own in-sample 75th-percentile gate: **250 pass / 749 fail** (of 999 scorable).

| quantity | pass median | fail median | **pass ÷ fail** | Mann–Whitney p |
|---|---|---|---|---|
| notional USD, 10-min window | 1,331,636 | 129,543 | **10.28×** | 8.7e-53 |
| print count, 10-min window | 4,195 | 281 | **14.93×** | 1.2e-60 |
| entry price | $1.90 | $1.91 | **0.995×** | **0.73 — not significant** |
| `move_at` at decision time | 0.519 | 0.142 | **3.65×** | 8.9e-63 |
| score (relative volume) | 674.3 | 3.99 | 169× | 3.5e-124 |
| `B_e` (the denominator) | 1,440 | 23,905 | **0.060× (16.6× smaller)** | 6.7e-75 |

**The illiquidity-filter explanation is refuted.** v0's passes were not thinner — they carried **10.3× the
notional** and **14.9× the print count** of the fails. They were not cheaper either: entry price is
statistically indistinguishable (ratio 0.995, p = 0.73).

**The deep-into-the-move explanation is confirmed**, and the `B_e` row explains the mechanism. The 169×
score ratio decomposes as ~10.3× more notional **times** a ~16.6× smaller baseline. v0's gate selected
**names that are normally quiet and are now genuinely loud** — which is exactly what relative volume is
designed to find. It worked as designed.

> **The consequence is uncomfortable and worth stating plainly: v0's gate-1 was not a broken attention
> detector. It was a working attention detector aimed at a population where attention arrives late.** Its
> passes sit 3.65× deeper into the move, and v0, v1 and R0-T0c2 independently found — on three different
> trade definitions — that more move already achieved predicts a worse forward outcome. An absolute floor
> does not address that; it addresses a different failure mode, which gate 5c just showed is 4 events here.

---

## What the stop leaves open — Cooper's call

Mechanical consequences, not recommendations.

**The price-on arm cannot be evaluated at the reference rung.** 9 contested trades will not distinguish
F+R from R. Three shapes are available, and none is mine to choose: run price-off only and report the
price filter purely as a diagnostic; adopt `MAX_PER_SHARE_COST_BP = 200` as the reference so the price-on
arm reaches 20; or accept the price-on arm as underpowered and read it as such.

**The floor's target population is 4 events.** Gate 5c passed on its letter — the pathology exists and
rank-only does crown low-activity winners — but `R vs F+R`, which the brief calls "the test of the whole
thesis of this version," would be decided by 4 of 47 contested moments even on the readable arm. That is
a fact about this population, not about the architecture.

**T3 points somewhere else entirely.** If the damage is late entry rather than dead tape, the lever is the
entry timing or the exit, not the qualification layer. v1-T5 already showed full-D1 concurrency at the
gate's own window length is 27.9% contested — thin, regime-dependent, not absent.

Nothing here closes the architecture. The floor is built, asserted, calibrated into the left tail, and
ready to run the moment the power question is resolved.

---

## Constraints held

`move_at` is the only move measure — `momentum_pct` appears in no threshold, score or slice, and resolves
only folder paths. D4: every quantity tick-derived; no spine numeric column enters any computed quantity.
D5: long-only, no short or fade variant specified, implemented or measured. D17: quote exclusions as
written, locked carried. D19: spread reported in bp **and** cents. Coverage flagged and carried at every
step — 2 depth-unavailable, 1.38% of quote rows excluded, 400 D1 events without a computable crossing in
the reused concurrency read.

**Spread and price are partly the same gate, as the plan required stating.** Spread in bp is
price-normalised over a $0.077–$227 population. Above $1.00 the minimum increment is a penny (Rule 612),
so a $2.15 name cannot quote tighter than ~47 bp, while a $0.19 name quotes on the $0.0001 sub-penny grid
and can show single-digit bp. The bp distribution is mechanically driven by price at the low end — which
is why the p1 spread reads 0 bp and why cents are reported alongside.

**Reproducibility gap, unchanged:** `B_e` is from `results/fundamental_exploration/e2/artifacts/`, still
uncommitted. **The floor does not depend on it** — only the ranker does, which is the architecture working
as intended.
