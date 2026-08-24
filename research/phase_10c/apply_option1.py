"""Option 1: the burst-envelope boundary IS the Stage 1 sub-burst threshold."""
import datetime as dt
import json

CFG, LOG = "config/phase_10c.json", "results/phase_10c/change_log.json"
c = json.load(open(CFG, encoding="utf-8"))
M = c["cooper_values"]["_class_M_fill_at_stage_0_approval"]

M["D2_max_cutoff_ms"] = "VOID"
c["a2_rules"]["D2_max_cutoff_status"] = (
    "VOID, Cooper option 1 (2026-08-24). A2.7 Revision 2 established there is no per-event "
    "fast/slow D2; the Stage 1 sub-burst threshold is the burst-envelope boundary "
    "(A2.7.D17), which needs no ceiling. The field is struck, not relaxed and not left "
    "pending -- the same disposition Phase 10b applied to its unreachable time-rescaling row.")

c["mechanism"]["threshold_search_superseded"] = {
    "superseded_on": "2026-08-24, Cooper option 1",
    "was": c["mechanism"]["threshold_search"],
    "now": {
        "rule": "A2.7.D17_burst_envelope_boundary -- argmax void across ALL troughs in the event",
        "ceiling": None,
        "void_thresholded": False,
        "no_peak_label": "unimodal",
        "no_threshold_label": "no_threshold",
    },
    "consequence_recorded": (
        "Prompt S3.2 (Correction 2) introduced the ceiling specifically to stop v4's unbounded "
        "trough scan. Option 1 removes it. Measured: v4's pathology has not recurred -- v4 gave a "
        "349 ns median sub-burst duration against 35.5 s for this boundary on raw intervals. "
        "D1 = 100 us now carries the anti-fragmentation work. Recorded so the removal is a visible "
        "decision rather than an unnoticed regression."),
}

c["stage_1"] = {
    "threshold_rule": "A2.7.D17_burst_envelope_boundary",
    "histogram_basis": "LOCALLY NORMALISED log intervals",
    "histogram_basis_note": (
        "Prompt Correction 3 (S3.3) makes the clock-time centered window the NORMALISER: each "
        "interval is divided by the local median over its window. T1.2 builds the window and T1.3 "
        "selects the threshold, in that order, so threshold selection operates on normalised "
        "intervals. Stage 0b's envelope measurement was on RAW intervals because Stage 0b applies "
        "no window by construction (A2.3), so the 35.5 s / 44.67 s figures are NOT the Stage 1 "
        "quantity and the D7 preview built on them does not transfer directly."),
    "threshold_in_seconds": (
        "The selected threshold is dimensionless -- a multiple of the local median. D7's band is in "
        "seconds, so the reportable threshold location is threshold x local_median at each "
        "interval, summarised per event by its median. Documented because it is an "
        "interpretation, not a restatement."),
    "d5_kernel_min": M["D5_first_kernel_min"],
    "labels": ["insufficient_context", "unimodal", "no_threshold"],
}

c["satisfiability_checks"]["check_2_stage_1_D15_exemption"] = (
    "D15_stage3_scope is Class M and still unset, so check 2 as literally written fails for Stage "
    "1. Recorded exemption: D15 is a Stage 3 SCOPE decision, consumed by no Stage 1 task, and "
    "unlike D16 it does not gate a statistic that a Stage 1 task produces -- so deferring it "
    "carries no pre-registration cost. Stage 1 proceeds; D15 is required before Stage 3. Flagged "
    "rather than silently waived.")

json.dump(c, open(CFG, "w", encoding="utf-8"), indent=2)

e = json.load(open(LOG, encoding="utf-8"))
e.append({"timestamp_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
          "authority": "Cooper, 2026-08-24, option 1",
          "field": "D2_max_cutoff_ms", "prior_class": "M", "new_class": "M",
          "prior_value": None, "new_value": "VOID",
          "stage_in_progress": "Stage 0b approved; Stage 1 starting",
          "task_in_progress": "option 1 carry-in, before T1.1",
          "outputs_already_existing_when_changed": [
              "results/phase_10c/digests/stage0b_digest.json",
              "results/phase_10c/artifacts/a3_d2_rule_confirmation.json"],
          "note": ("D2 is struck rather than valued. Its consumer, mechanism.threshold_search, is "
                   "superseded by the envelope rule in the same change.")})
json.dump(e, open(LOG, "w", encoding="utf-8"), indent=2)
print("option 1 applied. D2 =", M["D2_max_cutoff_ms"], "| D5 =", M["D5_first_kernel_min"])
