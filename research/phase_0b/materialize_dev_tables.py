"""Materialize dev_events, filtered_trades_dev, filtered_quotes_dev in the
E: DuckDB from the pinned config/dev_sample_events.csv.

Reuses src.data.ingest's schema-union helpers (the same logic that builds
filtered_trades/filtered_quotes) so the dev tables see the same type-drift
handling as the full-tier tables.
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import duckdb

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from src.data.db import get_connection  # noqa: E402
from src.data.ingest import _scan_union_schema, _build_select_for_file, _row_count  # noqa: E402


def load_dev_sample_csv() -> list[dict]:
    path = REPO_ROOT / "config" / "dev_sample_events.csv"
    with path.open(encoding="utf-8") as f:
        return list(csv.DictReader(f))


def materialize_dev_events(con: duckdb.DuckDBPyConnection, rows: list[dict]) -> None:
    con.execute("DROP TABLE IF EXISTS dev_events")
    con.execute(
        "CREATE TABLE dev_events (decile INTEGER, ticker VARCHAR, date DATE, "
        "momentum_pct DOUBLE, folder VARCHAR)"
    )
    for r in rows:
        con.execute(
            "INSERT INTO dev_events VALUES (?, ?, ?, ?, ?)",
            [int(r["decile"]), r["ticker"], r["date"], float(r["momentum_pct"]), r["folder"]],
        )


def materialize_filtered_dev(
    con: duckdb.DuckDBPyConnection, rows: list[dict], data_root: Path
) -> dict:
    filtered_dir = data_root / "filtered"
    results = {}

    type_overrides_by_label = {
        "trades": {"size": "BIGINT", "participant_timestamp": "BIGINT"},
        "quotes": {"ask_size": "BIGINT", "bid_size": "BIGINT"},
    }

    for label, parquet_name, table_name in [
        ("trades", "trades.parquet", "filtered_trades_dev"),
        ("quotes", "quotes.parquet", "filtered_quotes_dev"),
    ]:
        con.execute(f'DROP TABLE IF EXISTS "{table_name}"')

        files_meta = []
        for r in rows:
            pq = filtered_dir / r["folder"] / parquet_name
            files_meta.append((pq, r["ticker"], r["date"], float(r["momentum_pct"])))

        union_schema, file_columns = _scan_union_schema(
            con,
            [pq for pq, _, _, _ in files_meta],
            type_overrides=type_overrides_by_label[label],
        )
        col_ddl = ", ".join(f'"{c}" {t}' for c, t in union_schema.items())
        con.execute(
            f'CREATE TABLE "{table_name}" ({col_ddl}, '
            f'"ticker" VARCHAR, "event_date" DATE, "momentum_pct" DOUBLE)'
        )

        per_event_counts = {}
        for pq_path, ticker, event_date, momentum_pct in files_meta:
            posix_path = pq_path.as_posix()
            select_list = _build_select_for_file(
                posix_path,
                union_schema,
                file_columns,
                [
                    ("ticker", f"'{ticker}'"),
                    ("event_date", f"'{event_date}'::DATE"),
                    ("momentum_pct", f"CAST({momentum_pct} AS DOUBLE)"),
                ],
            )
            before = _row_count(con, table_name)
            con.execute(
                f'INSERT INTO "{table_name}" BY NAME '
                f"SELECT {select_list} FROM read_parquet('{posix_path}')"
            )
            after = _row_count(con, table_name)
            per_event_counts[f"{ticker}_{event_date}"] = after - before

        results[table_name] = {
            "total_rows": _row_count(con, table_name),
            "per_event_rows": per_event_counts,
        }

    return results


def main(out_path: str) -> None:
    rows = load_dev_sample_csv()
    con = get_connection(read_only=False)
    try:
        materialize_dev_events(con, rows)
        dev_events_count = _row_count(con, "dev_events")

        from src.data.paths import resolve_data_root

        filtered_results = materialize_filtered_dev(con, rows, resolve_data_root())
    finally:
        con.close()

    summary = {
        "dev_events_rows": dev_events_count,
        **filtered_results,
    }
    out = REPO_ROOT / out_path
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps({k: (v if k == "dev_events_rows" else v["total_rows"]) for k, v in summary.items()}, indent=2))


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "results/phase_0b/artifacts/dev_tables_materialized.json"
    main(target)
