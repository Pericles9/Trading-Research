"""
Arm B -- threshold + hysteresis against a time-of-day-matched flanking baseline.

The comparison arm. Its baseline deliberately differs from Arm A's (config
cooper_decision_points.1): Arm A self-normalizes within the T=0 session, Arm B
compares against what the SAME ticker did at the SAME minute-of-session on
T-3..T-1. The two are not reconciled -- the point is that they disagree in an
informative way rather than a confounded one.

Why time-of-day-matched and not a whole-day average: these names trade thin for
weeks and then enormously on the event day. A whole-day denominator saturates
immediately and the segmentation degenerates into a session flag.

Baseline denominator uses the canonical `trades_bitmap` to decide which flanking
sessions were actually COLLECTED. A collected session with zero prints is real
information (the name did not trade) and contributes zero-count minute slots; an
uncollected session contributes nothing at all, rather than silently depressing
the baseline toward zero.

D4: only tick arrival timestamps and tick prices are read. Flanking sessions
contribute COUNTS only -- no flanking price ever enters any quantity, so no price
basis crosses a session boundary (D4 Amendment A12 is not engaged).
"""
from __future__ import annotations

import numpy as np

__all__ = ["build_baseline", "arm_b_segment"]

_EPS = 1e-9


def _minute_hist(ts_ns: np.ndarray, start_ns: int, span_minutes: int) -> np.ndarray:
    """Prints per minute-of-session, minute 0 = the session's 04:00 ET origin."""
    h = np.zeros(span_minutes, dtype=np.int64)
    if ts_ns.size == 0:
        return h
    idx = ((ts_ns - start_ns) // 60_000_000_000).astype(np.int64)
    idx = idx[(idx >= 0) & (idx < span_minutes)]
    if idx.size:
        np.add.at(h, idx, 1)
    return h


def build_baseline(
    flanking: dict,
    t0_span_minutes: int,
    baseline_window_minutes: int,
    baseline_floor_per_min: float,
) -> dict:
    """Time-of-day-matched baseline rate, prints/min, per minute-of-session.

    `flanking` maps offset -> {"ts": ndarray[ns], "start_ns": int,
    "span_minutes": int, "collected": bool}. Only collected sessions enter the
    denominator.
    """
    W = baseline_window_minutes
    counts = np.zeros(t0_span_minutes, dtype=np.float64)
    slots = np.zeros(t0_span_minutes, dtype=np.float64)
    contributing = []

    for off, f in sorted(flanking.items()):
        if not f.get("collected", False):
            continue
        contributing.append(off)
        span = int(f["span_minutes"])
        h = _minute_hist(np.asarray(f["ts"], dtype=np.int64), int(f["start_ns"]), span)
        # prefix sums make the +/-W neighbourhood an O(1) lookup per minute
        csum = np.concatenate(([0], np.cumsum(h)))
        for m in range(t0_span_minutes):
            lo, hi = max(0, m - W), min(span - 1, m + W)
            if lo > hi:
                continue
            counts[m] += csum[hi + 1] - csum[lo]
            slots[m] += (hi - lo + 1)

    with np.errstate(divide="ignore", invalid="ignore"):
        rate = np.where(slots > 0, counts / np.maximum(slots, 1.0), np.nan)

    has_support = slots > 0
    has_prints = counts > 0
    if not contributing or not has_support.any():
        label = "baseline_undefined"
    elif bool(has_prints.all()):
        label = "defined"
    else:
        label = "baseline_partial"

    floored = np.where(np.isnan(rate), baseline_floor_per_min,
                       np.maximum(rate, baseline_floor_per_min))
    return {
        "rate_per_min": rate,
        "rate_floored": floored,
        "n_minutes": int(t0_span_minutes),
        "n_minutes_with_support": int(has_support.sum()),
        "n_minutes_with_prints": int(has_prints.sum()),
        "contributing_offsets": contributing,
        "label": label,
        "total_flanking_prints": float(
            sum(np.asarray(f["ts"]).size for o, f in flanking.items() if f.get("collected"))
        ),
    }


def _hysteresis(z: np.ndarray, on_thresh: float, off_thresh: float) -> np.ndarray:
    """Two-level Schmitt trigger. ON at z >= on_thresh, OFF at z < off_thresh,
    hold otherwise. Starts OFF."""
    state = np.zeros(z.size, dtype=np.int8)
    cur = 0
    for i in range(z.size):
        if cur == 0:
            if z[i] >= on_thresh:
                cur = 1
        else:
            if z[i] < off_thresh:
                cur = 0
        state[i] = cur
    return state


def _runs(state: np.ndarray) -> list[tuple[int, int]]:
    if state.size == 0:
        return []
    padded = np.concatenate(([0], state, [0]))
    e = np.diff(padded)
    return list(zip(np.flatnonzero(e == 1).tolist(), (np.flatnonzero(e == -1) - 1).tolist()))


def arm_b_segment(
    t0_ts: np.ndarray,
    t0_start_ns: int,
    t0_span_minutes: int,
    baseline: dict,
    *,
    grid_seconds: int,
    rate_window_seconds: int,
    on_multiplier: float,
    off_multiplier: float,
    min_dwell_seconds: float,
    merge_gap_seconds: float,
    baseline_floor_per_min: float,
) -> dict:
    """Segment the T=0 session. Returns bursts as print-index intervals, so the
    output shape matches Arm A exactly and the two are directly comparable.

    Order of operations (config.arm_b.order_of_operations): threshold with
    hysteresis, THEN merge gaps, THEN drop short bursts -- merging first so a
    real burst broken by one sub-threshold grid point is not destroyed by the
    dwell floor.
    """
    ts = np.asarray(t0_ts, dtype=np.int64)
    n = ts.size
    empty = {
        "bursts": [], "grid_ns": np.zeros(0, dtype=np.int64), "z": np.zeros(0),
        "rate_t0": np.zeros(0), "baseline_at_grid": np.zeros(0),
        "on_threshold": float(np.log(on_multiplier)),
        "off_threshold": float(np.log(off_multiplier)),
        "n_candidates_raw": 0, "n_after_merge": 0, "n_dropped_short": 0,
        "n_dropped_no_prints": 0,
    }
    if n == 0:
        return empty

    end_ns = t0_start_ns + int(t0_span_minutes) * 60_000_000_000
    step = int(grid_seconds) * 1_000_000_000
    grid = np.arange(t0_start_ns, end_ns + step, step, dtype=np.int64)

    half = int(rate_window_seconds) * 1_000_000_000 // 2
    lo = np.searchsorted(ts, grid - half, side="left")
    hi = np.searchsorted(ts, grid + half, side="left")
    rate_t0 = (hi - lo) / (rate_window_seconds / 60.0)  # prints per minute

    minute_of = np.clip(
        (grid - t0_start_ns) // 60_000_000_000, 0, t0_span_minutes - 1
    ).astype(np.int64)
    base_at_grid = baseline["rate_floored"][minute_of]

    z = np.log(rate_t0 + _EPS) - np.log(
        np.maximum(base_at_grid, baseline_floor_per_min) + _EPS
    )

    on_t, off_t = float(np.log(on_multiplier)), float(np.log(off_multiplier))
    state = _hysteresis(z, on_t, off_t)
    raw = _runs(state)
    n_raw = len(raw)

    # merge, then drop-short, both in grid time
    merged: list[list[int]] = []
    for a, b in raw:
        if merged and (grid[a] - grid[merged[-1][1]]) / 1e9 < merge_gap_seconds:
            merged[-1][1] = b
        else:
            merged.append([a, b])
    n_merged = len(merged)

    bursts, n_short, n_noprint = [], 0, 0
    for a, b in merged:
        s_ns, e_ns = int(grid[a]), int(grid[b])
        if (e_ns - s_ns) / 1e9 < min_dwell_seconds:
            n_short += 1
            continue
        i0 = int(np.searchsorted(ts, s_ns, side="left"))
        i1 = int(np.searchsorted(ts, e_ns, side="right")) - 1
        if i1 < i0:
            n_noprint += 1
            continue
        bursts.append({
            "start_idx": i0, "end_idx": i1,
            "start_ns": int(ts[i0]), "end_ns": int(ts[i1]),
            "grid_start_ns": s_ns, "grid_end_ns": e_ns,
        })

    return {
        "bursts": bursts, "grid_ns": grid, "z": z, "rate_t0": rate_t0,
        "baseline_at_grid": base_at_grid,
        "on_threshold": on_t, "off_threshold": off_t,
        "n_candidates_raw": n_raw, "n_after_merge": n_merged,
        "n_dropped_short": n_short, "n_dropped_no_prints": n_noprint,
    }


def _selftest() -> None:
    """Synthetic session: quiet, one dense burst, quiet. The burst must be found,
    its boundaries must bracket the dense region, and hysteresis must widen the
    interval relative to a single-threshold rule."""
    span_min = 960
    start = 0
    rng = np.random.default_rng(1)
    quiet_a = np.sort(rng.uniform(0, 300 * 60, 300))          # 1/min for 300 min
    dense = np.sort(rng.uniform(300 * 60, 320 * 60, 4000))    # 200/min for 20 min
    quiet_b = np.sort(rng.uniform(320 * 60, 960 * 60, 640))
    ts = (np.concatenate([quiet_a, dense, quiet_b]) * 1e9).astype(np.int64)

    flank = {
        o: {"ts": (np.sort(rng.uniform(0, 960 * 60, 900)) * 1e9).astype(np.int64),
            "start_ns": 0, "span_minutes": span_min, "collected": True}
        for o in (-3, -2, -1)
    }
    base = build_baseline(flank, span_min, 15, 0.05)
    assert base["label"] == "defined", base["label"]

    out = arm_b_segment(
        ts, start, span_min, base, grid_seconds=10, rate_window_seconds=60,
        on_multiplier=4.0, off_multiplier=2.0, min_dwell_seconds=60,
        merge_gap_seconds=120, baseline_floor_per_min=0.05,
    )
    # The dense region must be found as exactly one burst whose boundaries
    # bracket it. Additional bursts elsewhere are NOT a failure: at a 1/min
    # baseline a Poisson clump of 4 prints in a 60 s window is a genuine 4x
    # crossing, so a thin baseline legitimately yields small extra bursts. That
    # behaviour is what the sensitivity grid and chart 07 exist to expose.
    hits = [
        b for b in out["bursts"]
        if b["end_ns"] / 1e9 / 60 >= 300 and b["start_ns"] / 1e9 / 60 <= 320
    ]
    assert len(hits) == 1, f"dense region should be one burst, got {len(hits)}"
    b = hits[0]
    s, e = b["start_ns"] / 1e9 / 60, b["end_ns"] / 1e9 / 60
    assert 298 <= s <= 301, s
    assert 319 <= e <= 322, e
    # and it must carry the bulk of the prints
    n_in = b["end_idx"] - b["start_idx"] + 1
    assert n_in > 0.9 * 4000, n_in

    # uncollected flanking sessions => baseline_undefined
    flank_none = {o: dict(v, collected=False) for o, v in flank.items()}
    assert build_baseline(flank_none, span_min, 15, 0.05)["label"] == "baseline_undefined"

    # hysteresis: off < on must produce an interval at least as wide as on == off
    tight = arm_b_segment(
        ts, start, span_min, base, grid_seconds=10, rate_window_seconds=60,
        on_multiplier=4.0, off_multiplier=4.0, min_dwell_seconds=60,
        merge_gap_seconds=120, baseline_floor_per_min=0.05,
    )
    w_h = b["end_ns"] - b["start_ns"]
    w_t = tight["bursts"][0]["end_ns"] - tight["bursts"][0]["start_ns"]
    assert w_h >= w_t, (w_h, w_t)
    print("arm_b selftest OK (burst located, baseline labels, hysteresis widening)")


if __name__ == "__main__":
    _selftest()
