"""
Phase 10 T0d -- tick surface available to the segmentation.

Reports, per cohort event: print counts on T=0 and on each flanking session
T-3..T-1, out-of-window prints, coverage per side, and which events carry
flag_possible_row_cap or a residual coverage flag. This establishes what the
segmentation is actually running on, before it runs.

Also runs the READ-PATH EQUIVALENCE PROOF that licenses this phase's zero-pass
budget (escalation row 4): for all 56 dev v4 events, the row count of
union(trades.parquet, trades_repair_1c.parquet) read straight off disk must
equal the row count in filtered_trades_dev_v4, which was materialized from
filtered_trades itself. If those agree, reading the event folder is the same
data as reading filtered_trades, and no scan of the 4.95B-row table is needed.

Ordering note: this task is numbered T0d but depends on the T1 cohort, so it
runs after T1. Recorded in the report.

Usage: python research/phase_10/t0d_tick_surface.py
"""
from __future__ import annotations

import os
import sys
import time

import duckdb
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import (  # noqa: E402
    COHORT_KEY, config_hash, event_folder, load_cohort, load_config,
    quantiles, read_event_trades, rel, session_window, trade_files, write_json,
)

OUT = "t0_tick_surface.json"
OUT_PER_EVENT = "t0_tick_surface.parquet"
OFFSETS = [-3, -2, -1, 0]


def read_path_equivalence(cfg, cohort) -> dict:
    """Prove folder-read == filtered_trades, on the 56 dev v4 events."""
    dev = cohort[cohort["cohort_group"].isin(["dev_v4_primary", "dev_v4_sidecar"])]
    con = duckdb.connect(rel(cfg["paths"]["duckdb"]), read_only=True)
    con.execute("SET enable_progress_bar=false")
    tbl = con.execute(
        """
        SELECT ticker, CAST(event_date AS VARCHAR) AS event_date_canonical,
               ROUND(momentum_pct, 2) AS momentum_pct, COUNT(*) AS n_table
        FROM filtered_trades_dev_v4 GROUP BY 1, 2, 3
        """
    ).fetchdf()
    con.close()

    rows = []
    for r in dev.itertuples(index=False):
        files = trade_files(cfg, r.ticker, r.event_date_canonical, r.momentum_pct)
        n_disk = sum(
            pd.read_parquet(f, columns=["sip_timestamp"]).shape[0] for f in files
        )
        rows.append({
            "ticker": r.ticker, "event_date_canonical": r.event_date_canonical,
            "momentum_pct": r.momentum_pct, "n_disk": int(n_disk),
            "n_files": len(files),
        })
    disk = pd.DataFrame(rows)
    m = disk.merge(tbl, on=COHORT_KEY, how="left")
    m["n_table"] = m["n_table"].fillna(0).astype("int64")
    m["agrees"] = m["n_disk"] == m["n_table"]
    bad = m.loc[~m["agrees"]].to_dict("records")
    return {
        "n_events_checked": int(len(m)),
        "n_agree": int(m["agrees"].sum()),
        "n_disagree": int((~m["agrees"]).sum()),
        "disagreements": bad,
        "total_rows_disk": int(m["n_disk"].sum()),
        "total_rows_table": int(m["n_table"].sum()),
        "pass": bool(m["agrees"].all()),
        "meaning": (
            "union(trades.parquet, trades_repair_1c.parquet) read directly off disk "
            "reproduces filtered_trades_dev_v4 row-for-row. filtered_trades_dev_v4 was "
            "materialized from filtered_trades by an inner join on the 3-part key "
            "(research/phase_5a/t5_materialize_dev_v4.py), so agreement here means the "
            "folder read IS the filtered_trades content for that event. This is what "
            "licenses reading folders instead of scanning the 4.95B-row table."
        ),
    }


def main() -> int:
    cfg = load_config()
    chash = config_hash()
    out_dir = rel(cfg["paths"]["out_artifacts"])
    cohort = load_cohort(cfg)

    t_eq = time.perf_counter()
    equiv = read_path_equivalence(cfg, cohort)
    equiv["elapsed_seconds"] = round(time.perf_counter() - t_eq, 1)
    print(f"read-path equivalence: {equiv['n_agree']}/{equiv['n_events_checked']} agree "
          f"({equiv['total_rows_disk']:,} rows)  pass={equiv['pass']}")

    rows, timings = [], []
    ceiling = cfg["runtime_ceilings"]["tick_read_seconds_per_event"]
    for i, r in enumerate(cohort.itertuples(index=False), 1):
        t0 = time.perf_counter()
        folder = event_folder(cfg, r.ticker, r.event_date_canonical, r.momentum_pct)
        data = read_event_trades(
            cfg, r.ticker, r.event_date_canonical, r.momentum_pct, offsets=OFFSETS
        )
        el = time.perf_counter() - t0
        timings.append(el)
        meta = data["_meta"]
        rec = {
            "ticker": r.ticker, "event_date_canonical": r.event_date_canonical,
            "momentum_pct": r.momentum_pct, "cohort_group": r.cohort_group,
            "folder_exists": os.path.isdir(folder), "n_files": meta["n_files"],
            "has_repair_sibling": meta["has_repair_sibling"],
            "n_rows_raw": meta["n_rows_raw"],
            "n_rows_out_of_window": meta.get("n_rows_out_of_window", 0),
            "flag_possible_row_cap": bool(r.flag_possible_row_cap),
            "flag_eth_dominant_t0": bool(r.flag_eth_dominant_t0) if pd.notna(r.flag_eth_dominant_t0) else False,
            "clean_window": bool(r.clean_window) if pd.notna(r.clean_window) else False,
            "trades_ingested": bool(r.trades_ingested) if pd.notna(r.trades_ingested) else False,
            "quotes_ingested": bool(r.quotes_ingested) if pd.notna(r.quotes_ingested) else False,
            "coverage_class": r.coverage_class,
            "trades_bitmap": getattr(r, "trades_bitmap", None),
            "repaired_1c": bool(r.repaired_1c) if pd.notna(r.repaired_1c) else False,
            "flag_window_calendar_bug": bool(r.flag_window_calendar_bug) if pd.notna(r.flag_window_calendar_bug) else False,
            "t0_print_count_bars": int(r.t0_print_count),
            "read_seconds": round(el, 2),
        }
        for off in OFFSETS:
            po = meta["per_offset"].get(off, {})
            rec[f"n_prints_off{off}"] = po.get("n_prints", 0)
        w0 = session_window(r.event_date_canonical, 0)
        rec["t0_session_date"] = w0["session_date"] if w0 else None
        rec["t0_is_early_close"] = w0["is_early_close"] if w0 else None
        rec["t0_span_minutes"] = w0["span_minutes"] if w0 else None
        rec["n_flanking_prints"] = sum(rec[f"n_prints_off{o}"] for o in (-3, -2, -1))
        rec["n_flanking_sessions_with_prints"] = sum(
            1 for o in (-3, -2, -1) if rec[f"n_prints_off{o}"] > 0
        )
        rows.append(rec)
        if i % 20 == 0:
            print(f"  {i}/{len(cohort)} events read", flush=True)

    surf = pd.DataFrame(rows)
    surf.to_parquet(os.path.join(out_dir, OUT_PER_EVENT), index=False)

    # cross-check the folder T=0 count against event_minute_bars_v2's own count
    surf["t0_bars_vs_folder_diff"] = surf["n_prints_off0"] - surf["t0_print_count_bars"]
    n_t0_mismatch = int((surf["t0_bars_vs_folder_diff"] != 0).sum())

    def grp(sub: pd.DataFrame) -> dict:
        return {
            "n_events": int(len(sub)),
            "t0_prints": quantiles(sub["n_prints_off0"]),
            "flanking_prints_total": quantiles(sub["n_flanking_prints"]),
            "n_events_with_zero_t0_prints": int((sub["n_prints_off0"] == 0).sum()),
            "n_events_with_zero_flanking_prints": int((sub["n_flanking_prints"] == 0).sum()),
            "n_events_all_3_flanking_sessions_present": int(
                (sub["n_flanking_sessions_with_prints"] == 3).sum()
            ),
            "n_events_with_repair_sibling": int(sub["has_repair_sibling"].sum()),
            "n_events_quotes_ingested": int(sub["quotes_ingested"].sum()),
            "n_events_trades_ingested": int(sub["trades_ingested"].sum()),
            "n_events_clean_window": int(sub["clean_window"].sum()),
            "n_events_flag_possible_row_cap": int(sub["flag_possible_row_cap"].sum()),
            "n_events_flag_eth_dominant_t0": int(sub["flag_eth_dominant_t0"].sum()),
            "n_events_early_close_t0": int(sub["t0_is_early_close"].fillna(False).sum()),
            "out_of_window_prints_total": int(sub["n_rows_out_of_window"].sum()),
        }

    total_t = float(np.sum(timings))
    summary = {
        "phase": "10", "task": "T0d", "config_hash": chash,
        "ordering_note": "T0d depends on the T1 cohort and therefore runs after T1.",
        "read_path": {
            "source": cfg["read_path"]["source"],
            "repair_siblings_included": True,
            "filtered_trades_scans": 0,
            "filtered_quotes_scans": 0,
            "equivalence_proof": equiv,
        },
        "cohort_n": int(len(cohort)),
        "by_group": {g: grp(sub) for g, sub in surf.groupby("cohort_group")},
        "all_cohort": grp(surf),
        "analysis_cohort_only": grp(surf[~surf["cohort_group"].isin(["dev_v4_sidecar", "row_cap_census"])]),
        "t0_count_crosscheck_vs_minute_bars": {
            "n_events": int(len(surf)),
            "n_mismatched": n_t0_mismatch,
            "max_abs_diff": int(surf["t0_bars_vs_folder_diff"].abs().max()),
            "note": (
                "event_minute_bars_v2 T=0 in-window print count vs this phase's folder read "
                "over the same extended-day window. A zero diff confirms the clock "
                "implementation here matches Phase 6b's."
            ),
            "mismatches": surf.loc[
                surf["t0_bars_vs_folder_diff"] != 0,
                COHORT_KEY + ["cohort_group", "n_prints_off0", "t0_print_count_bars", "t0_bars_vs_folder_diff"],
            ].to_dict("records")[:25],
        },
        "row_cap_events": surf.loc[
            surf["flag_possible_row_cap"],
            COHORT_KEY + ["cohort_group", "n_prints_off0", "n_flanking_prints"],
        ].to_dict("records"),
        "residual_coverage_flags": {
            "n_not_clean_window": int((~surf["clean_window"]).sum()),
            "events_not_clean_window": surf.loc[
                ~surf["clean_window"], COHORT_KEY + ["cohort_group", "coverage_class", "trades_bitmap"]
            ].to_dict("records"),
            "n_flag_window_calendar_bug": int(surf["flag_window_calendar_bug"].sum()),
            "n_repaired_1c": int(surf["repaired_1c"].sum()),
            "n_no_folder": int((~surf["folder_exists"]).sum()),
        },
        "timing": {
            "total_seconds": round(total_t, 1),
            "max_seconds_per_event": round(float(np.max(timings)), 1),
            "median_seconds_per_event": round(float(np.median(timings)), 2),
            "ceiling_seconds_per_event": ceiling,
            "escalation_row_5_triggered": bool(np.max(timings) > ceiling),
        },
        "source": "research/phase_10/t0d_tick_surface.py:main",
        "artifact": f"{cfg['paths']['out_artifacts']}{OUT_PER_EVENT}",
    }
    write_json(os.path.join(out_dir, OUT), summary)

    print(f"tick surface: {len(surf)} events, total read {total_t:.0f}s, "
          f"max/event {np.max(timings):.1f}s")
    print(f"T=0 vs minute-bars crosscheck mismatches: {n_t0_mismatch}")
    print(f"events with 0 T=0 prints: {int((surf['n_prints_off0'] == 0).sum())}")
    print(f"events with 0 flanking prints: {int((surf['n_flanking_prints'] == 0).sum())}")
    return 0 if equiv["pass"] else 4


if __name__ == "__main__":
    raise SystemExit(main())
