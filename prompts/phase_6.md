# Phase 6 — Measurement 1: Concentration Curves & the Detection Latency Budget

**Date:** 2026-07-23
**Baseline:** `phase-5a-approved` — dev sample v4 pinned (50 primary + 6 sidecar), universe decisions D1/D2 recorded in `docs/Universe-Decisions.md`
**Objective:** First analysis phase. Compute volume and move concentration over the event-day session, minimum-window statistics, and the opportunity-decay curve, for the D1 universe. Materialize the reusable minute-bar cache as a side product.
**Primary success metric:** The detection latency budget is a number — median minutes to 50% of the day's move, with distribution — supported by the chart contract below.

---

**Context:**

- **Universe:** D1 (`in_scope=TRUE AND source_file='file1'`, n=15,763). **Eligibility for this measurement, per D2:** event-day trades present — `substr(trades_bitmap, 4, 1) = '1'` (bitmap positions are T-3..T+3, position 4 = T+0). `clean_window` is **not** a filter here; the measurement is intraday T=0 and the 287 event-day-only events are fully eligible. Report the eligible count and the ineligible remainder in the waterfall.
- **Two-tier:** all development against dev v4 (`filtered_trades_dev_v4`). One budgeted full pass over `filtered_trades` after config freeze. Sidecar events are processed by the same code path — sessions absent from an event's data simply produce no bars; that is the expected behavior, not an error (D2).
- **Cache side product:** the full pass materializes `event_minute_bars_v1` for **all seven offsets T-3..T+3**, not just T=0, even though this measurement consumes only T=0. Justification: the scan cost of the 4.95B-row pass is dominated by the spine join, not the output width; offsets T-3..T-1 are the baseline material for §5.1 step 2, and T+1..T+3 feed measurements 2–4. Materializing them now avoids re-scanning the full table three more times. Same reuse pattern as Phase 4's quotes-session cache.
- **Session time base:** XNYS regular session for the event date (pinned `pandas_market_calendars==5.4.0` / `exchange_calendars==4.13.2`), seconds since open, normalized to [0,1] over the 09:30–16:00 session (half-days per XNYS schedule, not assumed). Pre/post-session prints are **excluded from bars** but counted: log the excluded row share per event; if any event has > 50% of its T=0 rows outside the session, list it in the report.
- **Definitions (fixed — do not reinterpret):**
  - **Minute bar:** per event × offset × session-minute: `n_trades`, `volume`, `vwap`, `last_price`, `high`, `low`, first/last trade timestamps. Minute index from session open per XNYS.
  - **Volume concentration curve:** per event, cumulative volume share vs. cumulative session-time share, on T=0 bars sorted by time (not sorted by size — this is a time-path curve, not a Lorenz curve).
  - **Move concentration curve:** per event, cumulative path length `Σ |log(last_price_m / last_price_{m-1})|` share vs. session-time share, T=0.
  - **Minimum-window statistics:** per event, the length in minutes of the shortest contiguous window containing X% of T=0 session volume, for X ∈ {25, 50, 75}.
  - **Opportunity-decay curve:** per event, `|cum_move(t)| / |open→close move|` where `cum_move(t) = log(last_price_t / open_price)`, evaluated per minute; open price = first in-session print. Pooled: median and quartiles across events per minute. **Headline number:** the minute at which the pooled median crosses 0.5.
- All queries touching `filtered_trades` join through `momentum_events_canonical` on `(ticker, event_date_canonical, ROUND(momentum_pct,2))` with `in_scope=TRUE`. DuckDB SQL, not pandas, for anything at tick grain.
- Chart rule (amended standard): population > 200 events → pooled curves + stratified per-event overlays (top/bottom `momentum_pct` deciles + seeded random 30, seed 42), full population in the sortable index. No per-event chart per event.
- Standing constraints per `CLAUDE.md` apply.

---

## Tasks

- [ ] **T0 — Approval housekeeping, branch, verification, prompt/config commit**
  Record Phase 5a approval per the established pattern: `results/phase_5a/digest.json` → `complete_approved`, tag `phase-5a-approved`, fast-forward `master`, cut `phase/6`. **Verification:** join both dev v4 event manifests to `momentum_events_canonical` on `(ticker, event_date_canonical, ROUND(momentum_pct,2))` — must match 56/56. This confirms the canonical key was used in 5a's materialization (the 5a report's §5 wording says `event_date`; resolve the ambiguity on the record). Commit `prompts/phase_6.md` and `config/phase_6.json` (bar grain, X thresholds, overlay seed/sizes, sensitivity rule — every tunable in config).
  - [ ] T0a — Commit. If the manifest join is not 56/56, hard stop (escalation row 1).

- [ ] **T1 — Eligibility waterfall**
  From `momentum_events_canonical`, D1 universe → T=0-trades-eligible per the bitmap rule. Write counts to `results/phase_6/artifacts/t1_eligibility.json`: D1 total (expect 15,763), eligible, ineligible (with their bitmap patterns tabulated). Escalate per row 2 if ineligible > 1% of D1.
  - [ ] T1a — Commit

- [ ] **T2 — Dev tier: minute-bar builder + measurement pipeline**
  Build `research/phase_6/build_minute_bars.py` and the measurement computations against `filtered_trades_dev_v4` (both cohorts). Verify: bar minute indices lie within the XNYS session for each date (0 violations), no duplicate (event, offset, minute) keys, sidecar events yield bars only for sessions their bitmaps say exist, runtime < 60s per pass. Produce dev-tier versions of every §T4 output and eyeball-render the dev-tier curves.
  - [ ] T2a — Commit dev-tier artifacts + verification JSON

- [ ] **T3 — Config freeze + budgeted full pass**
  Commit frozen config, then run the single full pass: materialize DuckDB table `event_minute_bars_v1` (all eligible D1 events × available offsets T-3..T+3). Log: total bar rows, distinct events per offset, wall time. Post-pass integrity: distinct T=0 events in bars must equal T1's eligible count exactly (escalation row 4).
  - [ ] T3a — Pre-run commit (config + code, per §12) · T3b — Post-run commit

- [ ] **T4 — Measurements** (computed from `event_minute_bars_v1`, no further full-table passes)
  - [ ] T4a — Per-event volume and move concentration curves → `results/phase_6/artifacts/concentration_curves.parquet` (event, minute, cum shares)
  - [ ] T4b — Minimum-window stats (25/50/75) per event → `min_window_stats.parquet`
  - [ ] T4c — Opportunity-decay per event + pooled per-minute quantiles → `opportunity_decay.parquet`; headline minutes-to-50% written to digest
  - [ ] T4d — **Opening-print sensitivity:** recompute T4b/T4c excluding minute 0. If the pooled median minutes-to-50%-move shifts by more than 2× (either direction), stop per escalation row 5 — both variants committed and charted before any budget number is reported as final
  - [ ] T4e — Sortable full-population index (`index.html` per standard §7): per event — eligibility, min-window stats, minutes-to-50%, momentum_pct, decile
  - [ ] T4f — Commit

- [ ] **T5 — Charts** (per Chart Contract; kaleido-verified before commit)
  - [ ] T5a–e — Charts 01–05 · T5f — Commit

- [ ] **T6 — Digest and report**
  `digest.json` per §11 with headline metrics (minutes-to-50%-volume, minutes-to-50%-move, both sensitivity variants). `REPORT.md` per the Evidence Standard — **description only; the agent does not state whether the concentration supports any strategy family. The latency-budget interpretation is Cooper's.**
  - [ ] T6a — Commit; working tree clean

---

## Escalation Criteria

Stop, commit, post results, await instruction.

| # | Condition | Threshold | 
|---|---|---|
| 1 | Dev v4 manifest join vs. canonical spine | ≠ 56/56 |
| 2 | Ineligible share of D1 | > 1% (157 events) |
| 3 | Bar integrity: out-of-session minute indices or duplicate keys | any |
| 4 | Distinct T=0 events in `event_minute_bars_v1` vs. T1 eligible count | any deviation |
| 5 | Opening-print sensitivity: minutes-to-50%-move median shift | > 2× |
| 6 | Dev-tier runtime | > 60s per pass |
| 7 | More than one full pass over `filtered_trades` | > 1 |
| 8 | Write to base tables, dev tables (v3 or v4), or data root | any |
| 9 | Calendar pin drift | ≠ 5.4.0 / 4.13.2 |

---

## Chart Contract

| # | File | Question | Encoding | n shown | Looks like this if wrong |
|---|---|---|---|---|---|
| 01 | `charts/01_volume_concentration.html` | How front-loaded is event-day volume? | x = session-time share, y = cum volume share; pooled median + IQR band; faceted by momentum_pct decile | Per-facet n in title | Curves hug the diagonal (no concentration) or a single step at t=0 (opening-print artifact — cross-check chart 05) |
| 02 | `charts/02_move_concentration.html` | How front-loaded is the price path? | Same encoding, cum path-length share | Same | Same failure modes |
| 03 | `charts/03_min_window_cdf.html` | How long a window holds 25/50/75% of the volume? | CDF of window length (minutes, log x), one trace per X | n per trace | Mass at full session length (no bursts) or at 1 minute for all X (artifact) |
| 04 | `charts/04_opportunity_decay.html` | How fast does the move get spent? | x = minutes since open, y = median + quartile band of realized-move fraction; horizontal 0.5 rule annotated with the crossing minute; both with/without-minute-0 variants overlaid | n, both variants labeled | Median never reaches 0.5 (open≈close events dominating — check |open→close| denominator distribution) or crosses at minute 1 in the with-minute-0 variant only |
| 05 | `charts/05_per_event_overlay.html` | Do pooled curves hide heterogeneity? | Per-event opportunity-decay traces: top decile, bottom decile, seeded random 30 (seed 42), color by group, low alpha | Group ns | One group's traces systematically off the pooled band — pooled median is masking a mixture |

Standard chart rules apply (§9). No findings without the supporting distributional chart.

---

## Output Files

| File | Description |
|---|---|
| `config/phase_6.json` | All tunables |
| `results/phase_6/artifacts/t1_eligibility.json` | Waterfall |
| DuckDB table `event_minute_bars_v1` | Reusable cache, all offsets |
| `results/phase_6/artifacts/*.parquet` | Per-event measurement outputs (gitignored, regenerable) |
| `results/phase_6/artifacts/*_summary.json` | Committed summaries incl. sensitivity |
| `results/phase_6/charts/01–05*.html` + `index.html` | Per contract + sortable index |
| `results/phase_6/digest.json`, `REPORT.md` | Per standard |

---

## Reporting

On completion, post: eligibility waterfall · bar-cache row/event counts per offset + wall time · headline table (minutes-to-50% volume and move, with and without minute 0, with quartiles) · min-window stats summary · escalation check table (all 9 rows) · verification block with filter waterfall D1 → eligible → bars → curves · output file table · commit list. Description only — no strategy-family recommendations.

---

## Approval Gate

Do not begin Measurement 2 scoping or any use of these numbers in labeling/detector work until Cooper has reviewed the charts and given explicit approval. On approval, tag `phase-6-approved`. The latency budget number is set by Cooper from chart 04, not by the agent.
