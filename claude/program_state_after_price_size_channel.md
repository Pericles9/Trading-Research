# Program state, 2026-09-13 — what's actually left that a phase could move

**Type:** scoping note, same genre as `claude/what_would_change_a_decision.md`, generalized from the
price/size channel to the whole program now that both its candidates have a final disposition. **Written
because "proceed to a new phase" deserves the same gate every other phase in this lineage has been held
to** — a phase that can't name a decision it moves is the exact failure mode §0 of that document
describes, and picking one anyway to have something to run would be that failure mode in a new channel.

---

## 1. Where every live thread actually stands

| Thread | Status | Blocked on |
|---|---|---|
| Intraday timing/detector (D24) | **Closed.** Cost-scaling argument + 6/6 wrong-direction gradient. | — |
| Long thesis, both ends (D25) | **Closed.** 0/90 barrier cells, 0/29 markout cells, both below a matched null. | — |
| Within-session timing channel (D26) | **Closed.** No structure above 10ms; below 10ms is fragmentation on a cohort that can't measure there. | — |
| Candidate (a), impact by participation | **Closed, negative, measured.** Required cost (~11.0bp) is 4.6-6.5x below any achievable decile. | — |
| Candidate (b), ISO share hold-length | **Closed, not pursued.** Statistically well-powered at full tier (T4), but Cooper declined T5 — no measurement made either way. | Cooper's own call, already made |
| Candidate (c), book-walk depth | **Unrescued.** Needed (a) and (b) both null; (b) returned no measurement, not a null. | (a)/(b) resolving differently, which they won't retroactively |
| Universe scan — lookahead | **Closed, bounded not measured.** 6.5x displacement needed to churn 5% of membership; geometrically implausible. | — |
| Universe scan — live false-positive rate | **Open, but not by method.** `results/scope_universe_scan/REPORT.md` §15.1: "blocked on data acquisition... no further method will move it." | External data feed (D14 offline) |
| Short side / adverse tail (D25, "what this does NOT decide") | **Measured, not decided.** `t6_adverse_tail.json` exists; three things not in the repo could each close it. | Locate availability, halt risk, Reg SHO 201 — none in this checkout |
| Phase 12 — Halts & LULD | **Specified and drafted**, not run. | 16 `[Cooper]` slots citing verified exchange-mechanics documents — not agent judgment calls, not derivable from data on disk |
| Fundamentals (F1, D27-D33) | **Closed as a data-layer build.** `event_fundamentals` exists, verified 9/9. | **D32, explicitly: first analytical use needs a decision-relevant sentence, and "that sentence is Cooper's to write... not produced by this build."** |
| Operating Plan row 13 (noise floor) | Open, needs re-scoping against what already ran, not a fresh run. | A scoping judgment call — see §2 below |
| Operating Plan row 14 (signed flow feature layer) | Open, "re-scope, do not cancel." | Its original purpose (feeding rows 16/17's detector) is gone — see §2 |
| Operating Plan row 16 (regime labeling) | Its answer is partly known in advance (seed instability already observed). | `persistence_octaves` fix, itself unscheduled |
| Operating Plan row 17 (detector) | End-detector half has no object; entry-signal half already settled by evidence. | Effectively closed, not open |

## 2. Why rows 13/14 are not just picked up

Row 14's deliverable (signed volume, impact-efficiency, "cached, lag-baked") was scoped to feed the
detector work in rows 16/17. D26 closed the object those rows would have detected ("bursts that never
isolate do not end" — Operating Plan row 15's own cell). Building the feature layer now would be
infrastructure with no named consumer — **exactly** what §0 of `what_would_change_a_decision.md` opens
with: *"Eight versions of object definition ran after D13 had already re-anchored everything downstream.
The estimators were mostly fine. The work was not load-bearing."* Row 14 surviving in the Operating
Plan's insert as "re-scope, do not cancel" predates D24/D25/D26 landing in the form they did; the
Operating Plan itself has not been re-read against that closure the way this note is doing now. Same
reasoning kills row 13 as a fresh run — it would re-measure a channel (inter-trade timing) D26 already
closed, just under a different name.

**This is not "there is nothing left."** It is: everything with a named consumer is either closed,
blocked on data this environment cannot fetch (D14), or blocked on a decision that is explicitly
Cooper's to write, not mine (D32, and implicitly the same shape for Phase 12's exchange-mechanics
slots). Manufacturing a next phase around what's left over would be picking the object-definition
failure mode in a fourth channel.

## 3. What is not blocked, and is worth naming precisely

**Nothing in the current backlog clears the gate** (`what_would_change_a_decision.md` §0: a named
decision, a threshold derived in advance, both outcomes informative) **without one of the following
three things landing first, each specific and named, not a generic "more work":**

1. **A LULD band table and the other 15 `[Cooper]` exchange-mechanics facts** `prompts/phase_12.md`
   needs — cited documents Cooper has verified, per that prompt's own note that these "were never
   thresholds to set from judgement." Unblocks Phase 12 (halts/reopens), which D25 already flags as
   load-bearing under any thesis whose adverse side is unbounded — i.e. this is the one item on this
   list that D25 itself calls out as necessary, not merely available.
2. **The written sentence D32 reserves** — naming which decision a fundamentals-vs-outcome result
   would move, and the pre-registered threshold at which it moves — before any phase reads
   `event_fundamentals` against a market outcome. `docs/Universe-Decisions.md` D32 is explicit that
   this build does not produce that sentence and that its absence is not an oversight to fix, it is
   the boundary.
3. **External data for the short side or the universe scan's live false-positive rate** — locate
   availability, halt risk, Reg SHO 201 data, or a market-data feed the offline constraint (D14) does
   not currently allow this checkout to acquire.

**None of the three is a phase this session can run.** Two need Cooper's own input (a verified
reference table; a decision sentence that is explicitly not the executor's to write per D32's own
text — mirroring the Architect/Executor/Decider split `docs/Claude-Code-Operating-Plan.md` §0 states
as the load-bearing rule of this whole process). The third needs data acquisition this environment is
constitutionally unable to perform (D14).

## 4. Disposition

**This note does not propose a phase, and says so rather than picking one to avoid saying so.**
Consistent with `what_would_change_a_decision.md`'s own §4 in spirit (a "run nothing" finding is a
permitted, informative outcome, not a failure of the loop) — generalized here from "both price/size
candidates" to "every currently-open thread in the program." The three items in §3 are the concrete,
named things that would change this finding; each is stated so a future reader (or the next session)
can check whether it has landed rather than re-deriving this survey from scratch.
