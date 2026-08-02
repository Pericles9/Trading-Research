# Phase 8 — Event-Study Grid: Forward Markouts from Tradeable Anchors

**Date:** 2026-08-01
**Branch:** `phase/8`
**Baseline:** `phase-6b-approved` — `event_minute_bars_v2` (45,925,350 rows, extended-day, segment-tagged), D1 = 15,763 events
**Objective:** Produce the first forward-return measurement in the program — markouts from anchor points knowable in real time, bucketed by participation, with survivorship and coverage reported alongside.
**Primary success metric:** A complete markout grid over all D1 events with per-cell n, produced with **zero full-table passes** over `filtered_trades` / `filtered_quotes`.

---

**Context:**

- **This phase is scan-free.** Every measurement derives from `event_minute_bars_v2`. No pass over `filtered_trades` or `filtered_quotes` is authorized. This is escalation row 3 and it is a hard stop, not a budget.
- **Every prior measurement in this program is conditioned on the day's high**, which is not knowable in real time. `momentum_pct` is a prev_close→high quantity. This phase measures forward returns from timestamps at which a decision could actually have been made.
- **D4 stands.** All computed quantities are tick-derived. No spine numeric column (OHLC, volume fields) may enter any computation. `momentum_pct` remains exempt for universe selection only — **and is explicitly prohibited as a bucketing variable in this phase** (§ Task T5 note).
- **Baseline windows are three sessions, maximum.** The archive is event-windowed (T-3..T+3). There is no longer lookback available. Do not attempt to construct one from other events' windows for repeat tickers — those windows bracket other spike days and are not a quiet baseline.
- **D-a (Cooper, 2026-08-01):** the operative clock is the **gap-inclusive primary (516 min)**, anchored on `tick_close_t_minus_1_rth`. This governs T1 and T2 only; markouts (T5–T6) are log returns and carry no fraction-of-move denominator.
- **Flag, never delete.** Every population that fails a coverage or definedness condition is carried with a label and reported as its own row. No universe-level exclusions.
- Working directory: repo root. Standing constraints in `CLAUDE.md`. Decisions in `docs/Universe-Decisions.md`.

---

## Tasks

- [ ] **T0 — Branch, prompt, config, preconditions**
  Cut `phase/8` from main. Commit `prompts/phase_8.md` and `config/phase_8.json` before any other work.

  - [ ] T0a — Confirm tag `phase-6b-approved` exists and master is at it. If absent, escalation row 1.
  - [ ] T0b — **Verify `event_minute_bars_v2` covers all seven offsets (T-3..T+3) across the extended day.** Report per-offset row counts, distinct event counts, and observed `minute_index` range per offset and per session segment. 6b's gates only checked T=0; this phase depends on the flanking sessions. If v2 is T=0-only or any offset is materially incomplete, escalation row 2 — the phase reshapes and must not proceed.
  - [ ] T0c — Record the v2 table row count and a SHA256 of its DDL into `t0_preconditions.json` as the phase's pin.
  - [ ] T0d — Commit.

- [ ] **T1 — Decompose `realized(04:00)` (the 0.173)**
  6b reported median realized-at-RTH-open of 0.173 and glossed it as premarket. With a T-1 **RTH**-close anchor it is three things. Decompose per event into:
  - `seg_t1_post` — T-1 16:00→20:00 (observable path)
  - `seg_overnight` — T-1 last extended print → T0 first extended print (a jump, no path)
  - `seg_t0_pre` — T0 first extended print→09:30
  Report each as a share of `realized(09:30)` and as an absolute log move. Median, IQR, and full distribution per component. **No interpretation of which matters — report the three distributions.**
  - [ ] T1a — Events with no T-1 extended-day bars carry `decomp_undefined=TRUE`, reported as their own row, never imputed.
  - [ ] T1b — Chart 01. Commit.

- [ ] **T2 — Deferred items from Phase 6/6b, all scan-free against v2**

  - [ ] T2a — **ETH-dominant split on the extended-day decay curve.** Recompute the pooled opportunity-decay curve (primary, 516-clock) separately for `flag_eth_dominant_t0` TRUE (n=736) and FALSE, with per-group n. This question was asked in the RTH frame, where the flag meant "mismeasured"; in the extended frame it means "the move happens outside RTH." It has not been asked natively. Chart 02.
  - [ ] T2b — **Row-cap detector (ARBB, open since Phase 6 risk register).** Per-event T=0 total print count from v2. Report the distribution and flag any value at a suspicious round number (exactly 50,000 / 100,000 / 200,000, and any count appearing across ≥3 distinct events at the same exact value). Report ARBB's own count explicitly. **Do not attempt root cause** — that requires reading `filtered/` parquet files and is out of scope. Chart 03.
  - [ ] T2c — Commit.

- [ ] **T3 — Participation baseline construction**
  For each event and each clock anchor τ (see config), compute:
  - `v0(τ)` = cumulative T0 extended-day volume, 04:00 → τ
  - `b_clock(τ)` = **median** over offsets {T-1, T-2, T-3} of cumulative volume 04:00→τ on that session
  - `b_session` = **median** over {T-1, T-2, T-3} of full extended-session volume
  - `logrv_clock(τ) = log((v0(τ)+1) / (b_clock(τ)+1))`, `logrv_session(τ) = log((v0(τ)+1) / (b_session+1))`

  **Pre-registered selection rule, frozen in config, applied before any markout is computed:** for each anchor independently, if `b_clock(τ)` is zero or undefined for **>20%** of D1 events, that anchor uses `logrv_session`; otherwise it uses `logrv_clock`. The choice is made on the undefined rate alone. Record per-anchor which form was selected and the undefined rate that drove it in `decisions_log`.

  - [ ] T3a — Events with **no** T-1/T-2/T-3 trades in v2 get `participation_class='no_baseline'`. Carried, labelled, never pooled into quintiles. Report n.
  - [ ] T3b — Bucket: **cross-sectional quintile of the selected `logrv` at each anchor**, computed across D1 at that anchor. Only the rank is used; the level is never reported as a headline.
  - [ ] T3c — Report per-anchor: undefined rate, form selected, quintile boundaries, per-quintile n, `no_baseline` n. Commit.

- [ ] **T4 — Anchor construction**

  - [ ] T4a — **Clock anchors** (config): 09:00 ET, RTH open, open+5, open+15, open+30, open+60, open+120, T0 close. Anchor price = **last trade at or before the anchor timestamp** (consistent with 6b's `tick_close_t_minus_1_rth` convention). Events with no print at or before an anchor are labelled `anchor_undefined` at that anchor, carried, reported.
  - [ ] T4b — **Event-relative rung anchors.** Fixed ladder, frozen in config: first T0 minute at which cumulative volume reaches **1× / 2× / 5× / 10×** the same baseline selected in T3. Anchor price by the same convention. **Every rung is reported. No rung may be selected, recommended, or described as preferable** — see escalation row 10.
  - [ ] T4c — **Rung attrition** is a first-class output: for each rung, the count and fraction of D1 that ever reaches it, and the distribution of crossing time-of-day. Chart 07.
  - [ ] T4d — Commit.

- [ ] **T5 — Markout grid**
  Forward **signed log return** from each anchor price to each horizon. Long convention — report the sign as computed; **do not take absolute values**, a negative markout is a finding, not an error.

  Horizons: anchor+30 min, anchor+60 min, T0 close, T+1 close, T+3 close. Closing prices are tick-derived last extended-session prints from v2.

  - [ ] T5a — **Clock-anchor grid:** anchor × participation quintile × horizon, **faceted by era** (2020–21 vs 2022–24, boundary in config). Per-cell: n, median, IQR, and the full within-cell distribution retained for charting.
  - [ ] T5b — **Rung grid:** rung × crossing-time-of-day bin × horizon, era-faceted. Participation is constant by construction at a rung and is **not** a bucketing variable here.
  - [ ] T5c — **Prohibited bucketing variables, explicitly:** `momentum_pct` or any decile of it; realized-fraction-at-anchor; day-high-derived quantities; `flag_eth_dominant_t0` as a *bucket* (it is a chart split in T2a only). All are hindsight-contaminated — the bucket assignment would already know how the day resolved.
  - [ ] T5d — Flagged populations carried as their own labelled rows, never merged into quintiles: `no_baseline`, `anchor_undefined`, the 36 `has_t_minus_1_rth=FALSE`, the 5 `denom_nonpositive`, the 7 `flag_has_dup_prints`. Additionally report the flagship cell with and without the 7 dup-print events as a one-line sensitivity.
  - [ ] T5e — Charts 04, 05, 06. Commit.

- [ ] **T6 — Survivorship count (diagnostic, no accommodation)**
  Report only — no exclusions, no reweighting, no modelling.
  - [ ] T6a — Per-event: presence of T+1 / T+2 / T+3 sessions in v2, and per-ticker last-seen session anywhere in the archive vs. event date.
  - [ ] T6b — Report the implied post-event disappearance rate for D1, by era. State the observed rate with n. **No comparison to any external base rate, no causal language, no claim about bias magnitude.**
  - [ ] T6c — Chart 08. Commit.

- [ ] **T7 — Digest and report**
  `digest.json` per §11 and `REPORT.md`. Every claim cites its chart file. No recommendations.
  - [ ] T7a — Commit; confirm working tree clean.

---

## Escalation Criteria

Stop and post results. Do not proceed to the next task. Report in table order.

| # | Condition | Threshold | Action |
|---|---|---|---|
| 1 | Tag `phase-6b-approved` absent | any | Hard stop — post, await instruction |
| 2 | `event_minute_bars_v2` missing an offset, or extended-day coverage incomplete on any offset | any | Hard stop — post per-offset counts, await instruction. **Do not work around it.** |
| 3 | Any full-table pass over `filtered_trades` or `filtered_quotes` | any | Hard stop — post before running it |
| 4 | Read of a D4-quarantined spine numeric on any computation path | > 0 | Hard stop — post the file and line |
| 5 | `participation_class='no_baseline'` share of D1 | > 5% | Hard stop — bucketing is unreliable at that rate; post the count |
| 6 | Same-clock baseline undefined at an anchor | > 20% | **Not a stop.** Switch that anchor to `logrv_session` per T3's frozen rule; record in `decisions_log` |
| 7 | `anchor_undefined` at any clock anchor | > 10% of D1 | Hard stop — post per-anchor rates |
| 8 | Any markout cell n | < 100 | **Not a stop.** Mark the cell thin on the chart; state no claim from it |
| 9 | Write outside `prompts/`, `config/`, `research/phase_8/`, `results/phase_8/` | any | Hard stop |
| 10 | Any rung, anchor, or threshold selected, recommended, or described as preferable on the basis of its markouts | any | Hard stop — this is detector construction by peeking, not measurement |
| 11 | Any bucketing variable used that is not knowable at the anchor timestamp | any | Hard stop |

---

## Output Files

| File | Description | Status |
|---|---|---|
| `config/phase_8.json` | anchors, rung ladder, baseline selection rule + 20% threshold, quintile count, era boundary, horizons | [ ] |
| `results/phase_8/artifacts/t0_preconditions.json` | v2 per-offset coverage, DDL SHA256, row-count pin | [ ] |
| `results/phase_8/artifacts/t1_decomposition.json` | three-component decomposition, medians + IQR + undefined count | [ ] |
| `results/phase_8/artifacts/t2_eth_split.json` | decay curve by `flag_eth_dominant_t0`, per-group n | [ ] |
| `results/phase_8/artifacts/t2_row_cap_scan.json` | per-event T=0 print counts, round-number flags, ARBB explicit | [ ] |
| `results/phase_8/artifacts/t3_participation.json` | per-anchor undefined rate, form selected, quintile bounds, per-bucket n | [ ] |
| `results/phase_8/artifacts/t4_anchors.parquet` | per-event × anchor prices + labels (gitignored, regenerable) | [ ] |
| `results/phase_8/artifacts/t5_markout_grid.parquet` | full grid, per-cell distributions retained (gitignored) | [ ] |
| `results/phase_8/artifacts/t5_markout_summary.json` | per-cell n, median, IQR — clock and rung grids | [ ] |
| `results/phase_8/artifacts/t6_survivorship.json` | T+1..T+3 presence, per-ticker last-seen, rates by era | [ ] |
| `results/phase_8/charts/01–08*.html` | per Chart Contract, kaleido-verified | [ ] |

---

## Chart Contract

| # | File | Question | Encoding | n shown | Looks like this if wrong |
|---|---|---|---|---|---|
| 01 | `charts/01_realized_open_decomposition.html` | Of the move already realized at RTH open, how much is T-1 post-market, overnight jump, and T0 premarket? | Three side-by-side violins (one per component) of share-of-`realized(09:30)`, strip overlay, log-scale absolute-move panel beneath | n per component, `decomp_undefined` count in caption | All three violins overlap and centre near zero — the 0.173 has no dominant source and the decomposition doesn't separate |
| 02 | `charts/02_decay_by_eth_flag.html` | Does the extended-day decay curve differ for ETH-dominant events? | x=minutes since 04:00, y=median realized fraction, one line per flag group, IQR bands | n per group in legend | The two curves overlap within their IQR bands across the whole day |
| 03 | `charts/03_t0_print_count_distribution.html` | Are any events silently row-capped? | ECDF of per-event T=0 print count (log x), rug marks at flagged round numbers, ARBB annotated | n=15,763 in title; count of events at each flagged value | Smooth ECDF, no vertical steps, no mass at round numbers — no cap present |
| 04 | `charts/04_markout_heatmap.html` | Do forward returns vary with participation and entry timing? | Facet grid: rows=horizon, cols=era; x=anchor, y=participation quintile, colour=median markout; cells with n<100 hatched | Per-cell n printed in cell | Uniform colour across all cells — no structure in either dimension, in either era |
| 05 | `charts/05_markout_distributions_flagship.html` | What distribution sits behind the flagship heatmap cells? | Violin + strip per participation quintile at T0-close horizon, faceted by era, zero-line marked | Per-quintile n above each violin | Violins overlap almost entirely across quintiles; medians unordered |
| 06 | `charts/06_rung_markouts_by_crossing_time.html` | Does an early participation trigger pay differently from a late one? | Facet per rung; x=crossing time-of-day bin, y=markout, violin + strip, era as colour | Per-bin n above each violin | Flat across crossing-time bins within every rung |
| 07 | `charts/07_rung_attrition.html` | How much of the universe reaches each rung, and when? | Panel A: bar, x=rung, y=fraction of D1 reaching it. Panel B: ECDF of crossing time-of-day per rung | n per rung on bars; n per curve in legend | Near-100% at every rung (ladder non-discriminating) or near-zero above 1× (ladder unusable) |
| 08 | `charts/08_survivorship_census.html` | How often do these tickers stop trading after the event? | Panel A: bar, missing T+1/T+2/T+3 counts by era. Panel B: ECDF of (ticker last-seen session − event date) in sessions | n per bar and per curve | Panel B has essentially no mass at short horizons — tickers keep trading, no post-event attrition present in the archive |

Standard chart rules per §9 apply: distributions not centres, outliers shown never clipped, log scale where multiplicative, caption carries sample + filters + config hash.

---

## Reporting

On completion, post:

1. **Precondition table** — v2 per-offset coverage, distinct events, minute-index range per segment
2. **Decomposition table** — three components, median share, IQR, n, undefined count
3. **Participation table** — per anchor: baseline form selected, undefined rate, quintile bounds, per-quintile n, `no_baseline` n
4. **Flagship markout table** — T0-close horizon, participation quintile × era, with n, median, IQR per cell
5. **Rung attrition table** — per rung: n reaching, % of D1, median crossing time
6. **Flagged-population table** — every labelled row with its n and its markout, reported separately from the quintiles
7. **Survivorship table** — missing T+1/T+2/T+3 by era, with n
8. Escalation check table — all 11 rows, observed value, pass/fail
9. Verification block (§10) — every headline number with source, n, and repro command
10. Output file table with status filled in
11. Commit list

Every claim cites its chart. **No recommendations, no statement about what any result implies for strategy design, and no characterisation of any result as good, promising, weak, or disappointing.** The agent describes the picture.

---

## Approval Gate

Do not begin Phase 9 or any follow-on work until Cooper has reviewed the charts and given explicit approval. On approval, tag `phase-8-approved`.

The read on whether this archive contains a forward edge is Cooper's, from charts 04, 05, and 06 — not the agent's.
