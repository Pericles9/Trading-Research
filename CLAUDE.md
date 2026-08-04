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
- Universe-flag formulas are defined once in `src/data/canonical.py`; research scripts read flag columns
  off `momentum_events_canonical`, never re-derive them locally (D4 Amendment A9.3, 2026-07-24). The 15
  pre-A9 historical re-derivations of `flag_bad_denominator` are enumerated in
  `results/phase_7/artifacts/d4_retro_sweep.json` and left as-is; the rule is prospective.

## Reporting
- Never post a number without n. Never post a metric without the code path that produced it.
- Every claim points to a chart showing the underlying distribution (Evidence Standard).
- Charts: Plotly, standalone HTML, one per file. n per bucket, always. No smoothing unless asked.
  Log axes where data is multiplicative (here, it usually is). Distributions, not just centers.
  Outliers shown, never clipped.
- Every phase's `REPORT.md` must exist in both locations: the canonical `results/phase_{x}/REPORT.md`
  (the original, written as part of that phase's own commits) and a copy at
  `results/reports/phase_{x}_report.md` (cross-phase browsing folder, flat namespace). Copy, never
  move — the phase-folder copy stays the source of truth. Added 2026-07-23.

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
- **D4 (Phase 6c Amendment 8, 2026-07-24) — spine numeric columns permanently quarantined from computation.** Defect #4: `momentum_events`' numeric columns carry inconsistent adjustment bases, per ticker AND per column within the same row (confirmed via an independent price-free volume cross-check — AMC, a price-ratio-*passing* control, has price factor 5.24 vs. volume factor 10.06). Every numeric OHLC/volume column on the spine (`prev_close`, `open`, `high`, `low`, `close`, `event_open`, `event_high`, `event_close`, `event_volume`, any later-discovered price/size column) is diagnostic-display only — never an input to a computed quantity, in any phase, regardless of whether that event passes a price-ratio check. All measured quantities come from `filtered_trades`/`filtered_quotes` exclusively. Sole exception: `momentum_pct` remains the universe-selection/stratification variable (scale-invariant per row) — but it inherits the vendor's RTH-scoped, adjusted-basis high forever, so every premarket/extended-hours finding is conditional on that selection boundary. This supersedes Amendment 5's price-only tick-anchor authorization — D4 covers every spine numeric column, permanently, not just price. Full text: `docs/Universe-Decisions.md` D4. **D4 Amendment A9 (Phase 7, 2026-07-24):** `flag_bad_denominator` (`prev_close < floor OR momentum_pct >= cap`, `src/data/canonical.py`) is inside D4's `momentum_pct` exception (A9.1, denominator-reliability guard); the quarantine also reaches pre-ingestion `candidate_scan_inputs` files prospectively (A9.2); universe-flag formulas are defined once in `canonical.py` and never re-derived in research scripts (A9.3, also under Code & repo layout).
- **ETH-dominant flag (Phase 7 T2, 2026-07-24) — two additive canonical-view columns.** `momentum_events_canonical` (stage `t8`) carries `flag_eth_dominant_t0` (BOOLEAN, TRUE for the 736 D1 events whose T=0 tick rows are >50% outside the XNYS regular session, `excluded_share > 0.5`; FALSE otherwise) and `t0_eth_row_share` (DOUBLE, that share — **populated only for the 736 flagged events, NULL for every other row**, a deliberate zero-full-table-pass consequence). Both are tick-derived (not spine OHLC/volume) so **not** D4-quarantined. The flag is an annotation, not a universe filter: it does not enter `in_scope`, and no measurement excludes flagged events by default — exclusion is a per-phase Cooper decision. Verification/sensitivity: `results/phase_7/`.
- **D4 Amendment A12 (Phase 9, 2026-08-03) — being tick-derived does not certify a ratio across a session boundary.** Raw tick prices are stored as collected, so a corporate action between two sessions changes the basis between them exactly as it does on the spine. Any phase computing a cross-session ratio, level change, or return **carries a magnitude flag and reports the statistic with and without the flagged set**. Untrimmed stays primary; flagged events are reported as their own row, never dropped. **Denominators count** — a ratio whose *denominator* spans the boundary is covered even when the numerator does not (Phase 9's `retrace_excursion` denominator `H − A` spans (T−1,T0), so the flag applies at every horizon including same-day). Why it is mandatory: on the pooled `t0_close→t1_close` markout the median is robust (−0.0278 → −0.0284) but the **mean simple return flips sign, +3.73% → −1.53%**, in 10 of 12 headline cells. `flag_cross_session_extreme` (= `|log(p_later/p_earlier)| ≥ ln 1.8`, **magnitude only — not a corporate-action classifier**) lives in `results/phase_9/artifacts/t1_cross_session_flags.parquet`, per (event, session-pair), **not** in `canonical.py`. Full text: `docs/Universe-Decisions.md` D4 Amendment A12.
- **Three cross-phase flags live in phase artifacts, not on the canonical view** — `flag_has_dup_prints` (6b `event_index_v2`), `flag_possible_row_cap` (Phase 8 `a101_labels`), `flag_cross_session_extreme` (Phase 9 `t1_cross_session_flags`). Each was homed there because "nothing in `src/` changes mid-phase" barred a `src/` write at the time. They are the standing exceptions to A9.3's define-flags-once-in-`canonical.py` rule. Join to the artifact; do not re-derive. Promotion is an open Cooper decision (`docs/Open-Items-Register.md`).

## Strategy surface (D5)

- Selected surface: **intraday post-trigger, long-only, burst-scale horizons.**
- **Long-only.** Do not specify, implement, or measure short-side or fade variants. Do not implement SSR or borrow logic.
- **Measurement anchors are burst-relative by default.** Any session-relative or day-relative anchor — session open, previous close, session high, session close — must be named and justified in the phase prompt *before* it is used. An unjustified day-scale anchor is an escalation, not a style choice.
- **Every feature is computed as of decision time minus realistic pipeline latency.** Lag is baked into research, not added later in production.
- **The end-detector is a first-class deliverable.** Exit research is budgeted at least equally with entry research. Under a long-only strategy on a bull-to-bear flip, exit timing dominates variance and ruin risk.
- The Phase 6 / 6b session-anchored decay figures are archive. They are not the operative latency budget.
- Full text and scope: `docs/Universe-Decisions.md`, D5.

## Pointers
- All phase prompts follow docs/Agent_Prompt_Standard.md (v1.3, 2026-07-14) — defines the Evidence
  Standard, §9 Chart Contract, §10 Verification Block, §11 Digest Contract, §12 Git Discipline.
- Strategy context: docs/Mom-DB-Strategy-Research-Program.md (v2.0, 2026-08-03 — re-ranked under D5).
- Standing decisions: docs/Universe-Decisions.md — D1 analysis universe, D2 `clean_window`, D3 analysis
  clock, D4 tick-only measurement (**A12: cross-session ratios need the boundary flag**, 2026-08-03),
  **D5 strategy surface and horizon class** (2026-08-03).
- Repo map: docs/Research-Library-Map.md. Data layout: data/Schema.md.
- `docs/Claude-Code-Operating-Plan.md` is cited by prompts/phase_0a.md, prompts/phase_0b.md and
  docs/Research-Library-Map.md but has never existed in this checkout — Cooper holds it externally.
  Gap confirmed 2026-08-03, `results/redirect_d5/doc_existence_audit.json`.
