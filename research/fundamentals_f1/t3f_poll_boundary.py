"""
Build F1, F1-T3f: the poll-boundary filing count.

D7 makes detection a family indexed by polling interval -- a filing landing inside the
window between the instantaneous crossing (t0_ns, for the nanosecond_poll1 tier only) and
the 60-second coarser poll boundary means filing proximity is itself a family, not a
scalar. Answerable only for the nanosecond_poll1 tier (110 events) per D33 -- the other two
t0 tiers (minute_a102, first_trade_fallback) do not carry instantaneous-crossing precision,
so this task reports that limitation explicitly rather than extrapolating from a coarser
tier. Offline -- reads sec_filings.parquet (F1-T3) and t0_spine.parquet (F1-PF5), no network
call of its own.

Escalation row 6: if the count is zero, that's a sentence in the digest and the question is
closed for this tier. If it is not zero, stop and post -- it needs a decision, not a default.

Usage: .venv/Scripts/python.exe research/fundamentals_f1/t3f_poll_boundary.py
"""
from __future__ import annotations

import json
import os
import sys

import duckdb
import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from research.fundamentals_f1 import common as C  # noqa: E402

OUT_PATH = f"{C.ART}/t3f_poll_boundary_summary.json"
POLL_BOUNDARY_NS = 60 * 1_000_000_000  # 60 seconds


def main():
    t0_spine = pd.read_parquet(f"{C.ART}/t0_spine.parquet")
    identity = pd.read_parquet(f"{C.ART}/ticker_identity.parquet")[["event_id", "cik"]]
    filings = pd.read_parquet(f"{C.ART}/sec_filings.parquet")

    tier1 = t0_spine[t0_spine["t0_source"] == "nanosecond_poll1"][["event_id", "t0_ns"]].merge(
        identity, on="event_id", how="left"
    )
    assert len(tier1) == 110, f"expected 110 nanosecond_poll1 events, got {len(tier1)}"
    n_unresolved = tier1["cik"].isna().sum()

    con = duckdb.connect()
    con.register("tier1", tier1)
    con.register("filings", filings)
    hits = con.execute(f"""
        SELECT t.event_id, t.t0_ns, f.accession, f.form_type, f.accepted_ns,
               (f.accepted_ns - t.t0_ns) AS ns_after_t0
        FROM tier1 t
        JOIN filings f ON t.cik = f.cik
          AND f.accepted_ns > t.t0_ns
          AND f.accepted_ns <= t.t0_ns + {POLL_BOUNDARY_NS}
    """).df()

    fires = len(hits) > 0
    summary = {
        "tier": "nanosecond_poll1",
        "n_events_in_tier": 110,
        "n_unresolved_identity_in_tier": int(n_unresolved),
        "poll_boundary_seconds": 60,
        "n_filings_in_poll_boundary_window": len(hits),
        "escalation_row_6_fires": fires,
        "hits": hits.to_dict(orient="records") if fires else [],
        "other_tiers_note": (
            "minute_a102 (15,259 events) and first_trade_fallback (5,582 events) do not carry "
            "instantaneous-crossing precision (D33) and this question is not measurable for them "
            "at the required precision -- reported as a limitation, not extrapolated."
        ),
        "config_hash": C.cfg_hash(),
    }
    C.write_json(OUT_PATH, summary)
    print(json.dumps({k: v for k, v in summary.items() if k != "hits"}, indent=2, default=str))
    if fires:
        print("\n*** ESCALATION ROW 6 FIRES -- stop and post. Not a default. ***")
    else:
        print("\nescalation row 6 does not fire (count is zero). Closed for this tier.")


if __name__ == "__main__":
    main()
