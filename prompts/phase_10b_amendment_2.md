# Phase 10b — Amendment 2 (A10b.2): Diagnostic Resumption and Four Repairs

**Date:** 2026-08-13
**Follows:** DX10b.1 hard stop on row 6 (envelope test reference unavailable offline). D1 and D2 complete; D3–D5 not run.
**Row 15 override: granted by Cooper, 2026-08-13.** Row 15 fired on amendment count, but D1 established that the failures being counted were specification defects in my drafting, not method failures. The override is recorded here with its reason so it is not read later as a rule quietly abandoned.

**Supersedes:** A10b.1's `min_prints_per_block` rule and C2 bandwidth restriction; DX10b.1's D3a validation route. Everything else in `prompts/phase_10b.md` and `prompts/phase_10b_amendment_1.md` stands.

---

## The four defects being repaired, all mine

D1 and D2 established these. Recording them plainly because the pattern — specification error surviving into execution and costing a control run — is now four for four.

1. **`min_prints_per_block` made eligibility worse than every alternative.** Pure h/4 gives 0.762 of the sweep; the original fixed 60 s block 0.524; the alternative I rejected 0.429; **my rule 0.381.** Worst of four.
2. **My rationale for rejecting that alternative was factually wrong.** I wrote that declaring h < 60 s ineligible "would exclude v3's premarket knee of 16 s by construction." My replacement excludes 16 s as well — the floor binds below h = 69.8 s. I rejected an option for a defect my own rule shared.
3. **C3's time-rescaling target was never reachable.** 10 µs sits 10.61 rungs below the sweep floor of 2^-6 s. Void in the original prompt, void after amendment.
4. **A10b.1 made C4's time-rescaling row unsatisfiable by 0.09 of a rung.** 60 s is inside the sweep; the nearest eligible bandwidth became 128 s, 1.09 rungs away against a 1-rung tolerance.

And one specification inconsistency, from D2:

5. **A10b.1 restricted C2's bandwidths to h ≤ 1404 s but did not restrict its rungs.** D2 shows C2's four upward excursions are contiguous at T = 128–1024 s, against an injected rate timescale of 1404 s. One excursion at one physical scale, counted as four independent failures. **This repair is derived from seeing which rungs failed, so it is not adopted on reasoning alone — see A2-T6.**

---

## Task order, and why

**A2-T1 and A2-T2 run first and may end the phase.** They are the resumed D4 and D5: the knee's sampling distribution and whether its bias is one bias. If the knee cannot locate a scale, repairs 1–4 are moot and Phase 10b reports a method limitation. **Do not run A2-T3 onward until the A2-T2 decision point is posted and Cooper has responded.**

---

## Tasks

### A2-T0 — State, config, standing constraint

- [ ] **A2-T0a** — Report observed repo state. Assert nothing from this document. Confirm the three pre-existing dirty entries waived on 2026-08-06 are still the only ones.
- [ ] **A2-T0b** — Regenerate the six control per-draw realizations from seed 42. **Verify against the stored summaries before use** — all six print counts must reproduce exactly, as D0b confirmed. Hard stop on any mismatch.
- [ ] **A2-T0c** — Append to `CLAUDE.md` standing constraints:

  > **Environment is offline.** No package index, no R, no network fetch. Any prompt requiring an external package, a reference implementation, or a downloaded artifact must state an offline fallback at drafting time. `reuse-before-build` applies only to what is already installed.

  This is why row 6 fired. It is an environment fact that should not surface again as a per-phase surprise.
- [ ] **A2-T0d** — Commit this prompt and `config/phase_10b_amendment_2.json` before any computation.

### A2-T1 — Knee sampling distribution (resumed D4, unchanged)

Runs on the regenerated draws. Uses no envelope test.

- [ ] **A2-T1a** — For C3, C4, C3′, C4′, refit the knee independently on every draw. Report the **full distribution** of the estimated breakpoint: median, 2.5/97.5 percentiles, histogram.
- [ ] **A2-T1b** — Report **bias and spread separately**, in rungs. The current single-number rung error conflates them.
- [ ] **A2-T1c** — Coverage: does the injected scale fall inside the 95% interval, per control.
- [ ] **A2-T1d** — Also compute the ΔBIC ≤ 2 bracket and report alongside. **Where they differ, trust the bootstrap** — breakpoint estimation is non-regular and the chi-square-style calibration behind an analytic bracket does not hold here.
- [ ] **A2-T1e** — C4 and C4′ carry two transitions. Report each breakpoint's interval separately and whether they overlap. C4's fitted pair missed in **opposite** directions (6.10e-5 against 1e-5; 8 s against 60 s). **Report whether that compression is systematic across draws or a single-fit artifact.**
- [ ] A2-T1f — Chart 11. Commit.

### A2-T2 — Bias consistency and the decision point (resumed D5)

- [ ] **A2-T2a** — Test whether the four per-control biases are consistent with a **single common value**. Report the common-bias estimate, its interval, and the test's p-value.
- [ ] **A2-T2b** — Same, split single-scale (C3, C3′) versus multi-scale (C4, C4′).
- [ ] **A2-T2c — Pre-registered usability criteria.** Fixed here, before results are seen:

| Criterion | Threshold | Meaning if failed |
|---|---|---|
| 95% interval width on C3′ | ≤ 3 rungs (factor 8) | The knee cannot locate a scale at all |
| Injected scale inside 95% interval | ≥ 3 of 4 controls | The knee is biased in a way its own spread does not cover |
| Common bias across all four | p ≥ 0.05 | A calibration fitted on single-scale controls cannot transfer to the multi-scale real cohort |

  **The first two are the phase's survival test.** Failing either means the knee is unusable and Phase 10b reports a method limitation. Failing only the third means the knee is usable as an interval but must not be bias-corrected.
- [ ] **A2-T2d — Hard stop and post, whatever the outcome.** Do not proceed to A2-T3. Post charts 11 and 12 plus the criteria table and wait.
- [ ] A2-T2e — Chart 12. Commit.

> **If the knee fails A2-T2c rows 1 or 2:** the phase's likely disposition is that the Allan knee cannot locate a cluster timescale, which **also places a factor-of-3 uncertainty on v3's 128 s / 16 s knee** — currently the strongest surviving result in the program. That consequence gets recorded explicitly in the report, not absorbed. Cooper decides.

---

**Everything below runs only on Cooper's instruction after the A2-T2 decision point.**

---

### A2-T3 — Repair 1: drop the block-print floor

- [ ] **A2-T3a** — Remove `min_prints_per_block` from the held-out block rule. Block length becomes **h / 4, with no floor.** Eligible share returns to 0.762 and h = 60 s returns to the eligible set.
- [ ] **A2-T3b** — The floor existed because λ̂ was expected to be noisy on thin blocks. **That is an empirical question and C1 answers it.** Rerun C1 with no floor; required outcome is unchanged — no interior time-rescaling crossing. If C1 still passes, the floor was never earning its cost.
- [ ] **A2-T3c** — Report the eligible-bandwidth set under all four block rules (none, original 60 s, the rejected alternative, A10b.1's) against C1's pass/fail under each. **This is the evidence that decides whether the floor returns in any form.**
- [ ] **A2-T3d** — If C1 fails without the floor, **stop and post.** Do not reintroduce a floor by choosing a value — that is the tuning the gate forbids.
- [ ] A2-T3e — Chart 13. Commit.

### A2-T4 — Repair 2: strike the unreachable requirement

- [ ] **A2-T4a** — Mark C3's time-rescaling required outcome **void — target 10.61 rungs below the sweep floor.** It is struck, not relaxed, not moved. C3's knee requirement and plateau requirement stand unchanged.
- [ ] **A2-T4b** — Do **not** extend the bandwidth sweep downward to reach 10 µs. The sweep floor of 2^-6 s was set because narrower bandwidths are degenerate for held-out intensity fitting. Reaching a target by extending a range into a region known to be meaningless is the failure this phase exists to avoid.
- [ ] **A2-T4c** — Record in the report that **the time-rescaling method has no validated recovery of a microsecond-scale cluster** and cannot be read as evidence about the fragmentation scale. Its validation rests on C4 and C4′ only.
- [ ] **A2-T4d** — Run the D1 satisfiability audit against the **amended** criteria set. Every required outcome, target, achievable range, reachable yes/no. **Hard stop on any remaining unreachable row.**
- [ ] A2-T4e — Table only. Commit.

### A2-T5 — Repair 3: offline validation of the envelope test

Replaces DX10b.1 D3a. The reference-implementation route is void — this environment has no R, no package index, no port.

Three checks together are stronger than a single-example software match, which would only prove the same arithmetic was coded, not that it is calibrated.

- [ ] **A2-T5a — Single-rung reduction.** With the domain restricted to one rung, the global test must collapse **exactly** to the ordinary Monte Carlo rank p-value, (1 + number of simulations at least as extreme) / (1 + number of simulations). Exact identity. Report the comparison over 200 cases; any discrepancy is a hard stop.
- [ ] **A2-T5b — P-value uniformity under the null.** Treat each simulated curve in turn as the observed one. Under exchangeability the resulting p-values must be **uniform across the whole range**, not merely 5% below 0.05. Report the distribution and a uniformity test. This catches ordering bugs that preserve the tail while distorting the middle — the failure a type I error check alone would miss.
- [ ] **A2-T5c — Type I error.** C1 is a true null. Across 200 independent C1 datasets, report the rejection fraction at 5%. Required: within [0.02, 0.10].
- [ ] **A2-T5d** — All three must pass before the test is run on any control. **Hard stop otherwise, and post — do not proceed with a partially validated implementation.**
- [ ] **A2-T5e — Then run it.** Extreme-rank-length ordering, 2,499 draws, intensity re-estimated per simulation. Report per control per bandwidth: p-value or p-interval, envelope, and the rungs where the observed curve exits.
- [ ] **A2-T5f** — Table every control's verdict under the inside-band share rule against the envelope test, naming the driving rungs wherever they disagree.
- [ ] A2-T5g — Chart 10. Commit.

### A2-T6 — Repair 4: C2 rung restriction, and the prediction that earns it

**This repair is derived from seeing which rungs failed.** On reasoning alone it is indistinguishable from motivated reasoning, and it is not adopted on reasoning alone. It is adopted only if it makes a prediction that could fail and does not.

- [ ] **A2-T6a — The prediction, pre-registered before the run.** A10b.1 restricted C2's bandwidths to h ≤ the injected rate's own smoothing timescale, on the grounds that a null built from a wider λ̂ is misspecified by construction. The same argument applies to **rungs**: Allan's differencing removes rate variation slower than T, so as T approaches the injected timescale the differencing stops removing it and any mismatch surfaces as an upward excursion.

  **If that is the mechanism, the excursion band's position must move with the injected timescale.**

  Build **C2′ identically to C2 but with the injected rate timescale at 351 s** (config; a factor of 4 below C2's 1404 s, so 2 rungs).

  | | Prediction | Falsification |
  |---|---|---|
  | C2′ excursion band | Centre moves **down ~2 rungs** from C2's 128–1024 s | Band stays at 128–1024 s, or moves in the wrong direction, or does not move |

- [ ] **A2-T6b** — Run C2′. Report its excursion rungs against C2's, and the observed shift in rungs.
- [ ] **A2-T6c — If the prediction fails, the repair is void and C2's failure is real.** Report it as a genuine control failure and stop. Do not attempt a third explanation for C2.
- [ ] **A2-T6d — If the prediction holds,** apply the rung restriction to C2 and C2′ symmetrically with the bandwidth restriction already in force: rungs above the injected timescale are outside the range where the null is correctly specified, and are reported separately rather than counted as failures. **Apply it to no other control** — C1's null is correctly specified at every rung, and C3/C4 are required to be outside the band.
- [ ] **A2-T6e** — State explicitly whether this restriction has any counterpart on real data. It does not: on a real event there is no known injected timescale, so **no rung may be excluded on this basis outside the controls.** Record it as a control-only rule.
- [ ] A2-T6f — Chart 14. Commit.

### A2-T7 — Full control rerun under amended criteria

- [ ] **A2-T7a** — All seven controls (C1, C2, C2′, C3, C4, C3′, C4′) end to end through the shared pipeline. No separate control implementation.
- [ ] **A2-T7b** — Re-assert the standing passes: C3 plateau within ±25% of the size-weighted mean cluster size; C4 scale separation ≥ 1024; band coverage in [0.90, 0.99]. **Material movement in any is a hard stop.**
- [ ] **A2-T7c** — Post the full amended required-outcome table with the D1-style reachability column beside every row.
- [ ] A2-T7d — Chart 04 rebuilt, 2×4. Commit.

### A2-T8 — Report

- [ ] **A2-T8a** — `results/phase_10b/amendment_2/REPORT.md`. Every claim cites its chart, every statistic its n. No recommendations.
- [ ] **A2-T8b** — Disposition table: each of the five defects, and whether it is now closed, closed with a recorded limitation, or still open.
- [ ] **A2-T8c** — Digest. Commit. Post.

---

## Escalation Criteria

Original rows 0–14 and A10b.1 rows 4a–4d stand. **Row 15 is overridden for this amendment only** and returns to force afterwards.

| # | Condition | Threshold | Action |
|---|---|---|---|
| 0 | Cooper's review contradicts the numeric result | judgment | Hard stop |
| 1 | Working tree dirty beyond the three waived entries | any | Hard stop |
| 2 | Seed-42 regeneration does not reproduce stored summaries exactly | any | Hard stop — A2-T1 unrunnable |
| 3 | Any read of a real event, or any pass over `filtered_trades`/`filtered_quotes` | any | Hard stop |
| 4 | **A2-T2 decision point reached** | always | **Hard stop by design — post and wait** |
| 5 | Knee interval width on C3′ exceeds 3 rungs, or coverage below 3 of 4 | either | Hard stop — phase disposition decision, Cooper only |
| 6 | C1 fails without the block floor (A2-T3b) | any | Hard stop — **do not choose a floor value** |
| 7 | Any required outcome still unreachable after A2-T4d | any | Hard stop |
| 8 | Any envelope validation check fails (A2-T5a–c) | any | Hard stop — do not run the test on controls |
| 9 | C2′ prediction fails (A2-T6c) | any | Hard stop — repair void, C2 failure real, no third explanation |
| 10 | Any standing pass moves materially on rerun (A2-T7b) | any | Hard stop |
| 11 | Any write outside `prompts/`, `config/`, `research/`, `results/phase_10b/amendment_2/`, and the single `CLAUDE.md` append | any | Hard stop |
| 12 | A third amendment appears necessary | any | **Post and wait.** Row 15 returns to force; do not write it |

---

## Chart Contract

`results/phase_10b/amendment_2/charts/NN_name.html`.

| # | Filename | Question | Encoding | n annotation | Failure appearance |
|---|---|---|---|---|---|
| 10 | `10_global_envelope.html` | Does any control fail once multiplicity is handled? | x = rung (log s); observed curve; global envelope ribbon; pointwise band dashed for contrast; facet = control × bandwidth; p-value annotated per panel | draws; eligible rungs | Global envelope barely wider than pointwise → multiplicity was not the issue |
| 11 | `11_knee_sampling_distribution.html` | How far does the knee move between draws? | histogram of breakpoint per control; injected scale as vertical rule; 95% interval shaded; ΔBIC bracket overlaid as separate span | draws per control | Interval spanning several rungs → the knee cannot locate a scale, and its bias is beside the point |
| 12 | `12_bias_consistency.html` | One bias or several? | bias in rungs with interval, one row per control, single-scale and multi-scale grouped; common-bias band | draws per control | Non-overlapping intervals → no common bias, calibration cannot transfer |
| 13 | `13_block_rule_sensitivity.html` | Did the block floor ever earn its cost? | x = bandwidth (log s); eligible/ineligible under each of four block rules as stacked rows; C1 pass/fail marked per rule | bandwidths per rule | C1 fails without the floor → the floor was load-bearing after all |
| 14 | `14_c2prime_prediction.html` | Does the excursion band track the injected timescale? | x = rung (log s); C2 and C2′ excursion bands as spans; injected timescales as vertical rules; predicted C2′ position marked before observed | rungs per control | C2′ band coincident with C2's → mechanism wrong, C2 failure real |
| 04 | `04_control_harness.html` | *(rebuilt, 2×4)* | As A10b.1, plus C2′ | draws per control | As A10b.1 |

---

## Config

`config/phase_10b_amendment_2.json`. No value in the original config or A10b.1 is modified except as listed.

| Key | Value | Used by |
|---|---|---|
| `min_prints_per_block` | **removed** (was 20) | A2-T3 |
| `block_ratio` | 4 (unchanged, now floorless) | A2-T3 |
| `c3_t4_requirement` | `"void_unreachable"` | A2-T4 |
| `c2_prime_lambda_timescale_s` | 351 | A2-T6 |
| `c2_rung_restriction` | `"controls_only"` | A2-T6 |
| `knee_interval_max_rungs` | 3 | A2-T2c |
| `knee_coverage_min` | 3 of 4 | A2-T2c |
| `n_envelope_draws` | 2499 | A2-T5 |
| `envelope_ordering` | `"extreme_rank_length"` | A2-T5 |
| `intensity_reestimation` | `"per_simulation"` | A2-T5 |

---

## Output Files

| File | Description | Status |
|---|---|---|
| `prompts/phase_10b_amendment_2.md` | This file | [ ] |
| `config/phase_10b_amendment_2.json` | Per above | [ ] |
| `CLAUDE.md` | Offline constraint appended | [ ] |
| `results/phase_10b/amendment_2/artifacts/t1_knee_distributions.parquet` | Per-draw breakpoints, all controls | [ ] |
| `results/phase_10b/amendment_2/artifacts/t2_bias_consistency.json` | Common-bias estimate, interval, p-value, usability criteria | [ ] |
| `results/phase_10b/amendment_2/artifacts/t3_block_rule_sensitivity.json` | Four rules, eligible sets, C1 outcome under each | [ ] |
| `results/phase_10b/amendment_2/artifacts/t4_satisfiability_audit.json` | Amended criteria, reachability | [ ] |
| `results/phase_10b/amendment_2/artifacts/t5_envelope_validation.json` | Three offline checks | [ ] |
| `results/phase_10b/amendment_2/artifacts/t5_envelope_results.json` | p-values, verdict comparison | [ ] |
| `results/phase_10b/amendment_2/artifacts/t6_c2prime.json` | Predicted and observed excursion bands | [ ] |
| `results/phase_10b/amendment_2/artifacts/t7_controls.json` | All seven, amended outcomes | [ ] |
| `results/phase_10b/amendment_2/charts/04, 10–14*.html` | Per contract | [ ] |
| `results/phase_10b/amendment_2/{REPORT.md, digest.json}` | Per standard | [ ] |

---

## Reporting

**At the A2-T2 decision point, post:** knee distribution table (bias and spread separate, per control); coverage; bootstrap interval against ΔBIC bracket; multi-scale overlap and whether C4's compression is systematic; bias-consistency estimate with p-value, split single- versus multi-scale; the three usability criteria with observed values. Then stop.

**On completion, post additionally:** block-rule sensitivity with C1's outcome under each of four rules; amended satisfiability audit; envelope validation triad; verdict comparison under both rules with driving rungs named; C2′ predicted versus observed shift; full amended required-outcome table with reachability column; standing-pass re-assertion; escalation check, all 13 rows; verification block for every number, including explicit confirmation no real event was read; output table; commit list.

Description only. No recommendations. No characterisation of any result as good, promising, weak, or disappointing.

---

## Approval Gate

**A2-T2 is a mandatory stop.** Post and wait regardless of outcome.

On a full pass through A2-T7, Phase 10b resumes at T3 with: the knee reported as an interval, the floorless block rule, C3's time-rescaling row struck as void, and the C2 rung restriction as a control-only rule. **No real event is read until Cooper approves that resumption.**

Row 15 returns to force on completion of this amendment. **A third amendment is a hard stop, not a document to be written.**
