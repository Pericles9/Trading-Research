"""Apply Amendment 2's config edits. Run once, before any Stage B task."""
from __future__ import annotations

import json
import pathlib

p = pathlib.Path("config/phase_11.json")
c = json.loads(p.read_text())

c["spec"]["amendment_2"] = "prompts/phase_11_amendment_2.md"
c["spec"]["governing"] = (
    "Amendment 1 over v1 (Cooper 2026-08-15), as further amended by Amendment 2 "
    "(Cooper 2026-08-16, T4 gate). A 25-row v2 rewrite was circulated 2026-08-15, "
    "interrupted, and discarded; one v2 element was imported by explicit decision - "
    "T2a's hard/degraded state split.")
c["spec"]["escalation_row_ids"] = [
    "0", "1", "2", "3", "4a", "4b", "5", "6", "7", "8", "9", "10", "11", "12", "13",
    "14", "15", "16", "17", "18", "19", "20", "21", "22", "23", "24", "25", "26",
    "27", "28", "29"]
c["spec"]["escalation_rows"] = 31
c["spec"]["row_count_note"] = (
    "A2 states 'now 29 rows'. The explicit enumeration is 31: Amendment 1's 24 "
    "(0,1,2,3,4a,4b,5..22) plus A2-11's seven new rows (23..29). 29 is the highest row "
    "NUMBER, not the row count - 4a/4b split one number into two, and numbering starts "
    "at 0. Recorded at T0c as an editorial discrepancy, not a check failure; the audit "
    "covers all 31.")

# --- A2-2 / D16: reference convention -----------------------------------
c["d16_reference_convention"] = {
    "status": "Cooper, T4 gate 2026-08-16",
    "reference_midpoint": "contemporaneous consolidated best quote at delta = 0",
    "basis": "sip_timestamp",
    "secondary_asof_key": "sequence_number",
    "single_basis_all_segments": True,
    "why_delta_zero": (
        "The +100us peak sits 0.0003 above delta=0 in at-or-inside share, while the "
        "measured between-segment peak instability is 7 rungs. Selecting the peak would "
        "fit a signal two orders of magnitude below the measured noise."),
    "why_sip": (
        "Differences are marginal in both directions (sip higher in RTH 0.9808 vs "
        "0.9779; participant higher in premarket). Segment is a headline reporting axis, "
        "so switching basis by segment would put a measurement artifact on the axis "
        "being compared across. sip wins in RTH, the cell row 11 names."),
    "t6e_robustness": "participant_timestamp medians reported as one table; not primary, "
                      "not charted, no claim rests on it",
}

# --- A2-3 / D17: exclusion rule -----------------------------------------
c["d17_exclusion_rule"] = {
    "status": "Cooper, T4 gate 2026-08-16",
    "exclude_row_if": ["bid_price > ask_price (crossed)", "bid_price IS NULL",
                       "ask_price IS NULL", "bid_price <= 0", "ask_price <= 0",
                       "one side missing", "bid_size IS NULL OR bid_size = 0",
                       "ask_size IS NULL OR ask_size = 0"],
    "carry": ["locked (bid_price = ask_price)"],
    "why_locked_carried": ("A real transient state with a genuine zero spread; dropping "
                           "it biases measured spread upward."),
    "sql_predicate": ("(bid_price IS NULL OR ask_price IS NULL OR bid_price <= 0 OR "
                      "ask_price <= 0 OR bid_price > ask_price OR bid_size IS NULL OR "
                      "bid_size = 0 OR ask_size IS NULL OR ask_size = 0)"),
    "note_vs_stage_a": ("This is Stage A's state_hard_unusable UNION the zero-size "
                        "predicates, MINUS locked. Stage A's state_degraded bundled "
                        "locked with zero-size; D17 separates them."),
    "no_event_excluded_on_quality": True,
    "covariate_instead": "unusable_time_share per event x segment carried into "
                         "event_quote_metrics_v1 (T5b); T7g reports the headline with "
                         "and without the 3 events above 1% unusable share",
}

# --- A2-4 / D18: Stage B population -------------------------------------
c["d18_stage_b_population"] = {
    "status": "Cooper, T4 gate 2026-08-16",
    "compute": "all 15,369 detection-universe events, all three segments",
    "decision_cell": "RTH only",
    "premarket_and_post": "reported and charted; no kill/clear decision taken from them",
    "quotes_ingested_false": "excluded per D15, counted as its own row in the filter "
                             "waterfall",
    "no_staleness_based_event_exclusion": True,
}

# --- A2-6 / D19: units ---------------------------------------------------
c["d19_units"] = {
    "status": "Cooper, T4 gate 2026-08-16",
    "rule": "Every spread and cost quantity is reported in BOTH basis points and cents. "
            "Neither unit alone.",
    "baseline_proxy_banned": "No T-1 or T-3 spread is used as a proxy for detection-time "
                             "cost, in either unit.",
    "why": ("RTH median quoted spread falls 165.0 -> 83.9 bp across T-3 -> T=0 (-49%) "
            "while cents goes 3.64 -> 3.79 (+4%). Implied price ~$2.21 -> ~$4.52. The "
            "bp compression is the denominator growing."),
    "guarded_by": "escalation row 27",
}

# --- A2-7: impact windows ------------------------------------------------
c["impact"]["impact_windows_seconds"] = [1, 5, 30, 60]
c["impact"]["min_window_seconds"] = 1
c["impact"]["why_no_sub_second"] = (
    "Trade-weighted BBO age is an RTH median of 1,372.6 ms, so any sub-second window is "
    "dominated by exact-zero delta-mid and attenuates toward zero - the Phase 9 zero-atom "
    "pathology that fixed the median in 34 of 450 grid cells. Guarded by escalation "
    "row 23.")

# --- A2-9: bounded watchdog ---------------------------------------------
c["runtime"]["query_watchdog_scope"] = (
    "Applies to EVERY query in the phase except the single budgeted T5b pass, which is "
    "instead bounded by runtime_ceiling_seconds. The ceiling IS that query's watchdog. "
    "No query anywhere in the phase is unbounded. Cooper bounded the agent-authored "
    "carve-out in A2-9; guarded by escalation row 26.")
c["runtime"]["t5b_bound_seconds"] = 21600
c["runtime"]["runtime_ceiling_desc"] = (
    "6 hours. Ceiling on the T5a extrapolation AND the hard bound on the T5b pass "
    "itself. Accepted by Cooper in A2-9. T5a's dev-tier extrapolation is the primary "
    "protection; the ceiling is the backstop.")

# --- A2-5: kill threshold confirmed --------------------------------------
c["cooper_thresholds"]["row_11_kill_threshold_confirmed"] = "2026-08-16, A2-5, unchanged"
c["cooper_thresholds"]["cost_multiple_reporting"] = (
    "The 1x column remains the SOLE trigger for row 11. The 1.5x column is reported with "
    "EQUAL PROMINENCE in every table and on every chart. The expectation that 1.5x is "
    "the more honest read of realised cost was set at the T4 gate BEFORE Stage B ran; it "
    "is a statement about which column to read, not a prediction, and licenses no "
    "evaluative sentence - row 18 applies unchanged.")

# --- A2-0: standing qualifier -------------------------------------------
c["standing_qualifier"] = {
    "text": ("Effective spread measures the cost of the average print, not the cost of a "
             "specific order. Depth, queue position and fill probability are not "
             "measured in this phase."),
    "required_verbatim_in": ["REPORT.md section T7", "caption of chart 05",
                             "caption of chart 06", "caption of chart 07"],
    "guarded_by": "escalation row 29",
}

# --- A2-8: cache staleness columns --------------------------------------
c["outputs"]["stage_b_table_required_columns"] = [
    "bbo_age_at_trade_p50", "bbo_age_at_trade_p95", "trade_share_age_gt_1s",
    "trade_share_age_gt_60s", "n_bbo_changes", "unusable_time_share"]
c["outputs"]["stage_b_required_columns_guard"] = "escalation row 24, checked at T5c"

p.write_text(json.dumps(c, indent=2))
print("config patched")
print("  impact_windows:", c["impact"]["impact_windows_seconds"])
print("  rows enumerated:", len(c["spec"]["escalation_row_ids"]))
print("  D16/D17/D18/D19 present:",
      all(k in c for k in ["d16_reference_convention", "d17_exclusion_rule",
                           "d18_stage_b_population", "d19_units"]))
