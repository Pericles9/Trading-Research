"""
AlphaMomentum Phase 3 — The Alpha Hunter
==========================================
ML Regime Classification: XGBoost + UMAP + SHAP

Pipeline:
  1. Data Fusion: Merge Phase 1 (scanner context) + Phase 2 (halt-stitched signals)
  2. Label Engineering: Compute forward targets from raw tick data
     - Y_Contagion: Integrated Hawkes intensity AUC (09:45–10:00)
     - Y_Efficiency: MFE/MAE ratio (09:45–09:55)
  3. XGBoost Regime Model with inverse-rank sample weights
  4. Visualization: UMAP cluster map, SHAP beeswarm, calibration curve

Requires: xgboost, shap, umap-learn, scikit-learn, pandas, numpy, matplotlib, numba
"""

import os, sys, time, warnings, json
import datetime as dt
from pathlib import Path

import numpy as np
import pandas as pd
from numba import njit

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec
import matplotlib.dates as mdates

warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=DeprecationWarning)

# ─── Configuration ───────────────────────────────────────────────────────────
ROOT   = Path(r"D:\Mom_db")
DATA   = ROOT / "data"
PHASE1 = ROOT / "research" / "phase_1_context"
PHASE2 = ROOT / "research" / "phase_2_signal_forge"
OUT    = ROOT / "research" / "phase_3_alpha_hunter"
PLOTS  = OUT / "plots"
PLOTS.mkdir(parents=True, exist_ok=True)

# Hawkes parameters (must match Phase 2)
HAWKES_ALPHA = 0.8
HAWKES_BETA  = 1.0
HAWKES_FREEZE_SEC = 5.0

# Forward target windows
FORWARD_HAWKES_MINUTES = 15   # Y_Contagion: AUC of λ for 15 min post-FLIP
FORWARD_MFE_MINUTES    = 10   # Y_Efficiency: MFE/MAE for 10 min post-FLIP

DEVICE = "cpu"  # XGBoost on CPU is fine

# ─── Logging ─────────────────────────────────────────────────────────────────
LOG_LINES: list[str] = []
T0 = time.perf_counter()

def log(msg: str):
    elapsed = time.perf_counter() - T0
    line = f"[{elapsed:8.1f}s] {msg}"
    LOG_LINES.append(line)
    print(line)


# ═══════════════════════════════════════════════════════════════════════════════
#  Utility: ET Timestamp Conversion (reused from Phase 2)
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
#  Halt-Stitched Hawkes Kernel (reused from Phase 2)
# ═══════════════════════════════════════════════════════════════════════════════
@njit(cache=True)
def _hawkes_scan_halt_aware(dt_arr, alpha, beta, mu, halt_threshold):
    n = len(dt_arr) + 1
    intensity = np.empty(n, dtype=np.float64)
    accel     = np.empty(n, dtype=np.float64)
    S = 0.0
    intensity[0] = mu
    accel[0] = 0.0
    for i in range(1, n):
        d = dt_arr[i - 1]
        if d > halt_threshold:
            S = S + 1.0
        else:
            S = np.exp(-beta * d) * S + 1.0
        lam = mu + alpha * S
        intensity[i] = lam
        accel[i] = lam - intensity[i - 1]
    return intensity, accel


def hawkes_intensity(timestamps_sec, alpha=HAWKES_ALPHA, beta=HAWKES_BETA,
                     freeze_thresh=HAWKES_FREEZE_SEC):
    """Compute halt-stitched Hawkes intensity. Returns (intensity, accel)."""
    n = len(timestamps_sec)
    if n < 2:
        return np.zeros(n), np.zeros(n)
    dt_arr = np.diff(timestamps_sec).astype(np.float64)
    dt_arr = np.maximum(dt_arr, 1e-9)
    active_mask = dt_arr <= freeze_thresh
    active_dur = dt_arr[active_mask].sum() if active_mask.any() else 1e-6
    active_n = active_mask.sum() + 1
    mu = active_n / max(active_dur, 1e-6)
    intensity, accel = _hawkes_scan_halt_aware(dt_arr, alpha, beta, mu, freeze_thresh)
    return intensity, accel


# ═══════════════════════════════════════════════════════════════════════════════
#  Forward Target Computation
# ═══════════════════════════════════════════════════════════════════════════════
def compute_forward_targets(ticker: str, date_str: str, filtered_dir: str,
                            phi: float) -> dict:
    """
    Compute forward-looking targets from raw tick data:
      Y_Contagion: Integrated Hawkes AUC for 15 min post-FLIP (09:45–10:00)
      Y_Efficiency: MFE/MAE ratio for 10 min post-FLIP (09:45–09:55)
      return_15m: Raw 15-minute return from FLIP end
    """
    trades_file = DATA / "filtered" / filtered_dir / "trades.parquet"
    if not trades_file.exists():
        return {}

    try:
        tdf = pd.read_parquet(trades_file, columns=["sip_timestamp", "price", "size"])
    except Exception:
        return {}

    if len(tdf) == 0:
        return {}

    et_offset = utc_to_et_offset_hours(date_str)
    tdf = tdf.sort_values("sip_timestamp").reset_index(drop=True)
    tdf["dt_utc"] = pd.to_datetime(tdf["sip_timestamp"], unit="ns")
    tdf["dt_et"] = tdf["dt_utc"] - pd.Timedelta(hours=et_offset)

    # Filter to post-FLIP window (09:45–10:15 to cover both targets)
    flip_end   = pd.Timestamp(f"{date_str} 09:45:00")
    target_end = pd.Timestamp(f"{date_str} 10:15:00")  # max of 15m + 10m windows
    post = tdf[(tdf["dt_et"] >= flip_end) & (tdf["dt_et"] <= target_end)].reset_index(drop=True)

    if len(post) < 10:
        return {}

    post["price_adj"] = post["price"] * phi

    # Reference price: first trade at/after 09:45
    ref_price = post["price_adj"].iloc[0]
    if ref_price <= 0:
        return {}

    result = {}

    # ── Y_Contagion: Integrated Hawkes AUC (09:45–10:00) ────────────────
    hawkes_end = pd.Timestamp(f"{date_str} 10:00:00")
    hawkes_window = post[post["dt_et"] <= hawkes_end]

    if len(hawkes_window) >= 10:
        ts_sec = (hawkes_window["dt_et"] - hawkes_window["dt_et"].iloc[0]).dt.total_seconds().values
        lam, _ = hawkes_intensity(ts_sec)
        # Trapezoidal integration: AUC = Σ (λ_i + λ_{i+1})/2 * Δt_i
        if len(lam) >= 2:
            dt_vals = np.diff(ts_sec)
            dt_vals = np.minimum(dt_vals, HAWKES_FREEZE_SEC)  # cap at freeze thresh for AUC
            auc = np.sum(0.5 * (lam[:-1] + lam[1:]) * dt_vals)
            result["y_contagion"] = float(auc)
            result["hawkes_forward_mean"] = float(np.mean(lam))
            result["hawkes_forward_max"] = float(np.max(lam))

    # ── Y_Efficiency: MFE / MAE ratio (09:45–09:55) ─────────────────────
    mfe_end = pd.Timestamp(f"{date_str} 09:55:00")
    mfe_window = post[post["dt_et"] <= mfe_end]

    if len(mfe_window) >= 5:
        prices = mfe_window["price_adj"].values
        returns = (prices - ref_price) / ref_price

        mfe = float(np.max(returns))   # max favorable excursion
        mae = float(np.min(returns))   # max adverse excursion (negative)

        result["mfe_10m"] = mfe
        result["mae_10m"] = mae

        # MFE/MAE ratio: positive = clean trend, negative = chop
        # Guard against division by zero
        if abs(mae) > 1e-6:
            result["y_efficiency"] = abs(mfe / mae)
        else:
            result["y_efficiency"] = 100.0 if mfe > 0 else 0.0  # perfect run-up or flat

    # ── 15-minute return ─────────────────────────────────────────────────
    ret_end = pd.Timestamp(f"{date_str} 10:00:00")
    ret_window = post[post["dt_et"] <= ret_end]
    if len(ret_window) >= 5:
        last_price = ret_window["price_adj"].iloc[-1]
        result["return_15m"] = float((last_price - ref_price) / ref_price)

    return result


# ═══════════════════════════════════════════════════════════════════════════════
#  Data Fusion + Feature Engineering
# ═══════════════════════════════════════════════════════════════════════════════
def build_fused_dataset():
    """Merge Phase 1 + Phase 2, compute forward targets, build ML-ready dataset."""
    log("Loading Phase 1 (scanner_context) …")
    p1 = pd.read_parquet(PHASE1 / "scanner_context.parquet")
    log(f"  {len(p1):,} events")

    log("Loading Phase 2 (feature_matrix_v2_ext) …")
    p2 = pd.read_parquet(PHASE2 / "feature_matrix_v2_ext.parquet")
    log(f"  {len(p2):,} events, {len(p2.columns)} features")

    # ── Merge on [ticker, date] ──────────────────────────────────────────
    # Phase 2 already has gap_pct and gap_rank; take Phase 1's extra columns
    p1_extra = p1[["ticker", "date", "prev_close", "open", "high", "close",
                    "volume", "momentum_at_high", "vol_5min",
                    "volume_intensity_rank", "rvol"]].copy()

    fused = p2.merge(p1_extra, on=["ticker", "date"], how="left")
    log(f"  Fused: {len(fused):,} rows × {len(fused.columns)} cols")

    # ── Build filtered directory lookup ──────────────────────────────────
    filt_dirs = set(os.listdir(DATA / "filtered"))

    def find_filtered_dir(ticker, date):
        prefix = f"{ticker}_{date}_"
        matches = [d for d in filt_dirs if d.startswith(prefix)]
        return matches[0] if matches else None

    # ── Compute forward targets ──────────────────────────────────────────
    log("Computing forward targets (Y_Contagion, Y_Efficiency) …")
    forward_rows = []
    computed = 0
    skipped = 0

    for idx, row in fused.iterrows():
        ticker = row["ticker"]
        date_str = row["date"]
        phi = row["norm_factor"]

        if pd.isna(phi) or phi <= 0:
            skipped += 1
            forward_rows.append({})
            continue

        fdir = find_filtered_dir(ticker, date_str)
        if fdir is None:
            skipped += 1
            forward_rows.append({})
            continue

        targets = compute_forward_targets(ticker, date_str, fdir, phi)
        forward_rows.append(targets)
        computed += 1

        if (computed + skipped) % 500 == 0:
            rate = (computed + skipped) / max(time.perf_counter() - T0, 0.1)
            eta = (len(fused) - computed - skipped) / max(rate, 0.01)
            log(f"    {computed + skipped}/{len(fused)} "
                f"(computed={computed}, skip={skipped}) ETA={eta:.0f}s")

    log(f"  Forward targets: {computed} computed, {skipped} skipped")

    # Merge forward targets into fused dataset
    target_df = pd.DataFrame(forward_rows)
    for col in ["y_contagion", "y_efficiency", "return_15m", "mfe_10m", "mae_10m",
                "hawkes_forward_mean", "hawkes_forward_max"]:
        if col in target_df.columns:
            fused[col] = target_df[col].values
        else:
            fused[col] = np.nan

    # ── Derived features ─────────────────────────────────────────────────
    # Volume proxy for sample weights (rvol has only 101/4549 coverage)
    # Use volume_intensity_rank as proxy; fill with 0.5 (median rank) if missing
    fused["vol_proxy"] = fused["volume_intensity_rank"].fillna(0.5)

    # Log volume for weight computation
    fused["log_volume"] = np.log1p(fused["volume"].fillna(0))

    log(f"  Final fused dataset: {len(fused)} rows × {len(fused.columns)} cols")

    # Save
    fused.to_parquet(OUT / "fused_dataset.parquet", index=False)
    log(f"  Saved fused_dataset.parquet")

    return fused


# ═══════════════════════════════════════════════════════════════════════════════
#  Sample Weight Computation
# ═══════════════════════════════════════════════════════════════════════════════
def compute_sample_weights(df: pd.DataFrame) -> np.ndarray:
    """
    Weight = 1 / rank^2  ×  log(Relative_Volume)

    - Mistakes on Rank #1 stocks penalized 2500× more than Rank #50
    - Volume proxy boosts weight for high-activity events
    - Fallback: use volume_intensity_rank or log(volume) where rvol unavailable
    """
    rank = df["gap_rank"].values.astype(float)
    rank = np.maximum(rank, 1.0)  # floor at 1

    # Volume component: prefer rvol, fallback to volume_intensity_rank
    vol_component = df["rvol"].values.copy()
    # Fill NaN rvol with volume_intensity_rank mapped to pseudo-rvol
    nan_mask = np.isnan(vol_component)
    if nan_mask.any():
        # Use log(volume) as fallback, scaled to rvol-like range
        log_vol = np.log1p(df["volume"].fillna(1).values)
        # Normalize to [1, 10] range
        lv_min, lv_max = log_vol[nan_mask].min(), log_vol[nan_mask].max()
        if lv_max > lv_min:
            scaled = 1.0 + 9.0 * (log_vol - lv_min) / (lv_max - lv_min)
        else:
            scaled = np.full_like(log_vol, 5.0)
        vol_component[nan_mask] = scaled[nan_mask]

    vol_component = np.maximum(vol_component, 1.01)  # floor for log
    log_vol = np.log(vol_component)

    weights = (1.0 / rank**2) * log_vol
    weights = np.maximum(weights, 1e-6)  # floor to avoid zeros

    return weights


# ═══════════════════════════════════════════════════════════════════════════════
#  XGBoost Regime Model
# ═══════════════════════════════════════════════════════════════════════════════
def train_xgboost(df: pd.DataFrame):
    """
    Train XGBoost to predict Y_Contagion (forward Hawkes AUC).
    - Inverse-rank sample weighting
    - Monotonic constraint on gap_rank (lower rank → better)
    """
    import xgboost as xgb
    from sklearn.model_selection import TimeSeriesSplit
    from sklearn.metrics import mean_squared_error, r2_score

    log("Training XGBoost Regime Model …")

    # ── Feature selection ────────────────────────────────────────────────
    feature_cols = [
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
        "ofi_flip_mean", "ofi_flip_cumulative", "ofi_flip_max",
        "ofi_flip_imbalance_ratio",
        # Pre-Market Context
        "pm_high_distance", "pm_high_price", "pm_volume_ratio", "pm_trade_count",
        # Halt Context
        "is_post_halt", "n_halts", "max_halt_duration_sec", "total_halt_duration_sec",
        # Scanner Context (Phase 1)
        "gap_pct", "gap_rank", "momentum_at_high",
        "volume", "vol_5min", "volume_intensity_rank",
    ]

    target_col = "y_contagion"

    # ── Filter to valid rows ─────────────────────────────────────────────
    valid = df[target_col].notna()
    log(f"  Valid target rows: {valid.sum()}/{len(df)}")

    df_valid = df[valid].copy().reset_index(drop=True)

    # Fill feature NaNs with -1 (XGBoost handles missing values natively)
    X = df_valid[feature_cols].copy()
    y = df_valid[target_col].values

    # ── Sample weights ───────────────────────────────────────────────────
    weights = compute_sample_weights(df_valid)
    log(f"  Sample weights: min={weights.min():.6f}, max={weights.max():.4f}, "
        f"mean={weights.mean():.4f}")

    # ── Monotonic constraints ────────────────────────────────────────────
    # gap_rank: LOWER rank = BETTER → monotone_constraints = -1
    # (XGBoost: -1 = decreasing, 0 = none, 1 = increasing)
    mono_constraints = [0] * len(feature_cols)
    gap_rank_idx = feature_cols.index("gap_rank")
    mono_constraints[gap_rank_idx] = -1  # lower rank → higher prediction

    log(f"  Monotonic constraint on gap_rank (idx={gap_rank_idx}): -1 (decreasing)")

    # ── Time-based train/test split ──────────────────────────────────────
    # Sort by date for temporal integrity
    df_valid = df_valid.sort_values("date").reset_index(drop=True)
    X = df_valid[feature_cols].copy()
    y = df_valid[target_col].values
    weights = compute_sample_weights(df_valid)

    split_idx = int(len(df_valid) * 0.8)
    X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
    y_train, y_test = y[:split_idx], y[split_idx:]
    w_train, w_test = weights[:split_idx], weights[split_idx:]

    log(f"  Train: {len(X_train)}, Test: {len(X_test)} (80/20 temporal split)")
    log(f"  Train dates: {df_valid['date'].iloc[0]} → {df_valid['date'].iloc[split_idx-1]}")
    log(f"  Test dates:  {df_valid['date'].iloc[split_idx]} → {df_valid['date'].iloc[-1]}")

    # ── XGBoost training ─────────────────────────────────────────────────
    dtrain = xgb.DMatrix(X_train, label=y_train, weight=w_train,
                         feature_names=feature_cols)
    dtest  = xgb.DMatrix(X_test, label=y_test, weight=w_test,
                         feature_names=feature_cols)

    params = {
        "objective": "reg:squarederror",
        "eval_metric": ["rmse", "mae"],
        "max_depth": 6,
        "learning_rate": 0.05,
        "subsample": 0.8,
        "colsample_bytree": 0.8,
        "min_child_weight": 10,
        "gamma": 1.0,
        "reg_alpha": 0.1,
        "reg_lambda": 1.0,
        "monotone_constraints": tuple(mono_constraints),
        "tree_method": "hist",
        "seed": 42,
    }

    evals_result = {}
    model = xgb.train(
        params, dtrain,
        num_boost_round=500,
        evals=[(dtrain, "train"), (dtest, "test")],
        evals_result=evals_result,
        early_stopping_rounds=50,
        verbose_eval=False,
    )

    best_iter = model.best_iteration
    train_rmse = evals_result["train"]["rmse"][best_iter]
    test_rmse = evals_result["test"]["rmse"][best_iter]

    log(f"  Best iteration: {best_iter}")
    log(f"  Train RMSE: {train_rmse:.2f}")
    log(f"  Test RMSE:  {test_rmse:.2f}")

    # ── Predictions ──────────────────────────────────────────────────────
    y_pred_train = model.predict(dtrain)
    y_pred_test  = model.predict(dtest)

    r2_train = r2_score(y_train, y_pred_train)
    r2_test  = r2_score(y_test, y_pred_test)
    log(f"  Train R²: {r2_train:.4f}")
    log(f"  Test R²:  {r2_test:.4f}")

    # ── Feature importance ───────────────────────────────────────────────
    importance = model.get_score(importance_type="gain")
    imp_sorted = sorted(importance.items(), key=lambda x: x[1], reverse=True)
    log(f"\n  === Feature Importance (Gain) ===")
    for fname, gain in imp_sorted[:10]:
        log(f"    {fname:42s}  gain={gain:.2f}")

    # ── Save model ───────────────────────────────────────────────────────
    model.save_model(str(OUT / "xgb_regime_model.json"))
    log(f"  Saved xgb_regime_model.json")

    return {
        "model": model,
        "feature_cols": feature_cols,
        "X_train": X_train, "X_test": X_test,
        "y_train": y_train, "y_test": y_test,
        "y_pred_train": y_pred_train, "y_pred_test": y_pred_test,
        "w_train": w_train, "w_test": w_test,
        "df_valid": df_valid,
        "importance": imp_sorted,
        "best_iter": best_iter,
        "train_rmse": train_rmse, "test_rmse": test_rmse,
        "r2_train": r2_train, "r2_test": r2_test,
        "evals_result": evals_result,
        "params": params,
    }


# ═══════════════════════════════════════════════════════════════════════════════
#  Visualization: UMAP "Regime Map"
# ═══════════════════════════════════════════════════════════════════════════════
def generate_umap_regime_map(model_output: dict, fused: pd.DataFrame):
    """
    UMAP projection of the feature matrix, colored by actual 15m return.
    Goal: see if "Super-Runners" form a distinct island.
    """
    import umap

    log("Generating UMAP Regime Map …")

    feature_cols = model_output["feature_cols"]
    df = model_output["df_valid"].copy()

    # Need return_15m for coloring
    valid_mask = df["return_15m"].notna()
    df_plot = df[valid_mask].reset_index(drop=True)

    if len(df_plot) < 50:
        log("  Insufficient data for UMAP")
        return

    X = df_plot[feature_cols].fillna(-1).values
    returns = df_plot["return_15m"].values

    # Run UMAP
    reducer = umap.UMAP(
        n_components=2,
        n_neighbors=30,
        min_dist=0.3,
        metric="euclidean",
        random_state=42,
    )
    embedding = reducer.fit_transform(X)

    log(f"  UMAP embedding: {embedding.shape}")

    # ── Plot ─────────────────────────────────────────────────────────────
    fig, axes = plt.subplots(1, 2, figsize=(24, 10))

    # Panel 1: Colored by 15m Return
    ax1 = axes[0]
    # Clip returns for better color mapping
    ret_clipped = np.clip(returns * 100, -20, 50)  # percent

    scatter1 = ax1.scatter(
        embedding[:, 0], embedding[:, 1],
        c=ret_clipped, cmap="RdYlGn", s=8, alpha=0.6,
        vmin=-20, vmax=50
    )
    plt.colorbar(scatter1, ax=ax1, label="15-min Return (%)", shrink=0.8)

    # Highlight super-runners (>20% return)
    super_mask = returns > 0.20
    if super_mask.any():
        ax1.scatter(
            embedding[super_mask, 0], embedding[super_mask, 1],
            facecolors="none", edgecolors="red", s=80, linewidths=1.5,
            label=f"Super-Runners (>20%): {super_mask.sum()}"
        )
        ax1.legend(fontsize=10, loc="upper right")

    ax1.set_title("UMAP Regime Map — Colored by 15-min Return",
                  fontsize=14, fontweight="bold")
    ax1.set_xlabel("UMAP-1", fontsize=11)
    ax1.set_ylabel("UMAP-2", fontsize=11)
    ax1.grid(alpha=0.15)

    # Panel 2: Colored by Y_Contagion (forward Hawkes AUC)
    ax2 = axes[1]
    contagion = df_plot["y_contagion"].values
    contagion_clipped = np.clip(contagion, 0, np.nanpercentile(contagion, 95))

    scatter2 = ax2.scatter(
        embedding[:, 0], embedding[:, 1],
        c=contagion_clipped, cmap="hot_r", s=8, alpha=0.6,
    )
    plt.colorbar(scatter2, ax=ax2, label="Y_Contagion (Hawkes AUC)", shrink=0.8)

    # Highlight halted events
    halted = df_plot["n_halts"].values > 0
    if halted.any():
        ax2.scatter(
            embedding[halted, 0], embedding[halted, 1],
            facecolors="none", edgecolors="cyan", s=40, linewidths=0.8,
            alpha=0.5, label=f"Halted Events: {halted.sum()}"
        )
        ax2.legend(fontsize=10, loc="upper right")

    ax2.set_title("UMAP Regime Map — Colored by Forward Hawkes AUC",
                  fontsize=14, fontweight="bold")
    ax2.set_xlabel("UMAP-1", fontsize=11)
    ax2.set_ylabel("UMAP-2", fontsize=11)
    ax2.grid(alpha=0.15)

    fig.tight_layout()
    fig.savefig(PLOTS / "umap_regime_map.png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    log(f"  Saved umap_regime_map.png ({len(df_plot)} points)")

    return embedding


# ═══════════════════════════════════════════════════════════════════════════════
#  Visualization: SHAP Beeswarm
# ═══════════════════════════════════════════════════════════════════════════════
def generate_shap_analysis(model_output: dict):
    """Generate SHAP beeswarm plot to identify Golden Features."""
    import shap

    log("Generating SHAP analysis …")

    model = model_output["model"]
    X_test = model_output["X_test"]
    feature_cols = model_output["feature_cols"]

    # Create SHAP explainer
    explainer = shap.TreeExplainer(model)
    shap_values = explainer.shap_values(X_test)

    log(f"  SHAP values computed: {shap_values.shape}")

    # ── Beeswarm plot ────────────────────────────────────────────────────
    fig, ax = plt.subplots(figsize=(14, 12))
    shap.summary_plot(shap_values, X_test, feature_names=feature_cols,
                      show=False, max_display=20, plot_size=None)
    plt.title("SHAP Feature Importance — What Drives Contagion?",
              fontsize=14, fontweight="bold")
    plt.tight_layout()
    plt.savefig(PLOTS / "shap_beeswarm.png", dpi=150, bbox_inches="tight")
    plt.close("all")
    log(f"  Saved shap_beeswarm.png")

    # ── SHAP bar plot ────────────────────────────────────────────────────
    fig, ax = plt.subplots(figsize=(12, 10))
    shap.summary_plot(shap_values, X_test, feature_names=feature_cols,
                      plot_type="bar", show=False, max_display=15)
    plt.title("SHAP Mean |SHAP Value| — Golden Feature Ranking",
              fontsize=14, fontweight="bold")
    plt.tight_layout()
    plt.savefig(PLOTS / "shap_bar.png", dpi=150, bbox_inches="tight")
    plt.close("all")
    log(f"  Saved shap_bar.png")

    # ── Compute mean absolute SHAP per feature ──────────────────────────
    mean_abs_shap = np.abs(shap_values).mean(axis=0)
    shap_ranking = sorted(zip(feature_cols, mean_abs_shap),
                          key=lambda x: x[1], reverse=True)

    log(f"\n  === SHAP Golden Features ===")
    for i, (fname, val) in enumerate(shap_ranking[:10]):
        log(f"    #{i+1}: {fname:42s}  mean|SHAP|={val:.4f}")

    return shap_ranking, shap_values


# ═══════════════════════════════════════════════════════════════════════════════
#  Visualization: Probability Calibration Curve
# ═══════════════════════════════════════════════════════════════════════════════
def generate_calibration_plot(model_output: dict):
    """
    Plot Predicted Contagion vs. Actual Contagion.
    Binned calibration: sort by predicted, bin into deciles, compare means.
    """
    log("Generating calibration plot …")

    y_test = model_output["y_test"]
    y_pred = model_output["y_pred_test"]

    # Sort by predicted
    sort_idx = np.argsort(y_pred)
    y_pred_sorted = y_pred[sort_idx]
    y_test_sorted = y_test[sort_idx]

    # Bin into deciles
    n_bins = 10
    bin_size = len(y_test_sorted) // n_bins
    bin_pred_means = []
    bin_actual_means = []
    bin_actual_stds = []

    for i in range(n_bins):
        start = i * bin_size
        end = start + bin_size if i < n_bins - 1 else len(y_test_sorted)
        bin_pred_means.append(np.mean(y_pred_sorted[start:end]))
        bin_actual_means.append(np.mean(y_test_sorted[start:end]))
        bin_actual_stds.append(np.std(y_test_sorted[start:end]))

    bin_pred_means = np.array(bin_pred_means)
    bin_actual_means = np.array(bin_actual_means)
    bin_actual_stds = np.array(bin_actual_stds)

    fig, axes = plt.subplots(1, 2, figsize=(20, 8))

    # ── Panel 1: Calibration curve ───────────────────────────────────────
    ax1 = axes[0]
    ax1.errorbar(bin_pred_means, bin_actual_means, yerr=bin_actual_stds,
                 fmt="o-", color="#1565C0", linewidth=2, markersize=8,
                 capsize=5, label="Model Calibration")

    # Perfect calibration line
    min_val = min(bin_pred_means.min(), bin_actual_means.min())
    max_val = max(bin_pred_means.max(), bin_actual_means.max())
    ax1.plot([min_val, max_val], [min_val, max_val], "k--", alpha=0.5,
             linewidth=1.5, label="Perfect Calibration")

    ax1.set_xlabel("Predicted Contagion (Hawkes AUC)", fontsize=12)
    ax1.set_ylabel("Actual Contagion (Hawkes AUC)", fontsize=12)
    ax1.set_title("Probability Calibration — Predicted vs. Actual Contagion",
                  fontsize=14, fontweight="bold")
    ax1.legend(fontsize=11)
    ax1.grid(alpha=0.2)

    # ── Panel 2: Scatter of predictions vs actuals ───────────────────────
    ax2 = axes[1]

    # Clip for visibility
    y_test_clip = np.clip(y_test, 0, np.percentile(y_test, 99))
    y_pred_clip = np.clip(y_pred, 0, np.percentile(y_pred, 99))

    ax2.scatter(y_pred_clip, y_test_clip, s=5, alpha=0.3, color="#1565C0")
    ax2.plot([0, y_pred_clip.max()], [0, y_pred_clip.max()], "k--",
             alpha=0.5, linewidth=1.5)

    ax2.set_xlabel("Predicted Contagion", fontsize=12)
    ax2.set_ylabel("Actual Contagion", fontsize=12)
    ax2.set_title(f"Prediction Scatter — R² = {model_output['r2_test']:.4f}",
                  fontsize=14, fontweight="bold")
    ax2.grid(alpha=0.2)

    fig.tight_layout()
    fig.savefig(PLOTS / "calibration_curve.png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    log(f"  Saved calibration_curve.png")


# ═══════════════════════════════════════════════════════════════════════════════
#  Visualization: Training Curve
# ═══════════════════════════════════════════════════════════════════════════════
def generate_training_curve(model_output: dict):
    """Plot train/test RMSE over boosting rounds."""
    log("Generating training curve …")

    evals = model_output["evals_result"]
    train_rmse = evals["train"]["rmse"]
    test_rmse  = evals["test"]["rmse"]

    fig, ax = plt.subplots(figsize=(12, 6))
    ax.plot(train_rmse, label="Train RMSE", linewidth=1.5, color="#1565C0")
    ax.plot(test_rmse, label="Test RMSE", linewidth=1.5, color="#E91E63")
    ax.axvline(model_output["best_iter"], color="green", linestyle="--",
               alpha=0.7, label=f"Best Iteration: {model_output['best_iter']}")
    ax.set_xlabel("Boosting Round", fontsize=12)
    ax.set_ylabel("RMSE", fontsize=12)
    ax.set_title("XGBoost Training Curve", fontsize=14, fontweight="bold")
    ax.legend(fontsize=11)
    ax.grid(alpha=0.2)

    fig.savefig(PLOTS / "training_curve.png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    log(f"  Saved training_curve.png")


# ═══════════════════════════════════════════════════════════════════════════════
#  Deliverable: GOLDEN_FEATURES.md
# ═══════════════════════════════════════════════════════════════════════════════
def generate_golden_features(shap_ranking, model_output):
    """Generate the Golden Features report."""
    log("Writing GOLDEN_FEATURES.md …")

    xgb_imp = model_output["importance"]

    md = """# GOLDEN FEATURES — Phase 3 Alpha Hunter

## Top 5 Features That Drive Contagion Prediction

These features, ranked by mean |SHAP value|, have the most influence on
the XGBoost model's prediction of forward Hawkes intensity (Y_Contagion).

---

"""
    for i, (fname, shap_val) in enumerate(shap_ranking[:5]):
        # Find XGBoost gain rank
        xgb_rank = "N/A"
        for j, (f2, g) in enumerate(xgb_imp):
            if f2 == fname:
                xgb_rank = f"#{j+1}"
                break

        md += f"""### #{i+1}: `{fname}`
- **SHAP Mean |Value|:** {shap_val:.4f}
- **XGBoost Gain Rank:** {xgb_rank}
"""
        # Add interpretation based on feature name
        if "hawkes" in fname.lower():
            md += "- **Interpretation:** Hawkes self-exciting intensity — measures trade clustering momentum.\n"
        elif "cvd" in fname.lower():
            md += "- **Interpretation:** Cumulative Volume Delta — net directional volume pressure.\n"
        elif "gap" in fname.lower():
            md += "- **Interpretation:** Gap context from scanner — opening shock magnitude/ranking.\n"
        elif "ofi" in fname.lower():
            md += "- **Interpretation:** Order Flow Imbalance — top-of-book pressure dynamics.\n"
        elif "pm_" in fname.lower():
            md += "- **Interpretation:** Pre-market context — positioning before the open.\n"
        elif "halt" in fname.lower() or "post_halt" in fname.lower():
            md += "- **Interpretation:** Halt context — LULD halt dynamics and post-halt behavior.\n"
        elif "volume" in fname.lower() or "vol" in fname.lower():
            md += "- **Interpretation:** Volume dynamics — participation intensity.\n"
        elif "momentum" in fname.lower():
            md += "- **Interpretation:** Momentum at high — intraday momentum continuation.\n"
        md += "\n"

    md += """---

## Full SHAP Ranking (Top 15)

| Rank | Feature | Mean |SHAP| | XGBoost Gain Rank |
|---|---|---|---|
"""
    xgb_lookup = {f: i+1 for i, (f, _) in enumerate(xgb_imp)}
    for i, (fname, shap_val) in enumerate(shap_ranking[:15]):
        xgb_r = xgb_lookup.get(fname, "—")
        md += f"| {i+1} | `{fname}` | {shap_val:.4f} | #{xgb_r} |\n"

    md += f"""
---

## Model Performance

| Metric | Value |
|---|---|
| Train R² | {model_output['r2_train']:.4f} |
| Test R² | {model_output['r2_test']:.4f} |
| Train RMSE | {model_output['train_rmse']:.2f} |
| Test RMSE | {model_output['test_rmse']:.2f} |
| Best Iteration | {model_output['best_iter']} |
| Features Used | {len(model_output['feature_cols'])} |
| Monotonic Constraints | gap_rank (decreasing) |
"""

    (OUT / "GOLDEN_FEATURES.md").write_text(md, encoding="utf-8")
    log(f"  Saved GOLDEN_FEATURES.md")


# ═══════════════════════════════════════════════════════════════════════════════
#  Deliverable: Alpha_Audit.md
# ═══════════════════════════════════════════════════════════════════════════════
def generate_alpha_audit(model_output, fused, shap_ranking):
    """
    Generate the Alpha Audit answering:
    'Can we distinguish a +200% runner from a +20% trap before it happens?'
    """
    log("Writing Alpha_Audit.md …")

    df = model_output["df_valid"]
    y_test = model_output["y_test"]
    y_pred = model_output["y_pred_test"]
    X_test = model_output["X_test"]

    # Separate test set into buckets by actual return
    test_df = df.iloc[len(model_output["y_train"]):].copy().reset_index(drop=True)
    test_df["y_pred_contagion"] = y_pred

    # Return buckets
    super_runner = test_df["return_15m"] > 0.10   # >10% in 15 min
    moderate     = (test_df["return_15m"] >= 0.02) & (test_df["return_15m"] <= 0.10)
    trap         = test_df["return_15m"] < -0.02   # <-2% (gave it all back)
    flat         = ~super_runner & ~moderate & ~trap

    md = f"""# Alpha Audit — Phase 3 Alpha Hunter

## Core Question
> **Can we distinguish a +200% runner from a +20% trap before it happens?**

---

## 1. Dataset Summary

| Metric | Value |
|---|---|
| Total fused events | {len(fused):,} |
| Events with forward targets | {df['y_contagion'].notna().sum():,} |
| Test set size | {len(test_df):,} |
| Test date range | {test_df['date'].min()} → {test_df['date'].max()} |

---

## 2. Return Bucket Analysis (Test Set)

How does the model's predicted Contagion (forward Hawkes AUC) differ across
return outcomes?

| Bucket | Count | % | Avg Predicted Contagion | Avg Actual Contagion |
|---|---|---|---|---|
"""
    for label, mask in [("Super-Runners (>10%)", super_runner),
                         ("Moderate (+2% to +10%)", moderate),
                         ("Flat (−2% to +2%)", flat),
                         ("Traps (<−2%)", trap)]:
        n = mask.sum()
        pct = 100 * n / max(len(test_df), 1)
        avg_pred = test_df.loc[mask, "y_pred_contagion"].mean() if n > 0 else 0
        avg_actual = test_df.loc[mask, "y_contagion"].mean() if n > 0 else 0
        md += f"| {label} | {n} | {pct:.1f}% | {avg_pred:.1f} | {avg_actual:.1f} |\n"

    # ── Discrimination Power ─────────────────────────────────────────────
    # Can the model separate super-runners from traps?
    if super_runner.sum() > 0 and trap.sum() > 0:
        sr_pred = test_df.loc[super_runner, "y_pred_contagion"].values
        tp_pred = test_df.loc[trap, "y_pred_contagion"].values

        sr_mean = sr_pred.mean()
        tp_mean = tp_pred.mean()
        separation = sr_mean - tp_mean
        pooled_std = np.sqrt((sr_pred.std()**2 + tp_pred.std()**2) / 2)
        cohens_d = separation / max(pooled_std, 1e-6)

        md += f"""
### Discrimination Power

| Metric | Value |
|---|---|
| Super-Runner avg predicted contagion | {sr_mean:.1f} |
| Trap avg predicted contagion | {tp_mean:.1f} |
| Separation (ΔPred) | {separation:.1f} |
| Pooled StdDev | {pooled_std:.1f} |
| Cohen's d (effect size) | {cohens_d:.3f} |

**Interpretation:**
"""
        if cohens_d > 0.5:
            md += "The model shows **meaningful separation** between super-runners and traps. "
            md += f"Cohen's d = {cohens_d:.3f} indicates a {'large' if cohens_d > 0.8 else 'medium'} effect size.\n"
        elif cohens_d > 0.2:
            md += f"The model shows **small but detectable separation** (d={cohens_d:.3f}). "
            md += "The signal exists but needs refinement for production use.\n"
        else:
            md += f"The model shows **weak separation** (d={cohens_d:.3f}). "
            md += "Contagion alone may not be sufficient to distinguish outcomes.\n"

    # ── Top predictions vs actual outcomes ────────────────────────────────
    md += """
---

## 3. Top Predicted Contagion Events (Test Set)

The model's highest-conviction trades — did they actually run?

| Ticker | Date | Gap% | Rank | Pred Contagion | Actual Contagion | 15m Return |
|---|---|---|---|---|---|---|
"""
    top_pred = test_df.nlargest(15, "y_pred_contagion")
    for _, row in top_pred.iterrows():
        ret = f"{row['return_15m']*100:.1f}%" if pd.notna(row.get("return_15m")) else "N/A"
        actual = f"{row['y_contagion']:.0f}" if pd.notna(row.get("y_contagion")) else "N/A"
        md += (f"| {row['ticker']} | {row['date']} | {row['gap_pct']*100:.1f}% "
               f"| {int(row['gap_rank'])} | {row['y_pred_contagion']:.0f} "
               f"| {actual} | {ret} |\n")

    # ── SHAP-driven insights ─────────────────────────────────────────────
    md += """
---

## 4. Golden Feature Insights

"""
    top5_features = shap_ranking[:5]
    for i, (fname, shap_val) in enumerate(top5_features):
        md += f"**#{i+1} `{fname}`** (SHAP: {shap_val:.4f})\n\n"

    md += f"""
---

## 5. Model Configuration

| Parameter | Value |
|---|---|
| Algorithm | XGBoost (reg:squarederror) |
| Target | Y_Contagion (∫λ(t)dt, 15min post-FLIP) |
| Sample Weighting | 1/rank² × log(volume) |
| Monotonic Constraints | gap_rank (decreasing: lower rank → higher prediction) |
| Max Depth | {model_output['params']['max_depth']} |
| Learning Rate | {model_output['params']['learning_rate']} |
| Subsample | {model_output['params']['subsample']} |
| Train/Test Split | 80/20 temporal |
| Early Stopping | 50 rounds |
| Best Iteration | {model_output['best_iter']} |

---

## 6. Conclusion

"""
    # Auto-conclusion based on results
    r2 = model_output["r2_test"]
    if r2 > 0.3:
        md += f"**The model achieves R² = {r2:.4f} on the out-of-sample test set**, "
        md += "indicating meaningful predictive power for forward Hawkes contagion. "
    elif r2 > 0.1:
        md += f"**The model achieves R² = {r2:.4f} on the out-of-sample test set**, "
        md += "indicating some predictive signal exists but the task is inherently noisy. "
    else:
        md += f"**The model achieves R² = {r2:.4f} on the out-of-sample test set**, "
        md += "indicating this is a difficult prediction problem. "

    md += """The key insight is not whether we can perfectly predict contagion, but whether
the model's **ranking** is useful — do events the model flags as high-contagion
systematically produce larger moves than those it flags as low-contagion?

See the UMAP Regime Map (`plots/umap_regime_map.png`) to visually inspect
whether super-runners cluster separately from noise.

---

*Generated by Phase 3 Alpha Hunter Pipeline*
"""

    (OUT / "Alpha_Audit.md").write_text(md, encoding="utf-8")
    log(f"  Saved Alpha_Audit.md")


# ═══════════════════════════════════════════════════════════════════════════════
#  MAIN EXECUTION
# ═══════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    log("Phase 3 — The Alpha Hunter (ML Regime Classification)")
    log(f"  Workspace: {OUT}")

    # ── Step 1: Data Fusion + Label Engineering ──────────────────────────
    fused = build_fused_dataset()

    # Quick stats
    for col in ["y_contagion", "y_efficiency", "return_15m"]:
        vals = fused[col].dropna()
        if len(vals) > 0:
            log(f"  {col:25s}  n={len(vals):5d}  mean={vals.mean():12.2f}  "
                f"median={vals.median():12.2f}  std={vals.std():12.2f}")

    # ── Step 2: XGBoost Training ─────────────────────────────────────────
    model_output = train_xgboost(fused)

    # ── Step 3: Visualizations ───────────────────────────────────────────
    generate_training_curve(model_output)
    generate_calibration_plot(model_output)

    shap_ranking, shap_values = generate_shap_analysis(model_output)

    umap_embedding = generate_umap_regime_map(model_output, fused)

    # ── Step 4: Deliverables ─────────────────────────────────────────────
    generate_golden_features(shap_ranking, model_output)
    generate_alpha_audit(model_output, fused, shap_ranking)

    # ── Final summary ────────────────────────────────────────────────────
    total_time = time.perf_counter() - T0
    log(f"\n{'='*70}")
    log(f"PHASE 3 — ALPHA HUNTER — COMPLETE in {total_time:.1f}s")
    log(f"  Model: xgb_regime_model.json (R²={model_output['r2_test']:.4f})")
    log(f"  Golden Features: GOLDEN_FEATURES.md")
    log(f"  Alpha Audit: Alpha_Audit.md")
    log(f"  Plots: {len(list(PLOTS.glob('*.png')))} generated")
    log(f"{'='*70}")
