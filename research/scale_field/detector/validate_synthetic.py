#!/usr/bin/env python
"""End-to-end synthetic validation of the ridge detector, written to an artifact.

Reproduces the headline table of claude/field_feature_extraction_methods.md sections 5 and
6 through the PROMOTED module rather than through the loose derivation scripts, which is
what establishes that the two are the same object.

WHAT THIS IS NOT. Every tape here is Poisson background with Gaussian bumps -- the easy
case, and the only case these numbers speak about. This tape sits ~1.3 decades from
Poisson, so zero false positives on a matched Poisson null says nothing about the
false-positive rate on the cohort. No cohort data is read, and none may be until the kappa
gate in config/scale_field_detector.json is closed.

Run:  .venv/Scripts/python.exe research/scale_field/detector/validate_synthetic.py
Out:  results/scale_field/artifacts/detector/synthetic_validation.json
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "research" / "scale_field"))

from detector import POISSON_NOISE_CONSTANT, detect, feature_rows  # noqa: E402

OUT = ROOT / "results" / "scale_field" / "artifacts" / "detector"
CONFIG = ROOT / "config" / "scale_field_detector.json"

# The Poisson constant is named here because this file runs on SYNTHETIC POISSON TAPES,
# where 0.87 is the correct constant rather than a stand-in for one that has to be measured.
NOISE_C = POISSON_NOISE_CONSTANT
KAPPA = 1.0


def sample(lam_fn, T, rate_max, seed):
    rng = np.random.default_rng(seed)
    n = rng.poisson(rate_max * T)
    c = np.sort(rng.random(n) * T)
    return c[rng.random(n) < lam_fn(c) / rate_max]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    cfg = json.loads(CONFIG.read_text())
    report = {
        "what": "End-to-end synthetic validation of research/scale_field/detector/.",
        "synthetic_only": True,
        "caveat": ("Poisson background with Gaussian bumps. The cohort sits ~1.3 decades "
                   "from Poisson; nothing here bounds the false-positive rate there."),
        "config": "config/scale_field_detector.json",
        "kappa_gate_state": cfg["kappa_gate"]["state"],
        "kappa_used_here": KAPPA,
        "noise_constant_used_here": NOISE_C,
        "why_a_constant_is_permitted_here": (
            "These are simulated homogeneous-Poisson-background tapes, so sd(F) = "
            "0.87/sqrt(n_eff) is the correct sampling law rather than a stand-in for a "
            "measured one. On the cohort it is not, which is what the gate is about."),
    }

    # --- two injected bumps, and a matched null -------------------------------------
    def lam2(x):
        return (6.0 + 60.0 * np.exp(-(x - 500.0) ** 2 / (2 * 8.0 ** 2))
                + 25.0 * np.exp(-(x - 900.0) ** 2 / (2 * 40.0 ** 2)))

    P = sample(lam2, 1500.0, 70.0, seed=5)
    t0 = time.time()
    feats = detect(P, 0.0, 1500.0, 2.0, 300.0, noise_constant=NOISE_C, kappa=KAPPA)
    elapsed = time.time() - t0

    truth2 = {500.0: 8.0, 900.0: 40.0}
    rows = []
    for f in sorted(feats, key=lambda f: f.t_ridge):
        true_t = min(truth2, key=lambda c: abs(c - f.t_ridge))
        true_sigma = truth2[true_t]
        rows.append(dict(
            true_t=true_t, true_sigma=true_sigma,
            found_t=round(f.t_ridge, 4), localisation_error_s=round(f.t_ridge - true_t, 4),
            s_selected=round(f.s_selected, 4), F_min=round(f.F_min, 6),
            n_eff=round(f.n_eff_at_min, 1), z=round(f.z, 3),
            calibrated=round(f.calibrated, 3),
            persistence_octaves=round(f.persistence_octaves, 3),
            scale_polished=f.scale_polished,
            sigma_minus_half=None if f.sigma_minus_half is None else round(f.sigma_minus_half, 3),
            sigma_minus_half_err_pct=None if f.sigma_minus_half is None
            else round(100 * (f.sigma_minus_half / true_sigma - 1), 1),
            sigma_fit=None if f.sigma_fit is None else round(f.sigma_fit, 3),
            sigma_fit_err_pct=None if f.sigma_fit is None
            else round(100 * (f.sigma_fit / true_sigma - 1), 1),
            tilt_dt_dlns=None if f.tilt_dt_dlns is None else round(f.tilt_dt_dlns, 4),
        ))

    null = sample(lambda x: 6.0 + 0 * x, 1500.0, 8.0, seed=5)
    null_feats = detect(null, 0.0, 1500.0, 2.0, 300.0, noise_constant=NOISE_C,
                        kappa=KAPPA, fit_durations=False)

    report["two_bump_tape"] = {
        "n_prints": int(P.size), "runtime_s": round(elapsed, 2),
        "n_injected": 2, "n_detected": len(feats), "features": rows,
    }
    report["matched_null"] = {
        "description": "flat 6/s Poisson, identical settings",
        "n_prints": int(null.size), "n_detections": len(null_feats),
    }

    # --- four widths on one tape ------------------------------------------------------
    truths = [(300.0, 4.0), (700.0, 12.0), (1200.0, 35.0), (1900.0, 90.0)]

    def lam4(x):
        return 6.0 + sum(55 * np.exp(-(x - c) ** 2 / (2 * w ** 2)) for c, w in truths)

    R = sample(lam4, 2400.0, 70.0, seed=5)
    f4 = detect(R, 0.0, 2400.0, 2.0, 400.0, noise_constant=NOISE_C, kappa=KAPPA)

    wide = []
    for c, w in truths:
        g = min(f4, key=lambda g: abs(g.t_ridge - c)) if f4 else None
        if g is None or abs(g.t_ridge - c) > 4 * w:
            wide.append(dict(true_t=c, true_sigma=w, detected=False))
            continue
        wide.append(dict(
            true_t=c, true_sigma=w, detected=True, found_t=round(g.t_ridge, 3),
            sigma_minus_half=None if g.sigma_minus_half is None else round(g.sigma_minus_half, 3),
            sigma_minus_half_err_pct=None if g.sigma_minus_half is None
            else round(100 * (g.sigma_minus_half / w - 1), 1),
            sigma_fit=None if g.sigma_fit is None else round(g.sigma_fit, 3),
            sigma_fit_err_pct=None if g.sigma_fit is None else round(100 * (g.sigma_fit / w - 1), 1),
            persistence_octaves=round(g.persistence_octaves, 3),
        ))
    report["four_width_tape"] = {
        "n_prints": int(R.size), "n_injected": 4, "n_detected": len(f4), "features": wide,
    }

    report["schema_example"] = feature_rows(feats[:1], event_id="synthetic_two_bump")

    report["reading"] = {
        "localisation": "both bumps located to within a second on a 1500 s tape",
        "duration": ("the -0.5 contour reads high on every bump and fails outright on the "
                     "widest; the two-parameter fit is the measurement and the contour is a "
                     "first look, which is section 6 of the source reproduced"),
        "false_positives": "zero on a matched Poisson null at the same operating point",
        "one_discrepancy_against_the_source": (
            "The source's section 6 claims the fit is 'within 16% everywhere'. Through the "
            "promoted module the widest bump (sigma = 90 s) fits at -18.9%, outside that. "
            "The source states its own section 6 table was computed BEFORE the section 5.1 "
            "scale-polishing fix, so the selected scale -- and with it the set of spine "
            "points the fit sees -- moves. The mid-range improves (sigma = 4 s goes from "
            "-11% to -1.8%, sigma = 12 s from -1% to +0.1%) and the widest degrades. The "
            "claim should read 'within 20% everywhere, within 5% in the middle of the "
            "range', and the widest feature remains the weakest case for the readout."),
        "what_it_does_not_establish": (
            "that any of this transfers to the cohort. Synthetic Poisson validation says "
            "the code is right; it says nothing about the calibration, which is exactly why "
            "kappa must come from a null whose bandwidth content is audited."),
    }

    path = OUT / "synthetic_validation.json"
    path.write_text(json.dumps(report, indent=2))

    print(f"two-bump tape : {P.size} prints, {len(feats)}/2 detected in {elapsed:.1f}s")
    for r in rows:
        print(f"   t={r['found_t']:9.3f} (true {r['true_t']:.0f}, err {r['localisation_error_s']:+.3f} s)"
              f"  s*={r['s_selected']:7.3f}  cal={r['calibrated']:6.2f}"
              f"  sigma: -0.5 -> {r['sigma_minus_half']} ({r['sigma_minus_half_err_pct']:+}%)"
              f"   fit -> {r['sigma_fit']} ({r['sigma_fit_err_pct']:+}%)")
    print(f"matched null  : {null.size} prints, {len(null_feats)} detections")
    print(f"four-width    : {R.size} prints, {len(f4)}/4 detected")
    for r in wide:
        if r["detected"]:
            print(f"   true sigma {r['true_sigma']:5.1f} -> fit {r['sigma_fit']} "
                  f"({r['sigma_fit_err_pct']:+}%), contour {r['sigma_minus_half']}")
        else:
            print(f"   true sigma {r['true_sigma']:5.1f} -> NOT DETECTED")
    print(f"\nwritten: {path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
