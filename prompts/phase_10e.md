# Phase 10e — Does the path pay? Forward excursion, and the ceiling on timing detection

**Type:** measurement phase. Two arms. **Arm 1 gates Arm 2.**
**Closes:** the 10-series. Phases 10, 10b, 10c, 10d and the scale-space arc asked whether a burst is
definable as an object. This asks whether any of it predicts price. It is the last act of that saga.
**Branch:** `phase/10e`, cut from `master`.
**Standard:** `docs/Agent_Prompt_Standard.md` §§7–12 apply in full.

> **Landing corrections, 2026-08-30** — factual only, no threshold filled. (1) The branch base was
> `main`; there is no `main` in this repo (`origin/HEAD -> origin/master`), so it reads `master`
> throughout. (2) `config.frozen_inputs.scale_field_module` pointed at `research/scale_space/scale_field.py`,
> which does not exist and neither does that directory; corrected to `research/scale_field/scale_field.py`.
> (3) Flagged but **not** changed, because they are Cooper's: `arm2_max_events = 75` against a causal
> cohort of 78 (fires row 5, which also forbids silently reducing the cohort), and the two different
> D7 anchor artifacts named in the config's `_corrections_on_landing` block.

---

## Context — read before writing any code

**The programme has never measured capture on the intraday path.** Phase 8's markouts are anchored at
detection and at session scale, which D5 reads as archive. Phase 11's capture denominator was a
fixed-horizon 30-minute hold, which `model_selection_session_notes` §8 had already retired — *"nobody
holds to the close. The path is the resource."* Every remaining phase in the plan assumes an answer to
the question this phase asks.

**The unit of analysis is the candidate entry, not the event.** Entries occur repeatedly along one
event's path. Anchoring only at detection measures a single draw from a distribution that is meant to be
sampled many times. Consequences, all binding on this phase: clustering is by event, never by time;
one long, heavily sampled event must not dominate a pooled statistic; and every reported statistic
carries an effective n as well as a raw n.

**The cost unit comes from Phase 11 and is not re-derived here.** Round-trip cost is **70.98 bp /
2.512 cents**, RTH, 5-minute latency (`results/reports/phase_11_report.md`). Barriers in this phase are
expressed as multiples of it. Read it from config; do not recompute it.

**Why the kill condition is a share.** Phase 11's row-11 threshold was a median ratio. It did not fire
at 0.1608 against 0.50 — but realized capture was **non-positive on 52.86%** of the cell and the median
was computed on the 31.9% where the ratio existed at all. A median ratio cannot see a denominator that
does not exist. **No quantity whose denominator can go non-positive carries a gate in this phase.**
Every gate is a share, defined on every candidate entry.

**Arm 2 is deliberately non-causal and that is the point.** It runs the offline detector with full
lookahead to establish a ceiling. Non-causality only helps the oracle, so a null is decisive in a way a
null on a causal detector would not be. **No output of Arm 2 may be described as a detector, an entry
signal, or an operating point.** Same relationship Phase 10's offline segmentation had to Phase 17.

---

## Constraints

- **D4 stands.** Every computed quantity is tick- or bar-derived from D4-clean sources. No spine numeric
  column enters any computation. `momentum_pct` is permitted for stratification only.
- **D18 stands.** All three detection segments are computed and reported. **The gate rests on the RTH
  cell alone.**
- **D19 stands.** Every price, cost and excursion quantity is reported in **both basis points and
  cents**. Neither unit alone, ever.
- **D21 and D13 stand.** No burst object, no burst timescale, no burst-vs-quiet split appears anywhere in
  this phase. If a task appears to need one, stop and post.
- **Pass budget.** Arm 1: **zero** passes over `filtered_trades` or `filtered_quotes`. Arm 2: targeted
  per-event folder reads only, cohort capped in config; the equivalence licensing this was proven in
  Phase 10 v1 T0d.
- **Flag, never delete.** Any candidate entry or event failing a coverage or definedness condition is
  carried with a label and reported as its own row. Never pooled, never dropped.
- **Every tunable lives in `config/phase_10e.json`.** No magic numbers in code. Where this prompt does
  not pin a value, propose one, record it in `decisions_log`, and make it a config key.
- Working directory: repo root. Standing constraints in `CLAUDE.md`.

---

## Pre-registered reading rules

**These are written before the run and are not negotiable after it.** They exist because Phase 11's
denominator degenerated on the majority of its population and the gate could not see it.

| # | Condition | Required handling |
|---|---|---|
| **R1** | **Intra-bar ordering is unknown.** A minute bar's high and low have no order, so first-passage on bars is ambiguous whenever both barriers sit inside one bar's range. | Compute **both bounds** — `optimistic` (favourable extreme first in every bar) and `pessimistic` (adverse extreme first). **Never report a single first-passage number from Arm 1.** Report the **ambiguous share** = entries where the two bounds disagree on outcome. |
| **R2** | Entries where neither barrier is touched before expiry. | Reported as their own outcome class. The three classes (profit / stop / expiry) sum to 1 on every cell. **A "win rate" computed on touched-only entries is a banned output.** |
| **R3** | Entries with no fill — no print in the fill bar. | Own row, own share. Never silently dropped, never forward-filled. |
| **R4** | Entries whose MFE and MAE are both below the smallest barrier at every horizon (a dead tape). | Own share, reported per cell. This is a real outcome, not missing data. |
| **R5** | A pooled statistic dominated by few events. | Every pooled cell reports raw n, distinct events, and **effective n** under event-equal weighting. Cells where one event contributes > `config.max_event_share` are flagged on the chart. |
| **R6** | `p_clear` compared against break-even. | Break-even is arithmetic, not a choice: for a profit barrier at `k`× and a stop at `m`× round-trip cost, with one round trip charged, `p_breakeven = (m+1)/(k+m)`. **Compute and report it per cell alongside `p_clear`.** Do not assume 0.5. |
| **R7** | Any cell with n < `config.min_cell_n`. | Hatched on every chart, carries no claim, appears in no summary sentence. |

---

## Tasks

### T0 — State, branch, config, preconditions

**Commit nothing in T0a; it is read-only. Do not begin T1 until T0 is committed and posted.**

- [ ] **T0a — Observe state, assert nothing.** Report from `git` and the filesystem, not from this
      prompt: current branch; whether `phase-11-approved` exists and where; whether the working tree is
      clean; the `status` field of `results/phase_11/digest.json`; whether `event_minute_bars_v2` exists
      and its row count; which of the frozen artifacts named in T1a are present. **Post the table before
      anything else.**
- [ ] **T0b — Branch and prompt.** Cut `phase/10e` from `master`. Commit `prompts/phase_10e.md` as the
      first commit on the branch.
- [ ] **T0c — Config.** Author and commit `config/phase_10e.json` before any run. Every `[Cooper]` slot
      must be filled in the committed file or T1 hard-stops (row 2).
- [ ] **T0d — Satisfiability audit.** For every escalation row: (i) is the quantity computed by some
      task, (ii) is its threshold reachable in both directions, (iii) does any other row make it
      unreachable, (iv) is its scope unambiguous. **This audit exists because two of 10b's three
      amendments introduced an unreachable required outcome.** Post the table. Hard stop on any failure.
- [ ] T0e — Commit.

### ARM 1 — The excursion base rate *(zero tick passes)*

- [ ] **T1 — Candidate entry universe**
  - [ ] T1a — Build the candidate-entry table from `event_minute_bars_v2`, D1 universe, T=0 session.
        Reuse **frozen**: `det_anchor` from `results/phase_8/artifacts/a102_detection_anchors.parquet`
        (D7); `pq_rth_open` from `results/phase_8/artifacts/t3_participation.parquet` (**not** the
        anchors file — Phase 11 A1-7); the Phase 9 flags. **Do not re-derive any of them.**
  - [ ] T1b — One candidate entry per minute bar at or after `det_anchor`, per event. Carry:
        `minutes_since_anchor`, `n_prints`, `pq_rth_open`, `det_segment`, `era`, and every Phase 9 flag.
  - [ ] T1c — **Per-minute λ̂ and `s_min = 2.26/λ̂`** from the bar's print count. This is the scale-space
        arc's one surviving criterion and it enters here as a stratifier. **No field is computed** — only
        the floor. Carry `s_min_minute` on every candidate entry.
  - [ ] T1d — **Two entry denominators, both carried, never blended:**
        **(i) print-weighted** — every bar with `n_prints ≥ 1`. What is actually enterable.
        **(ii) event-equalised** — a seeded uniform subsample of `config.entries_per_event` bars per
        event, equal weight per event. Removes long-event dominance (R5).
  - [ ] T1e — Filter waterfall: rows in and out of every step, with the reason. Commit.

- [ ] **T2 — Fill, excursion, and the two bounds**
  - [ ] T2a — Fill price = `first_price` of bar `t + L`, for L ∈ `config.latency_minutes`. **Latency 0
        is a physical impossibility and is labelled the upper bound on every chart and table** (D7).
        **Arm 1's latency axis is coarser than achievable execution and therefore pessimistic** — state
        this in the report; Arm 2 carries the second-scale axis.
  - [ ] T2b — **MFE** = max `high` and **MAE** = min `low` over bars `[fill, fill + H]` for
        H ∈ `config.horizons_minutes`, relative to fill price. In **bp and cents** (D19) and in
        **multiples of round-trip cost**.
  - [ ] T2c — First-passage outcome under barriers `k`× profit / `m`× stop / expiry at H, over
        `config.barrier_grid`. **Compute both R1 bounds. Report the ambiguous share per cell.**
  - [ ] T2d — Apply R2, R3, R4 exactly as written. Three-class outcome shares sum to 1 per cell. Commit.

- [ ] **T3 — Distribution, stratification, and inference**
  - [ ] T3a — MFE and MAE **full distributions** per cell, never the median alone. Cells:
        latency × horizon × `det_segment` × `pq_rth_open` × era.
  - [ ] T3b — Stratify additionally by `minutes_since_anchor` band and by `s_min_minute` band. The
        second is where the surviving 10-series result enters: **does the tape's resolvability at a
        moment relate to what the path pays from that moment?**
  - [ ] T3c — **Event-clustered and ticker-clustered bootstrap CIs** on every headline share, seed and
        reps from config, following Phase 9's ticker-block construction.
  - [ ] T3d — `p_clear` and `p_breakeven` per cell per R6, both bounds per R1, with CIs. Commit.

- [ ] **T4 — THE ARM 1 GATE.** Post the gate table and **stop**. Do not begin Arm 2.
  - [ ] T4a — Report the three gate quantities on the named cell (`config.named_cell`): the R1
        **ambiguous share**; `p_clear` (both bounds) against `p_breakeven`; and the expiry share.
  - [ ] T4b — Report the same for every cell, so the named cell is visible as one point in a grid and
        not as a cherry-pick.
  - [ ] T4c — **Cooper reads charts 01–04 and decides.** Escalation rows 10, 11 and 12 are evaluated
        here. Arm 2 is unauthorised until Cooper says so in writing.
  - [ ] T4d — Commit. Post. Stop.

### ARM 2 — The oracle ceiling *(only after the T4 gate; targeted tick reads)*

- [ ] **T5 — Cohort and signal**
  - [ ] T5a — Cohort: the scale-space admissible set at the anchor +60 s window
        (`config.arm2_cohort`), capped at `config.arm2_max_events`. `collapse_same_timestamp` applies
        and is a precondition, not a detail.
  - [ ] T5b — **Three channels, not one. AMENDED 2026-08-30 under D23 — see the note below.**
        (i) **LEVEL centred** — `λ̂(t,s)` above its own trailing q90 at `s = 2·s_min(t)`, full lookahead.
        This is the **oracle ceiling** arm and is what the original prompt specified.
        (ii) **LEVEL causal** and (iii) **FIELD causal** — one-sided kernel, at `s = 2·s_min_causal(t)`
        where **`s_min_causal = 4.51/λ̂`, twice the centred floor.** These are the arms D23 opened.
        **The divergence `D` remains closed** — it fired its kill condition again under the causal kernel
        (3 and 2 onsets over 78 events). Do not build it.
        Reuse `research/scale_field/scale_field.py` unchanged; do not fork it. The causal path is
        `field_onesided()`; the causal floor is `s_min_onesided()` / `s_min_for_rate(kernel="onesided")`.
  - [ ] T5b-i — **Every channel's threshold is null-rate matched before any onset is compared.** Measure
        each channel's false-onset rate on matched null tape and set thresholds so all three fire at the
        same rate on burst-free tape. **An onset is a first-passage event and first passage of a noisier
        series occurs earlier for reasons that carry no information.** D22 measured FIELD firing at 2.8×
        the LEVEL rate; until that is equalised, "FIELD leads" and "FIELD is noisier" are not separable.
        Escalation row 23.

> **Amendment note, 2026-08-30.** The original T5b said *"LEVEL only — do not build the field
> derivative"* on the basis of D22. **D23 reversed that in part:** under a one-sided kernel the ordering
> flips, FIELD leading LEVEL by +1.515 kernel widths (+1.180 s) on 19/19 events, paired within event,
> Wilcoxon p = 1.9e−05. D22's saturation fact is untouched and `s_min` is untouched. **The instruction to
> skip the field is withdrawn; the instruction to skip `D` stands.**
>
> **Two limits D23 carries into T5b-i, both material here.** The lead rests on **19 of 100** cohort
> events — the two booleans are temporally segregated on most, matched share 20.0% against a 65.1%
> circular-shift null. And under a causal kernel `dL/dln s` weights recent lags while `λ̂` averages the
> whole half-kernel, centroid `0.80·s`, so **a shorter level kernel may buy the same lead**; the measured
> +1.52 is roughly twice the 0.80 centroid gap, which is suggestive but not separating. T5b-i is the
> test that separates them and it is the reason row 23 exists.

  - [ ] T5c — **Matched control:** random entries inside the same events, stratified on
        `seconds_since_anchor` so the control shares the oracle's position-in-path distribution.
        Intraday drift is real and large; an unmatched control would measure it. `config.control_draws`
        draws, seeded.
  - [ ] T5d — Commit.

- [ ] **T6 — Second-scale excursion**
  - [ ] T6a — Fill at `t + L` for L ∈ `config.latency_seconds`. **This is the real latency axis.**
  - [ ] T6b — MFE / MAE from tick prices over H ∈ `config.horizons_seconds`. **Tick data resolves the R1
        ordering ambiguity** — report first-passage as a single number here and say plainly that this is
        what Arm 1 could not do.
  - [ ] T6c — Same barrier grid, same `p_clear` / `p_breakeven` construction, same three-class shares.
  - [ ] T6d — Commit.

- [ ] **T7 — THE CEILING.** `p_clear(oracle) − p_clear(control)`, per cell, with event-clustered CIs.
      Report the full grid; the best cell is reported **with the grid around it**, never alone.
      Escalation row 13 is evaluated here. Commit.

### T8 — Charts, digest, report

- [ ] T8a — Every chart in the Chart Contract, kaleido-verified.
- [ ] T8b — `results/phase_10e/digest.json` per §11; `REPORT.md` per §10; cross-phase copy to
      `results/reports/phase_10e_report.md`.
- [ ] T8c — Verification block: every headline number with source, n, effective n, and repro command.
      Filter waterfall in full. Commit; `git status` clean.

---

## Escalation Criteria

Stop, commit current state, post observed values and charts, await instruction. **Do not attempt a fix.
Do not adjust a parameter to make a criterion pass. Table order is priority order.**

| # | Condition | Threshold | Action |
|---|---|---|---|
| 1 | `phase-11-approved` absent, or `master` moved since it | any | Hard stop at T0a — post tag/SHA state, do not proceed on assumption |
| 2 | Any `[Cooper]` config slot unfilled at T0c | any | Hard stop — the agent fills none of them |
| 3 | T0d satisfiability audit fails any check | any | Hard stop |
| 4 | Any pass over `filtered_trades` / `filtered_quotes` in Arm 1 | any (> 0) | Hard stop |
| 5 | Arm 2 tick reads exceed `config.arm2_max_events` | any | Hard stop — do not silently reduce the cohort either |
| 6 | Spine numeric column on a computation path | any (> 0) | Hard stop |
| 7 | `event_minute_bars_v2` row count ≠ 45,925,350 | any | Hard stop |
| 8 | A first-passage number reported from Arm 1 without both R1 bounds | any | Hard stop before posting |
| 9 | A win rate reported on touched-only entries (R2 violation) | any | Hard stop before posting |
| 10 | **R1 ambiguous share on the named cell** | `[Cooper]` — proposed **> 25%** | Hard stop at T4 — Arm 1 cannot carry a first-passage conclusion; MFE/MAE distributions stand, the label must come from Arm 2 |
| 11 | **No-fill share (R3) on the named cell** | `[Cooper]` — proposed **> 10%** | Hard stop at T4 — post the distribution by segment |
| 12 | **THE ARM 1 GATE.** `p_clear` on the named cell, **pessimistic bound**, against `p_breakeven` | `[Cooper]` — proposed: pessimistic `p_clear` below `p_breakeven` at **every** cell in the grid | Hard stop — **the path does not pay at minute scale. Post and stop. Do not run Arm 2.** |
| 13 | **THE CEILING.** `p_clear(oracle) − p_clear(control)`, best cell, lower bound of the event-clustered CI | `[Cooper]` — proposed **≤ 0** | Hard stop — **an oracle with lookahead does not beat random entry inside the same event. The timing-detector line closes.** |
| 14 | Any cell where one event contributes more than `config.max_event_share` presented without a flag | any | Hard stop before posting |
| 15 | Any cell with n < `config.min_cell_n` presented unhatched or carrying a claim | any | Hard stop before posting |
| 16 | Any quantity reported in one unit alone (D19) | any | Hard stop before posting |
| 17 | Any burst object, burst duration, burst timescale, or burst/quiet split appears in code or output | any | Hard stop — D13, D21 |
| 18 | Any output of Arm 2 described as a detector, entry signal, or operating point | any | Hard stop |
| 19 | Runtime exceeds `config.runtime_ceilings.runtime_ceiling_seconds_arm1` or `..._arm2` on its arm | any | Hard stop — do not reduce the cohort or the grid to fit |
| 20 | Write outside `results/phase_10e/`, `prompts/`, `config/`, `research/phase_10e/` | any | Hard stop — post intended path |
| 21 | Agent states a recommendation, or characterises a result as good / weak / promising / disappointing | any | Report sent back |
| 22 | A decision appended to `docs/Universe-Decisions.md` at a number not confirmed free by reading the file | any | Hard stop — the pointer list has been stale before and caused a near-collision at D20, and again at D23 on 2026-08-30 |
| 23 | Any onset compared across channels before T5b-i null-rate matching | any | Hard stop — the lead and the noise are not separable until the channels fire at equal rates on null tape |
| 24 | A causal kernel run against the **centred** floor `2.26/λ` | any | Hard stop — a one-sided kernel keeps half the mass, so `n_eff = √π·s·λ` and the causal floor is `4.51/λ`. Using `2.26/λ` puts every read at `n_eff = 4.00`, exactly half the target |

---

## Chart Contract

Standard chart rules apply (§9): Plotly, standalone HTML, one per file, n per bucket always,
distribution not centre, raw overlay where point count permits, log axes where multiplicative, outliers
shown never clipped, caption states sample + filters + config hash.

| # | File | Question | Encoding | n shown | Looks like this if wrong |
|---|---|---|---|---|---|
| 01 | `charts/01_excursion_distribution.html` | What does the path offer from an arbitrary entry? | ECDF of MFE and MAE (twin bp/cents axes), one line per horizon; facet by latency × segment; vertical rules at 1× and 1.5× round-trip cost | n and effective n per line | Both ECDFs crossing the 1× cost rule at nearly the same quantile — favourable and adverse excursion are symmetric and the path offers nothing a cost can be paid out of |
| 02 | `charts/02_outcome_shares.html` | How do entries actually end? | Stacked share of profit / stop / expiry, both R1 bounds side by side; x = barrier cell; facet by latency × horizon; `p_breakeven` drawn as a rule per cell | Per-bar n | Profit share below `p_breakeven` in every cell under both bounds — nothing in the grid clears its own arithmetic |
| 03 | `charts/03_ambiguity.html` | Can minute bars answer the first-passage question at all? | Ambiguous share (R1) as a heatmap over barrier × horizon; facet by latency | Per-cell n | Ambiguous share above the row-10 threshold across the grid — the bar basis cannot resolve ordering and Arm 1 is a distribution result only |
| 04 | `charts/04_path_position.html` | Does where you are on the path matter? | x = `minutes_since_anchor` band, y = `p_clear` (both bounds); ribbon = clustered CI; facet by segment × era | Per-band n and distinct events | Flat across every band — position on the path carries no information and the detection anchor is not special |
| 05 | `charts/05_smin_stratification.html` | Does the tape's resolvability relate to what the path pays? | x = `s_min_minute` band (log), y = `p_clear` and median MFE; violin + strip; RTH only | Per-band n | Flat — the one surviving 10-series criterion has no relationship to forward excursion, and `s_min` is an estimability gate only |
| 06 | `charts/06_oracle_vs_control.html` | **(Arm 2)** Does a detector with lookahead beat random entry? | ECDF of MFE, oracle vs. matched control, one pair per latency; facet by horizon; clustered CI band on the difference | n per line, distinct events | The two ECDFs superimposed — with full lookahead the detector selects moments no better than chance inside the same event |
| 07 | `charts/07_ceiling_grid.html` | **(Arm 2)** Where, if anywhere, does the ceiling clear? | Heatmap: rows = horizon, cols = latency; colour = `p_clear(oracle) − p_clear(control)`; cells n < min hatched; CI-straddles-zero cells ringed | Per-cell n printed | Uniform colour near zero — no latency or horizon choice separates, and the ceiling is flat |

---

## Output Files

| File | Description | Status |
|---|---|---|
| `prompts/phase_10e.md` | This prompt, committed before any work | [ ] |
| `config/phase_10e.json` | Every tunable; committed before any run | [ ] |
| `results/phase_10e/artifacts/t0d_satisfiability_audit.json` | All rows, four checks each | [ ] |
| `results/phase_10e/artifacts/t1_candidate_entries.parquet` | Entry table, both denominators, flags, `s_min_minute` | [ ] |
| `results/phase_10e/artifacts/t2_excursion.parquet` | MFE/MAE and both R1 first-passage bounds per entry × cell | [ ] |
| `results/phase_10e/artifacts/t3_shares.{parquet,json}` | `p_clear`, `p_breakeven`, three-class shares, CIs, effective n | [ ] |
| `results/phase_10e/artifacts/t4_gate.json` | The three gate quantities, named cell and full grid | [ ] |
| `results/phase_10e/artifacts/t5_oracle_entries.parquet` | Arm 2 onsets and matched control draws | [ ] |
| `results/phase_10e/artifacts/t7_ceiling.{parquet,json}` | Oracle − control, per cell, with CIs | [ ] |
| `results/phase_10e/charts/01–07*.html` (+ `.png`) | Per Chart Contract, kaleido-verified | [ ] |
| `results/phase_10e/{digest.json, REPORT.md}` | Per §10 / §11 | [ ] |
| `results/reports/phase_10e_report.md` | Cross-phase copy (standing rule) | [ ] |
| `docs/Open-Items-Register.md` | Any new open item, appended | [ ] |
| `docs/Research-Library-Map.md` | Phase 10e prompts, configs, artifacts, charts | [ ] |

Parquet artifacts are gitignored and regenerable per §12; JSON summaries, digest, report and charts are
committed.

---

## Reporting

On completion, post, in this order:

1. T0a state table — **observed, not asserted**
2. T0d satisfiability audit — all rows, four checks each
3. Filter waterfall — D1 universe → candidate entries → per-cell n, with reasons
4. R1–R7 reading-rule table with the observed value of each
5. Arm 1 outcome-share table — three classes, both bounds, `p_clear` against `p_breakeven`, per cell, with n and effective n
6. **The T4 gate table — the three gate quantities, named cell and full grid**
7. *(Arm 1 stops here at the T4 gate.)*
8. Arm 2 cohort and control-matching table
9. **The ceiling table — oracle − control, per cell, with clustered CIs**
10. Escalation check table — all 24 rows, observed against threshold, pass / fail
11. Verification block per §10 — every headline number with source, n, effective n, repro command
12. Output file table with status
13. Commit list

Every claim cites its chart. Every table carries n per row. **No recommendations. No operating point
proposed. No result characterised as good, promising, weak or disappointing.** The agent describes the
picture; the read is Cooper's.

---

## Approval Gate

**Two gates.**

**T4 is a hard gate inside the phase.** Arm 2 does not begin until Cooper has reviewed charts 01–04 and
either cleared row 12 or overruled it in writing. Nothing in Arm 2 is authorised before that.

**Do not tag, do not merge, and do not begin any follow-on scoping until Cooper has reviewed charts
05–07 and given explicit approval.** On approval, tag `phase-10e-approved` and fast-forward `master`.

**Chart 02 is the Arm 1 gate. Chart 06 is the Arm 2 gate. Chart 03 decides whether chart 02 can carry a
conclusion at all.** All three reads are Cooper's, not the agent's.
