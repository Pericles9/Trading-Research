"""
v1 shared plumbing.

The one substantive new piece is reconstruct_gap_gate(): a faithful post-hoc reconstruction of
the runner's own gap-gate logic, from the run's per-trade record plus the tick archive. It is
not a re-run -- scanner-epg-momentum is read-only per CLAUDE.md and nothing in it is executed
or imported -- but the gap gate is a deterministic function of the tick stream inside a PASS
window, and every PASS window's bounds are on record, so it can be reproduced exactly.

Semantics reproduced from scanner-epg-momentum/backtest/runner.py:822-895:
  - on the rising edge, if the move is already at or above the threshold -> IMMEDIATE entry
  - otherwise the gate enters a QUEUED wait and re-checks every tick while the window stays PASS
  - the first tick meeting the threshold enters (a queued entry)
  - if the window closes first, that window is BLOCKED
  - the condition is tested on price[i]; the fill is price[i+1], the NEXT tick
  - entry_ts is ts[i], the trigger tick, not the fill tick

That fill convention was validated against the existing run: 6/6 spot checks reproduce its
recorded entry_price exactly from px[i+1].

D4: the threshold is applied to move_at, measured against the tick-derived prior close. The
gate's own intraday_pct uses a three-source prev-close chain of which only one is tick-derived,
and v0-T4 measured the two at Spearman 0.314 -- they are not the same condition.
"""
from __future__ import annotations

import glob
import hashlib
import json
import os
import pathlib

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

CFG = "config/relative_momentum_v1.json"
ART = "results/relative_momentum/v1/artifacts"
CHARTS = "results/relative_momentum/v1/charts"

REPO = pathlib.Path(__file__).resolve().parents[2]

PER_TRADE = "scanner-epg-momentum/backtest/results/phase_f/val_full/per_trade.parquet"
PRIOR_CLOSE = "results/relative_momentum/r0/artifacts/t0a2_prior_close.parquet"
BASELINE = "results/fundamental_exploration/e2/artifacts/e2_t2a_baseline.parquet"
DETECTION_PRICE = "results/fundamental_exploration/artifacts/detection_price.parquet"
XS_FLAGS = "results/phase_9/artifacts/t1_cross_session_flags.parquet"
UNIVERSE = "results/phase_5/artifacts/quotes_bitmaps_all.parquet"

NS = 1_000_000_000


def load_cfg() -> dict:
    with open(REPO / CFG) as f:
        return json.load(f)


def cfg_hash() -> str:
    b = (REPO / CFG).read_bytes().replace(b"\r\n", b"\n")
    return hashlib.sha256(b).hexdigest()[:12]


def event_id(row) -> str:
    """Verbatim from research/phase_10/common.py:215."""
    return f"{row['ticker']}_{row['event_date_canonical']}_{row['momentum_pct']:.2f}"


def load_d1() -> pd.DataFrame:
    u = pd.read_parquet(REPO / UNIVERSE).copy()
    if pd.api.types.is_datetime64_any_dtype(u["event_date_canonical"]):
        u["event_date_canonical"] = u["event_date_canonical"].dt.strftime("%Y-%m-%d")
    u = u[u["source_file"] == "file1"][
        ["ticker", "event_date_canonical", "momentum_pct"]].copy()
    u["event_id"] = u.apply(event_id, axis=1)
    u["year"] = u["event_date_canonical"].str[:4]
    return u.reset_index(drop=True)


def event_folder(ticker: str, date: str) -> str | None:
    hits = sorted(glob.glob(str(REPO / "data" / "filtered" / f"{ticker}_{date}_*")))
    return hits[0] if hits else None


def read_ticks(folder: str) -> tuple[np.ndarray, np.ndarray, np.ndarray] | None:
    """Sorted (ts, price, size) for one event, from its own trades.parquet."""
    path = os.path.join(folder, "trades.parquet")
    if not os.path.exists(path):
        return None
    tb = pq.read_table(path, columns=["sip_timestamp", "price", "size"])
    ts = tb.column("sip_timestamp").to_numpy()
    px = tb.column("price").to_numpy()
    sz = tb.column("size").to_numpy().astype(np.float64)
    o = np.argsort(ts, kind="stable")
    return ts[o], px[o], sz[o]


def reconstruct_gap_gate(ts: np.ndarray, px: np.ndarray, windows: pd.DataFrame,
                         prior_close: float, threshold: float) -> dict | None:
    """Apply the runner's gap gate to this event's PASS windows, in time order.

    windows: one row per 'first' entry in the original run, carrying entry_ts (the window's
    rising edge) and natural_exit_ts / natural_exit_price (its window close).

    Returns the FIRST window that produces an entry, with the reconstructed entry, or None if
    every window was blocked. Also returns per-window bookkeeping so blocked windows are a
    reported number rather than an absence.
    """
    trigger_price = prior_close * (1.0 + threshold)
    n_blocked = 0
    for w in windows.sort_values("entry_ts").itertuples(index=False):
        lo = int(np.searchsorted(ts, w.entry_ts, side="left"))
        hi = int(np.searchsorted(ts, w.natural_exit_ts, side="right"))
        if hi <= lo:
            n_blocked += 1
            continue
        seg = px[lo:hi]
        qualifying = np.flatnonzero(seg >= trigger_price)
        if qualifying.size == 0:
            n_blocked += 1
            continue
        i = lo + int(qualifying[0])
        fill = float(px[i + 1]) if i + 1 < px.size else float(px[i])
        return {
            "ok": True,
            "entry_ts": int(ts[i]),
            "entry_price": fill,
            "trigger_price_observed": float(px[i]),
            "entry_kind": "immediate" if i == lo else "queued",
            "ticks_waited": int(i - lo),
            "wait_sec": float((ts[i] - w.entry_ts) / NS),
            "natural_exit_ts": int(w.natural_exit_ts),
            "natural_exit_price": float(w.natural_exit_price),
            "window_rising_edge_ts": int(w.entry_ts),
            "n_windows_blocked_before": n_blocked,
            "trigger_price_threshold": float(trigger_price),
        }
    return {"ok": False, "reason": "all_windows_blocked", "n_windows_blocked": n_blocked,
            "trigger_price_threshold": float(trigger_price)}


def window_dollar_volume(ts: np.ndarray, px: np.ndarray, sz: np.ndarray,
                         t_hi_ns: int, w_seconds: int) -> dict:
    """Dollar volume and print count in [t_hi - W, t_hi]. Causal, asserted."""
    lo = t_hi_ns - w_seconds * NS
    m = (ts >= lo) & (ts <= t_hi_ns)
    assert not (ts[m] > t_hi_ns).any(), "causality violated: a print after tau entered the window"
    if not m.any():
        return {"n_prints": 0, "dollar_volume": 0.0}
    return {"n_prints": int(m.sum()), "dollar_volume": float((px[m] * sz[m]).sum())}


def expanding_quantile_threshold(values: np.ndarray, q: float, min_n: int) -> tuple:
    """For each position k (in chronological order), the q-quantile of values[:k] -- strictly
    prior observations only. Returns (threshold, is_warmup) arrays.

    Where fewer than min_n prior observations exist the threshold is NaN and is_warmup is True;
    the caller passes those candidates rather than comparing against an undefined level.
    """
    n = values.size
    thr = np.full(n, np.nan)
    warm = np.zeros(n, dtype=bool)
    for k in range(n):
        if k < min_n:
            warm[k] = True
            continue
        thr[k] = float(np.quantile(values[:k], q))
    return thr, warm


def write_json(path: str, obj: dict) -> None:
    p = REPO / path
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, default=str)
