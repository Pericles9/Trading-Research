#!/usr/bin/env python
"""The interval channel: G, its derivatives, and a two-sided ridge detector.

Source: claude/field_feature_extraction_methods.md section 7, and the brief of 2026-09-09.

WHY A SECOND CHANNEL EXISTS AT ALL. The rate channel sees only lambda-hat. Two tapes with
identical lambda-hat(t) -- one Poisson, one violently clustered inside -- produce IDENTICAL
F fields. That blindness is structural, not a tuning problem, and the interval distribution
is the only place the difference lives.

    G(t,s) = E_w[ log10 dt_i ]  -  ( -log10 lambda-hat(t,s) )

the kernel-weighted mean log-interval against what the local rate implies.

THE BASELINE IS NOT ZERO, AND THIS IS THE LOAD-BEARING FACT. Under a locally homogeneous
Poisson process dt ~ Exp(lambda), so E[ln dt] = -ln lambda - gamma and

    G_0 = -gamma / ln 10 = -0.2506628...      (gamma = Euler-Mascheroni)

G's null is that CONSTANT. Building anything on "G = 0 is the null" is the same error this
arc has already made twice with a Poisson reference, one statistic removed. verify_baseline()
reproduces the constant numerically rather than trusting the algebra, and Gate 0 in the
validation script runs it.

CONVENTION. z_i = (t - t_i)/s, imported from moments.py, declared there, not restated here.

WHAT IS DELIBERATELY NOT BUILT: the apex/merge Newton solve. See the note above
detect_interval() -- the omission is a decision, not an oversight.
"""
from __future__ import annotations

from dataclasses import dataclass, field as _dc_field
from typing import Optional

import numpy as np

from .moments import CUT, MIN_PRINTS_IN_WINDOW, n_eff

LN10 = np.log(10.0)
EULER_MASCHERONI = 0.5772156649015328606

# G's Poisson baseline. A CONSTANT, not a zero.
G0 = -EULER_MASCHERONI / LN10

# sd of log10 of an exponential interval: sqrt(pi^2/6)/ln10. This is the 0.5570 decades
# already on this programme's record from the ITT work, arrived at independently here.
INTERVAL_SD_DECADES = np.sqrt(np.pi ** 2 / 6.0) / LN10

# Measured by Monte Carlo in measure_noise_constant(); see the validation artifact. It is a
# POISSON constant and carries exactly the same health warning as 0.87 does for F: it is not
# the constant to calibrate real tape with. Nothing here defaults to it.
POISSON_NOISE_CONSTANT_G = None


# ---------------------------------------------------------------------------------------
# Carriers: a print carries an interval only if it has a predecessor
# ---------------------------------------------------------------------------------------

def interval_carriers(prints, collapse_exact_ties: bool = True):
    """(t_i, x_i = log10 dt_i) for every print that has a predecessor.

    Returns (carrier_times, x, n_dropped_zero_intervals).

    ZERO INTERVALS. log10(0) is undefined, so simultaneous prints cannot carry an interval.
    On synthetic tapes exact ties are measure-zero. On the real tape they are NOT -- they are
    order fragmentation, one order reported as several prints -- and how to collapse that is
    an OPEN QUESTION owned by the concurrent gates thread (identity-based vs time-tolerance).
    `collapse_exact_ties` drops exactly-equal timestamps and nothing else. IT IS TEST
    SCAFFOLDING SO THAT SYNTHETIC ROBUSTNESS CAN BE PROBED, NOT A PROPOSED CONVENTION, and it
    must not be read as one. See GOING_LIVE.md.
    """
    p = np.sort(np.asarray(prints, dtype=float))
    dt = np.diff(p)
    carriers, x = p[1:], dt
    if collapse_exact_ties:
        ok = dt > 0
        n_dropped = int((~ok).sum())
        carriers, x = carriers[ok], dt[ok]
    else:
        n_dropped = 0
    return carriers, np.log10(x), n_dropped


# ---------------------------------------------------------------------------------------
# The moment machinery, extended with the covariate family N_k
#   M_k = sum(w z^k)/sum(w)          (already in moments.py, recomputed here over the
#   N_k = sum(w z^k x)/sum(w)         SAME carrier set so the identities below are exact)
#
# The recurrences are identical in shape to the M_k pair, because x_i is a per-print
# constant that rides through both derivatives untouched:
#   dN_k/dt = ( -N_{k+1} + k*N_{k-1} + N_k*M_1 ) / s
#   dN_k/du =   N_{k+2}  - k*N_k     - N_k*M_2
# ---------------------------------------------------------------------------------------

@dataclass(frozen=True)
class IntervalPoint:
    t: float
    s: float
    G: float
    D: float          # departure from the Poisson baseline, G - G0
    G_t: float
    G_u: float
    G_tt: float
    n_eff: float
    M: np.ndarray
    N: np.ndarray


def gmoments(carriers, x, t, s, K: int = 4, truncate: bool = True):
    """(M_0..M_K, N_0..N_K, W) at (t, s) from one pass over the local carriers."""
    if truncate:
        a, b = np.searchsorted(carriers, [t - CUT * s, t + CUT * s])
        if b - a < MIN_PRINTS_IN_WINDOW:
            return None
        loc_t, loc_x = carriers[a:b], x[a:b]
    else:
        loc_t, loc_x = carriers, x
        if loc_t.size < MIN_PRINTS_IN_WINDOW:
            return None

    z = (t - loc_t) / s          # THE CONVENTION, from moments.py
    w = np.exp(-0.5 * z * z)
    W = w.sum()
    if W <= 0:
        return None

    M = np.empty(K + 1)
    N = np.empty(K + 1)
    zz = np.ones_like(z)
    for k in range(K + 1):
        M[k] = (w * zz).sum() / W
        N[k] = (w * zz * loc_x).sum() / W
        zz = zz * z
    return M, N, float(W)


def _G_from(M, N, W, s):
    """G and its first two t-derivatives plus the u-derivative, from one moment pass.

    lambda-hat = W / (s*sqrt(2pi)), so log10 lambda-hat = (ln W - ln s - ln sqrt(2pi))/ln10
    and G = N_0 + log10 lambda-hat.
    """
    lam = W / (s * np.sqrt(2 * np.pi))
    G = N[0] + np.log10(lam)

    G_t = (-N[1] + N[0] * M[1] - M[1] / LN10) / s

    # G_u = N_2 - N_0*M_2 + F/ln10 -- the rate channel reappears inside the interval
    # channel's scale derivative, which is why the two are not independent by construction
    # and why the rate-hump cross-check in the validation is not a formality.
    G_u = N[2] - N[0] * M[2] + (M[2] - 1.0) / LN10

    dN0_dt = (-N[1] + N[0] * M[1]) / s
    dN1_dt = (-N[2] + N[0] + N[1] * M[1]) / s
    dM1_dt = (-M[2] + 1.0 + M[1] ** 2) / s
    dA_dt = -dN1_dt + dN0_dt * M[1] + N[0] * dM1_dt - dM1_dt / LN10
    G_tt = dA_dt / s

    return G, G_t, G_u, G_tt


def interval_at(carriers, x, t, s, truncate: bool = True):
    out = gmoments(carriers, x, t, s, K=4, truncate=truncate)
    if out is None:
        return None
    M, N, W = out
    G, G_t, G_u, G_tt = _G_from(M, N, W, s)
    return IntervalPoint(t=float(t), s=float(s), G=G, D=G - G0, G_t=G_t, G_u=G_u,
                         G_tt=G_tt, n_eff=n_eff(carriers, t, s), M=M, N=N)


def G(carriers, x, t, s, truncate=True) -> float:
    out = gmoments(carriers, x, t, s, K=4, truncate=truncate)
    return np.nan if out is None else _G_from(*out, s)[0]


def G_t(carriers, x, t, s, truncate=True) -> float:
    out = gmoments(carriers, x, t, s, K=4, truncate=truncate)
    return np.nan if out is None else _G_from(*out, s)[1]


def G_u(carriers, x, t, s, truncate=True) -> float:
    out = gmoments(carriers, x, t, s, K=4, truncate=truncate)
    return np.nan if out is None else _G_from(*out, s)[2]


def G_tt(carriers, x, t, s, truncate=True) -> float:
    out = gmoments(carriers, x, t, s, K=4, truncate=truncate)
    return np.nan if out is None else _G_from(*out, s)[3]


# ---------------------------------------------------------------------------------------
# Gate 0 -- the baseline constant, reproduced numerically rather than trusted
# ---------------------------------------------------------------------------------------

def verify_baseline(draw_counts=(10 ** 3, 10 ** 4, 10 ** 5, 10 ** 6, 10 ** 7), seed=101):
    """Monte Carlo E[log10 Exp(1)] against -gamma/ln10, and how many draws it takes.

    Same discipline the 0.5570-decade constant got elsewhere in this programme: verified
    over millions of draws before it was trusted.
    """
    rng = np.random.default_rng(seed)
    rows = []
    for n in draw_counts:
        vals = np.log10(rng.exponential(1.0, size=int(n)))
        mean = float(vals.mean())
        rows.append(dict(
            n_draws=int(n), measured_mean=mean, predicted=float(G0),
            abs_error=abs(mean - G0),
            measured_sd=float(vals.std(ddof=1)),
            predicted_sd=float(INTERVAL_SD_DECADES),
            standard_error=float(vals.std(ddof=1) / np.sqrt(n)),
        ))
    return rows


def measure_noise_constant(n_eff_targets=(8, 16, 32, 64, 128, 256), draws=4000, seed=202):
    """sd(G) * sqrt(n_eff) on homogeneous Poisson tape, per n_eff.

    THE CONSTANT IS NOT ASSUMED EQUAL TO F's. It cannot be: G is built from a different
    statistic. Analytically two terms contribute -- the weighted mean log-interval, whose
    sd is 0.5570/sqrt(n_eff), and log10 lambda-hat, whose sd is 0.4343/sqrt(n_eff) -- and
    they are NEGATIVELY correlated, because a window with more prints has shorter intervals.
    So the constant must land below sqrt(0.5570^2 + 0.4343^2) = 0.706 and is measured here
    rather than derived through that correlation.

    Returns rows of (n_eff_target, achieved n_eff, sd(G), sd*sqrt(n_eff)).
    """
    rng = np.random.default_rng(seed)
    rows = []
    for target in n_eff_targets:
        lam = 1.0
        s = target / (2 * np.sqrt(np.pi) * lam)   # n_eff = 2*sqrt(pi)*s*lambda
        span = 2 * CUT * s + 40.0 * s
        vals, achieved = [], []
        for _ in range(draws):
            n = rng.poisson(lam * span)
            p = np.sort(rng.random(n) * span)
            if p.size < 8:
                continue
            c, xx, _ = interval_carriers(p)
            if c.size < 8:
                continue
            t = span / 2.0
            g = G(c, xx, t, s)
            if np.isfinite(g):
                vals.append(g)
                achieved.append(n_eff(c, t, s))
        vals = np.asarray(vals)
        rows.append(dict(
            n_eff_target=float(target), n_eff_achieved=float(np.mean(achieved)),
            n_samples=int(vals.size), mean_G=float(vals.mean()), sd_G=float(vals.std(ddof=1)),
            constant=float(vals.std(ddof=1) * np.sqrt(np.mean(achieved))),
        ))
    return rows


# ---------------------------------------------------------------------------------------
# The detector.
#
# DESIGN DECISION 1 -- a parallel implementation, not a generalised ridge.py.
#   ridge.py is tested code carrying 18 passing assertions and I am not threading flags
#   through its body mid-build. The two detectors share an ARCHITECTURE (seed -> Newton
#   polish t -> edge guard -> calibrate -> group -> describe -> polish scale) and differ in
#   three places that are structural rather than parametric: two-sided seeding, a baseline
#   that is a constant rather than an arithmetic zero, and a different noise constant.
#   Mirroring the stages explicitly is more honest than a flag-riddled shared body. If a
#   third channel ever appears, factoring the common scan out earns its keep; with two it
#   does not.
#
# DESIGN DECISION 2 -- NO apex/merge Newton solve for G, and the reason is not effort.
#   For F the apex object is {F = 0, F_t = 0}, and F = 0 is ARITHMETIC: a locally flat rate
#   gives F = 0 exactly, with no distributional assumption, because the Gaussian satisfies
#   the heat equation. The corresponding object for G would be {G - G0 = 0, G_t = 0}, and
#   G0 is a POISSON constant. Its zero contour, its arches and its merge topology would
#   therefore all be Poisson-referenced -- precisely the dependence that has already killed
#   two constructions in this arc. The RIDGE does not have that problem: G0 is a constant,
#   so d(G - G0)/dt = dG/dt and the ridge LOCATIONS are invariant to the baseline entirely.
#   Only the magnitudes z and cal depend on G0. So the reference-free part of the machinery
#   is built and the reference-dependent part is not.
# ---------------------------------------------------------------------------------------

@dataclass
class IntervalFeature:
    t_ridge: float
    s_selected: float
    direction: str            # "clumped" (G below baseline) or "regular" (G above)
    G_at_ridge: float
    D_at_ridge: float         # G - G0
    n_eff_at_ridge: float
    z: float
    calibrated: float
    kappa_used: float
    noise_constant_used: float
    baseline_used: float
    persistence_octaves: float
    scale_polished: bool
    tilt_dt_dlns: Optional[float] = None
    members: list = _dc_field(default_factory=list, repr=False)


def _ridge_polish_G(carriers, x, t0, s, sign, iters=60):
    """Newton on d(sign*D)/dt = 0 with positive curvature -- an extremum of the departure."""
    t = t0
    for _ in range(iters):
        gt, gtt = G_t(carriers, x, t, s), G_tt(carriers, x, t, s)
        if not np.isfinite(gt) or sign * gtt <= 0:
            return None
        d = -np.clip(gt / gtt, -0.4 * s, 0.4 * s)
        t += d
        if abs(d) < 1e-10 * s:
            break
    final = G_tt(carriers, x, t, s)
    return t if (np.isfinite(final) and sign * final > 0) else None


def _dcal_du_G(carriers, x, t, s, span, noise_constant, sign, baseline):
    out = gmoments(carriers, x, t, s, K=4)
    if out is None:
        return np.nan
    M, N, W = out
    Gv, _, Gu, _ = _G_from(M, N, W, s)
    D = Gv - baseline
    n = n_eff(carriers, t, s)
    if n <= 0:
        return np.nan
    penalty = np.sqrt(2 * np.log(max(span / s, np.e)))
    # exactly the F-channel form with D in F's place: z = -sign*D*sqrt(n)/c
    return -(sign * np.sqrt(n) / noise_constant) * (Gu + D * M[2] / 2.0) + 1.0 / penalty


def _polish_scale_G(carriers, x, t_seed, u_lo, u_hi, span, noise_constant, sign, baseline,
                    iters=80):
    def g(u):
        s = np.exp(u)
        tr = _ridge_polish_G(carriers, x, t_seed, s, sign)
        if tr is None:
            return np.nan, None
        return _dcal_du_G(carriers, x, tr, s, span, noise_constant, sign, baseline), tr

    a, b = u_lo, u_hi
    ga, _ = g(a)
    gb, _ = g(b)
    if not (np.isfinite(ga) and np.isfinite(gb)) or ga * gb > 0:
        return None
    for _ in range(iters):
        m = 0.5 * (a + b)
        gm, _ = g(m)
        if not np.isfinite(gm):
            return None
        if ga * gm <= 0:
            b = m
        else:
            a, ga = m, gm
        if b - a < 1e-12:
            break
    u = 0.5 * (a + b)
    s = np.exp(u)
    tr = _ridge_polish_G(carriers, x, t_seed, s, sign)
    return (tr, s) if tr is not None else None


def detect_interval(prints, t0, t1, s_lo, s_hi, *, noise_constant, kappa,
                    per_octave=6, n_eff_floor=8.0, persistence_floor=1.0,
                    baseline=G0, directions=("clumped", "regular"),
                    polish_scale_step=True):
    """Two-sided ridge detection on the interval channel.

    noise_constant and kappa are keyword-only with NO defaults, exactly as in ridge.detect.
    The Poisson value measured by measure_noise_constant() is a Poisson value; it is not the
    constant to calibrate real tape with, and this signature is what stops it becoming one
    by default.

    `baseline` defaults to G0 = -gamma/ln10 rather than to zero. That default is the whole
    point of Gate 0 and is not a free parameter.
    """
    if noise_constant is None or kappa is None:
        raise ValueError(
            "noise_constant and kappa must both be named explicitly. G's Poisson noise "
            "constant is measured by measure_noise_constant() and is a POISSON constant; "
            "see the kappa_gate block in config/scale_field_detector.json and GOING_LIVE.md."
        )

    carriers, x, _ = interval_carriers(prints)
    span = t1 - t0
    n_rungs = int(per_octave * np.log2(s_hi / s_lo)) + 1
    ladder = np.exp(np.linspace(np.log(s_lo), np.log(s_hi), n_rungs))

    sign_of = {"clumped": +1.0, "regular": -1.0}
    feats = []

    for direction in directions:
        sign = sign_of[direction]
        pts = []
        for s in ladder:
            lo, hi = t0 + CUT * s, t1 - CUT * s
            if hi <= lo:
                continue
            ts = np.linspace(lo, hi, max(40, int((hi - lo) / (0.3 * s))))
            vs = np.array([sign * (G(carriers, x, t, s) - baseline) for t in ts])
            ok = np.isfinite(vs)
            for i in np.where(ok[:-2] & ok[1:-1] & ok[2:])[0] + 1:
                if not (vs[i] < vs[i - 1] and vs[i] < vs[i + 1]):
                    continue
                tr = _ridge_polish_G(carriers, x, ts[i], s, sign)
                if tr is None or tr < lo or tr > hi:
                    continue
                gv = G(carriers, x, tr, s)
                ne = n_eff(carriers, tr, s)
                if not np.isfinite(gv) or ne < n_eff_floor:
                    continue
                D = gv - baseline
                if sign * D >= 0:          # must be a departure in the sought direction
                    continue
                z = -sign * D * np.sqrt(ne) / noise_constant
                cal = z - np.sqrt(2 * np.log(max(span / s, np.e)))
                if cal > kappa:
                    pts.append((tr, s, gv, D, ne, z, cal))

        pts.sort(key=lambda r: -r[6])
        groups = []
        for r in pts:
            near = [g for g in groups if abs(r[0] - g["t"]) <= max(r[1], g["s"])]
            if not near:
                groups.append(dict(t=r[0], s=r[1], G=r[2], D=r[3], n_eff=r[4], z=r[5],
                                   cal=r[6], members=[r]))
            else:
                min(near, key=lambda g: abs(r[0] - g["t"]))["members"].append(r)

        for g in groups:
            scales = [m[1] for m in g["members"]]
            persist = np.log2(max(scales) / min(scales)) if len(scales) > 1 else 0.0
            if persist < persistence_floor:
                continue

            t_sel, s_sel = g["t"], g["s"]
            g_sel, d_sel, n_sel, z_sel, cal_sel = g["G"], g["D"], g["n_eff"], g["z"], g["cal"]
            polished = False
            if polish_scale_step:
                step = np.log(2) / per_octave
                for widen in (1.0, 2.0, 3.0):
                    got = _polish_scale_G(carriers, x, t_sel, np.log(s_sel) - widen * step,
                                          np.log(s_sel) + widen * step, span,
                                          noise_constant, sign, baseline)
                    if got:
                        t_sel, s_sel = got
                        g_sel = G(carriers, x, t_sel, s_sel)
                        d_sel = g_sel - baseline
                        n_sel = n_eff(carriers, t_sel, s_sel)
                        z_sel = -sign * d_sel * np.sqrt(n_sel) / noise_constant
                        cal_sel = z_sel - np.sqrt(2 * np.log(max(span / s_sel, np.e)))
                        polished = True
                        break

            m = sorted(g["members"], key=lambda r: r[1])
            tilt = None
            if len(m) >= 3:
                u = np.log([r[1] for r in m])
                tt = np.array([r[0] for r in m])
                if np.ptp(u) > 1e-9:
                    tilt = float(np.polyfit(u, tt, 1)[0])

            feats.append(IntervalFeature(
                t_ridge=float(t_sel), s_selected=float(s_sel), direction=direction,
                G_at_ridge=float(g_sel), D_at_ridge=float(d_sel),
                n_eff_at_ridge=float(n_sel), z=float(z_sel), calibrated=float(cal_sel),
                kappa_used=float(kappa), noise_constant_used=float(noise_constant),
                baseline_used=float(baseline), persistence_octaves=float(persist),
                scale_polished=polished, tilt_dt_dlns=tilt, members=g["members"],
            ))

    return sorted(feats, key=lambda f: -f.calibrated)


def interval_feature_rows(features, event_id="synthetic"):
    return [dict(
        event_id=event_id, channel="G", kernel="centred", direction=f.direction,
        t_ridge=f.t_ridge, s_selected=f.s_selected, G_at_ridge=f.G_at_ridge,
        D_at_ridge=f.D_at_ridge, n_eff_at_ridge=f.n_eff_at_ridge, z=f.z,
        calibrated=f.calibrated, kappa_used=f.kappa_used,
        noise_constant_used=f.noise_constant_used, baseline_used=f.baseline_used,
        persistence_octaves=f.persistence_octaves, tilt_dt_dlns=f.tilt_dt_dlns,
        scale_polished=f.scale_polished,
    ) for f in features]
