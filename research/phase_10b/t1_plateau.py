"""
Phase 10b T1 -- fragmentation-plateau check.

Hypothesis under test: the near-flat Allan plateau below the v3 knee is execution
fragmentation, and its height is set by sweep size rather than by anything about
the market.

For a cluster process the Fano/Allan plateau between cluster duration and cluster
spacing equals the SIZE-BIASED mean cluster size E[N^2]/E[N], not the plain mean
E[N]. Both regressions are reported so the difference is visible -- testing
against E[N] alone produces a slope below 1 and a spurious rejection.

SCOPE FENCE: the sweep-run grouping computed here exists only to produce the
x-axis of chart 01. It is written to its own artifact (t1_sweep_runs.parquet) and
is read by no other task in this phase. It never enters an Allan, intensity or
rescaling computation. Asserted in the verification block.

No escalation row fires on T1's outcome. Both outcomes are informative.

Usage: .venv/Scripts/python.exe research/phase_10b/t1_plateau.py
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import time

import numpy as np
import pandas as pd
from scipy import stats as sps

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "phase_10"))
from v2_common import COHORT_KEY, read_event_trades, rel, write_json  # noqa: E402

CFG = "config/phase_10b.json"
OUT_RUNS = "results/phase_10b/artifacts/t1_sweep_runs.parquet"
OUT_FIT = "results/phase_10b/artifacts/t1_plateau_fit.json"
SEGMENTS = ("premarket", "rth")


def load_cfg():
    with open(rel(CFG), encoding="utf-8") as f:
        return json.load(f)


def cfg_hash():
    with open(rel(CFG), "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()[:8]


def sweep_runs(ts_ns: np.ndarray, gap_s: float) -> dict:
    """Maximal runs of consecutive prints with inter-print gap <= gap_s.

    Singletons count as runs of size 1 -- for a cluster process most 'clusters'
    are size 1, and excluding them would bias E[N] and E[N^2]/E[N] upward.
    """
    n = ts_ns.size
    if n < 2:
        return {"n_runs": n, "mean_run_size": float(n), "size_weighted_mean_run_size": float(n),
                "n_prints": int(n)}
    gap_ns = gap_s * 1e9
    dt = np.diff(ts_ns)
    breaks = dt > gap_ns
    sizes = np.diff(np.concatenate(([0], np.flatnonzero(breaks) + 1, [n])))
    s = sizes.astype(np.float64)
    return {"n_runs": int(s.size), "mean_run_size": float(s.mean()),
            "size_weighted_mean_run_size": float((s ** 2).sum() / s.sum()),
            "n_prints": int(n), "max_run_size": int(s.max())}


def main() -> int:
    cfg = load_cfg()
    chash = cfg_hash()
    t1 = cfg["t1_fragmentation"]
    gaps = [t1["sweep_gap_s"]["primary"]] + list(t1["sweep_gap_s"]["sensitivity"])
    g_primary = t1["sweep_gap_s"]["primary"]
    lo_e, hi_e = t1["plateau_rungs_exponents"]
    flat_max = t1["plateau_flatness_max"]
    never = cfg["cohort"]["never_pooled"]

    cohort = pd.read_parquet(rel(cfg["cohort"]["manifest"]))
    cohort["event_date_canonical"] = cohort["event_date_canonical"].astype(str)

    # ---------------------------------------------------------------- T1b
    rows = []
    t0 = time.perf_counter()
    for i, r in enumerate(cohort.itertuples(index=False), 1):
        d = read_event_trades(cfg, r.ticker, r.event_date_canonical, r.momentum_pct, offsets=(0,))
        s0 = d.get(0)
        if s0 is None or len(s0) == 0:
            continue
        ts = s0["sip_timestamp"].to_numpy()
        for g in gaps:
            rows.append({"ticker": r.ticker, "event_date_canonical": r.event_date_canonical,
                         "momentum_pct": r.momentum_pct, "cohort_group": r.cohort_group,
                         "sweep_gap_s": g, **sweep_runs(ts, g)})
        if i % 25 == 0:
            print(f"  {i}/{len(cohort)} events ({time.perf_counter()-t0:.0f}s)", flush=True)
    runs = pd.DataFrame(rows)
    runs.attrs["scope_fence"] = t1["sweep_run_scope"]
    runs.to_parquet(rel(OUT_RUNS), index=False)

    # ---------------------------------------------------------------- T1c
    cur = pd.read_parquet(rel(cfg["paths"]["v3_allan_curves"]))
    cur["event_date_canonical"] = cur["event_date_canonical"].astype(str)
    pl = cur[(cur["observable"] == "print_rate")
             & (cur["T"] >= 2.0 ** lo_e) & (cur["T"] <= 2.0 ** hi_e) & (cur["allan"] > 0)].copy()
    pl["log_allan"] = np.log(pl["allan"])
    g = pl.groupby(COHORT_KEY + ["segment", "cohort_group"])["log_allan"]
    plateau = g.agg(plateau_height_log="mean",
                    plateau_iqr_log=lambda x: float(np.percentile(x, 75) - np.percentile(x, 25)),
                    n_rungs="size").reset_index()
    plateau["is_flat"] = plateau["plateau_iqr_log"] <= flat_max

    # ---------------------------------------------------------------- T1d
    m = plateau.merge(runs[runs["sweep_gap_s"] == g_primary], on=COHORT_KEY + ["cohort_group"],
                      how="left")
    pooled = m[~m["cohort_group"].isin(never)]

    def regress(sub, xcol):
        s = sub[sub["is_flat"] & (sub[xcol] > 0)]
        if len(s) < 5:
            return {"n": int(len(s)), "slope": None, "ci95": None, "r2": None, "intercept": None}
        x = np.log(s[xcol].to_numpy())
        y = s["plateau_height_log"].to_numpy()
        lr = sps.linregress(x, y)
        tcrit = sps.t.ppf(0.975, len(s) - 2)
        return {"n": int(len(s)), "slope": float(lr.slope),
                "ci95": [float(lr.slope - tcrit * lr.stderr), float(lr.slope + tcrit * lr.stderr)],
                "stderr": float(lr.stderr), "intercept": float(lr.intercept),
                "r2": float(lr.rvalue ** 2), "pvalue": float(lr.pvalue),
                "slope_1_inside_ci": bool(lr.slope - tcrit * lr.stderr <= 1.0
                                          <= lr.slope + tcrit * lr.stderr)}

    by_seg = {}
    for seg in SEGMENTS:
        sub = pooled[pooled["segment"] == seg]
        by_seg[seg] = {
            "n_events": int(len(sub)),
            "n_flat": int(sub["is_flat"].sum()),
            "n_excluded_not_flat": int((~sub["is_flat"]).sum()),
            "plateau_iqr_log": {"median": float(sub["plateau_iqr_log"].median()),
                                "max": float(sub["plateau_iqr_log"].max())},
            "plateau_height_log": {"median": float(sub.loc[sub["is_flat"], "plateau_height_log"].median()),
                                   "min": float(sub.loc[sub["is_flat"], "plateau_height_log"].min()),
                                   "max": float(sub.loc[sub["is_flat"], "plateau_height_log"].max())},
            "size_weighted_mean_run_size": {
                "median": float(sub.loc[sub["is_flat"], "size_weighted_mean_run_size"].median()),
                "min": float(sub.loc[sub["is_flat"], "size_weighted_mean_run_size"].min()),
                "max": float(sub.loc[sub["is_flat"], "size_weighted_mean_run_size"].max())},
            "regression_vs_size_weighted": regress(sub, "size_weighted_mean_run_size"),
            "regression_vs_plain_mean": regress(sub, "mean_run_size"),
        }

    sens = {}
    for gp in gaps:
        ms = plateau.merge(runs[runs["sweep_gap_s"] == gp], on=COHORT_KEY + ["cohort_group"],
                           how="left")
        ps = ms[~ms["cohort_group"].isin(never)]
        sens[f"gap_{gp:g}s"] = {
            seg: regress(ps[ps["segment"] == seg], "size_weighted_mean_run_size")
            for seg in SEGMENTS}

    carried = {gname: {"n_events": int(len(sub)), "n_flat": int(sub["is_flat"].sum()),
                       "regression_vs_size_weighted": regress(sub, "size_weighted_mean_run_size")}
               for gname, sub in m[m["cohort_group"].isin(never)].groupby("cohort_group")}

    summary = {
        "phase": "10b", "task": "T1", "config_hash": chash,
        "hypothesis": ("The near-flat Allan plateau below the v3 knee is execution fragmentation, "
                       "and its height is set by sweep size rather than by anything about the market. "
                       "For a cluster process the plateau equals the SIZE-BIASED mean cluster size "
                       "E[N^2]/E[N], so the prediction is a slope near 1 against that and a slope "
                       "below 1 against the plain mean E[N]."),
        "no_escalation_note": t1["no_escalation"],
        "scope_fence": t1["sweep_run_scope"],
        "plateau_definition": {
            "rungs_seconds": [2.0 ** lo_e, 2.0 ** hi_e],
            "n_rungs": int(plateau["n_rungs"].iloc[0]) if len(plateau) else 0,
            "height": "mean of natural-log Allan factor across the plateau rungs, print observable",
            "flatness_rule": f"IQR of log A across those rungs <= {flat_max}; above it the event is "
                             "NOT flat, is excluded from the fit, and is counted",
        },
        "sweep_gap_primary_s": g_primary,
        "by_segment": by_seg,
        "sensitivity_across_sweep_gap": sens,
        "carried_never_pooled": carried,
        "timing_seconds": round(time.perf_counter() - t0, 1),
        "source": "research/phase_10b/t1_plateau.py:main",
        "artifacts": [OUT_RUNS, OUT_FIT],
    }
    write_json(rel(OUT_FIT), summary)

    for seg in SEGMENTS:
        b = by_seg[seg]
        sw, pm = b["regression_vs_size_weighted"], b["regression_vs_plain_mean"]
        print(f"\n{seg}: n={b['n_events']} flat={b['n_flat']} excluded={b['n_excluded_not_flat']}")
        print(f"  vs SIZE-WEIGHTED E[N^2]/E[N]: slope {sw['slope']:+.4f} "
              f"CI95 [{sw['ci95'][0]:+.4f}, {sw['ci95'][1]:+.4f}] r2={sw['r2']:.4f} "
              f"| slope=1 inside CI: {sw['slope_1_inside_ci']}")
        print(f"  vs PLAIN MEAN E[N]         : slope {pm['slope']:+.4f} "
              f"CI95 [{pm['ci95'][0]:+.4f}, {pm['ci95'][1]:+.4f}] r2={pm['r2']:.4f} "
              f"| slope=1 inside CI: {pm['slope_1_inside_ci']}")
    print("\nsensitivity (slope vs size-weighted, by sweep gap):")
    for k, v in sens.items():
        print(f"  {k:14s} " + "  ".join(
            f"{s}={v[s]['slope']:+.4f}" for s in SEGMENTS if v[s]['slope'] is not None))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
