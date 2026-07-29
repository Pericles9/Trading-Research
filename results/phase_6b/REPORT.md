# Phase 6b — Measurement 1 Redo over the Full Extended Day (A8.2 tick-anchor resumption)

**Date:** 2026-07-29 · **Branch:** `phase/6b` · **Baseline:** `phase-7-approved` · **Status:** complete, awaiting approval

Resumed under Amendment 8 (A8.2, [prompts/phase_6b_amendment_8.md](../../prompts/phase_6b_amendment_8.md), Cooper-approved 2026-07-28). Description only — the latency-budget reading is Cooper's from chart 04.

---

## 0. Resumption setup

Phase 6b stopped at A6.1 (the defect-#4 basis test failed) *before* D4, the t8 canonical view, and the approved 6c/7 docs existed. Those are all preconditions for the D4-compliant redo, so `phase/6b` was fast-forwarded onto `phase-7-approved` (it was a strict ancestor) before any A6.2 work.

**The anchor change (D4).** 6b's opportunity-decay was anchored on the spine's `prev_close`, permanently quarantined by D4. Cooper's decision (2026-07-28): replace it with **`tick_close_t_minus_1_rth`** — the tick-derived last trade at/before the T-1 RTH close (`last_price` of the max-minute T-1 bar in segment `{premarket, rth}`, from `event_minute_bars_v2`). Both the anchor and `day_high_ext` are now tick-only.

`realized(t) = log(price_t / tick_close_T-1_RTH) / log(day_high_ext / tick_close_T-1_RTH)`

---

## 1. A6.2 — D4 sweep, rework, re-validate, re-freeze

**Sweep** ([a62_d4_sweep.json](artifacts/a62_d4_sweep.json)): a re-runnable tokenize+ast scan of `research/phase_6b/` + `config/phase_6b.json` found **13 measurement-path spine hits, all `prev_close`** (measurements_v2 5, t1_eligibility 5, t2_dev_pipeline 3); `build_minute_bars_v2` clean; a51/a61 retired diagnostics. **Rework** replaced every one with the tick anchor → re-run sweep **13 → 0**. **Dev re-validation**: 36.7 s (<60 s), 0 duplicate keys, 55/56 anchor coverage, `rth_legacy` = 39 min (matches Phase 6's dev tier). **Config re-frozen** to the tick anchor + dup-print spec + chart-08-dropped.

---

## 2. A6.3a — the single budgeted full pass

One pass over `filtered_trades` (4,951,605,544 rows) → **`event_minute_bars_v2`: 45,925,350 rows** (extended-day, segment-tagged, tz-aware), **24.75 min, 0 spill** ([t3_full_pass_v2_summary.json](artifacts/t3_full_pass_v2_summary.json)):

| gate | result |
|---|---|
| distinct T=0 events (row 3) | 15,763 = 15,763 ✓ |
| every v1 T=0 event present in v2 (row 4) | 0 missing ✓ |
| bar integrity (dup keys / out-of-window / bad segments) | 0 / 0 / 0 ✓ |
| tz ET-vs-UTC date mismatch | **0 / 4,041,077,893 rows** ✓ |

### The dup-print finding (row 7) — a real data-quality issue

A8.2 required a duplicate-print counter in the pass. The exact `COUNT(DISTINCT)` version was computationally infeasible (it spilled 350 GB in 2.5 h and was killed before filling the disk; disk reclaimed, DB intact, v2 never partially committed). Per Cooper it was reworked to a bounded **HLL approx** counter (re-run: 24.75 min, 0 spill).

The HLL coarse flag caught **9 events > 5%**. A targeted **exact** recheck ([a63a_dup_recheck.json](artifacts/a63a_dup_recheck.json)) confirmed **7 are real** — genuine exact-duplicate rows in `filtered_trades` on `(ticker, event_date, momentum_pct, sip_timestamp, price, size, sequence_number)`:

| event | prints | exact dups | rate |
|---|---|---|---|
| SCWO 2022-01-06 | 616 | 121 | 19.6% |
| SCWO 2022-01-07 | 634 | 121 | 19.1% |
| CETY 2022-01-05 | 485 | 58 | 12.0% |
| CETY 2022-01-24 | 473 | 55 | 11.6% |
| NUKK 2022-01-21 | 211 | 20 | 9.5% |
| NUKK 2022-01-14 | 235 | 20 | 8.5% |
| CETY 2022-01-12 | 865 | 58 | 6.7% |

(SMTK, SOWG — the 2 tiniest — were HLL small-cardinality artifacts, 0 exact dups.) All 7 real ones are **2022-01** events. Previously undetected: 6c's exact check was dev-tier only. **7 is a lower bound** — duplication below the ~2% HLL noise floor was not audited (each audit = another full scan). Impact: inflates volume/`n_trades` for these 7; **price-path decay unaffected** (a duplicate is the same price at the same timestamp); pooled results robust.

**Cooper disposition (2026-07-29): flag-and-proceed** — the 7 carry `flag_has_dup_prints=TRUE` in `event_index_v2` (annotation, not dropped); root-cause + full-population dedup deferred to a future remediation phase ([Open-Items-Register](../../docs/Open-Items-Register.md)).

---

## 3. A6.3b — extended-day measurements ([t4_measurements_v2_summary.json](artifacts/t4_measurements_v2_summary.json))

Anchor coverage: 15,727/15,763 have `has_t_minus_1_rth`; 36 (0.23%) no anchor (excluded from primary decay, flag-and-report); 5 (0.03%) `denom_nonpositive` — both under gates.

| measurement | value | chart |
|---|---|---|
| **primary pooled median crossing** | **516 min since 04:00 ET (~12:36 ET)** — gap-inclusive | [04](charts/04_opportunity_decay_ext.html) |
| **`rth_legacy` crossing** | **52 min since RTH open — reproduces Phase 6's 52 exactly** | [04](charts/04_opportunity_decay_ext.html) |
| realized at RTH open (median) | 0.173 (~17% of the move is premarket) | [04](charts/04_opportunity_decay_ext.html) |
| extended-day high time-of-day (median) | 12:13 ET; 09:30 & 16:00 spikes | [07](charts/07_high_time_of_day.html) |
| min-window medians (ext-day volume) | 25% = 23, 50% = 89, 75% = 222 min | [03](charts/03_min_window_cdf_ext.html) |
| segment volume share medians | premarket 0.9%, RTH 94.3%, post 1.8% | [06](charts/06_segment_volume_shares.html) |

The primary (516 min) and `rth_legacy` (52 min) differ because the prior-RTH-close anchor puts the overnight gap in the denominator, so the intraday move is a smaller fraction of the total. Chart 06 confirms premarket volume is a **real distribution, not a 0-spike** — ETH data is present, not a collection gap — and RTH is bimodal (a secondary mass near 0 = the ETH-dominant tail).

---

## 4. Escalation check

| # | condition | observed |
|---|---|---|
| 1 | measurement-path computation spine hits after rework | 0 ✓ |
| 2 | universe_selection hits outside momentum_pct / flag_bad_denominator | 0 ✓ |
| 3 | distinct T=0 ≠ 15,763 | 15,763 ✓ |
| 4 | v1 T=0 event absent from v2 | 0 ✓ |
| 5 | has_t_minus_1_rth=FALSE (report-only) | 36 (0.23%) |
| 6 | denom_nonpositive > 1% | 0.03% ✓ |
| 7 | dup-print coarse flag (>5% approx) | **9 flagged → 7 real (flag-and-proceed) + 2 artifacts** |
| 8 | dev-tier runtime > 60s | 36.7s ✓ |
| 9 | full passes over filtered_trades > 1 (measurement) | 1 ✓ (dup rechecks = diagnostic follow-ups, documented) |
| 10 | write to base/dev/v1 tables or data root | none ✓ |
| 11 | calendar pin drift | 5.4.0 / 4.13.2 ✓ |
| — | disk incident (exact-distinct blowup) | killed, disk reclaimed, DB intact, resolved via HLL |

---

## 5. Verification block

| metric | value | n | source | reproduce |
|---|---|---|---|---|
| D4 sweep (measurement path) | 13 → 0 | — | `a62_d4_sweep.json` | `python -m research.phase_6b.a62_d4_sweep` |
| v2 bar cache | 45,925,350 rows, 24.75 min | 15,763 | `t3_full_pass_v2_summary.json` | `python -m research.phase_6b.t3_full_pass_v2` (budgeted) |
| dup recheck | 7 real / 2 artifact | 9 | `a63a_dup_recheck.json` | `python -m research.phase_6b.a63a_dup_recheck` (1 extra scan) |
| primary crossing | 516 min | 15,727 | `t4_measurements_v2_summary.json` | `python -m research.phase_6b.t4_measurements_v2` |
| rth_legacy crossing | 52 min | 15,763 | `t4_measurements_v2_summary.json` | (same) |
| charts 01–07 | — | — | `charts/` | `python -m research.phase_6b.build_charts_v2` |

---

## 6. Commits

`A6.2` prompt → `A6.2a` sweep → `A6.2b` rework → `A6.2c` dev → `A6.2d` config re-freeze → `A6.3a` pre-run (×2, HLL rework) → `A6.3a` post-run (+ dup finding) → `A6.3b` T4 → `A6.3c` charts → `A6.3d` digest/report.

---

## Approval gate

Awaiting Cooper's review of the charts and the tick-anchor measurement. On approval, tag `phase-6b-approved` — **master fast-forwards** (first landing since `phase-5a-approved`). The latency-budget reading, and whether the operative clock is the gap-inclusive **primary (516 min)** or the RTH-intraday **`rth_legacy` (52 min)**, is Cooper's from chart 04 — not the agent's.
