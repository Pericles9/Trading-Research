"""
Attention and the excursion -- Brief 2 shared plumbing.

Brief: prompts/attention_excursion_b2.md. Config: config/attention_excursion_b2.json (Brief 1's frozen
config carried unchanged, plus `brief2_diff` -- the section 1 rulings R1-R5 -- and `brief2`, this brief's
own task parameters).

Everything that measures is Brief 1's code, imported unchanged from research/attention_excursion_b1/:
tick reading, the session clock and segments, the D26 collapse, the one-sided kernel, the excursion
components, the attention quantities and their causality and segment assertions. This module holds
only b2's paths and config, the R1 ladder extent, and the R3 window rule.
"""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import sys

import numpy as np

_B1 = pathlib.Path(__file__).resolve().parents[1] / "attention_excursion_b1"
if str(_B1) not in sys.path:
    sys.path.insert(0, str(_B1))
import attention as A  # noqa: E402,F401  (Brief 1, unchanged)
import common as C1  # noqa: E402  (Brief 1, unchanged)
import instruments as I  # noqa: E402  (Brief 1, unchanged)

REPO = C1.REPO
CFG = "config/attention_excursion_b2.json"
OUT = "results/attention_excursion/b2"
ART = f"{OUT}/artifacts"
CHARTS = f"{OUT}/charts"
B1_ART = C1.ART
NS = C1.NS
MIN_NS = C1.MIN_NS
WINDOW_MSG = "competition window leaves its clock segment"


def load_cfg() -> dict:
    with open(REPO / CFG, encoding="utf-8") as f:
        return json.load(f)


def cfg_hash() -> str:
    b = (REPO / CFG).read_bytes().replace(b"\r\n", b"\n")
    return hashlib.sha256(b).hexdigest()[:12]


def art(name: str) -> pathlib.Path:
    p = REPO / ART / name
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def b1_art(name: str) -> pathlib.Path:
    return REPO / B1_ART / name


def chart_path(task: str, name: str) -> pathlib.Path:
    p = REPO / CHARTS / task / name
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def write_json(name: str, obj) -> None:
    C1.write_json(f"{ART}/{name}", obj)


def read_json(name: str) -> dict:
    return json.load(open(art(name), encoding="utf-8"))


def assert_int64(df, col: str = "tau_ns") -> None:
    """Section 7: tau_ns is int64 in every artifact (Brief 1 found it drifting to float64 twice)."""
    if col in df:
        assert str(df[col].dtype) in ("Int64", "int64"), f"{col} is {df[col].dtype}, not int64"


# ------------------------------------------------------------------ R1: the ladder's extent

def a2_ladder_r1(ct: np.ndarray, tau_ns: int, anchor_ns: int, n_min: int, floor_coef: float, k_max: int,
                 min_half_window_ns: int = 10_000_000) -> tuple[list[dict], int | None]:
    """Brief 2 R1 (Cooper's exact-count cutoff): rungs k = 0, 1, ... down to and including the first k
    whose whole window [tau - round(W_k), tau] holds fewer than 2 x n_min collapsed prints -- the
    windows are nested, so no finer rung can reach n_min on both halves. Rungs 0 and 1 always.

    The rungs themselves come from Brief 1's instruments.a2_count_ladder, unchanged; this only sets its
    k_max. Returns (ladder, cutoff_k); cutoff_k is None when the 10 ms floor or k_max ends it first."""
    H = tau_ns - anchor_ns
    hi = int(np.searchsorted(ct, tau_ns, side="right"))
    cutoff = None
    for k in range(k_max + 1):
        W = H / (2.0 ** k)
        if W / 2.0 < min_half_window_ns:
            break
        a = tau_ns - int(round(W))
        if hi - int(np.searchsorted(ct, a, side="left")) < 2 * n_min:
            cutoff = k
            break
    k_gen = k_max if cutoff is None else max(cutoff, 1)
    lad = I.a2_count_ladder(ct, tau_ns, anchor_ns, n_min, floor_coef, k_gen, sequential=False,
                            min_half_window_ns=min_half_window_ns)
    if cutoff is not None and lad:
        last = lad[max(cutoff, 0)] if cutoff < len(lad) else lad[-1]
        assert last["n_recent"] + last["n_older"] < 2 * n_min, "R1 cutoff rung is not below 2 x n_min"
        assert all(not x["valid"] for x in lad if x["k"] >= cutoff), "R1: a rung at or past the cutoff is valid"
    return lad, cutoff


# ------------------------------------------------------------------ R3: the competition window rule

def seg_bounds(date: str) -> tuple[np.ndarray, int, int, int, int]:
    """[open, open + 60 s, close, close + 60 s] for searchsorted -> index into C1.SEGMENTS, plus
    04:00, 20:00, open, close for the date (XNYS calendar, early closes included)."""
    op, cl = C1.rth_bounds_ns(date)
    b = np.array([op, op + MIN_NS, cl, cl + MIN_NS], dtype=np.int64)
    return b, C1.et_ns(date, "04:00:00"), C1.et_ns(date, "20:00:00"), op, cl


def window_valid(t: np.ndarray, W: int, bounds: np.ndarray, t0400: int, t2000: int) -> np.ndarray:
    """R3: [t - W, t + W] inside one clock segment and free of both cross minutes. The segments are
    contiguous intervals, so both ends in the same non-cross segment means the whole window is; the
    premarket starts at 04:00 and after hours end at 20:00."""
    t = np.asarray(t, dtype=np.int64)
    lo, hi = np.searchsorted(bounds, t - W, "right"), np.searchsorted(bounds, t + W, "right")
    return (lo == hi) & (lo != 1) & (lo != 3) & (t - W >= t0400) & (t + W <= t2000)


def assert_windows(t: np.ndarray, W: int, bounds: np.ndarray, t0400: int, t2000: int) -> None:
    """Escalation row 3 for the competition windows: every retained window re-checked; raises."""
    t = np.asarray(t, dtype=np.int64)
    if t.size == 0:
        return
    lo = np.searchsorted(bounds, t - W, "right")
    hi = np.searchsorted(bounds, t + W, "right")
    mid = np.searchsorted(bounds, t, "right")
    bad = (lo != hi) | (lo != mid) | np.isin(lo, (1, 3)) | (t - W < t0400) | (t + W > t2000)
    for a, b in ((bounds[0], bounds[1]), (bounds[2], bounds[3])):        # no cross minute inside
        bad |= (t - W < b) & (t + W >= a)
    if bad.any():
        raise AssertionError(f"{WINDOW_MSG}: {int(bad.sum())} window(s), first at t={int(t[bad][0])}, W={W}")


def window_test() -> dict:
    """Section 7: the competition-window assertion must raise on a straddling window and on a window
    holding a cross minute, and pass a window inside one segment."""
    d = "2024-03-15"
    bounds, t0400, t2000, op, cl = seg_bounds(d)
    W = 5 * MIN_NS
    out = {}
    for name, t in {"straddles_open": op - 2 * MIN_NS, "holds_close_cross_minute": cl + 30 * NS,
                    "straddles_0400": t0400 + MIN_NS}.items():
        try:
            assert_windows(np.array([t]), W, bounds, t0400, t2000)
            out[name] = "DID NOT RAISE"
        except AssertionError as e:
            out[name] = "raised" if WINDOW_MSG in str(e) else f"raised other: {e}"
    ok_t = np.array([op + 60 * MIN_NS])
    assert window_valid(ok_t, W, bounds, t0400, t2000).all()
    assert_windows(ok_t, W, bounds, t0400, t2000)
    out["inside_regular_does_not_raise"] = "ok"
    out["passes"] = all(v in ("raised", "ok") for v in out.values())
    return out


def octave(age_s):
    return np.floor(np.log2(np.asarray(age_s, dtype=float))).astype(int)


def price_tier(p, cfg: dict):
    r4 = cfg["brief2_diff"]["R4"]["price_tier"]
    idx = np.searchsorted(np.asarray(r4["edges_usd"]), np.asarray(p, dtype=float), side="right")
    lab = np.asarray(r4["labels"], dtype=object)
    out = lab[np.clip(idx, 0, len(lab) - 1)]
    out[~np.isfinite(np.asarray(p, dtype=float))] = None
    return out


def jump_band(x, cfg: dict):
    r4 = cfg["brief2_diff"]["R4"]["jump_share_band"]
    x = np.asarray(x, dtype=float)
    idx = np.searchsorted(np.asarray(r4["edges"]), x, side="left")      # (a, b] bands; <= 0 is band 0
    lab = np.asarray(r4["labels"], dtype=object)
    out = lab[np.clip(idx, 0, len(lab) - 1)]
    out[~np.isfinite(x)] = None
    return out


def cpu_workers() -> int:
    return max(1, min(10, (os.cpu_count() or 2) - 2))
