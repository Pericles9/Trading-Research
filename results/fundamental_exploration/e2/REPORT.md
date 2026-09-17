# Fundamental exploration E2 — momentum magnitude and high-participation duration — REPORT

**Branch:** `explore/fundamental-e2` (cut from `explore/fundamental-e1`) · **Config hash:** `981a74a2f2ed`
**Status:** complete (T0–T7 run, this is T8). **Not a phase, not a finding.** Descriptive only — no
response variable here is promoted to a universe criterion (D32 Amendment A1's sentence, the "DF-6"
gate, is unchanged; E2 computes no outcome/cost variable, so it cannot trigger that sentence's
condition). Per the brief's own §7, this report is documentation: any partition tested later against
these responses is either declared in writing before this report is read, or labelled exploratory.

Full task list, pre-registered decisions (DE-1/DE-2/DE-3), and their resolution with Cooper:
`prompts/fundamental_exploration_e2.md`.

---

## Decisions resolved before T2 ran

- **DE-1** (extend D4's `momentum_pct` exception to this descriptive use): **Cooper — extend it.**
  `momentum_pct` is read directly from `momentum_events_canonical` throughout E2, described only,
  never bucketing anything, never entering a computed statistic beyond this report's own distribution
  summaries. Phase 8's bucketing prohibition is untouched.
- **DE-2 confirmation window `C`:** **10 minutes** (the brief's own suggested value).
- **DE-2 censoring horizon:** **"end of tick data"** — Cooper's choice, *not* the brief's suggested
  "end of extended session". Per-event data availability (the event's own last available minute bar
  in `event_minute_bars_v2`), not a fixed clock boundary.
- **DE-2 volume basis:** **dollar volume** (`volume x vwap` per minute bar), not share volume — a
  correction Cooper made after reviewing the first (share-volume) version of `B_e`'s distribution.
  Applies to both the baseline and the trailing 10-minute moving average.
- **DE-2 baseline floor:** **deferred.** Cooper, after seeing `B_e`'s real distribution: the floor
  isn't a percentile of that distribution, and its relevance was unclear pending the duration build.
  `baseline_thin` is absent from every artifact below, not computed and not defaulted to `False`.
- **t0 eligibility:** confirmed directly — `t0` itself may qualify as the window's own end
  (`duration_min = 0` is a legitimate, real value, not an edge case to exclude).

---

## T0 — Population, membership, coverage

`research/fundamental_exploration/e2_t0_population.py` (reused from `e2_t0_population.py`; see also
E1's own T0/T2 for the shared join/coverage machinery). D1 = `in_scope = TRUE AND source_file =
'file1'`, confirmed at exactly 15,763 rows via `results/phase_5a/artifacts/sampling_frame.parquet`
(D1's own citation artifact — not a live view scan, `source_file` is computed on the fly in
`canonical.py`'s view and a live scan is pathologically slow, same class as E1-T0's finding).
`event_id` unique; D1 fully contained in `event_fundamentals` (0 missing).

Coverage by group by year, D1 only, chart `e2_t0/01_coverage_by_year.html`: `flg` 97.1–99.9%, `si`
95.1–98.8%, `shs` 70.0–80.5%, `spl` 29.7–47.9% (carries E1-T2's own finding: `spl_quality`
`'unavailable'` conflates a confirmed zero-splits event with a true data gap). **D1 has zero 2025
events — structurally, not by filtering: every 2025 in-scope event is `file2`.**

---

## T1 — Distance-to-boundary audit

`research/fundamental_exploration/e2_t1_boundary_audit.py`, chart
`e2_t1/01_boundary_distance_by_split.html`. `log10(event_volume / min_volume_threshold)` per D1 event
(n=15,763, 0 missing on either column), read from raw `momentum_events` under D4 Amendment A13's
exemption. Overall median 2.95 (~891x the q05 selection boundary), close to the brief's own cited
926x for the full population.

Reported against every fundamental split E2-T5/T6 use (shares-outstanding decile, dilution flag,
reverse-split flag, days-since-filing bucket, `si_quality`). **None flagged** (median distance <
half the overall median, n≥20) — the closest is `si_quality == 'unavailable'` (median 2.04, n=452),
still well clear of the flagging bar. Read, not asserted as proof: the momentum half of E2 is not
obviously reporting the selection filter rather than the market, at least by this diagnostic.

---

## T2a/T2 — Baseline and window build

`research/fundamental_exploration/e2_t2a_baseline.py` / `e2_t2_window.py`, chart
`e2_t2a/01_baseline_distribution.html`. `B_e` (mean of T-3..T-1's regular-hours dollar volume per
10-minute interval) built from `event_minute_bars_v2`'s own trading-session-relative `session_offset`
(no calendar arithmetic needed — confirmed directly against `first_trade_ts`: `minute_index 0` ==
04:00:00 America/New_York). 15,495 events (98.3%) have all 3 prior sessions present; 247 have 1 or 2;
21 (0.13%) have none (`B_e` undefined, carried as `NaN`). `B_e` spans 6+ orders of magnitude: p1=$122,
p5=$488, p10=$951, median=$22,781, p90=$1.36M, max=$1.48B per 10-minute interval.

Window end: the first minute at/after `t0` where the trailing 10-minute average dollar volume drops
to ≤3x `B_e` and stays there 10 consecutive minutes; censored at the event's own last available bar
otherwise. Two explicit assertions (no event-day bar in the baseline; no pre-`t0` bar in the
duration) both pass — the second caught a real few-second boundary bug on its first run (fixed: the
window-end minute's own timestamp is clamped to `t0_ns` exactly when the qualifying run starts in
`t0`'s own minute).

**15,742/15,763 events processed (21 skipped, no baseline buildable). 0% censored across the entire
population.** Verified via two independent manual traces (AAL, premarket detection; UAL, RTH
detection during the 2020-03-20 COVID crash) as a genuine, correct consequence of the flat, RTH-based
baseline — 3x an already-substantial full-session average is a permissive bar that most events clear
almost immediately — not a bug. Cooper reviewed this directly and confirmed proceeding with the
definition as specified.

---

## T3 — The two responses, on their own

`research/fundamental_exploration/e2_t3_describe_responses.py`, charts
`e2_t3/01_momentum_and_duration.html` and `02_survival_and_baseline_facet.html`.

`momentum_pct` (n=15,763): median 42.37%, p75 62.0%, p90 104.1%, max 861.5%. `duration_min`
(n=15,742): **52.2% exactly 0**, 47.8% positive (median among those 36.0 min, p75 111.1 min, p90
428.9 min, max 7,562.4 min ≈ 5.25 days). Censored share (0%) and `baseline_thin` status ("not
computed — floor deferred") stated in-panel, not only in a caption. Survival curve is the plain
empirical function here, not Kaplan-Meier — the two coincide when `censored_share` is 0. Duration by
`n_baseline_sessions`: the 1- and 2-session groups (140, 107 events) are small relative to the
3-session group (15,495), shown side by side, not pooled.

---

## T4 — The time-of-day confound, no fundamental variable

`research/fundamental_exploration/e2_t4_time_of_day.py`, chart `e2_t4/01_duration_by_time_of_day.html`.
`t0` session counts: `regular` 11,033, `pre_market` 4,630, `after_hours` 79. Median duration is 0 in
every segment (consistent with T3), but the upper tail differs sharply: p90 by segment is
`pre_market` 528 min, `regular` 79 min, `after_hours` 15 min — pre-market events that *do* run a
positive duration run far longer, exactly as a flat, un-normalized RTH baseline predicts (premarket
dollar volume is a small fraction of the RTH-based bar, so it takes far longer to accumulate enough
activity to cross back below 3x). The right-hand half-hour-bucket panel shows p75/p90 only — median
is 0 for nearly every bucket, and a log axis cannot render a zero.

---

## T5 — Fundamentals against momentum_pct

`research/fundamental_exploration/e2_t5_fundamentals_vs_momentum.py`, five charts in `e2_t5/`
(shares-outstanding decile, dilution flag, reverse-split flag, days-since-filing bucket,
`si_quality`), each a small-multiples grid (rows=event year, cols=detection-price decile, x-axis
within panel=split value) — same layout as E1-T4/`research/phase_13/chart_common.py` for this
cross-cut shape. 1,142 cells across the 5 splits; 411 (36.0%) below the display floor (20), shown
thin rather than hidden. `momentum_pct` overall: n=15,763, median 42.37%, p90 104.1% (same figures as
T3, restated here as the ungrouped reference point for the grids).

---

## T6 — Fundamentals against window duration

`research/fundamental_exploration/e2_t6_fundamentals_vs_duration.py`, six charts in `e2_t6/`: the same
5 splits against `duration_min` in the same year x price-decile grid (files 01–05, **linear** y-axis —
duration's 52% zero-mass cannot render on a log axis), plus one direct E2-T4 facet (file 06: each
split x `t0_segment`, kept separate from the year/price grid so it stays legible rather than a
four-way cross). 1,142 cells (year/price grid); 412 (36.1%) below the display floor.
`censored_share` is 0 in every cell — a population-level fact (T2/T3), not something that varies cell
to cell, stated once rather than 1,142 times.

---

## T7 — Price-decile arm zero

`research/fundamental_exploration/e2_t7_price_decile_arm_zero.py`, chart
`e2_t7/01_arm_zero_by_price_decile.html`. Both responses split by detection-price decile alone — no
fundamental variable, no year cross-cut. `momentum_pct`'s median runs from 46.25% (D0, cheapest) down
across the decile range (matching Phase 11's own finding that net edge is a function of price level);
`duration_min` stays dominated by the same zero-mass pattern T3/T4 already established, at every price
decile.

---

## Scope boundary, restated from the brief

Does not touch the 2025 slice (D1 has none — see T0). Does not construct market cap or float — shares
outstanding only, as filed, split-corrected where `spl_` indicates a reverse split intervened. Does
not touch `fin_`. Does not compute net expectancy, excursion, or any cost-unit quantity. Does not drop
censored, thin-baseline, or uncovered events. Does not combine `momentum_pct` and `duration_min` into
a single score — they are mechanically coupled by construction (§3: a longer window gives more time to
print a higher high) and are reported separately throughout. Does not promote anything to a universe
criterion.
