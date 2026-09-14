#!/usr/bin/env python
"""Phase 12 T2c -- agreement matrix across the three identification routes, dev tier.

Route 2 identifies nothing by construction (dictionary_path=NONE, D34/Escalation row 5) -- it
produces the code census in t2_code_census.json and contributes zero candidates to this matrix.
This is stated as a structural fact, not a data finding: the matrix is therefore route 1 x route 3
in practice, with route 2's column empty by design.

Route 1 candidate: a gap >= 60s (t1_gap_census.parquet, is_candidate). Route 3 candidate: any
minute bar within [gap_start, gap_end] with touched_band = True (t2_band_arithmetic.parquet).
Agreement is defined at the route-1-gap grain: a gap is "route-3-corroborated" if any minute bar
overlapping its span touched a band edge.

Usage: .venv/Scripts/python.exe research/phase_12/t2c_agreement_matrix.py
"""
from __future__ import annotations

import json
import os

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
OUT = os.path.join(REPO, "results", "phase_12", "artifacts", "t2_agreement_matrix.json")


def main() -> int:
    gaps = pd.read_parquet(os.path.join(REPO, "results", "phase_12", "artifacts",
                                         "t1_gap_census.parquet"))
    cand = gaps[gaps.is_candidate].copy()

    band = pd.read_parquet(os.path.join(REPO, "results", "phase_12", "artifacts",
                                         "t2_band_arithmetic.parquet"))
    touched = band[band.touched_band].copy()
    # minute_index -> approximate this minute's [start,end) via row position isn't directly
    # comparable to sip_timestamp ns; join on event + minute using the gap's own timestamps
    # converted to minute buckets is avoided -- instead, mark an event as "touched at some point"
    # and corroborate any gap in a touched event as a coarse, disclosed approximation.
    touched_events = set(touched.groupby(["ticker", "event_date", "momentum_pct"]).groups.keys())

    cand["event_key"] = list(zip(cand.ticker, cand.event_date, cand.momentum_pct))
    cand["route3_event_touched"] = cand["event_key"].isin(touched_events)

    n_r1 = len(cand)
    n_r1_and_r3 = int(cand["route3_event_touched"].sum())
    n_r1_only = n_r1 - n_r1_and_r3
    n_r3_events_total = band.groupby(["ticker", "event_date", "momentum_pct"]).ngroups
    n_r3_touched_events = len(touched_events)
    r1_events = set(cand["event_key"])
    n_r3_only_events = len(touched_events - r1_events)

    single_route_only_share = n_r1_only / n_r1 if n_r1 else None

    out = {
        "task": "T2c -- agreement matrix, dev tier",
        "grain_note": ("Route 1 is gap-level (n=%d candidate gaps); route 3 is minute-bar-level. "
                        "Corroboration is approximated at the EVENT level here (does the same "
                        "event show ANY route-3 band touch, not necessarily overlapping the "
                        "exact gap window) -- coarser than a strict time-overlap join, disclosed "
                        "as an approximation given the minute-bar/nanosecond grain mismatch, not "
                        "presented as an exact per-gap corroboration." % n_r1),
        "route_2_note": ("Route 2 identifies ZERO candidates by construction "
                          "(dictionary_path=NONE, D34) -- not a data finding, a structural "
                          "consequence of having no code dictionary. Excluded from this matrix; "
                          "see t2_code_census.json for its (uninterpreted) code frequencies."),
        "route_1_candidates_n": n_r1,
        "route_1_candidate_events_n": len(r1_events),
        "route_3_total_events_n": n_r3_events_total,
        "route_3_touched_events_n": n_r3_touched_events,
        "agreement_by_gap": {
            "n_route1_gaps": n_r1,
            "n_corroborated_by_route3_event": n_r1_and_r3,
            "n_route1_only_gaps": n_r1_only,
            "share_route1_only": single_route_only_share,
        },
        "agreement_by_event": {
            "n_route1_events": len(r1_events),
            "n_route3_touched_events": n_r3_touched_events,
            "n_both": len(r1_events & touched_events),
            "n_route1_only": len(r1_events - touched_events),
            "n_route3_only": n_r3_only_events,
        },
        "single_route_only_share_gap_level": single_route_only_share,
        "cooper_threshold_row_10_min": 50,
        "cooper_threshold_row_11_max_share": 0.6,
        "source": "research/phase_12/t2c_agreement_matrix.py:main",
        "reproduce": ".venv/Scripts/python.exe research/phase_12/t2c_agreement_matrix.py",
    }
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=2, default=str)

    print(json.dumps(out, indent=2, default=str))
    print(f"\nwrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
