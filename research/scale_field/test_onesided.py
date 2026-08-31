"""
The causal re-derivation. This file IS the specification for the one-sided kernel, in
the same sense test_scale_field.py is for the centred one -- if it passes, the causal
estimator is right.

WHAT IT HAS TO ESTABLISH, and why each item is here rather than argued in prose:

  O1  the field cannot read forward                  -- BIT-EXACT, the whole point
  O2  and the centred one demonstrably can           -- quantifies what D22 flagged
  O3  fast FFT path == pairwise reference
  O4  analytic dL/dln s == finite difference
  O5  Poisson null still sits at zero
  O6  cross-channel Poisson identity survives
  O7  closed-form rate ramp, WITH the erfc correction that only the causal kernel has
  O8  n_eff exactly halves, so s_min exactly doubles -- the derived price of causality
  O9  the sign convention is unchanged
  O10 the -1 bound SURVIVES -- D22 structural fact 1 is not repaired by going causal

Run: python -m pytest test_onesided.py -q
"""
import numpy as np
import pytest
from scipy.special import erfc

from scale_field import (EULER_GAMMA, LN10, NEFF_S_MIN_COEF_ONESIDED,
                         collapse_same_timestamp, field_exact, field_onesided,
                         intervals, s_min_for_rate, s_min_onesided, seconds_since)

RNG = lambda s=0: np.random.default_rng(s)


def poisson_tape(rate, T, seed=0, t0=0.0):
    r = RNG(seed)
    t = t0 + np.cumsum(r.exponential(1 / rate, int(rate * T * 1.4) + 200))
    return t[t < t0 + T]


def burst_tape(bg, hi, start, dur, T, seed=0):
    r = RNG(seed); t = 0.0; out = []
    while t < T:
        t += r.exponential(1 / (hi if start <= t < start + dur else bg))
        if t < T:
            out.append(t)
    return np.array(out)


def prep(tape, cut=None):
    """`cut` truncates the tape at that many seconds AFTER ITS FIRST PRINT.

    The coordinate matters and the first draft of this file got it wrong: prep
    re-origins to ts[0], so truncating the raw tape at a grid time cuts somewhere
    else entirely -- here, 26 ms early, which silently left real prints out of the
    'full' tape and made the causality test fail against itself. Truncating on the
    same int64 array the origin is taken from is the only version that is comparing
    like with like."""
    ts = collapse_same_timestamp((np.asarray(tape) * 1e9).astype(np.int64))
    if cut is not None:
        ts = ts[ts <= ts[0] + np.int64(round(cut * 1e9))]
    ev, x = intervals(ts, origin=ts[0])
    return seconds_since(ts, ts[0]), ev, x


# --- O1. THE CAUSALITY ASSERTION -- bit-exact on the reference path -----------
def test_onesided_field_is_bit_identical_when_the_future_is_rewritten():
    """THE ASSERTION THE WHOLE RE-DERIVATION EXISTS TO PASS, and it is checked for
    EQUALITY rather than to a tolerance.

    The future is REWRITTEN, not deleted: every print after the last evaluation time
    is replaced by a different set of prints, same count. That keeps both arrays the
    same length, so numpy's pairwise summation associates identically and any
    difference at all is a real forward read rather than a reordered float sum.
    Deleting instead (next test) shortens the array, changes the association order,
    and costs about 4e-15 -- which is why that version cannot be asserted exactly and
    this one can."""
    tape = np.sort(burst_tape(20, 400, 150, 3, 300, 41))
    cut = 200.0
    a_args = prep(tape, )
    t0_raw = float(tape[0])
    fut = tape > t0_raw + cut
    alt = tape.copy()
    # same number of future prints, entirely different times, still sorted and later
    alt[fut] = np.sort(t0_raw + cut + 1e-3 + np.cumsum(
        RNG(99).exponential(0.02, int(fut.sum()))))
    tg = np.linspace(60, cut, 90)
    sc = np.geomspace(0.5, 12, 14)
    a = field_exact(*prep(tape), tg, sc, kernel="onesided")
    b = field_exact(*prep(alt), tg, sc, kernel="onesided")
    for k in ("m", "dm", "lograte", "dlograte", "n_eff"):
        fa, fb = a[k], b[k]
        assert np.array_equal(np.isnan(fa), np.isnan(fb)), f"{k}: mask moved"
        ok = np.isfinite(fa)
        assert ok.sum() > 100, k
        assert np.array_equal(fa[ok], fb[ok]), (
            f"{k}: rewriting the future changed the field by "
            f"{np.nanmax(np.abs(fa[ok] - fb[ok]))} -- the kernel reads forward")


def test_onesided_field_survives_the_future_being_deleted():
    """Deletion variant. Not exact, and the reason is recorded rather than absorbed:
    a shorter array changes numpy's pairwise-summation association order, which moves
    the last ulp. Measured 4e-15 across all five outputs, which is 4e-15 more than a
    forward read and thirteen orders below anything this field is read at."""
    tape = burst_tape(20, 400, 150, 3, 300, 41)
    tg = np.linspace(60, 200, 90)
    sc = np.geomspace(0.5, 12, 14)
    a = field_exact(*prep(tape), tg, sc, kernel="onesided")
    b = field_exact(*prep(tape, cut=tg[-1]), tg, sc, kernel="onesided")
    for k in ("m", "dm", "lograte", "dlograte"):
        ok = np.isfinite(a[k]) & np.isfinite(b[k])
        assert ok.sum() > 100, k
        assert np.nanmax(np.abs(a[k][ok] - b[k][ok])) < 1e-12, k


def test_onesided_fft_path_is_causal_too():
    """Same assertion on the production FFT path, which is the one that actually runs
    on tape. Truncation also changes the FFT length here, so 1e-12 again."""
    tape = burst_tape(20, 400, 150, 3, 300, 42)
    tg = np.linspace(60, 200, 200)
    sc = np.geomspace(0.5, 12, 12)
    a = field_onesided(*prep(tape), tg, sc)
    b = field_onesided(*prep(tape, cut=tg[-1]), tg, sc)
    for k in ("m", "dm", "lograte", "dlograte"):
        ok = np.isfinite(a[k]) & np.isfinite(b[k])
        assert ok.sum() > 200, k
        assert np.nanmax(np.abs(a[k][ok] - b[k][ok])) < 1e-12, k


# --- O2. and the CENTRED kernel demonstrably does read forward ---------------
def test_centred_field_reads_forward_and_the_onesided_one_does_not():
    """The contrast, measured rather than asserted. A burst starts at t=150. Read both
    fields at times strictly BEFORE it. The centred field already responds; the causal
    field is identically at its background value.

    This is D22's structural fact 2 turned into a number, and it is the reason no
    absolute timing claim in this line survived."""
    tape = burst_tape(20, 600, 150.0, 2.0, 300, 43)
    tg = np.linspace(140.0, 149.0, 40)          # entirely before the onset
    sc = np.array([2.0])
    args = prep(tape)
    cen = field_exact(*args, tg, sc)["dlograte"][:, 0]
    one = field_exact(*args, tg, sc, kernel="onesided")["dlograte"][:, 0]

    # the causal read must be indistinguishable from the same read on a tape that
    # simply has no burst in it at all
    notape = np.asarray(tape)[(np.asarray(tape) < 150.0) | (np.asarray(tape) >= 152.0)]
    one_nb = field_exact(*prep(notape), tg, sc, kernel="onesided")["dlograte"][:, 0]
    ok = np.isfinite(one) & np.isfinite(one_nb)
    assert ok.sum() > 20
    assert np.nanmax(np.abs(one[ok] - one_nb[ok])) < 1e-12, "causal field saw the burst"

    # the centred one, on the same points, does not have that property
    cen_nb = field_exact(*prep(notape), tg, sc)["dlograte"][:, 0]
    okc = np.isfinite(cen) & np.isfinite(cen_nb)
    fwd = np.nanmax(np.abs(cen[okc] - cen_nb[okc]))
    assert fwd > 0.05, (
        f"centred forward read only {fwd:.3g}; expected the burst to be visible "
        "before it happens")


# --- O3. FFT path reproduces the pairwise reference --------------------------
def test_onesided_fft_matches_pairwise_exact():
    """Accuracy of the production path against the pairwise reference.

    Error is set by BIN WIDTH, dt = min(scales)/sigma_lo, so it is worst in the first
    octave and small above it -- the same structure the centred path has, and asserted
    the same way: separately per octave band, so the tolerance cannot hide where the
    error lives. Tolerances are the MEASURED errors plus ~30% headroom, per field:

        m        0.186 fine / 0.064 coarse       lograte   0.227 / 0.075
        dm       0.596 fine / 0.147 coarse       dlograte  0.425 / 0.180

    Unlike the centred path this carries NO pyramid approximation -- only binning and
    the interpolation onto the output grid -- so raising sigma_lo buys accuracy back
    monotonically at linear cost, with no decimation error underneath it."""
    tape = burst_tape(15, 300, 200, 5, 400, 44)
    args = prep(tape)
    tg = np.linspace(80, 380, 160)
    sc = np.geomspace(1.0, 20, 14)
    a = field_exact(*args, tg, sc, kernel="onesided")
    b = field_onesided(*args, tg, sc)
    fine = sc < 2 * sc.min()
    for k, tol_fine, tol_coarse in (("m", 0.25, 0.09), ("dm", 0.78, 0.20),
                                    ("lograte", 0.30, 0.10), ("dlograte", 0.55, 0.24)):
        ok = np.isfinite(a[k]) & np.isfinite(b[k])
        assert ok.sum() > 0.3 * a[k].size, k
        sd = np.nanstd(a[k][ok]) or 1.0
        err = np.where(ok, np.abs(a[k] - b[k]), np.nan) / sd
        assert np.nanmax(err[:, fine]) < tol_fine, (k, "first octave",
                                                    np.nanmax(err[:, fine]))
        assert np.nanmax(err[:, ~fine]) < tol_coarse, (k, "coarse",
                                                       np.nanmax(err[:, ~fine]))


# --- O4. the analytic scale-derivative, one-sided ----------------------------
def test_onesided_analytic_derivative_matches_finite_difference():
    """dw/dln s = w*z^2 is claimed to be unchanged by the support restriction, because
    the indicator does not depend on s. Checked, not assumed."""
    args = prep(poisson_tape(20, 300, 45))
    tg = np.linspace(40, 260, 100)
    sc = np.geomspace(0.5, 20, 12)
    h = 1e-3
    f0 = field_exact(*args, tg, sc, kernel="onesided")
    fp = field_exact(*args, tg, sc * np.exp(h), kernel="onesided")
    fm = field_exact(*args, tg, sc * np.exp(-h), kernel="onesided")
    for a, b in (("m", "dm"), ("lograte", "dlograte")):
        fd = (fp[a] - fm[a]) / (2 * h)
        ok = np.isfinite(fd) & np.isfinite(f0[b])
        assert ok.sum() > 100, a
        assert np.nanmax(np.abs(f0[b][ok] - fd[ok])) / np.nanmax(np.abs(fd[ok])) < 1e-4


# --- O5. Poisson null sits at zero -------------------------------------------
def test_onesided_poisson_null_is_zero():
    """A half-Gaussian on homogeneous Poisson gives E_w[z^2] = 1 exactly, because
    int_0^inf z^2 e^{-z^2/2} dz == int_0^inf e^{-z^2/2} dz == sqrt(pi/2). So the null
    is zero for the causal kernel just as it is for the centred one -- the constant
    did not have to be re-tuned."""
    args = prep(poisson_tape(200, 400, 46))
    f = field_onesided(*args, np.linspace(60, 340, 200), np.geomspace(1.0, 30, 16))
    d = f["dlograte"][np.isfinite(f["dlograte"])]
    assert d.size > 1000
    assert abs(np.median(d)) < 0.05, np.median(d)


# --- O6. cross-channel Poisson identity survives the support restriction -----
def test_onesided_cross_channel_identity():
    """m + lograte/ln10 == -gamma/ln10, the same identity test_verification.py V2 pins
    for the centred kernel. E[log10 dt] is a property of the interval law, not of the
    weighting, so it must survive -- and it catches a bad normaliser Z(s), which the
    causal kernel DID have to change (sqrt(2pi) -> sqrt(pi/2))."""
    args = prep(poisson_tape(200, 400, 47))
    f = field_onesided(*args, np.linspace(60, 340, 200), np.geomspace(1.0, 30, 16))
    resid = f["m"] + f["lograte"] / LN10
    ok = np.isfinite(resid)
    assert ok.sum() > 1000
    assert abs(np.median(resid[ok]) + EULER_GAMMA / LN10) < 0.02, np.median(resid[ok])


# --- O7. closed-form rate ramp, with the term only the causal kernel has -----
def test_onesided_exponential_ramp_matches_closed_form():
    """lambda(t) = l0 e^{kt} through a half-Gaussian gives

        lambda_hat = l0 e^{kt} e^{k^2 s^2/2} erfc(ks/sqrt2)

    and therefore, with a = ks/sqrt2,

        dL/dln s = k^2 s^2 - 2a exp(-a^2) / (sqrt(pi) erfc(a)).

    The centred kernel gives just k^2 s^2 (V3). The extra term is the causal kernel
    paying for looking only backwards: on a RISING rate, widening a backward-looking
    window reaches further into slower tape, so the estimate FALLS. Note the measured
    sign flips negative here, opposite to the centred case -- a deterministic target
    that no amount of fitting could accidentally satisfy."""
    r = np.random.default_rng(48)
    l0, k, T = 400.0, 1 / 250.0, 900.0
    n = int(l0 / k * (np.exp(k * T) - 1))
    u = np.sort(r.uniform(0, 1, n))
    t = np.log(1 + u * (np.exp(k * T) - 1)) / k
    args = prep(t)
    sc = np.geomspace(3.0, 60.0, 14)
    f = field_onesided(*args, np.linspace(400, 700, 80), sc)
    a = k * sc / np.sqrt(2.0)
    pred = (k * sc) ** 2 - 2 * a * np.exp(-a * a) / (np.sqrt(np.pi) * erfc(a))
    obs = np.nanmedian(f["dlograte"], axis=0)
    ok = np.isfinite(obs)
    assert ok.sum() >= 8
    assert np.max(np.abs(obs[ok] - pred[ok])) < 0.03, list(zip(sc[ok], obs[ok], pred[ok]))
    assert np.all(pred < 0), "the causal correction should dominate on a rising ramp"


# --- O8. the price: n_eff halves, s_min doubles ------------------------------
def test_onesided_neff_is_exactly_half_and_s_min_exactly_double():
    """n_eff = 2 sqrt(pi) s lambda centred, sqrt(pi) s lambda one-sided. Half the
    support is half the effective sample, so the resolution floor doubles. This is
    the derived, non-negotiable cost of causality and it is why the usable scale
    range loses exactly one octave from the bottom."""
    lam = np.array([0.5, 2.5, 18.0, 45.0])
    assert np.allclose(s_min_onesided(lam), 2.0 * s_min_for_rate(lam), rtol=0, atol=0)
    assert abs(NEFF_S_MIN_COEF_ONESIDED - 8.0 / np.sqrt(np.pi)) < 1e-12
    assert abs(s_min_onesided(np.array([2.5]))[0] - 1.8054) < 1e-3   # rth median

    # and the empirical n_eff on a real tape agrees with the analytic halving
    args = prep(poisson_tape(120, 300, 49))
    tg = np.linspace(60, 240, 60)
    sc = np.geomspace(1.0, 12, 8)
    a = field_exact(*args, tg, sc)["n_eff"]
    b = field_exact(*args, tg, sc, kernel="onesided")["n_eff"]
    ok = np.isfinite(a) & np.isfinite(b) & (a > 0)
    assert abs(np.median(b[ok] / a[ok]) - 0.5) < 0.03, np.median(b[ok] / a[ok])


# --- O9. sign convention is unchanged ----------------------------------------
def test_onesided_sign_a_rate_burst_is_still_negative():
    """dL/dln s < 0 is still the burst orientation. The support restriction does not
    touch the sign, and burst_on()'s condition therefore carries over unamended."""
    tape = burst_tape(3, 120, 150, 4, 300, 50)
    args = prep(tape)
    # read INSIDE the burst -- for a causal kernel that means after its start
    f = field_exact(*args, np.array([152.5]), np.geomspace(1, 30, 12), kernel="onesided")
    assert np.nanmin(f["dlograte"]) < 0
    assert np.nanmax(f["dm"]) > 0


# --- O10. the -1 bound SURVIVES ----------------------------------------------
def test_onesided_is_still_bounded_below_by_minus_one():
    """D22 structural fact 1: dL/dln s = E_w[z^2] - 1 with E_w[z^2] >= 0, so the
    statistic saturates at -1 and discriminates poorly under either a sign or a
    magnitude condition. Restricting the support to z >= 0 does not change E_w[z^2]
    >= 0. GOING CAUSAL DOES NOT REPAIR THIS, and this test is here so that nobody
    reads the one-sided work as having repaired it."""
    for seed, tape in ((51, burst_tape(2, 2000, 150, 0.5, 300, 51)),
                       (52, poisson_tape(50, 300, 52))):
        args = prep(tape)
        f = field_onesided(*args, np.linspace(40, 260, 300), np.geomspace(0.2, 20, 20))
        d = f["dlograte"][np.isfinite(f["dlograte"])]
        assert d.size > 500, seed
        assert d.min() >= -1.0 - 1e-9, (seed, d.min())


def test_unknown_kernel_raises():
    with pytest.raises(ValueError):
        s_min_for_rate(np.array([2.5]), kernel="halfcauchy")
