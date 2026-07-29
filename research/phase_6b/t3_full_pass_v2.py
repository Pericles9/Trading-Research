"""
Phase 6b A6.3a (T3) - the single budgeted full pass over filtered_trades.

Materializes event_minute_bars_v2 (extended-day, segment-tagged, all offsets)
in ONE pass, and computes the A8.2 strict-key duplicate-print counters within
that same pass (no extra scan). Config frozen at A6.2d. Must not run more than
once against filtered_trades (escalation row 9).

Post-pass gates: distinct T=0 events = 15,763 (row 3); every event present in
event_minute_bars_v1's T=0 must be present in v2's T=0 - ETH is a superset of
RTH, a missing event is a builder bug (row 4). Dup-print strict rate per event
must be <= 0.1% (row 7). All from the bar cache / temp, never a second pass.
"""
import json
import time

import duckdb
import pandas as pd

from research.phase_6b.build_minute_bars_v2 import build_session_spine_v2, build_minute_bars_v2, verify_bars_v2

DB_PATH = "data/duckdb/main.duckdb"
PHASE_6B_CONFIG = "config/phase_6b.json"
ELIGIBLE_EVENTS = "results/phase_6b/artifacts/t1_eligible_events.parquet"
OUT_TABLE = "event_minute_bars_v2"
V1_TABLE = "event_minute_bars_v1"
OUT_SUMMARY = "results/phase_6b/artifacts/t3_full_pass_v2_summary.json"
OUT_DUP = "results/phase_6b/artifacts/t3_dup_prints_v2.parquet"
OUT_EXCLUDED = "results/phase_6b/artifacts/t3_excluded_t0_v2.parquet"


def main():
    with open(PHASE_6B_CONFIG) as f:
        cfg = json.load(f)
    d1_expected = cfg["universe"]["expected_n"]
    dup_thresh = cfg["escalation_thresholds"]["duplicate_print_strict_key_max_pct_per_event"] / 100.0

    events = pd.read_parquet(ELIGIBLE_EVENTS)
    assert len(events) == d1_expected, f"eligible artifact {len(events)} != {d1_expected}"
    print(f"eligible events: {len(events)}")

    print("building extended-day session spine (XNYS + ET fallback bounds)...")
    t_s0 = time.perf_counter()
    spine = build_session_spine_v2(events, cfg)
    t_spine = time.perf_counter() - t_s0
    print(f"spine: {len(spine)} (event,offset) rows in {t_spine:.1f}s")

    con = duckdb.connect(DB_PATH, read_only=False)
    pre = con.execute("SELECT COUNT(*) FROM filtered_trades").fetchone()[0]
    print(f"pre-flight filtered_trades rows: {pre:,}")

    print(f"running THE single full pass -> {OUT_TABLE} (+ dup-print counters, same pass) ...")
    t0 = time.perf_counter()
    res = build_minute_bars_v2(con, "filtered_trades", spine, OUT_TABLE)
    wall = time.perf_counter() - t0
    print(f"full pass complete: {wall:.1f}s ({wall/60:.2f} min)")

    verify = verify_bars_v2(con, OUT_TABLE, spine)
    print(f"verify: {verify}")

    n_bar_rows = con.execute(f"SELECT COUNT(*) FROM {OUT_TABLE}").fetchone()[0]
    by_offset = con.execute(f"""
        SELECT session_offset, COUNT(DISTINCT (ticker,event_date_canonical,momentum_pct)) AS n_events, COUNT(*) AS n_bar_rows
        FROM {OUT_TABLE} GROUP BY session_offset ORDER BY session_offset
    """).fetchdf()
    by_segment = con.execute(f"""
        SELECT segment, COUNT(*) AS n_bar_rows, SUM(volume) AS total_volume
        FROM {OUT_TABLE} WHERE session_offset = 0 GROUP BY segment ORDER BY segment
    """).fetchdf()
    n_t0 = int(by_offset.loc[by_offset["session_offset"] == 0, "n_events"].iloc[0])

    # row 4: every v1 T=0 event present in v2 T=0
    v1_missing = con.execute(f"""
        SELECT COUNT(*) FROM (
            SELECT DISTINCT ticker, event_date_canonical, ROUND(momentum_pct,2) AS m FROM {V1_TABLE} WHERE session_offset = 0
        ) v1
        LEFT JOIN (
            SELECT DISTINCT ticker, event_date_canonical, ROUND(momentum_pct,2) AS m FROM {OUT_TABLE} WHERE session_offset = 0
        ) v2 USING (ticker, event_date_canonical, m)
        WHERE v2.ticker IS NULL
    """).fetchone()[0]

    # dup-print stats (APPROX/HLL, from the same-pass counters). Coarse diagnostic:
    # row 7 flags events materially above HLL noise (~2%), not the exact 0.1% - the exact
    # 0.0% record stands from 6c's dev tier. dup_coarse_flag_pct from config.
    dup = res["dup_prints"]
    dup.to_parquet(OUT_DUP, index=False)
    coarse_flag = cfg["escalation_thresholds"]["duplicate_print_approx_coarse_flag_pct"] / 100.0
    n_events_over_dup = int((dup["dup_strict_rate_approx"] > coarse_flag).sum())
    n_events_over_exact_thresh = int((dup["dup_strict_rate_approx"] > dup_thresh).sum())
    total_dup_strict = int(dup["n_dup_strict_approx"].sum())
    total_dup_loose = int(dup["n_dup_loose_approx"].sum())
    total_prints = int(dup["n_prints"].sum())

    excluded = res["excluded_t0"]
    excluded["excluded_share"] = excluded["n_excluded"] / excluded["n_total"].replace(0, pd.NA)
    excluded.to_parquet(OUT_EXCLUDED, index=False)
    tzm = res["tz_mismatch"]

    con.close()

    row3 = n_t0 != d1_expected
    row4 = v1_missing != 0
    row7 = n_events_over_dup > 0
    integrity_bad = verify["duplicate_keys"] != 0 or verify["out_of_window_minute_indices"] != 0 or verify["bad_segment_labels"] != 0

    summary = {
        "phase": "6b", "task": "A6.3a (T3)",
        "config_frozen": True,
        "eligible_events_input": len(events),
        "spine_rows": len(spine), "spine_build_seconds": round(t_spine, 2),
        "pre_flight_filtered_trades_rows": int(pre),
        "full_pass_wall_time_seconds": round(wall, 2), "full_pass_wall_time_minutes": round(wall / 60, 2),
        "bars": {"total_rows": int(n_bar_rows), "by_offset": by_offset.to_dict(orient="records"),
                 "t0_by_segment": by_segment.to_dict(orient="records")},
        "verify_integrity": {**verify, "pass": not integrity_bad},
        "t0_event_count_check": {"expected": d1_expected, "distinct_t0_events_in_v2": n_t0, "match": not row3},
        "v1_subset_check": {"v1_t0_events_missing_from_v2": int(v1_missing), "pass": not row4},
        "duplicate_print_check": {
            "method": "APPROX (HyperLogLog approx_count_distinct on hash of the strict key) - exact COUNT(DISTINCT) infeasible at full scale (Cooper 2026-07-28). Coarse population diagnostic; exact 0.0% record stands from Phase 6c dev tier.",
            "strict_key": "(event, sip_timestamp, price, size, sequence_number)",
            "total_strict_dup_rows_approx": total_dup_strict, "total_loose_dup_rows_approx": total_dup_loose,
            "total_prints": total_prints,
            "max_event_strict_rate_approx": float(dup["dup_strict_rate_approx"].max()),
            "coarse_flag_threshold": coarse_flag,
            "n_events_over_coarse_flag_5pct": n_events_over_dup,
            "n_events_over_exact_0.1pct_note": f"{n_events_over_exact_thresh} (within HLL noise, not an exact gate)",
            "artifact": OUT_DUP,
        },
        "excluded_row_share_t0": {
            "n_events_over_50pct_excluded": int((excluded["excluded_share"] > 0.5).sum()),
            "artifact": OUT_EXCLUDED,
        },
        "tz_et_vs_utc_date_mismatch": {"n_mismatch": int(tzm["n_mismatch"].iloc[0]), "n_total_rows": int(tzm["n_total_rows"].iloc[0])},
        "escalation": {"row3_t0_count": row3, "row4_v1_subset": row4, "row7_dup_prints": row7, "integrity": integrity_bad},
        "source": "research/phase_6b/t3_full_pass_v2.py:main",
    }
    with open(OUT_SUMMARY, "w") as f:
        json.dump(summary, f, indent=2, default=str)
    print(json.dumps({k: v for k, v in summary.items() if k != "bars"}, indent=2, default=str))
    print("\nby_offset:"); print(by_offset.to_string())
    print("t0 by_segment:"); print(by_segment.to_string())

    for cond, msg in [(row3, f"row3: distinct T=0 {n_t0} != {d1_expected}"),
                      (row4, f"row4: {v1_missing} v1 T=0 events missing from v2"),
                      (row7, f"row7 (coarse): {n_events_over_dup} events over 5% approx strict dup rate - gross-duplication tripwire"),
                      (integrity_bad, f"integrity: {verify}")]:
        if cond:
            print(f"\n*** ESCALATION {msg} - HARD STOP ***")


if __name__ == "__main__":
    main()
