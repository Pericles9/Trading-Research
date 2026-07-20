"""
Phase 1c T6-R2 (Amendment 2) - SDOT remediation.

SDOT_2025-10-15_150.87's 2025-10-13 quotes heal collided with 1,603
pre-existing archive rows; the original (pre-guard) insert added 1,604
more on top, producing 3,207 combined rows of ambiguous/possibly-
overlapping origin.

Rather than attempting to identify and remove exactly the 1,604 inserted
rows (ambiguous if any fetched row happens to share sip_timestamp+
sequence_number with a pre-existing one), this deletes the full combined
session and re-derives the correct state directly from the untouched
original data/filtered/SDOT_2025-10-15_150.87/quotes.parquet file - a
robust guarantee of the exact target state (1,603 rows) regardless of any
overlap ambiguity, using the same _scan_union_schema/_build_select_for_file
mechanism as every other ingest in this phase.
"""
import json
import sys
from pathlib import Path

import duckdb
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from src.data.db import get_connection  # noqa: E402
from src.data.ingest import _build_select_for_file, _row_count, _scan_union_schema  # noqa: E402

FOLDER = "SDOT_2025-10-15_150.87"
ORIGINAL_FILE = Path(f"data/filtered/{FOLDER}/quotes.parquet")
REPAIR_FILE = Path(f"data/filtered/{FOLDER}/quotes_repair_1c.parquet")
TICKER = "SDOT"
EVENT_DATE_CANONICAL = "2025-10-15"
SESSION_DATE = "2025-10-13"
MOMENTUM_STR = "150.87"
OUT_SUMMARY = "results/phase_1c/artifacts/t6r2_sdot_remediation.json"

TYPE_OVERRIDES = {"ask_size": "BIGINT", "bid_size": "BIGINT"}


def main():
    con = get_connection(read_only=False)

    baseline_all = con.execute("SELECT COUNT(*) FROM filtered_quotes WHERE ticker = ?", [TICKER]).fetchone()[0]
    baseline_other_sessions = con.execute(
        "SELECT event_date, CAST(TO_TIMESTAMP(sip_timestamp/1e9) AS DATE) AS real_date, COUNT(*) AS n "
        "FROM filtered_quotes WHERE ticker = ? AND NOT (event_date = ? AND CAST(TO_TIMESTAMP(sip_timestamp/1e9) AS DATE) = ?) "
        "GROUP BY 1, 2 ORDER BY 1, 2",
        [TICKER, EVENT_DATE_CANONICAL, SESSION_DATE],
    ).fetchdf()

    before_target = con.execute(
        "SELECT COUNT(*) FROM filtered_quotes WHERE ticker = ? AND event_date = ? "
        "AND CAST(TO_TIMESTAMP(sip_timestamp/1e9) AS DATE) = ?",
        [TICKER, EVENT_DATE_CANONICAL, SESSION_DATE],
    ).fetchone()[0]

    con.execute(
        "DELETE FROM filtered_quotes WHERE ticker = ? AND event_date = ? "
        "AND CAST(TO_TIMESTAMP(sip_timestamp/1e9) AS DATE) = ?",
        [TICKER, EVENT_DATE_CANONICAL, SESSION_DATE],
    )
    after_delete = con.execute(
        "SELECT COUNT(*) FROM filtered_quotes WHERE ticker = ? AND event_date = ? "
        "AND CAST(TO_TIMESTAMP(sip_timestamp/1e9) AS DATE) = ?",
        [TICKER, EVENT_DATE_CANONICAL, SESSION_DATE],
    ).fetchone()[0]

    # Re-derive directly from the untouched original archive file, filtered
    # to just this session's real trade date - the authoritative pre-heal
    # source, sourced fresh rather than trusting any intermediate copy.
    orig_session_df = con.execute(
        f"SELECT * FROM read_parquet('{ORIGINAL_FILE.as_posix()}') "
        f"WHERE CAST(TO_TIMESTAMP(sip_timestamp/1e9) AS DATE) = DATE '{SESSION_DATE}'"
    ).fetchdf()
    restore_path = Path(f"data/filtered/{FOLDER}/_sdot_2025-10-13_restore_temp.parquet")
    orig_session_df.to_parquet(restore_path, index=False)

    union_schema, file_columns = _scan_union_schema(con, [restore_path], type_overrides=TYPE_OVERRIDES)
    select_list = _build_select_for_file(
        restore_path.as_posix(), union_schema, file_columns,
        [("ticker", f"'{TICKER}'"), ("event_date", f"'{EVENT_DATE_CANONICAL}'::DATE"), ("momentum_pct", f"CAST({MOMENTUM_STR} AS DOUBLE)")],
    )
    con.execute(f'INSERT INTO "filtered_quotes" BY NAME SELECT {select_list} FROM read_parquet(\'{restore_path.as_posix()}\')')
    restore_path.unlink()

    after_restore = con.execute(
        "SELECT COUNT(*) FROM filtered_quotes WHERE ticker = ? AND event_date = ? "
        "AND CAST(TO_TIMESTAMP(sip_timestamp/1e9) AS DATE) = ?",
        [TICKER, EVENT_DATE_CANONICAL, SESSION_DATE],
    ).fetchone()[0]

    after_all = con.execute("SELECT COUNT(*) FROM filtered_quotes WHERE ticker = ?", [TICKER]).fetchone()[0]
    after_other_sessions = con.execute(
        "SELECT event_date, CAST(TO_TIMESTAMP(sip_timestamp/1e9) AS DATE) AS real_date, COUNT(*) AS n "
        "FROM filtered_quotes WHERE ticker = ? AND NOT (event_date = ? AND CAST(TO_TIMESTAMP(sip_timestamp/1e9) AS DATE) = ?) "
        "GROUP BY 1, 2 ORDER BY 1, 2",
        [TICKER, EVENT_DATE_CANONICAL, SESSION_DATE],
    ).fetchdf()
    con.close()

    other_sessions_match = baseline_other_sessions.equals(after_other_sessions)
    expected_n = 1603
    target_correct = after_restore == expected_n
    total_correct = after_all == baseline_all - before_target + after_restore

    # Delete the (now-invalid) quotes repair sibling - trades sibling stays,
    # SDOT's trades gap is real and heals normally in T6-R3.
    repair_removed = False
    if REPAIR_FILE.exists():
        REPAIR_FILE.unlink()
        repair_removed = True

    # Patch the ledger: remove the bad SDOT quotes row, mark skipped_collision.
    # Backfill collision_status/preexisting_rows on pre-Amendment-2 rows
    # (all healed, since the guard didn't exist yet for them) for schema
    # consistency across the full ledger.
    ledger = pd.read_parquet("results/phase_1c/artifacts/repair_ledger.parquet")
    if "collision_status" not in ledger.columns:
        ledger["collision_status"] = "healed"
        ledger["preexisting_rows"] = 0
    ledger = ledger[~((ledger["ticker"] == TICKER) & (ledger["session"] == SESSION_DATE) & (ledger["side"] == "quotes"))]
    new_row = pd.DataFrame([{
        "event_key": "SDOT_2025-10-15", "ticker": TICKER, "session": SESSION_DATE,
        "event_date_canonical": EVENT_DATE_CANONICAL, "side": "quotes", "folder_name": FOLDER,
        "rows_staged": 0, "rows_ingested": 0, "post_ingest_row_count_for_pair": after_restore,
        "repair_file_path": None, "verification_problems": [], "verification_status": "skipped_collision",
        "collision_status": "skipped_collision", "preexisting_rows": expected_n,
    }])
    ledger = pd.concat([ledger, new_row], ignore_index=True)
    ledger.to_parquet("results/phase_1c/artifacts/repair_ledger.parquet", index=False)

    summary = {
        "phase": "1c", "task": "T6-R2",
        "before_target_session_count": before_target,
        "after_delete_count": after_delete,
        "after_restore_count": after_restore,
        "expected_count": expected_n,
        "target_correct": target_correct,
        "baseline_total_sdot_quotes": baseline_all,
        "after_total_sdot_quotes": after_all,
        "total_correct": total_correct,
        "other_sessions_unchanged": other_sessions_match,
        "repair_sibling_removed": repair_removed,
        "overall_pass": target_correct and total_correct and other_sessions_match,
    }
    with open(OUT_SUMMARY, "w") as f:
        json.dump(summary, f, indent=2, default=str)
    print(json.dumps(summary, indent=2, default=str))
    if not summary["overall_pass"]:
        raise SystemExit("T6-R2a: SDOT remediation verification FAILED - hard stop per amendment.")


if __name__ == "__main__":
    main()
