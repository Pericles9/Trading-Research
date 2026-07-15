---
tags:
  - type/results
  - domain/backtest
  - project/v5-strategy
  - status/complete
created: 2026-02-09
---

# AlphaMomentumHawkes v5 — Battle Royale Results

**Generated:** 2026-02-09 22:00:43
**Events:** 200 per mode
**Runtime:** 1050.6s (17.5 min)

## Head-to-Head Comparison

| Metric | Mode A (Clock-Watcher) | Mode B (Volume-Dilator) | Mode C (Two-Stage Runner) |
|--------|------------------------|-------------------------|---------------------------|
| Events w/ Trades | 139 | 139 | 139 |
| Total Entries | 8053 | 8391 | 8048 |
| **Total PnL %** | **-107.32%** | -390.36% | -134.09% |
| Avg PnL % | **-0.772%** | -2.808% | -0.965% |
| Median PnL % | **-0.860%** | -1.515% | **-0.860%** |
| **Win Rate %** | 37.3% | 33.0% | **37.4%** |
| Avg Winner % | **+1.11%** | +0.92% | +0.98% |
| Avg Loser % | -0.61% | -0.51% | -0.61% |
| **SQN** | **-0.67** | -2.34 | -0.87 |
| **Profit Factor** | **0.81** | 0.44 | 0.76 |
| Max Drawdown % | **-21.39%** | **-21.39%** | **-21.39%** |
| **Trades >10% PnL** | **5** | 2 | **5** |
| Avg Winner Hold (s) | 18.6s | 11.8s | 21.8s |
| Avg Loser Hold (s) | 20.2s | 11.2s | 20.3s |
| Slippage Cost % | 2731.79% | 2912.55% | 2678.58% |
| Reaper Kills (120s) | 2 | 1 | 2 |
| Exp. Gap Kills (45s) | 936 | 507 | 956 |
| Errors | 0 | 0 | 0 |

## Duration Analysis

Average hold time for **winning trades** by mode:

- **Mode A** (Clock-Watcher): Winners 18.6s / Losers 20.2s
- **Mode B** (Volume-Dilator): Winners 11.8s / Losers 11.2s
- **Mode C** (Two-Stage Runner): Winners 21.8s / Losers 20.3s

## Efficiency Analysis

- **Mode A**: Gross PnL=-107.32%, Slippage=2731.79%, Net=-2839.11%
- **Mode B**: Gross PnL=-390.36%, Slippage=2912.55%, Net=-3302.90%
- **Mode C**: Gross PnL=-134.09%, Slippage=2678.58%, Net=-2812.67%

## Winner Declaration

- Mode A: Score = 0.4×SQN(-0.67) + 0.3×PF(0.81) + 0.2×WR(37.3%) + 0.1×BigTrades(5) = **0.551**
- Mode B: Score = 0.4×SQN(-2.34) + 0.3×PF(0.44) + 0.2×WR(33.0%) + 0.1×BigTrades(2) = **-0.535**
- Mode C: Score = 0.4×SQN(-0.87) + 0.3×PF(0.76) + 0.2×WR(37.4%) + 0.1×BigTrades(5) = **0.456**

### **WINNER: Mode A (Clock-Watcher)**

## Raw Aggregates (JSON)

```json
{
  "A": {
    "mode": "A",
    "mode_name": "Clock-Watcher",
    "n_events": 194,
    "events_with_trades": 139,
    "total_entries": 8053,
    "avg_entries_per_event": 57.935251798561154,
    "total_pnl_pct": -107.31673164362326,
    "avg_pnl_pct": -0.7720628175800234,
    "median_pnl_pct": -0.8602580873682486,
    "std_pnl_pct": 11.557315853944923,
    "sqn": -0.6680295211595267,
    "profit_factor": 0.8117536901274093,
    "avg_win_rate_pct": 37.26538757131115,
    "avg_winner_pct": 1.1147020338084352,
    "avg_loser_pct": -0.6142884656233871,
    "max_drawdown_pct": -21.3876207963434,
    "trades_over_10pct": 5,
    "avg_winner_hold_sec": 18.636096736522997,
    "avg_loser_hold_sec": 20.220361896343405,
    "total_slippage_cost_pct": 2731.790476922714,
    "reaper_kills_120s": 2,
    "expectation_gap_kills_45s": 936,
    "n_errors": 0
  },
  "B": {
    "mode": "B",
    "mode_name": "Volume-Dilator",
    "n_events": 194,
    "events_with_trades": 139,
    "total_entries": 8391,
    "avg_entries_per_event": 60.36690647482014,
    "total_pnl_pct": -390.35770034313543,
    "avg_pnl_pct": -2.8083287794470175,
    "median_pnl_pct": -1.5149262007973063,
    "std_pnl_pct": 12.025946470491185,
    "sqn": -2.3352247462085325,
    "profit_factor": 0.44174437496256874,
    "avg_win_rate_pct": 33.039069032131714,
    "avg_winner_pct": 0.9225521065208214,
    "avg_loser_pct": -0.5061496403383466,
    "max_drawdown_pct": -21.3876207963434,
    "trades_over_10pct": 2,
    "avg_winner_hold_sec": 11.843160716397835,
    "avg_loser_hold_sec": 11.198292743925492,
    "total_slippage_cost_pct": 2912.5472283196764,
    "reaper_kills_120s": 1,
    "expectation_gap_kills_45s": 507,
    "n_errors": 0
  },
  "C": {
    "mode": "C",
    "mode_name": "Two-Stage Runner",
    "n_events": 194,
    "events_with_trades": 139,
    "total_entries": 8048,
    "avg_entries_per_event": 57.89928057553957,
    "total_pnl_pct": -134.0858063103788,
    "avg_pnl_pct": -0.9646460885638763,
    "median_pnl_pct": -0.8602580873682486,
    "std_pnl_pct": 11.082252519758278,
    "sqn": -0.870442256070264,
    "profit_factor": 0.7636127211300202,
    "avg_win_rate_pct": 37.39957884386072,
    "avg_winner_pct": 0.9771797778049371,
    "avg_loser_pct": -0.6063179366539211,
    "max_drawdown_pct": -21.3876207963434,
    "trades_over_10pct": 5,
    "avg_winner_hold_sec": 21.811789784777133,
    "avg_loser_hold_sec": 20.26991182742165,
    "total_slippage_cost_pct": 2678.5841337946986,
    "reaper_kills_120s": 2,
    "expectation_gap_kills_45s": 956,
    "n_errors": 0
  }
}

## Related

- [[v5_3_Final_Report]] — v5.3 Temporal Beta Hybrid report (follow-on run)
- [[V5 Backtest Runner]] — runner that produced this output
- [[README]] — brainstorm directory guide
- [[00-Index]] — vault index
```