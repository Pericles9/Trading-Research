"""
Phase 6b T4 - measurements from event_minute_bars_v2 (T=0 only). Reuses
research.phase_6.measurements' grid/concentration/min-window machinery
unchanged (the grid shape is identical whether it spans an RTH day or an
extended day - only session_total_minutes and what's fed in differs).
New here: segment volume shares, the primary opportunity-decay anchor, the
day-high time-of-day distribution, and the rth_legacy comparability variant
(built by re-indexing v2's own rth-segment bars to an RTH-relative clock and
running Phase 6's *original* decay function on them unchanged - not a
reimplementation).

A8.2 / D4 rework (Amendment 8, 2026-07-28): the primary decay anchor was
`prev_close` (a spine numeric column, quarantined by D4). It is replaced by
`tick_close_t_minus_1_rth` - the tick-derived last trade at or before the
T-1 RTH close (last_price of the max-minute T-1 bar within segment in
{premarket, rth}, from event_minute_bars_v2 itself). Both the anchor and
`day_high_ext` (MAX bar.high over the T+0 extended day) are now tick-only, so
the measurement reads no spine numeric column. Events with no T-1 pre/rth
trades have a NULL anchor (`has_t_minus_1_rth = FALSE`) and are excluded from
the primary decay population only (flag-and-report, per the approved
amendment), retained for concentration / min-window / segment / rth_legacy.
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
    "compute_tick_close_t_minus_1_rth", "compute_primary_opportunity_decay",
    "compute_rth_legacy_decay", "high_time_of_day",
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


def compute_tick_close_t_minus_1_rth(bars: pd.DataFrame) -> pd.DataFrame:
    """Per event: the tick-derived last trade at or before the T-1 RTH close -
    last_price of the max-minute_index bar at session_offset = -1 within
    segment in {premarket, rth} (everything up to and including RTH, excluding
    post). D4-compliant (tick data only, no spine column). NULL for events with
    no such bar (no T-1 premarket/rth trades) -> has_t_minus_1_rth = FALSE.
    `bars` must carry all offsets (not just T=0); same derivation as
    a61_basis_confirmation_rerun.py:49-55, now the measurement anchor."""
    tm1 = bars[(bars["session_offset"] == -1) & (bars["segment"].isin(["premarket", "rth"]))]
    if len(tm1) == 0:
        return pd.DataFrame(columns=EVENT_KEYS + ["tick_close_t_minus_1_rth"])
    idx = tm1.groupby(EVENT_KEYS)["minute_index"].idxmax()
    out = tm1.loc[idx, EVENT_KEYS + ["last_price"]].rename(columns={"last_price": "tick_close_t_minus_1_rth"})
    return out.reset_index(drop=True)


def compute_primary_opportunity_decay(grid: pd.DataFrame, tick_anchor: pd.Series, day_high_ext: pd.Series) -> tuple[pd.DataFrame, pd.DataFrame]:
    """realized(t) = log(last_price_t / tick_close_T-1_RTH) / log(day_high_ext / tick_close_T-1_RTH).
    tick_anchor (tick_close_t_minus_1_rth), day_high_ext: Series indexed by event_id
    (from grid's own event_id space). Both tick-derived (D4-compliant). Events with a
    NULL/non-positive anchor (has_t_minus_1_rth = FALSE) get realized = NaN throughout and
    minutes_to_50pct = NaN - excluded from the primary decay population, flag-and-report."""
    g = grid.sort_values(["event_id", "minute_index"]).copy()

    price_ffill = g.groupby("event_id")["last_price"].ffill()
    g["price_ffill"] = price_ffill
    g["anchor"] = g["event_id"].map(tick_anchor)
    g["day_high_ext"] = g["event_id"].map(day_high_ext)
    g["has_anchor"] = g["anchor"].notna() & (g["anchor"] > 0)

    has_started = g["price_ffill"].notna() & g["has_anchor"]
    g["cum_move"] = np.where(has_started, np.log(g["price_ffill"] / g["anchor"]), 0.0)

    denom = np.log(g["day_high_ext"] / g["anchor"])
    g["denom"] = denom
    g["realized_move_fraction"] = np.where((denom > 0) & g["has_anchor"], g["cum_move"] / denom, np.nan)
    # negative cum_move (price currently below the anchor) can make realized<0 - keep signed,
    # per the fixed formula (no abs() in the primary-anchor definition, unlike rth_legacy)

    per_minute = g[EVENT_KEYS + ["minute_index", "cum_move", "realized_move_fraction"]].copy()

    def _first_crossing(s: pd.Series) -> float:
        idx = np.where(s.to_numpy() >= 0.5)[0]
        return float(s.index[idx[0]]) if len(idx) else np.nan

    rows = []
    for event_id, sub in g.groupby("event_id", sort=False):
        keys = sub.iloc[0][EVENT_KEYS]
        rec = {k: keys[k] for k in EVENT_KEYS}
        rec["event_id"] = event_id
        rec["tick_close_t_minus_1_rth"] = sub["anchor"].iloc[0]
        rec["day_high_ext"] = sub["day_high_ext"].iloc[0]
        rec["has_t_minus_1_rth"] = bool(sub["has_anchor"].iloc[0])
        rec["denom_nonpositive"] = bool(sub["has_anchor"].iloc[0] and sub["denom"].iloc[0] <= 0)
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
