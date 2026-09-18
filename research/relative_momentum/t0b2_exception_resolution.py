"""
R0-T0b (part 2): resolve the gate-side exceptions against the canonical spine.

T0b's headline is a pair of counts. This resolves the smaller side of it -- the
(ticker, date) the participation gate was run on that are NOT in D1 -- so that
"39 events outside D1" is a described population rather than a residue.

Each exception is classified against, in order:
  1. the in_scope materialization (results/phase_5/artifacts/quotes_bitmaps_all.parquet)
     -> in_scope but source_file = 'file2'
  2. the raw spine table momentum_events -> on the spine but not in_scope
  3. neither -> not on the spine at all
and, where the spine has it, against the Phase 1b instrument classification
(results/phase_1b/artifacts/ticker_reference_snapshot.parquet), the classification
source of record per CLAUDE.md.

momentum_events is queried directly, NOT through momentum_events_canonical: the view
joins filtered_trades/filtered_quotes unconditionally and any query against it scans
both (research/fundamentals_f1/verify_event_fundamentals.py, 2026-09-12; confirmed
again in this run).

Usage: .venv/Scripts/python.exe research/relative_momentum/t0b2_exception_resolution.py
"""
from __future__ import annotations

import json
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from research.relative_momentum import common as C  # noqa: E402
from src.data.db import get_connection  # noqa: E402

OUT_JSON = f"{C.ART}/t0b2_exception_resolution.json"
OUT_PARQUET = f"{C.ART}/t0b2_gate_exceptions.parquet"
CLASSIFICATION = "results/phase_1b/artifacts/ticker_reference_snapshot.parquet"


def main() -> int:
    universe = C.load_universe()
    d1 = C.load_d1()
    runs = C.gate_run_events()
    runs["key"] = runs["ticker"].astype(str) + "|" + runs["date"].astype(str)

    d1_keys = set(d1["ticker"] + "|" + d1["event_date_canonical"])
    u_keys = {}
    for t, dt, sf in zip(universe["ticker"], universe["event_date_canonical"],
                         universe["source_file"]):
        u_keys[f"{t}|{dt}"] = sf

    gate = (runs[["ticker", "date", "key"]].drop_duplicates("key")
            .reset_index(drop=True))
    gate["in_d1"] = gate["key"].isin(d1_keys)
    exc = gate[~gate["in_d1"]].copy()

    # ---- spine lookup (raw table, not the view) ---------------------------
    con = get_connection(read_only=True)
    # momentum_events carries no source_file column; `date` is structurally NULL for
    # every file2 row and `event_date` is the file2-side date, so the raw-spine key is
    # built off both rather than off `date` alone.
    spine = con.execute(
        "SELECT ticker, CAST(date AS VARCHAR) AS date, "
        "CAST(event_date AS VARCHAR) AS event_date, momentum_pct FROM momentum_events"
    ).df()
    n_spine = len(spine)
    spine_date = spine["date"].fillna(spine["event_date"]).fillna("None").str.slice(0, 10)
    spine_keys = set(spine["ticker"] + "|" + spine_date)
    spine_by_ticker = set(spine["ticker"])

    # file2 rows have a structurally NULL date (CLAUDE.md universe rules), so the
    # (ticker, date) key cannot resolve them on the raw spine. The in_scope
    # materialization carries event_date_canonical and is the right lookup there.
    exc["in_scope_source_file"] = exc["key"].map(u_keys)

    def classify(row) -> str:
        if pd.notna(row["in_scope_source_file"]):
            return f"in_scope_but_source_file_{row['in_scope_source_file']}"
        if row["key"] in spine_keys:
            return "on_raw_spine_but_not_in_scope"
        if row["ticker"] in spine_by_ticker:
            return "ticker_on_spine_but_this_session_is_not"
        return "ticker_not_on_spine_at_all"

    exc["resolution"] = exc.apply(classify, axis=1)

    # ---- instrument classification ---------------------------------------
    cls_path = os.path.join(C.REPO, CLASSIFICATION)
    if os.path.exists(cls_path):
        cls = pd.read_parquet(cls_path)
        tcol = "ticker" if "ticker" in cls.columns else cls.columns[0]
        typecol = next((c for c in cls.columns
                        if c.lower() in ("type", "vendor_type", "instrument_class")), None)
        cmap = dict(zip(cls[tcol], cls[typecol])) if typecol else {}
        exc["vendor_type"] = exc["ticker"].map(cmap)
        cls_available = True
        cls_cols = list(cls.columns)
    else:
        exc["vendor_type"] = pd.NA
        cls_available = False
        cls_cols = []

    exc.to_parquet(os.path.join(C.REPO, OUT_PARQUET), index=False)

    res_counts = exc.groupby("resolution").size().astype(int).to_dict()
    type_counts = (exc.groupby(exc["vendor_type"].fillna("unresolved_ticker")).size()
                   .astype(int).to_dict())

    summary = {
        "task": "R0-T0b (part 2) gate-side exception resolution",
        "config_hash": C.cfg_hash(),
        "n_gate_run_events": int(len(gate)),
        "n_inside_D1": int(gate["in_d1"].sum()),
        "n_outside_D1": int(len(exc)),
        "resolution_counts": res_counts,
        "vendor_type_counts": type_counts,
        "classification_source": CLASSIFICATION if cls_available else None,
        "classification_columns": cls_cols,
        "classification_note": "CLAUDE.md: classification source of record is the Phase 1b "
                               "ticker_reference_snapshot; the API is never re-queried for "
                               "classification.",
        "raw_spine_rows": int(n_spine),
        "raw_spine_note": "momentum_events queried directly. file2 rows carry a structurally NULL "
                          "date, so (ticker, date) cannot resolve them on the raw spine -- the "
                          "in_scope materialization (which carries event_date_canonical) is the "
                          "lookup used for those.",
        "exceptions": exc[["ticker", "date", "resolution", "vendor_type"]]
                      .sort_values(["resolution", "ticker"]).to_dict("records"),
        "output_parquet": OUT_PARQUET,
    }
    C.write_json(OUT_JSON, summary)
    print(json.dumps({k: v for k, v in summary.items() if k != "exceptions"},
                     indent=2, default=str))
    print("\nexceptions:")
    print(pd.DataFrame(summary["exceptions"]).to_string())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
