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

### A caveat on `p_randomwalk` — RESOLVED IN §12, kept here as the reasoning that motivated it

`p_randomwalk = m/(k+m)` is the touch probability for a driftless walk run **until a barrier is hit**.
This phase imposes an expiry, and **11.34%** of named-cell entries expire untouched. Expiry censors the
**far** barrier more than the near one, so `p_clear` is mechanically depressed relative to `m/(k+m)` by an
amount that grows with the barrier span. The comparison is therefore conservative in one direction only:
a cell *clearing* `p_randomwalk` despite expiry is evidence of drift, but a cell falling below it is not
evidence against.

Under the naive comparator, optimistic `p_clear` exceeds `p_randomwalk` in **27 of 90** cells and **all 27
have `m = 1`** — the smaller span, and therefore the smaller censoring. That pattern is what identified
the comparator rather than the tape as the problem. Expiry share by horizon (median): H=1 **0.479**, H=5
0.257, H=15 0.113, H=30 0.059, H=60 0.031.

> **RESOLVED IN §12.** An expiry-matched baseline was built. The matched comparator is **0.3867** against
> an observed **0.3621**, and `p_clear` sits below the driftless baseline in **0 of 30 cells**. The
> corrected reading is stronger than "does not pay": **there is no drift here to pay with.**

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

---

## 12. T3c — the expiry-matched baseline, and a miscalibration I caught in my own null

Ordered before the close-out because §5's drift sentence rested on a comparator known to be wrong in a
known direction. Artifact: `t3c_null_baseline.json`.

**The simulation.** A driftless walk matched on the barrier distances, the expiry horizon, and the
**minute-bar discretisation** — stepped at 10 s and reduced to a per-minute high and low, so first passage
is judged on bars exactly as it is on tape. Synthetic; no data pass beyond reading a volatility
distribution; no gate touched and no threshold moved.

### 12.1 The first pass was wrong, and its own diagnostic said so

Calibrating σ from the raw Parkinson estimator `ln(high/low)/(2√ln2)` gave a null that **expired 23.70% of
the time against the tape's 11.34%**. A null that quiet under-reaches its barriers, which depresses its
`p_profit_first` and therefore **overstates** the drift it exists to measure. It would have reported
*drift in 30 of 30 cells*.

The cause is known rather than mysterious: **Parkinson from a sparse minute bar is downward-biased**,
because with few prints the observed high–low range understates the true one. These are minute bars on
micro-cap tape; many carry a handful of prints.

**So the null is matched on the quantity that actually governs this comparison — the censoring.** A
volatility scale is swept and, per cell, interpolated to the scale that reproduces *that cell's own*
observed expiry share. Matched by construction rather than assumed.

### 12.2 The calibrated result — and it reverses the intermediate one

| named cell, k=3 m=2 H=30 L=5 | value |
|---|---|
| observed `p_clear` optimistic | 0.3621 |
| `p_randomwalk` **naive** `m/(k+m)` | 0.4000 |
| **`p_randomwalk` expiry-matched** | **0.3867** |
| `p_breakeven` | 0.6000 |
| expiry share, observed vs null | 0.1134 vs **0.1134** — matched by construction |
| ambiguity, observed vs null | 0.0249 vs **0.0291** — *not* calibrated on, agrees to 0.4 pp |

**Drift: no.** Observed sits **below** the expiry-matched baseline, and does so in **0 of 30 cells** —
against 9 of 30 under the naive comparator.

**The ambiguity agreement is an independent validation.** The null was calibrated on expiry share alone,
yet reproduces the observed R1 tie rate to within 0.4 pp. That is evidence the bar-discretisation and the
tie mechanism are modelled correctly, and it was not fitted.

### 12.3 What this corrects, stated plainly

Cooper's prior — *"it moves the comparator a few points and does not change the verdict"* — is **correct**
for the properly calibrated null: 0.4000 → 0.3867, a move of **1.33 points**, verdict unchanged. My
uncalibrated intermediate suggested the opposite and was wrong. The self-check that caught it was the
null's own expiry share disagreeing with the tape's, which is why the diagnostic was worth printing
alongside the result rather than only the result.

**The corrected §5 sentence:** `p_clear` is below the driftless baseline at every cell under a comparator
matched on censoring. Not merely "does not pay" — **on this unconditional entry universe, at minute
resolution, there is no drift to pay with.**

---

## 13. The RTH-fill restricted cut

The named cell is labelled by **detection** segment, so RTH-detected entries can fill in the post session
where the tape is thinner, and the headline averages two tapes.

| fill bar sits in | `p_clear` opt | `p_clear` pess | n | events |
|---|---|---|---|---|
| **rth** | **0.3624** | 0.3426 | 1,932,241 | 10,410 |
| post | 0.2895 | 0.2775 | 675,101 | 10,201 |

**Restricting to RTH fills moves the headline by +0.0003** — from 0.3621 to 0.3624 — because RTH fills are
74% of the cell. The two tapes do differ from each other by 7.3 points, so the concern was well founded;
it simply does not move the aggregate. **Row 12 is unaffected**, and this is a robustness line rather than
a re-read of a gate that fired.

---

## 14. A specification defect in this phase, recorded as one

**Arm 1's finest horizon is 1 minute and its finest latency is 1 minute. The strategy class this
programme is pursuing holds for seconds to a few minutes and acts in 1–3 seconds. That regime is not in
Arm 1's grid at all.**

The prompt says so itself — *"Arm 1's latency axis is coarser than achievable execution and therefore
pessimistic — Arm 2 carries the real axis"* — and Arm 2's grid is specified in **seconds** (latency
0.25–5 s, horizons 10–300 s). The second-scale question was then gated behind a minute-scale null.

**A gate of that shape is only valid if the cheap arm's negative implies the expensive arm's negative.**
Here it does not, because the two arms cover different regimes. The cost logic — gate the tick pass behind
the free pass — was sound; the horizon mismatch inside it was not.

This is a defect in the phase's design, not a limitation of its finding, and it is recorded as such.

**Two further bounds on what Arm 1 establishes:**

- It measures the **unconditional** base rate: entry at every bar. Beating that base rate is a detector's
  entire function, so row 12 firing on the null is not by itself evidence that conditioning cannot clear
  it. §7's two stratifiers already move `p_clear` monotonically without any detector at all.
- Everything here is minute-resolution. Nothing in it speaks to the second scale.

---

## 15. The bar Arm 2 would have to clear, stated before it runs

| quantity | value |
|---|---|
| named cell, optimistic | 0.3621 |
| break-even | 0.6000 |
| **required conditional lift** | **+23.8 points** |
| best single observed stratum (0–14 min since anchor) | 0.4268 — still **17.3 short** |
| naive additive stack of both stratifiers | 0.5043 — still **9.6 short** |

The stack assumes independence *and* zero overlap between the two conditioners. Early bars are plausibly
also faster-resolving bars, so they overlap and **0.5043 is an upper bound on a stack that will not be
achieved**.

**So: Arm 2 must find roughly 24 points of lift where crude stratification found 8, with full lookahead to
find it.** Stating that in advance is what stops a marginal Arm 2 result being read as vindication — and
it is what an oracle ceiling is for. If an oracle with lookahead cannot close a 24-point gap, nothing
causal will, and the timing-detector line closes on evidence rather than on a horizon mismatch.

---

## 16. Close-out

**Established.** On the archive's RTH events, **unconditional minute-resolution entry**, at 1–5 minute
latency and 1–60 minute holds, under a 3:2 barrier scheme against a 71 bp round trip: `p_clear` does not
reach break-even at any of 90 cells, closest gap −0.210, both denominators on the same side. Under a
driftless null matched on censoring, `p_clear` is below the baseline at every cell — **there is no drift
to pay with at this resolution on this entry universe.**

**Not established.** Anything at the second scale. Anything conditional. The two are the same gap, and
Arm 2 is where both live.

**Two positive findings that should not be lost in a negative phase:**

1. **Conditioning moves `p_clear` monotonically in both stratifiers** — +8.5 points across path position,
   +7.8 points across `s_min`, with non-overlapping CIs at the extremes in each.
2. **`s_min` relates to forward excursion.** Chart 05's pre-registered failure appearance was a flat line,
   meaning `s_min` is an estimability gate only. It is not flat. This is the first time in this programme
   that a timing statistic has been connected to price at all — six versions of Phase 10 did not get
   there.

**The stop stands.** Arm 2 is unauthorised. Authorising it is a numbered decision with its reasoning on
the record, in the manner of D21, D22 and D23 — not a re-read of a gate that has already fired.

**What must not happen:** re-running Arm 1 with different barriers to find a cell that clears. 90 cells is
already a wide sweep, the closest gap is 21 points, and searching for a passing cell after a gate fires is
the failure this programme has spent six phases learning to avoid.

---

## 17. T4b — the horizon gradient, and it refutes the argument for Arm 2

Run at Cooper's instruction **before** D24 was taken, because §14's horizon-mismatch defect was used as an
argument *for* spending a tick pass and the evidence for or against it was already on disk. Artifact:
`t4b_horizon_gradient.json`. No new computation, no data pass, no gate touched — a re-cut of the committed
grid with latency, segment, denominator and barrier pair held fixed.

### 17.1 The derived cost argument

Round-trip cost is **fixed at 70.98 bp** and does not scale with the horizon. Typical price movement scales
roughly as **√H**. So the cost drag relative to the 30-minute named cell is `√(30/H)`:

| horizon | 30 min | 5 min | 60 s | 30 s | **10 s** |
|---|---|---|---|---|---|
| relative cost drag | 1.0× | 2.4× | 5.5× | 7.7× | **13.4×** |

**A 10-second hold faces roughly thirteen times the cost drag of the 30-minute hold that just failed.**
Shorter horizons are structurally *harder* against a fixed cost — so the minute-scale null was **generous**
to the second-scale case, not irrelevant to it. §14's defect is real in that the regimes differ; the
consequence runs the opposite way from how it was first stated.

### 17.2 The measured gradient

Named cell's barrier pair (k=3, m=2), latency 5, RTH, print-weighted:

| horizon | 60 min | 30 min | 15 min | 5 min | 1 min |
|---|---|---|---|---|---|
| `p_clear` optimistic | 0.3745 | 0.3436 | 0.2973 | 0.2110 | 0.1192 |
| **gap to break-even** | **−0.2255** | −0.2564 | −0.3027 | −0.3890 | **−0.4808** |
| expiry share | 0.0814 | 0.1440 | 0.2425 | 0.4404 | **0.6716** |

**The gap more than doubles as the horizon shortens from 60 minutes to 1**, and the gradient runs the same
way in **6 of 6 barrier pairs**. The expiry share reaching 67% at one minute is the same effect seen from
the other side: at short horizons against a fixed cost, most cells carry no outcome at all.

**Extrapolating toward 10–300 seconds runs against Arm 2, not for it.** The free test refuted the argument
it was run to check, which is why it was run before the decision rather than after.

### 17.3 Two corrections to what Arm 2 would have been

1. **`s_min` is a rate statistic.** `s_min = 2.26/λ̂` is `λ̂` inverted, so §7's `s_min` stratification is
   **already a coarse, minute-resolution version of the rate-based selection Arm 2 would perform** — and it
   delivered **+7.8 points against a required +23.8**. A second-scale rate detector would need to be about
   **three times as selective**. Finer resolution should help; three-fold is a large ask.
2. **Arm 2's lookahead is in the rate channel, not in price.** It would see future *arrivals*, not future
   returns, so it bounds **this family of rate-based timing detectors** rather than what any strategy could
   achieve. A narrower ceiling than the phase prompt claimed, and the record now says so.

### 17.4 Disposition

**D24 taken: Arm 2 is declined and the timing-detector line closes** — on the derived cost-scaling argument
and the observed gradient, not on budget. Full text in `docs/Universe-Decisions.md`. Next free number:
**D25**.

**What is not closed:** the *conditional* question at the second scale is untested, and D24 does not assert
it is untestable. It asserts the available evidence says the extrapolation runs the wrong way. Reopening
requires a numbered decision, so a seventh attempt cannot arrive under a new name.

---

## 18. Post-close-out — Phase 8 and Phase 9 re-read against a cost stack that postdates them

Run at Cooper's direction after D24. **Not part of Phase 10e's gated tasks**; a re-cut of committed
artifacts, no tick pass, no new measurement, no gate touched. Artifact: `t5_costed_markouts.json`.

**It also replaces an extrapolation with a measurement.** The read after D24 projected Arm 1's
gap-to-break-even past its 60-minute ceiling on the flattest observed slope, giving −0.194 at 120 min,
−0.164 at 240 min and −0.142 at a full session — flattening short of zero. That arithmetic is confirmed
(last slope 0.1026 per log-decade; at that rate the gap reaches zero at **9,440 minutes, 24 full
sessions**). But **Phase 8's grid already carries `t0_close`, `t1_close` and `t3_close`**, so the horizon
axis does not need extrapolating at all.

### 18.1 The comparison

A long trade held from the detection anchor to a horizon earns its markout and pays one round trip, so it
clears when `markout > 70.98 bp`. Reported as a **share**, defined on every event.

| latency | horizon | share clearing | 95% CI (event-clustered) | median markout | gap to cost |
|---|---|---|---|---|---|
| 0 | det+5 | 0.3538 | [0.346, 0.362] | −46.1 bp | −117.1 bp |
| 0 | t0_close | 0.3640 | [0.357, 0.371] | −350.6 bp | −421.6 bp |
| 0 | t1_close | 0.3485 | [0.341, 0.356] | −641.8 bp | −712.8 bp |
| 0 | t3_close | 0.3424 | [0.335, 0.350] | −885.5 bp | −956.5 bp |
| 5 | t0_close | 0.3835 | [0.376, 0.391] | −249.5 bp | −320.5 bp |
| 30 | det+60 | 0.3820 | [0.374, 0.389] | −41.3 bp | −112.3 bp |
| **30** | **t0_close** | **0.4270** | **[0.419, 0.435]** | **−96.8 bp** | **−167.8 bp** |
| 30 | t3_close | 0.3724 | [0.365, 0.380] | −625.4 bp | −696.4 bp |

**In 0 of 29 cells does more than half of the population clear one round trip.** The best cell anywhere —
latency 30 min, hold to the T=0 close — clears on **42.7%** of events with a **median markout of −96.8 bp**,
which is 167.8 bp short of cost.

### 18.2 The day-scale case does not rescue it; it is worse

**The median markout is negative at every latency and every horizon measured**, and it becomes *more*
negative as the horizon lengthens: −46 bp at det+5, −351 bp at the T=0 close, −642 bp at T+1, **−886 bp at
T+3** (latency 0). The median event is down roughly 9% three days after its detection anchor, before any
cost is charged.

**This reconciles with Arm 1 rather than contradicting it, and the reconciliation is the interesting
part.** Arm 1's `p_clear` *rises* with horizon while Phase 8's markout *falls* with horizon, because they
are different exit rules on the same paths: a longer hold gives more opportunity to **touch** a +213 bp
barrier somewhere along the way, while the price **at** the horizon keeps decaying. Both statistics point
the same way about the strategy class — one never reaches break-even, the other is negative throughout —
but only reading them together shows why.

### 18.3 Two patterns worth recording

**Later entry is better, monotonically.** At the T=0 close the share clearing rises 0.3640 → 0.3727 →
0.3835 → 0.4068 → **0.4270** as latency goes 0 → 1 → 5 → 15 → 30 minutes. Waiting longer before entering
improves the outcome at every horizon, which is the signature of entering a fade later and therefore
lower. It is also the opposite of what a latency axis usually shows, and it is why latency 0 being
*physically impossible* matters less here than it would elsewhere.

**A12 makes the result slightly worse, not better.** Removing `flag_cross_session_extreme` events at
`t1_close` moves the share 0.3615 → 0.3376 and the median −575.1 → −655.0 bp; at `t3_close`, 0.3535 →
0.3335 and −790.9 → −870.1 bp. The flagged set was mildly flattering, so the conclusion is robust to the
boundary flag rather than resting on it.

### 18.4 Path-risk context from Phase 9, attached

Median `retrace_excursion` at the T=0 close is **0.381** (RTH) and **0.615** (premarket) — the median event
gives back 38–62% of its excursion by the close, rising to 0.493 / 0.696 by T+1. So the negative markouts
above are not a thin tail dragging a mean: the central case is a substantial give-back.

### 18.5 What this establishes

**The thesis does not clear 70.98 bp at any horizon measured — intraday or multi-day, at any latency, on
either exit rule.** Arm 1 covered 1–60 minutes under barriers; this covers 5 minutes to three sessions
under hold-to-horizon. Neither clears, and the day-scale end is the worse of the two.

**What it does not establish:** anything conditional. Every number here is unconditional, and §7's
stratifiers moved `p_clear` by 8.5 and 7.8 points without any detector. This is a base-rate result.

**Two standing caveats bound it, both already on the register:** the archive under-samples events whose
move lives outside RTH (**31.9%** of session highs sit outside it, post and premarket equally at 15.9%),
and the live false-positive rate remains unmeasured and blocked on data acquisition.

---

## 19. The adverse tail, read from the short side

Run before any sign-reversed capture figure is repeated anywhere, because the median is the wrong
statistic for a position with bounded gain and unbounded loss. Artifact: `t6_adverse_tail.json`.
**This section reports distributions. It does not compare the two directions and does not characterise
what it finds.**

Sign convention: a long's markout `m` is a short's loss of `+m`, so the short's adverse tail is the
**right** tail of markout, and the short's adverse **excursion** is the long's MFE. Stop levels are in
round-trip multiples: 1× = 71 bp, 2× = 142, 3× = 213, 5× = 355, 10× = 710 bp.

### 19.1 Terminal tail — Phase 8 markout, latency 5, untrimmed

| horizon | median | p90 | p95 | p99 | worst observed | >2× | >5× | >10× |
|---|---|---|---|---|---|---|---|---|
| det+15 | −63 | 741 | 1,276 | 2,996 | 12,983 | 0.297 | 0.192 | 0.105 |
| det+60 | −190 | 1,152 | 2,073 | 5,102 | 14,638 | 0.320 | 0.241 | 0.155 |
| t0_close | −250 | 1,905 | 3,094 | 7,254 | 32,453 | 0.360 | 0.301 | 0.222 |
| t1_close | −575 | 2,292 | 3,815 | 9,065 | 43,316 | 0.345 | 0.303 | 0.247 |
| **t3_close** | **−791** | **2,877** | **4,574** | **10,857** | **44,768** | 0.344 | 0.310 | **0.262** |

All figures in bp. At T+3 the p99 adverse outcome is **10,857 bp** against a median of −791, and the worst
observed is **44,768 bp — a 448% adverse move**.

**The tail is not a boundary artifact.** The six worst events are **none of them** `flag_cross_session_extreme`:
UCAR 2024-03-28 (+44,768 bp), XPON 2024-10-08 (+44,089), SINT 2022-12-19 (+41,504), HSCS 2024-05-16
(+41,162). Removing the A12-flagged set moves p99 from 10,857 → 8,978 and the >10× share from 0.262 →
0.239; the worst observed is unchanged.

### 19.2 Path tail — the binding one

A position is not held to the horizon if it is closed first, so what governs survival is the **maximum
adverse excursion inside the horizon**. Phase 10e's own T2 table, RTH, latency 5:

**Entries within 14 minutes of the detection anchor:**

| H (min) | median | p90 | p95 | p99 | worst | >2× | >5× | >10× |
|---|---|---|---|---|---|---|---|---|
| 1 | 101 | 452 | 648 | 1,250 | 7,611 | 0.403 | 0.146 | 0.042 |
| 5 | 176 | 741 | 1,083 | 2,062 | 12,532 | 0.564 | 0.275 | 0.106 |
| 15 | 267 | 1,144 | 1,707 | 3,457 | 25,772 | 0.679 | 0.407 | 0.197 |
| **30** | **342** | **1,492** | **2,245** | **4,768** | **31,905** | **0.736** | **0.488** | **0.266** |
| 60 | 434 | 1,916 | 2,848 | 6,283 | 37,143 | 0.782 | 0.562 | 0.341 |

**Over all entries** (not only those near the anchor) the same distribution is materially lighter — at
H=30, median 214 vs 342, >10× share 0.139 vs 0.266.

**Two readings of that difference, both stated as measurement:**

- The path tail is **heavier than the terminal tail at every comparable point**, because it takes the
  maximum rather than the endpoint. At H=30 near the anchor, 26.6% of entries see an adverse excursion
  above 710 bp; the terminal distribution at det+30 puts 13.5% above the same line.
- **Entries near the anchor carry the heavier tail.** That is the same fact §18.3 recorded from the other
  side — later entry was monotonically better there — and it is the second independent statement that the
  minutes immediately after detection are the most violent part of the path.

### 19.3 What this does and does not settle

**Settled:** the adverse distribution is heavy-tailed at every horizon and every entry position measured,
the tail is not explained by the cross-session flag, and the shares breaching every plausible stop level
are large — 73.6% breach 2× round trip within 30 minutes of the anchor, 26.6% breach 10×.

**Not addressed here, and each can close the question independently:**

- **Locate availability**, which is binary, unmeasured, and a capability question rather than a research
  one.
- **Halt risk**, which is asymmetric against a short because the adverse direction is the unbounded one.
  Phase 12 is specified and drafted and has not run.
- **Reg SHO 201**, unmodelled. Most of the day-scale adverse mass sits at T+1 and T+3, where it is live.
- Every standing caveat on the register, with the sign reversed — notably that a name which halts and
  delists **leaves the sample**, and those are cases a short would be in.

