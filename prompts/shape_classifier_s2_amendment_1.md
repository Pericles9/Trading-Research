# Shape classifier S2 — Amendment 1: clear row 3, fix the crossing, predict what is left of the path

**Date:** 2026-09-29 · **Amends:** `prompts/shape_classifier_s2.md` after the HARD STOP at T5, commit
`92c99cc` on `explore/shape-classifier-s2`. Rulings R1–R5 stand as recorded in the report.

---

## A1.1 Row 3 is cleared — the gate applies to the flexible model

The positive control exists to prove the pipeline can see a leak when one is present. **M3 scores 1.000
in every cell with the rule inputs added**, so the pipeline sees the leak. The seven failing cells are
all M2 (logistic regression), balanced weights, type chop. Chop is the rules' leftover region
("everything else"), cut out by several thresholds at once, and a linear model under strong shrinkage
(C = 0.1) cannot draw that region exactly, even with the answer as an input. That is a property of the
model form, not a leak the pipeline missed.

**Row 3, revised:** M3 must reach AUC ≥ 0.95 in every cell; M2 is reported beside it, ungated. It is
cleared on the committed run. No re-run is needed for this item.

## A1.2 Fix the minute-bar crossing

Call `first_crossing` on the full arrays, as b1 did, so the 04:00 print is judged against its
predecessor. It affects the R1 `tcs_state` input only, 66 events. It is fixed before the re-run in A1.5.

## A1.3 The label at checkpoints after τ: predict what is left, not the whole path

**The design flaw is mine, in the brief.** At a checkpoint after τ, the label (the whole post-τ type)
already includes whatever happened between τ and the checkpoint. A model can then score well by
*recognising* what has happened rather than predicting what comes next. The report shows this directly:

- The top inputs after τ are **return so far**, **where the high came** and **the move in noise units**:
  the path describing itself.
- **Money moves the wrong way as AUC rises.** Burst, M3 top decile, median net forward return:

  | horizon | τ | τ+1m | τ+2m | τ+5m | τ+10m | τ+20m |
  |---|---|---|---|---|---|---|
  | +30 min | **+126** | +94 | −231 | −272 | −348 | −419 |
  | all test events, +30 min | −243 | −250 | −214 | −179 | −164 | −122 |
  | to 20:00 | −225 | −665 | −1,284 | −1,371 | −1,624 | −1,822 |
  | all test events, to 20:00 | −431 | −411 | −379 | −340 | −299 | −241 |

  By the time a burst is recognisable, what is left of it is mostly the give-back.

**Revised labels:**

- **Primary, at every checkpoint after τ: the remaining-path type.** Apply S1's rules unchanged to the
  path from the checkpoint's entry (the next print after the decision time) to 20:00. That means N = 100
  equal-volume buckets over the remaining path, `σ_path` from its own bucket returns, and its own
  200-draw shuffled null.
- **Secondary: the whole-path type**, as run, reported beside it so the difference is visible.
- At τ the two labels are the same by construction. The τ results stand as run.

The positive control at each checkpoint uses the remaining-path rule inputs.

## A1.4 Put uncertainty on the money figures

For each type's top predicted decile at each decision time, report **ticker-bootstrap 95% intervals**
for:

- the median net forward return;
- **the difference against all test events at the same decision time**, which is the number that matters;

with all three entries (next print, +1 s, +5 s) and both cost units. Also report bottom-decile figures.
Being confidently *not* a burst, or confidently exhausted, is a skip signal, and its value is the same
kind of difference.

## A1.5 What re-runs, and where it stops

- **Re-run:** T2 (the A1.2 fix), T3 (the remaining-path labels built per checkpoint), and T4–T8 for both
  labels.
- **Unchanged:** models, tuning grid, folds, controls (re-run for the new label), escalation rows 1, 2,
  4, 5 and 6, and row 3 as revised in A1.1.
- Stop after the report, as before.

**Report additions:**

- AUC by time for both labels side by side;
- how often a checkpoint's remaining-path type differs from the whole-path type, per type;
- the A1.4 intervals.

## A1.6 A12 — recorded here, acted on separately

T0 established that `flag_cross_session_extreme` for the (T−1, T0) pair reads the event day's own last
trade. It flags 54% of runaways against 1–2.5% of exhausted, fade and chop. So **every earlier "with and
without the flagged set" split (32 files) was partly a split on the event day's own outcome**, not only
on corporate-action basis breaks. No committed code used it as a model input.

That calls for a retraction-sweep note. A proper corporate-action flag, built from the split records
rather than a price-move magnitude, would replace it. **Neither is part of this re-run.** They are listed
for Cooper as a separate item.
