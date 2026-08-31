# Handoff — Phase 10e, Phase 12, and the leaned plan

**Prepared:** 2026-08-30 · **For:** a fresh Claude Code session · **Author:** chat layer (architect role)
**Nothing in this folder is authorised until Cooper says so.** Every `[Cooper]` slot is unfilled by
design; the agent fills none of them.

> ## ⚠ LANDED 2026-08-30 — read this box before anything else
>
> These files were pasted into a session and written to disk that day. **Four things were found on
> landing.** Two were corrected, two are flagged and left for Cooper.
>
> **1. The numbering collision the handoff predicted actually happened.** §4 below said the drafts were
> numbered D23–D26 "on the basis that D22 was taken by the scale-space close-out." **D23 was already
> taken** — appended earlier the same day as *"The causal re-derivation reverses D22's lead result"*
> (`docs/Universe-Decisions.md` line 904, commits `d026a1d` / `f0c1039`). The register was read to
> confirm, per this file's own instruction and Phase 10e escalation row 22. **The drafts are now
> D24–D27** in `docs/decisions_draft_D24_D27.md`, and cross-references here and in
> `docs/operating_plan_s6_replacement.md` were shifted to match. **References to D23 inside
> `prompts/phase_10e.md` and `config/phase_10e.json` were NOT touched** — those point at the real,
> taken D23 and are correct.
>
> **2. Draft D25 (was D24, "fast detection and ride") cannot be appended as written.** Its first bullet
> closes onset prediction partly because `dL/dln s` *"necessarily **lags** a level statistic … measured
> at −0.21 in units of `s`."* That is the centred-kernel number and **D23 reversed it**: under a
> one-sided kernel the field **leads** by +1.515 kernel widths on 19/19 events, paired within event,
> Wilcoxon p = 1.9e−05. The *conclusion* may well survive — saturation is untouched, the base is 19 of
> 100 events, and the fixed-kernel control is unrun — but the stated reason does not. Flagged in place,
> **not rewritten**; the wording is Cooper's. Draft D27's *"derivable and not yet applied"* is stale for
> the same reason and is annotated too.
>
> **3. Corrected, factual only:** `config/phase_10e.json` pointed `scale_field_module` at
> `research/scale_space/scale_field.py`, which does not exist and neither does that directory — the
> module is at `research/scale_field/scale_field.py`, and Arm 2 T5b would have failed to import. All
> three prompts said "cut from `main`"; there is no `main` branch (`origin/HEAD -> origin/master`), so
> they read `master`.
>
> **4. Flagged, not changed, because they are Cooper's:** `arm2_max_events = 75` against a causal cohort
> of **78** — that fires escalation row 5, which also forbids silently reducing the cohort. And the two
> different D7 anchor artifacts (`phase_8/a102_detection_anchors.parquet` here vs.
> `phase_10/v2_r13_detection.parquet` in the scale-space arc), both cited as D7.
>
> **Also observed, read-only:** `claude/scale_space_lessons.md`, cited in §3 as the authority for a
> closed item, **does not exist in this checkout.**
>
> **State at landing:** `phase-11-approved` exists at `05ccbfc`; `master` is 70 commits ahead of it (the
> scale-space arc, D22, D23) — **Phase 10e escalation row 1 fires as written** and needs your clearance.
> `event_minute_bars_v2` = **45,925,350**, matching row 7 exactly. All five frozen artifacts present.
> Working tree clean. `results/phase_11/digest.json` has **no `status` field** — T0a asks for it.
>
> **Neither Phase 10e nor Phase 12 can begin:** every `[Cooper]` slot is unfilled and both row 2s
> hard-stop. `prompts/universe_scan_scoping.md` carries no `[Cooper]` slot and is not blocked.

---

## 0. Read this first, in this order

1. `CLAUDE.md` (repo root) — standing constraints.
2. `docs/Agent_Prompt_Standard.md` §§7–12 — the format contract every prompt below follows.
3. `docs/Universe-Decisions.md` — D1–D23. **Read D5, D13, D19, D21, D22 and D23 before anything else.**
4. `docs/Claude-Code-Operating-Plan.md` §6 — then the replacement in `docs/operating_plan_s6_replacement.md`.
5. `results/reports/phase_11_report.md` — the cost stack. Its numbers set Phase 10e's barriers.
6. `prompts/phase_10e.md` — the phase to run.

**Do not** read the Phase 10 v1–v4 / 10b / 10c / 10d reports as instruction. They are closed. §3 below
says what is closed and why, and reopening any of it is an escalation, not a judgement call.

---

## 1. Where the programme actually is

**Phases 0–9 done. Phase 10 – 10d closed as a lineage (D21). Phase 11 done. Phase 12 not started.**

The 10-series asked one question across six versions and two diagnostics: *can a burst be defined as an
object on this tape?* The answer is no, and it is now well-evidenced rather than merely unproductive:

- **D21** closed threshold-from-trough and every repair inside it, including exact partition.
- The scale-space arc that followed closed the continuous version: the field derivative is bounded below
  by −1 and saturating (so it fires constantly under a sign condition and never under a magnitude one);
  the cross-channel divergence is degenerate against its Poisson reference (~100% ON share, 4 onsets
  across 75 events). **Only a thresholded rate ever fired reliably.**
- What survived is one derived criterion: **`s_min = 2.26/λ`**, the smallest timescale a tape of rate λ
  can resolve. It is the first applicability gate in the programme that is derived rather than adopted.

> **Amended on landing, per D23.** The third clause of the second bullet — *"only a thresholded rate ever
> fired reliably"* — was true of the **centred** kernel. Under a one-sided kernel the field boolean leads
> the level detector by +1.515 kernel widths on 19/19 contributing events. **D22's saturation fact and
> the `D` degeneracy both survive unchanged; the "it necessarily lags" half does not.** The causal floor
> is `s_min = 4.51/λ`, exactly twice the offline one. See D23 and `results/scale_field/REPORT.md` §15.

**What the 10-series never asked is whether any of it predicts price.** Phase 8 measured forward returns
from session- and day-anchored points, which D5 reads as archive. Phase 11's capture denominator was a
fixed-horizon hold that `model_selection_session_notes` §8 had already retired. So after eleven phases,
**capture on the intraday path is unmeasured.**

**Phase 10e is that measurement, and it is the last act of the 10-series.** It closes the saga by asking
the question the saga was ultimately for.

---

## 2. The Phase 11 number that shapes Phase 10e

Row 11's kill threshold did not fire — median round-trip cost ÷ realized capture **0.1608** at 1× against
a 0.50 trigger. The number underneath it:

| quantity | value |
|---|---|
| realized capture **non-positive** | **52.86%** of the named cell (n = 10,544) |
| rows with a **defined** ratio | **3,363 — 31.9%** |
| the 0.1608 median is computed on | that 31.9% |

The phase reported this honestly — pre-registered reading rule T7e-i caught it — but **the trigger was a
median ratio, which is conditional on the trade having made money**, so it could not act on it.

Two things follow, and both are built into `prompts/phase_10e.md`:

1. **Phase 10e's kill condition is a share, not a ratio.** A share is defined on every candidate entry.
   No quantity whose denominator can go non-positive may carry a gate in this phase.
2. **Every degeneracy reading rule is written before the run**, not discovered in the output.

**What Phase 11 delivered and Phase 10e consumes:** round-trip cost **70.98 bp / 2.512 cents** at 5-minute
latency, RTH. That is the unit the barriers are expressed in. Every entry must clear roughly **71 bp at
1×, 106 bp at 1.5×**.

---

## 3. Closed. Do not reopen. Reopening any of these is an escalation

Each needs a numbered Cooper decision to revisit, not an agent judgement.

| Closed | By |
|---|---|
| Hawkes calibration; branching-ratio estimation | D8, D9 |
| Two-state regime segmentation; "burst vs. quiet" as a split | D6, D8, D11, D13 |
| Constant-reference thresholding; envelope fitting; print aggregation | D8, `config/phase_10b.json` |
| Threshold-from-trough, all selection rules, and exact-partition replacement | **D21** |
| A burst timescale as an established number | D13 |
| Deriving a free parameter from a Poisson reference | scale-space close-out; **note: `claude/scale_space_lessons.md`, cited here originally, does not exist in this checkout — the standing record is D22/D23 and `results/scale_field/REPORT.md`** |
| Autoregressive conditional duration; fixed-bar volatility models; bars of any kind | `model_selection_session_notes` §1, §5 |
| The two-channel divergence `D` as a detector | D22 §14.3, **re-confirmed under the causal kernel by D23** — 3 and 2 onsets over 78 events |

**One rule generalises all of it and is worth holding in mind while writing code:**

> A parameter-free construction is only parameter-free relative to its reference. If the reference is a
> null the data violates by more than a decade, the "free" boolean is degenerate, and restoring it costs
> exactly the parameter that justified the construction.

`s_min` survived because its reference is **sample size**, not a distributional null. Apply that test to
any new "free" criterion before building on it.

---

## 4. What is in this handoff

| File | What it is | Status |
|---|---|---|
| `prompts/phase_10e.md` | The phase to run. Two arms; Arm 1 gates Arm 2. | Draft — needs Cooper's thresholds |
| `config/phase_10e.json` | Every tunable. `[Cooper]` slots unfilled. | Draft |
| `prompts/phase_12.md` | Halts & LULD. Independent data path, runs in parallel. | Draft — needs Cooper's thresholds |
| `config/phase_12.json` | Same. LULD band table entirely unfilled. | Draft |
| `prompts/universe_scan_scoping.md` | Scope and feasibility only. **Executes no scan.** **No `[Cooper]` slot — not blocked.** | Draft |
| `docs/operating_plan_s6_replacement.md` | Replacement §6 phase map + the superseding note. | Draft |
| `docs/decisions_draft_D24_D27.md` | Four decision texts for Cooper to take, amend, or reject. | **Drafts. Not decisions. Renumbered on landing.** |

**Decision numbering was not verified when this was written, and it was wrong.** D23 had already been
taken. The drafts are now **D24–D27**. **First task of any session that appends a decision: read the tail
of `docs/Universe-Decisions.md` and confirm the next free number from the file, not from this folder.**
It has now been stale twice — near-collision at D20, real collision at D23.

---

## 5. Order of work

| # | Work | Depends on | Notes |
|---|---|---|---|
| 1 | **Phase 10e Arm 1** | Phase 11 approval; **row 1 clearance (master +70)**; `[Cooper]` slots | Zero tick passes. Minute-bar caches only. |
| 2 | **Phase 10e Arm 2** | Arm 1's gate | Targeted per-event tick reads. Only if Arm 1 clears. Resolve the 75-vs-78 cohort cap first. |
| 3 | **Phase 12** | `[Cooper]` LULD band table | Parallel with 1 and 2. Different data path entirely. |
| 4 | **Universe scan scoping** | nothing — **the only unblocked item** | Parallel. Produces a written assessment, no measurement. |
| 5 | Re-specified 14 / 17 / 18 | Phase 10e result | Not drafted. Scope depends on what 10e says predicts. |
| 6 | Phase 19 | everything | Unchanged. |

Rows 13, 15 and 16 do not appear as phases. See `docs/operating_plan_s6_replacement.md` for why, and
`docs/decisions_draft_D24_D27.md` **D26** for the disposition text.

---

## 6. The two failure modes this handoff is written against

**The first is the programme's own.** Six versions of Phase 10 built the instrument before testing the
premise. Phase 10e is deliberately small, its expensive arm is gated behind its cheap arm, and its kill
condition is pre-registered. **If Arm 1's gate fails, stop. Do not run Arm 2. Do not repair Arm 1.**

**The second is the reporting boundary.** The executor measures and describes; it does not interpret.
"Median MFE at the 5-minute horizon is 84 bp, n = 41,203" is required. "Which suggests the path carries
tradeable excursion" is Cooper's, and writing it fires an escalation row. This is not ceremony — five
real defects in the scale-space build and eleven specification defects in 10b were caught by tests and
gates, and mostly in assistant-supplied code and prose. The gates are the part that has worked.

**A third instance, from the day this landed.** The causal re-derivation found a forward read in
`knn_rate()` — `lo = i - k//2` took k/2 prints from *each* side of `t`, so the scale selection was still
reading the future after the estimator had stopped. A re-run that swapped only the kernel would have
looked clean and still been cheating. And this file's own numbering warning caught a real collision the
same day it was written. **The gates keep finding things.**
