"""
Build F1, F1-T2: Massive bulk pull. Network step -- writes the raw archive, then stops.
Everything after this task is offline. Authorized by docs/Universe-Decisions.md D14
Amendment A1.

Pulls by Central Index Key wherever the endpoint actually supports it, not wherever the
work order assumed it would. Checked directly before building this: /vX/reference/financials
and /v3/reference/tickers both filter correctly on cik= (confirmed: requesting Apple's CIK
returns Apple's own data back). /stocks/v1/short-interest, /stocks/v1/short-volume,
/stocks/vX/float, and /v3/reference/splits do NOT -- passing cik= to any of them silently
returns an arbitrary, unfiltered result (ticker "A", "DPU", "GECCG" were all observed for
the *same* requested CIK across repeated tests), with no error of any kind. This is a worse
failure mode than simply not supporting the parameter, because a script that trusted it
would have archived confidently wrong data with no signal anything was off. Those five
endpoints are pulled by ticker instead, using the ticker string F1-T1 already verified for
each CIK -- not a raw event ticker, so identity resolution is still respected, just not via
a cik= parameter these endpoints don't actually honor.

"ratios" is named in the work order as its own pull target (grouped with "Financials and
Ratios" as a subscription-tier name) but no separate endpoint for it could be found: every
plausible path (/vX/reference/financials/ratios, /v1/reference/financials/ratios,
/stocks/vX/ratios, /vX/reference/fundamentals/ratios) returns 404. Not guessed further, not
substituted, not scraped, per F1-T2a's own instruction -- recorded as not_found in the
manifest and left for Cooper's attention rather than silently dropped or invented.

Endpoint map actually used:
  financials      cik=     /vX/reference/financials              (bundles income statement,
                                                                    balance sheet, cash flow
                                                                    statement, comprehensive
                                                                    income in one response)
  ticker_details  cik=     /v3/reference/tickers
  ticker_events   ticker   /vX/reference/tickers/{ticker}/events  (path-based, no cik variant)
  splits          ticker   /v3/reference/splits
  dividends       ticker   /v3/reference/dividends
  short_interest  ticker   /stocks/v1/short-interest
  short_volume    ticker   /stocks/v1/short-volume
  float           ticker   /stocks/vX/float                       (archive only -- D27)
  ratios          --       NOT FOUND, see above

Provenance (Amendment F1-A1 SS4): the financials fetch manifest records
source_of_record=false for the vendor's income statement/balance sheet/cash flow data --
archived as the companyfacts cross-check harness per F1-T0f/g, and per F1-T0f's Outcome A
may also populate fin_ directly downstream (fin_source=vendor_archive).

Usage: .venv/Scripts/python.exe research/fundamentals_f1/t2_massive_pull.py
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import time
from datetime import datetime, timezone

import pandas as pd
import requests

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from research.fundamentals_f1 import common as C  # noqa: E402

BASE_URL = "https://api.massive.com"
FETCH_DATE = "2026-09-12"
RAW_ROOT = f"data/raw/fundamentals/massive/{FETCH_DATE}"
MANIFEST_PATH = f"{RAW_ROOT}/fetch_manifest.json"
PROGRESS_PATH = f"{C.ART}/_t2_progress.json"
SUMMARY_PATH = f"{C.ART}/t2_pull_summary.json"

CIK_KEYED = {
    "financials": {"path": "/vX/reference/financials", "param": "cik", "source_of_record": False},
    "ticker_details": {"path": "/v3/reference/tickers", "param": "cik", "source_of_record": True},
}
TICKER_KEYED = {
    "splits": {"path": "/v3/reference/splits", "source_of_record": True},
    "dividends": {"path": "/v3/reference/dividends", "source_of_record": True},
    "short_interest": {"path": "/stocks/v1/short-interest", "source_of_record": True},
    "short_volume": {"path": "/stocks/v1/short-volume", "source_of_record": True},
    "float": {"path": "/stocks/vX/float", "source_of_record": False},  # D27: archive only
}
NOT_FOUND = ["ratios"]


def _get(session, url, params, key, max_retries=5):
    for attempt in range(max_retries):
        try:
            r = session.get(url, params={**params, "apiKey": key}, timeout=30)
            if r.status_code == 401:
                raise SystemExit("AUTH FAILURE -- 401. Hard stop, no retry loop (escalation row 4).")
            if r.status_code == 404:
                return None
            if r.status_code != 200:
                time.sleep(2 ** attempt)
                continue
            return r.json()
        except requests.exceptions.RequestException:
            time.sleep(2 ** attempt)
    raise RuntimeError(f"failed after {max_retries} attempts: {url} {params}")


def fetch_all_pages(session, url, params, key, cap=None):
    """Follows next_url. cap limits total records for endpoints with unbounded history
    (e.g. short_interest/short_volume, which are daily/settlement-period observations and
    could otherwise run to thousands of rows per ticker for a name with years of history)."""
    results = []
    next_url, next_params = url, {**params, "limit": 100}
    while next_url:
        d = _get(session, next_url, next_params, key)
        if d is None:
            break
        results.extend(d.get("results", []))
        next_url = d.get("next_url")
        next_params = {}  # next_url carries its own query string; only apiKey needs re-adding
        if cap and len(results) >= cap:
            break
    return results


def build_cik_identity_map() -> pd.DataFrame:
    """One row per CIK actually resolved in F1-T1, with a representative ticker."""
    spine = pd.read_parquet(f"{C.ART}/ticker_identity.parquet")
    resolved = spine.dropna(subset=["cik"])
    # representative ticker per CIK: the most frequent ticker string mapped to it
    rep = (resolved.groupby(["cik", "ticker"]).size().reset_index(name="n")
           .sort_values("n", ascending=False).drop_duplicates(subset="cik"))
    return rep[["cik", "ticker"]].reset_index(drop=True)


def write_raw(source: str, key_value: str, records: list) -> tuple[str, int, str]:
    d = os.path.join(RAW_ROOT, source)
    os.makedirs(d, exist_ok=True)
    path = os.path.join(d, f"{key_value}.json")
    content = json.dumps(records, indent=2)
    with open(path, "w") as f:
        f.write(content)
    checksum = hashlib.sha256(content.encode()).hexdigest()
    return path, len(records), checksum


def main():
    key = C.load_massive_api_key()
    cik_map = build_cik_identity_map()
    print(f"{len(cik_map)} distinct CIKs to pull (of {C.TARGET_ROW_COUNT} events, "
          f"{pd.read_parquet(f'{C.ART}/ticker_identity.parquet')['cik'].isna().sum()} unresolved and skipped)")

    session = requests.Session()
    os.makedirs(RAW_ROOT, exist_ok=True)

    if os.path.exists(PROGRESS_PATH):
        with open(PROGRESS_PATH) as f:
            progress = json.load(f)
    else:
        progress = {s: [] for s in list(CIK_KEYED) + list(TICKER_KEYED)}

    manifest = {"fetch_date": FETCH_DATE, "sources": {}, "not_found": NOT_FOUND}
    file_records = {s: [] for s in list(CIK_KEYED) + list(TICKER_KEYED)}

    for source, cfg in CIK_KEYED.items():
        done = set(progress[source])
        url = f"{BASE_URL}{cfg['path']}"
        for i, row in cik_map.iterrows():
            if row["cik"] in done:
                continue
            records = fetch_all_pages(session, url, {cfg["param"]: row["cik"]}, key)
            path, n, checksum = write_raw(source, row["cik"], records)
            file_records[source].append({"key": row["cik"], "path": path, "n": n, "sha256": checksum})
            progress[source].append(row["cik"])
            if len(progress[source]) % 300 == 0:
                print(f"  {source}: {len(progress[source])}/{len(cik_map)}")
                C.write_json(PROGRESS_PATH, progress)
        C.write_json(PROGRESS_PATH, progress)
        print(f"{source}: done, {len(progress[source])} CIKs")

    for source, cfg in TICKER_KEYED.items():
        done = set(progress[source])
        for i, row in cik_map.iterrows():
            if row["cik"] in done:
                continue
            if source == "float":
                d = _get(session, f"{BASE_URL}{cfg['path']}", {"ticker": row["ticker"]}, key)
                records = d.get("results", []) if d else []
            elif source in ("short_interest", "short_volume"):
                records = fetch_all_pages(session, f"{BASE_URL}{cfg['path']}", {"ticker": row["ticker"]}, key)
            else:
                records = fetch_all_pages(session, f"{BASE_URL}{cfg['path']}", {"ticker": row["ticker"]}, key)
            path, n, checksum = write_raw(source, row["cik"], records)
            file_records[source].append({"key": row["cik"], "ticker": row["ticker"], "path": path, "n": n, "sha256": checksum})
            progress[source].append(row["cik"])
            if len(progress[source]) % 300 == 0:
                print(f"  {source}: {len(progress[source])}/{len(cik_map)}")
                C.write_json(PROGRESS_PATH, progress)
        C.write_json(PROGRESS_PATH, progress)
        print(f"{source}: done, {len(progress[source])} CIKs")

    # ticker_events: path-based, keyed by ticker, no pagination
    source = "ticker_events"
    file_records[source] = []
    progress.setdefault(source, [])
    done = set(progress[source])
    for i, row in cik_map.iterrows():
        if row["cik"] in done:
            continue
        d = _get(session, f"{BASE_URL}/vX/reference/tickers/{row['ticker']}/events", {}, key)
        records = [d["results"]] if d and d.get("results") else []
        path, n, checksum = write_raw(source, row["cik"], records)
        file_records[source].append({"key": row["cik"], "ticker": row["ticker"], "path": path, "n": n, "sha256": checksum})
        progress[source].append(row["cik"])
        if len(progress[source]) % 300 == 0:
            print(f"  {source}: {len(progress[source])}/{len(cik_map)}")
            C.write_json(PROGRESS_PATH, progress)
    C.write_json(PROGRESS_PATH, progress)
    print(f"{source}: done, {len(progress[source])} CIKs")

    for source in list(CIK_KEYED) + list(TICKER_KEYED) + ["ticker_events"]:
        cfg = CIK_KEYED.get(source) or TICKER_KEYED.get(source) or {}
        manifest["sources"][source] = {
            "endpoint": cfg.get("path"),
            "keyed_by": "cik" if source in CIK_KEYED else "ticker",
            "source_of_record": cfg.get("source_of_record", True),
            "n_ciks_pulled": len(file_records.get(source, [])),
            "total_records": sum(r["n"] for r in file_records.get(source, [])),
            "request_timestamp_utc": datetime.now(timezone.utc).isoformat(),
        }
    C.write_json(MANIFEST_PATH, manifest)

    summary = {
        "cik_count": len(cik_map),
        "sources_pulled": {s: manifest["sources"][s]["total_records"] for s in manifest["sources"]},
        "not_found": NOT_FOUND,
        "manifest_path": MANIFEST_PATH,
        "config_hash": C.cfg_hash(),
    }
    C.write_json(SUMMARY_PATH, summary)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
