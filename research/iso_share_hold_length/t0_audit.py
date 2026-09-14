#!/usr/bin/env python
"""T0 -- audit: the entry-anchor window, exactly.

Two questions, both answered by inspection of the live schema and the
already-committed artifacts, not assumed:

1. Is `conditions` (the SIP condition-code list, needed for ISO share) present
   in the ingested DuckDB tables, or must it be read from raw per-event parquet?
2. What existing function/artifact converts a raw trade's `sip_timestamp` into
   "minutes since detection" for a given event, matching Phase 8/10e's own
   convention -- reused here, not redefined.

Finding, stated before this script exists so it can be checked rather than
taken on faith: `filtered_trades` / `filtered_trades_dev_v4` carry no
`conditions` column (dropped at ingestion) -- confirmed again below, live.
The detection anchor is `results/phase_8/artifacts/a102_detection_anchors.parquet`
(`det_minute`, a minute_index into `event_minute_bars_v2`'s T=0 scheme, per
(ticker, event_date_canonical, mp) -- `det_undefined` events, 394 of 15,763,
carry no anchor and are excluded exactly as `research/phase_10e/t1_candidate_entries.py`
does). `event_minute_bars_v2.first_trade_ts` / `.last_trade_ts` (epoch ns) give
the wall-clock bound of any minute_index, so the entry-anchor window
[T=0 session start, det_minute + 5min] resolves to a concrete [start_ns, end_ns]
pair per event without inventing a new anchor definition.

Read path for `conditions` itself: `research/phase_10/common.py`'s
`trade_files()` (base trades.parquet + Phase 1c repair siblings) for file
discovery -- reused as-is. Its own `read_event_trades()` does NOT request
`conditions` (only sip_timestamp/price/size/sequence_number), so T2 reads the
files directly with `columns=[...,"conditions"]`, mirroring
`research/scale_field/fragmentation_identity.py`'s `COLS`/`read_full()`
pattern rather than duplicating a second full read path.

Usage: .venv/Scripts/python.exe research/iso_share_hold_length/t0_audit.py
"""
from __future__ import annotations

import json
import os
import sys

import duckdb

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
DB = os.path.join(REPO, "data", "duckdb", "main.duckdb")
OUT = os.path.join(REPO, "results", "iso_share_hold_length", "artifacts", "t0_audit.json")

sys.path.insert(0, os.path.join(REPO, "research", "phase_10"))
import common  # noqa: E402


def main() -> int:
    con = duckdb.connect(DB, read_only=True)

    findings = {}

    # 1. conditions column, live check
    for tbl in ("filtered_trades", "filtered_trades_dev_v4"):
        cols = [r[0] for r in con.execute(f"DESCRIBE {tbl}").fetchall()]
        findings[f"conditions_in_{tbl}"] = "conditions" in cols
        findings[f"{tbl}_columns"] = cols

    # 2. det_minute anchor artifact -- shape and undefined count
    anch_path = os.path.join(REPO, "results", "phase_8", "artifacts",
                              "a102_detection_anchors.parquet")
    anch = con.execute(f"select * from read_parquet('{anch_path}')").df()
    findings["a102_detection_anchors_path"] = "results/phase_8/artifacts/a102_detection_anchors.parquet"
    findings["a102_n_events"] = int(len(anch))
    findings["a102_n_det_undefined"] = int(anch["det_undefined"].sum())
    findings["a102_columns"] = anch.columns.tolist()

    # 3. event_minute_bars_v2 carries first_trade_ts/last_trade_ts per minute_index
    con.execute(f"ATTACH '{DB}' AS m (READ_ONLY)")
    mb_cols = [r[0] for r in con.execute("DESCRIBE m.event_minute_bars_v2").fetchall()]
    findings["event_minute_bars_v2_has_trade_ts"] = (
        "first_trade_ts" in mb_cols and "last_trade_ts" in mb_cols
    )
    findings["event_minute_bars_v2_columns"] = mb_cols

    # 4. trade_files() / session_window() exist and are callable, reused not redefined
    findings["reused_functions"] = {
        "trade_files": "research/phase_10/common.py:trade_files",
        "session_window": "research/phase_10/common.py:session_window",
        "note": ("read_event_trades() in the same module does NOT request `conditions` -- "
                 "T2 reads trade_files()'s file list directly with an added `conditions` "
                 "column, per research/scale_field/fragmentation_identity.py's COLS pattern, "
                 "rather than extending or duplicating read_event_trades()."),
    }

    # 5. sanity: session_window() resolves for a known dev event (spot check, not a full pass)
    sw = common.session_window("2021-01-28", 0)
    findings["session_window_spot_check"] = {
        "event_date": "2021-01-28", "offset": 0,
        "resolved": sw is not None,
        "start_ns": sw["start_ns"] if sw else None,
        "end_ns": sw["end_ns"] if sw else None,
    }

    findings["window_definition"] = (
        "iso_share window = [session_window(event_date, 0)['start_ns'], "
        "last_trade_ts of event_minute_bars_v2 at minute_index = det_minute + 5]. "
        "Lower bound is T=0 extended-day session start (04:00 ET, D3); upper bound is the "
        "wall-clock end of the 5th minute bar after the detection anchor, read from the "
        "already-materialized minute cache rather than assumed from a fixed offset in "
        "seconds, since minute bars may be gappy (a bar with n_trades=0 still advances "
        "minute_index without advancing wall clock evenly)."
    )

    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(findings, fh, indent=2, default=str)

    print(f"conditions in filtered_trades:          {findings['conditions_in_filtered_trades']}")
    print(f"conditions in filtered_trades_dev_v4:   {findings['conditions_in_filtered_trades_dev_v4']}")
    print(f"a102 detection anchors: {findings['a102_n_events']} events, "
          f"{findings['a102_n_det_undefined']} det_undefined")
    print(f"event_minute_bars_v2 has trade_ts cols: {findings['event_minute_bars_v2_has_trade_ts']}")
    print(f"session_window() spot check resolved:   {findings['session_window_spot_check']['resolved']}")
    print(f"\nwrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
