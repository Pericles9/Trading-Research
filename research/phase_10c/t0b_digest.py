"""Phase 10c Stage 0b digest (T0b.7). Describes; evaluates only the mechanical gate."""
from __future__ import annotations

import importlib.util as ilu
import json
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "phase_10"))
from common import rel  # noqa: E402
_s = ilu.spec_from_file_location("c10c", os.path.join(HERE, "common.py"))
c10c = ilu.module_from_spec(_s); _s.loader.exec_module(c10c)

ART = "results/phase_10c/artifacts"
GRID = [1, 2, 4, 8, 16, 32, 64]


def main() -> int:
    cfg, chash = c10c.load_cfg(), c10c.cfg_hash()
    E, M = c10c.class_e(cfg), c10c.class_m(cfg)
    d16 = float(E["D16_min_median_void"])
    wf = json.load(open(rel(f"{ART}/t0b_waterfall.json"), encoding="utf-8"))
    man = json.load(open(rel(f"{ART}/t0b_chart_manifest.json"), encoding="utf-8"))
    ev = pd.read_parquet(rel(f"{ART}/t0b_2_void.parquet"))
    po = pd.read_parquet(rel(f"{ART}/t0b_1_prominence_order.parquet"))
    sw = pd.read_parquet(rel(f"{ART}/t0b_4_prominence_sweep.parquet"))
    df = pd.read_parquet(rel(f"{ART}/t0b_3_5_density_floor.parquet"))
    raw = pd.read_parquet(rel(f"{ART}/t0_4_density_d4.parquet")).drop_duplicates(
        subset=["ticker", "event_date_canonical"])
    prim = ev[~ev.is_sidecar]

    # ---- T0b.6 gate, evaluated by segment
    gate = {}
    fired = False
    for seg in ("premarket", "rth"):
        v = ev[ev.det_segment == seg]["void"].dropna()
        med = float(v.median())
        below = bool(med < d16)
        fired = fired or below
        gate[seg] = {"n": int(len(v)), "median_void": med, "p10": float(v.quantile(.1)),
                     "p90": float(v.quantile(.9)), "threshold_D16": d16, "below_threshold": below}
    gate["outcome"] = "HALT" if fired else "does not fire"

    # ---- A2.7 D2 selection rule
    f95 = float(prim.peak_lo_log10s.quantile(.95))
    s05 = float(prim.peak_hi_log10s.quantile(.05))
    sep = f95 < s05
    d2 = {"rule": cfg["a2_rules"]["D2_selection_rule"],
          "fast_mode_p95_log10s": f95, "slow_mode_p5_log10s": s05,
          "fast_p95_seconds": float(10 ** f95), "slow_p5_seconds": float(10 ** s05),
          "separated": bool(sep), "overlap_decades": float(max(0.0, f95 - s05)),
          "rule_applied": "rule 1 (set D2 in the gap)" if sep else "rule 2 (no single global D2)",
          "action": ("set D2 in the gap" if sep else
                     "ESCALATE. Report the overlap; do not pick a compromise value. Resolution is "
                     "per-segment or per-event D2, a new decision requiring its own amendment."),
          "n_primary_events": int(len(prim))}
    silent = {"question": ("A2.7's silent failure mode: is the LATER of the two most prominent "
                           "peaks the taller one? If so, a D2 above it selects the slow mode as "
                           "the intraburst peak without triggering no_intraburst_peak."),
              "n_events_slow_is_taller": int(po.slow_is_taller.sum()), "of": int(len(po)),
              "share": float(po.slow_is_taller.mean()),
              "by_segment": {s: {"n": int(g.slow_is_taller.sum()), "of": int(len(g))}
                             for s, g in po[~po.is_sidecar].groupby("det_segment")}}

    # ---- T0b.3 / A2.8 D5 derivation inputs
    d = df[df.det_segment.isin(["premarket", "rth"])]
    r = d[d.det_segment == "rth"]
    floors = r.groupby("precision_factor").derived_min_count.median().to_dict()
    wcs = r.groupby("kernel_min").window_count_median.median().to_dict()
    d5 = {}
    for f_, fl in floors.items():
        ok = [k for k, c in wcs.items() if c >= fl]
        d5[str(f_)] = {"derived_floor_median": float(fl),
                       "smallest_clearing_rung_min": (int(min(ok)) if ok else None),
                       "note": None if ok else f"no rung at or below D11={M['D11_grid_ceiling_min']} clears it"}
    too_few = {seg: {str(k): {str(f_): float(g2.too_few_prints_fraction.median())
                              for f_, g2 in g[g.kernel_min == k].groupby("precision_factor")}
                     for k in GRID}
               for seg, g in d.groupby("det_segment")}

    disp = sw.dropna(subset=["trough_log10s"]).groupby(
        ["ticker", "event_date_canonical"]).trough_log10s.agg(lambda s: s.max() - s.min())
    u = df.drop_duplicates(subset=["ticker", "event_date_canonical"])
    u = u[u.det_segment.isin(["premarket", "rth"])]

    ties = wf["prints_raw"] - wf["prints_tie_collapsed"]
    absorbed = wf["prints_tie_collapsed"] - wf["prints_after_D1_aggregation"]
    digest = {
        "phase": "10c", "stage": "0b", "tasks": "T0b.1-T0b.7",
        "config": "config/phase_10c.json", "config_hash": chash,
        "wall_clock_seconds": wf["timing_seconds"],
        "governing_documents": cfg["_governing_documents"],
        "stage_0b_constraints_honoured": {
            "no_sub_bursts": True, "no_normalisation_window_applied": True,
            "no_interval_pooling_across_events": True,
            "trough_and_void_computed": True,
            "why_permitted": "A2.3 permits a candidate trough and void because that is the "
                             "precondition being tested."},
        "verification_block": {
            "row_waterfall": {
                "events": wf["events"], "prints_raw": wf["prints_raw"],
                "exact_ties_collapsed_D12": int(ties),
                "prints_tie_collapsed": wf["prints_tie_collapsed"],
                "absorbed_by_D1_aggregation": int(absorbed),
                "absorbed_share_of_tie_collapsed": round(absorbed / wf["prints_tie_collapsed"], 6),
                "prints_after_D1_aggregation": wf["prints_after_D1_aggregation"],
                "intervals": wf["intervals"],
                "reconciles": bool(wf["prints_after_D1_aggregation"] - wf["events"] == wf["intervals"]),
                "identity": "intervals = prints_after_D1_aggregation - events",
                "sub_bursts_extracted": 0},
            "d4_quarantine_A1_8": c10c.verify_quarantine(),
            "cooper_values_used": {"class_E": E, "class_M": M},
            "D1_applied_us": wf["D1_sweep_floor_us"],
            "prominence_floor": {"method": "per-peak Poisson floor",
                                 "rule": "keep a peak iff prominence_counts > sqrt(count) at its bin",
                                 "derivation": cfg["a2_rules"]["prominence_floor_derivation"],
                                 "global_constant_used": False},
            "session_boundary": cfg["settled"]["D3_window"]["session_boundary"]},
        "T0b_1_peak_set": {
            "peak_count": {"min": int(ev.n_peaks.min()), "p25": float(ev.n_peaks.quantile(.25)),
                           "median": float(ev.n_peaks.median()),
                           "p75": float(ev.n_peaks.quantile(.75)), "max": int(ev.n_peaks.max())},
            "peak_count_by_segment": {s: float(g.n_peaks.median())
                                      for s, g in ev.groupby(ev.det_segment.fillna("unlabelled"))},
            "note": ("A2.2 states the method assumes a two-mode histogram. The surviving peak "
                     "count is reported here as measured, against a Poisson-derived floor.")},
        "T0b_2_void": {
            "labels": ev.label.value_counts().to_dict(),
            "by_segment": {s: {"n": int(g["void"].notna().sum()),
                               "median": float(g["void"].median()),
                               "p10": float(g["void"].quantile(.1)),
                               "p90": float(g["void"].quantile(.9))}
                           for s, g in ev.groupby(ev.det_segment.fillna("unlabelled"))}},
        "T0b_3_dispersion": {
            "sigma_raw_median": float(raw.sigma_log10.median()),
            "sigma_post_aggregation_median": float(ev.sigma_log10_post_agg.median()),
            "by_segment": {s: float(g.sigma_log10_post_agg.median())
                           for s, g in ev.groupby(ev.det_segment.fillna("unlabelled"))},
            "too_few_prints_fraction_by_segment_kernel_factor": too_few},
        "T0b_4_prominence_sensitivity": {
            "n_events": int(len(disp)),
            "trough_displacement_decades": {"median": float(np.median(disp)),
                                            "p90": float(np.percentile(disp, 90)),
                                            "max": float(np.max(disp))},
            "reporting_rule": cfg["a2_rules"]["prominence_sensitivity_reporting"],
            "no_pass_threshold": True},
        "T0b_5_near_detection_density": {
            s: {"session_prints_per_min_median": float(g.session_prints_per_min.median()),
                "near_detection_prints_per_min_median": float(g.near_detection_prints_per_min.median())}
            for s, g in u.groupby("det_segment")},
        "T0b_6_gate": gate,
        "A2_7_D2_selection": d2,
        "A2_7_silent_failure_incidence": silent,
        "A2_8_D5_derivation_inputs": {
            "rule": cfg["a2_rules"]["D5_derivation"],
            "rth_median_window_count_by_kernel": {str(k): float(v) for k, v in wcs.items()},
            "by_precision_factor": d5,
            "D6_rule": cfg["a2_rules"]["D6_derivation"]},
        "labelled_and_carried_counts": {
            "unimodal": int(ev.label.eq("unimodal").sum()),
            "adjacent_peaks": int(ev.label.eq("adjacent_peaks").sum()),
            "no_intraburst_peak": 0, "too_few_prints": 0, "no_threshold": 0,
            "note": ("The last three belong to Stage 1. Stage 0b selects no threshold and applies "
                     "no window; the too_few_prints figures above are a sensitivity sweep, not "
                     "carried labels.")},
        "class_M_still_held": {k: v for k, v in M.items() if v is None},
        "escalations_raised": ([] if sep else [{
            "id": "E1", "authority": "Phase-10c-Amendment-A2.md A2.7 rule 2",
            "condition": "fast-mode p95 and slow-mode p5 overlap",
            "observed": {"fast_p95_log10s": f95, "slow_p5_log10s": s05,
                         "overlap_decades": float(f95 - s05)},
            "action": ("No single global D2 exists. Reported, not resolved. A2.7 forbids picking a "
                       "compromise value; the resolution is per-segment or per-event D2, which is "
                       "a new decision requiring its own amendment.")}]),
        "charts": man["charts"],
        "next": ("T0b.7 HALT. Stage 0b does not flow into Stage 1. The T0b.6 gate did not fire; "
                 "the A2.7 D2 rule escalated. Awaiting Cooper's disposition and the held Class M "
                 "values D2, D4, D5, D6, D15."),
        "source": "research/phase_10c/t0b_digest.py:main"}

    os.makedirs(rel("results/phase_10c/digests"), exist_ok=True)
    c10c.write_json(rel("results/phase_10c/digests/stage0b_digest.json"), digest)
    print("stage 0b digest written")
    print(f"  waterfall reconciles: {digest['verification_block']['row_waterfall']['reconciles']}")
    print(f"  T0b.6 gate: {gate['outcome']}  "
          f"(premarket {gate['premarket']['median_void']:.4f}, rth {gate['rth']['median_void']:.4f} "
          f"vs D16={d16})")
    print(f"  A2.7 D2: {d2['rule_applied']}")
    print(f"  escalations: {len(digest['escalations_raised'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
