# Phase 10e — Does the path pay? Arm 1

**Type:** measurement phase, Arm 1 only. **Status: STOPPED AT THE T4 GATE — two hard stops fired.**
**Date:** 2026-09-02 · **Branch:** `phase/10e` · **Spec:** `prompts/phase_10e.md` ·
**Config:** `config/phase_10e.json`
**Arm 2 is not authorised and did not run.**

**The agent describes the picture; the read is Cooper's.** No recommendation is made and no result is
characterised as good, weak, promising or disappointing.

---

## 1. T0a — state, observed not asserted

| item | observed |
|---|---|
| branch | `phase/10e` |
| `phase-11-approved` | exists, `05ccbfc` |
| commits since the tag | 79 — **row 1b, not a stop**, recorded |
| working tree | dirty in one file only: `docs/Agent_Prompt_Standard.md`, Cooper's uncommitted v1.4 draft. Not phase work; 10e's row 1 does not stop on a dirty tree |
| `results/phase_11/digest.json` → `status` | **field absent** |
| `event_minute_bars_v2` | exists, **45,925,350 rows** — row 7 expects exactly that. **MATCH** |
| frozen artifacts (5) | all present; **all five match `frozen_baseline.json`** — row 1a passes |

**Row 1a was unsatisfiable as originally written** and was reworded in pre-flight: three of the five
frozen inputs are gitignored parquet and no digest records artifact content hashes, so the state at
`phase-11-approved` was never captured. The baseline verifies **forward only**; the tag period rests on
provenance — zero commits since the tag touched `research/phase_{8,9,10}/`, `config/phase_{8,9,10}.json`
or `src/`, and all three parquet mtimes predate the tag by 15–17 days.

## 2. T0d — satisfiability audit

**32 rows, four checks each: 29 pass, 3 deferred by design (2a, 5, 13 — all Arm 2, behind the T4 gate),
0 fail.** Row 3 does not fire. Artifact: `t0d_satisfiability_audit.json`.

The audit's first run **failed three rows** and was itself the hard stop that produced Cooper's
amendments: row 2 was unscoped and fired on Arm 2's slots; row 6 omitted the `momentum_pct` and A13
carve-outs and so fired on the phase's own T1c/T3b; and row 20's inline path list was narrower than
`config.write_allowlist`, so T8b's required report copy could not have been written without firing it.

---

## 3. T1e — the filter waterfall

| step | rows | events | reason |
|---|---|---|---|
| `event_minute_bars_v2`, all offsets | 45,925,350 | 15,763 | source |
| T=0 session only | 8,519,526 | 15,763 | `session_offset = 0` |
| inner join to D1 | 8,519,526 | 15,763 | `in_scope AND source_file='file1'` |
| join `a102`, drop `det_undefined` | 8,399,634 | **15,369** | 394 events carry no D7 anchor |
| bars at or after `det_minute` | **6,322,397** | 15,369 | T1b |
| bars with `n_trades = 0` | **0** | — | the table stores only bars that traded |
| **print-weighted denominator** | **6,322,397** | 15,369 | T1d(i) — what is actually enterable |
| event-equalised denominator | 606,351 | 15,369 | T1d(ii) — ≤ 40 bars/event, seed 42 |

**T1a-i, the anchor crosscheck — read, not re-derived (row 25).** `v2_r14_phase8_crosscheck.json`
reports **exact agreement, 110/110, share 1.0**, zero beyond tolerance, and the reference price agreeing
to within 1e−6 on all 110. The 60 s-poll comparison differs by exactly 1 minute on every event, which is
the floor-vs-ceil convention that artifact documents. **Row 25 does not fire; both arms resolve to
`a102`.**

---

## 4. The reading rules, with their observed values

| rule | observed |
|---|---|
| **R1** intra-bar ordering | Ambiguity is exactly the **tie rate** — both barriers first touched in the same bar, which is precisely where the bounds disagree. Named cell **2.49%**; range across the grid **2.09%–8.69%**. Both bounds reported everywhere |
| **R2** three outcome classes | Sum to 1 on every cell **under each bound separately — asserted in code**, not assumed. No win rate on touched-only entries is computed anywhere |
| **R3** no fill | Named cell **15.19%** — **row 11 FIRES**, see §6 |
| **R4** dead tape | Named cell **1.45%**; grid range 1.45%–2.07% |
| **R5** event dominance | Largest single event is **0.017%** of a cell against a 5% threshold. **0 of 90 cells** are event-dominated. Effective n reported on every cell |
| **R6** three numbers per cell | `p_clear`, `p_breakeven=(m+1)/(k+m)`, `p_randomwalk=m/(k+m)` — all three on every cell |
| **R7** thin cells | **0 of 90** cells fall below `min_cell_n = 100` |

---

## 5. THE T4 VERDICT

> ## Named cell: **`both_below`**

`print_weighted`, RTH, latency 5 min, horizon 30 min, **k = 3, m = 2**.

| quantity | value |
|---|---|
| `p_clear` **optimistic** | **0.3621**   CI(event) [0.3605, 0.3638] · CI(ticker) reported in artifact |
| `p_clear` **pessimistic** | **0.3372**   CI(event) [0.3357, 0.3387] |
| **`p_breakeven`** | **0.6000** |
| `p_randomwalk` | 0.4000 |
| three classes, optimistic | profit 0.3621 · stop 0.5245 · expiry 0.1134 |
| n | 5,632,168 · distinct events 15,288 · **effective n 10,359** |

Under the **event-equalised** denominator, never blended: optimistic **0.3561**, pessimistic **0.3328**,
n 495,983, effective n 14,493. Same side of break-even.

**Both bounds sit below break-even, so the bounds do not straddle it and row 10 does not fire.**

### The grid

**Optimistic `p_clear` is below `p_breakeven` in 0 of 90 cells.** Pessimistic likewise 0 of 90. The
closest any cell in either denominator comes to its own break-even is a gap of **−0.210** — `p_clear`
would have to rise by 21 percentage points.

Chart 02 shows every bar below its own red break-even line in every panel.

### A caveat on `p_randomwalk`, and it cuts against reading too much into it

`p_randomwalk = m/(k+m)` is the touch probability for a driftless walk run **until a barrier is hit**.
This phase imposes an expiry, and **11.34%** of named-cell entries expire untouched. Expiry censors the
**far** barrier more than the near one, so `p_clear` is mechanically depressed relative to `m/(k+m)` by
an amount that grows with the barrier span.

**Consequence: `p_clear < p_randomwalk` does NOT establish absence of drift.** The comparison is
conservative in one direction only — a cell *clearing* `p_randomwalk` despite expiry is evidence of
drift, but a cell falling below it is not evidence against. Observed: optimistic `p_clear` exceeds
`p_randomwalk` in **27 of 90** cells, and **all 27 have `m = 1`** — the barrier pair with the smaller
span and therefore the smaller expiry censoring. Expiry share by horizon (median): H=1 **0.479**, H=5
0.257, H=15 0.113, H=30 0.059, H=60 0.031.

Constructing an expiry-matched driftless baseline would settle it. **It was not built** — that is beyond
Arm 1 as specified, and it is logged as an open item rather than improvised at a gate.

---

## 6. The gate rows

| row | condition | observed | |
|---|---|---|---|
| 10 | bounds straddle `p_breakeven` on the named cell | `both_below` | **pass** |
| 10a | R1 ambiguous share > 0.25 — *reporting trigger, not a stop* | **0.0249** | pass |
| **11** | **R3 no-fill share on the named cell > 0.10** | **0.1519** | **FIRES** |
| **12** | **optimistic `p_clear` below `p_breakeven` at EVERY cell** | **0 of 90 clear** | **FIRES** |

### Row 11 — the distribution by segment, which the row requires posting

**By detection segment** (latency 5): post **32.40%**, rth **15.19%**, premarket 6.82%; pooled 10.92%.
At latency 1: post 27.69%, rth 13.19%, premarket 5.79%; pooled 9.41%. At latency 0 the share is **0.00%
by construction** — the fill bar *is* the entry bar, so latency 0 cannot register a no-fill, which
flatters it.

**By the entry bar's own segment** (latency 5), which locates the cause:

| entry bar sits in | no-fill | n |
|---|---|---|
| post | **27.28%** | 1,685,819 |
| rth | **5.27%** | 3,841,976 |
| premarket | 3.52% | 794,602 |

**By minutes since the anchor**, RTH-anchored events only, latency 5:

| band | no-fill | n |
|---|---|---|
| 0–29 | 5.84% | 290,029 |
| 30–59 | 7.13% | 275,222 |
| 60–119 | 9.39% | 509,365 |
| 120–239 | 12.84% | 870,788 |
| **240+** | **23.98%** | 1,128,960 |

So the named cell's 15.19% is not a property of RTH tape — **within RTH bars themselves the no-fill share
is 5.27%.** It is driven by entries far from the anchor whose fill minute falls in the post session,
where the tape thins. The entry universe as specified extends to the end of the extended day, and 240+
minutes past the anchor is where most of its rows sit.

---

## 7. Stratification

**Path position** (chart 04) — named cell's barriers, 95% event-clustered CIs, 2,000 reps:

| minutes since anchor | optimistic | pessimistic | n | events |
|---|---|---|---|---|
| 0–14 | **0.4268** [0.4230, 0.4303] | 0.3458 | 201,527 | 14,996 |
| 15–29 | 0.4086 [0.4047, 0.4126] | 0.3568 | 196,315 | 14,812 |
| 30–59 | 0.4009 | 0.3607 | 377,881 | 14,824 |
| 60–119 | 0.3824 | 0.3538 | 705,751 | 14,762 |
| 120–239 | 0.3682 | 0.3420 | 1,262,244 | 14,491 |
| 240+ | **0.3417** [0.3394, 0.3441] | 0.3261 | 2,888,450 | 13,424 |

**Monotone decline across all six bands**, with non-overlapping CIs between the extremes. Every band is
below break-even 0.600.

**`s_min` resolvability** (chart 05) — RTH only. This is the only place in Phase 10e where the
10-series' one surviving criterion is asked to relate to forward excursion:

| `s_min` band (s) | optimistic | pessimistic | n | events |
|---|---|---|---|---|
| [0, 0.5) | **0.3778** [0.3729, 0.3828] | 0.3373 | 306,510 | 6,231 |
| [0.5, 1) | 0.3556 | 0.3335 | 215,863 | 7,722 |
| [1, 2) | 0.3523 | 0.3338 | 278,089 | 8,895 |
| [2, 5) | 0.3550 | 0.3378 | 403,877 | 9,883 |
| [5, 10) | 0.3529 | 0.3377 | 322,220 | 10,067 |
| [10, 30) | 0.3383 | 0.3256 | 473,475 | 10,275 |
| [30, 100) | 0.3151 | 0.3045 | 381,538 | 10,241 |
| [100, ∞) | **0.3003** [0.2967, 0.3043] | 0.2908 | 225,770 | 10,070 |

**It is not flat.** The chart contract's failure appearance for chart 05 was *"flat — the one surviving
10-series criterion has no relationship to forward excursion, and `s_min` is an estimability gate only."*
`p_clear` falls **7.8 percentage points** from the fastest-resolving tape to the slowest, with
non-overlapping CIs at the extremes, and median MFE falls with it. The relationship is decreasing overall
though not strictly monotone — the four middle bands [0.5, 10) sit flat within ~0.3 pp of each other.
Every band remains below break-even.

---

## 8. Stopped here

**Two hard stops fired at T4. Arm 1 stops, Arm 2 is unauthorised and did not run.** Per the prompt:
state committed, observed values and charts posted, awaiting instruction. No parameter was adjusted and
no fix was attempted.

---

## 9. Escalation check — all rows

| rows | status |
|---|---|
| 1, 1a, 1a-i, 1b | pass — tag present, all five frozen inputs match the baseline, 79 commits recorded not stopped |
| 2 | pass — all five Arm 1 slots filled |
| 2a, 5, 13 | **deferred by design** — Arm 2, behind the T4 gate |
| 3 | pass — T0d 29/32 pass, 0 fail |
| 4 | pass — **zero** passes over `filtered_trades` / `filtered_quotes` |
| 6, 6a, 6b | pass — `momentum_pct` appears only inside the event key; no spine numeric on a computation path; no spine numeric in any committed artifact |
| 7 | pass — 45,925,350 exact |
| 8, 9 | pass — both R1 bounds on every first-passage number; no touched-only win rate anywhere |
| 10 | pass — `both_below`, no straddle |
| 10a | pass — 0.0249 against 0.25 |
| **11** | **FIRES — 0.1519 against 0.10** |
| **12** | **FIRES — 0 of 90 cells clear optimistically** |
| 14, 15 | pass — 0 event-dominated cells, 0 thin cells |
| 16 | pass — bp and cents together throughout |
| 17 | pass — no burst object, duration, timescale or quiet split appears |
| 18 | n/a — Arm 2 did not run |
| 19 | pass — T1 708 s, T2 436 s, T3 86 s, T3b 4 s; ceiling 3,600 s |
| 20 | pass — all writes inside `config.write_allowlist` |
| 21 | pass — no recommendation, no result characterised |
| 22 | pass — no decision appended; next free remains D24 |
| 23, 24 | n/a — Arm 2 |
| 25 | pass — one anchor, `a102`, both arms; crosscheck read not re-derived |

---

## 10. Verification block

| number | value | source | n / effective n | reproduce |
|---|---|---|---|---|
| candidate entries | 6,322,397 | `t1_waterfall.json` | 15,369 events | `research/phase_10e/t1_candidate_entries.py` |
| named-cell `p_clear` opt | 0.3621 | `t4_gate.json` | n 5,632,168 / eff 10,359 | `research/phase_10e/t4_gate.py` |
| named-cell `p_clear` pess | 0.3372 | `t4_gate.json` | same | same |
| `p_breakeven` | 0.6000 | `(m+1)/(k+m)`, k=3 m=2 | — | arithmetic |
| cells clearing optimistically | 0 of 90 | `t3_shares.parquet` | — | `research/phase_10e/t3_shares.py` |
| no-fill, named cell | 0.1519 | `t4_gate.json` | n 3,074,364 | `research/phase_10e/t4_gate.py` |
| ambiguous share, named cell | 0.0249 | `t3_shares.parquet` | n 5,632,168 | `research/phase_10e/t3_shares.py` |
| anchor agreement | 110/110 | `v2_r14_phase8_crosscheck.json` | — | read, not re-derived |
| `s_min` spread | 0.3778 → 0.3003 | `t3b_stratification.parquet` | per-band n in §7 | `research/phase_10e/t3b_stratification.py` |

**Runtime:** T1 708 s · T2 436 s · T3 86 s · T3b 4 s · charts 20 s. Well inside the 3,600 s Arm 1 ceiling.

---

## 11. Open items raised by this phase

1. **An expiry-matched driftless baseline does not exist.** `p_randomwalk = m/(k+m)` assumes no expiry,
   and expiry censors the far barrier more, so `p_clear < p_randomwalk` cannot be read as absence of
   drift. Constructing the matched baseline is the only way to read the drift question cleanly.
2. **Row 11's 15.19% is a property of the entry universe's reach, not of RTH tape** — 5.27% within RTH
   bars, 27.28% for entries whose fill minute lands in post. The universe as specified runs to the end of
   the extended day.
3. **`results/phase_11/digest.json` carries no `status` field**, which T0a asks for.
