# Phase 7 — Analysis-Readiness Closure: D4 Retro-Sweep, ETH-Dominant Flag & Sample Pin

**Date:** 2026-07-24
**Baseline:** `phase-6c-approved` (both `phase-6-approved` and `phase-6c-approved` tags must exist — see T0)
**Objective:** Close the two remaining cleanliness questions ahead of measurement work — (1) audit all approved-phase code for D4 violations (spine numeric columns feeding computation), (2) flag the 736 ETH-dominant-T=0 events on the canonical spine and test the latency-budget numbers' sensitivity to them — then pin all three analysis surfaces (canonical spine, dev v4, bar cache) in a single frozen analysis-ready manifest.
**Primary success metric:** `analysis_ready_manifest_v1.json` written with all three surfaces verified, zero unresolved D4 computation-class hits, and the Phase 6 crossings (52 / 57) exactly reproduced before the sensitivity variant is computed.

---

**Context:**

- This phase is **not** Phase 6b work. Per the 6c gate, 6b resumes at A6.2/A6.3 under A8.2 only after `phase-6c-approved` exists; this phase slots between the tag and that resumption. Do not read, modify, or execute anything under `research/phase_6b/` or `config/phase_6b.json` — A8.2 owns that sweep.
- **T0 resolution note (2026-07-24, recorded before any other work this phase):** T0's tag check found `phase-6-approved` absent. Investigation before acting on it surfaced `docs/Universe-Decisions.md` D3, which explicitly and deliberately documents that "Phase 6 was never approved (no `phase-6-approved` tag was ever created)" — Phase 6's RTH-only measurement was superseded by Phase 6b's extended-day redo, `results/phase_6/` was `git mv`'d to `results/phase_6_rth_only/`, and its `digest.json` status was set to `superseded_rth_only`. A first attempt at this task retroactively created the tag on Cooper's initial go-ahead, before D3 had been surfaced; on finding the conflict, Cooper chose to revert that tag/commit rather than amend D3. **Resolution: `phase-6-approved` does not exist by design and is not created by this phase. T0's precondition is satisfied by `phase-6c-approved` alone**, which supersedes both Phase 6 and Phase 6b's lineage. This phase still computes against the frozen `event_minute_bars_v1` cache (Phase 6's RTH-only bar table, retained per D3 as "a valid RTH-conditional cache") because its own zero-full-table-pass budget requires reusing an existing cache — this is a scoped sensitivity test of Phase 6's own superseded number, not a re-adoption of RTH-only as the standing methodology. D3's extended-day standing rule for future phases is unchanged by this phase.
- **Zero full-table passes this phase.** No scan of `filtered_trades` or `filtered_quotes`, dev tier excepted. Everything here is computable from committed artifacts, `event_minute_bars_v1` (30,309,950 rows), the dev v4 tables, code files, and the spine.
- Consequence of the zero-pass budget: `t0_eth_row_share` can only be populated for the 736 events already enumerated in `results/phase_6/artifacts/t3_excluded_t0_rows.parquet`. Events below the 0.5 threshold get NULL share, not a computed value. This is a deliberate design choice, not an omission — recomputing shares for all 15,763 would cost a full pass. Document it in the report.
- The new flag is an **annotation, not a drop** (flag-don't-delete). Whether flagged events are excluded from any given measurement is decided per-phase by Cooper at each phase's spec, never by this phase and never by default.
- D4 (see `docs/Universe-Decisions.md`): every spine numeric OHLC/volume column is permanently quarantined from computation; `momentum_pct` is the sole exception (universe selection/stratification only). Diagnostic **display** of spine numerics is allowed — Phase 6c's chart 04 volume cross-check is the calibration example of an allowed use.
- Canonical view recreation follows the Phase 2 T8 precedent: additive columns only, via `src/data/canonical.py`. No column removed, renamed, or retyped; no base table touched.
- Known reference counts: `in_scope` = 20,951; D1 (`in_scope AND source_file='file1'`) = 15,763; dev v4 = 56 (50 primary + 6 sidecar); `event_minute_bars_v1` distinct T=0 events = 15,763; ETH-dominant list = 736.
- Environment: `.venv` — duckdb 1.4.4, pandas, numpy, plotly + kaleido. No calendar arithmetic this phase.

---

## Tasks

- [ ] **T0 — Branch, tags, prompt, config**
  Verify `phase-6-approved` and `phase-6c-approved` tags both exist. If either is missing: hard stop (escalation row 1) — do nothing else. Cut `phase/7` from `phase-6c-approved`. Commit `prompts/phase_7.md` and `config/phase_7.json` before any other work. Config pins: `eth_dominant_threshold: 0.5` (inherited from Phase 6 T3, not re-derived), `decay_shift_escalation_min: 5`, `reproduction_targets: {crossing_with_min0: 52, crossing_excl_min0: 57}`, artifact paths.
  - [ ] T0a — Commit

- [ ] **T1 — D4 retroactive code sweep (phases 0–6 + src)**
  Enumerate spine numeric columns from the live `momentum_events` schema (every numeric column except `momentum_pct`). Sweep `src/`, `research/phase_0*/` through `research/phase_6/`, `research/phase_6c/`, and every prior-phase `config/*.json` for reads of those columns — AST-based where the file is Python, token search for SQL strings and configs. For each hit, record `{file, line, column, snippet, class}` where `class` is exactly one of:
  - `display_only` — value appears in a report table, chart label, log line, or diagnostic comparison and flows into no persisted metric, flag, or table
  - `universe_selection` — value participates in a WHERE clause, flag derivation, outlier fit, or any rule that determines `in_scope`, a flag column, or sample membership
  - `computation` — value flows into any persisted artifact number, materialized table, or reported measurement

  Selection criterion: if a hit could be argued into two classes, assign the **more severe** one (`computation` > `universe_selection` > `display_only`) and note the ambiguity — do not resolve it downward.
  - [ ] T1a — **Named suspect:** report exactly which input columns Phase 1b's bivariate outlier fit consumed, regardless of whether the sweep flags them. This is a required line item in `d4_retro_sweep.json` even if the answer is "none of the quarantined columns."
  - [ ] T1b — Write `results/phase_7/artifacts/d4_retro_sweep.json` (all hits, all classes, plus the T1a line item). Check escalation rows 2–3. Commit.

- [ ] **T2 — ETH-dominant flag on the canonical spine**
  Recreate `momentum_events_canonical` with two additive columns: `flag_eth_dominant_t0` (BOOLEAN, TRUE iff the event's key appears in `t3_excluded_t0_rows.parquet`, FALSE otherwise) and `t0_eth_row_share` (DOUBLE, the share from that artifact for the 736, NULL for all other rows). Join on the established event key (`ticker`, `event_date`, `ROUND(momentum_pct,2)`).
  - [ ] T2a — Verify: TRUE count = 736 exactly; `in_scope` = 20,951 and D1 = 15,763 unchanged; 0 duplicate join keys against the artifact. Check escalation row 4.
  - [ ] T2b — Write `results/phase_7/artifacts/t2_flag_verification.json`. Commit.

- [ ] **T3 — Latency-budget sensitivity to the flagged 736**
  All computation from `event_minute_bars_v1` (T=0) joined to the recreated canonical view — no other tick source.
  - [ ] T3a — Dev tier first: run the pipeline against the dev v4 subset of the bar cache (56 events), 60s ceiling, verify 0 duplicate keys and that every dev event whose Phase 6 dev-tier artifact showed >50% ETH share carries `flag_eth_dominant_t0 = TRUE` in the view (consistency between dev-tier and full-pass computation of the same quantity). Check escalation rows 5–6.
  - [ ] T3b — **Reproduction check:** recompute the pooled median opportunity-decay crossing on full D1 (n=15,763), both minute-0 variants. Must reproduce 52 / 57 exactly. Check escalation row 7. This runs and passes **before** the sensitivity variant exists.
  - [ ] T3c — Sensitivity variant: same computation on D1 excluding flagged events (n=15,027 expected — report actual). Both minute-0 variants. Also recompute min-window 25/50/75 medians for both populations. Check escalation row 8.
  - [ ] T3d — Write `results/phase_7/artifacts/t3_sensitivity_summary.json` (all crossings, all medians, both populations, all n). Commit.

- [ ] **T4 — Three-surface sample pin**
  Write `results/phase_7/artifacts/analysis_ready_manifest_v1.json` (committed, not gitignored) containing, per surface:
  - **Spine** — `in_scope`, D1, flag tallies (all flag columns including the two new ones), the view's defining SQL hash, and the full D1 event-key list's SHA256 (keys sorted, canonical serialization stated in the file)
  - **Dev v4** — manifest join vs. canonical spine (must be 56/56 exact), per-cohort counts, row counts of both dev tables, and the list of dev events carrying `flag_eth_dominant_t0`
  - **Bar cache** — `event_minute_bars_v1` total rows, per-offset event counts and row counts (must match the Phase 6 T3 table exactly), distinct T=0 events (must equal 15,763), 0 duplicate `(event, offset, minute)` keys, 0 out-of-session minute indices
  Check escalation rows 9–10.
  - [ ] T4a — Commit

- [ ] **T5 — Docs**
  Append to `docs/Open-Items-Register.md`: the ETH-dominant question closed (flag exists, sensitivity measured, exclusion decisions deferred to per-phase specs); the D4 retro-sweep outcome recorded with its artifact path. Add one line to `CLAUDE.md`'s Universe rules noting the two new canonical-view columns and that `t0_eth_row_share` is populated only for flagged events. No entry in `docs/Universe-Decisions.md` — the flag is an annotation, not a universe decision; if Cooper later excludes flagged events anywhere, that decision gets its own entry then.
  - [ ] T5a — Commit

- [ ] **T6 — Digest and report**
  `digest.json` per §11 and `REPORT.md`. Every claim cites its chart. Description only — no recommendations; the sensitivity numbers are inputs to Cooper's latency-budget confirmation at the gate, not the agent's to interpret.
  - [ ] T6a — Commit; confirm working tree clean

---

## Escalation Criteria

Stop and post results. Do not proceed to the next task. Table order is priority order.

| # | Condition | Threshold | Action |
|---|-----------|-----------|--------|
| 1 | `phase-6-approved` or `phase-6c-approved` tag missing | either absent | Hard stop before branch cut — post which tag is missing, await instruction |
| 2 | D4 sweep: `computation`-class hits | > 0 | Hard stop — post full hit list with snippets, await instruction. No fix attempted, no reclassification |
| 3 | D4 sweep: `universe_selection`-class hits on any column other than `momentum_pct` | > 0 | Hard stop — post hits + the T1a outlier-fit column list, await instruction |
| 4 | Flag verification: TRUE count ≠ 736, or `in_scope`/D1 counts changed, or duplicate join keys | any | Hard stop — post counts, await instruction |
| 5 | Dev-tier runtime | > 60s | Hard stop — post timing, await instruction |
| 6 | Dev-tier flag consistency: any dev event >50% ETH in the Phase 6 dev artifact not flagged TRUE (or vice versa) | any mismatch | Hard stop — post the mismatched events, await instruction |
| 7 | Reproduction check: full-D1 crossings ≠ 52 / 57 | any deviation | Hard stop — post observed crossings, await instruction. The sensitivity variant is not computed |
| 8 | Sensitivity: either crossing shifts by more than `decay_shift_escalation_min` vs. its full-D1 counterpart | > 5 min absolute | Hard stop — post both crossings + chart 02, await instruction |
| 9 | Dev v4 manifest join | ≠ 56/56 | Hard stop — post join detail, await instruction |
| 10 | Bar-cache integrity: any deviation from the Phase 6 T3 table, duplicate keys, or distinct T=0 ≠ 15,763 | any | Hard stop — post diff, await instruction |
| 11 | Any full-table pass over `filtered_trades` or `filtered_quotes` | > 0 | Hard stop — this phase's pass budget is zero |
| 12 | Any write outside `results/phase_7/`, `prompts/`, `config/phase_7.json`, `docs/`, `CLAUDE.md`, or the canonical view recreation; any read/write under `research/phase_6b/` | any | Hard stop |

---

## Output Files

| File | Description | Status |
|------|-------------|--------|
| `prompts/phase_7.md`, `config/phase_7.json` | This prompt + pinned thresholds and reproduction targets | [ ] |
| `results/phase_7/artifacts/d4_retro_sweep.json` | All sweep hits with class labels + T1a outlier-fit line item | [ ] |
| `results/phase_7/artifacts/t2_flag_verification.json` | Flag counts, unchanged universe counts, join-key check | [ ] |
| `results/phase_7/artifacts/t3_sensitivity_summary.json` | Crossings + min-window medians, both populations, both variants, all n | [ ] |
| `results/phase_7/artifacts/analysis_ready_manifest_v1.json` | The three-surface pin: counts, hashes, integrity checks | [ ] |
| `results/phase_7/charts/01–04*.html` | Per the Chart Contract | [ ] |
| `docs/Open-Items-Register.md`, `CLAUDE.md` | Register entries + new-column note | [ ] |
| `results/phase_7/digest.json`, `REPORT.md` | Per §11 | [ ] |

---

## Chart Contract

| # | File | Question | Encoding | n shown | Looks like this if wrong |
|---|------|----------|----------|---------|--------------------------|
| 01 | `charts/01_t0_eth_share_flagged.html` | How extreme are the flagged events — is the 0.5 threshold sitting on a mass point? | ECDF + histogram of `t0_eth_row_share` over the 736, x∈[0.5, 1.0], threshold line at 0.5, top-10 events labeled | n=736 in title | Heavy mass piled directly against 0.5 — the threshold is bisecting a mode, not separating a tail |
| 02 | `charts/02_decay_sensitivity.html` | Does excluding the 736 move the latency budget? | Pooled median + IQR opportunity-decay, 4 curves (full / excl-flagged × with / without minute 0), all 4 crossings annotated | Both population n in legend | Excl-flagged curves visibly detached from full-D1 curves; any crossing pair >5 min apart |
| 03 | `charts/03_min_window_cdf_sensitivity.html` | Do the min-window distributions move under exclusion? | 25/50/75% CDFs, full vs. excl-flagged overlaid (6 curves), medians marked | Both population n in title | Curve pairs separate visibly anywhere in the body, not just the tail |
| 04 | `charts/04_d4_sweep_hits.html` | Where do spine-numeric reads live, and are any of them load-bearing? | Bar: hits by phase (x) stacked by class (color), zero-hit phases shown as explicit zeros | Total hit count in title | Any non-zero `computation` segment; any `universe_selection` segment outside `momentum_pct` usage |

---

## Reporting

On completion, post:
1. D4 sweep summary table (hits by phase × class) + the T1a outlier-fit column list, stated verbatim
2. Flag verification counts (736 / 20,951 / 15,763)
3. Sensitivity table: all four crossings + min-window medians, both populations, with deltas
4. Escalation check table (all 12 rows)
5. Verification block (§10) — every metric with n, source artifact, and repro command
6. Output file table with status filled in
7. Commit list

Every claim cites its chart. No recommendations. The report states what shifted and by how much; whether the latency budget stands is Cooper's call.

---

## Approval Gate

Do not begin Phase 6b resumption (A6.2/A6.3) or any measurement work until Cooper has reviewed the charts and the manifest and given explicit approval. On approval, tag `phase-7-approved`. Phase 6b then resumes per A8.2 exactly as written — this phase changes nothing about those terms, except that 6b's config re-freeze will see the two new canonical-view columns, which A8.2's spine-numeric sweep should treat as flag/annotation columns, not quarantined numerics (`t0_eth_row_share` is derived from tick data, not from spine OHLC/volume).
