# Phase 10d — Burst Assembly Under a Merge Tolerance and a Run-Length Floor

**Date:** 2026-08-26
**Revision:** r2. Supersedes the r1 draft on the identity cell's `min_prints` value and on
`ok=False` separator handling, both found at T0b. r1 was never committed; this replaces it.
**Branch:** `phase/10d`, cut from **`master`** at **`213bd7c`**
**Baseline:** master HEAD `213bd7c` — two commits ahead of tag `phase-10c-closed` (`89c292b`). There
is no `main` branch and no `phase-10c-approved` tag.
**Supersedes:** the assembly step of `prompts/phase_10_v4.md` as carried into 10c. **Does not
supersede** 10c's window basis, kernels, or threshold-selection rule.
**Spec:** `prompts/phase_10d_spec.md`, and `prompts/phase_10c_closing_note_erratum.md`. Read both.
**Objective:** Assemble sub-bursts under a merge tolerance and a run-length floor rather than as
unfiltered runs of strictly consecutive sub-threshold intervals, and **attribute any change in the
duration distribution between the two mechanisms.**
**Primary success metric:** A sub-burst decomposition Cooper accepts on visual review against the
tape, produced with no post-hoc selected parameter value, reported with its merge tolerance, floor
and separator rule attached to every figure.

**T0 is already complete** — posted with both tables and two discrepancies, which are folded into
this revision. Re-verify T0a's state before T1; T0b's findings are carried below.

---

## 1. Context & Constraints

- **Read the erratum first.** An earlier draft was built from the 10c *outline* rather than the
  committed config and was wrong on four settled points. **If anything here contradicts
  `config/phase_10c.json` or a Stage 1 artifact, the artifact wins — post the discrepancy, do not
  resolve it as a judgment call.** That rule has already caught two defects in this prompt; keep
  applying it.
- **10c is settled background in full. Do not re-derive, grid, or adjust any of it:** the
  **centered** window (`trailing` and `anchored_to_detection` forbidden; the A2.5 density-inversion
  reasoning is not reopened); the **three kernels** with **D5 = 8 min primary**; 10c's **variant
  grid**; the **four segments** — premarket, rth, evening, and the unlabelled population — never
  collapsed to two; the per-interval derived data floor and the cell-level `ok.sum()` minimum, with
  `insufficient_context` carried and never given a fallback; **argmax-void selection across all
  troughs with no cutoff** (`D13_void_parameter.threshold` stays `null` — **do not reinstate 0.70 or
  any cutoff anywhere in the computation path**); histogram, bin grid, and the Poisson-floor
  peak-survival rule.
- **This phase changes one thing: how labelled intervals become burst objects.** If a task appears to
  require changing anything else, stop and post.
- **Two facts from T0b that this revision depends on**, both to be re-verified from the artifact
  rather than trusted from here: **10c applies no run-length floor at any point** — there is no
  `min_prints` variable in `s1_t1_subbursts.py`; and a run is broken **equally** by an interval at or
  above threshold and by one failing the `ok` mask.
- **Numbers in this prompt.** It carries no 10c measurement except where T0b's own report is cited,
  and those are marked. **Read every population count, duration figure and prior-version statistic
  from its committed artifact** — do not transcribe from this prompt or the spec, and check
  attribution before it goes in a table.
- **D15 is drafted, not recorded.** Appended at T1c after Cooper confirms spec §8. Until then D9
  governs unamended. Do not paraphrase it.
- **D14 — offline.** numpy 2.4.2, scipy 1.17.0, plotly 6.5.2, pyarrow 23.0.0, pandas 2.3.3 confirmed
  present at T0c. The assembly needs no new dependency. Attempt no install.
- **No real event is read until T2's control gate passes.**
- **Cohort and cell structure frozen.** Assert the hash.
- **D4 stands.** All quantities tick-derived; no spine numeric on any computation path.
- **Pass budget over `filtered_trades` / `filtered_quotes` is zero.** Any full-table plan is
  **standing escalation row 4**.
- **Phase 13 boundary.** Intervals are the operating variable; this phase produces no interval
  distribution as a characterized finding, no noise floor, no regime definitions.
- **Causal status unchanged.** 10c retired zero non-causal fields — the window stayed centered.
  **Claim no retirement.** The debt stays parked for Phase 17.
- **Offline, and nothing here is a detector.**
- **Every tunable in `config/phase_10d.json`.** No magic numbers in code.
- **Write scope, escalation row 13 as amended:** `prompts/`, `config/`, `research/`, `results/`, plus
  **append-only** to `docs/Universe-Decisions.md` and `docs/Research-Library-Map.md`.
- **Evidence Standard.** No finding without its chart. Every statistic carries its n. No
  recommendations. The agent describes the picture; Cooper decides what it means.

### Closed — do not reopen

D6, D8, D9. Histogram smoothing. Intensity estimation, envelope fitting, constant-reference
thresholding, two-state segmentation, Hawkes calibration, print aggregation, time-of-day-matched
flanking baselines. **The void cutoff** — retired in 10c, not reinstated. **Testing an `ok=False`
interval's raw `norm` value against `threshold + d`** — it uses a value the data floor declared
untrustworthy, and no grid position is offered for it. The wide log-spaced kernel grid and the
animated histogram are **deferred, not closed**.

---

## 2. Tasks

### T1 — Branch, decision, config

- [ ] **T1a** — Re-verify T0a's state table, then cut `phase/10d` from `master` at `213bd7c`. Lay out
      `results/phase_10d/` (`artifacts/`, `charts/`, `controls/`).
- [ ] **T1b** — Commit `prompts/phase_10d.md`, `prompts/phase_10d_spec.md` and
      `prompts/phase_10c_closing_note_erratum.md` **before any other work.**
- [ ] **T1c** — Append **D15** to `docs/Universe-Decisions.md`, verbatim from spec §7 with any Cooper
      amendment folded in. **Append-only.**
- [ ] **T1d** — Write `config/phase_10d.json`: `K ∈ {0,1,2,3,5}`; `d ∈ {0,0.25,0.5,1.0}` decades;
      `min_prints ∈ {2,3,5}` **reference 2**; `sep ∈ {hard_break, bridgeable_count_only}` **reference
      `hard_break`**; the spec §3.3 cost allocation; the counterfactual cutoff set; every seed. Each
      with a `_why`. **The grids are pre-registered by this commit** — narrowing any after seeing
      results voids the phase.
- [ ] T1e — Commit.

### T2 — Control gate — **hard barrier, no real event is read**

- [ ] **T2a — Implement `research/phase_10d/assemble.py`:** label against the argmax-void threshold,
      merge runs under `(K, d, sep)`, then apply `min_prints` to merged objects. **`d` is added to
      the threshold in decades of normalized log interval** — a multiplicative form on a negative log
      threshold inverts the intent. **Under `hard_break` an `ok=False` interval always ends a run;
      under `bridgeable_count_only` it counts against `K` and is exempt from the `d` test.** It is
      never tested on its raw `norm` value under either.
- [ ] **T2b — C1, identity.** **All eight degenerate `(K, d)` cells at `min_prints = 2`,
      `sep = hard_break`** must reproduce 10c's assembly **exactly, print for print**, and be
      identical to each other. Verify against a replay of a committed 10c cell, not only synthetic
      input. **Hard gate.**
- [ ] **T2c — C2, monotonicity.** Merged count non-increasing and merged duration non-decreasing as
      `K` and `d` rise; count non-increasing as `min_prints` rises. **Hard gate.**
- [ ] **T2d — C3, depth direction.** Raising `d` admits **more** separators, never fewer. **Hard
      gate** — catches the log-sign error.
- [ ] **T2e — C4, separator equivalence.** On a synthetic sequence containing **no** `ok=False`
      intervals, `hard_break` and `bridgeable_count_only` must produce **identical** output. **Hard
      gate** — this is what makes any difference on real data attributable to `ok=False` gaps and
      nothing else.
- [ ] **T2f — C5, floor no-op.** `min_prints = 2` must delete zero objects. **Hard gate** — this is
      what makes 2 the valid reference.
- [ ] **T2g — Evaluate the gate.** Post the control table. **Any failure is a hard stop and no real
      event is read.**
- [ ] T2h — Chart 01. Commit.

### T3 — The counterfactual gate report — **description only, nothing applied**

- [ ] **T3a** — Report the void-parameter distribution under 10c's argmax-void selection, pooled and
      per segment, per kernel.
- [ ] **T3b** — For each pre-registered candidate cutoff in config, report the share of ok cells that
      **would** be declined. **Apply none.** No cutoff enters the computation path anywhere.
- [ ] **T3c** — State it exactly, per T0b's correction: **10c cannot decline on void magnitude**
      (`D13_void_parameter.threshold: null` — void ranks, never gates); **a decline path on peak count
      does exist** — fewer than two surviving peaks, or no valid trough pair — **and it fired 0/504 on
      this cohort.** Report 10c's `insufficient_context` share alongside, and **state that the two are
      different quantities with different causes** (window data floor versus bimodality). **Do not
      present `insufficient_context` as comparable to v4's `no_threshold` share.**
- [ ] **T3d** — Note against D9's Zaliapin reasoning that a method which never declines on void
      magnitude cannot produce the decline share D9 calls a headline result. **Record the tension;
      resolve nothing.**
- [ ] T3e — Chart 02. Commit.

### T4 — Assembly

- [ ] **T4a** — Label every interval against the argmax-void threshold, exactly as 10c does.
- [ ] **T4b** — Assemble across `K` × `d` × `min_prints` × `sep` per the config's cost allocation:
      full cross at D5 = 8 min on the reference variant; identity cell plus the extremes of the
      non-degenerate range at the other kernels and variants. **Eight of the twenty `(K, d)`
      combinations are degenerate copies of the identity** — compute or collapse, but label them
      degenerate in the artifact either way.
- [ ] **T4c — Break-cause census.** For every run break in the reference cell, record whether it was
      caused by an interval **at or above threshold** or by one **failing the `ok` mask**, and report
      the split pooled and per segment. **This is the first measurement in the programme of how much
      burst fragmentation is a data-quality artifact rather than market behaviour.**
- [ ] **T4d** — Per sub-burst: start, end, duration, print count, share of session prints, share of
      session move. Per event: count, spacing, and move share carried by the largest, second, third.
      Session-move denominator per the D5 anchor note, unchanged.
- [ ] **T4e** — Sub-burst timing relative to the D7 detection anchor and to the event peak. **State
      the poll interval with every detection-anchored figure, per D7.**
- [ ] T4f — Charts 03–05. Commit.

### T5 — Attribution — **the deliverable**

- [ ] **T5a — Decompose the duration shift.** Three reads off the same grid, each with full
      distribution (q25 / median / q75 / max), pooled and per segment, per kernel:
      **floor-only** — `(K=0, d=0)` across `min_prints ∈ {2,3,5}`;
      **merge-only** — `min_prints = 2` across the 12 non-degenerate `(K, d)` cells;
      **joint** — the full surface, showing whether the two interact or simply add.
      State all three **alongside v4's and 10c's recorded figures read from their artifacts.**
      **Say which mechanism moved the number.** If neither moves duration materially, the scale is
      coming from where argmax-void puts the threshold and that is where the next phase looks.
      **Do not soften a null.**
- [ ] **T5b — `n_prints` composition by cell.** Report the object population's print-count
      distribution at each cell. **This distinguishes the two mechanisms where a median cannot:**
      merging *promotes* short objects into longer ones — the 2-print share falls while prints inside
      bursts are preserved; the floor *deletes* them — the 2-print share falls and those prints leave
      the burst population. Report both the share and the total prints-inside-bursts at every cell.
- [ ] **T5c — Separator sensitivity.** `hard_break` versus `bridgeable_count_only` at matched cells.
      **The difference is the measurement from T4c expressed in object terms.** Descriptive.
- [ ] **T5d — Parameter dominance.** Does count or duration track the merge tolerance more strongly
      than it tracks anything about the event? **Over the twelve non-degenerate cells only.**
      **This is 10d-R3.**
- [ ] **T5e — Count vs. print count, descriptive only.** Spearman and log-log slope against T=0 print
      count, session duration and absolute activity. **No pass/fail. No gate.** Retired at 10c.
      Prior-version figures read from their committed artifacts, attribution checked.
- [ ] **T5f — Degeneracy check.** Share of events yielding one session-spanning sub-burst, or
      duration at the timestamp resolution floor. Per segment.
- [ ] **T5g — Kernel and variant consistency.** Does the attribution hold across the three kernels
      and 10c's variants, or is it specific to one? Descriptive.
- [ ] T5h — Charts 06–09. Commit.

### T6 — Report

- [ ] **T6a** — Carry the causal audit forward **unchanged**. State that 10c retired zero non-causal
      fields and this phase retires none, reading counts from
      `results/phase_10/artifacts/v4_causal_audit.parquet`. **Claim no retirement.**
- [ ] **T6b** — Write `results/phase_10d/REPORT.md`. Audience: a fresh chat with no context. Every
      number carries its n, kernel, variant, merge cell, floor and separator rule, and its artifact
      path. **Lead with the attribution, not with a duration number.** No recommendations, no
      characterisation of any result as good, promising, weak or disappointing.
- [ ] **T6c** — Digest per the digest contract, headline rows for T3b, T3c, T4c, T5a and T5b. Post
      the exact digest diff before writing it.
- [ ] T6d — Commit. **Post and stop.**

---

## 3. Escalation Criteria

| # | Condition | Measure | Threshold |
|---|---|---|---|
| **10d-R0** | **Cooper rejects the decomposition on visual review against the tape** | Chart 05, tape review | **Overrides every other row in either direction.** The scale judgment lives here — §4 |
| 10d-R1 | 10c's committed assembly specification cannot be reconstructed from artifacts | T0b table | Any unfilled row — hard stop. *(Did not fire at T0.)* |
| 10d-R2 | Control gate fails | C1–C5 | Any failure — hard stop, no real event read |
| 10d-R3 | **The merge tolerance drives the answer** | Change in count and median duration **across the twelve non-degenerate cells** | Config; propose and justify. Fires if count or duration tracks the tolerance more strongly than any event characteristic |
| 10d-R4 | **Attribution is not separable** | Floor-only and merge-only shifts at T5a | Config. Fires if the two cannot be distinguished — the phase would then have no deliverable, only a combined number |
| 10d-R5 | Degenerate decomposition | Share yielding one session-spanning sub-burst, or duration at the resolution floor | Config |
| 10d-R6 | Attribution is kernel- or variant-specific | Consistency of T5a across kernels and variants | Config. **Inconsistency is a finding first** — fires only if no kernel shows a coherent effect |
| 10d-R7 | Any cutoff applied to the void parameter anywhere in the computation path | Code review at each commit | Any — hard stop. T3 reports counterfactuals; it applies none |
| 10d-R8 | Any `ok=False` interval tested on its raw `norm` value | Code review | Any — hard stop. That value is excluded by the data floor and no reading uses it |
| 10d-R9 | Any full-table plan over `filtered_trades` / `filtered_quotes` | Query plan | Any — **standing escalation row 4** |

**Explicitly not escalation rows:** sub-burst count correlating with print count (retired at 10c,
measured at T5e); the counterfactual declined share at T3b; and the T4c break-cause split, which is a
first measurement and carries no threshold.

**If any row fires:** hard stop, commit, post observed values and charts. Do not adjust parameters to
make a criterion pass. Do not narrow a pre-registered grid.

---

## 4. Note on the primary success metric

**No numeric duration bar is pre-registered, deliberately.** D13 records that no burst timescale is
established at usable precision, so a numeric bar would invent the quantity the programme has
recorded it does not have. The scale judgment is **10d-R0 — Cooper's visual review against the
tape** — and duration is reported at T5a without pass/fail attached. Cooper decision point, spec §8.4.

**And note what the deliverable actually is.** A shorter, longer or unchanged duration distribution is
not by itself the result. **The result is the attribution** — which mechanism moved it, and whether
it moved at all. A phase that improves the number without saying why has not answered the question.

---

## 5. Chart Contract

| # | File | Question | Looks like this if wrong |
|---|---|---|---|
| 01 | `01_control_assembly.html` | Does the reference cell reproduce 10c, and do all four axes move things the right way? | Any print-level difference at a degenerate cell; non-monotone count or duration; separator axis not inert on clean input |
| 02 | `02_void_counterfactual.html` | Where do argmax-void values sit, and what would a cutoff decline? | Nothing here can fail — description only. **Must be visibly labelled "no cutoff applied"** |
| 03 | `03_break_cause.html` | How often is a run broken by a real gap versus by a thin window? | A large `ok=False` share means the data floor is shaping the object population — a finding, not a failure |
| 04 | `04_duration_spacing_moveshare.html` | What do the extracted objects look like? | Duration piled at the resolution floor |
| 05 | `05_tape_review/` | **Do the marked bursts match what is on the tape?** | This is 10d-R0. Per-event, spanning the activity range and **all four segments** |
| 06 | `06_attribution.html` | **Floor-only vs merge-only vs joint — which moved duration?** | The two shifts indistinguishable — 10d-R4, and the phase has no deliverable |
| 07 | `07_nprints_composition.html` | Does merging promote short objects, or does the floor just delete them? | 2-print share falling while prints-inside-bursts falls with it — that is deletion, not promotion |
| 08 | `08_merge_surface.html` | How do count and duration move across the grid? **Degenerate plateau labelled a parameterization artifact** | A strong gradient in the tolerance direction — 10d-R3 |
| 09 | `09_kernel_variant_consistency.html` | Does the attribution hold across kernels and variants? | Effect present at one kernel only |
| 10 | `10_count_vs_print_count.html` | Descriptive only — how does count relate to activity? | Nothing here can fail. Reported for comparability |

---

## 6. Output Files

| File | Description | Status |
|---|---|---|
| `prompts/phase_10d.md`, `prompts/phase_10d_spec.md`, `prompts/phase_10c_closing_note_erratum.md` | This prompt, its spec, the erratum | [ ] |
| `config/phase_10d.json` | Four grids, cost allocation, counterfactual cutoffs, seeds, each with `_why` | [ ] |
| `research/phase_10d/assemble.py` | Merge, separator handling, run-length floor | [ ] |
| `results/phase_10d/controls/*.json` | C1–C5 outcomes | [ ] |
| `results/phase_10d/artifacts/t3_void_counterfactual.parquet` | Void distribution and counterfactual declined shares | [ ] |
| `results/phase_10d/artifacts/t4_break_cause.parquet` | Run-break census by cause | [ ] |
| `results/phase_10d/artifacts/t4_subbursts.parquet` | Per sub-burst, every grid cell, degeneracy flagged | [ ] |
| `results/phase_10d/artifacts/t5_attribution.json` | Floor-only / merge-only / joint decomposition | [ ] |
| `results/phase_10d/charts/*.html` | Charts 01–10 | [ ] |
| `docs/Universe-Decisions.md` | **Append-only** — D15 | [ ] |

---

## 7. Reporting

On completion, post:

1. Control gate table — control, required outcome, observed, pass/fail
2. **Attribution table — floor-only, merge-only, joint, with the verdict on which moved the number**
3. `n_prints` composition table — 2-print share and total prints-inside-bursts, by cell
4. Break-cause table — threshold crossing versus `ok=False`, pooled and per segment
5. Counterfactual table — void distribution and would-be declined share per candidate cutoff, with
   **"no cutoff applied"** stated
6. Separator sensitivity table
7. Parameter-dominance table — over the non-degenerate cells
8. Kernel and variant consistency table
9. Escalation check table — every row, observed value, pass/fail
10. Output file table with status filled in
11. Verification block — script path, function, row counts in and out of every filter, reproduction
    command, config hash, for every number above
12. Commit list

Every claim cites its chart. Every statistic carries its n, kernel, merge cell, floor and separator
rule. **No recommendations.**

---

## 8. Approval Gate

Post and stop. Do not begin follow-on work, do not draft a successor phase, do not characterise the
result. Cooper reads charts 05, 06 and 07 and decides.
