# D9 Lineage — Close-Out Record

**Date:** 2026-08-27
**Deciding gate:** Cooper's visual review against the tape — **10d-R0 fired.**
**Decision recorded:** `docs/Universe-Decisions.md` **D21**
**Closes:** the threshold-from-trough method established by D9 and carried through
v4 → 10c → 10d → Diag1. **Does not close** the locally-normalized log-interval representation.
**Audience:** a fresh chat with no context.

This file is the close-out mechanics record and the carried-evidence index. The reasoning is
Cooper's close-out document; the decision text is D21. **Nothing here re-argues the verdict.**

---

## 1. What fired, and what that means

**10d-R0** — *Cooper rejects the decomposition on visual review against the tape* — fired on
2026-08-27. That row overrides every other result in either direction, and it fired **after**
the mechanical defects were found and fixed, not before. Every numeric escalation row in 10d
passed; the phase's own code raised nothing. The method failed the only criterion that was
ever able to fail it, which is the pattern Phase 10's own record notes has held across the
lineage.

The verdict is about the method, not about 10d: **there is no privileged valley to find.**
Diag1 measured that directly (§2).

---

## 2. The evidence the decision rests on

All figures re-verified against their committed artifacts on 2026-08-27 before D21 was
appended. Kernel 8 min unless stated.

| Finding | Value | Artifact |
|---|---|---|
| Frames carrying a boundary with ≥3 surviving peaks | **99.8%** (median 8 peaks, median 7 candidate troughs) | `phase_10d_diag1/artifacts/t4_tables.json` |
| Frames that are the two-peak case the void parameter presumes | **4 of 2,308** | same |
| Ladder gradient: median location, rank 0 → rank 8 | **4.449 ms → 153.887 ms (35×)**, void 0.893 → 0.488 | same |
| Median winner–runner-up void gap | **0.0511** | same |
| Winner relocation between adjacent frames sharing 87.5% of data | **>0.5 dec in 27.3%**, **>1.0 dec in 17.5%** (n = 2,303 pairs) | same |
| Candidates reaching 100 ms vs. winners reaching it | **26.53%** vs. **6.73%** | same |
| Cross-kernel log-log slope of winner location on kernel | **≈0.48** | same |
| Run breaks that are real above-threshold gaps | **99.24%** (n = 170,592) | `phase_10d/artifacts/t4_break_cause.parquet` |
| Merge tolerance effect on median duration | **+0.0838 decades** | `phase_10d/artifacts/t5_attribution.json` |

### 2.1 A correction to the close-out draft's scale figures

The draft states the window-basis fix moved median duration "349 ns → 1.75 ms, a factor of
~3,700." **Those are not a matched pair.** From the artifacts:

| Figure | Value | n | Cohort |
|---|---|---|---|
| v4 pooled median | **349 ns** | 114,074 | v4's 100-event analysis cohort |
| **10c** pooled median, all three kernels | **1.294 ms** | 170,722 | 56-event dev sample |
| **10d** identity cell, 8-min primary kernel | **1.751 ms** | 46,709 | 56-event dev sample |

349 ns → 1.294 ms is **≈3,707×**; 349 ns → 1.751 ms is **≈5,017×**. The draft's "~3,700"
belongs to 1.29 ms, not 1.75 ms. **The cohorts also differ**, so all three comparisons are
across populations rather than like-for-like. Corrected in D21. The conclusion is unchanged
either way — the result remains four orders of magnitude short of a tradeable scale.

---

## 3. Carried forward — evidence is not retracted by the method being closed

Per the same rule that preserved v3's scale-separation result under D9. Each of these remains
citable and none depends on threshold-from-trough being correct.

| # | Carried finding | Where it lives |
|---|---|---|
| 1 | **The clock-time centered window at 10c's specification**, and the finding that a window with no anchor in clock time cannot produce a clock-time answer — the 349 ns → 1.29 ms move | `config/phase_10c.json` `/settled/D3_window`; `results/phase_10c/REPORT.md` |
| 2 | **10d's attribution machinery and its result: assembly is not the cause of the scale.** The merge moved duration +0.0838 decades; the floor's apparent 7.17× was *deletion* of trivial objects, not lengthening, proved by the `n_prints` composition read | `results/phase_10d/REPORT.md` §6; `research/phase_10d/{assemble,t5_attribution}.py` |
| 3 | **The break-cause census — 99.24% of run breaks are real gaps, not data-quality artifacts.** First measurement of that split in the programme | `results/phase_10d/artifacts/t4_break_cause*.parquet`; chart 03 |
| 4 | **Diag1's frame pipeline**, reconciled exactly against 10c's committed boundaries (16/16, float equality) and asserted per-frame against `envelope_boundary()` on 9,605 frames | `research/phase_10d_diag1/t1_frames.py`; `artifacts/t1d_reconciliation.json` |
| 5 | **`plot_boundary_through_time.py`** — reusable for any distribution-through-time question, not tied to this method | `research/phase_10d_diag1/plot_boundary_through_time.py` |
| 6 | **The locally-normalized log-interval field itself** — legible, persistent, carrying band structure that moves through the session. D9's *representation* stands | `results/phase_10d_diag1/charts/boundary_through_time/` (108 event charts, 3 contact sheets) |
| 7 | **The three hash-reproducibility defects** — Stage 1's stale recorded hash; `cfg_hash()` line-ending sensitivity; config encoding sensitivity. **Open, and independent of this close-out** | `results/phase_10d/REPORT.md` §2.7; `results/phase_10d_diag1/REPORT.md` §8.4 |
| 8 | **10c's animation docstring/code divergence** — window width and per-frame peak detection both differ from what the docstring claims. Open | `results/phase_10d_diag1/REPORT.md` §8.3 |

---

## 4. What is *not* closed, stated so it is not blurred later

**The locally-normalized log-interval representation survives.** What is closed is
**collapsing that field to a single boundary per event.** D9's representation is good; D9's
operational instruction is what dies. D21 says this in its own text; it is repeated here
because the distinction determines what a successor phase may reuse.

**No downstream phase is newly blocked.** D13 had already re-anchored Phases 13, 14, 16 and 17
to detection time, clock time, or price-path events, and that re-anchoring stands. The one
consequence recorded in the phase map is **row 15 (Burst hazard function)**, whose input was
burst duration distributions: it is now blocked on a successor object definition rather than
merely unstarted.

---

## 5. Options for what follows — Cooper's call, recorded not chosen

The close-out document sets out three and states a preference. **This file records them; it
selects nothing**, and no work has begun on any of them.

- **(a) A latent-state model** — hidden semi-Markov point process (Tokdar et al. 2010). The
  only remaining approach that produces the burst *object* the trading thesis wanted. Larger
  build, new assumptions needing their own validation, untested on this data.
- **(b) Use the field directly** — take the distribution's shape at each moment as a state
  descriptor and test it against forward returns with Phase 8's existing markout machinery. No
  segmentation, no threshold, no free parameter. Abandons the burst as an object, and with it
  D5's and D8's framing.
- **(c) Stop.** Sub-burst decomposition is optional work at this point, not load-bearing.
  Phase 11 is unblocked and executable now.

Cooper's stated read is **(b)**, offered in his document as a view rather than a finding.

---

## 6. Close-out mechanics performed

| Item | Status |
|---|---|
| Append **D21** to `docs/Universe-Decisions.md`, append-only | ✅ 57 insertions, **0 deletions** |
| Digest for the tape review — 10d-R0's firing recorded as the gate | ✅ `results/phase_10d/digest.json`, `status: closed_gate_fired`, `gate_outcome.fired: true` |
| Digest for the diagnostic | ✅ `results/phase_10d_diag1/digest.json`, `status: complete_reviewed` |
| `docs/Claude-Code-Operating-Plan.md` §6 — mark the sub-burst line closed, insert only, renumber nothing | ✅ row 10 gate cell extended with a CLOSED annotation mirroring row 10b's existing pattern; one inserted note on row 15. **No row removed, none renumbered** |
| Fix `CLAUDE.md`'s decision pointer list | ✅ see §6.1 |
| Carry every §4 item forward | ✅ §3 above |

### 6.1 What was done to `CLAUDE.md`, and why it was fixed rather than deleted

The pointer list was stale at **D14** while the register ran to **D19**, and that staleness
already produced one near-collision: Phase 10d's spec drafted its decision as D15, straight
into Phase 11's committed D15, on the stated basis that "D1–D14 are taken."

Deleting the list would have removed the collision risk and the information with it. Instead
the list is now **complete through D21**, and three things were added to stop it going stale
again:

1. an explicit statement that **`docs/Universe-Decisions.md` is the authority and the list is
   not to be used to pick the next free number**;
2. **"Next free number: D22."**, so the number is stated rather than inferred;
3. a standing rule: **any phase that appends a decision updates this list in the same commit.**

A second stale entry was corrected at the same time. `CLAUDE.md` said
`docs/Claude-Code-Operating-Plan.md` "has never existed in this checkout." **It exists** —
added 2026-08-13 by Phase 10b at commit `edfb1ea`, 21,003 bytes, and §6 is the phase map this
close-out edits. The note was true when written on 2026-08-03 and went stale ten days later.

---

## 7. Verification

| Claim | Check |
|---|---|
| Every figure quoted in D21 | Re-verified against `t4_tables.json`, `t5_attribution.json`, `t4_descriptive_summary.json` before the append; 13 of 13 matched |
| D21 append is append-only | `git diff --numstat` → `57 0` |
| Operating Plan edit is insert-only | `git diff` shows exactly one removed line — row 10's gate cell, replaced by its extended self. No renumbering |
| Decision numbering | `docs/Universe-Decisions.md` enumerated by regex: D1…D21 present, no duplicates, next free D22 |
| Nothing else touched | working tree carries only the two deliberately-untracked chart directories |
