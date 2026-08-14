# Phase 10b — Diagnostic 1 (DX10b.1): Gate Satisfiability, Excursion Structure, and a Test with a P-Value

**Date:** 2026-08-13
**Follows:** A10b.1 T2-R5 hard stop (escalation rows 4 and 4d fired; row 15 condition live).
**Status: this is NOT an amendment.** It changes no method, adopts no criterion, and reads no real event. It measures the statistical properties of the gate we already built and reports what it finds. **Cooper decides afterwards whether anything here becomes a gate criterion.** That decision, if it happens, is Amendment 2 and needs an explicit row 15 override.

**Why this exists.** Three of the four A10b.1 failures were arithmetic defects in my own specification — a required outcome roughly ten rungs outside its own sweep, a block-length rule that removed the bandwidth where the answer had to land, and an eligibility rule that made 62% of the sweep untestable. The fourth is real but small. Meanwhile every criterion in this phase is a threshold on a point estimate with **no sampling distribution anywhere** — no p-value, no interval, no statement of what the numbers would do by chance. That is the actual gap, and it is what makes it hard to tell a drafting error from a method failure.

---

## Scope boundary — read before starting

| Permitted | Forbidden |
|---|---|
| Reading existing `results/phase_10b/artifacts/*` | Reading any real event, any `filtered_trades`/`filtered_quotes` row |
| Re-simulating the six synthetic controls at higher draw counts | Changing any injected scale, cluster size, or background rate |
| Computing new statistics on control output | Changing any gate threshold, eligibility rule, or required outcome |
| Refitting the knee on existing and new draws | Changing the knee model form, the ladder, or the bandwidth sweep |
| Writing to `results/phase_10b/diagnostic_1/` | Writing to `results/phase_10b/artifacts/`, `charts/01–08`, or any `t2*` file |

**Hard stop if any task would alter a criterion rather than measure one.** The distinction is the whole point of the document.

---

## Context: what is statistically wrong with the gate as built

### 1. Every rung is being counted as if it were independent evidence

The inside-band share counts how many of 31 ladder rungs fall inside a simulated band. **Allan factor values at neighbouring rungs are computed from nested windows and are therefore strongly correlated** — a single real excursion spanning one physical scale shows up as three or four consecutive rungs outside. The share statistic treats those as four independent failures. Nothing in the phase corrects for this, and the ≥ 0.90 threshold was chosen by me with no justification beyond looking reasonable.

### 2. The band has a false-positive rate nobody accounted for

A 95% pointwise band across 31 rungs puts roughly **1.6 rungs outside by chance, about 0.8 of them above.** C1's worst observed upward share was 0.032 — that is **one rung**, against an expectation of 0.8. C1's upward behaviour was never anomalous. It was the nominal error rate of a pointwise band, and the gate had no way to say so.

C2's 0.129 is four rungs against the same 0.8 expectation. That looks like a real excess — **unless the four are adjacent**, in which case it is one excursion at one scale, and correlated rungs make four adjacent hits far more likely than the independent arithmetic suggests. **Diagnostic A settles this, and it is why it runs.**

### 3. There is prior art for exactly this, and it is well established

Comparing an observed curve against a family of simulated curves across a whole domain, with the multiplicity handled correctly, is the **global envelope test** (Myllymäki, Mrkvička, Grabarnik, Seijo & Hahn, *Global envelope tests for spatial processes*, JRSS-B 79:381–404, 2017). It is the standard tool in spatial point-process analysis, where the identical problem arises comparing an empirical curve to simulations across a range of distances.

What it gives us that the current band does not:

- A genuine p-value, plus critical bounds with a graphical reading: if the observed curve is not completely inside the 95% global envelope the null is rejected at 5%, and the places where it falls outside show why.
- Correct **global** type I error across the whole ladder — the multiplicity problem in §1 and §2 is what the method was built to solve.
- No independence assumption across rungs. The ordering is rank-based.

Two implementation facts that constrain us:

- Myllymäki et al. recommend at least 2,500 simulations for a single-function test at the 5% level. **We ran 200.** At 200 draws the test is underpowered and its p-value comes back as an interval rather than a number.
- The basic rank ordering is weak and produces ties, giving an interval of p-values whose endpoints are the most liberal and most conservative readings; a narrow interval is desirable and the test is inconclusive if the interval spans the significance level. The **extreme rank length** refinement breaks those ties, and refinements matter most exactly when the number of simulated curves is small.

One more point from the same source that bears directly on a bug the agent already caught: where the test function depends on an estimated intensity, one may either reuse the observed pattern's intensity estimate for every simulated curve, or re-estimate the intensity separately for each simulation. Re-estimating per simulation is the honest choice and matches the fix already applied — the in-sample band fitting defect found on the first control run was this exact error.

### 4. The knee has a bias but no measured variance

Rung errors of +0.97, +1.32, +1.61, +2.91 are all positive and reasonably tight. We do not know their standard error, so we cannot say whether they are four draws from one bias or genuinely different biases. **That distinction decides whether calibrating the knee is legitimate.** Breakpoint estimation is a non-regular problem — the likelihood is not smooth in the breakpoint position — so analytic standard errors are unreliable here and the answer has to come from resampling.

---

## Tasks

### D0 — State and scope

- [ ] **D0a** — Report observed repo state: branch, tip, working tree clean, which `results/phase_10b/artifacts/*` files exist with row counts, whether per-draw control realizations were persisted or only their summaries. **Assert nothing from this document.**
- [ ] **D0b** — **Hard stop if per-draw realizations were not persisted** and cannot be regenerated deterministically from the committed seed. D4 needs them; if the seed reproduces them exactly, regenerate and verify against the stored summaries before proceeding.
- [ ] **D0c** — Create `results/phase_10b/diagnostic_1/` with `charts/` and `artifacts/`. Commit this prompt and any config additions first.

### D1 — Satisfiability audit of every gate criterion

**This runs before any statistics.** It is pure arithmetic and it is the task that would have caught three of the four A10b.1 failures before they cost a run.

- [ ] **D1a** — For every required outcome in the original prompt and in A10b.1, mechanically check whether it is **reachable at all** given the ladder, the sweep bounds, and the eligibility rules in force. For each, report: the target value, the range the statistic can actually take, and reachable yes/no.
- [ ] **D1b** — Known cases to confirm rather than discover:
  - C3's time-rescaling target of 10 µs sits **~10.6 rungs below the sweep floor of 2^-6 s**. Never satisfiable at any bandwidth, in the original prompt or after amendment.
  - C4's target of 60 s is inside the sweep but was **removed from the eligible set** by A10b.1's block rule. Satisfiable before the amendment, not after.
- [ ] **D1c** — Report the interaction matrix: for each eligibility rule (pooled pair count, floored held-out time, block floor binding), which required outcomes it can render unreachable. **A rule that can void a required outcome is a defect regardless of whether it currently does.**
- [ ] **D1d** — Compute, for the cohort's median event rate of ~1.14 prints per second, the eligible bandwidth set under (i) the original fixed 60 s block, (ii) A10b.1's h/4 rule, and (iii) no block-length rule at all. Report the eligible share for each. **State plainly whether A10b.1's rule was worse than the alternative it rejected.**
- [ ] D1e — Table only, no chart. Commit.

### D2 — Diagnostic A: where the excursions sit

Read-only on existing artifacts. No simulation.

- [ ] **D2a** — For C1 and C2, at every eligible bandwidth, list the **rung index** of every out-of-band excursion, tagged above or below.
- [ ] **D2b** — Report whether excursions are **adjacent or scattered.** Give the longest consecutive run of out-of-band rungs, and the count of distinct runs. Four adjacent rungs is one excursion at one physical scale; four scattered rungs is four.
- [ ] **D2c** — Cross-reference against the `min_pairs_pooled < 20` low-power exclusion. **The original prompt never said whether that exclusion applies to the inside-band share, only to crossing determination.** Report the inside-band share both ways — with and without the low-power rungs. If C2's excursions sit in the excluded zone, its failure resolves under a rule that already exists.
- [ ] **D2d** — Report the empirical false-positive arithmetic alongside: expected rungs outside and above for a 95% pointwise band at the eligible rung count, against observed.
- [ ] D2e — Chart 09. Commit.

### D3 — Global envelope test on the control curves

The substantive statistical addition. **Computed and reported; not adopted.**

- [ ] **D3a — Reuse before building.** Check for a maintained implementation before writing one. The reference implementation is the R package `GET` (Myllymäki & Mrkvička). Report what exists in Python, whether calling the R package is practical in this environment, and what you propose. **If implementing directly, validate the implementation against `GET` on a published example before running it on our controls, and report that comparison.** The extreme-rank-length ordering is short to implement and easy to get subtly wrong.
- [ ] **D3b — Draw count.** Re-simulate all six controls at `n_envelope_draws` = 2,499 (config), per the published recommendation. Report wall time. **If 2,499 is impractical, report the largest achievable count and the resulting p-interval width — do not silently run fewer.**
- [ ] **D3c — Per-simulation intensity re-estimation.** For C2 and any control whose test function depends on an estimated rate, re-estimate the intensity separately for each simulated realization rather than reusing the observed estimate. Confirm this matches the fix already applied for the in-sample band defect, and state the check performed.
- [ ] **D3d — Run the test.** Extreme-rank-length ordering. For each control at each eligible bandwidth report: the p-value or p-interval, the global envelope, and the rungs where the observed curve leaves it.
- [ ] **D3e — The comparison that matters.** Table every control's verdict under the current inside-band share rule against its verdict under the global envelope test. **Where they disagree, say which rung or rungs drive the disagreement.** Specific question to answer explicitly: does C2 still fail once multiplicity is handled correctly?
- [ ] **D3f — Type I error check.** C1 is a true null. Across `n_type1_replicates` = 200 independent C1 datasets (config), report the fraction rejected at the 5% level. **This should come out near 0.05. If it does not, the test is misimplemented and nothing else in D3 is readable.**
- [ ] D3g — Chart 10. Commit.

### D4 — Diagnostic B: the knee's sampling distribution

- [ ] **D4a** — For each of C3, C4, C3′, C4′, refit the knee independently on every simulated draw. Report the **full distribution of the estimated breakpoint**, not a summary: median, 2.5/97.5 percentiles, and the histogram.
- [ ] **D4b** — Report bias (median estimate minus injected scale, in rungs) and spread (interpercentile width, in rungs) **separately**. The current single-number rung error conflates them.
- [ ] **D4c — Coverage.** Report whether the injected scale falls inside the 95% interval, per control. This is the interval-based version of the current ±1 rung requirement and it is the number Cooper needs to judge whether the knee is usable.
- [ ] **D4d — Profile bracket, for comparison.** Also compute the ΔBIC ≤ 2 breakpoint set from the fitted curves and report it alongside the bootstrap interval. **Where they differ, trust the bootstrap** — breakpoint estimation is non-regular and the chi-square-style calibration behind an analytic bracket does not hold. Reporting both shows by how much.
- [ ] **D4e — Multi-scale behaviour.** C4 and C4′ carry two transitions. Report each breakpoint's interval separately and whether the two intervals overlap. C4's fitted breakpoints missed in opposite directions — 6.10e-5 against an injected 1e-5, and 8 s against an injected 60 s. **Report whether that compression is systematic across draws or a single-fit artifact.** It decides whether a calibration fitted on single-scale controls could ever transfer to the real cohort, which is multi-scale by construction.
- [ ] D4f — Chart 11. Commit.

### D5 — Is the bias one bias?

- [ ] **D5a** — Using the D4 distributions, test whether the per-control biases are consistent with a **single common value**. Report the common-bias estimate with its interval, and the test's p-value.
- [ ] **D5b** — Report the same restricted to single-scale controls (C3, C3′) versus multi-scale (C4, C4′). **The pre-registered reading, fixed here before the result is seen:** a common bias across all four supports calibration; a common bias within single-scale controls that fails to extend to multi-scale controls means a calibration fitted on C3/C3′ must not be applied to the real cohort.
- [ ] **D5c** — No adoption. Report the finding; the decision is Cooper's.
- [ ] D5d — Chart 12. Commit.

### D6 — Report

- [ ] **D6a** — `results/phase_10b/diagnostic_1/REPORT.md`. Every claim cites its chart. Every statistic carries its n. **No recommendations.** Present the decision menu in D6b as options with their evidence, not as advice.
- [ ] **D6b** — Close with a table: each of the four A10b.1 failures, and whether this diagnostic shows it to be a specification defect, a genuine method limitation, or still unresolved.
- [ ] **D6c** — Digest to `results/phase_10b/diagnostic_1/digest.json`. Commit. Post.

---

## Escalation Criteria

| # | Condition | Threshold | Action |
|---|---|---|---|
| 0 | Cooper's review contradicts the numeric result | judgment | Hard stop |
| 1 | Working tree dirty at D0a | any | Hard stop before any write |
| 2 | Per-draw realizations neither persisted nor deterministically reproducible | any | Hard stop — D4 cannot run |
| 3 | Any read of a real event or any pass over `filtered_trades`/`filtered_quotes` | any | Hard stop |
| 4 | Any task would change a gate threshold, eligibility rule, injected scale, or required outcome | any | Hard stop — this document measures, it does not amend |
| 5 | Global envelope test type I error on C1 outside [0.02, 0.10] (D3f) | any | Hard stop — implementation is wrong, D3 unreadable |
| 6 | Envelope test implementation cannot be validated against the reference (D3a) | any | Hard stop — post what you have |
| 7 | Achievable draw count below 999 | < 999 | Hard stop — report the p-interval width and wait |
| 8 | Any write outside `results/phase_10b/diagnostic_1/`, `prompts/`, `config/`, `research/` | any | Hard stop |
| 9 | A second diagnostic round appears necessary | any | **Post and wait.** Do not write it |

---

## Chart Contract

`results/phase_10b/diagnostic_1/charts/NN_name.html`. Plotly, standalone, n annotated, raw values visible behind every aggregate.

| # | Filename | Question | Encoding | n annotation | Failure appearance |
|---|---|---|---|---|---|
| 09 | `09_excursion_map.html` | Are out-of-band rungs adjacent or scattered? | x = rung (log s); y = bandwidth; cell colour = above / below / inside; low-power rungs hatched; facet = control | rungs per bandwidth; run lengths in subtitle | Scattered single-rung hits across the ladder → excursions are noise, not structure at a scale |
| 10 | `10_global_envelope.html` | Does the control pass once multiplicity is handled? | x = rung (log s); y = curve value; global envelope ribbon; observed curve; pointwise band overlaid dashed for contrast; facet = control × bandwidth; p-value or p-interval annotated per panel | draws per envelope; eligible rung count | Global envelope barely wider than the pointwise band → multiplicity was not the problem and C2's failure is real |
| 11 | `11_knee_sampling_distribution.html` | How much does the knee move from draw to draw? | histogram of breakpoint estimate per control; injected scale as vertical rule; 95% interval shaded; ΔBIC ≤ 2 bracket overlaid as a separate span | draws per control | Interval spanning several rungs → the knee cannot locate a scale at all, and the +2–3× bias is beside the point |
| 12 | `12_bias_consistency.html` | Is it one bias or several? | bias in rungs with interval, one row per control, single-scale and multi-scale grouped; common-bias estimate as a vertical band | draws per control | Intervals not overlapping → no common bias, calibration cannot transfer to the real cohort |

---

## Config additions

Committed before any run. `config/phase_10b_diagnostic_1.json`.

| Key | Value | Used by |
|---|---|---|
| `n_envelope_draws` | 2499 | D3b |
| `n_type1_replicates` | 200 | D3f |
| `envelope_ordering` | `"extreme_rank_length"` | D3d |
| `envelope_alpha` | 0.05 | D3d, D3f |
| `intensity_reestimation` | `"per_simulation"` | D3c |
| `bootstrap_interval` | 0.95 | D4a, D4c |
| `min_envelope_draws` | 999 | Escalation row 7 |

No value in the original `config/phase_10b.json` or in A10b.1 is modified.

---

## Output Files

| File | Description | Status |
|---|---|---|
| `prompts/phase_10b_diagnostic_1.md` | This file | [ ] |
| `config/phase_10b_diagnostic_1.json` | New keys only | [ ] |
| `results/phase_10b/diagnostic_1/artifacts/d1_satisfiability_audit.json` | Every criterion, reachable yes/no, with the arithmetic | [ ] |
| `results/phase_10b/diagnostic_1/artifacts/d2_excursion_map.json` | Rung indices, run lengths, both inside-share readings | [ ] |
| `results/phase_10b/diagnostic_1/artifacts/d3_envelope_validation.json` | Reference comparison, type I error check | [ ] |
| `results/phase_10b/diagnostic_1/artifacts/d3_envelope_results.json` | p-values, envelopes, current-rule vs envelope verdicts | [ ] |
| `results/phase_10b/diagnostic_1/artifacts/d4_knee_distributions.parquet` | Per-draw breakpoint estimates, all controls | [ ] |
| `results/phase_10b/diagnostic_1/artifacts/d5_bias_consistency.json` | Common-bias estimate, interval, p-value | [ ] |
| `results/phase_10b/diagnostic_1/charts/09–12*.html` | Per contract | [ ] |
| `results/phase_10b/diagnostic_1/{REPORT.md, digest.json}` | Per standard | [ ] |

---

## Reporting

1. **Satisfiability table** — every criterion, target, achievable range, reachable yes/no; the eligible-bandwidth comparison across all three block rules.
2. **Excursion table** — rung indices, run lengths, above/below, inside-share with and without low-power rungs, expected-by-chance arithmetic alongside.
3. **Envelope validation** — reference comparison, type I error on C1, draw count achieved, p-interval width.
4. **Verdict comparison** — every control under the current rule against the global envelope test, with the driving rungs named where they disagree.
5. **Knee distribution table** — bias and spread separately, in rungs, per control; coverage of the injected scale; bootstrap interval against ΔBIC bracket.
6. **Multi-scale table** — C4 and C4′ breakpoints, separate intervals, overlap, whether compression is systematic.
7. **Bias consistency** — common-bias estimate with interval and p-value; single-scale versus multi-scale.
8. **Disposition table** (D6b) — each A10b.1 failure classified as specification defect, method limitation, or unresolved.
9. **Escalation check** — all 10 rows.
10. **Verification block** — script path, function, row counts in and out of every filter, reproduction command, config hash, for every number above. Plus explicit confirmation that no real event was read.
11. Output file table, commit list.

Description only. No recommendations. No characterisation of any result as good, promising, weak, or disappointing.

---

## Approval Gate

**Nothing here changes Phase 10b.** On completion, post and stop. Cooper reads charts 09–12 and decides among:

- **(a)** C2 and C1 resolve under existing rules or correct multiplicity handling → the gate passes as originally written, and Phase 10b resumes at T3 with the impossible C3 time-rescaling row struck as unsatisfiable.
- **(b)** The knee is usable as an interval rather than a point → Amendment 2, requiring an explicit row 15 override.
- **(c)** The knee's interval is too wide, or its bias does not transfer from single-scale to multi-scale → Phase 10b reports that the method cannot locate a cluster timescale, and that becomes the finding. **Note this would also put a factor-of-3 uncertainty on v3's 128 s / 16 s knee**, currently the strongest surviving result in the program, and that consequence gets recorded rather than absorbed.

**Do not proceed to any of these without Cooper's explicit choice.**
