"""
Phase 6b T4 - measurements from event_minute_bars_v2 (T=0 only). Reuses
research.phase_6.measurements' grid/concentration/min-window machinery
unchanged (the grid shape is identical whether it spans an RTH day or an
extended day - only session_total_minutes and what's fed in differs).
New here: segment volume shares, the primary prev_close/day_high_ext
opportunity-decay anchor, the day-high time-of-day distribution, and the
rth_legacy comparability variant (built by re-indexing v2's own rth-segment
bars to an RTH-relative clock and running Phase 6's *original* decay
function on them unchanged - not a reimplementation).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from research.phase_6.measurements import (
    EVENT_KEYS, build_full_grid, compute_concentration_curves, compute_min_window_stats,
    compute_opportunity_decay, pooled_per_minute_quantiles, pooled_median_crossing_minute,
)

__all__ = [
    "EVENT_KEYS", "build_full_grid", "compute_concentration_curves", "compute_min_window_stats",
    "compute_opportunity_decay", "pooled_per_minute_quantiles", "pooled_median_crossing_minute",
    "session_bounds_from_spine", "compute_day_high_ext", "compute_segment_shares",
    "compute_primary_opportunity_decay", "compute_rth_legacy_decay", "high_time_of_day",
]


def session_bounds_from_spine(spine: pd.DataFrame, offset: int = 0) -> pd.DataFrame:
    s = spine[spine["session_offset"] == offset].copy()
    s["day_length_minutes"] = np.ceil(
        (s["post_end_et"] - s["premarket_start_et"]).dt.total_seconds() / 60.0
    ).astype(int)
    s["rth_open_min"] = (s["rth_open_et"] - s["premarket_start_et"]).dt.total_seconds() / 60.0
    s["rth_close_min"] = (s["rth_close_et"] - s["premarket_start_et"]).dt.total_seconds() / 60.0
    s = s.rename(columns={"day_length_minutes": "session_total_minutes"})
    return s[EVENT_KEYS + ["session_total_minutes", "rth_open_min", "rth_close_min",
                           "premarket_start_et", "is_early_close"]].drop_duplicates(EVENT_KEYS)


def compute_day_high_ext(bars_t0: pd.DataFrame) -> pd.DataFrame:
    """Per event: MAX(bar.high) across the full extended day (all segments)."""
    out = bars_t0.groupby(EVENT_KEYS, as_index=False)["high"].max().rename(columns={"high": "day_high_ext"})
    return out


def compute_segment_shares(bars_t0: pd.DataFrame) -> pd.DataFrame:
    """Per event: volume share by segment (premarket/rth/post)."""
    totals = bars_t0.groupby(EVENT_KEYS)["volume"].sum().rename("total_volume")
    by_seg = bars_t0.groupby(EVENT_KEYS + ["segment"])["volume"].sum().unstack("segment", fill_value=0.0)
    for seg in ["premarket", "rth", "post"]:
        if seg not in by_seg.columns:
            by_seg[seg] = 0.0
    out = by_seg.join(totals).reset_index()
    for seg in ["premarket", "rth", "post"]:
        out[f"{seg}_share"] = np.where(out["total_volume"] > 0, out[seg] / out["total_volume"], np.nan)
    return out


def compute_primary_opportunity_decay(grid: pd.DataFrame, prev_close: pd.Series, day_high_ext: pd.Series) -> tuple[pd.DataFrame, pd.DataFrame]:
    """realized(t) = log(last_price_t / prev_close) / log(day_high_ext / prev_close).
    prev_close, day_high_ext: Series indexed by event_id (from grid's own event_id space)."""
    g = grid.sort_values(["event_id", "minute_index"]).copy()

    price_ffill = g.groupby("event_id")["last_price"].ffill()
    g["price_ffill"] = price_ffill
    g["prev_close"] = g["event_id"].map(prev_close)
    g["day_high_ext"] = g["event_id"].map(day_high_ext)

    has_started = g["price_ffill"].notna()
    g["cum_move"] = np.where(has_started, np.log(g["price_ffill"] / g["prev_close"]), 0.0)

    denom = np.log(g["day_high_ext"] / g["prev_close"])
    g["denom"] = denom
    g["realized_move_fraction"] = np.where(denom > 0, g["cum_move"] / denom, np.nan)
    # negative cum_move (price currently below prev_close) can make realized<0 - keep signed,
    # per the fixed formula (no abs() in the prompt's primary-anchor definition, unlike rth_legacy)

    per_minute = g[EVENT_KEYS + ["minute_index", "cum_move", "realized_move_fraction"]].copy()

    def _first_crossing(s: pd.Series) -> float:
        idx = np.where(s.to_numpy() >= 0.5)[0]
        return float(s.index[idx[0]]) if len(idx) else np.nan

    rows = []
    for event_id, sub in g.groupby("event_id", sort=False):
        keys = sub.iloc[0][EVENT_KEYS]
        rec = {k: keys[k] for k in EVENT_KEYS}
        rec["event_id"] = event_id
        rec["prev_close"] = sub["prev_close"].iloc[0]
        rec["day_high_ext"] = sub["day_high_ext"].iloc[0]
        rec["denom_nonpositive"] = bool(sub["denom"].iloc[0] <= 0)
        frac_indexed = sub.set_index("minute_index")["realized_move_fraction"]
        rec["minutes_to_50pct"] = _first_crossing(frac_indexed)
        rows.append(rec)
    per_event_summary = pd.DataFrame(rows)
    return per_minute, per_event_summary


def realized_at_minute(per_minute: pd.DataFrame, target_minute_by_event: pd.Series) -> pd.Series:
    """per event_id: realized_move_fraction at the event's own target minute (e.g. RTH-open minute)."""
    idx = per_minute.set_index(["event_id", "minute_index"])["realized_move_fraction"]
    out = {}
    for event_id, m in target_minute_by_event.items():
        m_int = int(round(m))
        out[event_id] = idx.get((event_id, m_int), np.nan)
    return pd.Series(out, name="realized_at_target")


def compute_rth_legacy_decay(bars_t0: pd.DataFrame, session_bounds: pd.DataFrame):
    """Phase 6's *original* decay definition (open=first RTH print, close=last
    RTH print), computed on v2's rth-segment bars only, re-indexed to an
    RTH-relative clock (minute 0 = RTH open) so Phase 6's own, unmodified
    build_full_grid/compute_opportunity_decay can be reused verbatim - not a
    reimplementation, so it is directly comparable to Phase 6's 52/57."""
    rth_bars = bars_t0[bars_t0["segment"] == "rth"][EVENT_KEYS + ["minute_index", "volume", "first_price", "last_price"]].copy()
    bounds = session_bounds[EVENT_KEYS + ["rth_open_min", "rth_close_min"]]
    rth_bars = rth_bars.merge(bounds, on=EVENT_KEYS, how="inner")
    rth_bars["minute_index"] = (rth_bars["minute_index"] - rth_bars["rth_open_min"]).round().astype(int)
    rth_bars = rth_bars.drop(columns=["rth_open_min", "rth_close_min"])

    rth_session_minutes = bounds.copy()
    rth_session_minutes["session_total_minutes"] = np.ceil(rth_session_minutes["rth_close_min"] - rth_session_minutes["rth_open_min"]).astype(int)
    rth_session_minutes = rth_session_minutes[EVENT_KEYS + ["session_total_minutes"]]

    grid_rth = build_full_grid(rth_bars, rth_session_minutes)
    per_minute_rth, per_event_summary_rth = compute_opportunity_decay(grid_rth, min_minute_included=0)
    return per_minute_rth, per_event_summary_rth


def high_time_of_day(bars_t0: pd.DataFrame, premarket_start_by_event: pd.Series) -> pd.DataFrame:
    """Per event: ET clock time-of-day of the minute bar achieving day_high_ext
    (first such minute if tied), as premarket_start_et + minute_index minutes."""
    max_high = bars_t0.groupby(EVENT_KEYS)["high"].transform("max")
    at_max = bars_t0[bars_t0["high"] == max_high].sort_values(EVENT_KEYS + ["minute_index"])
    first_at_max = at_max.drop_duplicates(EVENT_KEYS, keep="first").copy()

    def _key(row):
        return (row["ticker"], row["event_date_canonical"], row["momentum_pct"])

    first_at_max["event_key"] = first_at_max.apply(_key, axis=1)
    pm_start = premarket_start_by_event
    first_at_max["premarket_start_et"] = first_at_max["event_key"].map(pm_start)
    first_at_max["high_time_et"] = first_at_max["premarket_start_et"] + pd.to_timedelta(first_at_max["minute_index"], unit="m")
    first_at_max["high_time_of_day"] = first_at_max["high_time_et"].dt.time
    first_at_max["high_hour_decimal"] = first_at_max["high_time_et"].dt.hour + first_at_max["high_time_et"].dt.minute / 60.0
    return first_at_max[EVENT_KEYS + ["minute_index", "high", "high_time_of_day", "high_hour_decimal"]].rename(columns={"minute_index": "high_minute_index"})
