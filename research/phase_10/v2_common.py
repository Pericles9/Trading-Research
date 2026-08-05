"""
Phase 10 v2 shared plumbing: config, frozen-cohort assertion, and the adaptive
kNN rate estimator.

The v1 module `common.py` supplies the D3 session clock and the targeted
per-event tick reader; both are reused unchanged and are NOT reimplemented here.

D6: shape uses no baseline. The estimator normalizes by each event's own peak.
The flanking sessions have exactly one job — a single scalar per event for the
terminal condition.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import COHORT_KEY, rel  # noqa: E402,F401
from common import read_event_trades, session_window, write_json  # noqa: E402,F401

CONFIG_V2 = "config/phase_10_v2.json"
POOLED = ["dev_v4_primary", "activity_extension"]
NEVER_POOLED = ["row_cap_census", "dev_v4_sidecar"]


def load_config_v2() -> dict:
    with open(rel(CONFIG_V2), encoding="utf-8") as f:
        return json.load(f)


def config_hash_v2() -> str:
    with open(rel(CONFIG_V2), "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()[:8]


def cohort_content_hash(c: pd.DataFrame) -> str:
    body = c.sort_values(COHORT_KEY)[COHORT_KEY + ["cohort_group"]].to_csv(index=False)
    return hashlib.sha256(body.encode()).hexdigest()[:16]


def load_frozen_cohort(cfg: dict) -> pd.DataFrame:
    """Load the v1 manifest and ASSERT its content hash. Mismatch is escalation
    row 1 — the cohort is frozen, never redrawn (D6 / v2 context)."""
    c = pd.read_parquet(rel(cfg["paths"]["cohort_manifest"]))
    c["event_date_canonical"] = c["event_date_canonical"].astype(str)
    h = cohort_content_hash(c)
    expected = cfg["cohort"]["content_hash"]
    if h != expected:
        raise SystemExit(
            f"ESCALATION ROW 1 — cohort content hash {h} != pinned {expected}. "
            "The frozen v1 cohort has changed; v2 must not proceed."
        )
    return c


# ------------------------------------------------------------------ estimator

def knn_rate(ts_ns: np.ndarray, sizes: np.ndarray, k: int,
             zero_span_floor_seconds: float) -> dict:
    """Centred k-block adaptive kNN arrival-rate estimator.

    For sorted arrival times t[0..n-1] and window k, the block for index i is
    a = clip(i - k//2, 0, n-k), b = a + k - 1.

        span_i        = t[b] - t[a]
        print rate_i  = k / span_i                (prints  / second)
        volume rate_i = sum(size[a..b]) / span_i  (shares  / second)

    Evaluated AT the arrival times, so the sampling of the output is as adaptive
    as the estimator and no output grid is imposed (config.estimator).

    Boundary: at the first and last k//2 points the block is clamped and the span
    is one-sided. Not corrected; failure row 4 is the pre-registered guard.

    Returns rate arrays aligned to `ts_ns`, plus the count of floored spans —
    the quantity the tie-variant comparison exists to expose.
    """
    t = np.asarray(ts_ns, dtype=np.float64) / 1e9  # seconds
    s = np.asarray(sizes, dtype=np.float64)
    n = t.size
    if n == 0 or k > n:
        return {"print_rate": np.zeros(0), "volume_rate": np.zeros(0),
                "n_spans_floored": 0, "k_exceeds_n": bool(k > n), "n": int(n)}

    half = k // 2
    i = np.arange(n)
    a = np.clip(i - half, 0, n - k)
    b = a + k - 1

    span = t[b] - t[a]
    n_floored = int((span < zero_span_floor_seconds).sum())
    np.maximum(span, zero_span_floor_seconds, out=span)

    csum = np.concatenate(([0.0], np.cumsum(s)))
    block_size = csum[b + 1] - csum[a]

    return {
        "print_rate": k / span,
        "volume_rate": block_size / span,
        "n_spans_floored": n_floored,
        "k_exceeds_n": False,
        "n": int(n),
    }


def collapse_ties(ts_ns: np.ndarray, sizes: np.ndarray) -> tuple[np.ndarray, np.ndarray, int]:
    """Collapse consecutive same-timestamp prints into one arrival with summed
    size. Timestamps become strictly increasing, so a zero span is impossible."""
    t = np.asarray(ts_ns)
    if t.size == 0:
        return t, np.asarray(sizes), 0
    first = np.concatenate(([True], t[1:] != t[:-1]))
    idx = np.flatnonzero(first)
    summed = np.add.reduceat(np.asarray(sizes, dtype=np.float64), idx)
    return t[idx], summed, int(t.size - idx.size)


def tie_structure(ts_ns: np.ndarray) -> dict:
    """T0d — timestamp-tie structure. Diagnostic only; this is not an
    inter-trade interval distribution (escalation row 8 of the v1 prompt /
    Phase 13 boundary)."""
    t = np.asarray(ts_ns)
    n = t.size
    if n < 2:
        return {"n_prints": int(n), "n_tied_with_prev": 0, "share_tied": 0.0,
                "n_distinct_timestamps": int(n), "max_tie_run": int(n),
                "min_nonzero_gap_ns": None}
    d = np.diff(t)
    tied = int((d == 0).sum())
    nz = d[d > 0]
    first = np.concatenate(([True], d != 0))
    idx = np.flatnonzero(first)
    runs = np.diff(np.concatenate((idx, [n])))
    return {
        "n_prints": int(n),
        "n_tied_with_prev": tied,
        "share_tied": float(tied / (n - 1)),
        "n_distinct_timestamps": int(idx.size),
        "max_tie_run": int(runs.max()),
        "min_nonzero_gap_ns": int(nz.min()) if nz.size else None,
    }


# ------------------------------------------------------------------ crossings

def first_sustained_crossing(vals: np.ndarray, times: np.ndarray, start_idx: int,
                             level: float) -> tuple[float | None, bool]:
    """Time at which `vals` falls to `level` AND STAYS BELOW for the remainder.

    Implemented from the right: the last index at or after `start_idx` where
    vals > level; the crossing is the next point after it. Returns
    (elapsed_seconds_from_times[start_idx], never_reached).
    """
    seg = vals[start_idx:]
    above = np.flatnonzero(seg > level)
    if above.size == 0:
        return 0.0, False
    last = int(above[-1])
    if last >= seg.size - 1:
        return None, True
    j = start_idx + last + 1
    return float(times[j] - times[start_idx]) / 1e9, False


def quantiles(a, qs=(0.0, 0.25, 0.5, 0.75, 1.0)) -> dict:
    a = np.asarray(a, dtype=float)
    a = a[np.isfinite(a)]
    if a.size == 0:
        return {"n": 0, **{f"q{int(q * 100)}": None for q in qs}, "mean": None}
    return {"n": int(a.size),
            **{f"q{int(q * 100)}": float(np.quantile(a, q)) for q in qs},
            "mean": float(a.mean())}
