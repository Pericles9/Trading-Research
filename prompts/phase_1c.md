# Phase 1c — Targeted Re-Collection: Calendar-Bug Heal

**Date:** 2026-07-19
**Baseline:** Phase 1b approved (`phase-1b-approved`) — canonical spine live; in-scope universe 20,802/23,268; 142 events with `flag_missing_event_day` (cause `calendar_bug`), 8 with cause `unknown`, 1,849 in-scope events with `flag_window_calendar_bug` (session-shape damage from `collect_massive_data.py`'s federal-calendar window logic).
**Objective:** Heal every calendar-explained missing session by targeted fetch from the Massive API, verify, ingest, flip flags, and recompute the universe — restoring the ~150 pending events and clearing the window damage so no downstream phase carries a standing per-offset exclusion tax.
**Primary success metric:** Every deterministically-derived heal target fetched, verified, and ingested (or confirmed-empty with cause closed); all flag flips arithmetic-consistent; updated waterfall balances to 0 residual.

---

**Context:**
- **Approved scope (Cooper):** Full heal — the 142 missing event days, all calendar-explained missing flanking sessions across the 1,849 window-damaged events, Set B short-window outer sessions, and resolution of the 8 unknowns. **Hard boundary: the ~1,540 trades-only quote-file gap is NOT touched.** Its mechanism is uncharacterized (Phase 4 owns it); healing quotes into that population before it is understood risks papering over a pattern.
- The legacy collector `collect_massive_data.py` is never executed. This phase writes a new, purpose-built fetch script in `research/phase_1c/`.
- API key via environment variable only — never committed, logged, or echoed into artifacts.
- All fetched raw responses are staged and snapshotted before any ingestion. The API is the source for this phase only; later phases read the artifacts.
- Session calendar: the pinned XNYS calendar from `config/phase_1b.json` (same pinned version, restated in `config/phase_1c.json`).
- Writes to `filtered_trades`/`filtered_quotes` occur **only** in T6, only from verified staged files, and only for heal-target sessions. Nothing else in either table is modified, ever.
- Vendor historical ticks are immutable in principle, but data corrections and schema evolution happen — which is exactly what T3's control fetches exist to detect. Trust is earned there before anything is healed.

---

## Tasks

- [ ] **T0 — Branch and commit prompt**
  Cut `phase/1c` from main. Commit `prompts/phase_1c.md` and `config/phase_1c.json` before any other work.

- [ ] **T1 — Derive the heal-target list (deterministic, no row-count inference)**
  For every event carrying `flag_missing_event_day` (cause `calendar_bug`) or `flag_window_calendar_bug`: reconstruct the **legacy** window (federal-calendar business days, replicating `get_trading_window()` logic *in analysis code only* — the legacy script itself is not executed) and the **correct** window (pinned XNYS, T-3..T+3). Heal targets = (ticker, session) pairs in the correct window but absent from the legacy window. This derivation is purely calendrical — absence of rows in the tables is corroboration, never the selection criterion (thin names can legitimately print zero).
  Side rule per pair: events with `quotes_ingested = TRUE` → heal trades **and** quotes; trades-only-coverage events → heal **trades only** (the quote gap stays intact per the hard boundary).
  Separately: the 8 `unknown`-cause event days go on the list as **diagnostic fetches** (trades + quotes), tagged distinctly.
  Write `results/phase_1c/artifacts/heal_manifest.parquet`: ticker, session, event key, target type (event_day / flanking_setA / outer_setB / diagnostic_unknown), sides to fetch, status column for tracking.
  - [ ] T1a — Post manifest summary: pair counts by target type and by side, with n. Expected order: 2,000–4,500 pairs. If > 6,000, escalate (derivation suspect).
  - [ ] T1b — Cross-checks: all 142 event days present in the manifest; every Set A date from 1b's T5-R1 accounted for; zero pairs targeting quote-side of trades-only events. Any failure → escalate.
  - [ ] T1c — Commit

- [ ] **T2 — Fetch script**
  New script in `research/phase_1c/`: fetches trades and quotes for a (ticker, session) pair, writes staged parquet under `results/phase_1c/staging/{TICKER}_{SESSION}/`, aligned to the archive schema (column names, types, ordering). Vendor fields absent from the archive schema are dropped **and enumerated once** in the report; archive columns absent from the vendor response → escalate. Resumable via the manifest status column; chunked; respects rate limits; raw responses preserved alongside the aligned parquet.
  - [ ] T2a — Commit before any network run

- [ ] **T3 — Control fetches (trust gate — nothing heals before this passes)**
  Fetch 20 (ticker, session) pairs that **already exist** in the archive: stratified across years 2020–2025 and across event-day trade-count terciles, seed from config, event days only, both sides where coverage exists. Staged only — never ingested.
  Diff staged vs archive per pair: row counts; on matched rows, price/size/timestamp equality; condition-code and venue-code value sets.
  - [ ] T3a — Post the 20-row diff table (pair, archive n, fetched n, delta %, matched-row mismatch %, code-set differences) plus Chart 01
  - [ ] T3b — Gate: any pair with |row-count delta| > 1%, or matched-row field mismatch > 0.1%, or a condition/venue code set difference that changes which rows exist → **hard stop with the diff detail posted**. Cosmetic differences (column order, dtype width) are recorded and allowed.
  - [ ] T3c — Commit

- [ ] **T4 — Full fetch run**
  Execute the manifest. Commit before the run (long-run rule). Per-pair status updated in the manifest as fetched/failed/empty.
  - [ ] T4a — Sanity check on Set A event days: these were real trading sessions on mostly active names — if > 5% of the 142 event-day fetches return zero trades, that is an auth/parameter bug, not market reality → hard stop.
  - [ ] T4b — Vendor-side failures (errors, not empties) retried up to the config cap; unresolved failures listed with n. If > 2% of pairs, escalate.
  - [ ] T4c — Commit (manifest state)

- [ ] **T5 — Resolve the 8 unknowns**
  From their diagnostic fetches: vendor returns trades for the event day → reclassify cause to `collection_failure`, pair joins the heal set. Vendor confirms zero trades → set `confirmed_zero_event_day_trades = TRUE`, permanently out of scope, cause closed; record whether vendor quotes exist that day (halt signature) as an annotation only.
  - [ ] T5a — Post the 8-row resolution table
  - [ ] T5b — Commit

- [ ] **T6 — Verify, place sibling repair files, ingest**
  For every successfully fetched heal pair:
  1. Verification on staged data: session timestamps within the correct session bounds; ticker matches; schema matches archive exactly.
  2. Copy staged parquet to the event's folder as `trades_repair_1c.parquet` / `quotes_repair_1c.parquet` (originals never touched — repair provenance visible at file level, and the folder tree remains the source of truth for any future re-ingest).
  3. Ingest repair files into the main tables. Post-ingest per-pair check: table row count for (ticker, session) == staged row count exactly. Any mismatch → hard stop.
  Write `results/phase_1c/artifacts/repair_ledger.parquet`: pair, rows staged, rows ingested, file paths, fetch timestamp, verification status.
  - [ ] T6a — Commit before the ingestion run; commit the ledger after

- [ ] **T7 — Flag flips and universe recompute**
  - `flag_missing_event_day` → cleared where the event day healed and verified; `scope_pending_repair` → resolved.
  - `flag_window_calendar_bug` → cleared only where **every** damaged offset for that event healed; partially healed events keep the flag with remaining damaged offsets recorded.
  - `repaired_1c = TRUE` on every touched event (canonical view column).
  - Recompute `in_scope`. Post the arithmetic: prior 20,802 + restored events − any newly confirmed-zero exclusions = new count, every term with n. Must reconcile exactly against the ledger or → hard stop.
  - [ ] T7a — Updated waterfall (Chart 04); residual must be 0
  - [ ] T7b — Dev sample v2 is **not** re-pinned (frozen per standing rules); confirm all 50 dev events unaffected by this phase's writes (expected — none were flagged) and state it
  - [ ] T7c — Commit (canonical view change in `src/data/canonical.py` — instructed)

- [ ] **T8 — Volume reconciliation (informational — feeds Phase 6, gates nothing)**
  For the healed event days: fetched event-day trade volume vs the scan inputs' `event_volume`/`volume` for the same event. Post the ratio distribution with n and Chart 03. The scan's volume basis (venues, condition codes, session boundaries) is unknown — this is the archive's first tick-vs-scan cross-check, reported as measurement only. Escalate only if the median ratio falls outside [0.5, 2.0] (would suggest the fetch collected the wrong thing, not a basis difference).
  - [ ] T8a — Commit

- [ ] **T9 — Docs, digest, report**
  CLAUDE.md: update the flag bullet — `flag_missing_event_day` no longer "pending repair"; add:
  > - Repair provenance: sessions healed in Phase 1c exist as `*_repair_1c.parquet` sibling files inside event folders and are flagged `repaired_1c` on the canonical view. Any future full re-ingest of `filtered/` must include repair siblings. Never re-query the API for healed data — the staged artifacts and repair ledger are the record.
  Write `digest.json` per §11 and `REPORT.md`; every claim cites its chart; working tree clean.
  - [ ] T9a — Commit

---

## Escalation Criteria

Stop and post results. Commit first. Do not fix, tune, or proceed.

| Condition | Threshold | Action |
|---|---|---|
| Heal manifest size (T1a) | > 6,000 pairs | Hard stop — derivation suspect |
| Manifest cross-check failure (T1b) | any | Hard stop |
| Archive schema column absent from vendor response (T2/T3) | any | Hard stop |
| Control-fetch diff (T3b) | row delta > 1% or field mismatch > 0.1% or row-defining code-set difference, any pair | Hard stop — post full diff |
| Set A event-day fetches returning zero trades (T4a) | > 5% of 142 | Hard stop — auth/parameter bug presumption |
| Unresolved vendor-side fetch failures (T4b) | > 2% of pairs | Hard stop |
| Post-ingest row count ≠ staged row count (T6) | any pair | Hard stop |
| Universe arithmetic fails to reconcile against ledger (T7) | any | Hard stop |
| Updated waterfall residual (T7a) | ≠ 0 | Hard stop |
| Volume reconciliation median ratio (T8) | outside [0.5, 2.0] | Hard stop — wrong-data presumption |

---

## Output Files

| File | Description | Status |
|---|---|---|
| `config/phase_1c.json` | Calendar pin, control-fetch seed and count, retry cap, all thresholds | [ ] |
| `research/phase_1c/` fetch + verify scripts | Purpose-built collection path (legacy collector untouched) | [ ] |
| `results/phase_1c/artifacts/heal_manifest.parquet` | Deterministic target list with per-pair status | [ ] |
| `results/phase_1c/artifacts/control_fetch_diffs.parquet` | 20-pair archive-vs-vendor diff detail | [ ] |
| `results/phase_1c/artifacts/repair_ledger.parquet` | Per-pair staged/ingested/verified record | [ ] |
| `filtered/{event}/trades_repair_1c.parquet` (+ quotes where applicable) | Sibling repair files, per healed event | [ ] |
| `results/phase_1c/charts/01_control_fetch_diffs.html` | Chart contract #01 | [ ] |
| `results/phase_1c/charts/02_healed_sessions_by_offset.html` | Chart contract #02 | [ ] |
| `results/phase_1c/charts/03_volume_reconciliation.html` | Chart contract #03 | [ ] |
| `results/phase_1c/charts/04_universe_waterfall_v2.html` | Chart contract #04 | [ ] |

---

## Chart Contract

| # | File | Question | Encoding | n shown | Looks like this if wrong |
|---|---|---|---|---|---|
| 01 | `charts/01_control_fetch_diffs.html` | Does the new fetch path reproduce the archive? | x=control pair, y=row-count delta % (symmetric log), bars; second panel: matched-row field mismatch % per pair; threshold lines at ±1% and 0.1% | per-pair archive and fetched n in hover; 20 pairs in title | Bars breaching the threshold lines; deltas correlated with year (would suggest vendor-side data revisions rather than noise) |
| 02 | `charts/02_healed_sessions_by_offset.html` | Did the heal close the damage where it mattered? | x=window offset T-3..T+3, y=session count, grouped bars: damaged-before / healed / remaining; the 142 event-day heals distinct at T=0 | n on every bar | A "remaining" bar materially above zero at any offset without a matching entry in the failure lists |
| 03 | `charts/03_volume_reconciliation.html` | Does fetched event-day volume agree with the scan's event_volume? | x=scan volume (log), y=fetched volume (log), scatter, y=x reference line, ratio histogram inset | total n in title | Points far off the diagonal in a structured pattern (venue/condition basis mismatch) or a bimodal ratio cloud |
| 04 | `charts/04_universe_waterfall_v2.html` | Does the post-heal universe balance? | Waterfall: 1b terminal 20,802 → +restored → −confirmed-zero → new in-scope; terminal split by coverage as in 1b chart 03 | n every step | Any unexplained residual |

Standard chart rules per §9 apply. No per-event charts — repair phase, exempt per §7, not exempt from this contract.

---

## Reporting

On completion, post:
1. Heal manifest summary by target type and side, with n
2. Control-fetch diff table (all 20 pairs) and the dropped-vendor-fields enumeration
3. Fetch run outcome: fetched / empty / failed counts with n
4. The 8-unknowns resolution table
5. Repair ledger summary: pairs ingested, total rows added per table
6. Flag-flip arithmetic and the new in-scope count, every term with n
7. Volume reconciliation summary with ratio distribution stats and n
8. Escalation check table: every criterion, observed, pass/fail
9. Verification block (§10) for every headline number; output file table; commit list

Every claim cites its chart. No recommendations. Descriptions of what is visible only.

---

## Approval Gate

Do not begin Phase 2 or any follow-on work until Cooper has reviewed results and given explicit approval. Phase 2 (universe statistics on the healed canonical spine) will be drafted fresh after this gate.
