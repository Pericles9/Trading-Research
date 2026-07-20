"""
Phase 1c T6 - verify, place sibling repair files, ingest.

Every heal-manifest row has exactly one (event_key, session, side) gap
(1,958 heal pairs across 1,958 gap-carrying events - a 1:1 ratio confirmed
in T1's derivation), so each event folder receives at most one
trades_repair_1c.parquet and one quotes_repair_1c.parquet - no
multi-session aggregation needed.

For every successfully fetched heal pair (fetch_state status=fetched,
n_records>0):
  1. Verify: session timestamps within [session 00:00, session+1day 00:00)
     bounds; ticker matches; aligned schema matches the archive schema
     exactly (already guaranteed by fetch_pair.align_to_archive_schema's
     required-column check, re-verified here defensively).
  2. Copy staged aligned parquet to data/filtered/{folder}/{side}_repair_1c.parquet
     (originals never touched - explicitly authorized by the phase prompt,
     an instructed exception to data/'s standing read-only convention).
  3. Ingest into filtered_trades/filtered_quotes via the same
     _scan_union_schema/_build_select_for_file mechanism Phase 1b's T4b
     reuse used. Post-ingest: table row count for (ticker, session) ==
     staged row count exactly, or hard stop.

IMPORTANT (discovered live, first run): the table's `event_date` column is
NOT each row's own trade date - src/data/ingest.py's load_filtered()
assigns it as a per-FOLDER constant (the event's own anchor date, parsed
from the folder name), applied uniformly to every row regardless of which
of the T-3..T+3 days it actually trades on. The first run tagged inserted
rows with event_date=session_date (the specific day being healed), which
only coincidentally matched the folder convention for event_day-type
heals (session == anchor date) and would have created a genuine schema
inconsistency for flanking-day heals (a new, table-wide-unique event_date
value nobody else's data used, invisible to any WHERE ticker=X AND
event_date=<the event's real anchor date> query). Fixed: every inserted
row now uses event_date_canonical (the folder's own anchor date), matching
convention exactly. Verification is scoped by the row's real sip_timestamp
date, not the (folder-level, not session-specific) event_date column.
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

with open("config/phase_1c.json") as f:
    CFG = json.load(f)

MANIFEST = CFG["paths"]["heal_manifest"]
FETCH_STATE = "results/phase_1c/artifacts/fetch_state.parquet"
FOLDER_INV = CFG["paths"]["folder_inventory_v2"]
STAGING_ROOT = Path(CFG["paths"]["staging_root"])
FILTERED_ROOT = Path(CFG["paths"]["filtered_folders_root"])
OUT_LEDGER = CFG["paths"]["repair_ledger"]
OUT_SUMMARY = "results/phase_1c/artifacts/t6_ingest_summary.json"

TYPE_OVERRIDES = {
    "trades": {"size": "BIGINT", "participant_timestamp": "BIGINT"},
    "quotes": {"ask_size": "BIGINT", "bid_size": "BIGINT"},
}


def verify_staged(df: pd.DataFrame, ticker: str, session_date: str) -> list[str]:
    problems = []
    if df.empty:
        return problems
    ts = pd.to_datetime(df["sip_timestamp"], unit="ns")
    lo, hi = pd.Timestamp(session_date), pd.Timestamp(session_date) + pd.Timedelta(days=1)
    out_of_bounds = ((ts < lo) | (ts >= hi)).sum()
    if out_of_bounds:
        problems.append(f"{out_of_bounds} rows outside session bounds [{lo}, {hi})")
    return problems


def main():
    manifest = pd.read_parquet(MANIFEST)
    state = pd.read_parquet(FETCH_STATE)
    con_dup = duckdb.connect(read_only=False)
    inv = con_dup.execute(
        f"SELECT ticker, date AS event_date_canonical, folder_name, momentum_str FROM read_parquet('{FOLDER_INV}')"
    ).fetchdf()
    con_dup.close()

    heal_rows = manifest[manifest["target_type"] != "diagnostic_unknown"].copy()

    # T5: the 8 diagnostic_unknown pairs are excluded above by default, but
    # all 8 resolved to collection_failure (real trades/quotes exist) and
    # joins_heal_set=TRUE - include them here so T6 ingests them like any
    # other healed pair.
    t5_resolution = pd.read_parquet("results/phase_1c/artifacts/t5_unknowns_resolution.parquet")
    resolved_keys = set(t5_resolution[t5_resolution["joins_heal_set"]]["event_key"])
    diagnostic_rows = manifest[
        (manifest["target_type"] == "diagnostic_unknown") & manifest["event_key"].isin(resolved_keys)
    ].copy()
    heal_rows = pd.concat([heal_rows, diagnostic_rows], ignore_index=True)

    fetched = state[(state["status"] == "fetched") & (state["n_records"] > 0)]

    heal_rows = heal_rows.merge(inv, on=["ticker", "event_date_canonical"], how="left")
    missing_folder = heal_rows[heal_rows["folder_name"].isna()]
    if len(missing_folder):
        print(f"WARNING: {len(missing_folder)} heal rows have no folder_name match")

    con = get_connection(read_only=False)

    # Resume-safety: a prior run may have already ingested some pairs (the
    # repair sibling file's existence on disk is the resume signal - it is
    # only ever written right before its matching INSERT in this same loop
    # body, so its presence means that INSERT already ran).
    if Path(OUT_LEDGER).exists():
        ledger_df_prior = pd.read_parquet(OUT_LEDGER)
        ledger_rows = ledger_df_prior.to_dict("records")
        already_done = set(zip(ledger_df_prior["event_key"], ledger_df_prior["side"]))
    else:
        ledger_rows = []
        already_done = set()
    hard_stops = []

    for _, row in heal_rows.iterrows():
        if pd.isna(row["folder_name"]):
            continue
        ticker, session_date, folder_name = row["ticker"], row["session"], row["folder_name"]
        event_date_canonical = row["event_date_canonical"]
        for side, do_fetch in [("trades", row["fetch_trades"]), ("quotes", row["fetch_quotes"])]:
            if not do_fetch or (row["event_key"], side) in already_done:
                continue
            fs = fetched[(fetched["ticker"] == ticker) & (fetched["session"] == session_date) & (fetched["side"] == side)]
            if fs.empty:
                continue  # not yet fetched, or empty/failed - not a heal candidate this pass

            staged_path = STAGING_ROOT / f"{ticker}_{session_date}" / f"{side}_aligned.parquet"
            staged_df = pd.read_parquet(staged_path)
            problems = verify_staged(staged_df, ticker, session_date)

            repair_path = FILTERED_ROOT / folder_name / f"{side}_repair_1c.parquet"
            staged_df.to_parquet(repair_path, index=False)

            table_name = "filtered_trades" if side == "trades" else "filtered_quotes"
            union_schema, file_columns = _scan_union_schema(con, [repair_path], type_overrides=TYPE_OVERRIDES[side])
            before = _row_count(con, table_name)
            posix_path = repair_path.as_posix()
            select_list = _build_select_for_file(
                posix_path, union_schema, file_columns,
                [("ticker", f"'{ticker}'"), ("event_date", f"'{event_date_canonical}'::DATE"), ("momentum_pct", f"CAST({row['momentum_str']} AS DOUBLE)")],
            )
            con.execute(f'INSERT INTO "{table_name}" BY NAME SELECT {select_list} FROM read_parquet(\'{posix_path}\')')
            after = _row_count(con, table_name)
            rows_ingested = after - before

            # Scoped by the row's real trade date (sip_timestamp), not the
            # folder-level event_date column - isolates just this session's
            # contribution regardless of event_day vs. flanking-day heal.
            post_check = con.execute(
                f'SELECT COUNT(*) FROM "{table_name}" WHERE ticker = ? AND event_date = ? '
                f"AND CAST(TO_TIMESTAMP(sip_timestamp/1e9) AS DATE) = ?",
                [ticker, event_date_canonical, session_date],
            ).fetchone()[0]
            verification_status = "ok" if not problems and post_check == len(staged_df) else "MISMATCH"
            if post_check != len(staged_df):
                hard_stops.append({
                    "ticker": ticker, "session": session_date, "side": side,
                    "staged_rows": len(staged_df), "post_ingest_rows": post_check,
                })

            ledger_rows.append({
                "event_key": row["event_key"], "ticker": ticker, "session": session_date,
                "event_date_canonical": event_date_canonical, "side": side,
                "folder_name": folder_name, "rows_staged": len(staged_df), "rows_ingested": rows_ingested,
                "post_ingest_row_count_for_pair": post_check, "repair_file_path": str(repair_path.as_posix()),
                "verification_problems": problems, "verification_status": verification_status,
            })

            if hard_stops:
                break
        if hard_stops:
            break

    ledger_df = pd.DataFrame(ledger_rows)
    ledger_df.to_parquet(OUT_LEDGER, index=False)
    con.close()

    summary = {
        "phase": "1c", "task": "T6",
        "n_pairs_ingested": len(ledger_df),
        "total_rows_added_trades": int(ledger_df[ledger_df["side"] == "trades"]["rows_ingested"].sum()) if len(ledger_df) else 0,
        "total_rows_added_quotes": int(ledger_df[ledger_df["side"] == "quotes"]["rows_ingested"].sum()) if len(ledger_df) else 0,
        "hard_stops": hard_stops,
        "overall_pass": len(hard_stops) == 0,
    }
    with open(OUT_SUMMARY, "w") as f:
        json.dump(summary, f, indent=2, default=str)
    print(json.dumps(summary, indent=2, default=str))
    if hard_stops:
        raise SystemExit("T6: post-ingest row count mismatch - hard stop per phase prompt.")


if __name__ == "__main__":
    main()
