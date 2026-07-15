---
tags:
  - type/pipeline
  - domain/data
  - project/src-core
  - status/complete
created: 2026-04-04
---

# Phase 1 Extended — Build Log
**Generated:** 2026-02-23 21:28:50  
**Total execution time:** 459.0s

## Execution Trace
```
[     0.0s] STEP 1: Loading Phase 1 scanner context …
[     0.0s]   4,549 events loaded
[     0.1s] STEP 2: Processing events (split norm + pre-market metrics) …
[    53.6s]   … processed 500 events
[   153.3s]   … processed 1,000 events
[   199.0s]   … processed 1,500 events
[   252.7s]   … processed 2,000 events
[   336.0s]   … processed 2,500 events
[   429.9s]   Processed: 2,985
[   429.9s]   Skipped (no filtered dir): 1,550
[   429.9s]   Skipped (no trades file):  0
[   429.9s]   Skipped (no event-day):    14
[   429.9s]   Outlier norm factors:      1,080
[   429.9s] STEP 3: Computing PM_Relative_Rank at 7/8/9 AM …
[   433.4s]   Rank snapshots: 7,480 rows across 1016 dates
[   433.4s] STEP 4: Assembling extended_context …
[   433.4s]   Extended context: 2,985 rows, 25 columns
[   433.4s]   Columns: ['ticker', 'date', 'prev_close', 'open_adj', 'high_adj', 'close_adj', 'volume', 'gap_pct', 'gap_rank', 'norm_factor', 'pm_high', 'pm_volume', 'pm_trade_count', 'vol_5min', 'pm_rank_7am', 'pm_rank_8am', 'pm_rank_9am', 'sigma_pm', 'sigma_flip', 'sigma_std', 'n_pm_bars', 'n_flip_bars', 'n_std_bars', 'vol_ratio_flip_pm', 'regime_shift_flag']
[   433.4s]   Saved extended_context.parquet
[   433.5s]   Saved volatility_analysis.parquet (2,973 rows)
[   433.5s] STEP 5: Summary statistics …
[   433.5s]   PM_High available: 2,706 / 2,985
[   433.5s]   PM_Volume > 0:     2,706 / 2,985
[   433.5s]   σ_PM available:    2,629
[   433.5s]   σ_FLIP available:  2,666
[   433.5s]   Vol ratio (σ_FLIP/σ_PM): median=0.93, mean=inf, >3 regime shifts: 121 / 2,582 (4.7%)
[   433.5s]   Rank stability: #1 at 9 AM → #1 at open: 671 / 1016 (66.0%)
[   433.5s] STEP 6: Generating visualizations …
[   433.5s]   6a: Rank Migration plot …
[   433.5s]     Best day for rank migration: 2024-12-27 (16 gappers, 16 with PM data)
[   436.4s]     Saved rank_migration.png (6 tickers)
[   436.4s]   6b: Volatility heatmap …
[   436.4s]     Sampling 500 events for heatmap …
[   457.9s]     Saved volatility_heatmap.png (145 time bins)
[   457.9s]   6c: Split-fix verification scatter …
[   459.0s]     Saved split_fix_verification.png
[   459.0s] STEP 7: Writing DATA_FIXES.md …
[   459.0s]   DATA_FIXES.md written
[   459.0s] STEP 8: Writing MANIFEST.md …
[   459.0s]   MANIFEST.md written
[   459.0s] BUILD COMPLETE in 459.0s
```
