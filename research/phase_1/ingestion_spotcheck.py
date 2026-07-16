"""
Phase 1 T5a - DB coverage spot-check for the 409 parser-fix-recovered folders.

Reconstructs the 409 (0c's build_folder_inventory.py pre-fix pattern excluded
them; commit 18ccc23 widened the ticker regex to accept '.' and lowercase).
Runs one aggregated presence query per table against filtered_trades and
filtered_quotes - ticker-level membership, event-window date match as a
secondary column. Post only - no ingestion, repair, or modification.

Full-tier query against 4.9B/3.8B row tables. Bounded (WHERE ticker IN (...)),
aggregated (GROUP BY), never materializes the full tables.
"""
import json
import re
import duckdb
import pandas as pd

FOLDER_INVENTORY = "results/phase_0c/artifacts/folder_inventory.parquet"
DB_PATH = "data/duckdb/main.duckdb"
OUT_PATH = "results/phase_1/artifacts/ingestion_spotcheck.json"

# Pre-fix pattern from research/phase_0c/build_folder_inventory.py (before commit 18ccc23)
OLD_PATTERN = re.compile(r"^(?P<ticker>[A-Z0-9]+)_(?P<date>\d{4}-\d{2}-\d{2})_(?P<mom>[\d.]+)$")


def main():
    con = duckdb.connect(read_only=False)
    inv = con.execute(f"SELECT * FROM read_parquet('{FOLDER_INVENTORY}')").fetchdf()

    recovered_mask = (~inv["folder_name"].apply(lambda n: OLD_PATTERN.match(n) is not None)) & (
        ~inv["date_is_none"]
    )
    the_409 = inv[recovered_mask].copy()
    assert len(the_409) == 409, f"expected 409 recovered folders, got {len(the_409)}"

    is_dot_ticker = the_409["ticker"].str.contains(r"\.", regex=True)
    n_dot_ticker = int(is_dot_ticker.sum())
    n_lowercase_suffix = int((~is_dot_ticker).sum())
    assert (n_dot_ticker, n_lowercase_suffix) == (194, 215), (n_dot_ticker, n_lowercase_suffix)

    the_409["momentum_pct"] = the_409["momentum_str"].astype(float)
    the_409["event_date"] = pd.to_datetime(the_409["date"]).dt.date

    results = {}
    for table in ["filtered_trades", "filtered_quotes"]:
        con_db = duckdb.connect(database=DB_PATH, read_only=True)
        con_db.register("the_409_tmp", the_409[["ticker", "event_date", "momentum_pct"]])

        # Primary: ticker-level membership (any rows for this ticker, any date) -
        # one aggregated query, bounded by IN(...), no full-table materialization.
        ticker_presence = con_db.execute(
            f"""
            SELECT ft.ticker, COUNT(*) AS n_rows
            FROM {table} ft
            WHERE ft.ticker IN (SELECT DISTINCT ticker FROM the_409_tmp)
            GROUP BY ft.ticker
            """
        ).fetchdf()

        # Secondary: event-window date match - same table, grouped by
        # (ticker, event_date) so each of the 409's specific events can be
        # checked against its own date, not just ticker presence anywhere.
        ticker_date_presence = con_db.execute(
            f"""
            SELECT ft.ticker, ft.event_date, COUNT(*) AS n_rows
            FROM {table} ft
            WHERE ft.ticker IN (SELECT DISTINCT ticker FROM the_409_tmp)
            GROUP BY ft.ticker, ft.event_date
            """
        ).fetchdf()
        con_db.close()

        ticker_rows = dict(zip(ticker_presence["ticker"], ticker_presence["n_rows"]))
        date_rows = {
            (t, d): n
            for t, d, n in zip(
                ticker_date_presence["ticker"], ticker_date_presence["event_date"], ticker_date_presence["n_rows"]
            )
        }

        the_409[f"{table}_ticker_any_rows"] = the_409["ticker"].map(ticker_rows).fillna(0).astype(int)
        the_409[f"{table}_exact_event_date_rows"] = [
            date_rows.get((t, d), 0) for t, d in zip(the_409["ticker"], the_409["event_date"])
        ]

        n_ticker_present = int((the_409[f"{table}_ticker_any_rows"] > 0).sum())
        n_exact_event_present = int((the_409[f"{table}_exact_event_date_rows"] > 0).sum())

        results[table] = {
            "n_folders_with_any_ticker_rows": n_ticker_present,
            "n_folders_with_any_ticker_rows_pct": round(100 * n_ticker_present / 409, 2),
            "n_folders_absent_ticker_level": 409 - n_ticker_present,
            "n_folders_with_exact_event_date_rows": n_exact_event_present,
            "n_folders_with_exact_event_date_rows_pct": round(100 * n_exact_event_present / 409, 2),
        }

    summary = {
        "phase": "1",
        "task": "T5a",
        "n_recovered_folders": 409,
        "n_dot_ticker": n_dot_ticker,
        "n_lowercase_suffix": n_lowercase_suffix,
        "reconstruction_method": "research/phase_0c/build_folder_inventory.py pre-fix ticker "
        "pattern [A-Z0-9]+ applied against folder_inventory.parquet's folder_name; rows that "
        "fail the old pattern but have date_is_none=False are the 409 recovered by commit "
        "18ccc23's widened pattern [A-Za-z0-9.]+.",
        "coverage": results,
        "note": "Post only. No ingestion, repair, or modification performed on any table.",
    }

    with open(OUT_PATH, "w") as f:
        json.dump(summary, f, indent=2, default=str)

    # per-folder detail retained for the report table, not committed (parquet, gitignored)
    the_409.to_parquet("results/phase_1/artifacts/ingestion_spotcheck_409_detail.parquet", index=False)

    print(json.dumps(summary, indent=2, default=str))


if __name__ == "__main__":
    main()
