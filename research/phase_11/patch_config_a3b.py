"""Record Cooper's resolution of the row-2 firing: option (ii)."""
from __future__ import annotations

import json
import pathlib

p = pathlib.Path("config/phase_11.json")
c = json.loads(p.read_text())

c["t4c_tie_audit"]["resolution"] = {
    "decision": "OPTION (ii) - Cooper, 2026-08-16, resolving the row-2 firing recorded in "
                "results/phase_11/artifacts/t0c_satisfiability_audit_a3.json.",
    "rule": "T4c is computed INSIDE the single budgeted T5b pass. One scan of "
            "filtered_trades produces both event_quote_metrics_v1 and the tie audit.",
    "pass_budget_effect": "Unchanged at exactly ONE. Row 12 is satisfied because no "
                          "second scan occurs; T4c stops being a separate read.",
    "order_effect": "A3-6 steps 5 and 6 merge. Row 30 is evaluated AFTER the pass, on the "
                    "tie distribution the pass emits, and before T6. This costs nothing "
                    "in evidence: row 30's action is 'post the distribution, Cooper "
                    "decides on any fix' - post-hoc either way - and no headline exists "
                    "until T6/T7, so the tie bound is still known before any number that "
                    "depends on it is reported.",
    "row_28_effect": "T4b cleared at 98dac7c, so Stage B was already authorised. Row 28 is "
                     "unaffected.",
    "scope": "Phase 11 only. No frozen artifact is rebuilt and src/ is untouched "
             "(row 32).",
}

c["outputs"]["t5b_writes"] = {
    "new_table": "event_quote_metrics_v1",
    "permission": "escalation row 14a - creating a NEW phase-scoped table in main.duckdb "
                  "is permitted and precedented (Phase 8 created event_minute_bars_v2 "
                  "the same way). The ban in row 14 is on MUTATING what already exists.",
    "write_protocol": "T5b is the only task that opens main.duckdb read-write. It issues "
                      "exactly one CREATE OR REPLACE TABLE for event_quote_metrics_v1 and "
                      "touches nothing else. A before/after catalogue diff is recorded in "
                      "t5_cache_integrity.json so the 'no pre-existing object changed' "
                      "claim is evidenced rather than asserted.",
}

p.write_text(json.dumps(c, indent=2))
print("recorded option (ii)")

# ---- focused re-audit of the rows the resolution touches -------------------
focused = {
    "task": "T0c focused re-audit", "phase": "11", "date": "2026-08-16",
    "scope": "NARROW BY DESIGN. Cooper's option (ii) changes exactly one thing - where "
             "T4c's read happens. Only the rows that bear on that are re-checked; rows "
             "unaffected by it keep their verdicts from the A2 re-audit (98dac7c) and the "
             "A3 re-audit (25cfcc0). The scope of this re-audit is stated rather than "
             "implied so a later reader is not misled into thinking all 34 were re-run.",
    "rows_rechecked": {
        "12": {"was": "FAIL - T4c would be a second full scan of filtered_trades",
               "now": "PASS", "why": "T4c no longer performs its own read. The single "
                      "budgeted T5b scan emits the tie statistics alongside the cache, so "
                      "the pass count stays at exactly 1."},
        "30": {"was": "FAIL - only through its contradiction with row 12",
               "now": "PASS", "why": "The contradiction is removed. The threshold is set "
                      "at 25 bp, the quantity is produced by the pass, and the row is "
                      "evaluated after the pass and before T6."},
        "28": {"was": "PASS", "now": "PASS", "why": "T4b cleared at 98dac7c; Stage B was "
                                                    "already authorised. Untouched."},
        "24": {"was": "PASS", "now": "PASS", "why": "The required-column guard is checked "
                      "at T5c and was verified present on the dev-tier cache at T5a."},
        "14 / 14a": {"was": "PASS", "now": "PASS", "why": "T5b creates a NEW table, which "
                     "14a permits. The write protocol above makes the no-mutation claim "
                     "checkable via a catalogue diff."},
        "32": {"was": "PASS", "now": "PASS", "why": "No frozen artifact is rebuilt and no "
                                                    "src/ file is touched."},
    },
    "verdict": "ROW 2 NO LONGER FIRES on the rows this resolution touches. The single "
               "outstanding failure from 25cfcc0 is cleared.",
    "authorised_next": "T5b - the single budgeted pass, emitting event_quote_metrics_v1 "
                       "and the T4c tie audit together. Then row 30, then T5c, then T6.",
}
q = pathlib.Path("results/phase_11/artifacts/t0c_focused_reaudit_option_ii.json")
q.write_text(json.dumps(focused, indent=2))
print("wrote", q.name, "->", focused["verdict"])
