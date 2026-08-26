"""
Phase 10c Stage 1, T3 -- anchor-relative outputs.

T3a  sub-burst position relative to detection, per cell
T3b  near-anchor print density, per cell, per segment
T3c  which sub-burst is first, and which is largest by move-share, since detection
T3d  every output below carries the anchor-delta figures (ANCHOR_DELTA_CAPTION)

ANCHOR_DELTA_CAPTION is the mandatory inherited-uncertainty note (escalation row 7):
measured anchor-timing deltas (Amendment 3 A1) are median 112.9s (1.25<->1.30), 313.6s
(1.25<->1.35), 53.4s (1.30<->1.35), max 13,856s. The 2-minute kernel is 120s -- the
median cross-variant disagreement about where the origin sits is comparable to the
smallest kernel and a third of the 8-minute kernel. Only the 32-minute kernel is
comfortably larger than the widest pair's median.

Usage: .venv/Scripts/python.exe research/phase_10c/s1_t3_anchor_relative.py
"""
from __future__ import annotations

import importlib.util as ilu
import os
import sys
import time

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "phase_10"))
import common as p10  # noqa: E402
from common import rel  # noqa: E402
_s = ilu.spec_from_file_location("c10c", os.path.join(HERE, "common.py"))
c10c = ilu.module_from_spec(_s); _s.loader.exec_module(c10c)

ART = "results/phase_10c/artifacts"
ET = "America/New_York"
VARIANTS = [1.25, 1.30, 1.35]
KERNELS = [2.0, 8.0, 32.0]
ANCHOR_CODES = {"ACET": {8, 9, 41}, "OST": {14, 12, 41}, "CELH": {12}, "BMR": {12, 37}}

ANCHOR_DELTA_CAPTION = (
    "<b>Inherited anchor-delta uncertainty (Amendment 3 A1):</b> median cross-variant anchor "
    "disagreement 112.9s (1.25<->1.30), 313.6s (1.25<->1.35), 53.4s (1.30<->1.35); max 13,856s. "
    "The 2-min kernel is 120s -- comparable to the smallest median delta and ~1/3 of the 8-min "
    "kernel. Only the 32-min kernel is comfortably larger than the widest pair's median."
)


def main() -> int:
    import exchange_calendars as xcals
    cal = xcals.get_calendar("XNYS")
    cfg, chash = c10c.load_cfg(), c10c.cfg_hash()
    dev = c10c.load_dev_sample(cfg)
    det = pd.read_parquet(rel("results/phase_10/artifacts/v2_r13_detection.parquet"))
    det["event_date_canonical"] = det["event_date_canonical"].astype(str)
    cells = pd.read_parquet(rel(f"{ART}/s1_t1_cells.parquet"))
    sb = pd.read_parquet(rel(f"{ART}/s1_t1_subbursts.parquet"))

    # -------------------------------------------------------- per-variant anchor table
    anc_rows = []
    for r in dev.itertuples(index=False):
        for v in VARIANTS:
            row = det[(det.ticker == r.ticker) & (det.event_date_canonical
                      == r.event_date_canonical) & (np.isclose(det.threshold, v))]
            if not len(row) or pd.isna(row.iloc[0].det_ns_poll0):
                anc_rows.append({"ticker": r.ticker, "event_date_canonical":
                                 r.event_date_canonical, "threshold": v, "det_ns": np.nan})
                continue
            anc_rows.append({"ticker": r.ticker, "event_date_canonical": r.event_date_canonical,
                             "threshold": v, "det_ns": int(row.iloc[0].det_ns_poll0)})
    anc = pd.DataFrame(anc_rows)

    # -------------------------------------------------------- T3a sub-burst position vs detection
    sb_v = sb.merge(anc, on=["ticker", "event_date_canonical"], how="left")
    sb_v["t_from_detection_s"] = (sb_v.start_ns - sb_v.det_ns) / 1e9
    seg_map = cells[["ticker", "event_date_canonical", "threshold", "kernel_min",
                     "segment"]].drop_duplicates()
    sb_v = sb_v.merge(seg_map, on=["ticker", "event_date_canonical", "threshold", "kernel_min"],
                      how="left")
    sb_v.to_parquet(rel(f"{ART}/s1_t3a_subburst_position.parquet"), index=False)

    def summary(a):
        a = a[np.isfinite(a)]
        if a.size == 0:
            return {"n": 0, "median": None, "p25": None, "p75": None}
        return {"n": int(a.size), "median": float(np.median(a)),
                "p25": float(np.percentile(a, 25)), "p75": float(np.percentile(a, 75))}

    t3a_summary = []
    for (v, k, seg), g in sb_v.groupby(["threshold", "kernel_min", "segment"], dropna=False):
        s = summary(g.t_from_detection_s.to_numpy())
        t3a_summary.append({"threshold": v, "kernel_min": k, "segment": seg, **s})
    c10c.write_json(rel(f"{ART}/s1_t3a_summary.json"), {
        "phase": "10c", "stage": "1", "task": "T3a_position_vs_detection",
        "anchor_delta_caption": ANCHOR_DELTA_CAPTION,
        "population": "sub-bursts whose event has a valid anchor under that variant",
        "rows": t3a_summary, "config_hash": chash})

    # -------------------------------------------------------- T3b near-anchor print density
    t0 = time.perf_counter()
    dens_rows = []
    for i, r in enumerate(dev.itertuples(index=False), 1):
        d = p10.read_event_trades(cfg, r.ticker, r.event_date_canonical, r.momentum_pct,
                                  offsets=(0,))
        s0 = d.get(0)
        if s0 is None or len(s0) == 0:
            continue
        uniq = np.unique(s0["sip_timestamp"].to_numpy())
        agg_ts, _ = c10c.sweep_aggregate(uniq, float(c10c.class_m(cfg)["D1_sweep_floor_us"]))
        for v in VARIANTS:
            row = anc[(anc.ticker == r.ticker) & (anc.event_date_canonical
                      == r.event_date_canonical) & (np.isclose(anc.threshold, v))]
            det_ns = row.iloc[0].det_ns if len(row) else np.nan
            if pd.isna(det_ns):
                continue
            for k in KERNELS:
                half_ns = k * 60.0 * 1e9 / 2.0
                lo = np.searchsorted(agg_ts, det_ns - half_ns, "left")
                hi = np.searchsorted(agg_ts, det_ns + half_ns, "right")
                n_near = int(hi - lo)
                dens_rows.append({"ticker": r.ticker, "event_date_canonical":
                                  r.event_date_canonical, "threshold": v, "kernel_min": k,
                                  "n_prints_near_anchor": n_near,
                                  "prints_per_min": n_near / k})
        if i % 20 == 0:
            print(f"  T3b {i}/{len(dev)} ({time.perf_counter()-t0:.0f}s)", flush=True)

    t3b = pd.DataFrame(dens_rows)
    t3b = t3b.merge(seg_map, on=["ticker", "event_date_canonical", "threshold", "kernel_min"],
                    how="left")
    t3b.to_parquet(rel(f"{ART}/s1_t3b_near_anchor_density.parquet"), index=False)
    t3b_summary = []
    for (v, k, seg), g in t3b.groupby(["threshold", "kernel_min", "segment"], dropna=False):
        s = summary(g.prints_per_min.to_numpy())
        t3b_summary.append({"threshold": v, "kernel_min": k, "segment": seg, **s})
    c10c.write_json(rel(f"{ART}/s1_t3b_summary.json"), {
        "phase": "10c", "stage": "1", "task": "T3b_near_anchor_density",
        "anchor_delta_caption": ANCHOR_DELTA_CAPTION,
        "definition": "prints (D1-aggregated) within +/- kernel/2 minutes of that variant's anchor, "
                     "divided by kernel width -- prints per minute",
        "rows": t3b_summary, "config_hash": chash})

    # -------------------------------------------------------- T3c first / largest since detection
    after = sb_v[sb_v.t_from_detection_s >= 0].copy()
    first_rows, largest_rows = [], []
    for (tk, ed, v, k), g in after.groupby(["ticker", "event_date_canonical", "threshold",
                                            "kernel_min"]):
        fr = g.loc[g.t_from_detection_s.idxmin()]
        first_rows.append({"ticker": tk, "event_date_canonical": ed, "threshold": v,
                           "kernel_min": k, "t_from_detection_s": float(fr.t_from_detection_s),
                           "duration_s": float(fr.duration_s)})
        lr = g.loc[g.move_share.idxmax()] if g.move_share.notna().any() else None
        if lr is not None:
            largest_rows.append({"ticker": tk, "event_date_canonical": ed, "threshold": v,
                                 "kernel_min": k, "t_from_detection_s": float(lr.t_from_detection_s),
                                 "move_share": float(lr.move_share)})
    first_df, largest_df = pd.DataFrame(first_rows), pd.DataFrame(largest_rows)
    first_df.to_parquet(rel(f"{ART}/s1_t3c_first_subburst.parquet"), index=False)
    largest_df.to_parquet(rel(f"{ART}/s1_t3c_largest_subburst.parquet"), index=False)

    same_event = (first_df.merge(largest_df, on=["ticker", "event_date_canonical", "threshold",
                                                 "kernel_min"], suffixes=("_first", "_largest")))
    same_event["first_is_largest"] = np.isclose(same_event.t_from_detection_s_first,
                                                same_event.t_from_detection_s_largest)
    c10c.write_json(rel(f"{ART}/s1_t3c_summary.json"), {
        "phase": "10c", "stage": "1", "task": "T3c_first_and_largest_since_detection",
        "anchor_delta_caption": ANCHOR_DELTA_CAPTION,
        "population": "events with at least one sub-burst starting at or after detection, per cell",
        "n_cells_with_a_first_subburst": int(len(first_df)),
        "n_cells_with_a_largest_subburst": int(len(largest_df)),
        "share_where_first_is_also_largest": {
            str(v): float(g.first_is_largest.mean())
            for v, g in same_event.groupby("threshold")},
        "first_subburst_timing_summary": {
            str(v): summary(g.t_from_detection_s.to_numpy())
            for v, g in first_df.groupby("threshold")},
        "config_hash": chash,
    })

    print(f"\nT3a n sub-bursts with a valid anchor: {sb_v.det_ns.notna().sum()}/{len(sb_v)}")
    print(f"T3b n (event,variant,kernel) density rows: {len(t3b)}")
    print(f"T3c first-is-largest share by variant: "
          f"{ {str(v): float(g.first_is_largest.mean()) for v, g in same_event.groupby('threshold')} }")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
