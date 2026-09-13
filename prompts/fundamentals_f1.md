# Work order — fundamental data and float layer, build F1

**Date:** 2026-09-11 · **Type:** work order. Executable brief for Claude Code.
**Format:** step-by-step standard, not goals-and-tests. No derivation exists yet to pre-register numbers
against, and per the post-D26 rule, goals-and-tests before derivation is an unsupervised agent.
**Status:** this is a **data-layer build, not a research phase.** It carries no phase number, produces no
finding, and tests no hypothesis. It ends at a coverage report.

**Reconciliation note (2026-09-11, pre-flight, this file's own history).** The original draft of this
work order assumed several things that do not hold in this checkout: a companion scoping note that does
not exist, an `event_id` spine column that does not exist, a `t0` spine column that does not exist, and
an offline-environment carve-out for two network tasks that was not on record. All four were resolved
before any task ran — see `docs/Universe-Decisions.md` D27–D33 and the D14 Amendment A1, and the
git history of this file and this branch (`build/fundamentals-f1`, branched from `phase/10e`, not
`master`, because `master` does not yet carry D24–D26). The task list below is otherwise unchanged from
the original draft; §1's decisions are now registered (not proposed), and §3/§4's `t0` references are
updated to point at the resolution instead of assuming a column that was never there.

**Amendment note (2026-09-12).** F1-T0 fired escalation row 1 as designed (one vendor record per
period, no duplicates) but that test alone did not establish which vintage the record carried.
`prompts/fundamentals_f1_amendment_a1.md` named the gap and specified F1-T0f/F1-T0g to close it — both
run, both resolved: **Outcome A** (the vendor serves original as-filed values, confirmed on CLRB's
FY2023 `NetIncomeLoss`) and **`companyfacts` confirmed multi-vintage**. Escalation row 1 is retired;
rows 1a–1c (§6) and D14 Amendment A1's F1-T0 gap (already closed) are in force. F1-T1 and F1-T2 are
unblocked. The task list below reflects both amendments inline, at the sections they touch, rather than
requiring a second document to be read alongside this one.

**F1-T1 (identity spine) and F1-T2 (Massive bulk pull) both complete, 2026-09-12.** F1-T1: 20,951 events
resolved to CIK, 97.32% exact, 1.49% ambiguous (37 tickers), 1.18% unresolved — escalation row 2 does not
fire. F1-T2: 2,935 distinct CIKs pulled across 8 working endpoints (`ratios` not_found, recorded not
guessed), 23,480 raw files, 2.17 GB, zero fetch failures after two bugs (pagination, silent `cik=`
mishandling on four endpoints) were caught in dry-run testing and fixed before the full-scale run. The
network step is closed — everything from F1-T3 onward that touches Massive/SEC EDGAR still needs D14
Amendment A1's scope, but the bulk archive itself is done and immutable. Full results inline at F1-T1/F1-T2
below.

---

## 0. Standing constraints that apply, restated with values

Restated rather than cited, per the rule that a brief must carry its numbers inline.

| constraint | what it means here |
|---|---|
| **D4 — spine numerics quarantined** | `momentum_events_canonical` numeric columns are diagnostic-display only. This build **reads** `ticker`, `event_date_canonical`, `momentum_pct`, and `in_scope` from it and **writes nothing to it**. No output table may carry a spine numeric column under any name, including a transform of one. |
| **D14 — offline environment, amended for this build only** | The archive is offline by default. **D14 Amendment A1** authorizes network access narrowly for F1-T0 (the restatement gate test, queries the same Massive endpoint F1-T2 will pull in bulk), F1-T2 (Massive pull), and F1-T3 (SEC EDGAR pull) — immutable raw archives, written once, then stopped. Every other task runs offline against those archives. |
| **Flag, never delete** | An event with no usable value is a row with an explicit `unavailable` quality flag. Never dropped, never imputed, never forward-filled silently. |
| **Executable assertions** | Every membership or coverage claim in the digest must be produced by a script-level assertion that fails loudly, in the structured drift-dict + exit-code style of `tools/verify_cited_paths.py` / `tools/verify_claude_md_indices.py` — not a bare `assert`. Prose statements of membership are insufficient — this is the recurring defect pattern (the VEEE/CODX swap, the ticker `.nunique()` bug). |
| **Universe membership** | Inner join to `momentum_events_canonical WHERE in_scope = TRUE`. Target row count: **20,951** — confirmed against `results/phase_5/artifacts/quotes_bitmaps_all.parquet` (D15's own materialization, 20,951 rows), not a live `COUNT(*)` against the view, which is expensive (observed still under 10% complete after ~40 minutes; the view's staged construction joins `filtered_trades`/`filtered_quotes`, 4.9B/3.8B rows, for coverage flags regardless of which columns are selected). |
| **Identity key** | No spine or view column is named `event_id`. This build reuses the de facto convention already standard across `research/phase_10/`, `phase_10e/`, `phase_11/`, `scale_field/` (50+ files), defined once at `research/phase_10/common.py:215`: `f"{ticker}_{event_date_canonical}_{momentum_pct:.2f}"`. No second convention is invented for the same concept. |
| **t0 anchor** | No spine or view column is named `t0`, and no single existing artifact covers the universe at any one precision. Per D33: a tiered construction — nanosecond anchor (`v2_r13_detection.parquet`, 110 events) → minute anchor (`a102_detection_anchors.parquet` resolved via `event_minute_bars_v2`, 15,259 events) → first-trade fallback (each event's own `data/filtered/` folder, 5,582 events). Run and verified: 0 unavailable, sum = 20,951. Built once as `t0_spine.parquet` before F1-T1; every downstream task reads it rather than re-deriving t0. |
| **Git discipline** | Branch `build/fundamentals-f1` (off `phase/10e`, per the reconciliation note above). Commit before each run, at every task boundary, and before any escalation. Tag at the F1-T6 gate. |
| **Data documentation lives in `docs/data/`** | Not in `/data/`, which `.gitignore` excludes wholly. Schema and provenance documents are version-controlled artifacts. |

---

## 1. Registered decisions

**These are now registered as `docs/Universe-Decisions.md` D27–D32** (assigned during pre-flight,
2026-09-11 — the original draft proposed them as DF-1 through DF-6 and left the register numbers to
Cooper; they are no longer proposals). Written as decisions rather than guidance because each one, if
reversed later, invalidates work done under it.

**D27 (was DF-1) — The Massive float endpoint is banned from any computed quantity.**
`/stocks/vX/float` is documented "Plan History: Not applicable to this endpoint." It is a current
snapshot with no date parameter and no history, and it is marked experimental. Joining it to an event
from 2020–2024 — after an unknown number of offerings and reverse splits — is a lookahead of the same
class as D4's spine contamination and is treated the same way: it may be fetched and stored for
orientation in the raw archive, and it may never appear in `event_fundamentals` or any table a
downstream phase reads.

**D28 (was DF-2) — The as-of anchor is the acceptance timestamp of the latest filing strictly before
`t0`.** Not the event date. Not the period end. Not `filing_date`, which is a date and cannot
distinguish a filing accepted after the close from one accepted pre-open — a distinction that decides
correctness for every pre-market event. Acceptance timestamps come from the SEC filing index, not from
the vendor.

**D29 (was DF-3) — Every stored value carries its own as-of timestamp, lag, quality flag, and source
accession number, grouped by source vintage.**
Provenance attaches to the **vintage**, not to each field: all financial line items drawn from one
filing share one acceptance timestamp and one accession number, so the provenance columns are carried
once per group rather than once per field. Groups are declared in §4.

**D30 (was DF-4) — Joins resolve on the SEC Central Index Key, resolved as of `t0`, never on ticker.**
The universe is **2,930 tickers** across the 20,951 in-scope events (D1's 2,576 is a different, smaller
frame — 15,763 events, per `results/reports/phase_9_report.md` — and does not apply here; the original
work order mis-cited it against this build's population, corrected per Amendment F1-A1 §6) in the corner
of the market where symbols are recycled after delisting and reverse splits are routine. A ticker-keyed
join silently attaches one company's balance sheet to another company's event.

**D31 (was DF-5) — Share counts are stored as filed.**
No adjustment into any price basis at write time. Split factors are carried as a separate series so that
any later conversion is explicit and auditable. This programme already carries one documented
adjustment-basis mismatch; it does not need a second.

**D32 (was DF-6) — No fundamental column is put against any outcome variable under this work order.**
The build, the parse, the coverage report and the float construction proceed without an analysis gate.
The first regression, split, or conditional expectancy computed against a fundamental column requires a
written sentence naming the decision the result would change. That sentence does not exist yet.
**Producing one is Cooper's, and it is not a task in this document.**

**D33 (new, not in the original draft) — t0 for this build is a tiered construction.** See §0 above and
`docs/Universe-Decisions.md` D33 for the full reasoning: neither the spine nor any single existing
detection artifact covers the universe at one precision, so `t0_spine.parquet` is assembled from the
finest anchor actually available per event, with the source recorded per row.

---

## 2. Format decision — and why it is neither of the two options proposed

The proposed options were **a dict per momentum event** or **new columns on the momentum event file.** The
grain in the first instinct is right: **one record per event, carrying every value.** The container is wrong
in both cases, for different reasons.

**Against a dictionary or JSON blob per event:**

- The archive is DuckDB over parquet — a columnar store. A blob defeats predicate pushdown and column
  pruning, so every query that touches one field reads all of them, across 20,951 rows and eventually the
  full population.
- It has no typed nulls. "Missing" and "present but zero" become indistinguishable at the storage layer,
  which is precisely the distinction the `unavailable` quality flag exists to preserve.
- **It cannot be asserted on.** The Verification Block requires executable schema and membership assertions.
  A blob has no schema to assert against, so schema drift becomes invisible — the exact failure mode the
  assertion requirement was introduced to close.

**Against new columns on the momentum event file:**

- `momentum_events_canonical` is a **view**, created or replaced by `src/data/canonical.py::create_view`.
  Columns added to it do not persist; they are destroyed on the next regeneration.
- It is the **universe definition**. Putting rented vendor data inside the object that defines membership is
  how a fundamental field ends up in a selection criterion by accident — the q05 lookahead, one layer up and
  with a worse source.
- D4's quarantine draws a line at that table. Widening it is the wrong direction.

**The build instead is three layers, and the third layer is the dict-per-event instinct materialised as typed
columns:**

| layer | location | content | who reads it |
|---|---|---|---|
| **Raw** | `data/raw/fundamentals/<source>/<fetch_date>/` | exactly what came back over the wire, unmodified, with a fetch manifest and checksums | nothing downstream — audit only |
| **Normalized facts** | `data/fundamentals/*.parquet` | one table per source concept, keyed by Central Index Key and timestamp, many rows per company | the assembly step |
| **Event join** | `data/fundamentals/event_fundamentals.parquet` | **one row per `event_id`**, wide, typed, fully provenanced | analysis, once D32 is satisfied |

The normalized layer exists so that nothing is destroyed by the as-of join. The event layer exists so that a
downstream query is one join away from the spine. Rebuilding the event layer from the normalized layer must
be deterministic and cheap — if the as-of rule changes, it is one re-run, not a re-fetch.

A fourth artifact, **`t0_spine.parquet`** (D33), sits between the spine and the normalized layer: it is
built once, before F1-T1, and is what makes the event join's `t0` well-defined at all.

---

## 3. Task sequence

Tasks are ordered by **what has a clock on it**. Massive data is rented and expires with the subscription;
SEC data is free, permanent, and needs no key. The rented pull therefore comes early and broad, and the
expensive float tiers come after the coverage report says which events they would actually change.

### F1-PF — Pre-flight (new, not in the original draft)

- [x] **F1-PF1** — Register D27–D33 in `docs/Universe-Decisions.md`; update `CLAUDE.md`'s decision index
      in the same commit.
- [x] **F1-PF2** — Draft D14 Amendment A1 (scoped network exception for F1-T0/F1-T2/F1-T3 — F1-T0
      was missing from the first draft of this amendment and was added before F1-T0 ran, not after).
- [x] **F1-PF3** — Commit this file (`prompts/fundamentals_f1.md`), create `research/fundamentals_f1/`,
      `config/fundamentals_f1.json` skeleton.
- [x] **F1-PF4** — Branch `build/fundamentals-f1` (off `phase/10e`, not `master` — see the reconciliation
      note at the top of this file).
- [ ] **F1-PF5** — Build `t0_spine.parquet` per D33's tiering rule. Blocking for F1-T1.

### F1-T0 — The restatement test. Gate. Stop and post.

Massive's documentation is self-contradictory on the only question that matters for point-in-time use. It
says values are returned **as restated in the most recent filing, not as originally submitted**. It also says
multiple records may share a `filing_date` *because* filings restate prior comparatives — which implies
records are keyed by filing vintage and that filtering on `filing_date` is a valid as-of filter. Both cannot
be true.

**Needs the same Massive financials entitlement as F1-T2a below — check that first, so an authorization
failure here isn't misread as a data finding.** Confirmed 2026-09-11: `GET /vX/reference/financials`
returns 200 for a live query (`AAPL`), entitlement is not the blocker.

- [x] **F1-T0a** — Select a company in the universe with a known restatement or a filed amendment (form
      10-K/A or 10-Q/A). Record how it was identified. **Done, with a correction along the way:** a
      plain search for any 10-K/A in the universe (17 tickers found via SEC EDGAR full-text search
      cross-referenced against the universe ticker list) repeatedly surfaced administrative,
      Part-III-only amendments filed ~1 month after the original — a well-known small-cap compliance
      pattern (adding director/officer compensation disclosure that would otherwise need a proxy
      statement) that never touches financial-statement values and cannot distinguish either outcome
      branch below. **AGAE** and **CLRB** were confirmed instead via an 8-K Item 4.02 ("Non-Reliance on
      Previously Issued Financial Statements") search — the signal that actually accompanies a genuine
      financial restatement.
- [x] **F1-T0b** — Query the income statement endpoint for the period spanning the restatement, **unfiltered
      by `filing_date`**. Record the full response verbatim into the raw archive. **Done:**
      `research/fundamentals_f1/t0_restatement_test.py`; raw archive at
      `data/raw/fundamentals/massive/2026-09-11/t0_restatement_test/{AGAE,CLRB}_all_unfiltered.json`
      (18 and 59 records respectively, full history, every timeframe).
- [x] **F1-T0c** — Report: how many records exist for that single period, whether each carries a distinct
      `filing_date`, and whether the values differ between them. **Done:** zero duplicate
      `(start_date, end_date, timeframe)` keys in either company's complete history. The decisive
      check went further — CLRB's FY2023 record queried with `filing_date.lt=2024-08-09` (before its
      Item 4.02 8-K) returned **byte-identical** `filing_date` and `revenues` to an unfiltered query.
      `filing_date` does not gate the response to an earlier vintage; there is no earlier vintage to
      gate to.
- [x] **F1-T0d** — Repeat on a second company independently. One case is an anecdote. **Done:** AGAE and
      CLRB are independent companies, independent restatement mechanisms (administrative 10-K/A vs. a
      genuine Item 4.02 non-reliance event), same result.
- [x] **F1-T0e** — **Stop and post.** Do not proceed to any other task. **STOPPED HERE, 2026-09-11.**
      See outcome below — escalation row 1 fires. **Superseded 2026-09-12 by Amendment F1-A1 and
      F1-T0f/T0g below — the test above correctly established "one record per period" but not *which*
      vintage that record is; that question needed a second test.**
- [x] **F1-T0f** — Amendment F1-A1 §0, the disambiguating query. **Done, 2026-09-12: Outcome A.** CLRB's
      vendor `NetIncomeLoss` for FY2023 (-37,983,496, `filing_date=2024-03-27`) matches its *original*
      10-K (accession `0001410578-24-000307`) exactly — not its restated 10-K/A (accession
      `0001410578-24-001704`, filed 2024-10-29, value -42,770,610). **The vendor is point-in-time; it is
      frozen at first-filed and never updated on restatement.** `research/fundamentals_f1/t0f_t0g_disambiguation.py`,
      `results/fundamentals_f1/artifacts/t0f_t0g_disambiguation_summary.json`.
- [x] **F1-T0g** — Amendment F1-A1 §2, `companyfacts` multi-vintage verification on CLRB. **Done,
      2026-09-12: multi-vintage confirmed.** `NetIncomeLoss` for CLRB FY2023 has 5 observations across 5
      distinct accession numbers, 2 distinct values (-37,983,496 pre-restatement, -42,770,610 post), and
      the restated value correctly propagates into the FY2024 10-K's comparative column. `companyfacts`
      is genuinely multi-vintage. Same script/summary as F1-T0f.

| outcome | consequence |
|---|---|
| Multiple records per period, distinct `filing_date`, differing values | The vendor data is point-in-time. `filing_date < t0` is a valid as-of filter. Proceed as written. |
| One record per period carrying the latest values — CONFIRMED, 2026-09-11, then resolved further | The vendor financials are not point-in-time *in the sense of carrying multiple vintages* — but F1-T0f (2026-09-12) established the single record IS the original as-filed value, not the latest restated one. **Escalation row 1a fires: not a stop, a simplification.** See §6 below for the current escalation state. |

**Full outcome, superseding the row above:** `prompts/fundamentals_f1_amendment_a1.md` §0/§8. F1-T1 and
F1-T2 are unblocked (Amendment F1-A1 §4); `fin_` may be built from the vendor as originally planned
(Amendment F1-A1 §5, this file's §4 schema section).

### F1-T1 — Identity spine

**Done, 2026-09-12 — with a methodology correction caught mid-task, not after.** The first
implementation pre-filtered tickers via `/v3/reference/tickers?ticker=X&active=true/false`, treating
a ticker as unambiguous whenever that cheap enumeration found only one CIK, and skipping per-event
as-of resolution for it. That run found **zero** ambiguous tickers across all 2,930 — suspiciously
clean for a universe this file's own D30 text describes as "a corner of the market where symbols are
recycled after delisting and reverse splits are routine." Spot-checking the widest-date-span tickers
directly (querying `date=<earliest event>` vs. `date=<latest event>`) found a confirmed counter-example
the pre-filter missed entirely: **`NTRP`** resolves to "Neurotrope, Inc." (CIK `0001513856`) on
2020-01-22 and "NextTrip, Inc." (CIK `0000788611`) on 2025-10-24 — two different SEC registrants — and
the `active=true/false` enumeration for that exact ticker string found only one candidate. **The
shortcut method is unreliable and was not used in the result below** — every one of the 20,951 events
was resolved independently via its own `date`-parameterized query instead.
`research/fundamentals_f1/t1_identity.py`, `results/fundamentals_f1/artifacts/t1_identity_summary.json`.

- [x] **F1-T1a** — Built `ticker_identity` (`results/fundamentals_f1/artifacts/ticker_identity.parquet`):
      every `(ticker, t0)` pair resolved independently via `/v3/reference/tickers?ticker=X&date=<event_date>`
      (`t0`/event date from `t0_spine.parquet`, F1-PF5). SEC's `company_tickers.json` (current-snapshot
      cross-check, since SEC publishes no bulk historical ticker→CIK mapping) agrees on **98.66%**
      (18,083/18,329 checkable events) — a real, non-trivial disagreement rate, reported rather than
      investigated further here, since it validates only the *current* end of each ticker's history.
- [x] **F1-T1b** — CIK stored zero-padded to 10 characters, string type, throughout.
- [x] **F1-T1c** — **37 tickers** (313 events) flagged `resolved_ambiguous` — every event on a ticker
      whose *own events in this universe* resolved to more than one distinct CIK, with all distinct
      CIKs recorded per event (not only the events sitting on the "wrong" side of the split). The
      superseded shortcut method would have missed the CIK entirely for **84 tickers** — reported as
      `shortcut_blind_spots` in the summary so the discrepancy stays visible rather than disappearing
      the way it did on the first run.
- [x] **F1-T1d** — `resolved_exact` 20,390 (97.32%) / `resolved_ambiguous` 313 (1.49%) / `unresolved`
      248 (1.18%). Combined ambiguous+unresolved = **2.68%**, under the 5% escalation-row-2 threshold —
      **does not fire.** Cross-cut by year and by currently-delisted status in the summary JSON.
      Chart: `results/fundamentals_f1/charts/t1_identity_quality_by_year.html`.
- [x] **F1-T1e** — Committed.

### F1-T2 — Massive bulk pull. Network step. This is the piece with a deadline.

Runs connected, writes the raw archive, then stops. Everything after it is offline. **Gated on D14
Amendment A1 being committed first (F1-PF2) — do not start otherwise.** **Unblocked and the priority,
per Amendment F1-A1 §4 (2026-09-12): the F1-T0 finding bore on financial-statement vintages only. Six of
the ten endpoints below are unaffected — ticker details/events (current reference data, F1-T1
prerequisite), splits/dividends (dated corporate-action records, not restated statements), short
interest/volume (dated observations with their own settlement dates) — and they are the rented ones with
a subscription expiry behind them. F1-T0f's Outcome A (2026-09-12) confirms the financials/ratios
endpoints themselves are usable too (§4's caution has been resolved in the pull's favor), but the
provenance marking below stays as designed regardless — it costs nothing and the cross-check value holds.**

- [x] **F1-T2a** — Confirm the subscription actually includes what is needed. Financials require Stocks
      Developer or above, **or** Stocks Starter plus the Financials and Ratios expansion. **If an endpoint
      returns an authorization error, stop and post. Do not work around it, do not substitute a different
      endpoint, do not scrape.** Confirmed 2026-09-11 during F1-T0: `GET /vX/reference/financials` returns
      200 live, entitlement is not the blocker. **`ratios` has no reachable endpoint** at any of 4 plausible
      paths tried (all 404) — recorded `not_found`, not substituted or scraped, per this task's own
      instruction.
- [x] **F1-T2b** — Pull, for every Central Index Key in `ticker_identity`, across the full available history
      (records begin 2009-03-29): **income statements, balance sheets, cash flow statements, ratios, ticker
      details, ticker events, splits, dividends, short interest, short volume.** Pull by Central Index Key,
      not by ticker. **Amended, Amendment F1-A1 §4:** the fetch manifest for financial statements and
      ratios records `source_of_record: false` — archived as the `companyfacts` cross-check harness and
      the F1-T0f/g evidence base, and per F1-T0f's Outcome A they may now also populate `fin_` directly
      (`fin_source = vendor_archive`), which reverses the original "may not populate `fin_`" default this
      amendment's first draft set for the Outcome-B case. **Run 2026-09-12**
      (`research/fundamentals_f1/t2_massive_pull.py`): all 2,935 distinct resolved CIKs, all 8 working
      endpoints succeeded. **Two bugs caught and fixed before the full-scale run:** (1) pagination —
      `next_params` was set to `None` on subsequent pages, which crashed unpacking `**params`; fixed to
      `{}` (the vendor's `next_url` already carries its full query string). (2) **silent parameter
      mishandling** — `short_interest`, `short_volume`, `float`, and `splits` return HTTP 200 with an
      arbitrary *unfiltered* result (observed tickers "A", "DPU", "GECCG" for the same requested CIK across
      repeated tests) when passed `cik=`, with no error signal at all — worse than an outright rejection,
      since a script trusting it would have archived confidently wrong data. Fixed by pulling those four
      endpoints (plus `dividends`, same family) **by ticker** instead, using the F1-T1-verified ticker
      string per CIK — identity resolution is still respected, just not via a `cik=` parameter these
      endpoints don't actually honor. Both fixes validated on CLRB (paginated correctly, 78 financials
      records) before the full run. Result: `financials` 111,459 records, `ticker_details` 3,110,
      `splits` 2,554, `dividends` 35,356, `short_interest` 440,244, `short_volume` 1,776,508, `float` 2,671,
      `ticker_events` 2,655 — all 2,935 CIKs, zero failures. Full summary:
      `results/fundamentals_f1/artifacts/t2_pull_summary.json`.
- [x] **F1-T2c** — Pull the float endpoint too, once, and store it in the raw archive **only**. It is banned
      from the event layer by D27. Its presence in the archive is so that D27 can be audited later, not so
      that it can be used. Done as part of F1-T2b's run — 2,671 records across 2,935 CIKs (264 empty,
      expected: not every ticker has a float record). `source_of_record: false` in the manifest.
- [x] **F1-T2d** — Write a fetch manifest per source: endpoint, parameters, request timestamp, record count,
      file checksum. Archive raw responses unmodified.
      `data/raw/fundamentals/massive/2026-09-12/fetch_manifest.json` — one entry per source (endpoint,
      keyed_by, source_of_record, n_ciks_pulled, total_records, request_timestamp_utc).
      **Self-caught correction, 2026-09-12, during F1-T5d verification-script drafting:** per-file SHA256
      checksums were computed during the pull but never actually persisted anywhere — `fetch_manifest.json`
      only ever carried the aggregate per-source stats above. Fixed two ways: (1) `t2_massive_pull.py`
      now writes a separate `checksums.json` (source → filename → sha256) every run, not just this one;
      (2) retroactively computed and persisted `checksums.json` for the already-pulled archive (files
      unchanged since the pull, safe to hash after the fact). Verified complete: all 8 sources present,
      all 2,935 CIKs per source, 23,480 files, 23,480 checksums recorded.
- [x] **F1-T2e** — Document the schema of every archived source in `docs/data/fundamentals_sources.md`,
      version-controlled. Done — per-source field list, sample record, and a summary table (endpoint, key,
      source_of_record, n, total records) added to `docs/data/fundamentals_sources.md`'s "Massive vendor
      pull" section. Integrity spot-check (5 random files/source plus a full-population size/zero-length
      scan, all 8 sources): zero malformed-JSON files, zero non-list payloads, sizes consistent with each
      endpoint's expected volume. Archive: 23,480 files, 2.17 GB total.
- [x] **F1-T2f** — Commit. **The network step is now closed.**

> **Note on short interest and short volume.** These are not fundamentals and were not in the original
> request. They are in the pull because they are rented like everything else, they are event-dated, and they
> bear directly on a long-only bull-to-bear-flip thesis. Archiving them costs one endpoint each. Not
> archiving them costs a second subscription window later.

### F1-T3 — Filing index and event proximity

Free, permanent, and a prerequisite for D28 — the acceptance timestamp exists nowhere else. **Also gated
on D14 Amendment A1 (F1-PF2).**

- [x] **F1-T3a** — Download the EDGAR daily index for 2020-01-01 through the universe end date. Declare a
      descriptive User-Agent with a contact address, as the SEC requires, and respect the published request
      rate. Prefer the bulk archives over per-company calls wherever both exist.
      **Deviates from "prefer bulk" after checking why the bulk route doesn't actually satisfy F1-T3b:**
      the daily/full-index files carry a filing DATE only, no time, and `accepted_ns` is explicitly the
      load-bearing column. Used per-CIK `data.sec.gov/submissions/CIK##########.json` instead (itself a
      bulk-per-company pull, ~1 request/CIK, older-history pages fetched only when a CIK's "recent" window
      didn't reach back far enough) — full reasoning in `research/fundamentals_f1/t3_filing_index.py`'s
      docstring. **Timezone verified, not assumed:** cross-checked one filing's JSON `acceptanceDateTime`
      (`"...Z"` suffix) against its own human-readable index page, which independently confirmed the JSON
      value is genuine UTC. Run 2026-09-12: 2,935/2,935 CIKs pulled, paced at ~9 req/s.
- [x] **F1-T3b** — Build `sec_filings`: `cik`, `accession`, `form_type`, `accepted_ns`, `period_of_report`,
      `filing_date`. `accepted_ns` is the load-bearing column. **938,063 rows** after filtering to
      `[2019-12-04, 2025-11-05]` (2020-01-01 floor padded −30d/+5d for F1-T3d) and dropping rows with no
      parseable `accepted_ns`. `results/fundamentals_f1/artifacts/sec_filings.parquet`.
- [x] **F1-T3c** — Build `event_filing_proximity`, one row per event: the nearest filing with
      `accepted_ns < t0_ns`, its form type, its accession, and the elapsed time. Plus counts of filings in the
      preceding 24 hours and 72 hours. **20,951 rows** (exact universe). `flg_quality`: observed=20,683,
      unavailable=248 (matches F1-T1's unresolved-identity count exactly), no_filings_in_window=20.
      `results/fundamentals_f1/artifacts/event_filing_proximity.parquet`.
- [x] **F1-T3d** — Build `event_filings_window`, one row per `(event_id, accession)` for every filing within
      **−30 days to +5 days** of `t0`. This is the long companion table; nothing is lost to the as-of
      collapse in F1-T3c. **139,039 rows.** `results/fundamentals_f1/artifacts/event_filings_window.parquet`.
- [x] **F1-T3e** — Derive `flg_dilution_form_before_t0`: true when the nearest prior filing, or any filing in
      the preceding 72 hours, is in the **declared dilution form set**. Write the set out explicitly in
      `docs/data/fundamentals_sources.md` — at minimum the 424B prospectus-supplement family, S-1, S-3, and
      their effectiveness amendments, and 8-K filings reporting unregistered sales of equity securities. **The
      set is a documented decision, not an inline literal buried in code.** Set already recorded in
      `config/fundamentals_f1.json`'s `dilution_form_set` (F1-PF3); 8-K rows also checked for Item 3.02 in
      the `items` field, not form type alone. **TRUE for 1,726/20,951 events (8.2%).**
- [x] **F1-T3f** — **Report a number this programme specifically needs:** the count of events where a filing
      is accepted **between the instantaneous threshold crossing and the 60-second poll boundary.** D7 makes
      detection a family indexed by polling interval, so a filing landing inside that window means filing
      proximity is also a family, not a scalar. **Per D33, this is answerable only for the `nanosecond_poll1`
      tier of `t0_spine.parquet` (110 events)** — the other two tiers do not carry instantaneous-crossing
      precision, and this task reports that limitation explicitly rather than extrapolating from a coarser
      tier. If the count on that tier is zero, that is a sentence in the digest and the question is closed for
      that tier. If it is not zero, **stop and post** — it needs a decision, not a default.
      **Run: count is zero (0/110). Escalation row 6 does not fire — closed for this tier.**
      `results/fundamentals_f1/artifacts/t3f_poll_boundary_summary.json`.
- [x] **F1-T3g** — Chart: distribution of time-since-nearest-filing, and the form-type mix of the nearest
      prior filing. Commit. `results/fundamentals_f1/charts/t3_filing_proximity.html`.
- [x] **F1-T3h** — **New, Amendment F1-A1 §3.** From the filing index F1-T3 builds anyway: count in-scope
      **companies** and **events** where an 8-K Item 4.02, a 10-K/A, or a 10-Q/A **amending financial
      statements** (not a Part-III-only amendment — see the identification-method note in
      `docs/data/fundamentals_sources.md`) was accepted **after** the event's `fin_` vintage. Report as a
      share of the 20,951, cross-cut by year. Free — uses data already required for D28. **Decides
      escalation row 1c**: small (single-digit percent) means `fin_superseded_later` as a flag is
      adequate and F1-T4b stays optional; large means F1-T4b becomes mandatory. **The threshold is
      Cooper's, set before F1-T3 runs, not after seeing the number** (Amendment F1-A1 §9).
      **Signal used: 8-K Item 4.02 only** — checked directly (not assumed) whether `isXBRL`/`isInlineXBRL`
      metadata could cheaply separate genuine 10-K/A restatements from the Part-III-only administrative
      ones F1-T0 already found dominate this universe; it cannot (CLRB's own confirmed Part-III-only 2021
      10-K/A and confirmed genuine 2024 restatement both show `isXBRL=1`). Raw 10-K/A/10-Q/A-after-vintage
      counts reported separately, unclassified, never folded into the primary share. **Result: 776/20,951
      events (3.70% of the universe; 9.35% of the 8,303 events that had a measurable `fin_` vintage at
      all) — below Cooper's 10% threshold. Escalation row 1c does not fire; F1-T4f stays optional.**
      By year: 2020=0.73%, 2021=0.16%, 2022=0.35%, 2023=5.53%, 2024=7.36%, 2025=3.82%.
      `results/fundamentals_f1/artifacts/t3h_blast_radius_summary.json`.
      **Side finding, worth carrying into F1-T6:** only 8,303/20,951 events (39.6%) have ANY vendor
      financials record dated before `t0` at all. Diagnosed, not just observed — of events whose CIK has
      *some* financials record, the share where even the *earliest* one is still after `t0` is 93–97% for
      2020–2022 events but only 2–3% for 2024–2025. This reads as the vendor's financials coverage for this
      specific (small/thin, momentum-event) universe genuinely starting around 2022–2023, not a join bug —
      confirmed via `pd.read_parquet('financials_vintages.parquet')`'s own `accepted_ns` range (2009–2026,
      so the vendor has old data for *some* companies, just not most of the ones in this universe before
      that point). Carried into F1-T6a's coverage-by-year cross-cut, not silently absorbed into `fin_quality
      = unavailable` without comment.

### F1-T4 — Float tier 1: shares outstanding

**Do not start until Cooper sets the `filed_stale` lag threshold (§4, suggested placeholder 45 days) and
the `shs_quality` coverage floor (escalation row 5, suggested placeholder 70%). Both must be recorded in
`docs/data/fundamentals_sources.md` before this task runs, not adopted silently from the placeholders.**

- [x] **F1-T4a** — Download the SEC `companyfacts.zip` bulk archive. **Check its size before downloading** —
      it is multi-gigabyte and growing, and the disk budget should be confirmed rather than discovered.
      **Deviates after checking:** `HEAD` returned 1,408,785,961 bytes (1.4 GB) — disk was never the binding
      constraint (366 GB free), but the archive covers ~800,000+ filers to serve 2,935 (0.4%), and this build
      already hit real friction extracting a 23,480-file archive on this Windows/NTFS setup in F1-T2. Used
      per-CIK `data.sec.gov/api/xbrl/companyfacts/CIK##########.json` instead (same data, already proven in
      F1-T0g) — full reasoning in `research/fundamentals_f1/t4_shares_outstanding.py`'s docstring.
- [x] **F1-T4b** — Extract `dei:EntityCommonStockSharesOutstanding` for every Central Index Key in the
      universe. This is the **cover-page share count** — total shares issued as stated on the filing's cover,
      not float. Run 2026-09-12: 2,935/2,935 CIKs, 13 with no companyfacts record at all, 380 with
      companyfacts but no shares-outstanding tag.
- [x] **F1-T4c** — Build `shares_outstanding_observations`: `cik`, `shares`, `asof_ns` (the cover date the
      figure is stated as of), `accepted_ns`, `source_form`, `accession`. One row per observation. Keep every
      observation, including superseded ones. **84,826 rows, 2,542 distinct CIKs.** `accepted_ns` is not a
      native `companyfacts` field (`filed` is date-only, no time) — sourced via `(cik, accession)` join
      against F1-T3's `sec_filings`. 43,044 rows (50.7%) have no match — diagnosed, not assumed benign:
      **100% of the unmatched rows fall strictly outside F1-T3's fetch window** (either before 2019-12-04 —
      old historical observations no event needs — or after 2025-11-05 — the archive's own 2026-09-12 fetch
      date reaches well past every event's window). Zero genuine gaps inside the window.
      `results/fundamentals_f1/artifacts/shares_outstanding_observations.parquet`.
- [x] **F1-T4d** — Cross-check against the vendor's own share-count fields where both exist. **Report the
      disagreement distribution.** Do not reconcile them, do not pick a winner — report it. A systematic
      disagreement is a finding about the sources and belongs in the digest. **6,940 events have both** the
      SEC cover-page count (`shs_shares_outstanding`) and the vendor's average-shares figure
      (`fin_shares_basic`) — different concepts by construction (point-in-time count vs. period-average),
      so a disagreement here is expected, not necessarily an error. Ratio (SEC / vendor): median 1.03,
      p25–p75 = 1.00–1.26 (the bulk agrees closely), but the tail is extreme — p99 = 1,040×, max = 13.4M×.
      45.7% of events agree within 5%, 66.0% within 20%. **Not reconciled, not clipped** — the extreme tail
      is reported as-is; likely a units/definition mismatch on a handful of filings, not investigated further
      per this task's own "report it, don't fix it" instruction. `results/fundamentals_f1/artifacts/t4d_share_count_disagreement.json`.
- [x] **F1-T4e** — Commit.
- [ ] **F1-T4f** — **New, Amendment F1-A1 §2/§7 — renumbered from the amendment's "F1-T4b" to avoid
      colliding with the existing F1-T4b above (shares-outstanding extraction), which the amendment's
      own task-order table did not account for.** Build `fin_` from `companyfacts` element mapping, per
      Amendment F1-A1 §2: a declared element-priority list per `fin_` line item (nine concepts — revenue,
      net income, cash and equivalents, total assets, total liabilities, stockholders' equity, operating
      cash flow, basic/diluted shares — each may be tagged under multiple US-GAAP element names across
      filers), written into `docs/data/fundamentals_sources.md` before this task runs. **Invoke
      `reuse-before-build`/`prior-art-check` before writing the mapping by hand** — element
      normalization over `companyfacts` is solved in maintained libraries. **Conditional: only mandatory
      if F1-T3h's blast radius exceeds Cooper's threshold (escalation row 1c); otherwise optional**,
      since F1-T0f's Outcome A means the vendor archive already satisfies `fin_`'s primary path and this
      task's output would serve `fin_n_vintages`/`fin_superseded_later` and the cross-check harness only.
      **Not built — F1-T3h's blast radius (3.70%) stayed below Cooper's 10% threshold, so this stays optional
      per its own conditional. Left undone deliberately, not by oversight.**

### F1-T5 — Assemble `event_fundamentals`

- [x] **F1-T5a** — Build the table to the schema in §4, using an as-of join (DuckDB's `ASOF JOIN`, natively
      supported — DuckDB 1.4.4 confirmed installed) on `accepted_ns < t0_ns`, strictly less than, per group.
      `t0_ns`/`t0_source` come from `t0_spine.parquet` (F1-PF5) — not re-derived here. **`shs_` is the one
      exception**, per F1-T5d's own finding below — a plain ASOF on `accepted_ns` alone was insufficient.
      `data/fundamentals/event_fundamentals.parquet`, 20,951 rows.
- [x] **F1-T5b** — Compute `*_lag_ns` for every group as `t0_ns − asof_ns`. Carry it as a column. **A share
      count 40 days stale is a different measurement from one 2 days stale**, and pooling them without the lag
      visible repeats the events-do-not-share-a-clock error one layer up.
      `results/fundamentals_f1/charts/t6_lag_distributions.html`.
- [x] **F1-T5c** — Set quality flags per §4. **No imputation, no forward-fill beyond the declared as-of rule,
      no dropping.**
- [x] **F1-T5d** — Run the Verification Block in §5, in the structured drift-dict + exit-code + `--json`
      style of `tools/verify_cited_paths.py`. **Every assertion must pass before the table is committed.**
      **First run found 3 real defects, all fixed before the table was accepted as final — not silently
      routed around:**
      1. `event_id_set_equality` — false 100% mismatch, caused by the verification script itself, not the
         table: `quotes_bitmaps_all.parquet`'s `event_date_canonical` is `datetime64[ns]`, and an unguarded
         f-string rendered `"2021-01-28 00:00:00"` instead of `"2021-01-28"`. Fixed by normalizing to a date
         string before computing `event_id`.
      2. `no_lookahead` — **a genuine hard-stop condition, investigated to its actual source before fixing.**
         5 events had `shs_asof_ns >= t0_ns` despite `shs_accepted_ns < t0_ns`. Checked the raw
         `companyfacts` record directly (not assumed a join bug): a `dei:EntityCommonStockSharesOutstanding`
         cover-page "as of" date can genuinely postdate its own filing's SEC acceptance timestamp (confirmed
         on MDRR's accession `0001104659-20-037784`: `end=2020-03-31`, `filed=2020-03-24`) — a real source
         quirk, not corruption. DuckDB's `ASOF JOIN` supports exactly one inequality column, so the `shs_`
         join was rewritten as a window-function nearest-match requiring **both** `accepted_ns < t0_ns` AND
         `asof_ns < t0_ns` before ranking. `shs_quality` shifted by 3 rows after the fix (`filed_exact`
         5,410→5,407, `unavailable` 4,849→4,852) — the events whose only candidate observation failed the
         added constraint.
      3. `quality_enum_domains` — `fin_quality`'s value `as_filed_superseded_later` (Amendment F1-A1's
         revision to the schema) was never added to `config/fundamentals_f1.json`'s `quality_enums.fin_quality`
         list, which still carried the pre-amendment 3-value enum. Fixed the config.

      **Separately, while investigating a suspicious 100%-clean `spl_quality` result** (0 unavailable across
      all 20,951 events, before this script even ran) **found a second real bug**: `spl_n_splits_365d` used
      `count(*)` over a `LEFT JOIN`, which counts the phantom all-NULL row a `LEFT JOIN` emits for zero
      matches as 1 — so every event with genuinely zero splits showed count=1, not 0, making
      `spl_quality='observed'` fire universally. The *identical* bug was then found and fixed in
      `t3_filing_index.py`'s already-committed `flg_n_filings_72h` (confirmed directly: `flg_quality=
      unavailable` events, which cannot possibly match anything, showed `flg_n_filings_72h=1`). Fixed both
      to `count(<a_real_column>)`, which correctly excludes the outer-join's NULL placeholder row.
      `event_filing_proximity.parquet` and `event_fundamentals.parquet` both rebuilt after the fix.
      **All 9 Verification Block checks pass on the corrected table.**
- [x] **F1-T5e** — Commit.

### F1-T6 — Coverage report. Gate. Stop and post.

- [x] **F1-T6a** — Report coverage of every group, cross-cut by **year, detection-price decile, delisted
      status, and exchange**. **Overall coverage** (share with `*_quality != 'unavailable'`, n=20,951):
      `flg`=98.8%, `shs`=76.8%, `fin`=39.6%, `si`=97.3%, `spl`=41.7%. **Escalation row 5** (`shs_quality
      != 'unavailable'` for < 70%) **does not fire** — 76.8% clears Cooper's 70% floor.
      **Detection price**: tick-derived (`v2_r13_detection`'s `cross_price` / `a102_detection_anchors`'s
      `det_price_lat0` / a direct re-read of each `first_trade_fallback` event's own `trades.parquet`) —
      not a spine numeric, not D4-restricted, never stored in `event_fundamentals`.
      **Delisted status**: derived from F1-T2's `ticker_details` archive. **Found zero explicit
      `active=false` records anywhere in the archive** — every non-empty response shows `active=true`; the
      267 CIKs with an empty response are most plausibly delisted/inactive tickers the endpoint omits by
      default rather than flags, but this is not confirmed (would need a new `active=false` query, outside
      this build's authorized network scope) — reported as `unknown`, not reclassified as `delisted`, per
      "flag rather than silently resolve." `results/fundamentals_f1/artifacts/t6_context_summary.json`,
      `t6_coverage_report.json`.
- [x] **F1-T6b** — Chart the coverage surface. Per the chart contract, the distribution comes before any
      aggregate — no coverage percentage is reported without the distribution behind it.
      `results/fundamentals_f1/charts/t6_coverage_surface.html`.
- [x] **F1-T6c** — **State plainly whether coverage is missing at random.** The expected failure is that it
      is not: late filers, foreign private issuers on annual schedules, shells with thin structured data, and
      companies that delisted and stopped filing are concentrated in the cheapest, thinnest corner of this
      universe — which is where a large share of these events live. **Conditioning analysis on the covered
      subset would be a survivorship filter wearing a data-quality costume**, and a fresh instance of the
      population-level error the q05 line already cost a phase to establish.
      **Confirmed not missing at random — but the dominant axis is YEAR, not company quality.** `fin_`
      coverage by year: 2020=5.2%, 2021=2.4%, 2022=4.6%, 2023=48.4%, 2024=65.8%, 2025=60.9% — a coverage
      cliff around 2022–2023 (matches F1-T3h's side finding), not a gradual decline. By contrast, the
      delisted-status proxy shows almost no difference (`active`=39.7%, `unknown`=39.1%) and the
      price-decile gradient is modest and in the *opposite* direction from the naive "shells have worse
      data" expectation (cheapest decile 51.6% vs priciest decile 37.5%). **Reading:** this universe's `fin_`
      gap is overwhelmingly a vendor historical-backfill boundary for small/thin momentum names, not a
      survivorship pattern concentrated in bad companies — worth stating precisely rather than reaching for
      the generic "thin names have thin data" story the task's own framing anticipated, since the data
      doesn't actually support that specific mechanism here.
- [x] **F1-T6d** — **Stop. Tag. Post.** Tiers 2 and 3 are scoped after this report, not before.

### Out of scope for F1

**Float tier 2** (dilution correction between filings, from prospectus supplements, registration statements,
at-the-market programmes and 8-K unregistered sales) and **float tier 3** (affiliate subtraction from insider
forms 3/4/5 and 5%-holder schedules 13D/13G) are **not in this work order.** They are the expensive tiers,
they are free and permanent to build, and they should be scoped against the F1-T6 coverage report rather than
against ambition fixed in advance. `flg_dilution_form_before_t0` in F1-T3e is the cheap proxy that stands in
until they exist.

**No tier 2 or tier 3 columns are created in this build.** An absent column is honest; a column of nulls that
looks like data is not.

---

## 4. Schema — `event_fundamentals`

One row per `event_id`. Exactly 20,951 rows. Provenance is carried **per group**, not per field.

### Identity and anchor

| column | type | notes |
|---|---|---|
| `event_id` | str | primary key, `f"{ticker}_{event_date_canonical}_{momentum_pct:.2f}"` (`research/phase_10/common.py:215`) |
| `ticker` | str | as of the event |
| `cik` | str | zero-padded to 10 characters |
| `t0_ns` | int64 | event anchor, from `t0_spine.parquet` (D33) |
| `t0_source` | enum | `nanosecond_poll1` / `minute_a102` / `first_trade_fallback` / `unavailable` (D33) |
| `identity_quality` | enum | `resolved_exact` / `resolved_ambiguous` / `unresolved` |

### Group `flg_` — filing proximity (source: SEC daily index)

| column | type | notes |
|---|---|---|
| `flg_last_form` | str, nullable | form type of the nearest filing accepted before `t0` |
| `flg_last_accepted_ns` | int64, nullable | **strictly less than `t0_ns`** |
| `flg_last_accession` | str, nullable | |
| `flg_lag_ns` | int64, nullable | `t0_ns − flg_last_accepted_ns` |
| `flg_n_filings_24h` | int32 | count in the 24 hours before `t0` |
| `flg_n_filings_72h` | int32 | count in the 72 hours before `t0` |
| `flg_dilution_form_before_t0` | bool | against the declared form set (F1-T3e) |
| `flg_quality` | enum | `observed` / `no_filings_in_window` / `unavailable` |

`no_filings_in_window` and `unavailable` are different states and must not be collapsed. The first is a
measurement; the second is an absence of measurement.

### Group `shs_` — shares outstanding (source: SEC cover-page tag)

| column | type | notes |
|---|---|---|
| `shs_shares_outstanding` | int64, nullable | **as filed. Not split-adjusted.** |
| `shs_asof_ns` | int64, nullable | cover date the figure is stated as of |
| `shs_accepted_ns` | int64, nullable | **strictly less than `t0_ns`** |
| `shs_lag_ns` | int64, nullable | `t0_ns − shs_asof_ns` |
| `shs_source_form` | str, nullable | |
| `shs_accession` | str, nullable | |
| `shs_quality` | enum | `filed_exact` / `filed_stale` / `unavailable` |

`filed_exact` versus `filed_stale` is decided by a **declared lag threshold written into
`docs/data/fundamentals_sources.md` before the build runs**, not chosen after seeing the distribution.
Suggested starting value: 45 days. **Cooper sets it — F1-T4 does not start until this is recorded.**

### Group `fin_` — financial statement vintage (source: per F1-T0f outcome — Amendment F1-A1 §5)

| column | type | notes |
|---|---|---|
| `fin_source` | enum | **new, Amendment F1-A1.** `companyfacts` / `vendor_archive` / `unavailable`. No row's provenance may be ambiguous once two possible sources exist. |
| `fin_accession` | str, nullable | the single filing this whole group came from — now sourced from the observation's `accn` when `fin_source = companyfacts` |
| `fin_accepted_ns` | int64, nullable | **strictly less than `t0_ns`** |
| `fin_period_end` | date, nullable | |
| `fin_fiscal_year` | int16, nullable | |
| `fin_fiscal_quarter` | int8, nullable | |
| `fin_timeframe` | enum, nullable | `quarterly` / `annual` / `trailing_twelve_months` |
| `fin_lag_ns` | int64, nullable | `t0_ns − fin_period_end` |
| `fin_quality` | enum | **revised, Amendment F1-A1:** `as_filed` / `as_filed_superseded_later` / `restated_unknown_vintage` / `unavailable`. `as_filed_superseded_later` is the honest state for a correctly point-in-time figure a later filing revised — not a defect, and collapsing it into either neighbour loses the distinction. |
| `fin_n_vintages` | int16 | **new, Amendment F1-A1.** Count of distinct accession numbers reporting this period at or before `t0`. 1 is normal; higher means the period was already revised before the event. |
| `fin_superseded_later` | bool | **new, Amendment F1-A1.** True when any filing *after* `t0` revised this period. **Strictly a diagnostic — knowable only after the fact, and must never enter a computed quantity.** Same quarantine shape as D27 (the Massive float endpoint) and D4. |
| `fin_revenue` | float64, nullable | |
| `fin_net_income` | float64, nullable | |
| `fin_cash_and_equivalents` | float64, nullable | |
| `fin_total_assets` | float64, nullable | |
| `fin_total_liabilities` | float64, nullable | |
| `fin_stockholders_equity` | float64, nullable | |
| `fin_operating_cash_flow` | float64, nullable | |
| `fin_shares_basic` | float64, nullable | |
| `fin_shares_diluted` | float64, nullable | |

**F1-T0f/F1-T0g resolved the outcome (2026-09-12): Outcome A.** The vendor serves original as-filed
values (confirmed on CLRB's FY2023 `NetIncomeLoss`: vendor matches the original 10-K exactly, not the
restated 10-K/A), and is frozen at first-filed rather than updated on restatement. `fin_source =
vendor_archive` is therefore the primary path, `fin_quality = as_filed` the default outcome, and
`restated_unknown_vintage` applies only where a later `companyfacts`/8-K-Item-4.02 cross-check (F1-T3h)
finds the vendor's period was actually superseded and the vendor's own record shows no sign of it.
**`companyfacts` is confirmed genuinely multi-vintage** (F1-T0g: 5 observations, 2 distinct values, one
CLRB period) and remains available as the cross-check harness and the source for `fin_n_vintages` /
`fin_superseded_later`, per Amendment F1-A1 §2 — not as the mandatory primary source it would have been
under Outcome B.

**No derived metrics are stored.** Cash runway, burn rate, and every ratio are computed in analysis from these
line items, so the derivation is visible and versioned in the code that uses it rather than frozen into the
table.

### Group `si_` — short interest (source: vendor)

| column | type | notes |
|---|---|---|
| `si_shares_short` | int64, nullable | |
| `si_settlement_date` | date, nullable | |
| `si_asof_ns` | int64, nullable | **strictly less than `t0_ns`** |
| `si_lag_ns` | int64, nullable | |
| `si_quality` | enum | `observed` / `unavailable` |

Short interest settles twice monthly and publishes on a lag. **The lag here is large by construction** and
the column exists so that nobody forgets it.

### Group `spl_` — split history (source: vendor)

| column | type | notes |
|---|---|---|
| `spl_n_splits_365d` | int16 | splits in the 365 days before `t0` |
| `spl_reverse_split_365d` | bool | any ratio below 1 in that window |
| `spl_last_split_ratio` | float64, nullable | |
| `spl_last_split_ns` | int64, nullable | **strictly less than `t0_ns`** |
| `spl_quality` | enum | `observed` / `unavailable` |

### Companion tables

| table | grain | why it exists |
|---|---|---|
| `t0_spine` | one row per event | the tiered t0 construction (D33); everything below reads this rather than re-deriving t0 |
| `ticker_identity` | `(ticker, t0)` → Central Index Key | the join spine; audit trail for recycled symbols |
| `sec_filings` | one row per filing | the acceptance-timestamp source of record |
| `event_filings_window` | `(event_id, accession)` | nothing is lost to the as-of collapse |
| `shares_outstanding_observations` | one row per observation | every vintage kept, including superseded |
| `financials_vintages` | one row per `(cik, period, filing)` | per the F1-T0 outcome |

---

## 5. Verification Block

Script-level assertions, in the structured drift-dict + exit-code + `--json` twin-output style of
`tools/verify_cited_paths.py` / `tools/verify_claude_md_indices.py`. Each must fail loudly. **Prose
confirmation is not acceptable for any row in this table** — this is the recurring defect this block
exists to close.

- [ ] `event_fundamentals` has exactly **20,951** rows, and `event_id` is unique across them.
- [ ] The `event_id` set equals the `momentum_events_canonical WHERE in_scope = TRUE` set exactly (via
      `results/phase_5/artifacts/quotes_bitmaps_all.parquet`, not a live view scan). Assert set
      equality in both directions, not row counts — **equal counts with different membership is the exact
      defect that has occurred before in this repo.**
- [ ] `t0_spine`'s `nanosecond_poll1` / `minute_a102` / `first_trade_fallback` / `unavailable` tier counts
      sum to exactly 20,951, and the `nanosecond_poll1` tier count is exactly 110. Run and verified:
      110 / 15,259 / 5,582 / 0.
- [ ] For every group, **zero** rows have a non-null `*_accepted_ns`, `*_asof_ns`, or `*_last_split_ns` that
      is greater than or equal to `t0_ns`. Any violation is a hard stop, not a flag.
- [ ] Every quality column contains only values from its declared enum. Assert the domain explicitly; do not
      rely on a `CHECK` constraint the parquet round-trip will not preserve.
- [ ] No column in any output table shares a name with a `momentum_events_canonical` numeric column, and no
      output column is a transform of one. Assert against the live column list, not a hand-written list.
- [ ] Every non-null value in a group is accompanied by a non-null provenance set for that group. **A value
      without an accession number is a bug, not a low-quality row.**
- [ ] Every raw archive file named in a fetch manifest exists and matches its recorded checksum.
- [ ] The event layer rebuilds deterministically from the normalized layer: run the assembly twice and assert
      the outputs are byte-identical.

---

## 6. Escalation rows

Each row has been checked against the four-check audit — measurable, threshold set, reachable, and
non-contradictory with every other row.

**Row 1 is retired (Amendment F1-A1 §8, 2026-09-12).** It fired 2026-09-11, produced Amendment F1-A1, and
is superseded by rows 1a–1c below.

| # | condition | measurable as | action |
|---|---|---|---|
| 1a | F1-T0f shows the vendor serves original as-filed values | comparison in `t0f_t0g_disambiguation_summary.json` | **CONFIRMED, 2026-09-12.** Outcome A. Not a stop — a simplification. `fin_` builds from the vendor archive as originally planned (this file's §4 schema section, revised). |
| 1b | F1-T0g shows `companyfacts` carries one observation per period | `n_distinct_values` in the same summary | Did not fire — **CONFIRMED multi-vintage, 2026-09-12** (5 observations, 2 distinct values on the tested concept). Retained as a standing row for any future company/concept where it might. |
| 1c | F1-T3h blast radius exceeds a threshold **Cooper sets before F1-T3 runs** | share of events, from F1-T3h | The flag-only interim is not available; F1-T4b (the `companyfacts`-based `fin_` build) becomes mandatory rather than optional. **Not yet evaluated — F1-T3 has not run.** |
| 2 | `identity_quality` is not `resolved_exact` for **> 5%** of in-scope events | share of rows, from F1-T1d | **Checked, 2026-09-12: 2.68% (561/20,951). Does not fire.** Stop and post. The join spine is the foundation; a weak one contaminates every group above it. |
| 3 | Any `*_accepted_ns >= t0_ns` in a committed table | assertion in §5 | **Hard stop.** This is a bug in the as-of join, not a data-quality state. |
| 4 | An endpoint returns an authorization or entitlement error | HTTP status | **Stop and post.** Do not substitute an endpoint, do not scrape, do not proceed with partial coverage silently. |
| 5 | `shs_quality != 'unavailable'` for **< 70%** of in-scope events | coverage share, from F1-T6a | **Stop and post before any tier 2 or 3 work is scoped.** Threshold is a placeholder — **Cooper sets it before F1-T4 runs**, not after seeing the number. |
| 6 | Any filing accepted between the instantaneous crossing and the 60-second poll boundary | count, from F1-T3f (nanosecond tier only) | **Stop and post.** Filing proximity becomes a family indexed by polling interval, which is a decision, not a default. |
| 7 | `companyfacts.zip` exceeds the available disk budget | file size checked before download | **Stop and post.** Do not partially extract and proceed. |

Row 5 and row 2 do not conflict: row 2 gates on identity resolution and fires earlier; row 5 gates on share
count coverage and can only be evaluated after F1-T4. **Row 1c's threshold is Cooper's, per Amendment
F1-A1 §9 — not yet set, and F1-T3 does not run until it is.**

---

## 7. Digest contract

The build's digest reports, in this order:

1. The F1-T0 outcome, stated as one of the two branches in §3, in one sentence.
2. Identity resolution counts and shares, with the ambiguous-symbol chart.
3. Row counts and the set-equality assertion result.
4. The t0-tiering breakdown (`nanosecond_poll1` / `minute_a102` / `first_trade_fallback` / `unavailable`
   counts) and a one-sentence note that F1-T3f's poll-boundary question is scoped to the first tier only.
5. Coverage by group, **distribution before aggregate**, cross-cut by year, price decile, delisted status and
   exchange.
6. The lag distribution per group — not the mean, the distribution.
7. The vendor-versus-SEC share-count disagreement distribution from F1-T4d.
8. The F1-T3f poll-boundary count.
9. Every assertion in §5, with pass or fail stated individually.
10. A one-line note that the companion scoping note referenced in the original draft
    (`claude/fundamental_data_float_scoping_note.md`) does not exist in this checkout, and that this build
    proceeded on this file's own inline numbers per the original draft's own stated fallback.

**No finding. No interpretation. The agent describes the picture; Cooper decides what it means.**

---

## 8. What this work order deliberately does not do

- It does not build float. It builds **shares outstanding**, which is a different quantity, and it says so in
  every column name.
- It does not use the vendor float endpoint (D27).
- It does not compute a single derived ratio.
- It does not put any fundamental column against any outcome (D32).
- It does not choose the `filed_stale` threshold or the coverage floor. **Both are Cooper's, and both must be
  set before the run they gate, not after.**
