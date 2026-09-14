#!/usr/bin/env python
"""Phase 12 T1 -- route 1: tape gaps, dev tier.

T1a: per dev event, on the T=0 RTH segment, enumerate every inter-print gap in sip_timestamp,
carrying gap start/end, duration, last price before, first price after. Gaps with no resuming
print (the tail from the last trade to the RTH close) are recorded separately, per
config.route_1_tape_gaps.resumption_note -- they are a session-end/delisting signature, not a
halt candidate.

INTERPRETATION CHOICE, stated because the prompt's T1a and T1b read as if in tension: T1a says
"enumerate gaps... of length >= gap_threshold_seconds"; T1b says "report the distribution BEFORE
applying any threshold." Resolved by enumerating EVERY inter-print gap regardless of size and
carrying gap_threshold_seconds only as an `is_candidate` flag on top of the full distribution --
this is the only reading under which T1b's own distribution has anything to show.

Two-tier discipline (CLAUDE.md): dev tier only. Full-tier promotion is a separate, later decision,
not assumed here.

Usage: .venv/Scripts/python.exe research/phase_12/t1_gap_census.py
"""
from __future__ import annotations

import json
import os
import sys

import duckdb
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
DB = os.path.join(REPO, "data", "duckdb", "main.duckdb")
OUT_JSON = os.path.join(REPO, "results", "phase_12", "artifacts", "t1_gap_census.json")
OUT_PARQUET = os.path.join(REPO, "results", "phase_12", "artifacts", "t1_gap_census.parquet")
GAP_THRESHOLD_S = 60  # config.route_1_tape_gaps.gap_threshold_seconds

sys.path.insert(0, os.path.join(REPO, "research", "phase_10"))
import common  # noqa: E402


def main() -> int:
    cfg = json.load(open(os.path.join(REPO, "config", "phase_10.json"), encoding="utf-8"))
    con = duckdb.connect(DB, read_only=True)
    events = con.execute("""
        select distinct ticker, event_date, momentum_pct
        from filtered_trades_dev_v4
        order by 1, 2
    """).df()

    gap_rows = []
    event_summaries = []

    for r in events.itertuples(index=False):
        date_str = pd.Timestamp(r.event_date).strftime("%Y-%m-%d")
        files = common.trade_files(cfg, r.ticker, date_str, r.momentum_pct)
        if not files:
            event_summaries.append({"ticker": r.ticker, "event_date": date_str,
                                     "momentum_pct": r.momentum_pct, "status": "no_trade_files"})
            continue

        sw = common.session_window(date_str, 0)
        if sw is None:
            event_summaries.append({"ticker": r.ticker, "event_date": date_str,
                                     "momentum_pct": r.momentum_pct, "status": "no_session_window"})
            continue
        rth_open_ns, rth_close_ns = sw["rth_open_ns"], sw["rth_close_ns"]

        cols = ["sip_timestamp", "price", "sequence_number"]
        frames = [pd.read_parquet(f, columns=cols) for f in files]
        df = pd.concat(frames, ignore_index=True) if len(frames) > 1 else frames[0]
        rth = df[(df.sip_timestamp >= rth_open_ns) & (df.sip_timestamp <= rth_close_ns)]
        rth = rth.sort_values(["sip_timestamp", "sequence_number"]).reset_index(drop=True)

        n_prints = len(rth)
        if n_prints == 0:
            event_summaries.append({"ticker": r.ticker, "event_date": date_str,
                                     "momentum_pct": r.momentum_pct, "status": "no_rth_prints"})
            continue

        ts = rth["sip_timestamp"].to_numpy()
        px = rth["price"].to_numpy()
        n_gaps_this_event = 0
        for i in range(1, n_prints):
            dur_s = (ts[i] - ts[i - 1]) / 1e9
            if dur_s <= 0:
                continue
            gap_rows.append({
                "ticker": r.ticker, "event_date": date_str, "momentum_pct": r.momentum_pct,
                "gap_start_ns": int(ts[i - 1]), "gap_end_ns": int(ts[i]),
                "duration_s": float(dur_s),
                "last_price_before": float(px[i - 1]), "first_price_after": float(px[i]),
                "is_candidate": bool(dur_s >= GAP_THRESHOLD_S),
                "has_resumption": True,
            })
            n_gaps_this_event += 1

        trailing_s = (rth_close_ns - ts[-1]) / 1e9
        event_summaries.append({
            "ticker": r.ticker, "event_date": date_str, "momentum_pct": r.momentum_pct,
            "status": "ok", "n_rth_prints": n_prints, "n_gaps": n_gaps_this_event,
            "trailing_gap_to_close_s": float(trailing_s),
            "trailing_has_resumption": False,
        })

    gaps = pd.DataFrame(gap_rows)
    gaps.to_parquet(OUT_PARQUET, index=False)

    n_events = len(events)
    ok_events = [e for e in event_summaries if e["status"] == "ok"]
    n_candidates = int(gaps["is_candidate"].sum()) if len(gaps) else 0

    dist = {}
    if len(gaps):
        d = gaps["duration_s"]
        dist = {
            "n_gaps_total": int(len(gaps)),
            "n_candidates_ge_threshold": n_candidates,
            "share_candidates": float(n_candidates / len(gaps)),
            "p50": float(d.quantile(.5)), "p75": float(d.quantile(.75)),
            "p90": float(d.quantile(.9)), "p95": float(d.quantile(.95)),
            "p99": float(d.quantile(.99)), "max": float(d.max()), "min": float(d.min()),
        }

    trailing = [e["trailing_gap_to_close_s"] for e in ok_events]
    summary = {
        "task": "T1 -- route 1 tape gap census, dev tier",
        "tier": "dev (56 events, all cohorts)",
        "gap_threshold_seconds_config": GAP_THRESHOLD_S,
        "interpretation_note": ("Every inter-print RTH gap is enumerated regardless of size; "
                                 "is_candidate flags duration_s >= gap_threshold_seconds on top "
                                 "of the full distribution, per this script's own docstring."),
        "n_events": n_events,
        "n_events_ok": len(ok_events),
        "status_counts": pd.Series([e["status"] for e in event_summaries]).value_counts().to_dict(),
        "gap_distribution": dist,
        "trailing_gap_to_close_s_summary": {
            "n": len(trailing),
            "median": float(pd.Series(trailing).median()) if trailing else None,
            "max": float(pd.Series(trailing).max()) if trailing else None,
            "note": ("Trailing gaps (last print to RTH close) are NOT candidates -- "
                     "config.route_1_tape_gaps.resumption_note: no resumption means session "
                     "end or delisting, not a halt."),
        },
        "source": "research/phase_12/t1_gap_census.py:main",
        "reproduce": ".venv/Scripts/python.exe research/phase_12/t1_gap_census.py",
    }
    with open(OUT_JSON, "w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=2, default=str)

    print(f"n_events={n_events}  n_ok={len(ok_events)}")
    print("status counts:", summary["status_counts"])
    print("gap distribution:", json.dumps(dist, indent=2))
    print("trailing gap summary:", json.dumps(summary["trailing_gap_to_close_s_summary"], indent=2))
    print(f"\nwrote {OUT_JSON}\nwrote {OUT_PARQUET}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
