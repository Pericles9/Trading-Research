"""
AlphaMomentum Phase 2 (REVISED) — The Extended Signal Forge
============================================================
Full-day (04:00–16:00 ET) pipeline with halt-stitched Hawkes intensity,
extended CVD/Convexity across the 09:30 transition, halt context features,
and 4-panel anatomy plots.

Key changes from v1:
  - Hawkes kernel freezes S during halts (dt > 5s) — no phantom decay
  - CVD runs from 04:00 pre-market warm-up through 16:00 close
  - New features: is_post_halt, n_halts, max_halt_dur, hawkes_post_halt_surge
  - Anatomy plots: Price+Halts, Full-Day Hawkes, CVD Transition, Halt Zoom
  - Output: feature_matrix_v2_ext.parquet

Requires: PyTorch (CUDA), pandas, numpy, scipy, matplotlib, pyarrow, numba
"""

import os, sys, time, warnings, traceback
import datetime as dt
from pathlib import Path
from collections import defaultdict

import numpy as np
import pandas as pd
import torch
from scipy.signal import savgol_filter
from numba import njit

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec
import matplotlib.dates as mdates
from matplotlib.patches import Rectangle

warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=UserWarning)

# ─── Configuration ───────────────────────────────────────────────────────────
ROOT    = Path(r"D:\Mom_db")
DATA    = ROOT / "data"
PHASE1  = ROOT / "research" / "phase_1_context"
OUT     = ROOT / "research" / "phase_2_signal_forge"
PLOTS   = OUT / "plots_v2"
PLOTS.mkdir(parents=True, exist_ok=True)

# Hawkes parameters
HAWKES_ALPHA = 0.8    # excitation amplitude
HAWKES_BETA  = 1.0    # decay rate (1/beta = 1-second memory)
HAWKES_FREEZE_SEC = 5.0   # freeze S in Hawkes kernel for gaps > 5s
HALT_DETECT_SEC   = 300.0 # real LULD halt detection: gaps > 5 min (300s)

# CVD Convexity
CVD_WINDOW_SEC = 30   # sliding window for 2nd derivative

# Normalization outlier threshold
NORM_LOG_THRESHOLD = 3.0   # |log10(phi)| > 3 → exclude

# Time boundaries (ET)
PM_START_HOUR   = 4    # pre-market warm-up begins
PM_START_MINUTE = 0
RTH_OPEN_HOUR   = 9    # regular trading hours
RTH_OPEN_MINUTE = 30
FLIP_END_HOUR   = 9
FLIP_END_MINUTE = 45
RTH_CLOSE_HOUR  = 16
RTH_CLOSE_MINUTE = 0

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# ─── Logging ─────────────────────────────────────────────────────────────────
LOG_LINES: list[str] = []
T0 = time.perf_counter()
AUDIT_RECORDS: list[dict] = []

def log(msg: str):
    elapsed = time.perf_counter() - T0
    line = f"[{elapsed:8.1f}s] {msg}"
    LOG_LINES.append(line)
    print(line)


# ═══════════════════════════════════════════════════════════════════════════════
#  Utility: ET Timestamp Conversion
# ═══════════════════════════════════════════════════════════════════════════════
def is_dst(date_str: str) -> bool:
    """Check if a date falls in US Eastern Daylight Time (EDT)."""
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
#  HALT-STITCHED Hawkes Kernel
# ═══════════════════════════════════════════════════════════════════════════════
@njit(cache=True)
def _hawkes_scan_halt_aware(dt_arr, alpha, beta, mu, halt_threshold):
    """
    Halt-stitched Hawkes recurrence.

    During normal trading (dt <= halt_threshold):
        S_i = exp(-β * Δt_i) * S_{i-1} + 1
        λ(t_i) = μ + α * S_i

    During a halt (dt > halt_threshold):
        S_i = S_{i-1}  (FREEZE — no decay)
        λ(t_i) = μ + α * S_i  (resumes from frozen state)

    This prevents the Hawkes intensity from decaying to zero during
    a trading halt, preserving the self-exciting momentum signal.
    """
    n = len(dt_arr) + 1
    intensity = np.empty(n, dtype=np.float64)
    accel     = np.empty(n, dtype=np.float64)
    halt_mask = np.zeros(n, dtype=np.int8)      # 1 = first trade after a halt
    S = 0.0
    intensity[0] = mu
    accel[0] = 0.0
    for i in range(1, n):
        d = dt_arr[i - 1]
        if d > halt_threshold:
            # HALT: freeze S — do NOT decay
            halt_mask[i] = 1
            # S stays as-is; just add +1 for this arriving trade
            S = S + 1.0
        else:
            # Normal: exponential decay + excite
            S = np.exp(-beta * d) * S + 1.0
        lam = mu + alpha * S
        intensity[i] = lam
        accel[i] = lam - intensity[i - 1]
    return intensity, accel, halt_mask


def hawkes_intensity_halt_aware(timestamps_sec: np.ndarray,
                                 alpha: float = HAWKES_ALPHA,
                                 beta: float = HAWKES_BETA,
                                 halt_threshold: float = HAWKES_FREEZE_SEC
                                 ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Compute halt-stitched Hawkes intensity over full-day timestamps.
    Returns: (intensity, acceleration, halt_mask)
    """
    n = len(timestamps_sec)
    if n < 2:
        return np.zeros(n), np.zeros(n), np.zeros(n, dtype=np.int8)

    # Estimate baseline μ from active trading time only (exclude halt gaps)
    dt_arr = np.diff(timestamps_sec).astype(np.float64)
    dt_arr = np.maximum(dt_arr, 1e-9)

    active_mask = dt_arr <= halt_threshold
    active_duration = dt_arr[active_mask].sum() if active_mask.any() else 1e-6
    active_trades = active_mask.sum() + 1  # +1 for first trade
    mu = active_trades / max(active_duration, 1e-6)

    return _hawkes_scan_halt_aware(dt_arr, alpha, beta, mu, halt_threshold)


# ═══════════════════════════════════════════════════════════════════════════════
#  Feature: CVD & Convexity (Full-Day)
# ═══════════════════════════════════════════════════════════════════════════════
@njit(cache=True)
def _tick_rule_cvd(prices, volumes):
    """Numba-JIT tick rule → cumulative volume delta."""
    n = len(prices)
    cvd = np.empty(n, dtype=np.float64)
    sign = 1.0
    running = 0.0
    for i in range(n):
        if i > 0:
            if prices[i] > prices[i - 1]:
                sign = 1.0
            elif prices[i] < prices[i - 1]:
                sign = -1.0
        running += sign * volumes[i]
        cvd[i] = running
    return cvd


def compute_cvd(prices: np.ndarray, volumes: np.ndarray) -> np.ndarray:
    """Compute CVD using the tick rule (numba-accelerated)."""
    n = len(prices)
    if n < 2:
        return np.zeros(n)
    return _tick_rule_cvd(prices.astype(np.float64), volumes.astype(np.float64))


def compute_cvd_convexity(timestamps_sec: np.ndarray, cvd: np.ndarray,
                           window_sec: int = CVD_WINDOW_SEC) -> np.ndarray:
    """
    Compute 2nd derivative of CVD resampled to 1-second bins using Savitzky-Golay.
    Returns convexity at original timestamp resolution.
    """
    if len(timestamps_sec) < 10:
        return np.zeros(len(timestamps_sec))

    t_start = timestamps_sec[0]
    t_end = timestamps_sec[-1]
    duration = int(t_end - t_start) + 1

    if duration < 5:
        return np.zeros(len(timestamps_sec))

    # Clamp grid to max 50k seconds (~14 hours) to avoid memory blow-up
    if duration > 50000:
        duration = 50000
        t_end = t_start + duration

    grid_t = np.arange(t_start, t_end + 1, 1.0)
    grid_cvd = np.interp(grid_t, timestamps_sec, cvd)

    win_len = min(window_sec + 1 if window_sec % 2 == 0 else window_sec, len(grid_cvd))
    if win_len < 5:
        win_len = 5
    if win_len > len(grid_cvd):
        win_len = len(grid_cvd)
    if win_len % 2 == 0:
        win_len -= 1
    if win_len < 5:
        return np.zeros(len(timestamps_sec))

    try:
        cvd_2nd = savgol_filter(grid_cvd, window_length=win_len, polyorder=2, deriv=2)
    except Exception:
        return np.zeros(len(timestamps_sec))

    convexity = np.interp(timestamps_sec, grid_t, cvd_2nd)
    return convexity


# ═══════════════════════════════════════════════════════════════════════════════
#  Feature: Order Flow Imbalance (OFI)
# ═══════════════════════════════════════════════════════════════════════════════
@njit(cache=True)
def _ofi_kernel(bid_price, bid_size, ask_price, ask_size):
    """Numba-JIT Order Flow Imbalance kernel."""
    n = len(bid_price)
    ofi = np.zeros(n, dtype=np.float64)
    for i in range(1, n):
        if bid_price[i] >= bid_price[i - 1]:
            d_bid = bid_size[i] - bid_size[i - 1]
        else:
            d_bid = -bid_size[i - 1]
        if ask_price[i] <= ask_price[i - 1]:
            d_ask = ask_size[i] - ask_size[i - 1]
        else:
            d_ask = -ask_size[i - 1]
        ofi[i] = d_bid - d_ask
    return ofi


def compute_ofi(bid_price: np.ndarray, bid_size: np.ndarray,
                ask_price: np.ndarray, ask_size: np.ndarray) -> np.ndarray:
    n = len(bid_price)
    if n < 2:
        return np.zeros(n)
    return _ofi_kernel(
        bid_price.astype(np.float64), bid_size.astype(np.float64),
        ask_price.astype(np.float64), ask_size.astype(np.float64)
    )


# ═══════════════════════════════════════════════════════════════════════════════
#  Halt Detection (Simple Δt-Based)
# ═══════════════════════════════════════════════════════════════════════════════
def detect_halts_from_timestamps(dt_et: pd.Series, threshold_sec: float = HALT_DETECT_SEC
                                  ) -> list[dict]:
    """
    Detect halts as gaps > threshold_sec in ET timestamps.
    Only considers RTH window (09:30–16:00).
    Returns list of {start: Timestamp, end: Timestamp, duration_sec: float}.
    """
    halts = []
    if len(dt_et) < 2:
        return halts

    ts = dt_et.values.astype("datetime64[ns]").astype(np.int64) / 1e9
    diffs = np.diff(ts)

    rth_start_hm = RTH_OPEN_HOUR * 100 + RTH_OPEN_MINUTE  # 930
    rth_end_hm   = RTH_CLOSE_HOUR * 100 + RTH_CLOSE_MINUTE  # 1600

    hours = dt_et.dt.hour.values
    minutes = dt_et.dt.minute.values
    hm = hours * 100 + minutes

    for i in range(len(diffs)):
        if diffs[i] > threshold_sec:
            # Only count as halt if the gap starts within RTH
            if rth_start_hm <= hm[i] < rth_end_hm:
                halts.append({
                    "start": dt_et.iloc[i],
                    "end": dt_et.iloc[i + 1],
                    "duration_sec": float(diffs[i]),
                })
    return halts


# ═══════════════════════════════════════════════════════════════════════════════
#  MAIN PIPELINE: process_event_v2
# ═══════════════════════════════════════════════════════════════════════════════
def process_event(ticker: str, date_str: str, event_row: pd.Series,
                  filtered_dir: str) -> dict | None:
    """
    Process a single event across the FULL DAY (04:00–16:00 ET).
    Halt-stitched Hawkes, full-day CVD, halt context features.
    """
    t_start = time.perf_counter()
    et_offset = utc_to_et_offset_hours(date_str)

    trades_file = DATA / "filtered" / filtered_dir / "trades.parquet"
    quotes_file = DATA / "filtered" / filtered_dir / "quotes.parquet"

    if not trades_file.exists():
        return None

    # ─── Load trades ─────────────────────────────────────────────────────
    try:
        tdf = pd.read_parquet(trades_file, columns=["sip_timestamp", "price", "size"])
    except Exception:
        return None

    if len(tdf) == 0 or "price" not in tdf.columns:
        return None

    tdf = tdf.sort_values("sip_timestamp").reset_index(drop=True)
    tdf["dt_utc"] = pd.to_datetime(tdf["sip_timestamp"], unit="ns")
    tdf["dt_et"] = tdf["dt_utc"] - pd.Timedelta(hours=et_offset)

    # Filter to FULL DAY: 04:00–16:00 ET
    day_start = pd.Timestamp(f"{date_str} 04:00:00")
    day_end   = pd.Timestamp(f"{date_str} 16:00:00")
    tdf = tdf[(tdf["dt_et"] >= day_start) & (tdf["dt_et"] <= day_end)].reset_index(drop=True)

    if len(tdf) < 10:
        return None

    # ─── NORMALIZATION ───────────────────────────────────────────────────
    rth_open = pd.Timestamp(f"{date_str} 09:30:00")
    rth_mask = tdf["dt_et"] >= rth_open
    if rth_mask.sum() == 0:
        return None

    first_rth_price = tdf.loc[rth_mask, "price"].iloc[0]
    adjusted_open = event_row["open"]

    if first_rth_price <= 0 or adjusted_open <= 0:
        return None

    phi = adjusted_open / first_rth_price
    log_phi = np.log10(abs(phi)) if phi > 0 else 0

    if abs(log_phi) > NORM_LOG_THRESHOLD:
        return {"ticker": ticker, "date": date_str, "norm_factor": phi,
                "log_norm_factor": log_phi, "_status": "outlier",
                "_time": time.perf_counter() - t_start}

    tdf["price_adj"] = tdf["price"] * phi

    # ─── REGIME TAGGING (vectorised) ────────────────────────────────────
    et_hour = tdf["dt_et"].dt.hour
    et_minute = tdf["dt_et"].dt.minute
    et_hm = et_hour * 100 + et_minute

    tdf["regime"] = np.where(
        et_hm < 930, 1,          # PRE (04:00–09:29)
        np.where(et_hm < 945, 2, # FLIP (09:30–09:44)
                 3)               # STD  (09:45–16:00)
    )

    trades_pre  = tdf[tdf["regime"] == 1]
    trades_flip = tdf[tdf["regime"] == 2]
    trades_std  = tdf[tdf["regime"] == 3]
    trades_rth  = tdf[tdf["dt_et"] >= rth_open]   # 09:30–16:00

    # ─── HALT DETECTION ──────────────────────────────────────────────────
    halts = detect_halts_from_timestamps(tdf["dt_et"], HALT_DETECT_SEC)
    n_halts = len(halts)
    is_post_halt = int(n_halts > 0)
    max_halt_dur = max((h["duration_sec"] for h in halts), default=0.0)
    total_halt_dur = sum(h["duration_sec"] for h in halts)

    # seconds_since_unhalt: time from last halt end to first FLIP trade
    seconds_since_unhalt = np.nan
    if n_halts > 0 and len(trades_flip) > 0:
        flip_start_ts = trades_flip["dt_et"].iloc[0]
        # Find halts that ended before FLIP
        pre_flip_halts = [h for h in halts if h["end"] < flip_start_ts]
        if pre_flip_halts:
            last_halt_end = max(h["end"] for h in pre_flip_halts)
            seconds_since_unhalt = (flip_start_ts - last_halt_end).total_seconds()

    # ─── FEATURE: Pre-Market Context ─────────────────────────────────────
    pm_high_price = float(trades_pre["price_adj"].max()) if len(trades_pre) > 0 else np.nan
    pm_trade_count = len(trades_pre)

    if pd.notna(pm_high_price) and pm_high_price > 0:
        pm_high_distance = (adjusted_open - pm_high_price) / pm_high_price
    else:
        pm_high_distance = np.nan

    if len(trades_pre) > 0 and len(trades_flip) > 0:
        pre_duration = (trades_pre["dt_et"].iloc[-1] - trades_pre["dt_et"].iloc[0]).total_seconds() / 60
        flip_duration = 15.0
        pre_vol_per_min = trades_pre["size"].sum() / max(pre_duration, 1)
        flip_vol_per_min = trades_flip["size"].sum() / max(flip_duration, 1)
        pm_volume_ratio = flip_vol_per_min / max(pre_vol_per_min, 1)
    else:
        pm_volume_ratio = np.nan

    # ═══════════════════════════════════════════════════════════════════════
    #  FULL-DAY HALT-STITCHED HAWKES (04:00–16:00)
    # ═══════════════════════════════════════════════════════════════════════
    fullday_ts = (tdf["dt_et"] - tdf["dt_et"].iloc[0]).dt.total_seconds().values
    hawkes_lam, hawkes_acc, halt_mask_arr = hawkes_intensity_halt_aware(
        fullday_ts, halt_threshold=HAWKES_FREEZE_SEC)

    # ─── Extract Hawkes stats by regime ──────────────────────────────────
    # FLIP window
    flip_idx = tdf["regime"].values == 2
    if flip_idx.sum() >= 10:
        hawkes_flip_mean = float(np.nanmean(hawkes_lam[flip_idx]))
        hawkes_flip_max  = float(np.nanmax(hawkes_lam[flip_idx]))
        hawkes_acc_flip_mean = float(np.nanmean(hawkes_acc[flip_idx]))
        hawkes_acc_flip_max  = float(np.nanmax(hawkes_acc[flip_idx]))
    else:
        hawkes_flip_mean = hawkes_flip_max = hawkes_acc_flip_mean = hawkes_acc_flip_max = np.nan

    # Pre-Market window
    pre_idx = tdf["regime"].values == 1
    if pre_idx.sum() >= 10:
        hawkes_pre_mean = float(np.nanmean(hawkes_lam[pre_idx]))
        hawkes_pre_max  = float(np.nanmax(hawkes_lam[pre_idx]))
    else:
        hawkes_pre_mean = hawkes_pre_max = np.nan

    # Full RTH (09:30–16:00)
    rth_idx = (tdf["dt_et"] >= rth_open).values
    if rth_idx.sum() >= 10:
        hawkes_rth_mean = float(np.nanmean(hawkes_lam[rth_idx]))
        hawkes_rth_max  = float(np.nanmax(hawkes_lam[rth_idx]))
    else:
        hawkes_rth_mean = hawkes_rth_max = np.nan

    # Full day
    hawkes_fullday_mean = float(np.nanmean(hawkes_lam)) if len(hawkes_lam) > 0 else np.nan
    hawkes_fullday_max  = float(np.nanmax(hawkes_lam)) if len(hawkes_lam) > 0 else np.nan

    # Post-halt surge: max Hawkes in first 60s after each halt resumption
    hawkes_post_halt_surge = np.nan
    if n_halts > 0:
        surges = []
        for h in halts:
            h_end = h["end"]
            h_surge_end = h_end + pd.Timedelta(seconds=60)
            surge_mask = (tdf["dt_et"] >= h_end) & (tdf["dt_et"] < h_surge_end)
            if surge_mask.sum() > 0:
                surges.append(float(np.nanmax(hawkes_lam[surge_mask.values])))
        if surges:
            hawkes_post_halt_surge = max(surges)

    # ═══════════════════════════════════════════════════════════════════════
    #  FULL-DAY CVD & CONVEXITY
    # ═══════════════════════════════════════════════════════════════════════
    prices_all = tdf["price_adj"].values
    volumes_all = tdf["size"].values.astype(float)
    cvd_arr = compute_cvd(prices_all, volumes_all)

    convexity = compute_cvd_convexity(fullday_ts, cvd_arr)

    # CVD stats — FLIP
    if flip_idx.sum() >= 10:
        cvd_flip_final = float(cvd_arr[flip_idx][-1])
        cvd_conv_flip_mean = float(np.nanmean(convexity[flip_idx]))
        cvd_conv_flip_max  = float(np.nanmax(convexity[flip_idx]))
        cvd_conv_flip_sign = float((convexity[flip_idx] > 0).sum() / max(flip_idx.sum(), 1))
    else:
        cvd_flip_final = cvd_conv_flip_mean = cvd_conv_flip_max = cvd_conv_flip_sign = np.nan

    # CVD stats — Full Day
    cvd_fullday_final = float(cvd_arr[-1]) if len(cvd_arr) > 0 else np.nan

    # CVD Convexity — Transition window (09:25–09:35, the "Elbow")
    transition_start = pd.Timestamp(f"{date_str} 09:25:00")
    transition_end   = pd.Timestamp(f"{date_str} 09:35:00")
    trans_mask = ((tdf["dt_et"] >= transition_start) & (tdf["dt_et"] <= transition_end)).values
    if trans_mask.sum() >= 10:
        cvd_conv_transition_mean = float(np.nanmean(convexity[trans_mask]))
        cvd_conv_transition_max  = float(np.nanmax(convexity[trans_mask]))
    else:
        cvd_conv_transition_mean = cvd_conv_transition_max = np.nan

    # ═══════════════════════════════════════════════════════════════════════
    #  OFI (FLIP window — quotes)
    # ═══════════════════════════════════════════════════════════════════════
    ofi_flip_mean = ofi_flip_cum = ofi_flip_max = ofi_flip_imb = np.nan
    ofi_arr = np.array([])

    if quotes_file.exists():
        try:
            qdf = pd.read_parquet(quotes_file, columns=[
                "sip_timestamp", "bid_price", "bid_size", "ask_price", "ask_size"])
            if len(qdf) > 0 and "bid_price" in qdf.columns:
                qdf = qdf.sort_values("sip_timestamp").reset_index(drop=True)
                qdf["dt_utc"] = pd.to_datetime(qdf["sip_timestamp"], unit="ns")
                qdf["dt_et"] = qdf["dt_utc"] - pd.Timedelta(hours=et_offset)

                flip_start = pd.Timestamp(f"{date_str} 09:30:00")
                flip_end   = pd.Timestamp(f"{date_str} 09:45:00")
                qflip = qdf[(qdf["dt_et"] >= flip_start) & (qdf["dt_et"] < flip_end)]

                if len(qflip) >= 10:
                    bp = (qflip["bid_price"].values * phi).astype(np.float64)
                    bs = qflip["bid_size"].values.astype(np.float64)
                    ap = (qflip["ask_price"].values * phi).astype(np.float64)
                    az = qflip["ask_size"].values.astype(np.float64)

                    valid = (bp > 0) & (ap > 0) & (ap > bp)
                    if valid.sum() >= 10:
                        bp, bs, ap, az = bp[valid], bs[valid], ap[valid], az[valid]
                        ofi_arr = compute_ofi(bp, bs, ap, az)
                        ofi_flip_mean = float(np.nanmean(ofi_arr))
                        ofi_flip_cum  = float(np.nansum(ofi_arr))
                        ofi_flip_max  = float(np.nanmax(ofi_arr))
                        nonzero_ofi = ofi_arr[ofi_arr != 0]
                        if len(nonzero_ofi) > 0:
                            ofi_flip_imb = float((nonzero_ofi > 0).sum() / len(nonzero_ofi))
        except Exception:
            pass

    elapsed = time.perf_counter() - t_start

    return {
        "ticker": ticker,
        "date": date_str,
        "gap_pct": event_row["gap_pct"],
        "gap_rank": event_row["gap_rank"],
        "norm_factor": phi,
        "log_norm_factor": log_phi,
        # ── Hawkes (halt-stitched) ──
        "hawkes_intensity_flip_mean": hawkes_flip_mean,
        "hawkes_intensity_flip_max": hawkes_flip_max,
        "hawkes_accel_flip_mean": hawkes_acc_flip_mean,
        "hawkes_accel_flip_max": hawkes_acc_flip_max,
        "hawkes_pre_mean": hawkes_pre_mean,
        "hawkes_pre_max": hawkes_pre_max,
        "hawkes_rth_mean": hawkes_rth_mean,
        "hawkes_rth_max": hawkes_rth_max,
        "hawkes_fullday_mean": hawkes_fullday_mean,
        "hawkes_fullday_max": hawkes_fullday_max,
        "hawkes_post_halt_surge": hawkes_post_halt_surge,
        # ── CVD (full-day) ──
        "cvd_flip_final": cvd_flip_final,
        "cvd_fullday_final": cvd_fullday_final,
        "cvd_convexity_flip_mean": cvd_conv_flip_mean,
        "cvd_convexity_flip_max": cvd_conv_flip_max,
        "cvd_convexity_flip_sign_ratio": cvd_conv_flip_sign,
        "cvd_convexity_transition_mean": cvd_conv_transition_mean,
        "cvd_convexity_transition_max": cvd_conv_transition_max,
        # ── OFI ──
        "ofi_flip_mean": ofi_flip_mean,
        "ofi_flip_cumulative": ofi_flip_cum,
        "ofi_flip_max": ofi_flip_max,
        "ofi_flip_imbalance_ratio": ofi_flip_imb,
        # ── Pre-Market Context ──
        "pm_high_distance": pm_high_distance,
        "pm_high_price": pm_high_price,
        "pm_volume_ratio": pm_volume_ratio,
        "pm_trade_count": pm_trade_count,
        # ── Halt Context ──
        "is_post_halt": is_post_halt,
        "n_halts": n_halts,
        "max_halt_duration_sec": max_halt_dur,
        "total_halt_duration_sec": total_halt_dur,
        "seconds_since_unhalt": seconds_since_unhalt,
        # ── Internal ──
        "_status": "ok",
        "_time": elapsed,
        "_n_trades_total": len(tdf),
        "_n_trades_flip": int(flip_idx.sum()),
        "_n_quotes_flip": len(ofi_arr) if isinstance(ofi_arr, np.ndarray) else 0,
        # Time-series stashed for top ~50 runners (anatomy plots)
        "_tdf": tdf,
        "_hawkes_lam": hawkes_lam,
        "_hawkes_acc": hawkes_acc,
        "_halt_mask": halt_mask_arr,
        "_cvd": cvd_arr,
        "_cvd_convexity": convexity,
        "_halts": halts,
    }


# ═══════════════════════════════════════════════════════════════════════════════
#  4-Panel Anatomy Plot Generator (Full Day)
# ═══════════════════════════════════════════════════════════════════════════════
def generate_anatomy_plot_v2(result: dict, save_path: Path):
    """
    Generate 4-panel full-day anatomy plot:
      Panel 1: Price (04:00–16:00) with halt zones grey, PM light-blue
      Panel 2: Full-day Hawkes λ(t) with halt markers
      Panel 3: CVD & Convexity with 09:30 transition highlighted
      Panel 4: Halt resumption micro-zoom (first 60s post-halt)
    """
    ticker = result["ticker"]
    date_str = result["date"]
    tdf = result.get("_tdf")
    hawkes_lam = result.get("_hawkes_lam", np.array([]))
    hawkes_acc = result.get("_hawkes_acc", np.array([]))
    halt_mask_arr = result.get("_halt_mask", np.array([]))
    cvd_arr = result.get("_cvd", np.array([]))
    convexity = result.get("_cvd_convexity", np.array([]))
    halts = result.get("_halts", [])
    phi = result["norm_factor"]

    if tdf is None or len(tdf) < 10:
        return False

    times = tdf["dt_et"].values
    prices = tdf["price_adj"].values

    fig = plt.figure(figsize=(20, 22))
    gs = GridSpec(4, 1, height_ratios=[2.5, 1.5, 1.5, 1.5], hspace=0.3)

    # ─── Panel 1: Price with Halt Zones ──────────────────────────────────
    ax1 = fig.add_subplot(gs[0])

    # Background: pre-market zone
    pm_start = pd.Timestamp(f"{date_str} 04:00:00")
    rth_open = pd.Timestamp(f"{date_str} 09:30:00")
    rth_close = pd.Timestamp(f"{date_str} 16:00:00")

    ax1.axvspan(pm_start, rth_open, color="#E3F2FD", alpha=0.4, label="Pre-Market")

    # Halt zones in grey
    for i, h in enumerate(halts):
        lbl = "Halt Zone" if i == 0 else None
        ax1.axvspan(h["start"], h["end"], color="#9E9E9E", alpha=0.35, label=lbl)

    # Draw price by regime
    pre_mask = tdf["regime"].values == 1
    flip_mask = tdf["regime"].values == 2
    std_mask = tdf["regime"].values == 3

    if pre_mask.sum() > 0:
        ax1.plot(times[pre_mask], prices[pre_mask], color="#42A5F5",
                 linewidth=0.6, alpha=0.7, label="Pre-Market")
    if flip_mask.sum() > 0:
        ax1.plot(times[flip_mask], prices[flip_mask], color="#1565C0",
                 linewidth=1.4, alpha=0.95, label="FLIP (09:30–09:45)")
    if std_mask.sum() > 0:
        ax1.plot(times[std_mask], prices[std_mask], color="#2E7D32",
                 linewidth=0.9, alpha=0.8, label="STD (09:45–16:00)")

    # PM High line
    pm_high = result.get("pm_high_price")
    if pd.notna(pm_high) and pm_high > 0:
        ax1.axhline(pm_high, color="#FF9800", linewidth=1.5, linestyle="--",
                     alpha=0.8, label=f"PM High: ${pm_high:.2f}")

    # 9:30 vertical line
    ax1.axvline(rth_open, color="red", linewidth=1.2, alpha=0.6, linestyle=":")
    ax1.annotate("9:30 OPEN", xy=(rth_open, ax1.get_ylim()[1] if ax1.get_ylim()[1] != 1 else prices.max()),
                 fontsize=9, color="red", alpha=0.7, va="top")

    ax1.set_ylabel("Price (Split-Adjusted)", fontsize=11)
    halt_str = f"  |  {len(halts)} halt(s)" if halts else ""
    ax1.set_title(f"Extended Anatomy — {ticker} ({date_str})\n"
                  f"Gap: {result['gap_pct']*100:.1f}%  |  φ={phi:.4f}"
                  f"  |  Rank: #{int(result['gap_rank'])}{halt_str}",
                  fontsize=14, fontweight="bold")
    ax1.legend(fontsize=8, loc="upper left", ncol=2)
    ax1.grid(alpha=0.2)
    ax1.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))

    # ─── Panel 2: Full-Day Hawkes with Halt Markers ──────────────────────
    ax2 = fig.add_subplot(gs[1], sharex=ax1)

    if len(hawkes_lam) == len(tdf):
        ax2.plot(times, hawkes_lam, color="#E91E63", linewidth=0.9, alpha=0.9, label="λ(t)")

        # Mark halt freeze points
        if len(halt_mask_arr) == len(tdf):
            halt_points = halt_mask_arr.astype(bool)
            if halt_points.any():
                ax2.scatter(times[halt_points], hawkes_lam[halt_points],
                           color="#FF9800", s=15, zorder=5, marker="^",
                           label="Halt Resume")

        # Shade halt zones
        for h in halts:
            ax2.axvspan(h["start"], h["end"], color="#9E9E9E", alpha=0.25)

        # Pre-market / RTH boundary
        ax2.axvline(rth_open, color="red", linewidth=1, alpha=0.4, linestyle=":")

        ax2b = ax2.twinx()
        ax2b.fill_between(times, hawkes_acc, 0, where=hawkes_acc > 0,
                          color="#4CAF50", alpha=0.15, label="Δλ > 0")
        ax2b.fill_between(times, hawkes_acc, 0, where=hawkes_acc < 0,
                          color="#F44336", alpha=0.15, label="Δλ < 0")
        ax2b.set_ylabel("Δλ", fontsize=10, color="#666")
        ax2b.tick_params(axis="y", labelcolor="#666")

    ax2.set_ylabel("Hawkes λ(t) [halt-stitched]", fontsize=11, color="#E91E63")
    ax2.tick_params(axis="y", labelcolor="#E91E63")
    ax2.set_title("Full-Day Halt-Stitched Hawkes Intensity", fontsize=11)
    ax2.legend(fontsize=8, loc="upper right")
    ax2.grid(alpha=0.2)
    ax2.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))

    # ─── Panel 3: CVD + Convexity at 09:30 Transition ───────────────────
    ax3 = fig.add_subplot(gs[2], sharex=ax1)

    if len(cvd_arr) == len(tdf):
        ax3.plot(times, cvd_arr, color="#1565C0", linewidth=1.2, alpha=0.9, label="CVD")
        ax3.fill_between(times, cvd_arr, 0, alpha=0.08, color="#1565C0")

        if len(convexity) == len(tdf):
            ax3b = ax3.twinx()
            ax3b.plot(times, convexity, color="#FF5722", linewidth=0.7,
                      alpha=0.6, label="CVD'' (Convexity)")
            ax3b.axhline(0, color="#FF5722", linewidth=0.5, alpha=0.3)
            ax3b.set_ylabel("CVD'' (Convexity)", fontsize=10, color="#FF5722")
            ax3b.tick_params(axis="y", labelcolor="#FF5722")

        # Highlight transition window (09:25–09:35)
        trans_start = pd.Timestamp(f"{date_str} 09:25:00")
        trans_end   = pd.Timestamp(f"{date_str} 09:35:00")
        ax3.axvspan(trans_start, trans_end, color="#FFF9C4", alpha=0.5, label="09:30 Transition")
        ax3.axvline(rth_open, color="red", linewidth=1, alpha=0.4, linestyle=":")

    ax3.set_ylabel("CVD (Shares)", fontsize=11, color="#1565C0")
    ax3.tick_params(axis="y", labelcolor="#1565C0")
    ax3.set_title("CVD & Convexity — Full Day with 09:30 Transition", fontsize=11)
    ax3.legend(fontsize=8, loc="upper left")
    ax3.grid(alpha=0.2)
    ax3.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))

    # ─── Panel 4: Halt Resumption Micro-Zoom ─────────────────────────────
    ax4 = fig.add_subplot(gs[3])

    if halts and len(hawkes_lam) == len(tdf):
        # Pick the longest halt (most dramatic)
        biggest_halt = max(halts, key=lambda h: h["duration_sec"])
        zoom_start = biggest_halt["start"] - pd.Timedelta(seconds=30)
        zoom_end   = biggest_halt["end"] + pd.Timedelta(seconds=60)

        zoom_mask = ((tdf["dt_et"] >= zoom_start) & (tdf["dt_et"] <= zoom_end)).values

        if zoom_mask.sum() >= 5:
            zt = times[zoom_mask]
            zp = prices[zoom_mask]
            zl = hawkes_lam[zoom_mask]

            ax4.plot(zt, zp, color="#1565C0", linewidth=1.5, alpha=0.9, label="Price")
            ax4.axvspan(biggest_halt["start"], biggest_halt["end"],
                       color="#9E9E9E", alpha=0.4, label=f"Halt ({biggest_halt['duration_sec']:.0f}s)")

            ax4b = ax4.twinx()
            ax4b.plot(zt, zl, color="#E91E63", linewidth=1.5, alpha=0.9, label="λ(t)")
            ax4b.set_ylabel("Hawkes λ(t)", fontsize=10, color="#E91E63")
            ax4b.tick_params(axis="y", labelcolor="#E91E63")

            lines1, labels1 = ax4.get_legend_handles_labels()
            lines2, labels2 = ax4b.get_legend_handles_labels()
            ax4.legend(lines1 + lines2, labels1 + labels2, fontsize=8, loc="upper left")

            ax4.set_title(f"Halt Resumption Micro-Zoom — "
                         f"({biggest_halt['start'].strftime('%H:%M:%S')}–"
                         f"{biggest_halt['end'].strftime('%H:%M:%S')})",
                         fontsize=11)
        else:
            ax4.text(0.5, 0.5, "Insufficient data around halt",
                    ha="center", va="center", transform=ax4.transAxes, fontsize=12, color="#999")
            ax4.set_title("Halt Resumption Micro-Zoom", fontsize=11)
    else:
        # No halts — show FLIP micro-zoom (09:30–09:35) instead
        flip_zoom_start = pd.Timestamp(f"{date_str} 09:30:00")
        flip_zoom_end   = pd.Timestamp(f"{date_str} 09:35:00")
        zoom_mask = ((tdf["dt_et"] >= flip_zoom_start) & (tdf["dt_et"] <= flip_zoom_end)).values

        if zoom_mask.sum() >= 5:
            zt = times[zoom_mask]
            zp = prices[zoom_mask]
            zl = hawkes_lam[zoom_mask] if len(hawkes_lam) == len(tdf) else np.zeros(zoom_mask.sum())

            ax4.plot(zt, zp, color="#1565C0", linewidth=1.5, alpha=0.9, label="Price")

            ax4b = ax4.twinx()
            ax4b.plot(zt, zl, color="#E91E63", linewidth=1.5, alpha=0.9, label="λ(t)")
            ax4b.set_ylabel("Hawkes λ(t)", fontsize=10, color="#E91E63")
            ax4b.tick_params(axis="y", labelcolor="#E91E63")

            lines1, labels1 = ax4.get_legend_handles_labels()
            lines2, labels2 = ax4b.get_legend_handles_labels()
            ax4.legend(lines1 + lines2, labels1 + labels2, fontsize=8, loc="upper left")

            ax4.set_title("Open Micro-Zoom (09:30–09:35) — No Halts Detected", fontsize=11)
        else:
            ax4.text(0.5, 0.5, "No halt / insufficient open data",
                    ha="center", va="center", transform=ax4.transAxes, fontsize=12, color="#999")
            ax4.set_title("Panel 4 — Micro-Zoom", fontsize=11)

    ax4.set_xlabel("Time (ET)", fontsize=11)
    ax4.set_ylabel("Price (Split-Adjusted)", fontsize=11)
    ax4.grid(alpha=0.2)
    ax4.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M:%S"))

    fig.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return True


# ═══════════════════════════════════════════════════════════════════════════════
#  Intensity Heatmap Generator (Full Day)
# ═══════════════════════════════════════════════════════════════════════════════
def generate_intensity_heatmap_v2(all_events: list[dict], save_path: Path):
    """
    Full-day intensity heatmap: 5-minute bins from 04:00 to 16:00.
    Rows: events ranked by gap_pct.
    """
    # 5-minute bins: 04:00 to 16:00 = 144 bins
    bin_start_min = 4 * 60  # 04:00 in minutes-since-midnight
    bin_end_min   = 16 * 60  # 16:00
    bin_size = 5
    n_bins = (bin_end_min - bin_start_min) // bin_size

    bin_labels = []
    for b in range(n_bins):
        total_min = bin_start_min + b * bin_size
        h = total_min // 60
        m = total_min % 60
        bin_labels.append(f"{h:02d}:{m:02d}")

    rows = []
    labels = []
    for evt in all_events:
        tdf = evt.get("_tdf")
        lam = evt.get("_hawkes_lam", np.array([]))
        if tdf is None or len(lam) == 0 or len(lam) != len(tdf):
            continue

        minutes = tdf["dt_et"].dt.hour * 60 + tdf["dt_et"].dt.minute

        intensity_row = np.full(n_bins, np.nan)
        for b in range(n_bins):
            target_start = bin_start_min + b * bin_size
            target_end   = target_start + bin_size
            mask = (minutes >= target_start) & (minutes < target_end)
            if mask.sum() > 0:
                intensity_row[b] = np.mean(lam[mask.values])

        rows.append(intensity_row)
        halt_str = f" [{evt.get('n_halts',0)}H]" if evt.get("n_halts", 0) > 0 else ""
        labels.append(f"{evt['ticker']} ({evt['gap_pct']*100:.0f}%){halt_str}")

    if not rows:
        return

    heatmap = np.array(rows)

    # Normalize per row
    for i in range(len(heatmap)):
        row_max = np.nanmax(heatmap[i])
        if row_max > 0:
            heatmap[i] /= row_max

    fig, ax = plt.subplots(figsize=(22, max(4, len(rows) * 0.5)))
    im = ax.imshow(heatmap, aspect="auto", cmap="hot_r", interpolation="nearest")

    # Show every 6th label (every 30 min)
    tick_step = 6
    ax.set_xticks(range(0, n_bins, tick_step))
    ax.set_xticklabels([bin_labels[i] for i in range(0, n_bins, tick_step)], fontsize=8, rotation=45)
    ax.set_yticks(range(len(labels)))
    ax.set_yticklabels(labels, fontsize=8)

    # 9:30 vertical marker
    open_bin = (9 * 60 + 30 - bin_start_min) // bin_size
    ax.axvline(open_bin, color="lime", linewidth=2, linestyle="--", alpha=0.8)
    ax.annotate("9:30", xy=(open_bin, -0.5), fontsize=8, color="lime", fontweight="bold")

    # 9:45 marker
    flip_end_bin = (9 * 60 + 45 - bin_start_min) // bin_size
    ax.axvline(flip_end_bin, color="cyan", linewidth=1.5, linestyle="--", alpha=0.6)

    ax.set_title("Full-Day Hawkes Intensity Heatmap (Halt-Stitched)",
                 fontsize=14, fontweight="bold")
    ax.set_xlabel("Time (ET)", fontsize=11)

    plt.colorbar(im, ax=ax, label="Normalized Intensity", shrink=0.8)
    fig.tight_layout()
    fig.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.close(fig)


# ═══════════════════════════════════════════════════════════════════════════════
#  MAIN EXECUTION
# ═══════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    log(f"Phase 2 (REVISED) — Extended Signal Forge — GPU={DEVICE}")
    log(f"  Hawkes freeze: {HAWKES_FREEZE_SEC}s | Halt detect: {HALT_DETECT_SEC}s | α={HAWKES_ALPHA} β={HAWKES_BETA}")
    log(f"  Timeline: 04:00–16:00 ET (full day)")
    log(f"Loading scanner context …")

    scanner = pd.read_parquet(PHASE1 / "scanner_context.parquet")
    log(f"  {len(scanner):,} events loaded")

    # Build filtered directory lookup
    filt_dirs = set(os.listdir(DATA / "filtered"))

    def find_filtered_dir(ticker, date):
        prefix = f"{ticker}_{date}_"
        matches = [d for d in filt_dirs if d.startswith(prefix)]
        return matches[0] if matches else None

    # Sort by gap_pct descending so top runners are processed first
    scanner = scanner.sort_values("gap_pct", ascending=False).reset_index(drop=True)

    # Process all events
    results = []
    skipped = 0
    outliers = 0
    errors = 0

    log(f"Processing {len(scanner):,} events …")
    for idx, row in scanner.iterrows():
        ticker = row["ticker"]
        date_str = row["date"]
        fdir = find_filtered_dir(ticker, date_str)

        if fdir is None:
            skipped += 1
            continue

        try:
            result = process_event(ticker, date_str, row, fdir)
            if result is None:
                skipped += 1
            elif result.get("_status") == "outlier":
                outliers += 1
                AUDIT_RECORDS.append({
                    "ticker": ticker, "date": date_str,
                    "status": "outlier",
                    "norm_factor": result["norm_factor"],
                    "detail": f"log10(phi)={result['log_norm_factor']:.2f}"
                })
            else:
                results.append(result)
                # Free time-series from non-top events to save RAM.
                # Preserve first 50 results (top runners) for anatomy plots.
                if len(results) > 50:
                    strip_idx = len(results) - 51
                    if strip_idx >= 50:
                        old = results[strip_idx]
                        for key in ["_tdf", "_hawkes_lam", "_hawkes_acc",
                                    "_halt_mask", "_cvd", "_cvd_convexity", "_halts"]:
                            old.pop(key, None)
        except Exception as e:
            errors += 1
            AUDIT_RECORDS.append({
                "ticker": ticker, "date": date_str,
                "status": "error",
                "detail": str(e)[:200]
            })

        # Progress logging
        done = len(results) + skipped + outliers + errors
        if done % 200 == 0 or done == len(scanner):
            rate = done / max(time.perf_counter() - T0, 0.1)
            eta = (len(scanner) - done) / max(rate, 0.01)
            log(f"  Progress: {done}/{len(scanner)} "
                f"(ok={len(results)} skip={skipped} outlier={outliers} err={errors}) "
                f"ETA={eta:.0f}s")

    log(f"DONE: {len(results)} events processed, {skipped} skipped, "
        f"{outliers} outliers, {errors} errors")

    # ─── Find biggest "Halt-Runner" ──────────────────────────────────────
    # For the proof chart, prefer genuine LULD halts (max halt < 1hr)
    # with the most halt events and high Hawkes surge, among events
    # that still have _tdf preserved (top 50 by gap_pct)
    halt_runners_all = [r for r in results if r.get("n_halts", 0) > 0]
    log(f"  {len(halt_runners_all)} events with halts detected")

    # Genuine LULD candidates: have _tdf, max halt < 3600s, at least 2 halts
    luld_candidates = [r for r in halt_runners_all
                       if r.get("_tdf") is not None
                       and 0 < r.get("max_halt_duration_sec", 0) < 3600
                       and r.get("n_halts", 0) >= 2]
    # Sort by n_halts * post_halt_surge (prefer dramatic resumptions)
    luld_candidates.sort(
        key=lambda r: r.get("n_halts", 0) * max(r.get("hawkes_post_halt_surge", 0), 1),
        reverse=True)

    # Fallback: any halt-runner with _tdf
    if not luld_candidates:
        luld_candidates = [r for r in halt_runners_all if r.get("_tdf") is not None]
        luld_candidates.sort(key=lambda r: r.get("n_halts", 0), reverse=True)

    if luld_candidates:
        top_halt = luld_candidates[0]
        log(f"  Best halt-runner: {top_halt['ticker']} {top_halt['date']} "
            f"({top_halt['n_halts']} halts, max {top_halt['max_halt_duration_sec']:.0f}s, "
            f"surge λ={top_halt.get('hawkes_post_halt_surge', 0):.1f})")

    # ─── Generate anatomy plots for top 10 + biggest halt-runner ─────────
    log(f"Generating 4-panel anatomy plots …")
    anatomy_count = 0
    plotted_keys = set()

    # Always plot the best halt-runner first (the proof chart)
    if luld_candidates:
        r = luld_candidates[0]
        save_path = PLOTS / f"HALT_RUNNER_{r['ticker']}_{r['date']}.png"
        if generate_anatomy_plot_v2(r, save_path):
            anatomy_count += 1
            plotted_keys.add((r["ticker"], r["date"]))
            log(f"  ★ HALT_RUNNER_{r['ticker']}_{r['date']}.png (PROOF CHART)")

    # Then top runners by gap_pct
    for r in results[:50]:
        if anatomy_count >= 12:
            break
        key = (r["ticker"], r["date"])
        if key in plotted_keys:
            continue
        if r.get("_tdf") is None:
            continue
        save_path = PLOTS / f"anatomy_{r['ticker']}_{r['date']}.png"
        if generate_anatomy_plot_v2(r, save_path):
            anatomy_count += 1
            plotted_keys.add(key)
            halt_tag = f" [{r.get('n_halts',0)} halts]" if r.get("n_halts", 0) > 0 else ""
            log(f"  Saved anatomy_{r['ticker']}_{r['date']}.png{halt_tag}")

    log(f"  {anatomy_count} anatomy plots generated")

    # ─── Generate full-day intensity heatmap ─────────────────────────────
    log(f"Generating full-day intensity heatmap …")
    heatmap_events = [r for r in results[:100]
                      if r.get("_hawkes_lam") is not None and len(r.get("_hawkes_lam", [])) > 0][:30]
    generate_intensity_heatmap_v2(heatmap_events, PLOTS / "intensity_heatmap_v2.png")
    log(f"  Heatmap generated with {len(heatmap_events)} events")

    # ─── Assemble feature_matrix_v2_ext.parquet ──────────────────────────
    log(f"Assembling feature_matrix_v2_ext.parquet …")

    feature_cols = [
        "ticker", "date", "gap_pct", "gap_rank",
        "norm_factor", "log_norm_factor",
        # Hawkes (halt-stitched)
        "hawkes_intensity_flip_mean", "hawkes_intensity_flip_max",
        "hawkes_accel_flip_mean", "hawkes_accel_flip_max",
        "hawkes_pre_mean", "hawkes_pre_max",
        "hawkes_rth_mean", "hawkes_rth_max",
        "hawkes_fullday_mean", "hawkes_fullday_max",
        "hawkes_post_halt_surge",
        # CVD
        "cvd_flip_final", "cvd_fullday_final",
        "cvd_convexity_flip_mean", "cvd_convexity_flip_max",
        "cvd_convexity_flip_sign_ratio",
        "cvd_convexity_transition_mean", "cvd_convexity_transition_max",
        # OFI
        "ofi_flip_mean", "ofi_flip_cumulative", "ofi_flip_max", "ofi_flip_imbalance_ratio",
        # Pre-Market Context
        "pm_high_distance", "pm_high_price", "pm_volume_ratio", "pm_trade_count",
        # Halt Context
        "is_post_halt", "n_halts", "max_halt_duration_sec", "total_halt_duration_sec",
        "seconds_since_unhalt",
    ]

    fm_rows = []
    for r in results:
        fm_rows.append({k: r.get(k) for k in feature_cols})

    fm = pd.DataFrame(fm_rows)
    fm.to_parquet(OUT / "feature_matrix_v2_ext.parquet", index=False)
    log(f"  Saved feature_matrix_v2_ext.parquet: {len(fm)} rows × {len(fm.columns)} cols")

    # ─── Feature statistics ──────────────────────────────────────────────
    log(f"\n  === Feature Statistics ===")
    for col in feature_cols[4:]:  # skip ticker, date, gap_pct, gap_rank
        vals = fm[col].dropna()
        if len(vals) > 0:
            log(f"    {col:42s}  n={len(vals):5d}  mean={vals.mean():12.4f}  "
                f"median={vals.median():12.4f}  std={vals.std():12.4f}")

    # ─── Halt Context Summary ────────────────────────────────────────────
    log(f"\n  === Halt Context Summary ===")
    halt_events = fm[fm["is_post_halt"] == 1]
    log(f"    Events with halts: {len(halt_events)} / {len(fm)} "
        f"({100*len(halt_events)/max(len(fm),1):.1f}%)")
    if len(halt_events) > 0:
        log(f"    Avg halts per event: {halt_events['n_halts'].mean():.1f}")
        log(f"    Max halt duration: {halt_events['max_halt_duration_sec'].max():.0f}s")
        log(f"    Avg post-halt surge λ: {halt_events['hawkes_post_halt_surge'].mean():.1f}")
        log(f"    Top 5 halt-runners by max halt duration:")
        top5 = halt_events.nlargest(5, "max_halt_duration_sec")
        for _, row in top5.iterrows():
            log(f"      {row['ticker']:8s} {row['date']}  "
                f"halts={int(row['n_halts'])}  max_dur={row['max_halt_duration_sec']:.0f}s  "
                f"surge_λ={row['hawkes_post_halt_surge']:.1f}")

    # ─── Forge Audit Log v2 ──────────────────────────────────────────────
    total_time = time.perf_counter() - T0
    log(f"\nWriting Forge_Audit_Log_v2.md …")

    proc_times = [r.get("_time", 0) for r in results]
    gpu_mem = torch.cuda.max_memory_allocated() / (1024**2) if torch.cuda.is_available() else 0

    audit_log = f"""# Phase 2 (REVISED) — Extended Signal Forge — Audit Log
**Generated:** {dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Total execution time:** {total_time:.1f}s
**GPU Device:** {DEVICE} ({torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'N/A'})
**Peak GPU Memory:** {gpu_mem:.1f} MB
**Timeline:** 04:00–16:00 ET (full day)
**Hawkes Freeze Threshold:** {HAWKES_FREEZE_SEC}s
**LULD Halt Detection Threshold:** {HALT_DETECT_SEC}s

## Processing Summary
| Metric | Value |
|---|---|
| Events in scanner | {len(scanner):,} |
| Events with filtered data | {len(scanner) - skipped:,} |
| Successfully processed | {len(results):,} |
| Skipped (no data) | {skipped:,} |
| Norm factor outliers | {outliers:,} |
| Errors | {errors:,} |
| **Feature matrix rows** | **{len(fm):,}** |
| **Feature matrix columns** | **{len(fm.columns)}** |
| Events with halts | {len(halt_events):,} |
| Anatomy plots | {anatomy_count} |

## Processing Time
| Stat | Value |
|---|---|
| Mean per event | {np.mean(proc_times):.3f}s |
| Median per event | {np.median(proc_times):.3f}s |
| Max per event | {np.max(proc_times):.3f}s |
| Total wall-clock | {total_time:.1f}s |

## Hawkes Parameters (Halt-Stitched)
| Param | Value |
|---|---|
| α (excitation) | {HAWKES_ALPHA} |
| β (decay) | {HAWKES_BETA} |
| μ (baseline) | Estimated per-event (active time only) |
| Hawkes freeze threshold | {HAWKES_FREEZE_SEC}s |
| Halt detect threshold | {HALT_DETECT_SEC}s (LULD-style) |
| Halt behaviour | S frozen (no decay) during gap > freeze threshold |

## Key Changes from v1
- Hawkes kernel freezes S during halts — no phantom decay to zero
- Full-day timeline (04:00–16:00) instead of FLIP-only
- CVD runs across pre-market → RTH transition
- New features: is_post_halt, n_halts, halt durations, post-halt surge λ
- CVD Convexity measured at the 09:30 transition ("Elbow" window)
- 4-panel anatomy plots with halt zones + micro-zoom

## Normalization Factor Outliers ($|\\log_{{10}}(\\phi)| > {NORM_LOG_THRESHOLD}$)
"""
    outlier_records = [a for a in AUDIT_RECORDS if a["status"] == "outlier"]
    if outlier_records:
        audit_log += "| Ticker | Date | φ | Detail |\n|---|---|---|---|\n"
        for a in outlier_records[:50]:
            audit_log += f"| {a['ticker']} | {a['date']} | {a['norm_factor']:.6f} | {a['detail']} |\n"
    else:
        audit_log += "No normalization outliers detected.\n"

    audit_log += f"""
## Error Log
"""
    error_records = [a for a in AUDIT_RECORDS if a["status"] == "error"]
    if error_records:
        audit_log += "| Ticker | Date | Error |\n|---|---|---|\n"
        for a in error_records[:30]:
            audit_log += f"| {a['ticker']} | {a['date']} | {a['detail'][:100]} |\n"
    else:
        audit_log += "No processing errors.\n"

    audit_log += f"""
## Execution Trace
```
{chr(10).join(LOG_LINES)}
```
"""

    (OUT / "Forge_Audit_Log_v2.md").write_text(audit_log, encoding="utf-8")
    log(f"Forge_Audit_Log_v2.md written")
    log(f"PHASE 2 (REVISED) BUILD COMPLETE in {total_time:.1f}s")
