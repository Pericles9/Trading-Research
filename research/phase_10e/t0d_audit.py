import json, io, os

# (i) computed by some task  (ii) threshold reachable in both directions
# (iii) no other row makes it unreachable  (iv) scope unambiguous
R = []
def row(n, cond, i, ii, iii, iv, verdict, note=""):
    R.append({"row": n, "condition": cond,
              "i_computed_by_a_task": i, "ii_reachable_both_directions": ii,
              "iii_not_blocked_by_another_row": iii, "iv_scope_unambiguous": iv,
              "verdict": verdict, "note": note})

row("1", "phase-11-approved tag absent", True, True, True, True, "PASS",
    "T0a. Observed: tag exists at 05ccbfc.")
row("1a", "frozen input differs from frozen_baseline.json", True, True, True, True, "PASS",
    "T0a-i. Observed: all five match. NOTE this row was UNSATISFIABLE as originally written "
    "(it compared against a state at phase-11-approved that was never recorded) and was "
    "reworded in pre-flight. Had it not been, it would have failed check (ii) here.")
row("1a-i", "baseline verifies forward only; tag period is circumstantial", True, None, True,
    True, "PASS (not a stop)", "Informational by design.")
row("1b", "master moved AND 1a passes -> record, do not stop", True, True, True, True,
    "PASS (not a stop)", "Observed: 79 commits since the tag. Recorded in decisions_log.")

row("2", "any slot in config.cooper_slots_by_arm.arm1 still [Cooper] at T0c", True, True,
    True, True, "PASS",
    "AMENDED 2026-08-31 -- scoped to the arm being run, with the mapping in config so the row "
    "cannot drift from it. Observed: all five arm1 slots filled (profit_k=3, stop_m=2, "
    "row_10a=0.25, row_11=0.10, row_12=optimistic-bound). NOTE Cooper's amendment listed "
    "'cooper_thresholds.row_10_r1_straddle' in arm1; that key does not exist and was not "
    "created -- the straddle test is structural and has no parameter, so a slot that can "
    "never be filled would make this row unevaluable. The five real keys are listed instead.")
row("2a", "any slot in config.cooper_slots_by_arm.arm2 still [Cooper] at T5a", True, True,
    True, True, "DEFERRED BY DESIGN",
    "Explicitly NOT evaluated at T0c. All three arm2 slots are unfilled and that is intended; "
    "Arm 2 is gated behind T4 and its slots are not needed to run Arm 1.")
row("3", "T0d fails any check", True, True, True, True, "PASS", "This audit. See verdict.")
row("4", "any pass over filtered_trades/quotes in Arm 1", True, True, True, True, "PASS",
    "Arm 1 reads event_minute_bars_v2 and the frozen artifacts only.")
row("5", "Arm 2 cohort row count differs from arm2_cohort_expected_n", False, False, True,
    True, "DEFERRED",
    "Not evaluable at T0d: arm2_cohort_expected_n is unfilled. Not reached before T5a, which "
    "is behind the T4 gate. Recorded rather than passed.")
row("6", "spine numeric on a computation path, other than momentum_pct as a GROUPING KEY "
    "and other than an A13-permitted read", True, True, True, True, "PASS",
    "AMENDED 2026-08-31 -- both standing carve-outs now named in the row.")
row("6a", "momentum_pct in a numerator, denominator or any computed quantity rather than as "
    "a grouping key", True, True, True, True, "PASS",
    "The important half of the amendment. 'Permitted for stratification' is the kind of "
    "clause that erodes; a GROUPING KEY is checkable and an intent is not. Arm 1 uses "
    "momentum_pct only as part of event identity (ticker, date, momentum_pct), which is a "
    "key, not a measurement.")
row("6b", "any spine numeric written into a committed artifact under any name, other than a "
    "membership boolean, vintage label or selection-function coefficient", True, True, True,
    True, "PASS", "A13(a) made enforceable. The only part of A13 that can actually leak, so "
    "it is the part that gets a row.")
row("7", "event_minute_bars_v2 row count != 45,925,350", True, True, True, True, "PASS",
    "T0a. Observed 45,925,350 -- MATCH.")
row("8", "Arm 1 first-passage number without both R1 bounds", True, True, True, True, "PASS")
row("9", "win rate on touched-only entries", True, True, True, True, "PASS")
row("10", "optimistic and pessimistic p_clear straddle p_breakeven on the named cell", True,
    True, True, True, "PASS",
    "T3d/T4a. Mutually exclusive with row 12 -- see the cross-row note.")
row("10a", "R1 ambiguous share on the named cell > 0.25", True, True, True, True,
    "PASS (reporting trigger, not a stop)")
row("11", "no-fill share (R3) on the named cell > 0.10", True, True, True, True, "PASS")
row("12", "optimistic p_clear below p_breakeven at EVERY cell", True, True, True, True,
    "PASS", "Bound reversed 2026-08-31. Mutually exclusive with row 10.")
row("13", "ceiling: p_clear(oracle) - p_clear(control), best cell, CI lower bound", False,
    False, True, True, "DEFERRED",
    "Not evaluable at T0d: row_13_ceiling is unfilled. Arm 2 only, behind the T4 gate.")
row("14", "cell where one event exceeds max_event_share, presented unflagged", True, True,
    True, True, "PASS")
row("15", "cell with n < min_cell_n presented unhatched", True, True, True, True, "PASS")
row("16", "quantity reported in one unit alone (D19)", True, True, True, True, "PASS")
row("17", "burst object / duration / timescale / quiet split appears", True, True, True, True,
    "PASS")
row("18", "Arm 2 output described as a detector or operating point", True, True, True, True,
    "PASS")
row("19", "runtime exceeds the arm's ceiling", True, True, True, True, "PASS")
row("20", "write outside config.write_allowlist", True, True, True, True, "PASS",
    "AMENDED 2026-08-31 -- the row now REFERENCES the allowlist instead of restating it. The "
    "inline copy was narrower than both the allowlist and the Output Files table, so T8b's "
    "required report copy would have fired it. Fourth list in this programme to drift from "
    "its source; the generalising rule went into the v1.4 draft.")
row("21", "agent states a recommendation or characterises a result", True, True, True, True,
    "PASS")
row("22", "decision appended at a number not confirmed free by reading the file", True, True,
    True, True, "PASS", "tools/verify_claude_md_indices.py checks this; currently clean at D24.")
row("23", "onset compared across channels before T5b-i null-rate matching", True, True, True,
    True, "PASS", "Arm 2 only.")
row("24", "causal kernel run against the centred floor 2.26/lambda", True, True, True, True,
    "PASS", "Arm 2 only. s_min_onesided exists in code with coefficient 4.5135.")
row("25", "Arm 1 and Arm 2 resolve det_anchor to different artifacts", True, True, True, True,
    "PASS", "T1a-i. Both resolve to a102; v2_r14 crosscheck is read, not re-derived.")

fails = [r for r in R if r["verdict"].startswith("**FAIL")]
deferred = [r for r in R if r["verdict"].startswith("DEFERRED")]
passes = [r for r in R if r["verdict"].startswith("PASS")]
assert len(fails) + len(deferred) + len(passes) == len(R), (
    f"audit rows do not account: {len(passes)}+{len(deferred)}+{len(fails)} != {len(R)}")

out = {
 "task": "Phase 10e T0d -- satisfiability audit over every escalation row, four checks each",
 "why_this_exists": ("Two of 10b's three amendments introduced an unreachable required "
                     "outcome. This audit is a hard stop (row 3) precisely so that a phase "
                     "does not run against a criterion it cannot satisfy."),
 "checks": {"i": "is the quantity computed by some task",
            "ii": "is its threshold reachable in both directions",
            "iii": "does any other row make it unreachable",
            "iv": "is its scope unambiguous"},
 "n_rows_audited": len(R),
 "n_pass": len(passes),
 "n_deferred": len(deferred),
 "n_fail": len(fails),
 "VERDICT": ("PASS -- row 3 does not fire. All evaluable rows satisfy all four checks; three "
             "are deferred by design -- rows 2a, 5 and 13, all Arm 2, behind the T4 gate."),
 "cross_row_note_rows_10_and_12": (
   "MUTUALLY EXCLUSIVE, and this is a good property rather than a conflict. If row 12 fires "
   "(optimistic below break-even everywhere) then on the named cell pessimistic <= optimistic "
   "< break-even, so both bounds sit below and there is no straddle -- row 10 cannot fire. If "
   "row 10 fires (pessimistic < break-even < optimistic) then optimistic exceeds break-even on "
   "the named cell, so row 12 cannot fire. They partition the failure modes cleanly."),
 "rows": R,
 "amendments_applied_2026_08_31": [
   "row 2 scoped to the arm being run, mapping in config.cooper_slots_by_arm; row 2a added",
   "row 6 gained the momentum_pct and A13 carve-outs; rows 6a and 6b added, making the "
   "grouping-key restriction and the A13(a) write boundary separately checkable",
   "row 20 now references config.write_allowlist instead of restating it",
   "T4a now reports a VERDICT in {both_below, straddle, both_above}, because rows 10 and 12 "
   "are mutually exclusive but do not partition the outcome space -- two of the four "
   "outcomes fire no row at all",
 ],
 "t4_verdict_gap_closed": (
   "Rows 10 and 12 being mutually exclusive is correct but insufficient: 'neither fired' "
   "collapsed the named cell PAYING and the named cell FAILING WHILE ANOTHER CELL CLEARS -- "
   "opposite findings. A gate returning the same summary for its best and second-worst "
   "outcome is the Phase 11 row-11 defect again. T4a now states the verdict always, "
   "separately from the row-firing table."),
 "_resolved_failures_kept_for_the_record": [
   {"row": "2",
    "problem": ("Read literally it fires now -- three [Cooper] slots are unfilled -- which "
                "contradicts Cooper's own 2026-08-31 statement that Arm 2's slots are gated "
                "behind T4 regardless."),
    "minimal_fix": ("scope row 2 to the arm being run: fires at T0c for any slot ARM 1 needs, "
                    "and at T5a for any slot ARM 2 needs. Preserves the protection -- nothing "
                    "runs against an unfilled threshold -- without blocking Arm 1 on Arm 2's "
                    "parameters."),
    "whose_call": "Cooper. It changes an escalation row."},
   {"row": "6",
    "problem": ("Scope omits two standing carve-outs, so read literally the row fires on this "
                "phase's own T1c and T3b, which use momentum_pct for stratification as the "
                "Constraints section expressly permits."),
    "minimal_fix": ("add 'other than momentum_pct used for stratification (D4's sole "
                    "exception), and other than a read permitted by D4 Amendment A13'."),
    "whose_call": "Cooper."},
   {"row": "20",
    "problem": ("The row's path list is narrower than config.write_allowlist and narrower than "
                "the phase's own Output Files table. T8b requires results/reports/"
                "phase_10e_report.md, which row 20 forbids -- the phase cannot complete "
                "without firing it."),
    "minimal_fix": ("replace the inline list with 'outside config.write_allowlist', so the two "
                    "cannot drift apart again."),
    "whose_call": "Cooper."}],
 "observed_state_at_T0a": {
   "branch": "phase/10e", "tag": "phase-11-approved at 05ccbfc",
   "commits_since_tag": 79,
   "working_tree": "DIRTY -- docs/Agent_Prompt_Standard.md only, Cooper's uncommitted v1.4 "
                   "draft plus the section 12 sha256 edit Cooper directed. Not phase work, and "
                   "10e's row 1 does not stop on a dirty tree.",
   "phase_11_digest_status": "FIELD ABSENT",
   "event_minute_bars_v2": 45925350,
   "frozen_artifacts": "all five present; row 1a passes against the baseline"},
 "source": "Phase 10e T0d",
 "reproduce": "read prompts/phase_10e.md escalation table against config/phase_10e.json",
}
os.makedirs("results/phase_10e/artifacts", exist_ok=True)
io.open("results/phase_10e/artifacts/t0d_satisfiability_audit.json", "w",
        encoding="utf-8").write(json.dumps(out, indent=2))

print(f"T0d: {out['n_rows_audited']} rows audited -- {out['n_pass']} pass, "
      f"{out['n_deferred']} deferred, {out['n_fail']} FAIL "
      f"(accounts: {out['n_pass']}+{out['n_deferred']}+{out['n_fail']}="
      f"{out['n_pass']+out['n_deferred']+out['n_fail']})")
print(f"VERDICT: {out['VERDICT']}\n")
for f in fails:
    print(f"  ROW {f['row']}: {f['verdict']}")
    print(f"     {f['note'][:300]}")
print("\nwrote results/phase_10e/artifacts/t0d_satisfiability_audit.json")
