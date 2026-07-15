# Phase 0a — Repo Inventory, Organization & Library Map

**Date:** 2026-07-14
**Baseline:** None — this is the first executed phase. Precedes Phase 0 (harness setup) from the Operating Plan §6.
**Objective:** Inventory the research repo, reorganize it into the directory contract, and produce a complete, human-readable map of every file so all later phases start from a documented, clean slate.
**Primary success metric:** `docs/Research-Library-Map.md` exists, covers 100% of repo files (per the coverage rules in T4), and zero files are lost or orphaned by the reorganization (verified by before/after inventory diff in T5).

**Standard deviation notice (required per Agent_Prompt_Standard.md):** This phase produces no measurements, no backtest, and no data analysis. §7 (per-event charts) and §9 (chart contract) are explicitly empty — there is no distribution to show. The Evidence Standard is satisfied instead by the Verification Block (§10): every claim about the repo state must be backed by the inventory artifacts and git history.

---

## Context & Constraints

`CLAUDE.md` does not exist yet (it is a Phase 0 deliverable), so the standing rules are inlined here. Treat every one as hard.

- **Never write to D:.** Confirmed failing hardware. Data root is `E:\Trading Research\data`. DuckDB is `E:\Trading Research\data\duckdb\main.duckdb`.
- **Do not touch the data root at all in this phase.** No reads, no writes, no reorganization of anything under `E:\Trading Research\data`. This phase is about the *code and docs repo only*. The data layout is documented separately in `Schema.md` and is out of scope.
- **No deletions.** Files may be moved (`git mv` only) or left in place. Nothing is deleted, ever, in this phase. Candidates for deletion go in a list for Cooper.
- **No content edits except approved path fixes.** File contents are not modified, with one exception: import statements or path strings that break *because of an approved move*, and only the specific fixes listed and approved in T2.
- **`src/` is read-only for moves.** Nothing inside `src/` is moved or renamed. It may be read for the map and reference-scan.
- **Plan mode first.** Read this prompt, post your execution plan, wait for approval before any write.
- Hard stop means stop. Do not fix, do not tune, do not proceed.

---

## Tasks

- [ ] **T0 — Branch and commit prompt**
  Cut `phase/0a` from main. Commit `prompts/phase_0a.md` before any other work. No config file for this phase — organization only; note that in the commit message.

- [ ] **T1 — Read-only inventory pass**
  Walk the full repo (exclude `.git`, any virtualenvs, `__pycache__`, node_modules, and anything under the data root). Write `results/phase_0a/artifacts/inventory_before.json` with one record per file: relative path, size in bytes, extension, last-modified timestamp.
  - [ ] T1a — Build a reference map: for every `.py` file, list the imports and any hardcoded path strings it contains that point at other repo files. Write to `results/phase_0a/artifacts/reference_map.json`. This is the safety net for T3 — a file cannot be moved until every reference to it is known.
  - [ ] T1b — Report the total file count (excluding `results/**/artifacts` and `results/**/charts`, which are counted but described at folder level only). If this count exceeds the escalation threshold, stop per the table below.
  - [ ] T1c — Commit.

- [ ] **T2 — Reorganization proposal [HARD MID-PHASE GATE]**
  Post a move-map table to chat: current path → proposed path → one-line reason → every reference (from T1a) that the move would break → the exact one-line fix for each. Target layout is the directory contract from the Operating Plan §2.2:

  ```
  prompts/          config/           research/phase_{x}/
  src/              docs/             results/phase_{x}/
  ```

  Rules for the proposal:
  - Loose scripts at repo root, orphaned notebooks, and exploratory code go under `research/` (grouped by topic, or `research/legacy/` if their phase is unknowable).
  - Docs and specs go under `docs/`.
  - Files whose purpose you cannot determine after reading them go in an "unknown — needs Cooper" section of the table. **Do not guess a destination for them.** They stay put until classified.
  - Anything that looks like a deletion candidate (duplicates, empty files, stale outputs) goes in a separate "deletion candidates" list. It is a list, not an action.

  **Stop after posting the table. Do not execute any move until Cooper approves the map explicitly.** This mid-phase gate is a deliberate deviation from the one-gate-per-phase norm: file moves are the one operation in this phase that can silently break things, so the map gets human eyes before execution.

- [ ] **T3 — Execute approved moves**
  `git mv` only, so history follows the file. Apply only the approved map — no additions, no improvisation. Apply only the approved path fixes from the T2 table. One commit per logical group of moves (e.g., "move loose root scripts to research/legacy/"), not one giant commit.
  - [ ] T3a — After all moves: import-check every module under `src/` (`python -c "import <module>"` for each, or equivalent) and confirm zero import errors. Log the result.
  - [ ] T3b — Commit.

- [ ] **T4 — Write the Research Library Map**
  Write `docs/Research-Library-Map.md`. This file is destined for Cooper's project context in chat, so it must be complete and compact.

  Format:
  - Full directory tree of the repo (post-reorganization), data root excluded.
  - For every file: **1–2 sentence description** of what it is and what it does. Base descriptions on actually reading the file (docstring, header comments, or first ~100 lines) — not on the filename. Descriptions are descriptive only: what the file contains, what reads or writes it if evident. No evaluation, no recommendations.
  - Coverage rules: every file in `prompts/`, `config/`, `docs/`, `research/`, `src/`, and repo root gets its own entry. `results/**/artifacts/` and `results/**/charts/` are described at the **folder level** (one entry per folder: what phase produced it, what it holds). Binary/parquet files are described from name and context — do not open large binaries.
  - Header block at the top: generation date, commit hash it reflects, file count covered, and this standing rule stated verbatim: **"Any phase that adds, moves, or removes repo files must update this map in the same phase."**
  - Size cap: if the map exceeds ~600 lines, stop and propose a grouping convention to Cooper before continuing. A map too big to paste into project context has failed its purpose.
  - [ ] T4a — Commit.

- [ ] **T5 — Verification pass**
  Re-run the T1 inventory to `results/phase_0a/artifacts/inventory_after.json`. Diff against `inventory_before.json`: every file must be accounted for as unmoved, moved (with source→dest), or newly created by this phase. **Zero unexplained disappearances.** Post the diff summary.
  - [ ] T5a — Confirm `git log --follow` resolves history for at least 3 spot-checked moved files.
  - [ ] T5b — Commit.

- [ ] **T6 — Digest and report**
  Write `results/phase_0a/digest.json` per the Digest Contract (§11 of the standard) and `results/phase_0a/REPORT.md`. Populate `decisions_log` with every classification judgment made in T2/T4 (e.g., "put X under research/legacy because no phase reference found"). Populate `surprises` with anything found in the repo that no doc mentions — this field being empty on a first-ever inventory pass would itself be worth a second look.
  - [ ] T6a — Commit. Confirm working tree clean.

---

## Escalation Criteria

Stop and post results. Do not proceed to the next task.

| Condition | Threshold | Action |
|---|---|---|
| Repo file count (per T1b exclusions) | > 300 files | Hard stop — per-file mapping is unworkable at this scale; post count and propose grouping before T2 |
| A move would require editing any file under `src/` beyond a path-string fix listed in T2 | Any occurrence | Hard stop — post the conflict, await instruction |
| Any file references a `D:` path | Any occurrence | Hard stop — post the file list; these must be reviewed before anything else (hardware rule) |
| Files with undeterminable purpose | > 20 files | Hard stop — the repo is less documented than assumed; post the list before proposing moves |
| Import check (T3a) fails after moves | Any error | Hard stop — commit state, post the traceback, do not attempt fixes beyond the approved T2 list |
| Inventory diff (T5) shows an unexplained missing file | Any occurrence | Hard stop — commit state, post the diff, await instruction |

---

## Output Files

| File | Description | Status |
|---|---|---|
| `results/phase_0a/artifacts/inventory_before.json` | Pre-move full file inventory | [ ] |
| `results/phase_0a/artifacts/reference_map.json` | Import/path reference map for all .py files | [ ] |
| `results/phase_0a/artifacts/inventory_after.json` | Post-move inventory | [ ] |
| `docs/Research-Library-Map.md` | Full repo map with per-file descriptions — the deliverable Cooper puts into project context | [ ] |
| `results/phase_0a/REPORT.md` | Written report per the standard | [ ] |
| `results/phase_0a/digest.json` | Machine-readable return path | [ ] |

No files may be written outside these locations and the approved move destinations without posting to chat first.

---

## Chart Contract

None. This phase produces no measurements or distributions. Deviation justified in the header block. The Verification Block below carries the evidence burden instead.

---

## Verification Block

The report must include, in place of metric reproduction:

| Claim | Evidence | Repro |
|---|---|---|
| No files lost | inventory_before vs. inventory_after diff, all rows classified | `python -m research.phase_0a.diff_inventory` (or the equivalent script written in this phase) |
| Moves preserve history | `git log --follow` output for 3 spot-checked files | command per file |
| src imports intact | T3a import-check log, zero errors | the import-check command |
| Map coverage complete | file count in map header == inventory_after count (per coverage rules) | count command |

Every count posted carries the exclusion rules that produced it.

---

## Reporting

On completion, post:
1. Before/after directory trees (top 2 levels).
2. Move summary table: n files moved, n unmoved, n unknown-classification, n deletion candidates (list attached, no action taken).
3. Escalation check table: each criterion, observed value, pass/fail.
4. Verification block.
5. Output file table with status filled in.
6. Commit list.
7. The first ~30 lines of `docs/Research-Library-Map.md` inline, so format can be checked at a glance.

No recommendations. Descriptions of repo state only.

---

## Approval Gate

Do not begin Phase 0 (CLAUDE.md, dev sample, digest tooling, missing table loads) or any follow-on work until Cooper has reviewed the map and the diff and given explicit approval.
