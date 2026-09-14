# Impact by participation — closed, measured

**Governing prompt:** `prompts/impact_by_participation.md`. **Branch:** `impact-by-participation`
(cut from `phase/10e`, not `master` — see the prompt's own branch note). **Scope executed:**
T0–T4 (dev tier, read-only against frozen Phase 8/10e/11 artifacts), then, on Cooper's go-ahead,
T5–T6: the exact ordering-sensitive reclassification T1 flagged as needed, run against
`event_minute_bars_v2` (already-materialized, full universe — not a new pass over
`filtered_trades`/`filtered_quotes`), and the decisive comparison against T3's measured cost.

**Bottom line, stated once at the top:** closing the closest cell's gap requires round-trip cost
at or below **~11.0 bp — 15.5% of the 70.98 bp baseline**. The cheapest participation decile T3
measured is **50.7 bp, 4.6× that threshold. 0 of 10 deciles clear it.** No interpretation of what
this means for D24/D25 or candidate (b) follows (Evidence Standard) — stated as data.

---

## 1. Why this ran: the gate from `claude/what_would_change_a_decision.md`

A named decision (**D24, D25**), a threshold derived in advance (not chosen), both outcomes
informative. D24 and D25 rest on a flat **70.98 bp** round-trip cost
(`results/phase_11/artifacts/t7_cost_vs_capture.json`) treated as exogenous. This phase asked
whether realised cost conditional on how a trade is worked (its participation rate) is materially
lower — which would reopen the barrier-grid arithmetic — or not, which would harden D24/D25 from
provisional to final.

---

## 2. T1 — the threshold, and what it actually showed

**Closest cell:** Phase 10e Arm 1, latency 1 min, horizon 60 min, profit_k=3/stop_m=2. Measured
`p_clear_optimistic = 0.3885` against `p_breakeven = 0.6000`, gap **−0.2115**
(`results/phase_10e/REPORT.md` rounds this to "−0.210 / 21 points" — same cell, rounding only).

**What was derivable from already-materialized data, and what was not.** Barriers are built as
`profit_k × round_trip_bp` / `stop_m × round_trip_bp`
(`research/phase_10e/t2_excursion.py:60-63,155-156`), so `p_breakeven` is invariant to cost while
`p_clear` is not — in principle a derivable threshold. In practice, `t2_excursion.parquet` stores
touch **times** only at the six preset barrier levels T3's own grid already used, all computed at
the fixed `round_trip_bp = 70.98` — not a continuous price path, and not touch times at other
levels. So the exact, ordering-sensitive `p_clear` **cannot** be reclassified at a swept cost from
this artifact alone, contrary to what the prompt assumed going in.

**What was computed instead: an explicit upper bound.** `p_clear_upper_bound` = P(the shrunk
profit barrier was reached at all by horizon 60, order against the stop ignored). Sanity-checked
against the real quantity (bound must be ≥ T3's exact 0.3885 — it is, at 0.6501 at baseline).

**The finding.** The bound **already clears breakeven at the current cost** (0.6501 vs 0.6000 at
70.98 bp) and stays above it at every swept cost down to 5 bp. **47.4% of entries reach BOTH
barriers within the horizon at baseline, rising to ~89% as cost falls.** The ~0.26 gap between the
bound (0.65) and the exact measurement (0.39) is therefore almost entirely explained by **order**
— which barrier is touched first — not by whether the (shrunk) barrier is reachable at all.
Shrinking `round_trip_bp` shrinks both barriers together without itself resolving that race.

**Consequence stated once, applies throughout this report:** any cost reduction found below is a
necessary input, not a sufficient one, for closing D25's gap. Chart 01: `charts/01_threshold_sweep.html`.

---

## 3. T0 — no execution participation-rate variable existed

Grepped `research/phase_8/`, `research/phase_11/`, `src/data/canonical.py`,
`docs/data/Schema.md`, `docs/Research-Library-Map.md`. Zero hits for a trade-size-relative-to-
concurrent-volume construct. What exists under the name "participation" (`pq_rth_open`,
`research/phase_8/t3_participation.py`) is an event-level, pre-open relative-volume quintile — how
unusually active an event is against the same ticker's own T-1/T-2/T-3 baseline — not a
print-level execution rate. T2 built the latter from scratch.

---

## 4. T2 — the participation-rate variable

`participation_rate(print) = print.size / SUM(size)` over all trades in the same
`(ticker, event_date, momentum_pct, session_offset, minute_index)` bar, inclusive of the print's
own size — a retrospective measure of how large a real print was relative to its own minute's
printed volume, not a simulation of a hypothetical order. Minute grid reused from
`event_minute_bars_v2` rather than re-derived.

**Correction made mid-task:** `filtered_trades_dev_v4` carries 6 `flagged_sidecar` events
alongside the 50 `primary` ones (56 total); Phase 11's own prompt states the sidecar "is never
pooled" with primary. Restricted to `dev_cohort='primary'` on both the event list and the
per-print join.

**Result:** 50 events, 9,545,832 T=0+other-day prints, 99.25% matched to a minute bar, 10 balanced
deciles spanning participation_rate 0.00001 to 1.0 (a print that was its entire bar's volume).
Chart 02: `charts/02_participation_deciles.html`.

---

## 5. T3 — effective spread by decile

Reused `research/phase_11/stage_b_pipeline.py`'s `build_cache()` verbatim — the same function
Phase 11's own T5a used for dev-tier timing — for the Lee & Ready classification and
contemporaneous midpoint, rather than reimplementing it. Effective spread = `2*|price-mid|/mid`
(T8's `eff_frac` formula; direction-agnostic, so the Lee & Ready sign is carried but not actually
needed for this magnitude measure). Restricted to T=0 prints, matching T1's cell and Phase 11's
own Stage B scope.

**Two bugs found and fixed while building this:**
- `build_cache()` requires a `_bounds` table that neither it nor `t5a_dev_timing.py` actually
  creates — a pre-existing gap in Phase 11's own code (not introduced here), reconstructed inline.
- The first join (prints to T2's deciles on `ticker, event_date, minute_index` alone) is bar-level
  and produced a 6.1-billion-row cartesian blowup (45.6 GiB, OOM). Fixed by adding `sip_timestamp`
  to T2's own output and joining on the print's full natural key; a small residual tie population
  (~1%, consistent with Phase 11's own T4c tie audit) is deduplicated with the overage reported,
  not silently absorbed (`results/impact_by_participation/artifacts/t3_cost_by_decile.json` →
  `dedup_note`).

**Result:** effective spread is roughly **flat** across deciles 1–9 (~25–28 bp one-sided median)
and **rises** at decile 10 (~35.7 bp) — not a monotonic "lower participation, lower cost" shape.

| decile | n | eff_bp (one-sided median) |
|---|---|---|
| 1 (lowest participation) | 414,579 | 25.36 |
| 5 | 420,402 | 26.95 |
| 9 | 280,967 | 26.92 |
| 10 (highest participation) | 202,353 | 35.65 |

Full table: `results/impact_by_participation/artifacts/t3_cost_by_decile.json`. Chart 03:
`charts/03_cost_by_participation.html` (violin+strip, subsampled to 2,000 points/decile for
rendering — quartiles drawn from the full n).

---

## 6. T4 — comparison against baseline (the original stop point, before T5/T6 were authorised)

Round-trip-equivalent cost = 2 × T3's one-sided median (entry + exit both cross the spread).

| decile | n | round-trip-equivalent bp | % of 70.98 bp baseline | below baseline? |
|---|---|---|---|---|
| 1 | 414,579 | 50.71 | 71.4% | yes |
| 2 | 412,605 | 51.68 | 72.8% | yes |
| 3 | 426,078 | 52.56 | 74.1% | yes |
| 4 | 429,618 | 52.51 | 74.0% | yes |
| 5 | 420,402 | 53.89 | 75.9% | yes |
| 6 | 411,869 | 55.71 | 78.5% | yes |
| 7 | 392,568 | 56.99 | 80.3% | yes |
| 8 | 342,887 | 54.72 | 77.1% | yes |
| 9 | 280,967 | 53.84 | 75.8% | yes |
| 10 | 202,353 | 71.46 | 100.7% | no |

**9 of 10 deciles show round-trip-equivalent cost below the 70.98 bp headline** (dev tier, 50
events, T=0 only). Per §2's caveat, this alone did not establish whether narrower barriers built
from a cheaper cost would also win the ordering race — that required the exact reclassification,
authorised by Cooper and run next as T5.

---

## 7. T5 — the exact reclassification (Cooper-authorised, run after T4's stop)

T1 established that `t2_excursion.parquet` cannot support an exact ordering-sensitive
reclassification at a swept cost. It did **not** establish that no already-materialized data
could — `research/phase_10e/t2_excursion.py:101-106` shows the touch times it stores are computed
**entirely from `event_minute_bars_v2`'s `high`/`low` columns at minute granularity**:
`min(case when b.high >= fill_price*(1+k*rt) then minute_index end)`. That expression is
re-parametrisable at any swept `rt` directly against the same already-materialized cache Phase
10e's own Arm 1 already queried at full-universe scale (`research/phase_10e/t3_shares.py`,
`t4_gate.py`) — not a new pass over `filtered_trades`/`filtered_quotes`. So the exact quantity was
derivable after all, just not from the one artifact T1 checked.

**Method:** reused `t2_excursion.py`'s SQL pattern and `t3_shares.py`'s optimistic/pessimistic
tie-break logic, re-run against the **full candidate universe** (15,337 events, 5,727,491 entries
at latency=1 — `results/phase_10e/artifacts/t1_candidate_entries.parquet`), sweeping
`round_trip_bp` from 70.98 down to 5.00 (40 log-spaced points) holding `profit_k=3, stop_m=2`
fixed.

**Consistency checks, both required to pass before trusting the result:**
- Baseline (`rt_bp=70.98`) reproduces T3's own measured `p_clear_optimistic` **exactly**: 0.3885 =
  0.3885.
- Baseline sits **at or below** T1's upper bound at every point (0.3885 ≤ 0.6501) — the bound was
  a valid upper bound, as claimed.

**The exact result:** `p_clear_optimistic` rises smoothly and monotonically as cost falls, from
0.3885 at 70.98 bp to 0.6808 at 5.00 bp. **It crosses `p_breakeven` (0.6000) at an interpolated
round_trip_bp of ≈11.0 — a 84.5% reduction from baseline, to 15.5% of it.** Chart 01 (updated):
`charts/01_threshold_sweep.html`, now showing the bound, the exact curve, and the crossing point
together. Full sweep: `results/impact_by_participation/artifacts/t5_exact_reclassification.json`.

---

## 8. T6 — the decisive comparison

Does any measured participation decile reach ≈11.0 bp?

| decile | n | measured round-trip-equivalent bp | × required |
|---|---|---|---|
| 1 (lowest participation) | 414,579 | 50.71 | 4.6× |
| 2 | 412,605 | 51.68 | 4.7× |
| 3 | 426,078 | 52.56 | 4.8× |
| 4 | 429,618 | 52.51 | 4.8× |
| 5 | 420,402 | 53.89 | 4.9× |
| 6 | 411,869 | 55.71 | 5.1× |
| 7 | 392,568 | 56.99 | 5.2× |
| 8 | 342,887 | 54.72 | 5.0× |
| 9 | 280,967 | 53.84 | 4.9× |
| 10 (highest participation) | 202,353 | 71.46 | 6.5× |

**0 of 10 deciles clear it. The cheapest decile measured is 4.6× the required threshold.**
Chart 04: `charts/04_final_comparison.html`. Full table:
`results/impact_by_participation/artifacts/t6_final_comparison.json`.

**No interpretation of what this means for D24/D25 or candidate (b) follows** (Evidence
Standard). Stated as data: participation-rate variation, on this dev cohort, was measured to
achieve a cost reduction (28–29% at the cheapest deciles) that is real but roughly **5× short**
of what would be needed to close the closest cell's gap.

---

## 9. Escalation check

| # | Condition | Observed | Verdict |
|---|---|---|---|
| 1 | Working tree dirty at T0 | clean at every task boundary | pass |
| 2 | Full-tier pass before T4's Cooper approval | none through T4 — `build_cache()` ran on dev tables only. T5 (post-approval) queried `event_minute_bars_v2`, an already-materialized cache, not `filtered_trades`/`filtered_quotes` | pass |
| 3 | Write to `results/phase_8\|10e\|11/` or `src/` | none | pass |
| 4 | Spine numeric column enters a computed quantity | none — all inputs tick-derived or cost-config | pass |
| 5 | Short-side/fade construct | none | pass |
| 6 | T2's definition changed after T3 computed against it | it did change (dev_cohort fix) — T3 was rerun against the corrected T2, not patched in place | handled correctly, not a violation |
| 7 | Per-decile n < 100 in a headline decile | smallest decile n = 202,353 | pass, not triggered |
| 8 | T1 finds no `round_trip_bp*` closing the gap in [5, 70.98] | **anticipated wrong**: T1's bound crosses breakeven at every swept value including baseline — a third outcome this row's two branches didn't name. T5's exact curve, by contrast, does NOT cross at baseline and crosses only at ≈11.0 bp, which is the outcome this row was actually meant to catch. Reported as found in both cases, not forced into either named branch | see §§2, 7 |
| 9 | T4 shows cost at/above baseline at every decile | false at T4 (9/10 below baseline) — but T6's later, decisive comparison against the EXACT required threshold (not baseline) shows 0/10 clear it | see §8; candidate (b) still correctly not drafted here regardless, per the prompt's own scope |
| 10 | Write outside the authorised paths | none | pass |

---

## 10. Output files

| File | Status |
|---|---|
| `prompts/impact_by_participation.md` | committed |
| `research/impact_by_participation/{t0_audit,t1_threshold,t2_participation,t3_cost_by_decile,t4_compare,t5_exact_reclassification,t6_final_comparison}.py` | committed |
| `research/impact_by_participation/chart_{01,02,03,04}_*.py` | committed |
| `results/impact_by_participation/artifacts/{t0_audit,t1_threshold,t2_participation,t3_cost_by_decile,t4_compare,t5_exact_reclassification,t6_final_comparison}.json` | committed |
| `results/impact_by_participation/artifacts/*.parquet` | gitignored (regenerable), present locally |
| `results/impact_by_participation/charts/{01,02,03,04}_*.html` | committed |
| `results/impact_by_participation/REPORT.md` | this file |
| `results/reports/impact_by_participation_report.md` | copy |
| `docs/Open-Items-Register.md` | annotated in the same commit as this revision — the wrong-partition entry now carries the exact numbers |
| `docs/Claude-Code-Operating-Plan.md` | annotated in the same commit — row 18/19's price/size channel now has a closed, measured result for candidate (a) |

No `config/impact_by_participation.json` was needed: every task read frozen upstream configs
(`config/phase_10e.json`'s cell definition, `config/phase_11.json`'s `min_cell_n`) rather than
introducing new tunables of their own.

---

## 11. What Cooper is being asked to review

**Candidate (a) — impact by participation — is closed, measured, negative.** The two questions
T4 originally left open (§9, prior revision) are now answered: T5 established the exact required
threshold (≈11.0 bp), and T6 shows no measured decile is within 4.6× of it. What remains open:

1. **The magnitude gap (≈5×) is large enough that it is unlikely to be an artifact of the dev
   cohort (50 events) or the T=0-only restriction** — but this report does not claim that as
   established, only as a judgment call for Cooper on whether full-tier confirmation is worth
   spending given the size of the gap.
2. **Candidate (b) (ISO share, hold-length)** is the remaining candidate from
   `claude/what_would_change_a_decision.md` — its own threshold is independent of this result and
   has not been computed here.
3. **`what_would_change_a_decision.md` §4's "run nothing" criterion** requires BOTH (a) and (b) to
   fail. (a) has now failed by a wide margin; (b) has not been run. This report does not invoke
   §4 — that needs (b)'s own result first.
4. The `phase/10e` → `master` PR (#1) and the `impact-by-participation` → `phase/10e` merge this
   branch will eventually need — both unmerged, both awaiting review, per `CLAUDE.md`'s PR-review
   requirement.

**No recommendation is made on any of these four.**
