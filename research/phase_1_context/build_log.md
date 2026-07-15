---
tags:
  - type/pipeline
  - domain/data
  - project/src-core
  - status/complete
created: 2026-04-04
---

# Phase 1 Context Engine — Build Log
**Generated:** 2026-02-23 20:51:17  
**Total execution time:** 84.8s

## Summary Statistics
| Metric | Value |
|---|---|
| Raw momentum events loaded | 24,607 |
| Events after 30% gap filter | 4,549 |
| Unique dates | 1,307 |
| Unique tickers | 1,653 |
| Minute data coverage | 4,544 / 4,549 (99.9%) |
| RVOL computed | 101 / 4,549 (2.2%) |
| Open price consistent (<1% diff) | 41 / 125 checked |
| Open price split-adjusted discrepancy | 57 / 125 checked |
| Genuine open price discrepancies | 27 / 125 checked |
| Tickers missing all data | 1 |

## Key Data Gap Findings

### Daily Data Coverage
The `daily/` folder only contains data from **~Dec 2024 onward** (~82 trading days).
Since momentum events span 2020–2025, RVOL can only be computed for recent events.
Historical RVOL would require either archival daily data or computing average volume
from the minute-bar data.

### Split Adjustment
The events data (momentum_events/) uses **split-adjusted prices** while the raw
trade data (filtered/) has **unadjusted tick-level prices**. This explains the large
discrepancies where events_open >> first_trade (reverse splits) or first_trade >>
events_open (forward splits). Of 125 events checked, 57
showed split-adjusted ratios (>5x price difference).

## Data Gaps — Missing Daily Files
The following tickers in the scanner had no `daily/` parquet file (expected — daily data
only covers Dec 2024+):

```
AIRO
AMDU
ANGX
APXT
APXTW
ATON
AVGG
AVGU
BBBY
BGL
BLUW
BLUWU
BLUWW
BNBX
BRBI
BULL
BULLW
CAI
CBIO
CCCXW
CIGL
CRE
CRWG
CUPR
CV
CVNX
DAIC
DFDV
DNLI
DNUT
DOC
DOCS
DOGZ
DOMH
DOYU
DPRO
DRCT
DRMA
DRTS
DRUG
DSXpB
DSY
DTCK
DTIL
DTSS
DTST
DTSTW
DUO
DVAX
DVLT
```

## Open Price Discrepancies
### Genuine Discrepancies (not split-adjusted, >1% diff)
| Ticker | Date | Events Open | First Trade | Diff % |
|---|---|---|---|---|
| SAVA | 2020-09-14 | $5.11 | $7.17 | 40.3% |
| ACRS | 2021-01-19 | $14.05 | $9.38 | 33.2% |
| RVSN | 2024-01-16 | $1.93 | $2.45 | 26.9% |
| ANIX | 2021-03-12 | $6.71 | $4.98 | 25.8% |
| TDACU | 2021-02-26 | $21.53 | $16.30 | 24.3% |
| BFRIW | 2022-05-12 | $1.14 | $0.87 | 23.7% |
| GLBZ | 2023-05-03 | $9.47 | $7.58 | 20.0% |
| GTEC | 2020-11-10 | $3.45 | $3.90 | 13.0% |
| NNAVW | 2024-04-02 | $2.82 | $2.46 | 12.6% |
| CRGO | 2023-01-27 | $14.78 | $13.05 | 11.7% |
| EVGO | 2021-11-09 | $17.62 | $15.56 | 11.7% |
| MDAI | 2024-01-29 | $3.70 | $3.27 | 11.6% |
| AIRE | 2024-12-26 | $1.92 | $2.14 | 11.5% |
| BBBY | 2022-03-07 | $27.27 | $30.26 | 11.0% |
| APGE | 2024-03-05 | $59.91 | $65.41 | 9.2% |
| AVXL | 2021-02-04 | $19.94 | $18.25 | 8.5% |
| GTEC | 2021-11-19 | $8.78 | $8.07 | 8.1% |
| CCTG | 2024-02-02 | $5.78 | $5.32 | 7.9% |
| PRZO | 2023-12-20 | $1.09 | $1.01 | 7.3% |
| MYSZ | 2024-12-27 | $8.96 | $8.48 | 5.4% |
| SIG | 2020-01-16 | $28.35 | $27.26 | 3.8% |
| AREC | 2021-02-02 | $3.40 | $3.50 | 2.9% |
| KURA | 2024-01-24 | $18.40 | $18.80 | 2.2% |
| ONMD | 2024-05-23 | $1.40 | $1.37 | 2.1% |
| TDS | 2023-08-04 | $10.80 | $10.63 | 1.6% |
| CHRS | 2023-12-27 | $3.00 | $2.96 | 1.3% |
| DYN | 2024-01-03 | $18.00 | $18.23 | 1.3% |

### Split-Adjusted Events (57 total)
These events have a price ratio >5x between events_open and first filtered trade,
indicating a stock split/reverse-split between the event date and data collection.

## Survivorship Bias Audit
- Scanner contains 1,653 unique tickers.
- **1** tickers have neither minute nor daily data in the workspace.
- Note: `symbol-properties-database.csv` only contains crypto/futures — NOT US equities.
- Survivorship check uses minute + daily data presence as alternative signal.

## Execution Trace
```
[     0.0s] STEP 1: Loading momentum-event universe …
[     0.0s]   filtered_events: 23,268 rows
[     0.0s]   full_scan:        18,660 rows
[     0.0s]   scan_2025:        5,950 rows
[     0.1s]   Combined universe (deduped): 26,423 events across 1,466 dates
[     0.1s] STEP 2: Calculating gap at open & applying 30 % filter …
[     0.1s]   Events before filter: 24,607
[     0.1s]   Events after 30% gap filter: 4,549
[     0.1s]   Unique dates with >=1 gapper: 1,307
[     0.1s] STEP 3: Computing Gap_Rank per date …
[     0.1s]   Rank range: 1 – 18
[     0.1s] STEP 4: Computing Volume_Intensity (first 5 min) …
[    16.7s]   Minute data found for 4,544 / 4,549 events
[    16.7s]   Missing minute files: 5
[    16.7s] STEP 5: Computing RVOL (30-day average) …
[    16.7s]   Loading daily data for 1,653 unique tickers …
[    18.2s]   RVOL computed for 101 events
[    18.2s]   Missing daily files: 1,222 tickers
[    18.2s] STEP 6: Saving scanner_context.parquet …
[    18.2s]   Saved 4,549 rows → scanner_context.parquet
[    18.2s] STEP 7: Generating visualizations …
[    18.2s]   7a: Gap distribution histogram …
[    18.4s]     Saved gap_distribution_histogram.png (146 data points)
[    18.4s]   7b: Leaderboard snapshot …
[    18.7s]     Saved leaderboard_snapshot.png for 2025-09-09
[    18.7s]   7c: Rank stability plots (top 3 super-runners) …
[    19.3s]     Saved rank_stability_top3.png (3 runners)
[    19.3s] STEP 8: Quality control …
[    19.3s]   8a: Survivorship bias audit …
[    19.4s]     Tickers in scanner: 1,653
[    19.4s]     Tickers with minute data: 1,652
[    19.4s]     Tickers with daily data : 431
[    19.4s]     Tickers missing BOTH   : 1
[    19.4s]     Sample (no data at all): ['ETEC']
[    19.4s]   8b: Open price consistency check (events open vs filtered first trade) …
[    19.4s]        NOTE: Events data may have split-adjusted prices while trade data is raw.
[    84.8s]     Checked 125 events:
[    84.8s]       Consistent (<1% diff): 41
[    84.8s]       Split-adjusted (>5x ratio): 57
[    84.8s]       Genuine discrepancy: 27
[    84.8s]     Top genuine discrepancies:
[    84.8s]       SAVA 2020-09-14: events_open=$5.11, first_trade=$7.17, diff=40.3%
[    84.8s]       ACRS 2021-01-19: events_open=$14.05, first_trade=$9.38, diff=33.2%
[    84.8s]       RVSN 2024-01-16: events_open=$1.93, first_trade=$2.45, diff=26.9%
[    84.8s]       ANIX 2021-03-12: events_open=$6.71, first_trade=$4.98, diff=25.8%
[    84.8s]       TDACU 2021-02-26: events_open=$21.53, first_trade=$16.30, diff=24.3%
[    84.8s]       BFRIW 2022-05-12: events_open=$1.14, first_trade=$0.87, diff=23.7%
[    84.8s]       GLBZ 2023-05-03: events_open=$9.47, first_trade=$7.58, diff=20.0%
[    84.8s]       GTEC 2020-11-10: events_open=$3.45, first_trade=$3.90, diff=13.0%
[    84.8s]       NNAVW 2024-04-02: events_open=$2.82, first_trade=$2.46, diff=12.6%
[    84.8s]       CRGO 2023-01-27: events_open=$14.78, first_trade=$13.05, diff=11.7%
[    84.8s] STEP 9: Writing build_log.md …
```
