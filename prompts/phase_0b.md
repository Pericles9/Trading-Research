# Phase 0b — Harness Setup: Data Layer, CLAUDE.md, Table Loads, Dev Sample, Digest Tooling

**Date:** 2026-07-15
**Baseline:** Phase 0a complete (tag `phase-0a-approved`) — repo initialized, 950 files inventoried, zero moves, `docs/Research-Library-Map.md` written. Top blocking finding carried forward: `src/data/db.py` / `ingest.py` / `paths.py` are absent from the top-level checkout despite being described as live in `data/Schema.md`.
**Objective:** Complete Phase 0 of the Operating Plan: recover the data access layer, install `CLAUDE.md`, load `momentum_events`, build the pinned dev sample, and stand up digest/verification tooling.
**Primary success metric:** Dev sample rebuild from committed config produces a byte-identical event list, and digest tooling round-trips on a real digest. (Phase map gate: "Dev sample reproduces; digest tooling round-trips.")

---

## Context & Constraints

- **NEVER write to D:.** Data root `E:\Trading Research\data`. DuckDB at `E:\Trading Research\data\duckdb\main.duckdb`.
- The E: DuckDB currently holds exactly 5 tables (`filtered_trades` 4,899,401,773 rows, `filtered_quotes` 3,775,991,856, `raw_quotes` 1,757,761,017, `collection_stats`, `symbols_metadata`) per `data/Schema.md` (2026-07-14). Any divergence from those counts is an escalation, not a shrug.
- `hawkes-ofi-impact/` and `scanner-epg-momentum/` are independent repos. **Read-only** in this phase: you may search them and read their git history in T1, but you modify nothing inside them, ever.
- Known live `D:\` hardcodes exist (`results/phase_0a/REPORT.md` §5). **Do not execute any of those scripts.** They are quarantined until a remediation phase.
- Do not pull `filtered_trades` or `filtered_quotes` into pandas. DuckDB SQL for everything at scale.
- `momentum_pct` semantics are **not yet known** (that's Phase 1). This phase uses it only as a stratification key — no analysis of it.
- Plan mode first. Hard stop means stop.

---

## Tasks

- [ ] **T0 — Branch, commit prompt + config**
  Cut `phase/0b` from `phase-0a-approved`. Commit `prompts/phase_0b.md` and `config/phase_0b.json` (dev-sample parameters, below) before any other work.

- [ ] **T1 — Locate the data access layer [HARD MID-PHASE GATE]**
  Find `src/data/db.py`, `src/data/ingest.py`, `src/data/paths.py`, and `src/data/prepare_database_split.py`. Search, in order: (a) both nested repos' working trees, (b) both nested repos' full git histories (`git log --all --diff-filter=A -- '*paths.py'` etc.), (c) anywhere else on E: outside `data/`.
  - [ ] T1a — For every copy found: path, repo, commit, last-modified date, and whether its hardcoded defaults match Schema.md's E: paths. If multiple versions exist, diff them and report the differences as facts.
  - [ ] T1b — Independent of the search: open the E: DuckDB read-only with the raw `duckdb` package, list tables, and compare row counts against the Schema.md table above. Post the comparison.
  - [ ] T1c — Commit artifacts. **Post findings and stop.** Cooper decides the hosting model (copy into top-level `src/data/` with a provenance note, vendor from the nested repo, or rewrite). Do not implement any option before that decision.

- [ ] **T2 — Implement the approved hosting decision**
  Execute exactly what was approved in T1c. End state, regardless of option: `python -c "import src.data.db, src.data.ingest, src.data.paths"` succeeds from repo root, and `python -m src.data.ingest --verify-only` runs clean against the E: roots. Record the provenance of every file that lands in `src/` (source path + commit hash) in a header comment and in the decisions log.
  - [ ] T2a — Update `docs/Research-Library-Map.md` for the new files (standing rule).
  - [ ] T2b — Commit.

- [ ] **T3 — Write `CLAUDE.md`**
  Transcribe the block below verbatim to repo root, filling only the two bracketed items with facts established in T1/T2. Do not add, soften, or editorialize. Target under 120 lines.

  ```markdown
  # CLAUDE.md — Standing Constraints (Mom_db Research)

  ## Hard data rules
  - NEVER write to D:. Confirmed failing hardware, migrated off 2026-07-12.
  - Data root: E:\Trading Research\data. DuckDB: E:\Trading Research\data\duckdb\main.duckdb.
  - Env override precedence per src/data/paths.py: MOM_DB_DUCKDB_PATH > MOM_DB_DATABASE_ROOT > default.
  - Live D:\ hardcodes exist in [list from results/phase_0a/REPORT.md §5]. Never execute those files until a remediation phase clears them.

  ## Provenance quarantine
  - filtered/ and momentum_events: Confirmed → the primary research surface.
  - daily/, minute/, second10/, quote_data/: Inferred → baselines and reconciliation only, never headline results, until Phase 6 reconciliation passes.
  - trade_data/: Unknown → do not touch, ever, without explicit instruction.
  - metadata/, market-hours/, symbol-properties/, nautilus_catalog/: Inferred/Unknown → same quarantine as above.
  - src/data/ files vendored from [source repo @ commit] — provenance in file headers.

  ## Standing methodology
  - Event-study before backtest.
  - Effective spread, not quoted. Always cross the spread. Halts = forced hold through the reopen.
  - Lag every feature by realistic pipeline latency at decision time.
  - Time-based splits only, never random. Ticker-blocked splits — no ticker on both sides.
  - Two-tier execution: ALL development runs on the dev sample (dev_events / filtered_trades_dev /
    filtered_quotes_dev; 50 events, seed pinned, built in Phase 0b, NEVER rebuilt or reseeded).
    Full-tier runs only after dev output is reviewed and the config is frozen and committed.
  - DuckDB SQL over pandas. Never materialize filtered_trades (4.9B rows) or filtered_quotes (3.8B rows) into a dataframe.

  ## Code & repo layout
  - Exploratory code: research/phase_{x}/. Promoted code only: src/. Nothing in src/ changes mid-phase.
  - Deterministic, config-driven runs. Every tunable lives in config/phase_{x}.json, committed before the
    run that uses it. Outputs keyed by config hash.
  - hawkes-ofi-impact/ and scanner-epg-momentum/ are independent repos: read-only, never modified from here.
  - research/ is a live Obsidian vault; archive/ is immutable run output. Do not restructure either.
  - Any phase that adds, moves, or removes repo files updates docs/Research-Library-Map.md in the same phase.

  ## Reporting
  - Never post a number without n. Never post a metric without the code path that produced it.
  - Every claim points to a chart showing the underlying distribution (Evidence Standard).
  - Charts: Plotly, standalone HTML, one per file. n per bucket, always. No smoothing unless asked.
    Log axes where data is multiplicative (here, it usually is). Distributions, not just centers.
    Outliers shown, never clipped.

  ## Escalation
  - Hard stop means stop. Do not fix. Do not tune. Do not proceed. Commit state, post the criterion
    and the observed value, wait for instruction.

  ## Pointers
  - All phase prompts follow docs/Agent_Prompt_Standard.md.
  - Strategy context: docs/Mom-DB-Strategy-Research-Program.md — read the referenced section, not the whole doc.
  - Repo map: docs/Research-Library-Map.md. Data layout: data/Schema.md.
  ```

  - [ ] T3a — Verify the pointer paths resolve to real files; if a doc lives elsewhere, fix the pointer (not the doc) and log it.
  - [ ] T3b — Commit.

- [ ] **T4 — Load `momentum_events`**
  Load via the recovered ingest path (`python -m src.data.ingest --dataset momentum_events`) into the E: DuckDB. Then verify: table row count == `filtered_events_power_law_q05.parquet` row count == CSV row count (report all three).
  - [ ] T4a — Post counts only, no analysis: total events, distinct tickers, min/max event date, null count in `momentum_pct`. Deeper universe stats are Phase 2's job.
  - [ ] T4b — Report distinct event count vs. distinct `filtered/` folder count as two numbers side by side. Reconciling any gap is Phase 4's job — do not investigate here, just record it.
  - [ ] T4c — Commit.

- [ ] **T5 — Build the dev sample**
  Parameters from `config/phase_0b.json`: `n_events: 50`, `strata: momentum_pct deciles (10)`, `per_stratum: 5`, `seed: 42`, sampled uniformly within stratum, deterministic ordering before sampling (sort by ticker, date). Only events with an existing `filtered/` folder are eligible (log how many are excluded by that condition).
  - [ ] T5a — Write the 50-row event list to `config/dev_sample_events.csv` and **commit it**. This file is the pin. If a rebuild ever disagrees with it, that is an escalation, not a refresh.
  - [ ] T5b — Materialize `dev_events`, `filtered_trades_dev`, `filtered_quotes_dev` in the E: DuckDB. Report row counts for each and per-event tick counts.
  - [ ] T5c — Rebuild the event list from config in a fresh process; confirm byte-identical to the committed CSV.
  - [ ] T5d — Time one representative dev-tier query (e.g., per-event trade count + minute-bucketed volume across all 50 events). Report wall time against the 60s target.
  - [ ] T5e — Charts 01 and 02 per the contract. Commit.

- [ ] **T6 — Digest tooling + slash commands**
  - [ ] T6a — `research/phase_0b/validate_digest.py`: schema-validates a digest.json against the §11 contract (required fields, `headline_metrics[].chart` present, ≤100 lines).
  - [ ] T6b — `.claude/commands/`: `/digest` (regenerate digest from artifacts), `/verify` (re-run every `reproduce`/repro command in a digest and diff the numbers), `/gate` (print the escalation check table).
  - [ ] T6c — Round-trip test on real data: validate Phase 0a's digest.json, then validate this phase's own digest once written. Both must pass; failures are reported as facts.
  - [ ] T6d — Commit.

- [ ] **T7 — Digest, report, map update**
  `results/phase_0b/digest.json` + `REPORT.md`. Update `docs/Research-Library-Map.md` for everything this phase added. Decisions log gets every micro-decision (search order results, tie-breaks in sampling, any pointer fixes). Surprises field per usual.
  - [ ] T7a — Commit; working tree clean.

---

## Escalation Criteria

Stop and post results. Do not proceed to the next task.

| Condition | Threshold | Action |
|---|---|---|
| Data-layer files not found anywhere (working trees, git histories, E:) | Any of the 3 core files missing everywhere | Hard stop — the access layer must be rewritten, which is a Cooper decision |
| Multiple conflicting versions of a data-layer file | Diffs are not trivially explainable (e.g., only path defaults differ) | Hard stop at T1c gate with the diff — do not pick one |
| E: DuckDB row counts vs. Schema.md | Any table differs | Hard stop — the documented baseline is wrong or the DB changed |
| `momentum_events` parquet vs. CSV vs. loaded table counts | Any mismatch | Hard stop |
| `momentum_pct` nulls in `momentum_events` | > 0 | Hard stop — stratification key is broken |
| Events eligible for dev sampling | < 50 in any decile's reachable pool such that 5-per-stratum is impossible | Hard stop — post per-decile eligible counts |
| Dev sample rebuild (T5c) | Not byte-identical | Hard stop |
| Representative dev-tier query (T5d) | > 600s (10× target) | Hard stop — dev tier is not serving its purpose; post timing breakdown |
| Digest round-trip (T6c) | Phase 0a digest fails validation | Report the failure as a finding; do not edit Phase 0a's digest; continue |

---

## Output Files

| File | Description | Status |
|---|---|---|
| `config/phase_0b.json` | Dev-sample parameters (n, strata, seed) | [ ] |
| `config/dev_sample_events.csv` | The pinned 50-event list — committed, never regenerated | [ ] |
| `results/phase_0b/artifacts/data_layer_search.json` | T1 findings: every copy found, path, commit, diffs | [ ] |
| `results/phase_0b/artifacts/duckdb_state_check.json` | T1b table/row-count comparison vs. Schema.md | [ ] |
| `results/phase_0b/artifacts/momentum_events_load.json` | T4 three-way count verification | [ ] |
| `results/phase_0b/artifacts/dev_sample_build.json` | Per-stratum eligible pools, selections, row counts, T5d timing | [ ] |
| `CLAUDE.md` | Standing constraints, transcribed per T3 | [ ] |
| `research/phase_0b/validate_digest.py` | Digest schema validator | [ ] |
| `.claude/commands/{digest,verify,gate}.md` | Slash commands | [ ] |
| `results/phase_0b/charts/01_dev_sample_stratification.html` | Per contract | [ ] |
| `results/phase_0b/charts/02_dev_sample_event_sizes.html` | Per contract | [ ] |
| `results/phase_0b/REPORT.md`, `digest.json` | Per standard | [ ] |

New DuckDB tables (E:): `momentum_events`, `dev_events`, `filtered_trades_dev`, `filtered_quotes_dev`.

---

## Chart Contract

| # | File | Question | Encoding | n shown | Looks like this if wrong |
|---|---|---|---|---|---|
| 01 | `charts/01_dev_sample_stratification.html` | Does the 50-event dev sample span the full momentum_pct distribution? | x=momentum_pct (log), full-universe ECDF + histogram; dev-sample events as strip/rug overlay, colored; decile boundaries as vertical lines | Full n in title; eligible + selected n per decile annotated | Dev points cluster in a few deciles; one or more deciles empty |
| 02 | `charts/02_dev_sample_event_sizes.html` | How large are dev events in tick rows — will dev-tier iteration meet the <60s target? | x=event (sorted), y=trade + quote row counts (log), bar or strip, cumulative line secondary | Per-event rows in hover; total in title | A handful of events hold ~all rows — dev runtime dominated by outliers |

---

## Verification Block

Every headline number in the report carries source + repro per §10. Required rows at minimum: the three-way `momentum_events` count check, dev-table row counts, T5c byte-identity check (as a hash comparison), T5d timing, and the T1b DuckDB-vs-Schema.md comparison. Filter waterfall required for dev-sample eligibility (events in → with folders → per-decile pools → selected).

---

## Reporting

On completion, post: (1) T1 findings summary with the approved hosting decision restated, (2) DuckDB state table before/after this phase (tables + row counts), (3) dev-sample stratification table (decile, eligible n, selected n), (4) T5d timing, (5) escalation check table, (6) output file table with status, (7) commit list. Every claim cites its chart or artifact. No recommendations.

---

## Approval Gate

Do not begin Phase 1 (filter forensics) or any follow-on work until Cooper has reviewed results and given explicit approval. Tag `phase-0b-approved` on merge.
