# Phase 6c — Defect #4 Confirmation: Cohort-Stratified Verdict & Residual Diagnosis — Report

**Branch:** `phase/6c` | **Baseline:** tip of `phase/6b` (A6.1 full stop)

Description only, per the Evidence Standard — no recommendations. Amendment 7's chart pack and Amendment 8's disposition are Cooper's own judgment calls at the gate; this report states what was measured and what Cooper decided, not an independent interpretation.

---

## 1. T1 — Stratified recomputation (from `a61_basis_confirmation_rerun.json` only)

Recomputed A6.1's three criteria (2% band, 90% threshold) separately by dev v4 cohort — no re-measurement, no threshold changes.

| Stratum | n | Criterion 1 (% agree) | Pass (≥90%)? | Criterion 2 | Criterion 3 |
|---|---|---|---|---|---|
| Primary | 50 | **92.0%** (46/50) | **PASS** | pass (OCUL, MDIA stable) | pass (100%) |
| Sidecar | 6 | 40.0% (2/5, 1 undefined) | fail (expected) | n/a (no in-stratum dup tickers) | pass |
| Pooled (A6.1's original denominator) | 56 | 87.27% (48/55) | fail | pass | pass |

The pooled 87.27%-vs-90% "failure" that triggered the A6.1 stop was a cohort-composition artifact: the representative primary cohort passes at 92.0%; the sidecar (drawn *because* its 6 events are deliberately degraded, per Phase 5a §4) fails as expected and was never meant to be pooled into a population-level statistic. RBC (sidecar) is the sole undefined-ratio event. Source: `results/phase_6c/artifacts/t1_stratified_criteria.json`.

---

## 2. T2 — Per-residual classification (all 7)

Fixed rules applied literally (`config/phase_6c.json`), against primary-cohort medians (rth_bar_count=382, longest_intra_rth_gap=2min, eth_vs_rth_row_share=0.031):

| Ticker | Cohort | Classification | Key evidence |
|---|---|---|---|
| NEPH | primary | `band_margin` | rel_diff 3.0%, internal agreement 3.1%, no coverage anomaly |
| ZENA | primary | `band_margin` | rel_diff 2.9%, elevated ETH share (59.4% vs 3.1% median) but no vendor-high-exceeds signal |
| ACET | sidecar | `coverage_gap` | internal disagreement 16.3%, vendor high > our high, 3 supporting gap signals |
| NUKK | sidecar | `coverage_gap` | internal disagreement 33.4%, vendor high > our high, 79-min intra-RTH gap |
| PSIX | sidecar | `band_margin` | rel_diff 5.9%, internal agreement 6.3% |
| **SCLX** | primary | **`unexplained`** | vendor high > our high + gap evidence present, but internal disagreement only 3.4% — below the 10% coverage_gap trigger |
| **VEEE** | primary | **`unexplained`** | vendor high > our high + gap evidence present, but internal disagreement only 4.9% — below the 10% coverage_gap trigger |

5/7 resolved; SCLX and VEEE fit neither rule (gap evidence present without the internal-disagreement magnitude the `coverage_gap` rule requires) — escalation row 1 triggered per protocol, stopped before the original T3. Source: `results/phase_6c/artifacts/t2_residual_classification.json`.

---

## 3. Amendment 7 / A7.1 — Diagnostic chart pack (descriptive only, no reclassification)

Three predictions were pre-registered against SCLX/VEEE: **P1** (one-sidedness — thinness-driven residuals should never show `r-1 < 0` on either leg), **P2** (dose-response — deviation from 1 should grow as tape thinness increases), **P3** (separation — confirmed asymmetric `coverage_gap` cases should visually separate from symmetric `unexplained` cases).

- Chart 01 (`01_r_agreement_by_cohort.html`) — per-event `|r1'-r2'|/r2'` by cohort, 2% band.
- Chart 02 (`02_deviation_vs_thinness.html`) — geometric-mean deviation vs. tape thinness (P2).
- Chart 03 (`03_leg_direction.html`) — `r1'-1` vs `r2'-1` leg direction per event (P1, P3).
- Chart 04 (`residual_raw/`, 9 files + index) — raw tick-level evidence for all 7 residuals + AMC/AMCX controls, with an independent, price-free T+0 volume cross-check (ours vs. spine `event_volume`).

**Volume cross-check (the falsifying evidence):**

| Ticker | Cohort | T2 class | Our T+0 volume | Spine `event_volume` | Ratio |
|---|---|---|---|---|---|
| SCLX | primary | unexplained | 195,644 | 5,580 | **35.06** |
| VEEE | primary | unexplained | 185,604 | 13,425 | **13.83** |
| NEPH | primary | band_margin | 823,295 | 821,695 | 1.00 |
| ZENA | primary | band_margin | 47,423,604 | 47,353,548 | 1.00 |
| ACET | sidecar | coverage_gap | 610,089 | 378,899 | 1.61 |
| NUKK | sidecar | coverage_gap | 58,261 | 7,282 | 8.00 |
| PSIX | sidecar | band_margin | 63,728 | 63,728 | 1.00 |
| AMC | control | control | 135,501,142 | 13,474,947 | 10.06 |
| AMCX | control | control | 3,446,031 | 3,359,235 | 1.03 |

Source: `results/phase_6c/artifacts/a71_chartpack_summary.json`, `a71_chart04_summary.json`.

---

## 4. Amendment 8 — Cooper's disposition (gate outcome b) and D4

**Gate outcome: (b).** The thinness mechanism is falsified for SCLX/VEEE by the volume cross-check's *direction* — their tick volume exceeds spine `event_volume` by 35.1x/13.8x; a coverage gap can only produce a deficit. No `coverage_thin_symmetric` category was created. **SCLX and VEEE remain classified `unexplained`** — closed by severance, not explanation.

**D4** (recorded verbatim, `docs/Universe-Decisions.md`): all measured quantities in every analysis phase are derived exclusively from `filtered_trades`/`filtered_quotes`; every spine numeric OHLC/volume column is permanently quarantined from computation (diagnostic display only). This supersedes Amendment 5's price-only tick-anchor authorization. `momentum_pct` remains the sole exception (universe selection/stratification only). The full-population basis audit contemplated under Amendment 7 disposition (b) is superseded — a column never read needs no characterization.

**Final mechanism statement:** `momentum_events`' numeric columns carry inconsistent adjustment bases per ticker *and* per column within the same row — evidence: NUKK's price factor (7.98) and volume factor (8.001) are coherent (one real 1:8 split), but AMC's price factor (5.24) and volume factor (10.06) are not, despite AMC *passing* the price-ratio check. The tick archive is the trustworthy layer.

---

## 5. A8.1 — Closure tasks

- **T3′** — `results/phase_6c/artifacts/closure.json`: stratified criteria + final 7-way classification + 9-row volume cross-check + `disposition: "b_superseded_by_D4"`. No boolean.
- **T3″** — Dev-tier duplicate-print check, `filtered_trades_dev_v4`, both cohorts (56 events, 9,638,361 rows): the loose (event key, `sip_timestamp`, `price`, `size`) key flags 0.599% collision share (8/56 events over 0.1%), but every one of those collisions carries a **distinct `sequence_number`** — ordinary distinct trades sharing a tick/price/size on a busy tape, not duplicate ingestion. The strict key (adding `sequence_number`, present in this table) shows **0.0% true duplication, 0/56 events escalated**. Source: `results/phase_6c/artifacts/t3_dev_duplicate_print_check.json`.
- **T3‴** — Docs: D4 appended to `docs/Universe-Decisions.md`; `CLAUDE.md`'s Universe rules section gained the D4 constraint (all spine numeric columns, not just price); `docs/Open-Items-Register.md` closed the defect #4 item with the full discovery-to-severance narrative.

---

## 6. Escalation check table

| # | Condition | Threshold | Observed | Result |
|---|---|---|---|---|
| 1 | Any `unexplained` classification | >0 | 2 (SCLX, VEEE) | **triggered** — resolved by Amendment 7/8, not by reclassification |
| 2 | Primary-cohort criterion 1 | <90% | 92.0% | pass |
| 3 | Write outside phase paths, or new full-table pass | any | none | pass |
| 4 | Modification to 6b code/artifacts | any | none | pass |
| 5 (added, A8.1) | Dev-tier duplicate-print rate, strict key | >0.1% per event | 0.0% all events | pass |

---

## 7. Verification block

| Metric | Value | n | Source | Repro |
|---|---|---|---|---|
| Stratified criteria | table in §1 | 56 (50+6) | `t1_stratified_criteria.json` | `.venv/Scripts/python.exe -m research.phase_6c.t1_stratified` |
| Residual classification | table in §2 | 7 | `t2_residual_classification.json` | `.venv/Scripts/python.exe -m research.phase_6c.t2_classify` |
| Chart pack (01–03) | table in §3 | 55 | `a71_chartpack_summary.json` | `.venv/Scripts/python.exe -m research.phase_6c.a71_charts_01_03` |
| Raw evidence suite + volume cross-check | table in §3 | 9 | `a71_chart04_summary.json` | `.venv/Scripts/python.exe -m research.phase_6c.a71_chart_04_raw` |
| Closure artifact | disposition + full tables | — | `closure.json` | `.venv/Scripts/python.exe -m research.phase_6c.t3_closure` |
| Dev-tier duplicate check | 0.0% strict-key duplication | 9,638,361 rows | `t3_dev_duplicate_print_check.json` | `.venv/Scripts/python.exe -m research.phase_6c.t3_dup_check` |

**Filter waterfall:** `a61_basis_confirmation_rerun.json` full table (56 events) → primary (50) / sidecar (6) strata → 7 residuals → 5 classified (band_margin/coverage_gap) + 2 unexplained → Amendment 7 chart pack (55 events with defined ratios + 9-file raw suite) → Amendment 8 disposition (b) → D4 → closure.

**Environment:** `.venv` — duckdb 1.4.4, pandas, numpy, plotly + kaleido (chart render/verify). No calendar arithmetic this phase.

---

## 8. Output files

| File | Status |
|---|---|
| `prompts/phase_6c.md`, `config/phase_6c.json` | committed |
| `results/phase_6c/artifacts/t1_stratified_criteria.json`, `t2_residual_classification.json` | committed |
| `results/phase_6c/artifacts/a71_chartpack_summary.json`, `a71_chart04_summary.json` | committed |
| `results/phase_6c/artifacts/closure.json`, `t3_dev_duplicate_print_check.json` | committed |
| `results/phase_6c/charts/01–03*.html`, `residual_raw/` (9 files + index) | committed |
| `docs/Universe-Decisions.md` (D4) | committed |
| `CLAUDE.md` (D4 constraint) | committed |
| `docs/Open-Items-Register.md` (defect #4 closed) | committed |
| `results/phase_6c/digest.json`, `REPORT.md` | committed (this commit) |
| `results/reports/phase_6c_report.md` | committed (this commit, copy) |

### Commits (`ed1d9b5..HEAD`)

T0 branch/prompt/config · T1 stratified criteria · T2 residual classification (escalation row 1) · A7.1 diagnostic chart pack (charts 01–04) · A8/T3′ closure artifact · A8/T3″ dev-tier duplicate-print check · A8/T3‴ docs (D4, CLAUDE.md, Open-Items-Register) · T4 digest/REPORT (this commit).

---

## Approval Gate

On Cooper's approval: tag `phase-6c-approved`. Per Amendment 8, Phase 6b then resumes at A6.2/A6.3 (already tick-only) under the A8.2 terms — chart 08 dropped, duplicate-print counters added to the single budgeted full pass, a spine-numeric-column sweep of `research/phase_6b/` and `config/phase_6b.json` required before the config re-freeze commit. No 6b work of any kind before the tag exists.
