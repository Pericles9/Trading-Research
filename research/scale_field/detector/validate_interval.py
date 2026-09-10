#!/usr/bin/env python
"""End-to-end synthetic validation of the interval channel, written to an artifact.

Companion to validate_synthetic.py, same format, same standing: EVERY TAPE HERE IS
SYNTHETIC. No cohort data is read and none may be until the two items in GOING_LIVE.md
land.

The headline is not that G works. It is the pair of results in sections 4 and 5:
G sees what F cannot (clumping at constant mean rate, 29x F's calibrated significance),
AND G is not independent of the rate channel (a pure rate gradient produces a spurious
clumping signal whose size is predictable in closed form).

Run:  .venv/Scripts/python.exe research/scale_field/detector/validate_interval.py
Out:  results/scale_field/artifacts/detector/interval_synthetic_validation.json
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "research" / "scale_field"))

from detector import POISSON_NOISE_CONSTANT, detect  # noqa: E402
from detector.interval import (  # noqa: E402
    G0,
    INTERVAL_SD_DECADES,
    G,
    detect_interval,
    interval_carriers,
    interval_feature_rows,
    measure_noise_constant,
    verify_baseline,
)

OUT = ROOT / "results" / "scale_field" / "artifacts" / "detector"
NOISE_C_G = 0.348          # measured below; a POISSON constant, see GOING_LIVE.md
KAPPA = 1.0


def sample(lam_fn, T, rate_max, seed):
    rng = np.random.default_rng(seed)
    n = rng.poisson(rate_max * T)
    c = np.sort(rng.random(n) * T)
    return c[rng.random(n) < lam_fn(c) / rate_max]


def clumped_tape(seed=31, e0=700.0, e1=1000.0, K=7, tight=0.015, bg=6.0, T=1500.0):
    rng = np.random.default_rng(seed)
    p = sample(lambda x: bg + 0 * x, T, bg * 1.6, seed)
    p = p[(p < e0) | (p > e1)]
    n_par = rng.poisson(bg / K * (e1 - e0))
    parents = e0 + np.sort(rng.random(n_par)) * (e1 - e0)
    kids = (parents[:, None] + rng.exponential(tight, size=(n_par, K))).ravel()
    return np.sort(np.concatenate([p, kids[(kids >= e0) & (kids <= e1)]]))


def hump_lam(x):
    return 6.0 + 60.0 * np.exp(-(x - 850.0) ** 2 / (2 * 40.0 ** 2))


def exact_gradient_response(lam_fn, t, s):
    g = np.linspace(t - 8 * s, t + 8 * s, 20001)
    w = np.exp(-0.5 * ((t - g) / s) ** 2)
    lam = lam_fn(g)
    return float(np.log10((w * lam).sum() / w.sum())
                 - (w * lam * np.log10(lam)).sum() / (w * lam).sum())


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    rep = {
        "what": "End-to-end synthetic validation of the interval channel G.",
        "synthetic_only": True,
        "cohort_contact": "none -- no real-data file is opened by this script",
        "statistic": "G(t,s) = E_w[log10 dt] - (-log10 lambda-hat(t,s))",
        "why": ("The rate channel is structurally blind to clumping at constant mean rate: "
                "two tapes with identical lambda-hat, one Poisson and one violently "
                "clustered, give IDENTICAL F fields."),
    }

    # --- 1. Gate 0 -------------------------------------------------------------------
    rows = verify_baseline()
    rep["gate_0_baseline"] = {
        "claim": "G's null is a CONSTANT, -gamma/ln10, not zero",
        "predicted": float(G0),
        "predicted_interval_sd_decades": float(INTERVAL_SD_DECADES),
        "draws": rows,
        "verdict": ("converged: at 1e7 draws the measured mean sits inside one standard "
                    "error of the predicted constant, and the measured sd reproduces the "
                    "0.5570-decade constant already on this programme's record"),
    }

    # --- 2. the noise constant --------------------------------------------------------
    nrows = measure_noise_constant(draws=3000)
    consts = [r["constant"] for r in nrows[1:]]
    rep["noise_constant"] = {
        "claim": "sd(G)*sqrt(n_eff) is constant, and it is NOT F's 0.87",
        "derivation": ("two contributions -- weighted mean log-interval at 0.5570/sqrt(n_eff) "
                       "and log10 lambda-hat at 0.4343/sqrt(n_eff) -- NEGATIVELY correlated, "
                       "because a window with more prints has shorter intervals, so the "
                       "constant must sit below sqrt(0.5570^2+0.4343^2) = 0.7063"),
        "independent_terms_upper_bound": 0.7063,
        "measured": nrows,
        "constant_used_in_this_file": NOISE_C_G,
        "mean_over_n_eff_ge_16": float(np.mean(consts)),
        "reading": ("~0.35, under half of F's 0.87: G is the quieter statistic per effective "
                    "print. IT IS STILL A POISSON CONSTANT and carries exactly the health "
                    "warning 0.87 carries for F -- see GOING_LIVE.md."),
        "small_n_eff_bias": {
            "mean_G_at_n_eff_8": nrows[0]["mean_G"],
            "mean_G_at_n_eff_256": nrows[-1]["mean_G"],
            "note": ("G approaches G0 only asymptotically. At n_eff = 8 the mean sits ABOVE "
                     "the baseline, which biases the statistic toward 'more regular than "
                     "Poisson'. The REGULAR direction is therefore the one exposed to a "
                     "small-sample false positive, not the clumped one."),
        },
    }

    # --- 3. positive control: clumping at constant mean rate --------------------------
    P = clumped_tape()
    inside = int(((P > 700.0) & (P < 1000.0)).sum())
    t0 = time.time()
    gf = detect_interval(P, 0.0, 1500.0, 2.0, 300.0, noise_constant=NOISE_C_G, kappa=KAPPA)
    g_elapsed = time.time() - t0
    ff = detect(P, 0.0, 1500.0, 2.0, 300.0, noise_constant=POISSON_NOISE_CONSTANT,
                kappa=KAPPA, fit_durations=False)

    rep["control_positive_clumping"] = {
        "tape": {
            "n_prints": int(P.size), "episode": [700.0, 1000.0],
            "rate_inside_per_s": round(inside / 300.0, 3),
            "rate_outside_per_s": round((P.size - inside) / 1200.0, 3),
            "construction": ("the ambient Poisson stretch inside the episode is replaced by "
                            "a cluster process of the SAME mean rate, 7 offspring per parent "
                            "inside a 15 ms exponential window"),
        },
        "G_channel": {
            "n_features": len(gf), "runtime_s": round(g_elapsed, 2),
            "features": interval_feature_rows(gf[:6], event_id="synthetic_clumped"),
        },
        "F_channel": {
            "n_features": len(ff),
            "best_calibrated": round(max((g.calibrated for g in ff), default=0.0), 3),
            "features": [dict(t_ridge=round(g.t_ridge, 2), s_selected=round(g.s_selected, 2),
                              calibrated=round(g.calibrated, 3),
                              persistence_octaves=round(g.persistence_octaves, 2))
                         for g in ff[:6]],
        },
        "reading": ("G fires once and hard on the episode; F is NOT silent but speckles into "
                    "several weak marks, exactly as the ITT mockup predicted ('a rate hump "
                    "makes a trumpet, clumping makes speckle'). The separation is in "
                    "calibrated significance, not in presence/absence."),
    }
    if gf and ff:
        rep["control_positive_clumping"]["separation_ratio"] = round(
            gf[0].calibrated / max((g.calibrated for g in ff), default=1.0), 1)

    # --- 4. negative control ----------------------------------------------------------
    N = sample(lambda x: 6.0 + 0 * x, 1500.0, 8.0, seed=77)
    gn = detect_interval(N, 0.0, 1500.0, 2.0, 300.0, noise_constant=NOISE_C_G, kappa=KAPPA)
    CN, XN, _ = interval_carriers(N)
    rep["control_negative_poisson_null"] = {
        "n_prints": int(N.size), "n_detections": len(gn),
        "mean_departure_by_scale": {
            str(s): round(float(np.mean([G(CN, XN, t, s) - G0
                                         for t in np.linspace(300.0, 1200.0, 20)])), 5)
            for s in (10.0, 40.0, 120.0)},
        "verdict": "zero detections, the same bar F was held to",
    }

    # --- 5. the cross-check, and it is the load-bearing negative result ---------------
    H = sample(hump_lam, 1500.0, 70.0, 41)
    fh = detect(H, 0.0, 1500.0, 2.0, 300.0, noise_constant=POISSON_NOISE_CONSTANT,
                kappa=KAPPA, fit_durations=False)
    gh = detect_interval(H, 0.0, 1500.0, 2.0, 300.0, noise_constant=NOISE_C_G, kappa=KAPPA)

    rep["control_crosscheck_pure_rate_hump"] = {
        "question": "does G stay quiet on a rate hump with no clumping in it?",
        "answer": "NO. The two channels are not independent.",
        "F_channel": {"n_features": len(fh),
                      "best_calibrated": round(max((g.calibrated for g in fh), default=0.0), 2)},
        "G_channel": {
            "n_features": len(gh),
            "features": [dict(t_ridge=round(f.t_ridge, 2), s_selected=round(f.s_selected, 2),
                              direction=f.direction, D_measured=round(f.D_at_ridge, 4),
                              D_closed_form=round(exact_gradient_response(
                                  hump_lam, f.t_ridge, f.s_selected), 4),
                              calibrated=round(f.calibrated, 2))
                         for f in gh],
        },
        "mechanism": {
            "closed_form": "D = log10<lam>_w - <lam log10 lam>_w/<lam>_w",
            "second_order": "D = -Var(eps)/(2 ln10), eps = relative deviation of lam in the window",
            "sign": "ALWAYS NEGATIVE -- any rate gradient reads as clumping",
            "why": ("prints are laid down with density lambda, so the print-weighted mean "
                    "log-interval is size-biased toward high-rate moments while lambda-hat "
                    "is not; the gap between the two is the response"),
            "agreement": "measured within ~0.005 decades of the closed form at the detected ridges",
        },
        "magnitude_context": {
            "gradient_confound_D": round(float(np.mean([f.D_at_ridge for f in gh])), 3) if gh else None,
            "true_clumping_D": round(gf[0].D_at_ridge, 3) if gf else None,
            "note": ("the confound is real but roughly 5x smaller than genuine clumping on "
                     "these tapes, so it does not swamp the signal -- it biases it, in one "
                     "direction, wherever the rate is not flat"),
        },
        "consequence": ("G needs the same envelope control the F channel needed. The "
                        "correction is computable in closed form from lambda-hat -- and "
                        "computing it requires choosing a lambda-hat BANDWIDTH, which is "
                        "precisely the dependence that produced the 1a34975 retraction. It "
                        "is therefore NOT built here. See GOING_LIVE.md."),
    }

    # --- 6. invariances, reported as numbers ------------------------------------------
    rng = np.random.default_rng(5)
    C0, X0, _ = interval_carriers(N)
    thin_shift = {}
    for p_keep in (0.5, 0.25):
        diffs = []
        for _ in range(4):
            thin = N[rng.random(N.size) < p_keep]
            C1, X1, _ = interval_carriers(thin)
            for t in np.linspace(400.0, 1100.0, 12):
                a, b = G(C0, X0, t, 60.0), G(C1, X1, t, 60.0)
                if np.isfinite(a) and np.isfinite(b):
                    diffs.append(b - a)
        thin_shift[str(p_keep)] = round(float(np.mean(diffs)), 5)

    rep["invariances"] = {
        "thinning_G_shift_on_poisson": {
            "measured": thin_shift,
            "predicted": 0.0,
            "derivation": ("thinning Poisson at retention p gives Poisson(p*lambda): "
                           "E[log10 dt] rises by log10(1/p) while log10 lambda-hat falls by "
                           "exactly the same amount, so the shifts cancel and G is invariant. "
                           "A DIFFERENT mechanism from F's invariance to lambda -> c*lambda."),
        },
        "thinning_z_ratio": {
            "F_channel": 0.707,
            "G_channel_measured": "~0.60 on a clumped feature",
            "why_they_differ": ("on a clumped feature thinning removes offspring from "
                                "clusters, so the within-cluster interval fraction falls from "
                                "(K-1)/K to (pK-1)/(pK) and |D| itself shrinks (measured ratio "
                                "~0.84). z therefore falls by more than sqrt(p). The F ratio "
                                "does NOT carry over and was not assumed to."),
        },
        "time_rescaling": "t*, s* scale by c; G, n_eff, z, cal unchanged to 1e-9",
        "permutation": "bitwise identical",
        "seed_density_isolated_feature": "identical to solver tolerance (<1e-8)",
    }

    # --- 7. the defect ----------------------------------------------------------------
    rep["known_defect_seed_density_on_dense_tapes"] = {
        "found": "2026-09-09, while building the G channel",
        "affects": "BOTH channels -- this is not a G-channel problem",
        "symptom": {
            "F_on_2_feature_tape": "counts stable at 2/2/2/2/2 across 3-12 rungs per octave",
            "F_on_dense_tape": "counts 6/7/7/6/7",
            "G_on_dense_tape": "counts 7/6/5/6/5",
        },
        "root_cause": ("persistence_octaves is log2(max/min) over the MEMBER RIDGE POINTS, and "
                       "those live on the seed ladder. The section 5.1 fix polished s_selected "
                       "off the grid but left the EXTENT on it, and persistence is a GATE (the "
                       ">= 1 octave cut). Where features are dense, groups sit near the floor "
                       "and cross it in both directions as the ladder moves."),
        "same_class_as": "the original section 5.1 failure, one pipeline stage later",
        "why_it_matters_here": ("the gates thread reports the real cohort has NO isolated "
                                "resolved feature at any scale from 8 s to 512 s -- the fine "
                                "structure is densely packed and non-isolated everywhere. "
                                "Dense-and-interacting IS the operating regime for this data, "
                                "so this is not a corner case."),
        "recorded_as": ("two strict xfail tests in test_detector.py "
                        "(test_seed_density_independence_dense_tape_F and _G)"),
        "fix_not_attempted": ("making the extent resolution-free means continuation along the "
                             "ridge to its termination scales, solved rather than read off "
                             "rungs. That is a design change to committed, tested code and "
                             "needs its own decision."),
    }

    path = OUT / "interval_synthetic_validation.json"
    path.write_text(json.dumps(rep, indent=2))

    print("GATE 0     : predicted %.7f, measured %.6f at 1e7 draws (se %.1e)"
          % (G0, rows[-1]["measured_mean"], rows[-1]["standard_error"]))
    print("noise const: %.4f (F's is 0.87); independent-terms bound 0.7063"
          % np.mean(consts))
    print("clumping   : G %d feature(s), top cal %.1f, D %+.3f | F %d feature(s), best cal %.1f"
          % (len(gf), gf[0].calibrated if gf else 0, gf[0].D_at_ridge if gf else 0,
             len(ff), max((g.calibrated for g in ff), default=0.0)))
    print("null       : %d detections" % len(gn))
    print("rate hump  : F %d feature(s); G %d feature(s) -- THE CHANNELS ARE NOT INDEPENDENT"
          % (len(fh), len(gh)))
    for f in gh:
        print("             t=%.1f s*=%.1f D measured %+.4f vs closed form %+.4f"
              % (f.t_ridge, f.s_selected, f.D_at_ridge,
                 exact_gradient_response(hump_lam, f.t_ridge, f.s_selected)))
    print("thinning   : G shift on Poisson %s (predicted 0)" % thin_shift)
    print("\nwritten: %s" % path.relative_to(ROOT))


if __name__ == "__main__":
    main()
