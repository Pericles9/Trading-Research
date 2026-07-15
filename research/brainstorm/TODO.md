---
tags:
  - type/idea
  - project/src-core
  - status/wip
created: 2026-04-04
---

# Bivariate Kernel Hawkes — Implementation Checklist

## Phase 1: Preparation & Research
- [x] Analyze `univariate_kernel_hawkes.py`: `fit_linear_hawkes_torch`, `walk_forward_en_torch`, `compute_recursive_features_torch`
- [x] Verify data schema: trades.parquet (`sip_timestamp`, `price`, `size`), quotes.parquet (`sip_timestamp`, `ask_price`, `bid_price`)
- [x] Understand `prepare_active_trades` from `luld_halt_detection.py`
- [x] Create this TODO.md

## Phase 2: Data Engineering — Trade Classification (Lee-Ready)
- [ ] Load both `trades.parquet` and `quotes.parquet`
- [ ] Convert `sip_timestamp` (ns int64) → pd.Timestamp for both dataframes
- [ ] `pd.merge_asof` to align each trade with most recent quote (backward direction)
- [ ] Classify: Trade_Price >= Ask_Price → Buy; Trade_Price <= Bid_Price → Sell
- [ ] Tick Test fallback: if strictly between Bid and Ask, compare to previous trade price
- [ ] Split into `timestamps_buy` and `timestamps_sell` arrays
- [ ] Vectorize everything — no row iteration

## Phase 3: Bivariate Math — Dual Regression
- [ ] Compute `R_buy` using `compute_recursive_features_torch` on buy timestamps
- [ ] Compute `R_sell` using `compute_recursive_features_torch` on sell timestamps
- [ ] Sample `R_buy(t)` and `R_sell(t)` at every event time via `torch.searchsorted`
- [ ] **Regression A (Buy Intensity)**:
  - Target: 1/Δt_buy at buy timestamps
  - Features: [1, R_buy_at_buy, R_sell_at_buy]
  - Fit: ElasticNet/NNLS → μ_buy, α_buy←buy, α_buy←sell
- [ ] **Regression B (Sell Intensity)**:
  - Target: 1/Δt_sell at sell timestamps
  - Features: [1, R_buy_at_sell, R_sell_at_sell]
  - Fit: ElasticNet/NNLS → μ_sell, α_sell←buy, α_sell←sell

## Phase 4: Walk-Forward Refit
- [ ] Pre-compute `R_buy` and `R_sell` once on GPU for entire timeline
- [ ] For each window slice:
  - Slice buy/sell timestamps within window
  - Run two separate regressions
  - Store predictions for both streams
- [ ] Store `lam_buy_pred` and `lam_sell_pred`

## Phase 5: Output & Visualization
- [ ] Two-line intensity plot: Green = Buy Intensity, Red = Sell Intensity
- [ ] Correlation analysis: Buy Intensity vs Price (positive?), Sell Intensity vs Price (negative?)
- [ ] Save `summary.json` with separate stats for Buy and Sell parameters
- [ ] Output to `runs/bivariate_kernel_hawkes/<timestamp>/`

## Phase 6: Verify
- [ ] Run script end-to-end
- [ ] Fix any runtime errors
- [ ] Visual sanity check: Buy intensity spikes align with price moves up

## Related

- [[MHP Model]] — companion doc for the bivariate Hawkes module being built
- [[MHP_IMPLEMENTATION_SUMMARY]] — implementation summary
- [[README_MHP]] — MHP module overview
- [[README]] — brainstorm directory guide
- [[00-Index]] — vault index

## Related

- [[README]] — brainstorm directory guide
- [[MHP Model]] — the module this checklist was written for
- [[00-Index]] — vault index
