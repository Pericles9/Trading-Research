# Research Library Map

**Generated:** 2026-07-15 (Phase 0a), updated 2026-07-15 (Phase 0b — added `config/`, `.claude/`, `src/`, `CLAUDE.md`, and both phases' `research/phase_0b/`/`results/phase_0b/` content)
**Reflects commit:** end of Phase 0b (branch `phase/0b`), post-`phase-0a-approved`
**File count covered:** 987 files — 302 individual per-file entries below + 9 folder-level entries covering `archive/runs/`'s other 685 files, per the coverage rules established in Phase 0a.
**Standing rule:** Any phase that adds, moves, or removes repo files must update this map in the same phase.

This map covers `archive/`, `config/`, `docs/`, `notebooks/`, `prompts/`, `research/`, `results/`, `src/`, `.claude/`, and repo-root loose files. `data/` is excluded per standing rule (documented separately in `data/Schema.md`). `hawkes-ofi-impact/` and `scanner-epg-momentum/` are independent, already-git-tracked sibling projects — not walked file-by-file, but each gets a summary section below so this map isn't blind to a third of the workspace.

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
│   └── dev_sample_events.csv
├── docs/
│   └── Research-Library-Map.md
├── hawkes-ofi-impact/          [independent git repo — out of scope, see summary below]
├── notebooks/
│   ├── CLAUDE.md
│   └── *.ipynb (15 notebooks)
├── prompts/
│   ├── phase_0a.md
│   └── phase_0b.md
├── research/                   [Obsidian vault]
│   ├── .obsidian/
│   ├── CLAUDE.md
│   ├── alpha-hypotheses/
│   ├── brainstorm/
│   ├── phase_0a/
│   ├── phase_0b/
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

## `.claude/`

- `.claude/commands/digest.md` — `/digest`: regenerates the current phase's `digest.json` from its artifacts.
- `.claude/commands/verify.md` — `/verify`: re-runs every repro command in the current phase's digest/report and diffs the numbers.
- `.claude/commands/gate.md` — `/gate`: prints the current phase's escalation check table against live state.
- `.claude/scheduled_tasks.lock` — Harness-managed lock file for scheduled-wakeup state; not phase content.

## `prompts/`

- `prompts/phase_0a.md` — This phase's own instructions (task specification for Phase 0a: repo inventory, reorganization, and library-map generation).
- `prompts/phase_0b.md` — Phase 0b's own instructions (data-layer recovery, `CLAUDE.md`, table loads, dev sample, digest tooling).

## `docs/`

- `docs/Research-Library-Map.md` — This file.

## `src/` (recovered Phase 0b T2 — see `results/phase_0b/artifacts/data_layer_search_d_drive.json` for full provenance)

Did not exist anywhere in this checkout as of Phase 0a. Recovered by locating the only surviving copy at `D:\Trading Research\src\data\` (uncommitted/untracked working-tree state on that drive's own independent git repo — no commit hash applies) and copying `src/data/` only, per `data/Schema.md`'s documented interface. The rest of `D:\Trading Research\src\` (`backtest/`, `models/`, `signals/`, `utils/` — the modules the `research/` vault's companion docs describe) was not copied; only `src/data/` was in scope for this phase.

- `src/__init__.py` — Empty package marker (`"""Quant project source package."""`).
- `src/data/__init__.py` — Empty package marker (`"""Data ingestion and DuckDB access layer."""`).
- `src/data/paths.py` — Central path resolution (`resolve_data_root`, `resolve_database_root`, `resolve_duckdb_path`) with `MOM_DB_DATA_ROOT` / `MOM_DB_DATABASE_ROOT` / `MOM_DB_DUCKDB_PATH` env-var override precedence over hardcoded E: defaults.
- `src/data/db.py` — `get_connection()`: returns a DuckDB connection to the path `paths.py` resolves, creating the parent directory if needed.
- `src/data/ingest.py` — Multi-dataset ingest CLI (`--all` / `--dataset` / `--data-root` / `--db-path` / `--verify-only`); 11 registered loaders (`filtered`, `daily`, `minute`, `second10`, `quote_data`, `momentum_events`, `metadata`, `market_hours`, `symbol_properties`, `nautilus_catalog`, `trade_data`), each independently skip-if-exists.
- `src/data/prepare_database_split.py` — CLI that scaffolds/migrates storage to an external database root, writing a migration manifest and `env.example` template.

## Repo root

- `.gitignore` — Excludes `.venv/`, the top-level `data/` root only (anchored `/data/` — fixed in Phase 0b after an unanchored version also matched `src/data/`), the two sibling repos, `archive/runs/`, `notebooks/*.ipynb`, `/logs/`, and standard Python/cache artifacts from git tracking.
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

