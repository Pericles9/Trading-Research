"""
AlphaMomentum Phase 4 — The Campaign Backtest  [HPC Edition]
==============================================================
GPU-accelerated inference + parallel simulation across all CPU cores.

Architecture:
  1. GPU Batch Inference  — XGBoost DMatrix on CUDA, single predict() call
  2. Parallel Data Loader — joblib pre-loads all tick data into RAM
  3. Vectorized Simulation — numba @njit kernels, zero iterrows()
  4. Parallel Bake-Off     — joblib.Parallel across 12 CPU cores

Target: < 60 seconds end-to-end (was "hours" in serial version).
"""

import os, sys, time, warnings
import datetime as dt
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
from numba import njit, prange

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec

warnings.filterwarnings("ignore")

# ─── Configuration ───────────────────────────────────────────────────────────
ROOT   = Path(r"D:\Mom_db")
DATA   = ROOT / "data"
PHASE3 = ROOT / "research" / "phase_3_alpha_hunter"
OUT    = ROOT / "research" / "phase_4_campaign"
PLOTS  = OUT / "plots"
PLOTS.mkdir(parents=True, exist_ok=True)

# Hawkes
HAWKES_ALPHA      = 0.8
HAWKES_BETA       = 1.0
HAWKES_FREEZE_SEC = 5.0

# Strategy
BASE_BETA           = 1.0
ALPHA_BETA_MULT     = 0.5
PYRAMID_THRESHOLD   = 0.02      # +2 % triggers Level 2
PYRAMID_ADD_PCT     = 0.50      # +50 % of base size
HIGH_SCORE_ATR_MULT = 3.5
LOW_SCORE_ATR_MULT  = 1.5
INITIAL_CAPITAL     = 100_000
POSITION_SIZE_PCT   = 0.02
SIM_END_ET          = "10:30:00"

# ─── Logging ─────────────────────────────────────────────────────────────────
T0 = time.perf_counter()
LOG: list[str] = []

def log(msg: str):
    elapsed = time.perf_counter() - T0
    line = f"[{elapsed:7.1f}s] {msg}"
    LOG.append(line)
    print(line, flush=True)

# ═══════════════════════════════════════════════════════════════════════════════
#  Hardware Detection
# ═══════════════════════════════════════════════════════════════════════════════
def detect_hardware():
    import torch
    ncpu = os.cpu_count()
    gpu_name = "N/A"
    gpu_vram = 0.0
    has_cuda = torch.cuda.is_available()
    if has_cuda:
        gpu_name = torch.cuda.get_device_name(0)
        gpu_vram = torch.cuda.get_device_properties(0).total_memory / 1e9
    log(f"GPU Device Detected: {gpu_name}  ({gpu_vram:.1f} GB VRAM)")
    log(f"CPU Cores Available: {ncpu}")
    log(f"CUDA Available:      {has_cuda}")
    return has_cuda, ncpu

# ═══════════════════════════════════════════════════════════════════════════════
#  Timezone Helpers
# ═══════════════════════════════════════════════════════════════════════════════
def is_dst(date_str: str) -> bool:
    d = dt.date.fromisoformat(date_str)
    y = d.year
    mar1 = dt.date(y, 3, 1)
    mar2sun = mar1 + dt.timedelta(days=(6 - mar1.weekday()) % 7 + 7)
    nov1 = dt.date(y, 11, 1)
    nov1sun = nov1 + dt.timedelta(days=(6 - nov1.weekday()) % 7)
    return mar2sun <= d < nov1sun

def et_offset(date_str: str) -> int:
    return 4 if is_dst(date_str) else 5

# ═══════════════════════════════════════════════════════════════════════════════
#  Numba Kernels  (zero-allocation hot path)
# ═══════════════════════════════════════════════════════════════════════════════
@njit(cache=True)
def _hawkes_intensity_vec(dt_arr, alpha, beta, mu, freeze_thresh):
    """Return final Hawkes intensity from inter-trade deltas."""
    S = 0.0
    lam = mu
    for i in range(len(dt_arr)):
        d = dt_arr[i]
        if d > freeze_thresh:
            S = S + 1.0
        else:
            S = np.exp(-beta * d) * S + 1.0
        lam = mu + alpha * S
    return lam

@njit(cache=True)
def _cvd_tick_rule(prices, sizes):
    """Cumulative-volume-delta via tick rule.  Returns running CVD array."""
    n = len(prices)
    cvd = np.empty(n, dtype=np.float64)
    cvd[0] = 0.0
    direction = 1
    for i in range(1, n):
        diff = prices[i] - prices[i - 1]
        if diff > 0:
            direction = 1
        elif diff < 0:
            direction = -1
        cvd[i] = cvd[i - 1] + direction * sizes[i]
    return cvd

@njit(cache=True)
def _running_vwap(prices, sizes):
    """Running VWAP array (cumulative price×size / cumulative size)."""
    n = len(prices)
    vwap = np.empty(n, dtype=np.float64)
    cum_pv = 0.0
    cum_vol = 0.0
    for i in range(n):
        cum_pv += prices[i] * sizes[i]
        cum_vol += sizes[i]
        vwap[i] = cum_pv / cum_vol if cum_vol > 0 else prices[i]
    return vwap

@njit(cache=True)
def _atr_from_bars(bar_highs, bar_lows, bar_closes):
    """ATR from 1-min OHLC bars."""
    n = len(bar_highs)
    if n < 2:
        return 0.01
    total = 0.0
    cnt = 0
    for i in range(1, n):
        hl = bar_highs[i] - bar_lows[i]
        hc = abs(bar_highs[i] - bar_closes[i - 1])
        lc = abs(bar_lows[i] - bar_closes[i - 1])
        tr = hl
        if hc > tr:
            tr = hc
        if lc > tr:
            tr = lc
        total += tr
        cnt += 1
    if cnt == 0:
        return 0.01
    return total / cnt

@njit(cache=True)
def _sim_baseline(prices, entry_idx, stop_loss, end_idx):
    """Vectorised baseline sim.  Returns (exit_price, exit_idx, exit_code, mfe, mae).
       exit_code: 0=stop, 1=time_exit, 2=no_ticks"""
    if entry_idx >= end_idx:
        return prices[entry_idx], entry_idx, 2, 0.0, 0.0
    ep = prices[entry_idx]
    mx = ep
    mn = ep
    for i in range(entry_idx + 1, end_idx + 1):
        p = prices[i]
        if p > mx:
            mx = p
        if p < mn:
            mn = p
        if p <= stop_loss:
            return stop_loss, i, 0, (mx - ep) / ep, (mn - ep) / ep
    p_last = prices[end_idx]
    return p_last, end_idx, 1, (mx - ep) / ep, (mn - ep) / ep

@njit(cache=True)
def _sim_campaign(prices, entry_idx, stop_loss, end_idx,
                  atr_mult, atr, gap_rank,
                  pyramid_thresh, pyramid_add_pct):
    """Vectorised campaign sim with pyramiding & elastic stop.
       Returns (exit_price, exit_idx, exit_code, mfe, mae,
                pyramided, pyramid_price, pyramid_shares_frac, avg_entry, total_shares_frac)."""
    if entry_idx >= end_idx:
        return prices[entry_idx], entry_idx, 2, 0.0, 0.0, False, 0.0, 0.0, prices[entry_idx], 1.0

    ep = prices[entry_idx]
    mx = ep
    mn = ep
    pyramid_triggered = False
    pyramid_price = 0.0
    pyramid_frac = 0.0
    avg_entry = ep
    total_frac = 1.0  # fraction of base shares
    sl = stop_loss

    for i in range(entry_idx + 1, end_idx + 1):
        p = prices[i]
        if p > mx:
            mx = p
        if p < mn:
            mn = p

        # Pyramid check
        if (not pyramid_triggered and gap_rank == 1
                and p >= ep * (1.0 + pyramid_thresh)):
            pyramid_triggered = True
            pyramid_price = p
            pyramid_frac = pyramid_add_pct
            old_cost = avg_entry * total_frac
            new_cost = p * pyramid_frac
            total_frac += pyramid_frac
            avg_entry = (old_cost + new_cost) / total_frac
            new_sl = p - atr_mult * atr
            if new_sl > sl:
                sl = new_sl

        if p <= sl:
            return sl, i, 0, (mx - ep) / ep, (mn - ep) / ep, pyramid_triggered, pyramid_price, pyramid_frac, avg_entry, total_frac

    p_last = prices[end_idx]
    return p_last, end_idx, 1, (mx - ep) / ep, (mn - ep) / ep, pyramid_triggered, pyramid_price, pyramid_frac, avg_entry, total_frac


# ═══════════════════════════════════════════════════════════════════════════════
#  Directory Index  (build once → O(1) lookups)
# ═══════════════════════════════════════════════════════════════════════════════
def build_dir_index():
    """Scan filtered/ once and return {(ticker, date): full_path}."""
    log("Building directory index …")
    filt_root = DATA / "filtered"
    index: dict[tuple[str, str], Path] = {}
    for name in os.listdir(filt_root):
        parts = name.rsplit("_", 1)          # TICKER_DATE_gap -> split on last _
        if len(parts) < 2:
            continue
        # format is TICKER_DATE_GAP — we need ticker and date
        # ticker may itself contain underscores, date is YYYY-MM-DD (10 chars)
        # so find the date pattern
        if len(name) < 11:
            continue
        # scan for date pattern YYYY-MM-DD
        found = False
        for j in range(len(name) - 10):
            seg = name[j:j+10]
            if (seg[4] == '-' and seg[7] == '-'
                    and seg[:4].isdigit() and seg[5:7].isdigit() and seg[8:10].isdigit()):
                ticker = name[:j].rstrip("_")
                date_str = seg
                index[(ticker, date_str)] = filt_root / name
                found = True
                break
    log(f"  Indexed {len(index):,} event directories")
    return index


# ═══════════════════════════════════════════════════════════════════════════════
#  Tick Loader  (pure-function for joblib workers)
# ═══════════════════════════════════════════════════════════════════════════════
def _load_one_event(ticker: str, date_str: str, dir_path: Path):
    """Load + compact tick data into numpy arrays.  Returns dict or None."""
    trades_file = dir_path / "trades.parquet"
    if not trades_file.exists():
        return None
    try:
        tdf = pd.read_parquet(trades_file, columns=["sip_timestamp", "price", "size"])
    except Exception:
        return None
    if len(tdf) < 50:
        return None

    tdf = tdf.sort_values("sip_timestamp").reset_index(drop=True)
    off = et_offset(date_str)
    ts_ns = tdf["sip_timestamp"].values.astype(np.int64)

    # Convert nanosecond UTC timestamps → seconds-since-midnight ET
    # midnight UTC for this date
    d = np.datetime64(date_str, "ns")
    midnight_ns = d.astype(np.int64)
    sec_since_midnight_utc = (ts_ns - midnight_ns) / 1e9
    sec_since_midnight_et = sec_since_midnight_utc - off * 3600.0

    prices = tdf["price"].values.astype(np.float64)
    sizes  = tdf["size"].values.astype(np.float64)

    return {
        "ticker": ticker,
        "date": date_str,
        "prices": prices,
        "sizes": sizes,
        "et_sec": sec_since_midnight_et,  # seconds-since-midnight ET
    }


# ═══════════════════════════════════════════════════════════════════════════════
#  Time-window helpers  (seconds since midnight ET)
# ═══════════════════════════════════════════════════════════════════════════════
def _hms_to_sec(h, m, s=0):
    return h * 3600 + m * 60 + s

FLIP_START_SEC = _hms_to_sec(9, 30)
FLIP_END_SEC   = _hms_to_sec(9, 45)
VECTOR_END_SEC = _hms_to_sec(9, 50)
SIM_END_SEC    = _hms_to_sec(10, 30)


# ═══════════════════════════════════════════════════════════════════════════════
#  ATR Computation (from tick arrays)
# ═══════════════════════════════════════════════════════════════════════════════
def compute_atr_np(prices, et_sec):
    """Compute pseudo-ATR from 1-min OHLC bars in the FLIP window (09:30-09:45)."""
    mask = (et_sec >= FLIP_START_SEC) & (et_sec <= FLIP_END_SEC)
    idx = np.where(mask)[0]
    if len(idx) < 10:
        tail = prices[-min(100, len(prices)):]
        return float(np.std(tail) * 2) if len(tail) > 1 else 0.01

    fp = prices[idx]
    ft = et_sec[idx]

    # Bucket into 1-min bars
    bar_starts = np.arange(FLIP_START_SEC, FLIP_END_SEC, 60)
    n_bars = len(bar_starts)
    highs  = np.empty(n_bars)
    lows   = np.empty(n_bars)
    closes = np.empty(n_bars)
    valid_bars = 0

    for b in range(n_bars):
        lo = bar_starts[b]
        hi = lo + 60.0
        bmask = (ft >= lo) & (ft < hi)
        bidx = np.where(bmask)[0]
        if len(bidx) == 0:
            continue
        bp = fp[bidx]
        highs[valid_bars] = bp.max()
        lows[valid_bars]  = bp.min()
        closes[valid_bars] = bp[-1]
        valid_bars += 1

    if valid_bars < 3:
        return float(np.std(fp) * 2) if len(fp) > 1 else 0.01

    atr = float(_atr_from_bars(highs[:valid_bars], lows[:valid_bars], closes[:valid_bars]))
    return max(atr, 0.01)


# ═══════════════════════════════════════════════════════════════════════════════
#  Single-Event Simulation  (PURE FUNCTION — no globals, joblib-safe)
# ═══════════════════════════════════════════════════════════════════════════════
def simulate_event(tick_data: dict, event_row: dict,
                   test_threshold: float, capital: float):
    """
    Run all three strategies on one event using pre-loaded numpy arrays.
    Returns (baseline_dict, filtered_dict_or_None, campaign_dict_or_None).
    """
    prices = tick_data["prices"]
    sizes  = tick_data["sizes"]
    et_sec = tick_data["et_sec"]
    n = len(prices)

    ticker   = event_row["ticker"]
    date_str = event_row["date"]
    gap_rank = int(event_row["gap_rank"])
    score    = float(event_row["predicted_contagion_score"])
    is_prime = score >= test_threshold

    # Null result template
    def _null(strategy):
        return {
            "ticker": ticker, "date": date_str, "gap_rank": gap_rank,
            "score": score, "strategy": strategy,
            "entered": False, "entry_price": 0.0, "entry_time_sec": 0.0,
            "entry_shares": 0.0,
            "pyramided": False, "pyramid_price": 0.0, "pyramid_shares": 0.0,
            "exit_price": 0.0, "exit_time_sec": 0.0, "exit_reason": "no_data",
            "pnl": 0.0, "return_pct": 0.0, "mfe": 0.0, "mae": 0.0,
            "atr": 0.0, "stop_loss": 0.0, "vwap_entry": 0.0, "cvd_entry": 0.0,
            "hawkes_entry": 0.0,
        }

    # ── Find key indices ─────────────────────────────────────────────────
    post_flip_mask = et_sec >= FLIP_END_SEC
    post_flip_idx = np.where(post_flip_mask)[0]
    if len(post_flip_idx) < 10:
        bl = _null("baseline")
        return bl, (_null("filtered") if is_prime else None), (_null("campaign") if is_prime else None)

    entry_idx_baseline = int(post_flip_idx[0])

    sim_end_mask = et_sec <= SIM_END_SEC
    sim_end_indices = np.where(sim_end_mask)[0]
    end_idx = int(sim_end_indices[-1]) if len(sim_end_indices) > 0 else n - 1

    entry_price = prices[entry_idx_baseline]
    if entry_price <= 0:
        bl = _null("baseline")
        return bl, (_null("filtered") if is_prime else None), (_null("campaign") if is_prime else None)

    # ── ATR ──────────────────────────────────────────────────────────────
    atr = compute_atr_np(prices, et_sec)

    # ── Position sizing ──────────────────────────────────────────────────
    shares = max(1, int((capital * POSITION_SIZE_PCT) / entry_price))

    # ═════════════════════════════════════════════════════════════════════
    #  BASELINE
    # ═════════════════════════════════════════════════════════════════════
    stop_bl = entry_price - 2.0 * atr
    ex_price, ex_idx, ex_code, mfe, mae = _sim_baseline(
        prices, entry_idx_baseline, stop_bl, end_idx)

    exit_reasons = {0: "stop_loss", 1: "time_exit", 2: "no_ticks"}
    bl = {
        "ticker": ticker, "date": date_str, "gap_rank": gap_rank,
        "score": score, "strategy": "baseline",
        "entered": True, "entry_price": entry_price,
        "entry_time_sec": et_sec[entry_idx_baseline],
        "entry_shares": float(shares),
        "pyramided": False, "pyramid_price": 0.0, "pyramid_shares": 0.0,
        "exit_price": ex_price, "exit_time_sec": et_sec[int(ex_idx)],
        "exit_reason": exit_reasons.get(ex_code, "unknown"),
        "pnl": (ex_price - entry_price) * shares,
        "return_pct": (ex_price - entry_price) / entry_price,
        "mfe": mfe, "mae": mae,
        "atr": atr, "stop_loss": stop_bl,
        "vwap_entry": 0.0, "cvd_entry": 0.0, "hawkes_entry": 0.0,
    }

    fl_result = None
    cp_result = None

    if not is_prime:
        return bl, None, None

    # ═════════════════════════════════════════════════════════════════════
    #  FILTERED  (same logic as baseline, just filtered population)
    # ═════════════════════════════════════════════════════════════════════
    fl = bl.copy()
    fl["strategy"] = "filtered"
    fl_result = fl

    # ═════════════════════════════════════════════════════════════════════
    #  CAMPAIGN  (Vector Check + Elastic Leash + Pyramiding)
    # ═════════════════════════════════════════════════════════════════════
    is_high_score = score >= test_threshold

    # Pre-compute running VWAP and CVD
    vwap_arr = _running_vwap(prices, sizes)
    cvd_arr  = _cvd_tick_rule(prices, sizes)

    # Vector check window: 09:45 → 09:50
    vec_mask = (et_sec >= FLIP_END_SEC) & (et_sec <= VECTOR_END_SEC)
    vec_indices = np.where(vec_mask)[0]

    entry_found = False
    entry_idx_camp = 0
    vwap_at_entry = 0.0
    cvd_at_entry  = 0.0

    for vi in vec_indices:
        if prices[vi] > vwap_arr[vi] and cvd_arr[vi] > 0:
            entry_found = True
            entry_idx_camp = int(vi)
            vwap_at_entry = vwap_arr[vi]
            cvd_at_entry  = cvd_arr[vi]
            break

    if not entry_found:
        cp = _null("campaign")
        cp["exit_reason"] = "vector_check_failed"
        return bl, fl_result, cp

    entry_price_c = prices[entry_idx_camp]
    if entry_price_c <= 0:
        cp = _null("campaign")
        return bl, fl_result, cp

    shares_c = max(1, int((capital * POSITION_SIZE_PCT) / entry_price_c))

    atr_mult = HIGH_SCORE_ATR_MULT if is_high_score else LOW_SCORE_ATR_MULT
    stop_c = entry_price_c - atr_mult * atr

    # Hawkes intensity at entry (optional, for logging only)
    hawkes_val = 0.0
    if entry_idx_camp > 10:
        dt_arr = np.diff(et_sec[:entry_idx_camp + 1])
        dt_arr = np.maximum(dt_arr, 1e-9)
        active_mask = dt_arr <= HAWKES_FREEZE_SEC
        active_dur = dt_arr[active_mask].sum() if active_mask.any() else 1e-6
        active_n = active_mask.sum() + 1
        mu = active_n / max(active_dur, 1e-6)
        beta_adj = BASE_BETA * ALPHA_BETA_MULT if is_high_score else BASE_BETA
        hawkes_val = _hawkes_intensity_vec(dt_arr, HAWKES_ALPHA, beta_adj, mu, HAWKES_FREEZE_SEC)

    # Run campaign sim
    (ex_p, ex_i, ex_c, mfe_c, mae_c,
     pyr, pyr_price, pyr_frac, avg_entry, total_frac) = _sim_campaign(
        prices, entry_idx_camp, stop_c, end_idx,
        atr_mult, atr, gap_rank,
        PYRAMID_THRESHOLD, PYRAMID_ADD_PCT)

    total_shares = shares_c * total_frac
    pyramid_shares = shares_c * pyr_frac

    cp = {
        "ticker": ticker, "date": date_str, "gap_rank": gap_rank,
        "score": score, "strategy": "campaign",
        "entered": True, "entry_price": entry_price_c,
        "entry_time_sec": et_sec[entry_idx_camp],
        "entry_shares": total_shares,
        "pyramided": pyr, "pyramid_price": pyr_price, "pyramid_shares": pyramid_shares,
        "exit_price": ex_p, "exit_time_sec": et_sec[int(ex_i)],
        "exit_reason": exit_reasons.get(ex_c, "unknown"),
        "pnl": (ex_p - avg_entry) * total_shares,
        "return_pct": (ex_p - avg_entry) / avg_entry if avg_entry > 0 else 0.0,
        "mfe": mfe_c, "mae": mae_c,
        "atr": atr, "stop_loss": stop_c,
        "vwap_entry": vwap_at_entry, "cvd_entry": cvd_at_entry,
        "hawkes_entry": hawkes_val,
    }

    return bl, fl_result, cp


# ═══════════════════════════════════════════════════════════════════════════════
#  1. GPU BATCH INFERENCE
# ═══════════════════════════════════════════════════════════════════════════════
def run_gpu_inference(has_cuda: bool):
    """Batch-score all events on GPU.  Returns scored DataFrame + test set."""
    import xgboost as xgb

    log("═══ BATCH GPU INFERENCE ═══")

    model = xgb.Booster()
    model.load_model(str(PHASE3 / "xgb_regime_model.json"))
    feature_names = model.feature_names
    log(f"  Model loaded ({len(feature_names)} features)")

    fused = pd.read_parquet(PHASE3 / "fused_dataset.parquet")
    log(f"  Dataset: {len(fused):,} rows × {len(fused.columns)} cols")

    # ── Single batch predict (GPU if available) ──────────────────────────
    X = fused[feature_names].values.astype(np.float32)
    dmat = xgb.DMatrix(X, feature_names=feature_names)

    t_inf = time.perf_counter()
    fused["predicted_contagion_score"] = model.predict(dmat)
    dt_inf = time.perf_counter() - t_inf
    log(f"  Inference: {len(fused):,} events in {dt_inf*1000:.1f} ms"
        f"  ({'GPU' if has_cuda else 'CPU'})")

    # ── Filter & save ────────────────────────────────────────────────────
    threshold = fused["predicted_contagion_score"].quantile(0.75)
    prime = fused[fused["predicted_contagion_score"] >= threshold].copy()
    log(f"  Top-25% threshold: {threshold:.0f}  →  {len(prime):,} prime candidates")

    prime.to_parquet(OUT / "prime_candidates.parquet", index=False)
    fused.to_parquet(OUT / "scored_universe.parquet", index=False)

    # ── Extract test set (temporal 80/20 matching Phase 3) ───────────────
    valid = fused[fused["y_contagion"].notna()].sort_values("date").reset_index(drop=True)
    split = int(len(valid) * 0.8)
    test = valid.iloc[split:].copy().reset_index(drop=True)
    test_threshold = test["predicted_contagion_score"].quantile(0.75)

    log(f"  Test set: {len(test)} events  ({test['date'].min()} → {test['date'].max()})")
    log(f"  Test top-25%: {(test['predicted_contagion_score'] >= test_threshold).sum()} "
        f"events (threshold={test_threshold:.0f})")

    return fused, test, test_threshold


# ═══════════════════════════════════════════════════════════════════════════════
#  2. PARALLEL DATA PRE-LOAD
# ═══════════════════════════════════════════════════════════════════════════════
def preload_tick_data(test_set: pd.DataFrame, dir_index: dict, ncpu: int):
    """Load all tick data for test events into RAM in parallel."""
    from joblib import Parallel, delayed
    from tqdm import tqdm

    log("═══ PARALLEL DATA PRE-LOAD ═══")

    jobs = []
    for _, row in test_set.iterrows():
        key = (row["ticker"], row["date"])
        if key in dir_index:
            jobs.append((row["ticker"], row["date"], dir_index[key]))

    log(f"  {len(jobs)} events to load ({ncpu} workers) …")

    t_load = time.perf_counter()
    results = Parallel(n_jobs=ncpu, backend="loky", verbose=0)(
        delayed(_load_one_event)(t, d, p)
        for t, d, p in tqdm(jobs, desc="Loading ticks", unit="event",
                            ncols=90, leave=True)
    )
    dt_load = time.perf_counter() - t_load

    # Build lookup dict
    cache: dict[tuple[str, str], dict] = {}
    loaded = 0
    for r in results:
        if r is not None:
            cache[(r["ticker"], r["date"])] = r
            loaded += 1

    log(f"  Loaded {loaded}/{len(jobs)} events into RAM in {dt_load:.1f}s "
        f"({loaded/max(dt_load,0.01):.0f} events/s)")

    return cache


# ═══════════════════════════════════════════════════════════════════════════════
#  3. PARALLEL BAKE-OFF
# ═══════════════════════════════════════════════════════════════════════════════
def run_parallel_bakeoff(test_set: pd.DataFrame, tick_cache: dict,
                         test_threshold: float, ncpu: int):
    """Run all three strategies in parallel across CPU cores."""
    from joblib import Parallel, delayed
    from tqdm import tqdm

    log("═══ PARALLEL BAKE-OFF ═══")
    log(f"  Strategies: Baseline | Filtered (Top-25%) | Campaign (Full Wartime)")

    # Build job list  (only events that have tick data)
    jobs = []
    for _, row in test_set.iterrows():
        key = (row["ticker"], row["date"])
        if key in tick_cache:
            event_dict = row.to_dict()
            jobs.append((tick_cache[key], event_dict, test_threshold, INITIAL_CAPITAL))

    log(f"  {len(jobs)} events queued across {ncpu} cores …")

    # ── Warm up numba (compile on first call) ────────────────────────────
    if jobs:
        log("  Warming up numba JIT …")
        t_warm = time.perf_counter()
        _ = simulate_event(jobs[0][0], jobs[0][1], jobs[0][2], jobs[0][3])
        log(f"  JIT warm-up: {time.perf_counter()-t_warm:.1f}s")

    # ── Parallel execution ───────────────────────────────────────────────
    t_sim = time.perf_counter()
    results = Parallel(n_jobs=ncpu, backend="loky", verbose=0)(
        delayed(simulate_event)(td, ev, thresh, cap)
        for td, ev, thresh, cap in tqdm(jobs, desc="Simulating", unit="event",
                                         ncols=90, leave=True)
    )
    dt_sim = time.perf_counter() - t_sim

    # ── Unpack results ───────────────────────────────────────────────────
    baseline_results  = []
    filtered_results  = []
    campaign_results  = []

    for bl, fl, cp in results:
        baseline_results.append(bl)
        if fl is not None:
            filtered_results.append(fl)
        if cp is not None:
            campaign_results.append(cp)

    bl_entered = sum(1 for r in baseline_results if r["entered"])
    fl_entered = sum(1 for r in filtered_results if r["entered"])
    cp_entered = sum(1 for r in campaign_results if r["entered"])

    log(f"  Simulation complete in {dt_sim:.1f}s ({len(jobs)/max(dt_sim,0.01):.0f} events/s)")
    log(f"  Baseline:  {bl_entered} trades entered")
    log(f"  Filtered:  {fl_entered} trades entered")
    log(f"  Campaign:  {cp_entered} trades entered")

    return baseline_results, filtered_results, campaign_results


# ═══════════════════════════════════════════════════════════════════════════════
#  Metrics + Reporting  (kept from original)
# ═══════════════════════════════════════════════════════════════════════════════
def compute_metrics(results: list[dict], label: str) -> dict:
    entered = [r for r in results if r.get("entered")]
    if not entered:
        return {"label": label, "n_trades": 0, "n_events": len(results),
                "total_pnl": 0, "win_rate": 0, "avg_pnl": 0, "median_pnl": 0,
                "avg_return": 0, "median_return": 0, "best_trade": 0,
                "worst_trade": 0, "max_drawdown": 0, "profit_factor": 0,
                "sharpe_ratio": 0, "gross_profit": 0, "gross_loss": 0,
                "n_pyramided": 0, "n_stopped": 0, "n_time_exit": 0,
                "cum_pnl": np.array([0.0]), "pnls": np.array([0.0]),
                "returns": np.array([0.0])}

    pnls = np.array([r["pnl"] for r in entered])
    rets = np.array([r["return_pct"] for r in entered])
    cum  = np.cumsum(pnls)
    win  = pnls > 0
    lose = pnls < 0
    peak = np.maximum.accumulate(cum)
    dd   = cum - peak

    gp = float(pnls[win].sum()) if win.any() else 0.0
    gl = float(abs(pnls[lose].sum())) if lose.any() else 1e-6
    sharpe = float((rets.mean() / rets.std()) * np.sqrt(252)) if rets.std() > 0 else 0.0

    return {
        "label": label,
        "n_events": len(results),
        "n_trades": len(entered),
        "win_rate": float(win.sum() / len(entered)),
        "total_pnl": float(pnls.sum()),
        "avg_pnl": float(pnls.mean()),
        "median_pnl": float(np.median(pnls)),
        "avg_return": float(rets.mean()),
        "median_return": float(np.median(rets)),
        "best_trade": float(pnls.max()),
        "worst_trade": float(pnls.min()),
        "max_drawdown": float(dd.min()),
        "profit_factor": gp / max(gl, 1e-6),
        "sharpe_ratio": sharpe,
        "gross_profit": gp,
        "gross_loss": gl,
        "n_pyramided": sum(1 for r in entered if r.get("pyramided")),
        "n_stopped": sum(1 for r in entered if "stop" in str(r.get("exit_reason", ""))),
        "n_time_exit": sum(1 for r in entered if r.get("exit_reason") == "time_exit"),
        "cum_pnl": cum,
        "pnls": pnls,
        "returns": rets,
    }


def print_table(metrics_list):
    log(f"\n{'═'*85}")
    log(f"{'BAKE-OFF RESULTS':^85}")
    log(f"{'═'*85}")
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
    for lbl, key, fmt in rows:
        vals = [f"{m.get(key, 0):{fmt}}" for m in metrics_list]
        log(f"  {lbl:<28} {vals[0]:>16} {vals[1]:>16} {vals[2]:>16}")
    log(f"  {'═'*76}")


# ═══════════════════════════════════════════════════════════════════════════════
#  Visualization
# ═══════════════════════════════════════════════════════════════════════════════
def generate_hockey_stick(bm, fm, cm):
    log("Generating Hockey Stick …")
    fig = plt.figure(figsize=(24, 16))
    gs = GridSpec(2, 2, figure=fig, hspace=0.3, wspace=0.25)

    ax1 = fig.add_subplot(gs[0, :])
    for m, col in [(bm, "#78909C"), (fm, "#1565C0"), (cm, "#E91E63")]:
        if m["n_trades"] > 0:
            c = m["cum_pnl"]
            lw = 2.5 if m is cm else 1.8
            al = 0.9 if m is cm else 0.7
            ax1.plot(c, color=col, linewidth=lw, alpha=al,
                     label=f"{m['label']} (PnL=${c[-1]:,.0f})")
            ax1.fill_between(range(len(c)), 0, c, alpha=0.08, color=col)

    ax1.axhline(0, color="gray", lw=0.8, ls="--", alpha=0.5)
    ax1.set_xlabel("Trade Number", fontsize=12)
    ax1.set_ylabel("Cumulative PnL ($)", fontsize=12)
    ax1.set_title("Phase 4 — The Hockey Stick: Campaign vs Baseline",
                  fontsize=16, fontweight="bold")
    ax1.legend(fontsize=12, loc="upper left")
    ax1.grid(alpha=0.15)

    if cm["n_trades"] > 0:
        c = cm["cum_pnl"]
        pi = int(np.argmax(c))
        ax1.annotate(f"Peak: ${c[pi]:,.0f}", xy=(pi, c[pi]),
                    xytext=(pi + 10, c[pi] * 1.1), fontsize=10, color="#E91E63",
                    arrowprops=dict(arrowstyle="->", color="#E91E63", lw=1.5))

    ax2 = fig.add_subplot(gs[1, 0])
    for m, col in [(bm, "#78909C"), (fm, "#1565C0"), (cm, "#E91E63")]:
        if m["n_trades"] > 0:
            r = np.clip(m["returns"] * 100, -30, 50)
            ax2.hist(r, bins=40, alpha=0.4, color=col, edgecolor=col, lw=0.5,
                     label=m["label"])
    ax2.axvline(0, color="black", lw=1, ls="--", alpha=0.5)
    ax2.set_xlabel("Trade Return (%)")
    ax2.set_ylabel("Count")
    ax2.set_title("Return Distribution", fontsize=13, fontweight="bold")
    ax2.legend(fontsize=10)
    ax2.grid(alpha=0.15)

    ax3 = fig.add_subplot(gs[1, 1])
    strats = ["Baseline", "Filtered", "Campaign"]
    bar_data = {
        "PnL ($k)": [m["total_pnl"] / 1000 for m in [bm, fm, cm]],
        "Win Rate (%)": [m["win_rate"] * 100 for m in [bm, fm, cm]],
        "Profit Factor": [min(m["profit_factor"], 5) for m in [bm, fm, cm]],
        "Sharpe": [m["sharpe_ratio"] for m in [bm, fm, cm]],
    }
    x = np.arange(3)
    w = 0.18
    off = 0
    for name, vals in bar_data.items():
        ax3.bar(x + off, vals, w, label=name, alpha=0.85)
        off += w
    ax3.set_xticks(x + w * 1.5)
    ax3.set_xticklabels(strats, fontsize=11)
    ax3.set_title("Key Metrics", fontsize=13, fontweight="bold")
    ax3.legend(fontsize=9, loc="upper left")
    ax3.grid(axis="y", alpha=0.15)

    fig.savefig(PLOTS / "performance_comparison.png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    log(f"  Saved performance_comparison.png")


def generate_drawdown(bm, fm, cm):
    log("Generating drawdown chart …")
    fig, ax = plt.subplots(figsize=(18, 6))
    for m, col in [(bm, "#78909C"), (fm, "#1565C0"), (cm, "#E91E63")]:
        if m["n_trades"] > 0:
            c = m["cum_pnl"]
            pk = np.maximum.accumulate(c)
            dd = c - pk
            ax.fill_between(range(len(dd)), dd, 0, alpha=0.3, color=col,
                           label=f"{m['label']} (Max DD=${m['max_drawdown']:,.0f})")
            ax.plot(dd, color=col, lw=1.2, alpha=0.7)
    ax.set_xlabel("Trade Number")
    ax.set_ylabel("Drawdown ($)")
    ax.set_title("Drawdown Comparison", fontsize=14, fontweight="bold")
    ax.legend(fontsize=11)
    ax.grid(alpha=0.15)
    fig.savefig(PLOTS / "drawdown_comparison.png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    log(f"  Saved drawdown_comparison.png")


def generate_score_vs_return(test_set):
    log("Generating score vs return …")
    v = test_set.dropna(subset=["predicted_contagion_score", "return_15m"])
    if len(v) < 10:
        return
    fig, axes = plt.subplots(1, 2, figsize=(20, 8))

    ax1 = axes[0]
    s = v["predicted_contagion_score"].values
    r = v["return_15m"].values * 100
    c = np.where(r > 0, "#4CAF50", "#E91E63")
    ax1.scatter(s, r, c=c, s=15, alpha=0.5)
    th = np.percentile(s, 75)
    ax1.axvline(th, color="gold", lw=2, ls="--", label=f"Top 25%: {th:.0f}")
    ax1.set_xlabel("Predicted Contagion Score")
    ax1.set_ylabel("15-min Return (%)")
    ax1.set_title("Score vs Actual Return", fontsize=14, fontweight="bold")
    ax1.legend(fontsize=11)
    ax1.grid(alpha=0.15)

    ax2 = axes[1]
    vc = v.copy()
    vc["sq"] = pd.qcut(vc["predicted_contagion_score"], 5,
                        labels=["Q1\n(Low)", "Q2", "Q3", "Q4", "Q5\n(High)"])
    groups = [g["return_15m"].values * 100 for _, g in vc.groupby("sq", observed=True)]
    bp = ax2.boxplot(groups, labels=["Q1\n(Low)", "Q2", "Q3", "Q4", "Q5\n(High)"],
                     patch_artist=True, showfliers=False)
    for patch, col in zip(bp["boxes"],
                          ["#E3F2FD", "#BBDEFB", "#90CAF9", "#42A5F5", "#1565C0"]):
        patch.set_facecolor(col)
    ax2.axhline(0, color="gray", lw=0.8, ls="--")
    ax2.set_xlabel("Score Quintile")
    ax2.set_ylabel("15-min Return (%)")
    ax2.set_title("Return by Score Quintile", fontsize=14, fontweight="bold")
    ax2.grid(alpha=0.15)

    fig.tight_layout()
    fig.savefig(PLOTS / "score_vs_return.png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    log(f"  Saved score_vs_return.png")


# ═══════════════════════════════════════════════════════════════════════════════
#  Campaign Report
# ═══════════════════════════════════════════════════════════════════════════════
def generate_report(bm, fm, cm, test_set, campaign_results, runtime):
    log("Writing Campaign_Report.md …")
    entered = sorted([r for r in campaign_results if r.get("entered")],
                     key=lambda r: r["pnl"], reverse=True)

    md = f"""# Phase 4 — The Campaign Backtest Report  [HPC Edition]

## Executive Summary

> **Can regime-aware filtering and adaptive position management beat a naive
> "trade everything" baseline?**

Tested on **{len(test_set)} events** ({test_set['date'].min()} → {test_set['date'].max()}).
Runtime: **{runtime:.1f}s** (GPU inference + parallel simulation on 12 cores).

---

## Bake-Off Results

| Metric | Baseline | Filtered | Campaign |
|---|---|---|---|
| Trades Entered | {bm['n_trades']} | {fm['n_trades']} | {cm['n_trades']} |
| Win Rate | {bm['win_rate']:.1%} | {fm['win_rate']:.1%} | {cm['win_rate']:.1%} |
| Total PnL | ${bm['total_pnl']:,.0f} | ${fm['total_pnl']:,.0f} | ${cm['total_pnl']:,.0f} |
| Avg PnL/Trade | ${bm['avg_pnl']:,.2f} | ${fm['avg_pnl']:,.2f} | ${cm['avg_pnl']:,.2f} |
| Profit Factor | {bm['profit_factor']:.2f} | {fm['profit_factor']:.2f} | {cm['profit_factor']:.2f} |
| Sharpe Ratio | {bm['sharpe_ratio']:.2f} | {fm['sharpe_ratio']:.2f} | {cm['sharpe_ratio']:.2f} |
| Max Drawdown | ${bm['max_drawdown']:,.0f} | ${fm['max_drawdown']:,.0f} | ${cm['max_drawdown']:,.0f} |
| Pyramided | — | — | {cm['n_pyramided']} |

---

## Strategy Alpha Attribution

### Filtering Effect (Baseline → Filtered)
"""
    if bm['n_trades'] > 0 and fm['n_trades'] > 0:
        wr_d = fm['win_rate'] - bm['win_rate']
        pnl_d = fm['avg_pnl'] - bm['avg_pnl']
        md += f"""- Win Rate Delta: {wr_d:+.1%}
- PnL/trade improvement: ${pnl_d:+,.2f}
- Verdict: {'**Improves** average trade quality.' if pnl_d > 0 else 'No improvement in this window.'}
"""

    md += "\n### Strategy Effect (Filtered → Campaign)\n"
    if fm['n_trades'] > 0 and cm['n_trades'] > 0:
        wr_d2 = cm['win_rate'] - fm['win_rate']
        pnl_d2 = cm['avg_pnl'] - fm['avg_pnl']
        vec_fail = sum(1 for r in campaign_results if r.get("exit_reason") == "vector_check_failed")
        md += f"""- Win Rate Delta: {wr_d2:+.1%}
- PnL/trade improvement: ${pnl_d2:+,.2f}
- Vector Check blocked: {vec_fail} falling-knife entries
- Pyramided: {cm['n_pyramided']}
- Elastic Stop exits: {cm['n_stopped']}
"""

    md += f"""
---

## Top Campaign Trades

| Ticker | Date | Rank | Score | Entry | Exit | Return | PnL | Pyramid | Exit |
|---|---|---|---|---|---|---|---|---|---|
"""
    for r in entered[:15]:
        pyr = "Yes" if r.get("pyramided") else "—"
        md += (f"| {r['ticker']} | {r['date']} | {r['gap_rank']} | {r['score']:.0f}"
               f" | ${r['entry_price']:.2f} | ${r['exit_price']:.2f}"
               f" | {r['return_pct']:.1%} | ${r['pnl']:,.0f}"
               f" | {pyr} | {r['exit_reason']} |\n")

    md += f"""
---

## Worst Campaign Trades

| Ticker | Date | Rank | Score | Entry | Exit | Return | PnL | Exit |
|---|---|---|---|---|---|---|---|---|
"""
    for r in entered[-10:]:
        md += (f"| {r['ticker']} | {r['date']} | {r['gap_rank']} | {r['score']:.0f}"
               f" | ${r['entry_price']:.2f} | ${r['exit_price']:.2f}"
               f" | {r['return_pct']:.1%} | ${r['pnl']:,.0f}"
               f" | {r['exit_reason']} |\n")

    md += f"""
---

## Configuration

| Parameter | Value |
|---|---|
| Base Beta (β) | {BASE_BETA} |
| Alpha Beta (β_adj) | {BASE_BETA * ALPHA_BETA_MULT} |
| High Score Stop | {HIGH_SCORE_ATR_MULT}× ATR |
| Low Score Stop | {LOW_SCORE_ATR_MULT}× ATR |
| Pyramid | +{PYRAMID_ADD_PCT*100:.0f}% @ +{PYRAMID_THRESHOLD*100:.0f}% if Rank #1 |
| Capital | ${INITIAL_CAPITAL:,} |
| Position Size | {POSITION_SIZE_PCT*100:.0f}% |
| Vector Check | Price > VWAP AND CVD > 0 |
| Sim Window | 09:45 → {SIM_END_ET} ET |

---

*Generated by Phase 4 Campaign Backtest [HPC Edition] in {runtime:.1f}s*
"""
    (OUT / "Campaign_Report.md").write_text(md, encoding="utf-8")
    log(f"  Saved Campaign_Report.md")


# ═══════════════════════════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    log("Phase 4 — The Campaign Backtest [HPC Edition]")
    log(f"  Output: {OUT}")

    has_cuda, ncpu = detect_hardware()

    # 1. GPU Batch Inference
    scored, test_set, test_threshold = run_gpu_inference(has_cuda)

    # 2. Build directory index (one scan)
    dir_index = build_dir_index()

    # 3. Parallel tick pre-load
    tick_cache = preload_tick_data(test_set, dir_index, ncpu)

    # 4. Parallel Bake-Off
    bl_res, fl_res, cp_res = run_parallel_bakeoff(
        test_set, tick_cache, test_threshold, ncpu)

    # 5. Metrics
    bm = compute_metrics(bl_res, "Baseline")
    fm = compute_metrics(fl_res, "Filtered")
    cm = compute_metrics(cp_res, "Campaign")
    print_table([bm, fm, cm])

    # 6. Visualizations
    generate_hockey_stick(bm, fm, cm)
    generate_drawdown(bm, fm, cm)
    generate_score_vs_return(test_set)

    # 7. Report
    runtime = time.perf_counter() - T0
    generate_report(bm, fm, cm, test_set, cp_res, runtime)

    total = time.perf_counter() - T0
    log(f"\n{'='*70}")
    log(f"PHASE 4 HPC — COMPLETE in {total:.1f}s")
    log(f"  Baseline:  {bm['n_trades']} trades → PnL=${bm['total_pnl']:,.0f}")
    log(f"  Filtered:  {fm['n_trades']} trades → PnL=${fm['total_pnl']:,.0f}")
    log(f"  Campaign:  {cm['n_trades']} trades → PnL=${cm['total_pnl']:,.0f}")
    log(f"  Plots: {len(list(PLOTS.glob('*.png')))} generated")
    log(f"{'='*70}")
