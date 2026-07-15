---
tags:
  - type/results
  - domain/data
  - project/vault
  - status/needs-review
created: 2026-07-12
---

# Hardware Investigation — T5: Data Safety Assessment

## Bottom line

**A verified-trustworthy copy exists for the large majority of the data,
but it is not 100% complete, and D: should not be relied on as "the safe
copy" going forward — it is actively, currently erroring, not settled.**

## D: is live right now, not a historical/settled issue

Re-checked the event log at the end of this investigation: **D: threw 5
more bad-block events at 1:54:59 PM**, 30 seconds before a routine check —
under light diagnostic load, not the earlier heavy write/copy work. Total
for D: (`Harddisk1\DR1`) is now **909 events** (up from 887 an hour into
this report), spanning July 11 5:39 PM to *right now*. E: (`Harddisk0\DR0`)
remains unchanged at 174, all from a single July 9 burst, nothing since.
**D:'s problem is ongoing, not resolved by reducing I/O.**

## Genuinely unrecoverable data: unchanged at 4 files, not 9

Direct, repeated, current-moment content reads (`read_parquet` via DuckDB,
not just file-existence or byte-size checks) confirm:

| File | Status |
|---|---|
| `CING_quotes_2024_08_16.parquet` | Unreadable ("too small to be a Parquet file") — unchanged since original discovery |
| `CLRO_quotes_2023_05_09.parquet` | Unreadable (same) — unchanged |
| `POLA_quotes_2020_11_23.parquet` | Unreadable (I/O error, consistent across every check this session) |
| `RR_quotes_2024_09_23.parquet` | Unreadable (same) |

These 4 are the same ones identified hours ago, before today's hardware
investigation began — **no new permanent data loss found**, despite the
scare earlier in this session.

## What actually happened with the "9 corrupted files" scare

7 files (`PLRZ_quotes_2025_07_23`, `PMAX_quotes_2025_02_28`,
`POLA_quotes_2020_08_26`, `POLA_quotes_2021_10_28`, `RLYB_quotes_2024_04_11`,
`RNA_quotes_2022_12_14`, `RRGB_quotes_2020_03_19`) are **currently fine on
D:** — read successfully just now, correct sizes, correct row counts. What
went wrong: my earlier individual-file copy retry to E: ran *during* D:'s
active-error window and silently wrote 1-byte garbage to E: for these 7
files while reporting "COPIED OK" — a copy operation that appeared to
succeed while actually producing corrupt output, because it was reading
from a drive that was, at that exact moment, failing reads without always
raising a clean exception. **This is the real risk D:'s current state
poses**: not just "some reads will visibly fail," but "some reads may
silently return wrong data during an active-error window."

## E: copy status, verified by content read (not just size)

| Directory | Verified how | Result |
|---|---|---|
| `filtered/` | Full byte-count match (47,615/47,615 files, 183.106GB exact) earlier + 286-file random content spot-check just now | **Fully trustworthy** |
| `quote_data/` | 19,127/19,136 files byte-verified earlier + 150-file random content spot-check just now, all passing | **19,127/19,136 (99.95%) trustworthy** |
| `quote_data/` — 9 specific files | Confirmed broken 1-byte stubs on E: right now | **2 unrecoverable anywhere (same as the 4 above minus overlap — POLA_2020-11-23, RR_2024-09-23), 7 recoverable via a clean re-copy from D: while it's currently readable** |

## No third location exists

| Location | Free space | Viable? |
|---|---|---|
| C: | 8.7GB | No — far short of the ~210GB dataset |
| D: | 102.3GB (but this *is* the drive in question) | N/A |
| E: | 720.4GB | Already the backup target |
| External/network | None detected | N/A |

**There is no independent third copy anywhere.** The E: copy, once the 7
recoverable files are re-copied, would be the only complete, verified-good
copy outside of D: itself.

## What I have not done

No re-copy of the 7 recoverable files, no deletion of anything on D:, no
junction points, no ingestion. Per the approval gate, all of that waits for
your explicit review of this report — including the small, targeted re-copy
of the 7 files, even though it's low-risk (~15MB total) and D: currently
reads them fine.

## Recommendation for your consideration (not acted on)

1. The 7 recoverable files are small and D: currently reads them correctly
   — but given D: just produced a live error 30 seconds before a routine
   check, I'd want your go-ahead specifically before touching it again,
   however briefly.
2. The 2 permanently-lost-there files (`POLA_quotes_2020_11_23`,
   `RR_quotes_2024_09_23`) plus `CING`/`CLRO` remain a pre-existing,
   already-known gap — unaffected by today's hardware findings, not
   newly urgent.
3. Given D:'s active, ongoing errors, I'd treat any further D: read as
   carrying some (currently unquantified, since T4's SMART data was
   blocked) risk of a silent bad read — worth keeping in mind for the
   ingestion re-run once that's back on the table.
