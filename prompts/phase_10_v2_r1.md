# Phase 10 v2 — Resolution R1: derive the detection anchor

**Date:** 2026-08-04
**Branch:** `phase/10` (continues from `2ae8c95`)
**Resolves:** escalation row 9, raised at T0a
**Contains:** decision **D7** (to be recorded), amendments to `prompts/phase_10_v2.md` T2b and escalation rows 9 and 13, and two process fixes
**Objective:** Derive a detection anchor from tick data, then resume Phase 10 v2 from T0c.

---

## What was wrong

The v2 prompt's T2b said the detection timestamp was "taken from the canonical spine." **No such column exists, and never did.** The prompt asserted a source without verifying it, on the input that produces the phase's headline number. T0a caught it before any measurement ran, which is the escalation system working — but the error was in the prompt, not in the data.

Rows 1 and 2 passed. Cohort content hash `e1a0ac73a79aa573`, canonical join 114/114. Those hold; nothing about the cohort is reopened.

---

## D7 — The detection anchor is derived, not sourced

**Decision:** Phase 10 v2's detection anchor is derived from the tick archive under a pre-registered rule, at a pre-registered set of polling intervals. It is not sourced from the spine, and it is not the Phase 8 `det_minute` artifact.

**Definition:**
- **Reference price:** tick-derived T-1 regular-hours close. Phase 8 already computes this as `tick_close_t_minus_1_rth`; reuse the definition, recompute the value.
- **Trigger:** the running maximum of T=0 trade price reaching or exceeding `threshold × reference`.
- **Threshold:** 1.30 at the reference point, matching universe construction. Carried as a config parameter with its own sensitivity grid.
- **Detection time:** the first poll boundary at or after the trigger.

**Why the polling interval is mandatory and not a refinement.** Defining detection as the instant of crossing produces a detection time no real scanner could achieve — no polling interval, no feed latency, no bar close. That biases detection-to-peak **upward**: more apparent runway than exists. It is the optimistic direction, on the number every downstream phase is anchored to. Making the interval an explicit parameter is the only way that bias stays visible.

**Poll grid (confirm or override before commit):** instantaneous, 1s, 5s, 15s, 60s.
**Instantaneous is the explicit upper bound on runway and must be labeled as such on every chart and in every table where it appears. It is not a candidate operating point.**

**Threshold sensitivity grid (confirm or override before commit):** 1.25, 1.30, 1.35.

---

## Tasks

- [ ] **R1.0 — Preconditions**
  - [ ] Confirm branch `phase/10` at `2ae8c95`; confirm cohort content hash still `e1a0ac73a79aa573`.
  - [ ] Commit this prompt as `prompts/phase_10_v2_r1.md` before any other work.
  - [ ] Commit.

- [ ] **R1.1 — Record D7 and fix the docs allowlist**

  **Escalation row 13 is amended.** The v2 prompt restricted writes to `prompts/`, `config/`, `research/phase_10/`, `results/phase_10/` — which makes it impossible to record a decision where decisions are recorded. This conflict was flagged at the end of v1 and reproduced in v2. It is a prompt defect, not a data question.

  Row 13 now permits **append-only** writes to `docs/Universe-Decisions.md` and `docs/Research-Library-Map.md`, for decision entries and phase entries respectively. Every other `docs/` path stays out of scope, and no existing line in either file may be modified or deleted.

  - [ ] R1.1a — Append D7 to `docs/Universe-Decisions.md` using the D7 text above, in the file's established entry format.
  - [ ] R1.1b — Append the Phase 10 entry to `docs/Research-Library-Map.md`, still missing from v1.
  - [ ] R1.1c — **D6 is not yet in the decision record either.** If `docs/Universe-Decisions.md` has no D6 entry, append it from `D6_decision_record.md`. D6 is a standing decision currently existing only in conversation.
  - [ ] R1.1d — Commit.

- [ ] **R1.2 — Relabel the v1 artifacts**

  `results/phase_10/REPORT.md` and `digest.json` still present themselves as the phase's report while describing the superseded segmentation approach. Read cold in six months, the burst counts read as findings.

  - [ ] R1.2a — Rename to make the v1 evidentiary role explicit (e.g. `REPORT_v1_superseded.md`, `digest_v1_superseded.json`), and add a header pointing to D6. Content is otherwise unchanged — this is the evidence D6 rests on and is retained per D6 consequence (b).
  - [ ] R1.2b — Commit.

- [ ] **R1.3 — Derive the detection anchor**

  Per D7, for every cohort event, at every poll interval, at every threshold in the sensitivity grid.

  - [ ] R1.3a — Recompute the T-1 regular-hours close from tick. Report events where it is undefined; these are carried and flagged, never imputed.
  - [ ] R1.3b — Compute the trigger crossing and resolve it to each poll boundary.
  - [ ] R1.3c — **Never-crosses.** Phase 8 found events in-universe whose tick crossing does not exist. This is an expected consequence of D4: the universe was selected on `momentum_pct` computed from quarantined spine numerics, and we are re-deriving on tick. **Flag, carry, report as their own row. Never drop, never impute, never fall back to a spine value.** The count is a headline number.
  - [ ] R1.3d — **Detection segment.** Tag each event premarket / regular-hours / after-hours by its detection time, per the pinned session calendar. Segment is established as behaviourally material and becomes a **conditioning variable carried through every Phase 10 v2 timescale table** — not a footnote, and not something to be rediscovered downstream.
  - [ ] R1.3e — Commit.

- [ ] **R1.4 — Cross-check against Phase 8**

  At the 60-second poll, this anchor should approximately reproduce Phase 8's `det_minute` (110/114 usable, minute grain). It is a free validation of both.

  - [ ] R1.4a — Report per-event agreement and the disagreement distribution.
  - [ ] R1.4b — **Disagreement beyond the config tolerance is a hard stop, not a reconciliation exercise.** One of the two is wrong and which one matters. Do not adjust either to fit the other.
  - [ ] R1.4c — Commit.

- [ ] **R1.5 — Resume**

  Escalation row 9 is satisfied when R1.3 completes with the never-crosses count reported. Resume `prompts/phase_10_v2.md` from **T0c**, with the amendments below in force.

---

## Amendments to `prompts/phase_10_v2.md`

**T2b is replaced:**

> **Detection anchor.** Derived per D7 — first poll boundary at or after the running maximum of T=0 trade price reaches `threshold × tick-derived T-1 regular-hours close`. Computed at every poll interval and every threshold in the config grids. Not sourced from the spine; no spine timestamp exists. The instantaneous-poll variant is an upper bound on runway and is labeled as such everywhere it appears.

**Escalation row 9 is replaced:**

> Derived detection anchor undefined for a cohort event, for any reason other than the pre-registered never-crosses condition | any | Hard stop. Never-crosses events are flagged and carried per R1.3c and are **not** an escalation.

**Escalation row 13 is amended** per R1.1: append-only writes to `docs/Universe-Decisions.md` and `docs/Research-Library-Map.md` are permitted.

**Every T3, T4, and T5 quantity that references detection is now computed per poll interval**, and every detection-derived table carries the poll interval as a reported dimension. Chart 03 gains a poll-interval series. **The reported detection-to-peak distribution is not a single distribution — it is a family indexed by polling interval, and the spread across that family is a headline number.**

**Every timescale table is additionally reported split by detection segment** per R1.3d.

---

## Pre-registered failure criteria — additions

| # | Failure mode | Observable | Threshold |
|---|---|---|---|
| 7 | Anchor does not exist for the cohort | Share of cohort events in the never-crosses condition | Config; propose and justify |
| 8 | Phase 8 disagreement | Share of events where the 60s-poll anchor differs from `det_minute` beyond tolerance | Config |
| 9 | Polling dominates the answer | Ratio of median detection-to-peak at the instantaneous poll to that at the 60s poll | Config |

Row 9 is the one to watch. **If detection-to-peak collapses as the polling interval widens, the runway is an artifact of assuming instantaneous detection** — which is the specific bias D7 exists to expose. That is a finding, and it must be reported plainly rather than resolved by selecting the poll interval that gives the friendlier number.

Row 0 — Cooper's visual review — remains the operative criterion and now covers the detection marker's placement on the tape as well as the intensity profile.

---

## Reporting

Post, each with n:

1. Reference-price table — undefined count, per group
2. **Never-crosses table — count and share, per group, with the D4 explanation stated**
3. Detection anchor table — detection time distribution per poll interval, per threshold
4. **Detection segment table — premarket / regular-hours / after-hours counts**
5. Phase 8 cross-check table — agreement and disagreement distribution
6. Failure rows 7–9 — observed against threshold, pass/fail
7. Docs-record confirmation — D6 and D7 entries appended, Phase 10 map entry appended
8. Verification block per §10
9. Commit list

**Description only. Do not select a poll interval, do not select a threshold, and do not propose a runway figure.** Those reads are Cooper's.

---

## One thing to state plainly in the report

Detection comes from a price threshold. Peak comes from arrival intensity. Both are computed from the same T=0 tick stream. **These are different quantities and the comparison is legitimate, but the report must say so directly** rather than leave a reader to assume the two anchors are independently sourced. State it once, in the method section, without hedging.
