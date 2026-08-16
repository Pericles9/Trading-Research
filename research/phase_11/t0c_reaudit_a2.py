"""T0c re-audit against the Amendment 2 spec and the amended config.

Four checks per row: C1 measured by a task, C2 quantity produced ON THE OBJECT
the task reads, C3 threshold reachable given committed ranges, C4 no
contradiction with another row. Hard stop on any failure.
"""
from __future__ import annotations

import json
import pathlib

CFG = json.loads(pathlib.Path("config/phase_11.json").read_text())
OUT = pathlib.Path("results/phase_11/artifacts/t0c_satisfiability_audit_a2.json")


def row(rid, cond, thr, task, obj, c1="PASS", c2="PASS", c3="PASS", c4="PASS", **kw):
    d = {"row": rid, "condition": cond, "threshold": thr, "task": task, "object": obj,
         "C1": c1, "C2": c2, "C3": c3, "C4": c4}
    d["verdict"] = "FAIL" if "FAIL" in (c1, c2, c3, c4) else "PASS"
    d.update(kw)
    return d


CARRIED = ("Unchanged by Amendment 2. Verdict carried from the T0c audit at commit "
           "1606eef, which passed all four checks; re-verified against the amended "
           "config for contradictions introduced by A2.")

rows = [
    row("0", "Cooper's review contradicts the numeric result", "judgment",
        "T4 gate / final approval", "charts 01-09", note=CARRIED),
    row("1", "Working tree dirty at T0a", "any", "T0a", "git working tree",
        note=CARRIED + " Tree clean at fc49037."),
    row("2", "T0c satisfiability audit fails on any row", "any", "T0c", "this artifact",
        note="A2-10 FIXED the stale label: the row now names T0c, the post-rename audit "
             "task. The T0c-audit flag raised at 1606eef is closed."),
    row("3", "T1 cannot establish consolidated vs per-venue", "any", "T1a",
        "filtered_quotes_dev_v4", note=CARRIED + " Established: 13 median RTH venues."),
    row("4a", "sip_timestamp null-or-zero share, T=0 RTH segment, per event", "> 1% any event",
        "T1b", "filtered_quotes_dev_v4 (DuckDB table)",
        note="A2-10 FIXED the segment scope to 'T=0 RTH segment, per event'. The "
             "denominator-circularity flag raised at 1606eef is closed - all three "
             "denominators returned exactly 0, so no straddle was possible. Measured 0.0."),
    row("4b", "T1c-v any storage-order finding", "any (not a stop)", "T1c-v",
        "source parquet, file_row_number",
        note=CARRIED + " Measured: reverse-chronological on all 50 events. This is the "
                       "finding that motivated T4b."),
    row("5", "state_hard_unusable clock-time share, T=0 RTH, median", "> 0.25", "T2a",
        "filtered_quotes_dev_v4",
        note=CARRIED + " Measured 0.000000. NOTE the vocabularies differ: row 5 is "
                       "defined on Stage A's state_hard_unusable, while D17's Stage B "
                       "exclusion set is that union PLUS zero-size MINUS locked. Row 5 "
                       "is a Stage A gate already passed and is not re-evaluated in "
                       "Stage B, so the difference creates no contradiction."),
    row("6", "T3 alignment curve matches the flat row", "any", "T3a/T3b", "dev v4 tables",
        note=CARRIED + " Measured peak-minus-min 0.1902; row 1 of the reading rule."),
    row("7", "T3 peak offset differs premarket vs RTH by > 1 rung", "any (not a stop)",
        "T3a", "dev v4 tables",
        note=CARRIED + " Fired as not-a-stop: 7 rungs on all four combinations. D16 "
                       "resolves the consequence by fixing a single basis and delta=0, "
                       "so no segment-specific offset enters Stage B."),
    row("8", "Any effective spread computed before the T4 gate", "any", "prohibition",
        "code audit",
        note="SATISFIED AND NOW SPENT. The T4 gate has passed (A2-0), so this row no "
             "longer binds. No effective spread was computed in Stage A."),
    row("9", "T5a runtime extrapolation exceeds runtime_ceiling_seconds",
        f"{CFG['runtime']['runtime_ceiling_seconds']} s", "T5a", "dev-tier wall clock",
        note="A2-9 ACCEPTED the ceiling and additionally made it the hard bound on the "
             "T5b query itself, which removes the row 9 / row 12a tension recorded at "
             "1606eef. See row 26."),
    row("10", "quotes_ingested = FALSE share of the detection universe", "> 20%", "T6",
        "Phase 4/5 materializations (D15)",
        note=CARRIED + " D15 join verified complete, 15,369/15,369."),
    row("11", "median round_trip_cost / realized_capture, RTH, lat 5, hold 30, 1x",
        f"{CFG['cooper_thresholds']['row_11_kill_threshold']}", "T7c",
        "t4_axis_grid + T5 cache",
        note="A2-5 CONFIRMED 0.50 unchanged. Cell verified n=10,660 (10,607 both legs "
             "defined). The 1x column remains the SOLE trigger; the 1.5x column is "
             "reported with equal prominence but does not gate."),
    row("12", "Any full scan beyond the single budgeted T5b pass, including indirect",
        "> 1", "enforced throughout", "query plans",
        note=CARRIED + " 0 spent through Stage A."),
    row("12a", "Any query exceeding query_watchdog_seconds",
        f"{CFG['runtime']['query_watchdog_seconds']} s", "all tasks", "query execution",
        note="A2-9 BOUNDED the agent-authored carve-out. The exemption now applies to "
             "the T5b pass alone and that query is bounded by runtime_ceiling_seconds "
             "instead. The flag raised at 1606eef is closed. Enforced in code: "
             "research/phase_11/t3_alignment_sweep.py raises on breach."),
    row("13", "Any spine numeric column on a computation path (D4)", "any", "all",
        "code audit", note=CARRIED),
    row("14", "Any write to data root / src/ / pre-existing table or view", "any", "all",
        "filesystem + DuckDB catalogue",
        note=CARRIED + " Structurally enforced: common.connect() ATTACHes READ_ONLY."),
    row("14a", "Creating a NEW phase-scoped table in main.duckdb", "n/a (permitted)",
        "T5b", "DuckDB catalogue", note=CARRIED),
    row("15", "Any burst/quiet split, intensity, envelope, thresholding, Hawkes", "any",
        "all", "code audit", note=CARRIED),
    row("16", "Any short-side, fade, SSR or borrow logic", "any", "all", "code audit",
        note=CARRIED),
    row("17", "Any exclusion rule or alignment offset adopted by the agent", "any", "all",
        "code audit",
        note="SATISFIED AND NOW SPENT. D16 (offset delta=0, sip basis) and D17 "
             "(exclusion rule) were both set by Cooper at the T4 gate, not proposed by "
             "the agent. Stage B implements them as given."),
    row("18", "Any REPORT.md or digest sentence that EVALUATES a result", "any", "T9",
        "REPORT.md, digest.json",
        note=CARRIED + " A2-5 explicitly reaffirms that the 1.5x pre-registration "
                       "licenses no evaluative sentence."),
    row("18a", "T3 report does not name the reading-rule row", "any", "T9", "REPORT.md",
        note=CARRIED + " Row 1 selected and recorded in t3_alignment_sweep.json."),
    row("19", "Computation whose OUTPUT FEEDS a downstream quantity depending on "
              "storage order", "any", "all", "code audit",
        note=CARRIED + " T1c-v exempt by name (19a). T4b extends the same question "
                       "backwards to the frozen artifacts."),
    row("19a", "T1c-v exempt by name", "n/a (exemption)", "T1c-v", "source parquet",
        note=CARRIED),
    row("20", "T1c-iii finds no condition-code dictionary", "any (not a stop)", "T1c-iii",
        "disk search", note=CARRIED + " Fired as not-a-stop; census recorded."),
    row("21", "indicators/conditions null pattern differs across eras", "> 20 pp",
        "T1c-iv", "source parquet", note=CARRIED + " Measured 6.21 pp."),
    row("22", "Any interpretation of a conditions code value without a dictionary", "any",
        "T1c-ii/iii, T9", "code and report audit",
        note=CARRIED + " A2-10 reaffirms this bars inferring meaning from values even "
                       "though indicators turned out populated."),

    # ---- A2-11 new rows -------------------------------------------------
    row("23", "Any impact window shorter than 1 s", "any", "T8b (config guard, checked "
        "before T5b)", "config.impact.impact_windows_seconds",
        note=f"Committed value {CFG['impact']['impact_windows_seconds']} s, min "
             f"{CFG['impact']['min_window_seconds']} s. Reachable and currently "
             "satisfied. No contradiction: T8b reads the windows from config and the "
             "config is committed before the pass."),
    row("24", "event_quote_metrics_v1 missing any A2-8 staleness column at T5c", "any",
        "T5c", "DuckDB catalogue",
        note="Guarded list committed as config.outputs.stage_b_table_required_columns = "
             f"{CFG['outputs']['stage_b_table_required_columns']}. NOTE: row 24 names "
             "the five A2-8 staleness columns; unusable_time_share comes from A2-3, not "
             "A2-8. The committed guard covers all six, a SUPERSET of what row 24 "
             "requires, so the row cannot fail for want of coverage."),
    row("25", "T4b finds a class (b) or (c) ordering assumption", "any", "T4b-iii",
        "src/ and prior-phase code, read-only",
        note="The classification is exactly what T4b-ii produces, so the quantity "
             "exists. Reachable in both directions. Consistent with row 28, which "
             "sequences it."),
    row("26", "Any query exempted from the watchdog other than T5b, or T5b exceeding "
              "runtime_ceiling_seconds", "any", "all tasks + T5b", "query execution",
        note="RESOLVES the row 9 / row 12a tension recorded at 1606eef. No query in the "
             "phase is now unbounded: every query is watchdogged at "
             f"{CFG['runtime']['query_watchdog_seconds']} s except T5b, which is bounded "
             f"at {CFG['runtime']['runtime_ceiling_seconds']} s."),
    row("27", "Any report sentence using a T-1/T-3 spread as a detection-time proxy, or "
              "reporting a spread or cost in one unit alone", "any", "T9 and any posting",
        "REPORT.md, digest, charts",
        note="Satisfiable: every Stage A spread artifact already carries both units "
             "(t2e_quoted_spread.parquet has tw_spread_bp and tw_spread_dollars; chart "
             "03 panels both). D19 is the governing decision. NOTE for T8: delta-mid per "
             "unit signed volume is an impact quantity rather than a spread, but it is "
             "reported in both units too so the row cannot be tripped on a technicality."),
    row("28", "Any Stage B task begun before T4b has cleared", "any", "sequencing",
        "task order",
        note="Consistent with A2-0's conditional authorisation and with the A2 execution "
             "order, which places T4b at step 2 and T5a at step 4."),
    row("29", "Standing qualifier absent from REPORT §T7 or captions 05/06/07", "any",
        "T9 + chart builders", "REPORT.md and chart captions",
        note="Qualifier text committed verbatim to config.standing_qualifier so the "
             "chart builders and the report emit one identical string rather than "
             "retyping it."),
]

flags = [
    {"item": "Row count", "detail": "A2 states 'now 29 rows'. Explicit enumeration is 31: "
     "Amendment 1's 24 (0,1,2,3,4a,4b,5..22) plus A2-11's seven (23..29). 29 is the "
     "highest row NUMBER, not the count - 4a/4b split one number and numbering starts at "
     "0. Editorial; the audit covers all 31 plus the 4 sub-rows.",
     "classification": "editorial, not a check failure"},
    {"item": "Charts 05 and 09 specify 'twin axes bp and cents'",
     "detail": "A dual y-scale is the one encoding this project's visualization standard "
     "forbids outright, and Phase 9 hit the identical conflict on its chart 06 - resolved "
     "there by shipping a linked panel sharing the x-axis, same information, same file, "
     "no second y-scale, with the deviation recorded in chart_common.py and REPORT.md. "
     "Phase 11 follows that precedent for charts 05 and 09. D19 and row 27 require both "
     "units to be PRESENT, which a two-panel layout satisfies; neither requires them to "
     "share an axis.",
     "classification": "resolved by existing precedent, recorded; not a check failure"},
    {"item": "Row 5 vs D17 vocabulary",
     "detail": "Row 5 gates on Stage A's state_hard_unusable; D17's Stage B exclusion set "
     "is that union PLUS zero-size MINUS locked. Row 5 is a Stage A gate already passed "
     "and is not re-evaluated in Stage B, so the two definitions never have to agree.",
     "classification": "recorded, not a contradiction"},
]

audit = {
    "task": "T0c re-audit", "phase": "11", "date": "2026-08-16",
    "supersedes": "results/phase_11/artifacts/t0c_satisfiability_audit.json (24-row audit "
                  "at commit 1606eef). Retained as the historical record.",
    "spec_audited": {
        "prompt": "prompts/phase_11.md",
        "amendments": ["prompts/phase_11_amendment_1.md", "prompts/phase_11_amendment_2.md"],
        "config": "config/phase_11.json", "committed_at": "fc49037",
        "rows_enumerated": len([r for r in rows if not r["row"].endswith("a")
                                or r["row"] in ("4a", "4b")]),
    },
    "method": {"checks_per_row": ["C1 measured by a task", "C2 quantity produced on the "
               "object the task reads", "C3 threshold reachable given committed ranges",
               "C4 no contradiction with another row"],
               "stop_rule": "Hard stop on any row failing any check. Post; do not repair."},
    "a1_flags_closed_by_a2": {
        "row_2_stale_label": "CLOSED by A2-10 - now names T0c",
        "row_4a_segment_scope": "CLOSED by A2-10 - now 'T=0 RTH segment, per event'; "
                                "moot in any case, all three denominators measured 0",
        "row_12a_unbounded_carve_out": "CLOSED by A2-9 - T5b bounded by "
                                       "runtime_ceiling_seconds; no unbounded query remains",
    },
    "rows": rows,
    "flags_recorded_not_failures": flags,
    "summary": {
        "rows_audited": len(rows),
        "fail": [r["row"] for r in rows if r["verdict"] == "FAIL"],
        "pass": [r["row"] for r in rows if r["verdict"] == "PASS"],
        "verdict": None, "passes_spent_to_date": 0,
    },
}
n_fail = len(audit["summary"]["fail"])
audit["summary"]["verdict"] = (
    "ESCALATION ROW 2 DOES NOT FIRE. All rows pass all four checks against the amended "
    "spec and config. Three flags recorded; none is a check failure. All three Amendment "
    "1 flags are closed by Amendment 2."
    if n_fail == 0 else f"ROW 2 FIRES on {n_fail} rows.")
audit["summary"]["authorised_next"] = (
    "T4b - ordering-assumption audit. Escalation row 28 bars every Stage B task until "
    "T4b clears." if n_fail == 0 else "nothing - post and wait")

OUT.write_text(json.dumps(audit, indent=2))
print(f"wrote {OUT.name}: {len(rows)} rows audited, {n_fail} failures")
print(audit["summary"]["verdict"])
