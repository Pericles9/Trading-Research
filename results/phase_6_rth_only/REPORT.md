# Phase 6 — Measurement 1: Concentration Curves & the Detection Latency Budget — Report

**Branch:** `phase/6` | **Baseline:** `phase-5a-approved`

Description only, per the Evidence Standard — no recommendations, no strategy-family interpretation. The latency-budget number is Cooper's to set from chart 04.

---

## 1. Eligibility waterfall (T1)

D1 universe (`in_scope=TRUE AND source_file='file1'`) read from Phase 5a's already-materialized `sampling_frame.parquet` rather than re-querying `momentum_events_canonical` (that view's `trades_ingested`/`quotes_ingested` columns force a DISTINCT scan of `filtered_trades`+`filtered_quotes` on every query — reusing the frozen, freshness-checked artifact avoids a redundant multi-billion-row pass).

| Step | n | % of D1 |
|---|---|---|
| D1 total | 15,763 | 100% |
| T=0-trades-eligible (`substr(trades_bitmap,4,1)='1'`) | 15,763 | 100% |
| Ineligible | 0 | 0% |

The filter turned out non-binding: `in_scope` already requires `NOT flag_missing_event_day` (zero event-day trades excludes an event from the canonical spine entirely), so every D1 event already carries T=0 trades. Escalation row 2 (ineligible > 1%) does not trigger. Source: `results/phase_6/artifacts/t1_eligibility.json`.

---

## 2. Dev-tier verification (T2)

Against `filtered_trades_dev_v4` (56 events, both cohorts): build 0.68s (ceiling 60s), 0 duplicate `(event, offset, minute)` keys, 0 out-of-session minute indices, 0/56 mismatches between `trades_bitmap` and which `(event, offset)` combinations actually produced bars. 2/56 events (ZENA 59.4%, SLXN 53.1%) had >50% of T=0 rows outside the regular session. Dev-tier preview: pooled median opportunity-decay crossed 0.5 at minute 39 (with minute 0) / 55 (excluded), ratio 1.41×. Source: `results/phase_6/artifacts/t2_dev_pipeline_summary.json`.

---

## 3. Bar-cache materialization (T3)

Single full pass over `filtered_trades` (4,951,605,544 rows): **22.04 minutes**. `event_minute_bars_v1`: 30,309,950 bar rows across all 7 offsets.

| Offset | Events with bars | Bar rows |
|---|---|---|
| T-3 | 15,523 | 3,558,983 |
| T-2 | 15,595 | 3,670,917 |
| T-1 | 15,721 | 3,877,265 |
| **T+0** | **15,763** | **5,192,383** |
| T+1 | 15,739 | 4,934,647 |
| T+2 | 15,738 | 4,647,781 |
| T+3 | 15,747 | 4,427,974 |

Verify: 0 duplicate keys, 0 out-of-session minute indices (escalation row 3 clear). Distinct T=0 events in bars = 15,763, exact match to T1's eligible count (escalation row 4 clear).

**Excluded T=0 rows (pre/post-session prints):** 736/15,763 events (4.7%) have >50% of their T=0 rows outside the regular session — consistent in order of magnitude with the dev-tier rate (2/56, 3.6%). Top of the list (all >89% excluded): XRTX (99.2%), VERO (99.0%), RAYA (98.1%), SGBX (97.6%), PETZ 2021-11-03 (97.0%), NCNA (96.7%), CHNR (96.7%), CTOR (96.0%), COCH (95.6%), PETZ 2021-02-16 (95.4%). Full list (736 events): `results/phase_6/artifacts/t3_excluded_t0_rows.parquet`. Source: `results/phase_6/artifacts/t3_full_pass_summary.json`.

---

## 4. Measurements (T4)

Computed from `event_minute_bars_v1` (T=0 only), no further `filtered_trades` passes. 15,763 events, 6,128,310-row full per-minute grid (zero-volume / forward-filled-price for thin minutes).

**Minimum-window stats** (minutes to hold X% of T=0 session volume), n=15,763:

| X% | Median (min) |
|---|---|
| 25% | 20 |
| 50% | 72 |
| 75% | 183 |

Distributions: `charts/03_min_window_cdf.html`.

**Headline — minutes to 50% of the day's move** (pooled median crossing, n=15,763):

| Variant | Crossing minute | Sensitivity ratio |
|---|---|---|
| With minute 0 | 52 | — |
| Excluding minute 0 | 57 | 1.10× |

Escalation row 5 (ratio > 2× either direction) does not trigger — both variants committed and charted (`charts/04_opportunity_decay.html`) before this number is reported. 47 events (with minute 0) / 48 (excluding it) have an undefined realized-move-fraction denominator (`open_close_abs_move` = 0, or — rare — no trade at all after the variant's cutoff).

---

## 5. Escalation check table

| # | Condition | Threshold | Observed | Result |
|---|---|---|---|---|
| 1 | Dev v4 manifest join vs. canonical spine | ≠ 56/56 | 56/56 exact (5m09s) | pass |
| 2 | Ineligible share of D1 | > 1% (157) | 0 (0%) | pass |
| 3 | Bar integrity: out-of-session / duplicate keys | any | 0 / 0 (dev and full) | pass |
| 4 | Distinct T=0 events in bars vs. T1 eligible | any deviation | 15,763 == 15,763 | pass |
| 5 | Sensitivity ratio | > 2× either direction | 1.10× | pass |
| 6 | Dev-tier runtime | > 60s | 0.68s | pass |
| 7 | Full passes over `filtered_trades` | > 1 | 1 (22.04 min) | pass |
| 8 | Write to base/dev tables or data root | any | none — only `event_minute_bars_v1` created | pass |
| 9 | Calendar pin drift | ≠ 5.4.0 / 4.13.2 | 5.4.0 / 4.13.2 | pass |

No escalations triggered this phase.

---

## 6. Charts

- `01_volume_concentration.html` — pooled median + IQR by momentum_pct decile (n=15,763, 10 facets): all 10 deciles sit above the diagonal, no single-step-at-t=0 artifact.
- `02_move_concentration.html` — same encoding, cumulative path-length share: also above the diagonal, less pronounced than volume.
- `03_min_window_cdf.html` — 25/50/75% CDFs well separated, no mass-at-1-minute or mass-at-full-session artifact.
- `04_opportunity_decay.html` — pooled median + IQR, with/without-minute-0 overlaid, crossings at minute 52/57 annotated.
- `05_per_event_overlay.html` — top decile (n=30), bottom decile (n=30), seeded random 30 (seed 42) against the pooled band: individual events swing between 0 and 3+ repeatedly while the pooled median rises smoothly from ~0.2 to ~1.0; heterogeneity is visible but not obviously tied to a particular decile. Y-axis defaults to [0,3] (not clipped — population max realized-move-fraction is 2,306, 99th pct 12.1; full range reachable via autoscale/scroll-zoom).
- `index.html` — sortable, full 15,763-event population (eligibility, min-window stats, minutes-to-50%, momentum_pct, decile), no sampling.

Two rendering bugs were found and fixed during kaleido verification (see `digest.json` decisions_log): chart 05's overlay groups initially plotted the full ~1,580-event decile instead of a readable seeded sample, and charts 01/02's caption overlapped the bottom subplot row.

---

## 7. Verification block

| Metric | Value | n | Source | Repro |
|---|---|---|---|---|
| Eligibility waterfall | 15,763 / 15,763 / 0 | 15,763 | `results/phase_6/artifacts/t1_eligibility.json` | `.venv/Scripts/python.exe -m research.phase_6.t1_eligibility` |
| Dev-tier verify | 0.68s, 0/0 integrity, 0/56 sidecar mismatch | 56 | `results/phase_6/artifacts/t2_dev_pipeline_summary.json` | `.venv/Scripts/python.exe -m research.phase_6.t2_dev_pipeline` |
| Full pass | 22.04 min, 30,309,950 rows | 15,763 | `results/phase_6/artifacts/t3_full_pass_summary.json` | `.venv/Scripts/python.exe -m research.phase_6.t3_full_pass` |
| Min-window medians | 20 / 72 / 183 min | 15,763 | `results/phase_6/artifacts/t4_measurements_summary.json` | `.venv/Scripts/python.exe -m research.phase_6.t4_measurements` |
| Minutes-to-50%-move | 52 / 57 (ratio 1.10×) | 15,763 | `results/phase_6/artifacts/t4_measurements_summary.json` | same as above |

**Filter waterfall:** `momentum_events_canonical` → D1 (`in_scope=TRUE AND source_file='file1'`, 15,763) → T=0-eligible (15,763, non-binding) → `event_minute_bars_v1` (30,309,950 rows, all offsets; 5,192,383 at T=0) → per-minute grid (6,128,310 rows) → concentration curves / min-window stats / opportunity decay (15,763 events each).

**Environment:** `.venv` — duckdb 1.4.4, pandas, numpy, `pandas_market_calendars` 5.4.0 / `exchange_calendars` 4.13.2 (matches config pin exactly), plotly 6.5.2, kaleido.

---

## 8. Output files

| File | Status |
|---|---|
| `prompts/phase_6.md`, `config/phase_6.json` | committed |
| `research/phase_6/*.py` (11 scripts) | committed |
| `results/phase_6/artifacts/*.json` (4 summaries + t1 eligible-events list) | committed |
| `results/phase_6/artifacts/*.parquet` | gitignored, regenerable |
| DuckDB table `event_minute_bars_v1` | materialized (all 7 offsets) |
| `results/phase_6/charts/01–05*.html` + `index.html` | committed |
| `results/phase_6/digest.json`, `REPORT.md` | committed |

### Commits (`phase-5a-approved..HEAD`)

T0 branch/prompt/config + dev v4 verification · T1 eligibility waterfall · T2 dev-tier pipeline · T3a pre-run commit · T3b full pass · T4 measurements · T5 charts + index · T6 digest/REPORT (this commit).

---

## Approval Gate

Do not begin Measurement 2 scoping or any use of these numbers in labeling/detector work until Cooper has reviewed the charts and given explicit approval. On approval, tag `phase-6-approved`. The latency budget number (minutes to 50% of the day's move) is set by Cooper from chart 04, not by the agent.
