# Phase 10 (v2) — Intensity Profile and Burst Timescale

**Date:** 2026-08-04
**Branch:** `phase/10` (continues; v1 artifacts retained)
**Baseline:** `phase-9-approved`
**Supersedes:** `prompts/phase_10.md` v1 (segmentation). Superseded by D6, not amended — v1 is closed, not continued.
**Objective:** Measure the T=0 trade-arrival intensity profile and extract the timescales that anchor every downstream horizon: time from detection to peak intensity, and the decay timescale after peak.
**Primary success metric:** A decay timescale and a detection-to-peak distribution that Cooper accepts on visual review of the profile overlaid against the actual tape, and that are shown stable under resolution, observable, and level conditioning.

**Read D6 before starting.** It records why segmentation was abandoned and what may not be reintroduced.

---

## Context & constraints

- **No segmentation.** No burst count, no burst boundaries, no burst spacing, no state assignment, no threshold on the intensity series. If a task appears to require labeling intervals as burst-vs-not, stop and post. This is the failure D6 exists to prevent.
- **Shape uses no baseline.** Each event's rate curve is normalized by its own peak. The flanking sessions have exactly one job: a **single scalar per ticker** for the terminal condition. No intraday shape is estimated from flanking days — the material is too thin (median 2.8 prints/min; 45% of events below 2/min).
- **Cohort is reused, not redrawn.** The v1 cohort manifest (`t1_cohort_manifest.parquet`, 114 events: 50 dev v4 primary + 50 activity extension + 8 row-cap census + 6 sidecar, seed 42) is valid and stays frozen. Analysis cohort remains the 100 primary + extension events. Row-cap census and sidecar are carried, labeled, never pooled.
- **Pass budget over `filtered_trades` / `filtered_quotes` is zero.** Targeted per-event folder reads only, as proven equivalent in v1 T0d. Any full-table plan is escalation row 4.
- **D4 stands.** All computed quantities tick-derived. No spine numeric column enters any computation. `momentum_pct` for cohort identification only.
- **Phase 13 boundary unchanged.** Inter-trade time is an *input to rate estimation* and a diagnostic display axis. This phase does not produce inter-trade interval distributions, noise-floor characterization, or interval regime definitions.
- **Offline, not a detector.** No output may be described as a detector, entry signal, or operating point. Peak-anchored quantities are retrospective by construction and must be labeled as such wherever reported.
- **Flag, never delete.** Standard §§9–12 of `docs/Agent_Prompt_Standard.md` apply in full. Every statistic carries its n. Every claim cites its chart. Standing constraints in `CLAUDE.md`.

---

## Tasks

- [ ] **T0 — Preconditions and config**
  - [ ] T0a — Confirm `phase-9-approved`; confirm v1 cohort manifest present and hash-matched.
  - [ ] T0b — Commit `prompts/phase_10_v2.md` before any other work.
  - [ ] T0c — **Author `config/phase_10_v2.json` and commit before any run.** Must carry: resolution grid `k`; both observables; anchor definitions; decay fractions; terminal-condition multiples; tie-handling variants; level-conditioning strata; every failure threshold; runtime ceilings. Where this prompt does not pin a value, propose one, justify it in `decisions_log`, and make it a config key.
  - [ ] T0d — Report timestamp-tie structure per event: share of consecutive prints sharing a timestamp, and the resolution actually present in the data. v1 floored 370,525 gaps (mean 2.7% of prints, correlated 0.64 with print count). Ties are a first-order concern for any rate estimator and must be characterized before one is chosen.
  - [ ] T0e — Commit.

- [ ] **T1 — Intensity curve estimation**

  Estimate the T=0 trade-arrival rate as a continuous function of time, per event.

  **The estimator must be adaptive.** Within-session rate spans several orders of magnitude; any fixed bin width adequate at the peak is empty in the tails. The recommended family is a k-nearest-neighbour rate estimator — rate at time t derived from the elapsed time spanning the k nearest prints — which is scale-free and follows local density. An alternative adaptive estimator is acceptable if you justify it in `decisions_log` against this dynamic-range requirement. **Fixed-width binning is not acceptable.**

  - [ ] T1a — **Two observables, both run in full:** print arrival rate and share-volume arrival rate. These are not a primary and a check; they are co-equal and reported side by side throughout. Print rate is suspected of carrying a price-level fragmentation artifact (cheap stocks fragment more), which is the specific reason volume rate is run.
  - [ ] T1b — **Resolution grid.** Compute every downstream quantity at each `k` in the config grid. The grid must span at least two orders of magnitude (e.g. k ∈ {5, 15, 50, 150, 500}) and its endpoints must be justified against the observed print-count range. A single reference `k` is designated for headline reporting; the grid is not a sensitivity afterthought, it is the primary defence against caveat 1 and every headline number is reported with its across-grid spread.
  - [ ] T1c — **Tie handling.** Run the reference `k` under at least two tie variants: ties left as-is, and consecutive same-timestamp prints collapsed to a single event with summed size. Report both. If they diverge materially, that is escalation row 8.
  - [ ] T1d — Commit.

- [ ] **T2 — Anchors**
  - [ ] T2a — **Peak anchor.** Time of maximum smoothed rate, per event, per observable, per `k`. Retrospective — label it so everywhere.
  - [ ] T2b — **Detection anchor.** The scanner detection timestamp for the event, taken from the canonical spine. Causal and operationally meaningful.
  - [ ] T2c — Report peak-anchor stability across the resolution grid: how far the peak location moves as `k` varies, per event. A peak that wanders across the grid is not a peak.
  - [ ] T2d — Commit.

- [ ] **T3 — Shape and timescales**
  All quantities computed per observable, per `k`, on the self-normalized curve (rate divided by that event's own peak rate).
  - [ ] T3a — **Detection-to-peak interval**, signed. Negative values mean peak intensity preceded detection. **Do not clip, exclude, or absolute-value negative values** — their share is a headline number in its own right.
  - [ ] T3b — **Rise profile:** normalized intensity from detection to peak.
  - [ ] T3c — **Decay timescale:** elapsed time from peak until the normalized curve falls to each fraction in the config list (at minimum 1/2, 1/e, 1/10) and stays below it. Report the never-reached count separately rather than imputing.
  - [ ] T3d — **Terminal condition:** elapsed time from peak until the *unnormalized* rate falls below each configured multiple of the ticker's scalar flanking baseline (whole-day flanking rate, not time-of-day matched). Report undefined counts where the baseline is unusable.
  - [ ] T3e — Commit.

- [ ] **T4 — Level conditioning** *(caveat 2)*

  Self-normalization deliberately discards absolute level. This task tests whether that discard is safe.

  - [ ] T4a — Carry **absolute peak rate** as a per-event covariate throughout.
  - [ ] T4b — Report every T3 timescale distribution **stratified by absolute-peak-rate quartile**, not pooled only.
  - [ ] T4c — Report the rank correlation between each timescale and absolute peak rate, with n.
  - [ ] T4d — **Report the un-normalized profiles as a diagnostic** alongside the normalized ones, so the discarded dimension is visible rather than assumed away.
  - [ ] T4e — Commit.

  **If timescale varies systematically with absolute level, the deliverable is not one number — it is a conditioned family, and every downstream phase must inherit the conditioning variable.** That outcome is a legitimate result, not a failure; it is failure row 3 only if the variation is large enough that no single anchor timescale is usable. State the observed relationship and stop there.

- [ ] **T5 — Stability and failure criteria**
  - [ ] T5a — Timescale spread across the resolution grid, per event and pooled.
  - [ ] T5b — Timescale agreement between the two observables, per event.
  - [ ] T5c — Tie-variant agreement.
  - [ ] T5d — Evaluate every pre-registered failure row. Report observed against threshold, pass/fail. **Nothing beyond pass/fail.**
  - [ ] T5e — Commit.

- [ ] **T6 — Charts** — per contract below, kaleido-verified. Commit.

- [ ] **T7 — Digest and report** — `digest.json` per §11, `REPORT.md` per the Evidence Standard.

  **Description only.** State the timescales with their n and their across-grid spread. State which failure rows passed. **Do not propose a latency budget, do not select a reference `k` or an observable as correct, do not characterize any result as good, promising, weak, or disappointing.** The budget is read by Cooper off charts 03 and 04.
  - [ ] T7a — Commit; working tree clean.

---

## Pre-registered failure criteria

| # | Failure mode | Observable | Threshold | Note |
|---|---|---|---|---|
| **0** | **Cooper rejects the profile on visual review of chart 08 against the tape** | — | **Cooper's judgment** | **Overrides all other rows in either direction. A pass elsewhere is not acceptance.** |
| 1 | **Resolution instability** *(caveat 1)* | Ratio of the pooled median decay timescale at the widest `k` to that at the narrowest | Config; **propose and justify** | If the answer tracks the estimator's resolution, it is a property of the estimator, not the market — the same defect that produced Arm A's 0.96 print-count correlation |
| 2 | **Observable disagreement** | Rank correlation between print-rate and volume-rate decay timescale, per event | Config | Disagreement means at least one observable is measuring fragmentation rather than participation |
| 3 | **Level dependence too strong to pool** *(caveat 2)* | Ratio of median decay timescale in the top absolute-peak-rate quartile to the bottom | Config | Fires only where no single anchor timescale is usable. Mild dependence is a conditioning result, not a failure |
| 4 | **Peak not captured in-window** | Share of events whose peak sits within a configured margin of the window edge | Config | The profile is truncated and the timescale is a lower bound |
| 5 | **No decay within session** | Share of events never reaching the 1/2 fraction before window end | Config | Nothing to anchor to |
| 6 | **Peak instability across the grid** | Median absolute peak-location movement across `k`, relative to the decay timescale | Config | An anchor that moves further than the quantity it anchors is not an anchor |

**Row 0 is the operative one.** Rows 1–6 catch a measurement that is an artifact of its own machinery. They cannot catch a measurement that is well-behaved and meaningless. That judgment is Cooper's off chart 08.

**Standing lesson from v1, applied here:** a stability pass is not evidence of correctness. Both v1 arms passed every numeric row while being wrong. Rows 1–6 exist to *disqualify*, never to endorse.

**If any of rows 1–6 fire:** hard stop, commit, post observed values and charts. Do not adjust parameters to make a criterion pass. Do not reintroduce segmentation, thresholding, or Hawkes calibration on your own initiative — all three are closed by D6 and reopening any of them requires a numbered decision.

---

## Escalation criteria

| # | Condition | Threshold | Action |
|---|---|---|---|
| 1 | `phase-9-approved` absent, or v1 cohort manifest hash mismatch | any | Hard stop at T0a |
| 2 | Cohort join to `momentum_events_canonical` with `in_scope = TRUE` shortfall | any | Hard stop |
| 3 | Read of a D4-quarantined spine numeric on any computation path | > 0 | Hard stop — post file and line |
| 4 | Full-table pass over `filtered_trades` or `filtered_quotes` | any | Hard stop — post the query plan first |
| 5 | Runtime ceiling breached | per config | Hard stop — do not silently reduce the cohort or the grid |
| 6 | Any interval-labeling, thresholding, or state-assignment step introduced | any | Hard stop — closed by D6 |
| 7 | Fixed-width binning used as the rate estimator | any | Hard stop — see T1 |
| 8 | Tie variants diverge beyond the config tolerance | per config | Hard stop — post both |
| 9 | Detection timestamp unavailable or ambiguous for any cohort event | any | Hard stop — the detection anchor is load-bearing |
| 10 | Negative detection-to-peak values clipped, excluded, or absolute-valued | any | Hard stop |
| 11 | Any output described as a detector, entry signal, operating point, or latency budget | any | Hard stop before posting |
| 12 | Any `k`, observable, or timescale selected, recommended, or called preferable | any | Hard stop — the selection is Cooper's |
| 13 | Write outside `prompts/`, `config/`, `research/phase_10/`, `results/phase_10/` | any | Hard stop |

---

## Chart contract

| # | File | Question | Encoding | n shown | Looks like this if wrong |
|---|---|---|---|---|---|
| 01 | `01_profile_peak_anchored.html` | What shape does intensity have around its peak? | Self-normalized rate against time since peak; pooled median plus quartile band; one panel per observable | n events, n prints | Flat band — no common shape, so no timescale exists |
| 02 | `02_profile_detection_anchored.html` | What does it look like from the moment you could have known? | Same, anchored at scanner detection | n events | Peak already passed at t=0 for most events |
| 03 | `03_detection_to_peak.html` | **How much runway is there?** | Signed distribution of detection-to-peak, log-symmetric x, negative region shaded and labeled with its share | n events, negative share in caption | Mass concentrated at or below zero — the runway is gone before detection |
| 04 | `04_decay_timescale.html` | How fast does participation decay? | Distributions of time-to-half, time-to-1/e, time-to-1/10; never-reached counts in caption | n per fraction, never-reached count | Timescales at the window edge — truncation, not decay |
| 05 | `05_resolution_stability.html` | **Is the answer a property of the market or of the estimator?** *(caveat 1)* | Median decay timescale against `k`, log-log, with per-event spaghetti behind the median; both observables | n events per `k` | A straight sloped line — the timescale is just tracking resolution |
| 06 | `06_level_dependence.html` | **Does shape depend on absolute level?** *(caveat 2)* | Decay timescale against absolute peak rate, scatter with fitted trend; decay-timescale distributions by absolute-peak-rate quartile as a second panel; un-normalized profiles as a third | n per stratum | Clean monotone trend — one timescale does not exist, only a conditioned family |
| 07 | `07_observable_agreement.html` | Print rate versus volume rate | Per-event decay timescale scatter with identity line; per-event peak-location difference distribution | n events | Wide scatter — at least one observable is measuring fragmentation |
| 08 | `08_tape_review/` | **Does the profile correspond to what actually happened?** | **Per selected event, three stacked panels on a shared time axis. Top: individual trade prints, price against time, marker size by share count. Middle: estimated intensity curve, log scale, all `k` in the grid overlaid, both observables. Bottom: inter-trade time, log scale. Detection and peak marked as vertical rules on all three panels.** | Print count, peak rate, detection-to-peak in each event's title | Peak marker not where the tape visibly goes wild; curve at different `k` disagreeing about where the peak is |

Selection for chart 08 per config cap: full dev v4 primary cohort plus a stratified draw spanning the detection-to-peak range including its negative tail, plus every event flagged by any failure row. Sidecar and row-cap events included and labeled. Sortable index over the full cohort. **Do not exceed the config cap** — the §12 `event_charts/` rule exists because unbounded per-event output broke prior phases.

---

## Reporting

Post, each with n and each citing its chart:

1. Tie-structure table (T0d) — share of tied prints, per group
2. Estimator table — method, grid, justification against the dynamic-range requirement
3. Anchor table — peak-location stability across `k`; detection-anchor availability
4. **Detection-to-peak table — median, quartiles, and the share of negative values, per observable, per `k`**
5. Decay timescale table — per fraction, per observable, per `k`, with never-reached counts
6. Terminal-condition table — with undefined counts
7. **Level-conditioning table — every timescale by absolute-peak-rate quartile, plus rank correlations**
8. **Resolution-stability table — every headline number with its across-grid spread**
9. Observable-agreement table
10. Failure criteria table — rows 0–6, observed against threshold, pass/fail, nothing further
11. Escalation check table — all 13 rows
12. Verification block per §10 — every headline number with source, n, and reproduce command
13. Output file table; commit list

**No recommendations. No `k` selected. No observable selected. No latency budget proposed.** The agent describes the picture.

---

## Approval gate

Do not tag, do not merge, do not begin Phase 11 scoping until Cooper has reviewed the charts and given explicit approval. On approval, tag `phase-10-approved`.

**Chart 08 is the gate. Chart 03 is the number.** Charts 05 and 06 decide whether that number is one number or a conditioned family. All four reads are Cooper's.
