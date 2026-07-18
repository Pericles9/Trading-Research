"""
Phase 1b T4c/T4-R2 - build folder_inventory_v2.parquet.

Combines: 0c's folder inventory (24,609 date-valid folders) + has_trades_file/
has_quotes_file (from disk, already scanned by 0c) + match status (0c's t2c) +
instrument classification (T1-R3) + recovered-409 ingestion scope status (T4c)
+ per-event trades_ingested/quotes_ingested/in_scope from momentum_events_canonical
for matched folders (T4-R2).
"""
import json
import re
import sys

import duckdb
import pandas as pd

sys.path.insert(0, ".")
from src.data.db import get_connection  # noqa: E402

FOLDER_INVENTORY = "results/phase_0c/artifacts/folder_inventory.parquet"
JOIN_RECON_DETAIL = "results/phase_0c/artifacts/join_reconciliation_detail.json"
CLASSIFICATION = "results/phase_1b/artifacts/instrument_classification.parquet"
OUT_PARQUET = "results/phase_1b/artifacts/folder_inventory_v2.parquet"
OUT_SUMMARY = "results/phase_1b/artifacts/folder_inventory_v2_summary.json"

OLD_PATTERN = re.compile(r"^(?P<ticker>[A-Z0-9]+)_(?P<date>\d{4}-\d{2}-\d{2})_(?P<mom>[\d.]+)$")


def main():
    con = duckdb.connect(read_only=False)

    inv = con.execute(f"SELECT * FROM read_parquet('{FOLDER_INVENTORY}')").fetchdf()
    inv = inv.rename(columns={"class": "files_class", "has_trades": "has_trades_file", "has_quotes": "has_quotes_file"})
    inv = inv[inv["date_is_none"] == False].copy()  # noqa: E712 - scope: 24,609 date-valid folders
    assert len(inv) == 24609, len(inv)

    with open(JOIN_RECON_DETAIL) as f:
        t2c = pd.DataFrame(json.load(f)["t2c_results"])
    inv = inv.merge(t2c.rename(columns={"class": "match_status"}), on="folder_name", how="left")

    cls = con.execute(f"SELECT ticker, class AS instrument_class FROM read_parquet('{CLASSIFICATION}')").fetchdf()
    inv = inv.merge(cls, on="ticker", how="left")

    # Recovered-409 flag + ingestion scope status (T4c)
    recovered_mask = (~inv["folder_name"].apply(lambda n: OLD_PATTERN.match(n) is not None))
    inv["in_recovered_409"] = recovered_mask
    with open("results/phase_1b/artifacts/t4_pre_ingestion_list.json") as f:
        ingested_folders = {f["folder_name"] for f in json.load(f)["folders"]}

    def scope_status(row):
        if not row["in_recovered_409"]:
            return "not_applicable_pre_existing"
        if row["folder_name"] in ingested_folders:
            return "ingested"
        return "out_of_scope_unigested"

    inv["ingestion_scope_status"] = inv.apply(scope_status, axis=1)

    # Per-event trades_ingested/quotes_ingested/in_scope from the canonical
    # view, for matched folders (join on ticker + date + momentum, 2dp).
    con_db = get_connection(read_only=True)
    canon = con_db.execute(
        "SELECT ticker, event_date_canonical, ROUND(momentum_pct,2) AS mom_2dp, "
        "trades_ingested, quotes_ingested, in_scope FROM momentum_events_canonical"
    ).fetchdf()
    con_db.close()

    inv["mom_2dp"] = inv["momentum_str"].astype(float).round(2)
    inv["date_str"] = inv["date"]
    canon["date_str"] = canon["event_date_canonical"].astype(str)
    inv = inv.merge(
        canon[["ticker", "date_str", "mom_2dp", "trades_ingested", "quotes_ingested", "in_scope"]],
        on=["ticker", "date_str", "mom_2dp"], how="left",
    )

    keep_cols = [
        "folder_name", "ticker", "date", "momentum_str", "has_trades_file", "has_quotes_file",
        "match_status", "instrument_class", "in_recovered_409", "ingestion_scope_status",
        "trades_ingested", "quotes_ingested", "in_scope",
    ]
    inv[keep_cols].to_parquet(OUT_PARQUET, index=False)

    # T4-R2 headline table: trades-file-but-no-quotes-file, by class and by year
    trades_only = inv[(inv["has_trades_file"] == True) & (inv["has_quotes_file"] == False)].copy()  # noqa: E712
    trades_only["year"] = trades_only["date"].str.slice(0, 4)

    by_class = trades_only["instrument_class"].value_counts(dropna=False).to_dict()
    by_year = trades_only["year"].value_counts(dropna=False).sort_index().to_dict()

    n_trades_only = len(trades_only)
    expected = 1540
    diff = n_trades_only - expected
    surprise = abs(diff) > 50

    summary = {
        "phase": "1b",
        "task": "T4c_T4R2",
        "n_folders_total_date_valid": len(inv),
        "n_recovered_409": int(inv["in_recovered_409"].sum()),
        "ingestion_scope_status_counts": inv["ingestion_scope_status"].value_counts().to_dict(),
        "t4r2_trades_only_headline": {
            "n_folders_trades_file_no_quotes_file": n_trades_only,
            "n_events_affected": n_trades_only,  # 1:1 folder-to-event at this granularity
            "by_instrument_class": {str(k): int(v) for k, v in by_class.items()},
            "by_year": {str(k): int(v) for k, v in by_year.items()},
        },
        "t4r2a_cross_check": {
            "observed": n_trades_only,
            "expected_approx": expected,
            "diff": diff,
            "diff_exceeds_50": surprise,
            "note": "Not a hard stop per Amendment 2 T4-R2a - noted as a surprise if diff > 50, Phase 4 owns the explanation.",
        },
    }

    with open(OUT_SUMMARY, "w") as f:
        json.dump(summary, f, indent=2, default=str)
    print(json.dumps(summary, indent=2, default=str))


if __name__ == "__main__":
    main()
