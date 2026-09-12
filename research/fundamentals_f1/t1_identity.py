"""
Build F1, F1-T1: identity spine. Resolves the SEC Central Index Key as of t0 for every
(ticker, t0) pair in the in-scope universe.

CORRECTED METHOD (2026-09-12, after the first run's result was checked rather than trusted).
The first version of this script pre-filtered tickers via
/v3/reference/tickers?ticker=X&active=true/false, treating a ticker as unambiguous whenever
that enumeration found only one CIK, and skipping per-event as-of resolution for it. That
run found ZERO ambiguous tickers across all 2,930 -- a suspiciously clean result for a
universe D30 itself describes as "a corner of the market where symbols are recycled after
delisting and reverse splits are routine." Spot-checking the widest-date-span tickers
directly against /v3/reference/tickers?ticker=X&date=Y at each ticker's earliest and latest
event date found a confirmed counter-example the pre-filter missed entirely: **NTRP**
resolves to "Neurotrope, Inc." (CIK 0001513856) on 2020-01-22 and "NextTrip, Inc."
(CIK 0000788611) on 2025-10-24 -- two different SEC registrants, and the active=true/false
enumeration for ticker=NTRP found only one candidate. The shortcut is unreliable and is not
used to skip per-event resolution here; it is retained only as a secondary diagnostic
(see shortcut_blind_spots in the summary) precisely so this discrepancy stays visible
rather than disappearing the way it did the first time.

Method (F1-T1a): every one of the 20,951 events queries
/v3/reference/tickers?ticker=X&date=event_date_canonical independently. F1-T1c's ambiguity
flag is then derived directly from this: group resolved CIKs by ticker, and if a ticker's
own events in this universe resolved to more than one distinct CIK, EVERY event on that
ticker is flagged resolved_ambiguous (with all distinct CIKs found recorded), not only the
ones that happen to sit on the "wrong" side of the split -- the whole point is that a
ticker carrying any recycling risk in this universe should not be treated as safely
resolved anywhere it appears.

SEC cross-check (F1-T1a): SEC's bulk company_tickers.json is a CURRENT snapshot only, not
historical, so it can only validate the current end of each ticker's history -- reported
as an agreement-rate diagnostic, not used to override the vendor resolution.

CIK stored zero-padded to 10 digits, as a string (F1-T1b) -- never as an integer.

Network use authorized by docs/Universe-Decisions.md D14 Amendment A1 (F1-T2's own
authorization; ticker reference/events endpoints are explicitly named in that scope).

Usage: .venv/Scripts/python.exe research/fundamentals_f1/t1_identity.py
"""
from __future__ import annotations

import json
import os
import sys
import time

import pandas as pd
import requests

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from research.fundamentals_f1 import common as C  # noqa: E402

UA = "Mom_db Research fundamentals_f1 (cleeming29@gmail.com)"
BASE_URL = "https://api.massive.com"
OUT_PARQUET = f"{C.ART}/ticker_identity.parquet"
ASOF_CACHE_PATH = f"{C.ART}/_t1_asof_cache.json"
SHORTCUT_CACHE_PATH = f"{C.ART}/_t1_ticker_candidates_cache.json"  # from the first (superseded) run
SUMMARY_PATH = f"{C.ART}/t1_identity_summary.json"


def _get(session, url, params, key, max_retries=5):
    for attempt in range(max_retries):
        try:
            r = session.get(url, params={**params, "apiKey": key}, timeout=30)
            if r.status_code == 401:
                raise SystemExit("AUTH FAILURE -- 401. Hard stop, no retry loop (escalation row 4).")
            if r.status_code != 200:
                time.sleep(2 ** attempt)
                continue
            return r.json()
        except requests.exceptions.RequestException:
            time.sleep(2 ** attempt)
    raise RuntimeError(f"failed after {max_retries} attempts: {url} {params}")


def load_universe() -> pd.DataFrame:
    df = pd.read_parquet(C.UNIVERSE_MATERIALIZATION_PATH, columns=["ticker", "event_date_canonical", "momentum_pct"])
    df["event_date_canonical"] = df["event_date_canonical"].astype(str)
    df["mp"] = df["momentum_pct"].round(2)
    assert len(df) == C.TARGET_ROW_COUNT
    return df[["ticker", "event_date_canonical", "mp"]]


def resolve_asof(session, ticker: str, date: str, key: str) -> dict | None:
    d = _get(session, f"{BASE_URL}/v3/reference/tickers", {"ticker": ticker, "date": date}, key)
    results = d.get("results", [])
    if not results or not results[0].get("cik"):
        return None
    return {"cik": results[0]["cik"], "name": results[0].get("name"), "active": results[0].get("active")}


def fetch_sec_ticker_map() -> dict:
    r = requests.get("https://www.sec.gov/files/company_tickers.json", headers={"User-Agent": UA}, timeout=60)
    r.raise_for_status()
    raw = r.json()
    return {v["ticker"]: str(v["cik_str"]).zfill(10) for v in raw.values()}


def main():
    key = C.load_massive_api_key()
    universe = load_universe()
    unique_tickers = sorted(universe["ticker"].unique())
    print(f"universe: {len(universe)} events, {len(unique_tickers)} unique tickers")

    session = requests.Session()

    # per-event as-of resolution, cached by (ticker, date) -- most tickers have events on
    # distinct dates, but a handful share (ticker, date) across two momentum_pct rows, so
    # caching on the pair rather than the full event key saves those duplicate calls.
    if os.path.exists(ASOF_CACHE_PATH):
        with open(ASOF_CACHE_PATH) as f:
            asof_cache = json.load(f)
        print(f"resumed as-of cache: {len(asof_cache)} (ticker, date) pairs")
    else:
        asof_cache = {}

    keys = universe[["ticker", "event_date_canonical"]].drop_duplicates()
    print(f"{len(keys)} distinct (ticker, date) pairs to resolve")
    for i, r in enumerate(keys.itertuples(index=False)):
        cache_key = f"{r.ticker}|{r.event_date_canonical}"
        if cache_key in asof_cache:
            continue
        result = resolve_asof(session, r.ticker, r.event_date_canonical, key)
        asof_cache[cache_key] = result
        if (i + 1) % 500 == 0:
            print(f"  as-of resolved: {i + 1}/{len(keys)}")
            C.write_json(ASOF_CACHE_PATH, asof_cache)
    C.write_json(ASOF_CACHE_PATH, asof_cache)

    # shortcut method's blind spots -- reported, not used, per the module docstring
    shortcut_blind_spots = {"available": False}
    if os.path.exists(SHORTCUT_CACHE_PATH):
        with open(SHORTCUT_CACHE_PATH) as f:
            shortcut = json.load(f)
        mismatches = []
        for ticker in unique_tickers:
            shortcut_ciks = {c["cik"] for c in shortcut.get(ticker, [])}
            asof_ciks = {asof_cache[f"{ticker}|{d}"]["cik"] for d in
                         universe.loc[universe.ticker == ticker, "event_date_canonical"].unique()
                         if asof_cache.get(f"{ticker}|{d}")}
            if asof_ciks - shortcut_ciks:
                mismatches.append({"ticker": ticker, "shortcut_found": sorted(shortcut_ciks),
                                    "asof_found_but_shortcut_missed": sorted(asof_ciks - shortcut_ciks)})
        shortcut_blind_spots = {
            "available": True,
            "n_tickers_where_shortcut_missed_a_cik": len(mismatches),
            "examples": mismatches[:20],
        }

    rows = []
    for r in universe.itertuples(index=False):
        result = asof_cache.get(f"{r.ticker}|{r.event_date_canonical}")
        rows.append({
            "ticker": r.ticker, "event_date_canonical": r.event_date_canonical, "mp": r.mp,
            "cik": result["cik"] if result else None,
            "asof_active": result["active"] if result else None,
        })
    spine = pd.DataFrame(rows)

    # F1-T1c: group by ticker, flag every event on a ticker whose OWN events in this
    # universe resolved to more than one distinct CIK.
    ticker_cik_sets = spine.groupby("ticker")["cik"].apply(lambda s: sorted(set(s.dropna())))
    ambiguous_tickers = {t for t, ciks in ticker_cik_sets.items() if len(ciks) > 1}

    def quality_and_candidates(row):
        if row["cik"] is None:
            return "unresolved", []
        if row["ticker"] in ambiguous_tickers:
            return "resolved_ambiguous", ticker_cik_sets[row["ticker"]]
        return "resolved_exact", [row["cik"]]

    qc = spine.apply(quality_and_candidates, axis=1, result_type="expand")
    spine["identity_quality"] = qc[0]
    spine["candidate_ciks"] = qc[1]

    # currently_delisted: the as-of resolution's own "active" flag at query time is not
    # "current" -- derive current status from a fresh active=true check per ticker instead.
    currently_delisted = {}
    for ticker in unique_tickers:
        d = _get(session, f"{BASE_URL}/v3/reference/tickers", {"ticker": ticker, "active": "true"}, key)
        currently_delisted[ticker] = len(d.get("results", [])) == 0
    spine["currently_delisted"] = spine["ticker"].map(currently_delisted)

    spine["cik"] = spine["cik"].apply(lambda c: str(c).zfill(10) if c else None)
    spine["candidate_ciks"] = spine["candidate_ciks"].apply(lambda lst: json.dumps([str(c).zfill(10) for c in lst]))
    spine["event_id"] = [
        C.event_id({"ticker": t, "event_date_canonical": d, "momentum_pct": m})
        for t, d, m in zip(spine["ticker"], spine["event_date_canonical"], spine["mp"])
    ]
    spine = spine.drop(columns=["asof_active"]).rename(columns={"mp": "momentum_pct"})

    assert len(spine) == C.TARGET_ROW_COUNT
    assert spine["event_id"].is_unique

    sec_map = fetch_sec_ticker_map()
    checkable = spine[spine["identity_quality"] != "unresolved"]
    in_sec = checkable[checkable["ticker"].isin(sec_map.keys())]
    agree = (in_sec["cik"] == in_sec["ticker"].map(sec_map)).sum()
    sec_cross_check = {
        "n_tickers_in_sec_current_map": int(in_sec["ticker"].nunique()),
        "n_events_checkable": int(len(in_sec)),
        "n_events_agree": int(agree),
        "agree_rate": float(agree / len(in_sec)) if len(in_sec) else None,
        "note": "SEC's company_tickers.json is a CURRENT snapshot only -- this validates the "
                "current end of each ticker's history, not historical point-in-time resolution.",
    }

    os.makedirs(C.ART, exist_ok=True)
    spine.to_parquet(OUT_PARQUET, index=False)

    quality_counts = spine["identity_quality"].value_counts().to_dict()
    by_year = spine.copy()
    by_year["year"] = by_year["event_date_canonical"].str[:4]
    year_table = by_year.groupby(["year", "identity_quality"]).size().unstack(fill_value=0)
    delisted_table = by_year.groupby(["currently_delisted", "identity_quality"], dropna=False).size().unstack(fill_value=0)

    summary = {
        "method": "per-event as-of resolution (corrected 2026-09-12 -- see module docstring)",
        "rows": len(spine),
        "unique_tickers": len(unique_tickers),
        "ambiguous_ticker_count": len(ambiguous_tickers),
        "ambiguous_tickers_sample": sorted(ambiguous_tickers)[:30],
        "identity_quality_counts": {str(k): int(v) for k, v in quality_counts.items()},
        "identity_quality_share": {str(k): float(v) / len(spine) for k, v in quality_counts.items()},
        "escalation_row_2_threshold": 0.05,
        "escalation_row_2_fires": (quality_counts.get("resolved_ambiguous", 0)
                                    + quality_counts.get("unresolved", 0)) / len(spine) > 0.05,
        "by_year": year_table.to_dict(orient="index"),
        "by_currently_delisted": {str(k): v for k, v in delisted_table.to_dict(orient="index").items()},
        "sec_cross_check": sec_cross_check,
        "shortcut_blind_spots": shortcut_blind_spots,
        "config_hash": C.cfg_hash(),
    }
    C.write_json(SUMMARY_PATH, summary)
    print(json.dumps({k: v for k, v in summary.items() if k != "by_year"}, indent=2))


if __name__ == "__main__":
    main()
