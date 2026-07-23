"""
Phase 6 T4 - measurement computations from event_minute_bars_v1 (T=0 only).
No further full-table passes - everything here operates on the bars cache
(or its dev-tier equivalent), which is already small enough for pandas.

All three measurements share one full per-minute grid per event (0..session_
total_minutes-1, XNYS session length from the spine, half-days included):
minutes with no trade get volume=0 and a forward-filled last_price (no
trade = no price change). This is what lets "minimum contiguous window"
and "opportunity decay per minute" be computed correctly through thin
trading, not just across the minutes that happen to have prints.

opening_print_sensitivity: the exclude-minute-0 variant is a genuine
recompute, not a mask - it drops minute 0 from the grid entirely and
re-derives its own open_price (the first print at minute >= 1) and its
own open-to-close move magnitude, so it answers "what would this event's
curve look like if the opening print/auction hadn't happened," not just
"what does the curve look like with one data point hidden."
"""
from __future__ import annotations

import numpy as np
import pandas as pd

EVENT_KEYS = ["ticker", "event_date_canonical", "momentum_pct"]


def session_minutes_from_spine(spine: pd.DataFrame, offset: int = 0) -> pd.DataFrame:
    s = spine[spine["session_offset"] == offset].copy()
    s["session_total_minutes"] = np.ceil(
        (s["session_close_epoch"] - s["session_open_epoch"]) / 60.0
    ).astype(int)
    return s[EVENT_KEYS + ["session_total_minutes"]].drop_duplicates(EVENT_KEYS)


def _make_event_ids(keys_df: pd.DataFrame) -> pd.DataFrame:
    out = keys_df[EVENT_KEYS].drop_duplicates(EVENT_KEYS).reset_index(drop=True).copy()
    out["event_id"] = np.arange(len(out))
    return out


def build_full_grid(bars_t0: pd.DataFrame, session_minutes: pd.DataFrame) -> pd.DataFrame:
    """Returns one row per (event, minute) for minute in [0, session_total_minutes),
    with volume (0 if absent) and last_price/first_price (NaN if absent - not yet
    forward-filled; callers fill as needed for their own min-minute-included cutoff)."""
    ev_ids = _make_event_ids(session_minutes)
    sm = session_minutes.merge(ev_ids, on=EVENT_KEYS, how="left")

    n_minutes = sm["session_total_minutes"].to_numpy()
    event_id_arr = sm["event_id"].to_numpy()
    grid_event_id = np.repeat(event_id_arr, n_minutes)
    grid_minute = np.concatenate([np.arange(n) for n in n_minutes]) if len(n_minutes) else np.array([], dtype=int)
    grid = pd.DataFrame({"event_id": grid_event_id, "minute_index": grid_minute})

    bars = bars_t0.merge(ev_ids, on=EVENT_KEYS, how="inner")
    bars_small = bars[["event_id", "minute_index", "volume", "first_price", "last_price"]]

    grid = grid.merge(bars_small, on=["event_id", "minute_index"], how="left")
    grid["volume"] = grid["volume"].fillna(0.0)
    grid = grid.merge(ev_ids, on="event_id", how="left")
    return grid.sort_values(["event_id", "minute_index"]).reset_index(drop=True)


def compute_concentration_curves(grid: pd.DataFrame) -> pd.DataFrame:
    """Volume + move concentration, T=0, minute-index sorted (a time-path curve,
    not a Lorenz curve - never sorted by size)."""
    g = grid.sort_values(["event_id", "minute_index"]).copy()
    session_len = g.groupby("event_id")["minute_index"].transform("max") + 1

    g["cum_volume"] = g.groupby("event_id")["volume"].cumsum()
    total_volume = g.groupby("event_id")["volume"].transform("sum")
    g["volume_share"] = np.where(total_volume > 0, g["cum_volume"] / total_volume, np.nan)

    has_price = g["last_price"].notna()
    price_ffill = g.groupby("event_id")["last_price"].ffill()
    log_ret = np.log(price_ffill / price_ffill.groupby(g["event_id"]).shift(1))
    log_ret = log_ret.where(has_price & has_price.groupby(g["event_id"]).shift(1).fillna(False), 0.0)
    abs_ret = log_ret.abs().fillna(0.0)
    g["cum_path"] = abs_ret.groupby(g["event_id"]).cumsum()
    total_path = g.groupby("event_id")["cum_path"].transform("max")
    g["move_share"] = np.where(total_path > 0, g["cum_path"] / total_path, np.nan)

    g["time_share"] = (g["minute_index"] + 1) / session_len

    out = g[EVENT_KEYS + ["minute_index", "time_share", "volume_share", "move_share"]].copy()
    return out


def _min_window_length(volumes: np.ndarray, target_frac: float) -> int:
    """Shortest contiguous window (in grid minutes) whose sum >= target_frac *
    total. Two-pointer - valid because volumes are non-negative."""
    total = volumes.sum()
    if total <= 0:
        return len(volumes)
    target = target_frac * total
    n = len(volumes)
    left = 0
    running = 0.0
    best = n
    for right in range(n):
        running += volumes[right]
        while running - volumes[left] >= target and left < right:
            running -= volumes[left]
            left += 1
        if running >= target:
            best = min(best, right - left + 1)
    return best


def compute_min_window_stats(grid: pd.DataFrame, thresholds_pct: list[int], min_minute_included: int = 0) -> pd.DataFrame:
    g = grid[grid["minute_index"] >= min_minute_included]
    rows = []
    for event_id, sub in g.groupby("event_id", sort=False):
        vols = sub.sort_values("minute_index")["volume"].to_numpy()
        keys = sub.iloc[0][EVENT_KEYS]
        rec = {k: keys[k] for k in EVENT_KEYS}
        rec["event_id"] = event_id
        for x in thresholds_pct:
            rec[f"min_window_{x}pct_minutes"] = _min_window_length(vols, x / 100.0)
        rows.append(rec)
    return pd.DataFrame(rows)


def compute_opportunity_decay(grid: pd.DataFrame, min_minute_included: int = 0) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Returns (per_minute_fraction_long, per_event_summary).
    per_minute_fraction_long: event keys, minute_index, cum_move, realized_move_fraction.
    per_event_summary: event keys, open_price, close_price, open_close_abs_move,
    minutes_to_50pct (first crossing, NaN if never reached), denom_is_zero flag."""
    g = grid[grid["minute_index"] >= min_minute_included].sort_values(["event_id", "minute_index"]).copy()

    first_idx = g.groupby("event_id")["minute_index"].transform("min")
    is_first_row = g["minute_index"] == first_idx

    price_ffill = g.groupby("event_id")["last_price"].ffill()
    g["price_ffill"] = price_ffill

    # open_price: first_price at each event's first grid row in this variant (may itself
    # be NaN if that first minute had no trade - forward-fill handles it after that point;
    # before any trade, cum_move is defined as 0, not NaN, per the "nothing happened yet" convention).
    open_price_per_event = (
        g.loc[is_first_row].dropna(subset=["first_price"])
        .drop_duplicates("event_id")
        .set_index("event_id")["first_price"]
    )
    # fallback for events whose very first grid minute had no trade at all (first_price NaN there):
    # use the first non-null price_ffill value instead.
    fallback = g.dropna(subset=["price_ffill"]).groupby("event_id")["price_ffill"].first()
    open_price = open_price_per_event.combine_first(fallback)

    g["open_price"] = g["event_id"].map(open_price)
    has_started = g["price_ffill"].notna()
    g["cum_move"] = np.where(has_started, np.log(g["price_ffill"] / g["open_price"]), 0.0)

    close_price = g.groupby("event_id")["price_ffill"].last()
    g["close_price"] = g["event_id"].map(close_price)
    g["open_close_move"] = np.log(g["close_price"] / g["open_price"])
    denom = g["open_close_move"].abs()
    g["realized_move_fraction"] = np.where(denom > 0, g["cum_move"].abs() / denom, np.nan)

    per_minute = g[EVENT_KEYS + ["minute_index", "cum_move", "realized_move_fraction"]].copy()

    def _first_crossing(s: pd.Series) -> float:
        idx = np.where(s.to_numpy() >= 0.5)[0]
        return float(s.index[idx[0]]) if len(idx) else np.nan

    summary_rows = []
    for event_id, sub in g.groupby("event_id", sort=False):
        keys = sub.iloc[0][EVENT_KEYS]
        rec = {k: keys[k] for k in EVENT_KEYS}
        rec["event_id"] = event_id
        rec["open_price"] = sub["open_price"].iloc[0]
        rec["close_price"] = sub["close_price"].iloc[0]
        ocm = sub["open_close_move"].iloc[0]
        rec["open_close_abs_move"] = abs(ocm)
        # covers both a genuine open==close day and the (vanishingly rare) case
        # where this variant's cutoff leaves an event with no post-cutoff price
        # at all (e.g. a single lonely print in minute 0 only) - either way
        # realized_move_fraction is undefined for this event in this variant.
        rec["denom_is_zero"] = bool(pd.isna(ocm) or ocm == 0)
        frac_indexed = sub.set_index("minute_index")["realized_move_fraction"]
        rec["minutes_to_50pct"] = _first_crossing(frac_indexed)
        summary_rows.append(rec)
    per_event_summary = pd.DataFrame(summary_rows)

    return per_minute, per_event_summary


def pooled_per_minute_quantiles(per_minute: pd.DataFrame) -> pd.DataFrame:
    g = per_minute.dropna(subset=["realized_move_fraction"]).groupby("minute_index")["realized_move_fraction"]
    out = g.agg(median="median", q25=lambda s: s.quantile(0.25), q75=lambda s: s.quantile(0.75), n="count")
    return out.reset_index()


def pooled_median_crossing_minute(pooled: pd.DataFrame, threshold: float = 0.5) -> float:
    s = pooled.sort_values("minute_index")
    idx = np.where(s["median"].to_numpy() >= threshold)[0]
    if len(idx) == 0:
        return float("nan")
    return float(s["minute_index"].iloc[idx[0]])
