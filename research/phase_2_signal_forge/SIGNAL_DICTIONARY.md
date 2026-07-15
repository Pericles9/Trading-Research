---
tags:
  - type/pipeline
  - domain/signal
  - project/src-core
  - status/complete
created: 2026-04-04
---

# Signal Dictionary — Phase 2 Signal Forge

All features are computed per event (ticker, date) and aggregated into
per-regime summary statistics for the feature matrix.

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

## 2. Hawkes Intensity

### Mathematical Foundation
The Hawkes self-exciting point process models trade arrival clustering.
Given trade timestamps $\{t_1, t_2, \ldots, t_n\}$:

$$\lambda(t) = \mu + \alpha \sum_{t_j < t} e^{-\beta(t - t_j)}$$

where:
- $\mu$: baseline intensity (trades/sec)
- $\alpha$: excitation amplitude
- $\beta$: decay rate ($1/\beta$ = memory timescale)

**GPU Implementation:** Associative scan with exponential kernel.
Define $\Delta t_i = t_i - t_{i-1}$ and the running sum:
$$S_i = e^{-\beta \Delta t_i} \cdot S_{i-1} + 1, \quad S_0 = 0$$
$$\lambda(t_i) = \mu + \alpha \cdot S_i$$

Parameters: $\alpha = 0.8$, $\beta = 1.0$ (1-second decay), $\mu$ estimated
as mean event rate over the window.

### `hawkes_intensity_flip_mean`
- **Window:** FLIP regime (09:30:00 – 09:44:59 ET)
- **Aggregation:** Mean of $\lambda(t_i)$ over all trades in FLIP
- **Target:** Measures average trade clustering at the open shock.
  Higher values indicate more self-exciting behavior.

### `hawkes_intensity_flip_max`
- **Window:** FLIP regime
- **Aggregation:** Max of $\lambda(t_i)$
- **Target:** Peak trade intensity during the volatility shock.

### `hawkes_accel_flip_mean`
$$\Delta\lambda(t_i) = \lambda(t_i) - \lambda(t_{i-1})$$
- **Window:** FLIP regime
- **Aggregation:** Mean of $\Delta\lambda$
- **Target:** Average acceleration of trade arrivals. Positive = intensifying.

### `hawkes_accel_flip_max`
- **Window:** FLIP regime
- **Aggregation:** Max of $\Delta\lambda$
- **Target:** Maximum single-step intensity spike.

---

## 3. Cumulative Volume Delta (CVD) & Convexity

### Trade Classification (Tick Rule)
Each trade is classified as buy/sell using the tick rule:
$$\text{sign}_i = \begin{cases} +1 & \text{if } P_i > P_{i-1} \text{ (uptick)} \\ -1 & \text{if } P_i < P_{i-1} \text{ (downtick)} \\ \text{sign}_{i-1} & \text{if } P_i = P_{i-1} \text{ (zero-tick)} \end{cases}$$

### CVD
$$\text{CVD}(t) = \sum_{i: t_i \leq t} \text{sign}_i \cdot V_i$$
where $V_i$ is trade volume (shares).

### CVD Convexity (2nd Derivative)
Over a sliding 30-second window centered at time $t$:
$$\text{CVD}''(t) = \frac{\text{CVD}(t + \delta) - 2\cdot\text{CVD}(t) + \text{CVD}(t - \delta)}{\delta^2}$$
where $\delta = 15$ seconds. In practice, computed via Savitzky-Golay 2nd
derivative on CVD resampled to 1-second bins.

### `cvd_flip_final`
- **Window:** End of FLIP regime
- **Aggregation:** Final CVD value at 09:45:00
- **Target:** Net directional volume during the shock. Positive = net buying.

### `cvd_convexity_flip_mean`
- **Window:** FLIP regime, 30-second sliding window
- **Aggregation:** Mean of CVD''
- **Target:** Measures "parabolic buying" — sustained positive convexity
  indicates accelerating accumulation.

### `cvd_convexity_flip_max`
- **Window:** FLIP regime
- **Aggregation:** Max of CVD''
- **Target:** Peak parabolic buying signal.

### `cvd_convexity_flip_sign_ratio`
$$\text{ratio} = \frac{\sum \mathbb{1}[\text{CVD}''(t) > 0]}{N_{\text{bins}}}$$
- **Window:** FLIP regime
- **Target:** Fraction of time with positive convexity. Values > 0.7 indicate
  persistent parabolic buying.

---

## 4. Order Flow Imbalance (OFI)

### Mathematical Foundation
Using top-of-book quote updates, OFI captures the pressure differential:

$$\text{OFI}_i = \Delta B_i^{\text{size}} \cdot \mathbb{1}[B_i^{\text{price}} \geq B_{i-1}^{\text{price}}]
              - \Delta A_i^{\text{size}} \cdot \mathbb{1}[A_i^{\text{price}} \leq A_{i-1}^{\text{price}}]$$

where:
- $B^{\text{price}}, B^{\text{size}}$: best bid price and size
- $A^{\text{price}}, A^{\text{size}}$: best ask price and size
- $\Delta B_i^{\text{size}} = B_i^{\text{size}} - B_{i-1}^{\text{size}}$

### `ofi_flip_mean`
- **Window:** FLIP regime
- **Aggregation:** Mean OFI per quote update
- **Target:** Average directional order pressure. Positive = bid-side dominance.

### `ofi_flip_cumulative`
- **Window:** FLIP regime
- **Aggregation:** Cumulative sum of OFI over the window
- **Target:** Total order flow imbalance. Large positive values indicate
  persistent buyer aggression at the top of book.

### `ofi_flip_max`
- **Window:** FLIP regime
- **Aggregation:** Max single OFI reading
- **Target:** Peak order flow shock.

### `ofi_flip_imbalance_ratio`
$$\frac{\sum \mathbb{1}[\text{OFI}_i > 0]}{\sum \mathbb{1}[\text{OFI}_i \neq 0]}$$
- **Window:** FLIP regime
- **Target:** Fraction of non-zero OFI readings that are buyer-dominated.

---

## 5. Pre-Market Context

### `pm_high_distance`
$$\text{PM\_High\_Dist} = \frac{P_{\text{Open}} - P_{\text{PM\_High}}}{P_{\text{PM\_High}}}$$
- **Window:** PRE regime (04:00 – 09:29 ET)
- **Target:** % distance from the market open to the pre-market high.
  Negative = opened below PM high (common for momentum names that fade).
  Positive = gapped above PM high (very bullish).

### `pm_high_price`
- **Window:** PRE regime
- **Target:** The highest traded price during pre-market (split-adjusted).

### `pm_volume_ratio`
$$\text{PM\_Vol\_Ratio} = \frac{V_{\text{FLIP, 1min\_avg}}}{V_{\text{PRE, 1min\_avg}}}$$
- **Window:** PRE → FLIP crossover
- **Target:** How much volume explodes at the open vs pre-market baseline.
  Higher ratios indicate stronger open participation vs pre-market.

### `pm_trade_count`
- **Window:** PRE regime
- **Target:** Total number of pre-market trades. Proxy for pre-market interest.
  Zero means no pre-market activity.

---

## Feature Matrix Schema

| Column | Type | Description |
|---|---|---|
| `ticker` | str | Ticker symbol |
| `date` | str | Event date (YYYY-MM-DD) |
| `gap_pct` | float | Gap at open (from Phase 1) |
| `gap_rank` | int | Dense rank by gap_pct per date |
| `norm_factor` | float | $\phi$ |
| `log_norm_factor` | float | $\log_{10}(\phi)$ |
| `hawkes_intensity_flip_mean` | float | Mean Hawkes $\lambda$ in FLIP |
| `hawkes_intensity_flip_max` | float | Max Hawkes $\lambda$ in FLIP |
| `hawkes_accel_flip_mean` | float | Mean $\Delta\lambda$ in FLIP |
| `hawkes_accel_flip_max` | float | Max $\Delta\lambda$ in FLIP |
| `cvd_flip_final` | float | Final CVD at end of FLIP |
| `cvd_convexity_flip_mean` | float | Mean CVD'' in FLIP |
| `cvd_convexity_flip_max` | float | Max CVD'' in FLIP |
| `cvd_convexity_flip_sign_ratio` | float | Fraction CVD'' > 0 in FLIP |
| `ofi_flip_mean` | float | Mean OFI in FLIP |
| `ofi_flip_cumulative` | float | Cumulative OFI in FLIP |
| `ofi_flip_max` | float | Max OFI in FLIP |
| `ofi_flip_imbalance_ratio` | float | Fraction positive OFI in FLIP |
| `pm_high_distance` | float | Open vs PM high distance |
| `pm_high_price` | float | Pre-market high (adjusted) |
| `pm_volume_ratio` | float | FLIP vol / PM vol ratio |
| `pm_trade_count` | int | Pre-market trade count |

## Related

- [[Phase 2 — Signal Forge]] — parent phase summary doc
- [[SIGNAL_DICTIONARY_v2]] — extended v2 feature definitions
- [[00-Index]] — vault index
