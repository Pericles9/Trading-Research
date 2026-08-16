"""T7 - round-trip cost against available capture. The headline.

Reads event_quote_metrics_v1 and the frozen Phase 8/9 artifacts. No further scan.

T7a  entry cost = half effective spread crossing at det + latency;
     exit cost  = half effective spread crossing at exit. Round trip in log terms.
T7b  two capture denominators, never blended:
       (i) perfect-foresight ceiling  log(H / p_det), H = day_high_ext (frozen)
      (ii) realized capture at the matching fixed horizon (Phase 9 T4 grid)
T7c  ratio computed PER EVENT then distributed - never a ratio of medians.
     Reported at 1x, 1.5x and 2x cost, the 1.5x column with equal prominence.
T7d  share of events where round-trip cost exceeds realized capture outright.
T7e  Phase 9 flags carried as their own rows, never pooled.
T7e-i pre-registered reading rule for the named cell.
T7f  stale-price zero atom flagged per cell.
T7g  headline with and without the events above 1% unusable share.
T7h  locked clock-time share in the RTH decision cell.
"""
from __future__ import annotations

import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).parent))

import duckdb
import numpy as np
import pandas as pd
from common import ARTIFACTS, CONFIG, DB

ANCH = "results/phase_8/artifacts/a102_detection_anchors.parquet"
PART = "results/phase_8/artifacts/t3_participation.parquet"
GRID = "results/phase_9/artifacts/t4_axis_grid.parquet"
XS = "results/phase_9/artifacts/t1_cross_session_flags.parquet"
CAP = "results/phase_8/artifacts/a101_labels.parquet"
DUP = "results/phase_6b/artifacts/event_index_v2.parquet"
QSESS = "results/phase_4/artifacts/_actual_quotes_sessions_cache.parquet"
LAT = [0, 1, 5, 15, 30]
HOLDS = [5, 15, 30, 60, 120]
MULT = [1.0, 1.5, 2.0]
KILL = CONFIG["cooper_thresholds"]["row_11_kill_threshold"]
MIN_N = CONFIG["universe"]["min_cell_n"]


def main() -> None:
    con = duckdb.connect()
    con.execute(f"ATTACH '{DB}' AS mom (READ_ONLY)")
    con.execute("SET enable_progress_bar = false")

    # Effective spread on every bar, keyed for ASOF resolution at entry and exit.
    con.execute("""
        CREATE TABLE bars AS
        SELECT ticker, event_date, minute_index, tw_mid, sum_size,
               2.0 * sum_abs_p_minus_m_size / NULLIF(sum_size,0)               AS eff_dollars,
               2.0 * sum_abs_p_minus_m_size / NULLIF(sum_size,0)
                   / NULLIF(tw_mid,0)                                         AS eff_frac,
               unusable_time_share, locked_time_share, dur_ns_total
        FROM mom.event_quote_metrics_v1
        WHERE n_trades > 0 AND sum_size > 0
    """)
    con.execute(f"""
        CREATE TABLE g AS
        SELECT x.ticker, x.event_date_canonical AS event_date, x.latency, x.hold,
               x.entry_minute, x.exit_minute, x.entry_price, x.exit_price, x.markout,
               x.entry_undefined, x.exit_undefined, x.det_segment, x.era,
               a.day_high_ext, p.pq_rth_open
        FROM read_parquet('{GRID}') x
        JOIN read_parquet('{ANCH}') a
          ON a.ticker = x.ticker AND a.event_date_canonical = x.event_date_canonical
         AND round(a.mp,2) = round(x.mp,2) AND a.det_undefined = FALSE
        LEFT JOIN read_parquet('{PART}') p
          ON p.ticker = x.ticker AND p.event_date_canonical = x.event_date_canonical
         AND round(p.mp,2) = round(x.mp,2)
        JOIN (SELECT DISTINCT ticker, event_date_canonical, mom_2dp
              FROM read_parquet('{QSESS}')) q
          ON q.ticker = x.ticker AND q.event_date_canonical = x.event_date_canonical
         AND q.mom_2dp = round(x.mp,2)
        WHERE x.grid = 'fixed_horizon'
    """)
    # ASOF-resolve entry and exit bars, take half the effective spread at each.
    con.execute("""
        CREATE TABLE j AS
        SELECT g.*, be.eff_frac AS eff_entry, be.eff_dollars AS eff_entry_d,
               be.unusable_time_share AS unusable_entry, be.locked_time_share AS locked_entry,
               bx.eff_frac AS eff_exit, bx.eff_dollars AS eff_exit_d
        FROM g
        ASOF LEFT JOIN bars be
          ON g.ticker = be.ticker AND g.event_date = be.event_date
         AND g.entry_minute >= be.minute_index
        ASOF LEFT JOIN bars bx
          ON g.ticker = bx.ticker AND g.event_date = bx.event_date
         AND g.exit_minute >= bx.minute_index
    """)
    d = con.execute("SELECT * FROM j").df()

    # ---- T7a: round-trip cost in log terms -----------------------------
    d["rt_cost"] = 0.5 * d.eff_entry + 0.5 * d.eff_exit
    # ---- T7b: two denominators, never blended --------------------------
    d["cap_realized"] = d.markout
    d["cap_foresight"] = np.log(d.day_high_ext / d.entry_price.where(d.entry_price > 0))

    flags = {}
    for name, path, col, keys in [
        ("flag_cross_session_extreme", XS, "flag_cross_session_extreme",
         ["ticker", "event_date_canonical"]),
        ("flag_possible_row_cap", CAP, "flag_possible_row_cap",
         ["ticker", "event_date_canonical"]),
        ("flag_has_dup_prints", DUP, "flag_has_dup_prints",
         ["ticker", "event_date_canonical"]),
    ]:
        f = pd.read_parquet(path)
        f = f.groupby(keys)[col].max().reset_index().rename(
            columns={"event_date_canonical": "event_date"})
        f["event_date"] = pd.to_datetime(f["event_date"]).dt.date
        flags[name] = f
        d["event_date"] = pd.to_datetime(d["event_date"]).dt.date
        d = d.merge(f, on=["ticker", "event_date"], how="left")
        d[col] = d[col].fillna(False)

    valid = (~d.entry_undefined) & (~d.exit_undefined) & d.rt_cost.notna()
    for m in MULT:
        d[f"ratio_{m}x"] = np.where(valid & (d.cap_realized > 0),
                                    m * d.rt_cost / d.cap_realized, np.nan)
        d[f"ratio_fs_{m}x"] = np.where(valid & (d.cap_foresight > 0),
                                       m * d.rt_cost / d.cap_foresight, np.nan)
    d["cost_exceeds_capture_1x"] = np.where(
        valid & (d.cap_realized > 0), d.rt_cost > d.cap_realized, np.nan)
    d["capture_nonpositive"] = valid & (d.cap_realized <= 0)

    d.to_parquet(ARTIFACTS / "t7_cost_vs_capture.parquet", index=False)

    def cell(sub: pd.DataFrame) -> dict:
        r = sub["ratio_1.0x"].dropna()
        return {
            "n": int(len(sub)),
            "n_ratio_defined": int(len(r)),
            "median_ratio_1x": float(r.median()) if len(r) else None,
            "median_ratio_1_5x": float(sub["ratio_1.5x"].dropna().median())
                if sub["ratio_1.5x"].notna().any() else None,
            "median_ratio_2x": float(sub["ratio_2.0x"].dropna().median())
                if sub["ratio_2.0x"].notna().any() else None,
            "share_cost_exceeds_capture": float(sub.cost_exceeds_capture_1x.dropna().mean())
                if sub.cost_exceeds_capture_1x.notna().any() else None,
            "share_capture_nonpositive": float(sub.capture_nonpositive.mean()),
            "median_rt_cost_bp": float(sub.rt_cost.dropna().median() * 10000)
                if sub.rt_cost.notna().any() else None,
            "median_rt_cost_cents": float((sub.eff_entry_d.fillna(0) * 0.5
                                           + sub.eff_exit_d.fillna(0) * 0.5)
                                          .replace(0, np.nan).dropna().median() * 100)
                if len(sub) else None,
            "zero_atom": bool(len(r) and (r == 0).mean() > 0.5),
            "hatched_n_below_100": bool(len(sub) < MIN_N),
        }

    named = d[(d.det_segment == "rth") & (d.latency == 5) & (d.hold == 30)]
    nc = cell(named)
    med = nc["median_ratio_1x"]
    p25 = float(named["ratio_1.0x"].dropna().quantile(.25)) if nc["n_ratio_defined"] else None

    # ---- T7e-i pre-registered reading rule -----------------------------
    if nc["n_ratio_defined"] < MIN_N:
        rule = "Cell n < 100 after exclusions - the named cell is not populated enough to read; no row applies"
    elif nc["share_capture_nonpositive"] > 0.5:
        rule = ("Realized capture <= 0 for more than half the cell - the denominator is "
                "non-positive for the majority; the ratio is undefined on that population "
                "and is reported as a share, not a ratio")
    elif med is not None and med >= 1.0:
        rule = "Median >= 1.0 - cost exceeds capture at the median of the named cell"
    elif p25 is not None and p25 >= KILL:
        rule = ("Median < 1.0, 25th percentile >= config.kill_threshold - cost is below "
                "capture at the median; the lower quartile is at or above the threshold")
    else:
        rule = ("Median < 1.0, 25th percentile < config.kill_threshold - cost is below "
                "capture at the median; the lower quartile is below the threshold")

    grid_cells = []
    for (seg, lat, hold), sub in d.groupby(["det_segment", "latency", "hold"], dropna=False):
        c = cell(sub)
        c.update({"det_segment": seg, "latency": lat, "hold": hold})
        grid_cells.append(c)

    dirty = d[d.unusable_entry > 0.01]
    clean = d[(d.unusable_entry <= 0.01) | d.unusable_entry.isna()]
    nd = named[named.unusable_entry <= 0.01]

    out = {
        "task": "T7", "phase": "11", "date": "2026-08-16",
        "standing_qualifier": CONFIG["standing_qualifier"]["text"],
        "cost_multiple_note": CONFIG["cooper_thresholds"]["cost_multiple_reporting"],
        "named_cell": {"grid": "fixed_horizon", "det_segment": "rth", "latency": 5,
                       "hold": 30, **nc, "p25_ratio_1x": p25,
                       "kill_threshold": KILL,
                       "escalation_row_11": ("FIRES - HARD STOP" if med is not None
                                             and med >= KILL else "DOES NOT FIRE")},
        "t7e_i_reading_rule_row": rule,
        "grid": grid_cells,
        "t7d_share_cost_exceeds_capture_named_cell": nc["share_cost_exceeds_capture"],
        "t7e_flags": {k: {"n_events_flagged": int(d[d[k]][["ticker", "event_date"]]
                                                   .drop_duplicates().shape[0]),
                          "named_cell_median_ratio_1x_with":
                              float(named[named[k]]["ratio_1.0x"].dropna().median())
                              if named[named[k]]["ratio_1.0x"].notna().any() else None,
                          "named_cell_median_ratio_1x_without":
                              float(named[~named[k]]["ratio_1.0x"].dropna().median())
                              if named[~named[k]]["ratio_1.0x"].notna().any() else None}
                      for k in flags},
        "t7f_zero_atom_cells": int(sum(c["zero_atom"] for c in grid_cells)),
        "t7g_dirty_event_sensitivity": {
            "definition": "events whose ENTRY bar has unusable_time_share > 1%",
            "n_rows_dirty": int(len(dirty)), "n_rows_clean": int(len(clean)),
            "named_cell_median_ratio_1x_all": med,
            "named_cell_median_ratio_1x_excluding_dirty":
                float(nd["ratio_1.0x"].dropna().median())
                if nd["ratio_1.0x"].notna().any() else None,
        },
        "t7h_locked_share_rth_decision_cell": {
            "median_locked_time_share_entry_bar": float(named.locked_entry.dropna().median())
                if named.locked_entry.notna().any() else None,
            "p95": float(named.locked_entry.dropna().quantile(.95))
                if named.locked_entry.notna().any() else None,
            "n": int(named.locked_entry.notna().sum()),
            "meaning": "D17 carries locked quotes. If this is ~0 the choice is immaterial. "
                       "If not, measured spread is biased DOWNWARD and the headline is "
                       "optimistic by an amount this bounds.",
        },
    }
    pathlib.Path(ARTIFACTS / "t7_cost_vs_capture.json").write_text(json.dumps(out, indent=2, default=str))
    print("NAMED CELL:", json.dumps(out["named_cell"], indent=2, default=str))
    print("READING RULE:", rule)


if __name__ == "__main__":
    main()
