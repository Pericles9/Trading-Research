<!-- fullWidth: false tocVisible: true tableWrap: true -->
---
tags:
  - type/register
  - domain/data
  - status/live
created: 2026-07-22
last_reviewed: 2026-07-22
---

# Universe Decisions

Standing, append-only record of Cooper's decisions that fix the analysis universe and the
semantics of spine-level flags — the decisions every downstream phase inherits without
re-litigating. Not a bug tracker (see `docs/Open-Items-Register.md` for that); this file is
for decisions that change what population or which columns future phases are allowed to use
by default.

---

## D1 — Analysis universe

**Date:** 2026-07-22
**Deciding phase gate:** `phase-5-approved`

**Decision:** The analysis universe is `in_scope = TRUE AND source_file = 'file1'`. The
2025/file2 pull (5,188 events) is excluded from all analysis.

**Reasoning on record:** file2 is a separate collection process from file1, is ~100%
not-full-window on both trades and quotes (Phase 5 T2/T4: 5,188/5,188 trades, 5,187/5,188
quotes — Phase 5 Amendment 4 accepted this as structural, not a defect), and carries the
registered 3-column-schema data-quality issue (91.5% of file2 in-scope events have only
`price`/`sip_timestamp`/`size` — no `exchange`, `participant_timestamp`, or `correction`
fields even on the event day; Phase 2 REPORT §2).

**Consequence acknowledged:** the analysis date range ends 2024. Time-based validation
splits cannot test against 2025 — there is no 2025 analysis population to hold out or
validate against under this universe.

**Expected frame:** 15,763 events (15,349 `clean_window=TRUE`, 414 flagged). Verified at
Phase 5a T2 (`results/phase_5a/artifacts/sampling_frame.parquet`).

**How to apply:** every phase from Phase 5a forward filters on `source_file='file1'` in
addition to `in_scope=TRUE` unless a phase prompt explicitly authorizes touching file2 (e.g.,
a future recollection/reconciliation phase). Do not silently widen the universe back to all
20,951 in-scope events.

---

## D2 — `clean_window` semantics

**Date:** 2026-07-22
**Deciding phase gate:** `phase-5-approved`

**Decision:** `clean_window` is an **eligibility flag for window-dependent measurements**,
not a universe filter. It governs whether a specific measurement that needs the full
T-3..T+3 window can be computed for a given event — it does not govern whether the event
belongs in the analysis population.

**Reasoning on record:** events flagged for missing forward sessions (dominant pattern
`0001000` — event day present, all six flanking sessions absent, Phase 5 T2/T4) are
disproportionately consistent with halt/delisting outcomes, not collection loss. Silently
filtering `WHERE clean_window = TRUE` before computing outcome frequencies would drop
exactly the events most likely to represent adverse outcomes, inflating measured results
(survivorship bias) — this is risk register item #8 (`docs/Mom-DB-Strategy-Research-Program.md`
§8: "Delisting/halt handling in T+1 results — Day-2 strategy results inflated by silent
survivor filtering").

**Standing rule for all future phases:**
1. No query filters on `clean_window = TRUE` without the phase prompt explicitly stating
   which window-dependent measurement requires it and why (e.g., "T+3 markout requires the
   T+3 session to exist").
2. Wherever outcome frequencies are reported (win rate, markout, survival, halt rate, etc.),
   flagged events are counted as outcomes — not dropped, not silently excluded. If a flagged
   event cannot be measured on a given window-dependent statistic, that is itself a data
   point (e.g., "missing T+3 session" is evidence consistent with a halt/delisting outcome,
   not a NULL to discard).

**How to apply:** any phase writing a query that touches `clean_window`, `trades_full_window`,
or `quotes_full_window` must cite this decision and state which measurement the filter
serves. Aggregate/summary statistics computed over `source_file='file1'` (D1) default to the
full 15,763-event frame unless a specific window-dependent step requires narrowing.

---

## D3 — Analysis clock for intraday measurements is the full extended trading day

**Date:** 2026-07-23
**Deciding phase gate:** Phase 6b (pre-approval — recorded at phase start per Cooper's determination
in the phase 6b prompt, not at its approval gate)

**Decision:** The analysis clock for intraday measurements is the full extended trading day —
premarket, regular session, and post-market — per the XNYS schedule with extended-hours bounds,
with every bar tagged by session segment. RTH-only variants may be produced as labeled
comparability views but are never the primary measurement.

**Reasoning on record:** Phase 6 measured RTH only. 736/15,763 events (4.7%) had >50% of their
event-day prints outside the regular session (top of list 95–99%), and the archive's universe was
selected on `momentum_pct = (high − prev_close)/prev_close`, where the high may occur premarket.
Extended hours are structurally important to these names and cannot be excluded. Phase 6's numbers
are not wrong — they are RTH-conditional answers to a question that needed the full day.

**Supersession:** Phase 6 was never approved (no `phase-6-approved` tag was ever created). Its
outputs are retained, relabeled (not deleted) from `results/phase_6/` to `results/phase_6_rth_only/`
(`git mv`, no content changes), with `digest.json` status set to `superseded_rth_only`. The
`event_minute_bars_v1` DuckDB table (RTH-only cache) is retained untouched — a valid RTH-conditional
cache and the source of phase_6b's `rth_legacy` comparability variant.

**Standing rule for all future phases:** Any phase computing intraday minute-level measurements
uses the extended-day clock (`event_minute_bars_v2` or its successor) as the primary population.
An RTH-only cut is permitted only as an explicitly labeled comparability view, never presented as
the headline result. Session-date and segment-boundary computation must be timezone-aware
(`America/New_York`, DST-aware) — casting the UTC `sip_timestamp` to a date (the convention used
through Phase 6) misassigns EST-winter post-market prints after 19:00 ET to the next calendar day
and must not be reused for extended-day work.

---

## Related

- [[Open-Items-Register]] — the "2025 inclusion decision" item is closed there, referencing D1.
- `results/phase_5/REPORT.md` — the measurements (file2 flagged share, bitmap patterns) that
  motivated both decisions.
- `docs/Mom-DB-Strategy-Research-Program.md` §8 — risk register item #8, cited by D2.
- `results/phase_6_rth_only/` (formerly `results/phase_6/`) — the superseded RTH-only measurement
  that motivated D3; `results/phase_6b/` — the extended-day redo.
