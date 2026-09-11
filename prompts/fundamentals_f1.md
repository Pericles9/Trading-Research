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

---

## 0. Standing constraints that apply, restated with values

Restated rather than cited, per the rule that a brief must carry its numbers inline.

| constraint | what it means here |
|---|---|
| **D4 — spine numerics quarantined** | `momentum_events_canonical` numeric columns are diagnostic-display only. This build **reads** `ticker`, `event_date_canonical`, `momentum_pct`, and `in_scope` from it and **writes nothing to it**. No output table may carry a spine numeric column under any name, including a transform of one. |
| **D14 — offline environment, amended for this build only** | The archive is offline by default. **D14 Amendment A1** authorizes network access narrowly for F1-T2 (Massive pull) and F1-T3 (SEC EDGAR pull) — immutable raw archives, written once, then stopped. Every other task, and every task after those two, runs offline against those archives. |
| **Flag, never delete** | An event with no usable value is a row with an explicit `unavailable` quality flag. Never dropped, never imputed, never forward-filled silently. |
| **Executable assertions** | Every membership or coverage claim in the digest must be produced by a script-level assertion that fails loudly, in the structured drift-dict + exit-code style of `tools/verify_cited_paths.py` / `tools/verify_claude_md_indices.py` — not a bare `assert`. Prose statements of membership are insufficient — this is the recurring defect pattern (the VEEE/CODX swap, the ticker `.nunique()` bug). |
| **Universe membership** | Inner join to `momentum_events_canonical WHERE in_scope = TRUE`. Target row count: **20,951** — confirmed against `results/phase_5/artifacts/quotes_bitmaps_all.parquet` (D15's own materialization, 20,951 rows), not a live `COUNT(*)` against the view, which is expensive (observed still under 10% complete after ~40 minutes; the view's staged construction joins `filtered_trades`/`filtered_quotes`, 4.9B/3.8B rows, for coverage flags regardless of which columns are selected). |
| **Identity key** | No spine or view column is named `event_id`. This build reuses the de facto convention already standard across `research/phase_10/`, `phase_10e/`, `phase_11/`, `scale_field/` (50+ files), defined once at `research/phase_10/common.py:215`: `f"{ticker}_{event_date_canonical}_{momentum_pct:.2f}"`. No second convention is invented for the same concept. |
| **t0 anchor** | No spine or view column is named `t0`, and no single existing artifact covers the universe at any one precision. Per D33: a tiered construction — nanosecond anchor (`v2_r13_detection.parquet`, 114 events) → minute anchor (`a102_detection_anchors.parquet`, up to 15,763 events) → first-trade fallback (`filtered_trades`, the remainder). Built once as `t0_spine.parquet` before F1-T1; every downstream task reads it rather than re-deriving t0. |
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
The universe is 2,576 tickers in the corner of the market where symbols are recycled after delisting and
reverse splits are routine. A ticker-keyed join silently attaches one company's balance sheet to another
company's event.

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
- [x] **F1-PF2** — Draft D14 Amendment A1 (scoped network exception for F1-T2/F1-T3).
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
failure here isn't misread as a data finding.**

- [ ] **F1-T0a** — Select a company in the universe with a known restatement or a filed amendment (form
      10-K/A or 10-Q/A). Record how it was identified.
- [ ] **F1-T0b** — Query the income statement endpoint for the period spanning the restatement, **unfiltered
      by `filing_date`**. Record the full response verbatim into the raw archive.
- [ ] **F1-T0c** — Report: how many records exist for that single period, whether each carries a distinct
      `filing_date`, and whether the values differ between them.
- [ ] **F1-T0d** — Repeat on a second company independently. One case is an anecdote.
- [ ] **F1-T0e** — **Stop and post.** Do not proceed to any other task.

| outcome | consequence |
|---|---|
| Multiple records per period, distinct `filing_date`, differing values | The vendor data is point-in-time. `filing_date < t0` is a valid as-of filter. Proceed as written. |
| One record per period carrying the latest values | **The vendor financials are not point-in-time.** They may still be archived, but they may not be joined at `t0`. The SEC route becomes the only source of record for financials, and the work order needs an amendment before F1-T2 runs. |

### F1-T1 — Identity spine

- [ ] **F1-T1a** — Build `ticker_identity`: for every `(ticker, t0)` pair in the in-scope universe
      (`t0` from `t0_spine.parquet`, F1-PF5 — **not** assumed to exist trivially), resolve
      the SEC Central Index Key **as of `t0`**, using the vendor's Ticker Details and Ticker Events endpoints
      and the SEC's own ticker-to-identifier mapping as an independent cross-check.
- [ ] **F1-T1b** — Store the key zero-padded to 10 digits, as a string. Never as an integer — leading zeros
      are load-bearing and silently lost on numeric round-trip.
- [ ] **F1-T1c** — Flag every event whose ticker maps to **more than one** Central Index Key across the
      2020–2024 window as `resolved_ambiguous`, with both candidates recorded. These are the recycled symbols
      and they are the whole reason for this task.
- [ ] **F1-T1d** — Report the count and share of `resolved_exact` / `resolved_ambiguous` / `unresolved`,
      cross-cut by year and by whether the ticker is currently delisted. Chart the ambiguous and unresolved
      share by year.
- [ ] **F1-T1e** — Commit.

### F1-T2 — Massive bulk pull. Network step. This is the piece with a deadline.

Runs connected, writes the raw archive, then stops. Everything after it is offline. **Gated on D14
Amendment A1 being committed first (F1-PF2) — do not start otherwise.**

- [ ] **F1-T2a** — Confirm the subscription actually includes what is needed. Financials require Stocks
      Developer or above, **or** Stocks Starter plus the Financials and Ratios expansion. **If an endpoint
      returns an authorization error, stop and post. Do not work around it, do not substitute a different
      endpoint, do not scrape.**
- [ ] **F1-T2b** — Pull, for every Central Index Key in `ticker_identity`, across the full available history
      (records begin 2009-03-29): **income statements, balance sheets, cash flow statements, ratios, ticker
      details, ticker events, splits, dividends, short interest, short volume.** Pull by Central Index Key,
      not by ticker.
- [ ] **F1-T2c** — Pull the float endpoint too, once, and store it in the raw archive **only**. It is banned
      from the event layer by D27. Its presence in the archive is so that D27 can be audited later, not so
      that it can be used.
- [ ] **F1-T2d** — Write a fetch manifest per source: endpoint, parameters, request timestamp, record count,
      file checksum. Archive raw responses unmodified.
- [ ] **F1-T2e** — Document the schema of every archived source in `docs/data/fundamentals_sources.md`,
      version-controlled.
- [ ] **F1-T2f** — Commit. **The network step is now closed.**

> **Note on short interest and short volume.** These are not fundamentals and were not in the original
> request. They are in the pull because they are rented like everything else, they are event-dated, and they
> bear directly on a long-only bull-to-bear-flip thesis. Archiving them costs one endpoint each. Not
> archiving them costs a second subscription window later.

### F1-T3 — Filing index and event proximity

Free, permanent, and a prerequisite for D28 — the acceptance timestamp exists nowhere else. **Also gated
on D14 Amendment A1 (F1-PF2).**

- [ ] **F1-T3a** — Download the EDGAR daily index for 2020-01-01 through the universe end date. Declare a
      descriptive User-Agent with a contact address, as the SEC requires, and respect the published request
      rate. Prefer the bulk archives over per-company calls wherever both exist.
- [ ] **F1-T3b** — Build `sec_filings`: `cik`, `accession`, `form_type`, `accepted_ns`, `period_of_report`,
      `filing_date`. `accepted_ns` is the load-bearing column.
- [ ] **F1-T3c** — Build `event_filing_proximity`, one row per event: the nearest filing with
      `accepted_ns < t0_ns`, its form type, its accession, and the elapsed time. Plus counts of filings in the
      preceding 24 hours and 72 hours.
- [ ] **F1-T3d** — Build `event_filings_window`, one row per `(event_id, accession)` for every filing within
      **−30 days to +5 days** of `t0`. This is the long companion table; nothing is lost to the as-of
      collapse in F1-T3c.
- [ ] **F1-T3e** — Derive `flg_dilution_form_before_t0`: true when the nearest prior filing, or any filing in
      the preceding 72 hours, is in the **declared dilution form set**. Write the set out explicitly in
      `docs/data/fundamentals_sources.md` — at minimum the 424B prospectus-supplement family, S-1, S-3, and
      their effectiveness amendments, and 8-K filings reporting unregistered sales of equity securities. **The
      set is a documented decision, not an inline literal buried in code.**
- [ ] **F1-T3f** — **Report a number this programme specifically needs:** the count of events where a filing
      is accepted **between the instantaneous threshold crossing and the 60-second poll boundary.** D7 makes
      detection a family indexed by polling interval, so a filing landing inside that window means filing
      proximity is also a family, not a scalar. **Per D33, this is answerable only for the `nanosecond_poll1`
      tier of `t0_spine.parquet` (114 events)** — the other two tiers do not carry instantaneous-crossing
      precision, and this task reports that limitation explicitly rather than extrapolating from a coarser
      tier. If the count on that tier is zero, that is a sentence in the digest and the question is closed for
      that tier. If it is not zero, **stop and post** — it needs a decision, not a default.
- [ ] **F1-T3g** — Chart: distribution of time-since-nearest-filing, and the form-type mix of the nearest
      prior filing. Commit.

### F1-T4 — Float tier 1: shares outstanding

**Do not start until Cooper sets the `filed_stale` lag threshold (§4, suggested placeholder 45 days) and
the `shs_quality` coverage floor (escalation row 5, suggested placeholder 70%). Both must be recorded in
`docs/data/fundamentals_sources.md` before this task runs, not adopted silently from the placeholders.**

- [ ] **F1-T4a** — Download the SEC `companyfacts.zip` bulk archive. **Check its size before downloading** —
      it is multi-gigabyte and growing, and the disk budget should be confirmed rather than discovered.
- [ ] **F1-T4b** — Extract `dei:EntityCommonStockSharesOutstanding` for every Central Index Key in the
      universe. This is the **cover-page share count** — total shares issued as stated on the filing's cover,
      not float.
- [ ] **F1-T4c** — Build `shares_outstanding_observations`: `cik`, `shares`, `asof_ns` (the cover date the
      figure is stated as of), `accepted_ns`, `source_form`, `accession`. One row per observation. Keep every
      observation, including superseded ones.
- [ ] **F1-T4d** — Cross-check against the vendor's own share-count fields where both exist. **Report the
      disagreement distribution.** Do not reconcile them, do not pick a winner — report it. A systematic
      disagreement is a finding about the sources and belongs in the digest.
- [ ] **F1-T4e** — Commit.

### F1-T5 — Assemble `event_fundamentals`

- [ ] **F1-T5a** — Build the table to the schema in §4, using an as-of join (DuckDB's `ASOF JOIN`, natively
      supported — DuckDB 1.4.4 confirmed installed) on `accepted_ns < t0_ns`, strictly less than, per group.
      `t0_ns`/`t0_source` come from `t0_spine.parquet` (F1-PF5) — not re-derived here.
- [ ] **F1-T5b** — Compute `*_lag_ns` for every group as `t0_ns − asof_ns`. Carry it as a column. **A share
      count 40 days stale is a different measurement from one 2 days stale**, and pooling them without the lag
      visible repeats the events-do-not-share-a-clock error one layer up.
- [ ] **F1-T5c** — Set quality flags per §4. **No imputation, no forward-fill beyond the declared as-of rule,
      no dropping.**
- [ ] **F1-T5d** — Run the Verification Block in §5, in the structured drift-dict + exit-code + `--json`
      style of `tools/verify_cited_paths.py`. **Every assertion must pass before the table is committed.**
- [ ] **F1-T5e** — Commit.

### F1-T6 — Coverage report. Gate. Stop and post.

- [ ] **F1-T6a** — Report coverage of every group, cross-cut by **year, detection-price decile, delisted
      status, and exchange**.
- [ ] **F1-T6b** — Chart the coverage surface. Per the chart contract, the distribution comes before any
      aggregate — no coverage percentage is reported without the distribution behind it.
- [ ] **F1-T6c** — **State plainly whether coverage is missing at random.** The expected failure is that it
      is not: late filers, foreign private issuers on annual schedules, shells with thin structured data, and
      companies that delisted and stopped filing are concentrated in the cheapest, thinnest corner of this
      universe — which is where a large share of these events live. **Conditioning analysis on the covered
      subset would be a survivorship filter wearing a data-quality costume**, and a fresh instance of the
      population-level error the q05 line already cost a phase to establish.
- [ ] **F1-T6d** — **Stop. Tag. Post.** Tiers 2 and 3 are scoped after this report, not before.

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

### Group `fin_` — financial statement vintage (source: per F1-T0 outcome)

| column | type | notes |
|---|---|---|
| `fin_accession` | str, nullable | the single filing this whole group came from |
| `fin_accepted_ns` | int64, nullable | **strictly less than `t0_ns`** |
| `fin_period_end` | date, nullable | |
| `fin_fiscal_year` | int16, nullable | |
| `fin_fiscal_quarter` | int8, nullable | |
| `fin_timeframe` | enum, nullable | `quarterly` / `annual` / `trailing_twelve_months` |
| `fin_lag_ns` | int64, nullable | `t0_ns − fin_period_end` |
| `fin_quality` | enum | `as_filed` / `restated_unknown_vintage` / `unavailable` |
| `fin_revenue` | float64, nullable | |
| `fin_net_income` | float64, nullable | |
| `fin_cash_and_equivalents` | float64, nullable | |
| `fin_total_assets` | float64, nullable | |
| `fin_total_liabilities` | float64, nullable | |
| `fin_stockholders_equity` | float64, nullable | |
| `fin_operating_cash_flow` | float64, nullable | |
| `fin_shares_basic` | float64, nullable | |
| `fin_shares_diluted` | float64, nullable | |

**`restated_unknown_vintage` is the flag that carries the F1-T0 outcome into every row.** If the test shows
the vendor serves only latest-restated values, every row gets that flag and the contamination stays visible
at the point of use rather than living in a document nobody opens.

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
      sum to exactly 20,951, and the `nanosecond_poll1` tier count is exactly 114.
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

| # | condition | measurable as | action |
|---|---|---|---|
| 1 | F1-T0 shows one record per period carrying latest values | record count per `(cik, period)` in the unfiltered response | **Stop.** Vendor financials are not point-in-time. The work order needs an amendment before F1-T2. |
| 2 | `identity_quality` is not `resolved_exact` for **> 5%** of in-scope events | share of rows, from F1-T1d | **Stop and post.** The join spine is the foundation; a weak one contaminates every group above it. |
| 3 | Any `*_accepted_ns >= t0_ns` in a committed table | assertion in §5 | **Hard stop.** This is a bug in the as-of join, not a data-quality state. |
| 4 | An endpoint returns an authorization or entitlement error | HTTP status | **Stop and post.** Do not substitute an endpoint, do not scrape, do not proceed with partial coverage silently. |
| 5 | `shs_quality != 'unavailable'` for **< 70%** of in-scope events | coverage share, from F1-T6a | **Stop and post before any tier 2 or 3 work is scoped.** Threshold is a placeholder — **Cooper sets it before F1-T4 runs**, not after seeing the number. |
| 6 | Any filing accepted between the instantaneous crossing and the 60-second poll boundary | count, from F1-T3f (nanosecond tier only) | **Stop and post.** Filing proximity becomes a family indexed by polling interval, which is a decision, not a default. |
| 7 | `companyfacts.zip` exceeds the available disk budget | file size checked before download | **Stop and post.** Do not partially extract and proceed. |

Row 5 and row 2 do not conflict: row 2 gates on identity resolution and fires earlier; row 5 gates on share
count coverage and can only be evaluated after F1-T4.

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
