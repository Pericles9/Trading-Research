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

## D4 — All measured quantities are tick-only; the spine's numeric columns are permanently quarantined

**Date:** 2026-07-24
**Deciding phase gate:** Phase 6c Amendment 8 (pre-approval — recorded at disposition, ahead of
the `phase-6c-approved` tag, per the same pattern as D3)

**Decision:** *All measured quantities in every analysis phase are derived exclusively from
`filtered_trades` / `filtered_quotes`. The `momentum_events` spine provides event identity,
universe membership (`in_scope`, `source_file`, window flags), and stratification metadata only.
Every numeric OHLC and volume column on the spine (`prev_close`, `open`, `high`, `low`, `close`,
`event_open`, `event_high`, `event_close`, `event_volume`, and any later-discovered price/size
column) is permanently quarantined from analysis — diagnostic display only, never combined with
tick data in any computed quantity. Caveat, permanent: `momentum_pct` is itself spine-derived and
remains the universe-selection and stratification variable; it is scale-invariant per row, but
event selection therefore inherits the vendor's RTH-scoped, adjusted-basis high forever. Every
premarket or extended-hours finding is conditional on that selection boundary.*

**Reasoning on record:** Phase 6b discovered defect #4 (spine-tick price disagreement, ratios
2x–539x on 20/56 dev v4 events) and Phase 6c's A6.1 retest, cohort stratification, and residual
classification (T1/T2) narrowed it to 7 residuals against a passing primary cohort (92.0% ≥ 90%
threshold). Amendment 7's diagnostic chart pack (`results/phase_6c/charts/`) tested three
pre-registered predictions against the two remaining `unexplained` residuals (SCLX, VEEE) using
an independent, price-free signal — T+0 tick volume vs. the spine's `event_volume`. The
volume cross-check falsified the thinness mechanism for SCLX/VEEE by direction: their tick volume
*exceeds* spine `event_volume` by 35.1x and 13.8x — a coverage gap can only produce a deficit, not
a surplus. It also showed AMC (a control that *passes* the price-ratio check) has an incoherent
price factor (5.24) vs. volume factor (10.06) — proving the defect is not confined to
price-ratio-failing events and cannot be screened out by any per-event price-agreement test.
Conclusion: the spine's numeric columns cannot be certified even on events that pass price-ratio
checks. Per-ticker factor characterization is not pursued; the dependency on the spine's numeric
columns is severed instead. See `results/phase_6c/artifacts/closure.json` for the full evidence
table (stratified criteria, 7-way classification, 9-row volume cross-check).

**Supersession:** This supersedes the price-only framing of Phase 6b Amendment 5's original
tick-anchor authorization — that amendment addressed price columns only; D4 extends the same
quarantine to every spine numeric column, including `event_volume`, and makes it permanent rather
than provisional pending a mechanism confirmation. The full-population basis audit contemplated
under Amendment 7 disposition (b) is superseded by D4 — a source that is never read requires no
characterization.

**Standing rule for all future phases:** No query computes a measured quantity (a ratio, a level,
a return, a volume share, a spread, anything reported as a finding) from any spine numeric column.
Spine numeric columns may appear in diagnostic output (a chart annotation, a cross-check table)
labeled as such, but never as an input to a computed statistic. `momentum_pct` remains the sole
exception per the caveat above — it selects and stratifies the universe, it does not measure
anything within a phase.

**How to apply:** any phase touching `momentum_events`' price/volume columns cites this decision
and confirms (per Amendment 8's A8.2 sweep requirement) that every reference is diagnostic-display
only, never computation. SCLX and VEEE remain classified `unexplained` in the permanent record —
closed by severance, not by explanation.

### D4 Amendment A9 — scope clarifications from the Phase 7 retroactive sweep

**Date:** 2026-07-24
**Deciding phase gate:** Phase 7 T1 (pre-approval — recorded at disposition, same pattern as D3/D4)

Phase 7 T1's retroactive D4 sweep (`results/phase_7/artifacts/d4_retro_sweep.json`) swept `src/` and
the approved-phase lineage for reads of the spine's 16 non-`momentum_pct` numeric columns and found
26 genuine hits: 18 `universe_selection`-class (all the `flag_bad_denominator` formula and its
re-derivations, one of them live in `src/data/canonical.py`) and 5 `computation`-class (Phase 2's
`momentum_pct_recomputed` junk statistic; Phase 1's `event_volume` reads from pre-ingestion
candidate files). Both triggered the sweep's escalation rows 2/3. Cooper's resolution, **zero code
changes** (full text: `results/phase_7/artifacts/t1_escalation_resolution.json`):

- **A9.1 — `flag_bad_denominator` is inside the `momentum_pct` exception.** D4's sole exception is
  extended to cover `flag_bad_denominator` as currently defined in `src/data/canonical.py`
  (`prev_close < prev_close_floor OR momentum_pct >= mom_sanity_cap`), on the grounds that it is a
  **reliability guard on the exempted column's denominator** — `prev_close` is the denominator of
  `momentum_pct = (high − prev_close)/prev_close`, so a floor check on it is part of guarding the
  exempted selection variable, not an independent measurement. No remediation. A register item is
  opened (`docs/Open-Items-Register.md`) to characterize the false-negative exposure of this guard —
  near-threshold `prev_close` vs. a tick-derived prior-session close — dev-tier or targeted,
  unscheduled.

- **A9.2 — the quarantine reaches pre-ingestion source files, prospectively.** D4's quarantine
  extends to the pre-ingestion `candidate_scan_inputs` parquet files (the spine's own construction
  inputs, same semantic columns at a different physical location) for **all future computation**.
  Phase 1's forensic reads (`research/phase_1/refit_boundary.py`, `research/phase_1/orphan_drift.py`)
  and Phase 2's `momentum_pct_recomputed` statistic (`research/phase_2/t2_quality_screen.py`) are
  **grandfathered as selection-mechanism audits** — register annotations only, no deletions, no
  recomputation.

- **A9.3 — universe-flag formulas are defined once (prospective standard).** Universe-flag formulas
  live once in `src/data/canonical.py`; research scripts read flag columns off the canonical view and
  never re-derive them. Recorded in `CLAUDE.md`. The 15 historical re-derivations enumerated in the
  sweep artifact are left as-is.

**How to apply:** `flag_bad_denominator` reads (via the view or the raw `prev_close`/`momentum_pct`
guard formula) are D4-compliant and need no diagnostic-display justification — they are inside the
exception per A9.1. Every *other* spine numeric column remains fully quarantined per D4 above. New
code derives no universe flag locally (A9.3). The sweep artifact is the enumerated, frozen record of
the pre-A9 state.

---

## D5 — Strategy surface and horizon class

**Date:** 2026-08-03
**Deciding phase gate:** `phase-7-approved` (documentation redirect, `prompts/redirect_d5.md` — not a phase)

**Selected surface:** intraday post-trigger (§3.3 surface #2), long-only, burst-scale horizons.

**Definitions.**
- *Burst* — a contiguous high-intensity trade-arrival cluster within a T=0 session.
- *Burst-relative anchor* — a measurement origin located at a burst confirmation timestamp, as opposed to session open, session close, previous close, or session high.

**What D5 selects.** §4 (trading intraday during high-participation windows) and §5 (regime detection, direction signal, end-detector) of `docs/Mom-DB-Strategy-Research-Program.md` become the program spine. The operating premise is: a strong bull impulse that flips sharply to a strong bear impulse, traded as a sequence of short-horizon long entries gated on regime, with minimized time exposure — not held to a fixed horizon.

**What D5 demotes.** §3.3's ranking of T+1 (day-2) as surface #1. T+1 is reduced to one optional measurement pass for the "does this archive contain any edge at all" read. It is no longer a program pillar and no longer precedes detector work.

**What D5 kills.** All short-side variants, including T+1 fade. The SSR and borrow-availability modeling requirement in §7.2 is void for as long as D5 stands. Long-only, for execution-logistics and risk-control reasons.

**What D5 does not change.** §7.2 cost model (always cross the spread, effective spread as cost basis, slippage scaled to observed spread and participation, halts modeled as forced holds through the reopen). §7.3 validation discipline (time-based splits, ticker-blocked splits, universe-boundary and cost sensitivity). D1, D2, D4. Flag-never-delete. Two-tier dev/full discipline. The chart contract and the Evidence Standard.

**Recorded consequences.**
- (a) Session-anchored opportunity-decay measurements — Phase 6 RTH-only, and Phase 6b as currently scoped — measure a quantity outside D5's horizon class. They are retained as archive. They are **not** the operative latency budget.
- (b) The latency budget under D5 must be re-derived burst-relative.
- (c) Risk-register items #3 (missing counterfactuals) and #4 (circularity of regime frequency) are upgraded from "must happen before capital" to near-front blockers. Under D5 the false-positive rate of a live screen is a direct PnL term, not a caveat.
- (d) The archive universe (q05 power-law filter applied to completed daily moves) and the intended live universe (real-time ≥30% from previous close, pre- and post-market inclusive) are different populations. This mismatch becomes a first-class open item.

**Left open by D5, to be decided before any detector phase is specified.** Whether the entry signal is *onset prediction* (firing ahead of the cluster) or *fast detection and ride* (confirmation inside the cluster). §4.2 condition 4 bears directly on this. D5 does not decide it.

---

## Related

- [[Open-Items-Register]] — the "2025 inclusion decision" item is closed there, referencing D1;
  defect #4 is closed there, referencing D4.
- `results/phase_5/REPORT.md` — the measurements (file2 flagged share, bitmap patterns) that
  motivated both decisions.
- `docs/Mom-DB-Strategy-Research-Program.md` §8 — risk register item #8, cited by D2.
- `results/phase_6_rth_only/` (formerly `results/phase_6/`) — the superseded RTH-only measurement
  that motivated D3; `results/phase_6b/` — the extended-day redo.
- `results/phase_6c/` — defect #4 diagnosis, cohort stratification, residual classification, and
  the Amendment 7 chart pack that produced D4's falsifying evidence.
