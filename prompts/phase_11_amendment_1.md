# Phase 11 — Amendment 1

**Date:** 2026-08-15
**Amends:** `prompts/phase_11.md`
**Trigger:** Escalation row 2 — T0b satisfiability audit failed on rows 4, 5, 10, 12, 18, 19; rows 7 and 9 indeterminate by task ordering; row 14 ambiguous. Audit at `results/phase_11/artifacts/t0b_satisfiability_audit.json`, commit `dffa3e8`.
**Status of the run:** No config authored, no measurement executed, no pass spent. One audit query launched and killed at 120s before returning.

**This amendment is re-audited before execution.** T0b1 of the original prompt requires the four-check audit to run again against the amended set. That requirement stands and now covers 24 rows.

---

## A1-0 — Task reordering *(fixes rows 7 and 9)*

The audit cannot check a threshold that lives in a config not yet committed. T0 is reordered:

| Was | Now | Task |
|---|---|---|
| T0a | **T0a** | Verify state, assert nothing. Read-only. Hard stop if the tree is dirty. |
| T0c | **T0b** | Cut `phase/11` from `main`. Commit `prompts/phase_11.md`, `prompts/phase_11_amendment_1.md`, `config/phase_11.json`. |
| T0b | **T0c** | Satisfiability audit, four checks, all 24 rows, **against the committed config**. Hard stop on any failure. |

T0b1 is absorbed into T0c and deleted as a separate item. The re-audit requirement before any future amendment is unchanged.

---

## A1-1 — Row 4 split *(fixes rows 4, and the row 4 ↔ 19 contradiction)*

The audit is correct on every count. `filtered_quotes_dev_v4` is a relational table and has no row order; storage order exists only in the source parquet, which T1c authorises and T1b precedes.

**T1b-ii is deleted from T1b and re-homed as T1c-v**, where the source parquet is already authorised:

> - [ ] **T1c-v — Storage-order census.** Over the 50 primary dev events, read the source `quotes.parquet` via `read_parquet` with an explicit file-order row number. Report per event: share of consecutive rows in file order where `sip_timestamp` decreases; the same for `participant_timestamp` and `sequence_number`; and whether the three orderings agree with each other. **This is descriptive. It does not gate any task and no downstream quantity depends on it** — every query in this phase orders explicitly regardless of the result. Its purpose is to put a fact about the archive on record for future phases.

**T1b retains only the well-defined clock questions** — null share, coverage, resolution from smallest non-zero gap, epoch/timezone confirmation, and the `sip − participant` latency distribution — all of which are order-free aggregates.

Row 4 is replaced by two rows:

| # | Condition | Threshold | Action |
|---|---|---|---|
| 4a | T1b: `sip_timestamp` null-or-zero share on the T=0 RTH segment, per event | **`[Cooper]`** — proposal below | Hard stop — the reference clock is broken on that population |
| 4b | T1c-v: any storage-order finding | any | **Not a stop** — report and record. No threshold exists because no decision turns on it |

---

## A1-2 — Row 5 union definition *(fixes row 5)*

The predicates overlap; a sum is not a share. Replace the T2a wording:

> - [ ] **T2a — Unusable-state time share.** Define a quote row as **unusable** if it satisfies **any** of: `bid_price > ask_price` (crossed), `bid_price = ask_price` (locked), `bid_price` or `ask_price` null or ≤ 0, `bid_size` or `ask_size` null or = 0.
>   - **The headline quantity is the union:** the fraction of segment wall-clock time during which the prevailing quote is unusable. This is what row 5 tests. It is bounded in [0, 1] by construction.
>   - **Per-state shares are also reported, individually and explicitly labelled non-exclusive.** They may sum above the union. Report the pairwise overlap matrix so the double-counting is visible rather than inferred.
>   - A **wide** quote is not unusable. Width is the measurement, not a defect. Do not add a width predicate to this definition.

| # | Condition | Threshold | Action |
|---|---|---|---|
| 5 | T2a: **union** unusable-state clock-time share on the T=0 RTH segment, at the median event | **`[Cooper]`** — proposal below | Hard stop — best-bid-and-offer features unusable on that population |

---

## A1-3 — Rows 10 and 12: the coverage-column scan *(requires a Cooper decision)*

**The finding.** `momentum_events_canonical` is a view. `quotes_ingested` and `trades_ingested` are computed by `DISTINCT` scans over `filtered_quotes` (3.8B) and `filtered_trades` (4.95B) at every reference. `CLAUDE.md` requires every quote-derived statistic to filter on `quotes_ingested`. Stage A budgets zero passes. **Any two of those three hold; all three cannot.** It binds Stage A as well as Stage B, because T2e is a quote-derived statistic.

This is not only a Phase 11 problem. The cost is query-shape dependent — Phase 5a's dev-tier ASOF join through the same view completed in 17.1s while the audit query was still running at 120s — which means the optimizer pushes the predicate into the subquery in some shapes and not others. **An unpredictable cost is worse than a uniform one**, because it never shows up in a runtime estimate until it does.

**Two scan-free materializations already exist** and were reconciled against the database in Phase 4, whose three-way disk ↔ DB ↔ spine reconciliation returned zero unexplained rows and, on its own escalation row 1, zero events present and readable on disk but absent from `filtered_quotes`:

- `quotes_bitmaps_all.parquet` — 20,951 rows
- `_actual_quotes_sessions_cache.parquet` — 115,904 rows

**Recommendation — needs Cooper's sign-off, since it moves the source of record off the canonical view:**

> **D15 (proposed).** For Phase 11, `quotes_ingested` and `trades_ingested` are read from the two Phase 4 materializations rather than from `momentum_events_canonical`. Phase 4's reconciliation stands as the verification; no new scan is run to re-verify. Every artifact and chart caption states the coverage source explicitly. **This is a Phase 11 scope decision, not a change to the canonical view** — `src/` is not touched, per "nothing in `src/` changes mid-phase."

> **Open item (not this phase).** The canonical view should compute the coverage columns from a materialized table rather than a live `DISTINCT`. That is a `src/` change and belongs in a maintenance phase. Recorded to `docs/Open-Items-Register.md` with this finding attached, including the observation that prior phases' runtime figures may embed this cost invisibly.

**Row 12 is reworded to define what it counts, so the implicit scan cannot recur silently:**

| # | Condition | Threshold | Action |
|---|---|---|---|
| 12 | Any full scan of `filtered_quotes` or `filtered_trades` beyond the single budgeted pass in T5b — **including any scan triggered indirectly by referencing a view column that computes one** | > 1 | Hard stop |
| 12a | Any query that has run for longer than `config.query_watchdog_seconds` without returning | as configured | Kill the query, post what it was and what it touched, do not retry. *(This is what the agent already did; it becomes a rule.)* |

Row 10's threshold remains Cooper's, and under D15 it no longer conflicts with row 12.

---

## A1-4 — Row 14 wording *(resolves the ambiguity)*

Intended meaning: the existing main-line tables and the canonical view. Creating new phase-scoped tables inside `main.duckdb` is legal and precedented — Phase 8 created `event_minute_bars_v2` the same way.

| # | Condition | Threshold | Action |
|---|---|---|---|
| 14 | Any write to the data root, to `src/`, or to any **pre-existing** table or view in `main.duckdb` — specifically including `filtered_trades`, `filtered_quotes`, `momentum_events`, `momentum_events_canonical`, `event_minute_bars_v2`, and the `_dev_v3`/`_dev_v4` tables | any | Hard stop |
| 14a | Creating a **new** phase-scoped table in `main.duckdb` — `event_quote_metrics_v1` and any `_phase11` working table | — | **Permitted.** Named in the output file table, dropped or documented at the approval gate |

---

## A1-5 — Row 18 rewrite *(fixes row 18)*

The audit is right and this is the 10b defect class. A pre-registered reading rule exists for T3 alone; the row tested five other tasks against nothing, leaving no satisfying state for any sentence about the T7 headline.

The row was meant to prevent **characterisation**, not description. The Agent Prompt Standard already draws that line and the row should match it rather than invent a stricter one. Replace row 18 with:

| # | Condition | Threshold | Action |
|---|---|---|---|
| 18 | Any REPORT.md or digest sentence that **evaluates** a result — good, bad, strong, weak, promising, disappointing, encouraging, supportive of or contrary to the thesis — or states an implication for the strategy, or recommends an action | any | Hard stop before posting |
| 18a | For **T3 specifically**: the report does not name which pre-registered reading-rule row the curve matches | any | Hard stop before posting |

**Explicitly allowed and expected**, per the standard: measurements with n; description of what is visible in a chart, including direction, monotonicity, overlap, dispersion and thin buckets; explicit statements of uncertainty; explicit "I don't know". A sentence such as *"the ratio's ECDF sits entirely right of 1.0 at every latency (n = 10,607)"* is description and is required. *"which suggests the thesis is unviable"* is evaluation and fires row 18.

---

## A1-6 — Row 19 exemption *(fixes row 19)*

| # | Condition | Threshold | Action |
|---|---|---|---|
| 19 | Any computation **whose output feeds a downstream quantity** that depends on parquet storage order rather than an explicit `ORDER BY` or ASOF key | any | Hard stop |
| 19a | **T1c-v is exempt by name.** Measuring storage order necessarily depends on storage order, and its output feeds nothing | — | Exempt |

---

## A1-7 — Corrections carried from the audit

Both are drafting errors in the original prompt.

- **T6c:** `pq_rth_open` is read from `results/phase_8/artifacts/t3_participation.parquet`, **not** `a102_detection_anchors.parquet`. Reuse frozen; do not re-derive.
- **Context and T0a:** the dev v4 sidecar is **6 events on the trades side and 3 on the quotes side** — the three absent events drew quotes-side all-missing bitmap patterns, the documented non-failing case from Phase 5a. Stage A runs on the 50 primary events, so nothing in this phase binds on the sidecar. Correct the prompt text; no task changes.

---

## A1-8 — Chart Contract addition

Chart 01 gains a fourth panel:

> **Panel D** — storage-order census (T1c-v). x = share of consecutive file-order rows where the field decreases, y = event; one row of marks per field (`sip_timestamp`, `participant_timestamp`, `sequence_number`); n events annotated. **Looks like this if wrong:** nothing — this panel has no failure appearance because no hypothesis rests on it. It is a record of archive state.

---

## Thresholds — proposals, for Cooper to set or overrule

These are proposals so there is something concrete to react to. **None is adopted until Cooper states it.** The agent does not fill any of them.

| Row | Quantity | Proposed | Reasoning |
|---|---|---|---|
| 4a | `sip_timestamp` null-or-zero share, T=0 RTH, per event | **> 1%** on any event | The clock is either present or the row is unusable; this is not a graded quantity. A percent is generous. |
| 5 | Union unusable-state clock-time share, T=0 RTH, median event | **> 25%** | Above roughly a quarter of the session, the prevailing quote is more absent than present and a time-weighted spread is describing gaps. Set lower if you want the phase to fail loudly rather than degrade. |
| 10 | `quotes_ingested = FALSE` share of the detection universe | **> 20%** | Phase 4 put the in-scope file1 quotes-gap cohort at 386 of ~15.7k, so the expected value is low single digits. A 20% trigger means something unexpected has happened, not that the known gap exists. |
| 11 | **The kill threshold** — median round-trip cost ÷ realized capture, RTH cell, latency 5, hold 30, at 1× cost, n = 10,607 | **≥ 0.50** | At half the capture consumed by the round trip before any adverse selection, slippage beyond the touch, or fee, the remainder is not a strategy. This is the number that most wants your judgement rather than mine. |
| 21 | `indicators` / `conditions` null-pattern difference across eras | **> 20 percentage points** between any two eras | Not a stop either way; the threshold only decides when it gets its own report section. |

---

## Approval

Nothing runs until Cooper has:

1. Approved or overruled **D15** (coverage-column source). Stage A cannot run without it — T2e is quote-derived.
2. Set rows **4a, 5, 10, 11, 21**. Rows 4a and 5 gate Stage A specifically and are needed before T1 and T2.
3. Approved this amendment, after which T0a → T0b → T0c re-runs the four-check audit against all 24 rows and the committed config.

---

---

# Cooper's decisions — recorded 2026-08-15

*Appended by the agent as a record of the approval. The amendment text above is unmodified.*

A 25-row v2 rewrite of `prompts/phase_11.md` was also circulated on 2026-08-15 and then interrupted. Cooper ruled on which spec governs, and on the four open forks, before any task ran.

| Decision | Ruling |
|---|---|
| **Governing spec** | **Amendment 1 over v1.** `prompts/phase_11.md` (v1, committed `dffa3e8`) as amended by this document. 24 escalation rows. The v2 rewrite is **discarded**, with one element imported by explicit decision — see row 5 below. |
| **D15 — coverage-column source** | **APPROVED as proposed.** `quotes_ingested` / `trades_ingested` are read from `results/phase_5/artifacts/quotes_bitmaps_all.parquet` and `results/phase_4/artifacts/_actual_quotes_sessions_cache.parquet`. The canonical view is not referenced for these two columns and is not modified. Every artifact and chart caption states the coverage source. The view-remediation open item is recorded for a future maintenance phase, not done here. |
| **Row 5 — state definition** | **v2's hard/degraded split is imported, overriding A1-2's single union.** Row 5 triggers on **`state_hard_unusable` only** = null price ∪ non-positive price ∪ one-side-missing ∪ crossed. **`state_degraded`** = locked ∪ zero-size, among rows not already hard-unusable, is reported but does **not** fire the stop. Rationale of record: a locked quote (`bid = ask`) has a well-defined midpoint equal to both sides, and a zero-size quote still yields a computable midpoint; neither is "no midpoint exists". T2a additionally confirms `hard_unusable + degraded + clean = 1.0` per event to floating-point tolerance, and still reports per-state non-exclusive shares with the pairwise overlap matrix per A1-2. |
| **Row 5 — trigger** | **Median across events > 25%**, single trigger. v2's second clause (">20% of events above 50%") is **not** adopted. |
| **Row 4a** | **> 1%** on any single event. Hard stop. |
| **Row 10** | **> 20%** of the 15,369-event detection universe. Hard stop. |
| **Row 11 — kill threshold** | **≥ 0.50.** `config.kill_threshold = 0.50`. |
| **Row 21** | **> 20 percentage points** between any two eras. Not a stop; report-section trigger only. |

All `[Cooper]` thresholds are now set. Item 3 of the Approval section above is satisfied: T0a → T0b → T0c proceeds, with T0c re-running the four-check audit against all 24 rows and the committed `config/phase_11.json`.
