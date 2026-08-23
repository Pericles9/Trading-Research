"""Phase 10c Stage 0 digest (T0.8). Describes; does not evaluate."""
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

ART, CH = "results/phase_10c/artifacts", "results/phase_10c/charts"
PROM_SWEEP = [0.01, 0.02, 0.05, 0.10, 0.20]
P = 0.05


def J(p):
    return json.load(open(rel(p), encoding="utf-8"))


def main() -> int:
    cfg, chash = c10c.load_cfg(), c10c.cfg_hash()
    E, M = c10c.class_e(cfg), c10c.class_m(cfg)
    wf = J(f"{ART}/t0_waterfall.json")
    six = J(f"{ART}/t0_6_anchor_migration.json")
    sev = J(f"{ART}/t0_7_population.json")
    man = J(f"{ART}/t0_chart_manifest.json")
    ev = pd.read_parquet(rel(f"{ART}/t0_1_raw_landscape.parquet"))
    fl = pd.read_parquet(rel(f"{ART}/t0_2_floor_sensitivity.parquet"))
    d4 = pd.read_parquet(rel(f"{ART}/t0_4_density_d4.parquet"))
    cl = pd.read_parquet(rel(f"{ART}/t0_5_clipped_fraction.parquet"))

    e1 = ev[ev.prominence_frac == P]
    u = d4.drop_duplicates(subset=["ticker", "event_date_canonical"])
    n_ev = int(len(e1))

    # ---- verification block (S11)
    ties = wf["raw_prints"] - wf["prints_after_tie_collapse"]
    recon = (wf["prints_after_tie_collapse"] - wf["events_with_trades"]) == wf["intervals_raw"]
    seg = u.groupby([u.det_segment.fillna("UNLABELLED"), "is_sidecar"]).size()
    verification = {
        "row_waterfall": {
            "events_attempted": wf["events_attempted"],
            "events_with_trades": wf["events_with_trades"],
            "raw_prints_in": wf["raw_prints"],
            "exact_timestamp_ties_collapsed_D12": int(ties),
            "tie_share": round(ties / wf["raw_prints"], 6),
            "prints_after_tie_collapse": wf["prints_after_tie_collapse"],
            "intervals_computed": wf["intervals_raw"],
            "reconciles": bool(recon),
            "reconciliation_identity": ("intervals = prints_after_tie_collapse - events_with_trades "
                                        "(one interval is lost per event boundary)"),
            "sub_bursts_extracted": 0,
            "sub_bursts_note": "Stage 0 produces no sub-bursts by construction (A1.2)."},
        "d4_quarantine_A1_8": c10c.verify_quarantine(),
        "dev_sample": {"name": cfg["dev_sample"]["name"], "n_primary": n_ev - int(u.is_sidecar.sum()),
                       "n_sidecar": int(u.is_sidecar.sum()), "n_total": n_ev,
                       "seed": cfg["dev_sample"]["seed"],
                       "stratification": cfg["dev_sample"]["stratification"]},
        "segment_split": {f"{a}|sidecar={b}": int(v) for (a, b), v in seg.items()},
        "segment_note": ("All three events without a premarket/rth label are SIDECAR events, which "
                         "A1.6 already carries and reports separately. The 50 primary events are "
                         "cleanly premarket or rth."),
        "cooper_values_used": {"class_E": E, "class_M": M,
                               "class_M_note": "All null. Not required at Stage 0 (A1.9)."},
        "derived_data_floor": {
            "formula": "n >= ( sqrt(pi/2) * sigma_log10 / log10(F) )^2",
            "derivation": ("Asymptotic standard error of a sample median, SE = sqrt(pi/2)*sigma/"
                           "sqrt(n). Requiring the local median within a multiplicative factor F "
                           "in log space sets SE <= log10(F). sigma_log10 is the event's own "
                           "spread, so the floor is data-derived per event."),
            "sigma_log10_across_events": {"p10": float(u.sigma_log10.quantile(.1)),
                                          "median": float(u.sigma_log10.median()),
                                          "p90": float(u.sigma_log10.quantile(.9))},
            "at_configured_F": float(E["D4_median_precision_factor"]),
            "derived_min_count_median": float(
                d4[d4.precision_factor == E["D4_median_precision_factor"]].derived_min_count.median())},
        "config_hash": chash,
        "no_real_event_excluded": "All 56 dev-sample events returned trades.",
    }

    # ---- task findings
    lm = e1.leftmost_mode_log10s.dropna()
    fg = fl.groupby("floor_us")
    floor_tab = {}
    for f_ in sorted(fl.floor_us.unique()):
        s = fl[fl.floor_us == f_]
        floor_tab[str(int(f_))] = {
            "frac_absorbed_median": float(s.frac_absorbed.median()),
            "frac_absorbed_p90": float(s.frac_absorbed.quantile(.9)),
            "leftmost_mode_log10s_median": float(s[f"leftmost_mode_p{P}"].median()),
            "floor_itself_log10s": float(np.log10(f_ / 1e6)),
            "mode_minus_floor_decades": float(s[f"leftmost_mode_p{P}"].median() - np.log10(f_ / 1e6)),
            "largest_peak_log10s_median": float(s[f"largest_peak_p{P}"].median()),
            "largest_peak_log10s_p90": float(s[f"largest_peak_p{P}"].quantile(.9)),
            "admissible_under_check4_cond2": bool(
                (E["D7_threshold_lo_ms"] * 1000.0) / f_ >= 10.0)}

    d4_tab = {}
    for f_ in sorted(d4.precision_factor.unique()):
        s = d4[d4.precision_factor == f_]
        d4_tab[str(f_)] = {"derived_min_count_median": float(s.derived_min_count.median()),
                           "too_few_prints_median": float(s.too_few_prints_fraction.median()),
                           "too_few_prints_p90": float(s.too_few_prints_fraction.quantile(.9)),
                           "events_with_no_usable_interval":
                               int((s.too_few_prints_fraction >= 1.0).sum()), "of": int(len(s))}

    piv = cl.pivot_table(index="kernel_min", columns="cut_at_rth", values="clipped_fraction",
                         aggfunc="median")
    clip_tab = {str(int(k)): {"extended_day_only": float(piv.loc[k, False]),
                              "plus_rth_boundaries": float(piv.loc[k, True])} for k in piv.index}

    prom_tab = {str(p): {"leftmost_mode_median": float(ev[ev.prominence_frac == p]
                                                       .leftmost_mode_log10s.median()),
                         "n_peaks_median": float(ev[ev.prominence_frac == p].n_peaks.median())}
                for p in PROM_SWEEP}

    digest = {
        "phase": "10c", "stage": 0, "tasks": "T0.1-T0.8", "config": "config/phase_10c.json",
        "config_hash": chash, "wall_clock_seconds": wf["timing_seconds"],
        "governing_documents": cfg["_governing_documents"],
        "stage_0_constraints_honoured": {
            "no_sub_bursts": True, "no_threshold_selected": True,
            "no_void_parameter_computed": True, "no_normalisation_window_applied": True,
            "no_interval_pooling_across_events": True,
            "pooling_note": ("Every histogram is per event. Every population statement below is "
                             "the distribution ACROSS events of a per-event summary quantity.")},
        "verification_block": verification,
        "T0_1_raw_landscape": {
            "n_events": n_ev,
            "leftmost_mode_log10s": {"p10": float(lm.quantile(.1)), "median": float(lm.median()),
                                     "p90": float(lm.quantile(.9))},
            "leftmost_mode_seconds_median": float(10 ** lm.median()),
            "first_trough_log10s_median": float(e1.first_trough_log10s.dropna().median()),
            "frac_below_trough_median": float(e1.frac_below_trough.dropna().median()),
            "prominence_sweep": prom_tab},
        "T0_2_T0_3_floor_sensitivity": floor_tab,
        "T0_4_density_and_D4": {
            "prints_per_min_by_segment": {
                str(k): {"n": int(v["count"]), "p25": float(v["25%"]), "median": float(v["50%"]),
                         "p75": float(v["75%"])}
                for k, v in u.groupby(u.det_segment.fillna("UNLABELLED"))["prints_per_min_mean"]
                .describe()[["count", "25%", "50%", "75%"]].iterrows()},
            "window_count_at_4min_median_across_events": float(u.window_count_median.median()),
            "sensitivity": d4_tab,
            "A1_3_question": "Is the too_few_prints fraction flat or steep across 1.1-1.5?",
            "A1_3_answer": ("Steep. The median fraction moves 1.000 / 1.000 / 0.836 / 0.457 across "
                            "F = 1.1 / 1.2 / 1.3 / 1.5. D4 is load-bearing, not a preference. "
                            "Reported per A1.3; no value is recommended.")},
        "T0_5_clipped_fraction": {
            "by_kernel_median_across_events": clip_tab,
            "two_definitions_note": ("S3.3 motivates clipping solely by the overnight gap, which "
                                     "points at the extended-day edges. A centered window spanning "
                                     "the RTH open instead mixes two rate regimes. Both are "
                                     "reported; the choice between them is the D11 decision.")},
        "T0_6_anchor_migration": {
            "n_events": six["n_events"], "base": six["base_variant"],
            "n_moved_vs_each_variant": {k: v["n_moved"] for k, v in
                                        six["migration_vs_base"].items()},
            "segment_counts": six["segment_counts"][six["base_variant"]],
            "anchor_shift_seconds": six["anchor_shift_seconds_vs_base"],
            "resolution": ("Zero events change detection segment across all five poll variants. "
                           "Per A1.6 the anchor choice therefore remains a default rather than "
                           "becoming a decision with its own D-number. poll0 stands.")},
        "T0_7_population": {"candidates": sev["candidate_populations"],
                            "compute_estimates": sev["compute_estimates"],
                            "canonical_scan_seconds": sev["canonical_scan_seconds"],
                            "per_event_seconds_basis": sev["per_event_seconds_from_stage0"],
                            "note": sev["note"]},
        "reported_not_gated": {
            "implied_min_intervals_per_subburst":
                E["D8_min_median_duration_s"] / E["D7_threshold_hi_s"],
            "formula": "D8_min_median_duration_s / D7_threshold_hi_s",
            "note": "Reported per A1.4. Not evaluated."},
        "labelled_and_carried_counts": {
            "no_intraburst_peak": 0, "too_few_prints": 0, "no_threshold": 0,
            "note": ("All three labels belong to Stage 1. Stage 0 selects no threshold and applies "
                     "no window, so none can be produced here. The too_few_prints figures under "
                     "T0_4 are a SENSITIVITY SWEEP, not carried labels.")},
        "gate_outcomes": {"stage_0": "no gate; mandatory halt for disposition (A1.2 T0.8)"},
        "open_items_for_stage_0_approval": [
            {"id": "O1", "item": "peak-finding prominence has no configured value",
             "detail": ("config.mechanism.peak_finding fixes method and criterion "
                        "('prominence') and smoothing=false, but sets no prominence LEVEL. At "
                        "Stage 1 that value selects the intraburst peak and therefore the "
                        "threshold. Stage 0 swept it at 0.01/0.02/0.05/0.10/0.20 as a fraction of "
                        "each event's own peak density and reports every value rather than "
                        "choosing one. It needs a value before Stage 1."),
             "evidence": "T0_1_raw_landscape.prominence_sweep, chart s0_1"},
            {"id": "O2", "item": "session-boundary definition for clipping",
             "detail": ("Extended-day-only and plus-RTH clipping give materially different "
                        "clipped fractions and therefore different D11 readings. Both reported; "
                        "not chosen."),
             "evidence": "T0_5_clipped_fraction, chart s0_5"},
            {"id": "O3", "item": "D4 = 1.2 saturates the too_few_prints fraction",
             "detail": ("At the configured F = 1.2 the derived floor is 1,237 prints against a "
                        "median achievable 283 in a 4-minute window; the median event's "
                        "too_few_prints fraction is 1.000 and 30 of 56 events have no usable "
                        "interval. Reported per A1.3, which asked for steep-or-flat and forbade a "
                        "recommendation."),
             "evidence": "T0_4_density_and_D4.sensitivity, chart s0_4"},
            {"id": "O4", "item": "the leftmost mode tracks the sweep floor",
             "detail": ("Across all five candidate floors the leftmost surviving mode lands in the "
                        "first histogram bin above the floor, within 0.05 decades. The config "
                        "guide asked whether the floor that clears the sub-microsecond mode and "
                        "the floor that begins destroying real structure are far apart; in the "
                        "tested range they are not separated."),
             "evidence": "T0_2_T0_3_floor_sensitivity.mode_minus_floor_decades, chart s0_2"},
            {"id": "O5", "item": "check-4 condition 2 excludes the largest candidate floor",
             "detail": ("D7_threshold_lo_ms = 10 caps the admissible D1_sweep_floor_us at 1000. "
                        "The 10000 us candidate would fail check-4 condition 2 at Stage 1 against "
                        "the frozen D7_lo. Marked per floor in T0_2_T0_3_floor_sensitivity."),
             "evidence": "T0_2_T0_3_floor_sensitivity.admissible_under_check4_cond2"}],
        "charts": man["charts"],
        "escalations_raised": [],
        "next": ("T0.8 HALT. Stage 0 does not flow into Stage 1 (A1.2). Awaiting Cooper's "
                 "disposition and the five Class M values."),
        "source": "research/phase_10c/t0_digest.py:main"}

    os.makedirs(rel("results/phase_10c/digests"), exist_ok=True)
    c10c.write_json(rel("results/phase_10c/digests/stage0_digest.json"), digest)
    print("stage 0 digest written")
    print(f"  waterfall reconciles: {recon}")
    print(f"  momentum_pct quarantine verified: {verification['d4_quarantine_A1_8']['verified']}")
    print(f"  charts: {len(man['charts'])}")
    print(f"  open items: {len(digest['open_items_for_stage_0_approval'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
