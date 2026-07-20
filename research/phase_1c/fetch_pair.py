"""
Phase 1c T2 - fetch + schema-alignment primitives for one (ticker, session,
side) pair. Vendor endpoint/param shape confirmed from
results/rebuild_stage1/collect_massive_data_v2.py (T2-fixed trades
collector - read for reference only, never executed) and
data/collection_scripts/collect_massive_data.py (read-only reference for
the quotes-endpoint symmetry). Both source files are quarantined
(D:\\ hardcodes / legacy collector) and are never imported or executed by
this module - only their endpoint/param shape is replicated.

Writes staged output under results/phase_1c/staging/{TICKER}_{SESSION}/:
  {side}_raw.parquet      - full, unmodified vendor response (no column
                             selection, matching collect_massive_data_v2's
                             explicit "no column selection" design)
  {side}_aligned.parquet  - cast to the archive's file-level schema
                             (config/phase_1c.json archive_schema), ready
                             to serve as a trades_repair_1c.parquet /
                             quotes_repair_1c.parquet sibling in T6

This module performs no network calls at import time and is safe to import
for the escalation-threshold logic alone.
"""
import json
import os
import time
from pathlib import Path

import pandas as pd
import requests

with open("config/phase_1c.json") as f:
    CFG = json.load(f)

API = CFG["vendor_api"]
FETCH_CFG = CFG["fetch"]
ARCHIVE_SCHEMA = CFG["archive_schema"]
STAGING_ROOT = Path(CFG["paths"]["staging_root"])

_DUCKDB_TO_PANDAS = {
    "BIGINT": "Int64", "DOUBLE": "float64", "VARCHAR": "object", "BIGINT[]": "object",
}


class AuthError(Exception):
    pass


class ArchiveSchemaViolation(Exception):
    """Raised when an archive column is absent from every record of a vendor response - T2/T3 hard-stop criterion."""


def load_api_key() -> str:
    env = os.environ.get(API["api_key_env_var"])
    if env:
        return env.strip()
    with open(API["api_key_path"]) as f:
        return f.read().strip()


_last_request_time = [0.0]


def _rate_limit():
    cap = FETCH_CFG["requests_per_second_cap"]
    min_interval = 1.0 / cap if cap > 0 else 0
    elapsed = time.time() - _last_request_time[0]
    if elapsed < min_interval:
        time.sleep(min_interval - elapsed)
    _last_request_time[0] = time.time()


def fetch_all_pages(session: requests.Session, url: str, params: dict, api_key: str, context: str) -> list[dict]:
    """Paginate a vendor endpoint to completion. Mirrors the validated retry
    shape of results/rebuild_stage1/collect_massive_data_v2.py's
    fetch_all_pages (read for reference, not executed): 429/5xx retried with
    exponential backoff, any other non-200 or exhausted retries raises
    rather than silently returning a partial list."""
    results: list[dict] = []
    current_url = url
    current_params = params.copy()
    max_retries = FETCH_CFG["max_retries"]

    while True:
        attempt = 0
        page_ok = False
        while attempt < max_retries:
            _rate_limit()
            try:
                if current_url == url:
                    resp = session.get(current_url, params=current_params, timeout=FETCH_CFG["request_timeout_seconds"])
                else:
                    if "apiKey=" not in current_url:
                        sep = "&" if "?" in current_url else "?"
                        current_url = f"{current_url}{sep}apiKey={api_key}"
                    resp = session.get(current_url, timeout=FETCH_CFG["request_timeout_seconds"])

                if resp.status_code == 401:
                    raise AuthError(f"[{context}] 401 from vendor API - hard stop, no retry.")
                if resp.status_code == 429:
                    retry_after = resp.headers.get("Retry-After")
                    wait = float(retry_after) if retry_after else FETCH_CFG["backoff_base_seconds"] ** attempt
                    attempt += 1
                    time.sleep(wait)
                    continue
                if resp.status_code != 200:
                    attempt += 1
                    time.sleep(FETCH_CFG["backoff_base_seconds"] ** attempt)
                    continue

                data = resp.json()
                results.extend(data.get("results", []))
                next_url = data.get("next_url")
                if not next_url:
                    return results
                current_url = next_url
                current_params = {}
                page_ok = True
                break
            except AuthError:
                raise
            except requests.exceptions.RequestException:
                attempt += 1
                time.sleep(FETCH_CFG["backoff_base_seconds"] ** attempt)

        if not page_ok:
            raise RuntimeError(f"[{context}] failed after {max_retries} retries; {len(results)} records collected so far")


def fetch_side(session: requests.Session, ticker: str, session_date: str, side: str, api_key: str) -> list[dict]:
    endpoint = API["trades_endpoint"] if side == "trades" else API["quotes_endpoint"]
    url = f"{API['base_url']}{endpoint.format(ticker=ticker)}"
    params = {**API["params_template"], "timestamp": session_date, "apiKey": api_key}
    return fetch_all_pages(session, url, params, api_key, context=f"{ticker} {session_date} {side}")


def align_to_archive_schema(records: list[dict], side: str) -> tuple[pd.DataFrame, list[str], list[str]]:
    """Cast the raw vendor records to the archive's file-level column set.

    Amendment 1 (T3-R2): archive columns split into required vs optional
    (config's optional_fields, derived in T3-R1 from archive evidence -
    non-null rate < 1% AND demonstrably absent from some archive files'
    own schema, e.g. correction). A REQUIRED column absent from the vendor
    response still raises ArchiveSchemaViolation (hard stop, unchanged). An
    OPTIONAL column absent is NULL-filled here; whether that NULL-fill was
    legitimate for a given (ticker, session) - i.e. the archive's own rows
    for that exact pair are also all-null in that field - is verified
    against archive ground truth by the caller (only meaningful where
    archive data exists to compare against, i.e. control fetches; heal
    fetches have no prior archive row for that pair by construction).

    Returns (aligned_df, dropped_vendor_fields, optional_fields_null_filled).
    """
    archive_cols = ARCHIVE_SCHEMA[f"{side}_columns"]
    optional_cols = set(CFG["optional_fields"][side])
    required_cols = [c for c in archive_cols if c not in optional_cols]

    if not records:
        return pd.DataFrame(columns=archive_cols), [], []

    df = pd.DataFrame(records)
    vendor_cols = set(df.columns)
    missing_required = [c for c in required_cols if c not in vendor_cols]
    if missing_required:
        raise ArchiveSchemaViolation(
            f"Required archive column(s) {missing_required} absent from vendor {side} response "
            f"(vendor returned: {sorted(vendor_cols)})"
        )
    missing_optional = [c for c in archive_cols if c in optional_cols and c not in vendor_cols]
    for c in missing_optional:
        df[c] = None

    dropped = sorted(vendor_cols - set(archive_cols))
    aligned = df[archive_cols].copy()
    return aligned, dropped, missing_optional


def stage_pair(ticker: str, session: str, side: str, records: list[dict]) -> dict:
    """Writes raw + aligned parquet for one (ticker, session, side). Returns
    a small result dict for the caller's ledger/manifest bookkeeping."""
    folder = STAGING_ROOT / f"{ticker}_{session}"
    folder.mkdir(parents=True, exist_ok=True)

    raw_df = pd.DataFrame(records)
    raw_df.to_parquet(folder / f"{side}_raw.parquet", index=False)

    aligned_df, dropped_fields, optional_fields_null_filled = align_to_archive_schema(records, side)
    aligned_df.to_parquet(folder / f"{side}_aligned.parquet", index=False)

    return {
        "ticker": ticker, "session": session, "side": side,
        "n_records": len(records), "dropped_vendor_fields": dropped_fields,
        "optional_fields_null_filled": optional_fields_null_filled,
        "aligned_path": str((folder / f"{side}_aligned.parquet").as_posix()),
        "raw_path": str((folder / f"{side}_raw.parquet").as_posix()),
    }


def fetch_and_stage(session: requests.Session, ticker: str, session_date: str, side: str, api_key: str) -> dict:
    records = fetch_side(session, ticker, session_date, side, api_key)
    result = stage_pair(ticker, session_date, side, records)
    result["status"] = "empty" if len(records) == 0 else "fetched"
    return result
