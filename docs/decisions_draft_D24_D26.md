# Draft decision texts — D24 to D26

**These are DRAFTS. They record nothing. Cooper takes, amends, or rejects each one.**

**Numbers are provisional and are fixed only at append time.** This file has been renumbered twice.
Before appending any of these, **read the tail of `docs/Universe-Decisions.md` and confirm the next free
number from the file itself** — not from this heading, not from `CLAUDE.md`'s pointer list. Phase 10e
escalation row 22 hard-stops on it.

## Revision history of this file

| Date | Change |
|---|---|
| 2026-08-30 | Landed numbered D23–D26. **Collided** — D23 had been taken the same day by the causal re-derivation. Shifted to D24–D27. |
| 2026-08-31 | **The entry-signal draft (then D27's neighbour, D25) is WITHDRAWN — see below.** The remaining three shift down to D24, D25, D26. |

| current | subject | was |
|---|---|---|
| **D24** | Phase 10e scoping and numbering | D23 → D24 |
| — | ~~Entry-signal class: fast detection and ride~~ | **WITHDRAWN 2026-08-31, consumes no number** |
| **D25** | Disposition of Operating Plan rows 13, 15 and 16 | D25 → D26 → D25 |
| **D26** | `s ≥ 2.26/λ` as the applicability gate | D26 → D27 → D26 |

**References to D23 inside `prompts/phase_10e.md` and `config/phase_10e.json` are NOT drafts** — they
point at the real, taken D23 (the causal re-derivation) and are correct as written.

Append-only, verbatim, to `docs/Universe-Decisions.md`.

---

## WITHDRAWN — Entry-signal class: fast detection and ride

**Withdrawn 2026-08-31 by Cooper. It consumes no decision number and is kept here only as the record of
why it was not taken.**

The draft closed onset prediction on three stated reasons. **D23 removed two of them:**

| reason as drafted | status after D23 |
|---|---|
| `dL/dln s` saturates (`≥ −1`), so it discriminates poorly | **survives, untouched** |
| it *"necessarily lags"* a level statistic — measured at −0.21 in units of `s` | **reversed** — +1.515 kernel widths, 19/19 contributing events, paired within event, Wilcoxon p = 1.9e−05 |
| *"LEVEL is the only channel that fired reliably"* | **false** — FIELD fires and leads under a one-sided kernel |

Saturation is a statement about **discrimination**, not about **onset versus confirmation**. It is the
only surviving leg and it does not carry the conclusion alone.

**So the evidence base for closing onset prediction was substantially removed by D23, and taking the
decision now would close a question the evidence had just reopened.** The draft was written the day
before D23 landed. Repairing the wording would have preserved a conclusion whose support was gone —
the exact failure mode this programme keeps hitting, a stale record that later work reasons from.

**No decision is taken on entry-signal class.** The open item stays open, annotated in
`docs/Open-Items-Register.md` with a pointer to D23 and to the three tests that now decide it:

1. **Null-rate matching** (Phase 10e T5b-i, escalation row 23) — until the channels fire at equal rates
   on burst-free tape, *"FIELD leads"* and *"FIELD is noisier"* are the same statement.
2. **The fixed-kernel control** — under a causal kernel `dL/dln s` weights recent lags while `λ̂`
   averages the whole half-kernel (centroid `0.80·s`), so a shorter level kernel may buy the same lead.
   Measured lead +1.52 against a 0.80 centroid gap: suggestive, not separating.
3. **Price conversion of the lead** — +1.180 s of lead is not yet a number in basis points. Phase 10e
   Arm 2 is where it becomes one, or does not.

**A decision that says "still undecided" is not a decision and should not consume a number.**

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

## D25 — Disposition of Operating Plan rows 13, 15 and 16

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

## D26 — `s ≥ 2.26/λ` as the applicability gate

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

**Recorded alongside — the causal form, derived and APPLIED.** A one-sided kernel keeps half the mass, so
both `Σw` and `Σw²` halve and `n_eff = √π·s·λ`. **The causal floor is therefore exactly twice the offline
one: `s ≥ 4.51/λ`.** A 1-second causal read requires `λ ≥ 4.51` prints/s sustained; the median event in
the anchor +60 s window sits at 4.88/s.

This is no longer arithmetic awaiting use. Under D23 it was implemented and run:
`scale_field.s_min_onesided()` / `s_min_for_rate(kernel="onesided")`, coefficient **4.5135**, pinned by
`test_onesided_neff_is_exactly_half_and_s_min_exactly_double`. It carried the causal Task 1 re-run, where
median `s*` moved 1.567 s → 2.506 s. The warning it was written to give — *do not specify a causal
construction against the offline floor by mistake* — is now enforced as Phase 10e escalation row 24.

Nothing else in D26 is affected by D23. The `2.26/λ` gate itself, and the reference test it establishes,
are untouched — that was the part of D22 which explicitly survived.
