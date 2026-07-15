---
tags:
  - type/results
  - domain/data
  - project/src-core
  - status/complete
created: 2026-07-11
last_reviewed: 2026-07-11
---

# Quotes Migration Fix — T2 Schema Compatibility Check

## RESOLVED — subtractive 5-column fix approved (update, 2026-07-11)

The original hard stop below is preserved as-is for the record. It has since
been resolved by two follow-up investigations:

1. **Column usage scan** (`column_usage_scope.csv`) — grepped the actual
   production pipeline. Only 5 of the 12 `filtered/` quote columns are ever
   read by name anywhere in the codebase: `sip_timestamp`, `bid_price`,
   `ask_price`, `bid_size`, `ask_size` (both quote loaders,
   `hawkes-ofi-impact/data/loaders/quotes.py:51` and the scanner-epg-momentum
   equivalent). `participant_timestamp` — the field whose `quote_data/`
   mapping was the actual source of ambiguity below — is **not read by any
   downstream code**. The other unmapped columns (`ask_exchange`,
   `bid_exchange`, `conditions`, `sequence_number`, `tape`, `indicators`) are
   confirmed unused too.
2. **Direct row-level verification** (`timestamp_mapping_verification.md`) —
   joined `quote_data/` against known-correct `filtered/` files on the 4
   unambiguous shared fields. Every matched row showed `quote_data.timestamp
   == filtered.sip_timestamp` exactly (100%) and `quote_data.exchange ==
   filtered.participant_timestamp` exactly (100%). The mapping is confirmed
   by data, not inferred from timing patterns.

**Net effect:** the fix now uses a subtractive 5-column schema —
`sip_timestamp` (from `quote_data.timestamp`), `bid_price`, `ask_price`,
`bid_size`, `ask_size` — the exact set of columns downstream code reads, all
with confirmed (not assumed) 1:1 mapping. This matches the trades migration's
precedent exactly: write only the columns that are both unambiguous and
load-bearing, omit the rest, invent nothing. `participant_timestamp` is
dropped entirely rather than written from the still-inferential `exchange`
mapping, since nothing consumes it.

A separate, independent finding from the row-count-gap investigation
(`row_count_gap_investigation.md`) also applies here: `quote_data/` is a
single-session (4am–8pm ET) capture, while `filtered/`'s existing files
additionally carry multi-day context. Recovered files under this fix will
therefore be single-session only — documented explicitly in `fix_report.md`,
not a silent limitation.

**T3 (copy) is now approved to proceed** under this subtractive schema, for
matched, non-anomalous events only (see `flagged_anomalies.csv` for 12
events excluded pending separate investigation).

---

## Original result (2026-07-11, pre-resolution): HARD STOP — not a straight copy, not a clean subtractive fix

## What `filtered/*/quotes.parquet` (correct, existing) looks like

12 columns: `ask_exchange`, `ask_price`, `ask_size`, `bid_exchange`, `bid_price`,
`bid_size`, `conditions` (`BIGINT[]`), `participant_timestamp`, `sequence_number`,
`sip_timestamp`, `tape`, `indicators` (`BIGINT[]`).

`ask_exchange`/`bid_exchange` are small integer venue codes — sampled range 0–7,
8 distinct values in one reference file.

## What `data/quote_data/*.parquet` (the proposed recovery source) actually has

Only 6 columns: `timestamp`, `bid_price`, `bid_size`, `ask_price`, `ask_size`,
`exchange`.

**The `exchange` column is not an exchange code.** Sampled across 3 files
(`USAR`, `BULL`, `HTCO`), its values are 19-digit numbers in the same range as
`timestamp`, and `timestamp - exchange` is consistently 10,000–340,000 (i.e.
10–340 microseconds) — this is a second nanosecond-scale timestamp, not a
venue ID. It's almost certainly `participant_timestamp` (exchange-origination
time) sitting next to `timestamp` as `sip_timestamp` (SIP-receipt time), given
the realistic microsecond-scale gap between the two — but that reading is an
inference, not something the data confirms on its own. **The column name in
`quote_data/` is either mislabeled or the two are genuinely different things;
I did not resolve which, since resolving it means guessing.**

Real per-quote exchange-venue codes (matching `ask_exchange`/`bid_exchange`)
are **not present anywhere in `quote_data/`** under any column — they are a
true gap, not a naming issue.

## Column-by-column disposition

| `filtered/` column | `quote_data/` equivalent | Status |
|---|---|---|
| `bid_price` | `bid_price` | Direct match, safe |
| `bid_size` | `bid_size` | Direct match, safe |
| `ask_price` | `ask_price` | Direct match, safe |
| `ask_size` | `ask_size` | Direct match, safe |
| `sip_timestamp` | `timestamp` (probably) | Plausible but unconfirmed — no shared ID or cross-check available between the two sources to verify this is truly SIP time and not something else |
| `participant_timestamp` | `exchange` (probably, mislabeled) | Same caveat — inference, not verified |
| `ask_exchange` | — | **Not present in `quote_data/` at all** |
| `bid_exchange` | — | **Not present in `quote_data/` at all** |
| `conditions` | — | Not present |
| `sequence_number` | — | Not present |
| `tape` | — | Not present |
| `indicators` | — | Not present |

## Why this doesn't qualify as "subtractive, no invented columns"

The trades migration's subtractive precedent (`sip_timestamp`, `price`, `size`)
worked because all three were **unambiguous 1:1 name matches** — nothing was
inferred, only omitted. Here, 4 of 6 usable fields are unambiguous
(`bid_price`, `bid_size`, `ask_price`, `ask_size`), but the two timestamp
columns require assuming which real-world timestamp each mislabeled
`quote_data/` column represents. Writing `exchange` into a
`participant_timestamp` field, or `timestamp` into `sip_timestamp`, would be a
**derived/assumed mapping**, not a subtraction — exactly what this task's
escalation criteria rule out.

Per the escalation table: "Schema mismatch requiring more than a subtractive
fix → Hard stop — report, do not invent or derive columns." Stopping here.
**T3 (copy) has not been run. No files have been written or deleted.**
