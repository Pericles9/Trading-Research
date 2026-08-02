# Amendment A10.1 — Phase 8 resumption from T4c (escalation row 7, 09:00 anchor)

**Date:** 2026-08-01
**Branch:** `phase/8` (continues; do not re-cut)
**Baseline:** Phase 8 T0–T3 complete and committed; T4 computation complete; hard stop at escalation row 7
**Approved by:** Cooper, 2026-08-01
**Scope:** three changes only — 09:00 anchor disposition, escalation row 7 threshold, `flag_possible_row_cap` added to the carried-flag set. **No other element of `prompts/phase_8.md` is modified.** Everything not named below stands as written.

---

## 1. Why the stop was correct

Escalation row 7 fired at 11.04% on the 09:00 anchor and the agent stopped without attempting a fix. That is the discipline working. The threshold was set at 10% as a tripwire to force this decision, not as a limit derived from the data — and it forced it.

The 1,740 events are a **real coverage fact**: no T0 print at or before 09:00 in genuinely illiquid early-premarket names. Not a v2 defect, not an anchor construction bug. T0b already cleared v2's structural coverage.

---

## 2. A10.1a — 09:00 anchor retained, with a population guard

**Decision: retain.** T1 established that T0 premarket carries a median 0.64 share of `realized(09:30)` — the largest of the three components. The 09:00 anchor is the only clock anchor sitting inside that segment. Removing it removes the sole decision point touching where most of the pre-open move occurs.

Retention is conditional on all four of the following. They exist because the hazard is **not** the 11% — it is that chart 04 places anchor on the x-axis, so a column covering 89% of D1 sits beside columns covering ~99%, and the 1,740 absent events are systematically the thinnest names. Read left to right without a guard and a population change reads as an effect of entry timing.

- A10.1a-i — **Explicit denominator.** The 09:00 anchor reports **n=14,023** wherever it appears — grid cells, tables, chart annotations, digest. It never inherits D1's 15,763. Any table row carrying a 09:00 figure carries its own n.
- A10.1a-ii — **`has_premarket_print` becomes a carried label, not an exclusion.** Add to the T5 output a boolean per event. The 1,740 are labelled `has_premarket_print=FALSE`, dropped **only** from the 09:00 column, and present as normal at every other anchor. They are never dropped from the grid.
- A10.1a-iii — **Free comparison, report it.** At the `rth_open` anchor — where both groups are defined — report the markout distribution split by `has_premarket_print`, with per-group n. Description only.
- A10.1a-iv — **Chart 04 inline annotation (Cooper's call, 2026-08-01).** The 09:00 column carries an inline visual marker — hatched cell borders plus a column-header annotation reading the n and the excluded count. **No separate chart 04b.** The marker must be legible without hover. Chart contract row 04 is amended below.

---

## 3. A10.1b — Escalation row 7 threshold raised to 15%

Row 7 changes from `> 10%` to `> 15%` for clock anchors. It stays live: a clock anchor undefined for more than a sixth of the universe should still stop the phase.

The raise is **conditional on A10.1a-i and A10.1a-iv being implemented**. A higher tolerance for population divergence is only acceptable when the divergence is stated on the artifact.

Cooper may override the raised threshold at the gate if the resumed run surfaces a second anchor near the boundary. No anchor other than 09:00 is above 1.31%, so this is not expected.

---

## 4. A10.1c — `flag_possible_row_cap` added to the carried-flag set

T2b found exact round-number T=0 print counts: **50,000 ×2, 100,000 ×5, 200,000 ×1 — 8 events total.** ARBB lands on exactly 100,000 on one event and exactly 50,000 on another. This moves the ARBB item from "mechanism undetermined" to a near-confirmed collector row cap.

Two live consequences for this phase:

- A capped session is **truncated at the end**, so `v0(τ)` is correct at early anchors and understated at open+120 and t0_close → the event lands in a **lower participation quintile than it belongs in**.
- The **t0_close price for a capped event is the price at the cap, not the session close** — and t0_close is the flagship markout horizon. That is a contaminated return.

n=8, so aggregate impact is nil. Handled the same way as the 7 dup-print events:

- A10.1c-i — Define `flag_possible_row_cap` in `canonical.py` (per the A9.3 prospective standard: flag formulas defined once). Definition: T=0 print count exactly equal to any of {50,000, 100,000, 200,000}. Frozen — no fuzzy matching, no ±tolerance.
- A10.1c-ii — Add to T5d's carried-flag list. Own labelled row in the flagged-population table, never merged into quintiles.
- A10.1c-iii — One-line with/without sensitivity on the flagship cell (t0_close horizon), same treatment as the dup-print 7.
- A10.1c-iv — Root cause remains **out of scope**. Register as an open item; do not attempt here.

---

## 5. Resumed task checklist

T0–T3 and the T4 computation are complete and committed. Resume at T4c. All original Phase 8 constraints stand — **scan-free, D4, flag-never-delete, no recommendations.**

- A10.1-T0 — Commit `prompts/phase_8_amendment_10.md` and the updated `config/phase_8.json` before any other work. Config changes: escalation row 7 threshold 10 → 15; `flag_possible_row_cap` round-number set; `has_premarket_print` label enabled. **No re-run of T0–T3.**
- A10.1-T1 — Backfill `has_premarket_print` (from `t4_anchors.parquet`, no recomputation of prices) and `flag_possible_row_cap` (from `t2_row_cap_scan.json`). Join both into the anchor grid. Confirm counts: **1,740** and **8**. If either differs, hard stop. Commit.
- A10.1-T2 — T4c: rung attrition, chart 07. Every rung reported; none selected/recommended/preferable (row 10 live). Commit.
- A10.1-T3 — T5: markout grid (T5a–T5e) with deltas: 09:00 column n=14,023; `has_premarket_print` and `flag_possible_row_cap` in T5d carried-flag list; new `rth_open` split by `has_premarket_print` (A10.1a-iii); with/without sensitivity for the 8 row-cap events at t0_close (A10.1c-iii); charts 04 (amended), 05, 06. Commit.
- A10.1-T4 — T6: survivorship count, chart 08. Report only. Commit.
- A10.1-T5 — T7: digest and report. Amendment + escalation in `decisions_log` with observed 11.04% and the threshold change. Commit; confirm clean.

---

## 6. Escalation Criteria (amended — replaces the original table)

| # | Condition | Threshold | Action |
|---|---|---|---|
| 1 | Tag `phase-6b-approved` absent | any | Hard stop |
| 2 | `event_minute_bars_v2` missing an offset, or extended-day coverage incomplete | any | Hard stop — **cleared at T0b, retained for audit** |
| 3 | Any full-table pass over `filtered_trades` / `filtered_quotes` | any | Hard stop — post before running |
| 4 | Read of a D4-quarantined spine numeric on any computation path | > 0 | Hard stop — post file and line |
| 5 | `participation_class='no_baseline'` share of D1 | > 5% | Hard stop — **cleared at 0.13%** |
| 6 | Same-clock baseline undefined at an anchor | > 20% | Not a stop — switch to `logrv_session`; **not triggered** |
| 7 | `anchor_undefined` at any clock anchor | **> 15%** (A10.1b) | Hard stop — post per-anchor rates. **09:00 at 11.04% now passes** |
| 8 | Any markout cell n | < 100 | Not a stop — hatch the cell, state no claim |
| 9 | Write outside `prompts/`, `config/`, `research/phase_8/`, `results/phase_8/` | any | Hard stop |
| 10 | Any rung, anchor, or threshold selected, recommended, or described as preferable on the basis of its markouts | any | Hard stop |
| 11 | Any bucketing variable used that is not knowable at the anchor timestamp | any | Hard stop |
| 12 | `has_premarket_print=FALSE` count ≠ 1,740, or `flag_possible_row_cap` count ≠ 8 | any | Hard stop — artifacts disagree with the reported run |

---

## 7. Chart Contract deltas

Rows 01, 02, 03, 05, 06, 07, 08 unchanged. Row 04 replaced; row 09 added.

| # | File | Question | Encoding | n shown | Looks like this if wrong |
|---|---|---|---|---|---|
| 04 | `charts/04_markout_heatmap.html` | Do forward returns vary with participation and entry timing? | Facet grid: rows=horizon, cols=era; x=anchor, y=participation quintile, colour=median markout. Cells with n<100 hatched. **09:00 column carries hatched borders and a header annotation stating n=14,023 and 1,740 excluded — legible without hover.** | Per-cell n printed in cell; 09:00 column n in the header annotation | Uniform colour across all cells in both eras |
| 09 | `charts/09_rth_open_by_premarket_print.html` | Do names with no premarket print behave differently once RTH opens? | Violin + strip of `rth_open` markout, split by `has_premarket_print`, faceted by era, zero-line marked | Per-group n above each violin | The two violins overlap almost entirely and medians are unordered |

---

## 8. Output Files (additions)

| File | Description |
|---|---|
| `results/phase_8/charts/09_rth_open_by_premarket_print.html` | RTH-open markout split by `has_premarket_print` |
| `results/phase_8/artifacts/a101_label_backfill.json` | `has_premarket_print` and `flag_possible_row_cap` counts + join provenance |

---

## 9. Reporting (additions to the original list)

12. **09:00 anchor block** — n=14,023, excluded 1,740, and the A10.1a-iii comparison at `rth_open` with per-group n
13. **Row-cap block** — the 8 events listed by ticker/date with exact print counts, and the flagship with/without sensitivity
14. **Amendment note** — escalation row 7 observed 11.04%, threshold changed 10% → 15%, both conditions of the raise implemented

Every claim cites its chart. **No recommendations, no characterisation of any result as good, promising, weak, or disappointing.**

---

## Approval Gate

Do not begin Phase 9 or any follow-on work until Cooper has reviewed the charts and given explicit approval. On approval, tag `phase-8-approved`.
