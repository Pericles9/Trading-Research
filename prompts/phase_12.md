# Phase 12 — Halts & LULD

**Type:** measurement phase. Two stages. **Stage A is a feasibility gate.**
**Produces:** P(halt | state); time-to-halt; reopen gap distribution, long-side conditional.
**Gate:** the sizing constraint is a number — or its unavailability is a recorded finding.
**Branch:** `phase/12`, cut from `master`. **Runs in parallel with Phase 10e** — different data path,
no shared artifact, no dependency in either direction.
**Standard:** `docs/Agent_Prompt_Standard.md` §§7–12 apply in full.

> **Landing correction, 2026-08-30** — the branch base read `main`; there is no `main` in this repo
> (`origin/HEAD -> origin/master`), so it reads `master` throughout. **Nothing else was changed.** Every
> `[Cooper]` slot, including the entire LULD band table, is exactly as handed over, and escalation
> row 2 therefore hard-stops this phase at T0c until Cooper fills them.

---

## Context

`docs/Mom-DB-Strategy-Research-Program.md` §4.2 condition 2 states the thesis this phase tests:
**halts are the tail risk, not volatility.** The strategy-ending scenario is trapped-in-halt with an
adverse reopen, not a fast market. That makes halt risk a first-class model input and position sizing
constrained to survive the worst plausible reopen, not the average one.

**None of it has been measured.** Risk-register row 6 has been open since the programme began.

**Stage A exists because halt identification may not be possible from this archive.** Phase 11 found the
`indicators` field populated on 88.85% of source rows, 99.77% carrying a single code, and **no dictionary
on disk** — available and uninterpretable. If `conditions` is in the same state and the tape-gap and
band-arithmetic routes do not corroborate each other, **the honest deliverable of this phase is that
halts cannot be identified from what is on disk**, which is a first-order finding for the sizing question
and for any backtest that claims to model forced holds.

**The environment is offline (D14).** There is no package index, no network fetch, and no way to retrieve
the LULD plan or a reference implementation. **Every LULD band parameter therefore comes from
`config/phase_12.json`, supplied by Cooper.** The agent does not infer band widths, tier assignments, or
doubling windows from memory, from data, or from any source it cannot cite to a committed file. This is
the same failure that blocked 10b's global envelope test; it is anticipated here rather than discovered.

---

## Constraints

- **D4 stands.** Tick- and bar-derived only. No spine numeric column on a computation path.
- **D19 stands.** Every price quantity in **both basis points and cents**.
- **D2 is relevant, not decisive.** `clean_window`-flagged events with the `0001000` pattern were noted
  as *"disproportionately consistent with halt/delisting outcomes."* That is a prior, not evidence.
  **Do not use it to label halts.** It may be used as a stratifier and as a corroboration check.
- **Flag, never delete.** Every candidate halt that fails corroboration is carried and reported.
- **No route is privileged by assumption.** The three identification routes in T2 are reported
  independently and their agreement is measured, not assumed.
- Every tunable lives in `config/phase_12.json`. Working directory: repo root.

---

## Tasks

### T0 — State, branch, config, preconditions

- [ ] **T0a — Observe state, assert nothing.** Report from `git` and the filesystem: current branch;
      tag state; working tree clean; presence of the frozen artifacts named in T1; whether
      `conditions` and `indicators` columns exist in the source parquet and their null shares.
      **Read-only. Commit nothing. Post the table first.**
- [ ] **T0b** — Cut `phase/12` from `master`. Commit `prompts/phase_12.md` as the first commit.
- [ ] **T0c** — Commit `config/phase_12.json` before any run. **Hard stop if the LULD band table or any
      `[Cooper]` slot is unfilled** (row 2).
- [ ] **T0d** — Satisfiability audit over every escalation row, four checks each. Post. Hard stop on
      any failure.

### STAGE A — Can halts be identified at all?

- [ ] **T1 — Candidate halt census, route 1: tape gaps**
  - [ ] T1a — Per event, per session, enumerate gaps in `sip_timestamp` on the T=0 RTH segment of length
        ≥ `config.gap_threshold_seconds` with prints resuming afterwards. Carry gap start, end, duration,
        last price before, first price after.
  - [ ] T1b — **Report the gap-duration distribution before applying any threshold.** A halt has a
        characteristic minimum duration; a thin tape produces long gaps for ordinary reasons. If the
        distribution is smooth with no mass near the expected pause length, route 1 does not identify
        halts and says so. Chart 01.
  - [ ] T1c — Commit.

- [ ] **T2 — Routes 2 and 3, and their agreement**
  - [ ] T2a — **Route 2, condition codes.** Full census of `conditions` and `indicators` values on prints
        adjacent to every route-1 candidate, and on a matched sample of non-candidates. **Report the
        census. Do not infer the meaning of any code from its distribution** — that is banned, exactly as
        it was in Phase 11 row 22. A code is usable only if a dictionary exists in a committed file.
  - [ ] T2b — **Route 3, band arithmetic.** Using the band table in config only, compute the LULD
        reference price and band edges through the session and flag every moment the tape reached a band
        edge. Carry tier, price bracket, and whether a doubling window applied. **Every parameter cites
        its config key.**
  - [ ] T2c — **Agreement matrix.** Three routes × candidates: pairwise agreement, three-way agreement,
        and the share of candidates identified by exactly one route. Chart 02.
  - [ ] T2d — Commit.

- [ ] **T3 — THE STAGE A GATE.** Post and **stop**.
  - [ ] T3a — Report the corroborated-halt count and share against the detection universe, and the
        single-route-only share.
  - [ ] T3b — Escalation rows 10 and 11 are evaluated here. **Stage B is unauthorised until Cooper
        clears them in writing.**
  - [ ] T3c — If the gate fires, write the phase as a **feasibility finding**: halts are not identifiable
        from this archive, with the three routes' evidence, and record what data would be needed.
        **That is a complete and reportable phase outcome, not a failure.**
  - [ ] T3d — Commit. Post. Stop.

### STAGE B — The measurements *(only after the T3 gate)*

- [ ] **T4 — Time to halt, and P(halt | state)**
  - [ ] T4a — Distribution of time from `det_anchor` to first corroborated halt, per segment, with the
        censored population (events with no halt) reported as its own share. **This is survival data;
        events that never halt are censored observations, not absences.** Chart 03.
  - [ ] T4b — P(halt in the next `config.hazard_windows_minutes` | state), where every state variable is
        **knowable at decision time and lagged by realistic pipeline latency** — `CLAUDE.md` standing
        constraint. Candidate states from config; distance to the band edge is the obvious one and must
        be causal.
  - [ ] T4c — Report as distributions and empirical hazards. **No fitted hazard model, no parametric
        survival family** — that is not this phase. Chart 04.
  - [ ] T4d — Commit.

- [ ] **T5 — The reopen gap — the sizing number**
  - [ ] T5a — Reopen gap = first print after the halt against the last print before, in **bp and cents**
        (D19). Full distribution, never the median alone.
  - [ ] T5b — **Long-side conditional**, per §4.2 condition 2: the distribution of adverse reopen gaps
        for a position held long into the halt. Report the **left tail explicitly** — p01, p05, p10 — and
        the worst observed, with the event named.
  - [ ] T5c — Conditional on pre-halt state: direction of the last leg, time since detection, and
        participation quintile. Cells below `config.min_cell_n` hatched.
  - [ ] T5d — **The sizing constraint, stated as arithmetic and not as advice.** For each of
        `config.ruin_thresholds`, the position size at which the observed p01 adverse reopen produces a
        loss equal to that threshold. **This is a table of arithmetic consequences. The agent proposes
        no position size.** Charts 05, 06.
  - [ ] T5e — Commit.

- [ ] **T6 — Charts, digest, report.** Every chart in the contract, kaleido-verified. `digest.json` per
      §11, `REPORT.md` per §10, cross-phase copy to `results/reports/phase_12_report.md`. Verification
      block with every headline number's source, n, and repro command. Commit; `git status` clean.

---

## Escalation Criteria

Stop, commit, post observed values and charts, await instruction. Table order is priority order.

| # | Condition | Threshold | Action |
|---|---|---|---|
| 1 | Working tree dirty at T0a | any | Hard stop |
| 2 | LULD band table or any `[Cooper]` slot unfilled in the committed config | any | Hard stop at T0c |
| 3 | T0d satisfiability audit fails any check | any | Hard stop |
| 4 | Any LULD parameter used that does not cite a config key | any | Hard stop — no band width, tier, or doubling window from memory or inference |
| 5 | Meaning inferred for any `conditions` / `indicators` code without a dictionary in a committed file | any | Hard stop |
| 6 | Spine numeric column on a computation path | any (> 0) | Hard stop |
| 7 | A state variable used in T4b that is not knowable at decision time | any | Hard stop |
| 8 | A halt labelled from the `clean_window` `0001000` pattern | any | Hard stop — it is a prior, not evidence |
| 9 | Any cell below `config.min_cell_n` presented unhatched or carrying a claim | any | Hard stop before posting |
| 10 | **Corroborated-halt count** (≥ 2 routes agreeing) | `[Cooper]` — proposed **< 50 events** | Hard stop at T3 — **too few to measure a reopen distribution. Write the feasibility finding.** |
| 11 | **Single-route-only share** of candidates | `[Cooper]` — proposed **> 60%** | Hard stop at T3 — **the routes do not corroborate; identification is not established.** |
| 12 | Reopen-gap median reported without the full distribution and the left tail | any | Hard stop before posting |
| 13 | Any quantity reported in one unit alone (D19) | any | Hard stop before posting |
| 14 | A fitted hazard model or parametric survival family produced | any | Hard stop — out of scope |
| 15 | Agent proposes a position size, or characterises a result as good / weak / promising | any | Report sent back |
| 16 | Write outside `results/phase_12/`, `prompts/`, `config/`, `research/phase_12/` | any | Hard stop |
| 17 | Runtime exceeds `config.runtime_ceiling_seconds` | any | Hard stop — do not reduce the cohort to fit |

---

## Chart Contract

| # | File | Question | Encoding | n shown | Looks like this if wrong |
|---|---|---|---|---|---|
| 01 | `charts/01_gap_duration.html` | Do tape gaps carry a halt signature? | ECDF and histogram of RTH gap duration (log s); rule at the config pause length; facet by segment and participation quintile | n per facet | Smooth, featureless distribution with no mass near the pause length — gaps are thin-tape artifacts and route 1 identifies nothing |
| 02 | `charts/02_route_agreement.html` | Do the three identification routes agree? | UpSet-style or three-set bar chart of route intersections; single-route-only bar highlighted | n per set | Almost all mass in single-route-only bars — no corroboration, identification unestablished |
| 03 | `charts/03_time_to_halt.html` | How long does a position sit before halt risk bites? | ECDF of minutes from `det_anchor` to first halt; censored share stated in the caption; facet by segment | n and censored n | ECDF flat across the whole session — halt timing carries no relationship to detection |
| 04 | `charts/04_hazard_by_state.html` | Is halt risk predictable from causal state? | x = state bucket (distance to band edge), y = empirical hazard; violin/strip; facet by window | Per-bucket n | Flat across every state bucket — halt risk is not conditionable and only an unconditional rate is available |
| 05 | `charts/05_reopen_gap.html` | What does a reopen cost a long position? | ECDF of reopen gap, twin bp/cents axes; long-adverse side shaded; p01/p05/p10 rules annotated | n per line | Symmetric around zero with a thin left tail — the reopen is not the tail risk §4.2 assumes and condition 2 is unsupported |
| 06 | `charts/06_sizing_arithmetic.html` | What size survives the observed worst reopen? | x = position size, y = loss at observed p01 reopen; horizontal rules at each `ruin_threshold` | n underlying the p01 | Curve crossing every ruin threshold only at sizes far above any plausible position — halts do not bind sizing on this universe |

---

## Output Files

| File | Description | Status |
|---|---|---|
| `prompts/phase_12.md`, `config/phase_12.json` | Committed before any run | [ ] |
| `results/phase_12/artifacts/t0d_satisfiability_audit.json` | All rows, four checks each | [ ] |
| `results/phase_12/artifacts/t1_gap_census.{parquet,json}` | Route 1 candidates, full duration distribution | [ ] |
| `results/phase_12/artifacts/t2_code_census.json` | `conditions` / `indicators` census, adjacent and matched | [ ] |
| `results/phase_12/artifacts/t2_band_arithmetic.parquet` | Route 3 band edges and touches, every parameter's config key | [ ] |
| `results/phase_12/artifacts/t2_agreement_matrix.json` | Pairwise and three-way route agreement | [ ] |
| `results/phase_12/artifacts/t3_gate.json` | Corroborated count, single-route share, gate outcome | [ ] |
| `results/phase_12/artifacts/t4_hazard.{parquet,json}` | Time-to-halt, censoring, empirical hazards by state | [ ] |
| `results/phase_12/artifacts/t5_reopen.{parquet,json}` | Reopen distribution, long-side conditional, sizing arithmetic | [ ] |
| `results/phase_12/charts/01–06*.html` (+ `.png`) | Per contract, kaleido-verified | [ ] |
| `results/phase_12/{digest.json, REPORT.md}` | Per §10 / §11 | [ ] |
| `results/reports/phase_12_report.md` | Cross-phase copy | [ ] |
| `docs/Open-Items-Register.md` | Code dictionary availability; any data gap found | [ ] |

---

## Reporting

Post, in order: T0a state table (observed) · T0d audit · gap-duration distribution **before** any
threshold · code census · band-arithmetic parameter table with config keys · **route agreement matrix** ·
**the T3 gate table** · *(Stage A stops here)* · time-to-halt with censored share · hazard by state ·
**reopen distribution with left tail explicit** · sizing arithmetic table · escalation check, all 17 rows ·
verification block · output file table · commit list.

Every claim cites its chart. Every table carries n. **No recommendations. No position size proposed. No
result characterised.**

---

## Approval Gate

**T3 is a hard gate inside the phase.** Stage B does not begin until Cooper has reviewed charts 01–02 and
cleared rows 10 and 11 in writing.

**Do not tag or merge until Cooper has reviewed charts 03–06 and given explicit approval.** On approval,
tag `phase-12-approved` and fast-forward `master`.

**Chart 02 is the Stage A gate. Chart 05 is the phase.** Both reads are Cooper's.
