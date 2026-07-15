---
tags:
  - type/results
  - domain/data
  - project/src-core
  - status/complete
created: 2026-07-11
---

# Quotes Migration Fix — Row-Count Gap Root Cause Investigation

## Root cause: structural and legitimate — not a collection bug, not an inflated reference

`quote_data/` is a complete, correctly-scoped single-session (4:00 AM–8:00 PM ET)
quote capture for each event date. `filtered/`'s canonical `quotes.parquet`
files additionally carry several days of surrounding historical context per
event. Comparing raw row counts across the two mismatched scopes produced the
earlier "16–41% coverage" reading; once both are restricted to the same
session window, coverage is effectively complete.

## T1 — Coverage ratio distribution (broad sample, n=600)

Raw (unscoped) coverage ratio — `quote_data` rows ÷ `filtered` rows, full file:

| Percentile | Value |
|---|---|
| min | 1.3% |
| p10 | 15.8% |
| p25 | 22.1% |
| median | 33.0% |
| p75 | 51.0% |
| p90 | 71.9% |
| max | 14,760% (one extreme outlier, see T1 outliers below) |

No correlation with event size (`corr(coverage_ratio, filtered_row_count) = -0.004`)
or year (`corr(coverage_ratio, year) = -0.027`) — ruling out "worse for big/small
events" or "getting worse/better over time" as explanations. Median coverage is
essentially flat across 2020–2024 (0.29–0.36 each year). This pointed toward a
structural cause rather than an intermittent collection failure.

Full per-event data: `coverage_ratio_distribution.csv`.

## T2 — Truncation signature: not pagination cutoff, but a session-window mismatch

Checked whether thin events show the classic pagination-cutoff signature (data
starts at session open, stops partway through — the shape of the historical
trades pagination-cap bug). **They don't.** Instead:

- `quote_data`'s time window consistently sits **in the middle** of `filtered`'s
  window: median start position 46.9% through, median end position 53.3%
  through (0% = filtered's earliest timestamp, 100% = latest). Only 2/600
  events show the classic "starts at 0%, ends before 30%" cutoff shape.
- `quote_data`'s absolute window duration is tightly clustered: p25/median/p75
  = 954.7 / 959.9 / 960.9 minutes — effectively a **fixed 960-minute (16-hour)
  window**, not a variable cutoff point.
- `filtered`'s window duration is far larger and looser: median 12,480 minutes
  (~8.7 days).
- 960 / 12,480 = 7.69%, matching the independently-measured median **span
  ratio of 7.66%** almost exactly — confirming the mismatch is a scope
  difference, not noise.

**The 960-minute window is not arbitrary.** [`hawkes-ofi-impact/data/loaders/trades.py:106-121`](hawkes-ofi-impact/data/loaders/trades.py#L106-L121)
defines `_session_ns_bounds()` as exactly **4:00 AM – 8:00 PM ET (16 hours)**
— the same session filter [`hawkes-ofi-impact/data/loaders/quotes.py`](hawkes-ofi-impact/data/loaders/quotes.py)
applies to `filtered/`'s data by default (`session_filter=True`) before any
signal computation happens. `quote_data/`'s window is that exact session, not
a truncated pull.

### Decisive check: coverage ratio when both sides are scoped to the same session

Re-ran T1's comparison restricting `filtered/`'s row count to the same
4am–8pm ET window `quote_data/` covers (n=595, 5 dropped for date-parse edge
cases):

| Percentile | Session-scoped coverage ratio |
|---|---|
| p10 | 1.00 |
| p25 | 1.00 |
| median | **1.00** |
| p75 | 1.00 |
| p90 | 1.02 |

**543/595 events (91.3%) land within ±10% of exact parity; 554/595 (93.1%)
within ±20%.** Within the window the production pipeline actually uses,
`quote_data/` and `filtered/` agree almost exactly.

### Outliers (not the dominant pattern — flagged individually, not resolved here)

- **AUR 2021-11-19**: `quote_data` has 41,075,031 rows in-session — all with
  distinct timestamps (not a duplicate-row artifact). This matches the
  corruption signature already documented in
  [`results/final_gap_fill/migration_report.md`](results/final_gap_fill/migration_report.md#L24-L29)
  ("AUR: 29.99M corrupted rows → 157,573 genuine" for trades) — very likely
  the same known upstream corruption class recurring in quotes, not a new
  issue. Should be excluded/filtered, same as the trades case.
- A small cluster of 2–3x mismatches falls on extreme-volatility dates
  (DDS/GCO/AIR/BANX/CAR all 2020-03-19, CBRL 2020-03-24, OPRX 2020-03-17 — the
  COVID crash week). Direction is `quote_data` having *more* in-session rows
  than `filtered`, the opposite of the general gap — plausibly `filtered`'s
  own collection under-captured this specific high-volume week. Not
  investigated further; noted for awareness.

## T3 — `quote_data/` provenance

- **mtime clustering**: all 19,136 files were written Jan 11–15, 2026 (17,140
  of them on Jan 11 alone) — one collection campaign, not an incremental or
  patched-together corpus.
- `filtered/`'s `quotes.parquet` files (sampled 2,000) were written Jan 19–20,
  2026 — a **separate, later** build, roughly a week after `quote_data/`.
  Consistent with `filtered/` being a subsequent, richer migration that added
  multi-day context on top of what `quote_data/` already had.
- No per-file row-count cap found (row counts range from 194 to 41M+ across
  the sample) — ruling out a fixed-row-count API page limit as the shaping
  factor. The shaping factor is the time window, not a row cap.
- No builder script for `data/quote_data/` remains in the repo (only
  consumers: `audit_quotes_sweep.py`, `src/data/ingest.py`,
  `src/data/prepare_database_split.py`) — provenance is established from file
  evidence (mtimes, exact session-bounds match), not from reading collection
  code.

## T4 — Is `filtered/`'s reference count itself inflated?

Checked `COUNT(DISTINCT sip_timestamp) / COUNT(*)` on all 600 sampled
`filtered/quotes.parquet` files (the OCGN-style check — could the "thin"
side actually be correct and the "reference" side be duplicate-bloated?).

**No** — median dedup ratio is exactly 1.0 (no duplicates), p10 is 0.982.
Only 18/600 events (3%) have more than 5% duplicate `sip_timestamp` rows, and
none of those overlap with the largest coverage-mismatch outliers above. The
reference count is trustworthy; this is not an OCGN-shaped finding.

## T5 — Conclusion

- **Not** a fixable-via-recollection pagination/truncation bug (T2 ruled this
  out directly — no early-cutoff signature, a fixed intentional window
  instead).
- **Not** a reference-count-inflation artifact (T4 ruled this out — dedup
  ratio ≈ 1.0 across the sample).
- **Is** a structural, legitimate scope difference: `quote_data/` is a
  complete single-session (4am–8pm ET) capture; `filtered/` additionally
  carries multi-day surrounding context that `quote_data/` was never meant to
  provide. Within the session window the production pipeline actually
  consumes, the two sources agree almost exactly (median ratio 1.00, 91%
  within ±10%).
- One known-corruption outlier (AUR 2021-11-19) and a small unexplained
  cluster around the 2020-03 COVID-crash week remain open, flagged but not
  resolved here.
