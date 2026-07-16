# --- Provenance (Phase 0b T2) ---
# Recovered from D:\Trading Research\src\data\ingest.py (modified/uncommitted
# relative to that repo's HEAD; no commit hash applies). Source mtime:
# 2026-07-12 (same day the D:->E: migration completed). Content unmodified
# from the D: copy.
# ---------------------------------
"""
DuckDB data ingest pipeline for mom_db.

Usage:
    python -m src.data.ingest --all
    python -m src.data.ingest --dataset filtered
    python -m src.data.ingest --dataset minute --dataset daily
"""
from __future__ import annotations

import argparse
import json
import logging
import re
import sys
from datetime import date
from pathlib import Path
from typing import Callable

import duckdb
import pandas as pd

from src.data.db import get_connection
from src.data.paths import resolve_data_root

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
LOG_DIR = Path(__file__).parents[2] / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "ingest.log"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("ingest")

DATA_ROOT = resolve_data_root()

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _table_exists(con: duckdb.DuckDBPyConnection, name: str) -> bool:
    """Check if table or view already exists."""
    result = con.execute(
        "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = ?",
        [name],
    ).fetchone()
    return result[0] > 0  # type: ignore[index]


def _view_exists(con: duckdb.DuckDBPyConnection, name: str) -> bool:
    """Check if view exists."""
    result = con.execute(
        "SELECT COUNT(*) FROM information_schema.tables "
        "WHERE table_name = ? AND table_type = 'VIEW'",
        [name],
    ).fetchone()
    return result[0] > 0  # type: ignore[index]


def _row_count(con: duckdb.DuckDBPyConnection, name: str) -> int:
    return con.execute(f'SELECT COUNT(*) FROM "{name}"').fetchone()[0]  # type: ignore[index]


def _safe_glob(root: Path, pattern: str) -> list[Path]:
    """Glob, but return empty list instead of raising."""
    try:
        return sorted(root.glob(pattern))
    except Exception:
        return []


def _scan_union_schema(
    con: duckdb.DuckDBPyConnection,
    paths: list[Path],
    type_overrides: dict[str, str] | None = None,
    exclude_columns: set[str] | None = None,
) -> tuple[dict[str, str], dict[str, dict[str, str]]]:
    """Metadata-only scan of column names/types across a set of parquet files.

    Real corpora in this project mix files with different native schemas
    (subtractive vs. full-column migrations) and occasional per-file type
    drift (e.g. an all-integer column stored as DOUBLE in a minority of
    files). A plain CREATE TABLE AS + INSERT INTO on the first file's shape
    fails on every subsequent file that doesn't match it exactly.

    Returns (union_schema, file_columns):
      union_schema — {column: sql_type}, the full column set with a
        resolved type for each, used to build the CREATE TABLE.
      file_columns — {posix_path: {column: native_type}}, per-file column
        presence, used to build a per-file SELECT list (columns the file
        doesn't have are simply omitted; INSERT ... BY NAME NULL-fills
        them automatically).

    A type conflict (a column seen with more than one native type across
    the file set) must have an explicit entry in type_overrides, or this
    raises — conflicts are resolved by investigating the actual data, never
    by silently picking a type. See
    results/ingestion_run/schema_drift_characterization.md for the
    conflicts already investigated in this corpus.
    """
    type_overrides = type_overrides or {}
    exclude_columns = exclude_columns or set()

    posix_paths = [p.as_posix() for p in paths]
    file_list_sql = ", ".join(f"'{p}'" for p in posix_paths)
    df = con.execute(
        f"SELECT file_name, name, duckdb_type FROM parquet_schema([{file_list_sql}])"
    ).df()

    # parquet_schema() flattens the file's internal tree, not just top-level
    # columns. Nested types (LIST/MAP/STRUCT) surface as extra rows for
    # Parquet's physical encoding — a "schema" root row, and for each LIST
    # column a wrapper row (the column's own name, duckdb_type NULL) plus a
    # "list"/"element" pair carrying the leaf type. Naively keeping every row
    # misreads "element" as if it were a genuine flat column (this broke an
    # earlier version of this function). duckdb_type is NULL/NaN exactly for
    # the non-leaf wrapper rows, so filtering to real (string) duckdb_type
    # values already excludes "schema" and the LIST column's own wrapper row;
    # "list"/"element"/"key"/"value" are Parquet's reserved internal names
    # for the leaf level and are excluded explicitly. This corpus's only
    # LIST-typed columns (conditions, indicators) are confirmed unused by any
    # downstream code (see column_usage_scope.csv from the quotes-fix phase)
    # — dropping them here is a deliberate choice, not an accident of this
    # filter, and would need revisiting if a future LIST column mattered.
    PARQUET_LIST_INTERNAL_NAMES = {"schema", "list", "element", "key", "value", "entries"}

    file_columns: dict[str, dict[str, str]] = {}
    types_seen: dict[str, set[str]] = {}
    for file_name, name, dtype in zip(df["file_name"], df["name"], df["duckdb_type"]):
        if name in exclude_columns or name in PARQUET_LIST_INTERNAL_NAMES:
            continue
        if not isinstance(dtype, str):
            continue
        file_columns.setdefault(file_name, {})[name] = dtype
        types_seen.setdefault(name, set()).add(dtype)

    union_schema: dict[str, str] = {}
    for name, types in types_seen.items():
        if name in type_overrides:
            union_schema[name] = type_overrides[name]
        elif len(types) == 1:
            union_schema[name] = next(iter(types))
        else:
            raise ValueError(
                f"Unresolved type conflict for column '{name}': {sorted(types)}. "
                "Investigate and add an explicit type_overrides entry — "
                "do not silently cast."
            )

    return union_schema, file_columns


def _build_select_for_file(
    posix_path: str,
    union_schema: dict[str, str],
    file_columns: dict[str, dict[str, str]],
    literal_columns: list[tuple[str, str]],
) -> str:
    """Build a BY-NAME INSERT SELECT list for one file: only the columns
    this specific file actually has (cast to the resolved union type where
    it differs from the file's native type), plus literal columns computed
    from the folder/file name. Columns this file lacks are simply omitted —
    INSERT ... BY NAME NULL-fills them in the target table automatically."""
    cols = file_columns.get(posix_path, {})
    parts = [f'CAST("{name}" AS {union_schema[name]}) AS "{name}"' for name in cols]
    parts += [f'{expr} AS "{name}"' for name, expr in literal_columns]
    return ", ".join(parts)

# ---------------------------------------------------------------------------
# Dataset loaders
# ---------------------------------------------------------------------------

def load_filtered(con: duckdb.DuckDBPyConnection, data_root: Path) -> None:
    """Load filtered/ event TAQ snapshots into filtered_trades and filtered_quotes."""
    filtered_dir = data_root / "filtered"
    if not filtered_dir.exists():
        log.warning("filtered/ directory not found — skipping")
        return

    # Pattern: {TICKER}_{YYYY-MM-DD}_{momentum_pct_2dp}
    folder_pattern = re.compile(
        r"^(?P<ticker>[A-Z0-9]+)_(?P<date>\d{4}-\d{2}-\d{2})_(?P<mom>[\d.]+)$"
    )

    # Known, investigated type conflicts — see
    # results/ingestion_run/schema_drift_characterization.md. All *_size
    # conflicts verified whole-number-only across the full corpus;
    # participant_timestamp verified structurally unrecoverable in its
    # DOUBLE-typed minority (exceeds double's exact-integer range) and
    # confirmed unused by any downstream code.
    type_overrides_by_label = {
        "trades": {"size": "BIGINT", "participant_timestamp": "BIGINT"},
        "quotes": {"ask_size": "BIGINT", "bid_size": "BIGINT"},
    }

    for label, parquet_name, table_name in [
        ("trades", "trades.parquet", "filtered_trades"),
        ("quotes", "quotes.parquet", "filtered_quotes"),
    ]:
        if _table_exists(con, table_name):
            log.info(f"[{table_name}] already exists ({_row_count(con, table_name):,} rows) — skipping")
            continue

        files_meta: list[tuple[Path, str, str, float]] = []
        for d in sorted(filtered_dir.iterdir()):
            if not d.is_dir():
                continue
            m = folder_pattern.match(d.name)
            if not m:
                log.debug(f"Skipping non-matching folder: {d.name}")
                continue
            pq = d / parquet_name
            if pq.exists():
                files_meta.append(
                    (pq, m.group("ticker"), m.group("date"), float(m.group("mom")))
                )

        if not files_meta:
            log.warning(f"[{table_name}] No {parquet_name} files found")
            continue

        log.info(f"[{table_name}] Scanning schema across {len(files_meta)} files ...")
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

        log.info(f"[{table_name}] Loading {len(files_meta)} files ...")
        loaded = 0
        for pq_path, ticker, event_date, momentum_pct in files_meta:
            try:
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
                con.execute(
                    f'INSERT INTO "{table_name}" BY NAME '
                    f"SELECT {select_list} FROM read_parquet('{posix_path}')"
                )
                loaded += 1
            except Exception as exc:
                log.error(f"[{table_name}] Failed on {pq_path}: {exc}")

        log.info(f"[{table_name}] → {_row_count(con, table_name):,} rows from {loaded} files")


def load_daily(con: duckdb.DuckDBPyConnection, data_root: Path) -> None:
    """Load daily/ OHLCV bars into daily_bars."""
    table_name = "daily_bars"
    if _table_exists(con, table_name):
        log.info(f"[{table_name}] already exists ({_row_count(con, table_name):,} rows) — skipping")
        return

    daily_dir = data_root / "daily"
    if not daily_dir.exists():
        log.warning("daily/ directory not found — skipping")
        return

    files = _safe_glob(daily_dir, "*_daily.parquet")
    if not files:
        log.warning(f"[{table_name}] No *_daily.parquet files found")
        return

    log.info(f"[{table_name}] Loading {len(files)} files ...")
    first = True
    loaded = 0
    for f in files:
        ticker = f.stem.replace("_daily", "")
        try:
            q = f"""
                SELECT *, '{ticker}' AS ticker
                FROM read_parquet('{f.as_posix()}')
            """
            if first:
                con.execute(f'CREATE TABLE "{table_name}" AS {q}')
                first = False
            else:
                con.execute(f'INSERT INTO "{table_name}" {q}')
            loaded += 1
        except Exception as exc:
            log.error(f"[{table_name}] Failed on {f}: {exc}")

    if not first:
        log.info(f"[{table_name}] → {_row_count(con, table_name):,} rows from {loaded} files")


def load_minute(con: duckdb.DuckDBPyConnection, data_root: Path) -> None:
    """Load minute/ bars into minute_bars."""
    table_name = "minute_bars"
    if _table_exists(con, table_name):
        log.info(f"[{table_name}] already exists ({_row_count(con, table_name):,} rows) — skipping")
        return

    minute_dir = data_root / "minute"
    if not minute_dir.exists():
        log.warning("minute/ directory not found — skipping")
        return

    # minute/{TICKER}/{YYYY-MM-DD}.parquet
    log.info(f"[{table_name}] Scanning minute/ ...")
    first = True
    loaded = 0
    for ticker_dir in sorted(minute_dir.iterdir()):
        if not ticker_dir.is_dir():
            continue
        ticker = ticker_dir.name
        for f in _safe_glob(ticker_dir, "*.parquet"):
            session_date = f.stem  # YYYY-MM-DD
            try:
                q = f"""
                    SELECT *, '{ticker}' AS ticker,
                           '{session_date}'::DATE AS session_date
                    FROM read_parquet('{f.as_posix()}')
                """
                if first:
                    con.execute(f'CREATE TABLE "{table_name}" AS {q}')
                    first = False
                else:
                    con.execute(f'INSERT INTO "{table_name}" {q}')
                loaded += 1
            except Exception as exc:
                log.error(f"[{table_name}] Failed on {f}: {exc}")

    if not first:
        log.info(f"[{table_name}] → {_row_count(con, table_name):,} rows from {loaded} files")
    else:
        log.warning(f"[{table_name}] No parquet files found in minute/")


def load_second10(con: duckdb.DuckDBPyConnection, data_root: Path) -> None:
    """Load second10/ bars into second10_bars."""
    table_name = "second10_bars"
    if _table_exists(con, table_name):
        log.info(f"[{table_name}] already exists ({_row_count(con, table_name):,} rows) — skipping")
        return

    s10_dir = data_root / "second10"
    if not s10_dir.exists():
        log.warning("second10/ directory not found — skipping")
        return

    log.info(f"[{table_name}] Scanning second10/ ...")
    first = True
    loaded = 0
    for ticker_dir in sorted(s10_dir.iterdir()):
        if not ticker_dir.is_dir():
            continue
        ticker = ticker_dir.name
        for f in _safe_glob(ticker_dir, "*.parquet"):
            # Filename: {TICKER}_{YYYY-MM-DD}.parquet — parse date
            date_match = re.search(r"(\d{4}-\d{2}-\d{2})", f.stem)
            session_date = date_match.group(1) if date_match else "1970-01-01"
            try:
                q = f"""
                    SELECT *, '{ticker}' AS ticker,
                           '{session_date}'::DATE AS session_date
                    FROM read_parquet('{f.as_posix()}')
                """
                if first:
                    con.execute(f'CREATE TABLE "{table_name}" AS {q}')
                    first = False
                else:
                    con.execute(f'INSERT INTO "{table_name}" {q}')
                loaded += 1
            except Exception as exc:
                log.error(f"[{table_name}] Failed on {f}: {exc}")

    if not first:
        log.info(f"[{table_name}] → {_row_count(con, table_name):,} rows from {loaded} files")
    else:
        log.warning(f"[{table_name}] No parquet files found in second10/")


def load_quote_data(con: duckdb.DuckDBPyConnection, data_root: Path) -> None:
    """Load quote_data/ tick files into raw_quotes."""
    table_name = "raw_quotes"
    if _table_exists(con, table_name):
        log.info(f"[{table_name}] already exists ({_row_count(con, table_name):,} rows) — skipping")
        return

    qd_dir = data_root / "quote_data"
    if not qd_dir.exists():
        log.warning("quote_data/ directory not found — skipping")
        return

    # Pattern: {TICKER}_quotes_{YYYY}_{MM}_{DD}.parquet
    pat = re.compile(r"^(?P<ticker>[A-Z0-9]+)_quotes_(?P<y>\d{4})_(?P<m>\d{2})_(?P<d>\d{2})\.parquet$")

    files_meta: list[tuple[Path, str, str]] = []
    for f in sorted(qd_dir.glob("*.parquet")):
        m = pat.match(f.name)
        if not m:
            log.debug(f"Skipping non-matching file: {f.name}")
            continue
        quote_date = f"{m.group('y')}-{m.group('m')}-{m.group('d')}"
        files_meta.append((f, m.group("ticker"), quote_date))

    if not files_meta:
        log.warning(f"[{table_name}] No parquet files found in quote_data/")
        return

    # __index_level_0__ is a pandas-index serialization artifact (present in
    # ~10% of files), not real data — dropped, not unioned. ask_size/bid_size
    # DOUBLE-vs-BIGINT drift verified whole-number-only across the full
    # corpus. See results/ingestion_run/schema_drift_characterization.md.
    log.info(f"[{table_name}] Scanning schema across {len(files_meta)} files ...")
    try:
        union_schema, file_columns = _scan_union_schema(
            con,
            [f for f, _, _ in files_meta],
            type_overrides={"ask_size": "BIGINT", "bid_size": "BIGINT"},
            exclude_columns={"__index_level_0__"},
        )
    except duckdb.Error as exc:
        # A handful of files in this corpus are known-corrupted (fail to
        # even open) — fall back to a per-file scan so one bad file doesn't
        # block schema discovery for the other ~19,132.
        log.warning(f"[{table_name}] Bulk schema scan failed ({exc}); retrying file-by-file")
        readable = []
        for f, _, _ in files_meta:
            try:
                con.execute(f"SELECT * FROM parquet_schema('{f.as_posix()}') LIMIT 1").fetchone()
                readable.append(f)
            except duckdb.Error as file_exc:
                log.error(f"[{table_name}] Unreadable, excluded: {f}: {file_exc}")
        union_schema, file_columns = _scan_union_schema(
            con,
            readable,
            type_overrides={"ask_size": "BIGINT", "bid_size": "BIGINT"},
            exclude_columns={"__index_level_0__"},
        )

    col_ddl = ", ".join(f'"{c}" {t}' for c, t in union_schema.items())
    con.execute(
        f'CREATE TABLE "{table_name}" ({col_ddl}, "ticker" VARCHAR, "quote_date" DATE)'
    )

    log.info(f"[{table_name}] Loading {len(files_meta)} files ...")
    loaded = 0
    for f, ticker, quote_date in files_meta:
        posix_path = f.as_posix()
        if posix_path not in file_columns:
            log.error(f"[{table_name}] Failed on {f}: unreadable (excluded during schema scan)")
            continue
        try:
            select_list = _build_select_for_file(
                posix_path,
                union_schema,
                file_columns,
                [
                    ("ticker", f"'{ticker}'"),
                    ("quote_date", f"'{quote_date}'::DATE"),
                ],
            )
            con.execute(
                f'INSERT INTO "{table_name}" BY NAME '
                f"SELECT {select_list} FROM read_parquet('{posix_path}')"
            )
            loaded += 1
        except Exception as exc:
            log.error(f"[{table_name}] Failed on {f}: {exc}")

    log.info(f"[{table_name}] → {_row_count(con, table_name):,} rows from {loaded} files")


def load_momentum_events(con: duckdb.DuckDBPyConnection, data_root: Path) -> None:
    """Load momentum_events/ filtered event table."""
    table_name = "momentum_events"
    if _table_exists(con, table_name):
        log.info(f"[{table_name}] already exists ({_row_count(con, table_name):,} rows) — skipping")
        return

    pq = data_root / "momentum_events" / "filtered_events_power_law_q05.parquet"
    if not pq.exists():
        log.warning(f"[{table_name}] {pq} not found — skipping")
        return

    try:
        con.execute(f"""
            CREATE TABLE "{table_name}" AS
            SELECT * FROM read_parquet('{pq.as_posix()}')
        """)
        log.info(f"[{table_name}] → {_row_count(con, table_name):,} rows")
    except Exception as exc:
        log.error(f"[{table_name}] Failed: {exc}")


def load_metadata(con: duckdb.DuckDBPyConnection, data_root: Path) -> None:
    """Load metadata/ parquet files as individual tables."""
    meta_dir = data_root / "metadata"
    if not meta_dir.exists():
        log.warning("metadata/ directory not found — skipping")
        return

    for fname, table_name in [
        ("collection_stats.parquet", "collection_stats"),
        ("symbols_metadata.parquet", "symbols_metadata"),
    ]:
        if _table_exists(con, table_name):
            log.info(f"[{table_name}] already exists — skipping")
            continue
        pq = meta_dir / fname
        if not pq.exists():
            log.warning(f"[{table_name}] {pq} not found — skipping")
            continue
        try:
            con.execute(f"""
                CREATE TABLE "{table_name}" AS
                SELECT * FROM read_parquet('{pq.as_posix()}')
            """)
            log.info(f"[{table_name}] → {_row_count(con, table_name):,} rows")
        except Exception as exc:
            log.error(f"[{table_name}] Failed: {exc}")


def load_market_hours(con: duckdb.DuckDBPyConnection, data_root: Path) -> None:
    """Load market-hours/ JSON into market_hours table via pandas."""
    table_name = "market_hours"
    if _table_exists(con, table_name):
        log.info(f"[{table_name}] already exists — skipping")
        return

    json_path = data_root / "market-hours" / "market-hours-database.json"
    if not json_path.exists():
        log.warning(f"[{table_name}] {json_path} not found — skipping")
        return

    try:
        with open(json_path, "r") as f:
            raw = json.load(f)

        # Normalize — handle dict-of-dicts or list-of-dicts
        if isinstance(raw, dict):
            df = pd.json_normalize(
                [{"key": k, **v} if isinstance(v, dict) else {"key": k, "value": v}
                 for k, v in raw.items()]
            )
        elif isinstance(raw, list):
            df = pd.json_normalize(raw)
        else:
            log.warning(f"[{table_name}] Unexpected JSON structure — skipping")
            return

        con.execute(f'CREATE TABLE "{table_name}" AS SELECT * FROM df')
        log.info(f"[{table_name}] → {_row_count(con, table_name):,} rows")
    except Exception as exc:
        log.error(f"[{table_name}] Failed: {exc}")


def load_symbol_properties(con: duckdb.DuckDBPyConnection, data_root: Path) -> None:
    """Load symbol-properties/ CSV into symbol_properties table."""
    table_name = "symbol_properties"
    if _table_exists(con, table_name):
        log.info(f"[{table_name}] already exists — skipping")
        return

    csv_path = data_root / "symbol-properties" / "symbol-properties-database.csv"
    if not csv_path.exists():
        log.warning(f"[{table_name}] {csv_path} not found — skipping")
        return

    try:
        con.execute(f"""
            CREATE TABLE "{table_name}" AS
            SELECT * FROM read_csv_auto('{csv_path.as_posix()}')
        """)
        log.info(f"[{table_name}] → {_row_count(con, table_name):,} rows")
    except Exception as exc:
        log.error(f"[{table_name}] Failed: {exc}")


def load_nautilus_catalog(con: duckdb.DuckDBPyConnection, data_root: Path) -> None:
    """Create VIEWs over nautilus_catalog parquet files (do NOT materialize)."""
    catalog_dir = data_root / "nautilus_catalog"
    if not catalog_dir.exists():
        log.warning("nautilus_catalog/ directory not found — skipping")
        return

    views = {
        "nautilus_equity": "data/nautilus_catalog/data/equity/**/*.parquet",
        "nautilus_trade_tick": "data/nautilus_catalog/data/trade_tick/**/*.parquet",
    }

    for view_name, glob_pattern in views.items():
        if _view_exists(con, view_name):
            log.info(f"[{view_name}] VIEW already exists — skipping")
            continue

        full_glob = (data_root.parent / glob_pattern).as_posix()
        # Check if any files match
        matches = _safe_glob(data_root.parent, glob_pattern)
        if not matches:
            log.warning(f"[{view_name}] No files match {glob_pattern} — skipping")
            continue

        try:
            con.execute(f"""
                CREATE OR REPLACE VIEW "{view_name}" AS
                SELECT *, filename
                FROM read_parquet('{full_glob}', filename=true, union_by_name=true)
            """)
            log.warning(
                f"[{view_name}] Created as VIEW over live files — "
                "not a materialized table. Changes to underlying parquet files "
                "will be reflected in queries."
            )
        except Exception as exc:
            log.error(f"[{view_name}] Failed to create view: {exc}")


def load_trade_data(con: duckdb.DuckDBPyConnection, data_root: Path) -> None:
    """Load trade_data/ — legacy/unknown provenance."""
    td_dir = data_root / "trade_data"
    if not td_dir.exists():
        log.warning("trade_data/ directory not found — skipping")
        return

    log.warning(
        "[trade_data] ⚠ PROVENANCE UNKNOWN — review before using in production"
    )

    # Load top-level momentum_events_for_collection.parquet
    events_pq = td_dir / "momentum_events_for_collection.parquet"
    events_table = "trade_data_events"
    if events_pq.exists() and not _table_exists(con, events_table):
        try:
            con.execute(f"""
                CREATE TABLE "{events_table}" AS
                SELECT * FROM read_parquet('{events_pq.as_posix()}')
            """)
            log.info(f"[{events_table}] → {_row_count(con, events_table):,} rows")
        except Exception as exc:
            log.error(f"[{events_table}] Failed: {exc}")

    # Process each subfolder.
    # "batches", "by_date", "by_ticker", and "high_momentum" were removed
    # 2026-07-11: confirmed empty (0 parquet files) by direct inspection.
    # high_momentum was emptied by the trades-corpus cleanup earlier this
    # session (its unique/clean content now lives in filtered/); the other
    # three were already empty for unrelated, unknown reasons predating that
    # cleanup. "rebuild_validation_sample" exists with 58 parquet files (not
    # previously in this list) but was deliberately not added here — it
    # substantially overlaps data already loaded via load_filtered, and
    # whether staging/validation output belongs in a permanent trade_data_*
    # table is a judgment call left for explicit review rather than assumed.
    subfolders = ["enhanced"]
    skip_folders = ["logs", "metadata"]

    for sf in subfolders:
        sf_dir = td_dir / sf
        table_name = f"trade_data_{sf}"
        if _table_exists(con, table_name):
            log.info(f"[{table_name}] already exists — skipping")
            continue
        if not sf_dir.exists():
            log.info(f"[{table_name}] {sf}/ not found — skipping")
            continue

        parquets = _safe_glob(sf_dir, "**/*.parquet")
        if not parquets:
            log.info(f"[{table_name}] No parquet files in {sf}/ — skipping")
            continue

        log.info(f"[{table_name}] Loading {len(parquets)} files from {sf}/ ...")
        first = True
        loaded = 0
        for f in parquets:
            source_file = f.relative_to(td_dir).as_posix()
            try:
                q = f"""
                    SELECT *, '{source_file}' AS source_file
                    FROM read_parquet('{f.as_posix()}')
                """
                if first:
                    con.execute(f'CREATE TABLE "{table_name}" AS {q}')
                    first = False
                else:
                    con.execute(f'INSERT INTO "{table_name}" {q}')
                loaded += 1
            except Exception as exc:
                log.error(f"[{table_name}] Failed on {f}: {exc}")

        if not first:
            log.info(f"[{table_name}] → {_row_count(con, table_name):,} rows from {loaded} files")

    # Log skipped items for manual review
    for sf in skip_folders:
        sf_dir = td_dir / sf
        if sf_dir.exists():
            log.info(f"[trade_data] Skipped {sf}/ — flagged for manual review")

    # Log JSON progress files
    for jf in td_dir.glob("*_progress.json"):
        log.info(f"[trade_data] Skipped progress file: {jf.name} — flagged for manual review")


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

LOADERS: dict[str, Callable[[duckdb.DuckDBPyConnection, Path], None]] = {
    "filtered": load_filtered,
    "daily": load_daily,
    "minute": load_minute,
    "second10": load_second10,
    "quote_data": load_quote_data,
    "momentum_events": load_momentum_events,
    "metadata": load_metadata,
    "market_hours": load_market_hours,
    "symbol_properties": load_symbol_properties,
    "nautilus_catalog": load_nautilus_catalog,
    "trade_data": load_trade_data,
}

# ---------------------------------------------------------------------------
# Post-load verification
# ---------------------------------------------------------------------------

def verify(con: duckdb.DuckDBPyConnection) -> None:
    """Print table inventory and row counts."""
    print("\n" + "=" * 60)
    print("TABLE INVENTORY")
    print("=" * 60)

    try:
        tables_df = con.execute("""
            SELECT table_name, table_type
            FROM information_schema.tables
            WHERE table_schema = 'main'
            ORDER BY table_name
        """).df()
        print(tables_df.to_string(index=False))
    except Exception as exc:
        log.error(f"Failed to query table inventory: {exc}")

    print("\nROW COUNTS:")
    print("-" * 40)
    try:
        for row in con.execute("SHOW TABLES").fetchall():
            name = row[0]
            try:
                count = con.execute(f'SELECT COUNT(*) FROM "{name}"').fetchone()[0]
                print(f"  {name}: {count:,} rows")
            except Exception:
                print(f"  {name}: (error reading count)")
    except Exception as exc:
        log.error(f"Failed to enumerate tables: {exc}")

    # Also list views
    try:
        views = con.execute("""
            SELECT table_name FROM information_schema.tables
            WHERE table_schema = 'main' AND table_type = 'VIEW'
        """).fetchall()
        if views:
            print("\nVIEWS (live over parquet files):")
            print("-" * 40)
            for v in views:
                print(f"  {v[0]}")
    except Exception:
        pass

    print("=" * 60 + "\n")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest data into DuckDB")
    parser.add_argument(
        "--all", action="store_true", help="Load all datasets"
    )
    parser.add_argument(
        "--dataset",
        action="append",
        choices=list(LOADERS.keys()),
        help="Load specific dataset(s). Can be repeated.",
    )
    parser.add_argument(
        "--data-root",
        type=Path,
        default=DATA_ROOT,
        help=f"Root data directory (default: {DATA_ROOT})",
    )
    parser.add_argument(
        "--db-path",
        type=Path,
        default=None,
        help=(
            "DuckDB file path override. Uses src.data.db defaults when omitted "
            "(db_path arg -> MOM_DB_DUCKDB_PATH -> MOM_DB_DATABASE_ROOT/main.duckdb)."
        ),
    )
    parser.add_argument(
        "--verify-only",
        action="store_true",
        help="Only run post-load verification, do not ingest",
    )
    args = parser.parse_args()

    if not args.all and not args.dataset and not args.verify_only:
        parser.error("Specify --all, --dataset <name>, or --verify-only")

    con = get_connection(db_path=args.db_path)
    log.info(f"Connected to DuckDB at {con}")

    if args.verify_only:
        verify(con)
        con.close()
        return

    datasets = list(LOADERS.keys()) if args.all else (args.dataset or [])

    for ds in datasets:
        loader = LOADERS[ds]
        log.info(f"{'─' * 40}")
        log.info(f"Loading dataset: {ds}")
        log.info(f"{'─' * 40}")
        try:
            loader(con, args.data_root)
        except Exception as exc:
            log.error(f"FATAL error loading {ds}: {exc}", exc_info=True)
            # Continue with other datasets

    verify(con)
    con.close()
    log.info("Ingest complete.")


if __name__ == "__main__":
    main()
