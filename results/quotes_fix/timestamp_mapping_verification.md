---
tags:
  - type/results
  - domain/data
  - project/src-core
  - status/complete
created: 2026-07-11
---

# Quotes Migration Fix — T1 Timestamp Mapping Verification

## Result: CONFIRMED, exactly, via direct row comparison

Method: found 13,174 `(ticker, date)` events where `filtered/` already has a
correctly-populated `quotes.parquet` (not one of the 5,871 broken or 1,469 gap
events) **and** `quote_data/` has the matching raw file. Verified 3 events
(`AACG` 2020-06-11, 2020-06-16, 2020-08-03) by joining both sources on the 4
unambiguous shared numeric fields (`bid_price`, `ask_price`, `bid_size`,
`ask_size`) plus a coarse timestamp proximity filter, then comparing the two
candidate timestamp columns exactly (not approximately).

| Event | quote_data rows | Exact `timestamp = sip_timestamp` matches | Exact `exchange = participant_timestamp` matches |
|---|---|---|---|
| AACG 2020-06-11 | 790 | 790 / 790 (100%) | 792 / 790 (a few extra from duplicate-price join noise) |
| AACG 2020-06-16 | 2,246 | 2,246 / 2,246 (100%) | 2,252 / 2,246 |
| AACG 2020-08-03 | 770 | 770 / 770 (100%) | 774 / 770 |

Every row in `quote_data/` has an exact match in `filtered/`'s
`sip_timestamp` and `participant_timestamp` columns (the handful of "extra"
participant matches are join artifacts from duplicate bid/ask/size
combinations producing more candidate row-pairs than source rows — not
evidence against the mapping).

**Confirmed:**
- `quote_data.timestamp` **is** `sip_timestamp`.
- `quote_data.exchange` **is** `participant_timestamp` — the column name in
  `quote_data/` is a mislabel, not a different field.

## Important caveat found during verification: `quote_data/` is a subset, not a duplicate

Row counts do not match between the two sources for the same event:

| Event | `filtered/quotes.parquet` rows | `quote_data/` rows | Coverage |
|---|---|---|---|
| AACG 2020-06-11 | 4,812 | 790 | 16.4% |
| AACG 2020-06-16 | 5,488 | 2,246 | 40.9% |
| AACG 2020-08-03 | 1,858 | 770 | 41.4% |

`quote_data/` contains only 16–41% of the quote ticks that `filtered/`'s
canonical, correctly-populated files have for the same event. This means
recovering the 5,813 matched broken events from `quote_data/` would **not**
restore full row-level completeness — it would populate `quotes.parquet` with
a partial (16–41%-scale, in this sample) subset of the true quote stream, not
the full tick sequence. This is a fact for the pending decision, not something
resolved here.
