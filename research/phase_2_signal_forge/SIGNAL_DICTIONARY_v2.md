---
tags:
  - type/pipeline
  - domain/signal
  - project/src-core
  - status/complete
created: 2026-04-04
---

# Signal Dictionary — Phase 2 (REVISED) Extended Signal Forge

All features are computed per event (ticker, date) across the **full trading day
(04:00–16:00 ET)** with halt-stitched Hawkes and extended CVD.

---

## 1. Normalization

### `norm_factor` — Normalization Factor ($\phi$)
$$\phi = \frac{P_{\text{Adjusted, Open}}}{P_{\text{Raw, FirstRTHTrade}}}$$
- **Lookback:** N/A (point estimate at market open)
- **Target:** Bridges split-adjusted event prices with raw tick data.
  All downstream prices are pre-multiplied by $\phi$.
- **Units:** Dimensionless ratio

### `log_norm_factor` — Log Normalization Factor
$$\log_{10}(\phi)$$
- **Target:** Quality filter. Events with $|\log_{10}(\phi)| > 3$ are flagged.
- **Units:** Log-scale ratio

---

## 2. Hawkes Intensity (Halt-Stitched)

### Mathematical Foundation
The Hawkes self-exciting point process models trade arrival clustering.
Given trade timestamps $\{t_1, t_2, \ldots, t_n\}$:

$$\lambda(t) = \mu + \alpha \sum_{t_j < t} e^{-\beta(t - t_j)}$$

where:
- $\mu$: baseline intensity (trades/sec, estimated from **active** time only)
- $\alpha$: excitation amplitude
- $\beta$: decay rate ($1/\beta$ = memory timescale)

### Halt-Stitching Logic
**v2 Change:** During gaps $\Delta t > 5\text{s}$ (Hawkes freeze threshold),
the running sum $S$ is **frozen** — no exponential decay occurs:

$$S_i = \begin{cases}
  e^{-\beta \Delta t_i} \cdot S_{i-1} + 1 & \text{if } \Delta t_i \leq 5\text{s (normal)}} \\
  S_{i-1} + 1 & \text{if } \Delta t_i > 5\text{s (halt/gap)}}
\end{cases}$$

This prevents the Hawkes intensity from decaying to zero during a trading halt,
preserving the self-exciting momentum signal through LULD pauses.

**Baseline $\mu$ estimation** uses only active trading time (excluding halted gaps):
$$\mu = \frac{N_{\text{active trades}}}{\sum \Delta t_i \cdot \mathbb{1}[\Delta t_i \leq 5\text{s}]}$$

Parameters: $\alpha = 0.8$, $\beta = 1.0$ (1-second decay), freeze threshold = 5s.

### `hawkes_intensity_flip_mean`
- **Window:** FLIP regime (09:30:00 – 09:44:59 ET)
- **Aggregation:** Mean of $\lambda(t_i)$ over all trades in FLIP
- **Target:** Average trade clustering at the open shock.

### `hawkes_intensity_flip_max`
- **Window:** FLIP regime
- **Aggregation:** Max of $\lambda(t_i)$
- **Target:** Peak trade intensity during the volatility shock.

### `hawkes_accel_flip_mean`
$$\Delta\lambda(t_i) = \lambda(t_i) - \lambda(t_{i-1})$$
- **Window:** FLIP regime
- **Aggregation:** Mean of $\Delta\lambda$
- **Target:** Average acceleration of trade arrivals.

### `hawkes_accel_flip_max`
- **Window:** FLIP regime
- **Aggregation:** Max of $\Delta\lambda$

### `hawkes_pre_mean` *(v2 new)*
- **Window:** PRE regime (04:00 – 09:29 ET)
- **Aggregation:** Mean of $\lambda(t_i)$
- **Target:** Pre-market trade clustering. High values indicate significant
  pre-market activity and institutional positioning.

### `hawkes_pre_max` *(v2 new)*
- **Window:** PRE regime
- **Aggregation:** Max of $\lambda(t_i)$
- **Target:** Peak pre-market trade intensity.

### `hawkes_rth_mean` *(v2 new)*
- **Window:** RTH (09:30 – 16:00 ET)
- **Aggregation:** Mean of $\lambda(t_i)$
- **Target:** Average sustained trade clustering through the full session.

### `hawkes_rth_max` *(v2 new)*
- **Window:** RTH
- **Aggregation:** Max of $\lambda(t_i)$

### `hawkes_fullday_mean` *(v2 new)*
- **Window:** Full day (04:00 – 16:00 ET)
- **Aggregation:** Mean of $\lambda(t_i)$
- **Target:** Overall daily trade clustering.

### `hawkes_fullday_max` *(v2 new)*
- **Window:** Full day
- **Aggregation:** Max of $\lambda(t_i)$
- **Target:** Absolute peak trade intensity across the entire day.

### `hawkes_post_halt_surge` *(v2 new)*
- **Window:** First 60 seconds after each halt resumption
- **Aggregation:** Max of $\lambda(t_i)$ across all halt-resumption windows
- **Target:** Measures the intensity surge when trading resumes after a halt.
  Higher values indicate explosive momentum resumption post-LULD.

---

## 3. Cumulative Volume Delta (CVD) & Convexity

### Trade Classification (Tick Rule)
$$\text{sign}_i = \begin{cases} +1 & \text{if } P_i > P_{i-1} \text{ (uptick)} \\ -1 & \text{if } P_i < P_{i-1} \text{ (downtick)} \\ \text{sign}_{i-1} & \text{if } P_i = P_{i-1} \text{ (zero-tick)} \end{cases}$$

### CVD
$$\text{CVD}(t) = \sum_{i: t_i \leq t} \text{sign}_i \cdot V_i$$

**v2 Change:** CVD is now computed across the **full day (04:00–16:00)** instead
of FLIP-only, capturing the pre-market → RTH transition dynamics.

### CVD Convexity (2nd Derivative)
$$\text{CVD}''(t) \approx \text{SavGol}_{k=2, w=30\text{s}}(\text{CVD}(t))$$
Savitzky-Golay 2nd derivative on CVD resampled to 1-second bins.

### `cvd_flip_final`
- **Window:** End of FLIP regime
- **Aggregation:** Final CVD value at 09:45:00
- **Target:** Net directional volume during the shock.

### `cvd_fullday_final` *(v2 new)*
- **Window:** End of RTH (16:00 ET)
- **Aggregation:** Final CVD value over the full day
- **Target:** Total net directional volume from pre-market through close.

### `cvd_convexity_flip_mean`
- **Window:** FLIP regime, 30-second sliding window
- **Aggregation:** Mean of CVD''
- **Target:** "Parabolic buying" — sustained positive convexity.

### `cvd_convexity_flip_max`
- **Window:** FLIP regime
- **Aggregation:** Max of CVD''

### `cvd_convexity_flip_sign_ratio`
$$\text{ratio} = \frac{\sum \mathbb{1}[\text{CVD}''(t) > 0]}{N_{\text{bins}}}$$
- **Target:** Fraction of time with positive convexity. Values > 0.7 = persistent buying.

### `cvd_convexity_transition_mean` *(v2 new)*
- **Window:** Transition window (09:25 – 09:35 ET), spanning the RTH open
- **Aggregation:** Mean of CVD''
- **Target:** Captures the "Elbow" at the 09:30 AM transition — how convexity
  shifts as pre-market flows collide with the opening bell.

### `cvd_convexity_transition_max` *(v2 new)*
- **Window:** Transition window (09:25 – 09:35 ET)
- **Aggregation:** Max of CVD''
- **Target:** Peak convexity at the transition — indicates explosive volume
  acceleration at the open.

---

## 4. Order Flow Imbalance (OFI)

### Mathematical Foundation
$$\text{OFI}_i = \Delta B_i^{\text{size}} \cdot \mathbb{1}[B_i^{\text{price}} \geq B_{i-1}^{\text{price}}]
              - \Delta A_i^{\text{size}} \cdot \mathbb{1}[A_i^{\text{price}} \leq A_{i-1}^{\text{price}}]$$

### `ofi_flip_mean`
- **Window:** FLIP regime
- **Aggregation:** Mean OFI per quote update

### `ofi_flip_cumulative`
- **Window:** FLIP regime
- **Aggregation:** Cumulative sum of OFI

### `ofi_flip_max`
- **Window:** FLIP regime
- **Aggregation:** Max single OFI reading

### `ofi_flip_imbalance_ratio`
$$\frac{\sum \mathbb{1}[\text{OFI}_i > 0]}{\sum \mathbb{1}[\text{OFI}_i \neq 0]}$$

---

## 5. Pre-Market Context

### `pm_high_distance`
$$\text{PM\_High\_Dist} = \frac{P_{\text{Open}} - P_{\text{PM\_High}}}{P_{\text{PM\_High}}}$$
- **Window:** PRE regime (04:00 – 09:29 ET)

### `pm_high_price`
- **Window:** PRE regime
- **Target:** Highest traded price during pre-market (split-adjusted).

### `pm_volume_ratio`
$$\text{PM\_Vol\_Ratio} = \frac{V_{\text{FLIP, 1min\_avg}}}{V_{\text{PRE, 1min\_avg}}}$$

### `pm_trade_count`
- **Window:** PRE regime
- **Target:** Total pre-market trades.

---

## 6. Halt Context *(v2 new section)*

### Halt Detection
Halts are detected as gaps $\Delta t > 300\text{s}$ (5 minutes) between
consecutive trades during RTH (09:30–16:00 ET). This captures genuine LULD
trading halts without false-flagging normal mid-day lulls.

**Note:** The Hawkes kernel uses a separate, lower freeze threshold (5s) to
prevent any meaningful gap from causing phantom decay.

### `is_post_halt`
- **Type:** Binary (0 or 1)
- **Target:** Whether this event experienced any genuine LULD halt during RTH.

### `n_halts`
- **Type:** Integer count
- **Target:** Number of halt events detected. Multiple halts indicate highly
  volatile names that triggered LULD bands repeatedly.

### `max_halt_duration_sec`
- **Type:** Float (seconds)
- **Target:** Duration of the longest single halt. Typical LULD halts are
  5-10 minutes (300-600s). Extremely long values (>3600s) may indicate
  thinly-traded names with natural gaps rather than genuine halts.

### `total_halt_duration_sec`
- **Type:** Float (seconds)
- **Target:** Total time spent in halts across the session.

### `seconds_since_unhalt`
- **Type:** Float (seconds) or NaN
- **Target:** Time elapsed from the last pre-FLIP halt resumption to the
  first FLIP trade. NaN if no pre-FLIP halts occurred.

---

## Feature Matrix v2 Schema

| Column | Type | Window | New? |
|---|---|---|---|
| `ticker` | str | — | |
| `date` | str | — | |
| `gap_pct` | float | — | |
| `gap_rank` | int | — | |
| `norm_factor` | float | — | |
| `log_norm_factor` | float | — | |
| `hawkes_intensity_flip_mean` | float | FLIP | |
| `hawkes_intensity_flip_max` | float | FLIP | |
| `hawkes_accel_flip_mean` | float | FLIP | |
| `hawkes_accel_flip_max` | float | FLIP | |
| `hawkes_pre_mean` | float | PRE | ★ |
| `hawkes_pre_max` | float | PRE | ★ |
| `hawkes_rth_mean` | float | RTH | ★ |
| `hawkes_rth_max` | float | RTH | ★ |
| `hawkes_fullday_mean` | float | 04:00–16:00 | ★ |
| `hawkes_fullday_max` | float | 04:00–16:00 | ★ |
| `hawkes_post_halt_surge` | float | 60s post-halt | ★ |
| `cvd_flip_final` | float | FLIP | |
| `cvd_fullday_final` | float | 04:00–16:00 | ★ |
| `cvd_convexity_flip_mean` | float | FLIP | |
| `cvd_convexity_flip_max` | float | FLIP | |
| `cvd_convexity_flip_sign_ratio` | float | FLIP | |
| `cvd_convexity_transition_mean` | float | 09:25–09:35 | ★ |
| `cvd_convexity_transition_max` | float | 09:25–09:35 | ★ |
| `ofi_flip_mean` | float | FLIP | |
| `ofi_flip_cumulative` | float | FLIP | |
| `ofi_flip_max` | float | FLIP | |
| `ofi_flip_imbalance_ratio` | float | FLIP | |
| `pm_high_distance` | float | PRE | |
| `pm_high_price` | float | PRE | |
| `pm_volume_ratio` | float | PRE→FLIP | |
| `pm_trade_count` | int | PRE | |
| `is_post_halt` | int | RTH | ★ |
| `n_halts` | int | RTH | ★ |
| `max_halt_duration_sec` | float | RTH | ★ |
| `total_halt_duration_sec` | float | RTH | ★ |
| `seconds_since_unhalt` | float | Pre-FLIP | ★ |

**Total: 37 columns** (22 from v1 + 15 new)

## Related

- [[Phase 2 — Signal Forge]] — parent phase summary doc
- [[SIGNAL_DICTIONARY]] — v1 feature definitions
- [[00-Index]] — vault index
