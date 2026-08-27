# Research Library Map

**Generated:** 2026-07-15 (Phase 0a), updated 2026-07-15 (Phase 0b — added `config/`, `.claude/`, `src/`, `CLAUDE.md`, and both phases' `research/phase_0b/`/`results/phase_0b/` content), updated 2026-07-16 (Phase 0c — added `config/phase_0c.json`, `prompts/phase_0c.md`, two untracked `docs/` entries, and `research/phase_0c/`/`results/phase_0c/` content), updated 2026-07-16 (Phase 1 — added `config/phase_1.json`, `prompts/phase_1.md`, `docs/Agent_Prompt_Standard.md` now tracked at v1.3, `docs/Mom-DB-Strategy-Research-Program.md` now tracked, and `research/phase_1/`/`results/phase_1/` content), updated 2026-07-18 (Phase 1b — added `config/phase_1b.json`, `config/dev_sample_v2.json`, four `prompts/phase_1b*.md` (base + 3 amendments), `src/data/canonical.py`, `.secrets/` gitignore entry, and `research/phase_1b/`/`results/phase_1b/` content), updated 2026-07-20 (Phase 1c — added `config/phase_1c.json`, three `prompts/phase_1c*.md` (base + 2 amendments), `src/data/canonical.py` extended (`repaired_1c` column), and `research/phase_1c/`/`results/phase_1c/` content; `filtered/{event}/*_repair_1c.parquet` sibling files noted as a new data/ pattern, not individually catalogued per data/'s standing exclusion)
**Phase 8 catch-up (2026-08-01):** the per-file catalog below reflects the repo through end of Phase 1c and was **not maintained per-phase for Phases 2–7** (a pre-existing lapse in the standing rule, not created by Phase 8). Phase 8's own additions are recorded at folder level in the "Phase 8 additions" section immediately below; Phases 3–7 additions remain un-backfilled and are a known gap.

**Reflects commit:** per-file catalog = end of Phase 1c (branch `phase/1c`), post-`phase-1b-approved`; folder-level Phase 8 addendum = `phase-8-approved`; folder-level D5-redirect and Phase 9 addenda = `phase-9-approved` (2026-08-03), the commit at which both lines were integrated onto `master`
**File count covered:** ~1132 files — ~417 individual per-file entries below + 9 folder-level entries covering `archive/runs/`'s other 685 files, plus `results/phase_1c/staging/`'s thousands of gitignored fetch-output files (folder-level, not catalogued individually), per the coverage rules established in Phase 0a.
**Standing rule:** Any phase that adds, moves, or removes repo files must update this map in the same phase.

This map covers `archive/`, `config/`, `docs/`, `notebooks/`, `prompts/`, `research/`, `results/`, `src/`, `.claude/`, and repo-root loose files. `data/` is excluded per standing rule (documented separately in `data/Schema.md`). `hawkes-ofi-impact/` and `scanner-epg-momentum/` are independent, already-git-tracked sibling projects — not walked file-by-file, but each gets a summary section below so this map isn't blind to a third of the workspace.

---

## Phase 10 addendum — v3 and v4 (folder-level; branch `phase/10`, 2026-08-06)

Supersedes the "ran in two scopes" framing in the Phase 10 section below: the phase ran **four**
method versions on one branch, none approved. Ordering, with the decision each produced:

| Version | Method | Outcome | Decision |
|---|---|---|---|
| v1 | segmentation — Kleinberg 2-state (Arm A) and threshold+hysteresis (Arm B) | **rejected on row 0** (Cooper's tape review); all four numeric rows had passed | **D6** |
| v2 | intensity profile — one global peak, decay timescale | hard stop, rows 1, 2, 3, 6 | **D8** |
| v3 | envelope-and-excursion against the event's own envelope | **rejected on row 0**; its Allan/Fano gate and its Arm A test had both passed | **D9** |
| v4 | locally-normalized log inter-trade-interval thresholding + void gate | hard stop, rows 1 and 6 | — |

Files added beyond those listed in the Phase 10 section below:

- `prompts/phase_10_v3.md` — v3 spec, containing D8. `prompts/phase_10_v4.md` — v4 spec, containing D9.
- `config/phase_10_v3.json` — Allan/Fano dyadic ladder (2⁻⁶–2¹³ s, 20 rungs), broken-stick knee
  detection with BIC comparison, envelope scale derived from the knee, excursion multipliers, seven
  failure thresholds each with its justification.
- `config/phase_10_v4.json` — tie variants, normalization-window grid (10/20/30%), histogram and
  peak-finding parameters, void cutoff 0.70, minimum prints per sub-burst, eight failure thresholds
  each with its justification and its provenance (adopted from the literature vs. proposed here).
- `research/phase_10/v3_t1_gate.py` (Allan/Fano gate, broken-stick knee), `v3_t2_t4_subbursts.py`,
  `v3_t5_stability.py`, `v3_chart01.py`, `v3_t6_charts.py`, `v3_t6b_tape.py`.
- `research/phase_10/v4_pipeline.py` (intervals, local normalization, void gate, sub-bursts),
  `v4_t5_t6.py` (Arm A test, stability, causal audit), `v4_t7_charts.py`, `v4_t7b_tape.py`.
- `results/phase_10/artifacts/v3_*` — `t1_gate.json`, `t1_gate_curves.parquet`,
  `t1_gate_knees.parquet`, `t3_subbursts.parquet`, `t3_event_metrics.parquet`, `t2_t4_summary.json`,
  `t5_stability.json`, chart manifests.
- `results/phase_10/artifacts/v4_*` — `event_metrics.parquet`, `subbursts.parquet`,
  `histograms.parquet`, **`causal_audit.parquet`** (18 fields tagged causal / non-causal with a
  one-line reason each — the handoff artifact for Phase 17), `t5_t6_summary.json`,
  `pipeline_raw.json`, chart manifests.
- `results/phase_10/charts/v3_01–06*.html` (+ `.png`), `results/phase_10/charts/v4_01–05*.html`
  (+ `.png`) — kaleido-verified.
- `results/phase_10/charts/v3_07_tape_review/`, `v4_06_tape_review/` — per-event review sets, 60
  charts each plus a full-cohort sortable index, untracked via a nested `.gitignore` (the pattern
  first used by v1 and now standard for this phase).
- Superseded records, all retained, none deleted: `REPORT_v1_superseded.md` /
  `digest_v1_superseded.json`, `REPORT_v2_v3_superseded.md` / `digest_v2_v3_superseded.json`,
  `REPORT_v3_superseded.md` / `digest_v3_superseded.json`. Each carries a header naming the decision
  that superseded it, what survives, and what is withdrawn. Live record: `REPORT.md` / `digest.json`
  (v4). Cross-phase copies: `results/reports/phase_10_report.md` (v1),
  `phase_10_v3_report.md`, `phase_10_v4_report.md`.

**Note on v4's chart 06.** Its first build shaded sub-burst intervals on the full-session axis and
showed nothing — median sub-burst duration is 348 ns against a 57,600 s axis, i.e. sub-pixel. The
shipped version uses five panels: three full-session (with sub-burst *locations* marked as ticks,
labelled as locations rather than widths) plus two zoom panels (~2 s and ~5–20 µs) where intervals
are shaded to true extent. Recorded because any future per-event chart of a sub-second object hits
the same wall.

Files modified: `docs/Universe-Decisions.md` (**D8**, **D9**), this file. Both append-only.

New DB objects: none. New canonical-view flags: none.

---

## Phase 10 additions (folder-level; branch `phase/10`, in progress, 2026-08-04)

Phase 10 ran in two scopes on one branch. **v1 = "Burst Decomposition"** (segmentation, two arms) was
**rejected at its approval gate on failure criterion row 0** — Cooper's visual review against the tape —
and is superseded by `docs/Universe-Decisions.md` **D6**. **v2 = "Intensity Profile and Burst
Timescale"** replaces it. v1's artifacts are retained as the evidentiary record D6 rests on (D6
consequence (b)) and are **not inputs to any downstream phase**. Tick-grain throughout, zero passes over
`filtered_trades`/`filtered_quotes` — all tick reads are targeted per-event reads of
`data/filtered/{event}/trades.parquet` plus `*_repair_1c.parquet` siblings, proven row-for-row
equivalent to `filtered_trades_dev_v4` on 56/56 dev v4 events (9,638,361 rows).

Files added:

- `prompts/phase_10.md` — v1 spec (segmentation). **Closed, not continued.**
- `prompts/phase_10_v2.md` — v2 spec (intensity profiling), per D6.
- `prompts/phase_10_v2_r1.md` — R1 resolution: derives the detection anchor per D7, amends v2 T2b and
  escalation rows 9 and 13, and orders the docs entries this section is part of.
- `config/phase_10.json` — v1 config: cohort + seed, both arms' parameters and baselines, sensitivity
  grid, four pre-registered failure thresholds, chart-07 selection rule and cap, runtime ceilings.
- `config/phase_10_v2.json` — v2 config: resolution grid `k`, both observables, anchor definitions,
  decay fractions, terminal-condition multiples, tie variants, level-conditioning strata, poll and
  threshold grids (D7), failure thresholds, runtime ceilings.
- `research/phase_10/*.py` — `common` (config/cohort loaders, D3 extended-day session clock, targeted
  per-event tick reader), `kleinberg` (v1 Arm A, brute-force-verified), `arm_b` (v1 Arm B),
  `t1_cohort`, `t0d_tick_surface`, `t2_arm_a`, `t3_arm_b`, `t4_measure`, `t5_sensitivity`, `chartlib`,
  `t6a_charts`, `t6b_tape_review`, `v2_t0a_preconditions`, plus the v2 estimation/measurement modules.
- `results/phase_10/artifacts/*.json` — committed summaries (`t0_tick_surface`, `t1_cohort_summary`,
  `t2_arm_a_summary`, `t3_arm_b_summary`, `t4_burst_measurements`, `t5_sensitivity`,
  `t6a_chart_manifest`, `t6b_tape_review_manifest`, `v2_t0a_escalation_row9`, and the v2 artifacts);
  `*.parquet` gitignored/regenerable per Agent_Prompt_Standard §12.
- `results/phase_10/charts/01–06*.html` (+ `.png`) — v1, kaleido-verified.
- `results/phase_10/charts/07_tape_review/` — v1 per-event tape review, 80 charts + full-cohort
  sortable index, ~446 MB. Kept untracked by a **`.gitignore` nested inside that directory** rather
  than an edit to the repo-root `.gitignore`, so the §12 outcome holds without writing outside the
  phase's write allowlist. New pattern, recorded here.
- `results/phase_10/{REPORT_v1_superseded.md, digest_v1_superseded.json}` — the v1 record, renamed at
  R1.2 so it cannot be read cold as the phase's findings; cross-phase copy
  `results/reports/phase_10_report.md`.
- `results/phase_10/{REPORT.md, digest.json}` — v2.

Frozen cohort, shared by v1 and v2: `results/phase_10/artifacts/t1_cohort_manifest.parquet`, 114
events (50 dev v4 primary + 50 activity extension + 8 row-cap census + 6 sidecar), seed 42, content
hash `e1a0ac73a79aa573`. Pooled analysis cohort = 100; row-cap census and sidecar are carried,
labeled, never pooled. Stratified on **T=0 print-count decile** from `event_minute_bars_v2`, not
`momentum_pct`.

Files modified: `docs/Universe-Decisions.md` (**D6** — segmentation withdrawn in favour of intensity
profiling; **D7** — the detection anchor is derived, not sourced), this file. Both appended, never
edited in place, per the R1.1 amendment to escalation row 13.

New DB objects: none.

New flags: none on the canonical view. Phase 10 joins the three existing phase-artifact flags
(`flag_possible_row_cap`, `flag_has_dup_prints`, `flag_cross_session_extreme`) and re-derives nothing.

---

## Phase 9 additions (folder-level; `phase-9-approved`, 2026-08-03)

Phase 9 = "Path Shape, Cross-Session Integrity, and Clustered Inference" (repairs the cross-session price-basis defect in Phase 8's markouts, separates the detection-time / holding-period / latency axes, and adds the first retracement measurement). Read-only: zero passes over `filtered_trades`/`filtered_quotes`; every quantity derives from `event_minute_bars_v2` and frozen Phase 6b/8 artifacts. Files added:

- `prompts/phase_9.md` — the phase prompt, plus an appendix recording the T0 escalation-row-1 stop (no `main` branch; trunk `master` stale at `295a0e1` with 0 Phase 8 files) and Cooper's resolution (fast-forward `master` to `6dd52cf`, then cut `phase/9` from it).
- `config/phase_9.json` — CA flag threshold (`ln 1.8`), integer tolerance/range, trim bounds, bootstrap reps/seed, horizons, latencies, holds, write allowlist, baseline SHAs.
- `research/phase_9/*.py` — `common` (loaders, v2 row-pin guard, session-close convention, cell statistics), `t1_ca_detector`, `t2_sensitivity`, `t3_retracement`, `t4_axis_grid`, `t5_clustered`, `t6_runway_split`, `chart_common`, `chart_01`–`chart_08`.
- `results/phase_9/artifacts/*.json` — committed summaries (`t1_ca_detector`, `t2_cross_session_sensitivity`, `t3_retracement_summary`, `t4_axis_summary`, `t5_clustered_inference`, `t6_runway_split`); `*.parquet` (`t1_cross_session_flags`, `t3_retracement`, `t4_axis_grid`) gitignored/regenerable per Agent_Prompt_Standard §12.
- `results/phase_9/charts/01–08*.html` (+ `.png`) — kaleido-verified per the Chart Contract.
- `results/phase_9/{REPORT.md, digest.json}`; cross-phase copy `results/reports/phase_9_report.md`.

Files modified at approval: `docs/Universe-Decisions.md` (**D4 Amendment A12** — the tick-only quarantine extends to cross-session tick price ratios), `docs/Open-Items-Register.md` (four Phase 9 items opened), `CLAUDE.md` (cross-session basis rule + flag home), this file.

New flag, homed in the phase artifact and **not** in `src/data/canonical.py`: `flag_cross_session_extreme`, per (event, session-pair), in `results/phase_9/artifacts/t1_cross_session_flags.parquet` — parallel to Phase 8's `flag_possible_row_cap` and 6b's `flag_has_dup_prints`. Promoting it to the canonical view is a separate Cooper decision, open in `docs/Open-Items-Register.md`.

New DB objects: none.

**Branch integration note.** `phase/9` was cut from `master` at `6dd52cf` before the `docs/d5-redirect` line existed, so Phase 9 ran on a tree without D5, A11, or the Strategy Program v2.0. No measurement depends on D5 — Phase 9 cites D4 and reads `event_minute_bars_v2` plus frozen 6b/8 artifacts. At approval both lines were brought onto `master`: `docs/d5-redirect` fast-forwarded first (`6dd52cf` → `60494b9`), then `phase/9` merged in, with this file the only conflict (both lines appended a section here). `phase-9-approved` tags the integrated result.

---

## D5 redirect additions (documentation-only; branch `docs/d5-redirect`, 2026-08-03)

Not a phase — no data read, no measurement, no code run. Records `docs/Universe-Decisions.md` D5 (intraday post-trigger, long-only, burst-scale horizons) and re-sequences the program around it. Files added:

- `prompts/redirect_d5.md` — the Cooper-approved redirect prompt, committed before any edit.
- `docs/Claude-Code-Operating-Plan.md` — **newly tracked, Cooper-supplied 2026-08-03.** Cited by `prompts/phase_0a.md`, `prompts/phase_0b.md` and this file since Phase 0a, but had never existed in any commit on any branch; the gap was confirmed by the T0d audit and closed the same day. Committed unmodified first, then edited (§6 phase map).
- `results/redirect_d5/doc_existence_audit.json` — T0d eight-path existence audit, the search method that established the Operating Plan's absence, and the four recorded conflicts (C1–C4).
- `results/redirect_d5/verbatim_checks.json` — machine output of the T7 character-exact transcription checks.
- `results/redirect_d5/REPORT.md` — verification block, diffstat, commit list, and every agent-authored passage quoted in full. **No cross-phase copy at `results/reports/`** — that rule is scoped to phases, and `results/reports/` sat outside this prompt's allowed write set.

Files modified: `CLAUDE.md` (new `## Strategy surface (D5)` block, Pointers), `docs/Universe-Decisions.md` (D5 + D5 Amendment A11 — Phase 6b archive-only), `docs/Mom-DB-Strategy-Research-Program.md` (v2.0: §3.3, §6, §8, §9), `docs/Claude-Code-Operating-Plan.md` (§6 map rows 8+ replaced, D5 rows renumbered 10–19), `docs/Open-Items-Register.md` (three items opened, ARBB row-cap priority raised), this file. No deletions.

## Phase 8 additions (folder-level; `phase-8-approved`, 2026-08-01)

Phase 8 = "Event-Study Grid: Forward Markouts from Tradeable Anchors" (first forward-return measurement; scan-free over `event_minute_bars_v2`, D4-clean). Files added:

- `prompts/phase_8.md`, `prompts/phase_8_amendment_10.md` (A10.1 — 09:00 population guard), `prompts/phase_8_amendment_10_2.md` (A10.2 — detection anchor, contamination test; incl. A10.3 row-13 override).
- `config/phase_8.json` — anchors, rung ladder, participation-baseline rule, era boundary, horizons, detection anchor (1.30× tick), escalation rows, amendment blocks.
- `research/phase_8/*.py` — `t0_preconditions`, `t1_decomposition`, `t2a_eth_split`, `t2b_row_cap`, `t3_participation`, `t4_anchors`, `a101_backfill`, `t5_markout_grid`, `t6_survivorship`, `a102_detection`, `a102_contamination`, `a102c_grid`, `a102d_recoverability`, `chart_common`, `chart_01`–`chart_14` (`chart_10` also emits `10b`).
- `results/phase_8/artifacts/*.json` — committed summaries (`t0_preconditions`, `t1_decomposition`, `t2_eth_split`, `t2_row_cap_scan`, `t3_participation`, `t4_anchors_summary`, `a101_label_backfill`, `t5_markout_summary`, `t6_survivorship`, `a102_detection_summary`, `a102_contamination_test`, `a102_detection_markout_summary`, `a102_falsepositive_recoverability`); `*.parquet` gitignored/regenerable per Agent_Prompt_Standard §12.
- `results/phase_8/charts/01–14*.html` (+ `.png`) — kaleido-verified per the Chart Contract.
- `results/phase_8/{REPORT.md, digest.json}`; cross-phase copy `results/reports/phase_8_report.md`.
- `docs/Open-Items-Register.md` — two Phase 8 entries appended (false-positive rate unmeasured; `flag_possible_row_cap` canonical.py + root cause).

New DB objects: none (Phase 8 reused `event_minute_bars_v2` from `phase-6b-approved`; no table created or modified).

Per the coverage rules for this phase, `archive/runs/` (685 files of repetitive machine-generated run output) is described at the folder level, one entry per run subdirectory, rather than per file — every one of those 685 files is still individually catalogued in `results/phase_0a/artifacts/inventory_before.json` / `inventory_after.json`. Everything else gets a per-file entry.

---

## Directory tree (top 2 levels, `data/` excluded)

```text
E:\Trading Research/
├── .claude/
│   ├── commands/            (digest.md, verify.md, gate.md)
│   └── scheduled_tasks.lock
├── .gitignore
├── archive/
│   ├── CLAUDE.md
│   ├── INVENTORY.md
│   ├── misc/
│   └── runs/
├── CLAUDE.md
├── config/
│   ├── phase_0b.json
│   ├── phase_0c.json
│   ├── phase_1.json
│   └── dev_sample_events.csv
├── docs/
│   ├── Research-Library-Map.md
│   ├── Agent_Prompt_Standard.md      (tracked Phase 1 - v1.3)
│   ├── Agent_Prompt_Standard (1).md  [untracked - v1.1/1.2 copy, deletion candidate]
│   └── Mom-DB-Strategy-Research-Program.md (tracked Phase 1)
├── hawkes-ofi-impact/          [independent git repo — out of scope, see summary below]
├── notebooks/
│   ├── CLAUDE.md
│   └── *.ipynb (15 notebooks)
├── prompts/
│   ├── phase_0a.md
│   ├── phase_0b.md
│   ├── phase_0c.md
│   └── phase_1.md
├── research/                   [Obsidian vault]
│   ├── .obsidian/
│   ├── CLAUDE.md
│   ├── alpha-hypotheses/
│   ├── brainstorm/
│   ├── phase_0a/
│   ├── phase_0b/
│   ├── phase_0c/
│   ├── phase_1/                (this phase's own tooling, distinct from phase_1_context/ below)
│   ├── phase_1_context/
│   ├── phase_1_ext_hours/
│   ├── phase_2_signal_forge/
│   ├── phase_3_alpha_hunter/
│   ├── phase_4_campaign/
│   └── *.md (62 top-level notes)
├── results/
│   ├── cleanup/
│   ├── data_inventory/
│   ├── final_gap_fill/
│   ├── hardware/
│   ├── ingestion_fixes/
│   ├── ingestion_run/
│   ├── momentum_curation/
│   ├── phase_0a/
│   ├── phase_0b/
│   ├── phase_0c/
│   ├── phase_1/
│   ├── quotes_fix/
│   └── rebuild_stage1/
├── scanner-epg-momentum/       [independent git repo — out of scope, see summary below]
└── src/                        [recovered from D:\Trading Research in Phase 0b T2]
    ├── __init__.py
    └── data/
        └── db.py, ingest.py, paths.py, prepare_database_split.py, __init__.py
```

---

## Sibling projects (out of scope — summary only, no per-file walk)

### `hawkes-ofi-impact/`

Independent git repository (own `.git`, `CLAUDE.md`, `MEMORY.md`; 2 commits + untracked `notes/`). Top-level layout:

```text
hawkes-ofi-impact/
├── CLAUDE.md, MEMORY.md
├── .claude/            Claude Code project settings/skills
├── backtest/           Runner + phase-charting scripts
├── burst_detection/    Standalone burst-detection module (bars/data/detect/viz/zscore)
├── calibration/        Phase 0 through Phase U calibration scripts (one file per phase)
├── config/             Strategy/model parameter JSON
├── core/               Core engine code
├── data/               data/client.py (DuckDB connection), data/schemas/, data/loaders/
├── docs/                Schema.md, Data Schema.md, Data Client.md, Trade/Quote Loader docs, Scanner-Hawkes-OFI Impact.md (strategy spec), Project_Directory.md, phase results docs
├── live/                Live trading code
├── logs/, notebooks/, notes/, results/, scratch/, tests/, tools/, utils/
```

**What it is:** Algorithmic trading strategy for extended-hours momentum stocks — Hawkes-process order-flow-imbalance (OFI) price-impact model with EPG (event participation gate) entry logic, dynamic stops, and a full calibration phase sequence (Phase 0 through Phase U, all "Complete (Approved)" per its own status table except several "Pending approval": K, K2, L, L v2, L3, N, S, T, U).

**Current state (per its own `CLAUDE.md`):** Phase U (EXIT_D + LULD integration backtest) is the most recent, PF=1.0962 on 100-event val, with 4 open owner-decision questions. Phase K flagged an escalation (entry-edge mean cost-adjusted return ≤ 0). Phase N (oracle burst labeler) is flagged for revisit due to a loader-scoping flaw.

**Relationship to this program:** Per `scanner-epg-momentum/backtest/CLAUDE.md`, this is the **source project** that `scanner-epg-momentum` was derived from ("Source project: `D:\Trading Research\hawkes-ofi-impact`" — a stale pre-migration path, see D:\ findings). `research/`'s vault contains companion docs for several of its modules (`Hawkes Engine.md`, `Signal Processor.md`, `DuckDB Connection.md`, etc.) and one symlinked alpha-hypothesis doc.

### `scanner-epg-momentum/`

Independent git repository (own `.git`, `.claude/`, `MEMORY.md`; deep phase-based commit history). Top-level layout:

```text
scanner-epg-momentum/
├── MEMORY.md, Tradeable Setup Filter.md, live_system_architecture.md, docker-postgres-crashcourse.md
├── .claude/, .vscode/, .dockerignore
├── backtest/            Main code: runner.py, runner_rapid.py, epg_replay.py, setup_filter.py,
│                         charts.py + many phase_*/r1_*/r15_* chart & sweep scripts, config/, core/,
│                         data/, docs/, logs/, results/, scripts/, tests/, tools/, CLAUDE.md
├── docs/
├── live/
└── tests/
```

**What it is:** A standalone, deliberately simplified derivative of `hawkes-ofi-impact` — the "Scanner × EPG × LULD" momentum strategy (per `backtest/CLAUDE.md`: "Removes the full OFI/price-impact/regime stack. Entry: EPG rising edge + gap ≥ 30%. Exit: EPG window close (primary)."). Explicitly told not to import OFI normalization, Gate 3, or dynamic-stop modules from the parent project without approval.

**Current state (per its own `CLAUDE.md`):** Extensive phase history — Bootstrap through Phase EPG-Rapid R1 (gate-threshold sweep, in progress), plus several closed/abandoned lines (LULD quote-proximity exit line abandoned 2026-06-20 after V3/V3b/V3c found the halt population is dominated by discretionary "Straddle-State" pauses a quote-proximity detector structurally can't see; Phase CPD-1 CUSUM gate hard-stopped on CVaR5; Phase WJI-SlowEMA parked). A SlopeGate variant is deployed live without backtest validation yet. 378 tests currently required to pass before any backtest run.

**Relationship to this program:** Derived from `hawkes-ofi-impact` (see above). Its own `CLAUDE.md` still instructs "Always use `D:\Trading Research\.venv\Scripts\python.exe`" — a dead-drive path (see D:\ findings, T2).

---

## `archive/` (immutable historical records — never modified per its own `CLAUDE.md`)

- `archive/CLAUDE.md` — Directory-purpose doc: `archive/` holds read-only output artifacts from completed/superseded research runs; states the convention that `runs/` directories are timestamped and `misc/` holds one-off scripts/configs.
- `archive/INVENTORY.md` — Auto-generated catalog of everything under `archive/runs/` and `archive/misc/`: per-run-folder file counts, sizes, contents, and the script that produced each (references a `src/` that no longer exists in this checkout — see surprises).

### `archive/misc/` (15 files)

- `archive/misc/final_lead_lag_config.json` — Best lead-lag regression hyperparameters from a prior calibration run.
- `archive/misc/kelly_audit_events.json` — Kelly-criterion position-sizing audit event log.
- `archive/misc/retail_audit_events.json` — Retail-impact audit event log.
- `archive/misc/stat_validator.py` — Standalone copy of a statistical-validation script; self-documented as a copy of a canonical `src/backtest/stat_validator.py` that does not currently exist anywhere in this checkout.
- `archive/misc/quick_select_momentum.py` — One-off momentum-event selector script.
- `archive/misc/select_high_momentum_events.py` — One-off high-momentum event filter script; imports a `strategies.bivariate_momentum_hawkes.data_loader` module not present in this checkout.
- `archive/misc/tps_opt.db` — SQLite database from a TPS (trades-per-second) optimization sweep.
- `archive/misc/smoke_test_10.log` — Log from a 10-symbol smoke test run.
- `archive/misc/Signal_Lab_Report_I_LagVsNoise.png`, `_II_ROC.png`, `_III_Stationarity.png` — Signal-lab report screenshots (lag/noise, ROC curve, stationarity charts).
- `archive/misc/VCIG_2024-11-27_332.40_flow_zscore.png`, `WHLR_2024-09-05_553.40_flow_zscore.png`, `ZJYL_2023-12-18_1720.31_flow_zscore.png` — Example flow-z-score indicator plots for three specific symbol-day events.
- `archive/misc/newplot.png` — A one-off Plotly chart export.

### `archive/runs/` (685 files across 9 run subdirectories — folder-level entries)

| Subdirectory | Files | Size | Contents | Produced by (per `archive/INVENTORY.md`) |
|---|---|---|---|---|

| `bivariate_kernel_hawkes/` | 36 | 49MB | Fitted intensities (`.npy`), kernel weight plots (`.html`/`.png`), fit diagnostics (`.json`) | `src/models/hawkes_engine.py` (BivariateHawkesEngine) — `src/` not found in current checkout |
| `gpu_audit/` | 2 | 0.5MB | GPU-vs-CPU parity audit (`.parquet`) | `src/backtest/gpu_batch_runner.py` — not found |
| `luld_preview/` | 1 | 5MB | LULD halt preview report (`.html`) | `src/data/luld_halt_detection.py` — not found |
| `multivariate_hawkes/` | 50 | 16MB | MHP rolling analysis: causality matrices (`.json`), Granger plots (`.png`/`.html`), IRF (`.csv`) | `src/models/` MHP subsystem — not found |
| `research_notebook_runs/` | 339 | 1287MB | Full research-pipeline outputs per symbol-day: intensity plots, fitted params (`.npy`), feature matrices (`.parquet`) — heavily repetitive across ~150 timestamped subfolders | Notebooks → research phases 1-4 |
| `signal_lab/` | 200 | 34MB | Signal-filter comparison: ROC curves (`.png`), noise spectra (`.npy`), bakeoff summaries (`.txt`/`.json`) — repeated across ~10 timestamped reruns | `src/backtest/signal_bakeoff.py` — not found |
| `stat_validation/` | 40 | 104MB | Statistical validation: KS/AD test results (`.json`), regime transition matrices (`.png`), validated feature sets (`.parquet`) | `src/backtest/stat_validator.py` — not found (see `archive/misc/stat_validator.py` standalone copy) |
| `v53_temporal_beta/` | 5 | 1MB | v5.3 temporal-beta sweep configs and results (`.json`) | `src/backtest/v5_runner.py` — not found |
| `v5_battle/` | 12 | 2MB | v5 head-to-head battle configs, PnL curves (`.json`) | `src/backtest/v5_runner.py` + `optimizer.py` — not found |

All `src/*` producer paths above are as recorded in the pre-existing `archive/INVENTORY.md` — none of those `src/` files exist in the current checkout (see the `src/data/` surprise finding in `REPORT.md`).

---

## `notebooks/` (16 files — exploratory only, per its own `CLAUDE.md`; not git-tracked, see `.gitignore`)

- `notebooks/CLAUDE.md` — Directory-purpose doc: notebooks are exploratory tools, not production code; reusable logic should be extracted to `src/`; notebooks are not git-tracked for outputs.
- `notebooks/Analysis_Rolling_Hawkes.ipynb` — Rolling-window Hawkes-process analysis.
- `notebooks/Hawkes.ipynb` — Hawkes-process exploration and kernel visualization.
- `notebooks/ITT.ipynb` — "Inter Trade Time as Change Point Detection" — Kalman-filtered trade-rate regime detection with a hysteresis/debounce state machine and a composite scoring function (capture efficiency, volume intensity, entry lag, flicker count) over momentum event trade data; also produces candlestick + avg-time-between-trades indicator charts. Contains a `d:\Mom. DB started 11-21-25\...` hardcoded path (see D:\ findings).
- `notebooks/Lead-Lag of Intent.ipynb` — Lead-lag correlation analysis.
- `notebooks/Power_Law_Audit.ipynb` — Power-law distribution validation for the event catalog.
- `notebooks/Regime_Analysis.ipynb` — Regime detection and validation.
- `notebooks/Signal_Analysis.ipynb` — Signal-development/comparison notebook (not individually read in this pass — the file's cell structure exceeded the tool's per-read token limit even at a handful of lines; described from filename and directory context only).
- `notebooks/Signal_Lab_Report.ipynb` — Signal-filter comparison (Kalman, SWT, CUSUM, FracDiff).
- `notebooks/VIsualize 5 random (filtered).ipynb` — Randomly samples 5 events from `data/filtered/` and plots 1-minute candlestick, volume, and bid/ask quote-depth charts for each. Contains a `d:\Mom. DB started 11-21-25\...` hardcoded path (see D:\ findings).
- `notebooks/poisson_intensity_gate.ipynb` — Poisson intensity gating exploration.
- `notebooks/regime.ipynb` — Implements a liquidity/regime-gating state machine (volume-weighted stagnation %, Amihud price-impact ratio, ATR + relative-volume liquidity-shock detection, VWAP overlay) over 25 random momentum events; comments describe it as mimicking a Pine Script indicator. Contains a `d:\Mom. DB started 11-21-25\...` hardcoded path (see D:\ findings).
- `notebooks/tps.ipynb` — Very large (~168MB) notebook; not opened due to size. Name suggests trades-per-second analysis, related to `tps_backup_grid.ipynb` below.
- `notebooks/tps_backup_grid.ipynb` — 2D grid-search (Kalman R × debounce window) optimizing a composite "Alpha-Gate" trade-rate regime-detection score across ~30 sampled momentum tickers, with a heatmap of results.
- `notebooks/univariate_kernel_hawkes.ipynb` — Single-dimension Hawkes-process analysis.
- `notebooks/volume.ipynb` — Very large (~262MB) notebook; not opened due to size. Name suggests volume-based analysis.

---

## `config/`

- `config/phase_0b.json` — Dev-sample parameters (n_events, n_strata, per_stratum, seed, eligibility rule).
- `config/dev_sample_events.csv` — The pinned 50-event dev sample list. Committed, never regenerated in place — a disagreement on rebuild is an escalation, not a refresh.
- `config/phase_0c.json` — Seed, per-class failure-sample size, data root, and the folder-name format string under test for the join reconciliation.
- `config/phase_1.json` — Overlap threshold (0.95), chart subsample cap (50,000), seed (42), scan-input/filter-output/phase_0c-artifact paths for the filter forensics phase.
- `config/phase_1b.json` — Seed, dev-sample strat rule, outlier-flag thresholds, classification rule set + escalation thresholds, session-calendar library pin (`pandas_market_calendars` 5.4.0 / `exchange_calendars` 4.13.2, XNYS), retired-dev-v1 note.
- `config/dev_sample_v2.json` — Dev sample v2 manifest: 50 events, 10 deciles, seed 42, eligibility rule.
- `config/phase_1c.json` — Vendor API endpoint/param shape, archive schema (required + `optional_fields`), fetch/retry/rate-limit settings, control-fetch stratification, all escalation thresholds.
- `config/phase_2.json` — 2025-slice definition (confirmed `source_file='file2'`), session-calendar pin (records both the phase_1c pin and the actually-installed `.venv` version, which had drifted), quality-screen and escalation thresholds, `trade_data/`-quarantine path pointers.

## `.claude/`

- `.claude/commands/digest.md` — `/digest`: regenerates the current phase's `digest.json` from its artifacts.
- `.claude/commands/verify.md` — `/verify`: re-runs every repro command in the current phase's digest/report and diffs the numbers.
- `.claude/commands/gate.md` — `/gate`: prints the current phase's escalation check table against live state.
- `.claude/scheduled_tasks.lock` — Harness-managed lock file for scheduled-wakeup state; not phase content.

## `prompts/`

- `prompts/phase_0a.md` — This phase's own instructions (task specification for Phase 0a: repo inventory, reorganization, and library-map generation).
- `prompts/phase_0b.md` — Phase 0b's own instructions (data-layer recovery, `CLAUDE.md`, table loads, dev sample, digest tooling).
- `prompts/phase_0c.md` — Phase 0c's own instructions (bidirectional join reconciliation between `momentum_events` and `data/filtered/`).
- `prompts/phase_1.md` — Phase 1's own instructions (filter forensics: line-cited spec of `filter_events_power_law.py`, NULL-date and orphan-folder origin classification, DB coverage spot-check).
- `prompts/phase_1b.md` — Phase 1b's own instructions (universe repair & canonicalization: `momentum_events_canonical` view, instrument classification, outlier flags, dev sample v2).
- `prompts/phase_1b_amendment_1.md` — T1 escalation resolution: vendor reference API classification replaces the unusable advisory CSV.
- `prompts/phase_1b_amendment_2.md` — T4b escalation resolution: per-side (`trades_ingested`/`quotes_ingested`) coverage replaces the single `folder_ingested` flag.
- `prompts/phase_1b_amendment_3.md` — T5b escalation resolution: session-calendar mismatch root cause, `flag_missing_event_day`/`flag_window_calendar_bug`, XNYS calendar pinned project-wide.
- `prompts/phase_1c.md` — Phase 1c's own instructions (targeted re-collection: heal `flag_missing_event_day`/`flag_window_calendar_bug` via vendor re-fetch, trust-gate control fetches, flag flips, universe recompute).
- `prompts/phase_1c_amendment_1.md` — T3 escalation resolution: archive-schema-equality replaced with content-equivalence (optional sparse fields).
- `prompts/phase_1c_amendment_2.md` — T6 escalation resolution: pre-insertion collision guard (standing rule) + SDOT remediation.
- `prompts/phase_2.md` — Phase 2's own instructions (2025 reconciliation, `trade_data/high_momentum/` window coverage), including an addendum recording the pre-T1 finding that `high_momentum/` was already migrated into `filtered/` before this phase was cut.

## `docs/`

- `docs/Research-Library-Map.md` — This file.
- `docs/Agent_Prompt_Standard.md` — **Tracked, committed Phase 1 T0.** Cooper placed this at v1.3 (2026-07-14: Evidence Standard, §9 Chart Contract mandatory on analysis-only phases, §10 Verification Block, §11 Digest Contract, §12 Git Discipline). Resolves the Phase 0b/0c gap where no file existed at this exact path.
- `docs/Agent_Prompt_Standard (1).md` — **No longer present on disk.** The v1.1/v1.2 copy found during Phase 0c was still there and untracked immediately after T0's docs-housekeeping commit (verified, flagged as a deletion candidate). By T7 it was gone — removed or absorbed by Cooper's own fix rather than by any action taken in this phase, since this phase's write scope never touched `docs/`. Noted here so the discrepancy between T0's and T7's observations is on record rather than silently smoothed over.
- `docs/Mom-DB-Strategy-Research-Program.md` — **Tracked, committed Phase 1 T0.** Same appearance circumstances as the prompt standard (found untracked during Phase 0c). A detailed research-program spec (data audit → structural constraints → two-signal regime architecture → development process) whose §2.3 explicitly calls for the join reconciliation Phase 0c performed and the filter forensics Phase 1 performs.
- `docs/Open-Items-Register.md` — **Added Phase 2 T8.** Standing, append-only log of items surfaced but not resolved in the phase that found them (the 47 untraced `high_momentum` files, unread `enhanced/`/`rebuild_validation_sample/`, stale `Schema.md` `trade_data/` structure, uncorrected `.venv` calendar-library drift). No pre-existing register was found anywhere in the repo before this.
- `docs/Claude-Code-Operating-Plan.md` — **Tracked from 2026-08-03 (D5 redirect).** The harness/process plan whose §2.2 directory contract, §3 standard additions and §6 phase map are cited by `prompts/phase_0a.md`, `prompts/phase_0b.md` and line 518 of this file. Despite those citations it had never been committed on any branch — Cooper held it externally, and it was supplied and tracked when the D5 redirect's T4 needed to edit it. Its §6 map rows 8 and up are prompt filenames from 2026-08-03 onward; rows 0–7 remain the original plan slots and never tracked filenames.

## `src/` (recovered Phase 0b T2 — see `results/phase_0b/artifacts/data_layer_search_d_drive.json` for full provenance)

Did not exist anywhere in this checkout as of Phase 0a. Recovered by locating the only surviving copy at `D:\Trading Research\src\data\` (uncommitted/untracked working-tree state on that drive's own independent git repo — no commit hash applies) and copying `src/data/` only, per `data/Schema.md`'s documented interface. The rest of `D:\Trading Research\src\` (`backtest/`, `models/`, `signals/`, `utils/` — the modules the `research/` vault's companion docs describe) was not copied; only `src/data/` was in scope for this phase.

- `src/__init__.py` — Empty package marker (`"""Quant project source package."""`).
- `src/data/__init__.py` — Empty package marker (`"""Data ingestion and DuckDB access layer."""`).
- `src/data/paths.py` — Central path resolution (`resolve_data_root`, `resolve_database_root`, `resolve_duckdb_path`) with `MOM_DB_DATA_ROOT` / `MOM_DB_DATABASE_ROOT` / `MOM_DB_DUCKDB_PATH` env-var override precedence over hardcoded E: defaults.
- `src/data/db.py` — `get_connection()`: returns a DuckDB connection to the path `paths.py` resolves, creating the parent directory if needed.
- `src/data/ingest.py` — Multi-dataset ingest CLI (`--all` / `--dataset` / `--data-root` / `--db-path` / `--verify-only`); 11 registered loaders (`filtered`, `daily`, `minute`, `second10`, `quote_data`, `momentum_events`, `metadata`, `market_hours`, `symbol_properties`, `nautilus_catalog`, `trade_data`), each independently skip-if-exists.
- `src/data/prepare_database_split.py` — CLI that scaffolds/migrates storage to an external database root, writing a migration manifest and `env.example` template.
- `src/data/canonical.py` — **Added Phase 1b (instructed promotion, D1/D2).** `momentum_events_canonical` view over the raw `momentum_events` table (never modified). Staged construction (`create_view(con, stage=...)`: t2/t5/t6) as Phase 1b's own inputs became available. Per-side coverage (`trades_ingested`/`quotes_ingested`, Amendment 2), `flag_missing_event_day`/`flag_window_calendar_bug` (Amendment 3). `in_scope` is the single join point downstream code must use — the physical `filtered_trades`/`filtered_quotes` tables contain out-of-universe rows. **Extended Phase 2 T8:** `coverage_class` (`full_window`/`event_day_only`, off `filtered_trades`) and `quotes_full_window` (boolean, off `filtered_quotes`) — additive, non-destructive, joined from `results/phase_2/artifacts/coverage_class.parquet`. Governs the full_window primary-analysis population, not spine membership.

## Repo root

- `.gitignore` — Excludes `.venv/`, the top-level `data/` root only (anchored `/data/` — fixed in Phase 0b after an unanchored version also matched `src/data/`), the two sibling repos, `archive/runs/`, `notebooks/*.ipynb`, `/logs/`, standard Python/cache artifacts, `results/phase_*/artifacts/*.parquet` (added Phase 1, per Agent_Prompt_Standard.md v1.3 §12), and (added Phase 1b) `.secrets/` — local-only API key storage for Amendment 1's vendor reference pull, never committed.
- `CLAUDE.md` — Standing constraints for this program: hard data rules, provenance quarantine, methodology, repo layout, reporting, escalation, and pointers to the other standing docs (two of which don't resolve — see the file itself).

---

## `research/` (Obsidian vault — 157 files in scope)

`research/CLAUDE.md` — Vault-level contributor guide explaining the purpose of the `research/` Obsidian vault, its key files, tag conventions, naming conventions, and notes on symlinked docs and off-limits phase-pipeline parquet files.

Note: the great majority of the top-level notes below are companion docs for a `src/` codebase (`src/models/`, `src/signals/`, `src/backtest/`, `src/data/`, `src/utils/`) that does not exist anywhere in this checkout — see the `src/` finding in `REPORT.md`. Descriptions below state what each doc describes; they do not imply the described code is present on disk.

### `research/` top-level notes (62 files) + `.obsidian/` (9 files)

- `research/.obsidian/app.json` — Obsidian core application config file; currently empty (`{}`, no custom settings saved).
- `research/.obsidian/appearance.json` — Obsidian appearance/theme config file; currently empty (`{}`, default theme).
- `research/.obsidian/community-plugins.json` — Obsidian community plugin enablement list; currently an empty array (no community plugins enabled).
- `research/.obsidian/core-plugins.json` — Obsidian core plugin toggle config listing which built-in plugins (file-explorer, graph, backlink, templates, bases, etc.) are enabled.
- `research/.obsidian/graph.json` — Obsidian graph-view display settings (filters, colour groups, force-layout parameters) for this vault.
- `research/.obsidian/plugins/smart-connections/main.js` — Bundled JS source for the installed "Smart Connections" community plugin (AI chat/related-notes plugin).
- `research/.obsidian/plugins/smart-connections/manifest.json` — Plugin manifest for "Smart Connections" v4.1.8 by Brian Petro, describing it as a chat-with-your-notes / related-content plugin.
- `research/.obsidian/plugins/smart-connections/styles.css` — Bundled CSS stylesheet for the "Smart Connections" plugin UI.
- `research/.obsidian/workspace.json` — Obsidian workspace layout state file (pane/tab arrangement) for the vault.
- `research/00-Index.md` — Vault map of content (tags: type/reference, project/vault) with the src/ architecture diagram, research pipeline table (Phase 1-4), strategy version evolution table, and links to every module doc, notebook index, alpha hypotheses, brainstorm notes, and inventories.
- `research/Alpha Config.md` — Companion doc for `src/signals/alpha_config.py`, describing the `AlphaDeltaConfig` class holding all tunable entry-gate, exit-rule, dynamic-refit, and sizing parameters for the AlphaMomentumHawkes v5 strategy.
- `research/Archetype Backtest Runner.md` — Companion doc for `src/backtest/archetype_runner.py`, covering the archetype-seeded v3 instant-on simulation runner that classifies cold-start events on the first 20 trades and refits after 2 minutes.
- `research/Archetype Classifier.md` — Companion doc for `src/signals/archetype_classifier.py`, describing the `ArchetypeClassifier`/`ArchetypeResult` classes used for cold-start parameter seeding via nearest-archetype matching.
- `research/Archetype Injector.md` — Companion doc for `src/signals/archetype_injector.py`, describing the `ArchetypeInjector`/`ArchetypeMatch` classes used for v5's instant-on parameter injection and replay-buffer seeding.
- `research/Archetype Strategy.md` — Companion doc for `src/signals/archetype_strategy.py`, describing the Nautilus-compatible archetype-seeded momentum Hawkes strategy with zero-warmup cold-start and its phase state machine.
- `research/Archive Inventory.md` — Reference note summarizing archived run artifact directories under `archive/runs/` and `archive/misc/` (file counts, sizes, contents), pointing to `archive/INVENTORY.md` for the full catalog.
- `research/Audit Suite.md` — Companion doc for `src/backtest/analytics/audit.py`, describing the mandatory 4-audit forensic suite (latency, tick-vs-Lee-Ready, peak buyer trap, entry-to-climax) for validating v4+ trade quality.
- `research/Backtest Index.md` — Reference index of backtesting runners, optimization/execution modules, and analytics modules under `src/backtest/`, with a strategy-version dependency diagram.
- `research/Bivariate Strategy.md` — Companion doc for `src/signals/bivariate_strategy.py`, describing the Nautilus-compatible reactive-momentum Hawkes strategy (v2) and its three-phase (catalyst/entry/exit) execution framework.
- `research/CLAUDE.md` — Vault-level contributor guide (see above).
- `research/Data Index.md` — Reference index of data-layer modules (loaders, DuckDB, LULD detection) under `src/data/`, with a data-flow diagram and a table of the 314 GB of raw data sources.
- `research/Data Paths.md` — Companion doc for `src/data/paths.py`, describing the central path-resolution functions (`resolve_data_root`, `resolve_database_root`, `resolve_duckdb_path`) and their env-var override precedence.
- `research/Database Split.md` — Companion doc for `src/data/prepare_database_split.py`, describing the CLI tool that scaffolds and migrates storage to an external database root, writing a migration manifest and env template.
- `research/DuckDB Connection.md` — Companion doc for `src/data/db.py`, describing the single `get_connection()` function that returns a DuckDB connection to `data/duckdb/main.duckdb`.
- `research/DuckDB Ingest.md` — Companion doc for `src/data/ingest.py`, describing the 11-loader DuckDB ingest pipeline (filtered, daily, minute, quote_data, trade_data, etc.) plus dated investigation notes on which subfolders/files are actually loaded.
- `research/Excursion V1.md` — Companion doc for `src/backtest/analytics/excursion_v1.py`, describing the v1 MFE/MAE/PCR excursion analytics functions for round-trip trades.
- `research/Excursion V2.md` — Companion doc for `src/backtest/analytics/excursion_v2.py`, describing the v2 post-trade diagnostics adding K-Means toxic-entry clustering, branching-ratio correlation, and auto-threshold suggestions.
- `research/Exit Autopsy.md` — Companion doc for `src/backtest/analytics/exit_autopsy.py`, describing the premature-exit diagnostic module (Gain Sacrifice, Intensity SNR, Price-Near-High) and its hypothesis about PEAK_DECAY exits.
- `research/Flow Z-Score Indicator.md` — Companion doc for `src/signals/flow_zscore_indicator.py`, describing the `FlowZScoreAnalyzer` class that computes a log-space EWM volume Z-score and produces regime-coloured candlestick charts.
- `research/GPU Accelerated MHP.md` — Companion doc for `src/models/gpu_accelerated_mhp.py`, describing the `RollingHawkesGPU` nn.Module for JIT-compiled recursive-NLL batched rolling MHP fitting with AMP mixed precision.
- `research/GPU Batch Runner.md` — Companion doc for `src/backtest/gpu_batch_runner.py`, describing the full-session GPU tensor backtest runner using the associative-scan Hawkes engine, dynamic VRAM batching, and versioned Parquet output.
- `research/GPU Monte Carlo.md` — Companion doc for `src/backtest/analytics/gpu_monte_carlo.py`, describing the GPU-accelerated 10,000-path Monte Carlo equity-curve simulation (CuPy/PyTorch) with risk-of-ruin and drawdown-duration functions.
- `research/Hawkes Engine.md` — Companion doc for `src/models/hawkes_engine.py`, describing the `BivariateHawkesEngine` (batch + online) and `IntensityTracker` classes, including math for the bivariate Hawkes intensity and a planned event-time mode extension.
- `research/Intensity Gating.md` — Companion doc for `src/signals/intensity_gating.py`, describing the `IntensityGater` class that classifies market regimes (Quiet/Normal/High) from event arrival intensity using Schmitt-trigger hysteresis.
- `research/Kelly Engine.md` — Companion doc for `src/backtest/analytics/kelly_engine.py`, describing the rolling Half-Kelly position-sizing engine with equity-curve construction and Go/No-Go reporting.
- `research/Latency Audit.md` — Companion doc for `src/backtest/analytics/latency_audit.py`, describing the Phase 1 forensic latency audit that measures burst bottom/peak timing, acceleration, and volume impulse around entries.
- `research/LULD Halt Detection.md` — Companion doc for `src/data/luld_halt_detection.py`, describing LULD halt detection (30s VWAP bands + gap detection) and active-timeline compression, including the `HaltWindow` dataclass.
- `research/LULD Halt Logic.md` — Frontmatter-only stub note (tags: type/implementation, domain/data, domain/microstructure) with no title or body content yet; per `00-Index.md` intended as the companion doc for a LULD halt logic module.
- `research/Manifest.md` — Companion doc for `src/utils/manifest.py`, describing the backtest manifest/versioning system that tracks GPU audit runs with version IDs, hyperparameters, git/code fingerprint, and hardware telemetry.
- `research/MHP Analysis.md` — Companion doc for `src/models/analysis.py`, describing the MHP analysis module for causality analysis, impulse-response function plotting, interaction-matrix heatmaps, and fitted-intensity visualisation.
- `research/MHP Data Loader.md` — Companion doc for `src/models/data_loader.py`, describing the bivariate event-stream preparation functions (trade arrivals + volatility spikes) and high-momentum candidate discovery.
- `research/MHP Model.md` — Companion doc for `src/models/mhp_model.py`, describing the core D-dimensional `MultivariateHawkes` nn.Module (MLE fitting, Ogata thinning simulation, windowed log-likelihood).
- `research/Models Index.md` — Reference index of Hawkes/MHP model modules under `src/models/`, with a dependency graph linking core engines, MHP variants, and analysis/data modules.
- `research/Notebooks Index.md` — Reference index cataloguing the 15 Jupyter notebooks in `notebooks/`, grouped into Hawkes Process, Signal Analysis, Market Microstructure, and Data & Visualization categories.
- `research/Optimizer.md` — Companion doc for `src/backtest/optimizer.py`, describing the AlphaMomentumHawkes v4 3-iteration self-optimization loop and its 6 diagnostic scenario-adjustment rules.
- `research/Pandas Loader.md` — Companion doc for `src/data/pandas_loader.py`, describing the legacy Pandas-based data loader (Lee-Ready classification via `merge_asof`, LULD halt removal), noted as superseded by the Polars loader.
- `research/Parallel Runner.md` — Companion doc for `src/backtest/parallel_runner.py`, describing the `ProcessPoolExecutor`-based parallel batch runner for executing 20k+ events with checkpointing and result aggregation.
- `research/Phase 1 — Scanner Context.md` — Phase 1 results/pipeline doc for `research/phase_1_context/build_scanner_context.py`, describing the 9:30 AM "Top Gappers" scanner reconstruction, gap filtering/ranking, and output schema of `scanner_context.parquet`.
- `research/Phase 1b — Extended Hours.md` — Phase 1b results doc for the extended-hours context analysis (pre-market/after-hours), a manual-notebook process with no dedicated script, listing its output artifacts.
- `research/Phase 2 — Signal Forge.md` — Phase 2 results/pipeline doc for `build_signal_forge.py`/`build_signal_forge_v2.py`, describing the transformation of tick data into a 22- and 36-feature stochastic-momentum feature matrix, including halt-stitched Hawkes intensity and LULD features.
- `research/Phase 3 — Alpha Hunter.md` — Phase 3 results/pipeline doc for `research/phase_3_alpha_hunter/build_alpha_hunter.py`, describing the ML regime-classification pipeline that fuses Phase 1/2 features, trains XGBoost, and applies UMAP/SHAP analysis.
- `research/Phase 4 — Campaign.md` — Phase 4 results/pipeline doc for `build_campaign.py`/`build_campaign_hpc.py`, describing the regime-aware backtesting stage with a 3-way Baseline/Filtered/Campaign bake-off and HPC vs serial implementation comparison.
- `research/Polars Loader.md` — Companion doc for `src/data/polars_loader.py`, described as the canonical data loader: Polars zero-copy Arrow I/O, vectorised Lee-Ready classification, and the `EventData` dataclass.
- `research/Quote Data Timestamp Audit.md` — Phase V0.0b results doc (status: needs-review) documenting a full-corpus sweep of `data/quote_data` for schema drift and timestamp-precision issues, sibling to the trades audit, concluding the corpus is largely clean aside from 2 anomalous files and 4 unreadable files.
- `research/ReadMe.md` — Minimal vault entry-point note whose entire body is a single wikilink to `[[Scanner-Hawkes-OFI Impact]]`.
- `research/Regime Hawkes Correlation.md` — Companion doc for `src/models/regime_hawkes_corr.py`, describing the module that combines Poisson intensity-gating regimes with Hawkes fits to compute regime-gated lead/lag correlations against forward volatility.
- `research/Retail Impact.md` — Companion doc for `src/backtest/analytics/retail_impact.py`, describing the spread-centric retail transaction-cost model (half-spread vs square-root market impact, capital ladder, capacity ceiling).
- `research/Rolling Hawkes Engine.md` — Companion doc for `src/models/RollingHawkesEngine.py`, describing the rolling-window MHP estimation engine that fits `MultivariateHawkes` with warm-start parameters over sliding windows.
- `research/Rolling Pipeline.md` — Companion doc for `src/models/rolling_pipeline.py`, describing the CLI pipeline that integrates intensity gating with GPU-accelerated MHP fitting and exports parameter time-series/heatmaps.
- `research/Signal Bakeoff.md` — Companion doc for `src/backtest/signal_bakeoff.py`, describing the signal bake-off runner that compares 4 filter modes (Kalman-Bucy, SWT, CUSUM, FracDiff) against raw thresholds on SNR/FPR/TPR/profit factor.
- `research/Signal Processor.md` — Companion doc for `src/signals/signal_processor.py`, describing the four-mode structural alpha filter (Kalman-Bucy, SWT, CUSUM, FracDiff) with hot-swappable entry/exit filter backends.
- `research/Signals Index.md` — Reference index of signal-processing filters, strategy configs, regime gating, and Nautilus strategy adapters under `src/signals/`, with a filter-mode comparison table.
- `research/Slippage Engine.md` — Companion doc for `src/backtest/slippage_engine.py`, describing the `SlippageEngine` dataclass for L1 quote-based fill simulation and slippage aggregation stats.
- `research/Stat Validator.md` — Companion doc for `src/backtest/stat_validator.py`, describing the large-scale statistical validation pipeline (stratified sampling, parallel execution, sign-randomization permutation test, report generation) for v5.
- `research/Tensor Engine.md` — Companion doc for `src/models/tensor_engine.py`, describing the GPU-only associative-scan (Blelloch prefix-scan) Hawkes engine with vectorised intensity, CVD/VWAP/MFE-MAE signals, and Monte Carlo equity paths.
- `research/Trade Analyzer.md` — Companion doc for `src/backtest/analytics/trade_analyzer.py`, describing the Polars-based trade analyzer computing excursion profile, time/profit efficiency, and statistical robustness metrics (SQN, profit factor) with no for-loops.
- `research/Trade Data Timestamp Audit.md` — Phase V0.0 results doc (status: needs-review) documenting a full sweep of `data/trade_data/high_momentum` for schema drift and whole-second timestamp corruption, including fixes to the audit scripts and findings on duplicate ticker/date pairs and corruption mtimes, pending review.
- `research/Tradeable Setup Filter.md` — Alpha-spec note (symlinked from the canonical copy) specifying an unbuilt `core/filters/setup_filter.py` universe gate that uses four exponentially-forgotten signals (bar range, volume, dollar-volume thinness, body conviction) combined into a composite tradeability score, plus its validation/test plan.
- `research/Utils Index.md` — Reference index of utility modules under `src/utils/`, currently listing only the manifest/versioning module.
- `research/V2 Backtest Runner.md` — Companion doc for `src/backtest/v2_runner.py`, describing the Reactive-Momentum Hawkes v2 backtest runner with auto-tuning loop, catalog/event modes, and post-run parameter adjustment rules.
- `research/V5 Backtest Runner.md` — Companion doc for `src/backtest/v5_runner.py`, describing the production AlphaMomentumHawkes v5 tick-by-tick backtest simulation with its 6 entry gates and 7 exit triggers.

### `research/alpha-hypotheses/`

- `research/alpha-hypotheses/_template.md` — Blank Obsidian template for formalizing a new alpha hypothesis, with frontmatter tags and empty section headers (Hypothesis, Mathematical Specification, Data Requirements, Implementation Tasks, Backtest Requirements, Success Criteria, Results).
- `research/alpha-hypotheses/Scanner-Hawkes-OFI Impact.md` — Active alpha hypothesis spec combining a tradeable-setup scanner filter, Hawkes burst-onset detection, and trade/quote OFI confirmation to trade permanent price impact; includes the full mathematical spec and is a symlink to the canonical doc in `hawkes-ofi-impact/docs/`.

### `research/brainstorm/`

- `research/brainstorm/audit_report.json` — Raw JSON audit results for the AlphaMomentumHawkes v4 (Lead-Follower) backtest, with per-event latency/entry statistics keyed by event.
- `research/brainstorm/audit_report.txt` — Plain-text formatted version of the same v4 Lead-Follower audit (Latency, Tick Test vs Lee-Ready, Peak Buyer Trap, Entry-to-Climax Time checks).
- `research/brainstorm/chat_summary.txt` — Auto-generated session summary of a coding conversation covering a retail-impact transaction-cost engine, GPU Monte Carlo simulation, and a "retail scaling audit" notebook.
- `research/brainstorm/high_momentum_events.txt` — Plain list of roughly 30 ticker_date_magnitude event identifiers ranked by momentum magnitude, used elsewhere as sample/candidate events.
- `research/brainstorm/MHP_IMPLEMENTATION_SUMMARY.md` — Results doc summarizing a 7-file Multivariate Hawkes Process (MHP) module built for GPU-accelerated lead/lag analysis between trade arrivals and volatility spikes.
- `research/brainstorm/PREMATURE_EXIT_FIX_SUMMARY.md` — Results doc diagnosing and remediating "Premature Exit Syndrome" in the Bivariate Hawkes Momentum strategy, reporting a +14.44pp PnL improvement via EMA damping and dual-confirmation exit logic. Contains a `D:\Mom_db` path reference (see D:\ findings, T2).
- `research/brainstorm/Price Impact Bridge.md` — Idea/methodology note bridging Hawkes intensity forecasts to mid-price movement predictions via Order Flow Imbalance (OFI) decomposition.
- `research/brainstorm/README.md` — Short guide explaining the brainstorm directory holds raw one-idea-per-file dumps to be promoted to `alpha-hypotheses/`.
- `research/brainstorm/README_MHP.md` — Overview/usage doc for the Multivariate Hawkes Process (MHP) module.
- `research/brainstorm/TODO.md` — Implementation checklist (phases 1-6) for building a bivariate-kernel Hawkes model with Lee-Ready trade classification and walk-forward refit.
- `research/brainstorm/ToDo.markdown` — Informal brainstorm/chat transcript proposing a 4-step "Alpha Discovery" workflow (Context Engine, Signal Forge, Alpha Hunter, Campaign backtest).
- `research/brainstorm/v5_3_Final_Report.md` — Final results report for the AlphaMomentumHawkes v5.3 ("Temporal Beta" Hybrid) backtest; a symlink to the canonical copy in `archive/runs/`.
- `research/brainstorm/v5_Battle_Results.md` — "Battle Royale" results report comparing three v5 strategy modes on 200 events each; a symlink to the canonical copy in `archive/runs/`.

### `research/phase_0a/` (this phase's own tooling)

- `research/phase_0a/__init__.py` — Empty package marker enabling `python -m research.phase_0a.*` invocation.
- `research/phase_0a/build_inventory.py` — Walks the Phase 0a in-scope directories and writes the per-file inventory manifest (`inventory_before.json`/`inventory_after.json`).
- `research/phase_0a/build_reference_map.py` — Parses every in-scope `.py` file's imports and hardcoded path strings (including the `D:\` hardware-rule finding) into `reference_map.json`.
- `research/phase_0a/diff_inventory.py` — Diffs two inventory manifests and classifies every path as unmoved/moved/new/unexplained-missing; the Verification Block's repro script for T5.

### `research/phase_0b/` (this phase's own tooling)

- `research/phase_0b/__init__.py` — Empty package marker enabling `python -m research.phase_0b.*` invocation.
- `research/phase_0b/check_duckdb_state.py` — Opens the E: DuckDB read-only and compares table row counts against the baseline recorded in `data/Schema.md`; T1b's repro script.
- `research/phase_0b/build_dev_sample.py` — Builds the pinned 50-event dev sample: eligibility (must have a `filtered/` folder), momentum_pct-decile stratification via a fixed contiguous-split rule, seeded per-decile sampling; writes `config/dev_sample_events.csv`.
- `research/phase_0b/materialize_dev_tables.py` — Reads the pinned CSV and materializes `dev_events`, `filtered_trades_dev`, `filtered_quotes_dev` in the E: DuckDB, reusing `src.data.ingest`'s schema-union helpers.
- `research/phase_0b/chart_01_stratification.py` — Builds `01_dev_sample_stratification.html` (full-universe histogram/ECDF + dev-sample rug overlay by decile).
- `research/phase_0b/chart_02_event_sizes.py` — Builds `02_dev_sample_event_sizes.html` (per-event trade+quote row counts, log scale, cumulative-% line).
- `research/phase_0b/validate_digest.py` — Schema-validates a `digest.json` against a reconstruction of the (unlocated) digest contract; see `CLAUDE.md`'s Pointers section.

### `research/phase_0c/` (this phase's own tooling)

- `research/phase_0c/__init__.py` — Empty package marker enabling `python -m research.phase_0c.*` invocation.
- `research/phase_0c/build_folder_inventory.py` — Single `os.scandir` pass over `data/filtered/`; classifies every entry (ticker/date/momentum-string parsing, both-files/trades-only/quotes-only/neither/unparseable, `date_is_none` flag). Ticker segment accepts `.` and lowercase letters (warrant/preferred-share conventions); stray non-directory entries excluded from the classified denominator.
- `research/phase_0c/none_date_lookup.py` — Cross-references the `date_is_none` folders against `momentum_events` by (ticker, momentum_pct), reporting whether the corresponding event row's own date is valid, also null, unmatched, or ambiguous.
- `research/phase_0c/build_join_reconciliation.py` — T2a (reproduces Phase 0b's exact eligibility check), T2b (classifies non-joinable events into 6 failure classes), T2c (classifies every folder into matched/orphan/ambiguous/none_date_unresolved/unparseable).
- `research/phase_0c/build_failure_samples.py` — Draws up to 20 seeded examples per nonzero T2b class with full event detail and an actual disk listing for the ticker+date prefix.
- `research/phase_0c/chart_01_momentum_pct.py` — Builds `01_momentum_pct_joinable_vs_dropped.html` (overlaid ECDFs + strip sample).
- `research/phase_0c/chart_02_events_over_time.py` — Builds `02_events_over_time_by_join_status.html` (monthly stacked bars by join status).
- `research/phase_0c/chart_03_failure_classes.py` — Builds `03_failure_class_counts.html` (bar chart, all 6 T2b classes).

### `research/phase_1/` (this phase's own tooling — filter forensics; distinct from the pre-existing `research/phase_1_context/` below, an earlier, differently-numbered pipeline stage)

- `research/phase_1/refit_boundary.py` — Read-only re-implementation of `filter_events_power_law.py`'s fit (T2); derives the kept set and compares against `momentum_events` on a date/event_date-coalesced key, writing `refit_comparison.json`.
- `research/phase_1/orphan_drift.py` — T4's orphan membership test against raw scan inputs and the re-derived kept set; discovers and flags the 5,911 false-orphan date-bug subset, writing `orphan_classification.parquet` and `orphan_summary.json`.
- `research/phase_1/ingestion_spotcheck.py` — T5a: reconstructs the 409 parser-fix-recovered folders from `folder_inventory.parquet` and runs aggregated ticker-level/event-date presence queries against `filtered_trades`/`filtered_quotes`.
- `research/phase_1/dev_sample_spotcheck.py` — T5b: per-event row counts for the 50 dev-sample events against `filtered_trades_dev`/`filtered_quotes_dev`.
- `research/phase_1/build_charts.py` — Builds all three Chart Contract charts (T6): NULL-date ECDF, q05 boundary scatter, orphan reclassification ECDF.

### `research/phase_1b/` (this phase's own tooling — universe repair & canonicalization)

- `research/phase_1b/classify_instruments.py` — T1's original 9-rule heuristic classifier + advisory cross-check (superseded as verdict by Amendment 1, retained as validation).
- `research/phase_1b/fetch_ticker_reference.py` — Amendment 1 T1-R1: paginated bulk pull of `/v3/reference/tickers` (active + inactive) from the Massive API, writing `ticker_reference_snapshot.parquet`.
- `research/phase_1b/rebuild_classification.py` — Amendment 1 T1-R3: rebuilds `instrument_classification.parquet` with vendor `type` as the verdict; heuristic confusion matrix, ticker-reuse check.
- `research/phase_1b/build_canonical_spine.py` — T2: builds `momentum_events_canonical` (stage=t2), row-count/folder-join-ambiguity/no-folder-coverage checks.
- `research/phase_1b/mechanism_outlier_flag.py` — T3: `flag_bad_denominator`, confirms the 53.8M% row is caught.
- `research/phase_1b/reingest_recovered_folders.py` — T4b: re-ingests the 7 in-scope recovered folders into `filtered_trades`/`filtered_quotes` via `src.data.ingest`'s schema-union helpers.
- `research/phase_1b/build_folder_inventory_v2.py` — T4c/Amendment 2 T4-R2: builds `folder_inventory_v2.parquet` (scope/ingestion status), the universe-wide trades-only-folder headline.
- `research/phase_1b/zero_trades_cause_annotation.py` — Amendment 3 T5-R2: annotates the 150 zero-event-day-trades events `calendar_bug`/`unknown`, checks quote coverage for the 8 unknowns.
- `research/phase_1b/window_calendar_bug_quantification.py` — Amendment 3 T5-R3: reconstructs the legacy collector's exact window-stepping logic, compares against the pinned XNYS calendar session-by-session, quantifies `flag_window_calendar_bug`'s blast radius.
- `research/phase_1b/bivariate_outlier_flag.py` — T5: `flag_trades_mom_outlier` (q=0.995 quantile regression), `n_trades_event_day` (true-calendar-day trade count, not the folder's anchor-date tag).
- `research/phase_1b/build_waterfall.py` — T6: finalizes `in_scope`, event-side + folder-side accounting waterfalls.
- `research/phase_1b/build_dev_sample_v2.py` — T7: dev sample v2 manifest + `filtered_trades_dev_v2`/`filtered_quotes_dev_v2` materialization from the main tables, subset/zero-row verification.
- `research/phase_1b/build_chart_01.py` … `build_chart_05.py` — The five Chart Contract charts (01 trades-vs-momentum flags, 02 instrument classes, 03 universe waterfall, 04 dev v2 coverage, 05 calendar damage by offset).

### `research/phase_1c/` (this phase's own tooling — targeted re-collection, calendar-bug heal)

- `research/phase_1c/derive_archive_schema.py` — T0 support: full-corpus `parquet_schema()` scan confirming the file-level vs. DB-table archive schema (conditions/indicators LIST-typed and dropped by design).
- `research/phase_1c/build_heal_manifest.py` — T1: derives 1,966 heal-target pairs via pure per-event set difference (true XNYS window minus a replicated legacy `get_trading_window()`), not positional offset-index mapping.
- `research/phase_1c/t1_crosschecks.py` — T1b: 142-event-day / Set-A-date / quote-side-hard-boundary cross-checks.
- `research/phase_1c/fetch_pair.py` — T2: fetch + archive-schema-alignment primitives (required vs. optional columns, rate-limited pagination), reused by every downstream fetch script.
- `research/phase_1c/select_control_pairs.py` — T3/Amendment 1 T3-R3: 20-pair control selection (15 stratified + 5 targeted for the `correction` optional field).
- `research/phase_1c/derive_optional_fields.py` — Amendment 1 T3-R1: derives `optional_fields` from archive evidence (non-null rate + file-absence), via fast parquet-footer-metadata scan (not a full data scan).
- `research/phase_1c/run_control_fetch.py` — Amendment 1 T3-R4: formal 20-pair control diff against the archive.
- `research/phase_1c/run_full_fetch.py` — T4: executes the heal manifest (3,605 distinct pairs), checkpointed.
- `research/phase_1c/resolve_unknowns.py` — T5: resolves the 8 `unknown`-cause events via their diagnostic fetches.
- `research/phase_1c/ingest_repairs.py` — T6/Amendment 2: verify, place `*_repair_1c.parquet` siblings, ingest under the pre-insertion collision guard (T6-R1).
- `research/phase_1c/remediate_sdot.py` — Amendment 2 T6-R2: surgical removal + re-derivation of SDOT's duplicated quotes session.
- `research/phase_1c/scan_preexisting_quotes.py`, `scan_preexisting_trades.py` — Investigative (T6-R1a): whole-population pre-existing-row scan informing the collision guard's design.
- `research/phase_1c/flag_flips_and_recompute.py` — T7: flag clearing (coverage vs. authorship), universe recompute, `repaired_1c` cross-check.
- `research/phase_1c/volume_reconciliation.py` — T8: healed event-day fetched-vs-scan volume reconciliation.
- `research/phase_1c/build_chart_01.py` … `build_chart_04.py` — The four Chart Contract charts (01 control fetch diffs, 02 healed sessions by offset, 03 volume reconciliation, 04 universe waterfall v2).

### `research/phase_2/` (this phase's own tooling — 2025 reconciliation, `high_momentum/` window coverage)

- `research/phase_2/t1_population.py` — T1: spine guard (20,951) + 2025-slice population, replicated as a read-only CTE (zero-DuckDB-write phase — no `create_view()` calls until T8).
- `research/phase_2/t2_quality_screen.py` — T2: 2025 `momentum_pct` distribution, junk flags (sanity bound / `prev_close` floor / stored-vs-recomputed mismatch), duplicates, per-month counts, plus the migration-signature schema-fingerprint facet.
- `research/phase_2/t3_high_momentum_inventory.py` — T3a/b: documents `high_momentum/`'s absence from the E: data root (migrated into `filtered/` pre-phase, see `results/cleanup/`) and characterizes `momentum_events_for_collection.parquet`'s overlap with the canonical spine.
- `research/phase_2/t4_window_coverage.py` — T4: the core per-event × offset × source window-coverage matrix for the 5,188 2025 in-scope events (`high_momentum` N/A throughout).
- `research/phase_2/t5_source_comparison.py` — T5: overlap comparison between `filtered_trades` and `high_momentum` — N/A (0 compared pairs), documented rather than skipped.
- `research/phase_2/t8_coverage_class.py` — T8 addendum: generalizes T4's logic to ALL 20,951 in-scope events, producing `coverage_class`/`quotes_full_window` for `src/data/canonical.py`'s view extension.
- `research/phase_2/build_chart_01.py`, `build_chart_02.py`, `build_chart_03.py` — The three Chart Contract charts (01 window coverage by offset, 02 2025 momentum quality, 03 source row-count comparison — an annotated empty-state). Chart 04 not produced — condition (pre-2025 dates in `high_momentum`) never triggered.

### `research/phase_1_context/`

- `research/phase_1_context/build_log.md` — Generated build log for the Phase 1 Context Engine run (2026-02-23), recording execution time and summary counts.
- `research/phase_1_context/build_scanner_context.py` — Script that reconstructs the 9:30 AM "Top Gappers" scanner for every momentum-event day, applies a 30% gap filter, ranks tickers, and writes `scanner_context.parquet`. Contains a `D:\Mom_db` path (see D:\ findings, T2).
- `research/phase_1_context/MANIFEST.md` — Project manifest for Phase 1 (Context Engine): objective, results summary, five-stage data pipeline, and assumptions on timestamp alignment.
- `research/phase_1_context/plots/gap_distribution_histogram.png` — Plot output: distribution of gap-at-open percentages across the filtered scanner universe.
- `research/phase_1_context/plots/leaderboard_snapshot.png` — Plot output: snapshot of the ranked daily top-gappers leaderboard.
- `research/phase_1_context/plots/rank_stability_top3.png` — Plot output: stability/persistence of the top-3 gap-ranked tickers over time.
- `research/phase_1_context/scanner_context.parquet` — Phase 1 output: the reconstructed, gap-filtered, ranked scanner context table.

### `research/phase_1_ext_hours/`

- `research/phase_1_ext_hours/build_log.md` — Generated build log for the Phase 1 Extended (pre-market) run (2026-02-23).
- `research/phase_1_ext_hours/DATA_FIXES.md` — Doc explaining split-adjustment normalization and outlier winsorization applied to the extended-hours dataset.
- `research/phase_1_ext_hours/extended_context.parquet` — Phase 1 Extended output: per-event table with split-normalized prices and pre-market metrics.
- `research/phase_1_ext_hours/MANIFEST.md` — Project manifest for Phase 1 Extended: objective, results summary, pipeline stages.
- `research/phase_1_ext_hours/plots/rank_migration.png` — Plot output: minute-by-minute ranking of gappers migrating from pre-market through the opening bell.
- `research/phase_1_ext_hours/plots/split_fix_verification.png` — Scatter plot verifying the split-adjustment normalization fix.
- `research/phase_1_ext_hours/plots/volatility_heatmap.png` — Heatmap of 1-minute log-return volatility across PRE/OPEN_FLIP/STD regimes.
- `research/phase_1_ext_hours/volatility_analysis.parquet` — Phase 1 Extended output: per-event volatility-regime statistics.

### `research/phase_2_signal_forge/`

- `research/phase_2_signal_forge/build_signal_forge.py` — GPU-accelerated Phase 2 v1 script transforming raw tick trades/quotes into a stochastic-signal feature matrix (Hawkes intensity, CVD, OFI), producing `feature_matrix_v1.parquet`. Contains a `D:\Mom_db` path (see D:\ findings, T2).
- `research/phase_2_signal_forge/build_signal_forge_v2.py` — Revised Phase 2 script (Extended Signal Forge): full-day pipeline with a halt-stitched Hawkes kernel, producing `feature_matrix_v2_ext.parquet`. Contains a `D:\Mom_db` path (see D:\ findings, T2).
- `research/phase_2_signal_forge/feature_matrix_v1.parquet` — Phase 2 v1 output: GPU-computed feature matrix of Hawkes/CVD/OFI signals per event.
- `research/phase_2_signal_forge/feature_matrix_v2_ext.parquet` — Phase 2 v2 output: extended feature matrix with halt-stitched Hawkes and halt-context features.
- `research/phase_2_signal_forge/Forge_Audit_Log.md` — Generated audit log for the Phase 2 v1 build (2026-02-24, GPU: GTX 1070).
- `research/phase_2_signal_forge/Forge_Audit_Log_v2.md` — Generated audit log for the Phase 2 v2 (Extended) build (2026-02-24).
- `research/phase_2_signal_forge/MANIFEST.md` — Project manifest for Phase 2 Signal Forge: v1-to-v2 changes, results comparison, pipeline architecture.
- `research/phase_2_signal_forge/plots/anatomy_*.png` (10 files: CRIS, CURR, DXLG, GEN, META, NE, PFH, SDRL, SMRT, VSSYW) — v1 three-panel "anatomy" plots (Hawkes intensity/CVD/price) per sample event, generated by `build_signal_forge.py`.
- `research/phase_2_signal_forge/plots/intensity_heatmap.png` — v1 plot: heatmap of Hawkes intensity across sampled events.
- `research/phase_2_signal_forge/plots_v2/anatomy_*.png` (11 files: AI, CBL, CORZ, CORZW, CURR, DBD, GEN, NE, PFH, SDRL, SMRT, VAL) — v2 four-panel "anatomy" plots (with halt zones and micro-zoom) per sample event, generated by `build_signal_forge_v2.py`.
- `research/phase_2_signal_forge/plots_v2/HALT_RUNNER_TPST_2023-10-11.png` — v2 "proof chart" for ticker TPST illustrating halt-stitched Hawkes behavior across 41 LULD halts.
- `research/phase_2_signal_forge/plots_v2/intensity_heatmap_v2.png` — v2 plot: heatmap of halt-stitched Hawkes intensity across sampled events.
- `research/phase_2_signal_forge/SIGNAL_DICTIONARY.md` — Reference doc defining every v1 feature (normalization factor, Hawkes intensity/acceleration, CVD & convexity, OFI) with formulas and units.
- `research/phase_2_signal_forge/SIGNAL_DICTIONARY_v2.md` — Reference doc defining every v2 (Extended) feature, including halt-stitching logic.

### `research/phase_3_alpha_hunter/`

- `research/phase_3_alpha_hunter/Alpha_Audit.md` — Audit doc for Phase 3 evaluating whether the model distinguishes "+200% runners" from "+20% traps," with discrimination-power (Cohen's d) analysis.
- `research/phase_3_alpha_hunter/build_alpha_hunter.py` — Script implementing the Phase 3 ML regime-classification pipeline: fuses Phase 1/2 data, engineers forward targets, trains an XGBoost model, generates UMAP/SHAP visualizations. Contains a `D:\Mom_db` path (see D:\ findings, T2).
- `research/phase_3_alpha_hunter/fused_dataset.parquet` — Phase 3 output: merged Phase 1 + Phase 2 dataset with forward-target labels.
- `research/phase_3_alpha_hunter/GOLDEN_FEATURES.md` — Reference doc ranking top predictive features (by SHAP value) driving the XGBoost contagion-prediction model.
- `research/phase_3_alpha_hunter/plots/calibration_curve.png` — Plot: XGBoost model's prediction calibration curve.
- `research/phase_3_alpha_hunter/plots/shap_bar.png` — Plot: bar chart of mean |SHAP value| feature importances.
- `research/phase_3_alpha_hunter/plots/shap_beeswarm.png` — Plot: SHAP beeswarm chart of per-feature value/impact distribution.
- `research/phase_3_alpha_hunter/plots/training_curve.png` — Plot: XGBoost training/validation loss curve.
- `research/phase_3_alpha_hunter/plots/umap_regime_map.png` — Plot: UMAP dimensionality-reduction cluster map of event regimes.
- `research/phase_3_alpha_hunter/xgb_regime_model.json` — Serialized trained XGBoost model (tree dump).

### `research/phase_4_campaign/`

- `research/phase_4_campaign/build_campaign.py` — Script implementing the Phase 4 Campaign backtest: scores events via the XGBoost model, runs a regime-aware strategy, bakes off Baseline vs. Filtered vs. Campaign performance. Contains a `D:\Mom_db` path (see D:\ findings, T2).
- `research/phase_4_campaign/build_campaign_hpc.py` — HPC-optimized rewrite using GPU batch inference and joblib-parallel data loading, targeting under 60 seconds end-to-end. Contains a `D:\Mom_db` path (see D:\ findings, T2).
- `research/phase_4_campaign/Campaign_Report.md` — Results report (HPC edition) for the Phase 4 Campaign backtest on 523 events.
- `research/phase_4_campaign/plots/drawdown_comparison.png` — Plot: drawdown curves across the Baseline/Filtered/Campaign strategies.
- `research/phase_4_campaign/plots/performance_comparison.png` — Plot: cumulative equity-curve comparison across strategies.
- `research/phase_4_campaign/plots/score_vs_return.png` — Plot: model event score vs. realized return.
- `research/phase_4_campaign/prime_candidates.parquet` — Phase 4 output: XGBoost-scored candidate events selected for the Campaign strategy.
- `research/phase_4_campaign/scored_universe.parquet` — Phase 4 output: full 523-event test universe with model scores.

## `results/` (70 files pre-existing + `results/phase_0a/` this phase's own outputs)

Per `results/hardware/`, `results/ingestion_run/`, `results/rebuild_stage1/`, etc.: these 9 topic-named subdirectories are the working record of a D:→E: drive migration and subsequent data-integrity cleanup, dated 2026-07-10 through 2026-07-12 (the migration itself completed 2026-07-12, two days before this phase). None of these are phase-numbered per the Operating Plan's `results/phase_{x}/` convention — they predate it.

### `results/cleanup/`

- `results/cleanup/confirmed_lost_events.csv` — List of 47 (ticker, date) events from `high_momentum` confirmed unrecoverable in the 2025 gap-fill migration, with columns ticker, date, source_folder, reason (missing `momentum_pct` column or high null `sip_timestamp` rate), null_detail, had_exploded_markers.
- `results/cleanup/deletion_errors.csv` — Empty error log (header only: filename, error) recording zero errors during a deletion pass of migrated `high_momentum` originals.
- `results/cleanup/deletion_report.md` — Dated 2026-07-11 final report on migrating 5,902 verified-clean 2025 gap events into `filtered/` and deleting their `high_momentum` originals, covering clean-vs-lost classification, migration batches, post-migration validation, and the 47 files deliberately kept back.
- `results/cleanup/emergency_unblock_report.md` — Dated 2026-07-11 report on an emergency disk-space-driven re-verification (1,561 files, 100% pass) and scoped deletion of 30,297 safe `high_momentum` files (14.15GB) to free space on `D:` during the migration.
- `results/cleanup/high_momentum_unique_events.csv` — List of ticker/date pairs unique to `high_momentum` (not yet in `filtered/`), the candidate set for the gap-fill migration.
- `results/cleanup/migrate_remaining_errors.csv` — Empty error log (header only: source_folder, dest_dir, error) for the second migration batch of remaining events, recording zero errors.
- `results/cleanup/migrated_1561_reverification.csv` — Per-file re-verification results (schema, unit, granularity, row-count checks) for the first batch of 1,561 migrated trade files, all PASS.
- `results/cleanup/migration_candidates.csv` — Candidate list of clean (ticker, date, pct_whole_second, n_trades, had_exploded_markers) events eligible for migration from `high_momentum` to `filtered/`.
- `results/cleanup/migration_integrity_report.csv` — Full post-migration audit (schema fingerprint, unit, granularity, row counts) for all migrated destination directories, all marked PASS.
- `results/cleanup/migration_plan.csv` — Planned mapping of each migration-eligible event (ticker, date, momentum_pct_str, source_folder) to its destination `filtered/` directory name.
- `results/cleanup/migration_validation.csv` — Duplicate/second copy of the post-migration validation audit (same schema/unit/granularity/PASS columns as `migration_integrity_report.csv`) for the migrated event set.
- `results/cleanup/null_sweep_results.csv` — Per-source-folder null-value sweep results (total rows, null sip_timestamp/price/size counts, errors) confirming zero nulls in the migrated trade files.
- `results/cleanup/pre_deletion_manifest_final.csv` — Manifest listing every source file in `high_momentum` with a disposition reason (`already_in_filtered` or `migrated_and_verified`) and size in bytes, used to gate the final deletion pass.
- `results/cleanup/safe_delete_set.csv` — List of files (filename, size_bytes) confirmed safe to delete from `high_momentum` because a verified copy already exists elsewhere.

### `results/data_inventory/`

- `results/data_inventory/candle_data_inventory.csv` — Inventory table (one row per candle data location: `data/daily/`, `data/minute/`, `data/minute/trades/`, `data/second10/`, `data/illiquid_tests/`) documenting resolution, naming conventions, file counts, sizes, ticker/date coverage, and structural flags such as the 90GB of trade ticks mis-filed inside `data/minute/`; byte-identical to `candle_data_inventory.csv.txt` and `candle_data_inventory_copy.txt` (deletion candidate — see REPORT.md).
- `results/data_inventory/candle_data_inventory.csv.txt` — Duplicate copy of `candle_data_inventory.csv` (same content, `.txt` extension).
- `results/data_inventory/candle_data_inventory_copy.txt` — Second duplicate copy of `candle_data_inventory.csv`.
- `results/data_inventory/duckdb_ingestion_state.md` — Dated 2026-07-11 discovery audit finding `data/duckdb/main.duckdb` is completely empty (0 tables) and documenting the intended-vs-actual source paths/table names for all 11 registered ingestion loaders.
- `results/data_inventory/duckdb_loader_status.csv` — Per-loader status table (intended vs actual source, target table, row counts, classification, notes) for all 11 DuckDB loaders, confirming none had been run as of this date.
- `results/data_inventory/duckdb_loader_status.md` — Markdown rendition of the same loader-status table as `duckdb_loader_status.csv`, including a note that a direct `.csv` write was blocked by the repo's permission/off-limits-paths policy and a literal CSV block is embedded instead.
- `results/data_inventory/inventory_summary.md` — Dated 2026-07-11 top-level summary tying together the DuckDB ingestion-state findings and the candle-data-corpus inventory, including the `high_momentum` dangling-reference finding and the 5-location candle corpus table.
- `results/data_inventory/minute_trades_cleanup_report.md` — Dated 2026-07-11 final report on migrating 1,303 unique-only events from `data/minute/trades/` into `filtered/` and then deleting the entire 18,630-file `data/minute/trades/` directory (~84GB net freed on `D:`).
- `results/data_inventory/minute_trades_full_listing.csv` — Full per-file listing (ticker, date, size_bytes, mtime) of the 18,630 files under `data/minute/trades/` prior to its deletion.
- `results/data_inventory/minute_trades_investigation.md` — Dated 2026-07-11 investigation identifying `data/minute/trades/` as 90.1GB of raw trade ticks (not candle data) mis-filed inside the minute-bar tree, with 93% overlap and 7% (1,303 events) unique versus `filtered/`.
- `results/data_inventory/minute_trades_migration.csv` — Post-migration audit (schema, unit, granularity, PASS/FAIL) of the 1,303 events migrated from `data/minute/trades/` into `filtered/`.
- `results/data_inventory/minute_trades_migration_plan.csv` — Planned mapping (ticker, date, momentum_pct_str, dest_dir, source_file, migrated flag) of each unique `data/minute/trades/` event to its `filtered/` destination directory.

### `results/final_gap_fill/`

- `results/final_gap_fill/migration_47_plan.csv` — Planned mapping of the 47 previously-blocked events (ticker, date, momentum_pct_str, dest_dir, migrated flag) to their `filtered/` destination directories after a successful re-pull.
- `results/final_gap_fill/migration_report.md` — Dated 2026-07-11 report on re-pulling and migrating the final 47 blocked events via `collect_massive_data_v2.py`, confirming the earlier corruption was in the original collection run (not data unavailability) and leaving `filtered/` at 29,208 events.
- `results/final_gap_fill/pull_raw_results.csv` — Per-event fetch-and-audit detail (schema fingerprint, timestamp columns, unit, granularity, PASS) for the 47 re-pulled events.
- `results/final_gap_fill/pull_results.csv` — Per-event pull outcome (ticker, date, status=written, trade count) for the 47 re-pulled events, showing genuine trade counts far lower than the corrupted originals.

### `results/hardware/`

- `results/hardware/d_drive_inventory.md` — Dated 2026-07-12 inventory of `D:`'s ~355.6GB used space by top-level directory, classifying each as already-backed-up-to-E: or never-backed-up, totaling ~145.3GB never backed up.
- `results/hardware/data_safety_assessment.md` — Dated 2026-07-12 T5 data-safety assessment finding D: is actively erroring (909 bad-block events), 4 files permanently unrecoverable, and E:'s copy of `filtered/`/`quote_data/` verified trustworthy save for 7 recoverable files.
- `results/hardware/disk_events_full.csv` — Full itemized Windows event-log export (TimeCreated, EventId, Device, Message) of 1,061 disk bad-block error events across two physical disks.
- `results/hardware/disk_identity_mapping.md` — Dated 2026-07-12 report mapping physical disks to drive letters (Disk 0 Toshiba=E:, Disk 1 Samsung SSD=D:, Disk 2 Crucial NVMe=C:) and itemizing the 174 (E:) vs 887 (D:) bad-block errors by device and time window.
- `results/hardware/full_migration_verification.csv` — Per-file checksum verification log (source_path, dest_path, size_bytes, source/dest SHA256, match, status) for the D:-to-E: data migration copy.
- `results/hardware/shared_cause_check.md` — Dated 2026-07-12 report concluding E:'s and D:'s error bursts are temporally non-overlapping (~45-hour gap), leaving root cause between the two disks inconclusive.
- `results/hardware/smart_reliability_data.md` — Dated 2026-07-12 report noting SMART/reliability-counter checks were all blocked by lack of administrator elevation in this environment.

### `results/ingestion_fixes/`

- `results/ingestion_fixes/investigation_and_fixes.md` — Dated 2026-07-11 code-fix report for **`src/data/ingest.py`** addressing four items (dead `load_minute()` fallback path, `momentum_events` single-file loading confirmed intentional, `metadata` loader doc-vs-code mismatch, `trade_data`'s hardcoded subfolder list trimmed). Confirms `src/data/ingest.py` existed and was being actively edited as of 2026-07-11 — three days before this phase found it absent from the checkout.

### `results/ingestion_run/`

- `results/ingestion_run/disk_capacity_measurement.md` — Dated 2026-07-12 capacity-measurement report on `D:` usage after deleting a failed 102GB DuckDB file, estimating ingestion storage needs (~195.67GB) against 312.51GB of freed margin.
- `results/ingestion_run/loader_scope.md` — Dated 2026-07-11 classification of all 11 registered DuckDB loaders into in-scope (`filtered`, `quote_data`, `metadata`) versus deferred/out-of-scope for the current ingestion run.
- `results/ingestion_run/schema_drift_characterization.md` — Dated 2026-07-12 metadata-only schema scan of `filtered_trades`, `filtered_quotes`, and `raw_quotes` full corpora, characterizing type conflicts (e.g. `size` BIGINT/DOUBLE) and column presence drift.
- `results/ingestion_run/schema_drift_fix_report.md` — Dated 2026-07-12 report describing a schema-union fix added to `src/data/ingest.py` to handle heterogeneous per-file schemas, plus its verification against the previously-failing subset.
- `results/ingestion_run/schema_drift_raw.json` — Raw JSON schema-scan output (per-table, per-column file counts, presence percentage, types_seen/type_conflict flags) underlying `schema_drift_characterization.md`.
- `results/ingestion_run/subset_validation_report.md` — Dated 2026-07-11 subset-validation report showing the `filtered` and `quote_data` loaders failing 10-44% of a 50-file sample due to heterogeneous schemas and a `momentum_pct` overflow, gating a full run until fixed.

### `results/momentum_curation/`

- `results/momentum_curation/diff_report.csv` — Per-event diff (ticker, date, status) comparing the existing curated momentum-events file against a reproduction run, all sampled rows "unchanged".
- `results/momentum_curation/regenerated_candidate.parquet` — Binary parquet output from re-running the momentum-event curation script against current on-disk scan files; not opened (binary).
- `results/momentum_curation/reproduction_run_a_full_current.parquet` — Binary parquet output of "Run A" (script as-is), which exactly reproduced the existing curated file; not opened (binary; byte-identical to `regenerated_candidate.parquet` — deletion candidate, see REPORT.md).
- `results/momentum_curation/reproduction_run_b_excl_recovered.parquet` — Binary parquet output of "Run B" (7,252 recovered events excluded from the candidate pool), which did not reproduce the existing file; not opened (binary).
- `results/momentum_curation/validation_report.md` — Dated 2026-07-11 report validating the momentum-event curation pipeline by reproduction, concluding the existing curated file already includes all recovered events and rejected all 7,252 of them on the merits.

### `results/quotes_fix/`

- `results/quotes_fix/column_usage_scope.csv` — Per-column downstream-usage audit of `filtered/quotes.parquet`'s 12 columns, classifying each as load-bearing or unused.
- `results/quotes_fix/coverage_check.csv` — Per-event lookup checking whether each of 5,871 broken quote events has a matching source file in `quote_data/`.
- `results/quotes_fix/coverage_ratio_distribution.csv` — Per-event row-count comparison (filtered vs quote_data, coverage_ratio, timestamp spans) over a 600-event sample used to diagnose the quotes row-count gap.
- `results/quotes_fix/fix_report.md` — Dated 2026-07-11 final report on the quotes-migration fix: 5,800/5,871 broken quote events fixed via a subtractive 5-column schema copy from `quote_data/`, 71 unfixed.
- `results/quotes_fix/flagged_anomalies.csv` — List of 12 events excluded from the quotes fix for implausible in-session row counts, consistent with known trades-corruption tickers.
- `results/quotes_fix/quotes_schema_actual.md` — Dated 2026-07-11 enumeration of the actual 12-column schema of a correctly-populated `filtered/*/quotes.parquet` file, verified via `DESCRIBE`.
- `results/quotes_fix/row_count_gap_investigation.md` — Dated 2026-07-11 root-cause investigation concluding the quotes row-count "gap" is a legitimate session-window scope difference between `quote_data/` and `filtered/`, not a collection bug.
- `results/quotes_fix/schema_check.md` — Dated 2026-07-11 schema-compatibility check, initially a hard stop over an ambiguous timestamp-column mapping, later resolved to approve a subtractive 5-column fix.
- `results/quotes_fix/t3_copy_failures.csv` — Log of one copy failure during the quotes fix (CRC/data error reading the source file).
- `results/quotes_fix/t3_copy_successes.csv` — List of events whose `quotes.parquet` was successfully copied/fixed from `quote_data/`.
- `results/quotes_fix/t5_cleanup_deleted.csv` — List of empty placeholder directories removed after the quotes fix completed.
- `results/quotes_fix/t5_missing_markers.csv` — Small list of 3 events whose placeholder marker was missing/unaccounted for during cleanup verification.
- `results/quotes_fix/timestamp_mapping_verification.md` — Dated 2026-07-11 report confirming via direct row-level join that `quote_data.timestamp` equals `sip_timestamp`, and that `quote_data/` covers only 16-41% of `filtered/`'s row counts per event.

### `results/rebuild_stage1/`

- `results/rebuild_stage1/__pycache__/collect_massive_data_v2.cpython-314.pyc` — Compiled Python 3.14 bytecode cache for `collect_massive_data_v2.py`; not opened (binary).
- `results/rebuild_stage1/collect_massive_data_v2.py` — Corrected trades-collector script fixing a pagination-truncation bug (429 responses not retried) relative to `collect_massive_data.py`; contains a `D:\` path (see D:\ findings, T2).
- `results/rebuild_stage1/collection_log_v2.txt` — Timestamped INFO log of trade-collection runs by `collect_massive_data_v2.py`.
- `results/rebuild_stage1/go_no_go_report.md` — Dated 2026-07-10 go/no-go validation report; escalated after 10 of 30 planned validation events when one event failed a count-comparison threshold, halting further validation groups.
- `results/rebuild_stage1/group_a_count_comparison.csv` — Per-event comparison of trade counts between prior collector output and the new v2 collector for the 10 Group A validation events.
- `results/rebuild_stage1/run_validation_sample.py` — Validation-driver script that runs the v2 collector against a 30-event sample, audits each output, and checks escalation criteria incrementally; contains a `D:\` path (see D:\ findings, T2).
- `results/rebuild_stage1/t1_schema_rootcause.md` — Dated report tracing the `high_momentum` schema-loss corruption to a downstream process rather than the collector or raw API.
- `results/rebuild_stage1/validation_audit.csv` — Per-event audit detail (group, collector status, elapsed time, schema fingerprint, n_trades, unit) for the 10 Group A validation events.

### `results/phase_0a/` (this phase's own outputs)

- `results/phase_0a/artifacts/` — Machine-readable inventory manifests and reference maps produced by this phase (see `REPORT.md` for the full list).
- `results/phase_0a/digest.json`, `results/phase_0a/REPORT.md` — This phase's digest and written report (see `REPORT.md` itself for what it contains).

### `results/phase_0b/` (this phase's own outputs)

- `results/phase_0b/artifacts/data_layer_search.json` — T1's E:\ search (working trees + git history + rest of E:\): zero matches.
- `results/phase_0b/artifacts/data_layer_search_d_drive.json` — T1d's D:\ search: all 4 target files found at `D:\Trading Research\src\data\`, with mtimes, interface diffs, and git-provenance detail.
- `results/phase_0b/artifacts/duckdb_state_check.json` — T1b's table/row-count comparison against `data/Schema.md`; clean match.
- `results/phase_0b/artifacts/momentum_events_load.json` — T4's three-way count verification and T4a/T4b stats.
- `results/phase_0b/artifacts/dev_sample_build.json` — Eligibility waterfall, per-decile counts, T5c rebuild-hash check, T5d timing.
- `results/phase_0b/artifacts/dev_tables_materialized.json` — Per-event row counts for `filtered_trades_dev`/`filtered_quotes_dev`.
- `results/phase_0b/artifacts/digest_roundtrip_check.json` — T6c's round-trip result (Phase 0a's digest fails `headline_metrics_present`, reported not fixed).
- `results/phase_0b/charts/01_dev_sample_stratification.html`, `02_dev_sample_event_sizes.html` — This phase's two required charts.
- `results/phase_0b/digest.json`, `results/phase_0b/REPORT.md` — This phase's digest and written report.

### `results/phase_0c/` (this phase's own outputs)

- `results/phase_0c/artifacts/folder_inventory.parquet`, `folder_inventory_summary.json` — T1's full per-folder classification (post ticker-parser fix), and its summary counts.
- `results/phase_0c/artifacts/none_date_lookup.json` — T1 hard-stop resolution's cross-reference of the 114 `date_is_none` folders against `momentum_events`.
- `results/phase_0c/artifacts/join_reconciliation.json`, `join_reconciliation_detail.json` — T2a/T2b/T2c bidirectional join classification, summary and full per-row detail.
- `results/phase_0c/artifacts/failure_samples.json` — T3's seeded samples (up to 20 per nonzero T2b class) with disk-listing spot checks.
- `results/phase_0c/artifacts/repeat_ticker_comparison.json` — T4's third joinable-vs-dropped comparison (repeat-ticker rate).
- `results/phase_0c/charts/01_momentum_pct_joinable_vs_dropped.html`, `02_events_over_time_by_join_status.html`, `03_failure_class_counts.html` — This phase's three required charts.
- `results/phase_0c/digest.json`, `results/phase_0c/REPORT.md` — This phase's digest and written report.

### `results/phase_1/` (this phase's own outputs)

- `results/phase_1/filter_spec.md` — T1's line-cited spec of `filter_events_power_law.py`: the fit, the keep rule, the empirically-determined `momentum_pct` formula, and the NULL-date mechanism.
- `results/phase_1/artifacts/scan_input_inventory.json` — T1a's input inventory: existence, row counts, columns, and cleaning stats for both scan-input files.
- `results/phase_1/artifacts/refit_comparison.json` — T2's read-only refit vs `momentum_events` comparison (23,268/23,268, 100% overlap both directions).
- `results/phase_1/artifacts/null_date_forensics.json` — T3's NULL-date origin classification (b), evidence, and the `none_date_lookup` cross-reference.
- `results/phase_1/artifacts/orphan_classification.parquet` — T4's per-orphan membership/reclassification flags. **Gitignored** (regenerable via `research/phase_1/orphan_drift.py`), not committed.
- `results/phase_1/artifacts/orphan_summary.json` — T4's orphan fractions by class, including the false-orphan/genuine-orphan split.
- `results/phase_1/artifacts/ingestion_spotcheck.json` — T5's merged 409-folder DB-presence and 50-dev-event row-count results.
- `results/phase_1/artifacts/ingestion_spotcheck_409_detail.parquet` — T5a's per-folder detail backing the summary above. **Gitignored**, not committed.
- `results/phase_1/charts/01_momentum_pct_by_date_status.html`, `02_q05_boundary.html`, `03_orphans_vs_boundary.html` — This phase's three required charts.
- `results/phase_1/digest.json`, `results/phase_1/REPORT.md` — This phase's digest and written report.

### `results/phase_1b/` (this phase's own outputs)

- `results/phase_1b/artifacts/instrument_classification.parquet` — Rebuilt (Amendment 1) vendor-verdict classification, heuristic validation columns. **Gitignored**, not committed.
- `results/phase_1b/artifacts/instrument_classification_summary.json`, `instrument_classification_rebuild_summary.json` — T1a's original heuristic counts, then Amendment 1's rebuilt vendor-verdict counts + confusion matrix.
- `results/phase_1b/artifacts/ticker_reference_snapshot_summary.json` — Amendment 1 T1-R1a: 36,282-row bulk snapshot fetch + universe join summary (the snapshot parquet itself is gitignored).
- `results/phase_1b/artifacts/t1_gate_recheck.json` — Amendment 1 T1-R4: suspect-class gate re-check (0% unresolved).
- `results/phase_1b/artifacts/canonical_spine_t2_summary.json` — T2a/b/c: row count, folder-join ambiguity, no-folder coverage checks.
- `results/phase_1b/artifacts/mechanism_outlier_flag_summary.json` — T3: `flag_bad_denominator` counts, top-10 table, 53.8M% row confirmation.
- `results/phase_1b/artifacts/t4_pre_ingestion_list.json`, `t4_reingest_summary.json`, `t4r3_verification.json` — T4a pre-flight list, T4b post-ingest per-folder verification (the `GTN.A` escalation), Amendment 2 T4-R3's re-verification under the rewritten criterion.
- `results/phase_1b/artifacts/folder_inventory_v2.parquet`, `folder_inventory_v2_summary.json` — T4c/Amendment 2 T4-R2: 24,609-folder scope/ingestion status, universe-wide trades-only-folder headline (1,606 folders).
- `results/phase_1b/artifacts/t4d_dev_v1_forensics.json` — T4d: confirms dev v1 was materialized from a source other than the main tables.
- `results/phase_1b/artifacts/bivariate_outlier_flag_summary.json` — T5: `flag_trades_mom_outlier` fit + counts, the 150 zero-event-day-trades events + root-cause diagnosis.
- `results/phase_1b/artifacts/t5r1_calendar_mismatch.json` — Amendment 3 T5-R1: Set A (14 phantom-holiday dates) / Set B (7 phantom-session dates), 142-date cross-check.
- `results/phase_1b/artifacts/t5r2_zero_trades_cause.json` — Amendment 3 T5-R2: 142 `calendar_bug` / 8 `unknown` cause split, quote-coverage check for the 8 singletons.
- `results/phase_1b/artifacts/event_flags.parquet` — Per-event flags + `n_trades_event_day`, consolidated across T5 and Amendment 3. **Gitignored**, not committed.
- `results/phase_1b/artifacts/window_damage.parquet` — Amendment 3 T5-R3: per-event damaged-offset detail. **Gitignored**, not committed.
- `results/phase_1b/artifacts/t5r3_window_damage_summary.json` — Amendment 3 T5-R3: `flag_window_calendar_bug` blast radius (1,849/20,802), damage-by-offset table, 20-event corroboration sample.
- `results/phase_1b/artifacts/t5r4_gate_recheck.json` — Amendment 3 T5-R4: final gate re-check, all criteria pass.
- `results/phase_1b/artifacts/t6_waterfall_summary.json` — T6: event-side + folder-side accounting waterfalls, both residual 0.
- `results/phase_1b/artifacts/t7_dev_sample_v2_summary.json` — T7: dev v2 build, subset verification (0 mismatches), zero-row check (0 events).
- `results/phase_1b/charts/01_trades_vs_momentum_flags.html`, `02_instrument_classes.html`, `03_universe_waterfall.html`, `04_dev_v2_coverage.html`, `05_calendar_damage_by_offset.html` — This phase's five charts (04 is the contract's #4; 05 is Amendment 3's addition).
- `results/phase_1b/digest.json`, `results/phase_1b/REPORT.md` — This phase's digest and written report, covering the base prompt and all three amendments.

### `results/phase_1c/` (this phase's own outputs)

- `results/phase_1c/artifacts/archive_schema_reference.json` — T0 support: file-level vs. DB-table archive schema, full-corpus confirmed.
- `results/phase_1c/artifacts/heal_manifest.parquet` — T1: 1,966-pair deterministic heal-target list. **Gitignored**, not committed.
- `results/phase_1c/artifacts/t1_manifest_summary.json`, `t1b_crosscheck_summary.json` — T1a/b: pair counts by type/side, cross-check results.
- `results/phase_1c/artifacts/t3_escalation_correction_field.json` — T3: the original `correction`-absent hard-stop investigation.
- `results/phase_1c/artifacts/t3r1_optional_fields.json` — Amendment 1 T3-R1: per-column non-null rate + file-absence rate, `optional_fields` derivation.
- `results/phase_1c/artifacts/control_fetch_diffs.parquet`, `t3r4_control_diff_summary.json`, `t3r4_escalation_findings.json`, `t3r4_resolution.json` — Amendment 1 T3-R4: the 20-pair control diff, the ARBB/TRF-precision escalation, and its resolution (Cooper: "proceed").
- `results/phase_1c/artifacts/fetch_state.parquet` — T4: per-(ticker,session,side) fetch outcome. **Gitignored**, not committed.
- `results/phase_1c/artifacts/t4_fetch_run_summary.json` — T4: 3,605-pair fetch run outcome (3,585/8/12).
- `results/phase_1c/artifacts/t5_unknowns_resolution.parquet`, `t5_unknowns_summary.json` — T5: the 8 unknowns' diagnostic-fetch resolution (8/8 `collection_failure`).
- `results/phase_1c/artifacts/repair_ledger.parquet` — T6: per-pair staged/ingested/verified/collision record. **Gitignored**, not committed.
- `results/phase_1c/artifacts/t6_ingest_summary.json`, `t6_escalation_findings.json`, `t6r1a_collision_scan.json`, `t6r2_sdot_remediation.json` — T6/Amendment 2: ingestion summary, the RILY/SDOT escalations, the collision scan, SDOT's remediation verification.
- `results/phase_1c/artifacts/t7_recompute_summary.json` — T7: flag-flip counts, universe arithmetic (20,802 → 20,951), `repaired_1c` cross-check.
- `results/phase_1c/artifacts/volume_reconciliation.parquet`, `t8_volume_reconciliation_summary.json` — T8: 149-event fetched-vs-scan volume ratios.
- `results/phase_1c/staging/` — Raw + archive-schema-aligned fetch output per (ticker, session), thousands of files. **Gitignored**, not committed.
- `results/phase_1c/charts/01_control_fetch_diffs.html`, `02_healed_sessions_by_offset.html`, `03_volume_reconciliation.html`, `04_universe_waterfall_v2.html` — This phase's four Chart Contract charts.
- `results/phase_1c/digest.json`, `results/phase_1c/REPORT.md` — This phase's digest and written report, covering the base prompt and both amendments.

### `results/phase_2/` (this phase's own outputs)

- `results/phase_2/artifacts/t1_population.json` — T1: spine guard + 2025-slice population and strata.
- `results/phase_2/artifacts/scan_2025_quality.json`, `scan_2025_quality_rows.parquet` — T2: quality-screen summary + row-level detail. Parquet **gitignored**, not committed.
- `results/phase_2/artifacts/high_momentum_inventory_summary.json` — T3a: documents `high_momentum/`'s absence (no per-file inventory exists — nothing to inventory).
- `results/phase_2/artifacts/collection_list_overlap.json` — T3b: `momentum_events_for_collection.parquet` characterization + spine overlap, both directions.
- `results/phase_2/artifacts/window_coverage.parquet`, `window_coverage_summary.json` — T4: the core per-event × offset × source coverage matrix (2025 only) + summary. Parquet **gitignored**, not committed.
- `results/phase_2/artifacts/source_comparison.parquet`, `source_comparison_summary.json` — T5: empty-state overlap-comparison artifact + summary (N/A, `high_momentum` absent).
- `results/phase_2/artifacts/coverage_class.parquet`, `coverage_class_summary.json` — T8: per-event `coverage_class`/`quotes_full_window` for ALL in-scope events, joined into `momentum_events_canonical`. Parquet **gitignored**, not committed — regenerated by `research/phase_2/t8_coverage_class.py` before any fresh `create_view()` call.
- `results/phase_2/charts/01_window_coverage_by_offset.html`, `02_2025_momentum_quality.html`, `03_source_rowcount_comparison.html` — This phase's three Chart Contract charts.
- `results/phase_2/digest.json`, `results/phase_2/REPORT.md` — This phase's digest and written report, covering T1-T5 and the T8 addendum.


## Phase 10b — Randomness of Trade Arrivals Under a Non-Constant Rate (closed 2026-08-13)

Closed as a recorded negative result. No burst timescale established; **no real event was read**.
Report: `results/phase_10b/REPORT.md` (cross-phase copy at
`results/reports/phase_10b_report.md`).

**Prompts**
- `prompts/phase_10b.md` — the phase as originally specified
- `prompts/phase_10b_amendment_1.md` — A10b.1, knee statistic, h/4 blocks, directional band rule
- `prompts/phase_10b_diagnostic_1.md` — DX10b.1, satisfiability audit and excursion structure
- `prompts/phase_10b_amendment_2.md` — A10b.2, four repairs; T1-T2 executed, T3 onward never run
- `prompts/phase_10b_closeout.md` — CO10b, this close-out

**Configs**
- `config/phase_10b.json`, `config/phase_10b_diagnostic_1.json`,
  `config/phase_10b_amendment_2.json`

**Code** (`research/phase_10b/`)
- `pipeline.py` — shared Allan / intensity / rescaling pipeline; sparse Allan verified exactly
  against a dense reference on 200 cases
- `knee.py` — piecewise-linear knee, BIC-selected
- `t0e_cohort_assertion.py`, `t1_plateau.py`, `chart01_plateau.py`
- `t2_controls.py`, `t2r0_departure.py`, `t2r5_controls.py`, `chart04_controls.py`
- `dx1_d0_d1_d2.py`, `dx1_chart09.py`, `dx1_d3a_reuse.py`
- `a2_t1_t2_knee.py`, `a2_charts_11_12.py`, `co_verify.py`

**Artifacts** — `results/phase_10b/artifacts/` (cohort assertion, timestamp resolution, T1 plateau
fit, three control runs, departure direction, block eligibility, unseen-scale validation,
`co_verification.json`); `results/phase_10b/diagnostic_1/artifacts/` (satisfiability audit,
excursion map, envelope-validation block); `results/phase_10b/amendment_2/artifacts/` (per-draw knee
distributions, bias consistency).

**Charts** — `01_plateau_vs_sweep_size`, `04_control_harness` (control gate, six controls),
`diagnostic_1/charts/09_excursion_map`, `amendment_2/charts/11_knee_sampling_distribution`,
`amendment_2/charts/12_bias_consistency`.

**Decisions** — D10 (numbering), D11-D14 (close-out) in `docs/Universe-Decisions.md`.

**Prior art added by this phase**
- Myllymaki, Mrkvicka, Grabarnik, Seijo & Hahn (2017), *Global envelope tests for spatial
  processes*, JRSS-B 79:381-404 — multiplicity-correct curve-vs-simulation testing. Blocked offline.
- Rudemo (1982); Bowman (1984); Shimazaki & Shinomoto (2010) — cross-validated bandwidth selection
  for kernel intensity estimation; establishes held-out fitting as standard practice.
- Gourieroux, Monfort & Renault (1993), *Indirect inference*, J. Appl. Econ. 8:S85-S118 — the route
  recorded and declined.

## Phase 11 — Instrument Validation and the Cost Stack on the Detection Cell (2026-08-15)

First phase to compute a spread as a finding. Stage A validates whether `filtered_quotes` supports
effective-spread measurement at all; Stage B (gated at T4) measures the round-trip cost stack.

**Prompts**
- `prompts/phase_11.md` — the phase as originally specified (v1)
- `prompts/phase_11_amendment_1.md` — A1, repairs the six rows the T0b audit failed, plus Cooper's
  recorded decisions (governing spec, D15, the state-split import, and all five thresholds)

**Configs** — `config/phase_11.json` (24 escalation rows, Cooper thresholds, 27-rung alignment grid,
D15 sources, environment pin)

**Code** (`research/phase_11/`)
- `common.py` — READ_ONLY attach of `main.duckdb` into an in-memory database (structural row-14
  compliance), pinned XNYS session bounds, dev-primary event list with source-folder resolution
- `chart_common.py` — palette and layout helpers, reused unchanged from the approved Phase 9 set
- `t1_quote_table_identity.py` — T1a exchange identity, T1b timestamp semantics
- `t1c_source_columns.py` — T1c `indicators` / `conditions` census, dictionary search, storage order
- `t1_summary.py`, `t2_summary.py` — artifact assembly
- `t2_state_census.py` — T2 state census, run lengths, stale top-of-book, quote-to-trade, spread
- `t3_alignment_sweep.py` — T3 sweep, 27 rungs x 2 clock bases x 2 sessions
- `chart_01.py` … `chart_04.py`

**Artifacts** — `results/phase_11/artifacts/`: `t0b_satisfiability_audit.json` (the v1 audit that
fired row 2), `t0c_satisfiability_audit.json` (the passing re-audit), `t1_quote_table_identity.json`
plus the T1a/T1b/T1c tables, `t2_state_census.json` plus the T2a-T2e tables,
`t3_alignment_sweep.parquet`.

**Charts** — `01_quote_table_identity` (4 panels), `02_nonsensical_state_census` (9 facets),
`03_spread_event_vs_baseline`, `04_alignment_sweep`.

**Decisions** — D15 (coverage-column source), D16 (reference midpoint: contemporaneous
consolidated best quote at δ = 0 on the `sip_timestamp` basis), D17 (quote-state exclusion;
locked carried), D18 (Stage B population; RTH is the decision cell), D19 (both units always;
no baseline spread as a detection-time proxy) — all in `docs/Universe-Decisions.md`.

**Stage B code and outputs** (added after the T4 gate)
- `stage_b_pipeline.py` — the cache builder. Both sides of every ASOF join are materialised
  and no running-frame window survives, for the DuckDB 1.4.4 reasons recorded in the
  open-items register.
- `t5b_pass.py` — the single budgeted pass, event-partitioned into 39 batches with per-batch
  parquet checkpointing and resume; `run_t5b.sh` re-invokes it in fresh processes.
- `t6_effective_spread.py`, `t7_cost_vs_capture.py`, `t8_impact.py`, `t9_report.py`
  (the last carries a row-18 language guard that refuses to write an evaluative report).
- `chart_05.py` … `chart_09.py`.

**Stage B artifacts** — `t5_cache_integrity.json`, `t5b_row26_escalation.json`,
`t4c_tie_audit.json`, `t6_effective_spread.{parquet,json}`, `t6_cells.parquet`,
`t7_cost_vs_capture.{parquet,json}`, `t8_impact.{parquet,json}`, `t8_impact_cells.parquet`,
`t0c_satisfiability_audit_a2.json`, `t0c_satisfiability_audit_a3.json`,
`t0c_focused_reaudit_option_ii.json`, `t2e_i_implied_price.json`.

**DuckDB tables created** (escalation row 14a) — `event_quote_metrics_v1` (9,017,475 rows,
15,252 events, per event × offset × session-minute × segment) and
`event_quote_tie_audit_v1` (54,827 rows). Nothing pre-existing was modified.

**Charts** — `05_effective_spread_at_detection`, `06_cost_vs_capture` (the gate),
`07_cost_capture_grid`, `08_impact_by_participation`, `09_spread_vs_staleness`. Charts 05
and 09 ship as stacked bp/cents panels rather than the specified twin axes (A3-1, Phase 9
chart 06 precedent); the deviation is recorded in each caption.

**Escalations fired** — row 1 (dirty tree, resolved), row 2 (twice: six defective rows in
the v1 audit, then the T4c/row-12 pass-budget contradiction resolved by option (ii)), row 7
and row 20 (both not-a-stop), row 26 (runtime ceiling; one-off bounded exception accepted),
row 30 (tie price error p95 123.047 bp vs 25 bp; option (a) accepted).

**Open items added** — condition-code dictionary absent (with the full observed census);
`indicators` populated not null; withdrawn-quote filter recoverable but not buildable; source parquet
stored reverse-chronological; SIP-vs-direct-feed staleness as a permanent limitation; the canonical
view's live `DISTINCT` coverage columns.

**Prior art carried in** (cited from the prompt, not fetched — D14)
- Holden & Jacobsen (2014), *Liquidity Measurement Problems in Fast, Competitive Markets*, JF
  69:1747-1785 — the nonsensical-state census in T2 is this paper's recommendation applied here.
- Lee & Ready (1991) — quote rule with tick-rule fallback; the 5-second rule is **not** applied.
- Ellis, Michaely & O'Hara (2000); Odders-White (2000) — classification accuracy and the
  unclassifiable share, reported as its own row.
- Bartlett & McCrary (2017) — SIP-versus-direct-feed staleness, a permanent limitation of this
  archive.

## Phase 10c — Clock-Time Sub-Burst Decomposition (Stage 1 approved 2026-08-26; phase closes here)

Sixth method family attempted on the burst-timescale question (five in Phase 10) and the first to
produce sub-bursts that are not a reporting artifact. Stages 2 and 3 were never run; the program
proceeds to Phase 10d. Report: `results/phase_10c/REPORT.md` (cross-phase copy at
`results/reports/phase_10c_report.md`).

**Prompts** (two numbering series on this phase: an "A"-prefixed pair predating Stage 1, then a
plain-numbered "Amendment N" series; "Amendment 1" of the second series is filed under its
descriptive name, not `amendment_1.md` — kept as-is since it's already referenced by that name
elsewhere)
- `prompts/phase_10c.md` — the base phase prompt (Stage 0/0b spec)
- `prompts/phase_10c_amendment_a1.md` — A1, Class E/Class M decision taxonomy
- `prompts/phase_10c_amendment_a2.md` — A2, Stage 0b insertion, D16 void-gate floor
- `prompts/phase_10c_amendment_a2_7_a2_8_resolution.md` — "Amendment 1": A2.7/A2.8 resolution,
  including both revisions (R3 conflict resolution; A2.7 reframed as `A2.7.D17_burst_envelope_boundary`)
- `prompts/phase_10c_amendment_2.md` — session boundary redefinition
- `prompts/phase_10c_amendment_3.md` — threshold-variant handling (carry all 3, never collapse)
- `prompts/phase_10c_amendment_4.md` — closing-print rules, population tier
- `prompts/phase_10c_amendment_5.md` — condition-code dictionary, auction code set proposed
- `prompts/phase_10c_amendment_6.md` — auction rule closure, dictionary relocation
- `prompts/phase_10c_config_guide.md` — per-field derivation reasoning for the config
- `prompts/phase_10c_stage_1.md` — the Stage 1 prompt (T0-T7, escalation table, verification block)

**Config** — `config/phase_10c.json`: `cooper_values` (Class E/M taxonomy), `settled`, `mechanism`,
`gates`, `a2_rules` (D2/D5/D6/D17 registry), `closing_print_rule` (settled {8,15}, scope all trades),
`stage_1` (threshold rule), `dev_sample`.

**Vendor reference** — `docs/massive_trade_conditions.json`: the Massive (formerly Polygon)
trade-condition-code glossary, partial by design (9 codes with full attributes, 6 named with a
single stated attribute); moved here from a force-added entry under gitignored `data/metadata/`
(Amendment 6 section C).

**Code** (`research/phase_10c/`)
- `common.py` — shared plumbing: config/cfg-hash, dev-sample loader, tie-collapse, D1 sweep
  aggregation, log-interval histograms, Poisson peak-finding, session bounds, `assign_segment()`
  (the auction-code-aware segment classifier, Amendment 6), D4 floor derivation
- `s6_audit.py`, `s6_audit_0b.py` — per-stage satisfiability audits
- `t0_landscape.py`, `t0_6_7.py`, `t0_charts.py`, `t0_digest.py` — Stage 0 (T0.1-T0.8)
- `t0b_bimodality.py`, `t0b_charts.py`, `t0b_digest.py` — Stage 0b
- `a3_d2_rule_check.py`, `apply_a2.py`, `apply_a3.py`, `apply_a3_rev2.py`, `apply_option1.py` —
  amendment-application scripts (fast/slow-mode rule comparison, Class-E/M config mutations)
- `a4_boundary_relabel.py` — Amendment 2 (session boundary)
- `a5_variants.py`, `a5_chart.py` — Amendment 3 (threshold variants)
- `a6_conditions.py`, `a6_append.py` — Amendment 4 (closing-print rules)
- `a7_census.py` — Amendment 5 (condition-code census)
- `a8_auction_closure.py` — Amendment 6 (auction rule, real ACET reclassification)
- `t1_subbursts.py` — the original single-kernel/single-variant T1.1-T1.4 run, superseded by Stage
  1's multi-cell pipeline before Amendments 2-6 were applied to it (kept, not deleted)
- `s1_t0_denominator.py` — Stage 1 T0, the 36-vs-37-vs-38 denominator resolution
- `s1_t1_subbursts.py`, `s1_t1_verify.py` — Stage 1 T1, the 9-cell sub-burst extraction and its
  executable-assertion verification
- `s1_t2_anchor_independent.py`, `s1_t2_charts.py` — Stage 1 T2
- `s1_t3_anchor_relative.py`, `s1_t3_charts.py` — Stage 1 T3
- `s1_t4_cross_kernel.py`, `s1_t4_charts.py` — Stage 1 T4
- `s1_t5_descriptive.py` — Stage 1 T5
- `s1_t6_animation.py`, `s1_t6d_full_combined.py` — Stage 1 T6, both candidate layouts then the
  full-sample production under Cooper's chosen layout (combined comparative)
- `s1_t7_tape_review.py` — Stage 1 T7, Row 0 (adapted from `research/phase_10/v4_t7b_tape.py`'s
  proven 5-panel grammar)
- `s1_verification_block.py` — Stage 1's consolidated S5 Verification Block

**Artifacts** — `results/phase_10c/artifacts/` (36 JSON files spanning Stage 0/0b/Stage 1, plus the
per-cell parquets `s1_t1_cells.parquet`, `s1_t1_subbursts.parquet` and the T2-T5 summary tables, all
gitignored/regenerable per SS12); `results/phase_10c/digests/{stage0,stage0b,stage1}_digest.json`.

**Charts** — `results/phase_10c/charts/`: `s0_1-5*`, `b1-5*` (Stage 0/0b), `s1_02_01-04*` (T2),
`s1_03_05-07*` (T3), `s1_04_08-10*` (T4), `s1_05_11*` (T5), `a3_1_variant_anchor_deltas`.
`s1_06_t6_*` (4-event T6 layout samples), `s1_06_animation_full/` (T6d, 56 combined animations,
gitignored) and `s1_07_tape_review/` (T7, 56 five-panel charts, gitignored) are regenerable — their
manifests (`s1_t6d_manifest.json`, `s1_t7_tape_manifest.json`) are the committed record. **139/139
charts Kaleido-verified** stage-wide.

**Decisions** — `A2.7.D17_burst_envelope_boundary` and the `closing_print_rule` ({8,15}, all
trades) in `config/phase_10c.json`; a `docs/Universe-Decisions.md` D3 amendment recording the
session-boundary/auction-assignment rule as the standing convention for future intraday segment
work.

**Escalations / open items** — no escalation row fired in Stage 1's own code (19-row table reviewed
in `s1_verification_block.json`); one population-scope defect found in prior (Amendment 4-6) work
and flagged, not corrected retroactively (BMR, `docs/Open-Items-Register.md`); the eligible-pool gap
(15,299 vs. D14's 20,951) and the `det_ns_*` float64 repair remain open, carried to Phase 10d.


## Phase 10d — Burst Assembly Under a Merge Tolerance and a Run-Length Floor (2026-08-26)

Changes **one thing** relative to 10c: how labelled intervals become burst objects. Everything
upstream is 10c's, read and asserted at run time, never re-derived — the centered clock-time window,
the three kernels with D5 = 8 min primary, the variant grid, the four segments, the per-event derived
data floor, and argmax-void threshold selection with no cutoff. Deliverable is the **attribution**,
not a duration number.

Report: `results/phase_10d/REPORT.md` (cross-phase copy at `results/reports/phase_10d_report.md`).
Digest: `results/phase_10d/digest.json`.

**Prompts** — `prompts/phase_10d.md` (r2, the executable prompt), `prompts/phase_10d_spec.md` (r2,
the design and reasoning record) and `prompts/phase_10c_closing_note_erratum.md`, which corrects four
settled points the r1 drafts inherited from 10c's pre-phase outline rather than its committed config
(window basis, threshold rule, declined-share baseline, causal-debt retirement).

**Config** — `config/phase_10d.json`. Four grids, all pre-registered before any real event was read:
`K ∈ {0,1,2,3,5}`, `d ∈ {0,0.25,0.5,1.0}` decades **added** to the threshold, `min_prints ∈ {2,3,5}`
reference **2**, `sep ∈ {hard_break, bridgeable_count_only}` reference `hard_break`. Identity cell
`K=0, d=0, min_prints=2, sep=hard_break` reproduces 10c bit-exactly.

**Code** — `research/phase_10d/`:
- `assemble.py` — the merge, the separator rule and the run-length floor. The only place 10d changes
  anything; a pure function of the label array with no I/O and no config reads.
- `controls.py` — the T2 control gate, C1–C5, all hard, all passed before any real event was read.
- `t3_counterfactual.py`, `t3_chart.py` — void distribution and the would-be declined share at
  candidate cutoffs, **applied nowhere**.
- `t4_assembly.py` — the grid run. Imports 10c's labelling path (`s1_t1_subbursts.py`,
  `common.py`) by explicit spec rather than by `sys.path`, because `research/phase_10/common.py` and
  `research/phase_10c/common.py` share a module name and shadowing them raises a circular import.
- `t4_descriptive.py`, `t4_tape.py` — break-cause census, per-object/per-event description, timing,
  and the 43-event tape review.
- `t5_attribution.py`, `t5_charts.py` — the attribution and escalation-row evaluation.
- `t6_causal.py` — the causal audit, carried forward unchanged.
- `t2_chart.py` — the control-gate chart.

**Artifacts** — `results/phase_10d/controls/` (C1–C5 + `gate.json`) and
`results/phase_10d/artifacts/` (JSON summaries committed; the parquets — `t4_subbursts.parquet` at
6,811,163 rows, `t4_cell_summary`, `t4_break_cause`, `t5_*`, `causal_audit` — are gitignored and
regenerable per §12, exactly as 10c's are).

**Charts** — `results/phase_10d/charts/`: `01_control_assembly`, `02_void_counterfactual`,
`03_break_cause`, `04_duration_spacing_moveshare`, `06_attribution`, `07_nprints_composition`,
`08_merge_surface`, `09_kernel_variant_consistency`, `10_count_vs_print_count` — 10/10
Kaleido-verified. `05_tape_review/` (43 events, 270 MB) is **untracked and regenerable**, following
10c's `s1_07_tape_review/` convention; `results/phase_10d/artifacts/t4_tape_manifest.json` is the
committed record.

**Decisions** — `docs/Universe-Decisions.md` **D20**, drafted in spec §7 as D15. Renumbered because
Phase 11 had already appended D15–D19 and `CLAUDE.md`'s pointer list, which stops at D14, is stale.
Every other word of the decision is the spec's text verbatim; the renumber is recorded inline and is
open for Cooper.

**Findings** — the run-length floor moves median sub-burst duration **7.17× more** than the merge
tolerance does (+0.3209 vs +0.0838 decades at kernel 8), and the two are separable and mildly
super-additive. The first measurement in the programme of run-break cause: **0.761% of run breaks
involve an `ok=False` interval**, so fragmentation is essentially all real above-threshold gaps and
the separator axis is nearly inert.

**Escalations / open items** — no row fired in 10d's own code. **10d-R0, Cooper's tape review, is
open.** Two upstream defects found and recorded, with no 10c artifact edited: 10c applies no
run-length floor (52.3% of its objects are single-interval), and Stage 1's recorded `config_hash`
`998c2461` is stale by one commit — `39ec87e` edited `config/phase_10c.json` inside Stage 1 before
`692d9d0` produced the T1 artifacts. `cfg_hash()` is also line-ending sensitive and its convention
flipped between Stage 0 and Stage 0b. The eligible-pool gap (15,299 vs D14's 20,951) and the
`det_ns_*` float64 repair, which 10c's map entry carries to Phase 10d, were **not in 10d's prompt
scope** and remain open.
