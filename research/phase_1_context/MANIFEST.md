---
tags:
  - type/pipeline
  - domain/data
  - project/src-core
  - status/complete
created: 2026-04-04
---

# AlphaMomentum Phase 1 – Context Engine MANIFEST

## Related

- [[Phase 1 — Scanner Context]] — phase summary doc
- [[build_log]] — build log for this phase (same directory)

## Project Overview
**Name:** AlphaMomentum_Phase1_Context  
**Objective:** Reconstruct the 9:30 AM "Top Gappers" scanner for every day in the momentum_events universe, applying a 30% hard gap filter and producing ranked leaderboards with volume metrics.

**Build Status: COMPLETE**

---

## Results Summary

| Metric | Value |
|---|---|
| Raw momentum events (deduped) | 26,423 across 1,466 dates |
| **Events after 30% gap-at-open filter** | **4,549 across 1,307 dates** |
| Unique tickers in scanner | 1,653 |
| Max daily gappers | 18 |
| Minute data coverage | 99.9% (4,544 / 4,549) |
| RVOL coverage | 2.2% (101 / 4,549) — daily data only covers Dec 2024+ |
| Survivorship: tickers missing ALL data | 1 (ETEC) |

---

## Data Pipeline

### Stage 1: Event Universe Extraction
- **Source:** `data/momentum_events/filtered_events_power_law_q05.parquet` (23,268 events)  
  Supplemented by `full_2020_2024_momentum_scan_20251122_000515.parquet` (18,660 events) and `momentum_scan_2025.parquet` (5,950 events).
- **Date coverage:** ~1,257 unique trading days (2020–2025).
- **Key columns:** `ticker`, `date`, `prev_close`, `open`, `high`, `close`, `momentum_pct`, `event_volume`.

### Stage 2: Gap Calculation
$$G_t = \frac{P_{O,t} - P_{C,t-1}}{P_{C,t-1}}$$
- $P_{O,t}$ = Open price on event date (from momentum_events `open` column).
- $P_{C,t-1}$ = Previous trading day's close (from momentum_events `prev_close` column).

### Stage 3: 30% Hard Filter
- All tickers where $G_t < 0.30$ (30%) are discarded.
- This is more restrictive than the momentum_events scan threshold (which uses `high` vs `prev_close`).

### Stage 4: Intraday Ranking (per date)
- **Gap_Rank:** Numerical rank by gap % among all 30%+ gappers for that date (1 = highest gap).
- **Volume_Intensity:** Rank by first-5-minute trading volume (from `data/minute/` if available).
- **RVOL:** Relative Volume = event_day_volume / 30-day_avg_volume (from `data/daily/` lookback).

### Stage 5: Output
- **File:** `research/phase_1_context/scanner_context.parquet`  
  Indexed by `(ticker, date)`.

---

## Assumptions & Alignment Notes

### Timestamp Alignment: `daily/` vs `filtered/`
- **Daily files** (`data/daily/{TICKER}_daily.parquet`) contain OHLCV bars with a `date` column (string format `YYYY-MM-DD`). The `timestamp` column is epoch-ms at market close.
- **Filtered folders** (`data/filtered/{TICKER}_{DATE}_{MOM}/trades.parquet`) contain raw tick-level trades with nanosecond SIP timestamps.
- **Alignment logic:** The daily `open` is treated as the 9:30 AM auction/opening price. For validation, we compare daily `open` against the first trade price in filtered trades. Discrepancies > 1% are logged.

### `prev_close` Provenance
- The `prev_close` column in momentum_events is pre-computed upstream and is taken at face value. It represents the previous trading day's closing price, already adjusted for the correct business-day calendar (skipping weekends/holidays).
- If a stock was halted or had no prior-day trade, `prev_close` may be NaN — these rows are dropped.

### Ranking Logic
- Gap_Rank uses **dense ranking** (ties get the same rank, next rank is +1).
- Volume_Intensity ranking: only computed for tickers with minute-bar data in `data/minute/{TICKER}/{DATE}.parquet`. Others receive NaN.
- RVOL: requires ≥ 10 prior trading days in `data/daily/` to compute (otherwise NaN). Uses a 30-trading-day lookback window.

### Survivorship Bias
- `symbol-properties-database.csv` contains **crypto/futures/forex ONLY** — not US equities.
- Survivorship is instead validated by checking minute + daily data presence.
- Only 1 ticker (ETEC) has zero data in the workspace.

### Split-Adjusted Prices
- The events data (`momentum_events/`) uses **split-adjusted** daily OHLCV prices.
- The filtered tick data (`filtered/`) has **raw unadjusted** trade prices.
- Open price validation must account for this: events where the price ratio > 1.8x are flagged as split-adjusted.
- Of 125 sampled events, 41 were consistent (<1% diff), 57 were split-adjusted, and 27 had genuine discrepancies (mostly pre-market first trades or thin liquidity).

### Daily Data Limitation
- The `daily/` folder only contains data from **December 2024 onward** (~82 trading days).
- RVOL can only be computed for events in this recent window (101 of 4,549 events = 2.2%).
- Historical RVOL would require archival daily data or computing from minute bars.

---

## Outputs

| File | Description |
|---|---|
| `scanner_context.parquet` | Ranked gapper leaderboard indexed by (ticker, date) |
| `plots/gap_distribution_histogram.png` | Gap % distribution across 10 peak trading days |
| `plots/leaderboard_snapshot.png` | Top 10 scanner for best momentum day |
| `plots/rank_stability_top3.png` | Rank + price overlay for top 3 super-runners |
| `build_log.md` | Execution trace, data gaps, discrepancies |
| `MANIFEST.md` | This document |

---

## Quality Control Checks
1. **Survivorship bias audit** — cross-reference tickers against minute + daily data availability (symbol-properties only has crypto/futures).
2. **Open price consistency** — compare events `open` vs first RTH trade in filtered/ (filtering to 13:30+ UTC to skip pre-market). Split-adjusted events (>1.8x ratio) are identified separately.
3. **Data gap report** — daily data only covers Dec 2024+, minute data coverage is 99.9%.

---

## Key Data Quality Findings
1. **Split-adjusted prices in events data** — many tickers show 2x–1000x discrepancy between events open and raw trade prices due to historical reverse splits. This affects 45% of sampled validations.
2. **RVOL limited to recent events** — only 2.2% of events have 30-day lookback daily data.
3. **Pre-market gap movement** — some RTH first trades differ from daily open by 10-40%, indicating significant price movement between the auction print and the first executable trade.
4. **Extreme gap outliers** — top gapper is GPOR (2021-05-18) at 441x gap from emergence out of bankruptcy. These extreme outliers should be considered for winsorization in downstream models.
