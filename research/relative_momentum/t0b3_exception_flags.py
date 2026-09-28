"""
R0-T0b (part 3): why the 12 in-scope-CLASS gate exceptions are not in_scope.

T0b part 2 left one row of its own table unresolved: 11 CS and 1 ADRC gate events sit on
the raw spine, carry an instrument class that IS in scope, and are still not in_scope.
This resolves each against the three flags that make up in_scope, so the exception table
has no residue.

in_scope (src/data/canonical.py, stage t6/t7/t8) is:
    ic.class IN ('common', 'common_adr')
    AND NOT flag_bad_denominator
    AND NOT flag_trades_mom_outlier
    AND NOT flag_missing_event_day

flag_bad_denominator is a formula over raw spine columns (prev_close < floor OR
momentum_pct >= cap; thresholds from config/phase_1b.json) and is recomputed here from
momentum_events. It is inside D4's momentum_pct exception per A9.1 -- it is a
denominator-reliability guard, not a measurement. The other two are read from
results/phase_1b/artifacts/event_flags.parquet, the same artifact the view reads.

Nothing is queried through momentum_events_canonical.

Usage: .venv/Scripts/python.exe research/relative_momentum/t0b3_exception_flags.py
"""
from __future__ import annotations

import json
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from research.relative_momentum import common as C  # noqa: E402
from src.data.canonical import (  # noqa: E402
    CLASSIFICATION_PATH, EVENT_FLAGS_PATH, IN_SCOPE_CLASSES, _load_thresholds,
)
from src.data.db import get_connection  # noqa: E402

OUT_JSON = f"{C.ART}/t0b3_exception_flags.json"
EXC = f"{C.ART}/t0b2_gate_exceptions.parquet"


def main() -> int:
    exc = pd.read_parquet(os.path.join(C.REPO, EXC))
    floor, cap = _load_thresholds()

    con = get_connection(read_only=True)
    spine = con.execute(
        "SELECT ticker, CAST(date AS VARCHAR) AS date, "
        "CAST(event_date AS VARCHAR) AS event_date, momentum_pct, prev_close "
        "FROM momentum_events"
    ).df()
    spine["event_date_canonical"] = (spine["date"].fillna(spine["event_date"])
                                     .str.slice(0, 10))
    spine["key"] = spine["ticker"] + "|" + spine["event_date_canonical"].fillna("None")
    spine["flag_bad_denominator"] = (
        (spine["prev_close"] < floor) | (spine["momentum_pct"] >= cap)
    )

    ef = pd.read_parquet(os.path.join(C.REPO, EVENT_FLAGS_PATH))
    ef["event_date_canonical"] = ef["event_date_canonical"].astype(str).str.slice(0, 10)
    ef["key"] = ef["ticker"] + "|" + ef["event_date_canonical"]

    cls = pd.read_parquet(os.path.join(C.REPO, CLASSIFICATION_PATH))
    ccol = "class" if "class" in cls.columns else cls.columns[-1]
    cls_map = dict(zip(cls["ticker"], cls[ccol]))

    j = exc.merge(
        spine[["key", "momentum_pct", "prev_close", "flag_bad_denominator"]]
        .drop_duplicates("key"), on="key", how="left")
    j = j.merge(
        ef[["key", "flag_trades_mom_outlier", "flag_missing_event_day"]]
        .drop_duplicates("key"), on="key", how="left")
    j["instrument_class"] = j["ticker"].map(cls_map)
    j["class_in_scope"] = j["instrument_class"].isin(IN_SCOPE_CLASSES)

    def reason(r) -> str:
        if not r["class_in_scope"]:
            return f"instrument_class_{r['instrument_class']}"
        parts = []
        if bool(r["flag_bad_denominator"]):
            parts.append("flag_bad_denominator")
        if bool(r["flag_trades_mom_outlier"]) is True:
            parts.append("flag_trades_mom_outlier")
        if bool(r["flag_missing_event_day"]) is True:
            parts.append("flag_missing_event_day")
        if pd.isna(r["momentum_pct"]):
            parts.append("no_matching_spine_row")
        return "+".join(parts) if parts else "UNRESOLVED"

    j["not_in_scope_reason"] = j.apply(reason, axis=1)
    in_class = j[j["class_in_scope"]].copy()

    summary = {
        "task": "R0-T0b (part 3) why the in-scope-class gate exceptions are not in_scope",
        "config_hash": C.cfg_hash(),
        "in_scope_formula": "class IN ('common','common_adr') AND NOT flag_bad_denominator "
                            "AND NOT flag_trades_mom_outlier AND NOT flag_missing_event_day "
                            "(src/data/canonical.py, stage t6/t7/t8)",
        "flag_bad_denominator_thresholds": {"prev_close_floor": floor, "mom_sanity_cap": cap,
                                            "source": "config/phase_1b.json"},
        "n_exceptions_total": int(len(j)),
        "n_excluded_by_instrument_class": int((~j["class_in_scope"]).sum()),
        "n_in_scope_class_but_not_in_scope": int(len(in_class)),
        "reason_counts_all": j.groupby("not_in_scope_reason").size().astype(int).to_dict(),
        "reason_counts_in_scope_class": in_class.groupby("not_in_scope_reason").size()
                                        .astype(int).to_dict(),
        "in_scope_class_rows": in_class[["ticker", "date", "instrument_class", "momentum_pct",
                                         "prev_close", "flag_bad_denominator",
                                         "flag_trades_mom_outlier", "flag_missing_event_day",
                                         "not_in_scope_reason"]]
                               .sort_values("ticker").to_dict("records"),
    }
    C.write_json(OUT_JSON, summary)
    print(json.dumps({k: v for k, v in summary.items() if k != "in_scope_class_rows"},
                     indent=2, default=str))
    print("\nin-scope-class exceptions:")
    print(pd.DataFrame(summary["in_scope_class_rows"]).to_string())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
