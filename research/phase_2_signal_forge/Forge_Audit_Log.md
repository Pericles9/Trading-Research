---
tags:
  - type/pipeline
  - domain/signal
  - project/src-core
  - status/complete
created: 2026-04-04
---

# Phase 2 Signal Forge — Audit Log
**Generated:** 2026-02-24 16:35:43
**Total execution time:** 358.4s
**GPU Device:** cuda (NVIDIA GeForce GTX 1070)
**Peak GPU Memory:** 0.0 MB

## Processing Summary
| Metric | Value |
|---|---|
| Events in scanner | 4,549 |
| Events with filtered data | 2,967 |
| Successfully processed | 2,820 |
| Skipped (no data) | 1,582 |
| Norm factor outliers | 147 |
| Errors | 0 |
| **Feature matrix rows** | **2,820** |
| Anatomy plots | 10 |

## Processing Time
| Stat | Value |
|---|---|
| Mean per event | 0.114s |
| Median per event | 0.069s |
| Max per event | 2.478s |
| Total GPU | 358.4s |

## Hawkes Parameters
| Param | Value |
|---|---|
| α (excitation) | 0.8 |
| β (decay) | 1.0 |
| μ (baseline) | Estimated per-event |

## Normalization Factor Outliers ($|\log_{10}(\phi)| > 3.0$)
| Ticker | Date | φ | Detail |
|---|---|---|---|
| SINT | 2020-06-22 | 20146.520147 | log10(phi)=4.30 |
| GNPX | 2020-01-21 | 1983.471074 | log10(phi)=3.30 |
| STSS | 2024-05-28 | 6600.000000 | log10(phi)=3.82 |
| SBFM | 2022-04-05 | 1996.789727 | log10(phi)=3.30 |
| ONCO | 2024-01-25 | 3400.000000 | log10(phi)=3.53 |
| SBFM | 2022-03-09 | 2000.000000 | log10(phi)=3.30 |
| UPC | 2021-03-29 | 3606.870229 | log10(phi)=3.56 |
| RETO | 2021-02-22 | 5000.000000 | log10(phi)=3.70 |
| NAOV | 2020-12-02 | 2200.000000 | log10(phi)=3.34 |
| DRMA | 2022-12-30 | 2365.851703 | log10(phi)=3.37 |
| LGHL | 2020-07-16 | 2500.000000 | log10(phi)=3.40 |
| CDT | 2024-08-08 | 12000.000000 | log10(phi)=4.08 |
| IVP | 2024-01-26 | 2500.000000 | log10(phi)=3.40 |
| LGHL | 2021-01-08 | 2490.019960 | log10(phi)=3.40 |
| SONN | 2021-08-19 | 2464.000000 | log10(phi)=3.39 |
| ACON | 2024-01-08 | 9045.000000 | log10(phi)=3.96 |
| WHLR | 2024-09-06 | 4214.301930 | log10(phi)=3.62 |
| FRGT | 2022-11-14 | 9846.576597 | log10(phi)=3.99 |
| JAGX | 2023-10-12 | 1500.000000 | log10(phi)=3.18 |
| SONN | 2020-04-14 | 2491.685393 | log10(phi)=3.40 |
| TENX | 2020-12-29 | 1600.000000 | log10(phi)=3.20 |
| FRGT | 2022-07-26 | 10000.000000 | log10(phi)=4.00 |
| ELAB | 2024-01-16 | 4900.000000 | log10(phi)=3.69 |
| SGBX | 2020-09-25 | 1280.000000 | log10(phi)=3.11 |
| NCNA | 2024-03-13 | 5000.000000 | log10(phi)=3.70 |
| RDHL | 2022-10-19 | 1004.827664 | log10(phi)=3.00 |
| SBFM | 2023-05-11 | 2000.000000 | log10(phi)=3.30 |
| JFBR | 2023-04-10 | 1547.000000 | log10(phi)=3.19 |
| NDRA | 2024-06-05 | 1749.969002 | log10(phi)=3.24 |
| TGL | 2023-10-18 | 3506.603774 | log10(phi)=3.54 |
| NUWE | 2024-05-07 | 1470.000000 | log10(phi)=3.17 |
| XXII | 2024-09-13 | 3104.994031 | log10(phi)=3.49 |
| CYN | 2022-04-21 | 13636.363184 | log10(phi)=4.13 |
| CYN | 2024-04-23 | 15000.000000 | log10(phi)=4.18 |
| NAOV | 2020-09-22 | 2200.000000 | log10(phi)=3.34 |
| SGBX | 2020-03-31 | 1280.000000 | log10(phi)=3.11 |
| ELAB | 2024-10-03 | 4899.554424 | log10(phi)=3.69 |
| QNRX | 2022-07-01 | 5249.993977 | log10(phi)=3.72 |
| SBFM | 2024-04-01 | 2000.000000 | log10(phi)=3.30 |
| AREB | 2024-07-15 | 4369.378577 | log10(phi)=3.64 |
| ENSC | 2021-12-09 | 3593.357934 | log10(phi)=3.56 |
| SNES | 2021-03-19 | 1200.000000 | log10(phi)=3.08 |
| SGBX | 2020-10-16 | 1280.000000 | log10(phi)=3.11 |
| SONN | 2022-03-16 | 2452.604062 | log10(phi)=3.39 |
| LGHL | 2023-04-28 | 2500.000000 | log10(phi)=3.40 |
| SMX | 2024-12-06 | 71322.452830 | log10(phi)=4.85 |
| ELAB | 2024-10-25 | 4900.427611 | log10(phi)=3.69 |
| CYN | 2023-12-07 | 15000.000000 | log10(phi)=4.18 |
| FAMI | 2020-06-18 | 2400.000000 | log10(phi)=3.38 |
| SOBR | 2024-06-04 | 1100.000000 | log10(phi)=3.04 |

## Error Log
No processing errors.

## Execution Trace
```
[     0.0s] Phase 2 Signal Forge — GPU=cuda
[     0.0s] Loading scanner context …
[     0.0s]   4,549 events loaded
[     0.0s] Processing events …
[    20.1s]   Progress: 200/4549 (ok=119 skip=78 outlier=3 err=0) ETA=438s
[    39.5s]   Progress: 400/4549 (ok=243 skip=148 outlier=9 err=0) ETA=410s
[   101.8s]   Progress: 1000/4549 (ok=609 skip=359 outlier=32 err=0) ETA=361s
[   121.7s]   Progress: 1200/4549 (ok=725 skip=428 outlier=47 err=0) ETA=340s
[   155.7s]   Progress: 1600/4549 (ok=974 skip=564 outlier=62 err=0) ETA=287s
[   170.0s]   Progress: 1800/4549 (ok=1089 skip=639 outlier=72 err=0) ETA=260s
[   225.3s]   Progress: 2600/4549 (ok=1580 skip=931 outlier=89 err=0) ETA=169s
[   237.8s]   Progress: 2800/4549 (ok=1701 skip=1000 outlier=99 err=0) ETA=149s
[   249.4s]   Progress: 3000/4549 (ok=1831 skip=1064 outlier=105 err=0) ETA=129s
[   268.0s]   Progress: 3200/4549 (ok=1968 skip=1122 outlier=110 err=0) ETA=113s
[   294.3s]   Progress: 3600/4549 (ok=2225 skip=1254 outlier=121 err=0) ETA=78s
[   309.5s]   Progress: 3800/4549 (ok=2350 skip=1324 outlier=126 err=0) ETA=61s
[   331.2s]   Progress: 4200/4549 (ok=2594 skip=1468 outlier=138 err=0) ETA=28s
[   352.2s]   Progress: 4549/4549 (ok=2820 skip=1582 outlier=147 err=0) ETA=0s
[   352.2s] DONE: 2820 events processed, 1582 skipped, 147 outliers, 0 errors
[   352.2s] Generating anatomy plots for top 10 super-runners …
[   352.8s]   Saved anatomy_SMRT_2021-08-25.png
[   353.2s]   Saved anatomy_NE_2021-06-09.png
[   353.7s]   Saved anatomy_SDRL_2022-10-14.png
[   354.2s]   Saved anatomy_GEN_2022-11-08.png
[   354.7s]   Saved anatomy_CURR_2024-09-03.png
[   355.2s]   Saved anatomy_PFH_2020-09-02.png
[   355.7s]   Saved anatomy_DXLG_2021-09-08.png
[   356.2s]   Saved anatomy_CRIS_2023-09-29.png
[   357.1s]   Saved anatomy_META_2022-06-09.png
[   357.6s]   Saved anatomy_VSSYW_2024-06-07.png
[   357.6s]   10 anatomy plots generated
[   357.6s] Generating intensity heatmap …
[   358.3s]   Heatmap generated with 30 events
[   358.3s] Assembling feature_matrix_v1.parquet …
[   358.4s]   Saved feature_matrix_v1.parquet: 2820 rows × 22 cols
[   358.4s] 
  === Feature Statistics ===
[   358.4s]     norm_factor                               n= 2820  mean=     41.9117  median=      1.0043  std=    129.1074
[   358.4s]     log_norm_factor                           n= 2820  mean=      0.6360  median=      0.0019  std=      0.8415
[   358.4s]     hawkes_intensity_flip_mean                n= 2624  mean=     87.6801  median=     60.3541  std=    112.8235
[   358.4s]     hawkes_intensity_flip_max                 n= 2624  mean=    310.8846  median=    226.4462  std=    397.1658
[   358.4s]     hawkes_accel_flip_mean                    n= 2624  mean=      0.0045  median=      0.0007  std=      0.0229
[   358.4s]     hawkes_accel_flip_max                     n= 2624  mean=      0.8000  median=      0.8000  std=      0.0000
[   358.4s]     cvd_flip_final                            n= 2624  mean= -36608.1639  median= -18188.0000  std=1922144.2667
[   358.4s]     cvd_convexity_flip_mean                   n= 2624  mean=    -23.4039  median=     -3.1229  std=    361.1554
[   358.4s]     cvd_convexity_flip_max                    n= 2624  mean=   1368.0313  median=    603.8115  std=   3512.9824
[   358.4s]     cvd_convexity_flip_sign_ratio             n= 2624  mean=      0.4887  median=      0.4898  std=      0.0769
[   358.4s]     ofi_flip_mean                             n= 2683  mean=     -3.0157  median=     -4.9718  std=    253.1868
[   358.4s]     ofi_flip_cumulative                       n= 2683  mean= 224414.5360  median=  -7300.0000  std=8610397.1854
[   358.4s]     ofi_flip_max                              n= 2683  mean=  53239.0980  median=  25700.0000  std= 123595.0859
[   358.4s]     ofi_flip_imbalance_ratio                  n= 2683  mean=      0.4863  median=      0.4908  std=      0.0691
[   358.4s]     pm_high_distance                          n= 2596  mean=     -0.1712  median=     -0.1443  std=      0.1543
[   358.4s]     pm_high_price                             n= 2596  mean=    181.4346  median=     15.8118  std=   1063.2832
[   358.4s]     pm_volume_ratio                           n= 2581  mean=     37.1535  median=     15.0747  std=    190.8819
[   358.4s]     pm_trade_count                            n= 2820  mean=  52850.6518  median=  32139.5000  std=  68397.7058
[   358.4s] 
Writing Forge_Audit_Log.md …
```

## Related

- [[Phase 2 — Signal Forge]] — parent phase summary doc
- [[Forge_Audit_Log_v2]] — v2 revised audit log
- [[SIGNAL_DICTIONARY]] — feature definitions
- [[00-Index]] — vault index
