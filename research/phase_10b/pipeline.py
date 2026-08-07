"""
Phase 10b shared pipeline — used by T2 (synthetic controls), T3 (Allan vs matched
null) and T4 (time-rescaling). The control harness runs THIS code, not a parallel
implementation, or the control tests nothing.

SPARSE ALLAN. The ladder reaches 2^-20 s = 0.954 us. On a 57,600 s session that is
6.0e10 counting windows — a dense bincount cannot be allocated. Almost every window
is empty, so the estimator is rewritten over occupied bins only:

    A(T) = E[(N_{i+1} - N_i)^2] / (2 E[N])

    sum_i (N_{i+1}-N_i)^2  =  2*S2 - N_first^2 - N_last^2 - 2*P
      S2 = sum of N_i^2 over occupied bins
      P  = sum of N_i * N_{i+1} over ADJACENT occupied bin pairs
    E[N] = n_prints / n_windows

Both S2 and P come from the occupied bins alone, so the whole curve is O(n) per
rung regardless of how many windows the rung implies. Verified against a dense
reference in `_selftest`.

Fano uses the same sparse moments: Var = S2/n_win - mean^2.
"""
from __future__ import annotations

import numpy as np

__all__ = ["allan_fano_sparse", "allan_curve", "kernel_intensity", "simulate_inhomogeneous",
           "simulate_homogeneous", "simulate_cluster", "rescale_ks", "quantize"]

_NS = 1_000_000_000


def quantize(t_s: np.ndarray, resolution_ns: float) -> np.ndarray:
    """Snap continuous times (seconds) onto the archive's timestamp grid."""
    return np.round(np.asarray(t_s) * _NS / resolution_ns) * resolution_ns / _NS


def allan_fano_sparse(t_s: np.ndarray, start_s: float, end_s: float, T: float,
                      min_pairs: int) -> dict | None:
    """Allan and Fano factors at counting-window duration T, sparse formulation."""
    span = end_s - start_s
    n_win = int(np.floor(span / T))
    if n_win < 2:
        return None
    n_pairs = n_win - 1
    t = np.asarray(t_s, dtype=np.float64)
    b = np.floor((t - start_s) / T).astype(np.int64)
    b = b[(b >= 0) & (b < n_win)]
    n = b.size
    if n == 0:
        return None
    # b is non-decreasing (t sorted) -> run-length encode in O(n), no sort needed
    if n == 1:
        ub, cnt = b, np.array([1], dtype=np.int64)
    else:
        starts = np.flatnonzero(np.concatenate(([True], b[1:] != b[:-1])))
        ub = b[starts]
        cnt = np.diff(np.concatenate((starts, [n]))).astype(np.int64)
    c = cnt.astype(np.float64)
    S2 = float((c * c).sum())
    adj = np.flatnonzero(np.diff(ub) == 1)
    P = float((c[adj] * c[adj + 1]).sum()) if adj.size else 0.0
    n_first = float(c[0]) if ub[0] == 0 else 0.0
    n_last = float(c[-1]) if ub[-1] == n_win - 1 else 0.0
    ssd = 2.0 * S2 - n_first ** 2 - n_last ** 2 - 2.0 * P
    mean = n / n_win
    if mean <= 0:
        return None
    allan = (ssd / n_pairs) / (2.0 * mean)
    var = S2 / n_win - mean ** 2
    return {"T": float(T), "n_windows": int(n_win), "n_pairs": int(n_pairs),
            "n_prints_in_window": int(n), "mean_count": float(mean),
            "allan": float(allan), "fano": float(var / mean),
            "eligible": bool(n_pairs >= min_pairs)}


def allan_curve(t_s, start_s, end_s, ladder, min_pairs) -> list[dict]:
    out = []
    for T in ladder:
        r = allan_fano_sparse(t_s, start_s, end_s, T, min_pairs)
        if r is not None:
            out.append(r)
    return out


# ------------------------------------------------------------------ intensity
def kernel_intensity(t_fit_s: np.ndarray, grid_s: np.ndarray, h: float,
                     truncate: float = 4.0) -> np.ndarray:
    """Gaussian kernel intensity on `grid_s`, fitted from arrivals `t_fit_s`.

    Truncated at `truncate` bandwidths and evaluated by binned convolution so it
    is O(G log G) rather than O(n*G) — the grid is uniform, so a kernel applied
    to the arrival histogram is exact up to the bin width.
    """
    g = np.asarray(grid_s, dtype=np.float64)
    if g.size < 2 or t_fit_s.size == 0:
        return np.zeros(g.size)
    dx = float(g[1] - g[0])
    counts = np.histogram(t_fit_s, bins=np.concatenate((g - dx / 2, [g[-1] + dx / 2])))[0]
    half = max(1, int(np.ceil(truncate * h / dx)))
    k = np.exp(-0.5 * (np.arange(-half, half + 1) * dx / h) ** 2)
    k /= k.sum() * dx
    return np.convolve(counts.astype(np.float64), k, mode="same")


def simulate_inhomogeneous(lam: np.ndarray, grid_s: np.ndarray, rng,
                           resolution_ns: float | None = None) -> np.ndarray:
    """Draw an inhomogeneous Poisson realization from a piecewise-constant rate.

    N ~ Poisson(integral), positions from the normalized cumulative — O(N log G),
    no thinning loop.
    """
    dx = float(grid_s[1] - grid_s[0])
    lam = np.maximum(np.asarray(lam, dtype=np.float64), 0.0)
    cdf = np.cumsum(lam * dx)
    total = float(cdf[-1])
    if total <= 0:
        return np.zeros(0)
    n = int(rng.poisson(total))
    if n == 0:
        return np.zeros(0)
    u = rng.random(n) * total
    idx = np.searchsorted(cdf, u)
    idx = np.clip(idx, 0, grid_s.size - 1)
    t = grid_s[idx] + (rng.random(n) - 0.5) * dx
    t.sort()
    if resolution_ns:
        t = quantize(t, resolution_ns)
        t.sort()
    return t


def simulate_homogeneous(rate: float, start_s: float, end_s: float, rng,
                         resolution_ns: float | None = None) -> np.ndarray:
    n = int(rng.poisson(rate * (end_s - start_s)))
    t = np.sort(rng.random(n) * (end_s - start_s) + start_s)
    if resolution_ns:
        t = quantize(t, resolution_ns)
        t.sort()
    return t


def simulate_cluster(background: np.ndarray, k: int, duration_s: float, rng,
                     resolution_ns: float | None = None) -> np.ndarray:
    """Each background point becomes a cluster of `k` prints spread over
    `duration_s` — a Neyman-Scott process with fixed cluster size."""
    if background.size == 0:
        return background
    off = rng.random((background.size, k)) * duration_s
    t = (background[:, None] + off).ravel()
    t.sort()
    if resolution_ns:
        t = quantize(t, resolution_ns)
        t.sort()
    return t


# ------------------------------------------------------------------ rescaling
def rescale_ks(t_s: np.ndarray, start_s: float, end_s: float, h: float,
               block_s: float, lambda_floor: float, grid_dx: float,
               rng=None) -> dict:
    """Time-rescaling KS against unit exponential, with lambda-hat fitted OUT OF
    SAMPLE on alternating fixed-width blocks.

    Returns both folds. `lambda_floor` is absolute (prints/s); the fraction of
    held-out time sitting at it is reported, because at small h the floor rather
    than the market sets the answer.
    """
    from scipy import stats as sps

    t = np.asarray(t_s, dtype=np.float64)
    span = end_s - start_s
    if t.size < 10 or span <= 0:
        return {"folds": [], "n": 0}
    grid = np.arange(start_s, end_s + grid_dx, grid_dx)
    blk = np.floor((grid - start_s) / block_s).astype(np.int64)
    tblk = np.floor((t - start_s) / block_s).astype(np.int64)

    out = []
    for parity in (0, 1):
        fit_mask_t = (tblk % 2) != parity          # fit on the OTHER parity
        eval_grid = (blk % 2) == parity
        if fit_mask_t.sum() < 10 or eval_grid.sum() < 10:
            out.append(None)
            continue
        lam = kernel_intensity(t[fit_mask_t], grid, h)
        lam_eval = np.where(eval_grid, lam, 0.0)
        floored = float((lam[eval_grid] < lambda_floor).mean())
        lam_eval = np.where(eval_grid, np.maximum(lam, lambda_floor), 0.0)
        # rescaled time: Lambda(t) = integral of lambda over held-out region only
        cum = np.concatenate(([0.0], np.cumsum(lam_eval * grid_dx)))
        te = t[(tblk % 2) == parity]
        if te.size < 10:
            out.append(None)
            continue
        gi = np.clip(np.searchsorted(grid, te), 0, grid.size - 1)
        lam_t = cum[gi]
        d = np.diff(np.sort(lam_t))
        d = d[d > 0]
        if d.size < 10:
            out.append(None)
            continue
        ks = sps.kstest(d, "expon", args=(0.0, 1.0))
        out.append({"fold": parity, "n_intervals": int(d.size),
                    "ks_stat": float(ks.statistic), "ks_pvalue": float(ks.pvalue),
                    "floored_time_fraction": floored,
                    "mean_rescaled_interval": float(d.mean())})
    return {"folds": out, "n": int(t.size)}


# ------------------------------------------------------------------ selftest
def _selftest() -> None:
    """Sparse Allan must equal a dense reference exactly, including edge bins."""
    rng = np.random.default_rng(0)
    for trial in range(50):
        n = int(rng.integers(50, 800))
        start, end = 0.0, 100.0
        t = np.sort(rng.random(n) * (end - start) + start)
        for T in (0.37, 1.0, 3.3, 12.5):
            got = allan_fano_sparse(t, start, end, T, 0)
            n_win = int(np.floor((end - start) / T))
            b = np.floor((t - start) / T).astype(np.int64)
            b = b[(b >= 0) & (b < n_win)]
            dense = np.bincount(b, minlength=n_win).astype(float)
            ref_allan = ((np.diff(dense) ** 2).mean()) / (2 * dense.mean())
            ref_fano = dense.var() / dense.mean()
            assert abs(got["allan"] - ref_allan) < 1e-9 * max(1, ref_allan), (
                trial, T, got["allan"], ref_allan)
            assert abs(got["fano"] - ref_fano) < 1e-9 * max(1, ref_fano), (
                trial, T, got["fano"], ref_fano)
    # homogeneous Poisson -> Allan and Fano both near 1
    rng = np.random.default_rng(1)
    t = simulate_homogeneous(50.0, 0.0, 2000.0, rng)
    r = allan_fano_sparse(t, 0.0, 2000.0, 1.0, 0)
    assert 0.85 < r["allan"] < 1.15, r["allan"]
    assert 0.85 < r["fano"] < 1.15, r["fano"]
    # a cluster process of fixed size k -> plateau near k below cluster spacing
    rng = np.random.default_rng(2)
    bg = simulate_homogeneous(5.0, 0.0, 4000.0, rng)
    tc = simulate_cluster(bg, 6, 1e-5, rng)
    r = allan_fano_sparse(tc, 0.0, 4000.0, 0.5, 0)
    assert 4.0 < r["allan"] < 8.0, r["allan"]
    print("pipeline selftest OK — sparse Allan == dense on 50x4 cases; "
          "Poisson->1; cluster k=6 plateau in [4,8]")


if __name__ == "__main__":
    _selftest()
