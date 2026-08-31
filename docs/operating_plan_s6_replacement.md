# `docs/Claude-Code-Operating-Plan.md` §6 — replacement phase map

**Type:** proposed replacement text. **Not applied.** Cooper holds the Operating Plan and applies edits.
**Scope of change:** rows 10e (new), 13, 15, 16 dispositions, and one superseding note. **Rows 0–12, 14,
17, 18, 19, Opt-A and Parallel are unchanged in substance** — 10e is an insert, exactly as 10b was under
D10, and **nothing is renumbered.** The row-*n*-is-`prompts/phase_{n}.md` contract is preserved.

> **Landing note, 2026-08-30.** Draft-decision cross-references below were shifted by one
> (draft D25 → **D26**) because **D23 was already taken** by the causal re-derivation and the handoff's
> drafts renumbered to D24–D27. See `docs/decisions_draft_D24_D27.md`. References to the real D5, D10,
> D11, D13 and D21 are unchanged.

---

## Why 10e and not 20

The 10-series is the burst-detection saga: 10 (segmentation), 10b (arrival randomness), 10c (window
basis), 10d (assembly), Diag1, and the scale-space arc. Every version asked whether a burst is definable
as an object on this tape. **Phase 10e asks whether any of it predicts price**, which is the question the
saga was ultimately for and the only one that can close it. It belongs in the series, not after row 19.

This follows D10's precedent exactly: 10b was numbered as a continuation *"same object, better-founded
methods — and the numbering says so"*, and rows 11–19 were preserved unchanged. The same applies here.

---

## Replacement rows

Insert **immediately below row 10d** (or below row 10b if 10c/10d are not carried as their own rows):

| Phase | Name | Produces | Charts | Gate |
|---|---|---|---|---|
| **10e** | Does the path pay? Forward excursion, and the ceiling on timing detection | **Arm 1:** forward MFE/MAE per candidate entry across the path, both intra-bar ordering bounds, first-passage shares against arithmetic break-even, stratified by path position and by `s_min`. **Arm 2:** oracle-detector ceiling against a position-matched random control on the admissible cohort | Excursion ECDFs; outcome-share stacks; ordering-ambiguity heatmap; path-position and `s_min` stratification; oracle-vs-control ECDF; ceiling grid | **The path pays, or it does not.** Arm 1 gate: pessimistic `p_clear` against `p_breakeven`. Arm 2 gate: oracle − matched control, event-clustered CI. **A null on Arm 2 closes the timing-detector line** — non-causality only helps the oracle |

Replace rows 13, 15 and 16 with:

| Phase | Name | Produces | Charts | Gate |
|---|---|---|---|---|
| **13** | ~~Noise floor & tape characterization~~ — **FOLDED into 10e** | Its stated deliverable was interval and print-size distributions *"inside bursts vs. outside"*. **D11/D13 closed the burst/quiet split and `config/phase_10b.json` lists two-state segmentation as closed-do-not-reopen, so half of it has no object.** The remainder — interval distributions, the resolution floor, sub-burst composition, Allan structure — was delivered by the scale-space arc. What survives enters 10e as the `s_min` stratifier | — | **Does not run as a phase.** See D26 |
| **15** | ~~Burst hazard function~~ — **DEAD AS WRITTEN, absorbed** | Specified as *"duration distributions — P(death \| age)"*. **D13 and D21 leave no defensible burst durations, so its input does not exist.** The exit prior remains wanted and D5 budgets it at least equally with entry work — but its conditioning variable is now **time since entry**, not burst age, and it falls out of 10e's first-passage labels rather than needing its own phase | — | **Does not run as written.** See D26 |
| **16** | Regime labeling + stability | Unchanged in construction. **Deferred, not cancelled.** Its question is whether offline labels are stable under perturbation; if 10e's ceiling is flat there are no labels worth testing, and if it is not, the test belongs on **causal** labels, which do not exist until the detector phase | Label-set overlap under perturbation | Foundation solid, or sand — **evaluated after 10e, on causal labels** |

Row **12** is unchanged and is authorised to run **in parallel with 10e** — independent data path, no
shared artifact, no dependency in either direction.

Rows **14, 17, 18, 19** are unchanged in substance. Their **scope** is set by what 10e establishes;
none should be specified before it reports.

The **Parallel** row is unchanged and now has a scoping prompt (`prompts/universe_scan_scoping.md`).

---

## Superseding note — to be appended to §6, not to replace anything

> **Amended 2026-08-30.** The chain rows 10–15 was sequenced under D5 on the premise that the burst
> object would be established and every downstream horizon expressed in it. **D13 and D21 closed that
> premise.** Rows 10–10d and the scale-space arc produced one surviving criterion — the resolution floor
> `s ≥ 2.26/λ` — and no burst object, no burst timescale, and no detector.
>
> The consequence for the map is structural rather than cosmetic. **Row 15's input no longer exists**
> and row 13's *"inside bursts vs. outside"* framing has no object to split on. Both are disposed of
> above. **Row 10e is inserted to close the series** by asking the question the whole chain was for,
> which none of it asked: whether any timing state predicts price.
>
> The ordering consequence is that **10e precedes rows 14 and 16–19 in sequence while sitting before
> them in the map by number as well.** Row 12 is independent of all of it and runs in parallel. The
> Parallel universe scan is unchanged in status and remains a near-front blocker on row 17's operating
> point under D5 consequence (c).
>
> **What is not amended:** the row-*n*-is-a-filename contract, rows 0–9, the D5 strategy surface, and the
> approval-gate discipline in §1. Nothing here is renumbered and nothing is deleted.

---

## A note on §0.1 that should not be lost in the lean

§0.1's measurement / description / interpretation split is the control that has actually worked in this
programme. **Five real defects were found by tests during the scale-space build, and eleven specification
defects in 10b — mostly in code and prose supplied by the assistant, and the suite caught them where
review of the prose did not.**

The lean proposed here reduces **the number of phases**, not the rigour per phase. Every prompt in this
handoff carries a committed config, a satisfiability audit, escalation rows, a chart contract with
failure appearances, and pre-registered kill conditions.

Phase 11 is the argument for that, not against it: a threshold that was carefully set, pre-registered and
confirmed twice still watched the wrong quantity, because its denominator was non-positive on 52.86% of
its population and a median ratio cannot see that. **That calls for more care in writing the kill
condition, not less ceremony around it.**

> **A third datum for the same argument, from the day this landed.** The causal re-derivation found a
> forward read in `knn_rate()` — `lo = i - k//2` took k/2 prints from *each* side of `t`, so the scale
> selection was still reading the future after the estimator had stopped. Swapping only the kernel would
> have produced a clean-looking causal result that was still cheating. It was caught because the
> re-derivation was audited rather than declared, and because a test failed against itself on a
> coordinate bug. **The gates keep finding things; that is the argument for keeping them.**
