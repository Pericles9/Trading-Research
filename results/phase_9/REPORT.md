# Phase 9 — Path Shape, Cross-Session Integrity, and Clustered Inference

**Date:** 2026-08-03
**Branch:** `phase/9`, base `6dd52cf` · **Config hash:** `ba858a71171a`
**Baseline:** `phase-8-approved` (`2b0d623`) · `event_minute_bars_v2` 45,925,350 rows · D1 = 15,763 · detection universe = 15,369
**Status:** complete, no escalation triggered

> **Horizon ceiling.** `event_minute_bars_v2` carries session offsets −3…+3 only. **T+3 is the hard ceiling** and nothing in this report extrapolates past it. Every retracement figure below is stated within that ceiling.

---

## 0 · T0 — escalation row 1 fired and was resolved before any other work

| Check | Observed |
|---|---|
| `phase-8-approved` tag | Present → `2b0d6235cdfb1c74bf6957ea4704f0f705fafec3` |
| `main` branch | **Absent.** No local branch, no remotes configured |
| Repo trunk | `master` @ `295a0e1` ("phase-6b: approved by Cooper") |
| Had the trunk moved? | No — `master` was a strict ancestor of `phase/8` (`phase/8..master` = 0) |
| Phase 8 files on `master` / on `phase/8` | **0** / **74** |

Cutting from the trunk as literally instructed would have produced a tree with no `a102_contamination.parquet`, no `a102_detection_anchors.parquet` and no `research/phase_8/`, making T2, T3 and T4 unrunnable. Reported as a hard stop; no fix attempted. **Cooper's resolution:** fast-forward `master` to `phase/8` HEAD (`6dd52cf`; a clean fast-forward, no merge commit, no history rewrite), then cut `phase/9` from `master`. Full state recorded in `prompts/phase_9.md` appendix and `config/phase_9.json` → `baseline`.

---

## 1 · Corporate-action table

### 1.1 Flag counts per session pair

`flag_cross_session_extreme` = `|log(p_later_close / p_earlier_close)| ≥ ln(1.8)`, computed from `event_minute_bars_v2` last-trade prices only. **Magnitude only** — the detector encodes no corporate-action judgment (T1a). Homed in `results/phase_9/artifacts/t1_cross_session_flags.parquet`, parallel to `flag_possible_row_cap`; **not** added to `canonical.py` (T1d).

| Session pair | n defined | n undefined | n flagged | flagged share | n in integer band | integer share of flagged |
|---|---:|---:|---:|---:|---:|---:|
| (T−1, T0) | 15,729 | 34 | 890 | **5.66%** | 212 | 23.8% |
| (T0, T+1) | 15,741 | 22 | 251 | **1.59%** | 57 | 22.7% |
| (T0, T+2) | 15,744 | 19 | 450 | **2.86%** | 109 | 24.2% |
| (T0, T+3) | 15,747 | 16 | 623 | **3.96%** | 143 | 23.0% |

1,484 events (9.41% of D1) are flagged on at least one pair. Chart: [`01_cross_session_ratio_ecdf.html`](charts/01_cross_session_ratio_ecdf.html).

The (T−1, T0) pair carries the highest rate at 5.66%. Escalation row 5 names (T0, T+1) explicitly, so it is not triggered by that pair. (T−1, T0) spans the momentum event itself, where a large `|r|` is the phenomenon D1 selects on.

### 1.2 Integer-band diagnostic — the raw share is not readable on its own

The prompt's diagnostic asks what share of flagged ratios fall within 3% of `k` or `1/k` for `k ∈ 2…20`. Two properties of that test have to be reported with the answer:

- **The bands are not measure-zero.** A band `[k(1−tol), k(1+tol)]` has constant log-width `ln((1+tol)/(1−tol))` = 0.0600 for every `k`. Over the flagged log-range the bands cover **24.7–28.4%** by chance, per pair.
- **The bands touch at k = 17.** Adjacent integers are `ln(1+1/k)` apart, which shrinks with `k`; once that falls below the band width the bands tile the axis and membership is automatic. The informative range is `k = 2…16`.

| Pair | observed integer share | expected by chance | excess | obs/chance |
|---|---:|---:|---:|---:|
| (T−1, T0) | 23.82% | 24.72% | −0.90 pp | 0.96× |
| (T0, T+1) | 22.71% | 28.42% | −5.71 pp | 0.80× |
| (T0, T+2) | 24.22% | 25.21% | −0.98 pp | 0.96× |
| (T0, T+3) | 22.95% | 27.62% | −4.67 pp | 0.83× |

The aggregate share sits **at or below** chance for every pair. Against a **local** background (the off-band density in a window around `ln k`, which respects the steep decay of the flagged distribution), all pairs pooled:

| k | observed | expected (local) | excess | obs/exp |
|---:|---:|---:|---:|---:|
| **2** | **298** | 210.07 | **+87.9** | **1.42×** |
| 3 | 56 | 61.02 | −5.0 | 0.92× |
| 4 | 21 | 28.81 | −7.8 | 0.73× |
| 5 | 12 | 20.50 | −8.5 | 0.59× |
| 6 | 11 | 13.59 | −2.6 | 0.81× |
| 7 | 10 | 9.45 | +0.6 | 1.06× |
| 8 | 9 | 10.34 | −1.3 | 0.87× |
| 9 | 18 | 8.80 | +9.2 | 2.05× |
| 10 | 12 | 8.67 | +3.3 | 1.38× |
| 11 | 5 | 7.53 | −2.5 | 0.66× |
| 12 | 18 | 7.47 | +10.5 | 2.41× |
| 13 | 2 | 5.64 | −3.6 | 0.35× |
| 14 | 5 | 3.74 | +1.3 | 1.34× |
| 15 | 6 | 1.71 | +4.3 | 3.51× |
| 16 | 8 | 2.13 | +5.9 | 3.75× |

The k = 2 band splits 203 at 2× and 95 at 1/2×. Chart 01 marks the resolvable bands individually and the `k ≥ 17` tiling zone as a single labelled region.

**Range limitation.** `integer_ratio_range` is 2…20 per the prompt default. The most extreme flagged ratios (SINT 99.46×, XPON 95.65×, ASTI 181.50×) exceed that range, so their `nearest_integer_ratio` saturates at 20 with a large deviation and they are counted as *outside* the integer band. The threshold was not tuned. Stated as a property of the configured range.

### 1.3 Top of the flagged list

All three examples cited in the prompt reproduce exactly. Full 50-row list in `t1_ca_detector.json` → `top_50_by_abs_r`; complete flagged set in `t1_cross_session_flags.parquet`.

| Ticker | Date | Pair | p_earlier | p_later | ratio | log r | nearest k |
|---|---|---|---:|---:|---:|---:|---|
| ASTI | 2023-09-12 | (T−1,T0) | 0.0508 | 9.2200 | 181.496 | +5.201 | 20 (saturated) |
| SINT | 2022-12-19 | (T0,T+2) | 0.0738 | 12.2500 | 165.989 | +5.112 | 20 (saturated) |
| SINT | 2022-12-19 | (T0,T+3) | 0.0738 | 8.2500 | 111.789 | +4.717 | 20 (saturated) |
| IVP | 2024-05-08 | (T−1,T0) | 0.0350 | 3.6400 | 104.000 | +4.644 | 20 (saturated) |
| XPON | 2024-10-08 | (T0,T+3) | 0.0299 | 3.0900 | 103.344 | +4.638 | 20 (saturated) |
| **SINT** | **2022-12-19** | **(T0,T+1)** | **0.0738** | **7.3401** | **99.459** | +4.600 | 20 (saturated) |
| **XPON** | **2024-10-08** | **(T0,T+1)** | **0.0299** | **2.8600** | **95.652** | +4.561 | 20 (saturated) |
| UCAR | 2024-03-28 | (T0,T+3) | 0.0592 | 5.6200 | 94.932 | +4.553 | 20 (saturated) |
| **TWG** | **2024-10-24** | **(T0,T+1)** | **12.2800** | **0.5627** | **0.0458** | −3.083 | 1/20 (saturated) |

Prompt-cited values: SINT 99.5×, XPON 95.7×, TWG 0.046×. **Reproduced.**

### 1.4 Four-variant sensitivity (T2)

**Cross-check first.** Phase 9 session closes reproduce Phase 8's `t4_anchors` ASOF markouts **exactly** — `max|diff| = 0.000e+00` over 31,380 pairs, 0 differing by more than 1e-9. The two price paths are identical; only the corporate-action handling differs.

**`t0_close → t1_close`, pooled**

| Variant | n | median | mean log | **mean simple** | q01 | q99 | share > 0 |
|---|---:|---:|---:|---:|---:|---:|---:|
| (i) untrimmed — PRIMARY | 15,688 | −0.02782 | −0.01909 | **+3.7308%** | −0.4957 | +0.5745 | 0.396 |
| (ii) flagged only | 249 | +0.64803 | +0.42374 | **+329.6271%** | −2.3048 | +4.1216 | 0.622 |
| (ii) unflagged only | 15,439 | −0.02844 | −0.02623 | **−1.5253%** | −0.4265 | +0.4062 | 0.393 |
| (iii) flag-excluded | 15,439 | −0.02844 | −0.02623 | **−1.5253%** | −0.4265 | +0.4062 | 0.393 |
| (iv) trimmed 0.55–1.80 | 15,443 | −0.02846 | −0.02637 | **−1.5365%** | −0.4276 | +0.4061 | 0.393 |

**`t0_close → t3_close`, pooled**

| Variant | n | median | mean log | **mean simple** | q01 | q99 | share > 0 |
|---|---:|---:|---:|---:|---:|---:|---:|
| (i) untrimmed — PRIMARY | 15,692 | −0.04682 | −0.03709 | **+5.9031%** | −0.7538 | +0.8622 | 0.379 |
| (ii) flagged only | 621 | −0.59132 | +0.14543 | **+210.5111%** | −2.3392 | +3.4965 | 0.496 |
| (ii) unflagged only | 15,071 | −0.04673 | −0.04461 | **−2.5278%** | −0.5093 | +0.4890 | 0.375 |
| (iii) flag-excluded | 15,071 | −0.04673 | −0.04461 | **−2.5278%** | −0.5093 | +0.4890 | 0.375 |
| (iv) trimmed 0.55–1.80 | 15,083 | −0.04689 | −0.04497 | **−2.5531%** | −0.5132 | +0.4891 | 0.374 |

Chart: [`02_cross_session_sensitivity.html`](charts/02_cross_session_sensitivity.html). The prompt's cited restatement (median −0.0278 → −0.0285; mean simple +3.73% → −1.54%) is reproduced to the digit.

**Mean simple flips sign in 10 of the 12 headline cells** — every quintile and the 2022–2024 era at both horizons. The two that do not flip (`era_2020_2021` at both horizons) were already negative.

Per-quintile, `t0_close → t1_close`, variant (i) → (iii):

| Cell | n (i) → (iii) | median (i) | median (iii) | mean simple (i) | mean simple (iii) |
|---|---:|---:|---:|---:|---:|
| pooled | 15,688 → 15,439 | −0.02782 | −0.02844 | +3.731% | −1.525% |
| Q1 | 3,133 → 3,092 | −0.02985 | −0.03042 | +1.617% | −1.510% |
| Q2 | 3,127 → 3,075 | −0.02564 | −0.02631 | +5.552% | −0.927% |
| Q3 | 3,143 → 3,103 | −0.02335 | −0.02436 | +4.250% | −1.027% |
| Q4 | 3,145 → 3,094 | −0.02441 | −0.02481 | +5.565% | −1.273% |
| Q5 | 3,140 → 3,075 | −0.03781 | −0.03792 | +1.669% | −2.896% |

**(iii) and (iv) are near-duplicates by construction**, not independent checks: the flag band is [0.5556, 1.8] and the configured trim bounds are [0.55, 1.80], differing only on the sliver 0.55 ≤ ratio < 0.5556.

### 1.5 T2a — flagged share per quintile (escalation row 6)

| Horizon | pooled share | Q1 | Q2 | Q3 | Q4 | Q5 | max / pooled |
|---|---:|---:|---:|---:|---:|---:|---:|
| `t0_close→t1_close` | 1.587% (n=15,688) | 1.309% | 1.663% | 1.273% | 1.622% | 2.070% | **1.30×** |
| `t0_close→t3_close` | 3.957% (n=15,692) | 4.310% | 3.739% | 3.435% | 3.529% | 4.774% | **1.21×** |

No quintile exceeds 2× the pooled share. The flags are near-uniform across quintiles.

---

## 2 · Retracement table

Detection universe **n = 15,369**. `A = tick_close_t_minus_1_rth`, `H = day_high_ext` (both D4-clean, frozen from 6b), `p_det = det_price_lat0` (frozen from Phase 8 A10.2). **All figures within the T+3 ceiling.**

`retrace_excursion(h) = (H − p_h)/(H − A)` — 0 = still at the high, 1.0 = back to the T−1 RTH close, >1.0 = below it.

### 2.1 Quantiles, primary (all carried, untrimmed)

| Horizon | n | q05 | q25 | **median** | q75 | q95 | block CI 95% on median |
|---|---:|---:|---:|---:|---:|---:|---|
| `t0_close` | 15,369 | 0.050 | 0.232 | **0.450** | 0.700 | 1.002 | [0.4387, 0.4623] |
| `t1_close` | 15,352 | −0.376 | 0.241 | **0.561** | 0.819 | 1.155 | [0.5481, 0.5741] |
| `t2_close` | 15,353 | −0.578 | 0.223 | **0.597** | 0.874 | 1.259 | [0.5802, 0.6097] |
| `t3_close` | 15,355 | −0.754 | 0.210 | **0.620** | 0.917 | 1.333 | [0.6049, 0.6347] |

`retrace_detection(h) = (H − p_h)/(H − p_det)`:

| Horizon | n | q05 | q25 | **median** | q75 | q95 | block CI 95% on median |
|---|---:|---:|---:|---:|---:|---:|---|
| `t0_close` | 15,041 | 0.151 | 0.670 | **1.261** | 2.502 | 9.571 | [1.2365, 1.2840] |
| `t1_close` | 15,027 | −1.736 | 0.667 | **1.381** | 2.869 | 11.495 | [1.3509, 1.4115] |
| `t2_close` | 15,027 | −2.704 | 0.610 | **1.437** | 3.050 | 12.118 | [1.4035, 1.4665] |
| `t3_close` | 15,028 | −3.663 | 0.589 | **1.483** | 3.189 | 13.000 | [1.4500, 1.5147] |

Charts: [`03_retracement_ecdf.html`](charts/03_retracement_ecdf.html), [`04_retracement_by_segment.html`](charts/04_retracement_by_segment.html).

### 2.2 Level-crossing census (T3c)

| Horizon | n | n below A | **share below A** | n below p_det | **share below p_det** |
|---|---:|---:|---:|---:|---:|
| `t0_close` | 15,369 | 773 | **5.03%** | 9,373 | **60.99%** |
| `t1_close` | 15,352 | 1,651 | **10.75%** | 9,751 | **63.52%** |
| `t2_close` | 15,353 | 2,260 | **14.72%** | 9,847 | **64.14%** |
| `t3_close` | 15,355 | 2,802 | **18.25%** | 9,900 | **64.47%** |

By era, median `retrace_excursion`:

| Era | t0_close | t1_close | t2_close | t3_close |
|---|---:|---:|---:|---:|
| 2020–2021 | 0.4278 | 0.5596 | 0.6053 | 0.6250 |
| 2022–2024 | 0.4615 | 0.5617 | 0.5913 | 0.6174 |

By detection segment, median `retrace_excursion`:

| Segment | n | t0_close | t1_close | t2_close | t3_close |
|---|---:|---:|---:|---:|---:|
| premarket | 4,630 | 0.615 | 0.696 | 0.722 | 0.756 |
| rth | 10,660 | 0.381 | 0.493 | 0.527 | 0.553 |
| post | 79 | 0.357 | 0.571 | 0.658 | 0.607 |

### 2.3 T3d — cross-session flag variant

**Scope note.** `H − A` spans the (T−1,T0) boundary, because `A` is a T−1 price and `H` is a T0 price. The **denominator** flag therefore applies at *every* horizon including `t0_close`, not only at T+1…T+3. Both components and their union are carried.

| Horizon | n flag_any | share | denominator | numerator |
|---|---:|---:|---:|---:|
| `t0_close` | 886 | 5.76% | 886 | 0 |
| `t1_close` | 1,067 | 6.94% | 886 | 247 |
| `t2_close` | 1,215 | 7.91% | 886 | 444 |
| `t3_close` | 1,363 | 8.87% | 886 | 612 |

| Horizon | median, all carried | median, flag-excluded | median, flagged only | share below A (all) | (flag-excl) |
|---|---:|---:|---:|---:|---:|
| `t0_close` | 0.4500 (n=15,369) | 0.4626 (n=14,483) | 0.3149 (n=886) | 5.03% | 5.11% |
| `t1_close` | 0.5611 (n=15,352) | 0.5681 (n=14,286) | 0.4766 (n=1,066) | 10.75% | 10.88% |
| `t2_close` | 0.5967 (n=15,353) | 0.6036 (n=14,141) | 0.4972 (n=1,212) | 14.72% | 14.69% |
| `t3_close` | 0.6199 (n=15,355) | 0.6286 (n=13,994) | 0.5306 (n=1,361) | 18.25% | 18.10% |

### 2.4 Escalation rows 8 and 9

- **Row 8 — 0 events (0.0000%)** have an undefined excursion denominator, against a 2% threshold. All 5 of Phase 6b's `denom_nonpositive` events sit inside the 394 `det_undefined`, necessarily: `H ≤ A` implies `H < 1.30·A`, so detection can never fire. The carried n = 5 the prompt anticipated is empty in this population for a structural reason, not a missing check.
- **Row 9 — 328 events (2.1342%)** have `H − p_det ≤ 0` (`retrace_det_undefined`), against a 25% threshold. Carried, never imputed.

---

## 3 · Axis separation table

### 3.1 T4b — fixed-exit latency column with n attrition

Entry at `det + latency`, exit at `t0_close`. Entry prices were recomputed here and cross-checked against Phase 8's frozen `det_price_lat*`: **exact match, `max|diff| = 0.00e+00` at all five latencies.**

| Latency | n | median | trimmed mean simple | median effective hold | n lost vs det+0 | share lost |
|---|---:|---:|---:|---:|---:|---:|
| det+0 | 15,369 | −0.03509 | −1.8417% | 552 min | 0 | 0.00% |
| det+1 | 15,366 | −0.03161 | −1.8263% | 551 min | 3 | 0.02% |
| det+5 | 15,358 | −0.02496 | −1.4636% | 547 min | 11 | 0.07% |
| det+15 | 15,344 | −0.01717 | −0.7366% | 537 min | 25 | 0.16% |
| det+30 | 15,319 | −0.00968 | −0.3289% | 523 min | 50 | **0.33%** |

Chart: [`06_latency_fixed_exit.html`](charts/06_latency_fixed_exit.html). Total attrition across the whole ladder is 50 events (0.33%), so movement along this column is not sample composition (T4c). **`det+0` is a physical impossibility and is carried only as the ladder's upper bound.**

On this grid the **hold shortens as latency grows** (552 → 523 min), so latency and holding period remain entangled here — in the opposite direction from Phase 8 §19. The fixed-horizon grid is the one that separates them.

### 3.2 T4a — fixed-horizon grid, hold as an independent axis

Median markout, all detection bins pooled, eras pooled (`n` ≈ 15,3xx per cell; full 450-cell grid with per-cell n in `t4_axis_summary.json` and chart 05):

| latency \ hold | 5 min | 15 min | 30 min | 60 min | 120 min |
|---|---:|---:|---:|---:|---:|
| det+0 | −0.0047 | −0.0144 | −0.0223 | −0.0265 | −0.0328 |
| det+1 | −0.0038 | −0.0127 | −0.0195 | −0.0247 | −0.0305 |
| det+5 | −0.0025 | −0.0087 | −0.0145 | −0.0197 | −0.0248 |
| det+15 | −0.0000 | −0.0043 | −0.0079 | −0.0121 | −0.0168 |
| det+30 | +0.0000 | −0.0016 | −0.0041 | −0.0070 | −0.0112 |

With hold held constant, the median **rises monotonically with latency at every one of the five holds**; with latency held constant, it **falls monotonically with hold length at every one of the five latencies**. Both statements hold across all 25 pooled cells.

Chart: [`05_axis_separation_grid.html`](charts/05_axis_separation_grid.html).

**Detection-bin ordering across hold facets** (at det+5, most negative first):

| hold | ordering |
|---|---|
| 5 min | 1000-1100 < 0930-1000 < 1100-1300 < premarket < after_1300 |
| 15 min | 1000-1100 < 1100-1300 < 0930-1000 < after_1300 < premarket |
| 30 min | 1000-1100 < 0930-1000 < 1100-1300 < after_1300 < premarket |
| 60 min | 1000-1100 < 0930-1000 < 1100-1300 < after_1300 < premarket |
| 120 min | 1000-1100 < 1100-1300 < 0930-1000 < after_1300 < premarket |

`1000-1100` is the most negative bin in all five facets. `premarket` and `after_1300` occupy the two least-negative positions in four of five facets (at hold 5, `premarket` sits fourth). The middle positions (`0930-1000`, `1100-1300`) exchange rank in 2 of the 5 facets. The ordering is therefore stable at the extremes and not identical across facets.

**Escalation row 11 — 0 thin cells of 450** (minimum cell n = 1,888). Chart 05 hatches off the artifact's `thin` flag regardless of the count.

### 3.3 Stale-price atom — diagnostic added beyond the prompt

With last-trade-at-or-before pricing, a markout is **exactly 0** whenever no print lands between entry and exit. That is a point mass, not a density, and it **decides the median wherever it straddles the 50th percentile** — which needs nowhere near a 50% zero share. A cell that is 49.6% negative / 4.6% zero / 45.8% positive reports a median of exactly 0.0 off a 4.6% atom.

**34 of 450 cells** are in that state, concentrated in `premarket` and `after_1300` at high latency and short hold. Exact-zero shares run 3.5–10.8% at hold 5. Recorded per cell as `median_on_zero_atom` in `t4_axis_summary.json`; ringed in chart 05. Those medians are fixed by print density, not measured, and no claim in this report rests on one.

---

## 4 · Clustered inference table

D1 holds 15,763 events across **2,576 tickers**: median 3/ticker, mean 6.12, max 57. **81.0%** of events sit in tickers with ≥5 events, **58.9%** in tickers with ≥10. Top-20 by count: MTC 57, WORX 46, VVPR 38, BAOS 38, GFAI 36, PHUN 35, AEMD 35, MDIA 34, KXIN 34, OBLG 33, ENSC 33, COSM 32, INM 32, XCUR 32, CDIO 31, DUO 31, NCTY 31, MYSZ 31, MLGO 31, TIRX 30.

Ticker-block bootstrap: resample **tickers** with replacement, 2,000 reps, seed 42, percentile CI. Naive comparison is an event-level iid bootstrap at the same reps and seed.

| Statistic | n | tickers | median | **block 95% CI** | naive 95% CI | width ratio | median of per-ticker medians | share tickers negative |
|---|---:|---:|---:|---|---|---:|---:|---:|
| `t0_close→t1_close` pooled, untrimmed | 15,688 | 2,561 | −0.0278 | **[−0.0302, −0.0258]** | [−0.0300, −0.0260] | 1.08× | −0.0190 | 62.2% |
| `t0_close→t1_close` pooled, flag-excl | 15,439 | 2,560 | −0.0284 | [−0.0308, −0.0264] | [−0.0306, −0.0267] | 1.11× | −0.0197 | 62.5% |
| … Q1 | 3,133 | 1,344 | −0.0299 | [−0.0346, −0.0255] | [−0.0343, −0.0254] | 1.03× | −0.0300 | 61.2% |
| … Q2 | 3,127 | 1,440 | −0.0256 | [−0.0297, −0.0212] | [−0.0297, −0.0216] | 1.04× | −0.0218 | 59.0% |
| … Q3 | 3,143 | 1,493 | −0.0233 | [−0.0278, −0.0183] | [−0.0284, −0.0180] | 0.91× | −0.0199 | 58.9% |
| … Q4 | 3,145 | 1,503 | −0.0244 | [−0.0282, −0.0198] | [−0.0285, −0.0198] | 0.96× | −0.0193 | 59.3% |
| … Q5 | 3,140 | 1,156 | −0.0378 | [−0.0424, −0.0327] | [−0.0422, −0.0330] | 1.05× | −0.0315 | 63.3% |
| `det+5→t0_close` pooled | 15,358 | 2,543 | −0.0250 | [−0.0281, −0.0224] | [−0.0279, −0.0229] | 1.15× | −0.0179 | 61.9% |
| … premarket | 4,630 | 1,424 | −0.0430 | [−0.0513, −0.0329] | [−0.0508, −0.0339] | 1.09× | −0.0208 | 55.5% |
| … 0930-1000 | 1,888 | 1,181 | −0.0307 | [−0.0375, −0.0239] | [−0.0375, −0.0240] | 1.01× | −0.0263 | 59.7% |
| … 1000-1100 | 2,158 | 1,192 | −0.0296 | [−0.0353, −0.0214] | [−0.0352, −0.0213] | 1.00× | −0.0236 | 58.9% |
| … 1100-1300 | 2,868 | 1,387 | −0.0270 | [−0.0330, −0.0217] | [−0.0326, −0.0217] | 1.03× | −0.0218 | 62.1% |
| … after_1300 | 3,814 | 1,597 | −0.0142 | [−0.0174, −0.0114] | [−0.0174, −0.0117] | 1.05× | −0.0131 | 59.7% |
| `retrace_excursion` t0_close | 15,369 | 2,547 | +0.4500 | [+0.4387, +0.4623] | [+0.4432, +0.4583] | **1.56×** | +0.3695 | 0.0% |
| `retrace_excursion` t1_close | 15,352 | 2,543 | +0.5611 | [+0.5481, +0.5741] | [+0.5531, +0.5699] | **1.54×** | +0.4458 | 7.8% |
| `retrace_excursion` t2_close | 15,353 | 2,544 | +0.5967 | [+0.5802, +0.6097] | [+0.5859, +0.6053] | **1.52×** | +0.4698 | 10.0% |
| `retrace_excursion` t3_close | 15,355 | 2,543 | +0.6199 | [+0.6049, +0.6347] | [+0.6096, +0.6304] | **1.43×** | +0.4865 | 10.9% |
| `retrace_detection` t0_close | 15,041 | 2,528 | +1.2609 | [+1.2365, +1.2840] | [+1.2372, +1.2833] | 1.03× | +1.2818 | 0.0% |
| `retrace_detection` t1_close | 15,027 | 2,524 | +1.3810 | [+1.3509, +1.4115] | [+1.3542, +1.4091] | 1.10× | +1.3752 | 8.5% |
| `retrace_detection` t2_close | 15,027 | 2,524 | +1.4371 | [+1.4035, +1.4665] | [+1.4084, +1.4663] | 1.09× | +1.4194 | 11.2% |
| `retrace_detection` t3_close | 15,028 | 2,524 | +1.4827 | [+1.4500, +1.5147] | [+1.4518, +1.5124] | 1.07× | +1.4839 | 11.9% |

Chart: [`08_clustered_inference.html`](charts/08_clustered_inference.html). Width ratio block/naive: median **1.07×** across 21 statistics, range 0.91–1.56×. The markout medians pay 1.00–1.15×; the `retrace_excursion` medians pay 1.43–1.56×. Three ratios below 1.0 are Monte Carlo noise at 2,000 reps, not a narrower true interval.

**Escalation row 10 — the block CI on the pooled `t0_close→t1_close` median is [−0.03016, −0.02584] and excludes 0.**

The median-of-per-ticker-medians is closer to zero than the pooled median in every markout row.

---

## 5 · Runway split table

| Quantity | Value |
|---|---|
| Detection universe | 15,369 |
| Atom at `runway = 0` | **2,013 events (13.10%)** — a point mass, reported separately |
| ≤1 min / ≤5 min / ≤15 min / ≤30 min | 19.92% / 30.57% / 42.04% / 50.29% |
| ≤60 / ≤120 / ≤240 / ≤480 min | 59.32% / 69.52% / 81.29% / 95.51% |
| Median / mean / max | 30 min / 112.96 min / 959 min |
| q25 / q75 / q90 | 3 min / 170 min / 353 min |
| KDE mode 1 (log10 scale) | ~1.1 min |
| KDE mode 2 (log10 scale) | ~276.4 min |
| **KDE trough** | **~1.8 min**, only **1.19×** deep against mode 1 |
| Split at the trough | short 3,062 / long 12,307 |

**Locating the trough required two corrections.**

1. A raw-count argmin is unusable here. `runway_minutes` is integer-valued, so log bins below ~10 min are narrower than the integer lattice and alternate populated/empty; the first attempt returned a trough in an **empty bin at 1.5 min** immediately beside mode 1. Replaced with a Gaussian KDE on `log10(runway ≥ 1)`, bandwidth 0.15 log10 units. **Smoothing is used only to locate the trough — every bar in chart 07 is a raw count.**
2. **The bimodality is measure-dependent.** Counts per *log* bin rise mechanically as the bins widen. The measure-invariant object is density per *minute*:

| Bin | events | **per minute** |
|---|---:|---:|
| 0–20 min | 6,853 | **342.65** |
| 20–40 | 1,376 | 68.80 |
| 40–60 | 850 | 42.50 |
| 60–80 | 646 | 32.30 |
| 80–100 | 544 | 27.20 |
| 100–120 | 399 | 19.95 |
| 240–260 | 265 | 13.25 |
| **320–340** | 271 | **13.55** ← largest interior local maximum |
| 480–500 | 79 | 3.95 |

The per-minute density decays monotonically through the bulk. The 8 interior local maxima are ripples on a decaying curve; the largest sits **25× below** the first bin. The prompt's "second mass at 120–480 min" is 4,011 events spread over 360 minutes = **11 events/min**, against 4,699 events in the first 6 minutes at **~780 events/min**. The only genuine discontinuity is the atom at exactly 0.

Chart 07's stated failure appearance is *"a single smooth decay from zero with no trough — one population."* [`07_runway_bimodality.html`](charts/07_runway_bimodality.html) **matches that description.**

### 5.1 T6b — anchor-knowable characterisation

Across the ~1.8 min cut, on anchor-knowable variables only. Overlap is 1 − total variation on a common 50-bin grid: 1.000 = identical, 0.000 = disjoint.

| Variable | short median | long median | difference | **distribution overlap** |
|---|---:|---:|---:|---:|
| price at detection | 2.8550 | 3.2200 | +0.3650 | **0.977** |
| `logrv` at detection | 0.4283 | −0.0153 | −0.4437 | 0.886 |
| `pq_rth_open` | 3.0 | 3.0 | 0.0 | 0.882 |
| detection minute | 435.0 | 378.0 | −57.0 | **0.832** |

| Detection segment | n | share in long-runway |
|---|---:|---:|
| premarket | 4,630 | **88.4%** |
| rth | 10,660 | 76.8% |
| post | 79 | 34.2% |

Detection segment shows the largest categorical gap; the four numeric variables overlap between 0.832 and 0.977.

### 5.2 T6c — prohibition, restated

**`runway_minutes` is not anchor-knowable.** It is measured from the T0 extended-day high, which is not known until the session resolves. It must never be used as a markout bucket (Phase 8 escalation row 11; Phase 9 escalation row 12). **Zero markouts are computed anywhere in T6** — the split is diagnostic only.

---

## 6 · Escalation check table

| # | Condition | Threshold | Observed | Result |
|---|---|---|---|---|
| 1 | `phase-8-approved` absent or `main` moved | any | tag present @ `2b0d623`; **`main` does not exist**, trunk `master` stale at `295a0e1` with 0 Phase 8 files | **FIRED at T0 — resolved by Cooper:** master fast-forwarded to `6dd52cf`, phase/9 cut from it |
| 2 | Pass over `filtered_trades` / `filtered_quotes` | any (>0) | **0** — only table touched is `event_minute_bars_v2` | PASS |
| 3 | Spine numeric column on a computation path | any (>0) | **0** — `momentum_pct` used only as a join key, rounded to 2dp | PASS |
| 4 | `v2` row count ≠ 45,925,350 | any | **45,925,350** (asserted at every script entry) | PASS |
| 5 | `flag_cross_session_extreme` share of (T0,T+1) | > 5% | **1.5946%** | PASS |
| 6 | Flagged share in any quintile > 2× pooled | any | max **1.30×** (t1, Q5) and **1.21×** (t3, Q5) | PASS |
| 7 | Median sign flip, variant (i) vs (iii) | any | **0 of 12** headline cells; all 12 medians negative in both | PASS |
| 8 | `retrace_excursion` denominator undefined | > 2% | **0 (0.0000%)** | PASS |
| 9 | `retrace_det_undefined` share | > 25% | **328 (2.1342%)** | PASS |
| 10 | Block CI on pooled `t0→t1` median contains 0 | any | **[−0.03016, −0.02584]** — excludes 0 | PASS |
| 11 | T4 cell n < 100 presented without hatching | any | **0 thin cells of 450** (min n = 1,888); chart 05 hatches off the flag regardless | PASS |
| 12 | `runway_minutes` used as a markout bucket | any | **0 markouts computed in T6** | PASS |
| 13 | Write outside the allowed paths | any | all writes in `results/phase_9/`, `prompts/`, `config/`, `research/phase_9/`, plus `docs/Research-Library-Map.md` and `results/reports/phase_9_report.md` required by standing CLAUDE.md rules | PASS |
| 14 | Recommendation, or good/weak/promising characterisation | any | **none** | PASS |

---

## 7 · Verification block (§10)

| Metric | Value | n | Source | Repro |
|---|---|---:|---|---|
| `flag_cross_session_extreme` count, (T0,T+1) | 251 (1.5946%) | 15,741 | `research/phase_9/t1_ca_detector.py:main` | `python -m research.phase_9.t1_ca_detector` |
| Integer-band share of flagged set, pooled | 23.53% (vs 24.7% by chance) | 2,214 | same | same |
| Integer-band excess at k = 2 | 298 obs vs 210.07 local expected (1.42×) | 2,214 | same | same |
| `t0→t1` median, variant (i) / (iii) | −0.02782 / −0.02844 | 15,688 / 15,439 | `research/phase_9/t2_sensitivity.py:main` | `python -m research.phase_9.t2_sensitivity` |
| `t0→t1` mean simple, variant (i) / (iii) | +3.7308% / −1.5253% | 15,688 / 15,439 | same | same |
| Phase 8 markout cross-check | `max|diff|` = 0.000e+00 | 31,380 | same | same |
| `retrace_excursion` median t0/t1/t2/t3 | 0.4500 / 0.5611 / 0.5967 / 0.6199 | 15,369 / 15,352 / 15,353 / 15,355 | `research/phase_9/t3_retracement.py:main` | `python -m research.phase_9.t3_retracement` |
| Share `p_h < A`, t0/t1/t2/t3 | 5.03% / 10.75% / 14.72% / 18.25% | same | same | same |
| Fixed-exit medians L0…L30 | −0.03509 / −0.03161 / −0.02496 / −0.01717 / −0.00968 | 15,369 → 15,319 | `research/phase_9/t4_axis_grid.py:main` | `python -m research.phase_9.t4_axis_grid` |
| Entry-price cross-check vs Phase 8 `det_price_lat*` | `max|diff|` = 0.00e+00, all 5 latencies | 15,369 each | same | same |
| Ticker count / events-per-ticker median | 2,576 / 3 | 15,763 | `research/phase_9/t5_clustered.py:main` | `python -m research.phase_9.t5_clustered` |
| Block-bootstrap 95% CI, pooled overnight median | [−0.030160, −0.025838] | 15,688 (2,561 tickers) | same | same |
| Runway per-minute density, first bin | 342.65 events/min | 15,369 | `research/phase_9/t6_runway_split.py:main` | `python -m research.phase_9.t6_runway_split` |

**Config hash `ba858a71171a`** appears in the caption of all eight charts. It is `sha256[:12]` of `config/phase_9.json` with newlines normalised to LF, so it is stable across LF and CRLF checkouts.

### Filter waterfall

| Step | Rows in | Rows out | Dropped | Why |
|---|---:|---:|---:|---|
| D1 → session pairs with both closes present and > 0, (T−1,T0) | 15,763 | 15,729 | 34 | session absent from v2 (offsets −3…+3 only) or non-positive close; carried as undefined, never imputed |
| … (T0,T+1) | 15,763 | 15,741 | 22 | same |
| … (T0,T+2) | 15,763 | 15,744 | 19 | same |
| … (T0,T+3) | 15,763 | 15,747 | 16 | same |
| Phase 8 `a102_contamination` base, anchor `t0_close` | 31,380 | 31,380 | 0 | base population as Phase 8 left it (its flagged union already excluded there) |
| … → markout non-null | 31,380 | 31,380 | 0 | — |
| D1 → detection universe | 15,763 | 15,369 | 394 | `det_undefined`: tick T0 extended max never reaches 1.30× anchor (Phase 8 A10.3) |
| Detection universe → `retrace_excursion` defined | 15,369 | 15,369 | 0 | `H − A > 0`; all 5 of 6b's `denom_nonpositive` sit inside the 394 |
| Detection universe → `retrace_detection` defined | 15,369 | 15,041 | 328 | `H − p_det ≤ 0` (detection print already at the extended-day high); carried |
| T4 fixed-horizon cells → markout defined | 384,225 | 382,131 | 2,094 | entry or exit minute past the last T0 print (`det+latency+hold` runs off the session end); carried, never imputed |
| T4 fixed-exit cells → markout defined | 76,845 | 76,756 | 89 | `det + latency` past the last T0 print |

---

## 8 · Output file table

| File | Description | Status |
|---|---|---|
| `config/phase_9.json` | Thresholds, trim bounds, bootstrap seed/reps, horizons, latencies, holds | ✅ |
| `prompts/phase_9.md` | Phase prompt + T0 escalation appendix | ✅ |
| `results/phase_9/artifacts/t1_cross_session_flags.parquet` | Per (event, session-pair) ratio, flag, nearest-integer diagnostic — 62,961 rows | ✅ |
| `results/phase_9/artifacts/t1_ca_detector.json` | Flag counts, integer-clustering shares + chance baselines, top-50 list | ✅ |
| `results/phase_9/artifacts/t2_cross_session_sensitivity.json` | Four variants × cell, full statistic set, cross-check | ✅ |
| `results/phase_9/artifacts/t3_retracement.parquet` | Per-event retracement, four horizons, both denominators — 61,476 rows | ✅ |
| `results/phase_9/artifacts/t3_retracement_summary.json` | Quantiles, level-crossing census, era/segment, flag variants | ✅ |
| `results/phase_9/artifacts/t4_axis_grid.parquet` | latency × hold × det_bin × era cells — 461,070 rows | ✅ |
| `results/phase_9/artifacts/t4_axis_summary.json` | 450 cell medians, trimmed means, n, attrition, zero-atom diagnostic | ✅ |
| `results/phase_9/artifacts/t5_clustered_inference.json` | Ticker distribution, 21 bootstrap CIs, per-ticker medians | ✅ |
| `results/phase_9/artifacts/t6_runway_split.json` | Modes, trough, measure-dependence, population characterisation | ✅ |
| `results/phase_9/charts/01–08*.html` (+ `.png`) | 8 charts, all kaleido-verified | ✅ |
| `results/phase_9/{digest.json, REPORT.md}` | Per §10/§11 | ✅ |
| `results/reports/phase_9_report.md` | Cross-phase copy (standing CLAUDE.md rule) | ✅ |
| `docs/Research-Library-Map.md` | Updated with `research/phase_9/` and `results/phase_9/` | ✅ |

---

## 9 · Chart contract deviations

Two, both deliberate, both recorded in the chart docstrings.

1. **Chart 06** — the contract specifies an *"n-attrition line on secondary axis"*. A dual y-scale is the one encoding the project visualization standard forbids outright. Attrition ships as a **linked lower panel sharing the x-axis**: same information, same chart file, no second y-scale.
2. **Chart 08** — the forest plot is **split into two panels by unit**. Markout medians sit near −0.03 log and retracement medians near +1.4 ratio; pooled onto one axis the markout intervals collapse to invisible specks and the panel cannot be read.

**Palette note.** The categorical palette is carried unchanged from the approved 6b/7/8 charts. Run through the validator, the full 8-slot order fails the normal-vision adjacent-pair check (`#e87ba4` vs `#e34948`, ΔE 13.2 < 15). No Phase 9 chart uses more than 5 series, and the first 5 slots pass every check. Phase 9 caps categorical use at 5 and never reaches the failing pair. The sub-3:1 contrast warning on two slots is relieved by the per-bucket n labels the Evidence Standard already mandates.

**Outliers are never clipped.** Heavy-tailed panels open on a zoomed view with the out-of-view count stated in the caption; every point remains in the figure and double-click autoranges.

---

## 10 · Commits

| SHA | Task |
|---|---|
| `d50113f` | T0 — branch, prompt, config (row 1 fired and resolved) |
| `529c252` | T1 — cross-session corporate-action detector |
| `cb501e1` | T2 — cross-session sensitivity restatement, four variants |
| `f89bee1` | T3 — retracement measurement |
| `61b18e3` | T4 — axis separation grid |
| `de76c8b` | T5 — ticker-clustered inference |
| `f5c108d` | T6 — runway population split |
| `4edf2c9` | T7a — charts 01–08 |
| *(this commit)* | T7b — digest, REPORT, cross-phase copy, library map |

---

## Approval Gate

Do not begin Phase 10 or any follow-on work until Cooper has reviewed results and given explicit approval.
