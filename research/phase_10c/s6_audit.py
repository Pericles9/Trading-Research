"""
Phase 10c -- S6 satisfiability audit, evaluated PER STAGE per Amendment A1.9.

Target stage is taken from the command line (default 0). Reads the committed
config and the repo; runs no pipeline code and touches no real event data
beyond artifact metadata.

A1.9: "check 2 is evaluated per stage, not once. Stage 0 requires only the Class E
values present. Stage 1 requires Class E and Class M both present and Stage 0
approved."

S5 / A1.9: "no [Cooper] value is ever filled by the agent. Not inferred, not
defaulted, not copied from the v4 configuration. An empty field is a halt."

Usage: .venv/Scripts/python.exe research/phase_10c/s6_audit.py [stage]
"""
from __future__ import annotations

import hashlib
import json
import os
import sys

CFG = "config/phase_10c.json"
OUT = "results/phase_10c/artifacts/s6_satisfiability_audit_stage{stage}.json"


def main() -> int:
    stage = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    cfg = json.load(open(CFG, encoding="utf-8"))
    chash = hashlib.sha256(open(CFG, "rb").read()).hexdigest()[:8]
    cv = cfg["cooper_values"]
    classE = cv["_class_E_fill_before_stage_0"]
    classM = cv["_class_M_fill_at_stage_0_approval"]
    empty_E = sorted(k for k, v in classE.items() if v is None)
    empty_M = sorted(k for k, v in classM.items() if v is None)

    rows = []

    # ---------------------------------------------------------------- check 1
    c1 = {
        "check": "1 measurable",
        "verdict": "PASS",
        "basis": ("Re-confirmed from the 2026-08-22 audit and unchanged by A1. "
                  "filtered_trades carries sip_timestamp, sequence_number, price, size. "
                  "Detection anchors and detection prices exist in "
                  "results/phase_10/artifacts/v2_r13_detection.parquet. Dependencies present: "
                  "exchange_calendars 4.13.2 (D3 session clipping), scipy 1.17.0 "
                  "(find_peaks prominence), plotly 6.5.2, kaleido, duckdb 1.4.4."),
        "a1_8_quarantine_registered": ("filtered_trades.momentum_pct" in
                                       cfg["quarantine"]["columns"]),
        "quarantine_columns": cfg["quarantine"]["columns"],
        "stage_0_uses_no_cooper_value": True,
        "stage_0_task_inputs": {
            "T0.1": "raw intervals only",
            "T0.2": f"candidate floors {cfg['stage_0_sweeps']['T0_2_candidate_sweep_floors_us']} us",
            "T0.3": "largest peak per candidate floor",
            "T0.4": f"candidate precision factors {cfg['stage_0_sweeps']['T0_4_candidate_precision_factors']}",
            "T0.5": f"candidate kernels {cfg['stage_0_sweeps']['T0_5_candidate_kernels_min']} min",
            "T0.6": f"anchor variants {cfg['stage_0_sweeps']['T0_6_anchor_variants']}",
            "T0.7": "population counts"},
    }
    rows.append(c1)

    # ---------------------------------------------------------------- check 2
    if stage == 0:
        required, missing, req_label = classE, empty_E, "class_E only"
    else:
        required = {**classE, **classM}
        missing = empty_E + empty_M
        req_label = "class_E and class_M, stage 0 approved"
    c2 = {
        "check": "2 threshold set",
        "stage_evaluated": stage,
        "requirement": req_label,
        "config_rule": cfg["satisfiability_checks"][f"check_2_stage_{min(stage,1)}_requires"],
        "n_required": len(required),
        "n_present": len(required) - len(missing),
        "missing": missing,
        "verdict": "PASS" if not missing else "FAIL",
        "governing_rule": ("A1.9 / S5: no [Cooper] value is ever filled by the agent. Not "
                           "inferred, not defaulted, not copied from the v4 configuration. An "
                           "empty field is a halt."),
    }
    if stage == 0 and missing:
        c2["why_it_still_blocks_stage_0"] = (
            "Every Stage 0 task (T0.1-T0.7) is computable without these values -- Stage 0 "
            "produces no sub-bursts, selects no threshold and applies no normalisation window. "
            "The requirement is not computational, it is PRE-REGISTRATION. A1.1: Class E values "
            "'must be locked before any sub-burst exists', and A1.1's locking rule freezes them "
            "at Stage 0 approval so that a gate threshold cannot be set after seeing the "
            "landscape it will later judge. Running Stage 0 first and setting D7/D8/D9 afterwards "
            "would convert three pre-registered gates into descriptions of data already seen.")
    rows.append(c2)

    # ---------------------------------------------------------------- check 3
    ds = cfg["dev_sample"]
    c3 = {
        "check": "3 reachable",
        "verdict": "PASS",
        "resolutions": {
            "A1 dev sample": (f"Resolved by A1.6. dev_sample = {ds['name']}, n={ds['n']}, "
                              f"stratified by {ds['stratification']}. The 'momentum percentage "
                              "decile' wording is struck; dev_sample_v3.json is not used. "
                              "Verified 2026-08-22: dev_v4_primary has 50 of 50 detection anchors, "
                              "dev_sample_v3 has 0 of 50."),
            "A2 detection anchor": (f"Resolved by A1.6. Provisional variant "
                                    f"'{cfg['data']['detection_anchor_variant']}', confirmed or "
                                    "revised at Stage 0 approval on the T0.6 migration matrix."),
            "A3 population": ("Resolved by A1.7. Split into D14_population and D15_stage3_scope, "
                              "both Class M, both read from T0.7. Not required for Stage 0."),
            "sidecar": (f"A1.6: {ds['sidecar_events']['n']} sidecar events are "
                        f"{ds['sidecar_events']['disposition']} and reported "
                        f"{ds['sidecar_events']['reported']}.")},
        "note": "Stage 0 charts and digest fields are all reachable from the dev sample.",
    }
    rows.append(c3)

    # ---------------------------------------------------------------- check 4
    grid = [2 ** k for k in range(0, 10)]
    k_s2 = cfg["settled"]["D6_stage2_kernels_min"]
    d5 = cfg["settled"]["D5_first_kernel_min"]
    on_grid = {str(k): (k in grid) for k in k_s2}
    c4 = {
        "check": "4 non-contradictory",
        "stage_evaluated": stage,
        "verdict": "NOT APPLICABLE AT STAGE 0" if stage == 0 else "PENDING",
        "conditions": cfg["satisfiability_checks"]["check_4_conditions"],
        "removed_condition": cfg["satisfiability_checks"]["_removed_condition"],
        "c1_finding_resolved": ("A1.4 accepts the finding and replaces the condition. The max "
                               "cutoff bounds where the intraburst PEAK may sit, not where the "
                               "threshold lands; the threshold is a trough to the right of that "
                               "peak and routinely sits above the cutoff."),
        "c2_finding_resolved": {
            "note": ("A1.5 moves D5 to 4 min and D6 to {1, 4, 32}. All three Stage 2 kernels now "
                     "sit on the base-2 Stage 3 grid at rungs 0, 2 and 5."),
            "D5_first_kernel_min": d5, "D5_on_grid": d5 in grid,
            "D6_stage2_kernels_min": k_s2, "D6_on_grid": on_grid,
            "grid_first_10": grid},
        "why_na_at_stage_0": ("Both surviving conditions reference D1_sweep_floor_us, a Class M "
                              "value set at Stage 0 approval. Neither is evaluable before Stage 0 "
                              "runs, and neither is required by any Stage 0 task."),
    }
    # Forward-looking arithmetic on the surviving check-4 condition 2.
    floors = cfg["stage_0_sweeps"]["T0_2_candidate_sweep_floors_us"]
    c4["forward_risk_D7lo_vs_D1"] = {
        "condition": "D7_threshold_lo_ms must exceed D1_sweep_floor_us by >= 1 order of magnitude",
        "candidate_D1_floors_us": floors,
        "implied_min_D7_lo_ms_per_floor": {str(f): (f * 10) / 1000.0 for f in floors},
        "D7_lo_ms_that_satisfies_every_candidate_floor": (max(floors) * 10) / 1000.0,
        "risk": ("D7_threshold_lo_ms is Class E and frozen at Stage 0 approval; D1_sweep_floor_us "
                 "is Class M and read from Stage 0 output. If the pair fails this condition at "
                 "Stage 1, A1.1's locking rule leaves no way to repair it -- revising a Class E "
                 "gate value after its stage's output exists requires a new phase number. Setting "
                 "D7_threshold_lo_ms at or above the value shown satisfies the condition against "
                 "every candidate floor in T0.2's sweep."),
        "reported_not_recommended": True,
    }
    rows.append(c4)

    verdicts = {r["check"]: r["verdict"] for r in rows}
    blocking = [r["check"] for r in rows if r["verdict"] == "FAIL"]
    out = {
        "phase": "10c", "task": "S6 satisfiability audit", "stage_evaluated": stage,
        "config": CFG, "config_hash": chash,
        "governing_documents": cfg["_governing_documents"],
        "protocol": "A1.9 -- check 2 evaluated per stage, not once",
        "no_pipeline_code_executed": True,
        "no_real_event_processed": True,
        "checks": rows,
        "verdicts": verdicts,
        "blocking_checks": blocking,
        "action": ("HALT AND ESCALATE. Stage 0 not started."
                   if blocking else "All checks clear for this stage."),
        "source": "research/phase_10c/s6_audit.py:main",
    }
    p = OUT.format(stage=stage)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2)

    print(f"Phase 10c S6 audit -- stage {stage}, config hash {chash}")
    for r in rows:
        print(f"  check {r['check']:22s} {r['verdict']}")
    if c2["missing"]:
        print(f"\n  check 2 missing ({len(c2['missing'])} of {c2['n_required']}):")
        for m in c2["missing"]:
            print(f"     {m} = null")
    fr = c4["forward_risk_D7lo_vs_D1"]
    print(f"\n  forward arithmetic: D7_threshold_lo_ms >= "
          f"{fr['D7_lo_ms_that_satisfies_every_candidate_floor']} ms satisfies check-4 "
          f"condition 2 against every candidate D1 floor {fr['candidate_D1_floors_us']} us")
    print(f"\n  {out['action']}")
    print(f"  written: {p}")
    return 2 if blocking else 0


if __name__ == "__main__":
    raise SystemExit(main())
