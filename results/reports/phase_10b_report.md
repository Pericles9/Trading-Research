# Phase 10b — Randomness of Trade Arrivals Under a Non-Constant Rate

**Status: closed as a negative result, 2026-08-13.**
**No burst timescale is established by this phase, or by the Phase 10 / 10b program that preceded it.**

Phase 10b set out to measure the timescale at which trade arrivals stop being explainable as random. It never measured one. It failed at its own synthetic control gate, three times, and the third failure identified why: the estimator it relied on is sharp but biased, and the bias depends on a quantity that cannot be known on real data. The phase read **zero real events**. Every number below comes from simulated controls or from artifacts carried in from Phase 10.

---

## 1. What the phase was for

Phase 10 tried five method families to find a burst timescale. All five failed identically: each needed a reference level or a resolution — a bandwidth, a window, a threshold — and the answer tracked that choice rather than the market.

The diagnosis was that the question itself was ill-posed. "Bursty" and "Poisson with a time-varying rate" are not distinguishable without constraining how fast the rate may vary. Let the rate wiggle freely and it absorbs every cluster; force it flat and everything looks bursty. Phase 10b reframed it as:

> At what timescale do arrivals stop looking random, given a rate allowed to vary more slowly than that?

Two methods were to answer it and be cross-checked: the **Allan factor** against a *matched* inhomogeneous-Poisson null, and **time-rescaling** under a *held-out* intensity estimate. A ladder of 33 timescales from 2⁻²⁰ to 2¹² s and a bandwidth sweep of 21 rungs from 2⁻⁶ to 2¹⁴ s, both deliberately degenerate at their ends so that an answer landing on a boundary is identifiable as an artifact rather than a result.

The design decision that mattered most: **failure criteria were synthetic controls with known answers, not thresholds on outcomes.** Outcome thresholds had passed in every Phase 10 version while both arms were measuring the wrong object. A threshold on an outcome cannot detect a method that stably measures the wrong thing.

---

## 2. What happened

Three control runs. None reached real data.

**Run 1** failed all four controls. The causes were four defects in the pipeline implementation, each caught by a control whose answer was known in advance: an intensity fitted in-sample, which would have produced tight, confident, wrong bands with nothing flagging them; an integrated intensity snapped to grid nodes, giving a mean rescaled interval of 0.027 instead of 1.0; a grid that could not represent the held-out block structure; and a missing edge correction that halved the intensity estimate at the widest bandwidths. After repair, a homogeneous Poisson process passed the rescaling test at every bandwidth ≥ 64 s with mean rescaled interval 0.995–1.004, and the sparse Allan estimator was verified exactly against a dense reference on 200 cases.

**Run 2** passed the magnitude checks and failed the scale-recovery checks. Band coverage came in at 0.9348–0.9460 against a required [0.90, 0.99]; the injected cluster-size plateau was recovered as 5.9852 against a true 6.0000, an error of −0.25%; two injected scales were separated by a factor of 4.19 × 10⁶. But the crossing statistic located none of the injected timescales, and one required outcome — recovery of a 10 µs scale by time-rescaling — turned out to be arithmetically impossible, its target sitting 10.61 rungs below the sweep's own floor.

**Run 3**, after the first amendment replaced the crossing statistic with a piecewise-linear knee, passed C1 and the magnitude checks and failed the knee on three of four controls. It also fired a new criterion: a block-length rule introduced by that amendment made 13 of 21 bandwidths ineligible, a binding share of 0.6190 against a 0.40 threshold.

A subsequent diagnostic established that the amendment's block rule left **less** of the sweep testable (0.381) than the fixed 60 s block it replaced (0.524), than no rule at all (0.762), or than the alternative it had explicitly rejected (0.429) — and that the rationale for that rejection was itself wrong, since the replacement excluded the same bandwidth the rejected option was faulted for excluding.

Across the three runs the controls caught **six implementation defects and eleven specification defects**. Not one would have surfaced from an outcome threshold.

---

## 3. The central finding: the knee is sharp and it is biased

This is the most reusable thing the phase produced.

The knee — the breakpoint of a piecewise-linear fit to a log-log Allan curve, selected by BIC — was refit independently on 500 simulated realizations of each of four cluster processes with known injected timescales.

| Control | Injected | Median breakpoint | Bias (rungs) | 95% interval width | Injected inside interval |
|---|---|---|---|---|---|
| C3 | 10 µs | 3.0518e−5 s | +1.610 | 0.000 | No |
| C3′ | 1 ms | 1.9531e−3 s | +0.966 | 1.000 | No |
| C4 | 60 s (coarse of two) | 8 s | **−2.907** | 1.000 | No |
| C4′ | 100 ms | 0.25 s | +1.322 | 1.000 | No |

n = 500 draws per control. Source: `results/phase_10b/amendment_2/artifacts/t2_bias_consistency.json`, chart `amendment_2/charts/11_knee_sampling_distribution.html`.

The estimator does not fail by being vague. Its 95% interval spans **0 or 1 rung** on every control, and a ΔBIC ≤ 2 bracket computed independently agrees at width 0 throughout. It fails by being **biased**: it locates a scale sharply, and the scale it locates is not the injected one. The injected value falls inside the interval on **0 of 4** controls.

**The mechanism.** An Allan curve does not turn a corner; it curves smoothly through its transition. Fitting straight lines to it puts the fitted asymptotes' intersection *inside* the transition region rather than at its start. For a single-scale cluster process the plateau is approached from below, so the intersection lands above the injected duration — the +0.97 to +1.61 rung bias. For the coarse component of a two-scale process the curve lifts off an existing plateau, so the intersection lands below — the −2.91 rungs. The direction of the bias is set by which side of the transition the curve arrives from.

**The bias does not transfer.** Single-scale controls cluster: a common bias of +1.371 rungs with a spread across controls of 0.644 rungs. Adding the two-scale coarse transition widens that spread to 4.517 rungs. A homogeneity test rejects a single common bias in every grouping (p = 0), though that test is hypersensitive here — a near-deterministic estimator has standard errors approaching zero, so any difference registers, and the ranges rather than the p-values are the meaningful quantities.

The compression is systematic rather than an artifact of one fit. Across all 500 draws of the two-scale control, the fine breakpoint sits +1.610 rungs above its injected 10 µs and the coarse breakpoint −2.907 rungs below its injected 60 s. The two intervals do not overlap. Median separation is 18.0 rungs against a true separation of 22.5 — the estimator compresses the gap by roughly 4.5 rungs.

**Because the bias depends on the separation between scales, and that separation is exactly what is unknown on real data, the bias cannot be corrected out.** That is what closes the phase.

Two errors in the analysis code were found and fixed before these numbers were taken: a homogeneity test dividing by zero, because a control that selects the same rung in all 500 draws has a measured standard error of exactly zero (standard errors are now floored at the estimator's own quantisation); and a breakpoint position rule searching for a rise→flat transition when the coarse transition is flat→rise, which had produced a nonsense −20.9 rung bias. After the fix, the shape-fixed position rule and the nearest-to-injected statistic agree exactly on all four controls.

---

## 4. Consequences

Three decisions are recorded in `docs/Universe-Decisions.md`.

**D11 — the Allan knee cannot recover a cluster timescale.** Its 95% interval spans 0–1 rung while the injected scale falls inside it on 0 of 4 controls. The bias is a deterministic consequence of fitting straight lines to a smoothly curving function, and it is not a fixed offset — it depends on scale separation, which is unknowable on real data. No burst timescale is established by this program.

**D12 — v3's Allan knee carries a scale-dependent uncertainty.** v3's regular-hours knee at 128 s and premarket knee at 16 s are flat→rise transitions, structurally the same kind that carries the −2.91 rung (factor 7.5, downward) bias on the two-scale control. Applying the single-scale bias instead gives +1.371 rungs (factor 2.6, upward). **The true scale behind 128 s therefore sits somewhere in roughly 50 s to 1,000 s, and behind 16 s in roughly 6 s to 120 s.** These ranges are too wide to anchor a trading horizon. v3's knee remains valid as evidence that a transition *exists*; it is not valid as a measurement of where.

**D13 — D5's premise fails and downstream phases re-anchor.** D5 required a burst timescale to anchor every downstream horizon. None is available at usable precision. Phases 13, 14, 16 and 17 re-anchor to detection time, clock time, or price-path events instead. The specific re-anchoring is scoped when each phase is drafted. This is a first-order program finding, not a sixth failure.

**D14 — the environment is offline.** No package index, no R, no network fetch. Any prompt requiring an external package, a reference implementation, or a downloaded artifact must state an offline fallback at drafting time.

---

## 5. What survives from Phase 10

These are not invalidated by Phase 10b's failure, except as D12 qualifies the knee.

| Result | Value | n |
|---|---|---|
| Frozen cohort | hash `e1a0ac73a79aa573` | 114 events; analysis cohort 100 (premarket 28, regular-hours 70); row-cap 8 and dev sidecar 6 carried, labelled, never pooled |
| Detection anchor (D7) | exact agreement with Phase 8 `det_minute`; reference price deviation 0.000e+00 | 110/110 |
| Detection-to-peak | median ≈ 1,976 s; poll-grid ratio 1.010 | 100 |
| **Negative detection-to-peak share** | **28%** — peak intensity precedes detection | 100 |
| **Segment split** | premarket 0% negative vs regular-hours **40%**; decay 6,693 s vs 6.2 s | 28 / 70 |
| Session elevation | median **78.5×** flanking baseline; 86% exceed 4× | 100 |
| Concentration | ≈85% of prints in 15–33% of clock time | 100 |
| v3 Allan/Fano gate | pooled knee **128 s** regular-hours / **16 s** premarket; ΔBIC 45.6–68.7 across all four cells — **qualified by D12** | 70 / 28 |
| v3 regular-hours curve | A = 5.99 at 15.6 ms, 1,245 at 4,096 s; slope 0.171 below the knee, 1.043 above | 70 |
| v4 fragmentation | MRSN 2023-05-03: 7 prints inside 10.7 µs; median sub-burst duration 349 ns | 100 |
| Timestamp resolution | median 80.5 ns, min 49 ns, max 8,388 ns | 114 |

Sources: `results/phase_10/artifacts/` (`t1_cohort_manifest.parquet`, `v3_t1_gate.json`, `v2_t1_t4_summary.json`, `v4_subbursts.parquet`) and `results/phase_10b/artifacts/t0e_*`. All 109 figures in this summary and its source record were checked against artifacts; see `results/phase_10b/artifacts/co_verification.json`.

One standing comparison remains banned: no statement may compare a real Allan curve to the theoretical flat-rate value A = 1. v3's A = 1,245 at 4,096 s is consistent with the known non-flat rate and is not evidence of clustering.

---

## 6. Specification defects

Eleven drafting errors, all in prompts authored for this phase. The pattern — a specification error surviving into execution and costing a control run — is the phase's most transferable lesson, and the record is kept unaggregated deliberately.

| # | Defect | Consequence |
|---|---|---|
| 1 | A time-rescaling target set ≈10.6 rungs below its own sweep floor | Required outcome arithmetically impossible from the original prompt |
| 2 | Crossing specified as band-departure while v3 — the comparison target — used a knee | Would have compared unlike quantities; on real data the departure statistic lands on the fragmentation scale every time |
| 3 | Rationale for the widest-bandwidth crossing rule sign-inverted | The most permissive null is the *narrowest* eligible bandwidth, not the widest |
| 4 | Inside-band share treats correlated rungs as independent evidence | One excursion at one scale counted as four failures; this is what sank C2 |
| 5 | The 0.90 inside-band threshold had no justification | Chosen because it looked reasonable |
| 6 | A block-print floor made eligibility worse than all three alternatives | 0.381 against 0.762 / 0.524 / 0.429 |
| 7 | The rationale for rejecting one of those alternatives was factually wrong | Claimed it would exclude v3's 16 s premarket knee; the replacement excluded 16 s too |
| 8 | The first amendment made a time-rescaling row unsatisfiable by 0.09 of a rung | A repair created a new impossibility |
| 9 | C2's bandwidths were restricted but not its rungs | Same argument, one axis missed |
| 10 | A criterion required validation against a reference package in an offline environment | Blocked a task that was otherwise ready |
| 11 | An escalation row counted amendment rounds rather than measuring method fit | Fired on a condition it was not measuring — the same critique this phase levelled at outcome thresholds |

The excursion-structure diagnostic behind defect 4 is worth stating concretely: the inhomogeneous-Poisson control's four upward excursions were **contiguous**, at the four highest eligible rungs, whose pooled pair counts fall 181 → 90 → 44 → 21 against a floor of 20. One excursion at one physical scale, counted as four independent failures. The homogeneous control sat at one upward rung against 0.78 expected by chance for a 95% pointwise band across 31 rungs — never anomalous. Source: `results/phase_10b/diagnostic_1/artifacts/d2_excursion_map.json`, chart `diagnostic_1/charts/09_excursion_map.html`.

---

## 7. Prior art

New in this phase:

- **Myllymäki, Mrkvička, Grabarnik, Seijo & Hahn (2017)**, *Global envelope tests for spatial processes*, JRSS-B 79:381–404. The correct treatment for comparing an observed curve against simulated curves across a whole domain, with multiplicity handled and no independence assumption across the domain. Yields a genuine p-value plus a graphically readable envelope. At least 2,500 simulations are recommended for a single-curve test at the 5% level; this phase ran 200. The basic rank ordering is weak and returns a p-interval; the extreme-rank-length refinement breaks ties and matters most at small simulation counts. **This test was never run** — the environment has no R, no `rpy2`, no maintained Python port, and no reachable package index.
- **Cross-validated bandwidth selection for kernel intensity estimation** — Rudemo (1982), Bowman (1984), the likelihood cross-validation selectors in `spatstat`, and Shimazaki & Shinomoto (2010) for the spike-rate case with an explicit stiffness constant against overfitting. These establish held-out intensity fitting as standard practice rather than a local invention.
- **Gouriéroux, Monfort & Renault (1993)**, *Indirect inference*, J. Appl. Econ. 8:S85–S118. Inference from an "incorrect" criterion rescued by a simulation step, requiring only that the model can be simulated.

Carried from Phase 10: Kleinberg (2002); Filimonov & Sornette (2015); Brown, Barbieri, Ventura, Kass & Frank (2002); the Allan and Fano factors for point processes; Selinger et al. (2007) and Pasquale et al. (2010); Ko et al. (2012); Zaliapin & Ben-Zion (2013, 2020); and the metaorder and market-impact literature (Bouchaud, Farmer, Tóth).

---

## 8. The route not taken

A sharp biased statistic is a poor estimator but a good *summary statistic*. Indirect inference would recover the timescale by running simulated cluster processes through the identical biased pipeline and matching outputs, so the bias cancels rather than needing correction. Consistency requires the binding function — the map from true parameters to the biased statistic — to be one-to-one, and the very finding that failed the usability criterion supports this: the two-scale and single-scale controls having *different* biases means the statistic is sensitive to separation, which is what makes the map invertible. A common bias would have made the configuration unidentifiable.

The decision is not to pursue it. Recorded reasons: it would be the sixth method family attempted on this question; the design side proposed continuing three times across this phase and authored eleven specification defects in the process; and the cost stack, not the burst timescale, is the binding constraint on the scalping thesis and is measurable today — only ≈33.6% of the excursion sits above the detection price on a median ≈$3 stock, and no burst timescale changes that number.

The argument is preserved in `docs/Open-Items-Register.md` so that any future decision to revive it starts from the argument rather than rediscovering it.

---

## 9. Open items

- **The fragmentation-plateau check was never run.** The phase stopped before reaching it. The hypothesis: the sub-knee Allan plateau height, ≈6 on the controls, is execution fragmentation, and per event its height should track the *size-weighted* mean sweep size E[N²]/E[N] rather than the plain mean E[N]. It is cheap and it is the cleanest available explanation of the plateau.
- **The global envelope test is blocked offline.** It requires ≥ 2,499 simulations and an extreme-rank-length ordering, and needs either a reference implementation to validate against or an offline validation route agreed at drafting time.
- **Indirect inference is available and declined**, with the reasoning in §8.

---

## 10. Lessons

- **Synthetic controls with known answers are the correct gate.** They caught six implementation defects and eleven specification defects across three runs, before a single real event was read. Not one would have surfaced from an outcome threshold. This should govern every future measurement phase.
- **Parameter stability is not evidence of correctness.** The knee has a 95% interval of 0–1 rung and is wrong on every control. Sharpness and accuracy are different properties.
- **Pre-register the failure mode, not just the threshold.** The usability criteria were written expecting a bad estimator to be vague. It was sharp: the width criterion passed decisively, and the failure was caught only by a second criterion that happened to have been written.
- **A repair can create a new impossibility.** Two of three amendments introduced an unreachable required outcome. Run a satisfiability audit against the amended criteria set before executing any amendment. This is the single highest-value process change from the phase.
- **Statistics on correlated quantities need a method that knows they are correlated.** The inside-band share was the wrong tool.
- **State the environment's constraints at drafting time.**

---

## 11. What happens next

**Phase 11 — Spread & impact by participation.** It is unchanged in the Operating Plan and was never displaced by Phase 10 or 10b. Its participation-bucketed effective-spread measurement requires no burst timescale and is executable immediately.

The cost stack is the binding constraint on the scalping thesis. Phase 11 measures it.
