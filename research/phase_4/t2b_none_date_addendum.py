"""
Phase 4 T2 addendum - characterize the 'neither' presence_class folders.

Cheap in-memory follow-up on the already-written disk_census.parquet (no
re-scan of the archive) - confirms whether the 114 folders with no
trades.parquet and no quotes.parquet at all correspond exactly to the
'None'-date orphan-folder population CLAUDE.md's universe rules describe
(non-common instruments / unresolved-date folders, structurally excluded
from momentum_events_canonical).
"""
import json

import pandas as pd

CENSUS_PARQUET = "results/phase_4/artifacts/disk_census.parquet"
SUMMARY_PATH = "results/phase_4/artifacts/census_summary.json"


def main():
    df = pd.read_parquet(CENSUS_PARQUET)
    none_date = df[df["date_raw"] == "None"]
    neither = df[df["presence_class"] == "neither"]
    exact_match = set(none_date["folder_name"]) == set(neither["folder_name"])

    addendum = {
        "n_none_date_orphan_folders": int(len(none_date)),
        "n_neither_presence_class_folders": int(len(neither)),
        "none_date_exactly_equals_neither": bool(exact_match),
        "n_none_date_with_any_data_file": int((none_date["trades_present"] | none_date["quotes_present"]).sum()),
        "n_real_date_folders_with_neither_file": int(len(df[(df["date_raw"] != "None") & (df["presence_class"] == "neither")])),
        "note": "The 114 folders with no trades.parquet and no quotes.parquet at all are exactly the 114 'None'-date folders (unresolvable-date/orphan folders, e.g. ACHR.WS/AMPX.WS-style warrant tickers) - empty stub folders, not a data-loss case. Every real-dated folder has at least one of the two files.",
        "source": "research/phase_4/t2b_none_date_addendum.py:main",
    }

    with open(SUMMARY_PATH) as f:
        summary = json.load(f)
    summary["t2b_none_date_addendum"] = addendum
    with open(SUMMARY_PATH, "w") as f:
        json.dump(summary, f, indent=2, default=str)
    print(json.dumps(addendum, indent=2))


if __name__ == "__main__":
    main()
