"""
collect_massive_data_v2.py -- Trades Rebuild Stage 1, T2/T3.

Corrected trades collector, validated against a small sample before any full-corpus
rebuild is considered. See t1_schema_rootcause.md for why T1 required no fix here.

Fixes relative to data/collection_scripts/collect_massive_data.py:

  T2 -- pagination truncation. The original's `status_forcelist=[500, 502, 503, 504]`
  excludes 429; a 429 mid-pagination fell through to `if resp.status_code != 200:
  ... break`, which silently returned whatever had been accumulated so far as if it
  were a complete, successful pull -- indistinguishable from a ticker that genuinely
  only traded that many times that day. Under MAX_WORKERS=4 concurrent load against
  high-volume tickers (millions of trades/day, 20-130+ sequential pages), this is a
  plausible mechanism for the ~400-500k-trade truncations found in Group A. Fixed two
  ways: (1) 429 added to the urllib3 Retry status_forcelist so the adapter retries
  transient rate-limiting automatically; (2) the manual retry loop now treats any
  non-200/non-429 status, or exhausted retries, as a hard failure -- it raises
  PaginationIncompleteError instead of returning a partial list. A truncated pull can
  no longer look identical to a complete one.

  T1 (no code fix needed, kept explicit): raw API response and DataFrame construction
  already preserve the full schema (sip_timestamp/participant_timestamp/sequence_number/
  tape/id) -- verified live against AAME 2021-02-05 and cross-checked against existing
  data/filtered/*/trades.parquet output. No column selection is performed anywhere in
  this file, by design, so schema loss cannot silently reappear.

Scope decision (not in the original script, made explicit here): this collector fetches
a **single target date per event**, not the original's 7-trading-day window aggregated
into one file. The high_momentum corpus and its "current" naming convention
(TICKER_YYYY-MM-DD_trades.parquet) are one file per (ticker, date); a window-aggregated
file would never be comparable to the existing per-date trade counts T4 validates
against. If Stage 2 needs the surrounding window for a different purpose, that is a
separate, explicit decision for that phase -- not assumed here.

Retry count, backoff factor, timeout, and MAX_WORKERS are unchanged from
collect_massive_data.py except where the T2 fix required touching status_forcelist.

Scope: TRADES ONLY. Writes strictly to data/trade_data/rebuild_validation_sample/ --
never touches data/trade_data/high_momentum.
"""

import os
import time
import logging
import requests
import pandas as pd
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from requests.exceptions import ChunkedEncodingError, ConnectionError, ReadTimeout
from urllib3.exceptions import ProtocolError

# --- Configuration (unchanged from collect_massive_data.py except paths) ---
API_KEY = "0EoKh8FwIpRR8WWRcd1Dxxp_wv3pI7Su"
BASE_URL = "https://api.massive.com"
OUTPUT_DIR = r"D:\Trading Research\data\trade_data\rebuild_validation_sample"
MAX_WORKERS = 4  # unchanged -- do not raise without confirming rate-limit tier

LOG_PATH = r"D:\Trading Research\results\rebuild_stage1\collection_log_v2.txt"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler(LOG_PATH), logging.StreamHandler()],
)


class PaginationIncompleteError(Exception):
    """Raised when a fetch terminates before genuine end-of-data (absence of next_url)."""


# Telemetry for the T4 validation driver's escalation checks -- any 429 or auth
# error should surface to Cooper even though fetch_all_pages retries 429s
# automatically (that retry is a collector-correctness fix, not permission to
# silently push through rate-limiting during this validation run).
import threading
_telemetry_lock = threading.Lock()
RATE_LIMIT_HITS = 0
AUTH_ERROR_HITS = 0


def _record_rate_limit_hit():
    global RATE_LIMIT_HITS
    with _telemetry_lock:
        RATE_LIMIT_HITS += 1


def _record_auth_error_hit():
    global AUTH_ERROR_HITS
    with _telemetry_lock:
        AUTH_ERROR_HITS += 1


def fetch_all_pages(session, url, params, context=""):
    results = []
    current_url = url
    current_params = params.copy()

    while True:
        attempt = 0
        page_succeeded = False
        while attempt < 5:
            try:
                if current_url == url:
                    resp = session.get(current_url, params=current_params, timeout=60, stream=False)
                else:
                    if "apiKey=" not in current_url:
                        symbol = "?" if "?" not in current_url else "&"
                        current_url = f"{current_url}{symbol}apiKey={API_KEY}"
                    resp = session.get(current_url, timeout=60, stream=False)

                if resp.status_code == 429:
                    _record_rate_limit_hit()
                    retry_after = resp.headers.get("Retry-After")
                    wait_time = float(retry_after) if retry_after else 2 ** attempt
                    attempt += 1
                    logging.warning(f"[{context}] 429 rate-limited fetching {current_url}. "
                                     f"Retrying ({attempt}/5) in {wait_time}s...")
                    time.sleep(wait_time)
                    continue

                if resp.status_code in (401, 403):
                    _record_auth_error_hit()

                if resp.status_code != 200:
                    logging.error(f"[{context}] Error {resp.status_code} fetching {current_url}: {resp.text}")
                    raise PaginationIncompleteError(
                        f"[{context}] HTTP {resp.status_code} fetching {current_url} after "
                        f"{len(results)} records collected so far."
                    )

                data = resp.json()
                if "results" in data:
                    results.extend(data["results"])

                if data.get("next_url"):
                    current_url = data["next_url"]
                else:
                    return results  # genuine end of data

                page_succeeded = True
                break

            except PaginationIncompleteError:
                raise
            except (ChunkedEncodingError, ProtocolError, ConnectionError, ReadTimeout) as e:
                attempt += 1
                wait_time = 2 ** attempt
                logging.warning(f"[{context}] Connection error fetching {current_url}: {e}. "
                                 f"Retrying ({attempt}/5) in {wait_time}s...")
                time.sleep(wait_time)

        if not page_succeeded:
            raise PaginationIncompleteError(
                f"[{context}] Failed to fetch {current_url} after 5 retries; "
                f"{len(results)} records collected so far."
            )

    return results


def collect_one_event(ticker, date_str, output_dir=OUTPUT_DIR):
    """Fetch one (ticker, date)'s trades. Returns (status, detail).

    status is one of "written" (detail=n_trades), "empty" (detail=0, genuinely no
    trades that day), or "failed" (detail=error message; no file written).
    """
    out_path = os.path.join(output_dir, f"{ticker}_{date_str}_trades.parquet")

    session = requests.Session()
    retries = Retry(
        total=8,
        backoff_factor=2,
        status_forcelist=[429, 500, 502, 503, 504],  # T2 fix: 429 now retried
        allowed_methods=["GET"],
        raise_on_status=False,
    )
    session.mount("https://", HTTPAdapter(max_retries=retries))

    try:
        with session:
            trades = fetch_all_pages(
                session,
                f"{BASE_URL}/v3/trades/{ticker}",
                {"timestamp": date_str, "limit": 50000, "apiKey": API_KEY, "sort": "timestamp"},
                context=f"{ticker} {date_str}",
            )
    except PaginationIncompleteError as e:
        logging.error(str(e))
        return "failed", str(e)
    except Exception as e:
        logging.error(f"[{ticker} {date_str}] Unexpected error: {e}")
        return "failed", str(e)

    if not trades:
        logging.warning(f"[{ticker} {date_str}] 0 trades returned (day may be genuinely empty).")
        return "empty", 0

    df = pd.DataFrame(trades)  # no column selection/renaming -- full raw schema preserved
    if "participant_timestamp" in df.columns:
        df["participant_timestamp"] = pd.to_numeric(df["participant_timestamp"])
    if "sip_timestamp" in df.columns:
        df["sip_timestamp"] = pd.to_numeric(df["sip_timestamp"])

    os.makedirs(output_dir, exist_ok=True)
    df.to_parquet(out_path)
    logging.info(f"[{ticker} {date_str}] Wrote {len(df)} trades to {out_path}")
    return "written", len(df)


if __name__ == "__main__":
    # Manual smoke test -- one cheap event, not part of the T4 30-event sample.
    status, detail = collect_one_event("AAME", "2021-02-05")
    print(status, detail)
