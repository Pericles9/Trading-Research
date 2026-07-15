---
tags:
  - type/pipeline
  - domain/signal
  - project/src-core
  - status/complete
created: 2026-04-04
---

# Phase 2 (REVISED) — Extended Signal Forge — Audit Log
**Generated:** 2026-02-24 20:44:25
**Total execution time:** 653.5s
**GPU Device:** cuda (NVIDIA GeForce GTX 1070)
**Peak GPU Memory:** 0.0 MB
**Timeline:** 04:00–16:00 ET (full day)
**Hawkes Freeze Threshold:** 5.0s
**LULD Halt Detection Threshold:** 300.0s

## Processing Summary
| Metric | Value |
|---|---|
| Events in scanner | 4,549 |
| Events with filtered data | 2,963 |
| Successfully processed | 2,816 |
| Skipped (no data) | 1,586 |
| Norm factor outliers | 147 |
| Errors | 0 |
| **Feature matrix rows** | **2,816** |
| **Feature matrix columns** | **37** |
| Events with halts | 1,067 |
| Anatomy plots | 12 |

## Processing Time
| Stat | Value |
|---|---|
| Mean per event | 0.207s |
| Median per event | 0.130s |
| Max per event | 4.118s |
| Total wall-clock | 653.5s |

## Hawkes Parameters (Halt-Stitched)
| Param | Value |
|---|---|
| α (excitation) | 0.8 |
| β (decay) | 1.0 |
| μ (baseline) | Estimated per-event (active time only) |
| Hawkes freeze threshold | 5.0s |
| Halt detect threshold | 300.0s (LULD-style) |
| Halt behaviour | S frozen (no decay) during gap > freeze threshold |

## Key Changes from v1
- Hawkes kernel freezes S during halts — no phantom decay to zero
- Full-day timeline (04:00–16:00) instead of FLIP-only
- CVD runs across pre-market → RTH transition
- New features: is_post_halt, n_halts, halt durations, post-halt surge λ
- CVD Convexity measured at the 09:30 transition ("Elbow" window)
- 4-panel anatomy plots with halt zones + micro-zoom

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
[     0.0s] Phase 2 (REVISED) — Extended Signal Forge — GPU=cuda
[     0.0s]   Hawkes freeze: 5.0s | Halt detect: 300.0s | α=0.8 β=1.0
[     0.0s]   Timeline: 04:00–16:00 ET (full day)
[     0.0s] Loading scanner context …
[     0.0s]   4,549 events loaded
[     0.1s] Processing 4,549 events …
[    37.5s]   Progress: 200/4549 (ok=119 skip=78 outlier=3 err=0) ETA=816s
[    74.4s]   Progress: 400/4549 (ok=243 skip=148 outlier=9 err=0) ETA=772s
[   182.8s]   Progress: 1000/4549 (ok=609 skip=359 outlier=32 err=0) ETA=649s
[   217.6s]   Progress: 1200/4549 (ok=725 skip=428 outlier=47 err=0) ETA=607s
[   277.8s]   Progress: 1600/4549 (ok=974 skip=564 outlier=62 err=0) ETA=512s
[   303.5s]   Progress: 1800/4549 (ok=1089 skip=639 outlier=72 err=0) ETA=464s
[   408.2s]   Progress: 2600/4549 (ok=1580 skip=931 outlier=89 err=0) ETA=306s
[   429.7s]   Progress: 2800/4549 (ok=1700 skip=1001 outlier=99 err=0) ETA=268s
[   450.1s]   Progress: 3000/4549 (ok=1829 skip=1066 outlier=105 err=0) ETA=232s
[   480.6s]   Progress: 3200/4549 (ok=1966 skip=1124 outlier=110 err=0) ETA=203s
[   524.2s]   Progress: 3600/4549 (ok=2222 skip=1257 outlier=121 err=0) ETA=138s
[   548.6s]   Progress: 3800/4549 (ok=2347 skip=1327 outlier=126 err=0) ETA=108s
[   586.4s]   Progress: 4200/4549 (ok=2591 skip=1471 outlier=138 err=0) ETA=49s
[   622.8s]   Progress: 4549/4549 (ok=2816 skip=1586 outlier=147 err=0) ETA=0s
[   622.8s] DONE: 2816 events processed, 1586 skipped, 147 outliers, 0 errors
[   622.8s]   1067 events with halts detected
[   622.8s]   Best halt-runner: TPST 2023-10-11 (41 halts, max 604s, surge λ=881.9)
[   622.8s] Generating 4-panel anatomy plots …
[   640.2s]   ★ HALT_RUNNER_TPST_2023-10-11.png (PROOF CHART)
[   641.3s]   Saved anatomy_CBL_2021-11-02.png [1 halts]
[   642.1s]   Saved anatomy_SMRT_2021-08-25.png
[   642.8s]   Saved anatomy_NE_2021-06-09.png [14 halts]
[   643.6s]   Saved anatomy_DBD_2023-08-14.png [2 halts]
[   644.3s]   Saved anatomy_CORZW_2024-01-24.png [20 halts]
[   645.5s]   Saved anatomy_CORZ_2024-01-24.png [2 halts]
[   646.3s]   Saved anatomy_VAL_2021-05-03.png [4 halts]
[   647.1s]   Saved anatomy_SDRL_2022-10-14.png [23 halts]
[   649.3s]   Saved anatomy_GEN_2022-11-08.png
[   650.2s]   Saved anatomy_CURR_2024-09-03.png [6 halts]
[   651.0s]   Saved anatomy_PFH_2020-09-02.png [4 halts]
[   651.0s]   12 anatomy plots generated
[   651.0s] Generating full-day intensity heatmap …
[   653.4s]   Heatmap generated with 30 events
[   653.4s] Assembling feature_matrix_v2_ext.parquet …
[   653.5s]   Saved feature_matrix_v2_ext.parquet: 2816 rows × 37 cols
[   653.5s] 
  === Feature Statistics ===
[   653.5s]     norm_factor                                 n= 2816  mean=     41.9698  median=      1.0044  std=    129.1898
[   653.5s]     log_norm_factor                             n= 2816  mean=      0.6369  median=      0.0019  std=      0.8418
[   653.5s]     hawkes_intensity_flip_mean                  n= 2624  mean=     66.0199  median=     45.6266  std=     94.1371
[   653.5s]     hawkes_intensity_flip_max                   n= 2624  mean=    289.9865  median=    210.1106  std=    372.6609
[   653.5s]     hawkes_accel_flip_mean                      n= 2624  mean=      0.0120  median=      0.0002  std=      0.0955
[   653.5s]     hawkes_accel_flip_max                       n= 2624  mean=      0.8000  median=      0.8000  std=      0.0000
[   653.5s]     hawkes_pre_mean                             n= 2531  mean=     38.8749  median=     24.9830  std=     48.4779
[   653.5s]     hawkes_pre_max                              n= 2531  mean=    461.4589  median=    181.0331  std=    741.7414
[   653.5s]     hawkes_rth_mean                             n= 2816  mean=   1742.8474  median=     33.9439  std=  47054.5586
[   653.5s]     hawkes_rth_max                              n= 2816  mean=   2098.5147  median=    295.6557  std=  47045.1424
[   653.5s]     hawkes_fullday_mean                         n= 2816  mean=   1744.5054  median=     34.4471  std=  47054.4991
[   653.5s]     hawkes_fullday_max                          n= 2816  mean=   2290.2658  median=    361.5051  std=  47042.1332
[   653.5s]     hawkes_post_halt_surge                      n= 1067  mean=   4741.9723  median=    147.2845  std=  76371.7539
[   653.5s]     cvd_flip_final                              n= 2624  mean=-188091.9238  median= -51637.0000  std=2168589.2609
[   653.5s]     cvd_fullday_final                           n= 2816  mean=-1790628.8814  median=-661982.5000  std=4828603.9562
[   653.5s]     cvd_convexity_flip_mean                     n= 2624  mean=    -19.7702  median=     -3.2742  std=    325.0109
[   653.5s]     cvd_convexity_flip_max                      n= 2624  mean=   1927.6210  median=    753.7810  std=   5090.7871
[   653.5s]     cvd_convexity_flip_sign_ratio               n= 2624  mean=      0.4929  median=      0.4922  std=      0.0686
[   653.5s]     cvd_convexity_transition_mean               n= 2580  mean=    -33.6775  median=     -2.4986  std=    581.6038
[   653.5s]     cvd_convexity_transition_max                n= 2580  mean=   2671.2952  median=    895.6705  std=   9471.9494
[   653.5s]     ofi_flip_mean                               n= 2682  mean=     -3.0061  median=     -4.9607  std=    253.2335
[   653.5s]     ofi_flip_cumulative                         n= 2682  mean= 224498.6204  median=  -7300.0000  std=8612001.7521
[   653.5s]     ofi_flip_max                                n= 2682  mean=  53255.6674  median=  25700.0000  std= 123615.1534
[   653.5s]     ofi_flip_imbalance_ratio                    n= 2682  mean=      0.4863  median=      0.4908  std=      0.0691
[   653.5s]     pm_high_distance                            n= 2596  mean=     -0.1712  median=     -0.1443  std=      0.1543
[   653.5s]     pm_high_price                               n= 2596  mean=    181.4346  median=     15.8118  std=   1063.2832
[   653.5s]     pm_volume_ratio                             n= 2581  mean=     37.1535  median=     15.0747  std=    190.8819
[   653.5s]     pm_trade_count                              n= 2816  mean=  52925.7237  median=  32159.5000  std=  68417.2427
[   653.5s]     is_post_halt                                n= 2816  mean=      0.3789  median=      0.0000  std=      0.4852
[   653.5s]     n_halts                                     n= 2816  mean=      2.5295  median=      0.0000  std=      5.4904
[   653.5s]     max_halt_duration_sec                       n= 2816  mean=    627.4553  median=      0.0000  std=   1898.7832
[   653.5s]     total_halt_duration_sec                     n= 2816  mean=   2095.8763  median=      0.0000  std=   5209.4757
[   653.5s] 
  === Halt Context Summary ===
[   653.5s]     Events with halts: 1067 / 2816 (37.9%)
[   653.5s]     Avg halts per event: 6.7
[   653.5s]     Max halt duration: 19660s
[   653.5s]     Avg post-halt surge λ: 4742.0
[   653.5s]     Top 5 halt-runners by max halt duration:
[   653.5s]       BBLGW    2024-04-09  halts=4  max_dur=19660s  surge_λ=58.2
[   653.5s]       AMPGW    2022-03-10  halts=2  max_dur=19598s  surge_λ=8.3
[   653.5s]       IXHL     2022-03-14  halts=2  max_dur=19293s  surge_λ=125.8
[   653.5s]       PIIIW    2022-05-02  halts=1  max_dur=18332s  surge_λ=24.1
[   653.5s]       SEATW    2023-09-08  halts=4  max_dur=17407s  surge_λ=23.3
[   653.5s] 
Writing Forge_Audit_Log_v2.md …
```

## Related

- [[Phase 2 — Signal Forge]] — parent phase summary doc
- [[Forge_Audit_Log]] — v1 audit log
- [[SIGNAL_DICTIONARY_v2]] — v2 feature definitions
- [[00-Index]] — vault index
