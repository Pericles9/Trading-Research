"""Apply Amendment A2 to config/phase_10c.json, and log the Class E change per A1.1."""
import datetime as dt
import json
import os

ROOT = r"E:\Trading Research"
CFG = os.path.join(ROOT, "config", "phase_10c.json")
LOG = os.path.join(ROOT, "results", "phase_10c", "change_log.json")

c = json.load(open(CFG, encoding="utf-8"))
cv = c["cooper_values"]
E = cv["_class_E_fill_before_stage_0"]
M = cv["_class_M_fill_at_stage_0_approval"]

prior_d4 = E.get("D4_median_precision_factor")
prior_d5 = c["settled"].get("D5_first_kernel_min")
prior_d6 = c["settled"].get("D6_stage2_kernels_min")

# --- A2.11: D4 reclassified E -> M and HELD (was 1.2, set as Class E before Stage 0)
E.pop("D4_median_precision_factor", None)
M["D4_median_precision_factor"] = None

# --- A2.11: D16 is new, Class E, gates T0b.6, [Cooper], no value supplied
E["D16_min_median_void"] = None

# --- A2.8: D5 and D6 become Class M, derived at Stage 0b approval
c["settled"].pop("D5_first_kernel_min", None)
c["settled"].pop("D6_stage2_kernels_min", None)
M["D5_first_kernel_min"] = None
M["D6_stage2_kernels_min"] = None

cv["_class_E_note"] = ("A2.11 register. D4 moved to Class M; D16 added, gates T0b.6 and must be "
                       "set before Stage 0b runs.")
cv["_class_M_note"] = ("A2.6 dispositions: D1=100, D11=64, D14=20951 set at Stage 0 approval. "
                       "D2, D4, D5, D6, D15 held for Stage 0b approval. D5/D6 are DERIVED per "
                       "A2.8, not chosen.")

# --- A2.5: clip at the regular-session open and close
c["settled"]["D3_window"]["session_boundary"] = "clip_at_rth_open_and_close"
c["settled"]["D3_window"]["_a2_5"] = (
    "Resolved by A2.5 against open item O2. Premarket median print density 131.6/min vs RTH "
    "7.5/min is a 17x inversion; a centered window spanning 09:30 mixes two regimes and the local "
    "median is set by whichever side is denser. Extended-day-only clipping would permit that. "
    "D11 reads from the plus-RTH column of T0.5.")

# --- A2.7 D2 rule, A2.8 D5/D6 rules, A2.9 Stage 3 IO requirement
c["a2_rules"] = {
    "D2_selection_rule": ("From T0b.1's joint distribution of the two most prominent peak "
                          "locations: if the fast-mode p95 and the slow-mode p5 are separated, set "
                          "D2 in the gap positioned to keep no_intraburst_peak incidence low. If "
                          "they OVERLAP, no single global D2 exists -- do not pick a compromise; "
                          "report the overlap and escalate."),
    "D2_silent_failure_mode": ("In a sparse event the SLOW mode can be the taller peak. If D2 sits "
                               "above it, 'largest peak at or below D2' selects the slow mode as "
                               "the intraburst peak and the trough search runs to its right, "
                               "returning nothing or a meaningless value WITHOUT triggering "
                               "no_intraburst_peak."),
    "D5_derivation": ("Smallest rung on the base-2 grid at which the median RTH event clears the "
                      "D4 derived data floor, using near-detection density from T0b.5."),
    "D6_derivation": "{D5/4, D5, D5*4}, low rung >= 1 min, high rung <= D11.",
    "stage3_io_requirement": ("Each event's trades are pulled and aggregated ONCE; kernels loop in "
                              "memory over that single materialisation. No re-query per kernel. "
                              "Realistic Stage 3 cost is ~2-3x Stage 1, not Nx."),
    "prominence_floor_derivation": ("A2.4 Part 1: histogram bin counts carry Poisson noise of "
                                    "order sqrt(k). A peak whose prominence does not exceed the "
                                    "counting noise in its own bin is not distinguishable from "
                                    "noise. Derive a per-event minimum prominence on that basis."),
    "prominence_sensitivity_reporting": ("A2.4 Part 2: report the T0b.4 displacement distribution "
                                         "BESIDE the D9 slope distribution in the Stage 2 digest. "
                                         "No pass threshold is attached in this phase."),
}

c["stage_0b_sweeps"] = {
    "T0b_1_prominence_primary": None,
    "_prominence_note": "Derived per event from the Poisson floor (A2.4 Part 1); no constant.",
    "T0b_4_prominence_sweep": [0.01, 0.02, 0.05, 0.10, 0.20],
    "T0b_3_candidate_precision_factors": [1.1, 1.2, 1.3, 1.5],
    "T0b_5_near_detection_window_min": 30,
    "unimodal_label": "unimodal",
}

c["gates"]["stage_0b_bimodality"] = {
    "statistic": "median void parameter at the deepest trough between the two most prominent peaks",
    "min": "D16_min_median_void",
    "evaluated_by": "segment",
    "halt_condition": "median void below D16 in either segment",
    "_on_halt": ("The correct conclusion is that the log-interval decomposition is the wrong "
                 "instrument for this data -- not that a parameter needs adjusting. Do not alter "
                 "D1 or the prominence level to rescue the run."),
}
c["satisfiability_checks"]["check_2_stage_0b_requires"] = "class_E only (now includes D16)"
c["_governing_documents"].append("Phase-10c-Amendment-A2.md")

json.dump(c, open(CFG, "w", encoding="utf-8"), indent=2)

# --- A1.1 change log: D4 was Class E and Stage 0 output already existed
os.makedirs(os.path.dirname(LOG), exist_ok=True)
entries = json.load(open(LOG, encoding="utf-8")) if os.path.exists(LOG) else []
entries.append({
    "timestamp_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
    "authority": "Phase-10c-Amendment-A2.md A2.11",
    "field": "D4_median_precision_factor",
    "prior_class": "E", "new_class": "M",
    "prior_value": prior_d4, "new_value": None,
    "stage_in_progress": "Stage 0 approved; Stage 0b not started",
    "task_in_progress": "A2 carry-in, before any Stage 0b task",
    "outputs_already_existing_when_changed": [
        "results/phase_10c/digests/stage0_digest.json",
        "results/phase_10c/artifacts/t0_4_density_d4.parquet",
        "results/phase_10c/charts/s0_4_d4_sensitivity.html"],
    "note": ("A1.1 requires this entry because D4 was a Class E value and Stage 0 output that "
             "measured its sensitivity already existed when it changed. A2.11 reclassifies it to "
             "Class M on the grounds that Stage 0 answered A1.3's flat-or-steep question with "
             "'steep', making it a data question. D4 is not a gate value. Recorded as a fact, "
             "with no evaluative language attached."),
})
entries.append({
    "timestamp_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
    "authority": "Phase-10c-Amendment-A2.md A2.8",
    "field": "D5_first_kernel_min / D6_stage2_kernels_min",
    "prior_class": "settled", "new_class": "M (derived)",
    "prior_value": {"D5": prior_d5, "D6": prior_d6}, "new_value": None,
    "stage_in_progress": "Stage 0 approved; Stage 0b not started",
    "task_in_progress": "A2 carry-in, before any Stage 0b task",
    "outputs_already_existing_when_changed": ["results/phase_10c/digests/stage0_digest.json"],
    "note": ("Neither was a Class E gate value, so A1.1's locking rule does not apply; logged for "
             "completeness because both were previously 'settled' and are now derived."),
})
json.dump(entries, open(LOG, "w", encoding="utf-8"), indent=2)

print("A2 applied.")
print("  class E now:", json.dumps(cv["_class_E_fill_before_stage_0"]))
print("  class M now:", json.dumps(cv["_class_M_fill_at_stage_0_approval"]))
print("  change_log entries:", len(entries))
