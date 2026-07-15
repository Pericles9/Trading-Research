"""
AlphaMomentum Phase 2 — The Signal Forge (GPU-Accelerated)
==========================================================
Transforms raw tick-level trades/quotes into a feature matrix of stochastic
momentum signals using PyTorch CUDA kernels.

Pipeline: Normalization → Regime Tag → GPU Features → Feature Assembly → Plots

Requires: PyTorch (CUDA), pandas, numpy, scipy, matplotlib, pyarrow
"""

import os, sys, time, warnings, traceback
import datetime as dt
from pathlib import Path
from collections import defaultdict

import numpy as np
import pandas as pd
import torch
from scipy.signal import savgol_filter
from numba import njit, prange

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec
import matplotlib.dates as mdates

warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=UserWarning)

# ─── Configuration ───────────────────────────────────────────────────────────
ROOT    = Path(r"D:\Mom_db")
DATA    = ROOT / "data"
PHASE1  = ROOT / "research" / "phase_1_context"
OUT     = ROOT / "research" / "phase_2_signal_forge"
PLOTS   = OUT / "plots"
PLOTS.mkdir(parents=True, exist_ok=True)

# Hawkes parameters
HAWKES_ALPHA = 0.8    # excitation amplitude
HAWKES_BETA  = 1.0    # decay rate (1/beta = 1-second memory)

# CVD Convexity
CVD_WINDOW_SEC = 30   # sliding window for 2nd derivative
CVD_DELTA_SEC  = 15   # half-window for finite difference

# Normalization outlier threshold
NORM_LOG_THRESHOLD = 3.0   # |log10(phi)| > 3 → exclude

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
    # DST: 2nd Sunday of March to 1st Sunday of November
    mar1 = dt.date(year, 3, 1)
    mar_second_sun = mar1 + dt.timedelta(days=(6 - mar1.weekday()) % 7 + 7)
    nov1 = dt.date(year, 11, 1)
    nov_first_sun = nov1 + dt.timedelta(days=(6 - nov1.weekday()) % 7)
    return mar_second_sun <= d < nov_first_sun


def utc_to_et_offset_hours(date_str: str) -> int:
    """Return hours to subtract from UTC to get ET."""
    return 4 if is_dst(date_str) else 5


# ═══════════════════════════════════════════════════════════════════════════════
#  GPU Kernel: Hawkes Intensity (Associative Scan)
# ═══════════════════════════════════════════════════════════════════════════════
@njit(cache=True)
def _hawkes_scan(dt_arr, alpha, beta, mu):
    """Numba-JIT Hawkes recurrence: S_i = exp(-β Δt_i)*S_{i-1} + 1."""
    n = len(dt_arr) + 1
    intensity = np.empty(n, dtype=np.float64)
    accel     = np.empty(n, dtype=np.float64)
    S = 0.0
    intensity[0] = mu
    accel[0] = 0.0
    for i in range(1, n):
        S = np.exp(-beta * dt_arr[i - 1]) * S + 1.0
        lam = mu + alpha * S
        intensity[i] = lam
        accel[i] = lam - intensity[i - 1]
    return intensity, accel


def hawkes_intensity_gpu(timestamps_sec: np.ndarray, alpha: float = HAWKES_ALPHA,
                         beta: float = HAWKES_BETA) -> tuple[np.ndarray, np.ndarray]:
    """
    Compute Hawkes intensity λ(t) and acceleration Δλ(t) via numba JIT.
    The exponential-kernel recurrence is inherently sequential; numba
    compiles it to machine code for ~100x speedup over Python loops.
    GPU (PyTorch) is reserved for truly parallelisable batch ops.
    """
    n = len(timestamps_sec)
    if n < 2:
        return np.zeros(n), np.zeros(n)

    duration = timestamps_sec[-1] - timestamps_sec[0]
    mu = n / max(duration, 1e-6)

    dt_arr = np.diff(timestamps_sec).astype(np.float64)
    dt_arr = np.maximum(dt_arr, 1e-9)

    return _hawkes_scan(dt_arr, alpha, beta, mu)


# Alias for backward compat — same function, chunks are no longer needed
hawkes_intensity_gpu_batched = hawkes_intensity_gpu


# ═══════════════════════════════════════════════════════════════════════════════
#  Feature: CVD & Convexity
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
            # else keep previous sign
        running += sign * volumes[i]
        cvd[i] = running
    return cvd


def compute_cvd(prices: np.ndarray, volumes: np.ndarray) -> np.ndarray:
    """Compute Cumulative Volume Delta using the tick rule (numba-accelerated)."""
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

    # Resample CVD to 1-second bins
    t_start = timestamps_sec[0]
    t_end = timestamps_sec[-1]
    duration = int(t_end - t_start) + 1

    if duration < 5:
        return np.zeros(len(timestamps_sec))

    # Create 1-second grid
    grid_t = np.arange(t_start, t_end + 1, 1.0)
    # Forward-fill CVD onto grid
    grid_cvd = np.interp(grid_t, timestamps_sec, cvd)

    # Savitzky-Golay 2nd derivative
    # Window length must be odd and >= polyorder+2
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

    # Map back to original timestamps
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
    """Compute OFI from top-of-book quote updates (numba-accelerated)."""
    n = len(bid_price)
    if n < 2:
        return np.zeros(n)
    return _ofi_kernel(
        bid_price.astype(np.float64), bid_size.astype(np.float64),
        ask_price.astype(np.float64), ask_size.astype(np.float64)
    )


# ═══════════════════════════════════════════════════════════════════════════════
#  MAIN PIPELINE
# ═══════════════════════════════════════════════════════════════════════════════
def process_event(ticker: str, date_str: str, event_row: pd.Series,
                  filtered_dir: str) -> dict | None:
    """
    Process a single event: normalize, regime-tag, extract all features.
    Returns a dict of features or None if the event can't be processed.
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

    # Filter to event date only — use date bounds instead of strftime (faster)
    day_start = pd.Timestamp(f"{date_str} 04:00:00")
    day_end   = pd.Timestamp(f"{date_str} 20:00:00")
    tdf = tdf[(tdf["dt_et"] >= day_start) & (tdf["dt_et"] <= day_end)].reset_index(drop=True)

    if len(tdf) < 10:
        return None

    # ─── NORMALIZATION ───────────────────────────────────────────────────
    # Find first RTH trade (09:30+ ET)
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

    # Outlier check
    if abs(log_phi) > NORM_LOG_THRESHOLD:
        return {"ticker": ticker, "date": date_str, "norm_factor": phi,
                "log_norm_factor": log_phi, "_status": "outlier",
                "_time": time.perf_counter() - t_start}

    # Apply normalization to all raw trade prices
    tdf["price_adj"] = tdf["price"] * phi

    # ─── REGIME TAGGING (vectorised) ────────────────────────────────────
    # Use integer hour:minute arithmetic instead of .apply() for ~20x speedup
    et_hour = tdf["dt_et"].dt.hour
    et_minute = tdf["dt_et"].dt.minute
    et_hm = et_hour * 100 + et_minute  # e.g. 930, 945, 1600

    tdf["regime"] = np.where(
        et_hm < 930, 1,          # PRE
        np.where(et_hm < 945, 2, # FLIP
                 3)               # STD
    )

    trades_pre  = tdf[tdf["regime"] == 1]
    trades_flip = tdf[tdf["regime"] == 2]
    trades_std  = tdf[tdf["regime"] == 3]

    # ─── FEATURE: Pre-Market Context ─────────────────────────────────────
    pm_high_price = float(trades_pre["price_adj"].max()) if len(trades_pre) > 0 else np.nan
    pm_trade_count = len(trades_pre)

    if pd.notna(pm_high_price) and pm_high_price > 0:
        pm_high_distance = (adjusted_open - pm_high_price) / pm_high_price
    else:
        pm_high_distance = np.nan

    # PM volume ratio: avg 1-min volume in FLIP / avg 1-min volume in PRE
    if len(trades_pre) > 0 and len(trades_flip) > 0:
        pre_duration = (trades_pre["dt_et"].iloc[-1] - trades_pre["dt_et"].iloc[0]).total_seconds() / 60
        flip_duration = 15.0  # 15 minutes
        pre_vol_per_min = trades_pre["size"].sum() / max(pre_duration, 1)
        flip_vol_per_min = trades_flip["size"].sum() / max(flip_duration, 1)
        pm_volume_ratio = flip_vol_per_min / max(pre_vol_per_min, 1)
    else:
        pm_volume_ratio = np.nan

    # ─── FEATURE: Hawkes Intensity (FLIP) ────────────────────────────────
    if len(trades_flip) >= 10:
        flip_ts = (trades_flip["dt_et"] - trades_flip["dt_et"].iloc[0]).dt.total_seconds().values
        hawkes_lam, hawkes_acc = hawkes_intensity_gpu_batched(flip_ts)
        hawkes_flip_mean = float(np.nanmean(hawkes_lam))
        hawkes_flip_max  = float(np.nanmax(hawkes_lam))
        hawkes_acc_mean  = float(np.nanmean(hawkes_acc))
        hawkes_acc_max   = float(np.nanmax(hawkes_acc))
    else:
        hawkes_lam = np.array([])
        hawkes_acc = np.array([])
        hawkes_flip_mean = hawkes_flip_max = hawkes_acc_mean = hawkes_acc_max = np.nan

    # ─── FEATURE: CVD & Convexity (FLIP) ─────────────────────────────────
    if len(trades_flip) >= 10:
        prices_flip = trades_flip["price_adj"].values
        volumes_flip = trades_flip["size"].values.astype(float)
        cvd_arr = compute_cvd(prices_flip, volumes_flip)
        cvd_final = float(cvd_arr[-1])

        flip_ts_sec = (trades_flip["dt_et"] - trades_flip["dt_et"].iloc[0]).dt.total_seconds().values
        convexity = compute_cvd_convexity(flip_ts_sec, cvd_arr)
        cvd_conv_mean = float(np.nanmean(convexity))
        cvd_conv_max  = float(np.nanmax(convexity))
        nonzero = convexity[convexity != 0]
        cvd_conv_sign_ratio = float((convexity > 0).sum() / max(len(convexity), 1))
    else:
        cvd_arr = np.array([])
        convexity = np.array([])
        cvd_final = cvd_conv_mean = cvd_conv_max = cvd_conv_sign_ratio = np.nan

    # ─── FEATURE: OFI (FLIP) ─────────────────────────────────────────────
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

                # Filter directly to FLIP window (skip full date filter)
                flip_start = pd.Timestamp(f"{date_str} 09:30:00")
                flip_end   = pd.Timestamp(f"{date_str} 09:45:00")
                qflip = qdf[(qdf["dt_et"] >= flip_start) & (qdf["dt_et"] < flip_end)]

                if len(qflip) >= 10:
                    # Apply normalization to quote prices too
                    bp = (qflip["bid_price"].values * phi).astype(np.float64)
                    bs = qflip["bid_size"].values.astype(np.float64)
                    ap = (qflip["ask_price"].values * phi).astype(np.float64)
                    az = qflip["ask_size"].values.astype(np.float64)

                    # Remove quotes with obviously bad data
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
        "hawkes_intensity_flip_mean": hawkes_flip_mean,
        "hawkes_intensity_flip_max": hawkes_flip_max,
        "hawkes_accel_flip_mean": hawkes_acc_mean,
        "hawkes_accel_flip_max": hawkes_acc_max,
        "cvd_flip_final": cvd_final,
        "cvd_convexity_flip_mean": cvd_conv_mean,
        "cvd_convexity_flip_max": cvd_conv_max,
        "cvd_convexity_flip_sign_ratio": cvd_conv_sign_ratio,
        "ofi_flip_mean": ofi_flip_mean,
        "ofi_flip_cumulative": ofi_flip_cum,
        "ofi_flip_max": ofi_flip_max,
        "ofi_flip_imbalance_ratio": ofi_flip_imb,
        "pm_high_distance": pm_high_distance,
        "pm_high_price": pm_high_price,
        "pm_volume_ratio": pm_volume_ratio,
        "pm_trade_count": pm_trade_count,
        "_status": "ok",
        "_time": elapsed,
        "_n_trades_flip": len(trades_flip),
        "_n_quotes_flip": len(ofi_arr) if isinstance(ofi_arr, np.ndarray) else 0,
        # Time-series stashed ONLY for top ~50 runners (by gap_pct desc order).
        # Caller controls which results keep these; we populate them here
        # and the main loop will strip them from lower-ranked events.
        "_trades_flip": trades_flip if len(trades_flip) > 0 else None,
        "_trades_pre": trades_pre if len(trades_pre) > 0 else None,
        "_trades_std": trades_std.head(1000) if len(trades_std) > 0 else None,
        "_hawkes_lam": hawkes_lam,
        "_hawkes_acc": hawkes_acc,
        "_cvd": cvd_arr,
        "_cvd_convexity": convexity,
    }


# ═══════════════════════════════════════════════════════════════════════════════
#  Anatomy Plot Generator
# ═══════════════════════════════════════════════════════════════════════════════
def generate_anatomy_plot(result: dict, save_path: Path):
    """Generate 3-panel anatomy plot for a single event."""
    ticker = result["ticker"]
    date_str = result["date"]
    trades_flip = result.get("_trades_flip")
    trades_pre = result.get("_trades_pre")
    hawkes_lam = result.get("_hawkes_lam", np.array([]))
    hawkes_acc = result.get("_hawkes_acc", np.array([]))
    cvd_arr = result.get("_cvd", np.array([]))
    convexity = result.get("_cvd_convexity", np.array([]))
    phi = result["norm_factor"]

    if trades_flip is None or len(trades_flip) < 10:
        return False

    fig = plt.figure(figsize=(16, 14))
    gs = GridSpec(3, 1, height_ratios=[2, 1, 1], hspace=0.25)

    # ─── Top Panel: Price (split-fixed) with PM High line ────────────────
    ax1 = fig.add_subplot(gs[0])
    flip_times = trades_flip["dt_et"].values
    flip_prices = trades_flip["price_adj"].values

    # Pre-market trades on the left
    if trades_pre is not None and len(trades_pre) > 0:
        pre_times = trades_pre["dt_et"].values
        pre_prices = (trades_pre["price"].values * phi)
        ax1.plot(pre_times, pre_prices, color="#90CAF9", linewidth=0.5,
                 alpha=0.6, label="Pre-Market")

    ax1.plot(flip_times, flip_prices, color="#1565C0", linewidth=1.2,
             alpha=0.9, label="FLIP (09:30–09:45)")

    # STD trades
    trades_std = result.get("_trades_std")
    if trades_std is not None and len(trades_std) > 0:
        std_times = trades_std["dt_et"].values
        std_prices = (trades_std["price"].values * phi)
        ax1.plot(std_times, std_prices, color="#2E7D32", linewidth=0.8,
                 alpha=0.7, label="STD (09:45+)")

    # PM High line
    pm_high = result.get("pm_high_price")
    if pd.notna(pm_high) and pm_high > 0:
        ax1.axhline(pm_high, color="#FF9800", linewidth=1.5, linestyle="--",
                     alpha=0.8, label=f"PM High: ${pm_high:.2f}")

    # 9:30 vertical line
    open_time = pd.Timestamp(f"{date_str} 09:30:00")
    ax1.axvline(open_time, color="red", linewidth=1, alpha=0.5, linestyle=":")
    ax1.annotate("9:30 OPEN", xy=(open_time, ax1.get_ylim()[1]),
                 fontsize=8, color="red", alpha=0.7)

    ax1.set_ylabel("Price (Split-Adjusted)", fontsize=11)
    ax1.set_title(f"Anatomy of Momentum — {ticker} ({date_str})\n"
                  f"Gap: {result['gap_pct']*100:.1f}%  |  "
                  f"φ={phi:.4f}  |  Rank: #{int(result['gap_rank'])}",
                  fontsize=14, fontweight="bold")
    ax1.legend(fontsize=9, loc="upper left")
    ax1.grid(alpha=0.2)
    ax1.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))

    # ─── Middle Panel: Hawkes Intensity + Acceleration ───────────────────
    ax2 = fig.add_subplot(gs[1], sharex=ax1)

    if len(hawkes_lam) > 0 and len(hawkes_lam) == len(trades_flip):
        ax2.plot(flip_times, hawkes_lam, color="#E91E63", linewidth=1.2,
                 alpha=0.9, label="λ(t) Intensity")

        ax2b = ax2.twinx()
        ax2b.fill_between(flip_times, hawkes_acc, 0, where=hawkes_acc > 0,
                          color="#4CAF50", alpha=0.3, label="Δλ > 0 (accelerating)")
        ax2b.fill_between(flip_times, hawkes_acc, 0, where=hawkes_acc < 0,
                          color="#F44336", alpha=0.3, label="Δλ < 0 (decelerating)")
        ax2b.set_ylabel("Δλ (Acceleration)", fontsize=10, color="#666")
        ax2b.tick_params(axis="y", labelcolor="#666")

        lines1, labels1 = ax2.get_legend_handles_labels()
        lines2, labels2 = ax2b.get_legend_handles_labels()
        ax2.legend(lines1 + lines2, labels1 + labels2, fontsize=8, loc="upper right")

    ax2.set_ylabel("Hawkes λ(t)", fontsize=11, color="#E91E63")
    ax2.tick_params(axis="y", labelcolor="#E91E63")
    ax2.set_title("Hawkes Self-Exciting Intensity", fontsize=11)
    ax2.grid(alpha=0.2)
    ax2.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))

    # ─── Bottom Panel: CVD + Convexity ───────────────────────────────────
    ax3 = fig.add_subplot(gs[2], sharex=ax1)

    if len(cvd_arr) > 0 and len(cvd_arr) == len(trades_flip):
        ax3.plot(flip_times, cvd_arr, color="#1565C0", linewidth=1.5,
                 alpha=0.9, label="CVD")
        ax3.fill_between(flip_times, cvd_arr, 0, alpha=0.1, color="#1565C0")

        if len(convexity) > 0:
            ax3b = ax3.twinx()
            ax3b.plot(flip_times, convexity, color="#FF5722", linewidth=0.8,
                      alpha=0.7, label="CVD'' (Convexity)")
            ax3b.axhline(0, color="#FF5722", linewidth=0.5, alpha=0.3)
            ax3b.set_ylabel("CVD'' (Convexity)", fontsize=10, color="#FF5722")
            ax3b.tick_params(axis="y", labelcolor="#FF5722")

            lines1, labels1 = ax3.get_legend_handles_labels()
            lines2, labels2 = ax3b.get_legend_handles_labels()
            ax3.legend(lines1 + lines2, labels1 + labels2, fontsize=8, loc="upper left")

    ax3.set_ylabel("CVD (Shares)", fontsize=11, color="#1565C0")
    ax3.tick_params(axis="y", labelcolor="#1565C0")
    ax3.set_title("Cumulative Volume Delta & Convexity", fontsize=11)
    ax3.set_xlabel("Time (ET)", fontsize=11)
    ax3.grid(alpha=0.2)
    ax3.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))

    fig.savefig(save_path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return True


# ═══════════════════════════════════════════════════════════════════════════════
#  Intensity Heatmap Generator
# ═══════════════════════════════════════════════════════════════════════════════
def generate_intensity_heatmap(all_hawkes_by_event: list[dict], save_path: Path):
    """
    Generate a time-of-day intensity heatmap across all processed events.
    Bins: 1-minute resolution from 09:25 to 10:00 ET.
    Rows: events ranked by gap_pct.
    """
    n_bins = 35  # 09:25 to 10:00 in 1-min bins
    bin_labels = [f"09:{25+i:02d}" if 25+i < 60 else f"10:{25+i-60:02d}" for i in range(n_bins)]

    # Collect heatmap data
    rows = []
    labels = []
    for evt in all_hawkes_by_event:
        if evt.get("_trades_flip") is None:
            continue
        trades = evt["_trades_flip"]
        lam = evt.get("_hawkes_lam", np.array([]))
        if len(lam) == 0 or len(lam) != len(trades):
            continue

        # Bin by minute
        minutes = trades["dt_et"].dt.hour * 60 + trades["dt_et"].dt.minute
        bin_start = 9 * 60 + 25  # 09:25

        intensity_row = np.full(n_bins, np.nan)
        for b in range(n_bins):
            target_min = bin_start + b
            mask = minutes == target_min
            if mask.sum() > 0:
                intensity_row[b] = np.mean(lam[mask.values])

        rows.append(intensity_row)
        labels.append(f"{evt['ticker']} ({evt['gap_pct']*100:.0f}%)")

    if not rows:
        return

    heatmap = np.array(rows)

    # Normalize per row for visibility
    for i in range(len(heatmap)):
        row_max = np.nanmax(heatmap[i])
        if row_max > 0:
            heatmap[i] /= row_max

    fig, ax = plt.subplots(figsize=(16, max(4, len(rows) * 0.5)))
    im = ax.imshow(heatmap, aspect="auto", cmap="hot_r", interpolation="nearest")

    ax.set_xticks(range(0, n_bins, 5))
    ax.set_xticklabels([bin_labels[i] for i in range(0, n_bins, 5)], fontsize=9)
    ax.set_yticks(range(len(labels)))
    ax.set_yticklabels(labels, fontsize=8)

    # 9:30 vertical marker
    ax.axvline(5, color="lime", linewidth=2, linestyle="--", alpha=0.8)
    ax.annotate("9:30 OPEN", xy=(5, -0.5), fontsize=8, color="lime", fontweight="bold")

    # 9:45 marker
    ax.axvline(20, color="cyan", linewidth=1.5, linestyle="--", alpha=0.6)
    ax.annotate("9:45 STD", xy=(20, -0.5), fontsize=8, color="cyan")

    ax.set_title("Hawkes Intensity Heatmap — When Do Clusters Form?",
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
    log(f"Phase 2 Signal Forge — GPU={DEVICE}")
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

    log(f"Processing events …")
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
                # Preserve the first 50 results (top runners by gap_pct
                # since scanner is sorted descending) for anatomy plots.
                if len(results) > 50:
                    strip_idx = len(results) - 51
                    if strip_idx >= 50:   # never strip indices 0-49
                        old = results[strip_idx]
                        for key in ["_trades_flip", "_trades_pre", "_trades_std",
                                    "_hawkes_lam", "_hawkes_acc", "_cvd", "_cvd_convexity"]:
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

    # ─── Generate anatomy plots for top 10 ───────────────────────────────
    log(f"Generating anatomy plots for top 10 super-runners …")
    anatomy_count = 0
    anatomy_events_for_heatmap = []

    for r in results[:50]:  # Check up to 50 to find 10 plottable
        if anatomy_count >= 10:
            break
        save_path = PLOTS / f"anatomy_{r['ticker']}_{r['date']}.png"
        if generate_anatomy_plot(r, save_path):
            anatomy_count += 1
            anatomy_events_for_heatmap.append(r)
            log(f"  Saved anatomy_{r['ticker']}_{r['date']}.png")

    log(f"  {anatomy_count} anatomy plots generated")

    # ─── Generate intensity heatmap ──────────────────────────────────────
    log(f"Generating intensity heatmap …")
    # Include more events for the heatmap (top 30 with Hawkes data)
    heatmap_events = [r for r in results[:100]
                      if r.get("_hawkes_lam") is not None and len(r.get("_hawkes_lam", [])) > 0][:30]
    generate_intensity_heatmap(heatmap_events, PLOTS / "intensity_heatmap.png")
    log(f"  Heatmap generated with {len(heatmap_events)} events")

    # ─── Assemble feature matrix ─────────────────────────────────────────
    log(f"Assembling feature_matrix_v1.parquet …")

    feature_cols = [
        "ticker", "date", "gap_pct", "gap_rank",
        "norm_factor", "log_norm_factor",
        "hawkes_intensity_flip_mean", "hawkes_intensity_flip_max",
        "hawkes_accel_flip_mean", "hawkes_accel_flip_max",
        "cvd_flip_final", "cvd_convexity_flip_mean", "cvd_convexity_flip_max",
        "cvd_convexity_flip_sign_ratio",
        "ofi_flip_mean", "ofi_flip_cumulative", "ofi_flip_max", "ofi_flip_imbalance_ratio",
        "pm_high_distance", "pm_high_price", "pm_volume_ratio", "pm_trade_count",
    ]

    fm_rows = []
    for r in results:
        fm_rows.append({k: r.get(k) for k in feature_cols})

    fm = pd.DataFrame(fm_rows)
    fm.to_parquet(OUT / "feature_matrix_v1.parquet", index=False)
    log(f"  Saved feature_matrix_v1.parquet: {len(fm)} rows × {len(fm.columns)} cols")

    # ─── Feature statistics ──────────────────────────────────────────────
    log(f"\n  === Feature Statistics ===")
    for col in feature_cols[4:]:  # skip ticker, date, gap_pct, gap_rank
        vals = fm[col].dropna()
        if len(vals) > 0:
            log(f"    {col:40s}  n={len(vals):5d}  mean={vals.mean():12.4f}  "
                f"median={vals.median():12.4f}  std={vals.std():12.4f}")

    # ─── Forge Audit Log ─────────────────────────────────────────────────
    total_time = time.perf_counter() - T0
    log(f"\nWriting Forge_Audit_Log.md …")

    proc_times = [r.get("_time", 0) for r in results]
    gpu_mem = torch.cuda.max_memory_allocated() / (1024**2) if torch.cuda.is_available() else 0

    audit_log = f"""# Phase 2 Signal Forge — Audit Log
**Generated:** {dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Total execution time:** {total_time:.1f}s
**GPU Device:** {DEVICE} ({torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'N/A'})
**Peak GPU Memory:** {gpu_mem:.1f} MB

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
| Anatomy plots | {anatomy_count} |

## Processing Time
| Stat | Value |
|---|---|
| Mean per event | {np.mean(proc_times):.3f}s |
| Median per event | {np.median(proc_times):.3f}s |
| Max per event | {np.max(proc_times):.3f}s |
| Total GPU | {total_time:.1f}s |

## Hawkes Parameters
| Param | Value |
|---|---|
| α (excitation) | {HAWKES_ALPHA} |
| β (decay) | {HAWKES_BETA} |
| μ (baseline) | Estimated per-event |

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

    (OUT / "Forge_Audit_Log.md").write_text(audit_log, encoding="utf-8")
    log(f"Forge_Audit_Log.md written")
    log(f"PHASE 2 BUILD COMPLETE in {total_time:.1f}s")

    # Cleanup temp files
    for f in ["_check_data.py", "_find_top_runners.py", "_inspect_schemas.py"]:
        p = ROOT / f
        if p.exists():
            p.unlink()
