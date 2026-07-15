# Phase 0a Report — Repo Inventory, Organization & Library Map

**Branch:** `phase/0a` | **Commits:** 6 (list below) | **Status:** Complete, awaiting Cooper's review/approval of the map and diff per the phase's Approval Gate.

## 1. Before / after directory trees (top 2 levels)

### Before (start of phase — not yet a git repo)

```text
E:\Trading Research/
├── .venv/
├── archive/
│   ├── CLAUDE.md
│   ├── INVENTORY.md
│   ├── misc/
│   └── runs/
├── data/
├── hawkes-ofi-impact/        [independent git repo]
├── notebooks/
│   ├── CLAUDE.md
│   └── *.ipynb (15 files)
├── research/                 [Obsidian vault]
│   ├── .obsidian/
│   ├── CLAUDE.md
│   ├── alpha-hypotheses/
│   ├── brainstorm/
│   ├── phase_1_context/
│   ├── phase_1_ext_hours/
│   ├── phase_2_signal_forge/
│   ├── phase_3_alpha_hunter/
│   ├── phase_4_campaign/
│   └── *.md (62 files)
├── results/
│   ├── cleanup/, data_inventory/, final_gap_fill/, hardware/,
│   │   ingestion_fixes/, ingestion_run/, momentum_curation/,
│   │   quotes_fix/, rebuild_stage1/
└── scanner-epg-momentum/     [independent git repo]
```

### After (end of phase)

```text
E:\Trading Research/
├── .gitignore                [new]
├── .venv/                    [gitignored]
├── archive/                  [unchanged]
├── data/                     [untouched, gitignored]
├── docs/                     [new]
│   └── Research-Library-Map.md
├── hawkes-ofi-impact/        [unchanged, independent repo, gitignored]
├── notebooks/                [unchanged; *.ipynb gitignored per its own CLAUDE.md convention]
├── prompts/                  [new]
│   └── phase_0a.md
├── research/                 [unchanged, + new research/phase_0a/ subdir]
├── results/                  [unchanged, + new results/phase_0a/ subdir]
└── scanner-epg-momentum/     [unchanged, independent repo, gitignored]
```

## 2. Move summary table

| Metric | Count |
|---|---|
| Files moved (`git mv`) | 0 |
| Files unmoved (stayed in place) | 947 |
| Files newly created by this phase | 5 in `research/phase_0a/`, `results/phase_0a/artifacts/` (×6), `docs/Research-Library-Map.md`, `prompts/phase_0a.md`, `.gitignore` — see Output Files table |
| Unknown-classification files | 0 |
| Deletion candidates (list only, no action) | 4 groups — see below |

**Deletion candidates** (posted in T2, no action taken):
- `results/data_inventory/candle_data_inventory.csv` / `.csv.txt` / `_copy.txt` — 3 byte-identical copies.
- `results/momentum_curation/regenerated_candidate.parquet` / `reproduction_run_a_full_current.parquet` — byte-identical, different names.
- `notebooks/tps_backup_grid.ipynb` — name suggests a superseded backup.
- `archive/misc/stat_validator.py` — self-documented as a "standalone copy" of a `src/backtest/stat_validator.py` that no longer exists anywhere in the checkout.
- Also noted, lower confidence: 4 zero-byte files under `archive/runs/**` (interrupted writes), and 32 groups of byte-identical files within `archive/runs/**` (mostly expected repeated-rerun output, not necessarily cruft).

## 3. Escalation check table

| Criterion | Threshold | Observed | Pass/Fail |
|---|---|---|---|
| In-scope file count | ≤ 300 | 940 at T1 (950 final, including this phase's own outputs) | **FAIL — explicit user override obtained during planning**, logged in `decisions_log` |
| Move requiring `src/` edit beyond approved fix | 0 occurrences | 0 (no `src/` exists in scope; zero moves) | N/A / PASS |
| Files referencing a `D:` path | 0 occurrences | ~50 files total; 8 confirmed live `.py` hardcodes, 3 `.ipynb` hardcodes, 1 out-of-scope sibling-repo doc, ~39 inert archived output metadata | **FAIL — posted per hardware rule, not fixed** (see §4 and T2) |
| Undeterminable-purpose files | > 20 | 0 | PASS |
| Import check (T3a) | 0 errors | vacuous — no `src/` in scope | PASS (by design) |
| Inventory diff unexplained missing | 0 occurrences | 0 | PASS |

## 4. Verification block

| Claim | Evidence | Repro |
|---|---|---|
| No files lost | `results/phase_0a/artifacts/inventory_diff.json`: 947 unmoved, 0 moved, 2 new (this phase's own outputs), 1 changed-in-place (a benign mid-T1 self-correction to `reference_map.json`, explained in `t5_verification.json`), 0 unexplained missing | `python -m research.phase_0a.diff_inventory` |
| Moves preserve history | N/A — T2 approved zero moves. Spot-checked `git log --follow` on 3 pre-existing files instead (`archive/CLAUDE.md`, `research/00-Index.md`, `results/hardware/d_drive_inventory.md`); all resolve cleanly to the T0 baseline commit `78d812a`, as expected for never-renamed files | `git log --follow --oneline -- <path>` |
| `src/` imports intact | Vacuous — no `src/` directory exists within this phase's scope (both nested repos have their own internal module trees under different names) | see `results/phase_0a/artifacts/t3_import_check.json` |
| Map coverage complete | Map header states 950 files covered (265 individual entries + 9 folder-level entries for `archive/runs/`'s other 685 files); matches `inventory_after.json`'s `count: 950` | `python -m research.phase_0a.build_inventory` |

## 5. D:\ findings (hardware rule — posted, not fixed)

Live code with a hardcoded `D:\` path, confirmed via `research/phase_0a/build_reference_map.py`'s AST/regex scan of every in-scope `.py` file, plus manual notebook reads:

| File | Reference |
|---|---|
| `research/phase_1_context/build_scanner_context.py` | `ROOT = Path(r"D:\Mom_db")` |
| `research/phase_2_signal_forge/build_signal_forge.py` | same |
| `research/phase_2_signal_forge/build_signal_forge_v2.py` | same |
| `research/phase_3_alpha_hunter/build_alpha_hunter.py` | same |
| `research/phase_4_campaign/build_campaign.py` | same |
| `research/phase_4_campaign/build_campaign_hpc.py` | same |
| `results/rebuild_stage1/collect_massive_data_v2.py` | `D:\Trading...` |
| `results/rebuild_stage1/run_validation_sample.py` | `D:\Trading...` |
| `notebooks/ITT.ipynb` | `d:\Mom. DB started 11-21-25\data\filtered` |
| `notebooks/VIsualize 5 random (filtered).ipynb` | same |
| `notebooks/regime.ipynb` | same |

Out of scope (sibling repo, noted for completeness): `scanner-epg-momentum/backtest/CLAUDE.md` instructs "Always use `D:\Trading Research\.venv\Scripts\python.exe`" and records its own source-project path as `D:\Trading Research\hawkes-ofi-impact`.

Inert (archived output metadata, not a violation): ~39 files under `archive/runs/**`; `results/hardware/d_drive_inventory.md` and `results/ingestion_run/disk_capacity_measurement.md` are the migration's own documentation.

Full machine-readable detail: `results/phase_0a/artifacts/reference_map.json`.

## 6. The `src/` finding

`data/Schema.md` (last reviewed 2026-07-14, the day before this phase) describes `src/data/db.py`, `src/data/ingest.py`, and `src/data/paths.py` as the live data-access layer that performed the D:→E: migration's ingestion (4.9B+ rows). `research/`'s vault contains ~50 companion docs describing an extensive `src/` codebase beyond just the data layer (models, signals, backtest runners, analytics — a v5 strategy runner, GPU tensor engine, archetype classifiers). `results/ingestion_fixes/investigation_and_fixes.md`, dated 2026-07-11, documents active edits to `src/data/ingest.py` three days before this phase.

**No `src/` directory, and no file named `db.py`, `ingest.py`, or `paths.py`, exists anywhere in the current checkout** — verified by exhaustive search: repo root, both nested repos (exact filename and content grep), `data/` itself, hidden directories. The closest analogue, `hawkes-ofi-impact/data/client.py` (also present in `scanner-epg-momentum`), is a materially different, simpler module with no persistent-file path and no `MOM_DB_*` env-var support.

This phase located and reported this finding; it does not attempt to resolve it. Per the plan approved before execution, this is the highest-priority open item before Phase 0 begins.

## 7. Output files

| File | Status |
|---|---|
| `results/phase_0a/artifacts/inventory_before.json` | Done — 948 files |
| `results/phase_0a/artifacts/reference_map.json` | Done — 15 `.py` files scanned, 8 with live `D:\` hardcodes |
| `results/phase_0a/artifacts/inventory_after.json` | Done — 950 files |
| `results/phase_0a/artifacts/inventory_diff.json` | Done — 0 unexplained missing |
| `results/phase_0a/artifacts/t3_import_check.json` | Done — vacuous by design |
| `results/phase_0a/artifacts/t5_verification.json` | Done |
| `docs/Research-Library-Map.md` | Done — 459 lines, well under the 600-line cap |
| `results/phase_0a/REPORT.md` | Done (this file) |
| `results/phase_0a/digest.json` | Done |

## 8. Commit list

```text
78d812a chore: baseline snapshot pre-Phase-0a reorg
53e589e docs: add phase 0a prompt
c0c4a2d data: Phase 0a T1 inventory and reference-map artifacts
b7be7c5 chore: Phase 0a T3 - approved reorg = zero existing-file moves
02d0acb docs: Phase 0a Research Library Map
c96e214 data: Phase 0a T5 verification - zero unexplained missing files
```

(A 7th commit follows this REPORT.md + digest.json.)

## 9. Chart contract

None — this phase produces no measurements or distributions, per its own chart contract. The Verification Block above carries the evidence burden instead.
