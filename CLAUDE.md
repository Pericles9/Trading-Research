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

## Pointers
- All phase prompts follow docs/Agent_Prompt_Standard.md — no file exists at that path. The only
  copy found anywhere on E: or D: is scanner-epg-momentum/backtest/docs/Agent_Prompt_Standard (1).md
  (v1.1, 2026-05-10, inside the independent scanner-epg-momentum repo). That version does not define
  "§10 Verification Block" or "§11 Digest Contract," both referenced by prompts/phase_0a.md and
  prompts/phase_0b.md — a v1.2 or later likely exists somewhere this search didn't reach. Until it
  turns up, digest.json shape follows the precedent set by results/phase_0a/digest.json.
- Strategy context: docs/Mom-DB-Strategy-Research-Program.md — does not exist anywhere in this
  checkout (E: or D:) under any name found. Not fabricated as a pointer.
- Repo map: docs/Research-Library-Map.md. Data layout: data/Schema.md.
