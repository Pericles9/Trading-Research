# Phase 1c — Targeted Re-Collection: Calendar-Bug Heal — Report

**Branch:** `phase/1c` | **Baseline:** `phase-1b-approved` (818c875)

Covers the base prompt (`prompts/phase_1c.md`) and two amendments resolving escalations along the way: Amendment 1 (T3 archive-schema-absent hard stop → content-equivalence), Amendment 2 (T6 post-ingest-mismatch hard stop → collision guard + SDOT remediation). No recommendations below — description only, per the Evidence Standard.

---

## 1. Heal manifest summary (T1)

Derived as a pure per-event set difference (true XNYS T-3..T+3 window minus a faithful replication of the legacy federal-calendar `get_trading_window()`), not a positional offset-index mapping — verified more precise than Phase 1b's original damage labeling (ATER 2022-04-13: 1b flagged 2 damaged offsets; direct reconstruction shows only 1 real gap, since 2022-04-18 was already correctly archived at a shifted legacy position).

| Target type | n pairs | Population |
|---|---|---|
| `event_day` | 142 | `flag_missing_event_day`, cause `calendar_bug` |
| `flanking_setA` | 1,080 | `flag_window_calendar_bug`, missing session caused by a Set A phantom holiday |
| `outer_setB` | 736 | `flag_window_calendar_bug`, session pushed out of reach by a Set B phantom closure |
| `diagnostic_unknown` | 8 | `flag_missing_event_day`, cause `unknown` — diagnostic fetch, not assumed heal |
| **Total** | **1,966** | across 1,991 heal events + 8 diagnostic |

By side: trades 1,966 (always); quotes 1,952 (14 events were trades-only-coverage pre-heal — hard boundary respected).

33 of the 1,849 `flag_window_calendar_bug` events (the "anchor_on_set_a" surprise from Phase 1b) resolved to **zero derived gaps** — direct evidence their anchor-day data was always complete; Phase 1b's flag for them was a defensive placeholder, not real damage.

**T1a** (manifest size vs. 6,000 threshold): 1,966 — pass. **T1b cross-checks**: all 142 event days present; 13/14 Set A dates referenced (the 14th, 2025-11-11, verified as a genuine data gap — zero momentum events of any scope within its window, not a derivation miss); 0 quote-side pairs against trades-only events. All pass.

---

## 2. Control-fetch diff (T3, Amendment 1, T3-R4)

**T3 (base):** first live test (METC 2020-03-13 trades) hard-stopped on `correction` absent from the vendor response. Investigated: `correction` is non-null in only 0.0032% of `filtered_trades` (155,599/4,899,511,143) and absent from METC's own archive file too — a pre-existing sparse-field pattern, not a vendor regression.

**Amendment 1** replaced schema-equality with content-equivalence: a column is `optional` iff non-null rate < 1% **and** demonstrably absent from ≥1 sampled archive file (200-file sample, footer metadata scan). Result: `optional_fields = {trades: [correction], quotes: []}`. All other columns (including `trf_id`/`trf_timestamp` at 33.7% non-null, and `exchange`/`id`/`participant_timestamp`/`sequence_number`/`tape` at ~84%) remain required.

**T3-R4 (formal 20-pair run, 15 stratified + 5 targeted for `correction`):**

| Finding | Detail |
|---|---|
| 17/20 pairs (85%) | Exact match — 0.0% row delta, 0.0% field mismatch |
| ARBB 2024-02-13 trades | Archive 50,000 rows vs. fetched 197,326 (294.65% delta) — archive's max timestamp matches the fresh fetch exactly, but is missing rows spread across most of the session (including all of premarket); not the known Group A prefix-truncation pattern; mechanism undetermined |
| NTZ/ENSC/BHAT/XTIA trades | 6.3–7.4% matched-row price mismatches, all sub-cent (max $0.00005), 99% concentrated on exchange=4 (FINRA/ADF TRF prints) |
| Dropped vendor field | `decimal_size` (new, not in archive schema) — enumerated, not a stop |
| Targeted `correction` pairs | All 5 confirm the vendor still emits it where the archive has non-null rows — conditional-emission hypothesis holds |

**Resolution (Cooper: "proceed"):** both findings trace to pre-existing archive conditions, not the fetch/alignment path — the fresh fetch is *more* complete than the archive for ARBB, and the price difference is sub-cent, isolated to a comparison the heal path (fills absence only) never re-encounters. No threshold changed; documented in `results/phase_1c/artifacts/t3r4_resolution.json`. Chart: `results/phase_1c/charts/01_control_fetch_diffs.html`.

---

## 3. Fetch run outcome (T4)

3,605 distinct (ticker, session, side) work items. **3,585 fetched**, **8 empty** (all `flanking_setA`/`outer_setB`, none `event_day` — thin-name zero-trade days, expected), **12 failed** (0.33%, under the 2% T4b threshold) — all `ArchiveSchemaViolation` on required trades columns, concentrated on Set A dates (Columbus Day, Veterans Day, New Year's Eve observed), the same file-presence pattern T3-R1 characterized just above the 1% optional threshold. T4a (Set A event-day zero-trades): 0/142 — pass.

---

## 4. The 8 unknowns (T5)

| Result | n |
|---|---|
| `collection_failure` (real trades+quotes found) | 8/8 |
| `confirmed_zero_event_day_trades` | 0/8 |

Fetched volumes: 2,921–576,987 trades, 1,744–346,009 quotes per event — matching Phase 1b's original "possible_full_day_halt_signature" observation (substantial quote activity despite zero trades), now resolved as a collection gap rather than a genuine halt. All 8 join the heal set.

---

## 5. Ingestion (T6, T6-R1–R4, Amendment 2)

**First hard stop (RILY_2024-10-15_150.87, event-day heal):** post-ingest count 172,349 vastly exceeded the 93,943 staged rows. Root cause: `event_date` in `filtered_trades`/`filtered_quotes` is a **per-folder constant** (the event's own anchor date, per `src/data/ingest.py`'s `load_filtered()`), not each row's real trade date — the original insert used `session_date` instead of `event_date_canonical`, which only coincidentally matched for this event-day pair. Fixed; RILY's already-inserted data was independently re-verified correct under the fix (no re-ingestion needed).

**Second hard stop (SDOT_2025-10-15_150.87, flanking heal for 2025-10-13):** trades confirmed 0 pre-existing (matches the manifest exactly), but quotes already had 1,603 real rows for the identical date — collection succeeded for quotes where it failed for trades. The pre-fix insert added 1,604 more quotes on top (3,207 combined, likely overlapping).

**Amendment 2** added a standing pre-insertion collision guard (T6-R1): 0 pre-existing rows → heal normally; >0 → skip that side, record `skipped_collision`. Trades collisions would hard-stop (none occurred). **T6-R2** remediated SDOT: deleted the full combined session and re-derived from the untouched original archive file — verified restored to exactly 1,603, every other SDOT session unchanged. **T6-R3/R4** completed SDOT+SHMD and all remaining pairs under the guard.

**Final result:**

| | n |
|---|---|
| Healed | 3,885 |
| Skipped (collision) | 10 |
| Trades rows added | 52,094,401 |
| Quotes rows added | 49,136,980 |

The guard caught 10 collisions, not just the 2 known: SDOT, SHMD, **and all 8 of the T5 "unknowns"** (their quotes sides already had substantial pre-existing coverage, exactly matching Phase 1b's original halt-signature finding) — all skipped cleanly, trades healed normally. A secondary finding while reviewing results: `verify_staged()`'s session-bounds sanity check used a rigid UTC-midnight cutoff, mislabeling 1,437 pairs `MISMATCH` despite every one having the correct row count (legitimate after-hours trades spill past UTC midnight, the same pattern seen in ARBB); widened to a 6-hour tolerance and the ledger patched — no data was ever wrong. Chart: `results/phase_1c/charts/02_healed_sessions_by_offset.html`.

---

## 6. Flag flips and universe recompute (T7)

| Flag | Cleared | Residual | Cause of residual |
|---|---|---|---|
| `flag_missing_event_day` | 149/150 | 1 (SNWV_2022-10-10) | T4 fetch failure |
| `flag_window_calendar_bug` | 1,832/1,849 (1,799 repaired + 33 reclassified) | 17 | 12 T4 fetch failures + 4 confirmed-empty flanking sessions (SFHG, APLM×2, NXTT, STSS) |

Flag-clearing uses **coverage** (healed or `skipped_collision` — either means the session now has real data); `repaired_1c` (new canonical-view column) uses **authorship** (healed only). Independently cross-checked: Python-side and view-side `repaired_1c` counts match exactly (1,948 = 1,948).

**Universe arithmetic:** 20,802 + 149 restored − 0 confirmed-zero = **20,951**. Reconciles exactly against the ledger. Terminal coverage split: 20,772 both-sides + 179 trades-only + 0 no-trades = 20,951 (trades-only unchanged from Phase 1b's 179 — all 149 restored events already had `quotes_ingested=TRUE`, a folder-level property independent of the event-day flag). **T7b:** dev sample v2 confirmed unaffected — 0/50 events overlap the heal population; not re-pinned, per standing rules. Chart: `results/phase_1c/charts/04_universe_waterfall_v2.html`.

---

## 7. Volume reconciliation (T8, informational)

149/149 healed event-day trades reconciled against `momentum_events.event_volume`.

| Stat | Value |
|---|---|
| Median ratio | 1.017 |
| Mean | 40.46 |
| p25 / p75 | 1.004 / 10.02 |
| Min / max | 0.168 / 2203.9 |

Median well inside [0.5, 2.0] — not triggered. Distribution is right-skewed (a handful of events where fetched tick volume vastly exceeds the scan's recorded figure); shown in full, not clipped. Scan volume basis (venues, condition codes, session boundaries) unknown — measurement only. Chart: `results/phase_1c/charts/03_volume_reconciliation.html`.

---

## 8. Escalation check table

| Criterion | Threshold | Observed | Result |
|---|---|---|---|
| T1a manifest size | >6,000 | 1,966 | pass |
| T1b cross-checks | any failure | 0 | pass |
| T2/T3 archive column absent | any | `correction` | **hard stop → Amendment 1** |
| T3-R2 optional-field derivation >4/table | not a stop | 1 (trades), 0 (quotes) | no surprise |
| T3-R3 targeted-pair omission | any | 0/5 | pass |
| T3b control diff (row delta/mismatch) | >1% / >0.1% | ARBB 294.65%; 4 tickers 6.3–7.4% | **hard stop → resolved (proceed)** |
| T4a Set A event-day zero-trades | >5% of 142 | 0% | pass |
| T4b unresolved failures | >2% | 0.33% | pass |
| T6 post-ingest row count | any mismatch | RILY, then SDOT | **hard stop ×2 → fixed + Amendment 2** |
| T6-R2a SDOT post-removal | ≠1,603 or other session altered | 1,603 exact, others unchanged | pass |
| T6-R1 collision guard on trades | any | 0 | pass |
| T6-R1/T6-R3 collisions beyond SDOT+SHMD | not a stop | 8 more (T5 unknowns) | surprise, not a stop |
| T7 arithmetic reconciliation | fails to reconcile | reconciles exactly | pass |
| T7a waterfall residual | ≠0 | 0 | pass |
| T8 volume median ratio | outside [0.5, 2.0] | 1.017 | pass |

---

## 9. Verification block

| Number | Value | Source |
|---|---|---|
| Heal manifest pairs | 1,966 | `results/phase_1c/artifacts/heal_manifest.parquet` |
| Control diff pairs | 20 (40 side-fetches) | `results/phase_1c/artifacts/control_fetch_diffs.parquet` |
| Fetch run pairs | 3,605 (3,585/8/12) | `results/phase_1c/artifacts/fetch_state.parquet` |
| Repair ledger rows | 3,895 (3,885 healed + 10 skipped) | `results/phase_1c/artifacts/repair_ledger.parquet` |
| New in-scope | 20,951 | `results/phase_1c/artifacts/t7_recompute_summary.json`, re-run `src.data.canonical.create_view(stage="t6")` |
| Volume reconciliation n | 149 | `results/phase_1c/artifacts/volume_reconciliation.parquet` |

**Reproduce:** `python research/phase_1c/build_heal_manifest.py && python research/phase_1c/ingest_repairs.py && python research/phase_1c/flag_flips_and_recompute.py`

### Output files

| File | Status |
|---|---|
| `config/phase_1c.json` | committed |
| `research/phase_1c/*.py` (17 scripts) | committed |
| `results/phase_1c/artifacts/*.json` | committed |
| `results/phase_1c/artifacts/*.parquet` | gitignored, regenerable |
| `filtered/{event}/*_repair_1c.parquet` | 3,885 healed pairs, on disk (data/, not git-tracked) |
| `results/phase_1c/charts/01-04*.html` | committed |
| `src/data/canonical.py` | updated (`repaired_1c` column) |
| `results/phase_1c/digest.json`, `REPORT.md` | committed |

### Commits (phase-1b-approved..HEAD)

T0 branch/prompt/config · T1 heal manifest · T2 fetch script · T3 hard stop · Amendment 1 prompt · T3-R1 optional fields · T3-R3 control pairs · T3-R4 hard stop · T3-R4 resolution · T4 full fetch · T5 unknowns · T6 hard stop (RILY fix) · T6 hard stop (SDOT/guard discovery) · Amendment 2 prompt · T6-R1 guard · T6-R2 SDOT remediation · T6-R3/R4 completion · T7 flag flips · T7a chart 04 · T8 volume reconciliation · charts 01-03 · T9 CLAUDE.md · T9 digest.json · T9 REPORT.md (this commit).

---

## Approval Gate

Do not begin Phase 2 or any follow-on work until Cooper has reviewed results and given explicit approval.
