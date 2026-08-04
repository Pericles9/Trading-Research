"""
Phase 10 shared plumbing: config load, cohort I/O, session clock, and the
targeted per-event tick read.

Read path (config.read_path): every tick read is a direct parquet read of
`data/filtered/{TICKER}_{DATE}_{MOM:.2f}/trades.parquet` UNIONed with any
`trades_repair_1c.parquet` sibling. There is no read of `filtered_trades`
or `filtered_quotes` anywhere in this phase -- the pass budget over those
tables is zero (escalation row 4). `verify_read_path_equivalence` proves
the union reproduces `filtered_trades_dev_v4` row-for-row on the 56 dev v4
events, which is what licenses the substitution.

Session clock is D3 / Phase 6b: extended day [04:00 ET, post_end) with
post_end = 20:00 ET normally and 17:00 ET on an early-close date, session
dates from the pinned XNYS calendar, all timezone arithmetic in
America/New_York (never a UTC-cast of sip_timestamp).
"""
from __future__ import annotations

import glob
import hashlib
import json
import os
from datetime import time as dtime

import numpy as np
import pandas as pd
import pandas_market_calendars as mcal

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
CONFIG_PATH = os.path.join(REPO_ROOT, "config", "phase_10.json")

EARLY_CLOSE_THRESHOLD = dtime(16, 0, 0)
PREMARKET_START = dtime(4, 0, 0)
NORMAL_POST_END = dtime(20, 0, 0)
EARLY_CLOSE_POST_END = dtime(17, 0, 0)

_CAL_START = "2019-12-01"
_CAL_END = "2026-01-15"

_NS = 1_000_000_000


def load_config(path: str = CONFIG_PATH) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def config_hash(path: str = CONFIG_PATH) -> str:
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()[:8]


def rel(*parts: str) -> str:
    return os.path.join(REPO_ROOT, *parts)


# ---------------------------------------------------------------- session clock

_SESSION_CACHE: dict = {}


def _session_table() -> tuple[pd.DatetimeIndex, np.ndarray, np.ndarray, dict]:
    if "tbl" not in _SESSION_CACHE:
        xnys = mcal.get_calendar("XNYS")
        sched = xnys.schedule(start_date=_CAL_START, end_date=_CAL_END)
        sessions = pd.DatetimeIndex(sched.index).normalize()
        opens = sched["market_open"].dt.tz_convert("America/New_York").dt.tz_localize(None).to_numpy()
        closes = sched["market_close"].dt.tz_convert("America/New_York").dt.tz_localize(None).to_numpy()
        pos = {d: i for i, d in enumerate(sessions)}
        _SESSION_CACHE["tbl"] = (sessions, opens, closes, pos)
    return _SESSION_CACHE["tbl"]


def session_window(event_date: str, offset: int) -> dict | None:
    """Extended-day window for `offset` sessions from `event_date` (D3).

    Returns naive America/New_York wall-clock bounds plus their UTC-epoch-ns
    equivalents, so a sip_timestamp can be compared without per-row tz work.
    """
    sessions, opens, closes, pos = _session_table()
    d = pd.Timestamp(event_date).normalize()
    i0 = pos.get(d)
    if i0 is None:
        return None
    j = i0 + offset
    if j < 0 or j >= len(sessions):
        return None
    sess_date = sessions[j]
    rth_open = pd.Timestamp(opens[j])
    rth_close = pd.Timestamp(closes[j])
    is_early = rth_close.time() < EARLY_CLOSE_THRESHOLD
    start_et = pd.Timestamp.combine(sess_date.date(), PREMARKET_START)
    end_et = pd.Timestamp.combine(
        sess_date.date(), EARLY_CLOSE_POST_END if is_early else NORMAL_POST_END
    )
    to_ns = lambda t: int(t.tz_localize("America/New_York").tz_convert("UTC").value)  # noqa: E731
    return {
        "session_offset": offset,
        "session_date": sess_date.date().isoformat(),
        "start_et": start_et,
        "end_et": end_et,
        "rth_open_et": rth_open,
        "rth_close_et": rth_close,
        "is_early_close": bool(is_early),
        "start_ns": to_ns(start_et),
        "end_ns": to_ns(end_et),
        "rth_open_ns": to_ns(rth_open),
        "rth_close_ns": to_ns(rth_close),
        "span_minutes": int((end_et - start_et).total_seconds() // 60),
    }


def ns_to_et(ns) -> pd.Series:
    """UTC epoch ns -> naive America/New_York wall clock (display only)."""
    return (
        pd.to_datetime(pd.Series(ns), unit="ns", utc=True)
        .dt.tz_convert("America/New_York")
        .dt.tz_localize(None)
    )


# ---------------------------------------------------------------- tick reads

def event_folder(cfg: dict, ticker: str, event_date: str, momentum_pct: float) -> str:
    return rel(cfg["paths"]["filtered_root"], f"{ticker}_{event_date}_{momentum_pct:.2f}")


def trade_files(cfg: dict, ticker: str, event_date: str, momentum_pct: float) -> list[str]:
    """Base trades.parquet plus every *_repair_1c.parquet sibling (CLAUDE.md)."""
    folder = event_folder(cfg, ticker, event_date, momentum_pct)
    if not os.path.isdir(folder):
        return []
    out = []
    base = os.path.join(folder, "trades.parquet")
    if os.path.exists(base):
        out.append(base)
    out.extend(sorted(glob.glob(os.path.join(folder, "trades*_repair_1c.parquet"))))
    return out


_TRADE_COLS = ["sip_timestamp", "price", "size", "sequence_number"]


def read_event_trades(cfg, ticker, event_date, momentum_pct, offsets=(0,)) -> dict:
    """Targeted read of one event's trade prints, sliced to the requested
    extended-day session windows. Returns {offset: DataFrame} sorted by
    (sip_timestamp, sequence_number), plus '_meta' with the counts needed for
    the tick-surface report.

    Never touches filtered_trades / filtered_quotes.
    """
    files = trade_files(cfg, ticker, event_date, momentum_pct)
    meta = {
        "n_files": len(files),
        "has_repair_sibling": any("_repair_1c" in f for f in files),
        "n_rows_raw": 0,
        "n_rows_in_window": 0,
        "per_offset": {},
    }
    if not files:
        return {"_meta": meta}

    frames = [pd.read_parquet(f, columns=_TRADE_COLS) for f in files]
    df = pd.concat(frames, ignore_index=True) if len(frames) > 1 else frames[0]
    meta["n_rows_raw"] = int(len(df))

    ts = df["sip_timestamp"].to_numpy()
    out = {}
    for off in offsets:
        win = session_window(event_date, off)
        if win is None:
            meta["per_offset"][off] = {"n_prints": 0, "window": None}
            continue
        mask = (ts >= win["start_ns"]) & (ts < win["end_ns"])
        sub = df.loc[mask].sort_values(["sip_timestamp", "sequence_number"], kind="mergesort")
        sub = sub.reset_index(drop=True)
        out[off] = sub
        meta["per_offset"][off] = {
            "n_prints": int(len(sub)),
            "session_date": win["session_date"],
            "span_minutes": win["span_minutes"],
            "is_early_close": win["is_early_close"],
        }
        meta["n_rows_in_window"] += int(len(sub))
    meta["n_rows_out_of_window"] = int(meta["n_rows_raw"] - meta["n_rows_in_window"])
    out["_meta"] = meta
    return out


# ---------------------------------------------------------------- cohort I/O

COHORT_KEY = ["ticker", "event_date_canonical", "momentum_pct"]


def load_cohort(cfg: dict) -> pd.DataFrame:
    path = rel(cfg["paths"]["out_artifacts"], "t1_cohort_manifest.parquet")
    df = pd.read_parquet(path)
    df["event_date_canonical"] = df["event_date_canonical"].astype(str)
    return df


NON_POOLED_GROUPS = ("dev_v4_sidecar", "row_cap_census")


def analysis_cohort(cohort: pd.DataFrame) -> pd.DataFrame:
    """Cohort rows that enter pooled statistics: primary + extension only.

    The dev v4 sidecar (deliberately degraded archive) and the row-cap census
    (truncated session tails) are both carried, both labeled, and NEVER pooled.
    """
    return cohort[~cohort["cohort_group"].isin(NON_POOLED_GROUPS)].reset_index(drop=True)


def event_id(row) -> str:
    return f"{row['ticker']}_{row['event_date_canonical']}_{row['momentum_pct']:.2f}"


def write_json(path: str, obj: dict) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, default=_json_default)


def _json_default(o):
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        v = float(o)
        return None if not np.isfinite(v) else v
    if isinstance(o, (np.bool_,)):
        return bool(o)
    if isinstance(o, (pd.Timestamp,)):
        return o.isoformat()
    if isinstance(o, np.ndarray):
        return o.tolist()
    raise TypeError(f"not JSON serializable: {type(o)}")


def quantiles(a, qs=(0.0, 0.25, 0.5, 0.75, 1.0)) -> dict:
    a = np.asarray(a, dtype=float)
    a = a[np.isfinite(a)]
    if a.size == 0:
        return {"n": 0, **{f"q{int(q*100)}": None for q in qs}, "mean": None}
    return {
        "n": int(a.size),
        **{f"q{int(q*100)}": float(np.quantile(a, q)) for q in qs},
        "mean": float(a.mean()),
    }
