# Scale-field arc — closeout and recap

**Date:** 2026-09-11 · **Type:** closeout. Records no new decision; D26 is the decision.
**Covers:** the instrument-gates run through the D26 sweep and the Allan scope work.
**Audience:** you in six months, and the next phase's agent.

---

## 1. What was asked, and what came back

**Asked:** is the scale field detecting bursts on the tape, or picking up noise?

**Answer:** neither, in the end. **The field is a correct instrument. There was nothing in the timing
channel for it to find.** On this cohort, above 10 ms, both channels return the session envelope and
nothing else, under four controls. Below 10 ms the structure is order fragmentation, and the cohort was
already recorded as unable to measure there.

**The arc cost three retracted headlines to get there, and every retraction came from a control rather
than from a review.** That is the most transferable thing in this document.

---

## 2. Established — survives, all of it derivation- or control-based

| # | Result | Basis |
|---|---|---|
| 1 | **Rate channel finds nothing beyond the envelope.** Apparent 30 s crossover scaled as ~2.6h across a 300× bandwidth sweep; positive control `S30` returned 89.2 s against the real tape's 86.9 s | bandwidth family + positive control |
| 2 | **Interval channel finds nothing above 10 ms.** Divergence crosses zero at a 10 ms collapse tolerance **simultaneously at 1 s, 8 s and 64 s** | scale-invariance of the crossing |
| 3 | **Sub-millisecond runs are not events.** Sequence-contiguous 0.933 (0.987 at 0.1 ms) vs 0.000 null; price-monotone 0.868 vs 0.450; condition code 14 (`Intermarket Sweep`) enriched 7–15× | identity, not timing |
| 4 | **The D9 sub-burst objects were most likely not events** — one order, many prints. Closes what `resolution_floor_finding` §2 left explicitly open | follows from 3 |
| 5 | **No usable Allan regime on this tape.** Envelope-only ceiling / h = 0.55 → 0.19 as h grows; `A(T)` is valid only well below the finest scale on which the rate varies, and here the rate varies at every scale | bandwidth sweep |
| 6 | **Dense and non-isolated at every scale in 8–512 s.** Blob width sub-Poisson everywhere, never above — negative regions cut short by neighbours. An isolated bump can only widen them | closed-form geometry, calibrated 1.99–2.10 on Poisson, 2.838 vs 2.828 at σ=s |
| 7 | **Instrument properties.** Trade-weighted zero-sum to 1e-18; `sd(F)` table; width calibration; the empty satisfiable band at `rf = 1` (`n_eff = 8`, `2·sd = 0.785`, floor −1) | arithmetic, no null involved |

**Item 7 is recorded as instrument properties, not operating choices** — there is no operating point left
to choose between.

---

## 3. Withdrawn — and why each one fell

| Withdrawn | Replaced by | Mechanism |
|---|---|---|
| "Detects cleanly at `read_factor = 4`" | a scale-anchored statement | read factor is not a scale; the same `rf` reads 4.4 s in RTH and 153 s premarket |
| The 30 s crossover | nothing — artifact | re-estimating `λ̂` at bandwidth `h` from a tape already smooth at `h` composes to `h√2`, so any tape with an envelope shows spurious excess below ~3h |
| Sub-Poisson deficit as a finding | bias, two mechanisms | surrogate estimation noise 1–32 s (Poisson base tape read 0.628 against the real tape's 0.873); collapse dead time ≤31 ms |
| The Allan clustering premise | nothing | `A(T)` never had a rate-matched control; on the collapsed tape every rung is reproduced by a surrogate at or above the real value |
| v3's 128 s RTH knee | withdrawn | envelope-only `A(128 s)` runs 2.0–44.9 across every bandwidth tested |
| v3's 16 s premarket knee | corrected, marginal | 1.00 if the rate is smooth below ~100 s, 1.22–2.36 if it varies at 30 s or finer; this tape's envelope curvature is 92–111 s. **Quotable only with the bandwidth assumption stated** |
| rf 1 vs rf 4 absolute magnitudes | between-read-factor part survives | denominators were the retracted surrogate |

**Root cause of the largest one, worth carrying:** `phase_10_v3.md:73` stated that the Allan factor
"tolerates a slowly-varying underlying rate" **without the regime in which that is true.** Downstream it
read as drift-immunity, and the whole ladder became quotable. **A robustness claim stated without its
regime becomes a licence.**

---

## 4. What this changes for the pending rows

**This is the section the next phase's author needs.** Nothing below is a decision; each is a consequence
for you to confirm against the Operating Plan.

| row | name | consequence |
|---|---|---|
| **11** | Spread & impact by participation | **Unaffected and already the deliverable of record** — round-trip **70.98 bp / 2.512 cents** at 5-min latency, RTH. Its "burst vs quiet" half is now permanently unspecifiable, not merely blocked. Mark it closed rather than pending |
| **13** | Interval distribution | **Largely absorbed.** The interval channel ran, on a properly collapsed tape, with the fragmentation mode identified and removed. Anything 13 still wants should be scoped against what was already measured |
| **14** | Feature extraction | **Re-scope.** Any feature defined as a property of a burst object has no referent. Features defined on the continuous field remain possible; features defined on price/size are untouched |
| **15** | Burst hazard function | **Dead, and now for a stated reason.** `P(death \| age)` requires episodes with ages. Result 6 says there are no isolated episodes at any measurable scale. This should be recorded as closed by D26, not left as "structurally dead" |
| **16** | Regime labeling + stability | **Its answer is partly known in advance.** A label set cut from a dense, non-isolated field will be unstable under perturbation — the `persistence_octaves` seed-dependence is that result appearing early. If 16 runs, it should report the seed-stable fraction as a first-class quantity rather than discovering instability as a finding |
| **17** | Detector + end-detector | **The end-detector half has no object.** Bursts that never isolate do not end. The entry-signal-class question is also settled by evidence: nothing in this programme has predicted an onset, and D26 adds that in the timing channel there was no onset to predict |
| **18, 19** | Direction, joint walk-forward | **Untouched.** Both are price/size-channel work |
| **Parallel** | Unconditional universe scan | **Untouched and still the oldest open blocker.** It gates capital and multiplies every result in the programme, and it did not move while this arc ran |

**The scoping sentence that belongs in every one of these:** D26 closed the **timing** channel. Every
quantity in the arc derives from *when* prints happened. **Price and size were never examined**, are not
barred by D4, and are where rows 11, 18, 19 and the excursion work already live.

---

## 5. What is carried forward as reusable

- **The four-control standard** — negative, positive, null-parameter sweep, **blindness**. The fourth is
  the one normally absent: a negative and a positive both return "no detection" when the method works *and*
  when it has been tuned deaf.
- **The retraction sweep** — a decision that withdraws a premise carries the list of everything that cited
  it, three labels. Ten rows on D26; it found a live detector's blocker rationale resting on the withdrawn
  curve.
- **Scope conditions on robustness claims**, with the corollary this run earned: **when the regime is
  itself a function of a free parameter, it is swept, not quoted.**
- **Envelope invariance as a selection criterion**, with its own scope condition — "invariant to rate
  variation slower than the kernel," not unconditionally.
- **The identity-collapse rule and the code-14 mapping** — data-layer facts every future phase needs.
- **Goals-and-tests as a prompt format**, with its precondition: it works once a question is derived far
  enough to pre-register its numbers. Before that, the step-by-step standard.

---

## 6. What remains open

1. **Capture on the path has never been measured.** Eleven phases in, against a measured cost of 70.98 bp.
   That is the programme's gap and D26 does not touch it.
2. **The universe scan**, unscheduled and gating capital.
3. **Three blocked record edits** — `CLAUDE.md`'s D26 pointer index, its `data/Schema.md` pointer, and the
   git-discipline block from another session. **Three separate commits when that file frees up.**
4. **The wrong-partition question** — if the impact and ISO-share work both return null, whether the 119
   cells were the wrong partition is the honest thing left to ask.
5. **ISO share as a hold-length variable** — specified as such from the outset, since D24 closed entry
   timing on cost scaling.

---

## 7. Closeout mechanics

Against the house convention, adapted — this arc was not a numbered phase, so there is no digest or tag to
cut.

- [ ] **Operating Plan §6** — mark the scale-field line closed, gate outcome *no structure in the timing
      channel above 10 ms*. **Insert-only; renumber nothing.** Mark row 15 closed by D26 and annotate rows
      13, 14, 16, 17 per §4.
- [ ] **`docs/Research-Library-Map.md`** — the gate scripts, the control tapes (`S30`, `NS05`, Poisson
      base), the bandwidth-sweep artifacts, and the prior-art entries (SiZer, Dümbgen–Spokoiny, spike-train
      surrogates, Legéndy & Salcman, Kepler injection–recovery, Chakravarty et al. on ISOs).
- [ ] **`docs/Open-Items-Register.md`** — close the sub-burst reality question (result 4) and the
      applicability-gate item; open the wrong-partition question and the `persistence_octaves` stability
      item.
- [ ] **Charts** — `results/scale_field/charts/instrument_gates/` is gitignored by the same rule as the
      panel charts. **Open the retraction pair locally at least once** (`bandwidth_family_ratio.html`,
      `subsecond_collapse.html`); neither is legible from a table, and this record asserts what they show.
- [ ] **`docs/amendment_draft_prompt_standard_v1_4.md`** — yours to fold in or reject. Until then the
      four-control standard lives only in D26.

---

## 8. The one-paragraph version

**The scale field works. This cohort's timing channel has nothing in it above 10 ms, and below 10 ms what
looks like structure is one order reported many times.** Three headlines were retracted on the way, each by
a control: a read-factor claim that was really a scale claim, a 30 s crossover that was the surrogate's own
bandwidth, and a sub-Poisson deficit that was estimator bias. The D9 lineage's sub-burst objects were most
likely never events, which is why eight versions of object definition never survived a tape review.
**Closed rather than abandoned — the first time this question has been.** The price and size channel, where
the programme's remaining thesis lives, has not been opened.
