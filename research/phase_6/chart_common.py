"""
Phase 6 T5 - shared charting helpers. Standard chart rules per
Agent_Prompt_Standard.md SS9: Plotly, standalone HTML, one per file, n
annotated per bucket, distribution not just center, raw scatter/strip
behind aggregates where point count permits, no smoothing, outliers
shown never clipped, caption states sample/filters/config hash.
"""
from __future__ import annotations

import hashlib
import json

import numpy as np
import pandas as pd

EVENT_KEYS = ["ticker", "event_date_canonical", "momentum_pct"]


def config_hash(path="config/phase_6.json") -> str:
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()[:12]


def pooled_curve_by_group(long_df: pd.DataFrame, group_col: str, value_col: str, x_col: str, t_grid: np.ndarray):
    """long_df: one row per (event, x_col) with value_col (may be NaN). Interpolates
    each event's curve onto t_grid (linear, clamped at ends) and returns per-group
    median/q25/q75/n arrays aligned to t_grid. Events with <2 valid points are
    excluded from that value_col's pooling (e.g. zero total volume/path)."""
    out = {}
    for grp, sub in long_df.groupby(group_col):
        curves = []
        for _, ev_sub in sub.groupby(EVENT_KEYS):
            ev_sub = ev_sub.sort_values(x_col)
            x = ev_sub[x_col].to_numpy()
            y = ev_sub[value_col].to_numpy()
            valid = ~np.isnan(y)
            if valid.sum() < 2:
                continue
            xv, yv = x[valid], y[valid]
            curves.append(np.interp(t_grid, xv, yv, left=yv[0], right=yv[-1]))
        if not curves:
            out[grp] = {"median": np.full_like(t_grid, np.nan), "q25": np.full_like(t_grid, np.nan),
                        "q75": np.full_like(t_grid, np.nan), "n": 0}
            continue
        arr = np.array(curves)
        out[grp] = {
            "median": np.median(arr, axis=0), "q25": np.quantile(arr, 0.25, axis=0),
            "q75": np.quantile(arr, 0.75, axis=0), "n": arr.shape[0],
        }
    return out


def seeded_overlay_groups(events: pd.DataFrame, seed: int, n_random: int) -> dict:
    """events must carry a 'decile' column. Returns {'top_decile':df,'bottom_decile':df,
    'seeded_random_30':df} - each capped at n_random events (seed 42) so per-event overlay
    traces stay readable (~1,580 events per decile would render as unreadable spaghetti);
    only the sortable index (T4e) covers every event with no sampling."""
    rng = np.random.default_rng(seed)
    top_pool = events[events["decile"] == events["decile"].max()]
    bottom_pool = events[events["decile"] == events["decile"].min()]

    def _sample(pool):
        idx = rng.choice(pool.index.to_numpy(), size=min(n_random, len(pool)), replace=False)
        return pool.loc[idx]

    top = _sample(top_pool)
    bottom = _sample(bottom_pool)
    idx = rng.choice(events.index.to_numpy(), size=min(n_random, len(events)), replace=False)
    rand = events.loc[idx]
    return {"top_decile": top, "bottom_decile": bottom, f"seeded_random_{n_random}": rand}


CAPTION_TEMPLATE = "n={n} | filters: {filters} | config hash: {chash}"
