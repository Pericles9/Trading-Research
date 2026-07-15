---
tags:
  - type/data-schema
  - domain/data
  - project/src-core
  - status/complete
created: 2026-07-11
---

# Quotes Migration Fix — T2 Actual `filtered/*/quotes.parquet` Schema

Enumerated directly via `DESCRIBE SELECT * FROM read_parquet(...)` against a real,
correctly-populated file (`data/filtered/AACG_2020-06-11_50.02/quotes.parquet`),
not assumed from the trades schema or any doc.

| # | Column | Type |
|---|---|---|
| 1 | `ask_exchange` | BIGINT |
| 2 | `ask_price` | DOUBLE |
| 3 | `ask_size` | BIGINT |
| 4 | `bid_exchange` | BIGINT |
| 5 | `bid_price` | DOUBLE |
| 6 | `bid_size` | BIGINT |
| 7 | `conditions` | BIGINT[] |
| 8 | `participant_timestamp` | BIGINT |
| 9 | `sequence_number` | BIGINT |
| 10 | `sip_timestamp` | BIGINT |
| 11 | `tape` | BIGINT |
| 12 | `indicators` | BIGINT[] |

12 columns, confirmed. See `column_usage_scope.csv` for per-column downstream
usage (T3) and `timestamp_mapping_verification.md` for which of these
`quote_data/` can actually supply (T1).
