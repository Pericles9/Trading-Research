"""
Phase 1c T3-R4 (Amendment 1) - formal control-fetch diff run.

Fetches trades (+quotes where coverage exists) for all 20 control pairs
via fetch_pair.py, staging only (never ingested). Diffs staged vs archive
per pair: row counts, matched-row price/size equality, condition-code and
venue-code value sets, and (Amendment 1) archive non-null count vs fetched
non-null count for every optional field.

Amended gate (T3-R2): a REQUIRED column missing from a vendor response
already hard-stops inside fetch_pair.align_to_archive_schema. Here, the
additional Amendment-1-specific gate is checked: any targeted pair where
an optional field was NULL-filled on alignment (absent from the vendor
response) despite the archive having non-null values for that exact
(ticker, session) - the conditional-emission hypothesis would be falsified.
"""
import json
import sys
import time
from pathlib import Path

import duckdb
import pandas as pd
import requests

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import fetch_pair as fp  # noqa: E402

with open("config/phase_1c.json") as f:
    CFG = json.load(f)

CONTROL_PAIRS = "results/phase_1c/artifacts/control_pairs.parquet"
OUT_DIFFS = CFG["paths"]["control_fetch_diffs"]
OUT_SUMMARY = "results/phase_1c/artifacts/t3r4_control_diff_summary.json"
DB_PATH = CFG["paths"]["momentum_events_db"]
THRESHOLDS = CFG["escalation_thresholds"]
OPTIONAL_TRADES = set(CFG["optional_fields"]["trades"])
OPTIONAL_QUOTES = set(CFG["optional_fields"]["quotes"])


def archive_rows(con, folder_name, session_date, side):
    parquet_name = "trades.parquet" if side == "trades" else "quotes.parquet"
    path = f"data/filtered/{folder_name}/{parquet_name}"
    return con.execute(
        f"SELECT * FROM read_parquet('{path}') "
        f"WHERE CAST(TO_TIMESTAMP(sip_timestamp/1e9) AS DATE) = DATE '{session_date}'"
    ).fetchdf()


def diff_side(archive_df: pd.DataFrame, staged_df: pd.DataFrame, side: str) -> dict:
    archive_n, staged_n = len(archive_df), len(staged_df)
    row_delta_pct = 100 * (staged_n - archive_n) / archive_n if archive_n else (0.0 if staged_n == 0 else float("inf"))

    key_cols = ["sip_timestamp", "sequence_number"]
    value_cols = ["price", "size"] if side == "trades" else ["bid_price", "bid_size", "ask_price", "ask_size"]
    value_cols = [c for c in value_cols if c in archive_df.columns and c in staged_df.columns]

    n_matched, n_mismatched = 0, 0
    if archive_n and staged_n and all(c in archive_df.columns for c in key_cols) and all(c in staged_df.columns for c in key_cols):
        merged = archive_df[key_cols + value_cols].merge(
            staged_df[key_cols + value_cols], on=key_cols, how="inner", suffixes=("_archive", "_staged")
        )
        n_matched = len(merged)
        mismatch_mask = pd.Series(False, index=merged.index)
        for c in value_cols:
            mismatch_mask = mismatch_mask | (merged[f"{c}_archive"] != merged[f"{c}_staged"])
        n_mismatched = int(mismatch_mask.sum())
    field_mismatch_pct = 100 * n_mismatched / n_matched if n_matched else 0.0

    def code_set(df, col):
        if col not in df.columns or df.empty:
            return set()
        exploded = df[col].explode().dropna()
        return set(exploded.tolist())

    venue_col = "exchange" if side == "trades" else "ask_exchange"
    archive_venues = set(archive_df[venue_col].dropna().tolist()) if venue_col in archive_df.columns else set()
    staged_venues = set(staged_df[venue_col].dropna().tolist()) if venue_col in staged_df.columns else set()
    archive_conditions = code_set(archive_df, "conditions")
    staged_conditions = code_set(staged_df, "conditions")

    optional_fields = OPTIONAL_TRADES if side == "trades" else OPTIONAL_QUOTES
    optional_nn = {}
    for f in optional_fields:
        archive_nn = int(archive_df[f].notna().sum()) if f in archive_df.columns else 0
        staged_nn = int(staged_df[f].notna().sum()) if f in staged_df.columns else 0
        optional_nn[f] = {"archive_non_null": archive_nn, "staged_non_null": staged_nn}

    return {
        "archive_n": archive_n, "staged_n": staged_n, "row_delta_pct": round(row_delta_pct, 4),
        "n_matched_rows": n_matched, "n_mismatched_rows": n_mismatched,
        "field_mismatch_pct": round(field_mismatch_pct, 4),
        "venue_codes_archive_only": sorted(archive_venues - staged_venues),
        "venue_codes_staged_only": sorted(staged_venues - archive_venues),
        "condition_codes_archive_only": sorted(archive_conditions - staged_conditions),
        "condition_codes_staged_only": sorted(staged_conditions - archive_conditions),
        "optional_field_non_null_counts": optional_nn,
    }


def main():
    pairs = pd.read_parquet(CONTROL_PAIRS)
    con = duckdb.connect(database=DB_PATH, read_only=True)
    con_staging = duckdb.connect(read_only=False)

    api_key = fp.load_api_key()
    session = requests.Session()

    rows = []
    hard_stop_reasons = []
    dropped_fields_seen = set()

    for _, pair in pairs.iterrows():
        ticker, session_date, folder_name = pair["ticker"], pair["event_date_canonical"], pair["folder_name"]
        sides = ["trades"] + (["quotes"] if pair["quotes_ingested"] else [])
        for side in sides:
            t0 = time.time()
            try:
                fetch_result = fp.fetch_and_stage(session, ticker, session_date, side, api_key)
            except fp.ArchiveSchemaViolation as e:
                hard_stop_reasons.append({"pair": f"{ticker}_{session_date}", "side": side, "reason": str(e)})
                continue
            dropped_fields_seen.update(fetch_result["dropped_vendor_fields"])

            arch_df = archive_rows(con, folder_name, session_date, side)
            staged_df = con_staging.execute(f"SELECT * FROM read_parquet('{fetch_result['aligned_path']}')").fetchdf()
            diff = diff_side(arch_df, staged_df, side)
            diff.update({
                "ticker": ticker, "session": session_date, "folder_name": folder_name, "side": side,
                "pool": pair["pool"], "targeted_optional_field": pair["targeted_optional_field"],
                "optional_fields_null_filled": fetch_result["optional_fields_null_filled"],
                "fetch_seconds": round(time.time() - t0, 2),
            })

            # Amendment-1 gate: optional field null-filled but archive has non-null values for this pair
            for f in fetch_result["optional_fields_null_filled"]:
                if diff["optional_field_non_null_counts"].get(f, {}).get("archive_non_null", 0) > 0:
                    hard_stop_reasons.append({
                        "pair": f"{ticker}_{session_date}", "side": side, "field": f,
                        "reason": f"optional field '{f}' NULL-filled (absent from vendor response) but archive has "
                                  f"{diff['optional_field_non_null_counts'][f]['archive_non_null']} non-null rows for this pair - conditional-emission hypothesis falsified",
                    })

            rows.append(diff)
            print(f"{ticker} {session_date} {side}: archive_n={diff['archive_n']} staged_n={diff['staged_n']} "
                  f"delta%={diff['row_delta_pct']} field_mismatch%={diff['field_mismatch_pct']}")

    con.close()
    diffs_df = pd.DataFrame(rows)
    diffs_df.to_parquet(OUT_DIFFS, index=False)

    # Gate checks (T3b, unchanged thresholds; plus Amendment-1 conditional-emission gate above)
    gate_violations = diffs_df[
        (diffs_df["row_delta_pct"].abs() > THRESHOLDS["control_fetch_row_delta_pct_max"])
        | (diffs_df["field_mismatch_pct"] > THRESHOLDS["control_fetch_field_mismatch_pct_max"])
        | (diffs_df["venue_codes_archive_only"].apply(len) > 0)
        | (diffs_df["condition_codes_archive_only"].apply(len) > 0)
    ] if not diffs_df.empty else diffs_df

    overall_pass = len(hard_stop_reasons) == 0 and len(gate_violations) == 0

    summary = {
        "phase": "1c", "task": "T3-R4",
        "n_pairs": len(pairs), "n_side_fetches": len(diffs_df),
        "dropped_vendor_fields_enumerated": sorted(dropped_fields_seen),
        "hard_stop_reasons": hard_stop_reasons,
        "gate_violations": gate_violations.to_dict("records") if len(gate_violations) else [],
        "overall_pass": overall_pass,
        "thresholds": THRESHOLDS,
    }
    with open(OUT_SUMMARY, "w") as f:
        json.dump(summary, f, indent=2, default=str)
    print(json.dumps({k: v for k, v in summary.items() if k != "gate_violations"}, indent=2, default=str))

    if not overall_pass:
        raise SystemExit("T3-R4 control diff FAILED gate - see summary. Hard stop per phase prompt.")


if __name__ == "__main__":
    main()
