"""
Phase 10d -- burst assembly under a merge tolerance, a separator rule, and a run-length floor.

This module is the ONLY place 10d changes anything. Labelling, normalization, the window,
the histogram and the argmax-void threshold are 10c's and are read, never re-derived.

The assembly is a pure function of four arrays and four parameters:

    norm[i]  normalized log10 interval i          (float, may be non-finite)
    ok[i]    interval i cleared the data floor    (bool)
    ts[j]    aggregated print timestamps, len n+1 (int64 ns; interval i spans ts[i]..ts[i+1])
    thr      the argmax-void threshold            (float, normalized log10, typically negative)

    K          count tolerance   -- a separating run may hold at most K intervals
    d          depth tolerance   -- DECADES, ADDED to thr. Never multiplied: thr is a
                                    position on a normalized log axis and is negative, so
                                    multiplying tightens the tolerance as the factor grows,
                                    which is the exact inversion of intent (spec 3.1).
    sep        'hard_break' | 'bridgeable_count_only'
    min_prints applied to MERGED objects, never to raw runs

10c's rule is the (K=0, d=0, min_prints=2, sep='hard_break') cell exactly:
  - K=0 admits no separator, since two distinct runs are separated by at least one interval;
  - d=0 admits no separator, since a separator that cleared the floor is at or above thr by
    definition and `norm < thr + 0` is then false;
  - min_prints=2 is the true no-op: n_prints = n_intervals + 1 and n_intervals >= 1.

An ok=False interval is NEVER tested on its raw `norm` value under either separator rule.
That value was declared untrustworthy by the data floor. Doing so is escalation row 10d-R8.

Usage: imported. No side effects, no I/O, no config reads -- callers pass parameters in.
"""
from __future__ import annotations

import numpy as np

SEP_HARD_BREAK = "hard_break"
SEP_BRIDGEABLE = "bridgeable_count_only"
SEP_RULES = (SEP_HARD_BREAK, SEP_BRIDGEABLE)


def label_intervals(norm: np.ndarray, ok: np.ndarray, thr: float) -> np.ndarray:
    """10c's labelling, verbatim: research/phase_10c/s1_t1_subbursts.py

        inb = ok & np.isfinite(norm) & (norm < thr)

    Strict `<`. Not re-derived, not relaxed.
    """
    return np.asarray(ok, dtype=bool) & np.isfinite(norm) & (np.asarray(norm) < thr)


def raw_runs(inb: np.ndarray) -> list[tuple[int, int]]:
    """Maximal runs of strictly consecutive True indices, as inclusive (start, end) pairs.

    This is 10c's `np.split(idx, np.flatnonzero(np.diff(idx) != 1) + 1)` in closed form.
    """
    idx = np.flatnonzero(inb)
    if idx.size == 0:
        return []
    cuts = np.flatnonzero(np.diff(idx) != 1) + 1
    return [(int(r[0]), int(r[-1])) for r in np.split(idx, cuts)]


def _separator_admissible(lo: int, hi: int, norm: np.ndarray, ok: np.ndarray,
                          thr: float, d: float, sep: str) -> bool:
    """Can the separating run of indices [lo, hi] (inclusive) be bridged?

    Every separating interval must pass. Two interval kinds, handled differently:
      - cleared the floor  -> depth test, `norm < thr + d`
      - failed the floor   -> no trustworthy normalized value exists.
          hard_break            : never bridgeable
          bridgeable_count_only : exempt from the depth test (it already counted toward K)
    """
    if lo > hi:
        return True
    seg_ok = ok[lo:hi + 1]
    seg_norm = norm[lo:hi + 1]
    bad = ~seg_ok | ~np.isfinite(seg_norm)

    if bad.any():
        if sep == SEP_HARD_BREAK:
            return False
        # bridgeable_count_only: the floor-failing intervals are exempt from the depth
        # test. Their raw norm value is never consulted -- see 10d-R8.
    good = ~bad
    if good.any() and not np.all(seg_norm[good] < thr + d):
        return False
    return True


def assemble(norm: np.ndarray, ok: np.ndarray, ts: np.ndarray, thr: float,
             K: int, d: float, min_prints: int, sep: str,
             inb: np.ndarray | None = None) -> dict:
    """Assemble merged sub-burst objects. Returns arrays keyed by object.

    Objects are contiguous index spans. A merged object's span INCLUDES the separators it
    bridged -- that is what merging means, and its duration therefore includes separator
    time. `n_intervals_burst` carries the sub-threshold count separately so the n_prints
    composition analysis (T5b) can tell promotion from deletion.
    """
    if sep not in SEP_RULES:
        raise ValueError(f"unknown separator rule: {sep!r}")
    if K < 0:
        raise ValueError("K must be >= 0")
    if min_prints < 2:
        raise ValueError("min_prints < 2 is below the structural minimum (n_prints = n_intervals + 1)")

    norm = np.asarray(norm, dtype=float)
    ok = np.asarray(ok, dtype=bool)
    ts = np.asarray(ts)
    if inb is None:
        inb = label_intervals(norm, ok, thr)

    runs = raw_runs(inb)
    if not runs:
        return _empty_result()

    # ---- merge, left to right, transitively
    merged: list[dict] = []
    cur_s, cur_e = runs[0]
    cur_burst = cur_e - cur_s + 1
    cur_merges = 0
    for nxt_s, nxt_e in runs[1:]:
        gap_lo, gap_hi = cur_e + 1, nxt_s - 1
        gap_n = gap_hi - gap_lo + 1
        if gap_n <= K and _separator_admissible(gap_lo, gap_hi, norm, ok, thr, d, sep):
            cur_e = nxt_e
            cur_burst += nxt_e - nxt_s + 1
            cur_merges += 1
        else:
            merged.append({"start": cur_s, "end": cur_e, "burst": cur_burst, "merges": cur_merges})
            cur_s, cur_e = nxt_s, nxt_e
            cur_burst = nxt_e - nxt_s + 1
            cur_merges = 0
    merged.append({"start": cur_s, "end": cur_e, "burst": cur_burst, "merges": cur_merges})

    # ---- run-length floor, applied to MERGED objects
    start = np.array([m["start"] for m in merged], dtype=np.int64)
    end = np.array([m["end"] for m in merged], dtype=np.int64)
    n_int_total = end - start + 1
    n_prints = n_int_total + 1
    keep = n_prints >= min_prints

    return {
        "start_idx": start[keep],
        "end_idx": end[keep],
        "n_intervals_total": n_int_total[keep],
        "n_intervals_burst": np.array([m["burst"] for m in merged], dtype=np.int64)[keep],
        "n_prints": n_prints[keep],
        "n_merges": np.array([m["merges"] for m in merged], dtype=np.int64)[keep],
        "start_ns": ts[start[keep]],
        "end_ns": ts[end[keep] + 1],
        "duration_s": (ts[end[keep] + 1].astype(np.float64) - ts[start[keep]].astype(np.float64)) / 1e9,
        "n_objects": int(keep.sum()),
        "n_objects_before_floor": int(len(merged)),
        "n_deleted_by_floor": int((~keep).sum()),
    }


def _empty_result() -> dict:
    z_i = np.zeros(0, dtype=np.int64)
    return {"start_idx": z_i, "end_idx": z_i, "n_intervals_total": z_i,
            "n_intervals_burst": z_i, "n_prints": z_i, "n_merges": z_i,
            "start_ns": z_i, "end_ns": z_i, "duration_s": np.zeros(0),
            "n_objects": 0, "n_objects_before_floor": 0, "n_deleted_by_floor": 0}


def break_cause_census(inb: np.ndarray, norm: np.ndarray, ok: np.ndarray,
                       thr: float) -> dict:
    """T4c -- why is each run break there?

    Classifies the separating intervals between consecutive raw runs. Two causes:
      above_threshold : cleared the floor, but norm >= thr -- a real gap
      ok_false        : failed the data floor -- a data-quality artifact, not market behaviour

    Reported at interval level and at break level. A break counts as `ok_false_involved`
    if ANY of its separating intervals failed the floor, because under `hard_break` that
    alone makes the break unbridgeable regardless of the others.
    """
    runs = raw_runs(inb)
    n_breaks = max(len(runs) - 1, 0)
    iv_above = iv_okfalse = 0
    br_above_only = br_okfalse_involved = 0
    for (a_s, a_e), (b_s, b_e) in zip(runs[:-1], runs[1:]):
        lo, hi = a_e + 1, b_s - 1
        seg_ok = ok[lo:hi + 1]
        seg_norm = norm[lo:hi + 1]
        bad = ~seg_ok | ~np.isfinite(seg_norm)
        iv_okfalse += int(bad.sum())
        iv_above += int((~bad).sum())
        if bad.any():
            br_okfalse_involved += 1
        else:
            br_above_only += 1
    return {
        "n_runs": len(runs),
        "n_breaks": n_breaks,
        "intervals_above_threshold": iv_above,
        "intervals_ok_false": iv_okfalse,
        "breaks_above_threshold_only": br_above_only,
        "breaks_ok_false_involved": br_okfalse_involved,
    }
