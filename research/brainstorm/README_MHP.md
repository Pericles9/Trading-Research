---
tags:
  - type/reference
  - domain/hawkes
  - project/src-core
  - status/complete
created: 2026-04-04
---

# Multivariate Hawkes Process (MHP) Module

**Modular, object-oriented implementation for analyzing lead/lag relationships between Trade Arrivals and Volatility Spikes using GPU-accelerated PyTorch.**

## Overview

This module implements a 2-dimensional Hawkes process to model the interaction between:
- **Stream 0**: Trade Arrivals (all trade timestamps)
- **Stream 1**: Volatility Spikes (timestamps where rolling volatility exceeds threshold)

The conditional intensity for dimension $m$ is:

$$\lambda_m(t) = \mu_m + \sum_{n=0}^{1} \sum_{t_k^{(n)} < t} \alpha_{m,n} \cdot \beta \cdot e^{-\beta(t - t_k^{(n)})}$$

Where:
- $\mu_m$: Baseline intensity for stream $m$
- $\alpha_{m,n}$: Impact coefficient (Branching Ratio) - how stream $n$ excites stream $m$
- $\beta$: Decay rate (shared, default 10.0)

## Module Structure

```
Research Notebooks/
├── mhp_model.py      # Core MultivariateHawkes class (torch.nn.Module)
├── data_loader.py    # Data preprocessing and bivariate stream preparation
├── analysis.py       # Causality analysis and visualization
├── main.py           # Main execution script
└── README_MHP.md     # This file
```

## Installation Requirements

```bash
pip install torch numpy pandas plotly scipy pandas-market-calendars
```

## Quick Start

### Basic Usage

```bash
# Run on random high-momentum candidate
python main.py

# Run on specific candidate
python main.py --candidate "SPY_20240115_150.5"

# Customize parameters
python main.py --max_trades 100000 --vol_threshold 2.0 --beta 5.0 --epochs 1000
```

### Programmatic Usage

```python
from mhp_model import MultivariateHawkes
from data_loader import prepare_bivariate_data, load_data_from_dir
from analysis import analyze_causality, plot_impulse_response
from pathlib import Path

# Load data
df_trades, df_quotes = load_data_from_dir(
    Path("data/filtered"),
    "SPY_20240115_150.5"
)

# Prepare bivariate streams
events, metadata = prepare_bivariate_data(
    df_trades,
    df_quotes,
    vol_threshold=1.5,
    rolling_window=50
)

# Fit Multivariate Hawkes
model = MultivariateHawkes(D=2, beta=10.0)
history = model.fit(events, epochs=500, lr=0.01)

# Analyze causality
results = analyze_causality(model)

# Visualize
fig = plot_impulse_response(model, max_time=5.0)
fig.show()
```

## Key Components

### 1. mhp_model.py - MultivariateHawkes Class

**Core Methods:**
- `forward(t, events)` - Compute $\lambda(t)$ at time $t$
- `compute_log_likelihood(events, T)` - Calculate log-likelihood for MLE
- `fit(events, epochs, lr)` - Train using Adam optimizer with GPU acceleration
- `get_parameters()` - Extract fitted $\mu$, $\alpha$, $\beta$
- `branching_ratio()` - Check stability (must be < 1.0)
- `simulate(T)` - Generate synthetic event sequences

**Key Features:**
- Enforces positivity via `softplus()` activation
- Automatic stability penalty when branching ratio > 1.0
- Vectorized log-likelihood computation for GPU efficiency
- Built-in training loop with progress logging

### 2. data_loader.py - Data Preprocessing

**Main Function:** `prepare_bivariate_data(df_trades, df_quotes, vol_threshold, ...)`

**Processing Steps:**
1. **Stream 0 (Trades)**: Extract all trade timestamps, convert to seconds from start
2. **Stream 1 (Vol Spikes)**:
   - Calculate log returns from trade prices or quote mid-prices
   - Compute rolling volatility (std dev) over 50-tick window
   - Identify spikes: `vol > mean + vol_threshold * std`
   - Return spike timestamps

**Supporting Functions:**
- `load_data_from_dir()` - Load trades.parquet and quotes.parquet
- `get_high_momentum_candidates()` - Find directories with momentum > threshold

### 3. analysis.py - Causality Analysis

**Main Function:** `analyze_causality(model, labels)`

**Computed Metrics:**
- **Cross-Excitation Ratios**:
  - $\frac{\alpha_{0,1}}{\alpha_{1,1}}$ = How Vol drives Trades vs. Vol drives Vol
  - $\frac{\alpha_{1,0}}{\alpha_{0,0}}$ = How Trades drive Vol vs. Trades drive Trades
- **Branching Ratios**: $BR_m = \sum_n \alpha_{m,n} / \beta$ (must be < 1.0)
- **Dominant Direction**: Which stream Granger-causes the other more strongly

**Visualizations:**
- `plot_interaction_matrix()` - Heatmap of $\alpha$ matrix
- `plot_impulse_response()` - IRF showing $\Delta\lambda_m(t) = \alpha_{m,n} \beta e^{-\beta t}$
- `plot_fitted_intensities()` - Time series of $\lambda_m(t)$ with event rug plots

### 4. main.py - Execution Pipeline

**Full Workflow:**
1. Select candidate (random or specified)
2. Load trade and quote data
3. Prepare bivariate event streams
4. Fit Multivariate Hawkes model
5. Analyze causality relationships
6. Generate visualizations
7. Save results (JSON + HTML plots)

**Command-Line Arguments:**
```
--data_path         Path to data directory (default: ../data/filtered)
--candidate         Specific candidate to analyze
--min_momentum      Minimum momentum for random selection (default: 100.0)
--max_trades        Max trades to process (default: 50000)
--vol_threshold     Volatility spike threshold in std devs (default: 1.5)
--rolling_window    Window for rolling volatility (default: 50)
--beta              Decay rate parameter (default: 10.0)
--epochs            Optimization iterations (default: 500)
--lr                Learning rate (default: 0.01)
--no_plots          Skip plot generation
--seed              Random seed for reproducibility
```

## Output Structure

Each run creates a timestamped directory in `runs/multivariate_hawkes/`:

```
runs/multivariate_hawkes/20260204_143052_iter001/
├── summary.json                   # High-level results
├── mhp_parameters.json            # Fitted μ, α, β
├── data_metadata.json             # Data preprocessing info
├── training_history.json          # Loss and branching ratio per epoch
├── interaction_matrix.html        # α matrix heatmap
├── impulse_response.html          # IRF plots (2x2 grid)
└── fitted_intensities.html        # λ_m(t) time series
```

## Interpretation Guide

### Understanding the α Matrix

The interaction matrix $\alpha$ reveals directional influence:

```
             Trades (n=0)    Vol Spikes (n=1)
Trades (m=0)    α[0,0]          α[0,1]
Vol (m=1)       α[1,0]          α[1,1]
```

- **Diagonal terms** ($\alpha_{0,0}$, $\alpha_{1,1}$): Self-excitation
- **Off-diagonal terms**: Cross-excitation (Granger causality)
  - $\alpha_{0,1} > \alpha_{1,0}$: **Volatility LEADS trades** (Vol spikes predict trades)
  - $\alpha_{1,0} > \alpha_{0,1}$: **Trades LEAD volatility** (Trades cause Vol spikes)

### Branching Ratio Stability

$$BR_m = \sum_{n=0}^{1} \frac{\alpha_{m,n}}{\beta}$$

- **BR < 1.0**: Stationary, stable process ✓
- **BR ≥ 1.0**: Non-stationary, explosive process ⚠️

### Cross-Excitation Ratio

$$\text{Vol→Trades Strength} = \frac{\alpha_{0,1}}{\alpha_{1,1}}$$

- **Ratio > 1.0**: Vol spikes have stronger impact on future trades than on future vol
- **Ratio < 1.0**: Vol's self-excitation dominates

## Example Output

```
======================================================================
MULTIVARIATE HAWKES CAUSALITY ANALYSIS
======================================================================

[1] FITTED PARAMETERS
----------------------------------------------------------------------
Baseline Intensities (μ):
  μ[0] (Trade Arrivals    ):   1.234567 events/sec
  μ[1] (Vol Spikes        ):   0.045678 events/sec

Decay Rate (β): 10.0000
  → Half-life: 0.069315 seconds
  → Mean memory: 0.100000 seconds

Impact Matrix (α) - α[m,n] = influence of stream n on stream m:
         Trade Arrivals  Vol Spikes
[0] Trade Arrivals        0.250000    0.450000
[1] Vol Spikes            0.080000    0.120000

[2] BRANCHING RATIO ANALYSIS
----------------------------------------------------------------------
  BR[0] (Trade Arrivals    ): 0.070000  [STABLE]
  BR[1] (Vol Spikes        ): 0.020000  [STABLE]

  ✓ All branching ratios < 1.0 → Process is stationary

[3] CROSS-EXCITATION ANALYSIS (Lead/Lag Relationships)
----------------------------------------------------------------------

Self-Excitation:
  α[0,0] (Trades → Trades):  0.250000
  α[1,1] (Vol → Vol):        0.120000

Cross-Excitation:
  α[0,1] (Vol → Trades):     0.450000
  α[1,0] (Trades → Vol):     0.080000

  Cross-Excitation Ratio (Vol → Trades) / (Vol → Vol): 3.750000
    → Volatility spikes have STRONGER impact on trades than on future volatility
    → Vol LEADS trades (predictive signal)

  📊 DOMINANT CAUSALITY: Volatility → Trades
     Strength ratio: 5.62x
     → Volatility spikes are 5.62x more predictive of trades
```

## Performance Notes

- **GPU Acceleration**: Automatically uses CUDA if available
- **Vectorization**: Log-likelihood computed without Python loops
- **Scaling**: Handles 50,000+ trades efficiently
- **Memory**: Events stored as torch tensors on device

## Advanced Usage

### Custom Beta Selection

The decay rate $\beta$ controls the memory timescale:
- High $\beta$ (e.g., 20.0): Short memory (~0.05s half-life) - for HFT
- Low $\beta$ (e.g., 1.0): Long memory (~0.7s half-life) - for slower dynamics

```python
model = MultivariateHawkes(D=2, beta=20.0)  # Fast decay
```

### Volatility Threshold Tuning

Adjust `vol_threshold` if too few/many spikes detected:
- Higher threshold (e.g., 2.0): Only extreme vol spikes
- Lower threshold (e.g., 1.0): More sensitive to vol changes

```python
events, metadata = prepare_bivariate_data(
    df_trades, df_quotes,
    vol_threshold=2.0,  # Stricter spike detection
    rolling_window=100  # Longer smoothing window
)
```

### Simulation for Validation

Test if fitted parameters reproduce realistic dynamics:

```python
# Simulate 60 seconds of events
synthetic_events = model.simulate(T=60.0, seed=42)

print(f"Simulated {len(synthetic_events[0])} trades")
print(f"Simulated {len(synthetic_events[1])} vol spikes")
```

## Mathematical Background

### Log-Likelihood Formulation

$$\log L = \sum_{m=0}^{1} \left[ \sum_{i} \log \lambda_m(t_i^m) - \int_0^T \lambda_m(s) ds \right]$$

**First term** (event log-intensities):
$$\sum_{i} \log \left( \mu_m + \sum_n \sum_{t_k^n < t_i} \alpha_{m,n} \beta e^{-\beta(t_i - t_k^n)} \right)$$

**Second term** (integral of intensity):
$$\mu_m T + \sum_n \sum_k \alpha_{m,n} (1 - e^{-\beta(T - t_k^n)})$$

### Granger Causality Interpretation

In Hawkes terminology:
- $\alpha_{m,n} \neq 0$ ⟹ Stream $n$ **Granger-causes** stream $m$
- Past events in $n$ improve prediction of future intensity of $m$
- Analogous to VAR models but for point processes

### Impulse Response Function

The impact of a single event in stream $n$ at $t=0$ on stream $m$:

$$\text{IRF}_{m \leftarrow n}(t) = \alpha_{m,n} \beta e^{-\beta t}$$

- **Peak impact**: $\alpha_{m,n} \beta$ (at $t=0^+$)
- **Half-life**: $\ln(2) / \beta$
- **Cumulative impact**: $\alpha_{m,n}$ (integral over $[0,\infty)$)

## Troubleshooting

### Issue: Branching ratio > 1.0

**Cause**: Over-parameterized or insufficient data
**Solutions**:
- Reduce learning rate: `--lr 0.005`
- Increase regularization (modify `fit()` penalty term)
- Use more data: `--max_trades 100000`

### Issue: Too few volatility spikes

**Cause**: Threshold too high or data too smooth
**Solutions**:
- Lower threshold: `--vol_threshold 1.0`
- Shorter window: `--rolling_window 20`
- Check quote data quality

### Issue: Slow convergence

**Cause**: Learning rate or initialization issues
**Solutions**:
- Adjust learning rate: `--lr 0.05` (higher) or `--lr 0.001` (lower)
- Increase epochs: `--epochs 1000`
- Ensure GPU available: Check `torch.cuda.is_available()`

## References

1. **Hawkes, A. G. (1971)** - "Spectra of some self-exciting and mutually exciting point processes"
2. **Embrechts, P. et al. (2011)** - "Multivariate Hawkes processes: an application to financial data"
3. **Bacry, E. et al. (2015)** - "Hawkes processes in finance"

## Citation

If you use this module in research, please cite:
```
Multivariate Hawkes Process Module for Trade-Volatility Analysis
GitHub: [Your Repository]
Year: 2026
```

## License

[Your License Here]

## Related

- [[MHP_IMPLEMENTATION_SUMMARY]] — implementation summary with file inventory
- [[MHP Model]] — companion doc for the MHP module
- [[GPU Accelerated MHP]] — companion doc for the GPU-accelerated version
- [[README]] — brainstorm directory guide
- [[00-Index]] — vault index
