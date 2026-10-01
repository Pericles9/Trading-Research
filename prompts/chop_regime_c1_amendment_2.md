# Chop regime C1 — Amendment 2: put the efficiency ratio back in

**Date:** 2026-10-01 · **Amends:** `prompts/chop_regime_c1.md` as amended by Amendment 1, after the T9 stop at
`bcf6fbf` on `explore/chop-regime-c1`.
**Effect:** `er` returns to the suite's conditions. **Rebuild the suite only** (T8), from the committed T6
tables. No measure is recomputed. Commit, push, stop.

---

## A2.1 Why `er` was removed, and why that reading is wrong

Row 3b fired because the positive trend control missed in 2 of 100 midpoint cells (segment × rung × price
tier):

- after hours, rung 2, ≥ $10;
- regular hours, rung 10, $1–3.

In both cells **the null's 95th value is 0.99–1.00, which is the most `er` can be.** No injected drift can
clear a ceiling, so the miss says nothing about whether the instrument sees trend. It says that in those
cells, noise alone already fills the whole 0–1 scale. These are windows with so few midpoint moves that one
tick in either direction gives `er` near 1.

So the per-cell criterion in Amendment 1 was mis-specified at the ceiling, the same way the shuffle null was.
That is my error, not the instrument's. Read per rung, pooled over segments and tiers, the control passes in
24 of 24 rung-bases, and VWAP passes in all 101 gated cells.

**Ruling:** the positive control is read per rung. `er` is reinstated as a condition: `er` < x, at a chosen
rung or at every valid rung, per segment.

**What protects against the two ceiling cells:** panel B already draws each cell's null band. Where the band
reaches 1, an `er` slider can filter only by also filtering noise, and the picture shows it. **Add one
label:** in panel B and in the condition row, any cell whose null 95th value is ≥ 0.95 is marked "noise
fills the scale here". It is a label, not a rule. Nothing is excluded.

## A2.2 The bucket-dependence label on `er` is expected

`er` on pure noise scales about 1/√n, so its median halves from 16 to 64 buckets with no change in the tape.
The sweep's 20% rule could not pass for `er`; the brief should have said so. Keep the label, and add one line
to it in the suite: *"`er` is read only against its own 32-bucket null band; its level depends on the bucket
count by construction."* `cost_noise_h` passed the sweep and is unaffected.

## A2.3 One display change, after hours

After hours is 1.80M of 4.21M moment-minutes (43%), and 46.1% of its moment-minutes have no valid scale-free
rung. Pooled counts in panel A are therefore weighted heavily toward dead after-hours tape. **Panel A shows
per-segment counts first and the pooled total last**, in smaller type. Nothing else changes.

## A2.4 Unchanged

The 44% embedded sample (3,319 of 7,525 events, row 5) stands; C2 applies the committed config to all 7,525.
Every other result at `bcf6fbf` stands.

**Then stop.** Post the new file size and the config hash. The next step is Cooper's: set the filter, export
the config, commit it before C2 reads anything (§9).
