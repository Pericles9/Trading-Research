# Phase 1b — Amendment 3: T5b Escalation Resolution

**Date:** 2026-07-18
**Resolves:** T5b hard stop (150 zero-event-day-trades events > 50 threshold), commit 5a7d612. Root cause confirmed by the agent: `collect_massive_data.py:get_trading_window()` built collection windows against `pandas.tseries.holiday.USFederalHolidayCalendar`, which disagrees with the actual NYSE/NASDAQ session calendar. 142/150 event days were never collected because they fell on federal-but-not-market holidays.
**Decision (Cooper):** No repair in this phase. Flag, quantify the full blast radius, finish 1b. Targeted re-collection is Phase 1c, gated separately after the 1b gate. The legacy collector remains never-execute; 1c will use a new purpose-built script.

Commit this file to `prompts/`, then execute T5-R below and continue to T6.

---

**Context additions:**
- Reference session calendar from this point forward: `exchange_calendars` (or `pandas_market_calendars`) XNYS, **version pinned in `config/phase_1b.json`**. The federal holiday calendar is never used for any market-session logic anywhere in this project.
- `market-hours/market-hours-database.json` remains quarantined (Unknown provenance). Phase 4 validates it against the pinned library. Do not use it here.
- No writes to `filtered_trades`/`filtered_quotes` in this amendment. Quantification only.

---

## Tasks (insert before T6)

- [ ] **T5-R1 — Calendar mismatch derivation**
  Using the pinned XNYS calendar, derive deterministically over 2020-01-01..2025-12-31:
  - **Set A (phantom holidays):** dates the federal calendar treats as holidays but XNYS was open (expected: Columbus Day all years, Veterans Day weekday years + 2023's Friday-observed shift, Juneteenth 2021 observance).
  - **Set B (phantom sessions):** dates the federal calendar treats as business days but XNYS was closed (expected: Good Friday all years, special closures incl. 2025-01-09).
  Post both lists in full. Cross-check: every one of the 142 calendar-bug event dates must appear in Set A. If any mismatch date appears in either set that is not in the expected families above, list it under `surprises` and continue.
  - [ ] T5-R1a — Commit

- [ ] **T5-R2 — Zero-event-day cause annotation**
  Add `zero_trades_cause` to the flags artifact for the 150: `calendar_bug` (event date ∈ Set A, expected 142) or `unknown` (expected 8). These events get `flag_missing_event_day = TRUE` and are **out of scope** pending Phase 1c repair — record `scope_pending_repair = TRUE` so they are distinguishable from permanently excluded events.
  - [ ] T5-R2a — Singleton check (the 8 `unknown` events): count `filtered_quotes` rows on the event day for each. Post the 8-row table (ticker, date, n_quotes_event_day). Quotes present with zero trades is recorded as `possible_full_day_halt` in the artifact — recorded only, no further investigation, no scope change.
  - [ ] T5-R2b — Commit

- [ ] **T5-R3 — Blast-radius quantification (window-shape corruption)**
  For every in-scope event (including trades-only coverage), compute the **correct** 7-session window (T-3..T+3) from the pinned XNYS calendar. Then:
  - `flag_window_calendar_bug = TRUE` where the correct window contains ≥ 1 Set A date that is not the event day itself (that session was deterministically never collected), OR ≥ 1 Set B date was counted as a session by the legacy window logic (window one real session short).
  - Record per event: which offsets (T-3..T+3) are damaged, and the damage type (missing session / short window).
  - Corroboration check on a sample of 20 Set-A-affected events: confirm the archive contains an extra outer session (T-4 or T+4 present) consistent with the federal-calendar shift. Post the 20-row table.
  Report: total flagged n; breakdown by damaged offset with n per offset (a missing T+1 and a missing T-3 are different injuries — the offset table is the headline of this amendment); breakdown by damage type; flagged share of the in-scope universe.
  - [ ] T5-R3a — Chart 05 per the contract addition below
  - [ ] T5-R3b — Commit

- [ ] **T5-R4 — Re-check the T5b gate (restated)**
  The original T5b criterion is superseded: the 150 are now explained and flagged, not an open anomaly. New criteria for this amendment are in the table below. If none fire, resume the original prompt at T6.
  - [ ] T5-R4a — Commit

---

## Changes to the original prompt (downstream)

1. **`in_scope` (T6):** excludes `flag_missing_event_day = TRUE`. Does **not** exclude `flag_window_calendar_bug` — those events are valid for event-day work. The flag governs use, not membership:
   - Any analysis touching flanking sessions (baselines, pseudo-controls, T-3..T-1 features, T+1..T+3 outcomes) must filter on `flag_window_calendar_bug = FALSE` **for the offsets it uses**, and report the n excluded.
2. **T6 waterfall:** add a step — minus `flag_missing_event_day` (annotated "pending 1c repair") — after zero-trade events. Terminal buckets note the window-flagged count as an annotation, not a drop (they remain in scope).
3. **T7 dev v2 eligibility:** add `flag_window_calendar_bug = FALSE`. The dev sample must have clean 7-session windows.
4. **T8 CLAUDE.md block**, add:
   > - Session calendar: pinned `exchange_calendars` XNYS only. The federal holiday calendar is banned from all market logic — `collect_massive_data.py` used it and corrupted collection windows (see Phase 1b amendment 3). `market-hours-database.json` remains quarantined pending Phase 4 validation.
   > - `flag_missing_event_day` events are out of scope pending Phase 1c re-collection. `flag_window_calendar_bug` events are in scope for event-day work; any use of flanking sessions filters on this flag per damaged offset and reports the n excluded.
5. **T8 Schema.md addendum**, add:
   > **Confirmed 2026-07 (Phase 1b):** `collect_massive_data.py` computed T-3..T+3 windows against the US federal holiday calendar, not the exchange calendar. Consequences: event days falling on federal-but-not-market holidays (Columbus Day, Veterans Day, Juneteenth 2021 observance) were never collected (142 events); windows containing such dates are missing that session and include an extra outer session; windows containing market-closed federal-business days (Good Friday, special closures) are one real session short. Flags: `flag_missing_event_day`, `flag_window_calendar_bug` on the canonical view. Repair: Phase 1c (targeted re-collection).

---

## Escalation Criteria (amendment scope)

| Condition | Threshold | Action |
|---|---|---|
| Any of the 142 event dates not found in derived Set A | any | Hard stop — the root-cause story is incomplete; post the residual dates |
| `flag_window_calendar_bug` count | > 3,000 events (> ~15% of in-scope) | Hard stop — blast radius large enough to rethink the 1c/flag split before finishing 1b |
| Mismatch dates outside the expected families (T5-R1) | — | Not a stop — list under `surprises` |
| Set B (short-window) damage | — | Not a stop — quantified and flagged only |

---

## Chart Contract (addition)

| # | File | Question | Encoding | n shown | Looks like this if wrong |
|---|---|---|---|---|---|
| 05 | `charts/05_calendar_damage_by_offset.html` | Which window offsets did the calendar bug damage, and how many events per offset? | x=window offset (T-3..T+3), y=event count, grouped bars by damage type (missing session / short window); separate marker row for the 142 missing-event-day cases at T=0 | n on every bar; total flagged n and in-scope universe n in title | Damage spread uniformly across offsets with no concentration at dates adjacent to Set A/B holidays — would contradict the deterministic mechanism and suggest a second, unexplained cause |

---

## Phase 1c (preview — not part of this amendment, no work now)

Scope to be drafted after the 1b gate, sized by T5-R3's output: a new, purpose-built script fetching trades+quotes for exactly the missing (ticker, session) pairs from the vendor API; append to main tables with provenance columns; verification per pair; flag flips (`flag_missing_event_day` → cleared, `scope_pending_repair` → resolved) only after verification; dev v2 unchanged. The legacy collector is not executed.

---

## Approval Gate

Unchanged. The 1b gate now also constitutes approval of the 1c scope draft as next work.
