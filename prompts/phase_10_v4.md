# Phase 10 (v4) — Sub-Burst Detection from Locally-Normalized Log Inter-Trade Intervals

**Date:** 2026-08-04
**Branch:** `phase/10`
**Baseline:** `phase-9-approved`
**Supersedes:** `prompts/phase_10_v3.md` (envelope-and-excursion), which supersedes v2 and v2_r1
**Objective:** Detect sub-bursts within the T=0 session using an inter-trade interval threshold derived per event from the shape of its own interval distribution.
**Primary success metric:** A sub-burst decomposition Cooper accepts on visual review against the tape, whose count is demonstrably **not** a function of print count, and which reports honestly on which events it works for.

---

## D9 — Sub-bursts are detected from locally-normalized log inter-trade intervals

*(For appending to `docs/Universe-Decisions.md`. Append-only per escalation row 13 as amended by R1.)*

**Decision:** Sub-bursts are identified by thresholding the inter-trade interval, where the threshold is derived per event from the trough of its own locally-normalized log-interval distribution. v3's envelope-and-excursion approach is withdrawn before execution.

**Why.** Every prior attempt required estimating an intensity curve, which required choosing a smoothing scale, which made the answer track the estimator. Arm A's burst count correlated **0.96** with print count for this reason. v2's rows 1 and 6 failed for this reason. v3 would have inherited it through the envelope bandwidth. **Operating on intervals directly removes the mechanism rather than testing for it after the fact.**

**Prior art.** This is standard practice in two mature fields and was not invented here.

- **Neuroscience — spike train burst detection.** The log-interval histogram method (Selinger et al. 2007; Pasquale et al. 2010) locates peaks in the log-transformed interval histogram and sets the threshold at the minimum between the intra-burst peak and subsequent peaks. It carries a **void parameter** measuring peak separation, with a conventional cutoff of 0.7; where no intra-burst peak exists, no bursts are declared. Ko et al. (2012) handle non-stationary rate by normalizing log intervals against a **moving window of roughly 20% of the sequence**, reporting under 0.3% change in detected counts anywhere between 10% and 30%. Kapucu et al. (2012) derive thresholds from the cumulative moving average and skewness of the interval histogram, built for time-varying dynamics.
- **Seismology — earthquake declustering.** Baiesi & Paczuski (2004), extended by Zaliapin & Ben-Zion (2013, 2020), separate clustered from background events using the bimodality of a nearest-neighbour distance whose proximity metric scales with event magnitude — the window widens for larger events by construction.

**The warning that shapes this phase.** Zaliapin & Ben-Zion found the bimodality that separates clustered from background events is often violated in the vicinity of the largest earthquakes, where triggered activity dominates and a simple threshold between modes stops working. **Our entire T=0 session is that vicinity.** The void parameter is therefore a live gate, not a formality, and it is expected to fail on some events. **The share of events where it fails is a headline result, not an inconvenience.**

**Everything in this phase is offline and non-causal.** The threshold, the void gate, and the normalization window all read the completed session. This is correct for label construction and useless for trading. Phase 17's online detector must re-derive every one of these under causality, and this phase's job is to hand it a defensible target, not a tradeable rule.

**Consequences:**
- **(a)** v3 is withdrawn before execution; no v3 artifacts exist.
- **(b)** v2 artifacts remain the superseded evidentiary record per D8(b).
- **(c)** These carry forward unchanged: the frozen cohort (`e1a0ac73a79aa573`); the D7 detection anchor (110/110 exact against Phase 8, reference deviation 0.000e+00); detection-to-peak (median ~1,976s, poll ratio 1.010); the 28% negative share; the segment split.
- **(d)** D8's scale-separation gate is withdrawn as a separate task. The void parameter supersedes it: per-event rather than pooled, and computed as part of the method rather than alongside it.
- **(e)** Detection segment remains a stratification variable from the start.

---

## Context & constraints

- **Cohort frozen.** Assert content hash `e1a0ac73a79aa573` at T0. 114 events; analysis cohort 100; row-cap census and sidecar carried, labeled, never pooled.
- **Detection anchor reused, not re-derived.** D7 and the R1 artifacts stand.
- **Everything stratified by detection segment** — premarket (n=28), regular-hours (n=70), after-hours — from T1 onward. Pooled alongside, never instead.
- **No intensity curve is estimated anywhere in this phase.** If a task appears to require one, stop and post. That is the defect D9 exists to remove.
- **Pass budget over `filtered_trades` / `filtered_quotes` is zero.** Targeted folder reads only.
- **D4 stands.** All quantities tick-derived. No spine numeric on any computation path.
- **Phase 13 boundary.** This phase uses inter-trade intervals as its operating variable. It does **not** produce the interval distribution as a characterized finding, the noise floor, or interval regime definitions — those remain Phase 13's. The boundary is narrow here and must be stated in the report.
- **Offline only.** No output may be described as a detector, entry signal, or operating point.
- Standard §§9–12 apply. Every statistic carries its n. Every claim cites its chart. Escalation row 13 as amended by R1.

---

## Tasks

- [ ] **T0 — Preconditions, supersession, config**
  - [ ] T0a — Assert cohort hash; confirm `phase-9-approved`; confirm R1 detection anchor artifacts present.
  - [ ] T0b — Commit `prompts/phase_10_v4.md` before any other work.
  - [ ] T0c — Append D9 to `docs/Universe-Decisions.md`. Append-only, zero deletions. Note in the entry that v3 was withdrawn before execution.
  - [ ] T0d — **Author and commit `config/phase_10_v4.json`.** Must carry: normalization window grid; peak-finding method and parameters; void parameter cutoff; minimum prints per sub-burst; tie variants; segment strata; every failure threshold; chart caps; runtime ceilings. Propose and justify anything not pinned here.
  - [ ] T0e — Commit.

- [ ] **T1 — Intervals and ties**
  - [ ] T1a — Extract inter-trade intervals per event over the T=0 window.
  - [ ] T1b — **Tie handling is load-bearing here, more than in any prior version.** v1 floored 370,525 gaps — 2.7% of prints on average, up to 8.1%, correlated **0.64 with print count.** Zero-length intervals cannot be log-transformed. Run at least two variants: same-timestamp prints collapsed to one event with summed size, and zero intervals set to the data's actual timestamp resolution. Report the resolution actually present rather than assuming it.
  - [ ] T1c — Report tied-print share per event and per segment.
  - [ ] T1d — Commit.

- [ ] **T2 — Local normalization**

  Log-transform intervals, then normalize each against a local characteristic value estimated over a moving window, per Ko et al. This is what makes the threshold scale with the event.

  - [ ] T2a — Implement with the window as a fraction of sequence length. **Grid at minimum 10%, 20%, 30%** — the published insensitivity range. Use a robust location estimator, not the mean; justify the choice in `decisions_log`.
  - [ ] T2b — **The window is centered and therefore non-causal.** Record it as such. Do not substitute a trailing window to make it causal — that is Phase 17's problem and a different estimator.
  - [ ] T2c — Report sensitivity across the grid. Ko et al. report under 0.3% change in detected counts across 10–30%. **If ours moves materially more, our data differs from the published regime in a way that matters** — failure row 4.
  - [ ] T2d — Commit.

- [ ] **T3 — Threshold derivation and the void gate**
  - [ ] T3a — Build the normalized log-interval histogram per event. Locate peaks. State the peak-finding method and its parameters in config.
  - [ ] T3b — Identify the short-interval (intra-burst) peak and subsequent peaks; take the minimum between them as the candidate threshold.
  - [ ] T3c — **Compute the void parameter at each candidate minimum.** Threshold is the first minimum clearing the config cutoff. **Where no intra-burst peak exists, or no minimum clears the cutoff, no sub-bursts are declared for that event.** These events are carried, labeled `no_threshold`, and reported as their own row — never dropped, never given a fallback threshold.
  - [ ] T3d — **The `no_threshold` share is a headline number**, per the Zaliapin warning in D9. Report it pooled and per segment.
  - [ ] T3e — Commit.

- [ ] **T4 — Sub-burst identification**
  - [ ] T4a — Sub-bursts are runs of consecutive intervals below the per-event threshold, subject to a minimum print count per sub-burst (config, with sensitivity).
  - [ ] T4b — Per sub-burst: start, end, duration, print count, share of session prints, share of session move.
  - [ ] T4c — Per event: sub-burst count, spacing, and the move share carried by the largest, second, third.
  - [ ] T4d — Sub-burst timing relative to the D7 detection anchor and to the event peak.
  - [ ] T4e — Commit.

- [ ] **T5 — The Arm A test**

  **This decides whether the result is real.** Arm A produced stable, well-distributed burst counts that were a restatement of print count, and every numeric criterion in v1 passed anyway.

  - [ ] T5a — Spearman correlation of sub-burst count with T=0 print count, plus the log-log slope. Pooled and per segment.
  - [ ] T5b — The same against session duration and absolute activity. **If print count dominates duration, the count is an artifact.**
  - [ ] T5c — Sub-burst count per unit time and per thousand prints, distributed.
  - [ ] T5d — Evaluate failure row 1. Commit.

- [ ] **T6 — Stability and causal audit**
  - [ ] T6a — Normalization-window sensitivity (row 4); tie-variant agreement; minimum-print sensitivity.
  - [ ] T6b — Void parameter distribution across the cohort — how close to the cutoff do events sit? A cohort clustered just above the cutoff is fragile in a way a pass/fail count hides.
  - [ ] T6c — **Causal audit.** Tag every derived field `causal` or `non_causal` as a first-class column in the output artifacts, with a one-line reason. Produce a summary table of what Phase 17 must re-derive under causality. Everything in this phase except the detection anchor is expected to be non-causal; **if anything is tagged causal, justify it explicitly** rather than letting it pass.
  - [ ] T6d — Evaluate all failure rows. Observed against threshold, pass/fail, nothing further. Commit.

- [ ] **T7 — Charts** per contract below, kaleido-verified. **Chart 06 is produced whether or not numeric rows fire.** Commit.

- [ ] **T8 — Digest and report.** Description only. **Do not select a normalization window, a void cutoff, or a minimum print count; do not propose a latency budget; do not characterize results as good, promising, weak, or disappointing.** Commit; working tree clean.

---

## Pre-registered failure criteria

| # | Failure mode | Observable | Threshold |
|---|---|---|---|
| **0** | **Cooper rejects the decomposition on visual review of chart 06 against the tape** | — | **Cooper's judgment. Overrides every other row in either direction.** |
| **1** | **Sub-burst count is a restatement of print count** *(the Arm A test)* | Spearman(count, T=0 print count); log-log slope | **Proposed: correlation ≤ 0.50, slope ≤ 0.35.** Arm A scored 0.96 and 0.85 |
| 2 | Method does not apply to the cohort | Share of events labeled `no_threshold` | Config; propose and justify |
| 3 | Void parameters cluster at the cutoff | Share of events within a margin of the cutoff | Config |
| 4 | Normalization window drives the answer | Change in sub-burst count across the 10–30% window grid | Config. Published comparison: under 0.3% |
| 5 | Tie handling drives the answer | Sub-burst count agreement across tie variants | Config |
| 6 | Degenerate decomposition | Share of events yielding one sub-burst spanning the session, or duration at the timestamp resolution floor | Config |
| 7 | Segment incompatibility | Separation between premarket and regular-hours threshold distributions | Config |

**Rows 2 and 3 are the honest ones.** D9 predicts, on the seismology prior art, that the bimodality will fail for some events because the whole session sits in the vicinity of the dominant event. **A high `no_threshold` share is a finding about the data, not a failure of the method** — it says the method works where bimodality exists and reports where it doesn't, which is more useful than a global verdict. Row 2 fires only if the share is high enough that the method doesn't apply to the cohort at all.

**Row 1 remains the criterion that decides whether the result is real.** A pass on stability rows is not evidence of correctness — v1 proved that with all four rows passing while both arms were wrong.

**If any row fires:** hard stop, commit, post observed values and charts. Do not adjust parameters to make a criterion pass. Do not fall back to a global threshold for `no_threshold` events. Do not reintroduce intensity estimation, envelope fitting, constant-reference thresholding, two-state segmentation, or Hawkes calibration — all closed by D6, D8, and D9.

---

## Chart contract

| # | File | Question | Encoding | Looks like this if wrong |
|---|---|---|---|---|
| 01 | `01_log_interval_histograms.html` | **Is the interval distribution actually bimodal?** | Normalized log-interval histogram, a grid of events spanning the activity range and both segments; detected peaks, chosen trough, and void parameter annotated on each | Unimodal or ragged — no separation to threshold on, and the `no_threshold` share will be high |
| 02 | `02_void_parameter.html` | Which events support a threshold, and how comfortably? | Void parameter distribution across the cohort with the cutoff marked; per segment; second panel against T=0 print count | Mass piled just above the cutoff — a pass/fail count would hide the fragility |
| 03 | `03_subburst_count.html` | How many sub-bursts does a session have? | Per-event count distribution, per segment, per observable; `no_threshold` count in the caption | All mass at 1, or a single spike |
| 04 | `04_count_vs_prints.html` | **Is the count real or a print-count artifact?** *(row 1)* | Count against T=0 print count, log-log scatter, fitted slope with **Arm A's 0.85 drawn as a reference line**; second panel against session duration | Slope near Arm A's line — same defect, fifth method |
| 05 | `05_duration_spacing_moveshare.html` | What timescale do sub-bursts live at, and do they carry the move? | Duration and spacing distributions, log x, per segment, timestamp resolution floor marked; per-sub-burst move share with a ranked panel | Duration piled at the resolution floor; move shares uniformly small |
| 06 | `06_tape_review/` | **Does any of this correspond to what happened?** | **Per event, three panels on a shared time axis. Top: trade prints, price, marker size by share count, sub-burst intervals shaded. Middle: inter-trade time, log scale, with the per-event threshold drawn as a horizontal rule. Bottom: normalized log interval with the same threshold. Detection anchor and peak marked on all three.** | Shaded intervals not matching visible density changes on the tape |

**Chart 06 is produced even if numeric rows fire.** v2 skipped its tape review on the reasoning that acceptance was off the table — defensible for gating a disqualified measurement, but it also removed the only means of seeing *why*. Selection per config cap: dev v4 primary cohort, plus a stratified draw across segment and sub-burst count, plus **every `no_threshold` event up to the cap** — those are the most informative charts in the set, because they show what the method could not handle. Sidecar and row-cap included and labeled.

---

## Reporting

Post, each with n, each citing its chart, each split by segment:

1. Cohort and precondition assertions; D9 append confirmation with line counts
2. Tie-structure table — tied-print share, timestamp resolution, per group
3. **`no_threshold` table — count and share, pooled and per segment, with the Zaliapin bimodality reasoning stated**
4. Void parameter table — distribution, margin above cutoff
5. Threshold table — derived threshold per event, distributed, per segment
6. Sub-burst count, duration, spacing tables
7. Move-share table with undefined-denominator counts
8. **Row 1 table — correlation and slope against print count, duration, and activity**
9. Stability tables — normalization window, tie variant, minimum print count
10. **Causal audit table — every derived field tagged, and what Phase 17 must re-derive**
11. Failure criteria table — rows 0–7, observed against threshold, pass/fail, nothing further
12. Verification block per §10 — every headline number with source, n, reproduce command
13. Output files; commit list

---

## Approval gate

No tag, no merge, no Phase 11 scoping until Cooper approves. On approval, tag `phase-10-approved`.

**Chart 01 shows whether the method has anything to work with. Chart 04 shows whether the result is real. Chart 06 is the gate.** All three reads are Cooper's.
