# Phase 10 — Burst Decomposition

**Date:** 2026-08-04
**Branch:** `phase/10`
**Baseline:** `phase-9-approved`
**Objective:** Produce a per-event segmentation of the T=0 session into bursts, and from it the burst timescale — count, duration, spacing, and the fraction of the session move each burst carries.
**Primary success metric:** A burst segmentation that Cooper accepts on visual review against the actual tape, with burst count / duration / spacing distributions and a burst-relative concentration curve behind it.

**Gate significance:** this phase produces the number every downstream horizon in the program is expressed in. The burst-relative latency budget derived here replaces the session-anchored one from Phases 6 and 6b (D5 consequence (b), D5 Amendment A11). Nothing downstream is anchored correctly until this lands.

---

## Cooper decision points encoded in this draft

Two method choices were made by the architect and are flagged here rather than buried. **Confirm or override before this prompt is committed.**

1. **Baseline definition differs by arm, deliberately.** Arm A (Kleinberg) uses its own self-normalizing within-session baseline. Arm B (threshold + hysteresis) uses a time-of-day-matched flanking-day baseline. They are not made to match. The point is that the two arms disagree in an informative way rather than a confounded one.
2. **Two-state only.** Kleinberg's infinite-state (hierarchical, nested-burst) variant is **not** run this phase. It maps well onto "one large impulse containing sub-bursts" and may be worth a later amendment, but it multiplies both the output volume and the review burden, and the two-state result is the prerequisite for judging whether the hierarchy is needed.

---

## Context & constraints

- **This phase is tick-grain and therefore not scan-free.** Burst segmentation operates on individual trade prints, not minute bars. `event_minute_bars_v2` is insufficient. **The pass budget over the full `filtered_trades` table is zero** — all reads are targeted per-event reads against the committed cohort, joined through the canonical spine. If any read plans as a full-table scan, that is escalation row 4, not a budget question.
- **Scope is bounded to a committed cohort, not the full population.** Dev v4 primary cohort (50 events, seed 42, pinned) plus a stratified extension drawn per T1. There is no full-population run in this phase. A full-population run is a separate authorization.
- **D4 stands.** Every computed quantity is tick-derived. No spine numeric column (any OHLC or volume field) enters any computation. `momentum_pct` is permitted for cohort stratification only, per its standing universe-selection exception — it measures nothing within this phase.
- **Scope boundary — inter-trade intervals belong to Phase 13.** This phase uses inter-trade time as a **diagnostic display axis** on the per-event charts and as an input to Arm A's likelihood. It does **not** produce inter-trade interval distributions, characterize the noise floor, or define burst-vs-quiet interval regimes. Those are Phase 13's deliverable. If a task appears to require producing that distribution as a finding, stop and post — do not define it here and leave Phase 13 to inherit an unvetted definition.
- **This is offline segmentation, not detection.** Arm A is non-causal by construction: the optimal state sequence uses the full session. That is correct for this phase and is the same relationship Phase 16's offline regime labels have to Phase 17's online detector. **No output of this phase may be described as a detector, an entry signal, or an operating point.**
- **Row-cap contamination is load-bearing here, not a footnote.** A collector row cap truncates the tail of the session — which is exactly where burst termination and the bull-to-bear flip live. `flag_possible_row_cap` events are carried, labeled, and reported as their own row throughout. Never pooled. See the ARBB item in `docs/Open-Items-Register.md`.
- **Flag, never delete.** Any event failing a coverage or definedness condition is carried with a label and reported separately.
- Standard §§9–12 of `docs/Agent_Prompt_Standard.md` apply in full — chart contract, verification block, digest contract, git discipline. Every statistic carries its n. Every claim cites its chart.
- Standing constraints in `CLAUDE.md`. Decisions in `docs/Universe-Decisions.md`. Working directory: repo root.

---

## Tasks

- [ ] **T0 — Branch, prompt, config, preconditions**
  Cut `phase/10` from main.

  - [ ] T0a — Confirm tag `phase-9-approved` exists and main is at it. If absent, escalation row 1.
  - [ ] T0b — Commit `prompts/phase_10.md` before any other work.
  - [ ] T0c — **Author `config/phase_10.json` and commit it before any run.** Every tunable lives in config, none inline. At minimum it must carry: cohort definition and seed; both arms' parameters (Arm A `s` and `gamma`; Arm B on/off multipliers, minimum dwell, merge-gap tolerance); the baseline construction rule per arm; the sensitivity grid for both arms; the four pre-registered failure thresholds; the per-event chart selection rule and count cap; runtime ceilings. Where this prompt does not pin a value, propose one, record the reasoning in `decisions_log`, and make it a config key — do not hard-code it.
  - [ ] T0d — Report the tick surface available for the cohort: per-event print counts on T=0 and on each flanking session, coverage per side, and which cohort events carry `flag_possible_row_cap` or any residual coverage flag. This establishes what the segmentation is actually running on before it runs.
  - [ ] T0e — Commit.

- [ ] **T1 — Cohort construction**
  Dev v4 primary cohort (50 events) is the spine. Extend it with a stratified draw so the cohort spans the range of session activity rather than clustering at one intensity. Stratification variable and draw size are yours to propose, seeded and recorded in config; `momentum_pct` decile is the established precedent but is not mandated if you can motivate better. The 6 flagged dev v4 sidecar events are **carried separately and never pooled into cohort-level statistics** — they are deliberately degraded-archive events and exist to exercise broken-data code paths.
  - [ ] T1a — Write the cohort manifest as a committed artifact. Join it to `momentum_events_canonical` with `in_scope = TRUE` and report the match count. Any shortfall is escalation row 2.
  - [ ] T1b — Commit.

- [ ] **T2 — Arm A: Kleinberg continuous two-state**
  Kleinberg's burst detection for **continuous streams** — the two-state automaton over inter-arrival gaps, per "Bursty and Hierarchical Structure in Streams" (2002). This is the first half of the paper, not the batched-data variant: our observable is trade arrival times with no natural per-period denominator, so the batched proportion model does not apply.

  Existing implementations (`pybursts` in Python, `bursts` in R) may be used or the algorithm implemented directly — your call, recorded in `decisions_log` with the reason. If an external package is used, pin its version in config and state what was verified about its behaviour rather than assuming it.

  Baseline: **self-normalizing within-session**, per the decision block above. `s` sets the multiplicative distance between states; `gamma` sets the state-transition cost. Report both as configured and note explicitly that `gamma` is doing the work a minimum-dwell floor does in Arm B.
  - [ ] T2a — Per-event optimal state sequence over the T=0 session, resolved to burst intervals with start and end timestamps.
  - [ ] T2b — Report runtime per event and in aggregate. Escalation row 5 if the ceiling is breached.
  - [ ] T2c — Commit.

- [ ] **T3 — Arm B: threshold + hysteresis**
  The comparison arm. Trade arrival rate against a **time-of-day-matched flanking-session baseline** — rate at a given minute-of-session compared against the same minute-of-session across T-3…T-1 for that ticker, in log space. A whole-day average baseline is not acceptable: these names trade thin for weeks and then enormously on the event day, so a whole-day denominator saturates immediately and the segmentation degenerates into a session flag.

  Burst-on above the on-multiplier, burst-off below the off-multiplier, off strictly below on. Minimum dwell floor and merge-gap tolerance applied. All four parameters in config.
  - [ ] T3a — Per-event burst intervals, same output shape as T2a so the arms are directly comparable.
  - [ ] T3b — Report per-event baseline definedness. Events with insufficient flanking coverage to build a baseline are labeled and carried, not dropped.
  - [ ] T3c — Commit.

- [ ] **T4 — Burst-level measurements**
  Computed identically for both arms, reported side by side. Never pooled across arms.
  - [ ] T4a — Per-event burst count; duration per burst; spacing between consecutive bursts.
  - [ ] T4b — Fraction of the T=0 session move carried within each burst. Session move is tick-derived; state the denominator definition explicitly and report its undefined count.
  - [ ] T4c — **Burst-relative concentration curve** — cumulative share of move and of volume against time measured from burst confirmation, not from session open. This is the quantity that replaces the session-anchored decay curve as the latency budget input.
  - [ ] T4d — Time from burst start to the burst's own price extreme, distribution. This is the burst-scale analogue of the runway measurement and is the input Cooper needs to read a budget off chart 06.
  - [ ] T4e — All measurements reported with `flag_possible_row_cap` events broken out as their own row, and the dev v4 sidecar broken out as its own row.
  - [ ] T4f — Commit.

- [ ] **T5 — Sensitivity and stability**
  Both arms, over the config sensitivity grid.
  - [ ] T5a — Burst-set overlap under parameter perturbation, per arm. Define the overlap measure explicitly and justify it in `decisions_log` — an interval-overlap measure and a burst-count-agreement measure answer different questions and both are defensible; state which you chose and why.
  - [ ] T5b — Cross-arm agreement: where Arm A and Arm B agree and disagree on the same events, quantified with the same measure.
  - [ ] T5c — Evaluate all four pre-registered failure criteria against observed values. Report the table with observed value against threshold and pass/fail per row. **Do not characterize the result beyond pass/fail.**
  - [ ] T5d — Commit.

- [ ] **T6 — Charts**
  Per the contract below, kaleido-verified.
  - [ ] T6a — Charts 01–06.
  - [ ] T6b — **Chart 07, the per-event tape review set.** This is the chart the gate turns on. Bounded selection per config: the full dev v4 primary cohort plus a stratified draw by burst count spanning the top and bottom of the distribution and a seeded random middle. Sidecar events included but labeled. Sortable index over the full cohort. **Do not emit a chart per event across the whole cohort if that exceeds the config cap** — the §12 gitignore rule on `event_charts/` exists because thousands of multi-megabyte files broke prior phases.
  - [ ] T6c — Commit.

- [ ] **T7 — Digest and report**
  `digest.json` per §11. `REPORT.md` per the Evidence Standard.

  **Description only.** State the burst count, duration, and spacing distributions with their n. State which failure rows passed and which failed. State where the arms agree and disagree. **Do not state what the burst timescale implies for strategy design, do not propose a latency budget, do not select an arm, and do not characterize any result as good, promising, weak, or disappointing.** The latency budget is read by Cooper off chart 06. The arm selection is Cooper's off chart 07.
  - [ ] T7a — Commit; working tree clean.

---

## Pre-registered failure criteria

Fixed before the run. Evaluated at T5c. These are the conditions under which the segmentation method is judged to have failed, distinct from the operational hard stops below.

| # | Failure mode | Observable | Threshold | Applies to |
|---|---|---|---|---|
| **0** | **Cooper rejects the segmentation on visual review of chart 07 against the tape** | — | **Cooper's judgment, no numeric threshold** | **Both arms. Overrides rows 1–4 in either direction.** |
| 1 | Degenerate to session flag | Share of cohort events whose segmentation yields a single burst spanning the majority of the session | Threshold in config | Both arms |
| 2 | Fragmentation at the floor | Median burst duration sitting at or below the minimum dwell floor — the rule re-emitting its own parameter | Threshold in config | Arm B primarily; report for both |
| 3 | Parameter instability | Burst-set overlap under the sensitivity grid | Threshold in config | Both arms |
| 4 | No structure | Burst count distribution flat or effectively single-valued across the cohort | Threshold in config | Both arms |

**Row 0 is the operative one.** Rows 1–4 catch mechanically broken segmentation — a rule that emits one burst per session, or that merely restates its own dwell parameter. They cannot catch a rule that produces well-behaved statistics that correspond to nothing real on the tape. That judgment is made from chart 07 and it belongs to Cooper. **A pass on rows 1–4 does not constitute acceptance.**

Row 3 deserves particular attention. If small parameter changes reshuffle the burst set, that is the §5.1.1 "foundation is sand" condition arriving several phases ahead of Phase 16, and it needs to be on the record loudly rather than noted in passing.

**If any of rows 1–4 fire:** hard stop, commit, post the observed values and the relevant charts. **Do not** adjust parameters to make the criterion pass. **Do not** introduce offline changepoint detection on your own initiative — it is authorized only as a challenger method, only by a numbered amendment, and only after a pre-registered failure is on the record.

---

## Escalation criteria

Operational hard stops. Commit current state, post, await instruction.

| # | Condition | Threshold | Action |
|---|---|---|---|
| 1 | Tag `phase-9-approved` absent | any | Hard stop at T0a |
| 2 | Cohort manifest join to `momentum_events_canonical` with `in_scope = TRUE` | any shortfall | Hard stop — post the join detail |
| 3 | Read of a D4-quarantined spine numeric on any computation path | > 0 | Hard stop — post file and line |
| 4 | Any full-table pass over `filtered_trades` or `filtered_quotes` | any | Hard stop — post the query plan before running it |
| 5 | Runtime ceiling breached, either arm | per config | Hard stop — post per-event and aggregate timings. Do not silently reduce the cohort |
| 6 | Any per-event chart set exceeding the config cap | any | Hard stop before writing |
| 7 | Write outside `prompts/`, `config/`, `research/phase_10/`, `results/phase_10/` | any | Hard stop |
| 8 | Any inter-trade interval distribution produced as a reported finding rather than a diagnostic axis | any | Hard stop — this is Phase 13's deliverable |
| 9 | Any output described as a detector, entry signal, operating point, or latency budget | any | Hard stop before posting |
| 10 | Any arm, parameter set, or burst definition selected, recommended, or described as preferable | any | Hard stop — the selection is Cooper's |
| 11 | Offline changepoint detection or Hawkes-intensity methods run without a numbered amendment | any | Hard stop |

---

## Chart contract

| # | File | Question | Encoding | n shown | Looks like this if wrong |
|---|---|---|---|---|---|
| 01 | `charts/01_burst_count.html` | How many bursts does a session contain? | Distribution of per-event burst count, one panel per arm, row-cap and sidecar populations as separate overlaid series | n per arm, per carried population | All mass at 1 (failure row 1) or a single spike at one value (failure row 4) |
| 02 | `charts/02_burst_duration.html` | How long does a burst last? | Distribution of burst duration, log x, one series per arm, minimum dwell floor drawn as a vertical rule | n bursts and n events per arm | Mass piled against the dwell rule (failure row 2) |
| 03 | `charts/03_burst_spacing.html` | How far apart are consecutive bursts? | Distribution of inter-burst spacing, log x, per arm; single-burst events reported as a count in the caption, not silently dropped | n per arm, single-burst count in caption | Spacing distribution indistinguishable from the merge-gap tolerance — the parameter is generating the answer |
| 04 | `charts/04_burst_move_share.html` | How much of the session move does a burst carry? | Distribution of per-burst share of session move, per arm; ordered-by-rank panel showing share carried by the largest, second, third burst | n per arm, undefined-denominator count in caption | Shares uniformly small — bursts aren't where the move happens, which contradicts the premise this phase is built on |
| 05 | `charts/05_arm_agreement.html` | Where do the two arms agree? | Per-event overlap measure between Arm A and Arm B, distributed; scatter of Arm A burst count against Arm B burst count with the identity line | n events | Overlap distribution centred near zero — the two arms are measuring different things and neither is established |
| 06 | `charts/06_burst_relative_concentration.html` | How fast is a burst spent, measured from burst start? | Cumulative share of move and of volume against time since burst confirmation; pooled median plus quartile band, per arm; time-to-burst-extreme distribution as a second panel | n bursts per arm, per band | Curves hug the diagonal — no concentration within bursts, so burst-relative anchoring buys nothing over session anchoring |
| 07 | `charts/07_tape_review/` | **Does the segmentation correspond to anything real on the tape?** | **Per selected event, two stacked panels on a shared time axis. Top: individual trade prints, price against time, marker size by share count, detected burst intervals shaded — both arms, visually distinguishable. Bottom: inter-trade time, log scale, same x-axis, with each arm's rate measure and its on/off threshold lines drawn. Burst boundaries marked on both panels.** | Print count and burst count per arm in each event's title | Shaded intervals that don't correspond to visible density changes in the print stream, or that miss obvious clusters |

Chart 07 is the gate. Charts 01–06 are the supporting distributions. Standard chart rules apply — no finding stated without its supporting chart, no statistic without n.

---

## Output files

| File | Description |
|---|---|
| `prompts/phase_10.md`, `config/phase_10.json` | Committed before any run |
| `results/phase_10/artifacts/t0_tick_surface.json` | Cohort print counts, coverage, carried flags |
| `results/phase_10/artifacts/t1_cohort_manifest.parquet` | Committed cohort with stratification and seed |
| `results/phase_10/artifacts/t2_bursts_arm_a.parquet` | Arm A burst intervals (gitignored, regenerable) |
| `results/phase_10/artifacts/t3_bursts_arm_b.parquet` | Arm B burst intervals (gitignored, regenerable) |
| `results/phase_10/artifacts/t4_burst_measurements.json` | Count, duration, spacing, move-share, concentration — per arm, with n |
| `results/phase_10/artifacts/t5_sensitivity.json` | Overlap under perturbation, cross-arm agreement, failure-criteria table |
| `results/phase_10/charts/01–06*.html` | Kaleido-verified |
| `results/phase_10/charts/07_tape_review/` | Per-event review set plus sortable index (gitignored per §12) |
| `results/phase_10/digest.json`, `REPORT.md` | Per §11 |

---

## Reporting

On completion, post:

1. Tick surface table — cohort print counts, coverage, carried flags, with n
2. Cohort table — composition, stratification, join result, sidecar broken out
3. Burst count / duration / spacing tables — per arm, with n, quartiles, carried populations as own rows
4. Move-share table — per arm, including undefined-denominator count
5. Burst-relative concentration table — with the time-to-burst-extreme quartiles
6. Cross-arm agreement table
7. **Pre-registered failure criteria table — rows 1–4, observed against threshold, pass/fail, and nothing further**
8. Escalation check table — all 11 rows, observed, pass/fail
9. Verification block per §10 — every headline number with source, n, and reproduce command
10. Output file table with status
11. Commit list

Every claim cites its chart. **No recommendations. No arm selected. No latency budget proposed. No result characterized as good, promising, weak, or disappointing.** The agent describes the picture.

---

## Approval gate

Do not tag, do not merge, and do not begin Phase 11 scoping until Cooper has reviewed the charts and given explicit approval. On approval, tag `phase-10-approved`.

**Chart 07 is the gate.** Chart 06 sets the burst-relative latency budget. Both reads are Cooper's, not the agent's.
