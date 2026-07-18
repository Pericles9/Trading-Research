"""
Phase 1b T1-R1 - bulk reference snapshot from the Massive reference API.

Pulls /v3/reference/tickers for market=stocks, both active and inactive,
paginated to completion. Persists raw fields unmodified plus a
snapshot_utc column. API key read from .secrets/polygon_api_key.txt
(gitignored) - never printed, logged, or written into any artifact.
"""
import datetime
import time

import pandas as pd
import requests

BASE_URL = "https://api.massive.com"
KEY_PATH = ".secrets/polygon_api_key.txt"
OUT_PATH = "results/phase_1b/artifacts/ticker_reference_snapshot.parquet"


def load_key():
    with open(KEY_PATH) as f:
        return f.read().strip()


def fetch_all(session, key, active: bool):
    url = f"{BASE_URL}/v3/reference/tickers"
    params = {"market": "stocks", "active": str(active).lower(), "limit": 1000, "apiKey": key}
    results = []
    page = 0
    while True:
        attempt = 0
        while attempt < 5:
            try:
                resp = session.get(url, params=params, timeout=60)
                if resp.status_code == 401:
                    raise SystemExit("AUTH FAILURE - 401 from reference API. Hard stop, no retry loop.")
                if resp.status_code != 200:
                    attempt += 1
                    time.sleep(2**attempt)
                    continue
                data = resp.json()
                results.extend(data.get("results", []))
                page += 1
                if page % 10 == 0:
                    print(f"  active={active}: {page} pages, {len(results)} rows so far")
                next_url = data.get("next_url")
                if not next_url:
                    return results
                url = next_url
                params = {"apiKey": key}  # cursor is embedded in next_url
                break
            except SystemExit:
                raise
            except requests.exceptions.RequestException:
                attempt += 1
                time.sleep(2**attempt)
        else:
            raise RuntimeError(f"Failed to fetch page after 5 attempts (active={active}, page={page})")


def main():
    key = load_key()
    snapshot_utc = datetime.datetime.now(datetime.timezone.utc).isoformat()

    session = requests.Session()
    all_rows = []
    for active in (True, False):
        print(f"Fetching active={active}...")
        rows = fetch_all(session, key, active)
        print(f"  active={active}: {len(rows)} total rows")
        all_rows.extend(rows)

    df = pd.DataFrame(all_rows)
    df["snapshot_utc"] = snapshot_utc
    df["lookup_method"] = "bulk_reference_snapshot"

    df.to_parquet(OUT_PATH, index=False)
    print(f"\nWrote {len(df)} rows to {OUT_PATH}")
    print("Columns:", list(df.columns))
    print("Distinct tickers:", df["ticker"].nunique())


if __name__ == "__main__":
    main()
