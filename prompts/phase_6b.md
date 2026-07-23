# Phase 6b — Measurement 1 Redo: Concentration & Latency Budget over the Full Extended Day

**Date:** 2026-07-23
**Baseline:** tip of `phase/6` (unapproved). `master` remains at `phase-5a-approved`.
**Objective:** Supersede Phase 6's RTH-only measurement with the same measurement family computed over the full extended trading day (premarket + RTH + post-market). Relabel — do not delete — Phase 6's outputs. Record the session-scope decision as D3.
**Primary success metric:** The latency budget re-expressed on the extended-day clock, including the headline distribution "fraction of the prev_close→high move already realized by the 09:30 open," supported by the chart contract.

---

**Context:**

- **Why this phase exists:** Phase 6 measured RTH only. 736/15,763 events (4.7%) have >50% of their event-day prints outside the regular session (top of list 95–99%), and the archive's universe was selected on `momentum_pct = (high − prev_close)/prev_close`, where the high may occur premarket. Cooper's determination: extended hours are structurally important to these names and cannot be excluded. Phase 6's numbers are not wrong — they are RTH-conditional answers to a question that needed the full day.
- **D3 (record verbatim in `docs/Universe-Decisions.md`):** *The analysis clock for intraday measurements is the full extended trading day — premarket, regular session, and post-market, per XNYS schedule with extended-hours bounds — with every bar tagged by session segment. RTH-only variants may be produced as labeled comparability views but are never the primary measurement. Phase 6's RTH-only results are superseded by Phase 6b and retained under `results/phase_6_rth_only/`.*
- **Disposition of Phase 6:** never approved. Its digest status becomes `superseded_rth_only`. No `phase-6-approved` tag is ever created. Its artifacts, charts, and the `event_minute_bars_v1` table are retained untouched (v1 remains a valid RTH-conditional cache).
- **Universe:** D1 (n=15,763). Eligibility per D2 unchanged: event-day trades present. Phase 6 T1 established this is non-binding (15,763/15,763); re-verify, don't re-derive.
- **Session structure (fixed):**
  - Segments per event date, in `America/New_York`: **premarket** 04:00→RTH open, **rth** RTH open→RTH close, **post** RTH close→post end. RTH open/close and any early-close times come from the pinned XNYS schedule (`pandas_market_calendars==5.4.0`, request the schedule with pre/post columns; if the installed version does not expose pre/post bounds, use 04:00 ET start and 20:00 ET end — 17:00 ET post end on early-close days — and log that fallback in the report).
  - **Minute index runs from 04:00 ET** (index 0) to post end. Full day ≈ 960 minutes on a normal session.
  - **Timezone rule — critical:** session-date assignment and segment bounds are computed in `America/New_York` (DST-aware), NOT by casting the UTC `sip_timestamp` to a date. The UTC cast used by prior phases misassigns EST-winter post-market prints after 19:00 ET to the next calendar day. Rows outside 04:00–post-end ET on the event date are excluded and counted (expected to be near zero).
- **Definitions (fixed — do not reinterpret):**
  - **Minute bar:** as Phase 6 (`n_trades`, `volume`, `vwap`, `last_price`, `high`, `low`, first/last ts) plus `segment ∈ {premarket, rth, post}`. Table: **`event_minute_bars_v2`**, all offsets T-3..T+3, same one-budgeted-pass justification as Phase 6 (baseline material and measurements 2–4 need the same cache on the same clock).
  - **Volume / move concentration curves:** as Phase 6, but over the extended-day minute grid; time share normalized over the event date's full extended span.
  - **Minimum-window stats:** as Phase 6 (X ∈ {25,50,75}), extended day.
  - **Opportunity-decay — PRIMARY (new anchor):** per event, `realized(t) = log(last_price_t / prev_close) / log(day_high_ext / prev_close)`, where `prev_close` is the spine's value and `day_high_ext` is the maximum trade price across the full extended event day. Denominator is positive by universe construction (momentum_pct > 0). Pooled per-minute median + quartiles. **Headlines:** (a) minute since 04:00 at which the pooled median crosses 0.5; (b) the distribution across events of `realized(09:30 open)` — how much of the move is done before RTH begins; (c) distribution of the ET time-of-day of `day_high_ext`.
  - **Opportunity-decay — comparability variant:** Phase 6's RTH open→close definition, computed on v2's rth-segment bars, reported alongside so 6 and 6b are directly comparable. Labeled `rth_legacy` everywhere it appears.
- All tick queries join through `momentum_events_canonical` on `(ticker, event_date_canonical, ROUND(momentum_pct,2))`, `in_scope=TRUE`. DuckDB SQL at tick grain. Two-tier: dev v4 first (its tables carry ETH rows — no time filter was applied at materialization), config freeze, one budgeted full pass.
- Chart rule: population > 200 → pooled + stratified overlays (top/bottom deciles + seeded random 30, seed 42), full population in the sortable index.
- Standing constraints per `CLAUDE.md`.

---

## Tasks

- [ ] **T0 — Branch, supersession housekeeping, prompt/config commit**
  Cut `phase/6b` from the tip of `phase/6`. Then: (1) `git mv results/phase_6 results/phase_6_rth_only` — a rename, no file contents change; (2) set `results/phase_6_rth_only/digest.json` status → `superseded_rth_only` with a pointer to this phase; (3) append the supersession note + D3 to `docs/Universe-Decisions.md`; (4) update `docs/Open-Items-Register.md` if any Phase 6 items reference the old path. Commit `prompts/phase_6b.md` + `config/phase_6b.json` (segment bounds source, fallback hours, X thresholds, overlay seed, every tunable).
  - [ ] T0a — Verify: old artifacts all present under the new path (file count and byte sizes match pre-move), `event_minute_bars_v1` untouched. Commit.

- [ ] **T1 — Eligibility re-verification + prev_close guard**
  Re-verify D1 → T=0-eligible = 15,763 (expect non-binding, per Phase 6 T1). New guard for the primary decay anchor: `prev_close` present and > 0 for all 15,763. Write both to `results/phase_6b/artifacts/t1_eligibility.json`. Escalate per row 5 on any prev_close failure.
  - [ ] T1a — Commit

- [ ] **T2 — Dev tier: v2 bar builder + full measurement pipeline**
  Build against `filtered_trades_dev_v4`, both cohorts. Verify: 0 duplicate `(event, offset, minute)` keys; every bar's minute index within [0, day-length) for its date; every bar's segment consistent with the ET schedule; sidecar behavior per D2; runtime < 60s. **Timezone cross-check:** count dev rows whose `America/New_York` event-date assignment differs from the legacy UTC-cast assignment; log the count and example timestamps. Produce dev-tier versions of all T4 outputs and eyeball-render the curves.
  - [ ] T2a — Commit dev artifacts + verification JSON

- [ ] **T3 — Config freeze + budgeted full pass**
  Frozen-config commit, then the single full pass over `filtered_trades`: materialize `event_minute_bars_v2` (all eligible events × available offsets, extended-day grid, segment-tagged). Log total bar rows, distinct events per offset, per-segment row and volume shares (population level), wall time, and the population count of ET-vs-UTC date reassignments. Post-pass: distinct T=0 events = 15,763 exactly (row 3); every event present in v1's T=0 must be present in v2's T=0 (row 4 — ETH is a superset of RTH, a missing event means a builder bug).
  - [ ] T3a — Pre-run commit · T3b — Post-run commit

- [ ] **T4 — Measurements** (from `event_minute_bars_v2` only; no further full passes)
  - [ ] T4a — Volume + move concentration curves, extended day → `concentration_curves_v2.parquet`
  - [ ] T4b — Min-window stats (25/50/75) → `min_window_stats_v2.parquet`
  - [ ] T4c — Per-event segment volume shares (premarket / rth / post) → `segment_shares.parquet`
  - [ ] T4d — Opportunity-decay, primary anchor: per-event curves + pooled quantiles; headlines (a)(b)(c) to digest. Count and list events where `day_high_ext ≤ prev_close` (breaks the denominator; expected 0 by construction — escalate per row 5 if > 0.1%)
  - [ ] T4e — `rth_legacy` comparability variant, same outputs as Phase 6's T4c, labeled
  - [ ] T4f — Sortable full-population index: eligibility, segment shares, min-window stats, realized-at-0930, minutes-to-50% (primary and rth_legacy), high time-of-day, momentum_pct, decile
  - [ ] T4g — Commit

- [ ] **T5 — Charts** (per contract; kaleido-verified)
  - [ ] T5a–g — Charts 01–07 · T5h — Commit

- [ ] **T6 — Digest and report**
  `digest.json` with headlines (a)(b)(c) plus the rth_legacy crossing for comparison to Phase 6's 52/57. `REPORT.md` per Evidence Standard — description only; the latency-budget interpretation and any premarket-vs-RTH strategy implication are **Cooper's, from the charts**.
  - [ ] T6a — Commit; working tree clean

---

## Escalation Criteria

Stop, commit, post, await instruction.

| # | Condition | Threshold |
|---|---|---|
| 1 | Relabel integrity: any old-phase-6 file missing/changed under the new path, or v1 table touched | any |
| 2 | Segment-bound source: XNYS schedule lacks pre/post AND fallback hours produce any bar outside [04:00, post end) ET | any |
| 3 | Distinct T=0 events in v2 vs. 15,763 | any deviation |
| 4 | Any v1 T=0 event absent from v2 T=0 | any |
| 5 | `prev_close` missing/≤0, or `day_high_ext ≤ prev_close` | > 0.1% of events (or any prev_close failure) |
| 6 | Dev-tier runtime | > 60s per pass |
| 7 | Full passes over `filtered_trades` | > 1 |
| 8 | Write to base tables, dev tables, v1 bars, or data root | any |
| 9 | Calendar pin drift | ≠ 5.4.0 / 4.13.2 |

---

## Chart Contract

| # | File | Question | Encoding | n shown | Looks like this if wrong |
|---|---|---|---|---|---|
| 01 | `charts/01_volume_concentration_ext.html` | How front-loaded is volume on the extended-day clock? | x = extended-day time share, y = cum volume share; pooled median + IQR; vertical rules at RTH open/close; faceted by decile | per-facet n | Hugs diagonal; or a cliff exactly at the 09:30 rule with zero premarket mass in every facet — suspect collection-side ETH gaps, cross-check chart 06 |
| 02 | `charts/02_move_concentration_ext.html` | Same for the price path | same encoding, cum path-length share | same | same |
| 03 | `charts/03_min_window_cdf_ext.html` | Shortest window holding 25/50/75% of extended-day volume | CDF, log-x minutes, one trace per X | n per trace | mass at 1 min for all X, or at full day |
| 04 | `charts/04_opportunity_decay_ext.html` | When does the prev_close→high move happen? | x = minutes since 04:00 ET, y = median + quartile band of realized fraction; rules at 09:30/16:00; 0.5 crossing annotated; median realized-at-09:30 annotated; `rth_legacy` median overlaid, clearly labeled | n, variants labeled | Median starts near 1.0 at 04:00 (gap events where prev_close→high completed before any prints — check first-print times) or never departs the rth_legacy curve (ETH added nothing — cross-check chart 06) |
| 05 | `charts/05_per_event_overlay_ext.html` | Does the pooled curve hide a mixture? | per-event primary-decay traces: top decile 30 / bottom decile 30 / seeded random 30, low alpha, rules at 09:30/16:00 | group ns | one group systematically off the pooled band |
| 06 | `charts/06_segment_volume_shares.html` | How much of the tape is premarket / RTH / post? | per-event share distributions, one histogram per segment + population totals annotated | n=15,763 | premarket histogram is a spike at exactly 0 — ETH rows absent from collection, not from the market; escalate to Cooper in the report before any premarket claim |
| 07 | `charts/07_high_time_of_day.html` | When is the extended-day high made? | histogram of ET clock time of `day_high_ext`, rules at 09:30/16:00 | n=15,763 | uniform (no structure) or a bar exactly at 04:00 (first-print artifact) |

Standard §9 rules apply. No findings without the distributional chart.

---

## Output Files

| File | Description |
|---|---|
| `results/phase_6_rth_only/` | Phase 6's outputs, renamed, digest `superseded_rth_only` |
| `docs/Universe-Decisions.md` | D3 + supersession note appended |
| `config/phase_6b.json` | All tunables |
| DuckDB table `event_minute_bars_v2` | Extended-day cache, all offsets, segment-tagged (v1 retained) |
| `results/phase_6b/artifacts/*.parquet` | Per-event outputs (gitignored, regenerable) |
| `results/phase_6b/artifacts/*_summary.json`, `t1_eligibility.json` | Committed summaries |
| `results/phase_6b/charts/01–07*.html` + `index.html` | Per contract |
| `results/phase_6b/digest.json`, `REPORT.md` | Per standard |

---

## Reporting

On completion, post: relabel verification · eligibility + prev_close guard · v2 cache counts per offset, per-segment population shares, wall time, ET-vs-UTC reassignment count · headline table — (a) crossing minute since 04:00, (b) realized-at-09:30 distribution summary (median, quartiles, share of events > 0.5), (c) high time-of-day summary, plus rth_legacy crossing vs. Phase 6's 52/57 · min-window summary · escalation table (all 9 rows) · verification block with waterfall D1 → eligible → v2 bars → curves · output table · commit list. Description only.

---

## Approval Gate

Do not begin Measurement 2 scoping or any use of these numbers in labeling/detector work until Cooper has reviewed the charts and given explicit approval. On approval, tag `phase-6b-approved` and fast-forward `master` (this carries the supersession relabel and D3 with it). The latency budget — and the premarket-vs-RTH read — are set by Cooper from charts 04/06/07, not by the agent.
