"""
Phase 10c shared plumbing.

Stage 0 constraints enforced here:
  * NO sub-bursts, NO threshold selection, NO void parameter, NO normalisation
    window. Stage 0 measures the interval landscape and nothing else (A1.2).
  * NO interval pooling across events. Every histogram is per event; population
    statements are the distribution ACROSS events of a per-event summary (A1.2).
  * filtered_trades.momentum_pct is quarantined (A1.8). The tick reader selects
    only sip_timestamp, price, size, sequence_number, so the column is never
    loaded. Asserted in verify_quarantine().
"""
from __future__ import annotations

import hashlib
import json
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
P10 = os.path.join(HERE, "..", "phase_10")
sys.path.insert(0, P10)
from common import (COHORT_KEY, read_event_trades, rel, session_window,  # noqa: E402
                    trade_files)

CFG_PATH = "config/phase_10c.json"

# Fixed histogram support so per-event histograms are directly comparable.
# After the D12 exact-tie collapse the smallest possible interval is 1 ns, so
# log10 = -9 is a hard floor; 10^5 s is well beyond any extended-day session.
LOG_LO, LOG_HI = -9.0, 5.0


def load_cfg() -> dict:
    with open(rel(CFG_PATH), encoding="utf-8") as f:
        cfg = json.load(f)
    # shim: the Phase 10 tick reader wants cfg["paths"]["filtered_root"]
    cfg.setdefault("paths", {})["filtered_root"] = "data/filtered"
    return cfg


def cfg_hash() -> str:
    with open(rel(CFG_PATH), "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()[:8]


def class_e(cfg) -> dict:
    return cfg["cooper_values"]["_class_E_fill_before_stage_0"]


def class_m(cfg) -> dict:
    return cfg["cooper_values"]["_class_M_fill_at_stage_0_approval"]


def verify_quarantine() -> dict:
    """A1.8: confirm by column name that momentum_pct is never read from ticks."""
    import common as p10common
    cols = list(p10common._TRADE_COLS)
    return {"tick_reader_columns": cols,
            "momentum_pct_in_read_path": "momentum_pct" in cols,
            "verified": "momentum_pct" not in cols,
            "note": ("research/phase_10/common.py:_TRADE_COLS is the only column list the tick "
                     "reader uses. momentum_pct is absent from it, so the quarantined spine "
                     "numeric is never loaded, let alone computed on.")}


# ---------------------------------------------------------------- dev sample
def load_dev_sample(cfg) -> pd.DataFrame:
    """dev_v4_primary (50) plus dev_v4_sidecar (6), carried and LABELLED (A1.6)."""
    coh = pd.read_parquet(rel("results/phase_10/artifacts/t1_cohort_manifest.parquet"))
    coh["event_date_canonical"] = coh["event_date_canonical"].astype(str)
    want = [cfg["dev_sample"]["name"], "dev_v4_sidecar"]
    d = coh[coh["cohort_group"].isin(want)].copy().reset_index(drop=True)
    d["is_sidecar"] = d["cohort_group"] == "dev_v4_sidecar"
    return d


def load_detection(cfg) -> pd.DataFrame:
    """Detection anchors. Variant is cfg.data.detection_anchor_variant (provisional
    poll0 per A1.6; confirmed or revised at Stage 0 approval on T0.6)."""
    v = cfg["data"]["detection_anchor_variant"]
    d = pd.read_parquet(rel("results/phase_10/artifacts/v2_r13_detection.parquet"))
    d["event_date_canonical"] = d["event_date_canonical"].astype(str)
    keep = COHORT_KEY + [f"det_ns_{v}", f"det_segment_{v}"]
    d = d[keep].drop_duplicates(subset=COHORT_KEY).reset_index(drop=True)
    return d.rename(columns={f"det_ns_{v}": "det_ns", f"det_segment_{v}": "det_segment"})


# ---------------------------------------------------------------- intervals
def collapse_ties(ts_ns: np.ndarray) -> np.ndarray:
    """D12: collapse exact-timestamp ties into one trade event. log(0) is undefined
    and this is the reference variant -- no alternatives implemented (S2.5)."""
    if ts_ns.size == 0:
        return ts_ns
    return np.unique(ts_ns)


def sweep_aggregate(ts_ns: np.ndarray, floor_us: float) -> tuple[np.ndarray, int]:
    """D1 candidate: aggregate consecutive prints within floor_us of each other into
    one trade event, taking the FIRST constituent timestamp (S3.1).

    Chained: each print is compared to the timestamp of the group it would join, so
    a run of prints each within the floor of its predecessor becomes one event only
    while the run stays inside the floor of the group's opening print. Returns
    (aggregated timestamps, n_absorbed).
    """
    if ts_ns.size == 0:
        return ts_ns, 0
    floor_ns = float(floor_us) * 1000.0
    keep = np.empty(ts_ns.size, dtype=bool)
    keep[0] = True
    anchor = ts_ns[0]
    for i in range(1, ts_ns.size):
        if ts_ns[i] - anchor > floor_ns:
            keep[i] = True
            anchor = ts_ns[i]
        else:
            keep[i] = False
    return ts_ns[keep], int((~keep).sum())


def log_intervals(ts_ns: np.ndarray) -> np.ndarray:
    """log10 of inter-trade intervals in SECONDS. Input must already be tie-collapsed."""
    if ts_ns.size < 2:
        return np.zeros(0)
    dt = np.diff(ts_ns).astype(np.float64) / 1e9
    dt = dt[dt > 0]
    return np.log10(dt)


def hist_density(logs: np.ndarray, bin_width: float = 0.1):
    """Per-event log-interval histogram on the fixed support. Density, not counts,
    so events of different size are comparable. NO SMOOTHING (S2.2)."""
    edges = np.arange(LOG_LO, LOG_HI + bin_width, bin_width)
    cnt, _ = np.histogram(logs, bins=edges)
    centers = (edges[:-1] + edges[1:]) / 2.0
    n = cnt.sum()
    dens = cnt / (n * bin_width) if n else np.zeros_like(cnt, dtype=float)
    return centers, dens, cnt


def find_modes(centers, dens, prominence_frac: float):
    """Prominence-based peak detection, prominence expressed as a FRACTION of the
    histogram's own peak density so it is scale-free across events.

    NOTE: the config fixes the criterion ('prominence') but not its value. Stage 0
    therefore sweeps it and reports every value rather than choosing one.
    """
    from scipy.signal import find_peaks
    if dens.max() <= 0:
        return np.zeros(0, dtype=int)
    pk, _ = find_peaks(dens, prominence=prominence_frac * dens.max())
    return pk


def first_trough_right_of(centers, dens, peak_idx: int):
    """Index of the first local minimum strictly right of peak_idx, or None."""
    for i in range(peak_idx + 1, len(dens) - 1):
        if dens[i] <= dens[i - 1] and dens[i] < dens[i + 1]:
            return i
    return None


# ---------------------------------------------------------------- sessions
CLOSING_PRINT_CODES = frozenset({8, 15})


def assign_segment(a, codes, opn, close) -> str:
    """evening / premarket / rth, with the Amendment 6 auction override.

    A print carrying condition code 8 (Closing Prints) or 15 (Market Center
    Official Close) is assigned to 'rth' -- the session whose close it settles
    -- regardless of its timestamp. Without this override a closing-cross print
    a few microseconds past the close is bucketed into the NEXT day's evening
    segment while its own twin, timestamped a moment earlier, stays in rth: the
    tick stream and the anchor disagreeing about which session the print
    belongs to (Amendment 6 section A). Scope is all trades, not anchor
    classification only; the affected population is 291 near-close prints
    against 25.2M in the cohort (Amendment 6, from the Amendment 5 census).

    codes: iterable of int condition codes for this print, or None/empty if
    unavailable -- in which case the override cannot fire and the plain
    timestamp rule applies.
    """
    if codes and (set(codes) & CLOSING_PRINT_CODES):
        return "rth"
    if a > close:
        return "evening"
    if a >= opn:
        return "rth"
    return "premarket"


def session_bounds(event_date: str) -> dict | None:
    """Extended-day session bounds plus the RTH sub-boundaries."""
    w = session_window(event_date, 0)
    if w is None:
        return None
    return {"start_ns": w["start_ns"], "end_ns": w["end_ns"],
            "rth_open_ns": w["rth_open_ns"], "rth_close_ns": w["rth_close_ns"],
            "span_minutes": w["span_minutes"], "is_early_close": w["is_early_close"]}


def clipped_fraction(ts_ns: np.ndarray, bounds: dict, kernel_min: float,
                     cut_at_rth: bool) -> dict:
    """Fraction of interval midpoints whose CENTERED clock-time window of duration
    kernel_min would be clipped by a session boundary (D3).

    cut_at_rth=False -> clip only at the extended-day open/close. This is the
      variant S3.3 motivates: it names the overnight gap as the thing to exclude.
    cut_at_rth=True  -> additionally treat the RTH open and close as boundaries.
    Both are reported so the choice is visible rather than assumed.
    """
    if ts_ns.size < 2:
        return {"n_intervals": 0, "clipped_fraction": float("nan")}
    mid = (ts_ns[:-1].astype(np.float64) + ts_ns[1:].astype(np.float64)) / 2.0
    half = kernel_min * 60.0 * 1e9 / 2.0
    lo_edges = [bounds["start_ns"]]
    hi_edges = [bounds["end_ns"]]
    if cut_at_rth:
        lo_edges += [bounds["rth_open_ns"], bounds["rth_close_ns"]]
        hi_edges += [bounds["rth_open_ns"], bounds["rth_close_ns"]]
    lo = np.asarray(lo_edges, dtype=np.float64)
    hi = np.asarray(hi_edges, dtype=np.float64)
    # a window is clipped if any boundary falls strictly inside (mid-half, mid+half)
    left = (mid[:, None] - half < lo[None, :]) & (mid[:, None] > lo[None, :])
    right = (mid[:, None] + half > hi[None, :]) & (mid[:, None] < hi[None, :])
    clipped = (left | right).any(axis=1)
    # windows running past the outer session edges are clipped by definition
    clipped |= (mid - half < bounds["start_ns"]) | (mid + half > bounds["end_ns"])
    return {"n_intervals": int(mid.size), "clipped_fraction": float(clipped.mean())}


def median_se_min_count(sigma_log10: float, precision_factor: float) -> float:
    """D4 derivation, documented rather than picked.

    The standard error of a sample median is asymptotically
        SE = sqrt(pi/2) * sigma / sqrt(n)
    for a normal sample. Requiring the local median to be estimated to within a
    multiplicative factor F in log space means SE <= log10(F), hence
        n >= ( sqrt(pi/2) * sigma_log10 / log10(F) )^2
    sigma_log10 is the event's own spread of log10 intervals, so the floor is
    data-derived per event rather than a chosen constant.
    """
    if precision_factor <= 1.0 or sigma_log10 <= 0:
        return float("nan")
    return float((np.sqrt(np.pi / 2.0) * sigma_log10 / np.log10(precision_factor)) ** 2)


def write_json(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, default=str)
