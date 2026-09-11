# Draft amendment to `docs/Agent_Prompt_Standard.md` — Control Standard, Retraction Sweep, envelope invariance

**Date:** 2026-09-10 · **Status: DRAFT. Records nothing. For Cooper to mark up, fold in, or reject.**
**Source:** Cooper's proposed amendment of 2026-09-10, plus what the scale arc paid for.

**Why this is a draft file and not an edit to the standard.** `docs/Agent_Prompt_Standard.md` is the
document every phase prompt is written against, and the proposal was explicitly framed as Cooper's to
mark up. Amending it unilaterally would also make the standard the one document in this repo that
changed without the author deciding it should. **The three sections below are written in the standard's
own voice so they can be pasted in whole if accepted.**

**Nothing here changes who plans or who interprets.** The standard's Evidence Standard governs *how a
result is reported*; all three additions govern *whether a result is a result*, which the standard
currently leaves to the prompt author.

---

## §A — Control Standard *(new section)*

**Any claim of the form "real exceeds null" requires four controls.** One is not enough: the scale arc
produced three retractions with one control in place each time.

| control | asks | consequence of omitting it |
|---|---|---|
| **Negative** | does the procedure stay quiet on structureless data? | false positives read as findings |
| **Positive** | does it fire on known structure at the scale of interest? | cannot distinguish "no signal" from "wrong statistic" |
| **Null-parameter sweep** | is the boundary the data's, or the null's own free parameter? | **produced the 30 s crossover retraction** |
| **Blindness** | can the procedure still see anything here, or has it been tuned deaf? | nulls read as closure |

**The fourth is normally absent and is structurally invisible unless named.** A negative and a positive
control both return "no detection" when the method works *and* when it has been tuned into
insensitivity. Only a positive planted **at the edge of detectability** separates those.

**Corollary — the estimated-parameter null.** A null built by estimating a parameter from the data and
simulating from the estimate **is not unbiased at any setting of that parameter**: it carries estimator
noise as real structure at small bandwidth, and absorbs real structure at large bandwidth. The
conclusion must hold **across the family**, not at a chosen member. **A single-bandwidth null is a result
with an unreported free parameter.**

> **Worked instance, for calibration.** In the scale arc the crossover tracked the surrogate's bandwidth
> at ≈2.6h over 1–300 s, and a structureless positive control reproduced the real tape's crossover to
> within 0.5 s. Separately, at `T = 4 s` a known-Poisson tape read `0.628` against the real tape's
> `0.873` on the same statistic — **the control was more anomalous than the data**, which is what
> identified the deficit as procedure bias rather than a finding.

---

## §A2 — Scope conditions on invariance claims *(new, and it caused the arc's root failure)*

> **A robustness or invariance claim stated without the regime in which it holds becomes a licence.**
> Every such claim carries the bandwidth, scale range, or sample condition under which it is true, **in
> the same sentence**. *"X is insensitive to Y"* is not a usable statement; *"X is insensitive to Y for
> `T ≪ L`"* is.

**The worked instance is the root cause of the whole scale arc.** `prompts/phase_10_v3.md` stated that the
Allan factor *"tolerates a slowly-varying underlying rate."* True — and true only for `T` well below the
envelope's own variation scale, because `A(T)` differences successive counts, which cancels a trend
approximately linear across `2T`; once `T` approaches the scale on which the rate actually curves,
successive windows straddle different rates and the cancellation stops. **v3 stated the property and not
the regime**, and downstream that read as *"Allan is drift-immune, full stop"*, after which the whole
ladder was quotable and a year of work rested on it.

**It happened twice in one week.** The first draft of §C below said "prefer statistics provably zero under
a locally-Poisson rate path" as though the property were unconditional. It is not: `D` is exactly zero
only where `λ` is constant **across the kernel**. *"Envelope-invariant"* means *"invariant to rate
variation slower than the kernel"* — a scope condition, in precisely the position where v3 left one out.
**Two instances of one failure in one week, one of them in this amendment**, which is the argument for a
rule rather than a habit.

**Corollary — a scope condition is measured, not assumed.** When the regime is itself a function of a free
parameter, it is swept, not quoted. The Allan ceiling was expected to be a single observable number; swept
over the surrogate bandwidth it moves from 5.5 s to 57.7 s as `h` goes 10 s to 300 s. **The usable output
was not a ceiling but a dependence**, and quoting the single-bandwidth value would have been the §A
corollary's failure inside the section that defines it.

---

## §B — Retraction sweep *(new section)*

**When a decision withdraws a premise, the same commit carries the list of everything that cited it.**

**The gap this closes.** The decision register is append-only and citations run one way, so nothing links
a premise back to its citers. D26 withdrew the Allan clustering premise, which was load-bearing in a
build brief, a committed config's rationale field, a phase prompt, two working documents, **and the
blocker rationale of a detector heading for live use.** The last was found by accident while doing
something unrelated. **No mechanism in this project would have found it on purpose.**

**Requirement.** A decision that retracts anything includes a sweep table: every file that cited the
retracted quantity, each marked

- **`withdrawn`** — the claim goes;
- **`corrected`** — the claim needs restating, not deleting;
- **`unaffected — same conclusion, another route`** — the document cites the premise **and is still
  right**, because its conclusion has an independent derivation.

**The third label matters as much as the first two.** Without it a future reader cannot distinguish a
sound conclusion from an unreviewed one, and marking it is a positive statement rather than a dodge.

**Cost.** The search is a grep for the premise's distinctive numbers. D26's sweep took minutes and is
appended to that decision as the worked example.

**Two rules the first sweep produced, worth carrying:**

1. **A committed config's rationale field is swept but not edited.** Outputs are keyed by config hash, so
   amending a `why` string silently re-keys every artifact that config produced. **The correction lives
   in the decision; the config row says the rationale is stale and points there.**
2. **Historical prompts are bannered, not rewritten.** A phase prompt is the record of what was asked.
   A retraction banner at the head preserves the record and warns the reader; editing the body destroys
   the audit trail the standard exists to protect.

---

## §C — Envelope invariance *(new selection criterion)*

**Prefer statistics that are provably zero under a locally-Poisson rate path. When choosing one that is
not, the prompt must say so and say what removes the envelope.**

**This is a design criterion, not a caution.** The session envelope has now masqueraded as signal in
**four** distinct statistics on this data: the rate channel's field, the surviving cells under a
magnitude threshold, the Allan factor at every rung, and the interval channel's `G` (derived in closed
form in the detector thread, measured at `D` = −0.02 to −0.29 in the gates thread — two methods, one
conclusion). **On this tape, any statistic not explicitly envelope-invariant will report the envelope.**

The cross-channel divergence `D = m + lograte/ln10 + γ/ln10` satisfies the criterion: identically zero
under a locally-Poisson process **at any rate path**, so the envelope cancels by construction rather
than by correction. **That property is why it was the right instrument, and it should be the first thing
asked of the next one — before the estimator is written, not after its first result needs explaining.**

**A statistic that is not envelope-invariant remains admissible**, but the prompt must then state (i)
what removes the envelope, and (ii) which controls prove the removal worked.

> **Caveat that belongs with the criterion.** Envelope-invariance is a property of the *population*
> statistic. `D` is exactly zero only where `λ` is constant **across the kernel**; within-kernel rate
> variation drives it negative with no clustering present. So invariance narrows what a control must
> rule out — it does not remove the need for one.

---

## §D — Three rows for the anti-pattern table

| anti-pattern | why it fails |
|---|---|
| **Ratio to a null whose magnitude is itself scale-dependent** | the denominator collapses at one end of the axis and the ratio explodes with no change in the numerator. **The 40.9× at `read_factor = 1` was division by nearly nothing**, and the ratio was non-monotone in the read factor (37 / 46 / 21 / 11), which no property of the read should be. **Report absolute excess in `sd` units alongside any ratio.** |
| **A threshold quoted without a reference** | a number without a scale. Gate E's `r = 0.90–0.99` was unreadable until it had a ceiling — and the ceiling then ate the whole figure above 16 s, leaving an excess of 0.00–0.02. |
| **Feature counts on a dense, interacting field, reported without their spread over seeds** | dense-and-interacting is the **only** regime on this cohort — every quantile of the negative-run width sits at or below the Poisson value, never above, which is the signature of features packed closer than `2s` and truncating each other. So seed-dependent counts are the normal case here, not a corner case. **Either measure the field instead of counting features, or report the count distribution and the seed-stable fraction as first-class quantities.** |

**The third row is a class, not an instance.** It is the same ambiguity that defeated the burst mark — a
boolean extracted from a continuous field, unstable because the field has no gaps to cut at —
reappearing in a different detector (`persistence_octaves`, 6/7/7/6/7 and 7/6/5/6/5 on a dense tape).
**Worth fixing as a class.**

---

## §D2 — Known property, recorded rather than fixed: the config hash covers rationale text

Outputs are keyed by config hash, and the hash covers **every** field including `why` strings that cannot
affect any computation. So a stale rationale cannot be corrected without orphaning every artifact the
config produced — which is why D26's sweep marks `config/scale_field.json`'s `noise_reference.why` as
withdrawn-and-not-edited.

**Not worth fixing now**, and recorded so it is a known property rather than a surprise: **a hash over
computational fields only would let documentation be corrected without re-keying artifacts.** If the
config schema is ever revised, that is the change to make.

---

## §E — Note on the format rule, for wherever the standard discusses prompt style

Not proposed as a section; recorded so it is not lost. Full text in
`claude/what_would_change_a_decision.md` §5.

**Goals-and-tests is the right format once a question has been derived far enough to pre-register its
numbers. Before that, the step-by-step standard is right.** They are phases of one process, not
competing styles. The scale arc produced four retractions and a closed question in a week — but it
worked *because the numbers could be fixed in advance*. **With soft targets, goals-and-tests is just an
unsupervised agent.**

Two supporting rules, both paid for:

- **A brief must carry its numbers inline.** Citing a path the agent's checkout does not contain nearly
  cost a run.
- **Every gate needs a reference, not only a threshold.**
