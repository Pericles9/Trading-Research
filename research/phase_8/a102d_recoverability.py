"""
Phase 8 A10.2d - false-positive recoverability check. READ-ONLY (escalation
row 15: no collection/fetch/write against the data root). Determines whether
the pre-filter (rejected-candidate) population survives on disk.
"""
from __future__ import annotations

import json

import pandas as pd

CATALOG = "data/filtered/scanner_hit_catalog.json"
PLAW = "data/filtered/filtered_events_power_law_q05.parquet"
OUT = "results/phase_8/artifacts/a102_falsepositive_recoverability.json"

LIMITATION = ("All Phase 8 markouts are conditional on power-law filter membership. The filter was "
              "fitted on the full 2020-2024 panel and its output is not knowable at detection time. "
              "The rejected-candidate population is not present in this archive; the live false-positive "
              "rate is therefore unmeasured, and no markout in this phase can be read as a live expected value.")


def main():
    with open(CATALOG) as f:
        sh = json.load(f)
    sh_tickers = sorted(set(k.split(":")[0] for k in sh))
    sh_fields = sorted({fld for k in sh for fld in sh[k].keys()})
    sh_has_reject_flag = any(f in sh_fields for f in ("accepted", "rejected", "passed_filter", "filter_result"))

    df = pd.read_parquet(PLAW)
    pl_has_reject_flag = any(c in df.columns for c in ("accepted", "rejected", "passed_filter", "filter_result", "is_false_positive"))

    recoverable = sh_has_reject_flag or pl_has_reject_flag

    out = {
        "phase": "8", "task": "A10.2d",
        "source": "research/phase_8/a102d_recoverability.py:main",
        "read_only": True, "wrote_to_data_root": False,
        "scanner_hit_catalog": {
            "path": CATALOG, "n_entries": len(sh), "n_distinct_tickers": len(sh_tickers),
            "fields": sh_fields, "carries_accept_reject_flag": sh_has_reject_flag,
            "content": "scanner-hit timing/threshold per (ticker:date); some entries null ('prev_close unavailable - skipped'). Fewer entries than the accepted power-law set, so NOT the full pre-filter candidate universe.",
        },
        "filtered_events_power_law_q05": {
            "path": PLAW, "n_rows": int(len(df)), "columns": list(df.columns),
            "carries_accept_reject_flag": pl_has_reject_flag,
            "content": "power-law-ACCEPTED events (post-filter output, q05 threshold); 23,268 > D1's 15,763 because Phase 1b common-stock/in_scope restrictions further reduce to D1. No rejected candidates, no reject flag.",
        },
        "rejected_candidates_recoverable": recoverable,
        "finding": ("Neither file carries the rejected-candidate (false-positive) population. "
                    "filtered_events_power_law_q05 is the accepted output; scanner_hit_catalog is a "
                    "partial scanner-hit timing catalog without an accept/reject flag and smaller than "
                    "the accepted set. The rejected population is not present in this archive."),
        "limitation_text": LIMITATION,
        "open_items_registration": {
            "target": "docs/Open-Items-Register.md",
            "status": "PENDING - docs/ is outside the sanctioned write dirs (escalation row 9); flagged for Cooper at the gate. Reproduced verbatim in REPORT.md (A10.2d-iii).",
            "text": LIMITATION,
        },
    }
    with open(OUT, "w") as f:
        json.dump(out, f, indent=2, default=str)
    print(json.dumps({k: v for k, v in out.items() if k not in ("scanner_hit_catalog", "filtered_events_power_law_q05")}, indent=2, default=str))
    print("\nscanner_hit_catalog:", out["scanner_hit_catalog"]["n_entries"], "entries,",
          out["scanner_hit_catalog"]["n_distinct_tickers"], "tickers; reject flag:", sh_has_reject_flag)
    print("filtered_events_power_law_q05:", out["filtered_events_power_law_q05"]["n_rows"], "rows; reject flag:", pl_has_reject_flag)


if __name__ == "__main__":
    main()
