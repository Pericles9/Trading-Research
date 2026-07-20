"""
Phase 1c T3-R1 (Amendment 1) - derive which archive columns are optional
(legitimately, conditionally absent - collection-time behavior, not a
vendor regression) vs required.

A column qualifies as optional iff BOTH:
  (a) non-null rate in the full filtered_trades/filtered_quotes table is
      below config's non_null_rate_threshold_pct, AND
  (b) demonstrably absent from the per-file schema of >=1 file in a seeded
      sample of file_sample_size archive parquet files for that table -
      proving conditional presence was original collection behavior.

conditions (trades, quotes) and indicators (quotes) are LIST-typed columns
dropped from the DB tables by src/data/ingest.py's deliberate design
(unrelated to sparsity - see research/phase_1c/derive_archive_schema.py).
Non-null rate cannot be measured against the DB tables for these; they are
checked for per-file presence only and, absent contrary evidence, treated
as required (they are core per-trade/per-quote fields, not optional
metadata - confirmed non-empty in every sample file inspected).
"""
import json

import duckdb

with open("config/phase_1c.json") as f:
    CFG = json.load(f)

DB_PATH = CFG["paths"]["momentum_events_db"]
DERIVE_CFG = CFG["optional_field_derivation"]
THRESHOLD_PCT = DERIVE_CFG["non_null_rate_threshold_pct"]
SAMPLE_SIZE = DERIVE_CFG["file_sample_size"]
SEED = DERIVE_CFG["seed"]
OUT_SUMMARY = "results/phase_1c/artifacts/t3r1_optional_fields.json"

DB_BACKED_COLUMNS = {
    "trades": CFG["archive_schema"]["db_table_columns_trades"],
    "quotes": CFG["archive_schema"]["db_table_columns_quotes"],
}
LIST_TYPED_COLUMNS = {
    "trades": ["conditions"],
    "quotes": ["conditions", "indicators"],
}


def non_null_rates(con, table_name, glob_pattern, columns):
    """Exact non-null counts via parquet footer statistics (row-group
    num_rows/null_count), not a full data scan - orders of magnitude
    faster (~170s vs 50+ min measured directly) for a 4.9B/3.8B-row corpus.
    A column absent from a file's physical schema contributes 0 rows and 0
    nulls for that file's row groups (consistent with NULL-fill via
    INSERT ... BY NAME); dividing by the true DB-table row count (not the
    per-column row-group-presence count, which undercounts if the column
    is absent from some files) reproduces the same non-null rate a full
    data scan against the DB table would give."""
    total = con.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
    cols_sql = ", ".join(f"'{c}'" for c in columns)
    meta = con.execute(
        f"SELECT path_in_schema, SUM(row_group_num_rows) AS present_rows, SUM(stats_null_count) AS nulls "
        f"FROM parquet_metadata('{glob_pattern}') WHERE path_in_schema IN ({cols_sql}) GROUP BY path_in_schema"
    ).fetchdf()
    meta = meta.set_index("path_in_schema")
    counts = {}
    for c in columns:
        if c in meta.index:
            present_rows, nulls = meta.loc[c, "present_rows"], meta.loc[c, "nulls"]
            counts[c] = int(present_rows - nulls)
        else:
            counts[c] = 0
    return total, counts


def file_absence_counts(con, folder_glob_col, columns, sample_size, seed):
    import random
    from pathlib import Path

    all_files = sorted(Path("data/filtered").glob(folder_glob_col))
    rng = random.Random(seed)
    sample = rng.sample(all_files, min(sample_size, len(all_files)))

    posix_paths = [p.as_posix() for p in sample]
    file_list_sql = ", ".join(f"'{p}'" for p in posix_paths)
    schema_df = con.execute(
        f"SELECT file_name, name FROM parquet_schema([{file_list_sql}]) WHERE duckdb_type IS NOT NULL"
    ).df()
    present_by_file: dict[str, set[str]] = {}
    for fn, name in zip(schema_df["file_name"], schema_df["name"]):
        present_by_file.setdefault(fn, set()).add(name)

    absence_counts = {c: 0 for c in columns}
    for fn in posix_paths:
        cols_in_file = present_by_file.get(fn, set())
        for c in columns:
            if c not in cols_in_file:
                absence_counts[c] += 1
    return len(sample), absence_counts


def main():
    con = duckdb.connect(database=DB_PATH, read_only=True)

    result = {"phase": "1c", "task": "T3-R1", "threshold_non_null_pct": THRESHOLD_PCT, "file_sample_size": SAMPLE_SIZE, "seed": SEED, "tables": {}}

    for side, table_name, glob_name in [("trades", "filtered_trades", "*/trades.parquet"), ("quotes", "filtered_quotes", "*/quotes.parquet")]:
        db_cols = DB_BACKED_COLUMNS[side]
        total_rows, nn_counts = non_null_rates(con, table_name, f"data/filtered/{glob_name}", db_cols)
        n_sampled, absence_counts = file_absence_counts(con, glob_name, db_cols, SAMPLE_SIZE, SEED)

        fields = {}
        optional = []
        for c in db_cols:
            nn_rate_pct = 100 * nn_counts[c] / total_rows if total_rows else 0.0
            file_absence_rate_pct = 100 * absence_counts[c] / n_sampled if n_sampled else 0.0
            is_optional = (nn_rate_pct < THRESHOLD_PCT) and (absence_counts[c] > 0)
            fields[c] = {
                "non_null_count": nn_counts[c], "total_rows": total_rows, "non_null_rate_pct": round(nn_rate_pct, 6),
                "n_files_sampled": n_sampled, "n_files_missing_column": absence_counts[c],
                "file_absence_rate_pct": round(file_absence_rate_pct, 2),
                "optional": is_optional,
            }
            if is_optional:
                optional.append(c)

        # LIST-typed columns: presence-only check, no non-null-rate measurement possible
        list_cols = LIST_TYPED_COLUMNS[side]
        n_sampled_list, absence_list = file_absence_counts(con, glob_name, list_cols, SAMPLE_SIZE, SEED)
        for c in list_cols:
            fields[c] = {
                "non_null_count": None, "total_rows": None, "non_null_rate_pct": None,
                "n_files_sampled": n_sampled_list, "n_files_missing_column": absence_list[c],
                "file_absence_rate_pct": round(100 * absence_list[c] / n_sampled_list, 2) if n_sampled_list else 0.0,
                "optional": False,
                "note": "LIST-typed, dropped from DB tables by design (unrelated to sparsity) - non-null rate not measurable against the DB table; treated as required absent file-absence evidence.",
            }

        result["tables"][side] = {"fields": fields, "optional_fields": optional}

    con.close()

    CFG["optional_fields"]["trades"] = result["tables"]["trades"]["optional_fields"]
    CFG["optional_fields"]["quotes"] = result["tables"]["quotes"]["optional_fields"]
    with open("config/phase_1c.json", "w") as f:
        json.dump(CFG, f, indent=2)

    with open(OUT_SUMMARY, "w") as f:
        json.dump(result, f, indent=2, default=str)
    print(json.dumps(result, indent=2, default=str))

    n_trades_opt = len(result["tables"]["trades"]["optional_fields"])
    n_quotes_opt = len(result["tables"]["quotes"]["optional_fields"])
    print(f"\noptional_fields: trades={result['tables']['trades']['optional_fields']}, quotes={result['tables']['quotes']['optional_fields']}")
    if n_trades_opt > 4 or n_quotes_opt > 4:
        print("SURPRISE: >4 optional fields derived for a table - not a stop per Amendment 1's escalation table, flag under surprises.")


if __name__ == "__main__":
    main()
