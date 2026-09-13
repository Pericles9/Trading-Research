# Amendment F1-A1 — financials source of record after the F1-T0 gate

**Date:** 2026-09-12 · **Type:** formal amendment to `prompts/fundamentals_f1.md`.
**Trigger:** F1-T0 returned the second branch. Escalation row 1 fired as designed.
**Status:** approved and executed, 2026-09-12. F1-T0f and F1-T0g both run — see integration note below.

**Integration note.** This amendment was received referencing `prompts/fundamentals_build_f1.md`; the
actual committed filename in this repo is `prompts/fundamentals_f1.md` (the stem this build has used
since pre-flight, matching branch `build/fundamentals-f1`). Applied against the correct file. Separately,
§7's task-order table names the new `companyfacts`-based `fin_` build "F1-T4b" — that ID was already
taken by the shares-outstanding extraction task in the base work order (§3, F1-T4). Renumbered to
**F1-T4f** in `prompts/fundamentals_f1.md` to avoid the collision; noted there, not silently absorbed.
Both corrections are exactly the class of citation drift `tools/verify_cited_paths.py` and this
programme's decision-numbering discipline exist to catch — recorded rather than fixed invisibly.

**F1-T0f and F1-T0g were both run, 2026-09-12, before F1-T1/T2 resumed** (as §0/§7 require). Results:
**Outcome A** confirmed (the vendor serves original as-filed values) and `companyfacts` confirmed
genuinely multi-vintage. Full findings are integrated inline into `prompts/fundamentals_f1.md` at every
section this amendment touches (§0/§1's F1-T0 outcome, §4 schema, §6 escalation rows, F1-T1/T2/T3/T4
task descriptions) rather than left to be cross-referenced from this file alone. This file is kept as
the record of the amendment as given.

---

## 0. What the gate returned, and the one thing it did not establish

The method was right and is worth keeping as a reusable instrument. **Searching for 10-K/A hits mostly
administrative Part-III amendments** — exec-comp disclosure added a month after the original, touching no
financial figure. **8-K Item 4.02 (Non-Reliance on Previously Issued Financial Statements) is the signal that
actually means a restatement.** That distinction should go in `docs/data/` as a note; it will be needed again
in §3 below and it is not obvious.

The stop was correct. Escalation row 1 is satisfied and this amendment is its required output.

**But the test establishes that exactly one vintage exists per period. It does not establish which vintage
that is** — and the two possibilities have opposite consequences:

| what the single record carries | consequence |
|---|---|
| **Latest restated values** | Contaminated. Every event preceding a restatement carries figures nobody could have known. The diagnosis as written holds. |
| **Original as-filed values** | **Point-in-time and usable.** You get what was on file at `t0`, which is exactly what DF-2 asks for. What you lose is the ability to see restatements at all — which is a flag problem, not a contamination problem. |

The vendor's documentation says restated. That documentation has already contradicted itself once in this
build, which is why the gate existed. **It should not be trusted to settle the question it was wrong about.**

### F1-T0f — the disambiguating query. One query, decisive.

- [ ] Take CLRB's FY2023 record — the one already tested. Read the **actual value** the vendor returns for a
      line item the restatement changed.
- [ ] Read the same line item from the **original 10-K as filed** and from the **amended filing**.
- [ ] Whichever it matches is the answer.

Outcome A (matches the original) — the vendor data is point-in-time after all, and the only gap is that
restated periods are invisible. That gap is closed by a flag built from the 8-K Item 4.02 population in §3,
and **the `fin_` group can be built from the vendor as originally planned.**

Outcome B (matches the amendment) — the diagnosis stands and §2 is the redesign.

**Run this before anything in §2 is built.** It is minutes, and it decides whether the rest of this amendment
is necessary work or wasted work.

---

## 1. Proportionality — settle this before designing anything

Stated plainly, because the natural reflex here is to fix the problem at whatever cost it takes, and that
reflex is the failure mode this programme has already named.

**`fin_` is the weakest group in the schema.** The scoping note's argument was that for sub-$5 micro-cap
gappers, income-statement fields are mostly missing, mostly zero, and have no channel anyone has articulated
into a same-session intraday move. **DF-6 already forbids putting any of them against an outcome.** The groups
with a real mechanism — filing proximity, shares outstanding, dilution state — are untouched by this finding.

**Raw XBRL parsing per accepted filing is a large build.** Custom extension elements, inconsistent element
choice between filers, presentation linkbases, amended filings that re-tag. It is weeks, not days.

**Post-D26 rule, restated with its value: this lineage's failure mode was never a bad estimator, it was
running phases whose outcomes could not change a decision.** Spending weeks building a parser for the group
the programme has argued cannot change a decision would be that failure mode, executed diligently.

**So the constraint on this redesign is: it is cheap, or the group is deferred rather than rebuilt.** Deferring
`fin_` costs nothing that has been argued for. §2 is proposed because it is cheap, not because `fin_` is
important.

---

## 2. The redesign — `companyfacts`, not raw filing documents

**The work order's stated fallback was "the SEC route (raw XBRL per accepted filing)." That is the expensive
version of the right idea and it is not necessary.**

`companyfacts.zip` is **already in the plan** — F1-T4a downloads it for the shares-outstanding group. Its
structure is the reason it solves this:

Facts nest by taxonomy (`us-gaap`, `dei`) then by concept then by unit, and **every individual observation
carries `accn` (the accession number of the filing that reported it) and `filed` (that filing's date)**,
alongside `start`, `end`, `val`, `form`, `fy`, `fp`. Because every quarterly and annual filing restates prior
comparatives, **the same period appears repeatedly under different accession numbers** — which is exactly the
multi-vintage structure the vendor does not have.

**Filtering observations to `filed < t0` and taking the latest surviving one per concept reconstructs what
was on file at the event.** That is the definition of point-in-time, and it comes from a file already being
downloaded.

Three consequences worth stating:

- **`shs_` and `fin_` come from one parse pass.** The `dei` cover-page share count and the `us-gaap` line
  items are in the same archive, keyed the same way. The two groups stop being separate builds.
- **The archived vendor financials become the cross-check harness.** Comparing vendor-latest against
  companyfacts-latest, per concept, validates the element mapping for free. **The contaminated source becomes
  the test instrument for the clean one** — which is a better use for it than deletion, and a reason to keep
  archiving it in F1-T2.
- **Restatements become measurable rather than invisible.** `fin_n_vintages` and `fin_superseded_later` fall
  out of the same structure at no cost.

### The real cost, stated honestly

`companyfacts` gives **US-GAAP element names, not a normalized schema.** Revenue may be tagged `Revenues`,
`RevenueFromContractWithCustomerExcludingAssessedTax`, `SalesRevenueNet`, or a company-specific extension.
Each of the nine `fin_` line items needs a **declared element-priority list**, written into
`docs/data/fundamentals_sources.md` before the build runs.

This is bounded and well-trodden. **Invoke `reuse-before-build` and `prior-art-check` before writing a mapping
by hand** — element normalization over companyfacts is solved in maintained libraries, and adapting one is the
default posture.

### F1-T0g — verify the multi-vintage claim before relying on it

One source consulted for this amendment cautioned that "EDGAR keeps the latest value" on restatement. That
most likely describes the `frames` API, which selects one observation per entity per period by design, rather
than `companyfacts`, which is an append-only observation list. **Most likely is not verified.**

- [ ] Pull CLRB's `companyfacts` — the same company the vendor failed on.
- [ ] For the FY2023 concept the restatement changed, list every observation: `accn`, `filed`, `form`, `val`.
- [ ] **Count distinct `accn` and check whether `val` differs between them.**

| result | consequence |
|---|---|
| Two or more observations, differing values | `companyfacts` is multi-vintage. §2 proceeds. |
| One observation only | **Stop and post.** Neither source is point-in-time, and the only remaining route is raw filing documents — at which point §1's proportionality argument says defer `fin_`, not build it. |

**Testing on the company that already broke the vendor is the point.** A verification that cannot come back
against the proposal is not a verification.

---

## 3. Blast radius is a number, and it should be measured before any mapping is built

Whatever §2 concludes, **the size of the contaminated population is currently unknown.** Two companies were
found by search; that is a demonstration of existence, not a rate.

### New task — F1-T3h

- [ ] From the filing index F1-T3 builds anyway: count in-scope **companies** and **events** where an 8-K
      Item 4.02, a 10-K/A, or a 10-Q/A **amending financial statements** (not a Part-III-only amendment — §0)
      was accepted **after** the event's `fin_` vintage.
- [ ] Report as a share of the 20,951, cross-cut by year.
- [ ] Free. No new dependency. Uses data already required for DF-2.

| blast radius | what it decides |
|---|---|
| Small (single-digit percent of events) | A contamination **flag** on affected events may be adequate. The element-mapping build becomes optional rather than required, and `fin_` can carry vendor values with honest provenance in the interim. |
| Large | §2 is required, and the flag alone would not be defensible. |

**This number should exist before the mapping is written, not after.** It is the difference between a
necessary build and an expensive reflex.

---

## 4. The pull is unblocked. The gate touched four endpoints out of ten.

**This is the correction with a clock on it, and it should be acted on before anything else in this
amendment.**

F1-T2 was halted entirely. The gate's finding bears on **financial statement vintages** and on nothing else.

| endpoint | in scope of the F1-T0 finding? |
|---|---|
| income statements, balance sheets, cash flow statements, ratios | **Yes** — restated-vintage problem |
| ticker details, ticker events | No — current reference data, and F1-T1 needs it |
| splits, dividends | No — dated corporate-action records, not restated statements |
| short interest, short volume | No — dated observations with their own settlement dates |

**Six of ten endpoints are unaffected, and they are the rented ones with a subscription expiry behind them.**
Holding the entire pull hostage to a redesign of the weakest group inverts the asymmetry the scoping note was
built around: the vendor data expires, the SEC data does not.

### Amended F1-T2

- **Unblocked, and it is the priority.** Resume the full pull, all ten endpoints.
- **F1-T2b amended:** vendor financial statements and ratios are archived with
  `source_of_record: false` recorded in the fetch manifest. They are kept as the §2 cross-check harness and
  as the input to F1-T0f. **They may not populate `fin_` unless F1-T0f returns Outcome A.**
- F1-T1 is unblocked and runs first, as written — it was never in scope of the gate and is a prerequisite for
  the pull.

---

## 5. Schema changes to `event_fundamentals`

Group `fin_` only. No other group changes.

| column | change |
|---|---|
| `fin_source` | **new.** enum: `companyfacts` / `vendor_archive` / `unavailable`. No row's provenance may be ambiguous once two possible sources exist. |
| `fin_quality` | **revised enum:** `as_filed` / `as_filed_superseded_later` / `restated_unknown_vintage` / `unavailable`. The middle value is the honest state for a correctly point-in-time figure that a later filing revised — it is not a defect, and collapsing it into either neighbour loses the distinction. |
| `fin_n_vintages` | **new.** int16. Count of distinct accession numbers reporting this period at or before `t0`. 1 is normal; higher means the period was already revised before the event. |
| `fin_superseded_later` | **new.** bool. True when any filing after `t0` revised this period. **Strictly a diagnostic — it is knowable only after the fact and must never enter a computed quantity.** Same quarantine shape as DF-1 and D4. |
| `fin_accession` | unchanged in meaning, but now sourced from the observation's `accn` |

`fin_superseded_later` earns the same explicit ban as the vendor float endpoint because it is exactly the
same hazard: a column that is genuinely useful for auditing and a lookahead if joined to an outcome.

---

## 6. The ticker count — my error, not a discrepancy

**2,576 and 2,930 are both correct and describe different populations.** 2,576 is D1's ticker count, stated in
`results/reports/phase_9_report.md` against **15,763 events**. The work order applied it to the **20,951**
in-scope population, which is a different and larger set.

**The work order mis-cited it. There is nothing to reconcile in the data.**

- [ ] Correct §0 of `prompts/fundamentals_build_f1.md` to read **2,930 tickers across 20,951 in-scope
      events**, with D1's 2,576 noted alongside as the smaller frame's count.
- [ ] Downgrade the `docs/Open-Items-Register.md` entry from a discrepancy to a resolved note.

Worth recording as the small general lesson it is: **a count carried from one report into another is a
membership claim**, and membership claims in this repo are supposed to be asserted, not quoted. The
work order did the thing it tells the agent not to do.

---

## 7. Revised task order

| task | state |
|---|---|
| **F1-T0f** — disambiguating query, original vs restated (§0) | **new. Run first. Stop and post.** |
| **F1-T0g** — `companyfacts` multi-vintage verification on CLRB (§2) | **new. Stop and post.** |
| **F1-T1** — identity spine | **unblocked, unchanged** |
| **F1-T2** — vendor pull | **unblocked, amended per §4. Priority — this is the piece with the expiry.** |
| **F1-T3** — filing index and proximity | unchanged |
| **F1-T3h** — blast-radius count (§3) | **new** |
| **F1-T4** — shares outstanding from `companyfacts` | unchanged |
| **F1-T4b** — `fin_` from `companyfacts`, element mapping | **new, and conditional on F1-T0f, F1-T0g and F1-T3h — renumbered to F1-T4f in `prompts/fundamentals_f1.md`, see integration note above** |
| **F1-T5, F1-T6** | unchanged except the §5 columns |

---

## 8. Escalation row changes

- **Row 1 is retired.** It fired, it produced this amendment, and it is superseded by the rows below.

| # | condition | action |
|---|---|---|
| **1a** | F1-T0f shows the vendor serves original as-filed values | Outcome A. §2 becomes optional; amend again before building it. Not a stop — a simplification. |
| **1b** | F1-T0g shows `companyfacts` carries one observation per period | **Stop and post.** No point-in-time source exists. §1's proportionality argument then says **defer `fin_`**, and that disposition is pre-registered here so it is not re-argued under the pressure of having already built the surrounding layer. |
| **1c** | F1-T3h blast radius exceeds a threshold **Cooper sets before F1-T3 runs** | The flag-only interim is not available; F1-T4b becomes mandatory. |

Rows 2 through 7 of the original work order are unchanged and remain in force.

---

## 9. What this amendment does not do

- It does not decide that `fin_` will be built. It decides **what would have to be true** for it to be worth
  building, and pre-registers the deferral if those things are not true.
- It does not change any group other than `fin_`.
- It does not relax DF-6.
- It does not set the F1-T3h threshold, the `filed_stale` threshold, or the coverage floor. **All three remain
  Cooper's, and all three must be set before the run they gate.**
