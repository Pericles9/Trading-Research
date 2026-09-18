# Research Library Map

**Generated:** 2026-07-15 (Phase 0a), updated 2026-07-15 (Phase 0b — added `config/`, `.claude/`, `src/`, `CLAUDE.md`, and both phases' `research/phase_0b/`/`results/phase_0b/` content), updated 2026-07-16 (Phase 0c — added `config/phase_0c.json`, `prompts/phase_0c.md`, two untracked `docs/` entries, and `research/phase_0c/`/`results/phase_0c/` content), updated 2026-07-16 (Phase 1 — added `config/phase_1.json`, `prompts/phase_1.md`, `docs/Agent_Prompt_Standard.md` now tracked at v1.3, `docs/Mom-DB-Strategy-Research-Program.md` now tracked, and `research/phase_1/`/`results/phase_1/` content), updated 2026-07-18 (Phase 1b — added `config/phase_1b.json`, `config/dev_sample_v2.json`, four `prompts/phase_1b*.md` (base + 3 amendments), `src/data/canonical.py`, `.secrets/` gitignore entry, and `research/phase_1b/`/`results/phase_1b/` content), updated 2026-07-20 (Phase 1c — added `config/phase_1c.json`, three `prompts/phase_1c*.md` (base + 2 amendments), `src/data/canonical.py` extended (`repaired_1c` column), and `research/phase_1c/`/`results/phase_1c/` content; `filtered/{event}/*_repair_1c.parquet` sibling files noted as a new data/ pattern, not individually catalogued per data/'s standing exclusion)
**Phase 8 catch-up (2026-08-01):** the per-file catalog below reflects the repo through end of Phase 1c and was **not maintained per-phase for Phases 2–7** (a pre-existing lapse in the standing rule, not created by Phase 8). Phase 8's own additions are recorded at folder level in the "Phase 8 additions" section immediately below; Phases 3–7 additions remain un-backfilled and are a known gap.

**Reflects commit:** per-file catalog = end of Phase 1c (branch `phase/1c`), post-`phase-1b-approved`; folder-level Phase 8 addendum = `phase-8-approved`; folder-level D5-redirect and Phase 9 addenda = `phase-9-approved` (2026-08-03), the commit at which both lines were integrated onto `master`
**File count covered:** ~1132 files — ~417 individual per-file entries below + 9 folder-level entries covering `archive/runs/`'s other 685 files, plus `results/phase_1c/staging/`'s thousands of gitignored fetch-output files (folder-level, not catalogued individually), per the coverage rules established in Phase 0a.
**Standing rule:** Any phase that adds, moves, or removes repo files must update this map in the same phase.

This map covers `archive/`, `config/`, `docs/`, `notebooks/`, `prompts/`, `research/`, `results/`, `src/`, `.claude/`, and repo-root loose files. `data/` is excluded per standing rule (documented separately in `data/Schema.md`). `hawkes-ofi-impact/` and `scanner-epg-momentum/` are independent, already-git-tracked sibling projects — not walked file-by-file, but each gets a summary section below so this map isn't blind to a third of the workspace.

---

## Phase 13 addendum — fundamental partition test (folder-level; branch `phase/13`, 2026-09-13)

Cut from `master` once Build F1's PR #5 merged. Executes D32 Amendment A1's gating sentence
(pre-`t0` partitions vs. the round-trip cost stack), approved by Cooper 2026-09-13 with two
amendments: T3b/T3c run undirected, and no split is evaluated against a kill-condition margin
("exploratory, no kill condition") — see `prompts/phase_13.md`'s Approval Gate section.

- `prompts/phase_13.md` — the plan, translated from the architect's signed-off proposal into
  `Agent_Prompt_Standard.md` v1.4 format, reconciled against actual repo state before posting.
- `config/phase_13.json` — entry reference (`t0`), horizon grid (5/15/30/60 min), per-event cost-unit
  source (`event_quote_metrics_v1`, not Phase 11's population aggregate), split definitions.
- `research/phase_13/common.py` — shared config/DuckDB-connection plumbing.
  `FUNDAMENTALS_ROOT` routed through `resolve_data_root()` from the start (the class of bug Build F1
  hit and fixed 2026-09-12/13 — caught here before it could repeat, not after).
- `research/phase_13/t1_build_p0.py` — T1, the population-scale outcome. Per-event MFE/MAE from `t0`
  at 4 horizons, in units of that event's own round-trip cost (not a single global constant).
  **`minute_index` convention checked directly, not assumed:** both `event_minute_bars_v2` and
  `event_quote_metrics_v1` key it as minutes-since-04:00-ET, continuous across premarket/rth/post —
  confirmed against a known event before being relied on. **Bulk single-join design, not per-event
  point queries** — a single-ticker filtered query against `event_minute_bars_v2` (46M rows) was
  observed to be pathologically slow during reconciliation; the bulk join runs in well under the
  20-minute sleep window used to wait for it. Run and verified: round-trip cost located for
  15,252/20,951 events (72.8%); minute-bar coverage 15,763/20,951 (75.2%) — **this number exactly
  matches Build F1's own `a102_detection_anchors.parquet` row count**, meaning `event_minute_bars_v2`
  covers a specific historical Phase 8 cohort, not the full Build-F1 universe. Reported plainly
  (escalation row 5, LOG tier, fires at 75.2% < 80%), not silently absorbed.
  `results/phase_13/artifacts/p0_outcome.parquet` (gitignored, regenerable),
  `p0_coverage_summary.json` (tracked).

- `research/phase_13/t2_arm_zero.py` — T2, the price-decile control arm. No fundamental data at all —
  the competing explanation T3 must be read against (cheap stocks file more, dilute more, reverse-split
  more, and cost more to trade, so a fundamental split can be a price split in different clothes).
  `results/phase_13/artifacts/t2_arm_zero_summary.json` (tracked). Run: decile 0 (cheapest) shows the
  highest median MFE cost-multiple at every horizon (1.43x -> 2.66x, 5min -> 60min); no clean
  monotonic gradient in the middle deciles.
- `research/phase_13/t3_partitions.py` — T3, the three fundamental splits, cross-cut by event year and
  by detection-price decile exactly as `config.cross_cuts` specifies (same decile T2 uses, not a
  coarser bucket). A cell below `config.cross_cuts.min_cell_n_log_threshold` (200) is flagged rather
  than reported at equal weight — 344-472 of ~560 cells per split fall below that floor, a direct
  consequence of the year x decile x split-value granularity, reported plainly as a LOG-tier surprise,
  not hidden by coarsening the cut. **Quality-gating fix, caught before writing any split, not after:** `flg_dilution_form_before_t0` and `spl_reverse_split_365d`
  both default to `False` when their quality column reads `unavailable` (confirmed by direct
  crosstab — 248/20,951 for `flg_`, 12,219/20,951 — 58% — for `spl_`), so splitting on the raw
  boolean would fold "we don't know" into the "no dilution"/"no reverse split" side. Both splits are
  gated to quality-known rows only (`observed`, plus `no_filings_in_window` for `flg_`, a genuine
  negative not a missing value); excluded events are counted and reported, never silently dropped.
  T3b (share-turnover proxy) is a new construction: event-day tick volume
  (`event_minute_bars_v2`, `session_offset=0`) over shares outstanding, split-adjusted by
  `spl_last_split_ratio` when `spl_last_split_ns` falls strictly between `shs_asof_ns` and `t0_ns`
  (1,741/20,951 events needed the adjustment); split at the population median (11,971 events have a
  defined turnover value, 8,980 don't and are excluded rather than mis-binned). T3a keeps the
  pre-registered direction from the signed-off proposal; T3b/T3c are undirected, both tails reported,
  no pass/fail language anywhere in the script or its output.
  `results/phase_13/artifacts/t3_partition_summary.json` (tracked).

- `research/phase_13/{chart_common,chart_01..chart_06}.py`, `results/phase_13/charts/01-06*.{html,png}`
  — the Chart Contract, all 6 charts, kaleido-verified. Chart 01 surfaced a hard temporal cutoff in
  `event_minute_bars_v2`/`event_quote_metrics_v1`: 2020-2024 sit at exactly 100% minute-bar coverage,
  2025 at exactly 0% (5,188/5,188 events, zero bars) -- not a scattered gap, and exactly what makes
  Build F1's `a102_detection_anchors.parquet` row count (15,763) equal the 2020-2024 sum. Charts 03-05
  share a `small_multiples_split_chart()` builder (year x price-decile grid, horizon/metric buttons);
  chart 06 is the population-aggregate one-look comparison with no reference line, no ranking.
- `research/phase_13/verify_partition_test.py` — 7 checks, all pass: P0 coverage recomputed directly;
  every split's cross-cut cell n's conserve against an independent recount; no spine numeric column
  (D4) or fundamental-as-outcome-input (D32/A1); no chart or artifact declares a pass/fail verdict
  (a negation- and check-context-aware text scan, refined twice after it correctly caught real false
  hits on its own first runs against actual chart/report text); every artifact's `config_hash` matches;
  `kill_condition.enabled` confirmed `false`.
- `results/phase_13/{digest.json, REPORT.md}` + `results/reports/phase_13_report.md` — phase complete
  per the Digest Contract, `status: "complete"`, gate mode `sync-required`. T4 (tick-level confirmation)
  stays conditional and Cooper-gated, not required for this phase's own completion.

**Built:** T0 (branch, config), T1 (P0 outcome), T2 (arm zero), T3 (fundamental partitions), T5
(charts, Verification Block, digest, REPORT.md). **Not built, by design:** T4 (conditional tick
confirmation -- only runs if Cooper names a specific cross-cut after reviewing this phase's charts).

**CLOSED, 2026-09-14 -- read this before trusting any number above.** Cooper triggered T4
(tick-level confirmation, targeting T3b) after all. It found a real, one-directional look-ahead
bias in T1's window selection (`t1_build_p0.py`): the window always runs up to 60 seconds past the
labeled horizon, inflating every MFE/MAE figure above by a median 19.7% of the horizon at 5 min,
shrinking to 1.6% at 60 min -- T1's coverage stats are the sole exception. Cooper's decision:
**close as read, uncorrected** -- defensible because this phase was already exploratory with no
kill condition, so nothing here ever hinged on the exact numbers. New files:
`research/phase_13/{t4_tick_confirm,t4b_lookahead_diagnosis}.py`,
`results/phase_13/artifacts/t4b_lookahead_diagnosis.json`. Full record:
`docs/Universe-Decisions.md` D37, `results/phase_13/REPORT.md` §10.

---

## Build F1 addendum — fundamental data and float layer, pre-flight (folder-level; branch `build/fundamentals-f1`, 2026-09-11)

Unnumbered work unit (see `07af342`'s exact-stem convention, `tools/verify_cited_paths.py`), not a
numbered phase — no `research/phase_{n}/`/`results/phase_{n}/` pairing applies. Branched from
`phase/10e`, not `master`: `master`'s `docs/Universe-Decisions.md` does not yet carry D24–D26 (an open
pull request merging `phase/10e` into `master` is unmerged as of this addendum).

Files added, pre-flight only (F1-T0 through F1-T6 have not run yet):

- `prompts/fundamentals_f1.md` — the work order, reconciled against actual repo state before any task
  ran (no `event_id`/`t0` spine column exists, the companion scoping note referenced by the original
  draft does not exist, D14 as written has no network carve-out).
- `research/fundamentals_f1/common.py` — shared config/DuckDB-connection/identity-key/t0-tier plumbing.
  `event_id()` reused verbatim from `research/phase_10/common.py:215`.
- `config/fundamentals_f1.json` — frozen config skeleton; `cooper_pending` block holds the two
  thresholds (`filed_stale_days`, `shs_quality_coverage_floor`) that must be set before F1-T4 runs.
- `docs/data/fundamentals_sources.md` — tracked provenance doc for `data/raw/fundamentals/` and
  `data/fundamentals/` (both under the wholly-gitignored `/data/`), per the same convention as
  `docs/data/Schema.md`.
- `docs/Universe-Decisions.md` — **D14 Amendment A1** (scoped network exception for F1-T2/F1-T3) and
  **D27–D33** (the work order's DF-1..DF-6 registered, plus D33: the tiered t0 construction, a new
  artifact — `t0_spine.parquet` — not in the original draft). `CLAUDE.md`'s decision index updated in
  the same commit; next free number is now **D34**.
- `.gitignore` — added `results/fundamentals_f1/artifacts/*.parquet`, matching the existing
  `results/scale_field/artifacts/*.parquet` rule for non-`phase_*` work units.
- `research/fundamentals_f1/t0_assemble.py` — F1-PF5, builds `t0_spine.parquet` (gitignored parquet,
  20,951 rows) and `t0_assemble_summary.json` (tracked). Run and verified: tier counts
  `nanosecond_poll1`=110, `minute_a102`=15,259, `first_trade_fallback`=5,582, `unavailable`=0.
- `research/fundamentals_f1/t0_restatement_test.py` — F1-T0, the restatement gate test. Run and
  verified: escalation row 1 fires (`t0_restatement_test_summary.json`) — Massive's financials
  endpoint is not point-in-time via `filing_date`.
- Empty skeleton directory: `results/fundamentals_f1/charts/`.
- `data/raw/fundamentals/massive/2026-09-11/t0_restatement_test/` — raw archive (gitignored under
  `/data/`), two companies' full unfiltered financials history plus a fetch manifest.
- `prompts/fundamentals_f1_amendment_a1.md` — Amendment F1-A1 (2026-09-12): named the gap F1-T0 left
  (one vendor record per period, but which vintage?) and specified F1-T0f/F1-T0g to close it.
- `research/fundamentals_f1/t0f_t0g_disambiguation.py` — F1-T0f/F1-T0g. Run and verified: Outcome A
  (vendor serves original as-filed values) and `companyfacts` confirmed multi-vintage.
  `t0f_t0g_disambiguation_summary.json` tracked; `data/raw/fundamentals/sec/2026-09-12/companyfacts/`
  (gitignored) holds CLRB's archived `companyfacts` response.

- `research/fundamentals_f1/t1_identity.py` — F1-T1, identity spine. First implementation used a
  ticker-level `active=true/false` pre-filter that found zero ambiguous tickers across 2,930 —
  disproven by direct spot-check (`NTRP` resolves to two different SEC registrants at different
  dates, which the pre-filter missed) and superseded, same file, by per-event as-of resolution for
  all 20,951 events. Run and verified: 37 ambiguous tickers (313 events), 248 unresolved, escalation
  row 2 does not fire (2.68% < 5%). `ticker_identity.parquet` (gitignored) and `t1_identity_summary.json`
  (tracked) in `results/fundamentals_f1/artifacts/`.
- `research/fundamentals_f1/chart_t1_identity_quality.py` — F1-T1d chart, reusing
  `research/phase_9/chart_common.py`'s validated GREEN/YELLOW/RED status triad rather than a new
  palette. `results/fundamentals_f1/charts/t1_identity_quality_by_year.html`.
- `research/fundamentals_f1/t2_massive_pull.py` — F1-T2, the Massive bulk pull. Run and verified:
  2,935 distinct CIKs, 8 working endpoints (`ratios` not_found, no reachable path), zero fetch
  failures after two bugs caught and fixed in dry-run testing (pagination `next_params` crash; four
  endpoints — `short_interest`, `short_volume`, `float`, `splits` — silently ignoring `cik=` and
  returning arbitrary unfiltered results, fixed by pulling those by ticker instead).
  `t2_pull_summary.json` (tracked) in `results/fundamentals_f1/artifacts/`.
- `data/raw/fundamentals/massive/2026-09-12/<source>/<cik>.json` — raw archive (gitignored under
  `/data/`), 8 sources × 2,935 CIKs, 23,480 files, 2.17 GB. `fetch_manifest.json` (gitignored, same
  rule) records per-source endpoint/keying/record-count; sibling `checksums.json` (added 2026-09-12
  as a correction, see `prompts/fundamentals_f1.md`'s F1-T2d note) carries the per-file SHA256s.
- `.gitignore` — added `results/fundamentals_f1/artifacts/_*.json` (internal resumption/progress
  caches, distinct from the tracked summary JSONs).
- `docs/data/fundamentals_sources.md` — F1-T2e: per-source field schema, sample record, and a
  summary table for all 8 archived Massive sources.
- `research/fundamentals_f1/t3_filing_index.py` — F1-T3a-e, the SEC filing index. Per-CIK
  `submissions.json` (not the daily/full-index bulk archive — see docstring), 2,935/2,935 CIKs.
  Built `sec_filings.parquet` (938,063 rows), `event_filing_proximity.parquet` (20,951 rows),
  `event_filings_window.parquet` (139,039 rows), `item402_filings_full_history.parquet` (unbounded
  look-forward for F1-T3h). Raw archive: `data/raw/fundamentals/sec/2026-09-12/submissions/`
  (gitignored).
- `research/fundamentals_f1/t3f_poll_boundary.py` — F1-T3f. Nanosecond_poll1 tier only (110 events):
  zero filings in the poll-boundary window, escalation row 6 does not fire.
- `research/fundamentals_f1/chart_t3_filing_proximity.py` — F1-T3g chart.
  `results/fundamentals_f1/charts/t3_filing_proximity.html`.
- `research/fundamentals_f1/t3h_blast_radius.py` — F1-T3h (Amendment F1-A1 §3). 8-K Item 4.02 only
  as the genuine-restatement signal (isXBRL/isInlineXBRL checked directly and found unreliable as a
  classifier). 3.70% of the universe (776/20,951) — below Cooper's 10% threshold, escalation row 1c
  does not fire, F1-T4f stays optional. Side finding carried to F1-T6: vendor financials coverage
  before `t0` is only 39.6% universe-wide, concentrated almost entirely in 2023+ events.
- `research/fundamentals_f1/t5_prep_flatten.py` — flattens the F1-T2 vendor raw archive
  (financials/short_interest/splits) into `financials_vintages.parquet`, `short_interest_flat.parquet`,
  `splits_flat.parquet` for F1-T5's ASOF joins. Offline, no network call.
- `.gitignore` — added `results/fundamentals_f1/artifacts/_t3_parts/` and `_t4_parts/` (per-CIK
  parquet resumption caches, same pattern as the existing `_t5b_parts/` entry).
- `docs/Universe-Decisions.md` — D14 Amendment A1 clarification note (2026-09-12): the decision's
  "F1-T3 (SEC EDGAR ... `companyfacts.zip` pull)" wording bundled what the work order later split
  into F1-T3 and F1-T4; the authorization covers both.
- `research/fundamentals_f1/t4_shares_outstanding.py` — F1-T4a-d. Per-CIK `companyfacts` API, not the
  1.4 GB bulk zip (see docstring). `shares_outstanding_observations.parquet` (84,826 rows, 2,542
  CIKs). F1-T4d: vendor-vs-SEC share-count disagreement reported (median ratio 1.03, extreme tail to
  13.4M×), not reconciled. Raw archive: `data/raw/fundamentals/sec/2026-09-12/companyfacts/`.
- `research/fundamentals_f1/t5_prep_flatten.py` + `t6_prep_context.py` — companion-table flattening
  (financials/short_interest/splits) and per-event context (detection price decile, tick-derived not
  D4-restricted; exchange/delisted status from F1-T2's `ticker_details`).
- `research/fundamentals_f1/t5_assemble.py` — F1-T5, assembles `data/fundamentals/event_fundamentals.parquet`
  (20,951 rows, gitignored). `shs_` uses a window-function nearest-match (not a plain ASOF join) after
  F1-T5d's verification caught 5 rows where a SEC cover-page date genuinely postdated its own filing's
  acceptance timestamp — see `research/fundamentals_f1/verify_event_fundamentals.py`'s F1-T5d account
  in `prompts/fundamentals_f1.md`.
- `research/fundamentals_f1/verify_event_fundamentals.py` — F1-T5d Verification Block, structured
  drift-dict + exit-code + `--json` style. Found and fixed 3 real defects on its first run (a
  verification-script datetime-formatting bug, the `shs_asof_ns` hard-stop above, and a stale
  `fin_quality` enum in config) plus, via the suspicious 100%-clean `spl_quality` it made visible, a
  `COUNT(*)`-over-`LEFT JOIN` bug that also silently affected the already-committed
  `flg_n_filings_72h` (both fixed). **All 9 checks pass on the corrected table.**
- `research/fundamentals_f1/t6_coverage_report.py` + `chart_t6_coverage.py` + `chart_t6_lag_distributions.py`
  — F1-T6a/b, the coverage report and its two charts. Escalation row 5 does not fire (`shs_` coverage
  76.8% clears Cooper's 70% floor). Coverage is not missing at random, but the dominant axis is a
  vendor historical-backfill year boundary (2022→2023), not company quality — delisted-status and
  price-decile cross-cuts show little to no gradient.
- `results/fundamentals_f1/REPORT.md` (+ copy at `results/reports/fundamentals_f1_report.md`) — the
  full digest, in `prompts/fundamentals_f1.md` §7's exact order. **Build F1 complete.**

**Built:** the full F1-T0 through F1-T6 sequence, pre-flight through the coverage-report gate. See
`results/fundamentals_f1/REPORT.md` for the complete digest. **Out of scope by design:** float tiers 2
and 3 (§3 of the work order — scoped against this report, not before it) and F1-T4f (the
`companyfacts`-based `fin_` rebuild, stayed optional since F1-T3h's blast radius did not clear
Cooper's mandatory threshold).

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

## `tools/` (repo-hygiene gates — 2 files)

Both are **read-only** and **exit 1 on drift**, so either can gate a phase start. Neither edits what
it checks: a tool that silently repaired a reference would hide exactly the drift it exists to
surface. They exist because this repo has now been bitten three times by a hand-maintained index
going stale and five times by a cited path that did not resolve — the response in both cases was to
**make the class checkable rather than patch the instance**.

- `tools/verify_claude_md_indices.py` — Regenerates the enumerated lists in `CLAUDE.md` from the
  checkout and diffs them against what the file claims. Its first run found **11 listed `D:\`
  hardcodes against 24 live, 7 of the unlisted ones writing to `D:`**, plus a decision pointer sitting
  at D14 against a register running to D19. `CLAUDE.md` mandates running it in T0 of every phase.
- `tools/verify_cited_paths.py` — Resolves every repo path cited in `docs/`, `prompts/`, `CLAUDE.md`
  and `README_HANDOFF.md` against the checkout (2026-09-04). Scoped to **root-anchored** citations,
  skipping template placeholders and treating a phase prompt's references to its own
  `results/phase_{x}/` deliverables as specification rather than citation — without that scoping the
  first two passes reported 266 and 92 hits, nearly all false. Absences with a legitimate reason are
  **dispositioned individually with that reason and reported on every run**, never silently swallowed;
  a **staleness check** fails the gate when a disposition stops matching reality, so the one
  hand-maintained list in the tool cannot itself go stale. Current state: 643 distinct paths cited,
  **0 unresolved**, 11 dispositioned, 40 under four subtrees the map itself declares absent.

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


## Phase 10d — Diagnostic 1: The Boundary Through Time (2026-08-27)

Diagnostic, not a phase. Changed nothing, adopted no rule, appended no decision. Plotted the
candidates argmax-void discards — every chart in the programme before it showed only the winner.

Report: `results/phase_10d_diag1/REPORT.md` (copy at `results/reports/phase_10d_diag1_report.md`).
Digest: `results/phase_10d_diag1/digest.json`.

**Prompt / config** — `prompts/phase_10d_diag1.md`; `config/phase_10d_diag1.json`, hash
**`0879d61c`** *(computed with an explicit UTF-8 read — the file has non-ASCII `_why` strings and
hashes differently under cp1252; see the report §8.4)*.

**Code** — `research/phase_10d_diag1/`: `t1_frames.py` (frames, the full candidate ladder, and the
T1d reconciliation gate — imports 10c's `peaks_poisson`/`envelope_boundary` and asserts the top of
its own enumeration against `envelope_boundary()` on every frame); `t2_charts.py` (charts 01–05);
`t3_animation.py` (chart 06, scrubbable, plus the T3d layout comparison); `t4_tables.py` (all tables
and the stationary-or-shifting verdict).

**Findings** — the distribution is **not bimodal**: 99.8% of frames carrying a boundary hold ≥3
surviving peaks, and 4 of 2,308 are the two-peak case the void parameter presumes. Candidates reach
tradeable timescales far more often than winners do. **The coarse candidate is not the runner-up —
it is ladder rank 5+.** The selection is not stationary and switches rather than drifts.

**Discrepancies posted** — 10c *did* build the animated histogram (T6a–d, 56 events) and Cooper *did*
choose its layout at T6c, both of which the prompt described as deferred; and
`research/phase_10c/s1_t6_animation.py`'s docstring disagrees with its own code on the frame window
and on per-frame peak detection. Plus a third hash-reproducibility defect, encoding sensitivity.

## Phase 10d — Diagnostic 1, Charts Addendum (2026-08-27)

Pictures, not analysis. One distribution-and-boundaries-through-time chart per event, from the frames
Diag1 already committed.

**Prompt / config** — `prompts/phase_10d_diag1_charts.md`; `config/phase_10d_diag1_charts.json`
*(deliberately a separate file: editing `config/phase_10d_diag1.json` would have changed the hash
Diag1's report cites throughout)*.

**Code** — `research/phase_10d_diag1/`: `c1_emit_parquets.py` (emits `diag1_frames`, `diag1_ladder`,
`diag1_tape` — same frames and ladder as Diag1 T1, in the long form the plotter consumes);
`plot_boundary_through_time.py` (Cooper-supplied, installed unmodified except for repairing
transfer-corrupted characters); `c5_manifest.py` (manifest and gate verification).

**Charts** — `results/phase_10d_diag1/charts/boundary_through_time/`: 108 event charts, 3 contact
sheets, one shared `plotly.min.js`, 978 MB, **untracked and regenerable** per 10c's convention;
`results/phase_10d_diag1/artifacts/t_charts_manifest.json` is the committed record. All 43
tape-review events have an 8-min chart; every chart within a (kernel, theme) run shares one y-range,
verified by reading the range back out of each written file.

## D9 Lineage Close-Out — threshold-from-trough is closed (2026-08-27)

**10d-R0 fired on Cooper's tape review.** Closes the threshold-from-trough method established by D9
and carried through v4 → 10c → 10d → Diag1, including any exact-partition replacement, because the
defect is the premise that a privileged boundary exists rather than the arithmetic used to locate one.
**Does not close** the locally-normalized log-interval representation.

Record: `results/d9_lineage_closeout/REPORT.md` (copy at
`results/reports/d9_lineage_closeout_report.md`). Digest: `results/d9_lineage_closeout/digest.json`.
Decision: `docs/Universe-Decisions.md` **D21**, append-only.

**Carries eight findings forward** — evidence is not retracted by the method being closed, per the
rule that preserved v3's scale-separation result under D9. Chief among them: 10c's window fix and
what it demonstrated; 10d's attribution result that assembly is not the cause of the scale; the
break-cause census; Diag1's reconciled frame pipeline; and `plot_boundary_through_time.py`, which is
not tied to this method.

**Also corrected in this close-out** — `CLAUDE.md`'s decision pointer list, stale at D14 while the
register ran to D19, which had already produced one near-collision at D20. Now complete through D21,
with the next free number stated, the register named as the authority, and a standing rule that any
phase appending a decision updates the list in the same commit. And `CLAUDE.md`'s claim that
`docs/Claude-Code-Operating-Plan.md` has never existed — it exists, added 2026-08-13 at `edfb1ea`.

**D21 blocks nothing** — it closes one method and no more; D13's re-anchoring stands. Operating
Plan §6 row 10 is marked closed, insert-only, nothing renumbered. *(Corrected 2026-08-27, same day:
the first version of this entry also recorded row 15 as "blocked on a successor object definition".
That over-read the decision and is withdrawn in this file and in the phase map. Row 15 is open and
unstarted, as before.)*

---

## scale_field — continuous scale-space of trade timing (2026-08-28)

**Not a phase.** Spec is `prompts/scale_field_brief.md`, a build brief that explicitly declines to
become a phase prompt: the method has ~one free parameter, so there is nothing to pre-register, and
correctness is enforced by `research/scale_field/test_scale_field.py`, which IS the specification.
What it keeps from the standard: the frozen cohort with its hash asserted, segment stratification,
D4, the evidence standard, and "the artifact wins". Config `config/scale_field.json`.

**Code** — `research/scale_field/`: `scale_field.py` (the estimator; two channels, exact + Gaussian-
pyramid paths, Allan factor), `adapter.py` (the data boundary — event id → sorted int64-ns tape;
imports the Phase 10 read path and D3 clock unchanged rather than reimplementing them),
`reconcile_allan.py` (the gate), `run_field_one_event.py`, `plot_scale_field.py`, `make_digest.py`,
`test_break_is_not_the_pyramid.py`, and three test modules totalling **43** passing assertions —
including `test_verification.py`, Cooper's independent adversarial suite, which found defect (2).

**The gate PASSED, bit-exact.** `allan_factor()` reproduces Phase 10 v3's committed Allan curve on
**2,166 of 2,166** cells (114 events × 19 eligible rungs) with a **maximum relative difference of
0.000e+00**. Both paths also decline the same 2¹³ s rung for the same reason. Record:
`results/scale_field/artifacts/reconcile_allan.json`.

**Stopped at order-of-work step 3, as the brief instructs** — one event charted, then stop for
Cooper. Two events were run, not one: the median rth event's fine band came back **92% masked**
(at ~2.5 prints/s the `n_eff ≥ 8` floor is never cleared below 1 s), so the median premarket event
was added to exercise the channel. Step 4 (Cooper's read) and step 5 (matched-null thresholds, then
the cohort) are not started.

**Three defects found and fixed in the delivered estimator**, all recorded in
`results/scale_field/REPORT.md` §5. (1) `intervals()` differenced float64 seconds since the Unix
epoch, where the ULP is **238 ns** against an archive minimum gap of 49 ns — 4 of 899
strictly-increasing timestamps on `ALXO_2020-08-05_31.58` went non-positive, and the worst gap error
was 447 ns against a 954 ns scale floor. Every acceptance tape started near t=0, so nothing caught
it. Now differenced in int64 with an explicit origin. (2) **The rate channel had no data floor** —
found by Cooper's independent verification (`results/scale_field/VERIFICATION.md`, V5). It masked
only on `c0 > 0`, so a 15.6 ms kernel holding 0.14 expected prints still returned `|dL/dln s| ≈ 14`
against 0.4–1.1 where there is real data, and those values set the colour scale. Both channels now
share the `n_eff ≥ 8` floor and mask identically. (3) `allan_factor` tiled the data's own support
rather than an explicit window, which the reconciliation gate cannot be expressed without.

**Charts** — `results/scale_field/charts/{event_id}/`, extending Diag1's
`plot_boundary_through_time.py` with the kernel-scale axis replacing the boundary track, palette
imported from it so there is one palette rather than two that drift. Offline `--plotlyjs directory`,
never a CDN (D14). Chart 03 carries a dispersion-vs-scale row because A(T) is a variance statistic
and a median comparison would have produced a false negative.

**The knee criterion itself was withdrawn at Cooper's step-4 read (2026-08-28).** The brief made
v3's knees a prediction the continuous field had to change character near. Neither candidate summary
statistic recovers a known timescale at the scales this cohort lives at: pooled amplitude vs scale
does not select scale at all; the local ridge degrades to 0.18x recovered/injected by τ = 128 s; the
Allan knee has no stable conversion (8, 12.8, 5.1 over a 25× τ span). A knee disagreement is
therefore two uncalibrated statistics being compared. The **bit-exact Allan reproduction stands** —
as a gate on the point-process plumbing, which is what it actually tests.

**Descriptive result, n = 2, no null.** Each event's own Allan knee lands exactly on its segment's
committed v3 knee (AEHL rth 128.0 s; CREX premarket 16.0 s). On the continuous side, **an earlier
claim was withdrawn**: the rate-channel dispersion does *not* break near 200 s "on both events".
It is robust only on the dense premarket event (215–256 s across four configurations, including
`field_exact` with the pyramid removed entirely); on the sparse rth event it spans 64–1290 s and is
**not identified**. The mechanism is the resolution floor `s ≥ 2.26/λ` — AEHL at 2.46 prints/s has
s_min = 0.919 s, so its coarse band's first three octaves sit at or below its own floor. That floor
was expected to be a fine-band caveat and turns out to govern whether a *coarse*-band break is
identifiable at all; it is now drawn on every field panel. Sensitivity run:
`research/scale_field/test_break_is_not_the_pyramid.py`, which also records that the `sigma_lo` knob
proposed for the test is a no-op — decimation boundaries sit at `4·scales.min()·2^k` and `sigma_lo`
cancels. Read the four caveats in REPORT.md §4.2 before treating any of it as a finding.

**Untracked by design** — `results/scale_field/artifacts/*.parquet` and
`results/scale_field/charts/*/*.html` plus the local `plotly.min.js`, per the standing regenerable-
artifact rule; every JSON manifest is tracked. Report: `results/scale_field/REPORT.md`, copy at
`results/reports/scale_field_report.md`. Verification note: `results/scale_field/VERIFICATION.md`,
copy at `results/reports/scale_field_verification.md`. Digest: `results/scale_field/digest.json`.
No decision number appended; next free number remains **D22**.

**The resolution floor, and it is the finding.** `n_eff = 2√π·s·λ ≥ 8` rearranges to **`s ≥ 2.26/λ`** —
derived from the estimator's own effective sample size, not adopted from anywhere, no parameter to
argue about. Measured across the frozen 100-event cohort from `t0_print_count` and the D3 span alone
(no field computation, no tick pass, 0.2 s):

- median `s_min` **7.46 s** for rth events, **1.07 s** premarket, 5.16 s pooled;
- **15/100** events can support the coarse band's 1 s floor session-wide (rth 3/70) — but **the
  session is the wrong denominator.** Re-cut on the window a strategy would act in (D5: intraday
  post-trigger), admissibility rises six-fold: **43/49 events at the anchor +10 s horizon**,
  44/75 at +60 s, 35/93 at +15 min. The n falls with the window because only 49 of 100 events carry
  25 prints in the 10 s after their own trigger, and that drop is itself a finding;
- **0/n at the fine band's 15.6 ms floor at every window**;
- at each event's *most favourable 5% of its session*: 42/100 reach 1 s, 4/100 reach 100 ms,
  **0/100 reach 10 ms**. The best moment of the densest event in the cohort (SOS_2021-02-17,
  831,614 prints) is **58 ms**.

Against the committed sub-burst lineages, and the statement that needs no cross-method inference
because it is the artifacts' own `n_prints` column: **on the uncensored cells the MODAL committed
sub-burst is exactly two prints — 49.3% of them — which is a single interval.** 66.9% are ≤3 prints.
(v4's median of 3 is not comparable: `min_prints_reference: 3` censors that distribution, so its
54% at 3 is pile-up on a configured floor, not a natural mode. 10d's reference cell — `K=0, d=0,
min_prints=2, hard_break` — is an identity merge and comes back bit-identical to 10c Stage 1,
46,709 objects, which is a useful check of the 10d pipeline.) Cooper's phrasing — *"a statement about the two or three fastest prints in a session, not
about a market state"* — is not a hypothesis awaiting test; it is what the committed artifacts say
about themselves. **Caveat carried:** D9's operating variable is the interval itself and estimates no
intensity, so `n_eff` does not bind that lineage on its own terms, and none of this retracts D21 or
the sub-burst artifacts. Scripts `s_min_cohort.py`, `s_min_vs_subbursts.py`, `plot_s_min.py`;
artifacts `s_min_cohort.json`, `s_min_vs_subbursts.json`; charts `charts/cohort/04`, `05`.
**No decision appended; next free number remains D22.** Cooper's §4(a) notes `s ≥ 2.26/λ` is a
candidate for the applicability gate that 10c open item 4 and 10d §4 both leave open — that remains
an open Cooper decision, and nothing here applies it as one.

**Stopped after step r2.** The recovery grid (inject τ at the two measured background rates, fix the
summary statistic on evidence) is next and is not started; the matched null and the cohort run are
gated behind it.

**Corrections after Cooper's read on the floor result (2026-08-28).** Three checks were raised and
**two found errors in published numbers**, both fixed in place: (i) filtering 10d's `t4_subbursts`
on `kernel_min` alone left **78 `(K,d,min_prints,sep)` cells** and 1.93M rows, so the published
median was taken over a mixture of the assembly grid — the committed reference cell is 46,709 rows,
median 1.75 ms / 3 prints; (ii) session coverage was the wrong admissibility denominator and
understated it ~6×. A third check corrected wording: v4's minimum of 3 is a *configured* floor, not
the structural minimum of 2.

**The restatement test (`subburst_is_a_restatement.py`) came back NOT supported.** Regressing each
event's median sub-burst duration on a low quantile of its own inter-trade interval distribution,
log-log: on the uncensored source there is essentially no relationship (R² 0.004, n = 41), and on
censored v4 the moderate fit (R² 0.353) is *beaten by the median-interval control* (0.377), so it
reflects overall event pace rather than the left tail specifically. **So the finding is "the scale
is unmeasurable on this tape", not "the statistic was a restatement"** — the two alternatives are
distinguished, with the power caveat that 10c Stage 1 ran on 49 events, not 100.

**The constructive half, which the closing must not bury.** `s_min` does not say the field is
useless on this cohort; it says which band it works in. **The clusters are real** — three prints
inside 1.75 ms on a 0.30 prints/s tape is astronomically improbable under any stationary null — and
detection needs far fewer prints than rate estimation, so the burst-*detection* question stays open
while the burst-*duration* question closes. The band that survives is the second-to-minute band,
which is both measurable and the one the momentum system actually trades in. The accurate framing is
**"the tape cannot answer the question the lineage asked"**, not "the tape cannot answer any
question". Chart `charts/cohort/06_admissibility_by_window_*`.

**The operating envelope (2026-08-28).** The detection-window re-cut raised `s_min`, but a window
bounds the scale axis from **above** too: the 4-kernel-width edge mask admits only `s < W/8`. Usable
range at the median λ — anchor+10 s **0.67 decades (2.2 octaves)**, +60 s 1.21 (4.0), +300 s 1.71
(5.7), full session 2.59 (8.6). **Inside the operational window the field has about one decade of
usable scale, and two octaves in the first ten seconds.** That is recorded as an open **challenge to
this build's own premise**: a continuum is bought for automatic scale *selection*, which needs
decades to select across, and at 2–4 octaves three or four fixed kernels with matched-null bands
would carry almost the same information for far less machinery. What the field still earns: `s_min(t)`
fell out of the construction and produced the cohort finding; time-localisation is unaffected by a
short scale range; and the floor is time-varying, so a fixed-kernel scheme would need `s_min(t)`
anyway. **Step 3 (the recovery grid) is re-aimed and pre-registered in `config/scale_field.json`
`step_3_recovery_grid` — τ over 0.3–10 s at λ ∈ {2.5, 5, 8.4}/s in 10 s and 60 s windows, with a
fixed-kernel control arm — and must answer that question rather than assume it.** Not started.

**Half the cohort is inactive at a ten-second horizon — a universe result, not a caveat.** Only
**49 of 100** events carry ≥25 prints in the 10 s after their own detection anchor. Joined to Phase
11's quote-staleness table on the 49 events overlapping on their own detection segment:
**corr(log₁₀ T=0 print count, share of trades on quotes >1 s old) = −0.697**; events measurable at
+10 s are 44.8% stale (median 50,228 prints) against 56.1% for those that are not (7,188 prints).
Premarket's own figures point the same way — median event 62.3% stale but trade-weighted 31.6%, and
median quoted spread 760.3 bp at T=0 (both verified against `results/phase_11/artifacts/`). **The
measurable subset and the tradeable subset look like the same subset, and it is about half the
cohort.** Mechanically unsurprising — more prints means more quote updates — so it is a confirmation
that two independent constraints coincide, not a discovery.

**Audit: did the pooled-basis error reach 10d's own record? No.** `audit_10d_basis.py` — all 8 of
10d's digest headline metrics are accounted for (5 name their assembly cell; 3 are computed upstream
of the `(K,d,min_prints,sep)` grid, each exemption recorded with its reason), the T5 attribution
artifacts are keyed per cell by construction, and the REPORT's identity figure of 1.7513 ms over
46,709 objects reproduces exactly. **The pooled figure was mine and lived only in
`results/scale_field/`** — not a second instance of the 10c erratum class. The audit also produced a
free corroboration: 10d's own `share_2print` at the identity cell is 0.4934 against an independent
recomputation of 0.4934, so the two-print composition is corroborated rather than repeated.

**The restatement test is downgraded** to reported-and-left-alone. Two of the three concerns raised
against it were checked and do not apply — the predictor moved 1.47 decades (log₁₀ IQR), so the null
is not vacuous, and the response spans 4.43 decades, so it is not pinned by the object definition —
but the collinearity objection stands and is decisive for the v4 arm (both predictors scale with 1/λ;
a 0.024 R² gap on n=90 cannot separate them). The earlier claim that duration "tracks overall event
pace, not the left tail" is withdrawn as more than the design delivers. It enters no load-bearing
sentence; the floor result closes the object without it.

**Task 1 — the field boolean does not lead a level detector; it lags (2026-08-28).** The work order
made this the task that decides the rest. `FIELD` = sign of `dL/dln s` at the smallest scale clearing
`2·s_min(t)`; `LEVEL` = λ̂ above its own trailing q90 at that scale; window anchor → +60 s, n = 75.
**Two of the three pre-named readings do not apply and the third is a null.** It is *not* a
restatement — Jaccard **0.263** against a 0.9 bar, and R² of ridge strength on log λ̂ is **0.180**, so
the field is largely not rate. But it does *not* lead: the field fires first on **29.7%** of matched
onsets against a **50%** chance baseline, median lead **−0.060 s** (−0.21 kernel widths), consistent
across segments. Cooper's pre-fixed read was that firing at the same instants means the construction
adds nothing operationally; the measured answer is worse — it fires later.

Three controls were needed before any lead could be read, and the first run lacked them: the field
chatters at ~2.8× the level detector's onset rate, so a ±7.8 s nearest-onset match paired **100%** of
level onsets by chance. Added: debounce at one kernel width applied to *both* booleans (arithmetic,
not a threshold — a run shorter than its own kernel is unresolved), a tolerance tied to the field's
own onset spacing, and a **circular-shift null** (200 draws/event, count and spacing preserved).
Also corrected: the work order's `dL/dln s > 0` selects **voids** on this estimator
(`dL/dln s = E_w[z²] − 1` → −1 inside a cluster; negative at 14/14 scales inside a synthetic burst),
so the orientation comparable to a high-activity level detector is `< 0`. Both are reported.

**What survives:** the parameter-free construction is a genuine structural gain — zero is not a
tunable and 2.26 is not a cutoff — and the field remains distinct from a rate detector. Distinct and
earlier are different properties and only the second was tradeable. **Tasks 2–5 not started**;
Task 3's fixed-kernel control arm is now more important, not less. Script `t1_lead_time.py`, chart
`charts/cohort/07_lead_time_*`, artifact `t1_lead_time.json`. **No decision appended; next free
number remains D22.**

**CLOSED 2026-08-28 — D22. The scale-space field closes as a detector; the resolution floor
survives.** Two structural properties of the estimator, not two unlucky runs: `dL/dln s = E_w[z²] − 1`
is **bounded below by −1** and therefore saturates (ON 34% of the window under a sign condition, 2.8×
the level detector's onset rate; almost never under a magnitude one), and it is a **centred**
concentration statistic that cannot go negative until the burst is centred in the kernel — so a lag of
a fraction of `s` was derivable in advance, and the measured −0.21 kernel widths sits there
(29.7% field-first against a 50% chance baseline, binomial p = 3.05e-10, n = 239).

**The one test left, the two-channel divergence `D = m + lograte/ln10 + γ/ln10`, fails on real tape.**
Its zero is the *Poisson* identity, and this tape sits **1.29 decades below it** — so the
parameter-free form `D < 0` is ON ~100% of the time and emits 4 onsets across 75 events. A
permanently-ON boolean is not a detector. The relative form (`D` below its own trailing q10, the
mirror of the level detector) gives a point estimate of +0.23 kernel widths but **binomial p = 0.349
on n = 41 from 20 of 75 events** — not distinguishable from chance — and is no longer parameter-free,
which was the property `D` was proposed for. **The pre-registered kill condition is met.**

**The sign now lives in code once.** `scale_field.burst_on()` / `divergence_on()` / `scale_index_at()`
define the booleans, so prose references the helper instead of restating the condition — the error was
always in prose, never in the suite, which used `argmin` and `-nanmin` correctly throughout. Three new
tests pin the sign, the −1 bound, and the Poisson identity. **46 assertions pass.**

**Standing, undischarged precondition, recorded in D22:** both booleans use a **centred** kernel and
read forward by ~`s`. Relative ordering survives; **no absolute timing claim does.** Nothing in this
line is tradeable until it is re-derived on a one-sided kernel.

**What survives is the deliverable** — the resolution floor `s ≥ 2.26/λ` (the first applicability
criterion the programme has had that is derived rather than adopted), the 49.3% two-print composition,
measurable ≈ tradeable ≈ half the cohort, and the ~4.8-orders-of-magnitude gap between the D9
lineage's timescales and what the tape supports. **Tasks 2–5 not run:** at 2–4 usable octaves with the
onset test negative, the fixed-kernel arm is the likely winner rather than a control. Decision:
`docs/Universe-Decisions.md` **D22**; `CLAUDE.md` pointer list updated in the same commit; **next free
number D23**.
**REOPENED IN PART 2026-08-30 — D23. The causal re-derivation reverses D22's lead result.**
D22's own standing precondition (both booleans centred, so both read forward by ~`s`;
"relative ordering survives — both cheat equally") was discharged by re-deriving the
estimator on a causal half-Gaussian, `w(u) = exp(−u²/2s²)·1[u ≥ 0]`. **The parenthesis is
false.** `LEVEL` is a level statistic that a centred kernel advances by seeing future mass;
`FIELD` is a centred concentration statistic that cannot respond until the burst is
centred. They do not cheat equally, and removing the forward read from both flips the
ordering: the field goes from **−0.204** kernel widths (12/45 events leading) to **+1.515**
(**19/19** events, sign test p = 3.8e−06; 18/18 with the largest contributor dropped),
median **+1.180 s**, both segments agreeing in sign.

**The paired control is what makes it a finding.** The 19 causal contributors are a strict
subset of the centred 45, so it runs within event: centred 3/19 lead (−0.187), causal 19/19
(+1.515), paired difference **+1.906 s-units, 18/19 positive, Wilcoxon p = 1.9e−05**. The
19 are not a special subpopulation — centred median on them (−0.187) ≈ on the other 26
(−0.209), Mann-Whitney p = 0.954; dropping the largest causal contributor (36% of onsets)
leaves causal 18/18 and the paired difference 17/18 positive. Code path
`t1_paired_control.py` → `t1_paired_control.json`. Same frozen cohort and hash, same anchors, ladder, debounce, tolerance rule,
200-draw circular-shift null and window; one thing changed.

**What did NOT change, and it is deliberate.** `dw/dln s = w·z²` regardless of the support
restriction, so `dL/dln s = E_w[z²] − 1 ≥ −1` under the causal kernel too. **D22's
structural fact 1 — saturation — survives untouched** (still ON 23.4% vs LEVEL's 11.9%),
and `test_onesided_is_still_bounded_below_by_minus_one` exists so the causal work cannot be
misread as having repaired it. The Poisson cross-channel identity survives too. The D
channel fires its kill condition again (median D −1.284 decades, 3 and 2 onsets over 78
events).

**The derived price.** `n_eff` halves (`2√π·s·λ` → `√π·s·λ`), so **`s_min` doubles to
`4.514/λ`** and the bottom octave of the usable range is gone; median `s*` 1.567 → 2.506 s.
Against that, the centred field needs 4 kernel widths of *future*, so in a live window it is
undefined above `W/8` and **not computable until `T + 4·s*`** — median **6.27 s**, q75
**12.72 s**, against the ten-second horizon at which half this cohort is inactive. The
`W/8` ceiling that bounded §11's usable range was never a property of the data.

**Two defects found in the same run, both reported not silently fixed.** (1) `knn_rate()`
used `lo = i − k//2` — k/2 prints on *each* side of `t` — so `λ̂` → `s_min(t)` → the scale
`s*` the booleans are read at depended on prints that had not happened; swapping only the
estimator would have left the scale selection cheating while the estimator looked clean.
(2) A coordinate bug in the first draft of the causality test (`prep` re-origins to the
first print, so truncating the raw tape cut 26 ms off-target) — caught by the test failing
against itself, which is the defect class `test_verification.py` exists for.

**Code** — `scale_field.py` gains `field_onesided()` (explicit FFT convolution, **no
pyramid**: half-Gaussians do not compose in quadrature and the pyramid's symmetric
pre-decimation low-pass would leak future into past, so the causal path carries strictly
*fewer* approximations than the centred one it is compared against), `s_min_onesided()`,
`kernel=` on `field_exact()` and `s_min_for_rate()`. `t1_lead_time.py` takes
`--kernel centred|onesided` and counts event attrition by reason. New
`test_onesided.py` (13 assertions); new `plot_onesided.py`.

**Tests** — 59 passing (16 acceptance + 8 verification + 13 causal + adapter,
pyramid-sensitivity, sign/bound/identity pins). Causality is asserted for **bit equality**
by *rewriting* the future rather than deleting it, so array lengths match and numpy's
pairwise summation associates identically; the deletion variant is 4e-15 and the reason is
recorded rather than absorbed. The closed-form causal rate ramp
`dL/dln s = k²s² − 2a·e^{−a²}/(√π·erfc(a))`, `a = ks/√2`, matches to < 0.03 across 14
scales and is *negative* where the centred form is positive.

**Allan hard-stop gate re-run after the estimator change: 2,166/2,166 cells, max relative
difference 0.000e+00.** The only diff in `reconcile_allan.json` is the config-hash key.

**What this does not settle.** Saturation stands. Only **19 of 100** cohort events
contribute a matched onset, and the two booleans are temporally segregated on most (matched
share of LEVEL onsets 20.0% against a 65.1% null; the null gives 50.0% field-first so the
*sign* is not a selection artifact, but the base is 19 events). And under a causal kernel
`dL/dln s` weights recent lags while `λ̂` averages the half-kernel, centroid `0.80·s` — so
**a shorter level kernel might buy the same lead**. The measured +1.52 is about twice the
0.80 centroid gap, so it is not purely that, but only a fixed-kernel control separates them.
**Task 3 is therefore promoted from declined formality to the decisive test, and is unrun** —
D22 declined it because the onset test was negative, and it is no longer negative.

Artifacts `t1_lead_time_onesided.{json,parquet}`; charts
`charts/cohort/08_onesided_{light,dark}.html`. Decision: `docs/Universe-Decisions.md`
**D23**, with a forward pointer added to D22 so it is not cited standalone; `CLAUDE.md`
pointer list updated in the same commit. **Next free number D24.**


## Handoff landing — Phase 10e, Phase 12, universe-scan scoping (2026-08-30)

**Not phases yet. Specs only, nothing run.** Seven files landed from a chat-layer handoff paste. Both
measurement phases are hard-stopped by their own escalation row 2 (`[Cooper]` slots unfilled: 8 in
`config/phase_10e.json`, 16 in `config/phase_12.json`, including the entire LULD band table). The agent
fills none of them.

**Files** — `prompts/phase_10e.md` + `config/phase_10e.json` (forward excursion and the detector ceiling;
two arms, Arm 1 gates Arm 2; 24 escalation rows); `prompts/phase_12.md` + `config/phase_12.json` (halts
and LULD; Stage A is a feasibility gate; 17 rows); `prompts/universe_scan_scoping.md` (**the only
unblocked item** — no `[Cooper]` slot, read-only on data, produces a written feasibility assessment and
no measurement); `docs/operating_plan_s6_replacement.md` (proposed §6 map: 10e inserted, rows 13/15/16
disposed, nothing renumbered); `docs/decisions_draft_D24_D26.md` (four draft decision texts);
`README_HANDOFF.md`.

**The numbering collision the handoff predicted, and it happened.** The drafts arrived numbered D23–D26
on the belief that D22 was the last decision taken. **D23 was already taken the same day** — the causal
re-derivation. The register was read to confirm (the handoff's own instruction, and Phase 10e escalation
row 22), and the drafts were renumbered **D24–D27**, with cross-references in `README_HANDOFF.md` and
`operating_plan_s6_replacement.md` shifted to match. **References to D23 inside `prompts/phase_10e.md`
and `config/phase_10e.json` were left alone** — those cite the real D23 and are correct. The pointer list
has now been stale twice: near-collision at D20, real collision at D23.

**Draft D25 cannot be appended as written, and it is flagged in place rather than rewritten.** Its
justification for closing onset prediction rests partly on `dL/dln s` *"necessarily lagging"* a level
statistic at −0.21 kernel widths — the centred-kernel number, which **D23 reversed** (+1.515 under a
one-sided kernel, 19/19 events, paired, Wilcoxon p = 1.9e−05). Saturation and the `D` degeneracy survive
and still support the conclusion; the stated reason does not. Draft D27's *"derivable and not yet
applied"* is stale for the same reason and is annotated. Both notes say what the minimum repair is and
leave the wording to Cooper.

**Two factual corrections made on landing.** `config/phase_10e.json` pointed `scale_field_module` at
`research/scale_space/scale_field.py` — that path and that directory do not exist, the module is at
`research/scale_field/scale_field.py`, and Arm 2 T5b would have failed to import. All three prompts said
"cut from `main`"; there is no `main` branch (`origin/HEAD -> origin/master`), so they read `master`.

**Three flagged and deliberately not changed, because they are Cooper's:** `arm2_max_events = 75`
against a causal cohort of **78** (fires row 5, which also forbids silently reducing the cohort); the two
different artifacts both cited as the D7 anchor (`phase_8/a102_detection_anchors.parquet` in this config
vs. `phase_10/v2_r13_detection.parquet` in the scale-space arc); and Phase 10e escalation **row 1, which
fires as written** — `phase-11-approved` is at `05ccbfc` and `master` is 70 commits ahead of it.

**Also recorded:** `claude/scale_space_lessons.md`, cited by the handoff as the authority for a
closed-do-not-reopen item, does not exist in this checkout; the standing record is D22/D23 and
`results/scale_field/REPORT.md`. And `results/phase_11/digest.json` carries no `status` field, which
Phase 10e T0a asks for.

**State observed read-only at landing:** `event_minute_bars_v2` = **45,925,350** rows, matching escalation
row 7 exactly; all five frozen artifacts present; working tree clean.

### Handoff resolutions (2026-08-31)

Cooper returned rulings on all four flagged items and named four defects of drafting, one of them
systematic. **The systematic one is worth carrying forward:** the chat layer sees Project docs and the
repo through one interface, the executor sees only the repo, so **any prompt or config drafted for the
executor must cite repo paths only**; where a Project doc is the source of a fact, the fact is restated
in the prompt rather than pointed at. That is what produced the `claude/scale_space_lessons.md` citation.
Alongside it: an invented path presented as fact is a fabrication rather than a defect, and the correct
behaviour was to mark it `[verify]`.

**Rulings applied.** (1) **The entry-signal draft decision is WITHDRAWN and consumes no number** — D23
removed two of its three stated reasons, and saturation, the only survivor, speaks to discrimination
rather than to onset-versus-confirmation. The remaining drafts shift to **D24–D26**
(`docs/decisions_draft_D24_D26.md`, renumbered a second time); the open item is annotated in
`docs/Open-Items-Register.md` with the three tests that now decide it (null-rate matching, the
fixed-kernel control, price conversion of the lead). *"A decision that says still-undecided is not a
decision and should not consume a number."* (2) **Escalation row 1 amended, not cleared** — split into
1 / 1a / 1b, where **1a compares the five frozen inputs' content hashes against their state at
`phase-11-approved`** and 1b records branch movement without stopping; new task T0a-i. An unconditional
branch check became the integrity test it was a poor proxy for. (3) **`arm2_max_events` retired** in
favour of `arm2_cohort_artifact` + `arm2_cohort_expected_n`, with row 5 firing on a difference in
**either** direction — 75 vs 78 was set identity, not a cap. (4) **One detection anchor, `a102`, across
both arms**, new escalation row 25 and task T1a-i; `results/phase_10/artifacts/v2_r14_phase8_crosscheck.json`
is read rather than re-derived. (5) **Phase 12's LULD band table drafted** from public sources and marked
`_STATUS: DRAFT`, with `source_document` deliberately left `[Cooper]` — the config must cite a verified
document, not a URL, so row 2 still blocks the phase. Two questions recorded open: whether the
closing-period doubling applies to a Tier 2 security that crossed $3.00 mid-session, and whether the
brackets key off previous close or the live reference price. `price_bracket` and `doubling_window_active`
are promoted to **required** T4b state variables, because the median event crosses $3.00 during the event
and its band goes 20% -> 10% while price roughly doubles — **the relative move needed to halt roughly
halves as the event runs, mechanically**, and a hazard model without the bracket would attribute that to
the tape.

**Still blocked:** 8 real `[Cooper]` slots in `config/phase_10e.json`, 7 in `config/phase_12.json`.


## Programme close-out (2026-09-02)

**`results/programme_closeout/REPORT.md`**, copy at `results/reports/programme_closeout_report.md`.
Cross-phase, records no decision. **Written for a reader with no context**, against the test 10b's
close-out set: could someone who has never seen this repository read only that file and correctly decide
what to do next?

Carries the thesis as originally stated (quoted, not paraphrased); what closed it on **both** sides -- the
long by D25 at both ends, the short on the structural identity that the screen selects on demonstrated
upward explosiveness and the trade bets against it; the two questions never answerable from disk (live
false-positive rate, RTH-scoped population coverage); **what survives independent of the thesis** --
`s >= 2.26/lambda` and its causal form, `s_min` relating to forward excursion, the cost stack and its
horizon-invariance; **seven specification defects in full**, including four of the agent's own; and the
apparatus as the transferable asset.

**The one variant not excluded** is recorded there: late-entry multi-day short, 173 bp before borrow, with
**no tail read at that entry point** -- and the tail read is what closed the near-anchor version, so that
test comes first if it is ever pursued.

---

## Scale-field derivational arc, filed from `scale_field_bundle/` (2026-09-08)

**Not a phase, and it records no decision.** Five documents, eight scripts and two mockups, delivered as
a loose `scale_field_bundle/` folder at the repo root and distributed the same day. **All of it is
synthetic or closed-form — no file in it has touched the cohort.** Reading order and the full
verification record: `docs/Scale-Field-Arc-Index.md`.

**`claude/` enters this map for the first time.** The directory was created on 2026-09-08 by the
instrument-gates run and was not catalogued. It is where chat-layer documents land — the register's open
item on `claude/scale_space_lessons.md` asks where such documents live, and this is the answer in
practice, though the item itself stays open because that document is still not in the checkout.

**`claude/` (6 files)**
- `claude/scale_field_instrument_gates.md` — the gate battery run against the cohort, 2026-09-08
  (pre-existing; committed at `67248fa`/`17e7238`, not part of this filing).
- `claude/scale_field_reading_grammar.md` — the shape dictionary, the noise ruler, and three structural
  problems with the sign-based burst mark.
- `claude/scale_field_price_layouts.md` — field-against-price layouts; the order-flow-imbalance field is
  the one it argues for.
- `claude/scale_field_itt_overlay.md` — amends the above §1.2: the ITT pane is not redundant with
  `s_min`; both go on one log-duration axis.
- `claude/field_feature_extraction_methods.md` — closed-form derivatives, Newton apex/merge solving, the
  ridge-first pipeline, the duration fit, and a frozen parameter surface.
- `claude/field_credibility_and_value_tests.md` — credibility and value as separate questions, ordered
  cheapest-killer-first.

**Filenames were not chosen at filing time.** Each document is cited by path from its siblings and from
`claude/scale_field_instrument_gates.md`; the citations set the names. That also means the paths now
resolve under `tools/verify_cited_paths.py` rather than dangling.

**Code** — `research/scale_field/derivations/`, eight self-contained scripts `01_verify_calculus.py`
through `08_itt_mockup_generator.py` (numpy only, except 07–08 which need scipy and plotly). Run from the
repo root after filing: **every number quoted in the five documents reproduced**, including the
seed-independence test failing at `8.6e-2` in `ln s` before the §5.1 fix and passing at `5e-13` after it.
Three packaging defects were repaired in the move — four scripts sourced siblings under names the
bundling had renamed away and could not run at all, and the two generators wrote to an authoring-sandbox
path absent from this checkout.

**Charts** — `results/scale_field/charts/mockups/`: `scale_field_price_mockup.html` and
`scale_field_itt_overlay.html`, both regenerated in place from the committed generators rather than
imported. HTML is gitignored under the standing `results/scale_field/charts/*/*.html` rule;
`results/scale_field/charts/mockups/chart_manifest.json` is tracked and carries every reproduced number.

**Docs** — `docs/Scale-Field-Arc-Index.md`, the delivered bundle README rewritten to point at the real
destinations.

---

## Scale-field ridge detector — the instrument built from the arc (2026-09-09)

**A reopening, taken by Cooper on 2026-09-09.** D22 closed the scale-space field as a detector.
This builds the ridge-first detector specified in `claude/field_feature_extraction_methods.md` and
stays inside the instrument lane: it emits a feature table, touches no forward return, and disturbs
neither D24 nor D25. **It has not been run on the cohort and cannot be** — see the kappa gate below.

**Config** — `config/scale_field_detector.json`, committed before the code that uses it. Seven of the
nine parameters are derived rather than chosen; `kappa` and the noise constant are **null**.

**Code** — `research/scale_field/detector/`, a package rather than flat files so it cannot collide
with concurrent work in `research/scale_field/`:
- `moments.py` — the machinery. Kernel-weighted moments `M_0..M_6` and closed-form `F, F_t, F_u,
  F_tt, F_tu, F_uu` at any `(t, ln s)`, `n_eff` computed from the prints with no rate estimate and no
  bandwidth, `lam_hat`, and `field_fft` — a deliberately independent convolution path kept for the
  agreement test. **The `z = (t - t_i)/s` convention is declared once here and nowhere else.**
- `ridge.py` — seed → Newton-polish `t` → edge guard → calibrate → group → describe → **polish the
  scale**. Plus `apex_newton` for `{F = 0, F_t = 0}` and the two-parameter duration fit.
- `test_detector.py` — 18 tests, all passing.
- `validate_synthetic.py` — end-to-end validation through the promoted module.

**Artifact** — `results/scale_field/artifacts/detector/synthetic_validation.json`.

**The kappa gate is open, and it is enforced in code.** `detect()` takes `noise_constant` and `kappa`
as keyword arguments with no defaults and raises without them. The Poisson constant 0.87 is wrong on
this tape by roughly `sqrt(A(s))`; the matched null that should replace it is the object commit
`1a34975` withdrew. Until a null whose bandwidth content is audited exists, this detector runs on
synthetic tapes only.

**Three of the tests had never been run** and are the three the source flagged as having a
demonstrated failure rate: the `z`-convention test (a flipped convention leaves `F` untouched and
negates every odd `t`-derivative, so it is invisible in any rendered field), the forbidden-sign count
(zero creations going coarse, the causality theorem counted rather than assumed), and
moment-recursion against convolution. All pass. Measured against a brute-force direct sum that is
neither implementation, the moment path agrees to `1e-8`–`4e-7` and the convolution path to `~1e-4`,
shrinking with bin width — correct and discretization-limited.

**One discrepancy against the source is recorded in the artifact rather than smoothed over:** section
6 claims the duration fit is "within 16% everywhere"; through the promoted module the widest bump
(`sigma = 90 s`) fits at **−18.9%**. The source's table predates its own section 5.1 scale-polishing
fix, so mid-range accuracy improves (`sigma = 4 s`, −11% → −1.8%) and the widest degrades. The claim
should read *within 20% everywhere, within 5% mid-range*.

---

## Scale-field interval channel (G) — the second channel, and what it cost to check (2026-09-09)

**Synthetic only. No cohort data was read.** Extends `research/scale_field/detector/` with the
interval-channel counterpart of the F-channel detector, per
`claude/field_feature_extraction_methods.md` §7. Records no decision.

**Why a second channel exists.** The rate channel is structurally blind to clumping at constant
mean rate: two tapes with identical `lambda-hat(t)`, one Poisson and one violently clustered,
produce **identical** F fields. The interval distribution is the only place that difference lives.

**Code** — `research/scale_field/detector/interval.py`: `G`, its derivatives from a second weighted
moment family `N_k`, Gate 0's constant check, the measured noise constant, and a two-sided ridge
detector (`clumped` and `regular` departures). `validate_interval.py` writes
`results/scale_field/artifacts/detector/interval_synthetic_validation.json`.
`GOING_LIVE.md` states the two blockers and the exact call shape the real run needs.

**Gate 0 — G's null is a CONSTANT, not zero.** `-gamma/ln10 = -0.2506816`, measured `-0.250630`
at 1e7 draws, inside one standard error; the interval sd came back `0.55703` against a predicted
`0.557004`, independently reproducing the 0.5570-decade constant already on this programme's record.

**The measured noise constant is 0.348, not F's 0.87** — derived envelope `< sqrt(0.5570^2 +
0.4343^2) = 0.7063`, because the two contributions are negatively correlated. G is the quieter
statistic per effective print. It is still a Poisson constant and carries the same health warning.

**Two design decisions, both stated rather than defaulted.** (1) A parallel implementation rather
than a generalised `ridge.py`, because the two differ structurally — two-sided seeding, a
non-arithmetic baseline, a different noise constant — and threading flags through tested code was
the worse trade. (2) **No apex/merge Newton solve for G.** For F, `F = 0` is *arithmetic*; the
corresponding `G - G0 = 0` is *Poisson-referenced*, so its arches and merges would inherit exactly
the dependence that has already killed two constructions in this arc. Ridge locations are invariant
to the baseline (`G0` is a constant, so it cancels in `dG/dt`); only magnitudes depend on it. The
reference-free half is built, the reference-dependent half is not.

**Two results worth the build:**
- **G sees what F cannot** — on a rate-matched clumping episode, G fires at **29x** F's best
  calibrated significance. F is not silent; it speckles into several weak marks, which is the ITT
  mockup's "a rate hump makes a trumpet, clumping makes speckle" confirmed as a test.
- **The channels are NOT independent.** On a pure rate hump with no clumping in it, **G also fires**,
  in the clumped direction, at the hump's flanks. The mechanism is exact: prints are laid down with
  density `lambda`, so the print-weighted mean log-interval is size-biased toward high-rate moments
  while `lambda-hat` is not, giving `D = log10<lam>_w - <lam log10 lam>_w/<lam>_w = -Var(eps)/(2 ln10)`,
  **always negative** — any rate gradient reads as clumping. Measured within ~0.005 decades of the
  closed form. The correction needs a `lambda-hat` bandwidth, which is the dependence that produced
  the `1a34975` retraction, so it is deliberately not built.

**A defect in the ALREADY-COMMITTED F channel, found by this work.** `persistence_octaves` is
`log2(max/min)` over member ridge points, which live on the seed ladder — the §5.1 fix polished
`s_selected` off the grid but left the *extent* on it, and persistence gates the feature count. On a
dense tape F gives 6/7/7/6/7 and G gives 7/6/5/6/5 across seed densities, against a stable 2/2/2/2/2
on the two-feature tape the committed F test uses. **The F channel's seed-independence was a property
of the easy test tape, not of the algorithm.** Recorded as two `strict=True` xfail tests. It matters
here more than it would elsewhere: the gates thread reports no isolated resolved feature anywhere from
8 s to 512 s, so dense-and-interacting is this cohort's operating regime. Any feature-count statistic
is unsafe until it is fixed; per-feature quantities are unaffected.

**Doc correction applied.** `claude/field_feature_extraction_methods.md` §6 said the duration fit is
"within 16% everywhere"; through the promoted module it is **within 20% everywhere, within 5%
mid-range** (`sigma = 90 s` fits at -18.9%). The measured table is left as it was and a dated note
carries the post-§5.1 numbers.

**Tests:** 33 passed, 2 xfailed.

**D26 lands on this work and is recorded in `GOING_LIVE.md` as a third blocker.** D26 (2026-09-09)
closes cohort timing work and addresses this package by name: it *"closes cohort timing work, not
instrument work on synthetic data, and is the gate that detector clears if it is ever pointed at the
cohort."* So the G channel is inside what D26 permits and stops being so the moment it reads a cohort
tape. Two of D26's measured findings also change the contract, both toward more caution: the
fragmentation collapse's dead time **bites 60% of the real tape's intervals** and biases G toward the
`regular` direction — the same direction as its small-`n_eff` bias — and the surrogate carries an
**estimation-noise floor** of its own, so sweeping its bandwidth is necessary but not sufficient.

---

## Scale-field detector panels — the two channels, rendered (2026-09-10)

**Synthetic only, no cohort file touched, records no decision.** Renders the detector tests that
already passed, through the same code path that passed them — `ridge.detect` for F and
`interval.detect_interval` for G — so the charts are a view of committed results rather than a new
measurement. Inside D26, which permits instrument work on synthetic data.

**Code** — `research/scale_field/detector/panels.py`. **Charts** —
`results/scale_field/charts/detector/`: `s1_rate_hump_only.html`, `s2_clumping_only.html`,
`s3_combined.html`, with `chart_manifest.json` tracked and the HTML gitignored under the standing
`results/scale_field/charts/*/*.html` rule.

**The renderer is imported, not rewritten**, per the one-palette rule: `THEMES` from
`research/phase_10d_diag1/plot_boundary_through_time.py`, and `add_channel`,
`add_resolution_floor`, `knn_rate`, `et` from `research/scale_field/plot_scale_field.py`.
`add_channel` is called once per channel. Neither module was modified.

| scenario | corresponds to | F | G |
|---|---|---|---|
| 1 — pure rate hump, zero clumping | `test_cross_check_G_DOES_respond_to_a_pure_rate_hump` | 1 feature, cal 77.1 | **2 features, cal 40.5, on the FLANKS** — the size-bias artifact on display |
| 2 — clumping at constant mean rate | `test_positive_control_G_sees_what_F_cannot` | 7 speckle marks, best cal 4.8 | 5 features, best cal **139.3** |
| 3 — a rate excursion that also clusters | no single test; combination of the two controls | hump at t=850 cal 76.5, speckle at t=598 cal 4.2 | clump at t=625 **D = −0.99**, hump-flank skirt at t=983 **D = −0.19** |

**Scenario 3 is the one that reads.** The two channels separate cleanly on one axis: F owns the
hump where G shows only a shallow skirt, G owns the clump where F shows only speckle, and the
**departure magnitude tells the two G marks apart — −0.99 for real clumping against −0.19 for the
uncorrected gradient artifact**, a 5x separation legible directly off the colourbar.

**Two things are deliberately displayed uncorrected, and captioned as such on every panel.** G's
rate-gradient size-bias is not corrected, so scenario 1's marks are the expected artifact rather
than false positives to explain away; and feature counts on scenario 3 are captioned illustrative
only, because `persistence_octaves` is still read off the seed ladder. Neither was fixed here —
both are open items in `research/scale_field/detector/GOING_LIVE.md`.

**Citation note.** The brief for this work cited `field_validity_goals_prompt.md` as the source of
the reuse-the-renderer rule. **No file of that name exists in this checkout or in git history.** The
rule itself is real and is the repo's standing practice — `gate_charts.py`, `plot_scale_field.py`,
`plot_lead_time.py` and `plot_onesided.py` all import the one palette — so the practice was followed
and the citation is recorded as unresolvable, per the same class of defect
`tools/verify_cited_paths.py` exists to surface.

---

## Scale-field instrument gates — Gates 0–F on the real cohort, and the retraction sweep (2026-09-07 to 2026-09-10)

**Not a phase, and diagnostic only until D26.** Runs the scale field against the real cohort tape
for the first time — everything mapped above this section is synthetic-only. Answers one question:
does the field detect real structure, or the session envelope and estimator noise? The answer is
**D26 — the within-session timing line is closed** (`docs/Universe-Decisions.md`), reached only after
three headline results were run down and retracted by their own controls. This section maps the
instrument, not the decision — read `docs/Universe-Decisions.md` D26 and `claude/scale_field_arc_closeout.md`
for the findings themselves.

**Code — `research/scale_field/`, orchestration and gates.** `instrument_gates.py` runs Gates
0/A–F in sequence against the real tape, stopping on first failure; diagnostic only, no digest, no
decision. Per-gate scripts:

| script | what it gates |
|---|---|
| `gateA_resolve.py` | Gate A's zero-sum identity on the field's own `lograte`-weighted intensity, with an inhomogeneous-Poisson control to separate real residual from finite-domain/mask artifact |
| `gateD_cohort.py` | widens the print-count-stratified cohort so Gate D's shaded-fraction-vs-print-count regression has leverage |
| `gateD_vs_surrogate.py` | re-runs Gate D against a rate-matched smooth-envelope surrogate instead of a print-count regression, per segment, never pooled — separates "detects clustering" from "detects the diurnal envelope" |
| `gateE_ceiling.py` | builds a reliability ceiling for Gate E's split-half correlation from a smooth-rate surrogate and the envelope-subtracted residual, so `r` near 1 isn't misread as fine-structure detection |
| `gateF_calibration.py` | derives Gate F's negative-run-width reference values (2.00 pure Poisson; `2·sqrt(1+σ²/s²)` Gaussian bump) against the estimator's own biases |
| `gateF_recompute.py` | re-runs Gate F's width statistic with the calibration fix (mean not median run length, edge/NaN/segment-truncation excluded) |
| `gate_charts.py` | diagnostic Plotly charts for the gates, palette reused from `research/phase_10d_diag1/plot_boundary_through_time.py` |

**Code — the retraction chain.** Each of the three retracted headlines has its own script:
`surrogate_bandwidth_family.py` and `bandwidth_floor.py` sweep the surrogate smoothing bandwidth `h`
and locate the real-vs-surrogate crossover, which is what showed the "30 s crossover" scales as
`≈2.6h` rather than being a tape property. `subpoisson_check.py` tests the ~10% Allan-factor deficit
against a known-Poisson positive control (bias, not a sub-Poisson finding). `allan_validity_ceiling.py`
and `allan_ceiling_sweep.py` measure the Allan-factor validity ceiling directly (rather than assume it
via rule-of-thumb) across a bandwidth family, which is what withdrew v3's 128 s/16 s knees.
`fragmentation_identity.py` identifies same-order-fill fragmentation from trade-record signatures
(monotone price + multi-venue OR sequence-contiguity) rather than a time tolerance, permutation-tested
against a null — the basis for D26 result 3 (condition code 14, one order many prints). Supporting:
`divergence_controlled.py`, `divergence_vs_tolerance.py`, `subsecond_origin.py`, `reconcile_allan.py`
(order-of-work step 2, a hard-stop reconciliation against Phase 10 v3's committed Allan curve, float-for-float
tol 1e-12), `crossover_vs_decay.py`, `excess_variance.py`, `collapsed_tape_measures.py`,
`absolute_vs_ratio.py`, `subburst_is_a_restatement.py` (tests whether the committed sub-burst-duration
statistic is a restatement of a low quantile of the event's own interval distribution — feeds D26
result 4), and the lead-time pair `t1_lead_time.py` / `t1_paired_control.py` with their charts
`plot_lead_time.py` / `plot_onesided.py`.

**Control tapes — three surrogates, three different jobs, built in `bandwidth_floor.py` and
`surrogate_bandwidth_family.py` off a shared thinned-Poisson `draw()`:**

- **`S30` ("envelope only").** Thinned Poisson from the real event's own intensity smoothed at
  `h = 30 s`. Carries the diurnal envelope shape above 30 s and **nothing** below it — the positive
  control for "envelope, no clustering." Reproduced the real tape's crossover to within 0.5 s, which
  is what retracted the 30 s-crossover finding.
- **`NS05` ("known fine structure").** A Neyman–Scott cluster process on the same envelope: parents
  thinned from the same smoothed intensity, each spawning Poisson(μ=3.0) offspring at Gaussian
  σ = 0.5 s offsets. Same mean intensity and envelope as the real tape, but with **known** clustering
  at a known scale — the blindness control proving the procedure can detect fine structure at all.
- **Poisson base ("nothing").** Homogeneous Poisson, same print count as the real tape, uniform
  arrival times. The negative control; any statistic must read its null value on this tape at every
  scale.

**Artifacts — `results/scale_field/artifacts/instrument_gates/`, 34 files, ~6.9 MB, tracked as
JSON.** One per gate/script above (`gateA_resolve.json`, `gateD_vs_surrogate.json`,
`gateF_recompute.json`, `allan_validity_ceiling.json`, `allan_ceiling_sweep.json`,
`fragmentation_identity.json`, `collapsed_tape_measures.json`, `subpoisson_check.json`,
`surrogate_bandwidth_family.json`, `bandwidth_floor.json`, `crossover_vs_decay.json`, and 23 more,
one per script in the two tables above). **Configs:** `config/scale_field_detector.json` — the frozen
parameter surface per `claude/field_feature_extraction_methods.md` §10, committed before this run,
scoped to produce a feature table only (touches no forward return, reopens D22 per Cooper
2026-09-09, does not reopen D24/D25).

**Charts — an outlier in the standing convention.** `results/scale_field/charts/instrument_gates/`
holds 28 gitignored HTML files (plus the local `plotly.min.js`) — the two the closeout singles out
for a Cooper visual read are `bandwidth_family_ratio.html` (10.4 KB) and `subsecond_collapse.html`
(16.6 KB), both real and non-trivial. **Unlike every other chart directory in this tree
(`cohort/`, `detector/`, `event_panels/`, `mockups/`, each per-event folder), this directory has no
`chart_manifest.json`** — the tracked enumeration-of-gitignored-HTML the `.gitignore` comment
describes as the standing pattern. So these 28 charts are currently enumerated nowhere in git; only
this map entry and the closeout note record that they exist. **Gap noted, not fixed here** — writing
one is a natural companion task to the Cooper chart review the closeout already asks for.

**Prior art.** Cited at `claude/scale_field_arc_closeout.md`'s closeout checklist as owed to this
map; assembled here from where each is actually used:

- **SiZer** — Chaudhuri & Marron, *SiZer for Exploration of Structures in Curves*, JASA 1999.
  `claude/field_feature_extraction_methods.md` calls it "the closest published relative of your whole
  panel" — same idea as the scale-vs-significance map here, read as one object across the scale
  family. Not implemented from directly; cited as the closest published analogue.
- **Dümbgen–Spokoiny** — *Multiscale Testing of Qualitative Hypotheses*, Ann. Statist. 2001. **This
  one is implemented, not just cited**: `research/scale_field/derivations/03_fingerprint_raw_topology.py:123`
  carries `cal = z - sqrt(2*log(max(T_span/s, e)))` verbatim as the per-scale calibration, so that a
  detection at 3 s and one at 300 s are comparable under one decision threshold.
  `claude/field_feature_extraction_methods.md` §4.2 and `claude/scale_field_reading_grammar.md` carry
  the derivation.
  Selinger et al. 2007 and Pasquale et al. 2010 (log-interval histogram burst detection) and Ko et al.
  2012 (locally-normalized log-interval method, adopted in Phase 10 v4 — `prompts/phase_10_v4.md`,
  `docs/Universe-Decisions.md:548`, `docs/Open-Items-Register.md:51`). None of the scale-field arc's
  own surrogate-generation code (`bandwidth_floor.py`, `surrogate_bandwidth_family.py`) cites a named
  spike-train surrogate paper directly — the connection is methodological (thinned-Poisson /
  Neyman–Scott construction is the same family of technique) rather than a direct import.
- **Legéndy & Salcman** and **Kepler injection–recovery** — **cited nowhere in this repo except the
  closeout checklist line itself** (`claude/scale_field_arc_closeout.md:123`). A whole-repo,
  case-insensitive search for `Legendy`, `Salcman`, and `Kepler` returns exactly that one file and no
  other. Recorded here as **owed, not resolved** — per the same standard as the citation notes
  elsewhere in this map, an unelaborated reference is flagged rather than silently completed with
  invented content. Whoever wrote the checklist line has the source; it is not reconstructable from
  what is in the checkout.
- **Chakravarty, Jain, Upson & Wood**, *Clean Sweep*, JFQA 2012 — ISOs carry disproportionate price
  discovery relative to volume share. Used in `docs/Universe-Decisions.md` D26 ("Scope — what this
  does not close") and `claude/what_would_change_a_decision.md` to motivate ISO share as a
  hold-length state variable — the open item this section's Library Map neighbor,
  `docs/Open-Items-Register.md`'s wrong-partition entry, names as one of the two candidates that
  could still reopen D24/D25.

---

## Scale-field detector — closed against D26 (2026-09-11)

**Documentation closeout. No logic change, no cohort file touched, records no decision — D26 is the
decision.** Occasioned by `claude/scale_field_arc_closeout.md`, which flagged an unreconciled detector
implementation sitting in territory D26 had just closed as how a closed line gets restarted by accident.

**Status rewritten, not appended.** `research/scale_field/detector/GOING_LIVE.md` previously read as
BLOCKED on two pending inputs. It now reads **CLOSED BY D26, NOT PENDING ON D26'S INPUTS** — a real
distinction, because a reader skimming for "what is still needed" should not go hunting for a null
constant that no longer matters. Both blockers are answered in
`claude/going_live_blockers_answered.md`, and each resolution is now recorded in place:

- **Blocker 2 (collapse convention) — answered.** Both rules exist and are measured: the identity rule
  (`research/scale_field/fragmentation_identity.py`) retaining ~70% of prints, and a **10 ms** time
  tolerance whose crossing is scale-invariant at `s` = 1 s, 8 s and 64 s. **For `G` the answer is the
  10 ms tolerance**, because the identity rule's conservatism leaves a −0.84 decade residual that is not
  market structure.
- **Blocker 1 (null constant) — answered, and this section's own rationale was WITHDRAWN.** The
  conclusion stands (no fixed matched-null reference exists), but the stated reason for rejecting `0.87`
  does not: D26 withdrew the Allan curve as a clustering measurement, and on a 10 ms collapsed tape
  `A(15.6 ms)` falls 9.79 → **0.91**, so at fine scales `0.87` is very nearly right. The coarse-scale
  departure is the **rate envelope**, not clustering. **Going live on the previous text would have
  imported a retracted premise into a running detector** — the retraction sweep catching a live consumer.
- **The surviving open item is `persistence_octaves`**, still a grid quantity. Left unfixed deliberately:
  the fix is a design change to tested code and, with the cohort question closed, there is no longer a
  reason to spend it.

**Three pointer comments added** at the top of `moments.py`, `ridge.py` and `interval.py` — closed by
D26, synthetic only, see `GOING_LIVE.md`. Same discipline as this package's convention test: the thing
most likely to bite later is a silent assumption nobody restates.

**Two in-code claims corrected in the same pass, comments only.** `moments.py`'s
`POISSON_NOISE_CONSTANT` block carried the withdrawn `sqrt(A(s))` rationale verbatim, and `ridge.py` §6
still said the duration fit is "within 16% / 6%" where the artifact says 20% / 5%. **33 tests pass and
2 xfail, unchanged**, and the diff is comments and docstrings only.

**`a24fecd` reconciled.** It was flagged as possibly another session's independent detector. **It is
this package** — same author, and its commit message is the one written when `moments.py` and `ridge.py`
were first promoted. There is no second implementation and nothing to merge. *(The flag was raised in a
document cited as `timing_line_close_draft.md`, which does not exist in this checkout or in git history;
the reconciliation was done against the commit itself, which does.)*

**Git structure.** Four fully-merged local branches pruned with `git branch -d`: `phase/10d`
(`8ee1734`), `phase/10d-diag1` (`e22663e`), `scale-field` (`0ff37d1`), `scope/universe-scan`
(`6fe3608`). `origin/master` was **52 commits behind** the real state of the research (11 on local
`master` never pushed, plus 41 on `phase/10e`); nothing was at risk, since `origin/phase/10e` already
contained all 52.

> **CORRECTION, same day.** This entry first read *"not fixable from here … opening that PR is a Cooper
> action"*, reasoning from `gh` not being installed to there being no route at all. **That inference was
> wrong.** Stored git credentials plus a direct GitHub API call work — confirmed by reading the result
> back over the same API. **[PR #1](https://github.com/Pericles9/Trading-Research/pull/1) — "Phase 10e,
> D23–D26, and the scale-field arc closeout", `phase/10e` → `master`, 52 commits, 179 files, mergeable
> clean — is open**, raised by a peer session on 2026-09-11. The absent tool was a true fact and a bad
> premise, which is the same shape as the `sqrt(A(s))` correction two paragraphs above.
>
> **What was right is that MERGING is Cooper's call**, not opening: CLAUDE.md requires review, and the
> PR is deliberately unmerged. **Note also that this closeout commit is NOT in PR #1** — it sits on
> `impact-by-participation`, which is 1 commit ahead of `phase/10e`'s tip (`07af342`), so it reaches
> `master` by a later PR from that branch.

**Also flagged, not fixed:** `claude/fragmentation_and_the_closure.md` is tracked but appears nowhere in
this map, against the standing rule that any phase adding files updates it in the same phase. It belongs
to the gates thread, so its entry is left to that thread rather than written here.

## Phase 12 — Halts & LULD, Stage A (dev tier, 2026-09-13)

**Type:** measurement phase, two-stage. Stage A (T0a–T3) run this pass; Stage B unauthorised —
Escalation rows 10/11 fired at T3 and the Approval Gate blocks Stage B until Cooper clears them in
writing. `docs/Universe-Decisions.md` D34, `docs/data/luld_plan_reference.md`,
`results/phase_12/REPORT.md`.

**Code — `research/phase_12/`.** `t0d_audit.py` (satisfiability audit, all 17 escalation rows,
reused methodology from `research/phase_10e/t0d_audit.py`); `t1_gap_census.py` (route 1: every RTH
inter-print gap, dev tier, `is_candidate` flag at ≥60s on top of the full distribution);
`t2a_condition_census.py` (route 2: opaque code-frequency census, candidates vs. a matched
non-candidate sample — no dictionary exists, so this task identifies nothing by construction);
`t2b_band_arithmetic.py` (route 3: reference price and band edges from `event_minute_bars_v2`,
minute-bar granularity, D4-safe — previous close from tick data, never a spine column);
`t2c_agreement_matrix.py` (the three-route agreement read, route 2 contributing zero by
construction); `t3_gate.py` (the Stage A gate itself). `chart_01_gap_duration.py`,
`chart_02_route_agreement.py`.

**Data — `docs/data/luld_plan_reference.md` (new).** A secondary, compiled reference on LULD band
mechanics, produced by live web research under Cooper's explicit one-time authorization (D34) —
corrects a backwards doubling-boundary direction in the original 2026-08-31 draft and adds a
pre-Amendment-18 (2020-02-24) regime branch this cohort's earliest dev event needs.

**Finding, stated once:** route 1 shows a real, modest excess in candidate-gap counts right at the
300-second LULD pause length (not the smooth, featureless null the chart contract names as the
failure case); route 3 touches a band edge in 13/55 dev events; only 9 events show cross-route
agreement, and the single-route-only share (90.3%) exceeds Cooper's 60% ceiling. Route 2
contributes nothing — no code dictionary exists on disk, confirming Phase 11 A2-11's own finding
again on this task's own read. Three concrete, named things would close the gap: a partial
dictionary for the two candidate-exclusive indicator codes (3, 7); full-tier promotion; tick-level
(not minute-bar) band arithmetic.

## Reg SHO 201 — a first-step measurement, not a phase (2026-09-14)

**Not a numbered phase.** `research/reg_sho_201/t1_trigger_check.py` (per-event Rule 201 trigger
check, dev tier, reusing Phase 12's D4-safe previous-close construction) and
`chart_01_decline_distribution.py`. `docs/data/reg_sho_201_reference.md` (the researched, verified
rule). `docs/Universe-Decisions.md` D36 records the authorization's exact scope: a measurement
only. **D5's long-only constraint is unchanged; this closes nothing about the short side.**

## Fundamental exploration E1 — descriptive baseline, not a phase (2026-09-15)

**Branch `explore/fundamental-e1`, cut from `master`.** `prompts/fundamental_exploration_e1.md` (the
brief, with §7 recording two drafting-slip corrections resolved before any code ran: light theme not
dark, and charts nest under `results/fundamental_exploration/charts/` per every other task's
convention rather than a new top-level `charts/`) and `config/fundamental_exploration.json`.
`research/fundamental_exploration/` — `common.py`/`chart_common.py` (shared plumbing, palette carried
by value from `phase/13`'s own `chart_common.py` — that branch is unmerged, not present on this
checkout, so copied from its own history rather than imported), `t0_join_and_assert.py` +
`t0b_detection_price.py` (F1-T6's `detection_price` reconstructed locally, that gitignored
intermediate isn't present on this checkout), `t1_prep_tape_metrics.py` (bulk DuckDB join against
`filtered_trades` — see below), `t1_univariate_{fundamentals,tape}.py`, `t2_coverage.py`,
`t3_shares_x_price.py`, `t4_fundamentals_vs_volume.py`, `t5_filing_landscape.py`,
`t6_reverse_split_cohort.py`, `t7_collinearity.py`, one `chart_*.py` per task. Descriptive only — no
fundamental column touches an outcome variable. `results/fundamental_exploration/REPORT.md` (copied
to `results/reports/fundamental_exploration_report.md` per the cross-phase convention).

Two data-quality findings surfaced while building this, neither acted on in `event_fundamentals`
itself (Build F1 is closed and separately verified; this reads it, doesn't edit it): `spl_quality`
conflates a confirmed zero-splits event with a true data gap (both read `"unavailable"`,
`t5_assemble.py:180-181` — 98% of the "unavailable" rows actually have a resolved CIK); and 54 events
carry `shs_shares_outstanding == 0.0` exactly, plus a further ~146 with an implausibly small nonzero
count (<100,000 shares against real trading volume in the tens of millions) — both handled in
`common.add_corrected_shares_outstanding` (NaN for the exact-zero case; a `shs_share_count_suspect`
diagnostic, never a filter, for the rest) rather than corrected upstream.

`t1_prep_tape_metrics.py`'s bulk join (event volume/print-count/inter-trade-interval from
`filtered_trades`, 4.9B rows) OOM'd twice before landing — 20,951 of ~24,726 total event-folders are
in-scope, so this join touches ~85% of the table, not a small slice, and a window function
(`LAG` for median inter-trade interval) needs a per-partition sort that blew past DuckDB's 25GB
default limit (80% of this machine's 32GB RAM). Fixed by isolating the window-function query from the
cheap aggregates, batching it by event year with per-batch checkpointing, and an automatic
split-and-retry fallback for a batch that still OOMs on its own connection. Recorded as a standing
reference note for future bulk joins against `filtered_trades`/`filtered_quotes`.

## Relative momentum R0 — qualification-layer scoping, not a phase — STOPPED AT T0b (2026-09-17)

**Branch `explore/relative-momentum-r0`, cut from `explore/fundamental-e1`** (which is merged forward
with `origin/master` at `09c6733` and carries the fundamental layer DR-4 reads).
`prompts/relative_momentum_r0.md` — the v3 brief, filed by this run so that the config's `_meta.prompt`
citation resolves; it carries a filing note listing the seven paths it cites that do not exist in this
checkout, four of them marked `[unverified]` inline. `config/relative_momentum_r0.json`.
`research/relative_momentum/` — `common.py` (config, identity key, the D1 population, and a read-only
re-implementation of the participation gate's own `list_events` rule), `chart_common.py` (palette
carried by value from `research/fundamental_exploration/chart_common.py`), `t0a_population.py`,
`t0b_overlap_join.py`, `t0b2_exception_resolution.py`, `t0b3_exception_flags.py`, `chart_t0b.py`.
`results/relative_momentum/r0/` — `REPORT.md` (copied to
`results/reports/relative_momentum_r0_report.md` per the cross-phase convention), `artifacts/`,
`charts/`.

**Nothing under `scanner-epg-momentum/` was executed, imported or modified** — the brief makes that
repository read-only, so its event-selection rule was re-implemented over `data/filtered` instead.
Both projects resolve to the same physical archive: that repo's `DATA_ROOT` is `parents[4] / "data"`
= `E:/Trading Research/data`.

**T0b fired.** The gate's event set and D1 are materially disjoint in one direction. 97.27% of the
reproducible headline profit-factor run (`phase_f/val_full`, PF = 1.9194, n = 1,027 events) sits
inside D1 — but D1 is 15.4× larger, the gate has ever been **run** on 6.96% of it (1,097 / 15,763),
and on **zero** events before 2023-11-17, so three of D1's five years carry no gate observation at
all. The single rule that removes 10,046 of D1's 15,763 events from the gate's admissible universe is
its `min_mom_pct = 50.0` floor; no D1 event is excluded for any other reason. All 39 gate events
outside D1 resolve with no residue: 27 by instrument class (18 warrant, 5 fund product, 4 preferred)
and 12 by `flag_trades_mom_outlier`, every one of those twelve above +700% momentum.

T0a part 2 (the `move_at` prior-close coverage pass), T1, T1c, T2, T3, T4 and T5 did not run. §I.7's
two open items — the liveness sweep and the ratcheting reading — were never reached, so neither was
consumed. Part II (R1) was not authorised and is untouched.

**Two brief deviations, each following E1's precedent on the identical slip:** light theme, not dark;
and charts under `results/relative_momentum/r0/charts/` rather than a new top-level `charts/`
directory (see the E1 entry above and `prompts/fundamental_exploration_e1.md` §7). Both recorded in
`config/relative_momentum_r0.json` `chart_theme.deviation_from_brief`.

A live `SELECT` against `momentum_events_canonical` was attempted at T0a and killed after >10 minutes
of eight-thread CPU — the view joins `filtered_trades`/`filtered_quotes` unconditionally for its
coverage flags. Same finding `research/fundamentals_f1/verify_event_fundamentals.py` recorded on
2026-09-12, reproduced; D1 is built from `results/phase_5/artifacts/quotes_bitmaps_all.parquet`
instead, as E1 and F1 already do.

**Addendum 2026-09-18.** Two sections added after the stop, in answer to the 2026-09-18 read of T0b;
neither restarts the brief. `research/relative_momentum/t0b4_fire_rate.py` re-measures the fire rate
that read infers from: T0b's run/fired pair is a union across 101 result files, which cannot be a
fire-rate denominator. Measured within a run, on the `rising_edge` runner family only (the rapid
`entry_eligible` family writes `n_pass_edges = 0` on every row while recording nonzero pass-to-fail
transitions and trades -- unavailable on that axis, not negative, and `common.runner_family` now makes
the split), the gate fires on **99.83%** of what it sees, 0 runs of 34 with zero fires. The read's
conclusion holds and is understated. The selectivity sits one layer earlier: 201 of 1,228 attempted
events in the PF run never reached the gate, the largest single reason being `setup_filter_fail`
(88) -- **a string no code in this checkout emits**, so the population behind PF = 1.9194 was filtered
by a rule that is no longer in the source.

`research/relative_momentum/t0c_phase11_reslice.py` + `chart_t0c.py` run that read's own section-3
check on Phase 11's committed `t7_cost_vs_capture.parquet`, no new data pass. The named cell
reproduces n = 10,544 exactly. The pre-cost median **does** flip -- -164 bp on the full cell to +66 bp
on the gate-admissible domain and +92 bp on the PF population -- and decomposing the 2x2 shows the
`mom >= 50` floor does all of it (+134 bp alone) while the 2023-11-17 date boundary alone gives
-204 bp and works against the flip. Net of cost it does **not** flip: median round-trip cost rises
70.98 -> 106.30 -> 112.57 bp across those same slices and the net median stays negative. The slicing
variable is `momentum_pct`, a prior-close-to-day's-high quantity the brief's section I.2 bars as a
bucketing variable, so the flip is what conditioning on a lookahead variable does mechanically -- the
gate's *live* entry logic is causal, its *backtest population* is not. Charts 03/04 are ECDFs so the
median is read as a crossing of the whole distribution. Sections 4 and 5 of that read are its own
open decisions and are untouched.

**Addendum 2, 2026-09-18 -- the causal re-run, which reverses Addendum 1's T0c.** On the erratum to
the 2026-09-18 read, which mandates rerunning that check with `move_at`.
`research/relative_momentum/t0a2_prior_close.py` finally builds T0a part 2, the tick-derived prior
session close -- reused verbatim from `research/phase_12/t2b_band_arithmetic.py` and
`research/reg_sho_201/t1_trigger_check.py` (last RTH minute bar's `last_price` at
`session_offset = -1` from `event_minute_bars_v2`, which covers exactly D1's 15,763 events), not the
15,763-folder tick pass originally anticipated. Coverage **15,721 / 15,763 (99.73%)**; 42 events
carried as unavailable. One recorded divergence: that table predates Phase 10c Amendment 6's `{8, 15}`
auction override, exposure bounded by A6's own census at 291 near-close prints against 25.2M.

`research/relative_momentum/t0c2_move_at_reslice.py` + `chart_t0c2.py` re-run T0c on
`move_at_entry = (entry_price - prior_close) / prior_close` at the named cell's own entry instant, so
nothing after the decision enters the slicing variable. **The sign reverses.** T0c's gate-admissible
slice read +66 bp gross / -57 bp net; its causal analogue reads **-1,054 bp gross / -966 bp net**, and
no slice in the causal table has a positive median. The crosstab quantifies the lookahead exactly:
of the 2,904 events the `momentum_pct >= 50` slice selected, **2,577 (88.7%) had not moved 50% at
decision time**. The response curve (chart 05, no threshold set on it) is negative in all ten deciles
and monotone the wrong way above the median -- net -129 bp at decile 5 falling to **-883 bp** at
decile 9. The erratum's one exploratory lead does not survive: the entire positive result on the
causal slice sits inside the 39 `flag_cross_session_extreme` events (net +863 bp), while the 84
unflagged ones net **-1,659 bp** and are negative 87.5% of the time, with `move_at_entry` reaching
2,043% -- A12's population, not a lead. Addendum 1's T0c table carries a supersession banner and is
retained as the record of what the defective specification produced. Charts 05/06; 06 is built to be
read directly against 03, and the pair is the finding. Path A / Path B and the citation fix remain
Cooper's open decisions, untouched.

## Relative momentum v0 -- build and evaluate, a real backtest (2026-09-18)

**Branch `explore/relative-momentum-v0`, cut from `explore/relative-momentum-r0`** (R0's
`t0a2_prior_close.parquet` is a direct input; `move_at` needs it).
`prompts/relative_momentum_v0.md` and `config/relative_momentum_v0.json`.
`research/relative_momentum_v0/` -- `common.py` (population, causal window-volume reader with the
causality assertion in code), `chart_common.py`, `t0_population.py`, `t1_score.py`, `t2_gates.py`,
`t3_evaluate.py`, `t4_diagnostic.py`, `charts.py`. `results/relative_momentum/v0/` -- `REPORT.md`
(copied to `results/reports/relative_momentum_v0_report.md`), `artifacts/`, `charts/` (4).

**Facet 1 reused as-is, not re-derived:** the existing fired population from
`scanner-epg-momentum/backtest/results/phase_f/val_full/per_trade.parquet`, first window per event.
Nothing in that repository executed, imported or modified. **Coverage stated plainly: 997 of 15,763
D1 events, 6.32%**, val split 2023-11-17 to 2024-07-22, 168 session dates. Three population facts
recorded because they change what the numbers mean -- the **gap gate was off** in that run
(`gap_gate_enabled: false`, `blocked_by_gap: 0`, entry `intraday_pct` median +11.25%, p25 -23.42%, so
these are not "+30% crossers at entry"); the first-window window-close exit is `epg_window_close` for
860 of 1,027 with the rest LULD, carried; and the median hold is **540 s**, not the 52 s that is the
median across all 6,004 trades in the run.

**Facet 2 built fresh.** Attention score v0 = 10-minute trailing dollar volume / E2's `B_e`, causal
(asserted in code, not assumed). Volume read from each event's own `filtered/` folder rather than
`filtered_trades` -- a targeted 10-minute range query against that 4.9B-row table does not prune,
measured at 9.5 s for one window; the folder pass did all 1,027 in 66 s. `B_e`'s definition checked
rather than assumed: the `total/B_e` ratio takes exactly the values 39/78/117 = `n_baseline_sessions`
x 39 ten-minute RTH blocks. Known scale mismatch carried as a facet: `B_e` is RTH-scoped and 644 of
999 candidate moments are pre-market.

**Result: the qualification layer selects worse trades.** Policy A (every first-window signal, n=999
like-for-like) median gross markout **0 bp**, win rate 49.6%; Policy B (both gates, n=244) median
**-218 bp**, win rate 40.6%. The level gate does it, not the cross-sectional one. Mechanism in the
score decile panel: the top two deciles -- exactly where the 75th-percentile gate selects -- carry the
worst medians (-200 and -388 bp). **Mean and median disagree in sign and both are reported**: B's mean
(+214 bp) is indistinguishable from A's (+194) because qualification widens both tails, so a
profit-factor read of the same trades would call B neutral. **No policy's median trade clears cost in
either unit** -- best net median anywhere is -71 bp, and the per-share leg is brutal on this cohort
(median entry price $1.94, so 2.512 cents is 129.5 bp).

**Second finding, which bounds the first:** 79.5% of candidate moments had **no competitor live at
all**, median live-set size 1, so gate 2 passed 892 of 999 and 794 passes were uncontested -- only 42
of Policy B's 244 trades came from a contested moment. But candidate density here is 6.11/session
against D1's **17.35/session over the same dates (2.84x)**, so this is a **lower bound** and gate 2's
inertness is a property of this population, not a measured property of the universe.

**Diagnostic:** Spearman(score, `move_at`) = **0.692**, flat across the A12 split (0.687 clear / 0.697
flagged), so the collinearity is not a cross-session artifact -- the score substantially restates the
move. Separately, the gate's own `intraday_pct_at_entry` correlates only **0.314** with the
tick-derived `move_at`: only one of its three prev-close sources is tick-derived.

The decile panel reproduces R0-T0c2's response curve on a **different trade definition** (gate
rising-edge/window-close, 540 s median hold, vs Phase 11's fixed 30-minute horizon): more move already
achieved at decision time predicts a worse forward outcome. `B_e` comes from E2 artifacts that remain
**uncommitted**, so the score is not reproducible from a clean checkout until those land.
