"""
R0-T0a (part 1): the D1 population, in code, with an asserted count.

Part 2 of T0a -- the move_at prior-close coverage assert -- is t0a2_prior_close.py.
It is deliberately NOT run before T0b: T0b is a stopping gate (brief section I.1) and
the prior-close recompute is a 15,763-event pass over data/filtered. Running the
expensive half before the gate that may stop the brief would be work spent on a
question that may not survive.

Usage: .venv/Scripts/python.exe research/relative_momentum/t0a_population.py
"""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from research.relative_momentum import common as C  # noqa: E402

OUT = f"{C.ART}/t0a_population.json"


def main() -> int:
    cfg = C.load_cfg()
    universe = C.load_universe()
    d1 = C.load_d1()

    checks = []

    checks.append({
        "name": "in_scope_universe_row_count",
        "pass": bool(len(universe) == 20951),
        "n": len(universe), "expected": 20951,
        "note": "results/phase_5/artifacts/quotes_bitmaps_all.parquet is D15's materialization "
                "of momentum_events_canonical WHERE in_scope = TRUE.",
    })

    exp = cfg["universe"]["expected_row_count"]
    checks.append({
        "name": "d1_row_count",
        "pass": bool(len(d1) == exp),
        "n": len(d1), "expected": exp,
        "rule": cfg["universe"]["membership_rule"],
    })

    checks.append({
        "name": "d1_event_id_unique",
        "pass": bool(d1["event_id"].is_unique),
        "n_rows": len(d1), "n_unique": int(d1["event_id"].nunique()),
    })

    checks.append({
        "name": "d1_ticker_date_unique",
        "pass": bool(not d1.duplicated(["ticker", "event_date_canonical"]).any()),
        "n_dup_ticker_date": int(d1.duplicated(["ticker", "event_date_canonical"]).sum()),
        "note": "Whether (ticker, date) alone is a key matters for T0b: the gate's own event "
                "identity is the folder name (ticker, date, mom_pct) and its result files carry "
                "only (ticker, date).",
    })

    by_source = universe.groupby("source_file").size().to_dict()
    by_year = d1.groupby("year").size().to_dict()

    n_fail = sum(1 for c in checks if not c["pass"])
    summary = {
        "task": "R0-T0a (part 1) D1 population",
        "config_hash": C.cfg_hash(),
        "n_checks": len(checks), "n_fail": n_fail, "checks": checks,
        "in_scope_by_source_file": {k: int(v) for k, v in by_source.items()},
        "d1_by_year": {k: int(v) for k, v in by_year.items()},
        "d1_date_min": d1["event_date_canonical"].min(),
        "d1_date_max": d1["event_date_canonical"].max(),
        "d1_n_distinct_tickers": int(d1["ticker"].nunique()),
        "d1_n_distinct_session_dates": int(d1["event_date_canonical"].nunique()),
    }
    C.write_json(OUT, summary)
    print(json.dumps(summary, indent=2, default=str))
    return 1 if n_fail else 0


if __name__ == "__main__":
    raise SystemExit(main())
