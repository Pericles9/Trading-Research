# Phase 11 — Amendment 3

**Date:** 2026-08-16
**Amends:** `prompts/phase_11.md`, as amended by Amendments 1 and 2
**Trigger:** T0c re-audit (0 failures, 3 flags) and T4b ordering audit (15 hits, all class (a)) at `fc49037` / `98dac7c`. Rules the three flags and adds one audit the T4b scope could not have surfaced.
**Blocking status:** **Nothing here blocks T5a.** T5a is timing only and touches no price semantics. T4c below runs before T5b.

**Re-audit required.** T0c re-runs against the amended set — now **34 enumerated rows** — before T5b.

---

## A3-0 — Row count *(flag 1: accept, editorial)*

The audit's enumeration is correct: **31 rows**, highest number 29. The "29 rows" figure in Amendment 2 was the highest row number, not the count — 4a/4b split one number into two and numbering starts at 0. This amendment adds three, giving **34 enumerated rows**. Report the enumerated count, not the highest number, in every future audit.

---

## A3-1 — Twin axes → linked panels *(flag 2: accept, my error)*

Charts 05 and 09 specify a dual y-scale. **That is the one encoding the project's visualization standard forbids outright**, and Phase 9 resolved the identical conflict on its chart 06 with a linked panel sharing the x-axis. Follow that precedent.

The reason this matters more than usual here: **D19 exists because bp and cents move in opposite directions.** RTH median goes 165.0 → 83.9 bp while cents goes 3.64 → 3.79. On twin axes a reader can see one line, read a slope, and believe they have seen both units. Linked panels make the divergence the visible fact rather than an artifact of scale choice.

> Charts **05** and **09**: two vertically stacked panels sharing the x-axis — upper in basis points, lower in cents, identical faceting and identical n annotations on both. Single file. Deviation from the prompt's encoding recorded in the chart caption, citing this amendment and the Phase 9 chart 06 precedent.

Chart 03 already specifies two panels and is unchanged. D19 and row 27 are satisfied by a two-panel layout: both units are present.

---

## A3-2 — Row 5 / D17 vocabulary *(flag 3: accept, with a stronger reason)*

The audit's reason — the two never have to agree, because row 5 is a passed Stage A gate not re-evaluated in Stage B — is correct but weaker than what the evidence supports. Record the stronger one:

> **D17's excluded set is a strict subset of the row 5 union.** T2a's union included locked; D17 carries locked. The D17-excluded set is therefore the row 5 union **minus** locked. A subset of a set whose RTH clock-time share measured exactly 0.000000 also measures 0. **The passed gate transfers to the narrower rule a fortiori** — it is not merely non-interacting with it.

This belongs on record in case a later phase asks whether the gate that passed covered the rule actually used.

**Carrying locked is a choice, so make it auditable:**

> - [ ] **T7h (new)** — report **locked clock-time share** in the RTH decision cell, alongside the T7 headline, as its own row with n. If it is ~0, the choice is immaterial and that is on record. If it is not, measured spread is biased **downward** and the headline is optimistic by an amount this number bounds. Description only.

---

## A3-3 — T4c: tie-dependence audit *(new — the class T4b's scope could not reach)*

**T4b was scoped to row-order dependence and correctly found none.** The adjacent class it could not surface by construction is **tie dependence under an explicit ordering key**.

`arg_min(price, sip_timestamp)` is deterministic only where `sip_timestamp` is unique within the group. T1b found **58,465 tied-sip rows** on the quotes side in dev alone, and Phase 10 v1 measured trades-side resolution at the same 49 / 80.5 ns, so ties are near-certain on trades. Where two prints in a minute share the minimum (or maximum) `sip_timestamp` **and differ in price**, `first_price` and `last_price` are arbitrary among the tied set — with no ordering error anywhere in the code and nothing for a row-order audit to find.

### What is and is not exposed

**Not exposed — `det_anchor` timing.** `det_minute = MIN(minute_index) FILTER (high >= threshold)`, and `high = MAX(price)`. MAX and MIN over a set are tie-immune by construction. **Phase 8's detection minute is sound regardless of the T4c result.**

**Exposed — the `first_price` / `last_price` consumers:** `det_price_lat*`, Phase 9 entry and exit prices, and `tick_close_t_minus_1_rth`. That is the whole surface, and it is narrower than it first appears.

> - [ ] **T4c — Tie-dependence audit.** Read-only. Runs before T5b; does not block T5a.
>   - [ ] T4c-i — Over the detection universe, count `(event_id, minute_index)` groups where the **minimum** `sip_timestamp` is shared by ≥2 trades, and separately where the **maximum** is. Report the share of minute bars affected, and the share of **detection-minute** bars affected.
>   - [ ] T4c-ii — Of those, the share where the tied prints **differ in price**. Exact-duplicate prints are harmless here; cross-reference `flag_has_dup_prints` from Phase 9 and report the overlap.
>   - [ ] T4c-iii — **Bounded price error.** For each affected bar, the range of possible `first_price` / `last_price` across the tied set, in **basis points and cents** (D19). Report the distribution, and separately for the bars that feed `det_price_lat*` and Phase 9 entry/exit — those are the ones that reach the headline.
>   - [ ] T4c-iv — **Measure and bound only. Do not fix.** `sequence_number` is the available tiebreak — T1b established it never inverts under the sip sort and breaks all 58,465 tied rows uniquely — but applying it means rebuilding `event_minute_bars_v2` and re-deriving frozen artifacts. **That is a Cooper decision, not an agent one** (row 32).

**Also add to T4b, as T4b-iv** — the same trap in aggregate form, distinct from the `first_value`/`last_value` window functions already cleared: grep the pipeline for DuckDB's **`first()`** and **`last()`** aggregates, **`ANY_VALUE()`**, **`mode()`**, and **`DISTINCT ON`**. Classify by the same (a)/(b)/(c) scheme.

---

## A3-4 — New escalation rows

| # | Condition | Threshold | Action |
|---|---|---|---|
| 30 | T4c-iii: p95 bounded price error across affected bars feeding `det_price_lat*` or Phase 9 entry/exit | **`[Cooper]`** — proposed **> 25 bp** | Hard stop — post the distribution, Cooper decides on any fix |
| 31 | T4b-iv finds `first()`, `last()`, `ANY_VALUE()`, `mode()` or `DISTINCT ON` on a data path producing an artifact Phase 11 reuses frozen | any | Hard stop |
| 32 | Any rebuild of a frozen artifact, or any `src/` change, undertaken without an explicit Cooper decision — **including applying the `sequence_number` tiebreak** | any | Hard stop |

**Threshold reasoning for row 30, for Cooper to set or overrule.** The headline is a cost ratio whose numerator runs to tens or hundreds of basis points. A price ambiguity of a few bp is below the noise floor of the thing being measured and does not justify rebuilding four frozen artifacts. 25 bp is where the ambiguity starts to be a material fraction of a plausible round-trip cost. Row 32 exists because the fix is easy, tempting, and expensive in ways that are not visible from inside the task.

---

## A3-5 — Amended output files

| File | Change |
|---|---|
| `results/phase_11/artifacts/t4c_tie_audit.{parquet,json}` | **New** — tie counts, price-differing share, bounded error distribution, detection-minute and entry/exit breakouts |
| `results/phase_11/artifacts/t4b_ordering_audit.json` | Adds T4b-iv aggregate-function enumeration |
| `results/phase_11/artifacts/t7_cost_vs_capture.{parquet,json}` | Adds T7h locked-share row |
| `results/phase_11/charts/05_*.html`, `09_*.html` | Two-panel layout; caption records the encoding deviation |
| `docs/Open-Items-Register.md` | Tie-dependence finding and its bound, whatever T4c returns; the a fortiori note from A3-2 |

---

## A3-6 — Execution order, amended

1. **T2e-i** — implied-price decomposition. No computation. *(unchanged)*
2. **T5a** — dev-tier timing and extrapolation against the 21,600 s ceiling. **Hard stop rather than reduce cohort or grid.** *(unchanged, unblocked)*
3. **T0c** — re-audit, 34 rows, amended spec and config.
4. **T4b-iv** — aggregate-function grep.
5. **T4c** — tie-dependence audit. Row 30 gate.
6. **T5b** — the single budgeted pass.
7. **T6 → T7 → T8 → T9.**

Steps 3–5 are cheap and touch no tick data. Running T5a first means the ceiling question is answered before any further audit effort is spent — if the pass cannot run, the tie bound does not matter yet.

No further Cooper gate until T9, unless a row fires.
