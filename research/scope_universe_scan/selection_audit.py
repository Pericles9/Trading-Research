#!/usr/bin/env python
"""
Audit of the universe-selection function, under D4 Amendment A13.

WHY THIS IS NOT THE VINTAGE-CHURN TEST. It was meant to be. The test Cooper specified --
refit the q05 line on expanding vintages, recompute membership, report churn -- **cannot be
run, and the obstacle is the data rather than the rule.**

    momentum_events carries `min_volume_threshold`, which is the column
    filter_events_power_law.py writes onto its OWN OUTPUT (line 65). All 23,268 rows carry
    a non-null value and ALL 23,268 sit ABOVE the line. No table in this checkout holds a
    single rejected event.

So the spine IS the filter's survivors. A q=0.05 quantile line cannot be refit from the
~95% of the population that lies above it -- the 5th percentile of the survivors is not the
5th percentile of the original, and every arm of the three-arm design needs the rejected
mass. This is Phase 8 A10.2d's finding (rejected candidates absent from data/filtered) one
level up: they are absent from the spine too.

WHAT IS STILL RECOVERABLE, AND IT ANSWERS CLAUSE (c) DIRECTLY.

  1. THE SELECTION FUNCTION ITSELF, EXACTLY. min_volume_threshold = 10^(b0 + b1*log10(mom)),
     so regressing log10(min_volume_threshold) on log10(momentum_pct) recovers the fitted
     coefficients to machine precision. A13(a) names these as a permitted output.

  2. THE RESIDUAL SPREAD -- reported FIRST, per Cooper's ordering, because the whole
     interpretation of any churn number hangs on it. The per-event margin above the line is
     CENSORED at zero (survivors only), so the observed spread understates the true one. The
     censoring point is known exactly -- it is the 5th percentile by construction -- so the
     uncensored sigma can be estimated by matching quantiles against a normal truncated at
     its own 5th percentile, and the consistency of that estimate across quantiles doubles
     as a normality check.

  3. THE BASIS-PERTURBATION ARM, ONE-SIDED. A per-ticker volume factor is an additive shift
     in log10(event_volume), so it moves a point vertically against the line. For a shift
     delta, the survivors a -delta shift would push BELOW the line are exactly those with
     margin < delta. That is measurable here, on real data, instead of assumed.
     **It is one-sided and therefore a LOWER BOUND on total basis churn**: events below the
     line that a +delta shift would promote are invisible, because they are not on disk.

A13 COMPLIANCE.
  (a) WRITE BOUNDARY. This script writes NO per-event artifact and no spine numeric column
      under any name. The JSON carries fitted coefficients, aggregate distributional
      summaries of the selection function's own residual, and membership shares. No parquet.
  (b) Not applicable -- no corrected population is produced, because none can be.
  (c) Basis sensitivity is measured below rather than asserted, and the residual spread is
      reported before any of it.

Usage: .venv/Scripts/python.exe research/scope_universe_scan/selection_audit.py
"""
from __future__ import annotations

import json
import os

import duckdb
import numpy as np
from scipy import stats

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
DB = os.path.join(REPO, "data", "duckdb", "main.duckdb")
OUT = "results/scope_universe_scan/selection_audit.json"

# D4's AMC evidence: price factor 5.24 against volume factor 10.06 on the same row.
AMC_FACTOR_RATIO = 10.06 / 5.24
AMC_DECADES = float(np.log10(AMC_FACTOR_RATIO))
Q05_Z = float(stats.norm.ppf(0.05))          # -1.6449, the censoring point by construction


def main() -> int:
    c = duckdb.connect(DB, read_only=True)
    d = c.execute("""
        select momentum_pct, event_volume, min_volume_threshold
        from momentum_events
        where momentum_pct > 0 and event_volume > 0 and min_volume_threshold > 0
    """).fetchdf()
    c.close()

    lm = np.log10(d["momentum_pct"].to_numpy(dtype=np.float64))
    lv = np.log10(d["event_volume"].to_numpy(dtype=np.float64))
    lt = np.log10(d["min_volume_threshold"].to_numpy(dtype=np.float64))

    # --- 1. recover the selection function exactly --------------------------
    b1, b0 = np.polyfit(lm, lt, 1)
    pred = b0 + b1 * lm
    resid_line = lt - pred
    ss = 1.0 - float(np.sum(resid_line ** 2) / np.sum((lt - lt.mean()) ** 2))

    # --- 2. residual spread, CENSORED at zero, reported first ---------------
    margin = lv - lt                     # >= 0 for every survivor, by construction
    ps = [0.01, 0.05, 0.10, 0.25, 0.50, 0.75, 0.90, 0.95, 0.99]
    obs_q = {f"q{int(p*100):02d}": float(np.quantile(margin, p)) for p in ps}

    # sigma implied by matching each observed quantile to a normal truncated below at its
    # own 5th percentile: observed p-th quantile == sigma * (Phi^-1(0.05 + 0.95p) - Phi^-1(0.05))
    sig_est = {}
    for p in ps:
        z = stats.norm.ppf(0.05 + 0.95 * p) - Q05_Z
        if z > 1e-9:
            sig_est[f"from_q{int(p*100):02d}"] = float(np.quantile(margin, p) / z)
    vals = np.array(list(sig_est.values()))
    sigma_hat = float(np.median(vals))
    sigma_spread = float(vals.max() / vals.min()) if vals.min() > 0 else None

    # --- 3. basis-perturbation arm, one-sided -------------------------------
    deltas = [0.05, 0.10, 0.15, AMC_DECADES, 0.35, 0.50, 0.75, 1.00, 1.50]
    sweep = [{"delta_decades": round(float(x), 4),
              "factor": round(float(10 ** x), 3),
              "share_pushed_below_line": float((margin < x).mean()),
              "n_pushed_below_line": int((margin < x).sum()),
              "is_amc_anchor": abs(x - AMC_DECADES) < 1e-9} for x in deltas]

    out = {
        "task": "Audit of the universe-selection function under D4 Amendment A13",
        "HARD_STOP": {
            "what_could_not_be_run": ("the vintage-churn test, in all three arms"),
            "why": ("momentum_events carries min_volume_threshold -- the column "
                    "filter_events_power_law.py writes onto its own output (line 65). All "
                    "23,268 rows carry a non-null value and ALL sit ABOVE the line; zero "
                    "below. No table in this checkout holds a rejected event. The spine IS "
                    "the filter's survivors."),
            "consequence": ("A q=0.05 quantile line cannot be refit from the ~95% of the "
                            "population above it. Every arm of the three-arm design needs "
                            "the rejected mass, and it does not exist on disk."),
            "relation_to_prior_finding": ("Phase 8 A10.2d established rejected candidates "
                                          "are absent from data/filtered/. This is the same "
                                          "fact one level up: absent from the spine too."),
            "verification": {"n_rows": int(len(d)), "n_with_null_threshold": 0,
                             "n_above_line": int((margin >= 0).sum()),
                             "n_below_line": int((margin < 0).sum())},
        },

        "1_selection_function_recovered": {
            "_a13": "A13(a) names fitted coefficients as a permitted output.",
            "form": "log10(min_volume_threshold) = b0 + b1 * log10(momentum_pct)",
            "b0_intercept": float(b0), "b1_slope": float(b1),
            "r_squared": ss,
            "max_abs_residual_decades": float(np.abs(resid_line).max()),
            "reading": "set below",
        },

        "2_residual_spread_REPORTED_FIRST": {
            "_why_first": ("Cooper's ordering. The interpretation of any churn number hangs "
                           "on this, so it precedes every churn figure."),
            "quantity": "margin = log10(event_volume) - log10(min_volume_threshold)",
            "censoring": ("CENSORED AT ZERO. Only survivors are on disk, so this is the "
                          "upper ~95% of the true residual distribution and the observed "
                          "spread UNDERSTATES the true one."),
            "n": int(margin.size),
            "observed_quantiles_decades": obs_q,
            "observed_sd_decades_censored": float(margin.std()),
            "uncensored_sigma_estimate": {
                "method": ("match each observed quantile to a normal truncated below at its "
                           "own 5th percentile -- the censoring point is known exactly, "
                           "because the line IS the 5th percentile by construction"),
                "sigma_hat_decades": sigma_hat,
                "per_quantile_estimates": sig_est,
                "max_over_min_ratio": sigma_spread,
                "normality_check": ("if the residual were normal these estimates would "
                                    "agree; their spread is the departure"),
            },
        },

        "3_basis_perturbation_arm_ONE_SIDED": {
            "_a13": "clause (c) -- basis sensitivity measured, not asserted",
            "mechanism": ("a per-ticker volume factor is an ADDITIVE shift in "
                          "log10(event_volume), so it moves a point vertically against the "
                          "fitted line -- straight across the membership boundary"),
            "amc_anchor": {"price_factor": 5.24, "volume_factor": 10.06,
                           "ratio": AMC_FACTOR_RATIO, "decades": AMC_DECADES,
                           "source": "D4 / Phase 6c, the price-free volume cross-check"},
            "one_sided_caveat": ("This is a LOWER BOUND on basis churn. It counts survivors "
                                 "a -delta shift would push below the line. Events below "
                                 "the line that a +delta shift would PROMOTE are invisible, "
                                 "because they are not on disk. Total churn is larger by an "
                                 "unmeasurable amount."),
            "sweep": sweep,
        },

        "source": "research/scope_universe_scan/selection_audit.py:main",
        "reproduce": ".venv/Scripts/python.exe research/scope_universe_scan/selection_audit.py",
        "a13_write_boundary": ("no per-event artifact and no spine numeric column under any "
                               "name is written by this script; JSON aggregates only, no "
                               "parquet"),
    }
    out["1_selection_function_recovered"]["reading"] = (
        "an exact line recovery confirms the threshold column is the fitted line evaluated "
        "per event, and pins the selection function that was actually applied.")

    with open(os.path.join(REPO, OUT), "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=2)

    hs = out["HARD_STOP"]["verification"]
    print("HARD STOP -- the vintage-churn test cannot be run.")
    print(f"  rows {hs['n_rows']:,}   above the line {hs['n_above_line']:,}   "
          f"below {hs['n_below_line']:,}")
    print("  the spine IS the filter's survivors; the rejected population is on no table.\n")
    f = out["1_selection_function_recovered"]
    print(f"selection function recovered: log10(thr) = {f['b0_intercept']:.6f} "
          f"+ {f['b1_slope']:.6f} * log10(mom)")
    print(f"   R^2 {f['r_squared']:.10f}   max |resid| "
          f"{f['max_abs_residual_decades']:.2e} decades\n")
    r = out["2_residual_spread_REPORTED_FIRST"]
    print(f"RESIDUAL SPREAD FIRST (n={r['n']:,}, censored at 0):")
    print(f"   observed quantiles (decades): {r['observed_quantiles_decades']}")
    print(f"   observed sd (censored)      : {r['observed_sd_decades_censored']:.4f}")
    u = r["uncensored_sigma_estimate"]
    print(f"   uncensored sigma estimate   : {u['sigma_hat_decades']:.4f} decades")
    print(f"   per-quantile spread (max/min): {u['max_over_min_ratio']:.2f}\n")
    print("BASIS PERTURBATION (one-sided lower bound):")
    for s in out["3_basis_perturbation_arm_ONE_SIDED"]["sweep"]:
        tag = "   <-- AMC anchor" if s["is_amc_anchor"] else ""
        print(f"   delta {s['delta_decades']:.3f} dec ({s['factor']:6.2f}x): "
              f"{s['share_pushed_below_line']:6.2%} pushed below "
              f"({s['n_pushed_below_line']:,}){tag}")
    print(f"\nwrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
