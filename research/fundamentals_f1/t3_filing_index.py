"""
Build F1, F1-T3a-e: SEC filing index and event proximity. Network step -- writes the raw
archive, then stops. Authorized by docs/Universe-Decisions.md D14 Amendment A1, scoped to
this task.

Per-CIK submissions.json, not the daily/full-index bulk archives, despite F1-T3a's literal
"prefer the bulk archives" instruction -- checked directly before building this: the
daily/full-index files (form.idx / master.idx) carry only a filing DATE, no time, and
`accepted_ns` is explicitly the load-bearing column for this whole task (F1-T3b). Getting
acceptance time from the bulk route would mean fetching every individual filing's own
index page anyway -- exactly as many requests as the per-CIK route, for a worse join (date
only, keyed by CIK+date collision risk on multi-filing days) instead of a better one
(exact timestamp, one call typically covers a company's entire relevant history). The
per-CIK submissions API is *itself* a bulk pull, just bulk-per-company rather than
bulk-per-day: one call returns up to 1000 recent filings for a CIK; only companies with a
longer filing history need a second call against `filings.files`.

Timezone check done directly, not assumed (the field is a well-known point of confusion):
submissions.json's `acceptanceDateTime` carries a trailing "Z" that could plausibly be
either UTC or a mislabeled Eastern local time. Cross-checked one filing (CLRB
0001104659-26-096766) against its own human-readable -index.htm page, which independently
states "Accepted 2026-08-14 12:11:24" -- Eastern Daylight Time (UTC-4) of the JSON's
"2026-08-14T16:11:24.000Z". They match exactly: the JSON value is genuine UTC. Parsed as
such, directly comparable to t0_ns with no conversion.

Usage: .venv/Scripts/python.exe research/fundamentals_f1/t3_filing_index.py
"""
from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone

import duckdb
import pandas as pd
import requests

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from research.fundamentals_f1 import common as C  # noqa: E402

FETCH_DATE = "2026-09-12"
RAW_ROOT = f"data/raw/fundamentals/sec/{FETCH_DATE}/submissions"
MANIFEST_PATH = f"data/raw/fundamentals/sec/{FETCH_DATE}/submissions_manifest.json"
PROGRESS_PATH = f"{C.ART}/_t3_progress.json"

SEC_FILINGS_PATH = f"{C.ART}/sec_filings.parquet"
EVENT_PROXIMITY_PATH = f"{C.ART}/event_filing_proximity.parquet"
EVENT_WINDOW_PATH = f"{C.ART}/event_filings_window.parquet"
SUMMARY_PATH = f"{C.ART}/t3_filing_index_summary.json"

FIELDS = ["accessionNumber", "form", "filingDate", "reportDate", "acceptanceDateTime", "items"]


REQUEST_PACING_SEC = 0.11  # SEC's published fair-access guidance: stay well under 10 req/s


def fetch_json(session, url, ua, max_retries=6):
    for attempt in range(max_retries):
        try:
            r = session.get(url, headers={"User-Agent": ua}, timeout=30)
            time.sleep(REQUEST_PACING_SEC)
            if r.status_code == 404:
                return None
            if r.status_code == 403 or r.status_code == 401:
                raise SystemExit(f"AUTH/RATE FAILURE -- {r.status_code} on {url}. Hard stop (escalation row 4).")
            if r.status_code != 200:
                time.sleep(2 ** attempt)
                continue
            return r.json()
        except requests.exceptions.RequestException:
            time.sleep(2 ** attempt)
    raise RuntimeError(f"failed after {max_retries} attempts: {url}")


def pull_cik_filings(session, cik: str, ua: str, min_filing_date: str) -> tuple[pd.DataFrame, list[dict]]:
    """Returns (dataframe of filings, list of raw-archive records for the manifest)."""
    url = f"https://data.sec.gov/submissions/CIK{cik}.json"
    d = fetch_json(session, url, ua)
    if d is None:
        return pd.DataFrame(columns=FIELDS), []

    archive_note = []
    raw_path = os.path.join(RAW_ROOT, f"{cik}.json")
    os.makedirs(RAW_ROOT, exist_ok=True)
    with open(raw_path, "w") as f:
        json.dump(d, f)
    archive_note.append({"path": raw_path, "kind": "primary"})

    recent = d.get("filings", {}).get("recent", {})
    frames = [pd.DataFrame({k: recent.get(k, []) for k in FIELDS})]

    older_files = d.get("filings", {}).get("files", [])
    earliest = frames[0]["filingDate"].min() if len(frames[0]) else "9999-99-99"
    for finfo in older_files:
        if pd.isna(earliest) or earliest > min_filing_date:
            older_url = f"https://data.sec.gov/submissions/{finfo['name']}"
            od = fetch_json(session, older_url, ua)
            if od:
                older_raw_path = os.path.join(RAW_ROOT, f"{cik}__{finfo['name']}")
                with open(older_raw_path, "w") as f:
                    json.dump(od, f)
                archive_note.append({"path": older_raw_path, "kind": "older_history"})
                frames.append(pd.DataFrame({k: od.get(k, []) for k in FIELDS}))
                earliest = frames[-1]["filingDate"].min() if len(frames[-1]) else earliest
        else:
            break

    out = pd.concat(frames, ignore_index=True)
    out["cik"] = cik
    return out, archive_note


def main():
    cfg = C.load_cfg()
    ua = cfg["sec_edgar"]["user_agent"]
    cik_map = C.build_cik_identity_map()

    t0_spine = pd.read_parquet(f"{C.ART}/t0_spine.parquet")
    universe_min = t0_spine["event_date_canonical"].min()
    universe_max = t0_spine["event_date_canonical"].max()
    min_filing_date = (pd.Timestamp(universe_min) - timedelta(days=30)).strftime("%Y-%m-%d")
    max_filing_date = (pd.Timestamp(universe_max) + timedelta(days=5)).strftime("%Y-%m-%d")
    daily_index_floor = cfg["sec_edgar"]["daily_index_start_date"]  # 2020-01-01, F1-T3a's stated floor
    fetch_floor = min(min_filing_date, daily_index_floor)
    print(f"universe event dates {universe_min}..{universe_max}; "
          f"filing window kept [{fetch_floor}, {max_filing_date}] "
          f"(F1-T3a floor {daily_index_floor}, F1-T3d -30/+5d padding)")

    session = requests.Session()
    if os.path.exists(PROGRESS_PATH):
        with open(PROGRESS_PATH) as f:
            progress = json.load(f)
    else:
        progress = {"done_ciks": []}
    done = set(progress["done_ciks"])

    manifest_records = []
    all_frames = []
    n = len(cik_map)
    for i, row in cik_map.iterrows():
        cik = row["cik"]
        cache_path = f"{C.ART}/_t3_parts/{cik}.parquet"
        if cik in done and os.path.exists(cache_path):
            all_frames.append(pd.read_parquet(cache_path))
            continue
        df, notes = pull_cik_filings(session, cik, ua, fetch_floor)
        os.makedirs(f"{C.ART}/_t3_parts", exist_ok=True)
        df.to_parquet(cache_path, index=False)
        all_frames.append(df)
        manifest_records.extend([{**note, "cik": cik} for note in notes])
        progress["done_ciks"].append(cik)
        if len(progress["done_ciks"]) % 300 == 0:
            print(f"  {len(progress['done_ciks'])}/{n}")
            C.write_json(PROGRESS_PATH, progress)
    C.write_json(PROGRESS_PATH, progress)
    print(f"pulled/loaded filings for {len(progress['done_ciks'])}/{n} CIKs")

    filings = pd.concat(all_frames, ignore_index=True)
    filings = filings.rename(columns={
        "accessionNumber": "accession", "form": "form_type",
        "filingDate": "filing_date", "reportDate": "period_of_report",
    })
    filings["accepted_ns"] = pd.to_datetime(
        filings["acceptanceDateTime"], utc=True, errors="coerce"
    ).astype("int64")
    filings.loc[filings["acceptanceDateTime"].isna() | (filings["acceptanceDateTime"] == ""), "accepted_ns"] = pd.NA
    filings["accepted_ns"] = filings["accepted_ns"].astype("Int64")
    filings = filings.drop(columns=["acceptanceDateTime"])
    filings["period_of_report"] = filings["period_of_report"].replace("", pd.NA)
    filings["items"] = filings["items"].replace("", pd.NA)

    # F1-T3h needs 8-K Item 4.02 filings with NO upper date bound (a restatement can land
    # any time after the event's fin_ vintage, not just within the -30d/+5d companion-table
    # window below) -- extract this full-history subset before the window truncation
    # discards anything past max_filing_date. Small (Item 4.02 filings are rare), so keeping
    # it unbounded costs nothing.
    item402 = filings[
        (filings["form_type"] == "8-K")
        & filings["items"].astype(str).str.contains("4.02", na=False)
    ].dropna(subset=["accepted_ns"]).drop_duplicates(subset=["cik", "accession"])
    item402 = item402[["cik", "accession", "accepted_ns", "filing_date"]]
    item402.to_parquet(f"{C.ART}/item402_filings_full_history.parquet", index=False)
    print(f"item402_filings_full_history: {len(item402)} rows, no date-window truncation")

    before = len(filings)
    filings = filings[(filings["filing_date"] >= fetch_floor) & (filings["filing_date"] <= max_filing_date)].copy()
    filings = filings.dropna(subset=["accepted_ns"]).drop_duplicates(subset=["cik", "accession"])
    print(f"sec_filings: {before} raw rows fetched -> {len(filings)} after window filter "
          f"[{fetch_floor}, {max_filing_date}] + accepted_ns present + dedup")

    filings.to_parquet(SEC_FILINGS_PATH, index=False)

    # ---- event join: identity + t0 ----
    identity = pd.read_parquet(f"{C.ART}/ticker_identity.parquet")[["event_id", "cik", "identity_quality"]]
    events = t0_spine[["event_id", "t0_ns"]].merge(identity, on="event_id", how="left")
    assert len(events) == C.TARGET_ROW_COUNT

    con = duckdb.connect()
    con.register("filings", filings)
    con.register("events", events)

    # F1-T3c: nearest prior filing (ASOF) + 24h/72h counts
    ns_24h = 24 * 3600 * 1_000_000_000
    ns_72h = 72 * 3600 * 1_000_000_000
    proximity = con.execute(f"""
        WITH nearest AS (
            SELECT e.event_id, e.cik, e.t0_ns,
                   f.accession AS flg_last_accession, f.form_type AS flg_last_form,
                   f.accepted_ns AS flg_last_accepted_ns
            FROM events e
            ASOF LEFT JOIN filings f
              ON e.cik = f.cik AND f.accepted_ns < e.t0_ns
        ),
        counts AS (
            -- count(f.accepted_ns), NOT count(*): a LEFT JOIN with zero matches still emits
            -- one row (all f.* NULL) per left-side event, and count(*) would count that
            -- phantom row as 1 -- caught 2026-09-12 via t5_assemble.py's spl_n_splits_365d
            -- showing the identical symptom (every event's count >= 1, never 0). Confirmed
            -- here too: pre-fix, flg_quality='unavailable' events (no cik, cannot possibly
            -- match anything) showed flg_n_filings_72h=1, not 0.
            SELECT e.event_id,
                   count(f.accepted_ns) FILTER (WHERE f.accepted_ns >= e.t0_ns - {ns_24h}) AS flg_n_filings_24h,
                   count(f.accepted_ns) AS flg_n_filings_72h
            FROM events e
            LEFT JOIN filings f
              ON e.cik = f.cik AND f.accepted_ns >= e.t0_ns - {ns_72h} AND f.accepted_ns < e.t0_ns
            GROUP BY e.event_id
        )
        SELECT n.event_id, n.cik, n.t0_ns, n.flg_last_form, n.flg_last_accession, n.flg_last_accepted_ns,
               (n.t0_ns - n.flg_last_accepted_ns) AS flg_lag_ns,
               c.flg_n_filings_24h, c.flg_n_filings_72h
        FROM nearest n JOIN counts c USING (event_id)
    """).df()

    proximity["flg_quality"] = "observed"
    proximity.loc[proximity["cik"].isna(), "flg_quality"] = "unavailable"
    proximity.loc[proximity["cik"].notna() & proximity["flg_last_accepted_ns"].isna(), "flg_quality"] = "no_filings_in_window"

    # F1-T3e: dilution flag, using the declared form set + 8-K Item 3.02
    dilution_forms = set(cfg["dilution_form_set"]["minimum_forms"]) - {"8-K (Item 3.02)"}

    def is_dilution_row(form_type, items):
        if form_type in dilution_forms:
            return True
        if form_type == "8-K" and isinstance(items, str) and "3.02" in items.split(","):
            return True
        return False

    filings["is_dilution_form"] = [is_dilution_row(ft, it) for ft, it in zip(filings["form_type"], filings["items"])]
    con.register("filings2", filings)
    window72 = con.execute(f"""
        SELECT e.event_id, bool_or(f.is_dilution_form) AS any_dilution_72h
        FROM events e
        JOIN filings2 f ON e.cik = f.cik AND f.accepted_ns >= e.t0_ns - {ns_72h} AND f.accepted_ns < e.t0_ns
        GROUP BY e.event_id
    """).df()
    proximity = proximity.merge(window72, on="event_id", how="left")
    proximity["any_dilution_72h"] = proximity["any_dilution_72h"].fillna(False)
    last_is_dilution = [is_dilution_row(ft, None) for ft in proximity["flg_last_form"]]
    proximity["flg_dilution_form_before_t0"] = proximity["any_dilution_72h"] | pd.Series(last_is_dilution, index=proximity.index)
    proximity = proximity.drop(columns=["any_dilution_72h", "cik", "t0_ns"])

    proximity.to_parquet(EVENT_PROXIMITY_PATH, index=False)

    # F1-T3d: event_filings_window, -30d/+5d, one row per (event_id, accession)
    ns_30d = 30 * 86400 * 1_000_000_000
    ns_5d = 5 * 86400 * 1_000_000_000
    window = con.execute(f"""
        SELECT e.event_id, f.accession, f.form_type, f.accepted_ns, f.filing_date, f.period_of_report, f.items
        FROM events e
        JOIN filings f ON e.cik = f.cik
          AND f.accepted_ns >= e.t0_ns - {ns_30d} AND f.accepted_ns <= e.t0_ns + {ns_5d}
    """).df()
    window.to_parquet(EVENT_WINDOW_PATH, index=False)

    # manifest for the raw archive
    manifest = {
        "fetch_date": FETCH_DATE, "user_agent": ua,
        "n_ciks": n, "n_primary_files": sum(1 for m in manifest_records if m["kind"] == "primary"),
        "n_older_history_files": sum(1 for m in manifest_records if m["kind"] == "older_history"),
        "raw_root": RAW_ROOT,
    }
    C.write_json(MANIFEST_PATH, manifest)

    summary = {
        "n_ciks_pulled": n,
        "sec_filings_rows": len(filings),
        "sec_filings_date_window": [fetch_floor, max_filing_date],
        "event_filing_proximity_rows": len(proximity),
        "flg_quality_counts": proximity["flg_quality"].value_counts().to_dict(),
        "flg_dilution_form_before_t0_true": int(proximity["flg_dilution_form_before_t0"].sum()),
        "event_filings_window_rows": len(window),
        "config_hash": C.cfg_hash(),
    }
    C.write_json(SUMMARY_PATH, summary)
    print(json.dumps(summary, indent=2, default=str))


if __name__ == "__main__":
    main()
