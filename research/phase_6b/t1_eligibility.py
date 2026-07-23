"""
Phase 6b T1 - eligibility re-verification + prev_close guard.

Re-verifies (does not re-derive) Phase 6 T1's result: D1 -> T=0-trades-
eligible via results/phase_6_rth_only/artifacts/t1_eligible_events.parquet
(the frozen output of that exact check). Adds the new guard this phase's
primary opportunity-decay anchor needs: prev_close present and > 0 for
every eligible event, joined from momentum_events (the raw table - prev_close
is not exposed on momentum_events_canonical).
"""
import json

import duckdb
import pandas as pd

PHASE_6B_CONFIG = "config/phase_6b.json"
DB_PATH = "data/duckdb/main.duckdb"
PHASE_6_ELIGIBLE = "results/phase_6_rth_only/artifacts/t1_eligible_events.parquet"
OUT_SUMMARY = "results/phase_6b/artifacts/t1_eligibility.json"
OUT_EVENTS = "results/phase_6b/artifacts/t1_eligible_events.parquet"


def main():
    with open(PHASE_6B_CONFIG) as f:
        cfg = json.load(f)
    d1_expected = cfg["universe"]["expected_n"]

    events = pd.read_parquet(PHASE_6_ELIGIBLE)
    n_eligible = len(events)
    reverify_ok = n_eligible == d1_expected
    print(f"re-verified eligible events from Phase 6 T1: {n_eligible} (expected {d1_expected})")

    con = duckdb.connect(DB_PATH, read_only=True)
    pc = con.execute("""
        SELECT ticker, COALESCE(date, event_date) AS event_date_canonical, ROUND(momentum_pct, 2) AS mom_2dp, prev_close
        FROM momentum_events
    """).fetchdf()
    con.close()
    pc["event_date_canonical"] = pd.to_datetime(pc["event_date_canonical"])

    ev = events.copy()
    ev["event_date_canonical"] = pd.to_datetime(ev["event_date_canonical"])
    ev["mom_2dp"] = ev["momentum_pct"].round(2)
    merged = ev.merge(pc, on=["ticker", "event_date_canonical", "mom_2dp"], how="left")

    n_missing_prev_close = int(merged["prev_close"].isna().sum())
    n_nonpositive_prev_close = int((merged["prev_close"] <= 0).sum())
    n_prev_close_failures = n_missing_prev_close + n_nonpositive_prev_close
    pct_failures = 100.0 * n_prev_close_failures / n_eligible

    merged[["ticker", "event_date_canonical", "momentum_pct", "source_file", "trades_bitmap", "quotes_bitmap", "prev_close"]].to_parquet(OUT_EVENTS, index=False)

    row5_triggered = n_prev_close_failures > 0
    summary = {
        "phase": "6b", "task": "T1",
        "d1_reverify": {"expected": d1_expected, "observed": n_eligible, "pass": reverify_ok},
        "prev_close_guard": {
            "n_eligible": n_eligible,
            "n_missing": n_missing_prev_close,
            "n_nonpositive": n_nonpositive_prev_close,
            "n_failures": n_prev_close_failures,
            "pct_failures": round(pct_failures, 4),
            "pass": not row5_triggered,
        },
        "escalation_row5_triggered": row5_triggered,
        "source": "research/phase_6b/t1_eligibility.py:main",
        "artifact": OUT_EVENTS,
    }
    with open(OUT_SUMMARY, "w") as f:
        json.dump(summary, f, indent=2, default=str)
    print(json.dumps(summary, indent=2, default=str))

    if not reverify_ok:
        print(f"\n*** WARNING: re-verified eligible count {n_eligible} != expected {d1_expected} ***")
    if row5_triggered:
        print(f"\n*** ESCALATION row 5: {n_prev_close_failures} prev_close failure(s) ({pct_failures:.4f}%) - HARD STOP ***")


if __name__ == "__main__":
    main()
