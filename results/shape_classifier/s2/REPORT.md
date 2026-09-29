# Shape classifier S2 — can the six types be predicted, at the crossing and as the path unfolds?

**Brief:** `prompts/shape_classifier_s2.md` · **Config:** `config/shape_classifier_s2.json` (hash `f0206c2d8137`) · **Branch:** `explore/shape-classifier-s2` · **Code:** `research/shape_classifier_s2/` · **Built at:** `c96f572` · 2026-09-28

Exploratory modelling build, not a phase. The test is ticker-blocked and time-ordered (folds test 2022, 2023, 2024); everything else is exploratory. This report describes the artifacts and charts; it does not interpret them.

**Status: HARD STOP -- escalation row 3 fired; state committed, nothing fixed or tuned. This report is the record of that state (T0-T7 ran; T8 generated as the record).**

## Escalation table

| row | criterion | tier | observed | fires |
|---|---|---|---|---|
| 1 | any input uses data after its decision time | HARD STOP | 0 input rows after their decision time (t0_audit.parquet) | no |
| 2 | negative control outside 0.45–0.55 (R5 read: mean of 3 folds × 10 shuffles) | HARD STOP | 0 of 354 type × model × time cells outside; means span 0.469–0.528 | no |
| 3 | positive control below 0.95 (R4 gate: rule inputs, M2 and M3) | HARD STOP | 7 of 720 per-fold cells below 0.95; minimum 0.9385 | yes |
| 4 | one input > half of a type's permutation importance (M3) | LOG | 0 fold × time × type cells; inputs: none | no |
| 5 | a fold's primary test set < 20 events of a type | LOG | 14 fold × time × type cells (listed in §4) | LOG |
| 6 | sklearn / HistGradientBoostingClassifier unavailable offline | HARD STOP | sklearn 1.8.0; HistGradientBoostingClassifier imported | no |

## 1. Timing audit (T0) and the A12 finding

### 1.1 How `flag_cross_session_extreme` is built

- Code: `research/phase_9/t1_ca_detector.py:main, research/phase_9/common.py::session_closes / closes_wide`.
- Per session pair: r = log(p_later_close / p_earlier_close); flag = |r| >= ca_flag_log_threshold; threshold |log r| ≥ 0.5878 (ratio outside 0.5556–1.80).
- Close: ARG_MAX(last_price, minute_index) over event_minute_bars_v2 rows of that session offset: the last trade of the extended day (any segment).
- Pair carried by b1, b2 and S1: tm1_t0 -- (close of T-1, close of T0); research/attention_excursion_b1/t1_t2_summary.py joins session_pair == 'tm1_t0'.
- **It uses the event day's close.** The T0 close is the event day's last trade, so the flag reads the whole event day, after tau.
- Checked on disk (15,519 S2 events; 15,519 carry the tm1_t0 pair): the T0 close equals the event day's last print at or before 20:00 for 15,512 (7 differ); that last print is after τ for 15,517. Flagged: 887.
- Flag rate by S1 type (N = 100): runaway 0.541 (204/377); burst 0.242 (143/590); slow climb 0.402 (247/615); exhausted 0.011 (29/2,754); fade 0.015 (28/1,878); chop 0.025 (236/9,299).

### 1.2 Every earlier use of the flag

33 tracked code files read the flag (list checked against `git grep`): 32 facet, 1 builder. Files that use it as an **input** (a fitted model, a selection rule or a threshold): **0**. the rough pre-S2 run (Claude, on S1's per-event tables, brief 'What came before') used the flag as a model input; it is not in the repository.

| file | use | how |
|---|---|---|
| `research/attention_excursion_b1/build_report.py` | facet | report sentence (flagged count) |
| `research/attention_excursion_b1/charts.py` | facet | chart annotation |
| `research/attention_excursion_b1/t1_t2_summary.py` | facet | tm1_t0 flag joined to t2_tau; flagged count reported |
| `research/attention_excursion_b1/t4_excursion.py` | facet | flag carried on the excursion rows |
| `research/attention_excursion_b1/t5_attention.py` | facet | flag carried on the attention rows |
| `research/attention_excursion_b2/build_report.py` | facet | facet listing in the report |
| `research/attention_excursion_b2/t0_population.py` | facet | flag carried; counts reported |
| `research/attention_excursion_b2/t1_excursion.py` | facet | flag carried |
| `research/attention_excursion_b2/t2_attention.py` | facet | flag carried |
| `research/attention_excursion_b2/t4_step_zero.py` | facet | one facet of the step-zero panels |
| `research/phase_10/v2_r13_detection.py` | facet | joined tm1_t0 flag; counts of flagged events reported |
| `research/phase_10e/t1_candidate_entries.py` | facet | tm1_t0 flag carried on every candidate entry; count reported |
| `research/phase_10e/t2_excursion.py` | facet | flag carried |
| `research/phase_10e/t5_costed_markouts.py` | facet | every statistic with and without the tm1_t0-flagged set (A12) |
| `research/phase_10e/t6_adverse_tail.py` | facet | with and without the tm1_t0-flagged set (A12) |
| `research/phase_11/t4b_ordering_audit.py` | facet | file-ordering audit lists the flag artifact |
| `research/phase_11/t7_cost_vs_capture.py` | facet | flag joined as one of three carried flags |
| `research/phase_9/chart_01.py` | facet | chart annotation |
| `research/phase_9/chart_02.py` | facet | chart split flagged / unflagged |
| `research/phase_9/t1_ca_detector.py` | builder | builds the flag for pairs tm1_t0, t0_t1, t0_t2, t0_t3 |
| `research/phase_9/t2_sensitivity.py` | facet | markouts reported flagged-only / unflagged / flagged-excluded per pair |
| `research/phase_9/t3_retracement.py` | facet | retracement reported with the flag (either side) excluded and only |
| `research/phase_9/t5_clustered.py` | facet | clustered interval with the t0_t1-flagged set removed, beside the full set |
| `research/relative_momentum/t0c2_move_at_reslice.py` | facet | every headline with and without the flagged set (A12) |
| `research/relative_momentum/t0c_phase11_reslice.py` | facet | every slice with and without the flagged set (A12) |
| `research/relative_momentum_v0/t4_diagnostic.py` | facet | split on the flag, flagged rows never dropped |
| `research/relative_momentum_v1/t4_diagnostic.py` | facet | split on the flag, flagged rows never dropped |
| `research/scale_field/event_panels.py` | facet | flag listed on event panels (any pair) |
| `research/scope_universe_scan/basis_test.py` | facet | carried per A12 (docstring) |
| `research/scope_universe_scan/basis_test_stage2.py` | facet | basis test reported with and without the tm1_t0-flagged set |
| `research/shape_atlas_s1/build_report.py` | facet | descriptor listing in the report |
| `research/shape_atlas_s1/t1_paths.py` | facet | flag carried on s1_events |
| `research/shape_atlas_s1/t5_atlas.py` | facet | tape descriptor shown per type (hindsight allowed in S1) |

Non-code records naming the flag (reports, briefs, configs, docs): 35 files — `CLAUDE.md`, `config/attention_excursion_b2.json`, `config/phase_10.json`, `config/phase_10_v2.json`, `config/phase_10e.json`, `config/phase_11.json`, `config/phase_9.json`, `config/relative_momentum_v0.json`, `config/scale_field_panels.json`, `config/shape_atlas_s1.json`, `config/shape_classifier_s2.json`, `docs/Open-Items-Register.md`, `docs/Research-Library-Map.md`, `docs/Universe-Decisions.md`, `prompts/attention_excursion.md`, `prompts/attention_excursion_b1.md`, `prompts/phase_11.md`, `prompts/phase_9.md`, `prompts/shape_classifier_s2.md`, `results/attention_excursion/b1/REPORT.md`, `results/attention_excursion/b2/REPORT.md`, `results/phase_10/REPORT_v2_v3_superseded.md`, `results/phase_10e/REPORT.md`, `results/phase_9/REPORT.md`, `results/relative_momentum/r0/REPORT.md`, `results/relative_momentum/v0/REPORT.md`, `results/relative_momentum/v1/REPORT.md`, `results/reports/attention_excursion_b1_report.md`, `results/reports/attention_excursion_b2_report.md`, `results/reports/phase_10_v2_report.md`, `results/reports/phase_10e_report.md`, `results/reports/phase_9_report.md`, `results/reports/relative_momentum_r0_report.md`, `results/reports/relative_momentum_v0_report.md`, `results/reports/relative_momentum_v1_report.md`.

### 1.3 Latest data timestamp of every input

| group | input | what it reads | rows | after decision | max (latest − decision), s |
|---|---|---|---|---|---|
| A | `accel` | accel_k0..4, validity, a2_ignition (rung windows end at tau) | 15,519 | 0 | 0.000000000 |
| A | `cross_section` | live_n, flow_share (live names crossed at or before tau; windows end at tau) | 15,519 | 0 | 0.000000000 |
| A | `dilution` | dilution_tau (R3) | 15,346 | 0 | -0.047366656 |
| A | `filings` | filing_24h, last_form (accepted < tau) | 15,346 | 0 | -0.047366656 |
| A | `first_print` | tau_is_first_print | 15,519 | 0 | 0.000000000 |
| A | `pre` | pre-tau trade rate and dollar flow | 15,519 | 0 | 0.000000000 |
| A | `reverse_split` | reverse split in 365 days (last split timestamp) | 6,064 | 0 | -28800.017080576 |
| A | `runup` | run-up descriptors, gap_share (S1: prints in [segment start, tau]) | 15,519 | 0 | 0.000000000 |
| A | `shares` | shares outstanding (R3) | 12,429 | 0 | -11.363152384 |
| A | `short_interest` | short interest share (R2: assumed publication 20:00 ET) | 14,803 | 0 | -28800.004704000 |
| A | `timing` | timing (time of day, segment, auction minute) | 15,519 | 0 | 0.000000000 |
| A | `turnover` | turnover (shares 04:00 -> tau; tau-anchored count) | 15,519 | 0 | 0.000000000 |
| B | `B` | Group B (prints tau < ts <= d) | 130,139 | 0 | 0.000000000 |
| C | `group_c_query_grid` | path so far on the master grid (x(t) reads prints <= tau + t) | 130,139 | 0 | 0.000000000 |
| tape | `tcs` | tcs_state (R1) | 145,658 | 0 | 0.000000000 |

Row 1: **0** violations. Per decision time: `artifacts/t0_audit.parquet`.

### 1.4 Other timing findings, measured before the build

- **Stored τ is float64-rounded.** every stored tau_ns in b1 t2_tau, b2 and S1 is a multiple of 256 ns: float64-rounded upstream (error <= 128 ns either way): all 15,519 stored values are multiples of 256 ns; the crossing print equals the stored value for 1,436, is later for 7,146 and earlier for 6,937 (max |difference| 128 ns). 38 events have prints after the crossing print and at or before the stored τ (38 prints). Handling: decision time at tau = tau_d = max(stored tau, the crossing print's own timestamp); b2 / S1 inputs built on the stored tau are then <= tau_d, the crossing print is <= tau_d, and entries are after it. Live names crossing after τ_d: 0.
- **`tau_close_sensitive` (Cooper R1).** Not settled at τ for 3,585 events (measured on b1's stored values before the build). The minute-bar crossing is recomputed from ticks with b1's `first_crossing`: 15,170 of 15,236 within 128 ns of b1's stored value (max 7282306884162 ns; exact-only 0, b1-only 0); the fully settled flag equals b1's for 15,513 of 15,519. State at each decision time: τ false 10,798, not_settled 3,591, true 1,130; τ+1m false 13,079, not_settled 1,310, true 1,130; τ+2m false 13,079, true 2,440; τ+5m false 13,079, true 2,440; τ+10m false 13,079, true 2,440; τ+20m false 13,079, true 2,440; vol 0.25× false 12,476, not_settled 312, true 2,103; vol 0.5× false 11,941, not_settled 156, true 1,991; vol 1× false 10,935, not_settled 77, true 1,722; vol 2× false 9,467, not_settled 39, true 1,325.
- **Defect found in T2's minute-bar crossing, not fixed (found at the HARD STOP).** For 66 of 15,236 events T2's crossing is more than 128 ns from b1's stored value — all earlier (by 0.0000001 s to 7282 s, median 0.260 s). Cause (66 of 66): T2 called first_crossing on the 04:00-20:00 slice; the slice's first print has no predecessor so is never a spike, while b1's full-array call judges it against its pre-04:00 predecessor and skips it; b1's full-array call reproduces b1 within 128 ns for 66 of 66. Scope: Cooper R1 tcs_state input only; the crossing T2 used is a real print, used only once it has happened (no timing violation). found at the row 3 HARD STOP; the fix (call first_crossing on the full arrays) waits for instruction. Evidence: `artifacts/t2b_mb_diagnosis.parquet` (`research/shape_classifier_s2/t2b_mb_diagnosis.py`).
- **Short interest (Cooper R2).** F1's `si_asof_ns` is the settlement date, not publication. Rebuilt from the raw vendor files: latest settlement whose assumed publication (10 XNYS sessions later) is before the event date — 14,803 events (F1 settlement-dated: 15,107; same value as F1: 162); median settlement 24 days before the event. FINRA's actual lag is not verifiable offline [verify].
- **Fundamentals re-anchored at τ (Cooper R3).** Shares outstanding available for 12,429 events (F1 at t0: 11,835); equal to F1's value for 14,921, different for 598; split correction applied to 1,197. Dilution flag TRUE for 1,194 (F1 at t0: 1,196; 4 differ). Filings cross-check against b2 (accepted < τ): filing_24h agrees for 100.00%, last form for 99.99% of 15,347 events.
- **τ is confirmed at its successor.** tau is the first print >= 1.30 x prior close that is not a spike; the spike test reads the print after it, so tau is confirmed at its successor. Seconds from the τ print to its successor: median 0.002092, 90th pct 5.119, 99th 201.6, max 10861; zero (same timestamp) for 0.7% (n 15,517).
- **Live set.** live_n / flow_share count other D1 names that crossed at or before tau; D1 membership is the vendor's day-level selection (momentum_pct, RTH high), so the live set is conditional on that selection boundary like the whole population (D4, A13).
- CLAUDE.md index check (`tools/verify_claude_md_indices.py`): exit 0.

## 2. Controls (T5) — `charts/t5/controls.html`

**Negative (Cooper R5).** Labels permuted within each fold's training window, 10 shuffles per fold, Group C typical paths rebuilt from the permuted labels, M1–M4 at the real run's settings. Row 2 reads the mean of the 30 per-fold primary AUCs per type × model × decision time: 0 of 354 cells outside 0.45–0.55; means span 0.469–0.528. Single-shuffle per-fold AUCs outside the band: 2,866 of 10,620 (the brief's construction read cell by cell).

| model | class weight | mean AUC, min | mean AUC, max | single shuffle, min | single shuffle, max |
|---|---|---|---|---|---|
| M1 | none | 0.491 | 0.508 | 0.347 | 0.664 |
| M2 | balanced | 0.479 | 0.517 | 0.288 | 0.680 |
| M2 | none | 0.470 | 0.514 | 0.277 | 0.660 |
| M3 | balanced | 0.473 | 0.528 | 0.297 | 0.780 |
| M3 | none | 0.469 | 0.527 | 0.260 | 0.694 |
| M4 | balanced | 0.487 | 0.516 | 0.288 | 0.688 |
| M4 | none | 0.486 | 0.518 | 0.278 | 0.694 |

**Positive (Cooper R4).** Rule inputs (post100_rise_pct, post100_fall_pct, post100_u_peak) added to M2 and M3 at every decision time, real run's settings: 7 of 720 per-fold cells below 0.95; minimum 0.9385.

**Row 3 fires.** The cells below 0.95, with the setting each used (the real run's choice, R4):

| fold | decision time | model | class weight | type | AUC | n | n_type | setting |
|---|---|---|---|---|---|---|---|---|
| 1 | τ+10m | M2 | balanced | chop | 0.9493 | 997 | 548 | `{'C': 0.1}` |
| 1 | τ+20m | M2 | balanced | chop | 0.9489 | 997 | 548 | `{'C': 0.1}` |
| 1 | vol 0.5× | M2 | balanced | chop | 0.9478 | 911 | 508 | `{'C': 0.1}` |
| 1 | vol 1× | M2 | balanced | chop | 0.9411 | 819 | 459 | `{'C': 0.1}` |
| 2 | vol 1× | M2 | balanced | chop | 0.9452 | 637 | 386 | `{'C': 0.1}` |
| 1 | vol 2× | M2 | balanced | chop | 0.9391 | 703 | 409 | `{'C': 0.1}` |
| 2 | vol 2× | M2 | balanced | chop | 0.9385 | 547 | 326 | `{'C': 0.1}` |

Rule-inputs run, minimum per-fold primary AUC by model, class weight and type:

| model | class weight | runaway | burst | slow climb | exhausted | fade | chop |
|---|---|---|---|---|---|---|---|
| M2 | balanced | 0.9745 | 0.9641 | 0.9701 | 0.9741 | 0.9656 | 0.9385 |
| M2 | none | 0.9803 | 0.9721 | 0.9694 | 0.9806 | 0.9772 | 0.9591 |
| M3 | balanced | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
| M3 | none | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 |

terminal_log (the brief's construction), reported ungated, per type:

| model | class weight | runaway | burst | slow climb | exhausted | fade | chop |
|---|---|---|---|---|---|---|---|
| M2 | balanced | 0.940 (min 0.861) | 0.791 (min 0.713) | 0.884 (min 0.855) | 0.839 (min 0.749) | 0.884 (min 0.859) | 0.787 (min 0.764) |
| M2 | none | 0.957 (min 0.897) | 0.826 (min 0.768) | 0.913 (min 0.886) | 0.842 (min 0.758) | 0.894 (min 0.869) | 0.809 (min 0.781) |
| M3 | balanced | 0.957 (min 0.884) | 0.814 (min 0.768) | 0.901 (min 0.881) | 0.872 (min 0.752) | 0.901 (min 0.853) | 0.818 (min 0.772) |
| M3 | none | 0.961 (min 0.910) | 0.839 (min 0.789) | 0.908 (min 0.887) | 0.877 (min 0.761) | 0.906 (min 0.861) | 0.823 (min 0.774) |

(terminal_log cells: mean and minimum of the per-fold primary AUCs over the three folds and ten decision times.)

**Baseline (M1 vs M0 at τ), primary read, mean of three folds:**

| model | runaway | burst | slow climb | exhausted | fade | chop | log loss | skill vs M0 |
|---|---|---|---|---|---|---|---|---|
| M0 | 0.500 | 0.500 | 0.500 | 0.500 | 0.500 | 0.500 | 1.2212 | 0.0000 |
| M1 | 0.586 | 0.673 | 0.572 | 0.592 | 0.546 | 0.523 | 1.2059 | 0.0124 |

## 3. Population, decision times and folds (T2, T3)

15,519 S1 events with τ; excluded from every fold: 49 dev_v3 and 4 sidecar events; unlabelled (S1 N = 100 untyped): 6.

| decision time | reached | not_reached | undefined | elapsed min (10/50/90th pct) |
|---|---|---|---|---|
| τ | 15,519 | 0 | 0 | – |
| τ+1m | 15,519 | 0 | 0 | – |
| τ+2m | 15,519 | 0 | 0 | – |
| τ+5m | 15,519 | 0 | 0 | – |
| τ+10m | 15,519 | 0 | 0 | – |
| τ+20m | 15,519 | 0 | 0 | – |
| vol 0.25× | 14,891 | 443 | 185 | 0.1 / 2.8 / 36.9 |
| vol 0.5× | 14,088 | 1,246 | 185 | 0.1 / 5.4 / 68.9 |
| vol 1× | 12,734 | 2,600 | 185 | 0.3 / 8.7 / 118.2 |
| vol 2× | 10,831 | 4,503 | 185 | 0.4 / 12.8 / 160.7 |

| fold | role | events | tickers | runaway | burst | slow climb | exhausted | fade | chop |
|---|---|---|---|---|---|---|---|---|---|
| 1 | train | 5,289 | 1,501 | 157 | 232 | 202 | 1,047 | 696 | 2,955 |
| 1 | sub | 3,376 | 1,166 | 85 | 165 | 121 | 739 | 396 | 1,870 |
| 1 | val | 688 | 335 | 25 | 24 | 26 | 116 | 115 | 382 |
| 1 | test | 2,232 | 884 | 53 | 79 | 98 | 409 | 298 | 1,295 |
| 1 | primary | 997 | 396 | 30 | 39 | 40 | 204 | 136 | 548 |
| 2 | train | 7,521 | 1,897 | 210 | 311 | 300 | 1,456 | 994 | 4,250 |
| 2 | sub | 5,289 | 1,501 | 157 | 232 | 202 | 1,047 | 696 | 2,955 |
| 2 | val | 997 | 396 | 30 | 39 | 40 | 204 | 136 | 548 |
| 2 | test | 2,952 | 1,055 | 61 | 105 | 111 | 522 | 338 | 1,815 |
| 2 | primary | 804 | 289 | 22 | 32 | 36 | 126 | 97 | 491 |
| 3 | train | 10,473 | 2,186 | 271 | 416 | 411 | 1,978 | 1,332 | 6,065 |
| 3 | sub | 7,521 | 1,897 | 210 | 311 | 300 | 1,456 | 994 | 4,250 |
| 3 | val | 804 | 289 | 22 | 32 | 36 | 126 | 97 | 491 |
| 3 | test | 4,987 | 1,397 | 104 | 172 | 202 | 767 | 540 | 3,202 |
| 3 | primary | 1,241 | 367 | 15 | 42 | 52 | 203 | 153 | 776 |

Counts per fold × role × type × decision time × state: `artifacts/t3_counts.parquet`.

**Row 5 (LOG).** 14 fold × decision time × type cells have fewer than 20 events of the type among the primary events that reached the decision time; they are shown (hollow markers) and not read; the cells follow.

| fold | type | decision times | n range |
|---|---|---|---|
| 2 | runaway | vol 0.25×, vol 0.5×, vol 1×, vol 2× | 16–19 |
| 3 | runaway | τ, τ+1m, τ+2m, τ+5m, τ+10m, τ+20m, vol 0.25×, vol 0.5×, vol 1×, vol 2× | 11–15 |

## 4. Results per type — `charts/t4/auc_by_time.html`, `lift_by_time.html`, `calibration.html`, `confusion.html`, `charts/t6/forward_returns.html`, `charts/t7/importance.html`

AUC cells: mean of the readable folds' primary-read AUCs, with their range in brackets; `[k/3 read]` marks cells where row 5 leaves only k of the three folds readable (the others are on the chart, hollow). Lift uses the same readable folds. Per-fold values with 95% ticker-bootstrap intervals are in `artifacts/t4_auc.parquet` and on the chart.

### 4.1 runaway

Primary test events of the type that reached each decision time (three folds summed): τ 67, τ+1m 67, τ+2m 67, τ+5m 67, τ+10m 67, τ+20m 67, vol 0.25× 63, vol 0.5× 61, vol 1× 59, vol 2× 53.

| model | τ | τ+1m | τ+2m | τ+5m | τ+10m | τ+20m | vol 0.25× | vol 0.5× | vol 1× | vol 2× |
|---|---|---|---|---|---|---|---|---|---|---|
| M0 (none) | 0.500 (0.50–0.50) [2/3 read] | 0.500 (0.50–0.50) [2/3 read] | 0.500 (0.50–0.50) [2/3 read] | 0.500 (0.50–0.50) [2/3 read] | 0.500 (0.50–0.50) [2/3 read] | 0.500 (0.50–0.50) [2/3 read] | 0.500 (0.50–0.50) [1/3 read] | 0.500 (0.50–0.50) [1/3 read] | 0.500 (0.50–0.50) [1/3 read] | 0.500 (0.50–0.50) [1/3 read] |
| M1 (none) | 0.630 (0.59–0.67) [2/3 read] | – | – | – | – | – | – | – | – | – |
| M2 (none) | 0.614 (0.57–0.66) [2/3 read] | 0.619 (0.57–0.67) [2/3 read] | 0.625 (0.60–0.65) [2/3 read] | 0.653 (0.62–0.68) [2/3 read] | 0.667 (0.66–0.68) [2/3 read] | 0.680 (0.67–0.69) [2/3 read] | 0.705 (0.70–0.70) [1/3 read] | 0.740 (0.74–0.74) [1/3 read] | 0.767 (0.77–0.77) [1/3 read] | 0.738 (0.74–0.74) [1/3 read] |
| M3 (none) | 0.611 (0.56–0.66) [2/3 read] | 0.631 (0.58–0.69) [2/3 read] | 0.643 (0.63–0.65) [2/3 read] | 0.714 (0.67–0.76) [2/3 read] | 0.634 (0.60–0.67) [2/3 read] | 0.646 (0.64–0.65) [2/3 read] | 0.743 (0.74–0.74) [1/3 read] | 0.735 (0.73–0.73) [1/3 read] | 0.726 (0.73–0.73) [1/3 read] | 0.700 (0.70–0.70) [1/3 read] |
| M4 (none) | – | 0.496 (0.46–0.53) [2/3 read] | 0.491 (0.46–0.52) [2/3 read] | 0.589 (0.56–0.62) [2/3 read] | 0.648 (0.56–0.74) [2/3 read] | 0.632 (0.55–0.71) [2/3 read] | 0.553 (0.55–0.55) [1/3 read] | 0.671 (0.67–0.67) [1/3 read] | 0.656 (0.66–0.66) [1/3 read] | 0.585 (0.59–0.59) [1/3 read] |
| M2 (balanced) | 0.610 (0.55–0.67) [2/3 read] | 0.625 (0.56–0.69) [2/3 read] | 0.629 (0.59–0.67) [2/3 read] | 0.666 (0.62–0.71) [2/3 read] | 0.651 (0.61–0.69) [2/3 read] | 0.640 (0.63–0.65) [2/3 read] | 0.712 (0.71–0.71) [1/3 read] | 0.731 (0.73–0.73) [1/3 read] | 0.760 (0.76–0.76) [1/3 read] | 0.720 (0.72–0.72) [1/3 read] |
| M3 (balanced) | 0.578 (0.52–0.64) [2/3 read] | 0.639 (0.61–0.67) [2/3 read] | 0.649 (0.65–0.65) [2/3 read] | 0.702 (0.64–0.76) [2/3 read] | 0.680 (0.67–0.69) [2/3 read] | 0.681 (0.68–0.68) [2/3 read] | 0.724 (0.72–0.72) [1/3 read] | 0.698 (0.70–0.70) [1/3 read] | 0.737 (0.74–0.74) [1/3 read] | 0.707 (0.71–0.71) [1/3 read] |
| M4 (balanced) | – | 0.503 (0.45–0.56) [2/3 read] | 0.483 (0.45–0.51) [2/3 read] | 0.587 (0.56–0.61) [2/3 read] | 0.634 (0.52–0.74) [2/3 read] | 0.598 (0.50–0.69) [2/3 read] | 0.520 (0.52–0.52) [1/3 read] | 0.618 (0.62–0.62) [1/3 read] | 0.634 (0.63–0.63) [1/3 read] | 0.553 (0.55–0.55) [1/3 read] |

Top-10% lift (mean of the readable folds, primary):

| model | τ | τ+1m | τ+2m | τ+5m | τ+10m | τ+20m | vol 0.25× | vol 0.5× | vol 1× | vol 2× |
|---|---|---|---|---|---|---|---|---|---|---|
| M2 (none) | 1.90 | 1.67 | 1.73 | 1.73 | 2.12 | 2.29 | 2.06 | 3.41 | 3.44 | 4.57 |
| M3 (none) | 2.29 | 2.79 | 2.29 | 2.40 | 1.45 | 2.23 | 2.74 | 4.10 | 2.76 | 3.81 |
| M4 (none) | – | 1.06 | 1.22 | 1.46 | 2.02 | 2.10 | 1.00 | 2.16 | 2.43 | 1.87 |

Median net forward return, bp (net 70.98 bp; entry = next print after the decision time, the zero-latency upper bound; three folds pooled). Quantile functions, the cents unit and the 1 s / 5 s entries are on `forward_returns.html`:

| set | τ | τ+1m | τ+2m | τ+5m | τ+10m | τ+20m | vol 0.25× | vol 0.5× | vol 1× | vol 2× |
|---|---|---|---|---|---|---|---|---|---|---|
| M3 top decile, +30 min | -141 (n 306) | -148 (n 305) | -102 (n 305) | -130 (n 305) | -162 (n 305) | -221 (n 305) | -185 (n 292) | -176 (n 278) | -271 (n 247) | -148 (n 213) |
| all primary, +30 min | -243 (n 3,034) | -250 (n 3,030) | -214 (n 3,029) | -179 (n 3,030) | -164 (n 3,023) | -122 (n 3,014) | -190 (n 2,904) | -194 (n 2,749) | -181 (n 2,468) | -151 (n 2,104) |
| M3 top decile, to 20:00 | -375 (n 306) | -288 (n 306) | -340 (n 306) | -324 (n 306) | -309 (n 306) | -395 (n 306) | -415 (n 293) | -258 (n 278) | -496 (n 249) | -711 (n 213) |
| all primary, to 20:00 | -431 (n 3,042) | -411 (n 3,042) | -379 (n 3,041) | -340 (n 3,041) | -299 (n 3,039) | -241 (n 3,037) | -344 (n 2,911) | -352 (n 2,755) | -383 (n 2,476) | -400 (n 2,113) |

M3 permutation importance, top three inputs by share (mean of three folds):

| decision time | 1st | 2nd | 3rd |
|---|---|---|---|
| τ | `log10_runup_shares` 0.14 | `log10_turnover` 0.10 | `runup_max_drawdown_s` 0.09 |
| τ+1m | `log10_runup_shares` 0.11 | `log10_turnover` 0.11 | `runup_max_drawdown_s` 0.06 |
| τ+2m | `log10_turnover` 0.08 | `tod_h` 0.06 | `dist_slow_climb` 0.06 |
| τ+5m | `asinh_z_ret` 0.09 | `dd_log` 0.07 | `runup_max_drawdown_s` 0.06 |
| τ+10m | `accel_post` 0.10 | `asinh_z_ret` 0.06 | `ret_log` 0.06 |
| τ+20m | `ret_log` 0.08 | `asinh_z_ret` 0.08 | `u_high` 0.07 |
| vol 0.25× | `dd_log` 0.12 | `dist_slow_climb` 0.06 | `log10_runup_shares` 0.05 |
| vol 0.5× | `dd_log` 0.13 | `ret_log` 0.12 | `log10_runup_shares` 0.12 |
| vol 1× | `dist_exhausted` 0.08 | `log10_runup_shares` 0.08 | `asinh_z_dd` 0.07 |
| vol 2× | `ret_log` 0.09 | `dist_exhausted` 0.07 | `dd_log` 0.07 |

### 4.2 burst

Primary test events of the type that reached each decision time (three folds summed): τ 113, τ+1m 113, τ+2m 113, τ+5m 113, τ+10m 113, τ+20m 113, vol 0.25× 113, vol 0.5× 112, vol 1× 112, vol 2× 109.

| model | τ | τ+1m | τ+2m | τ+5m | τ+10m | τ+20m | vol 0.25× | vol 0.5× | vol 1× | vol 2× |
|---|---|---|---|---|---|---|---|---|---|---|
| M0 (none) | 0.500 (0.50–0.50) | 0.500 (0.50–0.50) | 0.500 (0.50–0.50) | 0.500 (0.50–0.50) | 0.500 (0.50–0.50) | 0.500 (0.50–0.50) | 0.500 (0.50–0.50) | 0.500 (0.50–0.50) | 0.500 (0.50–0.50) | 0.500 (0.50–0.50) |
| M1 (none) | 0.673 (0.65–0.69) | – | – | – | – | – | – | – | – | – |
| M2 (none) | 0.653 (0.63–0.68) | 0.667 (0.64–0.68) | 0.683 (0.63–0.72) | 0.735 (0.67–0.80) | 0.763 (0.69–0.84) | 0.810 (0.72–0.90) | 0.706 (0.67–0.72) | 0.699 (0.66–0.74) | 0.719 (0.65–0.76) | 0.733 (0.67–0.78) |
| M3 (none) | 0.671 (0.65–0.70) | 0.680 (0.64–0.73) | 0.703 (0.61–0.78) | 0.743 (0.64–0.80) | 0.786 (0.71–0.85) | 0.818 (0.71–0.90) | 0.734 (0.69–0.77) | 0.716 (0.66–0.75) | 0.727 (0.62–0.79) | 0.763 (0.71–0.81) |
| M4 (none) | – | 0.579 (0.51–0.65) | 0.587 (0.57–0.60) | 0.651 (0.61–0.68) | 0.711 (0.65–0.77) | 0.775 (0.69–0.85) | 0.638 (0.59–0.69) | 0.634 (0.58–0.70) | 0.622 (0.56–0.69) | 0.664 (0.63–0.68) |
| M2 (balanced) | 0.654 (0.61–0.70) | 0.670 (0.65–0.70) | 0.686 (0.64–0.74) | 0.736 (0.67–0.81) | 0.764 (0.69–0.85) | 0.805 (0.72–0.89) | 0.704 (0.67–0.74) | 0.702 (0.66–0.73) | 0.723 (0.67–0.77) | 0.731 (0.67–0.79) |
| M3 (balanced) | 0.649 (0.63–0.69) | 0.657 (0.60–0.73) | 0.672 (0.60–0.73) | 0.714 (0.63–0.81) | 0.769 (0.69–0.86) | 0.809 (0.73–0.87) | 0.709 (0.66–0.76) | 0.698 (0.64–0.74) | 0.728 (0.65–0.77) | 0.771 (0.73–0.81) |
| M4 (balanced) | – | 0.586 (0.53–0.65) | 0.581 (0.57–0.59) | 0.644 (0.60–0.67) | 0.698 (0.64–0.75) | 0.767 (0.68–0.84) | 0.640 (0.59–0.70) | 0.634 (0.58–0.68) | 0.628 (0.56–0.69) | 0.664 (0.64–0.68) |

Top-10% lift (mean of the readable folds, primary):

| model | τ | τ+1m | τ+2m | τ+5m | τ+10m | τ+20m | vol 0.25× | vol 0.5× | vol 1× | vol 2× |
|---|---|---|---|---|---|---|---|---|---|---|
| M2 (none) | 2.65 | 2.87 | 3.11 | 3.93 | 4.16 | 5.08 | 2.79 | 2.36 | 3.14 | 3.00 |
| M3 (none) | 2.87 | 3.24 | 2.82 | 3.83 | 4.51 | 5.08 | 3.47 | 2.51 | 2.82 | 3.79 |
| M4 (none) | – | 1.81 | 2.18 | 2.10 | 3.37 | 4.02 | 1.74 | 2.04 | 1.87 | 2.54 |

Median net forward return, bp (net 70.98 bp; entry = next print after the decision time, the zero-latency upper bound; three folds pooled). Quantile functions, the cents unit and the 1 s / 5 s entries are on `forward_returns.html`:

| set | τ | τ+1m | τ+2m | τ+5m | τ+10m | τ+20m | vol 0.25× | vol 0.5× | vol 1× | vol 2× |
|---|---|---|---|---|---|---|---|---|---|---|
| M3 top decile, +30 min | 126 (n 305) | 94 (n 306) | -231 (n 306) | -272 (n 306) | -348 (n 303) | -419 (n 301) | -32 (n 292) | -95 (n 277) | -81 (n 249) | -175 (n 213) |
| all primary, +30 min | -243 (n 3,034) | -250 (n 3,030) | -214 (n 3,029) | -179 (n 3,030) | -164 (n 3,023) | -122 (n 3,014) | -190 (n 2,904) | -194 (n 2,749) | -181 (n 2,468) | -151 (n 2,104) |
| M3 top decile, to 20:00 | -225 (n 306) | -665 (n 306) | -1284 (n 306) | -1371 (n 306) | -1624 (n 306) | -1822 (n 304) | -497 (n 293) | -996 (n 278) | -631 (n 249) | -1151 (n 213) |
| all primary, to 20:00 | -431 (n 3,042) | -411 (n 3,042) | -379 (n 3,041) | -340 (n 3,041) | -299 (n 3,039) | -241 (n 3,037) | -344 (n 2,911) | -352 (n 2,755) | -383 (n 2,476) | -400 (n 2,113) |

M3 permutation importance, top three inputs by share (mean of three folds):

| decision time | 1st | 2nd | 3rd |
|---|---|---|---|
| τ | `tod_h` 0.19 | `accel_k0` 0.11 | `log10_pre_trades_per_min` 0.11 |
| τ+1m | `accel_k0` 0.13 | `log10_post_dollars_per_min` 0.11 | `ret_log` 0.07 |
| τ+2m | `tod_h` 0.11 | `ret_log` 0.10 | `log10_post_dollars_per_min` 0.07 |
| τ+5m | `tod_h` 0.17 | `ret_log` 0.12 | `asinh_z_ret` 0.09 |
| τ+10m | `asinh_z_ret` 0.17 | `ret_log` 0.13 | `tod_h` 0.12 |
| τ+20m | `ret_log` 0.18 | `asinh_z_ret` 0.16 | `tod_h` 0.13 |
| vol 0.25× | `tod_h` 0.10 | `asinh_z_ret` 0.09 | `last_form` 0.07 |
| vol 0.5× | `tod_h` 0.10 | `dist_burst` 0.10 | `log10_pre_trades_per_min` 0.07 |
| vol 1× | `tod_h` 0.23 | `accel_k0` 0.05 | `ret_log` 0.05 |
| vol 2× | `ret_log` 0.12 | `tod_h` 0.09 | `dist_burst` 0.07 |

### 4.3 slow climb

Primary test events of the type that reached each decision time (three folds summed): τ 128, τ+1m 128, τ+2m 128, τ+5m 128, τ+10m 128, τ+20m 128, vol 0.25× 125, vol 0.5× 122, vol 1× 121, vol 2× 114.

| model | τ | τ+1m | τ+2m | τ+5m | τ+10m | τ+20m | vol 0.25× | vol 0.5× | vol 1× | vol 2× |
|---|---|---|---|---|---|---|---|---|---|---|
| M0 (none) | 0.500 (0.50–0.50) | 0.500 (0.50–0.50) | 0.500 (0.50–0.50) | 0.500 (0.50–0.50) | 0.500 (0.50–0.50) | 0.500 (0.50–0.50) | 0.500 (0.50–0.50) | 0.500 (0.50–0.50) | 0.500 (0.50–0.50) | 0.500 (0.50–0.50) |
| M1 (none) | 0.572 (0.56–0.59) | – | – | – | – | – | – | – | – | – |
| M2 (none) | 0.545 (0.48–0.61) | 0.595 (0.57–0.65) | 0.598 (0.55–0.66) | 0.593 (0.55–0.65) | 0.631 (0.58–0.70) | 0.695 (0.63–0.81) | 0.626 (0.58–0.69) | 0.620 (0.58–0.70) | 0.664 (0.63–0.72) | 0.697 (0.67–0.75) |
| M3 (none) | 0.536 (0.49–0.58) | 0.601 (0.56–0.62) | 0.601 (0.59–0.62) | 0.604 (0.57–0.64) | 0.643 (0.63–0.66) | 0.705 (0.67–0.77) | 0.622 (0.56–0.70) | 0.615 (0.58–0.65) | 0.658 (0.63–0.68) | 0.706 (0.65–0.79) |
| M4 (none) | – | 0.580 (0.55–0.61) | 0.565 (0.52–0.64) | 0.606 (0.58–0.62) | 0.616 (0.58–0.65) | 0.675 (0.64–0.74) | 0.589 (0.55–0.62) | 0.618 (0.60–0.65) | 0.683 (0.64–0.73) | 0.699 (0.67–0.72) |
| M2 (balanced) | 0.518 (0.48–0.58) | 0.574 (0.53–0.63) | 0.567 (0.52–0.64) | 0.567 (0.53–0.63) | 0.606 (0.57–0.68) | 0.665 (0.60–0.77) | 0.600 (0.54–0.67) | 0.593 (0.54–0.67) | 0.635 (0.60–0.68) | 0.676 (0.66–0.70) |
| M3 (balanced) | 0.556 (0.52–0.58) | 0.596 (0.57–0.63) | 0.588 (0.56–0.62) | 0.585 (0.54–0.61) | 0.640 (0.64–0.64) | 0.701 (0.66–0.76) | 0.615 (0.57–0.70) | 0.610 (0.56–0.66) | 0.625 (0.60–0.65) | 0.697 (0.66–0.75) |
| M4 (balanced) | – | 0.576 (0.53–0.60) | 0.556 (0.50–0.62) | 0.591 (0.58–0.61) | 0.596 (0.55–0.62) | 0.655 (0.62–0.69) | 0.584 (0.55–0.60) | 0.601 (0.58–0.61) | 0.675 (0.64–0.72) | 0.680 (0.67–0.70) |

Top-10% lift (mean of the readable folds, primary):

| model | τ | τ+1m | τ+2m | τ+5m | τ+10m | τ+20m | vol 0.25× | vol 0.5× | vol 1× | vol 2× |
|---|---|---|---|---|---|---|---|---|---|---|
| M2 (none) | 1.60 | 1.36 | 1.51 | 1.67 | 2.46 | 2.97 | 1.58 | 1.94 | 2.27 | 2.86 |
| M3 (none) | 1.51 | 1.67 | 1.66 | 1.83 | 1.96 | 2.44 | 1.68 | 2.08 | 2.43 | 2.84 |
| M4 (none) | – | 1.52 | 1.32 | 1.59 | 2.14 | 2.28 | 1.16 | 1.87 | 2.19 | 2.20 |

Median net forward return, bp (net 70.98 bp; entry = next print after the decision time, the zero-latency upper bound; three folds pooled). Quantile functions, the cents unit and the 1 s / 5 s entries are on `forward_returns.html`:

| set | τ | τ+1m | τ+2m | τ+5m | τ+10m | τ+20m | vol 0.25× | vol 0.5× | vol 1× | vol 2× |
|---|---|---|---|---|---|---|---|---|---|---|
| M3 top decile, +30 min | -188 (n 306) | -363 (n 306) | -225 (n 306) | -194 (n 306) | -243 (n 306) | -306 (n 306) | -190 (n 293) | -247 (n 278) | -335 (n 249) | -241 (n 213) |
| all primary, +30 min | -243 (n 3,034) | -250 (n 3,030) | -214 (n 3,029) | -179 (n 3,030) | -164 (n 3,023) | -122 (n 3,014) | -190 (n 2,904) | -194 (n 2,749) | -181 (n 2,468) | -151 (n 2,104) |
| M3 top decile, to 20:00 | -311 (n 306) | -594 (n 306) | -745 (n 306) | -812 (n 306) | -762 (n 306) | -852 (n 306) | -470 (n 293) | -547 (n 278) | -621 (n 249) | -809 (n 213) |
| all primary, to 20:00 | -431 (n 3,042) | -411 (n 3,042) | -379 (n 3,041) | -340 (n 3,041) | -299 (n 3,039) | -241 (n 3,037) | -344 (n 2,911) | -352 (n 2,755) | -383 (n 2,476) | -400 (n 2,113) |

M3 permutation importance, top three inputs by share (mean of three folds):

| decision time | 1st | 2nd | 3rd |
|---|---|---|---|
| τ | `tod_h` 0.11 | `accel_k3` 0.08 | `runup_height_s` 0.07 |
| τ+1m | `ret_log` 0.08 | `asinh_z_dd` 0.06 | `asinh_z_ret` 0.06 |
| τ+2m | `accel_k4` 0.07 | `short_interest_share` 0.07 | `accel_k3` 0.06 |
| τ+5m | `ret_log` 0.12 | `lr_trade_rate` 0.05 | `log10_post_trades_per_min` 0.04 |
| τ+10m | `ret_log` 0.26 | `asinh_z_ret` 0.08 | `tod_h` 0.06 |
| τ+20m | `asinh_z_ret` 0.21 | `ret_log` 0.16 | `dd_log` 0.09 |
| vol 0.25× | `asinh_z_ret` 0.15 | `ret_log` 0.06 | `short_interest_share` 0.06 |
| vol 0.5× | `ret_log` 0.28 | `asinh_z_ret` 0.06 | `asinh_z_dd` 0.04 |
| vol 1× | `ret_log` 0.37 | `asinh_z_ret` 0.10 | `u_high` 0.05 |
| vol 2× | `asinh_z_ret` 0.20 | `dd_log` 0.14 | `ret_log` 0.07 |

### 4.4 exhausted

Primary test events of the type that reached each decision time (three folds summed): τ 533, τ+1m 533, τ+2m 533, τ+5m 533, τ+10m 533, τ+20m 533, vol 0.25× 489, vol 0.5× 447, vol 1× 373, vol 2× 282.

| model | τ | τ+1m | τ+2m | τ+5m | τ+10m | τ+20m | vol 0.25× | vol 0.5× | vol 1× | vol 2× |
|---|---|---|---|---|---|---|---|---|---|---|
| M0 (none) | 0.500 (0.50–0.50) | 0.500 (0.50–0.50) | 0.500 (0.50–0.50) | 0.500 (0.50–0.50) | 0.500 (0.50–0.50) | 0.500 (0.50–0.50) | 0.500 (0.50–0.50) | 0.500 (0.50–0.50) | 0.500 (0.50–0.50) | 0.500 (0.50–0.50) |
| M1 (none) | 0.592 (0.57–0.63) | – | – | – | – | – | – | – | – | – |
| M2 (none) | 0.607 (0.59–0.63) | 0.699 (0.67–0.72) | 0.732 (0.72–0.74) | 0.770 (0.77–0.77) | 0.805 (0.80–0.81) | 0.830 (0.82–0.83) | 0.776 (0.77–0.79) | 0.805 (0.80–0.81) | 0.813 (0.81–0.82) | 0.816 (0.80–0.84) |
| M3 (none) | 0.604 (0.59–0.62) | 0.722 (0.70–0.75) | 0.748 (0.73–0.77) | 0.795 (0.79–0.80) | 0.836 (0.83–0.84) | 0.863 (0.86–0.87) | 0.789 (0.78–0.80) | 0.845 (0.84–0.86) | 0.856 (0.85–0.86) | 0.859 (0.84–0.87) |
| M4 (none) | – | 0.663 (0.63–0.68) | 0.697 (0.69–0.70) | 0.732 (0.73–0.73) | 0.770 (0.76–0.77) | 0.788 (0.78–0.79) | 0.743 (0.73–0.76) | 0.773 (0.76–0.79) | 0.786 (0.78–0.80) | 0.786 (0.78–0.80) |
| M2 (balanced) | 0.612 (0.58–0.65) | 0.696 (0.66–0.73) | 0.728 (0.71–0.75) | 0.764 (0.76–0.77) | 0.802 (0.79–0.81) | 0.828 (0.81–0.84) | 0.773 (0.76–0.78) | 0.802 (0.79–0.81) | 0.809 (0.81–0.81) | 0.808 (0.79–0.82) |
| M3 (balanced) | 0.595 (0.57–0.62) | 0.705 (0.67–0.74) | 0.746 (0.73–0.77) | 0.785 (0.78–0.79) | 0.827 (0.82–0.84) | 0.857 (0.85–0.86) | 0.784 (0.78–0.79) | 0.840 (0.83–0.85) | 0.854 (0.85–0.86) | 0.860 (0.85–0.88) |
| M4 (balanced) | – | 0.662 (0.63–0.68) | 0.698 (0.69–0.70) | 0.730 (0.73–0.73) | 0.765 (0.76–0.77) | 0.786 (0.78–0.79) | 0.743 (0.73–0.76) | 0.773 (0.76–0.79) | 0.781 (0.78–0.79) | 0.780 (0.77–0.79) |

Top-10% lift (mean of the readable folds, primary):

| model | τ | τ+1m | τ+2m | τ+5m | τ+10m | τ+20m | vol 0.25× | vol 0.5× | vol 1× | vol 2× |
|---|---|---|---|---|---|---|---|---|---|---|
| M2 (none) | 1.79 | 2.42 | 2.60 | 2.96 | 3.12 | 3.51 | 3.12 | 3.54 | 3.57 | 3.66 |
| M3 (none) | 1.73 | 2.65 | 2.97 | 3.32 | 3.45 | 3.78 | 3.22 | 3.86 | 4.32 | 4.50 |
| M4 (none) | – | 2.13 | 2.17 | 2.44 | 2.55 | 2.61 | 2.72 | 2.94 | 3.10 | 3.30 |

Median net forward return, bp (net 70.98 bp; entry = next print after the decision time, the zero-latency upper bound; three folds pooled). Quantile functions, the cents unit and the 1 s / 5 s entries are on `forward_returns.html`:

| set | τ | τ+1m | τ+2m | τ+5m | τ+10m | τ+20m | vol 0.25× | vol 0.5× | vol 1× | vol 2× |
|---|---|---|---|---|---|---|---|---|---|---|
| M3 top decile, +30 min | -323 (n 302) | -294 (n 300) | -207 (n 299) | -132 (n 299) | -91 (n 300) | -71 (n 296) | -73 (n 291) | -96 (n 278) | -112 (n 244) | -71 (n 208) |
| all primary, +30 min | -243 (n 3,034) | -250 (n 3,030) | -214 (n 3,029) | -179 (n 3,030) | -164 (n 3,023) | -122 (n 3,014) | -190 (n 2,904) | -194 (n 2,749) | -181 (n 2,468) | -151 (n 2,104) |
| M3 top decile, to 20:00 | -602 (n 306) | -386 (n 306) | -297 (n 305) | -223 (n 305) | -72 (n 304) | -71 (n 304) | -68 (n 292) | -123 (n 278) | -72 (n 249) | -20 (n 213) |
| all primary, to 20:00 | -431 (n 3,042) | -411 (n 3,042) | -379 (n 3,041) | -340 (n 3,041) | -299 (n 3,039) | -241 (n 3,037) | -344 (n 2,911) | -352 (n 2,755) | -383 (n 2,476) | -400 (n 2,113) |

M3 permutation importance, top three inputs by share (mean of three folds):

| decision time | 1st | 2nd | 3rd |
|---|---|---|---|
| τ | `tod_h` 0.38 | `log10_pre_trades_per_min` 0.15 | `last_form` 0.05 |
| τ+1m | `tod_h` 0.24 | `asinh_z_ret` 0.15 | `u_high` 0.10 |
| τ+2m | `tod_h` 0.24 | `u_high` 0.24 | `asinh_z_ret` 0.13 |
| τ+5m | `u_high` 0.29 | `asinh_z_ret` 0.22 | `tod_h` 0.21 |
| τ+10m | `u_high` 0.31 | `tod_h` 0.23 | `asinh_z_ret` 0.16 |
| τ+20m | `u_high` 0.44 | `tod_h` 0.18 | `ret_log` 0.13 |
| vol 0.25× | `tod_h` 0.30 | `u_high` 0.18 | `ret_log` 0.14 |
| vol 0.5× | `tod_h` 0.29 | `u_high` 0.26 | `ret_log` 0.14 |
| vol 1× | `u_high` 0.34 | `tod_h` 0.27 | `asinh_z_ret` 0.11 |
| vol 2× | `u_high` 0.31 | `tod_h` 0.27 | `high_log` 0.09 |

### 4.5 fade

Primary test events of the type that reached each decision time (three folds summed): τ 386, τ+1m 386, τ+2m 386, τ+5m 386, τ+10m 386, τ+20m 386, vol 0.25× 379, vol 0.5× 364, vol 1× 333, vol 2× 276.

| model | τ | τ+1m | τ+2m | τ+5m | τ+10m | τ+20m | vol 0.25× | vol 0.5× | vol 1× | vol 2× |
|---|---|---|---|---|---|---|---|---|---|---|
| M0 (none) | 0.500 (0.50–0.50) | 0.500 (0.50–0.50) | 0.500 (0.50–0.50) | 0.500 (0.50–0.50) | 0.500 (0.50–0.50) | 0.500 (0.50–0.50) | 0.500 (0.50–0.50) | 0.500 (0.50–0.50) | 0.500 (0.50–0.50) | 0.500 (0.50–0.50) |
| M1 (none) | 0.546 (0.54–0.55) | – | – | – | – | – | – | – | – | – |
| M2 (none) | 0.552 (0.55–0.56) | 0.613 (0.60–0.62) | 0.614 (0.61–0.63) | 0.628 (0.61–0.65) | 0.651 (0.63–0.69) | 0.661 (0.64–0.68) | 0.614 (0.60–0.63) | 0.621 (0.61–0.63) | 0.646 (0.62–0.66) | 0.636 (0.62–0.65) |
| M3 (none) | 0.562 (0.54–0.60) | 0.625 (0.61–0.65) | 0.640 (0.62–0.66) | 0.653 (0.63–0.67) | 0.669 (0.64–0.70) | 0.679 (0.66–0.70) | 0.642 (0.62–0.66) | 0.643 (0.62–0.66) | 0.679 (0.67–0.69) | 0.667 (0.65–0.70) |
| M4 (none) | – | 0.592 (0.56–0.61) | 0.591 (0.56–0.61) | 0.593 (0.56–0.63) | 0.602 (0.56–0.65) | 0.631 (0.62–0.64) | 0.588 (0.56–0.62) | 0.612 (0.58–0.65) | 0.616 (0.56–0.70) | 0.613 (0.60–0.63) |
| M2 (balanced) | 0.540 (0.53–0.55) | 0.586 (0.58–0.60) | 0.586 (0.58–0.59) | 0.601 (0.59–0.62) | 0.623 (0.60–0.66) | 0.645 (0.62–0.66) | 0.588 (0.59–0.59) | 0.584 (0.57–0.59) | 0.618 (0.59–0.64) | 0.615 (0.60–0.64) |
| M3 (balanced) | 0.554 (0.53–0.59) | 0.613 (0.59–0.64) | 0.618 (0.61–0.63) | 0.636 (0.62–0.65) | 0.661 (0.65–0.68) | 0.672 (0.65–0.70) | 0.625 (0.61–0.64) | 0.627 (0.59–0.66) | 0.666 (0.65–0.67) | 0.655 (0.64–0.68) |
| M4 (balanced) | – | 0.575 (0.57–0.59) | 0.559 (0.54–0.57) | 0.560 (0.53–0.60) | 0.581 (0.53–0.63) | 0.617 (0.59–0.63) | 0.574 (0.57–0.58) | 0.594 (0.58–0.61) | 0.600 (0.55–0.67) | 0.609 (0.60–0.62) |

Top-10% lift (mean of the readable folds, primary):

| model | τ | τ+1m | τ+2m | τ+5m | τ+10m | τ+20m | vol 0.25× | vol 0.5× | vol 1× | vol 2× |
|---|---|---|---|---|---|---|---|---|---|---|
| M2 (none) | 1.24 | 1.76 | 1.81 | 1.50 | 2.02 | 2.59 | 1.93 | 1.88 | 2.15 | 2.08 |
| M3 (none) | 1.60 | 2.19 | 2.16 | 2.10 | 2.42 | 2.52 | 1.91 | 2.07 | 2.11 | 2.10 |
| M4 (none) | – | 1.30 | 1.64 | 1.34 | 1.47 | 2.09 | 1.42 | 1.70 | 1.58 | 1.96 |

Median net forward return, bp (net 70.98 bp; entry = next print after the decision time, the zero-latency upper bound; three folds pooled). Quantile functions, the cents unit and the 1 s / 5 s entries are on `forward_returns.html`:

| set | τ | τ+1m | τ+2m | τ+5m | τ+10m | τ+20m | vol 0.25× | vol 0.5× | vol 1× | vol 2× |
|---|---|---|---|---|---|---|---|---|---|---|
| M3 top decile, +30 min | -434 (n 306) | -556 (n 306) | -613 (n 306) | -558 (n 305) | -508 (n 306) | -240 (n 305) | -515 (n 293) | -526 (n 278) | -354 (n 249) | -236 (n 213) |
| all primary, +30 min | -243 (n 3,034) | -250 (n 3,030) | -214 (n 3,029) | -179 (n 3,030) | -164 (n 3,023) | -122 (n 3,014) | -190 (n 2,904) | -194 (n 2,749) | -181 (n 2,468) | -151 (n 2,104) |
| M3 top decile, to 20:00 | -570 (n 306) | -1109 (n 306) | -1054 (n 306) | -984 (n 306) | -831 (n 306) | -598 (n 306) | -1022 (n 293) | -910 (n 278) | -579 (n 249) | -663 (n 213) |
| all primary, to 20:00 | -431 (n 3,042) | -411 (n 3,042) | -379 (n 3,041) | -340 (n 3,041) | -299 (n 3,039) | -241 (n 3,037) | -344 (n 2,911) | -352 (n 2,755) | -383 (n 2,476) | -400 (n 2,113) |

M3 permutation importance, top three inputs by share (mean of three folds):

| decision time | 1st | 2nd | 3rd |
|---|---|---|---|
| τ | `tod_h` 0.25 | `log10_pre_dollars_per_min` 0.09 | `accel_k1` 0.06 |
| τ+1m | `tod_h` 0.10 | `log10_post_trades_per_min` 0.10 | `lr_dollar_rate` 0.07 |
| τ+2m | `tod_h` 0.16 | `high_log` 0.09 | `log10_post_dollars_per_min` 0.05 |
| τ+5m | `high_log` 0.17 | `tod_h` 0.13 | `u_high` 0.09 |
| τ+10m | `high_log` 0.15 | `u_high` 0.14 | `tod_h` 0.11 |
| τ+20m | `u_high` 0.25 | `high_log` 0.14 | `tod_h` 0.08 |
| vol 0.25× | `tod_h` 0.14 | `gap_share` 0.08 | `asinh_z_high` 0.07 |
| vol 0.5× | `tod_h` 0.18 | `u_high` 0.09 | `asinh_z_high` 0.08 |
| vol 1× | `tod_h` 0.17 | `dd_log` 0.08 | `high_log` 0.08 |
| vol 2× | `tod_h` 0.14 | `dd_log` 0.12 | `u_high` 0.11 |

### 4.6 chop

Primary test events of the type that reached each decision time (three folds summed): τ 1,815, τ+1m 1,815, τ+2m 1,815, τ+5m 1,815, τ+10m 1,815, τ+20m 1,815, vol 0.25× 1,744, vol 0.5× 1,650, vol 1× 1,479, vol 2× 1,280.

| model | τ | τ+1m | τ+2m | τ+5m | τ+10m | τ+20m | vol 0.25× | vol 0.5× | vol 1× | vol 2× |
|---|---|---|---|---|---|---|---|---|---|---|
| M0 (none) | 0.500 (0.50–0.50) | 0.500 (0.50–0.50) | 0.500 (0.50–0.50) | 0.500 (0.50–0.50) | 0.500 (0.50–0.50) | 0.500 (0.50–0.50) | 0.500 (0.50–0.50) | 0.500 (0.50–0.50) | 0.500 (0.50–0.50) | 0.500 (0.50–0.50) |
| M1 (none) | 0.523 (0.50–0.54) | – | – | – | – | – | – | – | – | – |
| M2 (none) | 0.551 (0.54–0.57) | 0.571 (0.56–0.59) | 0.584 (0.57–0.60) | 0.600 (0.57–0.62) | 0.620 (0.61–0.63) | 0.649 (0.63–0.66) | 0.626 (0.62–0.63) | 0.653 (0.65–0.66) | 0.651 (0.63–0.68) | 0.630 (0.60–0.66) |
| M3 (none) | 0.559 (0.54–0.58) | 0.598 (0.57–0.61) | 0.602 (0.59–0.61) | 0.625 (0.61–0.64) | 0.653 (0.64–0.66) | 0.668 (0.66–0.68) | 0.615 (0.60–0.62) | 0.653 (0.63–0.67) | 0.666 (0.65–0.70) | 0.658 (0.65–0.66) |
| M4 (none) | – | 0.518 (0.50–0.55) | 0.538 (0.52–0.56) | 0.566 (0.56–0.58) | 0.579 (0.57–0.59) | 0.613 (0.60–0.62) | 0.598 (0.58–0.62) | 0.601 (0.59–0.61) | 0.616 (0.60–0.63) | 0.592 (0.57–0.62) |
| M2 (balanced) | 0.537 (0.53–0.54) | 0.555 (0.54–0.57) | 0.561 (0.56–0.56) | 0.568 (0.56–0.57) | 0.580 (0.58–0.59) | 0.610 (0.60–0.62) | 0.582 (0.56–0.61) | 0.606 (0.59–0.62) | 0.610 (0.60–0.62) | 0.603 (0.59–0.62) |
| M3 (balanced) | 0.550 (0.53–0.56) | 0.576 (0.55–0.59) | 0.588 (0.57–0.60) | 0.602 (0.57–0.63) | 0.626 (0.61–0.65) | 0.656 (0.65–0.67) | 0.597 (0.57–0.62) | 0.638 (0.60–0.66) | 0.652 (0.62–0.68) | 0.657 (0.64–0.67) |
| M4 (balanced) | – | 0.496 (0.48–0.51) | 0.507 (0.48–0.54) | 0.525 (0.50–0.56) | 0.524 (0.51–0.55) | 0.554 (0.51–0.58) | 0.531 (0.51–0.56) | 0.547 (0.53–0.56) | 0.571 (0.57–0.58) | 0.568 (0.54–0.59) |

Top-10% lift (mean of the readable folds, primary):

| model | τ | τ+1m | τ+2m | τ+5m | τ+10m | τ+20m | vol 0.25× | vol 0.5× | vol 1× | vol 2× |
|---|---|---|---|---|---|---|---|---|---|---|
| M2 (none) | 1.14 | 1.20 | 1.19 | 1.17 | 1.23 | 1.28 | 1.30 | 1.33 | 1.33 | 1.25 |
| M3 (none) | 1.19 | 1.22 | 1.26 | 1.27 | 1.29 | 1.34 | 1.23 | 1.29 | 1.34 | 1.44 |
| M4 (none) | – | 1.04 | 1.09 | 1.17 | 1.15 | 1.14 | 1.14 | 1.22 | 1.23 | 1.21 |

Median net forward return, bp (net 70.98 bp; entry = next print after the decision time, the zero-latency upper bound; three folds pooled). Quantile functions, the cents unit and the 1 s / 5 s entries are on `forward_returns.html`:

| set | τ | τ+1m | τ+2m | τ+5m | τ+10m | τ+20m | vol 0.25× | vol 0.5× | vol 1× | vol 2× |
|---|---|---|---|---|---|---|---|---|---|---|
| M3 top decile, +30 min | -203 (n 306) | -223 (n 306) | -202 (n 306) | -156 (n 306) | -147 (n 306) | -122 (n 305) | -133 (n 291) | -191 (n 276) | -145 (n 249) | -161 (n 210) |
| all primary, +30 min | -243 (n 3,034) | -250 (n 3,030) | -214 (n 3,029) | -179 (n 3,030) | -164 (n 3,023) | -122 (n 3,014) | -190 (n 2,904) | -194 (n 2,749) | -181 (n 2,468) | -151 (n 2,104) |
| M3 top decile, to 20:00 | -383 (n 306) | -393 (n 306) | -374 (n 306) | -242 (n 306) | -382 (n 306) | -121 (n 305) | -238 (n 293) | -190 (n 277) | -278 (n 249) | -227 (n 212) |
| all primary, to 20:00 | -431 (n 3,042) | -411 (n 3,042) | -379 (n 3,041) | -340 (n 3,041) | -299 (n 3,039) | -241 (n 3,037) | -344 (n 2,911) | -352 (n 2,755) | -383 (n 2,476) | -400 (n 2,113) |

M3 permutation importance, top three inputs by share (mean of three folds):

| decision time | 1st | 2nd | 3rd |
|---|---|---|---|
| τ | `tod_h` 0.19 | `last_form` 0.10 | `log10_pre_trades_per_min` 0.10 |
| τ+1m | `tod_h` 0.16 | `asinh_z_ret` 0.08 | `u_high` 0.06 |
| τ+2m | `tod_h` 0.23 | `u_high` 0.16 | `asinh_z_ret` 0.10 |
| τ+5m | `tod_h` 0.22 | `u_high` 0.20 | `asinh_z_ret` 0.15 |
| τ+10m | `tod_h` 0.24 | `u_high` 0.21 | `asinh_z_ret` 0.13 |
| τ+20m | `u_high` 0.21 | `tod_h` 0.20 | `ret_log` 0.17 |
| vol 0.25× | `tod_h` 0.17 | `ret_log` 0.16 | `u_high` 0.11 |
| vol 0.5× | `tod_h` 0.21 | `u_high` 0.16 | `ret_log` 0.16 |
| vol 1× | `tod_h` 0.20 | `u_high` 0.19 | `ret_log` 0.11 |
| vol 2× | `tod_h` 0.19 | `ret_log` 0.14 | `u_high` 0.14 |

## 5. Pooled tables

Multiclass log-loss skill against M0 on the same test rows (1 − LL / LL_M0), primary read, mean of three folds:

| model | τ | τ+1m | τ+2m | τ+5m | τ+10m | τ+20m | vol 0.25× | vol 0.5× | vol 1× | vol 2× |
|---|---|---|---|---|---|---|---|---|---|---|
| M0 (none) | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| M1 (none) | 0.0124 | – | – | – | – | – | – | – | – | – |
| M2 (none) | -0.0197 | 0.0057 | 0.0176 | 0.0382 | 0.0639 | 0.0963 | 0.0482 | 0.0604 | 0.0674 | 0.0606 |
| M3 (none) | 0.0044 | 0.0478 | 0.0561 | 0.0869 | 0.1183 | 0.1514 | 0.0803 | 0.1070 | 0.1235 | 0.1212 |
| M4 (none) | – | 0.0009 | -0.0024 | 0.0161 | 0.0372 | 0.0633 | 0.0358 | 0.0429 | 0.0569 | 0.0576 |
| M2 (balanced) | -0.4510 | -0.4156 | -0.4024 | -0.3763 | -0.3428 | -0.2983 | -0.3606 | -0.3401 | -0.3259 | -0.3305 |
| M3 (balanced) | -0.1245 | -0.0552 | -0.0739 | -0.0173 | -0.0112 | 0.0333 | -0.0661 | -0.0247 | 0.0074 | 0.0263 |
| M4 (balanced) | – | -0.4535 | -0.4627 | -0.4407 | -0.4220 | -0.3975 | -0.4065 | -0.3791 | -0.3511 | -0.3519 |

Secondary read (all test events), M3 (none), AUC mean of three folds:

| type | τ | τ+1m | τ+2m | τ+5m | τ+10m | τ+20m | vol 0.25× | vol 0.5× | vol 1× | vol 2× |
|---|---|---|---|---|---|---|---|---|---|---|
| runaway | 0.617 (0.60–0.63) | 0.620 (0.58–0.64) | 0.638 (0.63–0.65) | 0.695 (0.68–0.72) | 0.666 (0.62–0.70) | 0.688 (0.66–0.71) | 0.658 (0.64–0.67) | 0.672 (0.63–0.69) | 0.681 (0.62–0.71) | 0.650 (0.61–0.68) |
| burst | 0.672 (0.65–0.70) | 0.691 (0.66–0.75) | 0.702 (0.66–0.74) | 0.746 (0.71–0.80) | 0.789 (0.76–0.84) | 0.814 (0.77–0.85) | 0.722 (0.71–0.73) | 0.729 (0.70–0.74) | 0.741 (0.70–0.77) | 0.763 (0.75–0.77) |
| slow climb | 0.547 (0.53–0.56) | 0.570 (0.56–0.58) | 0.585 (0.57–0.61) | 0.607 (0.59–0.62) | 0.640 (0.61–0.67) | 0.697 (0.68–0.73) | 0.618 (0.60–0.64) | 0.627 (0.62–0.64) | 0.657 (0.65–0.67) | 0.686 (0.66–0.74) |
| exhausted | 0.603 (0.59–0.61) | 0.705 (0.70–0.71) | 0.742 (0.74–0.75) | 0.800 (0.80–0.80) | 0.840 (0.84–0.85) | 0.870 (0.86–0.88) | 0.796 (0.79–0.80) | 0.833 (0.83–0.84) | 0.846 (0.84–0.86) | 0.839 (0.82–0.85) |
| fade | 0.574 (0.55–0.59) | 0.620 (0.60–0.64) | 0.631 (0.62–0.64) | 0.646 (0.62–0.66) | 0.671 (0.65–0.68) | 0.681 (0.67–0.69) | 0.642 (0.63–0.66) | 0.652 (0.63–0.66) | 0.674 (0.66–0.68) | 0.684 (0.68–0.69) |
| chop | 0.550 (0.54–0.56) | 0.579 (0.56–0.59) | 0.587 (0.58–0.59) | 0.617 (0.61–0.62) | 0.647 (0.64–0.66) | 0.671 (0.66–0.68) | 0.617 (0.61–0.63) | 0.645 (0.62–0.67) | 0.652 (0.65–0.66) | 0.647 (0.64–0.66) |

Rung: M3 (none) probabilities scored against the N = 50 and N = 200 labels (never fitted), primary read, mean AUC of three folds:

| label | type | τ | τ+1m | τ+2m | τ+5m | τ+10m | τ+20m | vol 0.25× | vol 0.5× | vol 1× | vol 2× |
|---|---|---|---|---|---|---|---|---|---|---|---|
| N = 50 | runaway | 0.576 | 0.612 | 0.614 | 0.698 | 0.669 | 0.677 | 0.671 | 0.686 | 0.671 | 0.631 |
| N = 50 | burst | 0.607 | 0.623 | 0.651 | 0.703 | 0.748 | 0.784 | 0.691 | 0.685 | 0.695 | 0.706 |
| N = 50 | slow climb | 0.516 | 0.597 | 0.586 | 0.601 | 0.644 | 0.711 | 0.594 | 0.623 | 0.646 | 0.677 |
| N = 50 | exhausted | 0.607 | 0.723 | 0.744 | 0.795 | 0.830 | 0.862 | 0.795 | 0.844 | 0.859 | 0.857 |
| N = 50 | fade | 0.554 | 0.594 | 0.618 | 0.635 | 0.649 | 0.670 | 0.629 | 0.624 | 0.680 | 0.657 |
| N = 50 | chop | 0.552 | 0.582 | 0.597 | 0.614 | 0.638 | 0.656 | 0.609 | 0.642 | 0.653 | 0.638 |
| N = 100 | runaway | 0.568 | 0.594 | 0.605 | 0.685 | 0.668 | 0.693 | 0.660 | 0.676 | 0.689 | 0.643 |
| N = 100 | burst | 0.671 | 0.680 | 0.703 | 0.743 | 0.786 | 0.818 | 0.734 | 0.716 | 0.727 | 0.763 |
| N = 100 | slow climb | 0.536 | 0.601 | 0.601 | 0.604 | 0.643 | 0.705 | 0.622 | 0.615 | 0.658 | 0.706 |
| N = 100 | exhausted | 0.604 | 0.722 | 0.748 | 0.795 | 0.836 | 0.863 | 0.789 | 0.845 | 0.856 | 0.859 |
| N = 100 | fade | 0.562 | 0.625 | 0.640 | 0.653 | 0.669 | 0.679 | 0.642 | 0.643 | 0.679 | 0.667 |
| N = 100 | chop | 0.559 | 0.598 | 0.602 | 0.625 | 0.653 | 0.668 | 0.615 | 0.653 | 0.666 | 0.658 |
| N = 200 | runaway | 0.628 | 0.642 | 0.626 | 0.713 | 0.718 | 0.733 | 0.706 | 0.717 | 0.706 | 0.660 |
| N = 200 | burst | 0.650 | 0.677 | 0.692 | 0.729 | 0.775 | 0.823 | 0.715 | 0.733 | 0.733 | 0.744 |
| N = 200 | slow climb | 0.526 | 0.580 | 0.572 | 0.612 | 0.631 | 0.691 | 0.614 | 0.608 | 0.656 | 0.704 |
| N = 200 | exhausted | 0.602 | 0.705 | 0.728 | 0.783 | 0.825 | 0.858 | 0.783 | 0.839 | 0.852 | 0.849 |
| N = 200 | fade | 0.578 | 0.608 | 0.630 | 0.647 | 0.666 | 0.684 | 0.631 | 0.641 | 0.697 | 0.677 |
| N = 200 | chop | 0.563 | 0.602 | 0.603 | 0.627 | 0.657 | 0.681 | 0.628 | 0.656 | 0.672 | 0.664 |

Confusion at the most probable type, M3 (none), primary read, three folds summed, at τ and at τ + 20 min (row = true type, cells = counts):

*τ*

| true \ predicted | runaway | burst | slow climb | exhausted | fade | chop |
|---|---|---|---|---|---|---|
| runaway | 0 | 0 | 0 | 2 | 0 | 65 |
| burst | 0 | 0 | 0 | 3 | 0 | 110 |
| slow climb | 0 | 1 | 0 | 0 | 0 | 127 |
| exhausted | 0 | 1 | 0 | 34 | 0 | 498 |
| fade | 0 | 0 | 0 | 3 | 2 | 381 |
| chop | 1 | 1 | 0 | 30 | 7 | 1,776 |

*τ+20m*

| true \ predicted | runaway | burst | slow climb | exhausted | fade | chop |
|---|---|---|---|---|---|---|
| runaway | 0 | 1 | 1 | 2 | 1 | 62 |
| burst | 0 | 12 | 4 | 2 | 0 | 95 |
| slow climb | 0 | 5 | 2 | 5 | 0 | 116 |
| exhausted | 0 | 0 | 0 | 245 | 3 | 285 |
| fade | 0 | 2 | 0 | 21 | 32 | 331 |
| chop | 2 | 9 | 2 | 126 | 32 | 1,644 |

Settings chosen by validation log loss inside the training windows (count of fold × decision time jobs):

| model | class weight | setting | jobs |
|---|---|---|---|
| M2 | balanced | `{'C': 0.1}` | 29 |
| M2 | balanced | `{'C': 1.0}` | 1 |
| M2 | none | `{'C': 0.1}` | 30 |
| M3 | balanced | `{'learning_rate': 0.03, 'max_leaf_nodes': 15, 'max_iter': 200}` | 4 |
| M3 | balanced | `{'learning_rate': 0.03, 'max_leaf_nodes': 15, 'max_iter': 500}` | 1 |
| M3 | balanced | `{'learning_rate': 0.03, 'max_leaf_nodes': 31, 'max_iter': 200}` | 22 |
| M3 | balanced | `{'learning_rate': 0.03, 'max_leaf_nodes': 31, 'max_iter': 500}` | 3 |
| M3 | none | `{'learning_rate': 0.03, 'max_leaf_nodes': 15, 'max_iter': 200}` | 30 |
| M4 | balanced | `{'k': 100}` | 27 |
| M4 | none | `{'k': 100}` | 27 |

## 6. Rulings and declared interpretations

- **R1_tau_close_sensitive** — measured: tau_close_sensitive (b1 A1.3: |tau(revised close) - tau(minute-bar close)| > 60 s) is not settled at tau for 3,585 of 15,519 events: the minute-bar-close crossing comes after tau for 3,302 and never happens for 283. It is settled by tau + 60 s for every event. Ruling: causal 3-level input: at each decision time d the flag as far as it is settled by d -- TRUE / FALSE / not_settled.
- **R2_short_interest** — measured: F1's si_asof_ns is the SETTLEMENT date (midnight UTC), not publication; settlement -> event date median 7 calendar days, 5% on the event date itself. No publication date on disk. Under an 8-session publication assumption only 2,104 of 15,107 events would use the settlement F1 used. Ruling: latest settlement whose assumed publication, 10 XNYS sessions after settlement (conservative; FINRA's actual lag not verifiable offline [verify]), is a session strictly before the event date.
- **R3_fundamentals_anchor** — measured: F1 anchors at t0 (D28/D33); t0 > tau for 1,477 events. One event (LNSR_2024-11-07_31.57) carries a shares count accepted after tau; six events' F1 filing windows reach past tau (dilution flag FALSE for all six either way). Ruling: re-anchor at tau with D28's rule: accepted_ns < tau (and, for shares, asof < tau as in F1's T5), from F1's own raw SEC archive.
- **R4_positive_control** — measured: on S1's tables with the S2 folds (primary sets, HGB): + terminal_log gives runaway 0.94-0.95, burst 0.79-0.81, slow climb 0.89-0.92, exhausted 0.76-0.80, fade 0.85-0.88, chop 0.75-0.80 -- row 3 would fire because terminal return does not set the type. + the rule inputs gives 1.000 (HGB) and >= 0.993 (logistic) for every type and fold. Ruling: two positive-control runs on M2 and M3 at every decision time; row 3 gates on the rule-inputs leak (post100_rise_pct, post100_fall_pct, post100_u_peak); the briefed terminal_log run is reported beside it, ungated.
- **R5_negative_control** — measured: one shuffle per fold (HGB, 10 shuffles): runaway ranged 0.32-0.69 and fell outside 0.45-0.55 in 60% of fold cells (burst/slow climb/fade 17-20%, exhausted 10%, chop 0%); pooling folds biases runaway to 0.458 because base rates differ by fold Ruling: 10 independent shuffles per fold; row 2 reads the mean per-fold AUC over the 3 folds x 10 shuffles for each type x model x decision time against 0.45-0.55; hyperparameters fixed at the real run's choices; single-shuffle per-fold values reported beside it.

- `not_reached`: a checkpoint's decision exists only for events that reach it; reach status is known only at 20:00 (when the whole path, hence the label, is known), so it can never be an input. Each checkpoint's models are fitted and scored on events that reached it; not_reached and undefined events stay in every table with counts per fold x type x checkpoint
- `undefined_volume_checkpoint`: tau in an auction minute has no segment start (Amendment 3), so the reference volume and the four volume checkpoints are 'undefined' for those events
- `wall_clock_past_2000`: tau + x beyond 20:00 ET is not_reached
- `m0_per_checkpoint`: M0 at checkpoint c = type shares among the training events that reached c
- `latency`: brief's entry (next print strictly after the decision time) is primary and is the zero-latency upper bound (Phase 8 / D7 convention); CLAUDE.md / D5 require realistic latency, so entries at the first print at or after d + 1 s and d + 5 s (Phase 10e's tick latency grid) are reported beside it
- `class_weights`: none and balanced are separate model variants for M2, M3 and M4, each tuned on its own; both reported. M4 balanced = neighbour votes weighted by 1 / training class share, renormalised
- `tuning_split`: inside each fold's training window: sub-train = training years before the last one; validation = the last training year's events whose ticker is not in the sub-train years (mirrors the primary read). Refit on the whole training window with the chosen setting
- `hgb_early_stopping`: off (sklearn turns it on by itself above 10,000 rows, which would override the declared iteration grid)
- `hgb_categoricals`: native (categorical_features), one column per input
- `m2_encoding`: numeric: training median fill + missing-indicator column for every input missing anywhere in training; booleans as 0/1 with the same; categoricals one-hot with a 'missing' level; StandardScaler; lbfgs multinomial, max_iter 3000
- `smoothing`: M1 cell shares and M4 neighbour shares smoothed with one pseudo-event at M0's shares: (n_type + 1 * p0_type) / (n + 1), so log loss is finite
- `m1_cells`: turnover band = training-fold quartiles of log10 turnover plus 'missing'; ignition True / False / missing; tau_anchor_segment (5 levels)
- `tau_rounding`: d = tau_d = max(stored tau_ns, the crossing print's own timestamp). Every stored tau_ns in b1 / b2 / S1 is a multiple of 256 ns (float64-rounded upstream, error <= 128 ns either way; T0 measured it before the build); the crossing print = the earliest print at tau_price within 128 ns of the stored value. Inputs b2 / S1 built on the stored tau are then <= tau_d, the crossing print is <= tau_d, and entries (next print after d) are never the crossing print. Wall-clock and volume checkpoints count from tau_d
- `group_b_offsets`: post_trades_per_min = (collapsed prints + 0.5) / elapsed minutes; post_dollars_per_min = (dollars + 1) / elapsed minutes (finite logs when nothing traded); elapsed floored at 1 s
- `group_b_transforms`: log1p on max_gap_s and since_last_print_s; asinh on z_ret, z_high, z_dd, rv_ratio (monotone, so M3 is unaffected; keeps M2's standardisation finite)
- `sigma_pre_not_an_input`: sigma_pre is the noise scale only; it is not itself a model input

Excluded inputs: `flag_cross_session_extreme` — A12 flag; T0 documents that it is built from the event day's own last trade (after tau) -- excluded; `competition_excess` — uses other names' activity after tau; `post_tau_vector_components` — every S1 or b2 post-tau vector component (u_peak, rise_s, fall_s, terminal, sigma_path, jump_share, halt_in_path, ...); `momentum_pct` — D4 (and set from the day's RTH high); `f1_t0_anchored_fields` — flg_dilution_form_before_t0, shs_* as anchored at t0, si_* as settlement-dated: replaced by the R2/R3 tau-anchored versions; `tau_close_sensitive_raw` — replaced by the R1 causal state.

Deferred, not built (brief §4): a two-stage model; predicting the components and applying the type rules; sequential updating of the at-crossing probabilities.

## 7. Reproduction and outputs

```
.venv/Scripts/python.exe research/shape_classifier_s2/t1_group_a.py
.venv/Scripts/python.exe research/shape_classifier_s2/t2_checkpoints.py
.venv/Scripts/python.exe research/shape_classifier_s2/t0_audit.py
.venv/Scripts/python.exe research/shape_classifier_s2/t3_folds.py
.venv/Scripts/python.exe research/shape_classifier_s2/t4_models.py
.venv/Scripts/python.exe research/shape_classifier_s2/t4_scores.py
.venv/Scripts/python.exe research/shape_classifier_s2/t5_controls.py
.venv/Scripts/python.exe research/shape_classifier_s2/t6_money.py
.venv/Scripts/python.exe research/shape_classifier_s2/t7_importance.py
.venv/Scripts/python.exe research/shape_classifier_s2/charts.py
.venv/Scripts/python.exe research/shape_classifier_s2/build_report.py
```

T0's audit runs after T1 and T2 because it audits what they built; T1 and T2 also assert their own inputs as they write them. `results/shape_classifier/s2/cache/` (master-grid paths, rebuilt by T2) is git-ignored in place and not committed.

Artifacts (`results/shape_classifier/s2/artifacts/`): `t0_a12.json`, `t0_audit.parquet`, `t0_summary.json`, `t1_group_a.parquet`, `t1_summary.json`, `t2_checkpoints.parquet`, `t2_event_meta.parquet`, `t2_forward.parquet`, `t2_group_c.parquet`, `t2_summary.json`, `t2_typical_paths.parquet`, `t2b_mb_diagnosis.json`, `t2b_mb_diagnosis.parquet`, `t3_counts.parquet`, `t3_membership.parquet`, `t3_row5.parquet`, `t3_summary.json`, `t4_auc.parquet`, `t4_calibration.parquet`, `t4_confusion.parquet`, `t4_lift.parquet`, `t4_logloss.parquet`, `t4_predictions.parquet`, `t4_scores_summary.json`, `t4_summary.json`, `t4_tuning.parquet`, `t5_negative.parquet`, `t5_negative_gate.parquet`, `t5_positive.parquet`, `t5_summary.json`, `t6_forward.parquet`, `t6_summary.json`, `t7_importance.parquet`, `t7_row4.parquet`, `t7_summary.json`.

Charts: `charts/t4/auc_by_time.html`, `charts/t4/lift_by_time.html`, `charts/t4/calibration.html`, `charts/t4/confusion.html`, `charts/t5/controls.html`, `charts/t6/forward_returns.html`, `charts/t7/importance.html`.

