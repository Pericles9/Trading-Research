"""Apply Amendment 3's config edits. Run once."""
from __future__ import annotations

import json
import pathlib

p = pathlib.Path("config/phase_11.json")
c = json.loads(p.read_text())

c["spec"]["amendment_3"] = "prompts/phase_11_amendment_3.md"
c["spec"]["escalation_row_ids"] = c["spec"]["escalation_row_ids"] + ["30", "31", "32"]
c["spec"]["escalation_rows"] = 34
c["spec"]["row_count_note"] = (
    "A3-0: report the ENUMERATED count, not the highest row number. Enumeration is 34 "
    "(0,1,2,3,4a,4b,5..29,30,31,32); highest number is 32. 4a/4b split one number into "
    "two and numbering starts at 0.")

c["cooper_thresholds"]["row_30_tie_price_error_p95_bp_max"] = None
c["cooper_thresholds"]["row_30_proposal_by_cooper_bp"] = 25.0
c["cooper_thresholds"]["row_30_status"] = (
    "UNSET. A3-4 marks row 30 [Cooper] and states a PROPOSAL of > 25 bp with reasoning, "
    "plus 'for Cooper to set or overrule'. Under the standing rule that [Cooper] "
    "thresholds are set before execution and are not the agent's to propose or fill, the "
    "proposal is not adopted until Cooper states it. Row 30 gates T4c, step 5 of the "
    "A3-6 order; T2e-i and T5a (steps 1-2) are explicitly unblocked and run first. "
    "Flagged at the T0c re-audit.")

c["charts"] = {"twin_axis_deviation": (
    "A3-1: charts 05 and 09 ship as two vertically stacked panels sharing the x-axis - "
    "upper basis points, lower cents, identical faceting and identical n annotations on "
    "both, single file. The prompt specified twin y-axes, which this project's "
    "visualization standard forbids outright; Phase 9 chart 06 set the precedent. "
    "Recorded in each chart caption. D19 and escalation row 27 are satisfied because "
    "both units are present. Rationale (A3-1): bp and cents move in OPPOSITE directions "
    "here, so twin axes would let a reader see one line, read a slope, and believe they "
    "had seen both units.")}

c["d17_exclusion_rule"]["a_fortiori_note"] = (
    "A3-2: the D17-excluded set is a STRICT SUBSET of the row 5 union - T2a's union "
    "included locked, D17 carries it, so D17-excluded = row 5 union MINUS locked. A "
    "subset of a set whose RTH clock-time share measured exactly 0.000000 also measures "
    "0. The passed gate transfers to the narrower rule a fortiori, not merely by "
    "non-interaction. T7h reports the locked clock-time share in the RTH decision cell "
    "so the carry decision is auditable.")

c["t4c_tie_audit"] = {
    "authority": "prompts/phase_11_amendment_3.md A3-3",
    "not_exposed": ("det_minute = MIN(minute_index) FILTER (high >= threshold) with "
                    "high = MAX(price). MAX and MIN over a set are tie-immune by "
                    "construction, so Phase 8's detection MINUTE is sound regardless of "
                    "the T4c result."),
    "exposed": ["det_price_lat0/1/5/15/30 (via first_price/last_price)",
                "Phase 9 t4_axis_grid entry_price and exit_price",
                "tick_close_t_minus_1_rth"],
    "measure_only": ("T4c-iv: measure and bound only. sequence_number is the available "
                     "tiebreak but applying it means rebuilding event_minute_bars_v2 and "
                     "re-deriving frozen artifacts - a Cooper decision, guarded by "
                     "escalation row 32."),
}

p.write_text(json.dumps(c, indent=2))
print("config patched; rows enumerated:", len(c["spec"]["escalation_row_ids"]))
print("row 30 threshold:", c["cooper_thresholds"]["row_30_tie_price_error_p95_bp_max"],
      "(proposal", c["cooper_thresholds"]["row_30_proposal_by_cooper_bp"], "bp)")
