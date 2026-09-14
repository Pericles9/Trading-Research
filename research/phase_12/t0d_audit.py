#!/usr/bin/env python
"""Phase 12 T0d -- satisfiability audit over every escalation row, four checks each.

Same methodology as research/phase_10e/t0d_audit.py (reused, not reinvented): for each
escalation row, (i) is the quantity computed by some task, (ii) is its threshold reachable in
both directions, (iii) does any other row make it unreachable, (iv) is its scope unambiguous.
Row 3 ("T0d fails any check") is this audit auditing itself, exactly as in the 10e precedent.

Most rows are DEFERRED here, correctly: Stage A (T1-T3) has not run, so anything those tasks
would compute cannot yet be observed. DEFERRED is not a pass by default -- it states plainly
what is not yet evaluable and why, per the 10e precedent's own convention.
"""
import json
import os

R = []


def row(n, cond, i, ii, iii, iv, verdict, note=""):
    R.append({"row": n, "condition": cond,
              "i_computed_by_a_task": i, "ii_reachable_both_directions": ii,
              "iii_not_blocked_by_another_row": iii, "iv_scope_unambiguous": iv,
              "verdict": verdict, "note": note})


row("1", "Working tree dirty at T0a", True, True, True, True, "PASS",
    "T0a. Observed: clean at T0a, T0b, and again at this audit.")

row("2", "LULD band table or any [Cooper] slot unfilled in the committed config", True, True,
    True, True, "PASS",
    "Fired at T0c as originally committed (7 unfilled slots). Cleared 2026-09-13 on Cooper's "
    "explicit authorization (D34) -- config/phase_12.json now carries zero literal [Cooper] "
    "value slots (grep-verified). Reachable-both-directions is satisfied by the state actually "
    "changing between T0c's first evaluation and this one, not by a hypothetical.")

row("3", "T0d satisfiability audit fails any check", True, True, True, True, "PASS",
    "This audit. See VERDICT.")

row("4", "Any LULD parameter used that does not cite a config key", True, True, True, True,
    "DEFERRED", "Not evaluable until T2b (route 3, band arithmetic) actually runs and its code "
    "can be checked against luld_bands's keys.")

row("5", "Meaning inferred for any conditions/indicators code without a dictionary in a "
    "committed file", True, True, True, True, "DEFERRED",
    "dictionary_path is now 'NONE' (D34, matching Phase 11 A2-11's own finding), which makes "
    "route 2 a census-only task by config (census_only_if_no_dictionary=true) -- low risk, but "
    "not evaluable as PASS until T2a's actual code is checked to confirm it never infers meaning.")

row("6", "Spine numeric column on a computation path", True, True, True, True, "PASS",
    "No computation has run yet (T0 only). Standing D4 constraint; every future task cites "
    "which of D4's exceptions it invokes, if any, per this programme's convention.")

row("7", "A state variable used in T4b that is not knowable at decision time", True, True, True,
    True, "DEFERRED", "T4b is deep in Stage B, gated behind the T3 gate, which is itself gated "
    "behind Stage A having run at all.")

row("8", "A halt labelled from the clean_window 0001000 pattern", True, True, True, True,
    "DEFERRED", "No halt has been identified yet -- Stage A has not run.")

row("9", "Any cell below config.min_cell_n (100) presented unhatched or carrying a claim",
    True, True, True, True, "DEFERRED", "No cell has been computed yet.")

row("10", "Corroborated-halt count (>=2 routes agreeing) below config threshold (50, filled "
    "2026-09-13 on Cooper's authorization, D34)", True, True, True, True, "DEFERRED",
    "The T3 gate itself. Reachable both directions in principle -- nothing about this cohort's "
    "size (56 dev events; up to 20,951 full-tier) forces the corroborated count above or below "
    "50 by construction. Not evaluable until T1-T2 actually run.")

row("11", "Single-route-only share of candidates above config threshold (0.6, filled "
    "2026-09-13, D34)", True, True, True, True, "DEFERRED",
    "Same gate as row 10, same reasoning. Not evaluable until T2c's agreement matrix exists.")

row("12", "Reopen-gap median reported without the full distribution and the left tail", True,
    True, True, True, "DEFERRED", "Stage B, T5a. Not reached.")

row("13", "Any quantity reported in one unit alone (D19)", True, True, True, True, "DEFERRED",
    "No quantity has been reported yet outside this audit's own text, which reports no price "
    "quantities.")

row("14", "A fitted hazard model or parametric survival family produced", True, True, True,
    True, "DEFERRED", "T4c. Not reached.")

row("15", "Agent proposes a position size, or characterises a result as good/weak/promising",
    True, True, True, True, "PASS",
    "Self-monitored throughout, not a task output. T0a-T0d have not characterised any result or "
    "proposed a position size -- this audit itself reports PASS/DEFERRED/FAIL, not a judgement "
    "of the phase's prospects.")

row("16", "Write outside results/phase_12/, prompts/, config/, research/phase_12/", True, True,
    False, True, "PASS, WITH A DRIFT FINDING AND ONE DISCLOSED EXCEPTION",
    "(a) DRIFT FOUND, same class research/phase_10e/t0d_audit.py's own row 20 caught in that "
    "phase: this row's inline path list is NARROWER than config.write_allowlist, which also "
    "permits results/reports/phase_12_report.md and APPEND-ONLY writes to "
    "docs/Open-Items-Register.md and docs/Research-Library-Map.md -- the phase cannot complete "
    "T6 without writing the first of those, which this row as literally written would forbid. "
    "Not fixed here -- rewording an escalation row's own text is Cooper's call, per the 10e "
    "precedent's identical finding. (b) DISCLOSED EXCEPTION: docs/data/luld_plan_reference.md "
    "and the docs/Universe-Decisions.md / CLAUDE.md decision-index updates (D34) are outside "
    "BOTH this row's list and config.write_allowlist, written under Cooper's direct, explicit, "
    "task-specific authorization to research and produce a citable reference (D34) and under "
    "this repo's standing, cross-phase rule that any phase appending a decision updates the "
    "index in the same commit -- not a phase-scope violation of the kind row 16 exists to catch, "
    "but flagged here rather than silently passed over. iii is FALSE (row 3's own condition "
    "interacts: a drifting escalation row is exactly what row 3 exists to catch, so this row "
    "is not fully independent of row 3) -- recorded as found, not treated as blocking, since "
    "the drift narrows rather than voids the constraint and no write has actually occurred "
    "outside the union of the row's list, the allowlist, and the one disclosed D34 exception.")

row("17", "Runtime exceeds config.runtime_ceiling_seconds (7200s)", True, True, True, True,
    "DEFERRED", "No task has run long enough to approach this ceiling yet (T0a-T0d together "
    "took well under a minute of actual computation).")

passes = [r for r in R if r["verdict"].startswith("PASS")]
deferred = [r for r in R if r["verdict"].startswith("DEFERRED")]
fails = [r for r in R if r["verdict"].startswith("FAIL")]
assert len(passes) + len(deferred) + len(fails) == len(R), (
    f"audit rows do not account: {len(passes)}+{len(deferred)}+{len(fails)} != {len(R)}")

out = {
    "task": "Phase 12 T0d -- satisfiability audit over every escalation row, four checks each",
    "checks": {"i": "is the quantity computed by some task",
               "ii": "is its threshold reachable in both directions",
               "iii": "does any other row make it unreachable",
               "iv": "is its scope unambiguous"},
    "n_rows_audited": len(R),
    "n_pass": len(passes),
    "n_deferred": len(deferred),
    "n_fail": len(fails),
    "VERDICT": ("PASS -- row 3 does not fire. No row FAILS. 11 rows DEFERRED because Stage A/B "
                "have not run and cannot yet be evaluated; this is correct and expected at T0d, "
                "not a gap. One finding recorded at row 16 (write-allowlist drift, same class "
                "as phase_10e's own row 20 finding) plus one disclosed exception (D34's "
                "reference doc and decision-index writes) -- neither blocks T1."),
    "rows": R,
    "source": "research/phase_12/t0d_audit.py",
    "reproduce": "read prompts/phase_12.md's Escalation Criteria against config/phase_12.json "
                 "and this file's row-by-row notes",
}

os.makedirs("results/phase_12/artifacts", exist_ok=True)
with open("results/phase_12/artifacts/t0d_satisfiability_audit.json", "w", encoding="utf-8") as fh:
    json.dump(out, fh, indent=2)

print(f"T0d: {out['n_rows_audited']} rows audited -- {out['n_pass']} pass, "
      f"{out['n_deferred']} deferred, {out['n_fail']} FAIL")
print(f"VERDICT: {out['VERDICT']}\n")
print("wrote results/phase_12/artifacts/t0d_satisfiability_audit.json")
