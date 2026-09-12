#!/usr/bin/env python
"""The moment machinery: closed-form derivatives of the scale field to any order.

WHAT THIS IS. lambda-hat(t,s) is a sum of Gaussians over the prints, so F is an ANALYTIC
function of (t, ln s) with closed-form derivatives of every order. There is no grid
anywhere in the mathematics. The grid in the panel build is a rendering choice that
leaked into the measurement; nothing here inherits it.

Source: claude/field_feature_extraction_methods.md section 1. Every formula below was
checked against central differences in research/scale_field/derivations/01_verify_calculus.py
(max relative error 2.8e-9) before being promoted here.

THE CONVENTION IS DECLARED ONCE, HERE, AND NEVER RESTATED IN PROSE:

    z_i = (t - t_i) / s

With the other sign, every ODD t-derivative flips -- F_t and F_tu are wrong while F, F_u,
F_tt and F_uu are unchanged, so the field itself looks perfectly fine and the bug is
invisible in every rendered output. The author of the source document shipped exactly that
bug. test_detector.py::test_z_convention is what holds this file to it: it checks F_t
against a central difference of F, which is convention-independent, so a flipped z fails
loudly instead of silently.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

# Kernel truncation. Derived, not chosen: exp(-18) ~= 1.5e-8. config/scale_field_detector.json
CUT = 6.0

# The Poisson sampling-noise constant, sd(F) ~= 0.87/sqrt(n_eff). It is defined here so it
# can be named, and it is NOT a default anywhere: on a tape whose Allan factor runs 5.99 at
# 15.6 ms to 1245 at 4096 s the true sd is larger by roughly sqrt(A(s)), so a z built on
# this constant is inflated ~2.4x at the fine end and ~35x at the coarse end. See the
# kappa_gate block in config/scale_field_detector.json.
POISSON_NOISE_CONSTANT = 0.87

SQRT2 = np.sqrt(2.0)

# Minimum prints inside the truncated window for the moments to be defined at all. This is a
# numerical guard on the ratio M_k = sum(w z^k)/sum(w), not the statistical n_eff floor.
MIN_PRINTS_IN_WINDOW = 3


@dataclass(frozen=True)
class FieldPoint:
    """Everything the detector needs at one (t, s), from one pass over the local prints."""

    t: float
    s: float
    F: float
    F_t: float
    F_u: float
    F_tt: float
    F_tu: float
    F_uu: float
    n_eff: float
    M: np.ndarray


def moments(prints: np.ndarray, t: float, s: float, K: int = 6, truncate: bool = True):
    """Kernel-weighted moments M_0..M_K at (t, s).  M_0 = 1 by construction.

    `prints` must be sorted ascending. With truncate=True only prints within +-CUT*s are
    touched, which is what makes one evaluation O(local count) rather than O(N).
    Returns None where the window is too thin for the ratio to be meaningful.
    """
    if truncate:
        a, b = np.searchsorted(prints, [t - CUT * s, t + CUT * s])
        if b - a < MIN_PRINTS_IN_WINDOW:
            return None
        local = prints[a:b]
    else:
        local = prints
        if local.size < MIN_PRINTS_IN_WINDOW:
            return None

    z = (t - local) / s  # THE CONVENTION. See module docstring.
    w = np.exp(-0.5 * z * z)
    W = w.sum()
    if W <= 0:
        return None

    out = np.empty(K + 1)
    zz = np.ones_like(z)
    for k in range(K + 1):
        out[k] = (w * zz).sum() / W
        zz = zz * z
    return out


def lam_hat(prints: np.ndarray, t: float, s: float) -> float:
    """The smoothed trade rate itself: lambda-hat = (1/(s*sqrt(2pi))) * sum_i w_i.

    Present because the zero-sum correctness check needs it -- F*lambda-hat = s^2*lambda'',
    and the integral of lambda'' over the line is exactly zero, so the lambda-hat-weighted
    integral of F must vanish at every scale.
    """
    a, b = np.searchsorted(prints, [t - CUT * s, t + CUT * s])
    if b - a < 1:
        return 0.0
    z = (t - prints[a:b]) / s
    return float(np.exp(-0.5 * z * z).sum() / (s * np.sqrt(2 * np.pi)))


def n_eff(prints: np.ndarray, t: float, s: float) -> float:
    """n_eff = sqrt(2) * sum_i exp(-z_i^2/2).

    Exactly 2*sqrt(pi)*s*lambda for a homogeneous process, but computed from the prints
    directly -- so the admissibility boundary needs no lambda-hat, no bandwidth for
    lambda-hat, and no smoothing choice. A whole layer of arbitrariness in s_min disappears
    and the boundary becomes a level set of an exactly computable function.
    """
    a, b = np.searchsorted(prints, [t - CUT * s, t + CUT * s])
    if b - a < 1:
        return 0.0
    z = (t - prints[a:b]) / s
    return float(SQRT2 * np.exp(-0.5 * z * z).sum())


# --------------------------------------------------------------------------------------
# The two recurrences that generate everything, and the six derivatives written out.
#   dM_k/dt = ( -M_{k+1} + k*M_{k-1} + M_k*M_1 ) / s
#   dM_k/du =   M_{k+2}  - k*M_k     - M_k*M_2          u = ln s
# --------------------------------------------------------------------------------------


def dM_du(M: np.ndarray, k: int) -> float:
    return M[k + 2] - k * M[k] - M[k] * M[2]


def _field_from_moments(M: np.ndarray, s: float):
    """The six derivatives from one moment vector. Returns (F, F_t, F_u, F_tt, F_tu, F_uu)."""
    F = M[2] - 1.0
    F_t = (-M[3] + 2 * M[1] + M[2] * M[1]) / s
    F_u = M[4] - 2 * M[2] - M[2] ** 2

    # dM_1/dt, dM_2/dt, dM_3/dt with the 1/s factored out
    dM1 = -M[2] + 1.0 + M[1] ** 2
    dM2 = -M[3] + 2 * M[1] + M[2] * M[1]
    dM3 = -M[4] + 3 * M[2] + M[3] * M[1]
    F_tt = (-dM3 + 2 * dM1 + M[2] * dM1 + M[1] * dM2) / s ** 2

    A = -M[3] + 2 * M[1] + M[2] * M[1]
    dM1u = dM_du(M, 1)
    dM2u = dM_du(M, 2)
    dM3u = dM_du(M, 3)
    dAu = -dM3u + 2 * dM1u + M[2] * dM1u + M[1] * dM2u
    F_tu = (dAu - A) / s

    dM4u = dM_du(M, 4)
    F_uu = dM4u - 2 * dM2u - 2 * M[2] * dM2u

    return F, F_t, F_u, F_tt, F_tu, F_uu


def field_at(prints: np.ndarray, t: float, s: float, truncate: bool = True):
    """One pass over the local prints -> F and all five derivatives plus n_eff.

    This is the entry point the pipeline uses; calling the scalar helpers below in sequence
    recomputes the moments each time and is for tests and readability, not for hot loops.
    """
    M = moments(prints, t, s, K=6, truncate=truncate)
    if M is None:
        return None
    F, F_t, F_u, F_tt, F_tu, F_uu = _field_from_moments(M, s)
    return FieldPoint(
        t=float(t), s=float(s), F=F, F_t=F_t, F_u=F_u, F_tt=F_tt, F_tu=F_tu, F_uu=F_uu,
        n_eff=n_eff(prints, t, s), M=M,
    )


# --- scalar helpers -------------------------------------------------------------------

def _m(prints, t, s, truncate=True):
    M = moments(prints, t, s, K=6, truncate=truncate)
    return M


def F(prints, t, s, truncate=True) -> float:
    M = _m(prints, t, s, truncate)
    return np.nan if M is None else M[2] - 1.0


def F_t(prints, t, s, truncate=True) -> float:
    M = _m(prints, t, s, truncate)
    return np.nan if M is None else _field_from_moments(M, s)[1]


def F_u(prints, t, s, truncate=True) -> float:
    M = _m(prints, t, s, truncate)
    return np.nan if M is None else _field_from_moments(M, s)[2]


def F_tt(prints, t, s, truncate=True) -> float:
    M = _m(prints, t, s, truncate)
    return np.nan if M is None else _field_from_moments(M, s)[3]


def F_tu(prints, t, s, truncate=True) -> float:
    M = _m(prints, t, s, truncate)
    return np.nan if M is None else _field_from_moments(M, s)[4]


def F_uu(prints, t, s, truncate=True) -> float:
    M = _m(prints, t, s, truncate)
    return np.nan if M is None else _field_from_moments(M, s)[5]


# --- an independent code path, for the agreement test ---------------------------------

def field_fft(prints: np.ndarray, t0: float, t1: float, s: float, dt: float):
    """F on a grid by direct convolution -- a SECOND, independent implementation.

    Deliberately shares no code with the moment recursion above. F = s^2 * lam'' / lam,
    with lam and lam'' each formed by convolving the binned counting process with the
    Gaussian and with the Gaussian's exact second derivative:

        g(x)   = exp(-x^2/2s^2) / (s*sqrt(2pi))
        g''(x) = g(x) * (x^2 - s^2) / s^4

    Returns (grid_t, F_grid). The dt^2 scaling of the second-derivative kernel is where the
    source document's author put a bug this week, which is the reason this path exists.
    """
    n = int(np.ceil((t1 - t0) / dt))
    edges = t0 + dt * np.arange(n + 1)
    counts, _ = np.histogram(prints, bins=edges)
    centres = 0.5 * (edges[:-1] + edges[1:])

    half = int(np.ceil(CUT * s / dt))
    x = dt * np.arange(-half, half + 1)
    g = np.exp(-0.5 * (x / s) ** 2) / (s * np.sqrt(2 * np.pi))
    g2 = g * (x ** 2 - s ** 2) / s ** 4

    lam = np.convolve(counts, g, mode="same")
    lam2 = np.convolve(counts, g2, mode="same")
    with np.errstate(divide="ignore", invalid="ignore"):
        out = s ** 2 * lam2 / lam
    return centres, out
