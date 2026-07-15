---
tags:
  - type/results
  - domain/data
  - project/vault
  - status/needs-review
created: 2026-07-11
---

# `data/minute/trades/` Investigation

Read-only. No files moved, deleted, or modified. This follows up on the Data
Layer Inventory's finding that `data/minute/trades/` holds 90.1 GB inside the
minute-bar candle location but isn't candle data.

## T1 — What it actually is

Not a ticker. `data/minute/trades/` is a real directory (not disguised as one
ticker) that sits alongside genuine per-ticker folders directly under
`data/minute/`. Inside it: 2,913 ticker subdirectories, each holding
`{date}.parquet` files — same nesting depth as real minute-bar tickers, which
is exactly what makes it indistinguishable from a ticker by directory listing
alone (`ls data/minute/` shows `trades` as just another entry).

- **18,630 files, 90.12 GB, 2,913 tickers, 1,257 distinct dates**
- **Date range: 2020-01-03 → 2024-12-31** — entirely before the 2025 gap this
  project just filled; unrelated to that effort.
- **Ticker universe is broad, not meme-stock-specific.** A prior pass
  characterized this as meme-stock tick dumps (AMC/GME/CLOV-type names); a
  random sample instead shows the same kind of tickers used throughout this
  project's momentum-event corpus (CHEK, SILO, ATHpB, GAIA, CAL, POET, PACB,
  etc., including preferred-share `p`-suffix tickers). The earlier
  characterization likely came from spot-checking the largest files, which
  skew toward genuine high-volume 2021 squeeze days — not representative of
  the corpus as a whole.
- **Schema (per-file, verified directly, not merged across files with
  drift):** 20 columns, and unusually, it doubles up short-form Polygon
  fields and expanded/renamed equivalents in the same file — `t`/`timestamp`,
  `p`/`price`, `s`/`size`, `x`/`exchange`, `c`/`conditions`, `i`/`trade_id`,
  plus both `participant_ts` and `participant_timestamp_ms`, both
  `timestamp` and `timestamp_ms`. This is raw trade-tick data (Polygon-style),
  not OHLCV — no open/high/low/close/volume columns anywhere.

## T2 — Comparison against `filtered/`

**93% of it duplicates `filtered/`; 7% is genuinely unique.**

- `filtered/` has 23,306 `(ticker, date)` pairs (excluding `_None_` entries).
- `data/minute/trades/` has 18,630 `(ticker, date)` pairs.
- **Overlap: 17,327 pairs (93.0%) already exist in `filtered/`.**
- **Unique to `minute/trades/`: 1,303 pairs (7.0%) — not in `filtered/` at all.**

Content check, not just name-matching: for a sample event (CHEK 2020-01-09,
1,761 rows), `filtered/`'s corresponding directory (`CHEK_2020-01-09_30.22`)
turned out to hold a **7-9 day window**, not a single day — the original
collector (`collect_massive_data.py`, pre-v2) pulls a multi-day window per
event, not just the named date; only the newer v2 collector used in the final
gap-fill pulls a single target date. Restricting `filtered/`'s data to the
exact calendar window `minute/trades/` covers yields **exactly 1,761 rows** —
matching the file's row count precisely. A fuzzy join (price + size exact,
timestamp within 1ms) matched **3,142 pairs** with **zero exact-timestamp
matches** — the timestamps differ by a few hundred microseconds to under 1ms,
consistent with two different clock references on the same trade (e.g.
participant-feed vs. SIP timestamp for the same execution), not coincidental
similarity or random noise. This is the same trade data, re-derived or
re-collected through a different pipeline stage — **duplicate content, not
byte-identical files.**

Sizes, not just counts:
- **Overlapping (duplicate) portion: 17,327 files, 88.45 GB**
- **Unique-only portion: 1,303 files, 1.67 GB**

The unique-only 1,303 pairs span **198 distinct tickers** and are spread
across all five years (2020: 172, 2021: 70, 2022: 433, 2023: 416, 2024: 212)
— not concentrated in one date range or a handful of tickers that might
suggest a narrow edge case. This is a real, broad-based gap in `filtered/`'s
coverage, the same shape of finding as the earlier `high_momentum` 2025 gap.

## T3 — Origin

- **mtime clustering:** all 18,630 files were written between
  **2025-11-22 00:05 and 2025-11-23 01:28** — a ~25-hour window, essentially
  one bulk operation. This overlaps the same late-November 2025 window found
  clustering across the rest of the candle corpus (Nov 21–27) and close to
  the `BULK_REWRITE_DATE = 2025-11-24` constant found in this project's own
  `audit_full_sweep.py` (used to correlate corrupted-file mtimes in the
  trades corpus). Consistent with one large copy/migration event touching
  multiple parts of this data tree at once — not evidence of what produced
  the content originally, just when it was last written to this location.
- **Code reference — more specific than a passing mention.** `src/data/ingest.py`'s
  `load_minute()` (lines 183-234) has a **deliberate, explicit fallback code
  path** for this exact layout:
  ```python
  # minute/{TICKER_OR_SUBFOLDER}/{YYYY-MM-DD}.parquet  OR
  # minute/trades/{TICKER}/{YYYY-MM-DD}.parquet
  # Handle both layouts
  ...
  else:
      # Nested: minute/trades/{TICKER}/{date}.parquet
      for sub_sub in sorted(ticker_dir.iterdir()):
          ...
  ```
  When `ticker_dir` is `data/minute/trades/` itself, `_safe_glob(ticker_dir, "*.parquet")`
  finds nothing directly inside it (files are one level deeper, under each
  ticker), so the loader falls into the "nested" branch and walks
  `minute/trades/{TICKER}/{date}.parquet` as if each were a normal
  minute-bar ticker file — `SELECT *, ticker, session_date FROM
  read_parquet(...)`, destined for the same `minute_bars` table as genuine
  OHLCV data. Someone wrote this fallback deliberately, aware this directory
  exists — this isn't an accidental glob catching stray files.
  **Practical consequence if `--all` ingestion is ever run:** because
  directory iteration is alphabetically sorted, real ticker directories
  (numbers, A–S) create `minute_bars` with a genuine OHLCV schema before the
  loop reaches `trades/`. Every one of the 18,630 trades files then hits
  `INSERT INTO "minute_bars"` with a completely different (raw trade-tick)
  column set, which will raise a schema-mismatch exception, caught per-file
  by the existing `except Exception: log.error(...)` — meaning a real
  ingestion run would silently swallow 18,630 errors rather than crash, but
  would also burn significant time reading and attempting to insert 90 GB of
  data that can never succeed. Not found in the prior inventory pass; this is
  a materially more specific problem than "one loader references
  `high_momentum`."

## T4 — Classification

**Something else entirely — not a clean "duplicate, safe to delete" and not a
clean "unique, needs filing." It's both, split cleanly by content:**

1. **17,327 of 18,630 files (88.45 GB, 93%) — duplicate.** Same trades
   already present in `filtered/`, confirmed by content (row counts match
   exactly when scoped to the same calendar window; price+size+near-identical
   timestamp matches at high rate), not just by ticker/date label matching.
2. **1,303 of 18,630 files (1.67 GB, 7%) — unique.** Not present anywhere
   else in the canonical corpus. 198 tickers, spread across 2020–2024.
   **This is the escalation-triggering finding** — a meaningful fraction of
   unique data that would be permanently lost if this directory were deleted
   wholesale on the "it's just duplicate trade ticks" assumption.
3. **Separately: an active code hazard**, independent of the duplicate/unique
   split — `load_minute()` will attempt (and fail, noisily) to ingest all
   18,630 of these files as minute bars if DuckDB ingestion is ever run.

No remediation performed. The three findings above are independent — the
duplicate/unique split answers "is this safe to delete," the code hazard
answers "does something depend on this path staying as-is" (answer: only in
the sense that it needs the fallback code path *removed or fixed*, not
preserved, since the fallback never produces useful output).

## Escalation check

| Condition | Result |
|---|---|
| Data appears unique, any meaningful fraction | **Yes — 1,303 pairs / 1.67 GB (7%), reported prominently above, not buried** |
| Unhandled exception during investigation | None |
