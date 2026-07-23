"""
Phase 6 T3 - the single budgeted full pass over filtered_trades. Config is
frozen (config/phase_6.json, committed at T0, unchanged through T2).

Materializes DuckDB table event_minute_bars_v1: all T1-eligible D1 events
(15,763 - eligibility turned out non-binding, T1) x available offsets
T-3..T+3. Same code path as T2 (research/phase_6/build_minute_bars.py),
verified against filtered_trades_dev_v4 first. This script must not be
run more than once against filtered_trades (escalation row 7).
"""
import json
import time

import duckdb
import pandas as pd

from research.phase_6.build_minute_bars import build_session_spine, build_minute_bars, verify_bars

DB_PATH = "data/duckdb/main.duckdb"
PHASE_6_CONFIG = "config/phase_6.json"
ELIGIBLE_EVENTS = "results/phase_6/artifacts/t1_eligible_events.parquet"
T1_SUMMARY = "results/phase_6/artifacts/t1_eligibility.json"
OUT_TABLE = "event_minute_bars_v1"
OUT_SUMMARY = "results/phase_6/artifacts/t3_full_pass_summary.json"
OUT_EXCLUDED_T0 = "results/phase_6/artifacts/t3_excluded_t0_rows.parquet"


def main():
    with open(PHASE_6_CONFIG) as f:
        cfg = json.load(f)
    with open(T1_SUMMARY) as f:
        t1 = json.load(f)
    t1_eligible_n = t1["eligible"]["n"]

    events = pd.read_parquet(ELIGIBLE_EVENTS)
    print(f"eligible events loaded: {len(events)} (T1 summary says {t1_eligible_n})")
    assert len(events) == t1_eligible_n, "eligible-events artifact does not match T1 summary - stale artifact"

    print("building session spine (XNYS calendar arithmetic + market_open/close per session)...")
    t_spine0 = time.perf_counter()
    spine = build_session_spine(events, cfg)
    t_spine = time.perf_counter() - t_spine0
    print(f"session spine: {len(spine)} (event,offset) rows in {t_spine:.1f}s")

    con = duckdb.connect(DB_PATH, read_only=False)

    pre_check = con.execute("SELECT COUNT(*) FROM filtered_trades").fetchone()[0]
    print(f"pre-flight: filtered_trades row count = {pre_check:,}")

    print(f"running THE single full pass over filtered_trades -> {OUT_TABLE} ...")
    t0 = time.perf_counter()
    build_result = build_minute_bars(con, "filtered_trades", spine, OUT_TABLE)
    wall_time = time.perf_counter() - t0
    print(f"full pass complete: {wall_time:.1f}s ({wall_time/60:.2f} min)")

    verify = verify_bars(con, OUT_TABLE, spine)
    print(f"verify: {verify}")

    n_bar_rows = con.execute(f"SELECT COUNT(*) FROM {OUT_TABLE}").fetchone()[0]
    by_offset = con.execute(f"""
        SELECT session_offset, COUNT(DISTINCT (ticker,event_date_canonical,momentum_pct)) AS n_events, COUNT(*) AS n_bar_rows
        FROM {OUT_TABLE} GROUP BY session_offset ORDER BY session_offset
    """).fetchdf()
    n_t0_events = int(by_offset.loc[by_offset["session_offset"] == 0, "n_events"].iloc[0])
    print(by_offset)

    excluded_t0 = build_result["excluded_t0"]
    excluded_t0["excluded_share"] = excluded_t0["n_excluded"] / excluded_t0["n_total"].replace(0, pd.NA)
    excluded_t0.to_parquet(OUT_EXCLUDED_T0, index=False)
    high_excluded = excluded_t0[excluded_t0["excluded_share"] > 0.5].sort_values("excluded_share", ascending=False)

    con.close()

    row3_triggered = verify["duplicate_keys"] != 0 or verify["out_of_session_minute_indices"] != 0
    row4_triggered = n_t0_events != t1_eligible_n
    row7_note = "This script executes exactly one CREATE TABLE ... AS SELECT over filtered_trades per invocation; do not re-run against filtered_trades once this has completed successfully."

    summary = {
        "phase": "6", "task": "T3",
        "config_frozen": True,
        "eligible_events_input": len(events),
        "spine_rows": len(spine),
        "spine_build_seconds": round(t_spine, 2),
        "pre_flight_filtered_trades_rows": int(pre_check),
        "full_pass_wall_time_seconds": round(wall_time, 2),
        "full_pass_wall_time_minutes": round(wall_time / 60, 2),
        "bars": {
            "total_rows": int(n_bar_rows),
            "by_offset": by_offset.to_dict(orient="records"),
        },
        "verify_integrity": {**verify, "pass": not row3_triggered},
        "t0_event_count_check": {
            "t1_eligible_n": t1_eligible_n,
            "distinct_t0_events_in_bars": n_t0_events,
            "match": not row4_triggered,
        },
        "excluded_row_share_t0": {
            "n_events_over_50pct_excluded": int(len(high_excluded)),
            "top_20_flagged_events": high_excluded.head(20)[["ticker", "event_date_canonical", "n_in_session", "n_excluded", "n_total", "excluded_share"]].to_dict(orient="records"),
            "artifact": OUT_EXCLUDED_T0,
        },
        "escalation_row3_triggered": row3_triggered,
        "escalation_row4_triggered": row4_triggered,
        "escalation_row7_note": row7_note,
        "source": "research/phase_6/t3_full_pass.py:main",
    }
    with open(OUT_SUMMARY, "w") as f:
        json.dump(summary, f, indent=2, default=str)
    print(json.dumps(summary, indent=2, default=str))

    if row3_triggered:
        print("\n*** ESCALATION row 3: bar integrity violation - HARD STOP ***")
    if row4_triggered:
        print(f"\n*** ESCALATION row 4: distinct T=0 events in bars ({n_t0_events}) != T1 eligible count ({t1_eligible_n}) - HARD STOP ***")


if __name__ == "__main__":
    main()
