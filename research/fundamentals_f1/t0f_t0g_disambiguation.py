"""
Build F1, Amendment F1-A1 SS0/SS2: F1-T0f (the disambiguating query) and F1-T0g
(companyfacts multi-vintage verification), both on CLRB -- the company that already broke
the vendor in F1-T0.

F1-T0's original test established that exactly one vendor record exists per period. It did
not establish WHICH vintage that record is. This script answers that, and separately
verifies SEC companyfacts is genuinely multi-vintage (the structure Amendment F1-A1 SS2
proposes to build fin_ from).

CLRB's 8-K Item 4.02 (accession 0001104659-24-087859, filed 2024-08-09) attributes the
restatement to warrant accounting treatment from an October 2022 financing, covering FY2023,
FY2022 annual statements and four 2023-2024 interim periods. The correction filings:
  - original FY2023 10-K:  accession 0001410578-24-000307, filed 2024-03-27
  - restated FY2023 10-K/A: accession 0001410578-24-001704, filed 2024-10-29

Network use authorized by docs/Universe-Decisions.md D14 Amendment A1 (F1-T0's own
authorization covers this -- it is the same restatement-test task, continued).

Usage: .venv/Scripts/python.exe research/fundamentals_f1/t0f_t0g_disambiguation.py
"""
from __future__ import annotations

import json
import os
import sys

import requests

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from research.fundamentals_f1 import common as C  # noqa: E402

UA = "Mom_db Research fundamentals_f1 (cleeming29@gmail.com)"
CIK = "0001279704"  # CLRB
ORIG_ACCN = "0001410578-24-000307"
RESTATED_ACCN = "0001410578-24-001704"
VENDOR_ARCHIVE = f"{C.RAW_ROOT}/massive/2026-09-11/t0_restatement_test/CLRB_all_unfiltered.json"
COMPANYFACTS_DIR = f"{C.RAW_ROOT}/sec/2026-09-12/companyfacts"
SUMMARY_PATH = f"{C.ART}/t0f_t0g_disambiguation_summary.json"


def fetch_companyfacts() -> dict:
    os.makedirs(COMPANYFACTS_DIR, exist_ok=True)
    path = f"{COMPANYFACTS_DIR}/CIK{CIK}.json"
    r = requests.get(f"https://data.sec.gov/api/xbrl/companyfacts/CIK{CIK}.json",
                      headers={"User-Agent": UA}, timeout=60)
    r.raise_for_status()
    with open(path, "w") as f:
        f.write(r.text)
    return r.json()


def f1_t0f(facts: dict) -> dict:
    """The disambiguating query: does the vendor's single FY2023 record match the original
    10-K or the restated 10-K/A?"""
    with open(VENDOR_ARCHIVE) as f:
        vendor_recs = json.load(f)
    vendor_fy2023 = next(
        r for r in vendor_recs
        if r.get("start_date") == "2023-01-01" and r.get("end_date") == "2023-12-31" and r.get("timeframe") == "annual"
    )
    vendor_ni = vendor_fy2023["financials"]["income_statement"]["net_income_loss"]["value"]
    vendor_filing_date = vendor_fy2023.get("filing_date")

    obs = facts["facts"]["us-gaap"]["NetIncomeLoss"]["units"]["USD"]
    orig_val = next(o["val"] for o in obs if o["accn"] == ORIG_ACCN and o["end"] == "2023-12-31" and o["start"] == "2023-01-01")
    restated_val = next(o["val"] for o in obs if o["accn"] == RESTATED_ACCN and o["end"] == "2023-12-31" and o["start"] == "2023-01-01")

    matches_original = vendor_ni == orig_val
    matches_restated = vendor_ni == restated_val
    outcome = "A_original_as_filed" if matches_original else ("B_latest_restated" if matches_restated else "NEITHER")

    return {
        "concept_tested": "NetIncomeLoss",
        "vendor_value": vendor_ni,
        "vendor_filing_date": vendor_filing_date,
        "original_10k_value": orig_val,
        "original_10k_accn": ORIG_ACCN,
        "original_10k_filed": "2024-03-27",
        "restated_10ka_value": restated_val,
        "restated_10ka_accn": RESTATED_ACCN,
        "restated_10ka_filed": "2024-10-29",
        "matches_original": matches_original,
        "matches_restated": matches_restated,
        "outcome": outcome,
    }


def f1_t0g(facts: dict) -> dict:
    """companyfacts multi-vintage verification: list every observation of the restated
    concept for the affected period, across every filing that reported it."""
    obs = facts["facts"]["us-gaap"]["NetIncomeLoss"]["units"]["USD"]
    period_obs = [o for o in obs if o.get("start") == "2023-01-01" and o.get("end") == "2023-12-31"]
    distinct_accn = sorted({o["accn"] for o in period_obs})
    distinct_vals = sorted({o["val"] for o in period_obs})
    observations = [
        {"accn": o["accn"], "filed": o["filed"], "form": o["form"], "val": o["val"]}
        for o in sorted(period_obs, key=lambda x: x["filed"])
    ]
    outcome = "multi_vintage_confirmed" if len(distinct_vals) > 1 else "single_observation_only"
    return {
        "concept_tested": "NetIncomeLoss",
        "period": "2023-01-01 to 2023-12-31",
        "n_observations": len(period_obs),
        "n_distinct_accn": len(distinct_accn),
        "n_distinct_values": len(distinct_vals),
        "observations": observations,
        "outcome": outcome,
    }


def main():
    facts = fetch_companyfacts()
    t0f = f1_t0f(facts)
    t0g = f1_t0g(facts)

    print("F1-T0f (disambiguating query):")
    print(f"  vendor: {t0f['vendor_value']} (filing_date={t0f['vendor_filing_date']})")
    print(f"  original 10-K: {t0f['original_10k_value']}")
    print(f"  restated 10-K/A: {t0f['restated_10ka_value']}")
    print(f"  outcome: {t0f['outcome']}")
    print()
    print("F1-T0g (companyfacts multi-vintage verification):")
    print(f"  {t0g['n_observations']} observations, {t0g['n_distinct_accn']} distinct accn, "
          f"{t0g['n_distinct_values']} distinct values")
    print(f"  outcome: {t0g['outcome']}")

    summary = {"f1_t0f": t0f, "f1_t0g": t0g}
    C.write_json(SUMMARY_PATH, summary)


if __name__ == "__main__":
    main()
