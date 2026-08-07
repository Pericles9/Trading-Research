"""
Phase 10b A10b.1 Change 1 -- the knee statistic.

Continuous piecewise-linear fit of log A(T) against log2 T over the ELIGIBLE
rungs, k = 1..knee_max_segments segments, breakpoints searched over rung
positions only, k selected by BIC.

This replaces the void departure-point statistic. A cluster process departs from
Poisson at the finest resolvable scale -- two points inside one cluster can be
arbitrarily close -- so a departure point measures the finest clustering present,
not the injected timescale. On real data it would land on the fragmentation scale
in every event. The injected timescale appears instead as the transition from the
rising segment to the plateau, which is what a knee measures, and which is the
same object v3's Allan/Fano gate reports.

Shared by T2 (controls) and T3 (real cohort). One implementation.
"""
from __future__ import annotations

import itertools

import numpy as np

__all__ = ["fit_piecewise", "MIN_SEG_RUNGS"]

MIN_SEG_RUNGS = 3   # a segment shorter than this is not a slope, it is two points


def _design(x: np.ndarray, bps: tuple[float, ...]) -> np.ndarray:
    """Continuous piecewise-linear basis: [1, x, (x-b1)+, (x-b2)+, ...]."""
    cols = [np.ones_like(x), x]
    for b in bps:
        cols.append(np.maximum(x - b, 0.0))
    return np.column_stack(cols)


def _rss(x, y, bps):
    X = _design(x, bps)
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    return float(((y - X @ beta) ** 2).sum()), beta


def fit_piecewise(T_s: np.ndarray, allan: np.ndarray, max_segments: int = 3) -> dict | None:
    """Returns the BIC-selected continuous piecewise-linear fit.

    x is log2 T (so a breakpoint is a rung position), y is natural-log Allan.
    BIC = n ln(RSS/n) + p ln n, with p = 2k: k slopes, one intercept, and k-1
    breakpoint locations.
    """
    m = np.isfinite(T_s) & np.isfinite(allan) & (allan > 0) & (T_s > 0)
    x, y = np.log2(np.asarray(T_s)[m]), np.log(np.asarray(allan)[m])
    o = np.argsort(x)
    x, y = x[o], y[o]
    n = x.size
    if n < 2 * MIN_SEG_RUNGS:
        return None

    fits = {}
    for k in range(1, max_segments + 1):
        need = k * MIN_SEG_RUNGS
        if n < need:
            continue
        best = None
        # breakpoints sit at rung positions; each segment keeps >= MIN_SEG_RUNGS rungs
        idxs = range(MIN_SEG_RUNGS, n - MIN_SEG_RUNGS + 1)
        for combo in itertools.combinations(idxs, k - 1):
            if any(combo[i + 1] - combo[i] < MIN_SEG_RUNGS for i in range(len(combo) - 1)):
                continue
            bps = tuple(x[i] for i in combo)
            r, beta = _rss(x, y, bps)
            if best is None or r < best[0]:
                best = (r, bps, beta, combo)
        if best is None:
            continue
        r, bps, beta, combo = best
        p = 2 * k
        bic = n * np.log(max(r, 1e-300) / n) + p * np.log(n)
        # segment slopes: cumulative sum of the hinge coefficients
        slopes = [float(beta[1])]
        for j in range(2, 2 + len(bps)):
            slopes.append(slopes[-1] + float(beta[j]))
        fits[k] = {"k": k, "rss": r, "bic": float(bic), "n_rungs": int(n),
                   "breakpoints_log2T": [float(b) for b in bps],
                   "breakpoints_T_s": [float(2.0 ** b) for b in bps],
                   "breakpoint_rung_index": [int(i) for i in combo],
                   "segment_slopes": slopes, "intercept": float(beta[0])}
    if not fits:
        return None
    sel = min(fits.values(), key=lambda f: f["bic"])
    return {"selected_k": sel["k"], "selected": sel,
            "delta_bic_vs_k1": float(fits[1]["bic"] - sel["bic"]) if 1 in fits else None,
            "bic_by_k": {str(k): f["bic"] for k, f in fits.items()},
            "x_is": "log2 T (rung position)", "y_is": "natural log Allan factor",
            "bic_formula": "n*ln(RSS/n) + p*ln(n), p = 2k",
            "min_segment_rungs": MIN_SEG_RUNGS}


def _selftest():
    """A known two-segment curve must be recovered at the injected breakpoint."""
    rng = np.random.default_rng(0)
    x = np.arange(-20, 13, dtype=float)
    for true_bp in (-8.0, -3.0, 4.0):
        y = np.where(x < true_bp, 0.9 * (x - true_bp), 0.0) * -1.0
        y = np.maximum(0.0, np.where(x < true_bp, 0.0, 0.0)) + np.where(
            x < true_bp, 0.8 * (x - true_bp), 0.0)
        yy = y + rng.normal(0, 0.01, x.size)
        f = fit_piecewise(2.0 ** x, np.exp(yy), 3)
        got = f["selected"]["breakpoints_T_s"]
        err = min(abs(np.log2(g) - true_bp) for g in got)
        assert err <= 1.0, (true_bp, got, err)
    print("knee selftest OK -- injected breakpoints recovered within 1 rung "
          "at log2 T = -8, -3, +4")


if __name__ == "__main__":
    _selftest()
