# Shape classifier S2 — can the six types be predicted, at the crossing and as the path unfolds?

**Brief:** `prompts/shape_classifier_s2.md` and **Amendment 1** `prompts/shape_classifier_s2_amendment_1.md` · **Config:** `config/shape_classifier_s2.json` (hash `8f42e9c7eb74`) · **Branch:** `explore/shape-classifier-s2` · **Code:** `research/shape_classifier_s2/` · **Built at:** `3617bc3` · 2026-09-29

Exploratory modelling build, not a phase. The test is ticker-blocked and time-ordered (folds test 2022, 2023, 2024); everything else is exploratory. This report describes the artifacts and charts; it does not interpret them.

**Two labels (Amendment 1 A1.3).** *Remaining* (primary): the S1 type of the path from each checkpoint's entry (the next print after the decision time) to 20:00, by S1's rules and its own 200-draw null; at τ it is the whole-path type. *Whole* (secondary): the S1 type of the whole post-τ path, as first run. Every table below carries both.

**Status: stop after the report (Amendment 1 A1.5) for Cooper.**

## Escalation table

| row | criterion | tier | observed | fires |
|---|---|---|---|---|
| 1 | any input uses data after its decision time | HARD STOP | 0 input rows after their decision time (t0_audit.parquet) | no |
| 2 | negative control outside 0.45–0.55 (R5 read: mean of 3 folds × 10 shuffles) | HARD STOP | 0 of 708 label × type × model × time cells outside; means span 0.465–0.530 | no |
| 3 | positive control below 0.95 (R4 rule inputs; A1.1: M3 gated, M2 reported) | HARD STOP | M3: 0 of 720 per-fold cells below 0.95 (minimum 0.9980); M2, ungated: remaining 4 of 360 below (min 0.9266); whole 7 of 360 below (min 0.9384) | no |
| 4 | one input > half of a type's permutation importance (M3) | LOG | 2 label × fold × time × type cells; inputs: ret_log, tod_h | LOG |
| 5 | a fold's primary test set < 20 labelled events of a type | LOG | remaining 10 fold × time × type cells; whole 14 fold × time × type cells (§3) | LOG |
| 6 | sklearn / HistGradientBoostingClassifier unavailable offline | HARD STOP | sklearn 1.8.0; HistGradientBoostingClassifier imported | no |

Row 3 on the first run (commit `92c99cc`): 7 of 720 cells below 0.95, all M2 (balanced), chop; cleared by Cooper's A1.1 on that run (M3 1.000 in every cell). The table above is the re-run.

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

33 tracked code files read the flag (list checked against `git grep`): 32 facet, 1 builder. Files that use it as an **input** (a fitted model, a selection rule or a threshold): **0**. The rough pre-S2 run (Claude, on S1's per-event tables, brief 'What came before') used the flag as a model input; it is not in the repository.

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

Non-code records naming the flag (reports, briefs, configs, docs): 38 files — `CLAUDE.md`, `config/attention_excursion_b2.json`, `config/phase_10.json`, `config/phase_10_v2.json`, `config/phase_10e.json`, `config/phase_11.json`, `config/phase_9.json`, `config/relative_momentum_v0.json`, `config/scale_field_panels.json`, `config/shape_atlas_s1.json`, `config/shape_classifier_s2.json`, `docs/Open-Items-Register.md`, `docs/Research-Library-Map.md`, `docs/Universe-Decisions.md`, `prompts/attention_excursion.md`, `prompts/attention_excursion_b1.md`, `prompts/phase_11.md`, `prompts/phase_9.md`, `prompts/shape_classifier_s2.md`, `prompts/shape_classifier_s2_amendment_1.md`, `results/attention_excursion/b1/REPORT.md`, `results/attention_excursion/b2/REPORT.md`, `results/phase_10/REPORT_v2_v3_superseded.md`, `results/phase_10e/REPORT.md`, `results/phase_9/REPORT.md`, `results/relative_momentum/r0/REPORT.md`, `results/relative_momentum/v0/REPORT.md`, `results/relative_momentum/v1/REPORT.md`, `results/reports/attention_excursion_b1_report.md`, `results/reports/attention_excursion_b2_report.md`, `results/reports/phase_10_v2_report.md`, `results/reports/phase_10e_report.md`, `results/reports/phase_9_report.md`, `results/reports/relative_momentum_r0_report.md`, `results/reports/relative_momentum_v0_report.md`, `results/reports/relative_momentum_v1_report.md`, `results/reports/shape_classifier_s2_report.md`, `results/shape_classifier/s2/REPORT.md`.

**A1.6 (recorded, acted on separately).** recorded: the tm1_t0 A12 flag reads the event day's own last trade (T0), so the 32 earlier with/without splits were partly splits on the event day's outcome; a retraction-sweep note and a split-record corporate-action flag are listed for Cooper as a separate item, not part of this re-run.

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

Row 1: **0** violations. Per decision time: `artifacts/t0_audit.parquet`. The labels (both) are outputs, never inputs.

### 1.4 Other timing findings, measured before the build

- **Stored τ is float64-rounded.** every stored tau_ns in b1 t2_tau, b2 and S1 is a multiple of 256 ns: float64-rounded upstream (error <= 128 ns either way): all 15,519 stored values are multiples of 256 ns; the crossing print equals the stored value for 1,436, is later for 7,146 and earlier for 6,937 (max |difference| 128 ns). 38 events have prints after the crossing print and at or before the stored τ (38 prints). Handling: decision time at tau = tau_d = max(stored tau, the crossing print's own timestamp); b2 / S1 inputs built on the stored tau are then <= tau_d, the crossing print is <= tau_d, and entries are after it. Live names crossing after τ_d: 0.
- **`tau_close_sensitive` (Cooper R1) and the A1.2 fix.** Not settled at τ for 3,585 events (measured on b1's stored values before the build). The minute-bar crossing is recomputed from ticks with b1's `first_crossing` on the full print arrays (A1.2): 15,236 of 15,236 within 128 ns of b1's stored value (max 0.000000128 s; exact-only 0, b1-only 0); the fully settled flag equals b1's for 15,519 of 15,519. Before the fix, 66 events differed (T2 called it on the 04:00–20:00 slice; diagnosis `artifacts/t2b_mb_diagnosis.*`, as committed at `92c99cc`). State at each decision time: τ false 10,804, not_settled 3,591, true 1,124; τ+1m false 13,085, not_settled 1,310, true 1,124; τ+2m false 13,085, true 2,434; τ+5m false 13,085, true 2,434; τ+10m false 13,085, true 2,434; τ+20m false 13,085, true 2,434; vol 0.25× false 12,482, not_settled 312, true 2,097; vol 0.5× false 11,947, not_settled 156, true 1,985; vol 1× false 10,941, not_settled 77, true 1,716; vol 2× false 9,473, not_settled 39, true 1,319.
- **Short interest (Cooper R2).** F1's `si_asof_ns` is the settlement date, not publication. Rebuilt from the raw vendor files: latest settlement whose assumed publication (10 XNYS sessions later) is before the event date — 14,803 events (F1 settlement-dated: 15,107; same value as F1: 162); median settlement 24 days before the event. FINRA's actual lag is not verifiable offline [verify].
- **Fundamentals re-anchored at τ (Cooper R3).** Shares outstanding available for 12,429 events (F1 at t0: 11,835); equal to F1's value for 14,921, different for 598; split correction applied to 1,197. Dilution flag TRUE for 1,194 (F1 at t0: 1,196; 4 differ). Filings cross-check against b2 (accepted < τ): filing_24h agrees for 100.00%, last form for 99.99% of 15,347 events.
- **τ is confirmed at its successor.** Tau is the first print >= 1.30 x prior close that is not a spike; the spike test reads the print after it, so tau is confirmed at its successor. Seconds from the τ print to its successor: median 0.002092, 90th pct 5.119, 99th 201.6, max 10861; zero (same timestamp) for 0.7% (n 15,517).
- **Live set.** Live_n / flow_share count other D1 names that crossed at or before tau; D1 membership is the vendor's day-level selection (momentum_pct, RTH high), so the live set is conditional on that selection boundary like the whole population (D4, A13).
- CLAUDE.md index check (`tools/verify_claude_md_indices.py`): exit 0.

## 2. Controls (T5) — `charts/t5/controls.html`

**Negative (Cooper R5).** Labels permuted within each fold's training window (the remaining label per decision time), 10 shuffles per fold, Group C typical paths rebuilt from the permuted labels, M1–M4 at the real run's settings. Row 2 reads the mean of the 30 per-fold primary AUCs: 0 of 708 cells outside 0.45–0.55; means span 0.465–0.530. Single-shuffle per-fold AUCs outside the band: 5,192 of 21,240 (the brief's construction read cell by cell).

| label | model | class weight | mean AUC, min | mean AUC, max | single shuffle, min | single shuffle, max |
|---|---|---|---|---|---|---|
| remaining | M1 | none | 0.491 | 0.508 | 0.347 | 0.664 |
| remaining | M2 | balanced | 0.479 | 0.520 | 0.324 | 0.674 |
| remaining | M2 | none | 0.472 | 0.519 | 0.316 | 0.691 |
| remaining | M3 | balanced | 0.481 | 0.528 | 0.329 | 0.742 |
| remaining | M3 | none | 0.477 | 0.527 | 0.283 | 0.666 |
| remaining | M4 | balanced | 0.488 | 0.530 | 0.329 | 0.690 |
| remaining | M4 | none | 0.490 | 0.528 | 0.335 | 0.708 |
| whole | M1 | none | 0.491 | 0.508 | 0.347 | 0.664 |
| whole | M2 | balanced | 0.479 | 0.517 | 0.287 | 0.680 |
| whole | M2 | none | 0.470 | 0.514 | 0.276 | 0.660 |
| whole | M3 | balanced | 0.472 | 0.528 | 0.302 | 0.749 |
| whole | M3 | none | 0.465 | 0.527 | 0.242 | 0.694 |
| whole | M4 | balanced | 0.487 | 0.516 | 0.288 | 0.688 |
| whole | M4 | none | 0.486 | 0.518 | 0.278 | 0.694 |

**Positive (Cooper R4; row 3 per A1.1).** The rule inputs of each label's own path (whole: post100 rise_pct, fall_pct, u_peak; remaining: the remaining path's) added to M2 and M3 at every decision time, real run's settings. Row 3 gates M3: 0 of 720 per-fold cells below 0.95; minimum 0.9980. Minimum per-fold primary AUC by label, model, class weight and type:

| label | model | class weight | runaway | burst | slow climb | exhausted | fade | chop |
|---|---|---|---|---|---|---|---|---|
| remaining | M2 | balanced | 0.9781 | 0.9566 | 0.9537 | 0.9649 | 0.9622 | 0.9266 |
| remaining | M2 | none | 0.9863 | 0.9609 | 0.9537 | 0.9737 | 0.9700 | 0.9453 |
| remaining | M3 | balanced | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
| remaining | M3 | none | 1.0000 | 0.9997 | 1.0000 | 0.9980 | 1.0000 | 1.0000 |
| whole | M2 | balanced | 0.9745 | 0.9641 | 0.9699 | 0.9741 | 0.9655 | 0.9384 |
| whole | M2 | none | 0.9805 | 0.9721 | 0.9693 | 0.9806 | 0.9773 | 0.9591 |
| whole | M3 | balanced | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 |
| whole | M3 | none | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 1.0000 |

terminal_log of each label's own path (the brief's construction), reported ungated — mean (minimum) of the per-fold primary AUCs over folds and decision times:

| label | model | class weight | runaway | burst | slow climb | exhausted | fade | chop |
|---|---|---|---|---|---|---|---|---|
| remaining | M2 | balanced | 0.930 (0.884) | 0.752 (0.658) | 0.856 (0.808) | 0.781 (0.748) | 0.865 (0.821) | 0.774 (0.742) |
| remaining | M2 | none | 0.948 (0.899) | 0.803 (0.734) | 0.895 (0.859) | 0.793 (0.758) | 0.869 (0.828) | 0.797 (0.768) |
| remaining | M3 | balanced | 0.952 (0.932) | 0.792 (0.707) | 0.893 (0.849) | 0.793 (0.748) | 0.868 (0.841) | 0.804 (0.770) |
| remaining | M3 | none | 0.957 (0.937) | 0.822 (0.722) | 0.903 (0.868) | 0.808 (0.763) | 0.875 (0.840) | 0.809 (0.773) |
| whole | M2 | balanced | 0.940 (0.860) | 0.791 (0.713) | 0.884 (0.856) | 0.839 (0.749) | 0.884 (0.859) | 0.786 (0.764) |
| whole | M2 | none | 0.957 (0.896) | 0.826 (0.768) | 0.913 (0.886) | 0.842 (0.758) | 0.894 (0.869) | 0.809 (0.781) |
| whole | M3 | balanced | 0.957 (0.895) | 0.816 (0.768) | 0.901 (0.875) | 0.872 (0.748) | 0.901 (0.852) | 0.818 (0.770) |
| whole | M3 | none | 0.961 (0.918) | 0.841 (0.787) | 0.908 (0.889) | 0.877 (0.763) | 0.906 (0.860) | 0.823 (0.773) |

**Baseline (M1 vs M0 at τ, where both labels are the same), primary read, mean of three folds:**

| model | runaway | burst | slow climb | exhausted | fade | chop | log loss | skill vs M0 |
|---|---|---|---|---|---|---|---|---|
| M0 | 0.500 | 0.500 | 0.500 | 0.500 | 0.500 | 0.500 | 1.2212 | 0.0000 |
| M1 | 0.586 | 0.673 | 0.572 | 0.592 | 0.546 | 0.523 | 1.2059 | 0.0124 |

## 3. Population, decision times, labels and folds (T2, T3a, T3)

15,519 S1 events with τ; excluded from every fold: 49 dev_v3 and 4 sidecar events; without the whole-path label: 6.

| decision time | reached | not_reached | undefined | elapsed min (10/50/90th pct) | remaining label typed | no entry | path too short | σ zero / no null |
|---|---|---|---|---|---|---|---|---|
| τ | 15,519 | 0 | 0 | – | 15,513 | 0 | 0 | 0 |
| τ+1m | 15,519 | 0 | 0 | – | 15,502 | 8 | 8 | 1 |
| τ+2m | 15,519 | 0 | 0 | – | 15,499 | 9 | 9 | 2 |
| τ+5m | 15,519 | 0 | 0 | – | 15,493 | 13 | 9 | 4 |
| τ+10m | 15,519 | 0 | 0 | – | 15,482 | 18 | 13 | 6 |
| τ+20m | 15,519 | 0 | 0 | – | 15,453 | 31 | 28 | 7 |
| vol 0.25× | 14,891 | 443 | 185 | 0.1 / 2.8 / 36.9 | 14,859 | 4 | 20 | 8 |
| vol 0.5× | 14,088 | 1,246 | 185 | 0.1 / 5.4 / 68.9 | 14,053 | 10 | 18 | 7 |
| vol 1× | 12,734 | 2,600 | 185 | 0.3 / 8.7 / 118.2 | 12,703 | 10 | 12 | 9 |
| vol 2× | 10,831 | 4,503 | 185 | 0.4 / 12.8 / 160.7 | 10,806 | 14 | 9 | 2 |

Type shares of the remaining-path label at each decision time (all events with the label):

| type | τ | τ+1m | τ+2m | τ+5m | τ+10m | τ+20m | vol 0.25× | vol 0.5× | vol 1× | vol 2× |
|---|---|---|---|---|---|---|---|---|---|---|
| runaway | 377 | 383 | 390 | 419 | 445 | 448 | 383 | 389 | 350 | 292 |
| burst | 590 | 563 | 535 | 547 | 509 | 520 | 581 | 570 | 488 | 483 |
| slow climb | 615 | 638 | 657 | 698 | 747 | 775 | 664 | 619 | 603 | 532 |
| exhausted | 2,754 | 2,887 | 2,891 | 2,888 | 2,903 | 2,680 | 2,564 | 2,419 | 2,246 | 1,860 |
| fade | 1,878 | 1,777 | 1,770 | 1,685 | 1,617 | 1,521 | 1,663 | 1,550 | 1,386 | 1,197 |
| chop | 9,299 | 9,254 | 9,256 | 9,256 | 9,261 | 9,509 | 9,004 | 8,506 | 7,630 | 6,442 |

**How often the remaining-path type differs from the whole-path type (A1.5), per whole-path type** — share of the events of that whole type whose remaining type at the checkpoint is different (n = labelled, non-dev events of the whole type at that checkpoint):

| whole type | τ | τ+1m | τ+2m | τ+5m | τ+10m | τ+20m | vol 0.25× | vol 0.5× | vol 1× | vol 2× |
|---|---|---|---|---|---|---|---|---|---|---|
| runaway | 0% (n 375) | 15% (n 375) | 19% (n 375) | 22% (n 375) | 22% (n 374) | 27% (n 374) | 24% (n 359) | 29% (n 343) | 31% (n 328) | 37% (n 290) |
| burst | 0% (n 588) | 26% (n 588) | 35% (n 588) | 43% (n 588) | 50% (n 587) | 58% (n 586) | 32% (n 577) | 35% (n 570) | 42% (n 557) | 48% (n 541) |
| slow climb | 0% (n 613) | 19% (n 613) | 20% (n 613) | 24% (n 613) | 26% (n 613) | 35% (n 612) | 22% (n 602) | 30% (n 593) | 37% (n 569) | 41% (n 541) |
| exhausted | 0% (n 2,745) | 32% (n 2,738) | 40% (n 2,735) | 52% (n 2,734) | 59% (n 2,729) | 66% (n 2,718) | 48% (n 2,549) | 53% (n 2,347) | 55% (n 1,978) | 54% (n 1,519) |
| fade | 0% (n 1,872) | 28% (n 1,872) | 30% (n 1,872) | 40% (n 1,872) | 48% (n 1,871) | 57% (n 1,870) | 34% (n 1,825) | 40% (n 1,759) | 45% (n 1,618) | 49% (n 1,360) |
| chop | 0% (n 9,267) | 14% (n 9,263) | 16% (n 9,263) | 20% (n 9,258) | 22% (n 9,255) | 24% (n 9,241) | 17% (n 8,897) | 19% (n 8,391) | 21% (n 7,608) | 23% (n 6,515) |

What the whole type becomes at τ + 20 min (counts of the remaining type), for reference:

| whole type \ remaining type | runaway | burst | slow climb | exhausted | fade | chop |
|---|---|---|---|---|---|---|
| runaway | 273 | 0 | 17 | 1 | 0 | 83 |
| burst | 1 | 245 | 1 | 37 | 104 | 198 |
| slow climb | 4 | 23 | 396 | 1 | 23 | 165 |
| exhausted | 8 | 14 | 17 | 919 | 181 | 1,579 |
| fade | 0 | 36 | 7 | 621 | 809 | 397 |
| chop | 161 | 201 | 335 | 1,094 | 395 | 7,055 |

Folds (whole-path type counts; the remaining label's per-checkpoint counts are in `artifacts/t3_counts.parquet`):

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

**Row 5 (LOG).** Fold × decision time × type cells with fewer than 20 labelled events of the type among the primary events that reached the decision time; shown (hollow markers) and not read; the cells follow.

*remaining label* (10 cells)

| fold | type | decision times | n range |
|---|---|---|---|
| 2 | runaway | vol 0.25×, vol 0.5×, vol 1×, vol 2× | 12–17 |
| 3 | runaway | τ, τ+10m, vol 0.25×, vol 0.5×, vol 1×, vol 2× | 10–19 |

*whole label* (14 cells)

| fold | type | decision times | n range |
|---|---|---|---|
| 2 | runaway | vol 0.25×, vol 0.5×, vol 1×, vol 2× | 16–19 |
| 3 | runaway | τ, τ+1m, τ+2m, τ+5m, τ+10m, τ+20m, vol 0.25×, vol 0.5×, vol 1×, vol 2× | 11–15 |

## 4. Results per type — `charts/t4/auc_by_time.html`, `lift_by_time.html`, `calibration.html`, `confusion.html`, `charts/t6/money_intervals.html`, `forward_returns.html`, `charts/t7/importance.html`

AUC cells: mean of the readable folds' primary-read AUCs, with their range in brackets; `[k/3 read]` marks cells where row 5 leaves only k of the three folds readable (the others are on the chart, hollow). Rows pair the two labels for each model (class weight none; balanced in §5). At τ both labels are the same. Per-fold values with 95% ticker-bootstrap intervals: `artifacts/t4_auc.parquet` and the chart.

Money (A1.4): median net forward return of the model's decile minus that of all primary test events at the decision time, bp net of 70.98, next-print entry, with the 95% ticker-bootstrap interval (500 resamples, paired) and n; M3 (none). Every entry, unit, horizon and model: `charts/t6/money_intervals.html`, `artifacts/t6_forward.parquet`.

### 4.1 runaway

Labelled primary test events of the type at each decision time (three folds summed) — remaining: τ 67, τ+1m 77, τ+2m 77, τ+5m 80, τ+10m 76, τ+20m 78, vol 0.25× 67, vol 0.5× 69, vol 1× 63, vol 2× 46; whole: τ 67, τ+1m 67, τ+2m 67, τ+5m 67, τ+10m 67, τ+20m 67, vol 0.25× 63, vol 0.5× 61, vol 1× 59, vol 2× 53.

| model — label | τ | τ+1m | τ+2m | τ+5m | τ+10m | τ+20m | vol 0.25× | vol 0.5× | vol 1× | vol 2× |
|---|---|---|---|---|---|---|---|---|---|---|
| M1 (τ only) | 0.630 (0.59–0.67) [2/3 read] | – | – | – | – | – | – | – | – | – |
| M2 — remaining | 0.614 (0.57–0.66) [2/3 read] | 0.622 (0.61–0.64) | 0.623 (0.60–0.65) | 0.628 (0.60–0.66) | 0.657 (0.62–0.69) [2/3 read] | 0.579 (0.56–0.61) | 0.595 (0.60–0.60) [1/3 read] | 0.547 (0.55–0.55) [1/3 read] | 0.641 (0.64–0.64) [1/3 read] | 0.503 (0.50–0.50) [1/3 read] |
| M2 — whole | 0.614 (0.57–0.66) [2/3 read] | 0.619 (0.57–0.67) [2/3 read] | 0.625 (0.60–0.65) [2/3 read] | 0.653 (0.62–0.68) [2/3 read] | 0.666 (0.66–0.68) [2/3 read] | 0.680 (0.67–0.68) [2/3 read] | 0.705 (0.70–0.70) [1/3 read] | 0.740 (0.74–0.74) [1/3 read] | 0.767 (0.77–0.77) [1/3 read] | 0.738 (0.74–0.74) [1/3 read] |
| M3 — remaining | 0.603 (0.55–0.65) [2/3 read] | 0.657 (0.62–0.68) | 0.659 (0.64–0.68) | 0.662 (0.61–0.71) | 0.627 (0.61–0.65) [2/3 read] | 0.604 (0.58–0.65) | 0.571 (0.57–0.57) [1/3 read] | 0.567 (0.57–0.57) [1/3 read] | 0.606 (0.61–0.61) [1/3 read] | 0.656 (0.66–0.66) [1/3 read] |
| M3 — whole | 0.603 (0.55–0.65) [2/3 read] | 0.621 (0.58–0.66) [2/3 read] | 0.661 (0.65–0.68) [2/3 read] | 0.715 (0.66–0.77) [2/3 read] | 0.626 (0.61–0.65) [2/3 read] | 0.659 (0.66–0.66) [2/3 read] | 0.741 (0.74–0.74) [1/3 read] | 0.744 (0.74–0.74) [1/3 read] | 0.730 (0.73–0.73) [1/3 read] | 0.711 (0.71–0.71) [1/3 read] |
| M4 — remaining | – | 0.540 (0.43–0.65) | 0.488 (0.45–0.54) | 0.559 (0.51–0.64) | 0.490 (0.45–0.53) [2/3 read] | 0.502 (0.43–0.55) | 0.534 (0.53–0.53) [1/3 read] | 0.553 (0.55–0.55) [1/3 read] | 0.540 (0.54–0.54) [1/3 read] | 0.570 (0.57–0.57) [1/3 read] |
| M4 — whole | – | 0.496 (0.46–0.53) [2/3 read] | 0.491 (0.46–0.52) [2/3 read] | 0.589 (0.56–0.62) [2/3 read] | 0.648 (0.56–0.74) [2/3 read] | 0.632 (0.55–0.71) [2/3 read] | 0.553 (0.55–0.55) [1/3 read] | 0.671 (0.67–0.67) [1/3 read] | 0.656 (0.66–0.66) [1/3 read] | 0.585 (0.59–0.59) [1/3 read] |

Top-10% lift (mean of the readable folds, primary):

| model — label | τ | τ+1m | τ+2m | τ+5m | τ+10m | τ+20m | vol 0.25× | vol 0.5× | vol 1× | vol 2× |
|---|---|---|---|---|---|---|---|---|---|---|
| M2 — remaining | 2.07 | 2.23 | 1.86 | 1.94 | 1.91 | 1.53 | 2.55 | 1.84 | 2.05 | 0.82 |
| M2 — whole | 2.07 | 1.67 | 1.73 | 1.73 | 2.12 | 2.29 | 2.06 | 3.41 | 3.44 | 4.57 |
| M3 — remaining | 2.07 | 1.95 | 2.16 | 2.22 | 2.46 | 1.78 | 1.53 | 2.11 | 1.76 | 1.65 |
| M3 — whole | 2.07 | 2.29 | 2.46 | 2.96 | 1.84 | 1.84 | 2.74 | 4.44 | 3.44 | 4.57 |

Decile minus all, median net bp (M3, next-print entry):

| label, set, horizon | τ | τ+1m | τ+2m | τ+5m | τ+10m | τ+20m | vol 0.25× | vol 0.5× | vol 1× | vol 2× |
|---|---|---|---|---|---|---|---|---|---|---|
| remaining, top decile, +30 min | +95 [-13, +181] (n 306) | +166 [+86, +242] (n 305) | +69 [+9, +159] (n 303) | +108 [+23, +181] (n 303) | +30 [-33, +133] (n 305) | +14 [-85, +60] (n 303) | +75 [-27, +164] (n 291) | +136 [+85, +230] (n 274) | +95 [+28, +128] (n 246) | +78 [-22, +140] (n 213) |
| remaining, bottom decile, +30 min | -133 [-216, -52] (n 305) | -52 [-156, +37] (n 304) | -101 [-187, -3] (n 304) | -130 [-229, -41] (n 305) | +19 [-52, +76] (n 302) | +51 [-78, +69] (n 302) | -140 [-228, -43] (n 293) | -39 [-179, +91] (n 275) | -200 [-316, +8] (n 247) | +6 [-172, +91] (n 209) |
| remaining, top decile, to 20:00 | +50 [-196, +212] (n 306) | +236 [+102, +410] (n 305) | +85 [-35, +234] (n 305) | +270 [+108, +443] (n 305) | +157 [+12, +319] (n 305) | -8 [-174, +123] (n 304) | +201 [+52, +300] (n 293) | +307 [+170, +444] (n 276) | +314 [+207, +435] (n 248) | +402 [+126, +574] (n 213) |
| remaining, bottom decile, to 20:00 | -140 [-234, -2] (n 306) | -84 [-219, +96] (n 305) | -63 [-210, +123] (n 305) | -154 [-293, +22] (n 305) | +142 [+1, +243] (n 305) | +80 [-47, +196] (n 304) | -29 [-281, +155] (n 293) | -110 [-272, +60] (n 276) | +5 [-170, +179] (n 248) | -8 [-294, +306] (n 213) |
| whole, top decile, +30 min | +95 [-19, +169] (n 306) | +92 [-22, +173] (n 305) | +102 [+8, +176] (n 305) | +67 [-49, +159] (n 305) | +2 [-83, +56] (n 305) | -78 [-164, +2] (n 305) | -6 [-72, +99] (n 292) | +40 [-45, +139] (n 278) | -128 [-220, +7] (n 247) | +43 [-92, +154] (n 213) |
| whole, bottom decile, +30 min | -133 [-198, -60] (n 305) | -61 [-178, +28] (n 305) | -22 [-134, +38] (n 303) | +44 [-16, +112] (n 304) | +29 [-14, +82] (n 299) | +31 [-30, +88] (n 300) | +119 [+79, +180] (n 292) | +109 [+42, +146] (n 276) | +62 [+17, +128] (n 247) | +82 [+50, +182] (n 208) |
| whole, top decile, to 20:00 | +50 [-174, +215] (n 306) | +61 [-107, +229] (n 306) | +42 [-105, +205] (n 306) | -53 [-201, +104] (n 306) | -24 [-163, +136] (n 306) | -207 [-495, -40] (n 306) | -12 [-249, +145] (n 293) | +94 [-165, +216] (n 278) | -29 [-303, +196] (n 249) | -270 [-600, +44] (n 213) |
| whole, bottom decile, to 20:00 | -140 [-215, +2] (n 306) | -93 [-221, +75] (n 306) | +0 [-142, +85] (n 306) | +79 [-36, +186] (n 305) | +146 [+46, +242] (n 304) | +170 [+67, +269] (n 305) | +275 [+168, +382] (n 293) | +193 [+78, +312] (n 278) | +229 [+89, +372] (n 249) | +404 [+329, +508] (n 213) |

M3 permutation importance, remaining label, top three inputs by share (mean of three folds; the whole label is on the chart):

| decision time | 1st | 2nd | 3rd |
|---|---|---|---|
| τ | `log10_runup_shares` 0.14 | `runup_max_drawdown_s` 0.11 | `log10_turnover` 0.11 |
| τ+1m | `tod_h` 0.07 | `log10_runup_shares` 0.07 | `log10_turnover` 0.06 |
| τ+2m | `high_log` 0.07 | `tod_h` 0.07 | `last_form` 0.07 |
| τ+5m | `tod_h` 0.08 | `ret_log` 0.05 | `high_log` 0.05 |
| τ+10m | `accel_post` 0.14 | `log10_turnover` 0.12 | `log10_runup_shares` 0.08 |
| τ+20m | `log10_runup_shares` 0.09 | `lr_dollar_rate` 0.08 | `log10_turnover` 0.06 |
| vol 0.25× | `log10_runup_shares` 0.10 | `accel_k3` 0.09 | `log10_turnover` 0.06 |
| vol 0.5× | `log10_runup_shares` 0.17 | `ret_log` 0.09 | `rv_post` 0.05 |
| vol 1× | `asinh_z_dd` 0.08 | `flow_share_rest_k0` 0.08 | `asinh_z_ret` 0.06 |
| vol 2× | `tod_h` 0.09 | `log1p_max_gap_s` 0.07 | `flow_share_60_k0` 0.06 |

### 4.2 burst

Labelled primary test events of the type at each decision time (three folds summed) — remaining: τ 113, τ+1m 103, τ+2m 113, τ+5m 114, τ+10m 93, τ+20m 106, vol 0.25× 104, vol 0.5× 110, vol 1× 94, vol 2× 105; whole: τ 113, τ+1m 113, τ+2m 113, τ+5m 113, τ+10m 113, τ+20m 113, vol 0.25× 113, vol 0.5× 112, vol 1× 112, vol 2× 109.

| model — label | τ | τ+1m | τ+2m | τ+5m | τ+10m | τ+20m | vol 0.25× | vol 0.5× | vol 1× | vol 2× |
|---|---|---|---|---|---|---|---|---|---|---|
| M1 (τ only) | 0.673 (0.65–0.69) | – | – | – | – | – | – | – | – | – |
| M2 — remaining | 0.653 (0.63–0.68) | 0.623 (0.51–0.71) | 0.644 (0.58–0.74) | 0.656 (0.58–0.75) | 0.624 (0.57–0.71) | 0.630 (0.51–0.72) | 0.672 (0.59–0.82) | 0.646 (0.59–0.74) | 0.637 (0.51–0.75) | 0.642 (0.53–0.71) |
| M2 — whole | 0.653 (0.63–0.68) | 0.667 (0.65–0.68) | 0.683 (0.63–0.72) | 0.735 (0.67–0.80) | 0.763 (0.69–0.84) | 0.810 (0.72–0.90) | 0.706 (0.67–0.72) | 0.699 (0.66–0.74) | 0.719 (0.65–0.76) | 0.733 (0.67–0.78) |
| M3 — remaining | 0.667 (0.64–0.69) | 0.647 (0.57–0.69) | 0.639 (0.57–0.68) | 0.626 (0.58–0.68) | 0.651 (0.59–0.70) | 0.678 (0.64–0.72) | 0.683 (0.61–0.80) | 0.670 (0.63–0.74) | 0.635 (0.50–0.75) | 0.652 (0.64–0.67) |
| M3 — whole | 0.667 (0.64–0.69) | 0.679 (0.63–0.73) | 0.701 (0.61–0.77) | 0.747 (0.64–0.82) | 0.788 (0.71–0.86) | 0.817 (0.71–0.90) | 0.734 (0.69–0.76) | 0.711 (0.65–0.74) | 0.735 (0.62–0.80) | 0.757 (0.71–0.79) |
| M4 — remaining | – | 0.515 (0.49–0.54) | 0.533 (0.51–0.55) | 0.521 (0.49–0.54) | 0.508 (0.46–0.53) | 0.519 (0.44–0.56) | 0.480 (0.43–0.51) | 0.565 (0.50–0.62) | 0.507 (0.47–0.56) | 0.534 (0.51–0.56) |
| M4 — whole | – | 0.579 (0.51–0.65) | 0.587 (0.57–0.60) | 0.651 (0.61–0.68) | 0.711 (0.65–0.77) | 0.775 (0.69–0.85) | 0.638 (0.59–0.69) | 0.634 (0.58–0.70) | 0.622 (0.56–0.69) | 0.664 (0.63–0.68) |

Top-10% lift (mean of the readable folds, primary):

| model — label | τ | τ+1m | τ+2m | τ+5m | τ+10m | τ+20m | vol 0.25× | vol 0.5× | vol 1× | vol 2× |
|---|---|---|---|---|---|---|---|---|---|---|
| M2 — remaining | 2.65 | 2.56 | 3.01 | 2.83 | 2.51 | 2.81 | 2.69 | 2.26 | 2.79 | 2.41 |
| M2 — whole | 2.65 | 2.87 | 3.11 | 3.93 | 4.16 | 5.08 | 2.79 | 2.36 | 3.14 | 3.00 |
| M3 — remaining | 2.78 | 2.09 | 2.35 | 2.02 | 3.05 | 2.39 | 2.77 | 2.49 | 2.51 | 2.70 |
| M3 — whole | 2.78 | 3.22 | 2.88 | 3.65 | 4.52 | 4.88 | 3.17 | 2.79 | 2.68 | 3.38 |

Decile minus all, median net bp (M3, next-print entry):

| label, set, horizon | τ | τ+1m | τ+2m | τ+5m | τ+10m | τ+20m | vol 0.25× | vol 0.5× | vol 1× | vol 2× |
|---|---|---|---|---|---|---|---|---|---|---|
| remaining, top decile, +30 min | +274 [+116, +484] (n 306) | +179 [+11, +303] (n 305) | +163 [+51, +274] (n 305) | +104 [-14, +183] (n 305) | +93 [-10, +157] (n 303) | +51 [-1, +108] (n 303) | +349 [+135, +613] (n 292) | +314 [+94, +674] (n 276) | +219 [+80, +367] (n 247) | +286 [+88, +499] (n 213) |
| remaining, bottom decile, +30 min | +34 [-44, +102] (n 304) | -122 [-196, -49] (n 304) | +17 [-97, +105] (n 303) | -69 [-181, +36] (n 305) | -8 [-105, +57] (n 304) | -78 [-189, +32] (n 303) | -33 [-101, +75] (n 291) | -9 [-140, +116] (n 276) | -20 [-137, +71] (n 246) | -68 [-138, +69] (n 212) |
| remaining, top decile, to 20:00 | +90 [-138, +484] (n 306) | +44 [-165, +202] (n 305) | +13 [-247, +244] (n 305) | +211 [+12, +427] (n 305) | +338 [+212, +534] (n 305) | +255 [+125, +434] (n 304) | +183 [-5, +360] (n 293) | +165 [-29, +333] (n 276) | +245 [+91, +605] (n 248) | +566 [+256, +787] (n 213) |
| remaining, bottom decile, to 20:00 | -97 [-259, +104] (n 306) | -203 [-400, -23] (n 305) | -114 [-347, +76] (n 305) | -209 [-400, -7] (n 305) | -61 [-182, +125] (n 305) | -156 [-239, -15] (n 304) | +62 [-46, +188] (n 293) | -50 [-212, +129] (n 276) | -112 [-328, +24] (n 248) | -117 [-381, +113] (n 213) |
| whole, top decile, +30 min | +274 [+109, +476] (n 306) | +315 [+136, +597] (n 306) | -79 [-291, +141] (n 306) | -148 [-341, +64] (n 306) | -220 [-455, -14] (n 304) | -244 [-468, -80] (n 302) | +275 [+9, +551] (n 291) | +130 [-183, +351] (n 277) | +100 [-164, +246] (n 249) | -156 [-472, +80] (n 213) |
| whole, bottom decile, +30 min | +34 [-37, +96] (n 304) | +26 [-25, +90] (n 305) | +16 [-87, +68] (n 305) | +48 [-0, +107] (n 305) | +70 [-1, +102] (n 304) | +58 [+4, +106] (n 304) | +85 [+31, +154] (n 293) | +122 [+53, +147] (n 278) | +71 [+25, +129] (n 248) | +80 [+51, +167] (n 208) |
| whole, top decile, to 20:00 | +90 [-142, +409] (n 306) | -191 [-445, +77] (n 306) | -889 [-1173, -593] (n 306) | -1019 [-1289, -679] (n 306) | -1421 [-1812, -1185] (n 306) | -1590 [-2054, -1210] (n 305) | -142 [-373, +34] (n 292) | -587 [-751, -278] (n 278) | -257 [-713, -31] (n 249) | -946 [-1269, -508] (n 213) |
| whole, bottom decile, to 20:00 | -97 [-243, +78] (n 306) | +85 [-74, +217] (n 306) | +20 [-103, +115] (n 306) | +156 [+27, +263] (n 306) | +114 [+24, +263] (n 306) | +170 [+45, +232] (n 306) | +203 [+84, +283] (n 293) | +182 [+83, +272] (n 278) | +255 [+155, +357] (n 249) | +345 [+258, +449] (n 213) |

M3 permutation importance, remaining label, top three inputs by share (mean of three folds; the whole label is on the chart):

| decision time | 1st | 2nd | 3rd |
|---|---|---|---|
| τ | `tod_h` 0.18 | `accel_k0` 0.12 | `log10_pre_trades_per_min` 0.09 |
| τ+1m | `tod_h` 0.13 | `log10_post_dollars_per_min` 0.10 | `accel_k0` 0.07 |
| τ+2m | `tod_h` 0.12 | `log10_post_dollars_per_min` 0.10 | `log10_turnover` 0.08 |
| τ+5m | `tod_h` 0.17 | `log10_pre_dollars_per_min` 0.09 | `accel_k0` 0.05 |
| τ+10m | `tod_h` 0.21 | `log1p_since_last_print_s` 0.09 | `log10_shares_outstanding` 0.05 |
| τ+20m | `tod_h` 0.15 | `log10_post_dollars_per_min` 0.07 | `log10_runup_shares` 0.05 |
| vol 0.25× | `tod_h` 0.22 | `log10_pre_trades_per_min` 0.10 | `log10_turnover` 0.09 |
| vol 0.5× | `tod_h` 0.12 | `short_interest_share` 0.07 | `flow_share_rest_k0` 0.07 |
| vol 1× | `tod_h` 0.12 | `log10_runup_shares` 0.11 | `dist_runaway` 0.08 |
| vol 2× | `tod_h` 0.17 | `log10_pre_trades_per_min` 0.09 | `log10_turnover` 0.06 |

### 4.3 slow climb

Labelled primary test events of the type at each decision time (three folds summed) — remaining: τ 128, τ+1m 128, τ+2m 129, τ+5m 146, τ+10m 163, τ+20m 162, vol 0.25× 137, vol 0.5× 120, vol 1× 108, vol 2× 105; whole: τ 128, τ+1m 128, τ+2m 128, τ+5m 128, τ+10m 128, τ+20m 128, vol 0.25× 125, vol 0.5× 122, vol 1× 121, vol 2× 114.

| model — label | τ | τ+1m | τ+2m | τ+5m | τ+10m | τ+20m | vol 0.25× | vol 0.5× | vol 1× | vol 2× |
|---|---|---|---|---|---|---|---|---|---|---|
| M1 (τ only) | 0.572 (0.56–0.59) | – | – | – | – | – | – | – | – | – |
| M2 — remaining | 0.546 (0.48–0.61) | 0.529 (0.51–0.56) | 0.525 (0.47–0.57) | 0.548 (0.51–0.62) | 0.545 (0.51–0.60) | 0.593 (0.56–0.61) | 0.533 (0.49–0.59) | 0.509 (0.50–0.52) | 0.516 (0.48–0.54) | 0.504 (0.49–0.51) |
| M2 — whole | 0.546 (0.48–0.61) | 0.596 (0.57–0.65) | 0.599 (0.55–0.66) | 0.593 (0.55–0.65) | 0.631 (0.58–0.70) | 0.695 (0.63–0.81) | 0.626 (0.58–0.69) | 0.620 (0.58–0.70) | 0.664 (0.63–0.72) | 0.697 (0.67–0.75) |
| M3 — remaining | 0.542 (0.50–0.57) | 0.525 (0.48–0.56) | 0.545 (0.48–0.60) | 0.541 (0.51–0.58) | 0.560 (0.49–0.64) | 0.607 (0.53–0.66) | 0.517 (0.51–0.52) | 0.513 (0.40–0.58) | 0.506 (0.44–0.61) | 0.494 (0.38–0.58) |
| M3 — whole | 0.542 (0.50–0.57) | 0.609 (0.60–0.62) | 0.613 (0.58–0.66) | 0.601 (0.56–0.64) | 0.638 (0.62–0.66) | 0.711 (0.67–0.76) | 0.629 (0.57–0.70) | 0.614 (0.59–0.64) | 0.661 (0.63–0.69) | 0.700 (0.65–0.78) |
| M4 — remaining | – | 0.509 (0.49–0.52) | 0.544 (0.52–0.58) | 0.539 (0.46–0.60) | 0.508 (0.46–0.54) | 0.548 (0.48–0.64) | 0.509 (0.48–0.53) | 0.497 (0.48–0.51) | 0.535 (0.52–0.55) | 0.468 (0.43–0.49) |
| M4 — whole | – | 0.580 (0.55–0.61) | 0.565 (0.52–0.64) | 0.606 (0.58–0.62) | 0.616 (0.58–0.65) | 0.675 (0.64–0.74) | 0.589 (0.55–0.62) | 0.618 (0.60–0.65) | 0.683 (0.64–0.73) | 0.699 (0.67–0.72) |

Top-10% lift (mean of the readable folds, primary):

| model — label | τ | τ+1m | τ+2m | τ+5m | τ+10m | τ+20m | vol 0.25× | vol 0.5× | vol 1× | vol 2× |
|---|---|---|---|---|---|---|---|---|---|---|
| M2 — remaining | 1.60 | 0.93 | 1.29 | 1.23 | 1.35 | 1.66 | 1.11 | 1.25 | 0.98 | 0.94 |
| M2 — whole | 1.60 | 1.36 | 1.51 | 1.61 | 2.46 | 2.97 | 1.58 | 1.94 | 2.27 | 2.86 |
| M3 — remaining | 1.30 | 1.10 | 1.43 | 1.24 | 1.39 | 1.44 | 1.10 | 1.04 | 0.88 | 1.11 |
| M3 — whole | 1.30 | 1.88 | 1.78 | 1.78 | 2.15 | 2.69 | 1.50 | 1.78 | 2.61 | 2.45 |

Decile minus all, median net bp (M3, next-print entry):

| label, set, horizon | τ | τ+1m | τ+2m | τ+5m | τ+10m | τ+20m | vol 0.25× | vol 0.5× | vol 1× | vol 2× |
|---|---|---|---|---|---|---|---|---|---|---|
| remaining, top decile, +30 min | -5 [-126, +135] (n 305) | -27 [-129, +43] (n 305) | +100 [+15, +160] (n 304) | +108 [+28, +163] (n 304) | +62 [+4, +103] (n 305) | +8 [-43, +53] (n 304) | +89 [+13, +183] (n 292) | +107 [+11, +155] (n 275) | +90 [-9, +158] (n 246) | +97 [+18, +219] (n 213) |
| remaining, bottom decile, +30 min | -66 [-174, +42] (n 302) | -26 [-108, +48] (n 298) | -57 [-116, +23] (n 301) | -127 [-221, -47] (n 303) | -71 [-215, +2] (n 300) | +13 [-91, +64] (n 294) | -86 [-154, +58] (n 293) | -14 [-165, +83] (n 274) | -21 [-138, +91] (n 246) | +3 [-107, +57] (n 211) |
| remaining, top decile, to 20:00 | +94 [-95, +265] (n 306) | +46 [-157, +183] (n 305) | +148 [-38, +275] (n 305) | +196 [+58, +309] (n 305) | +222 [+54, +357] (n 305) | +184 [+45, +289] (n 304) | +177 [+24, +284] (n 293) | +190 [-14, +308] (n 276) | +216 [-60, +356] (n 248) | +199 [-81, +382] (n 213) |
| remaining, bottom decile, to 20:00 | +15 [-155, +169] (n 306) | -50 [-199, +167] (n 305) | -25 [-192, +210] (n 305) | -174 [-312, +7] (n 305) | -84 [-260, +76] (n 305) | +77 [-91, +185] (n 304) | -47 [-203, +178] (n 293) | -122 [-268, +95] (n 276) | -28 [-211, +132] (n 248) | +4 [-234, +291] (n 213) |
| whole, top decile, +30 min | -5 [-127, +147] (n 305) | -113 [-242, +43] (n 306) | -71 [-184, +97] (n 306) | -17 [-233, +105] (n 306) | -62 [-167, +34] (n 306) | -147 [-242, -48] (n 306) | +10 [-93, +99] (n 293) | -50 [-189, +47] (n 278) | -168 [-289, -23] (n 249) | -125 [-295, -12] (n 213) |
| whole, bottom decile, +30 min | -66 [-184, +50] (n 302) | +10 [-73, +80] (n 299) | +44 [-36, +145] (n 297) | +57 [-3, +127] (n 301) | +37 [-6, +98] (n 299) | +51 [+18, +97] (n 295) | +119 [+70, +159] (n 291) | +123 [+49, +150] (n 278) | +110 [+79, +157] (n 246) | +80 [+43, +153] (n 208) |
| whole, top decile, to 20:00 | +94 [-94, +249] (n 306) | -315 [-485, -101] (n 306) | -401 [-660, -204] (n 306) | -431 [-636, -233] (n 306) | -442 [-671, -186] (n 306) | -579 [-860, -421] (n 306) | -119 [-334, +65] (n 293) | -164 [-356, +88] (n 278) | -226 [-487, -29] (n 249) | -410 [-692, -253] (n 213) |
| whole, bottom decile, to 20:00 | +15 [-112, +196] (n 306) | +111 [-3, +315] (n 306) | +160 [+35, +334] (n 306) | +110 [+13, +239] (n 306) | +228 [+130, +356] (n 305) | +244 [+126, +344] (n 304) | +319 [+248, +386] (n 292) | +202 [+101, +320] (n 278) | +315 [+235, +435] (n 248) | +397 [+273, +501] (n 213) |

M3 permutation importance, remaining label, top three inputs by share (mean of three folds; the whole label is on the chart):

| decision time | 1st | 2nd | 3rd |
|---|---|---|---|
| τ | `tod_h` 0.13 | `runup_height_s` 0.08 | `accel_k3` 0.05 |
| τ+1m | `short_interest_share` 0.13 | `log10_post_dollars_per_min` 0.06 | `runup_max_drawdown_s` 0.05 |
| τ+2m | `ret_log` 0.05 | `log10_shares_outstanding` 0.05 | `last_form` 0.05 |
| τ+5m | `short_interest_share` 0.06 | `runup_u_launch` 0.06 | `log10_shares_outstanding` 0.05 |
| τ+10m | `tod_h` 0.10 | `log1p_max_gap_s` 0.06 | `lr_dollar_rate` 0.05 |
| τ+20m | `tod_h` 0.11 | `short_interest_share` 0.09 | `log10_shares_outstanding` 0.07 |
| vol 0.25× | `short_interest_share` 0.08 | `accel_k1` 0.06 | `high_log` 0.05 |
| vol 0.5× | `short_interest_share` 0.09 | `asinh_z_high` 0.08 | `log10_shares_outstanding` 0.07 |
| vol 1× | `log10_post_dollars_per_min` 0.06 | `tod_h` 0.04 | `elapsed_min` 0.03 |
| vol 2× | `tod_h` 0.04 | `log10_post_trades_per_min` 0.04 | `high_log` 0.04 |

### 4.4 exhausted

Labelled primary test events of the type at each decision time (three folds summed) — remaining: τ 533, τ+1m 546, τ+2m 525, τ+5m 520, τ+10m 579, τ+20m 525, vol 0.25× 477, vol 0.5× 464, vol 1× 417, vol 2× 360; whole: τ 533, τ+1m 533, τ+2m 533, τ+5m 533, τ+10m 533, τ+20m 533, vol 0.25× 489, vol 0.5× 447, vol 1× 373, vol 2× 282.

| model — label | τ | τ+1m | τ+2m | τ+5m | τ+10m | τ+20m | vol 0.25× | vol 0.5× | vol 1× | vol 2× |
|---|---|---|---|---|---|---|---|---|---|---|
| M1 (τ only) | 0.592 (0.57–0.63) | – | – | – | – | – | – | – | – | – |
| M2 — remaining | 0.607 (0.59–0.63) | 0.604 (0.59–0.62) | 0.606 (0.58–0.62) | 0.629 (0.60–0.65) | 0.617 (0.61–0.63) | 0.582 (0.57–0.60) | 0.618 (0.60–0.64) | 0.583 (0.57–0.60) | 0.586 (0.57–0.60) | 0.610 (0.60–0.64) |
| M2 — whole | 0.607 (0.59–0.63) | 0.699 (0.67–0.72) | 0.732 (0.72–0.74) | 0.770 (0.77–0.77) | 0.805 (0.80–0.81) | 0.830 (0.82–0.83) | 0.776 (0.77–0.79) | 0.805 (0.80–0.81) | 0.813 (0.81–0.82) | 0.816 (0.80–0.84) |
| M3 — remaining | 0.607 (0.59–0.63) | 0.622 (0.61–0.63) | 0.615 (0.59–0.64) | 0.631 (0.61–0.65) | 0.613 (0.60–0.62) | 0.596 (0.59–0.61) | 0.603 (0.59–0.61) | 0.579 (0.55–0.60) | 0.590 (0.57–0.61) | 0.609 (0.59–0.63) |
| M3 — whole | 0.607 (0.59–0.63) | 0.720 (0.70–0.75) | 0.750 (0.74–0.77) | 0.793 (0.79–0.79) | 0.835 (0.83–0.84) | 0.862 (0.85–0.87) | 0.790 (0.78–0.79) | 0.842 (0.83–0.85) | 0.857 (0.85–0.86) | 0.860 (0.84–0.87) |
| M4 — remaining | – | 0.518 (0.50–0.53) | 0.544 (0.54–0.56) | 0.569 (0.54–0.59) | 0.536 (0.53–0.55) | 0.552 (0.53–0.58) | 0.491 (0.46–0.52) | 0.487 (0.47–0.51) | 0.491 (0.46–0.53) | 0.522 (0.50–0.56) |
| M4 — whole | – | 0.663 (0.63–0.68) | 0.697 (0.69–0.70) | 0.732 (0.73–0.73) | 0.770 (0.76–0.77) | 0.788 (0.78–0.79) | 0.743 (0.73–0.76) | 0.773 (0.76–0.79) | 0.786 (0.78–0.80) | 0.786 (0.78–0.80) |

Top-10% lift (mean of the readable folds, primary):

| model — label | τ | τ+1m | τ+2m | τ+5m | τ+10m | τ+20m | vol 0.25× | vol 0.5× | vol 1× | vol 2× |
|---|---|---|---|---|---|---|---|---|---|---|
| M2 — remaining | 1.79 | 1.72 | 1.63 | 1.80 | 1.46 | 1.65 | 1.44 | 1.52 | 1.57 | 1.56 |
| M2 — whole | 1.79 | 2.41 | 2.60 | 2.96 | 3.12 | 3.51 | 3.12 | 3.54 | 3.59 | 3.66 |
| M3 — remaining | 1.85 | 1.70 | 1.70 | 1.74 | 1.44 | 1.49 | 1.54 | 1.46 | 1.42 | 1.82 |
| M3 — whole | 1.85 | 2.63 | 2.90 | 3.36 | 3.48 | 3.76 | 3.24 | 3.84 | 4.23 | 4.58 |

Decile minus all, median net bp (M3, next-print entry):

| label, set, horizon | τ | τ+1m | τ+2m | τ+5m | τ+10m | τ+20m | vol 0.25× | vol 0.5× | vol 1× | vol 2× |
|---|---|---|---|---|---|---|---|---|---|---|
| remaining, top decile, +30 min | -128 [-237, -8] (n 302) | -125 [-259, -14] (n 299) | -114 [-294, +26] (n 299) | -174 [-295, -34] (n 301) | -183 [-321, -33] (n 298) | -208 [-292, -119] (n 298) | -142 [-246, -42] (n 290) | -163 [-315, +58] (n 274) | -140 [-303, -45] (n 246) | -116 [-303, +30] (n 210) |
| remaining, bottom decile, +30 min | +348 [+176, +565] (n 306) | +285 [+165, +438] (n 304) | +269 [+154, +394] (n 305) | +171 [+101, +262] (n 305) | +126 [+38, +213] (n 305) | +61 [+27, +124] (n 304) | +271 [+117, +440] (n 291) | +212 [+121, +364] (n 275) | +143 [+55, +289] (n 246) | +355 [+194, +530] (n 212) |
| remaining, top decile, to 20:00 | -171 [-279, +37] (n 306) | -263 [-430, -112] (n 305) | -431 [-649, -244] (n 305) | -821 [-1282, -517] (n 305) | -425 [-757, -155] (n 305) | -581 [-914, -335] (n 304) | -152 [-307, +37] (n 293) | -308 [-551, -97] (n 276) | -198 [-569, -31] (n 248) | -804 [-1123, -398] (n 213) |
| remaining, bottom decile, to 20:00 | +109 [-75, +274] (n 306) | +341 [+163, +579] (n 305) | +457 [+253, +728] (n 305) | +551 [+319, +741] (n 305) | +574 [+332, +843] (n 305) | +367 [+218, +581] (n 304) | +273 [+30, +433] (n 293) | +253 [+26, +537] (n 276) | +462 [+330, +745] (n 248) | +509 [+278, +927] (n 213) |
| whole, top decile, +30 min | -128 [-231, -2] (n 302) | -35 [-113, +41] (n 298) | +33 [-60, +86] (n 300) | +48 [-33, +119] (n 299) | +72 [+19, +109] (n 297) | +51 [-12, +107] (n 295) | +119 [+72, +170] (n 291) | +98 [+29, +146] (n 278) | +106 [+32, +133] (n 244) | +86 [+57, +171] (n 208) |
| whole, bottom decile, +30 min | +348 [+182, +564] (n 306) | -125 [-285, +62] (n 306) | -410 [-574, -246] (n 306) | -412 [-653, -310] (n 306) | -346 [-540, -128] (n 306) | -376 [-499, -155] (n 306) | -147 [-260, -79] (n 292) | -237 [-337, -141] (n 278) | -213 [-327, -31] (n 248) | -172 [-321, -10] (n 213) |
| whole, top decile, to 20:00 | -171 [-287, +21] (n 306) | +38 [-126, +158] (n 306) | +88 [-30, +255] (n 305) | +114 [+21, +233] (n 305) | +197 [+117, +272] (n 304) | +178 [+107, +268] (n 304) | +293 [+215, +372] (n 292) | +257 [+131, +345] (n 278) | +312 [+215, +423] (n 249) | +420 [+312, +545] (n 213) |
| whole, bottom decile, to 20:00 | +109 [-82, +297] (n 306) | -736 [-963, -573] (n 306) | -871 [-1141, -561] (n 306) | -1215 [-1419, -842] (n 306) | -1278 [-1552, -953] (n 306) | -1009 [-1450, -673] (n 306) | -205 [-334, -68] (n 293) | -132 [-354, -4] (n 278) | -175 [-321, -17] (n 249) | -380 [-714, -168] (n 213) |

M3 permutation importance, remaining label, top three inputs by share (mean of three folds; the whole label is on the chart):

| decision time | 1st | 2nd | 3rd |
|---|---|---|---|
| τ | `tod_h` 0.38 | `log10_pre_trades_per_min` 0.14 | `last_form` 0.06 |
| τ+1m | `tod_h` 0.35 | `ret_log` 0.10 | `log10_turnover` 0.09 |
| τ+2m | `tod_h` 0.32 | `ret_log` 0.13 | `last_form` 0.05 |
| τ+5m | `tod_h` 0.26 | `ret_log` 0.22 | `runup_height_s` 0.05 |
| τ+10m | `ret_log` 0.24 | `tod_h` 0.22 | `asinh_z_high` 0.04 |
| τ+20m | `ret_log` 0.26 | `tod_h` 0.25 | `asinh_z_ret` 0.04 |
| vol 0.25× | `tod_h` 0.32 | `asinh_z_high` 0.07 | `log10_turnover` 0.05 |
| vol 0.5× | `tod_h` 0.32 | `log1p_max_gap_s` 0.07 | `accel_post` 0.04 |
| vol 1× | `tod_h` 0.41 | `u_high` 0.04 | `asinh_z_ret` 0.03 |
| vol 2× | `ret_log` 0.20 | `tod_h` 0.16 | `vol_progress` 0.07 |

### 4.5 fade

Labelled primary test events of the type at each decision time (three folds summed) — remaining: τ 386, τ+1m 361, τ+2m 368, τ+5m 345, τ+10m 335, τ+20m 317, vol 0.25× 342, vol 0.5× 311, vol 1× 309, vol 2× 274; whole: τ 386, τ+1m 386, τ+2m 386, τ+5m 386, τ+10m 386, τ+20m 386, vol 0.25× 379, vol 0.5× 364, vol 1× 333, vol 2× 276.

| model — label | τ | τ+1m | τ+2m | τ+5m | τ+10m | τ+20m | vol 0.25× | vol 0.5× | vol 1× | vol 2× |
|---|---|---|---|---|---|---|---|---|---|---|
| M1 (τ only) | 0.546 (0.54–0.55) | – | – | – | – | – | – | – | – | – |
| M2 — remaining | 0.552 (0.55–0.56) | 0.602 (0.59–0.61) | 0.594 (0.55–0.64) | 0.627 (0.59–0.67) | 0.629 (0.57–0.66) | 0.639 (0.62–0.66) | 0.593 (0.54–0.62) | 0.625 (0.57–0.67) | 0.587 (0.51–0.63) | 0.579 (0.52–0.63) |
| M2 — whole | 0.552 (0.55–0.56) | 0.613 (0.60–0.62) | 0.614 (0.61–0.63) | 0.628 (0.61–0.65) | 0.651 (0.63–0.69) | 0.661 (0.64–0.68) | 0.614 (0.60–0.63) | 0.621 (0.61–0.63) | 0.646 (0.62–0.66) | 0.636 (0.62–0.65) |
| M3 — remaining | 0.564 (0.55–0.59) | 0.588 (0.57–0.61) | 0.600 (0.57–0.62) | 0.618 (0.59–0.64) | 0.639 (0.61–0.66) | 0.649 (0.63–0.68) | 0.608 (0.57–0.63) | 0.633 (0.60–0.66) | 0.593 (0.56–0.61) | 0.590 (0.54–0.64) |
| M3 — whole | 0.564 (0.55–0.59) | 0.626 (0.61–0.65) | 0.642 (0.62–0.66) | 0.655 (0.63–0.67) | 0.675 (0.65–0.70) | 0.686 (0.67–0.71) | 0.641 (0.62–0.66) | 0.642 (0.62–0.66) | 0.678 (0.67–0.69) | 0.676 (0.66–0.71) |
| M4 — remaining | – | 0.570 (0.54–0.59) | 0.547 (0.53–0.56) | 0.574 (0.55–0.61) | 0.566 (0.52–0.60) | 0.554 (0.50–0.61) | 0.557 (0.53–0.59) | 0.589 (0.56–0.61) | 0.565 (0.51–0.62) | 0.521 (0.50–0.54) |
| M4 — whole | – | 0.592 (0.56–0.61) | 0.591 (0.56–0.61) | 0.593 (0.56–0.63) | 0.602 (0.56–0.65) | 0.631 (0.62–0.64) | 0.588 (0.56–0.62) | 0.612 (0.58–0.65) | 0.616 (0.56–0.70) | 0.613 (0.60–0.63) |

Top-10% lift (mean of the readable folds, primary):

| model — label | τ | τ+1m | τ+2m | τ+5m | τ+10m | τ+20m | vol 0.25× | vol 0.5× | vol 1× | vol 2× |
|---|---|---|---|---|---|---|---|---|---|---|
| M2 — remaining | 1.19 | 1.75 | 1.83 | 1.79 | 1.72 | 2.20 | 1.82 | 1.90 | 1.60 | 1.57 |
| M2 — whole | 1.19 | 1.76 | 1.81 | 1.50 | 2.00 | 2.62 | 1.93 | 1.88 | 2.09 | 2.04 |
| M3 — remaining | 1.52 | 1.58 | 1.46 | 1.67 | 1.92 | 2.08 | 1.78 | 1.65 | 1.38 | 1.83 |
| M3 — whole | 1.52 | 1.88 | 2.32 | 2.02 | 2.43 | 2.58 | 1.84 | 2.03 | 2.05 | 2.29 |

Decile minus all, median net bp (M3, next-print entry):

| label, set, horizon | τ | τ+1m | τ+2m | τ+5m | τ+10m | τ+20m | vol 0.25× | vol 0.5× | vol 1× | vol 2× |
|---|---|---|---|---|---|---|---|---|---|---|
| remaining, top decile, +30 min | -244 [-401, -116] (n 306) | -144 [-262, +13] (n 305) | -355 [-479, -187] (n 305) | -396 [-521, -147] (n 305) | -315 [-527, -132] (n 305) | -86 [-244, +55] (n 303) | -322 [-458, -185] (n 293) | -376 [-579, -169] (n 276) | -382 [-628, -135] (n 248) | -459 [-650, -187] (n 213) |
| remaining, bottom decile, +30 min | -42 [-182, +83] (n 303) | +2 [-77, +69] (n 299) | +66 [+5, +135] (n 299) | +74 [-2, +135] (n 297) | +93 [+67, +132] (n 296) | +51 [+17, +82] (n 290) | +99 [+44, +150] (n 290) | +91 [+19, +134] (n 275) | +59 [-1, +122] (n 244) | +80 [+44, +137] (n 211) |
| remaining, top decile, to 20:00 | -227 [-410, -66] (n 306) | -437 [-658, -238] (n 305) | -681 [-914, -423] (n 305) | -736 [-950, -373] (n 305) | -1011 [-1306, -704] (n 305) | -990 [-1403, -727] (n 304) | -658 [-839, -481] (n 293) | -819 [-1076, -609] (n 276) | -722 [-964, -428] (n 248) | -789 [-1049, -595] (n 213) |
| remaining, bottom decile, to 20:00 | +16 [-185, +257] (n 306) | +203 [+11, +348] (n 305) | +129 [+7, +289] (n 305) | +270 [+141, +340] (n 305) | +242 [+178, +339] (n 305) | +215 [+130, +312] (n 304) | +273 [+150, +366] (n 293) | +224 [+120, +308] (n 276) | +280 [+192, +380] (n 248) | +365 [+242, +457] (n 213) |
| whole, top decile, +30 min | -244 [-387, -120] (n 306) | -261 [-423, -113] (n 306) | -525 [-646, -380] (n 306) | -387 [-560, -252] (n 305) | -362 [-467, -168] (n 306) | -95 [-216, +19] (n 305) | -279 [-403, -127] (n 293) | -344 [-481, -177] (n 278) | -181 [-307, -31] (n 249) | -120 [-361, -44] (n 213) |
| whole, bottom decile, +30 min | -42 [-176, +81] (n 303) | +66 [-32, +148] (n 298) | +22 [-41, +92] (n 299) | +62 [-48, +120] (n 298) | +65 [+15, +112] (n 294) | +38 [-36, +64] (n 291) | +101 [+44, +160] (n 286) | +123 [+49, +162] (n 276) | +69 [+21, +124] (n 245) | +107 [+50, +164] (n 208) |
| whole, top decile, to 20:00 | -227 [-397, -64] (n 306) | -544 [-779, -321] (n 306) | -845 [-1034, -657] (n 306) | -594 [-815, -402] (n 306) | -549 [-742, -399] (n 306) | -337 [-478, -209] (n 306) | -571 [-819, -439] (n 293) | -559 [-764, -357] (n 278) | -195 [-414, -11] (n 249) | -380 [-766, -232] (n 213) |
| whole, bottom decile, to 20:00 | +16 [-187, +235] (n 306) | +116 [-96, +300] (n 306) | +8 [-170, +182] (n 306) | +51 [-155, +183] (n 305) | +164 [+60, +247] (n 305) | +170 [+83, +246] (n 304) | +319 [+202, +432] (n 292) | +169 [+29, +299] (n 278) | +278 [+197, +376] (n 249) | +397 [+311, +515] (n 212) |

M3 permutation importance, remaining label, top three inputs by share (mean of three folds; the whole label is on the chart):

| decision time | 1st | 2nd | 3rd |
|---|---|---|---|
| τ | `tod_h` 0.23 | `log10_pre_dollars_per_min` 0.12 | `accel_k1` 0.10 |
| τ+1m | `log10_post_dollars_per_min` 0.11 | `vol_progress` 0.09 | `gap_share` 0.07 |
| τ+2m | `log10_post_trades_per_min` 0.24 | `tod_h` 0.08 | `log10_post_dollars_per_min` 0.07 |
| τ+5m | `log10_post_trades_per_min` 0.12 | `accel_post` 0.08 | `asinh_z_high` 0.07 |
| τ+10m | `log10_runup_minutes` 0.07 | `log10_post_trades_per_min` 0.06 | `log10_post_dollars_per_min` 0.05 |
| τ+20m | `log10_post_trades_per_min` 0.15 | `log1p_since_last_print_s` 0.08 | `tod_h` 0.07 |
| vol 0.25× | `log10_post_dollars_per_min` 0.08 | `gap_share` 0.07 | `accel_k0` 0.06 |
| vol 0.5× | `elapsed_min` 0.12 | `asinh_z_high` 0.08 | `tod_h` 0.07 |
| vol 1× | `elapsed_min` 0.16 | `log10_post_dollars_per_min` 0.07 | `asinh_z_ret` 0.06 |
| vol 2× | `asinh_z_dd` 0.08 | `log10_post_dollars_per_min` 0.07 | `log1p_max_gap_s` 0.07 |

### 4.6 chop

Labelled primary test events of the type at each decision time (three folds summed) — remaining: τ 1,815, τ+1m 1,825, τ+2m 1,827, τ+5m 1,832, τ+10m 1,787, τ+20m 1,842, vol 0.25× 1,782, vol 0.5× 1,678, vol 1× 1,483, vol 2× 1,221; whole: τ 1,815, τ+1m 1,815, τ+2m 1,815, τ+5m 1,815, τ+10m 1,815, τ+20m 1,815, vol 0.25× 1,744, vol 0.5× 1,650, vol 1× 1,479, vol 2× 1,280.

| model — label | τ | τ+1m | τ+2m | τ+5m | τ+10m | τ+20m | vol 0.25× | vol 0.5× | vol 1× | vol 2× |
|---|---|---|---|---|---|---|---|---|---|---|
| M1 (τ only) | 0.523 (0.50–0.54) | – | – | – | – | – | – | – | – | – |
| M2 — remaining | 0.551 (0.54–0.57) | 0.567 (0.54–0.59) | 0.578 (0.56–0.59) | 0.585 (0.56–0.60) | 0.582 (0.57–0.59) | 0.576 (0.56–0.59) | 0.577 (0.55–0.59) | 0.558 (0.53–0.58) | 0.561 (0.55–0.57) | 0.574 (0.55–0.59) |
| M2 — whole | 0.551 (0.54–0.57) | 0.571 (0.56–0.59) | 0.584 (0.57–0.60) | 0.600 (0.57–0.62) | 0.620 (0.61–0.63) | 0.649 (0.63–0.66) | 0.626 (0.62–0.63) | 0.653 (0.65–0.66) | 0.651 (0.63–0.68) | 0.630 (0.60–0.66) |
| M3 — remaining | 0.565 (0.55–0.58) | 0.569 (0.56–0.58) | 0.577 (0.55–0.60) | 0.587 (0.56–0.61) | 0.570 (0.52–0.61) | 0.564 (0.55–0.59) | 0.577 (0.56–0.59) | 0.556 (0.52–0.59) | 0.556 (0.54–0.57) | 0.581 (0.55–0.60) |
| M3 — whole | 0.565 (0.55–0.58) | 0.594 (0.57–0.61) | 0.603 (0.59–0.61) | 0.624 (0.60–0.64) | 0.653 (0.65–0.66) | 0.670 (0.66–0.68) | 0.615 (0.60–0.63) | 0.652 (0.63–0.67) | 0.665 (0.65–0.70) | 0.661 (0.65–0.67) |
| M4 — remaining | – | 0.512 (0.49–0.54) | 0.539 (0.54–0.55) | 0.572 (0.56–0.59) | 0.549 (0.53–0.56) | 0.541 (0.53–0.55) | 0.505 (0.50–0.51) | 0.513 (0.50–0.52) | 0.509 (0.50–0.51) | 0.518 (0.49–0.55) |
| M4 — whole | – | 0.518 (0.50–0.55) | 0.538 (0.52–0.56) | 0.566 (0.56–0.58) | 0.579 (0.57–0.59) | 0.613 (0.60–0.62) | 0.598 (0.58–0.62) | 0.601 (0.59–0.61) | 0.616 (0.60–0.63) | 0.592 (0.57–0.62) |

Top-10% lift (mean of the readable folds, primary):

| model — label | τ | τ+1m | τ+2m | τ+5m | τ+10m | τ+20m | vol 0.25× | vol 0.5× | vol 1× | vol 2× |
|---|---|---|---|---|---|---|---|---|---|---|
| M2 — remaining | 1.14 | 1.12 | 1.14 | 1.17 | 1.20 | 1.17 | 1.19 | 1.09 | 1.15 | 1.18 |
| M2 — whole | 1.14 | 1.20 | 1.19 | 1.16 | 1.23 | 1.28 | 1.30 | 1.33 | 1.32 | 1.26 |
| M3 — remaining | 1.18 | 1.12 | 1.14 | 1.18 | 1.17 | 1.16 | 1.17 | 1.09 | 1.14 | 1.10 |
| M3 — whole | 1.18 | 1.19 | 1.27 | 1.27 | 1.28 | 1.34 | 1.23 | 1.28 | 1.36 | 1.41 |

Decile minus all, median net bp (M3, next-print entry):

| label, set, horizon | τ | τ+1m | τ+2m | τ+5m | τ+10m | τ+20m | vol 0.25× | vol 0.5× | vol 1× | vol 2× |
|---|---|---|---|---|---|---|---|---|---|---|
| remaining, top decile, +30 min | +45 [-34, +164] (n 306) | +63 [-20, +162] (n 305) | +136 [+48, +196] (n 305) | +108 [+30, +171] (n 303) | +93 [+25, +127] (n 303) | +47 [-23, +73] (n 298) | +86 [-2, +136] (n 291) | +81 [+5, +138] (n 275) | +112 [+54, +178] (n 247) | +115 [+61, +174] (n 211) |
| remaining, bottom decile, +30 min | -174 [-336, -100] (n 302) | -198 [-433, +11] (n 303) | -278 [-469, -26] (n 301) | -400 [-562, -268] (n 303) | -418 [-624, -257] (n 303) | -217 [-468, -76] (n 300) | -147 [-347, -32] (n 292) | -341 [-580, -120] (n 274) | -299 [-568, -144] (n 248) | -193 [-421, +54] (n 212) |
| remaining, top decile, to 20:00 | +119 [-8, +264] (n 306) | +382 [+224, +505] (n 305) | +366 [+200, +498] (n 305) | +283 [+126, +444] (n 305) | +342 [+249, +448] (n 305) | +240 [+152, +344] (n 304) | +273 [+142, +368] (n 293) | +236 [+108, +346] (n 276) | +375 [+200, +514] (n 248) | +371 [+148, +514] (n 213) |
| remaining, bottom decile, to 20:00 | -265 [-455, -86] (n 306) | -499 [-854, -309] (n 305) | -838 [-1247, -479] (n 305) | -1244 [-1604, -887] (n 305) | -1550 [-1862, -1133] (n 305) | -1412 [-1885, -808] (n 304) | -430 [-657, -137] (n 293) | -809 [-1019, -531] (n 276) | -817 [-1133, -439] (n 248) | -814 [-1128, -350] (n 213) |
| whole, top decile, +30 min | +45 [-32, +172] (n 306) | +23 [-96, +108] (n 306) | +18 [-77, +104] (n 306) | +17 [-84, +114] (n 306) | +14 [-57, +62] (n 306) | +2 [-69, +52] (n 305) | +22 [-70, +97] (n 291) | +33 [-62, +121] (n 275) | +43 [-22, +90] (n 249) | +10 [-57, +86] (n 210) |
| whole, bottom decile, +30 min | -174 [-316, -86] (n 302) | -70 [-178, +41] (n 300) | -6 [-106, +65] (n 302) | -20 [-92, +71] (n 303) | +28 [-69, +86] (n 301) | -25 [-110, +39] (n 298) | +110 [+44, +158] (n 291) | +76 [+0, +132] (n 278) | +110 [+53, +172] (n 245) | +80 [-6, +129] (n 208) |
| whole, top decile, to 20:00 | +119 [-8, +272] (n 306) | -109 [-226, +140] (n 306) | +23 [-136, +200] (n 306) | +64 [-75, +191] (n 306) | -13 [-196, +105] (n 306) | +154 [+33, +234] (n 305) | +142 [+19, +234] (n 293) | +172 [+6, +284] (n 277) | +113 [-6, +239] (n 249) | +176 [+3, +325] (n 212) |
| whole, bottom decile, to 20:00 | -265 [-443, -86] (n 306) | -69 [-284, +112] (n 306) | +20 [-141, +131] (n 305) | +28 [-167, +136] (n 305) | +75 [-98, +172] (n 304) | +112 [-57, +204] (n 304) | +293 [+212, +387] (n 292) | +149 [+53, +251] (n 278) | +306 [+187, +402] (n 249) | +329 [+220, +464] (n 213) |

M3 permutation importance, remaining label, top three inputs by share (mean of three folds; the whole label is on the chart):

| decision time | 1st | 2nd | 3rd |
|---|---|---|---|
| τ | `tod_h` 0.17 | `log10_pre_trades_per_min` 0.10 | `last_form` 0.09 |
| τ+1m | `tod_h` 0.14 | `ret_log` 0.11 | `last_form` 0.07 |
| τ+2m | `ret_log` 0.17 | `tod_h` 0.08 | `last_form` 0.07 |
| τ+5m | `ret_log` 0.22 | `runup_height_s` 0.07 | `tod_h` 0.06 |
| τ+10m | `ret_log` 0.23 | `runup_height_s` 0.07 | `log10_post_dollars_per_min` 0.04 |
| τ+20m | `ret_log` 0.30 | `accel_k3` 0.07 | `lr_dollar_rate` 0.03 |
| vol 0.25× | `tod_h` 0.13 | `asinh_z_ret` 0.05 | `log10_turnover` 0.05 |
| vol 0.5× | `asinh_z_high` 0.08 | `dist_burst` 0.06 | `last_form` 0.06 |
| vol 1× | `tod_h` 0.07 | `elapsed_min` 0.07 | `ret_log` 0.06 |
| vol 2× | `asinh_z_ret` 0.08 | `vol_progress` 0.06 | `tod_h` 0.06 |

## 5. Pooled tables

Multiclass log-loss skill against M0 on the same test rows (1 − LL / LL_M0), primary read, mean of three folds:

| model — label | τ | τ+1m | τ+2m | τ+5m | τ+10m | τ+20m | vol 0.25× | vol 0.5× | vol 1× | vol 2× |
|---|---|---|---|---|---|---|---|---|---|---|
| M1 (none) — whole | 0.0124 | – | – | – | – | – | – | – | – | – |
| M2 (none) — remaining | -0.0197 | -0.0212 | -0.0162 | -0.0080 | -0.0187 | -0.0078 | -0.0120 | -0.0036 | -0.0214 | -0.0258 |
| M2 (none) — whole | -0.0197 | 0.0057 | 0.0175 | 0.0382 | 0.0639 | 0.0963 | 0.0483 | 0.0604 | 0.0674 | 0.0606 |
| M2 (balanced) — remaining | -0.4509 | -0.4675 | -0.4500 | -0.4333 | -0.4537 | -0.4604 | -0.4557 | -0.4638 | -0.4551 | -0.3953 |
| M2 (balanced) — whole | -0.4509 | -0.4154 | -0.4023 | -0.3764 | -0.3430 | -0.2984 | -0.3605 | -0.3401 | -0.3264 | -0.3305 |
| M3 (none) — remaining | 0.0063 | 0.0094 | 0.0106 | 0.0123 | 0.0128 | 0.0174 | 0.0079 | 0.0013 | -0.0029 | -0.0071 |
| M3 (none) — whole | 0.0063 | 0.0457 | 0.0589 | 0.0874 | 0.1185 | 0.1536 | 0.0808 | 0.1046 | 0.1240 | 0.1224 |
| M3 (balanced) — remaining | -0.1298 | -0.0988 | -0.1174 | -0.1147 | -0.1225 | -0.1266 | -0.1606 | -0.1606 | -0.1577 | -0.1105 |
| M3 (balanced) — whole | -0.1298 | -0.0843 | -0.0713 | -0.0430 | -0.0107 | 0.0369 | -0.0547 | -0.0261 | 0.0091 | 0.0228 |
| M4 (none) — remaining | – | -0.0205 | -0.0194 | -0.0060 | -0.0187 | -0.0126 | -0.0307 | -0.0269 | -0.0357 | -0.0455 |
| M4 (none) — whole | – | 0.0009 | -0.0024 | 0.0161 | 0.0372 | 0.0633 | 0.0358 | 0.0429 | 0.0569 | 0.0576 |
| M4 (balanced) — remaining | – | -0.4867 | -0.4839 | -0.4611 | -0.4683 | -0.5005 | -0.5055 | -0.4878 | -0.4744 | -0.4262 |
| M4 (balanced) — whole | – | -0.4535 | -0.4627 | -0.4407 | -0.4220 | -0.3975 | -0.4065 | -0.3791 | -0.3511 | -0.3519 |

Balanced class weights, primary AUC (mean of the readable folds):

*runaway*

| model — label | τ | τ+1m | τ+2m | τ+5m | τ+10m | τ+20m | vol 0.25× | vol 0.5× | vol 1× | vol 2× |
|---|---|---|---|---|---|---|---|---|---|---|
| M2 — remaining | 0.610 (0.55–0.67) [2/3 read] | 0.613 (0.61–0.62) | 0.618 (0.58–0.66) | 0.621 (0.60–0.64) | 0.654 (0.62–0.69) [2/3 read] | 0.579 (0.54–0.60) | 0.599 (0.60–0.60) [1/3 read] | 0.554 (0.55–0.55) [1/3 read] | 0.639 (0.64–0.64) [1/3 read] | 0.486 (0.49–0.49) [1/3 read] |
| M2 — whole | 0.610 (0.55–0.67) [2/3 read] | 0.625 (0.56–0.69) [2/3 read] | 0.629 (0.59–0.67) [2/3 read] | 0.666 (0.62–0.71) [2/3 read] | 0.651 (0.61–0.69) [2/3 read] | 0.640 (0.63–0.65) [2/3 read] | 0.712 (0.71–0.71) [1/3 read] | 0.731 (0.73–0.73) [1/3 read] | 0.760 (0.76–0.76) [1/3 read] | 0.720 (0.72–0.72) [1/3 read] |
| M3 — remaining | 0.562 (0.51–0.62) [2/3 read] | 0.656 (0.62–0.68) | 0.636 (0.61–0.67) | 0.682 (0.66–0.71) | 0.600 (0.57–0.63) [2/3 read] | 0.584 (0.55–0.62) | 0.606 (0.61–0.61) [1/3 read] | 0.568 (0.57–0.57) [1/3 read] | 0.619 (0.62–0.62) [1/3 read] | 0.626 (0.63–0.63) [1/3 read] |
| M3 — whole | 0.562 (0.51–0.62) [2/3 read] | 0.645 (0.61–0.68) [2/3 read] | 0.649 (0.65–0.65) [2/3 read] | 0.693 (0.63–0.76) [2/3 read] | 0.674 (0.67–0.68) [2/3 read] | 0.667 (0.66–0.68) [2/3 read] | 0.753 (0.75–0.75) [1/3 read] | 0.710 (0.71–0.71) [1/3 read] | 0.732 (0.73–0.73) [1/3 read] | 0.701 (0.70–0.70) [1/3 read] |
| M4 — remaining | – | 0.549 (0.43–0.66) | 0.489 (0.45–0.55) | 0.568 (0.54–0.63) | 0.496 (0.45–0.55) [2/3 read] | 0.494 (0.42–0.54) | 0.508 (0.51–0.51) [1/3 read] | 0.533 (0.53–0.53) [1/3 read] | 0.516 (0.52–0.52) [1/3 read] | 0.557 (0.56–0.56) [1/3 read] |
| M4 — whole | – | 0.503 (0.45–0.56) [2/3 read] | 0.483 (0.45–0.51) [2/3 read] | 0.587 (0.56–0.61) [2/3 read] | 0.634 (0.52–0.74) [2/3 read] | 0.598 (0.50–0.69) [2/3 read] | 0.520 (0.52–0.52) [1/3 read] | 0.618 (0.62–0.62) [1/3 read] | 0.634 (0.63–0.63) [1/3 read] | 0.553 (0.55–0.55) [1/3 read] |

*burst*

| model — label | τ | τ+1m | τ+2m | τ+5m | τ+10m | τ+20m | vol 0.25× | vol 0.5× | vol 1× | vol 2× |
|---|---|---|---|---|---|---|---|---|---|---|
| M2 — remaining | 0.654 (0.62–0.70) | 0.617 (0.53–0.68) | 0.637 (0.57–0.73) | 0.651 (0.55–0.76) | 0.621 (0.56–0.72) | 0.623 (0.49–0.73) | 0.664 (0.59–0.82) | 0.648 (0.58–0.75) | 0.637 (0.51–0.76) | 0.639 (0.53–0.70) |
| M2 — whole | 0.654 (0.62–0.70) | 0.670 (0.65–0.70) | 0.686 (0.64–0.74) | 0.736 (0.67–0.81) | 0.764 (0.69–0.85) | 0.805 (0.72–0.89) | 0.703 (0.67–0.74) | 0.702 (0.66–0.73) | 0.723 (0.67–0.77) | 0.731 (0.67–0.79) |
| M3 — remaining | 0.641 (0.63–0.66) | 0.646 (0.55–0.70) | 0.653 (0.56–0.70) | 0.624 (0.59–0.69) | 0.654 (0.58–0.72) | 0.628 (0.60–0.67) | 0.660 (0.60–0.76) | 0.663 (0.62–0.73) | 0.627 (0.52–0.71) | 0.678 (0.64–0.73) |
| M3 — whole | 0.641 (0.63–0.66) | 0.667 (0.63–0.72) | 0.673 (0.60–0.74) | 0.711 (0.62–0.81) | 0.755 (0.67–0.85) | 0.811 (0.72–0.88) | 0.710 (0.66–0.76) | 0.705 (0.66–0.74) | 0.729 (0.66–0.78) | 0.770 (0.74–0.80) |
| M4 — remaining | – | 0.528 (0.51–0.55) | 0.534 (0.51–0.55) | 0.521 (0.51–0.53) | 0.519 (0.48–0.54) | 0.520 (0.44–0.57) | 0.493 (0.45–0.53) | 0.570 (0.49–0.62) | 0.516 (0.48–0.56) | 0.544 (0.51–0.59) |
| M4 — whole | – | 0.586 (0.53–0.65) | 0.581 (0.57–0.59) | 0.644 (0.60–0.67) | 0.698 (0.64–0.75) | 0.767 (0.68–0.84) | 0.640 (0.59–0.70) | 0.634 (0.58–0.68) | 0.628 (0.56–0.69) | 0.664 (0.64–0.68) |

*slow climb*

| model — label | τ | τ+1m | τ+2m | τ+5m | τ+10m | τ+20m | vol 0.25× | vol 0.5× | vol 1× | vol 2× |
|---|---|---|---|---|---|---|---|---|---|---|
| M2 — remaining | 0.518 (0.48–0.58) | 0.516 (0.49–0.54) | 0.507 (0.46–0.56) | 0.533 (0.47–0.61) | 0.529 (0.47–0.59) | 0.574 (0.56–0.60) | 0.520 (0.47–0.58) | 0.501 (0.47–0.52) | 0.503 (0.46–0.53) | 0.484 (0.44–0.51) |
| M2 — whole | 0.518 (0.48–0.58) | 0.574 (0.53–0.63) | 0.568 (0.53–0.64) | 0.568 (0.53–0.63) | 0.606 (0.57–0.68) | 0.665 (0.60–0.77) | 0.600 (0.54–0.67) | 0.593 (0.54–0.67) | 0.634 (0.60–0.68) | 0.676 (0.66–0.71) |
| M3 — remaining | 0.560 (0.54–0.59) | 0.548 (0.54–0.57) | 0.538 (0.46–0.59) | 0.539 (0.48–0.61) | 0.556 (0.52–0.62) | 0.606 (0.51–0.67) | 0.508 (0.46–0.53) | 0.505 (0.40–0.57) | 0.509 (0.46–0.58) | 0.496 (0.41–0.55) |
| M3 — whole | 0.560 (0.54–0.59) | 0.603 (0.56–0.64) | 0.593 (0.57–0.63) | 0.590 (0.55–0.61) | 0.629 (0.62–0.65) | 0.707 (0.65–0.78) | 0.629 (0.57–0.71) | 0.601 (0.55–0.65) | 0.631 (0.62–0.64) | 0.696 (0.66–0.76) |
| M4 — remaining | – | 0.514 (0.49–0.54) | 0.543 (0.51–0.58) | 0.529 (0.45–0.60) | 0.505 (0.48–0.53) | 0.544 (0.48–0.66) | 0.511 (0.48–0.53) | 0.499 (0.47–0.52) | 0.551 (0.55–0.56) | 0.480 (0.46–0.49) |
| M4 — whole | – | 0.576 (0.53–0.60) | 0.556 (0.50–0.62) | 0.591 (0.58–0.61) | 0.596 (0.55–0.62) | 0.655 (0.62–0.69) | 0.584 (0.55–0.60) | 0.601 (0.58–0.61) | 0.675 (0.64–0.72) | 0.680 (0.67–0.70) |

*exhausted*

| model — label | τ | τ+1m | τ+2m | τ+5m | τ+10m | τ+20m | vol 0.25× | vol 0.5× | vol 1× | vol 2× |
|---|---|---|---|---|---|---|---|---|---|---|
| M2 — remaining | 0.613 (0.58–0.65) | 0.588 (0.56–0.61) | 0.585 (0.54–0.62) | 0.610 (0.58–0.63) | 0.588 (0.58–0.59) | 0.577 (0.55–0.59) | 0.620 (0.60–0.64) | 0.583 (0.57–0.60) | 0.583 (0.57–0.61) | 0.594 (0.56–0.62) |
| M2 — whole | 0.613 (0.58–0.65) | 0.696 (0.66–0.73) | 0.728 (0.71–0.75) | 0.765 (0.76–0.77) | 0.802 (0.79–0.81) | 0.828 (0.81–0.84) | 0.774 (0.76–0.78) | 0.802 (0.79–0.81) | 0.809 (0.81–0.81) | 0.808 (0.79–0.82) |
| M3 — remaining | 0.595 (0.57–0.62) | 0.601 (0.58–0.61) | 0.611 (0.60–0.64) | 0.620 (0.59–0.64) | 0.612 (0.59–0.62) | 0.580 (0.56–0.59) | 0.597 (0.59–0.61) | 0.577 (0.57–0.58) | 0.589 (0.58–0.61) | 0.589 (0.58–0.60) |
| M3 — whole | 0.595 (0.57–0.62) | 0.713 (0.68–0.75) | 0.746 (0.73–0.77) | 0.789 (0.79–0.79) | 0.827 (0.82–0.83) | 0.858 (0.85–0.86) | 0.783 (0.77–0.79) | 0.840 (0.83–0.85) | 0.856 (0.85–0.86) | 0.858 (0.85–0.87) |
| M4 — remaining | – | 0.517 (0.51–0.52) | 0.541 (0.53–0.56) | 0.562 (0.50–0.61) | 0.519 (0.50–0.54) | 0.545 (0.51–0.58) | 0.482 (0.47–0.50) | 0.492 (0.47–0.51) | 0.483 (0.44–0.53) | 0.507 (0.48–0.55) |
| M4 — whole | – | 0.662 (0.63–0.68) | 0.698 (0.69–0.70) | 0.730 (0.73–0.73) | 0.765 (0.76–0.77) | 0.786 (0.78–0.79) | 0.743 (0.73–0.76) | 0.773 (0.76–0.79) | 0.781 (0.78–0.79) | 0.780 (0.77–0.79) |

*fade*

| model — label | τ | τ+1m | τ+2m | τ+5m | τ+10m | τ+20m | vol 0.25× | vol 0.5× | vol 1× | vol 2× |
|---|---|---|---|---|---|---|---|---|---|---|
| M2 — remaining | 0.540 (0.53–0.55) | 0.585 (0.58–0.59) | 0.591 (0.57–0.63) | 0.620 (0.59–0.66) | 0.621 (0.57–0.66) | 0.627 (0.62–0.65) | 0.579 (0.53–0.61) | 0.613 (0.56–0.65) | 0.581 (0.51–0.63) | 0.576 (0.53–0.61) |
| M2 — whole | 0.540 (0.53–0.55) | 0.586 (0.58–0.60) | 0.586 (0.58–0.59) | 0.601 (0.59–0.62) | 0.623 (0.60–0.66) | 0.645 (0.62–0.66) | 0.588 (0.59–0.59) | 0.585 (0.57–0.59) | 0.618 (0.59–0.64) | 0.615 (0.60–0.64) |
| M3 — remaining | 0.544 (0.52–0.58) | 0.576 (0.54–0.60) | 0.593 (0.56–0.61) | 0.603 (0.60–0.61) | 0.617 (0.59–0.65) | 0.628 (0.60–0.66) | 0.599 (0.56–0.62) | 0.623 (0.59–0.64) | 0.581 (0.56–0.60) | 0.594 (0.55–0.64) |
| M3 — whole | 0.544 (0.52–0.58) | 0.617 (0.60–0.64) | 0.619 (0.60–0.64) | 0.639 (0.63–0.65) | 0.655 (0.64–0.67) | 0.676 (0.65–0.70) | 0.624 (0.62–0.64) | 0.624 (0.59–0.65) | 0.665 (0.65–0.68) | 0.653 (0.64–0.68) |
| M4 — remaining | – | 0.566 (0.56–0.58) | 0.545 (0.53–0.56) | 0.566 (0.53–0.60) | 0.565 (0.51–0.60) | 0.561 (0.51–0.62) | 0.549 (0.54–0.56) | 0.590 (0.56–0.61) | 0.565 (0.51–0.63) | 0.525 (0.51–0.54) |
| M4 — whole | – | 0.575 (0.57–0.59) | 0.559 (0.54–0.57) | 0.560 (0.53–0.60) | 0.581 (0.53–0.63) | 0.617 (0.59–0.63) | 0.574 (0.57–0.58) | 0.594 (0.58–0.61) | 0.600 (0.55–0.67) | 0.609 (0.60–0.62) |

*chop*

| model — label | τ | τ+1m | τ+2m | τ+5m | τ+10m | τ+20m | vol 0.25× | vol 0.5× | vol 1× | vol 2× |
|---|---|---|---|---|---|---|---|---|---|---|
| M2 — remaining | 0.537 (0.53–0.54) | 0.554 (0.54–0.57) | 0.569 (0.55–0.59) | 0.564 (0.55–0.58) | 0.563 (0.55–0.58) | 0.572 (0.56–0.59) | 0.546 (0.53–0.56) | 0.544 (0.53–0.55) | 0.543 (0.50–0.57) | 0.555 (0.55–0.56) |
| M2 — whole | 0.537 (0.53–0.54) | 0.555 (0.54–0.57) | 0.561 (0.56–0.56) | 0.568 (0.56–0.57) | 0.580 (0.58–0.58) | 0.610 (0.60–0.62) | 0.582 (0.56–0.61) | 0.606 (0.59–0.62) | 0.609 (0.60–0.62) | 0.603 (0.59–0.62) |
| M3 — remaining | 0.547 (0.52–0.57) | 0.560 (0.54–0.58) | 0.570 (0.54–0.59) | 0.569 (0.55–0.59) | 0.541 (0.51–0.56) | 0.547 (0.53–0.56) | 0.567 (0.55–0.59) | 0.542 (0.52–0.57) | 0.547 (0.54–0.56) | 0.573 (0.56–0.58) |
| M3 — whole | 0.547 (0.52–0.57) | 0.577 (0.56–0.59) | 0.593 (0.57–0.61) | 0.610 (0.58–0.63) | 0.624 (0.62–0.64) | 0.657 (0.65–0.67) | 0.598 (0.58–0.61) | 0.633 (0.60–0.67) | 0.651 (0.62–0.68) | 0.654 (0.63–0.67) |
| M4 — remaining | – | 0.497 (0.47–0.54) | 0.527 (0.53–0.53) | 0.549 (0.54–0.56) | 0.540 (0.52–0.55) | 0.530 (0.52–0.54) | 0.505 (0.50–0.51) | 0.504 (0.50–0.51) | 0.506 (0.49–0.53) | 0.505 (0.47–0.54) |
| M4 — whole | – | 0.496 (0.48–0.51) | 0.507 (0.48–0.54) | 0.525 (0.50–0.56) | 0.524 (0.51–0.55) | 0.554 (0.51–0.58) | 0.531 (0.51–0.56) | 0.547 (0.53–0.56) | 0.571 (0.57–0.58) | 0.568 (0.54–0.59) |

Secondary read (all test events), M3 (none), AUC mean of three folds:

| type — label | τ | τ+1m | τ+2m | τ+5m | τ+10m | τ+20m | vol 0.25× | vol 0.5× | vol 1× | vol 2× |
|---|---|---|---|---|---|---|---|---|---|---|
| runaway — remaining | 0.612 (0.59–0.63) | 0.613 (0.55–0.65) | 0.632 (0.61–0.65) | 0.619 (0.57–0.66) | 0.597 (0.57–0.63) | 0.575 (0.55–0.60) | 0.565 (0.54–0.58) | 0.562 (0.54–0.61) | 0.581 (0.56–0.60) | 0.567 (0.54–0.61) |
| runaway — whole | 0.612 (0.59–0.63) | 0.622 (0.58–0.65) | 0.648 (0.64–0.66) | 0.693 (0.68–0.72) | 0.667 (0.62–0.71) | 0.699 (0.67–0.72) | 0.664 (0.64–0.69) | 0.672 (0.62–0.70) | 0.679 (0.62–0.71) | 0.657 (0.60–0.70) |
| burst — remaining | 0.670 (0.65–0.70) | 0.649 (0.61–0.70) | 0.641 (0.60–0.67) | 0.626 (0.60–0.66) | 0.635 (0.62–0.66) | 0.648 (0.63–0.66) | 0.666 (0.64–0.70) | 0.633 (0.59–0.67) | 0.660 (0.61–0.70) | 0.649 (0.63–0.66) |
| burst — whole | 0.670 (0.65–0.70) | 0.691 (0.66–0.75) | 0.701 (0.66–0.75) | 0.742 (0.70–0.81) | 0.788 (0.76–0.84) | 0.815 (0.77–0.85) | 0.723 (0.70–0.74) | 0.727 (0.70–0.74) | 0.743 (0.70–0.77) | 0.763 (0.76–0.78) |
| slow climb — remaining | 0.558 (0.56–0.56) | 0.546 (0.52–0.56) | 0.565 (0.55–0.58) | 0.559 (0.50–0.61) | 0.570 (0.53–0.60) | 0.579 (0.57–0.59) | 0.545 (0.54–0.55) | 0.543 (0.51–0.56) | 0.551 (0.51–0.60) | 0.553 (0.52–0.58) |
| slow climb — whole | 0.558 (0.56–0.56) | 0.585 (0.56–0.61) | 0.589 (0.58–0.60) | 0.612 (0.59–0.63) | 0.637 (0.61–0.66) | 0.697 (0.68–0.72) | 0.619 (0.60–0.65) | 0.630 (0.62–0.64) | 0.660 (0.65–0.67) | 0.684 (0.66–0.73) |
| exhausted — remaining | 0.602 (0.59–0.61) | 0.605 (0.60–0.62) | 0.608 (0.59–0.62) | 0.620 (0.61–0.63) | 0.613 (0.60–0.63) | 0.610 (0.61–0.61) | 0.592 (0.57–0.61) | 0.584 (0.54–0.61) | 0.591 (0.57–0.60) | 0.610 (0.59–0.63) |
| exhausted — whole | 0.602 (0.59–0.61) | 0.703 (0.69–0.71) | 0.743 (0.74–0.75) | 0.799 (0.80–0.80) | 0.839 (0.84–0.84) | 0.869 (0.86–0.88) | 0.795 (0.79–0.80) | 0.833 (0.83–0.84) | 0.846 (0.84–0.86) | 0.839 (0.83–0.85) |
| fade — remaining | 0.576 (0.56–0.59) | 0.593 (0.57–0.61) | 0.605 (0.56–0.63) | 0.623 (0.59–0.64) | 0.641 (0.61–0.66) | 0.638 (0.61–0.66) | 0.601 (0.57–0.62) | 0.621 (0.58–0.65) | 0.610 (0.57–0.64) | 0.606 (0.58–0.63) |
| fade — whole | 0.576 (0.56–0.59) | 0.620 (0.60–0.64) | 0.633 (0.63–0.64) | 0.649 (0.63–0.66) | 0.675 (0.66–0.69) | 0.687 (0.68–0.69) | 0.642 (0.63–0.66) | 0.651 (0.63–0.66) | 0.676 (0.67–0.69) | 0.685 (0.68–0.69) |
| chop — remaining | 0.551 (0.54–0.56) | 0.560 (0.55–0.57) | 0.565 (0.55–0.58) | 0.574 (0.57–0.58) | 0.572 (0.54–0.60) | 0.572 (0.56–0.58) | 0.565 (0.55–0.58) | 0.554 (0.52–0.58) | 0.558 (0.54–0.57) | 0.572 (0.55–0.59) |
| chop — whole | 0.551 (0.54–0.56) | 0.577 (0.56–0.58) | 0.588 (0.58–0.59) | 0.619 (0.61–0.63) | 0.646 (0.64–0.66) | 0.672 (0.66–0.68) | 0.615 (0.60–0.63) | 0.644 (0.62–0.67) | 0.652 (0.64–0.66) | 0.648 (0.64–0.66) |

Rung (whole label only): M3 (none) probabilities scored against the N = 50 and N = 200 whole-path labels (never fitted), primary read, mean AUC of three folds:

| label | type | τ | τ+1m | τ+2m | τ+5m | τ+10m | τ+20m | vol 0.25× | vol 0.5× | vol 1× | vol 2× |
|---|---|---|---|---|---|---|---|---|---|---|---|
| N = 50 | runaway | 0.569 | 0.605 | 0.621 | 0.694 | 0.661 | 0.681 | 0.684 | 0.681 | 0.664 | 0.637 |
| N = 50 | burst | 0.606 | 0.609 | 0.656 | 0.705 | 0.748 | 0.785 | 0.687 | 0.685 | 0.704 | 0.703 |
| N = 50 | slow climb | 0.521 | 0.596 | 0.593 | 0.608 | 0.637 | 0.714 | 0.604 | 0.622 | 0.651 | 0.669 |
| N = 50 | exhausted | 0.610 | 0.723 | 0.746 | 0.794 | 0.830 | 0.861 | 0.796 | 0.842 | 0.860 | 0.860 |
| N = 50 | fade | 0.556 | 0.594 | 0.616 | 0.633 | 0.650 | 0.676 | 0.629 | 0.625 | 0.682 | 0.662 |
| N = 50 | chop | 0.561 | 0.577 | 0.596 | 0.613 | 0.636 | 0.655 | 0.611 | 0.639 | 0.655 | 0.641 |
| N = 100 | runaway | 0.560 | 0.591 | 0.620 | 0.693 | 0.666 | 0.708 | 0.671 | 0.674 | 0.683 | 0.653 |
| N = 100 | burst | 0.667 | 0.679 | 0.701 | 0.747 | 0.788 | 0.817 | 0.734 | 0.711 | 0.735 | 0.757 |
| N = 100 | slow climb | 0.542 | 0.609 | 0.613 | 0.601 | 0.638 | 0.711 | 0.629 | 0.614 | 0.661 | 0.700 |
| N = 100 | exhausted | 0.607 | 0.720 | 0.750 | 0.793 | 0.835 | 0.862 | 0.790 | 0.842 | 0.857 | 0.860 |
| N = 100 | fade | 0.564 | 0.626 | 0.642 | 0.655 | 0.675 | 0.686 | 0.641 | 0.642 | 0.678 | 0.676 |
| N = 100 | chop | 0.565 | 0.594 | 0.603 | 0.624 | 0.653 | 0.670 | 0.615 | 0.652 | 0.665 | 0.661 |
| N = 200 | runaway | 0.618 | 0.643 | 0.642 | 0.720 | 0.715 | 0.743 | 0.705 | 0.710 | 0.699 | 0.675 |
| N = 200 | burst | 0.649 | 0.673 | 0.691 | 0.731 | 0.779 | 0.824 | 0.711 | 0.730 | 0.740 | 0.738 |
| N = 200 | slow climb | 0.536 | 0.582 | 0.581 | 0.603 | 0.628 | 0.695 | 0.621 | 0.610 | 0.661 | 0.694 |
| N = 200 | exhausted | 0.605 | 0.704 | 0.732 | 0.782 | 0.824 | 0.856 | 0.784 | 0.838 | 0.854 | 0.851 |
| N = 200 | fade | 0.580 | 0.611 | 0.631 | 0.645 | 0.668 | 0.687 | 0.632 | 0.639 | 0.696 | 0.681 |
| N = 200 | chop | 0.570 | 0.597 | 0.606 | 0.625 | 0.657 | 0.680 | 0.629 | 0.651 | 0.671 | 0.665 |

Confusion at the most probable type, M3 (none), primary read, three folds summed, remaining label at τ + 20 min (row = true type, cells = counts):

| true \ predicted | runaway | burst | slow climb | exhausted | fade | chop |
|---|---|---|---|---|---|---|
| runaway | 0 | 0 | 0 | 1 | 0 | 77 |
| burst | 0 | 0 | 0 | 1 | 1 | 104 |
| slow climb | 0 | 0 | 0 | 2 | 2 | 158 |
| exhausted | 0 | 0 | 0 | 36 | 6 | 483 |
| fade | 0 | 0 | 0 | 14 | 7 | 296 |
| chop | 1 | 0 | 0 | 36 | 9 | 1,796 |

Settings chosen by validation log loss inside the training windows (count of fold × decision time jobs; the remaining label's τ jobs are the whole label's):

| label | model | class weight | setting | jobs |
|---|---|---|---|---|
| remaining | M2 | balanced | `{'C': 0.1}` | 29 |
| remaining | M2 | balanced | `{'C': 1.0}` | 1 |
| remaining | M2 | none | `{'C': 0.1}` | 30 |
| remaining | M3 | balanced | `{'learning_rate': 0.03, 'max_leaf_nodes': 15, 'max_iter': 200}` | 4 |
| remaining | M3 | balanced | `{'learning_rate': 0.03, 'max_leaf_nodes': 15, 'max_iter': 500}` | 1 |
| remaining | M3 | balanced | `{'learning_rate': 0.03, 'max_leaf_nodes': 31, 'max_iter': 200}` | 22 |
| remaining | M3 | balanced | `{'learning_rate': 0.03, 'max_leaf_nodes': 31, 'max_iter': 500}` | 2 |
| remaining | M3 | balanced | `{'learning_rate': 0.1, 'max_leaf_nodes': 15, 'max_iter': 200}` | 1 |
| remaining | M3 | none | `{'learning_rate': 0.03, 'max_leaf_nodes': 15, 'max_iter': 200}` | 30 |
| remaining | M4 | balanced | `{'k': 100}` | 27 |
| remaining | M4 | none | `{'k': 100}` | 27 |
| whole | M2 | balanced | `{'C': 0.1}` | 29 |
| whole | M2 | balanced | `{'C': 1.0}` | 1 |
| whole | M2 | none | `{'C': 0.1}` | 30 |
| whole | M3 | balanced | `{'learning_rate': 0.03, 'max_leaf_nodes': 15, 'max_iter': 200}` | 4 |
| whole | M3 | balanced | `{'learning_rate': 0.03, 'max_leaf_nodes': 15, 'max_iter': 500}` | 1 |
| whole | M3 | balanced | `{'learning_rate': 0.03, 'max_leaf_nodes': 31, 'max_iter': 200}` | 23 |
| whole | M3 | balanced | `{'learning_rate': 0.03, 'max_leaf_nodes': 31, 'max_iter': 500}` | 1 |
| whole | M3 | balanced | `{'learning_rate': 0.1, 'max_leaf_nodes': 15, 'max_iter': 200}` | 1 |
| whole | M3 | none | `{'learning_rate': 0.03, 'max_leaf_nodes': 15, 'max_iter': 200}` | 30 |
| whole | M4 | balanced | `{'k': 100}` | 27 |
| whole | M4 | none | `{'k': 100}` | 27 |

**Row 4 (LOG).** Cells where one input carries more than half of a type's M3 permutation importance, with the input's timing re-check (its row in §1.3):

| label | fold | time | type | input | share | AUC drop | base AUC | n_type |
|---|---|---|---|---|---|---|---|---|
| remaining | 2 | τ+20m | chop | `ret_log` | 0.51 | 0.0180 | 0.548 | 487 |
| remaining | 3 | vol 1× | exhausted | `tod_h` | 0.55 | 0.0640 | 0.611 | 163 |

## 6. Rulings, the amendment and declared interpretations

- **R1_tau_close_sensitive** — measured: tau_close_sensitive (b1 A1.3: |tau(revised close) - tau(minute-bar close)| > 60 s) is not settled at tau for 3,585 of 15,519 events: the minute-bar-close crossing comes after tau for 3,302 and never happens for 283. It is settled by tau + 60 s for every event. Ruling: causal 3-level input: at each decision time d the flag as far as it is settled by d -- TRUE / FALSE / not_settled.
- **R2_short_interest** — measured: F1's si_asof_ns is the SETTLEMENT date (midnight UTC), not publication; settlement -> event date median 7 calendar days, 5% on the event date itself. No publication date on disk. Under an 8-session publication assumption only 2,104 of 15,107 events would use the settlement F1 used. Ruling: latest settlement whose assumed publication, 10 XNYS sessions after settlement (conservative; FINRA's actual lag not verifiable offline [verify]), is a session strictly before the event date.
- **R3_fundamentals_anchor** — measured: F1 anchors at t0 (D28/D33); t0 > tau for 1,477 events. One event (LNSR_2024-11-07_31.57) carries a shares count accepted after tau; six events' F1 filing windows reach past tau (dilution flag FALSE for all six either way). Ruling: re-anchor at tau with D28's rule: accepted_ns < tau (and, for shares, asof < tau as in F1's T5), from F1's own raw SEC archive.
- **R4_positive_control** — measured: on S1's tables with the S2 folds (primary sets, HGB): + terminal_log gives runaway 0.94-0.95, burst 0.79-0.81, slow climb 0.89-0.92, exhausted 0.76-0.80, fade 0.85-0.88, chop 0.75-0.80 -- row 3 would fire because terminal return does not set the type. + the rule inputs gives 1.000 (HGB) and >= 0.993 (logistic) for every type and fold. Ruling: two positive-control runs on M2 and M3 at every decision time; row 3 gates on the rule-inputs leak (post100_rise_pct, post100_fall_pct, post100_u_peak); the briefed terminal_log run is reported beside it, ungated.
- **R5_negative_control** — measured: one shuffle per fold (HGB, 10 shuffles): runaway ranged 0.32-0.69 and fell outside 0.45-0.55 in 60% of fold cells (burst/slow climb/fade 17-20%, exhausted 10%, chop 0%); pooling folds biases runaway to 0.458 because base rates differ by fold Ruling: 10 independent shuffles per fold; row 2 reads the mean per-fold AUC over the 3 folds x 10 shuffles for each type x model x decision time against 0.45-0.55; hyperparameters fixed at the real run's choices; single-shuffle per-fold values reported beside it.

- **Amendment 1, A1_1_row3** — revised: M3 (class weight none and balanced) must reach AUC >= 0.95 in every per-fold primary cell of the rule-inputs positive control, every type and decision time, for each label; M2 reported beside it, ungated. Cleared on the committed run (M3 1.000 in all 360 cells)..
- **Amendment 1, A1_2_crossing** — T2 calls b1's common.first_crossing on the full print arrays with lo / hi = the 04:00 / 20:00 indices (as b1 did), so the 04:00 print is judged against its predecessor; affects the R1 tcs_state input only.
- **Amendment 1, A1_5_scope** — re-run T2 (A1.2), T3 (remaining-path labels: t3a_remaining_labels.py; folds and counts for both labels), T0 (the audit of the re-built inputs), T4-T8 for both labels; models, grid, folds, controls and escalation rows unchanged except row 3 (A1.1). Stop after the report..
- **Amendment 1, charts** — every page gains a label selector; charts/t6/money_intervals.html is added (the A1.4 differences with intervals, all entries and units); forward_returns.html keeps the next-print entry only (the latency sensitivity is on money_intervals.html) and adds the bottom decile, to keep the page under ~25 MB.
- **Amendment 1, A1_6_a12** — recorded: the tm1_t0 A12 flag reads the event day's own last trade (T0), so the 32 earlier with/without splits were partly splits on the event day's outcome; a retraction-sweep note and a split-record corporate-action flag are listed for Cooper as a separate item, not part of this re-run.
- **Amendment 1, A1.3 primary_after_tau** — remaining-path type at each checkpoint after tau: S1's rules unchanged (config/shape_atlas_s1.json theory_types) applied to the path from the checkpoint's entry to 20:00.
- **Amendment 1, A1.3 path** — entry = the first print with ts > d (the zero-latency entry of T2); element 0 = the entry print's price; N = 100 equal-volume buckets (instruments.bucketize) over the prints with ts > the entry's timestamp up to the last print <= 20:00 -- S1's post-tau construction with the entry print in tau's place.
- **Amendment 1, A1.3 components_and_null** — s1common.real_pipeline / null_pipeline unchanged: sigma_path from the path's own bucket log returns; 200 draws with replacement of its own demeaned bucket returns; rise_pct / fall_pct = mid-rank percentiles against the draws with sigma > 0; rng = numpy default_rng([20260927 (S1's null seed), S1 event_index, 10 + the checkpoint's position in the decision-time order, 100]).
- **Amendment 1, A1.3 unavailable** — no entry print before 20:00 (no_entry); fewer than 2 prints after the entry (path_too_short); untyped when the path's sigma_path is zero or no null draw has sigma > 0 -- carried and counted, never fitted or scored at that checkpoint.
- **Amendment 1, A1.3 at_tau** — the two labels are the same by construction (brief A1.3): the remaining-label results at tau are the whole-label results at tau, copied (identical label vector and pipeline).
- **Amendment 1, A1.3 secondary** — the whole-path type (S1, N = 100), as run, re-run with the A1.2 fix; N = 50 / 200 rung labels stay with the whole label only.
- **Amendment 1, A1.3 group_c_and_m4** — for the remaining label, the typical paths (tune and final stages) and the M4 votes use the training events' remaining-path type at that checkpoint; the path so far and its grid are unchanged.
- **Amendment 1, A1.3 m0** — shares of the label among the labelled training events that reached the checkpoint.
- **Amendment 1, A1.3 positive_control** — rules = the remaining path's rise_pct, fall_pct, u_peak at the checkpoint (gated, M3); terminal_log = the remaining path's terminal log return (reported, ungated); at tau the whole path's.
- **Amendment 1, A1.4 sets** — per label, model variant, type and decision time: top decile (score >= its 90th percentile within each fold's primary test set, ties included) and bottom decile (score <= its 10th percentile), pooled over the three folds; against all labelled primary test events that reached the decision time.
- **Amendment 1, A1.4 statistics** — median net forward return of the top decile, the bottom decile and all; differences top - all and bottom - all.
- **Amendment 1, A1.4 intervals** — 95% percentile intervals from 500 ticker bootstrap resamples of the pooled primary test set (its tickers are disjoint across folds); a resample weights each row by its ticker's draw count; weighted medians; the same resample serves the subset and all, so the difference is paired.
- **Amendment 1, A1.4 grid** — every horizon (+10, +30, +60 min, to 20:00), entry (next print, >= d + 1 s, >= d + 5 s) and unit (net bp, net cents).
- **Amendment 1, A1.4 seed** — 20260929.

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
.venv/Scripts/python.exe research/shape_classifier_s2/t3a_remaining_labels.py
.venv/Scripts/python.exe research/shape_classifier_s2/t0_audit.py
.venv/Scripts/python.exe research/shape_classifier_s2/t3_folds.py
.venv/Scripts/python.exe research/shape_classifier_s2/t4_models.py
.venv/Scripts/python.exe research/shape_classifier_s2/t4_scores.py
.venv/Scripts/python.exe research/shape_classifier_s2/t6_money.py
.venv/Scripts/python.exe research/shape_classifier_s2/t7_importance.py
.venv/Scripts/python.exe research/shape_classifier_s2/t5_controls.py
.venv/Scripts/python.exe research/shape_classifier_s2/charts.py
.venv/Scripts/python.exe research/shape_classifier_s2/build_report.py
```

T0's audit runs after T1 and T2 because it audits what they built; T1 and T2 also assert their own inputs as they write them. `t2b_mb_diagnosis.py` is the record of the pre-A1.2 defect (not re-run). `results/shape_classifier/s2/cache/` (tick-pass caches and master-grid paths, rebuilt by T1/T2) is git-ignored in place and not committed.

Artifacts (`results/shape_classifier/s2/artifacts/`): `t0_a12.json`, `t0_audit.parquet`, `t0_summary.json`, `t1_group_a.parquet`, `t1_summary.json`, `t2_checkpoints.parquet`, `t2_event_meta.parquet`, `t2_forward.parquet`, `t2_group_c.parquet`, `t2_summary.json`, `t2_typical_paths.parquet`, `t2b_mb_diagnosis.json`, `t2b_mb_diagnosis.parquet`, `t3_counts.parquet`, `t3_membership.parquet`, `t3_row5.parquet`, `t3_summary.json`, `t3a_remaining_labels.parquet`, `t3a_summary.json`, `t4_auc.parquet`, `t4_calibration.parquet`, `t4_confusion.parquet`, `t4_group_c_remaining.parquet`, `t4_lift.parquet`, `t4_logloss.parquet`, `t4_predictions.parquet`, `t4_scores_summary.json`, `t4_summary.json`, `t4_tuning.parquet`, `t5_negative.parquet`, `t5_negative_gate.parquet`, `t5_positive.parquet`, `t5_summary.json`, `t6_forward.parquet`, `t6_summary.json`, `t7_importance.parquet`, `t7_row4.parquet`, `t7_summary.json`.

Charts: `charts/t4/auc_by_time.html`, `charts/t4/lift_by_time.html`, `charts/t4/calibration.html`, `charts/t4/confusion.html`, `charts/t5/controls.html`, `charts/t6/money_intervals.html`, `charts/t6/forward_returns.html`, `charts/t7/importance.html`.

