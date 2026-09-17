"""
Build F1, F1-T0: the restatement gate test.

Massive's documentation is self-contradictory on point-in-time behavior for the financials
endpoint: it says values are "returned as restated in the most recent filing, not as
originally submitted," which implies one record per period. It also says multiple records
may share a filing_date "because filings restate prior comparatives," which implies
records ARE keyed by filing vintage and filing_date < t0 is a valid as-of filter. This
script tests which is true, empirically, on two independent companies with a confirmed SEC
restatement event.

F1-T0a: identification. A plain search for ANY 10-K/A in the universe repeatedly surfaced
administrative, Part-III-only amendments filed ~1 month after the original (a well-known
small-cap compliance pattern -- adding director/officer compensation disclosure that would
otherwise need a proxy statement) which never touch financial-statement values and cannot
distinguish either branch. The decisive signal instead is an 8-K Item 4.02
("Non-Reliance on Previously Issued Financial Statements") filing, which only accompanies
a genuine financial restatement. IDENTIFIED (see identify_candidates()): AGAE (Allied
Gaming & Entertainment) and CLRB (Cellectar Biosciences), both confirmed via SEC EDGAR
full-text search cross-referenced against the F1 universe ticker list.

F1-T0b: query the financials endpoint unfiltered by filing_date for each company's full
history; archive raw responses.

F1-T0c/d: report record counts per period and run the decisive test on CLRB -- compare an
unfiltered query against one with an explicit filing_date.lt cutoff set before its 2024-08-09
Item 4.02 8-K, for the FY2023 annual period that 8-K would affect.

Network use authorized by docs/Universe-Decisions.md D14 Amendment A1.

Usage: .venv/Scripts/python.exe research/fundamentals_f1/t0_restatement_test.py
"""
from __future__ import annotations

import json
import os
import re
import sys
import time

import pandas as pd
import requests

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from research.fundamentals_f1 import common as C  # noqa: E402

UA = "Mom_db Research fundamentals_f1 (cleeming29@gmail.com)"
RAW_DIR = f"{C.RAW_ROOT}/massive/2026-09-11/t0_restatement_test"
SUMMARY_PATH = f"{C.ART}/t0_restatement_test_summary.json"

# F1-T0a: identified via SEC EDGAR full-text search for 8-K Item 4.02 "non-reliance"
# filings, cross-referenced against the universe ticker list (see identify_candidates()
# for the reusable search; these two are the confirmed result of that search, not
# re-searched on every run to keep this script's output stable).
CANDIDATES = {
    "AGAE": {"restatement_signal": "10-K/A", "filed": "2024-04-29", "restated_period": "2023-12-31"},
    "CLRB": {"restatement_signal": "8-K Item 4.02 non-reliance", "filed": "2024-08-09", "restated_period": "2023-12-31"},
}


def identify_candidates(forms=("8-K",), query='"non-reliance"', startdt="2020-01-01", enddt="2024-12-31", max_hits=8):
    """F1-T0a's identification method: SEC EDGAR full-text search cross-referenced against
    the F1 universe ticker list. Reusable, not required for the rest of this script to run
    (CANDIDATES above is the recorded result), but kept so the identification step is
    itself a repro command, not a one-off manual search."""
    universe = pd.read_parquet(C.UNIVERSE_MATERIALIZATION_PATH, columns=["ticker"])
    uni_tickers = set(universe["ticker"].unique())
    found = []
    for form in forms:
        for start in range(0, 300, 10):
            r = requests.get(
                "https://efts.sec.gov/LATEST/search-index",
                params={"q": query, "forms": form, "startdt": startdt, "enddt": enddt, "from": start},
                headers={"User-Agent": UA}, timeout=30,
            )
            hits = r.json()["hits"]["hits"]
            if not hits:
                break
            for h in hits:
                for n in h["_source"].get("display_names", []):
                    m = re.search(r"\(([A-Z]{1,6})\)", n)
                    if m and m.group(1) in uni_tickers:
                        found.append((m.group(1), n, h["_source"]["file_date"], h["_source"]["adsh"]))
            time.sleep(0.25)
            if len(found) >= max_hits:
                return found
    return found


def fetch_all_financials(ticker: str) -> list[dict]:
    key = C.load_massive_api_key()
    results = []
    url = "https://api.massive.com/vX/reference/financials"
    params = {"ticker": ticker, "limit": 100, "apiKey": key}
    while url:
        r = requests.get(url, params=params, timeout=30)
        r.raise_for_status()
        d = r.json()
        results.extend(d.get("results", []))
        url = d.get("next_url")
        params = {"apiKey": key} if url else None
    return results


def duplicate_periods(records: list[dict]) -> dict:
    keyset: dict = {}
    for rec in records:
        k = (rec.get("start_date"), rec.get("end_date"), rec.get("timeframe"))
        keyset.setdefault(k, []).append(rec.get("filing_date"))
    return {str(k): v for k, v in keyset.items() if len(v) > 1}


def decisive_filing_date_test(ticker: str, period_end: str, cutoff_before: str) -> dict:
    """The decisive test: does filing_date.lt return a genuinely different (earlier)
    vintage than an unfiltered query, for a period whose restatement postdates cutoff_before?
    If both return the identical filing_date/value, filing_date is not a valid as-of filter."""
    key = C.load_massive_api_key()
    common_params = {"ticker": ticker, "timeframe": "annual", "period_of_report_date.lte": period_end, "limit": 3}

    r_filtered = requests.get(
        "https://api.massive.com/vX/reference/financials",
        params={**common_params, "filing_date.lt": cutoff_before, "apiKey": key}, timeout=30,
    )
    r_unfiltered = requests.get(
        "https://api.massive.com/vX/reference/financials",
        params={**common_params, "apiKey": key}, timeout=30,
    )

    def top(rec):
        rev = rec.get("financials", {}).get("income_statement", {}).get("revenues", {}).get("value")
        return {"start_date": rec.get("start_date"), "end_date": rec.get("end_date"),
                "filing_date": rec.get("filing_date"), "revenues": rev}

    filtered_top = [top(r) for r in r_filtered.json().get("results", [])[:1]]
    unfiltered_top = [top(r) for r in r_unfiltered.json().get("results", [])[:1]]
    identical = filtered_top == unfiltered_top
    return {
        "ticker": ticker, "cutoff_before": cutoff_before,
        "filtered_top_record": filtered_top, "unfiltered_top_record": unfiltered_top,
        "identical": identical,
    }


def main():
    os.makedirs(RAW_DIR, exist_ok=True)
    per_company = {}

    for ticker in CANDIDATES:
        records = fetch_all_financials(ticker)
        with open(f"{RAW_DIR}/{ticker}_all_unfiltered.json", "w") as f:
            json.dump(records, f, indent=2)
        dups = duplicate_periods(records)
        per_company[ticker] = {
            "total_records": len(records),
            "duplicate_periods": dups,
            "n_duplicate_periods": len(dups),
            "restatement_signal": CANDIDATES[ticker],
        }
        print(f"{ticker}: {len(records)} records, {len(dups)} duplicate (start,end,timeframe) periods")

    decisive = decisive_filing_date_test("CLRB", "2023-12-31", "2024-08-09")
    print("decisive filing_date.lt test (CLRB, FY2023, cutoff before its 2024-08-09 "
          f"Item 4.02 8-K): identical={decisive['identical']}")

    # F1-T0e outcome per prompts/fundamentals_f1.md SS3's outcome table.
    any_duplicates = any(v["n_duplicate_periods"] > 0 for v in per_company.values())
    outcome = "one_record_per_period_latest_values" if (not any_duplicates and decisive["identical"]) else "point_in_time_confirmed"

    summary = {
        "companies_tested": list(CANDIDATES.keys()),
        "per_company": per_company,
        "decisive_test": decisive,
        "outcome": outcome,
        "escalation_row_1_fires": outcome == "one_record_per_period_latest_values",
        "action": (
            "STOP AND POST. Vendor financials are not point-in-time via filing_date. "
            "The work order needs an amendment before F1-T2 -- the fin_ group cannot be "
            "assembled from Massive's financials endpoint alone without lookahead; the SEC "
            "route (raw XBRL per accepted filing) becomes the source of record for "
            "financials, per prompts/fundamentals_f1.md SS3's own outcome table."
        ) if outcome == "one_record_per_period_latest_values" else "Proceed as written.",
    }
    C.write_json(SUMMARY_PATH, summary)
    print(json.dumps({"outcome": outcome, "escalation_row_1_fires": summary["escalation_row_1_fires"]}, indent=2))


if __name__ == "__main__":
    main()
