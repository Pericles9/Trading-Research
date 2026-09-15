"""
E2-T2a: baseline volume B_e, the part of DE-2's window definition that does NOT depend
on the still-pending baseline floor (or on C or the censoring horizon) -- run now, per
Cooper's instruction, to produce B_e's real distribution before the floor is set.

event_minute_bars_v2's session_offset already runs -3..+3 relative TRADING sessions
around the event (0 = event day), with segment in {premarket, rth, post} -- confirmed
directly (session_offset=-3..-1, segment='rth' gives exactly the 3 prior regular-hours
sessions DE-2 asks for, 390 one-minute bars = 39 ten-minute intervals each, minute_index
330-719). No calendar-day arithmetic needed; the table's own build
(research/phase_6b/build_minute_bars_v2.py) already handles session skipping.

B_e = total rth volume across whichever of T-3..T-1 have non-zero rth volume, divided by
(n_baseline_sessions_present x 39 ten-minute intervals) -- the denominator uses sessions
ACTUALLY present, not a fixed 3, so a thin baseline from a missing prior session and a
thin baseline from genuinely low volume stay distinguishable (n_baseline_sessions is
carried as its own column precisely so the two are never conflated).

Usage: .venv/Scripts/python.exe research/fundamental_exploration/e2_t2a_baseline.py
"""
from __future__ import annotations

import json
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from research.fundamental_exploration import common as C  # noqa: E402

INTERVALS_PER_SESSION = 39  # 390 rth minutes / 10


def main() -> int:
    cfg_e2 = C.load_cfg(C.CFG_E2)
    frame = pd.read_parquet(cfg_e2["universe"]["materialization_path"])
    frame["event_id"] = frame.apply(C.event_id, axis=1)
    key = frame[["event_id", "ticker", "event_date_canonical", "momentum_pct"]].copy()

    con = C.connect(read_only=True)
    con.register("d1_key", key)
    sql = """
        SELECT k.event_id, b.session_offset, SUM(b.volume) AS session_rth_volume
        FROM d1_key k
        JOIN event_minute_bars_v2 b
          ON b.ticker = k.ticker AND b.event_date_canonical = k.event_date_canonical
         AND b.momentum_pct = k.momentum_pct
        WHERE b.session_offset IN (-3, -2, -1) AND b.segment = 'rth'
        GROUP BY k.event_id, b.session_offset
    """
    per_session = con.execute(sql).df()
    con.close()

    # full (event_id x session_offset in {-3,-2,-1}) grid -- a combo absent from per_session
    # is exactly "no rth data that session", filled 0, same treatment as a present-but-zero row.
    grid = pd.MultiIndex.from_product(
        [key["event_id"], [-3, -2, -1]], names=["event_id", "session_offset"]
    ).to_frame(index=False)
    grid = grid.merge(per_session, on=["event_id", "session_offset"], how="left")
    grid["session_rth_volume"] = grid["session_rth_volume"].fillna(0)
    grid["session_present"] = grid["session_rth_volume"] > 0

    # session_rth_volume is already 0 for any non-present session (filled above), so a plain
    # sum over all 3 nominal sessions equals the sum over just the present ones.
    agg = grid.groupby("event_id").agg(
        n_baseline_sessions=("session_present", "sum"),
        total_baseline_volume=("session_rth_volume", "sum"),
    ).reset_index()
    agg["B_e"] = agg["total_baseline_volume"] / (agg["n_baseline_sessions"] * INTERVALS_PER_SESSION)
    agg.loc[agg["n_baseline_sessions"] == 0, "B_e"] = pd.NA

    out = key[["event_id"]].merge(agg, on="event_id", how="left")
    out["n_baseline_sessions"] = out["n_baseline_sessions"].fillna(0).astype(int)
    out["total_baseline_volume"] = out["total_baseline_volume"].fillna(0)

    out.to_parquet(f"{C.ART_E2}/e2_t2a_baseline.parquet", index=False)

    n_zero_baseline_sessions = int((out["n_baseline_sessions"] == 0).sum())
    b_e_valid = out["B_e"].dropna()
    summary = {
        "task": "E2-T2a baseline volume B_e (pre-floor)",
        "config_hash": C.cfg_hash(C.CFG_E2),
        "n_total": len(out),
        "n_baseline_sessions_counts": out["n_baseline_sessions"].value_counts().sort_index().to_dict(),
        "n_zero_baseline_sessions": n_zero_baseline_sessions,
        "n_zero_baseline_sessions_note": "events with none of T-3..T-1 showing rth volume -- B_e is "
                                         "undefined (NaN) for these, not zero. DE-2's window/duration "
                                         "build cannot run for them.",
        "B_e_distribution_shares_per_10min": {
            "n": int(len(b_e_valid)), "min": float(b_e_valid.min()),
            "p1": float(b_e_valid.quantile(0.01)), "p5": float(b_e_valid.quantile(0.05)),
            "p10": float(b_e_valid.quantile(0.10)), "p25": float(b_e_valid.quantile(0.25)),
            "median": float(b_e_valid.quantile(0.50)), "p75": float(b_e_valid.quantile(0.75)),
            "p90": float(b_e_valid.quantile(0.90)), "max": float(b_e_valid.max()),
        },
    }
    C.write_json(f"{C.ART_E2}/e2_t2a_baseline_summary.json", summary)
    print(json.dumps(summary, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
