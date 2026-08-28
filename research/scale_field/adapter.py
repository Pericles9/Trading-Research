"""
The data boundary. Nothing downstream knows anything about DuckDB, parquet, or the
folder layout.

`load_event_prints(event_id, segment)` turns an event id into a sorted nanosecond
timestamp array. `load_cohort()` loads the frozen manifest and asserts its hash.

WHAT THIS FILE DOES NOT DO, DELIBERATELY: it does not implement a read path. The
targeted per-event reader and the D3 session clock already exist, are committed,
and were proven equivalent to `filtered_trades_dev_v4` row-for-row on all 56 dev v4
events at Phase 10 T0d. They are imported unchanged from
`research/phase_10/common.py` (reuse-before-build). Reimplementing them here would
be a second read path to keep in sync and would void that equivalence proof.

Constraints, and where each one is discharged:

  * targeted per-event read only, ZERO full-table passes over filtered_trades
    (standing escalation row 4)         -> common.read_event_trades, which reads
                                           data/filtered/{FOLDER}/trades.parquet
                                           UNIONed with its *_repair_1c siblings.
  * sip_timestamp, not participant_timestamp. Phase 11 A2 settled sip as the single
    basis for the whole phase; do not switch basis by segment.
                                        -> common._TRADE_COLS; asserted below.
  * ties break on sequence_number, which never inverts under the sip sort and broke
    all 58,465 tied rows uniquely in Phase 11. Sort on
    (sip_timestamp, sequence_number).   -> common.read_event_trades sorts on exactly
                                           that pair with a stable mergesort.
  * segment assignment uses the ET wall clock, never the UTC-cast-to-date
    convention, which misassigns EST-winter post prints.
                                        -> common.session_window, which takes the
                                           session date and the RTH open/close from
                                           the pinned XNYS calendar and localizes in
                                           America/New_York before converting to
                                           epoch ns. See DEVIATION below.
  * D4: tick-derived only. No spine numeric column on any computation path.
                                        -> only sip_timestamp leaves this module.

DEVIATION FROM THE HANDOFF DOCSTRING, recorded rather than silently taken. The stub
specified segment assignment "via the DuckDB ICU extension --
TO_TIMESTAMP(sip_timestamp/1e9) AT TIME ZONE 'America/New_York'". That names one
implementation of the ET wall clock, and it is not the one this repo uses: Phase 10
onward reads event folders directly and never opens DuckDB on the tick path at all,
because the pass budget over filtered_trades is zero. The CONSTRAINT the stub is
protecting -- ET wall clock, never a UTC cast -- is met exactly, by
common.session_window. The mechanism differs. Nothing else about the stub changed.

The tie policy is a SEPARATE decision from the tie ORDER and is not taken here.
This function returns ties uncollapsed, as specified; `scale_field.collapse_same_timestamp`
is what applies the reference variant, and it is the caller's choice to apply it.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(REPO_ROOT, "research", "phase_10"))

from common import (  # noqa: E402
    COHORT_KEY, _TRADE_COLS, read_event_trades, rel, session_window,
)

SEGMENTS = ("premarket", "rth", "post")
CONFIG_PATH = os.path.join(REPO_ROOT, "config", "scale_field.json")

# The single basis for the whole phase (Phase 11 A2). Asserted, not assumed: if the
# shared reader ever stops selecting sip_timestamp, every downstream number silently
# changes basis instead of failing.
assert "sip_timestamp" in _TRADE_COLS, "shared reader no longer reads sip_timestamp"
assert "sequence_number" in _TRADE_COLS, "shared reader no longer reads sequence_number"


# --------------------------------------------------------------------------- #
# config
# --------------------------------------------------------------------------- #

def load_config(path: str = CONFIG_PATH) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def config_hash(path: str = CONFIG_PATH) -> str:
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()[:8]


def _read_cfg(cfg: dict | None) -> dict:
    return load_config() if cfg is None else cfg


# --------------------------------------------------------------------------- #
# frozen cohort
# --------------------------------------------------------------------------- #

def cohort_content_hash(c: pd.DataFrame) -> str:
    """Phase 10b T0e's formula, unchanged -- the hash is only meaningful if it is
    computed the same way that produced the committed value."""
    body = c.sort_values(COHORT_KEY)[COHORT_KEY + ["cohort_group"]].to_csv(index=False)
    return hashlib.sha256(body.encode()).hexdigest()[:16]


class CohortMismatch(RuntimeError):
    """The frozen cohort is not the frozen cohort. Hard stop -- do not proceed."""


def load_cohort(cfg: dict | None = None, assert_hash: bool = True) -> pd.DataFrame:
    """The frozen Phase 10 manifest, hash asserted on every run.

    n = 114 total, 100 in the analysis cohort (the 8 row_cap_census and 6
    dev_v4_sidecar rows are carried, labeled, and NEVER pooled). Adds a boolean
    `pooled` column so no caller has to re-derive that rule.
    """
    cfg = _read_cfg(cfg)
    cc = cfg["cohort"]
    c = pd.read_parquet(rel(cc["manifest"]))
    c["event_date_canonical"] = c["event_date_canonical"].astype(str)
    got = cohort_content_hash(c)
    c["pooled"] = ~c["cohort_group"].isin(cc["never_pooled"])
    c["event_id"] = [make_event_id(r.ticker, r.event_date_canonical, r.momentum_pct)
                     for r in c.itertuples(index=False)]
    if not assert_hash:
        return c
    problems = []
    if got != cc["content_hash"]:
        problems.append(f"content hash {got} != committed {cc['content_hash']}")
    if len(c) != cc["n_total"]:
        problems.append(f"n_total {len(c)} != {cc['n_total']}")
    if int(c["pooled"].sum()) != cc["analysis_cohort_n"]:
        problems.append(f"analysis cohort {int(c['pooled'].sum())} != {cc['analysis_cohort_n']}")
    if problems:
        raise CohortMismatch("frozen cohort assertion failed: " + "; ".join(problems))
    return c


def load_detection(cfg: dict | None = None) -> pd.DataFrame:
    """The D7 detection anchor, REUSED not re-derived, at the committed threshold and
    poll interval. Returns one row per event with `segment` (where the anchor fell,
    an EVENT-level label) and `anchor_ns`."""
    cfg = _read_cfg(cfg)
    da = cfg["detection_anchor"]
    d = pd.read_parquet(rel(da["artifact"]))
    d["event_date_canonical"] = d["event_date_canonical"].astype(str)
    d = d[np.isclose(d["threshold"], da["threshold"])].copy()
    out = d[COHORT_KEY + [da["segment_source"], da["anchor_ns_source"], "never_crosses"]].rename(
        columns={da["segment_source"]: "segment", da["anchor_ns_source"]: "anchor_ns"})
    out["event_id"] = [make_event_id(r.ticker, r.event_date_canonical, r.momentum_pct)
                       for r in out.itertuples(index=False)]
    return out.reset_index(drop=True)


# --------------------------------------------------------------------------- #
# event ids
# --------------------------------------------------------------------------- #

def make_event_id(ticker: str, event_date: str, momentum_pct: float) -> str:
    """The Phase 10 event id, which is also the filtered/ folder name."""
    return f"{ticker}_{event_date}_{momentum_pct:.2f}"


def parse_event_id(event_id: str) -> tuple[str, str, float]:
    """-> (ticker, event_date_canonical, momentum_pct).

    rsplit, not split: a ticker may contain an underscore, the date and the momentum
    field never do. Round-trips make_event_id exactly.
    """
    try:
        ticker, date, mom = event_id.rsplit("_", 2)
        return ticker, date, float(mom)
    except ValueError as e:
        raise ValueError(f"not an event id: {event_id!r}") from e


# --------------------------------------------------------------------------- #
# segment bounds -- ET wall clock, D3
# --------------------------------------------------------------------------- #

def segment_bounds_ns(event_date: str) -> dict[str, tuple[int, int]]:
    """Half-open [start, end) epoch-ns bounds per segment for the T=0 extended day.

    The three tile [04:00 ET, post_end) exactly and are disjoint, so a print belongs
    to exactly one. post_end is 20:00 ET, or 17:00 ET on an early-close date; both
    the session date and the RTH open/close come from the pinned XNYS calendar and
    are localized in America/New_York before the epoch conversion.
    """
    w = session_window(event_date, 0)
    if w is None:
        raise ValueError(f"{event_date} is not a session on the pinned XNYS calendar")
    return {
        "premarket": (w["start_ns"], w["rth_open_ns"]),
        "rth": (w["rth_open_ns"], w["rth_close_ns"]),
        "post": (w["rth_close_ns"], w["end_ns"]),
    }


# --------------------------------------------------------------------------- #
# the handoff
# --------------------------------------------------------------------------- #

def load_event_prints(event_id: str, segment: str | None = None,
                      cfg: dict | None = None) -> np.ndarray:
    """Return sip_timestamp for one event's T=0 session, int64 nanoseconds since the
    Unix epoch (UTC), sorted ascending, ties NOT yet collapsed.

    `segment` is None for the whole extended day, or one of SEGMENTS for the
    wall-clock slice. Returns an empty int64 array where the event has no prints in
    the requested window -- never None, never a fallback value.
    """
    ts, _ = load_event_prints_meta(event_id, segment, cfg)
    return ts


def load_event_prints_meta(event_id: str, segment: str | None = None,
                           cfg: dict | None = None) -> tuple[np.ndarray, dict]:
    """`load_event_prints` plus the counts a report has to carry: prints read, prints
    kept, the window, and the tie structure. Every n posted downstream comes from
    here rather than being recounted."""
    cfg = _read_cfg(cfg)
    if segment is not None and segment not in SEGMENTS:
        raise ValueError(f"segment must be None or one of {SEGMENTS}, got {segment!r}")
    ticker, date, mom = parse_event_id(event_id)

    d = read_event_trades({"paths": {"filtered_root": cfg["paths"]["filtered_root"]}},
                          ticker, date, mom, offsets=(0,))
    df = d.get(0)
    bounds = segment_bounds_ns(date)
    lo, hi = bounds[segment] if segment else (
        bounds["premarket"][0], bounds["post"][1])

    meta = {
        "event_id": event_id, "ticker": ticker, "event_date_canonical": date,
        "momentum_pct": mom, "segment": segment or "all",
        "window_start_ns": int(lo), "window_end_ns": int(hi),
        "n_files": d["_meta"]["n_files"],
        "has_repair_sibling": d["_meta"]["has_repair_sibling"],
        "n_rows_raw": d["_meta"]["n_rows_raw"],
        "n_prints_session": 0 if df is None else int(len(df)),
    }
    if df is None or len(df) == 0:
        meta.update(n_prints=0, n_unique_timestamps=0, n_tied_prints=0,
                    min_nonzero_gap_ns=None, span_seconds=0.0)
        return np.zeros(0, dtype=np.int64), meta

    # read_event_trades has already sorted on (sip_timestamp, sequence_number).
    ts = df["sip_timestamp"].to_numpy(dtype=np.int64)
    ts = ts[(ts >= lo) & (ts < hi)]
    uniq = np.unique(ts)
    gaps = np.diff(uniq)
    meta.update(
        n_prints=int(ts.size),
        n_unique_timestamps=int(uniq.size),
        n_tied_prints=int(ts.size - uniq.size),
        min_nonzero_gap_ns=int(gaps.min()) if gaps.size else None,
        span_seconds=float((ts[-1] - ts[0]) / 1e9) if ts.size else 0.0,
    )
    return ts, meta


def load_event_tape(event_id: str, segment: str | None = None,
                    cfg: dict | None = None) -> pd.DataFrame:
    """(sip_timestamp, price) for the orientation panel. DISPLAY ONLY.

    Price is read here for one reason: a scale-space field is unreadable without the
    tape beside it. It is tick-derived from filtered/ trade prints, so it is not a
    D4-quarantined spine column -- but nothing computed in this brief takes price as
    an input, and no ratio is formed from it, so A12's cross-session boundary flag
    has nothing to attach to either. If price ever enters a computation here, that is
    a new decision and it goes in the register first.
    """
    cfg = _read_cfg(cfg)
    ticker, date, mom = parse_event_id(event_id)
    d = read_event_trades({"paths": {"filtered_root": cfg["paths"]["filtered_root"]}},
                          ticker, date, mom, offsets=(0,))
    df = d.get(0)
    if df is None or len(df) == 0:
        return pd.DataFrame({"ts_ns": np.zeros(0, np.int64), "price": np.zeros(0)})
    bounds = segment_bounds_ns(date)
    lo, hi = bounds[segment] if segment else (bounds["premarket"][0], bounds["post"][1])
    ts = df["sip_timestamp"].to_numpy(dtype=np.int64)
    k = (ts >= lo) & (ts < hi)
    return pd.DataFrame({"ts_ns": ts[k], "price": df["price"].to_numpy()[k]})
