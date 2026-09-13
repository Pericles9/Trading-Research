# CLAUDE.md — Standing Constraints (Mom_db Research)

## Hard data rules
- NEVER write to D:. Confirmed failing hardware, migrated off 2026-07-12.
- Data root: E:\Trading Research\data. DuckDB: E:\Trading Research\data\duckdb\main.duckdb.
- Env override precedence per src/data/paths.py: MOM_DB_DUCKDB_PATH > MOM_DB_DATABASE_ROOT > default.
- **The D:\ hardcode list below is GENERATED, not hand-maintained.** Regenerate and verify with
  `.venv/Scripts/python.exe tools/verify_claude_md_indices.py` (exit 1 on drift). **Run it in T0 of
  every phase.** Hand-maintained indices in this file have gone stale three times — the decision
  pointer sat at D14 against a register at D19 (near-collision at D20), the same pointer said D22 was
  last when D23 had been taken (actual collision, 2026-08-30), and this list carried 11 entries
  against 24 live hardcodes while omitting a file that WRITES to D: (2026-08-31). A list a human
  maintains by hand in a repo this size will be stale again. **Any enumerated list in this file is
  either generated and verified by that script, or it is deleted and replaced by the command that
  produces it.**
- Live D:\ hardcodes exist in: data/collection_scripts/collect_massive_data.py, data/collection_scripts/filter_events_power_law.py, data/collection_scripts/inspect_parquet_columns.py, notebooks/Analysis_Rolling_Hawkes.ipynb, notebooks/Power_Law_Audit.ipynb, notebooks/Regime_Analysis.ipynb, notebooks/Signal_Analysis.ipynb, notebooks/Signal_Lab_Report.ipynb, notebooks/VIsualize 5 random (filtered).ipynb, notebooks/regime.ipynb, notebooks/tps_backup_grid.ipynb, notebooks/univariate_kernel_hawkes.ipynb, research/phase_10c/s1_verification_block.py, research/phase_1_context/build_scanner_context.py, research/phase_2_signal_forge/build_signal_forge.py, research/phase_2_signal_forge/build_signal_forge_v2.py, research/phase_3_alpha_hunter/build_alpha_hunter.py, research/phase_4_campaign/build_campaign.py, research/phase_4_campaign/build_campaign_hpc.py, research/phase_7/t1_d4_sweep.py, results/rebuild_stage1/collect_massive_data_v2.py, results/rebuild_stage1/run_validation_sample.py. Never execute those files until a remediation phase clears them.
  Regenerated 2026-09-10: **22 live hardcodes** (24 → 22 — `research/phase_1c/fetch_pair.py` and
  `src/data/prepare_database_split.py` dropped: their only D: mention is now inside a docstring,
  not executable code). Excluded by the generator and correctly so — `src/data/{db,ingest,paths}.py`
  and `tools/verify_cited_paths.py`, whose only D: mention is a docstring or provenance comment,
  `tools/verify_claude_md_indices.py` itself (read-only gate), and 31 reports/JSON that quote a
  path as a record.

## Provenance quarantine
- filtered/ and momentum_events: Confirmed → the primary research surface.
- daily/, minute/, second10/, quote_data/: Inferred → baselines and reconciliation only, never headline results, until Phase 6 reconciliation passes.
- trade_data/: Unknown → do not touch, ever, without explicit instruction.
- metadata/, market-hours/, symbol-properties/, nautilus_catalog/: Inferred/Unknown → same quarantine as above.
- src/data/ files vendored from D:\Trading Research\src\data\ — uncommitted/untracked working-tree state on that drive (no clean commit hash applies), mtimes 2026-03-14 to 2026-07-13. Provenance in file headers.

## Standing methodology
- **On an archive that retains only selected records, sensitivity analyses are runnable and
  counterfactual re-selection analyses are not.** A *sensitivity* question — how much would the
  answer move if this input were wrong? — needs only what was kept. A *counterfactual* question —
  which records would a different rule have chosen? — needs what was discarded, and this archive
  does not have it (Phase 8 A10.2d for `data/filtered/`; A13's first use for the spine). **Apply
  this test when the method is chosen, not after it fails.** It is one line, and it would have
  re-aimed the vintage-churn design before it was specified: A13 clause (c) survived because it was
  a sensitivity, clauses (a) and (b) died because they were counterfactuals. Same shape as `s_min`'s
  survival — references about *sample size* survive, references about *process shape* do not.
  Added 2026-08-31.
- Event-study before backtest.
- Effective spread, not quoted. Always cross the spread. Halts = forced hold through the reopen.
- Lag every feature by realistic pipeline latency at decision time.
- Time-based splits only, never random. Ticker-blocked splits — no ticker on both sides.
- Two-tier execution: ALL development runs on the dev sample (dev_events / filtered_trades_dev /
  filtered_quotes_dev; 50 events, seed pinned, built in Phase 0b, NEVER rebuilt or reseeded).
  Full-tier runs only after dev output is reviewed and the config is frozen and committed.
- DuckDB SQL over pandas. Never materialize filtered_trades (4.9B rows) or filtered_quotes (3.8B rows) into a dataframe.

## Code & repo layout
- **Commits stage explicitly named paths. `git add -A`, `git add .` and `git commit -a` are not
  used.** The paths staged in a commit are that phase's Output Files table and nothing else. Added
  2026-08-31 after a wildcard stage captured an uncommitted human-authored draft of
  `docs/Agent_Prompt_Standard.md` and put it in an unrelated commit. In a repo that carries
  uncommitted human work, a wildcard stage will eventually capture some of it, and the audit trail
  then says what happened to be dirty rather than what was intended. This mirrors the
  `write_allowlist` discipline that already bounds which paths a phase may write.
- **Git discipline: work on a phase branch, commit at each real checkpoint, push to `origin`
  intermittently rather than hoarding local commits.** Never commit or push directly to `master`;
  merge phase branches to `master` via pull request, never a local `git merge` + push. Never
  force-push a shared branch (`master`, or any `phase/*` already pushed to `origin`) without explicit
  instruction, and never skip hooks or signing (`--no-verify`, `--no-gpg-sign`) without explicit
  instruction. Commit messages describe the *why*, tied to the phase's Output Files table — see the
  explicit-path rule above; run `git status`/`git diff` before every commit to confirm only the
  intended paths are staged. Push after each phase's commits land, after any hard stop is committed,
  and at any other natural checkpoint — a local-only history that only reaches `origin` at the very
  end defeats the audit trail this file already requires everywhere else. Added 2026-09-08.
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
- **D4 Amendment A13 (2026-08-31) — spine numerics may be READ to audit the universe-selection
  function.** Granted because the contamination is already in the universe: `event_volume` built the
  population every phase runs on, and refusing would make that function *permanently unauditable*.
  **(a) Write boundary, not an intent test:** no committed artifact a downstream phase reads may carry
  a spine numeric column under any name, including a transform of one. Permitted outputs are a
  membership boolean, a vintage label, and the selection function's own fitted coefficients — nothing
  relating a spine numeric to a market outcome. **(b)** Any population produced this way is causally
  valid and **not basis-clean**, and carries that sentence. **(c)** Basis sensitivity is **measured**,
  on the same axis as whatever churn the run was for, with the residual spread reported first.
  Consumes no decision number. **First use produced a hard stop:** the spine is the q05 filter's
  *survivors* (`min_volume_threshold` non-null on all 23,268 rows, all above the line), so the
  rejected population is on no table and **the lookahead is unmeasurable from disk**. What was
  recovered: the selection function exactly (R² = 1.0), uncensored residual σ = 1.737 decades, and
  basis churn of **1.44%** at the AMC 1.92× anchor. Full text: `docs/Universe-Decisions.md` D4
  Amendment A13; evidence `results/scope_universe_scan/REPORT.md` §14.
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
- All phase prompts follow docs/Agent_Prompt_Standard.md (**v1.4, adopted 2026-09-12** — supersedes
  v1.3; the v1.4 draft sat unapplied since 2026-08-31 until this approval). Defines the Evidence
  Standard; **The Control Standard** (four controls — negative, positive, null-parameter sweep,
  blindness — for any "real exceeds null" claim; scope conditions on robustness claims; envelope
  invariance as a selection criterion); §3 Plan Authorship; §5 Escalation Criteria (two-tier,
  `HARD STOP`/`LOG`); §9 Approval Gate (`async`/`sync-required`); §10 Chart Contract; §11
  Verification Block; §12 Digest Contract; §13 Git Discipline; and the standing **Retraction
  Sweep** rule (a decision that withdraws a premise carries, in the same commit, a table of every
  citing file marked withdrawn/corrected/unaffected). **Section numbers shifted from v1.3** —
  historical prompts citing old numbers (e.g. `prompts/universe_scan_scoping.md`'s "§10 and §12")
  are bannered record of what was live when written, per the standard's own Retraction Sweep rule,
  and are not corrected retroactively.
- Strategy context: docs/Mom-DB-Strategy-Research-Program.md (v2.0, 2026-08-03 — re-ranked under D5).
- **Standing decisions: `docs/Universe-Decisions.md` is the AUTHORITY. The list below is a
  convenience index and is not to be used to pick the next free decision number** — read the file.
  A stale index that specs reason from is worse than no index: this one sat at D14 while the register
  ran to D19, and a Phase 10d spec drafted its decision as D15 straight into a collision with Phase 11's.
  **Any phase that appends a decision updates this list in the same commit.** Complete as of 2026-08-27:
  - D1 analysis universe · D2 `clean_window` · D3 analysis clock · **D4 tick-only measurement**
    (A9 scope, **A12 cross-session ratios need the boundary flag**) · **D5 strategy surface and
    horizon class** (A11) · D6 burst measurement moves to intensity profiling · D7 detection anchor
    is derived · D8 sub-burst structure vs. the event's own envelope · **D9 sub-bursts from
    locally-normalized log inter-trade intervals** · D10 Phase 10b scoping and numbering ·
    D11 the Allan knee cannot recover a cluster timescale · D12 v3's Allan knee carries
    scale-dependent uncertainty · **D13 D5's premise fails; downstream phases re-anchor** ·
    D14 environment is offline · D15 Phase 11 coverage-column source · D16 instrument reference
    convention · D17 quote-state exclusion · D18 Stage B population and the decision cell ·
    D19 spreads and costs in both units · D20 sub-bursts assembled under a merge tolerance and a
    run-length floor · **D21 threshold-from-trough is closed; the log-interval representation is not**
    (2026-08-27, 10d-R0 fired) · **D22 the scale-space field closes as a detector; the resolution
    floor `s >= 2.26/lambda` survives and is the first derived-not-adopted applicability criterion**
    (2026-08-28, **amended by D23**) · **D23 the causal re-derivation reverses D22's lead
    result; D22's structural fact 2 does not survive a one-sided kernel, fact 1 does**
    (2026-08-30) · **D24 Arm 2 declined and the timing-detector line closes, on a derived
    cost-scaling argument (fixed cost against sqrt(H) movement -- 13.4x the drag at 10 s) and
    an observed horizon gradient running the wrong way in 6 of 6 barrier pairs** (2026-09-02) ·
    **D25 the long thesis is closed at BOTH ends, measured -- intraday by barriers (0 of 90
    cells clear, and below a censoring-matched null in 0 of 30) and day-scale by
    hold-to-horizon markouts (0 of 29 cells, median negative at every horizon, -886 bp at
    T+3)** (2026-09-02) · **D26 the within-session timing line is closed -- above 10 ms both
    channels return the session envelope and nothing else under four controls; below 10 ms
    the structure is order fragmentation on a cohort already unable to measure there; three
    prior headlines (the 30 s crossover, the Allan clustering premise, v3's 128 s knee)
    retracted by control, not by review** (2026-09-09/10) · **D27 the Massive float endpoint
    is banned from any computed quantity** · **D28 fundamentals as-of anchor is a filing's
    acceptance timestamp strictly before t0** · **D29 fundamentals provenance is carried per
    source vintage, not per field** · **D30 fundamentals joins resolve on CIK as of t0, never
    ticker** · **D31 share counts are stored as filed, no basis adjustment at write time** ·
    **D32 no fundamental column goes against any outcome variable under Build F1** ·
    **D33 Build F1's t0 is a tiered construction -- nanosecond anchor for 110 events, minute
    anchor (resolved via event_minute_bars_v2) for 15,259, first-trade fallback (read from
    each event's own filtered/ folder) for 5,582, zero unavailable -- since no single anchor
    covers the ~20,951-event universe** (D27-D33, 2026-09-11, Build F1 pre-flight; tier counts
    confirmed by the actual F1-PF5 run) · **D34 Cooper authorized one-time live research to
    verify Phase 12's LULD parameters against Nasdaq's actual policy -- caught and fixed a
    backwards doubling-boundary direction ($3.00 itself doubles, not excluded) and a
    pre-Amendment-18 regime gap affecting one dev event; D14 and Escalation row 4 stand
    unchanged for every other value and every future phase** (2026-09-13,
    docs/data/luld_plan_reference.md).
  - **Next free number: D35.**
- Repo map: docs/Research-Library-Map.md. Data layout: docs/data/Schema.md (tracked copy of
  record; `data/Schema.md` is a local, untracked mirror — `.gitignore` excludes `/data/` wholly,
  so edit the tracked copy and mirror the change there). Corrected 2026-09-10 — `data/Schema.md`
  had no version history and no backup until the copy of record moved under `docs/data/`.
- `docs/Claude-Code-Operating-Plan.md` **exists** (added 2026-08-13, commit `edfb1ea`; §6 is the phase
  map). The note previously here said it had never existed in this checkout — true when written on
  2026-08-03 per `results/redirect_d5/doc_existence_audit.json`, stale since Phase 10b created it.
  Corrected 2026-08-27.

## Environment

- **Environment is offline.** No package index, no R, no network fetch. Any prompt requiring an
  external package, a reference implementation, or a downloaded artifact must state an offline
  fallback at drafting time. `reuse-before-build` applies only to what is already installed.
  (Added 2026-08-13, A10b.2 A2-T0c. This is why Phase 10b DX10b.1 escalation row 6 fired: the
  global envelope test could not be validated against its R reference implementation.)

- **D14 (Phase 10b close-out, 2026-08-13):** the offline constraint above is a standing decision in
  `docs/Universe-Decisions.md`, not only an environment note.
