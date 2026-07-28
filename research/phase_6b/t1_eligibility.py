"""
Phase 6b T1 - eligibility re-verification.

Re-verifies (does not re-derive) Phase 6 T1's result: D1 -> T=0-trades-
eligible via results/phase_6_rth_only/artifacts/t1_eligible_events.parquet
(the frozen output of that exact check).

A8.2/D4 rework (Amendment 8, 2026-07-28): the original T1 also ran a
`prev_close` guard (present and > 0) for the pre-D4 opportunity-decay anchor.
D4 quarantines `prev_close`; the anchor is now the tick-derived
`tick_close_t_minus_1_rth`, which cannot be checked here (it needs the T-1
bars from event_minute_bars_v2, built at T3). So T1 no longer reads any
spine column - it is pure D1 re-verification. The primary-anchor eligibility
(`has_t_minus_1_rth`) is determined at T4 from the bar cache, per-event,
flag-and-report (events without it are excluded from the primary decay
population only, retained for all other measurements).
"""
import json

import pandas as pd

PHASE_6B_CONFIG = "config/phase_6b.json"
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

    # Carry only the identity + bitmap columns forward - no spine numeric (D4).
    keep = [c for c in ["ticker", "event_date_canonical", "momentum_pct", "source_file",
                        "trades_bitmap", "quotes_bitmap"] if c in events.columns]
    events[keep].to_parquet(OUT_EVENTS, index=False)

    summary = {
        "phase": "6b", "task": "T1",
        "d1_reverify": {"expected": d1_expected, "observed": n_eligible, "pass": reverify_ok},
        "primary_anchor_eligibility_note": (
            "has_t_minus_1_rth (a T-1 premarket/rth session with >=1 trade, needed for the "
            "tick_close_t_minus_1_rth anchor) is determined at T4 from event_minute_bars_v2, "
            "not here - it needs the T-1 bars. Flag-and-report: events without it are excluded "
            "from the primary decay population only (approved Amendment 8)."
        ),
        "spine_numeric_reads": 0,
        "source": "research/phase_6b/t1_eligibility.py:main",
        "artifact": OUT_EVENTS,
    }
    with open(OUT_SUMMARY, "w") as f:
        json.dump(summary, f, indent=2, default=str)
    print(json.dumps(summary, indent=2, default=str))

    if not reverify_ok:
        print(f"\n*** WARNING: re-verified eligible count {n_eligible} != expected {d1_expected} ***")


if __name__ == "__main__":
    main()
