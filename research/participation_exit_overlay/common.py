"""
Participation / exit overlay -- shared plumbing.

Builds participation_onset and participation_end from event_minute_bars_v2 under the rule the
brief states, reusing E2's baseline B_e unchanged.

WHY THE WINDOW IS REBUILT RATHER THAN REUSED. The brief says to reuse E2's window artifact if it
exists. It exists and it is not usable as an exit: 443 of the 903 (49.1%) carry a window_end_ts
BEFORE the EPG entry, 40.75% have duration_min == 0 (participation "ends" at t0 itself),
window_end_ts - tau reaches 5.0 days, and the `censored` column is False on all 15,742 rows --
which cannot be right if the event-day censoring the brief attributes to E2 was applied. E2's
brief, config and code were never committed [CORRECTED 2026-09-23, Part III of
prompts/attention_excursion_b1.md: they are committed on origin/explore/fundamental-e2 and on master via
PR #13; the config records C = 10 min, dollar volume, censoring at end of tick data. The zero-duration mass
is E2's units defect -- a per-minute average against a per-10-minute B_e -- corrected on
fix/e2-window-units. This module's trailing SUM is the correct unit], so the declared C, the volume basis and the censoring
rule cannot be read from the repository either. B_e is reused verbatim; the window is rebuilt.

Restricting the minute series to session_offset = 0 is what enforces censoring at the event-day
extended session end -- it is structural, not a filter applied afterwards.
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

CFG = "config/participation_exit_overlay.json"
ART = "results/participation_exit_overlay/artifacts"
CHARTS = "results/participation_exit_overlay/charts"

REPO = pathlib.Path(__file__).resolve().parents[2]

POPULATION = "results/relative_momentum/v2/artifacts/t1_measured.parquet"
BASELINE = "results/fundamental_exploration/e2/artifacts/e2_t2a_baseline.parquet"
E2_WINDOW = "results/fundamental_exploration/e2/artifacts/e2_t2_window.parquet"
FUNDAMENTALS = "results/fundamental_exploration/e2/artifacts/e2_d1_fundamentals.parquet"
DETECTION_PRICE = "results/fundamental_exploration/artifacts/detection_price.parquet"
HALT_LABELS = "scanner-epg-momentum/backtest/results/phase_luld_v3c/halt_labels_v3c.json"

NS = 1_000_000_000
MIN_NS = 60 * NS
SESSION_MINUTES = 960          # 04:00 -> 20:00 ET
ET = "America/New_York"


def load_cfg() -> dict:
    with open(REPO / CFG) as f:
        return json.load(f)


def cfg_hash() -> str:
    b = (REPO / CFG).read_bytes().replace(b"\r\n", b"\n")
    return hashlib.sha256(b).hexdigest()[:12]


def write_json(path: str, obj: dict) -> None:
    p = REPO / path
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, default=str)


def session_base_ns(date_str: str) -> int:
    """04:00:00 America/New_York on the event day, in epoch ns. DST-aware -- the offset is resolved
    by the tz database for that date, not assumed (CLAUDE.md session-calendar rule)."""
    ts = pd.Timestamp(f"{date_str} 04:00:00", tz=ET)
    return int(ts.tz_convert("UTC").value)


def load_population() -> pd.DataFrame:
    """The 903 gap-gated entries, with v2's snapped int64 tau_ns."""
    d = pd.read_parquet(REPO / POPULATION)
    d = d[d["measured"]].copy().reset_index(drop=True)
    d["natural_exit_ts"] = d["natural_exit_ts"].astype("float64").astype("int64")
    return d


def event_folder(ticker: str, date: str) -> str | None:
    hits = sorted(glob.glob(str(REPO / "data" / "filtered" / f"{ticker}_{date}_*")))
    return hits[0] if hits else None


# ------------------------------------------------------- the participation rule

def run_length_first(cond: np.ndarray, start_idx: int, c: int) -> int | None:
    """First index i >= start_idx where cond[i:i+c] is all True. None if no such run exists.

    This is the 'and stays there for C consecutive minutes' clause. A run that would extend past
    the end of the series cannot be confirmed, so it does not count -- which is the censoring rule
    doing its job rather than an off-by-one.
    """
    n = cond.size
    if c <= 0 or start_idx >= n:
        return None
    # cumulative trick: a run of c Trues starting at i means cond[i:i+c].sum() == c
    cs = np.concatenate([[0], np.cumsum(cond.astype(np.int64))])
    for i in range(start_idx, n - c + 1):
        if cs[i + c] - cs[i] == c:
            return int(i)
    return None


def participation_marks(minute_dollar: np.ndarray, b_e: float, t0_minute: int,
                        c: int, multiple: float, trailing: int = 10) -> dict:
    """Onset and end of participation on one event's minute grid.

    minute_dollar : dollar volume per minute, length SESSION_MINUTES, zeros for empty minutes
    t0_minute     : the minute index of t0; both marks are searched STRICTLY AFTER it
    """
    # trailing SUM over `trailing` minutes -- dimensionally comparable with B_e, which is itself a
    # per-10-minute-block figure. A per-minute average would be 10x smaller than B_e.
    k = np.ones(trailing, dtype=np.float64)
    tr = np.convolve(minute_dollar, k, mode="full")[: minute_dollar.size]
    thresh = multiple * b_e
    start = max(t0_minute + 1, 0)
    onset = run_length_first(tr >= thresh, start, c)
    end = run_length_first(tr <= thresh, start, c)
    return {"onset_minute": onset, "end_minute": end,
            "trailing_at_t0": float(tr[t0_minute]) if 0 <= t0_minute < tr.size else np.nan,
            "threshold_usd": float(thresh),
            "peak_trailing_usd": float(tr[start:].max()) if start < tr.size else np.nan}


# ------------------------------------------------------------- tick side

def read_ticks_px(folder: str) -> tuple[np.ndarray, np.ndarray] | None:
    """Sorted (sip_timestamp, price) for one event. Both exits are priced off this one array so
    they share a basis."""
    path = os.path.join(folder, "trades.parquet")
    if not os.path.exists(path):
        return None
    tb = pq.read_table(path, columns=["sip_timestamp", "price"])
    ts = tb.column("sip_timestamp").to_numpy()
    px = tb.column("price").to_numpy()
    if ts.size == 0:
        return None
    o = np.argsort(ts, kind="stable")
    return ts[o], px[o]


def last_print_at_or_before(ts: np.ndarray, px: np.ndarray, t: int) -> float:
    """Tick-exact exit price: the last print at or before t. Both exits are priced this way so the
    comparison is not between a tick basis and a bar basis."""
    j = int(np.searchsorted(ts, t, side="right")) - 1
    return float(px[j]) if j >= 0 else np.nan


SPIKE_THRESHOLD = 0.03  # declared here, not an established repo convention -- see below


def last_print_at_or_before_robust(ts: np.ndarray, px: np.ndarray, t: int,
                                   spike_threshold: float = SPIKE_THRESHOLD) -> dict:
    """last_print_at_or_before, guarded against a single isolated bad tick.

    FOUND MID-RUN, NOT ANTICIPATED BY THE BRIEF. Found in T3: AMC 2024-05-14's exit priced at
    $11.48 against entry and v1's own recorded exit both at $6.63 -- a single 4-share print
    carrying condition codes [32, 37] (37 = odd lot, per docs/data/condition_indicator_code_
    reference.md; 32 is NOT resolved in this repo and its meaning is not asserted here),
    sandwiched between two $6.63 prints microseconds apart. 154 of 903 exits (17%) differed from
    v1's recorded price by >1%, 19 by >5%, 3 by >20%.

    Odd lots are 44% of all trades in this archive (checked on this event alone: 1,514,946 of
    3,472,949), so excluding them outright would be a large, uncited methodology change and would
    make this pricing incomparable with v0/v1/v2's raw next-tick fills, which apply no condition
    or size filter at all. Instead: a condition-and-size-agnostic SPIKE detector. The picked print
    at index j is flagged a spike only if it deviates from BOTH its immediate predecessor and
    immediate successor by more than spike_threshold, AND those two neighbours agree with each
    other within spike_threshold / 2 -- the V-shaped signature of an isolated bad print reverting
    immediately, as opposed to a genuine fast move (which does not revert). A spike with no
    successor to confirm reversion (the very last tick before the exit) is left alone rather than
    guessed at.

    This is a NEW rule, declared for this task, not a claimed established repo convention. Every
    substitution is counted and the share is reported (t3's summary), never silently absorbed.
    """
    n = ts.size
    j = int(np.searchsorted(ts, t, side="right")) - 1
    if j < 0:
        return {"price": np.nan, "spike_replaced": False, "idx": None}

    def is_spike(i: int) -> bool:
        if i <= 0 or i >= n - 1:
            return False
        prev, cur, nxt = px[i - 1], px[i], px[i + 1]
        if prev <= 0 or nxt <= 0:
            return False
        dev_prev = abs(cur - prev) / prev
        dev_next = abs(cur - nxt) / nxt
        neighbours_agree = abs(prev - nxt) / max(prev, nxt) <= spike_threshold / 2
        return bool(dev_prev > spike_threshold and dev_next > spike_threshold and neighbours_agree)

    i = j
    replaced = False
    while i >= 0 and is_spike(i):
        i -= 1
        replaced = True
    if i < 0:
        # every candidate back to the start of the tape was a spike -- fall back to the original
        # pick rather than return nothing; this has not occurred in this dataset (checked below).
        return {"price": float(px[j]), "spike_replaced": False, "idx": j,
                "note": "walked off the start of the tape; kept original pick"}
    return {"price": float(px[i]), "spike_replaced": replaced, "idx": i,
            "n_ticks_walked_back": j - i}


def max_gap_in(ts: np.ndarray, lo: int, hi: int) -> float:
    """Largest inter-trade gap, in seconds, inside [lo, hi]. The halt PROXY -- a gap measurement,
    not a halt classifier."""
    m = (ts >= lo) & (ts <= hi)
    sel = ts[m]
    if sel.size < 2:
        return float("nan")
    return float(np.max(np.diff(sel)) / NS)


def load_halt_labels() -> dict:
    """{'TICKER|DATE': [(start_ns, end_ns), ...]} from LULD-V3c's labeler.

    The LULD exit LINE was abandoned 2026-06-20 (docs/Phase_LULD_V3c.md); these are the labeler's
    halt observations, which are a measurement and not the abandoned exit rule.
    """
    p = REPO / HALT_LABELS
    if not p.exists():
        return {}
    raw = json.load(open(p))
    out: dict[str, list] = {}
    for e in raw.get("events", []):
        key = f"{e['ticker']}|{e['date']}"
        out[key] = [(int(float(h["start_sec"]) * NS), int(float(h["end_sec"]) * NS))
                    for h in e.get("halts", [])]
    return out
