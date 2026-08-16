"""T5a - dev-tier timing and extrapolation (A3-6 execution step 2).

Runs the FULL Stage B pipeline on dev v4, reports wall time, and extrapolates to
the detection universe using per-event print counts as the scaling variable.

If the extrapolation exceeds config.runtime.runtime_ceiling_seconds this is a
HARD STOP (escalation row 9 / row 26). The cohort, the grid and the ladder are
not reduced.

The scaling variable is obtained WITHOUT a pass: per-event T=0 print counts come
from event_minute_bars_v2, which is already materialised. Quote counts have no
materialised equivalent, so they are estimated from the dev-measured
quote-to-trade ratio per segment (T2d) and the estimate is labelled as such.
"""
from __future__ import annotations

import json
import pathlib
import sys
import time

sys.path.insert(0, str(pathlib.Path(__file__).parent))

import pandas as pd
from common import ARTIFACTS, CONFIG, connect, primary_events, session_bounds
from stage_b_pipeline import build_cache

CEIL = CONFIG["runtime"]["runtime_ceiling_seconds"]


def main() -> None:
    con = connect()
    ev = primary_events(con)
    dates = con.execute(
        "SELECT DISTINCT et(sip_timestamp)::DATE d FROM mom.filtered_quotes_dev_v4 "
        "WHERE dev_cohort='primary'").df()["d"]
    con.register("sb_df", session_bounds(dates))
    con.execute("CREATE TABLE sb AS SELECT * FROM sb_df")

    print("running the full Stage B pipeline on dev v4 (50 primary events)...")
    secs = build_cache(con, "mom.filtered_quotes_dev_v4", "mom.filtered_trades_dev_v4",
                       "dev_cohort='primary'", out_table="_dev_cache")
    n_rows = con.execute("SELECT COUNT(*) FROM _dev_cache").fetchone()[0]
    n_ev = con.execute("SELECT COUNT(DISTINCT (ticker, event_date)) FROM _dev_cache").fetchone()[0]
    print(f"  wall {secs:.1f}s | cache rows {n_rows:,} | events {n_ev}")

    # ---- dev-tier workload, T=0 only ------------------------------------
    dev_tr = con.execute("""
        SELECT COUNT(*) FROM mom.filtered_trades_dev_v4 x
        WHERE dev_cohort='primary' AND et(sip_timestamp)::DATE = event_date""").fetchone()[0]
    dev_q = con.execute("""
        SELECT COUNT(*) FROM mom.filtered_quotes_dev_v4 x
        WHERE dev_cohort='primary' AND et(sip_timestamp)::DATE = event_date""").fetchone()[0]

    # ---- full-tier workload from the materialised minute bars (no pass) --
    full_tr = con.execute("""
        SELECT SUM(b.n_trades)::BIGINT AS n_trades,
               COUNT(DISTINCT (b.ticker, b.event_date_canonical, b.momentum_pct)) AS n_events
        FROM mom.event_minute_bars_v2 b
        JOIN read_parquet('results/phase_8/artifacts/a102_detection_anchors.parquet') a
          ON a.ticker = b.ticker AND a.event_date_canonical = b.event_date_canonical
         AND round(a.mp, 2) = round(b.momentum_pct, 2)
        WHERE b.session_offset = 0 AND a.det_undefined = FALSE
    """).df().iloc[0]
    qt_ratio = dev_q / dev_tr
    full_q_est = int(full_tr["n_trades"] * qt_ratio)

    rows_per_sec = (dev_tr + dev_q) / secs
    est_secs = (full_tr["n_trades"] + full_q_est) / rows_per_sec

    out = {
        "task": "T5a", "phase": "11", "date": "2026-08-16",
        "dev_run": {"wall_seconds": round(secs, 2), "cache_rows": int(n_rows),
                    "events": int(n_ev), "t0_trades": int(dev_tr), "t0_quotes": int(dev_q),
                    "t0_rows_total": int(dev_tr + dev_q),
                    "rows_per_second": round(rows_per_sec, 0)},
        "full_tier_workload": {
            "source_of_trade_count": "event_minute_bars_v2 SUM(n_trades) at "
                                     "session_offset = 0, joined to the detection "
                                     "universe. Already materialised - NO PASS SPENT.",
            "events": int(full_tr["n_events"]),
            "t0_trades": int(full_tr["n_trades"]),
            "t0_quotes_estimated": full_q_est,
            "quote_to_trade_ratio_used": round(qt_ratio, 4),
            "quote_estimate_caveat": "There is no materialised per-event quote count, so "
                                     "the quote workload is ESTIMATED from the dev-tier "
                                     "T=0 quote-to-trade ratio. Labelled as an estimate; "
                                     "the trade half is exact.",
        },
        "extrapolation": {
            "method": "linear in total T=0 rows (trades + quotes) at the dev-measured "
                      "throughput; the pipeline is event-partitioned so cost is linear "
                      "in rows, not superlinear",
            "estimated_seconds": round(est_secs, 1),
            "estimated_hours": round(est_secs / 3600, 2),
            "ceiling_seconds": CEIL,
            "headroom_factor": round(CEIL / est_secs, 2) if est_secs else None,
        },
    }
    out["escalation_row_9"] = {
        "threshold": f"extrapolation > {CEIL} s",
        "observed": round(est_secs, 1),
        "verdict": "FIRES - HARD STOP" if est_secs > CEIL else "DOES NOT FIRE",
    }
    out["authorised"] = ("T5b may run." if est_secs <= CEIL else
                         "T5b is NOT authorised. Post and wait; do not reduce the "
                         "cohort, the grid or the ladder.")

    pathlib.Path(ARTIFACTS / "t5a_dev_timing.json").write_text(json.dumps(out, indent=2))
    print(f"\n  dev T=0 rows      {dev_tr + dev_q:>12,}  ({rows_per_sec:,.0f} rows/s)")
    print(f"  full T=0 trades   {int(full_tr['n_trades']):>12,}  (exact, from minute bars)")
    print(f"  full T=0 quotes   {full_q_est:>12,}  (estimated at {qt_ratio:.3f} q/t)")
    print(f"  EXTRAPOLATION     {est_secs:>12,.0f} s = {est_secs/3600:.2f} h"
          f"   ceiling {CEIL} s = {CEIL/3600:.0f} h")
    print(f"  row 9: {out['escalation_row_9']['verdict']}")


if __name__ == "__main__":
    main()
