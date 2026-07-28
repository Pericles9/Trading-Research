# Phase 6b — Amendment 8 (A8.2): Resumption on the Tick-Only Anchor

> **STATUS: APPROVED by Cooper 2026-07-28** (draft reviewed and approved as written; the four proposed decisions below were accepted). Encodes (a) the A8.2 terms recorded verbatim in `results/phase_6c/REPORT.md:138`, (b) Cooper's anchor decision (tick T-1 RTH close), (c) the standard phase scaffolding. Committed as the A6.2 start commit.
>
> **Resolved decisions** (were the draft's `[CONFIRM]` items): (1) the A6.2 / A6.3 task split below is the operative reading of "resumes at A6.2/A6.3"; (2) `has_t_minus_1_rth = FALSE` events are flag-and-report — excluded from the *primary* decay population only, retained for concentration / min-window / segment / `rth_legacy`, no fallback anchor; (3) escalation thresholds set to denom-nonpositive **1.0%**, dup-print **0.1%** per event, `has_t_minus_1_rth = FALSE` not an escalation; (4) chart 08 is dropped (don't add the basis-diagnostic chart — the committed contract ran to 07).

**Date:** 2026-07-28
**Baseline:** tip of `phase/6b` (`539b46d`, the A6.1 full stop). `phase-6c-approved` and `phase-7-approved` both now exist — the two gate preconditions are met. `master` remains at `phase-5a-approved` and fast-forwards only at `phase-6b-approved` (per `phase_6b.md`'s own gate + the phase-6c digest note).
**Objective:** Complete Phase 6b — the extended-day concentration & latency-budget measurement — under D4. The measurement that stopped at A6.1 was anchored on the spine's `prev_close`, now permanently quarantined. This amendment reworks the opportunity-decay anchor to a **tick-only** basis, re-validates on the dev tier, runs the one budgeted full pass (never run — 6b stopped before T3), and produces the T4–T6 deliverables.
**Primary success metric:** `event_minute_bars_v2` materialized (extended-day, 15,763 T=0 events, v1 a strict subset), the tick-anchored opportunity-decay crossings reported with their `rth_legacy` comparability overlay, and a D4-clean sweep of all 6b code — zero spine-numeric computation-class hits surviving.

---

## Context

- **Why the anchor changed.** 6b's `compute_primary_opportunity_decay` computed `realized(t) = log(last_price_t / prev_close) / log(day_high_ext / prev_close)`. `prev_close` is a spine numeric column, quarantined by **D4** (`docs/Universe-Decisions.md`). D4 closed defect #4 by *severance* — the spine's numeric columns are never certified, tick data is the sole source. So the anchor must be replaced, not the code merely re-run.
- **The anchor (Cooper's decision, 2026-07-28).** The `prev_close` base becomes **`tick_close_t_minus_1_rth`** — the `last_price` of the last bar at `session_offset = -1` within `segment IN ('premarket','rth')` (the last trade at or before the T-1 RTH close), sourced from `event_minute_bars_v2`. This is the direct tick analog of `prev_close` and is already derived in `a61_basis_confirmation_rerun.py:49-55`. `day_high_ext` (`MAX(bar.high)` over the T+0 extended day) is already tick-derived and unchanged.

  Reworked primary decay: `realized(t) = log(price_ffill_t / tick_close_T-1_RTH) / log(day_high_ext / tick_close_T-1_RTH)` — **both inputs tick-only, D4-compliant.**
- **A8.2 terms, verbatim** (`results/phase_6c/REPORT.md:138`): "resumes at A6.2/A6.3 (already tick-only) under the A8.2 terms — chart 08 dropped, duplicate-print counters added to the single budgeted full pass, a spine-numeric-column sweep of `research/phase_6b/` and `config/phase_6b.json` required before the config re-freeze commit."
- **The two Phase 7 t8 columns.** `momentum_events_canonical` now carries `flag_eth_dominant_t0` and `t0_eth_row_share` (stage t8). The A6.2a sweep treats these as **flag/annotation columns, not quarantined numerics** (`t0_eth_row_share` is tick-derived). They are annotations — no measurement excludes flagged events by default this phase.
- **What is done / not done.** T0 (relabel, D3), T1 (eligibility), T2 (dev-tier v2 builder + pipeline), A5.1/A6.1 (basis tests, now superseded) are complete and committed. **`event_minute_bars_v2` (full cache) was never built** — 6b stopped before T3. Dev-tier `event_minute_bars_dev_v2` + dev artifacts exist and are valid.
- **Standing constraints.** `CLAUDE.md` applies. Extended-day clock per **D3** (`event_minute_bars_v2`, the tz-aware `America/New_York` builder), never the RTH-only v1. One budgeted full pass over `filtered_trades`, dev tier excepted. Reads of the canonical view still trigger the `trades_ingested`/`quotes_ingested` scans (Phase 7 finding) — source eligibility from the frozen D1 artifact, not a live view count.

---

## Tasks

- [ ] **A6.2 — D4 rework, sweep, dev re-validation, config re-freeze** *(no full-table pass)*
  - [ ] **A6.2a — Spine-numeric sweep of `research/phase_6b/` + `config/phase_6b.json`.** Same method as Phase 7 T1 (enumerate the 16 non-`momentum_pct` spine numerics; AST/token scan; classify each hit `display_only` / `universe_selection` / `computation`, more-severe-on-ambiguity). The two t8 columns are flag/annotation, not quarantined. Write `results/phase_6b/artifacts/a62_d4_sweep.json`. **Every `computation`-class hit must be eliminated by A6.2b** (or escalate). Superseded scripts `a51_/a61_basis_confirmation*.py` are diagnostic-only and out of the measurement path — recorded in the sweep as retired, not reworked.
  - [ ] **A6.2b — Rework `measurements_v2.py`** to the tick anchor. Replace every `prev_close` read in the decay path with `tick_close_t_minus_1_rth` (derived from `event_minute_bars_v2`, offset −1, segment ∈ {premarket, rth}, max-minute `last_price`). New eligibility: `has_t_minus_1_rth` (a T-1 RTH session with ≥1 trade). `denom_nonpositive` ⇔ `day_high_ext ≤ tick_close_T-1_RTH`. No spine column enters any computed quantity.
  - [ ] **A6.2c — Dev re-validation.** Re-run the reworked pipeline against `event_minute_bars_dev_v2` (both cohorts), 60s ceiling, 0 duplicate keys, dev decay curves rendered. Report `n` with `has_t_minus_1_rth = FALSE` and `n denom_nonpositive`. Commit dev artifacts.
  - [ ] **A6.2d — Config re-freeze.** Rewrite `config/phase_6b.json`: **remove** the `prev_close` guard tunables, **add** the tick-anchor definition (offset/segment/reduction), the dup-print strict-key spec, and note chart 08 is dropped. Commit frozen config + this approved prompt as the **A6.2 pre-run commit**.

- [ ] **A6.3 — Budgeted full pass + measurements + charts + digest/report**
  - [ ] **A6.3a (T3) — The single full pass.** Materialize `event_minute_bars_v2` (all eligible × available offsets, extended-day, segment-tagged) in one pass over `filtered_trades`, **with strict-key duplicate-print counters** (A8.2; the 6c A8/T3″ strict key). Post-pass: distinct T=0 = 15,763 (row 3); every v1 T=0 event present in v2 T=0 (row 4). Pre-run + post-run commits.
  - [ ] **A6.3b (T4) — Measurements** from `event_minute_bars_v2` only: concentration curves, min-window (25/50/75), segment shares, opportunity-decay (tick-anchor **primary** + `rth_legacy` comparability, both labeled), sortable full-population index. Report the primary crossing and the `rth_legacy` crossing (comparable to Phase 6's 52/57). Count/list `denom_nonpositive` and `has_t_minus_1_rth = FALSE` events.
  - [ ] **A6.3c (T5) — Charts 01–07**, kaleido-verified. **Chart 08 dropped** (A8.2). Chart 04's anchor label is `tick_close_T-1_RTH`, not `prev_close`.
  - [ ] **A6.3d (T6) — Digest + REPORT** (+ `results/reports/phase_6b_report.md` copy). Description only — the latency-budget and premarket-vs-RTH reading is Cooper's, from the charts. Commit; working tree clean.

---

## Escalation Criteria

Stop, commit, post, await instruction. (Supersedes `phase_6b.md`'s table where rows overlap.)

| # | Condition | Threshold |
|---|-----------|-----------|
| 1 | A6.2a sweep: any `computation`-class spine-numeric hit surviving into the measurement path after A6.2b | > 0 |
| 2 | A6.2a sweep: any `universe_selection`-class hit on a column other than `momentum_pct` / `flag_bad_denominator` (A9.1) | > 0 |
| 3 | Distinct T=0 events in `event_minute_bars_v2` ≠ 15,763 | any deviation |
| 4 | Any v1 T=0 event absent from v2 T=0 (ETH ⊇ RTH) | any |
| 5 | `has_t_minus_1_rth = FALSE` — **not an escalation**; flag-and-report, excluded from the primary decay population, retained for all other measurements, counted in the report | (report only) |
| 6 | `denom_nonpositive` (`day_high_ext ≤ tick_close_T-1_RTH`) | > 1.0% |
| 7 | Strict-key duplicate-print rate on the full pass | > 0.1% per event |
| 8 | Dev-tier runtime | > 60s per pass |
| 9 | Full passes over `filtered_trades` | > 1 |
| 10 | Write to base tables, dev tables, `event_minute_bars_v1`, or data root | any |
| 11 | Calendar pin drift | ≠ 5.4.0 / 4.13.2 |

---

## Chart Contract

Inherits `phase_6b.md` charts 01–07 unchanged **except**: chart 04's decay anchor is `tick_close_T-1_RTH` (the x-axis, bands, 0.5 crossing, and `rth_legacy` overlay are as written, only the `prev_close` references rename). **Chart 08 is dropped** (A8.2 — the basis-diagnostic chart is moot under D4's severance). Standard §9 rules apply; no finding without its distributional chart.

---

## Approval Gate

On Cooper's approval of the completed measurement: tag `phase-6b-approved`; **`master` fast-forwards** (6b's own gate + the phase-6c digest note — this is the first landing on master since `phase-5a-approved`). The latency-budget interpretation and any premarket-vs-RTH implication are Cooper's, from the charts. This amendment changes nothing in `phase_6c`/`phase_7` (both approved).

---

## Resolved decisions (draft `[CONFIRM]` items, approved 2026-07-28)

1. **A6.2 / A6.3 task split** — approved as the operative reading of "resumes at A6.2/A6.3".
2. **`has_t_minus_1_rth = FALSE` events** — flag-and-report; excluded from the *primary* decay population only (retained for concentration / min-window / segment / `rth_legacy`); no fallback anchor.
3. **Escalation thresholds** — denom-nonpositive 1.0% (row 6), dup-print 0.1%/event (row 7); `has_t_minus_1_rth = FALSE` is report-only, not an escalation (row 5).
4. **Chart 08** — dropped (not added); the committed contract runs to 07.
