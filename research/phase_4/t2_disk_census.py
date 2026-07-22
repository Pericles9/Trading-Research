"""
Phase 4 T2 - filesystem census of filtered/.

One pass over every event folder under the data root's filtered/ dir.
Deliberately NOT spine-joined (the one exception per the phase's Context
section) - this must also count out-of-universe folders (including the
"None"-date orphan folders and non-common-instrument tickers CLAUDE.md's
universe rules describe) to locate the gap relative to the universe.

Readability = parquet footer opens and row count returns; per T2's
instruction this does NOT scan full contents. row_count comes from
DuckDB's parquet_file_metadata() (footer-level file metadata, no data
page reads). min/max session date comes from parquet_metadata()'s
row-group-level column statistics for sip_timestamp (also footer-level -
every parquet writer used here embedded min/max stats per row group,
verified on a sample folder) - not a data scan. Session date convention
matches Phase 2/3 (CAST(TO_TIMESTAMP(sip_timestamp/1e9) AS DATE), i.e.
UTC date of the nanosecond epoch timestamp).

Both metadata calls run batched (one SQL call per chunk of files) for
speed; a chunk that raises an exception falls back to a per-file loop so
a single corrupt/unreadable file cannot silently swallow its whole
batch - required for T2b's exhaustive unreadable/zero-row listing and
escalation row 3.
"""
import json
import os
import re
from datetime import datetime, timezone

import duckdb
import pandas as pd

DATA_ROOT = "E:/Trading Research/data"
FILTERED_DIR = f"{DATA_ROOT}/filtered"
PHASE_4_CONFIG = "config/phase_4.json"
OUT_PARQUET = "results/phase_4/artifacts/disk_census.parquet"
OUT_SUMMARY = "results/phase_4/artifacts/census_summary.json"

FOLDER_RE = re.compile(r"^(?P<ticker>.+)_(?P<date>\d{4}-\d{2}-\d{2}|None)_(?P<mom>[\d.\-]+)$")
CHUNK_SIZE = 2000


def list_folders():
    entries = os.scandir(FILTERED_DIR)
    folders, non_folder_files = [], []
    for e in entries:
        if e.is_dir():
            folders.append(e.name)
        else:
            non_folder_files.append(e.name)
    return sorted(folders), sorted(non_folder_files)


def parse_folder(name):
    m = FOLDER_RE.match(name)
    if not m:
        return {"ticker": None, "date_raw": None, "momentum_raw": None, "parse_ok": False}
    d = m.group("date")
    return {
        "ticker": m.group("ticker"),
        "date_raw": d,
        "date_parsed": None if d == "None" else d,
        "momentum_raw": m.group("mom"),
        "momentum_pct": float(m.group("mom")) if m.group("mom") not in (None, "") else None,
        "parse_ok": True,
    }


def batched_file_metadata(con, files):
    """Returns dict: file -> {'readable': bool, 'row_count': int|None, 'error': str|None}"""
    out = {}
    for i in range(0, len(files), CHUNK_SIZE):
        chunk = files[i:i + CHUNK_SIZE]
        try:
            df = con.execute(
                "SELECT file_name, num_rows FROM parquet_file_metadata(?)", [chunk]
            ).fetchdf()
            found = set(df["file_name"])
            for f in chunk:
                if f in found:
                    row = df[df["file_name"] == f].iloc[0]
                    out[f] = {"readable": True, "row_count": int(row["num_rows"]), "error": None}
                else:
                    out[f] = {"readable": False, "row_count": None, "error": "not_returned_by_batch"}
        except Exception:
            # fall back to per-file so one corrupt file doesn't swallow the whole chunk
            for f in chunk:
                try:
                    r = con.execute(
                        "SELECT num_rows FROM parquet_file_metadata(?)", [[f]]
                    ).fetchdf()
                    out[f] = {"readable": True, "row_count": int(r.iloc[0]["num_rows"]), "error": None}
                except Exception as e2:
                    out[f] = {"readable": False, "row_count": None, "error": str(e2)}
    return out


def batched_session_range(con, files):
    """Returns dict: file -> {'min_date': date|None, 'max_date': date|None}"""
    out = {}
    for i in range(0, len(files), CHUNK_SIZE):
        chunk = files[i:i + CHUNK_SIZE]
        try:
            df = con.execute(
                """
                SELECT file_name, MIN(TRY_CAST(stats_min_value AS BIGINT)) AS min_ns,
                       MAX(TRY_CAST(stats_max_value AS BIGINT)) AS max_ns
                FROM parquet_metadata(?)
                WHERE path_in_schema = 'sip_timestamp'
                GROUP BY file_name
                """,
                [chunk],
            ).fetchdf()
            for _, row in df.iterrows():
                out[row["file_name"]] = {"min_ns": row["min_ns"], "max_ns": row["max_ns"]}
        except Exception:
            for f in chunk:
                try:
                    r = con.execute(
                        """
                        SELECT MIN(TRY_CAST(stats_min_value AS BIGINT)) AS min_ns,
                               MAX(TRY_CAST(stats_max_value AS BIGINT)) AS max_ns
                        FROM parquet_metadata(?)
                        WHERE path_in_schema = 'sip_timestamp'
                        """,
                        [[f]],
                    ).fetchdf()
                    out[f] = {"min_ns": r.iloc[0]["min_ns"], "max_ns": r.iloc[0]["max_ns"]}
                except Exception:
                    out[f] = {"min_ns": None, "max_ns": None}
    return out


def ns_to_date(ns):
    if ns is None or pd.isna(ns):
        return None
    return datetime.fromtimestamp(int(ns) // 1_000_000_000, tz=timezone.utc).date()


def main():
    with open(PHASE_4_CONFIG) as f:
        cfg = json.load(f)

    print("listing folders under", FILTERED_DIR)
    folders, non_folder_files = list_folders()
    print(f"{len(folders)} event folders, {len(non_folder_files)} non-folder top-level files")

    trades_files, quotes_files = [], []
    rows = []
    for name in folders:
        parsed = parse_folder(name)
        tpath = f"{FILTERED_DIR}/{name}/trades.parquet"
        qpath = f"{FILTERED_DIR}/{name}/quotes.parquet"
        t_present = os.path.exists(tpath)
        q_present = os.path.exists(qpath)
        if t_present:
            trades_files.append(tpath)
        if q_present:
            quotes_files.append(qpath)
        rows.append({
            "folder_name": name, **parsed,
            "trades_path": tpath, "trades_present": t_present,
            "quotes_path": qpath, "quotes_present": q_present,
        })

    df = pd.DataFrame(rows)
    print(f"trades.parquet present: {df['trades_present'].sum()}; quotes.parquet present: {df['quotes_present'].sum()}")

    con = duckdb.connect()

    print("batched file metadata (row counts, readability)...")
    t_meta = batched_file_metadata(con, trades_files)
    q_meta = batched_file_metadata(con, quotes_files)

    print("batched row-group session-range stats...")
    t_range = batched_session_range(con, trades_files)
    q_range = batched_session_range(con, quotes_files)
    con.close()

    def fill(row, side, meta, rng):
        path = row[f"{side}_path"]
        present = row[f"{side}_present"]
        if not present:
            row[f"{side}_readable"] = None
            row[f"{side}_row_count"] = None
            row[f"{side}_min_date"] = None
            row[f"{side}_max_date"] = None
            row[f"{side}_error"] = None
            return row
        m = meta.get(path, {"readable": False, "row_count": None, "error": "missing_from_metadata_pass"})
        row[f"{side}_readable"] = m["readable"]
        row[f"{side}_row_count"] = m["row_count"]
        row[f"{side}_error"] = m["error"]
        r = rng.get(path, {"min_ns": None, "max_ns": None})
        row[f"{side}_min_date"] = ns_to_date(r["min_ns"])
        row[f"{side}_max_date"] = ns_to_date(r["max_ns"])
        return row

    df = df.apply(lambda row: fill(row, "trades", t_meta, t_range), axis=1)
    df = df.apply(lambda row: fill(row, "quotes", q_meta, q_range), axis=1)

    def presence_class(row):
        if row["trades_present"] and row["quotes_present"]:
            return "both"
        if row["trades_present"] and not row["quotes_present"]:
            return "trades_only"
        if row["quotes_present"] and not row["trades_present"]:
            return "quotes_only"
        return "neither"

    df["presence_class"] = df.apply(presence_class, axis=1)

    df.to_parquet(OUT_PARQUET, index=False)

    presence_counts = df["presence_class"].value_counts().to_dict()

    unreadable_or_zero = []
    for _, row in df.iterrows():
        for side in ("trades", "quotes"):
            if row[f"{side}_present"]:
                if row[f"{side}_readable"] is False:
                    unreadable_or_zero.append({
                        "folder": row["folder_name"], "side": side, "issue": "unreadable",
                        "error": row[f"{side}_error"],
                    })
                elif row[f"{side}_readable"] is True and (row[f"{side}_row_count"] == 0):
                    unreadable_or_zero.append({
                        "folder": row["folder_name"], "side": side, "issue": "zero_row",
                        "error": None,
                    })

    quotes_unreadable_or_zero = [u for u in unreadable_or_zero if u["side"] == "quotes"]

    hist = cfg["historical_reference"]
    current_trades_files = int(df["trades_present"].sum())
    current_quotes_files = int(df["quotes_present"].sum())

    summary = {
        "phase": "4", "task": "T2",
        "note": "Deliberately NOT spine-joined - counts all folders on disk including out-of-universe (e.g. 'None'-date orphan folders, non-common-instrument tickers).",
        "n_event_folders": len(folders),
        "non_folder_top_level_files": non_folder_files,
        "presence_class_counts": {str(k): int(v) for k, v in presence_counts.items()},
        "unparsed_folder_names": df.loc[~df["parse_ok"], "folder_name"].tolist(),
        "historical_reference_comparison": {
            "source": hist["source"], "snapshot_date": hist["snapshot_date"],
            "historical_trades_files": hist["trades_files"], "current_trades_files": current_trades_files,
            "trades_drift": current_trades_files - hist["trades_files"],
            "historical_quotes_files": hist["quotes_files"], "current_quotes_files": current_quotes_files,
            "quotes_drift": current_quotes_files - hist["quotes_files"],
            "note": "Historical reference is pre-Phase-1c re-collection, treated as informational only per config/phase_4.json - drift described, not attributed.",
        },
        "unreadable_or_zero_row_count": len(unreadable_or_zero),
        "unreadable_or_zero_row_files": unreadable_or_zero,
        "quotes_unreadable_or_zero_row_count": len(quotes_unreadable_or_zero),
        "escalation_check_row3": {
            "condition": "present-but-unreadable or zero-row quotes.parquet",
            "threshold": "0",
            "observed": len(quotes_unreadable_or_zero),
            "triggered": len(quotes_unreadable_or_zero) >= 1,
        },
        "source": "research/phase_4/t2_disk_census.py:main",
        "artifact": OUT_PARQUET,
    }
    with open(OUT_SUMMARY, "w") as f:
        json.dump(summary, f, indent=2, default=str)
    print(json.dumps({k: v for k, v in summary.items() if k not in ("unreadable_or_zero_row_files",)}, indent=2, default=str))
    print(f"unreadable_or_zero_row_files: {len(unreadable_or_zero)} entries (see {OUT_SUMMARY})")

    if summary["escalation_check_row3"]["triggered"]:
        print("\n*** ESCALATION row 3: unreadable/zero-row quotes.parquet found - see census_summary.json ***")


if __name__ == "__main__":
    main()
