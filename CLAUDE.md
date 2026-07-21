# CLAUDE.md — Standing Constraints (Mom_db Research)

## Hard data rules
- NEVER write to D:. Confirmed failing hardware, migrated off 2026-07-12.
- Data root: E:\Trading Research\data. DuckDB: E:\Trading Research\data\duckdb\main.duckdb.
- Env override precedence per src/data/paths.py: MOM_DB_DUCKDB_PATH > MOM_DB_DATABASE_ROOT > default.
- Live D:\ hardcodes exist in: research/phase_1_context/build_scanner_context.py, research/phase_2_signal_forge/build_signal_forge.py, research/phase_2_signal_forge/build_signal_forge_v2.py, research/phase_3_alpha_hunter/build_alpha_hunter.py, research/phase_4_campaign/build_campaign.py, research/phase_4_campaign/build_campaign_hpc.py, results/rebuild_stage1/collect_massive_data_v2.py, results/rebuild_stage1/run_validation_sample.py, notebooks/ITT.ipynb, notebooks/VIsualize 5 random (filtered).ipynb, notebooks/regime.ipynb. Never execute those files until a remediation phase clears them.

## Provenance quarantine
- filtered/ and momentum_events: Confirmed → the primary research surface.
- daily/, minute/, second10/, quote_data/: Inferred → baselines and reconciliation only, never headline results, until Phase 6 reconciliation passes.
- trade_data/: Unknown → do not touch, ever, without explicit instruction.
- metadata/, market-hours/, symbol-properties/, nautilus_catalog/: Inferred/Unknown → same quarantine as above.
- src/data/ files vendored from D:\Trading Research\src\data\ — uncommitted/untracked working-tree state on that drive (no clean commit hash applies), mtimes 2026-03-14 to 2026-07-13. Provenance in file headers.

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

**Universe rules (Phase 1b, Cooper-approved):**
- Universe membership = inner join to `momentum_events_canonical` WHERE `in_scope = TRUE`. Never aggregate `filtered_trades`/`filtered_quotes` without this join — the tables physically contain out-of-universe rows (1,341 orphan-folder events and non-common instruments).
- Canonical event date = `event_date_canonical`. Never use raw `momentum_events.date` (structurally NULL for all file2 rows).
- Instrument scope: common stock only (all share classes, ADRs), per vendor reference type CS/ADRC. Preferreds, warrants, rights, units, ETFs/ETNs/funds, and unresolved tickers are out of scope. Classification source of record: `results/phase_1b/artifacts/ticker_reference_snapshot.parquet` — never re-query the API for classification.
- Outliers are flags, never deletions. Default exclusion happens in the canonical view. Changing a flag definition is a Cooper decision.
- Dev sample = v3 (`config/dev_sample_v3.json`, seed 42; eligibility = v2's rule + `coverage_class='full_window' AND quotes_full_window=TRUE`). Re-pinned Phase 3 Amendment 1 — v2's eligibility rule predated `coverage_class` (Phase 2 T8) and never screened T-3..T+3 window completeness (15/50 v2 events were `event_day_only`, including one pre-2025 event). v2 (`config/dev_sample_v2.json`) is retired but remains committed as the historical sample. v1 and the un-suffixed `*_dev` tables remain retired — do not read them. Dev tables are materialized from main tables only.
- Coverage is per-side: `trades_ingested` and `quotes_ingested` on the canonical view. Any quote-derived statistic filters on `quotes_ingested = TRUE` and reports the n excluded by that filter. Trades-only events (~1,540-folder population, Phase 4 owns the explanation) are in scope for trade-side work only.
- Session calendar: pinned `exchange_calendars` XNYS only. The federal holiday calendar is banned from all market logic — `collect_massive_data.py` used it and corrupted collection windows (see Phase 1b amendment 3). `market-hours-database.json` remains quarantined pending Phase 4 validation.
- `flag_missing_event_day` (Phase 1c): 149/150 healed and cleared (1 residual, SNWV_2022-10-10, a vendor-fetch failure — still out of scope). `flag_window_calendar_bug`: 1,832/1,849 cleared (1,799 repaired + 33 reclassified — Phase 1c's direct set-difference re-derivation found these carried no real damage, a Phase 1b placeholder); 17 residual (the same vendor-fetch failures plus 4 confirmed-empty thin-trading flanking sessions). Both residual populations remain out of scope / flagged; any use of flanking sessions still filters on `flag_window_calendar_bug` per damaged offset and reports the n excluded.
- Repair provenance: sessions healed in Phase 1c exist as `*_repair_1c.parquet` sibling files inside event folders and are flagged `repaired_1c` on the canonical view. Any future full re-ingest of `filtered/` must include repair siblings. Never re-query the API for healed data — the staged artifacts and repair ledger are the record. Heal writes fill genuine absence only. A pre-insertion collision guard skips any (ticker, session, side) that already has rows — heal never merges, dedupes, or supplements existing collection output. Sessions covered by pre-existing rows are flagged covered but not `repaired_1c`.

## Pointers
- All phase prompts follow docs/Agent_Prompt_Standard.md (v1.3, 2026-07-14) — defines the Evidence
  Standard, §9 Chart Contract, §10 Verification Block, §11 Digest Contract, §12 Git Discipline.
- Strategy context: docs/Mom-DB-Strategy-Research-Program.md.
- Repo map: docs/Research-Library-Map.md. Data layout: data/Schema.md.
