"""Apply the A2.7/A2.8 resolution: settled parts only. Conflicts C1/C2/C3 are recorded, not applied."""
import datetime as dt, json, os
import pandas as pd

CFG, LOG = "config/phase_10c.json", "results/phase_10c/change_log.json"
c = json.load(open(CFG, encoding="utf-8"))
M = c["cooper_values"]["_class_M_fill_at_stage_0_approval"]
prior_d4 = M.get("D4_median_precision_factor")

# --- A2.8: F = 1.5
M["D4_median_precision_factor"] = 1.5

# --- A2.7: D2 becomes per-event in scope; the selection rule is NOT set (conflict C1)
c["a2_rules"]["D2_scope"] = "per_event"
c["a2_rules"]["D2_scope_rationale"] = (
    "A2.7 resolution. T0b.1 found a median of 10 surviving peaks per event (max 17); a single "
    "segment-level split was always a compromise against that much per-event structure.")
c["a2_rules"]["D2_selection_rule_status"] = "UNSET -- pending conflict C1"
c["a2_rules"]["D2_selection_rule_conflict_C1"] = (
    "The drafted rule takes the first trough whose VOID PARAMETER clears 0.70. That contradicts "
    "config D13_void_parameter ('never thresholded in this phase', threshold null, marked "
    "deliberate and permanent) and prompt S4 ('This phase does NOT threshold on the void parameter "
    "at all', naming 0.70 as the retired v4 value). Not implemented. Either D13 and S4 are amended "
    "or the rule uses a different discriminator.")
c["a2_rules"]["D2_stage1_verification"] = (
    "Stage 1 must re-run the silent-selection check (largest peak at or below D2 without "
    "triggering no_intraburst_peak) using the per-event D2 and report the rate against the Stage "
    "0b baseline of 19/56 all-events, 15/50 primary. If the rate does not drop meaningfully, "
    "per-event D2 has not solved the problem it was adopted for.")

# --- labels
c["labels_carried"] = {
    "no_intraburst_peak": "no peak at or below D2",
    "too_few_prints": "window below the derived data floor (v4 count-based lineage)",
    "no_threshold": "void gate produced no threshold",
    "insufficient_context": ("A2.8: fewer than the derived floor of prints in the window for an "
                             "event/kernel pair. Carried forward, never given a fallback estimate."),
    "unimodal": "fewer than two surviving peaks",
}

# --- housekeeping: section-prefixed local labels
c["local_label_convention"] = {
    "rule": "Local decision labels carry their appendix section prefix.",
    "A2.7.D2": "fast/slow-mode interval boundary (local). NOT master D2, the 2025-data-exclusion flag.",
    "A2.8.D5": "first validation kernel (local). NOT master D5, the long-only burst-scale thesis.",
    "A2.8.D4": "median precision factor F (local).",
}

# --- D5/D6 derivation recorded; fields left unset pending the (a)/(b) choice and C3
c["a2_rules"]["D5_derivation_result"] = {
    "at_F": 1.5, "rth_floor": 156, "rth_clears_at_min": 8,
    "premarket_floor": 94, "premarket_clears_at_min": 1,
    "binding_segment": "rth",
    "implied_D5": 8, "implied_D6": [2, 8, 32],
    "status": "UNSET -- pending Cooper's (a)/(b) choice and conflict C3",
    "conflict_C3": ("The (a) option keeps 5 minutes, but A1.5 amended D5 from 5 to 4 precisely so "
                    "every Stage 2 kernel sits on the base-2 grid, and 5 is not a base-2 rung. The "
                    "live options are 4 (A1.5) or 8 (what A2.8's rule derives at F=1.5)."),
    "conflict_C2": ("Every clearing rung above was computed on CENTERED windows clipped at the RTH "
                    "open and close per A2.5. A2.8 says 'trailing window', which config D3_window "
                    "forbids (_forbidden_variants includes 'trailing') and prompt S3.3 forbids "
                    "explicitly. On a trailing window these numbers would differ."),
}
c["_governing_documents"].append("Phase-10c-Amendment-A2.7-A2.8-Resolution.md")
json.dump(c, open(CFG, "w", encoding="utf-8"), indent=2)

e = json.load(open(LOG, encoding="utf-8"))
e.append({"timestamp_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
          "authority": "Phase 10c Amendment 1 (A2.7/A2.8 resolution), A2.8",
          "field": "D4_median_precision_factor", "prior_class": "M", "new_class": "M",
          "prior_value": prior_d4, "new_value": 1.5,
          "stage_in_progress": "Stage 0b approved; Stage 1 not started",
          "task_in_progress": "A2.7/A2.8 resolution carry-in",
          "outputs_already_existing_when_changed": [
              "results/phase_10c/digests/stage0b_digest.json",
              "results/phase_10c/artifacts/t0b_3_5_density_floor.parquet"],
          "note": ("D4 is Class M and not a gate value, so A1.1's locking rule does not bar setting "
                   "it from measurement; A2.11 reclassified it to M for exactly that reason. "
                   "Logged because Stage 0b output measuring its sensitivity already existed.")})
json.dump(e, open(LOG, "w", encoding="utf-8"), indent=2)

# --- R1 accounting artifact
ev = pd.read_parquet("results/phase_10c/artifacts/t0b_2_void.parquet")
po = pd.read_parquet("results/phase_10c/artifacts/t0b_1_prominence_order.parquet")
ev["seg"] = ev.det_segment.fillna("unlabelled")
po["seg"] = po.det_segment.fillna("unlabelled")
tab = ev.groupby(["seg", "is_sidecar"]).size().unstack(fill_value=0)
acc = {
    "question": "56 total vs 53 in the T0b.6 gate table vs 50 implied by the 3+12 breakdown",
    "resolved": True, "events_missing": 0, "events_double_counted": 0,
    "by_segment": {s: {"primary": int(tab.loc[s].get(False, 0)),
                       "sidecar": int(tab.loc[s].get(True, 0)),
                       "total": int(tab.loc[s].sum())} for s in tab.index},
    "totals": {"all": int(len(ev)), "primary": int((~ev.is_sidecar).sum()),
               "sidecar": int(ev.is_sidecar.sum())},
    "explanation": {
        "56": "all dev-sample events, 50 primary + 6 sidecar",
        "53": ("the T0b.6 gate table = premarket 16 + rth 37. The gate is specified by segment and "
               "segment means premarket or rth, so the 3 omitted events are post(1) and "
               "unlabelled(2) -- ALL of them sidecar, which A1.6 already carries separately."),
        "50": "primary only, splitting premarket 15 + rth 35"},
    "silent_failure_figure": {
        "19_of_56": "counts ALL events including sidecar",
        "published_breakdown_3_of_15_and_12_of_35": "was PRIMARY ONLY, totalling 15 of 50",
        "sidecar_contribution": int(po[po.is_sidecar].slow_is_taller.sum()),
        "identity": "15 primary + 4 sidecar = 19",
        "defect": ("presentation, not population: one figure quoted on all-56 with its breakdown "
                   "on primary-only in the same sentence. Stage 1 names the population inline for "
                   "every count.")},
    "source": "research/phase_10c/apply_a3.py",
}
json.dump(acc, open("results/phase_10c/artifacts/a3_event_accounting.json", "w",
                    encoding="utf-8"), indent=2)
print("applied. D4 =", M["D4_median_precision_factor"], "| D2 scope =", c["a2_rules"]["D2_scope"])
print("class M:", json.dumps(M))
print("accounting artifact written; events_missing =", acc["events_missing"])
