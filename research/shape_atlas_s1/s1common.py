"""
Shape atlas S1 -- shared plumbing. Exploratory, hindsight used by design; nothing here is a tested result.

Brief: prompts/shape_atlas_s1.md. Config: config/shape_atlas_s1.json (reproducibility only).

Measurement reuses the programme's instrument unchanged: Brief 1's research/attention_excursion_b1/
(tick reading, session clock, equal-volume buckets via instruments.bucketize) through b2's b2common.
This module adds one code path that every S1 path goes through -- real or null:

    path_pipeline(lp0, steps, idx)  re-integrate `steps` under the index `idx` from lp0, then compute
                                    the components (batch form of instruments.components) and the
                                    G-point resampled sigma-normalised path.
    real:  steps = the path's own bucket log returns, idx = the identity
    null:  steps = those returns demeaned,            idx = draws with replacement

so the section 9 identity test (a real path through the null pipeline with the identity index and no
demeaning) checks the null's wiring against the exact function the real paths use.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import pathlib
import sys

import numpy as np

_B2 = pathlib.Path(__file__).resolve().parents[1] / "attention_excursion_b2"
if str(_B2) not in sys.path:
    sys.path.insert(0, str(_B2))
import b2common as B2  # noqa: E402

C1, I = B2.C1, B2.I
REPO = B2.REPO
CFG = "config/shape_atlas_s1.json"
OUT = "results/shape_atlas/s1"
ART = f"{OUT}/artifacts"
CHARTS = f"{OUT}/charts"
NS = B2.NS
VIEW_CODE = {"post": 0, "runup": 1, "whole_day": 2}
TYPES = ["runaway", "burst", "slow_climb", "exhausted", "fade", "chop"]
TIE_TOL = math.log1p(1e-9)


def load_cfg() -> dict:
    with open(REPO / CFG, encoding="utf-8") as f:
        return json.load(f)


def cfg_hash() -> str:
    return hashlib.sha256((REPO / CFG).read_bytes().replace(b"\r\n", b"\n")).hexdigest()[:12]


def art(name: str) -> pathlib.Path:
    p = REPO / ART / name
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def chart_path(name: str) -> pathlib.Path:
    p = REPO / CHARTS / name
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def src(key: str) -> pathlib.Path:
    return REPO / load_cfg()["sources"][key]


def write_json(name: str, obj) -> None:
    C1.write_json(f"{ART}/{name}", obj)


def read_json(name: str) -> dict:
    return json.load(open(art(name), encoding="utf-8"))


# ------------------------------------------------------------------ the one path pipeline

def comps_batch(lp: np.ndarray) -> dict:
    """instruments.components (Brief 1, A2.1 RV scale, A2.3 tie rule) for M paths at once.
    lp: (M, N + 1) log prices, element 0 the view's start. Returns arrays of length M."""
    lp = np.atleast_2d(np.asarray(lp, dtype=np.float64))
    M, N1 = lp.shape
    N = N1 - 1
    r = np.diff(lp, axis=1)
    rv = np.sum(r * r, axis=1)
    sp = np.sqrt(rv)
    top = lp.max(axis=1)
    tied = lp >= (top - TIE_TOL)[:, None]
    i_pk = tied.argmax(axis=1)
    last_tied = N - np.argmax(tied[:, ::-1], axis=1)
    run_max = np.maximum.accumulate(lp, axis=1)
    before = np.arange(N1)[None, :] <= i_pk[:, None]
    dip = np.where(before, run_max - lp, 0.0).max(axis=1)
    ar = np.arange(M)
    rise = lp[ar, i_pk] - lp[:, 0]
    fall = lp[ar, i_pk] - lp[:, N]
    term = lp[:, N] - lp[:, 0]
    ok = np.isfinite(sp) & (sp > 0)
    div = np.where(ok, sp, np.nan)
    return {"i_peak": i_pk, "u_peak": i_pk / N, "sigma_path": sp, "sigma_b": sp / math.sqrt(N),
            "rise_s": rise / div, "fall_s": fall / div, "dip_before_peak_s": dip / div, "terminal_s": term / div,
            "rise_log": rise, "fall_log": fall, "terminal_log": term, "peak_tied": tied.sum(axis=1) > 1,
            "peak_tie_span_u": (last_tied - i_pk) / N, "sigma_zero": ~ok,
            "rise_bp": np.expm1(rise) * 1e4, "fall_bp": (np.exp(rise) - np.exp(-fall + rise)) * 1e4}


def resample(lp: np.ndarray, sigma: np.ndarray, G: int) -> np.ndarray:
    """(M, N + 1) log paths -> (M, G) heights (log p - log p(0)) / sigma at u_g = (g + 1) / G, linear
    interpolation on the path's own volume clock u = i / N. NaN rows where sigma is zero."""
    lp = np.atleast_2d(lp)
    N = lp.shape[1] - 1
    pos = (np.arange(G) + 1) / G * N
    i0 = np.minimum(np.floor(pos).astype(int), N - 1)
    w = pos - i0
    h = (lp - lp[:, :1]) / np.where(sigma > 0, sigma, np.nan)[:, None]
    out = h[:, i0] * (1.0 - w) + h[:, i0 + 1] * w
    assert out.shape[1] == G, "resampled path does not have G points"
    return out


def resample_levels(y: np.ndarray, G: int) -> np.ndarray:
    """(M, N + 1) values on u = i / N -> (M, G) at u_g = (g + 1) / G, linear interpolation, no rescaling
    (the prior-close axis)."""
    y = np.atleast_2d(np.asarray(y, dtype=np.float64))
    N = y.shape[1] - 1
    pos = (np.arange(G) + 1) / G * N
    i0 = np.minimum(np.floor(pos).astype(int), N - 1)
    w = pos - i0
    out = y[:, i0] * (1.0 - w) + y[:, i0 + 1] * w
    assert out.shape[1] == G, "resampled path does not have G points"
    return out


def reintegrate(lp0: float, steps: np.ndarray, idx: np.ndarray) -> np.ndarray:
    idx = np.atleast_2d(idx)
    return np.concatenate([np.full((idx.shape[0], 1), lp0), lp0 + np.cumsum(steps[idx], axis=1)], axis=1)


def path_pipeline(lp0: float, steps: np.ndarray, idx: np.ndarray, G: int) -> tuple[np.ndarray, dict, np.ndarray]:
    paths = reintegrate(lp0, steps, idx)
    c = comps_batch(paths)
    return paths, c, resample(paths, c["sigma_path"], G)


def real_pipeline(lp: np.ndarray, G: int):
    lp = np.asarray(lp, dtype=np.float64)
    return path_pipeline(float(lp[0]), np.diff(lp), np.arange(lp.size - 1)[None, :], G)


def null_pipeline(lp: np.ndarray, idx: np.ndarray, G: int, demean: bool = True):
    lp = np.asarray(lp, dtype=np.float64)
    r = np.diff(lp)
    return path_pipeline(float(lp[0]), r - r.mean() if demean else r, idx, G)


def null_index(cfg: dict, event_index: int, view: str, N: int, n_draws: int) -> np.ndarray:
    """The event's null draw indices; row d is the same draw whatever n_draws is (row-by-row stream)."""
    rng = np.random.default_rng([cfg["null"]["seed"], int(event_index), VIEW_CODE[view], int(N)])
    return rng.integers(0, N, size=(n_draws, N))


def identity_test(lp: np.ndarray, G: int) -> bool:
    """Section 9: a real path through the null pipeline with the identity index and no demeaning gives
    output identical to the real pipeline."""
    a = real_pipeline(lp, G)
    b = null_pipeline(lp, np.arange(len(lp) - 1)[None, :], G, demean=False)
    same = np.array_equal(a[0], b[0]) and np.array_equal(a[2], b[2], equal_nan=True)
    return bool(same and all(np.array_equal(a[1][k], b[1][k], equal_nan=True) for k in a[1]))


# ------------------------------------------------------------------ percentiles and theory types

def pct_vs(null: np.ndarray, x: float) -> float:
    """Mid-rank percentile of x among the null draws (0..100)."""
    null = np.asarray(null, dtype=float)
    return float(100.0 * ((null < x).sum() + 0.5 * (null == x).sum()) / null.size)


def pct_leave_one_out(v: np.ndarray) -> np.ndarray:
    """Each draw's mid-rank percentile among the other draws of the same event."""
    v = np.asarray(v, dtype=float)
    less = (v[None, :] < v[:, None]).sum(axis=1)
    eq = (v[None, :] == v[:, None]).sum(axis=1) - 1
    return 100.0 * (less + 0.5 * eq) / (v.size - 1)


def theory_type(rise_pct, fall_pct, u_peak) -> np.ndarray:
    """Section 3, first match wins: runaway, burst, slow_climb, exhausted, fade, chop."""
    rp, fp, u = (np.asarray(x, dtype=float) for x in (rise_pct, fall_pct, u_peak))
    out = np.full(rp.shape, "chop", dtype=object)
    done = np.zeros(rp.shape, dtype=bool)
    for name, m in (("runaway", (rp >= 90) & (u >= 0.9)), ("burst", (rp >= 90) & (u < 0.5)),
                    ("slow_climb", (rp >= 90) & (u >= 0.5) & (u < 0.9)), ("exhausted", (u < 0.05) & (rp < 50)),
                    ("fade", fp >= 90)):
        sel = m & ~done
        out[sel] = name
        done |= sel
    out[~(np.isfinite(rp) & np.isfinite(u))] = None
    return out


def price_tier(p, cfg: dict):
    t = cfg["theory_types"]
    idx = np.searchsorted(np.asarray(t["price_tier_edges_usd"]), np.asarray(p, dtype=float), side="right")
    return np.asarray(t["price_tier_labels"], dtype=object)[np.clip(idx, 0, 3)]
