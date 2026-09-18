"""
Relative momentum v0 -- shared plumbing.

Facet 1 (entry/exit) is the existing participation gate, reused as-is from its committed
per-trade record. Nothing under scanner-epg-momentum/ is executed, imported or modified.
Facet 2 (qualification) is built here.

D4: every measured quantity is tick-derived. No spine numeric column enters a computed
quantity anywhere in this package -- momentum_pct is used only to resolve an event folder
name, which is a path lookup, not an input to any number.
"""
from __future__ import annotations

import glob
import hashlib
import json
import os
import pathlib

import numpy as np
import pandas as pd

CFG = "config/relative_momentum_v0.json"
ART = "results/relative_momentum/v0/artifacts"
CHARTS = "results/relative_momentum/v0/charts"

REPO = pathlib.Path(__file__).resolve().parents[2]

PER_TRADE = ("scanner-epg-momentum/backtest/results/phase_f/val_full/per_trade.parquet")
PRIOR_CLOSE = "results/relative_momentum/r0/artifacts/t0a2_prior_close.parquet"
BASELINE = "results/fundamental_exploration/e2/artifacts/e2_t2a_baseline.parquet"
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
    """Verbatim from research/phase_10/common.py:215 -- do not modify independently."""
    return f"{row['ticker']}_{row['event_date_canonical']}_{row['momentum_pct']:.2f}"


def load_d1() -> pd.DataFrame:
    """D1 = momentum_events_canonical WHERE in_scope AND source_file = 'file1', via D15's
    materialization. A live SELECT against the view scans filtered_trades/filtered_quotes
    unconditionally; see research/relative_momentum/common.py."""
    u = pd.read_parquet(REPO / UNIVERSE).copy()
    if pd.api.types.is_datetime64_any_dtype(u["event_date_canonical"]):
        u["event_date_canonical"] = u["event_date_canonical"].dt.strftime("%Y-%m-%d")
    u = u[u["source_file"] == "file1"][
        ["ticker", "event_date_canonical", "momentum_pct"]].copy()
    u["event_id"] = u.apply(event_id, axis=1)
    return u.reset_index(drop=True)


def first_window_trades() -> pd.DataFrame:
    """One row per event: the gate's FIRST rising-edge entry and its window-close exit.

    entry_type == 'first' marks the first entry of EACH pass window, so an event carries
    several. The brief's 'first window only' is the earliest of them, taken per (ticker, date).
    """
    d = pd.read_parquet(REPO / PER_TRADE)
    f = d[d["entry_type"] == "first"].sort_values("entry_ts")
    fw = f.groupby(["ticker", "date"], as_index=False).first()
    fw["date"] = fw["date"].astype(str).str.slice(0, 10)
    fw["natural_hold_sec"] = (fw["natural_exit_ts"] - fw["entry_ts"]) / NS
    fw["key"] = fw["ticker"] + "|" + fw["date"]
    return fw.reset_index(drop=True)


def event_folder(ticker: str, date: str) -> str | None:
    """Resolve an event's filtered/ folder by (ticker, date), the same glob fallback
    scanner-epg-momentum/backtest/data/loaders/trades.py::load_trades uses when the exact
    momentum-suffixed name does not match."""
    hits = sorted(glob.glob(str(REPO / "data" / "filtered" / f"{ticker}_{date}_*")))
    return hits[0] if hits else None


def window_dollar_volume(folder: str, t_hi_ns: int, w_seconds: int) -> dict:
    """Dollar volume and print count of every trade in [t_hi - W, t_hi], from the event's
    own trades.parquet.

    CAUSAL, asserted here rather than assumed: the upper bound is t_hi inclusive and no row
    with sip_timestamp > t_hi is read into any returned quantity.
    """
    import pyarrow.parquet as pq

    path = os.path.join(folder, "trades.parquet")
    if not os.path.exists(path):
        return {"ok": False, "reason": "no_trades_parquet"}
    tb = pq.read_table(path, columns=["sip_timestamp", "price", "size"])
    ts = tb.column("sip_timestamp").to_numpy()
    lo = t_hi_ns - w_seconds * NS
    m = (ts >= lo) & (ts <= t_hi_ns)
    assert not (ts[m] > t_hi_ns).any(), "causality violated: a print after tau entered the window"
    if not m.any():
        return {"ok": True, "n_prints": 0, "dollar_volume": 0.0, "share_volume": 0,
                "reason": "zero_prints_in_window"}
    px = tb.column("price").to_numpy()[m]
    sz = tb.column("size").to_numpy()[m].astype(np.float64)
    return {"ok": True, "n_prints": int(m.sum()),
            "dollar_volume": float((px * sz).sum()), "share_volume": int(sz.sum()),
            "reason": None}


def write_json(path: str, obj: dict) -> None:
    p = REPO / path
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, default=str)
