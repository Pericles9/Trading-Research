"""
AlphaMomentum Phase 4 — The Campaign Backtest
===============================================
Regime-aware backtesting: Inference → Filtering → Campaign Strategy → Bake-Off

Pipeline:
  1. Inference Engine: Score all events via XGBoost → prime_candidates.parquet
  2. Campaign Strategy: Elastic Leash, Vector Check, Pyramiding
  3. Bake-Off: Baseline vs Filtered vs Campaign on 523 test events
  4. Visualization: Hockey Stick equity curve comparison

Requires: xgboost, pandas, numpy, numba, matplotlib
"""

import os, sys, time, warnings, json
import datetime as dt
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional

import numpy as np
import pandas as pd
from numba import njit

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec

warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=DeprecationWarning)

# ─── Configuration ───────────────────────────────────────────────────────────
ROOT   = Path(r"D:\Mom_db")
DATA   = ROOT / "data"
PHASE2 = ROOT / "research" / "phase_2_signal_forge"
PHASE3 = ROOT / "research" / "phase_3_alpha_hunter"
OUT    = ROOT / "research" / "phase_4_campaign"
PLOTS  = OUT / "plots"
PLOTS.mkdir(parents=True, exist_ok=True)

# Hawkes parameters (must match Phase 2/3)
HAWKES_ALPHA     = 0.8
HAWKES_BETA      = 1.0
HAWKES_FREEZE_SEC = 5.0

# Strategy parameters
BASE_BETA         = 1.0        # Standard Hawkes decay
ALPHA_BETA_MULT   = 0.5        # Slow decay multiplier for high-score events
PYRAMID_THRESHOLD = 0.02       # +2% move triggers Level 2
PYRAMID_ADD_PCT   = 0.50       # Add 50% size at Level 2
HIGH_SCORE_ATR_MULT = 3.5      # Elastic leash: high score → wide stop
LOW_SCORE_ATR_MULT  = 1.5      # Elastic leash: low score → tight stop
INITIAL_CAPITAL     = 100_000  # $100k starting capital
POSITION_SIZE_PCT   = 0.02     # 2% of capital per trade (base)

# Time windows
FLIP_START_ET = "09:30:00"     # RTH open
FLIP_END_ET   = "09:45:00"     # End of FLIP window
SIM_END_ET    = "10:30:00"     # 1-hour simulation window

# ─── Logging ─────────────────────────────────────────────────────────────────
LOG_LINES: list[str] = []
T0 = time.perf_counter()

def log(msg: str):
    elapsed = time.perf_counter() - T0
    line = f"[{elapsed:8.1f}s] {msg}"
    LOG_LINES.append(line)
    print(line)


# ═══════════════════════════════════════════════════════════════════════════════
#  Utility: ET Timestamp Conversion
# ═══════════════════════════════════════════════════════════════════════════════
def is_dst(date_str: str) -> bool:
    d = dt.date.fromisoformat(date_str)
    year = d.year
    mar1 = dt.date(year, 3, 1)
    mar_second_sun = mar1 + dt.timedelta(days=(6 - mar1.weekday()) % 7 + 7)
    nov1 = dt.date(year, 11, 1)
    nov_first_sun = nov1 + dt.timedelta(days=(6 - nov1.weekday()) % 7)
    return mar_second_sun <= d < nov_first_sun

def utc_to_et_offset_hours(date_str: str) -> int:
    return 4 if is_dst(date_str) else 5


# ═══════════════════════════════════════════════════════════════════════════════
#  Halt-Stitched Hawkes Kernel (from Phase 2/3)
# ═══════════════════════════════════════════════════════════════════════════════
@njit(cache=True)
def _hawkes_scan_halt_aware(dt_arr, alpha, beta, mu, halt_threshold):
    n = len(dt_arr) + 1
    intensity = np.empty(n, dtype=np.float64)
    S = 0.0
    intensity[0] = mu
    for i in range(1, n):
        d = dt_arr[i - 1]
        if d > halt_threshold:
            S = S + 1.0
        else:
            S = np.exp(-beta * d) * S + 1.0
        intensity[i] = mu + alpha * S
    return intensity


def hawkes_intensity(timestamps_sec, alpha=HAWKES_ALPHA, beta=HAWKES_BETA,
                     freeze_thresh=HAWKES_FREEZE_SEC):
    """Compute halt-stitched Hawkes intensity array."""
    n = len(timestamps_sec)
    if n < 2:
        return np.zeros(n)
    dt_arr = np.diff(timestamps_sec).astype(np.float64)
    dt_arr = np.maximum(dt_arr, 1e-9)
    active_mask = dt_arr <= freeze_thresh
    active_dur = dt_arr[active_mask].sum() if active_mask.any() else 1e-6
    active_n = active_mask.sum() + 1
    mu = active_n / max(active_dur, 1e-6)
    return _hawkes_scan_halt_aware(dt_arr, alpha, beta, mu, freeze_thresh)


# ═══════════════════════════════════════════════════════════════════════════════
#  1. INFERENCE ENGINE
# ═══════════════════════════════════════════════════════════════════════════════
def run_inference_engine():
    """
    Load XGBoost model, score all events, identify prime candidates (Top 25%).
    Returns the scored DataFrame and the test-set subset.
    """
    import xgboost as xgb

    log("═══ INFERENCE ENGINE ═══")

    # Load model
    model = xgb.Booster()
    model.load_model(str(PHASE3 / "xgb_regime_model.json"))
    feature_names = model.feature_names
    log(f"  Loaded XGBoost model ({len(feature_names)} features)")

    # Load fused dataset (has all features + forward targets)
    fused = pd.read_parquet(PHASE3 / "fused_dataset.parquet")
    log(f"  Loaded fused dataset: {len(fused):,} rows")

    # ── Score all events ─────────────────────────────────────────────────
    X_all = fused[feature_names].copy()
    dmat = xgb.DMatrix(X_all, feature_names=feature_names)
    fused["predicted_contagion_score"] = model.predict(dmat)
    log(f"  Scored {len(fused):,} events")
    log(f"  Score stats: min={fused['predicted_contagion_score'].min():.0f}, "
        f"max={fused['predicted_contagion_score'].max():.0f}, "
        f"median={fused['predicted_contagion_score'].median():.0f}")

    # ── Filter: Top 25th percentile ──────────────────────────────────────
    threshold_75 = fused["predicted_contagion_score"].quantile(0.75)
    prime = fused[fused["predicted_contagion_score"] >= threshold_75].copy()
    log(f"  Top 25% threshold: score >= {threshold_75:.0f}")
    log(f"  Prime candidates: {len(prime):,} events")

    # Save
    prime.to_parquet(OUT / "prime_candidates.parquet", index=False)
    fused.to_parquet(OUT / "scored_universe.parquet", index=False)
    log(f"  Saved prime_candidates.parquet and scored_universe.parquet")

    # ── Identify test set (temporal 80/20 split matching Phase 3) ────────
    valid = fused[fused["y_contagion"].notna()].sort_values("date").reset_index(drop=True)
    split_idx = int(len(valid) * 0.8)
    test_set = valid.iloc[split_idx:].copy().reset_index(drop=True)
    log(f"  Test set: {len(test_set)} events "
        f"({test_set['date'].min()} → {test_set['date'].max()})")

    # Test set stats
    test_threshold = test_set["predicted_contagion_score"].quantile(0.75)
    test_prime = test_set[test_set["predicted_contagion_score"] >= test_threshold]
    log(f"  Test prime (top 25%): {len(test_prime)} events (threshold={test_threshold:.0f})")

    return fused, test_set, threshold_75


# ═══════════════════════════════════════════════════════════════════════════════
#  2. CAMPAIGN STRATEGY — Tick-Level Trade Simulation
# ═══════════════════════════════════════════════════════════════════════════════
@dataclass
class TradeResult:
    """Result of simulating one trade event."""
    ticker: str = ""
    date: str = ""
    gap_rank: int = 0
    score: float = 0.0
    strategy: str = ""

    # Entry
    entered: bool = False
    entry_price: float = 0.0
    entry_time: str = ""
    entry_size_shares: float = 0.0

    # Pyramid
    pyramided: bool = False
    pyramid_price: float = 0.0
    pyramid_shares: float = 0.0

    # Exit
    exit_price: float = 0.0
    exit_time: str = ""
    exit_reason: str = ""

    # P&L
    pnl_dollars: float = 0.0
    return_pct: float = 0.0
    max_favorable: float = 0.0
    max_adverse: float = 0.0

    # Context
    vwap_at_entry: float = 0.0
    cvd_at_entry: float = 0.0
    atr_14: float = 0.0
    hawkes_entry_intensity: float = 0.0
    stop_loss_price: float = 0.0


def load_event_ticks(ticker: str, date_str: str) -> Optional[pd.DataFrame]:
    """Load and prepare tick data for a single event."""
    filt_dirs = os.listdir(DATA / "filtered")
    prefix = f"{ticker}_{date_str}_"
    matches = [d for d in filt_dirs if d.startswith(prefix)]
    if not matches:
        return None

    trades_file = DATA / "filtered" / matches[0] / "trades.parquet"
    if not trades_file.exists():
        return None

    try:
        tdf = pd.read_parquet(trades_file, columns=["sip_timestamp", "price", "size"])
    except Exception:
        return None

    if len(tdf) < 50:
        return None

    et_offset = utc_to_et_offset_hours(date_str)
    tdf = tdf.sort_values("sip_timestamp").reset_index(drop=True)
    tdf["dt_utc"] = pd.to_datetime(tdf["sip_timestamp"], unit="ns")
    tdf["dt_et"] = tdf["dt_utc"] - pd.Timedelta(hours=et_offset)
    return tdf


def compute_vwap(tdf: pd.DataFrame, up_to_idx: int) -> float:
    """Compute VWAP from start of day up to given index."""
    slc = tdf.iloc[:up_to_idx + 1]
    pv = (slc["price"] * slc["size"]).sum()
    vol = slc["size"].sum()
    return pv / vol if vol > 0 else slc["price"].iloc[-1]


def compute_atr_from_ticks(tdf: pd.DataFrame, date_str: str, n_bars: int = 14) -> float:
    """
    Compute pseudo-ATR from 1-minute OHLC bars in the FLIP window.
    Returns ATR in price units.
    """
    flip_start = pd.Timestamp(f"{date_str} 09:30:00")
    flip_end = pd.Timestamp(f"{date_str} 09:45:00")

    flip_ticks = tdf[(tdf["dt_et"] >= flip_start) & (tdf["dt_et"] <= flip_end)].copy()
    if len(flip_ticks) < 10:
        # Fallback: use simple std of recent prices
        return tdf["price"].tail(100).std() * 2

    # Build 1-minute bars
    flip_ticks = flip_ticks.set_index("dt_et")
    bars = flip_ticks["price"].resample("1min").ohlc().dropna()
    if len(bars) < 3:
        return flip_ticks["price"].std() * 2

    # True Range = max(H-L, |H-Pc|, |L-Pc|)
    highs = bars["high"].values
    lows = bars["low"].values
    closes = bars["close"].values

    trs = []
    for i in range(1, len(bars)):
        tr = max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i - 1]),
            abs(lows[i] - closes[i - 1])
        )
        trs.append(tr)

    if not trs:
        return flip_ticks["price"].std() * 2

    # ATR = simple average of last n TRs
    atr = np.mean(trs[-min(n_bars, len(trs)):])
    return max(atr, 0.01)  # floor


def compute_cvd_at_time(tdf: pd.DataFrame, up_to_idx: int) -> float:
    """
    Simple CVD approximation using tick rule:
    price_change > 0 → buy, < 0 → sell, == 0 → previous direction.
    """
    slc = tdf.iloc[:up_to_idx + 1]
    prices = slc["price"].values
    sizes = slc["size"].values

    if len(prices) < 2:
        return 0.0

    cvd = 0.0
    direction = 1  # start as buy
    for i in range(1, len(prices)):
        diff = prices[i] - prices[i - 1]
        if diff > 0:
            direction = 1
        elif diff < 0:
            direction = -1
        cvd += direction * sizes[i]

    return cvd


def simulate_trade_baseline(event: pd.Series, tdf: pd.DataFrame,
                            capital: float) -> TradeResult:
    """
    BASELINE strategy: Trade everything. Simple entry at FLIP end,
    fixed 2x ATR stop, exit at sim_end or stop hit.
    No filtering, no pyramiding, no regime awareness.
    """
    result = TradeResult(
        ticker=event["ticker"], date=event["date"],
        gap_rank=int(event["gap_rank"]), score=event.get("predicted_contagion_score", 0),
        strategy="baseline"
    )

    date_str = event["date"]
    flip_end = pd.Timestamp(f"{date_str} 09:45:00")
    sim_end  = pd.Timestamp(f"{date_str} {SIM_END_ET}")

    # Find entry point: first trade after FLIP end
    post_flip = tdf[tdf["dt_et"] >= flip_end]
    if len(post_flip) < 10:
        return result

    entry_idx = post_flip.index[0]
    entry_price = tdf.loc[entry_idx, "price"]
    entry_time = str(tdf.loc[entry_idx, "dt_et"])

    if entry_price <= 0:
        return result

    # ATR for stop
    atr = compute_atr_from_ticks(tdf, date_str)

    # Fixed 2.0x ATR stop (baseline)
    stop_loss = entry_price - 2.0 * atr

    # Position sizing: 2% of capital
    shares = max(1, int((capital * POSITION_SIZE_PCT) / entry_price))

    result.entered = True
    result.entry_price = entry_price
    result.entry_time = entry_time
    result.entry_size_shares = shares
    result.atr_14 = atr
    result.stop_loss_price = stop_loss

    # Simulate forward
    sim_ticks = tdf[(tdf.index > entry_idx) & (tdf["dt_et"] <= sim_end)]
    if len(sim_ticks) == 0:
        result.exit_price = entry_price
        result.exit_reason = "no_ticks"
        return result

    max_price = entry_price
    min_price = entry_price

    for idx, row in sim_ticks.iterrows():
        price = row["price"]
        max_price = max(max_price, price)
        min_price = min(min_price, price)

        # Stop loss hit
        if price <= stop_loss:
            result.exit_price = stop_loss
            result.exit_time = str(row["dt_et"])
            result.exit_reason = "stop_loss"
            break
    else:
        # Time exit
        result.exit_price = sim_ticks.iloc[-1]["price"]
        result.exit_time = str(sim_ticks.iloc[-1]["dt_et"])
        result.exit_reason = "time_exit"

    result.max_favorable = (max_price - entry_price) / entry_price
    result.max_adverse = (min_price - entry_price) / entry_price
    result.pnl_dollars = (result.exit_price - entry_price) * shares
    result.return_pct = (result.exit_price - entry_price) / entry_price

    return result


def simulate_trade_filtered(event: pd.Series, tdf: pd.DataFrame,
                            capital: float) -> TradeResult:
    """
    FILTERED strategy: Trade only top-25% scored events.
    Same logic as baseline (no strategy changes, just filtering).
    """
    result = simulate_trade_baseline(event, tdf, capital)
    result.strategy = "filtered"
    return result


def simulate_trade_campaign(event: pd.Series, tdf: pd.DataFrame,
                            capital: float, score_threshold: float) -> TradeResult:
    """
    CAMPAIGN strategy: The full "Wartime" algorithm.
    
    - Vector Check: Price > VWAP AND CVD > 0 before entry
    - Elastic Leash: Stop width based on regime score
    - Pyramiding: +50% position if +2% AND gap_rank == 1
    - Adjusted beta: Slower Hawkes decay for high-score events
    """
    result = TradeResult(
        ticker=event["ticker"], date=event["date"],
        gap_rank=int(event["gap_rank"]), score=event.get("predicted_contagion_score", 0),
        strategy="campaign"
    )

    date_str = event["date"]
    score = event.get("predicted_contagion_score", 0)
    is_high_score = score >= score_threshold

    flip_end = pd.Timestamp(f"{date_str} 09:45:00")
    sim_end  = pd.Timestamp(f"{date_str} {SIM_END_ET}")

    # ── Pre-entry window: 09:45 → 09:50 (5-min vector check window) ─────
    vector_window_end = pd.Timestamp(f"{date_str} 09:50:00")
    post_flip = tdf[(tdf["dt_et"] >= flip_end) & (tdf["dt_et"] <= vector_window_end)]

    if len(post_flip) < 10:
        result.exit_reason = "insufficient_ticks"
        return result

    # ── VECTOR CHECK: wait for Price > VWAP AND CVD > 0 ─────────────────
    entry_found = False
    entry_idx = None

    for scan_idx in post_flip.index:
        price = tdf.loc[scan_idx, "price"]
        vwap = compute_vwap(tdf, scan_idx)
        cvd = compute_cvd_at_time(tdf, scan_idx)

        if price > vwap and cvd > 0:
            entry_found = True
            entry_idx = scan_idx
            result.vwap_at_entry = vwap
            result.cvd_at_entry = cvd
            break

    if not entry_found:
        result.exit_reason = "vector_check_failed"
        return result

    entry_price = tdf.loc[entry_idx, "price"]
    entry_time = str(tdf.loc[entry_idx, "dt_et"])

    if entry_price <= 0:
        return result

    # ── ATR computation ──────────────────────────────────────────────────
    atr = compute_atr_from_ticks(tdf, date_str)

    # ── Elastic Leash: stop width based on score ─────────────────────────
    if is_high_score:
        atr_mult = HIGH_SCORE_ATR_MULT   # 3.5x ATR — loose leash
    else:
        atr_mult = LOW_SCORE_ATR_MULT     # 1.5x ATR — tight leash

    stop_loss = entry_price - atr_mult * atr

    # ── Position sizing ──────────────────────────────────────────────────
    base_shares = max(1, int((capital * POSITION_SIZE_PCT) / entry_price))
    total_shares = base_shares

    result.entered = True
    result.entry_price = entry_price
    result.entry_time = entry_time
    result.entry_size_shares = base_shares
    result.atr_14 = atr
    result.stop_loss_price = stop_loss

    # ── Compute Hawkes intensity at entry for logging ────────────────────
    pre_entry = tdf[tdf.index <= entry_idx]
    if len(pre_entry) > 10:
        ts_sec = (pre_entry["dt_et"] - pre_entry["dt_et"].iloc[0]).dt.total_seconds().values

        # Adjusted beta for high-score events
        beta_adj = BASE_BETA * ALPHA_BETA_MULT if is_high_score else BASE_BETA
        lam = hawkes_intensity(ts_sec, alpha=HAWKES_ALPHA, beta=beta_adj)
        result.hawkes_entry_intensity = float(lam[-1])

    # ── Simulate forward with pyramiding ─────────────────────────────────
    sim_ticks = tdf[(tdf.index > entry_idx) & (tdf["dt_et"] <= sim_end)]
    if len(sim_ticks) == 0:
        result.exit_price = entry_price
        result.exit_reason = "no_ticks"
        return result

    max_price = entry_price
    min_price = entry_price
    pyramid_triggered = False
    avg_entry = entry_price

    for idx, row in sim_ticks.iterrows():
        price = row["price"]
        max_price = max(max_price, price)
        min_price = min(min_price, price)

        # ── PYRAMID CHECK: +2% AND gap_rank == 1 ────────────────────
        if (not pyramid_triggered and
            event["gap_rank"] == 1 and
            price >= entry_price * (1 + PYRAMID_THRESHOLD)):

            pyramid_shares = int(base_shares * PYRAMID_ADD_PCT)
            if pyramid_shares > 0:
                pyramid_triggered = True
                # Update average entry
                old_cost = avg_entry * total_shares
                new_cost = price * pyramid_shares
                total_shares += pyramid_shares
                avg_entry = (old_cost + new_cost) / total_shares

                result.pyramided = True
                result.pyramid_price = price
                result.pyramid_shares = pyramid_shares

                # Trail the stop up: maintain ATR distance from new entry
                stop_loss = max(stop_loss, price - atr_mult * atr)

        # ── STOP LOSS CHECK ──────────────────────────────────────────
        if price <= stop_loss:
            result.exit_price = stop_loss
            result.exit_time = str(row["dt_et"])
            result.exit_reason = "elastic_stop"
            break
    else:
        # Time exit
        result.exit_price = sim_ticks.iloc[-1]["price"]
        result.exit_time = str(sim_ticks.iloc[-1]["dt_et"])
        result.exit_reason = "time_exit"

    result.entry_size_shares = total_shares  # total including pyramid
    result.max_favorable = (max_price - entry_price) / entry_price
    result.max_adverse = (min_price - entry_price) / entry_price
    result.pnl_dollars = (result.exit_price - avg_entry) * total_shares
    result.return_pct = (result.exit_price - avg_entry) / avg_entry

    return result


# ═══════════════════════════════════════════════════════════════════════════════
#  3. THE BAKE-OFF
# ═══════════════════════════════════════════════════════════════════════════════
def run_bakeoff(test_set: pd.DataFrame, score_threshold_75: float):
    """
    Run three simulations on the same 523 test events:
      1. Baseline: Trade everything, basic stops
      2. Filtered: Trade only Top 25% scores, same basic logic
      3. Campaign: Top 25% + pyramiding + elastic leash + vector check
    """
    log("═══ THE BAKE-OFF ═══")

    # Pre-build directory lookup for speed
    filt_dirs = set(os.listdir(DATA / "filtered"))

    def find_dir(ticker, date):
        prefix = f"{ticker}_{date}_"
        return next((d for d in filt_dirs if d.startswith(prefix)), None)

    # Test-set top 25% threshold (within test set)
    test_threshold = test_set["predicted_contagion_score"].quantile(0.75)
    is_prime = test_set["predicted_contagion_score"] >= test_threshold
    log(f"  Test set: {len(test_set)} events")
    log(f"  Test top-25% threshold: {test_threshold:.0f}")
    log(f"  Prime candidates in test: {is_prime.sum()}")

    # Results containers
    baseline_results = []
    filtered_results = []
    campaign_results = []

    capital = INITIAL_CAPITAL
    processed = 0
    skipped = 0

    for i, (_, event) in enumerate(test_set.iterrows()):
        ticker = event["ticker"]
        date_str = event["date"]

        # Load tick data (shared across all three strategies)
        fdir = find_dir(ticker, date_str)
        if fdir is None:
            skipped += 1
            continue

        tdf = load_event_ticks(ticker, date_str)
        if tdf is None:
            skipped += 1
            continue

        # 1) BASELINE: trade everything
        bl = simulate_trade_baseline(event, tdf, capital)
        baseline_results.append(bl)

        # 2) FILTERED: only trade top 25%
        if event["predicted_contagion_score"] >= test_threshold:
            fl = simulate_trade_filtered(event, tdf, capital)
            filtered_results.append(fl)

        # 3) CAMPAIGN: top 25% + full wartime algorithm
        if event["predicted_contagion_score"] >= test_threshold:
            cp = simulate_trade_campaign(event, tdf, capital, test_threshold)
            campaign_results.append(cp)

        processed += 1
        if (processed + skipped) % 100 == 0:
            rate = (processed + skipped) / max(time.perf_counter() - T0, 0.1)
            remaining = len(test_set) - processed - skipped
            eta = remaining / max(rate, 0.01)
            log(f"    {processed + skipped}/{len(test_set)} "
                f"(processed={processed}, skip={skipped}) ETA={eta:.0f}s")

    log(f"  Bake-off complete: {processed} processed, {skipped} skipped")
    log(f"  Baseline trades: {sum(1 for r in baseline_results if r.entered)}")
    log(f"  Filtered trades: {sum(1 for r in filtered_results if r.entered)}")
    log(f"  Campaign trades: {sum(1 for r in campaign_results if r.entered)}")

    return baseline_results, filtered_results, campaign_results


# ═══════════════════════════════════════════════════════════════════════════════
#  Analysis & Metrics
# ═══════════════════════════════════════════════════════════════════════════════
def compute_strategy_metrics(results: list[TradeResult], label: str) -> dict:
    """Compute comprehensive performance metrics for a strategy."""
    entered = [r for r in results if r.entered]
    if not entered:
        return {"label": label, "n_trades": 0}

    pnls = np.array([r.pnl_dollars for r in entered])
    returns = np.array([r.return_pct for r in entered])
    cum_pnl = np.cumsum(pnls)

    winners = pnls > 0
    losers = pnls < 0

    # Max drawdown
    peak = np.maximum.accumulate(cum_pnl)
    drawdown = cum_pnl - peak
    max_dd = drawdown.min()

    # Profit factor
    gross_profit = pnls[winners].sum() if winners.any() else 0
    gross_loss = abs(pnls[losers].sum()) if losers.any() else 1e-6

    # Sharpe (annualized, assuming ~252 trading days)
    if returns.std() > 0:
        sharpe = (returns.mean() / returns.std()) * np.sqrt(252)
    else:
        sharpe = 0.0

    metrics = {
        "label": label,
        "n_events": len(results),
        "n_trades": len(entered),
        "win_rate": winners.sum() / len(entered),
        "total_pnl": pnls.sum(),
        "avg_pnl": pnls.mean(),
        "median_pnl": np.median(pnls),
        "avg_return": returns.mean(),
        "median_return": np.median(returns),
        "best_trade": pnls.max(),
        "worst_trade": pnls.min(),
        "max_drawdown": max_dd,
        "profit_factor": gross_profit / max(gross_loss, 1e-6),
        "sharpe_ratio": sharpe,
        "gross_profit": gross_profit,
        "gross_loss": gross_loss,
        "n_pyramided": sum(1 for r in entered if r.pyramided),
        "n_stopped": sum(1 for r in entered if "stop" in r.exit_reason),
        "n_time_exit": sum(1 for r in entered if r.exit_reason == "time_exit"),
        "cum_pnl": cum_pnl,
        "pnls": pnls,
        "returns": returns,
    }
    return metrics


def print_metrics_table(metrics_list: list[dict]):
    """Print a formatted comparison table."""
    log(f"\n{'═'*85}")
    log(f"{'BAKE-OFF RESULTS':^85}")
    log(f"{'═'*85}")

    headers = ["Metric", "Baseline", "Filtered", "Campaign"]
    log(f"  {'Metric':<28} {'Baseline':>16} {'Filtered':>16} {'Campaign':>16}")
    log(f"  {'─'*28} {'─'*16} {'─'*16} {'─'*16}")

    rows = [
        ("Trades Entered", "n_trades", "d"),
        ("Win Rate", "win_rate", ".1%"),
        ("Total PnL ($)", "total_pnl", ",.0f"),
        ("Avg PnL ($)", "avg_pnl", ",.2f"),
        ("Median PnL ($)", "median_pnl", ",.2f"),
        ("Avg Return", "avg_return", ".2%"),
        ("Best Trade ($)", "best_trade", ",.0f"),
        ("Worst Trade ($)", "worst_trade", ",.0f"),
        ("Max Drawdown ($)", "max_drawdown", ",.0f"),
        ("Profit Factor", "profit_factor", ".2f"),
        ("Sharpe Ratio", "sharpe_ratio", ".2f"),
        ("Pyramided Trades", "n_pyramided", "d"),
        ("Stop-Loss Exits", "n_stopped", "d"),
        ("Time Exits", "n_time_exit", "d"),
    ]

    for row_label, key, fmt in rows:
        vals = []
        for m in metrics_list:
            v = m.get(key, 0)
            if v == 0 and key not in m:
                vals.append("—")
            else:
                vals.append(f"{v:{fmt}}")

        log(f"  {row_label:<28} {vals[0]:>16} {vals[1]:>16} {vals[2]:>16}")

    log(f"  {'═'*76}")


# ═══════════════════════════════════════════════════════════════════════════════
#  4. VISUALIZATION: The "Hockey Stick"
# ═══════════════════════════════════════════════════════════════════════════════
def generate_hockey_stick(baseline_m, filtered_m, campaign_m):
    """
    Generate the cumulative PnL comparison ("Hockey Stick") chart.
    """
    log("Generating Hockey Stick visualization …")

    fig = plt.figure(figsize=(24, 16))
    gs = GridSpec(2, 2, figure=fig, hspace=0.3, wspace=0.25)

    # ── Panel 1: Cumulative PnL (The Hockey Stick) ───────────────────────
    ax1 = fig.add_subplot(gs[0, :])

    for m, color, ls in [(baseline_m, "#78909C", "-"),
                          (filtered_m, "#1565C0", "-"),
                          (campaign_m, "#E91E63", "-")]:
        if m["n_trades"] > 0:
            cum = m["cum_pnl"]
            x = np.arange(len(cum))
            ax1.plot(x, cum, color=color, linewidth=2.5 if m == campaign_m else 1.8,
                     linestyle=ls, label=f"{m['label']} (PnL=${cum[-1]:,.0f})",
                     alpha=0.9 if m == campaign_m else 0.7)
            # Fill positive area
            ax1.fill_between(x, 0, cum, alpha=0.08, color=color)

    ax1.axhline(0, color="gray", linewidth=0.8, linestyle="--", alpha=0.5)
    ax1.set_xlabel("Trade Number", fontsize=12)
    ax1.set_ylabel("Cumulative PnL ($)", fontsize=12)
    ax1.set_title("Phase 4 — The Hockey Stick: Campaign vs Baseline",
                  fontsize=16, fontweight="bold")
    ax1.legend(fontsize=12, loc="upper left")
    ax1.grid(alpha=0.15)

    # Add annotations for key points
    if campaign_m["n_trades"] > 0:
        cum = campaign_m["cum_pnl"]
        peak_idx = np.argmax(cum)
        ax1.annotate(f"Peak: ${cum[peak_idx]:,.0f}",
                    xy=(peak_idx, cum[peak_idx]),
                    xytext=(peak_idx + 10, cum[peak_idx] * 1.1),
                    fontsize=10, color="#E91E63",
                    arrowprops=dict(arrowstyle="->", color="#E91E63", lw=1.5))

    # ── Panel 2: Trade-by-Trade Returns Distribution ─────────────────────
    ax2 = fig.add_subplot(gs[1, 0])

    for m, color, label in [(baseline_m, "#78909C", "Baseline"),
                              (filtered_m, "#1565C0", "Filtered"),
                              (campaign_m, "#E91E63", "Campaign")]:
        if m["n_trades"] > 0:
            returns = m["returns"] * 100  # to percent
            returns_clip = np.clip(returns, -30, 50)
            ax2.hist(returns_clip, bins=40, alpha=0.4, color=color, label=label,
                     edgecolor=color, linewidth=0.5)

    ax2.axvline(0, color="black", linewidth=1, linestyle="--", alpha=0.5)
    ax2.set_xlabel("Trade Return (%)", fontsize=11)
    ax2.set_ylabel("Count", fontsize=11)
    ax2.set_title("Return Distribution", fontsize=13, fontweight="bold")
    ax2.legend(fontsize=10)
    ax2.grid(alpha=0.15)

    # ── Panel 3: Performance Summary Bar Chart ───────────────────────────
    ax3 = fig.add_subplot(gs[1, 1])

    strategies = ["Baseline", "Filtered", "Campaign"]
    colors = ["#78909C", "#1565C0", "#E91E63"]

    metrics_bars = {
        "Total PnL ($k)": [m["total_pnl"] / 1000 for m in [baseline_m, filtered_m, campaign_m]],
        "Win Rate (%)": [m["win_rate"] * 100 for m in [baseline_m, filtered_m, campaign_m]],
        "Profit Factor": [min(m["profit_factor"], 5) for m in [baseline_m, filtered_m, campaign_m]],
        "Sharpe Ratio": [m["sharpe_ratio"] for m in [baseline_m, filtered_m, campaign_m]],
    }

    x = np.arange(len(strategies))
    width = 0.18
    offset = 0

    for metric_name, vals in metrics_bars.items():
        bars = ax3.bar(x + offset, vals, width, label=metric_name, alpha=0.85)
        offset += width

    ax3.set_xticks(x + width * 1.5)
    ax3.set_xticklabels(strategies, fontsize=11)
    ax3.set_title("Key Metrics Comparison", fontsize=13, fontweight="bold")
    ax3.legend(fontsize=9, loc="upper left")
    ax3.grid(axis="y", alpha=0.15)

    fig.savefig(PLOTS / "performance_comparison.png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    log(f"  Saved performance_comparison.png")


def generate_drawdown_chart(baseline_m, filtered_m, campaign_m):
    """Generate drawdown comparison chart."""
    log("Generating drawdown chart …")

    fig, ax = plt.subplots(figsize=(18, 6))

    for m, color in [(baseline_m, "#78909C"),
                      (filtered_m, "#1565C0"),
                      (campaign_m, "#E91E63")]:
        if m["n_trades"] > 0:
            cum = m["cum_pnl"]
            peak = np.maximum.accumulate(cum)
            dd = cum - peak
            ax.fill_between(np.arange(len(dd)), dd, 0, alpha=0.3, color=color,
                           label=f"{m['label']} (Max DD=${m['max_drawdown']:,.0f})")
            ax.plot(dd, color=color, linewidth=1.2, alpha=0.7)

    ax.set_xlabel("Trade Number", fontsize=12)
    ax.set_ylabel("Drawdown ($)", fontsize=12)
    ax.set_title("Drawdown Comparison", fontsize=14, fontweight="bold")
    ax.legend(fontsize=11)
    ax.grid(alpha=0.15)

    fig.savefig(PLOTS / "drawdown_comparison.png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    log(f"  Saved drawdown_comparison.png")


def generate_score_vs_return_chart(test_set: pd.DataFrame):
    """Show predicted contagion score vs actual 15m return."""
    log("Generating score vs return chart …")

    valid = test_set.dropna(subset=["predicted_contagion_score", "return_15m"])
    if len(valid) < 10:
        log("  Insufficient data")
        return

    fig, axes = plt.subplots(1, 2, figsize=(20, 8))

    # Panel 1: Scatter
    ax1 = axes[0]
    scores = valid["predicted_contagion_score"].values
    returns = valid["return_15m"].values * 100  # percent

    colors = np.where(returns > 0, "#4CAF50", "#E91E63")
    ax1.scatter(scores, returns, c=colors, s=15, alpha=0.5)

    # Top-25% threshold
    threshold = np.percentile(scores, 75)
    ax1.axvline(threshold, color="gold", linewidth=2, linestyle="--",
               label=f"Top 25% Threshold: {threshold:.0f}")

    ax1.set_xlabel("Predicted Contagion Score", fontsize=12)
    ax1.set_ylabel("15-min Return (%)", fontsize=12)
    ax1.set_title("Score vs Actual Return", fontsize=14, fontweight="bold")
    ax1.legend(fontsize=11)
    ax1.grid(alpha=0.15)

    # Panel 2: Score quintile boxplot
    ax2 = axes[1]
    valid_copy = valid.copy()
    valid_copy["score_quintile"] = pd.qcut(valid_copy["predicted_contagion_score"],
                                            5, labels=["Q1\n(Low)", "Q2", "Q3", "Q4", "Q5\n(High)"])
    quintile_groups = [group["return_15m"].values * 100
                       for _, group in valid_copy.groupby("score_quintile", observed=True)]
    labels = ["Q1\n(Low)", "Q2", "Q3", "Q4", "Q5\n(High)"]

    bp = ax2.boxplot(quintile_groups, labels=labels, patch_artist=True,
                     showfliers=False)
    colors_bp = ["#E3F2FD", "#BBDEFB", "#90CAF9", "#42A5F5", "#1565C0"]
    for patch, color in zip(bp["boxes"], colors_bp):
        patch.set_facecolor(color)

    ax2.axhline(0, color="gray", linewidth=0.8, linestyle="--")
    ax2.set_xlabel("Score Quintile", fontsize=12)
    ax2.set_ylabel("15-min Return (%)", fontsize=12)
    ax2.set_title("Return by Score Quintile — Does the Score Predict?",
                  fontsize=14, fontweight="bold")
    ax2.grid(alpha=0.15)

    fig.tight_layout()
    fig.savefig(PLOTS / "score_vs_return.png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    log(f"  Saved score_vs_return.png")


# ═══════════════════════════════════════════════════════════════════════════════
#  Deliverable: Campaign_Report.md
# ═══════════════════════════════════════════════════════════════════════════════
def generate_campaign_report(baseline_m, filtered_m, campaign_m, test_set,
                              campaign_results):
    """Generate the campaign backtest report."""
    log("Writing Campaign_Report.md …")

    # Top campaign trades
    entered = [r for r in campaign_results if r.entered]
    entered.sort(key=lambda r: r.pnl_dollars, reverse=True)

    md = f"""# Phase 4 — The Campaign Backtest Report

## Executive Summary

> **Can regime-aware filtering and adaptive position management beat a naive "trade everything" baseline?**

This report compares three strategies on **{len(test_set)} test events**
({test_set['date'].min()} → {test_set['date'].max()}):

1. **Baseline**: Trade every event with fixed 2×ATR stops
2. **Filtered**: Trade only top-25% contagion scores (same logic)
3. **Campaign**: Top-25% + Vector Check + Elastic Leash + Pyramiding

---

## Bake-Off Results

| Metric | Baseline | Filtered | Campaign |
|---|---|---|---|
| Trades Entered | {baseline_m['n_trades']} | {filtered_m['n_trades']} | {campaign_m['n_trades']} |
| Win Rate | {baseline_m['win_rate']:.1%} | {filtered_m['win_rate']:.1%} | {campaign_m['win_rate']:.1%} |
| Total PnL | ${baseline_m['total_pnl']:,.0f} | ${filtered_m['total_pnl']:,.0f} | ${campaign_m['total_pnl']:,.0f} |
| Avg PnL/Trade | ${baseline_m['avg_pnl']:,.2f} | ${filtered_m['avg_pnl']:,.2f} | ${campaign_m['avg_pnl']:,.2f} |
| Profit Factor | {baseline_m['profit_factor']:.2f} | {filtered_m['profit_factor']:.2f} | {campaign_m['profit_factor']:.2f} |
| Sharpe Ratio | {baseline_m['sharpe_ratio']:.2f} | {filtered_m['sharpe_ratio']:.2f} | {campaign_m['sharpe_ratio']:.2f} |
| Max Drawdown | ${baseline_m['max_drawdown']:,.0f} | ${filtered_m['max_drawdown']:,.0f} | ${campaign_m['max_drawdown']:,.0f} |
| Pyramided Trades | — | — | {campaign_m['n_pyramided']} |

---

## Strategy Alpha Attribution

### 1. Filtering Effect (Baseline → Filtered)
"""
    # Compute alpha from filtering
    if baseline_m['n_trades'] > 0 and filtered_m['n_trades'] > 0:
        filter_pnl_improvement = filtered_m['total_pnl'] - (baseline_m['total_pnl'] * filtered_m['n_trades'] / baseline_m['n_trades'])
        filter_wr_delta = filtered_m['win_rate'] - baseline_m['win_rate']
        md += f"""
- **Win Rate Delta**: {filter_wr_delta:+.1%}
- **PnL per trade improvement**: ${filtered_m['avg_pnl'] - baseline_m['avg_pnl']:+,.2f}
- **Interpretation**: Removing the bottom 75% of events """
        if filtered_m['avg_pnl'] > baseline_m['avg_pnl']:
            md += "**improves** average trade quality.\n"
        else:
            md += "does not improve average trade quality in this test window.\n"

    md += """
### 2. Strategy Effect (Filtered → Campaign)
"""
    if filtered_m['n_trades'] > 0 and campaign_m['n_trades'] > 0:
        strat_wr_delta = campaign_m['win_rate'] - filtered_m['win_rate']
        strat_pnl_delta = campaign_m['avg_pnl'] - filtered_m['avg_pnl']
        md += f"""
- **Win Rate Delta**: {strat_wr_delta:+.1%}
- **PnL per trade improvement**: ${strat_pnl_delta:+,.2f}
- **Vector Check filtered out**: {len([r for r in campaign_results if r.exit_reason == 'vector_check_failed'])} events (falling knives avoided)
- **Trades pyramided**: {campaign_m['n_pyramided']} (rank #1 events with +2% move)
- **Elastic Stop exits**: {campaign_m['n_stopped']}
"""

    md += f"""
---

## Top Campaign Trades

| Ticker | Date | Rank | Score | Entry | Exit | Return | PnL | Pyramid | Exit Reason |
|---|---|---|---|---|---|---|---|---|---|
"""
    for r in entered[:15]:
        pyr = "Yes" if r.pyramided else "—"
        md += (f"| {r.ticker} | {r.date} | {r.gap_rank} | {r.score:.0f} "
               f"| ${r.entry_price:.2f} | ${r.exit_price:.2f} "
               f"| {r.return_pct:.1%} | ${r.pnl_dollars:,.0f} "
               f"| {pyr} | {r.exit_reason} |\n")

    md += f"""
---

## Worst Campaign Trades

| Ticker | Date | Rank | Score | Entry | Exit | Return | PnL | Exit Reason |
|---|---|---|---|---|---|---|---|---|
"""
    for r in entered[-10:]:
        md += (f"| {r.ticker} | {r.date} | {r.gap_rank} | {r.score:.0f} "
               f"| ${r.entry_price:.2f} | ${r.exit_price:.2f} "
               f"| {r.return_pct:.1%} | ${r.pnl_dollars:,.0f} "
               f"| {r.exit_reason} |\n")

    md += f"""
---

## Strategy Configuration

| Parameter | Value |
|---|---|
| Base Beta (β) | {BASE_BETA} |
| Alpha Beta (β_adj) | β × {ALPHA_BETA_MULT} = {BASE_BETA * ALPHA_BETA_MULT} |
| High Score ATR Stop | {HIGH_SCORE_ATR_MULT}× ATR |
| Low Score ATR Stop | {LOW_SCORE_ATR_MULT}× ATR |
| Pyramid Threshold | +{PYRAMID_THRESHOLD*100:.0f}% move, Rank #1 only |
| Pyramid Size | +{PYRAMID_ADD_PCT*100:.0f}% of base position |
| Initial Capital | ${INITIAL_CAPITAL:,} |
| Position Size | {POSITION_SIZE_PCT*100:.0f}% of capital |
| Entry: Vector Check | Price > VWAP AND CVD > 0 |
| Simulation Window | 09:45 → {SIM_END_ET} ET |

---

## Plots

- **Hockey Stick**: `plots/performance_comparison.png`
- **Drawdown**: `plots/drawdown_comparison.png`
- **Score vs Return**: `plots/score_vs_return.png`

---

*Generated by Phase 4 Campaign Backtest Pipeline*
"""

    (OUT / "Campaign_Report.md").write_text(md, encoding="utf-8")
    log(f"  Saved Campaign_Report.md")


# ═══════════════════════════════════════════════════════════════════════════════
#  MAIN EXECUTION
# ═══════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    log("Phase 4 — The Campaign Backtest")
    log(f"  Workspace: {OUT}")

    # ── Step 1: Inference Engine ─────────────────────────────────────────
    scored_universe, test_set, score_threshold = run_inference_engine()

    # ── Step 2 & 3: The Bake-Off ────────────────────────────────────────
    baseline_results, filtered_results, campaign_results = run_bakeoff(
        test_set, score_threshold
    )

    # ── Compute Metrics ──────────────────────────────────────────────────
    baseline_m  = compute_strategy_metrics(baseline_results, "Baseline")
    filtered_m  = compute_strategy_metrics(filtered_results, "Filtered")
    campaign_m  = compute_strategy_metrics(campaign_results, "Campaign")

    print_metrics_table([baseline_m, filtered_m, campaign_m])

    # ── Step 4: Visualizations ───────────────────────────────────────────
    generate_hockey_stick(baseline_m, filtered_m, campaign_m)
    generate_drawdown_chart(baseline_m, filtered_m, campaign_m)
    generate_score_vs_return_chart(test_set)

    # ── Report ───────────────────────────────────────────────────────────
    generate_campaign_report(baseline_m, filtered_m, campaign_m,
                             test_set, campaign_results)

    # ── Final summary ────────────────────────────────────────────────────
    total_time = time.perf_counter() - T0
    log(f"\n{'='*70}")
    log(f"PHASE 4 — CAMPAIGN BACKTEST — COMPLETE in {total_time:.1f}s")
    log(f"  Baseline:  {baseline_m['n_trades']} trades, PnL=${baseline_m['total_pnl']:,.0f}")
    log(f"  Filtered:  {filtered_m['n_trades']} trades, PnL=${filtered_m['total_pnl']:,.0f}")
    log(f"  Campaign:  {campaign_m['n_trades']} trades, PnL=${campaign_m['total_pnl']:,.0f}")
    log(f"  Report: Campaign_Report.md")
    log(f"  Plots: {len(list(PLOTS.glob('*.png')))} generated")
    log(f"{'='*70}")
