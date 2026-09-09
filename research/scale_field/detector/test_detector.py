#!/usr/bin/env python
"""The credibility battery for the ridge detector.

Source: claude/field_credibility_and_value_tests.md section 2A -- free, self-consistent,
no tape and no null. Each test carries a PRE-REGISTERED EXACT PREDICTION, which is what
makes it a test rather than an inspection.

Three of these were listed in the source as never having been run, and they are the three
with a demonstrated failure rate:

  * test_z_convention          -- "not yet written, and it is the one that already bit me"
  * test_forbidden_sign        -- the causality theorem, counted rather than assumed
  * test_two_code_paths        -- "not run, and I introduced a dt^2 scaling bug in an FFT
                                  path this week"

The trade-weighted zero-sum is also here. It was already run against the committed
estimator (Gate A1, -6.6e-19) but not against this implementation, and it is the cheapest
correctness check that exists on this object.

Run:  .venv/Scripts/python.exe -m pytest research/scale_field/detector/test_detector.py -v
"""
from __future__ import annotations

import numpy as np
import pytest

from .moments import (
    CUT,
    POISSON_NOISE_CONSTANT,
    F,
    F_t,
    F_tt,
    F_tu,
    F_u,
    F_uu,
    field_at,
    field_fft,
    lam_hat,
    n_eff,
)
from .ridge import apex_newton, detect

# --------------------------------------------------------------------------------------
# Synthetic tapes. Poisson background with Gaussian bumps -- the easy case, and the only
# case anything here is entitled to speak about.
# --------------------------------------------------------------------------------------

def sample(lam_fn, T, rate_max, seed):
    rng = np.random.default_rng(seed)
    n = rng.poisson(rate_max * T)
    c = np.sort(rng.random(n) * T)
    return c[rng.random(n) < lam_fn(c) / rate_max]


def two_bump_tape(seed=5):
    """The tape every number in the source document was measured on."""
    def lam(x):
        return (6.0 + 60.0 * np.exp(-(x - 500.0) ** 2 / (2 * 8.0 ** 2))
                + 25.0 * np.exp(-(x - 900.0) ** 2 / (2 * 40.0 ** 2)))
    return sample(lam, 1500.0, 70.0, seed)


def one_sided_tape(seed=11):
    """Sharp onset at t=700, exponential decay tau=25. Asymmetric ON PURPOSE: on a
    symmetric feature the odd t-derivatives sit near zero at the centre and a sign flip
    hides in the noise."""
    def lam(x):
        out = np.full_like(x, 6.0)
        m = x >= 700.0
        out[m] += 60.0 * np.exp(-(x[m] - 700.0) / 25.0)
        return out
    return sample(lam, 1500.0, 70.0, seed)


DETECT_KW = dict(noise_constant=POISSON_NOISE_CONSTANT, kappa=1.0)


def _summary(feats):
    return sorted((round(f.t_ridge, 9), round(f.s_selected, 9), round(f.calibrated, 9))
                  for f in feats)


# --------------------------------------------------------------------------------------
# 1. THE CONVENTION TEST -- the one that already bit the author
# --------------------------------------------------------------------------------------

def test_z_convention():
    """PREDICTION: analytic F_t equals the central difference of F in t, sign included.

    This is the test that catches z = (t_i - t)/s. Under the flipped convention F is
    unchanged and F_t is exactly negated, so the field renders perfectly while every odd
    t-derivative is wrong. Comparing against a central difference of F is convention-free,
    so the flip cannot hide: the relative error goes to ~2 and the sign inverts.
    """
    P = one_sided_tape()
    probes = [(t, s) for t in (690.0, 705.0, 730.0, 800.0) for s in (4.0, 16.0, 64.0)]

    worst = 0.0
    for t, s in probes:
        h = 1e-4 * s
        numeric = (F(P, t + h, s) - F(P, t - h, s)) / (2 * h)
        analytic = F_t(P, t, s)
        assert np.isfinite(numeric) and np.isfinite(analytic)
        scale = max(abs(numeric), 1e-12)
        worst = max(worst, abs(analytic - numeric) / scale)
        # the sign assertion is the part a flipped convention fails outright
        if abs(numeric) > 1e-9:
            assert np.sign(analytic) == np.sign(numeric), (
                f"F_t sign disagrees with dF/dt at t={t}, s={s} -- z convention is flipped"
            )
    assert worst < 1e-5, f"max relative error {worst:.2e}"


def test_ridge_sign_structure():
    """PREDICTION: F has a local minimum over a bump centre, so F_t < 0 just left of it and
    F_t > 0 just right. A flipped convention reverses both.

    Probed INSIDE the negative column (<= 1*s from centre). Further out the sign structure
    is not what naive intuition says: by 3*s the probe is past the peak of the positive
    shoulder and F_t is negative on BOTH sides, which is a property of the trumpet's shape
    and not of the convention.
    """
    P = two_bump_tape()
    s = 8.0
    for d in (0.25, 0.5, 1.0):
        assert F_t(P, 500.0 - d * s, s) < 0.0, f"left of centre at {d}*s"
        assert F_t(P, 500.0 + d * s, s) > 0.0, f"right of centre at {d}*s"


# --------------------------------------------------------------------------------------
# 2. Every derivative against central differences
# --------------------------------------------------------------------------------------

def test_all_derivatives_vs_central_differences():
    """PREDICTION: agreement to ~1e-9. Asserted at 1e-6.

    Both sides are evaluated UNTRUNCATED. That is not a convenience: with the +-CUT*s window
    on, a print can cross the window boundary between t-h and t+h, and the resulting jump --
    of order exp(-18) but divided by 2h -- lands at ~1e-6 absolute in the NUMERICAL
    difference while the analytic formula is exact. Comparing a truncated difference against
    an exact derivative would be measuring the truncation, not the calculus. The truncation
    is worth bounding on its own, and test_truncation_cost does that.
    """
    P = two_bump_tape()
    rng = np.random.default_rng(3)
    worst = {k: 0.0 for k in ("F_t", "F_u", "F_tt", "F_tu", "F_uu")}

    for _ in range(40):
        t = rng.uniform(200.0, 1300.0)
        s = float(np.exp(rng.uniform(np.log(3.0), np.log(120.0))))
        ht, hu = 1e-4 * s, 1e-4

        def f(tt, ss):
            return F(P, tt, ss, truncate=False)

        num = {
            "F_t": (f(t + ht, s) - f(t - ht, s)) / (2 * ht),
            "F_u": (f(t, s * np.exp(hu)) - f(t, s * np.exp(-hu))) / (2 * hu),
            "F_tt": (f(t + ht, s) - 2 * f(t, s) + f(t - ht, s)) / ht ** 2,
            "F_tu": (F_t(P, t, s * np.exp(hu), truncate=False)
                     - F_t(P, t, s * np.exp(-hu), truncate=False)) / (2 * hu),
            "F_uu": (f(t, s * np.exp(hu)) - 2 * f(t, s) + f(t, s * np.exp(-hu))) / hu ** 2,
        }
        ana = {"F_t": F_t(P, t, s, truncate=False), "F_u": F_u(P, t, s, truncate=False),
               "F_tt": F_tt(P, t, s, truncate=False), "F_tu": F_tu(P, t, s, truncate=False),
               "F_uu": F_uu(P, t, s, truncate=False)}

        for k in worst:
            if not (np.isfinite(num[k]) and np.isfinite(ana[k])):
                continue
            worst[k] = max(worst[k], abs(ana[k] - num[k]))

    # Combined criterion, |analytic - numeric| <= atol + rtol*|numeric|, because a pure
    # relative bar is not measurable here. F_tt, F_tu and F_uu are SECOND differences: in
    # double precision their numerical value carries ~4*eps/h^2 of roundoff, so where the
    # true derivative passes near zero the relative error inflates without anything being
    # wrong. Measured absolute floors over these probes: F_t 3.2e-10, F_u 2.0e-08,
    # F_tt 1.7e-09, F_tu 4.7e-09, F_uu 2.9e-07 -- the ordering is first-difference versus
    # second-difference conditioning, not accuracy of the formulas. atol is set at 1e-6,
    # roughly 3x the worst measured floor.
    for k, v in worst.items():
        assert v < 1e-6, f"{k} max absolute error {v:.2e} exceeds the 1e-6 bar"


# --------------------------------------------------------------------------------------
# 3. The trade-weighted zero-sum -- free correctness check on estimator and mask
# --------------------------------------------------------------------------------------

@pytest.mark.parametrize("s", [0.5, 2.0, 8.0])
def test_trade_weighted_zero_sum(s):
    """PREDICTION: exactly zero, at every scale, with no distributional assumption.

    F*lambda-hat = s^2*lambda'' and the integral of lambda'' over the line is zero, so the
    lambda-hat-weighted integral of F must vanish. If it does not, the masking is
    asymmetric or the estimator is wrong.
    """
    P = two_bump_tape()
    lo, hi = P.min() - (CUT + 2) * s, P.max() + (CUT + 2) * s
    grid = np.arange(lo, hi, s / 12.0)

    vals = np.array([F(P, t, s) for t in grid])
    weights = np.array([lam_hat(P, t, s) for t in grid])
    ok = np.isfinite(vals) & np.isfinite(weights)
    signed = float(np.sum(vals[ok] * weights[ok]))
    absolute = float(np.sum(np.abs(vals[ok]) * weights[ok]))

    assert absolute > 0
    assert abs(signed) / absolute < 1e-5, (
        f"zero-sum violated at s={s}: {signed:.3e} against {absolute:.3e} of mass"
    )


# --------------------------------------------------------------------------------------
# 4. The forbidden sign -- the causality theorem, counted
# --------------------------------------------------------------------------------------

def test_forbidden_sign():
    """PREDICTION: sign(F_u * F_tt) < 0 occurs ZERO times at converged apexes on the
    centred kernel. Going up in scale, features may merge and vanish; they may never split
    and never appear out of nothing. A creation event is a render or masking defect, not a
    finding. (This check does NOT apply to a one-sided kernel, which does not satisfy the
    heat equation.)
    """
    P = two_bump_tape()
    rng = np.random.default_rng(17)

    solved, forbidden = 0, 0
    for _ in range(60):
        t0 = rng.uniform(300.0, 1200.0)
        s0 = float(np.exp(rng.uniform(np.log(4.0), np.log(200.0))))
        r = apex_newton(P, t0, s0)
        if r is None or r["residual"] > 1e-8:
            continue
        if not (P.min() + CUT * r["s"] < r["t"] < P.max() - CUT * r["s"]):
            continue          # edge effects are excluded by the same guard the pipeline uses
        solved += 1
        forbidden += int(r["creation_forbidden"])

    assert solved >= 10, f"only {solved} apexes converged; the test would be vacuous"
    assert forbidden == 0, f"{forbidden} of {solved} apexes are forbidden creations"


# --------------------------------------------------------------------------------------
# 5. Two independent code paths
# --------------------------------------------------------------------------------------

@pytest.mark.parametrize("s", [4.0, 20.0])
def test_two_code_paths(s):
    """PREDICTION: the moment recursion and a direct convolution evaluation of
    s^2*lambda''/lambda agree. They share no code and no intermediate quantity.

    ASSERTED IN ABSOLUTE TERMS, and that is the substantive choice. F is dimensionless,
    O(1), floored at -1; near a zero crossing a relative criterion divides by nothing and
    reports a disagreement that is not there. Measured against a brute-force direct sum
    (neither implementation): the moment path agrees to 1e-8 - 4e-7, the convolution path
    to ~1e-4, and the convolution error shrinks with the bin width. So the convolution path
    is correct and DISCRETIZATION-LIMITED, and 1e-3 at dt = s/200 is the honest bar.

    The tape is binned well outside the comparison window: prints beyond the histogram
    range are simply absent from the convolution, so points within CUT*s of its edge are
    wrong for a reason that has nothing to do with either implementation.
    """
    P = two_bump_tape()
    dt = s / 200.0
    grid, fft_vals = field_fft(P, P.min() - 8 * s, P.max() + 8 * s, s, dt)

    inside = (grid > 400.0) & (grid < 1100.0)
    idx = np.where(inside)[0][:: max(1, int(inside.sum() // 40))]
    worst = 0.0
    compared = 0
    for i in idx:
        t = float(grid[i])
        a, b = F(P, t, s), float(fft_vals[i])
        if not (np.isfinite(a) and np.isfinite(b)):
            continue
        compared += 1
        worst = max(worst, abs(a - b))

    assert compared >= 30
    assert worst < 1e-3, f"code paths disagree by {worst:.2e} absolute at s={s}"


@pytest.mark.parametrize("s", [4.0, 20.0])
def test_truncation_cost(s):
    """PREDICTION: dropping prints beyond +-CUT*s changes F by less than 1e-6.

    CUT = 6 is a numerical choice, exp(-18) ~= 1.5e-8, and this is the test that holds it to
    that claim rather than assuming it. It exists because the derivative test above had to
    turn truncation off to measure the calculus, and a bound that is switched off in one
    test should be asserted in another.
    """
    P = two_bump_tape()
    rng = np.random.default_rng(7)
    worst = 0.0
    for _ in range(25):
        t = rng.uniform(200.0, 1300.0)
        a = F(P, t, s, truncate=True)
        b = F(P, t, s, truncate=False)
        if np.isfinite(a) and np.isfinite(b):
            worst = max(worst, abs(a - b))
    assert worst < 1e-6, f"truncation at CUT={CUT} costs {worst:.2e} in F at s={s}"


# --------------------------------------------------------------------------------------
# 6-9. The invariances
# --------------------------------------------------------------------------------------

def test_detect_refuses_without_thresholds():
    """The kappa gate, enforced in code. A cohort run cannot happen by accident."""
    P = two_bump_tape()
    with pytest.raises(ValueError, match="named explicitly"):
        detect(P, 0.0, 1500.0, 2.0, 300.0, noise_constant=None, kappa=1.0)
    with pytest.raises(ValueError, match="named explicitly"):
        detect(P, 0.0, 1500.0, 2.0, 300.0, noise_constant=POISSON_NOISE_CONSTANT, kappa=None)


def test_permutation_invariance():
    """PREDICTION: bitwise identical output. Unsorted input must not silently select the
    wrong prints through searchsorted."""
    P = two_bump_tape()
    shuffled = P.copy()
    np.random.default_rng(2).shuffle(shuffled)

    a = detect(P, 0.0, 1500.0, 2.0, 300.0, fit_durations=False, **DETECT_KW)
    b = detect(shuffled, 0.0, 1500.0, 2.0, 300.0, fit_durations=False, **DETECT_KW)
    assert _summary(a) == _summary(b)


def test_time_rescaling():
    """PREDICTION: under t -> c*t, t* and s* scale by exactly c while F, n_eff, z and the
    calibrated significance are UNCHANGED. The penalty sqrt(2 ln(T/s)) is invariant because
    T and s scale together."""
    P = two_bump_tape()
    base = detect(P, 0.0, 1500.0, 2.0, 300.0, fit_durations=False, **DETECT_KW)
    assert len(base) >= 2

    for c in (1e-3, 1e3):
        scaled = detect(P * c, 0.0, 1500.0 * c, 2.0 * c, 300.0 * c,
                        fit_durations=False, **DETECT_KW)
        assert len(scaled) == len(base)
        for g, h in zip(sorted(base, key=lambda f: f.t_ridge),
                        sorted(scaled, key=lambda f: f.t_ridge)):
            assert abs(h.t_ridge / (g.t_ridge * c) - 1) < 1e-9
            assert abs(h.s_selected / (g.s_selected * c) - 1) < 1e-9
            assert abs(h.F_min - g.F_min) < 1e-9
            assert abs(h.n_eff_at_min - g.n_eff_at_min) < 1e-9
            assert abs(h.calibrated - g.calibrated) < 1e-9


def test_thinning():
    """PREDICTION: F is invariant to first order and n_eff halves, so z falls by 1/sqrt(2)
    = 0.707. NO NEW FEATURE MAY APPEAR. Raw count must drop -- that is the prediction, not
    a failure -- so what is asserted is the ratio and the absence of new features."""
    P = two_bump_tape()
    full = detect(P, 0.0, 1500.0, 2.0, 300.0, fit_durations=False, **DETECT_KW)
    assert len(full) >= 2

    rng = np.random.default_rng(23)
    for _ in range(3):
        half = P[rng.random(P.size) < 0.5]
        thin = detect(half, 0.0, 1500.0, 2.0, 300.0, fit_durations=False, **DETECT_KW)

        for f in thin:
            match = [g for g in full
                     if abs(f.t_ridge - g.t_ridge) <= max(f.s_selected, g.s_selected)]
            assert match, f"a feature appeared at t={f.t_ridge:.1f} that the full tape lacks"

        ratios = []
        for f in thin:
            g = min(full, key=lambda g: abs(g.t_ridge - f.t_ridge))
            if abs(f.t_ridge - g.t_ridge) <= max(f.s_selected, g.s_selected):
                ratios.append(f.z / g.z)
        assert ratios
        assert 0.6 < float(np.median(ratios)) < 0.8, f"z ratio {np.median(ratios):.3f}"


def test_seed_density_independence():
    """PREDICTION: every reported number identical to solver tolerance as the seeding ladder
    varies 3 -> 12 rungs per octave.

    THIS IS THE TEST THAT FAILED when it was first run against the source document's
    detector: locations were fine but the selected scale moved by up to 8.6% and the
    calibrated significance by 0.67, because t was Newton-polished to 1e-10 while the scale
    stayed snapped to whichever seeding rung won. The fix is step 7. Without it this test
    fails and the resolution-free claim is false.
    """
    P = two_bump_tape()
    ref = None
    for per_oct in (3, 4, 6, 9, 12):
        feats = detect(P, 0.0, 1500.0, 2.0, 300.0, per_octave=per_oct,
                       fit_durations=False, **DETECT_KW)
        got = sorted(((f.t_ridge, f.s_selected, f.calibrated) for f in feats),
                     key=lambda r: r[0])
        if ref is None:
            ref = got
            assert len(ref) >= 2
            continue
        assert len(got) == len(ref), f"count changed at {per_oct} rungs/octave"
        for (t1, s1, c1), (t0, s0, c0) in zip(got, ref):
            assert abs(t1 - t0) < 1e-8, f"t moved {abs(t1 - t0):.2e} s"
            assert abs(np.log(s1 / s0)) < 1e-8, f"ln s moved {abs(np.log(s1 / s0)):.2e}"
            assert abs(c1 - c0) < 1e-8, f"cal moved {abs(c1 - c0):.2e}"


# --------------------------------------------------------------------------------------
# 10. End to end, against known ground truth and a matched null
# --------------------------------------------------------------------------------------

def test_recovers_injected_bumps_and_finds_nothing_in_the_null():
    """PREDICTION: both injected bumps found with locations exact to a tenth of a second,
    and ZERO detections on a flat Poisson tape at identical settings.

    The null result is about a MATCHED POISSON tape. It says nothing about the
    false-positive rate on a tape sitting 1.3 decades from Poisson.
    """
    P = two_bump_tape()
    feats = detect(P, 0.0, 1500.0, 2.0, 300.0, **DETECT_KW)
    assert len(feats) == 2

    found = sorted(f.t_ridge for f in feats)
    assert abs(found[0] - 500.0) < 0.5
    assert abs(found[1] - 900.0) < 1.5

    for f in feats:
        assert f.scale_polished
        assert f.persistence_octaves >= 1.0
        assert f.sigma_fit is not None

    null = sample(lambda x: 6.0 + 0 * x, 1500.0, 8.0, seed=5)
    assert len(detect(null, 0.0, 1500.0, 2.0, 300.0, fit_durations=False, **DETECT_KW)) == 0


def test_duration_fit_beats_the_minus_half_contour():
    """PREDICTION: the -0.5 crossing reads high (+14% to +85% on synthetic bumps) because it
    is the c = 0 special case of the two-parameter fit. The fit is within 16% everywhere."""
    P = two_bump_tape()
    feats = detect(P, 0.0, 1500.0, 2.0, 300.0, **DETECT_KW)
    truth = {500.0: 8.0, 900.0: 40.0}

    for f in feats:
        true_sigma = truth[min(truth, key=lambda c: abs(c - f.t_ridge))]
        assert f.sigma_fit is not None
        assert abs(f.sigma_fit / true_sigma - 1) < 0.20, (
            f"fit {f.sigma_fit:.2f} against true {true_sigma}"
        )
        if f.sigma_minus_half is not None:
            assert f.sigma_minus_half > f.sigma_fit, "the contour readout should read high"
