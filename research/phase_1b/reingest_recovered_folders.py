"""
Phase 1b T4b - re-ingest the 7 in-scope (common/common_adr) recovered
folders into the existing filtered_trades/filtered_quotes tables, reusing
src.data.ingest's schema-union insert mechanics (same helpers load_filtered
uses internally). INSERT INTO the existing tables - does not recreate them.

Writes to filtered_trades/filtered_quotes ONLY here, per the phase's write
scope. Never touches any other table.
"""
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from src.data.db import get_connection  # noqa: E402
from src.data.ingest import _build_select_for_file, _row_count, _scan_union_schema  # noqa: E402

PRE_LIST_PATH = "results/phase_1b/artifacts/t4_pre_ingestion_list.json"
OUT_SUMMARY = "results/phase_1b/artifacts/t4_reingest_summary.json"

TYPE_OVERRIDES = {
    "trades": {"size": "BIGINT", "participant_timestamp": "BIGINT"},
    "quotes": {"ask_size": "BIGINT", "bid_size": "BIGINT"},
}


def main():
    with open(PRE_LIST_PATH) as f:
        folders = json.load(f)["folders"]

    con = get_connection(read_only=False)

    results = []
    for label, parquet_name, table_name, exists_key in [
        ("trades", "trades.parquet", "filtered_trades", "trades_parquet_exists"),
        ("quotes", "quotes.parquet", "filtered_quotes", "quotes_parquet_exists"),
    ]:
        eligible = [f for f in folders if f[exists_key]]
        if not eligible:
            continue
        paths = [Path(f"data/filtered/{f['folder_name']}/{parquet_name}") for f in eligible]

        union_schema, file_columns = _scan_union_schema(con, paths, type_overrides=TYPE_OVERRIDES[label])

        before = _row_count(con, table_name)
        for f, pq_path in zip(eligible, paths):
            posix_path = pq_path.as_posix()
            select_list = _build_select_for_file(
                posix_path,
                union_schema,
                file_columns,
                [
                    ("ticker", f"'{f['ticker']}'"),
                    ("event_date", f"'{f['date']}'::DATE"),
                    ("momentum_pct", f"CAST({f['momentum_str']} AS DOUBLE)"),
                ],
            )
            con.execute(
                f'INSERT INTO "{table_name}" BY NAME '
                f"SELECT {select_list} FROM read_parquet('{posix_path}')"
            )
        after = _row_count(con, table_name)
        results.append({"table": table_name, "n_files_inserted": len(eligible), "rows_before": before, "rows_after": after, "rows_added": after - before})

    # Post-ingest per-folder verification
    per_folder = []
    for f in folders:
        t_rows = con.execute(
            "SELECT COUNT(*) FROM filtered_trades WHERE ticker = ? AND event_date = ?",
            [f["ticker"], f["date"]],
        ).fetchone()[0]
        q_rows = con.execute(
            "SELECT COUNT(*) FROM filtered_quotes WHERE ticker = ? AND event_date = ?",
            [f["ticker"], f["date"]],
        ).fetchone()[0]
        per_folder.append({
            "folder_name": f["folder_name"], "ticker": f["ticker"], "date": f["date"],
            "trades_parquet_existed": f["trades_parquet_exists"], "quotes_parquet_existed": f["quotes_parquet_exists"],
            "n_trades_rows": t_rows, "n_quotes_rows": q_rows,
        })

    zero_row_folders = [
        p for p in per_folder
        if (p["trades_parquet_existed"] and p["n_trades_rows"] == 0)
        or (p["quotes_parquet_existed"] and p["n_quotes_rows"] == 0)
    ]
    missing_source_zero = [
        p for p in per_folder
        if (not p["quotes_parquet_existed"] and p["n_quotes_rows"] == 0)
    ]

    summary = {
        "phase": "1b",
        "task": "T4b",
        "table_load_results": results,
        "per_folder_verification": per_folder,
        "zero_row_folders_any_reason": zero_row_folders,
        "zero_row_explained_by_missing_source_file": missing_source_zero,
        "zero_row_unexplained": [p for p in zero_row_folders if p not in missing_source_zero],
        "escalation": {
            "criterion": "any re-ingested folder with 0 rows post-ingest",
            "n_zero_row_folders": len(zero_row_folders),
            "triggered": len(zero_row_folders) > 0,
        },
    }

    with open(OUT_SUMMARY, "w") as f:
        json.dump(summary, f, indent=2, default=str)
    print(json.dumps(summary, indent=2, default=str))


if __name__ == "__main__":
    main()
