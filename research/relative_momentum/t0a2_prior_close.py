"""
R0-T0a (part 2): the tick-derived prior session close, for all of D1.

This is the half of T0a the first pass deliberately did not run -- T0b was a stopping gate
and fired before it was needed. The 2026-09-18 erratum needs it: `move_at` cannot be built
without it.

CONSTRUCTION -- reused, not re-derived (reuse-before-build). The last RTH minute bar's
last_price on session_offset = -1, from event_minute_bars_v2. This is verbatim the
construction research/phase_12/t2b_band_arithmetic.py uses for LULD band arithmetic and
research/reg_sho_201/t1_trigger_check.py reuses for Rule 201's prior close, both of which
call it out as D4-safe. event_minute_bars_v2 is Phase 6b's extended-day tick aggregate
(45,925,350 rows); D5 Amendment A11 states reuse of that table needs no citation, and it
covers exactly the 15,763 (ticker, event_date_canonical) pairs that are D1.

DIVERGENCE FROM THE BRIEF'S LITERAL WORDING, recorded rather than silently taken. Brief
section I.2 specifies the closing print be "resolved by the two-rule condition-code fix on
{8, 15}" (Phase 10c Amendment 6's auction override, src/data/canonical-adjacent
research/phase_10c/common.py::assign_segment). event_minute_bars_v2 is Phase 6b output and
predates that amendment, so its `segment` is assigned on the timestamp rule alone. The
exposure is bounded and small: Amendment 6's own census puts the affected population at 291
near-close prints against 25.2M in the cohort, and this construction takes the last RTH
minute bar rather than a specific print, so an official cross print bucketed a few
microseconds into the next evening segment costs at most the difference between it and the
last in-range print of the same minute. Building the A6-exact version instead would mean a
fresh 15,763-folder tick pass over data/filtered. Reported as a named residual; say so if
the exact version is wanted.

D4: both inputs are tick-derived. No spine numeric column is read.

Usage: .venv/Scripts/python.exe research/relative_momentum/t0a2_prior_close.py
"""
from __future__ import annotations

import json
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from research.relative_momentum import common as C  # noqa: E402
from src.data.db import get_connection  # noqa: E402

OUT_JSON = f"{C.ART}/t0a2_prior_close.json"
OUT_PARQUET = f"{C.ART}/t0a2_prior_close.parquet"

SQL = """
SELECT ticker, CAST(event_date_canonical AS VARCHAR) AS event_date_canonical,
       momentum_pct,
       argMax(last_price, minute_index) AS prior_close,
       max(minute_index)                AS prior_close_minute_index,
       argMax(last_trade_ts, minute_index) AS prior_close_ts,
       count(*)                         AS n_prior_rth_bars
FROM event_minute_bars_v2
WHERE session_offset = -1 AND segment = 'rth' AND last_price IS NOT NULL
GROUP BY 1, 2, 3
"""


def main() -> int:
    d1 = C.load_d1()

    con = get_connection(read_only=True)
    pc = con.execute(SQL).df()
    pc["momentum_pct"] = pc["momentum_pct"].round(2)

    d1 = d1.copy()
    d1["momentum_pct"] = d1["momentum_pct"].round(2)
    j = d1.merge(pc, on=["ticker", "event_date_canonical", "momentum_pct"], how="left")
    assert len(j) == len(d1), "prior-close join changed the D1 row count"

    j["prior_close_available"] = j["prior_close"].notna() & (j["prior_close"] > 0)
    j[["event_id", "ticker", "event_date_canonical", "momentum_pct", "year",
       "prior_close", "prior_close_minute_index", "prior_close_ts", "n_prior_rth_bars",
       "prior_close_available"]].to_parquet(os.path.join(C.REPO, OUT_PARQUET), index=False)

    n = len(j)
    n_ok = int(j["prior_close_available"].sum())
    n_missing = n - n_ok
    n_nonpositive = int((j["prior_close"].notna() & (j["prior_close"] <= 0)).sum())

    checks = [
        {"name": "row_count_preserved", "pass": bool(len(j) == 15763),
         "n": len(j), "expected": 15763},
        {"name": "move_at_recompute_covers_full_D1",
         "pass": bool(n_missing == 0), "n_covered": n_ok, "n_not_covered": n_missing,
         "note": "brief T0a: 'Assert the move_at recompute covers the full D1 set; report as "
                 "a first-class number the events where the tick-derived prior close cannot "
                 "be built. Carried, never dropped.' The uncovered events are written to the "
                 "parquet with prior_close_available = FALSE, not filtered out."},
    ]

    by_year = j.groupby("year")["prior_close_available"].agg(["size", "sum"])
    by_year.columns = ["n_d1", "n_prior_close_available"]
    by_year["n_missing"] = by_year["n_d1"] - by_year["n_prior_close_available"]

    summary = {
        "task": "R0-T0a (part 2) tick-derived prior session close for D1",
        "config_hash": C.cfg_hash(),
        "construction": "last RTH minute bar's last_price at session_offset = -1, from "
                        "event_minute_bars_v2 (Phase 6b, tick-derived). Verbatim the "
                        "construction in research/phase_12/t2b_band_arithmetic.py and "
                        "research/reg_sho_201/t1_trigger_check.py.",
        "divergence_from_brief_I2": "brief I.2 specifies the Phase 10c Amendment 6 {8, 15} "
                                    "auction override on the closing print. event_minute_bars_v2 "
                                    "predates that amendment and segments on the timestamp rule "
                                    "alone. A6's own census bounds the affected population at 291 "
                                    "near-close prints against 25.2M; this takes the last RTH "
                                    "MINUTE BAR, not a specific print, so the residual is smaller "
                                    "still. The A6-exact alternative is a fresh 15,763-folder tick "
                                    "pass. Named residual, not a silent substitution.",
        "d4": "both inputs tick-derived; no spine numeric column read.",
        "n_d1": n,
        "n_prior_close_available": n_ok,
        "n_prior_close_unavailable": n_missing,
        "n_prior_close_nonpositive": n_nonpositive,
        "share_covered": n_ok / n,
        "by_year": by_year.astype(int).reset_index().to_dict("records"),
        "n_checks": len(checks), "n_fail": sum(1 for c in checks if not c["pass"]),
        "checks": checks,
        "output_parquet": OUT_PARQUET,
    }
    C.write_json(OUT_JSON, summary)
    print(json.dumps(summary, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
