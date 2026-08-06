# Phase 10b — Randomness of Trade Arrivals Under a Non-Constant Rate

**Date:** 2026-08-06
**Baseline:** Phase 10 v4, escalated (`phase/10`, unmerged, untagged as of drafting — **verify in T0a, do not assume**). Frozen cohort hash `e1a0ac73a79aa573`, 114 events.
**Objective:** Determine the timescale, if any, at which trade arrivals stop being explainable by an inhomogeneous Poisson process whose rate varies more slowly than that timescale — separately for premarket and regular-hours detections.
**Primary success metric:** Two independent crossing estimates (Allan-vs-matched-null, and time-rescaling under held-out intensity) are produced per segment, each with its synthetic-control validation passed, and their agreement against each other and against v3's knee is reported against the pre-registered bands in T5.

**Standard deviation notice (per `docs/Agent_Prompt_Standard.md`):** Analysis-only phase, no trade records, so §7 per-event charts are not required in the backtest sense. **They are required anyway** in the tape-review form specified in T6 — see the Standing Lessons note that row 0 is the only escalation criterion that has ever fired correctly. §9 chart contract applies in full.

**A negative result is a valid completion of this phase.** If arrivals are indistinguishable from a slowly-varying Poisson rate at every measured scale, that is the finding, it is reported as the finding, and no method is retuned to produce a positive one. Retuning in response to a null result is a banned output under Operating Plan §4.3.

---

## Context & Constraints

### What this phase is

Phase 10 tried five method families and all five failed the same way: each needed a reference level or a resolution — a bandwidth, a window, a threshold — and the answer tracked that choice rather than the market. The binary question "are there bursts?" is ill-posed, because "bursty" and "Poisson with a time-varying rate" are not distinguishable without constraining how fast the rate may vary. Let λ(t) wiggle freely and it absorbs every cluster; force it flat and everything is bursty.

The well-posed version, and the only question this phase asks:

> **At what timescale do arrivals stop looking random, given a rate allowed to vary more slowly than that?**

Timescale is therefore the reported axis, not a hidden parameter. Every bandwidth in this phase **defines the null being tested**, not the answer being reported, and every bandwidth is swept and reported as a family. **A single-bandwidth headline number is not a deliverable of this phase and must not appear in the report.**

### Carried-forward evidence (do not re-derive)

| Result | Value | Source |
|---|---|---|
| Frozen cohort | hash `e1a0ac73a79aa573`, 114 events | Phase 10 |
| Analysis cohort | 100 (premarket 28, regular-hours 70; row-cap 8 + sidecar 6 carried, labeled, **never pooled**) | Phase 10 |
| Detection anchor (D7) | 110/110 exact vs Phase 8 `det_minute`, reference deviation 0.000e+00 | Phase 10, validated |
| v3 Allan/Fano knee | **128 s** regular-hours, **16 s** premarket; ΔBIC 45.6–68.7 on all four cells | Phase 10 v3 |
| v3 regular-hours Allan curve | A = 5.99 at 15.6 ms, 1,245 at 4,096 s; slope 0.173 below knee, 1.017 above | Phase 10 v3 |
| v4 fragmentation mode | MRSN 2023-05-03: 7 prints inside 10.7 µs; median sub-burst duration 349 ns | Phase 10 v4 |
| Timestamp resolution | measured per event — median 80.5 ns, min 49 ns, max 8,388 ns | Phase 10 v1 |
| Session elevation | median 78.5× flanking baseline; 86% exceed 4× | Phase 10 |

### The correction that motivates T3's design — read this before writing any code

v3's Allan curve was compared against **theoretical Poisson (flat rate) = 1**. The rate is known not to be flat: session elevation is 78.5×, decay differs by three orders of magnitude across segments, and 28% of events peak before detection. Allan's successive differencing removes rate variation **slower than T**; at the long rungs, the event's own intensity profile varies plenty inside 2T and survives into the numerator. **A(T) = 1,245 at 4,096 s is therefore consistent with the null, not evidence against it.**

Consequences that are binding on this prompt:

- **No statement in the report may compare a real Allan curve to the constant 1.** The comparison object is the matched-null band from T3 and nothing else.
- The v3 knee at 128 s is, on present evidence, equally consistent with being the crossover between two artifacts — the fragmentation plateau below it and the intensity profile above it — as with being a burst timescale. **T1 and T3 are what distinguish those.** The prompt takes no position and neither may the report.

### Standing constraints

- **Cohort frozen.** Assert the hash. No redraw, no extension, no substitution.
- **Segment stratification from the start.** Premarket and regular-hours are computed and reported separately at every task. Pooled-across-segment statistics are not produced.
- **No aggregation of prints.** Cooper's standing call from Phase 10. Every print is kept. Where a scale is uninterpretable because of fragmentation, **decline to interpret it** rather than aggregate through it. The sweep-run definition in T1 is a **diagnostic grouping for a scatter plot only** — it must not enter any Allan, intensity, or rescaling computation anywhere in this phase.
- **D4 stands.** All quantities tick-derived. No spine numeric on any computation path. `momentum_pct` for cohort identification only.
- **Pass budget over `filtered_trades` / `filtered_quotes` is zero.** Targeted folder reads only; equivalence proven in v1 T0d.
- **Phase 13 boundary.** Intervals are an operating variable here. This phase does **not** produce the inter-trade interval distribution as a characterized finding, the noise floor, or interval regime definitions. If a task appears to be producing one, stop and post.
- **Offline. Nothing here is a detector.** Causal audit tagging carries forward from v4 — every derived field tagged causal or non-causal.
- **Escalation row 13 as amended:** writes permitted to `prompts/`, `config/`, `research/`, `results/`, plus **append-only** to `docs/Universe-Decisions.md` and `docs/Research-Library-Map.md`. Row 13 covers `docs/Claude-Code-Operating-Plan.md` for the single T0c edit specified below and nothing else.
- **Every tunable in `config/phase_10b.json`.** No magic numbers in code. Ladders, sweep bounds, thresholds, seeds, all of it.
- **Chart standard.** No finding without its chart. Every statistic carries its n.

### Closed — do not reopen

D6 (no within-session quiet state), D8 (event-relative reference), D9 (interval-based, no intensity curve as operating variable). Hawkes calibration. Constant-reference thresholding, two-state segmentation, envelope fitting, print aggregation, time-of-day-matched flanking baselines. Any task that finds itself needing one of these is a hard stop, not a workaround.

---

## Tasks

### T0 — Repository management and Phase 10 close-out

This runs first, in full, before any measurement. **Do not begin T1 until T0 is committed and posted.**

- [ ] **T0a — Verify state, assert nothing.**
  Report, from `git` and the filesystem rather than from this prompt: current branch; whether `phase/10` exists and its tip; whether tags `phase-10-approved` or any `phase-10*` tag exist; the `status` field of every `results/phase_10*/digest.json` found; whether the working tree is clean; which of v1–v4 have committed prompts and configs. **Hard stop if the working tree is dirty.** Post the table before doing anything else.
  - [ ] T0a1 — Commit nothing in this task; it is read-only.

- [ ] **T0b — Close Phase 10 as a recorded negative result.**
  Set the Phase 10 digest `status` → `complete_approved`, with a headline metric row `{"name": "burst_timescale_established", "value": 0, "n": 100, "source": "results/phase_10/REPORT.md"}` and a `surprises` entry naming the shared root cause (every method's answer tracked its own reference level or resolution). Tag `phase-10-approved` at the branch tip. Fast-forward `main`.
  **Approval here is approval of the phase, not of a finding.** The surviving results — the detection anchor validation, the 28% negative detection-to-peak share, the segment split, the session elevation, the concentration figures, and the v3 Allan/Fano gate — are what is being merged. They are currently stranded on an unmerged branch and that is the problem this task fixes.
  - [ ] T0b1 — Post the exact digest diff before writing it.
  - [ ] T0b2 — Commit.

- [ ] **T0c — Record D10 and the numbering.**
  Append to `docs/Universe-Decisions.md`, verbatim:

  > **D10 — Phase 10b scoping and numbering**
  > **Date:** 2026-08-06 · **Deciding phase gate:** Cooper decision at the Phase 10 close-out
  > **Decision:** The arrival-randomness work is numbered **Phase 10b**, not Phase 11. It is a direct continuation of Phase 10 — same object, better-founded methods — and the numbering says so.
  > **Consequence:** Operating Plan §6 row 11 (*Spread & impact by participation*) is **preserved unchanged**, along with rows 12–19. The row-*n*-is-`prompts/phase_{n}.md` contract established 2026-08-03 is not broken and no downstream row is renumbered.
  > **Recorded alongside:** row 11's participation-bucketed effective-spread half does not depend on a burst timescale and is executable independently of Phase 10b's outcome. Only its "burst vs. quiet" half is blocked. This is recorded so the cost-stack measurement is not treated as blocked in full by Phase 10's failure.

  Then add one row to `docs/Claude-Code-Operating-Plan.md` §6, immediately below row 10, labeled **10b**, name *Randomness of trade arrivals under a non-constant rate*, gate *Crossing timescale is a number, or its absence is a recorded finding*. **Insert only. Do not renumber, do not edit any other row.**
  - [ ] T0c1 — Commit.

- [ ] **T0d — Cut the branch and lay out the new results folder.**
  Cut `phase/10b` from `main`. Create `results/phase_10b/` with `charts/`, `artifacts/`, and `event_charts/`. **Nothing in this phase writes to any `results/phase_10*` path other than `results/phase_10b/`.** Commit `prompts/phase_10b.md` and `config/phase_10b.json` before any other work in the branch.
  - [ ] T0d1 — Commit.

- [ ] **T0e — Cohort assertion.**
  Recompute the cohort hash and assert `e1a0ac73a79aa573`. Assert 114 total, analysis cohort 100, premarket 28, regular-hours 70, row-cap 8, sidecar 6. **Hard stop on any mismatch, including a mismatch in the segment split.** Report the per-event timestamp resolution distribution as a precondition, not an assumption.
  - [ ] T0e1 — Commit.

### T1 — Fragmentation-plateau check

Cheap, and it may reframe the phase. Runs before any new machinery is built.

**Hypothesis under test:** the near-flat Allan plateau below the v3 knee is execution fragmentation, and its height is set by sweep size rather than by anything about the market.

- [ ] **T1a — Verify the inputs exist.** Confirm `results/phase_10*/artifacts/` holds **per-event** v3 Allan curves and the v4 sub-burst artifacts. **Hard stop if only pooled Allan curves survive** — the check requires per-event pairing and cannot be run on pooled output.
- [ ] **T1b — Sweep-run diagnostic grouping.** Per event, group consecutive prints into maximal runs with inter-print gap ≤ `sweep_gap_s` (config: primary 1e-4 s, sensitivity rungs 1e-5 s and 1e-3 s). For each event compute: run count, plain mean run size E[N], and **size-weighted mean run size E[N²]/E[N]**, each with its n.
  **This grouping exists only to produce the x-axis of chart 01. It is written to its own artifact and is not readable by any later task.** Assert this in the verification block.
- [ ] **T1c — Plateau height.** Per event, take the mean of log A(T) over the flat region, defined in config as rungs 2^-6 s through 2^2 s, and report the within-event dispersion across those rungs alongside it. An event whose "plateau" has interquartile range in log A exceeding `plateau_flatness_max` (config: 0.35 in natural log) is **not flat** and is excluded from the fit and counted in the report.
- [ ] **T1d — The test.** Regress plateau height on E[N²]/E[N], per segment. **The prediction is a slope near 1 against the size-weighted mean, not against the plain mean** — for a cluster process with variable cluster size the plateau tracks the second moment over the first, and testing against E[N] alone will produce a slope below 1 and a spurious rejection. Report both regressions so the difference is visible.
- [ ] T1e — Chart 01. Commit.

**No escalation row fires on T1's outcome.** Both outcomes are informative and both are reported. If the plateau does track sweep size, T3 and T4 decline to interpret below the plateau's upper edge and say so. If it does not, that is recorded as an open surprise and the phase continues unchanged.

### T2 — Synthetic control harness

**This is the gate for the whole phase.** Nothing in T3, T4 or T5 is interpretable until T2 passes. Outcome-shaped failure criteria have been written five times across Phase 10 and caught the real problem zero times, because an outcome threshold cannot detect a method stably measuring the wrong object. These are thresholds on **known answers** instead.

Build the T3 and T4 pipelines here, and run them end to end on simulated inputs **before** any real event is touched. The pipeline code is shared — no separate control implementation, or the control tests nothing.

- [ ] **T2a — C1, homogeneous Poisson.** Rate matched to a real regular-hours event's mean, same duration, same timestamp quantization (80.5 ns). n = `n_control_draws` (config: 200).
  **Required outcome:** T3 curve inside the 95% matched-null band on ≥ 90% of eligible rungs; T4 reports no interior crossing.
- [ ] **T2b — C2, inhomogeneous Poisson with a real event's shape.** λ(t) taken from a real event's smoothed profile, arrivals redrawn.
  **Required outcome:** same as C1. This is the control that would have caught v1 Arm A — a method that finds burst structure in C2 is measuring the intensity profile, not clustering.
- [ ] **T2c — C3, cluster process with known parameters.** Fixed cluster size `k` = 6, cluster duration 10 µs, background rate matched to a real event.
  **Required outcome:** T1c plateau height within ±25% of E[N²]/E[N]; T3 and T4 crossings each within 1 rung of the injected 10 µs.
- [ ] **T2d — C4, two injected scales.** 6-print sweeps at 10 µs **plus** 20-print clusters at 60 s, on the same matched background.
  **Required outcome:** both scales visible and separated in T3's curve; T4 recovers the 60 s scale within 1 rung. This is the control for the actual claim the phase might make — that there is a fragmentation scale and a separate event scale.
- [ ] **T2e — Band coverage.** Verify the matched-null band achieves nominal coverage on C1 and C2 at each rung: empirical coverage within [0.90, 0.99] for a nominal 95% band. Under-coverage means the band is too narrow and every subsequent "outside the band" result is inflated.
- [ ] T2f — Chart 04. Commit.

**Hard stop on any C1–C4 required outcome not met.** Do not proceed to T3. Do not adjust the method to make a control pass — post the control output and wait.

### T3 — Allan factor against a matched null, real cohort

- [ ] **T3a — Ladder.** Powers of 2 in seconds, **2^-20 (0.954 µs) through 2^12 (4,096 s)**, 33 rungs. v3's 19 rungs (2^-6 through 2^12) are a strict subset, so v3's numbers remain directly comparable rung-for-rung — assert that comparability numerically, do not claim it.
  The floor extends below v3's because the fragmentation plateau's **lower** edge sits below 15.6 ms and T1's hypothesis cannot be closed without seeing where the plateau starts. 2^-20 is ~12× the median 80.5 ns resolution; going lower measures quantization.
- [ ] **T3b — Power annotation, and it is load-bearing.** For every rung report the number of adjacent window pairs, per event and pooled per segment. A regular-hours session is ~23,400 s, so T = 4,096 s yields ~2 pairs per event. **Rungs with fewer than `min_pairs_pooled` (config: 20) pooled pairs are plotted greyed and excluded from crossing determination; per-event curves require `min_pairs_event` (config: 5).** Report explicitly which rungs this excludes.
  **Note for the report:** this places v3's headline A = 1,245 at 4,096 s inside the low-power zone. State the pair count next to that figure wherever it is cited.
- [ ] **T3c — Matched null.** For each event, estimate λ̂(t) at each bandwidth h in the T4a sweep, simulate `n_null_draws` (config: 200) inhomogeneous Poisson realizations from λ̂ with the event's own duration and timestamp quantization, compute each realization's Allan curve, and take the 2.5/97.5 percentiles per rung as the band.
  **The band is a family over h, not one band.** Report the full family. The crossing is where the real curve leaves the band **at the widest h for which it still leaves it** — that is the strongest statement, because it is the crossing that survives the most permissive null.
- [ ] **T3d — Crossing.** Per segment, per h: the lowest eligible rung above which the real pooled curve is outside the band at every subsequent eligible rung. Report as a rung index with its bracketing seconds, not as a point estimate with false precision.
- [ ] T3e — Charts 02, 03. Commit.

### T4 — Time-rescaling under held-out intensity

Naive time-rescaling is circular. Inverted — sweep the bandwidth, find where residual clustering vanishes — it is still circular **if λ̂ is fitted in sample**: as h shrinks, λ̂ puts a bump under every arrival, the residual degenerates for reasons that have nothing to do with the market, and a crossing is guaranteed to exist at a location set by the estimator's degrees of freedom. That is Phase 10's failure mode wearing a different hat.

**λ̂ is therefore fitted out of sample throughout.** This is standard practice, not a local invention — cross-validated bandwidth selection for kernel intensity estimation is long established (Rudemo 1982; Bowman 1984; Diggle's and the likelihood cross-validation selectors in `spatstat`; Shimazaki & Shinomoto 2010 for the spike-rate case, which introduces an explicit stiffness constant to prevent exactly this overfitting).

- [ ] **T4a — Bandwidth sweep.** Powers of 2 in seconds, **2^-6 (15.6 ms) through 2^14 (16,384 s)**, 21 rungs. The bounds are deliberately outside the interesting range at both ends: 2^-6 is narrow enough to be degenerate, 2^14 is wider than a regular-hours session and so effectively flat. **A crossing that lands on either endpoint is not a crossing — it is the sweep hitting its own boundary, and must be reported as such.** Gaussian kernel, config-specified.
- [ ] **T4b — Held-out fitting.** Partition each event's session into fixed 60 s blocks, independent of h. Fit λ̂ on odd blocks, evaluate rescaled intervals on even blocks; then swap. Report both folds separately — a large fold difference is itself a finding.
- [ ] **T4c — Intensity floor and its accounting.** At small h, λ̂ from neighbouring blocks contributes almost nothing inside a held-out block and Λ collapses. Floor λ̂ at `lambda_floor_frac` × (event print count / event duration), config 1e-3. **Report the fraction of held-out time sitting at the floor, per bandwidth, per segment. Bandwidths with more than `floored_time_max` (config: 0.20) floored time are excluded from crossing determination and shaded on chart 05.** Without this accounting the small-h end reports the floor rather than the market.
- [ ] **T4d — Goodness of fit.** Kolmogorov–Smirnov statistic of the rescaled intervals against unit exponential, per event, per h, per fold, each with its n. Pool per segment by reporting the distribution of per-event statistics, not a pooled statistic over pooled intervals.
- [ ] **T4e — Crossing.** The smallest h at which the per-event KS distribution is consistent with exponential at `ks_alpha` (config: 0.05) for at least `ks_pass_share` (config: 0.50) of the segment's events, and remains so at every larger eligible h. Report the share-vs-h curve, not just the crossing.
- [ ] **T4f — Reference marker, not a choice.** Also compute the Shimazaki–Shinomoto optimized bandwidth per event and mark its distribution on chart 05. It is an objectively selected bandwidth, so its position relative to the crossing is informative. **It does not select anything in this phase** and no result is conditioned on it.
- [ ] T4g — Charts 05, 06. Commit.

### T5 — Cross-method agreement, pre-registered

v1's two arms agreed at median Jaccard 0.31 with zero events matching on burst count and nothing was watching it. This task is what watches it.

- [ ] **T5a** — Assemble the three estimates per segment: T3 Allan crossing, T4 time-rescaling crossing, v3's knee (128 s regular-hours, 16 s premarket).
- [ ] **T5b — Agreement bands, fixed before the run.** The ladder resolution is a factor of 2, so:

| Spread across the three estimates | Reading | Action |
|---|---|---|
| ≤ 1 rung (factor 2) | Agreement | Report as the phase's convergent estimate |
| 2 rungs (factor 4) | Partial | Report all three, no single headline number |
| > 2 rungs | Disagreement | **Escalation row 6 — hard stop** |

  Applied per segment separately. A segment where one method produces no crossing at all is not a disagreement — it is reported as a non-result for that method and the remaining two are compared.
- [ ] T5c — Chart 08. Commit.

### T6 — Tape review

**Produced regardless of every numeric outcome above, including a T2 hard stop.** v2 skipped this and could not be judged at all; v3 produced it and row 0 fired correctly.

- [ ] **T6a** — Per event, a standalone Plotly HTML with shared x-axis: panel 1, individual trade prints (price, size-scaled markers); panel 2, inter-trade time on log scale; panel 3, the T3 Allan crossing and T4 crossing drawn as horizontal reference scales with the v3 knee alongside. Zoom-linked. Full cohort of 100, both segments, labeled.
- [ ] **T6b** — Sortable index at `results/phase_10b/event_charts/index.html` covering all 114 including row-cap and sidecar, labeled and never pooled. Sortable by ticker, date, segment, print count, sweep-run count, T3 crossing rung, T4 crossing rung.
- [ ] T6c — Commit.

### T7 — Report and digest

- [ ] **T7a** — `results/phase_10b/REPORT.md` per §6 and §10. Every claim cites its chart. No recommendations. No causal language. **No comparison of any Allan curve to the constant 1.**
- [ ] **T7b** — `results/phase_10b/digest.json` per §11, ≤ 100 lines. The `surprises` field is expected to be non-empty.
- [ ] T7c — Commit. Post digest.

---

## Escalation Criteria

Stop, commit current state, post results, name the criterion and the observed value, and wait. Do not fix. Do not tune. Do not proceed. **Report in table order — the table is the priority order.**

| # | Condition | Threshold | Action |
|---|---|---|---|
| **0** | **Cooper's visual review against the tape (T6) contradicts the numeric result** | Cooper's judgment | **Hard stop.** Stays at the top; the only criterion that has ever fired correctly |
| 1 | Working tree dirty at T0a, or observed repo state differs from T0a's own report | any | Hard stop before any write |
| 2 | Cohort hash ≠ `e1a0ac73a79aa573`, or any count in T0e mismatched | any | Hard stop |
| 3 | Per-event v3 Allan curves not found (T1a) | absent | Hard stop — T1 cannot run on pooled output |
| 4 | Any C1–C4 required outcome not met (T2a–T2d) | any | Hard stop — do not proceed to T3, do not adjust method |
| 5 | Matched-null band coverage outside [0.90, 0.99] on C1 or C2 (T2e) | any rung | Hard stop |
| 6 | Cross-method spread > 2 rungs on either segment (T5b) | > 2 rungs | Hard stop |
| 7 | T4 crossing lands on either sweep endpoint (2^-6 or 2^14) | either | Hard stop — sweep boundary, not a crossing |
| 8 | Floored held-out time > 0.20 at every bandwidth in the sweep for a segment | all rungs | Hard stop — no interpretable region exists |
| 9 | Two folds in T4b give crossings differing by > 2 rungs | > 2 rungs | Hard stop |
| 10 | Any task requires a Phase 13 deliverable (interval distribution, noise floor, interval regime definitions) | any | Hard stop — scope boundary |
| 11 | Any task requires print aggregation, a constant reference threshold, two-state segmentation, envelope fitting, or a flanking baseline | any | Hard stop — closed by prior decision |
| 12 | Any read or write of a spine numeric column on a computation path | any | Hard stop — D4 |
| 13 | Any write outside `prompts/`, `config/`, `research/`, `results/phase_10b/`, the append-only `docs/Universe-Decisions.md` and `docs/Research-Library-Map.md`, and the single specified `docs/Claude-Code-Operating-Plan.md` insert | any | Hard stop |
| 14 | Any full-table pass over `filtered_trades` or `filtered_quotes` | any | Hard stop — pass budget is zero |

**No escalation criteria apply to T1's outcome.** Both outcomes are informative. State that explicitly in the T1 report section.

---

## Chart Contract

`results/phase_10b/charts/NN_name.html`. Plotly, standalone, one chart per file, n annotated per bucket, no smoothing unless specified, log scale where multiplicative, raw points behind every aggregate where point count permits.

| # | Filename | Question | Encoding | n annotation | Failure appearance |
|---|---|---|---|---|---|
| 01 | `01_plateau_vs_sweep_size.html` | Does the sub-knee Allan plateau height track sweep size? | x = size-weighted mean run size E[N²]/E[N] (log); y = plateau height (log); colour = segment; **second trace against plain E[N] for contrast**; fit overlaid; raw points visible | n per segment; excluded non-flat events counted in subtitle | Flat scatter, or slope ≠ 1 against **both** x-definitions → plateau is not fragmentation, and T3's sub-knee region is not explained |
| 02 | `02_allan_matched_null.html` | Where does the real Allan curve leave a matched-Poisson band? | x = rung (log s); y = A(T) (log); real curve solid; band ribbons, one per bandwidth h; facet = segment; low-power rungs greyed | pooled window-pair count per rung on hover and axis strip | Real curve inside the band at every rung → arrivals random at every scale, Cooper's hypothesis holds |
| 03 | `03_allan_per_event.html` | Is the pooled curve representative, or driven by a few events? | per-event curves as translucent spaghetti, median overlaid, band behind; facet = segment | n events per segment; per-event pair counts in hover | Wide fan with no common shape → pooled curve is an artifact of pooling and T3d's crossing is not a population statement |
| 04 | `04_synthetic_controls.html` | Does the pipeline return the right answer on data with a known answer? | 2×2 facet C1–C4; same encoding as 02; injected scales marked with vertical rules on C3/C4 | n draws per control | C1 or C2 outside the band → the method finds structure in Poisson data; C3 or C4 misses its injected scale → it cannot find structure that is there |
| 05 | `05_ks_vs_bandwidth.html` | At what bandwidth does residual clustering vanish out of sample? | x = bandwidth h (log s); y = share of events passing exponential KS; one trace per fold; facet = segment; floored-time > 0.20 region shaded; Shimazaki–Shinomoto bandwidth distribution as a rug | n events per segment; floored-time fraction on secondary axis | Monotone rise straight into the small-h boundary → in-sample-style overfitting survived the held-out design; flat at zero everywhere → no bandwidth explains the arrivals |
| 06 | `06_exponential_qq.html` | What does the residual actually look like at and around the crossing? | Q-Q of rescaled intervals vs unit exponential, at the crossing h and at ±2 rungs; facet = segment × h; 45° reference; per-event traces translucent | n intervals per panel | Heavy upper tail at every h → clustering the rate never explains; straight line at every h including the widest → no clustering to find |
| 07 | *(per-event, see T6)* | — | — | — | — |
| 08 | `08_method_agreement.html` | Do the three independent estimates land in the same place? | x = timescale (log s); three markers per segment with rung-width error bars; ±1 and ±2 rung agreement bands shaded | n events behind each estimate | Markers spread across decades → no convergent timescale; and per T5b that is a hard stop, not a result to average over |

---

## Output Files

| File | Description | Status |
|---|---|---|
| `prompts/phase_10b.md` | This prompt | [ ] |
| `config/phase_10b.json` | Ladders, sweep bounds, kernel, seeds, all thresholds | [ ] |
| `docs/Universe-Decisions.md` | D10 appended | [ ] |
| `docs/Claude-Code-Operating-Plan.md` | §6 row 10b inserted, nothing else touched | [ ] |
| `results/phase_10/digest.json` | Status → `complete_approved`, negative headline metric (T0b) | [ ] |
| `results/phase_10b/artifacts/t0e_cohort_assertion.json` | Hash, counts, per-event timestamp resolution | [ ] |
| `results/phase_10b/artifacts/t1_sweep_runs.parquet` | Diagnostic grouping — chart 01 x-axis only, read by nothing else | [ ] |
| `results/phase_10b/artifacts/t1_plateau_fit.json` | Both regressions, exclusions counted | [ ] |
| `results/phase_10b/artifacts/t2_controls.json` | C1–C4 outcomes, band coverage | [ ] |
| `results/phase_10b/artifacts/t3_allan_curves.parquet` | Per-event curves, pair counts, band family over h | [ ] |
| `results/phase_10b/artifacts/t3_crossings.json` | Per segment, per h | [ ] |
| `results/phase_10b/artifacts/t4_ks_sweep.parquet` | Per event, per h, per fold; KS, n, floored-time fraction | [ ] |
| `results/phase_10b/artifacts/t4_crossings.json` | Per segment, both folds | [ ] |
| `results/phase_10b/artifacts/t5_agreement.json` | Three estimates, spread in rungs, band verdict | [ ] |
| `results/phase_10b/charts/01–06, 08*.html` | Per contract | [ ] |
| `results/phase_10b/event_charts/{TICKER}_{DATE}.html` + `index.html` | T6, all 114 in the index | [ ] |
| `results/phase_10b/REPORT.md`, `digest.json` | Per standard | [ ] |

---

## Reporting

On completion, post:

1. **T0 close-out table** — repo state observed, digest diff applied, tag and merge confirmed, D10 recorded.
2. **Cohort assertion** — hash, all counts, timestamp resolution distribution with n.
3. **T1 table** — both regressions (size-weighted and plain), slopes with confidence intervals, excluded non-flat event count, per segment.
4. **T2 control table** — C1–C4, each required outcome, observed, pass/fail; band coverage per rung summary.
5. **T3 table** — crossing rung per segment per bandwidth, with pooled pair count at each crossing rung, and the widest h at which the crossing survives.
6. **T4 table** — crossing bandwidth per segment per fold, share-passing at the crossing, floored-time fraction, Shimazaki–Shinomoto bandwidth median for reference.
7. **T5 agreement table** — three estimates per segment, spread in rungs, band verdict.
8. **Escalation check table** — all 15 rows, observed value, pass/fail.
9. **Verification block** (§10) — for every headline number: the script path and function, row counts in and out of every filter, a one-line reproduction command, the config hash. Plus the explicit assertion that `t1_sweep_runs.parquet` is read by no task other than chart 01.
10. **Output file table** with final status.
11. **Commit list.**

Every posted table carries n per row. Every prose claim carries its chart filename. Description only — no recommendations, no "suggests / confirms / indicates / therefore".

On escalation, post: which criterion triggered and the observed value; the tables completed up to that point; no recommendations.

---

## Approval Gate

Do not begin Phase 11 (*Spread & impact by participation*, unchanged) or any follow-on work until Cooper has reviewed the charts and given explicit approval. **The crossing timescale — or the finding that none exists at a tradeable scale — is read by Cooper from charts 02, 05 and 08, not asserted by the agent.**

If this phase concludes that no burst timescale exists at a tradeable scale, that makes D5's premise wrong and forces Phases 13, 14, 16 and 17 to re-anchor to detection, clock time, or price-path events. **That is a first-order program finding, not a sixth failure**, and it is reported in exactly those terms.
