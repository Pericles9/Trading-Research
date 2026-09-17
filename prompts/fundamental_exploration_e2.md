# Fundamental exploration E2 — momentum magnitude and high-participation duration

**Date:** 2026-09-15 · **Type:** exploration brief. Minimal task list, same weight as E1.
**Status:** **not a phase.** Records no decision, tests no hypothesis, produces no finding.
**Population:** **D1 only** — `in_scope = TRUE AND source_file = 'file1'`, n = 15,763.
**Outputs:** `results/fundamental_exploration/e2/` · `charts/fundamental_exploration/e2/`. Branch
`explore/fundamental-e2`.
**Depends on:** E1's coverage cross-tab. If E1 has not run, E2-T0 produces it first.

---

## 0. What this is, and the one line it does cross

E1 crossed fundamentals against event characteristics only. **E2 adds two response variables measured on
the event itself**, so it sits one step closer to DF-6 than E1 did. It is still not an edge test: neither
response is knowable in real time, so neither can become an entry signal. What they *can* become is a
universe filter, which is exactly what DF-6 guards. **Nothing in E2 may be promoted to a universe criterion
without the DF-6 sentence being written first.**

Two responses:

| response | definition | source |
|---|---|---|
| **Momentum pct** | `(high − prev_close) / prev_close × 100`, the spine column, as always used | `momentum_events_canonical` |
| **High-participation window duration** | minutes from `t0` until 10-minute average volume falls back to **3× baseline**, baseline = the 3 prior sessions | `event_minute_bars_v2` |

---

## 1. Pre-registered decisions

**DE-1 — D4's `momentum_pct` exception is extended, for this brief only, to cover use as a response
variable in a descriptive study.**

D4 quarantines spine numerics and exempts `momentum_pct` on the grounds that *"it selects and stratifies
the universe, it does not measure anything within a phase."* E2 measures with it. Phase 8 separately
**prohibited `momentum_pct` as a bucketing variable**, because it is conditioned on the day's high and so
is not knowable in real time.

This extension is **narrow and must stay narrow**: `momentum_pct` may be a *described* quantity in E2. It
may not bucket anything, may not enter any computed statistic in any numbered phase, and Phase 8's
prohibition is untouched. **Cooper signs this or E2 uses a tick-derived recompute instead.**

**DE-2 — Window definition. Every number below is declared before the run, not chosen after seeing the
distribution.**

- **Baseline `B_e`** = total volume across sessions T-3, T-2, T-1, **regular hours**, divided by the number
  of 10-minute intervals in those sessions. Flat — no time-of-day matching, per Cooper. Tick-derived from
  `event_minute_bars_v2`; the spine's volume column is not used (D4).
- **Prior-session requirement:** at least **one** of T-3..T-1 present with non-zero regular-hours volume.
  `n_baseline_sessions` (0–3) is carried as a column and **every panel is faceted by it.** A one-session
  baseline is a different measurement from a three-session one.
- **Window start** = `t0`.
- **Window end** = the first minute after `t0` at which the trailing 10-minute average volume is
  **≤ 3 × `B_e`** *and stays at or below it for **C** consecutive minutes.* **Suggested C = 10. Cooper
  sets it.** Without the confirmation rule this measures the first dip in a noisy series, not the end of
  participation, and the duration distribution will be dominated by flicker.
- **Censoring horizon** = end of the event-day **extended** session. **Cooper confirms.** Events with no
  qualifying end are **censored at the horizon**, carried, and reported as their own share.
- **Baseline floor:** events whose `B_e` falls below a declared floor are flagged `baseline_thin` and
  carried. **Cooper sets the floor.** These are names that print near-nothing on quiet days, where
  3× baseline is a trivially low bar and the duration is not measuring what the definition intends.
- **Duration** = window end − `t0`, in minutes.

**DE-3 — No mean is taken across censored events.** Median only while the censored share leaves the median
defined; otherwise the survival curve is the reported object. This is not statistical decoration —
averaging over right-censored durations biases them downward by construction, and the censored share here
is expected to be large.

---

## 2. The confound that has to be measured first, because it is structural

The universe filter is `log_vol ~ log_mom`, quantile `q = 0.05`, keep where
`log_vol > log_vol_threshold` (`filter_events_power_law.py:42,43,62`). **The universe is selected on volume
conditional on momentum.**

That makes momentum and anything correlated with volume conditionally dependent *inside the sample* even if
they are independent in the population — a selection artefact, not a finding. Shares outstanding is
correlated with volume. **So "fundamentals against momentum pct" is confounded by the universe's own
construction before any data is read.**

The good news is that it is cheaply bounded. The q05 closure already established the boundary is extremely
permissive: **median event sits 926× above the threshold, only 1.51% within 2×.** If the fundamental
deciles all sit far from the line, the artefact is negligible and can be dismissed with evidence.

**E2-T1 computes `log10(event_volume / min_volume_threshold)` per event and reports its distribution by
fundamental decile.** This is a **selection-mechanism audit**, the class A9.2 permits for these columns —
diagnostic only, entering no other computed quantity.

**If a fundamental decile's distance-to-boundary distribution sits materially closer to the line than the
others, the momentum half of E2 is reporting the filter, not the market**, and that must be said in the
report rather than discovered later.

---

## 3. One coupling to name before the charts are read

`momentum_pct` is a prior-close-to-**high** measure. A longer high-participation window means more time in
which to print a higher high. **The two responses are mechanically coupled, positively, by construction.**
They are not two independent views of the same fundamental variable, and any panel showing both must say
so. Report them separately; do not build a combined score.

---

## 4. Tasks

**E2-T0 — Population, membership, coverage.**
D1 = `in_scope = TRUE AND source_file = 'file1'`. Assert the count in code. Join `event_fundamentals`;
assert set equality against the D1 event set in both directions. Report fundamental coverage by group by
year, carried forward from E1 if it exists.

**E2-T1 — Distance-to-boundary audit.** §2. Run this **before** anything is read off a momentum chart.

**E2-T2 — Build the window.**
Per event, from `event_minute_bars_v2`: `B_e`, `n_baseline_sessions`, `baseline_thin`, the trailing
10-minute volume series from `t0`, the window end under DE-2, `duration_min`, and `censored`. Assert no
event-day bar enters the baseline and no pre-`t0` bar enters the duration. Write one row per event.

**E2-T3 — Describe the two responses on their own.**
Distributions of `momentum_pct` and `duration_min`. **State the censored share and the `baseline_thin`
share in the same panel as the distribution, not in a caption.** Survival curve for duration. Duration
faceted by `n_baseline_sessions`.

**E2-T4 — The time-of-day confound, made visible.**
A flat baseline ignores the intraday volume U-shape, so a morning event has further to fall than an
afternoon one. **Every duration panel in E2-T5 and E2-T6 is faceted by `t0` session segment (pre-market /
regular / after) and by `t0` half-hour bucket.** E2-T4 establishes the size of the effect on its own,
without any fundamental variable, so the later panels can be read against it.

**E2-T5 — Fundamentals against momentum pct.**
`shs_shares_outstanding` decile · `flg_dilution_form_before_t0` · `spl_reverse_split_365d` ·
`flg_lag_ns` bucket · `si_` where covered. **Within year, within detection-price decile.** Distribution per
cell with cell n shown. Read against E2-T1's audit.

**E2-T6 — Fundamentals against window duration.**
Same splits, same within-year within-price-decile structure, plus the E2-T4 facets. Censored share reported
per cell — a cell whose censored share differs from its neighbours is reporting censoring, not duration.

**E2-T7 — Price-decile arm zero.**
Both responses split by detection-price decile alone, no fundamental variable. Phase 11 established net
edge is a function of price level; if the price decile reproduces everything the fundamental splits show,
**the fundamental layer earned nothing here** — which is a real result, obtained cheaply, and the check
most likely to come back against the work that motivated it.

**E2-T8 — Report.**
`results/fundamental_exploration/e2/REPORT.md`. Describes the pictures. No interpretation, no
recommendations, no findings section.

---

## 5. Conventions carried

Dark theme · per-task chart subfolders · distribution before any aggregate · outliers flagged, never
deleted · `unavailable`, zero, and censored are three different states and are never collapsed · every
membership and coverage claim asserted in code, not prose · the agent describes the picture, Cooper decides
what it means.

---

## 6. What this does not do

- Does not touch the 2025 slice. Prior-session coverage there is ~1% and the baseline cannot be built.
- Does not construct market cap or float. Shares outstanding only, as filed, split-corrected where
  `spl_` says a reverse split intervened.
- Does not touch `fin_`.
- Does not compute net expectancy, excursion, or any cost-unit quantity.
- Does not drop censored, thin-baseline, or uncovered events.
- Does not combine the two responses into a single score.
- Does not promote anything to a universe criterion.

---

## 7. Two risks worth stating

**The momentum half may be structurally uninterpretable.** §2 decides that, and it decides it in ten
minutes. If the audit comes back badly, the duration half still stands on its own and the momentum half is
recorded as blocked by the universe construction — which is worth knowing and cheap to learn.

**E2 seeds priors harder than E1 did**, because these are response variables. After reading it, no split
can honestly be called pre-registered unless it was written down first. Same rule as E1: E2 is
documentation; anything tested later is either declared before this report is read or labelled exploratory.

---

## 8. Corrections and gates recorded at T0 time, before code ran

Per this repo's reuse-before-build / cite-and-verify discipline (same practice as
`prompts/fundamental_exploration_e1.md` §7):

- **§5 "Dark theme."** Same drafting slip as E1 §3 — no dark-theme chart exists anywhere in this repo's
  history (phase_6/8/9/11/13, fundamentals_f1 all use the same validated light palette, INK on SURFACE).
  Not re-litigated here; E2 uses the light palette, copied by value into
  `research/fundamental_exploration/chart_common.py` (E1's own module, reused, not duplicated).
- **"DF-6" resolved.** `docs/Universe-Decisions.md` D32 ("No fundamental column is put against any
  outcome variable under Build F1", gate `prompts/fundamentals_f1.md` DF-6) already carries **D32
  Amendment A1** — the written sentence Cooper signed off 2026-09-13: *"If a partition of the universe on
  a pre-`t0` observable produces a sub-population whose net-expectancy distribution clears the round-trip
  cost stack ... then D24 and D25's arithmetic reopens ... If no partition does, the fundamental layer is
  documentation and the line stays closed."* E2 computes no outcome variable at all (§6: "does not
  compute net expectancy, excursion, or any cost-unit quantity"), so nothing in E2 can trigger this
  sentence's condition — the §0 warning is a forward guardrail against a *later* step, not a gate E2 itself
  needs to clear.
- **Branch.** Cut from `explore/fundamental-e1` (not `master`) — E2 depends on E1's completed work
  (`common.py`/`chart_common.py` plumbing, `detection_price`, coverage-by-year), and `master` does not
  have E1 merged yet. `origin/master` merged into this branch immediately after cutting it, to pick up
  Phase 13's closure (D37), `D32 Amendment A1` itself, and a data-root path bug fix in
  `fundamentals_f1/common.py` that `research/fundamental_exploration/common.py` shared (same bug class,
  fixed here in the same style: routed through `resolve_data_root()`, not a cwd-relative literal).

**Genuinely blocking, not resolved by verification alone — DE-1 and three of DE-2's parameters were
Cooper's to set, not mine to assume. Asked and resolved 2026-09-15 (`config/fundamental_exploration_e2.json`
`cooper_pending`):**

1. **DE-1 sign-off — RESOLVED: extend D4's exception.** `momentum_pct` read directly from
   `momentum_events_canonical`, described only, never bucketing, never entering a computed statistic in
   any numbered phase.
2. **DE-2 confirmation window `C` — RESOLVED: 10 minutes**, the brief's own suggested value.
3. **DE-2 censoring horizon — RESOLVED, but NOT the brief's suggested default.** Cooper chose
   **"end of tick data"**: per-event data availability (the last minute bar actually present for that
   event in `event_minute_bars_v2`), not a fixed clock boundary like the extended session's close. An
   event with no qualifying window end by its own last available bar is censored there.
4. **DE-2 baseline floor — still PENDING.** Cooper's instruction: compute `B_e`'s actual distribution
   first (this does not depend on `C`, the horizon, or a floor value — it only needs the 3 prior sessions'
   regular-hours volume), then set the floor from real percentiles rather than a blind guess. E2-T2's full
   window/duration/censoring build stays blocked until this lands; the baseline-only computation is not
   blocked and runs first.

**Two corrections from live verification, before any E2 code ran (same discipline as item 1 above):**

- `source_file` (D1's own population rule) is **not a stored column** — `src/data/canonical.py` computes
  it on the fly (`CASE WHEN me.date IS NOT NULL THEN 'file1' WHEN me.event_date IS NOT NULL THEN 'file2'
  END`) inside `momentum_events_canonical`'s view definition. A live `COUNT(*)` filtering on it joins
  `filtered_trades`/`filtered_quotes` and is pathologically slow (same class as E1-T0's finding).
  `results/phase_5a/artifacts/sampling_frame.parquet` — D1's own citation artifact — already carries
  `source_file` for exactly this population, confirmed at 15,763 rows directly. Used instead of a live
  scan.
- `log_vol`, `log_mom`, `log_vol_threshold` (cited in §2 as `filter_events_power_law.py:42,43,62`) are
  **not persisted column names** — they're transient pandas variables inside that script. Only their
  downstream product, `min_volume_threshold` (`= 10**log_vol_threshold`), is written to disk, as a column
  on the raw `momentum_events` table (confirmed non-null on all 23,268 rows). E2-T1's audit reads
  `event_volume` and `min_volume_threshold` from `momentum_events` directly, under D4 Amendment A13's
  exemption — `data/collection_scripts/filter_events_power_law.py` itself is on CLAUDE.md's banned-
  execution list and is never run.
