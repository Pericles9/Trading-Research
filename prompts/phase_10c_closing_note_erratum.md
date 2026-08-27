# Phase 10c — Closing Note, Erratum 1

**Date:** 2026-08-26
**Corrects:** `prompts/phase_10c_closing_note.md`, committed at `de10c6f`
**Status:** correction to a committed document. **Appended, not substituted.** The original stays as
the record of what was written; this states what was wrong and what is true.

---

## Why this exists

The closing note was drafted from `phase_10c_subburst_refinement_outline.md` — the pre-phase notes —
rather than from `config/phase_10c.json` and the Stage 1 artifacts. 10c departed from that outline on
several settled points, and the closing note carried the outline's language into a document that
purports to describe what ran. The Stage 1 agent caught it at T0 of the 10d preconditions check.

**Everything below is corrected against the committed record. Where this erratum and the original
disagree, the artifact wins and the original is wrong.**

---

## Corrections

| # | Original says | Committed record says | Where |
|---|---|---|---|
| **1** | "With the window redefined as clock-time and **trailing**" | The window is **centered**, clipped at RTH open/close and day edges. `trailing` and `anchored_to_detection` are listed forbidden variants. Resolution recorded 2026-08-24: *"CENTERED, as committed. The outline's trailing wording is void."* | §1; also §5 bullet 1 |
| **2** | §3 row 1 frames the anchoring as an open choice between "pure trailing wall-clock" and "anchored to event onset / the D7 detection anchor" | **Neither.** Both are forbidden variants. The question was closed 2026-08-24 in favour of centered, on the A2.5 density-inversion reasoning | §3 row 1 |
| **3** | "The **trailing window is causal** where v4's centred window was not… record which of the 16 non-causal fields this retires" | **Nothing was retired.** `n_retired_by_stage1: 0`. The window stayed centered, the causal debt is unchanged, and it remains parked for Phase 17 exactly as v4's audit left it | §3 row 7 |
| **4** | "Only the **single** validation kernel… was run" | Stage 1 computed **three** kernels — 2, 8 and 32 minutes — all reported. D5 = **8 min** is the primary | §4 bullet 1 |
| **5** | §3 rows 4 and 5 instruct comparison of a `no_threshold` share against v4's 10/100 | 10c's `no_threshold` share is **0% (0/504 cells), by construction** — the method never thresholds, so it cannot decline. `no_threshold` and `unimodal` appear zero times in the artifacts. **The label 10c actually carries is `insufficient_context`** — a different quantity with a different cause (the trailing-window data floor, not bimodality) — at 0%–42% across cells | §3 rows 4, 5 |
| **6** | §8 names "the first-trough rule" among the things 10d changes | 10c's committed rule is **`A2.7.D17_burst_envelope_boundary`: argmax void across ALL troughs, never thresholded.** `D13_void_parameter.threshold` is `null`, marked *deliberate and permanent*. The first-trough-at-0.70 rule was proposed inside 10c and **rejected** as contradicting config D13, "naming 0.70 as the retired v4 value" | §8 |

---

## What correction 6 means, because it changes more than a sentence

The closing note, and the 10d documents drafted alongside it, were built on the premise that the
threshold is still located by scanning left-to-right for the first trough clearing 0.70 — a rule
biased toward whichever mode sits nearest the short-interval peak.

**That rule is not what runs.** 10c selects the trough with the **highest void parameter across all
troughs** — the best-separated valley, wherever it sits, with no cutoff. That is a materially better
rule, it handles more than two modes by construction, and it removes the specific bias the 10d drafts
were built to correct.

**Consequence for what comes next:** trough selection is no longer the leading suspect for the
residual scale problem. **Burst assembly is** — the rule that a sub-burst is a run of *strictly
consecutive* sub-threshold intervals, which splits one sustained burst into several whenever a single
interval crosses back over the threshold. Phase 10d is rescoped accordingly and now changes assembly
only. See `prompts/phase_10d_spec.md`.

---

## What the closing note got right and is unaffected

- That 10c stops at Stage 1 and the remainder goes to a new phase number rather than an extension.
- That 10c is neither a negative-result close nor an unqualified success, and must be written as
  both halves in the same paragraph.
- The instruction to record what was **not** run — the wide log-spaced multi-kernel grid beyond the
  three committed kernels, the animated histogram, and the four cross-kernel interpretation
  diagnostics — and that these were deferred on Cooper's call, not abandoned on evidence.
- The retirement of the count-vs-print-count hard-stop gate, carried forward.
- All four Open-Items entries, with item 3 amended per correction 5: the population to characterise
  is `insufficient_context`, and separately the fact that **10c declines no event on bimodality
  grounds at all**, which is itself worth logging against D9's Zaliapin reasoning.
- §8's core instruction — do not fix the residual scale problem inside 10c by moving a parameter.

---

## Action

Commit this file to `prompts/` alongside the original. **Do not edit `de10c6f`'s content.** Where the
Stage 1 report or digest has already stated any corrected item per the original, correct it here and
list the discrepancy rather than rewriting history — the standing rule that the artifact wins and
discrepancies are reported, not silently fixed.

---

## Agent note appended at 10d T1b, 2026-08-26

Committed verbatim as received. Two observations recorded rather than silently edited, per the same
artifact-wins rule this document establishes:

1. **Correction 5's parenthetical says "the trailing-window data floor."** The window is centered —
   this erratum's own correction 1 establishes that. The floor is the centered-window per-interval
   derived floor (`wcount >= (sqrt(pi/2)*sigma_log10/log10 F)^2`, `F = 1.5`) plus the cell-level
   `ok.sum() >= 50` minimum. The word "trailing" there is residue of the same outline wording this
   document voids.
2. **Correction 5 and the "cannot decline" phrasing are exact on the void axis and slightly strong
   in general.** `D13_void_parameter.threshold: null` means void ranks and never gates, so 10c cannot
   decline on void magnitude. A decline path on *peak count* does exist in
   `research/phase_10c/s1_t1_subbursts.py` — fewer than two Poisson-surviving peaks, or no valid
   trough pair, emits `no_threshold`. It fired 0/504 on this cohort. Phase 10d T3c states it that
   exact way.
