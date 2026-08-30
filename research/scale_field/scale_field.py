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

# n_eff = 2*sqrt(pi)*s*lambda >= neff_min  =>  s >= NEFF_S_MIN_COEF / lambda.
# The fine band's real floor is arithmetic, not a config choice: at the median rth
# rate of 2.5 prints/s nothing below 903 ms is measurable at ANY output resolution.
NEFF_S_MIN_COEF = 8.0 / (2.0 * np.sqrt(np.pi))           # 2.2568


def s_min_for_rate(lam, neff_min: float = 8.0):
    """Smallest resolvable kernel scale at local print rate `lam` (prints/s).

    This is a DATA limit and cannot be charted around. Plot it on every fine-band
    figure so the blank region is labelled rather than mysterious."""
    lam = np.asarray(lam, dtype=np.float64)
    return np.divide(neff_min / (2.0 * np.sqrt(np.pi)), lam,
                     out=np.full_like(lam, np.inf), where=lam > 0)


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


def intervals(ts_ns: np.ndarray, origin: int | None = None):
    """-> (event_time_seconds_since_origin, log10_interval_seconds).

    Differencing happens in int64 NANOSECONDS. float64 seconds since the Unix epoch
    has a ULP of 238 ns against an archive resolution of 80.5 ns median / 49 ns min,
    so differencing there destroys the fine band. Positions are float64 but only
    RELATIVE to an explicit origin, where the ULP is negligible."""
    ts = np.asarray(ts_ns, dtype=np.int64)
    d = np.diff(ts)
    if d.size and np.any(d <= 0):
        raise ValueError("non-positive interval: collapse ties first")
    o = np.int64(ts[0] if origin is None else origin)
    return (ts[1:] - o).astype(np.float64) / 1e9, np.log10(d.astype(np.float64) * 1e-9)


def seconds_since(ts_ns, origin: int) -> np.ndarray:
    """Print times as float64 seconds relative to an explicit origin."""
    return (np.asarray(ts_ns, dtype=np.int64) - np.int64(origin)).astype(np.float64) / 1e9


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


def field(ts_s, ev_s, x, t_grid, scales, neff_min=8.0, sigma_lo=8.0, edge_scales=4.0,
          reduce="interp"):   # "auto" is for RENDERING; see _reduce_extremum
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
    col_w = float(np.median(np.diff(t_grid))) if nT > 1 else np.inf
    out = {k: np.full((nT, nS), np.nan) for k in
           ("m", "dm", "lograte", "dlograte", "n_eff", "n_eff_rate")}
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

        # The rate channel needs the SAME data floor as the interval channel. Without
        # it, a window holding a fraction of a print returns a confident-looking number:
        # at 2.5 prints/s and s = 15.6 ms the expected in-kernel count is 0.14 and
        # |dL/dln s| reaches ~14 decades/e-fold, which then sets the colour scale and
        # buries everything real. Measured, see test_rate_channel_declines_on_empty_windows.
        ch = gaussian_filter1d(c, half, order=0, **G)
        neff_rate = np.divide(2 * rt * sg * c0 * c0, ch, out=np.zeros_like(c0), where=ch > 0)
        cpos = (c0 > 0) & (neff_rate >= neff_min)
        lr = np.where(cpos, np.log(np.divide(c0, dt, out=np.ones_like(c0), where=c0 > 0)), np.nan)
        dlr = np.divide(sg * sg * c2, c0, out=np.full_like(c0, np.nan), where=cpos)
        dlr = np.where(cpos, dlr, np.nan)

        gt = t0 + (np.arange(len(c0)) + 0.5) * dt
        edge = (t_grid > t0 + edge_scales * s) & (t_grid < t1 - edge_scales * s)
        for name, arr in (("m", m), ("dm", dm), ("lograte", lr),
                          ("dlograte", dlr), ("n_eff", neff), ("n_eff_rate", neff_rate)):
            # "auto": extremum ONLY where the kernel is narrower than an output
            # column. Above that the field is already resolved and extremum just
            # raises the noise floor (measured: background p99 0.59 -> 1.53).
            use_ext = (reduce == "extremum") or (reduce == "auto" and s < col_w)
            v = (_reduce_extremum(t_grid, gt, arr) if use_ext
                 else np.interp(t_grid, gt, arr, left=np.nan, right=np.nan))
            out[name][:, j] = np.where(edge, v, np.nan)
    return out


def _reduce_extremum(t_grid, gt, arr):
    """Map a fine native grid onto a coarser output grid by keeping, per output cell,
    the value of LARGEST MAGNITUDE rather than a point sample.

    Point-sampling a field whose kernel is far narrower than the output spacing does
    not blur short features, it DELETES the ones that fall between columns -- a 50 ms
    burst rendered at 1.5 s per column survives only by luck. Extremum reduction is
    the standard waveform/oscilloscope decimation and costs nothing extra.

    OFF BY DEFAULT, and that is a measured negative result rather than an oversight.
    Tested against point sampling on injected bursts at their own scale (peak over
    background p99): 150 ms 2.4x -> 1.0x, 500 ms 3.3x -> 2.9x, 2 s 7.3x -> 7.3x. It
    raises the background floor as much as the signal (p99 0.59 -> 1.53). The apparent
    early win was an artefact of maximising over the unmasked fine-band noise that the
    rate channel's missing n_eff floor was producing. Kept, off, as the record.
    """
    if len(gt) <= len(t_grid):
        return np.interp(t_grid, gt, arr, left=np.nan, right=np.nan)
    edges = np.empty(len(t_grid) + 1)
    edges[1:-1] = 0.5 * (t_grid[1:] + t_grid[:-1])
    edges[0] = t_grid[0] - (edges[1] - t_grid[0]); edges[-1] = t_grid[-1] + (t_grid[-1] - edges[-2])
    idx = np.searchsorted(gt, edges)
    out = np.full(len(t_grid), np.nan)
    for i in range(len(t_grid)):
        seg = arr[idx[i]:idx[i + 1]]
        if seg.size == 0:
            continue
        fin = seg[np.isfinite(seg)]
        if fin.size:
            out[i] = fin[np.argmax(np.abs(fin))]
    return out


# --------------------------------------------------------------------------- #
# the booleans -- defined ONCE, in code, so prose can reference them
# --------------------------------------------------------------------------- #

def scale_index_at(scales, s_min_t, factor=2.0, defined=None):
    """Per time point, the index of the smallest ladder scale >= factor * s_min(t).

    `factor` keeps the read off the boundary itself: s_min moves with lambda, so a read
    taken AT the boundary is partly definitional -- the boundary dropping and the tape
    speeding up are the same event. -1 where no ladder scale qualifies or the field is
    undefined there."""
    scales = np.asarray(scales, float)
    s_target = factor * np.asarray(s_min_t, float)
    out = np.full(s_target.size, -1, dtype=np.int64)
    for i in range(s_target.size):
        if not np.isfinite(s_target[i]):
            continue
        ok = scales >= s_target[i]
        if defined is not None:
            ok = ok & np.asarray(defined[i], bool)
        c = np.flatnonzero(ok)
        if c.size:
            out[i] = c[0]
    return out


def burst_on(f, scales, s_min_t, factor=2.0):
    """THE BURST BOOLEAN. Defined once, here, so that prose never restates the condition.

    ON where dL/dln s < 0 at the smallest ladder scale clearing `factor * s_min(t)`.

    THE SIGN, AND WHY THIS FUNCTION EXISTS. dL/dln s = E_w[z^2] - 1 with z = (t-t_i)/s.
    At a cluster centre the kernel's mass sits at z ~ 0 and it goes to -1; in a gap the
    nearest prints are at |z| >> 1 and it goes positive. So NEGATIVE is burst-like and
    POSITIVE selects voids. The acceptance suite always had this right -- it takes argmin
    and -nanmin throughout -- but a work order restated it in English and inverted it.
    Restating a sign convention in prose is the failure mode; referencing this helper is
    the fix.

    NOTE THE BOUND: dL/dln s >= -1 because E_w[z^2] >= 0, so the burst signal SATURATES.
    Under a sign condition it fires often; under a magnitude condition it barely fires at
    all. That is structural and is why this is a poor detector in either direction.

    Returns (on, s_star, jstar).
    """
    dlr = f["dlograte"]
    j = scale_index_at(scales, s_min_t, factor, defined=np.isfinite(dlr))
    ok = j >= 0
    ii = np.arange(dlr.shape[0])
    v = np.where(ok, dlr[ii, np.clip(j, 0, None)], np.nan)
    s_star = np.where(ok, np.asarray(scales, float)[np.clip(j, 0, None)], np.nan)
    return (ok & np.isfinite(v) & (v < 0)), s_star, j


def divergence(f):
    """D(t,s) = m + lograte/ln10 + gamma/ln10.

    IDENTICALLY ZERO at every scale under a locally Poisson process AT ANY RATE PATH,
    because m -> -log10(lambda) - gamma/ln10 while lograte -> ln(lambda). So its sign
    needs no null to read, and unlike dL/dln s it is a LEVEL DIFFERENCE BETWEEN TWO
    CHANNELS at one scale -- it has neither the centring nor the boundedness that make
    the scale-derivative a poor onset detector.

    The acceptance suite asserts the identity (test_cross_channel_identity_on_poisson);
    this promotes it from a unit-test fixture to an emitted field.
    """
    return f["m"] + f["lograte"] / LN10 + EULER_GAMMA / LN10


def divergence_on(f, scales, s_min_t, factor=2.0):
    """ON where D < 0 at the smallest ladder scale clearing factor * s_min(t).
    Negative = more clustered than Poisson. Returns (on, s_star, jstar)."""
    D = divergence(f)
    j = scale_index_at(scales, s_min_t, factor, defined=np.isfinite(D))
    ok = j >= 0
    ii = np.arange(D.shape[0])
    v = np.where(ok, D[ii, np.clip(j, 0, None)], np.nan)
    s_star = np.where(ok, np.asarray(scales, float)[np.clip(j, 0, None)], np.nan)
    return (ok & np.isfinite(v) & (v < 0)), s_star, j


# --------------------------------------------------------------------------- #
# reconciliation target: Allan factor (phase 10 v3 / 10b)
# --------------------------------------------------------------------------- #

def allan_factor(ts_s, T, t_start=None, t_end=None, min_windows=2):
    """A(T) = E[(N_{i+1}-N_i)^2] / (2 E[N]) over NON-OVERLAPPING windows of width T.
    Homogeneous Poisson -> 1 flat. Returns (A, n_adjacent_pairs).

    THE WINDOW ORIGIN IS AN ARGUMENT, NOT AN ASSUMPTION. Unset, windows tile
    [min(ts), max(ts)) -- the data's own support, which is what a synthetic tape
    wants and what the acceptance suite asserts against. Phase 10 v3 tiled the D3
    extended session [04:00 ET, post_end) instead, so empty stretches are real zeros
    rather than omissions (config/phase_10_v3.json gate.window_origin). Reconciling
    against v3 REQUIRES passing that window explicitly -- the origin, the span, and
    therefore every count depends on it. `min_windows` mirrors v3's
    min_windows_for_a_rung: a rung with fewer windows is dropped, not returned small.

    These three arguments are what the reconciliation gate runs on, and without them
    it cannot be expressed at all. Defaults reproduce the argument-free behaviour
    exactly; test_allan_window_defaults_are_the_data_support asserts that.
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
