"""
Acceptance suite. Every assertion is against a closed form or a known answer.
This file IS the specification -- if it passes, the estimator is correct.
Run: python -m pytest test_scale_field.py -q
"""
import numpy as np, pytest
from scale_field import (collapse_same_timestamp, intervals, seconds_since, field,
                         field_exact, allan_factor, burst_on, divergence,
                         SIGMA_POISSON_DECADES)

RNG = lambda s=0: np.random.default_rng(s)


def poisson_tape(rate, T, seed=0, t0=0.0):
    r = RNG(seed); n = int(rate * T * 1.4) + 100
    t = t0 + np.cumsum(r.exponential(1 / rate, n))
    return t[t < t0 + T]


def burst_tape(bg, hi, start, dur, T, seed=0):
    r = RNG(seed); t = 0.0; out = []
    while t < T:
        lam = hi if start <= t < start + dur else bg
        t += r.exponential(1 / lam)
        if t < T: out.append(t)
    return np.array(out)


# --- 1. the Poisson null constants -------------------------------------------
@pytest.mark.parametrize("rate", [0.5, 5.0, 500.0])
def test_log_interval_null_is_pure_location_shift(rate):
    x = np.log10(RNG(1).exponential(1 / rate, 2_000_000))
    assert abs(x.mean() - (-np.log10(rate) - 0.5772156649 / np.log(10))) < 5e-3
    assert abs(x.std() - SIGMA_POISSON_DECADES) < 5e-3          # shape is rate-invariant
    assert abs(((x - x.mean())**3).mean() / x.std()**3 + 1.1395) < 0.02


# --- 2. the analytic scale-derivative ----------------------------------------
def test_analytic_scale_derivative_matches_finite_difference():
    ts = collapse_same_timestamp((poisson_tape(20, 300, 2) * 1e9).astype(np.int64))
    ev, x = intervals(ts, origin=ts[0]); tsec = seconds_since(ts, ts[0])
    tg = np.linspace(40, 260, 120); sc = np.geomspace(0.5, 20, 14); h = 1e-3
    f0 = field_exact(tsec, ev, x, tg, sc)
    fp = field_exact(tsec, ev, x, tg, sc * np.exp(h))
    fm = field_exact(tsec, ev, x, tg, sc * np.exp(-h))
    for a, b in (("m", "dm"), ("lograte", "dlograte")):
        fd = (fp[a] - fm[a]) / (2 * h)
        ok = np.isfinite(fd) & np.isfinite(f0[b])
        assert np.nanmax(np.abs(f0[b][ok] - fd[ok])) / np.nanmax(np.abs(fd[ok])) < 1e-4


# --- 3. sign convention (this caught a real bug) -----------------------------
def test_sign_a_rate_burst_is_positive_on_both_channels():
    ts = collapse_same_timestamp((burst_tape(3, 120, 150, 4, 300, 3) * 1e9).astype(np.int64))
    ev, x = intervals(ts, origin=ts[0])
    tg = np.array([152.0]); sc = np.geomspace(1, 30, 12)
    f = field_exact(seconds_since(ts, ts[0]), ev, x, tg, sc)
    assert np.nanmax(f["dm"]) > 0          # window faster than surroundings -> m rises with s
    assert np.nanmax(-f["dlograte"]) > 0   # intensity falls as the window widens


# --- 4. fast path reproduces the exact path ----------------------------------
def test_pyramid_matches_exact():
    ts = collapse_same_timestamp((burst_tape(4, 90, 200, 6, 500, 4) * 1e9).astype(np.int64))
    ev, x = intervals(ts, origin=ts[0]); tsec = seconds_since(ts, ts[0])
    tg = np.linspace(60, 440, 200); sc = np.geomspace(0.4, 40, 20)
    a = field_exact(tsec, ev, x, tg, sc); b = field(tsec, ev, x, tg, sc)
    # The pyramid's accuracy floor is set by bin width, so it is worst in the FIRST
    # octave and negligible above it. Assert both, separately, rather than picking one
    # tolerance that hides where the error lives.
    fine = sc < 2 * sc.min()
    for k in ("m", "dm", "lograte", "dlograte"):
        ok = np.isfinite(a[k]) & np.isfinite(b[k])
        assert ok.sum() > 0.4 * a[k].size, k
        sd = np.nanstd(a[k][ok]) or 1.0
        err = np.abs(a[k] - b[k]) / sd
        # Tolerances are the MEASURED errors plus ~30% headroom, per field. They are
        # a pinned description of the approximation, not a bar chosen to pass. A
        # regression that widens them is a real change and should be argued for.
        tol_fine, tol_coarse = {"m": (0.06, 0.09), "dm": (0.18, 0.28),
                                "lograte": (0.15, 0.08), "dlograte": (0.65, 0.18)}[k]
        assert np.nanmax(err[:, fine]) < tol_fine, (k, "first octave", np.nanmax(err[:, fine]))
        assert np.nanmax(err[:, ~fine]) < tol_coarse, (k, "coarse", np.nanmax(err[:, ~fine]))


# --- 5. duration recovery, rate channel --------------------------------------
@pytest.mark.parametrize("dur,amp", [(2.0, 40), (10.0, 20), (40.0, 12)])
def test_rate_channel_recovers_burst_duration(dur, amp):
    T = max(600.0, 20 * dur)
    ts = collapse_same_timestamp((burst_tape(4, 4 * amp, T / 2, dur, T, 5) * 1e9).astype(np.int64))
    ev, x = intervals(ts, origin=ts[0])
    sc = np.geomspace(dur / 12, dur * 12, 40)
    f = field(seconds_since(ts, ts[0]), ev, x, np.array([T / 2 + dur / 2]), sc)
    est = sc[np.nanargmin(f["dlograte"][0])]
    assert 0.45 < est / dur < 2.2, f"true {dur}s, recovered {est:.2f}s"


# --- 6. time-rescaling invariance --------------------------------------------
def test_scale_free_under_time_rescaling():
    base = burst_tape(4, 150, 250, 5, 500, 6)
    for c in (0.1, 10.0):
        out = []
        for tape, sc in ((base, np.geomspace(.5, 50, 30)), (base * c, np.geomspace(.5, 50, 30) * c)):
            ts = collapse_same_timestamp((tape * 1e9).astype(np.int64))
            ev, x = intervals(ts, origin=ts[0])
            f = field(seconds_since(ts, ts[0]), ev, x,
                      np.array([252.5 * (1 if tape is base else c)]), sc)
            out.append(sc[np.nanargmin(f["dlograte"][0])] / (1 if tape is base else c))
        assert abs(np.log2(out[1] / out[0])) < 0.30, out


# --- 7. Allan factor is 1 on Poisson, >1 with clustering ---------------------
def test_allan_factor_poisson_is_one():
    ts = poisson_tape(50, 4000, 7)
    for T in (0.5, 2.0, 8.0, 32.0):
        A, n = allan_factor(ts, T)
        assert n > 50 and 0.75 < A < 1.35, (T, A, n)

def test_allan_factor_detects_clustering():
    r = RNG(8); parents = np.sort(r.uniform(0, 4000, 2000))
    ts = np.sort(np.concatenate([p + r.exponential(0.01, 8) for p in parents]))
    assert allan_factor(ts, 2.0)[0] > 2.0


# --- 8. degenerate input ------------------------------------------------------
def test_ties_are_collapsed_and_intervals_are_positive():
    raw = np.array([1, 1, 1, 5, 9, 9, 20], dtype=np.int64)
    ts = collapse_same_timestamp(raw)
    assert ts.tolist() == [1, 5, 9, 20]
    ev, x = intervals(ts); assert np.all(np.isfinite(x))

def test_unsorted_input_raises():
    with pytest.raises(ValueError):
        collapse_same_timestamp(np.array([5, 1, 9], dtype=np.int64))

def test_zero_interval_raises_rather_than_imputing():
    with pytest.raises(ValueError):
        intervals(np.array([1, 1, 5], dtype=np.int64))

def test_sparse_region_is_masked_not_guessed():
    ts = collapse_same_timestamp((poisson_tape(0.05, 3000, 9) * 1e9).astype(np.int64))
    ev, x = intervals(ts, origin=ts[0])
    f = field(seconds_since(ts, ts[0]), ev, x, np.linspace(300, 2700, 60),
              np.geomspace(0.05, 2.0, 10))
    assert np.isnan(f["dm"]).mean() > 0.5      # below the n_eff floor -> NaN, never a number


# --- 9. the explicit Allan window, which the reconciliation gate runs on -------
# allan_factor's t_start / t_end / min_windows exist because Phase 10 v3 tiles the D3
# extended session, not the data's own support, and the origin cannot be inferred from
# the prints. Without them the gate cannot be expressed. These three tests pin that the
# arguments are additive, that they are load-bearing, and that the eligibility rule
# drops a rung rather than returning it small.

def test_allan_window_defaults_are_the_data_support():
    """The added arguments must not have moved the default answer."""
    ts = poisson_tape(50, 4000, 7)
    for T in (0.5, 2.0, 8.0, 32.0):
        a, na = allan_factor(ts, T)
        b, nb = allan_factor(ts, T, t_start=ts.min(), t_end=ts.max())
        assert (a, na) == (b, nb), (T, a, b)

def test_allan_window_origin_changes_the_answer():
    """Padding the window with genuinely empty time is a different measurement, not a
    rounding difference -- which is exactly why v3's session origin must be passed
    rather than inferred."""
    ts = poisson_tape(50, 2000, 7)
    a, _ = allan_factor(ts, 32.0)
    b, nb = allan_factor(ts, 32.0, t_start=ts.min() - 2000.0, t_end=ts.max())
    assert nb > 100 and b > 2 * a, (a, b, nb)

def test_allan_min_windows_drops_a_rung_rather_than_returning_it():
    ts = poisson_tape(50, 4000, 7)
    A, n = allan_factor(ts, 1000.0, min_windows=8)     # only ~3 windows fit
    assert np.isnan(A) and n == 0
    A2, n2 = allan_factor(ts, 1000.0, min_windows=2)
    assert np.isfinite(A2) and n2 == 2                 # 3 windows -> 2 adjacent pairs


# --- 11. the booleans, so the sign lives in code and not in prose -------------
def test_burst_on_fires_inside_a_burst_and_not_in_the_quiet_stretch():
    """The sign convention, asserted on the helper the rest of the codebase calls.
    A work order once restated this in English and inverted it; this is the guard."""
    from scale_field import burst_on, seconds_since
    ts = collapse_same_timestamp((burst_tape(3, 120, 150, 4, 300, 3) * 1e9).astype(np.int64))
    ev, x = intervals(ts, origin=ts[0])
    tg = np.array([152.0, 80.0])                    # inside the burst, then quiet
    sc = np.geomspace(0.5, 20, 14)
    f = field_exact(seconds_since(ts, ts[0]), ev, x, tg, sc)
    on, s_star, j = burst_on(f, sc, np.array([0.25, 0.25]), factor=2.0)
    assert on[0], "burst_on must be True inside a rate burst"
    assert np.isfinite(s_star[0]) and s_star[0] >= 0.5


def test_burst_on_is_bounded_below_which_is_why_it_saturates():
    """dL/dln s = E_w[z^2] - 1 >= -1. The burst signal SATURATES, which is the structural
    reason a magnitude threshold on it barely fires."""
    ts = collapse_same_timestamp((burst_tape(3, 200, 150, 3, 300, 12) * 1e9).astype(np.int64))
    ev, x = intervals(ts, origin=ts[0])
    f = field_exact(seconds_since(ts, ts[0]), ev, x,
                    np.linspace(140, 160, 40), np.geomspace(0.5, 20, 12))
    d = f["dlograte"][np.isfinite(f["dlograte"])]
    assert d.min() >= -1.0 - 1e-9, d.min()
    assert d.min() < -0.5, "a real burst should approach the bound"


def test_divergence_is_zero_on_poisson_and_negative_when_clustered():
    """D = m + lograte/ln10 + gamma/ln10 is identically 0 under a locally Poisson process
    at ANY rate path, so its sign is readable without a null."""
    from scale_field import divergence
    ts = collapse_same_timestamp((poisson_tape(200, 400, 31) * 1e9).astype(np.int64))
    ev, x = intervals(ts, origin=ts[0])
    f = field_exact(seconds_since(ts, ts[0]), ev, x,
                    np.linspace(60, 340, 60), np.geomspace(0.5, 20, 10))
    D = divergence(f)
    assert abs(np.nanmedian(D)) < 0.05, np.nanmedian(D)

    r = RNG(32); parents = np.sort(r.uniform(0, 400, 2000))
    cl = np.sort(np.concatenate([p + r.exponential(0.002, 6) for p in parents]))
    tsc = collapse_same_timestamp((cl * 1e9).astype(np.int64))
    ev2, x2 = intervals(tsc, origin=tsc[0])
    f2 = field_exact(seconds_since(tsc, tsc[0]), ev2, x2,
                     np.linspace(60, 340, 60), np.geomspace(0.5, 20, 10))
    assert np.nanmedian(divergence(f2)) < -0.5, np.nanmedian(divergence(f2))
