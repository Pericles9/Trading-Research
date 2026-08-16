"""Phase 11 shared helpers.

Standing constraints enforced structurally here:
  - The main DuckDB is ATTACHed READ_ONLY into an in-memory database, so no
    Phase 11 query can write to a pre-existing table or view (escalation row 14).
  - Session segmentation uses the pinned exchange_calendars XNYS calendar
    (CLAUDE.md standing rule; config/phase_11.json `environment`).
  - Nanosecond arithmetic stays on the raw BIGINT columns. make_timestamp_ns()
    truncates to microseconds, so it is used only for date / time-of-day
    assignment, never for resolution or gap measurement.
"""
from __future__ import annotations

import datetime as _dt
import json
import pathlib

import duckdb
import pandas as pd

REPO = pathlib.Path(__file__).resolve().parents[2]
DB = REPO / "data" / "duckdb" / "main.duckdb"
ARTIFACTS = REPO / "results" / "phase_11" / "artifacts"
CHARTS = REPO / "results" / "phase_11" / "charts"
CONFIG = json.loads((REPO / "config" / "phase_11.json").read_text())

# Extended-session bounds, ET. Matches the Phase 8/9 minute_index origin (04:00 ET).
EXT_OPEN = _dt.time(4, 0)
EXT_CLOSE = _dt.time(20, 0)


def connect() -> duckdb.DuckDBPyConnection:
    """In-memory DuckDB with the research database attached READ_ONLY."""
    con = duckdb.connect()
    con.execute(f"ATTACH '{DB}' AS mom (READ_ONLY)")
    # UTC nanoseconds -> naive ET timestamp. Microsecond truncation is acceptable
    # here because this macro is only ever used for date / time-of-day bucketing.
    con.execute(
        "CREATE MACRO et(ns) AS "
        "(make_timestamp_ns(ns) AT TIME ZONE 'UTC' AT TIME ZONE 'America/New_York')"
    )
    return con


def session_bounds(dates) -> pd.DataFrame:
    """XNYS regular open/close per session date, in naive ET.

    Half days are carried through as the calendar reports them; RTH is never
    assumed to be 09:30-16:00.
    """
    import exchange_calendars as xcals

    cal = xcals.get_calendar("XNYS")
    dates = sorted({pd.Timestamp(d).date() for d in dates})
    rows = []
    for d in dates:
        ts = pd.Timestamp(d)
        if not cal.is_session(ts):
            rows.append(
                {"session_date": d, "is_session": False, "rth_open": None, "rth_close": None}
            )
            continue
        o = cal.session_open(ts).tz_convert("America/New_York").tz_localize(None)
        c = cal.session_close(ts).tz_convert("America/New_York").tz_localize(None)
        rows.append({"session_date": d, "is_session": True, "rth_open": o, "rth_close": c})
    return pd.DataFrame(rows)


def primary_events(con) -> pd.DataFrame:
    """The 50 frozen dev-v4 primary events, with their source folder path."""
    df = con.execute(
        """
        SELECT ticker, event_date, ANY_VALUE(momentum_pct) AS momentum_pct, COUNT(*) AS n_quote_rows
        FROM mom.filtered_quotes_dev_v4
        WHERE dev_cohort = 'primary'
        GROUP BY 1, 2
        ORDER BY 1, 2
        """
    ).df()
    df["event_date"] = pd.to_datetime(df["event_date"]).dt.date
    folders = []
    for t, d, m in zip(df["ticker"], df["event_date"], df["momentum_pct"]):
        # Folder names carry momentum to 2dp, e.g. AACG_2020-02-18_40.86
        cands = list((REPO / "data" / "filtered").glob(f"{t}_{d}_*"))
        match = None
        for c in cands:
            try:
                if abs(float(c.name.rsplit("_", 1)[1]) - float(m)) < 0.005:
                    match = c
                    break
            except ValueError:
                continue
        folders.append(str(match) if match else None)
    df["folder"] = folders
    return df


def write_json(name: str, payload) -> pathlib.Path:
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    p = ARTIFACTS / name
    p.write_text(json.dumps(payload, indent=2, default=str))
    return p
