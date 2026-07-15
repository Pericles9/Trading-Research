---
tags:
  - type/pipeline
  - domain/data
  - project/src-core
  - status/complete
created: 2026-04-04
---

# DATA_FIXES.md — Split-Adjustment & Outlier Treatment
**Generated:** 2026-02-23 21:28:50

## 1. Split-Adjustment Normalization

### Problem
The momentum-events data (`momentum_events/*.parquet`) uses **split-adjusted** OHLCV
prices from the market data provider.  The raw tick-level data in `filtered/` has
**unadjusted** trade prices.  This creates a mismatch that propagates into any
feature comparing tick-level prices to daily OHLCV (e.g., open-gap calculations,
pre-market high ratios).

### Solution: Normalization Factor
For every event with filtered/ trade data, we compute:

$$
\text{Norm\_Factor} = \frac{\text{Events\_Open (adjusted)}}{\text{First\_RTH\_Trade (raw)}}
$$

Where **First_RTH_Trade** is the first trade at or after 13:30 UTC (9:30 AM ET) on
the event date within the filtered/ trades file.

All raw tick prices are then multiplied by this factor:
$$
P_{adj} = P_{raw} \times \text{Norm\_Factor}
$$

### Normalization Factor Statistics
| Stat | Value |
|---|---|
| Count | 2,985 |
| Mean | 431.7462 |
| Median | 1.2754 |
| Std | 3136.5146 |
| Min | 0.026175 |
| Max | 74543.29 |
| Factors = 1.0 (no split) | 1,163 (39.0%) |
| Extreme factors (>10x or <0.1x) | 1,080 |

### Extreme Normalization Factors (>10x or <0.1x)
These represent massive reverse-splits or corporate actions:

| Ticker | Date | Norm Factor | Events Open | First Trade |
|---|---|---|---|---|
| SMX | 2024-12-06 | 74543.2853 | $37800.90 | $0.5071 |
| SMX | 2024-12-30 | 73245.6452 | $34227.69 | $0.4673 |
| SMX | 2024-12-26 | 70278.2939 | $24962.85 | $0.3552 |
| DGLY | 2020-06-08 | 40000.0000 | $143600.00 | $3.5900 |
| NDRA | 2022-04-08 | 35000.0000 | $21700.00 | $0.6200 |
| VCIG | 2023-06-20 | 29400.0000 | $111720.00 | $3.8000 |
| VCIG | 2024-10-29 | 29400.0000 | $3328.08 | $0.1132 |
| SINT | 2022-12-19 | 25000.0000 | $2100.00 | $0.0840 |
| EJH | 2023-07-31 | 25000.0000 | $3992.50 | $0.1597 |
| APVO | 2021-11-23 | 23745.8282 | $309645.60 | $13.0400 |
| TNXP | 2022-12-12 | 23357.8732 | $11422.00 | $0.4890 |
| SINT | 2020-06-22 | 20146.5201 | $55000.00 | $2.7300 |
| SINT | 2022-10-26 | 20000.0000 | $2722.00 | $0.1361 |
| TNXP | 2022-06-01 | 19943.9776 | $71200.00 | $3.5700 |
| GDHG | 2024-06-12 | 18750.0000 | $5250.00 | $0.2800 |
| GDHG | 2024-07-01 | 18750.0000 | $3731.25 | $0.1990 |
| GWAV | 2024-05-09 | 16500.0000 | $1303.50 | $0.0790 |
| GWAV | 2024-05-15 | 16500.0000 | $1056.00 | $0.0640 |
| GWAV | 2024-05-16 | 16500.0000 | $1668.15 | $0.1011 |
| GWAV | 2024-05-17 | 16500.0000 | $3445.20 | $0.2088 |

## 2. GPOR-Style Outlier Winsorization

### Problem
Some events represent **bankruptcy emergence** or **extreme corporate restructuring**
where the gap percentage is astronomically high (e.g., GPOR at 441x, CBL at 290x).
These outliers would dominate any ML feature distribution and corrupt gradient-based
models.

### Treatment
Events with `gap_pct > 10.0` (1,000%) are flagged in `winsorized_flag`.
Downstream models should either:
- **Winsorize** these to the 99th percentile of gap_pct
- **Exclude** them from training (they are n=21 events)
- **Bin** them into a separate "restructuring" class

### Flagged Events
| Ticker | Date | Gap % | Norm Factor |
|---|---|---|---|
| CBL | 2021-11-02 | 29066.7% | 1.0000 |
| SMRT | 2021-08-25 | 17757.1% | 1.0000 |
| NE | 2021-06-09 | 12150.0% | 1.0000 |
| DBD | 2023-08-14 | 9500.0% | 1.0000 |
| CORZW | 2024-01-24 | 7900.0% | 1.0000 |
| CORZ | 2024-01-24 | 6837.5% | 1.0000 |
| VAL | 2021-05-03 | 6563.6% | 1.0041 |
| SDRL | 2022-10-14 | 4998.0% | 1.0396 |
| GEN | 2022-11-08 | 4909.5% | 1.0520 |
| CURR | 2024-09-03 | 4683.3% | 1.0000 |
| PFH | 2020-09-02 | 3711.9% | 1.0000 |
| AI | 2020-12-09 | 3563.0% | 1.0000 |
| DXLG | 2021-09-08 | 3276.2% | 0.9958 |
| CAMP | 2024-10-11 | 2690.0% | 1.0000 |
| CRC | 2020-10-28 | 1590.7% | 1.0000 |
| CRIS | 2023-09-29 | 1478.9% | 0.9967 |
| META | 2022-06-09 | 1478.2% | 0.9999 |
| HTZ | 2021-11-09 | 1374.7% | 1.0000 |
| VSSYW | 2024-06-07 | 1250.0% | 1.0004 |
| VTGN | 2023-08-07 | 1185.7% | 0.9818 |
| NUKK | 2023-12-26 | 1096.0% | 6.2947 |

## 3. Pre-Market Data Quality Notes

- **Pre-market trades available**: Of 2,985 processed events, 
  2,706 (90.7%) had 
  at least one pre-market trade.
- **Thin pre-market**: Some events have <10 PM trades, making PM_High unreliable.
  Events with `pm_trade_count < 10` should use PM metrics cautiously.
- **EDT/EST ambiguity**: UTC offsets are fixed at -4h (EDT). For EST dates 
  (Nov–Mar), pre-market session starts ~1h earlier in UTC. This affects the 
  7 AM / 8 AM / 9 AM rank snapshots by ±1 hour. Documented, not corrected.

## 4. Verification
The scatter plot `plots/split_fix_verification.png` shows Daily_Open vs First_Trade
before and after normalization. After normalization, the points collapse to the 
1:1 line, confirming the split-factor alignment.

## Related

- [[Phase 1b — Extended Hours]] — parent phase summary doc
- [[00-Index]] — vault index
