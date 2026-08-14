# Phase 10b — Close-Out (CO10b): The Record, and Instructions to Write It Up

**Date:** 2026-08-13
**Decision (Cooper):** **Stop.** Phase 10b closes as a recorded negative result. No third amendment. No indirect-inference round. Row 15 stands.
**Trigger:** A10b.2 escalation row 5 — knee usability criteria 2 and 3 failed (injected scale inside the 95% interval on 0 of 4 controls; common bias rejected).

This document has two parts. **Part 1 is the record** — every decision, finding, error and piece of prior art from the Phase 10b design and gate work, so none of it lives only in a chat transcript. **Part 2 is the task list** to verify that record against artifacts, write `results/phase_10b/SUMMARY.md`, and close the repo.

**Part 1 is not authoritative on numbers.** It is my transcription and it may contain errors. **Every number in it must be verified against an artifact before it enters the summary**, and any discrepancy is reported, not silently corrected. This is the v2 lesson: a prompt once asserted a spine column that never existed, on the phase's headline input.

---

# PART 1 — THE RECORD

## 1.1 What Phase 10b was for

Phase 10 tried five method families to find a burst timescale and all five failed the same way: each needed a reference level or a resolution — a bandwidth, window, or threshold — and the answer tracked that choice rather than the market.

Phase 10b reframed the question. "Bursty" and "Poisson with a time-varying rate" are not distinguishable without constraining how fast the rate may vary; let the rate wiggle freely and it absorbs every cluster, force it flat and everything is bursty. The well-posed version:

> **At what timescale do arrivals stop looking random, given a rate allowed to vary more slowly than that?**

Two methods, cross-checked: an Allan factor against a **matched** inhomogeneous-Poisson null, and time-rescaling under a **held-out** intensity estimate. A synthetic control harness gated both.

**Phase 10b never read a real event.** It failed at its own control gate, three times.

## 1.2 Decisions taken

| # | Decision | Status |
|---|---|---|
| **D10** | Numbered **10b**, a continuation of Phase 10, not Phase 11. Operating Plan §6 rows 11–19 preserved unchanged; the row-*n*-is-`prompts/phase_{n}.md` contract not broken | Recorded |
| — | Phase 10 closed as a recorded negative result and merged, so its surviving findings stop being stranded on an unmerged branch | Executed |
| — | **Failure criteria are synthetic controls with known answers, not outcome thresholds.** Outcome thresholds passed in every Phase 10 version while both arms were wrong; a threshold on an outcome cannot detect a method stably measuring the wrong object | Executed — and it worked |
| — | Timescale ladder 2^-20 to 2^12 s, 33 rungs. v3's 19 rungs are a strict subset, preserving rung-for-rung comparability | Executed |
| — | Bandwidth sweep 2^-6 to 2^14 s, 21 rungs, deliberately degenerate at both ends so a crossing on an endpoint is identifiable as a boundary artifact | Executed |
| — | Intensity fitted **out of sample**. In-sample fitting guarantees a crossing whose location is set by the estimator's degrees of freedom — Phase 10's failure mode in a new hat | Executed |
| — | Agreement bands pre-registered: ≤1 rung agreement, 2 rungs partial, >2 rungs hard stop | Never reached |
| — | Comparison to theoretical flat-rate Poisson (A = 1) **banned**. v3's A = 1,245 at 4,096 s is consistent with the known non-flat rate and is not evidence of clustering | Standing |
| **A10b.1** | Crossing statistic changed from band-departure to **knee**; held-out block length h/4; directional band rule (upward excursions only); C2 bandwidth restricted to h ≤ its injected rate timescale; T6 wording repaired | Executed |
| **DX10b.1** | Satisfiability audit; excursion-structure diagnostic; global envelope test; knee sampling distribution by parametric bootstrap | D1, D2 executed; D3 blocked |
| **A10b.2** | Row 15 override granted; drop the block-print floor; strike C3's time-rescaling row as void; offline validation triad replacing the reference-implementation route; C2 rung restriction conditional on a C2′ prediction | T1–T2 executed; T3 onward never run |
| **CO10b** | **Stop.** Close as a negative result | This document |

## 1.3 New decisions to record now

Append to `docs/Universe-Decisions.md`, verbatim, as **D11–D14**. Wording is fixed; do not paraphrase.

> **D11 — The Allan knee cannot recover a cluster timescale**
> **Date:** 2026-08-13 · **Gate:** Phase 10b close-out
> The piecewise-linear breakpoint on a log-log Allan curve is a **sharp but biased** estimator of cluster timescale. Across 500 draws per control its 95% interval spans 0–1 rung while the injected scale falls inside that interval on **0 of 4** controls. Bias is +0.97 to +1.61 rungs on single-scale controls and −2.91 rungs on the coarse transition of a two-scale control. The bias is a deterministic consequence of fitting straight lines to a smoothly-curving function — the fitted asymptotes intersect inside the transition region, pushing a fine transition up and pulling a coarse one down. It is **not** a fixed offset: it depends on the separation between scales, which is unknowable on real data. **No burst timescale is established by this program.**

> **D12 — v3's Allan knee carries a scale-dependent uncertainty**
> **Date:** 2026-08-13 · **Gate:** Phase 10b close-out
> v3's regular-hours knee at 128 s and premarket knee at 16 s are flat→rise transitions, structurally the same kind of transition that carries the −2.91 rung (factor 7.5, downward) bias on control C4. Applying single-scale bias instead gives +1.4 rungs (factor 2.6, upward). **The true scale behind v3's 128 s therefore sits somewhere in roughly 50 s to 1,000 s, and behind 16 s in roughly 6 s to 120 s.** These ranges are too wide to anchor a trading horizon. v3's knee remains valid as evidence that a transition **exists**; it is not valid as a measurement of **where**.

> **D13 — D5's premise fails; downstream phases re-anchor**
> **Date:** 2026-08-13 · **Gate:** Phase 10b close-out
> D5 required a burst timescale to anchor every downstream horizon. No such timescale is available at usable precision. **Phases 13, 14, 16 and 17 re-anchor to detection time, clock time, or price-path events** rather than to a burst scale. The specific re-anchoring for each phase is scoped when that phase is drafted; this decision records only that the burst-scale anchor is unavailable. **This is a first-order program finding, not a sixth failure.**

> **D14 — Environment is offline**
> **Date:** 2026-08-13 · **Gate:** Phase 10b close-out
> No package index, no R, no network fetch. Any prompt requiring an external package, a reference implementation, or a downloaded artifact must state an offline fallback at drafting time. `reuse-before-build` applies only to what is already installed. *(Also append to `CLAUDE.md` standing constraints.)*

## 1.4 Findings — Phase 10b control harness

**Verify every figure against artifacts.** Reported here as transcription.

### Run 1 — original T2. Failed all four controls.

Four **implementation** defects, all found by the controls and fixed before any result was taken:

1. In-sample band fitting, violating the config's own circularity note — would have produced tight, confident, wrong bands, and every downstream out-of-band call would have been inflated with nothing flagging it
2. Integrated intensity snapped to grid nodes — mean rescaled interval 0.027 instead of 1.0
3. A grid that could not represent the 60 s block structure
4. Missing edge correction, halving the intensity estimate at the widest bandwidths

After fixes: homogeneous Poisson passes the rescaling test at every h ≥ 64 s, mean rescaled interval 0.995–1.004. Sparse Allan verified exactly against a dense reference on 200 cases.

### Run 2 — T2-R5 under the original prompt

| Passed | |
|---|---|
| Band coverage | 0.9348–0.9460 against [0.90, 0.99] |
| C3 plateau height | 5.9852 vs size-weighted mean 6.0000 (−0.25%) |
| C4 scale separation | peaks at 7.6e-6 s and 32 s, separation 4.19e6 |

| Failed | |
|---|---|
| C1 inside-band share | 0.871 at h = 64 s |
| C2 inside-band share | 0.774 at h = 16,384 s |
| C1 time-rescaling interior crossing | h = 64 s |
| C3 knee | 9.537e-7 s vs injected 1e-5 |
| C3/C4 time-rescaling crossing | none at any eligible h |

### Run 3 — A10b.1 T2-R5

| Control | Check | Required | Observed | |
|---|---|---|---|---|
| C1 | inside-band, upper-only, min over all eligible h | ≥ 0.90 | 0.9677 | PASS |
| C1 | time-rescaling interior crossing | none | none | PASS |
| C2 | inside-band, upper-only, min over h ≤ 1404 s | ≥ 0.90 | 0.8710 | FAIL |
| C2 | time-rescaling interior crossing | none | none | PASS |
| C3 | plateau vs size-weighted mean | ±25% | −0.246% | PASS |
| C3 | knee recovers 10 µs | ≤ 1 rung | +1.610 | FAIL |
| C3 | time-rescaling recovers 10 µs | ≤ 1 rung | target outside sweep | FAIL |
| C4 | two scales separated | ≥ 1024 | 4,194,304 | PASS |
| C4 | knee recovers 60 s | ≤ 1 rung | +2.907 | FAIL |
| C4 | time-rescaling recovers 60 s | ≤ 1 rung | none | FAIL |
| C3′ | knee recovers 1 ms | ≤ 1 rung | +0.966 | PASS |
| C4′ | knee recovers 100 ms | ≤ 1 rung | +1.322 | FAIL |
| All | band coverage | [0.90, 0.99] | 0.9292–0.9497 | PASS |

Row 4d fired: `block_floor_event` 17.45–22.63 s, binding share 0.6190 of the 21-rung sweep against a 0.40 threshold — 13 of 21 bandwidths ineligible.

Knee recovery detail — k = 3 selected on every control, ΔBIC vs k = 1 between 84.0 and 97.2. Breakpoints: C3 3.05e-5 and 256 s; C4 6.10e-5 and 8 s; C3′ 2.44e-4 and 1.95e-3; C4′ 0.015625 and 0.25.

### DX10b.1 — D1 satisfiability audit

Eligible share of the 21-rung bandwidth sweep at the controls' rate, `block_floor_event` = 17.45 s:

| Block rule | Eligible | Share |
|---|---|---|
| No block-length rule (pure h/4) | 16/21 | **0.762** |
| Original fixed 60 s | 11/21 | 0.524 |
| The alternative A10b.1 rejected | 9/21 | 0.429 |
| **A10b.1's max(h/4, floor)** | 8/21 | **0.381** |

Reachability: C3's time-rescaling target 10.61 rungs below the sweep floor — unreachable. C4's target inside the sweep but nearest eligible bandwidth 128 s, 1.09 rungs against a 1-rung tolerance — **made unreachable by A10b.1, by 0.09 of a rung.** All four knee requirements reachable.

### DX10b.1 — D2 excursion structure

| Control | h | Above | Runs | Rungs |
|---|---|---|---|---|
| C2 | 256 | 3 | [2,3] | T = 128, 256, 512 s |
| C2 | 1024 | 4 | [2,4] | T = 128, 256, 512, 1024 s |
| C2 | 4096 | 4 | [1,2,4] | same four |
| C2 | 16384 | 4 | [1,2,4] | same four |
| C1 | 256 / 16384 | 1 each | [1,2] | T = 6.1e-5 s |

C2's upward excursions are **contiguous**, at the four highest eligible rungs, whose pooled pair counts fall 181 → 90 → 44 → 21 against a floor of 20. **One excursion at one physical scale, counted as four independent failures.** C1 sits at one upward rung against 0.78 expected by chance for a 95% pointwise band across 31 rungs — never anomalous.

The low-power exclusion already applied to the share; including all 33 rungs moves C2's worst reading 0.8710 → 0.8788, so low power is not what decides C2.

Row 6 fired at D3a: no R, no `Rscript`, no `rpy2`, no maintained Python port of the reference package, no reachable package index.

### A10b.2 — T1/T2, knee sampling distribution, 500 draws per control

| Control | Injected | Median breakpoint | Bias (rungs) | 95% CI width | Covers injected |
|---|---|---|---|---|---|
| C3 | 10 µs | 3.0518e-5 s | +1.610 | 0.000 | No |
| C3′ | 1 ms | 1.9531e-3 s | +0.966 | 1.000 | No |
| C4 | 60 s | 8 s | −2.907 | 1.000 | No |
| C4′ | 100 ms | 0.25 s | +1.322 | 1.000 | No |

ΔBIC ≤ 2 bracket independently agrees at width 0 on every control.

**Multi-scale compression is systematic, not a single-fit artifact.** Across all 500 draws C4's first breakpoint sits +1.610 rungs above the injected 10 µs and its last −2.907 rungs below the injected 60 s. Intervals do not overlap. Median separation 18.0 rungs against a true 22.5 — the estimator compresses the gap by ~4.5 rungs.

Bias consistency:

| Grouping | Common bias | CI95 | Range | Q p-value |
|---|---|---|---|---|
| All four | +0.863 | [+0.848, +0.878] | 4.517 | 0 |
| Single-scale | +1.371 | [+1.351, +1.391] | 0.644 | 1.33e-202 |
| Multi-scale | +0.248 | [+0.226, +0.270] | 4.229 | 0 |

**Q is hypersensitive here** — the estimator is nearly deterministic, so standard errors approach zero and any difference registers. **The meaningful numbers are the ranges: 0.644 rungs within single-scale, 4.517 once the coarse two-scale transition enters.**

Usability criteria: interval width on C3′ 1.000 against ≤ 3 — **pass**. Injected scale inside interval 0 of 4 against ≥ 3 of 4 — **fail**. Common bias p = 0 against ≥ 0.05 — **fail**. Survival test failed.

Two further code defects found and fixed before these numbers were taken: Cochran's Q dividing by zero (standard errors now floored at the estimator's own quantisation, one rung over √12 over √n), and a breakpoint position rule searching rise→flat when the coarse transition is flat→rise, which had returned a nonsense −20.9 rung bias. After the fix the shape-fixed rule and nearest-to-injected agree exactly on all four controls.

## 1.5 Findings carried in from Phase 10 — still standing

These survive and are what the phase's merge preserved. **They are not invalidated by Phase 10b's failure**, except as D12 qualifies the knee.

| Result | Value |
|---|---|
| Frozen cohort | hash `e1a0ac73a79aa573`, 114 events; analysis cohort 100 (premarket 28, regular-hours 70); row-cap 8 and sidecar 6 carried, labeled, never pooled |
| Detection anchor (D7) | 110/110 exact vs Phase 8 `det_minute`; reference deviation 0.000e+00 |
| Detection-to-peak | median ~1,976 s; poll-grid ratio 1.010 |
| **Negative detection-to-peak share** | **28%** — peak intensity precedes detection |
| **Segment split** | premarket 0% negative vs regular-hours **40%**; decay 6,693 s vs 6.2 s |
| Session elevation | median **78.5×** flanking baseline; 86% exceed 4× |
| Concentration | ~85% of prints in 15–33% of clock time |
| v3 Allan/Fano gate | knee 128 s regular-hours / 16 s premarket, ΔBIC 45.6–68.7 on all four cells — **now qualified by D12** |
| v3 regular-hours curve | A = 5.99 at 15.6 ms, 1,245 at 4,096 s; slope 0.173 below the knee, 1.017 above |
| v4 fragmentation | MRSN 2023-05-03: 7 prints inside 10.7 µs; median sub-burst duration 349 ns |
| Timestamp resolution | median 80.5 ns, min 49 ns, max 8,388 ns |

**The fragmentation-plateau hypothesis (T1) was never tested.** The phase never reached it. It remains open: does the sub-knee Allan plateau height track the **size-weighted** mean sweep size, E[N²]/E[N], per event? Record it as an open item — it is cheap and it is the cleanest available explanation of the plateau at ≈6.

## 1.6 Specification defects — on the record

Ten drafting errors, all mine, all in prompts I authored. Recorded because the pattern is the phase's most transferable lesson.

| # | Defect | Consequence |
|---|---|---|
| 1 | C3's time-rescaling target set ~10.6 rungs below its own sweep floor | Required outcome arithmetically impossible from the original prompt |
| 2 | Crossing specified as band-departure while v3 — the comparison target — used a knee | Would have compared unlike quantities; on real data the departure statistic lands on the fragmentation scale every time |
| 3 | Rationale for the widest-h crossing rule sign-inverted | The most permissive null is the **narrowest** eligible bandwidth, not the widest |
| 4 | Inside-band share treats correlated rungs as independent evidence | One excursion at one scale counted as four failures; this is what sank C2 |
| 5 | The 0.90 inside-band threshold had no justification | Chosen because it looked reasonable |
| 6 | `min_prints_per_block` made eligibility worse than all three alternatives | 0.381 against 0.762 / 0.524 / 0.429 |
| 7 | The rationale for rejecting the alternative was factually wrong | Claimed it would exclude v3's 16 s premarket knee; the replacement excluded 16 s too |
| 8 | A10b.1 made C4's time-rescaling row unsatisfiable by 0.09 of a rung | A repair created a new impossibility |
| 9 | C2's bandwidths restricted but not its rungs | Same argument, one axis missed |
| 10 | Row 6 required validation against a reference package in an offline environment | Blocked a task that was otherwise ready |
| 11 | Row 15 counted amendment rounds rather than measuring method fit | Fired on a condition it was not measuring — the same critique this phase levelled at outcome thresholds |

## 1.7 Prior art checked during Phase 10b

New in this phase:

- **Myllymäki, Mrkvička, Grabarnik, Seijo & Hahn (2017)**, *Global envelope tests for spatial processes*, JRSS-B 79:381–404. The correct treatment for comparing an observed curve against simulated curves across a whole domain with multiplicity handled and no independence assumption. Gives a real p-value plus a graphically readable envelope. Recommended at least 2,500 simulations for a single-curve test at 5%; we ran 200. The basic rank ordering is weak and yields a p-interval; the **extreme rank length** refinement breaks ties and matters most at small simulation counts. **Blocked offline. Never run.**
- **Cross-validated bandwidth selection for kernel intensity estimation** — Rudemo (1982), Bowman (1984), Diggle's and likelihood cross-validation selectors in `spatstat`, and Shimazaki & Shinomoto (2010) for the spike-rate case with an explicit stiffness constant against overfitting. Established the held-out fitting requirement as standard practice rather than a local invention.
- **Gouriéroux, Monfort & Renault (1993)**, *Indirect inference*, J. Appl. Econ. 8:S85–S118. Inference from an "incorrect" criterion, rescued by a simulation step; requires only that the model can be simulated. **The route not taken — see §1.8.**

Carried from Phase 10: Kleinberg (2002); Filimonov & Sornette (2015); Brown, Barbieri, Ventura, Kass & Frank (2002); Allan/Fano factor for point processes; Selinger et al. (2007) and Pasquale et al. (2010); Ko et al. (2012); Zaliapin & Ben-Zion (2013, 2020); the metaorder and market-impact literature (Bouchaud, Farmer, Tóth).

## 1.8 The route not taken — record it, do not pursue it

A sharp biased statistic is a poor estimator but a **good summary statistic.** Indirect inference would recover the timescale by running simulated cluster processes through the identical biased pipeline and matching outputs, so the bias cancels rather than needing correction. Consistency requires the binding function — the map from true parameters to the biased statistic — to be one-to-one, and **the very finding that failed usability criterion 3 supports this: C4 and C4′ having different biases means the statistic is sensitive to separation, which is what makes the map invertible.** A common bias would have made the configuration unidentifiable.

**Cooper's decision is not to pursue it.** Reasons, recorded so the decision is legible later:

- Phase 10b would be the sixth method family attempted on this question
- The chat-side architect proposed continuing three times across this phase and authored eleven specification defects in the process
- **The cost stack is the binding constraint on the scalping thesis and is measurable today.** Only ~33.6% of the excursion sits above the detection price on a median ~$3 stock. No burst timescale changes that number

Record in `docs/Open-Items-Register.md` as available-but-declined, with the reasoning above, so a future decision to revive it starts from the argument rather than rediscovering it.

## 1.9 Lessons

- **Synthetic controls with known answers are the correct gate.** They caught six implementation defects and three specification defects across three runs, before a single real event was read. **Not one of these would have surfaced from an outcome threshold.** This is the phase's most valuable output and it should govern every future measurement phase.
- **Parameter stability is not evidence of correctness.** The knee has a 95% interval of 0–1 rung and is wrong on every control. Sharpness and accuracy are different properties, and this phase is the cleanest demonstration the program has produced.
- **Pre-register the failure mode, not just the threshold.** The usability criteria were written expecting a bad estimator to be **vague**. It was sharp. Criterion 1 passed decisively; the failure was caught by a second criterion, by luck of having written one.
- **A repair can create a new impossibility.** Two of three amendments introduced an unreachable required outcome. **Run a satisfiability audit against the amended criteria set before executing any amendment.** This is the single highest-value process change from the phase.
- **Statistics on correlated quantities need a method that knows they are correlated.** The inside-band share was the wrong tool and a global envelope test is the right one.
- **State the environment's constraints at drafting time.** Offline is a fact about this repo, not a surprise to be rediscovered per phase.

---

# PART 2 — TASKS

### CO-T0 — State and scope

- [ ] **CO-T0a** — Report observed repo state: branch, tip, tags, working tree, which `results/phase_10b/**` artifacts exist with row counts. Assert nothing from Part 1.
- [ ] **CO-T0b** — **No computation in this close-out.** No simulation, no refit, no real event, no pass over `filtered_trades`/`filtered_quotes`. Reading committed artifacts only. Hard stop on any write outside the Output Files table.

### CO-T1 — Verify Part 1 against artifacts

**This runs before the summary is written.** Part 1 is transcription and may be wrong.

- [ ] **CO-T1a** — Check every number in §1.4 and §1.5 against its artifact. Produce a table: figure, value as stated in Part 1, value in the artifact, artifact path, match yes/no.
- [ ] **CO-T1b** — **Report discrepancies; do not silently correct them.** Where an artifact disagrees with Part 1, the artifact wins in the summary and the discrepancy is listed in the verification block.
- [ ] **CO-T1c** — Flag any figure in Part 1 with **no** supporting artifact. Those are quarantined: they may appear in the summary only if labeled as unverified, or they are dropped.
- [ ] CO-T1d — Commit.

### CO-T2 — Write `results/phase_10b/SUMMARY.md`

**The audience is a fresh chat with no context.** The test: could someone who has never seen this phase read only this document and correctly decide what to do next? Write for that reader.

Required sections, in order:

1. **Verdict, first paragraph, no preamble.** Phase 10b closes as a negative result. No burst timescale established. State it plainly and do not soften it.
2. **What the phase was and why it existed** — the ill-posedness of the binary question, the reframing, the two methods, the control gate.
3. **What happened** — three control runs, what each established, where each stopped. Include the defect counts.
4. **The central finding** — the knee is sharp and biased; the mechanism (straight lines fitted to a curve, asymptotes meeting inside the transition); why the bias does not transfer across configurations. This is the most reusable thing the phase produced.
5. **Consequences** — D11, D12, D13 in full, including the 50–1,000 s and 6–120 s ranges on v3's knees and their meaning for downstream anchoring.
6. **What survives from Phase 10** — the §1.5 table, with D12's qualification attached to the v3 row.
7. **Specification defects** — the §1.6 table in full. **Do not soften or aggregate it.** An honest error record is the point.
8. **Prior art** — §1.7, with the offline block on the envelope test stated as a fact about the environment.
9. **The route not taken** — §1.8, including why the binding-function argument is supported by the failed criterion, and Cooper's reasons for declining.
10. **Open items** — the fragmentation-plateau check (never run); the global envelope test (blocked offline); indirect inference (declined, available).
11. **Lessons** — §1.9.
12. **What happens next** — Phase 11, *Spread & impact by participation*, unchanged in the Operating Plan and never displaced. Its participation-bucketed effective-spread half needs no burst timescale and is executable immediately. State that the cost stack is the binding constraint on the scalping thesis.

Rules:

- [ ] **CO-T2a** — Every number carries its n and its artifact path.
- [ ] **CO-T2b** — **No recommendations.** No characterisation of any result as good, promising, weak, or disappointing. Describe.
- [ ] **CO-T2c** — Do not write the phase as a success with caveats. **It is a negative result and the summary's job is to make that unambiguous** while preserving what was learned.
- [ ] **CO-T2d** — Do not reproduce Part 1 verbatim. Part 1 is source material; the summary is a written document.
- [ ] CO-T2e — Commit.

### CO-T3 — Registers

- [ ] **CO-T3a** — Append **D11, D12, D13, D14** to `docs/Universe-Decisions.md`, verbatim from §1.3. Append-only.
- [ ] **CO-T3b** — Append **D14** to `CLAUDE.md` standing constraints.
- [ ] **CO-T3c** — Append to `docs/Open-Items-Register.md`: fragmentation-plateau check (never run, cheap, method stated); global envelope test (blocked offline, draw-count requirement stated); indirect inference (declined with reasons, §1.8 argument preserved).
- [ ] **CO-T3d** — Update `docs/Research-Library-Map.md` with the Phase 10b prompts, configs, artifacts, charts, and the three new prior-art entries.
- [ ] **CO-T3e** — Operating Plan §6: mark row 10b closed, gate outcome *no burst timescale established*. **Rows 11–19 untouched.**
- [ ] CO-T3f — Commit.

### CO-T4 — Close the repo state

- [ ] **CO-T4a** — `results/phase_10b/digest.json`: status → `complete_approved`; headline metric `{"name": "burst_timescale_established", "value": 0, "n": 0, "source": "results/phase_10b/SUMMARY.md"}` with n = 0 because no real event was analysed. `surprises` non-empty — at minimum the sharp-but-biased finding and the eleven specification defects.
- [ ] **CO-T4b** — Post the exact digest diff before writing it.
- [ ] **CO-T4c** — Tag `phase-10b-closed`. **Not `phase-10b-approved`** — the convention marks an approved result and there is no result here. Fast-forward `main`.
- [ ] **CO-T4d** — Cross-phase copy to `results/reports/phase_10b_summary.md`.
- [ ] CO-T4e — Commit. Post.

---

## Escalation Criteria

| # | Condition | Threshold | Action |
|---|---|---|---|
| 0 | Cooper's review of the summary contradicts the record | judgment | Hard stop |
| 1 | Working tree dirty beyond the three entries waived 2026-08-06 | any | Hard stop |
| 2 | Any figure in Part 1 disagrees with its artifact | any | **Not a stop** — report in CO-T1a, artifact wins |
| 3 | More than 5 figures in Part 1 have no supporting artifact | > 5 | Hard stop — the record is not reconstructable, post and wait |
| 4 | Any computation, simulation, or refit | any | Hard stop — this is a close-out |
| 5 | Any read of a real event or pass over `filtered_trades`/`filtered_quotes` | any | Hard stop |
| 6 | Any write outside the Output Files table | any | Hard stop |
| 7 | Any edit to Operating Plan rows 11–19 | any | Hard stop |

---

## Output Files

| File | Description | Status |
|---|---|---|
| `prompts/phase_10b_closeout.md` | This file | [ ] |
| `results/phase_10b/SUMMARY.md` | The phase summary | [ ] |
| `results/phase_10b/artifacts/co_verification.json` | Part 1 figures against artifacts, discrepancies, unsupported figures | [ ] |
| `results/phase_10b/digest.json` | Status, headline metric, surprises | [ ] |
| `results/reports/phase_10b_summary.md` | Cross-phase copy | [ ] |
| `docs/Universe-Decisions.md` | D11–D14 appended | [ ] |
| `docs/Open-Items-Register.md` | Three entries appended | [ ] |
| `docs/Research-Library-Map.md` | Phase 10b entries, three prior-art entries | [ ] |
| `docs/Claude-Code-Operating-Plan.md` | Row 10b marked closed | [ ] |
| `CLAUDE.md` | D14 appended | [ ] |

---

## Reporting

On completion, post: the CO-T1 verification table with every discrepancy and unsupported figure named · the SUMMARY.md section list with word counts · the four decision texts as written to the register · the digest diff · tag and merge confirmation · escalation check, all 8 rows · output file table · commit list.

Description only. No recommendations.

---

## Approval Gate

Do not begin Phase 11 until Cooper has read `results/phase_10b/SUMMARY.md` and given explicit approval. **On approval the next work is Phase 11, *Spread & impact by participation*, whose participation-bucketed effective-spread measurement requires no burst timescale and is the binding constraint on the scalping thesis.**
