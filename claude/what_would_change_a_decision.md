# What result would change what decision

**Date:** 2026-09-10 · **Type:** scoping note. Records no decision. **Written before any next phase is
briefed**, per the standing question raised at review on 2026-09-09.

---

## 0. Why this document exists at all

**This lineage's failure mode was never a bad estimator. It was running phases whose outcomes could not
change a decision.** Eight versions of object definition ran after D13 had already re-anchored everything
downstream. The estimators were mostly fine. The work was not load-bearing.

So the gate on any next phase is one sentence, written before the brief: **what result would change what
decision?** If it cannot be answered in a sentence naming a specific decision and a specific direction,
the phase should not run.

**A phase passes this gate only if all three hold:**

1. **A named decision it could move** — a D-number in `docs/Universe-Decisions.md`, not "our
   understanding".
2. **A stated threshold, in advance** — the value at which the decision moves, derived not chosen.
3. **Both outcomes are informative** — if the null result changes nothing, the phase is a lottery ticket
   and the cost is real.

---

## 1. The binding constraint, stated first

**D24 and D25 closed tradeability on cost arithmetic, and Phase 11's own close-out named the cost stack
as the binding constraint.** The round trip is **70.98 bp**. D25 measured the day-scale markout median
negative at every horizon (−886 bp at T+3) and the intraday barrier grid clearing in 0 of 90 cells.

**So the honest default is that nothing in the price/size channel can change a decision either**, because
costs bind regardless of what an impact measurement returns. **Any next phase has to beat that
default explicitly, in its first paragraph, or it is D26's mistake in a new channel.**

That is the test the three candidates below are held to. Two survive it. One does not, in the form it is
usually proposed.

---

## 2. The three candidates, against the gate

### (a) Impact by participation — **survives, and it is the only one that can reopen the arithmetic**

| | |
|---|---|
| **Decision it moves** | **D24 and D25.** Both rest on a cost stack treated as exogenous. |
| **Threshold** | Realised impact at achievable participation materially **below** the 70.98 bp assumed round trip. Threshold must be set from the *gap* D25 measured, not chosen: the closest barrier cell missed by −0.210, so the cost reduction that would close it is derivable before the run. |
| **If it comes back the other way** | Informative, and strongly: it converts "costs bind, assumed" into "costs bind, measured", which **retires the last soft assumption under D24/D25** and makes those closures final rather than provisional. |

**This is the only candidate that can reopen the programme's central closure.** It is also the one whose
null result is most valuable, because it hardens two existing decisions rather than leaving them resting
on an unmeasured input.

### (b) ISO share as a state variable — **survives, and it is the most novel**

| | |
|---|---|
| **Decision it moves** | **D5's successor question** — not D5 itself, which is archived. An entry condition and, more importantly, a *hold-length* condition. |
| **Threshold** | ISO share at or before the anchor separates continuation from fade **by enough to survive 70.98 bp**. That is the number to pre-register, and it is derivable from D25's markout grid: the separation must exceed the cost, not merely be statistically significant. |
| **If it comes back null** | Informative. It closes the price/size channel's most literature-supported candidate on this cohort and makes D26's "this is not evidence these events lack tradeable structure" much narrower. |

**Why this one is genuinely different from everything already tried.** Every prior attempt in this
lineage measured *when things happened*. ISO share measures **who was trading and how badly they wanted
it** — a participant-type variable, not a timing variable. It has documented forward content (Chakravarty,
Jain, Upson & Wood, *Clean Sweep*, JFQA 2012, find ISOs carry disproportionate price discovery relative to
volume share). **And it is already in the parquet**, as a by-product of the fragmentation cleanup: `conditions`
code 14, confirmed, per print.

**The one thing to fix before it is briefed:** the only route past a cost floor is holding longer, not
trading better. So this must be specified as a **hold-length** question from the outset — does ISO share
predict *sustained* continuation — and not as an entry-timing question, which D24's cost-scaling argument
(fixed cost against √H movement) has already closed.

### (c) Book-walk depth as a universe filter — **does not survive as usually proposed**

| | |
|---|---|
| **Decision it would move** | D1's universe definition. |
| **Why it fails the gate** | **Prior and cost, not logic.** *(Corrected 2026-09-10: an earlier version of this row argued a filter "changes which events are studied, not whether any pay". That is too strong and is withdrawn — a subpopulation cutting across all 119 cells **can** pay while none of the cells does, which is the standard wrong-partition argument and is not closed by D25's coverage.)* What actually justifies the rejection: the prior is poor, D25's coverage is broad, and the covariate route tests the same thing for nearly nothing inside a phase that is running anyway. **That is a prioritisation call, not a proof** — recorded as one, so that "but the partition was wrong" cannot be walked back through later, which is the shape of argument that restarted this lineage twice. |
| **What would rescue it** | Only if run **as a stratifier inside (a) or (b)**, where it can move a threshold rather than define a population. Cheap there, and it costs nothing extra since the run structure is already characterised. |

**Stated plainly: depth is a covariate, not a phase.** Proposing it as its own phase is how this lineage
generated eight object definitions. **But it is rejected on priority, not on impossibility**, and if (a)
and (b) both return null the wrong-partition question is the honest thing left to ask — with the prior
stated in advance, and against the same 70.98 bp floor.

---

## 3. The recommendation, as a view

**(a) first, then (b), and (c) only inside them.**

Not because (b) is less interesting — it is more interesting, and §2(b) says why. But **(a) is the only
one whose result changes a decision in *both* directions**, and it is the one that determines whether (b)
is worth running at all. If realised impact confirms the 70.98 bp stack, then (b)'s threshold is known
before it starts and may already be unreachable; if impact comes back materially lower, (b)'s threshold
moves and the whole channel reopens.

**Running (b) first risks measuring a real effect that cannot clear a cost floor nobody has measured** —
which is a more sophisticated version of the mistake this document exists to prevent.

---

## 4. What would make me say "run nothing"

Stated in advance, so it is a criterion and not a mood:

**If (a) returns realised impact at or above the assumed stack, and (b)'s pre-registered separation
threshold is then computed to exceed anything the ISO literature reports** — the programme has measured
its closure from both ends and should stop rather than continue. **D26 closed a channel; that would close
the question.** It is worth saying now, before the numbers arrive, that this is a permitted outcome.

---

## 5. The format rule this arc earned

Recorded here because it belongs with the scoping decision rather than inside a finding.

**Goals-and-tests is the right format once a question has been derived far enough to pre-register its
numbers. Before that, the step-by-step standard is the right one.** They are phases of the same process,
not competing styles. This arc produced four retractions and a closed question in about a week on a line
that had gone a year without closing one — but it worked *because the numbers could be fixed in advance*.
The reading grammar's derivations existed, so freedom over method was safe. **In month one of this
programme, with no derivations to fix targets against, the same format would have produced confident
nonsense**, because goals-and-tests with soft targets is just an unsupervised agent.

Two smaller rules, both paid for in this arc:

- **A brief must carry its numbers inline.** Citing a path the agent's checkout does not contain nearly
  cost a run; it happened to buy an independent re-derivation instead.
- **Every gate needs a reference, not only a threshold.** Gate E's `r = 0.90–0.99` was unreadable until it
  had a ceiling, and the entire surrogate arc turned on the null's own free parameter being *swept* rather
  than picked. **A threshold without a reference is a number without a scale.**

**Against this, the next phase would be briefed step-by-step, not goals-and-tests** — the price/size
channel has no derived reading grammar, and the cost threshold in §2 is the only pre-registrable number
currently in hand.
