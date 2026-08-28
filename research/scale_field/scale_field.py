"""
Continuous scale-space of trade timing.

Two channels over one field in (time, kernel scale):

  channel 2  RATE      dL/dln s   L = ln( kernel-smoothed trade intensity )
  channel 1  INTERVAL  dm/dln s   m = kernel-weighted mean log10 inter-trade interval

Both derivatives are exact and analytic. There is no kernel grid in the method --
the scale axis is a continuum; the array of scales below is quadrature for plotting.

Two implementations:
  field_exact  O(|t_grid| x n_prints x n_scales).  Reference only. Used by the tests.
  field        O(n_grid) per scale via a Gaussian pyramid.  Use this on real events.

No dependency beyond numpy + scipy (D14).
"""
from __future__ import annotations
import numpy as np
from scipy.ndimage import gaussian_filter1d

LN10 = np.log(10.0)
SIGMA_POISSON_DECADES = np.sqrt(np.pi**2 / 6.0) / LN10   # 0.55696 -- sd of log10(Exp), any rate
EULER_GAMMA = 0.5772156649015329


# --------------------------------------------------------------------------- #
# input preparation
# --------------------------------------------------------------------------- #

def collapse_same_timestamp(ts_ns: np.ndarray) -> np.ndarray:
    """Reference tie variant (config/phase_10_v4.json). Consecutive prints sharing a
    timestamp collapse to one arrival, so every interval is strictly positive and the
    log transform is defined without an imputed value."""
    ts_ns = np.asarray(ts_ns, dtype=np.int64)
    if ts_ns.size and np.any(np.diff(ts_ns) < 0):
        raise ValueError("timestamps must be sorted ascending before collapsing")
    return np.unique(ts_ns)


NS = 1_000_000_000


def _assert_resolved(t_s: np.ndarray, dt_ns: np.ndarray) -> None:
    """float64 seconds must resolve the SMALLEST gap present, with headroom.

    This is not a theoretical concern, it is the failure this guard was written
    after. Epoch nanoseconds are ~1.6e18; as float64 SECONDS the ULP is 238 ns,
    while the archive's median timestamp resolution is 80.5 ns and its minimum is
    49 ns. Measured on ALXO_2020-08-05_31.58: 4 of 899 strictly-increasing unique
    timestamps went NON-POSITIVE under `ts/1e9`, and the worst gap error was 447 ns
    against a 954 ns scale floor -- the whole fine band would have been quantization
    noise wearing a plausible shape. Rebasing to an int64 origin first drops the
    worst error to 0.004 ns. Hence `origin_ns`, and hence this check: passing the
    wrong origin now fails loudly instead of returning numbers.
    """
    if t_s.size == 0 or dt_ns.size == 0:
        return
    ulp = float(np.spacing(float(np.abs(t_s).max())))
    finest = float(dt_ns.min()) / NS
    if ulp > finest / 8.0:
        raise ValueError(
            f"float64 seconds cannot resolve this tape: ULP {ulp * 1e9:.1f} ns vs "
            f"smallest gap {finest * 1e9:.1f} ns. Pass origin_ns (epoch-ns timestamps "
            f"must be rebased before the float conversion, not after)."
        )


def to_seconds(ts_ns: np.ndarray, origin_ns: int | None = None) -> tuple[np.ndarray, int]:
    """int64 epoch ns -> (float64 seconds measured from `origin_ns`, origin_ns).

    The rate channel and the interval channel MUST share one origin or their time
    axes are offset against each other. Default origin is the first timestamp.
    """
    ts_ns = np.asarray(ts_ns, dtype=np.int64)
    origin = int(ts_ns[0]) if origin_ns is None and ts_ns.size else int(origin_ns or 0)
    return (ts_ns - origin).astype(np.float64) / 1e9, origin


def intervals(ts_ns: np.ndarray, origin_ns: int = 0) -> tuple[np.ndarray, np.ndarray]:
    """-> (event_time_seconds, log10_interval).  Interval is attributed to its CLOSING
    print, so element i is the gap that ended at ts[i+1].

    Gaps are differenced in int64 BEFORE any float conversion, so the interval is
    exact regardless of the timestamps' magnitude. `origin_ns` rebases the returned
    time axis and must match the one used for the rate channel -- see `to_seconds`.
    It defaults to 0 (absolute epoch seconds), which is correct only for a tape whose
    timestamps are small; `_assert_resolved` raises rather than let that pass
    silently on real epoch-ns data.
    """
    ts_ns = np.asarray(ts_ns, dtype=np.int64)
    dt_ns = np.diff(ts_ns)
    if np.any(dt_ns <= 0):
        raise ValueError("non-positive interval: collapse ties first")
    t = (ts_ns[1:] - int(origin_ns)).astype(np.float64) / 1e9
    _assert_resolved(t, dt_ns)
    return t, np.log10(dt_ns.astype(np.float64) / 1e9)


# --------------------------------------------------------------------------- #
# reference implementation -- exact, slow, used by tests
# --------------------------------------------------------------------------- #

def field_exact(ts_s, ev_s, x, t_grid, scales, neff_min=8.0):
    """Direct pairwise evaluation. ts_s = all print times (rate channel);
    ev_s, x = interval-carrying times and their log10 intervals (interval channel)."""
    nT, nS = len(t_grid), len(scales)
    out = {k: np.full((nT, nS), np.nan) for k in
           ("m", "dm", "lograte", "dlograte", "n_eff")}
    for j, s in enumerate(scales):
        z = (t_grid[:, None] - ev_s[None, :]) / s
        w = np.exp(-0.5 * z * z)
        dw = w * (z * z)                                   # dw/dln s, unnormalised kernel
        B = w.sum(1)
        neff = np.divide(B * B, (w * w).sum(1), out=np.zeros_like(B), where=B > 0)
        out["n_eff"][:, j] = neff
        ok = neff >= neff_min
        if ok.any():
            Bo = B[ok]
            m = (w[ok] @ x) / Bo
            out["m"][ok, j] = m
            out["dm"][ok, j] = ((dw[ok] @ x) - m * dw[ok].sum(1)) / Bo

        zz = (t_grid[:, None] - ts_s[None, :]) / s
        g = np.exp(-0.5 * zz * zz) / (s * np.sqrt(2 * np.pi))
        lam = g.sum(1)
        good = lam > 0
        out["lograte"][good, j] = np.log(lam[good])
        out["dlograte"][good, j] = (g * (zz * zz - 1.0)).sum(1)[good] / lam[good]
    return out


# --------------------------------------------------------------------------- #
# production implementation -- Gaussian pyramid, O(n_grid) per scale
# --------------------------------------------------------------------------- #

def _bin(ts_s, ev_s, x, t0, dt, n):
    c = np.bincount(np.clip(((ts_s - t0) / dt).astype(np.int64), 0, n - 1), minlength=n).astype(float)
    idx = np.clip(((ev_s - t0) / dt).astype(np.int64), 0, n - 1)
    ce = np.bincount(idx, minlength=n).astype(float)
    sx = np.bincount(idx, weights=x, minlength=n).astype(float)
    return c, ce, sx


def field(ts_s, ev_s, x, t_grid, scales, neff_min=8.0, sigma_lo=8.0, edge_scales=4.0):
    """Same quantities as field_exact, via a Gaussian pyramid.

    ACCURACY (measured against field_exact, not asserted by hope -- see
    test_pyramid_matches_exact). Error is controlled by sigma in BINS, so it is
    largest in the first octave and wherever the pyramid has just decimated.
    At the defaults, worst-case error as a fraction of each field's own sd:
        lograte  0.11 fine / 0.05 coarse      m   0.04 fine / 0.06 coarse
        dlograte 0.49 fine / 0.12 coarse      dm  0.13 fine / 0.21 coarse
    dm is the noisiest -- it is a second derivative of a RATIO of two sparse
    binned quantities. If a result depends on dm at the finest octave, verify it
    on a subsample with field_exact rather than trusting this path.

    Scales are visited fine -> coarse. Smoothing accumulates in the arrays, so each
    step only applies the INCREMENTAL kernel sigma_eff = sqrt(sigma^2 - sigma_acc^2)
    (Gaussians compose in quadrature, and derivatives commute with convolution, so
    order=2 applied to an already-smoothed array is still the exact second derivative
    of the fully-smoothed signal). Before every 2x decimation the array is low-passed
    to >= 1 bin, which is what keeps subsampling from aliasing -- summing raw bins
    does not, and that error does not shrink as the base grid is refined.
    """
    scales = np.asarray(scales, float)
    order = np.argsort(scales)
    t0 = float(min(ts_s.min(), ev_s.min()))
    t1 = float(max(ts_s.max(), ev_s.max()))
    dt = scales.min() / sigma_lo
    n = int(np.ceil((t1 - t0) / dt)) + 1
    c, ce, sx = _bin(ts_s, ev_s, x, t0, dt, n)
    sacc = 0.0                                    # accumulated smoothing, current grid units
    G = dict(mode="constant", cval=0.0, truncate=4.0)

    def smooth(arr, target, acc):
        e2 = target * target - acc * acc
        return arr if e2 <= 1e-9 else gaussian_filter1d(arr, np.sqrt(e2), order=0, **G)

    nT, nS = len(t_grid), len(scales)
    out = {k: np.full((nT, nS), np.nan) for k in
           ("m", "dm", "lograte", "dlograte", "n_eff")}
    rt = np.sqrt(np.pi)

    for j in order:
        s = scales[j]
        while s / dt > 4 * sigma_lo and len(c) > 64:   # every 2 octaves; see ACCURACY note
            pre = 1.0                                     # low-pass to 1 bin before subsampling
            c, ce, sx = (smooth(a, pre, sacc) for a in (c, ce, sx))
            sacc = max(sacc, pre)
            # counts are EXTENSIVE: subsampling doubles the bin width, so the mass
            # per bin doubles. Dropping this factor silently halves n_eff per octave.
            c, ce, sx = 2 * c[::2].copy(), 2 * ce[::2].copy(), 2 * sx[::2].copy()
            dt *= 2; sacc /= 2.0
        sg = s / dt
        eff = np.sqrt(max(sg * sg - sacc * sacc, 1e-12))
        half = np.sqrt(max(sg * sg / 2.0 - sacc * sacc, 1e-12))
        c0 = gaussian_filter1d(c, eff, order=0, **G)
        c2 = gaussian_filter1d(c, eff, order=2, **G)
        e0 = gaussian_filter1d(ce, eff, order=0, **G)
        e2 = gaussian_filter1d(ce, eff, order=2, **G)
        eh = gaussian_filter1d(ce, half, order=0, **G)
        x0 = gaussian_filter1d(sx, eff, order=0, **G)
        x2 = gaussian_filter1d(sx, eff, order=2, **G)

        pos = e0 > 0
        m = np.divide(x0, e0, out=np.full_like(e0, np.nan), where=pos)
        dm = np.divide(sg * sg * (x2 - m * e2), e0, out=np.full_like(e0, np.nan), where=pos)
        neff = np.divide(2 * rt * sg * e0 * e0, eh, out=np.zeros_like(e0), where=eh > 0)
        bad = ~(neff >= neff_min)
        m = np.where(bad, np.nan, m); dm = np.where(bad, np.nan, dm)

        cpos = c0 > 0
        lr = np.where(cpos, np.log(np.divide(c0, dt, out=np.ones_like(c0), where=cpos)), np.nan)
        dlr = np.divide(sg * sg * c2, c0, out=np.full_like(c0, np.nan), where=cpos)

        gt = t0 + (np.arange(len(c0)) + 0.5) * dt
        edge = (t_grid > t0 + edge_scales * s) & (t_grid < t1 - edge_scales * s)
        for name, arr in (("m", m), ("dm", dm), ("lograte", lr),
                          ("dlograte", dlr), ("n_eff", neff)):
            v = np.interp(t_grid, gt, arr, left=np.nan, right=np.nan)
            out[name][:, j] = np.where(edge, v, np.nan)
    return out


# --------------------------------------------------------------------------- #
# reconciliation target: Allan factor (phase 10 v3 / 10b)
# --------------------------------------------------------------------------- #

def allan_factor(ts_s, T, t_start=None, t_end=None, min_windows=2):
    """A(T) = E[(N_{i+1}-N_i)^2] / (2 E[N]) over NON-OVERLAPPING windows of width T.
    Homogeneous Poisson -> 1 flat. Returns (A, n_adjacent_pairs).

    THE WINDOW ORIGIN IS AN ARGUMENT, NOT AN ASSUMPTION. Unset, windows tile
    [min(ts), max(ts)) -- the data's own support, which is what a synthetic tape
    wants and what the unit tests assert against. Phase 10 v3 tiled the D3 extended
    session [04:00 ET, post_end) instead, so empty stretches are real zeros rather
    than omissions (config/phase_10_v3.json gate.window_origin). Reconciling against
    v3 REQUIRES passing that window explicitly -- the origin, the span, and therefore
    every count depends on it. `min_windows` mirrors v3's min_windows_for_a_rung: a
    rung with fewer windows than this is dropped, not returned small.
    """
    ts_s = np.asarray(ts_s, dtype=np.float64)
    t0 = float(ts_s.min()) if t_start is None else float(t_start)
    t1 = float(ts_s.max()) if t_end is None else float(t_end)
    nb = int((t1 - t0) // T)
    if nb < max(2, int(min_windows)):
        return np.nan, 0
    idx = ((ts_s - t0) / T).astype(np.int64)
    idx = idx[(idx >= 0) & (idx < nb)]        # drop the partial trailing window; never clip into it
    N = np.bincount(idx, minlength=nb).astype(float)
    d = np.diff(N)
    mu = N.mean()
    return (np.nan, len(d)) if mu <= 0 else ((d * d).mean() / (2 * mu), len(d))
