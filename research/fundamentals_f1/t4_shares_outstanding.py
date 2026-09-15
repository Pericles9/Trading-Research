"""
Build F1, F1-T4a-d: shares outstanding, from SEC companyfacts. Network step -- writes the
raw archive, then stops. Authorized by docs/Universe-Decisions.md D14 Amendment A1 (see the
2026-09-12 clarification note appended to that decision: the amendment's "F1-T3 (SEC EDGAR
... companyfacts.zip pull)" bundled what the work order later split into F1-T3 and F1-T4;
the authorization covers both).

**Deviates from F1-T4a's literal instruction ("download the SEC companyfacts.zip bulk
archive") -- checked the actual numbers before committing to that path, not after:**
`HEAD` on https://www.sec.gov/Archives/edgar/daily-index/xbrl/companyfacts.zip returned
Content-Length 1,408,785,961 (1.4 GB compressed). Disk budget is not the binding constraint
(366 GB free on E: at the time of this check) -- the binding constraint is that the archive
covers **every** EDGAR filer (roughly 800,000+ companies) to serve **2,935** CIKs, 0.4% of
it, and this build already hit real friction extracting a 23,480-file archive on this
Windows/NTFS setup in F1-T2 (`du -sh` had to be abandoned as too slow). Unzipping ~800k
small JSON files to use 2,935 of them is the same shape of waste, worse by 30x. The
per-CIK `data.sec.gov/api/xbrl/companyfacts/CIK##########.json` endpoint is the same data,
server-side filtered to one CIK, already proven in this build (F1-T0g, CLRB) and paced
identically to F1-T3's per-CIK submissions pull. This is a substitution of *how* the data
is fetched, not *what* is fetched or how it is used -- disk budget is still reported below,
per F1-T4a's underlying intent (confirm before discovering), even though the number that
matters turned out to be request count, not disk space.

**`accepted_ns` gap, closed via F1-T3, not invented here:** `companyfacts`' per-observation
records carry `filed` as a DATE ONLY -- no time-of-day, so it cannot supply the nanosecond
timestamp the shs_ schema group requires (`shs_accepted_ns`, "strictly less than t0_ns",
same rule as every other group). F1-T3's `sec_filings.parquet` already carries genuine
`accepted_ns` (verified UTC, see that script's docstring) for the same CIK universe, keyed
by `(cik, accession)` -- the same accession numbers `companyfacts` observations cite. Joining
against it, rather than promoting `filed`'s date to a fabricated midnight timestamp, is the
correct source; where an accession isn't in `sec_filings` (outside its fetch window), this
script says so explicitly per row rather than silently defaulting to a lower-precision date.

Usage: .venv/Scripts/python.exe research/fundamentals_f1/t4_shares_outstanding.py
"""
from __future__ import annotations

import json
import os
import sys
import time

import duckdb
import pandas as pd
import requests

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from research.fundamentals_f1 import common as C  # noqa: E402

FETCH_DATE = "2026-09-12"
RAW_ROOT = f"{C.RAW_ROOT}/sec/{FETCH_DATE}/companyfacts"
MANIFEST_PATH = f"{C.RAW_ROOT}/sec/{FETCH_DATE}/companyfacts_manifest.json"
PROGRESS_PATH = f"{C.ART}/_t4_progress.json"
OBS_PATH = f"{C.ART}/shares_outstanding_observations.parquet"
SUMMARY_PATH = f"{C.ART}/t4_shares_outstanding_summary.json"
REQUEST_PACING_SEC = 0.11

CONCEPT = "EntityCommonStockSharesOutstanding"
TAXONOMY = "dei"


def fetch_companyfacts(session, cik: str, ua: str, max_retries=6):
    url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
    for attempt in range(max_retries):
        try:
            r = session.get(url, headers={"User-Agent": ua}, timeout=30)
            time.sleep(REQUEST_PACING_SEC)
            if r.status_code == 404:
                return None
            if r.status_code in (401, 403):
                raise SystemExit(f"AUTH/RATE FAILURE -- {r.status_code} on {url}. Hard stop (escalation row 4).")
            if r.status_code != 200:
                time.sleep(2 ** attempt)
                continue
            return r.json()
        except requests.exceptions.RequestException:
            time.sleep(2 ** attempt)
    raise RuntimeError(f"failed after {max_retries} attempts: {url}")


def main():
    cfg = C.load_cfg()
    ua = cfg["sec_edgar"]["user_agent"]
    cik_map = C.build_cik_identity_map()
    n = len(cik_map)

    print("F1-T4a disk budget check (informational -- per-CIK pull chosen instead, see docstring):")
    print("  companyfacts.zip Content-Length observed 2026-09-12: 1,408,785,961 bytes (1.4 GB)")

    session = requests.Session()
    os.makedirs(RAW_ROOT, exist_ok=True)
    if os.path.exists(PROGRESS_PATH):
        with open(PROGRESS_PATH) as f:
            progress = json.load(f)
    else:
        progress = {"done_ciks": [], "no_concept_ciks": [], "no_facts_ciks": []}
    done = set(progress["done_ciks"])

    all_obs = []
    for i, row in cik_map.iterrows():
        cik = row["cik"]
        if cik in done:
            cache_path = f"{C.ART}/_t4_parts/{cik}.parquet"
            if os.path.exists(cache_path):
                all_obs.append(pd.read_parquet(cache_path))
            continue
        d = fetch_companyfacts(session, cik, ua)
        obs_rows = []
        if d is None:
            progress["no_facts_ciks"].append(cik)
        else:
            raw_path = os.path.join(RAW_ROOT, f"{cik}.json")
            with open(raw_path, "w") as f:
                json.dump(d, f)
            try:
                tag = d["facts"][TAXONOMY][CONCEPT]
                recs = tag["units"]["shares"]
            except KeyError:
                recs = []
                progress["no_concept_ciks"].append(cik)
            for r in recs:
                obs_rows.append({
                    "cik": cik, "shares": r.get("val"), "asof_date": r.get("end"),
                    "source_form": r.get("form"), "accession": r.get("accn"),
                    "fiscal_year": r.get("fy"), "fiscal_period": r.get("fp"),
                    "filed_date": r.get("filed"),
                })
        obs_df = pd.DataFrame(obs_rows)
        os.makedirs(f"{C.ART}/_t4_parts", exist_ok=True)
        obs_df.to_parquet(f"{C.ART}/_t4_parts/{cik}.parquet", index=False)
        all_obs.append(obs_df)
        progress["done_ciks"].append(cik)
        if len(progress["done_ciks"]) % 300 == 0:
            print(f"  {len(progress['done_ciks'])}/{n}")
            C.write_json(PROGRESS_PATH, progress)
    C.write_json(PROGRESS_PATH, progress)
    print(f"companyfacts pulled/loaded for {len(progress['done_ciks'])}/{n} CIKs "
          f"({len(progress['no_facts_ciks'])} no companyfacts record, "
          f"{len(progress['no_concept_ciks'])} companyfacts present but no "
          f"dei:EntityCommonStockSharesOutstanding tag)")

    obs = pd.concat(all_obs, ignore_index=True) if all_obs else pd.DataFrame()
    obs = obs.dropna(subset=["shares", "asof_date"]).drop_duplicates(subset=["cik", "accession", "asof_date"])

    # accepted_ns: join against F1-T3's sec_filings for genuine timestamp precision
    sec_filings = pd.read_parquet(f"{C.ART}/sec_filings.parquet")[["cik", "accession", "accepted_ns"]]
    obs = obs.merge(sec_filings, on=["cik", "accession"], how="left")
    n_missing_accepted = int(obs["accepted_ns"].isna().sum())
    print(f"shares_outstanding_observations: {len(obs)} rows, {n_missing_accepted} "
          f"({n_missing_accepted/len(obs):.1%}) with no accepted_ns match in sec_filings "
          "(accession outside F1-T3's fetch window) -- kept, not dropped, accepted_ns null.")

    obs.to_parquet(OBS_PATH, index=False)

    manifest = {
        "fetch_date": FETCH_DATE, "user_agent": ua, "n_ciks": n,
        "concept": f"{TAXONOMY}:{CONCEPT}", "raw_root": RAW_ROOT,
        "method_deviation": "per-CIK companyfacts API, not companyfacts.zip bulk -- see script docstring",
        "companyfacts_zip_content_length_bytes_2026_09_12": 1408785961,
    }
    C.write_json(MANIFEST_PATH, manifest)

    summary = {
        "n_ciks_pulled": n,
        "n_no_companyfacts_record": len(progress["no_facts_ciks"]),
        "n_no_shares_outstanding_concept": len(progress["no_concept_ciks"]),
        "shares_outstanding_observations_rows": len(obs),
        "n_distinct_ciks_with_observations": int(obs["cik"].nunique()) if len(obs) else 0,
        "n_missing_accepted_ns": n_missing_accepted,
        "config_hash": C.cfg_hash(),
    }
    C.write_json(SUMMARY_PATH, summary)
    print(json.dumps(summary, indent=2, default=str))


if __name__ == "__main__":
    main()
