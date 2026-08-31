# Draft decision texts — D24 to D27

**These are DRAFTS. They record nothing. Cooper takes, amends, or rejects each one.**

**RENUMBERED ON LANDING, 2026-08-30.** The handoff numbered these D23–D26 on the basis that D22 was the
last decision taken. **It was not: D23 was appended earlier the same day** — *"The causal re-derivation
reverses D22's lead result; D22's second structural fact does not survive"* (`docs/Universe-Decisions.md`
line 904, commits `d026a1d` / `f0c1039`). The register was read to confirm this, per the handoff's own
instruction and Phase 10e escalation row 22, and the next free number is **D24**. Every draft below is
shifted by one:

| handoff draft | now | subject |
|---|---|---|
| D23 | **D24** | Phase 10e scoping and numbering |
| D24 | **D25** | Entry-signal class: fast detection and ride |
| D25 | **D26** | Disposition of Operating Plan rows 13, 15 and 16 |
| D26 | **D27** | `s ≥ 2.26/λ` as the applicability gate |

Cross-references in `README_HANDOFF.md` and `docs/operating_plan_s6_replacement.md` were updated to match.
**References to D23 inside `prompts/phase_10e.md` and `config/phase_10e.json` were NOT changed** — those
point at the real, taken D23 (the causal kernel) and are correct as written.

**Before any of these is appended, re-read the tail of `docs/Universe-Decisions.md` and confirm the next
free number from the file itself.** It was stale once already today.

Append-only, verbatim, to `docs/Universe-Decisions.md`.

---

## D24 — Phase 10e scoping and numbering

**Date:** [Cooper] · **Deciding gate:** Cooper decision following the scale-space close-out

**Decision.** The forward-excursion and detector-ceiling work is numbered **Phase 10e**, not Phase 20. It
is the closing act of the 10-series — the same object the series has pursued since Phase 10, asked the
one question the series never asked.

**Consequence.** Operating Plan §6 rows **11–19, Opt-A and Parallel are preserved unchanged**, and the
row-*n*-is-`prompts/phase_{n}.md` contract established 2026-08-03 is not broken. **No downstream row is
renumbered.** This mirrors D10 exactly.

**Recorded alongside.** Phase 12 does not depend on Phase 10e in either direction and is authorised to
run in parallel on an independent data path.

---

## D25 — Entry-signal class: fast detection and ride

**Date:** [Cooper] · **Deciding gate:** the evidence accumulated across Phase 10 – 10d and the
scale-space arc

**Closes:** the open item recorded by D5 as *"Entry-signal class undecided — onset prediction vs. fast
detection and ride"*, left open 2026-08-03 to be decided before any detector phase is specified.

**Decision.** The entry signal is **fast detection and ride**. Onset prediction is closed.

**Why.** Nothing in this programme has predicted an onset, and three independent constructions have now
failed to:

- `dL/dln s` is **bounded below by −1 and centred**, both readable in one line from `E_w[z²] − 1`. It
  saturates, so a sign condition fires constantly (~2.8× the level detector's rate) and a magnitude
  condition almost never (2 of 200). It cannot go negative until a burst is **centred** in the kernel, so
  it necessarily **lags** a level statistic by a fraction of `s` — measured at −0.21 in units of `s`.
- `D = m + lograte/ln10 + γ/ln10` is degenerate against its Poisson reference: the tape sits 1.29 decades
  below the identity at the read scale, so `D < 0` is permanently true. ON share ~100%, 4 onsets across
  75 events.
- **LEVEL — a thresholded rate — is the only channel that fired reliably**, and it confirms inside the
  cluster rather than ahead of it.

**Consequence.** Detector work is specified as confirmation inside a regime, not anticipation of one.
Features, null distributions and latency budgets follow from that. **Reopening onset prediction requires
a numbered decision**, so that a fifth attempt cannot arrive under a new name.

**What is NOT closed.** That a *level* signal confirms early enough to be tradeable is exactly what
Phase 10e Arm 2 measures. D25 closes the signal **class**, not the question of whether the surviving
class pays.

> ### ⚠ LANDING NOTE — the first bullet is stale and this draft cannot be appended as written
>
> **Flagged 2026-08-30, not rewritten — the wording is Cooper's to fix.**
>
> The first bullet's clause *"it necessarily **lags** a level statistic by a fraction of `s` — measured
> at −0.21 in units of `s`"* is the **centred-kernel** measurement, and **D23 reversed it.** Under a
> one-sided kernel the field **leads** by **+1.515 kernel widths (+1.180 s)** on **19 of 19** contributing
> events; paired within event against the centred arm on those same 19, **3/19 → 19/19**, paired
> difference **+1.906 s-units, 18/19 positive, Wilcoxon p = 1.9e−05**. The word *"necessarily"* is the
> part that fails: the lag was a property of the centred kernel, not of the statistic.
>
> **What still supports the decision, unchanged:**
> - **Saturation** — `dL/dln s = E_w[z²] − 1 ≥ −1` holds under the causal kernel too, because
>   `dw/dln s = w·z²` regardless of the support restriction. D22 structural fact 1 is untouched.
> - **`D` is degenerate** — it fired its kill condition *again* under the causal kernel (3 and 2 onsets
>   across 78 events), so that bullet stands as written.
> - The causal lead rests on **19 of 100** cohort events, and under a causal kernel `dL/dln s` weights
>   recent lags while `λ̂` averages the whole half-kernel (centroid `0.80·s`) — **a shorter level kernel
>   might buy the same lead.** That is Phase 10e Arm 2 T5b-i / escalation row 23, and it is unrun.
>
> **So the conclusion may well survive; the stated reason does not.** Suggested minimum repair: strike
> *"necessarily lags … −0.21"*, replace with the saturation argument plus the 19-of-100 base and the
> unrun fixed-kernel control, and cite D23. Appending it unrepaired would put a superseded number into
> the register as the justification for closing a line of work.

---

## D26 — Disposition of Operating Plan rows 13, 15 and 16

**Date:** [Cooper] · **Deciding gate:** Cooper decision on the leaned plan

**Decision.**

**Row 13 — folded into Phase 10e.** Its deliverable was interval and print-size distributions *"inside
bursts vs. outside"*. D11 and D13 closed the burst/quiet split and two-state segmentation is
closed-do-not-reopen, so half of it has no object; the remainder was delivered by the scale-space arc.
What survives — the resolution floor `s ≥ 2.26/λ` — enters Phase 10e as a stratifier. **Row 13 does not
run as a phase.**

**Row 15 — dead as written, absorbed into Phase 10e's labels.** It was specified as *"duration
distributions — P(death | age)"*. D13 and D21 leave no defensible burst durations, so **its input does
not exist.** The exit prior remains a first-class deliverable and D5's budget for it is unchanged, but
its conditioning variable is **time since entry**, not burst age, and it is produced by the first-passage
labelling in Phase 10e rather than by a separate phase.

**Row 16 — deferred, not cancelled.** The label-perturbation stability test is unchanged in construction.
It is evaluated **after Phase 10e**, and on **causal** labels rather than offline ones. If 10e's ceiling
is flat there are no labels worth testing; if it is not, the labels the test should run on do not exist
until the detector phase.

**Consequence.** No row is deleted and no row is renumbered. Rows 14, 17, 18 and 19 are unchanged in
substance; their **scope** is set by what Phase 10e establishes and none should be specified before it
reports.

---

## D27 — `s ≥ 2.26/λ` as the applicability gate

**Date:** [Cooper] · **Deciding gate:** Cooper decision on the scale-space close-out

**Closes:** the question left open by Phase 10c open item 4 and Phase 10d §4 — whether an applicability
gate should exist and what it should be.

**Decision.** `s_min = 2.26/λ` is adopted as the applicability gate. A timescale `s` is measurable at a
moment only where `s ≥ 2.26/λ̂(t)`. Below the floor a quantity is carried, labelled, and never given a
fallback value — the same treatment as `insufficient_context`.

**Why this one and not the alternatives.** It is `n_eff = 2√π·s·λ ≥ 8` rearranged: **a statement about
how many effective observations sit in a window, not about the process generating them.** That question
has the same answer whether the tape is Poisson, Hawkes, or a multifractal cascade. It is the first
criterion in this programme that is derived rather than adopted, and it is the reason it survived when
both Poisson-referenced constructions did not.

**The test it establishes for future criteria**, and the reason this decision is worth taking rather than
leaving as a finding:

> Does the reference depend on the process being anything in particular? — it will fail on this tape.
> Does it depend only on how much data is in the window? — it will survive.

**Consequence.** `n_eff ≥ 8` is a convention and halving it halves the floor. That does not matter for
anything decided so far, because the gaps it has been used to establish are orders of magnitude rather
than factors. **Any future use where a factor of two would change a conclusion must state the convention
explicitly and report sensitivity to it.**

**Recorded alongside — the causal form, derivable and not yet applied.** A one-sided kernel keeps half
the mass, so both `Σw` and `Σw²` halve and `n_eff = √π·s·λ`. **The causal floor is therefore exactly
twice the offline one: `s ≥ 4.51/λ`.** A 1-second causal read requires `λ ≥ 4.51` prints/s sustained; the
median event in the anchor +60 s window sits at 4.88/s. This is arithmetic, not a measurement, and it
belongs on the record before any causal construction is specified against the offline floor by mistake.

> ### ⚠ LANDING NOTE — the closing paragraph's status changed on 2026-08-30
>
> *"derivable and **not yet applied**"* is no longer true. The causal floor **has** been derived,
> implemented and run under D23: `scale_field.s_min_onesided()` /
> `s_min_for_rate(kernel="onesided")`, coefficient **4.5135**, pinned by
> `test_onesided_neff_is_exactly_half_and_s_min_exactly_double`. It carried the causal Task 1 re-run,
> where median `s*` moved 1.567 s → 2.506 s. The arithmetic in the paragraph is correct and is
> corroborated by the run; only *"not yet applied"* wants changing, and the sentence about specifying a
> causal construction against the offline floor by mistake is now enforced as Phase 10e escalation
> row 24.
>
> Nothing else in D27 is affected. The `2.26/λ` gate itself, and the reference test it establishes, are
> untouched by D23 — that was the part of D22 which explicitly survived.
