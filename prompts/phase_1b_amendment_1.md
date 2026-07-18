# Phase 1b — Amendment 1: T1 Escalation Resolution

**Date:** 2026-07-17
**Resolves:** T1 hard stop (unresolved suspect-class tickers 174/3,377 = 5.15% > 2%), commit 230b913.
**Decision (Cooper):** Replace the heuristic-plus-advisory classification with an authoritative pull from the Massive reference API. The heuristic is retained as a validation layer, not the verdict. Full universe (all 3,377 distinct tickers), not just the 174 suspects.

Commit this file to `prompts/` before resuming. Then execute T1-R below, re-run the T1 gate, and continue the original prompt from T2 unchanged except where noted.

---

**Context additions:**
- API key via environment variable only. Never committed, never logged, never echoed into any artifact or report.
- The API is queried in this task only. After T1-R, `results/phase_1b/artifacts/ticker_reference_snapshot.parquet` is the classification source of record — no other task or phase re-queries the API. If a future phase needs classification, it reads the artifact.
- `symbol-properties-database.csv` is dropped from the classification flow entirely. It stays quarantined. Record its removal in the Decisions Log.

---

## Tasks

- [ ] **T1-R1 — Bulk reference snapshot**
  Pull the vendor's reference tickers listing for US equities, paginated to completion, **both active and inactive/delisted** tickers. Persist the raw responses (all fields, unmodified) to `results/phase_1b/artifacts/ticker_reference_snapshot.parquet`, with a `snapshot_utc` column.
  - [ ] T1-R1a — Join against the 3,377 distinct universe tickers. Report matched / unmatched counts with n.
  - [ ] T1-R1b — Commit (before any per-ticker calls)

- [ ] **T1-R2 — Residual per-ticker lookups**
  For every universe ticker unmatched in T1-R1: per-ticker reference lookup **as of that ticker's earliest event date** in `momentum_events_canonical`-to-be (use `COALESCE(date, event_date)`). Append results to the snapshot artifact with `lookup_method = 'per_ticker_dated'`.
  - [ ] T1-R2a — Anything still unmatched after both passes: class = `unresolved`, listed in full in the report. These default **out of scope** (Cooper decision — do not attempt further resolution).
  - [ ] T1-R2b — Commit

- [ ] **T1-R3 — Rebuild the classification table**
  Rebuild `instrument_classification.parquet` with vendor `type` as the verdict:

  | Vendor type | Class | In scope (D4) |
  |---|---|---|
  | CS (incl. class shares) | common | yes |
  | ADRC | common_adr | yes |
  | PFD | preferred | no |
  | WARRANT | warrant | no |
  | UNIT | unit | no |
  | RIGHT | right | no |
  | ETF / ETN / ETV / FUND / index-linked | fund_product | no |
  | any other vendor type | other — enumerate each distinct value in the report | no |
  | unmatched after T1-R2 | unresolved | no |

  Retain columns: `ticker, vendor_type, class, in_scope_class, heuristic_class (original T1 rule output), heuristic_agrees, lookup_method, as_of_date`.
  - [ ] T1-R3a — **Heuristic validation table:** heuristic class × vendor class confusion matrix, with n per cell. Every disagreement cell enumerated in the report (ticker-level list if ≤ 50 rows, artifact reference if more).
  - [ ] T1-R3b — **Ticker-reuse check:** tickers whose vendor record's active window does not cover all of that ticker's event dates. Count and list. If > 25, escalate; otherwise record per-ticker in the artifact and continue.
  - [ ] T1-R3c — Regenerate the T1a classification counts table (class × source) from the rebuilt table.
  - [ ] T1-R3d — Commit

- [ ] **T1-R4 — Re-check the T1 gate**
  Escalation criterion restated: `unresolved` class > 2% of distinct tickers → hard stop. (Expected: near zero. If it trips now, the vendor doesn't recognize a material slice of its own universe — stop and post.)
  - [ ] T1-R4a — Commit; resume original prompt at T2

---

## Changes to the original prompt (downstream of T1)

1. **T2 spine:** `instrument_class` comes from the rebuilt table. Add `vendor_type` as a passthrough column on the view.
2. **T4 re-ingestion scope:** in-scope recovered folders = vendor class `common`/`common_adr`. Expected count may shift slightly from the ~10 estimate; report the final list before ingesting. If it exceeds 25 folders, post the list and pause for confirmation before the ingestion run (a larger-than-expected count means the heuristic misread the recovered set, which is worth eyes before writes).
3. **T5/T6/T7 populations:** all references to `('common','common_class_share')` become `('common','common_adr')`.
4. **T6 waterfall:** add one step — minus `fund_product` — between the non-common-instruments step and bad-denominator. ETF/ETN removal is a distinct, visible loss, not folded into "non-common."
5. **Chart 02:** add `fund_product` and `unresolved` as classes; suspect classes no longer exist post-rebuild.
6. **T8 CLAUDE.md block**, replace the instrument-scope bullet with:
   > - Instrument scope: common stock only (all share classes, ADRs), per vendor reference type CS/ADRC. Preferreds, warrants, rights, units, ETFs/ETNs/funds, and unresolved tickers are out of scope. Classification source of record: `results/phase_1b/artifacts/ticker_reference_snapshot.parquet` — never re-query the API for classification.

---

## Escalation Criteria (amendment scope)

| Condition | Threshold | Action |
|---|---|---|
| Universe tickers unmatched after both passes | > 2% of 3,377 | Hard stop — post list, await instruction |
| Ticker-reuse conflicts (T1-R3b) | > 25 tickers | Hard stop — post list, await instruction |
| Heuristic-vs-vendor disagreement outside suspect classes | > 5% of matched tickers | Hard stop — post confusion matrix, await instruction |
| In-scope recovered-folder count (T4, revised) | > 25 folders | Soft stop — post list, await confirmation before ingesting |
| API key absent / auth failure | any | Hard stop — no retry loops, no key handling improvisation |

---

## Output Files (additions)

| File | Description | Status |
|---|---|---|
| `results/phase_1b/artifacts/ticker_reference_snapshot.parquet` | Raw vendor reference records, both passes, with snapshot timestamp and lookup method | [ ] |
| `results/phase_1b/artifacts/instrument_classification.parquet` (rebuilt) | Vendor-verdict classification with heuristic validation columns | [ ] |

Digest addition: `decisions_log` entry for the advisory-source swap; `headline_metrics` entries for matched %, unresolved n, fund_product n, heuristic disagreement rate — each with n and chart/table reference per the Evidence Standard.

---

## Approval Gate

Unchanged. The original Phase 1b gate stands; this amendment does not add an intermediate approval unless an escalation above fires.
