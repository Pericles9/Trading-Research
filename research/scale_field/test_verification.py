"""
Adversarial verification. Targets the defect CLASS the float64-ULP bug came from:
silent precision, unit, masking and population errors that return plausible numbers.
Every tape here is deliberately hostile in a way the acceptance suite's tapes are not.
"""
import numpy as np, pytest
from scale_field import (collapse_same_timestamp, intervals, seconds_since, field,
                         field_exact, SIGMA_POISSON_DECADES)

GAMMA_DEC = 0.5772156649015329 / np.log(10.0)     # 0.250684
EPOCH_2020 = 1_596_000_000_000_000_000            # ~2020-07-29, a real sip_timestamp

def poisson_ns(rate, T, seed, res_ns=1):
    r = np.random.default_rng(seed)
    t = np.cumsum(r.exponential(1 / rate, int(rate * T * 1.4) + 200))
    t = t[t < T]
    return (np.round(t * 1e9 / res_ns) * res_ns).astype(np.int64)

def burst_ns(bg, hi, start, dur, T, seed, res_ns=1):
    r = np.random.default_rng(seed); t = 0.0; out = []
    while t < T:
        t += r.exponential(1 / (hi if start <= t < start + dur else bg))
        if t < T: out.append(t)
    a = np.array(out)
    return (np.round(a * 1e9 / res_ns) * res_ns).astype(np.int64)


# --- V1. epoch offset must not change anything -------------------------------
def test_field_is_invariant_to_epoch_offset():
    base = burst_ns(20, 400, 150, 3, 300, 21)
    outs = []
    for off in (0, EPOCH_2020):
        ts = collapse_same_timestamp(base + off)
        ev, x = intervals(ts, origin=ts[0])
        f = field(seconds_since(ts, ts[0]), ev, x,
                  np.linspace(20, 280, 300), np.geomspace(0.05, 20, 30))
        outs.append(f)
    for k in ("m", "dm", "lograte", "dlograte"):
        a, b = outs[0][k], outs[1][k]
        ok = np.isfinite(a) & np.isfinite(b)
        assert np.isfinite(a).sum() == np.isfinite(b).sum(), k
        assert np.nanmax(np.abs(a[ok] - b[ok])) < 1e-9, (k, np.nanmax(np.abs(a[ok] - b[ok])))


# --- V2. the two channels must agree by a KNOWN constant on Poisson ----------
def test_cross_channel_identity_on_poisson():
    """m = -log10(lambda) - gamma/ln10 and lograte = ln(lambda), so
       m + lograte/ln10 == -gamma/ln10 exactly, at every scale, for any rate.
       One assertion that catches a unit error, a sign error or a bad normaliser
       in either channel."""
    ts = collapse_same_timestamp(poisson_ns(200, 400, 22))
    ev, x = intervals(ts, origin=ts[0])
    f = field(seconds_since(ts, ts[0]), ev, x,
              np.linspace(60, 340, 200), np.geomspace(0.5, 30, 24))
    resid = f["m"] + f["lograte"] / np.log(10.0)
    ok = np.isfinite(resid)
    assert ok.sum() > 1000
    assert abs(np.nanmedian(resid[ok]) + GAMMA_DEC) < 0.02, np.nanmedian(resid[ok])


# --- V3. analytic rate path: exponential ramp --------------------------------
def test_exponential_rate_ramp_matches_closed_form():
    """lambda(t) = l0*exp(k t) => smoothed log-rate = ln l0 + k t + k^2 s^2 / 2,
       so dL/dln s = k^2 s^2 exactly. Deterministic target, no fitting."""
    r = np.random.default_rng(23); l0, k, T = 300.0, 1 / 250.0, 900.0
    n = int(l0 / k * (np.exp(k * T) - 1))
    u = np.sort(r.uniform(0, 1, n))
    t = np.log(1 + u * (np.exp(k * T) - 1)) / k              # inverse-CDF sampling
    ts = collapse_same_timestamp((t * 1e9).astype(np.int64))
    ev, x = intervals(ts, origin=ts[0])
    sc = np.geomspace(2.0, 60.0, 16)
    f = field(seconds_since(ts, ts[0]), ev, x, np.linspace(300, 600, 80), sc)
    pred = (k * sc) ** 2
    obs = np.nanmedian(f["dlograte"], axis=0)
    ok = np.isfinite(obs) & (pred > 1e-3)
    assert ok.sum() >= 5
    assert np.max(np.abs(obs[ok] - pred[ok])) < 0.02, list(zip(sc[ok], obs[ok], pred[ok]))


# --- V4. fast n_eff must match exact n_eff -----------------------------------
def test_neff_fast_matches_exact():
    ts = collapse_same_timestamp(burst_ns(8, 200, 200, 5, 400, 24))
    ev, x = intervals(ts, origin=ts[0]); tsec = seconds_since(ts, ts[0])
    tg = np.linspace(60, 340, 150); sc = np.geomspace(0.5, 25, 16)
    a = field_exact(tsec, ev, x, tg, sc)["n_eff"]
    b = field(tsec, ev, x, tg, sc)["n_eff"]
    ok = np.isfinite(a) & np.isfinite(b) & (b > 0)
    assert np.nanmax(np.abs(np.log(a[ok] / b[ok]))) < 0.15


# --- V5. does the RATE channel have a data floor at all? ---------------------
def test_rate_channel_declines_on_empty_windows():
    """The interval channel masks on n_eff. The rate channel must too, or it will
       return confident-looking numbers from windows holding a fraction of a print.
       rth median is ~2.5 prints/s: a 15.6 ms kernel holds ~0.04 expected prints."""
    ts = collapse_same_timestamp(poisson_ns(2.5, 3000, 25))
    ev, x = intervals(ts, origin=ts[0]); tsec = seconds_since(ts, ts[0])
    f = field(tsec, ev, x, np.linspace(200, 2800, 400), np.geomspace(0.0156, 0.25, 8))
    frac = np.isfinite(f["dlograte"]).mean()
    assert frac < 0.05, (
        f"rate channel returned finite values in {frac:.0%} of cells at scales where "
        "the expected in-kernel print count is far below 1")


# --- V6. tie collapsing attenuates the rate channel inside bursts ------------
def test_tie_collapsing_does_not_attenuate_the_burst():
    """Ties concentrate where activity is highest, so collapsing them removes
       proportionally more prints inside a burst than outside -- it attenuates the
       very thing being measured. v1 floored 2.7% of prints on average, 8.1% max."""
    # A sweep through several resting orders reports as several prints at ONE
    # timestamp. Model that: during the burst each arrival emits a cluster of
    # simultaneous prints; the background emits singles.
    r = np.random.default_rng(126)
    base = burst_ns(20, 900, 150, 2.0, 300, 26, res_ns=100)
    mult = np.where((base >= 150 * 10**9) & (base < 152 * 10**9), 1 + r.poisson(3, base.size), 1)
    raw = np.sort(np.repeat(base, mult))
    col = collapse_same_timestamp(raw)
    lost = 1 - len(col) / len(raw)
    assert lost > 0.02, f"test tape is not exercising ties (only {lost:.1%} lost)"
    peaks = []
    for ts in (np.unique(raw), col):
        ev, x = intervals(ts, origin=ts[0])
        f = field(seconds_since(ts, ts[0]), ev, x, np.array([151.0]),
                  np.geomspace(0.2, 20, 24))
        peaks.append(np.nanmin(f["dlograte"][0]))
    atten = 1 - peaks[1] / peaks[0]
    assert abs(atten) < 0.10, (
        f"collapsing ties lost {lost:.1%} of prints and moved the burst's rate-channel "
        f"amplitude by {atten:+.1%}")


# --- V7. stationary non-Poisson intervals -> zero derivative ------------------
def test_stationary_lognormal_intervals_give_zero_dm():
    r = np.random.default_rng(27)
    d = np.exp(r.normal(np.log(0.02), 0.9, 120_000))
    ts = collapse_same_timestamp((np.cumsum(d) * 1e9).astype(np.int64))
    ev, x = intervals(ts, origin=ts[0])
    f = field(seconds_since(ts, ts[0]), ev, x,
              np.linspace(200, 1800, 200), np.geomspace(0.5, 40, 20))
    ok = np.isfinite(f["dm"])
    assert abs(np.nanmedian(f["dm"][ok])) < 0.02
    assert np.nanpercentile(np.abs(f["dm"][ok]), 99) < 0.25


# --- V8. response is monotone in burst amplitude -----------------------------
def test_response_monotone_in_amplitude():
    got = []
    for amp in (4, 8, 16, 32):
        ts = collapse_same_timestamp(burst_ns(10, 10 * amp, 200, 4, 400, 28))
        ev, x = intervals(ts, origin=ts[0])
        f = field(seconds_since(ts, ts[0]), ev, x, np.array([202.0]),
                  np.geomspace(0.5, 30, 20))
        got.append(-np.nanmin(f["dlograte"][0]))
    assert all(b > a for a, b in zip(got, got[1:])), got
