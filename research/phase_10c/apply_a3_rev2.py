"""Carry Revision 2: A2.7 demoted, burst-envelope boundary registered as its own decision."""
import datetime as dt
import json

import pandas as pd

CFG, LOG = "config/phase_10c.json", "results/phase_10c/change_log.json"
c = json.load(open(CFG, encoding="utf-8"))
d = pd.read_parquet("results/phase_10c/artifacts/a3_d2_rule_comparison.parquet")
p = d[~d.is_sidecar]
E = c["cooper_values"]["_class_E_fill_before_stage_0"]

c["a2_rules"]["A2_7_status"] = "DEMOTED to descriptive diagnostic, Revision 2 (2026-08-24)"
c["a2_rules"]["A2_7_demotion_reason"] = (
    "A2.7's single-boundary premise assumed one fast mode, one slow mode, one boundary. T0b.1 "
    "measured a median of 10 surviving peaks per event (max 17). Two structurally different "
    "candidate-set rules were tested head to head; they agree on which trough is D2 on only "
    "12/56 events (21.4%) and where they disagree the median differs by 3.5 decades -- two "
    "different objects, not two estimates of one. Neither reduces the silent-failure rate. "
    "Chasing a fourth variant would be searching for whichever specification makes the check "
    "pass, the failure mode already ruled out for Kleinberg, ACD and the Allan/Fano knee.")
c["a2_rules"]["A2_7_silent_failure_reporting"] = (
    "Carried into the Stage 1 digest as a DESCRIPTIVE report, not a gate: 58.0% (29/50) under "
    "rule A and 64.0% (32/50) under rule B, primary population. Caveat carried with the numbers: "
    "this is NOT a clean deterioration from Stage 0b's 30%. That baseline asked whether the later "
    "of the top-two peaks was taller, a hazard proxy with no D2 in existence. These figures "
    "measure the actual A2.7 question against a computed D2 for the first time. Different "
    "statistics; 30 -> 58 is not a valid before/after.")
c["a2_rules"]["A2_7_peak_ranking"] = (
    "Resolved to PROMINENCE, not height. Height was inconsistent with how peaks are found and "
    "kept everywhere else in the pipeline (prominence-filtered against the Poisson floor). Moot "
    "for the envelope rule, where all troughs are candidates, but recorded.")
c["a2_rules"]["D2_max_cutoff_status"] = (
    "A2.7 Revision 2 states there is no per-event fast/slow D2. The field remains null and its "
    "consumer -- mechanism.threshold_search, which anchors the trough search to 'largest peak at "
    "or below D2' -- has NOT been formally superseded. See open_question_stage1_threshold_source.")

env = {
    "label": "A2.7.D17_burst_envelope_boundary",
    "section_prefix_note": ("Prefixed per the housekeeping convention. Distinct from A2.7.D2 (the "
                            "void fast/slow boundary, now reframed away) and from master "
                            "D-numbers in docs/Universe-Decisions.md."),
    "definition": ("argmax void parameter across ALL troughs in the event; no threshold applied "
                   "anywhere, per D13_void_parameter. Peaks are those surviving the "
                   "Poisson-derived per-peak floor (A2.4 Part 1); each trough's void is taken "
                   "against its immediately adjacent surviving peaks."),
    "measures": ("where burst-period activity gives way to background or quiet activity -- a "
                 "burst-envelope boundary, NOT an intraburst fast/slow split."),
    "provenance": "Rule B in a3_d2_rule_confirmation.json, relabelled per Revision 2.",
    "dev_sample_measurement": {
        "n_primary": int(len(p)),
        "median_seconds_pooled": float(10 ** p.d2_ruleB_log10s.median()),
        "median_seconds_by_segment": {s: float(10 ** g.d2_ruleB_log10s.median())
                                      for s, g in p.groupby("det_segment")},
        "median_void": float(d.void_ruleB.median()),
        "check4_cond1_pass_share": 49 / 56,
        "_note": "dev sample only; indicative, not the Stage 1 population figure"},
    "relationship_to_prompt_s3_2": (
        "S3.2 (Correction 2) introduced a CEILING on the trough search precisely to stop v4's "
        "unbounded scan. This rule is an unbounded scan over all troughs, so it drops that "
        "ceiling. Measured consequence: v4's pathology has NOT recurred -- v4 produced a 349 ns "
        "median sub-burst duration, this boundary sits at 35.5 s pooled, eight orders of "
        "magnitude away. D1 = 100 us now does the anti-fragmentation work the ceiling was "
        "carrying. Recorded so the dropped ceiling is a visible decision rather than an unnoticed "
        "regression."),
    "status": "adopted as a reported quantity; its role in Stage 1 threshold selection is NOT stated",
}
c["a2_rules"]["A2_7_D17_burst_envelope_boundary"] = env

c["open_question_stage1_threshold_source"] = {
    "question": "Which quantity is the Stage 1 sub-burst threshold?",
    "option_1": ("the burst-envelope boundary (A2.7.D17). Then D2_max_cutoff_ms is void and "
                 "mechanism.threshold_search is superseded."),
    "option_2": ("the S3.2 D2-anchored intraburst-peak search stands and the envelope boundary is "
                 "an additional reported quantity. Then D2_max_cutoff_ms still needs a value, "
                 "which A2.7 Revision 2 says does not exist."),
    "why_it_matters": ("The two give materially different Stage 1 pipelines, and under option 1 "
                       "the Stage 1 scale-sanity gate is likely to fire -- see d7_gate_preview."),
    "d7_gate_preview": {
        "band_seconds": [E["D7_threshold_lo_ms"] / 1000.0, E["D7_threshold_hi_s"]],
        "envelope_median_seconds_by_segment": {
            s: float(10 ** g.d2_ruleB_log10s.median()) for s, g in p.groupby("det_segment")},
        "premarket_in_band": True, "rth_in_band": False,
        "consequence": ("RTH median 44.67 s exceeds D7_threshold_hi_s = 10 s. The Stage 1 gate "
                        "halts if EITHER segment is out of band. This is the dev sample, not the "
                        "D14 population, so it is indicative rather than binding -- but it is the "
                        "arithmetic available before the run."),
        "d7_hi_rationale_cross_check": ("The config guide set D7_hi as 'the largest inter-trade "
                                        "gap you would still call burst interior', noting that a "
                                        "30 s threshold makes a 25 s silence burst interior and is "
                                        "incoherent for a scalp. At 44.67 s a 40 s silence would "
                                        "count as burst interior.")},
}
json.dump(c, open(CFG, "w", encoding="utf-8"), indent=2)

e = json.load(open(LOG, encoding="utf-8"))
e.append({
    "timestamp_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
    "authority": "Phase 10c Amendment 1, Revision 2 (2026-08-24)",
    "field": "A2.7 status + A2.7.D17_burst_envelope_boundary",
    "prior_class": "gate", "new_class": "descriptive diagnostic",
    "prior_value": "A2.7 silent-failure check as a Stage 1 gate",
    "new_value": "descriptive report; Rule B relabelled as the burst-envelope boundary",
    "stage_in_progress": "Stage 0b approved; Stage 1 not started",
    "task_in_progress": "Revision 2 carry-in",
    "outputs_already_existing_when_changed": [
        "results/phase_10c/artifacts/a3_d2_rule_confirmation.json",
        "results/phase_10c/artifacts/a3_d2_rule_comparison.parquet"],
    "note": ("Logged because the demotion was decided after the measurement that motivated it "
             "existed. A2.7 was never a Class E pre-registered gate value, so A1.1's locking rule "
             "does not bar the change; recorded as a fact.")})
json.dump(e, open(LOG, "w", encoding="utf-8"), indent=2)
print("Revision 2 applied. New decision:", env["label"])
print("  envelope median by segment:", env["dev_sample_measurement"]["median_seconds_by_segment"])
