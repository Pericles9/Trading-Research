# Phase 12 — Halts & LULD. Stage A complete, dev tier. Gate fires. Stage B not authorised.

**Governing prompt:** `prompts/phase_12.md`. **Branch:** `phase/12`, cut from `master`
(2026-09-13). **Scope executed:** T0a–T3 (dev tier, 56 events). **Stage B does not run** — the
Approval Gate requires Cooper to clear Escalation rows 10/11 in writing before Stage B begins, and
both rows fire at this tier (see §6).

**Bottom line, stated once at the top:** on the 56-event dev sample, the three halt-identification
routes do not corroborate well enough to establish that halts are identifiable from this archive.
Route 1 (tape gaps) finds a real, modest signature near the 300-second LULD pause length — the
distribution is not smooth throughout, contrary to the null hypothesis T1b poses — but produces
1,991 candidate gaps across only 42 events, far more than plausible halts. Route 2 (condition
codes) identifies nothing by construction: no code dictionary exists on disk. Route 3 (band
arithmetic) finds 13 of 55 events touching a band edge. Only 9 events show agreement between
routes 1 and 3. **This is a reportable outcome per the prompt's own design (T3c), not a failure**,
and the dev-tier scale of the corroborated-count threshold specifically is flagged as likely
uninformative about the full archive (see §6's caveat) — the share-based threshold is not.

---

## 0. Cooper's authorization enabling this phase to start

T0a (2026-09-13) found `config/phase_12.json` carrying 7 unfilled `[Cooper]` slots, which
Escalation row 2 hard-stops at T0c by design. Cooper authorized (a) live research to verify the
LULD band parameters against Nasdaq's actual policy and (b) filling the remaining numeric
thresholds with the file's own proposals, both explicitly flagged flexible. This is recorded as
**D34** (`docs/Universe-Decisions.md`) — a one-time, explicitly directed exception to Escalation
row 4 / D14's standing rule, not a change to that rule for any other value or future phase. The
research found and fixed a real error (the Tier-2 $3.00 doubling boundary was backwards) and a
population-relevant gap (one dev event predates Amendment 18). Full account:
`docs/data/luld_plan_reference.md`.

---

## 1. T0a — state, observed

Branch clean at every checkpoint. `conditions` present in all 56 dev trades.parquet files (0
missing); null on 37.4% of trade rows. `indicators` (quotes-side only) null on 11.16% of quote
rows — 88.84% populated, independently reproducing Phase 11 A2-11's frozen 88.85% finding. Frozen
inputs (`results/phase_8/artifacts/a102_detection_anchors.parquet`, Phase 11's `t1c_indicators`/
`t1c_conditions_codes` census) all present. Full detail: `results/iso_share_hold_length/artifacts/t0_audit.json`
covered the same DuckDB-schema check for a different phase; this phase's own live check is in
commit history (T0a, 2026-09-13).

## 2. T0d — satisfiability audit, all 17 rows

6 pass, 11 deferred (Stage A/B hadn't run yet — expected, not a gap), 0 fail. One finding: the
escalation table's own row 16 write-path list is narrower than `config.write_allowlist` — the same
class of drift `research/phase_10e/t0d_audit.py`'s own row 20 caught in that phase. Not fixed here
(rewording an escalation row is Cooper's call, per that exact precedent). One disclosed exception:
`docs/data/luld_plan_reference.md` and the D34 decision-index writes sit outside both the row's
list and the allowlist, made under Cooper's direct authorization and this repo's standing
decision-index rule. Full detail: `results/phase_12/artifacts/t0d_satisfiability_audit.json`.

## 3. T1 — route 1, tape gaps (before any threshold)

56/56 dev events, 3,062,919 RTH inter-print gaps enumerated (none pre-filtered — `is_candidate`
flags duration ≥ 60s on top of the full distribution, an interpretation choice stated in the
script, since T1a's and T1b's literal text otherwise read in tension). 1,991 candidates (0.065% of
all gaps). **Finding:** candidate-gap counts (uniform 20-second bins) decline smoothly from
200–300s (56, 44, 31, 21, 19) then reverse upward at 300–320s (31) before resuming decline — a
modest but real local excess at the 300-second pause length, not a smooth power-law tail
throughout. Chart 01: `charts/01_gap_duration.html`.

## 4. T2a — route 2, condition-code census (uninterpreted)

1,991 candidates vs. a matched random sample of 1,991 non-candidate gaps. Quote indicator codes
**3** and **7** appear only in candidate-gap windows (54 and 63 occurrences respectively) and never
in the matched sample; code 8 appears at a similarly low rate in both. No meaning is inferred from
any code (Escalation row 5); `dictionary_path = NONE` (D34, confirming Phase 11 A2-11's own
finding), so route 2 produces a census only and identifies nothing. Full table:
`artifacts/t2_code_census.json`.

**Follow-up, 2026-09-14 (D35) — dictionary research authorized and attempted, load-bearing codes
still unresolved.** Cooper authorized live research (same method as D34's LULD verification) to
find a real code dictionary. Trade condition codes 37 (Odd Lot Trade) and 2 (Average Price Trade)
were resolved with high confidence, and 14 (Intermarket Sweep) cross-referenced against D26's
existing confirmation — **none bear on halt identification.** The two codes that actually matter,
quote indicators 3 and 7, **could not be resolved** after roughly a dozen search/fetch attempts
(full account: `docs/data/condition_indicator_code_reference.md`) — the vendor's specific numeric
mapping sits behind an authenticated API endpoint this session has no key for, and every primary
regulatory-specification PDF tried failed to extract as readable text, the same failure mode D34
hit for a different set of documents. **`dictionary_path` stays `NONE`; route 2 still identifies
nothing; the Stage A gate result below is unchanged by this research.**

## 5. T2b — route 3, band arithmetic

Reference price (5-minute rolling VWAP, 1% hysteresis) and band edges computed from
`event_minute_bars_v2` (tick-derived; no spine column read, D4/Escalation-row-6-safe), previous
close taken from the last T-1 RTH minute bar's `last_price`, not any spine column. Applies the
corrected $3.00 doubling boundary and the pre/post-Amendment-18 branch (D34). 55/56 events
processed (1 has no T-1 RTH bar, excluded and reported). **7/55 events (12.7%) cross a percentage
bracket mid-session; 13/55 (23.6%) touch a band edge at minute-bar resolution.** Exactly 1
pre-Amendment-18 event (AACG), as D34 predicted. Every parameter cites its config key (row 4). Tier
is assumed 2 for all events, not individually confirmed against an index membership list
(unavailable in this checkout) — disclosed limitation. Full table: `artifacts/t2_band_arithmetic.json`.

## 6. T2c — agreement matrix, and the T3 gate

| | route 1 only | route 3 only | both routes | route 2 |
|---|---|---|---|---|
| n events | 33 | 4 | 9 | 0 (by construction) |

At the finer gap level: 1,991 route-1 candidates, 1,797 (90.3%) with no route-3 corroboration in
the same event. Agreement is approximated at the event level (route 1 is gap-level, route 3 is
minute-bar-level — a strict time-overlap join is coarser given the grain mismatch, disclosed rather
than presented as exact). Chart 02: `charts/02_route_agreement.html`.

**T3 — THE STAGE A GATE.**

| row | condition | threshold | observed | fires |
|---|---|---|---|---|
| 10 | corroborated-halt count < floor | 50 | 9 | **yes** |
| 11 | single-route-only share > ceiling | 0.6 | 0.903 | **yes** |

**Methodological caveat, stated because it changes how this should be read, not to soften it.**
Row 10's floor (50) was almost certainly calibrated for a full-tier population (~20,951 events),
not this 56-event dev sample — 50/56 would require corroboration on ~89% of the *entire* dev
cohort, an implausible bar for any real archive. **This dev-tier row-10 firing is expected at this
sample size and is not read as a conclusive archive-wide finding.** Row 11 is a *share*, not a
count, and does not have the same small-n floor problem — its firing (0.903 vs. 0.6) is read as the
more informative of the two at this tier.

**T3c — the feasibility finding, per the prompt's own instruction that this is a complete and
reportable outcome, not a failure.** What would close the gap, named concretely: (a) a
condition/indicator code dictionary — even a partial one mapping just the two candidate-exclusive
codes (3, 7) — would let route 2 actually identify rather than only census; (b) full-tier promotion
would test whether row 10's count floor is reachable at scale, which 56 events structurally cannot
answer regardless of the true halt rate; (c) tick-level (not minute-bar) band arithmetic would
remove the coarsest source of the route-1/route-3 grain mismatch this pass approximated around.

**No recommendation is made on any of these three** (Evidence Standard). Full gate detail:
`artifacts/t3_gate.json`.

---

## 7. Escalation check, all 17 rows

| # | Condition | Observed | Verdict |
|---|---|---|---|
| 1 | Working tree dirty at T0a | clean at every checkpoint | pass |
| 2 | LULD/`[Cooper]` slot unfilled at T0c | fired once (7 slots), cleared by D34 | resolved, not open |
| 3 | T0d fails any check | 0 fail | pass |
| 4 | LULD parameter without a config-key citation | every T2b parameter cites one (script's `config_keys_used`) | pass |
| 5 | Meaning inferred for a code without a dictionary | none — T2a reports frequencies only | pass |
| 6 | Spine numeric on a computation path | none — previous close from tick data, D4-safe | pass |
| 7 | T4b state variable not knowable at decision time | not reached | not evaluated |
| 8 | Halt labelled from `clean_window` `0001000` | not reached | not evaluated |
| 9 | Cell below `min_cell_n` unhatched | not reached | not evaluated |
| 10 | Corroborated count < 50 | 9 | **fires — Stage A gate, see §6** |
| 11 | Single-route-only share > 0.6 | 0.903 | **fires — Stage A gate, see §6** |
| 12 | Reopen-gap median without full distribution | not reached | not evaluated |
| 13 | Quantity in one unit alone | not reached | not evaluated |
| 14 | Fitted hazard/survival model produced | not reached | not evaluated |
| 15 | Position size proposed / result characterised | none | pass |
| 16 | Write outside allowed paths | drift + 1 disclosed exception, see §2 | pass, with finding |
| 17 | Runtime exceeds ceiling | well under, all tasks combined | pass |

---

## 8. Output files

| File | Status |
|---|---|
| `prompts/phase_12.md`, `config/phase_12.json` | committed |
| `docs/data/luld_plan_reference.md` | committed (D34) |
| `research/phase_12/{t0d_audit,t1_gap_census,t2a_condition_census,t2b_band_arithmetic,t2c_agreement_matrix,t3_gate}.py` | committed |
| `research/phase_12/chart_{01,02}_*.py` | committed |
| `results/phase_12/artifacts/{t0d_satisfiability_audit,t1_gap_census,t2_code_census,t2b_band_arithmetic,t2_agreement_matrix,t3_gate}.json` | committed |
| `results/phase_12/artifacts/*.parquet` | gitignored (regenerable, matches existing `results/phase_*/artifacts/*.parquet` rule) |
| `results/phase_12/charts/{01,02}_*.html` | committed |
| `results/phase_12/REPORT.md` | this file |
| `results/reports/phase_12_report.md` | copy |
| `results/phase_12/digest.json` | machine-readable return path |
| `docs/Universe-Decisions.md`, `CLAUDE.md` | D34 added |

---

## 9. What Cooper is being asked to review

**Stage A is complete at dev tier; Stage B is unauthorised.** Per the Approval Gate: "Stage B does
not begin until Cooper has reviewed charts 01–02 and cleared rows 10 and 11 in writing." Three
things follow:

1. Both gate rows fire, but row 10's floor is likely miscalibrated for this tier (§6) — full-tier
   promotion is the direct way to find out whether the count floor is reachable at scale.
2. Row 11 (share-based, not floor-sensitive) still shows routes that mostly disagree — whether
   that changes at full tier, with a real dictionary, or with tick-level band arithmetic is open.
3. A cheap, concrete option exists before any full-tier spend: a partial code dictionary for
   codes 3 and 7 (§4) would let route 2 contribute for the first time.

**No recommendation is made on any of these three, and Stage B does not run without Cooper's
explicit written clearance of rows 10/11, per the Approval Gate.**
