# Phase 10c — Clock-Time Sub-Burst Decomposition

**Status: Stage 1 approved by Cooper, 2026-08-26. Phase closes here — Stages 2 and 3 were never
run. The program proceeds to Phase 10d.**

**For the first time across six method families (five in Phase 10, this the sixth), a burst
decomposition produced sub-bursts that are not a reporting artifact.** Phase 10 v4's method found a
median sub-burst duration of 349 ns — one marketable order sweeping the book, not market structure.
Stage 1's clock-time-normalized, multi-kernel mechanism produced 170,722 sub-bursts across 56 dev
events with a 0% `no_threshold` rate and durations that scale with the session, not with tick noise.

---

## 1. What the phase was for

Phase 10's diagnosis (carried into Phase 10b, which then spent itself proving no *global* burst
timescale is measurable — `docs/Universe-Decisions.md` D11–D13) was that a single-scale method
cannot distinguish "bursty" from "Poisson with a time-varying rate" without constraining how fast
the rate may vary. Phase 10c's answer: normalize every inter-trade interval by a **clock-time local
median**, computed independently at three window widths (a multi-kernel grid, not one free
parameter), and let sub-bursts fall out per kernel rather than committing to a single timescale.

The v4 failure this phase exists to fix: a narrow, isolated interval spike at ~1/1700 of the local
median, produced by one order sweeping several resting quotes microseconds apart — the void gate
locked onto it every time, at every event, regardless of kernel choice, because nothing in v4's
mechanism could tell a multi-fill sweep from a real pause in arrivals.

---

## 2. Satisfiability gating and the amendment sequence

Every stage ran a four-check satisfiability audit before any code executed (Agent_Prompt_Standard
§A1.9). Stage 0's first audit passed 1/4; Stage 0b's first audit failed check 2. Six formal
amendments followed, each resolving exactly one escalated question:

| Amendment | Resolved |
|---|---|
| A1 | Class E / Class M decision taxonomy; Stage 0 interval-landscape tasks |
| A2 (pre-Stage-1) | Stage 0b insertion, D16 void-gate floor = 0.25 |
| "Amendment 1" (`amendment_a2_7_a2_8_resolution.md`) | A2.7/A2.8: both candidate fast/slow-mode split rules **increased** the silent-selection rate they existed to reduce (21.4% rule agreement). Revision 2 demoted A2.7 from a gate to a descriptive diagnostic and introduced `A2.7.D17_burst_envelope_boundary` — argmax void across ALL troughs, no ceiling, no threshold — as the Stage 1 threshold rule (Cooper's choice "1") |
| Amendment 2 | Trading day redefined as `(prior XNYS session close, this session's close]`; only 1 event (ACET) moves; D5/D6 confirmed unchanged |
| Amendment 3 | The detection artifact carries 3 momentum-threshold variants (1.25/1.30/1.35) per event — `load_detection()` had been silently selecting 1.25 via `drop_duplicates`. Decision: carry all three in parallel, never collapse to one |
| Amendment 4 | Two closing-print rules proposed (condition-code-keyed auction assignment; evening/premarket/rth segments); population tier set to dev |
| Amendment 5 | Massive vendor condition-code dictionary supplied and stored; code set {8,15} vs {8,9,15} found immaterial on this cohort (0/877 near-close prints carry 9 without 8 or 15) |
| Amendment 6 | Auction rule settled: **{8,15}, scope all trades**. Dictionary relocated out of a gitignored tree (`data/metadata/` → `docs/massive_trade_conditions.json`) |

Full text of every amendment: `prompts/phase_10c_amendment_*.md` (recovered verbatim from the
session transcript where not committed at the time — see §8).

---

## 3. Stage 1 — the mechanism, run for the first time

**Frozen configuration at Stage 1 (`config/phase_10c.json`, hash `998c2461`):**

| Class E (economic, locked pre-Stage-0) | Value |
|---|---|
| `D7_threshold` band | 10 ms – 10 s |
| `D8_min_median_duration_s` | 30 |
| `D9_slope_max` | 0.5 |
| `D16_min_median_void` | 0.25 |

| Class M (measured, set at Stage 0 approval) | Value |
|---|---|
| `D4_median_precision_factor` (F) | 1.5 |
| `D5_first_kernel_min` | 8 |
| `D6_stage2_kernels_min` | {2, 8, 32} |
| Threshold variants | {1.25, 1.30, 1.35}, all three carried |

**Population:** dev sample, 56 events (`dev_v4_primary` 50 + `dev_v4_sidecar` 6), seed 42,
stratified by `t0_print_count` decile, drawn before Stage 1 existed — no circularity between
sample selection and the measured quantity.

**Design decision, stated rather than left implicit:** sub-burst extraction (tie collapse → D1
aggregation → centered clock-time local median → histogram → envelope-boundary threshold → runs)
is a function of `(event, kernel)` only — nothing in the mechanism reads the threshold variant. The
variant only determines which segment an event is stratified into and where its detection anchor
sits. Stage 1 therefore computed 56 × 3 = 168 (event, kernel) cells once each, then cross-joined
each onto all 3 variants' own segment/anchor context to form the 9 reported cells — verified
identical to independent per-variant recomputation (`s1_t4_cross_kernel.py`, max spread across
variants = 0.0 for both threshold location and void).

**Waterfall (population-named at every stage, `s1_t1_waterfall_per_cell.json`):** 3,774,862 raw
prints → 3,671,288 tie-collapsed → 2,629,076 after D1 (100 µs floor) → 2,629,020 intervals →
**170,722 sub-bursts** across the 168 kernel-cells. `no_threshold` share: **0%** in every cell —
every event with sufficient context found a computable trough.

---

## 4. Findings, T2–T5 (descriptive; no gate anywhere in this stage)

- **T2 — anchor-independent quantities agree closely across variants, with one instructive
  exception.** Sub-burst spacing is *identical* across all 3 variants at every kernel (confirmed by
  direct check, not assumed — spacing never depends on the anchor). Threshold location, duration
  and void mostly agree; RTH threshold location at kernel=8min shows medians 0.058s / 2.659s /
  0.028s across 1.25/1.30/1.35 — traced to a single event, CODX 2020-03-11, sitting alone in a
  ~90×-wide sorted gap of a distribution spanning 8 orders of magnitude, whose segment membership
  is variant-dependent. A median-of-a-heavy-tailed-sample instability, not a recomputation
  difference (`s1_t2e_agreement.json`).
- **T3 — the first sub-burst since detection is rarely the largest.** First-is-also-largest-by-
  move-share in 7.3% / 10.8% / 9.7% of cells at 1.25/1.30/1.35 (`s1_t3c_summary.json`).
- **T4 — cross-kernel behavior is heterogeneous, and one pattern was unanticipated.** The per-event
  log-log slope of threshold location vs. kernel width has median **−1.359** (p25 −3.142, p75
  0.429, n=43) — neither flat (a real structural interval) nor the ~1:1 scaling the prompt named as
  the free-parameter signature. A third, negative pattern, reported as measured; the read is
  Cooper's. Best-separated kernel: 32min for 21 events, 2min for 16, 8min for 12 — differs by event
  and mildly by segment, not significantly correlated with event size or detection price decile
  (`s1_t4_summary.json`).
- **T5 — sub-burst count vs. print count is positive as expected** (no gate; Amendment 1 retired
  this as a criterion). A2.7 silent-selection rate 57.9%/60.5%/61.2% by kernel — **not comparable**
  to Stage 0b's 30% figure, a different statistic measured before the envelope boundary existed.

---

## 5. Defects found this stage, reported not silently fixed

- **T0 — a counting bug, not a population difference.** Amendment 6 reported "n_rth 36→37 with
  ACET added." Both numbers traced to `int(r_.ticker.nunique())`, which collapses two dev-sample
  events sharing a ticker (OCUL appears twice, on different dates) into one count. True pre-override
  population is 37 (matching the independently-computed dev-manifest table exactly); true
  post-override is **38**, not 37 — the earlier "37" was a coincidence, the counting bug (−1) and
  ACET's real addition (+1) cancelling numerically. Same error class as the VEEE/CODX offsetting
  swap already on record from Amendment 4. Floor and rung values were computed on the correct
  row-set throughout and are unaffected (`s1_t0_denominator.json`).
- **T1 — a population-scope defect in prior (Amendment 4–6) work, not in Stage 1's own code.** BMR
  — one of the four "genuine after-hours anchors" Amendment 4's discriminant test used to justify
  the {8,15} code set — is `cohort_group='activity_extension'`, not a dev-sample event.
  `a6_conditions.py`/`a7_census.py` read `t1_cohort_manifest.parquet` (114 rows across 4 cohort
  groups) without filtering to the 56-event dev sample, so every "114-event cohort" figure in
  Amendments 4–6 silently spanned 58 events beyond Stage 1's population. Does not change the
  {8,15} decision (BMR's own codes carry neither code regardless of scope). Logged to
  `docs/Open-Items-Register.md`, not retroactively edited in the tagged/committed amendment
  artifacts (`s1_t1_verify.json`).

---

## 6. Verification Block (S5)

- **Chart Contract:** **139/139 charts Kaleido-verified** (27 static T2–T6-sample + 56 T6d combined
  animations + 56 T7 tape-review charts). Two gaps were found and closed before this total was
  reached — T6d and T7 had originally bypassed the PNG-verification path entirely.
- **Executable assertions** (`s1_t1_verify.json`, all PASS): every event resolves to at most one
  segment per variant; ACET's auction override is confirmed firing (all 6 affected cells land
  `rth`); no variant was deduplicated at load; Class M unchanged open to close.
- **Escalation table, all 19 rows reviewed** (`s1_verification_block.json`): **13 not fired**
  (confirmed by construction — D13 never gates, D3 stays centered, no combining rule, no
  evaluative language, no spine numeric enters a computation); **4 unevaluable** (rows 13–16,
  `[Cooper]` thresholds never set — raw figures reported, none invented); **1 reserved** for Cooper
  (row 0, the tape review); **1 violation found — in prior amendment work**, flagged not silently
  corrected (§5, BMR); **0 violations in anything Stage 1 itself produced.**

---

## 7. T6 — Cooper's layout choice, run to completion

Both candidate T6c layouts (per-kernel-separate; combined 3-panel comparative) were built on 4
representative events for Cooper's choice. **Cooper chose combined comparative.** T6d then ran on
the full 56-event dev sample: 56/56, 0 skips, all Kaleido-verified
(`results/phase_10c/charts/s1_06_animation_full/`, gitignored/regenerable — the manifest is the
committed record).

## Row 0

56 five-panel tape-review charts were produced (`results/phase_10c/charts/s1_07_tape_review/`,
reference cell kernel=8min/threshold=1.25) and were not evaluated by this pipeline, per the
standing rule that row 0 overrides every numeric row and is Cooper's alone. **Cooper approved Stage
1.**

---

## 8. Known gaps in the record

- Amendments 2–6 were pasted as full documents and acted on directly but never saved as their own
  committed prompt files at the time — recovered verbatim from the session transcript as part of
  this close-out (`prompts/phase_10c_amendment_{2..6}.md`); no content was reconstructed or
  paraphrased.
- The eligible-pool gap (15,299 eligible vs. D14's 20,951 canonical in-scope events, 5,652
  unexplained) remains open and is required before any full-population run.
- `det_ns_*` float64 precision (256 ns quantization) remains unrepaired at source; Phase 10c is
  unaffected (nearest-match recovers all tested anchors at 0 ns residual).
- The auction rule {8,15} remains empirical plus semantic, not independently validated against a
  ground truth of actual closing auctions.
- Whether the 51.57% "volume-but-not-last-sale" share of the trade stream (Amendment 5 D) reflects
  order fragmentation was raised and explicitly declined as a mid-phase scope expansion — recorded
  with both sides of the argument in `docs/Open-Items-Register.md`.

---

## 9. Standing decisions recorded

- **`docs/Universe-Decisions.md` D3, Amendment (Phase 10c):** the session-boundary and
  auction-print assignment rule this phase established is now the standing convention for any
  future intraday segment work — see that entry for the full rule.
- **`A2.7.D17_burst_envelope_boundary`**: the burst-envelope threshold rule (argmax void across all
  troughs, no ceiling) — local decision registry, `config/phase_10c.json` → `a2_rules`.
- **Closing-print/auction rule:** codes {8, 15}, scope all trades — `config/phase_10c.json` →
  `closing_print_rule`.

---

## 10. What happens next

Cooper: *"we have learned what we need... going to do a 10d."* Stage 1 is approved; Stages 2
(multi-kernel scale-coupling gate) and 3 (full-population run) are **not run** and are not
scheduled under this phase number. The program proceeds to **Phase 10d**, scope set by Cooper's
next prompt.
