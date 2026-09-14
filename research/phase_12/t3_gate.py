#!/usr/bin/env python
"""Phase 12 T3 -- THE STAGE A GATE. Dev tier. Post and stop.

T3a: corroborated-halt count and share against the detection universe, single-route-only share.
T3b: evaluate Escalation rows 10 and 11. Stage B is unauthorised until Cooper clears them in
writing (Approval Gate).
T3c: if the gate fires, write the feasibility finding.

METHODOLOGICAL CAVEAT, stated because it changes how this result should be read, not to soften
it: config.cooper_thresholds.row_10_corroborated_halt_count_min = 50 was filled (D34) from the
config's own long-standing proposal, most plausibly calibrated with a FULL-TIER population
(~20,951 events) in mind, not the 56-event dev sample -- 50 corroborated events out of 56 total
would require corroboration on ~89% of the entire dev cohort, an implausible bar for any real
archive. Per CLAUDE.md's two-tier rule, Stage A runs dev-tier first regardless; this gate result
is the correct and required dev-tier checkpoint, but a dev-tier "row 10 fires" should be read as
largely UNINFORMATIVE about full-tier feasibility, not as a conclusive archive-wide finding --
row 11 (a SHARE, not a count) is not subject to the same small-n floor problem and is read as more
informative at this tier.

Usage: .venv/Scripts/python.exe research/phase_12/t3_gate.py
"""
from __future__ import annotations

import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
OUT = os.path.join(REPO, "results", "phase_12", "artifacts", "t3_gate.json")


def main() -> int:
    agree = json.load(open(os.path.join(REPO, "results", "phase_12", "artifacts",
                                         "t2_agreement_matrix.json"), encoding="utf-8"))
    ev = agree["agreement_by_event"]

    row_10_min = agree["cooper_threshold_row_10_min"]
    row_11_max = agree["cooper_threshold_row_11_max_share"]
    corroborated_count = ev["n_both"]
    single_route_share = agree["single_route_only_share_gap_level"]

    row_10_fires = corroborated_count < row_10_min
    row_11_fires = single_route_share > row_11_max

    out = {
        "task": "T3 -- THE STAGE A GATE, dev tier",
        "T3a_observed": {
            "corroborated_halt_count_events": corroborated_count,
            "detection_universe_events": agree["route_3_total_events_n"],
            "detection_universe_events_note": ("55 dev events had route-3 data computed (the "
                                                "full dev-tier population reaching this task); 42 "
                                                "of those also had at least one route-1 candidate "
                                                "gap -- see t2_agreement_matrix.json for the full "
                                                "breakdown."),
            "single_route_only_share_gap_level": single_route_share,
            "single_route_only_share_event_level": (ev["n_route1_only"] + ev["n_route3_only"]) /
                                                    (ev["n_route1_only"] + ev["n_route3_only"] + ev["n_both"]),
        },
        "T3b_escalation_evaluation": {
            "row_10": {"condition": "corroborated_halt_count < config threshold",
                       "threshold": row_10_min, "observed": corroborated_count,
                       "fires": row_10_fires,
                       "action_if_fires": "Hard stop at T3 -- too few to measure a reopen distribution"},
            "row_11": {"condition": "single_route_only_share > config threshold",
                       "threshold": row_11_max, "observed": round(single_route_share, 4),
                       "fires": row_11_fires,
                       "action_if_fires": "Hard stop at T3 -- routes do not corroborate"},
            "gate_fires": bool(row_10_fires or row_11_fires),
        },
        "methodological_caveat": ("row_10's threshold (50) was almost certainly calibrated for a "
                                   "full-tier population (~20,951 events), not this 56-event dev "
                                   "sample -- 50/56 would require corroboration on ~89% of the "
                                   "entire cohort. This dev-tier row-10 firing is expected at this "
                                   "sample size and should not be read as a conclusive archive-wide "
                                   "finding. row_11 is a SHARE, not a count, and does not have the "
                                   "same small-n floor problem -- its firing (0.903 vs. a 0.6 "
                                   "ceiling) is the more informative of the two at dev tier."),
        "T3c_feasibility_finding": (
            "STAGE A GATE FIRES on both rows at dev tier. Per the prompt's own T3c: this is a "
            "complete and reportable phase outcome, not a failure. On the 56-event dev sample: "
            "route 1 (tape gaps) finds a real, if modest, signature near the 300s pause length "
            "(T1b) but produces 1,991 candidate gaps across only 42 events -- far more candidates "
            "than plausible halts, meaning most are thin-tape artifacts, not pauses. Route 2 "
            "(condition/indicator codes) identifies nothing by construction -- no dictionary "
            "exists on disk (Phase 11 A2-11, confirmed again here). Route 3 (band arithmetic) "
            "finds 13 of 55 events touching a band edge at minute-bar resolution. Only 9 events "
            "show agreement between routes 1 and 3 (event-level approximation). What data would "
            "close this: (a) a condition/indicator code dictionary, even a partial one mapping "
            "just the codes found exclusive to candidate windows (3, 7 -- t2_code_census.json), "
            "would let route 2 actually identify rather than only census; (b) full-tier promotion "
            "(~20,951 events) would test whether row 10's count floor is reachable at scale, which "
            "56 events structurally cannot answer regardless of the true halt rate; (c) tick-level "
            "(not minute-bar) band arithmetic would remove the coarsest source of route-1/route-3 "
            "grain mismatch this dev-tier pass had to approximate around."
        ),
        "source": "research/phase_12/t3_gate.py:main",
        "reproduce": ".venv/Scripts/python.exe research/phase_12/t3_gate.py",
    }
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=2, default=str)

    print(json.dumps(out, indent=2, default=str))
    print(f"\nwrote {OUT}")
    print("\n*** STAGE A GATE FIRES. Stage B is unauthorised until Cooper clears rows 10/11 in "
          "writing, per the Approval Gate. STOPPING HERE. ***")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
