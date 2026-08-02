# Amendment A10.2 — Detection-anchored markouts, contamination test, and the false-positive question

**Date:** 2026-08-01
**Branch:** `phase/8` (continues; do not re-cut)
**Baseline:** Phase 8 complete through A10.1-T5; all artifacts committed; `phase-8-approved` **not yet tagged**
**Approved by:** Cooper, 2026-08-01
**Scope:** four additions. **No prior Phase 8 result is retracted, recomputed, or modified.** T0–T7 and A10.1 outputs stand exactly as reported. This amendment adds a tradeable-anchor grid alongside them and gates the tag on it.

---

## 1. Why this amendment exists

Phase 8's clock anchors (09:00, rth_open, open+N) assume the event is known to exist at the anchor timestamp. **It is not.** Live scanner mechanics surface a candidate only once intraday price has crossed **+30% from prior close**. Before that crossing, the ticker is one of several thousand and there is no signal to act on.

- **Every clock anchor before the crossing is a hindsight anchor.** It prices an entry that could not have been taken.
- **The Q1→Q5 gradient has a mechanical explanation that must be ruled out.** D1 membership is conditioned on a large T0 move occurring. Low pre-open participation means the move has not yet happened; the selection criterion guarantees it will; therefore more of it remains after the anchor. A monotonic decline in markout with rising pre-open participation is what that arithmetic predicts with zero forecasting content. Chart 09 shows the same mechanism a second time.

A10.2 does not assume the gradient is artifactual. It builds the test that separates the two readings, and it builds the anchor a live system could actually use.

---

## 2. A10.2a — Detection anchor construction

**Definition (frozen in config):** `det_anchor` = the first T0 extended-day minute at which the last trade price ≥ **1.30 × `tick_close_t_minus_1_rth`**.

- Tick-derived both sides (D4 stands; no spine prev_close).
- Extended day, not RTH.
- Price threshold only. The power-law filter is not applied at detection (§5).
- No smoothing, no confirmation bar, no minimum-volume qualifier (row 14).

- A10.2a-i — Coverage check: count/share of D1 whose tick-derived T0 extended max reaches 1.30 × anchor. Near-total expected; if not, tick threshold and Phase 1's `momentum_pct` disagree — that's the finding. Never-cross → `det_undefined=TRUE`, own row. Escalation row 13.
- A10.2a-ii — Detection-time distribution: ECDF of `det_anchor` time-of-day by session segment, n per segment. Chart 10.
- A10.2a-iii — Detection vs high: minutes from `det_anchor` to `day_high_ext` time, and log distance between the two prices. The runway measurement. Distribution. Chart 11.
- A10.2a-iv — Latency offsets: markout anchors at `det_anchor` + 0/+1/+5/+15/+30 min. Anchor price = last trade at/before. Zero-latency is a physical impossibility, included only as the upper bound — label as such on every chart.
- Commit.

---

## 3. A10.2b — Contamination test (the gate condition)

The single question: **does the participation gradient survive at an anchor with no remaining T0 hindsight?** `t0_close` is the only anchor where the entire T0 move — including the high that defined membership — is in the past.

- A10.2b-i — Markout grid, `t0_close → t1_close`, by participation quintile, by era, per-cell n/median/IQR + within-cell distribution.
- A10.2b-ii — Same for `t0_close → t3_close`.
- A10.2b-iii — Chart 12, matching chart 05's encoding.

**Reading rule (stated in advance):**

| Observation | Meaning |
|---|---|
| Gradient present and monotonic at `t0_close → t1_close` | Participation carries information the selection criterion does not already guarantee |
| Gradient flat or non-monotonic | The `rth_open` gradient is consistent with selection arithmetic; Phase 8's headline is not established as a forward edge |

The agent states which of the two the chart shows and nothing further. The persistence of the gradient at `t1/t3` horizons *measured from `rth_open`* is not independent evidence (those returns contain the T0 move). Only the `t0_close`-anchored version is a clean read.

- Commit.

---

## 4. A10.2c — Detection-anchored markout grid

- A10.2c-i — Horizons: `det+5`, `det+15`, `det+30`, `det+60`, `t0_close`, `t1_close`, `t3_close`, each measured from each of the five latency offsets. Signed log returns, sign kept.
- A10.2c-ii — Bucketing dimension: detection time-of-day (fixed bins: premarket / 09:30–10:00 / 10:00–11:00 / 11:00–13:00 / after 13:00). Participation at detection is not used (near-collinear with the anchor).
- A10.2c-iii — Era facet retained.
- A10.2c-iv — Carried flags: all five T5d populations + `det_undefined`. Own rows, never pooled.
- A10.2c-v — Charts 13 (heatmap) and 14 (distributions behind the flagship cell). Chart 14 mandatory.
- A10.2c-vi — Premarket detections reported separately, no liquidity claim.
- Commit.

The rung ladder (charts 06–07) is now secondary — a diagnostic, not extended.

---

## 5. A10.2d — The false-positive population

D1 contains no false positives; a live scanner fires on the +30% crossing alone and would surface rejected candidates too, which are not in this archive. Every markout is conditional on membership, not knowable at detection time.

- A10.2d-i — Recoverability check (read-only): whether the pre-filter candidate population survives on disk. Known candidates: `data/filtered/scanner_hit_catalog.json`, `data/filtered/filtered_events_power_law_q05.parquet`. Report contents, row counts, whether rejected candidates are carried.
- A10.2d-ii — If rejected candidates recoverable: count + implied acceptance rate at the crossing, by era. Stop there.
- A10.2d-iii — If not recoverable: register a standing limitation in `docs/Open-Items-Register.md` and reproduce verbatim in `REPORT.md`:

  > *All Phase 8 markouts are conditional on power-law filter membership. The filter was fitted on the full 2020–2024 panel and its output is not knowable at detection time. The rejected-candidate population is not present in this archive; the live false-positive rate is therefore unmeasured, and no markout in this phase can be read as a live expected value.*

- Commit.

---

## 6. Chart Contract (additions 10–14)

| # | File | Question | Encoding | n | Wrong-looks-like |
|---|---|---|---|---|---|
| 10 | `charts/10_detection_time_distribution.html` | When would the scanner fire? | ECDF of `det_anchor` time-of-day, one curve per segment, era as line style | n per segment; `det_undefined` in caption | all mass in one minute |
| 11 | `charts/11_detection_to_high_runway.html` | How much time/move remain after detection? | Panel A: ECDF minutes det→high. Panel B: ECDF log distance det→high. Era faceted | n per curve | Panel A concentrated near zero |
| 12 | `charts/12_contamination_test.html` | Gradient survive with no T0 hindsight? | Violin+strip of `t0_close→t1_close` by quintile, era faceted, zero-line. Encoding matched to chart 05 | per-quintile n | violins overlap, medians unordered |
| 13 | `charts/13_detection_markout_heatmap.html` | Returns vary with detection time & latency? | Facet rows=horizon cols=era; x=latency, y=detection bin, colour=median markout; n<100 hatched; zero-latency marked upper bound | per-cell n | uniform colour |
| 14 | `charts/14_detection_markout_distributions.html` | Distribution behind flagship detection cell? | Violin+strip at `det+5→t0_close` by detection bin, era faceted, zero-line | per-bin n | violins centred zero, overlapping |

---

## 7. Escalation Criteria (additions 13–16)

Rows 1–12 stand as amended by A10.1.

| # | Condition | Threshold | Action |
|---|---|---|---|
| 13 | D1 events whose tick-derived T0 extended max never reaches 1.30 × anchor | > 2% | Hard stop — tick threshold and `momentum_pct` disagree; post count + sample. Do not adjust the multiplier. |
| 14 | Any smoothing/confirmation/volume qualifier/multiplier ≠ 1.30 in the detection rule | any | Hard stop — detector construction |
| 15 | Any new collection/fetch/write against the data root during A10.2d | any | Hard stop — read-only |
| 16 | Any REPORT.md statement characterising the contamination-test result beyond which §3 row the chart matches | any | Hard stop before posting |

Row 3 (zero full passes over `filtered_trades`/`filtered_quotes`) remains live. A10.2 is scan-free against `event_minute_bars_v2`; A10.2d reads two small files and touches neither table.

---

## 8. Output Files (additions)

| File | Description |
|---|---|
| `results/phase_8/artifacts/a102_detection_anchors.parquet` | per-event det_anchor, latency offsets, prices, labels (gitignored) |
| `results/phase_8/artifacts/a102_detection_summary.json` | coverage, detection-time dist, runway, det_undefined n |
| `results/phase_8/artifacts/a102_contamination_test.json` | t0_close→t1/t3 grids, per-cell n/median/IQR |
| `results/phase_8/artifacts/a102_detection_markout_grid.parquet` | full detection-anchored grid (gitignored) |
| `results/phase_8/artifacts/a102_falsepositive_recoverability.json` | candidate files content; acceptance rate if derivable |
| `results/phase_8/charts/10–14*.html` | kaleido-verified |

---

## 9. Reporting (additions 15–21)

15. Detection coverage block — % crossing 1.30×, det_undefined n, row 13 status
16. Detection-time table — median/quartiles of det_anchor by segment, n
17. Runway table — minutes & log distance det→high, quartiles, by era, n
18. Contamination-test table — t0_close→t1_close by quintile×era, n/median/IQR, followed by one sentence stating which §3 row the chart matches and nothing more
19. Detection markout table — flagship det+5→t0_close by detection bin × era, n
20. Premarket-detection row, separately, no liquidity claim
21. False-positive block — disk findings; if unrecoverable, §5 limitation verbatim

No recommendations. No characterisation as good/promising/weak/disappointing.

---

## Approval Gate

**`phase-8-approved` is not tagged until A10.2 completes and Cooper has reviewed charts 11, 12, 13, and 14.** Chart 12 is the gate. Chart 11 sets the ceiling. The read is Cooper's.
