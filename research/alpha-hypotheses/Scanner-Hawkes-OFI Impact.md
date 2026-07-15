<!-- fullWidth: false tocVisible: true tableWrap: true -->
---
status: ACTIVE
created: 2026-02-28
updated: 2026-03-19
session_hours: 04:00–20:00 ET (extended hours — pre-market through post-market)
tags:
  - type/strategy
  - domain/hawkes
  - domain/ofi
  - domain/price-impact
  - domain/signal
  - project/hawkes-ofi-impact
  - status/approved
---

# Alpha Hypothesis — Scanner × Hawkes × OFI Price Impact

> **Edge:** Small retail trader with high risk tolerance, low capital, and agility in volatile / low-liquidity stocks gapping >50% on strong catalysts. Institutional players cannot size into these names; the edge is timing the burst of aggressive order flow and riding permanent price impact before it dissipates.

---

## Hypothesis

When a stock qualifies as a tradeable setup (see [[Tradeable Setup Filter]]) **and** the Hawkes engine detects the *onset* of a genuine burst (rising excitation, not just an elevated busy period) **and** trade-based OFI confirms directional imbalance with quote-level signals corroborating the move, the predicted permanent price impact will exceed transaction costs over a short forward horizon. Enter on each qualifying gate fire. Exit on the earliest of three defined signals. Re-enter if gates fire again while the event remains active — no limit on trades per event, no pyramiding (flat between trades).

> **Session definition:** All signal computation, warm-up, λ_ref calibration, and extended-hours data ingestion covers the full **4:00 AM – 8:00 PM ET** window. This includes pre-market and post-market. Normal-hours assumptions (9:30–16:00) do not apply anywhere in this system.

**Architectural principle — each layer has a distinct role:**

| Layer | Signal | Role |
|-------|--------|------|
| Setup filter | See [[Tradeable Setup Filter]] | Universe filter — does this stock meet the conditions we want to trade? |
| Hawkes | $\dot{E}(t)$ — excitation rate of change | Burst onset detector — is flow accelerating right now? |
| OFI (trade) | Lee-Ready signed volume | Directional ground truth — which way is the aggressive flow? |
| OFI (quote) | Microprice + quote imbalance | Real-time leading confirmation — is the book supporting the move? |
| Impact bridge | $\Delta mid_{perm}$ | Cost filter — does predicted impact clear spread + slippage? |

Hawkes detects clustering. OFI measures direction. Quote signals confirm in real time before trades settle. Conflating any of these produces either double-counting or gaps in coverage.

---

## Three Required Conditions (AND Gate)

1. **Setup filter** — stock passes the tradeable setup conditions defined in [[Tradeable Setup Filter]]
2. **Hawkes burst onset** — $\dot{E}(t) > \theta_{slope}$ AND $E(t) > E_{min}$ (rising excitation above a floor, not just elevated)
3. **Burst magnitude gate** — $|\Delta mid_{5s}| > K \cdot \text{spread}$ AND $\text{dollar\_vol} > V_{min}$, with quote imbalance and microprice confirming direction

> **Sample size warning:** Run marginal gate pass rates on the historical universe before writing any backtest code (Phase 0). If the triple-AND passes fewer than 150 events, convert to the scoring gate (see [[#Scoring Gate Fallback]]). If fewer than 75, stop and investigate the universe filter before proceeding. This is a blocking step.

---

## Mathematical Specification

### Layer 1 — Bivariate Hawkes Intensity (Clock-Time, Adaptive β)

$$\lambda_m(t) = \mu_m + \sum_{k=1}^{K} \alpha_{m,self}^{(k)} R_{m}^{(k)}(t) + \sum_{k=1}^{K} \alpha_{m,cross}^{(k)} R_{\bar{m}}^{(k)}(t)$$

**Clock-time kernel:**

$$R^{(k)}(t) = 1 + e^{-\beta_k^{eff}(t) \cdot dt} \cdot R^{(k)}(t^-)$$

Clock-time semantics are preserved throughout. β adapts to the current arrival rate so the kernel does not degenerate at high TPS.

**Adaptive β:**

$$\beta_k^{eff}(t) = \beta_k^{base} \cdot \frac{\hat{\lambda}(t)}{\lambda_{ref}}$$

where $\hat{\lambda}(t)$ is a Kalman-filtered estimate of the current arrival intensity (see [[#Kalman Intensity Estimator]]), $\lambda_{ref}$ is the per-symbol per-session baseline arrival rate, and $\beta_k^{base}$ is the nominal value at reference rate.

**Why β scales up at high TPS:** Hawkes detects temporal clustering — whether trades arrive sooner than the baseline predicts. At 500 TPS with fixed β, each `dt` is tiny, `exp(-β·dt) ≈ 1`, and R accumulates unconditionally. Scaling β proportionally keeps the effective decay window constant in seconds so the kernel continues asking "did this trade cause the next one to arrive sooner?" rather than just counting arrivals.

**Excitation ratio:**

$$E(t) = \frac{\lambda_{buy}(t) + \lambda_{sell}(t)}{\mu_{buy} + \mu_{sell}}$$

Dimensionless and stationary across regimes. $E(t) = 1$ means current activity is indistinguishable from background. $E(t) \gg 1$ is a genuine burst. Using total intensity in both numerator and denominator keeps $E(t)$ classification-agnostic — a directional burst in buys raises the total intensity ratio correctly without depending on which component fires.

> **Implementation note:** All downstream uses of $E(t)$ — the Ė gate, regime state machine, EXIT 2 subcritical threshold, and EXIT 3 — use this total intensity definition throughout. The bivariate intensities $\lambda_{buy}(t)$ and $\lambda_{sell}(t)$ are still tracked separately for OFI directional confirmation; they are summed only for the excitation ratio.

**Gate condition — burst onset, not burst level:**

$$\dot{E}(t) > \theta_{slope} \quad \text{AND} \quad E(t) > E_{min}$$

A genuine burst has a rapidly rising $E(t)$. A busy session period has a high but flat $E(t)$. Requiring the slope catches the onset of a burst and rejects the sustained elevated activity that produced false signals in prior testing. Both conditions are required.

Calibrate $\theta_{slope}$ and $E_{min}$ from the historical event catalog — compute the distribution of $\dot{E}(t)$ and $E(t)$ at labeled burst onsets vs. busy-period noise, then set thresholds at percentiles that give acceptable precision/recall tradeoff.

#### Ė(t) Computation — Concrete Specification

E(t) is piecewise constant between events — it jumps at each arrival and is flat between them. A raw finite difference $\Delta E / \Delta t$ between consecutive events has variance proportional to $1/\Delta t^2$, which blows up during high-TPS bursts (Δt ≈ 2ms at 500 TPS) right when the signal is most needed.

**Use a running EMA of per-event ΔE/Δt values:**

$$\dot{E}_{ema}(t_i) = \rho_E \cdot \dot{E}_{ema}(t_{i-1}) + (1 - \rho_E) \cdot \frac{E(t_i) - E(t_{i-1})}{\min(t_i - t_{i-1},\; 1.0)}$$

The denominator is capped at 1.0 second to prevent a single slow inter-arrival from producing a near-zero slope estimate. $\rho_E$ is calibrated to give approximately a 500ms effective window at λ_ref (at 100 TPS: $\rho_E \approx 0.98$). At 500 TPS during a burst, this naturally shortens to ~100ms.

**Edge cases:**
- Freeze $\dot{E}_{ema}$ during LULD halt windows along with R and λ̂.
- Before the 30-event warm-up threshold, do not expose $\dot{E}_{ema}$ as a gate-eligible signal.

> **Module to build:** `core/hawkes/engine.py` — `update_edot()` is a required method on the engine. See project directory.

**Beta — free scalar in MLE:**

K=1 is the production architecture, selected based on Phase A iteration 2 empirical evidence: with K=7, only kernel 0 (beta=100, ~7ms half-life) carried meaningful weight; kernels 1–5 were at the optimizer's lower bound (1e-8). The multi-kernel architecture collapsed to K≈1 regardless of starting point, making the fixed beta bank an unjustified prior on decay timescale.

Beta is now a fitted parameter in the MLE with bounds (1.0, 10000.0). The parameter vector is:

`[alpha_self_buy, alpha_cross_buy, alpha_self_sell, alpha_cross_sell, mu_buy, mu_sell, beta]`

Seven parameters total. Bounds: alpha (1e-8, beta_max), mu (1e-6, 1000), beta (1.0, 10000.0). Alpha upper bound scales with beta_max since n_base = alpha/beta ≈ 0.55.

At runtime, the adaptive scaling still applies on top of the MLE-fitted beta:

`beta_eff = beta_mle * (lambda_hat / lambda_ref)`

These are not in conflict — MLE finds the base value, the adaptive mechanism handles rate variation within a session. At 5× λ_ref, beta_eff = 5 × beta_mle, preserving time windows in seconds.

> **Kernel count resolution (Phase A iteration 2):** K=1 selected based on empirical kernel collapse. The original plan to test K=3/4/5/7 was executed in iteration 1, but those results were invalidated by the self-inclusion bug. Iteration 2 showed definitive single-kernel dominance even with corrected code. K=1 with free beta is simpler, has fewer parameters (7 vs 30), and lets the data choose the decay timescale.

---

#### Kalman Intensity Estimator

The arrival intensity $\hat{\lambda}(t)$ is estimated using a 1D EKF rather than a simple EMA. The EMA has a cold-start problem — the initial value is arbitrary until roughly $1/(1-\rho)$ events have been observed. In pre-market trading that window may span the most important part of the event. The EKF addresses this by initializing with an informative prior ($\lambda_{ref}$) and high initial uncertainty, converging rapidly from the first event.

> **Implementation note — EKF approximation:** A standard linear Kalman filter is not theoretically optimal here. Poisson intensity is bounded below at zero, the observation $y_t = 1/\Delta t_i$ is a nonlinear function of the state, and the observation noise variance depends on the state itself. This formulation is an **Extended Kalman Filter (EKF)** approximation. Theoretical optimality would require the **Snyder filter** (see [[#Snyder Filter Evaluation]]). The EKF approximation is validated empirically in Phase A.

**State and observation model:**

$$\lambda_t = \lambda_{t-1} + w_t, \quad w_t \sim \mathcal{N}(0, Q)$$
$$y_t = \frac{1}{\Delta t_i} + v_t, \quad v_t \sim \mathcal{N}(0,\; R(\lambda_{t-1}))$$

where $y_t = 1/\Delta t_i$ is the instantaneous rate estimate and $R(\lambda) = \max(\hat{\lambda},\; c_R \cdot \lambda_{ref})^2$ with $c_R = 0.1$.

**Initialization:**
$$\hat{\lambda}_0 = \lambda_{ref}, \quad P_0 = (3 \cdot \lambda_{ref})^2$$

**Update step (per event):**

$$P_{pred} = P + Q$$
$$K = \frac{P_{pred}}{P_{pred} + \max(\hat{\lambda},\; c_R \cdot \lambda_{ref})^2}$$
$$\hat{\lambda} \leftarrow \hat{\lambda} + K \cdot (y_t - \hat{\lambda})$$
$$P \leftarrow (1 - K) \cdot P_{pred}$$

**Process noise calibration:** $Q = (Q_{scale} \cdot \lambda_{ref})^2$ where $Q_{scale} \approx 0.01$ is a starting point. Calibrate from the burst catalog by minimizing out-of-sample prediction error on held-out burst trajectories.

**LULD halt handling:** Freeze the Kalman state during halt windows. On halt resume, inflate uncertainty:

$$P \leftarrow P + Q \cdot t_{halt} \cdot \lambda_{ref}$$

where $t_{halt}$ is halt duration in seconds.

> **Why log-state:** The naive formulation clips `lambda_hat` at zero after each update. Clipping violates the Gaussian state assumption — the covariance $P$ remains calibrated for a full Gaussian, making the filter overconfident in near-zero intensity. The log-state formulation eliminates this: state $x = \log\lambda$ is unbounded and Gaussian; $\lambda = e^x$ is always positive by construction. EKF linearisation (Jacobian $H = e^x = \hat\lambda$) is the standard first-order approximation.

> **Module to build:** `core/hawkes/ekf.py` — `KalmanIntensityEstimator` (log-state EKF). Needs `update(dt)`, `on_halt_resume(halt_duration_sec)`, and a `lambda_hat` property. See project directory.

---

#### Snyder Filter Evaluation

The theoretically optimal filter for Poisson point process intensity is the **Snyder filter**, which solves the filtering equations exactly. It is computationally more expensive and requires an ODE solve between each event arrival.

**Phase A evaluation — EKF vs. Snyder head-to-head:**

1. **Tracking accuracy:** Compare λ̂(t) from each against a ground-truth rolling rate estimate on 20+ labeled burst events. Report mean absolute error and peak-tracking lag.
2. **Computational cost:** Wall-clock time per event update on production hardware. Target: < 0.5ms per event.
3. **Parameter stability:** Compare α and μ estimates from MLE when each filter's λ̂(t) is used for adaptive β scaling.

**Decision rule:** Use Snyder if tracking MAE is more than 15% lower than EKF **and** per-event compute time < 0.5ms. Otherwise lock EKF and document the benchmark result. This is a binary decision with a hard cutoff.

> **Module to build:** `core/hawkes/ekf.py` — include both `KalmanIntensityEstimator` (EKF) and `SnyderFilter`. Benchmark both in Phase A.

---

#### Online Refitting Architecture

The fundamental problem with a one-time offline calibration is that these events are non-stationary and each stock has a different microstructure character. A single parameter set cannot capture both a liquid pre-market gapper and an ultra-thin post-market mover. The engine needs to track the current state of each stock during its session.

The architecture has two layers running simultaneously:

**Hot path — per event, every trade (microseconds):** Snyder filter updates lambda_hat. Kernel R values decay and increment. E(t) recomputes. Regime state machine checks for transitions. Uses the current best parameter estimate. MLE has no presence here.

**Warm path — every 50–100 events, background thread (sub-second):** Forgetting MLE refits on the rolling event buffer using the current rho. When the optimizer converges, the parameter set is swapped atomically via `swap_params()`. The hot path keeps running with the previous params while the refit is in flight. The hot path must never block waiting for the warm path.

**Refit trigger:** Every `refit_interval_events` events (default: 50), the accumulated event buffer is passed to `fit_online()`. This function uses the previous parameter solution as one of the optimizer starting points (warm start), which dramatically improves convergence speed compared to cold-start MLE.

**Atomic parameter swap:** When the warm path optimizer converges, all 7 parameters (4 alpha, 2 mu, 1 beta) are swapped atomically using a threading lock. The hot path never reads a partially-updated state.

**Rho as staleness control:** In the online refitting context, rho controls how fast old data is discarded from the rolling buffer's weighted likelihood. Lower rho values cause the first 200 trades of a new stock to dominate the fit more quickly; higher rho values retain more history. The optimal rho may differ from the offline sweep value (0.9999). A secondary rho validation under the online framing is required in Phase A iteration 4.

> **Module to build:** `core/hawkes/engine.py` — `swap_params()` method with threading lock for atomic updates. `core/hawkes/forgetting.py` — `fit_online()` entry point with warm start from previous solution.

---

#### Branching Ratio and Regime State Machine

**Branching ratio — exact spectral radius of the 2×2 branching matrix:**

With K=1, the branching matrix simplifies to:

$$\mathbf{M} = \frac{1}{\beta} \begin{pmatrix} \alpha_{buy,self} & \alpha_{buy,cross} \\ \alpha_{sell,cross} & \alpha_{sell,self} \end{pmatrix}$$

$$n_{base} = \rho(\mathbf{M}) = \frac{(M_{11} + M_{22}) + \sqrt{(M_{11} - M_{22})^2 + 4\, M_{12} M_{21}}}{2}$$

The $n_{eff}(t)$ diagnostic uses the same structure with $\beta_k^{eff}(t)$ replacing $\beta_k^{base}$.

> **Why spectral radius, not average row sum:** Average row sum equals spectral radius only when the matrix is symmetric — i.e., when buy and sell excitation are identical. In directional bursts, $\alpha_{buy,self} \gg \alpha_{sell,self}$ is expected. Average row sum underestimates the true spectral radius in that regime, causing the SUPERCRITICAL gate to lag precisely during highest-conviction events. The exact formula costs one square root and is always correct.

> **Use $n_{base}$ for the SUPERCRITICAL detection gate.** Track $n_{eff}(t)$ for diagnostics only.

> **Module to build:** `core/hawkes/engine.py` — `branching_ratio_base()` and `branching_ratio_eff()` methods using the exact 2×2 spectral radius formula. See project directory.

**Regime state machine:**

| State | Condition | Model Active |
|-------|-----------|--------------|
| BASELINE | $E(t) \leq E_{min}$ | Hawkes fitting; no signal |
| BUILDING | $\dot{E}(t) > \theta_{slope}$ AND $E(t) > E_{min}$ | Hawkes fitting; burst onset gate can fire |
| SUPERCRITICAL | $n_{base} \geq n_{thresh}$ | Hawkes fitting paused; intensity monitor active |
| COLLAPSE | $n_{base} < n_{thresh}$ after SUPERCRITICAL | Post-collapse lockout; ≥50 events before BASELINE → BUILDING can re-fire |

> **Module to build:** `core/hawkes/regime.py` — `RegimeStateMachine`. States as enum. Must expose: `update(E, n_base, lambda_hat)`, `check_hard_stop(time_since_entry)`, `freeze()`, `resume(halt_duration_sec)`. EXIT 4 override runs before all other logic. Post-collapse lockout is ≥50 events. See project directory.

**Forgetting rate calibration — select ρ based on the memory window needed during bursts, not at baseline:**

| ρ | Memory (events) | Memory at λ_ref = 100 TPS | Memory at 5× burst (500 TPS) |
|---|----------------|--------------------------|------------------------------|
| 0.999 | ~1,000 | ~10s | ~2s |
| 0.9995 | ~2,000 | ~20s | ~4s |
| 0.9999 | ~10,000 | ~100s | ~20s |

Calibrate $\rho$ from the historical burst catalog. Plot $n_{base}(t)$ trajectories across 20+ historical bursts at candidate ρ values and select by precision/recall on regime classification.

> **Module to build:** `core/hawkes/forgetting.py` — exponential forgetting MLE. Weights per-event log-likelihood by `rho^(n - i)` (event-count-indexed, not timestamp-indexed). See project directory.

#### Likelihood Approximation with Time-Varying β

The standard Hawkes log-likelihood compensator assumes β is constant. With adaptive β the compensator integral has no closed form. The approximation used here treats β as locally constant within each inter-event interval: use the β_eff computed at event $i$ for the decay from $t_i$ to $t_{i+1}$, then update β_eff at $t_{i+1}$ before computing the next contribution.

**Validation requirement (Phase A) — two windows required:**

*Window 1 — quiet pre-market:* Compare adaptive-β MLE estimates to standard fixed-β MLE estimates on the same data. α and μ estimates should be nearly identical.

*Window 2 — burst windows (10+ labeled burst events):* Run three models on each burst window: (1) adaptive-β MLE (production), (2) fixed-β MLE at β_base, (3) segmented fixed-β MLE (split at λ̂ peak, fit separately on pre-peak and post-peak segments). If adaptive-β α estimates differ from segmented fixed-β by > 30% on average, either cap β_eff at 3× β_base or stop re-fitting MLE during the rapid β-transition phase.

**Halt handling — LULD dead time must not be treated as quiet time:**

During a LULD halt, if the Hawkes engine is running in clock-time mode, a halt gap will cause `exp(-β·dt) ≈ 0` and R collapses, missing the post-halt burst. Use halt detection (see `utils/halt_detection.py` — needs to be built) to identify halt periods from tick gaps. During a halt:

- Freeze $R^{(k)}$, $\hat{\lambda}(t)$ Kalman state, $\mu$ updates, regime state, and $\dot{E}_{ema}$
- On resume, inflate Kalman uncertainty to adapt faster immediately post-halt

**Warm-up requirement:** Do not compute $E(t)$ until ≥ 30 baseline events have been observed since 4:00 AM ET. The EKF runs from event 1. Only the MLE-derived signals (E(t), Ė(t), n(t)) require the 30-event threshold.

---

### Layer 2 — OFI: Trade-Based (Primary) and Quote-Based (Real-Time Confirmation)

OFI is the directional signal. Hawkes is the clustering detector. They answer different questions and must not be conflated.

#### 2a — Trade-Based OFI (Primary Directional Signal)

$$\text{OFI}_{gate}(t) = \text{OFI}(t - 10s,\; t) = \sum_{i:\, t_i \in [t-10s,\; t]} s_i \cdot v_i$$

where $s_i \in \{+1, -1\}$ is trade direction classified by the Lee-Ready rule and $v_i$ is trade size in shares. A fixed **10-second trailing window** is used for the Gate 3 impact bridge input.

> **Window validation (Phase C):** Run the OFI vs. Δmid regression separately with 5s, 10s, 20s, and 30s windows. Use the window maximizing out-of-sample R². The 10s default is the starting point, not an assumption.

**Spread-normalized OFI for cross-symbol comparability:**

$$\text{OFI}_{norm}(t) = \frac{\text{OFI}_{gate}(t)}{\bar{s}(t-10s,\, t) \cdot \bar{Q}(t)}$$

where $\bar{s}(t-10s,\, t)$ is the quote-update-weighted average spread over the same 10-second window and $\bar{Q}(t)$ is the rolling mean trade size computed since 4:00 AM ET.

> **Why time-averaged spread:** OFI_gate accumulates flow at whatever spreads existed over the past 10 seconds. Normalizing by instantaneous spread introduces a scale mismatch — spread can change 50–200% within a burst window. The time-averaged spread over the same window is the correct normalizer.

**Q_bar stability guard:** Require at least 50 trades since 4:00 AM ET before using OFI_norm. Below this threshold, fall back to raw OFI with the per-tier median Q_bar from the training catalog. Winsorize Q_bar at the 95th percentile of historical per-tier values.

**Trade classification — two-step microprice classifier:**

Standard Lee-Ready classifies a trade as ambiguous when price equals the prevailing mid. In wide pre-market spreads, trades can print inside the spread via midpoint executions. Lee-Ready flags these as ambiguous, but many are directionally real. The two-step classifier recovers these events.

Step 1: Standard Lee-Ready vs. mid with session-hour-adjusted ambiguity threshold.
Step 2 (for Step-1 ambiguous prints): Compare price vs. microprice using `0.5 × half-spread` margin. If the trade is above microprice it is a buy; below is a sell; truly neither is AMBIGUOUS and excluded.

> **Module to build:** `core/ofi/trade_ofi.py` — `compute_trade_ofi()` and two-step classifier. Session-hour adjusted threshold loaded from `config/lee_ready_thresholds.json`. See project directory.

**Why microprice works for Step 2:** If the bid is heavy and ask is thin, microprice sits above mid. A trade printing at mid is then below microprice — classified as a sell. A genuine buy in a thin-ask book would have lifted the ask, not printed at mid.

**Session-hour diagnostic:** Report the Step 2 classification rate separately for pre-market, regular hours, and post-market. If Step 2 fires more than 30% of the time during regular hours, the ambiguity threshold is too wide.

**Lee-Ready ambiguity threshold — empirically derived, not assumed:**

1. Compute final ambiguity rates across the full filtered training catalog per symbol, session hour, and spread tier.
2. Set the veto threshold at the 85th percentile of ambiguity rates observed during confirmed burst windows.
3. If pre-market ambiguity is structurally higher than regular hours after the two-step classifier, define a session-hour-adjusted threshold.
4. Store in `config/lee_ready_thresholds.json`.

**Hawkes robustness to residual classification noise:**

*Total intensity parallel stream:* Run a total-intensity λ̂ tracker on the full event stream regardless of classification. If the bivariate n_base fires a regime gate but total intensity shows no clustering signal, the trigger is likely a classification artifact. Use as a veto when the two disagree significantly.

*Phase A classification robustness test:* Run the bivariate Hawkes with three classification variants: (a) two-step microprice (production), (b) standard Lee-Ready only, (c) direction-agnostic. If precision/recall differs < 5% across variants, two-step classifier is sufficient.

**Gate 3 pre-market fallback:** If pre-market OFI_norm predictive R² (measured in Phase C on the validation split) is less than half of regular-hours R², apply a higher OFI_norm threshold for pre-market Gate 3 fires and increase the weight of QI + microprice in the scoring gate.

#### 2b — Quote-Based OFI (Real-Time Leading Confirmation)

Trade-based OFI lags — you wait for a trade, then classify it. The quote provides a forward-leaning view before trades fully settle.

**Microprice (size-weighted mid):**

$$m_w(t) = \frac{P_{ask} \cdot Q_{bid} + P_{bid} \cdot Q_{ask}}{Q_{bid} + Q_{ask}}$$

**Quote imbalance at the touch:**

$$\text{QI}(t) = \frac{Q_{bid} - Q_{ask}}{Q_{bid} + Q_{ask}} \in [-1, 1]$$

**Denoising QI:** Require QI to remain above a threshold for a minimum of 3 consecutive quote updates before it counts as a signal. In a fast market 3 updates may span 20ms; in a slow market 300ms. The filter adapts to market pace naturally.

**How trade and quote OFI are used together:** Trade OFI is the primary Gate 3 input. QI and microprice direction are confirming conditions. If QI is flat or negative while trade OFI is positive, the book is not supporting the move and the signal is weaker.

> **Module to build:** `core/ofi/quote_ofi.py` — `compute_microprice()`, `compute_quote_imbalance()`, `apply_persistence_filter()`. See project directory.

---

### Layer 3 — Burst Magnitude Gate and Persistence Bridge

> **Phase C finding (2026-03-21):** The original OFI-predicted impact model (`beta_tier * |OFI|^gamma * sign(OFI)`) produced R^2 < 0.001 for all spread tiers. Root cause: these are catalyst-driven events (earnings/news gaps) where OFI measures reactive flow after the price adjusts, not causal flow. See design decisions log.

**Gate 3 — Burst magnitude check:**

$$\text{Gate 3 fires when: } |\Delta mid_{5s}| > K_{tier} \cdot s(t) \quad \text{AND} \quad \text{dollar\_vol}(t) > V_{min}$$

where $s(t)$ is the current spread at burst time and $K_{tier}$ is a per-tier multiplier calibrated in Phase C. The activity qualifier $V_{min}$ filters illiquid events where spread width reflects inactivity, not volatility. Both $K_{tier}$ and $V_{min}$ are calibrated from the training catalog to maximize the yield of same-direction continuation events (pass rate x same-direction rate).

> **Why burst magnitude replaced OFI impact:** Phase C calibration on 5,113 events showed OFI has no predictive power for short-term price impact in catalyst-driven momentum events (R^2 < 0.001 across all tiers and OFI windows). The burst magnitude check answers a different question: "has the price already moved enough to confirm this is a real momentum event?" rather than "will the price move enough to cover costs?" The activity qualifier addresses the wide-tier bimodality problem: wide-spread events are a mixture of illiquid-nothing-happening (low activity, 30% amplification) and volatile-everything-happening (high activity, 46% amplification identical to medium tier).

**Spread tier definitions:**

| Tier | Spread as % of price | Typical universe |
|------|---------------------|-----------------|
| Tight | < 0.5% | More liquid gappers |
| Medium | 0.5% – 2% | Main universe |
| Wide | > 2% | Bimodal: illiquid (low activity) vs volatile (high activity) |

**OFI role after reformulation:** Trade OFI retains a directional confirmation role (56-60% sign agreement with delta_mid across tiers, improving to ~75% for high-activity medium events). It is used as a confirming signal in the scoring gate fallback, not as a predictive input for Gate 3.

> **Module to build:** `core/impact/price_impact_bridge.py` — `PriceImpactBridge`. Needs `calibrate()`, `check_gate3()`, `spread_widening_flag()`, and `recalibrate()`. Params persisted to `config/price_impact_bridge_params.json`. See project directory.

---

### Layer 4 — Permanent vs. Transient Impact (Exit Timing Signal)

> **Phase C role change (2026-03-21):** perm_frac was originally an entry-gate input (part of the OFI impact prediction). With Gate 3 reformulated as burst magnitude, perm_frac shifts to an **exit timing signal**: high perm_frac (momentum amplification) → hold longer; perm_frac near 1.0 → tighter exit. The calibration methodology is unchanged.

**Permanent fraction prior (offline, per spread tier):**

*Mid-based (baseline):*

$$\text{perm\_frac}_{tier}^{mid} = \frac{\text{Cov}(\Delta mid_{60s},\; \Delta mid_{5s})}{\text{Var}(\Delta mid_{5s})} \quad \text{per spread tier, clean events only}$$

*VWAP-based (noise-robust alternative):*

$$\text{perm\_frac}_{tier}^{vwap} = \frac{\text{Cov}(\Delta vwap_{60s},\; \Delta vwap_{5s})}{\text{Var}(\Delta vwap_{5s})} \quad \text{per spread tier, clean events only}$$

> **Why OLS slope, not E[ratio]:** When $\Delta mid_{5s}$ is near zero, the ratio blows up and outlier events dominate. The OLS slope $\text{Cov}(Y,X)/\text{Var}(X)$ is robust to near-zero denominators, handles negative impacts correctly, uses all the data, and produces an R² as a quality diagnostic.

**Selection:** Compute the standard deviation of per-event perm_frac under each method per tier. If the VWAP-based estimate has at least 20% lower standard deviation, use VWAP. Document the comparison and selection in `config/price_impact_bridge_params.json`.

**Event cleanliness filter:** Only include events where no secondary burst fires in the [t+5s, t+60s] measurement window. An event is clean if E(t) drops below $E_{min}$ after the primary burst and does not recover before t+60s.

> **Module to build:** `core/impact/price_impact_bridge.py` — `is_clean_event()` as a standalone utility function used by the calibration pipeline. See project directory.

Report the fraction of events filtered by this check. If > 40% of events are multi-burst, estimate perm_frac using an event-study regression with a secondary-burst indicator rather than the simple survival ratio.

**Spread derivative as real-time permanence confirmation:**

$$\text{spread\_widening}(t) = s(t) - s(t - 10s) > 0$$

Monitor in the 5–10s window post-burst. Apply a 50ms persistence filter to quote updates before computing $\dot{s}$.

**Spread derivative multiplier — f(ṡ(t)) specification:**

$$f(\dot{s}(t)) = 0.5 + 0.5 \cdot \sigma\!\left(\frac{\dot{s}(t) - \dot{s}_{med}}{\dot{s}_{scale}}\right)$$

where $\sigma$ is the logistic function, $\dot{s}_{med}$ is the median spread derivative observed during confirmed burst events in the training catalog, and $\dot{s}_{scale}$ is the interquartile range of that distribution. Calibrate $\dot{s}_{med}$ and $\dot{s}_{scale}$ per spread tier in Phase C. If calibration produces unstable estimates (fewer than 50 clean events per tier), fall back to a step function: f = 1.0 if ṡ > 0, f = 0.5 if ṡ ≤ 0. Log which version is active per tier.

**perm_frac as exit timing signal:**

perm_frac > 1.0 indicates momentum amplification (the 60s move exceeds the 5s move). Phase C calibration found perm_frac > 1.0 for all tiers, confirming that these catalyst-driven events tend to continue rather than revert. In the exit stack, perm_frac informs hold duration: higher perm_frac tiers warrant holding closer to the EXIT 4 time limit; perm_frac near 1.0 warrants tighter EXIT 2/3 thresholds. The exact mapping is calibrated in Phase E.

---

### Layer 5 — Tradeable Setup Filter

See [[Tradeable Setup Filter]] for full specification.

**Role in this system:** The setup filter is a universe gate, not a real-time signal. It determines which symbols are eligible for the Hawkes and OFI layers to run on during the 4:00 AM – 8:00 PM ET session.

**Critical role in Layer 3 calibration:** The setup filter must be applied retroactively to the historical event catalog before calibrating the price impact bridge. Including unfiltered events corrupts the $\beta_{tier}$ and perm_frac regressions with data structurally unlike the actual trading universe.

**Volume acceleration for real-time persistence:**

$$\ddot{V}(t) = \text{VolRate}(t,\, 5s) - \text{VolRate}(t - 5s,\, 10s)$$

Positive $\ddot{V}(t)$ means cumulative volume is accelerating. Computable tick-by-tick with sub-second resolution.

> **Module to build:** `core/features/volume_acceleration.py` — `compute_vol_accel()`. Returns NaN (no-signal, not a veto) if fewer than 10 trades in window. See project directory.

---

## Full Signal Stack

```
Tradeable Setup Filter (see [[Tradeable Setup Filter]])
4:00 AM – 8:00 PM ET extended session
          │
          │  Eligible symbols only
          ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                          REAL-TIME ENGINE                                │
│                     (4:00 AM – 8:00 PM ET)                               │
│                                                                          │
│  Hawkes (clock-time, adaptive β, exponential forgetting)                │
│          │                                                               │
│  Regime: BASELINE → BUILDING → SUPERCRITICAL → COLLAPSE                 │
│                                                                          │
│  BASELINE / BUILDING:              Trade OFI          Quote OFI         │
│  E(t) = λ(t)/μ               Σ s_i·v_i (Lee-Ready)    Microprice m_w   │
│  Ė(t) = EMA[ΔE/Δt]          OFI_gate = 10s window     QI(t)            │
│  n_base = spectral radius     OFI_norm = OFI/(s·Q̄)    (3-update        │
│  Gate: Ė > θ_slope            Q̄ guard: ≥50 trades       persistence)   │
│         AND E > E_min                                      │            │
│                                                            │            │
│  SUPERCRITICAL (n_base ≥ n_thresh):  └──────┬─────────────┘            │
│  Hawkes fitting paused                      │                           │
│  EKF λ̂(t) monitored vs. entry peak         │                           │
│  Exit when λ̂(t) < p_collapse × peak        │                           │
│  EXIT 4 (90s) overrides unconditionally     │                           │
│  Halt >30s during position → exit at lift   │                           │
│          │                                  │                           │
│          │                      Burst Magnitude Gate                    │
│          │                      |Δmid_5s| > K_tier × spread            │
│          │                      AND dollar_vol > V_min                 │
│          │                      perm_frac_tier → exit timing           │
│          │                      OFI sign → direction confirmation      │
│          │                                  │                           │
│          └──────────────────┬───────────────┘                           │
│                             │                                           │
│             Volume Acceleration ──► still-in-play confirmation         │
│                             │                                           │
│          ┌──────────────────────────────────────────────────────┐       │
│          │  1. Setup filter passed (see [[Tradeable Setup Filter]])│     │
│          │  2. Ė(t) > θ_slope AND E(t) > E_min                  │       │
│          │  3. |Δmid_5s| > K_tier × spread AND dollar_vol > V_min│      │
│          │  [opt] QI persistent positive AND microprice rising  │       │
│          │  [opt] vol_acceleration > 0                          │       │
│          └─────────────────────┬────────────────────────────────┘       │
│                                │                                        │
└────────────────────────────────┼────────────────────────────────────────┘
                                 │
                      Entry (repeatable)
                                 │
                  Position held until first of:
                  EXIT 1 (PRIMARY): mid drops X bps from entry — hard stop
                  EXIT 2: regime-aware intensity exit (see Exit Logic)
                  EXIT 3: vol_accel < 0 AND E(t) < p_exit3 × E_peak_since_entry
                  EXIT 4 (HARD): 90s max hold — checked first, unconditional
```

---

## Exit Logic

Exits are ordered by priority. EXIT 4 is evaluated first, unconditionally, before any other exit logic runs.

**EXIT 4 — Hard time stop (90s, checked first):** Force exit if 90 seconds have elapsed since entry. Unconditional; overrides all other exit logic including SUPERCRITICAL intensity monitoring.

**EXIT 1 — Price-based hard stop (PRIMARY, sub-second):** If mid drops $X$ bps from entry, exit immediately. $X$ is calibrated from the slippage model's adverse fill distribution — in the 50–75 bps range for names with 1–3% spreads. Do not rely on a Hawkes-derived signal as the primary stop; Hawkes updates per event and can lag price by several hundred milliseconds.

**EXIT 2 — Regime-aware intensity exit (seconds):**

- **Entered in BUILDING (subcritical):** Exit when $E(t)$ decays below a fade threshold.

  *Stage 1 (burst catalog, no trade outcomes):* From all labeled burst events in the training catalog, compute the E(t) trajectory from burst onset through decay. Identify the "burst exhaustion" point as the first time E(t) drops below $E_{min}$ and does not recover within 30s. Fit the distribution of E(t) at exhaustion points. Set the subcritical exit threshold at the 25th percentile.

  *Stage 2 (validation split, trade outcomes):* Verify that trades hitting the EXIT 2 threshold show mean forward return < 0 in the 10–30s after exit. Adjust through burst dynamics, not by fitting to realized PnL.

- **Entered in or transitioned to SUPERCRITICAL:** Exit when $\hat{\lambda}(t)$ drops below $p_{collapse}$% of its peak value since SUPERCRITICAL entry. Hawkes fitting is paused; this exit requires no valid model fit.

**EXIT 3 — Volume acceleration reversal (seconds):**

$$\text{EXIT 3: } \ddot{V}(t) < 0 \quad \text{AND} \quad E(t) < p_{exit3} \cdot E_{peak,entry}(t)$$

where $E_{peak,entry}(t)$ is the **maximum E observed since entry** (not the session peak). $p_{exit3} \in [0.5, 0.8]$ is calibrated in Phase E. Do not use the session peak — E(t) is below session peak for ~95% of any hold duration, making that condition trivially satisfied.

---

## Scoring Gate Fallback

If Phase 0 shows 75–149 triple-AND fires in the historical universe, convert to a continuous scoring system.

| Condition | Weight |
|-----------|--------|
| $\dot{E}(t) > \theta_{slope}$ | 0.40 |
| $E(t) > E_{min}$ | 0.20 |
| Burst magnitude gate (Gate 3): magnitude + activity qualifier | 0.25 |
| QI persistent positive AND microprice rising | 0.10 |
| $\ddot{V}(t) > 0$ | 0.05 |

Entry fires when score $\geq 0.65$. The burst magnitude gate (weight 0.25) is a hard veto regardless of score.

**Gate architecture decision rules:**

| Phase 0 triple-AND count | Architecture |
|--------------------------|-------------|
| ≥ 150 | AND gate |
| 75 – 149 | Scoring gate |
| < 75 | Stop — investigate universe filter or catalog before proceeding |

---

## Data Requirements

- **Source tables:** `filtered/{TICKER}_{DATE}_{MOM}/trades.parquet` and `filtered/{TICKER}_{DATE}_{MOM}/quotes.parquet`. All signals are derived exclusively from these two files.
- **Bars for setup filter:** Reconstructed from `trades.parquet` tick data by binning into 1-minute OHLCV bars. Dollar volume computed per bar as `sum(price × size)` over all trades in the bin.
- **Symbols:** All events in the catalog passing [[Tradeable Setup Filter]] conditions
- **Date range:** 2020-01-01 → present
- **Session hours:** 4:00 AM – 8:00 PM ET

### Features Required — All Need to Be Built

| Feature | Source | Module |
|---------|--------|--------|
| `setup_filter_mask` | 1m bars from trades.parquet | `core/filters/setup_filter.py` |
| `ofi_gate` | trades.parquet | `core/ofi/trade_ofi.py` |
| `ofi_norm` | trades.parquet + quotes.parquet | `core/ofi/trade_ofi.py` |
| `lambda_hat` | EKF estimator | `core/hawkes/ekf.py` |
| `lambda_hat_total` | EKF (total stream) | `core/hawkes/ekf.py` |
| `perm_frac_by_tier` | trades.parquet + quotes.parquet | `core/impact/price_impact_bridge.py` |
| `spread_derivative_multiplier` | quotes.parquet | `core/impact/price_impact_bridge.py` |
| `exit2_subcritical_threshold` | Hawkes output (Phase C) | `calibration/phase_c_impact.py` |
| `lee_ready_step2_rate` | trades.parquet | `core/ofi/trade_ofi.py` |
| `quote_imbalance_qi` | quotes.parquet | `core/ofi/quote_ofi.py` |
| `microprice` | quotes.parquet | `core/ofi/quote_ofi.py` |
| `volume_acceleration` | trades.parquet | `core/features/volume_acceleration.py` |
| `excitation_ratio_E` | Hawkes output | `core/hawkes/engine.py` |
| `excitation_slope_Edot` | Hawkes output | `core/hawkes/engine.py` |
| `branching_ratio_n_base` | Hawkes output | `core/hawkes/engine.py` |
| `branching_ratio_n_eff` | Hawkes output | `core/hawkes/engine.py` |
| `regime_state` | Hawkes output | `core/hawkes/regime.py` |
| `lambda_hat_peak_entry` | Hawkes output | `core/hawkes/regime.py` |
| `e_peak_entry` | Hawkes output | `core/hawkes/regime.py` |
| `beta_impact_by_tier` | trades.parquet + quotes.parquet | `core/impact/price_impact_bridge.py` |
| `spread_derivative` | quotes.parquet | `core/impact/price_impact_bridge.py` |
| `lambda_ref_per_session` | trades.parquet | `data/loaders/trades.py` |
| `halt_windows` | trades.parquet + quotes.parquet | `utils/halt_detection.py` |
| `lee_ready_ambiguity_rate` | trades.parquet | `core/ofi/trade_ofi.py` |

**Removed:** `depth_ratio_D(t)` as a calibrated feature (retained as real-time sanity veto only). `scanner_rank_dynamic` removed entirely — replaced by [[Tradeable Setup Filter]].

---

## Implementation Tasks

### Phase 0 — Gate Pass Rate Analysis (BLOCKING)

Do this before writing any other code.

- [ ] Apply setup filter mask to full historical event catalog; record surviving event count
- [ ] Proxy Gate 2 using a simple intensity threshold on the filtered universe
- [ ] Proxy Gate 3 using a basic OFI and spread estimate on the filtered universe
- [ ] Compute marginal pass rates: Gate 1 alone, Gates 1+2, Gates 1+2+3
- [ ] If triple-AND ≥ 150: proceed with AND gate; if 75–149: implement scoring gate; if < 75: stop
- [ ] Document result and gate architecture decision before proceeding to Phase 0.5

**Visual deliverables:**
- Bar chart of marginal pass rates: events surviving setup filter → + Gate 2 → + Gate 3
- Timeline scatter: for 20–30 setup-filtered events, mark triple-AND fire times across the 4am–8pm window

---

### Phase 0.5 — Train/Validation/Test Split (BLOCKING)

> **Status: COMPLETE** — Train: 2,162 events (2020-01-03 to 2023-11-17), Val: 720 events (2023-11-17 to 2024-07-22), Test: 722 events (2024-07-23 to 2024-12-31). Boundary locked in `config/holdout_boundary.json`.

- [x] Sort the Phase 0 filtered event catalog chronologically by event date
- [x] Define split boundaries by event count: Train (oldest 60%), Validation (middle 20%), Test (most recent 20% — **locked until Phase E**)
- [x] Write the test split boundary date to `config/holdout_boundary.json`. Lock it.
- [x] Confirm: no calibration code in Phases A–D touches the test split. Add an assertion to each calibration script.
- [x] Document event counts per split and the boundary date.

**Walk-forward validation (Phase E):** In addition to the single test split, implement rolling walk-forward: calibrate on a 12-month window, test on the following 3 months, roll forward. For each 3-month test window, bootstrap resample the individual trades 1,000 times and report the 5th/50th/95th percentile of PF.

---

### Phase A — Hawkes Engine

> **Status: COMPLETE (Iteration 7)** — K=1 univariate, beta_fixed=0.1 (6.93s half-life), rho=0.99, 4 params (2 self-alphas + 2 mus). Median n_base=0.154. See [[Phase A Results]] for full iteration history.

**Iterations 1–3 (SUPERSEDED):**

- [x] ~~Build `core/hawkes/engine.py` — K-kernel architecture~~ *(superseded by K=1 rewrite in iter 4)*
- [x] Build `core/hawkes/ekf.py` — `KalmanIntensityEstimator` (log-state EKF) + `SnyderFilter`
- [x] Build `core/hawkes/regime.py` — `RegimeStateMachine` (unchanged)
- [x] ~~Build `core/hawkes/forgetting.py` — fixed-beta MLE~~ *(superseded by free-beta rewrite in iter 4)*
- [x] ~~**Kernel count comparison:** K=7 selected~~ *(invalidated — iteration 2 showed K≈1 collapse)*
- [x] **EKF vs. Snyder benchmark:** Snyder MAE=56 vs EKF MAE=1.1M; **SNYDER selected**

**Iterations 4–5 (SUPERSEDED by iter 7):**

- [x] Rewrite `core/hawkes/engine.py` — K=1, free beta, `swap_params()` with threading lock
- [x] Rewrite `core/hawkes/forgetting.py` — free-beta MLE with analytical gradient, `fit_online()` warm start
- [x] Rewrite `calibration/phase_a_hawkes.py` — constant online refitting (cold start + refit every 50 trades)
- [x] Update tests: atomicity, warm start convergence, free-beta recovery, O(N^2) brute-force cross-validation
- [x] Secondary rho validation: {0.995, 0.999, 0.9995, 0.9999} — rho=0.9999 confirmed
- [x] Beta distribution analysis: histogram, bound-hit fraction (7.3% at bound=10000)
- [x] Convergence speed validation: median refit 7ms (well within 500ms target)
- [x] Beta bound derived from inter-arrival analysis: P99(1/median_dt) = 6,273 → bound = 10,000
- [x] Production calibration: 2,162/2,162 events, median n_base=0.552, median beta=1,352
- [ ] **Classification robustness test:** *(Deferred — requires labeled events; address in Phase B/C)*

**Iteration 7 (CURRENT — 2026-03-26):**

- [x] Drop cross-excitation: univariate model, 4 params (alpha_buy_self, alpha_sell_self, mu_buy, mu_sell)
- [x] Fix beta at 0.1 (half-life 6.93s, regime-detection timescale) — not MLE-fitted
- [x] Rho sweep: {0.99, 0.995, 0.999, 0.9995} on 50 events — rho=0.99 selected (LL=-1085, monotonically best)
- [x] Production calibration: 50 events, median n_base=0.154, 0% alpha saturation, 100% subcritical

**Visual deliverables:**
- E(t) and Ė(t) trace with trade arrival rug plot; mark gate fires
- n_base(t) and n_eff(t) trajectories for 20+ labeled burst events
- Regime state step function vs. E(t) and λ̂(t) and price on shared time axis
- Forgetting rate calibration: n_base(t) trajectories for candidate ρ values; 5 burst + 5 non-burst sessions
- Halt freeze validation: known halt-resume event, with and without freeze
- Threshold calibration histograms: Ė(t) distribution at burst onsets vs. noise; precision/recall curve for θ_slope
- EKF vs. Snyder tracking: λ̂(t) trajectories on 20+ burst events; MAE table; per-event compute time histogram
- Beta distribution: histogram of fitted beta across all refits and training events
- Rho secondary validation: parameter stability and n_base precision/recall by rho value
- Total intensity vs. bivariate regime: confirm they agree on burst timing

---

### Phase B — OFI Features

> **Status: COMPLETE (Approved)** — 2,160/2,162 events; Q_bar: tight=242, medium=285, wide=193; amb rate median 9.4%; Step 2 activation 7.7%. See [[Phase B Results]].

- [x] Build `core/ofi/trade_ofi.py` — `compute_trade_ofi(trades, window_sec=10)`
  - Two-step microprice classifier (not standard Lee-Ready alone)
  - Spread-normalized variant: `OFI_norm = OFI / (spread × Q_bar)` with ≥50-trade guard and 95th-pct Winsorize
  - Fallback when trade count < 50: per-tier median Q_bar from training catalog
  - Track final ambiguity rate (after both steps) per 60s window; Step 2 activation rate separately
- [x] Run two-step classifier calibration:
  - Step 1 ambiguity band: 10% of spread around mid
  - Step 2 margin: 0.5 × half-spread
  - Thresholds stored in `config/lee_ready_thresholds.json`
  - Same thresholds for all sessions (pre-market/regular/post-market — negligible difference)
- [x] Build `core/ofi/quote_ofi.py`
  - `compute_microprice(bid_px, ask_px, bid_sz, ask_sz) -> float`
  - `compute_quote_imbalance(bid_sz, ask_sz) -> float`
  - `apply_persistence_filter(qi_series, min_consecutive=3)`
- [x] 34 unit tests (18 trade_ofi + 16 quote_ofi), all passing

**Known implementation risks (from Phase A pattern review):**

- **Division by zero in OFI_norm and microprice:** Three distinct cases occur on real data: `spread = 0` in pre-market before opening quotes establish; `Q_bar = 0` before the rolling mean has accumulated any trades; `Q_bid + Q_ask = 0` in thin pre-market books (microprice denominator). All three require explicit guards in `compute_trade_ofi` and `compute_microprice`. The formulas look clean on paper but will crash or produce inf/NaN on edge-case events without guards. Analogous to the mu lower bound issue in Phase A — the degenerate case is not obvious until the data hits it.
- **Step 2 calibration requires manual labeling first:** Calibrating the Step 2 threshold requires 50+ labeled midpoint prints from pre-market sessions with known 5s forward returns > 0.3%. This is a blocking subtask that requires data annotation work before the module can be calibrated. Plan the labeling effort before writing code.
- **Numba caching:** If `classify_trade` or the OFI inner loop are Numba-compiled, clear `__pycache__` after any function modification. Stale compiled code runs silently with the old logic — same issue encountered in Phase A.
- **Windows encoding:** Use ASCII in all logging and print statements. Symbols such as lambda, rho, delta, Q-bar will cause cp1252 encoding errors on this machine.

**Visual deliverables:**
- OFI vs. price trace: cumulative OFI and mid-price on shared time axis for 3–5 burst events
- OFI_norm distribution: histogram at gate-fire moments by spread tier
- Microprice vs. mid divergence: 60s window around a burst; microprice should visibly lead
- QI persistence filter: raw vs. filtered QI on a noisy quote sequence
- Two-step classifier comparison: final ambiguity rate vs. Lee-Ready-only per session hour
- Pre-market OFI_norm R² vs. regular hours R²: side-by-side scatter per tier on validation split

---

### Phase C — Burst Magnitude Gate and Persistence Bridge

> **Reformulated 2026-03-21.** The original OFI-predicted impact model (beta_tier * |OFI|^gamma * sign(OFI)) produced R^2 < 0.001 for all tiers because these are catalyst-driven events where flow follows price. Gate 3 is now a burst magnitude check with activity qualifier. perm_frac shifts to exit timing. See design decisions log.

- [x] Build `core/impact/price_impact_bridge.py` — `PriceImpactBridge`
- [x] Implement `calibrate()`:
  - Replay E(t) trajectories on all training events using `hawkes_replay_fixed_beta`
  - Detect burst time via steepest rolling mid-price change (not E(t) peak — Hawkes timescale is sub-ms, not useful for 5-60s windows)
  - Compute delta_mid_5s, delta_mid_60s anchored to burst time in single pass
  - Compute per-event spread tier and median spread
  - Compute OFI at burst time (for directional confirmation analysis)
  - Log results to `config/price_impact_bridge_params.json`
- [x] **Calibrate Gate 3 thresholds per tier:**
  - For each tier: sweep K_tier values, compute pass rate and same-direction continuation rate
  - Select K_tier that maximizes yield (pass_rate x same_dir_rate) subject to same_dir >= 65%
  - Calibrate V_min (minimum dollar volume) as activity qualifier
  - Report per-tier: K_tier, V_min, pass rate, same-dir rate, amplification rate
- [x] **Calibrate perm_frac per tier (exit timing signal):**
  - Mid-based: Cov(delta_mid_60s, delta_mid_5s) / Var(delta_mid_5s) per tier
  - Report per-event perm_frac distribution: same-direction rate, amplification rate, percentiles
  - Report perm_frac x activity interaction (high dollar_vol events show stronger amplification)
- [x] **EXIT 2 subcritical calibration (Stage 1 — burst dynamics only):**
  - Compute E(t) trajectory from burst onset through decay
  - Set subcritical exit threshold at 25th percentile of exhaustion E(t)
  - Store result in `config/exit2_subcritical_threshold.json`
- [x] Implement `check_gate3(delta_mid_5s, spread, dollar_vol, tier) -> bool`
- [x] Implement `spread_widening_flag(quotes, t, window_sec=10) -> bool` with 50ms persistence filter
- [x] Expose `recalibrate(lookback_days=90)` for quarterly regime robustness

**Known implementation risks:**

- **E(t) replay required:** Phase A stored only final fitted parameters — not E(t) time series. Phase C replays the Hawkes engine on all training events using `hawkes_replay_fixed_beta` (no EKF/adaptive scaling — adaptive beta causes lambda_hat divergence in retrospective analysis).
- **Burst detection uses price, not E(t):** The K=1 beta=1352 Hawkes kernel has ~0.7ms timescale. E(t) finds microsecond trade clustering, not momentum onset. Price-based detection (steepest rolling mid-price change) correctly identifies the momentum event.
- **Wide-tier bimodality:** Wide-spread events are a mixture of illiquid (nothing happening, low activity, 30% amplification) and volatile (everything happening, high activity, 46% amplification = identical to medium). The activity qualifier V_min separates these populations.
- **Dual forward window must be a single pass:** delta_mid_5s and delta_mid_60s from the same quote stream, anchored to the same burst timestamp.
- **Windows encoding:** Use ASCII in all logging and print statements.

**Visual deliverables:**
- Gate 3 threshold sweep: pass rate and same-dir rate vs K_tier per tier
- Activity qualifier analysis: amplification rate vs dollar_vol (continuous, per tier)
- perm_frac distribution per tier: histogram with same-dir and amplification rates marked
- perm_frac x activity interaction: rolling amplification rate vs log(dollar_vol) per tier
- OFI sign agreement vs activity: rolling OFI direction agreement vs dollar_vol per tier
- Activity vs spread scatter: log(dollar_vol) vs log(spread) showing tier overlap and bimodality
- EXIT 2 subcritical threshold: distribution of E(t) at burst exhaustion points; mark 25th percentile

---

### Phase D — Volume Acceleration

> **Status: COMPLETE (Approved)** — Module built and tested (31 tests). EXIT 3 E(t) condition was degenerate with iter 5 beta=1352; now functional with iter 7 beta=0.1. See [[Phase D Results]].

- [x] Build `core/features/volume_acceleration.py` — `compute_vol_accel(trades, window_sec=5)`
  - Shares/sec in current 5s window minus prior 10s baseline window
  - Return NaN (no-signal) if fewer than 10 trades in current window
  - `e_peak_entry` tracking lives in `RegimeStateMachine`; reset on each new entry
  - Also provides `compute_vol_accel_series()` for calibration/visualization
- [x] 31 unit tests across 5 classes, all passing

**Known implementation risks (from Phase A pattern review):**

- **NaN must propagate as no-signal, not veto:** The NaN return (fewer than 10 trades in window) must be treated by every caller as "skip EXIT 3 check," not as zero or False. If any caller interprets NaN as a failed condition, EXIT 3 becomes a veto that fires whenever data is sparse. Test this explicitly in integration before wiring into the backtest runner.
- **Numba caching:** Clear `__pycache__` after any JIT function changes to `compute_vol_accel`. Stale compiled code runs silently — same issue encountered in Phase A.
- **Windows encoding:** Use ASCII in all logging and print statements.

**Visual deliverables:**
- Volume acceleration trace: cumulative volume / V̈(t) / mid-price on shared time axis for 3–5 bursts
- Exit 3 timing analysis: mark EXIT 3 fires on price traces; compare PnL captured vs. given back
- Exit 3 threshold calibration: PnL captured at p_exit3 values 0.5–0.8

---

### Phase E — Backtest Runner

> **Status: IN PROGRESS** — v6 test run complete (100 val events, stratified sample). PF=1.54, Win%=44.4%, all 4 exits functional. See [[Phase E v6 Test Run Results]].

- [x] Build `backtest/runner.py` — wire all modules together
  - Online-refitting Hawkes (cold start 1000 trades + refit every 50 on 10k sliding window)
  - Lee-Ready two-step classifier via `compute_trade_ofi`
  - `check_gate3()` for burst magnitude gate (K=0.25, delta_mid_5s > K * spread)
  - Setup filter mask
  - `compute_vol_accel` for EXIT 3 with `e_peak_entry` comparator
  - EPG (EventAnchor + ParticipationGate) with k=5, tau=300s, p=0.65
- [x] Implement entry gate: EPG PASS + Gate 3 fire + positive direction
- [x] Implement exit stack: EXIT 4 (90s) > EXIT 1 (75 bps) > EXIT 2 (E<1.2) > EXIT 3 (vol decel + E decay)
- [x] EXIT 2 recalibrated: threshold=1.2 (Hawkes equilibrium-based, 27% of trades, 70% win rate)
- [x] Walk-forward with bootstrap CIs: 3-month windows, all 3 windows 5th-pct PF > 1.0
- [x] Sequential positions: one at a time, no pyramiding, no cooldown
- [x] Fill model: next-trade price; PnL in percent
- [x] Year-stratified random sampling (--random-sample N, --seed)
- [ ] **EXIT 2 Stage 2 validation:** Verify mean forward return at EXIT 2 is < 0 in 10-30s after exit
- [ ] **Full val split run** (1228 events) or larger stratified sample
- [ ] **Parameter sensitivity analysis** (±20% perturbation on test split)
- [ ] **Test split run** (after val results are stable)

**Known implementation risks (from Phase A pattern review):**

- **EXIT 4 priority:** EXIT 4 (90s hard stop) must be the first check in the exit stack, evaluated unconditionally before any other exit condition. In an if-elif chain it is easy to accidentally order it last or nest it inside another condition. Test explicitly: a 91-second hold must trigger EXIT 4 even when all other exit conditions would produce a different result.
- **E_peak_since_entry, not session E_peak:** EXIT 3 uses the maximum E observed since the current entry time, not the session maximum. E(t) is below session peak for ~95% of any hold duration; using session peak makes EXIT 3 fire on almost every trade immediately after entry. The regime state machine resets this tracker on each `on_entry()` call — confirm this is wired correctly in the runner.
- **lambda_ref lookback must not include the event day:** For each event, lambda_ref is computed from T-3 to T-1 trading days prior to the event date. Including same-day trades in the baseline rate introduces information leakage that inflates n_base during the burst and biases the gate toward firing.
- **Windows encoding:** Use ASCII in all logging and print statements.

**Parameter sensitivity analysis (required before success criteria):** For each of θ_slope, E_min, n_thresh, ρ, composite_thresh, perm_frac per tier, p_exit3 — perturb by ±20% and re-run on the test split. A robust result must not drop below PF 1.1 on any single ±20% perturbation. Parameters with |Pearson correlation| > 0.7 between perturbation magnitude and PF change are flagged as fragile.

**Visual deliverables:**
- Individual trade walkthrough: 10–15 representative trades; per-trade chart with all signals on shared time axis
- Equity curve: cumulative PnL with drawdown; split by spread tier and time-of-day bucket
- Hold time distribution: by exit type and win/loss
- Exit type breakdown: stacked bar of EXIT 1/2/3/4 fraction
- Slippage as % of gross PnL: scatter per trade with 30% threshold line
- PnL by session hour: full 4am–8pm window
- Parameter sensitivity table: PF at ±20% perturbation of each key parameter
- Walk-forward PF distribution: histogram with 5th/50th/95th bootstrap CI per window

### Phase F — MFE/MAE Excursion Analysis

> **Status: COMPLETE** — 15,557 trades instrumented with per-trade MFE/MAE. Excursion analysis shows stop width is not the issue — all EXIT_1 losses hit the full 75 bps floor. 51.6% of EXIT_1 losses are immediately adverse (MFE < 0.05%). Tightening stop to -40 bps would cut 20.9% of winners. Recommendation: improve entry quality, not stop width.

- [x] Instrument `backtest/runner.py` with per-trade MFE/MAE tracking (mid-based)
- [x] Re-run 100-event stratified val sample — exact reproduction confirmed (PF=1.618, n=15,557, EXIT_1=5,712)
- [x] Step 3A: MAE/MFE distribution by exit type
- [x] Step 3B: 5,001-trade scatter sample (stratified by exit type)
- [x] Step 3C: EXIT_1 loss deep dive — 51.6% never favorable, 37.9% saw 20+ bps green before reversal
- [x] Step 3D: OFI quartile analysis — 2.42 bps range, no gradient (OFI magnitude does not predict MAE)
- [x] Step 3E: Winner drawdown — 35.2% dipped >20 bps, 20.9% dipped >40 bps before winning

### Phase F v2 — Trade Feature Correlation & Excursion Analysis

> **Status: COMPLETE** — 15,557 trades enriched with 13 entry feature snapshots (Hawkes state, OFI, spread, quote imbalance, microprice, vol accel, time of day). Correlation analysis against pnl_pct, mfe_pct, mae_pct. 50 interactive Plotly charts. Gap % unavailable (daily data does not cover val-split events).

---

## Success Criteria

Evaluated on the test split only.

| Metric | Threshold | Reasoning |
|--------|-----------|-----------|
| Profit Factor | > 1.3 | After slippage; evaluated on locked test split |
| Walk-forward median PF | > 1.1 | Confirms PF is not specific to a single time period |
| Walk-forward robustness | ≥ 60% of windows with 5th-pct bootstrap PF > 1.0 | Confirms wins are distributed, not concentrated |
| SQN | > 1.0 | Stabilized from prior negative performance |
| Mean slippage / gross PnL | < 30% | Single entry architecture addresses prior cost blowout |
| Win rate | > 45% | Momentum events with confirmed permanent impact |
| Avg hold time | 20–90s | Too short = noise; too long = mean reversion |
| Triple-AND sample size | ≥ 150 (test split) | Below this, scoring gate was used |
| Parameter sensitivity | PF ≥ 1.1 at any ±20% perturbation | Confirms robustness, not curve fit |

---

## Known Risks & Mitigants

| Risk | Mitigant |
|------|----------|
| LULD halt treated as quiet time | Freeze all state during halt windows; inflate Kalman uncertainty on resume; if halt > 30s while position held in SUPERCRITICAL, exit at market on halt lift |
| Busy session generates noisy Ė signal | Gate requires both Ė(t) > θ_slope AND E(t) > E_min; Ė uses EMA with 1.0s denominator cap |
| Hawkes not warmed up early in extended session | Require ≥30 baseline events since 4:00 AM before exposing E(t), Ė, n as gate signals |
| Lee-Ready misclassification in wide-spread books | Two-step microprice classifier; session-hour-adjusted threshold; stored in `config/lee_ready_thresholds.json` |
| QI flicker in thin book | 3-consecutive-update persistence filter |
| β_impact non-stationary across regimes | Quarterly rolling recalibration via `PriceImpactBridge.recalibrate()` |
| Setup filter applied inconsistently to historical calibration | Explicit setup filter mask applied before any regression in Phase C; test split excluded |
| perm_frac contaminated by multi-burst events | Event cleanliness filter; clean vs. multi-burst estimates compared |
| Triple-AND gate too restrictive | Phase 0 is blocking; scoring gate fallback fully defined |
| Over-fitting across 20+ free parameters | Train/validation/test split; walk-forward validation; parameter sensitivity analysis; kernel count validated in Phase A |
| Windows encoding (cp1252) on Windows | Use ASCII equivalents in all log and print statements in every calibration script and module. Greek and mathematical symbols (lambda, rho, mu, alpha, beta, delta, theta, Q-bar) cause cp1252 encoding errors on this machine. Applies to every phase. |
| Python 3.11 required for scipy/numba | Default Python on this machine is 3.14; scipy and numba are only available on 3.11. Always invoke: `C:\Users\cleem\AppData\Local\Programs\Python\Python311\python.exe`. Applies to every phase. |
| Numba stale cache after JIT function edits | After modifying any Numba-compiled function, clear `__pycache__` directories before re-running or the old compiled code executes silently. Applies to Phase B (classify_trade, OFI inner loop) and Phase D (compute_vol_accel). |
| OFI_norm and microprice division by zero (Phase B) | Three cases on real data: spread=0 (pre-market before opening quotes), Q_bar=0 (before 50 trades accumulate), Q_bid+Q_ask=0 (thin pre-market books). All three require explicit guards in compute_trade_ofi and compute_microprice before the formulas are applied. |
| Phase C E(t) replay scale and checkpointing | Generating E(t) trajectories for the event cleanliness filter requires replaying the Hawkes engine on all 2,162 training events — roughly equivalent in compute cost to Phase A. Requires checkpointing at event granularity; a failure without checkpoints loses the entire replay. |
| Phase C dual forward window single-pass requirement | Delta_mid_5s and Delta_mid_60s must be computed in a single pass over the quote stream anchored to the same burst timestamp. Separate passes risk mismatched time windows — the same class of bug as the Phase A two-pass compensator divergence. |
| EXIT 4 ordering in backtest runner (Phase E) | EXIT 4 (90s hard stop) must be evaluated first, unconditionally, before any other exit logic. Incorrect ordering in an if-elif chain is a high-probability implementation bug. Test explicitly with a 91s hold before accepting the runner. |
| EXIT 3 E_peak_since_entry vs. session peak (Phase E) | EXIT 3 must use E_peak_since_entry (max E since the current entry), not the session E_peak. E(t) is below session peak for ~95% of any hold duration; using session peak makes EXIT 3 fire immediately on nearly every trade. |
| lambda_ref lookback contamination (Phase E) | lambda_ref must be computed from T-3 to T-1 trading days, never from the event day itself. Including same-day trades in the baseline rate introduces information leakage that inflates n_base during the burst. |
| Online refitting silently not executing (runner loads median params and never calls swap_params) | Before any backtest run is considered valid, verify refit execution with a per-event log trace showing n_base variance. A constant n_base across all trades is a definitive failure signal. See Phase F v2 post-mortem. |

---

## Design Decisions Log

| Decision | Rationale |
|----------|-----------|
| Clock-time Hawkes with adaptive β | Preserves time-domain clustering semantics; prevents R explosion at high TPS |
| Gate on Ė(t) not E(t) level | Sustained busy periods produce high flat E(t); genuine burst onset produces rising E(t) |
| Ė(t) as EMA of per-event ΔE/Δt | Raw finite difference variance blows up at high TPS; EMA with 1.0s denominator cap gives stable slope estimate |
| E(t) as total intensity ratio | Bivariate process has no single λ; total intensity is classification-agnostic for burst detection |
| Log-state EKF for λ̂ | Direct clipping truncates the Gaussian state distribution; log-state ensures positivity by construction |
| n_base as spectral radius of 2×2 branching matrix | Average row sum fails under directional burst asymmetry; exact 2×2 spectral radius is always correct |
| Forgetting likelihood indexed by event count | Memory table directly interpretable; timestamp-based indexing was ambiguous |
| OFI signed power \|OFI\|^γ · sign(OFI) | Non-integer γ on a negative OFI value is undefined in the reals; signed power is the standard extension |
| perm_frac as OLS slope | E[ratio] is dominated by near-zero denominators; OLS slope is robust |
| OFI_norm uses time-averaged spread | Instantaneous spread can change 50–200% within a burst window |
| EXIT 2 subcritical calibrated from burst dynamics | Calibrating on PnL is in-sample fitting; burst exhaustion distribution is a structural calibration |
| perm_frac computed using both mid and VWAP; winner selected per tier | Quoted mid at t+5s is noisy in wide-spread books; SD comparison determines which is more stable |
| Kernel count validated before locking architecture | 28 α parameters on 150–300 events is a high-dimensional fit; parsimony reduces overfitting risk |
| n_base (not n_eff) for SUPERCRITICAL gate | Adaptive β causes n_eff to shrink during bursts — exactly backwards for detection |
| Trade-based OFI as primary directional signal | Book too unstable in gapping stocks; executed trades are ground truth |
| Phase 0 as blocking step | Prevents building a full system that fires fewer than 75 times in history |
| EXIT 4 checked unconditionally first | Hard stop must override all other logic; prevents hanging positions |
| EXIT 3 uses E_peak_since_entry, not session peak | Session peak is satisfied for ~95% of any hold duration |
| Single-pass LL (log-sum + compensator in one loop) | Two-pass design caused EKF state divergence between log-sum and compensator; compensator drift grew with event count, causing alpha saturation (Phase A iter 1 bug) |
| Soft branching-ratio penalty in MLE, not hard α bounds | Hard bounds produce boundary solutions; soft penalty `N_eff × 100 × (n_base - 0.99)²` allows optimizer to find interior solutions |
| μ lower bound `max(λ_ref × 0.01, 0.01)` | Without exogenous baseline floor, MLE converges to degenerate pure-branching solution (μ→0, n_base→1) regardless of compensator correctness |
| **Fixed β in MLE (Option A) — adaptive β only at runtime** | Adaptive β creates circular optimization: optimizer controls α/μ → influences λ̂ → changes β_eff → reduces compensator cost of fast kernels. This exploit causes all excitation to concentrate on β₀=100 with identical degenerate parameters regardless of ρ. Parameters must be estimated at the reference intensity using fixed β_base; adaptive scaling applies only during live replay. (Phase A iter 2 fix) |
| **Two-layer n_base penalty: soft at 0.85, hard wall at 0.90** | Single threshold at 0.99 was too permissive — optimizer found degenerate solutions at n_base≈0.995 that were barely penalized. Two-layer penalty: `5000×(n-0.85)²` steers optimizer away from criticality; `+50000×(n-0.90)²` makes supercritical solutions prohibitively expensive. (Phase A iter 2 fix) |
| **μ floor raised to `max(λ_ref × 0.05, 0.1)`** | Previous floor `max(λ_ref × 0.01, 0.01)` was too low — allowed optimizer to push μ to near-zero while loading all intensity onto fast-kernel excitation. 5% of observed rate ensures meaningful exogenous baseline. (Phase A iter 2 fix) |
| **Left-limit convention: compute λ(t_i^-) BEFORE adding event to R** | Self-inclusion bug: adding event i to R before computing intensity inflated log(λ) by α_self at every event (68% log-sum overestimate on 3-event test). This caused all excitation to concentrate on the fastest kernel, suppressed μ to floor, and made val LL insensitive to ρ. Fix validated with 3 analytical tests (hand-computed to 1e-6) and 8 O(N^2) brute-force cross-validation tests (matching to 1e-10). (Phase A iter 3 fix) |
| **K=1 selected based on empirical kernel collapse** | With K=7, only kernel 0 (β=100, ~7ms half-life) carried meaningful weight in iteration 2; kernels 1–5 at lower bound (1e-8). The 7-kernel architecture collapsed to K≈1 regardless of starting point. K=1 with free β is simpler (7 vs 30 parameters), avoids the unjustified multi-timescale prior, and lets the data choose a single decay rate. (Phase A iter 4 decision) |
| **Beta free in MLE rather than fixed bank** | Fixed β_base=[100, 40, 15, 6, 2, 0.8, 0.3] was an unjustified prior on decay timescale. With K=1, β is added to the MLE parameter vector with bounds (1.0, 10000.0). The joint α-β surface has more local minima than α-only, making multi-start optimization (3–5 restarts) more important. (Phase A iter 4 decision; bound updated iter 5) |
| **Beta upper bound 10000 derived from inter-arrival analysis** | Original bound of 500 caused 100% saturation. Bound of 2000 reduced to 31% saturation. Systematic analysis of 1/median_dt across all 2,162 training events: P99 = 6,273, max = 31,225 (China ADR cluster). Bound set to ceil(P99 × 1.5 / 500) × 500 = 10,000. Production result: 7.3% at bound (157 events — extreme-liquidity tail beyond P99, all subcritical). Alpha upper bound scales with beta_max. (Phase A iter 5) |
| **Online refitting every 50 trades (MANDATORY)** | Per-stock non-stationarity means a single offline parameter set cannot serve both liquid pre-market gapers and thin post-market movers. This is a required runtime behavior, not an optional optimization. Cold start: first 1,000 trades per event, 5 restarts. Warm path: every 50 trades, 1 restart, rolling 10,000-trade window. Params applied via atomic swap — hot path never reads partial state. Per-event lambda_ref from T-3 to T-1 days (not global constant). n_base_at_entry must reflect the currently active refitted params, not the init config. A constant n_base across all trades is a definitive failure signal. (Phase A iter 4 decision; clarified after Phase F v2 post-mortem) |
| **Gate 3 reformulated: burst magnitude + activity qualifier replaces OFI impact prediction** | Phase C calibration (5,113 events, all spread tiers) found OFI->delta_mid R^2 < 0.001. Root cause: these are catalyst-driven events (earnings/news gaps) where OFI measures reactive flow after the price adjusts, not causal flow. OFI sign agreement with delta_mid is only 56-60% — better than random but too weak to predict magnitude. The burst magnitude gate (delta_mid_5s > K x spread AND dollar_vol > V_min) answers the right question: "has the price already confirmed this is a real momentum event?" The activity qualifier addresses wide-tier bimodality: wide-spread events split into illiquid-nothing-happening (30% amplification) vs volatile-everything-happening (46% amplification, identical to medium). Dollar volume separates these populations (Spearman rho with amplification = +0.179 for wide, p < 0.0001). perm_frac shifts from entry gate to exit timing signal — perm_frac > 1.0 for all tiers confirms momentum amplification, informing hold duration rather than entry decision. (Phase C iter 2, 2026-03-21) |

---

## Results

### Phase E v6 — 100-Event Stratified Val Sample (2026-03-26)

| Metric | Value |
|--------|-------|
| Events processed | 100 (89 with trades, 10 skipped, 1 error) |
| Total trades | 21,076 |
| Profit Factor | **1.54** |
| Win Rate | 44.4% |
| SQN | 15.78 |
| Mean PnL | +0.24% per trade |
| Median PnL | 0.00% per trade |
| Total PnL | +4,957.5% cumulative |
| Mean hold time | 11.3s |
| Profitable events | 80/89 (89.9%) |

**Exit breakdown:** EXIT_1 39.1%, EXIT_2 27.2%, EXIT_3 32.2%, EXIT_4 1.5%

**Walk-forward (3-month windows):** All 3 windows have 5th-percentile PF > 1.0. Median window PF: 1.57.

**Sample:** Year-stratified random sample (seed=42): 16 events from 2023, 84 from 2024. Covers all 9 months of val split.

**Fill model:** Next-trade price. PnL in percent. One position at a time, no pyramiding.

See [[Phase E v6 Test Run Results]] for full analysis.

---

## Related Notes

- [[Tradeable Setup Filter]] — universe gate; must be applied to historical catalog before Layer 3 calibration
- [[Project Directory]] — full modular project structure; all modules listed as "needs to be built" are defined here