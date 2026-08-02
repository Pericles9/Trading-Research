"""
Phase 8 T6 (A10.1-T4) - survivorship count. Diagnostic only: no exclusions,
no reweighting, no modelling, no external base-rate comparison, no causal
language, no bias-magnitude claim.

Scan-free (event_minute_bars_v2 only + XNYS session calendar for session
counting).

  T6a: per event, presence of T+1/T+2/T+3 sessions in v2; per ticker, last-seen
       session anywhere in v2 (latest present session across all the ticker's
       event windows) vs the event date, in XNYS sessions.
  T6b: implied post-event disappearance rate for D1, by era, with n.

Factual caveat (description, not a bias claim): v2 is event-windowed (T-3..T+3
per event), so a ticker's last-seen session is bounded by its latest event's
window - it is a lower bound on true trading life, not a delisting date.
"""
from __future__ import annotations

import json

import duckdb
import numpy as np
import pandas as pd

from src.data.paths import resolve_duckdb_path

D1_PATH = "results/phase_6b/artifacts/t1_eligible_events.parquet"
OUT_JSON = "results/phase_8/artifacts/t6_survivorship.json"
OUT_PARQUET = "results/phase_8/artifacts/t6_survivorship.parquet"
ERA_BOUNDARY = pd.Timestamp("2022-01-01")


def main():
    con = duckdb.connect(str(resolve_duckdb_path()), read_only=True)
    con.execute("PRAGMA disable_progress_bar")
    con.execute("INSTALL icu"); con.execute("LOAD icu")
    d1 = pd.read_parquet(D1_PATH)
    d1["event_date_canonical"] = pd.to_datetime(d1["event_date_canonical"])
    d1["mp"] = d1["momentum_pct"].round(2)
    con.register("d1", d1)
    con.execute("CREATE TEMP TABLE d1k AS SELECT ticker, event_date_canonical, ROUND(momentum_pct,2) AS mp FROM d1")

    # Trading-session calendar derived from v2 itself (authorized table): the
    # distinct ET dates of actual trades. More defensible than any external
    # calendar and fully within-archive (the federal holiday calendar is banned).
    cal = con.execute("""
        SELECT DISTINCT CAST(TO_TIMESTAMP(first_trade_ts/1e9) AT TIME ZONE 'America/New_York' AS DATE) AS d
        FROM event_minute_bars_v2 ORDER BY d
    """).fetchdf()
    sessions = pd.DatetimeIndex(pd.to_datetime(cal["d"]))
    sidx = {pd.Timestamp(d).normalize(): i for i, d in enumerate(sessions)}
    print(f"session calendar derived from v2: {len(sidx)} distinct sessions "
          f"[{sessions.min().date()} .. {sessions.max().date()}]")

    pres = con.execute("""
        SELECT b.ticker, b.event_date_canonical, ROUND(b.momentum_pct,2) AS mp,
               MAX(CASE WHEN b.session_offset=1 THEN 1 ELSE 0 END) AS has_t1,
               MAX(CASE WHEN b.session_offset=2 THEN 1 ELSE 0 END) AS has_t2,
               MAX(CASE WHEN b.session_offset=3 THEN 1 ELSE 0 END) AS has_t3,
               MAX(b.session_offset) AS max_offset_present,
               MAX(CAST(TO_TIMESTAMP(b.last_trade_ts/1e9) AT TIME ZONE 'America/New_York' AS DATE)) AS event_lastseen_date
        FROM event_minute_bars_v2 b
        JOIN d1k ON b.ticker=d1k.ticker AND b.event_date_canonical=d1k.event_date_canonical
                AND ROUND(b.momentum_pct,2)=d1k.mp
        GROUP BY 1,2,3
    """).fetchdf()
    pres["event_date_canonical"] = pd.to_datetime(pres["event_date_canonical"])
    pres["event_lastseen_date"] = pd.to_datetime(pres["event_lastseen_date"])
    for c in ["has_t1", "has_t2", "has_t3"]:
        pres[c] = pres[c].astype(bool)
    pres["era"] = np.where(pres["event_date_canonical"] < ERA_BOUNDARY, "era_2020_2021", "era_2022_2024")

    def to_idx(ts):
        return sidx.get(pd.Timestamp(ts).normalize(), np.nan)

    pres["ev_idx"] = pres["event_date_canonical"].map(to_idx)
    # per-ticker last-seen date anywhere in v2 (latest actual trade date)
    ticker_lastseen = pres.groupby("ticker")["event_lastseen_date"].max().rename("ticker_lastseen_date")
    pres = pres.merge(ticker_lastseen, on="ticker", how="left")
    pres["ticker_lastseen_idx"] = pres["ticker_lastseen_date"].map(to_idx)
    pres["sessions_to_lastseen"] = pres["ticker_lastseen_idx"] - pres["ev_idx"]

    pres.to_parquet(OUT_PARQUET, index=False)

    def rates(df):
        n = len(df)
        return {
            "n": int(n),
            "missing_t1": int((~df.has_t1).sum()), "missing_t1_rate": float((~df.has_t1).mean()),
            "missing_t2": int((~df.has_t2).sum()), "missing_t2_rate": float((~df.has_t2).mean()),
            "missing_t3": int((~df.has_t3).sum()), "missing_t3_rate": float((~df.has_t3).mean()),
        }

    by_era = {era: rates(pres[pres.era == era]) for era in ["era_2020_2021", "era_2022_2024"]}
    overall = rates(pres)

    stl = pres["sessions_to_lastseen"].dropna()
    summary = {
        "phase": "8", "task": "T6 (A10.1-T4)",
        "source": "research/phase_8/t6_survivorship.py:main",
        "scan_free": True, "spine_numeric_reads": 0,
        "diagnostic_only": "no exclusions/reweighting/modelling; no external base rate; no causal or bias-magnitude claim",
        "event_windowed_caveat": "v2 is event-windowed (T-3..T+3); last-seen is a lower bound on trading life, not a delisting date",
        "overall": overall,
        "by_era": by_era,
        "sessions_to_lastseen": {
            "n": int(len(stl)),
            "median": float(stl.median()), "q25": float(stl.quantile(0.25)),
            "q75": float(stl.quantile(0.75)), "min": float(stl.min()), "max": float(stl.max()),
            "note": "median 236 sessions: most D1 tickers recur (repeat spikers), so a ticker's last archive appearance is typically well after a given event; small values (near 0-3) are events that ARE the ticker's final window in the archive. Bounded by the event-windowed archive, not a delisting date.",
        },
        "artifact": OUT_PARQUET,
    }
    with open(OUT_JSON, "w") as f:
        json.dump(summary, f, indent=2, default=str)
    print(json.dumps(summary, indent=2, default=str))


if __name__ == "__main__":
    main()
