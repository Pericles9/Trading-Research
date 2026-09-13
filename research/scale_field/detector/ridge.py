#!/usr/bin/env python
# CLOSED BY D26 (2026-09-11). Synthetic tapes only -- do not point this at cohort data.
# Correctness is not in question; the cohort question it answered is. See GOING_LIVE.md.
"""The ridge-first detection pipeline, and the ordering result behind it.

Source: claude/field_feature_extraction_methods.md sections 3, 5, 5.1 and 6.

THE ORDERING IS THE RESULT, so it is worth stating before the code. Building it the natural
way -- trace the F = 0 fingerprint, extract arches, then filter -- produced 157 apexes on a
12,748-print synthetic tape, of which the filter kept ONE (an edge artifact) and lost both
injected bumps. Noise arches have the same SHAPE as real arches, so a topology built on the
raw zero set is a topology of noise and the linking across scales is meaningless before the
noise is gone. Ridges first, calibrate, THEN group.

STEP 7 IS NOT OPTIONAL. Without the scale polish the selected scale stays snapped to
whichever seeding rung won, which moves s* by up to 8.6% as the ladder density varies --
small enough to read as noise, large enough to make every duration comparison across events
meaningless, which is the one thing the detector exists to produce.

NO THRESHOLD HAS A DEFAULT. detect() requires noise_constant and kappa as explicit
arguments, so a cohort run cannot happen here without someone naming both numbers. That
guard stays. As of D26 it is belt-and-braces rather than the load-bearing gate it was: the
cohort question it protected has been closed by measurement, so there is no longer a number
whose arrival would unlock anything. See GOING_LIVE.md.
"""
from __future__ import annotations

from dataclasses import dataclass, field as _dc_field
from typing import Optional

import numpy as np

from .moments import CUT, F, F_t, F_tt, F_u, field_at, moments, n_eff

# Defaults that ARE derived, and match config/scale_field_detector.json
SEED_RUNGS_PER_OCTAVE = 6
N_EFF_FLOOR = 8.0
PERSISTENCE_FLOOR_OCTAVES = 1.0


@dataclass
class Feature:
    """One detected formation. A row, not a region of shading.

    Schema follows section 8 of the source: this table IS the resolution-free
    representation, and any render is generated from it rather than the other way round.
    """

    t_ridge: float
    s_selected: float
    F_min: float
    n_eff_at_min: float
    z: float
    calibrated: float
    kappa_used: float
    noise_constant_used: float
    persistence_octaves: float
    scale_polished: bool
    edge_guard_ok: bool
    sigma_minus_half: Optional[float] = None   # the -0.5 contour readout (a first look)
    sigma_fit: Optional[float] = None          # the two-parameter fit (the measurement)
    c_fit: Optional[float] = None
    fit_rss: Optional[float] = None
    tilt_dt_dlns: Optional[float] = None
    feature_class: str = "bump"
    members: list = _dc_field(default_factory=list, repr=False)


# ---------------------------------------------------------------------------------------
# Step 2 -- Newton polish of t along the ridge (F_t = 0, F_tt > 0)
# ---------------------------------------------------------------------------------------

def ridge_polish(prints, t0, s, iters=60):
    """Newton on F_t = 0 using exact F_t, F_tt. Converges t to ~1e-10*s."""
    t = t0
    for _ in range(iters):
        ft, ftt = F_t(prints, t, s), F_tt(prints, t, s)
        if not np.isfinite(ft) or ftt <= 0:
            return None
        d = -np.clip(ft / ftt, -0.4 * s, 0.4 * s)
        t += d
        if abs(d) < 1e-10 * s:
            break
    final = F_tt(prints, t, s)
    return t if (np.isfinite(final) and final > 0) else None


# ---------------------------------------------------------------------------------------
# Section 3 -- apexes and merge points: one 2x2 Newton solve finds every topological event
# ---------------------------------------------------------------------------------------

def apex_newton(prints, t0, s0, iters=60):
    """Solve {F = 0, F_t = 0} exactly. No grid: pure Newton on two analytic functions.

    The sign of F_u * F_tt at the solution says which kind it is:
      > 0  an arch closing -- a pair annihilating going up in scale
      < 0  a pair CREATED going up, which the causality theorem forbids on a centred
           kernel. A free correctness check on the estimator and the mask, and the thing
           test_forbidden_sign counts.
    """
    t, u = t0, np.log(s0)
    for _ in range(iters):
        s = np.exp(u)
        fp = field_at(prints, t, s)
        if fp is None:
            return None
        r = np.array([fp.F, fp.F_t])
        J = np.array([[fp.F_t, fp.F_u], [fp.F_tt, fp.F_tu]])
        try:
            d = np.linalg.solve(J, -r)
        except np.linalg.LinAlgError:
            return None
        d[0] = np.clip(d[0], -0.6 * s, 0.6 * s)
        d[1] = np.clip(d[1], -0.35, 0.35)
        t, u = t + d[0], u + d[1]
        if abs(d[0]) < 1e-10 * s and abs(d[1]) < 1e-12:
            break
    s = np.exp(u)
    fp = field_at(prints, t, s)
    if fp is None:
        return None
    return dict(t=t, s=s, F=fp.F, F_t=fp.F_t, F_u=fp.F_u, F_tt=fp.F_tt,
                residual=float(max(abs(fp.F), abs(fp.F_t))),
                creation_forbidden=bool(fp.F_u * fp.F_tt < 0))


# ---------------------------------------------------------------------------------------
# Step 7 -- scale polishing. Derivatives were already in hand; see section 5.1.
#   n_eff = sqrt(2)*sum(w)   =>  d n_eff/du = n_eff * M_2       (because dw/du = w*z^2)
#   z     = -F*sqrt(n)/c     =>  dz/du     = -(sqrt(n)/c)*(F_u + F*M_2/2)
#   cal   = z - sqrt(2 ln(T/s)) => dcal/du = dz/du + 1/sqrt(2 ln(T/s))
# ---------------------------------------------------------------------------------------

def dcal_du(prints, t, s, span, noise_constant):
    M = moments(prints, t, s)
    if M is None:
        return np.nan
    n = n_eff(prints, t, s)
    if n <= 0:
        return np.nan
    F_val = M[2] - 1.0
    Fu = M[4] - 2 * M[2] - M[2] ** 2
    penalty = np.sqrt(2 * np.log(max(span / s, np.e)))
    return -(np.sqrt(n) / noise_constant) * (Fu + F_val * M[2] / 2.0) + 1.0 / penalty


def polish_scale(prints, t_seed, u_lo, u_hi, span, noise_constant, iters=80):
    """Bisect dcal/du = 0 along the ridge, re-polishing t at each trial scale."""
    def g(u):
        s = np.exp(u)
        tr = ridge_polish(prints, t_seed, s)
        if tr is None:
            return np.nan, None
        return dcal_du(prints, tr, s, span, noise_constant), tr

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
    tr = ridge_polish(prints, t_seed, s)
    return (tr, s) if tr is not None else None


# ---------------------------------------------------------------------------------------
# Section 6 -- the duration readout. The -0.5 crossing is the c=0 special case of this fit,
# which is exactly why it reads high: +14% to +85% on synthetic bumps, and it fails outright
# on the widest. The fit is within 20% everywhere and within 5% mid-range -- the source's own
# "16% / 6%" table predates its section 5.1 scale polish; corrected 2026-09-09 against
# results/scale_field/artifacts/detector/synthetic_validation.json.
#   F(s) = -( s^2/(sigma^2+s^2) ) / ( 1 + c*sqrt(sigma^2+s^2) ),  c = b*sqrt(2pi)/N
# ---------------------------------------------------------------------------------------

def fit_duration(members):
    """Two-parameter fit of the closed form along the spine. Returns (sigma, c, rss)."""
    from scipy.optimize import least_squares

    m = sorted(members, key=lambda r: r[1])
    s = np.array([r[1] for r in m], dtype=float)
    f = np.array([r[2] for r in m], dtype=float)
    if s.size < 4:
        return None, None, None

    def resid(p):
        sig, c = np.exp(p[0]), np.exp(p[1])
        u = sig ** 2 + s ** 2
        return (-(s ** 2 / u) / (1 + c * np.sqrt(u))) - f

    best = None
    for s0 in (s.min(), np.sqrt(s.min() * s.max()), s.max()):
        for c0 in (-9.0, -5.0, -2.0):
            try:
                r = least_squares(resid, [np.log(s0), c0], method="lm", max_nfev=4000)
            except Exception:
                continue
            if best is None or r.cost < best.cost:
                best = r
    if best is None:
        return None, None, None
    return float(np.exp(best.x[0])), float(np.exp(best.x[1])), float(2 * best.cost)


def _tilt(members):
    """dt/d ln s along the spine -- onset/decay asymmetry as a measured rate.

    A column leaning right as it rises is a sharp onset with a slow decay.
    """
    m = sorted(members, key=lambda r: r[1])
    if len(m) < 3:
        return None
    u = np.log([r[1] for r in m])
    t = np.array([r[0] for r in m], dtype=float)
    if np.ptp(u) < 1e-9:
        return None
    return float(np.polyfit(u, t, 1)[0])


# ---------------------------------------------------------------------------------------
# The pipeline
# ---------------------------------------------------------------------------------------

def detect(prints, t0, t1, s_lo, s_hi, *, noise_constant, kappa,
           per_octave=SEED_RUNGS_PER_OCTAVE, n_eff_floor=N_EFF_FLOOR,
           persistence_floor=PERSISTENCE_FLOOR_OCTAVES, polish_scale_step=True,
           fit_durations=True):
    """Seed -> polish -> guard -> calibrate -> group -> describe -> polish scale.

    noise_constant and kappa are keyword-only and have NO defaults. See the module
    docstring and config/scale_field_detector.json.
    """
    if noise_constant is None or kappa is None:
        raise ValueError(
            "noise_constant and kappa must both be named explicitly. The Poisson value "
            "0.87 is not a default here: on this tape the true sd(F) is larger by roughly "
            "sqrt(A(s)). See the kappa_gate block in config/scale_field_detector.json."
        )

    # Sorted input is a precondition of every searchsorted window in moments.py, and an
    # unsorted array does not raise -- it silently selects the wrong prints. Sorting here
    # makes that impossible and is what test_permutation_invariance actually tests.
    prints = np.sort(np.asarray(prints, dtype=float))
    span = t1 - t0
    n_rungs = int(per_octave * np.log2(s_hi / s_lo)) + 1
    ladder = np.exp(np.linspace(np.log(s_lo), np.log(s_hi), n_rungs))

    pts = []
    for s in ladder:
        # step 3, the edge guard -- CUT*s inside each end. Not optional: the raw pipeline's
        # one survivor on a synthetic tape was an edge effect.
        lo, hi = t0 + CUT * s, t1 - CUT * s
        if hi <= lo:
            continue
        # step 1, seeding. The grid exists ONLY here and never touches a reported number.
        ts = np.linspace(lo, hi, max(40, int((hi - lo) / (0.3 * s))))
        vs = np.array([F(prints, t, s) for t in ts])
        ok = np.isfinite(vs)
        for i in np.where(ok[:-2] & ok[1:-1] & ok[2:])[0] + 1:
            if not (vs[i] < vs[i - 1] and vs[i] < vs[i + 1]):
                continue
            tr = ridge_polish(prints, ts[i], s)          # step 2
            if tr is None or tr < lo or tr > hi:
                continue
            f_val, ne = F(prints, tr, s), n_eff(prints, tr, s)
            if not np.isfinite(f_val) or ne < n_eff_floor or f_val >= 0:
                continue
            z = -f_val * np.sqrt(ne) / noise_constant     # step 4
            cal = z - np.sqrt(2 * np.log(max(span / s, np.e)))
            if cal > kappa:
                pts.append((tr, s, f_val, ne, z, cal))

    # step 5, grouping. Radius is the kernel's own width; no free number.
    pts.sort(key=lambda r: -r[5])
    groups = []
    for r in pts:
        near = [g for g in groups if abs(r[0] - g["t"]) <= max(r[1], g["s"])]
        if not near:
            groups.append(dict(t=r[0], s=r[1], F=r[2], n_eff=r[3], z=r[4], cal=r[5],
                               members=[r]))
        else:
            min(near, key=lambda g: abs(r[0] - g["t"]))["members"].append(r)

    feats = []
    for g in groups:
        scales = [m[1] for m in g["members"]]
        persist = np.log2(max(scales) / min(scales)) if len(scales) > 1 else 0.0
        if persist < persistence_floor:
            continue

        t_sel, s_sel, f_sel, n_sel, z_sel, cal_sel = g["t"], g["s"], g["F"], g["n_eff"], g["z"], g["cal"]
        polished = False
        if polish_scale_step:
            step = np.log(2) / per_octave
            for widen in (1.0, 2.0, 3.0):
                got = polish_scale(prints, t_sel, np.log(s_sel) - widen * step,
                                   np.log(s_sel) + widen * step, span, noise_constant)
                if got:
                    t_sel, s_sel = got
                    f_sel, n_sel = F(prints, t_sel, s_sel), n_eff(prints, t_sel, s_sel)
                    z_sel = -f_sel * np.sqrt(n_sel) / noise_constant
                    cal_sel = z_sel - np.sqrt(2 * np.log(max(span / s_sel, np.e)))
                    polished = True
                    break

        below = [m for m in sorted(g["members"], key=lambda m: m[1]) if m[2] < -0.5]
        sigma_half = below[0][1] if below else None

        sigma_fit = c_fit = rss = None
        if fit_durations:
            sigma_fit, c_fit, rss = fit_duration(g["members"])

        feats.append(Feature(
            t_ridge=float(t_sel), s_selected=float(s_sel), F_min=float(f_sel),
            n_eff_at_min=float(n_sel), z=float(z_sel), calibrated=float(cal_sel),
            kappa_used=float(kappa), noise_constant_used=float(noise_constant),
            persistence_octaves=float(persist), scale_polished=polished,
            edge_guard_ok=True, sigma_minus_half=sigma_half, sigma_fit=sigma_fit,
            c_fit=c_fit, fit_rss=rss, tilt_dt_dlns=_tilt(g["members"]),
            members=g["members"],
        ))

    return sorted(feats, key=lambda f: -f.calibrated)


def feature_rows(features, event_id="synthetic", channel="F", kernel="centred"):
    """The section 8 output schema, as plain dicts ready for a dataframe."""
    return [dict(
        event_id=event_id, channel=channel, kernel=kernel,
        t_ridge=f.t_ridge, s_selected=f.s_selected, sigma_fit=f.sigma_fit,
        c_fit=f.c_fit, fit_rss=f.fit_rss, sigma_minus_half=f.sigma_minus_half,
        F_min=f.F_min, n_eff_at_min=f.n_eff_at_min, z=f.z, calibrated=f.calibrated,
        kappa_used=f.kappa_used, noise_constant_used=f.noise_constant_used,
        persistence_octaves=f.persistence_octaves, tilt_dt_dlns=f.tilt_dt_dlns,
        feature_class=f.feature_class, scale_polished=f.scale_polished,
        edge_guard_ok=f.edge_guard_ok,
    ) for f in features]
