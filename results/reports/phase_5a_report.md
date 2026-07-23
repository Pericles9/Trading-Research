# Phase 5a — Dev Sample v4 Rebuild + Universe Decision Record — Report

**Branch:** `phase/5a` | **Baseline:** `phase-5-approved`

Description only, per the Evidence Standard — no recommendations. No analysis was performed this phase (per the phase objective); this report covers decision-recording and dev-sample construction only.

---

## 1. T1 — Universe decisions D1/D2

Recorded verbatim to `docs/Universe-Decisions.md`:

- **D1 — Analysis universe:** `in_scope=TRUE AND source_file='file1'`. file2 (5,188 events) excluded — separate collection process, ~100% not-full-window (Phase 5 T2/T4), registered 3-column-schema issue. Consequence: analysis date range ends 2024, no 2025 holdout for time-based splits. Expected frame: 15,763 events (15,349 clean, 414 flagged).
- **D2 — `clean_window` semantics:** an eligibility flag for window-dependent measurements, not a universe filter. No `clean_window=TRUE` filtering without the requesting phase naming the measurement that needs it; flagged events count as outcomes wherever outcome frequencies are reported (risk register #8, `docs/Mom-DB-Strategy-Research-Program.md` §8 — silent survivor filtering inflates T+1 results).

`docs/Open-Items-Register.md`'s implicit "2025 inclusion" question (open since Phase 2 T8) is formally closed, referencing D1. The separate "2025 T=0 data quality" item remains open on its own terms.

---

## 2. T2 — Sampling frame

| Check | Expected | Observed | Result |
|---|---|---|---|
| Frame total (D1 universe) | 15,763 | 15,763 | pass |
| `clean_window=TRUE` | 15,349 | 15,349 | pass |
| Flagged | 414 | 414 | pass |

Reconciled exactly against `spine_window_flags.parquet`'s own file1 figures (Phase 5 T4a): trades cohort 287, quotes cohort 386, overlap 259/28/127, union 414 — every check matches. Source: `results/phase_5a/artifacts/t2_frame_summary.json`.

---

## 3. T3 — Primary cohort draw (50 events)

**v3 sampling function located unambiguously:** `research/phase_3/build_dev_sample_v3.py`, lines 63–73 (`pd.qcut` deciles + `np.random.default_rng(42).choice` per decile pool, sorted-decile iteration order). Inline in `main()`, not a factored function — replicated verbatim in `research/phase_5a/t3_draw_primary.py:draw` rather than reimplemented from memory, per escalation row 2's requirement.

Drawn from the clean file1 frame (n=15,349), 10 deciles × 5 events, seed 42:

| Decile | n | momentum_pct range (sampled) | Pool size |
|---|---|---|---|
| 0 | 5 | 30.20 – 31.58 | 1,539 |
| 1 | 5 | 31.79 – 33.24 | 1,531 |
| 2 | 5 | 33.48 – 35.14 | 1,537 |
| 3 | 5 | 35.84 – 37.90 | 1,536 |
| 4 | 5 | 39.24 – 41.81 | 1,534 |
| 5 | 5 | 42.47 – 46.43 | 1,533 |
| 6 | 5 | 47.66 – 53.30 | 1,537 |
| 7 | 5 | 55.53 – 68.87 | 1,533 |
| 8 | 5 | 74.93 – 100.46 | 1,535 |
| 9 | 5 | 110.45 – 259.85 | 1,534 |

All 10 decile pools far exceed the 5-event minimum (smallest: 1,531 — escalation row 4 clear). Draw run twice within-process: byte-identical (escalation row 3 clear). Source: `results/phase_5a/artifacts/t3_primary_draw_summary.json`.

---

## 4. T4 — Flagged sidecar draw (6 events)

414 flagged file1 events span **54 distinct** combined (`trades_bitmap|quotes_bitmap`) patterns — well above 6, so the top-pattern-duplication fallback was not exercised. One event per pattern for the top 6 by frequency, seed 42:

| Ticker | Event date | momentum_pct | Pattern (trades\|quotes) | Pattern frequency |
|---|---|---|---|---|
| SLXN | 2024-08-19 | 31.79 | `0011111\|0011111` | 121 |
| APLD | 2022-03-28 | 45.24 | `1111111\|0000000` | 98 |
| ACET | 2020-09-18 | 32.84 | `0111111\|0111111` | 63 |
| RBC | 2022-09-26 | 44.21 | `0001111\|0001111` | 16 |
| NUKK | 2022-04-18 | 50.37 | `0111111\|0000000` | 8 |
| PSIX | 2022-11-15 | 74.86 | `0011111\|0000000` | 7 |

Draw run twice within-process: byte-identical (escalation row 3 clear). Never pooled with the primary cohort. Source: `results/phase_5a/artifacts/t4_sidecar_draw_summary.json`.

---

## 5. T5 — Materialize `filtered_trades_dev_v4` / `filtered_quotes_dev_v4`

56-event manifest (50 primary + 6 sidecar) joined through `momentum_events_canonical`'s key shape `(ticker, event_date, ROUND(momentum_pct,2))` against `filtered_trades`/`filtered_quotes` — spine join, never folder presence. `filtered_trades_dev_v3`/`filtered_quotes_dev_v3` untouched (escalation row 7 clear).

| Table | Cohort | Rows | Events |
|---|---|---|---|
| trades | primary | 9,545,832 | 50 |
| trades | flagged_sidecar | 92,529 | 6 |
| quotes | primary | 7,142,293 | 50 |
| quotes | flagged_sidecar | 107,057 | 3 |

**T5a — presence check:** 0/50 primary events missing either side (escalation row 5 clear). 3/6 sidecar events have 0 quotes rows (APLD, NUKK, PSIX) — not a failure: each of their drawn patterns is quotes-side all-missing (`...|0000000`), the documented non-failing case for the sidecar.

**Representative query timing:** effective spread (ASOF join to the prevailing quote — CLAUDE.md's "cross the spread, not quoted" standing rule) median by event, primary cohort: **17.1s** (ceiling 60s, escalation row 6 clear), covering all 50 primary events. Source: `results/phase_5a/artifacts/t5_materialize_summary.json`.

---

## 6. T6 — Representativeness chart

`charts/01_dev_v4_representativeness.html`: Panel A's step-ECDF (frame n=15,349 vs. primary cohort n=50) track closely with no visible departure; sidecar events (n=6) shown as position-only rug marks, clearly labeled, never pooled into either ECDF. Panel B's per-decile view shows the 5 sampled points in each decile spanning that decile's frame distribution rather than clustering. Visually verified via kaleido PNG render before commit.

---

## 7. Escalation check table

| # | Condition | Threshold | Observed | Result |
|---|---|---|---|---|
| 1 | Frame counts | ≠15,763/15,349/414 | 15,763/15,349/414 exact | pass |
| 2 | v3 sampling function not located | cannot cite path | located, `research/phase_3/build_dev_sample_v3.py:63-73` | pass |
| 3 | Draw reproducibility | any diff | byte-identical, both cohorts | pass |
| 4 | Decile with <5 clean events | n<5 | smallest pool 1,531 | pass |
| 5 | Primary event missing trades/quotes | any | 0/50 | pass |
| 6 | Dev-tier runtime | >60s | 17.1s | pass |
| 7 | Write to base tables/v3 dev tables/data root | any | none | pass |

No escalations triggered this phase.

---

## 8. Verification block

| Metric | Value | n | Source | Repro |
|---|---|---|---|---|
| Sampling frame | 15,763/15,349/414 | 15,763 | `results/phase_5a/artifacts/t2_frame_summary.json` | `.venv/Scripts/python.exe -m research.phase_5a.t2_sampling_frame` |
| Primary cohort draw | 50, 10/10 deciles | 50 | `results/phase_5a/artifacts/t3_primary_draw_summary.json` | `.venv/Scripts/python.exe -m research.phase_5a.t3_draw_primary` |
| Sidecar draw | 6, top 6/54 patterns | 6 | `results/phase_5a/artifacts/t4_sidecar_draw_summary.json` | `.venv/Scripts/python.exe -m research.phase_5a.t4_draw_sidecar` |
| Dev v4 materialization + timing | table in §5 | 56 | `results/phase_5a/artifacts/t5_materialize_summary.json` | `.venv/Scripts/python.exe -m research.phase_5a.t5_materialize_dev_v4` |

**Filter waterfall:** `momentum_events_canonical` (23,268 rows) → `in_scope=TRUE` (20,951) → `source_file='file1'` (15,763, D1) → `clean_window=TRUE` (15,349, primary draw population) / `clean_window=FALSE` (414, sidecar draw population) → primary draw (50, 5/decile×10) + sidecar draw (6, 1/pattern×top-6) → `filtered_trades_dev_v4`/`filtered_quotes_dev_v4` (9,638,361 / 7,249,350 total rows across both cohorts).

**Environment:** `.venv` — duckdb 1.4.4, pandas, numpy (`default_rng`), `pandas_market_calendars`/`exchange_calendars` not invoked this phase (no calendar arithmetic — the frame's `clean_window` etc. are carried columns from Phase 5, not recomputed).

---

## 9. Output files

| File | Status |
|---|---|
| `prompts/phase_5a.md` | committed |
| `config/phase_5a.json` | committed |
| `docs/Universe-Decisions.md` | committed (new) |
| `research/phase_5a/*.py` (5 scripts) | committed |
| `results/phase_5a/artifacts/*.json` | committed |
| `results/phase_5a/artifacts/*.parquet` | gitignored, regenerable |
| `results/phase_5a/charts/01_dev_v4_representativeness.html` | committed |
| DuckDB tables `filtered_trades_dev_v4`, `filtered_quotes_dev_v4` | materialized |
| `docs/Open-Items-Register.md` | updated (2025 inclusion item closed) |
| `results/phase_5a/digest.json`, `REPORT.md` | committed |

### Commits (`phase-5-approved..HEAD`)

T0 branch/prompt/config · T1 Universe Decisions D1/D2 · T2 sampling frame · T3 primary cohort draw · T4 flagged sidecar draw · T5 dev v4 materialization · T6 representativeness chart · T7 digest/REPORT (this commit).

---

## Approval Gate

Do not begin Phase 6 scoping or any analysis work until Cooper has reviewed results and given explicit approval. On approval, tag `phase-5a-approved`. Dev sample v4 is then pinned — it does not change for the remainder of the program.
