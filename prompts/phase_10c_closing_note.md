# Phase 10c — Closing Note

**Date:** 2026-08-26
**For:** the agent currently closing Phase 10c
**Author of this instruction:** Cooper
**Status:** close-out context and recording instruction. **Not a phase prompt, not an amendment.**
It authorises no new measurement, changes no method, and moves no parameter.

---

## 1. Why 10c stops at stage 1

Phase 10c existed to test one hypothesis. v4's sub-burst decomposition failed on scale — median
sub-burst duration 349 nanoseconds, order-fragmentation scale rather than anything legible on the
tape — and the hypothesis was that the cause was **the normalization window basis**: a window
defined as a fraction of print count (20% of sequence length), centred rather than trailing. A
window with no anchor in clock time has no reason to produce a clock-time-scale answer. 10c changed
the window basis and nothing else about the core mechanism.

**Cooper's read from the stage-1 chart review is that the hypothesis is confirmed at the stage it
governs.** With the window redefined as clock-time and trailing, the pipeline behaves as intended
through peak detection:

1. intervals normalize against a window that means something in wall-clock terms,
2. the log transform and histogram construction are well-formed,
3. peak-finding locates the modes the method depends on, and the bimodal structure is present and
   visible on review.

**The residual defect sits downstream of that.** What remains unsatisfactory is the step that
converts the normalized distribution into burst objects — and it is two steps, not one:

- **Threshold derivation.** Currently the first trough, scanning left to right from the
  short-interval peak, whose void parameter clears 0.70. The rule is local by design, so that it
  behaves identically regardless of how many modes exist further right. The cost of that locality is
  a known bias: it selects whichever mode sits nearest the short-interval peak, which is the
  fragmentation mode wherever one is present.
- **Burst assembly.** Currently maximal runs of *strictly consecutive* sub-threshold intervals. One
  interval marginally above threshold splits what is on the tape a single sustained burst into two
  shorter ones. This inflates count and deflates duration by construction.

Neither is a refinement of the window basis. Both change the mechanism **D9** fixes. By the lineage
convention this program has used since v3→v4, a mechanism change takes a new phase number and a
numbered decision. **That work is Phase 10d.** 10c closes with its own question answered.

---

## 2. How to characterise 10c in the report — read this before writing the verdict

**10c is not a negative-result close.** Phase 10 closed at `phase-10-approved` as a recorded
negative result. 10c does not close that way, and must not be written as a sixth failure.

**10c is also not a clean success.** It validated its hypothesis on one kernel and stopped before
the multi-kernel work that was the other half of its design.

Write it as what it is: **a scoped hypothesis test that returned a positive result on the stage it
tested, and located the residual defect one stage further down** — *unless §3 rows 3, 4 or 5 say
otherwise, in which case write what they say and flag the disagreement with §1 explicitly.* State the
confirmed part and the stopped-at part in the same paragraph so neither can be quoted alone.

Per the Evidence Standard: describe, do not recommend. Do not characterise any result as promising,
encouraging, or disappointing. The decision to route the remainder to 10d is Cooper's and is already
made — record it, do not re-argue it or justify it with results.

---

## 3. What must be on the record before the tag

Every figure below comes from stage-1 artifacts, carries its **n**, and cites its artifact path. **Do
not transcribe any stage-1 figure from this document — it contains none.** (The v4 figures it does
cite are from committed prior-phase artifacts and are there for comparison only.) Where a quantity
was not computed in stage 1, say so explicitly rather than leaving the row blank.

**§1's characterisation is Cooper's read from chart review, not a measured result.** Rows 3, 4 and 5
below are what put it on the record. Write them from the artifacts and let them say what they say —
including if they disagree with §1.

| # | Must be recorded | Why it matters later |
|---|---|---|
| 1 | **The exact stage-1 kernel specification as run** — window duration, and which of the two open definitions was used: pure trailing wall-clock, or anchored to event onset / the D7 detection anchor. (That the window is *trailing* rather than centred is 10c's defining change and is settled; the duration and the anchoring convention are what must be read off the artifact.) | 10c left the anchoring as an open question and the duration as a starting value. Whichever was implemented is now the de facto convention 10d inherits. It must be a recorded choice, not an undocumented one. |
| 2 | **The minimum-data floor for the trailing window** — its value, its units, its label for events that fail it, and the count of events that failed it, per segment | Replaces v4's `min_prints_for_normalization` (200, count-based). A time-based window needs its own floor and its own label. Same convention as `no_threshold` / `too_few_prints`: carried, labelled, never given a fallback. |
| 3 | **Peak-detection outcome across the cohort** — share of events yielding ≥2 detected peaks under the clock-time kernel, pooled and per segment, with the peak-finding parameters as run | This is the evidence that steps 1–3 work. It is the load-bearing positive result of the phase. |
| 4 | **Void parameter distribution and `no_threshold` share under the clock-time kernel**, pooled and per segment, **stated alongside v4's 10/100** | The direct comparison against v4 is the phase's headline. It answers whether the window change made the gate more or less applicable. |
| 5 | **Median sub-burst duration under the clock-time kernel, stated alongside v4's 349 ns**, with the full distribution (q25/median/q75/max), pooled and per segment | This is the number the whole phase was about. It must appear as an explicit before/after, whatever it shows. |
| 6 | **Sub-burst count vs. T=0 print count** — Spearman and log-log slope, **as a descriptive figure with no pass/fail attached** (see §5) | The gate is retired; the measurement is not. It stays comparable to v1/v3/v4's figures. |
| 7 | **Causal status of the new window.** The trailing window is causal where v4's centred window was not. Record the change against the v4 causal audit (`results/phase_10/artifacts/v4_causal_audit.parquet`) — which of the 16 non-causal fields this retires, and which remain | This was logged as Phase 17 rework debt. Retiring part of it is a real result and should not be lost. |

---

## 4. What was **not** run — record this explicitly

10c's design had a second half that was never executed. It was **deferred on Cooper's call, not
abandoned on evidence.** Anyone reading the record later must be able to tell those apart, or these
become orphaned the way v3's scale-separation result did.

State plainly, as its own section, that the following were specified in the 10c outline and **not
run**:

- The **wide log-spaced multi-kernel grid** (1 minute through an hours-to-multi-day ceiling,
  geometric spacing). Only the single validation kernel recorded at §3 row 1 was run.
- **Threshold location vs. window size, per event** — the diagnostic that distinguishes "the void
  gate is finding a real structural interval" from "the trough lands wherever the local median puts
  it."
- **Void parameter strength by kernel, per event** — the per-event map of which scales are legible.
- **Temporal overlap across kernels**, read off the animation.
- **Heterogeneity across events** — whether legible kernel scale tracks event duration, segment, or
  detection price decile.
- The **animated histogram through time** — the synced panel on the tape-review time axis, and with
  it the question of whether a single per-event threshold is the right object at all, or whether the
  histogram's shape shifts materially across a session.

**The consequence to record:** the "events don't share a clock" question, which motivated the wide
range, is **untested at the within-event level.** One kernel cannot test it. This is not evidence
against the wide-range argument; it is an absence of evidence either way, and it belongs on the
Open-Items Register rather than in the report's findings.

---

## 5. What carries forward to 10d unchanged

Record these as carried, so 10d does not have to re-derive or re-argue them:

- **The clock-time trailing window basis**, at the specification recorded under §3 row 1. This is
  10c's deliverable and 10d treats it as settled background.
- **The retirement of the count-vs-print-count hard-stop gate** (the old row 1). A positive relation
  between sub-burst count and print count is expected — a bigger, longer, more active event
  mechanically produces more sub-bursts under any reasonable definition. It is reported descriptively
  and **never functions as a gate that can hard-stop a phase.** This revision was made in 10c on
  Cooper's call and is sound independent of anything 10c measured.
- **Log-transform of inter-trade intervals.**
- **`collapse_same_timestamp`** as the reference tie-handling variant.
- **Histogram construction and peak-finding as specified** — bin width, range, prominence rule,
  minimum peak separation, no smoothing. Smoothing stays closed: it reintroduces the bandwidth
  parameter D9 exists to remove.
- **D4** — every computed quantity tick-derived, no spine numerics on any computation path.
- **Segment stratification** (premarket / regular-hours) at every task.
- **Cohort frozen**, hash asserted, no redraw.

---

## 6. Open items to log

Append to `docs/Open-Items-Register.md`, each with its source artifact and this phase as the logging
phase:

1. **Within-event multi-scale structure is untested.** The wide log-spaced kernel grid was specified
   and not run. Whether a single event is legible at more than one window scale, and whether legible
   scale tracks event characteristics, is unknown. **Unscheduled.**
2. **Whether the per-event threshold should be time-varying is unexamined.** The animated histogram,
   which was the instrument for this, was not built. If a session's histogram shape shifts materially
   across the session, a single constant threshold per event is the wrong object and the sub-burst
   definition itself would need reshaping. **Unscheduled.**
3. **The `no_threshold` population is still uncharacterized.** This item is already on the register
   from v4 (10 events, premarket 3/28, rth 7/70). Update it with the clock-time kernel's
   `no_threshold` set: whether it is the same events, and the size of the overlap. Do not close it —
   what distinguishes those events remains uninvestigated.
4. **The void cutoff (0.70) remains literature-adopted, not established on this data.** It is
   inherited from the spike-train convention the program has otherwise stepped back from as a
   calibration source. Carried unchanged; the tension is named rather than left implicit.

---

## 7. Close-out mechanics

- Set the Phase 10c digest `status` per the digest contract, with headline metric rows for §3
  items 3, 4, 5 and 7. **Post the exact digest diff before writing it.**
- Add a `surprises` entry if stage 1 produced one. Do not pre-judge whether it did — §3 rows 4 and 5
  are the comparisons most likely to hold one.
- Tag at the branch tip per the phase-tag convention and fast-forward `main`. The surviving results
  must not be left stranded on an unmerged branch — that is the failure Phase 10's own close-out
  existed to fix.
- Write scope is unchanged: `prompts/`, `config/`, `research/`, `results/`, plus **append-only** to
  `docs/Universe-Decisions.md` and `docs/Research-Library-Map.md`, per escalation row 13 as amended.
- **Record no new numbered decision in this close-out.** The decision that amends D9 belongs to 10d
  and is drafted with it. 10c's close-out records results, not method changes.

---

## 8. The one thing not to do

Do not treat the residual scale problem as something to fix inside 10c by adjusting a parameter —
the void cutoff, the first-trough rule, the run-length floor, or the window duration. Adjusting any
of them here is exactly the tuning the phase gates exist to forbid. **10c ends where its hypothesis
ends.**

For the record, so this is not misread as a promise: **10d reopens two of those four and closes the
other two.** The first-trough rule and the run-length floor are what 10d changes. The **window
duration** is fixed background in 10d — 10c's recorded specification, not re-derived, not gridded.
The **void cutoff** stays carried at 0.70 and unrevisited; it remains on the register as a named
tension, not a 10d task.

---

## Correction (2026-08-26, appended after reconciliation against the committed Stage 1 record)

The text above is preserved verbatim as received — it is what Cooper actually sent, and this repo's
convention is to keep an issued instruction on record rather than edit it after the fact. But its
technical description of what Stage 1 specified and ran does not match `prompts/phase_10c.md`,
`config/phase_10c.json`, or the tagged Stage 1 artifacts (`phase-10c-stage1`), on three load-bearing
points. Recorded here so nothing downstream — 10d included — inherits the wrong premise.

**1. The window is centered, not trailing — and was never trailing.** `prompts/phase_10c.md:178-182`
states, in the original design, "the local normalisation window is defined in clock time. It remains
**centered** ... Do not implement a trailing variant" — twice, for a stated reason
(`prompts/phase_10c.md:185`; `config/phase_10c.json` → `settled.D3_window._a2_5`): a centered window
spanning the 09:30 open would let RTH's 17x-denser print rate set the local median for premarket
intervals too. `config/phase_10c.json` → `settled.D3_window._c2_resolution` records this exact
question being raised and settled on 2026-08-24: *"CENTERED, as committed. The outline's trailing
wording is void."* Stage 1's own escalation table carried this forward as a hard stop (row 2, "any
trailing-window implementation") that never fired. **Consequence: the causal-status claim in §1 and
§3 row 7 is also reversed.** A centered window reads forward in time by construction — this is the
*same* non-causal property `results/phase_10/artifacts/v4_causal_audit.parquet` flagged in v4
(`local_median_log_interval`: "CENTRED moving median — reads forward in time by half a window ...
Phase 17 needs a trailing estimator"). Cross-checked directly: **0 of the 16 non-causal fields in
the v4 audit are retired by Stage 1** — every one of them (histogram, peaks, void parameter, the
threshold, the sub-burst objects, move share) still derives from a centered window over a completed
session. The causal debt is exactly where v4 left it, still parked for Phase 17, because the fix
that would have retired it (trailing) was tried in the outline stage and rejected for the density-
inversion reason above — not because it was never considered.

**2. The threshold rule Stage 1 ran is not "first trough left of peak, void ≥ 0.70."** That is v4's
retired rule. `config/phase_10c.json` → `cooper_values._class_E_fill_before_stage_0.D13_void_parameter`
is `null`, "deliberate and permanent... never thresholded in this phase" — 0.70 does not appear
anywhere in Stage 1's mechanism, and Stage 1's escalation row 1 (any void cutoff applied anywhere)
never fired. What Stage 1 actually ran is `A2.7.D17_burst_envelope_boundary`
(`research/phase_10c/common.py:envelope_boundary` / `s1_t1_subbursts.py`): the argmax of the void
parameter across **every** trough in the event, not the first one right of the short-interval peak,
adopted specifically because two earlier candidate rules that *were* local to that peak (Amendment
1, "A2.7/A2.8 Resolution") were measured to increase, not decrease, the rate of silently selecting
the wrong mode.

**The underlying concern in §1 is not wrong, though — it is just evidenced differently than
described, and Stage 1 already measured it directly rather than leaving it as a described risk:**
`s1_t5_summary.json` (T5b) found the tallest peak at-or-below the chosen boundary is the
fastest-arriving one only 38–42% of the time (57.9%–61.2% "silent selection", by kernel) — i.e. the
non-parametric, all-troughs rule *still* does not reliably land on a boundary that isolates a single
clean mode. `s1_t4_summary.json` (T4a) adds a second, independent signal: the per-event log-log
slope of threshold location against kernel width has median **−1.359**, not flat and not the ~1:1
free-parameter signature — a third pattern nobody had named going in. Both are real, measured
evidence that deriving a single burst-defining threshold and assembling runs from it is unresolved
mechanism work, which is exactly the category of problem §1 and §8 route to Phase 10d rather than
tune inside 10c. The routing decision stands; only the diagnosis quoted for it should cite these two
figures, not the retired v4 rule.

**3. The multi-kernel grid, the per-event diagnostics, and the animation were run in Stage 1 — none
of them were deferred.** §4 lists six items as "specified and not run." Five of them are exactly what
Stage 1's T1–T6 tasks are: the {2, 8, 32}-minute kernel grid (not one validation kernel — all three,
crossed with all three momentum-threshold variants, 168 (event, kernel) computations,
`s1_t1_cells.parquet`); threshold-location-vs-window-size per event (T4a, above); void-parameter
strength by kernel per event (T4b: kernel 32min best-separates 21 events, 2min 16, 8min 12,
`s1_t4_summary.json`); heterogeneity against event size/segment/price decile (T4c, `s1_t4_summary.json`
— neither correlation significant at p<0.05 in this dev sample); and the animated histogram through
time, synced across kernels (T6, both candidate layouts built, Cooper's combined-comparative choice
run on the full 56-event sample, `results/phase_10c/charts/s1_06_animation_full/`). **What is
genuinely not run**, and is the accurate content for §4: a kernel grid *wider* than the three rungs
{2, 8, 32} (this grid was derived as D5÷4, D5, D5×4 from the single RTH floor-clearing kernel D5=8 —
it was never meant to span "1 minute through an hours-to-multi-day ceiling"); and Stage 2 (the
multi-kernel scale-coupling gate) and Stage 3 (the full-population run), which is what "stage 1 —
not stage 2 or 3" actually refers to.

**What §1's headline conclusion gets right, unaffected by the above:** Stage 1 did confirm the
histogram/peak-detection chain works under a clock-time-normalized window — every event in the dev
sample produces a computable trough (0% `no_threshold`, against v4's 10/100 = 10%), and the resulting
sub-burst durations sit at session/market scale rather than at v4's 349 ns order-sweep scale (pooled
median 1.29 ms, `s1_t1_subbursts.parquet`). The corrected, evidence-cited account of all of this is
in `results/phase_10c/REPORT.md` (updated alongside this correction) and its cross-phase copy;
`docs/Open-Items-Register.md`'s Phase 10c close-out entry carries the accurate "not run" list
forward to 10d.
