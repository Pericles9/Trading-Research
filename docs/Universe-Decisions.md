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

**D3 Amendment (Phase 10c, 2026-08-26) — session boundary and auction-print assignment.** Phase
10c needed a more precise session-boundary rule than "cast to an ET date" to correctly attribute
prints near a session close, and settled two standing conventions any future phase doing intraday
segment work should reuse rather than re-derive:

- **Trading day** = `(prior XNYS session close, this session's close]`, with bounds from
  `exchange_calendars`' own `session_close`/`session_open` — no fixed clock constant, so early
  closes and holidays resolve automatically. Within a day: `evening` (prior close → 20:00 ET),
  `premarket` (04:00 → 09:30 ET), `rth` (09:30 ET → this session's close). The 20:00–04:00 span was
  measured empty across the dev sample, not assumed so.
- **Auction-print assignment overrides the timestamp rule.** A print carrying vendor condition
  code 8 (Closing Prints) or 15 (Market Center Official Close) is assigned to the session whose
  close it settles, regardless of its timestamp — otherwise a closing-cross print a few
  microseconds past the close is bucketed into the *next* day's evening segment while its own twin,
  timestamped a moment earlier, stays in that day's `rth`: the tick stream disagreeing with itself
  about which session a print belongs to. Implemented as `assign_segment()` in
  `research/phase_10c/common.py`. **Standing limitation:** empirical plus semantic, not
  independently validated — the code set is confirmed to mean what the vendor dictionary
  (`docs/massive_trade_conditions.json`) says, not confirmed to capture every closing auction in
  the archive or exclude every non-auction print.

Full text and the resolution sequence: `results/phase_10c/REPORT.md` §2-3;
`prompts/phase_10c_amendment_{2,4,5,6}.md`.

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

### D4 Amendment A12 — the quarantine extends to cross-session tick price ratios

**Date:** 2026-08-03
**Deciding phase gate:** Phase 9 approval (`phase-9-approved`)

**The gap A12 closes.** D4 severed the dependency on the spine's numeric columns because their
adjustment basis is inconsistent per ticker and per column. The same inconsistency exists in the
**raw tick archive across a session boundary**: `filtered_trades` prices are stored as collected, so
a corporate action between two sessions changes the basis between them exactly as it does on the
spine. D4 as written is silent on this, because it was framed around *which table* a number comes
from. Phase 8 §18/§19 applied D4's within-day guard correctly and then computed
`t0_close → t1_close` and `t0_close → t3_close` ratios across that boundary anyway — tick-sourced
throughout, and still basis-mismatched.

**Decision:** *A price ratio spanning a session boundary is not certified by being tick-derived. Any
phase computing a cross-session ratio, level change, or return from tick data carries a
magnitude-based cross-session flag and reports the statistic with and without the flagged set. D4
governs the source; A12 governs the boundary.*

**Measured basis (Phase 9 T1/T2, n = 15,763 D1 events).** `flag_cross_session_extreme` =
`|log(p_later_close / p_earlier_close)| ≥ ln 1.8`, magnitude only — the detector encodes no
corporate-action judgment. Flag rates: (T−1,T0) 890/15,729 = 5.66%; (T0,T+1) 251/15,741 = 1.59%;
(T0,T+2) 450/15,744 = 2.86%; (T0,T+3) 623/15,747 = 3.96%. 1,484 events (9.41%) flagged on at least
one pair.

**Why the flag is mandatory rather than advisory.** On the pooled `t0_close → t1_close` statistic the
**median is robust** (−0.02782 → −0.02844) but the **mean simple return flips sign, +3.7308% →
−1.5253%**, and it flips in 10 of the 12 headline cells (every quintile and the 2022–2024 era at
both horizons; the two that do not flip were already negative). A phase reporting a cross-session
mean without the flag reports the wrong sign. This is a boundary problem, not a pricing-path
problem: Phase 9's session closes reproduce Phase 8's ASOF markouts exactly, `max|diff| = 0.000e+00`
over 31,380 pairs.

**What A12 does not claim.** The flag is **not** a corporate-action classifier. Phase 9's
integer-clustering diagnostic found the aggregate within-tolerance share (22.7–24.2% per pair) sits
*at or below* the rate expected by chance (24.7–28.4%), because the 3% bands are not measure-zero
(constant log-width 0.0600 for every `k`) and they touch at `k = 17`, above which membership is
automatic. Against a local background the excess is confined to `k = 2` (298 observed vs 210.07
expected, 1.42×), with `k = 3,4,5` at or below background. The flagged set is a **magnitude**
population that demonstrably contains reverse splits — not a certified corporate-action list. Do not
read it as one, and do not read the raw within-tolerance share without its chance baseline.

**Standing rule for all future phases:** any cross-session tick quantity carries the flag, ships
untrimmed as the primary, and reports the flagged set as its own row (never silently dropped — the
flag-never-delete rule is unchanged). **Denominators count:** a ratio whose *denominator* spans the
boundary is covered even when the numerator does not. Phase 9 T3's `retrace_excursion` denominator
`H − A` spans (T−1,T0) because `A` is a T−1 price and `H` is a T0 price, so the flag applies at every
horizon including same-day `t0_close`, not only at T+1…T+3.

**Home of the flag:** `results/phase_9/artifacts/t1_cross_session_flags.parquet`, per (event,
session-pair) — parallel to `flag_possible_row_cap` (Phase 8) and `flag_has_dup_prints` (6b).
**Not** in `src/data/canonical.py`; promoting it there is a separate Cooper decision, open in
[[Open-Items-Register]].

**How to apply:** any phase computing a quantity across a session boundary cites A12, states which
pairs it spans, and reports the with/without-flag pair. Within-day quantities are unaffected.

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

### D5 Amendment A11 — Phase 6b disposition: archive-only, no new run

**Date:** 2026-08-03
**Deciding phase gate:** Cooper decision at the D5 redirect (`prompts/redirect_d5.md` T6)

**Correction of the T6 premise.** T6 as written states that `prompts/phase_6b.md` and
`config/phase_6b.json` "are currently queued to resume the moment `phase-7-approved` exists, per
Amendment A8.2." That premise is stale. Phase 6b has already run and been approved — tag
`phase-6b-approved` exists, `prompts/phase_6b_amendment_8.md` is committed, and `results/phase_6b/`
is the declared baseline of Phase 8 (`event_minute_bars_v2`, 45,925,350 rows). The live question is
therefore not whether to resume 6b, but what standing its completed output has under D5.

**Decision: archive-only, no new run.**

- **6b's session-anchored extended-day decay output is archive.** It stays committed and citable. It
  is **not** the operative latency budget, exactly as D5 consequence (a) states. Any phase citing a
  6b or Phase 6 decay figure labels it as the session-anchored quantity and does not present it as a
  budget under D5.
- **No re-run, no re-scope, no successor phase is authorized by this amendment.** The burst-relative
  latency budget required by D5 consequence (b) will be derived by a phase specified on its own
  terms.
- **`event_minute_bars_v2` is unaffected as a data artifact.** A11 demotes 6b's *conclusions*, not
  its tables. Phases 8 and 9 both build on `event_minute_bars_v2` and remain valid; the D4 rule that
  every measured quantity is tick-derived is what makes that table load-bearing, and nothing in D5
  touches it.
- **A8.2's terms are not modified.** Its sweep requirement (every spine numeric reference confirmed
  diagnostic-display only) stands unchanged. A11 adds a disposition; it does not amend A8.2.
- **`prompts/phase_6b.md` and `config/phase_6b.json` are left exactly as committed** — the historical
  record of what ran, not a queue entry.

**How to apply:** cite A11 when reusing any `results/phase_6/` or `results/phase_6b/` decay
statistic, and state that it is session-anchored and superseded as a budget. Reuse of
`event_minute_bars_v2` itself needs no citation.

---

## D6 — Burst measurement moves from segmentation to intensity profiling

**Date:** 2026-08-04
**Deciding phase gate:** Phase 10 v1 approval gate — failure criterion row 0 fired (segmentation rejected on Cooper's visual review against the tape)
**Supersedes:** the operational reading of D5's burst definition ("a contiguous high-intensity trade-arrival cluster within a T=0 session")
**Affects:** Phases 10, 11, 13, 14, 16, 17

**Decision.** The T=0 session is **not segmented into bursts**. A continuous relative-intensity profile is measured instead. D5's requirement — a burst timescale to anchor every downstream horizon — is satisfied from the *shape* of the intensity profile rather than from burst boundaries. There is no burst count, no burst spacing, and no per-burst move share. Those quantities are **withdrawn as deliverables**.

**Why.** Both Phase 10 arms failed, in opposite directions, from a shared assumption: **that a quiet state exists on T=0 to detect bursts against.** It does not.

- **Evidence 1 — the session is uniformly extreme.** Whole-session T=0 arrival rate against the flanking-day baseline rate, n=96: median **78.5×**, 5th percentile 2.5×. **86% of events exceed Arm B's own 4× on-threshold on a whole-session average basis.** By its own rule the entire session qualifies. There is no within-session baseline to threshold against; the baseline is the T− days.
- **Evidence 2 — Arm A's burst count measured the data, not the market.** Spearman correlation between burst count and T=0 print count: **+0.96**, log-log slope 0.85. Median burst duration falls 11.4 s → 0.6 s across print-count quartiles. Kleinberg's two-state automaton assumes exponential inter-arrival gaps within a state; trade arrivals are heavy-tailed, so the Viterbi path flips state to accommodate gaps the model considers impossible. More prints, more flips. Compounding this, the transition cost scales as `gamma × ln(n)` while transition opportunities scale as `n` — fragmentation wins by construction as sessions get busier.
- **Evidence 3 — Arm B's denominator was unusable.** Flanking-day density: median **2.8 prints/min**, 45% of events below 2/min, 27% below 0.5/min. 73 of 100 analysis-cohort events carry `baseline_partial`. An intraday shape cannot be estimated from that material. The result was a per-minute z-score with **median −1.26 and 25th percentile −17.7** on sessions running 78× hot — an unstable variance denominator on thin names, where an empty T=0 minute scores −18. That flicker is what fragmented a uniformly elevated session into ~25 pieces. Merge-and-dwell then rescued the fragments into approximately-correct blobs, which is why Arm B looked accurate while being imprecise.
- **Evidence 4 — the same misspecification killed the earlier Hawkes work.** A branching ratio pinned at criticality is a documented failure signature, not a finding. Filimonov & Sornette (2015), *Apparent criticality and calibration issues in the Hawkes self-excited point process model*, show that calibration on mixtures of Poisson processes with regime changes yields spurious apparent critical values of n≈1 when the true value is n=0, and that regime shifts systematically bias the branching ratio upward. Constant-baseline Hawkes on a session whose intensity varies by orders of magnitude can only express that variation through self-excitation, so it maxes out self-excitation. The Hawkes project and the burst-detection project are one dead end found twice, not two.

**What the data does support.** Roughly 85% of session prints fall in 15–33% of session clock time. There is real concentration within the session — it is simply not two-state structure, and it is not resolvable by thresholding.

**What replaces the burst timescale.**

| Old deliverable | Replacement |
|---|---|
| Burst count per event | *(withdrawn)* |
| Burst duration, spacing | Decay timescale of the intensity profile |
| Burst-relative concentration curve | Peak-anchored and detection-anchored intensity profile |
| Burst confirmation as anchor | Peak intensity and scanner detection time as anchors |
| Latency budget | **Time from detection to peak intensity** |

**Time from detection to peak intensity is the runway.** It requires no baseline, no threshold, and no calibration. If that distribution is centred at 90 seconds, every downstream phase is a 90-second problem. If peak intensity routinely *precedes* detection, that is a first-order finding about the entire program and the segmentation approach could never have surfaced it cleanly.

**Method constraints carried into Phase 10 v2.**
- **Shape uses no baseline.** Each event's rate curve is normalized by its own peak. This also cancels the price-level print-fragmentation effect on level, which was the artifact behind Evidence 2.
- **The flanking days retain exactly one job: the terminal condition** — has activity returned to normal. That requires a single scalar per ticker, not an intraday shape. 2.8 prints/min is sufficient for a scalar. The saturation objection that killed whole-day baselines for segmentation does not apply, because a smooth decaying curve is read once at its crossing rather than thresholded continuously.
- **Time-of-day matching is abandoned.** Not because of non-stationarity in event timing — a clock-matched denominator does not assume events align — but because the flanking material is too thin to estimate an intraday shape at all. Recorded here so the reasoning is not re-litigated from the wrong premise later.
- **Rate estimation must be adaptive.** Within-session arrival rate spans several orders of magnitude. Fixed-width binning is not acceptable: any bin width adequate at the peak is empty in the tails and vice versa. An adaptive estimator whose resolution follows local density is required.

**Recorded consequences.**
- (a) Phase 10 is re-scoped. `prompts/phase_10.md` is replaced by `prompts/phase_10_v2.md`; the segmentation version is superseded, not amended.
- (b) Phase 10's Arm A and Arm B artifacts are retained as the evidentiary record for this decision and are **not** inputs to any downstream phase.
- (c) Phase 14's regime-label design no longer inherits a burst segmentation. It inherits an intensity profile and its timescales.
- (d) Phase 13's scope is unchanged — inter-trade interval distributions remain its deliverable.
- (e) Any downstream phase that anchored a horizon to "burst confirmation" re-anchors to peak intensity or detection time. Both are pinned in Phase 10 v2.

**Standing lessons.**
- **Parameter stability is not evidence of correctness.** All four pre-registered numeric failure criteria passed. Row 3 — parameter stability — passed comfortably on both arms (median interval Jaccard 0.77 and 0.93). Both arms reliably produced the same wrong answer under perturbation. Stability tests detect noise sensitivity; they cannot detect a wrong model. Future pre-registration must not treat a stability pass as acceptance.
- **Cross-arm agreement was the loudest signal and nothing was watching it.** Median interval Jaccard between arms: **0.31**, with zero events agreeing on burst count. Where two independently-motivated methods are run, their disagreement requires a pre-registered threshold of its own.
- **Row 0 earned its place.** Cooper's visual review against the tape was the only criterion that fired, and it fired correctly. It stays as the top row of every future failure table.

**How to apply:** cite D6 before using any `results/phase_10/` Arm A or Arm B artifact — they are evidence for this decision, not measurement inputs. Any phase inheriting a "burst-relative" anchor from D5 re-anchors to peak intensity or detection time.

---

## D7 — The detection anchor is derived, not sourced

**Date:** 2026-08-04
**Deciding phase gate:** Phase 10 v2 escalation row 9, raised at T0a and resolved by `prompts/phase_10_v2_r1.md`

**What was wrong.** `prompts/phase_10_v2.md` T2b specified the detection timestamp as "taken from the canonical spine." **No such column exists, and never did.** `momentum_events_canonical` carries no timestamp column of any kind; the underlying `momentum_events` spine has `date` and `event_date` as date-only strings and `created_at` as a record-creation field. The prompt asserted a source without verifying it, on the input that produces the phase's headline number. T0a caught it before any measurement ran.

**Decision.** Phase 10 v2's detection anchor is **derived from the tick archive under a pre-registered rule, at a pre-registered set of polling intervals**. It is not sourced from the spine, and it is not the Phase 8 `det_minute` artifact.

**Definition.**
- **Reference price:** tick-derived T−1 regular-hours close. Phase 8 already computes this as `tick_close_t_minus_1_rth`; reuse the definition, recompute the value.
- **Trigger:** the running maximum of T=0 trade price reaching or exceeding `threshold × reference`.
- **Threshold:** 1.30 at the reference point, matching universe construction. Carried as a config parameter with its own sensitivity grid.
- **Detection time:** the first poll boundary at or after the trigger.

**Why the polling interval is mandatory and not a refinement.** Defining detection as the instant of crossing produces a detection time no real scanner could achieve — no polling interval, no feed latency, no bar close. That biases detection-to-peak **upward**: more apparent runway than exists. It is the optimistic direction, on the number every downstream phase is anchored to. Making the interval an explicit parameter is the only way that bias stays visible. **The instantaneous-poll variant is the explicit upper bound on runway and is labeled as such on every chart and in every table where it appears. It is not a candidate operating point.**

**Pinned grids.** Poll intervals: instantaneous, 1 s, 5 s, 15 s, 60 s. Thresholds: 1.25, 1.30, 1.35.

**Never-crosses.** Events in-universe whose tick crossing does not exist are an expected consequence of D4 — the universe was selected on `momentum_pct` computed from quarantined spine numerics, and the anchor is re-derived on tick. They are **flagged, carried, and reported as their own row. Never dropped, never imputed, never resolved by falling back to a spine value.** The count is a headline number.

**Detection segment.** Each event is tagged premarket / regular-hours / after-hours by its detection time, per the pinned XNYS calendar. Segment is a **conditioning variable carried through every Phase 10 v2 timescale table**, not a footnote.

**Stated limitation.** Detection comes from a price threshold; peak comes from arrival intensity; both are computed from the same T=0 tick stream. These are different quantities and the comparison is legitimate, but the two anchors are **not independently sourced**, and every report using them says so.

**Recorded consequences.**
- (a) `prompts/phase_10_v2.md` T2b is replaced by the definition above.
- (b) Escalation row 9 is replaced: a derived anchor undefined for any reason *other than* the pre-registered never-crosses condition is a hard stop; never-crosses events are not an escalation.
- (c) Escalation row 13 is amended to permit **append-only** writes to `docs/Universe-Decisions.md` and `docs/Research-Library-Map.md`. The prior allowlist made it impossible to record a decision where decisions are recorded — a prompt defect that surfaced in Phase 10 v1 and reproduced in v2.
- (d) Every T3/T4/T5 quantity referencing detection is computed **per poll interval**, and the detection-to-peak distribution is a **family indexed by polling interval**, not a single distribution. The spread across that family is a headline number.

**How to apply:** cite D7 wherever a detection time is used in or after Phase 10 v2, and state the poll interval with the number. A detection-anchored figure quoted without its poll interval is incomplete.


## D8 — Sub-burst structure, measured against the event's own envelope

**Date:** 2026-08-04
**Deciding phase gate:** Phase 10 v2 hard stop — pre-registered failure rows 1, 2, 3 and 6 fired
**Supersedes:** `prompts/phase_10_v2.md` and `prompts/phase_10_v2_r1.md`; reverses D6's abandonment of within-session structure while retaining D6's diagnosis
**Affects:** Phases 10, 11, 13, 14, 16, 17

**Decision.** Phase 10 measures sub-burst structure within the T=0 session, using the event's own slowly-varying intensity as the reference level. D6's abandonment of within-session structure is reversed. D6's diagnosis is retained.

**What D6 got right and what it got wrong.** D6 correctly established that no quiet state exists on T=0 — the session runs a median 78× above flanking baseline throughout, so there is nothing to threshold against. That finding stands. D6 then drew the wrong conclusion from it: that within-session structure should be abandoned in favour of one global peak and one decay number. That discarded the structure the trading thesis depends on. An event-level decay figure cannot inform intraday entry or exit; sub-burst structure can.

**The actual defect, common to all four prior attempts.** Every method so far compared a fast-varying arrival rate against a reference level that does not describe the data:

| Attempt | Reference level | Failure |
|---|---|---|
| Arm A (Kleinberg) | session mean rate, constant | rate varies by orders of magnitude within the session; burst count correlated **0.96** with print count |
| Arm B | flanking-day, time-of-day matched | too thin to estimate — median 2.8 prints/min, 73/100 `baseline_partial` |
| Hawkes (prior project) | constant exogenous baseline | branching ratio pinned at criticality, a documented misspecification signature |
| v2 | none — one global peak | discarded within-session structure entirely; decay timescale ill-posed, four rows fired |

**The reference level must track the event.** Sub-bursts are excursions above the event's own envelope, not above a constant. This repairs Arm A's defect at the root: burst count correlated with print count because a fast rate was compared to a fixed level, so more prints produced more crossings. A reference that follows the event removes that mechanism rather than tuning around it.

**Conditional on a scale separation existing.** Envelope-and-excursion is only well-posed if the intensity process has a characteristic clustering scale — a slow band for the envelope, a fast band for the sub-bursts, and a gap between. If the process is self-similar, no principled envelope bandwidth exists and any choice manufactures the sub-bursts it then finds. That is Arm A's failure in new clothing. Phase 10 v3 T1 tests this with the Allan and Fano factors computed directly on the point process — no intensity estimation, no smoothing bandwidth, no threshold — and it is a **hard gate**.

**Recorded consequences.**
- **(a)** v2's one-global-peak framing and its T3c decay timescale are withdrawn.
- **(b)** v2 artifacts are superseded, not deleted, and retained as the evidentiary record. Renamed `*_v3_superseded` with a header pointing here.
- **(c)** These v2 results survive and carry forward: the derived detection anchor (110/110 exact against Phase 8 `det_minute`, reference-price deviation 0.000e+00); detection-to-peak (median ~1,976 s at the 1 s poll, poll-grid ratio 1.010); the ~28% negative share; the segment split (premarket 0% negative, regular-hours 40%); the adaptive nearest-neighbour intensity estimator.
- **(d)** Detection segment becomes a **stratification variable from the start**, not a discovery. Premarket and regular-hours events differ by three orders of magnitude on v2's decay statistic and 40 points on negative share.
- **(e)** If T1's gate fails, D5's premise is wrong — no burst timescale exists to anchor downstream horizons to — and Phases 11, 13, 14, 16 and 17 re-anchor to detection, clock time, or price-path events. That is a first-order program finding, not a phase failure.

**How to apply:** cite D8 before treating any within-session intensity structure as measurable. Any method comparing a fast-varying arrival rate to a constant reference level is closed by this decision, as are two-state segmentation and constant-baseline Hawkes calibration; reopening any requires a numbered decision.


## D9 — Sub-bursts are detected from locally-normalized log inter-trade intervals

**Date:** 2026-08-04
**Deciding phase gate:** Phase 10 v3 rejected on failure row 0 (Cooper's visual review of chart 07 against the tape)
**Supersedes:** `prompts/phase_10_v3.md` (envelope-and-excursion), which superseded v2 and v2_r1
**Affects:** Phases 10, 11, 13, 14, 16, 17

**Decision.** Sub-bursts are identified by thresholding the inter-trade interval, where the threshold is derived per event from the trough of its own locally-normalized log-interval distribution. v3's envelope-and-excursion approach is withdrawn.

**Why.** Every prior attempt required estimating an intensity curve, which required choosing a smoothing scale, which made the answer track the estimator. Arm A's burst count correlated **0.96** with print count for this reason. v2's rows 1 and 6 failed for this reason. v3 carried it in the envelope bandwidth — and although v3's Arm A test passed (Spearman 0.277/0.353), its row 3 failed at a median interval Jaccard of 0.0735 between sub-burst sets computed at the two ends of its own knee interval, which is the same defect surfacing one level up. **Operating on intervals directly removes the mechanism rather than testing for it after the fact.**

**Prior art.** This is standard practice in two mature fields and was not invented here.

- **Neuroscience — spike train burst detection.** The log-interval histogram method (Selinger et al. 2007; Pasquale et al. 2010) locates peaks in the log-transformed interval histogram and sets the threshold at the minimum between the intra-burst peak and subsequent peaks. It carries a **void parameter** measuring peak separation, with a conventional cutoff of 0.7; where no intra-burst peak exists, no bursts are declared. Ko et al. (2012) handle non-stationary rate by normalizing log intervals against a **moving window of roughly 20% of the sequence**, reporting under 0.3% change in detected counts anywhere between 10% and 30%. Kapucu et al. (2012) derive thresholds from the cumulative moving average and skewness of the interval histogram, built for time-varying dynamics.
- **Seismology — earthquake declustering.** Baiesi & Paczuski (2004), extended by Zaliapin & Ben-Zion (2013, 2020), separate clustered from background events using the bimodality of a nearest-neighbour distance whose proximity metric scales with event magnitude — the window widens for larger events by construction.

**The warning that shapes this phase.** Zaliapin & Ben-Zion found the bimodality that separates clustered from background events is often violated in the vicinity of the largest earthquakes, where triggered activity dominates and a simple threshold between modes stops working. **Our entire T=0 session is that vicinity.** The void parameter is therefore a live gate, not a formality, and it is expected to fail on some events. **The share of events where it fails is a headline result, not an inconvenience.**

**Everything in this phase is offline and non-causal.** The threshold, the void gate, and the normalization window all read the completed session. This is correct for label construction and useless for trading. Phase 17's online detector must re-derive every one of these under causality, and this phase's job is to hand it a defensible target, not a tradeable rule.

**Recorded consequences.**
- **(a)** *(corrected against the record — see the editorial note below)* v3 is withdrawn. It **was executed in full** before withdrawal, and its artifacts exist and are retained as evidentiary record alongside v2's.
- **(b)** v2 artifacts remain the superseded evidentiary record per D8(b).
- **(c)** These carry forward unchanged: the frozen cohort (`e1a0ac73a79aa573`); the D7 detection anchor (110/110 exact against Phase 8, reference deviation 0.000e+00); detection-to-peak (median ~1,976 s, poll ratio 1.010); the ~28% negative share; the segment split.
- **(d)** D8's scale-separation gate is withdrawn as a separate task. The void parameter supersedes it: per-event rather than pooled, and computed as part of the method rather than alongside it. *(Note: that gate PASSED when run — see the editorial note.)*
- **(e)** Detection segment remains a stratification variable from the start.

**Editorial note on consequence (a), recorded because a decision record must not contradict the repo.** The D9 text as drafted states "v3 is withdrawn before execution; no v3 artifacts exist." That is not what happened, and it is corrected above rather than transcribed. Phase 10 v3 ran to completion on 2026-08-05:

- its T1 Allan/Fano scale-separation **gate PASSED** on all four segment-by-observable cells (knees 128 s rth / 16 s premarket for the print observable, ΔBIC 45.6–68.7, slope changes 0.61–0.87);
- its failure **row 1 — the Arm A test — PASSED** for the first time in the phase (Spearman 0.2772 / 0.3531, log-log slope 0.2605 / 0.1849, against Arm A's 0.96 and 0.85);
- rows 2, 3 and 4 fired, row 3 most severely;
- **Cooper then rejected it on row 0**, visual review of chart 07 against the tape.

v3's artifacts are committed under `results/phase_10/artifacts/v3_*` with report and digest at `results/phase_10/{REPORT.md, digest.json}` (status `rejected`). Two v3 results are load-bearing for D9's own reasoning and would be lost if the record said v3 never ran: the demonstration that **a characteristic clustering scale does exist** in this data, and the demonstration that **an event-relative reference breaks the print-count dependence** that sank Arm A. D9 supersedes v3's *method*; it does not erase v3's *evidence*.

**How to apply:** cite D9 before any within-session sub-burst work. Intensity estimation, envelope fitting, constant-reference thresholding, two-state segmentation and constant-baseline Hawkes calibration are all closed (D6, D8, D9); reopening any requires a numbered decision. A `no_threshold` event is never given a fallback threshold.


## D10 — Phase 10b scoping and numbering

**Date:** 2026-08-06 · **Deciding phase gate:** Cooper decision at the Phase 10 close-out

**Decision:** The arrival-randomness work is numbered **Phase 10b**, not Phase 11. It is a direct continuation of Phase 10 — same object, better-founded methods — and the numbering says so.

**Consequence:** Operating Plan §6 row 11 (*Spread & impact by participation*) is **preserved unchanged**, along with rows 12–19. The row-*n*-is-`prompts/phase_{n}.md` contract established 2026-08-03 is not broken and no downstream row is renumbered.

**Recorded alongside:** row 11's participation-bucketed effective-spread half does not depend on a burst timescale and is executable independently of Phase 10b's outcome. Only its "burst vs. quiet" half is blocked. This is recorded so the cost-stack measurement is not treated as blocked in full by Phase 10's failure.

**How to apply:** cite D10 when reading the Operating Plan §6 map — row 10b sits between rows 10 and 11 and is not a renumbering of anything. Phase 10 itself is closed at tag `phase-10-approved` as a recorded negative result (no burst timescale established); D10 does not reopen it.


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


---

## D11 — The Allan knee cannot recover a cluster timescale

**Date:** 2026-08-13 · **Gate:** Phase 10b close-out

The piecewise-linear breakpoint on a log-log Allan curve is a **sharp but biased** estimator of
cluster timescale. Across 500 draws per control its 95% interval spans 0-1 rung while the injected
scale falls inside that interval on **0 of 4** controls. Bias is +0.97 to +1.61 rungs on single-scale
controls and -2.91 rungs on the coarse transition of a two-scale control. The bias is a deterministic
consequence of fitting straight lines to a smoothly-curving function - the fitted asymptotes
intersect inside the transition region, pushing a fine transition up and pulling a coarse one down.
It is **not** a fixed offset: it depends on the separation between scales, which is unknowable on
real data. **No burst timescale is established by this program.**

Evidence: `results/phase_10b/amendment_2/artifacts/t2_bias_consistency.json`,
`results/phase_10b/amendment_2/charts/11_knee_sampling_distribution.html`,
`results/phase_10b/REPORT.md`.

## D12 — v3's Allan knee carries a scale-dependent uncertainty

**Date:** 2026-08-13 · **Gate:** Phase 10b close-out

v3's regular-hours knee at 128 s and premarket knee at 16 s are flat->rise transitions, structurally
the same kind of transition that carries the -2.91 rung (factor 7.5, downward) bias on control C4.
Applying single-scale bias instead gives +1.4 rungs (factor 2.6, upward). **The true scale behind
v3's 128 s therefore sits somewhere in roughly 50 s to 1,000 s, and behind 16 s in roughly 6 s to
120 s.** These ranges are too wide to anchor a trading horizon. v3's knee remains valid as evidence
that a transition **exists**; it is not valid as a measurement of **where**.

Verified against artifact: the 128 s and 16 s figures are the POOLED median-curve fits in
`results/phase_10/artifacts/v3_t1_gate.json` (`segment_fits.print_rate.{rth,premarket}.fit.
knee_seconds`), delta-BIC 45.614 / 68.653 / 53.103 / 49.563 across the four configured cells. The
per-event medians in `v3_t1_gate_knees.parquet` are a different object (rth 64 s) and are not what
this decision refers to.

## D13 — D5's premise fails; downstream phases re-anchor

**Date:** 2026-08-13 · **Gate:** Phase 10b close-out

D5 required a burst timescale to anchor every downstream horizon. No such timescale is available at
usable precision. **Phases 13, 14, 16 and 17 re-anchor to detection time, clock time, or price-path
events** rather than to a burst scale. The specific re-anchoring for each phase is scoped when that
phase is drafted; this decision records only that the burst-scale anchor is unavailable. **This is a
first-order program finding, not a sixth failure.**

## D14 — Environment is offline

**Date:** 2026-08-13 · **Gate:** Phase 10b close-out

No package index, no R, no network fetch. Any prompt requiring an external package, a reference
implementation, or a downloaded artifact must state an offline fallback at drafting time.
`reuse-before-build` applies only to what is already installed.

## D15 — Phase 11 reads the quote/trade coverage columns from the Phase 4/5 materializations

**Date:** 2026-08-15 · **Gate:** Phase 11 Amendment 1, approved by Cooper before T1 ran

`momentum_events_canonical` is a VIEW. Its `quotes_ingested` and `trades_ingested` columns are
computed by `SELECT DISTINCT ticker, event_date, round(momentum_pct,2)` over `filtered_quotes`
(3.8B rows) and `filtered_trades` (4.95B rows) — **at every reference to the view**.

`CLAUDE.md` requires every quote-derived statistic to filter on `quotes_ingested = TRUE`. Phase 11
Stage A budgets **zero** full passes and Stage B budgets **exactly one**. Those three constraints are
mutually unsatisfiable: obeying the standing rule through the view costs a scan every time, and the
conflict binds Stage A as well as Stage B because T2e is a quote-derived statistic. The cost is also
query-shape dependent — Phase 5a's dev-tier ASOF join through the same view returned in 17.1 s while
the Phase 11 T0b audit query was still running at 120 s and was killed — so it never appears in a
runtime estimate until it fires.

**Decision.** For Phase 11, `quotes_ingested` and `trades_ingested` are read from:

- `results/phase_5/artifacts/quotes_bitmaps_all.parquet` (20,951 rows)
- `results/phase_4/artifacts/_actual_quotes_sessions_cache.parquet` (115,904 rows)

Phase 4's three-way disk ↔ DB ↔ spine reconciliation stands as the verification; no new scan is run
to re-verify. Join-key compatibility was checked at T0c: **15,369 of 15,369 detection-universe events
match on (ticker, event_date_canonical, round(momentum_pct,2)), 0 unmatched.**

**Scope.** Phase 11 only. This is a phase scope decision, **not** a change to the canonical view.
`src/` is not touched, per "nothing in `src/` changes mid-phase". The standing rule itself is
unchanged — every quote-derived statistic still filters on `quotes_ingested = TRUE` and still reports
the n excluded. D15 changes only **where that column is read from**. Every artifact and every chart
caption states the coverage source explicitly.

**Open item, not this phase.** The canonical view should compute the coverage columns from a
materialized table rather than a live `DISTINCT`. That is a `src/` change and belongs in a
maintenance phase. Recorded in `docs/Open-Items-Register.md`, including the observation that prior
phases' runtime figures may embed this cost invisibly.

## D16 — Instrument reference convention for all quote-derived work

**Date:** 2026-08-16 · **Gate:** Phase 11 T4, Amendment 2 A2-2

For Phase 11 and all subsequent quote-derived work: the reference midpoint is the **contemporaneous
consolidated best quote at δ = 0 on the `sip_timestamp` basis**, with `sequence_number` as the
secondary ASOF key. **A single basis is used across all segments.**

**Offset — δ = 0, not the +100 µs peak.** Phase 11 T3 measured the peak at 0.0003 above the δ=0
at-or-inside share, while the between-segment peak instability was 7 sweep rungs. Selecting the peak
would fit a signal two orders of magnitude below the measured noise. δ=0 is contemporaneous and
requires no appeal to a fitted value.

**Basis — `sip`, single, whole phase.** Differences are marginal in both directions (sip higher in
RTH, 0.9808 vs 0.9779; participant higher in premarket). Segment is a headline reporting axis, so
switching basis by segment would place a measurement artifact directly on the axis being compared
across. `sip` wins in RTH, the cell escalation row 11 names. The `participant_timestamp` medians ship
as a robustness table (T6e): not primary, not charted, no claim resting on it.

**Tie handling.** `sequence_number` never inverts under the sip sort on any of the 50 dev-primary
events and breaks all 58,465 tied-sip rows uniquely. Use it; never fall back to arbitrary order.

## D17 — Quote-state exclusion rule

**Date:** 2026-08-16 · **Gate:** Phase 11 T4, Amendment 2 A2-3

A quote row is **excluded** if crossed (`bid > ask`), price null or ≤ 0, one side missing, or
`bid_size`/`ask_size` null or zero. **Locked quotes (`bid = ask`) are carried** — a real transient
state with a genuine zero spread, and dropping it biases measured spread upward.

**No event is excluded on quote-quality grounds.** The dirtiest dev event reaches 12.8% unusable
time; excluding events on a quality metric is post-hoc selection. Instead `unusable_time_share` is
carried per event × segment as a covariate in `event_quote_metrics_v1`, and T7g reports the headline
with and without the events above 1% unusable share.

The choice is not load-bearing: Phase 11 T2 measured RTH `state_hard_unusable` at a median of exactly
0.000000 (p95 0.0073), with `one_side_miss` and `null_price` occurring in zero of 150 T=0 cells.

Relative to Phase 11 Stage A's census vocabulary, D17 = `state_hard_unusable` ∪ the zero-size
predicates, **minus** locked. Stage A's `state_degraded` bundled locked together with zero-size;
D17 separates them.

## D18 — Stage B population and the decision cell

**Date:** 2026-08-16 · **Gate:** Phase 11 T4, Amendment 2 A2-4

Stage B computes all **15,369** detection-universe events and reports all three segments. **The
viability decision rests on the RTH cell alone.** Premarket and post are reported and charted; no
kill/clear decision is taken from them.

`quotes_ingested = FALSE` is excluded per D15 and counted as its own row in the filter waterfall.
There is **no staleness-based event exclusion**.

The RTH-only decision cell was already justified on sign in Phase 9. Phase 11 Stage A adds a second,
independent justification: premarket median quoted spread 760.3 bp with 62.3% of trades on quotes
older than 1 s and 30.7% older than 60 s; post 250.6 bp with 75.3% / 44.3%.

## D19 — Spreads and costs are reported in both units, and baselines are not proxies

**Date:** 2026-08-16 · **Gate:** Phase 11 T4, Amendment 2 A2-6

Every spread and cost quantity in this program is reported in **both basis points and cents**.
Neither unit is reported alone. **No baseline-session (T−1, T−3) spread is used as a proxy for
detection-time cost**, in either unit.

Phase 11 T2e measured the RTH median time-weighted quoted spread at 165.0 → 127.6 → 83.9 bp across
T−3 / T−1 / T=0 — a 49% fall — while the same cells in cents go 3.64 → 3.43 → 3.79, a 4% rise.
Backing the implied price out of each bp/cents pair gives ≈ $2.21 at T−3 and ≈ $4.52 at T=0. **The
basis-point compression is the denominator growing**; the absolute spread is flat to slightly wider
on the event day.

Two structural consequences: detection fires after a ~30% move, so the bp spread at detection is
mechanically compressed relative to the baseline session; and a cost estimate built from a
baseline-session spread therefore overstates detection-time cost in bp.

Guarded by Phase 11 escalation row 27.

## D20 — Sub-bursts are assembled under a merge tolerance and a run-length floor

**Date:** 2026-08-26 · **Gate:** Cooper decision at the Phase 10c close-out

**Numbering note, recorded rather than silently corrected.** `prompts/phase_10d_spec.md` §7 drafts
this decision as **D15**, on the stated belief that "D1–D14 are taken". They are not: **D15–D19 were
appended by Phase 11** (D15 coverage-column source, D16 instrument reference convention, D17
quote-state exclusion, D18 Stage B population, D19 spread/cost units). `CLAUDE.md`'s pointer list
also stops at D14 and is stale in the same way. Appending a second D15 would collide with a
committed decision and corrupt the register, and the append-only rule leaves no clean way to
renumber afterwards. **The number is therefore D20; every other word below is the spec's §7 text
verbatim.** Confirm or override the renumber.

**Amends:** D9's assembly rule only. D9's operating variable, its normalization and its
decline-rather-than-invent convention stand, as does 10c's argmax-void threshold selection.

**Decision.** A sub-burst is a maximal run of sub-threshold intervals **under a pre-registered merge
tolerance and a pre-registered minimum run length**, both reported as grids whose reference cell
reproduces the prior rule exactly. Whether a merge may bridge an interval excluded by the data floor
is governed by a pre-registered **separator rule**, reference `hard_break`, with the alternative
reading reported alongside.

**Why.** Two independent mechanisms fragment the object population, and neither depends on the
threshold being wrong. Strict consecutiveness splits one sustained burst whenever a single interval
crosses back over the threshold — or whenever the local window was too thin to normalize against,
which is a data-quality artifact and not market behaviour. And with no run-length floor, every
single-interval run is emitted as a sub-burst; a single-interval object is one gap with no internal
structure and cannot be a burst under any reading. Both deflate duration **by construction**,
independently of threshold location.

**What does not change.** The operating variable. The centered clock-time window at 10c's
specification, `trailing` and `anchored_to_detection` still forbidden. The three kernels.
**argmax-void selection with no cutoff** — `threshold: null` remains deliberate and permanent.
Histogram, bin grid, peak-survival rule. D4. Segment stratification across all four segments.
`insufficient_context` carried, labelled, never given a fallback.

**Recorded alongside.** Every grid is reported in full and never selected after seeing results. **The
phase's deliverable is the attribution** — how much of any duration shift is floor-driven and how
much merge-driven — not a single improved number. **And separately:** 10c cannot decline on void
magnitude, so it produces no bimodality-failure share; D9 holds that share to be a headline result.
10d reports the void distribution and the counterfactual declined share at candidate cutoffs **as
description, applying none.** Whether an applicability gate should exist is left open.

**How to apply:** cite D20 alongside D9 for any sub-burst assembled after 2026-08-26. **A sub-burst
figure quoted without its merge tolerance, its run-length floor and its separator rule is
incomplete**, as a detection-anchored figure quoted without its poll interval is incomplete under D7.

## D21 — Threshold-from-trough is closed; the log-interval representation is not

**Date:** 2026-08-27 · **Gate:** Cooper's visual review against the tape, **10d-R0 fired**

**Closes:** D9's operational instruction — that a sub-burst threshold is derived per event
from a trough of its locally-normalized log-interval distribution — and every version built
on it: v4, 10c, 10d.

**Decision.** No sub-burst boundary is derived by selecting a trough from the
locally-normalized log-interval histogram. This closes first-trough selection, argmax-void
selection, any cutoff on the void parameter, and **any exact-partition replacement**, because
the defect is the premise that a privileged boundary exists rather than the method used to
locate one.

**Why.** On this data the histogram is richly multimodal, not bimodal: **99.8% of frames
carrying a boundary hold three or more surviving peaks** (median 8 peaks, median 7 candidate
troughs), and the two-peak case the void parameter presumes occurs in **4 of 2,308 frames**.
Candidate troughs form a smooth gradient — median location rising **35×** from rank 0
(4.449 ms) to rank 8 (153.887 ms) while void falls smoothly from 0.893 to 0.488, median
winner–runner-up gap **0.0511** — so any selection is a cut on a continuum. The selection is
unstable across frames sharing **87.5%** of their data: the winner relocates by more than
0.5 decades between **27.3%** of adjacent frame pairs and by more than a full decade between
**17.5%**. The rule is systematically biased to the fine end — **26.53%** of candidates reach
100 ms against **6.73%** of winners. And it is partly an artifact of the window: the winner's
absolute location scales across kernels with a log-log slope of about **0.48**, roughly the
square root of window size, so neither a structural interval nor a pure denominator effect.
The window-basis defect (10c) and the assembly defect (10d) were both real and both fixed,
and the method still fails.

**On the scale figures, stated as a matched pair.** v4's pooled median sub-burst duration was
**349 ns** (n = 114,074, v4's 100-event analysis cohort). 10c's pooled median across its three
kernels is **1.294 ms** (n = 170,722, the 56-event dev sample) — a factor of **≈3,707**. 10d's
identity cell at the 8-minute primary kernel is **1.751 ms** (n = 46,709), a factor of ≈5,017
against v4. The close-out draft paired "1.75 ms" with "~3,700"; those are different cells and
the pair is corrected here. **The cohorts also differ**, so every one of these comparisons is
across populations, not like-for-like. Either way the result is four orders of magnitude short
of a tradeable scale and the conclusion is unchanged.

**What is NOT closed.** The locally-normalized log-interval field itself. It is legible and
carries persistent structure that moves through the session. What is closed is collapsing it
to one boundary per event. **D9's representation stands; D9's operational instruction does
not.**

**Consequence.** D5's burst-relative anchor remains unavailable, as D13 already recorded.
**No downstream phase is newly blocked by this decision** — Phases 13, 14, 16 and 17
re-anchored to detection time, clock time, or price-path events under D13, and that
re-anchoring stands.

**Evidence is not retracted by the method being closed**, per the same rule that preserved
v3's scale-separation result under D9. The carried findings are listed in
`results/d9_lineage_closeout/REPORT.md` §3 and remain citable.

**Numbering note.** Recorded as D21 because D20 was appended by Phase 10d on 2026-08-26.
`CLAUDE.md`'s decision pointer list was stale at D14 and is corrected in the same commit as
this decision; the register in this file, not that list, is the authority for the next free
number.
