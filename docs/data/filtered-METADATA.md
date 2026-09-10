<!-- COPY OF RECORD for `data/filtered/METADATA.md`, which is untracked because `.gitignore`
     excludes `/data/` wholly. Edit HERE; mirror to `data/filtered/METADATA.md` for anyone reading the
     data tree directly. Established 2026-09-10, D26 follow-up. -->

# Filtered Data Metadata

This folder contains subsets of market data organized by instrument and event date.

## Directory Structure
Each subdirectory represents a specific trading session/event for an instrument.
Format: `SYMBOL_DATE_METRIC/` (e.g., `AACG_2020-02-18_40.86/`)

## File Formats
Each subdirectory contains Parquet files compatible with Pandas and Nautilus Trader (with custom loading).

### trades.parquet
Contains executed trade data.
**Columns:**
- `participant_timestamp` (int64, nanoseconds): The primary time index.
- `sip_timestamp` (int64, nanoseconds): Secondary timestamp.
- `price` (float64): Trade price.
- `size` (int64): Trade volume.
- `exchange` (int64): Exchange ID.
- `conditions` (object): Trade conditions — a list of SIP condition codes per print.
  **Code 14 = `Intermarket Sweep`** (public trade-conditions glossary, recorded 2026-09-09;
  the rest of the code table is NOT established in this repo and any other code's meaning
  is [verify]). Code 14 is enriched **7-15x inside sub-millisecond print runs** on the
  scale-field cohort, which is what identified those runs as the single-venue legs of
  intermarket sweeps rather than as independent arrivals — see
  `claude/fragmentation_and_the_closure.md` and D26.
- `id`, `sequence_number`, `tape`, `trf_id`, `trf_timestamp`: Metadata fields.
  **`sequence_number` is load-bearing for fragmentation detection**: prints inside a
  sub-millisecond run are consecutive in it 93-99% of the time against a
  run-structure-preserving permutation null of 0.000.

### quotes.parquet
Contains Top-of-Book (L1) quote data.
**Columns:**
- `participant_timestamp` (int64, nanoseconds): Primary time index.
- `bid_price` (float64), `bid_size` (int64), `bid_exchange` (int64).
- `ask_price` (float64), `ask_size` (int64), `ask_exchange` (int64).
- `sip_timestamp`, `sequence_number`, `tape`, `conditions`, `indicators`.

## Accessing Data
To load this data in Python:
```python
import pandas as pd
import os

folder_path = "data/filtered/SYMBOL_DATE_METRIC"
trades = pd.read_parquet(os.path.join(folder_path, "trades.parquet"))
quotes = pd.read_parquet(os.path.join(folder_path, "quotes.parquet"))
```
