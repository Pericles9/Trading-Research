# Phase 9 — Path Shape, Cross-Session Integrity, and Clustered Inference

**Date:** 2026-08-03
**Baseline:** `phase-8-approved` (pending) — `event_minute_bars_v2`, 45,925,350 rows; D1 = 15,763; detection universe n = 15,369
**Objective:** Repair the cross-session price-basis defect found in Phase 8's markouts, separate the three confounded axes (detection time-of-day / holding period / latency), and produce the first **retracement** measurement of the excursion itself.
**Primary success metric:** A cross-session corporate-action flag is materialised and every Phase 8 cross-session statistic is reported with and without it; retracement ECDFs exist at T0/T+1/T+2/T+3 with ticker-clustered confidence intervals.

---

**Context:**

- Working directory: repo root. Branch `phase/9` cut from `main`.
- **Read-only phase.** Zero passes over `filtered_trades` / `filtered_quotes`. Every quantity derives from `event_minute_bars_v2` and frozen Phase 6b/8 artifacts.
- **D4 remains in force and is being extended.** No spine numeric column on any computation path. `momentum_pct` stays diagnostic-display-only.
- **Flag, never delete.** No event is dropped from any population. Suspect events are flagged, carried, and reported as their own row.
- Primary statistics are **untrimmed**. Trimmed and flag-excluded variants ship *alongside* as sensitivity, never instead of.
- `event_minute_bars_v2` carries session offsets −3…+3 only. **T+3 is the hard horizon ceiling.** Do not extrapolate beyond it; state the ceiling in the report.
- Charts: Plotly, standalone HTML, one chart per file, per Agent_Prompt_Standard §9.
- Config `config/phase_9.json` holds: `ca_flag_log_threshold`, `ca_integer_tolerance`, `integer_ratio_range`, `trim_ratio_bounds`, `bootstrap_reps`, `bootstrap_seed`, `horizons`, `latencies`, `hold_minutes`.

---

## Background — what this phase is fixing

Phase 8 §18/§19 computed markouts across session boundaries using raw tick prices with no corporate-action handling. Inspection of `a102_contamination.parquet` found 245 `t0_close → t1_close` pairs (1.56%) with price ratios beyond 1.8× / 0.55×, clustering at 2×, 1/2×, 10×, 12× — reverse-split signatures, not returns. Examples: SINT 2022-12-19 ($0.0738 → $7.3401, 99.5×); XPON 2024-10-08 ($0.0299 → $2.86, 95.7×); TWG 2024-10-24 ($12.28 → $0.5627, 0.046×).

Effect on the pooled `t0_close → t1_close` statistic: median moves −0.0278 → −0.0285 (robust), **mean simple return moves +3.73% → −1.54% (sign flip)**.

D4 quarantined spine numerics because of adjustment-basis mismatch. The same mismatch exists in raw tick prices **across a session boundary**. Phase 8 applied the guard within-day and then computed cross-day ratios anyway. This phase closes that gap.

---

## Tasks

- [ ] **T0 — Branch and commit prompt**
  Cut `phase/9` from `main`. Commit `prompts/phase_9.md` and `config/phase_9.json` before any other work. Confirm `phase-8-approved` tag state and record the commit SHA in the digest.

- [ ] **T1 — Cross-session corporate-action detector**
  For every ordered session pair used anywhere in Phase 8 or this phase — (T0,T+1), (T0,T+2), (T0,T+3), (T−1,T0) — compute `r = log(p_later_close / p_earlier_close)` from `event_minute_bars_v2` last-trade prices only.

  - [ ] T1a — Set `flag_cross_session_extreme` = `|r| >= ca_flag_log_threshold` (default `ln(1.8)`). **Magnitude only.** Do not encode a corporate-action judgment in the detector.
  - [ ] T1b — Diagnostic: for flagged pairs, compute `exp(r)` and report the share falling within `ca_integer_tolerance` (default 3%) of `k` or `1/k` for integer `k` in `integer_ratio_range` (default 2…20). Report the histogram of `exp(r)` on a log axis with integer bands marked. **This is evidence about what the flagged set is, not part of the flag.**
  - [ ] T1c — Write the full flagged list (ticker, event_date, session pair, both prices, ratio, nearest integer ratio, absolute deviation from it) to `artifacts/t1_cross_session_flags.parquet`. Post the top 50 by `|r|` in the report.
  - [ ] T1d — Materialise `flag_cross_session_extreme` per (event, session-pair) in `artifacts/t1_cross_session_flags.parquet`. **Home it in the phase-9 artifact, parallel to `flag_possible_row_cap`** — do not add to `canonical.py` without Cooper's instruction.
  - [ ] T1e — Commit.

- [ ] **T2 — Phase 8 cross-session sensitivity restatement**
  Recompute every Phase 8 cross-session statistic — `t0_close → t1_close` and `t0_close → t3_close`, pooled and by `pq_rth_open` quintile and era — in four variants: **(i) untrimmed all**, **(ii) flagged carried but reported separately**, **(iii) flagged excluded**, **(iv) trimmed to `trim_ratio_bounds`** (default 0.55–1.80).

  For each variant × cell report: `n`, median, mean log, **mean simple return**, IQR, q01/q05/q95/q99, share > 0.

  - [ ] T2a — Report the flagged-set share **per quintile** so it is visible whether the flags could manufacture the gradient.
  - [ ] T2b — Commit.

- [ ] **T3 — Retracement measurement (new)**
  The Phase 8 grid measures markouts from anchors. It never measures how much of the excursion comes back. This task does.

  For each event in the detection universe (n = 15,369), with `A = tick_close_t_minus_1_rth` (D4-clean, frozen from 6b) and `H = day_high_ext`:

  - [ ] T3a — **Excursion retracement**, at horizons `h ∈ {t0_close, t1_close, t2_close, t3_close}`:
        `retrace_excursion(h) = (H − p_h) / (H − A)`, defined only where `H − A > 0` (reuse 6b's `denom_nonpositive`, n=5, carried).
        `0` = still at the high. `1.0` = fully back to the T−1 RTH close. `>1.0` = below it.
  - [ ] T3b — **Detection-relative retracement**, same horizons:
        `retrace_detection(h) = (H − p_h) / (H − p_det)` where `p_det = det_price_lat0`. Defined only where `H − p_det > 0`; carry the rest as `retrace_det_undefined` with its own n.
  - [ ] T3c — **Level-crossing census.** Per horizon, the share of events where `p_h < A` (fully round-tripped) and where `p_h < p_det` (below the detection level). Report n and share, by era and by detection segment (premarket / rth / post).
  - [ ] T3d — Recompute T3a–T3c with `flag_cross_session_extreme` events carried separately. All T+1/T+2/T+3 retracement figures ship in both variants.
  - [ ] T3e — Commit.

- [ ] **T4 — Axis separation grid**
  Phase 8 §19 confounded detection time-of-day with holding period, and §19's latency claim confounded latency with holding period. Rebuild the grid with **holding period as an explicit independent axis**.

  - [ ] T4a — Fixed-horizon grid: entry at `det + latency`, exit at `entry + hold`, for `latency ∈ latencies` (0,1,5,15,30) × `hold ∈ hold_minutes` (5,15,30,60,120) × `det_bin` (5 bins) × era. Report median, trimmed mean simple, n per cell. Cells with n < 100 hatched and carry no claim.
  - [ ] T4b — Fixed-exit grid: entry at `det + latency`, exit at `t0_close`, same latency set. This is the only axis where latency is unconfounded by hold length. Report the full distribution per latency, not just the median.
  - [ ] T4c — Explicitly report, per cell, the **n attrition** across the latency axis so it is visible that changes are not sample composition.
  - [ ] T4d — Commit.

- [ ] **T5 — Ticker-clustered inference**
  D1 contains 15,763 events across 2,576 distinct tickers (mean 6.1/ticker, max 57; 59% of events sit in tickers with ≥10 events). Nominal n materially overstates independent observations.

  - [ ] T5a — Report the events-per-ticker distribution: n tickers, median, mean, max, share of events in tickers with ≥5 and ≥10 events, top-20 tickers by event count.
  - [ ] T5b — **Ticker-block bootstrap** (resample tickers with replacement, `bootstrap_reps` default 2000, `bootstrap_seed` from config) producing 95% CIs on every headline median in this phase and on the Phase 8 headline medians being restated: `t0_close→t1_close` pooled and per quintile, `det+5→t0_close` pooled and per det_bin, and each retracement median.
  - [ ] T5c — Report **median of per-ticker medians** and **share of tickers with negative median** alongside every pooled median.
  - [ ] T5d — Commit.

- [ ] **T6 — Runway population split**
  `runway_minutes` is not unimodal: 2,013 events (12.8%) have runway exactly 0, 19.9% ≤1 min, 30.6% ≤5 min, then a second mass at 120–480 min.

  - [ ] T6a — Report the full histogram (linear and log-x) and locate the trough between the two modes empirically. Do not assume a cut point.
  - [ ] T6b — Characterise the two populations on **anchor-knowable variables only** (detection segment, detection minute, `pq_rth_open`, price level at detection, `logrv` at detection). Report whether any separates them.
  - [ ] T6c — **`runway_minutes` is not anchor-knowable and must never be used as a markout bucket** (Phase 8 escalation row 11 applies). It is a diagnostic split only. State this in the report.
  - [ ] T6d — Commit.

- [ ] **T7 — Charts, digest, report**
  Produce every chart in the Chart Contract. Write `results/phase_9/digest.json` per §11 and `results/phase_9/REPORT.md`. Every claim cites its chart file. Every statistic carries n.
  - [ ] T7a — Commit; confirm `git status` clean.

---

## Escalation Criteria

Stop, commit current state, post results, await instruction. Do not attempt a fix. Table order is priority order.

| # | Condition | Threshold | Action |
|---|---|---|---|
| 1 | `phase-8-approved` tag absent or `main` moved | any | Hard stop — post tag/SHA state |
| 2 | Any pass over `filtered_trades` or `filtered_quotes` | any (>0) | Hard stop |
| 3 | Spine numeric column on a computation path | any (>0) | Hard stop |
| 4 | `v2` row count ≠ 45,925,350 | any | Hard stop |
| 5 | `flag_cross_session_extreme` share of (T0,T+1) pairs | > 5% | Hard stop — post distribution + top-50 list |
| 6 | Flagged-set share in any single quintile exceeds 2× the pooled share | any | Hard stop — the flag may be manufacturing the gradient |
| 7 | Median flips sign between variant (i) untrimmed and variant (iii) flag-excluded on any headline cell | any | Hard stop — post both |
| 8 | `retrace_excursion` denominator undefined | > 2% of detection universe | Hard stop — post breakdown |
| 9 | `retrace_det_undefined` share | > 25% | Hard stop — post breakdown by segment |
| 10 | Ticker-block bootstrap 95% CI on pooled `t0_close→t1_close` median contains 0 | any | Hard stop — post CI and per-ticker distribution |
| 11 | Any T4 cell with n < 100 presented without hatching | any | Hard stop |
| 12 | `runway_minutes` or any other non-anchor-knowable variable used as a markout bucket | any | Hard stop |
| 13 | Write outside `results/phase_9/`, `prompts/`, `config/`, `research/phase_9/` | any | Hard stop — post intended path |
| 14 | Agent states a recommendation, or characterises a result as good/weak/promising | any | Report sent back |

---

## Output Files

| File | Description | Status |
|---|---|---|
| `config/phase_9.json` | Thresholds, trim bounds, bootstrap seed/reps, horizons, latencies, holds | [ ] |
| `prompts/phase_9.md` | This prompt | [ ] |
| `results/phase_9/artifacts/t1_cross_session_flags.parquet` | Per (event, session-pair) ratio, flag, nearest-integer diagnostic | [ ] |
| `results/phase_9/artifacts/t1_ca_detector.json` | Flag counts, integer-clustering shares, top-50 list | [ ] |
| `results/phase_9/artifacts/t2_cross_session_sensitivity.json` | Four variants × cell, full statistic set | [ ] |
| `results/phase_9/artifacts/t3_retracement.parquet` | Per-event retracement at all four horizons, both denominators | [ ] |
| `results/phase_9/artifacts/t3_retracement_summary.json` | Retracement quantiles, level-crossing census, by era/segment | [ ] |
| `results/phase_9/artifacts/t4_axis_grid.parquet` | latency × hold × det_bin × era cells | [ ] |
| `results/phase_9/artifacts/t4_axis_summary.json` | Cell medians, trimmed means, n, attrition | [ ] |
| `results/phase_9/artifacts/t5_clustered_inference.json` | Ticker distribution, bootstrap CIs, per-ticker medians | [ ] |
| `results/phase_9/artifacts/t6_runway_split.json` | Mode locations, trough, population characterisation | [ ] |
| `results/phase_9/charts/01–08*.html` (+ `.png`) | Per Chart Contract, kaleido-verified | [ ] |
| `results/phase_9/{digest.json, REPORT.md}` | Per §10/§11 | [ ] |

---

## Chart Contract

| # | File | Question | Encoding | n shown | Looks like this if wrong |
|---|---|---|---|---|---|
| 01 | `charts/01_cross_session_ratio_ecdf.html` | Are the extreme cross-session ratios corporate actions or real moves? | x = `exp(r)` log scale, ECDF + rug of flagged points; vertical bands at integer `k` and `1/k`; flag threshold marked | n total, n flagged, n within integer tolerance, in title | Flagged points spread smoothly with no mass at integer bands — then they are real moves and the flag is over-broad |
| 02 | `charts/02_cross_session_sensitivity.html` | Does the flagged set change the conclusion or only the tails? | facet per variant (i–iv); x = quintile, y = markout, violin + strip; median and mean-simple both marked with distinct glyphs | Per-cell n above each violin | Medians shift materially between variants — then the flag is not tail-only and the Phase 8 restatement is larger than a footnote |
| 03 | `charts/03_retracement_ecdf.html` | How much of the excursion comes back, and how fast? | x = `retrace_excursion` (0 = at high, 1 = back to T−1 close), ECDF, one line per horizon (t0…t3); reference lines at 0.5 and 1.0 | n per horizon in legend | ECDFs bunched far left and near-identical across horizons — then nothing retraces and "mean reversion" is unsupported at any horizon |
| 04 | `charts/04_retracement_by_segment.html` | Do premarket-detected and RTH-detected events retrace differently? | facet per horizon; x = detection segment, y = `retrace_excursion`, violin + strip; ticker-block bootstrap CI on each median overlaid | Per-segment n above each violin | Violins fully overlap across segments at every horizon — no segment effect |
| 05 | `charts/05_axis_separation_grid.html` | Is the Phase 8 time-of-day gradient real, or was it holding period? | heatmap facet per `hold`; x = `det_bin`, y = `latency`, colour = median markout, diverging about 0; cells n<100 hatched | n printed in every cell | The `det_bin` ordering is identical across `hold` facets — then time-of-day is real and Phase 8 §19 stands as written |
| 06 | `charts/06_latency_fixed_exit.html` | Does entry latency matter when the exit is fixed? | x = latency, y = markout to `t0_close`, violin + strip; n-attrition line on secondary axis | n per latency above each violin | Violins identical across latency — then latency genuinely does not matter and Phase 8's claim stands |
| 07 | `charts/07_runway_bimodality.html` | Is runway one population or two? | x = `runway_minutes` (linear panel + log panel), histogram; empirical trough marked; colour by detection segment | n per segment in legend | A single smooth decay from zero with no trough — one population, and the Phase 8 medians are readable as-is |
| 08 | `charts/08_clustered_inference.html` | How much does ticker clustering cost us? | left: events-per-ticker histogram (log y); right: forest plot of every headline median with ticker-block bootstrap 95% CI and naive CI side by side | n events, n tickers in title; n per interval | Block CIs indistinguishable from naive CIs — clustering costs nothing |

---

## Verification

Report a verification block per §10 covering, at minimum:

| Metric | n | Source | Repro |
|---|---|---|---|
| `flag_cross_session_extreme` count, (T0,T+1) | | `research/phase_9/t1_ca_detector.py:main` | `python -m research.phase_9.t1_ca_detector` |
| Integer-band share of flagged set | | same | same |
| `t0_close→t1_close` median and mean-simple, all four variants | | `research/phase_9/t2_sensitivity.py:main` | `python -m research.phase_9.t2_sensitivity` |
| `retrace_excursion` median at each horizon | | `research/phase_9/t3_retracement.py:main` | `python -m research.phase_9.t3_retracement` |
| Share `p_h < A` at each horizon | | same | same |
| Fixed-exit latency medians (L0…L30) | | `research/phase_9/t4_axis_grid.py:main` | `python -m research.phase_9.t4_axis_grid` |
| Ticker count, events-per-ticker median | | `research/phase_9/t5_clustered.py:main` | `python -m research.phase_9.t5_clustered` |
| Block-bootstrap 95% CI, pooled overnight median | | same | same |

Plus a filter waterfall (rows in / rows out / dropped / why) for every population restriction, and the config hash in every chart caption.

---

## Reporting

On completion, post:

1. **Corporate-action table** — flag counts per session pair, integer-band share, top-50 list, and the four-variant sensitivity table for `t0_close→t1_close` and `t0_close→t3_close` (n, median, mean log, mean simple, q01/q99 per cell).
2. **Retracement table** — `retrace_excursion` and `retrace_detection` quantiles at t0/t1/t2/t3, plus the level-crossing census (share below `A`, share below `p_det`), by era and detection segment, with block-bootstrap CIs.
3. **Axis separation table** — the `latency × hold × det_bin` grid, and separately the fixed-exit latency column with n attrition.
4. **Clustered inference table** — every headline median with naive and block-bootstrap 95% CI side by side, plus median-of-per-ticker-medians and share of tickers negative.
5. **Runway split table** — mode locations, empirical trough, and the anchor-knowable characterisation of the two populations.
6. Escalation check table — every row, observed value, pass/fail.
7. Verification block (§10).
8. Output file table with status filled in.
9. Commit list.

Every claim cites its chart. Every statistic carries n. **No recommendations. No characterisation of any result as good, weak, promising, or disappointing.** State the T+3 horizon ceiling explicitly wherever a retracement figure is reported.

---

## Approval Gate

Do not begin Phase 10 or any follow-on work until Cooper has reviewed results and given explicit approval.

---

## Appendix — T0 escalation row 1, fired and resolved

*Not part of the spec above. Recorded here because escalation row 1 triggered before any other work and the resolution changed the branch base.*

**Observed at T0 (2026-08-03), before any file was created:**

| Check | Observed |
|---|---|
| `phase-8-approved` tag | Present → `2b0d6235cdfb1c74bf6957ea4704f0f705fafec3` ("phase-8 A10.2-T7: digest + REPORT updated (items 15-21)", 2026-08-02) |
| `main` branch | **Absent.** No local branch named `main`; no remotes configured. |
| Repo trunk | `master` @ `295a0e17aa6b013ac35e5e55c19639983c4b1b59` ("phase-6b: approved by Cooper - formally recorded") |
| Had the trunk moved? | No — `master` was a strict ancestor of `phase/8` (`phase/8..master` = 0). It had never been advanced past phase-6b approval. |
| Trunk vs `phase/8` | `master..phase/8` = 19 commits, all Phase 8 work, unmerged |
| Phase 8 files on `master` | **0** (`results/phase_8`, `research/phase_8`, `config/phase_8.json`) |
| Phase 8 files on `phase/8` | 74 |

Cutting `phase/9` from the trunk as literally instructed would have produced a tree with no `a102_contamination.parquet`, no `a102_detection_anchors.parquet`, no `t5_markout_grid.parquet` and no `research/phase_8/` — making T2, T3 and T4 unrunnable. Reported as a hard stop; no fix attempted.

**Cooper's resolution (2026-08-03):** advance the trunk first, then cut. `master` was fast-forwarded to `phase/8` HEAD (`6dd52cf`) — a clean fast-forward, no merge commit, no history rewrite — completing the trunk-advance step skipped after Phase 8 approval. `phase/9` was then cut from `master`.

**Resulting base:** `master` == `phase/9` base == `6dd52cf9aa94dbf168b655b2f1c4f1cfec5ac015`.

The single commit between `phase-8-approved` and the base touches `results/reports/phase_8_report.md` (cross-phase copy, a standing CLAUDE.md requirement), `docs/Open-Items-Register.md`, and `docs/Research-Library-Map.md`. No measurement code, no artifact.

Other T0 preconditions, all read-only: `event_minute_bars_v2` = **45,925,350** rows (row 4 pass); zero passes over `filtered_trades`/`filtered_quotes` (row 2 pass); no computation run (row 3 n/a); no writes (row 13 pass).
