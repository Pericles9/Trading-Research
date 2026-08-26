"""
Phase 10c Stage 1 -- consolidated Verification Block (S5), assembled once every
task (T0-T7) is done. Synthesizes what already ran; does not recompute anything.

Sections required by the prompt:
  - waterfall reconciliation, per cell, every stage's count + population named
  - Class M held (open vs close)
  - executable assertions (not prose)
  - Chart Contract (Kaleido-verified before commit)
  - escalation table review (19 rows; which fired)

Usage: .venv/Scripts/python.exe research/phase_10c/s1_verification_block.py
"""
from __future__ import annotations

import glob
import importlib.util as ilu
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "phase_10"))
from common import rel  # noqa: E402
_s = ilu.spec_from_file_location("c10c", os.path.join(HERE, "common.py"))
c10c = ilu.module_from_spec(_s); _s.loader.exec_module(c10c)

ART = "results/phase_10c/artifacts"


def main() -> int:
    cfg, chash = c10c.load_cfg(), c10c.cfg_hash()

    executable_assertions = json.load(open(rel(f"{ART}/s1_t1_verify.json"), encoding="utf-8"))
    waterfall_pooled = json.load(open(rel(f"{ART}/s1_t1_waterfall.json"), encoding="utf-8"))
    waterfall_per_cell = json.load(open(rel(f"{ART}/s1_t1_waterfall_per_cell.json"),
                                        encoding="utf-8"))

    chart_manifests = sorted(glob.glob(rel(f"{ART}/s1_t*_chart_manifest.json"))) + \
        [rel(f"{ART}/s1_t6d_manifest.json"), rel(f"{ART}/s1_t7_tape_manifest.json")]
    chart_tally = {"n_total": 0, "n_kaleido_verified": 0, "by_manifest": {}}
    for m in chart_manifests:
        if not os.path.exists(m):
            continue
        d = json.load(open(m, encoding="utf-8"))
        charts = d.get("charts", [])
        n_ok = sum(1 for c in charts if c.get("kaleido_verified"))
        chart_tally["n_total"] += len(charts)
        chart_tally["n_kaleido_verified"] += n_ok
        chart_tally["by_manifest"][os.path.basename(m)] = {"n": len(charts), "kaleido_ok": n_ok}

    escalation_rows = {
        "0": {"condition": "visual review against the tape", "status": "RESERVED",
             "note": "produced (T7, 56 charts), not evaluated by this pipeline -- Cooper's alone"},
        "1": {"condition": "void parameter cutoff applied anywhere", "status": "NOT FIRED",
             "note": "D13_void_parameter threshold is null throughout; void only ranks "
                     "(argmax across troughs in envelope_boundary()), never gates"},
        "2": {"condition": "trailing-window implementation", "status": "NOT FIRED",
             "note": "every local median uses pandas .rolling(win, center=True, ...)"},
        "3": {"condition": "kernel or variant dropped/promoted/selected on results",
             "status": "NOT FIRED", "note": "all 3 kernels and 3 variants carried in parallel "
                       "through every task, T0-T7"},
        "4": {"condition": "kernel outputs combined into a single per-event signal",
             "status": "NOT FIRED", "note": "T4 explicitly kept per-kernel throughout; no "
                       "combining rule implemented anywhere"},
        "5": {"condition": "summary statistic without its supporting distributional chart",
             "status": "NOT FIRED", "note": f"{chart_tally['n_kaleido_verified']}/"
                       f"{chart_tally['n_total']} charts kaleido-verified; T5a's chart added "
                       "specifically to satisfy this row"},
        "6": {"condition": "count without population named inline", "status": "NOT FIRED",
             "note": "n stated in every summary table (T1c, T2a-d, T3a-c, T4, T5a-b)"},
        "7": {"condition": "T3 quantity without the anchor-delta uncertainty in caption",
             "status": "NOT FIRED", "note": "ANCHOR_DELTA_CAPTION applied to every T3 JSON "
                       "output and every T3 chart"},
        "8": {"condition": "condition code interpreted beyond docs/massive_trade_conditions.json",
             "status": "NOT FIRED", "note": "codes {8,15} used per that file's stated meaning "
                       "only; no other code interpreted"},
        "9": {"condition": "result characterized evaluatively rather than described",
             "status": "NOT FIRED", "note": "every finding stated as measured, with reads left "
                       "explicitly to Cooper (T4a, T4b, T4c, T2e, T5b)"},
        "10": {"condition": "prose asserts membership/inclusion/exclusion the code does not "
                            "assert", "status": "VIOLATION FOUND IN PRIOR WORK, FLAGGED",
              "note": "Amendment 4-6's 'genuine after-hours anchor' framing implicitly asserted "
                      "BMR was a dev-sample event; the code (unfiltered cohort manifest read) "
                      "never asserted that. Found in Stage 1 T1, logged to "
                      "docs/Open-Items-Register.md, not silently corrected in the tagged/"
                      "committed Amendment artifacts. Stage 1's OWN new code does not repeat "
                      "this -- confirmed by the BMR assertion in s1_t1_verify.json."},
        "11": {"condition": "write to an archived drive", "status": "NOT FIRED",
              "note": "no D:\\ path referenced anywhere in Stage 1"},
        "12": {"condition": "spine OHLC or volume numeric enters a computation",
              "status": "NOT FIRED", "note": "every price used (agg_px, price_at_detection) is "
                        "tick-derived; momentum_pct never read (verify_quarantine)"},
        "13": {"condition": "median sub-burst duration below [Cooper] at 8/32min kernel",
              "status": "UNEVALUABLE", "note": "[Cooper] threshold not set. Duration figures "
                        "reported in T2b (medians span microseconds to tens of seconds by "
                        "segment/kernel); no pass/fail determination made"},
        "14": {"condition": "insufficient_context share exceeds [Cooper] in any cell",
              "status": "UNEVALUABLE", "note": "[Cooper] threshold not set. Raw shares reported "
                        "in T1c (0%-42%, highest at 2min RTH by construction)"},
        "15": {"condition": "no_threshold share exceeds [Cooper] in any cell",
              "status": "UNEVALUABLE", "note": "[Cooper] threshold not set. Raw share is 0% in "
                        "every cell (T1c)"},
        "16": {"condition": "T4a shows threshold location scaling ~1:1 with kernel width",
              "status": "UNEVALUABLE", "note": "[Cooper] slope band not set. Measured slope "
                        "reported (median -1.359); the read is explicitly Cooper's (T4a)"},
        "17": {"condition": "any [Cooper] parameter filled by the agent", "status": "NOT FIRED",
              "note": "D7/D8/D9/D16 and the row-13/14/15/16 thresholds remain unset; none "
                      "invented to force an evaluation"},
        "18": {"condition": "agent-side workaround applied instead of stopping and escalating",
              "status": "NOT FIRED", "note": "the two real defects found this stage (T0's "
                        "nunique() undercount, T1's BMR scope mixing) were reported and fixed "
                        "at the source/flagged in the register, not silently worked around"},
    }

    out = {
        "phase": "10c", "stage": "1", "task": "S5_verification_block", "config_hash": chash,
        "waterfall_reconciliation": {
            "pooled_upstream_variant_kernel_independent_stages": waterfall_pooled,
            "per_cell": waterfall_per_cell["per_cell"],
            "per_cell_note": waterfall_per_cell["pooled_upstream_stages_variant_kernel_independent"]["note"],
        },
        "class_M_held": executable_assertions["checks"]["class_M_unchanged_open_to_close"],
        "executable_assertions": executable_assertions["checks"],
        "chart_contract": chart_tally,
        "escalation_table": escalation_rows,
        "escalation_summary": {
            "not_fired": sum(1 for v in escalation_rows.values() if v["status"] == "NOT FIRED"),
            "unevaluable_cooper_unset": sum(1 for v in escalation_rows.values()
                                            if v["status"] == "UNEVALUABLE"),
            "reserved_for_cooper": 1,
            "violation_found_in_prior_work_flagged": 1,
            "violation_found_in_stage1_own_code": 0,
        },
        "source": "research/phase_10c/s1_verification_block.py:main",
    }
    c10c.write_json(rel(f"{ART}/s1_verification_block.json"), out)

    print(f"Chart Contract: {chart_tally['n_kaleido_verified']}/{chart_tally['n_total']} "
          f"kaleido-verified")
    print(f"Escalation table: {out['escalation_summary']}")
    print(f"Class M held: {out['class_M_held']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
