---
tags:
  - type/pipeline
  - domain/signal
  - project/src-core
  - status/complete
created: 2026-04-04
---

# GOLDEN FEATURES — Phase 3 Alpha Hunter

## Top 5 Features That Drive Contagion Prediction

These features, ranked by mean |SHAP value|, have the most influence on
the XGBoost model's prediction of forward Hawkes intensity (Y_Contagion).

---

### #1: `hawkes_rth_mean`
- **SHAP Mean |Value|:** 13938.4482
- **XGBoost Gain Rank:** #1
- **Interpretation:** Hawkes self-exciting intensity — measures trade clustering momentum.

### #2: `hawkes_fullday_mean`
- **SHAP Mean |Value|:** 4157.1064
- **XGBoost Gain Rank:** #2
- **Interpretation:** Hawkes self-exciting intensity — measures trade clustering momentum.

### #3: `hawkes_intensity_flip_mean`
- **SHAP Mean |Value|:** 2564.8135
- **XGBoost Gain Rank:** #3
- **Interpretation:** Hawkes self-exciting intensity — measures trade clustering momentum.

### #4: `hawkes_rth_max`
- **SHAP Mean |Value|:** 1868.9569
- **XGBoost Gain Rank:** #4
- **Interpretation:** Hawkes self-exciting intensity — measures trade clustering momentum.

### #5: `hawkes_accel_flip_mean`
- **SHAP Mean |Value|:** 1676.1364
- **XGBoost Gain Rank:** #9
- **Interpretation:** Hawkes self-exciting intensity — measures trade clustering momentum.

---

## Full SHAP Ranking (Top 15)

| Rank | Feature | Mean |SHAP| | XGBoost Gain Rank |
|---|---|---|---|
| 1 | `hawkes_rth_mean` | 13938.4482 | #1 |
| 2 | `hawkes_fullday_mean` | 4157.1064 | #2 |
| 3 | `hawkes_intensity_flip_mean` | 2564.8135 | #3 |
| 4 | `hawkes_rth_max` | 1868.9569 | #4 |
| 5 | `hawkes_accel_flip_mean` | 1676.1364 | #9 |
| 6 | `volume` | 663.2959 | #6 |
| 7 | `cvd_convexity_flip_sign_ratio` | 645.7985 | #7 |
| 8 | `hawkes_accel_flip_max` | 555.6824 | #10 |
| 9 | `max_halt_duration_sec` | 538.8381 | #8 |
| 10 | `total_halt_duration_sec` | 512.1044 | #15 |
| 11 | `ofi_flip_imbalance_ratio` | 469.0812 | #11 |
| 12 | `cvd_convexity_flip_mean` | 415.0751 | #21 |
| 13 | `cvd_flip_final` | 412.0722 | #19 |
| 14 | `cvd_fullday_final` | 382.0078 | #30 |
| 15 | `pm_trade_count` | 362.8561 | #12 |

---

## Model Performance

| Metric | Value |
|---|---|
| Train R² | 0.2629 |
| Test R² | 0.6235 |
| Train RMSE | 25466.80 |
| Test RMSE | 26655.51 |
| Best Iteration | 27 |
| Features Used | 36 |
| Monotonic Constraints | gap_rank (decreasing) |

## Related

- [[Phase 3 — Alpha Hunter]] — parent phase summary doc
- [[Alpha_Audit]] — model performance report
- [[00-Index]] — vault index
