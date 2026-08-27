"""
Phase 10d T6a -- causal audit, carried forward UNCHANGED.

10c retired zero of v4's non-causal fields: the window stayed centered, so the causal debt
is exactly as v4's audit left it and remains parked for Phase 17. 10d retires none either
and claims none. Counts are READ from results/phase_10/artifacts/v4_causal_audit.parquet.

10d adds fields. Every one of them is non-causal, and for the same reason as its parents:
the argmax-void threshold is a property of the completed-session histogram, and the ok mask
comes from a CENTRED rolling median that reads forward in time by half a window. A merge
tolerance and a run-length floor applied to non-causal objects cannot make them causal.

Usage: .venv/Scripts/python.exe research/phase_10d/t6_causal.py
"""
from __future__ import annotations

import hashlib
import json
import os

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
ART = os.path.join(ROOT, "results", "phase_10d", "artifacts")

NEW_FIELDS = [
    ("merge_admissibility", "non_causal",
     "tests each separating interval's normalized value against threshold + d. The "
     "threshold is the argmax-void trough of the COMPLETED-session histogram, so the test "
     "cannot be evaluated before the session ends."),
    ("separator_rule_outcome", "non_causal",
     "whether a separator is ok=False depends on the CENTRED rolling window count, which "
     "reads forward in time by half a kernel. Non-causal for the same reason "
     "local_median_log_interval is."),
    ("merged_subburst_object", "non_causal",
     "a merge of runs that are themselves runs below a completed-session threshold. "
     "Inherits non-causality from subburst_intervals; merging cannot remove it."),
    ("min_prints_filter_outcome", "non_causal",
     "a filter applied to merged objects, which are non-causal. A filter on a non-causal "
     "object is non-causal."),
    ("merged_subburst_duration", "non_causal",
     "aggregate of merged_subburst_object; its span includes bridged separators, all of "
     "which were classified against the completed-session threshold."),
    ("n_prints_in_bursts", "non_causal", "aggregate of merged_subburst_object."),
    ("break_cause_label", "non_causal",
     "classifies each run break as above-threshold or ok=False. Both discriminants are "
     "completed-session quantities."),
    ("counterfactual_declined_share", "non_causal",
     "a function of the void parameter, which v4's audit already tags non_causal. Reported, "
     "never applied, and non-causal either way."),
]


def main() -> int:
    with open(os.path.join(ROOT, "config", "phase_10d.json"), encoding="utf-8") as f:
        C10D = json.load(f)
    chash = hashlib.sha256(json.dumps(C10D, sort_keys=True).encode()).hexdigest()[:8]

    v4 = pd.read_parquet(os.path.join(ROOT, "results", "phase_10", "artifacts",
                                      "v4_causal_audit.parquet"))
    n_non = int((v4.causality == "non_causal").sum())
    n_caus = int((v4.causality == "CAUSAL").sum())

    carried = v4.assign(origin="v4", status_in_10d="carried unchanged",
                        retired_by_10d=False)[
        ["field", "causality", "reason", "origin", "status_in_10d", "retired_by_10d"]]
    added = pd.DataFrame(
        [{"field": f, "causality": c, "reason": r, "origin": "10d",
          "status_in_10d": "new in 10d", "retired_by_10d": False}
         for f, c, r in NEW_FIELDS])
    out = pd.concat([carried, added], ignore_index=True)
    out["config_hash"] = chash
    out.to_parquet(os.path.join(ART, "causal_audit.parquet"), index=False)

    summ = {
        "phase": "10d", "task": "T6a", "config_hash": chash,
        "v4_source": "results/phase_10/artifacts/v4_causal_audit.parquet",
        "v4_fields_total": int(len(v4)),
        "v4_non_causal": n_non, "v4_causal": n_caus,
        "v4_causal_fields": v4[v4.causality == "CAUSAL"].field.tolist(),
        "retired_by_10c": 0,
        "_retired_by_10c_source": ("results/phase_10c/digests/stage1_digest.json "
                                   "/v4_comparison/causal_status_vs_v4_causal_audit: "
                                   "n_retired_by_stage1 = 0, 'window stayed centered, not "
                                   "trailing; causal debt unchanged, still parked for "
                                   "Phase 17'"),
        "retired_by_10d": 0,
        "fields_added_by_10d": len(NEW_FIELDS),
        "fields_added_by_10d_causal": 0,
        "total_fields_after_10d": int(len(out)),
        "total_non_causal_after_10d": int((out.causality == "non_causal").sum()),
        "statement": (
            "10d RETIRES NO CAUSAL DEBT AND CLAIMS NONE. All 16 of v4's non-causal fields "
            "remain non-causal and all 8 fields 10d adds are non-causal too. The two causal "
            "fields -- detection_anchor_ns and detection_segment -- are unchanged. The debt "
            "stays parked for Phase 17. The reason is structural, not an oversight: the "
            "window is CENTRED (10c's committed D3_window, with 'trailing' a forbidden "
            "variant), so every quantity downstream of the local median reads forward in "
            "time by half a kernel; and the argmax-void threshold is a property of the "
            "completed-session histogram. A merge tolerance and a run-length floor operate "
            "on objects that are already non-causal and cannot make them causal."),
        "artifact": "results/phase_10d/artifacts/causal_audit.parquet"}
    with open(os.path.join(ART, "t6_causal_audit.json"), "w", encoding="utf-8") as f:
        json.dump(summ, f, indent=2)

    print(f"v4: {len(v4)} fields, {n_non} non_causal, {n_caus} CAUSAL "
          f"({', '.join(summ['v4_causal_fields'])})")
    print(f"10c retired: 0   10d retires: 0   10d adds: {len(NEW_FIELDS)}, all non_causal")
    print(f"after 10d: {len(out)} fields, {summ['total_non_causal_after_10d']} non_causal")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
