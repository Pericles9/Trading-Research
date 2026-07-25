# Phase 7 — Analysis-Readiness Closure: D4 Retro-Sweep, ETH-Dominant Flag & Sample Pin

**Date:** 2026-07-24 · **Branch:** `phase/7` · **Baseline:** `phase-6c-approved` · **Status:** complete, awaiting approval

Every measurement in this phase is **scan-free**: zero full-table passes over `filtered_trades`/`filtered_quotes` (escalation row 11 held). Description only — no recommendations; the sensitivity numbers are inputs to Cooper's latency-budget confirmation at the gate, not the agent's to interpret.

---

## 0. T0 note — `phase-6-approved` does not exist by design

T0's tag check found `phase-6-approved` absent. Before acting, investigation surfaced `docs/Universe-Decisions.md` **D3**, which explicitly records that "Phase 6 was never approved (no `phase-6-approved` tag was ever created)" — Phase 6's RTH-only measurement was superseded by Phase 6b's extended-day redo, `results/phase_6/` was `git mv`'d to `results/phase_6_rth_only/`, digest status `superseded_rth_only`. A first attempt at this task retroactively created the tag on an initial go-ahead; on finding the D3 conflict, Cooper chose to **revert** it. **Resolution: T0's precondition is satisfied by `phase-6c-approved` alone**, which supersedes both Phase 6 and 6b. This phase still computes against the `event_minute_bars_v1` RTH cache (retained per D3 as "a valid RTH-conditional cache") — a scoped sensitivity test of Phase 6's own superseded number, not a re-adoption of RTH-only as the standing methodology.

---

## 1. D4 retroactive sweep (T1) — hits by phase × class

Swept `src/` and the approved-phase lineage (`research/phase_0a`…`phase_6c`, excluding `phase_6b` and the never-approved `*_context/_signal_forge/_alpha_hunter/_campaign` legacy dirs) for reads of `momentum_events`' 16 non-`momentum_pct` numeric columns. Scoped to the 61 files referencing the spine, classified by full-file read. **Chart:** [04_d4_sweep_hits.html](charts/04_d4_sweep_hits.html) · **Artifact:** [d4_retro_sweep.json](artifacts/d4_retro_sweep.json)

| phase | display_only | universe_selection | computation | total |
|---|---|---|---|---|
| 0a, 0b, 0c, 1c, 5a, 6 | 0 | 0 | 0 | 0 |
| 1 | 1 | 0 | 2 | 3 |
| 1b | 0 | 4 | 0 | 4 |
| 2 | 0 | 6 | 3 | 9 |
| 3 | 0 | 2 | 0 | 2 |
| 4 | 0 | 3 | 0 | 3 |
| 5 | 0 | 2 | 0 | 2 |
| 6c | 2 | 0 | 0 | 2 |
| src | 0 | 1 | 0 | 1 |
| **total** | **3** | **18** | **5** | **26** |

**T1a — bivariate outlier-fit input columns, stated verbatim from the artifact:** *"none of the quarantined columns — the fit's two inputs are momentum_pct (the D4 sole exception) and n_trades_event_day, which is COUNT(*) over filtered_trades (tick-derived, not a spine column at all, not even a quarantined one). Verified by full read of research/phase_1b/bivariate_outlier_flag.py:34-108."* (The `prev_close`-consuming flag is `mechanism_outlier_flag.py`, a *different*, univariate flag — recorded separately as a hit.)

**Escalation rows 2 (computation > 0) and 3 (universe_selection on non-`momentum_pct` > 0) both triggered.** Resolved by Cooper's **D4 Amendment A9** with **zero code changes** ([t1_escalation_resolution.json](artifacts/t1_escalation_resolution.json), `docs/Universe-Decisions.md` D4 §A9):

- **A9.1** — the 18 universe_selection hits are all one formula, `flag_bad_denominator` (`prev_close < floor OR momentum_pct >= cap`); it is placed **inside** D4's `momentum_pct` exception as a reliability guard on the exempted column's denominator. Register item opened (unscheduled): characterize false-negative exposure vs. a tick-derived prior-session close.
- **A9.2** — the 5 computation hits (Phase 2's `momentum_pct_recomputed`; Phase 1's `event_volume` reads from pre-ingestion `candidate_scan_inputs` files) are grandfathered as selection-mechanism audits; the quarantine extends to pre-ingestion files prospectively.
- **A9.3** — prospective standard (now in `CLAUDE.md`): universe-flag formulas defined once in `canonical.py`, never re-derived; the 15 historical re-derivations left as-is.

---

## 2. ETH-dominant flag verification (T2) — 736 / 20,951 / 15,763

`momentum_events_canonical` recreated at **stage `t8`** (additive, Phase 2 T8 / Phase 5 T5 precedent) with `flag_eth_dominant_t0` (BOOLEAN, TRUE iff `excluded_share > 0.5`) and `t0_eth_row_share` (DOUBLE, NULL off-flag). Both tick-derived → **not** D4-quarantined. Verified **scan-free** (the view is never SELECTed — its `trades_ingested`/`quotes_ingested` columns scan `filtered_trades`/`quotes`, and EXPLAIN confirmed DuckDB does not prune them). **Chart:** [01_t0_eth_share_flagged.html](charts/01_t0_eth_share_flagged.html) · **Artifact:** [t2_flag_verification.json](artifacts/t2_flag_verification.json)

| check | observed | expected | pass |
|---|---|---|---|
| `flag_eth_dominant_t0` TRUE | 736 | 736 | ✓ |
| `in_scope` | 20,951 | 20,951 (unchanged) | ✓ |
| D1 (`in_scope AND file1`) | 15,763 | 15,763 (unchanged) | ✓ |
| duplicate join keys | 0 | 0 | ✓ |
| flagged share range | [0.500, 0.992] | — | — |

Chart 01 shows the flagged distribution is a **declining shoulder from ~0.55**, not a mass piled on 0.5 — the threshold separates a genuine tail, not a mode.

---

## 3. Latency-budget sensitivity (T3)

Method (forced by the zero-pass + no-calendar budget): re-pool Phase 6's per-event realized-move-fraction artifacts (the `event_minute_bars_v1` computation, frozen) by event membership. Flag membership = the 736-key set, byte-identical to the view's `flag_eth_dominant_t0` column (T2-verified). **Chart:** [02_decay_sensitivity.html](charts/02_decay_sensitivity.html), [03_min_window_cdf_sensitivity.html](charts/03_min_window_cdf_sensitivity.html) · **Artifact:** [t3_sensitivity_summary.json](artifacts/t3_sensitivity_summary.json)

**Pooled median opportunity-decay crossing (minutes to 50% realized move):**

| variant | full (n=15,763) | excl-flagged (n=15,027) | delta | escalation (>5 min) |
|---|---|---|---|---|
| with minute 0 | 52 | 54 | +2 | no |
| excl minute 0 | 57 | 58 | +1 | no |

The full-D1 crossings **reproduce Phase 6 exactly (52 / 57)** before the sensitivity variant was computed (row 7 check). Chart 02's four curves overlap almost perfectly — the budget is insensitive to the flagged events.

**Minimum-window medians (minutes; of T=0 session volume):**

| variant | pop | 25% | 50% | 75% |
|---|---|---|---|---|
| with min 0 | full | 20 | 72 | 183 |
| with min 0 | excl-flagged | 20 | 74 | 186 |
| excl min 0 | full | 20 | 73 | 183 |
| excl min 0 | excl-flagged | 21 | 75 | 185 |

Every median moves ≤ 3 minutes. Chart 03's CDF pairs are visually indistinguishable in the body.

**Dev tier (T3a):** 15.12 s (< 60 s), 0 duplicate keys in the bar cache for the 56 dev events, and the dev-flagged set `{SLXN 2024-08-19, ZENA 2024-10-11}` matches the Phase 6 dev artifact's >50% set exactly (same shares 0.531 / 0.594) — dev-tier and full-pass computation of the same quantity agree.

---

## 4. Three-surface pin (T4)

[analysis_ready_manifest_v1.json](artifacts/analysis_ready_manifest_v1.json) — all three surfaces verified, escalation rows 9/10 clear.

- **Spine:** `in_scope`=20,951, D1=15,763; flag tallies over both populations (all 736 flagged fall in D1); stage-`t8` view-DDL SHA256 + D1 event-key SHA256 (15,763 keys, serialization stated in-file). Computed scan-free.
- **Dev v4:** manifest join **56/56** exact; 50 primary + 6 sidecar; dev tables 9,638,361 / 7,249,350 rows; 2 dev events carry the flag.
- **Bar cache:** 30,309,950 rows, 15,763 distinct T=0 events, 0 duplicate `(event,offset,minute)` keys, `minute_index ∈ [0,389]` (< 390 RTH bound, no out-of-session leakage), all 7 per-offset counts **byte-identical to the Phase 6 T3 table**.

---

## 5. Escalation check table (all 12 rows)

| # | condition | observed | status |
|---|---|---|---|
| 1 | required tag missing | `phase-6c-approved` present; `phase-6-approved` absent by design (D3) | resolved, not a stop |
| 2 | D4 computation hits > 0 | 5 | **triggered → resolved A9.2 (zero code change)** |
| 3 | D4 universe_selection on non-`momentum_pct` > 0 | 18 | **triggered → resolved A9.1/A9.3 (zero code change)** |
| 4 | flag ≠ 736 / counts changed / dup keys | 736 / 20,951 / 15,763 / 0 | clear |
| 5 | dev-tier runtime > 60 s | 15.12 s | clear |
| 6 | dev flag inconsistency | 0 (SLXN, ZENA match) | clear |
| 7 | reproduction ≠ 52/57 | 52 / 57 exact | clear |
| 8 | sensitivity shift > 5 min | +2 / +1 min | clear |
| 9 | dev v4 join ≠ 56/56 | 56/56 | clear |
| 10 | bar-cache deviation / dup / T=0 ≠ 15,763 | 0 / 0 / 15,763 | clear |
| 11 | any full-table pass | 0 | clear |
| 12 | write out of scope / touch phase_6b | none | clear |

---

## 6. Verification block (§10)

| metric | value | n | source artifact | reproduce |
|---|---|---|---|---|
| D4 sweep hits | 26 (5/18/3) | 26 | `d4_retro_sweep.json` | `python -m research.phase_7.t1_d4_sweep` |
| flag TRUE / in_scope / D1 | 736 / 20,951 / 15,763 | 20,951 | `t2_flag_verification.json` | `python -m research.phase_7.t2_eth_flag` |
| reproduction crossings | 52 / 57 | 15,763 | `t3_sensitivity_summary.json` | `python -m research.phase_7.t3_sensitivity` |
| sensitivity crossings | 54 / 58 (Δ+2/+1) | 15,027 | `t3_sensitivity_summary.json` | `python -m research.phase_7.t3_sensitivity` |
| min-window medians (full) | 20 / 72 / 183 | 15,763 | `t3_sensitivity_summary.json` | `python -m research.phase_7.t3_sensitivity` |
| bar cache rows / T=0 | 30,309,950 / 15,763 | 15,763 | `analysis_ready_manifest_v1.json` | `python -m research.phase_7.t4_manifest` |
| dev v4 join | 56/56 | 56 | `analysis_ready_manifest_v1.json` | `python -m research.phase_7.t4_manifest` |

Charts: `python -m research.phase_7.build_chart_04` and `python -m research.phase_7.build_charts_01_03`.

---

## 7. Output files

| file | status |
|---|---|
| `prompts/phase_7.md`, `config/phase_7.json` | ✓ committed |
| `results/phase_7/artifacts/d4_retro_sweep.json` | ✓ |
| `results/phase_7/artifacts/t1_escalation_resolution.json` | ✓ |
| `results/phase_7/artifacts/t2_flag_verification.json` | ✓ |
| `results/phase_7/artifacts/t3_sensitivity_summary.json` | ✓ |
| `results/phase_7/artifacts/analysis_ready_manifest_v1.json` | ✓ |
| `results/phase_7/charts/01–04*.html` (+ PNG) | ✓ kaleido-verified |
| `src/data/canonical.py` (stage t8) | ✓ |
| `docs/Universe-Decisions.md`, `docs/Open-Items-Register.md`, `CLAUDE.md` | ✓ |
| `results/phase_7/digest.json`, `REPORT.md` | ✓ |

## 8. Commits

`phase-7 T0` (branch/prompt/config + tag resolution) · `T1` (sweep, hard stop) · `T1 A9` (escalation resolution + docs) · `T2` (t8 flag) · `T3` (sensitivity) · `T4` (manifest) · `T5` (docs) · `T6` (charts, digest, report).

---

## Approval gate

Awaiting Cooper's review of the charts and manifest. On approval, tag `phase-7-approved`; Phase 6b then resumes per A8.2 exactly as written — its spine-numeric sweep treats the two new columns as flag/annotation columns, not quarantined numerics (`t0_eth_row_share` is tick-derived). Per **A9.4**, the sensitivity numbers are **descriptive context on the superseded RTH-only measurement**, not latency-budget confirmation — whether the budget stands is Cooper's call.
